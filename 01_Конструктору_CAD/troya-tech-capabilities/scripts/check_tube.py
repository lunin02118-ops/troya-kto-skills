# -*- coding: utf-8 -*-
"""Проверка трубной детали на возможности TROYA: труборез Bodor K0-65 + трубогибы + оснастка.

Примеры:
  python check_tube.py --shape round --a 32 --s 1.2 --length 2400 --bend-r 85 85 --straights 120 300 90
  python check_tube.py --shape rect --a 40 --b 20 --s 1.5 --length 1800 --bend-r 90 --plane b
  python check_tube.py --shape square --a 25 --s 1.5 --length 7000 --json

Вердикты: OK / УСЛОВНО (нужна проверка/оснастка/данные) / НЕЛЬЗЯ (своими силами).
"""
import argparse
import json
import math
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "tube_capabilities.json"
DENSITY = {"steel": 7.85, "ss": 7.93, "al": 2.70}  # г/см3


def linear_mass(shape, a, b, s, material):
    """кг/м по наружному контуру (упрощённо, без радиусов скругления)."""
    rho = DENSITY[material]
    if shape == "round":
        area = math.pi * (a - s) * s
    elif shape in ("square", "rect"):
        b = b or a
        area = 2 * (a + b) * s - 4 * s * s
    elif shape == "oval":  # плоскоовальная: 2 полукруга Ø b + 2 прямых (a-b)
        area = (math.pi * (b - s) + 2 * (a - b)) * s
    else:
        return None
    return area * rho / 1000.0  # мм2 * г/см3 -> кг/м


def check_laser(c, args, res):
    L = c["tube_laser"]
    a, b = args.a, args.b or args.a
    notes, verdict = [], "OK"
    if args.shape == "round":
        lo, hi = L["round_d"]
        if not lo <= a <= hi:
            verdict = "НЕЛЬЗЯ"; notes.append(f"Ø{a} вне диапазона Ø{lo}–{hi}")
    elif args.shape in ("square", "rect", "oval"):
        lo, hi = L["rect_side"]
        if not (lo <= a <= hi and lo <= b <= hi):
            verdict = "НЕЛЬЗЯ"; notes.append(f"стороны {a}×{b} вне {lo}–{hi}")
        if args.shape == "oval":
            notes.append("овальная труба — зажим «лапами изнутри», подтвердить у оператора")
    elif args.shape in ("angle", "channel"):
        m = max(a, b)
        if m > L["angle_channel_side_max_catalog"]:
            verdict = "НЕЛЬЗЯ"; notes.append(f"полка {m} > {L['angle_channel_side_max_catalog']}")
        elif m > L["angle_channel_side_max"]:
            verdict = "УСЛОВНО"; notes.append(f"полка {m} > {L['angle_channel_side_max']} по договору (каталог допускает до 80)")
    if args.length is not None and args.length + L["min_tail"] > L["stock_length_max"]:
        verdict = "НЕЛЬЗЯ"; notes.append(f"длина детали {args.length} + отход {L['min_tail']} > хлыста {L['stock_length_max']}")
    if args.s:
        m = linear_mass(args.shape, a, b, args.s, args.material)
        if m:
            res["linear_mass_kg_m"] = round(m, 2)
            if m > L["linear_mass_max_kg_m"]:
                verdict = "НЕЛЬЗЯ"; notes.append(f"{m:.1f} кг/м > {L['linear_mass_max_kg_m']} кг/м")
            elif m * L["stock_length_max"] / 1000 > L["stock_mass_max_kg"]:
                notes.append(f"хлыст 6,5 м ≈{m*6.5:.0f} кг > {L['stock_mass_max_kg']} кг — брать короче")
        notes.append("макс. толщина стенки по материалу в паспорте не указана — сверить с таблицей режимов 3 кВт")
    if verdict == 'OK' and (L.get('wall_max') is None or args.s is None or args.length is None or args.shape == 'oval'):
        verdict = 'УСЛОВНО'
    if args.length is None:
        notes.append('Длина заготовки не задана — проверка длины не выполнена')
    if args.s is None:
        notes.append('Толщина стенки не задана — масса и режимы резки не проверены')
    res["laser"] = {"machine": L["model"], "status": L['status'], "verdict": verdict, "notes": notes}


def check_bend(c, args, res):
    if not args.bend_r:
        return
    a, b = args.a, args.b
    out = {"benders": [], "tooling": [], "verdict": "НЕЛЬЗЯ", "notes": []}
    for m in c["benders"]:
        ok, why = None, ""
        if args.shape == "round" and "round_steel" in m:
            lo, hi = m["round_steel"]["d"]
            smax = m["round_steel"].get("s_max")
            if args.material == "ss" and "round_stainless" in m:
                hi, smax = m["round_stainless"]["d_max"], m["round_stainless"]["s_max"]
            ok = (lo is None or a >= lo) and a <= hi and (smax is None or args.s is None or args.s <= smax)
            why = f"Ø{lo or '?'}–{hi}, s≤{smax or '?'}"
            if ok and (lo is None or smax is None or args.s is None or args.material == 'al'
                       or (args.material == 'ss' and 'round_stainless' not in m)):
                ok = None
        elif args.shape in ("square", "rect") and "profile_steel" in m:
            lo, hi = m["profile_steel"]["a"]
            ok = lo <= a <= hi and (not b or lo <= b <= hi) and (args.s is None or args.s <= m["profile_steel"]["s_max"])
            why = f"профиль {lo}–{hi}, s≤{m['profile_steel']['s_max']}"
            if ok and (args.s is None or args.material != 'steel'):
                ok = None
        if m['status'] not in ('passport', 'offer'):
            ok = None
        out["benders"].append({"id": m["id"], "model": m["model"], "fits": ok, "limits": why or m.get("note", "нет данных"),
                               "status": m["status"]})
    need = sorted(set(args.bend_r))
    tol = 0.5
    for r in need:
        hits = [t for t in c["tooling"]
                if t["shape"] == args.shape and abs(t["a"] - a) <= tol
                and (args.shape in ("round", "square") or (t["b"] and b and abs(t["b"] - b) <= tol))
                and abs(t["clr"] - r) <= tol
                and (t.get('s') is None or (args.s is not None and abs(t['s']-args.s) <= 0.05))
                and (not args.plane or not t["plane"] or t["plane"] == args.plane)]
        out["tooling"].append({"R": r, "found": hits})
    candidates = []
    for machine in out['benders']:
        definition = next(m for m in c['benders'] if m['id'] == machine['id'])
        compatible = [[t for t in radius['found'] if t['machine'] == machine['id']
                       and t['status'] in ('passport','offer','drawing')
                       and (args.shape in ('round','square') or
                            (args.plane is not None and t.get('plane') == args.plane))]
                      for radius in out['tooling']]
        clr = definition.get('clr')
        radius_fits = bool(clr) and all(clr[0] <= r <= clr[1] for r in need)
        if machine['fits'] is True and radius_fits and all(compatible):
            candidates.append(dict(machine=machine['id'], tooling=compatible))
    out['confirmed_candidates'] = candidates
    out['verdict'] = 'OK' if candidates else 'УСЛОВНО'
    if not candidates:
        out['notes'].append('Нет подтверждённого сочетания: материал/стенка + пределы станка + вся оснастка на этом станке. Запросить технолога; OK не подтверждён.')
        miss = [x['R'] for x in out['tooling'] if not x['found']]
        if miss:
            out['notes'].append(f'Нет совместимой оснастки под R {miss}')
        if all(x['fits'] is False for x in out['benders']):
            out['verdict'] = 'НЕЛЬЗЯ'
    if len(need) > 2:
        out["notes"].append("более 2 радиусов в детали: на CNC35ED — 2 радиуса + раскатка за установку")
        if out['verdict'] == 'OK':
            out['verdict'] = 'УСЛОВНО'
    # прямые участки
    selected_tools = [t for candidate in candidates for group in candidate['tooling'] for t in group]
    L1 = max((t['L1_clamp'] for t in selected_tools if t.get('L1_clamp')), default=None)
    limit = L1 or (1.5 * a)
    src = f"L1={L1} (оснастка)" if L1 else f"1,5·D≈{limit:.0f} (ориентир)"
    for i, st in enumerate(args.straights or []):
        if st < limit:
            out["notes"].append(f"прямая #{i+1} = {st} < {src} — нужен припуск/перехват, согласовать с технологом")
            if out["verdict"] == "OK":
                out["verdict"] = "УСЛОВНО"
    if args.s and a / args.s > 25:
        out["notes"].append(f"D/s = {a/args.s:.0f} > 25 — тонкостенная, гибка только с дорном, нужен пробный гиб")
        if out['verdict'] == 'OK':
            out['verdict'] = 'УСЛОВНО'
    if not args.straights or L1 is None or any(t.get('L1_clamp') is None for t in selected_tools):
        out['notes'].append('Прямые участки/длины прижимов не подтверждены; ориентир 1,5·D не заменяет данные оснастки')
        if out['verdict'] == 'OK':
            out['verdict'] = 'УСЛОВНО'
    res["bending"] = out


def validate_input(args):
    for name in ('a', 'b', 's', 'length'):
        value = getattr(args, name)
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError(f'{name}: требуется конечное положительное значение')
    for name in ('bend_r', 'straights'):
        if any(not math.isfinite(value) or value <= 0 for value in (getattr(args,name) or [])):
            raise ValueError(f'{name}: требуются конечные положительные значения')
    if args.shape in ('rect','oval','angle','channel') and args.b is None:
        raise ValueError('Для этого профиля требуется --b')
    if args.shape == 'oval' and args.a < args.b:
        raise ValueError('Для овала a должна быть не меньше b')
    if args.shape == 'square' and args.b is not None and args.b != args.a:
        raise ValueError('Для квадрата b должна равняться a')
    if args.shape in ('round','square','rect','oval') and args.s is not None and 2*args.s >= min(args.a,args.b or args.a):
        raise ValueError('Стенка должна быть меньше половины наружного размера')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shape", required=True, choices=["round", "square", "rect", "oval", "angle", "channel"])
    ap.add_argument("--a", type=float, required=True, help="Ø или большая сторона, мм")
    ap.add_argument("--b", type=float, help="малая сторона, мм")
    ap.add_argument("--s", type=float, help="толщина стенки, мм")
    ap.add_argument("--material", default="steel", choices=list(DENSITY))
    ap.add_argument("--length", type=float, help="длина заготовки детали (развёртка), мм")
    ap.add_argument("--bend-r", type=float, nargs="*", help="радиусы гибов по оси, мм")
    ap.add_argument("--plane", choices=["a", "b"], help="какая сторона профиля в плоскости гиба")
    ap.add_argument("--straights", type=float, nargs="*", help="длины прямых участков по порядку, мм")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        validate_input(args)
    except ValueError as exc:
        ap.error(str(exc))
    if args.shape == "square":
        args.b = args.a
    sys.stdout.reconfigure(encoding="utf-8")
    c = json.loads(DATA.read_text(encoding="utf-8"))
    res = {"input": {k: v for k, v in vars(args).items() if v not in (None, False)},
           "data_updated": c['_meta']['updated'], 'coverage': 'Проверка перечисленных пределов; не утверждение КД к выпуску'}
    check_laser(c, args, res)
    check_bend(c, args, res)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    print(f"Профиль: {args.shape} {args.a:g}" + (f"×{args.b:g}" if args.b and args.shape != 'round' else "")
          + (f"×{args.s:g}" if args.s else "") + (f"  ~{res.get('linear_mass_kg_m')} кг/м" if res.get("linear_mass_kg_m") else ""))
    lz = res["laser"]
    print(f"\n[Труборез] {lz['verdict']} — {lz['machine']}")
    for n in lz["notes"]:
        print("   •", n)
    if "bending" in res:
        bd = res["bending"]
        print(f"\n[Гибка] {bd['verdict']}")
        for m in bd["benders"]:
            mark = {True: "подходит", False: "не подходит", None: "нет данных"}[m["fits"]]
            if m["fits"] and m["status"] == "os_only":
                mark += " (по обозначению модели, не подтверждено)"
            print(f"   {m['model']}: {mark} ({m['limits']})")
        for t in bd["tooling"]:
            if t["found"]:
                for h in t["found"]:
                    extra = ", ".join(f"{k}={h[k]}" for k in ("L1_clamp", "L2_pressure", "plane") if h.get(k))
                    print(f"   R{t['R']:g}: оснастка есть — {h['machine']}" + (f" ({extra})" if extra else ""))
            else:
                print(f"   R{t['R']:g}: оснастки НЕТ")
        for n in bd["notes"]:
            print("   •", n)


if __name__ == "__main__":
    main()

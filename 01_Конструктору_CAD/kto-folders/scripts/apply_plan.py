"""Выполняет plan.csv из sort_plan.py. Ничего не удаляет.

python apply_plan.py --plan <папка плана>\\plan.csv            # только показать (по умолчанию)
python apply_plan.py --plan ... --apply                        # копировать
python apply_plan.py --plan ... --apply --move --quarantine <папка>   # копировать, сверить, исходник -> карантин

- создаёт все папки из folders.txt (полное дерево заказа, даже пустые);
- копирует с сохранением дат во временный файл, сверяет SHA-256, затем переименовывает;
- если в месте назначения уже есть файл: тот же SHA-256 — пропуск; другой — новый файл кладётся
  в <папка назначения>\\_Конфликт_<дата>\\ и попадает в журнал (ничего не перезаписывается; занятое имя
  и там — к нему добавляется « (2)», « (3)»…);
- --move: исходник переносится в карантин с сохранением относительного пути (не удаляется);
- журнал: apply_log_<дата-время>.csv рядом с планом (у каждого запуска свой);
- пути назначения обязаны лежать внутри папки заказа, а исходники — внутри разбираемой папки (meta.json),
  иначе запуск останавливается без действий;
- --move не трогает исходник, изменённый менее 2 ч назад.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import shutil
import sys

REPARSE_POINT = 0x400


def long_path(p):
    p = os.path.abspath(p)
    if os.name == "nt" and not p.startswith("\\\\?\\"):
        return "\\\\?\\UNC\\" + p[2:] if p.startswith("\\\\") else "\\\\?\\" + p
    return p


def inside(path, root):
    """Path is inside root after resolving symlinks/junctions; reparse escapes fail closed."""
    p_abs, r_abs = os.path.abspath(path), os.path.abspath(root)
    def has_reparse_component(candidate):
        cur = candidate
        while True:
            try:
                st = os.lstat(cur)
                if os.path.islink(cur) or (getattr(st, "st_file_attributes", 0) & REPARSE_POINT):
                    return True
            except FileNotFoundError:
                pass
            parent = os.path.dirname(cur)
            if parent == cur:
                return False
            cur = parent
    if has_reparse_component(p_abs) or has_reparse_component(r_abs):
        return False
    try:
        return os.path.commonpath([os.path.realpath(p_abs), os.path.realpath(r_abs)]).casefold() == os.path.realpath(r_abs).casefold() \
            and os.path.normcase(p_abs) != os.path.normcase(r_abs)
    except ValueError:
        return False


def roots_overlap(left, right):
    l, r = os.path.realpath(os.path.abspath(left)).casefold(), os.path.realpath(os.path.abspath(right)).casefold()
    return l == r or l.startswith(r + os.sep) or r.startswith(l + os.sep)


FRESH = datetime.timedelta(hours=2)


def conflict_name(dst, stamp):
    """Свободное имя в <папка dst>\\_Конфликт_<stamp>: две строки плана с одним dst не затирают друг друга."""
    folder = os.path.join(os.path.dirname(dst), f"_Конфликт_{stamp}")
    stem, ext = os.path.splitext(os.path.basename(dst))
    final, n = os.path.join(folder, stem + ext), 1
    while os.path.exists(long_path(final)) or os.path.exists(long_path(final + ".part")):
        n += 1
        final = os.path.join(folder, f"{stem} ({n}){ext}")
    return final


def sha256(path):
    h = hashlib.sha256()
    with open(long_path(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--move", action="store_true")
    ap.add_argument("--quarantine")
    a = ap.parse_args()
    if a.move and not a.quarantine:
        ap.error("--move требует --quarantine")

    plan_dir = os.path.dirname(os.path.abspath(a.plan))
    meta = json.load(open(os.path.join(plan_dir, "meta.json"), encoding="utf-8"))
    with open(a.plan, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    folders_file = os.path.join(plan_dir, "folders.txt")
    folders = [l.strip() for l in open(folders_file, encoding="utf-8") if l.strip()] if os.path.exists(folders_file) else []

    # Колонку dst разрешено править руками (SKILL.md): опечатка или абсолютный путь увели бы файлы в чужой заказ
    # или в корень _Заявки. Всё, что пишется, должно лежать внутри папки заказа — иначе ничего не делаем.
    outside = [r["dst"] for r in rows if r["action"] == "copy" and not inside(r["dst"], meta["order"])]
    outside += [d for d in folders if not inside(d, meta["order"])]
    if outside:
        print(f"ОСТАНОВЛЕНО: {len(outside)} путей вне папки заказа {meta['order']}:")
        for d in outside[:20]:
            print("  ", d)
        sys.exit(2)
    # Исходник тоже должен лежать в разбираемой папке: при --move относительный путь от неё с «..» увёл бы файл
    # мимо карантина, а исходник из чужой папки в плане — признак испорченного plan.csv.
    stray = [r["src"] for r in rows if r["action"] == "copy" and not inside(r["src"], meta["src"])]
    if stray:
        print(f"ОСТАНОВЛЕНО: {len(stray)} исходников вне разбираемой папки {meta['src']}:")
        for d in stray[:20]:
            print("  ", d)
        sys.exit(2)

    todo = [r for r in rows if r["action"] == "copy"]
    roots = [meta["src"], meta["order"]]
    if a.move:
        qroot = os.path.abspath(a.quarantine)
        roots.append(qroot)
        if roots_overlap(qroot, meta["src"]) or roots_overlap(qroot, meta["order"]):
            print("ОСТАНОВЛЕНО: карантин пересекается с источником или заказом")
            sys.exit(2)
    # Check every existing ancestor of all roots/targets before creating any directory.
    for root in roots:
        cur = os.path.abspath(root)
        while True:
            try:
                st = os.lstat(cur)
                if os.path.islink(cur) or (getattr(st, "st_file_attributes", 0) & REPARSE_POINT):
                    print(f"ОСТАНОВЛЕНО: reparse/link в корне или предке: {cur}")
                    sys.exit(2)
            except FileNotFoundError:
                pass
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    if a.move:
        for r in todo:
            q = os.path.join(a.quarantine, os.path.relpath(r["src"], meta["src"]))
            if not inside(q, a.quarantine):
                print(f"ОСТАНОВЛЕНО: путь карантина вне карантина: {q}")
                sys.exit(2)

    print(f"Заказ: {meta['order']}\nФайлов в плане: {len(rows)}, к переносу: {len(todo)}, "
          f"пропуск: {len(rows) - len(todo)}, папок создать: {len(folders)}")
    print("Режим:", "ПЕРЕНОС (копия → сверка → исходник в карантин)" if a.move else "КОПИРОВАНИЕ (исходник не меняется)")
    if not a.apply:
        print("Это пробный запуск. Для выполнения добавьте --apply.")
        return

    for d in folders:
        os.makedirs(long_path(d), exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log = []
    ok = err = same = conflict = 0
    for r in todo:
        src, dst, want = r["src"], r["dst"], r["sha256"]
        status, final = "", dst
        try:
            if not os.path.exists(long_path(src)):
                raise FileNotFoundError("исходник пропал")
            if sha256(src) != want:
                raise RuntimeError("исходник изменился после построения плана — перестройте план")
            if a.move and datetime.datetime.now() - datetime.datetime.fromtimestamp(os.stat(long_path(src)).st_mtime) < FRESH:
                raise RuntimeError("исходник изменён менее 2 ч назад — с ним, возможно, работают; не трогаю")
            if os.path.exists(long_path(dst)):
                if sha256(dst) == want:
                    status = "уже есть"
                    same += 1
                else:
                    final = conflict_name(dst, stamp)
                    conflict += 1
            if not status:
                os.makedirs(long_path(os.path.dirname(final)), exist_ok=True)
                tmp = final + ".part"
                shutil.copy2(long_path(src), long_path(tmp))
                if sha256(tmp) != want:
                    raise RuntimeError("контрольная сумма копии не совпала (временный файл оставлен: .part)")
                os.replace(long_path(tmp), long_path(final))
                status = "скопирован" if final == dst else "конфликт имени"
                ok += 1
            if a.move:
                q = os.path.join(a.quarantine, os.path.relpath(src, meta["src"]))
                if not inside(q, a.quarantine):
                    raise RuntimeError(f"путь в карантине вне папки карантина: {q}")
                os.makedirs(long_path(os.path.dirname(q)), exist_ok=True)
                if os.path.exists(long_path(q)):
                    raise RuntimeError(f"в карантине уже есть {q}")
                shutil.move(long_path(src), long_path(q))
                status += " + исходник в карантин"
        except Exception as e:  # noqa: BLE001 — журналируем и идём дальше
            status = f"ОШИБКА: {e}"
            err += 1
        log.append({"src": src, "dst": final, "status": status, "sha256": want})

    # Журнал каждого запуска — свой файл: повторный запуск того же плана не затирает историю.
    log_path = os.path.join(plan_dir, f"apply_log_{stamp}.csv")
    with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, ["src", "dst", "status", "sha256"], delimiter=";")
        w.writeheader()
        w.writerows(log)
    print(f"Готово: скопировано {ok}, уже было {same}, конфликтов имён {conflict}, ошибок {err}. Журнал: {log_path}")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()

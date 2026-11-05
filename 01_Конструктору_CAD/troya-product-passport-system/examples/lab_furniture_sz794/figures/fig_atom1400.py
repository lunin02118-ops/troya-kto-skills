# -*- coding: utf-8 -*-
"""Рисунки для стола ученического «Атом» 1400×600×750 для кабинета химии с мойкой СтAt1400C-02 (поз. 7):
рисунок 1 «Общий вид», рисунок 2 «Схема монтажа стола» (разнесённый вид), рисунок 3 «Подключение раковины
и крана», изображение для обложки.
Металлокаркас — по КД заказа 794 («Стол 1400х600х750.pdf», «Рама.pdf»): опоры 724×500 из трубы 40×20×1,5
как у «Атома» 1200, рама экрана 1220×402, столешница 1404×604×16. Сервисной тумбы, отверстия под раковину
и бортиков в КД нет: это опция данной нестандартной модификации (пользователь, 24.10.2026) — тумба (подвесная,
под столешницей по центру, дверца к учащимся), раковина и кран показаны по описанию СЗ № 794-М. Тумба крепится к экрану винтом М8×35
через отверстие в задней стенке (пользователь, 24.10.2026) — ось и выноска на рисунке 2.
Запуск: python -P fig_atom1400.py <папка вывода>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fig_atom1200 import D, H, LEGS, YF, YL, YO, Z_TOP, palette, parts as atom_parts, sup
from fig_demo1800 import mixer
from iso import Drawing, extrude, box, ring, rounded_rect, translate
from sch import Sheet

L = 1400
SUP = sup(L)
TUMBA = (550, 850, 70, 466, 120, Z_TOP)   # условно: x0, x1, y0, y1, z0, z1 — перед экраном, 120 мм от пола
SINK = (700, 250)                         # ось раковины
R_RIM, R_BOWL = 80, 62                    # борт и чаша раковины (посадочный Ø 135)
MIX = (700, 420)                          # ось крана — над тумбой, за раковиной


def disc(cx, cy, r, z0, h, name, pat=None, line=1.0, n=32):
    """Цилиндр с вертикальной осью."""
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
    return extrude(pts, (0, 0, h), name, pat, line, smooth=True)


def parts():
    g = atom_parts(False, L)
    g["top"] = [extrude(rounded_rect(0, 0, L, D, Z_TOP, r_front=50), (0, 0, H - Z_TOP), "столешница",
                        ring((SINK[0], SINK[1], H), R_RIM + 4))]
    x0, x1, y0, y1, z0, z1 = TUMBA
    g["tumba"] = [box(x0, y0, z0, x1, y1, z1, "тумба"), box(x0 + 2, y0 - 16, z0 + 2, x1 - 2, y0, z1 - 2, "дверца")]
    cx, cy = SINK
    g["sink"] = [disc(cx, cy, R_RIM, H, 3, "раковина", ring((cx, cy, H + 3), R_BOWL) + [("dot", (cx, cy, H + 3), 10)]),
                 disc(cx, cy, R_BOWL, H - 110, 110, "раковина")]
    g["drain"] = [disc(cx, cy, 20, H - 130, 20, "слив", line=0.7), disc(cx, cy, 20, H - 350, 220, "слив", line=0.7)]
    g["tap"] = [s for i, s in enumerate(mixer(MIX[0], MIX[1], H)) if i not in (4, 6)]   # кран без левого вентиля
    return g


def general():
    g = parts()
    del g["sink"][1]                      # чаша и слив скрыты в тумбе
    del g["drain"]
    d = Drawing(116, 76, view="спереди-справа")
    for items in g.values():
        d.add(*items)
    d.callout(1, (SUP[1][1], 320, 300), (12, -8))
    d.callout(2, (L - 300, YF + 9, 380), (18, -10))
    d.callout(3, (1050, 150, H), (18, 10))
    d.callout(4, (620, TUMBA[2] - 16, 300), (-16, -10))
    d.callout(6, (SINK[0] - R_RIM, SINK[1], H + 3), (-18, 4))
    d.callout(8, (MIX[0], MIX[1], H + 170), (16, 12))
    d.callout(9, (SUP[1][0] - 20, YO[0] - 12, 1), (-14, -6))
    return d


def mounting():
    g = parts()
    up, fwd = 350, 380
    off = {"frame": (0, 0, 0), "feet": (0, 0, -90), "brackets": (0, 0, -45), "tumba": (0, -fwd, 0),
           "top": (0, 0, up), "rim_long": (0, 0, up + 160), "rim_l": (-170, 0, up + 110), "rim_r": (170, 0, up + 110),
           "sink": (0, 0, up + 440), "drain": (0, 0, up + 440), "tap": (0, 0, up + 300),
           "socket": (0, 0, 0), "shield": (0, 0, 0)}
    d = Drawing(116, 104, view="спереди-справа")
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    ax = "dashdot"
    for x in (70, L - 70):                            # саморезы: лапа верхняя — столешница
        for y in (YL[0] + 40, YL[1] - 40):
            # видимая часть оси: выше неё луч к наблюдателю (+x, −y, +z) упирается в поднятую столешницу
            z_vis = Z_TOP + up - min(L - x, y)
            if z_vis > 734:
                d.polyline([(x, y, 734), (x, y, z_vis)], ax, 0.5)
    d.polyline([(8, 383, H + up), (8 - 170, 383, H + up + 110)], ax, 0.5)
    d.polyline([(L - 8, 383, H + up), (L - 8 + 170, 383, H + up + 110)], ax, 0.5)
    d.polyline([(L - 300, D - 8, H + up), (L - 300, D - 8, H + up + 160)], ax, 0.5)
    xc = (TUMBA[0] + TUMBA[1]) / 2
    # тумба — на место; ось начинается за очерком выдвинутой тумбы (луч к наблюдателю: +x, −y, +z)
    d.polyline([(xc, TUMBA[3] - fwd + (TUMBA[1] - xc), 450), (xc, TUMBA[3] - 20, 450)], ax, 0.5)
    d.polyline([(SINK[0], SINK[1], H + up), (SINK[0], SINK[1], H + up + 440 - 350)], ax, 0.5)
    d.polyline([(MIX[0], MIX[1], H + up), (MIX[0], MIX[1], H + up + 300)], ax, 0.5)
    for x0, x1 in SUP:                                # опора М8 через кронштейн в лапу
        for yo in YO:
            if (x0, yo) != (SUP[0][0], YO[1]):        # задняя левая — за выдвинутой тумбой
                d.polyline([((x0 + x1) / 2, yo, 10), ((x0 + x1) / 2, yo, -82)], ax, 0.5)
    d.callout(1, (SUP[1][1], 320, 300), (12, -8))
    d.callout(2, (L - 300, YF + 9, 380), (16, -10))
    d.callout(3, (850, 150, H + up), (14, 10))
    d.callout(4, (620, TUMBA[2] - 16 - fwd, 300), (-14, -8))
    d.callout(6, (SINK[0] - 0.7 * R_RIM, SINK[1] - 0.7 * R_RIM, H + up + 443), (-4, 14))
    d.callout(7, (SINK[0] - 20, SINK[1], H + up + 440 - 250), (-16, -4))
    d.callout(8, (MIX[0], MIX[1], H + up + 300 + 170), (14, 6))
    d.callout(9, (SUP[1][0] - 20, YO[0] - 12, -44), (-12, -6))
    d.callout("М6×10", (100, YF, 400), (-16, 6))
    d.callout("М8×35", (xc, TUMBA[3] - 80, 450), (4, -20))     # винт через заднюю стенку тумбы в экран
    d.callout("опора М8", (SUP[1][1] - 20, YO[0] - 12, -86), (12, -4))
    return d


def water(path):
    """Схема подключения раковины и однорожкового крана к водопроводу холодной воды (В1) и канализации (К1),
    обозначения трубопроводов по ГОСТ 21.601; подводка, запорный кран и трубопроводы — сети здания."""
    s = Sheet(116, 88)

    def lead(x, y, xt, yt, label, left=False):
        """Выноска: точка на элементе, наклонная линия и полка с надписью."""
        s.dot(x, y, 0.9)
        w = s.text_w(label, 3.0) + 1.0
        x2 = xt - w if left else xt + w
        s.line([(x, y), (xt, yt), (x2, yt)], 0.18)
        s.text(min(xt, x2) + 0.5, yt - 0.8, label, 3.0)

    zt = 28                                            # верх столешницы
    s.line([(4, zt), (82, zt)], 0.5)
    s.line([(4, zt + 2.4), (82, zt + 2.4)], 0.25)
    # раковина (разрез): борт на столешнице, круглая чаша, выпуск
    s.line([(18, zt - 1), (46, zt - 1), (46, zt), (18, zt), (18, zt - 1)], 0.35)
    bowl = [(32 + 12 * math.cos(math.radians(a)), zt + 15 * math.sin(math.radians(a))) for a in range(0, 181, 10)]
    s.line(bowl, 0.5)
    s.line([(32, zt + 15), (32, zt + 20)], 0.5)
    s.rect(30, zt + 20, 34, zt + 23, 0.35)
    # кран однорожковый: корпус, излив, вентиль
    s.rect(53, zt - 4, 59, zt, 0.35)
    s.line([(56, zt - 4), (56, zt - 18), (36, zt - 18), (36, zt - 11)], 0.5)
    s.line([(59, zt - 2.5), (62, zt - 2.5)], 0.35)
    # гибкая подводка и запорный кран на В1
    xe = 70
    s.line([(56, zt), (56, zt + 18), (xe, zt + 24), (xe, zt + 32)], 0.35, dash=(1.6, 0.8))
    y = zt + 32
    s.line([(xe - 1.5, y), (xe + 1.5, y + 3), (xe + 1.5, y), (xe - 1.5, y + 3), (xe - 1.5, y)], 0.35)
    s.line([(xe, y + 3), (xe, zt + 43)], 0.6)
    s.text(xe - 1.8, zt + 47, "В1", 3.0)
    # слив: гофра 40×220 с петлёй гидрозатвора к канализации
    s.line([(32, zt + 23), (32, zt + 33), (34, zt + 35), (38, zt + 35), (40, zt + 33), (40, zt + 29),
            (42, zt + 27.5), (45, zt + 28), (47, zt + 31), (47, zt + 36)], 0.5, dash=(1.6, 0.8))
    s.line([(44, zt + 36), (50, zt + 36), (50, zt + 43), (44, zt + 43), (44, zt + 36)], 0.5)
    s.text(45, zt + 47, "К1", 3.0)
    # позиции
    lead(56, zt - 12, 66, zt - 22, "8")
    lead(42, zt + 8, 12, zt + 10, "6", left=True)
    lead(32, zt + 30, 12, zt + 27, "7", left=True)
    # условные обозначения
    x, y = 86, 14
    for t in ("6 – раковина", "     лабораторная", "7 – слив, гофра", "     40×220 мм", "8 – кран", "     однорожковый",
              "В1 – холодная вода", "К1 – канализация", "     Ø50"):
        s.text(x, y, t, 2.7)
        y += 4.4
    s.text(4, 83, "Подводка гибкая и запорный кран G1/2\", трубопроводы В1 и К1 –", 2.6)
    s.text(4, 87, "сети здания, в комплект поставки не входят.", 2.6)
    s.save(path)
    return path


PALETTE = dict(palette(False), **{"тумба": (206, 206, 202), "дверца": (214, 214, 210), "раковина": (242, 242, 242),
                                  "слив": (150, 152, 156), "смеситель": (170, 172, 176)})


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    d = general()
    print(d.render(os.path.join(out, "07_рис1_общий_вид.png")))
    print(mounting().render(os.path.join(out, "07_рис2_схема_монтажа.png")))
    print(water(os.path.join(out, "07_рис3_подключение_раковины.png")))
    d.w_mm, d.h_mm = 67, 56
    print(d.render(os.path.join(out, "07_обложка.png"), palette=PALETTE))


if __name__ == "__main__":
    main()

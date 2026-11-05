# -*- coding: utf-8 -*-
"""Рисунки для стола препараторского пристенного СПП.М2.00 (поз. 4): рисунок 1 «Общий вид», рисунок 2 «Схема монтажа
стола и надстройки» (разнесённый вид), изображение для обложки. Схема электрическая — fig_el_spp1200.py.
Геометрия — по КД заказа 794: СБ и схема сборки СПП.М2.00 (1204×704×750(1350)): каркас стола 1144×644×720 из трубы
30×30×1,5 (опоры левая и правая, перемычки), столешница 1204×704×22 со скруглёнными передними углами, царга 404 мм
у стены, вставки боковые 374 мм; каркас полки надстройки 1198×130×578 из трубы 25×25×1,5, полка 1220×190×22,
под полкой светильник IP65, короб с двумя розетками, бокс с дифавтоматом у правой опоры. Цоколя надстройки
в изделии нет (пользователь, 24.10.2026) — не рисуется.
Сторона стены — y = 704.
Запуск: python -P fig_spp1200.py <папка вывода>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fig_atom1200 import LEGS
from iso import Drawing, box, extrude, rounded_rect, translate

L, D = 1204, 704
Z_FOOT = 8
Z_TOP = 728                              # низ столешницы
H = Z_TOP + 22                           # 750
LX = [(30, 60), (1144, 1174)]            # ноги стола 30×30
LY = [(30, 60), (644, 674)]
SX = [(3, 28), (1176, 1201)]             # стойки надстройки 25×25
SY = [(574, 599), (679, 704)]            # глубина каркаса полки 130
Z_SH = H + 578                           # низ полки 1328
BOX = (40, 1040, 600, 679, 1150, 1220)   # короб с розетками
RCD = (1060, 1166, 610, 679, 1145, 1225)  # бокс с дифавтоматом
LAMP = (60, 1140, 605, 655, 1290, 1322)  # светильник под полкой


def parts():
    g = {k: [] for k in ("frame", "feet", "top", "panel", "ins_l", "ins_r", "super", "shelf", "box")}
    for x0, x1 in LX:
        for y0, y1 in LY:
            g["frame"].append(box(x0, y0, Z_FOOT, x1, y1, Z_TOP, "каркас"))
            g["feet"].append(box(x0 + 3, y0 + 3, 0, x1 - 3, y1 - 3, Z_FOOT, "опора регулируемая", line=0.7))
        g["frame"].append(box(x0, LY[0][1], Z_TOP - 30, x1, LY[1][0], Z_TOP, "каркас"))        # верх опоры
    for y0, y1 in LY:                                                                         # перемычки
        g["frame"].append(box(LX[0][1], y0, Z_TOP - 30, LX[1][0], y1, Z_TOP, "каркас"))
    g["top"].append(extrude(rounded_rect(0, 0, L, D, Z_TOP, r_front=50), (0, 0, 22), "столешница"))
    g["panel"].append(box(LX[0][1], LY[1][0] - 16, Z_TOP - 30 - 374, LX[1][0], LY[1][0], Z_TOP - 30, "царга"))
    for k, (x0, x1) in (("ins_l", LX[0]), ("ins_r", LX[1])):
        g[k].append(box(x0 + 7, LY[0][1], Z_TOP - 30 - 344, x0 + 23, LY[1][0], Z_TOP - 30, "вставка"))
    for x0, x1 in SX:                                                                         # опоры полки
        for y0, y1 in SY:
            g["super"].append(box(x0, y0, H, x1, y1, Z_SH, "каркас"))
        for z0 in (H + 120, Z_SH - 25):
            g["super"].append(box(x0, SY[0][1], z0, x1, SY[1][0], z0 + 25, "каркас"))
    g["super"].append(box(SX[0][1], SY[1][0], Z_SH - 25, SX[1][0], SY[1][1], Z_SH, "каркас"))   # перемычка полки
    x0, x1, y0, y1, z0, z1 = LAMP
    g["super"].append(box(x0, y0, z0, x1, y1, z1, "светильник"))
    x0, x1, y0, y1, z0, z1 = RCD
    g["super"].append(box(x0, y0, z0, x1, y1, z1, "бокс", {"front": [
        ("l", (x0 + 20, y0, z0 + 20), (x1 - 20, y0, z0 + 20)), ("l", (x1 - 20, y0, z0 + 20), (x1 - 20, y0, z1 - 20)),
        ("l", (x1 - 20, y0, z1 - 20), (x0 + 20, y0, z1 - 20)), ("l", (x0 + 20, y0, z1 - 20), (x0 + 20, y0, z0 + 20))]}))
    g["shelf"].append(extrude(rounded_rect(-8, D - 190, L + 8, D, Z_SH, r_front=50), (0, 0, 22), "полка"))
    x0, x1, y0, y1, z0, z1 = BOX
    sockets = []
    for xs in (820, 920):                                                    # две розетки на лицевой стороне короба
        q = [(xs, y0, z0 + 12), (xs + 80, y0, z0 + 12), (xs + 80, y0, z1 - 12), (xs, y0, z1 - 12)]
        sockets += [("l", q[i], q[(i + 1) % 4]) for i in range(4)]
        sockets += [("dot", (xs + 28, y0, (z0 + z1) / 2), 4), ("dot", (xs + 52, y0, (z0 + z1) / 2), 4)]
    g["box"].append(box(x0, y0, z0, x1, y1, z1, "короб", {"front": sockets}))
    return g


def general():
    g = parts()
    d = Drawing(116, 100, view="спереди-слева")
    for items in g.values():
        d.add(*items)
    d.callout(1, (45, LY[0][0], 300), (-14, -8))
    d.callout(2, (850, 250, H), (16, 12))
    d.callout(3, (15, SY[0][0], 1000), (-14, 4))
    d.callout(4, (300, D - 150, Z_SH + 22), (-12, 10))
    d.callout(5, (300, LAMP[2], LAMP[4] + 10), (-22, 6))
    d.callout(6, (860, BOX[2], 1185), (6, 22))
    d.callout(7, ((RCD[0] + RCD[1]) / 2, RCD[2], 1185), (14, 10))
    d.callout(11, (LX[0][0] + 7, 400, 500), (-16, -6))
    d.callout(12, (500, BOX[2], 1185), (-24, 2))
    d.callout(9, (45, 45, 3), (-10, -6))
    return d


def mounting():
    g = parts()
    up = 260
    off = {"frame": (0, 0, 0), "feet": (0, 0, -80), "top": (0, 0, up), "panel": (0, 260, 0), "ins_l": (-220, 0, 0),
           "ins_r": (220, 0, 0), "super": (0, 0, up + 260), "shelf": (0, 0, up + 420), "box": (0, -300, up + 260)}
    d = Drawing(116, 100, view="спереди-слева")
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    ax = "dashdot"
    for x0, x1 in LX:                                   # шурупы 4×19: каркас стола — столешница
        for y in (45, 659):
            d.polyline([((x0 + x1) / 2, y, Z_TOP), ((x0 + x1) / 2, y, Z_TOP + up)], ax, 0.5)
    for x0, x1 in SX:                                   # винты М8×60: стойки надстройки через столешницу в каркас
        for y0, y1 in SY:
            d.polyline([((x0 + x1) / 2, (y0 + y1) / 2, H + up), ((x0 + x1) / 2, (y0 + y1) / 2, H + up + 260)], ax, 0.5)
        d.polyline([((x0 + x1) / 2, D - 95, Z_SH + up + 260), ((x0 + x1) / 2, D - 95, Z_SH + up + 420)], ax, 0.5)
    d.polyline([(600, LY[1][0] + 260, 500), (600, LY[1][0], 500)], ax, 0.5)
    d.polyline([(LX[0][0] - 205, 350, 550), (LX[0][0] + 15, 350, 550)], ax, 0.5)
    d.polyline([(LX[1][1] + 205, 350, 550), (LX[1][1] - 15, 350, 550)], ax, 0.5)
    d.polyline([(500, BOX[2] - 300, 1185 + up + 260), (500, BOX[2], 1185 + up + 260)], ax, 0.5)
    d.callout(1, (45, LY[0][0], 300), (-12, -8))
    d.callout(2, (1000, 420, H + up), (22, -4))
    d.callout(3, (15, SY[0][0], 1000 + up + 260), (-12, 4))
    d.callout(4, (300, D - 150, Z_SH + 22 + up + 420), (-10, 8))
    d.callout(10, (1100, LY[1][0] - 16 + 260, 420), (16, -14))
    d.callout(11, (LX[0][0] - 213, 400, 500), (-10, -6))
    d.callout(12, (1000, BOX[2] - 300, 1185 + up + 260), (18, 6))
    d.callout("М8×16", (LX[1][0], LY[0][0] + 15, Z_TOP - 15), (18, -4))
    d.callout("М8×60", (SX[1][0] + 12, SY[1][0] + 12, H + up + 130), (22, -10))
    d.callout("4×19", (LX[1][0] + 15, 45, Z_TOP + 130), (18, -2))
    return d


PALETTE = {"каркас": LEGS, "опора регулируемая": (45, 45, 45), "столешница": (214, 214, 210), "царга": (206, 206, 202),
           "вставка": (206, 206, 202), "полка": (214, 214, 210), "короб": (206, 206, 202),
           "светильник": (238, 238, 238), "бокс": (236, 236, 236)}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    d = general()
    print(d.render(os.path.join(out, "04_рис1_общий_вид.png")))
    print(mounting().render(os.path.join(out, "04_рис2_схема_монтажа.png")))
    d.w_mm, d.h_mm = 67, 56
    print(d.render(os.path.join(out, "04_обложка.png"), palette=PALETTE))


if __name__ == "__main__":
    main()

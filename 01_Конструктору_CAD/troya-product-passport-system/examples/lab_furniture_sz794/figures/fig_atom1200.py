# -*- coding: utf-8 -*-
"""Рисунки для столов «Атом» 1200×600×750 (поз. 5 — физика с розетками, поз. 6 — биология):
рисунок 1 «Общий вид», рисунок 2 «Схема монтажа» (разнесённый вид), изображение для обложки.
Геометрия — по КД заказа 794 («Стол 1200х600х750.pdf»: виды спереди, слева, сверху) и схемам сборки
03_Корпус\\02_Схемы сборки: две розетки вплотную к продольному бортику по центру, щиток на внутренней
стороне правой опоры, гофра под столешницей и внутри правой опоры, кронштейн крепления к полу —
Z-образная пластина под торцом лапы, крепится винтом регулируемой опоры М8.
Запуск: python -P fig_atom1200.py <папка вывода>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import Drawing, box, extrude, holes_grid, ring, rounded_rect, slots, translate

L, D, H = 1200, 600, 750
T_TOP = 16
Z_TOP = H - T_TOP                 # низ столешницы


def sup(L):
    """Стойки опор по x (труба 40×20): 50 мм от торцов столешницы; между ними рама экрана (L − 180)."""
    return [(50, 90), (L - 90, L - 50)]


SUP = sup(L)
YP = [(310, 330), (450, 470)]     # трубы стойки по y (вид слева КД: стойка 310…470 от переднего края)
YL = (80, 580)                    # лапы 500 мм
YO = (YL[0] + 30, YL[1] - 30)     # оси регулируемых опор: 30 мм от торцов лап (3D-модель)
YF = 470                          # экран: рамка 20×20 за стойками
YS = (D - 16 - 72, D - 16)        # розетки вплотную к продольному бортику


def rib_side(x0):
    """Боковой бортик 402×72 мм со скруглением R50 переднего верхнего угла, ЛДСП 16."""
    y0, y1, z0, z1, r = D - 16 - 402, D - 16, H, H + 72, 50
    pts = [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1)]
    for i in range(11):
        a = math.radians(90 + 90 * i / 10)
        pts.append((x0, y0 + r + r * math.cos(a), z1 - r + r * math.sin(a)))
    return extrude(pts, (16, 0, 0), "бортик боковой")


def bracket(xc, yo, s):
    """Кронштейн крепления к полу: Z-образная полоса 24×2 мм. Верхняя полка — под торцом лапы, на ней
    винт опоры М8; нижняя полка с отверстием под дюбель лежит на полу, отогнута внутрь стола (s = ±1 по x)."""
    y = yo - 12
    pts = [(xc - 14 * s, y, 10), (xc + 16 * s, y, 10), (xc + 28 * s, y, 2), (xc + 60 * s, y, 2),
           (xc + 60 * s, y, 0), (xc + 26 * s, y, 0), (xc + 14 * s, y, 8), (xc - 14 * s, y, 8)]
    return extrude(pts, (0, 24, 0), "кронштейн", line=0.7)


def parts(electric, L=L):
    """Тела в собранном положении, сгруппированные для разнесённого вида; L — длина стола (1200 или 1400)."""
    g = {k: [] for k in ("frame", "feet", "brackets", "top", "rim_long", "rim_l", "rim_r", "socket", "shield")}
    for (x0, x1), s in zip(sup(L), (1, -1)):
        xc = (x0 + x1) / 2
        g["frame"].append(box(x0, YL[0], 10, x1, YL[1], 30, "лапа низ"))
        g["frame"].append(box(x0, YL[0], 714, x1, YL[1], 734, "лапа верх"))
        for y0, y1 in YP:
            g["frame"].append(box(x0, y0, 30, x1, y1, 714, "стойка"))
        sl = {f: slots(338, 60, 442, 690, 22, lambda u, v, x=x: (x, u, v)) for f, x in (("left", xc - 1), ("right", xc + 1))}
        g["frame"].append(box(xc - 1, 330, 40, xc + 1, 450, 704, "вставка", sl, line=0.7))
        for yo in YO:
            g["feet"].append(box(xc - 12, yo - 12, 0, xc + 12, yo + 12, 8, "опора регулируемая", line=0.7))
            g["brackets"].append(bracket(xc, yo, s))
    # экран: рамка 20×20 и перфорированная вставка
    perf = {f: holes_grid(L // 2 - 410, 345, L // 2 + 410, 685, 22, 4.5, lambda u, v, y=y: (u, y, v))
            for f, y in (("front", YF + 9), ("back", YF + 11))}
    g["frame"] += [
        box(110, YF + 9, 335, L - 110, YF + 11, 694, "царга перфорированная", perf, line=0.7),
        box(90, YF, 694, L - 90, YF + 20, 714, "рама верх"), box(90, YF, 315, L - 90, YF + 20, 335, "рама низ"),
        box(90, YF, 335, 110, YF + 20, 694, "рама стойка"), box(L - 110, YF, 335, L - 90, YF + 20, 694, "рама стойка"),
    ]
    g["top"].append(extrude(rounded_rect(0, 0, L, D, Z_TOP, r_front=50), (0, 0, T_TOP), "столешница"))
    g["rim_long"].append(box(0, D - 16, H, L, D, H + 73, "бортик задний"))
    g["rim_l"].append(rib_side(0))
    g["rim_r"].append(rib_side(L - 16))
    if electric:
        yc = (YS[0] + YS[1]) / 2
        for x0 in (L // 2 - 90, L // 2):   # розетка двойная: два гнезда в общем корпусе
            face = ring((x0 + 45, yc, H + 35), 24) + [("dot", (x0 + 45 + d, yc, H + 35), 3) for d in (-9, 9)]
            g["socket"].append(box(x0, YS[0], H, x0 + 90, YS[1], H + 35, "розетка двойная", {"top": face}))
        g["shield"].append(box(L - 150, 335, 540, L - 90, 445, 660, "щиток"))
    return g


def general(electric):
    """Рисунок 1. Поз. 5 — со стороны учащихся (видны розетки у бортика), поз. 6 — со стороны экрана, как в КД."""
    g = parts(electric)
    d = Drawing(116, 80, view="спереди-слева" if electric else "сзади-справа")
    for items in g.values():
        d.add(*items)
    if electric:
        d.callout(1, (50, 400, 300), (-16, -2))
        d.callout(2, (300, YF + 9, 380), (16, -16))
        d.callout(3, (750, 200, H), (22, -10))
        d.callout(4, (555, (YS[0] + YS[1]) / 2, H + 35), (-14, 12))
        d.callout(7, (120, YO[0] - 12, 1), (-14, -4))
    else:
        d.callout(1, (1150, 460, 300), (-18, -4))
        d.callout(2, (420, YF + 11, 500), (18, 2))
        d.callout(3, (250, 120, H), (-12, 8))
        d.callout(4, (1085, YO[1] + 12, 1), (14, -2))
    return d


def mounting(electric):
    """Рисунок 2: разнесённый вид со стороны учащихся слева (как схема сборки 03_Корпус)."""
    g = parts(electric)
    up = 350
    off = {"frame": (0, 0, 0), "feet": (0, 0, -90), "brackets": (0, 0, -45), "top": (0, 0, up),
           "rim_long": (0, 0, up + 160), "rim_l": (-170, 0, up + 110), "rim_r": (170, 0, up + 110),
           "socket": (0, 0, up + 120), "shield": (-100, 0, 0)}
    d = Drawing(116, 96 if electric else 80, view="спереди-слева")   # поз. 5: рисунок 2 помещается под п. 4.2.3
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    ax = "dashdot"
    for x in (70, 1130):                              # саморезы: лапа верхняя — столешница
        for y in (YL[0] + 40, YL[1] - 40):
            # видимая часть оси: выше неё луч к наблюдателю (−x, −y, +z) упирается в поднятую столешницу
            z_vis = min(Z_TOP + up, Z_TOP + up - min(x, y))
            if z_vis > 734:
                d.polyline([(x, y, 734), (x, y, z_vis)], ax, 0.5)
    d.polyline([(8, 383, H + up), (8 - 170, 383, H + up + 110)], ax, 0.5)
    d.polyline([(L - 8, 383, H + up), (L - 8 + 170, 383, H + up + 110)], ax, 0.5)
    d.polyline([(600, D - 8, H + up), (600, D - 8, H + up + 160)], ax, 0.5)
    for xc in (70, 1130):                             # опора М8 через кронштейн в лапу
        for yo in YO:
            d.polyline([(xc, yo, 10), (xc, yo, -82)], ax, 0.5)
    if electric:
        yc = (YS[0] + YS[1]) / 2
        d.polyline([(600, yc, H + up), (600, yc, H + up + 120)], ax, 0.5)
        d.polyline([(1110, 390, 600), (1010, 390, 600)], ax, 0.5)
        # провод в гофротрубе (невидимый контур): под столешницей от розеток к правой опоре и внутри неё к полу
        zg = Z_TOP + up - 8
        d.polyline([(690, yc, zg), (1095, yc, zg), (1095, 390, zg)], True, 0.8)
        d.polyline([(1130, 390, 700), (1130, 390, 0)], True, 0.8)
        # щиток на левой опоре (по заказу) — контур другого положения, зеркально правому
        x0, x1, y0, y1, z0, z1 = 190, 250, 335, 445, 540, 660
        for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
            for z in (z0, z1):
                d.polyline([(*a, z), (*b, z)], "phantom", 0.5)
            d.polyline([(*a, z0), (*a, z1)], "phantom", 0.5)
    d.callout(1, (50, 400, 300), (-14, -2))
    d.callout(2, (500, YF + 9, 400), (12, -16))
    d.callout(3, (400, 150, H + up), (-14, 8) if electric else (-18, 16))
    d.callout("М6×10", (1095, YF, 600), (26, 6))
    d.callout("опора М8", (1130, YO[0] - 12, -86), (12, -4))
    if electric:
        d.callout(4, (555, (YS[0] + YS[1]) / 2, H + up + 155), (-10, 12))
        d.callout(5, (950, 390, 600), (20, 2))
        d.callout("5 (по заказу)", (190, 335, 660), (-12, 6))
        d.callout(6, (1130, 390, 300), (14, -2))
        d.callout(7, (120, YO[0] - 12, -44), (-12, -4))
    else:
        d.callout(4, (120, YO[0] - 12, -44), (-12, -4))
    return d


LEGS, SCREEN = (122, 126, 132), (198, 201, 205)


def palette(electric):
    """Нейтральные тона: цвета экрана, опор и облицовки задаются заказом (свидетельство о приёмке), не рисунком."""
    pal = {n: LEGS for n in ("лапа низ", "лапа верх", "стойка", "вставка", "кронштейн")}
    pal.update({n: SCREEN for n in ("царга перфорированная", "рама верх", "рама низ", "рама стойка")})
    pal.update({"столешница": (222, 222, 219), "бортик задний": (190, 190, 187), "бортик боковой": (190, 190, 187),
                "опора регулируемая": (45, 45, 45), "розетка двойная": (242, 242, 242), "щиток": (236, 236, 236)})
    return pal


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    for key, electric in (("05", True), ("06", False)):
        d = general(electric)
        print(d.render(os.path.join(out, f"{key}_рис1_общий_вид.png")))
        print(mounting(electric).render(os.path.join(out, f"{key}_рис2_схема_монтажа.png")))
        d.w_mm, d.h_mm = 67, 56           # рамка изображения на обложке
        print(d.render(os.path.join(out, f"{key}_обложка.png"), palette=palette(electric)))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Схемы сборки тумб и ящика стола демонстрационного 1800×750×900 (поз. 1 — химия, поз. 2 — физика).
Источник — схема сборки «Стол демонстрационный в каб. физики» (сх сб.pdf, 24.10.2026) и деталировка
«Демонстр.столы с бортиками…» (03_Корпус\\02_Схемы сборки): боковины 839×547 стоят на дне (горизонте) и крепятся
к нему конфирматами 50 снизу, ножки 27 мм под дном, ребро жёсткости 418×71 вверху сзади на эксцентриках и шкантах,
полка 416×537 на полкодержателях, дверцы на внешних петлях; ящик — боковины 501×101, задняя стенка 359×101
(эксцентрик + шкант), дно ХДФ 390×500 на гвоздях, накладка 447×140, направляющие 500 мм на саморезах 16 мм.
У поз. 1 дно тумбы под мойкой 452×452 (сзади проход для коммуникаций), полка только в тумбе с ящиком.
У поз. 2 между тумбами передняя панель 725×206 со щитком и розеткой (эксцентрики + шканты в боковины тумб).
Запуск: python -P fig_demo_tumba.py <папка вывода>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import Drawing, box, extrude, translate

W, D, T = 452, 547, 16                 # тумба: ширина, глубина, толщина ЛДСП
Z_LEG = 27                             # ножка 27 мм
Z_BOT = Z_LEG + T                      # верх дна (горизонта)
Z_TOP = Z_BOT + 839                    # верх боковин
X_R = W + 724                          # левый край правой тумбы (между тумбами передняя панель 725)
DOOR_L, DOOR_R, OVERLAY = (45, 832), (45, 690), (694, 834)   # дверца 787, дверца 645, накладка 140 (по высоте)
BOX_X = ((W - 391) / 2, (W + 391) / 2)  # короб ящика 391 = 359 + 2×16, по центру проёма 420
BOX_Z = (715, 816)                     # боковины ящика высотой 101


def disc(cx, cy, r, z0, h, name, line=1.0, n=24):
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
    return extrude(pts, (0, 0, h), name, None, line, smooth=True)


def handle(xc, y, z):
    """Ручка-скоба 128 мм на лицевой стороне (y — лицевая плоскость)."""
    return [box(xc - 64, y - 28, z, xc - 56, y, z + 10, "ручка", line=0.7),
            box(xc + 56, y - 28, z, xc + 64, y, z + 10, "ручка", line=0.7),
            box(xc - 64, y - 36, z, xc + 64, y - 28, z + 10, "ручка", line=0.7)]


def drawer_parts(x0=0.0, y0=0.0, z0=0.0):
    """Ящик в собранном положении (относительно тумбы с левым краем x0), группы для разнесённого вида."""
    a, b = BOX_X
    z1, z2 = BOX_Z
    o = lambda s: translate(s, (x0, y0, z0))
    g = {
        "side_l": [box(a, 0, z1, a + T, 501, z2, "ящик")],
        "side_r": [box(b - T, 0, z1, b, 501, z2, "ящик")],
        "back": [box(a + T, 501 - T, z1, b - T, 501, z2, "ящик")],
        "bottom": [box(a + 0.5, 0, z1 - 3, b - 0.5, 500, z1, "дно ящика", line=0.7)],
        "overlay": [box(2.5, -T, OVERLAY[0], W - 2.5, 0, OVERLAY[1], "накладка")] + handle(W / 2, -T, 758),
        "guide_l": [box(T, 0, 748, a, 500, 783, "направляющая", line=0.7)],
        "guide_r": [box(b, 0, 748, W - T, 500, 783, "направляющая", line=0.7)],
    }
    return {k: [o(s) for s in v] for k, v in g.items()}


def tumba_parts(x0, bottom_d, shelf, door, hinge_right, drawer):
    """Тумба с левым краем x0: группы тел в собранном положении."""
    o = lambda s: translate(s, (x0, 0, 0))
    legs = [disc(x, y, 20, 0, Z_LEG, "ножка", line=0.7)
            for x in (45, W - 45) for y in (45, bottom_d - 45)]
    g = {
        "legs": legs,
        "bottom": [box(0, 0, Z_LEG, W, bottom_d, Z_BOT, "корпус")],
        "side_l": [box(0, 0, Z_BOT, T, D, Z_TOP, "корпус")],
        "side_r": [box(W - T, 0, Z_BOT, W, D, Z_TOP, "корпус")],
        "rib": [box(T + 1, D - T, Z_TOP - 71, W - T - 1, D, Z_TOP, "корпус")],
        "shelf": [box(T + 2, 5, 420, W - T - 2, 542, 420 + T, "корпус")] if shelf else [],
    }
    xh = W - 30 if hinge_right else 30                      # петли — у наружной кромки дверцы
    d = [box(2.5, -T, door[0], W - 2.5, 0, door[1], "дверца")]
    d += handle(W / 2, -T, door[1] - 60)
    d += [box(xh - 9, 0, z - 22, xh + 9, 36, z + 22, "петля", line=0.6) for z in (door[0] + 100, door[1] - 100)]
    g["door"] = d
    g = {k: [o(s) for s in v] for k, v in g.items()}
    if drawer:
        g["drawer"] = [s for v in drawer_parts(x0).values() for s in v]
    return g


def tumba():
    """Рисунок «Схема сборки тумбы с ящиком» (у поз. 1 и 2 одинаковая): разнесённый вид. Тумба с дверцей
    собирается так же, без ящика — в тексте паспорта."""
    g = tumba_parts(0, D, True, DOOR_R, True, True)
    off = {"legs": (0, 0, -230), "bottom": (0, 0, -110), "side_l": (-170, 0, 0), "side_r": (170, 0, 0),
           "rib": (0, 0, 150), "shelf": (0, -270, 0), "door": (0, -720, 0), "drawer": (0, -430, 0)}
    d = Drawing(116, 60, view="спереди-справа")
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    ax = "dashdot"
    for xs, dx in ((T / 2, -170), (W - T / 2, 170)):         # конфирматы 50: дно — боковины (снизу)
        for y in (60, D - 60):
            d.polyline([(xs + dx, y, Z_BOT), (xs, y, Z_BOT - 110)], ax, 0.5)
    for xs, dx in ((T, -170), (W - T, 170)):                 # ребро — боковины: стяжки и шканты
        d.polyline([(xs + dx, D - 8, Z_TOP - 35), (xs, D - 8, Z_TOP - 35 + 150)], ax, 0.5)
    for x in (45, W - 45):                                   # ножки — в дно
        d.polyline([(x, D - 45, Z_LEG - 230), (x, D - 45, Z_LEG - 110)], ax, 0.5)
    d.callout("боковина", (W + 170, 300, 450), (12, -6))
    d.callout("ребро жёсткости", (W - 60, D, Z_TOP + 150 - 35), (12, 8))
    d.callout("дно", (W - 60, 0, Z_BOT - 110), (16, -12))
    d.callout("ножка 27", (W - 25, 25, -215), (12, -16))
    d.callout("ящик", (BOX_X[1], 250 - 430, BOX_Z[1]), (-20, 10))
    d.callout("полка", (T + 2, 5 - 270, 428), (-16, 0))
    d.callout("петля", (W - 21, -720 + 36, DOOR_R[0] + 100), (10, -10))
    d.callout("дверца", (100, -T - 720, 300), (-14, -8))
    return d


def drawer():
    """Рисунок «Схема сборки ящика»: разнесённый вид."""
    g = drawer_parts()
    off = {"side_l": (-130, 0, 0), "side_r": (130, 0, 0), "back": (0, 200, 0), "bottom": (0, 0, -150),
           "overlay": (0, -280, 0), "guide_l": (-300, 0, 0), "guide_r": (300, 0, 0)}
    d = Drawing(116, 52, view="спереди-справа")
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    a, b = BOX_X
    z1, z2 = BOX_Z
    zm = (z1 + z2) / 2
    ax = "dashdot"
    for x, dx in ((a + T / 2, -130), (b - T / 2, 130)):      # стенка задняя — боковины
        d.polyline([(x + dx, 501 - T / 2, zm), (x + dx, 501 + 200 - T / 2, zm)], ax, 0.5)
    for x in (a + 60, b - 60):                               # дно — гвоздями
        d.polyline([(x, 470, z1 - 150), (x, 470, z1)], ax, 0.5)
    for x, dx in ((a + T / 2, -130), (b - T / 2, 130)):      # накладка — боковины
        d.polyline([(x + dx, -T - 280, zm), (x + dx, 0, zm)], ax, 0.5)
    for xs, dx in ((a, -300), (b, 300)):                     # направляющие — боковины ящика
        d.polyline([(xs + dx + (14 if dx < 0 else -14), 250, 765), (xs + (dx * 130 / 300), 250, 765)], ax, 0.5)
    d.callout("боковина ящика", (b + 130, 300, z2 - 20), (12, 10))
    d.callout("стенка задняя", ((a + b) / 2 + 100, 501 + 200, z2), (10, 12))
    d.callout("дно (ХДФ)", (a + 100, 80, z1 - 150), (-20, 12))
    d.callout("накладка", (100, -T - 280, OVERLAY[0] + 30), (-14, -8))
    d.callout("ручка", (W / 2 + 64, -T - 36 - 280, 763), (10, -10))
    d.callout("направляющая", (W - T + 300, 0, 765), (12, -8))
    return d


PALETTE = {"корпус": (206, 206, 202), "дверца": (214, 214, 210), "накладка": (214, 214, 210), "ящик": (206, 206, 202),
           "дно ящика": (225, 215, 195), "ручка": (150, 152, 156), "петля": (170, 172, 176), "ножка": (45, 45, 45),
           "направляющая": (170, 172, 176), "панель": (206, 206, 202), "щиток": (236, 236, 236),
           "розетка": (242, 242, 242)}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    print(tumba().render(os.path.join(out, "01_02_схема_сборки_тумбы.png")))
    print(drawer().render(os.path.join(out, "01_02_схема_сборки_ящика.png")))


if __name__ == "__main__":
    main()

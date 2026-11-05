# -*- coding: utf-8 -*-
"""Рисунки для тумбы лабораторной с мойкой ТЛМ.М2.760.00 (поз. 3): рисунок 1 «Общий вид», рисунок 2 «Схема монтажа
тумбы» (разнесённый вид), рисунок 3 «Подключение смесителя и сифона», изображение для обложки.
Геометрия — по КД заказа 794: СБ ТЛМ.М2.760.00, каркас ТЛМ.М2.760.01 (опоры боковые 582×729 из трубы 30×30×1,5
со связью на высоте 139 мм, перемычки 698 мм вверху спереди и сзади, опоры регулируемые М6), крышка ТЛМ.М2.760.00.01
804×604×22 (саморезы 4×16 снизу через каркас). По фото готового изделия (24.10.2026): крышка — столешница из ЛДСП
с врезной прямоугольной мойкой, смещённой влево, отверстие под смеситель за мойкой. Мойка — полипропиленовая
Stegler RM-490G (пользователь, 24.10.2026): 550×450×310 наружные, чаша 490×390×290. Корпус из ЛДСП
открыт сверху (боковины, задняя стенка, дно) и стоит внутри каркаса на уголках стяжки, закреплённых на связях
боковых опор; две дверцы (на фото не навешены).
Запуск: python -P fig_tumba760.py <папка вывода>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fig_atom1200 import LEGS
from fig_demo1800 import mixer, rect_lines, water
from iso import Drawing, box, extrude, rounded_rect, translate

L, D = 804, 604
Z_FOOT = 10                            # регулируемые опоры М6
FX = [(23, 53), (751, 781)]            # боковые опоры (сторона трубы 30 вдоль x)
FY = (11, 593)                         # глубина каркаса 582
ZF = (Z_FOOT, Z_FOOT + 729)            # высота каркаса 729 + опоры = 739
Z_TIE = Z_FOOT + 139                   # верх связи
Z_WT = ZF[1]                           # низ столешницы
H = Z_WT + 21                          # верх столешницы 760
T_LDSP = 16
SINK = (80, 630, 55, 505)              # мойка полипропиленовая Stegler RM-490G: 550 × 450 по борту, смещена влево
RIM = 6                                # борт мойки над столешницей
BOWL_IN = 30                           # ширина борта: чаша внутри 490 × 390
BOWL_D = 304                           # корпус чаши под столешницей (наружная высота мойки 310 − борт)
DRAIN = (355, 280)                     # выпуск
MIX = (355, 549)                       # отверстие под смеситель — за мойкой
CORPUS = (53, 751, 41, 593, Z_TIE + 3, ZF[1] - 30)   # корпус ЛДСП между опорами: на уголках связей, до перемычек


def sink_top():
    """Узор верха борта мойки: контур чаши и выпуск."""
    x0, x1, y0, y1 = SINK
    k = BOWL_IN
    return rect_lines(x0 + k, x1 - k, y0 + k, y1 - k, H + RIM) + [("dot", (DRAIN[0], DRAIN[1], H + RIM), 14)]


def corpus_parts():
    """Корпус из ЛДСП 16: боковины, задняя стенка, дно (сверху открыт — под мойкой)."""
    x0, x1, y0, y1, z0, z1 = CORPUS
    t = T_LDSP
    return [box(x0, y0, z0, x0 + t, y1, z1, "корпус"), box(x1 - t, y0, z0, x1, y1, z1, "корпус"),
            box(x0 + t, y1 - t, z0 + t, x1 - t, y1, z1, "корпус"), box(x0 + t, y0, z0, x1 - t, y1 - t, z0 + t, "корпус")]


def parts():
    g = {k: [] for k in ("frame", "feet", "corpus", "doors", "top", "sink", "bowl", "mixer", "brackets")}
    for x0, x1 in FX:
        for y0 in (FY[0], FY[1] - 30):
            g["frame"].append(box(x0, y0, ZF[0], x1, y0 + 30, ZF[1], "каркас"))
            g["feet"].append(box(x0 + 3, y0 + 3, 0, x1 - 3, y0 + 27, Z_FOOT, "опора регулируемая", line=0.7))
        for z0 in (ZF[0], Z_TIE - 30, ZF[1] - 30):                 # низ, связь, верх боковой опоры
            g["frame"].append(box(x0, FY[0] + 30, z0, x1, FY[1] - 30, z0 + 30, "каркас"))
    for y0 in (FY[0], FY[1] - 30):                                   # перемычки
        g["frame"].append(box(FX[0][1], y0, ZF[1] - 30, FX[1][0], y0 + 30, ZF[1], "каркас"))
    for x0 in (FX[0][1], FX[1][0] - 30):                             # уголки стяжки на связях
        for yb in (120, 450):
            g["brackets"].append(box(x0, yb, Z_TIE, x0 + 30, yb + 30, Z_TIE + 3, "уголок", line=0.6))
    g["corpus"] += corpus_parts()
    x0, x1, y0, y1, z0, z1 = CORPUS
    for dx0, dx1 in ((x0 + 2, (x0 + x1) / 2 - 1), ((x0 + x1) / 2 + 1, x1 - 2)):
        g["doors"].append(box(dx0, y0 - 16, z0 + 2, dx1, y0, z1 - 2, "дверца"))
        xh = dx1 - 40 if dx0 < (x0 + x1) / 2 else dx0 + 28    # ручки у притвора
        g["doors"].append(box(xh, y0 - 26, z1 - 170, xh + 12, y0 - 16, z1 - 70, "ручка", line=0.7))
    g["top"].append(box(0, 0, Z_WT, L, D, H, "столешница"))
    sx0, sx1, sy0, sy1 = SINK
    g["sink"].append(extrude(rounded_rect(sx0, sy0, sx1, sy1, H, r_front=40, r_back=40), (0, 0, RIM), "мойка",
                             sink_top()))
    k = BOWL_IN - 5                                                  # стенка чаши 5 мм
    g["bowl"].append(box(sx0 + k, sy0 + k, H - BOWL_D, sx1 - k, sy1 - k, H, "мойка"))
    g["mixer"] += mixer(MIX[0], MIX[1], H)
    return g


def general():
    g = parts()
    del g["bowl"]                                      # чаша скрыта в корпусе
    d = Drawing(116, 92, view="спереди-справа")
    for items in g.values():
        d.add(*items)
    d.callout(1, (FX[1][1], 300, Z_TIE - 15), (14, -8))
    d.callout(2, (CORPUS[1], 330, 420), (16, 4))
    d.callout(3, (220, CORPUS[2] - 16, 420), (-16, -10))
    d.callout(5, (432, CORPUS[2] - 26, CORPUS[5] - 120), (-18, 6))
    d.callout(6, (710, 300, H), (16, 14))
    d.callout(7, (SINK[0] + 60, SINK[2], H + RIM), (-18, 6))
    d.callout(9, (MIX[0], MIX[1], H + 170), (-12, 10))
    return d


def mounting():
    g = parts()
    up, fwd = 330, 420
    s_up, m_up = up + BOWL_D + 70, up + BOWL_D + 310        # низ чаши поднятой мойки на 70 мм выше столешницы
    off = {"frame": (0, 0, 0), "feet": (0, 0, -80), "brackets": (0, 0, 0), "corpus": (0, -fwd, 0),
           "doors": (0, -fwd - 160, 0), "top": (0, 0, up), "sink": (0, 0, s_up), "bowl": (0, 0, s_up),
           "mixer": (0, 0, m_up)}
    d = Drawing(116, 94, view="спереди-справа")          # 94 мм: рисунок встаёт на страницу после п. 4.2.4
    for k, items in g.items():
        d.add(*[translate(s, off[k]) for s in items])
    ax = "dashdot"
    # дверцы — на петли боковин корпуса, оси у наружных кромок дверец. Видимый участок по лучу к наблюдателю
    # (+x, −y, +z): у левой дверцы — над её верхней кромкой, у правой — сразу за кромкой. Ось корпуса не показана —
    # корпус открыт сверху и закрывает её целиком
    zd = CORPUS[5] - 30
    y_back = CORPUS[2] - fwd - 160
    for xd, y0 in ((CORPUS[0] + 8, y_back + (CORPUS[5] - 2 - zd)), (CORPUS[1] - 8, y_back + 8)):
        d.polyline([(xd, y0, zd), (xd, CORPUS[2] - fwd, zd)], ax, 0.5)
    for x, y in ((38, 26), (766, 26), (766, 578)):                                              # столешница на каркас
        d.polyline([(x, y, Z_WT), (x, y, Z_WT + up)], ax, 0.5)
    # мойка в вырез: оси по диагональным углам под бортом, вне очерка чаши; верхние ≈ 13 мм закрыты бортом
    for x, y in ((SINK[0] + 15, SINK[2] + 15), (SINK[1] - 15, SINK[3] - 15)):
        d.polyline([(x, y, H + up), (x, y, H + s_up - 20)], ax, 0.5)
    # смеситель — в отверстие столешницы; ниже борта поднятой мойки ось закрыта мойкой
    d.polyline([(MIX[0], MIX[1], H + s_up + RIM), (MIX[0], MIX[1], H + m_up)], ax, 0.5)
    x0, x1 = FX[1]                                    # опоры слева закрыты выдвинутым корпусом
    for y0 in (FY[0], FY[1] - 30):
        d.polyline([((x0 + x1) / 2, y0 + 15, ZF[0]), ((x0 + x1) / 2, y0 + 15, -72)], ax, 0.5)
    d.callout(1, (FX[1][1], 300, Z_TIE - 15), (12, -8))
    d.callout(2, (CORPUS[1], 330 - fwd, 420), (14, 6))
    d.callout(3, (220, CORPUS[2] - fwd - 176, 420), (-14, -8))
    d.callout(6, (710, 300, H + up), (14, 8))
    d.callout(7, (SINK[0] + 110, SINK[2], H + s_up + RIM), (-18, 4))
    d.callout(9, (MIX[0], MIX[1], H + m_up + 170), (-12, 6))
    d.callout("М8×16", (FX[1][0], FY[0] + 15, ZF[1] - 15), (24, 6))
    d.callout("4×16", (38, 26, Z_WT + 160), (-14, 4))
    d.callout("М6×16", (FX[1][0] - 15, 465, Z_TIE + 3), (18, -6))
    d.callout("опора М6", (FX[1][0] + 15, FY[0] + 15, -76), (12, -4))
    return d


WATER_POZ3 = {"mixer": "9", "sink": "7", "siphon": "8", "hose": "10",
              "legend": ("7 – мойка врезная", "8 – сифон", "9 – смеситель", "     двухрожковый",
                         "10 – подводка гибкая")}

PALETTE = {"каркас": LEGS, "уголок": LEGS, "опора регулируемая": (45, 45, 45), "корпус": (206, 206, 202),
           "дверца": (214, 214, 210), "ручка": (150, 152, 156), "столешница": (230, 230, 227),
           "мойка": (244, 244, 242), "смеситель": (170, 172, 176)}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    d = general()
    print(d.render(os.path.join(out, "03_рис1_общий_вид.png")))
    print(mounting().render(os.path.join(out, "03_рис2_схема_монтажа.png")))
    print(water(os.path.join(out, "03_рис3_подключение_мойки.png"), WATER_POZ3))
    d.w_mm, d.h_mm = 67, 56
    print(d.render(os.path.join(out, "03_обложка.png"), palette=PALETTE))


if __name__ == "__main__":
    main()

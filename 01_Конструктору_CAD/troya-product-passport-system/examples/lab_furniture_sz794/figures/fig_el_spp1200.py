# -*- coding: utf-8 -*-
"""Схема электрическая принципиальная стола препараторского пристенного СПП.М2.00 (поз. 4).
Состав — по комплектности паспорта и КД (короб надстройки с двумя розетками, бокс с дифавтоматом, светильник IP65
под полкой, кабель 3×2,5 в кабель-канале). Отдельного выключателя светильника в комплекте нет: цепь светильника
показана параллельно розеткам после дифавтомата (подтверждает конструктор).
Запуск: python -P fig_el_spp1200.py <папка вывода>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sch import DASH, DASH_DOT, W_THIN, Sheet

L_, N_, PE_ = 18, 28, 38          # ряды проводников L, N, PE


def scheme():
    s = Sheet(116, 104)
    # ввод от групповой линии кабелем W1 из комплекта
    for y, name in ((L_, "L"), (N_, "N"), (PE_, "PE")):
        s.line([(6, y), (37 if y != PE_ else 64, y)])
        s.text(1.5, y + 1.2, name, 3.5)
    s.text(1.5, 46, "~220 В", 3.0)
    s.text(1.5, 50, "50 Гц", 3.0)
    s.cable_tick(14, L_, PE_, "W1")

    # A1 — бокс с дифавтоматом QFD1
    s.rect(22, 6, 62, 46, dash=DASH_DOT)
    s.text(22, 4.6, "A1", 3.5)
    s.ellipse(28, 23, 1.6, 7.5)
    s.rect(25.5, 8, 30.5, 13, w=0.35)
    s.text(28, 10.6, "IΔ", 3.0, anchor="mm")
    s.line([(28, 13), (28, 15.5)])
    mids = [s.breaker_pole(37, y) for y in (L_, N_)]
    xm = mids[0][0]
    s.line([(30.5, 10.5), (xm, 10.5), (xm, mids[1][1])], W_THIN, DASH)
    s.text(45, 11, "QFD1", 3.5)
    s.text(45, 15, "16 А, 30 мА", 3.0)

    # линии после дифавтомата
    s.line([(44, L_), (100, L_)])
    s.line([(44, N_), (110, N_)])
    s.line([(64, PE_), (105, PE_)])
    s.cable_tick(66, L_, PE_, "W2")

    # XS1, XS2 — розетки в коробе надстройки
    for xs, name in ((70, "XS1"), (85, "XS2")):
        for i, y in enumerate((L_, N_, PE_)):
            x = xs + 4.5 * i
            s.dot(x, y)
            s.line([(x, y), (x, 46)])
            s.socket_down(x, 46)
        s.rect(xs - 2.5, 43.5, xs + 11.5, 51.5, dash=DASH_DOT)
        s.text(xs + 4.5, 55.5, name, 3.5, anchor="ms")
        for i, t in enumerate(("L", "N", "PE")):
            s.text(xs + 4.5 * i, 50.6, t, 2.0, anchor="ms")

    # EL1 — светильник (ГОСТ 2.732): круг с крестом, корпус на PE
    cx, cy, r = 105, 48, 3.2
    s.line([(100, L_), (100, cy), (cx - r, cy)])
    s.line([(110, N_), (110, cy), (cx + r, cy)])
    s.dot(105, PE_)
    s.line([(105, PE_), (105, cy - r)], W_THIN)
    s.ellipse(cx, cy, r, r)
    k = r / math.sqrt(2)
    s.line([(cx - k, cy - k), (cx + k, cy + k)], W_THIN)
    s.line([(cx - k, cy + k), (cx + k, cy - k)], W_THIN)
    s.text(cx, 56, "EL1", 3.5, anchor="ms")
    s.cable_tick(98, L_, PE_, "W3")

    s.parts_list(1, 62, [
        ("A1", "Бокс для модульного оборудования", "1", ""),
        ("QFD1", "Выключатель автоматический дифференциального тока 2P (1P+N), 16 А, 30 мА", "1", ""),
        ("XS1, XS2", "Розетка с заземляющим контактом, 16 А, 250 В", "2", ""),
        ("EL1", "Светильник светодиодный пылевлагозащищённый IP65, 36 Вт", "1", ""),
        ("W2, W3", "Кабель медный 3×2,5 мм² в кабель-канале", "1 к-т", ""),
        ("W1", "Кабель ввода медный 3×2,5 мм²", "1", ""),
    ])
    return s


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    print(scheme().save(os.path.join(out, "04_рис3_схема_электрическая.png")))


if __name__ == "__main__":
    main()

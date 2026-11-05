# -*- coding: utf-8 -*-
"""Рисунки паспорта изделия 01 (образец — стол ученический 1200×500×760): рисунок 1 «Общий вид»,
рисунок 2 «Схема монтажа» (разнесённый вид) и изображение для обложки.
Геометрия — <источник: КД …, схема сборки …, модель bCAD …>. Размеры номинальные, без кромки.
Запуск: python -P -E fig_01.py <папка вывода>   (обычно figures\\out)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from iso import Drawing, box, translate

L, D, H = 1200, 500, 760          # габарит
T_TOP = 22                        # толщина столешницы
Z_TOP = H - T_TOP                 # низ столешницы
LEG = 40                          # труба опоры 40×40


def parts():
    """Тела по группам: ключ группы — что поднимается или сдвигается на схеме монтажа."""
    g = {"frame": [], "top": []}
    for x in (60, L - 60 - LEG):
        for y in (40, D - 40 - LEG):
            g["frame"].append(box(x, y, 0, x + LEG, y + LEG, Z_TOP, "каркас"))
        g["frame"].append(box(x, 40, Z_TOP - 60, x + LEG, D - 40, Z_TOP, "каркас"))       # связь опоры
    g["frame"].append(box(60, D - 40 - LEG, Z_TOP - 60, L - 60, D - 40, Z_TOP, "каркас"))  # царга
    g["top"].append(box(0, 0, Z_TOP, L, D, H, "столешница"))
    return g


def general():
    """Рисунок 1: позиции — номера строк таблицы комплектности (1 — каркас, 2 — столешница)."""
    d = Drawing(116, 80, view="спереди-справа")
    for items in parts().values():
        d.add(*items)
    d.callout(1, (80, 40, 300), (-16, -6))      # передняя левая опора
    d.callout(2, (L - 200, 250, H), (14, 8))
    return d


def mounting():
    """Рисунок 2: столешница поднята над каркасом, штрихпунктир — куда она ставится."""
    up = 250
    d = Drawing(116, 90, view="спереди-справа")
    for k, items in parts().items():
        d.add(*[translate(s, (0, 0, up if k == "top" else 0)) for s in items])
    for x, y in ((80, 60), (L - 80, 60), (L - 80, D - 60)):
        d.polyline([(x, y, Z_TOP), (x, y, Z_TOP + up)], "dashdot", 0.5)
    d.callout(1, (80, 40, 300), (-16, -6))      # передняя левая опора
    d.callout(2, (L - 200, 250, H + up), (14, 8))
    return d


PALETTE = {"каркас": (70, 70, 72), "столешница": (225, 222, 214)}   # нейтральные тона: цвета — по заказу


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    os.makedirs(out, exist_ok=True)
    d = general()
    print(d.render(os.path.join(out, "01_рис1_общий_вид.png")))
    print(mounting().render(os.path.join(out, "01_рис2_схема_монтажа.png")))
    d.w_mm, d.h_mm = 67, 56           # рамка изображения на обложке
    print(d.render(os.path.join(out, "01_обложка.png"), palette=PALETTE))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

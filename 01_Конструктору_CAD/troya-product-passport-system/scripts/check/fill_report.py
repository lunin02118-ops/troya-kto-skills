# -*- coding: utf-8 -*-
"""Заполнение страниц PDF паспорта: ищет полупустые страницы — признак плохого переноса.

  python -P -E fill_report.py <pdf или папка> [--low 0.6] [--out отчёт.txt]

fill — доля высоты полосы набора, занятая текстом, рисунками и линиями таблиц (колонтитул не считается).
LOW — страница ниже порога, кроме обложки и последней: обычно таблица или рисунок ушли на следующую
страницу целиком. Сравнивать с отчётом прежней версии: страница, которая была полной и стала LOW, —
следствие последней правки. Для A5 шаблона TROYA поля 34 pt сверху и снизу (680 twips).
"""
import argparse
import glob
import os
import sys

import pymupdf

TOP, BOTTOM = 34.0, 34.0     # поля полосы набора, pt


def footer_top(page):
    """Верх колонтитула: линия над обозначением документа (во всю полосу у нижнего поля), иначе нижнее поле."""
    h, w = page.rect.height, page.rect.width
    ys = [dr["rect"].y0 for dr in page.get_drawings()
          if dr["rect"].height < 1.5 and dr["rect"].width > 0.6 * w and dr["rect"].y0 > h - BOTTOM - 12]
    return min(ys) if ys else h - BOTTOM


def page_fill(page):
    h = page.rect.height
    cut = footer_top(page) - 0.5                    # ниже — колонтитул
    ys = [b[3] for b in page.get_text("blocks") if b[1] < cut and b[4].strip()]
    ys += [im["bbox"][3] for im in page.get_image_info() if im["bbox"][1] < cut]
    ys += [dr["rect"].y1 for dr in page.get_drawings() if dr["rect"].y0 < cut and dr["rect"].y1 >= TOP - 2]
    if not ys:
        return 0.0
    return max(0.0, min(1.0, (min(max(ys), cut) - TOP) / (h - TOP - BOTTOM)))


def lines(page):
    cut = footer_top(page) - 0.5
    txt = [b[4].strip().replace("\n", " ") for b in page.get_text("blocks") if b[1] < cut and b[4].strip()]
    return (txt[0][:60], txt[-1][:60]) if txt else ("", "")


def report(path, low):
    doc = pymupdf.open(path)
    out = [f"== {os.path.basename(path)} pages={doc.page_count}"]
    flagged = 0
    for i, page in enumerate(doc):
        f = page_fill(page)
        first, last = lines(page)
        bad = 0 < i < doc.page_count - 1 and f < low
        flagged += bad
        out.append(f"p{i + 1:02d} fill={f:.2f}{' LOW' if bad else '    '} | first: {first} | last: {last}")
    out.append(f"-- LOW: {flagged}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--low", type=float, default=0.6)
    ap.add_argument("--out")
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.src, "*.pdf"))) if os.path.isdir(a.src) else [a.src]
    text = []
    for f in files:
        text += report(f, a.low)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

# -*- coding: utf-8 -*-
"""Лента страниц PDF в один PNG — посмотреть переносы и рисунки глазами.

  python -P -E render_pages.py <pdf> <страницы> <out.png> [--dpi 60] [--cols 4]

Страницы: «4,5,6», «4-7» или «all». Удобно рендерить одни и те же страницы до и после правки.
Пути с кириллицей из Git Bash передавать как есть; если pymupdf не находит файл — скопировать PDF
во временную папку с латинским именем.
"""
import argparse
import sys

import pymupdf
from PIL import Image


def parse_pages(spec, n):
    if spec == "all":
        return list(range(1, n + 1))
    pages = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages += range(int(a), int(b) + 1)
        else:
            pages.append(int(part))
    return [p for p in pages if 1 <= p <= n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("pages")
    ap.add_argument("out")
    ap.add_argument("--dpi", type=int, default=60)
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    doc = pymupdf.open(a.pdf)
    ims = []
    for p in parse_pages(a.pages, doc.page_count):
        pix = doc[p - 1].get_pixmap(dpi=a.dpi)
        ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    if not ims:
        sys.exit("нет страниц")
    gap = 8
    w, h = max(i.width for i in ims), max(i.height for i in ims)
    cols = min(a.cols, len(ims))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), (150, 150, 150))
    for k, im in enumerate(ims):
        r, c = divmod(k, cols)
        sheet.paste(im, (gap + c * (w + gap), gap + r * (h + gap)))
    sheet.save(a.out)
    print(a.out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

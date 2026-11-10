# -*- coding: utf-8 -*-
"""Рисунки паспортов стульев Nomad — листы пошаговых схем сборки (буквы деталей как на схеме).

Запуск: python -P -E figures\\fig_nomad.py figures\\out
Источник — опубликованные схемы сборки (Пошаговые_Европа). Для NC5-7V пока макет 11.11.2026
(шурупы 4,2×16 ×4); после выкладки схемы заменить путь V_PDF на опубликованный и пересобрать.
"""
import sys
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageChops

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("out"))
EU = Path(r"<WORK>\07_Документация_изделий\02_Инструкции_сборки\Пошаговые_Европа")
R_PDF = EU / "NOMAD_NC3-7R_Стул" / "NC3-7R Схемы сборки.pdf"
V_PDF = Path(r"<WORK>\99_Служебное\Схемы_сборки_NC5-7V\Переделка_вала_2026-11-11\Проверки\Макет.pdf")
DPI = 220
FOOT = 555          # ниже — колонтитул схемы (NOMAD / NC…, номер листа)

# (файл PNG, номер листа с 1, область x0, y0, x1, y1 в пунктах листа 842 × 595)
R = [("r_cover.png", 1, (40, 95, 630, 520)),
     ("r_kit.png", 2, (20, 20, 822, 480)),
     ("r_s1.png", 3, (20, 15, 822, FOOT)),
     ("r_s2.png", 4, (20, 15, 822, FOOT)),
     ("r_s3.png", 5, (20, 15, 822, FOOT)),
     ("r_s4b.png", 7, (20, 15, 822, FOOT)),
     ("r_s5.png", 8, (20, 15, 822, FOOT)),
     ("r_s5b.png", 9, (20, 15, 822, FOOT)),
     ("r_s6.png", 10, (20, 15, 822, FOOT))]
V = [("v_cover.png", 1, (150, 100, 560, 520)),
     ("v_kit.png", 2, (20, 20, 822, 470)),
     ("v_s1.png", 3, (20, 15, 822, FOOT)),
     ("v_s2.png", 4, (20, 15, 822, FOOT)),
     ("v_s3.png", 5, (20, 15, 822, FOOT)),
     ("v_s4a.png", 6, (20, 15, 822, FOOT)),
     ("v_s4b.png", 7, (20, 15, 822, FOOT)),
     ("v_s5.png", 8, (20, 15, 822, FOOT)),
     ("v_s6a.png", 9, (20, 15, 822, FOOT)),
     ("v_s6b.png", 10, (20, 15, 822, FOOT)),
     ("v_s7a.png", 11, (20, 15, 822, FOOT)),
     ("v_s7b.png", 12, (20, 15, 822, FOOT)),
     ("v_s8.png", 13, (20, 15, 822, FOOT))]


def trim(im, pad=12):
    bg = Image.new("RGB", im.size, "white")
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    if not box:
        return im
    x0, y0, x1, y1 = box
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))


def cut(pdf, items):
    doc = fitz.open(pdf)
    for name, page, clip in items:
        pix = doc[page - 1].get_pixmap(dpi=DPI, clip=fitz.Rect(*clip))
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        trim(im).save(OUT / name, dpi=(DPI, DPI))
        print(name, "<-", pdf.name, "лист", page)


OUT.mkdir(parents=True, exist_ok=True)
cut(R_PDF, R)
cut(V_PDF, V)

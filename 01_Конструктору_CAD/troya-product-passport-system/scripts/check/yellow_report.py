# -*- coding: utf-8 -*-
"""Открытые вопросы паспортов: всё, что выделено жёлтым (разметка [[…]] в products.py), с контекстом.

  python -P -E yellow_report.py <docx или папка> [--out отчёт.txt]

По этому списку пишется вопрос пользователю: изделие (шифр и наименование), раздел, что под вопросом.
"""
import argparse
import glob
import os
import sys

from docx import Document
from docx.enum.text import WD_COLOR_INDEX


def paragraphs(doc):
    yield from doc.paragraphs
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def report(path):
    doc = Document(path)
    seen, out = set(), []
    for p in paragraphs(doc):
        if p._p in seen:                # объединённые ячейки повторяют абзац; храним сам элемент, не id()
            continue
        seen.add(p._p)
        marks = [r.text for r in p.runs if r.font.highlight_color == WD_COLOR_INDEX.YELLOW and r.text.strip()]
        if marks:
            ctx = p.text.strip().replace("\n", " ")
            out.append(f"  [{' | '.join(marks)}]  ← {ctx[:150]}")
    return [f"== {os.path.basename(path)}: {len(out)}"] + out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out")
    a = ap.parse_args()
    files = sorted(f for f in glob.glob(os.path.join(a.src, "*.docx")) if not os.path.basename(f).startswith("~$")) \
        if os.path.isdir(a.src) else [a.src]
    text = []
    for f in files:
        text += report(f)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(text) + "\n")
    print("\n".join(text))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

# -*- coding: utf-8 -*-
"""Генерация паспортов ПС/РЭ изделий по данным проекта (products.py рядом с этим файлом).

Запуск:  python -P -E build.py <папка_вывода> [ключ_изделия ...]
Шаблон оформления — Шаблон_паспорта_TROYA.docx рядом с этим файлом (обложка с рамками и логотипом, A5,
Times New Roman 11 пт); другой шаблон — переменная TEMPLATE в products.py.
Редакция и дата в колонтитуле — REVISION, REVISION_DATE в products.py (у изделия — ключи rev, rev_date).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common  # noqa: E402
import products  # noqa: E402
from passport_lib import Passport  # noqa: E402

TEMPLATE = getattr(products, "TEMPLATE", os.path.join(HERE, "Шаблон_паспорта_TROYA.docx"))
common.REVISION = getattr(products, "REVISION", common.REVISION)
common.REVISION_DATE = getattr(products, "REVISION_DATE", common.REVISION_DATE)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = sys.argv[1]
    keys = set(sys.argv[2:])
    os.makedirs(out, exist_ok=True)
    for pr in products.ALL:
        if keys and pr["key"] not in keys:
            continue
        rev_date = pr.get("rev_date", common.REVISION_DATE)
        if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", rev_date):
            sys.exit(f"{pr['key']}: дата редакции «{rev_date}» — задайте REVISION_DATE (дд.мм.гггг) в products.py")
        d = Passport(TEMPLATE)
        l1, l2, code = pr["cover"]
        year = rev_date[-4:]
        d.cover(l1, l2, code, year=year, picture=common.img(pr, "cover"))
        common.build(d, pr)
        path = os.path.join(out, pr["file"])
        d.save(path, f"{pr['Name_nom']} {pr['code'].replace('[[', '').replace(']]', '')} ПС/РЭ",
               doc_code=common.doc_code(pr), rev=common.revision(pr), standard=common.standard(pr))
        print("OK", path)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

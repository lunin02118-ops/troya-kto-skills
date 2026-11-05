# -*- coding: utf-8 -*-
"""Заводит папку генератора паспортов: копия движка, шаблона docx, библиотек рисунков и заготовок данных.

  python -P -E new_project.py <папка_проекта>

Папка проекта самодостаточна: выданный паспорт можно пересобрать тем же кодом, даже если навык потом
изменится. Существующие файлы не перезаписываются: при совпадении имени скрипт останавливается.
У владельца ПК папку заводят в <WORK>\\99_Служебное\\Паспорта_<тема>_<ГГГГ-ММ-ДД> (служебный инструмент,
не документ); готовые docx/pdf выводят в рабочий раздел документации.
"""
import os
import shutil
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [  # (источник в навыке, путь в проекте)
    ("scripts/engine/passport_lib.py", "passport_lib.py"),
    ("scripts/engine/common.py", "common.py"),
    ("scripts/engine/build.py", "build.py"),
    ("templates/Шаблон_паспорта_TROYA.docx", "Шаблон_паспорта_TROYA.docx"),
    ("templates/project/products.py", "products.py"),
    ("templates/project/README.md", "README.md"),
    ("scripts/figures/iso.py", "figures/iso.py"),
    ("scripts/figures/sch.py", "figures/sch.py"),
    ("templates/project/figures/fig_01.py", "figures/fig_01.py"),
]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = os.path.abspath(sys.argv[1])
    clash = [dst for _, dst in FILES if os.path.exists(os.path.join(root, dst))]
    if clash:
        sys.exit("Уже есть, не перезаписываю: " + ", ".join(clash))
    for src, dst in FILES:
        target = os.path.join(root, dst)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(os.path.join(SKILL, src), target)
    os.makedirs(os.path.join(root, "figures", "out", "Архив"), exist_ok=True)
    os.makedirs(os.path.join(root, "Архив"), exist_ok=True)
    print("Проект создан:", root)
    print("Дальше: заполнить products.py и figures\\fig_01.py, затем")
    print("  python -P -E figures\\fig_01.py figures\\out")
    print("  python -P -E build.py <папка вывода>")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()

# -*- coding: utf-8 -*-
"""
create_request.py — Создание новой заявки по эталонному стандарту ТОО «TROYA».
Регламент: 'Инструкция по папкам конструкторской заявки' (Ред. 2 от 18.09.2026).
Шаблон: '_Шаблон_заказа'.

Железные правила чистоты (Zero-Duplication & Zero-Extraction):
1. СЗ размещается ТОЛЬКО В КОРНЕ ЗАКАЗА. Копирование в 01_Исходные данные/Документы ЗАПРЕЩЕНО.
2. Извлечение фото/видео/рендеров из СЗ СТРОГО ЗАПРЕЩЕНО.
3. 01_Исходные данные/Документы — только для входящих файлов клиента (ТЗ, сметы, договоры).
"""

import os
import sys
import argparse
import re
import shutil

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_ROOT = r"<СЕТЬ_КО>\_Заявки"
TEMPLATE_NAME = "_Шаблон_заказа"

STANDARD_STRUCTURE = {
    "01_Исходные данные": ["Документы", "Фото и видео"],
    "02_Металл": [
        os.path.join("_Шаблон_изделия", "01_3D"),
        os.path.join("_Шаблон_изделия", "02_PDF"),
        os.path.join("_Шаблон_изделия", "03_ЧПУ", "Лазер_Лист"),
        os.path.join("_Шаблон_изделия", "03_ЧПУ", "Труборез"),
        os.path.join("_Шаблон_изделия", "04_Сопроводительная документация"),
        os.path.join("_Шаблон_изделия", "_Аннулировано"),
    ],
    "03_Корпус": [
        "01_Модели",
        "02_Схемы сборки",
        "03_Раскрой",
        "04_Ведомости",
        "05_Визуализация",
        "_Аннулировано"
    ],
    "04_Войлок": [
        "01_Чертежи",
        "02_ЧПУ",
        "_Аннулировано"
    ]
}

def validate_and_format_name(number, code, obj_name, city):
    num = str(number).strip().replace("/", "-").replace("\\", "-")
    cd = str(code).strip().replace("/", " ").replace("\\", " ") if code else ""
    obj = str(obj_name).strip().replace("/", " ").replace("\\", " ").replace('"', '').replace("'", "")
    ct = str(city).strip().replace("/", " ").replace("\\", " ").replace('"', '').replace("'", "")

    # Очистка спецсимволов: № « » , . ! + #
    for ch in ['№', '«', '»', ',', '.', '!', '+', '#']:
        obj = obj.replace(ch, '')
        ct = ct.replace(ch, '')

    obj = re.sub(r"\s+", " ", obj).strip()
    ct = re.sub(r"\s+", " ", ct).strip()

    if cd:
        folder_name = f"{num}_{cd}_{obj}_{ct}"
    else:
        folder_name = f"{num}_{obj}_{ct}"

    if len(folder_name) > 40:
        print(f"[WARNING] Имя папки длиннее 40 знаков ({len(folder_name)}): '{folder_name}'. Рекомендуется сократить объект.")

    return folder_name

def create_new_request(root_path, folder_name, sz_file=None, dry_run=True):
    root_path = os.path.abspath(root_path)
    if not os.path.isdir(root_path) or os.path.islink(root_path):
        raise FileNotFoundError(f"Exact request root unavailable: {root_path}")
    target_dir = os.path.abspath(os.path.join(root_path, folder_name))
    if os.path.commonpath([root_path, target_dir]) != root_path or os.path.islink(target_dir):
        raise ValueError(f"Target escaped exact root: {target_dir}")
    template_path = os.path.join(root_path, TEMPLATE_NAME)

    print("=" * 80)
    print(f"СОЗДАНИЕ НОВОЙ ЗАЯВКИ: {folder_name}")
    print(f"Путь: {target_dir}")
    print(f"Режим: {'🟡 СУХОЙ ПРОГОН (--dry-run)' if dry_run else '🟢 СОЗДАНИЕ ПАПОК'}")
    print("=" * 80)

    if os.path.lexists(target_dir):
        print(f"[WARNING] Папка {folder_name} уже существует!")
        return False

    if not dry_run:
        if os.path.isfile(template_path) and not os.path.islink(template_path) and os.path.commonpath([root_path, os.path.abspath(template_path)]) == root_path:
            shutil.copytree(template_path, target_dir)
            print(f"Скопирован шаблон из: {template_path}")
        else:
            os.makedirs(target_dir, exist_ok=True)
            for top, subs in STANDARD_STRUCTURE.items():
                top_dir = os.path.join(target_dir, top)
                os.makedirs(top_dir, exist_ok=True)
                for s in subs:
                    os.makedirs(os.path.join(top_dir, s), exist_ok=True)
            print("Развернута эталонная структура папок.")

        # Копирование файла СЗ (СТРОГО В КОРЕНЬ, БЕЗ ДУБЛИРОВАНИЯ И БЕЗ ИЗВЛЕЧЕНИЯ КАРТИНОК)
        if sz_file and os.path.isfile(sz_file) and not os.path.islink(sz_file):
            sz_dest = os.path.join(target_dir, os.path.basename(sz_file))
            shutil.copy2(sz_file, sz_dest)
            print(f"[OK] СЗ сохранена СТРОГО В КОРНЕ: {os.path.basename(sz_file)}")
            print("  (Запрет на дублирование в 'Документы' соблюден: файл не копировался)")
            print("  (Запрет на извлечение медиа соблюден: картинки из СЗ не извлекались)")

        print(f"\n✅ Заявка '{folder_name}' успешно создана по регламенту Ред. 2 от 18.09.2026!")
    else:
        print("\n💡 Для фактического создания выполните команду без флага --dry-run")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Создание новой заявки по эталонной структуре Ред. 2.")
    parser.add_argument("--number", required=True, help="Номер заявки (например: 175, 87-1, 222)")
    parser.add_argument("--code", default="", help="Код источника заказа: Т, Ал, Аст, М (ВЭД убран 15.10.2026)")
    parser.add_argument("--object", required=True, dest="obj", help="Наименование объекта/клиента (например: Гостиница Центр, Офис Север)")
    parser.add_argument("--city", required=True, help="Город (например: Астана, Алматы, Павлодар)")
    parser.add_argument("--sz-file", default=None, help="Путь к файлу официальной СЗ (копируется строго в корень!)")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="Корневой каталог заявок")
    parser.add_argument("--execute", action="store_true", help="Выполнить создание; без флага только dry-run")
    args = parser.parse_args()

    name = validate_and_format_name(args.number, args.code, args.obj, args.city)
    create_new_request(args.root, name, sz_file=args.sz_file, dry_run=not args.execute)




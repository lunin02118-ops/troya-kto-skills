# -*- coding: utf-8 -*-
"""
audit_requests.py — Скрипт инженерного аудита сетевой папки _Заявки.
Проверяет соответствие корпоративному регламенту 'Инструкция по папкам конструкторской заявки'
(Ред. 2 от 18.09.2026 по ТЗ-03 ред. 8 и ТЗ-04) и шаблону '_Шаблон_заказа'.

Ключевые критерии:
1. Корректность наименования: <номер>_<код>_<объект>_<город> (длина <= 40 знаков).
2. Наличие СЗ строго в корне заказа.
3. Отсутствие дубликатов СЗ в 01_Исходные данные/Документы.
4. Отсутствие мусорных файлов (Thumbs.db, Desktop.ini, ~$*.docx, *.tmp).
5. Наличие обязательных эталонных каталогов 01_Исходные данные, 02_Металл, 03_Корпус, 04_Войлок.
"""

import os
import sys
import json
import re
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_ROOT = r"<СЕТЬ_КО>\_Заявки"

STANDARD_FOLDERS_TOP = [
    "01_Исходные данные",
    "02_Металл",
    "03_Корпус",
    "04_Войлок"
]

TEMPLATE_SUBFOLDERS = {
    "01_Исходные данные": ["Документы", "Фото и видео"],
    "02_Металл": ["_Шаблон_изделия"],
    "03_Корпус": ["01_Модели", "02_Схемы сборки", "03_Раскрой", "04_Ведомости", "05_Визуализация"],
    "04_Войлок": ["01_Чертежи", "02_ЧПУ"]
}

JUNK_PATTERNS = [
    r"^Thumbs\.db$",
    r"^\~\$.*",
    r".*\.tmp$",
    r".*\.bak$",
    r"^Desktop\.ini$"
]

def is_junk_file(filename):
    for pat in JUNK_PATTERNS:
        if re.search(pat, filename, re.IGNORECASE):
            return True
    return False

def is_sz_file(filename):
    lower = filename.lower()
    return any(k in lower for k in ["сз", "служебная", "заявка на изготовление"]) and os.path.splitext(lower)[1] in [".docx", ".doc", ".pdf"]

def check_folder_naming(folder_name):
    if folder_name.startswith("_") or "шаблон" in folder_name.lower():
        return True, "Служебная/Шаблон"

    if len(folder_name) > 40:
        return False, f"Имя длиннее 40 знаков ({len(folder_name)} символов)"

    parts = folder_name.split("_")
    if len(parts) < 3:
        return False, f"Имя содержит {len(parts)} блока(ов) вместо требуемых >= 3 через '_'"

    num_part = parts[0].strip()
    if not re.match(r"^[0-9]+(-[0-9]+)?|[0-9]+[а-яА-Яa-zA-Z-]*|[а-яА-Яa-zA-Z]+-?[0-9]+", num_part):
        return False, f"Первый блок '{num_part}' не содержит номера заявки"

    return True, "OK"

def audit_single_request(folder_path):
    folder_name = os.path.basename(folder_path)
    report = {
        "folder": folder_name,
        "valid_name": False,
        "name_reason": "",
        "missing_top_dirs": [],
        "missing_sub_dirs": [],
        "extra_top_dirs": [],
        "junk_files": [],
        "has_sz_in_root": False,
        "has_sz_duplicate_in_docs": False,
        "total_files": 0,
        "total_size_mb": 0.0,
        "status": "PASS"
    }

    # 1. Проверка имени
    val_name, reason = check_folder_naming(folder_name)
    report["valid_name"] = val_name
    report["name_reason"] = reason

    # 2. Проверка структуры папок
    try:
        sub_items = os.listdir(folder_path)
    except Exception as e:
        report["status"] = "ERROR"
        report["name_reason"] = str(e)
        return report

    actual_dirs = [d for d in sub_items if os.path.isdir(os.path.join(folder_path, d))]
    actual_files = [f for f in sub_items if os.path.isfile(os.path.join(folder_path, f))]

    for expected in STANDARD_FOLDERS_TOP:
        if expected not in actual_dirs:
            report["missing_top_dirs"].append(expected)

    for actual in actual_dirs:
        if actual not in STANDARD_FOLDERS_TOP and not actual.startswith("_"):
            report["extra_top_dirs"].append(actual)

    for top, subs in TEMPLATE_SUBFOLDERS.items():
        top_path = os.path.join(folder_path, top)
        if os.path.exists(top_path):
            existing_subs = [d for d in os.listdir(top_path) if os.path.isdir(os.path.join(top_path, d))]
            for s in subs:
                if s not in existing_subs:
                    report["missing_sub_dirs"].append(f"{top}/{s}")

    # 3. Проверка СЗ в корне и дублирования
    for f in actual_files:
        if is_sz_file(f):
            report["has_sz_in_root"] = True

    docs_path = os.path.join(folder_path, "01_Исходные данные", "Документы")
    if os.path.exists(docs_path):
        for df in os.listdir(docs_path):
            if is_sz_file(df):
                report["has_sz_duplicate_in_docs"] = True

    # 4. Обход всех файлов для мусора и статистики
    total_size = 0
    total_files = 0
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not d.startswith("_Карантин") and d != "05_Архив"]
        if "_Карантин" in root or "05_Архив" in root:
            continue
        for f in files:
            total_files += 1
            full_p = os.path.join(root, f)
            try:
                total_size += os.path.getsize(full_p)
            except:
                pass
            if is_junk_file(f):
                rel = os.path.relpath(full_p, folder_path)
                report["junk_files"].append(rel)

    report["total_files"] = total_files
    report["total_size_mb"] = round(total_size / (1024 * 1024), 2)

    # Итоговый статус
    if not report["valid_name"] or report["missing_top_dirs"] or report["junk_files"] or report["has_sz_duplicate_in_docs"]:
        report["status"] = "WARN"
    if not report["has_sz_in_root"]:
        report["status"] = "WARN"

    return report

def run_audit(root_dir=DEFAULT_ROOT):
    print("=" * 80)
    print(f"АУДИТ СЕТЕВОГО ХРАНИЛИЩА ЗАЯВОК ПО РЕГЛАМЕНТУ РЕД. 2 (18.09.2026)")
    print(f"Путь: {root_dir}")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if not os.path.exists(root_dir):
        print(f"[CRITICAL ERROR] Путь {root_dir} недоступен!")
        return

    items = sorted(os.listdir(root_dir))
    request_dirs = [os.path.join(root_dir, i) for i in items if os.path.isdir(os.path.join(root_dir, i))]

    results = []
    pass_cnt = 0
    warn_cnt = 0

    for r_dir in request_dirs:
        bname = os.path.basename(r_dir)
        if bname.startswith("_") or "шаблон" in bname.lower():
            continue
        rep = audit_single_request(r_dir)
        results.append(rep)
        if rep["status"] == "PASS":
            pass_cnt += 1
        else:
            warn_cnt += 1

    print(f"Всего проанализировано заявок: {len(results)}")
    print(f"✅ Полностью соответствуют: {pass_cnt}")
    print(f"⚠️ Требуют внимания/нормализации: {warn_cnt}")
    print("-" * 80)

    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "⚠️"
        print(f"{status_icon} [{r['status']}] {r['folder']}")
        if not r["valid_name"]:
            print(f"    - Некорректное имя: {r['name_reason']}")
        if r["has_sz_duplicate_in_docs"]:
            print(f"    - ⛔ ОБНАРУЖЕН ДУБЛИКАТ СЗ в '01_Исходные данные/Документы'!")
        if not r["has_sz_in_root"]:
            print(f"    - ⚠️ Нет файла СЗ в корне заказа")
        if r["missing_top_dirs"]:
            print(f"    - Отсутствуют базовые папки: {', '.join(r['missing_top_dirs'])}")
        if r["junk_files"]:
            print(f"    - Найдено мусорных файлов: {len(r['junk_files'])} шт.")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    run_audit(path)

# -*- coding: utf-8 -*-
"""
clean_junk.py — Скрипт поиска и безопасной зачистки мусорных файлов:
Thumbs.db, Desktop.ini, временных файлов блокировки (~$*.xlsx, ~$*.docx) и *.tmp.
По умолчанию работает в режиме безопасного отчета (--dry-run).
Для удаления передается флаг --execute.
"""

import os
import sys
import argparse
import re
import hashlib
import shutil

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_ROOT = r"<СЕТЬ_КО>\_Заявки"

JUNK_PATTERNS = [
    r"^Thumbs\.db$",
    r"^\~\$.*",
    r".*\.tmp$",
    r".*\.bak$",
    r"^Desktop\.ini$"
]
PROTECTED_PATTERNS = [r"^\~\$.*", r".*\.bak$"]

def is_junk(name):
    for pat in JUNK_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False

def is_protected(name):
    return any(re.search(pat, name, re.IGNORECASE) for pat in PROTECTED_PATTERNS)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def quarantine_path(root_path, rel_path):
    """Return a non-colliding quarantine path strictly below the requested root."""
    root = os.path.abspath(root_path)
    quarantine = os.path.abspath(os.path.join(root, "05_Архив", "_Карантин_мусор"))
    if os.path.commonpath([root, quarantine]) != root:
        raise ValueError("Карантин должен находиться внутри exact root")
    target = os.path.join(quarantine, rel_path)
    stem, ext = os.path.splitext(target)
    index = 1
    while os.path.exists(target):
        target = f"{stem}__{index}{ext}"
        index += 1
    return target

def assert_regular_within_root(root_path, source_path):
    root = os.path.abspath(root_path)
    source = os.path.abspath(source_path)
    if os.path.islink(source) or not os.path.isfile(source):
        raise OSError(f"Source is not a regular file: {source}")
    if os.path.commonpath([os.path.realpath(root), os.path.realpath(source)]) != os.path.realpath(root):
        raise OSError(f"Source escaped exact root: {source}")
    cursor = os.path.dirname(source)
    while os.path.commonpath([root, cursor]) == root:
        attrs = getattr(os.lstat(cursor), "st_file_attributes", 0)
        if os.path.islink(cursor) or attrs & 0x400:
            raise OSError(f"Reparse/symlink parent rejected: {cursor}")
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent

def assert_path_ancestors(root_path, path):
    root=os.path.abspath(root_path); path=os.path.abspath(path)
    if os.path.commonpath([root,path]) != root: raise OSError(f"Path escaped exact root: {path}")
    cursor=path
    while True:
        if os.path.lexists(cursor):
            attrs=getattr(os.lstat(cursor), "st_file_attributes", 0)
            if os.path.islink(cursor) or attrs & 0x400: raise OSError(f"Reparse path rejected: {cursor}")
        parent=os.path.dirname(cursor)
        if parent==cursor: break
        cursor=parent
def clean_directory(root_path=DEFAULT_ROOT, execute=False):
    assert_path_ancestors(root_path, root_path)
    if not os.path.isdir(root_path) or os.path.islink(root_path):
        raise FileNotFoundError(f"Exact root is unavailable or is a link: {root_path}")

    print("=" * 80)
    print(f"СКАНИРОВАНИЕ НА МУСОРНЫЕ И ВРЕМЕННЫЕ ФАЙЛЫ: {root_path}")
    print(f"Режим: {'🔴 ВЫПОЛНЕНИЕ УДАЛЕНИЯ (--execute)' if execute else '🟡 БЕЗОПАСНЫЙ СУХОЙ ПРОГОН (--dry-run)'}")
    print("=" * 80)

    found = []
    total_size = 0

    scan_errors = []
    quarantine_root = os.path.abspath(os.path.join(root_path, "05_Архив", "_Карантин_мусор"))
    def _onerror(exc):
        scan_errors.append(str(exc))
    for r, dirs, files in os.walk(root_path, onerror=_onerror, followlinks=False):
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(r, d)) and not getattr(os.lstat(os.path.join(r,d)), 'st_file_attributes', 0)&0x400]
        if os.path.abspath(r) == quarantine_root or os.path.abspath(r).startswith(quarantine_root + os.sep):
            continue
        for f in files:
            if is_junk(f):
                full_p = os.path.join(r, f)
                if os.path.islink(full_p):
                    scan_errors.append(f"reparse/symlink skipped: {full_p}")
                    continue
                try:
                    sz = os.path.getsize(full_p)
                except Exception:
                    sz = 0
                rel_p = os.path.relpath(full_p, root_path)
                found.append((full_p, rel_p, sz))
                total_size += sz

    if scan_errors:
        raise OSError("Junk scan failed closed: " + "; ".join(scan_errors))
    if not found:
        print("✅ Мусорных и временных файлов не обнаружено! Каталог чист.")
        return

    print(f"Обнаружено {len(found)} мусорных файлов ({round(total_size / 1024, 1)} КБ):")
    for full_p, rel_p, sz in found:
        print(f"  • {rel_p} ({sz} байт)")

    if execute:
        print("\\nПеремещение в проверяемый карантин внутри exact root...")
        quarantined = 0
        errors = 0
        for full_p, rel_p, sz in found:
            try:
                if is_protected(os.path.basename(full_p)):
                    print(f"  [REVIEW ONLY] active/backup-like file retained: {rel_p}")
                    continue
                assert_regular_within_root(root_path, full_p)
                before = sha256(full_p)
                target = quarantine_path(root_path, rel_p)
                assert_path_ancestors(root_path, target)
                target_parent = os.path.dirname(target)
                cursor = target_parent
                while not os.path.exists(cursor) and os.path.dirname(cursor) != cursor:
                    cursor = os.path.dirname(cursor)
                    if not os.path.exists(cursor):
                        cursor = os.path.dirname(cursor)
                        continue
                    attrs = getattr(os.lstat(cursor), "st_file_attributes", 0)
                    if os.path.islink(cursor) or attrs & 0x400:
                        raise OSError(f"Quarantine destination reparse point: {cursor}")
                    parent_cursor = os.path.dirname(cursor)
                    if parent_cursor == cursor: break
                    cursor = parent_cursor
                if os.path.exists(target):
                    raise FileExistsError(f"Quarantine collision: {target}")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.move(full_p, target)
                after = sha256(target)
                if before != after:
                    raise IOError("SHA-256 изменился после quarantine")
                quarantined += 1
                print(f"  [QUARANTINED] {rel_p} -> {os.path.relpath(target, root_path)} [{after}]")
            except Exception as e:
                print(f"  [ERROR] Не удалось проверить/переместить {rel_p}: {e}")
                errors += 1
        print(f"\\nИтог: В карантин перемещено {quarantined} файлов. Ошибок: {errors}")
        if errors:
            raise RuntimeError(f'Quarantine incomplete: {errors} errors; inspect retained files and quarantine')
    else:
        print("\\n💡 Для карантина с SHA-256 запустите: python clean_junk.py --execute")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Поиск и очистка временных и мусорных файлов.")
    parser.add_argument("--path", default=DEFAULT_ROOT, help="Путь к сетевой папке")
    parser.add_argument("--execute", action="store_true", help="Выполнить фактическое удаление")
    args = parser.parse_args()
    if args.execute and args.path == DEFAULT_ROOT:
        parser.error("--path is required with --execute")
    clean_directory(args.path, execute=args.execute)








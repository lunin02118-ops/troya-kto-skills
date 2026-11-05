"""Conservative SolidWorks assembly organizer with fail-closed link repair."""
import hashlib
import json
import os
import shutil
import time
import uuid

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PACKAGE_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
_SW_CANDIDATES = [
    os.environ.get("SW_AUTOMATION_DIR"),
    os.path.join(_PACKAGE_ROOT, "solidworks-automation"),
    r"<WORK>\99_Служебное\Навыки_агентов\01_Конструктору_CAD\solidworks-automation",
]
SW_SKILL_DIR = next((p for p in _SW_CANDIDATES if p and os.path.isdir(p)), None)
if not SW_SKILL_DIR:
    raise ImportError("SolidWorks automation dependency unavailable; set SW_AUTOMATION_DIR")
if SW_SKILL_DIR not in os.sys.path:
    os.sys.path.insert(0, SW_SKILL_DIR)
if os.path.join(SW_SKILL_DIR, "scripts") not in os.sys.path:
    os.sys.path.insert(0, os.path.join(SW_SKILL_DIR, "scripts"))

from scripts.sw_connect import connect_solidworks, open_document, save_document, get_com_member

CAD_EXTENSIONS = {".sldasm", ".sldprt", ".slddrw"}
TEMP_EXTENSIONS = {".tmp"}
REPARSE_POINT = 0x400


def _is_reparse_or_link(path):
    cur = os.path.abspath(path)
    while True:
        try:
            st = os.lstat(cur)
            if os.path.islink(cur) or (getattr(st, "st_file_attributes", 0) & REPARSE_POINT):
                return True
        except FileNotFoundError:
            pass
        parent = os.path.dirname(cur)
        if parent == cur:
            return False
        cur = parent


def _inside(path, root):
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]).casefold() == os.path.realpath(root).casefold()
    except ValueError:
        return False


def purge_junk_files(root_dir: str):
    """Return exact temporary candidates only; never delete exchange/backups."""
    return [os.path.join(root, name) for root, _, files in os.walk(root_dir) for name in files
            if os.path.splitext(name)[1].lower() in TEMP_EXTENSIONS or name.startswith("~$")]


def _open_doc(sw, path):
    try:
        method = getattr(sw, "GetOpenDocumentByName")
        return method(os.path.abspath(path))
    except Exception as exc:
        raise RuntimeError(f"Не удалось установить ownership state для {path}: {exc}") from exc


def _dependency_paths(doc):
    raw = get_com_member(doc, "GetDependencies2", True, False, False)
    if raw is None:
        raise RuntimeError("GetDependencies2 не вернул данные")
    values = list(raw) if isinstance(raw, (list, tuple)) else [raw]
    if len(values) % 2:
        raise RuntimeError(f"GetDependencies2 вернул нечётное число элементов: {len(values)}")
    paths = []
    for i in range(0, len(values), 2):
        if not values[i] or not values[i + 1]:
            raise RuntimeError(f"GetDependencies2 содержит неполную пару на позиции {i}")
        paths.append(os.path.normcase(os.path.abspath(str(values[i + 1]))))
    return paths


def _component_states(doc):
    components = get_com_member(doc, "GetComponents", False)
    if components is None:
        raise RuntimeError("GetComponents не вернул данные")
    result = {}
    if not isinstance(components, (list, tuple)):
        raise RuntimeError("GetComponents вернул неожиданный тип")
    for comp in components:
        path = get_com_member(comp, "GetPathName")
        state = get_com_member(comp, "GetSuppression2")
        if not path:
            raise RuntimeError("Компонент без пути")
        if state not in (0, 1, 2, 3, 4):
            raise RuntimeError(f"Недопустимое состояние компонента {path}: {state}")
        result[os.path.normcase(os.path.abspath(path))] = state
    return result


def _verify_references(doc, asm_path, baseline_states, old_to_new):
    paths = _dependency_paths(doc)
    missing = [path for path in paths if not os.path.exists(path)]
    if missing:
        raise RuntimeError(f"Отсутствуют зависимости {asm_path}: {missing[:5]}")
    after = _component_states(doc)
    norm_map = {os.path.normcase(os.path.abspath(old)): os.path.normcase(os.path.abspath(new))
                for old, new in old_to_new.items()}
    expected = {norm_map.get(os.path.normcase(os.path.abspath(old)), os.path.normcase(os.path.abspath(old))): state
                for old, state in baseline_states.items()}
    if set(after) != set(expected):
        raise RuntimeError(f"Набор компонентов изменился: expected={sorted(expected)}, actual={sorted(after)}")
    for path, state in after.items():
        if state == 5:
            raise RuntimeError(f"Несогласованное состояние компонента: {path}")
        if state == 0 and expected.get(path) != 0:
            raise RuntimeError(f"Новый подавленный компонент: {path}")
        if path in expected and state != expected[path]:
            raise RuntimeError(f"Изменилось состояние компонента {path}: {expected[path]} -> {state}")


def _preflight(assembly_dir, all_files, path_map):
    root = os.path.abspath(assembly_dir)
    if _is_reparse_or_link(root):
        raise RuntimeError(f"Корень сборки или его предок является reparse/link: {root}")
    destinations = set()
    for old, new in path_map.items():
        if not _inside(old, root) or not _inside(new, root):
            raise RuntimeError(f"Путь вне корня сборки: {old} -> {new}")
        if _is_reparse_or_link(old) or _is_reparse_or_link(os.path.dirname(new)):
            raise RuntimeError(f"Reparse/link в пути перемещения: {old} -> {new}")
        key = os.path.normcase(os.path.abspath(new))
        if key in destinations or os.path.exists(new):
            raise RuntimeError(f"Коллизия назначения до начала операции: {new}")
        destinations.add(key)
    for path in all_files:
        if _is_reparse_or_link(path):
            raise RuntimeError(f"Исходный CAD-файл находится под reparse/link: {path}")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup_files(paths, backup_dir):
    os.makedirs(backup_dir, exist_ok=False)
    manifest = {}
    for path in paths:
        dst = os.path.join(backup_dir, os.path.basename(path))
        shutil.copy2(path, dst)
        expected = _sha256(path)
        if _sha256(dst) != expected:
            raise RuntimeError(f"Backup checksum mismatch: {path}")
        manifest[path] = {"backup": dst, "sha256": expected}
    with open(os.path.join(backup_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def organize_folder(assembly_dir: str, subassembly_map: dict = None):
    if not os.path.isdir(assembly_dir):
        raise FileNotFoundError(f"Папка не найдена: {assembly_dir}")
    root = os.path.abspath(assembly_dir)
    all_files = [os.path.join(root, f) for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]
    main_asms = [f for f in all_files if f.lower().endswith(".sldasm")]
    if not main_asms:
        raise RuntimeError("Главная сборка .SLDASM не найдена; операция остановлена")
    if subassembly_map is None:
        subassembly_map = {"Стандартные изделия и фурнитура": ["винт", "саморез", "гайка", "шайба", "заклепка", "опора", "заглушка", "стяжк", "крючок", "din", "iso", "гост"], "ЛДСП": ["столешниц", "царг", "stl", "canomad", "щит", "полка", "экран"]}
    path_map = {}
    for target_folder, patterns in subassembly_map.items():
        for path in list(all_files):
            if path in main_asms or not os.path.isfile(path):
                continue
            if any(p.lower() in os.path.basename(path).lower() for p in patterns):
                path_map[path] = os.path.join(root, target_folder, os.path.basename(path))
                all_files.remove(path)
    _preflight(root, all_files + list(path_map), path_map)
    backup_dir = os.path.join(os.path.dirname(root), f"{os.path.basename(root)}.organize-backup-{uuid.uuid4().hex}")
    assembly_backups = _backup_files(main_asms, backup_dir)
    moved, opened_by_us = [], []
    sw = None
    baselines = {}
    try:
        sw_info = connect_solidworks(visible=True, return_metadata=True)
        sw = sw_info[0] if isinstance(sw_info, tuple) else sw_info
        for path in all_files + list(path_map):
            if path.lower().endswith(tuple(CAD_EXTENSIONS)) and _open_doc(sw, path) is not None:
                raise RuntimeError(f"Входной документ уже открыт в SolidWorks: {path}")
        # Baseline is captured before moving anything; only assemblies that contain old paths are rewritten.
        for asm_path in main_asms:
            doc = open_document(sw, asm_path, raise_on_error=True)
            opened_by_us.append(doc)
            baselines[asm_path] = (_dependency_paths(doc), _component_states(doc))
            sw.CloseDoc(get_com_member(doc, "GetTitle"))
            opened_by_us.remove(doc)
        moved_map = {
            old: new for old, new in path_map.items()
            if any(os.path.normcase(os.path.abspath(dep)) == os.path.normcase(os.path.abspath(old))
                   for deps, _ in baselines.values() for dep in deps)
        }
        for old, new in path_map.items():
            if old not in moved_map:
                continue
            os.makedirs(os.path.dirname(new), exist_ok=True)
            shutil.move(old, new)
            moved.append((old, new))
        results = []
        for asm_path in main_asms:
            deps, states = baselines[asm_path]
            actual = {old: new for old, new in moved_map.items() if any(os.path.normcase(os.path.abspath(d)) == os.path.normcase(os.path.abspath(old)) for d in deps)}
            if not actual:
                continue
            for old, new in actual.items():
                result = sw.ReplaceReferencedDocument(asm_path, old, new)
                if result in (False, None, 0):
                    raise RuntimeError(f"ReplaceReferencedDocument не подтверждён: {asm_path}: {old} -> {new}")
                results.append((asm_path, old, new, result))
            doc = open_document(sw, asm_path, raise_on_error=True)
            opened_by_us.append(doc)
            rebuild = get_com_member(doc, "EditRebuild3")
            if rebuild in (False, None, 0):
                raise RuntimeError(f"Перестроение сборки не подтверждено: {asm_path}")
            _verify_references(doc, asm_path, states, actual)
            if not save_document(doc):
                raise RuntimeError(f"Сохранение сборки не подтверждено: {asm_path}")
            sw.CloseDoc(get_com_member(doc, "GetTitle"))
            opened_by_us.remove(doc)
            reopened = open_document(sw, asm_path, raise_on_error=True)
            opened_by_us.append(reopened)
            if get_com_member(reopened, "EditRebuild3") in (False, None, 0):
                raise RuntimeError(f"Повторное перестроение сборки не подтверждено: {asm_path}")
            _verify_references(reopened, asm_path, states, actual)
        print(f"[Done] Связи сохранены и проверены: replacements={len(results)}, assemblies={len(main_asms)}")
    except Exception:
        restore_errors = []
        # Release only documents opened by this operation before restoring their files.
        for doc in list(reversed(opened_by_us)):
            try:
                sw.CloseDoc(get_com_member(doc, "GetTitle"))
                opened_by_us.remove(doc)
            except Exception as close_exc:
                restore_errors.append(f"close before rollback: {close_exc}")
        for path, record in assembly_backups.items():
            try:
                shutil.copy2(record["backup"], path)
                if _sha256(path) != record["sha256"]:
                    restore_errors.append(f"checksum: {path}")
            except Exception as restore_exc:
                restore_errors.append(f"bytes {path}: {restore_exc}")
        for old, new in reversed(moved):
            try:
                if os.path.exists(new) and not os.path.exists(old):
                    os.makedirs(os.path.dirname(old), exist_ok=True)
                    shutil.move(new, old)
                if not os.path.exists(old):
                    restore_errors.append(f"path: {old}")
            except Exception as restore_exc:
                restore_errors.append(f"path {old}: {restore_exc}")
        if restore_errors:
            raise RuntimeError("Rollback completed with errors: " + "; ".join(restore_errors))
        raise
    finally:
        for doc in reversed(opened_by_us):
            try:
                sw.CloseDoc(get_com_member(doc, "GetTitle"))
            except Exception:
                pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        sys.exit("Укажите папку изделия: python organize_assembly.py <папка>")
    organize_folder(sys.argv[1])

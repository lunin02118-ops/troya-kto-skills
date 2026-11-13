# -*- coding: utf-8 -*-
"""
cad_material_inspector.py
Инженерный геометрический анализатор деталей для SolidWorks и КОМПАС-3D.
Только проверка (ничего не записывает). Выполняет физический анализ 3D-модели (дерево фич, твердые тела, BoundingBox,
толщина стенки, коэффициент заполнения, радиусы) через MCP и COM API.

СТРОГИЙ РЕГЛАМЕНТ:
Назначение материалов производится ИСКЛЮЧИТЕЛЬНО на основе анализа самой геометрии детали.
Назначение по наивным строкам, именам файлов или тексту заявок СТРОГО ЗАПРЕЩЕНО!
"""

import os
import sys
import math
import json
import shutil
import time
import pythoncom
import win32com.client
from typing import Dict, Any, List, Optional, Tuple

sys.stdout.reconfigure(encoding="utf-8")

# Стандартные пути к библиотекам
DEFAULT_GOST_MAT_DB = r"<СЕТЬ_КО>\_Библиотека проектирования\_инструменты_конструктора\04_Библиотеки_Материалов_и_Профилей\Библиотека материалов\Библиотека_Материалов_ГОСТ.sldmat"
ALT_GOST_MAT_DB = r"<WORK>\05_Развитие_КТО\01_Программы_КТО\ESKD-AUTO\04_Библиотеки_Материалов_и_Профилей\Библиотека материалов\Библиотека_Материалов_ГОСТ.sldmat"

# Библиотека в инструментарии конструктора на сервере (есть у всех конструкторов)
NAS_GOST_MAT_DB = r"<СЕТЬ_КО>\_Библиотека проектирования\_инструменты_конструктора\04_Библиотеки_Материалов_и_Профилей\Библиотека материалов\Библиотека_Материалов_ГОСТ.sldmat"

def get_material_db_path() -> str:
    if os.path.exists(DEFAULT_GOST_MAT_DB):
        return DEFAULT_GOST_MAT_DB
    if os.path.exists(ALT_GOST_MAT_DB):
        return ALT_GOST_MAT_DB
    if os.path.exists(NAS_GOST_MAT_DB):
        return NAS_GOST_MAT_DB
    return DEFAULT_GOST_MAT_DB

# Таблица стандартных толщин листового проката ТРОЯ / ГОСТ
STANDARD_SHEET_THICKNESSES = [
    (0.8, "Лист 0,8 ГОСТ 19904-90 / 08пс ГОСТ 16523-97"),
    (0.95, "Лист оцинкованный 0,95 ГОСТ 14918-80 / 08пс"),
    (1.0, "Лист 1,0 ГОСТ 19904-90 / 08кп ГОСТ 16523-97"),
    (1.2, "Лист 1,2 ГОСТ 19904-90 / 08пс ГОСТ 16523-97"),
    (2.0, "Лист 2,0 ГОСТ 19904-90 / 08пс ГОСТ 16523-97"),
    (2.5, "Лист 2,5 ГОСТ 19903-2015 / Ст3сп ГОСТ 14637-89"),
    (3.0, "Лист 3,0 ГОСТ 19903-2015 / Ст3сп ГОСТ 14637-89"),
    (4.0, "Лист 4,0 ГОСТ 19903-2015 / Ст3сп ГОСТ 14637-89"),
    (6.0, "Лист 6,0 ГОСТ 19903-2015 / 09Г2С ГОСТ 19281-2014"),
    (8.0, "Лист 8,0 ГОСТ 19903-2015 / Ст3сп ГОСТ 14637-89"),
    (10.0, "Лист 10,0 ГОСТ 19903-2015 / Ст3сп ГОСТ 14637-89"),
]

# Таблица стандартных профильных труб ТРОЯ / ГОСТ
STANDARD_RECT_TUBES = {
    (40, 20, 1.2): "Труба 40х20х1,2 ГОСТ 8645-68 / 08пс ГОСТ 13663-86",
    (40, 20, 1.5): "Труба 40х20х1,5 ГОСТ 8645-68 / 08пс ГОСТ 13663-86",
    (40, 20, 2.0): "Труба 40х20х2,0 ГОСТ 8645-68 / Ст3сп ГОСТ 13663-86",
    (50, 25, 1.2): "Труба ПО 50х25х1,2 ГОСТ 8644-68 / 08пс ГОСТ 13663-86",
    (50, 25, 1.5): "Труба ПО 50х25х1,5 ГОСТ 8644-68 / 08пс ГОСТ 13663-86",
    (50, 25, 2.0): "Труба 50х25х2,0 ГОСТ 8645-68 / Ст3сп ГОСТ 13663-86",
    (60, 15, 1.5): "Труба 60х15х1,5 ГОСТ 8645-68 / 08пс ГОСТ 13663-86",
    (60, 30, 1.5): "Труба 60х30х1,5 ГОСТ 8645-68 / 08пс ГОСТ 13663-86",
    (60, 40, 3.0): "Труба 60х40х3,0 ГОСТ 8645-68 / Ст3сп ГОСТ 13663-86",
    (70, 20, 1.5): "Труба 70х20х1,5 ГОСТ 8645-68 / 08пс ГОСТ 13663-86",
}

STANDARD_SQUARE_TUBES = {
    (20, 20, 1.2): "Труба 20х20х1,2 ГОСТ 8639-82 / 08пс ГОСТ 13663-86",
    (20, 20, 1.5): "Труба 20х20х1,5 ГОСТ 8639-82 / Ст3сп ГОСТ 13663-86",
    (25, 25, 1.5): "Труба 25х25х1,5 ГОСТ 8639-82 / Ст3сп ГОСТ 13663-86",
    (30, 30, 1.5): "Труба 30х30х1,5 ГОСТ 8639-82 / 08пс ГОСТ 13663-86",
    (40, 40, 1.5): "Труба 40х40х1,5 ГОСТ 8639-82 / 08пс ГОСТ 13663-86",
    (40, 40, 2.0): "Труба 40х40х2,0 ГОСТ 8639-82 / Ст3сп ГОСТ 13663-86",
    (50, 50, 2.0): "Труба 50х50х2,0 ГОСТ 8639-82 / Ст3сп ГОСТ 13663-86",
    (60, 60, 2.0): "Труба 60х60х2,0 ГОСТ 8639-82 / Ст3сп ГОСТ 13663-86",
    (80, 80, 4.0): "Труба 80х80х4,0 ГОСТ 8639-82 / В 10 ГОСТ 13663-86",
}

STANDARD_ROUND_TUBES = {
    (16, 1.5): "Труба 16х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (20, 1.5): "Труба 20х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (22, 1.5): "Труба 22х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (25, 1.5): "Труба 25х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (28, 1.5): "Труба 28х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (32, 1.5): "Труба 32х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (50, 1.5): "Труба 50х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
    (60, 1.5): "Труба 60х1,5 ГОСТ 10704-91 / 08пс ГОСТ 10705-80",
}

class GeometryProbeResult:
    def __init__(self):
        self.doc_path = ""
        self.doc_name = ""
        self.category = ""          # sheet_metal, rect_tube, square_tube, round_tube, ldsp, hardware, solid
        self.detected_material = ""
        self.bounding_box_mm = (0.0, 0.0, 0.0) # (min_dim, mid_dim, max_dim)
        self.volume_cm3 = 0.0
        self.sheet_thickness_mm = 0.0
        self.wall_thickness_mm = 0.0
        self.section_width_mm = 0.0
        self.section_height_mm = 0.0
        self.filling_ratio = 1.0
        self.feature_types = []
        self.evidence = ""
        self.body_count = 0

def probe_part_geometry(doc) -> GeometryProbeResult:
    """Анализирует геометрию детали в SolidWorks и определяет ее тип и материал."""
    res = GeometryProbeResult()
    res.doc_path = doc.GetPathName
    res.doc_name = os.path.basename(res.doc_path)

    # Multi-body status is evidence, not a filename/category guess.
    try:
        # SolidWorks IPartDoc.GetBodies2(swSolidBody=0) returns visible bodies.
        bodies = doc.GetBodies2(0, False)
        res.body_count = len(bodies or [])
    except Exception:
        res.body_count = 0
    
    # 1. Извлечение массово-инерционных характеристик
    mp = doc.GetMassProperties
    vol_m3 = mp[3] if mp else 0.0
    vol_mm3 = vol_m3 * 1e9
    res.volume_cm3 = vol_mm3 / 1000.0
    
    # 2. Габариты детали (Bounding Box)
    box = doc.GetPartBox(True)
    if box:
        dx = abs(box[3] - box[0]) * 1000.0
        dy = abs(box[4] - box[1]) * 1000.0
        dz = abs(box[5] - box[2]) * 1000.0
        dims = sorted([dx, dy, dz])
        res.bounding_box_mm = (round(dims[0], 2), round(dims[1], 2), round(dims[2], 2))
    else:
        dims = [0.0, 0.0, 0.0]
        
    d_min, d_mid, d_max = dims[0], dims[1], dims[2]
    
    # 3. Инспекция дерева элементов (Feature Tree)
    feat = doc.FirstFeature
    is_sheet_metal = False
    sheet_thickness = 0.0
    
    while feat:
        ft = feat.GetTypeName2
        res.feature_types.append(ft)
        
        if ft in ['SheetMetal', 'SMBaseFlange']:
            is_sheet_metal = True
            sm_data = feat.GetDefinition
            if sm_data:
                try:
                    th = sm_data.Thickness * 1000.0
                    if th > 0.05:
                        sheet_thickness = th
                except Exception:
                    pass
        feat = feat.GetNextFeature
        
    # --- КРИТЕРИЙ 1: ЛИСТОВОЙ МЕТАЛЛ (SHEET METAL) ---
    if is_sheet_metal or (d_min <= 3.5 and 'FlatPattern' in res.feature_types):
        res.category = "sheet_metal"
        if sheet_thickness <= 0.05:
            sheet_thickness = d_min
        res.sheet_thickness_mm = round(sheet_thickness, 2)
        
        # Подбор по таблице толщин
        best_diff = 999.0
        best_mat = STANDARD_SHEET_THICKNESSES[0][1]
        for std_th, mat_name in STANDARD_SHEET_THICKNESSES:
            diff = abs(std_th - res.sheet_thickness_mm)
            if diff < best_diff:
                best_diff = diff
                best_mat = mat_name
                
        res.detected_material = best_mat
        res.evidence = f"Дерево содержит фичи SheetMetal/FlatPattern; фактическая толщина листа s={res.sheet_thickness_mm} мм"
        return res

    # --- КРИТЕРИЙ 2: ДЛИННОМЕРНЫЕ ПОЛЫЕ ПРОФИЛИ (ТРУБЫ) ---
    length = d_max
    w1, w2 = d_min, d_mid
    outer_area = w1 * w2
    cross_metal_area = (vol_mm3 / length) if length > 0 else 0.0
    filling_ratio = (cross_metal_area / outer_area) if outer_area > 0 else 1.0
    res.filling_ratio = round(filling_ratio, 3)
    
    # Проверка на полую трубу (коэффициент заполнения < 0.55 и поперечные размеры > 8 мм)
    if filling_ratio < 0.55 and w1 >= 8.0 and length > 2.0 * w2:
        # Расчет расчетной толщины стенки трубы:
        # 4*t^2 - 2*(w1+w2)*t + cross_metal_area = 0
        A_p = 4.0
        B_p = -2.0 * (w1 + w2)
        C_p = cross_metal_area
        disc = B_p**2 - 4.0 * A_p * C_p
        t_calc = (-B_p - math.sqrt(max(0.0, disc))) / (2.0 * A_p) if disc >= 0 else 1.5
        res.wall_thickness_mm = round(t_calc, 2)
        
        # Стандартизация стенки
        std_walls = [1.2, 1.5, 2.0, 3.0, 4.0]
        wall_std = min(std_walls, key=lambda x: abs(x - t_calc))
        
        # Определение типа сечения: круглая / квадратная / прямоугольная
        if abs(w1 - w2) < 2.0:
            # Квадратная труба
            size_std = round(w1 / 5.0) * 5
            res.section_width_mm = size_std
            res.section_height_mm = size_std
            res.category = "square_tube"
            key = (size_std, size_std, wall_std)
            if key in STANDARD_SQUARE_TUBES:
                res.detected_material = STANDARD_SQUARE_TUBES[key]
            else:
                res.detected_material = f"Труба {size_std}х{size_std}х{wall_std} ГОСТ 8639-82 / 08пс ГОСТ 13663-86"
            res.evidence = f"Полый профиль квадратного сечения {size_std}x{size_std} со стенкой {wall_std} мм (коэф. заполнения {filling_ratio*100:.1f}%)"
            return res
        else:
            # Прямоугольная труба
            w_std = round(w2 / 5.0) * 5
            h_std = round(w1 / 5.0) * 5
            res.section_width_mm = w_std
            res.section_height_mm = h_std
            res.category = "rect_tube"
            key = (w_std, h_std, wall_std)
            if key in STANDARD_RECT_TUBES:
                res.detected_material = STANDARD_RECT_TUBES[key]
            else:
                res.detected_material = f"Труба {w_std}х{h_std}х{wall_std} ГОСТ 8645-68 / 08пс ГОСТ 13663-86"
            res.evidence = f"Полый прямоугольный профиль {w_std}x{h_std} со стенкой {wall_std} мм (коэф. заполнения {filling_ratio*100:.1f}%)"
            return res

    # --- КРИТЕРИЙ 3: МЕБЕЛЬНЫЕ ПЛИТЫ (ЛДСП / ФАНЕРА / МДФ) ---
    # Сплошная плоская плита без гибов, толщина 16 мм, площадь более 0.05 м2
    sheet_like = any(ft in {'SheetMetal', 'SMBaseFlange', 'EdgeFlange', 'FlatPattern'}
                     for ft in res.feature_types)
    area_m2 = (d_mid * d_max) / 1_000_000.0
    is_flat = d_min > 0 and (d_mid / d_min >= 4.0) and (d_max / d_min >= 4.0)
    if (not sheet_like and res.body_count == 1 and filling_ratio > 0.7 and
            abs(d_min - 16.0) <= 1.0 and area_m2 > 0.05 and is_flat):
        res.category = "ldsp"
        res.sheet_thickness_mm = 16.0
        res.detected_material = "ЛДСП 16 мм ГОСТ 32289-2013 / ГОСТ 10632-2014"
        res.evidence = f"Сплошной плоский мебельный щит габаритами {d_max:.0f}x{d_mid:.0f} мм и толщиной {d_min:.1f} мм"
        return res
        
    # --- КРИТЕРИЙ 4: ПЛАСТИК / ФУРНИТУРА / ЗАГЛУШКИ (ТОЛЬКО МАЛЫЕ ПОКУПНЫЕ ЭЛЕМЕНТЫ) ---
    # Feature names such as Plastic/Mold/Draft are not material proof. Without
    # an explicit body/appearance/material evidence source, remain unresolved.

    # --- КРИТЕРИЙ 5: ОБЩИЙ СТАЛЬНОЙ ПРОКАТ (МНОГОТЕЛЬНЫЕ КАРКАСЫ ИЛИ СТАЛЬ) ---
    res.category = "unresolved"
    res.detected_material = ""
    res.evidence = (f"Материал не установлен по геометрии; требуется инженерная проверка "
                    f"(габариты {d_min:.1f}x{d_mid:.1f}x{d_max:.1f} мм, тел: {res.body_count})")
    return res

SKIP_DIRS = {"_Аннулировано", "_Прежние_выпуски", "Архив", "_Архив", "_Карантин"}


def current_material(doc) -> str:
    """Материал активной конфигурации — только чтение."""
    try:
        cfg = doc.ConfigurationManager.ActiveConfiguration.Name
        db = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "")
        observed = doc.GetMaterialPropertyName2(cfg, db)
        if isinstance(observed, (tuple, list)):
            observed = observed[0] if observed else ""
        return str(observed or "")
    except Exception:
        return ""


def analyze_directory(root_dir: str):
    """Только проверка: геометрия каждой детали папки и сравнение с назначенным материалом. Ничего не записывает.

    Назначает материал конструктор надстройкой ЕСКД (AGENT_GUIDE ESKD-AUTO, п.1). Спорное — решает конструктор (п.6).
    """
    print("=" * 80)
    print("ПРОВЕРКА МАТЕРИАЛОВ ПО ГЕОМЕТРИИ (только чтение)")
    print(f"Папка: {root_dir}")
    print(f"База материалов для сверки: {get_material_db_path()}")
    print("=" * 80)
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        sys.exit("SolidWorks не запущен. Откройте его и повторите: второй экземпляр скрипт не запускает.")

    vErrors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    vWarnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    parts = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        parts += [os.path.join(root, f) for f in files if f.upper().endswith(".SLDPRT") and not f.startswith("~$")]

    differ, unresolved, failures = [], [], []
    for p in sorted(parts):
        opened_here = False
        try:
            doc = sw.GetOpenDocumentByName(os.path.abspath(p))
        except Exception:
            doc = None
        if doc is None:
            doc = sw.OpenDoc6(p, 1, 1 | 2, "", vErrors, vWarnings)   # тихо, только чтение
            opened_here = bool(doc)
        if not doc:
            failures.append((p, "не открылась"))
            continue
        try:
            res = probe_part_geometry(doc)
            now = current_material(doc)
        finally:
            if opened_here:
                sw.CloseDoc(p)
        print(f"\n🔬 {res.doc_name}")
        print(f"   Габариты: {res.bounding_box_mm[0]} x {res.bounding_box_mm[1]} x {res.bounding_box_mm[2]} мм | V={res.volume_cm3:.1f} см³")
        print(f"   По геометрии: {res.detected_material or 'не установлен — нужна проверка конструктора'} ({res.evidence})")
        print(f"   Назначено в модели: {now or '—'}")
        if not res.detected_material:
            unresolved.append(p)
        elif res.detected_material != now:
            differ.append((p, now, res.detected_material))

    print("\n" + "=" * 80)
    print(f"Деталей: {len(parts)}; расходится с геометрией: {len(differ)}; не установлено: {len(unresolved)}; не открылось: {len(failures)}")
    for p, now, geo in differ:
        print(f"   РАСХОЖДЕНИЕ: {p}\n      в модели: {now or '—'}\n      по геометрии: {geo}")
    for p, reason in failures:
        print(f"   ОШИБКА: {p} — {reason}")
    print("Исправляет конструктор надстройкой ЕСКД. Скрипт ничего не менял.")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Укажите папку с моделями: python cad_material_inspector.py \"<папка>\"")
    analyze_directory(sys.argv[1])

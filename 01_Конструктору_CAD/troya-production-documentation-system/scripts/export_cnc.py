#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль экспорта файлов ЧПУ ТОО «Компания TROYA».
Реализует строгие инженерные регламенты:
1. Листовой металл -> формат DXF (1:1 ЧИСТЫЙ КОНТУР РЕЗА для листового лазера).
   - В DXF выгружается ТОЛЬКО внешний контур и внутренние отверстия детали на слое '0'.
   - Категорически запрещено наличие рамок чертежа, штампов, размеров, надписей и таблиц.
   - Стандарт наименования файла: {Обозначение} {Наименование}_{Толщина}мм_{Ширина}х{Длина}.dxf
     Пример: 85T.СМ.01.004 Заглушка_2.0мм_23х48.dxf
2. Трубный прокат -> формат IGS для лазерного трубореза.
3. Исключение для гибки: трубы, подлежащие гибке (дуги, кольца, рамы),
   ЗАПРЕЩЕНО выкладывать в IGS (требуют технологический припуск на захват дорна; нарезаются на пиле по заявке).
"""

import os
import sys
import glob
import math
import shutil
from typing import List, Tuple, Optional
import win32com.client
import ezdxf

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


class CncExporter:
    def __init__(self, order_root: str):
        self.root = os.path.abspath(order_root)
        if not os.path.isdir(self.root):
            raise FileNotFoundError(f"CNC path binding preflight failed: {self.root}")
        self.models_dir = os.path.join(self.root, "01 3D-Модели")
        self.cnc_laser_dir = os.path.join(self.root, r"03 ЧПУ и Раскрой\Лазер_Лист")
        self.cnc_tube_dir = os.path.join(self.root, r"03 ЧПУ и Раскрой\Труборез")

        os.makedirs(self.cnc_laser_dir, exist_ok=True)
        os.makedirs(self.cnc_tube_dir, exist_ok=True)

        # Защита от дублирования: старое дерево не удаляется, а уходит в карантин.
        legacy_drw_dxf = os.path.join(self.root, r"02 Чертежи\DXF")
        if os.path.exists(legacy_drw_dxf):
            self._quarantine(legacy_drw_dxf)
            print(f"[QUARANTINE] Legacy DXF tree: {legacy_drw_dxf}")

    def _quarantine(self, path):
        source = os.path.abspath(path)
        root = self.root
        if os.path.commonpath([root, source]) != root:
            raise ValueError("Quarantine source is outside exact order root")
        qroot = os.path.join(root, "_Карантин_перед_экспортом")
        os.makedirs(qroot, exist_ok=True)
        target = os.path.join(qroot, os.path.basename(source))
        index = 1
        while os.path.exists(target):
            target = os.path.join(qroot, f"{os.path.basename(source)}__{index}")
            index += 1
        shutil.move(source, target)
        if not os.path.exists(target):
            raise IOError(f"Quarantine verification failed: {source}")
        return target

    def clean_legacy_dxf_duplicates(self):
        """Перемещает из 02 Чертежи папку DXF в проверяемый карантин."""
        legacy_drw_dxf = os.path.join(self.root, r"02 Чертежи\DXF")
        if os.path.exists(legacy_drw_dxf):
            self._quarantine(legacy_drw_dxf)

    def export_sheet_metal_to_dxf(self, prt_rel_or_abs_path: str, name_override: Optional[str] = None) -> Optional[str]:
        """
        Экспортирует деталь из листового металла в чистый 1:1 DXF контур для лазерной резки.
        Формирует имя по стандарту: {Обозначение} {Наименование}_{Толщина}мм_{Ширина}х{Длина}.dxf
        """
        full_prt = prt_rel_or_abs_path if os.path.isabs(prt_rel_or_abs_path) else os.path.join(self.root, prt_rel_or_abs_path)
        if not os.path.exists(full_prt):
            print(f"[ERROR] Файл 3D-модели не найден: {full_prt}")
            return None

        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = False
        errors = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_I4, 0)

        doc = sw.OpenDoc6(full_prt, 1, 1, "", errors, warnings)
        if not doc:
            print(f"[ERROR] Не удалось открыть 3D-модель: {full_prt}")
            return None

        try:
            # 1. Определение габаритов и толщины по Bounding Box модели
            box = doc.GetPartBox(True)
            dx = abs(box[3] - box[0]) * 1000.0
            dy = abs(box[4] - box[1]) * 1000.0
            dz = abs(box[5] - box[2]) * 1000.0
            dims = sorted([dx, dy, dz])
            thickness = round(dims[0], 1)
            width = round(dims[1])
            length = round(dims[2])

            # 2. Метаданные (Обозначение и Наименование)
            cpm = doc.Extension.CustomPropertyManager("")
            desig = cpm.Get("Обозначение") or os.path.basename(full_prt).split()[0]
            name = name_override or cpm.Get("Наименование") or "Деталь"

            # Стандартизированное имя файла: {Обозначение} {Наименование}_{Толщина}мм_{Ширина}х{Длина}.dxf
            filename = f"{desig} {name}_{thickness:.1f}мм_{width}х{length}.dxf"
            laser_dxf_path = os.path.join(self.cnc_laser_dir, filename)

            # 3. Поиск базового эскиза контура реза (Sketch1 или эскиз развертки)
            feat = doc.FirstFeature
            base_sketch = None
            while feat:
                tname = feat.GetTypeName2 if isinstance(feat.GetTypeName2, str) else feat.GetTypeName2()
                if tname == "ProfileFeature" or "sketch" in feat.Name.lower():
                    if feat.Name == "Sketch1" or base_sketch is None:
                        base_sketch = feat
                        if feat.Name == "Sketch1":
                            break
                # Проверка подэлементов (Base-Flange, FlatPattern)
                sub = feat.GetFirstSubFeature
                while sub:
                    if "sketch" in sub.Name.lower():
                        base_sketch = sub
                        break
                    sub = sub.GetNextSubFeature
                if base_sketch and feat.Name == "Sketch1":
                    break
                feat = feat.GetNextFeature

            if not base_sketch:
                print(f"[ERROR] Не найден эскиз контура реза в: {full_prt}")
                return None

            sk = base_sketch.GetSpecificFeature2
            segs = sk.GetSketchSegments
            if not segs:
                print(f"[ERROR] Эскиз {base_sketch.Name} не содержит сегментов!")
                return None

            raw_entities = []
            for s in segs:
                st = s.GetType
                if st == 0:  # Линия
                    sp = s.GetStartPoint2
                    ep = s.GetEndPoint2
                    p1 = (sp.X * 1000.0, sp.Y * 1000.0, sp.Z * 1000.0)
                    p2 = (ep.X * 1000.0, ep.Y * 1000.0, ep.Z * 1000.0)
                    raw_entities.append(("LINE", p1, p2))
                elif st == 1:  # Дуга
                    cp = s.GetCenterPoint2
                    sp = s.GetStartPoint2
                    ep = s.GetEndPoint2
                    c = (cp.X * 1000.0, cp.Y * 1000.0, cp.Z * 1000.0)
                    p1 = (sp.X * 1000.0, sp.Y * 1000.0, sp.Z * 1000.0)
                    p2 = (ep.X * 1000.0, ep.Y * 1000.0, ep.Z * 1000.0)
                    r = math.sqrt((p1[0] - c[0]) ** 2 + (p1[1] - c[1]) ** 2 + (p1[2] - c[2]) ** 2)
                    arc_len = s.GetLength * 1000.0
                    raw_entities.append(("ARC", c, p1, p2, r, arc_len))

            # 4. Проекция на главную плоскость детали
            all_pts = []
            for item in raw_entities:
                if item[0] == "LINE":
                    all_pts.extend([item[1], item[2]])
                elif item[0] == "ARC":
                    all_pts.extend([item[1], item[2], item[3]])

            rx = max(p[0] for p in all_pts) - min(p[0] for p in all_pts)
            ry = max(p[1] for p in all_pts) - min(p[1] for p in all_pts)
            rz = max(p[2] for p in all_pts) - min(p[2] for p in all_pts)
            ranges = sorted([(rx, 0), (ry, 1), (rz, 2)], reverse=True)
            iu, iv = ranges[0][1], ranges[1][1]

            min_u = min(p[iu] for p in all_pts)
            min_v = min(p[iv] for p in all_pts)

            # 5. Генерация чистого 1:1 DXF (только контур на слое '0')
            dxf_doc = ezdxf.new("R2010")
            msp = dxf_doc.modelspace()

            for item in raw_entities:
                if item[0] == "LINE":
                    u1, v1 = item[1][iu] - min_u, item[1][iv] - min_v
                    u2, v2 = item[2][iu] - min_u, item[2][iv] - min_v
                    msp.add_line((u1, v1), (u2, v2), dxfattribs={"layer": "0"})
                elif item[0] == "ARC":
                    cu, cv = item[1][iu] - min_u, item[1][iv] - min_v
                    u1, v1 = item[2][iu] - min_u, item[2][iv] - min_v
                    u2, v2 = item[3][iu] - min_u, item[3][iv] - min_v
                    r = item[4]
                    arc_len = item[5]

                    ang1 = math.degrees(math.atan2(v1 - cv, u1 - cu)) % 360.0
                    ang2 = math.degrees(math.atan2(v2 - cv, u2 - cu)) % 360.0

                    # В DXF дуги строятся строго против часовой стрелки (CCW)
                    sweep1 = (ang2 - ang1) % 360.0
                    len1 = math.radians(sweep1) * r
                    sweep2 = (ang1 - ang2) % 360.0
                    len2 = math.radians(sweep2) * r

                    if abs(len1 - arc_len) < abs(len2 - arc_len):
                        start_angle, end_angle = ang1, ang2
                    else:
                        start_angle, end_angle = ang2, ang1

                    msp.add_arc(center=(cu, cv), radius=r, start_angle=start_angle, end_angle=end_angle, dxfattribs={"layer": "0"})

            # Сохранение строго в 03 ЧПУ и Раскрой\Лазер_Лист (без дублирования в Чертежи)
            dxf_doc.saveas(laser_dxf_path)

            print(f"[EXPORT LASER DXF] Выгружен чистый контур: {filename}")
            print(f"  Габариты: {width}х{length} мм, Толщина: {thickness} мм, Объектов контура: {len(msp)}")
            return laser_dxf_path

        finally:
            sw.CloseDoc(doc.GetTitle)

    def export_straight_tubes_to_igs(self, tube_parts: List[Tuple[str, str]]):
        """
        Экспортирует в IGS исключительно прямые детали из трубы.
        tube_parts: список кортежей (относительный путь к .SLDPRT, выходное имя .igs)
        """
        # Старые файлы не удаляются: они переносятся в карантин exact order root.
        for f in glob.glob(os.path.join(self.cnc_tube_dir, "*.*")):
            self._quarantine(f)

        sw = win32com.client.Dispatch("SldWorks.Application")
        sw.Visible = False
        errors = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(win32com.client.pythoncom.VT_BYREF | win32com.client.pythoncom.VT_I4, 0)

        for rel_path, out_name in tube_parts:
            # Защита от дуг под гибку
            if any(k in out_name.lower() for k in ["дуга", "гиб", "гнут"]):
                print(f"[SKIP IGS] Пропущена деталь под гибку: {out_name} (требует припуск на захват)")
                continue

            full_prt = os.path.join(self.root, rel_path)
            out_igs = os.path.join(self.cnc_tube_dir, out_name)
            doc = sw.OpenDoc6(full_prt, 1, 1, "", errors, warnings)
            if doc:
                doc.SaveAs3(out_igs, 0, 2)
                print(f"[EXPORT IGS] Сохранен для трубореза: {out_name}")
                sw.CloseDoc(doc.GetTitle)
            else:
                print(f"[ERROR] Не удалось открыть: {full_prt}")

        print("Экспорт прямых труб в IGS завершен.")


if __name__ == "__main__":
    root_dir = sys.argv[1] if len(sys.argv) > 1 else r"<WORK>\03_Проекты\85_Т"
    exporter = CncExporter(root_dir)
    exporter.clean_legacy_dxf_duplicates()
    
    # Пример выгрузки для текущего заказа:
    plug_path = r"01 3D-Модели\85T.СМ.01.000 Лежак\85T.СМ.01.004 Заглушка.SLDPRT"
    exporter.export_sheet_metal_to_dxf(plug_path)

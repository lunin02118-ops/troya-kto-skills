# -*- coding: utf-8 -*-
"""Excel «Технологические возможности TROYA» для технологов и конструкторов.

Вызывается из build_registry.py (--xlsx). Данные по трубе — из data/tube_capabilities.json,
правила для КД и пробелы — из data/dfm_rules.csv и data/gaps.csv.
"""
import csv
import json
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DATA = Path(__file__).resolve().parent.parent / "data"

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(bold=True, color="FFFFFF")
GRP_FILL = PatternFill("solid", fgColor="D9E1F2")
STATUS_FILL = {
    "Паспорт/договор": PatternFill("solid", fgColor="C6EFCE"),
    "passport": PatternFill("solid", fgColor="C6EFCE"),
    "КП/каталог": PatternFill("solid", fgColor="FFEB9C"),
    "offer": PatternFill("solid", fgColor="FFEB9C"),
    "drawing": PatternFill("solid", fgColor="DDEBF7"),
    "Лист цеха": PatternFill("solid", fgColor="DDEBF7"),
    "Только ОС": PatternFill("solid", fgColor="F2F2F2"),
    "os_only": PatternFill("solid", fgColor="F2F2F2"),
    "Общее правило": PatternFill("solid", fgColor="FCE4D6"),
    "Нет данных": PatternFill("solid", fgColor="FFC7CE"),
}
STATUS_RU = {"passport": "Паспорт/договор", "offer": "КП/каталог", "drawing": "Лист цеха", "os_only": "Только ОС"}
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

SUMMARY = [
    ("01 Резка трубы/профиля",
     "Лазерная резка трубы: отверстия, пазы, фигурные торцы, врезки «под седло», резка в размер; мерная резка пилами под углом; пробивка отверстий штампом.",
     "Bodor K0-65 3 кВт: Ø6–90, □/▭ 6–90, уголок/швеллер ≤60; хлыст ≤6,5 м, ≤70 кг, ≤11 кг/м; позиц. 0,05; отход 40 мм. Углорезы MC-315B ×2, MC275A, YDL-300B.",
     "Паспорт/договор"),
    ("02 Раскрой листа",
     "Координатная пробивка, высечка, формовка, маркировка; лазерный раскрой листа (модель уточнить); рубка на гильотине; вырубка углов.",
     "DADONG D-ES300: 30 т, лист ≤6,35 мм, 2500×1250(1500), с перехватом до 5000, 32 станции Ø1,5–88,9, ±0,1 мм.",
     "КП/каталог"),
    ("03 Гибка листа",
     "Гибка на листогибочных прессах, в т.ч. с ЧПУ.",
     "PBH-160-3100 (ЧПУ, 160 т × 3100 мм); Xinchuang 40 т × 2500; ручной XSQ-1.",
     "Только ОС"),
    ("04 Гибка трубы",
     "Дорновая гибка с ЧПУ, правая/левая, пространственные детали (3D), раскатка больших радиусов, гибка проталкиванием.",
     "Cansa CNC-35/ED: Ø8–35×2 (нерж 32×1,5), профиль до 30×30×2, CLR 20–100 + раскатка, ≤190°, дорн 4000. Также CSM TM RE, YT50CNC (до Ø50), DM-38. Оснастка: 20 комплектов R (лист «Трубогиб — оснастка R»).",
     "Паспорт/договор"),
    ("05 Проволока и сетка",
     "Гибка проволоки с ЧПУ, правка-отрезка, сварка сетки, гибка сетки, точечная контактная сварка.",
     "Машина формовки проволоки ЧПУ, сварка сетки (двухрежимная), сеткогиб, DTN-80.",
     "Только ОС"),
    ("06 Сварка",
     "MIG/MAG полуавтоматы, MMA, роботизированная лазерная сварка.",
     "Kemppi Kempact 323A ×12, Overman 250, VEGAMIG 250, робот KOZA KZH-JR612; вытяжки KUA ×3.",
     "Только ОС"),
    ("07 Механообработка",
     "Токарная, сверлильная, фрезерная (металл), заточка, шлифование, полирование.",
     "1К62, сверлильные ×4, фрезерные, полировальная машина.",
     "Только ОС"),
    ("08 Покраска",
     "Порошковая окраска с полимеризацией, жидкая окраска.",
     "Линия EUROSTATIK-APC, камеры полимеризации ×2, камера MF9235B.",
     "Только ОС"),
    ("09 Пластмассы",
     "Литьё под давлением, экструзионно-выдувное формование, термовставка резьбовых втулок, переработка литников.",
     "ТПА КМ 230 КК, ТВ200н/1000; выдувная YM FH CS 700/80B; 9 собственных пресс-форм (заглушки, уплотнители, сиденье, спинка, моноблок, СЛОТТ, направляющая).",
     "Только ОС"),
    ("10 Заливка 2К",
     "Дозирование и заливка двухкомпонентных составов со статическим смешением.",
     "Дозирующие машины «Стандарт», «Компакт» С-001.",
     "Только ОС"),
    ("11 Деревообработка (корпус)",
     "Раскрой плит, ЧПУ-обработка, кромкооблицовка (прямо- и криволинейная), присадка, гнутоклееные детали из шпона.",
     "HOMAG SAWTEQ B-200, DRILLTEQ V-200, KDT KD-610R, кромочные ×7, фрезеры ЧПУ до 2000×3000, пресс МН3841.",
     "Только ОС"),
    ("12 Текстиль/войлок",
     "Раскрой ткани/войлока ножом с ЧПУ.",
     "ZX-1825V.",
     "Только ОС"),
    ("13 Упаковка", "Обвязка, обмотка, обёртка стрейч-плёнкой.", "UDB 101A, S1200, T1650QY.", "Только ОС"),
    ("14 Инфраструктура", "Сжатый воздух, газ, подъёмно-транспортное оборудование.",
     "Компрессоры ×3 + осушитель, газовая установка, погрузчики ×5, подъёмники HPlift ×2.", "Только ОС"),
]


def _hdr(ws, headers, widths, row=1):
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        c = ws.cell(row=row, column=i, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _row(ws, r, values, status_col=None):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=r, column=i, value=v)
        c.alignment, c.border = WRAP, BORDER
    if status_col:
        st = ws.cell(row=r, column=status_col).value
        if st in STATUS_FILL:
            ws.cell(row=r, column=status_col).fill = STATUS_FILL[st]


def _read_csv(name):
    with open(DATA / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def sheet_summary(wb):
    ws = wb.active
    ws.title = "Сводка"
    ws["A1"] = "Технологические возможности ТОО «TROYA» — сводка по переделам"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (f"Сформировано {date.today():%d.%m.%Y}. Источники: ведомость ОС (сч. 2410) на 22.09.2026, паспорта и КП из "
                "«Технологические возможности\\Паспорта_и_КП_оборудования». Статус: зелёный — паспорт/договор, жёлтый — КП/каталог, "
                "голубой — лист цеха, серый — только название в ОС (характеристики не подтверждены), розовый — общее правило.")
    ws["A2"].alignment = WRAP
    ws.merge_cells("A2:D2")
    ws.row_dimensions[2].height = 48
    _hdr(ws, ["Передел", "Что умеем", "Ключевое оборудование и пределы", "Достоверность"], [26, 55, 80, 18], row=4)
    for r, v in enumerate(SUMMARY, 5):
        _row(ws, r, v, status_col=4)


def sheet_registry(wb, rows):
    ws = wb.create_sheet("Реестр оборудования")
    _hdr(ws, ["Передел", "Вид оборудования", "Модель / краткое имя", "Кол-во", "ЧПУ",
              "Возможности для КД", "Достоверность", "Источник", "Наименования в ведомости ОС"],
         [24, 30, 34, 8, 7, 70, 16, 30, 60])
    r = 2
    for x in rows:
        _row(ws, r, [x["group"], x["kind"], x["short"], x["qty"], x["cnc"], x["spec"], x["status"], x["source"],
                     "\n".join(x["os_names"])], status_col=7)
        ws.cell(row=r, column=1).fill = GRP_FILL
        r += 1
    ws.auto_filter.ref = f"A1:I{r-1}"


def sheet_laser(wb, c):
    L = c["tube_laser"]
    ws = wb.create_sheet("Труборез K0-65")
    _hdr(ws, ["Параметр", "Значение", "Источник"], [44, 70, 22])
    data = [
        ("Станок", L["model"], "Паспорт"),
        ("Круглая труба, Ø", f"{L['round_d'][0]}–{L['round_d'][1]} мм", "Паспорт/договор"),
        ("Квадратная труба", "□6×6 – □90×90 мм", "Паспорт/договор"),
        ("Прямоугольная труба", "обе стороны 6–90 мм", "Договор"),
        ("Уголок, швеллер (наибольшая полка)", f"≤{L['angle_channel_side_max']} мм (договор); 6–80 мм (каталог K0)", "Договор/каталог"),
        ("Овальная труба", "до 90×90, зажим кулачками изнутри", "Каталог"),
        ("Длина хлыста (заготовки)", f"≤{L['stock_length_max']} мм", "Паспорт"),
        ("Масса хлыста / погонная", f"≤{L['stock_mass_max_kg']} кг; ≤{L['linear_mass_max_kg_m']} кг/м", "Паспорт"),
        ("Минимальный отход (хвост)", f"{L['min_tail']} мм", "Паспорт"),
        ("Точность позиционирования X/Y", f"{L['positioning']} мм", "Паспорт"),
        ("Повторяемость", f"{L['repositioning']} мм", "Паспорт"),
        ("Точность детали", L["accuracy_class"], "Каталог"),
        ("Шероховатость реза (стенка 0–6 мм)", L["roughness_0_6mm"], "Каталог"),
        ("Скорость X / ускорение / патрон", "120 м/мин / 1G / 150 об/мин", "Паспорт"),
        ("Лазер / голова / ЧПУ", "3000 Вт BODOR POWER; Bodor Genius T, автофокус; BodorThinker 3.0, EtherCAT", "Договор"),
        ("Газы", "; ".join(f"{k}: {v}" for k, v in L["gases"].items()), "Каталог"),
        ("Раскладка фасонных профилей", L["nesting_gap_rule"], "Каталог"),
        ("Макс. толщина стенки", L["wall_max_note"], "Нет данных"),
        ("Габарит станка, масса", "9260×1700×1972 мм, 2270 кг", "Договор"),
    ]
    for r, v in enumerate(data, 2):
        _row(ws, r, v)
        if v[2] == "Нет данных":
            ws.cell(row=r, column=3).fill = STATUS_FILL["Нет данных"]
    r = len(data) + 3
    ws.cell(row=r, column=1, value="Требования к трубе-заготовке (вносить в заявку на закуп / ТТ)").font = Font(bold=True)
    for i, t in enumerate(L["stock_requirements"], r + 1):
        _row(ws, i, [f"{i - r}", t, "Каталог"])


def sheet_benders(wb, c):
    ws = wb.create_sheet("Трубогибы")
    _hdr(ws, ["Станок", "ЧПУ", "Круг, сталь", "Нерж.", "Профиль", "CLR, мм", "Угол", "Радиусов в детали",
              "Дорн / длина", "Точность", "Импорт геометрии", "Достоверность", "Примечание"],
         [34, 6, 16, 12, 16, 22, 8, 26, 14, 22, 22, 16, 45])
    for r, m in enumerate(c["benders"], 2):
        rs, ss, ps = m.get("round_steel"), m.get("round_stainless"), m.get("profile_steel")
        rep = m.get("repeatability")
        _row(ws, r, [
            m["model"], "да" if m.get("cnc") else "нет",
            (f"Ø{rs['d'][0] or '?'}–{rs['d'][1]}" + (f"×{rs['s_max']}" if rs.get("s_max") else "")) if rs else "",
            f"Ø{ss['d_max']}×{ss['s_max']}" if ss else "",
            f"{ps['a'][0]}×{ps['a'][0]}–{ps['a'][1]}×{ps['a'][1]}×{ps['s_max']}" if ps else "",
            (f"{m['clr'][0]}–{m['clr'][1]}; " + m.get("clr_note", "")) if m.get("clr") else "",
            m.get("angle_max", ""), m.get("radii_per_part", ""),
            (f"{m['mandrel_length']} (опц. {m.get('mandrel_length_option')})" if m.get("mandrel_length") else ""),
            (f"гиб ±{rep['bend_deg']}°, поворот ±{rep['rotation_deg']}°, подача ±{rep['feed_mm']}" if rep else ""),
            m.get("import", ""), STATUS_RU[m["status"]], m.get("note", "")], status_col=12)
        for col in (3, 4, 5, 6, 10):  # десятичная запятая в числовых колонках
            cell = ws.cell(row=r, column=col)
            if isinstance(cell.value, str):
                cell.value = cell.value.replace(".0×", "×").replace(".0 ", " ").replace(".", ",")


def sheet_tooling(wb, c):
    ws = wb.create_sheet("Трубогиб — оснастка R")
    shape_ru = {"round": "круглая", "square": "квадратная", "rect": "прямоугольная", "oval": "плоскоовальная"}
    plane_ru = {"a": "большая сторона в плоскости гиба («на ребро»)", "b": "малая сторона в плоскости гиба («плашмя»)", None: ""}
    _hdr(ws, ["Станок", "Профиль", "Размер, мм", "Стенка, мм", "R по оси, мм", "L1 прижим, мм", "L2 прокат, мм",
              "Ориентация", "R/D", "Достоверность"], [26, 16, 12, 11, 12, 13, 13, 40, 8, 16])
    rows = sorted(c["tooling"], key=lambda t: (t["machine"], t["shape"], t["a"], t["clr"]))
    for r, t in enumerate(rows, 2):
        size = f"Ø{t['a']:g}" if t["shape"] == "round" else f"{t['a']:g}×{t['b']:g}"
        bend_dim = t["a"] if t["shape"] == "round" else (t["b"] if t["plane"] != "a" else t["a"]) if t["b"] else t["a"]
        machine = "Cansa CNC-35/ED" if t["machine"] == "CNC35ED" else "CSM TM RE (Flexy)" if t["machine"] == "CSM-TMRE" else t["machine"]
        _row(ws, r, [machine, shape_ru[t["shape"]], size, t["s"], t["clr"], t["L1_clamp"], t["L2_pressure"],
                     plane_ru[t["plane"]], round(t["clr"] / bend_dim, 2), STATUS_RU[t["status"]]], status_col=10)
    ws.auto_filter.ref = f"A1:J{len(rows) + 1}"
    r = len(rows) + 3
    ws.cell(row=r, column=1, value="Пояснения").font = Font(bold=True)
    for i, n in enumerate(c["tooling_notes"] + c["rules_of_thumb"], r + 1):
        ws.cell(row=i, column=1, value=n).alignment = WRAP
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=10)
        ws.row_dimensions[i].height = 32


def sheet_sheet_metal(wb):
    ws = wb.create_sheet("Лист — пробивка, гибка")
    _hdr(ws, ["Параметр", "DADONG D-ES300 (пробивной с ЧПУ)", "Источник"], [40, 70, 16])
    data = [
        ("Усилие", "300 кН (30 т), серво-привод бойка, станина О-образная", "КП"),
        ("Толщина листа", "≤ 6,35 мм", "КП"),
        ("Лист без перехвата", "2500×1250 (исполнение 1250) / 2500×1500 — какое у TROYA, УТОЧНИТЬ", "КП"),
        ("Лист с перехватом", "5000×1250 / 5000×1500", "КП"),
        ("Револьвер", "32 станции, раскладка по КП: 16A / 10B / 2BC / 2C / 2B; из них 2 индексные (поворот инструмента 360°), +2 опция", "КП"),
        ("Станции A", "Ø 1,5–12,7 мм", "КП"),
        ("Станции B", "Ø 12,7–31,7 мм", "КП"),
        ("Станции C", "Ø 31,7–50,8 мм", "КП"),
        ("Станции D", "Ø 50,8–88,9 мм", "КП"),
        ("Ход бойка", "32 мм (формовки, выдавки, жалюзи — при наличии инструмента)", "КП"),
        ("Скорость", "до 1500 уд/мин; шаг 1 мм — 900; шаг 25,4 — 500 уд/мин", "КП"),
        ("Точность позиционирования", "±0,1 мм", "КП"),
        ("Оси", "5: X, Y, T (револьвер), C (индекс), A (боёк)", "КП"),
        ("Функции", "пробивка, высечка (nibbling), формовка, прокатка рифтов, маркировка, резка", "КП"),
        ("Набор инструмента", "ЗАПРОСИТЬ перечень пуансонов/матриц у технолога", "Нет данных"),
    ]
    for r, v in enumerate(data, 2):
        _row(ws, r, v)
        if v[2] == "Нет данных":
            ws.cell(row=r, column=3).fill = STATUS_FILL["Нет данных"]
    r = len(data) + 3
    ws.cell(row=r, column=1, value="Листогибочные прессы").font = Font(bold=True)
    for i, v in enumerate([
        ("PBH-160-3100 с ЧПУ", "160 т × 3100 мм (из наименования ОС). Оси заднего упора, набор пуансонов/матриц — ЗАПРОСИТЬ", "Только ОС"),
        ("Xinchuang Machine 40T/2500", "40 т × 2500 мм (из наименования ОС)", "Только ОС"),
        ("XSQ-1", "Ручной листогиб", "Только ОС"),
        ("Гильотина Weier Machine T10", "Длина/толщина реза ЗАПРОСИТЬ", "Только ОС"),
    ], r + 1):
        _row(ws, i, v, status_col=3)


def sheet_dfm(wb):
    ws = wb.create_sheet("Правила для КД")
    rows = _read_csv("dfm_rules.csv")
    _hdr(ws, ["Код", "Передел", "Правило для конструктора", "Значение / предел", "Достоверность", "Источник"],
         [8, 20, 70, 36, 16, 30])
    for r, x in enumerate(rows, 2):
        _row(ws, r, [x["id"], x["process"], x["rule"], x["value"], x["status"], x["source"]], status_col=5)
    ws.auto_filter.ref = f"A1:F{len(rows) + 1}"


def sheet_gaps(wb):
    ws = wb.create_sheet("Пробелы — запросить")
    rows = _read_csv("gaps.csv")
    _hdr(ws, ["Приоритет", "Оборудование", "Что запросить", "Зачем конструктору", "Ответственный", "Статус"],
         [10, 34, 60, 50, 18, 14])
    for r, x in enumerate(rows, 2):
        _row(ws, r, [x["priority"], x["machine"], x["request"], x["why"], x["owner"], x["state"]])
    ws.auto_filter.ref = f"A1:F{len(rows) + 1}"


def make_xlsx(rows, path):
    c = json.loads((DATA / "tube_capabilities.json").read_text(encoding="utf-8"))
    wb = Workbook()
    sheet_summary(wb)
    sheet_registry(wb, [r for r in rows if not r["group"].startswith("15")])
    sheet_laser(wb, c)
    sheet_benders(wb, c)
    sheet_tooling(wb, c)
    sheet_sheet_metal(wb)
    sheet_dfm(wb)
    sheet_gaps(wb)
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 90
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)

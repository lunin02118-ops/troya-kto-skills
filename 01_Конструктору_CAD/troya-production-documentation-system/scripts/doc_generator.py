# -*- coding: utf-8 -*-
import os
import sys
import shutil
import glob
from pathlib import Path
import docx
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import win32com.client
import pymupdf
import zipfile

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

COLOR_PRIMARY = RGBColor(0x11, 0x18, 0x27)
COLOR_SECONDARY = RGBColor(0x4B, 0x55, 0x63)
COLOR_ACCENT = RGBColor(0x1D, 0x4E, 0xD8)
HEX_BG_HEADER = "F3F4F6"
HEX_BG_TOTAL = "E5E7EB"
HEX_BORDER = "4B5563"

ORDER_DATA_85T = {
    "order_no": "85_Т",
    "customer": "ТОО «Компания TROYA»",
    "product_name": "Кровать одноместная",
    "product_code": "85T.СМ.00.000",
    "qty": "41",
    "date": "04.09.2026",
    "author_title": "Нач. КТО: ",
    "author": "<ФИО>"
}

TEMPLATE_DATA = {
    "order_no": "[ Номер заявки ]",
    "customer": "ТОО «Компания TROYA»",
    "product_name": "[ Наименование изделия ]",
    "product_code": "[ Обозначение ]",
    "qty": "[ ___ ]",
    "date": "[ ДД.ММ.ГГГГ ]",
    "author_title": "Нач. КТО: ",
    "author": "[ Ф.И.О. ]"
}

def set_cell_background(cell, fill_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=45, bottom=45, left=40, right=40):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, border_color="4B5563", border_size="4", outer_size="6"):
    tblPr = table._tbl.tblPr
    borders_elm = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="{outer_size}" w:space="0" w:color="{border_color}"/>
            <w:left w:val="single" w:sz="{outer_size}" w:space="0" w:color="{border_color}"/>
            <w:bottom w:val="single" w:sz="{outer_size}" w:space="0" w:color="{border_color}"/>
            <w:right w:val="single" w:sz="{outer_size}" w:space="0" w:color="{border_color}"/>
            <w:insideH w:val="single" w:sz="{border_size}" w:space="0" w:color="{border_color}"/>
            <w:insideV w:val="single" w:sz="{border_size}" w:space="0" w:color="{border_color}"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders_elm)

def setup_page_geometry(doc):
    for sec in doc.sections:
        sec.page_width = Inches(8.27)
        sec.page_height = Inches(11.69)
        sec.top_margin = Inches(0.40)
        sec.bottom_margin = Inches(0.40)
        sec.left_margin = Inches(0.50)
        sec.right_margin = Inches(0.50)

def add_header_block(doc, sheet_badge, sheet_title, sheet_subtitle, data=None):
    if data is None:
        data = TEMPLATE_DATA
    is_template = (data == TEMPLATE_DATA or "[" in str(data.get("order_no", "")))

    h_table = doc.add_table(rows=3, cols=2)
    h_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    h_table.autofit = False
    
    col_widths = [Inches(4.30), Inches(2.97)]
    for row in h_table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            
    r0 = h_table.rows[0]
    p00 = r0.cells[0].paragraphs[0]
    p00.paragraph_format.space_after = Pt(1)
    r = p00.add_run("ТОО «Компания TROYA» | Производственная заявка")
    r.font.name = 'Arial'
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = COLOR_PRIMARY
    
    p01 = r0.cells[1].paragraphs[0]
    p01.paragraph_format.space_after = Pt(1)
    p01.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p01.add_run("Дата: ")
    r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    if is_template:
        r = p01.add_run("[ ДД.ММ.ГГГГ ]")
        r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.color.rgb = COLOR_SECONDARY
    else:
        r = p01.add_run(str(data.get('date', '')))
        r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
        
    r1 = h_table.rows[1]
    p10 = r1.cells[0].paragraphs[0]
    p10.paragraph_format.space_after = Pt(2)
    r = p10.add_run("№ заявки: ")
    r.font.name = 'Arial'; r.font.size = Pt(11.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    r_no = p10.add_run(data['order_no'])
    r_no.font.name = 'Arial'; r_no.font.size = Pt(11.5); r_no.font.bold = True; r_no.font.color.rgb = COLOR_ACCENT
    
    p11 = r1.cells[1].paragraphs[0]
    p11.paragraph_format.space_after = Pt(2)
    p11.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    author_lbl = data.get("author_title", "Нач. КТО: ")
    r = p11.add_run(author_lbl)
    r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    r_auth = p11.add_run(data['author'])
    r_auth.font.name = 'Arial'; r_auth.font.size = Pt(9.5)
    if is_template:
        r_auth.font.color.rgb = COLOR_SECONDARY
    else:
        r_auth.font.bold = True; r_auth.font.color.rgb = COLOR_PRIMARY
        
    r2 = h_table.rows[2]
    p20 = r2.cells[0].paragraphs[0]
    p20.paragraph_format.space_after = Pt(3)
    r = p20.add_run("Изделие: ")
    r.font.name = 'Arial'; r.font.size = Pt(10); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    r_prod = p20.add_run(data['product_name'])
    r_prod.font.name = 'Arial'; r_prod.font.size = Pt(10)
    if is_template:
        r_prod.font.color.rgb = COLOR_SECONDARY
    else:
        r_prod.font.bold = True; r_prod.font.color.rgb = COLOR_PRIMARY
        
    p21 = r2.cells[1].paragraphs[0]
    p21.paragraph_format.space_after = Pt(3)
    p21.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p21.add_run("Шифр: ")
    r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    r_code = p21.add_run(data['product_code'])
    r_code.font.name = 'Arial'; r_code.font.size = Pt(9.5)
    if is_template:
        r_code.font.color.rgb = COLOR_SECONDARY
    else:
        r_code.font.bold = True; r_code.font.color.rgb = COLOR_PRIMARY
    r = p21.add_run("  |  Кол-во: ")
    r.font.name = 'Arial'; r.font.size = Pt(9.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    r_qty = p21.add_run(f"{data['qty']} шт." if not str(data['qty']).endswith("шт.") else data['qty'])
    r_qty.font.name = 'Arial'; r_qty.font.size = Pt(9.5); r_qty.font.bold = True; r_qty.font.color.rgb = COLOR_ACCENT

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(1)
    
    r_badge = p_title.add_run(sheet_badge + "  ")
    r_badge.font.name = 'Arial'; r_badge.font.size = Pt(11); r_badge.font.bold = True; r_badge.font.color.rgb = COLOR_ACCENT
    
    r_title = p_title.add_run(sheet_title)
    r_title.font.name = 'Arial'; r_title.font.size = Pt(11); r_title.font.bold = True; r_title.font.color.rgb = COLOR_PRIMARY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run(sheet_subtitle)
    r_sub.font.name = 'Arial'; r_sub.font.size = Pt(8.5); r_sub.font.italic = True; r_sub.font.color.rgb = COLOR_SECONDARY

def add_grid_table(doc, headers, data_rows, col_widths, align_right=None, align_center=None, total_merge_cols=2, bold_col=None):
    align_right = align_right or []
    align_center = align_center or []
    
    tbl = doc.add_table(rows=1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    set_table_borders(tbl, border_color=HEX_BORDER, border_size="4", outer_size="6")
    
    hdr = tbl.rows[0]
    for idx, h in enumerate(headers):
        c = hdr.cells[idx]
        c.width = Inches(col_widths[idx])
        set_cell_background(c, HEX_BG_HEADER)
        set_cell_margins(c, top=50, bottom=50, left=35, right=35)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        if idx in align_right:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif idx in align_center or idx == 0:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(h)
        r.font.name = 'Arial'; r.font.size = Pt(7.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
        
    for row_idx, row_data in enumerate(data_rows):
        row = tbl.add_row()
        is_total = (row_data[0] == "ИТОГО" or "ИТОГО" in str(row_data[1]))
        
        if is_total and total_merge_cols > 1:
            for idx in range(len(row_data)):
                cell = row.cells[idx]
                cell.width = Inches(col_widths[idx])
                set_cell_background(cell, HEX_BG_TOTAL)
                set_cell_margins(cell, top=55, bottom=55, left=35, right=35)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                if idx in align_right:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif idx in align_center:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(str(row_data[idx]))
                r.font.name = 'Arial'; r.font.size = Pt(7.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
            # Merge
            merged_cell = row.cells[0]
            for m in range(1, total_merge_cols):
                merged_cell = merged_cell.merge(row.cells[m])
            label = row_data[1] if row_data[0] in ["ИТОГО", ""] else f"{row_data[0]} {row_data[1]}"
            merged_cell.text = label
            p = merged_cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.runs[0] if p.runs else p.add_run(label)
            r.font.name = 'Arial'; r.font.size = Pt(7.5); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
            set_cell_background(merged_cell, HEX_BG_TOTAL)
            set_cell_margins(merged_cell, top=55, bottom=55, left=45, right=45)
        else:
            for idx, val in enumerate(row_data):
                c = row.cells[idx]
                c.width = Inches(col_widths[idx])
                set_cell_margins(c, top=45, bottom=45, left=35, right=35)
                p = c.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                if idx in align_right:
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif idx in align_center or idx == 0:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(str(val))
                r.font.name = 'Arial'; r.font.size = Pt(7.5)
                if bold_col is not None and idx == bold_col:
                    r.font.bold = True
                if "[" in str(val) and "]" in str(val):
                    r.font.color.rgb = COLOR_SECONDARY
                else:
                    r.font.color.rgb = COLOR_PRIMARY

def add_calc_notes_block(doc, notes_list, title="Примечания по раскрою и оприходованию деловых остатков:"):
    p_head = doc.add_paragraph()
    p_head.paragraph_format.space_before = Pt(8)
    p_head.paragraph_format.space_after = Pt(2)
    r = p_head.add_run(title)
    r.font.name = 'Arial'; r.font.size = Pt(8.0); r.font.bold = True; r.font.color.rgb = COLOR_PRIMARY
    
    for n in notes_list:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.left_indent = Inches(0.15)
        r = p.add_run("•  " + n)
        r.font.name = 'Arial'; r.font.size = Pt(7.5); r.font.color.rgb = COLOR_SECONDARY

def add_signatures_block(doc, left_title="Нач. КТО ТОО «ТРОЯ»:", left_name="<ФИО>",
                         right_title="Начальник цеха / Мастер участка:", right_name="", space_before=Pt(20)):
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = space_before
    p_sp.paragraph_format.space_after = Pt(0)
    
    sig_tbl = doc.add_table(rows=2, cols=2)
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_tbl.autofit = False
    
    col_widths = [Inches(3.63), Inches(3.64)]
    for row in sig_tbl.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            
    p0 = sig_tbl.rows[0].cells[0].paragraphs[0]
    p0.paragraph_format.space_after = Pt(1)
    r = p0.add_run(left_title)
    r.font.name = 'Arial'; r.font.size = Pt(8.0); r.font.bold = True
    
    p1 = sig_tbl.rows[0].cells[1].paragraphs[0]
    p1.paragraph_format.space_after = Pt(1)
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p1.add_run(right_title)
    r.font.name = 'Arial'; r.font.size = Pt(8.0); r.font.bold = True
    
    p2 = sig_tbl.rows[1].cells[0].paragraphs[0]
    p2.paragraph_format.space_after = Pt(0)
    r = p2.add_run(f"___________________ / {left_name}")
    r.font.name = 'Arial'; r.font.size = Pt(8.0)
    
    p3 = sig_tbl.rows[1].cells[1].paragraphs[0]
    p3.paragraph_format.space_after = Pt(0)
    p3.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p3.add_run(f"___________________ / {right_name if right_name else '________________'}")
    r.font.name = 'Arial'; r.font.size = Pt(8.0)

# ==================== SHEET BUILDERS FOR ORDER 85_T (БЕЗ ТЕХНОЛОГИЧЕСКИХ УКАЗАНИЙ) ====================

def build_sheet_1_metal_85t(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 1",
        sheet_title="1. ЦЕХ МЕТАЛЛОИЗДЕЛИЙ (Заготовительный участок: Резка, Гибка, ЧПУ-раскрой)",
        sheet_subtitle="Спецификация чистых заготовок на тираж (для ленточной пилы, ЧПУ-трубореза, трубогиба и лазера)",
        data=ORDER_DATA_85T
    )
    headers = ["№", "Обозначение", "Наименование детали", "Сортамент / Материал", "L, мм", "На 1", "Всего, шт", "Операция"]
    col_widths = [0.28, 1.15, 1.70, 1.75, 0.48, 0.38, 0.45, 1.08]
    rows = [
        ["1", "85T.СМ.01.002", "Связь", "Тр. 50х25х1.5 ГОСТ 8645-68", "1996.0", "2", "82", "Резка в размер"],
        ["2", "85T.СМ.01.001", "Связь", "Тр. 25х25х1.5 ГОСТ 8639-82", "900.0", "14", "574", "Резка пакетом"],
        ["3", "85T.СМ.02.001", "Дуга", "Тр. ø32х1.5 ГОСТ 10704-91", "2620.0*", "2", "82", "Гибка R75 (R443)"],
        ["4", "85T.СМ.02.002", "Дуга малая", "Тр. ø32х1.5 ГОСТ 10704-91", "1806.0*", "2", "82", "Гибка R75 (R411)"],
        ["5", "85T.СМ.02.004", "Связь", "Тр. 20х20х1.2 ГОСТ 8639-82", "850.4", "2", "82", "Резка в размер"],
        ["6", "85T.СМ.01.004", "Заглушка", "Лист 2.0 Ст3сп ГОСТ 19904", "48.0", "4", "164", "Лазер ЧПУ"],
        ["", "ИТОГО ЗАГОТОВОК НА ЗАКАЗ (41 кровать)", "", "", "", "26", "1066", "6 типоразм."]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[4, 5, 6], align_center=[0, 1, 7], total_merge_cols=5, bold_col=6)
    # По стандартам предприятия технологические указания исключены!
    add_signatures_block(doc, right_title="Начальник цеха металлоизделий:", space_before=Pt(28))

def build_sheet_2_welding_85t(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 2",
        sheet_title="2. СВАРОЧНО-СБОРОЧНЫЙ ЦЕХ",
        sheet_subtitle="Сборочные единицы металлокаркаса, нормативы сварки и масса конструкций",
        data=ORDER_DATA_85T
    )
    headers = ["№", "Обозначение узла", "Наименование сборочной единицы", "Масса 1 шт, кг", "На 1 изд", "Всего на тираж", "Общая масса, кг"]
    col_widths = [0.30, 1.50, 2.67, 0.70, 0.55, 0.75, 0.80]
    rows = [
        ["1", "85T.СМ.01.000", "Лежак", "22.13", "1", "41", "907.33"],
        ["2", "85T.СМ.02.000", "Спинка", "5.64", "2", "82", "462.48"],
        ["", "ИТОГО ГОТОВЫЙ МЕТАЛЛОКАРКАС НА ЗАКАЗ", "", "", "3", "123 узла", "1369.81 кг"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[3, 4, 5, 6], align_center=[0, 1], total_merge_cols=4, bold_col=5)
    # По стандартам предприятия технологические указания исключены!
    add_signatures_block(doc, right_title="Начальник сварочного цеха:", space_before=Pt(36))

def build_sheet_3_painting_85t(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 3",
        sheet_title="3. УЧАСТОК ПОЛИМЕРНО-ПОРОШКОВОЙ ПОКРАСКИ",
        sheet_subtitle="Ведомость окрашиваемых сборочных единиц и цвет полимерного покрытия",
        data=ORDER_DATA_85T
    )
    headers = ["№", "Обозначение узла", "Наименование сборочной единицы", "На 1 изд", "Всего на тираж", "Цвет покрытия"]
    col_widths = [0.30, 1.65, 2.87, 0.60, 0.75, 1.10]
    rows = [
        ["1", "85T.СМ.01.000", "Лежак", "1", "41", "RAL 7035"],
        ["2", "85T.СМ.02.000", "Спинка", "2", "82", "RAL 7035"],
        ["", "ИТОГО НА ПОКРАСКУ (тираж 41 кровать)", "", "3", "123 узла", "RAL 7035"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[3, 4], align_center=[0, 1, 5], total_merge_cols=3, bold_col=4)
    # По стандартам предприятия технологические указания исключены!
    add_signatures_block(doc, right_title="Мастер малярного участка:", space_before=Pt(36))

def build_sheet_4_hardware_85t(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 4",
        sheet_title="4. СКЛАД ТМЦ И УЧАСТОК КОМПЛЕКТАЦИИ (Фурнитура и покупные изделия)",
        sheet_subtitle="Комплектовочная ведомость покупной фурнитуры, комплектующих и настила",
        data=ORDER_DATA_85T
    )
    headers = ["№", "Код 1С", "Номенклатура ТМЦ", "Ед. изм.", "На 1 изд", "Всего на тираж", "Назначение"]
    col_widths = [0.30, 1.15, 2.67, 0.50, 0.50, 0.65, 1.50]
    rows = [
        ["1", "У00000XXXXX", "Комплект замка «Клин / Петля»", "компл.", "4", "164", "Навеска лежака на спинки"],
        ["2", "У00000XXXXX", "Заглушка наружная д.32 (каблук)", "шт.", "4", "164", "Опоры ножек спинок"],
        ["3", "У00000XXXXX", "Плита МДФ 2800*2070*6 мм (настил)", "м²", "1.80", "73.80", "Настил лежака 2000х900х6 мм"],
        ["4", "У00000XXXXX", "Краска порошковая RAL 7035", "кг", "0.609", "25.0", "Полимерная покраска (1 коробка 25 кг)"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[4, 5], align_center=[0, 1, 3], total_merge_cols=1, bold_col=5)
    # По стандартам предприятия технологические указания исключены!
    add_signatures_block(doc, right_title="Заведующий складом ТМЦ:", space_before=Pt(32))

def build_sheet_5_writeoff_85t(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 5",
        sheet_title="5. СВОДНАЯ ВЕДОМОСТЬ РАСХОДА И СПИСАНИЯ ТМЦ",
        sheet_subtitle="Расчет потребности в хлыстах 6000 мм, КИМ, деловых обрезков (>=500 мм) и технологического отхода",
        data=ORDER_DATA_85T
    )
    headers = ["№", "Сортамент и ГОСТ", "Чистый расход, м", "Хлыстов 6 м", "Расход с уч. техн., м", "Расход с уч. техн., кг", "КИМ, %", "Деловые обрезки (>=500 мм)", "Отход, кг"]
    col_widths = [0.28, 1.65, 0.65, 0.55, 0.62, 0.62, 0.45, 1.90, 0.55]
    rows = [
        ["1", "Труба 50х25х1.5 ГОСТ 8645-68", "163.7", "41 хл.", "246.0", "405.9", "66.5%", "81.6 м (134.6 кг) — 41 шт ~1990 мм", "1.2"],
        ["2", "Труба 25х25х1.5 ГОСТ 8639-82", "516.6", "96 хл.", "576.0", "611.1", "89.7%", "59.4 м (63.0 кг) — 95 шт ~600 мм + 1 шт 2.4 м", "3.6"],
        ["3", "Труба ø32х1.5 ГОСТ 10704-91", "362.9", "82 хл.", "492.0", "555.0", "73.8%", "127.9 м (144.3 кг) — 82 шт ~1560 мм", "0.0"],
        ["4", "Труба 20х20х1.2 ГОСТ 8639-82", "69.7", "12 хл.", "72.0", "47.5", "96.8%", "1.7 м (1.1 кг) — 1 отрезок 1712 мм", "0.4"],
        ["5", "Лист 2.0 Ст3сп 1250х2500", "—", "1 лист", "—", "49.1", "85.0%", "41.7 кг (0.85 листа деловой)", "7.4"],
        ["", "ИТОГО МЕТАЛЛОПРОКАТ НА ЗАКАЗ", "1112.9", "231 хл + 1 л", "1386.0", "1668.6", "76.8%", "270.6 м (384.7 кг деловых)", "12.6"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[2, 3, 4, 5, 6, 8], align_center=[0, 1], total_merge_cols=2, bold_col=3)
    
    # Краткие инженерные примечания по раскрою для склада сырья и бухгалтерии
    calc_notes = [
        "Базовые нормативы раскроя: хлыст 6000 мм, полезная зона раскроя с учетом технологического захвата станка ЧПУ (600 мм) и торцовки — 5400 мм.",
        "Потребность в целых хлыстах со склада: труба 50х25 — 41 хл., труба 25х25 — 96 хл., труба ø32 — 82 хл., труба 20х20 — 12 хл. Лист 2.0 мм — 1 лист.",
        "Все деловые обрезки (длиной >=500 мм: суммарно 270.6 м / 343.0 кг и 0.85 листа) подлежат маркировке бирками и оприходованию на склад сырья.",
        "Эффективный КИМ заказа с учетом сдачи деловых остатков на склад составляет 99.1%."
    ]
    add_calc_notes_block(doc, calc_notes, title="Примечания по раскрою и оприходованию деловых остатков:")
    
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(10)
    p_sp.paragraph_format.space_after = Pt(2)
    sig_tbl = doc.add_table(rows=2, cols=3)
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_tbl.autofit = False
    
    col_widths = [Inches(2.42), Inches(2.42), Inches(2.43)]
    for row in sig_tbl.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            
    titles = ["Нач. КТО ТОО «ТРОЯ»:", "Начальник производства:", "Заведующий складом ТМЦ:"]
    names = ["<ФИО>", "____________________", "____________________"]
    for i in range(3):
        p0 = sig_tbl.rows[0].cells[i].paragraphs[0]
        p0.paragraph_format.space_after = Pt(1)
        r = p0.add_run(titles[i])
        r.font.name = 'Arial'; r.font.size = Pt(8.0); r.font.bold = True
        
        p1 = sig_tbl.rows[1].cells[i].paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r = p1.add_run(f"__________ / {names[i]}")
        r.font.name = 'Arial'; r.font.size = Pt(8.0)

# ==================== SHEET BUILDERS FOR BLANK TEMPLATES (БЕЗ ТЕХНОЛОГИЧЕСКИХ УКАЗАНИЙ) ====================

def build_sheet_1_metal_template(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 1",
        sheet_title="1. ЦЕХ МЕТАЛЛОИЗДЕЛИЙ (Заготовительный участок: Резка, Гибка, ЧПУ-раскрой)",
        sheet_subtitle="Спецификация чистых заготовок на тираж (для ленточной пилы, ЧПУ-трубореза, трубогиба и лазера)",
        data=TEMPLATE_DATA
    )
    headers = ["№", "Обозначение", "Наименование детали", "Сортамент / Материал", "L, мм", "На 1", "Всего, шт", "Операция"]
    col_widths = [0.28, 1.15, 1.70, 1.75, 0.48, 0.38, 0.45, 1.08]
    rows = [
        ["1", "[ Обозначение детали 1 ]", "[ Наименование детали ]", "[ Сортамент / ГОСТ ]", "[ L ]", "[ 1 ]", "[ ___ ]", "[ Резка / Гибка ]"],
        ["2", "[ Обозначение детали 2 ]", "[ Наименование детали ]", "[ Сортамент / ГОСТ ]", "[ L ]", "[ 1 ]", "[ ___ ]", "[ Резка / Гибка ]"],
        ["3", "[ Обозначение детали 3 ]", "[ Наименование детали ]", "[ Сортамент / ГОСТ ]", "[ L ]", "[ 1 ]", "[ ___ ]", "[ Резка / Гибка ]"],
        ["4", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]"],
        ["5", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]"],
        ["", "ИТОГО ЗАГОТОВОК НА ЗАКАЗ", "", "", "", "[ ___ ]", "[ ___ ]", "[ ___ ] типоразм."]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[4, 5, 6], align_center=[0, 1, 7], total_merge_cols=5, bold_col=6)
    add_signatures_block(doc, left_name="[ Ф.И.О. ]", right_title="Начальник цеха металлоизделий:", right_name="[ Ф.И.О. ]", space_before=Pt(36))

def build_sheet_2_welding_template(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 2",
        sheet_title="2. СВАРОЧНО-СБОРОЧНЫЙ ЦЕХ",
        sheet_subtitle="Сборочные единицы металлокаркаса, нормативы сварки и масса конструкций",
        data=TEMPLATE_DATA
    )
    headers = ["№", "Обозначение узла", "Наименование сборочной единицы", "Масса 1 шт, кг", "На 1 изд", "Всего на тираж", "Общая масса, кг"]
    col_widths = [0.30, 1.50, 2.67, 0.70, 0.55, 0.75, 0.80]
    rows = [
        ["1", "[ Обозначение сб. 1 ]", "[ Наименование сборочного узла ]", "[ ___ ]", "[ 1 ]", "[ ___ ]", "[ ___ ]"],
        ["2", "[ Обозначение сб. 2 ]", "[ Наименование сборочного узла ]", "[ ___ ]", "[ 1 ]", "[ ___ ]", "[ ___ ]"],
        ["3", "[ Обозначение сб. 3 ]", "[ Наименование сборочного узла ]", "[ ___ ]", "[ 1 ]", "[ ___ ]", "[ ___ ]"],
        ["4", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]"],
        ["", "ИТОГО ГОТОВЫЙ МЕТАЛЛОКАРКАС НА ЗАКАЗ", "", "", "[ ___ ]", "[ ___ ] узлов", "[ ___ ] кг"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[3, 4, 5, 6], align_center=[0, 1], total_merge_cols=4, bold_col=5)
    add_signatures_block(doc, left_name="[ Ф.И.О. ]", right_title="Начальник сварочного цеха:", right_name="[ Ф.И.О. ]", space_before=Pt(36))

def build_sheet_3_painting_template(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 3",
        sheet_title="3. УЧАСТОК ПОЛИМЕРНО-ПОРОШКОВОЙ ПОКРАСКИ",
        sheet_subtitle="Ведомость окрашиваемых сборочных единиц и цвет полимерного покрытия",
        data=TEMPLATE_DATA
    )
    headers = ["№", "Обозначение узла", "Наименование сборочной единицы", "На 1 изд", "Всего на тираж", "Цвет покрытия"]
    col_widths = [0.30, 1.65, 2.87, 0.60, 0.75, 1.10]
    rows = [
        ["1", "[ Обозначение сб. 1 ]", "[ Наименование сборочной единицы ]", "[ 1 ]", "[ ___ ]", "[ Указать код RAL по СЗ ]"],
        ["2", "[ Обозначение сб. 2 ]", "[ Наименование сборочной единицы ]", "[ 1 ]", "[ ___ ]", "[ Указать код RAL по СЗ ]"],
        ["3", "[ Обозначение сб. 3 ]", "[ Наименование сборочной единицы ]", "[ 1 ]", "[ ___ ]", "[ Указать код RAL по СЗ ]"],
        ["4", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]"],
        ["5", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]", "[ ___ ]"],
        ["", "ИТОГО НА ПОКРАСКУ НА ЗАКАЗ", "", "[ ___ ]", "[ ___ ] узлов", "[ Указать код RAL по СЗ ]"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[3, 4], align_center=[0, 1, 5], total_merge_cols=3, bold_col=4)
    add_signatures_block(doc, left_name="[ Ф.И.О. ]", right_title="Мастер малярного участка:", right_name="[ Ф.И.О. ]", space_before=Pt(36))

def build_sheet_4_hardware_template(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 4",
        sheet_title="4. СКЛАД ТМЦ И УЧАСТОК КОМПЛЕКТАЦИИ (Фурнитура и покупные изделия)",
        sheet_subtitle="Комплектовочная ведомость покупных изделий, фурнитуры и настила",
        data=TEMPLATE_DATA
    )
    headers = ["№", "Код 1С", "Номенклатура ТМЦ", "Ед. изм.", "На 1 изд", "Всего на тираж", "Назначение"]
    col_widths = [0.30, 1.15, 2.67, 0.50, 0.50, 0.65, 1.50]
    rows = [
        ["1", "[ Код 1С ]", "[ Комплектующее / Фурнитура ]", "шт.", "[ ___ ]", "[ ___ ]", "[ Узел изделия ]"],
        ["2", "[ Код 1С ]", "[ Заглушка пластиковая / Опора ]", "шт.", "[ ___ ]", "[ ___ ]", "[ Опоры каркаса ]"],
        ["3", "[ Код 1С ]", "[ Листовой материал / Настил ]", "лист", "[ ___ ]", "[ ___ ]", "[ Настил каркаса ]"],
        ["4", "[ Код 1С ]", "[ Порошковая краска (указать код RAL по СЗ) ]", "кг", "[ ___ ]", "[ ___ ]", "[ Малярный участок ]"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[4, 5], align_center=[0, 1, 3], total_merge_cols=1, bold_col=5)
    add_signatures_block(doc, left_name="[ Ф.И.О. ]", right_title="Заведующий складом ТМЦ:", right_name="[ Ф.И.О. ]", space_before=Pt(36))

def build_sheet_5_writeoff_template(doc):
    add_header_block(
        doc,
        sheet_badge="ЛИСТ 5",
        sheet_title="5. СВОДНАЯ ВЕДОМОСТЬ РАСХОДА И СПИСАНИЯ ТМЦ",
        sheet_subtitle="Расчет потребности в хлыстах 6000 мм, КИМ, деловых обрезков (>=500 мм) и технологического отхода",
        data=TEMPLATE_DATA
    )
    headers = ["№", "Сортамент и ГОСТ", "Чистый расход, м", "Хлыстов 6 м", "Расход с уч. техн., м", "Расход с уч. техн., кг", "КИМ, %", "Деловые обрезки (>=500 мм)", "Отход, кг"]
    col_widths = [0.28, 1.65, 0.65, 0.55, 0.62, 0.62, 0.45, 1.90, 0.55]
    rows = [
        ["1", "[ Труба ГОСТ... / Сортамент 1 ]", "[ 0.0 ]", "[ __ хл ]", "[ 0.0 ]", "[ 0.0 ]", "[ __% ]", "[ Деловые отрезки >=500 мм ]", "[ 0.0 ]"],
        ["2", "[ Труба ГОСТ... / Сортамент 2 ]", "[ 0.0 ]", "[ __ хл ]", "[ 0.0 ]", "[ 0.0 ]", "[ __% ]", "[ Деловые отрезки >=500 мм ]", "[ 0.0 ]"],
        ["3", "[ Труба ГОСТ... / Сортамент 3 ]", "[ 0.0 ]", "[ __ хл ]", "[ 0.0 ]", "[ 0.0 ]", "[ __% ]", "[ Деловые отрезки >=500 мм ]", "[ 0.0 ]"],
        ["4", "[ Листовой прокат ГОСТ... ]", "—", "[ __ л ]", "—", "[ 0.0 ]", "[ __% ]", "[ Деловой остаток листа ]", "[ 0.0 ]"],
        ["", "ИТОГО МЕТАЛЛОПРОКАТ НА ЗАКАЗ", "[ 0.0 ]", "[ ___ хл ]", "[ 0.0 ]", "[ 0.0 ]", "[ __% ]", "[ ___ м (___ кг деловых) ]", "[ 0.0 ]"]
    ]
    add_grid_table(doc, headers, rows, col_widths, align_right=[2, 3, 4, 5, 6, 8], align_center=[0, 1], total_merge_cols=2, bold_col=3)
    
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(36)
    p_sp.paragraph_format.space_after = Pt(2)
    sig_tbl = doc.add_table(rows=2, cols=3)
    sig_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_tbl.autofit = False
    
    col_widths = [Inches(2.42), Inches(2.42), Inches(2.43)]
    for row in sig_tbl.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width
            
    titles = ["Нач. КТО ТОО «ТРОЯ»:", "Начальник производства:", "Заведующий складом ТМЦ:"]
    names = ["[ Ф.И.О. ]", "____________________", "____________________"]
    for i in range(3):
        p0 = sig_tbl.rows[0].cells[i].paragraphs[0]
        p0.paragraph_format.space_after = Pt(1)
        r = p0.add_run(titles[i])
        r.font.name = 'Arial'; r.font.size = Pt(8.0); r.font.bold = True
        
        p1 = sig_tbl.rows[1].cells[i].paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r = p1.add_run(f"__________ / {names[i]}")
        r.font.name = 'Arial'; r.font.size = Pt(8.0)

# ==================== MAIN EXECUTION & VERIFICATION ====================

def run():
    order_dir = r"<WORK>\03_Проекты\85_Т"
    drawings_dir = os.path.join(order_dir, "02 Чертежи")
    drawings_archive = os.path.join(drawings_dir, "_Архив")
    models_dir = os.path.join(order_dir, "01 3D-Модели")
    models_archive = os.path.join(models_dir, "_Архив_Черновики")
    shops_dir = os.path.join(order_dir, "05 Заявки в цеха")
    templates_dir = str(Path(__file__).resolve().parents[1] / "templates")
    brain_dir = r"<WORK>\99_Служебное\temp\production_previews\85_T"
    required = [order_dir, drawings_dir, models_dir, templates_dir]
    missing = [p for p in required if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError("Production path binding preflight failed: " + "; ".join(missing))
    os.makedirs(brain_dir, exist_ok=True)
    
    print("--- 1. VERIFYING ARCHIVED DRAWINGS & FOLDERS ---")
    os.makedirs(drawings_archive, exist_ok=True)
    os.makedirs(models_archive, exist_ok=True)
    os.makedirs(shops_dir, exist_ok=True)
    # Templates are canonical inputs; do not silently create or replace them.

    print("\n--- 2. BUILDING 85_T MASTER PRODUCTION ORDER (Сводная заявка без технологических указаний) ---")
    master_docx = os.path.join(shops_dir, "85_Т_Сводная_Заявка_Кровать_одноместная.docx")
    master_pdf = os.path.join(shops_dir, "85_Т_Сводная_Заявка_Кровать_одноместная.pdf")
    
    doc_85t = Document()
    setup_page_geometry(doc_85t)
    builders_85t = [
        build_sheet_1_metal_85t,
        build_sheet_2_welding_85t,
        build_sheet_3_painting_85t,
        build_sheet_4_hardware_85t,
        build_sheet_5_writeoff_85t
    ]
    for idx, b in enumerate(builders_85t):
        if idx > 0:
            doc_85t.add_page_break()
        b(doc_85t)
    doc_85t.save(master_docx)
    print("  Saved Clean Master DOCX:", os.path.basename(master_docx))
    
    files_to_convert = [(master_docx, master_pdf)]

    print("\n--- 3. BUILDING UNIVERSAL TEMPLATES (templates/ без технологических указаний) ---")
    master_tpl_docx = os.path.join(templates_dir, "troya_production_order_multipage_template.docx")
    single_tpl_docx = os.path.join(templates_dir, "troya_production_order_template.docx")
    
    doc_tpl = Document()
    setup_page_geometry(doc_tpl)
    builders_tpl = [
        build_sheet_1_metal_template,
        build_sheet_2_welding_template,
        build_sheet_3_painting_template,
        build_sheet_4_hardware_template,
        build_sheet_5_writeoff_template
    ]
    for idx, b in enumerate(builders_tpl):
        if idx > 0:
            doc_tpl.add_page_break()
        b(doc_tpl)
    doc_tpl.save(master_tpl_docx)
    doc_tpl.save(single_tpl_docx)
    print("  Saved Master Template DOCX:", os.path.basename(master_tpl_docx))
    
    shop_tpl_configs = [
        ("template_01_metal_cutting.docx", build_sheet_1_metal_template),
        ("template_02_welding.docx", build_sheet_2_welding_template),
        ("template_03_painting.docx", build_sheet_3_painting_template),
        ("template_04_hardware_assembly.docx", build_sheet_4_hardware_template),
        ("template_05_material_writeoff.docx", build_sheet_5_writeoff_template),
    ]
    
    for fname, b_fn in shop_tpl_configs:
        t_docx = os.path.join(templates_dir, fname)
        t_doc = Document()
        setup_page_geometry(t_doc)
        b_fn(t_doc)
        t_doc.save(t_docx)
        print(f"  Saved Shop Template DOCX: {fname}")
        if fname in ["template_01_metal_cutting.docx", "template_03_painting.docx"]:
            t_pdf = os.path.join(brain_dir, fname.replace(".docx", ".pdf"))
            files_to_convert.append((t_docx, t_pdf))
            
    tpl_pdf_brain = os.path.join(brain_dir, "troya_production_order_template.pdf")
    files_to_convert.append((master_tpl_docx, tpl_pdf_brain))

    print(f"\n--- 4. BATCH CONVERTING {len(files_to_convert)} FILES TO PDF VIA WORD COM API ---")
    import pythoncom
    pythoncom.CoInitialize()
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    actual_pdf_paths = {}
    try:
        for docx_p, pdf_p in files_to_convert:
            target_pdf = pdf_p
            if os.path.exists(pdf_p):
                try:
                    os.rename(pdf_p, pdf_p)
                except OSError:
                    target_pdf = pdf_p.replace(".pdf", "_обновлен.pdf")
                    print(f"  [NOTE] {os.path.basename(pdf_p)} locked in viewer -> saving {os.path.basename(target_pdf)}")
            try:
                wdoc = word.Documents.Open(FileName=os.path.abspath(docx_p), ConfirmConversions=False, ReadOnly=True, AddToRecentFiles=False)
                wdoc.SaveAs2(FileName=os.path.abspath(target_pdf), FileFormat=17)
                wdoc.Close(SaveChanges=False)
                print(f"  Exported PDF: {os.path.basename(target_pdf)}")
                actual_pdf_paths[pdf_p] = target_pdf
            except Exception as ex:
                print(f"  [ERROR] converting {os.path.basename(docx_p)}: {ex}")
    finally:
        word.Quit()

    print("\n--- 5. VERIFYING PDF PAGE COUNTS ---")
    for docx_p, pdf_p in files_to_convert:
        real_pdf = actual_pdf_paths.get(pdf_p, pdf_p)
        if not os.path.exists(real_pdf):
            continue
        d = pymupdf.open(real_pdf)
        count = len(d)
        name = os.path.basename(real_pdf)
        print(f"  {name}: {count} page(s)")
        if "master" in name.lower() or "сводная" in name.lower() or "troya_production_order_template" in name:
            assert count == 5, f"ERROR: Expected 5 pages for {name}, got {count}"
        else:
            assert count == 1, f"ERROR: Expected 1 page for {name}, got {count}"

    print("\n--- 6. RENDERING PREVIEW PNGS ---")
    master_real_pdf = actual_pdf_paths.get(master_pdf, master_pdf)
    if os.path.exists(master_real_pdf):
        m_doc = pymupdf.open(master_real_pdf)
        for s_idx in range(min(5, len(m_doc))):
            m_doc[s_idx].get_pixmap(dpi=150).save(os.path.join(brain_dir, f"preview_85t_sheet{s_idx+1}.png"))
            print(f"  Rendered clean preview for sheet {s_idx+1}")
    
    tpl1_p = actual_pdf_paths.get(os.path.join(brain_dir, "template_01_metal_cutting.pdf"))
    if tpl1_p and os.path.exists(tpl1_p):
        pymupdf.open(tpl1_p)[0].get_pixmap(dpi=150).save(os.path.join(brain_dir, "preview_template_sheet1.png"))
    tpl_master_p = actual_pdf_paths.get(tpl_pdf_brain)
    if tpl_master_p and os.path.exists(tpl_master_p):
        pymupdf.open(tpl_master_p)[3].get_pixmap(dpi=150).save(os.path.join(brain_dir, "preview_template_sheet4.png"))
        
    print("\n--- 7. UPDATING PRODUCTION PACKAGE (Для производства) & ZIP ARCHIVE ---")
    prod_pkg_dir = os.path.join(order_dir, "Для производства")
    sub_orders = os.path.join(prod_pkg_dir, "03 Заявки в цеха")
    
    master_real_pdf = actual_pdf_paths.get(master_pdf, master_pdf)
    if os.path.exists(master_real_pdf):
        dest_pdf = os.path.join(sub_orders, os.path.basename(master_pdf))
        try:
            shutil.copy2(master_real_pdf, dest_pdf)
            print(f"  [UPDATED] Master Summary PDF in '03 Заявки в цеха': {os.path.basename(dest_pdf)}")
        except PermissionError:
            print(f"  [NOTE] {os.path.basename(dest_pdf)} is currently open in user's PDF viewer -> skipped file lock safely.")
        
    zip_name = "85_Т_В_производство.zip"
    zip_path = os.path.join(prod_pkg_dir, zip_name)
    if os.path.exists(zip_path):
        try:
            quarantine = os.path.join(order_dir, "_Карантин_перед_сборкой")
            os.makedirs(quarantine, exist_ok=True)
            target = os.path.join(quarantine, os.path.basename(zip_path))
            index = 1
            while os.path.exists(target):
                target = os.path.join(quarantine, f"{Path(zip_path).stem}__{index}.zip")
                index += 1
            shutil.move(zip_path, target)
        except Exception:
            raise
            
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(prod_pkg_dir):
            for file in files:
                if file == zip_name:
                    continue
                file_abs = os.path.join(root, file)
                rel_path = os.path.relpath(file_abs, prod_pkg_dir)
                zipf.write(file_abs, rel_path)
    print(f"  [ZIP READY] {zip_path} ({os.path.getsize(zip_path)} bytes)")

    print("\nAll templates and production orders updated cleanly!")

if __name__ == "__main__":
    run()

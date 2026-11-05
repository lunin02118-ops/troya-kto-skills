# -*- coding: utf-8 -*-
"""Сборка паспорта (ПС/РЭ) на основе шаблона TROYA (templates\Шаблон_паспорта_TROYA.docx, из «Паспорт стул Nomad.docx»).

Обложка (рамки с адресами, логотип TROYA, рамка «г. Павлодар / год») берётся
из шаблона без изменений, остальное тело документа формируется заново
в оформлении шаблона: Times New Roman 11 пт, A5, заголовки 12 пт полужирные.

Разметка в тексте:
  **текст**  — полужирный;
  [[текст]]  — жёлтая заливка: значение требует подтверждения конструктором.
"""
import copy
import math
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips, RGBColor, Cm
from PIL import Image

FONT = "Times New Roman"
TEXT_W = 6600          # ширина полосы набора A5 с корешком, twips
REV_TAB = 3000         # табулятор редакции в колонтитуле: правее самого длинного обозначения «… ПС»
COVER_LAST = 17        # последний элемент обложки в шаблоне (рамка «г. Павлодар»)
IMAGE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
TEXT_H = 10547         # высота полосы набора A5 (11907 − поля 680 + 680), twips
KEEP_SHORT = TEXT_H // 2          # таблица ниже половины полосы не разрывается между страницами
KEEP_WHOLE = int(TEXT_H * 0.85)   # то же для table(whole=True) — комплектность

TOKEN = re.compile(r"(\*\*.+?\*\*|\[\[.+?\]\])")
MARKS = re.compile(r"\*\*|\[\[|\]\]")


def _lang(rpr, val="ru-RU"):
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:val"), val)


def _fonts(run):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    rfonts.set(qn("w:cs"), FONT)
    rfonts.set(qn("w:eastAsia"), FONT)
    _lang(rpr)


class Passport:
    def __init__(self, template):
        self.doc = Document(template)
        self.body = self.doc.element.body
        self.sec_no = 0
        self.item_no = 0
        self.fig_no = 0
        self._strip_template()

    # ------------------------------------------------------------ шаблон
    def _strip_template(self):
        els = list(self.body)
        for el in els[COVER_LAST + 1:]:
            if el.tag != qn("w:sectPr"):
                self.body.remove(el)

    def _cleanup_images(self):
        part = self.doc.part
        xml = self.body.xml
        for rid, rel in list(part.rels.items()):
            if rel.reltype == IMAGE_REL and f'"{rid}"' not in xml:
                part.drop_rel(rid)

    @staticmethod
    def _set_runs(p_el, text):
        runs = p_el.findall(qn("w:r"))
        first = runs[0]
        for r in runs[1:]:
            p_el.remove(r)
        for t in first.findall(qn("w:t")):
            first.remove(t)
        rpr = first.find(qn("w:rPr"))
        if rpr is not None:
            _lang(rpr)
        p_el.remove(first)
        for chunk in TOKEN.split(text):
            if not chunk:
                continue
            hl = chunk.startswith("[[") and chunk.endswith("]]")
            if hl:
                chunk = chunk[2:-2]
            r = copy.deepcopy(first)
            if hl:
                rp = r.find(qn("w:rPr"))
                h = OxmlElement("w:highlight")
                h.set(qn("w:val"), "yellow")
                lang = rp.find(qn("w:lang"))
                lang.addprevious(h)
            t = OxmlElement("w:t")
            t.text = chunk
            t.set(qn("xml:space"), "preserve")
            r.append(t)
            p_el.append(r)

    def cover(self, line1, line2, code, year="2026", picture_note="Место для изображения изделия", picture=None):
        els = list(self.body)
        self._set_runs(els[8], line1)
        if line2:
            self._set_runs(els[9], line2)
        else:
            self.body.remove(els[9])
        self._set_runs(els[10], code)
        # год в нижней рамке обложки
        ts = els[COVER_LAST].findall(".//" + qn("w:t"))
        for i, t in enumerate(ts):
            if t.text == "202" and i + 1 < len(ts) and ts[i + 1].text and ts[i + 1].text[0].isdigit():
                ts[i + 1].text = year[-1] + ts[i + 1].text[1:]
        # изображение изделия (PNG из figures\out) или рамка-заполнитель
        pic_p = els[12]
        if picture:
            new = self.picture(picture, 6.7)
            new.paragraph_format.keep_with_next = False
            pic_p.addprevious(new._p)
        else:
            tbl = self._placeholder_table(picture_note, "Изображение изделия (3D-вид)", Cm(5.6), width=3800)
            pic_p.addprevious(tbl)
        self.body.remove(pic_p)

    # ------------------------------------------------------------ абзацы
    def _p(self, align="both", first=567, left=0, before=0, after=0, keep=False):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = 1.0
        if first:
            pf.first_line_indent = Twips(first)
        if left:
            pf.left_indent = Twips(left)
        pf.alignment = {
            "both": WD_ALIGN_PARAGRAPH.JUSTIFY,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
        }[align]
        pf.keep_with_next = keep
        pf.widow_control = True          # запрет висячих строк: не менее двух строк абзаца на странице
        return p

    @staticmethod
    def _rich(p, text, size=11, bold=False, italic=False, color=None):
        for chunk in TOKEN.split(text):
            if not chunk:
                continue
            b, hl = bold, False
            if chunk.startswith("**") and chunk.endswith("**"):
                inner = chunk[2:-2]
                if "[[" in inner:
                    Passport._rich(p, inner, size=size, bold=True, italic=italic, color=color)
                    continue
                chunk, b = inner, True
            elif chunk.startswith("[[") and chunk.endswith("]]"):
                chunk, hl = chunk[2:-2], True
            run = p.add_run(chunk)
            _fonts(run)
            run.font.size = Pt(size)
            run.font.bold = b
            run.font.italic = italic
            if color:
                run.font.color.rgb = RGBColor.from_string(color)
            if hl:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        return p

    def text(self, text, size=11, align="both", first=567, bold=False, italic=False, before=0, after=0, keep=False):
        p = self._p(align=align, first=first, before=before, after=after, keep=keep)
        return self._rich(p, text, size=size, bold=bold, italic=italic)

    def blank(self, size=6):
        p = self._p(first=0)
        r = p.add_run("")
        _fonts(r)
        r.font.size = Pt(size)
        return p

    def section(self, title):
        self.sec_no += 1
        self.item_no = 0
        p = self._p(align="center", first=0, before=12, after=6, keep=True)
        self._rich(p, f"{self.sec_no}. {title.upper()}", size=12, bold=True)
        return p

    def subsection(self, title):
        self.item_no += 1
        p = self._p(align="left", first=426, before=4, after=2, keep=True)
        self._rich(p, f"{self.sec_no}.{self.item_no}. {title}", bold=True)
        return p

    def item(self, text, keep=False):
        """Нумерованный пункт раздела: «5.3. Текст»."""
        self.item_no += 1
        p = self._p(first=426, keep=keep)
        return self._rich(p, f"{self.sec_no}.{self.item_no}. {text}")

    def dash(self, text):
        p = self._p(first=0, left=284)
        p.paragraph_format.first_line_indent = Twips(-198)
        p.paragraph_format.left_indent = Twips(482)
        return self._rich(p, "– " + text)

    def page_break(self):
        p = self._p(first=0)
        p.add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------ таблицы
    @staticmethod
    def _cell_text(cell, text, size=10, bold=False, align="left"):
        cell.text = ""
        p = cell.paragraphs[0]
        pf = p.paragraph_format
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)
        pf.line_spacing = 1.0
        pf.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
                        "both": WD_ALIGN_PARAGRAPH.JUSTIFY}[align]
        Passport._rich(p, text, size=size, bold=bold)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    @staticmethod
    def _fix_widths(table, widths):
        tbl = table._tbl
        tblPr = tbl.tblPr
        for tag in ("w:tblW", "w:tblLayout"):
            old = tblPr.find(qn(tag))
            if old is not None:
                tblPr.remove(old)
        tblW = OxmlElement("w:tblW")
        tblW.set(qn("w:w"), str(sum(widths)))
        tblW.set(qn("w:type"), "dxa")
        tblPr.append(tblW)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tblPr.append(layout)
        grid = tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(w))
        for row in table.rows:
            for cell, w in zip(row.cells, widths):
                cell.width = Twips(w)

    @staticmethod
    def _row_h(row, widths, size):
        """Оценка высоты строки таблицы, twips: строки самой длинной ячейки × интерлиньяж (Times New Roman)."""
        char_w = size * 9.6
        lines = max(max(1, math.ceil(len(MARKS.sub("", v)) * char_w * 1.1 / (w - 216))) for v, w in zip(row, widths))
        return lines * size * 23 + 30

    @staticmethod
    def _keep_row(row):
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True

    def table(self, header, rows, widths, align=None, header_size=10, size=10, repeat_header=True, long_left=999,
              whole=False, keep_next=False):
        """Таблица. Переносы: таблица ниже KEEP_SHORT (whole=True — ниже KEEP_WHOLE) держится целиком на одной
        странице; у длинной таблицы внизу страницы остаётся не менее трёх строк с заголовком, на новую страницу
        переносится не менее трёх. keep_next — последняя строка держится со следующим абзацем (примечания)."""
        align = align or ["left"] * len(widths)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(widths), style="Table Grid")
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            self._cell_text(t.rows[0].cells[i], h, size=header_size, bold=True, align="center")
        if repeat_header:
            trPr = t.rows[0]._tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader")
            trPr.append(th)
        for r, row in enumerate(rows, start=1):
            for c, val in enumerate(row):
                a = align[c]
                if a == "center" and len(val) > long_left:
                    a = "left"
                self._cell_text(t.rows[r].cells[c], val, size=size, align=a)
            # строка таблицы не разрывается между страницами
            trPr = t.rows[r]._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit")
            trPr.append(cs)
        self._fix_widths(t, widths)
        n = len(rows)
        if sum(self._row_h(r, widths, size) for r in [header] + rows) <= (KEEP_WHOLE if whole else KEEP_SHORT):
            keep = range(n)
        else:
            keep = set(range(min(3, n))) | set(range(max(n - 2, 0), n))
        for i in keep:
            self._keep_row(t.rows[i])
        if keep_next:
            self._keep_row(t.rows[n])
        self.blank(4).paragraph_format.keep_with_next = keep_next
        return t

    def _placeholder_table(self, title, note, height, width=TEXT_W - 400):
        t = self.doc.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl = t._tbl
        tblPr = tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for side in ("top", "left", "bottom", "right"):
            b = OxmlElement(f"w:{side}")
            b.set(qn("w:val"), "dashed")
            b.set(qn("w:sz"), "6")
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), "8C8C8C")
            borders.append(b)
        tblPr.append(borders)
        row = t.rows[0]
        row.height = height
        row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
        cell = row.cells[0]
        self._cell_text(cell, title, size=10, bold=True, align="center")
        p2 = cell.add_paragraph()
        p2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(0)
        self._rich(p2, note, size=9, italic=True, color="7F7F7F")
        for p in cell.paragraphs[:1]:
            for r in p.runs:
                r.font.color.rgb = RGBColor.from_string("7F7F7F")
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "F7F7F7")
        tcPr.append(shd)
        self._fix_widths(t, [width])
        el = tbl
        el.getparent().remove(el)
        return el

    def picture(self, path, width_cm, align="center"):
        """Абзац с рисунком PNG заданной ширины (не шире полосы набора)."""
        p = self._p(align=align, first=0, keep=True)
        p.add_run().add_picture(path, width=Cm(min(width_cm, TEXT_W / 567.0)))
        return p

    def figure(self, caption, note, height_cm=5.5, image=None):
        """Рисунок (PNG) или место под рисунок/схему + подпись «Рисунок N – ...» по ГОСТ 2.105."""
        self.fig_no += 1
        if image:
            with Image.open(image) as im:
                w_cm = im.width / im.info.get("dpi", (300, 300))[0] * 2.54
            self.picture(image, w_cm)
        else:
            p = self._p(first=0, keep=True)
            p._p.addnext(self._placeholder_table("МЕСТО ДЛЯ РИСУНКА (СХЕМЫ)", note, Cm(height_cm)))
            # пустой абзац-якорь удаляем: таблица стоит на его месте
            self.body.remove(p._p)
        cap = self._p(align="center", first=0, before=3, after=6)
        self._rich(cap, f"Рисунок {self.fig_no} – {caption}", size=10)
        return self.fig_no

    def form(self, text, before=4, size=11, keep=False):
        """Строка бланка (с полями «____»): без выравнивания по ширине."""
        return self.text(text, size=size, align="left", first=0, before=before, keep=keep)

    def signatures(self, label, fields, label_w=1700, keep_next=False):
        """Блок подписи: «Метка: ____ ____ ____» с подписями полей мелким шрифтом."""
        gap = 150
        cols = []
        for cap, w in fields:
            cols += [(cap, w - gap), (None, gap)]
        cols = cols[:-1]
        widths = [label_w] + [w for _, w in cols]
        widths[-1] += gap
        t = self.doc.add_table(rows=2, cols=len(widths))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        self._cell_text(t.rows[0].cells[0], label, size=10, align="left")
        t.rows[0].cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
        t.rows[0].height = Cm(0.8)
        for i, (cap, _) in enumerate(cols, start=1):
            top = t.rows[0].cells[i]
            self._cell_text(top, "", size=11)
            if cap is None:
                self._cell_text(t.rows[1].cells[i], "", size=6)
                continue
            tcPr = top._tc.get_or_add_tcPr()
            b = OxmlElement("w:tcBorders")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "0")
            bottom.set(qn("w:color"), "000000")
            b.append(bottom)
            tcPr.append(b)
            self._cell_text(t.rows[1].cells[i], cap, size=8, align="center")
            for r in t.rows[1].cells[i].paragraphs[0].runs:
                r.font.italic = True
        self._cell_text(t.rows[1].cells[0], "", size=6)
        self._fix_widths(t, widths)
        # блок подписи не разрывается и держится с предыдущим абзацем
        for row in t.rows:
            row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for c in t.rows[0].cells:
            c.paragraphs[0].paragraph_format.keep_with_next = True
        if keep_next:
            self._keep_row(t.rows[1])
        prev = t._tbl.getprevious()
        if prev is not None and prev.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            Paragraph(prev, self.doc._body).paragraph_format.keep_with_next = True
        return t

    def keep_together(self, p):
        p.paragraph_format.keep_together = True
        return p

    # ------------------------------------------------------------ колонтитул
    @staticmethod
    def _footer_run(text=None, tab=False):
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        for a in ("w:ascii", "w:hAnsi", "w:cs"):
            rf.set(qn(a), FONT)
        rpr.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "20")
        rpr.append(sz)
        r.append(rpr)
        if tab:
            r.append(OxmlElement("w:tab"))
        if text is not None:
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = text
            r.append(t)
        return r

    def page_numbers(self, doc_code=None, rev=None):
        """Нижний колонтитул (кроме обложки): номер страницы; с doc_code — «обозначение документа … номер»
        над тонкой линией по ширине полосы набора; rev — «Ред. N от дата» на табуляторе REV_TAB."""
        sec = self.doc.sections[0]
        sec.different_first_page_header_footer = True
        sec.footer_distance = Twips(340)
        p = sec.footer.paragraphs[0]
        if doc_code:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            if rev:
                p.paragraph_format.tab_stops.add_tab_stop(Twips(REV_TAB))
            p.paragraph_format.tab_stops.add_tab_stop(Twips(TEXT_W), 2)      # 2 = по правому краю
            pbdr = OxmlElement("w:pBdr")
            top = OxmlElement("w:top")
            for k, v in (("w:val", "single"), ("w:sz", "4"), ("w:space", "1"), ("w:color", "auto")):
                top.set(qn(k), v)
            pbdr.append(top)
            # порядок CT_PPr: pBdr раньше shd/tabs/spacing/ind/jc
            p._p.get_or_add_pPr().insert_element_before(
                pbdr, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:spacing", "w:ind", "w:jc", "w:rPr")
            p._p.append(self._footer_run(doc_code))
            if rev:
                p._p.append(self._footer_run(rev, tab=True))
            p._p.append(self._footer_run(tab=True))
        else:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        # поле PAGE из fldChar: шрифт результата берётся из rPr, а fldSimple Word переформатирует
        for kind in ("begin", "instr", "separate", "result", "end"):
            if kind == "result":
                p._p.append(self._footer_run("1"))
                continue
            r = self._footer_run()
            if kind == "instr":
                it = OxmlElement("w:instrText")
                it.set(qn("xml:space"), "preserve")
                it.text = " PAGE "
                r.append(it)
            else:
                fc = OxmlElement("w:fldChar")
                fc.set(qn("w:fldCharType"), kind)
                r.append(fc)
            p._p.append(r)

    def save(self, path, title, doc_code=None, rev=None, standard="ГОСТ 22046-2016"):
        self._cleanup_images()
        self.page_numbers(doc_code, rev)
        cp = self.doc.core_properties
        cp.title = title
        cp.subject = "Паспорт и руководство по эксплуатации"
        cp.keywords = f"ПС/РЭ; ТР ТС 025/2012; {standard}"
        cp.comments = ""
        self.doc.save(path)

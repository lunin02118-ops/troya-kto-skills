# -*- coding: utf-8 -*-
"""Схемы для паспортов (электрические по ГОСТ 2.702 / 2.721 / 2.755, водопроводные по ГОСТ 2.785).
Координаты — в миллиметрах от левого верхнего угла, ось y вниз. Вывод PNG 300 dpi, шрифт ГОСТ тип Б.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def _gost_font():
    """Шрифт ГОСТ тип Б: GOST_BU.ttf (Unicode) в системе или у пользователя; путь можно задать GOST_FONT.
    Без него — Arial с предупреждением (рисунок строится, но шрифт не по ГОСТ 2.304)."""
    cands = [os.environ.get("GOST_FONT"), r"C:\Windows\Fonts\GOST_BU.ttf",
             os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\Fonts\GOST_BU.ttf")]
    for p in cands:
        if p and os.path.exists(p):
            return p
    print("ВНИМАНИЕ: шрифт GOST_BU.ttf не найден, подписи рисунков — Arial", file=sys.stderr)
    return r"C:\Windows\Fonts\arial.ttf"


FONT_B = _gost_font()   # Unicode-версия: в GOST_B.TTF нет Δ, а × ² Ø подменены кириллицей
DPI = 300
SS = 3                      # суперсэмплинг для сглаживания
W_MAIN = 0.35               # линии связи и УГО
W_THIN = 0.25               # рамки устройств, таблицы, выносные линии
DASH = (2.0, 1.2)           # штриховая (механическая связь)
DASH_DOT = (6.0, 1.0, 0.6, 1.0)   # штрихпунктирная тонкая (границы устройств)


class Sheet:
    def __init__(self, w_mm, h_mm):
        self.w, self.h = w_mm, h_mm
        self.k = DPI / 25.4 * SS
        self.img = Image.new("L", (int(w_mm * self.k), int(h_mm * self.k)), 255)
        self.dr = ImageDraw.Draw(self.img)
        self._fonts = {}

    # ------------------------------------------------------------ базовые
    def _p(self, x, y):
        return (x * self.k, y * self.k)

    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(FONT_B, int(size * self.k))
        return self._fonts[size]

    def line(self, pts, w=W_MAIN, dash=None):
        if dash is None:
            px = [self._p(*p) for p in pts]
            self.dr.line(px, fill=0, width=max(1, round(w * self.k)), joint="curve")
            r = w * self.k / 2
            for x, y in px:      # скругление стыков и концов
                self.dr.ellipse((x - r, y - r, x + r, y + r), fill=0)
            return
        for a, b in zip(pts, pts[1:]):
            self._dashed(a, b, w, dash)

    def _dashed(self, a, b, w, pattern):
        L = math.dist(a, b)
        if L == 0:
            return
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        s, i = 0.0, 0
        while s < L:
            seg = pattern[i % len(pattern)]
            if i % 2 == 0:
                e = min(L, s + seg)
                self.line([(a[0] + ux * s, a[1] + uy * s), (a[0] + ux * e, a[1] + uy * e)], w)
            s += seg
            i += 1

    def rect(self, x0, y0, x1, y1, w=W_THIN, dash=None):
        self.line([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], w, dash)

    def dot(self, x, y, d=1.0):
        cx, cy = self._p(x, y)
        r = d / 2 * self.k
        self.dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)

    def ellipse(self, cx, cy, rx, ry, w=W_MAIN):
        x0, y0 = self._p(cx - rx, cy - ry)
        x1, y1 = self._p(cx + rx, cy + ry)
        self.dr.ellipse((x0, y0, x1, y1), outline=0, width=max(1, round(w * self.k)))

    def text(self, x, y, s, size=3.5, anchor="ls"):
        """anchor как в PIL: l/m/r по горизонтали, a/m/s/d по вертикали (s — базовая линия)."""
        self.dr.text(self._p(x, y), s, font=self.font(size), fill=0, anchor=anchor)

    def text_w(self, s, size=3.5):
        return self.font(size).getlength(s) / self.k

    def save(self, path):
        img = self.img.resize((int(self.w * DPI / 25.4), int(self.h * DPI / 25.4)), Image.LANCZOS)
        img.save(path, dpi=(DPI, DPI))
        return path

    # ------------------------------------------------------------ УГО (ГОСТ 2.721, 2.755)
    def breaker_pole(self, x, y, l=6.0, h=3.4):
        """Полюс автоматического выключателя (контакт замыкающий + функция выключателя «×»).
        Ток слева направо: провод подходит в (x, y), неподвижный контакт в (x + l + 1, y).
        Возвращает точку середины ножа — для механической связи."""
        self.line([(x, y), (x + l, y - h)])
        c, a = x + l + 1, 0.7
        self.line([(c - a, y - a), (c + a, y + a)], W_THIN)
        self.line([(c - a, y + a), (c + a, y - a)], W_THIN)
        return (x + l / 2, y - h / 2)

    def socket_down(self, x, y, a=1.3, h=2.4):
        """Гнездо разъёмного соединения (ГОСТ 2.755), провод приходит сверху в вершину (x, y)."""
        self.line([(x - a, y + h), (x, y), (x + a, y + h)])

    def chassis(self, x, y, half=4.0):
        """Соединение с корпусом (ГОСТ 2.721): провод приходит сверху в (x, y)."""
        self.line([(x - half, y), (x + half, y)])
        n = 4
        for i in range(n):
            xs = x - half + 2 * half * (i + 0.5) / n
            self.line([(xs + 0.8, y), (xs - 0.8, y + 1.8)], W_THIN)

    def cable_tick(self, x, y_top, y_bot, label=None):
        """Обозначение жгута (кабеля): наклонная черта через провода и позиционное обозначение."""
        self.line([(x - 1.5, y_bot + 2), (x + 1.5, y_top - 2)], W_THIN)
        if label:
            self.text(x + 2, y_top - 3, label, 3.5)

    # ------------------------------------------------------------ перечень элементов
    def parts_list(self, x0, y0, rows, cols=(18, 72, 12, 12), size=3.0, row_h=5.0):
        """Перечень элементов (упрощённо по ГОСТ 2.701): поз. обозначение, наименование, кол., примечание.
        Длинные наименования переносятся по словам. Возвращает y низа таблицы."""
        head = ("Поз. обозн.", "Наименование", "Кол.", "Прим.")
        xs = [x0]
        for c in cols:
            xs.append(xs[-1] + c)

        def wrap(s, width):
            out, cur = [], ""
            for word in s.split(" "):
                t = (cur + " " + word).strip()
                if self.text_w(t, size) <= width - 2 or not cur:
                    cur = t
                else:
                    out.append(cur)
                    cur = word
            out.append(cur)
            return out

        y = y0
        lines = [y]
        cells = []
        for r, row in enumerate([head] + list(rows)):
            wrapped = [wrap(v, cols[i]) for i, v in enumerate(row)]
            n = max(len(w) for w in wrapped)
            h = row_h + (n - 1) * size * 1.15
            cells.append((y, h, wrapped, r == 0))
            y += h
            lines.append(y)
        for yy in lines:
            self.line([(x0, yy), (xs[-1], yy)], W_THIN if yy not in (lines[0], lines[1], lines[-1]) else W_MAIN)
        for xx in xs:
            self.line([(xx, lines[0]), (xx, lines[-1])], W_MAIN if xx in (xs[0], xs[-1]) else W_THIN)
        for yy, h, wrapped, is_head in cells:
            for i, lines_i in enumerate(wrapped):
                n = len(lines_i)
                top = yy + h / 2 - (n - 1) * size * 1.15 / 2
                for j, s in enumerate(lines_i):
                    cy = top + j * size * 1.15
                    if i == 1 and not is_head:
                        self.text(xs[i] + 1.2, cy, s, size, anchor="lm")
                    else:
                        self.text((xs[i] + xs[i + 1]) / 2, cy, s, size, anchor="mm")
        return lines[-1]

# -*- coding: utf-8 -*-
"""Изометрия по ГОСТ 2.317 (прямоугольная изометрия) для рисунков паспортов: тела из граней,
скрытые грани — алгоритмом художника, линии чёрные, заливка белая, позиции по ГОСТ 2.109.

Оси: x — длина (слева направо), y — глубина (от фронта к задней стенке), z — высота. Размеры в мм.
Наблюдатель спереди-справа-сверху: видны грани фронта (y min), правая (x max) и верх (z max).
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


FONT_B = _gost_font()   # Unicode-версия шрифта ГОСТ тип Б
DPI = 300
SS = 3                      # суперсэмплинг для сглаживания
VIEWS = {"спереди-справа": (1, -1), "спереди-слева": (-1, -1), "сзади-справа": (1, 1), "сзади-слева": (-1, 1)}
W_VIEW = R_AX = S_AX = None


def set_view(name):
    """Направление на наблюдателя (сверху под углом изометрии) и экранные оси."""
    global W_VIEW, R_AX, S_AX
    sx, sy = VIEWS[name]
    W_VIEW = (sx / math.sqrt(3), sy / math.sqrt(3), 1 / math.sqrt(3))
    r = (-W_VIEW[1], W_VIEW[0], 0.0)
    n = math.hypot(r[0], r[1])
    R_AX = (r[0] / n, r[1] / n, 0.0)
    S_AX = cross(W_VIEW, R_AX)




def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def proj(p):
    return dot(p, R_AX), dot(p, S_AX)


set_view("спереди-справа")


class Face:
    def __init__(self, pts, normal, pattern=None, sil=None):
        self.pts = pts
        self.normal = normal
        self.pattern = pattern      # функция (face) -> список примитивов в 3D
        self.sil = sil              # гладкая грань цилиндра: {(i, j): нормаль соседней грани по ребру i–j}


class Solid:
    def __init__(self, faces, name="", line=1.0):
        self.faces = faces
        self.name = name
        self.line = line            # множитель толщины контура
        xs = [p[0] for f in faces for p in f.pts]
        ys = [p[1] for f in faces for p in f.pts]
        zs = [p[2] for f in faces for p in f.pts]
        self.bb = (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    def depth(self):
        b = self.bb
        return dot(((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2), W_VIEW)


def translate(solid, v):
    """Копия тела, сдвинутая на вектор v (для разнесённых схем монтажа)."""
    def mv(prim):
        if prim[0] in ("dot", "ring"):
            return (prim[0], add(prim[1], v)) + tuple(prim[2:])
        return ("line", add(prim[1], v), add(prim[2], v))
    faces = [Face([add(p, v) for p in f.pts], f.normal, [mv(q) for q in f.pattern] if f.pattern else None, f.sil)
             for f in solid.faces]
    return Solid(faces, solid.name, solid.line)


def box(x0, y0, z0, x1, y1, z1, name="", patterns=None, line=1.0):
    """patterns: {'front'|'back'|'left'|'right'|'top'|'bottom': функция}."""
    patterns = patterns or {}
    P = lambda x, y, z: (x, y, z)
    faces = [
        Face([P(x0, y0, z0), P(x1, y0, z0), P(x1, y0, z1), P(x0, y0, z1)], (0, -1, 0), patterns.get("front")),
        Face([P(x1, y1, z0), P(x0, y1, z0), P(x0, y1, z1), P(x1, y1, z1)], (0, 1, 0), patterns.get("back")),
        Face([P(x0, y1, z0), P(x0, y0, z0), P(x0, y0, z1), P(x0, y1, z1)], (-1, 0, 0), patterns.get("left")),
        Face([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], (1, 0, 0), patterns.get("right")),
        Face([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], (0, 0, 1), patterns.get("top")),
        Face([P(x0, y1, z0), P(x1, y1, z0), P(x1, y0, z0), P(x0, y0, z0)], (0, 0, -1), patterns.get("bottom")),
    ]
    return Solid(faces, name, line)


def extrude(poly, vec, name="", cap_pattern=None, line=1.0, smooth=False):
    """Призма: плоский многоугольник poly (точки 3D) выдавлен на вектор vec; smooth — боковая поверхность
    цилиндра: рёбра между боковыми гранями обводятся только на очерке."""
    top = [add(p, vec) for p in poly]
    c = tuple(sum(p[i] for p in poly + top) / (2 * len(poly)) for i in range(3))
    faces = []
    n0 = cross(sub(poly[1], poly[0]), sub(poly[2], poly[0]))
    if dot(n0, vec) > 0:
        n0 = (-n0[0], -n0[1], -n0[2])
    faces.append(Face(list(poly), n0))
    faces.append(Face(top, (-n0[0], -n0[1], -n0[2]), cap_pattern))
    k = len(poly)
    for i in range(k):
        a, b = poly[i], poly[(i + 1) % k]
        q = [a, b, add(b, vec), add(a, vec)]
        n = cross(sub(b, a), vec)
        m = tuple(sum(p[j] for p in q) / 4 for j in range(3))
        if dot(n, sub(m, c)) < 0:
            n = (-n[0], -n[1], -n[2])
        faces.append(Face(q, n))
    if smooth:
        side = faces[2:]
        for i, f in enumerate(side):
            f.sil = {(1, 2): side[(i + 1) % k].normal, (3, 0): side[i - 1].normal}
    return Solid(faces, name, line)


def rounded_rect(x0, y0, x1, y1, z, r_front=0.0, r_back=0.0, seg=8):
    """Контур прямоугольника в плоскости z со скруглёнными передними (y0) и/или задними углами."""
    pts = []

    def arc(cx, cy, r, a0, a1):
        for i in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))

    if r_front:
        arc(x0 + r_front, y0 + r_front, r_front, 180, 270)
        arc(x1 - r_front, y0 + r_front, r_front, 270, 360)
    else:
        pts += [(x0, y0, z), (x1, y0, z)]
    if r_back:
        arc(x1 - r_back, y1 - r_back, r_back, 0, 90)
        arc(x0 + r_back, y1 - r_back, r_back, 90, 180)
    else:
        pts += [(x1, y1, z), (x0, y1, z)]
    return pts


# ---------- узоры граней (перфорация, жалюзи, контуры)
def ring(center, r, axis="z"):
    """Окружность на грани (контур гнезда розетки, отверстие): axis — нормаль грани."""
    return [("ring", center, r, axis)]


def _ring_pts(prim, n=28):
    (cx, cy, cz), r, axis = prim[1], prim[2], prim[3]
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        u, w = r * math.cos(a), r * math.sin(a)
        out.append({"z": (cx + u, cy + w, cz), "x": (cx, cy + u, cz + w), "y": (cx + u, cy, cz + w)}[axis])
    return out



def holes_grid(u0, v0, u1, v1, step, r, plane):
    """Круглые отверстия на плоской грани. plane(u, v) -> точка 3D."""
    out = []
    nu = int((u1 - u0) // step)
    nv = int((v1 - v0) // step)
    du = (u1 - u0 - nu * step) / 2
    dv = (v1 - v0 - nv * step) / 2
    for i in range(nu + 1):
        for j in range(nv + 1):
            out.append(("dot", plane(u0 + du + i * step, v0 + dv + j * step), r))
    return out


def slots(u0, v0, u1, v1, step, plane):
    """Горизонтальные прорези (жалюзи) на грани."""
    out = []
    v = v0
    while v <= v1:
        out.append(("line", plane(u0, v), plane(u1, v)))
        v += step
    return out


class Drawing:
    def __init__(self, width_mm, height_mm, margin_mm=2.0, view="спереди-справа"):
        self.w_mm, self.h_mm, self.m_mm = width_mm, height_mm, margin_mm
        self.view = view
        self.solids = []
        self.callouts = []      # (pos, anchor3d, (dx_mm, dy_mm)) — смещение подписи от проекции точки
        self.lines3d = []       # дополнительные линии (гофра, провода): список точек 3D
        self.texts = []

    def add(self, *solids):
        self.solids.extend(solids)

    def callout(self, pos, anchor, offset):
        self.callouts.append((str(pos), anchor, offset))

    def polyline(self, pts, dash=False, width=1.0):
        """dash: False — сплошная, True — штриховая (невидимый контур), "dashdot" — штрихпунктирная,
        "phantom" — штрихпунктирная с двумя точками (другое положение детали, ГОСТ 2.303)."""
        self.lines3d.append((pts, dash, width))

    # ----- порядок отрисовки
    def _order(self):
        S = self.solids
        n = len(S)
        eps = 1e-6
        scr = []
        for s in S:
            ps = [proj(p) for f in s.faces for p in f.pts]
            scr.append((min(p[0] for p in ps), min(p[1] for p in ps), max(p[0] for p in ps), max(p[1] for p in ps)))

        def behind(a, b):     # a дальше от наблюдателя, чем b
            A, B = a.bb, b.bb
            for i in range(3):
                if W_VIEW[i] > 0 and A[i + 3] <= B[i] + eps:
                    return True
                if W_VIEW[i] < 0 and A[i] >= B[i + 3] - eps:
                    return True
            return False

        after = {i: set() for i in range(n)}
        indeg = [0] * n
        for i in range(n):
            for j in range(i + 1, n):
                si, sj = scr[i], scr[j]
                if si[2] < sj[0] or sj[2] < si[0] or si[3] < sj[1] or sj[3] < si[1]:
                    continue
                bi, bj = behind(S[i], S[j]), behind(S[j], S[i])
                if bi and bj:       # разделены плоскостями в обе стороны — друг друга не закрывают
                    continue
                if bi and not bj:
                    a, b = i, j
                elif bj and not bi:
                    a, b = j, i
                else:
                    a, b = (i, j) if S[i].depth() <= S[j].depth() else (j, i)
                if b not in after[a]:
                    after[a].add(b)
                    indeg[b] += 1
        order, ready = [], sorted([i for i in range(n) if indeg[i] == 0], key=lambda k: S[k].depth())
        while ready:
            k = ready.pop(0)
            order.append(k)
            for m in after[k]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
            ready.sort(key=lambda q: S[q].depth())
        rest = sorted(set(range(n)) - set(order), key=lambda k: S[k].depth())
        return [S[k] for k in order + rest]

    def render(self, path, line_mm=0.30, palette=None):
        """palette — {имя тела: (R, G, B)}: цветной вид с заливкой и светотенью (для обложки), без позиций."""
        px_mm = DPI / 25.4 * SS
        set_view(self.view)
        callouts = [] if palette else self.callouts
        W, H = int(self.w_mm * px_mm), int(self.h_mm * px_mm)
        pts = [proj(p) for s in self.solids for f in s.faces for p in f.pts]
        pts += [proj(p) for ln in self.lines3d for p in ln[0]]
        minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
        miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
        m = self.m_mm * px_mm
        font = ImageFont.truetype(FONT_B, int(3.5 * px_mm))
        probe = ImageDraw.Draw(Image.new("L", (10, 10)))
        # элементы раскладки: координата модели + неизменяемый в пикселях вынос подписи
        ix = [(minx, 0, 0), (maxx, 0, 0)]
        iy = [(0, 0, 0), (maxy - miny, 0, 0)]
        for pos, a, (dx, dy) in callouts:
            ax, ay = proj(a)
            shelf = max(probe.textlength(pos, font=font) + 1.2 * px_mm, 5 * px_mm)
            ex = dx * px_mm + (-shelf if dx < 0 else shelf)
            ix.append((ax, min(0, ex, dx * px_mm), max(0, ex, dx * px_mm)))
            ey = -dy * px_mm
            iy.append((maxy - ay, min(0, ey - 4.6 * px_mm), max(0, ey)))

        def fit(items, span):
            k = float("inf")
            for xi, loi, hii in items:
                for xj, loj, hij in items:
                    if xj > xi:
                        k = min(k, (span - hij + loi) / (xj - xi))
            lo = min((x - items[0][0]) * k + l for x, l, h in items)
            hi = max((x - items[0][0]) * k + h for x, l, h in items)
            return k, lo, hi

        kx, _, _ = fit(ix, W - 2 * m)
        ky, _, _ = fit(iy, H - 2 * m)
        k = min(kx, ky)
        lo = min((x - minx) * k + l for x, l, h in ix)
        hi = max((x - minx) * k + h for x, l, h in ix)
        ox = m + ((W - 2 * m) - (hi - lo)) / 2 - lo
        lo = min(t * k + l for t, l, h in iy)
        hi = max(t * k + h for t, l, h in iy)
        oy = m + ((H - 2 * m) - (hi - lo)) / 2 - lo

        def T(p3):
            x, y = proj(p3)
            return (ox + (x - minx) * k, oy + (maxy - y) * k)

        mode, white, ink = ("RGB", (255, 255, 255), (70, 70, 70)) if palette else ("L", 255, 0)
        img = Image.new(mode, (W, H), white)
        dr = ImageDraw.Draw(img)
        if palette:
            line_mm *= 0.5
        lw = max(1, int(line_mm * px_mm))
        thin = max(1, int(line_mm * 0.55 * px_mm))
        lv = (W_VIEW[0] - 0.3 * R_AX[0], W_VIEW[1] - 0.3 * R_AX[1], W_VIEW[2] + 0.8)
        ln = math.sqrt(dot(lv, lv))
        lv = (lv[0] / ln, lv[1] / ln, lv[2] / ln)

        def outline(f, poly):
            """Контур грани; у гладкой грани — кромки и рёбра очерка (соседняя грань повёрнута от наблюдателя)."""
            if not f.sil:
                return [poly + [poly[0]]]
            segs = [[poly[0], poly[1]], [poly[2], poly[3]]]
            return segs + [[poly[i], poly[j]] for (i, j), nb in f.sil.items() if dot(nb, W_VIEW) <= 1e-9]

        for s in self._order():
            base = palette.get(s.name, (245, 245, 245)) if palette else None
            for f in s.faces:
                if dot(f.normal, W_VIEW) <= 1e-9:
                    continue
                poly = [T(p) for p in f.pts]
                if palette:
                    nn = math.sqrt(dot(f.normal, f.normal))
                    sh = 0.62 + 0.38 * max(0.0, dot(f.normal, lv) / nn)
                    fill = tuple(int(c * sh) for c in base)
                    dr.polygon(poly, fill=fill)
                    if f.pattern:
                        pd = tuple(int(c * 0.45) for c in fill)
                        for prim in f.pattern:
                            if prim[0] == "dot":
                                c = T(prim[1])
                                rr = prim[2] * k
                                dr.ellipse([c[0] - rr, c[1] - rr * 0.75, c[0] + rr, c[1] + rr * 0.75], fill=pd)
                            elif prim[0] == "ring":
                                q = [T(p) for p in _ring_pts(prim)]
                                dr.line(q + [q[0]], fill=ink, width=thin)
                            else:
                                dr.line([T(prim[1]), T(prim[2])], fill=pd, width=thin)
                    for seg in outline(f, poly):
                        dr.line(seg, fill=ink, width=int(lw * s.line), joint="curve")
                    continue
                dr.polygon(poly, fill=255)
                if f.pattern:
                    layer = Image.new("L", (W, H), 0)
                    mask = Image.new("L", (W, H), 0)
                    ImageDraw.Draw(mask).polygon(poly, fill=255)
                    ld = ImageDraw.Draw(layer)
                    for prim in f.pattern:
                        if prim[0] == "dot":
                            c = T(prim[1])
                            rr = prim[2] * k
                            ld.ellipse([c[0] - rr, c[1] - rr * 0.75, c[0] + rr, c[1] + rr * 0.75], fill=255)
                        elif prim[0] == "ring":
                            q = [T(p) for p in _ring_pts(prim)]
                            ld.line(q + [q[0]], fill=255, width=thin)
                        else:
                            ld.line([T(prim[1]), T(prim[2])], fill=255, width=thin)
                    black = Image.new("L", (W, H), 0)
                    img.paste(black, (0, 0), Image.composite(layer, Image.new("L", (W, H), 0), mask))
                for seg in outline(f, poly):
                    dr.line(seg, fill=0, width=int(lw * s.line), joint="curve")
        for pts3, dash, width in self.lines3d:
            P = [T(p) for p in pts3]
            if dash:
                pat = {"dashdot": (6, 1, 0.6, 1), "phantom": (6, 1, 0.6, 1, 0.6, 1)}.get(dash, (3, 1.5))
                for i in range(len(P) - 1):
                    _dash(dr, P[i], P[i + 1], [q * px_mm for q in pat], max(1, int(lw * width)))
            else:
                dr.line(P, fill=0, width=max(1, int(lw * width)), joint="curve")
        font = ImageFont.truetype(FONT_B, int(3.5 * px_mm))
        for pos, a, (dx, dy) in callouts:
            c = T(a)
            e = (c[0] + dx * px_mm, c[1] - dy * px_mm)
            r = 0.55 * px_mm
            dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=0)
            tw = dr.textlength(pos, font=font)
            shelf = max(tw + 1.2 * px_mm, 5 * px_mm)
            left = dx < 0
            x2 = e[0] - shelf if left else e[0] + shelf
            dr.line([c, e], fill=0, width=thin)
            dr.line([e, (x2, e[1])], fill=0, width=thin)
            tx = (min(e[0], x2) + max(e[0], x2)) / 2 - tw / 2
            dr.text((tx, e[1] - 4.3 * px_mm), pos, font=font, fill=0)
        for (x_mm, y_mm, text, size) in self.texts:
            f2 = ImageFont.truetype(FONT_B, int(size * px_mm))
            dr.text((x_mm * px_mm, y_mm * px_mm), text, font=f2, fill=0)
        img = img.resize((W // SS, H // SS), Image.LANCZOS)
        img.save(path, dpi=(DPI, DPI))
        return path


def _dash(dr, a, b, pattern, width):
    """Прерывистая линия: pattern — длины штрихов и промежутков в пикселях (штрих, пробел, ...)."""
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L == 0:
        return
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    t, i = 0.0, 0
    while t < L:
        t2 = min(L, t + pattern[i % len(pattern)])
        if i % 2 == 0:
            dr.line([(a[0] + ux * t, a[1] + uy * t), (a[0] + ux * t2, a[1] + uy * t2)], fill=0, width=width)
        t, i = t2, i + 1

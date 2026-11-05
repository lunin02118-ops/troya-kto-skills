# -*- coding: utf-8 -*-
"""Supervised SW+ form helper using window/control identity, never screen coordinates.
python macro_ui.py list | shot <png> | click-text <text> [title] [pid]"""
import ctypes, sys, time
import win32gui, win32con, win32ui, win32process
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")


def forms():
    out = []
    def cb(h, _):
        if win32gui.IsWindowVisible(h) and (win32gui.GetClassName(h) == "ThunderDFrame" or (win32gui.GetClassName(h) == "#32770" and "Отчет об ошибках" not in win32gui.GetWindowText(h))):
            pid = win32process.GetWindowThreadProcessId(h)[1]
            out.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h), win32gui.GetWindowRect(h), pid))
    win32gui.EnumWindows(cb, None)
    return out


def inner(h):
    """Дочернее окно, куда приходят щелчки MSForms (обычно класс 'F3 Server ...')."""
    kids = []
    win32gui.EnumChildWindows(h, lambda c, _: kids.append((c, win32gui.GetClassName(c))), None)
    for c, cls in kids:
        if cls.startswith("F3 Server"):
            return c
    return kids[0][0] if kids else h


def shot(h, path):
    l, t, r, b = win32gui.GetWindowRect(h)
    w_, h_ = r - l, b - t
    hdc = win32gui.GetWindowDC(h)
    src = win32ui.CreateDCFromHandle(hdc)
    mem = src.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(src, w_, h_)
    mem.SelectObject(bmp)
    ctypes.windll.user32.PrintWindow(h, mem.GetSafeHdc(), 2)
    info = bmp.GetInfo()
    img = Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), bmp.GetBitmapBits(True), "raw", "BGRX", 0, 1)
    img.save(path)
    win32gui.DeleteObject(bmp.GetHandle()); mem.DeleteDC(); src.DeleteDC(); win32gui.ReleaseDC(h, hdc)
    return (l, t)


def click(h, sx, sy):
    """sx, sy — координаты на снимке окна (от левого верхнего угла окна)."""
    l, t, _, _ = win32gui.GetWindowRect(h)
    X, Y = l + sx, t + sy
    kids = []
    win32gui.EnumChildWindows(h, lambda k, _: kids.append(k), None)
    hit = [k for k in kids if win32gui.IsWindowVisible(k) and (lambda r: r[0] <= X < r[2] and r[1] <= Y < r[3])(win32gui.GetWindowRect(k))]
    c = min(hit, key=lambda k: (lambda r: (r[2] - r[0]) * (r[3] - r[1]))(win32gui.GetWindowRect(k))) if hit else inner(h)
    cx, cy = win32gui.ScreenToClient(c, (X, Y))
    lp = (cy << 16) | (cx & 0xFFFF)
    win32gui.PostMessage(c, win32con.WM_MOUSEMOVE, 0, lp)
    win32gui.PostMessage(c, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
    time.sleep(0.08)
    win32gui.PostMessage(c, win32con.WM_LBUTTONUP, 0, lp)


def click_text(h, text):
    """Click a visible child control by its current window text and validate identity."""
    wanted = str(text).casefold()
    kids = []
    win32gui.EnumChildWindows(h, lambda k, _: kids.append(k), None)
    matches = [k for k in kids if win32gui.IsWindowVisible(k) and win32gui.IsWindowEnabled(k)
               and wanted in win32gui.GetWindowText(k).casefold()]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one visible control containing {text!r}, found {len(matches)}")
    c = matches[0]
    label = win32gui.GetWindowText(c)
    cls = win32gui.GetClassName(c)
    if not label:
        raise RuntimeError("control identity has no text")
    if not win32gui.IsWindowEnabled(c):
        raise RuntimeError(f"control {label!r} is disabled")
    win32gui.PostMessage(c, win32con.BM_CLICK, 0, 0)
    return {"text": label, "class": cls, "pid": win32process.GetWindowThreadProcessId(h)[1]}


def select_form(fs, title=None, pid=None):
    candidates = fs
    if title:
        candidates = [f for f in candidates if str(title).casefold() in f[2].casefold()]
    if pid:
        candidates = [f for f in candidates if int(f[4]) == int(pid)]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one form (title={title!r}, pid={pid!r}), found {len(candidates)}")
    return candidates[0]


if __name__ == "__main__":
    cmd = sys.argv[1]
    fs = forms()
    if cmd == "list":
        for f in fs:
            print(f)
    elif cmd == "shot":
        for i, f in enumerate(fs):
            p = sys.argv[2].replace(".png", "_%d.png" % i)
            shot(f[0], p)
            print(p, f)
    elif cmd == "click":
        raise SystemExit("coordinate click is disabled; use click-text <text> <title> <pid>")
    elif cmd == "pid":
        f = select_form(fs, sys.argv[2] if len(sys.argv) > 2 else None)
        print(f[4])
    elif cmd == "click-text":
        title = sys.argv[3] if len(sys.argv) > 3 else None
        if len(sys.argv) < 5:
            raise SystemExit("click-text requires title and PID captured from pid command")
        pid = int(sys.argv[4])
        f = select_form(fs, title, pid)
        print("control", click_text(f[0], sys.argv[2]), "window", f[2], "pid", f[4])

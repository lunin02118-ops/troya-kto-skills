# -*- coding: utf-8 -*-
"""Открыть чертёж (активировать) и запустить макрос SW+: run_macro.py <чертёж.SLDDRW> <макрос.swp> <модуль> <процедура> [--drop-sheet ИМЯ]
Процесс висит, пока форма открыта (RunMacro2 синхронный)."""
import sys, time, subprocess
import win32com.client as w
sys.stdout.reconfigure(encoding="utf-8")
SW = w.gencache.EnsureModule("{83A33D31-27C5-11CE-BFD4-00400513BB57}", 0, 33, 0)
sw = w.GetActiveObject("SldWorks.Application")
drw, macro, mod, proc = sys.argv[1:5]
drop = sys.argv[sys.argv.index("--drop-sheet") + 1] if "--drop-sheet" in sys.argv else None
pid_file = sys.argv[sys.argv.index("--pid-file") + 1] if "--pid-file" in sys.argv else None
if pid_file:
    # RunMacro2 has no ownership token; fail closed when more than one host exists.
    raw = subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         "@(Get-Process -Name SLDWORKS -ErrorAction SilentlyContinue | % Id) -join ','"],
        text=True, stderr=subprocess.STDOUT).strip()
    pids = [p for p in raw.split(',') if p.isdigit()]
    if len(pids) != 1:
        raise RuntimeError("cannot establish unique owned SLDWORKS PID")
    with open(pid_file, "w", encoding="ascii", newline="\n") as fh:
        fh.write(pids[0] + "\n")
    print("SW_PID", pids[0])
d = sw.GetOpenDocumentByName(drw) or sw.OpenDoc6(drw, 3, 1, "", 0, 0)[0]
m = SW.IModelDoc2(d._oleobj_)
sw.ActivateDoc3(drw, False, 0, 0)
if drop:
    dd = SW.IDrawingDoc(m._oleobj_)
    names = list(dd.GetSheetNames())
    if drop in names:
        dd.ActivateSheet([n for n in names if n != drop][0])
        m.ClearSelection2(True)
        ok = m.Extension.SelectByID2(drop, "SHEET", 0, 0, 0, False, 0, None, 0)
        print("лист", drop, "выбран", ok, "удалён", m.Extension.DeleteSelection2(0))
    print("листы:", list(dd.GetSheetNames()))
err = None
t = time.time()
ok = sw.RunMacro2(macro, mod, proc, 0, 0)
print("RunMacro2", ok, "", "%.0f с" % (time.time() - t))

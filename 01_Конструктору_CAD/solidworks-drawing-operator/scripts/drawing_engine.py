import os
import sys
import time
import atexit
import shutil
import tempfile
from pathlib import Path
import win32com.client
import pythoncom
from win32com.client import VARIANT

sys.stdout.reconfigure(encoding='utf-8')

def _resolve_format(sheet_size):
    """Resolve a configured template; never assume a SolidWorks installation/version."""
    key = str(sheet_size or "A3").upper()
    env_name = f"SW_SHEET_FORMAT_{key}"
    configured = os.environ.get(env_name)
    if not configured or not os.path.isfile(configured):
        raise FileNotFoundError(
            f"{env_name} must point to an existing .slddrt template; "
            "native drawing generation is blocked until configured"
        )
    return configured


def _save_as_checked(doc,path,err,warn):
    return _save_outputs_transaction(doc,(path,),err,warn)


def _save_outputs_transaction(doc, outputs, err, warn):
    """Prepare all sibling outputs, verify them, retain backups, then commit together."""
    import hashlib, uuid, stat
    run=uuid.uuid4().hex
    targets=[Path(os.path.abspath(p)) for p in outputs]
    if not targets or len(set(targets))!=len(targets):
        raise ValueError('Output paths must be distinct')
    def guard(path):
        for p in (path,*path.parents):
            try:st=p.lstat()
            except FileNotFoundError:continue
            if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
                raise RuntimeError(f'Reparse output path rejected: {p}')
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    snapshots={};stages={};backups={};committed=[]
    for target in targets:
        guard(target)
        if target.exists() and not target.is_file():raise ValueError(f'Output is not a file: {target}')
        snapshots[target]=digest(target)
    try:
        for target in targets:
            target.parent.mkdir(parents=True,exist_ok=True)
            stage=target.with_name(f'.{target.stem}.stage-{run}{target.suffix}')
            guard(stage);stages[target]=stage
            err.value=0;warn.value=0
            result=doc.SaveAs4(str(stage),0,0,err,warn)
            if not bool(result) or int(err.value or 0) or int(warn.value or 0) or not stage.is_file() or not stage.stat().st_size:
                raise RuntimeError(f'SaveAs4 failed: {target}, result={result}, errors={err.value}, warnings={warn.value}')
        for target in targets:
            guard(target)
            if digest(target)!=snapshots[target]:raise RuntimeError(f'Output changed during preparation: {target}')
            if snapshots[target] is not None:
                backup=target.parent/'_Резерв_чертежей'/run/target.name
                guard(backup);backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,backup)
                if digest(backup)!=snapshots[target]:raise RuntimeError(f'Backup SHA mismatch: {target}')
                backups[target]=backup
        for target in targets:
            guard(target)
            if digest(target)!=snapshots[target]:raise RuntimeError(f'Output changed before commit: {target}')
            payload_hash=digest(stages[target])
            committed.append(target)
            os.replace(stages[target],target)
            if digest(target)!=payload_hash:raise RuntimeError(f'Committed SHA mismatch: {target}')
        return {'outputs':[str(p) for p in targets],'backups':[str(p) for p in backups.values()]}
    except Exception as exc:
        rollback_errors=[]
        for target in reversed(committed):
            try:
                guard(target)
                if target.exists():
                    failed=target.parent/f'_failed_outputs_{run}'/target.name
                    guard(failed);failed.parent.mkdir(parents=True,exist_ok=True)
                    target.rename(failed)
                if target in backups:
                    shutil.copy2(backups[target],target)
                    if digest(target)!=snapshots[target]:raise RuntimeError('Rollback SHA mismatch')
            except Exception as failure:rollback_errors.append(str(failure))
        if rollback_errors:raise RuntimeError(f'{exc}; rollback errors={rollback_errors}; backups retained') from exc
        raise
    finally:
        for target,stage in stages.items():
            if stage.exists():
                failed=target.parent/f'_failed_outputs_{run}'/stage.name
                guard(failed);failed.parent.mkdir(parents=True,exist_ok=True)
                stage.rename(failed)


def add_gost_horizontal_dim(doc_drw, drw, x1, x2, y, offset, dim_val_str):
    """Legacy visual guide only; not a native/associative CAD dimension and never release evidence."""
    dim_y = y + offset
    ext_y = dim_y + (0.003 if offset > 0 else -0.003)
    
    # 1. Extension lines (Выносные линии)
    doc_drw.SketchManager.CreateLine(x1, y, 0, x1, ext_y, 0)
    doc_drw.SketchManager.CreateLine(x2, y, 0, x2, ext_y, 0)
    
    # 2. Dimension line (Размерная линия)
    doc_drw.SketchManager.CreateLine(x1, dim_y, 0, x2, dim_y, 0)
    
    # 3. Dimension text (Размерное число над линией)
    mid_x = (x1 + x2) / 2.0
    text_y = dim_y + 0.001
    drw.CreateText2(f"{dim_val_str}", mid_x, text_y, 0, 0.0035, 0)


def add_gost_vertical_dim(doc_drw, drw, y1, y2, x, offset, dim_val_str):
    """Legacy visual guide only; not a native/associative CAD dimension and never release evidence."""
    dim_x = x + offset
    ext_x = dim_x + (-0.003 if offset < 0 else 0.003)
    
    # 1. Extension lines (Выносные линии)
    doc_drw.SketchManager.CreateLine(x, y1, 0, ext_x, y1, 0)
    doc_drw.SketchManager.CreateLine(x, y2, 0, ext_x, y2, 0)
    
    # 2. Dimension line (Размерная линия)
    doc_drw.SketchManager.CreateLine(dim_x, y1, 0, dim_x, y2, 0)
    
    # 3. Dimension text (Размерное число слева от линии, повернутое на 90 градусов)
    mid_y = (y1 + y2) / 2.0
    text_x = dim_x - 0.001
    drw.CreateText2(f"{dim_val_str}", text_x, mid_y, 0, 0.0035, 90)


def _iter_display_dimensions(view):
    """Yield the IDisplayDimension chain (GetFirstDisplayDimension5, then GetNext5)."""
    first = getattr(view, "GetFirstDisplayDimension5", None)
    if first is None:
        first = getattr(view, "GetFirstDisplayDimension", None)
    if first is None:
        return
    current = first()
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        next_method = getattr(current, "GetNext5", None)
        if next_method is not None:
            current = next_method()
            continue
        raise RuntimeError('IDisplayDimension.GetNext5 is unavailable; dimension chain cannot be verified')


def _member_value(obj, name, *args):
    value = getattr(obj, name, None)
    if value is None:
        return None
    return value(*args) if callable(value) else value


def _validate_native_dimensions(view):
    """Validate imported native dimensions; unknown association state fails closed."""
    dimensions = list(_iter_display_dimensions(view) or [])
    if not dimensions:
        return {"status": "incomplete_no_verified_display_dimensions", "count": 0, "references_valid": False}
    attached_total = 0
    for display_dimension in dimensions:
        if _member_value(display_dimension, "GetDimension2", 0) is None:
            return {"status": "incomplete_native_reference_missing", "count": len(dimensions), "references_valid": False}
        annotation = _member_value(display_dimension, "GetAnnotation")
        if annotation is None:
            return {"status": "incomplete_annotation_missing", "count": len(dimensions), "references_valid": False}
        dangling = _member_value(annotation, "IsDangling")
        if dangling is None:
            dangling = _member_value(display_dimension, "AnnotationIsDangling")
        if dangling is None:
            return {"status": "incomplete_dangling_state_unknown", "count": len(dimensions), "references_valid": False}
        if bool(dangling):
            return {"status": "incomplete_dangling_dimension", "count": len(dimensions), "references_valid": False}
        attached = _member_value(annotation, "GetAttachedEntities3")
        if attached is None:
            attached = _member_value(annotation, "GetAttachedEntities2")
        if attached is None:
            return {"status": "incomplete_attached_geometry_api", "count": len(dimensions), "references_valid": False}
        if isinstance(attached, tuple) and len(attached) == 2 and isinstance(attached[1], (int, float)):
            attached = attached[0]
        try:
            attached_count = len(attached)
        except TypeError:
            attached_count = 1 if attached else 0
        if attached_count == 0:
            return {"status": "incomplete_attached_geometry_missing", "count": len(dimensions), "references_valid": False}
        attached_total += attached_count
    return {"status": "verified", "count": len(dimensions), "references_valid": True, "associative": True, "attached_count": attached_total}


def _insert_native_dimensions(drawing, view):
    """Import marked model dimensions using the documented InsertModelAnnotations3 contract."""
    try:
        drawing.ActivateView(view.GetName2)
        method = getattr(drawing, "InsertModelAnnotations3", None)
        if method is None:
            return {"status": "incomplete_native_api_unavailable", "count": 0, "references_valid": False}
        inserted = method(0, 32768, False, True, False, False)
        if inserted is False or inserted is None:
            return {"status": "incomplete_native_import_failed", "count": 0, "references_valid": False}
        return _validate_native_dimensions(view)
    except Exception as exc:
        return {"status": "incomplete_native_dimension_error", "count": 0, "references_valid": False, "error": str(exc)}


def create_2d_drawing(model_path: str, output_drw_path: str = None, scale_val: str = "1:2", sheet_size: str = "A3", technical_requirements: str = None):
    """Create a drawing without modifying the source; restore session state on every exit."""
    import math, hashlib
    model_path=os.path.abspath(model_path)
    if not os.path.isfile(model_path):raise FileNotFoundError(model_path)
    ext=Path(model_path).suffix.lower()
    if ext not in ('.sldprt','.sldasm'):raise ValueError('A native SolidWorks part or assembly is required')
    size=str(sheet_size).upper()
    dimensions={'A3':(0.420,0.297),'A4':(0.297,0.210)}
    if size not in dimensions:raise ValueError('Supported sheet sizes: A3, A4')
    parts=str(scale_val).split(':')
    if len(parts)!=2:raise ValueError('Scale must have the form numerator:denominator')
    s_num,s_den=map(float,parts)
    if not all(math.isfinite(v) and v>0 for v in (s_num,s_den)):raise ValueError('Scale values must be positive and finite')
    output_drw_path=os.path.abspath(output_drw_path or str(Path(model_path).with_suffix('.SLDDRW')))
    if Path(output_drw_path).suffix.lower()!='.slddrw':raise ValueError('Output must be a .SLDDRW file')
    pdf_path=str(Path(output_drw_path).with_suffix('.PDF'))
    fmt_file=_resolve_format(size)
    width,height=dimensions[size]
    try:
        sw=win32com.client.GetActiveObject('SldWorks.Application')
        launched_here=False
    except Exception:
        sw=win32com.client.DispatchEx('SldWorks.Application')
        launched_here=True
    # COM activation can reuse a singleton. Never exit an application on an unproven ownership claim.
    doc_3d=doc_drw=None
    source_opened_here=False
    old_popup_pref=None
    preference_changed=False
    err=VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    warn=VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    try:
        # Ownership checks must succeed before any document or session mutation.
        for target in (output_drw_path,pdf_path):
            if sw.GetOpenDocumentByName(target) is not None:raise RuntimeError('Output is already open: '+target)
        doc_3d=sw.GetOpenDocumentByName(model_path)
        template=os.environ.get('SW_DRAWING_TEMPLATE') or sw.GetDocumentTemplate(3,'',12,width,height)
        if not template or not os.path.isfile(template):raise FileNotFoundError('An existing .drwdot drawing template is required (SW_DRAWING_TEMPLATE or configured default)')
        old_popup_pref=sw.GetUserPreferenceToggle(26)
        if old_popup_pref is None:raise RuntimeError('Cannot record the current dialog preference')
        preference_changed=True
        sw.SetUserPreferenceToggle(26,False)
        if doc_3d is None:
            err.value=warn.value=0
            doc_3d=sw.OpenDoc6(model_path,2 if ext=='.sldasm' else 1,2,'',err,warn)
            source_opened_here=doc_3d is not None
            if doc_3d is None or int(err.value or 0) or int(warn.value or 0):raise RuntimeError('Source model could not be opened cleanly')
        doc_drw=sw.NewDocument(template,12,width,height)
        if doc_drw is None:raise RuntimeError('SolidWorks did not create a drawing')
        drawing=win32com.client.dynamic.Dispatch(doc_drw)
        sheet=drawing.GetCurrentSheet()
        if sheet is None:raise RuntimeError('New drawing has no sheet')
        sheet_name=_member_value(sheet,'GetName')
        if drawing.SetupSheet5(sheet_name,12,0,s_num,s_den,True,fmt_file,width,height,'',True) is not True:
            raise RuntimeError('Sheet format or scale was not applied')
        views=[]
        for name,x,y,mode in (('*Front',.36,.60,0),('*Top',.36,.27,0),('*Right',.69,.60,0),('*Isometric',.79,.77,3)):
            view=drawing.CreateDrawViewFromModelView3(model_path,name,x*width,y*height,0)
            if view is None:raise RuntimeError('Failed to create view: '+name)
            view.SetDisplayMode3(False,mode,False,True)
            if mode==0:view.SetDisplayTangentEdges2(0)
            views.append(view)
        if doc_drw.ForceRebuild3(False) is not True:raise RuntimeError('Drawing rebuild failed')
        dimension_evidence=_insert_native_dimensions(drawing,views[0])
        if technical_requirements:
            if drawing.CreateText2(str(technical_requirements),.03,.07,0,.0035,0) is None:
                raise RuntimeError('Technical requirements were not inserted')
        if doc_drw.ForceRebuild3(False) is not True:raise RuntimeError('Final drawing rebuild failed')
        if dimension_evidence.get('status')=='verified':
            dimension_evidence=_validate_native_dimensions(views[0])
        doc_drw.ViewZoomtofit2()
        saving=_save_outputs_transaction(doc_drw,(output_drw_path,pdf_path),err,warn)
        dimension_evidence.update(pdf_path=pdf_path,pdf_sha256=hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest(),
                                  model_path=model_path,model_sha256=hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),rebuild_verified=True)
        return {'drawing_path':output_drw_path,'pdf_path':pdf_path,'dimension_status':dimension_evidence,
                'save_transaction':saving,'application_left_running':launched_here}
    finally:
        cleanup_errors=[]
        for document,owned in ((doc_drw,doc_drw is not None),(doc_3d,source_opened_here)):
            if document is not None and owned:
                try:sw.CloseDoc(_member_value(document,'GetTitle'))
                except Exception as exc:cleanup_errors.append(str(exc))
        if preference_changed:
            try:sw.SetUserPreferenceToggle(26,old_popup_pref)
            except Exception as exc:cleanup_errors.append(str(exc))
        if cleanup_errors:raise RuntimeError('Session cleanup failed: '+'; '.join(cleanup_errors))

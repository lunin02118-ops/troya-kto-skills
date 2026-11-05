import hashlib, os, sys, tempfile
import pymupdf
from rapidocr_onnxruntime import RapidOCR
from PIL import Image
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
def _sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def _native_evidence_ok(pdf_path,evidence):
 if not isinstance(evidence,dict) or evidence.get('status')!='verified': return False
 count=evidence.get('count',0)
 if not isinstance(count,int) or isinstance(count,bool): return False
 return count>0 and evidence.get('associative') is True and evidence.get('references_valid') is True and evidence.get('rebuild_verified') is True and os.path.normcase(os.path.abspath(str(evidence.get('pdf_path',''))))==os.path.normcase(os.path.abspath(pdf_path)) and str(evidence.get('pdf_sha256','')).lower()==_sha256(pdf_path).lower()
def validate_drawing(pdf_path:str,dimension_evidence=None,expected_title_fields=None):
 if not os.path.isfile(pdf_path): return False,'PDF файл чертежа не найден',[]
 png_tmp=None; doc=None; im=None
 try:
  with tempfile.NamedTemporaryFile(prefix='drawing_ocr_',suffix='.png',delete=False) as tmp: png_tmp=tmp.name
  doc=pymupdf.open(pdf_path)
  if len(doc)==0: return False,'PDF файл пуст',[]
  pix=doc[0].get_pixmap(dpi=150); pix.save(png_tmp); im=Image.open(png_tmp); w,h=im.size; arr=np.array(im.convert('L'))
  area=arr[int(.05*h):int(.75*h),int(.05*w):int(.95*w)]; nonwhite=np.sum(area<240); geo=(nonwhite/area.size)*100.0
  title=arr[int(.75*h):int(.98*h),int(.50*w):int(.98*w)]; density=(np.sum(title<240)/title.size)*100.0
  ocr=RapidOCR()
  result,_=ocr(png_tmp); lines=[x[1] for x in result if x[2]>.4] if result else []
  title_result,_=ocr(title); title_lines=[x[1] for x in title_result if x[2]>.4] if title_result else []
 except Exception as exc: return False,f'BLOCKED: PDF/OCR validation failed: {exc}',[]
 finally:
  try:
   if im is not None: im.close()
  finally:
   try:
    if doc is not None: doc.close()
   finally:
    if png_tmp and os.path.exists(png_tmp):
     try: os.remove(png_tmp)
     except OSError: pass
 assoc=_native_evidence_ok(pdf_path,dimension_evidence)
 if geo<.20: return False,f'ОТКЛОНЕНО: Поле чертежа пусто ({geo:.3f}%)',lines
 if not assoc: return False,'BLOCKED: verified native associative evidence bound to this PDF is missing or invalid',lines
 if not isinstance(expected_title_fields,(list,tuple)) or not expected_title_fields: return False,'INCOMPLETE: visual screening only; nonempty expected_title_fields were not supplied',lines
 expected=[str(x).strip().lower() for x in expected_title_fields if str(x).strip()]; low=[str(x).lower() for x in title_lines]; missing=[x for x in expected if not any(x in line for line in low)]
 if not expected: return False,'INCOMPLETE: expected_title_fields are blank',lines
 if missing: return False,f'INCOMPLETE: expected title fields not found by OCR: {missing}',lines
 return True,f'PASS: visual screening and verified native evidence (Геометрия: {geo:.2f}%, Штамп: {density:.2f}%)',lines

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import traceback
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, date
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET

import olefile
import mpxj
import jpype

ROOT = Path('/mnt/data/triplecheck_fresh')
OUT = Path('/mnt/data/hardened_run')
OUT.mkdir(parents=True, exist_ok=True)

NS_MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS_PKG_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'

VENDOR_ACUMEN_TERMS = [
    'acumen', 'fuse', 'metric history', 'forensic analyzer', 'diagnostics',
    'schedule quality', 'quick add', 'ribbon', 'tripwire', 'metric library'
]
VENDOR_SSI_TERMS = [
    'ssi', 'directional path', 'driving slack', 'path-01', 'path 01', 'path-02',
    'path 02', 'path-03', 'path 03', 'drag', 'driving path'
]
SCHEDULE_EXTS = {'.mpp', '.xml', '.xer'}
ORACLE_EXTS = {'.xlsx', '.afw'}


def clean_text(v: Any) -> str:
    if v is None:
        return ''
    s = str(v)
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'\s+', ' ', s).strip()


def norm_token(s: str) -> str:
    s = clean_text(s).lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return ' '.join(s.split())


def norm_stem(path_or_name: str) -> str:
    return norm_token(Path(path_or_name).stem)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    b = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(b).hexdigest()


def lname(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def jstr(v: Any) -> str | None:
    if v is None:
        return None
    s = clean_text(v)
    return s or None


def jnum(v: Any) -> float | int | None:
    if v is None:
        return None
    try:
        x = float(str(v))
        if math.isfinite(x):
            if x.is_integer():
                return int(x)
            return round(x, 8)
    except Exception:
        return None
    return None


def jdate(v: Any) -> str | None:
    if v is None:
        return None
    try:
        # java.time LocalDateTime/LocalDate stringify deterministically
        return str(v)
    except Exception:
        return clean_text(v) or None


def safe_call(obj: Any, method: str, *args: Any) -> Any:
    try:
        return getattr(obj, method)(*args)
    except Exception:
        return None


def ole_meta(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        ole = olefile.OleFileIO(str(path))
        md = ole.get_metadata()
        for key in [
            'title', 'subject', 'author', 'keywords', 'comments', 'template',
            'last_saved_by', 'revision_number', 'create_time', 'last_saved_time',
            'creating_application', 'manager', 'company', 'category', 'content_status'
        ]:
            v = getattr(md, key, None)
            if isinstance(v, bytes):
                try:
                    v = v.decode('cp1252', 'replace')
                except Exception:
                    v = repr(v)
            if isinstance(v, (datetime, date)):
                v = v.isoformat()
            if v not in (None, '', b''):
                out[key] = v
        hp = getattr(md, 'heading_pairs', None)
        tp = getattr(md, 'titles_of_parts', None)
        if hp:
            out['heading_pairs'] = [clean_text(x.decode('cp1252','replace') if isinstance(x,bytes) else x) for x in hp]
        if tp:
            out['titles_of_parts'] = [clean_text(x.decode('cp1252','replace') if isinstance(x,bytes) else x) for x in tp]
        out['ole_stream_count'] = len(ole.listdir())
        out['ole_root_storages'] = sorted({parts[0] for parts in ole.listdir() if parts})[:100]
        ole.close()
    except Exception as e:
        out['ole_error'] = f'{type(e).__name__}: {e}'
    return out


# ---------- MPXJ semantic extraction ----------

def start_jvm() -> None:
    if not jpype.isJVMStarted():
        jpype.startJVM(convertStrings=True)


def task_row(t: Any) -> dict[str, Any]:
    cal = safe_call(t, 'getCalendar')
    return {
        'uid': jnum(safe_call(t, 'getUniqueID')),
        'id': jnum(safe_call(t, 'getID')),
        'name': jstr(safe_call(t, 'getName')),
        'wbs': jstr(safe_call(t, 'getWBS')),
        'outline_number': jstr(safe_call(t, 'getOutlineNumber')),
        'outline_level': jnum(safe_call(t, 'getOutlineLevel')),
        'summary': bool(safe_call(t, 'getSummary') or False),
        'milestone': bool(safe_call(t, 'getMilestone') or False),
        'active': safe_call(t, 'getActive') is not False,
        'manual': bool(safe_call(t, 'getManual') or False) if hasattr(t, 'getManual') else None,
        'start': jdate(safe_call(t, 'getStart')),
        'finish': jdate(safe_call(t, 'getFinish')),
        'actual_start': jdate(safe_call(t, 'getActualStart')),
        'actual_finish': jdate(safe_call(t, 'getActualFinish')),
        'baseline_start': jdate(safe_call(t, 'getBaselineStart')),
        'baseline_finish': jdate(safe_call(t, 'getBaselineFinish')),
        'duration': jstr(safe_call(t, 'getDuration')),
        'remaining_duration': jstr(safe_call(t, 'getRemainingDuration')),
        'actual_duration': jstr(safe_call(t, 'getActualDuration')),
        'baseline_duration': jstr(safe_call(t, 'getBaselineDuration')),
        'percent_complete': jnum(safe_call(t, 'getPercentageComplete')),
        'percent_work_complete': jnum(safe_call(t, 'getPercentageWorkComplete')),
        'total_slack': jstr(safe_call(t, 'getTotalSlack')),
        'free_slack': jstr(safe_call(t, 'getFreeSlack')),
        'critical': bool(safe_call(t, 'getCritical') or False),
        'constraint_type': jstr(safe_call(t, 'getConstraintType')),
        'constraint_date': jdate(safe_call(t, 'getConstraintDate')),
        'deadline': jdate(safe_call(t, 'getDeadline')),
        'calendar_uid': jnum(safe_call(t, 'getCalendarUniqueID')),
        'calendar_name': jstr(safe_call(cal, 'getName')) if cal else None,
        'cost': jnum(safe_call(t, 'getCost')),
        'actual_cost': jnum(safe_call(t, 'getActualCost')),
        'baseline_cost': jnum(safe_call(t, 'getBaselineCost')),
        'work': jstr(safe_call(t, 'getWork')),
        'actual_work': jstr(safe_call(t, 'getActualWork')),
        'baseline_work': jstr(safe_call(t, 'getBaselineWork')),
        'resource_names': jstr(safe_call(t, 'getResourceNames')),
        'guid': jstr(safe_call(t, 'getGUID')),
    }


def relation_row(r: Any) -> dict[str, Any]:
    p = safe_call(r, 'getPredecessorTask')
    s = safe_call(r, 'getSuccessorTask')
    return {
        'pred_uid': jnum(safe_call(p, 'getUniqueID')) if p else None,
        'succ_uid': jnum(safe_call(s, 'getUniqueID')) if s else None,
        'type': jstr(safe_call(r, 'getType')),
        'lag': jstr(safe_call(r, 'getLag')),
        'driving': safe_call(r, 'getDriving'),
    }


def calendar_row(c: Any) -> dict[str, Any]:
    ex = safe_call(c, 'getCalendarExceptions')
    workweeks = safe_call(c, 'getWorkWeeks')
    daytypes = []
    for day in ['SUNDAY','MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY']:
        try:
            Day = jpype.JClass('org.mpxj.Day')
            d = getattr(Day, day)
            daytypes.append((day, jstr(c.getCalendarDayType(d))))
        except Exception:
            pass
    return {
        'uid': jnum(safe_call(c, 'getUniqueID')),
        'name': jstr(safe_call(c, 'getName')),
        'parent_uid': jnum(safe_call(c, 'getParentUniqueID')),
        'minutes_per_day': jnum(safe_call(c, 'getMinutesPerDay')),
        'minutes_per_week': jnum(safe_call(c, 'getMinutesPerWeek')),
        'minutes_per_month': jnum(safe_call(c, 'getMinutesPerMonth')),
        'type': jstr(safe_call(c, 'getType')),
        'day_types': daytypes,
        'exception_count': len(ex) if ex is not None else 0,
        'workweek_count': len(workweeks) if workweeks is not None else 0,
    }


def resource_row(r: Any) -> dict[str, Any]:
    return {
        'uid': jnum(safe_call(r, 'getUniqueID')),
        'id': jnum(safe_call(r, 'getID')),
        'name': jstr(safe_call(r, 'getName')),
        'type': jstr(safe_call(r, 'getType')),
        'calendar_uid': jnum(safe_call(r, 'getCalendarUniqueID')),
        'group': jstr(safe_call(r, 'getGroup')),
        'max_units': jnum(safe_call(r, 'getMaxUnits')),
        'cost': jnum(safe_call(r, 'getCost')),
        'actual_cost': jnum(safe_call(r, 'getActualCost')),
        'work': jstr(safe_call(r, 'getWork')),
        'actual_work': jstr(safe_call(r, 'getActualWork')),
        'active': safe_call(r, 'getActive') is not False,
    }


def assignment_row(a: Any) -> dict[str, Any]:
    t = safe_call(a, 'getTask')
    r = safe_call(a, 'getResource')
    return {
        'task_uid': jnum(safe_call(t, 'getUniqueID')) if t else jnum(safe_call(a, 'getTaskUniqueID')),
        'resource_uid': jnum(safe_call(r, 'getUniqueID')) if r else jnum(safe_call(a, 'getResourceUniqueID')),
        'start': jdate(safe_call(a, 'getStart')),
        'finish': jdate(safe_call(a, 'getFinish')),
        'actual_start': jdate(safe_call(a, 'getActualStart')),
        'actual_finish': jdate(safe_call(a, 'getActualFinish')),
        'work': jstr(safe_call(a, 'getWork')),
        'actual_work': jstr(safe_call(a, 'getActualWork')),
        'cost': jnum(safe_call(a, 'getCost')),
        'actual_cost': jnum(safe_call(a, 'getActualCost')),
        'units': jnum(safe_call(a, 'getUnits')),
        'leveling_delay': jstr(safe_call(a, 'getLevelingDelay')),
    }


def parse_schedule(path: Path) -> dict[str, Any]:
    start_jvm()
    from org.mpxj.reader import UniversalProjectReader
    out: dict[str, Any] = {'kind': 'schedule', 'parser': 'MPXJ-python', 'parser_package': getattr(mpxj, '__file__', '')}
    try:
        pf = UniversalProjectReader().read(str(path))
        props = pf.getProjectProperties()
        prop_fields = [
            'ProjectTitle','Name','StatusDate','StartDate','FinishDate','ScheduledFinish','CreationDate',
            'LastScheduledDate','CurrentDate','MinutesPerDay','MinutesPerWeek','DaysPerMonth','ScheduleFrom',
            'DefaultCalendarUniqueID','CurrencyCode','MustFinishBy','BaselineStart','BaselineFinish'
        ]
        properties = {}
        for f in prop_fields:
            v = safe_call(props, 'get'+f)
            if 'Date' in f or 'Start' in f or 'Finish' in f:
                v = jdate(v)
            elif 'Minutes' in f or 'Days' in f or 'UniqueID' in f:
                v = jnum(v)
            else:
                v = jstr(v)
            if v is not None:
                properties[f] = v
        tasks = [task_row(t) for t in pf.getTasks()]
        relations = [relation_row(r) for r in pf.getRelations()]
        calendars = [calendar_row(c) for c in pf.getCalendars()]
        resources = [resource_row(r) for r in pf.getResources()]
        assignments = [assignment_row(a) for a in pf.getResourceAssignments()]
        tasks.sort(key=lambda x: ((x['uid'] is None), x['uid'] if x['uid'] is not None else 10**18, x['id'] or 0))
        relations.sort(key=lambda x: (x['pred_uid'] or -1, x['succ_uid'] or -1, x['type'] or '', x['lag'] or ''))
        calendars.sort(key=lambda x: (x['uid'] if x['uid'] is not None else 10**18, x['name'] or ''))
        resources.sort(key=lambda x: (x['uid'] if x['uid'] is not None else 10**18, x['name'] or ''))
        assignments.sort(key=lambda x: (x['task_uid'] or -1, x['resource_uid'] or -1, x['start'] or ''))
        out.update({
            'properties': properties,
            'tasks': tasks,
            'relations': relations,
            'calendars': calendars,
            'resources': resources,
            'assignments': assignments,
            'counts': {
                'tasks_all': len(tasks),
                'tasks_nonzero_uid': sum(1 for t in tasks if t['uid'] not in (None, 0)),
                'tasks_summary': sum(1 for t in tasks if t['summary']),
                'tasks_milestone': sum(1 for t in tasks if t['milestone']),
                'tasks_inactive': sum(1 for t in tasks if not t['active']),
                'relations': len(relations),
                'calendars': len(calendars),
                'resources': len(resources),
                'assignments': len(assignments),
            }
        })
        identity_tasks = [
            {k:t.get(k) for k in ('uid','id','name','wbs','outline_number','summary','milestone','active')}
            for t in tasks
        ]
        logic = [{k:r.get(k) for k in ('pred_uid','succ_uid','type','lag')} for r in relations]
        schedule_fields = [
            {k:t.get(k) for k in (
                'uid','start','finish','actual_start','actual_finish','baseline_start','baseline_finish',
                'duration','remaining_duration','actual_duration','baseline_duration','percent_complete',
                'total_slack','free_slack','critical','constraint_type','constraint_date','deadline','calendar_uid'
            )} for t in tasks
        ]
        resource_fields = {'resources':resources,'assignments':assignments}
        calendar_fields = calendars
        out['fingerprints'] = {
            'identity': sha256_json({'project_title':properties.get('ProjectTitle') or properties.get('Name'), 'status':properties.get('StatusDate'), 'tasks':identity_tasks}),
            'logic': sha256_json(logic),
            'schedule': sha256_json(schedule_fields),
            'calendar': sha256_json(calendar_fields),
            'resource': sha256_json(resource_fields),
            'combined': sha256_json({'properties':properties,'tasks':tasks,'relations':relations,'calendars':calendars,'resources':resources,'assignments':assignments}),
        }
        out['task_uid_set'] = [t['uid'] for t in tasks if isinstance(t['uid'], int) and t['uid'] != 0]
        out['task_name_set'] = sorted({norm_token(t['name']) for t in tasks if t.get('name') and t.get('uid') != 0})
    except Exception as e:
        out['parse_error'] = f'{type(e).__name__}: {e}'
        out['traceback'] = traceback.format_exc(limit=5)
    return out


# ---------- OOXML workbook extraction ----------

def read_core_props(z: zipfile.ZipFile) -> dict[str, Any]:
    out = {}
    for name in ['docProps/core.xml','docProps/app.xml','docProps/custom.xml']:
        if name not in z.namelist():
            continue
        try:
            root = ET.fromstring(z.read(name))
            for e in root.iter():
                key = lname(e.tag)
                txt = clean_text(e.text)
                if txt:
                    out[f'{Path(name).stem}.{key}'] = txt
        except Exception as e:
            out[f'{name}.error'] = str(e)
    return out


def xlsx_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    out=[]
    for si in root:
        texts=[]
        for e in si.iter():
            if lname(e.tag)=='t' and e.text is not None:
                texts.append(e.text)
        out.append(''.join(texts))
    return out


def xlsx_sheet_map(z: zipfile.ZipFile) -> list[tuple[str,str]]:
    names = z.namelist()
    if 'xl/workbook.xml' not in names:
        return []
    relmap={}
    if 'xl/_rels/workbook.xml.rels' in names:
        rr=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        for r in rr:
            rid=r.attrib.get('Id')
            target=r.attrib.get('Target','')
            if target.startswith('/'):
                target=target.lstrip('/')
            elif not target.startswith('xl/'):
                target='xl/'+target
            target=str(Path(target))
            relmap[rid]=target
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    out=[]
    for e in wb.iter():
        if lname(e.tag)=='sheet':
            n=e.attrib.get('name','')
            rid=e.attrib.get('{%s}id'%NS_REL)
            target=relmap.get(rid,'')
            out.append((n,target))
    return out

CELL_REF_RE = re.compile(r'([A-Z]+)(\d+)')
def col_index(ref: str) -> int:
    m=CELL_REF_RE.match(ref or '')
    if not m: return -1
    n=0
    for ch in m.group(1): n=n*26+(ord(ch)-64)
    return n


def parse_xlsx(path: Path) -> dict[str, Any]:
    out: dict[str, Any]={'kind':'xlsx'}
    try:
        with zipfile.ZipFile(path) as z:
            z.testzip()
            names=z.namelist()
            ss=xlsx_shared_strings(z)
            sheet_map=xlsx_sheet_map(z)
            core=read_core_props(z)
            all_text=[]
            all_formulas=[]
            sheet_summaries=[]
            all_rows_for_headers=[]
            uid_numbers=set()
            explicit_files=set()
            date_like=set()
            project_strings=set()
            cell_digest=hashlib.sha256()
            for sheet_name,target in sheet_map:
                if target not in names:
                    sheet_summaries.append({'name':sheet_name,'target':target,'error':'missing worksheet part'})
                    continue
                root=ET.fromstring(z.read(target))
                count=0; nonempty=0; formulas=0; texts=0; nums=0
                first_rows=[]
                row_values=defaultdict(dict)
                for c in root.iter():
                    if lname(c.tag)!='c': continue
                    count += 1
                    ref=c.attrib.get('r','')
                    typ=c.attrib.get('t','')
                    ftxt=''
                    vtxt=''
                    inline=''
                    for ch in c:
                        if lname(ch.tag)=='f': ftxt=ch.text or ''
                        elif lname(ch.tag)=='v': vtxt=ch.text or ''
                        elif lname(ch.tag)=='is':
                            inline=''.join((x.text or '') for x in ch.iter() if lname(x.tag)=='t')
                    val: Any=''
                    if typ=='s' and vtxt:
                        try: val=ss[int(vtxt)]
                        except Exception: val=vtxt
                    elif typ in ('inlineStr','str'):
                        val=inline or vtxt
                    elif typ=='b': val='TRUE' if vtxt=='1' else 'FALSE'
                    else: val=vtxt
                    if ftxt:
                        formulas += 1; all_formulas.append(ftxt)
                    if val not in ('',None):
                        nonempty += 1
                        cell_digest.update(f'{sheet_name}|{ref}|{typ}|{val}|{ftxt}\n'.encode('utf-8','replace'))
                        if isinstance(val,str):
                            txt=clean_text(val)
                            if txt:
                                all_text.append(txt); texts += 1
                                low=txt.lower()
                                for m in re.finditer(r'[^\\/:*?"<>|\r\n]+\.(?:mpp|xer|xml|afw|xlsx)', txt, re.I):
                                    explicit_files.add(clean_text(m.group(0)))
                                if any(k in low for k in ['project','hard_file','hard file','large test','tp1','tp2','tp3','tp4','evm','data center','commercial construction','usa otb']):
                                    project_strings.add(txt[:250])
                                if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?', txt):
                                    date_like.add(txt)
                        else: nums += 1
                        # retain first 80 rows x 40 cols for structural/header analysis
                        m=CELL_REF_RE.match(ref)
                        if m:
                            rn=int(m.group(2)); ci=col_index(ref)
                            if rn<=80 and ci<=40:
                                row_values[rn][ci]=clean_text(val)
                            if ci<=10:
                                try:
                                    iv=int(float(str(val)))
                                    if 0 < iv < 10000000: uid_numbers.add(iv)
                                except Exception: pass
                for rn in sorted(row_values):
                    cols=row_values[rn]
                    first_rows.append({'row':rn,'values':[cols.get(i,'') for i in range(1,max(cols.keys(), default=0)+1)]})
                sheet_summaries.append({
                    'name':sheet_name,'target':target,'cell_count':count,'nonempty_count':nonempty,
                    'formula_count':formulas,'text_count':texts,'numeric_count':nums,
                    'first_rows':first_rows,
                })
                all_rows_for_headers.extend((sheet_name,r['row'],r['values']) for r in first_rows)
            lower='\n'.join(all_text).lower()
            ac=sum(lower.count(t) for t in VENDOR_ACUMEN_TERMS)
            ssis=sum(lower.count(t) for t in VENDOR_SSI_TERMS)
            sheet_low=' '.join(n.lower() for n,_ in sheet_map)
            ac += sum(3 for t in VENDOR_ACUMEN_TERMS if t in sheet_low)
            ssis += sum(3 for t in VENDOR_SSI_TERMS if t in sheet_low)
            if ac and ssis:
                vendor='Acumen+SSI/Mixed'
            elif ac:
                vendor='Acumen Fuse'
            elif ssis:
                vendor='SSI Tools'
            else:
                vendor='Other/Unknown'
            # Identify likely header rows and columns
            header_hits=[]
            header_terms={'uid','unique id','id','activity id','activity name','name','description','project','project name','status date','data date','driving slack','drag','metric','value','count','percentage'}
            for sh,rn,vals in all_rows_for_headers:
                nv=[norm_token(v) for v in vals if v]
                score=sum(1 for v in nv if v in header_terms or any(h in v for h in ['driving slack','unique id','activity name','project name','data date']))
                if score>=2:
                    header_hits.append({'sheet':sh,'row':rn,'values':vals,'score':score})
            out.update({
                'core_properties':core,
                'zip_parts':len(names),
                'sheets':[n for n,_ in sheet_map],
                'sheet_summaries':sheet_summaries,
                'cell_count':sum(s.get('cell_count',0) for s in sheet_summaries),
                'nonempty_count':sum(s.get('nonempty_count',0) for s in sheet_summaries),
                'formula_count':sum(s.get('formula_count',0) for s in sheet_summaries),
                'chart_parts':sum(1 for n in names if n.startswith('xl/charts/chart') and n.endswith('.xml')),
                'table_parts':sum(1 for n in names if n.startswith('xl/tables/table') and n.endswith('.xml')),
                'pivot_parts':sum(1 for n in names if n.startswith('xl/pivotTables/') and n.endswith('.xml')),
                'external_links':sum(1 for n in names if n.startswith('xl/externalLinks/externalLink') and n.endswith('.xml')),
                'has_vba':any(n.endswith('vbaProject.bin') for n in names),
                'vendor':vendor,
                'vendor_scores':{'acumen':ac,'ssi':ssis},
                'explicit_file_references':sorted(explicit_files),
                'project_strings':sorted(project_strings)[:500],
                'date_like_strings':sorted(date_like),
                'numeric_id_candidates':sorted(uid_numbers)[:20000],
                'header_hits':sorted(header_hits,key=lambda x:(-x['score'],x['sheet'],x['row']))[:100],
                'text_digest':hashlib.sha256('\n'.join(all_text).encode('utf-8','replace')).hexdigest(),
                'formula_digest':hashlib.sha256('\n'.join(all_formulas).encode('utf-8','replace')).hexdigest(),
                'cell_digest':cell_digest.hexdigest(),
                'all_text_sample':all_text[:500],
                'all_text_count':len(all_text),
            })
    except Exception as e:
        out['parse_error']=f'{type(e).__name__}: {e}'
        out['traceback']=traceback.format_exc(limit=5)
    return out


# ---------- Other formats ----------

def extract_utf16_strings(raw: bytes, min_chars: int=4) -> list[str]:
    # scan aligned UTF-16LE strings, preserving all printable runs
    out=[]
    for offset in (0,1):
        chars=[]
        i=offset
        while i+1<len(raw):
            code=raw[i] | (raw[i+1]<<8)
            ch=chr(code)
            if ch.isprintable() and ch not in '\x00\r\n\t' and code<0xFFFE:
                chars.append(ch)
            else:
                if len(chars)>=min_chars:
                    out.append(''.join(chars))
                chars=[]
            i+=2
        if len(chars)>=min_chars: out.append(''.join(chars))
    return out


def parse_afw(path: Path) -> dict[str, Any]:
    out={'kind':'afw'}
    try:
        b=path.read_bytes()
        raw=gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b
        strings=extract_utf16_strings(raw,4)
        ascii_strings=[m.group(0).decode('latin1','replace') for m in re.finditer(rb'[\x20-\x7e]{4,}',raw)]
        all_strings=list(dict.fromkeys(clean_text(s) for s in strings+ascii_strings if clean_text(s)))
        explicit=[]; project=[]; dates=[]; formulas=[]; metrics=[]
        for s in all_strings:
            low=s.lower()
            if re.search(r'\.(mpp|xer|xml|afw|xlsx)\b',low): explicit.append(s[:500])
            if any(k in low for k in ['project','hard_file','hard file','large test','tp1','tp2','tp3','tp4','evm','data center','commercial construction','usa otb']): project.append(s[:500])
            if re.search(r'\b(?:sum|average|countif|if|round|min|max)\s*\(',s,re.I): formulas.append(s[:2000])
            if any(k in low for k in ['missing logic','logic density','critical path','bei','cpli','float ratio','spi','cpi','tcpi','duration ratio','invalid dates','hard constraints']): metrics.append(s[:500])
            if re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',s): dates.append(s[:200])
        out.update({
            'compressed_size':len(b),'decompressed_size':len(raw),
            'decompressed_sha256':hashlib.sha256(raw).hexdigest(),
            'string_count':len(all_strings),
            'explicit_file_references':sorted(set(explicit)),
            'project_strings':sorted(set(project))[:1000],
            'date_strings':sorted(set(dates))[:500],
            'formula_strings':sorted(set(formulas))[:5000],
            'metric_strings':sorted(set(metrics))[:2000],
            'string_digest':hashlib.sha256('\n'.join(all_strings).encode('utf-8','replace')).hexdigest(),
            'string_sample':all_strings[:500],
        })
    except Exception as e:
        out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_docx(path: Path) -> dict[str, Any]:
    out={'kind':'docx'}
    try:
        with zipfile.ZipFile(path) as z:
            z.testzip(); names=z.namelist(); texts=[]
            parts=[n for n in names if n.startswith('word/') and n.endswith('.xml') and any(x in n for x in ['document.xml','header','footer','footnotes','endnotes','comments'])]
            for n in parts:
                root=ET.fromstring(z.read(n))
                for e in root.iter():
                    if lname(e.tag) in ('t','instrText') and e.text: texts.append(e.text)
            text='\n'.join(texts)
            out.update({'parts':parts,'text_count':len(texts),'word_count':len(text.split()),'text_digest':hashlib.sha256(text.encode('utf-8')).hexdigest(),'sample':text[:5000]})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_pdf(path: Path) -> dict[str, Any]:
    out={'kind':'pdf'}
    try:
        info=subprocess.run(['pdfinfo',str(path)],capture_output=True,text=True,timeout=60)
        meta={}
        if info.returncode==0:
            for line in info.stdout.splitlines():
                if ':' in line:
                    k,v=line.split(':',1); meta[k.strip()]=v.strip()
        txt=subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,text=True,timeout=300)
        text=txt.stdout
        out.update({'metadata':meta,'word_count':len(text.split()),'text_digest':hashlib.sha256(text.encode('utf-8','replace')).hexdigest(),'sample':text[:8000],'pdftotext_returncode':txt.returncode})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_image(path: Path) -> dict[str, Any]:
    out={'kind':'image'}
    try:
        from PIL import Image
        with Image.open(path) as im:
            out.update({'format':im.format,'width':im.width,'height':im.height,'mode':im.mode,'frames':getattr(im,'n_frames',1)})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_json_file(path: Path) -> dict[str, Any]:
    out={'kind':'json'}
    try:
        obj=json.loads(path.read_text(encoding='utf-8-sig'))
        out.update({'top_type':type(obj).__name__,'keys':list(obj)[:200] if isinstance(obj,dict) else None,'item_count':len(obj) if hasattr(obj,'__len__') else None,'json_digest':sha256_json(obj),'sample':json.dumps(obj,ensure_ascii=False)[:8000]})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_zip(path: Path) -> dict[str, Any]:
    out={'kind':'zip'}
    try:
        with zipfile.ZipFile(path) as z:
            bad=z.testzip()
            members=[]
            traversal=[]
            for i in z.infolist():
                n=i.filename
                pp=Path(n)
                if pp.is_absolute() or '..' in pp.parts: traversal.append(n)
                members.append({'name':n,'size':i.file_size,'compressed':i.compress_size,'crc':f'{i.CRC:08x}'})
            out.update({'member_count':len(members),'bad_member':bad,'path_traversal_members':traversal,'member_digest':sha256_json(members),'members':members})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_ppt(path: Path) -> dict[str, Any]:
    out={'kind':'ppt'}
    try:
        strings=subprocess.run(['strings','-el',str(path)],capture_output=True,text=True,timeout=60).stdout
        ascii_s=subprocess.run(['strings','-a',str(path)],capture_output=True,text=True,timeout=60).stdout
        text=strings+'\n'+ascii_s
        out.update({'string_count':len(text.splitlines()),'text_digest':hashlib.sha256(text.encode('utf-8','replace')).hexdigest(),'sample':text[:8000]})
    except Exception as e: out['parse_error']=f'{type(e).__name__}: {e}'
    return out


def parse_file(path: Path) -> dict[str, Any]:
    ext=path.suffix.lower()
    if ext in ('.mpp','.xml','.xer'):
        # XML that is not a schedule will be caught and separately summarized.
        d=parse_schedule(path)
        if d.get('parse_error') and ext=='.xml':
            try:
                root=ET.parse(path).getroot()
                d['xml_root']=lname(root.tag)
            except Exception as e:
                d['xml_parse_error']=str(e)
        if ext=='.mpp': d['ole_metadata']=ole_meta(path)
        return d
    if ext=='.xlsx': return parse_xlsx(path)
    if ext=='.afw': return parse_afw(path)
    if ext=='.docx': return parse_docx(path)
    if ext=='.pdf': return parse_pdf(path)
    if ext in ('.png','.jpg','.jpeg'): return parse_image(path)
    if ext=='.json': return parse_json_file(path)
    if ext=='.zip': return parse_zip(path)
    if ext=='.ppt': return parse_ppt(path)
    return {'kind':'unknown','file_cmd':subprocess.run(['file','-b',str(path)],capture_output=True,text=True).stdout.strip()}


# ---------- Inventory and association ----------

def relpath(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def build_inventory() -> tuple[list[dict[str,Any]], list[dict[str,Any]]]:
    paths=[]
    by_sha=defaultdict(list)
    for p in sorted((x for x in ROOT.rglob('*') if x.is_file()), key=lambda x:relpath(x).lower()):
        h=sha256_file(p)
        rec={'path':relpath(p),'filename':p.name,'extension':p.suffix.lower(),'size':p.stat().st_size,'sha256':h}
        paths.append(rec); by_sha[h].append(rec)
    unique=[]
    for idx,(h,rows) in enumerate(sorted(by_sha.items(), key=lambda kv:min(r['path'].lower() for r in kv[1]))):
        canonical=min(rows,key=lambda r:(len(Path(r['path']).parts),r['path'].lower()))
        p=ROOT/canonical['path']
        meta=parse_file(p)
        unique.append({
            'file_id':f'F{idx+1:04d}','sha256':h,'size':canonical['size'],'extension':canonical['extension'],
            'canonical_path':canonical['path'],'filename':canonical['filename'],'alias_count':len(rows),
            'aliases':[r['path'] for r in rows],'metadata':meta
        })
    id_by_sha={u['sha256']:u['file_id'] for u in unique}
    for p in paths: p['file_id']=id_by_sha[p['sha256']]
    return paths,unique


def schedule_label(u: dict[str,Any]) -> str:
    md=u['metadata']; props=md.get('properties',{})
    return props.get('ProjectTitle') or props.get('Name') or Path(u['filename']).stem


def workbook_text_blob(md: dict[str,Any]) -> str:
    parts=[]
    parts += md.get('sheets',[])
    parts += md.get('explicit_file_references',[])
    parts += md.get('project_strings',[])
    parts += md.get('all_text_sample',[])
    parts += [f'{k} {v}' for k,v in md.get('core_properties',{}).items()]
    for h in md.get('header_hits',[]): parts += h.get('values',[])
    return '\n'.join(clean_text(x) for x in parts if clean_text(x))


def afw_text_blob(md: dict[str,Any]) -> str:
    parts=[]
    for k in ['explicit_file_references','project_strings','date_strings','metric_strings','string_sample']:
        parts += md.get(k,[])
    return '\n'.join(clean_text(x) for x in parts if clean_text(x))


def path_family_tokens(path: str) -> set[str]:
    stop={'ref1','ref2','mpp','test','files','extracted','metric','history','report','acumen','ssi','fuse','xlsx','xml','afw'}
    return {t for t in norm_token(path).split() if len(t)>1 and t not in stop}


def score_oracle_schedule(oracle: dict[str,Any], schedule: dict[str,Any]) -> tuple[int,list[str]]:
    om=oracle['metadata']; sm=schedule['metadata']
    text=workbook_text_blob(om) if oracle['extension']=='.xlsx' else afw_text_blob(om)
    nt=norm_token(text)
    reasons=[]; score=0
    sched_filename=schedule['filename']; stem=norm_stem(sched_filename)
    title=norm_token(schedule_label(schedule))
    # explicit filename references are strongest
    expl=[norm_token(x) for x in om.get('explicit_file_references',[])]
    if stem and any(stem in x or x in stem for x in expl if len(x)>3):
        score+=120; reasons.append('explicit schedule filename/path reference')
    elif stem and stem in nt:
        score+=90; reasons.append('schedule filename stem appears in content')
    if title and len(title)>=4 and title in nt:
        score+=70; reasons.append('project title appears in content')
    props=sm.get('properties',{})
    status=props.get('StatusDate')
    if status:
        day=status.split('T')[0]
        variants={day}
        try:
            dt=datetime.fromisoformat(day)
            variants |= {f'{dt.month}/{dt.day}/{dt.year}',f'{dt.month}/{dt.day}/{str(dt.year)[2:]}'}
        except Exception: pass
        if any(v.lower() in text.lower() for v in variants):
            score+=20; reasons.append('status/data date appears in content')
    # task-name overlap from content sample/project strings. conservative, only distinctive names >=6 chars.
    s_names={x for x in sm.get('task_name_set',[]) if len(x)>=6 and not re.fullmatch(r'task\s*\d+',x)}
    if s_names:
        hits=[x for x in s_names if x in nt]
        ratio=len(hits)/len(s_names)
        if len(hits)>=20 or ratio>=0.5:
            score+=80; reasons.append(f'task-name overlap {len(hits)}/{len(s_names)}')
        elif len(hits)>=5:
            score+=35; reasons.append(f'task-name overlap {len(hits)}/{len(s_names)}')
        elif len(hits)>=1:
            score+=8; reasons.append(f'limited task-name overlap {len(hits)}')
    # numeric ID overlap (weak because IDs are common)
    oids=set(om.get('numeric_id_candidates',[]))
    suids=set(sm.get('task_uid_set',[]))
    if oids and suids:
        n=len(oids & suids)
        if n>=50 and n/max(1,len(suids))>=0.25:
            score+=50; reasons.append(f'UID/ID numeric overlap {n}')
        elif n>=10:
            score+=15; reasons.append(f'UID/ID numeric overlap {n}')
    # folder/context similarity is weak and never sufficient alone
    ot=path_family_tokens(oracle['canonical_path']); st=path_family_tokens(schedule['canonical_path'])
    common=ot&st
    if len(common)>=2:
        score+=15; reasons.append('same family/path context: '+','.join(sorted(common)[:8]))
    elif common:
        score+=5; reasons.append('one shared path token: '+next(iter(common)))
    # filename token overlap
    of=set(norm_stem(oracle['filename']).split()); sf=set(stem.split())
    fn=of&sf
    if len(fn)>=2:
        score+=15; reasons.append('filename token overlap: '+','.join(sorted(fn)))
    return score,reasons


def associate(unique: list[dict[str,Any]]) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    schedules=[u for u in unique if u['extension'] in SCHEDULE_EXTS and not u['metadata'].get('parse_error')]
    oracles=[u for u in unique if u['extension'] in ORACLE_EXTS]
    edges=[]; coverage={'vendor_xlsx_total':0,'vendor_xlsx_associated':0,'vendor_xlsx_unresolved':[],'all_oracles':len(oracles)}
    for o in oracles:
        scored=[]
        for s in schedules:
            sc,rs=score_oracle_schedule(o,s)
            if sc>0: scored.append((sc,s,rs))
        scored.sort(key=lambda x:(-x[0],x[1]['canonical_path'].lower()))
        # multi-project workbooks can legitimately have several high candidates. Retain all within 30 of top and >=50.
        selected=[]
        if scored:
            top=scored[0][0]
            selected=[x for x in scored if x[0]>=50 and x[0]>=top-30]
        vendor=o['metadata'].get('vendor') if o['extension']=='.xlsx' else 'Acumen Fuse Workspace'
        if o['extension']=='.xlsx' and vendor in ('Acumen Fuse','SSI Tools','Acumen+SSI/Mixed'):
            coverage['vendor_xlsx_total']+=1
        if selected:
            if o['extension']=='.xlsx' and vendor in ('Acumen Fuse','SSI Tools','Acumen+SSI/Mixed'):
                coverage['vendor_xlsx_associated']+=1
            for sc,s,rs in selected:
                confidence='confirmed' if sc>=150 else 'probable' if sc>=90 else 'tentative'
                edges.append({'oracle_file_id':o['file_id'],'oracle_path':o['canonical_path'],'oracle_vendor':vendor,
                              'schedule_file_id':s['file_id'],'schedule_path':s['canonical_path'],'schedule_title':schedule_label(s),
                              'score':sc,'confidence':confidence,'evidence':rs})
        else:
            if o['extension']=='.xlsx' and vendor in ('Acumen Fuse','SSI Tools','Acumen+SSI/Mixed'):
                coverage['vendor_xlsx_unresolved'].append({'file_id':o['file_id'],'path':o['canonical_path'],'vendor':vendor,'top_candidates':[
                    {'schedule':x[1]['canonical_path'],'score':x[0],'evidence':x[2]} for x in scored[:5]
                ]})
    # schedule equivalence edges based on fingerprints
    sched_edges=[]
    for i,a in enumerate(schedules):
        for b in schedules[i+1:]:
            af=a['metadata'].get('fingerprints',{}); bf=b['metadata'].get('fingerprints',{})
            same=[]
            for k in ['identity','logic','schedule','calendar','resource','combined']:
                if af.get(k) and af.get(k)==bf.get(k): same.append(k)
            if same:
                sched_edges.append({'left_file_id':a['file_id'],'left_path':a['canonical_path'],'right_file_id':b['file_id'],'right_path':b['canonical_path'],'matching_fingerprints':same})
    coverage['vendor_xlsx_rate']=coverage['vendor_xlsx_associated']/coverage['vendor_xlsx_total'] if coverage['vendor_xlsx_total'] else 1.0
    return edges, {'coverage':coverage,'schedule_equivalence_edges':sched_edges}


def main() -> None:
    print('Building full path and unique payload inventory...', flush=True)
    paths,unique=build_inventory()
    print(f'Parsed {len(paths)} paths / {len(unique)} unique payloads', flush=True)
    edges,assoc_meta=associate(unique)
    result={
        'generated':datetime.now().isoformat(),
        'source_root':str(ROOT),
        'process_version':'hardened-audit-v1',
        'tool_versions':{
            'python':sys.version,
            'mpxj_python':getattr(mpxj,'__file__',''),
            'jpype':getattr(jpype,'__version__',''),
            'java':subprocess.run(['java','-version'],capture_output=True,text=True).stderr.splitlines()[:3],
        },
        'path_count':len(paths),'unique_payload_count':len(unique),
        'extension_counts':dict(Counter(p['extension'] for p in paths)),
        'unique_extension_counts':dict(Counter(u['extension'] for u in unique)),
        'paths':paths,'files':unique,'associations':edges,**assoc_meta,
    }
    (OUT/'HARDENED_CORPUS_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # flattened files CSV
    with (OUT/'HARDENED_FILE_INVENTORY.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['file_id','canonical_path','filename','extension','size','sha256','alias_count','kind','parse_error','vendor','project_title','status_date','task_count','relation_count','sheet_count','cell_count','formula_count','explicit_file_references']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for u in unique:
            md=u['metadata']; props=md.get('properties',{}); counts=md.get('counts',{})
            w.writerow({
                'file_id':u['file_id'],'canonical_path':u['canonical_path'],'filename':u['filename'],'extension':u['extension'],'size':u['size'],'sha256':u['sha256'],'alias_count':u['alias_count'],
                'kind':md.get('kind'),'parse_error':md.get('parse_error',''),'vendor':md.get('vendor',''),'project_title':props.get('ProjectTitle') or props.get('Name') or md.get('ole_metadata',{}).get('title',''),
                'status_date':props.get('StatusDate',''),'task_count':counts.get('tasks_all',''),'relation_count':counts.get('relations',''),'sheet_count':len(md.get('sheets',[])),
                'cell_count':md.get('cell_count',''),'formula_count':md.get('formula_count',''),'explicit_file_references':' | '.join(md.get('explicit_file_references',[])[:100])
            })
    with (OUT/'HARDENED_ORACLE_SCHEDULE_CROSSWALK.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['oracle_file_id','oracle_path','oracle_vendor','schedule_file_id','schedule_path','schedule_title','score','confidence','evidence']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for e in edges:
            row=dict(e); row['evidence']=' | '.join(row['evidence']); w.writerow(row)
    with (OUT/'HARDENED_UNRESOLVED_VENDOR_XLSX.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['file_id','path','vendor','top_candidates']
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for e in assoc_meta['coverage']['vendor_xlsx_unresolved']:
            row=dict(e); row['top_candidates']=json.dumps(row['top_candidates'],ensure_ascii=False); w.writerow(row)
    print(json.dumps({k:result[k] for k in ['path_count','unique_payload_count','extension_counts','unique_extension_counts']},indent=2), flush=True)
    print(json.dumps(assoc_meta['coverage'],indent=2), flush=True)

if __name__=='__main__':
    main()

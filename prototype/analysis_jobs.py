"""Short SQLite transactions; spatial work runs outside the portal state lock."""
import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
import analysis_engine as engine
from capabilities import require

def dump(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)
def now():return datetime.now(timezone.utc).isoformat()
def initialize(db):
    with sqlite3.connect(db) as c:
        c.execute('CREATE TABLE IF NOT EXISTS analysis_inputs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, original TEXT NOT NULL, normalized TEXT NOT NULL, crs TEXT NOT NULL, created TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS analysis_jobs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, input_id TEXT NOT NULL, name TEXT NOT NULL, request_key TEXT NOT NULL, digest TEXT NOT NULL, snapshot TEXT NOT NULL, status TEXT NOT NULL, result TEXT, error TEXT, created TEXT NOT NULL, started REAL, token TEXT, UNIQUE(owner,request_key))')

        if 'progress' not in {r[1] for r in c.execute('PRAGMA table_info(analysis_jobs)')}:c.execute('ALTER TABLE analysis_jobs ADD COLUMN progress TEXT')

class JobCancelled(Exception):pass

def check_area(data,limit):
    if limit is None:return
    from shapely.geometry import shape
    from shapely.ops import transform
    areas=[transform(engine.PROJECT,shape(f['geometry'])).area/10000 for f in data['features']]
    require(all(a<=limit for a in areas) and sum(areas)<=limit,'单地块或本批次面积超过成果查询上限（'+str(limit)+'公顷）')

def own(c,table,id,user):
    row=c.execute(f'SELECT * FROM {table} WHERE id=? AND owner=?',(id,user)).fetchone()
    require(row is not None,'记录不存在或无访问权限',404);return dict(row)

def dispatch(db,user,action,p,area_limit=None):
    require(isinstance(p,dict),'参数格式错误')
    if action=='analysis.catalog':return engine.catalog()
    if action=='analysis.spatial':
        data=engine.normalize(p.get('geometry'),p.get('crs'))
        check_area(data,area_limit)
        return engine.spatial_tool(data,p.get('operation'),p.get('distance',0))
    if action=='analysis.input':
        original=p.get('geometry'); normalized=engine.normalize(original,p.get('crs'))
        check_area(normalized,area_limit)
        ident=uuid.uuid4().hex
        with sqlite3.connect(db) as c:c.execute('INSERT INTO analysis_inputs VALUES(?,?,?,?,?,?)',(ident,user,dump(original),dump(normalized),p['crs'],now()))
        return dict(id=ident,normalized=normalized,count=len(normalized['features']),crs='EPSG:4326')
    with sqlite3.connect(db,timeout=10) as c:
        c.row_factory=sqlite3.Row
        if action=='analysis.create':
            source=own(c,'analysis_inputs',p.get('inputId'),user)
            check_area(json.loads(source['normalized']),area_limit)
            key=p.get('requestKey');name=p.get('name','地块核查')
            require(isinstance(key,str) and 1<=len(key)<=100,'缺少有效幂等键')
            require(isinstance(name,str) and 0<len(name.strip())<=100,'任务名称需为 1～100 字')
            snapshot=engine.catalog();snapshot.pop('sample')
            digest=hashlib.sha256(dump([source['id'],name,snapshot]).encode()).hexdigest()
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT id,digest FROM analysis_jobs WHERE owner=? AND request_key=?',(user,key)).fetchone()
            if old:
                require(old['digest']==digest,'幂等键已用于不同任务',409);return dict(id=old['id'])
            ident=uuid.uuid4().hex
            c.execute('INSERT INTO analysis_jobs(id,owner,input_id,name,request_key,digest,snapshot,status,created) VALUES(?,?,?,?,?,?,?,?,?)',(ident,user,source['id'],name,key,digest,dump(snapshot),'排队中',now()))
            normalized=json.loads(source['normalized']);progress=dict(total=len(normalized['features']),completed=0,parcels=[dict(id=f['properties']['id'],name=f['properties']['name'],status='排队中') for f in normalized['features']])
            c.execute('UPDATE analysis_jobs SET progress=? WHERE id=?',(dump(progress),ident))
            return dict(id=ident)
        if action=='analysis.list':
            return [dict(r) for r in c.execute('SELECT id,name,status,created FROM analysis_jobs WHERE owner=? ORDER BY created DESC LIMIT 50',(user,))]
        job=own(c,'analysis_jobs',p.get('id'),user)
        if action=='analysis.cancel':
            c.execute("UPDATE analysis_jobs SET status='已取消' WHERE id=? AND status IN ('排队中','运行中')",(job['id'],));return {'ok':True}
        if action=='analysis.get':
            return {k:json.loads(v) if k in ['result','progress'] and v else v for k,v in job.items() if k in ('id','name','status','error','created','result','progress')}
        if action=='analysis.export':
            require(job['result'] is not None,'任务尚无结果',409)
            from analysis_reports import export
            return export(job,p.get('format'))
        require(False,'分析接口不存在',404)

def work_once(db):
    with sqlite3.connect(db,timeout=10) as c:
        c.row_factory=sqlite3.Row;c.execute('BEGIN IMMEDIATE')
        c.execute("UPDATE analysis_jobs SET status='失败', error='执行中断或超时，请重新运行' WHERE status='运行中' AND started<?",(time.time()-120,))
        row=c.execute("SELECT * FROM analysis_jobs WHERE status='排队中' ORDER BY created LIMIT 1").fetchone()
        if not row:return False
        job=dict(row);token=uuid.uuid4().hex
        c.execute("UPDATE analysis_jobs SET status='运行中',started=?,token=? WHERE id=?",(time.time(),token,job['id']))
        source=c.execute('SELECT normalized, crs FROM analysis_inputs WHERE id=?',(job['input_id'],)).fetchone()
    def progress(done,current):
        finished={p['id']:p for p in done};data=json.loads(source[0]);items=[dict(id=f['properties']['id'],name=f['properties']['name'],status='已完成' if f['properties']['id'] in finished else '运行中' if f['properties']['id']==current else '等待中',state=finished.get(f['properties']['id'],{}).get('state','')) for f in data['features']]
        with sqlite3.connect(db,timeout=10) as c:
            updated=c.execute("UPDATE analysis_jobs SET progress=? WHERE id=? AND status='运行中' AND token=?",(dump(dict(total=len(items),completed=len(done),parcels=items)),job['id'],token))
            if not updated.rowcount:raise JobCancelled()
    try:
        result=engine.analyze(json.loads(source[0]),json.loads(job['snapshot']),progress_callback=progress);result['sourceCRS']=source[1];status='部分完成' if result['state']=='无法判定' else '成功';error=None
    except JobCancelled:return True
    except Exception:
        result=None;status='失败';error='空间计算失败，请检查几何和数据后重新运行'
    with sqlite3.connect(db,timeout=10) as c:
        c.execute("UPDATE analysis_jobs SET status=?,result=?,error=? WHERE id=? AND status='运行中' AND token=?",(status,dump(result) if result else None,error,job['id'],token))
    return True

def worker(db):
    while True:
        try:
            if work_once(db):continue
        except sqlite3.Error:pass
        time.sleep(.5)

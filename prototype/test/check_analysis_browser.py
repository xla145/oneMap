"""End-to-end checks via agent-browser; run against an isolated --db server."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5217')
ROOT=Path(__file__).resolve().parents[1]/'reports'
ROOT.mkdir(exist_ok=True)
(ROOT/'screenshots').mkdir(exist_ok=True)
SESSION='analysis-acceptance'
checks=[]
def browser(*args,script=None):
    p=subprocess.run(['agent-browser','--session',SESSION,'--json',*args],input=script,text=True,capture_output=True,timeout=35)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    r=json.loads(p.stdout)
    if not r.get('success'):raise RuntimeError(r)
    return r.get('data',{})
def ev(s):return browser('eval','--stdin',script=s)['result']
def ready(expr):
    for _ in range(40):
        if ev(expr):return
        time.sleep(.25)
    raise AssertionError('Timeout: '+expr)
def click(selector):
    ev('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center"})')
    browser('click',selector)
def check(name,condition):
    assert condition,name
    checks.append(name)
try:
    browser('set','viewport','1440','1000')
    browser('open',BASE+'/#/front/capabilities/compliance')
    ready("!!document.querySelector('#ana-map canvas')")
    click('[data-analysis="sample"]');click('[data-analysis="run"]')
    ready("document.querySelectorAll('#ana-result tbody tr').length===6")
    check('conflict and clear parcels',ev("document.querySelector('#ana-result').textContent.includes('未发现所选规则冲突') && document.querySelector('#ana-result').textContent.includes('发现冲突')"))
    ev("window.downloadNames=[];const old=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download)window.downloadNames.push(this.download);return old.call(this)}")
    for format in ['html','csv','geojson']:click('[data-format="'+format+'"]')
    ready('window.downloadNames.length===3')
    check('three result exports',ev('window.downloadNames.length')==3)
    click('[data-analysis="locate"]')
    browser('screenshot',str(ROOT/'screenshots/analysis-desktop.png'),'--full')
    clear={'type':'Polygon','coordinates':[[[111.82,40.86],[111.85,40.86],[111.85,40.89],[111.82,40.89],[111.82,40.86]]]}
    file=Path(tempfile.gettempdir())/'analysis-upload-clear.geojson';file.write_text(json.dumps(clear))
    browser('upload','#ana-file',str(file));ready("document.querySelector('#ana-status').textContent.includes('已读取')")
    click('[data-analysis="run"]');ready("document.querySelectorAll('#ana-result tbody tr').length===3")
    check('uploaded clear parcel',ev("document.querySelector('#ana-result h2').textContent==='未发现所选规则冲突'"))
    browser('fill','#ana-geometry','[[0,0],[1,1],[1,0],[0,1],[0,0]]');click('[data-analysis="validate"]')
    ready("document.querySelector('#ana-status').textContent.includes('几何无效')")
    check('invalid geometry visible',True)
    for width in [1440,1024,390]:
        browser('set','viewport',str(width),'900')
        check(f'compliance layout {width}',ev('document.documentElement.scrollWidth<=innerWidth+1'))
    browser('screenshot',str(ROOT/'screenshots/analysis-mobile.png'),'--full')
    browser('open',BASE+'/#/front/capabilities/overlay')
    ready("!!document.querySelector('#ana-map canvas')")
    click('[data-analysis="sample"]')
    browser('select','#ana-operation','union');click('[data-analysis="spatial"]')
    ready("document.querySelector('#ana-status').textContent.includes('融合去重面积')")
    check('overlay union returns real geometry',ev("document.querySelector('#analysis-workbench').spatialResult.features.length===1"))
    browser('select','#ana-operation','intersection');click('[data-analysis="spatial"]')
    ready("document.querySelector('#ana-status').textContent.includes('结果为空')")
    check('disjoint intersection empty',True)
    check('overlay mobile layout',ev('document.documentElement.scrollWidth<=innerWidth+1'))
    errors=browser('errors');check('no browser errors',not errors.get('errors'))
    (ROOT/'analysis-browser-checks.json').write_text(json.dumps({'checks':checks,'browserErrors':errors},ensure_ascii=False,indent=2))
    print(f'{len(checks)} analysis browser checks passed',flush=True)
finally:browser('close')

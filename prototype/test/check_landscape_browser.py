"""Landscape routes and editor workflow, against an isolated --db server."""
import json, os, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5219')
SESSION='landscape-acceptance';checks=[]
def b(*args):
 p=subprocess.run(['agent-browser','--session',SESSION,'--json',*args],capture_output=True,text=True,timeout=35)
 if p.returncode:raise RuntimeError(p.stderr or p.stdout)
 r=json.loads(p.stdout)
 if not r.get('success'):raise RuntimeError(r)
 return r.get('data',{})
def ev(s):return b('eval',s)['result']
def wait(s):
 for _ in range(35):
  if ev(s):return
  time.sleep(.2)
 raise AssertionError(s)
def click(s):
 ev('document.querySelector('+json.dumps(s)+').scrollIntoView({block:"center"})');b('click',s)
try:
 for width in [1440,1024,390]:
  b('set','viewport',str(width),'1000')
  for topic in ['', 'landscape','planning','energy','public','ecology']:
   b('open',BASE+'/#/front/landscape'+('/'+topic if topic else ''))
   wait("!!document.querySelector('#main canvas')")
   r=ev("({overflow:document.documentElement.scrollWidth>innerWidth+1,images:[...document.querySelectorAll('#main img')].every(i=>(i.loading==='lazy'&&!i.complete)||(i.complete&&i.naturalWidth>0)),chapters:document.querySelectorAll('.scenic-chapters details').length,cards:document.querySelectorAll('.scenic-story').length})")
   assert not r['overflow'] and r['images'],(width,topic,r)
   assert r['chapters']>=3 if topic else r['cards']==5,(topic,r)
   checks.append(dict(width=width,topic=topic or 'overview',passed=True))
   if width==390 and topic=='ecology':b('screenshot',str(ROOT/'screenshots/landscape-ecology-mobile.png'),'--full')
   if width==1440 and topic=='ecology':b('screenshot',str(ROOT/'screenshots/landscape-ecology-desktop.png'))
 print('18 responsive landscape routes passed',flush=True)
 b('set','viewport','1440','1000')
 ev("sessionStorage.setItem('onemap-user','admin')")
 b('open',BASE+'/#/admin/public-portal?tab=topics')
 wait("!!document.querySelector('[data-action=\"pub-edit\"][data-id=\"topics:ecology\"]')")
 click('[data-action="pub-edit"][data-id="topics:ecology"]')
 wait("!!document.querySelector('[name=sectionTitle0]')")
 assert ev("document.querySelector('[name=sectionText0]').value.length>20")
 b('fill','[name="sectionTitle0"]','验收章节：生态工程导读')
 click('#pub-editor button')
 wait("!document.querySelector('#dialog').open")
 b('open',BASE+'/#/front/landscape/ecology');wait("!!document.querySelector('.scenic-chapters')")
 assert not ev("document.querySelector('#main').textContent.includes('验收章节：生态工程导读')")
 b('open',BASE+'/#/admin/public-portal?tab=topics');wait("!!document.querySelector('[data-action=\"pub-publish\"][data-id=\"topics:ecology\"]')")
 click('[data-action="pub-publish"][data-id="topics:ecology"]')
 wait("document.querySelector('[data-action=\"pub-publish\"][data-id=\"topics:ecology\"]').closest('section').textContent.includes('已发布')")
 b('open',BASE+'/#/front/landscape/ecology');wait("document.querySelector('#main')?.textContent.includes('验收章节：生态工程导读')")
 checks.append(dict(workflow='draft isolation and publish',passed=True))
 errors=b('errors');assert not errors.get('errors'),errors
 (ROOT/'landscape-browser-checks.json').write_text(json.dumps(dict(checks=checks,browserErrors=errors),ensure_ascii=False,indent=2))
 print('Editor draft/publication passed; no browser errors',flush=True)
finally:b('close')

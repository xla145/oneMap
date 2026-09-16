"""Optional browser smoke check. Requires agent-browser on PATH and running server."""
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5190')

def browser(*args,script=None):
    r=subprocess.run(['agent-browser','--session','intelligence-qa',*args],input=script,text=True,capture_output=True,timeout=30)
    if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    return r.stdout.strip()

def inspect():
    raw=browser('eval','--stdin',script='''(async()=>{for(let i=0;i<30&&!window.appReady;i++)await new Promise(r=>setTimeout(r,100));return JSON.stringify({url:location.hash,ready:!!window.appReady,heading:document.querySelector('main h1,main h2')?.textContent||'',overflow:document.documentElement.scrollWidth>innerWidth,blank:!document.querySelector('main')?.innerText.trim(),brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length});})()''')
    value=json.loads(raw)
    return json.loads(value) if isinstance(value,str) else value

def main():
    rows=[]
    for width,routes in [(1440,['front/home','front/assistant','front/agents','front/catalog','front/applications','front/profile','admin/overview','admin/agents','admin/resources','admin/indicators','admin/knowledge','admin/corpora','admin/memories','admin/calls','admin/approvals','admin/settings']),(390,['front/home','front/assistant','front/catalog','front/profile','admin/resources','admin/overview']),(1920,['front/home','admin/overview'])]:
        browser('set','viewport',str(width),'1080' if width>=1440 else '844')
        for route in routes:
            browser('open',BASE+'/#/'+route)
            value=inspect();value['width']=width
            assert value['ready'] and not value['blank'] and not value['overflow'] and not value['brokenImages'],value
            rows.append(value)
            print(f"OK {width} {route}",flush=True)
            if (width,route) in [(1440,'front/home'),(1440,'admin/overview'),(390,'front/home'),(390,'admin/resources')]:
                browser('screenshot',str(ROOT/'screenshots'/f"v2-{route.replace('/','-')}-{width}.png"),'--full')
    errors=browser('errors')
    if errors: raise AssertionError(errors)
    (ROOT/'capability-layout-checks.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    print(f'{len(rows)} page/viewport checks passed; no browser errors.',flush=True)

if __name__=='__main__':main()

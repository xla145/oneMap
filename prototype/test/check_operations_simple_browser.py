"""Read-only layout/navigation checks. Point DEMO_QA_URL at an isolated QA server."""
import json
import os
from pathlib import Path
import subprocess

BASE = os.environ['DEMO_QA_URL'].rstrip('/')
SESSION = 'operations-simple-layout'
ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
ROUTES = ['overview','todos','settings','collection/overview','collection/tasks','collection/orders','collection/registrations','collection/imports','collection/batches','quality/models','quality/tasks','quality/results','quality/reports','quality/orders','catalog/systems','catalog/sources','catalog/directories','catalog/assets','catalog/relations','standards/definitions','standards/changes','warehouse/domains','warehouse/tables','publishing/apis','publishing/layers','monitoring/overview','monitoring/collection','monitoring/calls','monitoring/inspections','monitoring/rules','monitoring/alerts']

def browser(*args, script=None):
    result = subprocess.run(['agent-browser','--session',SESSION,*args], input=script, text=True, capture_output=True, timeout=30)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()

def evaluate(script):
    return json.loads(browser('eval','--stdin',script=script))

def page(route, user='admin'):
    evaluate(f"sessionStorage.setItem('onemap-user',{json.dumps(user)});null")
    browser('open',BASE+'/#/'+route)
    # Bound the wait within the page so failed assertions cannot lock the browser daemon.
    result=evaluate("""(async()=>{for(let i=0;i<80;i++){if(window.appReady&&document.querySelector('main h1'))return {heading:document.querySelector('main h1').textContent,overflow:document.documentElement.scrollWidth>innerWidth,menu:[...document.querySelectorAll('[data-menu-group=operations] a')].map(x=>x.textContent.trim())};await new Promise(r=>setTimeout(r,100));}throw Error('Page did not become ready')})()""")
    assert not result['overflow'],(route,result)
    return result

if __name__=='__main__':
    REPORTS.mkdir(exist_ok=True);(REPORTS/'screenshots').mkdir(exist_ok=True)
    browser('open',BASE)
    results=[]
    for width in [1440,390]:
        browser('set','viewport',str(width),'1000')
        for route in ROUTES:
            result=page('admin/operations/'+route)
            assert result['heading'] not in ['页面不存在','暂无管理权限','运营中心正在准备'],(route,result)
            assert result['menu']==['工作台','数据归集','数据资产','运行监控','配置管理'],result
            results.append(dict(width=width,route=route,**result))
            if route in ['overview','settings']:
                browser('screenshot',str(REPORTS/'screenshots'/('operations-simple-'+route+'-'+str(width)+'.png')))
    forbidden=page('admin/operations/settings','u1')
    assert forbidden['heading']=='暂无管理权限',forbidden
    allowed=page('front/operations/todos','u1')
    assert allowed['heading']=='我的运营待办',allowed
    errors=browser('errors')
    assert not errors,errors
    (REPORTS/'operations-simple-browser-checks.json').write_text(json.dumps(dict(pages=results,permissions=[forbidden,allowed],browserErrors=errors),ensure_ascii=False,indent=2))
    print(f'{len(results)} desktop/mobile route checks and 2 permission views passed.')
    browser('close')

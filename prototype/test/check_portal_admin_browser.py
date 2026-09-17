"""Run only against an isolated QA server: this exercises publishing and account review."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5197')
SESSION='portal-admin-qa'
ROOT=Path(__file__).resolve().parent

def browser(*args,script=None):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],input=script,text=True,capture_output=True,timeout=40)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def ev(script):
    raw=browser('eval','--stdin',script=script)
    return json.loads(raw) if raw else None
def wait(expression):browser('wait','--fn',expression)
def page(route,user='admin'):
    ev(f"sessionStorage.setItem('onemap-user',{json.dumps(user)});")
    browser('open',BASE+'/#/'+route);wait('window.appReady === true')
    if route in ['admin/portal-analytics','admin/portal-audit']:wait("!!document.querySelector('#pm-report table, #pm-report .pm-metrics')")
    if route in ['admin/portal-security','admin/portal-monitor']:wait("!!document.querySelector('#ops-content table')")
    wait("!!document.querySelector('main h1')")
    info=ev("({heading:document.querySelector('main h1').textContent,overflow:document.documentElement.scrollWidth>innerWidth})")
    assert not info['overflow'],(route,info)
    return info

def click(selector):
    browser('scrollintoview',selector)
    browser('click',selector)
def fill(selector,value):browser('fill',selector,value)
def submit(selector):click(selector+' button[type=submit], '+selector+' button:not([type])')
def api(action,payload,user='admin'):
    req=Request(BASE+'/api/action',data=json.dumps(dict(action=action,payload=payload)).encode(),headers={'Content-Type':'application/json','X-Demo-User':user})
    with urlopen(req) as r:return json.load(r)

def main():
    browser('open',BASE);wait('window.appReady === true')
    browser('set','viewport','1440','1000')
    routes=['admin/resources','admin/portal-tools','admin/portal-keys','admin/portal-users','admin/portal-roles','admin/portal-materials','admin/portal-audit','admin/portal-security','admin/portal-monitor','admin/portal-analytics','admin/public-portal?tab=services']
    results=[]
    for route in routes:
        results.append(dict(route=route,width=1440,**page(route)));print('OK',route,flush=True)
    page('admin/portal-tools')
    click('[data-menu-group="tools"] > summary')
    assert ev("!document.querySelector('[data-menu-group=tools]').open")
    browser('reload');wait('window.appReady === true')
    assert ev("!document.querySelector('[data-menu-group=tools]').open")
    click('[data-menu-group="tools"] > summary')
    browser('screenshot',str(ROOT/'screenshots'/'portal-admin-tools.png'))
    # Register and publish a custom tool through the UI.
    click('[data-action=pm-edit][data-id="tools:"]')
    fill('#pm-editor [name=name]','浏览器验收工具');fill('#pm-editor [name=category]','验收工具')
    fill('#pm-editor [name=url]','https://example.org/tool');submit('#pm-editor')
    wait("!document.querySelector('#dialog').open")
    tool_id=ev("[...document.querySelectorAll('tbody tr')].find(r=>r.textContent.includes('浏览器验收工具')).querySelector('[data-action=pm-publish]').dataset.id")
    # Tool publication now requires approval of the current configuration.
    def tool_revision():
        req=Request(BASE+'/api/bootstrap',headers={'X-Demo-User':'admin','X-Demo-Mode':'admin'})
        with urlopen(req) as response:state=json.load(response)
        return next(r['rev'] for r in state['portalManagement']['tools'] if r['id']==tool_id.split(':')[1])
    api('centers.tool.submit',dict(id=tool_id.split(':')[1],rev=tool_revision()))
    api('centers.tool.review',dict(id=tool_id.split(':')[1],rev=tool_revision(),decision='通过',note='浏览器验收配置审核通过'))
    browser('reload');wait('window.appReady === true')
    click('[data-action=pm-publish][data-id="'+tool_id+'"]');browser('wait','--text','发布成功')
    page('front/capabilities','u1');assert ev("document.querySelector('main').textContent.includes('浏览器验收工具')")
    page('admin/portal-tools');click('[data-action=pm-disable][data-id="'+tool_id+'"]');browser('wait','--text','已下架')
    page('front/capabilities/'+tool_id.split(':')[1],'u1');assert ev("document.querySelector('main').textContent.includes('工具已下架')")
    print('OK tool publish and disable',flush=True)
    # Upload a real file; its published metadata must appear on the front page.
    page('admin/portal-materials');click('[data-action=pm-edit][data-id="materials:"]')
    fill('#pm-editor [name=name]','浏览器验收资料');fill('#pm-editor [name=category]','技术标准')
    with tempfile.NamedTemporaryFile(suffix='.txt',mode='w',delete=False) as f:f.write('门户资料附件验收');filename=f.name
    browser('upload','#pm-editor [name=file]',filename);submit('#pm-editor');wait("!document.querySelector('#dialog').open")
    material_id=ev("[...document.querySelectorAll('tbody tr')].find(r=>r.textContent.includes('浏览器验收资料')).querySelector('[data-action=pm-publish]').dataset.id")
    click('[data-action=pm-publish][data-id="'+material_id+'"]');browser('wait','--text','发布成功')
    page('front/knowledge','u1');assert ev("document.querySelector('.pm-downloads').textContent.includes('浏览器验收资料')")
    click('[data-action=pm-download]');browser('wait','--text','资料已下载');Path(filename).unlink()
    print('OK attachment publication and download',flush=True)
    # Registration review and enterprise role.
    page('front/register','u1');fill('#pm-register [name=name]','浏览器验收用户');fill('#pm-register [name=department]','验收单位');fill('#pm-register [name=contact]','qa-'+str(time.time_ns())+'@example.invalid');fill('#pm-register [name=reason]','门户业务功能验收');submit('#pm-register');browser('wait','--text','申请已提交')
    page('admin/portal-users');click('[data-action=pm-review]');browser('select','#pm-review [name=portalRole]','企业用户');fill('#pm-review [name=note]','演示资料完整，同意开通');submit('#pm-review');browser('wait','--text','审核完成')
    page('admin/portal-roles');assert ev("[...document.querySelectorAll('tbody tr')].some(r=>r.textContent.includes('浏览器验收用户')&&r.textContent.includes('企业用户'))")
    print('OK registration review and role',flush=True)
    # API key review, one-time activation, real API call, disabled-key rejection.
    page('front/api-keys','u1');click('[data-action=ops-key-apply]');browser('select','#ops-key-apply [name=scope]','tool:coordinate');fill('#ops-key-apply [name=purpose]','浏览器接口验收');submit('#ops-key-apply');browser('wait','--text','密钥申请已提交')
    page('admin/portal-keys');click('[data-action=ops-key-review]');fill('#ops-key-review [name=note]','同意演示集成');submit('#ops-key-review');browser('wait','--text','审核完成')
    page('front/api-keys','u1');click('[data-action=ops-key-activate]');wait("!!document.querySelector('.pm-secret')")
    secret=ev("document.querySelector('.pm-secret').value")
    request=Request(BASE+'/api/v1/tools/invoke',data=json.dumps(dict(toolId='coordinate',parameters=dict(x=111.7,y=40.8))).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+secret})
    with urlopen(request) as response:assert json.load(response)['result']['crs']=='EPSG:3857'
    click('[data-action=close]');page('admin/portal-keys');click('[data-action=ops-key-toggle]');browser('wait','--text','密钥状态已更新')
    try:urlopen(request);raise AssertionError('Disabled key accepted')
    except HTTPError as error:assert error.code==401
    print('OK API key review, invocation and revocation',flush=True)
    page('front/capabilities/coordinate','u1');click('#pub-tool button');browser('wait','--text','转换结果')
    page('admin/portal-analytics');assert ev("Number(document.querySelectorAll('.pm-metric strong')[4].textContent)>0")
    page('admin/portal-audit');fill('#pm-report-filter [name=q]','tools.invoke');submit('#pm-report-filter');wait("document.querySelector('#pm-report')?.textContent.includes('401')")
    page('admin/portal-security');click('[data-action=ops-backup]');browser('wait','--text','备份已创建');wait("!!document.querySelector('[data-action=ops-restore]')")
    print('OK telemetry, audit and database backup',flush=True)
    for route in ['admin/portal-tools','admin/portal-security','admin/portal-monitor','admin/portal-analytics','admin/portal-keys','front/register','front/knowledge']:
        browser('set','viewport','390','844');results.append(dict(route=route,width=390,**page(route,'u1' if route.startswith('front/') else 'admin')));print('OK mobile',route,flush=True)
    page('admin/portal-tools');browser('screenshot',str(ROOT/'screenshots'/'portal-admin-mobile.png'))
    browser('set','viewport','1440','1000');page('admin/portal-analytics');browser('screenshot',str(ROOT/'screenshots'/'portal-admin-analytics.png'))
    errors=browser('errors');assert not errors,errors
    (ROOT/'portal-admin-browser-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print('Portal administration browser checks passed.',flush=True)

if __name__=='__main__':main()

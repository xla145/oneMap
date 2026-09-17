"""Run against an isolated server only. Real UI saves and published views."""
import json,os,subprocess,time
from pathlib import Path
from urllib.request import Request,urlopen
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5298')
SESSION='integration-v2'
def browser(*args):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],capture_output=True,text=True,timeout=35)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def ev(js):return json.loads(browser('eval',js))
def wait(js):browser('wait','--fn',js)
def click(s):
    ev('document.querySelector('+json.dumps(s)+').scrollIntoView({block:"center",inline:"nearest"})')
    browser('click',s)
def fill(s,v):browser('fill',s,v)
def page(route,user='admin'):
    ev('sessionStorage.setItem("onemap-user",'+json.dumps(user)+')')
    browser('open',BASE+'/#/'+route);browser('reload');wait('window.appReady === true')
def api(op,p):
    req=Request(BASE+'/api/action',data=json.dumps(dict(action=op,payload=p)).encode(),headers={'Content-Type':'application/json','X-Demo-User':'admin'})
    with urlopen(req) as response:return json.load(response)
def main():
    browser('open',BASE);browser('set','viewport','1440','1000');page('admin/center-integration')
    for tab in ['overview','presentation','announcements','placement','monitor','systems','national','vertical','tenants','horizontal']:
        page('admin/center-integration?tab='+tab)
        if tab=='monitor':wait('!!document.querySelector(".ig-columns")')
        assert not ev('document.documentElement.scrollWidth>innerWidth'),tab
        print('OK admin',tab,flush=True)
    page('admin/center-integration?tab=presentation');click('[data-action="ig-edit"][data-id="contents:"]')
    fill('#ig-form [name=name]','综合集成浏览器验收Banner');fill('#ig-form [name=description]','后台发布后展示');fill('#ig-form [name=url]','#/front/shared-resources')
    click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    key=ev('[...document.querySelectorAll("tbody tr")].find(r=>r.textContent.includes("综合集成浏览器验收Banner")).querySelector("[data-action=ig-publish]").dataset.id')
    click('[data-action="ig-publish"][data-id="'+key+'"]');browser('wait','--text','已保存')
    page('front/integrated-portal','u1');wait('document.querySelector("main").textContent.includes("综合集成浏览器验收Banner")')
    assert not ev('document.documentElement.scrollWidth>innerWidth')
    browser('screenshot','/tmp/onemap-integration-portal.png')
    print('OK publish -> visible portal',flush=True)
    fill('#ig-search [name=query]','耕地');click('#ig-search [type=submit]');wait('document.querySelectorAll(".ct-card").length>0')
    favorite=ev('document.querySelector("[data-action=ig-favorite]").dataset.id');click('[data-action="ig-favorite"][data-id="'+favorite+'"]')
    page('front/integrated-workbench','u1');click('[data-action=ig-preferences]')
    fill('#ig-form [name=refreshSeconds]','120');fill('#ig-form [name=quietStart]','23:00');fill('#ig-form [name=quietEnd]','07:00');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    browser('reload');wait('window.appReady === true');click('[data-action=ig-preferences]');assert ev('document.querySelector("#ig-form [name=refreshSeconds]").value')=='120';click('#dialog [data-action=close]')
    print('OK preferences persistence',flush=True)
    page('admin/integration-results','admin');click('[data-action=ig-load-map]');wait('!!document.querySelector("#ig-map canvas")');browser('screenshot','/tmp/onemap-integration-map.png')
    click('[data-action=ig-query-point]');browser('select','#ig-form [name=mode]','penetrate');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open');wait('document.querySelector("#ig-feature").textContent.includes("查询结果")')
    assert ev('document.querySelectorAll("#ig-map-history [data-action=ig-map-history]").length>0')
    print('OK real 2D scene and authorized spatial query',flush=True)
    page('admin/center-integration?tab=tenants');click('[data-action=ig-tenant-child][data-id=tenant-province]')
    tenant_name='浏览器验收租户'+str(time.time_ns());fill('#ig-form [name=name]',tenant_name);fill('#ig-form [name=region]','呼和浩特市');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    tid=ev('[...document.querySelectorAll("tbody tr")].find(r=>r.textContent.includes('+json.dumps(tenant_name)+')).querySelector("[data-action=ig-tenant-member]").dataset.id')
    click('[data-action=ig-tenant-member][data-id="'+tid+'"]');browser('select','#ig-form [name=userId]','u1');browser('select','#ig-form [name=permissions]','read','write');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    page('admin/integration-resources?view=tenants','u1');click('[data-action=ig-tenant-asset][data-id="'+tid+'"]');fill('#ig-form [name=name]','私有空间验收记录');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    assert ev('document.querySelector("main").textContent.includes("私有空间验收记录")')
    page('admin/integration-resources?view=tenants','u2');assert not ev('document.querySelector("main").textContent.includes("私有空间验收记录")')
    print('OK tenant membership and isolated workspace',flush=True)
    browser('set','viewport','390','844')
    for route in ['front/integrated-portal','front/integrated-workbench','admin/integration-results','admin/center-integration']:
        page(route,'admin');assert not ev('document.documentElement.scrollWidth>innerWidth'),route
        print('OK mobile',route,flush=True)
    page('front/integrated-workbench','u1');browser('screenshot','/tmp/onemap-integration-mobile.png')
    print('Integration browser checks passed.',flush=True)
if __name__=='__main__':main()

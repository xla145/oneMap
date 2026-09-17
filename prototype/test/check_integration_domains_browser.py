"""Run against an isolated QA database. Covers the three use domains and settings."""
import json,os,subprocess,time
from urllib.request import Request,urlopen
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5197');SESSION='three-domains';REPORT=[]
def browser(*args):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],capture_output=True,text=True,timeout=45)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def ev(js):return json.loads(browser('eval',js))
def wait(js):browser('wait','--fn',js)
def click(sel):browser('scrollintoview',sel);browser('click',sel)
def api(action,payload={},user='admin'):
    r=Request(BASE+'/api/action',data=json.dumps(dict(action=action,payload=payload)).encode(),headers={'Content-Type':'application/json','X-Demo-User':user,'X-Demo-Mode':'admin'})
    with urlopen(r) as f:return json.load(f)
def data(user='admin'):
    with urlopen(Request(BASE+'/api/bootstrap',headers={'X-Demo-User':user,'X-Demo-Mode':'admin'})) as f:return json.load(f)
def page(path,title):
    browser('open',BASE+'/#/'+path);wait('window.appReady && document.querySelector("h1")?.textContent==='+json.dumps(title))
def check(name,ok):
    assert ok,name
    REPORT.append(name);print('OK',name,flush=True)
def main():
    browser('open',BASE);ev('sessionStorage.setItem("onemap-user","admin")');browser('set','viewport','1440','1000');browser('reload')
    page('admin/integration-resources','数字资源')
    check('three use domains and one configuration entry',ev('[...document.querySelectorAll("[data-menu-group=integration] a")].map(a=>a.textContent)')==['一张图成果','数字资源','个人工作台','集成配置'])
    check('internal shell and no maintenance actions on use cards',not ev('document.body.classList.contains("portal-mode")||!!document.querySelector("[data-action=ig-placement]")'))
    click('[data-action=ig-resource-detail]');wait('document.querySelector("#dialog").open')
    check('resource details show origin and maintenance entry',ev('document.querySelector("#dialog").textContent.includes("来源中心")&&document.querySelector("#dialog").textContent.includes("到原中心维护")'))
    click('#dialog [data-action=close]')
    click('[data-action=ig-resource-kind][data-id=工具]');wait('location.hash.includes("kind=") && !!document.querySelector("[name=kind]")')
    check('type count and result scope agree',ev('[...document.querySelectorAll(".ct-card .tag")].every(x=>x.textContent==="工具")'))
    browser('fill','#ig-search [name=query]','空间');click('#ig-search [type=submit]');wait('location.hash.includes("query=") && document.querySelector("[name=query]")?.value==="空间"')
    browser('reload');wait('window.appReady && document.querySelector("[name=query]")?.value==="空间"')
    check('search and kind survive reload',ev('document.querySelector("[name=kind]").value')=='工具')
    page('admin/integration-resources?kind=工具','数字资源')
    favorite=ev('document.querySelector("[data-action=ig-favorite]").dataset.id')
    if favorite in data()['centers']['favorites']:api('centers.favorite',{'id':favorite});browser('reload');wait('window.appReady')
    click('[data-action=ig-favorite][data-id="'+favorite+'"]');wait('document.querySelector("[data-action=ig-favorite]")?.textContent==="取消收藏"')
    page('admin/integration-workbench','个人工作台');wait('!document.querySelector("#main").textContent.includes("正在读取本人")')
    check('desktop includes tasks apps tools messages and shared favorite',ev('["我的待办","我的应用","我的工具","消息提醒与公告"].every(t=>document.querySelector("#main").textContent.includes(t))') and ev('[...document.querySelectorAll("[data-action=ig-favorite]")].some(e=>e.dataset.id==='+json.dumps(favorite)+')'))
    click('[data-action=ig-preferences]');wait('document.querySelector("#ig-form")');browser('select','[name=metrics]','待办','正常','逾期','预警','已办','消息','收藏');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    check('all personal metrics render numbers',not ev('document.querySelector("#main").textContent.includes("undefined")'))
    marker='domains-'+str(time.time_ns())
    api('integration.admin.task.import',dict(systemId='system-5',payload=[dict(id=marker+u,name=marker+u,userId=u,status='待办',version=1) for u in ['admin','u1','u2']]))
    browser('reload');wait('window.appReady && document.querySelector("#main").textContent.includes('+json.dumps(marker+'admin')+')')
    check('admin personal desk excludes other recipients',not ev('document.querySelector("#main").textContent.includes('+json.dumps(marker+'u1')+')'))
    click('[data-action=ig-work-filter][data-id=正常]');wait('!!document.querySelector("#ig-task-filter")&&!document.querySelector("#main").textContent.includes("正在读取本人")')
    check('counter click uses matching server list',ev('document.querySelector("#ig-task-filter [name=status]").value')=='正常' and ev('document.querySelector("#main").textContent.includes('+json.dumps(marker+'admin')+')'))
    page('admin/integration-settings','集成配置')
    check('four settings groups',ev('[...document.querySelectorAll("[aria-label=集成配置分类] a")].map(a=>a.textContent)')==['门户展示','系统接入','运行维护','权限与租户'])
    for tab in ['overview','presentation','announcements','placement','systems','national','vertical','horizontal','plans','tasks','receipts','exceptions','monitor','access','tenants']:
        page('admin/center-integration?tab='+tab,'集成配置')
        check('legacy configuration '+tab,'integration-settings' in browser('get','url') and not ev('document.documentElement.scrollWidth>innerWidth'))
    page('admin/center-integration?tab=tasks&system=system-5','集成配置')
    check('source context retained with detail tabs',ev('document.querySelector("#main").textContent.includes("认证关联")&&document.querySelector("[name=system]").value==="system-5"'))
    click('[data-action=ig-task-adapter][data-id=system-5]');wait('!!document.querySelector("#ig-user-mapping")');check('mapping remains editable',True);click('#dialog [data-action=close]')
    page('admin/integration-settings?tab=policy','集成配置');click('[data-action=ig-policy]');wait('!!document.querySelector("#ig-form [name=maxAreaHa]")');check('policy separate from presentation',not ev('!!document.querySelector("#ig-form [name=title]")'));click('#dialog [data-action=close]')
    page('admin/integration-settings','集成配置');click('[data-action=ig-settings]');wait('!!document.querySelector("#ig-form [name=title]")');check('visual settings exclude policy',not ev('!!document.querySelector("#ig-form [name=maxAreaHa]")'));click('#dialog [data-action=close]')
    for old,title in [('integrated-portal','数字资源'),('internal-home','数字资源'),('integrated-workbench','个人工作台'),('integration-results','一张图成果')]:
        page('front/'+old,title);check('legacy use '+old,'#/admin/integration-' in browser('get','url'))
    page('admin/integration-results?tab=usage','一张图成果');check('scoped results usage exists',ev('document.querySelector("#main").textContent.includes("图层全链路监测")'))
    browser('set','viewport','390','844')
    for path,title in [('integration-workbench','个人工作台'),('integration-resources','数字资源'),('integration-settings','集成配置'),('integration-results','一张图成果')]:
        page('admin/'+path,title);check('390px '+path,not ev('document.documentElement.scrollWidth>innerWidth'));browser('screenshot','/tmp/'+path+'-390.png')
    ev('sessionStorage.setItem("onemap-user","u1")');page('admin/integration-workbench','个人工作台');browser('reload');wait('window.appReady && document.querySelector("h1")?.textContent==="个人工作台"')
    check('internal business user has no configuration menu',not ev('[...document.querySelectorAll("[data-menu-group=integration] a")].some(a=>a.getAttribute("href").includes("integration-settings"))'))
    page('admin/integration','个人工作台');check('generic integration restores legal last page',ev('location.hash')=='#/admin/integration-workbench')
    check('no browser errors',not browser('errors'))
    print(json.dumps(REPORT,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

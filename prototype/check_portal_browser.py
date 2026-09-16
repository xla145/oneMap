"""Portal navigation and interaction checks. Point at a disposable database."""
import json
import os
import subprocess
from pathlib import Path
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5194')
ROOT=Path(__file__).resolve().parent
checks=[]
visit=0
def browser(*args):
    p=subprocess.run(['agent-browser','--session','portal-check',*args],text=True,capture_output=True,timeout=25)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def js(source):
    raw=browser('eval',source)
    try:return json.loads(raw)
    except ValueError:return raw
def wait(condition):
    assert js('(async()=>{for(let i=0;i<80;i++){if('+condition+')return true;await new Promise(r=>setTimeout(r,75));}return false;})()'),str(js('document.body.innerText.slice(-1300)'))
def open_route(route):
    global visit
    visit+=1;browser('open',BASE+'/?portal-check='+str(visit)+'#/'+route)
    wait('window.appReady && !!document.querySelector("main h1,main h2")')
def click(selector):
    browser('scrollintoview',selector);browser('click',selector)
def action(name,ident=None):click('[data-action='+json.dumps(name)+']'+('[data-id='+json.dumps(ident,ensure_ascii=False)+']' if ident else ''))
def good(name):
    assert not js('document.documentElement.scrollWidth>innerWidth'),name+' overflow'
    assert not js('!!document.querySelector(".form-error")'),name+' form error'
    checks.append(name);print('OK '+name,flush=True)
def screenshot(name,full=False):
    args=['screenshot',str(ROOT/'screenshots'/('portal-'+name+'.png'))]
    if full:args.append('--full')
    browser(*args)

browser('set','viewport','1440','1080')
open_route('front/home')
assert js('document.querySelector(".sidebar")===null')
assert js('document.querySelectorAll(".portal-nav a").length')==5
assert js('new Set([...document.querySelectorAll(".portal-nav a")].map(x=>x.getBoundingClientRect().y)).size')==1
screenshot('home-desktop',True);good('门户首页和横向导航，移除管理侧栏')
action('portalCategory','图层服务');wait('document.querySelector("#list-filter")?.value==="图层服务"');assert js('document.querySelectorAll(".resource-card").length')>0;good('首页分类跳转并筛选资源')
click('.resource-card [data-action=resource]');wait('document.querySelector("#dialog").open');assert '字段与元数据' in js('document.querySelector("#dialog").innerText');good('门户资源详情');action('close')
click('.portal-nav a[href="#/front/knowledge"]');wait('document.querySelector("main h1")?.textContent==="知识中心"');action('portalKnowledge');wait('!!document.querySelector(".portal-document-body")');good('知识中心查阅来源和正文');action('close')
click('.portal-nav a[href="#/front/tools"]');wait('document.querySelectorAll(".portal-tool-card").length===5');screenshot('tools-desktop');good('五类面向业务的工具服务')
action('portalScenarios');wait('!!document.querySelector(".portal-scenario-dialog")');click('.portal-scenario-dialog [data-agent="a1"]');wait('document.querySelectorAll(".assistant-message").length>0');assert js('!!document.querySelector(".portal-back")');good('场景提问进入独立助手页面')
click('.portal-back');wait('!!document.querySelector("#portal-search")');browser('fill','#portal-question','什么是耕地占补平衡？');js('document.querySelector("#portal-search").requestSubmit()');wait('document.querySelectorAll(".citation").length>0');assert '政策知识助手' in js('document.querySelector(".chat-header").innerText');screenshot('assistant-desktop');good('门户搜索进入知识助手并返回引用')
action('portalAccount');wait('!!document.querySelector(".portal-account-links")');action('portalAccountNavigate','/front/applications');wait('document.querySelector("main h1")?.textContent==="我的申请"');good('个人入口查看申请')
action('portalAccount');action('portalAccountNavigate','/front/profile');wait('!!document.querySelector("#preferences-form")');good('个人入口查看偏好与历史')
click('.portal-footer a[href="#/admin/overview"]');wait('!!document.querySelector(".sidebar")');assert not js('document.body.classList.contains("portal-mode")');assert not js('!!document.querySelector(".portal-header")');good('后台管理保持独立布局')
action('switchMode');wait('!!document.querySelector("#portal-search")');good('后台返回门户首页')
for width in [1440,1024,390]:
    browser('set','viewport',str(width),'1080' if width==1440 else '844')
    for route in ['home','catalog','agents','tools','knowledge','assistant','profile','applications']:
        open_route('front/'+route);good(str(width)+' '+route)
        if route=='home' and width==390:
            screenshot('home-mobile',True);action('portalMenu');assert js('document.body.classList.contains("portal-menu-open")');click('.portal-nav a[href="#/front/tools"]');wait('document.querySelectorAll(".portal-tool-card").length===5');assert not js('document.body.classList.contains("portal-menu-open")');good('移动导航展开、跳转与自动收起')
            screenshot('tools-mobile')
errors=browser('errors');assert not errors,errors
(ROOT/'portal-browser-checks.json').write_text(json.dumps(dict(base=BASE,checks=checks,errors=errors),ensure_ascii=False,indent=2))
print(str(len(checks))+' portal checks passed',flush=True)

"""Run on an isolated database: tests navigation, local sync recovery and result permissions."""
import json
import os
import subprocess
import time
from pathlib import Path
from urllib.request import Request,urlopen

BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5197')
SESSION='integration-admin-workflows'
REPORT=[]

def browser(*args):
    result=subprocess.run(['agent-browser','--session',SESSION,*args],capture_output=True,text=True,timeout=40)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()

def ev(js):return json.loads(browser('eval',js))
def wait(js):browser('wait','--fn',js)
def click(selector):
    browser('scrollintoview',selector);browser('click',selector)
def fill(selector,value):browser('fill',selector,value)
def check(name,condition):
    assert condition,name
    REPORT.append(name);print('OK',name,flush=True)
def page(tab):
    browser('open',BASE+'/#/admin/center-integration?tab='+tab)
    wait('window.appReady === true && document.querySelector("h1")?.textContent === '+json.dumps("集成配置"))
def close():click('#dialog [data-action=close]')
def data():
    with urlopen(Request(BASE+'/api/bootstrap',headers={'X-Demo-User':'admin','X-Demo-Mode':'admin'})) as r:return json.load(r)
TITLES=dict(overview='运行总览',presentation='内部门户展示',announcements='公告通知',placement='成果编排',systems='内部系统',national='国家对接',vertical='纵向交换',horizontal='横向联动',plans='接入计划',tasks='待办同步',receipts='办理核对',exceptions='异常处理',monitor='使用统计',access='成果使用授权',tenants='三级租户')

def main():
    browser('open',BASE);ev('sessionStorage.setItem("onemap-user","admin")');browser('set','viewport','1440','1000')
    browser('reload');wait('window.appReady === true')
    for tab in TITLES:
        page(tab)
        check('page '+tab,not ev('document.documentElement.scrollWidth>innerWidth'))
    page('overview');click('.ig-admin-metric');wait('document.querySelector("h1")?.textContent === "集成配置"')
    check('summary carries filter', 'filter=incomplete' in browser('get','url'))
    browser('reload');wait('window.appReady === true');check('refresh retains destination',ev('document.querySelector("h1").textContent')=='集成配置')
    click('a[href="#/admin/center-integration?tab=tasks&system=system-5"]');wait('document.querySelector("h1")?.textContent === "集成配置"')
    check('system links to filtered tasks',ev('document.querySelector("[name=system]").value')=='system-5')
    marker='qa-'+str(time.time_ns());payload=[dict(id=marker,name='浏览器同步验收 '+marker,userId=marker,status='处理中',version=1)]
    click('[data-action=ig-task-import][data-id=system-5]');fill('[name=payload]',json.dumps(payload,ensure_ascii=False));click('#ig-form [type=submit]')
    wait('document.querySelector("#dialog")?.textContent.includes("接收人无法匹配")')
    check('failed import is atomic',not any(r['externalId']==marker for r in data()['centers']['externalTodos']))
    run=data()['integration']['administration']['runs'][-1];close()
    click('[data-action=ig-task-adapter][data-id=system-5]');click('[data-add-mapping=user]')
    fill('#ig-user-mapping .ig-mapping-row:last-child [data-mapping-key]',marker)
    browser('select','#ig-user-mapping .ig-mapping-row:last-child [data-mapping-value]','u2')
    # Preserve existing source-state aliases while adding ours when needed.
    existing=ev('Array.from(document.querySelectorAll("#ig-status-mapping [data-mapping-key]")).map(x=>x.value)')
    if '处理中' not in existing:
        click('[data-add-mapping=status]');fill('#ig-status-mapping .ig-mapping-row:last-child [data-mapping-key]','处理中')
    click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    click('[data-action=ig-task-retry][data-id="'+run['id']+'"]');wait('document.querySelector("#dialog")?.textContent.includes("已完成")');close()
    tasks=data()['centers']['externalTodos'];task=next(r for r in tasks if r['externalId']==marker)
    check('mapping retry resolves source failure',next(r for r in data()['integration']['administration']['runs'] if r['id']==run['id'])['resolved'])
    click('[data-action=ig-task-import][data-id=system-5]');fill('[name=payload]',json.dumps(payload,ensure_ascii=False));click('#ig-form [type=submit]');wait('document.querySelector("#dialog")?.textContent.includes("跳过 1")');close()
    check('repeat import remains one task',len([r for r in data()['centers']['externalTodos'] if r['externalId']==marker])==1)
    page('receipts');click('[data-action=ig-task-receipt][data-id="'+task['id']+'"]');browser('select','[name=sourceStatus]','已办');fill('[name=evidence]','来源系统截图显示已办，等待同步更新');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    check('mismatch recorded without modifying source task',next(r for r in data()['integration']['administration']['receipts'] if r['taskId']==task['id'])['status']=='状态不一致')
    click('[data-action=ig-task-history][data-id="'+task['id']+'"]');wait('document.querySelector("#dialog")?.textContent.includes("等待同步更新")');close()
    page('plans');click('[data-action=ig-plan-edit]');fill('[name=name]','联调计划 '+marker);fill('[name=owner]','测试负责人');fill('[name=department]','规划部门');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    check('plan is persisted',any(r['name']=='联调计划 '+marker for r in data()['integration']['plans']))
    page('access');click('[data-action=ig-access-edit][data-id=u2]');browser('check','[name=view]');browser('uncheck','[name=analyze]');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    click('[data-action=identity]');browser('select','#pc-login-form [name=userId]','u2');click('#pc-login-form button.primary')
    wait('document.querySelector("h1")?.textContent === "个人工作台"');browser('open',BASE+'/#/admin/integration-results');wait('!!document.querySelector("#ig-map canvas")')
    check('viewer enters results without management menu',not ev('!!document.querySelector("nav a[href*=center-integration]")'))
    check('viewer query controls disabled',ev('document.querySelector("[data-action=ig-query-point]").disabled'))
    browser('open',BASE+'/#/admin/center-integration?tab=access');wait('document.querySelector("h1")?.textContent === "暂无管理权限"')
    check('viewer cannot enter management',True)
    ev('sessionStorage.setItem("onemap-user","admin")');browser('reload');wait('window.appReady === true');page('access')
    click('[data-action=ig-access-edit][data-id=u2]');browser('uncheck','[name=view]');click('#ig-form [type=submit]');wait('!document.querySelector("#dialog").open')
    ev('sessionStorage.setItem("onemap-user","u2")');browser('open',BASE+'/#/admin/integration-results');browser('reload');wait('document.querySelector("h1")?.textContent === "暂无管理权限"')
    check('revocation prevents result access',True)
    ev('sessionStorage.setItem("onemap-user","admin")');browser('reload');wait('window.appReady === true')
    browser('set','viewport','390','844')
    for tab in ['overview','tasks','access','plans']:
        page(tab);check('mobile '+tab,not ev('document.documentElement.scrollWidth>innerWidth'))
    browser('screenshot','/tmp/integration-admin-mobile.png')
    browser('set','viewport','1440','1000');page('overview');browser('screenshot','/tmp/integration-admin-desktop.png')
    check('no browser exceptions',not browser('errors').strip())
    Path('/tmp/integration-admin-browser-checks.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
    print('Integration administration browser checks passed.',flush=True)

if __name__=='__main__':main()

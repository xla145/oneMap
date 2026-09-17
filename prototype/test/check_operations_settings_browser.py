"""Mutating UI acceptance: DEMO_QA_URL must point to an isolated QA database."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

BASE=os.environ['DEMO_QA_URL'].rstrip('/')
SESSION='operations-config-checks'
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'reports'
PREFIX='配置验收-'+str(int(time.time()))
results=[]

def browser(*args,script=None):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],input=script,text=True,capture_output=True,timeout=30)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def ev(script):return json.loads(browser('eval','--stdin',script=script))
def wait(expr):
    ev('(async()=>{for(let i=0;i<80;i++){if('+expr+')return true;await new Promise(r=>setTimeout(r,100));}throw Error("UI timeout: "+document.querySelector("main").innerText.slice(-900))})()')
def page(config,record=None,user='admin'):
    ev('sessionStorage.setItem("onemap-user",'+json.dumps(user)+');null')
    route='/#/admin/operations/settings?config='+config+(('&record='+record) if record else '')
    browser('open',BASE+route)
    wait('window.appReady && document.querySelector("main h1")')
def fill(selector,value):
    ev('(()=>{const el=document.querySelector('+json.dumps(selector)+');el.value='+json.dumps(value)+';el.dispatchEvent(new Event("input",{bubbles:true}));el.dispatchEvent(new Event("change",{bubbles:true}));return true;})()')
def click(selector):ev('document.querySelector('+json.dumps(selector)+').click();null')
def save():
    ev('document.querySelector("#oc-config-form").requestSubmit();null')
    wait('document.querySelector("#oc-config-save-state")?.textContent==="正在查看已保存配置"')
def bootstrap():
    req=urllib.request.Request(BASE+'/api/bootstrap',headers={'X-Demo-User':'admin','X-Demo-Mode':'admin'})
    with urllib.request.urlopen(req) as r:return json.load(r)

def main():
    REPORT.mkdir(exist_ok=True);(REPORT/'screenshots').mkdir(exist_ok=True)
    browser('open',BASE)
    page('standards','new')
    fill('#oc-config-form [name=name]',PREFIX+'-标准')
    fill('[data-standard-row] [data-column=name]','id')
    fill('[data-standard-row] [data-column=label]','编号')
    click('[data-config-action=add-field]')
    fill('[data-standard-row]:last-child [data-column=name]','id')
    fill('[data-standard-row]:last-child [data-column=label]','面积')
    fill('[data-standard-row]:last-child [data-column=type]','number')
    ev('document.querySelector("#oc-config-form").requestSubmit();null')
    wait('document.querySelector("#oc-config-form [role=alert]").textContent.includes("重复")')
    fill('[data-standard-row]:last-child [data-column=name]','area')
    save()
    standard_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    assert next(x for x in bootstrap()['centers']['standards'] if x['id']==standard_id)['status']=='草稿'
    # Unsaved edits disable publication, so the visible form cannot publish an old saved draft.
    fill('#oc-config-form [name=name]',PREFIX+'-标准修改')
    assert ev('document.querySelector("[data-config-action=publish]").disabled')
    save();click('[data-config-action=publish]')
    wait('!document.querySelector("[data-config-action=publish]")')
    saved=next(x for x in bootstrap()['centers']['standards'] if x['id']==standard_id)
    assert saved['status']=='已发布' and saved['fields'][1]['type']=='number'
    results.append('可视化标准：新增字段、阻止重复、保存草稿、阻止未保存发布、发布与持久化')
    browser('open',BASE+'/#/admin/operations/collection/tasks/new')
    wait('document.querySelector("#oc-editor [name=standardId]")')
    assert ev('[...document.querySelector("#oc-editor [name=standardId]").options].some(x=>x.value==='+json.dumps(standard_id)+')')
    results.append('发布后的标准实际出现在归集任务选择项')
    fill('#oc-editor [name=name]',PREFIX+'-归集任务')
    fill('#oc-editor [name=assigneeIds]','u1')
    fill('#oc-editor [name=dueAt]','2026-12-31T12:00')
    fill('#oc-editor [name=standardId]',standard_id)
    ev('document.querySelector("#oc-editor").requestSubmit();null')
    wait('!document.querySelector("#oc-editor") && document.querySelector("main h1").textContent==='+json.dumps(PREFIX+'-归集任务'))
    task=next(x for x in bootstrap()['operations']['tasks'] if x['name']==PREFIX+'-归集任务')
    page('standards',standard_id)
    assert ev('[...document.querySelectorAll(".oc-config-impact a")].some(x=>x.hash.endsWith('+json.dumps(task['id'])+'))')
    results.append('配置使用情况显示真实引用的归集任务，并可定位该任务')
    page('models','new')
    fill('#oc-config-form [name=name]',PREFIX+'-模板')
    click('[name=ruleIds][value=rule-id]');click('[name=ruleIds][value=rule-area]')
    save();model_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    click('[data-config-action=publish]');wait('!document.querySelector("[data-config-action=publish]")')
    model=next(x for x in bootstrap()['operations']['models'] if x['id']==model_id)
    assert len(model['published']['rules'])==2
    results.append('勾选规则保存并发布模板，后端保存两项规则快照')
    page('rules','rule-area')
    fill('#oc-config-form [name=name]','面积非负（验收修订）');save()
    page('models',model_id)
    assert ev('document.querySelector("#oc-config-records").innerText.includes("规则已变化，需重新发布")')
    save();click('[data-config-action=publish]');wait('!document.querySelector("[data-config-action=publish]")')
    assert ev('document.querySelector("#oc-config-records").innerText.includes("已发布版本可用")')
    results.append('规则修订后模板标记失效；重新保存发布后恢复可用')
    page('sources','new');fill('#oc-config-form [name=name]',PREFIX+'-外部来源')
    fill('#oc-config-form [name=kind]','PostgreSQL');fill('#oc-config-form [name=provider]','验收单位')
    fill('#oc-config-form [name=endpoint]','https://example.com/database');save()
    source_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    click('[data-config-action=check-source]')
    wait('document.querySelector("#toast")?.textContent.includes("外部连接仍待联调")')
    assert next(x for x in bootstrap()['centers']['sources'] if x['id']==source_id)['status']=='待外部联调'
    results.append('外部来源保存与检查均保持待联调，未假报连接成功')
    page('directories','new');fill('#oc-config-form [name=name]',PREFIX+'-目录');save()
    directory_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    assert any(x['id']==directory_id for x in bootstrap()['operations']['directories'])
    page('domains','new');fill('#oc-config-form [name=name]',PREFIX+'-存储');fill('#oc-config-form [name=sourceId]','source-local');save()
    domain_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    assert any(x['id']==domain_id for x in bootstrap()['operations']['domains'])
    page('alertRules','new');fill('#oc-config-form [name=name]',PREFIX+'-告警');fill('#oc-config-form [name=level]','严重');save()
    alert_id=ev('new URLSearchParams(location.hash.split("?")[1]).get("record")')
    assert next(x for x in bootstrap()['operations']['alertRules'] if x['id']==alert_id)['level']=='严重'
    results.append('目录、存储位置、告警规则均在当前页面保存到真实业务记录')
    page('standards')
    fill('#oc-config-search','不存在的配置名称')
    assert ev('[...document.querySelectorAll(".oc-config-record")].every(x=>x.hidden)')
    results.append('配置搜索过滤真实列表')
    views=[]
    for width in [1440,390]:
        browser('set','viewport',str(width),'1000')
        for key in ['standards','models','rules','sources','directories','domains','alertRules']:
            page(key)
            state=ev('({width:innerWidth,scroll:document.documentElement.scrollWidth,editor:!!document.querySelector("#oc-config-form")})')
            assert state['editor'] and state['width']>=state['scroll'],(key,state)
            views.append(dict(config=key,**state))
            if key=='standards':browser('screenshot',str(REPORT/'screenshots'/('operations-config-editor-'+str(width)+'.png')),'--full')
    page('standards',user='u1')
    assert ev('document.querySelector("main h1").textContent==="暂无管理权限" && !document.querySelector("#oc-config-form")')
    errors=browser('errors');assert not errors,errors
    (REPORT/'operations-settings-browser-checks.json').write_text(json.dumps(dict(base=BASE,checks=results,views=views,permission='非管理员无法访问配置编辑',browserErrors=errors,automation='DOM input/change/click and requestSubmit through agent-browser; read-only API assertions'),ensure_ascii=False,indent=2)+'\n')
    print(str(len(results))+' configuration workflow checks, '+str(len(views))+' responsive views and permission checks passed.')
    browser('close')

if __name__=='__main__':main()

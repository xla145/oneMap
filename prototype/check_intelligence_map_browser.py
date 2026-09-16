"""Map/chat workflows via agent-browser. Requires an independent demo database."""
import json
import os
import subprocess

BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5199')
SESSION='intelligence-map-regression'


def browser(*args,script=None):
    r=subprocess.run(['agent-browser','--session',SESSION,*args],input=script,capture_output=True,text=True,timeout=30)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    return r.stdout.strip()


def js(source):return json.loads(browser('eval','--stdin',script=source))


def wait(expression):
    assert js('(async()=>{for(let i=0;i<80;i++){if('+expression+')return true;await new Promise(r=>setTimeout(r,100));}return false;})()'),expression


def settle():wait('document.querySelector(".ai-workspace")?.dataset.ready==="true" && document.querySelector(".ai-workspace")?.dataset.busy==="false"')


def submit(question):
    count=js('document.querySelectorAll(".ai-message-result").length')
    browser('fill','#chat-form textarea',question)
    browser('click','#chat-form .send-btn')
    wait('document.querySelectorAll(".ai-message-result").length>'+str(count))
    settle()


def click_point(x,y):
    browser('mouse','move',str(round(x)),str(round(y)))
    browser('mouse','down');browser('mouse','up')


try:
    browser('set','viewport','1440','1080')
    browser('open',BASE+'/#/front/intelligence')
    wait('window.appReady && document.querySelector(".ai-topic-grid")')
    browser('click','.ai-topic-grid [data-agent=a3]')
    wait('document.querySelectorAll("[data-result-id]").length===3');settle()
    assert '400' in js('document.querySelector("#ai-result-panel").innerText')
    assert not js('document.documentElement.scrollWidth>innerWidth')
    print('PASS topic entry, shared conversation, 3 features / 400 hectares',flush=True)

    browser('click','[data-result-id=r_scene_demo_0]')
    wait('!document.querySelector(".ai-feature-panel").hidden')
    assert '128.6' in js('document.querySelector(".ai-feature-panel").innerText')
    browser('click','[data-ai=use-feature]')
    submit('统计这个图斑的属性面积')
    assert js('document.querySelectorAll("[data-result-id]").length')==1
    assert '所选图斑' in js('document.querySelector("#ai-scope-label").innerText')
    browser('select','#chat-form [name=period]','2025年')
    submit('统计这个图斑的属性面积')
    assert '仅提供2026年数据' in js('document.querySelector("#ai-result-panel").innerText')
    assert js('document.querySelectorAll("[data-result-id]").length')==0
    browser('select','#chat-form [name=period]','2026年')
    browser('click','[data-ai=clear]')
    submit('统计当前范围的耕地图斑数量和属性面积')
    assert js('document.querySelectorAll("[data-result-id]").length')==3
    print('PASS feature-to-chat, multi-turn time filtering, clearing selection',flush=True)

    if js('!document.querySelector(".ai-feature-panel").hidden'):browser('click','[data-ai=close-detail]')
    browser('click','[data-ai=box]')
    bounds=js('(()=>{const r=document.querySelector("#ai-map-host").getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};})()')
    click_point(bounds['x']+60,bounds['y']+115)
    click_point(bounds['x']+bounds['w']-70,bounds['y']+bounds['h']-120)
    wait('document.querySelector("#ai-scope-label").innerText.includes("自定义选区")')
    submit('统计当前范围的耕地图斑面积')
    assert '自定义选区' in js('document.querySelector("#ai-result-panel").innerText')
    assert js('document.querySelectorAll("[data-result-id]").length')>=1
    browser('click','.ai-result-caliber summary')
    assert '不计算交叠面积' in js('document.querySelector(".ai-result-caliber").innerText')
    browser('screenshot','/tmp/intelligence-map-workspace.png','--full')
    sid=js('(async()=>{const d=await (await fetch("/api/bootstrap")).json();return d.sessions.at(-1).id;})()')
    browser('click','[data-ai=new]');settle()
    assert '自定义选区' not in js('document.querySelector("#ai-scope-label").innerText')
    browser('click','.ai-history>summary')
    browser('click','[data-action=resume][data-id="'+sid+'"]');settle()
    assert '自定义选区' in js('document.querySelector("#ai-scope-label").innerText')
    first=js('document.querySelector("[data-action=mapResult]").dataset.id')
    browser('focus','[data-action=mapResult][data-id="'+first+'"]')
    browser('press','Enter')
    wait('document.querySelectorAll("[data-result-id]").length===3')
    print('PASS drawn extent, result overlay, fresh task, historical snapshot restore',flush=True)

    browser('set','viewport','390','844')
    browser('click','[data-ai-tab=map]')
    browser('scrollintoview','#ai-map-host')
    assert not js('document.documentElement.scrollWidth>innerWidth')
    browser('screenshot','/tmp/intelligence-map-mobile.png')
    browser('eval','window.scrollTo(0,0)')
    browser('click','[data-ai-tab=results]')
    assert js('document.querySelector("#ai-result-panel").getBoundingClientRect().height')>0
    browser('click','[data-ai-tab=chat]')
    assert js('document.querySelector("#chat-form").getBoundingClientRect().height')>0
    browser('set','viewport','1440','1080')
    browser('open',BASE+'/#/front/intelligence')
    wait('document.querySelector(".ai-topic-grid")')
    browser('click','.ai-topic-grid [data-agent=a2]')
    wait('document.querySelector(".citation")')
    assert not js('!!document.querySelector(".ai-workspace")')
    assert not browser('errors')
    print('PASS responsive tabs, policy-only assistant and clean teardown',flush=True)
except Exception:
    browser('screenshot','/tmp/intelligence-map-test-failure.png','--full')
    print(js('document.body.innerText.slice(-1600)'))
    raise
finally:
    browser('close')

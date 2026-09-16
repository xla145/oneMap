"""UI workflow checks using agent-browser. Use a disposable server database."""
import json
import os
import subprocess
import tempfile
from pathlib import Path
BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5192')
ROOT=Path(__file__).resolve().parent
SESSION='capability-qa'
checks=[]
def browser(*args):
    p=subprocess.run(['agent-browser','--session',SESSION,*args],capture_output=True,text=True,timeout=25)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout.strip()
def js(source):
    raw=browser('eval',source)
    try:return json.loads(raw)
    except ValueError:return raw
def wait(expression):
    value=js('(async()=>{for(let i=0;i<60;i++){if('+expression+')return true;await new Promise(r=>setTimeout(r,100));}return false;})()')
    assert value is True,expression+' '+str(js('document.body.innerText.slice(-1500)'))
def open_route(route):
    browser('open',BASE+'/#/'+route);wait('window.appReady && document.querySelector("main")?.innerText.trim()')
def click(selector):
    browser('scrollintoview',selector);browser('click',selector)
def action(name,ident=None):click('[data-action='+json.dumps(name)+']'+('[data-id='+json.dumps(ident)+']' if ident else ''))
def fill(selector,value):browser('fill',selector,value)
def submit(form,condition):
    js('document.querySelector('+json.dumps(form)+').requestSubmit()');wait(condition)
def good(name):
    assert not js('!!document.querySelector(".form-error")'),js('document.querySelector(".form-error")?.innerText')
    assert not js('document.documentElement.scrollWidth>innerWidth')
    checks.append(name);print('OK '+name,flush=True)
def screen(name):
    (ROOT/'screenshots').mkdir(exist_ok=True);browser('screenshot',str(ROOT/'screenshots'/('v2-'+name+'.png')))

browser('set','viewport','1440','1080')
open_route('admin/knowledge');action('graph','k1');assert js('document.querySelectorAll(".knowledge-graph svg g").length')==3;screen('graph');good('知识图谱与处理状态');action('close')
action('importDoc')
with tempfile.TemporaryDirectory() as folder:
    first=Path(folder)/'批次验证.md';second=Path(folder)/'长文验证.txt';first.write_text('耕地质量核查。\n\n耕地质量核查。\n\n保留来源依据。');second.write_text('长文验证内容'*2500)
    browser('upload','input[type=file]',str(first),str(second));submit('#import-form','document.querySelector("#dialog")?.innerText.includes("知识处理批次")')
assert js('document.querySelectorAll(".batch-item").length')==2;assert '失败' not in js('document.querySelector("#dialog").innerText');screen('batch');good('多文件导入、去重及超过一万字正文处理');action('close')
open_route('admin/resources');action('edit','resources:r1');fill('#field-rows .field-row [data-field=alias]','浏览器独有字段别名');submit('#editor-form','!document.querySelector("#dialog").open');action('publish','resources:r1');action('confirmMutation','publish:resources:r1');wait('!document.querySelector("#dialog").open');good('元数据字段配置保存与发布')
open_route('front/assistant');fill('#chat-form textarea','浏览器独有字段别名');submit('#chat-form','document.querySelectorAll(".answer-resource").length>0');assert '地质灾害巡查记录表' in js('document.querySelector(".answer-resources").innerText');good('字段别名驱动前台召回')
action('applyMessage');assert js('!!document.querySelector("#apply-form")');fill('[name=purpose]','用于浏览器验证资源申请流程');submit('#apply-form','document.querySelector("#dialog")?.innerText.includes("办理时间线")');assert js('location.hash')=='#/front/assistant';good('对话内申请提交并保留会话');action('close')
action('newChat');fill('#chat-form textarea','包头市地灾');submit('#chat-form','document.querySelectorAll(".assistant-message").length>0');action('handoffList');click('[data-action="handoff"]');wait('document.querySelector(".user-message")?.innerText.includes("接续上次任务")');wait('document.querySelectorAll(".assistant-message").length>0');assert '包头市' in js('document.querySelector(".answer-context").innerText');good('新会话接续历史区域与主题')
open_route('front/agents');action('useAgent','a_team');wait('document.querySelector(".chat-header")?.innerText.includes("耕地保护协同助手")');fill('#chat-form textarea','分析耕地保护');submit('#chat-form','document.querySelectorAll(".indicator-result").length>0');assert js('document.querySelectorAll(".citation").length')>0;screen('collaboration');good('资源、知识、指标多智能体协同')
open_route('admin/indicators');action('compare','i_rate');submit('#compare-form','document.querySelectorAll(".comparison-chart > div").length>0');assert js('document.querySelectorAll(".comparison-chart > div").length')==4;screen('comparison');good('复合指标跨年度和区域对比');action('close')
open_route('admin/corpora');action('evaluations');submit('#evaluation-form','document.querySelectorAll(".evaluation-case").length>0');text=js('document.querySelector("#evaluation-output").innerText');assert '已发布' in text and '当前草稿' in text;screen('evaluation');good('语料发布版与草稿版回归评测');action('close')
action('trial','corpora:c3');submit('#trial-form','document.querySelector("#trial-output")?.innerText.includes("total_area")');assert '750' in js('document.querySelector("#trial-output").innerText');good('参数化 SQL 本地只读执行');action('close')
action('trial','corpora:c_api');fill('[name=question]','耕地');submit('#trial-form','document.querySelector("#trial-output")?.innerText.includes("耕地")');good('NL2API 模板本地资源查询');action('close')
open_route('admin/calls');action('tab','interfaces');action('interfaceTest');submit('#invoke-form','document.querySelector("#invoke-output")?.innerText.includes("调用完成")');good('版本化能力接口试调用');action('close')
open_route('front/profile');browser('select','[name=skill]','入门');submit('#preferences-form','document.querySelector("#toast")?.innerText.includes("偏好已保存")');good('技能画像保存')
for route in ['front/assistant','admin/knowledge','admin/corpora','admin/indicators']:
    browser('set','viewport','390','844');open_route(route);good('移动视口 '+route)
errors=browser('errors');assert not errors,errors
(ROOT/'capability-browser-checks.json').write_text(json.dumps(dict(base=BASE,checks=checks,errors=errors),ensure_ascii=False,indent=2))
print(str(len(checks))+' UI checks passed',flush=True)

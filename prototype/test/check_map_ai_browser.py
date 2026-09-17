"""AI map integration smoke. Run against an isolated QA database."""
import prototype.test.check_integration_browser as b
b.SESSION='map-ai-qa'
b.browser('open',b.BASE)
b.browser('set','viewport','1440','1000')
b.page('admin/integration-results')
b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
b.ev('window.aiMapNode=document.querySelector(".pc-ol-target")')
b.click('[data-action=ig-tab][data-id=tools]')
b.wait('!!document.querySelector("#mt-basic")')
b.click('#mt-basic button')
b.wait('document.querySelectorAll(".mt-result").length===1')
b.click('[data-mw=ai]')
b.wait('!!document.querySelector("#mai-question")')
assert b.ev('window.aiMapNode===document.querySelector(".pc-ol-target")')

def ask(q):
    b.fill('#mai-question',q);b.click('#mai-submit')
    b.wait('!document.querySelector("#mai-submit").disabled')
    assert '未完成' not in b.ev('document.querySelector("#mai-messages").textContent')

ask('查询呼和浩特市的永久基本农田')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')==4
assert '本地业务解析' in b.ev('document.querySelector("#mai-mode").textContent')
assert 'FROM map_features' in b.ev('document.querySelector("#mai-results").textContent')
b.click('#mai-results [data-ai=locate]')
assert b.ev('document.querySelectorAll("#mai-results tr[aria-selected=true]").length')==1
b.click('#mai-results [data-ai=visible]')
assert '显示图层' in b.ev('document.querySelector("#mai-results [data-ai=visible]").textContent')
b.click('#mai-results [data-ai=visible]')
ask('按旗县统计')
assert b.ev('document.querySelectorAll(".mai-groups p").length')>0
b.click('[data-ai=close]');b.click('[data-mw=ai]')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')==4
assert b.ev('window.aiMapNode===document.querySelector(".pc-ol-target")')
b.click('[data-ai=new]');ask('查询建设用地')
ask('只看未审批的')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')>0
# Table selection must also become the map's selected object.
b.click('#mai-results [data-ai=locate]');b.click('[data-ai=selected]')
assert '选中对象' in b.ev('document.querySelector("#mai-scope").textContent')
b.click('[data-ai=new]');ask('查询周边1公里的建设用地')
ask('只看未审批的')
b.click('[data-ai=clear-scope]')
# Finish a real map polygon by clicking its first vertex.
b.click('[data-ai=draw]')
rect=b.ev('(()=>{const r=document.querySelector(".pc-ol-target").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
for dx,dy in [(-40,-40),(40,-40),(40,40),(-40,-40)]:
    b.browser('mouse','move',str(round(rect['x']+dx)),str(round(rect['y']+dy)))
    b.browser('mouse','down');b.browser('mouse','up')
b.wait('document.querySelector("#mai-scope").textContent==="地图绘制范围"')
b.click('[data-ai=new]');ask('查询范围内的建设用地')
b.click('[data-ai=clear-scope]')
b.click('[data-ai=new]');ask('查询全部')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')==100
b.click('[data-ai=page][data-id="2"]')
b.wait('!document.querySelector("#mai-submit").disabled')
assert '第 2 /' in b.ev('document.querySelector("#mai-results").textContent')
assert not b.ev('document.documentElement.scrollWidth>innerWidth')
b.browser('screenshot','/tmp/onemap-ai-desktop.png')
print('OK query, SQL, followup, grouping, layer visibility, selection, pagination, retained map',flush=True)
# Restoring a historical result revalidates it on the server.
b.click('#mw-ai-panel > details:last-child > summary')
b.wait('!!document.querySelector("#mai-history [data-ai=restore]")')
b.click('#mai-history [data-ai=restore]')
b.wait('!document.querySelector("#mai-submit").disabled')
assert '历史结果' in b.ev('document.querySelector("#mai-status").textContent')
# The existing tool result survives opening/closing the assistant.
b.click('[data-ai=close]');b.click('[data-mw=tools]')
b.wait('!!document.querySelector("#mt-basic")')
assert b.ev('document.querySelectorAll(".mt-result").length')==1
b.click('[data-mw=ai]')
# Mobile draw mode exposes the same map and closing cancels drawing.
b.browser('set','viewport','390','844')
assert not b.ev('document.documentElement.scrollWidth>innerWidth')
b.click('[data-ai=draw]')
assert b.ev('!!document.querySelector(".mw-right.mai-drawing")')
assert b.ev('document.querySelector(".mw-right").getBoundingClientRect().height')<=140
b.browser('screenshot','/tmp/onemap-ai-mobile-draw.png')
b.click('[data-ai=close]');b.click('[data-mw=ai]')
assert not b.ev('!!document.querySelector(".mai-drawing")')
b.browser('screenshot','/tmp/onemap-ai-mobile.png')
print('OK mobile layout and drawing access',flush=True)
# A reloaded runtime clears retained assistant state even when it was closed.
b.browser('set','viewport','1440','1000')
b.click('[data-ai=close]');b.click('[data-action=ig-load-map]')
b.wait('window.aiMapNode!==document.querySelector(".pc-ol-target") && document.querySelectorAll("[data-ig-layer]").length===28')
b.click('[data-mw=ai]')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')==0
# Delay delivery of an actual response to check stop/stale-response handling.
b.ev('window.realFetch=window.fetch;window.fetch=async (...args)=>{const response=await window.realFetch(...args);if(args[1]?.body && JSON.parse(args[1].body).action==="integration.ai.ask")await new Promise(resolve=>window.releaseAI=resolve);return response}')
b.fill('#mai-question','查询建设用地');b.click('#mai-submit')
b.wait('typeof window.releaseAI==="function"')
b.click('[data-ai=stop]');b.ev('window.releaseAI();window.fetch=window.realFetch;true')
b.wait('document.querySelector("#mai-stop").hidden')
assert b.ev('document.querySelectorAll("#mai-results [data-ai=locate]").length')==0
# Viewing rights alone must not expose the assistant.
b.api('integration.admin.access.save',dict(id='u2',rev=0,values=dict(view=True,analyze=False)))
b.page('admin/integration-results','u2')
b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
assert not b.ev('!!document.querySelector("[data-mw=ai]")')
print('OK scope/nearby followup, polygon, history, tool coexistence, reload, stop, view-only access',flush=True)
b.browser('close')

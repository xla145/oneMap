"""Shared-map tool chaining; DEMO_QA_URL must point at an isolated QA database."""
import json
import check_integration_browser as b
b.SESSION='shared-tools-final'
b.browser('open',b.BASE)
b.browser('set','viewport','1440','1000')
b.page('admin/integration-results')
b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
b.ev('window.sharedMapNode=document.querySelector(".pc-ol-target")')
b.click('[data-action=ig-tab][data-id=tools]')
b.wait('!!document.querySelector("#mt-basic")')
assert b.ev('window.sharedMapNode===document.querySelector(".pc-ol-target")')
b.click('#mt-basic button')
b.wait('document.querySelectorAll(".mt-result").length===1')
b.click('[data-mt=use][data-id=R1]')
assert '1 个' in b.ev('document.querySelector("#mt-input-count").textContent')
b.browser('select','#mt-choice','buffer')
b.click('#mt-basic button')
b.wait('document.querySelectorAll(".mt-result").length===2')
b.click('[data-mt=use][data-id=R2]')
b.browser('select','#mt-choice','area')
b.wait('document.querySelector("#ana-operation")?.value==="area"')
assert len(json.loads(b.ev('document.querySelector("#ana-geometry").value'))['features'])==1
assert '融合' in b.ev('document.querySelector("#ana-operation-hint").textContent')
b.click('[data-analysis=spatial]')
b.wait('document.querySelectorAll(".mt-result").length===3')
b.click('[data-mt=use][data-id=R3]')
b.click('[data-mt=append][data-id=R2]')
b.browser('select','#mt-choice','overlay')
b.wait('!!document.querySelector("#ana-operation")')
assert len(json.loads(b.ev('document.querySelector("#ana-geometry").value'))['features'])==2
b.click('[data-analysis=spatial]')
b.wait('document.querySelectorAll(".mt-result").length===4')
b.click('[data-mt=use][data-id=R4]')
b.browser('select','#mt-choice','compliance')
b.wait('!!document.querySelector("[data-analysis=run]")')
b.click('[data-analysis=run]')
b.wait('document.querySelectorAll("[data-analysis=export]").length===3')
b.wait('document.querySelectorAll(".mt-result").length===5')
assert b.ev('document.querySelectorAll(".pc-ol-target").length')==1
assert b.ev('window.sharedMapNode===document.querySelector(".pc-ol-target")')
# Retain parameters and results when switching tools and closing the panel.
b.browser('select','#mt-choice','buffer')
b.fill('[name=mt-distance]','2500')
b.browser('select','#mt-choice','coordinate')
b.browser('select','#mt-choice','buffer')
assert b.ev('document.querySelector("[name=mt-distance]").value')=='2500'
b.click('[data-mt=close]')
b.click('[data-action=ig-tab][data-id=tools]')
assert b.ev('document.querySelectorAll(".mt-result").length')==5
assert b.ev('document.querySelector("[name=mt-distance]").value')=='2500'
b.click('[data-mt=visible][data-id=R5]')
assert not b.ev('document.querySelector("[data-mt=visible][data-id=R5]").checked')
b.click('[data-mt=remove][data-id=R5]')
assert b.ev('document.querySelectorAll(".mt-result").length')==4
assert not b.ev('document.documentElement.scrollWidth>innerWidth')
b.browser('scrollintoview','#mt-choice')
b.browser('screenshot','/tmp/onemap-shared-tools-desktop.png')
b.browser('set','viewport','390','844')
assert not b.ev('document.documentElement.scrollWidth>innerWidth')
b.browser('scrollintoview','#mt-choice')
b.browser('screenshot','/tmp/onemap-shared-tools-mobile.png')
assert b.browser('errors') in ['', 'No errors']
print('Passed: coordinate → point buffer → area → intersection → compliance, same map, results, parameters, visibility, removal, mobile, no errors.')

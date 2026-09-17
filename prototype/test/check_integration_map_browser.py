"""Exercise the real map and scene lifecycle on isolated QA storage."""
import json
import prototype.test.check_integration_browser as b
b.SESSION='integration-map'

def map_click(dx=0,dy=0):
    b.browser('scrollintoview','#ig-map')
    pos=b.ev('(()=>{const r=document.querySelector(".pc-ol-target").getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()')
    b.browser('mouse','move',str(round(pos[0]+dx)),str(round(pos[1]+dy)));b.browser('mouse','down');b.browser('mouse','up')

def main():
    b.browser('open',b.BASE);b.ev('sessionStorage.removeItem("ig-map-state-admin")');b.browser('set','viewport','1600','1100');b.page('admin/integration-results')
    b.wait('!!document.querySelector("#ig-map canvas") && !!document.querySelector("[data-ig-layer]")')
    assert b.ev('document.querySelectorAll("#ig-map canvas").length>0')
    assert b.ev('[...document.querySelectorAll(".sidebar a")].some(a=>a.getAttribute("href")==="#/admin/integration-results")')
    assert not b.ev('document.body.classList.contains("portal-mode")')
    assert not b.ev('document.documentElement.scrollWidth>innerWidth')
    version=b.api('integration.versions',dict(entity='settings'))
    original=b.api('integration.preview',dict(entity='settings',rev=version['rev']))['draft']
    saved=b.api('integration.settings.save',dict(rev=version['rev'],values=dict(original,maxAreaHa=1234)))
    try:
        b.page('admin/integration-results');b.wait('!!document.querySelector("[data-ig-layer]")')
        assert '1000000 公顷' in b.ev('document.querySelector("#ig-map-state").textContent')
    finally:b.api('integration.settings.save',dict(rev=saved['rev'],values=original))
    layer=b.ev('document.querySelector("[data-ig-layer]").dataset.igLayer')
    b.fill('[name=layerSearch]','不存在的图层')
    assert b.ev('document.querySelectorAll("[data-ig-layer]").length')==0
    assert '2个已启用' in b.ev('document.querySelector("#ig-map-state").textContent')
    b.fill('[name=layerSearch]','');b.browser('select','[name=layerGroup]','department')
    b.click('[data-action=ig-map-layer][data-id="'+layer+'"]')
    b.wait('document.querySelector("#ig-map-position").textContent.includes("中心经纬度")')
    b.browser('select','[name=mapCity]','150100')
    assert b.ev('document.querySelectorAll("[name=mapCounty] option").length')>1
    b.browser('select','[name=mapCounty]','150102')
    b.browser('select','[name=mapCity]','150200')
    assert not b.ev('[...document.querySelectorAll("[name=mapCounty] option")].some(o=>o.value==="150102")')
    print('OK automatic map, layer filtering, grouping and city/county cascade',flush=True)
    b.click('[data-action=ig-query-point]')
    b.browser('select','#ig-form [name=mode]','nearby');b.fill('#ig-form [name=x]','111.7');b.fill('#ig-form [name=y]','40.8');b.fill('#ig-form [name=radius]','1000')
    b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open && !!document.querySelector(".ig-result-item")')
    assert b.ev('document.querySelectorAll(".ig-result-item").length')==2
    b.click('[data-action=ig-map-result][data-id="0"]')
    assert b.ev('document.querySelector("#ig-feature").textContent.includes("呼和浩特市")')
    assert b.ev('!!document.querySelector(".ig-feature-fields")')
    b.click('[data-action=ig-map-results]');b.click('[data-action=ig-map-fit-results]')
    b.click('[data-action=ig-map-expand]');assert b.ev('!!document.querySelector(".ig-map-expanded")')
    b.browser('select','[name=mapPointMode]','penetrate');map_click()
    b.wait('document.querySelectorAll(".ig-result-item").length===2')
    b.click('[data-action=ig-select-box]');map_click(-20,-20);map_click(20,20)
    b.wait('document.querySelectorAll(".ig-result-item").length===2')
    assert '拉框' in b.ev('document.querySelector("#ig-map-history").textContent')
    b.ev('document.querySelector("#ig-layers").scrollTop=0')
    b.browser('screenshot','/tmp/onemap-map-expanded.png')
    b.click('[data-action=ig-select-polygon]');b.browser('press','Escape')
    assert b.ev('!!document.querySelector(".ig-map-expanded")')
    assert b.ev('document.querySelector(".pc-map-draw-hint").hidden')
    # Delay a real query response, then hide layers: its eventual response must not redraw them.
    b.ev("window.originalFetch=window.fetch; window.releaseQuery=null;window.queryReleased=false;window.fetch=async(...args)=>{const r=await window.originalFetch(...args);if(String(args[1]?.body||'').includes('integration.map.query')){await new Promise(resolve=>window.releaseQuery=resolve);window.queryReleased=true;}return r;};true")
    map_click();b.wait('typeof window.releaseQuery==="function"')
    b.click('[data-action=ig-hide-layers]');b.ev('window.releaseQuery();window.fetch=window.originalFetch;true')
    b.wait('window.queryReleased');b.browser('wait','200')
    assert b.ev('document.querySelectorAll(".ig-result-item").length')==0
    print('OK map pointer query, box drawing and stale-response isolation',flush=True)

    b.browser('press','Escape');assert not b.ev('!!document.querySelector(".ig-map-expanded")')
    b.click('[data-action=ig-hide-layers]');assert b.ev('[...document.querySelectorAll("[data-ig-layer]")].every(e=>!e.checked)')
    assert b.ev('document.querySelectorAll(".ig-result-item").length')==0
    assert '未启用图层' in b.ev('document.querySelector("#ig-map-legend").textContent')
    b.click('[data-action=ig-show-layers]')
    # Replay history after opening its disclosure; current runtime permissions are rechecked.
    b.ev('document.querySelector(".ig-map-history").open=true')
    history=b.ev('document.querySelector("[data-action=ig-map-history]").dataset.id')
    b.click('[data-action=ig-map-history][data-id="'+history+'"]');b.wait('document.querySelectorAll(".ig-result-item").length===2')
    b.click('[data-action=ig-map-clear]');assert b.ev('document.querySelectorAll(".ig-result-item").length')==0
    print('OK surrounding query, result location, clearing, history and expanded workspace',flush=True)
    # Change scene repeatedly and ensure no duplicate map or stale callback is left behind.
    b.click('[data-action=ig-load-map]');b.click('[data-action=ig-load-map]')
    b.wait('!!document.querySelector("[data-ig-layer]")');assert b.ev('document.querySelectorAll(".pc-ol-target").length')==1
    b.browser('set','viewport','390','844');b.browser('reload');b.wait('!!document.querySelector("[data-ig-layer]")')
    assert not b.ev('document.documentElement.scrollWidth>innerWidth')
    b.click('[data-action=ig-map-expand]');assert not b.ev('document.documentElement.scrollWidth>innerWidth')
    b.browser('scrollintoview','#ig-map');b.browser('screenshot','/tmp/onemap-map-mobile.png')
    b.browser('press','Escape');b.page('front/integrated-portal');assert b.ev('document.querySelectorAll(".pc-ol-target").length')==0
    assert not b.ev('document.body.classList.contains("portal-mode")')
    b.page('front/integration-results');b.wait('location.hash==="#/admin/integration-results" && !!document.querySelector("#ig-map canvas")')
    b.fill('[name=layerSearch]','耕地');b.browser('select','[name=layerGroup]','department')
    b.click('[data-action=ig-hide-layers]');b.click('[data-action=ig-tab][data-id=tools]')
    b.wait('location.hash.includes("tab=tools") && !!document.querySelector("#ig-result-search")')
    saved=b.ev('JSON.parse(sessionStorage.getItem("ig-map-state-admin"))')
    assert saved['filter']=='耕地' and saved['group']=='department'
    b.click('[data-action=ig-tab][data-id=map]');b.wait('!!document.querySelector("#ig-map canvas")&&!!document.querySelector("[name=layerSearch]")')
    assert b.ev('document.querySelector("[name=layerSearch]").value')=='耕地'
    assert b.ev('document.querySelector("[name=layerGroup]").value')=='department'
    assert b.ev('[...document.querySelectorAll("[data-ig-layer]")].every(e=>!e.checked)')
    b.click('[data-action=ig-tab][data-id=tools]');b.wait('location.hash.includes("tab=tools")&&!!document.querySelector("#ig-result-search")')
    restored=b.ev('JSON.parse(sessionStorage.getItem("ig-map-state-admin"))')
    assert abs(saved['view']['center'][0]-restored['view']['center'][0])<1e-5
    assert abs(saved['view']['resolution']-restored['view']['resolution'])<1e-5
    print('OK map return restores filters, visibility and view',flush=True)
    b.page('admin/integration-results');b.wait('!!document.querySelector("#ig-map canvas")')
    b.ev('sessionStorage.setItem("onemap-user","u1")');b.browser('reload');b.wait('document.querySelector("h1")?.textContent==="暂无管理权限"');assert b.ev('document.querySelectorAll("#ig-map canvas").length')==0
    assert b.browser('errors') in ['', 'No errors']
    print('OK reload lifecycle, mobile layout and navigation cleanup',flush=True)
    print('Integration map browser checks passed.',flush=True)
if __name__=='__main__':main()

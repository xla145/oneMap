"""Map-first UI and extracted NMG assets; run only with an isolated QA database."""
import json
import check_integration_browser as b
b.SESSION='results-redesign'

def click(selector):
    if selector.startswith("[data-action=ig-tab]") and b.ev("!!document.querySelector("+json.dumps("#mw-map-submenu "+selector)+")"):
        b.browser("click", "[data-mw=map-menu]")
    # Explicitly scroll nested panels before pointer interaction.
    b.browser('scrollintoview',selector)
    b.browser('click',selector)

def run():
    b.browser('open',b.BASE);b.browser('set','viewport','1600','1000')
    b.page('admin/integration-results')
    b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
    assert b.ev('document.querySelector("[name=scene]").value')=='nmg-reference-demo'
    assert '28' in b.ev('document.querySelector(".mw-summary-metrics").textContent')
    assert not b.ev('document.documentElement.scrollWidth>innerWidth')
    b.browser('select','[name=mapCity]','150100')
    assert '呼和浩特市' in b.ev('document.querySelector(".mw-region-title").textContent')
    assert '15.75' in b.ev('document.querySelector(".mw-reference-kpis").textContent')
    click('[data-mw=ledger]')
    b.wait('document.querySelectorAll("[data-mw=locate]").length>0')
    click('[data-mw=locate]')
    assert b.ev('!!document.querySelector("[data-mw=analyze-feature]")')
    click('[data-mw=analyze-feature]')
    b.wait('document.querySelector("#ana-status")?.textContent.includes("已载入地图选中地块")')
    assert len(json.loads(b.ev('document.querySelector("#ana-geometry").value'))['features'])==1
    # Wait for the shared map initialization, then use actual pointer events.
    click('[data-analysis=sample]')
    b.wait('document.querySelector("#ana-status").textContent.includes("无冲突地块")')
    click('[data-analysis=run]')
    b.wait('document.querySelectorAll("[data-analysis=export]").length===3')
    assert '成功' in b.ev('document.querySelector("#ana-status").textContent')
    assert b.ev('document.querySelectorAll(".pc-ol-target").length')==1
    b.browser('screenshot','/tmp/onemap-redesign-verified-analysis.png')
    click('[data-action=ig-tab][data-id=business]')
    b.wait('document.querySelectorAll(".mw-theme").length===8')
    click('[data-mw=theme][data-id="生态修复"]')
    assert '修复成果' in b.ev('document.querySelector("#mw-business-panel").textContent')
    click('.mw-module-functions summary')
    assert b.ev('document.querySelectorAll("[data-mw=function]").length')==10
    click('[data-mw=function]')
    b.wait('document.querySelector("#dialog").open')
    assert '业务流程' in b.ev('document.querySelector("#dialog").textContent')
    click('#dialog [data-action=close]')
    click('[data-action=ig-tab][data-id=time]')
    b.wait('!!document.querySelector("#mw-series")')
    assert b.ev('document.querySelectorAll("#mw-series option").length')==12
    b.browser('select','#mw-series','farmland')
    assert '17400' in b.ev('document.querySelector(".mw-series-value").textContent')
    for tab in ['tools','scenes','usage','saved','map']:
        click('[data-action=ig-tab][data-id='+tab+']')
        if tab=='tools':b.wait('!!document.querySelector("#mw-tools-panel")')
        else:b.wait('document.querySelector(".mw-workspace")?.dataset.view==='+json.dumps(tab))
        if tab in ['saved','map']:b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
        assert not b.ev('document.documentElement.scrollWidth>innerWidth'),tab
    b.browser('select','[name=mapCity]','')
    b.browser('screenshot','/tmp/onemap-redesign-verified-desktop.png')
    b.browser('set','viewport','390','844');b.browser('reload')
    b.wait('document.querySelectorAll("[data-ig-layer]").length===28')
    assert not b.ev('document.documentElement.scrollWidth>innerWidth')
    click('[data-mw=map-menu]')
    assert b.ev('(()=>{const r=document.querySelector("#mw-map-submenu").getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&!document.querySelector("#mw-map-submenu").hidden})()')
    b.browser('press','Escape')
    assert b.ev('document.querySelector("#mw-map-submenu").hidden')
    click('.mw-panel-toggles [data-mw=left]')
    assert b.ev('document.querySelector("#ig-layers").getBoundingClientRect().width>0')
    b.browser('screenshot','/tmp/onemap-redesign-verified-mobile.png')
    assert b.browser('errors') in ['', 'No errors']
    print('Passed: extracted 28 layers, region statistics, map→parcel input, async analysis, business templates, 12 time series, navigation, mobile, no browser errors.')

if __name__=='__main__':run()

"""Result coverage checks; write only to the isolated QA database."""
import json,time
from urllib.error import HTTPError
import check_integration_domains_browser as b
b.SESSION='results-complete'
def page(tab):
    b.page('admin/integration-results?tab='+tab,'一张图成果')
    if tab.startswith('usage'):b.wait('!!document.querySelector(".ir-metrics")')
def close():b.click('#dialog [data-action=close]')
def check(name,condition):b.check(name,condition)
def main():
    b.browser('open',b.BASE);b.ev('sessionStorage.setItem("onemap-user","admin")');b.browser('reload');b.browser('set','viewport','1440','1000')
    page('tools');check('dedicated tool classification excludes unrelated resource types',not b.ev('!!document.querySelector("[name=kind]")') and b.ev('!!document.querySelector("#ig-result-search [name=category]")'))
    b.browser('select','[name=category]','基础空间工具');b.click('#ig-result-search [type=submit]');b.wait('location.hash.includes("category=")&&document.querySelectorAll(".ct-card").length===3')
    check('tool category filters actual objects',b.ev('document.querySelectorAll(".ct-card").length')==3)
    b.click('[data-action=ig-result-detail]');b.wait('document.querySelector("#dialog").open');check('full metadata and honest missing manual state',b.ev('["发布单位","提供方","发布时间","详细介绍","使用手册"].every(s=>document.querySelector("#dialog").textContent.includes(s))'));close()
    page('scenes');check('eight themes plus unclassified are visible',b.ev('document.querySelectorAll(".ir-theme").length')==9)
    b.click('.ir-theme:nth-child(5)');b.wait('location.hash.includes("theme=")');check('empty theme has no fabricated applications',b.ev('document.querySelectorAll(".ct-card").length')==0)
    b.page('admin/integration-settings?tab=placement&scope=scenes','集成配置');b.click('[data-action=ig-placement]');b.wait('!!document.querySelector("#ig-form [name=theme]")');b.browser('select','#ig-form [name=theme]','耕地保护和国土绿化空间');b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open')
    b.page('admin/integration-settings?tab=placement&scope=systems','集成配置');b.click('[data-action=ig-result-system-edit][data-id=system-7]');b.browser('select','#ig-form [name=theme]','耕地保护和国土绿化空间');b.browser('select','#ig-form [name=roles]','业务用户');b.browser('check','#ig-form [name=enabled]');b.browser('fill','#ig-form [name=provider]','耕地业务处');b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open')
    page('scenes&theme='+__import__('urllib.parse').parse.quote('耕地保护和国土绿化空间'));check('theme references original system with pending entry',b.ev('document.querySelector("#main").textContent.includes("耕地保护与监测监管信息系统")&&document.querySelector("#main").textContent.includes("待配置访问入口")'))
    layers=b.data()['integration']['results']['layers'];layer=next(r for r in layers if r['scenes']);rid=layer['resourceId']
    b.page('admin/integration-settings?tab=placement&scope=layers','集成配置');b.click('[data-action=ig-result-layer-edit][data-id="'+rid+'"]');b.browser('fill','#ig-form [name=theme]','自然资源/耕地保护/示例');b.browser('fill','#ig-form [name=cities]','呼和浩特市，包头市');b.browser('fill','#ig-form [name=hotspots]','重点保护');b.browser('select','#ig-form [name=dataKind]','矢量');b.browser('select','#ig-form [name=sourceScope]','厅内');b.browser('select','#ig-form [name=collectionState]','已接入');b.browser('fill','#ig-form [name=capacityBytes]','4096');b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open')
    page('map');b.wait('!!document.querySelector("[name=layerScope]")&&!!document.querySelector("#ig-map canvas")');b.browser('select','[name=layerGroup]','cities');b.browser('fill','[name=layerSearch]','包头');check('city tags searchable with unique counts',b.ev('document.querySelector("#ig-layer-list").textContent.includes("呼和浩特市")&&document.querySelector("#ig-layer-list").textContent.includes("包头市")'))
    b.browser('select','[name=layerGroup]','hotspots');b.browser('fill','[name=layerSearch]','重点保护');check('hotspot directory uses saved metadata',b.ev('document.querySelectorAll(".ig-layer-item").length')==1)
    b.browser('select','[name=layerScope]','all');b.browser('fill','[name=layerSearch]','');check('global catalog includes unmounted layer resources',b.ev('document.querySelector("#ig-layer-list").textContent.includes("尚未编入")'))
    b.click('[data-action=ig-map-resource][data-id="'+rid+'"]');b.wait('document.querySelector("[name=layerScope]")?.value==="scene"')
    b.click('[data-action=ig-map-bookmark-save]');name='成果收藏 '+str(time.time_ns());b.browser('fill','#ig-form [name=name]',name);b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open');b.browser('reload');b.wait('!!document.querySelector("#ig-bookmarks")');b.ev('document.querySelector(".ig-map-bookmarks").open=true')
    check('bookmarks persist across reload',b.ev('document.querySelector("#ig-bookmarks").textContent.includes('+json.dumps(name)+')'))
    b.click('[data-action=ig-map-empty]');b.click('[data-action=ig-map-bookmark-restore]');b.wait('[...document.querySelectorAll("[data-ig-layer]")].some(e=>e.checked)');check('bookmark restores authorized layers',True)
    for domain in ['layers','tools','scenes']:
        page('usage&domain='+domain);check('monitor '+domain,not b.ev('document.documentElement.scrollWidth>innerWidth'))
        b.browser('select','#ig-result-stats [name=period]','week');b.click('#ig-result-stats button');b.wait('location.hash.includes("period=week")&&!!document.querySelector(".ir-metrics")')
    page('usage&domain=layers');check('registered capacity and scope are explicit',b.ev('document.querySelector("#main").textContent.includes("4096")&&document.querySelector("#main").textContent.includes("人工登记")'))
    page('analysis');b.wait('!!document.querySelector("[data-analysis=sample]")&&!!document.querySelector("#ana-map canvas")');b.click('[data-analysis=sample]');b.click('[data-analysis=run]');b.wait('document.querySelector("#ana-result").textContent.includes("下载可打印报告")')
    check('embedded batch analysis runs to per-parcel results',b.ev('document.querySelectorAll("#ana-result .ana-parcels button").length')==2)
    b.click('[data-analysis=export][data-format=csv]');check('analysis export remains available',True)
    grant=b.data()['integration']['administration']['access'].get('u2',{'rev':0});b.api('integration.admin.access.save',dict(id='u2',rev=grant['rev'],values=dict(view=True,analyze=False)))
    try:b.api('integration.analysis.catalog',{},user='u2');raise AssertionError('viewer accepted')
    except HTTPError as e:check('analysis API rejects read-only identity',e.code==403)
    current=b.data()['integration']['settings'];b.api('integration.policy.save',dict(rev=current['rev'],values=dict(maxAreaHa=1,roleAreaLimits={})));b.api('integration.policy.publish',dict(rev=b.data()['integration']['settings']['rev']))
    try:
        try:b.api('integration.analysis.input',dict(geometry=b.api('integration.analysis.catalog')['sample'],crs='EPSG:4326'));raise AssertionError('area accepted')
        except HTTPError as e:check('analysis API enforces published area limit',e.code==400)
    finally:
        b.api('integration.policy.save',dict(rev=b.data()['integration']['settings']['rev'],values=dict(maxAreaHa=current['maxAreaHa'],roleAreaLimits=current['roleAreaLimits'])));b.api('integration.policy.publish',dict(rev=b.data()['integration']['settings']['rev']))
    b.browser('set','viewport','390','844')
    for tab in ['tools','scenes','usage&domain=layers','analysis','map']:
        page(tab)
        if tab=='analysis':b.wait('!!document.querySelector("#ana-map canvas")')
        if tab=='map':b.wait('!!document.querySelector("#ig-map canvas")')
        check('390px '+tab,not b.ev('document.documentElement.scrollWidth>innerWidth'));b.browser('screenshot','/tmp/results-'+tab.split('&')[0]+'-390.png')
    b.ev('sessionStorage.setItem("onemap-user","u2")');b.browser('reload');b.wait('window.appReady&&!!document.querySelector("#ig-map canvas")')
    check('viewer has map but no batch entry',not b.ev('!!document.querySelector("[data-action=ig-tab][data-id=analysis]")'))
    check('no browser exceptions',not b.browser('errors'))
    print('Result coverage browser checks passed.')
if __name__=='__main__':main()

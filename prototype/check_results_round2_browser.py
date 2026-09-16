"""Use isolated QA with the extra published scene from ResultCoverage.extra_scene."""
import json
import check_integration_domains_browser as b
b.SESSION='results-round2'
def page(tab):
 b.page('admin/integration-results?tab='+tab,'一张图成果')
def draw():
 b.browser('scrollintoview','#ana-map')
 x,y=b.ev('(()=>{const r=document.querySelector("#ana-map .pc-ol-target").getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()')
 for dx,dy in [(-35,-25),(35,-25),(0,30),(-35,-25)]:
  b.browser('mouse','move',str(round(x+dx)),str(round(y+dy)));b.browser('mouse','down');b.browser('mouse','up')
def count(n):b.wait('document.querySelectorAll(".ana-draft-row").length==='+str(n))
def main():
 b.browser('open',b.BASE);b.ev('sessionStorage.setItem("onemap-user","admin");sessionStorage.removeItem("ig-map-state-admin")');b.browser('reload');b.browser('set','viewport','1440','1000')
 page('map');b.wait('!!document.querySelector("#ig-map canvas")&&!!document.querySelector("[name=layerScope]")')
 b.browser('select','[name=layerScope]','all');b.click('[data-action=ig-map-resource][data-id=r3]');b.wait('!!document.querySelector("[data-ig-layer=\\"overlay:r3\\"]")')
 b.check('catalog overlays without switching base scene',b.ev('document.querySelector("[name=scene]").value==="scene_cropland"&&document.querySelectorAll("[data-ig-layer]").length===3'))
 b.click('[data-action=ig-map-bookmark-save]');b.browser('fill','#ig-form [name=name]','跨场景组合测试');b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open')
 b.browser('reload');b.wait('!!document.querySelector("[data-ig-layer=\\"overlay:r3\\"]")');b.check('overlay survives reload',True)
 b.click('[data-action=ig-map-remove-overlay][data-id=r3]');b.wait('!document.querySelector("[data-ig-layer=\\"overlay:r3\\"]")')
 b.ev('document.querySelector(".ig-map-bookmarks").open=true');b.click('[data-action=ig-map-bookmark-restore]');b.wait('!!document.querySelector("[data-ig-layer=\\"overlay:r3\\"]")');b.check('bookmark restores overlay source',True)
 page('analysis');b.wait('!!document.querySelector("#ana-map canvas")');b.click('[data-analysis=sample]');count(2)
 b.click('[data-analysis=draw]');draw();count(3);b.check('drawing appends without replacing previous parcels',b.ev('JSON.parse(document.querySelector("#ana-geometry").value).features[0].properties.id==="parcel-1"'))
 b.click('[data-analysis=parcel-edit][data-index="2"]');b.browser('fill','#ana-editor-name','追加编辑地块');b.click('[data-analysis=parcel-edit-save]');b.check('edit changes selected name',b.ev('document.querySelector("#ana-draft-list").textContent.includes("追加编辑地块")'))
 b.click('[data-analysis=parcel-redraw][data-index="2"]');draw();count(3);b.check('redraw keeps identity and other parcels',b.ev('JSON.parse(document.querySelector("#ana-geometry").value).features[2].properties.name==="追加编辑地块"'))
 b.click('[data-analysis=parcel-remove][data-index="2"]');count(2);b.click('[data-analysis=run]');b.wait('document.querySelector("#ana-result").textContent.includes("下载可打印报告")');b.check('edited batch runs with remaining parcels',b.ev('document.querySelectorAll("#ana-result .ana-parcels button").length===2'))
 page('usage&domain=layers');b.wait('!!document.querySelector(".ir-metrics")');b.check('resource scale cards',b.ev('["可见数据库表","矢量图层","栅格图层","证照图层","形态未登记图层"].every(x=>document.querySelector("#main").textContent.includes(x))'))
 b.browser('set','viewport','390','844')
 for tab in ['analysis','usage&domain=layers','map']:
  page(tab)
  b.wait('!!document.querySelector('+json.dumps('#ana-map canvas' if tab=='analysis' else '#ig-map canvas' if tab=='map' else '.ir-metrics')+')')
  if tab=='analysis':b.click('[data-analysis=sample]');count(2)
  b.check('mobile '+tab,not b.ev('document.documentElement.scrollWidth>innerWidth'))
  b.browser('screenshot','/tmp/results-round2-'+tab.split('&')[0]+'.png')
 b.check('no browser exceptions',not b.browser('errors'))
 print('Round 2 browser checks passed.',flush=True)
if __name__=='__main__':main()

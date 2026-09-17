"""OpenLayers browser regression. Run against an independent demo database."""
import json
import os
import subprocess

BASE = os.environ.get('DEMO_QA_URL', 'http://127.0.0.1:5198')
SESSION = 'onemap-map-regression'


def browser(*args, script=None):
    result = subprocess.run(['agent-browser', '--session', SESSION, *args], input=script,
                            text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def js(script):
    return json.loads(browser('eval', '--stdin', script=script))


def wait(expression):
    assert js('(async()=>{for(let i=0;i<60;i++){if(' + expression + ')return true;'
              'await new Promise(r=>setTimeout(r,100));}return false;})()'), expression


def mouse_click(x, y):
    browser('mouse', 'move', str(x), str(y))
    browser('mouse', 'down')
    browser('mouse', 'up')


try:
    browser('set', 'viewport', '1440', '1080')
    browser('open', BASE + '/#/front/scenes/scene_cropland')
    wait('window.appReady && document.querySelector(".ol-layer canvas")')
    assert js('document.querySelector(".pc-map-surface").dataset.engine') == 'openlayers'
    assert js('document.querySelectorAll("[data-base-id^=demo-]").length') == 3
    browser('check', '[data-admin=counties]')
    assert js('document.querySelector("[data-admin=counties]").checked')
    counts=js('(async()=>{const {demoMapData:d}=await import("/frontend/demo-map-data.js");return [d.cities.features.length,d.counties.features.length];})()')
    assert counts == [12,103]
    js('window.originalCanvas=document.querySelector(".ol-viewport");true')
    browser('select', '[name=sceneRegion]', '包头市')
    browser('click', '[data-base-id=base-gray]')
    browser('uncheck', '[data-scene-layer]:not(:disabled)')
    browser('check', '[data-scene-layer]:not(:disabled)')
    assert js('originalCanvas===document.querySelector(".ol-viewport")')
    assert js('document.querySelector(".pc-map-surface").dataset.base') == 'base-gray'
    browser('screenshot', '/tmp/onemap-openlayers-scene.png', '--full')
    print('PASS scene rendering, region locator, base style, stable canvas on layer toggle', flush=True)

    # Exercise the public adapter with deterministic geometry and real pointer input.
    js('''(async()=>{
      const {mountSceneMap}=await import('/frontend/map.js?v=demo-map-v1');
      window.fixture=document.createElement('div');
      fixture.style.cssText='position:fixed;inset:0 auto auto 0;width:900px;height:600px;z-index:10000;background:white';
      document.body.append(fixture);
      const feature={id:'allowed',name:'测试图斑',coordinates:[[110.7,40.7],[111.3,40.7],[111.3,41.3],[110.7,41.3]]};
      window.mapConfig={extent:[108,38,114,44],basemaps:[{id:'base-terrain',name:'自然地理',category:'基础底图'},{id:'base-gray',name:'浅色底图',category:'基础底图'}],defaultBase:'base-terrain',widgets:[{code:'query'},{code:'measure'}],layers:[{id:'allowed-layer',access:'已授权',visible:true,features:[feature]},{id:'restricted-layer',access:'需申请',visible:true,features:[{...feature,id:'restricted'}]}]};
      window.mapQA=await mountSceneMap(fixture,mapConfig,{onSelect:f=>window.picked=f.id,onMeasure:r=>window.measured=r});
      mapQA.restoreViewState({center:[111,41],resolution:.005,rotation:0,basemapId:'base-gray'});
      return true;
    })()''')
    mouse_click(450, 300)
    wait('window.picked === "allowed"')
    assert js('''(()=>{const before=mapQA.getViewState();mapConfig.layers[0].visible=false;mapQA.setLayers(mapConfig.layers);return JSON.stringify(before)===JSON.stringify(mapQA.getViewState());})()''')
    js('window.picked=null;true')
    mouse_click(450, 300)
    assert js('window.picked') is None
    js('mapConfig.layers[0].visible=true;mapQA.setLayers(mapConfig.layers);true')
    browser('click', '[style*="z-index: 10000"] [data-map=draw]')
    mouse_click(250, 160)
    mouse_click(600, 160)
    mouse_click(600, 350)
    mouse_click(250, 160)  # Close the polygon by clicking its first vertex.
    wait('window.measured && Number(measured.area)>0')
    assert js('measured.coordinates[0].toString()===measured.coordinates.at(-1).toString()')
    assert js('fixture.querySelector("[data-map=draw]").getAttribute("aria-pressed")') == 'false'
    js('mapQA.destroy();mapQA.destroy();fixture.remove();true')
    print('PASS feature query, denied/hidden layers, view preservation, polygon measurement, disposal', flush=True)

    browser('set', 'viewport', '390', '844')
    wait('document.querySelector(".ol-viewport").clientWidth > 0')
    assert not js('document.documentElement.scrollWidth>innerWidth')
    browser('scrollintoview', '.pc-ol-target')
    browser('screenshot', '/tmp/onemap-openlayers-mobile.png')
    browser('open', BASE + '/#/front/intelligence')
    wait('window.appReady && !document.querySelector(".ol-viewport")')
    assert not browser('errors')
    print('PASS mobile layout and route teardown; no browser errors', flush=True)
except Exception:
    print(js('JSON.stringify({measured:window.measured,fixture:window.fixture?.innerHTML})'))
    browser('screenshot', '/tmp/onemap-draw-failure.png')
    raise
finally:
    browser('close')

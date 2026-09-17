"""Read-only responsive route checks using agent-browser and an isolated browser.
Start server.py with an independent --db, then set DEMO_QA_URL before running.
"""
import json
import os
from pathlib import Path
import subprocess

BASE=os.environ.get('DEMO_QA_URL','http://127.0.0.1:5217')
SESSION='public-route-regression'
ROOT=Path(__file__).resolve().parents[1]/'reports'
ROOT.mkdir(exist_ok=True)
(ROOT/'screenshots').mkdir(exist_ok=True)
checks=[]

def browser(*args,script=None):
    r=subprocess.run(['agent-browser','--session',SESSION,'--json',*args],input=script,text=True,capture_output=True,timeout=35)
    if r.returncode:raise RuntimeError(r.stderr or r.stdout)
    result=json.loads(r.stdout)
    if not result.get('success'):raise RuntimeError(result)
    return result.get('data',{})

def evaluate(script):return browser('eval','--stdin',script=script)['result']

routes=[('home','一张图'),('data','数据服务'),('catalog','数据服务'),('search?q=矿业权','综合搜索'),('data/r_scene_demo','耕地监测示例图层'),('map','地图浏览'),('capabilities','工具中心'),('tools','工具中心'),('capabilities/coordinate','坐标转换'),('capabilities/area','面积量算'),('capabilities/buffer','点缓冲区分析'),('services','办事服务'),('services/notice','国土空间规划公示'),('services/progress','用地审批进度查询'),('knowledge','资讯下载'),('landscape','大美内蒙古'),('landscape/ecology','北疆安全生态屏障'),('requests','我的咨询与意见'),('app-center','应用中心'),('internal-home','资源汇聚一张图'),('assistant','资源检索助手')]
try:
    for width in [1440,1024,390]:
        browser('set','viewport',str(width),'900')
        for route,heading in routes:
            browser('open',BASE+'/#/front/'+route)
            browser('wait','--fn',"window.appReady === true && !!document.querySelector('#main')")
            browser('snapshot','-i')
            data=evaluate("""({width:innerWidth,scroll:document.documentElement.scrollWidth,text:document.querySelector('#main').innerText,nav:[...document.querySelectorAll('.portal-nav>a')].map(a=>a.innerText)})""")
            assert data['scroll']<=width+1,(width,route,'horizontal overflow',data['scroll'])
            assert heading in data['text'],(route,'heading missing',data['text'][:300])
            assert data['nav']==['首页','数据服务','能力服务','办事服务','资讯下载','大美内蒙古'],data['nav']
            if route=='home':assert '任务督办' not in data['text'] and '我的待办' not in data['text']
            if route.startswith('search'):assert '矿业权基础信息表' in data['text']
            if route in ['map','data/r_scene_demo','capabilities/area']:
                browser('wait','--fn',"document.querySelectorAll('canvas').length > 0")
            checks.append({'width':width,'route':route,'status':'passed'})
        print(f'{width}px: {len(routes)} routes passed',flush=True)
    errors=browser('errors')
    (ROOT/'public-portal-checks.json').write_text(json.dumps({'checks':checks,'browserErrors':errors},ensure_ascii=False,indent=2))
    print(f'{len(checks)} responsive route checks passed; result: public-portal-checks.json',flush=True)
finally:
    browser('close')

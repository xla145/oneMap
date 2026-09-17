"""Tool requirements regression; run against an isolated DEMO_QA_URL database."""
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen
import check_portal_admin_browser as b


def state(user='admin',mode='admin'):
    with urlopen(Request(b.BASE+'/api/bootstrap',headers={'X-Demo-User':user,'X-Demo-Mode':mode})) as response:return json.load(response)


def check_direct_use():
    for user in ['admin','u1']:
        for key in ['coordinate','area','buffer','overlay','compliance']:
            b.page('front/capabilities',user)
            b.click('[data-tool-use="'+key+'"]')
            b.wait('location.hash.includes("view=use")')
            assert not b.ev('!!document.querySelector(".tc-detail")')
            if key in ['coordinate','area','buffer']:
                b.wait('!!document.querySelector("#pub-tool")');b.submit('#pub-tool')
                b.wait('document.querySelector("#pub-tool-result").textContent.includes("'+('转换结果' if key=='coordinate' else '计算完成')+'")')
            else:
                b.wait('!!document.querySelector("#ana-geometry")')
                b.click('[data-analysis=sample]')
                b.click('[data-analysis='+('spatial' if key=='overlay' else 'run')+']')
                b.wait('document.querySelector("'+('#ana-status' if key=='overlay' else '#ana-result')+'").textContent.includes("'+('计算完成' if key=='overlay' else '任务结果')+'")')
            print('OK direct use',user,key,flush=True)


def main():
    assert os.environ.get('DEMO_QA_URL'),'Set DEMO_QA_URL to an isolated QA server'
    b.SESSION='tool-requirements-qa'
    b.browser('open',b.BASE);b.browser('set','viewport','1440','1000')
    check_direct_use()
    b.page('front/capabilities','u1')
    b.fill('#tc-filter [name=q]','坐标');b.submit('#tc-filter')
    b.wait('document.querySelectorAll(".pub-card").length===1')
    b.page('front/capabilities/coordinate','u1');b.submit('#tc-test')
    b.wait('document.querySelector("#tc-output").textContent.includes("EPSG:4546")')
    assert '执行失败' not in b.ev('document.querySelector("#tc-output").textContent')
    print('OK catalogue search and CGCS2000 online test',flush=True)

    b.page('admin/portal-tools');b.click('[data-action=pm-edit][data-id="tools:"]')
    name='工具中心验收'+str(time.time_ns())
    b.fill('#pm-editor [name=name]',name);b.fill('#pm-editor [name=category]','验收组件')
    b.browser('select','#pm-editor [name=engine]','area');b.browser('select','#pm-editor [name=module]','面积核算')
    b.browser('select','#pm-editor [name=region]','包头市');b.browser('select','#pm-editor [name=directoryId]','dir-tool')
    b.fill('#pm-editor [name=provider]','验收数源单位');b.fill('#pm-editor [name=apiDescription]','接收空间图形并核算面积')
    b.browser('screenshot','/tmp/tool-center-upload.png');b.browser('upload','#pm-editor [name=screenshotFile]','/tmp/tool-center-upload.png')
    b.submit('#pm-editor');b.wait('!document.querySelector("#dialog").open')
    tool=next(r for r in state()['portalManagement']['tools'] if r['name']==name);key=tool['id']
    def revision():return next(r['rev'] for r in state()['portalManagement']['tools'] if r['id']==key)
    b.api('centers.tool.submit',{'id':key,'rev':revision()});b.api('centers.tool.review',{'id':key,'rev':revision(),'decision':'通过','note':'截图与接口信息符合要求'})
    b.api('portal.publish',{'entity':'tools','id':key,'rev':revision()})
    b.page('front/capabilities','u1');b.browser('select','#tc-filter [name=region]','包头市');b.submit('#tc-filter');b.wait('document.querySelectorAll(".pub-card").length===1')
    assert name in b.ev('document.querySelector("main").textContent')
    b.page('front/capabilities/'+key,'u1');assert b.ev('!!document.querySelector(".tc-detail-image")')
    assert '验收数源单位' in b.ev('document.querySelector("main").textContent')
    b.submit('#tc-test');b.wait('document.querySelector("#tc-output").textContent.includes("areaSquareMeters")')
    print('OK registration, screenshot, review, catalogue linkage and real area test',flush=True)

    b.page('admin/portal-tools');b.click('[data-action=pm-tool-permissions]');b.click('[data-action=pm-permission-add]')
    b.browser('select','#pm-tool-permissions [name=category0]','验收组件');b.browser('select','#pm-tool-permissions [name=module0]','面积核算')
    b.submit('#pm-tool-permissions');b.wait('!document.querySelector("#dialog").open')
    b.page('front/capabilities','u1');assert name not in b.ev('document.querySelector("main").textContent')
    b.page('admin/portal-tools');b.click('[data-action=pm-tool-permissions]');b.click('[data-action=pm-permission-remove]');b.submit('#pm-tool-permissions');b.wait('!document.querySelector("#dialog").open')
    print('OK role, category and module restriction',flush=True)

    b.page('front/capabilities','u1');b.click('[data-action=tc-apply]')
    assert b.ev('!!document.querySelector("#apply-form")')
    b.fill('#apply-form [name=purpose]','工具中心浏览器验收使用申请');b.submit('#apply-form');b.wait('!document.querySelector("#dialog").open')
    b.page('front/applications','u1');assert '工具中心浏览器验收使用申请' in b.ev('document.querySelector("main").textContent')
    print('OK shared resource application flow',flush=True)

    for width in [1440,390]:
        b.browser('set','viewport',str(width),'1000')
        for route in ['front/capabilities','front/capabilities/'+key,'admin/center-tools']:
            b.page(route,'admin' if route.startswith('admin') else 'u1')
            assert not b.ev('document.documentElement.scrollWidth>innerWidth'),(width,route)
        b.page('front/capabilities','u1');b.browser('screenshot',str(b.ROOT/'screenshots'/('tool-center-'+str(width)+'.png')))
    assert not b.browser('errors'),b.browser('errors')
    print('OK desktop/mobile layouts; tool center browser checks passed',flush=True)


if __name__=='__main__':main()

"""Optimization regression. Run against isolated QA storage only."""
import base64,json,os,struct,tempfile,time,zlib
from pathlib import Path
import check_integration_browser as b
b.SESSION='integration-opt'

def png():
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',4,4,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes([30,110,80])*4)*4))+chunk(b'IEND',b'')

def main():
    b.browser('open',b.BASE);b.browser('set','viewport','1440','1000');b.page('admin/center-integration')
    b.page('admin/center-integration?tab=presentation');b.click('[data-action=ig-edit][data-id="contents:"]')
    name='优化验收Banner'+str(time.time_ns());b.fill('#ig-form [name=name]',name);b.fill('#ig-form [name=description]','图片上传、预览和历史版本验收')
    with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as f:f.write(png());path=f.name
    b.browser('upload','[data-ig-upload=image]',path);b.wait('document.querySelector("#ig-form [name=imageData]").value.startsWith("data:image/")')
    b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open');Path(path).unlink()
    ident=b.ev('[...document.querySelectorAll("tbody tr")].find(r=>r.textContent.includes('+json.dumps(name)+')).querySelector("[data-action=ig-preview]").dataset.id')
    b.click('[data-action=ig-preview][data-id="'+ident+'"]');b.wait('!!document.querySelector("#dialog [name=previewUser]") && document.querySelector("#dialog img")?.complete')
    assert b.ev('document.querySelector("#dialog img").naturalWidth>0')
    b.browser('select','[name=previewUser]','u1');b.wait('document.querySelector("#dialog [role=status]").textContent.includes("可见")')
    b.browser('screenshot','/tmp/onemap-integration-draft-preview.png');b.click('[aria-label="关闭弹窗"]')
    b.click('[data-action=ig-publish][data-id="'+ident+'"]');b.browser('wait','--text','已保存')
    b.click('[data-action=ig-edit][data-id="'+ident+'"]');b.fill('#ig-form [name=name]',name+'第二版');b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open');b.click('[data-action=ig-publish][data-id="'+ident+'"]')
    b.click('[data-action=ig-versions][data-id="'+ident+'"]');b.wait('document.querySelector("#dialog").textContent.includes("v2")')
    assert b.ev('document.querySelectorAll("#dialog [data-action=ig-restore]").length')==2
    b.click('[aria-label="关闭弹窗"]')
    # Restore API has backend version/concurrency coverage; inspect the resulting draft through UI.
    key=ident.split(':')[1]
    versions=b.api('integration.versions',dict(entity='contents',id=key))
    b.api('integration.restore',dict(entity='contents',id=key,rev=versions['rev'],version=1))
    b.page('admin/integration-resources','admin');assert b.ev('document.querySelector("main").textContent.includes('+json.dumps(name+'第二版')+')')
    b.page('front/integrated-portal','u1');assert b.ev('document.querySelector("main").textContent.includes('+json.dumps(name+'第二版')+')')
    print('OK image upload, preview, publication history and non-publishing restore',flush=True)
    b.page('admin/center-integration');b.page('admin/center-integration?tab=presentation');b.click('[data-action=ig-settings]')
    b.browser('check','#ig-form [name=bannerAutoplay]');b.fill('#ig-form [name=bannerSeconds]','3')
    b.click('#ig-form [type=submit]');b.wait('!document.querySelector("#dialog").open');b.click('[data-action=ig-settings-publish]')
    b.page('front/integrated-portal','u1');assert b.ev('document.querySelector(".ig-carousel")!==null');b.click('[data-action=ig-slide-pause]')
    assert b.ev('document.querySelector("[data-action=ig-slide-pause]").textContent.includes("继续")')
    b.click('[data-action=ig-resource-kind][data-id=知识]');b.wait('!!document.querySelector(".ct-catalog-filters")');b.click('[data-action=ig-open][data-id="'+b.ev('[...document.querySelectorAll("[data-action=ig-open]")].find(e=>e.dataset.id.startsWith("knowledge:")).dataset.id')+'"]');b.wait('document.querySelector("#dialog").open')
    assert b.ev('!!document.querySelector("#dialog .portal-document-body")')
    b.click('[aria-label="关闭弹窗"]');b.browser('select','.ct-catalog-filters [name=kind]','智能体');b.click('[data-action=ig-open][data-id="'+b.ev('document.querySelector("[data-action=ig-open]").dataset.id')+'"]');b.wait('document.querySelector("#dialog").open')
    assert b.ev('!!document.querySelector("#dialog [data-action=useAgent]")')
    print('OK carousel controls and exact knowledge/agent details',flush=True)
    b.page('admin/center-integration');b.page('admin/center-integration?tab=monitor');b.wait('!!document.querySelector(".ig-columns")')
    b.browser('select','#ig-monitor-filter [name=period]','week');b.browser('select','#ig-monitor-filter [name=eventType]','success');b.click('#ig-monitor-filter [type=submit]');b.wait('!!document.querySelector(".ig-columns")')
    assert b.ev('document.querySelector("main").textContent.includes("工具成功")')
    b.browser('screenshot','/tmp/onemap-integration-filtered-monitor.png')
    b.browser('set','viewport','390','844')
    for route in ['front/integrated-portal','front/integrated-workbench','admin/center-integration']:
        b.page(route);assert not b.ev('document.documentElement.scrollWidth>innerWidth'),route
    print('OK monitor filters and mobile layout',flush=True)
    print('Integration optimization browser checks passed.',flush=True)
if __name__=='__main__':main()

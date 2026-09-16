"""Content workflows; run against an isolated QA database only."""
import json
import check_portal_admin_browser as qa
qa.SESSION='content-admin-qa'

def main():
    qa.browser('open',qa.BASE);qa.wait('window.appReady === true')
    qa.browser('set','viewport','1440','1000')
    for tab in ['settings','topics','services','tickets']:
        qa.page('admin/public-portal?tab='+tab)
        assert qa.ev("!document.querySelector('main .pub-tabs')")
    qa.page('admin/public-portal?tab=services')
    qa.click('[data-action=pub-edit][data-id="services:"]')
    for key,value in dict(name='内容管理验收事项',category='测试',body='办理说明',process='申请 → 审核',materials='申请表',timeLimit='5 个工作日',phone='0471-12345',order='0').items():
        qa.fill('#pub-editor [name='+key+']',value)
    qa.submit('#pub-editor');qa.wait("!document.querySelector('#dialog').open")
    key=qa.ev("[...document.querySelectorAll('tbody tr')].find(r=>r.textContent.includes('内容管理验收事项')).querySelector('[data-action=pub-preview]').dataset.id")
    qa.click('[data-action=pub-preview][data-id="'+key+'"]')
    assert qa.ev("document.querySelector('#dialog').textContent.includes('申请表')")
    qa.browser('press','Escape')
    qa.click('[data-action=pub-publish][data-id="'+key+'"]');qa.browser('wait','--text','已发布，对外门户已更新')
    qa.page('front/services/'+key.split(':')[1],'u1')
    assert qa.ev("document.querySelector('main').textContent.includes('5 个工作日')")
    qa.fill('#pub-ticket [name=title]','浏览器咨询验收');qa.fill('#pub-ticket [name=body]','请问材料要求');qa.submit('#pub-ticket')
    qa.browser('wait','--text','浏览器咨询验收')
    qa.page('admin/public-portal?tab=tickets');qa.click('[data-action=pub-reply]')
    assert qa.ev("document.querySelector('#dialog').textContent.includes('请问材料要求')")
    qa.fill('#pub-reply [name=reply]','请提交申请表');qa.submit('#pub-reply');qa.wait("!document.querySelector('#dialog').open")
    qa.page('front/requests','u1');assert qa.ev("document.querySelector('main').textContent.includes('请提交申请表')")
    qa.page('admin/public-portal?tab=services')
    qa.fill('#pub-admin-filter [name=q]','内容管理验收事项');qa.submit('#pub-admin-filter')
    qa.wait("document.querySelectorAll('tbody tr').length === 1")
    qa.click('[data-action=pub-disable][data-id="'+key+'"]');qa.browser('wait','--text','已下架')
    qa.click('[data-action=pub-delete][data-id="'+key+'"]');qa.submit('#pub-delete-confirm');qa.wait("!document.querySelector('#dialog').open")
    assert qa.ev("document.querySelector('tbody').textContent.includes('没有符合条件')")
    qa.page('admin/public-portal?tab=services')
    qa.browser('screenshot',str(qa.ROOT/'screenshots'/'content-admin-services.png'))
    for tab in ['topics','tickets','settings']:
        qa.page('admin/public-portal?tab='+tab)
        qa.browser('screenshot',str(qa.ROOT/'screenshots'/('content-admin-'+tab+'.png')))
    qa.browser('set','viewport','390','844')
    for tab in ['settings','topics','services','tickets']:
        qa.page('admin/public-portal?tab='+tab)
    qa.page('admin/public-portal?tab=unknown')
    assert qa.ev("document.querySelector('main h1').textContent === '大美内蒙古专题'")
    assert not qa.browser('errors')
    print('PASS: 8 desktop/mobile views, fallback route, create/preview/publish/front guide, feedback/reply, search/disable/delete')

if __name__=='__main__':main()

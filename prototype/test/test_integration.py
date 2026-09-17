import unittest
import json
from copy import deepcopy
import integration as ig
import centers
import capabilities as cap
from seed import seed
from server import execute,bootstrap,user_for

class IntegrationWorkflows(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.a=user_for(self.s,'admin');self.u=user_for(self.s,'u1');self.other=user_for(self.s,'u2');bootstrap(self.s,self.a,'admin');self.p=ig.migrate(self.s)
    def call(self,op,p=None,u=None):return execute(self.s,u or self.a,'integration.'+op,p or {})
    def save(self,entity,values,old=None):return self.call('save',dict(entity=entity,values=values,**({'id':old['id'],'rev':old['rev']} if old else {})))
    def change(self,op,entity,r):return self.call(op,dict(entity=entity,id=r['id'],rev=r['rev']))
    def tenant(self,name='盟市甲',parent='tenant-province',level='盟市',u=None,rights=None):return self.call('tenant.save',dict(values=dict(name=name,region='呼和浩特市',parentId=parent,level=level,enabled=True,permissions=rights or ig.PERMS)),u)
    def member(self,t,u,rights):return self.call('tenant.member',dict(tenantId=t['id'],values=dict(userId=u['id'],permissions=rights)))
    def content(self):return self.save('contents',dict(name='验收Banner',kind='banner',description='说明',audience='全部',order=1,color='#123456',url='#/front/shared-resources'))
    def notice(self,**kwargs):return self.save('announcements',dict(name='更新通知',body='数据与功能已更新',**kwargs))
    def test_draft_publish_edit_and_disable(self):
        r=self.content();self.assertFalse(any(x['name']==r['name'] for x in ig.bootstrap(self.s,self.u,'front')['contents']))
        r=self.change('publish','contents',r);self.assertTrue(any(x['name']==r['name'] for x in ig.bootstrap(self.s,self.u,'front')['contents']))
        edited=self.save('contents',dict(r,name='未发布改动'),r);self.assertTrue(any(x['name']=='验收Banner' for x in ig.bootstrap(self.s,self.u,'front')['contents']))
        self.change('disable','contents',edited);self.assertFalse(any(x['name']=='验收Banner' for x in ig.bootstrap(self.s,self.u,'front')['contents']))
    def test_stale_revision_and_admin_boundary(self):
        r=self.content()
        with self.assertRaises(cap.Invalid):self.call('publish',dict(entity='contents',id=r['id'],rev=0))
        for op in ['save','inspect','monitor','settings.publish','peer.save','placement']:
            with self.assertRaises(cap.Invalid):self.call(op,{},self.u)
    def test_unsafe_content_and_admin_navigation(self):
        for url in ['javascript:alert(1)','http://example.org','#/admin/overview']:
            with self.assertRaises(cap.Invalid):self.save('contents',dict(name='非法链接',url=url,audience='全部'))
        with self.assertRaises(cap.Invalid):self.save('contents',dict(name='非法颜色',color='red;background:url(x)'))
    def test_announcement_scope_expiry_and_revision_read(self):
        r=self.notice(audience='平台管理员');r=self.change('publish','announcements',r);self.assertEqual(ig.messages(self.s,self.u),[])
        r=self.notice(endsAt='2020-01-01');self.change('publish','announcements',r);self.assertEqual(ig.messages(self.s,self.u),[])
        r=self.notice();r=self.change('publish','announcements',r);m=ig.messages(self.s,self.u)[0];self.call('message.read',dict(id=m['id']),self.u)
        self.assertTrue(ig.messages(self.s,self.u)[0]['read']);self.assertFalse(ig.messages(self.s,self.other)[0]['read'])
        r=self.change('publish','announcements',r);self.assertFalse(ig.messages(self.s,self.u)[0]['read'])
    def test_message_cannot_read_another_recipient(self):
        self.s['platform']['notifications'].append(dict(id='private',recipientId='u1',title='私信',body='正文',at='2026-01-01',read=False))
        with self.assertRaises(cap.Invalid):self.call('message.read',dict(id='message:private'),self.other)
        self.call('message.read',dict(id='message:private'),self.u);self.assertTrue(self.s['platform']['notifications'][-1]['read'])
    def test_preference_isolation_and_validation(self):
        v=dict(ig.DEFAULT_PREF,quietStart='23:00',quietEnd='07:00',order=['resource:r1'],groups={'resource:r1':'常用'})
        self.call('preferences',dict(rev=1,values=v),self.u)
        self.assertEqual(ig.prefs(self.p,self.other)['quietStart'],'')
        for changes in [dict(refreshSeconds=1),dict(quietStart='25:00'),dict(order=['resource:hidden']),dict(metrics=['任意SQL'])]:
            with self.assertRaises(cap.Invalid):self.call('preferences',dict(rev=2,values=dict(v,**changes)),self.u)
    def test_statistics_record_real_visible_access_only(self):
        self.assertEqual(ig.metrics(self.s,self.u)['popular'],[])
        self.call('open',dict(id='resource:r1'),self.u);self.call('search',dict(query='地灾'),self.u)
        self.assertEqual(ig.metrics(self.s,self.u)['popular'][0]['count'],1)
        self.assertEqual(ig.metrics(self.s,self.u)['hotwords'][0]['name'],'地灾')
        with self.assertRaises(cap.Invalid):self.call('open',dict(id='resource:r12'),self.u)
    def test_settings_publish_is_separate_from_draft(self):
        old=self.p['settings'];r=self.call('settings.save',dict(rev=old['rev'],values=dict(title='新标题',subtitle='新说明',theme='blue')))
        self.assertNotEqual(ig.bootstrap(self.s,self.u,'front')['settings']['title'],'新标题')
        self.call('settings.publish',dict(rev=r['rev']));self.assertEqual(ig.bootstrap(self.s,self.u,'front')['settings']['title'],'新标题')
    def test_catalog_placement_does_not_publish_private_asset(self):
        with self.assertRaises(cap.Invalid):self.call('placement',dict(id='resource:missing',values={}))
        self.call('placement',dict(id='resource:r1',values=dict(theme=ig.THEMES[0],department='自然资源厅')))
        self.assertEqual(next(r for r in ig.catalog(self.s,self.u) if r['id']=='resource:r1')['placement']['theme'],ig.THEMES[0])
    def test_tenant_workspace_isolation_and_ancestor_revocation(self):
        a=self.tenant();b=self.tenant('盟市乙');self.member(a,self.u,['read','write'])
        self.call('tenant.asset',dict(tenantId=a['id'],values=dict(name='甲的资源',description='甲数据')),self.u)
        self.call('tenant.asset',dict(tenantId=b['id'],values=dict(name='乙的资源',description='乙数据')))
        self.assertEqual(len(ig.bootstrap(self.s,self.u,'front')['tenantAssets']),1)
        with self.assertRaises(cap.Invalid):self.call('tenant.asset',dict(tenantId=b['id'],values=dict(name='越权')),self.u)
        a=self.call('tenant.save',dict(id=a['id'],rev=a['rev'],values=dict(a,permissions=['read'])))
        with self.assertRaises(cap.Invalid):self.call('tenant.asset',dict(tenantId=a['id'],values=dict(name='撤权后写入')),self.u)
    def test_tenant_admin_cannot_delegate_unheld_permission(self):
        a=self.tenant();self.member(a,self.u,['read','members'])
        with self.assertRaises(cap.Invalid):self.call('tenant.member',dict(tenantId=a['id'],values=dict(userId='u2',permissions=['read','write'])),self.u)
    def test_tenant_level_scope_and_disabled_ancestor(self):
        a=self.tenant();child=self.tenant('旗县甲',a['id'],'旗县');self.member(child,self.u,['read'])
        with self.assertRaises(cap.Invalid):self.tenant('跳级县','tenant-province','旗县')
        with self.assertRaises(cap.Invalid):self.tenant('越权下级',a['id'],'旗县',self.u)
        self.call('tenant.save',dict(id=a['id'],rev=a['rev'],values=dict(a,enabled=False)))
        self.assertEqual(ig.visible_tenants(self.p,self.u),[])
    def test_exchange_batch_validation_atomic_and_history(self):
        peer=self.p['peers'][0];r=self.call('exchange.import',dict(id=peer['id'],rows=[dict(id='one',name='资源',kind='图层服务',url='https://example.org'),dict(id='two',name='失败',kind='图层服务',url='javascript:bad')]))
        self.assertEqual(r['status'],'导入失败');self.assertEqual(r['rows'],[])
        r=self.call('exchange.import',dict(id=peer['id'],rows=[dict(id='one',name='资源',kind='图层服务',url='https://example.org')]))
        self.assertEqual(r['count'],1);self.assertEqual(len(self.p['exchanges']),2)
        self.assertFalse(any(row['id']=='one' for row in ig.catalog(self.s,self.u)))
    def test_exchange_direction_and_status_honesty(self):
        peer=self.p['peers'][0];r=self.call('peer.save',dict(id=peer['id'],rev=peer['rev'],values=dict(peer,endpoint='https://example.org',authClientId='client_portal',direction='导入')))
        self.assertEqual(r['status'],'配置完整·待联调')
        with self.assertRaises(cap.Invalid):self.call('exchange.export',dict(id=r['id']))
        check=self.call('inspect');self.assertTrue(any(x['status']=='待外部联调' for x in check['failures']))
    def test_received_directory_upserts_and_failed_batch_does_not_overwrite(self):
        rows=[dict(id='external',name='第一次',kind='图层服务',url='https://example.org')]
        self.call('exchange.import',dict(id='national',rows=rows))
        rows[0]['name']='更新名称';r=self.call('exchange.import',dict(id='national',rows=rows))
        self.assertEqual(r['updatedCount'],1);self.assertEqual(len(self.p['received']),1)
        self.call('exchange.import',dict(id='national',rows=rows+[dict(id='bad',name='不合格',kind='非法',url='')]))
        self.assertEqual(self.p['received'][0]['rev'],2)
        self.assertEqual(ig.bootstrap(self.s,self.u,'front')['received'],[])
    def test_save_roundtrip_persistence(self):
        self.content();state=json.loads(json.dumps(self.s));self.assertEqual(len(ig.migrate(state)['contents']),6)
    def test_map_query_modes_history_and_reauthorization(self):
        req=dict(sceneId='scene_cropland',mode='penetrate',x=111.7,y=40.8)
        result=self.call('map.query',req);self.assertGreaterEqual(result['total'],2)
        self.assertEqual(self.call('map.query',dict(req,mode='point'))['total'],1)
        self.assertGreater(self.call('map.query',dict(req,mode='nearby',radius=100))['total'],0)
        self.assertEqual(len(self.p['mapHistory']),3)
        self.assertEqual(ig.bootstrap(self.s,self.u,'front')['mapHistory'],[])
        with self.assertRaises(cap.Invalid):self.call('map.query',dict(req,layerIds=['not-authorized']))
        self.s['platform']['apps'][0]['listed']=False
        with self.assertRaises(cap.Invalid):self.call('map.query',req)
    def test_map_area_policy_only_applies_after_publication(self):
        req=dict(sceneId='scene_cropland',mode='nearby',x=111.7,y=40.8,radius=1000)
        settings=self.p['settings'];r=self.call('policy.save',dict(rev=settings['rev'],values=dict(settings,maxAreaHa=1)))
        self.assertGreater(self.call('map.query',req)['areaHa'],1)
        self.call('policy.publish',dict(rev=r['rev']))
        with self.assertRaises(cap.Invalid):self.call('map.query',req)

    def test_query_geometry_matches_requested_point_buffer_and_box(self):
        scene=self.s['platform']['scenes'][0]['id']
        point=self.call('map.query',dict(sceneId=scene,mode='penetrate',x=111.7,y=40.8))
        self.assertEqual(point['queryGeometry']['type'],'Point')
        self.assertEqual(list(point['queryGeometry']['coordinates']),[111.7,40.8])
        nearby=self.call('map.query',dict(sceneId=scene,mode='nearby',x=111.7,y=40.8,radius=1000))
        self.assertEqual(nearby['queryGeometry']['type'],'Polygon')
        self.assertGreater(nearby['areaHa'],300)
        self.assertLess(nearby['areaHa'],320)
        geom={'type':'Polygon','coordinates':[[[111.69,40.79],[111.71,40.79],[111.71,40.81],[111.69,40.81],[111.69,40.79]]]}
        box=self.call('map.query',dict(sceneId=scene,mode='box',geometry=geom))
        self.assertEqual(box['history']['mode'],'box')
        self.assertEqual(json.loads(json.dumps(box['queryGeometry'])),geom)

    def test_publish_versions_restore_draft_without_changing_live(self):
        r=self.content();r=self.change('publish','contents',r)
        r=self.save('contents',dict(r,name='第二版'),r);r=self.change('publish','contents',r)
        versions=self.call('versions',dict(entity='contents',id=r['id']))['versions']
        self.assertEqual([v['version'] for v in versions],[1,2])
        self.assertNotIn('versions',versions[1]['snapshot'])
        restored=self.call('restore',dict(entity='contents',id=r['id'],rev=r['rev'],version=1))
        self.assertEqual(restored['name'],'验收Banner');self.assertEqual(restored['published']['name'],'第二版')
        r=self.change('publish','contents',restored);self.assertEqual(r['version'],3);self.assertEqual(r['published']['name'],'验收Banner')
        with self.assertRaises(cap.Invalid):self.call('restore',dict(entity='contents',id=r['id'],rev=1,version=1))
        with self.assertRaises(cap.Invalid):self.call('versions',dict(entity='contents',id=r['id']),self.u)
    def test_preview_does_not_publish_and_respects_selected_identity(self):
        r=self.notice(audience='平台管理员')
        preview=self.call('preview',dict(entity='announcements',id=r['id'],rev=r['rev'],userId='u1'))
        self.assertFalse(preview['visible']);self.assertIsNone(preview['published'])
        self.assertFalse(ig.messages(self.s,self.u))
        with self.assertRaises(cap.Invalid):self.call('preview',dict(entity='announcements',id=r['id'],rev=r['rev']),self.u)
    def test_target_department_and_tenant_are_intersected_and_rechecked(self):
        tenant=self.tenant();self.member(tenant,self.u,['read'])
        r=self.notice(departments=[self.u['department']],tenantIds=[tenant['id']]);self.change('publish','announcements',r)
        self.assertEqual(len(ig.messages(self.s,self.u)),1);self.assertEqual(ig.messages(self.s,self.other),[])
        self.u['department']='其他部门';self.assertEqual(ig.messages(self.s,self.u),[])
        self.u['department']=r['departments'][0]
        member=next(x for x in self.p['members'] if x['userId']=='u1')
        self.call('tenant.member',dict(tenantId=tenant['id'],rev=member['rev'],values=dict(userId='u1',permissions=[])))
        self.assertEqual(ig.messages(self.s,self.u),[])
        with self.assertRaises(cap.Invalid):self.call('message.read',dict(id=r['id']+':1'),self.u)
    def test_uploaded_raster_persists_and_unsafe_media_rejected(self):
        image='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1UAAAAASUVORK5CYII='
        r=self.save('contents',dict(name='上传图片',kind='banner',image=image));r=self.change('publish','contents',r)
        self.assertEqual(next(x for x in ig.bootstrap(self.s,self.u,'front')['contents'] if x['id']==r['id'])['image'],image)
        for invalid in ['data:image/svg+xml;base64,PHN2Zz4=','data:image/png;base64,aGVsbG8=','javascript:alert(1)']:
            with self.assertRaises(cap.Invalid):self.save('contents',dict(name='拒绝素材',image=invalid))
    def test_policy_restore_requires_separate_publication(self):
        old=self.p['settings'];r=self.call('settings.save',dict(rev=old['rev'],values=dict(old,roleAreaLimits={self.u['role']:1},bannerAutoplay=True,bannerSeconds=5)))
        self.call('policy.publish',dict(rev=r['rev']))
        req=dict(sceneId='scene_cropland',mode='nearby',x=111.7,y=40.8,radius=1000)
        with self.assertRaises(cap.Invalid):self.call('map.query',req,self.u)
        self.assertGreater(self.call('map.query',req)['areaHa'],1)
        current=self.p['settings'];r=self.call('restore',dict(entity='settings',rev=current['rev'],version=1))
        self.assertEqual(r['roleAreaLimits'],{});self.assertEqual(r['published']['roleAreaLimits'][self.u['role']],1)
        self.call('policy.publish',dict(rev=r['rev']))
        self.assertEqual(self.p['settings']['published']['roleAreaLimits'],{})
        with self.assertRaises(cap.Invalid):self.call('settings.save',dict(rev=self.p['settings']['rev'],values=dict(self.p['settings'],roleAreaLimits={self.u['role']:10000001})))
    def test_object_navigation_revalidates_channel_and_returns_exact_action(self):
        row=next(x for x in ig.catalog(self.s,self.u) if x['id'].startswith('knowledge:'))
        result=self.call('open',dict(id=row['id']),self.u)
        self.assertEqual(result,dict(action='portalKnowledge',id=row['id'].split(':')[1]))
        agent=next(x for x in ig.catalog(self.s,self.u) if x['id'].startswith('agent:'))
        self.assertEqual(self.call('open',dict(id=agent['id']),self.u)['action'],'agentDetail')
        raw=cap.find(self.s['agents'],agent['id'].split(':')[1]);raw['status']='已停用'
        with self.assertRaises(cap.Invalid):self.call('open',dict(id=agent['id']),self.u)
    def test_monitor_filters_result_types_and_chronological_weeks(self):
        self.p['events']=[dict(id='e1',kind='open',at='2026-01-05T10:00:00',department='甲部门',userId='u1',target='resource:r1',name='数据一'),dict(id='e2',kind='open',at='2026-01-01T10:00:00',department='乙部门',userId='u2',target='resource:r1',name='数据一')]
        import portal_management as pm
        pm.migrate(self.s)['events']=[dict(id=str(i),kind='tool',at='2026-01-05T10:00:00',department='甲部门',userId='u1',name='测试工具',status=status) for i,status in enumerate(['成功','失败','打开入口'])]
        result=self.call('monitor',dict(start='2026-01-02',end='2026-01-06',department='甲部门',period='week'))
        self.assertEqual(result['opens'],1);self.assertEqual(result['toolSuccess'],1);self.assertEqual(result['externalOpens'],1);self.assertEqual(result['days'][0]['name'],'2026-W02')
        result=self.call('monitor',dict(eventType='success'));self.assertEqual(result['tools'],1);self.assertEqual(result['opens'],0)
        with self.assertRaises(cap.Invalid):self.call('monitor',dict(start='2026-02-01',end='2026-01-01'))

if __name__=='__main__':unittest.main()

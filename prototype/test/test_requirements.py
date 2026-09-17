"""Detailed prose regressions. Each test runs on isolated in-memory fixtures."""
import base64
import json
import unittest
from copy import deepcopy
from seed import seed
from platform_seed import migrate, record
import platform_domain as d
import platform_features as f
from capabilities import Invalid


class DetailedRequirements(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.p=migrate(self.s)
        self.admin=d.find(self.s['users'],'admin');self.user=d.find(self.s['users'],'u1')

    def call(self,action,payload=None,user=None):
        return d.execute(self.s,user or self.admin,'platform.'+action,payload or {})

    def save(self,entity,id,values):
        row=d.find(self.p[entity],id)
        return self.call('save',dict(entity=entity,id=id,rev=row['rev'] if row else 0,values=values))

    def transition(self,entity,id,command,**values):
        return self.call('transition',dict(entity=entity,id=id,rev=d.find(self.p[entity],id)['rev'],command=command,**values))

    def case(self,key='new',**values):
        return self.call('caseCreate',dict(modelId='bm_project',requestId=key,region='全区',formData=dict(projectName='共同项目',area=20,purpose='公共设施'),**values),self.user)

    def test_task_receivers_include_handler_and_applicant(self):
        case=self.case()
        targets={(e['type'],e['recipientId']) for e in self.p['events'] if e['aggregateId']==case['id']}
        self.assertIn(('workflow.task.created','reviewer'),targets)
        self.assertIn(('workflow.progress.created','u1'),targets)
        self.call('caseAction',dict(id=case['id'],rev=case['rev'],command='complete',requestId='complete1',note='初审通过'),d.find(self.s['users'],'reviewer'))
        self.assertTrue(any(e['type']=='workflow.task.complete' and e['recipientId']=='admin' for e in self.p['events']))

    def test_proxy_and_assist_are_in_todo_and_expired_proxy_is_not(self):
        case=self.case()
        self.p['delegations'].append(record('proxy','代理',ownerId='reviewer',agentId='u2',modelId='bm_project',enabled=True,validFrom='2020-01-01',validUntil='2099-01-01'))
        u2=d.find(self.s['users'],'u2');case['region']='呼和浩特市'
        data=d.bootstrap(self.s,u2)['cases'];self.assertTrue(next(c for c in data if c['id']==case['id'])['isTodo'])
        self.p['delegations'][0]['validUntil']='2020-01-02'
        self.assertFalse(f.todo(self.p,u2,case))
        case['subtasks'].append(dict(id='assist',userId='u2',status='待办'))
        self.assertTrue(f.todo(self.p,u2,case))

    def test_message_priority_and_overlapping_subscriptions(self):
        self.p['subscriptions'].append(record('wildcard','全部动态',eventType='*',recipientId='u1',channelId='ch_inbox',enabled=True))
        d.emit(self.p,self.admin,'app.test',record('ordinary','普通',region='全区'))
        self.p['events'][-1]['priority']=9
        d.emit(self.p,self.admin,'app.test',record('urgent','紧急',region='全区'))
        self.p['events'][-1]['priority']=1
        self.assertEqual(len(self.p['deliveries']),2)
        d.dispatch(self.s)
        self.assertEqual(self.p['notifications'][0]['title'],'紧急')
        d.dispatch(self.s);d.dispatch(self.s)
        self.assertEqual(len(self.p['notifications']),2)
        self.assertTrue(all(n['target']=='/front/messages' for n in self.p['notifications']))

    def test_subscription_change_revokes_queued_message(self):
        self.call('testEvent')
        self.save('subscriptions','sub_apps',{'eventType':'resource.*'})
        d.dispatch(self.s)
        self.assertEqual(self.p['deliveries'][0]['status'],'已取消')
        self.assertEqual(self.p['notifications'],[])

    def test_queue_limit_preserves_overflow_for_operator_retry(self):
        self.save('channels','ch_inbox',{'queueLimit':1})
        self.call('testEvent');self.call('testEvent')
        self.assertEqual([r['status'] for r in self.p['deliveries']],['待投递','失败队列'])
        d.dispatch(self.s);self.call('retry',{'id':self.p['deliveries'][1]['id']})
        self.assertEqual(len(self.p['notifications']),2)

    def test_scene_crs_layout_and_preview(self):
        config=deepcopy(self.p['scenes'][0]['config'])
        config['panelOrder']=['map','layers','map']
        with self.assertRaises(Invalid):self.call('sceneValidate',{'config':config})
        config=deepcopy(self.p['scenes'][0]['config'])
        d.find(self.s['resources'],'r_scene_demo')['published']['crs']='EPSG:3857'
        with self.assertRaises(Invalid):self.call('sceneValidate',{'config':config})
        d.find(self.s['resources'],'r_scene_demo')['published']['crs']='CGCS2000'
        preview=self.call('sceneRuntime',{'id':'st_cropland','template':True,'preview':True})
        self.assertTrue(preview['config']['layers'][0]['features'])
        self.assertTrue(preview['config']['widgets'])
        with self.assertRaises(Invalid):self.call('sceneRuntime',{'id':'st_cropland','template':True,'preview':True},self.user)

    def test_unavailable_engine_cannot_be_submitted(self):
        config=deepcopy(self.p['scenes'][0]['config']);config['engine']='external-3d';config['widgets']=[]
        self.save('scenes','scene_cropland',{'config':config})
        self.save('apps','app_cropland',{'name':'三维不可运行'})
        with self.assertRaises(Invalid):self.transition('apps','app_cropland','submit')

    def test_stop_target_delists_app_but_keeps_history(self):
        self.transition('scenes','scene_cropland','disable')
        self.assertFalse(d.find(self.p['apps'],'app_cropland')['listed'])
        self.assertIsNotNone(d.find(self.p['apps'],'app_cropland')['published'])
        with self.assertRaises(Invalid):self.call('appOpen',{'id':'app_cropland'},self.user)

    def test_project_reuse_and_scope(self):
        a=self.case(projectType='建设用地');b=self.case('second',projectId=a['projectId'])
        self.assertEqual(a['projectId'],b['projectId'])
        self.assertEqual(d.find(self.p['projects'],a['projectId'])['type'],'建设用地')
        with self.assertRaises(Invalid):self.call('caseCreate',dict(modelId='bm_project',requestId='bad',projectId=a['projectId'],region='呼和浩特市',formData=dict(projectName='越权',area=1,purpose='测试')),d.find(self.s['users'],'u2'))

    def test_compliance_revision_permissions_and_audit(self):
        c=self.case()
        with self.assertRaises(Invalid):self.call('compliance',dict(id=c['id'],rev=c['rev'],compliance='合规',note='申请人自审'),self.user)
        rev=c['rev'];self.call('compliance',dict(id=c['id'],rev=rev,compliance='不合规',note='缺少法定材料'))
        self.assertEqual(c['compliance'],'不合规');self.assertEqual(c['history'][-1]['action'],'compliance')
        with self.assertRaises(Invalid):self.call('compliance',dict(id=c['id'],rev=rev,compliance='合规',note='旧页面'))

    def test_supervision_create_resolve(self):
        c=self.case();r=self.call('supervise',{'caseId':c['id'],'note':'请补充审查结果'})
        self.assertEqual(r['status'],'督办中')
        self.call('supervise',{'caseId':c['id'],'id':r['id'],'rev':r['rev'],'note':'材料已核验'})
        self.assertEqual(r['status'],'已解除')

    def test_rules_accept_form_fields_and_typed_libraries(self):
        expression="purpose == '公共设施' and project_area < area_threshold"
        self.save('businessAssets','',dict(name='通用业务校验',kind='业务规则',code='valid_general',value=expression,region='全区'))
        result=self.call('ruleTrial',{'expression':expression,'context':{'purpose':'公共设施','area':20}})
        self.assertTrue(result['passed']);self.assertEqual(result['context']['project_area'],20)
        self.save('businessAssets','ba_param',{'value':'10'})
        self.assertFalse(self.call('ruleTrial',{'expression':expression,'context':{'purpose':'公共设施','area':20}})['passed'])
        with self.assertRaises(Invalid):self.call('ruleTrial',{'expression':'__import__("os")','context':{}})

    def test_variable_cycle_and_invalid_reference(self):
        self.save('businessAssets','ba_var',{'value':'project_area'})
        with self.assertRaises(Invalid):self.call('ruleTrial',{'expression':'project_area > 0','context':{}})
        with self.assertRaises(Invalid):self.save('businessAssets','',dict(name='非法引用',kind='通用规则',code='missing',value='unknown > 0'))

    def test_app_credentials_created_once_and_never_persist_plaintext(self):
        r=self.save('authClients','',dict(name='新客户端',appId='app_project',group='用途管制',mfa=False,enabled=True,protocol='本地演示会话',entry='#/front/home'))
        self.assertTrue(r['appSecret']);self.assertNotIn(r['appSecret'],json.dumps(self.s))
        self.assertNotIn('secretHash',json.dumps(d.bootstrap(self.s,self.admin,'admin')))
        edited=self.save('authClients',r['id'],{'name':'改名'})
        self.assertNotIn('appSecret',edited)

    def test_registration_creates_only_scoped_demo_user_and_is_idempotent(self):
        payload=dict(kind='自然人',method='线上自主注册',name='演示测试',subjectCode='DEMO-AUDIT-1',outcome='通过')
        n=len(self.s['users']);r=self.call('registration',payload,self.user)
        self.assertEqual(len(self.s['users']),n+1)
        user=d.find(self.s['users'],r['userId']);self.assertEqual(user['role'],'业务用户')
        self.assertEqual(self.call('registration',payload,self.user)['userId'],r['userId'])
        self.assertEqual(len(self.s['users']),n+1)

    def test_gateway_timeout_fallback_trace(self):
        self.save('upstreams','up_a',{'latency':2000})
        r=self.call('gatewayTrial',{'id':'gw_resources','userId':'u1','question':'耕地'})
        self.assertEqual(r['statusCode'],200);self.assertEqual([a['statusCode'] for a in r['attempts']],[504,200])

    def test_images_require_raster_content_and_size(self):
        good='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\nminimal').decode()
        self.save('sceneTemplates','st_cropland',{'logo':good})
        for bad in ['data:image/svg+xml;base64,PHN2Zz4=', 'data:image/png;base64,ZmFrZQ==', 'data:image/png;base64,'+'A'*400000]:
            with self.assertRaises(Invalid):self.save('sceneTemplates','st_cropland',{'logo':bad})

    def test_dashboard_owned_settings_and_help_persistence(self):
        self.call('dashboard',{'modules':['apps','todo']},self.user)
        self.assertEqual(d.bootstrap(self.s,self.user)['dashboards'][0]['modules'],['apps','todo'])
        self.assertEqual(d.bootstrap(self.s,d.find(self.s['users'],'u2'))['dashboards'],[])
        self.assertEqual(len(self.p['helpDocs']),6)
        self.save('helpDocs','help_faq',{'body':'已更新的使用帮助'})
        self.assertEqual(d.find(d.bootstrap(self.s,self.user)['helpDocs'],'help_faq')['body'],'已更新的使用帮助')

    def setup_pull(self):
        channel=self.save('channels','',dict(name='消费测试',type='拉取队列',enabled=True,concurrency=8,queueLimit=20,failMode=False))
        self.save('subscriptions','sub_apps',dict(channelId=channel['id']))
        self.call('testEvent')
        return channel

    def test_pull_ack_idempotent_and_conflicting_ack_rejected(self):
        channel=self.setup_pull();batch=self.call('pull',{'channelId':channel['id']},self.user)
        item=batch['items'][0];delivery=d.find(self.p['deliveries'],item['deliveryId'])
        self.assertEqual(delivery['status'],'消费中')
        payload=dict(deliveryId=item['deliveryId'],receiptToken=item['receiptToken'],outcome='成功')
        self.call('ack',payload,self.user);self.assertEqual(delivery['status'],'已处理')
        self.assertTrue(self.call('ack',payload,self.user)['duplicate'])
        with self.assertRaises(Invalid):self.call('ack',{**payload,'outcome':'失败'},self.user)
        with self.assertRaises(Invalid):self.call('ack',payload,d.find(self.s['users'],'u2'))

    def test_expired_consumer_lease_cannot_ack_and_enters_retry(self):
        channel=self.setup_pull();item=self.call('pull',{'channelId':channel['id']},self.user)['items'][0]
        delivery=d.find(self.p['deliveries'],item['deliveryId']);delivery['leaseUntil']='2020-01-01T00:00:00'
        with self.assertRaises(Invalid):self.call('ack',dict(deliveryId=item['deliveryId'],receiptToken=item['receiptToken'],outcome='成功'),self.user)
        d.dispatch(self.s);self.assertEqual(delivery['status'],'等待重试')

    def test_event_schema_defaults_filters_dedupe_and_summary(self):
        source=self.save('eventSources','',dict(name='地灾源',type='geology.*',priority=1,enabled=True,sourceSystem='geology',schema={'level':'number','name':'string'},defaults={'name':'默认事件名'},allowedRoles=['业务用户']))
        channel=self.save('channels','',dict(name='外部消费队列',type='拉取队列',concurrency=8,enabled=True,failMode=False))
        self.save('subscriptions','',dict(name='橙色预警',eventType='geology.*',topic='地灾',tags=['橙色'],sourceSystem='geology',recipientId='u1',channelId=channel['id'],enabled=True,rank=1,contentMode='摘要'))
        payload=dict(sourceId=source['id'],eventId='event1',eventType='geology.alert',topic='地灾',tags=['橙色'],data={'level':2})
        event=self.call('ingestEvent',payload);self.assertEqual(event['data']['name'],'默认事件名')
        self.call('ingestEvent',payload)
        self.assertEqual(len(self.p['deliveries']),1)
        batch=self.call('pull',{'channelId':channel['id']},self.user)
        self.assertNotIn('data',batch['items'][0]['event'])
        with self.assertRaises(Invalid):self.call('ingestEvent',{**payload,'eventId':'invalid','data':{'level':'bad'}})

    def test_event_acl_and_current_subscription_rechecked_at_pull(self):
        channel=self.setup_pull();d.dispatch(self.s)
        self.save('subscriptions','sub_apps',{'enabled':False})
        self.assertEqual(self.call('pull',{'channelId':channel['id']},self.user)['items'],[])
        self.assertEqual(self.p['deliveries'][0]['status'],'已取消')

    def test_channel_monitoring_uses_all_delivery_records(self):
        self.setup_pull();d.dispatch(self.s)
        stats=d.bootstrap(self.s,self.admin,'admin')['channelStats']
        self.assertEqual(sum(c['backlog'] for c in stats),1)

    def test_child_unit_delegation_and_scope_boundaries(self):
        manager=d.find(self.s['users'],'org_admin')
        child=self.call('save',dict(entity='organizations',values=dict(name='下级科室',parentId='org_geo',region='呼和浩特市')),manager)
        user=self.call('userSave',{'values':dict(name='下级管理员',orgId=child['id'],region='呼和浩特市',role='单位管理员',enabled=True)},manager)
        self.assertEqual(user['role'],'单位管理员')
        with self.assertRaises(Invalid):self.call('userSave',{'values':dict(name='越级',orgId='org_hall',region='全区',role='单位管理员',enabled=True)},manager)
        with self.assertRaises(Invalid):self.call('userSave',{'values':dict(name='同级',orgId='org_geo',region='呼和浩特市',role='单位管理员',enabled=True)},manager)

    def test_generated_client_secret_verifies_and_rotation_revokes_old(self):
        client=self.save('authClients','',dict(name='接口接入',appId='app_project',group='业务组',mfa=False,enabled=True,protocol='本地演示会话',entry='#/front/home'))
        payload={'appKey':client['key'],'appSecret':client['appSecret']}
        self.assertTrue(self.call('clientVerify',payload)['ok'])
        self.call('rotateSecret',{'id':client['id']})
        with self.assertRaises(Invalid):self.call('clientVerify',payload)

    def test_assignee_cannot_bypass_region_scope(self):
        case=self.case();case['region']='包头市';case['assigneeId']='u2'
        with self.assertRaises(Invalid):self.call('caseDetail',{'id':case['id']},d.find(self.s['users'],'u2'))

    def test_flow_manager_can_edit_knowledge_but_not_other_intelligence_assets(self):
        import server
        manager=d.find(self.s['users'],'flow_manager');knowledge=self.s['knowledge'][0]
        updated=server.execute(self.s,manager,'save',dict(entity='knowledge',id=knowledge['id'],rev=knowledge['rev'],values={'body':'政策文件正文补充，供业务审查引用。'}))
        self.assertIn('政策文件正文补充',updated['body'])
        with self.assertRaises(Invalid):server.execute(self.s,manager,'save',dict(entity='resources',id='r1',rev=1,values={'name':'越权修改'}))
        manager['region']='呼和浩特市'
        with self.assertRaises(Invalid):server.execute(self.s,manager,'save',dict(entity='knowledge',id=updated['id'],rev=updated['rev'],values={'body':'不能修改全区文件'}))


if __name__=='__main__':unittest.main()

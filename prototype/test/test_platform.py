"""Behavioral application/platform tests; isolated fixtures and SQLite only."""
import json
import sqlite3
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from seed import seed
from platform_seed import migrate
import platform_domain as domain
import platform_store as store
from capabilities import Invalid


class PlatformFlows(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.p=migrate(self.s)
        self.admin=self.user('admin');self.u=self.user('u1');self.other=self.user('u2')
    def user(self,key):return domain.find(self.s['users'],key)
    def call(self,action,values=None,user=None):return domain.execute(self.s,user or self.admin,'platform.'+action,values or {})
    def save(self,e,id,values,user=None):
        r=domain.find(self.p[e],id) if id else None
        return self.call('save',dict(entity=e,id=id,rev=r['rev'] if r else 0,values=values),user)
    def trans(self,e,id,command,**extra):
        r=domain.find(self.p[e],id)
        return self.call('transition',dict(entity=e,id=id,rev=r['rev'],command=command,**extra))
    def create(self,key='new',user=None):
        return self.call('caseCreate',dict(modelId='bm_project',requestId=key,region='呼和浩特市',formData={'projectName':'测试项目','area':20,'purpose':'验证版本与状态流转'}),user or self.u)
    def handle(self,c,command,key='key',user=None,**values):return self.call('caseAction',dict(id=c['id'],rev=c['rev'],command=command,note='测试办理意见',requestId=key,**values),user)

    def test_store_roundtrip_preserves_empty_collections_and_legacy(self):
        with sqlite3.connect(':memory:') as c:
            c.execute('CREATE TABLE state(id INTEGER PRIMARY KEY, body TEXT)');c.execute('INSERT INTO state VALUES(1,?)',(json.dumps(seed()),));store.initialize(c);store.save(c,self.s)
            self.assertGreater(c.execute('SELECT count(*) FROM platform_records').fetchone()[0],20)
            loaded=json.loads(c.execute('SELECT body FROM state').fetchone()[0]);self.assertNotIn('platform',loaded)
            store.load(c,loaded);migrate(loaded);self.assertEqual(loaded['platform']['deliveries'],[])
            self.assertEqual(loaded['resources'],self.s['resources']);self.assertEqual(loaded['applications'],self.s['applications'])
            store.save(c,loaded);self.assertEqual(len(loaded['platform']['scenes']),1)

    def test_migration_preserves_original_assets(self):
        original=deepcopy(self.s);migrate(self.s);migrate(self.s)
        self.assertEqual(self.s,original)

    def test_template_copy_is_independent_and_deletion_checks_refs(self):
        copy=self.trans('sceneTemplates','st_cropland','copy')
        copy['config']['layers'][0]['visible']=False
        self.assertTrue(self.p['sceneTemplates'][0]['config']['layers'][0]['visible'])
        with self.assertRaises(Invalid):self.trans('sceneTemplates','st_cropland','delete')
        with self.assertRaises(Invalid):self.trans('widgetGroups','wg_common','delete')

    def test_scene_rejects_crs_and_default_base(self):
        config=deepcopy(self.p['scenes'][0]['config']);config['basemaps'][0]['crs']='EPSG:3857'
        with self.assertRaises(Invalid):self.call('sceneValidate',{'config':config})
        config=deepcopy(self.p['scenes'][0]['config']);config['defaultBase']='missing'
        with self.assertRaises(Invalid):self.call('sceneValidate',{'config':config})

    def test_scene_runtime_enforces_layer_grants_and_stopped_widget(self):
        runtime=self.call('sceneRuntime',{'id':'scene_cropland'},self.u)
        restricted=next(l for l in runtime['config']['layers'] if l['resourceId']=='r11')
        self.assertEqual(restricted['features'],[])
        self.trans('widgets','w_query','disable')
        runtime=self.call('sceneRuntime',{'id':'scene_cropland'},self.u)
        self.assertIn('w_query',runtime['disabledWidgets'])

    def test_control_versions_remain_pinned(self):
        self.save('widgets','w_query',{'name':'新版查询控件'});self.trans('widgets','w_query','publish')
        runtime=self.call('sceneRuntime',{'id':'scene_cropland'},self.u)
        self.assertEqual(next(w for w in runtime['config']['widgets'] if w['id']=='w_query')['name'],'属性查询')

    def test_app_review_snapshot_and_delist(self):
        a=self.p['apps'][0];self.save('apps',a['id'],{'name':'新版本应用'})
        public=domain.bootstrap(self.s,self.admin,'front')['apps'][0]
        self.assertEqual(public['name'],'耕地保护专题')
        self.trans('apps',a['id'],'submit');self.trans('apps',a['id'],'approve',note='依赖检查通过')
        self.assertEqual(domain.bootstrap(self.s,self.u)['apps'][0]['name'],'新版本应用')
        self.trans('apps',a['id'],'disable',note='暂时停止服务')
        with self.assertRaises(Invalid):self.call('sceneRuntime',{'id':'scene_cropland'},self.u)

    def test_unprivileged_app_writes_are_rejected(self):
        with self.assertRaises(Invalid):self.save('apps','app_cropland',{'name':'越权'},self.u)
        a=self.p['apps'][0];self.save('apps',a['id'],{'name':'提交新版'});self.trans('apps',a['id'],'submit')
        with self.assertRaises(Invalid):self.call('transition',dict(entity='apps',id=a['id'],rev=domain.find(self.p['apps'],a['id'])['rev'],command='approve',note='无权审核'),self.user('app_manager'))

    def test_case_validation_and_idempotency(self):
        c=self.create();self.assertEqual(c['id'],self.create()['id'])
        with self.assertRaises(Invalid):self.call('caseCreate',dict(modelId='bm_project',requestId='bad',region='全区',formData={'projectName':'坏值','area':-1,'purpose':'验证'}),self.u)
        with self.assertRaises(Invalid):self.call('caseCreate',dict(modelId='bm_project',requestId='wide',region='全区',formData={'projectName':'越权','area':1,'purpose':'验证'}),self.other)

    def test_flow_versions_drive_new_instances_only(self):
        c=self.create();self.save('workflows','wf_review',{'nodes':[{'id':'only','name':'单节点审查','assigneeId':'reviewer','hours':2}]})
        with self.assertRaises(Invalid):self.trans('workflows','wf_review','publish')
        self.trans('workflows','wf_review','deploy');self.trans('workflows','wf_review','publish')
        other=self.create('second');self.assertEqual(len(other['workflow']['nodes']),1);self.assertEqual(len(c['workflow']['nodes']),2)
        self.handle(other,'complete',user=self.user('reviewer'));self.assertEqual(other['status'],'已办结')

    def test_task_complete_conflict_and_repeated_command(self):
        c=self.create();oldrev=c['rev'];result=self.handle(c,'complete',user=self.user('reviewer'))
        repeated=self.call('caseAction',dict(id=c['id'],rev=oldrev,command='complete',requestId='key',note='重复'),self.user('reviewer'))
        self.assertEqual(result,repeated);self.assertEqual(c['nodeIndex'],1)
        with self.assertRaises(Invalid):self.call('caseAction',dict(id=c['id'],rev=oldrev,command='complete',requestId='new',note='旧页面'))

    def test_assist_delegate_suspend_resume_and_return(self):
        c=self.create();self.handle(c,'assist','a',userId='u2')
        with self.assertRaises(Invalid):self.handle(c,'complete','b')
        self.handle(c,'assistComplete','c',self.other,subtaskId=c['subtasks'][0]['id'])
        self.handle(c,'delegate','d',userId='u2');self.assertEqual(c['assigneeId'],'u2')
        self.handle(c,'suspend','e')
        with self.assertRaises(Invalid):self.handle(c,'complete','f',self.other)
        self.handle(c,'resume','g');self.handle(c,'complete','h',self.other)
        self.handle(c,'return','i');self.assertEqual(c['nodeIndex'],0)

    def test_withdraw_and_void_are_terminal(self):
        c=self.create();self.handle(c,'withdraw',user=self.u);self.assertEqual(c['status'],'已撤回')
        with self.assertRaises(Invalid):self.handle(c,'complete','after')
        other=self.create('second');self.handle(other,'void');self.assertEqual(other['status'],'已作废')

    def test_work_calendar_and_rules(self):
        end=domain.deadline(self.p,1,'ba_hours',datetime(2026,9,18,17,30))
        self.assertEqual(end,'2026-09-21T09:30:00')
        self.assertTrue(domain.safe_rule('area > 0 and area < 100',{'area':20}))
        with self.assertRaises(Invalid):domain.safe_rule('__import__("os")',{})

    def test_org_manager_cannot_expand_scope_or_elevate_role(self):
        u=self.user('org_admin')
        with self.assertRaises(Invalid):self.call('userSave',{'id':'u2','rev':self.other['rev'],'values':{'region':'全区'}},u)
        with self.assertRaises(Invalid):self.call('userSave',{'id':'u2','rev':self.other['rev'],'values':{'role':'平台管理员'}},u)
        r=self.call('userSave',{'id':'u2','rev':self.other['rev'],'values':{'name':'授权范围内编辑'}},u)
        self.assertEqual(r['name'],'授权范围内编辑')

    def test_message_failure_retry_dedup_and_revocation(self):
        self.save('subscriptions','sub_apps',{'channelId':'ch_webhook'});self.call('testEvent');domain.dispatch(self.s)
        d=self.p['deliveries'][0];self.assertEqual(d['status'],'等待重试')
        self.save('channels','ch_webhook',{'failMode':False});self.call('retry',{'id':d['id']});self.assertEqual(d['status'],'已送达')
        self.save('subscriptions','sub_apps',{'channelId':'ch_inbox'});self.call('testEvent');domain.dispatch(self.s);domain.dispatch(self.s)
        self.assertEqual(len(self.p['notifications']),1)
        with self.assertRaises(Invalid):self.call('notifyRead',{'id':self.p['notifications'][0]['id']},self.other)

    def test_gateway_routes_limits_and_fallback(self):
        first=self.call('gatewayTrial',{'id':'gw_resources','userId':'u1','question':'耕地'})
        self.assertEqual(first['statusCode'],200);self.assertTrue(first['result'])
        self.save('upstreams','up_a',{'enabled':False})
        second=self.call('gatewayTrial',{'id':'gw_resources','userId':'u1'});self.assertEqual(second['upstream'],'本地资源实例 B')
        self.save('routes','gw_resources',{'limit':1})
        self.assertEqual(self.call('gatewayTrial',{'id':'gw_resources','userId':'u1'})['statusCode'],429)

    def test_mfa_and_secret_never_in_bootstrap(self):
        self.save('authClients','client_portal',{'mfa':True})
        self.assertFalse(self.call('login',{'userId':'u1','code':'bad'})['ok'])
        self.assertTrue(self.call('login',{'userId':'u1','code':'246810'})['ok'])
        secret=self.call('rotateSecret',{'id':'client_portal'})['appSecret']
        self.assertNotIn(secret,json.dumps(self.s));self.assertNotIn('secretHash',json.dumps(domain.bootstrap(self.s,self.admin,'admin')))

    def test_context_cannot_reference_inaccessible_scene_case_or_region(self):
        valid=domain.validate_context(self.s,self.u,{'sceneId':'scene_cropland','region':'包头市'})
        self.assertEqual(valid['sceneId'],'scene_cropland')
        with self.assertRaises(Invalid):domain.validate_context(self.s,self.other,{'region':'包头市'})
        self.trans('apps','app_cropland','disable',note='停用')
        with self.assertRaises(Invalid):domain.validate_context(self.s,self.u,{'sceneId':'scene_cropland'})

    def test_flow_export_import_and_external_widget_boundary(self):
        exported=self.call('flowExport',{'id':'wf_review'});new=self.call('flowImport',{'data':exported});self.assertNotEqual(new['id'],'wf_review');self.assertEqual(new['status'],'草稿')
        w=self.save('widgets','',dict(name='外部控件',code='external',groupId='wg_common',engine='local-2d',terminal='桌面',entry='package:demo.json'))
        with self.assertRaises(Invalid):self.trans('widgets',w['id'],'publish')


if __name__=='__main__':unittest.main()

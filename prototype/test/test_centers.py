import unittest
import json
import tempfile
import sqlite3
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import centers
import capabilities as cap
import portal_management as pm
import platform_store
from seed import seed
from server import execute, bootstrap, user_for

class CenterWorkflows(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin');self.c=centers.migrate(self.s)
    def call(self,op,p=None,user=None):return execute(self.s,user or self.admin,'centers.'+op,p or {})
    def save(self,entity,values,old=None):return self.call('save',dict(entity=entity,values=values,**({'id':old['id'],'rev':old['rev']} if old else {})))
    def ingestion(self,bad=False):
        return self.save('ingestions',dict(name='归集测试',sourceId='source-local',region='全区',category='耕地',layer='基础层',mode='在线填报',standardId='standard-basic',ruleIds=['rule-id','rule-name','rule-area'],dataRows='id,name,region,area\n1,地块甲,呼和浩特市,'+('-3' if bad else '12.5')+'\n2,地块乙,包头市,4'))
    def change(self,op,entity,row,**payload):
        current=centers.find(self.c[entity],row['id']);return self.call(op,dict(id=row['id'],rev=current['rev'],**payload))
    def approve(self,rid='r1',method=''):
        a=execute(self.s,self.user,'apply',dict(resourceIds=[rid],purpose='使用中心功能进行验证',method=method,validUntil=(date.today()+timedelta(days=30)).isoformat()))
        execute(self.s,self.admin,'decide',dict(id=a['id'],rev=a['rev'],resourceId=rid,decision='已通过',note='符合业务测试使用要求'))
        return self.s['grants'][-1],self.c['deliveries'][-1]
    def test_governance_remediation_registration_publication_and_query(self):
        r=self.ingestion(True);self.change('ingestion.submit','ingestions',r)
        report=self.change('ingestion.check','ingestions',r);self.assertFalse(report['passed']);self.assertEqual(report['issues'][0]['field'],'area')
        with self.assertRaises(cap.Invalid):self.change('ingestion.register','ingestions',r)
        issue=self.call('quality.issue',dict(id=report['id'],assigneeId='admin'))
        self.change('issue.feedback','issues',issue,note='修正面积负值并核对台账',dataRows=r['dataRows'].replace('-3','3'),evidence='台账校核记录')
        self.change('issue.review','issues',issue);self.assertEqual(self.c['issues'][0]['status'],'已办结')
        result=self.change('ingestion.register','ingestions',r);resource=cap.find(self.s['resources'],result['resourceId'])
        self.assertEqual(resource['status'],'草稿');self.assertIsNone(cap.published(resource));self.assertEqual(len(self.c['datasets']),1)
        with self.assertRaises(cap.Invalid):self.change('ingestion.register','ingestions',r)
        service=self.save('publications',dict(name='数据查询服务',resourceId=resource['id'],protocol='本地数据接口'))
        service=self.change('publication.publish','publications',service)
        self.assertIsNotNone(cap.published(resource))
        with self.assertRaises(cap.Invalid):self.call('service.query',dict(id=service['id']),self.user)
        self.approve(resource['id'])
        result=self.call('service.query',dict(id=service['id'],region='呼和浩特市',fields='id,name'),self.user)
        self.assertEqual(result['total'],1);self.assertEqual(set(result['rows'][0]),{'id','name'})
    def test_stale_rules_block_registration(self):
        r=self.ingestion();self.change('ingestion.submit','ingestions',r);self.change('ingestion.check','ingestions',r)
        rule=self.c['rules'][0];self.save('rules',dict(rule,name='变更规则名称'),rule)
        with self.assertRaises(cap.Invalid):self.change('ingestion.register','ingestions',r)
        self.change('ingestion.check','ingestions',r);self.change('ingestion.register','ingestions',r)
    def test_revisions_and_illegal_transitions(self):
        r=self.ingestion()
        with self.assertRaises(cap.Invalid):self.call('ingestion.submit',dict(id=r['id'],rev=0))
        with self.assertRaises(cap.Invalid):self.change('ingestion.check','ingestions',r)
        self.change('ingestion.submit','ingestions',r)
        with self.assertRaises(cap.Invalid):self.save('ingestions',r,centers.find(self.c['ingestions'],r['id']))
        self.change('ingestion.return','ingestions',r,note='数据需补正')
        saved=self.save('ingestions',r,centers.find(self.c['ingestions'],r['id']));self.assertEqual(saved['status'],'草稿')
    def test_bad_csv_and_empty_rules_rejected(self):
        for body in ['id,id\n1,2','id,name\n1,2,3','id,name','bad name,id\na,1']:
            with self.assertRaises(cap.Invalid):centers.csv_data(body)
        with self.assertRaises(cap.Invalid):self.save('ingestions',dict(name='无质检',sourceId='source-local',dataRows='id\n1',ruleIds=[]))
    def test_standard_build_creates_real_resource_draft(self):
        ds=self.call('dataset.create',dict(name='标准建表',standardId='standard-basic',layer='专题层'))
        r=cap.find(self.s['resources'],ds['resourceId']);self.assertEqual([f['name'] for f in r['fields']],['id','name','region','area']);self.assertEqual(ds['rowCount'],0)
    def test_todo_mapping_idempotency_scope_and_atomic_validation(self):
        system=self.c['systems'][4];rows=[dict(id='x1',name='规划待办',userId='u1',status='待办',dueAt='2026-01-01T00:00:00',entry='#/front/workbench')]
        self.call('todos.import',dict(systemId=system['id'],payload=rows));self.call('todos.import',dict(systemId=system['id'],payload=rows))
        self.assertEqual(len(self.c['externalTodos']),1)
        data=centers.bootstrap(self.s,self.user,'front');self.assertEqual(len([r for r in data['todos'] if r.get('externalId')=='x1']),1)
        other=user_for(self.s,'u2');self.assertFalse(any(r.get('externalId')=='x1' for r in centers.bootstrap(self.s,other,'front')['todos']))
        with self.assertRaises(cap.Invalid):self.call('todos.import',dict(systemId=system['id'],payload=rows+[dict(rows[0],id='x2',userId='missing')]))
        self.assertEqual(len(self.c['externalTodos']),1)
    def test_system_check_does_not_claim_external_connected(self):
        system=self.c['systems'][0];value=dict(system,entry='https://example.org',authClientId='client_portal',mapping=system['mapping'])
        saved=self.save('systems',value,system);result=self.change('system.check','systems',saved)
        self.assertEqual(result['status'],'配置通过·待联调')
    def test_directory_and_node_cycles_rejected(self):
        parent=self.c['directories'][0];child=self.save('directories',dict(name='子目录',parentId=parent['id'],kind='数据库表'))
        with self.assertRaises(cap.Invalid):self.save('directories',dict(parent,parentId=child['id']),parent)
        root=self.c['nodes'][0]
        with self.assertRaises(cap.Invalid):self.save('nodes',dict(root,parentId=root['id']),root)
        with self.assertRaises(cap.Invalid):self.call('delete',dict(entity='directories',id=parent['id'],rev=parent['rev']))
    def test_delivery_lifecycle_scope_and_revocation(self):
        grant,d=self.approve('r1');d=self.change('delivery.run','deliveries',d)
        self.assertEqual(d['status'],'可领取')
        payload=self.call('delivery.download',{'id':d['id']},self.user);self.assertIn('content',payload)
        with self.assertRaises(cap.Invalid):self.call('delivery.download',{'id':d['id']},user_for(self.s,'u2'))
        execute(self.s,self.admin,'grant.revoke',dict(id=grant['id'],rev=grant['rev'],reason='业务测试结束撤销授权'))
        with self.assertRaises(cap.Invalid):self.call('delivery.download',{'id':d['id']},self.user)
    def test_download_revalidates_hidden_fields(self):
        d=self.call('delivery.create',dict(userId='u1',resourceId='r2',method='数据下载',region='呼和浩特市',fields='area'))
        d=self.change('delivery.run','deliveries',d);self.assertEqual(d['status'],'可领取')
        r=cap.find(self.s['resources'],'r2');r['published']['fields'][1]['display']=False
        with self.assertRaises(cap.Invalid):self.call('delivery.download',{'id':d['id']},self.user)
    def test_delivery_failure_retry_and_offline_notice(self):
        g,d=self.approve('r8');d=self.change('delivery.run','deliveries',d);self.assertEqual(d['status'],'失败');self.assertIn('服务地址',d['error'])
        g,d=self.approve('r1','离线获取');d=self.change('delivery.run','deliveries',d,pickupPlace='测试窗口',pickupAt='2026-12-31T10:00')
        self.assertEqual(d['status'],'可领取');self.call('delivery.receive',dict(id=d['id'],rev=d['rev'],note='已领取'),self.user)
        self.assertEqual(centers.find(self.c['deliveries'],d['id'])['status'],'已领取')
    def test_subscription_generates_package_and_pauses_on_revoked_grant(self):
        g,d=self.approve('r1','数据订阅');sub=self.call('subscription.create',dict(deliveryId=d['id'],intervalSeconds=60))
        self.change('subscription.run','subscriptions',sub);self.assertEqual(len(self.c['deliveries']),2)
        execute(self.s,self.admin,'grant.revoke',dict(id=g['id'],rev=g['rev'],reason='撤销订阅源授权测试'))
        sub=self.change('subscription.run','subscriptions',sub);self.assertEqual(sub['status'],'已暂停');self.assertTrue(sub['error'])
    def test_ordinary_user_cannot_manage_centers(self):
        for op,p in [('save',dict(entity='rules',values={'name':'不允许'})),('inspection.run',{}),('tool.trial',{'id':'coordinate','payload':{'x':111,'y':40}})]:
            with self.assertRaises(cap.Invalid):self.call(op,p,self.user)
    def test_favorites_check_visibility_and_toggle(self):
        self.call('favorite',{'id':'resource:r1'},self.user);self.assertIn('resource:r1',self.c['favorites']['u1'])
        self.call('favorite',{'id':'resource:r1'},self.user);self.assertEqual(self.c['favorites']['u1'],[])
        with self.assertRaises(cap.Invalid):self.call('favorite',{'id':'resource:r12'},self.user)
    def test_tool_review_before_publish_and_edit_invalidates_approval(self):
        r=pm.migrate(self.s)['tools'][0]
        with self.assertRaises(cap.Invalid):execute(self.s,self.admin,'portal.publish',dict(entity='tools',id=r['id'],rev=r['rev']))
        self.call('tool.submit',dict(id=r['id'],rev=r['rev']));self.call('tool.review',dict(id=r['id'],rev=r['rev'],decision='通过',note='接口配置检查符合要求'))
        execute(self.s,self.admin,'portal.publish',dict(entity='tools',id=r['id'],rev=r['rev']))
        r=execute(self.s,self.admin,'portal.save',dict(entity='tools',id=r['id'],rev=r['rev'],values={'name':'修改版本'}))
        with self.assertRaises(cap.Invalid):execute(self.s,self.admin,'portal.publish',dict(entity='tools',id=r['id'],rev=r['rev']))
    def test_tool_trials_compute_coordinates_and_polygon_area(self):
        result=self.call('tool.trial',dict(id='coordinate',payload={'x':0,'y':0}));self.assertEqual(result['status'],'成功');self.assertEqual(result['output']['x'],0)
        polygon={'type':'Polygon','coordinates':[[[111,40],[111.01,40],[111.01,40.01],[111,40.01],[111,40]]]}
        result=self.call('tool.trial',dict(id='area',payload={'geometry':polygon}));self.assertEqual(result['status'],'成功');self.assertGreater(result['output']['areaSquareMeters'],0)
        result=self.call('tool.trial',dict(id='coordinate',payload={'x':999,'y':0}));self.assertEqual(result['status'],'失败');self.assertTrue(result['error'])
    def test_spatial_write_is_local_and_revision_guarded(self):
        r={'engine':'spatial-store'};polygon={'type':'Polygon','coordinates':[[[111,40],[111.01,40],[111.01,40.01],[111,40.01],[111,40]]]}
        payload=dict(resourceId='r3',featureId='test',revision=1,geometry=polygon)
        result=centers.run_tool(self.s,r,payload);self.assertEqual(result['count'],1)
        with self.assertRaises(cap.Invalid):centers.run_tool(self.s,r,payload)
        rows=centers.run_tool(self.s,{'engine':'spatial-query'},{'resourceId':'r3'});self.assertEqual(len(rows['features']),1)
        centers.run_tool(self.s,{'engine':'spatial-edit'},dict(payload,revision=2,operation='delete'))
        self.assertEqual(len(centers.run_tool(self.s,{'engine':'spatial-query'},{'resourceId':'r3'})['features']),0)
    def test_centers_persist_with_platform_store(self):
        r=self.ingestion()
        with tempfile.TemporaryDirectory() as folder,sqlite3.connect(str(Path(folder)/'state.db')) as conn:
            conn.execute('CREATE TABLE state(id INTEGER PRIMARY KEY,body TEXT)');conn.execute('INSERT INTO state VALUES(1,?)',('{}',));platform_store.initialize(conn);platform_store.save(conn,self.s)
            restored=json.loads(conn.execute('SELECT body FROM state WHERE id=1').fetchone()[0]);self.assertEqual(restored['centers']['ingestions'][0]['id'],r['id'])

    def test_assignee_can_feedback_but_cannot_review_or_access_others(self):
        r=self.ingestion(True);self.change('ingestion.submit','ingestions',r)
        report=self.change('ingestion.check','ingestions',r)
        issue=self.call('quality.issue',dict(id=report['id'],assigneeId='u1'))
        self.assertEqual(len(centers.bootstrap(self.s,self.user,'front')['ingestions']),1)
        self.assertEqual(centers.bootstrap(self.s,user_for(self.s,'u2'),'front')['issues'],[])
        payload=dict(id=issue['id'],rev=issue['rev'],note='核对并修正负数面积',evidence='台账',dataRows=r['dataRows'].replace('-3','3'))
        with self.assertRaises(cap.Invalid):self.call('issue.feedback',payload,user_for(self.s,'u2'))
        result=self.call('issue.feedback',payload,self.user)
        with self.assertRaises(cap.Invalid):self.call('issue.review',dict(id=issue['id'],rev=result['rev']),self.user)
        self.change('issue.review','issues',issue)

    def test_tool_templates_are_idempotent_unpublished_and_admin_only(self):
        with self.assertRaises(cap.Invalid):self.call('tool.templates',{},self.user)
        result=self.call('tool.templates');self.assertEqual(len(result['created']),4)
        self.assertEqual(self.call('tool.templates')['created'],[])
        rows=[r for r in pm.migrate(self.s)['tools'] if r['engine'].startswith('spatial-')]
        self.assertEqual(len(rows),4)
        for r in rows:self.assertEqual(r['audience'],'管理员');self.assertIsNone(cap.published(r))

    def test_sso_configuration_and_exchange_direction(self):
        r=self.c['systems'][0];r=self.save('systems',dict(r,entry='https://example.org'),r)
        result=self.change('system.check','systems',r)
        self.assertIn('单点登录客户端',result['lastCheck']['missing']);self.assertEqual(result['status'],'待配置')
        node=self.c['nodes'][0];node=self.save('nodes',dict(node,direction='导入'),node)
        with self.assertRaises(cap.Invalid):self.call('node.export',{'id':node['id']})

if __name__=='__main__':unittest.main()

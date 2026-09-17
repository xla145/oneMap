"""Portal publishing and review boundaries, independent of the user's demo database."""
import base64
import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
from seed import seed
from server import bootstrap, execute, user_for, find, public_resources
from capabilities import Invalid
import portal_management as pm


class PortalManagementTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin')
        self.m=pm.migrate(self.s)
    def call(self,a,p,u=None):return pm.execute(self.s,u or self.admin,a,p)
    def front(self):return pm.bootstrap(self.s,self.user,'front')
    def save(self,entity,values,row=None):return self.call('portal.save',dict(entity=entity,values=values,**({'id':row['id'],'rev':row['rev']} if row else {})))
    def transition(self,action,entity,r):
        current=pm.find(self.m[entity],r['id'])
        revision=r['rev']
        if action=='publish' and entity=='tools' and current['rev']==revision:
            execute(self.s,self.admin,'centers.tool.submit',dict(id=current['id'],rev=current['rev']))
            execute(self.s,self.admin,'centers.tool.review',dict(id=current['id'],rev=current['rev'],decision='通过',note='测试工具配置审核通过'))
            revision=current['rev']
        return self.call('portal.'+action,dict(entity=entity,id=r['id'],rev=revision))

    def test_tools_migrate_once_and_do_not_overwrite_edits(self):
        self.assertEqual(len(self.m['tools']),5)
        self.m['tools'][0]['name']='已编辑';before=deepcopy(self.s)
        pm.migrate(self.s);self.assertEqual(self.s,before)
    def test_tool_publication_isolation_conflict_and_disable_during_edit(self):
        r=self.m['tools'][0];draft=self.save('tools',{'name':'新版名称'},r)
        self.assertNotEqual(self.front()['tools'][0]['name'],'新版名称')
        with self.assertRaises(Invalid):self.transition('publish','tools',r)
        live=self.transition('publish','tools',draft);self.assertEqual(pm.tool(self.s,r['id'])['name'],'新版名称')
        disabled=self.transition('disable','tools',live)
        with self.assertRaises(Invalid):pm.tool(self.s,r['id'])
        edited=self.save('tools',{'name':'下架修改'},disabled)
        with self.assertRaises(Invalid):pm.tool(self.s,r['id'])
        self.assertNotIn(r['id'],[r['id'] for r in self.front()['tools']])
        self.transition('publish','tools',edited);self.assertEqual(pm.tool(self.s,r['id'])['name'],'下架修改')
    def test_external_url_and_engine_restrictions(self):
        for url in ['javascript:alert(1)','http://example.org','https://user:secret@example.org']:
            with self.assertRaises(Invalid):self.save('tools',dict(name='工具',category='外部',engine='external',url=url))
        with self.assertRaises(Invalid):self.save('tools',dict(name='工具',category='外部',engine='execute-shell'))
        r=self.save('tools',dict(name='自定义工具',category='分析',engine='overlay'))
        self.transition('publish','tools',r);pm.tool(self.s,r['id'],'overlay')
        with self.assertRaises(Invalid):pm.tool(self.s,r['id'],'compliance')
    def test_material_file_version_and_unpublished_payload_not_in_bootstrap(self):
        r=self.save('materials',dict(name='测试资料',category='培训',filename='指南.pdf',fileData=base64.b64encode(b'%PDF-example').decode()))
        self.assertEqual(self.front()['materials'],[])
        r=self.transition('publish','materials',r)
        row=self.front()['materials'][0];self.assertNotIn('fileData',row)
        self.assertNotIn('fileData',pm.bootstrap(self.s,self.admin,'admin')['materials'][0]['published'])
        d=self.call('portal.materialDownload',{'id':r['id']},self.user)
        self.assertEqual(base64.b64decode(d['content']),b'%PDF-example')
        draft=self.save('materials',dict(filename='新版.txt',fileData=base64.b64encode(b'new').decode()),r)
        self.assertEqual(self.call('portal.materialDownload',{'id':r['id']},self.user)['filename'],'指南.pdf')
        r=self.transition('publish','materials',draft)
        self.assertEqual(self.call('portal.materialDownload',{'id':r['id']},self.user)['filename'],'新版.txt')
        self.transition('disable','materials',r)
        with self.assertRaises(Invalid):self.call('portal.materialDownload',{'id':r['id']},self.user)
    def test_attachment_validation_and_admin_boundary(self):
        for filename,data in [('bad.html','eA=='),('../a.pdf','eA=='),('a.pdf','not-base64'),('a.pdf','')]:
            with self.assertRaises(Invalid):self.save('materials',dict(name='资料',category='培训',filename=filename,fileData=data))
        with self.assertRaises(Invalid):self.call('portal.save',dict(entity='tools',values={}),self.user)
    def test_registration_pending_idempotent_review_and_privacy(self):
        payload=dict(name='演示申请人',department='测试单位',contact='test@example.invalid',reason='测试访问',requestId='one')
        before=len(self.s['users']);r=self.call('portal.register',payload,self.user)
        self.assertEqual(self.call('portal.register',payload,self.user),r);self.assertEqual(len(self.s['users']),before)
        self.assertEqual(pm.bootstrap(self.s,user_for(self.s,'u2'),'front')['registrations'],[])
        review=dict(id=r['id'],rev=r['rev'],status='已通过',note='资料完整',orgId='org_hall',region='全区')
        with self.assertRaises(Invalid):self.call('portal.review',review,self.user)
        result=self.call('portal.review',review);self.assertEqual(len(self.s['users']),before+1)
        self.assertEqual(find(self.s['users'],result['userId'])['role'],'业务用户')
        with self.assertRaises(Invalid):self.call('portal.review',review)
    def test_rejection_never_creates_user(self):
        before=len(self.s['users']);r=self.call('portal.register',dict(name='测试',department='测试',contact='reject@example.invalid',reason='测试',requestId='r'),self.user)
        self.call('portal.review',dict(id=r['id'],rev=r['rev'],status='已驳回',note='信息需完善'))
        self.assertEqual(len(self.s['users']),before)
    def test_resource_edit_after_disable_does_not_republish(self):
        r=find(self.s['resources'],'r2')
        execute(self.s,self.admin,'disable',dict(entity='resources',id=r['id'],rev=r['rev']))
        draft=execute(self.s,self.admin,'save',dict(entity='resources',id=r['id'],rev=r['rev'],values={'name':'下架后编辑资源'}))
        self.assertNotIn(r['id'],[x['id'] for x in public_resources(self.s,self.user)])
        execute(self.s,self.admin,'publish',dict(entity='resources',id=draft['id'],rev=draft['rev']))
        self.assertIn(r['id'],[x['id'] for x in public_resources(self.s,self.user)])
    def test_resource_url_does_not_leak_and_requires_current_grant(self):
        r=find(self.s['resources'],'r1');r['published']['serviceUrl']='https://example.org/resource'
        front=find(public_resources(self.s,self.user),'r1');self.assertNotIn('serviceUrl',front);self.assertTrue(front['hasServiceUrl'])
        with self.assertRaises(Invalid):self.call('portal.resourceAccess',dict(id='r1',kind='serviceUrl'),self.user)
        self.s['grants'].append(dict(userId=self.user['id'],resourceId='r1',validUntil='2999-01-01'))
        self.assertEqual(self.call('portal.resourceAccess',dict(id='r1',kind='serviceUrl'),self.user)['url'],'https://example.org/resource')
        r['status']='已停用'
        with self.assertRaises(Invalid):self.call('portal.resourceAccess',dict(id='r1',kind='serviceUrl'),self.user)
    def test_reports_statistics_filters_and_access(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/'test.sqlite3';pm.initialize(db)
            self.call('portal.visit',{'route':'/front/data'},self.user)
            self.call('portal.visit',{'route':'/front/data'},self.user)
            self.call('portal.toolResult',{'id':'coordinate','status':'成功','durationMs':4},self.user)
            pm.record_request(db,('trace-1',pm.now(),'u1','测试用户','POST','/api/action','analysis.spatial','overlay',403,2,'127.0.0.1','已下架'))
            r=pm.report(db,self.s,self.admin,{'kind':'api','q':'trace-1'})
            self.assertEqual(r['total'],1);self.assertEqual(r['rows'][0]['status'],'403')
            self.assertEqual(r['stats']['pv'],2);self.assertEqual(r['stats']['uv'],1)
            self.assertEqual(r['stats']['tools'][3]['failed'],1)
            with self.assertRaises(Invalid):pm.report(db,self.s,self.user,{})
            with self.assertRaises(Invalid):pm.report(db,self.s,self.admin,{'start':'not-a-date'})
            self.assertEqual(pm.report(db,self.s,self.admin,{'start':'2999-01-01'})['total'],0)


class PortalKeyTests(PortalManagementTests):
    def setUp(self):
        super().setUp()
        import portal_keys
        self.keys=portal_keys
    def test_key_review_once_secret_scope_disable_expiry(self):
        r=self.call('portal.keyApply',dict(kind='tool',targetId='coordinate',purpose='接口集成',days=30),self.user)
        with self.assertRaises(Invalid):self.call('portal.keyActivate',dict(id=r['id'],rev=r['rev']),self.user)
        r=self.call('portal.keyReview',dict(id=r['id'],rev=r['rev'],status='已通过',note='同意集成'))
        result=self.call('portal.keyActivate',dict(id=r['id'],rev=r['rev']),self.user)
        secret=result['secret'];self.assertNotIn(secret,str(self.s))
        self.assertNotIn('secretHash',self.front()['apiKeys'][0])
        u,key,t=self.keys.authenticate(self.s,'Bearer '+secret,'tool','coordinate');self.assertEqual(u['id'],self.user['id'])
        with self.assertRaises(Invalid):self.keys.authenticate(self.s,'Bearer '+secret,'tool','overlay')
        with self.assertRaises(Invalid):self.call('portal.keyActivate',dict(id=key['id'],rev=key['rev']),self.user)
        key=self.call('portal.keyToggle',dict(id=key['id'],rev=key['rev']))
        with self.assertRaises(Invalid):self.keys.authenticate(self.s,'Bearer '+secret,'tool','coordinate')
        self.call('portal.keyToggle',dict(id=key['id'],rev=key['rev']))
        self.keys.rows(self.s)[0]['validUntil']='2000-01-01'
        with self.assertRaises(Invalid):self.keys.authenticate(self.s,'Bearer '+secret,'tool','coordinate')
    def test_portal_role_and_tool_access_enforced(self):
        t=self.m['tools'][0];t=self.save('tools',{'audience':'企业用户'},t);self.transition('publish','tools',t)
        with self.assertRaises(Invalid):pm.tool(self.s,'coordinate',u=self.user)
        self.assertNotIn('coordinate',[t['id'] for t in self.front()['tools']])
        self.user=self.call('portal.userRole',dict(id=self.user['id'],rev=self.user.get('rev',1),role='企业用户'))
        pm.tool(self.s,'coordinate',u=self.user)
        with self.assertRaises(Invalid):self.call('portal.userRole',dict(id=self.admin['id'],rev=self.admin.get('rev',1),role='普通用户'))
    def test_api_execution_coordinate_and_spatial(self):
        t=pm.tool(self.s,'coordinate');r=self.keys.invoke(t,{'x':111.7,'y':40.8})
        back=self.keys.invoke(t,dict(x=r['x'],y=r['y'],direction='inverse'))
        self.assertAlmostEqual(back['x'],111.7);self.assertAlmostEqual(back['y'],40.8)
        with self.assertRaises(Invalid):self.keys.invoke(t,{'x':float('nan'),'y':40})
    def test_unapproved_key_is_not_usable_and_data_needs_grant(self):
        with self.assertRaises(Invalid):self.keys.authenticate(self.s,'Bearer invalid','tool','coordinate')
        with self.assertRaises(Invalid):self.call('portal.keyApply',dict(kind='data',targetId='r1',purpose='取数'),self.user)

class PortalOperationsTests(unittest.TestCase):
    def setUp(self):
        import portal_operations as ops
        import server
        self.ops=ops;self.server=server;self.temp=tempfile.TemporaryDirectory();self.old=server.DB
        server.DB=Path(self.temp.name)/'ops.sqlite3';server.init_db()
        import sqlite3
        with sqlite3.connect(server.DB) as c:self.s=server.read_state(c)
        self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
    def tearDown(self):self.server.DB=self.old;self.temp.cleanup();self.ops.RATE.clear()
    def test_ip_and_rate_policies_are_applied(self):
        c=self.ops.settings(self.s);c.update(whitelistEnabled=True,networks=['192.0.2.0/24'])
        self.ops.check_request(self.s,'192.0.2.3','browser');self.ops.check_request(self.s,'127.0.0.1','browser')
        with self.assertRaises(Invalid):self.ops.check_request(self.s,'198.51.100.1','browser')
        c.update(rateEnabled=True,requestsPerMinute=10)
        for _ in range(10):self.ops.check_request(self.s,'192.0.2.3','browser')
        with self.assertRaises(Invalid) as e:self.ops.check_request(self.s,'192.0.2.3','browser')
        self.assertEqual(e.exception.status,429)
        c['blockedAgents']=['crawler']
        with self.assertRaises(Invalid):self.ops.check_request(self.s,'127.0.0.1','test CRAWLER')
    def test_security_admin_validation_and_cert_validation(self):
        cfg=self.ops.settings(self.s)
        with self.assertRaises(Invalid):self.ops.execute(self.server.DB,self.s,self.user,'portal.securityGet',{})
        for values in [dict(cfg,networks=['bad-ip']),dict(cfg,tlsEnabled=True,certPath='/nonexistent',keyPath='/nonexistent'),dict(cfg,requestsPerMinute=-1)]:
            with self.assertRaises(Invalid):self.ops.execute(self.server.DB,self.s,self.admin,'portal.securitySave',dict(rev=cfg['rev'],values=values))
    def test_backup_restore_integrity_and_confirmation(self):
        import sqlite3
        db=self.server.DB;r=self.ops.backup(db)
        with sqlite3.connect(db) as c:c.execute("INSERT INTO portal_requests VALUES('test','2026-09-16','','','GET','/api/test','','',200,1,'127.0.0.1','')")
        with self.assertRaises(Invalid):self.ops.execute(db,self.s,self.admin,'portal.restore',{'id':r['id'],'confirm':'wrong'})
        out=self.ops.execute(db,self.s,self.admin,'portal.restore',{'id':r['id'],'confirm':r['id']})
        self.assertTrue(out['safetyBackup'].startswith('before-restore'))
        with sqlite3.connect(db) as c:self.assertEqual(c.execute('SELECT count(*) FROM portal_requests').fetchone()[0],0)
        self.assertEqual(len(self.ops.backups(db)),2)

if __name__=='__main__':unittest.main()

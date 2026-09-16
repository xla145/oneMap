import unittest
from copy import deepcopy
from datetime import date, timedelta
import capabilities as cap
import admin_design
import portal_management as portal
from seed import seed
from server import execute, bootstrap, user_for, public_resources

class AdminDesignTests(unittest.TestCase):
    def setUp(self):
        self.s=seed(); self.admin=user_for(self.s,'admin'); self.user=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin')
    def call(self,action,p,user=None):return execute(self.s,user or self.admin,action,p)
    def approve(self,rid='r1'):
        a=self.call('apply',dict(resourceIds=[rid],purpose='用于测试个人授权边界',validUntil=(date.today()+timedelta(days=10)).isoformat()),self.user)
        self.call('decide',dict(id=a['id'],rev=a['rev'],resourceId=rid,decision='已通过',note='用途符合测试范围'))
        return self.s['grants'][-1]
    def test_grant_is_individual_and_revoke_blocks_access(self):
        g=self.approve();r=cap.published(cap.find(self.s['resources'],'r1'))
        self.assertTrue(cap.authorized(self.s,self.user,r))
        other=dict(self.user,id='another-user')
        self.assertFalse(cap.authorized(self.s,other,r))
        self.assertTrue(g['sourceApplicationId']);self.assertEqual(g['deliveryStatus'],'已生效')
        self.call('grant.revoke',dict(id=g['id'],rev=g['rev'],reason='业务结束撤销测试授权'))
        self.assertFalse(cap.authorized(self.s,self.user,r))
        self.assertEqual(admin_design.grant_rows(self.s,self.admin)[0]['deliveryStatus'],'已停止')
        self.assertEqual(next(x for x in public_resources(self.s,self.user) if x['id']=='r1')['access'],'可申请')
    def test_grant_permission_revision_and_expiry(self):
        g=self.approve()
        with self.assertRaises(cap.Invalid):self.call('grant.revoke',dict(id=g['id'],rev=1,reason='不允许普通用户撤销'),self.user)
        with self.assertRaises(cap.Invalid):self.call('grant.revoke',dict(id=g['id'],rev=0,reason='过期版本不允许操作'))
        g['validUntil']='2000-01-01'
        self.assertEqual(admin_design.grant_rows(self.s,self.admin)[0]['displayStatus'],'已过期')
        self.assertFalse(cap.authorized(self.s,self.user,cap.published(cap.find(self.s['resources'],'r1'))))
    def test_legacy_grant_migration_preserves_access_and_is_idempotent(self):
        self.s['grants']=[dict(userId='u1',resourceId='r1',validUntil='2099-01-01')]
        admin_design.migrate(self.s);before=deepcopy(self.s['grants']);admin_design.migrate(self.s)
        self.assertEqual(before,self.s['grants']);self.assertTrue(cap.authorized(self.s,self.user,cap.find(self.s['resources'],'r1')))
    def test_policy_is_independent_and_draft_does_not_open_resource(self):
        r=cap.find(self.s['resources'],'r1')
        self.call('save',dict(entity='resources',id=r['id'],rev=r['rev'],values={'sharingPolicy':'开放使用'}))
        r=cap.find(self.s['resources'],'r1')
        self.assertFalse(cap.authorized(self.s,self.user,cap.published(r)))
        self.call('publish',dict(entity='resources',id=r['id'],rev=r['rev']))
        self.assertTrue(cap.authorized(self.s,self.user,cap.published(r)))
        self.call('save',dict(entity='resources',id=r['id'],rev=r['rev'],values={'sharingPolicy':'限制使用'}))
        r=cap.find(self.s['resources'],'r1');self.call('publish',dict(entity='resources',id=r['id'],rev=r['rev']))
        self.assertFalse(cap.authorized(self.s,self.user,cap.published(r)))
    def test_content_channels_keep_independent_versions_and_withdrawal(self):
        r=self.s['knowledge'][0];key=r['id'];old=r['body']
        self.call('save',dict(entity='knowledge',id=key,rev=r['rev'],values={'body':'新的独立门户文章内容，用于渠道版本隔离验证。'}))
        r=cap.find(self.s['knowledge'],key)
        self.call('knowledge.channel',dict(id=key,rev=r['rev'],channel='portal',enabled=True))
        self.assertEqual(cap.knowledge_channel(r,'index')['body'],old)
        self.assertIn('独立门户',cap.knowledge_channel(r,'portal')['body'])
        self.call('knowledge.channel',dict(id=key,rev=r['rev'],channel='index',enabled=False))
        self.assertIsNone(cap.knowledge_channel(r,'index'))
        self.assertIsNotNone(cap.knowledge_channel(r,'portal'))
        self.assertNotIn(key,[x['documentId'] for x in cap.search_knowledge(self.s,self.user,'耕地')])
        self.call('knowledge.channel',dict(id=key,rev=r['rev'],channel='index',enabled=True))
        self.call('knowledge.channel',dict(id=key,rev=r['rev'],channel='portal',enabled=False))
        self.assertIsNotNone(cap.knowledge_channel(r,'index'))
        with self.assertRaises(cap.Invalid):self.call('portal.newsDownload',{'id':key},self.user)
    def test_global_disable_does_not_reactivate_other_channel(self):
        r=self.s['knowledge'][0]
        self.call('knowledge.channel',dict(id=r['id'],rev=r['rev'],channel='portal',enabled=True))
        self.call('disable',dict(entity='knowledge',id=r['id'],rev=r['rev']))
        self.call('knowledge.channel',dict(id=r['id'],rev=r['rev'],channel='index',enabled=True))
        self.assertIsNone(cap.knowledge_channel(r,'portal'))
        self.assertIsNotNone(cap.knowledge_channel(r,'index'))
        with self.assertRaises(cap.Invalid):self.call('publish',dict(entity='knowledge',id=r['id'],rev=r['rev']))
    def test_linked_tool_enforces_shared_grant_and_stop(self):
        t=portal.migrate(self.s)['tools'][0]
        self.call('portal.save',dict(entity='tools',id=t['id'],rev=t['rev'],values={'resourceId':'r8'}))
        t=portal.find(portal.migrate(self.s)['tools'],t['id'])
        self.call('centers.tool.submit',dict(id=t['id'],rev=t['rev']))
        self.call('centers.tool.review',dict(id=t['id'],rev=t['rev'],decision='通过',note='测试关联工具审核通过'))
        self.call('portal.publish',dict(entity='tools',id=t['id'],rev=t['rev']))
        with self.assertRaises(cap.Invalid):portal.tool(self.s,t['id'],u=self.user)
        g=self.approve('r8');self.assertEqual(portal.tool(self.s,t['id'],u=self.user)['resourceId'],'r8')
        self.call('grant.revoke',dict(id=g['id'],rev=g['rev'],reason='撤销后工具调用应失败'))
        with self.assertRaises(cap.Invalid):portal.tool(self.s,t['id'],u=self.user)
    def test_linked_tool_rejects_non_tool_and_duplicate(self):
        tools=portal.migrate(self.s)['tools'];t=tools[0]
        with self.assertRaises(cap.Invalid):self.call('portal.save',dict(entity='tools',id=t['id'],rev=t['rev'],values={'resourceId':'r1'}))
        self.call('portal.save',dict(entity='tools',id=t['id'],rev=t['rev'],values={'resourceId':'r8'}))
        t=tools[1]
        with self.assertRaises(cap.Invalid):self.call('portal.save',dict(entity='tools',id=t['id'],rev=t['rev'],values={'resourceId':'r8'}))
    def test_approved_expiry_cannot_expand_requested_expiry(self):
        until=(date.today()+timedelta(days=10)).isoformat()
        a=self.call('apply',dict(resourceIds=['r1'],purpose='测试核准截止期限',validUntil=until),self.user)
        payload=dict(id=a['id'],rev=a['rev'],resourceId='r1',decision='已通过',note='核准期限范围测试',approvedUntil='2099-01-01')
        with self.assertRaises(cap.Invalid):self.call('decide',payload)
        self.assertEqual(a['items'][0]['status'],'待审核')
        payload['approvedUntil']=(date.today()+timedelta(days=3)).isoformat()
        self.call('decide',payload)
        self.assertEqual(self.s['grants'][-1]['validUntil'],payload['approvedUntil'])
    def test_bootstrap_uses_channels_and_restricts_approval_records(self):
        self.approve()
        r=self.s['knowledge'][0]
        self.call('knowledge.channel',dict(id=r['id'],rev=r['rev'],channel='index',enabled=False))
        data=bootstrap(self.s,self.user,'front')
        self.assertNotIn(r['id'],[x['id'] for x in data['knowledge']])
        self.assertIn(r['id'],[x['id'] for x in data['portalArticles']])
        self.assertTrue(all('chunks' not in x for x in data['portalArticles']))
        app_admin=next(u for u in self.s['users'] if u['role']=='应用管理员')
        self.assertEqual(bootstrap(self.s,app_admin,'admin')['applications'],[])
    def test_quality_does_not_claim_business_data_passed(self):
        rows=bootstrap(self.s,self.admin,'admin')['platform']['quality']
        self.assertTrue(rows);self.assertTrue(all(r['status'] in ['元数据完整性通过','待补充'] for r in rows))

if __name__=='__main__':unittest.main()

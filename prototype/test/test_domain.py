import unittest
from copy import deepcopy
from datetime import date, timedelta
from seed import seed
from server import execute, bootstrap, user_for, published, Invalid, public_resources

class Workflows(unittest.TestCase):
    def setUp(self):
        self.s=seed(); self.u=user_for(self.s,'u1');self.admin=user_for(self.s,'admin')
    def call(self,action,p,user=None): return execute(self.s,user or self.u,action,p)
    def test_publish_isolates_draft(self):
        r=self.s['resources'][0];p=deepcopy(r['published'])
        self.call('save',dict(entity='resources',id=r['id'],rev=r['rev'],values={'aliases':'特别业务别名'}),self.admin)
        r=self.s['resources'][0];self.assertEqual(p['aliases'],published(r)['aliases'])
        self.call('publish',dict(entity='resources',id=r['id'],rev=r['rev']),self.admin)
        sess=self.call('chat',dict(question='特别业务别名',agentId='a1'))
        self.assertIn('r1',sess['messages'][-1]['resourceIds'])
    def test_multi_resource_approval_and_idempotency(self):
        p=dict(resourceIds=['r1','r8'],purpose='用于地灾巡查原型验证',validUntil=(date.today()+timedelta(days=30)).isoformat(),requestId='unique')
        a=self.call('apply',p);self.assertEqual(self.call('apply',p)['id'],a['id']);self.assertEqual(len(self.s['applications']),1)
        self.call('decide',dict(id=a['id'],rev=1,resourceId='r1',decision='已通过',note='用途符合演示要求'),self.admin)
        self.call('decide',dict(id=a['id'],rev=2,resourceId='r8',decision='已驳回',note='工具暂不提供使用'),self.admin)
        self.assertEqual(a['status'],'部分通过');self.assertEqual(next(r for r in public_resources(self.s,self.u) if r['id']=='r1')['access'],'已授权')
        self.assertEqual(next(r for r in public_resources(self.s,self.u) if r['id']=='r8')['access'],'可申请')
    def test_cross_user_memory_and_conversation(self):
        a=self.call('chat',dict(question='找地灾巡查记录表',agentId='a1'))
        other=user_for(self.s,'u2');self.assertEqual(bootstrap(self.s,other,'front')['sessions'],[])
        with self.assertRaises(Invalid):self.call('chat',dict(question='继续',agentId='a1',sessionId=a['id']),other)
        self.call('preferences',dict(userId='u1',rev=1,region='呼和浩特市',domain='地灾',detail='详细',summary='地灾巡查',enabled=True))
        b=self.call('chat',dict(question='查询地灾',agentId='a1'));self.assertEqual(b['context']['region'],'呼和浩特市')
        b=self.call('chat',dict(question='只看包头市',agentId='a1',sessionId=b['id'],context={'region':'呼和浩特市','period':'全部时间'}));self.assertEqual(b['context']['region'],'包头市')
    def test_unknown_query_and_restricted_resource(self):
        a=self.call('chat',dict(question='完全不匹配的量子问题',agentId='a1'));self.assertEqual(a['messages'][-1]['resourceIds'],[])
        self.assertNotIn('r12',[r['id'] for r in public_resources(self.s,self.u)])
        r=next(r for r in public_resources(self.s,self.u) if r['id']=='r1');self.assertNotIn('sample',r)
    def test_document_citation_snapshot(self):
        a=self.call('chat',dict(question='什么是耕地占补平衡',agentId='a2'))
        c=a['messages'][-1]['citations'][0];self.assertEqual(c['documentId'],'k1');self.assertEqual(c['version'],1)
        self.call('disable',dict(entity='knowledge',id='k1',rev=1),self.admin)
        b=self.call('chat',dict(question='什么是耕地占补平衡',agentId='a2'));self.assertEqual(b['messages'][-1]['citations'],[])
        self.assertTrue(c['chunks'])
    def test_indicator_trial_and_published_value(self):
        result=self.call('trial',dict(entity='indicators',id='i1'),self.admin);self.assertEqual(result['value'],400)
        self.call('save',dict(entity='indicators',id='i1',rev=1,values={'unit':'亩','caliber':'示例测试口径','values':'10,20,30'}),self.admin)
        r=self.s['indicators'][0];self.call('publish',dict(entity='indicators',id=r['id'],rev=r['rev']),self.admin)
        a=self.call('chat',dict(question='查询耕地保有量指标',agentId='a3'));self.assertEqual(a['messages'][-1]['indicators'][0]['value'],60)
        self.assertEqual(a['messages'][-1]['indicators'][0]['unit'],'亩')
    def test_feedback_to_sample(self):
        a=self.call('chat',dict(question='找最近的地灾巡查记录表',agentId='a1'))
        f=self.call('feedback',dict(sessionId=a['id'],messageId=a['messages'][-1]['id'],note='请改进回答'))
        self.call('feedbackConvert',{'id':f['id']},self.admin)
        sample=next(c for c in self.s['corpora'] if c['id']==f['sampleId'])
        self.assertEqual(sample['status'],'草稿');self.assertEqual(sample['body'],'找最近的地灾巡查记录表')
        self.call('save',dict(entity='corpora',id=sample['id'],rev=sample['rev'],values={'answer':'已经修正的业务答案'}),self.admin)
        sample=next(c for c in self.s['corpora'] if c['id']==f['sampleId'])
        self.call('publish',dict(entity='corpora',id=sample['id'],rev=sample['rev']),self.admin)
        b=self.call('chat',dict(question='找最近的地灾巡查记录表',agentId='a1'))
        self.assertIn('已经修正的业务答案',b['messages'][-1]['text'])
    def test_write_permissions_and_conflict(self):
        with self.assertRaises(Invalid):self.call('save',dict(entity='knowledge',values={'name':'不应保存'}))
        with self.assertRaises(Invalid):self.call('disable',dict(entity='resources',id='r1',rev=0),self.admin)
        with self.assertRaises(Invalid):self.call('preferences',dict(userId='u2',rev=1))
    def test_template_variable_validation(self):
        with self.assertRaises(Invalid):self.call('save',dict(entity='corpora',values={'name':'错误模板','type':'提示词模板','body':'{{unknown}}','variables':''}),self.admin)
    def test_stop_agent_and_role_bootstrap(self):
        self.call('disable',dict(entity='agents',id='a1',rev=1),self.admin)
        with self.assertRaises(Invalid):self.call('chat',dict(question='地灾',agentId='a1'))
        self.assertFalse(bootstrap(self.s,self.u,'admin')['integration']['canManage'])

if __name__=='__main__':unittest.main()

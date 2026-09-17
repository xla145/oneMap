import unittest
from seed import seed
import public_portal
from server import execute, user_for, find


class PortalComparisons(unittest.TestCase):
    def setUp(self):
        self.s=seed()
        public_portal.migrate(self.s)
        self.u=user_for(self.s,'u1')

    def ask(self,q,user=None):
        return execute(self.s,user or self.u,'chat',dict(agentId='a3',question=q))['messages'][-1]

    def test_region_comparison(self):
        r=self.ask('对比2026年呼和浩特市和包头市的耕地面积')['templateRuns'][0]
        self.assertEqual([x['数值'] for x in r['rows']],[400,280])
        self.assertIn('-120',r['answer']);self.assertIn('-30.00%',r['answer'])

    def test_year_comparison(self):
        r=self.ask('呼和浩特市2025年与2026年耕地面积变化多少？')['templateRuns'][0]
        self.assertEqual([x['数值'] for x in r['rows']],[350,400])
        self.assertIn('+14.29%',r['answer'])

    def test_target_and_rate(self):
        r=self.ask('对比2026年呼和浩特市的耕地面积和保护目标')['templateRuns'][0]
        self.assertIn('95.24%',r['answer']);self.assertIn('-20',r['answer'])
        r=self.ask('对比2026年呼和浩特市和包头市的耕地保护达标指数')['templateRuns'][0]
        self.assertEqual([x['数值'] for x in r['rows']],[95.24,93.33])
        self.assertIn('-1.91 个百分点',r['answer'])

    def test_missing_data_and_restricted_user(self):
        for q,u in [('对比2024年和2026年呼和浩特市耕地面积',self.u),('对比2026年呼和浩特市和包头市耕地面积',user_for(self.s,'u2'))]:
            r=self.ask(q,u)['templateRuns'][0]
            self.assertEqual(r['rows'],[]);self.assertIn('本次未生成对比',r['answer'])

    def test_zero_baseline_and_live_published_data(self):
        r=find(self.s['resources'],'r2')['published']
        r['dataRows']=r['dataRows'].replace('2025年,呼和浩特市,350,420','2025年,呼和浩特市,0,420')
        result=self.ask('对比2025年和2026年呼和浩特市耕地面积')['templateRuns'][0]
        self.assertIn('基期为零',result['answer'])
        self.assertEqual(result['rows'][0]['数值'],0)

    def test_agent_scope_and_no_display(self):
        agent=find(self.s['agents'],'a3')['published'];agent['indicatorIds']='i1'
        self.assertEqual(self.ask('对比2025年和2026年呼和浩特市耕地面积')['templateRuns'][0]['rows'],[])
        agent['indicatorIds']='i_area';agent['steps']='识别指标\n示例试算'
        self.assertEqual(self.ask('对比2025年和2026年呼和浩特市耕地面积')['templateRuns'],[])

    def test_common_service_answers_use_published_guide(self):
        for q,expected in [('用地审批进度怎么查？','project_demo_1'),('数据申请需要什么材料？','用途'),('不动产登记信息如何查询？','身份核验')]:
            r=execute(self.s,self.u,'chat',dict(agentId='a1',question=q))['messages'][-1]
            self.assertIn(expected,r['text'])
            self.assertNotIn('暂未找到',r['text'])

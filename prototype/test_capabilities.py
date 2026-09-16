"""Behavioral regressions for the requirements gap remediation."""
import unittest
from copy import deepcopy
from seed import seed
from server import execute, bootstrap, user_for, find, Invalid
from capabilities import migrate, calculate, template_trial

class CapabilityWorkflows(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.u=user_for(self.s,'u1')
    def call(self,action,p,user=None):return execute(self.s,user or self.admin,action,p)
    def change(self,e,ident,values,publish=True):
        row=find(self.s[e],ident)
        saved=self.call('save',dict(entity=e,id=ident,rev=row['rev'],values=values))
        if publish:self.call('publish',dict(entity=e,id=ident,rev=saved['rev']))
        return find(self.s[e],ident)
    def ask(self,q,agent='a1',**kw):return self.call('chat',dict(question=q,agentId=agent,**kw),self.u)['messages'][-1]
    def test_prompt_publish_changes_output_not_draft(self):
        self.change('corpora','c1',dict(outputTemplate='核查通过 {{count}} {{region}} {{resources}}'),False)
        self.assertNotIn('核查通过',self.ask('地灾巡查')['text'])
        r=find(self.s['corpora'],'c1');self.call('publish',dict(entity='corpora',id='c1',rev=r['rev']))
        self.assertIn('核查通过',self.ask('地灾巡查')['text'])
    def test_steps_drive_execution_and_child_outputs(self):
        self.change('agents','a1',dict(steps='识别条件\n展示结果'))
        self.assertEqual(self.ask('地灾巡查')['resourceIds'],[])
        result=self.ask('分析耕地保护','a_team')
        self.assertTrue(result['citations']);self.assertTrue(result['indicators'])
        self.assertTrue(any(t.get('children') for t in result['trace']))
    def test_agent_cycle_rejected(self):
        self.change('agents','a2',dict(steps='调用指标智能体\n展示结果',indicatorAgentId='a3'))
        self.change('agents','a3',dict(steps='调用知识智能体\n展示结果',knowledgeAgentId='a2'))
        with self.assertRaises(Invalid):self.ask('耕地','a2')
    def test_field_alias_query_and_display_flags(self):
        fields=deepcopy(find(self.s['resources'],'r1')['fields']);fields[1].update(alias='独有标注词',query=True,display=False)
        self.change('resources','r1',dict(fields=fields))
        self.assertIn('r1',self.ask('独有标注词')['resourceIds'])
        front=bootstrap(self.s,self.u,'front');r=find(front['resources'],'r1');self.assertNotIn('area',[f['name'] for f in r['fields']])
        fields[1]['query']=False;self.change('resources','r1',dict(fields=fields))
        self.assertNotIn('r1',self.ask('独有标注词')['resourceIds'])
    def test_dictionary_value_and_template(self):
        self.change('dictionaries','dt1',dict(items='001:独有业务枚举:ENUM_TEST'))
        self.assertTrue(self.ask('ENUM_TEST')['resourceIds'])
        fields=self.call('templateApply',dict(id='mt1'))['fields'];self.assertEqual(fields[1]['name'],'area')
        with self.assertRaises(Invalid):self.change('dictionaries','dt1',dict(items='1:甲:A\n1:乙:B'))
    def test_invalid_relationship_rejected(self):
        with self.assertRaises(Invalid):self.change('resources','r1',dict(relationRules='表关联|r2|missing|area'))
        r=self.change('resources','r1',dict(relationRules='表关联|r2|region_code|region_code'))
        self.assertEqual(r['relationEdges'][0]['target'],'r2')
    def test_batch_partial_failure_and_large_document(self):
        result=self.call('importBatch',dict(files=[dict(name='长文.md',body='长文内容'*4000),dict(name='bad.txt',body='文'*70000),dict(name='重复.txt',body='第一段\n\n第一段\n\n第二段')]))
        self.assertEqual([x['status'] for x in result['items']],['完成','失败','完成'])
        self.assertEqual(result['items'][2]['cleaning']['duplicates'],1)
        self.assertNotIn(result['items'][0]['documentId'],[r['id'] for r in bootstrap(self.s,self.u,'front')['knowledge']])
    def test_graph_invalid_endpoint_and_relevant_citation(self):
        with self.assertRaises(Invalid):self.change('knowledge','k1',dict(entities='x|耕地|概念',edges='x|保护|absent'))
        self.change('knowledge','k1',dict(body='第一段讨论矿山。\n\n耕地核查必须检查补充地块质量。'))
        result=self.ask('补充地块质量','a2');self.assertIn('补充地块',result['text']);self.assertNotIn('第一段',result['text'])
    def test_knowledge_and_agent_permissions(self):
        self.change('knowledge','k1',dict(visibility='管理员'))
        self.assertNotIn('k1',[r['id'] for r in bootstrap(self.s,self.u,'front')['knowledge']])
        self.assertEqual(self.ask('什么是耕地占补平衡','a2')['citations'],[])
        self.change('agents','a1',dict(departments='地灾防治处'))
        with self.assertRaises(Invalid):self.ask('地灾')
    def test_table_formula_trends_and_permission(self):
        r=find(self.s['indicators'],'i_area');self.assertEqual(calculate(self.s,r,self.u,dict(region='呼和浩特市',period='2026年'))['value'],400)
        self.change('resources','r2',dict(dataRows='period,region,area,target\n2026年,呼和浩特市,210,420\n2025年,呼和浩特市,105,420'))
        rate=calculate(self.s,find(self.s['indicators'],'i_rate'),self.u,dict(region='呼和浩特市',period='2026年'));self.assertEqual(rate['value'],50)
        compare=self.call('indicatorCompare',dict(id='i_rate',regions='呼和浩特市',periods='2025年,2026年'))
        self.assertEqual(compare['rows'][1]['change'],100)
        self.change('resources','r2',dict(access='可申请'))
        with self.assertRaises(Invalid):calculate(self.s,find(self.s['indicators'],'i_rate'),self.u)
    def test_missing_field_cycle_and_division(self):
        with self.assertRaises(Invalid):self.change('indicators','i_area',dict(field='missing'))
        with self.assertRaises(Invalid):self.change('indicators','i_rate',dict(expression='i_rate + 1'))
        with self.assertRaises(Invalid):self.change('indicators','i_rate',dict(expression='i_area / 0'))
        with self.assertRaises(Invalid):self.change('indicators','i_rate',dict(expression='__import__("os")'))
    def test_sql_and_api_execution(self):
        r=template_trial(self.s,self.u,find(self.s['corpora'],'c3'),dict(region='呼和浩特市'))
        self.assertEqual(r['rows'][0]['total_area'],750)
        api=template_trial(self.s,self.u,find(self.s['corpora'],'c_api'),dict(question='耕地',region='全区'));self.assertEqual(len(api['rows']),2)
        bad=deepcopy(find(self.s['corpora'],'c3'));bad['body']='DELETE FROM demo_cropland'
        with self.assertRaises(Invalid):template_trial(self.s,self.u,bad,{})
    def test_evaluation_not_training_leak_and_no_session_writes(self):
        self.change('corpora','c2',dict(answer='此标准答案只在样例里',expectedAnswer='此标准答案只在样例里'))
        r=self.call('evaluate',dict(agentId='a1',caseIds=['c2']))
        self.assertEqual(r['passed'],0);self.assertEqual(self.s['sessions'],[])
        self.assertTrue(self.call('evaluationExport',{})['count'])
    def test_regression_detects_draft_difference(self):
        self.change('corpora','c2',dict(expectedAnswer='回归标记',expectedResources='',resourceIds=''))
        self.change('corpora','c1',dict(outputTemplate='回归标记 {{count}}'),False)
        r=self.call('evaluate',dict(agentId='a1',caseIds=['c2']))
        self.assertEqual([x['status'] for x in r['results']],['失败','通过'])
    def test_memory_handoff_explicit_override_and_isolation(self):
        first=self.call('chat',dict(question='包头市地灾',agentId='a1'),self.u)
        next_session=self.call('chat',dict(question='继续上次任务',agentId='a1'),self.u)
        self.assertNotEqual(first['id'],next_session['id']);self.assertEqual(next_session['context']['region'],'包头市')
        third=self.call('chat',dict(question='接续但只看赤峰市',agentId='a1',resumeFrom=first['id']),self.u)
        self.assertEqual(third['context']['region'],'赤峰市')
        with self.assertRaises(Invalid):self.call('chat',dict(question='接续',agentId='a1',resumeFrom=first['id']),user_for(self.s,'u2'))
        m=find(self.s['memories'],'u1');self.assertEqual(len(m['facts']),3)
    def test_manual_summary_and_skill_used(self):
        self.call('preferences',dict(userId='u1',rev=1,region='全区',domain='耕地',detail='简洁',summary='关注包头市地灾',enabled=True,skill='入门'),self.u)
        result=self.ask('继续查相关资源');self.assertEqual(result['context']['region'],'包头市');self.assertIn('业务说明',result['text'])
    def test_feedback_to_metadata_and_memory(self):
        sess=self.call('chat',dict(question='地灾巡查',agentId='a1'),self.u)
        f=self.call('feedback',dict(sessionId=sess['id'],messageId=sess['messages'][-1]['id'],note='需要新的标注'),self.u)
        d=self.call('feedbackDraft',dict(id=f['id'],kind='metadata',targetId='r1',text='反馈新别名'));self.call('feedbackApply',dict(id=d['id']))
        self.assertEqual(find(self.s['resources'],'r1')['status'],'草稿');self.assertNotIn('r1',self.ask('反馈新别名')['resourceIds'])
        d=self.call('feedbackDraft',dict(id=f['id'],kind='memory',text='关注包头市地灾'));self.call('feedbackApply',dict(id=d['id']))
        self.assertEqual(find(self.s['memories'],'u1')['summary'],'关注包头市地灾')
    def test_migration_preserves_history_and_idempotence(self):
        s=deepcopy(self.s);s.pop('schemaVersion');s['applications'].append({'id':'retained'});s['resources'][0]['aliases']='自定义别名'
        migrate(s);before=deepcopy(s);migrate(s);self.assertEqual(s,before);self.assertEqual(s['applications'][0]['id'],'retained');self.assertEqual(s['resources'][0]['aliases'],'自定义别名')
    def test_row_scope_and_private_indicator_config(self):
        other=user_for(self.s,'u2')
        with self.assertRaises(Invalid):calculate(self.s,find(self.s['indicators'],'i_area'),other,dict(region='包头市',period='2026年'))
        r=calculate(self.s,find(self.s['indicators'],'i_area'),other,dict(region='全区',period='2026年'))
        self.assertEqual(r['value'],400)
        result=template_trial(self.s,other,find(self.s['corpora'],'c3'),dict(region='包头市'))
        self.assertIsNone(result['rows'][0]['total_area'])
        self.assertNotIn('values',find(bootstrap(self.s,other,'front')['indicators'],'i1'))
    def test_draft_name_not_in_published_answer(self):
        self.change('resources','r1',dict(name='未发布的资源名称'),False)
        self.assertNotIn('未发布的资源名称',self.ask('地灾巡查')['text'])
    def test_prompt_unknown_output_variable_rejected(self):
        with self.assertRaises(Invalid):self.change('corpora','c1',dict(outputTemplate='{{unknown}}'))

    def test_versioned_interface_trace(self):
        r=self.call('invoke',dict(apiVersion='v1',agentId='a1',question='地灾巡查'),self.u)
        self.assertEqual(r['traceId'],self.s['calls'][-1]['id']);self.assertTrue(r['message']['trace'])
        with self.assertRaises(Invalid):self.call('invoke',dict(apiVersion='v2'),self.u)

if __name__=='__main__':unittest.main()

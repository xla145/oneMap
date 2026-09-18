import json
import os
import unittest
from copy import deepcopy
from unittest.mock import patch, MagicMock
from urllib.error import URLError
from seed import seed
from server import bootstrap, execute, user_for
import capabilities as cap
import map_ai as ai


class MapAITest(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.u=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin')
        self.env=patch.dict(os.environ,{'MAP_AI_PLANNER_URL':''});self.env.start();self.addCleanup(self.env.stop)
        self.context={'sceneId':'nmg-reference-demo'}

    def call(self,op='ask',user=None,**p):
        if op=='ask':p.setdefault('context',self.context)
        return execute(self.s,user or self.admin,'integration.ai.'+op,p)

    def test_explicit_demo_mode_never_calls_model(self):
        with patch.dict(os.environ,{'MAP_AI_PLANNER_URL':'https://planner.example/query'}), patch.object(ai,'build_opener') as gateway:
            r=self.call(question='查询永久基本农田',mode='demo')
            self.assertEqual(r['mode'],'演示规则模式')
            self.assertGreater(r['total'],0)
            gateway.assert_not_called()

    def test_model_mode_requires_configuration_and_valid_mode(self):
        self.assertFalse(self.call(op='capabilities')['modelConfigured'])
        for mode in ['model','invalid']:
            with self.subTest(mode=mode), self.assertRaises(cap.Invalid):
                self.call(question='查询永久基本农田',mode=mode)
        self.assertEqual(ai.store(self.s),[])

    def test_scope_is_returned_for_map_and_followup(self):
        polygon={'type':'Polygon','coordinates':[[[111.7,40.8],[111.701,40.8],[111.701,40.801],[111.7,40.8]]]}
        r=self.call(question='查询范围内的建设用地',mode='demo',context={**self.context,'geometry':polygon})
        self.assertEqual(r['scope']['type'],'Polygon')
        next_result=self.call(question='按旗县统计',mode='demo',previousId=r['queryId'],context={**self.context,'geometry':r['scope']})
        self.assertEqual(next_result['total'],r['total'])
        self.assertEqual(sum(g['count'] for g in next_result['statistics']),r['total'])

    def test_real_sql_filter_and_units(self):
        r=self.call(question='查询呼和浩特市的永久基本农田')
        runtime,_,rows,_=ai.dataset(self.s,self.admin,self.context)
        expected=[x for x in rows if x['layer_id']=='nmg:primeFarmland' and x['region']=='呼和浩特市']
        self.assertEqual(r['total'],len(expected));self.assertGreater(r['total'],0)
        self.assertAlmostEqual(r['areaHa'],sum(x['area_ha'] or 0 for x in expected))
        feature=next(l for l in runtime['config']['layers'] if l['id']=='nmg:primeFarmland')['features'][0]
        normalized=next(x for x in rows if x['originalId']==str(feature['id']) and x['layer_id']=='nmg:primeFarmland')
        self.assertEqual(feature['unit'],'亩');self.assertAlmostEqual(normalized['area_ha'],feature['area']/15)
        self.assertIn('FROM map_features',r['sql']);self.assertNotIn('呼和浩特',r['sql'])
        self.assertEqual(r['loaded'],r['total']);self.assertIn('演示数据',r['summary'])

    def test_followup_and_grouping(self):
        first=self.call(question='查询建设用地')
        second=self.call(question='只看未审批的',previousId=first['queryId'])
        self.assertLess(second['total'],first['total']);self.assertGreater(second['total'],0)
        self.assertTrue(all(x['approval'] in ['待报批','未报批','未审批','待审批'] for x in second['rows']))
        grouped=self.call(question='按旗县统计',previousId=second['queryId'])
        self.assertEqual(sum(x['count'] for x in grouped['statistics']),second['total'])
        changed=self.call(question='换成2025年',previousId=second['queryId'])
        self.assertTrue(all(x['year']==2025 for x in changed['rows']))

    def test_area_negation_and_clarification(self):
        r=self.call(question='查询面积不超过20亩的建设用地')
        self.assertIn('"area_ha" <= ?',r['sql'])
        for q in ['查询北京市的建设用地','查询违法建设用地','查询建设用地投资金额','查询已审批建设用地','查询20亩以下的建设用地','查询2025年之前的建设用地','查询建设用地负责人为张三']:
            with self.subTest(q=q):self.assertEqual(self.call(question=q)['status'],'clarification')

    def test_risk_alias_and_polygon_limit(self):
        r=self.call(question='查询高风险区')
        self.assertGreater(r['total'],0)
        self.assertTrue(all(x['risk'] in ['高','高风险','高风险区','高易发区'] for x in r['rows']))
        polygon={'type':'Polygon','coordinates':[[[111.7,40.8],[111.701,40.8],[111.701,40.801],[111.7,40.8]]]}
        result=self.call(question='查询范围内的建设用地',context={**self.context,'geometry':polygon})
        self.assertEqual(result['status'],'completed')
        self.s['integration']['settings']['published']['maxAreaHa']=0.0001
        with self.assertRaises(cap.Invalid):self.call(question='查询范围内的建设用地',context={**self.context,'geometry':polygon})

    def test_pagination_full_total(self):
        r=self.call(question='查询全部')
        self.assertGreater(r['total'],100);self.assertEqual(len(r['rows']),100)
        page=self.call('result',id=r['queryId'],page=2)
        self.assertEqual(page['total'],r['total']);self.assertEqual(page['areaHa'],r['areaHa'])
        self.assertFalse({x['fid'] for x in page['rows']} & {x['fid'] for x in r['rows']})

    def test_permissions_and_ownership(self):
        with self.assertRaises(cap.Invalid):self.call(user=self.u,question='查询全部')
        execute(self.s,self.admin,'integration.admin.access.save',dict(id='u1',rev=0,values=dict(view=True,analyze=True)))
        r=self.call(user=self.u,question='查询全部')
        with self.assertRaises(cap.Invalid):self.call('result',id=r['queryId'])
        with self.assertRaises(cap.Invalid):self.call(question='查询全部',context={**self.context,'layerIds':['secret']})
        execute(self.s,self.admin,'integration.admin.access.save',dict(id='u1',rev=1,values=dict(view=True,analyze=False)))
        for op in ['result','history','cancel']:
            with self.subTest(op=op),self.assertRaises(cap.Invalid):self.call(op,user=self.u,id=r['queryId'])

    def test_history_fingerprint_and_cancel(self):
        r=self.call(question='查询建设用地')
        self.assertEqual(self.call('history')[0]['id'],r['queryId'])
        original=ai.dataset
        def changed(*args):
            runtime,layers,rows,_=original(*args);return runtime,layers,rows,'changed'
        with patch.object(ai,'dataset',side_effect=changed),self.assertRaises(cap.Invalid):self.call('result',id=r['queryId'])
        self.call('cancel',id=r['queryId'])
        with self.assertRaises(cap.Invalid):self.call('result',id=r['queryId'])
        self.assertEqual(self.call('history'),[])

    def test_parameter_injection_and_plan_rejection(self):
        _,layers,rows,_=ai.dataset(self.s,self.admin,self.context)
        plan=ai.valid_plan(dict(filters=[dict(field='name',op='eq',value="'; DROP TABLE map_features;--")]),layers)
        r=ai.run(rows,plan,None);self.assertEqual(r['total'],0);self.assertNotIn('DROP',r['sql'])
        for plan in [dict(sql='DROP TABLE map_features'),dict(filters=[dict(field='name); DROP TABLE x',op='eq',value='x')]),dict(filters=[dict(field='layer_id',op='eq',value='secret')])]:
            with self.subTest(plan=plan),self.assertRaises(cap.Invalid):ai.valid_plan(plan,layers)

    def test_spatial_scope_and_nearby(self):
        r=self.call(question='查询建设用地');g=r['mapResult']['features'][0]['geometry']
        self.assertEqual(g['type'],'Point')
        nearby=self.call(question='查询周边1公里的建设用地',context={**self.context,'geometry':g})
        self.assertGreater(nearby['total'],0);self.assertLess(nearby['total'],r['total'])
        self.assertIn('spatial_match(geometry)',nearby['sql'])
        for c,q in [(self.context,'查询范围内的建设用地'),({**self.context,'geometry':g},'查询建设用地'),({**self.context,'geometry':{'type':'Point','coordinates':[999,91]}},'周边1公里')]:
            with self.subTest(q=q,c=c),self.assertRaises(cap.Invalid):self.call(question=q,context=c)

    def test_gateway_contract_and_failure(self):
        _,layers,rows,_=ai.dataset(self.s,self.admin,self.context)
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(dict(filters=[dict(field='year',op='eq',value=2025)])).encode()
        opener=MagicMock();opener.open.return_value=response
        with patch.dict(os.environ,{'MAP_AI_PLANNER_URL':'https://planner.example/query'}),patch.object(ai,'build_opener',return_value=opener):
            r=self.call(question='查询2025年');self.assertEqual(r['mode'],'模型规划服务')
            self.assertTrue(all(x['year']==2025 for x in r['rows']))
            sent=json.loads(opener.open.call_args[0][0].data)
            self.assertIn('schema',sent);self.assertNotIn('rows',sent)
            opener.open.side_effect=URLError('offline')
            with self.assertRaises(cap.Invalid) as error:self.call(question='查询全部')
            self.assertEqual(error.exception.status,502)

    def test_merge_rechecks_and_preserves_concurrent_changes(self):
        r=self.call(question='查询建设用地');row=deepcopy(ai.own(self.s,self.admin,r['queryId']))
        current=deepcopy(self.s);current['integration']['aiQueries']=[];current['unrelated']='concurrent update'
        ai.save_query(current,self.admin,row)
        self.assertEqual(current['unrelated'],'concurrent update');self.assertEqual(len(ai.store(current)),1)
        row['fingerprint']='old'
        with self.assertRaises(cap.Invalid):ai.save_query(current,self.admin,row)

if __name__=='__main__':unittest.main()

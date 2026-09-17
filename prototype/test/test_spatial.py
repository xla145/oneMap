import unittest
from seed import seed
from server import execute, bootstrap, user_for
from capabilities import Invalid
from spatial import valid_ring, intersects, contained


def polygon(ring):
    return {'type':'Polygon','coordinates':[ring]}


class GeometryChecks(unittest.TestCase):
    def test_crossing_containment_touching_and_disjoint(self):
        a=[[0,0],[2,0],[2,2],[0,2],[0,0]]
        self.assertTrue(intersects(a,[[2,0],[3,0],[3,1],[2,1],[2,0]]))
        self.assertFalse(intersects(a,[[3,0],[4,0],[4,1],[3,1],[3,0]]))
        self.assertTrue(contained([[.5,.5],[1,.5],[1,1],[.5,1],[.5,.5]],a))
        self.assertTrue(intersects(a,[[-1,.8],[3,.8],[3,1.2],[-1,1.2],[-1,.8]]))
        self.assertFalse(contained(a,[[-1,.8],[3,.8],[3,1.2],[-1,1.2],[-1,.8]]))
        # Concave notch: vertices alone cannot establish polygon containment.
        notch=[[0,0],[4,0],[4,4],[3,4],[3,1],[1,1],[1,4],[0,4],[0,0]]
        self.assertFalse(contained([[.5,.5],[3.5,.5],[3.5,3.5],[.5,3.5],[.5,.5]],notch))

    def test_invalid_geometry(self):
        for ring in [[[0,0],[2,2],[0,2],[2,0],[0,0]],[[0,0],[1,1],[2,2],[0,0]],[[0,0],[1,0],[1,float('nan')],[0,0]],[[0,0],[1,0],[1,1],[0,1]]]:
            with self.subTest(ring=ring), self.assertRaises(Invalid):valid_ring(polygon(ring))


class SpatialWorkflows(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.u=user_for(self.s,'u1')
        self.context={'mode':'region','region':'全区','period':'全部时间','crs':'EPSG:4490','sceneId':'scene_cropland','layerIds':['layer_demo']}

    def ask(self,q='统计耕地图斑面积',context=None,session=None,user=None):
        return execute(self.s,user or self.u,'chat',dict(agentId='a1',question=q,spatialContext=context if context is not None else self.context,sessionId=session,context={'region':(context or self.context)['region'],'period':(context or self.context).get('period','全部时间')}))

    def test_region_statistics_and_multi_turn(self):
        a=self.ask();r=a['messages'][-1]['analysisResult']
        self.assertEqual(r['statistics']['count'],3)
        self.assertEqual(r['statistics']['attributeArea'],400)
        b=self.ask('只看包头市',session=a['id'])
        self.assertEqual(b['messages'][-1]['analysisResult']['statistics']['count'],1)
        self.assertEqual(b['messages'][-3]['analysisResult']['statistics']['count'],3)

    def test_partial_intersection_does_not_sum_whole_feature_area(self):
        c={**self.context,'mode':'polygon','geometry':polygon([[109.9,40.55],[110.2,40.55],[110.2,40.7],[109.9,40.7],[109.9,40.55]])}
        result=self.ask(context=c)['messages'][-1]['analysisResult']
        self.assertEqual(result['statistics'],dict(count=1,fullCount=0,partialCount=1,attributeArea=None,unit='公顷'))
        self.assertIn('不计算交叠面积',result['caliber'])

    def test_feature_scope_and_region_conflict(self):
        c={**self.context,'mode':'features','featureRefs':[{'layerId':'layer_demo','id':'r_scene_demo_0'}]}
        self.assertEqual(self.ask(context=c)['messages'][-1]['analysisResult']['statistics']['count'],1)
        with self.assertRaises(Invalid):self.ask('只看呼和浩特市',context=c)
        c['featureRefs'][0]['id']='forged'
        with self.assertRaises(Invalid):self.ask(context=c)

    def test_permission_filter_and_history_revocation(self):
        c={**self.context,'layerIds':['layer_demo','layer_farmland']}
        a=self.ask(context=c);result=a['messages'][-1]['analysisResult']
        self.assertTrue(result['partial']);self.assertEqual(len(result['features']),3)
        self.assertTrue(all(f['resourceId']=='r_scene_demo' for f in result['features']))
        resource=next(r for r in self.s['resources'] if r['id']=='r_scene_demo')
        resource['published']['access']='可申请'
        saved=bootstrap(self.s,self.u,'front')['sessions'][0]['messages'][-1]['analysisResult']
        self.assertEqual(saved['status'],'unavailable');self.assertEqual(saved['features'],[])
        self.assertIsNone(saved['statistics'])

    def test_user_scope_agent_disable_and_old_client_compatibility(self):
        other=user_for(self.s,'u2')
        with self.assertRaises(Invalid):self.ask(user=other)
        c={**self.context,'region':'呼和浩特市'}
        self.assertEqual(self.ask(context=c,user=other)['messages'][-1]['analysisResult']['statistics']['count'],1)
        a=next(a for a in self.s['agents'] if a['id']=='a1');a['published']['mapEnabled']=False
        with self.assertRaises(Invalid):self.ask()
        plain=execute(self.s,self.u,'chat',{'agentId':'a1','question':'查找耕地资源'})
        self.assertNotIn('analysisResult',plain['messages'][-1])

    def test_unsupported_time_and_geometry_are_explicit(self):
        r=self.ask(context={**self.context,'period':'2025年'})['messages'][-1]['analysisResult']
        self.assertEqual(r['status'],'no_data');self.assertEqual(r['features'],[])
        r=self.ask('计算选区交叠面积')['messages'][-1]['analysisResult']
        self.assertEqual(r['status'],'unsupported')
        with self.assertRaises(Invalid):self.ask(context={**self.context,'mode':'polygon','geometry':polygon([[0,0],[2,2],[0,2],[2,0],[0,0]])})

    def test_spatial_scope_does_not_use_administrative_indicator(self):
        c={**self.context,'mode':'features','featureRefs':[{'layerId':'layer_demo','id':'r_scene_demo_0'}]}
        result=execute(self.s,self.u,'chat',dict(agentId='a3',question='分析耕地指标和图斑面积',spatialContext=c))['messages'][-1]
        self.assertEqual(result['indicators'],[])
        self.assertEqual(result['analysisResult']['statistics']['attributeArea'],128.6)


if __name__=='__main__':unittest.main()

import unittest
from copy import deepcopy
from datetime import date, timedelta
from seed import seed
from server import execute, bootstrap, user_for
from capabilities import Invalid
import portal_management as pm
import centers
import prototype.test.tool_center as tc


class ToolCenterTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin')

    def run_tool(self,engine,p):return centers.run_tool(self.s,{'engine':engine},p)

    def test_cgcs2000_projection_round_trip_and_text_inputs(self):
        result=self.run_tool('coordinate',{'source':'EPSG:4490','target':'EPSG:4546','geometry':'POINT (111.7 40.8)'})
        restored=self.run_tool('coordinate',{'source':'EPSG:4546','target':'EPSG:4490','geometry':result['wkt']})
        self.assertAlmostEqual(restored['x'],111.7,places=7);self.assertAlmostEqual(restored['y'],40.8,places=7)
        self.assertFalse(restored['approximateDatum'])
        approximate=self.run_tool('coordinate',{'source':'EPSG:4490','target':'EPSG:4326','x':111.7,'y':40.8})
        self.assertTrue(approximate['approximateDatum']);self.assertIn('近似',approximate['note'])
        self.assertIn('近似',self.run_tool('area',{'geometry':tc.POLYGON,'crs':'EPSG:4490'})['coordinateNote'])
        text='J1,111.7,40.75\nJ2,111.76,40.75\nJ3,111.76,40.81\nJ4,111.7,40.81'
        area=self.run_tool('area',{'geometry':text})
        self.assertGreater(area['areaSquareMeters'],100000)
        self.assertEqual(tc.geometry('POLYGON ((0 0,1 0,1 1,0 0))').geom_type,'Polygon')
        for payload in [{'x':999,'y':40},{'source':'EPSG:9999','x':1,'y':2},{'geometry':'POINT (NaN 2)'}]:
            with self.assertRaises(Invalid):self.run_tool('coordinate',payload)

    def test_checks_report_missing_evidence_and_detect_errors(self):
        r=self.run_tool('spatial-check',{'geometry':tc.POLYGON});self.assertFalse(r['complete'])
        r=self.run_tool('spatial-check',{'geometry':tc.POLYGON,'boundary':tc.POLYGON,'neighbors':[tc.POLYGON]})
        self.assertTrue(r['complete']);self.assertEqual(r['checks'][-1]['detail']['neighborIndexes'],[1])
        r=self.run_tool('spatial-check',{'geometry':'POLYGON ((0 0,2 2,0 2,2 0,0 0))'})
        self.assertFalse(r['valid']);self.assertEqual(r['checks'][2]['status'],'不通过')
        r=self.run_tool('spatial-check',{'geometry':'POLYGON ((0 0,2 0,2 0,2 2,0 0))','boundary':'POLYGON ((0 0,1 0,1 1,0 0))'})
        self.assertEqual(r['checks'][3]['status'],'不通过');self.assertEqual(r['checks'][4]['status'],'不通过')

    def test_local_layer_query_by_region_coordinate_and_edit_by_name(self):
        p={'resourceId':'r3','featureId':'f1','revision':1,'geometry':tc.POLYGON,'properties':{'name':'地块一','region':'呼和浩特市'}}
        self.run_tool('spatial-store',p)
        q=self.run_tool('spatial-query',{'resourceId':'r3','coordinate':[111.72,40.77],'region':'呼和浩特市'})
        self.assertEqual(q['total'],1)
        self.assertEqual(self.run_tool('spatial-query',{'resourceId':'r3','coordinate':[0,0]})['total'],0)
        self.assertEqual(self.run_tool('spatial-query',{'resourceId':'r3','region':'包头市'})['total'],0)
        self.run_tool('spatial-edit',{'resourceId':'r3','name':'地块一','revision':2,'operation':'update','geometry':tc.POLYGON})
        self.assertEqual(self.run_tool('spatial-query',{'resourceId':'r3'})['features'][0]['properties']['region'],'呼和浩特市')
        with self.assertRaises(Invalid):self.run_tool('spatial-edit',{'resourceId':'r3','name':'地块一','revision':2,'operation':'delete'})
        self.run_tool('spatial-edit',{'resourceId':'r3','name':'地块一','revision':3,'operation':'delete'})
        self.assertEqual(self.run_tool('spatial-query',{'resourceId':'r3'})['total'],0)

    def test_permissions_apply_to_bootstrap_and_every_online_call(self):
        execute(self.s,self.admin,'portal.toolPermissions',{'rev':1,'rules':[{'role':'普通用户','category':'基础空间工具','module':'坐标转换'}]})
        self.assertNotIn('coordinate',[r['id'] for r in bootstrap(self.s,self.user,'front')['portalManagement']['tools']])
        for action in ['portal.toolCheck','portal.toolRun','portal.toolResult']:
            with self.assertRaises(Invalid):execute(self.s,self.user,action,{'id':'coordinate','payload':{'x':1,'y':2},'status':'成功'})
        self.assertIn('coordinate',[r['id'] for r in bootstrap(self.s,self.admin,'front')['portalManagement']['tools']])
        with self.assertRaises(Invalid):execute(self.s,self.user,'portal.toolPermissions',{'rev':2,'rules':[]})

    def test_application_resource_authorization_and_revocation(self):
        tool=pm.migrate(self.s)['tools'][0];tool['published']['resourceId']='r4'
        resource=next(r for r in self.s['resources'] if r['id']=='r4')
        resource['published'].update(type='工具服务',sharingPolicy='申请使用',access='可申请')
        payload={'id':'coordinate','payload':{'x':111,'y':40}}
        with self.assertRaises(Invalid):execute(self.s,self.user,'portal.toolRun',payload)
        a=execute(self.s,self.user,'apply',{'resourceIds':['r4'],'purpose':'使用空间工具核查项目','validUntil':(date.today()+timedelta(days=30)).isoformat()})
        execute(self.s,self.admin,'decide',{'id':a['id'],'rev':a['rev'],'resourceId':'r4','decision':'已通过','note':'同意业务工具使用申请'})
        self.assertIn('x',execute(self.s,self.user,'portal.toolRun',payload))
        row=next(r for r in bootstrap(self.s,self.user,'front')['portalManagement']['tools'] if r['id']=='coordinate')
        self.assertEqual(row['applicationCount'],1);self.assertEqual(row['provider'],resource['published']['source'])
        grant=self.s['grants'][-1]
        execute(self.s,self.admin,'grant.revoke',{'id':grant['id'],'rev':grant['rev'],'reason':'业务工具测试结束撤销'})
        with self.assertRaises(Invalid):execute(self.s,self.user,'portal.toolRun',payload)

    def test_metadata_and_screenshot_change_requires_review_again(self):
        r=pm.migrate(self.s)['tools'][0]
        r=execute(self.s,self.admin,'portal.save',{'entity':'tools','id':r['id'],'rev':r['rev'],'values':{'region':'包头市','directoryId':'dir-tool','interfaceType':'REST','module':'坐标转换'}})
        execute(self.s,self.admin,'centers.tool.submit',{'id':r['id'],'rev':r['rev']})
        current=pm.find(pm.migrate(self.s)['tools'],r['id'])
        execute(self.s,self.admin,'centers.tool.review',{'id':r['id'],'rev':current['rev'],'decision':'通过','note':'审核配置内容符合要求'})
        execute(self.s,self.admin,'portal.publish',{'entity':'tools','id':r['id'],'rev':current['rev']})
        row=next(x for x in bootstrap(self.s,self.user,'front')['portalManagement']['tools'] if x['id']==r['id'])
        self.assertEqual(row['directoryName'],'工具服务');self.assertEqual(row['region'],'包头市');self.assertTrue(row['contract']['parameters'])
        signature=centers.tool_signature(current);current['screenshot']='different';self.assertNotEqual(signature,centers.tool_signature(current))
        with self.assertRaises(Invalid):execute(self.s,self.admin,'portal.save',{'entity':'tools','id':current['id'],'rev':current['rev'],'values':{'screenshot':'data:image/svg+xml;base64,PHN2Zz4='}})


if __name__=='__main__':unittest.main()

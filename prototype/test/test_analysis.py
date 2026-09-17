import json
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import box, Polygon, MultiPolygon
from shapely.ops import transform
from capabilities import Invalid
import analysis_engine as e
import analysis_jobs as j

class AnalysisTests(unittest.TestCase):
    def test_conflict_clear_and_deduplicated_area(self):
        r=e.analyze(e.catalog()['sample'],e.catalog())
        self.assertEqual([p['state'] for p in r['parcels']],['发现冲突','未发现所选规则冲突'])
        self.assertLess(r['parcels'][0]['conflictArea'],sum(x['area'] or 0 for x in r['rows'][:3]))
    def test_holes_and_multipolygon(self):
        outer=box(111.64,40.69,111.74,40.80);hole=box(111.65,40.7,111.73,40.79)
        poly=Polygon(outer.exterior.coords,[hole.exterior.coords])
        value=e.feature(MultiPolygon([poly,box(111.82,40.86,111.84,40.88)]))
        normalized=e.normalize(json.loads(json.dumps(value)),'EPSG:4326')
        self.assertAlmostEqual(e.analyze(normalized,e.catalog())['rows'][0]['area'],0)
    def test_invalid_geometries(self):
        for value in [[],{'type':'FeatureCollection','features':[]},[[0,0],[1,1],[1,0],[0,1],[0,0]],[[0,0],[1,0],[1,1]],[[0,0],[1,0],[float('nan'),1],[0,0]],{'type':'Point','coordinates':[111,40]}]:
            with self.subTest(value=value),self.assertRaises(Invalid):e.normalize(value,'EPSG:4326')
    def test_coverage_missing_expired_denied(self):
        for field,value in [('geometry',None),('authorized',False),('current',False)]:
            catalog=e.catalog();catalog['layers'][0][field]=value
            self.assertEqual(e.analyze(e.catalog()['sample'],catalog)['state'],'无法判定')
        outside={'type':'FeatureCollection','features':[e.feature(box(112,41,112.1,41.1),id='out',name='范围外')]}
        self.assertEqual(e.analyze(outside,e.catalog())['state'],'无法判定')
    def test_touch_is_review(self):
        data={'type':'FeatureCollection','features':[e.feature(box(111.63,40.71,111.65,40.73),id='touch',name='接触')]}
        self.assertEqual(e.analyze(data,e.catalog())['state'],'需人工复核')
    def test_spatial_operations_and_empty_result(self):
        data=e.catalog()['sample']
        self.assertTrue(e.spatial_tool(data,'intersection')['empty'])
        union=e.spatial_tool(data,'union')['areaSquareMeters']
        self.assertGreater(e.spatial_tool(data,'buffer',100)['areaSquareMeters'],union)
        self.assertEqual(e.spatial_tool(data,'area')['areaSquareMeters'],union)
        self.assertLess(e.spatial_tool(data,'difference')['areaSquareMeters'],union)
        with self.assertRaises(Invalid):e.spatial_tool(data,'buffer',float('inf'))
    def test_projected_input(self):
        from pyproj import Transformer
        geom=box(111.82,40.86,111.84,40.88)
        projected=transform(Transformer.from_crs(4326,3857,always_xy=True).transform,geom)
        normalized=e.normalize(json.loads(json.dumps(e.feature(projected))),'EPSG:3857')
        self.assertEqual(e.analyze(normalized,e.catalog())['state'],'未发现所选规则冲突')

class JobsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'test.sqlite3';j.initialize(self.db)
    def tearDown(self):self.tmp.cleanup()
    def call(self,a,p={},user='u1'):return j.dispatch(self.db,user,'analysis.'+a,p)
    def create(self):
        source=self.call('input',{'geometry':json.dumps(e.catalog()['sample']),'crs':'EPSG:4326'})
        p={'inputId':source['id'],'requestKey':'test-key','name':'<script>alert(1)</script>'}
        return self.call('create',p),p
    def test_execution_exports_idempotency_and_ownership(self):
        job,p=self.create();self.assertEqual(job,self.call('create',p))
        with self.assertRaises(Invalid):self.call('create',{**p,'name':'different'})
        for action in ['get','cancel','export']:
            with self.assertRaises(Invalid):self.call(action,{'id':job['id'],'format':'html'},user='u2')
        with self.assertRaises(Invalid):self.call('create',p,user='u2')
        self.assertTrue(j.work_once(self.db));r=self.call('get',job)
        self.assertEqual(r['status'],'成功');self.assertEqual(r['result']['state'],'发现冲突')
        report=self.call('export',{**job,'format':'html'})['content']
        self.assertNotIn('<script>',report);self.assertIn('<svg',report);self.assertIn('&lt;script&gt;',report)
        self.assertEqual(json.loads(self.call('export',{**job,'format':'geojson'})['content']),r['result']['conflicts'])
        self.assertIn('示例生态红线',self.call('export',{**job,'format':'csv'})['content'])
        self.assertEqual(self.call('list',user='u2'),[])
    def test_cancel_and_restart(self):
        job,p=self.create();self.call('cancel',job);self.assertFalse(j.work_once(self.db))
        self.assertEqual(self.call('get',job)['status'],'已取消')
        new=self.call('create',{**p,'requestKey':'second'});j.initialize(self.db);j.work_once(self.db)
        self.assertEqual(self.call('get',new)['status'],'成功')

if __name__=='__main__':unittest.main()

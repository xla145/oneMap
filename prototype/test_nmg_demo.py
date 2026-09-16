import unittest
from seed import seed
from server import bootstrap,execute,user_for
import capabilities as cap
import integration_results as results

class NmgReferenceTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');bootstrap(self.s,self.admin,'admin')
    def runtime(self):
        return execute(self.s,self.admin,'integration.results.map.runtime',{'sceneId':'nmg-reference-demo'})
    def test_extracted_geometry_types_and_counts(self):
        runtime=self.runtime();layers=runtime['config']['layers']
        self.assertEqual(len(layers),28)
        self.assertEqual(sum(len(l['features']) for l in layers),1176)
        self.assertEqual({f['geometry']['type'] for l in layers for f in l['features']},{'Point','LineString','Polygon'})
        self.assertEqual(len(runtime['reference']['series']['indicators']),12)
    def test_reference_requires_view_and_rejects_overlay_injection(self):
        with self.assertRaises(cap.Invalid):results.map_runtime(self.s,user_for(self.s,'u1'),{'sceneId':'nmg-reference-demo'})
        with self.assertRaises(cap.Invalid):results.map_runtime(self.s,self.admin,{'sceneId':'nmg-reference-demo','extraLayers':[{'resourceId':'r1'}]})
    def test_point_line_polygon_spatial_query(self):
        runtime=self.runtime()
        for kind in ['Point','LineString','Polygon']:
            layer=next(l for l in runtime['config']['layers'] if l['features'][0]['geometry']['type']==kind)
            feature=layer['features'][0];g=feature['geometry'];point=g['coordinates'] if kind=='Point' else g['coordinates'][0] if kind=='LineString' else g['coordinates'][0][0]
            result=execute(self.s,self.admin,'integration.map.query',dict(sceneId=runtime['id'],mode='penetrate',layerIds=[layer['id']],x=point[0],y=point[1]))
            self.assertIn(feature['id'],[r['id'] for r in result['rows']])
    def test_reference_bookmark_roundtrip_and_runtime_isolation(self):
        runtime=self.runtime();ids=[runtime['config']['layers'][0]['id']]
        row=execute(self.s,self.admin,'integration.bookmark.save',dict(values=dict(name='参考地图',sceneId=runtime['id'],layerIds=ids,view=dict(center=[111,44],resolution=.04,rotation=0,basemapId='demo-img'))))
        restored=execute(self.s,self.admin,'integration.bookmark.restore',dict(id=row['id']))
        self.assertEqual(restored['layerIds'],ids)
        runtime['config']['layers'].clear()
        self.assertEqual(len(self.runtime()['config']['layers']),28)

if __name__=='__main__':unittest.main()

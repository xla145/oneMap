import unittest,tempfile,sqlite3,json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from seed import seed
from server import bootstrap,execute,user_for
import integration_results as r
import integration as ig
import analysis_jobs as jobs
import analysis_engine as engine
import capabilities as cap

class ResultCoverage(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.u=user_for(self.s,'u1');bootstrap(self.s,self.admin,'admin')
    def grant(self):execute(self.s,self.admin,'integration.admin.access.save',dict(id='u1',rev=0,values=dict(view=True,analyze=False)))
    def test_result_projection_requires_view_and_reads_published_metadata(self):
        self.assertIsNone(r.bootstrap(self.s,self.u))
        with self.assertRaises(cap.Invalid):r.stats(self.s,self.u,{})
        self.grant();data=r.bootstrap(self.s,self.u);self.assertTrue(data['tools'])
        tool=self.s['portalAdmin']['tools'][0] if 'portalAdmin' in self.s else None
        app=self.s['platform']['apps'][0];app['description']='秘密草稿';app['owner']='草稿单位'
        self.assertNotIn('秘密草稿',json.dumps(r.bootstrap(self.s,self.admin),ensure_ascii=False))
        scenes=r.bootstrap(self.s,self.admin)['scenes'];self.assertTrue(any(x['theme']=='耕地保护和国土绿化空间' for x in scenes))
        self.assertTrue(any(not x['theme'] for x in scenes))
    def test_catalog_metadata_and_scene_references(self):
        layer=next(x for x in r.bootstrap(self.s,self.admin)['layers'] if x['scenes']);key=layer['resourceId']
        self.assertTrue(layer['scenes'])
        execute(self.s,self.admin,'integration.layer.metadata',dict(id=key,rev=0,values=dict(theme='自然资源/耕地/现状',department='登记部门',cities=['呼和浩特市','包头市'],hotspots=['耕地保护'],dataKind='矢量',sourceScope='厅内',collectionState='已接入',capacityBytes=1024)))
        row=next(x for x in r.bootstrap(self.s,self.admin)['layers'] if x['resourceId']==key)
        self.assertEqual(row['layerTheme'],'自然资源/耕地/现状');self.assertEqual(row['cities'],['呼和浩特市','包头市']);self.assertEqual(row['hotspots'],['耕地保护'])
        result=r.stats(self.s,self.admin,dict(domain='layers'));self.assertEqual(result['capacityBytes'],1024);self.assertEqual(result['capacityKnown'],1)
        with self.assertRaises(cap.Invalid):execute(self.s,self.u,'integration.layer.metadata',dict(id=key,rev=1,values={}))
    def test_system_visibility_revocation_and_main_record_unchanged(self):
        self.grant();system=self.s['centers']['systems'][0];before=deepcopy(system);system['entry']='https://example.org/system'
        arg=dict(id=system['id'],rev=0,values=dict(theme=ig.THEMES[0],roles=['业务用户'],enabled=True,provider='业务部门'))
        execute(self.s,self.admin,'integration.results.system.save',arg)
        self.assertEqual(len(r.bootstrap(self.s,self.u)['systems']),1)
        self.assertTrue(execute(self.s,self.u,'integration.results.system.open',dict(id=system['id']))['external'])
        execute(self.s,self.admin,'integration.results.system.save',{**arg,'rev':1,'values':{**arg['values'],'enabled':False}})
        with self.assertRaises(cap.Invalid):execute(self.s,self.u,'integration.results.system.open',dict(id=system['id']))
        self.assertEqual(system,{**before,'entry':'https://example.org/system'})
    def test_stats_separate_events_and_apply_filters(self):
        tool=r.bootstrap(self.s,self.admin)['tools'][0];events=self.s['integration']['events'];date=ig.c.now()
        for kind,user,department in [('open','u1','A'),('call','u1','A'),('call','u2','B'),('search','u1','A')]:events.append(dict(id=str(len(events)),kind=kind,userId=user,department=department,target=tool['id'],at=date))
        m=r.stats(self.s,self.admin,dict(domain='tools',department='A',period='month',resource=tool['id']))
        self.assertEqual(m['cumulative']['calls'],2);self.assertEqual(m['filtered']['calls'],1);self.assertEqual(m['filtered']['opens'],1);self.assertEqual(m['filtered']['users'],1);self.assertEqual(m['rankings'][0]['count'],1)
        with self.assertRaises(cap.Invalid):r.stats(self.s,self.admin,dict(domain='tools',resource='secret:missing'))
        with self.assertRaises(cap.Invalid):r.stats(self.s,self.admin,dict(start='2026-12-01',end='2026-01-01'))
    def test_query_records_unique_authorized_resources_only(self):
        execute(self.s,self.admin,'integration.map.query',dict(sceneId='scene_cropland',mode='point',x=111.7,y=40.8))
        events=[e for e in self.s['integration']['events'] if e['kind']=='layerQuery']
        self.assertTrue(events);self.assertEqual(len(events),len({e['target'] for e in events}))
        m=r.stats(self.s,self.admin,dict(domain='layers'));self.assertEqual(m['cumulative']['queries'],len(events));self.assertEqual(m['cumulative']['calls'],0)
        self.grant();self.s['resources'][0]['published']['visibility']='管理员'
        hidden=self.s['resources'][0]['id'];projection=r.bootstrap(self.s,self.u)
        self.assertNotIn(hidden,[x['resourceId'] for x in projection['layers']])
    def test_bookmark_restoration_drops_removed_layers(self):
        from platform_domain import scene_runtime
        scene=scene_runtime(self.s,self.admin,dict(id='scene_cropland'));layer=scene['config']['layers'][0]
        saved=execute(self.s,self.admin,'integration.bookmark.save',dict(values=dict(name='个人地图',sceneId=scene['id'],layerIds=[layer['id']],view=dict(center=[111.7,40.8],resolution=.01,rotation=0,basemapId='demo-img'))))
        with self.assertRaises(cap.Invalid):execute(self.s,self.u,'integration.bookmark.restore',dict(id=saved['id']))
        # Recheck live runtime rather than trusting the saved layer list.
        with patch('platform_domain.scene_runtime',return_value={**scene,'config':{**scene['config'],'layers':[]}}):
            restored=execute(self.s,self.admin,'integration.bookmark.restore',dict(id=saved['id']))
        self.assertEqual(restored['layerIds'],[]);self.assertEqual(restored['removedCount'],1)

    def extra_scene(self):
        source=next(a for a in self.s['platform']['apps'] if a.get('published',{}).get('targetId')=='scene_cropland')
        app=deepcopy(source);app['id']='extra-app';app['published']['id']=app['id'];app['published']['targetId']='extra-scene'
        scene=deepcopy(app['published']['targetSnapshot']);scene['id']='extra-scene';scene['name']='额外场景'
        layer=deepcopy(scene['config']['layers'][0]);layer.update(id='extra-layer',resourceId='r3',name='额外图层')
        scene['config']['layers']=[layer];app['published']['targetSnapshot']=scene
        self.s['platform']['scenes'].append(deepcopy(scene));self.s['platform']['apps'].append(app)
        return dict(resourceId='r3',sceneId='extra-scene'),app

    def test_overlay_query_bookmark_and_revoked_source(self):
        ref,app=self.extra_scene();args=dict(sceneId='scene_cropland',extraLayers=[ref,ref])
        runtime=r.map_runtime(self.s,self.admin,args);self.assertEqual(runtime['extraLayers'],[ref])
        self.assertEqual(sum(l['resourceId']=='r3' for l in runtime['config']['layers']),1)
        result=execute(self.s,self.admin,'integration.map.query',dict(**args,layerIds=['overlay:r3'],mode='point',x=111.7,y=40.8))
        self.assertEqual(result['rows'][0]['layerId'],'overlay:r3')
        saved=execute(self.s,self.admin,'integration.bookmark.save',dict(values=dict(**args,name='组合',layerIds=['overlay:r3'],view=dict(center=[111.7,40.8],resolution=.01,rotation=0,basemapId='demo-img'))))
        app['listed']=False
        with self.assertRaises(cap.Invalid):r.map_runtime(self.s,self.admin,args)
        safe=r.map_runtime(self.s,self.admin,args,strict=False);self.assertEqual(safe['extraLayers'],[])
        restored=execute(self.s,self.admin,'integration.bookmark.restore',dict(id=saved['id']))
        self.assertEqual(restored['layerIds'],[]);self.assertEqual(restored['removedCount'],1)
        with self.assertRaises(cap.Invalid):execute(self.s,self.admin,'integration.map.query',dict(**args,mode='point',x=111.7,y=40.8))

    def test_runtime_cannot_accept_unpublished_or_unmounted_layer(self):
        args=dict(sceneId='scene_cropland',extraLayers=[dict(resourceId='r3',sceneId='scene_cropland')])
        with self.assertRaises(cap.Invalid):r.map_runtime(self.s,self.admin,args)
        with self.assertRaises(cap.Invalid):r.map_runtime(self.s,self.u,args)
        self.assertEqual(r.map_runtime(self.s,self.admin,args,strict=False)['droppedLayers'],1)

    def test_usage_users_match_selected_activity_and_scale_is_visible(self):
        tool=r.bootstrap(self.s,self.admin)['tools'][0]
        for kind,uid in [('open','viewer'),('call','caller'),('call','caller')]:
            self.s['integration']['events'].append(dict(kind=kind,target=tool['id'],userId=uid,department='A',at=ig.c.now()))
        calls=r.stats(self.s,self.admin,dict(domain='tools',activity='call'))
        self.assertEqual(calls['cumulative']['users'],1);self.assertEqual(calls['cumulative']['calls'],2)
        self.assertEqual(r.stats(self.s,self.admin,dict(domain='tools',activity='open'))['cumulative']['users'],1)
        m=r.stats(self.s,self.admin,dict(domain='layers'))
        self.assertEqual(m['scale']['dataTables'],len([x for x in ig.catalog(self.s,self.admin) if x['kind']=='数据库表']))
        self.assertEqual(m['scale']['unclassifiedLayers'],m['total'])

class BatchProgress(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'jobs.sqlite3';jobs.initialize(self.db)
    def tearDown(self):self.tmp.cleanup()
    def create(self):
        source=jobs.dispatch(self.db,'u1','analysis.input',dict(geometry=json.dumps(engine.catalog()['sample']),crs='EPSG:4326'))
        args=dict(inputId=source['id'],name='批量核查',requestKey='unique')
        return jobs.dispatch(self.db,'u1','analysis.create',args),args
    def test_progress_is_persisted_and_owner_scoped(self):
        job,_=self.create();self.assertEqual(jobs.dispatch(self.db,'u1','analysis.get',job)['progress']['completed'],0)
        jobs.work_once(self.db);data=jobs.dispatch(self.db,'u1','analysis.get',job)
        self.assertEqual(data['progress']['completed'],2);self.assertTrue(all(p['status']=='已完成' for p in data['progress']['parcels']))
        with self.assertRaises(cap.Invalid):jobs.dispatch(self.db,'u2','analysis.get',job)
    def test_area_rechecked_for_existing_input_and_new_input(self):
        _,args=self.create()
        with self.assertRaises(cap.Invalid):jobs.dispatch(self.db,'u1','analysis.create',{**args,'requestKey':'new'},area_limit=1)
        with self.assertRaises(cap.Invalid):jobs.dispatch(self.db,'u1','analysis.input',dict(geometry=json.dumps(engine.catalog()['sample']),crs='EPSG:4326'),area_limit=1)
    def test_running_cancellation_stops_next_parcel(self):
        job,_=self.create();original=engine.analyze
        def cancel(data,snapshot,progress_callback=None):
            jobs.dispatch(self.db,'u1','analysis.cancel',job)
            return original(data,snapshot,progress_callback)
        with patch('analysis_engine.analyze',side_effect=cancel):jobs.work_once(self.db)
        result=jobs.dispatch(self.db,'u1','analysis.get',job);self.assertEqual(result['status'],'已取消');self.assertIsNone(result['result'])

if __name__=='__main__':unittest.main()

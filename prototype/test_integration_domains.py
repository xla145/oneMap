"""Three-domain regressions: publication isolation, personal scope and admission."""
import unittest
from copy import deepcopy
from seed import seed
from server import bootstrap,execute,user_for
import integration as ig
import integration_admin as ia
import capabilities as cap

class IntegrationDomains(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.u=user_for(self.s,'u1');bootstrap(self.s,self.admin,'admin')
    def test_public_identity_not_implicitly_admitted(self):
        public=dict(self.u,id='public-new',internalAccess=False);self.s['users'].append(public)
        with self.assertRaises(cap.Invalid):bootstrap(self.s,public,'admin')
        with self.assertRaises(cap.Invalid):execute(self.s,public,'integration.workbench',{})
        self.assertTrue(bootstrap(self.s,self.u,'admin')['integration']['internalAccess'])
        self.u['internalAccess']=False
        with self.assertRaises(cap.Invalid):bootstrap(self.s,self.u,'admin')
        self.assertFalse(ia.rights(self.s,self.u)['view'])
    def test_migration_is_one_time_and_preserves_revocation(self):
        self.u['internalAccess']=False;ia.migrate(self.s)
        self.assertFalse(ia.internal_access(self.s,self.u))
        public=dict(self.u,id='later-user');public.pop('internalAccess');self.s['users'].append(public)
        ia.migrate(self.s);self.assertFalse(ia.internal_access(self.s,public))
    def test_identity_admission_is_admin_controlled_and_audited(self):
        self.u['internalAccess']=False
        result=execute(self.s,self.admin,'platform.userSave',dict(id=self.u['id'],rev=self.u['rev'],values=dict(internalAccess=True)))
        self.assertTrue(result['internalAccess'])
        current=user_for(self.s,'u1');self.assertTrue(ia.internal_access(self.s,current))
        self.assertEqual(self.s['platform']['audit'][-1]['changes']['internalAccess'],dict(before=False,after=True))
        with self.assertRaises(cap.Invalid):execute(self.s,current,'platform.userSave',dict(id=current['id'],rev=current['rev'],values=dict(internalAccess=True)))
        result=execute(self.s,self.admin,'platform.userSave',dict(id=current['id'],rev=current['rev'],values=dict(internalAccess=False)))
        with self.assertRaises(cap.Invalid):bootstrap(self.s,user_for(self.s,'u1'),'admin')
    def test_admin_resource_projection_has_only_live_snapshots(self):
        p=self.s['integration'];p['settings']['title']='未发布标题'
        r=p['contents'][0];published=r['published']['name'];r['name']='未发布导航'
        result=bootstrap(self.s,self.admin,'admin')['integration']
        self.assertEqual(result['settings']['title'],'未发布标题')
        self.assertNotEqual(result['resourcePortal']['settings']['title'],'未发布标题')
        self.assertEqual(next(x for x in result['resourcePortal']['contents'] if x['id']==r['id'])['name'],published)
        self.assertNotIn('published',result['resourcePortal']['contents'][0])
    def test_personal_admin_tasks_and_exclusive_counts(self):
        for user in ['admin','u1','u2']:
            execute(self.s,self.admin,'integration.admin.task.import',dict(systemId='system-5',payload=[dict(id=user+'-todo',name=user+' task',userId=user,status='待办',version=1,dueAt=''),dict(id=user+'-done',name=user+' finished',userId=user,status='已办',version=1,dueAt='2000-01-01T00:00')]))
        for user in [self.admin,self.u,user_for(self.s,'u2')]:
            result=bootstrap(self.s,user,'admin')['integration']['personalWorkbench']
            external=[r for r in result['todos'] if r.get('systemId')]
            self.assertEqual(len(external),2);self.assertTrue(all(r['userId']==user['id'] for r in external))
            counts=result['counts'];self.assertEqual(counts['待办'],sum(counts[k] for k in ['正常','逾期','预警']))
            for status in ['待办','正常','逾期','预警','已办']:
                rows=execute(self.s,user,'integration.workbench',dict(status=status))['todos']
                self.assertEqual(len(rows),counts[status])
            self.assertEqual(len(execute(self.s,user,'integration.workbench',dict(query=user['id']+' task'))['todos']),1)
    def test_publication_domains_do_not_cross_publish(self):
        p=self.s['integration']['settings'];original=deepcopy(p['published'])
        execute(self.s,self.admin,'integration.policy.save',dict(rev=p['rev'],values=dict(maxAreaHa=1,roleAreaLimits={})))
        execute(self.s,self.admin,'integration.settings.save',dict(rev=p['rev'],values=dict(p,title='待发布视觉标题')))
        execute(self.s,self.admin,'integration.policy.publish',dict(rev=p['rev']))
        self.assertEqual(p['published']['title'],original['title']);self.assertEqual(p['published']['maxAreaHa'],1)
        execute(self.s,self.admin,'integration.policy.save',dict(rev=p['rev'],values=dict(maxAreaHa=2,roleAreaLimits={})))
        execute(self.s,self.admin,'integration.settings.publish',dict(rev=p['rev']))
        self.assertEqual(p['published']['maxAreaHa'],1);self.assertEqual(p['published']['title'],'待发布视觉标题')
        with self.assertRaises(cap.Invalid):execute(self.s,self.u,'integration.policy.publish',dict(rev=p['rev']))
    def test_result_summary_requires_grant_and_hides_details(self):
        self.assertIsNone(bootstrap(self.s,self.u,'admin')['integration']['resultUsage'])
        execute(self.s,self.admin,'integration.admin.access.save',dict(id=self.u['id'],rev=0,values=dict(view=True,analyze=False)))
        summary=bootstrap(self.s,self.u,'admin')['integration']['resultUsage']
        self.assertEqual(set(summary),{'counts','opens','calls','users','scope'})
        self.assertNotIn('administration',bootstrap(self.s,self.u,'admin')['integration'])

if __name__=='__main__':unittest.main()

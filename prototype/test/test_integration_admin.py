import unittest
from copy import deepcopy
from seed import seed
from server import execute,bootstrap,user_for
import integration
import integration_admin as ia
import capabilities as cap


class IntegrationAdministration(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
        bootstrap(self.s,self.admin,'admin');self.p=self.s['integration'];self.system='system-5'

    def call(self,op,arg=None,user=None):
        return execute(self.s,user or self.admin,'integration.admin.'+op,arg or {})

    def row(self,**kw):
        return dict(dict(id='task-001',name='规划复核',userId='u1',status='待办',createdAt='2026-09-16T10:00',dueAt='',entry='',version=1),**kw)

    def sync(self,rows):return self.call('task.import',dict(systemId=self.system,payload=rows))

    def test_result_rights_grant_revoke_without_management(self):
        self.assertFalse(bootstrap(self.s,self.user,'admin')['integration']['resultPermissions']['view'])
        result=self.call('access.save',dict(id='u1',rev=0,values=dict(view=True,analyze=False)))
        data=bootstrap(self.s,self.user,'admin')
        self.assertTrue(data['integration']['resultPermissions']['view'])
        self.assertFalse(data['integration']['canManage'])
        self.assertFalse(data['integration']['resultPermissions']['analyze'])
        self.assertNotIn('administration',data['integration'])
        self.assertEqual(data['centers']['systems'],[])
        for op in ['access.save','task.detail','task.import','task.receipt','task.history']:
            with self.assertRaises(cap.Invalid):self.call(op,{},self.user)
        with self.assertRaises(cap.Invalid):execute(self.s,self.user,'integration.map.query',{})
        self.call('access.save',dict(id='u1',rev=result['rev'],values=dict(view=False,analyze=False)))
        self.assertFalse(bootstrap(self.s,self.user,'admin')['integration']['resultPermissions']['view'])
        with self.assertRaises(cap.Invalid):self.call('access.save',dict(id='u1',rev=0,values=dict(view=True,analyze=True)))

    def test_analysis_requires_view_and_preserves_resource_scope(self):
        with self.assertRaises(cap.Invalid):self.call('access.save',dict(id='u1',rev=0,values=dict(view=False,analyze=True)))
        self.call('access.save',dict(id='u1',rev=0,values=dict(view=True,analyze=True)))
        self.assertTrue(ia.rights(self.s,self.user)['analyze'])
        with self.assertRaises(cap.Invalid):execute(self.s,self.user,'integration.map.query',dict(sceneId='private-missing',mode='point',x=111,y=40))
        self.user['enabled']=False
        self.assertFalse(ia.rights(self.s,self.user)['view'])

    def test_sync_idempotence_newer_version_and_old_version_rejection(self):
        first=self.sync([self.row()]);self.assertEqual(first['added'],1)
        task=self.s['centers']['externalTodos'][0];rev=task['rev']
        repeat=self.sync([self.row()]);self.assertEqual(repeat['skipped'],1);self.assertEqual(task['rev'],rev)
        conflict=self.sync([self.row(name='同版本修改')]);self.assertEqual(conflict['status'],'校验失败');self.assertEqual(task['name'],'规划复核')
        next_run=self.sync([self.row(version=2,status='已办')]);self.assertEqual(next_run['updatedCount'],1)
        stale=self.sync([self.row()]);self.assertEqual(stale['status'],'校验失败');self.assertEqual(task['status'],'已办')
        with self.assertRaises(cap.Invalid):execute(self.s,self.admin,'centers.todos.import',dict(systemId=self.system,payload=[self.row()]))

    def test_whole_batch_atomic_failure_retry_and_error_resolution(self):
        rows=[self.row(),self.row(id='other',userId='external-user',status='处理中')]
        run=self.sync(rows);self.assertEqual(run['status'],'校验失败');self.assertEqual(run['errors'][0]['row'],2)
        self.assertEqual(self.s['centers']['externalTodos'],[])
        self.call('task.adapter',dict(id=self.system,rev=0,values=dict(userMap={'external-user':'u1'},statusMap={'待办':'待办','处理中':'待办'},versionField='version')))
        retry=self.call('task.retry',dict(id=run['id'],rev=run['rev']))
        self.assertEqual(retry['status'],'已完成');self.assertEqual(retry['added'],2)
        stats=ia.bootstrap(self.s,self.admin,True)['administration']
        self.assertTrue(next(r for r in stats['runs'] if r['id']==run['id'])['resolved'])
        with self.assertRaises(cap.Invalid):self.call('task.retry',dict(id=run['id'],rev=run['rev']))

    def test_invalid_payload_history_and_inactive_recipient(self):
        for payload in ['not json',[],[self.row(version='1')],[self.row(),self.row()],[self.row(entry='javascript:bad')]]:
            run=self.sync(payload);self.assertEqual(run['status'],'校验失败');self.assertTrue(run['errors'])
        self.assertEqual(self.s['centers']['externalTodos'],[])
        self.user['enabled']=False
        self.assertEqual(self.sync([self.row()])['status'],'校验失败')
        self.assertNotIn('payload',ia.bootstrap(self.s,self.admin,True)['administration']['runs'][0])

    def test_receipt_mismatch_and_task_update_invalidate_confirmation(self):
        self.sync([self.row()]);task=self.s['centers']['externalTodos'][0]
        args=dict(id=task['id'],rev=task['rev'],values=dict(sourceStatus='已办',evidence='来源系统截图核对结果'))
        result=self.call('task.receipt',args);self.assertEqual(result['status'],'状态不一致');self.assertEqual(task['status'],'待办')
        args['values']['sourceStatus']='待办';result=self.call('task.receipt',args);self.assertEqual(result['status'],'人工核对一致')
        self.assertEqual(ia.bootstrap(self.s,self.admin,True)['administration']['receipts'][0]['status'],'人工核对一致')
        self.sync([self.row(version=2,status='已办')])
        self.assertEqual(ia.bootstrap(self.s,self.admin,True)['administration']['receipts'][0]['status'],'待核对')
        with self.assertRaises(cap.Invalid):self.call('task.receipt',args)
        self.assertEqual(len(self.call('task.history',dict(id=task['id']))['receipts']),2)

    def test_mapping_revision_validation(self):
        args=dict(id=self.system,rev=0,values=dict(userMap={},statusMap={'open':'待办'},versionField='sourceVersion'))
        self.call('task.adapter',args)
        with self.assertRaises(cap.Invalid):self.call('task.adapter',args)
        args['rev']=1;args['values']['userMap']={'external':'not-found'}
        with self.assertRaises(cap.Invalid):self.call('task.adapter',args)
        self.assertEqual(ia.adapter(self.s,self.system)['rev'],1)

    def test_failed_batch_can_be_archived_with_audited_reason(self):
        run=self.sync('invalid payload')
        with self.assertRaises(cap.Invalid):self.call('task.archive',dict(id=run['id'],rev=run['rev'],values=dict(kind='已另批修正',replacement='missing',reason='来源数据已修正')))
        self.call('task.archive',dict(id=run['id'],rev=run['rev'],values=dict(kind='来源撤回',reason='来源单位撤回本次错误文件')))
        row=self.call('task.detail',dict(id=run['id']))
        self.assertEqual(row['status'],'校验失败')
        self.assertEqual(row['resolution']['kind'],'来源撤回')
        self.assertEqual(row['resolution']['actor'],self.admin['name'])
        self.assertTrue(ia.bootstrap(self.s,self.admin,True)['administration']['runs'][-1]['archived'])
        with self.assertRaises(cap.Invalid):self.call('task.retry',dict(id=row['id'],rev=row['rev']))
        with self.assertRaises(cap.Invalid):self.call('task.archive',dict(id=row['id'],rev=row['rev'],values=dict(kind='来源撤回',reason='再次归档不应允许')))

    def test_configuration_issues_do_not_claim_external_connection(self):
        issues=ia.system_issues(self.s);self.assertEqual(len(issues),9)
        r=self.s['centers']['systems'][-1];r['entry']='https://example.org'
        self.assertEqual(len(ia.system_issues(self.s)),8)
        self.assertEqual(r['status'],'待配置')
        before=deepcopy(self.p);ia.migrate(self.s);self.assertEqual(before,self.p)


if __name__=='__main__':unittest.main()

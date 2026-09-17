import unittest
from copy import deepcopy
from seed import seed
from server import execute,bootstrap,user_for
import operations_center as ops
import centers as c
from capabilities import Invalid

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();self.admin=user_for(self.s,'admin');self.u1=user_for(self.s,'u1');self.u2=user_for(self.s,'u2')
        bootstrap(self.s,self.admin,'admin');self.o=ops.migrate(self.s);self.c=c.migrate(self.s)
    def call(self,op,p=None,u=None):return execute(self.s,u or self.admin,'operations.'+op,p or {})
    def save(self,entity,values,old=None):return self.call('save',dict(entity=entity,values=values,id=(old or {}).get('id'),rev=(old or {}).get('rev')))
    def change(self,op,entity,r,**kw):
        row=c.find(self.o[entity],r['id']);return self.call(op,dict(id=row['id'],rev=row['rev'],**kw))
    def task(self):
        task=self.save('tasks',dict(name='归集验收（示例）',assigneeIds=['u1'],dueAt='2026-12-31T12:00',sourceId='source-local',standardId='standard-basic'))
        self.change('task.dispatch','tasks',task);return self.o['orders'][-1]
    def submit(self,r,bad=False):
        self.call('order.save',dict(id=r['id'],rev=r['rev'],dataRows='id,name,region,area\n1,测试,呼和浩特市,'+('-1' if bad else '1')),self.u1)
        self.call('order.submit',dict(id=r['id'],rev=r['rev']),self.u1)
    def batch(self,bad=False):
        order=self.task();self.submit(order,bad);self.change('order.review','orders',order,decision='通过',note='材料核实无误');return c.find(self.c['ingestions'],order['ingestionId'])
    def qc(self,batch):return execute(self.s,self.admin,'centers.ingestion.check',dict(id=batch['id'],rev=batch['rev']))
    def target(self):return execute(self.s,self.admin,'centers.dataset.create',dict(name='入库空表',standardId='standard-basic'))
    def job(self,batch,target):return self.save('imports',dict(name='映射入库',ingestionId=batch['id'],datasetId=target['id'],mapping={k:k for k in target['fields']}))
    def test_order_scope_review_return_and_submission_history(self):
        order=self.task()
        for u in [self.u2,self.admin]:
            with self.assertRaises(Invalid):self.call('order.save',dict(id=order['id'],rev=order['rev'],dataRows='id\n1'),u)
        self.submit(order)
        with self.assertRaises(Invalid):self.call('order.review',dict(id=order['id'],rev=order['rev'],decision='通过',note='越权'),self.u1)
        self.change('order.review','orders',order,decision='退回',note='请补充核实')
        self.submit(order)
        self.assertEqual(len(order['submissions']),2)
        self.change('order.review','orders',order,decision='通过',note='材料符合要求')
        self.assertEqual(len(self.c['ingestions']),1)
        with self.assertRaises(Invalid):self.change('order.review','orders',order,decision='通过',note='重复')
        self.assertEqual(ops.bootstrap(self.s,self.u2,'front')['orders'],[])
        self.assertFalse(any(t['id']==order['id'] for t in c.bootstrap(self.s,self.u1,'front')['todos']))
    def test_unified_todo_identity_and_scope(self):
        order=self.task();todos=c.bootstrap(self.s,self.u1,'front')['todos'];self.assertEqual(sum(r['id']==order['id'] for r in todos),1)
        self.assertFalse(any(r['id']==order['id'] for r in c.bootstrap(self.s,self.u2,'front')['todos']))
        self.assertTrue(any(r['id']==order['id'] for r in ops.bootstrap(self.s,self.u1,'front')['todos']))
    def test_stale_revision_and_duplicate_dispatch(self):
        order=self.task();task=self.o['tasks'][0]
        with self.assertRaises(Invalid):self.call('task.dispatch',dict(id=task['id'],rev=1))
        with self.assertRaises(Invalid):self.change('task.dispatch','tasks',task)
        self.assertEqual(len(self.o['orders']),1)
    def test_model_version_and_runs_are_separate(self):
        batch=self.batch(True)
        model=self.save('models',dict(name='本地质检',ruleIds=['rule-area']))
        model=self.change('model.publish','models',model)
        task=self.save('qualityTasks',dict(name='质量检查任务',modelId=model['id'],ingestionId=batch['id']))
        r1=self.change('quality.run','qualityTasks',task);r2=self.change('quality.run','qualityTasks',task)
        self.assertNotEqual(r1['id'],r2['id']);self.assertFalse(r1['passed']);self.assertEqual(r1['executionStatus'],'已完成')
        self.assertEqual(r1['modelSnapshot']['version'],1)
        rule=self.c['rules'][-1];execute(self.s,self.admin,'centers.save',dict(entity='rules',id=rule['id'],rev=rule['rev'],values=dict(rule,name='新规则')))
        with self.assertRaises(Invalid):self.change('quality.run','qualityTasks',task)
    def test_import_keeps_same_resource_and_rejects_duplicate(self):
        batch=self.batch();self.qc(batch);ds=self.target();count=len(self.s['resources']);job=self.job(batch,ds)
        result=self.change('import.run','imports',job);self.assertEqual(result['status'],'成功')
        self.assertEqual(len(self.s['resources']),count);self.assertEqual(batch['resourceId'],ds['resourceId'])
        with self.assertRaises(Invalid):self.change('import.run','imports',job)
        self.assertEqual(result['attempts'][0]['rowCount'],1)
    def test_stale_report_creates_failed_attempt_then_retry(self):
        batch=self.batch();self.qc(batch);ds=self.target();job=self.job(batch,ds)
        batch['dataRows']=batch['dataRows'].replace(',1',',2');batch['dataRevision']+=1
        result=self.change('import.run','imports',job);self.assertEqual(result['status'],'失败');self.assertIn('重新检查',result['attempts'][0]['error'])
        self.qc(batch);result=self.change('import.run','imports',job);self.assertEqual(result['status'],'成功');self.assertEqual(len(result['attempts']),2)
    def test_target_standard_revision_blocks_import(self):
        batch=self.batch();self.qc(batch);ds=self.target();job=self.job(batch,ds)
        standard=self.c['standards'][0];execute(self.s,self.admin,'centers.standard.publish',dict(id=standard['id'],rev=standard['rev']))
        result=self.change('import.run','imports',job);self.assertEqual(result['status'],'失败')
    def test_existing_asset_catalog_does_not_import_or_change_sharing(self):
        resource=deepcopy(self.s['resources'][0]);self.save('catalogs',dict(name=resource['name'],resourceId=resource['id'],directoryId='op-dir-root',department='示例单位'))
        self.assertEqual(self.s['resources'][0],resource);self.assertEqual(self.c['ingestions'],[])
        with self.assertRaises(Invalid):self.save('catalogs',dict(name='重复',resourceId=resource['id'],directoryId='op-dir-root',department='示例单位'))
        root=self.o['directories'][0];child=self.save('directories',dict(name='子目录',parentId=root['id'],kind='公共目录'))
        with self.assertRaises(Invalid):self.save('directories',dict(name='根',parentId=child['id'],kind='公共目录'),root)
    def test_alert_dedup_recovery_and_close(self):
        batch=self.batch(True);self.qc(batch);self.call('inspection.run');self.call('inspection.run')
        self.assertEqual(len(self.o['alerts']),1);alert=self.o['alerts'][0];self.assertEqual(alert['count'],2)
        self.change('alert.transition','alerts',alert,status='处理中',note='开始核对')
        self.change('alert.transition','alerts',alert,status='待验证',note='已完成处理')
        with self.assertRaises(Invalid):self.change('alert.transition','alerts',alert,status='已关闭',note='仍未恢复')
        batch['dataRows']=batch['dataRows'].replace('-1','1');batch['dataRevision']+=1;self.qc(batch)
        self.call('inspection.run');self.assertTrue(alert['recoveredAt']);self.assertEqual(alert['status'],'待验证')
        self.change('alert.transition','alerts',alert,status='已关闭',note='复检及巡检已正常')
    def test_nonadmin_cannot_manage_configuration(self):
        for op in ['save','task.dispatch','model.publish','quality.run','import.run','inspection.run','alert.transition']:
            with self.assertRaises(Invalid):self.call(op,{},self.u1)
    def test_domain_build_and_external_connection_boundary(self):
        ds=self.call('dataset.create',dict(name='目标节点建表',standardId='standard-basic',domainId='domain-local'))
        self.assertEqual(ds['domainId'],'domain-local')
        source=execute(self.s,self.admin,'centers.save',dict(entity='sources',values=dict(name='外部库',kind='PostgreSQL',provider='示例单位',endpoint='https://example.org')))
        domain=self.save('domains',dict(name='外部数据库',kind='数据库',sourceId=source['id']))
        with self.assertRaises(Invalid):self.call('dataset.create',dict(name='外部表',standardId='standard-basic',domainId=domain['id']))
    def test_delete_preserves_referenced_nodes_and_executed_tasks(self):
        directory=self.o['directories'][0];r=self.s['resources'][0]
        cat=self.save('catalogs',dict(name=r['name'],resourceId=r['id'],directoryId=directory['id'],department='测试单位'))
        with self.assertRaises(Invalid):self.call('delete',dict(entity='directories',id=directory['id'],rev=directory['rev']))
        self.call('delete',dict(entity='catalogs',id=cat['id'],rev=cat['rev']))
        self.assertTrue(c.find(self.s['resources'],r['id']))
        self.task();task=self.o['tasks'][0]
        with self.assertRaises(Invalid):self.call('delete',dict(entity='tasks',id=task['id'],rev=task['rev']))
    def test_migration_additive(self):
        before=deepcopy(self.s['resources']);ops.migrate(self.s);ops.migrate(self.s)
        self.assertEqual(before,self.s['resources']);self.assertEqual(len(self.o['directories']),1)

if __name__=='__main__':unittest.main()

"""Public portal content lifecycle, access boundaries and citizen feedback."""
import unittest
from copy import deepcopy
import json
from seed import seed
from server import bootstrap, execute, user_for, find
from capabilities import Invalid
import public_portal


class PublicPortalTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();public_portal.migrate(self.s)
        self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1');self.other=user_for(self.s,'u2')

    def call(self, action, payload, user=None):return execute(self.s,user or self.user,action,payload)
    def front(self,user=None):return bootstrap(self.s,user or self.user,'front')['publicPortal']

    def test_migration_preserves_edited_and_removed_content(self):
        self.s['publicPortal']['topics'].pop();self.s['publicPortal']['settings']['title']='自定义首页'
        before=deepcopy(self.s);public_portal.migrate(self.s);self.assertEqual(before,self.s)

    def test_content_draft_publish_disable_and_conflict(self):
        r=self.s['publicPortal']['topics'][0]
        draft=self.call('public.save',dict(entity='topics',id=r['id'],rev=r['rev'],values={'name':'新专题名称'}),self.admin)
        self.assertNotEqual(self.front()['topics'][0]['name'],'新专题名称')
        with self.assertRaises(Invalid) as error:self.call('public.publish',dict(entity='topics',id=r['id'],rev=r['rev']),self.admin)
        self.assertEqual(error.exception.status,409)
        published=self.call('public.publish',dict(entity='topics',id=draft['id'],rev=draft['rev']),self.admin)
        self.assertEqual(self.front()['topics'][0]['name'],'新专题名称')
        self.call('public.disable',dict(entity='topics',id=published['id'],rev=published['rev']),self.admin)
        self.assertNotIn(r['id'],[x['id'] for x in self.front()['topics']])

    def test_home_draft_does_not_leak(self):
        r=self.s['publicPortal']['settings'];self.call('public.save',dict(entity='settings',id='home',rev=r['rev'],values={'title':'仅草稿标题'}),self.admin)
        self.assertNotEqual(self.front()['settings']['title'],'仅草稿标题')

    def test_admin_required_and_external_urls_validated(self):
        with self.assertRaises(Invalid) as error:self.call('public.save',dict(entity='topics',values={'name':'越权'}))
        self.assertEqual(error.exception.status,403)
        for url in ['javascript:alert(1)','http://example.com','https://user:pass@example.com']:
            with self.assertRaises(Invalid):self.call('public.save',dict(entity='topics',values={'name':'标题','body':'正文','url':url}),self.admin)

    def test_feedback_idempotency_and_owner_isolation(self):
        payload=dict(serviceId='notice',title='公示意见',body='请补充规划说明',requestId='once')
        ticket=self.call('public.ticket',payload)
        self.assertEqual(ticket,self.call('public.ticket',payload));self.assertEqual(len(self.s['publicPortal']['tickets']),1)
        self.assertEqual(self.front(self.other)['tickets'],[])
        with self.assertRaises(Invalid):self.call('public.reply',dict(id=ticket['id'],rev=1,status='已回复',reply='越权回复'),self.other)
        updated=self.call('public.reply',dict(id=ticket['id'],rev=1,status='已回复',reply='已补充说明'),self.admin)
        self.assertEqual(updated['status'],'已回复');self.assertEqual(self.front()['tickets'][0]['history'][0]['body'],'已补充说明')
        with self.assertRaises(Invalid) as error:self.call('public.reply',dict(id=ticket['id'],rev=1,status='已回复',reply='旧版本'),self.admin)
        self.assertEqual(error.exception.status,409)

    def test_cannot_submit_to_disabled_service(self):
        self.s['publicPortal']['services'][0]['status']='已停用'
        with self.assertRaises(Invalid):self.call('public.ticket',dict(serviceId='estate',title='标题',body='正文',requestId='x'))

    def test_progress_only_returns_permitted_cases(self):
        rows=self.call('public.progress',dict(query='project_demo_1'));self.assertTrue(rows)
        self.assertEqual(self.call('public.progress',dict(query='project_demo_1'),self.other),[])
        self.assertEqual(self.call('public.progress',dict(query='not-found')),[])

    def test_download_requires_current_authorization(self):
        with self.assertRaises(Invalid) as error:self.call('public.download',{'id':'r1'})
        self.assertEqual(error.exception.status,403)
        self.s['grants'].append(dict(userId='u1',resourceId='r1',validUntil='2000-01-01'))
        with self.assertRaises(Invalid):self.call('public.download',{'id':'r1'})
        self.s['grants'][0]['validUntil']='2999-01-01'
        result=self.call('public.download',{'id':'r1'})
        self.assertTrue(result['filename'].endswith('.csv'));self.assertTrue(result['content'])
        self.assertEqual(len(self.front()['downloads']),1);self.assertEqual(self.front(self.other)['downloads'],[])

    def test_download_rejects_disabled_and_hidden_resource(self):
        with self.assertRaises(Invalid):self.call('public.download',{'id':'r12'})
        find(self.s['resources'],'r2')['status']='已停用'
        with self.assertRaises(Invalid):self.call('public.download',{'id':'r2'})

    def test_map_filters_requested_resource_and_unauthorized_geometry(self):
        config=self.call('public.map',{'resourceId':'r11'})
        self.assertTrue(config['layers'])
        self.assertTrue(all(x['resourceId']=='r11' and x['features']==[] for x in config['layers']))
        cfg=self.call('public.map',{'resourceId':'r_scene_demo'})
        self.assertTrue(cfg['layers'][0]['features'])
        result=self.call('public.download',{'id':'r_scene_demo'})
        self.assertTrue(json.loads(result['content'])['features'])
        # A visible resource without a registered layer must not get unrelated geometry.
        self.assertEqual(self.call('public.map',{'resourceId':'r7'})['layers'],[])

    def test_new_draft_needs_publish_and_resource_references_are_validated(self):
        r=self.call('public.save',dict(entity='topics',values={'name':'新建专题','body':'正文','cover':'map','resourceIds':['r2']}),self.admin)
        self.assertNotIn(r['id'],[r['id'] for r in self.front()['topics']])
        with self.assertRaises(Invalid):self.call('public.save',dict(entity='topics',values={'name':'错误引用','body':'正文','resourceIds':['missing']}),self.admin)

    def test_service_guide_fields_follow_publication(self):
        row=self.s['publicPortal']['services'][0]
        values=dict(process='申请 → 审核',materials='申请表',timeLimit='5 个工作日',phone='0471-12345',order=0)
        draft=self.call('public.save',dict(entity='services',id=row['id'],rev=row['rev'],values=values),self.admin)
        self.assertNotIn('process',self.front()['services'][0])
        pub=self.call('public.publish',dict(entity='services',id=row['id'],rev=draft['rev']),self.admin)
        for key,value in values.items():self.assertEqual(self.front()['services'][0][key],value)
        with self.assertRaises(Invalid):self.call('public.publish',dict(entity='services',id=row['id'],rev=pub['rev']),self.admin)

    def test_delete_requires_offline_revision_and_admin_preserves_feedback(self):
        ticket=self.call('public.ticket',dict(serviceId='notice',title='意见',body='保留原记录',requestId='delete-test'))
        row=find(self.s['publicPortal']['services'],'notice')
        payload=dict(entity='services',id=row['id'],rev=row['rev'])
        with self.assertRaises(Invalid):self.call('public.delete',payload,self.admin)
        off=self.call('public.disable',payload,self.admin)
        draft=self.call('public.save',dict(entity='services',id=row['id'],rev=off['rev'],values={'name':'下架修改'}),self.admin)
        self.assertNotIn(row['id'],[r['id'] for r in self.front()['services']])
        with self.assertRaises(Invalid):self.call('public.delete',dict(payload,rev=draft['rev']))
        with self.assertRaises(Invalid):self.call('public.delete',payload,self.admin)
        self.call('public.delete',dict(payload,rev=draft['rev']),self.admin)
        self.assertIsNone(find(self.s['publicPortal']['services'],'notice'))
        self.assertEqual(self.front()['tickets'][0],ticket)
        home=self.s['publicPortal']['settings']
        with self.assertRaises(Invalid):self.call('public.delete',dict(entity='settings',id='home',rev=home['rev']),self.admin)

    def test_reply_cannot_regress_and_allows_supplement(self):
        row=self.call('public.ticket',dict(serviceId='notice',title='意见',body='内容',requestId='reply-test'))
        done=self.call('public.reply',dict(id=row['id'],rev=1,status='已回复',reply='已答复'),self.admin)
        with self.assertRaises(Invalid):self.call('public.reply',dict(id=row['id'],rev=done['rev'],status='处理中',reply='回退'),self.admin)
        extra=self.call('public.reply',dict(id=row['id'],rev=done['rev'],status='已回复',reply='补充说明'),self.admin)
        self.assertEqual(len(extra['history']),2)


class TopicContentTests(unittest.TestCase):
    def setUp(self):
        self.s=seed();public_portal.migrate(self.s)
        self.admin=user_for(self.s,'admin');self.user=user_for(self.s,'u1')
    def save(self,values,user=None):
        topic=self.s['publicPortal']['topics'][0]
        return execute(self.s,user or self.admin,'public.save',dict(entity='topics',id=topic['id'],rev=topic['rev'],values=values))
    def test_topic_sections_media_publication_and_preservation(self):
        values=dict(cover='nature',coverUrl='https://example.org/nature.jpg',coverCredit='业务单位授权照片',sections=[dict(title='专题章节',text='已核实的章节内容')],media=[dict(type='document',url='https://example.org/atlas.pdf',title='公开图集',source='业务单位')])
        row=self.save(values)
        before=public_portal.bootstrap(self.s,self.user,'front')['topics'][0]
        self.assertNotIn('media',before)
        execute(self.s,self.admin,'public.publish',dict(entity='topics',id=row['id'],rev=row['rev']))
        after=public_portal.bootstrap(self.s,self.user,'front')['topics'][0]
        self.assertEqual(after['sections'],values['sections']);self.assertEqual(after['media'],values['media'])
        public_portal.migrate(self.s)
        self.assertEqual(public_portal.bootstrap(self.s,self.user,'front')['topics'][0]['coverUrl'],values['coverUrl'])
    def test_invalid_media_and_sections_rejected(self):
        cases=[{'coverUrl':'javascript:alert(1)','coverCredit':'来源'}, {'coverUrl':'https://example.org/a.jpg'}, {'sections':[dict(title='只有标题')]}, {'sections':[dict(title='a',text='b')]*7}, {'media':[dict(title='资料',source='来源',type='image',url='http://example.org/a')]}, {'media':[dict(title='资料',source='来源',type='iframe',url='https://example.org/a')]}, {'media':[dict(title='资料',source='来源',type='video',url='https://user:pass@example.org/a')]}]
        for values in cases:
            with self.subTest(values=values),self.assertRaises(Invalid):self.save(values)
    def test_only_admin_can_edit_and_explicit_empty_sections_preserved(self):
        with self.assertRaises(Invalid):self.save({'sections':[]},self.user)
        row=self.save({'sections':[],'media':[]})
        execute(self.s,self.admin,'public.publish',dict(entity='topics',id=row['id'],rev=row['rev']))
        self.assertEqual(public_portal.bootstrap(self.s,self.user,'front')['topics'][0]['sections'],[])

if __name__=='__main__':unittest.main()

"""Information-center publication, migration and visibility regressions."""
import unittest
from copy import deepcopy
from seed import seed
from news_content import migrate
from server import bootstrap, execute, user_for, find


class NewsContentTests(unittest.TestCase):
    def setUp(self):
        self.state = seed()
        self.original = deepcopy(self.state['knowledge'])
        migrate(self.state)
        self.admin = user_for(self.state, 'admin')
        self.user = user_for(self.state, 'u1')

    def test_upgrade_preserves_original_records_and_does_not_resurrect_deleted_content(self):
        for original in self.original:
            self.assertEqual(find(self.state['knowledge'], original['id']), original)
        self.state['knowledge'] = [r for r in self.state['knowledge'] if r['id'] != 'news_standard']
        before = deepcopy(self.state)
        migrate(self.state)
        self.assertEqual(before, self.state)

    def test_four_columns_have_published_content_and_processed_body(self):
        front = bootstrap(self.state, self.user, 'front')['knowledge']
        self.assertTrue({'政策法规','行业动态','技术标准','培训资源'}.issubset({r['category'] for r in front}))
        self.assertTrue(all(r.get('body') and r.get('chunks') for r in front if r['id'].startswith('news_')))

    def test_draft_is_not_visible_until_published(self):
        original = find(self.state['knowledge'], 'news_standard')
        draft = execute(self.state, self.admin, 'save', dict(entity='knowledge', id=original['id'], rev=original['rev'], values={'name':'修订后的技术标准资料'}))
        self.assertNotEqual(find(bootstrap(self.state,self.user,'front')['knowledge'],draft['id'])['name'],draft['name'])
        execute(self.state,self.admin,'publish',dict(entity='knowledge',id=draft['id'],rev=draft['rev']))
        self.assertEqual(find(bootstrap(self.state,self.user,'front')['knowledge'],draft['id'])['name'],draft['name'])

    def test_disabled_and_restricted_content_is_not_exposed(self):
        find(self.state['knowledge'],'news_standard')['status']='已停用'
        find(self.state['knowledge'],'news_policy')['published']['visibility']='管理员'
        ids={r['id'] for r in bootstrap(self.state,self.user,'front')['knowledge']}
        self.assertNotIn('news_standard',ids)
        self.assertNotIn('news_policy',ids)

"""Read-only checks against a running oneMap Python server (not a generic file server)."""
import http.client
import sys
import unittest
from urllib.parse import urlsplit, quote

BASE = urlsplit(sys.argv.pop(1) if len(sys.argv) > 1 else 'http://127.0.0.1:5190')

class GISStaticHTTPTests(unittest.TestCase):
    def get(self, path):
        conn = http.client.HTTPConnection(BASE.hostname, BASE.port or 80, timeout=8)
        conn.request('GET', path)
        response = conn.getresponse()
        body = response.read()
        status = response.status
        conn.close()
        return status, body

    def test_root_and_legacy_bundle_remain_available(self):
        status, body = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn(b'gisEntryRoutes', body)
        self.assertEqual(self.get('/app.js')[0], 200)

    def test_local_map_bundle_is_served(self):
        for path in ['index.html', 'portal.html', 'requirements.html', 'app.js', 'spatial.js',
                     'style.css', 'guide-assistant.js', 'data/map-data.js',
                     'assets/vendor/leaflet/leaflet.js', 'assets/vendor/leaflet/leaflet.css',
                     'assets/relief.webp', 'assets/photos/scenic-ecology.jpg']:
            with self.subTest(path=path):
                status, body = self.get('/gis/' + path)
                self.assertEqual(status, 200)
                self.assertGreater(len(body), 100)

    def test_chinese_document_paths(self):
        for name in ['需求说明书与原型交互设计.md', '功能覆盖追踪表.md', '功能覆盖追踪表.csv', '验收记录.md']:
            with self.subTest(name=name):
                status, body = self.get('/gis/docs/' + quote(name))
                self.assertEqual(status, 200)
                self.assertGreater(len(body), 100)

    def test_no_directory_listing_traversal_or_executable_sources(self):
        for path in ['/gis/', '/gis/../index.html', '/gis/%2e%2e/index.html',
                     '/gis/%2e%2e%2findex.html', '/gis/test/spatial.test.cjs',
                     '/gis/test/static-http.py', '/gis/not-found.js']:
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)

if __name__ == '__main__':
    unittest.main()

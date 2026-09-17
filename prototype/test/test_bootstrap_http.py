"""Bootstrap transport, identity isolation and slow-client lock regression."""
import gzip
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
import server


class BootstrapHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.old_db = server.DB
        server.DB = Path(cls.temp.name) / 'test.sqlite3'
        server.init_db()
        cls.lock_available = []

        class Handler(server.Handler):
            def reply(self, status, data):
                def probe():
                    acquired = server.LOCK.acquire(timeout=0.3)
                    cls.lock_available.append(acquired)
                    if acquired:
                        server.LOCK.release()
                worker = threading.Thread(target=probe)
                worker.start()
                worker.join()
                super().reply(status, data)

        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        server.DB = cls.old_db
        cls.temp.cleanup()

    def request(self, encoding='', user='u1', mode='front'):
        conn = http.client.HTTPConnection(*self.httpd.server_address)
        conn.request('GET', '/api/bootstrap', headers={
            'Accept-Encoding': encoding, 'X-Demo-User': user, 'X-Demo-Mode': mode})
        response = conn.getresponse()
        body = response.read()
        status, headers = response.status, dict(response.getheaders())
        conn.close()
        self.assertEqual(int(headers['Content-Length']), len(body))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertTrue(self.lock_available[-1], 'Response transmission holds global lock')
        return status, headers, body

    def test_gzip_preserves_response_and_reduces_transfer(self):
        _, _, plain = self.request()
        status, headers, zipped = self.request('br, gzip')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertEqual(headers['Vary'], 'Accept-Encoding')
        self.assertLess(len(zipped), len(plain) / 3)
        decoded = json.loads(gzip.decompress(zipped))
        expected = json.loads(plain)
        decoded.pop('serverTime'); expected.pop('serverTime')
        self.assertEqual(decoded, expected)

    def test_identity_and_explicit_gzip_refusal(self):
        for encoding in ['', 'identity', 'gzip;q=0, *;q=1']:
            with self.subTest(encoding=encoding):
                status, headers, body = self.request(encoding)
                self.assertEqual(status, 200)
                self.assertNotIn('Content-Encoding', headers)
                self.assertEqual(json.loads(body)['user']['id'], 'u1')

    def test_admin_and_front_remain_isolated(self):
        _, _, body = self.request('gzip', 'admin', 'admin')
        admin = json.loads(gzip.decompress(body))
        self.assertEqual(admin['user']['role'], '平台管理员')
        self.assertTrue(admin['users'])
        _, _, body = self.request('gzip')
        front = json.loads(gzip.decompress(body))
        self.assertEqual(front['user']['id'], 'u1')
        self.assertEqual(front['users'], [])


if __name__ == '__main__':
    unittest.main()

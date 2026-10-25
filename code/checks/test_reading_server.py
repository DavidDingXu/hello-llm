"""使用真实 HTTP 请求核对本地阅读入口、同步与视频分段，不依赖 Markdown。"""
from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'reading_server_checks', ROOT / 'visuals' / 'serve_reading.py')
server_module = importlib.util.module_from_spec(spec)
# 服务本身只用标准库。构建器在用例中写入临时页面，避免网站依赖影响读者检查。
builder = types.ModuleType('build_reading')
builder.COLUMN = ROOT.parent
with patch.dict(sys.modules, {'build_reading': builder}):
    spec.loader.exec_module(server_module)


class QuietReadingHandler(server_module.ReadingHandler):
    def log_message(self, format, *args):
        pass


class ReadingServerChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.page = self.root / 'index.html'
        self.page.write_bytes(b'old page')
        self.current_page = b'<!doctype html><title>Fresh reading page</title>'
        self.video = bytes(range(256)) * 600
        (self.root / 'lesson.mp4').write_bytes(self.video)
        assets = self.root / 'reading_site'
        assets.mkdir()
        (assets / 'site.js').write_bytes(b'window.readingReady = true;')

        def build_current_page():
            self.page.write_bytes(self.current_page)

        sync = patch.object(server_module, 'sync_reading', build_current_page)
        sync.start()
        self.addCleanup(sync.stop)
        self.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), partial(QuietReadingHandler, directory=str(self.root)))
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, headers=None):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.headers, response.read()
        finally:
            connection.close()

    def test_root_url_serves_current_reading_home_instead_of_directory_listing(self):
        for path in ('/', '/?lesson=01'):
            with self.subTest(path=path):
                status, headers, body = self.request('GET', path)
                self.assertEqual(status, 200)
                self.assertEqual(body, self.current_page)
                self.assertIn('text/html', headers['Content-Type'])

    def test_head_refreshes_home_and_returns_get_headers_without_body(self):
        for path in ('/', '/?lesson=01', quote('/index.html') + '?lesson=01'):
            with self.subTest(path=path):
                self.page.write_bytes(b'stale')
                status, headers, body = self.request('HEAD', path)
                self.assertEqual(status, 200)
                self.assertEqual(self.page.read_bytes(), self.current_page)
                self.assertEqual(int(headers['Content-Length']), len(self.current_page))
                self.assertEqual(body, b'')
                get_status, get_headers, _ = self.request('GET', path)
                self.assertEqual(get_status, status)
                for name in ('Content-Type', 'Content-Length', 'Cache-Control', 'Accept-Ranges'):
                    self.assertEqual(headers[name], get_headers[name])

    def test_static_assets_do_not_trigger_page_builds(self):
        def unexpected_build():
            raise AssertionError('静态资源请求不应重建阅读页')

        with patch.object(server_module, 'sync_reading', unexpected_build):
            status, headers, body = self.request('GET', '/reading_site/site.js?v=1')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'window.readingReady = true;')
        self.assertIn('no-store', headers['Cache-Control'])

    def test_video_ranges_return_only_requested_bytes(self):
        cases = (
            ('bytes=7-17', 7, 17),
            ('bytes=-7', 153593, 153599),
            ('bytes=153590-', 153590, 153599),
            ('bytes=153590-999999', 153590, 153599),
            ('bytes=0-70000', 0, 70000),
        )
        for value, first, last in cases:
            with self.subTest(range=value):
                status, headers, body = self.request('GET', '/lesson.mp4', {'Range': value})
                self.assertEqual(status, 206)
                self.assertEqual(headers['Content-Range'], f'bytes {first}-{last}/153600')
                self.assertEqual(int(headers['Content-Length']), last - first + 1)
                self.assertEqual(body, self.video[first:last + 1])
                head_status, head_headers, head_body = self.request(
                    'HEAD', '/lesson.mp4', {'Range': value})
                self.assertEqual(head_status, status)
                self.assertEqual(head_headers['Content-Range'], headers['Content-Range'])
                self.assertEqual(head_headers['Content-Length'], headers['Content-Length'])
                self.assertEqual(head_body, b'')

    def test_unsatisfiable_video_ranges_return_empty_416(self):
        for value in ('bytes=153600-', 'bytes=10-9', 'bytes=-0'):
            for method in ('GET', 'HEAD'):
                with self.subTest(method=method, range=value):
                    status, headers, body = self.request(method, '/lesson.mp4', {'Range': value})
                    self.assertEqual(status, 416)
                    self.assertEqual(headers['Content-Range'], 'bytes */153600')
                    self.assertEqual(headers['Content-Length'], '0')
                    self.assertEqual(body, b'')

    def test_full_video_still_returns_all_bytes(self):
        status, headers, body = self.request('GET', '/lesson.mp4')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Accept-Ranges'], 'bytes')
        self.assertEqual(int(headers['Content-Length']), 153600)
        self.assertEqual(body, self.video)


if __name__ == '__main__':
    unittest.main()

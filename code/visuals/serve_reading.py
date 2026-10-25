"""本地预览：正文变更在请求时重新生成；禁用开发预览的浏览器缓存。"""
import argparse
from functools import partial
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import threading
import importlib
import re
import build_reading as reading
COLUMN = reading.COLUMN
_generator_version = None


def sync_reading():
    global _generator_version
    source = Path(reading.__file__)
    version = (source.stat().st_mtime_ns, source.stat().st_size)
    if version != _generator_version:
        importlib.invalidate_caches()
        cached = getattr(reading, '__cached__', None)
        if cached:
            Path(cached).unlink(missing_ok=True)
        importlib.reload(reading)
    _generator_version = version
    reading.build_all()

_lock = threading.Lock()


class ReadingHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        # GET 与 HEAD 共用同步及首页入口，避免 HEAD 读取过期页面信息。
        request_path, separator, query = self.path.partition('?')
        if request_path.endswith(('/', '.html')):
            with _lock:
                sync_reading()
        if request_path == '/':
            self.path = '/index.html' + separator + query
        # 浏览器按字节取视频片段，才能在文件尚未全部下载时跳到章节。
        self._range_remaining = None
        requested = self.headers.get('Range')
        path = Path(self.translate_path(self.path))
        if not requested or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
        start, end = 0, -1
        if match and any(match.groups()) and size:
            first, last = match.groups()
            if first:
                start = int(first)
                end = min(int(last) if last else size - 1, size - 1)
            elif int(last):
                start, end = max(0, size - int(last)), size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        source = path.open('rb')
        source.seek(start)
        self._range_remaining = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(self._range_remaining))
        self.end_headers()
        return source

    def copyfile(self, source, outputfile):
        if self._range_remaining is None:
            return super().copyfile(source, outputfile)
        remaining = self._range_remaining
        while remaining:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8874)
    args = parser.parse_args()
    sync_reading()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(ReadingHandler, directory=str(COLUMN)))
    print(f'本地阅读：http://127.0.0.1:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

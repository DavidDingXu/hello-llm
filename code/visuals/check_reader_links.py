"""检查读者文档、本地页面与本项目绝对 URL 对应的文件；不访问网络。"""
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import markdown

ROOT = Path(__file__).resolve().parents[2]
SITE = 'daviddingxu.github.io'
REPOSITORY = '/DavidDingXu/hello-llm/'


class References(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links, self.ids = [], set()
        self.redirect = None
        self.preserves_hash = 'location.hash' in text
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh' and self.preserves_hash:
            match = re.fullmatch(r'\s*\d+\s*;\s*url\s*=\s*(.+)', attrs.get('content', ''), re.I)
            if match:
                self.redirect = match.group(1).strip(' \"\'')
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        for field in ('href', 'src', 'data-src', 'poster'):
            if attrs.get(field):
                self.links.append(attrs[field])
        if attrs.get('srcset'):
            self.links.extend(item.strip().split()[0] for item in attrs['srcset'].split(',') if item.strip())


def parse(path):
    text = path.read_text(encoding='utf-8')
    if path.suffix == '.md':
        text = markdown.markdown(text, extensions=['fenced_code', 'tables', 'md_in_html', 'toc'])
    return References(text)


def destination(url, document, root):
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    if parsed.netloc.lower() == SITE and path.startswith('/hello-llm/'):
        relative = path.removeprefix('/hello-llm/')
        target = root / relative
        if not relative or path.endswith('/'):
            target /= 'index.html'
    elif parsed.netloc.lower() == 'github.com' and path.startswith(REPOSITORY):
        match = re.match(r'(?:blob|tree)/main/(.*)', path.removeprefix(REPOSITORY))
        if not match:
            return None
        target = root / match[1]
    elif not parsed.scheme and not parsed.netloc:
        target = document if not path else document.parent / path
    else:
        return None
    return target.resolve(), unquote(parsed.fragment)


def check_links(root=ROOT):
    root = Path(root).resolve()
    documents = [p for p in root.rglob('*') if p.is_file() and p.suffix in {'.md', '.html'}
                 and not set(p.relative_to(root).parts) & {'.git', '_build', 'dist', 'node_modules', '.venv'}]
    parsed, issues, checked = {}, [], 0
    for document in documents:
        current = parsed.setdefault(document, parse(document))
        for url in current.links:
            target = destination(url, document, root)
            if target is None:
                continue
            path, fragment = target
            checked += 1
            problem = None
            if not path.is_relative_to(root):
                problem = '链接越出仓库目录'
            elif not path.exists():
                problem = '目标文件不存在'
            elif fragment and path.suffix == '.html':
                # Legacy lesson URLs explicitly forward location.hash to course/.
                # Check the final local page, while bounding loops and repository access.
                seen = set()
                found = False
                while path.is_relative_to(root) and path.is_file() and path.suffix == '.html' and path not in seen:
                    seen.add(path)
                    if path not in parsed:
                        parsed[path] = parse(path)
                    if fragment in parsed[path].ids:
                        found = True
                        break
                    redirect = parsed[path].redirect
                    resolved = destination(redirect, path, root) if redirect else None
                    if resolved is None:
                        break
                    path, next_fragment = resolved
                    fragment = next_fragment or fragment
                if not found:
                    problem = '页面锚点不存在'
            elif fragment and path.suffix == '.py' and re.fullmatch(r'L\d+(?:-L\d+)?', fragment):
                lines = len(path.read_text(encoding='utf-8').splitlines())
                if any(not 1 <= int(n) <= lines for n in re.findall(r'\d+', fragment)):
                    problem = '源码行号不存在'
            if problem:
                issues.append(f'{document.relative_to(root).as_posix()} → {url}：{problem}')
    return checked, issues


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    checked, issues = check_links(parser.parse_args().root)
    if issues:
        raise SystemExit('\n'.join(issues))
    print(f'已核对 {checked} 处项目文件链接，未发现缺失目标。')

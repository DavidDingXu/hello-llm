"""内容检查：按顺序执行正文Python、检查本地链接和阅读页一致性。"""
from contextlib import redirect_stdout
from html.parser import HTMLParser
import io
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urlparse

import markdown
import torch
from build_reading import COLUMN, article_paths, build_all, render_body
sys.path.insert(0, str(COLUMN / 'code'))


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]
    def handle_starttag(self, tag, attrs):
        attributes=dict(attrs)
        if tag in ('a','img'):
            value=attributes.get('href' if tag=='a' else 'src')
            if value:self.links.append(value)


def main():
    torch.set_num_threads(1)
    stale=build_all(check=True)
    if stale:raise AssertionError('阅读页过期：'+', '.join(str(p) for p in stale))
    total=0
    for article in article_paths():
        source=article.read_text(encoding='utf-8');links=Links()
        links.feed(render_body(source))
        for link in links.links:
            parsed=urlparse(link)
            if parsed.scheme or not parsed.path:continue
            target=(article.parent/unquote(parsed.path)).resolve()
            if not target.exists():raise AssertionError(f'{article.parent.name} 缺少资源：{link}')
        namespace={'__name__':'article_check'}
        blocks=re.findall(r'```python\n(.*?)```',source,re.S)
        started=time.perf_counter()
        with redirect_stdout(io.StringIO()):
            for number,block in enumerate(blocks,1):
                exec(compile(block,f'{article}:block{number}','exec'),namespace)
        total+=len(blocks)
        print(f'{article.parent.name}: {len(blocks)} 段Python、{len(links.links)}个链接通过（{time.perf_counter()-started:.2f}s）',flush=True)
    print(f'合计：{len(article_paths())}篇，{total}段Python。')


if __name__=='__main__':main()

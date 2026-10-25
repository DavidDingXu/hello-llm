"""双语学习站的正文、搜索定位、子路径链接与独立静态导出回归。"""
from contextlib import redirect_stdout
import base64
from html.parser import HTMLParser
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import quote, unquote, urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
COLUMN = ROOT.parent
VISUALS = ROOT / 'visuals'
BASE_URL = 'https://example.test/hello-llm/'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reading = (load_module('reading_site_builder_checks', VISUALS / 'build_reading.py')
           if importlib.util.find_spec('markdown') is not None else None)


class Page(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.document = document
        self.line_starts = [0]
        for line in document.splitlines(keepends=True):
            self.line_starts.append(self.line_starts[-1] + len(line))
        self.ids, self.references, self.switches = set(), [], []
        self.article_start = self.article_end = None
        self.language = self.root = ''
        self.details, self.answers = [], []
        self.summary_depth = 0
        self.feed(document)

    def position(self):
        line, offset = self.getpos()
        return self.line_starts[line - 1] + offset

    @property
    def article(self):
        if self.article_start is None or self.article_end is None:
            return None
        return self.document[self.article_start:self.article_end]

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        for name in ('href', 'src', 'poster', 'xlink:href'):
            if attrs.get(name):
                self.references.append(attrs[name])
        if tag == 'html':
            self.language = attrs.get('lang', '')
        if tag == 'body':
            self.root = attrs.get('data-root', '')
        if 'language-switch' in attrs.get('class', '').split():
            self.switches.append(attrs['href'])
        if tag == 'article' and attrs.get('id') == 'article-body':
            self.article_start = self.position() + len(self.get_starttag_text())
        if tag == 'details':
            inside_article = self.article_start is not None and self.article_end is None
            self.details.append([] if inside_article and 'answer' in attrs.get('class', '').split() else None)
        if tag == 'summary':
            self.summary_depth += 1

    def handle_endtag(self, tag):
        if tag == 'article' and self.article_start is not None:
            self.article_end = self.position()
        if tag == 'details' and self.details:
            answer = self.details.pop()
            if answer:
                self.answers.append(''.join(answer))
        if tag == 'summary':
            self.summary_depth -= 1

    def handle_data(self, value):
        if not self.summary_depth:
            for answer in self.details:
                if answer is not None:
                    answer.append(value)


def compact(value):
    return re.sub(r'\s+', '', value)


@unittest.skipIf(reading is None, '学习站正文检查需要网站依赖 Markdown')
class ReadingSiteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = reading.article_paths()
        cls.pages = {path: Page(path.read_text(encoding='utf-8'))
                     for path in [*COLUMN.glob('阅读*.html'), *COLUMN.glob('index*.html'),
                                  *(COLUMN / 'course').glob('*.html'), *(COLUMN / 'chapters').glob('*/*.html')]}
        cls.indexes = {}
        for language, suffix in (('zh', ''), ('en', '.en')):
            text = (VISUALS / 'reading_site' / f'search-index{suffix}.js').read_text(encoding='utf-8')
            cls.indexes[language] = json.loads(text.split('window.LEARNING_DATA = ', 1)[1].strip().removesuffix(';'))

    def test_both_languages_keep_the_exact_markdown_body(self):
        self.assertEqual(len(self.paths), 23)
        for source in self.paths:
            for suffix in ('', '.en'):
                with self.subTest(article=source.parent.name, language=suffix or 'zh'):
                    markdown = source.with_name(f'README{suffix}.md').read_text(encoding='utf-8')
                    context = reading.build_context(self.paths, 'en' if suffix else 'zh')
                    row = next(row for row in context['records'] if row['path'] == source)
                    page = self.pages[COLUMN / row['url']]
                    def without_urls(value):
                        return re.sub(r'\b(?:href|src|srcset|data-src|data-full-figure)="[^"]*"', '', value)
                    self.assertEqual(without_urls(page.article), without_urls(reading.render_body(markdown, source.with_name(f'README{suffix}.md'))))

    def test_translation_preserves_every_fenced_example_verbatim(self):
        fence = re.compile(r'^```([^\n]*)\n(.*?)^```[ \t]*$', re.M | re.S)
        for source in self.paths:
            with self.subTest(article=source.parent.name):
                chinese = fence.findall(source.read_text(encoding='utf-8'))
                english = fence.findall(source.with_name('README.en.md').read_text(encoding='utf-8'))
                self.assertEqual(english, chinese)

    def test_pending_video_has_no_empty_player(self):
        panel = reading.video_panel({'id': '01', 'video': {'status': 'pending'}}, '../../', 'zh')
        self.assertEqual('', panel)
        self.assertNotIn('<video', panel)
        self.assertNotIn('src=""', panel)

    def test_images_reserve_space_and_defer_images_beyond_the_first(self):
        image = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'first.gif').write_bytes(image)
            (root / 'second.gif').write_bytes(image)
            markup = reading.render_body('# Test\n\n![First](first.gif)\n\n![Second](second.gif)', root / 'README.md')
            images = re.findall(r'<img\b[^>]+>', markup)
            self.assertEqual(len(images), 2)
            for tag in images:
                self.assertIn('width="1" height="1"', tag)
            self.assertIn('loading="eager"', images[0])
            self.assertIn('loading="lazy"', images[1])

    def test_video_requires_a_bilibili_address_and_keeps_audio_language_clear(self):
        row = {'id': '01', 'video': {'status': 'ready', 'audio_language': 'zh-CN',
                                   'bilibili': {'bvid': 'BV1xjHg6ZEFD'}}}
        localized = reading.localize_ui(reading.video_panel(row, '../../', 'en'), 'en')
        self.assertIn('Chinese audio', localized)
        self.assertIn('Watch in HD on Bilibili', localized)
        self.assertIn('autoplay=0', localized)
        self.assertNotIn('<video', localized)

    def test_all_23_videos_link_to_bilibili_without_release_downloads(self):
        data = json.loads((VISUALS / 'reading_site/videos.json').read_text(encoding='utf-8'))
        self.assertEqual({row['id'] for row in data['videos']}, {'intro', '00', 'end', *(f'{n:02d}' for n in range(1, 21))})
        for video in data['videos']:
            with self.subTest(video=video['id']):
                panel = reading.video_panel({'id': video['id'], 'video': video}, '../../', 'en')
                self.assertIn('https://www.bilibili.com/video/' + video['bilibili']['bvid'], panel)
                self.assertIn('data-src="https://player.bilibili.com/player.html?', panel)
                self.assertNotIn('/releases/download/', panel)
                self.assertNotIn('<video', panel)
                self.assertNotIn('kind="subtitles"', panel)
        broken = {**data['videos'][0], 'bilibili': None}
        with self.assertRaisesRegex(ValueError, '缺少 B 站地址'):
            reading.video_panel({'id': 'intro', 'video': broken}, '../../', 'zh')

    def test_search_results_resolve_and_include_folded_answers(self):
        for language, index in self.indexes.items():
            self.assertEqual(len(index['lessons']), 23)
            text_by_page = {}
            for section in index['sections']:
                split = urlsplit(section['url'])
                target = COLUMN / unquote(split.path)
                with self.subTest(language=language, result=section['url']):
                    self.assertIn(target, self.pages)
                    if split.fragment:
                        self.assertIn(unquote(split.fragment), self.pages[target].ids)
                    self.assertEqual(self.pages[target].language, 'en' if language == 'en' else 'zh-CN')
                text_by_page.setdefault(target, []).append(section['text'])
            answer_count = 0
            for target, texts in text_by_page.items():
                searchable = compact(' '.join(texts))
                for answer in self.pages[target].answers:
                    answer_count += 1
                    with self.subTest(language=language, answer_in=str(target.relative_to(COLUMN))):
                        self.assertIn(compact(answer), searchable)
            self.assertGreater(answer_count, 0)

    def test_static_links_and_language_switches_stay_inside_project_path(self):
        for path, page in self.pages.items():
            base = BASE_URL + quote(path.relative_to(COLUMN).as_posix())
            for reference in page.references:
                parsed = urlsplit(reference)
                if parsed.scheme or parsed.netloc:
                    continue
                resolved = urlsplit(urljoin(base, reference))
                with self.subTest(page=path.name, article=path.parent.name, reference=reference):
                    self.assertTrue(resolved.path.startswith('/hello-llm/'), resolved.path)
                    relative = unquote(resolved.path.removeprefix('/hello-llm/'))
                    target = COLUMN / relative
                    self.assertTrue(target.is_file(), relative)
                    if resolved.fragment and target in self.pages:
                        self.assertIn(unquote(resolved.fragment), self.pages[target].ids)
            if page.root:
                self.assertEqual(len(page.switches), 1, str(path))
                alternate = urlsplit(urljoin(base, page.switches[0]))
                target = COLUMN / unquote(alternate.path.removeprefix('/hello-llm/'))
                self.assertEqual(target.parent, path.parent)
                self.assertNotEqual(self.pages[target].language, page.language)
                # 搜索脚本用页面的 data-root 拼接索引 URL；从任一文章也应落回同一站点。
                language = 'en' if page.language == 'en' else 'zh'
                for section in self.indexes[language]['sections']:
                    self.assertEqual(urljoin(base, page.root + section['url']), urljoin(BASE_URL, section['url']))


class LearningSiteExportChecks(unittest.TestCase):
    def setUp(self):
        exporter = VISUALS / 'export_learning_site.py'
        self.assertTrue(exporter.is_file(), '尚未实现独立静态学习站导出')
        self.exporter = load_module('learning_site_export_checks', exporter)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name)
        self.source = self.temporary / 'source'
        self.source.mkdir()
        self.target = self.temporary / 'site'
        self.expected = {
            'index.html', 'index.en.html',
            'chapters/01-测试/index.html', 'chapters/01-测试/index.en.html',
            'chapters/01-测试/README.md', 'chapters/01-测试/README.en.md',
            'chapters/01-测试/images/figure.svg', 'chapters/01-测试/images/lazy.png',
            'assets/brand.png', 'code/visuals/reading_site/site.css',
        }
        self.write('index.html', '<a href="index.en.html">EN</a><a href="chapters/01-测试/index.html">开始</a>'
                   '<link rel="stylesheet" href="code/visuals/reading_site/site.css?v=1">')
        self.write('index.en.html', '<a href="index.html">中文</a><a href="chapters/01-测试/index.en.html">Start</a>')
        for suffix in ('', '.en'):
            self.write(f'chapters/01-测试/index{suffix}.html', f'<a href="README{suffix}.md">Source</a>'
                       '<img src="images/figure.svg"><script>const image = new Image(); image.src="images/lazy.png";</script>')
            self.write(f'chapters/01-测试/README{suffix}.md', '# Lesson\n')
        self.write('chapters/01-测试/images/figure.svg', '<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.write('chapters/01-测试/images/lazy.png', 'test image')
        self.write('assets/brand.png', 'brand image')
        self.write('code/visuals/reading_site/site.css', 'body{background:url("../../../assets/brand.png")}')
        for forbidden in ('chapters/01-测试/images/unused.png', '发布资料/规划.md',
                          'code/artifacts/pretrain.pt', 'code/visuals/build_reading.py'):
            self.write(forbidden, 'not a runtime resource')

    def write(self, relative, content):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def export(self):
        return self.exporter.export(self.target, source=self.source)

    def test_offline_site_preserves_licenses_and_required_notices(self):
        names = ('LICENSE', 'LICENSE-CONTENT', 'NOTICE', 'LICENSING.md')
        for name in names:
            self.write('code/' + name, 'Original terms: ' + name)
        self.write('LICENSE', 'Root license takes precedence')
        self.export()
        for name in names:
            expected = 'Root license takes precedence' if name == 'LICENSE' else 'Original terms: ' + name
            self.assertEqual((self.target / name).read_text(encoding='utf-8'), expected)

    def test_release_download_has_a_bundled_offline_copy(self):
        asset = 'dist/v0.1.0/hello-llm-v0.1.0-zh-CN.pdf'
        self.write(asset, 'PDF fixture')
        self.write('index.html', '<a href="https://example.org/releases/download/v0.1.0/book.pdf" '
                   f'data-offline-href="{asset}">PDF</a>')
        self.export()
        self.assertEqual((self.target / asset).read_text(), 'PDF fixture')

    def test_share_preview_is_available_in_the_offline_site(self):
        self.write('assets/social-preview.png', 'share image fixture')
        self.write('index.html', '<link rel="image_src" href="assets/social-preview.png">')
        self.export()
        self.assertEqual((self.target / 'assets/social-preview.png').read_text(), 'share image fixture')

    def test_picture_packages_desktop_svg_and_mobile_fallback(self):
        self.write('chapters/01-测试/images/web/figure.svg', '<svg xmlns="http://www.w3.org/2000/svg"/>')
        path = self.source / 'chapters/01-测试/index.html'
        path.write_text(path.read_text() + '<picture><source media="(min-width:900px)" srcset="images/web/figure.svg"><img src="images/figure.svg"></picture>')
        self.export()
        self.assertTrue((self.target / 'chapters/01-测试/images/web/figure.svg').is_file())
        self.assertTrue((self.target / 'chapters/01-测试/images/figure.svg').is_file())

    def test_three_labs_keep_bundles_license_and_linked_readable_sources_offline(self):
        resources = {
            'code/visuals/reading_site/' + name for name in
            ('tensor3d.js', 'surface3d.js', 'embedding3d.js', 'rope3d.js',
             'model3d.js', 'tensor3d-LICENSE.txt')
        } | {
            'code/artifacts/lessons/l07.json',
            'code/artifacts/lessons/l13.json',
            'code/artifacts/first_run/forward_trace.json',
            'code/tiny_lm/rope.py', 'code/tiny_lm/model.py',
        }
        for name in resources:
            self.write(name, 'readable lab reference')
        self.write('index.html', ''.join(f'<a href="{name}">Reference</a>' for name in resources))
        self.export()
        for name in resources:
            self.assertEqual((self.target / name).read_text(), 'readable lab reference')
        self.assertFalse((self.target / 'code/artifacts/pretrain.pt').exists())

    def test_export_follows_references_and_omits_unlinked_author_files(self):
        self.export()
        actual = {path.relative_to(self.target).as_posix() for path in self.target.rglob('*') if path.is_file()}
        self.assertEqual(actual, self.expected | {'index.html', '.nojekyll', '.learning-site-export'})
        self.assertEqual((self.target / 'index.html').read_bytes(), (self.source / 'index.html').read_bytes())

    def test_ready_video_copies_only_referenced_video_posters_and_captions(self):
        media = {'assets/videos/01-测试/lesson.mp4', 'assets/videos/01-测试/lesson.webm',
                 'assets/videos/01-测试/封面.PNG', 'assets/videos/01-测试/cover.JPG', 'assets/videos/01-测试/captions.en.vtt'}
        for relative in media:
            self.write(relative, 'runtime media: ' + relative)
        for suffix, poster in (('', '封面.PNG'), ('.en', 'cover.JPG')):
            page = f'chapters/01-测试/index{suffix}.html'
            markup = (self.source / page).read_text(encoding='utf-8')
            markup += (f'<video controls src="../../assets/videos/01-测试/lesson.mp4" '
                       f'poster="../../assets/videos/01-测试/{poster}">'
                       '<source src="../../assets/videos/01-测试/lesson.webm" type="video/webm">'
                       '<track kind="captions" src="../../assets/videos/01-测试/captions.en.vtt" srclang="en">'
                       '</video>')
            self.write(page, markup)
        self.write('assets/videos/02-待制作/unfinished.mp4', 'not linked from HTML')
        self.write('assets/videos/01-测试/old-cover.png', 'unused cover')
        self.write('发布资料/学习站/视频清单.json', '{"02":{"status":"pending"}}')
        self.export()
        actual = {path.relative_to(self.target).as_posix() for path in self.target.rglob('*') if path.is_file()}
        self.assertEqual(actual, self.expected | media | {'index.html', '.nojekyll', '.learning-site-export'})
        for relative in media:
            self.assertEqual((self.target / relative).read_bytes(), (self.source / relative).read_bytes())

    def test_video_directory_does_not_admit_plans_scripts_or_weights(self):
        for name in ('制作计划.md', '编辑记录.json', 'render.py', 'checkpoint.pt'):
            with self.subTest(name=name):
                relative = 'assets/videos/01-测试/' + name
                self.write(relative, 'author-only content')
                self.write('index.html', f'<a href="{relative}">Author material</a>')
                with self.assertRaises(ValueError):
                    self.export()
                self.assertFalse(self.target.exists())

    def test_existing_unowned_directory_is_never_overwritten(self):
        self.target.mkdir()
        original = self.target / 'personal.txt'
        original.write_text('keep this', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.export()
        self.assertEqual(original.read_text(encoding='utf-8'), 'keep this')
        self.assertEqual(list(self.target.iterdir()), [original])

    def test_missing_dependency_keeps_previous_complete_export(self):
        self.export()
        previous = (self.target / 'index.html').read_bytes()
        self.write('index.html', '<img src="chapters/01-测试/images/missing.png">')
        with self.assertRaises(FileNotFoundError):
            self.export()
        self.assertEqual((self.target / 'index.html').read_bytes(), previous)

    def test_linked_author_source_is_rejected_before_copying(self):
        self.write('index.html', '<a href="code/visuals/build_reading.py">Author source</a>')
        with self.assertRaises(ValueError):
            self.export()
        self.assertFalse(self.target.exists())

    def test_reexport_removes_resources_that_are_no_longer_used(self):
        self.export()
        for suffix in ('', '.en'):
            self.write(f'chapters/01-测试/index{suffix}.html', f'<a href="README{suffix}.md">Source</a>')
        self.export()
        self.assertFalse((self.target / 'chapters/01-测试/images').exists())
        self.assertTrue((self.target / 'chapters/01-测试/README.en.md').is_file())



if __name__ == '__main__':
    unittest.main()

"""阅读页的正文必须逐字来自当前 Markdown，旧构建不能静默通过。"""
import importlib.util
import html
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_reading', ROOT / 'visuals/build_reading.py')
reading = None
if importlib.util.find_spec('markdown') is not None:
    reading = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reading)


@unittest.skipIf(reading is None, '阅读页检查需要网站依赖 Markdown')
class ReadingSourceChecks(unittest.TestCase):
    def test_local_clone_keeps_online_downloads_until_book_files_are_present(self):
        context = {'language': 'zh', 'asset_version': 'test', 'content_version': 'test'}
        with tempfile.TemporaryDirectory() as folder, patch.object(reading, 'COLUMN', Path(folder)):
            self.assertNotIn('data-offline-bundle=', reading.page_head('Test', context, './'))
            for suffix in ('.pdf', '.epub'):
                target = Path(folder) / reading.BOOK_DIR / (reading.BOOK_STEM + suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'fixture')
            self.assertIn('data-offline-bundle="true"', reading.page_head('Test', context, './'))

    def test_experiment_is_discoverable_inside_article_without_eager_loading(self):
        source = next((reading.COLUMN / 'chapters').glob('01-*/README.md'))
        body = reading.render_body(source.read_text(encoding='utf-8'), source)
        self.assertIn('class="inline-experiment"', body)
        self.assertIn('data-src="walkthrough.html"', body)
        self.assertNotIn('src="walkthrough.html"', body.replace('data-src=', 'deferred='))
        self.assertEqual(body.count('class="inline-experiment"'), 1)

    def test_language_switch_has_matching_destinations_for_every_section(self):
        paths = reading.article_paths()
        contexts = [reading.build_context(paths, language) for language in ('zh', 'en')]
        for source in paths:
            pages = [reading.build_document(source, paths, context) for context in contexts]
            anchors = [re.findall(r'<h2\b[^>]*\bid="([^"]+)"', page) for page in pages]
            self.assertEqual(len(anchors[0]), len(anchors[1]), source.parent.name)
            for index, page in enumerate(pages):
                mapping = re.search(r'data-alternate-sections="([^"]*)"', page).group(1)
                self.assertEqual(json.loads(html.unescape(mapping)), anchors[1 - index])

    def test_diagrams_offer_vectors_for_full_size_reading(self):
        source = next((reading.COLUMN / 'chapters').glob('02-*/README.md'))
        body = reading.render_body(source.read_text(encoding='utf-8'), source)
        self.assertIn('src="images/01-机制.svg"', body)
        source = next((reading.COLUMN / 'chapters').glob('19-*/README.md'))
        body = reading.render_body(source.read_text(encoding='utf-8'), source)
        self.assertIn('data-full-figure=', body)
        self.assertIn('.svg"', body.split('data-full-figure=', 1)[1].split('>', 1)[0])

    def test_three_experiments_are_lazy_and_labelled_for_their_content(self):
        labels = {'04': ('三维损失曲面', '3D loss surface'),
                  '07': ('三维 Embedding 查表', '3D embedding lookup'),
                  '12': ('三维张量实验', '3D tensor lab'),
                  '13': ('三维 RoPE 实验', '3D RoPE lab'),
                  '16': ('三维模型解剖台', '3D model inspector')}
        for number, names in labels.items():
            for suffix, label in zip(('', '.en'), names):
                with self.subTest(number=number, language=suffix):
                    source = next((reading.COLUMN / 'chapters').glob(f'{number}-*/README{suffix}.md'))
                    body = reading.render_body(source.read_text(encoding='utf-8'), source)
                    filename = f'lab3d{suffix}.html'
                    self.assertIn(label, body)
                    self.assertIn(f'data-src="{filename}"', body)
                    self.assertNotIn(f'src="{filename}"', body.replace('data-src=', 'deferred='))
                    self.assertIn('class="js-experiment inline-expand"', body)
                    if number != '04':
                        self.assertNotIn('三维损失曲面', body)
                        self.assertNotIn('Loss surface', body)

    def test_web_downloads_target_the_matching_release(self):
        context = reading.build_context(reading.article_paths())
        page = reading.build_index(reading.article_paths(), context)
        tag = 'v' + reading.RELEASE['version']
        self.assertIn('/releases/download/' + tag + '/', page)
        self.assertIn('data-offline-href="dist/' + tag + '/', page)

    def test_reading_has_no_manual_completion_or_raw_source_action(self):
        source = next((reading.COLUMN / 'chapters').glob('01-*/README.md'))
        page = reading.build_document(source)
        self.assertNotIn('data-complete=', page)
        self.assertNotIn('查看 Markdown 原文', page)
        self.assertNotIn('class="stage-index">01', page)

    def test_repository_navigation_does_not_duplicate_website_navigation(self):
        source = next((reading.COLUMN / 'chapters').glob('01-*/README.md'))
        raw = source.read_text(encoding='utf-8')
        self.assertIn('<!-- chapter-navigation:start -->', raw)
        body = reading.render_body(raw, source)
        self.assertNotIn('chapter-navigation:', body)
        self.assertNotIn('../../README.md', body)
        self.assertEqual(reading.build_document(source).count('class="chapter-nav"'), 1)

    def test_share_metadata_points_to_the_public_article_in_each_language(self):
        source = next((reading.COLUMN / 'chapters').glob('01-*/README.md'))
        for language in ('zh', 'en'):
            context = reading.build_context(reading.article_paths(), language)
            page = reading.build_document(source, context=context)
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page).group(1)
            self.assertTrue(canonical.startswith('https://daviddingxu.github.io/hello-llm/'))
            self.assertTrue(canonical.endswith('.en.html' if language == 'en' else '.html'))
            self.assertIn('property="og:description"', page)
            self.assertIn('assets/social-preview.png', page)
            self.assertIn('class="copy-page-link js-only"', page)

    def test_home_offers_training_and_a_clear_learning_start_before_optional_resources(self):
        paths = reading.article_paths()
        for language, suffix in (('zh', ''), ('en', '.en')):
            with self.subTest(language=language):
                context = reading.build_context(paths, language)
                page = reading.build_index(paths, context)
                hero = page.split('class="hero-actions"', 1)[1].split('</div>', 1)[0]
                self.assertEqual(hero.count('<a '), 2)
                self.assertIn(f'href="course/20{suffix}.html#training-lab"', hero)
                self.assertIn(f'id="continue-learning" href="course/01{suffix}.html"', hero)
                self.assertNotIn('href="#downloads"', hero)
                self.assertIn('id="downloads"', page)
                self.assertLess(page.index('id="curriculum"'), page.index('id="experiments"'))
                self.assertLess(page.index('id="curriculum"'), page.index('id="videos"'))
                # Existing deep links still reach their resources, but extras start folded.
                self.assertRegex(page, r'<details[^>]*id="videos"[^>]*>')
                self.assertNotRegex(page, r'<details[^>]*id="videos"[^>]*\bopen\b')
                self.assertNotIn('class="model-pipeline"', page)

    def test_feedback_links_carry_the_current_chapter_and_public_location(self):
        for language in ('zh', 'en'):
            context = reading.build_context(reading.article_paths(), language)
            row = next(r for r in context['records'] if r['id'] == '17')
            panel = reading.reader_feedback(row, context)
            links = re.findall(r'href="([^"]+)"', panel)
            self.assertEqual(len(links), 2)
            for link in links:
                parsed = urlsplit(html.unescape(link))
                query = parse_qs(parsed.query)
                self.assertEqual(parsed.netloc, 'github.com')
                self.assertIn(query['template'][0], ('question.yml', 'content.yml'))
                self.assertIn(row['title'], query['title'][0])
                self.assertIn('v' + reading.RELEASE['version'], query['location'][0])
                self.assertIn('https://daviddingxu.github.io/hello-llm/', query['location'][0])

    def test_every_article_body_is_current_markdown_render(self):
        context = reading.build_context(reading.article_paths())
        for source in reading.article_paths():
            with self.subTest(article=source.parent.name):
                row = next(row for row in context['records'] if row['path'] == source)
                page = (reading.COLUMN / row['url']).read_text(encoding='utf-8')
                body = page.split('<article id="article-body">', 1)[1].split('</article>', 1)[0]
                # 移动阅读页只允许改变资源地址，正文与代码仍逐字保留。
                def without_urls(value):
                    return re.sub(r'\b(?:href|src|srcset|data-src|data-full-figure)="[^"]*"', '', value)
                self.assertEqual(without_urls(body), without_urls(reading.render_body(source.read_text(encoding='utf-8'), source)))
                expected = reading.source_digest(source.read_text(encoding='utf-8'))
                self.assertEqual(re.search(r'name="source-sha256" content="([a-f0-9]+)"', page).group(1), expected)

    def test_public_chapter_addresses_are_ascii_and_keep_legacy_hash_redirects(self):
        for language in ('zh', 'en'):
            context = reading.build_context(reading.article_paths(), language)
            for row in context['records']:
                self.assertTrue(row['url'].isascii())
                self.assertRegex(row['url'], r'^course/(?:intro|end|\d{2})(?:\.en)?\.html$')
                legacy = row['path'].with_name('index.en.html' if language == 'en' else 'index.html').read_text()
                self.assertIn('../../' + row['url'], legacy)
                self.assertIn('location.search + location.hash', legacy)

    def test_inline_bilibili_player_is_deferred_and_offers_an_hd_watch_link(self):
        data = reading.build_context(reading.article_paths())['records'][0]
        video = {**data['video'], 'bilibili': {'bvid': 'BV1edHT6eEGr', 'part': 1}}
        panel = reading.video_panel({**data, 'video': video}, '../', 'zh')
        self.assertIn('class="bilibili-embed"', panel)
        self.assertIn('data-src="https://player.bilibili.com/player.html?', panel)
        self.assertIn('bvid=BV1edHT6eEGr&amp;p=1&amp;autoplay=0', panel)
        self.assertNotIn('src="https://player.bilibili.com/', panel.replace('data-src=', 'deferred='))
        self.assertIn('B 站高清观看', panel)
        self.assertIn('href="https://www.bilibili.com/video/BV1edHT6eEGr/?p=1"', panel)
        self.assertNotIn('<video', panel)
        self.assertNotIn('releases/download', panel)
        self.assertNotIn('.mp4', panel)
        with self.assertRaisesRegex(ValueError, '标识无效'):
            reading.video_panel({**data, 'video': {**video, 'bilibili': {'bvid': 'bad'}}}, '../', 'zh')

    def test_a_markdown_edit_changes_content_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'README.md'
            path.write_text('# 标题\n\n原来内容\n', encoding='utf-8')
            before = reading.build_document(path, [path])
            path.write_text('# 标题\n\n新的解释\n', encoding='utf-8')
            after = reading.build_document(path, [path])
            self.assertNotEqual(before, after)
            self.assertIn('<p>新的解释</p>', after)
            self.assertNotIn('<p>原来内容</p>', after)

    def test_folded_answer_keeps_markdown_code_and_images_readable(self):
        # 折叠不能把内部的代码围栏或图片原样打印成Markdown文本。
        source = ('# 练习\n\n<details class="answer" markdown="1">\n'
                  '<summary>展开答案</summary>\n\n答案是 **4**。\n\n'
                  '```python\nprint(2 + 2)\n```\n\n![计算路径](images/路径.png)\n\n</details>\n')
        body = reading.render_body(source)
        self.assertIn('<strong>4</strong>', body)
        self.assertIn('<code class="language-python">print(2 + 2)', body)
        self.assertIn('src="images/路径.png"', body)
        self.assertNotIn('```python', body)
        self.assertNotRegex(body, r'<details[^>]*\bopen\b')

    def test_section_links_resolve_when_headings_repeat(self):
        # 同名标题仍应各自定位到对应段落，不能两项都跳向第一处。
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'README.md'
            path.write_text('# 标题\n\n## 先读图\n\n第一段\n\n'
                            '## 先读图\n\n第二段\n', encoding='utf-8')
            page = reading.build_document(path, [path])
            destinations = re.findall(r'<h2 id="([^"]+)"', page)
            self.assertEqual(len(set(destinations)), 2)
            navigation = page.split('<nav class="reading-route"', 1)[1].split('</nav>', 1)[0]
            links = re.findall(r'href="#([^"]+)"', navigation)
            self.assertEqual(links, destinations)


if __name__ == '__main__':
    unittest.main()

"""绝对网站链接也必须落到实际交付的页面，避免相对链接检查漏报。"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visuals.check_reader_links import check_links


class ReaderLinkChecks(unittest.TestCase):
    def test_legacy_hash_redirect_checks_the_destination_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'current.html').write_text('<section id="lab">实验</section>', encoding='utf-8')
            (root / 'old.html').write_text('<meta http-equiv="refresh" content="0;url=current.html"><script>location.replace("current.html" + location.search + location.hash);</script>', encoding='utf-8')
            (root / 'README.md').write_text('[实验](old.html#lab)\n[错误](old.html#missing)', encoding='utf-8')
            _, issues = check_links(root)
            self.assertEqual(len(issues), 1)
            self.assertIn('#missing', issues[0])

    def test_redirect_cycle_does_not_hide_a_missing_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, target in [('a', 'b'), ('b', 'a')]:
                (root / f'{name}.html').write_text(f'<meta http-equiv="refresh" content="0;url={target}.html"><script>location.replace("{target}.html" + location.hash);</script>', encoding='utf-8')
            (root / 'README.md').write_text('[错误](a.html#missing)', encoding='utf-8')
            _, issues = check_links(root)
            self.assertEqual(len(issues), 1)
            self.assertIn('页面锚点不存在', issues[0])

    def test_missing_absolute_course_page_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('[回放](https://daviddingxu.github.io/hello-llm/chapters/17/training-replay.html)', encoding='utf-8')
            count, issues = check_links(root)
            self.assertEqual(count, 1)
            self.assertEqual(len(issues), 1)
            self.assertIn('目标文件不存在', issues[0])

    def test_encoded_paths_and_html_fragments_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '实验.html').write_text('<section id="运行">实验</section>', encoding='utf-8')
            (root / 'README.md').write_text('[实验](%E5%AE%9E%E9%AA%8C.html#%E8%BF%90%E8%A1%8C)\n[错误](实验.html#不存在)', encoding='utf-8')
            count, issues = check_links(root)
            self.assertEqual(count, 2)
            self.assertEqual(len(issues), 1)
            self.assertIn('页面锚点不存在', issues[0])

    def test_github_source_links_check_the_delivered_file_and_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'model.py').write_text('value = 1\n', encoding='utf-8')
            (root / 'README.md').write_text('[源码](https://github.com/DavidDingXu/hello-llm/blob/main/model.py#L2)\n[外部文档](https://example.com/not-a-local-file)', encoding='utf-8')
            count, issues = check_links(root)
            self.assertEqual(count, 1)
            self.assertIn('源码行号不存在', issues[0])

    def test_relative_parent_paths_cannot_leave_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'README.md').write_text('[文件](../outside.md)', encoding='utf-8')
            _, issues = check_links(root)
            self.assertIn('链接越出仓库目录', issues[0])


if __name__ == '__main__':
    unittest.main()

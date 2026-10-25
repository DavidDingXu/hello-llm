"""教学日志必须观察实际计算，且不能改变结果或把 trace 留到下一次运行。"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tiny_lm.scalar import forward
from tiny_lm.teaching import observe_lesson


class TeachingLogTests(unittest.TestCase):
    def test_logs_follow_changed_input_instead_of_a_saved_example(self):
        text = io.StringIO()
        previous = sys.gettrace()
        with contextlib.redirect_stdout(text), observe_lesson(1, verbose=True):
            result = forward([3, 2], [1, 3], -1)
        self.assertEqual(result, 8)
        self.assertIn('inputs = [3, 2]', text.getvalue())
        self.assertIn('total = 9.0', text.getvalue())
        self.assertIn('return = 8.0', text.getvalue())
        self.assertIs(sys.gettrace(), previous)

    def test_failure_restores_previous_trace(self):
        previous = sys.gettrace()
        text = io.StringIO()
        with contextlib.redirect_stdout(text):
            with self.assertRaises(ValueError), observe_lesson(1, verbose=True):
                forward([], [], 0)
        self.assertIs(sys.gettrace(), previous)
        self.assertIn('抛出异常：ValueError', text.getvalue())
        self.assertNotIn('返回值已算出', text.getvalue())

    def test_step_can_continue_and_produces_same_gradients_and_update(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for flags, stdin in [([], ''), (['--verbose'], ''), (['--step'], '\nc\n')]:
                target = Path(directory) / f'{len(outputs)}.json'
                run = subprocess.run([sys.executable, '-m', 'lessons.l05', *flags, '--out', str(target)],
                    input=stdin, text=True, capture_output=True, cwd=root, encoding='utf-8', timeout=30)
                self.assertEqual(run.returncode, 0, run.stderr)
                outputs.append(json.loads(target.read_text(encoding='utf-8')))
                if flags:
                    self.assertIn('d_output = -4.0', run.stdout)
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0], outputs[2])


if __name__ == '__main__':
    unittest.main()

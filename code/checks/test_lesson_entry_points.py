"""运行入口必须执行读者正在修改的实现，训练步数必须影响本次结果。"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lessons import experiments


class LessonEntryTests(unittest.TestCase):
    def test_training_without_out_preserves_the_saved_first_run(self):
        """读者直接启动训练时，新实验不能覆盖随课提供的原权重。"""
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='new-reader-run-') as temporary:
            folder = Path(temporary)
            # 隔离真实代码与数据输出，不让这次集成检查改动课程源目录。
            shutil.copytree(root / 'tiny_lm', folder / 'tiny_lm',
                            ignore=shutil.ignore_patterns('__pycache__'))
            original = folder / 'artifacts/first_run/pretrain.pt'
            original.parent.mkdir(parents=True)
            original_bytes = b'original reader checkpoint'
            original.write_bytes(original_bytes)
            run = subprocess.run(
                [sys.executable, '-m', 'tiny_lm.train', '--smoke'],
                cwd=folder, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(original.read_bytes() == original_bytes,
                            '未指定--out的新训练覆盖了原始实验')
            for stage in ('initial', 'pretrain', 'sft'):
                self.assertTrue((folder / f'artifacts/my_run/{stage}.pt').is_file())

    def test_removing_relu_changes_the_lesson03_experiment(self):
        """模拟读者把 ReLU 改成原样通过；两条差值分支应重新抵消。"""
        self.assertEqual([r['y'] for r in experiments.lesson03()['rows']], [0, 1, 1, 0])
        with patch('tiny_lm.manual_mlp.relu', lambda value: value):
            rows = experiments.lesson03()['rows']
        self.assertEqual([r['y'] for r in rows], [0, 0, 0, 0])

    def test_lesson06_cli_runs_the_requested_updates(self):
        """0 步只检查初值，1 步应产生不同结果；输出不应总是旧的500步记录。"""
        root = Path(__file__).resolve().parents[1]
        records = []
        with tempfile.TemporaryDirectory(prefix='lesson-entry-') as temporary:
            for steps in (0, 1):
                output = Path(temporary) / f'xor-{steps}.json'
                run = subprocess.run(
                    [sys.executable, '-m', 'lessons.l06', '--steps', str(steps),
                     '--out', str(output)],
                    cwd=root, capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(run.returncode, 0, run.stderr)
                record = json.loads(output.read_text(encoding='utf-8'))['xor']
                self.assertEqual(record['steps'], steps)
                self.assertIn('xor', run.stdout)
                self.assertIn('predictions', run.stdout)
                records.append(record)
        self.assertAlmostEqual(records[0]['final_loss'], 0.47225, places=6)
        self.assertLess(records[1]['final_loss'], records[0]['final_loss'])


if __name__ == '__main__':
    unittest.main()

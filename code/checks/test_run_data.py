"""每次训练的数据应随运行保存，改事实不能改变旧实验或伪造回放来源。"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from lessons.training_replay import build_training_replay
from tiny_lm import data
from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.train import compare_stages, run_pretrain, run_sft

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / 'artifacts/first_run'
ORIGINAL_FACTS = [('小丁', '红色', '苹果'), ('小周', '黄色', '香蕉'),
                  ('小陈', '紫色', '葡萄'), ('小李', '绿色', '梨子'),
                  ('小王', '红色', '草莓'), ('小赵', '黄色', '柠檬'),
                  ('小吴', '绿色', '西瓜'), ('小何', '紫色', '桑葚')]
SWAPPED_FACTS = [('小丁', '黄色', '香蕉'), ('小周', '红色', '苹果'), *ORIGINAL_FACTS[2:]]


def _digests(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.iterdir() if p.is_file()}


class RunDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='训练快照 ')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.run_directory = Path(cls.temporary.name) / 'swapped_run'
        cls.reference_before = _digests(ROOT / 'data')
        with patch.object(data, 'FACTS', SWAPPED_FACTS):
            checkpoint = run_pretrain(cls.run_directory, steps=1)
        # 两阶段之间恢复生成规则；SFT 必须仍使用预训练运行里保存的记录。
        with patch.object(data, 'FACTS', ORIGINAL_FACTS):
            run_sft(checkpoint, cls.run_directory, steps=1)
        compare_stages(cls.run_directory)
        cls.reference_after = _digests(ROOT / 'data')

    def test_training_saves_exact_records_vocabulary_and_manifest_in_its_run(self):
        snapshot = self.run_directory / 'data'
        self.assertTrue((snapshot / 'manifest.json').is_file())
        manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
        first = json.loads((snapshot / 'pretrain_train.jsonl').read_text(encoding='utf-8').splitlines()[0])
        self.assertEqual(first['text'], '早上，小丁喜欢黄色的香蕉。')
        _, tokenizer, metadata = load_checkpoint(self.run_directory / 'pretrain.pt')
        self.assertEqual(json.loads((snapshot / 'vocab.json').read_text(encoding='utf-8')),
                         tokenizer.to_dict())
        self.assertEqual(hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
                         metadata['dataset_hash'])
        for name, entry in manifest['files'].items():
            content = (snapshot / name).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry['sha256'])
            self.assertEqual(len(content.splitlines()), entry['records'])

    def test_new_training_does_not_overwrite_the_reference_dataset(self):
        self.assertEqual(self.reference_before, self.reference_after)

    def test_sft_keeps_the_pretraining_records_when_generator_changes(self):
        report = json.loads((self.run_directory / 'sft_log.json').read_text(encoding='utf-8'))
        self.assertEqual(report['answers']['sft_train'][0]['expected'], '黄色的香蕉。')
        self.assertEqual(report['answers']['sft_train'][1]['expected'], '红色的苹果。')

    def test_sft_to_another_directory_carries_the_same_snapshot(self):
        destination = Path(self.temporary.name) / 'sft_only'
        with patch.object(data, 'FACTS', ORIGINAL_FACTS):
            run_sft(self.run_directory / 'pretrain.pt', destination, steps=1)
        self.assertTrue((destination / 'data/manifest.json').is_file())
        self.assertEqual(_digests(self.run_directory / 'data'), _digests(destination / 'data'))
        report = json.loads((destination / 'sft_log.json').read_text(encoding='utf-8'))
        self.assertEqual(report['answers']['sft_train'][0]['expected'], '黄色的香蕉。')

    def test_replay_uses_run_snapshot_after_generator_changes(self):
        with patch.object(data, 'FACTS', ORIGINAL_FACTS):
            report = build_training_replay(self.run_directory)
        self.assertEqual(report['sft_example']['record']['answer'], '黄色的香蕉。')
        self.assertEqual(report['provenance']['dataset_source'], 'run_snapshot')
        self.assertTrue(report['provenance']['dataset_hash_matches_sources'])
        self.assertTrue(report['provenance']['original_files_unchanged'])


class ReplayDataIntegrityTests(unittest.TestCase):
    def test_first_run_replays_its_original_records_with_swapped_generator(self):
        with patch.object(data, 'FACTS', SWAPPED_FACTS):
            report = build_training_replay(FIRST)
        self.assertEqual(report['sft_example']['record']['answer'], '红色的苹果。')
        self.assertEqual(report['provenance']['dataset_source'], 'run_snapshot')

    def test_bad_snapshot_is_rejected_without_falling_back_to_generator(self):
        for damage in ('content', 'manifest', 'vocabulary', 'missing_file'):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary) / 'run'
                shutil.copytree(FIRST, directory)
                snapshot = directory / 'data'
                if damage in ('content', 'manifest'):
                    path = snapshot / 'sft_train.jsonl'
                    content = path.read_text(encoding='utf-8').replace('红色的苹果。', '黄色的香蕉。', 1)
                    path.write_text(content, encoding='utf-8', newline='\n')
                    if damage == 'manifest':
                        path = snapshot / 'manifest.json'
                        manifest = json.loads(path.read_text(encoding='utf-8'))
                        manifest['files']['sft_train.jsonl']['sha256'] = hashlib.sha256(content.encode()).hexdigest()
                        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
                elif damage == 'vocabulary':
                    path = snapshot / 'vocab.json'
                    vocab = json.loads(path.read_text(encoding='utf-8'))
                    vocab['tokens'][4], vocab['tokens'][5] = vocab['tokens'][5], vocab['tokens'][4]
                    path.write_text(json.dumps(vocab, ensure_ascii=False), encoding='utf-8')
                else:
                    (snapshot / 'sft_val.jsonl').unlink()
                with self.assertRaisesRegex(ValueError, '快照|词表|摘要'):
                    build_training_replay(directory)

    def test_legacy_run_only_replays_when_generator_still_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'run'
            shutil.copytree(FIRST, directory)
            shutil.rmtree(directory / 'data')
            with patch.object(data, 'FACTS', ORIGINAL_FACTS):
                report = build_training_replay(directory)
            self.assertEqual(report['provenance']['dataset_source'], 'validated_current_generator')
            self.assertFalse((directory / 'data').exists())
            with patch.object(data, 'FACTS', SWAPPED_FACTS):
                with self.assertRaisesRegex(ValueError, '快照|摘要'):
                    build_training_replay(directory)


if __name__ == '__main__':
    unittest.main()

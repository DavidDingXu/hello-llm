"""回放检查关注监督边界与参数变化时点，不以曲线好看作为正确性依据。"""
import hashlib
import json
import math
import random
import shutil
import tempfile
import unittest
from pathlib import Path

import torch

from lessons.training_replay import build_training_replay
from tiny_lm.data import make_pretrain_batch
from tiny_lm.tokenizer import CharTokenizer

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / 'artifacts/first_run'


class TrainingReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 构建一次真实首步回放；前后直接核对原始权重文件的字节摘要。
        paths = [FIRST / f'{stage}.pt' for stage in ('initial', 'pretrain', 'sft')]
        cls.before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        cls.groups = {p.stem: [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
                      for p in (FIRST / 'data').glob('*.jsonl')}
        cls.tokenizer = CharTokenizer.from_dict(
            json.loads((FIRST / 'data/vocab.json').read_text(encoding='utf-8')))
        cls.report = build_training_replay()
        cls.after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

    def test_batch_targets_are_shifted_and_include_eos_but_ignore_padding(self):
        first = self.report['first_step']
        records = random.Random(42).sample(self.groups['pretrain_train'], 16)
        tokenizer = self.tokenizer
        x, y = make_pretrain_batch(records, tokenizer)
        row = first['batch']['representative']
        self.assertEqual(first['batch']['record_ids'], [r['record_id'] for r in records])
        self.assertEqual(row['input_ids'], x[0].tolist())
        self.assertEqual(row['target_ids'], y[0].tolist())
        self.assertEqual(row['input_ids'][0], 1)
        self.assertEqual(row['target_tokens'][0], records[0]['text'][0])
        last = row['eos_target_positions'][0]
        self.assertEqual(row['target_ids'][last], 2)
        self.assertEqual(row['input_tokens'][last], records[0]['text'][-1])
        self.assertEqual(last, len(records[0]['text']))
        for i in range(last):
            self.assertEqual(row['target_ids'][i], row['input_ids'][i + 1])
        for i in row['padding_positions']:
            self.assertEqual(row['input_ids'][i], 0)
            self.assertEqual(row['target_ids'][i], -100)
            self.assertFalse(row['loss_mask'][i])
        self.assertEqual(first['valid_target_count'], int((y != -100).sum()))
        self.assertEqual(first['valid_target_count'], sum(len(r['text']) + 1 for r in records))
        self.assertEqual(first['shapes']['logits'], [16, 32, 79])
        trace = first['forward']['shape_trace']
        self.assertEqual([row['name'] for row in trace],
                         ['input', 'embedding', 'block1', 'block2', 'final_norm', 'logits'])
        self.assertEqual(trace[1]['shape'], [16, 32, 64])
        self.assertEqual(trace[-1]['shape'], [16, 32, 79])
        target = first['target_probability']
        self.assertEqual(target['target_id'], row['target_ids'][target['position']])
        scores = target['logits']
        weights = [math.exp(s - max(scores)) for s in scores]
        expected = weights[target['target_id']] / sum(weights)
        self.assertAlmostEqual(target['probability'], expected, places=7)

    def test_sft_first_answer_eos_and_prompt_mask_have_correct_boundaries(self):
        row = self.report['sft_example']
        first = row['first_answer_index']
        self.assertEqual(first, row['prefix_length'] - 1)
        self.assertEqual(first, 14)
        self.assertTrue(all(y == -100 for y in row['target_ids'][:first]))
        self.assertEqual(row['input_tokens'][first], '：')
        self.assertEqual(row['target_tokens'][first], '红')
        self.assertEqual(row['valid_target_count'], len(row['record']['answer']) + 1)
        self.assertEqual(row['valid_target_count'], 7)
        self.assertEqual(row['target_ids'][row['eos_target_positions'][0]], 2)
        self.assertTrue(all(row['target_ids'][i] == -100 for i in row['padding_positions']))

    def test_backward_and_clipping_leave_parameters_until_optimizer_step(self):
        first = self.report['first_step']
        digests = first['parameter_digests']
        for name in ('after_forward', 'after_backward', 'after_clip'):
            self.assertEqual(digests['initial'], digests[name])
        self.assertNotEqual(digests['initial'], digests['after_optimizer'])
        gradient = first['gradient_norm']
        self.assertLessEqual(gradient['after_clip'], gradient['max_norm'] + 1e-5)
        scale = min(1., gradient['max_norm'] / (gradient['before_clip'] + 1e-6))
        observed = first['observed_parameter']
        self.assertAlmostEqual(observed['gradient_after_clip'],
                               observed['gradient_before_clip'] * scale, places=7)
        self.assertAlmostEqual(observed['update'],
                               observed['value_after'] - observed['value_before'], places=12)
        changes = first['aggregate_parameter_change']
        self.assertEqual(changes['total_coordinates'], 92352)
        self.assertGreater(changes['changed_coordinates'], 1)
        self.assertEqual(self.before, self.after)

    def test_histories_are_original_samples_without_interpolated_updates(self):
        for stage, steps in [('pretrain', 1000), ('sft', 300)]:
            source = json.loads((FIRST / f'{stage}_log.json').read_text(encoding='utf-8'))
            history = self.report['histories'][stage]
            self.assertEqual(history['history'], source['history'])
            self.assertEqual([r['step'] for r in history['history']], list(range(0, steps + 1, 50)))
            self.assertFalse(history['interpolated'])
            self.assertFalse(history['intermediate_checkpoints_saved'])
        self.assertEqual(self.report['first_step']['source'], 'replayed_from_saved_initial_checkpoint')
        comparison = json.loads((FIRST / 'generation_comparison.json').read_text(encoding='utf-8'))
        self.assertEqual(self.report['saved_generation_comparison'], comparison)

    def test_generation_probabilities_mask_specials_without_changing_loss_distribution(self):
        for prefix in self.report['prefix_comparisons']:
            for stage in prefix['stages'].values():
                raw = stage['raw_probabilities']
                generation = stage['generation_probabilities']
                self.assertEqual(len(raw), 79)
                self.assertAlmostEqual(sum(raw), 1., places=6)
                self.assertAlmostEqual(sum(generation), 1., places=6)
                for token in (0, 1, 3):
                    self.assertGreater(raw[token], 0.)
                    self.assertEqual(generation[token], 0.)
                self.assertGreater(generation[2], 0.)  # EOS 可以正常结束生成。
                target = prefix['expected_next_id']
                self.assertEqual(stage['expected_next_probability'], raw[target])

    def test_custom_run_reads_its_own_checkpoints_and_logs(self):
        # 用临时副本验证路径不会退回硬编码的 first_run；不改原始权重。
        with tempfile.TemporaryDirectory(prefix='训练回放 ') as directory:
            directory = Path(directory)
            for name in ('initial.pt', 'pretrain.pt', 'sft.pt', 'pretrain_log.json',
                         'sft_log.json', 'generation_comparison.json'):
                shutil.copy2(FIRST / name, directory / name)
            shutil.copytree(FIRST / 'data', directory / 'data')
            log_path = directory / 'pretrain_log.json'
            log = json.loads(log_path.read_text(encoding='utf-8'))
            log.update({'seed': 7, 'batch_size': 3, 'learning_rate': .0015})
            log_path.write_text(json.dumps(log), encoding='utf-8')
            # 日志配置被单独修改时应拒绝；否则回放的首批已不是该检查点记录的实验。
            with self.assertRaisesRegex(ValueError, '配置'):
                build_training_replay(directory)
            checkpoint = directory / 'pretrain.pt'
            payload = torch.load(checkpoint, map_location='cpu', weights_only=True)
            # 这是验证配置读取的临时夹具，不把修改元数据称作完成了一次新训练。
            payload['metadata'].update({'seed': 7, 'batch_size': 3, 'learning_rate': .0015})
            torch.save(payload, checkpoint)
            report = build_training_replay(directory)
            self.assertEqual(report['provenance']['run_directory'], str(directory.resolve()))
            self.assertTrue(report['provenance']['original_files_unchanged'])
            self.assertIn(str((directory / 'initial.pt').resolve()),
                          report['provenance']['file_sha256_before'])
            expected = random.Random(7).sample(self.groups['pretrain_train'], 3)
            self.assertEqual(report['first_step']['batch']['record_ids'],
                             [r['record_id'] for r in expected])
            self.assertEqual(report['first_step']['optimizer']['learning_rate'], .0015)

    def test_rejects_mixed_parent_or_history_with_invented_last_step(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            for name in ('initial.pt', 'pretrain.pt', 'sft.pt', 'pretrain_log.json',
                         'sft_log.json', 'generation_comparison.json'):
                shutil.copy2(FIRST / name, directory / name)
            shutil.copytree(FIRST / 'data', directory / 'data')
            path = directory / 'sft_log.json'
            log = json.loads(path.read_text(encoding='utf-8'))
            log['parent_parameter_sha256'] = 'another-pretrain'
            path.write_text(json.dumps(log), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '父参数'):
                build_training_replay(directory)
            shutil.copy2(FIRST / 'sft_log.json', path)
            log = json.loads(path.read_text(encoding='utf-8'))
            log['history'][-1]['step'] = 299
            path.write_text(json.dumps(log), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '步数|采样'):
                build_training_replay(directory)
            shutil.copy2(FIRST / 'sft_log.json', path)
            checkpoint = directory / 'sft.pt'
            payload = torch.load(checkpoint, map_location='cpu', weights_only=True)
            payload['metadata']['parent_parameter_sha256'] = 'another-pretrain'
            torch.save(payload, checkpoint)
            with self.assertRaisesRegex(ValueError, '父参数'):
                build_training_replay(directory)


if __name__ == '__main__':
    unittest.main()

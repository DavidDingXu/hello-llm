"""防止续写保留实验漏算停止符、改变评估分母或破坏成对比较。"""
import hashlib
import random
import tempfile
import unittest
from pathlib import Path

import torch

from lessons import retention_experiment as experiment
from tiny_lm.data import build_records, make_sft_batch
from tiny_lm.tokenizer import CharTokenizer

ROOT = Path(__file__).resolve().parents[1]


class RetentionExperimentTests(unittest.TestCase):
    def test_old_tasks_cover_every_familiar_scene_person_template_and_score_eos(self):
        groups = experiment.build_evaluation_sets()
        old = groups['old_continuation']
        self.assertEqual([len(groups[k]) for k in groups], [24, 8, 256])
        self.assertEqual(len({r['record_id'] for r in old}), 256)
        self.assertEqual(old[0]['prompt'], '早上，小丁喜欢')
        self.assertEqual(old[0]['answer'], '红色的苹果。')
        self.assertEqual(old[-1]['prompt'], '散步时，小何选了')
        self.assertEqual(old[-1]['answer'], '桑葚，它是紫色的。')
        self.assertEqual({r['template_id'] for r in old}, {0, 1, 2, 3})
        tokenizer = CharTokenizer.for_course()
        _, targets = make_sft_batch(old, tokenizer)
        self.assertEqual(int((targets != -100).sum()), 1792)
        self.assertEqual(int((targets == 2).sum()), 256)

    def test_matching_text_without_eos_is_not_a_complete_answer(self):
        records = [{'record_id': 'one', 'prompt': '早上，小丁喜欢', 'answer': '红色的苹果。'},
                   {'record_id': 'two', 'prompt': '晚上，小周拿着', 'answer': '黄色的香蕉。'}]
        outputs = [{'generated_text': '红色的苹果。', 'stop_reason': 'max_new_tokens'},
                   {'generated_text': '黄色的香蕉。', 'stop_reason': 'eos'}]
        result = experiment.score_generations(records, outputs)
        self.assertEqual(result['sample_count'], 2)
        self.assertEqual(result['text_exact_count'], 2)
        self.assertEqual(result['complete_exact_count'], 1)
        self.assertEqual(result['eos_count'], 1)
        self.assertFalse(result['items'][0]['complete_exact'])

    def test_paired_trials_use_same_batches_and_leave_source_checkpoint_unchanged(self):
        checkpoint = ROOT / 'artifacts/first_run/pretrain.pt'
        before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        report = experiment.run_experiment(checkpoint, steps=1, seeds=(42,))
        after = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        original, lower = report['trials'][:2]
        self.assertEqual(original['sampled_batches_sha256'], lower['sampled_batches_sha256'])
        self.assertNotEqual(original['parameter_sha256'], lower['parameter_sha256'])
        self.assertEqual(original['history'][0], lower['history'][0])
        for trial in report['trials']:
            self.assertEqual(trial['evaluation']['old_continuation']['valid_target_count'], 1792)
            self.assertEqual(trial['evaluation']['sft_train']['valid_target_count'], 168)
            self.assertEqual(trial['evaluation']['sft_val']['valid_target_count'], 56)
        self.assertTrue(report['provenance']['checkpoint_unchanged'])

    def test_mixed_batch_supervises_twelve_answers_and_four_full_old_texts(self):
        groups = build_records()
        tokenizer = CharTokenizer.for_course()
        x, y, selection = experiment.sample_training_batch(
            groups['sft_train'], tokenizer, random.Random(42), batch_size=16,
            replay_records=groups['pretrain_train'], replay_sampler=random.Random(42))
        self.assertEqual(tuple(x.shape), (16, 32))
        self.assertEqual(len(selection['sft_record_ids']), 12)
        self.assertEqual(len(selection['pretrain_record_ids']), 4)
        self.assertEqual(selection['sft_valid_targets'], 84)
        self.assertEqual(int((y[:12] != -100).sum()), 84)
        old_by_id = {r['record_id']: r for r in groups['pretrain_train']}
        expected_old_tokens = sum(len(old_by_id[k]['text']) + 1
                                  for k in selection['pretrain_record_ids'])
        self.assertEqual(selection['pretrain_valid_targets'], expected_old_tokens)
        self.assertEqual(int((y[12:] != -100).sum()), expected_old_tokens)
        self.assertTrue(bool((y[:12, 0] == -100).all()))
        self.assertTrue(bool((y[12:, 0] != -100).all()))
        self.assertEqual(int((y == 2).sum()), 16)
        held_out_ids = {r['record_id'] for r in groups['sft_val'] + groups['pretrain_val']}
        self.assertFalse(held_out_ids.intersection(selection['sft_record_ids'] +
                                                  selection['pretrain_record_ids']))

    def test_output_cannot_replace_original_logs_or_data(self):
        with self.assertRaisesRegex(ValueError, '原始|数据'):
            experiment.write_report(ROOT / 'artifacts/first_run/sft_log.json', {})
        with self.assertRaisesRegex(ValueError, '原始|数据'):
            experiment.write_report(ROOT / 'data/manifest.json', {})
        with tempfile.TemporaryDirectory(prefix='保留实验 ') as directory:
            output = Path(directory) / 'result.json'
            experiment.write_report(output, {'completed': True})
            self.assertEqual(output.read_text(encoding='utf-8').strip(), '{\n  "completed": true\n}')


if __name__ == '__main__':
    unittest.main()

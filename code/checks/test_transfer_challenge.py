"""独立任务的验收应能拒绝会运行但错题、未知字被吞和旧词表尺寸等实现。"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from exercises import transfer_solution
from lessons.transfer_challenge import read_data, run, verify_submission
from tiny_lm.data import make_pretrain_batch
from tiny_lm.model import ModelConfig, TinyLM


class TransferChallengeTests(unittest.TestCase):
    def submission(self, **overrides):
        functions = {name: getattr(transfer_solution, name)
                     for name in ('build_tokenizer', 'make_batch', 'build_model')}
        functions.update(overrides)
        return SimpleNamespace(**functions)

    def test_reference_uses_training_vocabulary_and_disjoint_known_character_validation(self):
        data, _ = read_data()
        tokenizer, _, checks = verify_submission(transfer_solution, data)
        self.assertEqual(tokenizer.vocab_size, 67)
        self.assertEqual((len(data['train']), len(data['validation'])), (288, 72))
        self.assertTrue(all(checks.values()))

    def test_wrong_eos_unknown_character_and_fixed_vocab_are_rejected(self):
        data, _ = read_data()
        def omit_eos(records, tokenizer, max_len=32):
            x, y = transfer_solution.make_batch(records, tokenizer, max_len)
            y[y == 2] = -100
            return x, y
        with self.assertRaisesRegex(AssertionError, 'EOS'):
            verify_submission(self.submission(make_batch=omit_eos), data)
        with self.assertRaisesRegex(AssertionError, '未知字'):
            verify_submission(self.submission(make_batch=make_pretrain_batch), data)
        with self.assertRaisesRegex(AssertionError, '旧词表'):
            verify_submission(self.submission(build_model=lambda tokenizer: TinyLM(ModelConfig())), data)

    def test_training_saves_reloadable_own_checkpoint_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(prefix='迁移验收 ') as temporary:
            out = Path(temporary) / '自己的实验'
            report = run(transfer_solution, out=out, steps=1, seed=7, train=True)
            self.assertTrue(report['checkpoint_reloaded'])
            self.assertEqual(report['parameter_count'], 90816)
            self.assertEqual(report['history'][-1]['step'], 1)
            self.assertTrue((out / 'model.pt').is_file())
            self.assertEqual(json.loads((out / 'report.json').read_text(encoding='utf-8')), report)
            old = (out / 'model.pt').read_bytes()
            with self.assertRaisesRegex(ValueError, '已有文件'):
                run(transfer_solution, out=out, steps=1, train=True)
            self.assertEqual((out / 'model.pt').read_bytes(), old)


if __name__ == '__main__':
    unittest.main()

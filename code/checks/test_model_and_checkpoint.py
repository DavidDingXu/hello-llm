import tempfile
import unittest
from pathlib import Path

import torch

from tiny_lm.checkpoint import load_checkpoint, save_checkpoint
from tiny_lm.generate import generate
from tiny_lm.layers import RMSNorm
from tiny_lm.model import ModelConfig, TinyLM
from tiny_lm.tokenizer import CharTokenizer
from tiny_lm.trace import parameter_digest
from tiny_lm.train import compare_stages


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(42)
        torch.set_num_threads(1)
        self.model = TinyLM(ModelConfig())

    def test_future_tokens_do_not_change_earlier_predictions(self):
        original = torch.tensor([[1, 5, 6, 7, 8]])
        changed = torch.tensor([[1, 5, 6, 12, 20]])
        self.model.eval()
        before = self.model(original)
        after = self.model(changed)
        torch.testing.assert_close(before[:, :3], after[:, :3], rtol=1e-5, atol=1e-6)
        self.assertEqual(before.shape, (1, 5, 79))
        self.assertEqual(sum(p.numel() for p in self.model.parameters()), 92352)

    def test_norm_matches_a_small_numeric_example(self):
        out = RMSNorm(2)(torch.tensor([3., 4.]))
        torch.testing.assert_close(out, torch.tensor([.8485278, 1.1313704]))

    def test_checkpoint_preserves_the_same_logits(self):
        tok = CharTokenizer.for_course()
        inputs = torch.tensor([[1, 5, 6]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '中文 checkpoint.pt'
            save_checkpoint(path, self.model, tok, {'stage': 'test'})
            restored, restored_tok, metadata = load_checkpoint(path)
            torch.testing.assert_close(self.model(inputs), restored(inputs))
            self.assertEqual(restored_tok.encode('小丁'), tok.encode('小丁'))
            self.assertEqual(metadata['stage'], 'test')

    def test_generation_stops_on_eos_without_changing_parameters(self):
        for parameter in self.model.parameters():
            parameter.data.zero_()
        tok = CharTokenizer.for_course()
        before = [p.detach().clone() for p in self.model.parameters()]
        result = generate(self.model, tok, '小丁', greedy=True, max_new_tokens=8)
        self.assertEqual(result['stop_reason'], 'eos')
        self.assertEqual(result['generated_text'], '')
        for old, new in zip(before, self.model.parameters()):
            torch.testing.assert_close(old, new)

    def test_stage_comparison_rejects_sft_from_replaced_pretrain_weights(self):
        """复用输出目录重做预训练后，旧SFT不能冒充新权重的下一阶段。"""
        tok = CharTokenizer.for_course()
        old_parent = parameter_digest(self.model)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            save_checkpoint(folder / 'sft.pt', self.model, tok,
                            {'stage': 'sft', 'parent_parameter_sha256': old_parent})
            with torch.no_grad():
                self.model.embedding.weight[0, 0] += 0.25
            save_checkpoint(folder / 'pretrain.pt', self.model, tok, {'stage': 'pretrain'})
            with self.assertRaisesRegex(ValueError, 'sft.pt'):
                compare_stages(folder)
            self.assertFalse((folder / 'generation_comparison.json').exists())

    def test_stage_comparison_accepts_matching_sft_parent(self):
        """父权重一致时，应正常生成两个阶段的结果并保存对照。"""
        tok = CharTokenizer.for_course()
        parent = parameter_digest(self.model)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            save_checkpoint(folder / 'pretrain.pt', self.model, tok, {'stage': 'pretrain'})
            save_checkpoint(folder / 'sft.pt', self.model, tok,
                            {'stage': 'sft', 'parent_parameter_sha256': parent})
            comparison = compare_stages(folder)
            self.assertEqual(set(comparison), {'pretrain', 'sft'})
            self.assertTrue((folder / 'generation_comparison.json').exists())


if __name__ == '__main__':
    unittest.main()

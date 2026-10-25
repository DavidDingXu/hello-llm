import unittest

import torch

from tiny_lm.attention import attention_2d, merge_heads, split_heads
from tiny_lm.rope import apply_rope


class AttentionTests(unittest.TestCase):
    def test_causal_weighted_sum_matches_the_hand_example(self):
        q = torch.tensor([[1., 0.], [0., 1.], [1., 1.]])
        v = torch.tensor([[1., 0.], [0., 2.], [1., 2.]])
        result, trace = attention_2d(q, q, v, causal=True)
        expected = torch.tensor([[1., 0.], [.33023845, 1.33952310],
                                 [.75174492, 1.50348984]])
        torch.testing.assert_close(result, expected, rtol=1e-6, atol=1e-6)
        self.assertEqual(trace['weights'][0, 2].item(), 0.)

    def test_heads_preserve_position_and_feature_coordinates(self):
        x = torch.arange(12).reshape(1, 3, 4)
        heads = split_heads(x, 2)
        expected = torch.tensor([[[[0, 1], [4, 5], [8, 9]],
                                  [[2, 3], [6, 7], [10, 11]]]])
        torch.testing.assert_close(heads, expected)
        torch.testing.assert_close(merge_heads(heads), x)

    def test_rope_keeps_norms_and_relative_position_dot_products(self):
        torch.manual_seed(4)
        q = torch.randn(1, 2, 4, 8)
        k = torch.randn(1, 2, 4, 8)
        q0, k0 = apply_rope(q, k, torch.arange(4))
        q7, k7 = apply_rope(q, k, torch.arange(4) + 7)
        torch.testing.assert_close(q.norm(dim=-1), q0.norm(dim=-1))
        torch.testing.assert_close(q0 @ k0.transpose(-2, -1),
                                   q7 @ k7.transpose(-2, -1), rtol=1e-5, atol=2e-6)


if __name__ == '__main__':
    unittest.main()

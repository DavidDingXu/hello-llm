import math
import unittest

import torch

from tiny_lm.data import build_records, make_pretrain_batch, make_sft_batch
from tiny_lm.losses import token_loss
from tiny_lm.tokenizer import CharTokenizer


class DataAndLossTests(unittest.TestCase):
    def setUp(self):
        self.records = build_records()
        self.tokenizer = CharTokenizer.for_course()

    def test_record_split_keeps_complete_sentences_disjoint(self):
        train = {r['text'] for r in self.records['pretrain_train']}
        val = {r['text'] for r in self.records['pretrain_val']}
        self.assertEqual((len(train), len(val)), (256, 64))
        self.assertFalse(train & val)
        text = '小丁喜欢苹果。\n'
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(text)), text)
        self.assertEqual(self.tokenizer.vocab_size, 79)

    def test_pretrain_labels_predict_the_next_character_and_eos(self):
        x, y = make_pretrain_batch([{'text': '小丁'}], self.tokenizer, max_len=5)
        self.assertEqual(x[0, 0].item(), 1)
        self.assertEqual(self.tokenizer.decode(y[0, :2].tolist()), '小丁')
        self.assertEqual(y[0, 2].item(), 2)
        self.assertEqual(y[0, 3:].tolist(), [-100, -100])
        with self.assertRaises(ValueError):
            make_pretrain_batch([{'text': '小丁'}], self.tokenizer, max_len=2)

    def test_sft_supervises_first_answer_character_and_eos(self):
        sample = {'prompt': '问：小丁喜欢什么水果？\n答：', 'answer': '红色的苹果。'}
        x, y = make_sft_batch([sample], self.tokenizer, max_len=32)
        self.assertTrue(torch.all(y[0, :14] == -100))
        self.assertEqual(self.tokenizer.decode([y[0, 14].item()]), '红')
        self.assertEqual(y[0, 20].item(), 2)
        self.assertTrue(torch.all(y[0, 21:] == -100))
        self.assertEqual(x.shape, (1, 32))

    def test_loss_uses_logits_and_ignores_padding(self):
        logits = torch.tensor([[[0., math.log(2), math.log(3)], [8., 1., -3.]]],
                              requires_grad=True)
        loss = token_loss(logits, torch.tensor([[2, -100]]))
        self.assertAlmostEqual(loss.item(), math.log(2), places=6)
        loss.backward()
        self.assertTrue(torch.equal(logits.grad[0, 1], torch.zeros(3)))
        with self.assertRaises(ValueError):
            token_loss(logits.detach(), torch.tensor([[-100, -100]]))


if __name__ == '__main__':
    unittest.main()

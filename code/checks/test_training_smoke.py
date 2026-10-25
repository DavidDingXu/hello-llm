import unittest

import torch

from tiny_lm.data import build_records, make_pretrain_batch
from tiny_lm.model import ModelConfig, TinyLM
from tiny_lm.tensor_mlp import train_xor
from tiny_lm.tokenizer import CharTokenizer
from tiny_lm.train import evaluate, train_step


class TrainingTests(unittest.TestCase):
    def test_xor_learns_from_the_specified_initial_parameters(self):
        result = train_xor(steps=500)
        self.assertLess(result['final_loss'], .02)
        self.assertEqual([round(x) for x in result['predictions']], [0, 1, 1, 0])

    def test_real_model_can_fit_a_small_batch_and_evaluation_does_not_update_it(self):
        torch.set_num_threads(1)
        torch.manual_seed(42)
        model = TinyLM(ModelConfig())
        tok = CharTokenizer.for_course()
        records = [r for r in build_records()['pretrain_train'] if r['template_id'] == 3][:4]
        x, y = make_pretrain_batch(records, tok)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.003, weight_decay=.01)
        initial = evaluate(model, [(x, y)])
        for _ in range(240):
            train_step(model, x, y, optimizer)
        before = [p.detach().clone() for p in model.parameters()]
        final = evaluate(model, [(x, y)])
        self.assertLess(final, .1)
        self.assertLess(final, initial / 10)
        for old, new in zip(before, model.parameters()):
            torch.testing.assert_close(old, new)


if __name__ == '__main__':
    unittest.main()

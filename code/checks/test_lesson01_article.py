"""正文是读者的可执行来源：用工程实现核对其中的函数与串联示例。"""
import contextlib
import io
from pathlib import Path
import re
import unittest

from tiny_lm.scalar import neuron as reference_neuron


class Lesson01ArticleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        article = Path(__file__).resolve().parents[2] / 'chapters/01-neuron/README.md'
        cls.namespace = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for block in re.findall(r'```python\n(.*?)```', article.read_text(encoding='utf-8'), re.S):
                exec(compile(block, str(article), 'exec'), cls.namespace)

    def test_one_two_and_three_inputs_match_companion_code(self):
        cases = [([4], [.5], 1), ([2, 1], [1, 3], -1),
                 ([1, 2, 3], [.5, -1, 2], -1), ([2, 1], [1, 3], -6)]
        for inputs, weights, bias in cases:
            with self.subTest(inputs=inputs):
                self.assertEqual(self.namespace['neuron'](inputs, weights, bias),
                                 reference_neuron(inputs, weights, bias))

    def test_article_chain_reuses_the_same_function(self):
        self.assertEqual(self.namespace['first'], 4)
        self.assertEqual(self.namespace['second'], 3)

    def test_invalid_input_contract_matches_companion_code(self):
        for inputs, weights in [([], []), ([1, 2], [3])]:
            with self.subTest(inputs=inputs):
                with self.assertRaises(ValueError):
                    self.namespace['neuron'](inputs, weights)


if __name__ == '__main__':
    unittest.main()

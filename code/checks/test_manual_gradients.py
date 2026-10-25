import copy
import unittest

from tiny_lm.manual_mlp import backward, forward, step
from tiny_lm.scalar import linear, neuron


class ManualNetworkTests(unittest.TestCase):
    def test_neuron_distinguishes_input_weight_and_bias(self):
        self.assertEqual(neuron([2, 1], [1, 3], -1), 4)
        self.assertEqual(neuron([2, 2], [1, 3], -1), 7)
        self.assertEqual(neuron([2, 1], [1, 3], 0), 5)

    def test_linear_rows_produce_separate_outputs(self):
        self.assertEqual(linear([2, 1], [[1, 2], [3, 4]], [1, -1]), [5, 9])
        with self.assertRaises(ValueError):
            linear([2, 1], [[1, 2, 3]], [0])

    def test_manual_gradients_match_independent_parameter_perturbations(self):
        params = {'W1': [[1., 0.], [0., 1.]], 'b1': [0., 0.],
                  'W2': [[1., -1.]], 'b2': [0.]}
        prediction, cache = forward([1., 2.], params)
        self.assertEqual(prediction, -1.)
        original = copy.deepcopy(params)
        gradients = backward(cache, 1., params)
        self.assertEqual(params, original, 'backward must not update parameters')
        self.assertEqual(gradients['W1'], [[-4., -8.], [4., 8.]])
        self.assertEqual(gradients['W2'], [[-4., -8.]])
        for name in params:
            positions = ([(i, j) for i, row in enumerate(params[name]) for j in range(len(row))]
                         if name.startswith('W') else [(i,) for i in range(len(params[name]))])
            for position in positions:
                variants = []
                for sign in (1, -1):
                    changed = copy.deepcopy(params)
                    if len(position) == 2:
                        i, j = position
                        changed[name][i][j] += sign * 1e-6
                    else:
                        changed[name][position[0]] += sign * 1e-6
                    value, _ = forward([1., 2.], changed)
                    variants.append((value - 1.) ** 2)
                numerical = (variants[0] - variants[1]) / 2e-6
                expected = (gradients[name][position[0]][position[1]]
                            if len(position) == 2 else gradients[name][position[0]])
                self.assertAlmostEqual(numerical, expected, places=6)
        step(params, gradients, .01)
        updated, _ = forward([1., 2.], params)
        self.assertAlmostEqual(updated, -.2896, places=7)
        self.assertAlmostEqual((updated - 1.) ** 2, 1.66306816, places=7)


if __name__ == '__main__':
    unittest.main()

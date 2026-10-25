"""第01讲：一个神经元的手算、改数和连接预览。

核心乘加与ReLU在 tiny_lm/scalar.py。这里准备例子、打印各阶段结果，
再导出同一份数值记录；不会训练参数。项目根目录运行 python -m lessons.l01，
只需要Python标准库。
"""
import argparse
from pathlib import Path

from tiny_lm.scalar import forward, neuron
from tiny_lm.trace import export_trace
from tiny_lm.teaching import add_observation_arguments, observe_lesson


def build_example():
    """返回输入、参数、乘积与输出；三个变体每次只改一处，便于核对影响。"""
    inputs, weights, bias = [2, 1], [1, 3], -1
    return {'kind': 'hand_calc', 'lesson': 1, 'inputs': inputs, 'weights': weights, 'bias': bias,
            'products': [x * w for x, w in zip(inputs, weights)],
            'sum': sum(x * w for x, w in zip(inputs, weights)),
            'weighted_sum': forward(inputs, weights, bias),
            'activation': 'ReLU', 'output': neuron(inputs, weights, bias),
            'variants': [
                {'name': '只改输入', 'inputs': [2, 2], 'weights': weights, 'bias': bias,
                 'output': neuron([2, 2], weights, bias)},
                {'name': '只改偏置', 'inputs': inputs, 'weights': weights, 'bias': 0,
                 'output': neuron(inputs, weights, 0)},
                {'name': '负数输入', 'inputs': [-2, 0], 'weights': weights, 'bias': bias,
                 'before_relu': forward([-2, 0], weights, bias),
                 'output': neuron([-2, 0], weights, bias)}]}


def build_activation_example():
    """固定三个目标，比较纯乘加与ReLU(x−1)能否同时满足，不含参数搜索。"""
    inputs = [0, 1, 2]
    return {'kind': 'hand_calc', 'inputs': inputs, 'targets': [0, 0, 1],
            'affine': {'weight': 0, 'bias': 0,
                       'outputs': [forward([x], [0], 0) for x in inputs]},
            'relu': {'weight': 1, 'bias': -1,
                     'before_relu': [forward([x], [1], -1) for x in inputs],
                     'outputs': [neuron([x], [1], -1) for x in inputs]}}


def build_network_example():
    """只数2→2→1结构里的参数：每条连线一个权重，每个计算单元一个偏置。"""
    widths = [2, 2, 1]
    weights = sum(a * b for a, b in zip(widths[:-1], widths[1:]))  # 相邻两层全连接的连线数。
    biases = sum(widths[1:])  # 输入点只是数据，不配偏置。
    return {'kind': 'structure_example', 'widths': widths,
            'weight_count': weights, 'bias_count': biases,
            'parameter_count': weights + biases}


def main():
    """按讲解顺序打印算例，并保存供图解核对的JSON。"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('artifacts/lesson01.json'))
    add_observation_arguments(parser)
    args = parser.parse_args()
    with observe_lesson(1, verbose=args.verbose, step=args.step):
        result = build_example()
    print('输入：[2, 1]；权重：[1, 3]；偏置：-1')
    print('第一条：2 × 1 = 2')
    print('第二条：1 × 3 = 3')
    print('汇总：2 + 3 = 5')
    print('加偏置：5 - 1 = 4')
    print(f"经过 ReLU：max(0, 4) = {result['output']:g}")
    for variant in result['variants']:
        print(f"{variant['name']} → {variant['output']:g}")
    # 与主算例分开：这个反例解释为什么还需要非线性。
    activation = build_activation_example()
    result['activation_example'] = activation
    print('为什么需要非线性：输入 [0, 1, 2]，目标 [0, 0, 1]')
    print(f"只乘加，满足前两项后：{activation['affine']['outputs']}")
    print(f"先减 1，再经过 ReLU：{activation['relu']['outputs']}")
    print(f"主算例输出作为下一项输入：{neuron([result['output']], [0.5], 1):g}")
    network = build_network_example()
    result['network_example'] = network
    print(f"结构预览 [2, 2, 1]：{network['weight_count']} 个权重 + {network['bias_count']} 个偏置 = {network['parameter_count']} 个参数")
    export_trace(args.out, result)  # 保存的是本次计算结果；这一步不修改任何参数。
    print(f'数值记录：{args.out}')


if __name__ == '__main__':
    main()

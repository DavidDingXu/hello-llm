"""用普通 Python 实现单个神经元和一层乘加，不自动求梯度或更新参数。"""


def forward(inputs, weights, bias=0.0):
    """输入和权重为等长的一维序列，返回加权和加偏置这个标量。

    inputs 是当前样本；weights 和 bias 是可调参数，本函数只读取它们。
    """
    if len(inputs) != len(weights) or not inputs:
        raise ValueError('输入与权重必须非空且等长')
    total = 0.0
    for value, weight in zip(inputs, weights):
        total += value * weight
    return total + bias


def relu(value):
    """ReLU 激活：正数原样通过，负数与零返回零；输入输出都是标量。"""
    return max(0.0, value)


def neuron(inputs, weights, bias=0.0):
    """先乘加再做 ReLU，返回单个神经元的输出。"""
    return relu(forward(inputs, weights, bias))


def linear(inputs, weights, biases):
    """一维输入经多个乘加单元，返回一维输出列表。

    若输入有 n 个数、输出有 m 个数，weights 的形状为 [m,n]，
    每行负责一个输出；biases 的长度为 m。这里不加激活函数。
    """
    if not weights or len(weights) != len(biases):
        raise ValueError('每个输出都需要一行权重和一个偏置')
    return [forward(inputs, row, bias) for row, bias in zip(weights, biases)]

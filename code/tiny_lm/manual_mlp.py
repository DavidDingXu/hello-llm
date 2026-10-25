"""单样本、单输出的两层网络：手写前向、平方误差的反向传播与参数更新。

params 存权重和偏置，cache 存一次前向的中间结果，target 是期望输出。
forward 算数值，backward 算梯度，step 才修改参数。
"""

from .scalar import linear, relu


def forward(inputs, params):
    """返回标量预测和反向传播所需的 cache，不修改 params。

    输入长度为 n，隐藏层宽度为 m；W1 为 [m,n]、b1 为 [m]，
    W2 为 [1,m]、b2 为 [1]。z 是激活前的数，h 是 ReLU 后的数。
    """
    z = linear(inputs, params['W1'], params['b1'])
    hidden = [relu(value) for value in z]
    prediction = linear(hidden, params['W2'], params['b2'])[0]
    return prediction, {'x': list(inputs), 'z': z, 'h': hidden, 'prediction': prediction}


def backward(cache, target, params):
    """根据同一次前向的 cache 和参数，返回各参数对平方误差的梯度。

    target 是标量标签；返回字典与 params 的键和形状相同。
    梯度描述参数微小变化对误差的影响，这一步不修改参数。
    """
    # d_output 表示 dL/dprediction；损失 L = (prediction - target) ** 2。
    d_output = 2 * (cache['prediction'] - target)
    d_hidden = [d_output * weight for weight in params['W2'][0]]
    # 穿过 ReLU 时，正区间导数为 1，负区间为 0；零点在这里也取 0。
    d_z = [gradient if z > 0 else 0.0 for gradient, z in zip(d_hidden, cache['z'])]
    # 一条乘加边的权重梯度 = 该输出的梯度 × 这条边的输入。
    return {
        'W2': [[d_output * value for value in cache['h']]],
        'b2': [d_output],
        'W1': [[gradient * value for value in cache['x']] for gradient in d_z],
        'b1': d_z,
    }


def step(params, gradients, learning_rate):
    """原地执行参数 -= 学习率 × 梯度，无返回值。

    gradients 应先按更新前的整套参数算好；循环虽然逐项赋值，
    每项使用的仍是同一次前向得到的梯度，不在更新途中重算梯度。
    """
    if learning_rate <= 0:
        raise ValueError('学习率应为正数')
    for name, values in params.items():
        if name.startswith('W'):
            for i, row in enumerate(values):
                for j in range(len(row)):
                    row[j] -= learning_rate * gradients[name][i][j]
        else:
            for i in range(len(values)):
                values[i] -= learning_rate * gradients[name][i]


def hand_example():
    """返回一份新的 2→2→1 参数字典，用于可手算的前向和反向例子。"""
    return {'W1': [[1., 0.], [0., 1.]], 'b1': [0., 0.],
            'W2': [[1., -1.]], 'b2': [0.]}

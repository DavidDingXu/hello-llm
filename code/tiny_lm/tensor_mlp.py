"""用 PyTorch 张量重现两层网络，并记录固定初值的 XOR 训练过程。

张量是可带多个轴的数表。这里 B 表示一批样本数，n 为输入宽度，m 为隐藏宽度。
"""
import torch
from torch import nn


class TensorMLP(nn.Module):
    """参数布局与手写网络相同：W1[m,n]、b1[m]、W2[1,m]、b2[1]。"""

    def __init__(self, params):
        """把普通列表转成可求梯度的参数，交给 nn.Module 统一登记。"""
        super().__init__()
        for name, values in params.items():
            setattr(self, name, nn.Parameter(torch.tensor(values, dtype=torch.float32)))

    def forward(self, x):
        """输入 x 为 [B,n]，返回 [B,1] 预测；不在此计算损失或更新参数。"""
        # 样本放在行上，而权重的行对应输出，所以矩阵乘法使用 W1.T。
        # b1[m] 会广播到每个样本行；广播不代表每行各有一份可调偏置。
        hidden = torch.relu(x @ self.W1.T + self.b1)
        return hidden @ self.W2.T + self.b2


def train_xor(steps=500):
    """以四条 XOR 样本训练 2→4→1 网络，返回预测、损失和训练记录。

    x 为 [4,2] 输入，target 为 [4,1] 标签。固定参数初值和学习率，
    steps 表示实际更新次数；step=0 的记录发生在任何更新之前。
    """
    torch.set_num_threads(1)
    params = {'W1': [[.4, -.2], [-.3, .5], [.2, .3], [-.4, -.1]],
              'b1': [.1, .1, -.1, .2], 'W2': [[.5, -.4, .3, .2]], 'b2': [0.]}
    model = TensorMLP(params)
    x = torch.tensor([[0., 0.], [0., 1.], [1., 0.], [1., 1.]])
    target = torch.tensor([[0.], [1.], [1.], [0.]])
    optimizer = torch.optim.SGD(model.parameters(), lr=.1)
    rows = []
    for step in range(steps + 1):
        prediction = model(x)
        loss = (prediction - target).square().mean()
        if step % 10 == 0 or step == steps:
            rows.append({'step': step, 'loss': loss.item(),
                         'predictions': prediction.detach().flatten().tolist()})
        if step == steps:
            break
        # PyTorch 默认累加梯度：先清空旧值，再反向求梯度，最后执行更新。
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return {'final_loss': loss.item(), 'predictions': prediction.detach().flatten().tolist(),
            'history': rows, 'initial_params': params, 'steps': steps, 'learning_rate': .1}

"""把下一字符的原始分数和正确编号转成一个可反向传播的损失标量。

B 为一批样本数，T 为位置数，V 为词表大小；标签 -100 表示该位置不计损失。
"""

import torch.nn.functional as F


def token_loss(logits, targets):
    """logits 为 [B,T,V] 分数，targets 为 [B,T] 整数标签，返回有效位置的平均损失。

    标签应已与输入错开一位：当前位置的分数用来预测下一个字符。
    本函数构造损失；调用 loss.backward() 才会沿计算图求参数梯度。
    """
    if logits.ndim != 3 or targets.shape != logits.shape[:2]:
        raise ValueError('需要 [B,T,V] 分数与 [B,T] 标签')
    if not (targets != -100).any():
        raise ValueError('批次没有需要预测的有效标签')
    # 把 B、T 合成位置轴，V 保留为候选字符轴；这不会混合不同位置的分数。
    # cross_entropy 内部处理 log-softmax，不能先把 logits 转成概率再传入。
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1),
                           ignore_index=-100)

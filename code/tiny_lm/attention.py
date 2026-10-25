"""多头因果自注意力：投影、拆头、加入位置、按权重汇总内容，再合头。

B 为样本数，T 为位置数，D 为总向量宽度，H 为头数，d=D/H 为每头宽度。
q 是发起匹配的查询，k 是被匹配的键，v 是按匹配结果汇总的内容向量。
"""

import math

import torch
from torch import nn

from .rope import apply_rope


def split_heads(x, heads):
    """将 [B,T,D] 改排为 [B,H,T,d]；只改变轴的组织，不新增可调参数。"""
    batch, positions, width = x.shape
    if heads <= 0 or width % heads:
        raise ValueError('特征维度应能被注意力头数整除')
    return x.reshape(batch, positions, heads, width // heads).transpose(1, 2)


def merge_heads(x):
    """把 [B,H,T,d] 合回 [B,T,D]，是 split_heads 的逆向排列。"""
    batch, heads, positions, width = x.shape
    # transpose 后元素在内存中通常不连续；先排成连续存储，再合并头与特征轴。
    return x.transpose(1, 2).contiguous().reshape(batch, positions, heads * width)


def attention_2d(q, k, v, causal=False):
    """对 [T,d] 或带 [B,H] 前置轴的 q/k/v 计算注意力。

    返回与 v 同形的汇总结果，以及分数、可见性 mask、归一化权重。
    scores/weights 最后两轴都是 [T,T]：行是查询位置，列是被读取的位置。
    """
    scores = q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])
    mask = torch.ones(scores.shape[-2:], dtype=torch.bool, device=q.device)
    if causal:
        # 行 t 只允许看列 0..t；下三角含对角线，当前位置可以读取自己。
        mask = mask.tril()
        scores = scores.masked_fill(~mask, float('-inf'))
    # 最后一轴是键的位置：每个查询行独立分配总和为 1 的权重。
    # 被填为 -inf 的分数经 softmax 后权重为 0，不参与随后对 v 的汇总。
    weights = torch.softmax(scores, dim=-1)
    output = weights @ v
    return output, {'scores': scores, 'mask': mask, 'weights': weights}


class CausalSelfAttention(nn.Module):
    """输入输出均为 [B,T,D]；四个线性投影的权重 [D,D] 是可训练参数。

    q、k、v 来自同一输入的不同投影，因而叫自注意力；它们是中间结果，
    不是另外存储的模型参数。这里不缓存历史 K/v，每次都计算完整输入序列。
    """

    def __init__(self, width, heads, theta=10000.):
        """width 指 D，heads 指 H，theta 控制 RoPE 各维度对的旋转频率。"""
        super().__init__()
        self.heads = heads
        self.theta = theta
        self.q_proj = nn.Linear(width, width, bias=False)
        self.k_proj = nn.Linear(width, width, bias=False)
        self.v_proj = nn.Linear(width, width, bias=False)
        self.out_proj = nn.Linear(width, width, bias=False)

    def forward(self, x, return_trace=False):
        """前向计算上下文表示；可选返回未经 detach 的中间张量，供检查。"""
        q = split_heads(self.q_proj(x), self.heads)
        k = split_heads(self.k_proj(x), self.heads)
        v = split_heads(self.v_proj(x), self.heads)
        # 每个位置只旋转 q/k 的特征对；v 保持原投影值，作为被汇总的内容。
        q, k = apply_rope(q, k, torch.arange(x.shape[1], device=x.device), self.theta)
        context, details = attention_2d(q, k, v, causal=True)
        # 合头只是拼接；out_proj 才用可训练权重混合不同头的结果。
        output = self.out_proj(merge_heads(context))
        if return_trace:
            details.update({'q': q, 'k': k, 'v': v, 'output': output})
            return output, details
        return output

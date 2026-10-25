"""构成 Transformer 块的归一化、逐位置前馈网络和残差连接。

B 为样本数，T 为位置数，D 为向量宽度，F 为前馈网络的扩展宽度。
这些层都保留 [B,T,D] 的外部形状；注意力交换位置信息，前馈网络处理各位置的特征。
"""

import torch
from torch import nn
import torch.nn.functional as F

from .attention import CausalSelfAttention


class RMSNorm(nn.Module):
    """按每个位置的均方根缩放向量；scale[D] 可训练，eps 是固定小常数。

    与减均值的归一化不同，这里只控制大小，不减去特征均值。
    """

    def __init__(self, width, eps=1e-5):
        """width 指最后一轴的宽度 D，eps 避免均方为零时除以零。"""
        super().__init__()
        self.scale = nn.Parameter(torch.ones(width))
        self.eps = eps

    def forward(self, x):
        """输入 [...,D]，返回同形张量；只在最后一轴求均方，不混合样本或位置。"""
        # keepdim 保留长度为 1 的特征轴，缩放因子才可广播到原向量的 D 个数。
        # rsqrt 是平方根的倒数；scale[D] 在所有样本、位置之间共享。
        return x * torch.rsqrt(x.square().mean(dim=-1, keepdim=True) + self.eps) * self.scale


class SwiGLU(nn.Module):
    """逐位置的门控前馈网络：两路 D→F 投影逐元素相乘，再投影回 D。

    up、gate、down 的权重可训练；gate 经 SiLU 后不是概率，也不限制在 0..1。
    """

    def __init__(self, width, expanded):
        """width 指 D，expanded 指 F；三次投影都不使用偏置。"""
        super().__init__()
        self.up = nn.Linear(width, expanded, bias=False)
        self.gate = nn.Linear(width, expanded, bias=False)
        self.down = nn.Linear(expanded, width, bias=False)

    def forward(self, x):
        """输入输出均为 [...,D]，乘法发生在相同位置的 F 维中间特征之间。"""
        return self.down(F.silu(self.gate(x)) * self.up(x))


class TransformerBlock(nn.Module):
    """先归一化再进入子层的 Transformer 块，子层结果通过残差相加。

    每次相加的两项都是 [B,T,D]，因此既保留原表示，也容纳新算出的变化。
    """

    def __init__(self, config):
        """从配置建立两套 RMSNorm、一层因果注意力和一层 SwiGLU。"""
        super().__init__()
        self.norm1 = RMSNorm(config.d_model, config.norm_eps)
        self.attention = CausalSelfAttention(config.d_model, config.n_heads, config.rope_theta)
        self.norm2 = RMSNorm(config.d_model, config.norm_eps)
        self.ffn = SwiGLU(config.d_model, config.d_ff)

    def forward(self, x, return_trace=False):
        """返回 [B,T,D] 表示；trace 分支额外返回中间张量，计算规则相同。"""
        if return_trace:
            attention_out, trace = self.attention(self.norm1(x), return_trace=True)
            after_attention = x + attention_out
            output = after_attention + self.ffn(self.norm2(after_attention))
            trace.update({'input': x, 'after_attention': after_attention, 'block_output': output})
            return output, trace
        # 两处都先归一化送入子层，但残差支路相加的是归一化前的表示。
        x = x + self.attention(self.norm1(x))
        return x + self.ffn(self.norm2(x))

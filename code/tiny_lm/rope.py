"""用旋转位置编码（RoPE）改变查询 q 与键 k，使匹配分数能区分相对位置。

B 为样本数，H 为注意力头数，T 为位置数，d 为每头宽度；本模块没有可训练参数。
"""

import torch


def apply_rope(q, k, positions, theta=10000.):
    """q/k 为同形 [...,T,d] 张量，positions[T] 为位置编号，返回旋转后的 q/k。

    d 必须是偶数，相邻的两维组成一个平面；不同平面按不同频率旋转。
    theta 是固定频率基数，frequency/cosine/sine 是本次前向计算的中间量。
    """
    width = q.shape[-1]
    if width % 2 or q.shape != k.shape or positions.ndim != 1 or len(positions) != q.shape[-2]:
        raise ValueError('Q/K 应同形、头维度为偶数，位置数与序列长度相等')
    # 0,2,... 标记每一对的起始维度；频率数为 d/2，不是给每维独立旋转。
    frequency = theta ** (-torch.arange(0, width, 2, device=q.device, dtype=q.dtype) / width)
    # [T,1] × [1,d/2] 得到每个位置、每一对的角度；随后广播到 B、H 两轴。
    angles = positions.to(device=q.device, dtype=q.dtype)[:, None] * frequency[None, :]
    cosine, sine = angles.cos(), angles.sin()

    def rotate(x):
        """将 (第 0、1 维)、(第 2、3 维) 等相邻坐标分别做二维旋转。"""
        even, odd = x[..., 0::2], x[..., 1::2]
        # stack 先恢复每对内部的偶/奇顺序，flatten 再按原顺序合回 d 维。
        return torch.stack((even * cosine - odd * sine,
                            even * sine + odd * cosine), dim=-1).flatten(-2)

    return rotate(q), rotate(k)

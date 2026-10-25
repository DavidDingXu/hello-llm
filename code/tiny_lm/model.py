"""将字符向量表、Transformer 块和输出投影连接为下一字符预测模型。

B 为样本数，T 为输入位置数，D 为表示宽度，H 为头数，d=D/H 为每头宽度，
V 为词表大小。前向从编号 [B,T] 得到分数 [B,T,V]，不在模型内计算标签或更新参数。
"""

from dataclasses import dataclass

from torch import nn

from .layers import RMSNorm, TransformerBlock


@dataclass
class ModelConfig:
    """模型结构与固定数值设置；配置本身不参与梯度更新。

    vocab_size=V，d_model=D，n_heads=H，d_ff 为前馈扩展宽度；
    n_layers 为块数，max_seq_len 限制 T，rope_theta/norm_eps 是位置旋转与归一化常数。
    """
    vocab_size: int = 79
    d_model: int = 64
    n_layers: int = 2
    n_heads: int = 2
    d_ff: int = 128
    max_seq_len: int = 32
    rope_theta: float = 10000.
    norm_eps: float = 1e-5

    def __post_init__(self):
        """在建模前检查拆头与 RoPE 配对所需的尺寸条件。"""
        if min(self.vocab_size, self.d_model, self.n_layers, self.n_heads, self.d_ff,
               self.max_seq_len) <= 0 or self.d_model % self.n_heads:
            raise ValueError('模型尺寸必须为正，且宽度应能被头数整除')
        if (self.d_model // self.n_heads) % 2:
            raise ValueError('RoPE 要求每个头的特征维度为偶数')


class TinyLM(nn.Module):
    """只有因果自注意力的语言模型；每个位置的分数用于预测它之后的字符。

    词向量表 [V,D] 与输出权重 [V,D] 是两套独立参数，不共享权重。
    各块的投影权重和归一化缩放也可训练；本模型不使用偏置或 Dropout。
    """

    def __init__(self, config):
        """按 ModelConfig 建立并初始化参数，不加载训练权重。"""
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.blocks = nn.ModuleList([TransformerBlock(config) for _ in range(config.n_layers)])
        self.final_norm = RMSNorm(config.d_model, config.norm_eps)
        self.output = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.apply(self._initialize)

    @staticmethod
    def _initialize(module):
        """初始化线性层和词向量表的权重；RMSNorm 的缩放保留其全 1 初值。"""
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0., std=.02)

    def forward(self, ids, return_trace=False):
        """输入整数编号 [B,T]，返回原始分数 logits[B,T,V]。

        return_trace=True 时另返回各层中间张量，不主动用 detach 切断梯度路径。
        logits 尚未归一化为概率，也不是生成出的字符编号。
        """
        if ids.ndim != 2 or not 0 < ids.shape[1] <= self.config.max_seq_len:
            raise ValueError('输入应为 [B,T]，且 1 <= T <= 最大序列长度')
        x = self.embedding(ids)
        trace = {'ids': ids, 'embedding': x, 'blocks': []}
        for block in self.blocks:
            if return_trace:
                x, detail = block(x, return_trace=True)
                trace['blocks'].append(detail)
            else:
                x = block(x)
        normalized = self.final_norm(x)
        logits = self.output(normalized)
        if return_trace:
            trace.update({'normalized': normalized, 'logits': logits})
            return logits, trace
        return logits

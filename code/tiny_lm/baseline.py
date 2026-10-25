"""只看当前位置字符编号的基线，作为没有上下文混合时的对照。

B 为样本数，T 为位置数，D 为向量宽度，V 为词表大小。
"""
from torch import nn


class CharBaseline(nn.Module):
    """可训练参数只有词向量表 [V,D] 和输出权重 [V,D]。

    不同位置不交换信息；同一编号无论前文是什么，都会产生相同的输出分数。
    """

    def __init__(self, vocab_size, width=16):
        """vocab_size 指 V，width 指 D；不使用输出偏置。"""
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, width)
        self.output = nn.Linear(width, vocab_size, bias=False)

    def forward(self, ids):
        """输入整数编号 [B,T]，查出向量 [B,T,D]，返回原始分数 [B,T,V]。"""
        return self.output(self.embedding(ids))

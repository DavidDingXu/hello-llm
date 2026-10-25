"""在字符与整数编号之间转换，并保存词表顺序。

编号只是查表索引，不表示字符的数值大小或语义；可训练的向量在模型的 Embedding 中。
固定特殊编号为 PAD=0（补齐）、BOS=1（开头）、EOS=2（结束）、UNK=3（未知字符）。
"""


class CharTokenizer:
    """按单个字符编码的分词器；itos 用编号查符号，stoi 用符号查编号。"""

    def __init__(self, tokens):
        """tokens 是按编号排列的完整词表，前四项必须是固定特殊符号。"""
        if tokens[:4] != ['<pad>', '<bos>', '<eos>', '<unk>'] or len(tokens) != len(set(tokens)):
            raise ValueError('词表必须包含固定特殊项，且不能重复')
        self.itos = list(tokens)
        self.stoi = {token: i for i, token in enumerate(tokens)}

    @property
    def vocab_size(self):
        """词表大小 V，包含四个特殊符号，也等于模型输出分数的个数。"""
        return len(self.itos)

    @classmethod
    def for_course(cls):
        """按固定水果语法建立词表，排序使字符编号可重复生成。"""
        from .data import build_records
        # 这里事先定义全部合法字符，包含留出模板所用字符；不统计留出集频率，
        # 也不在此训练向量。训练/验证记录的划分仍由 data 模块决定。
        characters = set()
        for records in build_records().values():
            for record in records:
                characters.update(record.get('text', record.get('prompt', '') + record.get('answer', '')))
        return cls(['<pad>', '<bos>', '<eos>', '<unk>'] + sorted(characters))

    def encode(self, text, add_bos=False, add_eos=False):
        """把字符串转成整数列表；未见字符记为 UNK，可选地添加开头和结束符。"""
        return ([1] if add_bos else []) + [self.stoi.get(char, 3) for char in text] + ([2] if add_eos else [])

    def decode(self, ids, skip_special_tokens=True):
        """按整数列表还原字符串；默认略去编号 0—3 的特殊符号。"""
        return ''.join(self.itos[index] for index in ids if not skip_special_tokens or index >= 4)

    def to_dict(self):
        """返回可写入 JSON 的词表信息；编号依赖列表顺序，不能另行重排。"""
        return {'tokens': self.itos, 'kind': 'character', 'version': 1}

    @classmethod
    def from_dict(cls, data):
        """从保存的词表恢复相同的字符编号。"""
        return cls(data['tokens'])

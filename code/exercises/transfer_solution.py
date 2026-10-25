"""第20讲参考实现；完成自己的预测与提交后再对照。"""
from tiny_lm.data import make_pretrain_batch
from tiny_lm.model import ModelConfig, TinyLM
from tiny_lm.tokenizer import CharTokenizer


def build_tokenizer(train_records):
    """从训练文本取得字符集合；不读取留出文本，不继承原来79项词表。"""
    characters = sorted({char for row in train_records for char in row['text']})
    return CharTokenizer(['<pad>', '<bos>', '<eos>', '<unk>'] + characters)


def make_batch(records, tokenizer, max_len=32):
    """复用第09讲的错位与填充；新数据先检查词表覆盖，避免悄悄训练UNK。"""
    for row in records:
        unknown = sorted(set(row['text']) - tokenizer.stoi.keys())
        if unknown:
            raise ValueError('词表未覆盖字符：' + ''.join(unknown))
    # 旧组件会保留EOS标签；样本过长时报错，不通过截断删除训练答案。
    return make_pretrain_batch(records, tokenizer, max_len=max_len)


def build_model(tokenizer):
    """结构保持两层、64维；只把数据决定的词表大小接入输入表与输出头。"""
    return TinyLM(ModelConfig(vocab_size=tokenizer.vocab_size))

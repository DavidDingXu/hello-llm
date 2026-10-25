"""第20讲独立任务：先写三个函数，再执行 lessons.transfer_challenge 检查。

数据从 exercises/transfer_data.json 读取，不修改原课程 FACTS。
不要在这里读取 validation、参考实现或作者训练后的权重。
"""


def build_tokenizer(train_records):
    """训练字符去重并排序后接在四个特殊项后；返回 CharTokenizer，特殊编号保持0—3。"""
    raise NotImplementedError("先完成 build_tokenizer：从训练文字收集字符")


def make_batch(records, tokenizer, max_len=32):
    """返回 [B,max_len] 的整数输入/标签；错位、EOS、右填充，拒绝未知字和过长样本。"""
    raise NotImplementedError("完成 make_batch：核对每个输入对应的下一项目标")


def build_model(tokenizer):
    """返回随机初始化的 TinyLM；词表尺寸必须来自传入的 tokenizer。"""
    raise NotImplementedError("完成 build_model：将新词表尺寸接到配置")

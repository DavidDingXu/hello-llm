"""生成固定水果文本，按模板留出验证集，再编码成下一字符预测题。

这里只准备输入和标签，不计算梯度。B 表示样本数，T 表示补齐后的输入位置数。
输入中的 PAD=0 用于补齐；标签中的 -100 用于排除无需预测的位置。
"""

import hashlib
import json
from pathlib import Path

# 人物与水果事实在训练集和验证集间共用；留出的是整种句式，不是新事实。
FACTS = [('小丁', '红色', '苹果'), ('小周', '黄色', '香蕉'),
         ('小陈', '紫色', '葡萄'), ('小李', '绿色', '梨子'),
         ('小王', '红色', '草莓'), ('小赵', '黄色', '柠檬'),
         ('小吴', '绿色', '西瓜'), ('小何', '紫色', '桑葚')]
SCENES = ['早上', '中午', '下午', '晚上', '周末', '放学后', '午饭后', '散步时']
TEXT_TEMPLATES = [
    '{scene}，{name}喜欢{color}的{fruit}。',
    '{scene}，{name}拿着{color}的{fruit}。',
    '{scene}，{name}说：我爱吃{fruit}。',
    '{scene}，{name}选了{fruit}，它是{color}的。',
    '{scene}，{color}的{fruit}放在{name}面前。',
]
QUESTION_TEMPLATES = ['{name}喜欢什么水果？', '请说出{name}喜欢的水果。',
                      '{name}爱吃哪种水果？', '{name}最喜欢的水果是什么？']


def build_records():
    """返回四组原始记录：预训练训练/验证各 256/64 条，监督微调（SFT）各 24/8 条。

    预训练留出最后一种文本模板，SFT 留出最后一种提问模板，
    避免把同模板生成的句子随机拆到两边后，把记住句式误当成泛化。
    留出模板还含训练正文未见字符，不能把这次差异完全归因于句式变化。
    """
    groups = {key: [] for key in ('pretrain_train', 'pretrain_val', 'sft_train', 'sft_val')}
    for t, template in enumerate(TEXT_TEMPLATES):
        for s, scene in enumerate(SCENES):
            for n, (name, color, fruit) in enumerate(FACTS):
                record = {'record_id': f'p-{t}-{s}-{n}', 'template_id': t,
                          'text': template.format(scene=scene, name=name, color=color, fruit=fruit)}
                groups['pretrain_train' if t < 4 else 'pretrain_val'].append(record)
    for t, template in enumerate(QUESTION_TEMPLATES):
        for n, (name, color, fruit) in enumerate(FACTS):
            question = template.format(name=name)
            record = {'record_id': f's-{t}-{n}', 'template_id': t,
                      'prompt': f'问：{question}\n答：', 'answer': f'{color}的{fruit}。'}
            groups['sft_train' if t < 3 else 'sft_val'].append(record)
    return groups


def _pad_pairs(pairs, max_len):
    """将已对齐的 (输入编号, 标签编号) 列表补齐为两个 [B,T] 整数张量。

    T=max_len；长样本报错而不截断，短样本在右侧分别补 0 和 -100。
    输入的 0 仍会参与前向，但它对应的补齐标签不参与损失。
    """
    import torch
    if not pairs:
        raise ValueError('批次不能为空')
    xs, ys = [], []
    for x, y in pairs:
        if len(x) > max_len:
            raise ValueError(f'样本需要 {len(x)} 个输入位置，超过 {max_len}；不静默截断')
        xs.append(x + [0] * (max_len - len(x)))
        ys.append(y + [-100] * (max_len - len(y)))
    return torch.tensor(xs, dtype=torch.long), torch.tensor(ys, dtype=torch.long)


def make_pretrain_batch(records, tokenizer, max_len=32):
    """把 text 记录转成输入 x 和下一字符标签 y，均为 [B,T]。

    完整序列先加 BOS=1 和 EOS=2；x 去掉末项，y 去掉首项，
    因而 y 的每个位置恰好是该输入位置之后的字符，结束符也需要预测。
    """
    pairs = []
    for record in records:
        tokens = [1] + tokenizer.encode(record['text']) + [2]
        pairs.append((tokens[:-1], tokens[1:]))
    return _pad_pairs(pairs, max_len)


def make_sft_batch(records, tokenizer, max_len=32):
    """把 prompt/answer 记录转成 [B,T] 输入与仅监督答案的标签。

    SFT（监督微调）仍做下一字符预测，但提示词只提供上下文，
    不作为直接预测目标。答案字符及其后的 EOS 都保留有效标签。
    """
    pairs = []
    for record in records:
        prefix = [1] + tokenizer.encode(record['prompt'])
        tokens = prefix + tokenizer.encode(record['answer']) + [2]
        targets = tokens[1:]
        # 设含 BOS 的 prefix 长度为 L：首答案在完整序列的索引 L，
        # 去掉首项后落在 targets[L-1]，所以只屏蔽前 L-1 项，不能屏蔽到 L。
        # -100 只关闭这些位置的直接损失；提示词向量仍可经答案的计算路径获得梯度。
        targets[:len(prefix) - 1] = [-100] * (len(prefix) - 1)
        pairs.append((tokens[:-1], targets))
    return _pad_pairs(pairs, max_len)


def course_data_manifest(groups):
    """在内存中计算记录清单；保留原 v1 格式，使旧检查点摘要仍可核对。"""
    manifest = {'version': 1, 'description': '固定教学语法；按完整模板留出', 'files': {}}
    for group, records in groups.items():
        content = ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records)
        manifest['files'][f'{group}.jsonl'] = {'records': len(records),
                                             'sha256': hashlib.sha256(content.encode()).hexdigest()}
    return manifest


def course_data_hash(manifest):
    """返回检查点与日志使用的数据摘要；不依赖清单文件的缩进和键顺序。"""
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def write_course_data(directory, groups=None, tokenizer=None):
    """写出四组 JSONL、词表及含记录数/内容摘要的清单，返回清单字典。

    训练入口传入本次实际使用的记录和词表；省略时按当前规则生成。
    SHA-256 摘要用于核对文件内容，不是模型的训练参数。
    """
    from .tokenizer import CharTokenizer
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    groups = build_records() if groups is None else groups
    tokenizer = CharTokenizer.for_course() if tokenizer is None else tokenizer
    manifest = course_data_manifest(groups)
    for group, records in groups.items():
        content = ''.join(json.dumps(record, ensure_ascii=False) + '\n' for record in records)
        path = directory / f'{group}.jsonl'
        path.write_text(content, encoding='utf-8', newline='\n')
    (directory / 'vocab.json').write_text(json.dumps(tokenizer.to_dict(), ensure_ascii=False, indent=2),
                                         encoding='utf-8')
    (directory / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                            encoding='utf-8')
    return manifest


def load_run_data(run_directory, tokenizer, dataset_hash):
    """返回已核验的 (四组记录, 清单, 来源)，始终只读运行目录。

    优先使用 run/data 快照，并核对文件字节、记录数、词表及检查点数据摘要。
    旧运行没有快照时，只有当前生成规则仍与检查点完全一致才允许回退；
    已有但损坏的快照不会回退，以免把当前数据冒充原实验。
    """
    from .tokenizer import CharTokenizer
    snapshot = Path(run_directory) / 'data'
    if snapshot.exists():
        source = 'run_snapshot'
        try:
            manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
            names = ('pretrain_train', 'pretrain_val', 'sft_train', 'sft_val')
            if set(manifest['files']) != {f'{name}.jsonl' for name in names}:
                raise ValueError('数据快照清单必须包含完整的四组记录')
            groups = {}
            for name in names:
                content = (snapshot / f'{name}.jsonl').read_bytes()
                entry = manifest['files'][f'{name}.jsonl']
                if hashlib.sha256(content).hexdigest() != entry['sha256']:
                    raise ValueError(f'数据快照 {name}.jsonl 的内容摘要不一致')
                groups[name] = [json.loads(line) for line in content.decode('utf-8').splitlines()]
                if len(groups[name]) != entry['records']:
                    raise ValueError(f'数据快照 {name}.jsonl 的记录数不一致')
            saved_tokenizer = CharTokenizer.from_dict(
                json.loads((snapshot / 'vocab.json').read_text(encoding='utf-8')))
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ValueError(f'数据快照缺失或格式损坏：{snapshot}') from error
    else:
        source = 'validated_current_generator'
        groups = build_records()
        manifest = course_data_manifest(groups)
        saved_tokenizer = CharTokenizer.for_course()
    if course_data_hash(manifest) != dataset_hash:
        raise ValueError('数据摘要与检查点不一致；请恢复该运行的原始 data 快照，不能用当前规则冒充原数据')
    if saved_tokenizer.itos != tokenizer.itos:
        raise ValueError('数据词表与检查点词表不一致，不能重放原字符编号')
    return groups, manifest, source

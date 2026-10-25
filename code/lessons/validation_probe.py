"""事后补查（post-hoc）：用训练中出现过的字符组成未训练的新句式。

只读取 first_run 的三份检查点，比较下一字损失；不训练或保存模型。
运行：python -m lessons.validation_probe --out artifacts/validation_probe.json
"""
import argparse
import json
from pathlib import Path

import torch

from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.data import FACTS, SCENES, build_records, make_pretrain_batch
from tiny_lm.trace import export_trace, parameter_digest
from tiny_lm.train import evaluate

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = '{scene}，{name}爱吃{color}的{fruit}。'


def probe():
    """返回覆盖检查及固定权重的评分；新模板在看到原实验结果后选定。"""
    torch.set_num_threads(1)
    groups = build_records()
    # 8 个场景乘 8 条人物事实；只改变表达，不新增事实或字符。
    records = [{'text': TEMPLATE.format(scene=scene, name=name, color=color, fruit=fruit)}
               for scene in SCENES for name, color, fruit in FACTS]
    train_texts = {r['text'] for r in groups['pretrain_train']}
    probe_texts = {r['text'] for r in records}
    train_chars = set(''.join(train_texts))
    uncovered = sorted(set(''.join(probe_texts)) - train_chars)
    overlap = sorted(probe_texts & train_texts)
    facts_coverage = {name: sum(f'{name}爱吃{color}的{fruit}。' in r['text'] for r in records)
                      for name, color, fruit in FACTS}
    if uncovered or overlap or len(probe_texts) != len(records):
        raise ValueError('探针必须使用已见字符、各句唯一，且与训练完整句不重合')
    if any(count != len(SCENES) for count in facts_coverage.values()):
        raise ValueError('每条人物事实必须覆盖全部场景')
    checks = {'record_count': len(records), 'unique_record_count': len(probe_texts),
              'facts_coverage': facts_coverage, 'unseen_characters': uncovered,
              'complete_sentence_overlap': overlap,
              'original_heldout_unseen_characters': sorted(
                  set(''.join(r['text'] for r in groups['pretrain_val'])) - train_chars)}

    datasets = {'pretrain_train': groups['pretrain_train'],
                'original_heldout': groups['pretrain_val'], 'probe': records}
    stages, valid_tokens = {}, {}
    for stage in ('initial', 'pretrain', 'sft'):
        checkpoint = ROOT / 'artifacts/first_run' / f'{stage}.pt'
        model, tokenizer, _ = load_checkpoint(checkpoint)
        before = parameter_digest(model)
        losses = {}
        for name, rows in datasets.items():
            if any(3 in tokenizer.encode(r['text']) for r in rows):
                raise ValueError('当前数据含检查点词表外字符，不能用 UNK 代替评分')
            # x 是 BOS+正文，y 是正文+EOS；补齐标签为 -100，不计入平均。
            batches = [make_pretrain_batch(rows[i:i + 16], tokenizer,
                                          max_len=model.config.max_seq_len)
                       for i in range(0, len(rows), 16)]
            valid_tokens[name] = sum(int((y != -100).sum()) for _, y in batches)
            # evaluate 关闭梯度；各批平均损失按有效目标数加权，非简单平均。
            losses[name] = evaluate(model, batches)
        after = parameter_digest(model)
        if after != before:
            raise RuntimeError('评分改变了模型参数')
        stages[stage] = {'checkpoint': checkpoint.relative_to(ROOT).as_posix(),
                         'parameter_sha256_before': before, 'parameter_sha256_after': after,
                         'parameters_unchanged': True, 'losses': losses}
    return {'kind': 'post_hoc_validation_probe', 'post_hoc': True, 'template': TEMPLATE,
            'limitation': '看到原实验结果后补选的探针，不能当作事先留出的独立泛化成绩。',
            'scoring': '全词表下一字交叉熵，含 EOS，忽略 -100；按全体有效目标数平均。',
            'environment': {'torch': str(torch.__version__), 'device': 'cpu',
                            'dtype': 'float32', 'threads': torch.get_num_threads()},
            'checks': checks, 'valid_tokens': valid_tokens, 'records': records, 'stages': stages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/validation_probe.json')
    args = parser.parse_args()
    report = probe()
    export_trace(args.out, report)
    print(json.dumps({'post_hoc': True, 'template': TEMPLATE, 'checks': report['checks'],
                      'valid_tokens': report['valid_tokens'],
                      'losses': {stage: row['losses'] for stage, row in report['stages'].items()},
                      'report': str(args.out)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""第20讲独立迁移验收：先检查自己的三个函数，再选择实际训练。

python -m lessons.transfer_challenge --module exercises.transfer_task
python -m lessons.transfer_challenge --module exercises.transfer_task --train --out artifacts/my_transfer
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import random

import torch

from tiny_lm.checkpoint import load_checkpoint, save_checkpoint
from tiny_lm.generate import generate
from tiny_lm.train import evaluate, train_step
from tiny_lm.trace import parameter_digest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'exercises/transfer_data.json'


def read_data(path=DATA):
    """读题目给出的固定划分；验证整句不重合，留出字符均在训练中出现过。"""
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    train = {row['text'] for row in data['train']}
    val = {row['text'] for row in data['validation']}
    if train & val or len(train) != len(data['train']) or len(val) != len(data['validation']):
        raise ValueError('训练/留出整句不能重复')
    train_chars = set(''.join(train))
    if not set(''.join(val)) <= train_chars:
        raise ValueError('本任务应只改变句式，留出字符必须在训练中出现')
    return data, hashlib.sha256(raw).hexdigest()


def verify_submission(submission, data):
    """使用额外的小输入验收函数行为，不以抄中原来79或特定字符编号为通过。"""
    train = data['train']
    tokenizer = submission.build_tokenizer(train)
    chars = sorted({c for row in train for c in row['text']})
    expected_vocab = ['<pad>', '<bos>', '<eos>', '<unk>'] + chars
    assert tokenizer.itos == expected_vocab, '词表必须只来自本任务训练文字，并保持固定特殊编号'
    # 换一份最小数据，排除把本任务词表或字符编号直接写死的实现。
    other = submission.build_tokenizer([{'text': '甲乙。'}, {'text': '甲丙。'}])
    assert other.itos == ['<pad>', '<bos>', '<eos>', '<unk>'] + sorted('甲乙丙。')
    assert 3 not in tokenizer.encode('小唐喜欢橙色的橘子。'), '新人物/水果必须能编码'

    records = [{'text': '小唐'}, {'text': '橘子。'}]
    x, y = submission.make_batch(records, tokenizer, max_len=6)
    assert x.dtype == y.dtype == torch.long and x.shape == y.shape == (2, 6)
    for index, row in enumerate(records):
        ids = tokenizer.encode(row['text'])
        length = len(ids) + 1
        assert x[index].tolist() == [1] + ids + [0] * (6 - length), '输入必须以BOS开始、右侧补PAD'
        assert y[index].tolist() == ids + [2] + [-100] * (6 - length), '标签须错一位、保留EOS、只忽略填充'
    for sample, limit in [({'text': '龘'}, 6), ({'text': '小唐'}, 2)]:
        try:
            submission.make_batch([sample], tokenizer, max_len=limit)
        except ValueError:
            pass
        else:
            raise AssertionError('未知字和过长样本都必须明确拒绝')

    torch.manual_seed(42)
    model = submission.build_model(tokenizer)
    assert model.config.vocab_size == len(expected_vocab), '模型配置仍在沿用旧词表大小'
    assert (model.config.d_model, model.config.n_heads, model.config.n_layers,
            model.config.d_ff, model.config.max_seq_len) == (64, 2, 2, 128, 32), '本题只改词表，不改网络规模'
    with torch.no_grad():
        scores = model(x)
        changed = x.clone()
        changed[0, 2] = tokenizer.stoi['丁']
        altered = model(changed)
    assert scores.shape == (2, 6, len(expected_vocab)), '模型输出候选数必须等于新词表大小'
    assert torch.allclose(scores[0, :2], altered[0, :2]), '新模型不应泄漏未来位置'
    return tokenizer, model, {
        'new_vocabulary': True, 'works_on_other_characters': True,
        'shift_eos_padding': True, 'rejects_unknown_and_long_text': True,
        'output_matches_vocabulary': True, 'future_invisible': True,
    }


def run(submission, *, out=None, steps=1000, seed=42, train=False):
    """验收实现；可选从随机初值训练，保存自己的权重再重载，不改原课程数据。"""
    torch.set_num_threads(1)
    data, dataset_hash = read_data()
    tokenizer, checked_model, checks = verify_submission(submission, data)
    del checked_model
    report = {'task': 'new_character_transfer', 'dataset_sha256': dataset_hash,
              'seed': seed, 'checks': checks, 'vocabulary_size': tokenizer.vocab_size,
              'train_records': len(data['train']), 'validation_records': len(data['validation']),
              'validation_characters_seen_in_train': True, 'full_sentence_overlap': 0}
    if not train:
        return report
    if out is None or steps <= 0:
        raise ValueError('训练需要新的--out目录与正数步数')
    out = Path(out)
    # 首次实验写独立目录；重复运行请选另一个目录，避免把两个实验混在一起。
    if out.exists() and any(out.iterdir()):
        raise ValueError('输出目录已有文件，请为这次实验另选新目录')
    torch.manual_seed(seed)
    model = submission.build_model(tokenizer)
    sampler = random.Random(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.003, betas=(.9, .99),
                                 eps=1e-8, weight_decay=.01)
    def batches(rows):
        return [submission.make_batch(rows[i:i + 16], tokenizer) for i in range(0, len(rows), 16)]
    train_batches, val_batches = batches(data['train']), batches(data['validation'])
    history = []
    for step in range(steps + 1):
        if step % 50 == 0 or step == steps:
            history.append({'step': step, 'train_loss': evaluate(model, train_batches),
                            'validation_loss': evaluate(model, val_batches)})
        if step == steps:
            break
        # 仅训练划分进入反向；留出题只在evaluate中读取，不参与参数选择。
        selected = sampler.sample(data['train'], min(16, len(data['train'])))
        x, y = submission.make_batch(selected, tokenizer)
        train_step(model, x, y, optimizer, observe_token=tokenizer.stoi['小'])
    out.mkdir(parents=True, exist_ok=True)
    (out / 'data.json').write_bytes(DATA.read_bytes())
    checkpoint = out / 'model.pt'
    save_checkpoint(checkpoint, model, tokenizer,
                    {'stage': 'transfer_challenge', 'steps': steps, 'seed': seed,
                     'dataset_sha256': dataset_hash})
    # 验收磁盘上的模型，而非只相信刚刚留在内存中的对象。
    loaded, restored_tokenizer, _ = load_checkpoint(checkpoint)
    assert parameter_digest(loaded) == parameter_digest(model)
    probes = []
    for row in data['probes']:
        result = generate(loaded, restored_tokenizer, row['prompt'],
                          max_new_tokens=16, greedy=True)
        probes.append({**row, 'actual': result['generated_text'],
                       'stop_reason': result['stop_reason'],
                       'matched': result['generated_text'] == row['expected'] and result['stop_reason'] == 'eos'})
    report.update({'steps': steps, 'learning_rate': .003, 'history': history, 'probes': probes,
                   'parameter_count': sum(p.numel() for p in loaded.parameters()),
                   'parameter_sha256': parameter_digest(loaded),
                   'checkpoint_reloaded': True, 'checkpoint': 'model.pt',
                   'torch': str(torch.__version__)})
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', default='exercises.transfer_task')
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    try:
        report = run(importlib.import_module(args.module), out=args.out,
                     steps=args.steps, seed=args.seed, train=args.train)
    except (NotImplementedError, AssertionError, ValueError) as error:
        parser.exit(1, f'本次验收未通过：{error}\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

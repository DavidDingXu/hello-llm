"""第19讲：先降低微调学习率，再检验一项固定混训假设，同时评价新旧能力。

默认只查看已保存报告：python -m lessons.retention_experiment --inspect
重跑固定实验并另存：python -m lessons.retention_experiment --out artifacts/my_retention.json
全部训练只在内存发生，复用课程的模型、train_step、evaluate 和 generate；
不保存新权重，不改原数据与 first_run/transfer_run。运行仅需 requirements.txt。
"""
import argparse
import copy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import sys
import time

import torch

from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.data import build_records, load_run_data, make_pretrain_batch, make_sft_batch
from tiny_lm.generate import generate
from tiny_lm.trace import export_trace, parameter_digest
from tiny_lm.train import evaluate, train_step

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = ROOT / 'artifacts/first_run/pretrain.pt'
DEFAULT_REPORT = ROOT / 'artifacts/retention_experiment.json'
# 第一轮只比较学习率；第二轮在看过第一轮结果后固定 12 条问答 + 4 条原正文。
# strategy 与 protocol_round 保留这一区别，不把第二轮包装成未见结果前的预注册。
CONDITIONS = (('original_lr', .001, 'sft_only', 1),
              ('lower_lr', .0001, 'sft_only', 1),
              ('mixed_replay', .001, 'mixed_replay', 2))
GROUPS = ('sft_train', 'sft_val', 'old_continuation')


def content_hash(value):
    """规范化 JSON 内容摘要；与操作系统路径、JSON 缩进及换行符无关。"""
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def build_evaluation_sets(groups=None):
    """固定 24/8 条问答与 256 条熟悉续写；每条均按前缀/目标后缀表示。

    续写覆盖预训练训练集全部 8 人物 × 8 场景 × 4 模板。切点提前按模板固定，
    不根据任何模型输出选择题目；第四个预训练留出模板不算熟悉续写。
    """
    groups = build_records() if groups is None else groups
    old = []
    markers = ('喜欢', '拿着', '说：我爱吃', '选了')
    for record in groups['pretrain_train']:
        marker = markers[record['template_id']]
        prefix, answer = record['text'].split(marker, 1)
        old.append({'record_id': record['record_id'], 'template_id': record['template_id'],
                    'prompt': prefix + marker, 'answer': answer})
    return {'sft_train': [dict(r) for r in groups['sft_train']],
            'sft_val': [dict(r) for r in groups['sft_val']], 'old_continuation': old}


def prepare_batches(evaluation_sets, tokenizer, batch_size):
    """所有组都用相同标签规则：只计算目标后缀字符与 EOS，不计算给定前缀。"""
    return {name: [make_sft_batch(records[i:i + batch_size], tokenizer)
                   for i in range(0, len(records), batch_size)]
            for name, records in evaluation_sets.items()}


def measure_losses(model, batches):
    """复用有效 token 加权的课程评估器；不同阶段始终用同一批评估目标。"""
    return {name: evaluate(model, pairs) for name, pairs in batches.items()}


def score_generations(records, outputs):
    """分别报告文本完全一致、产生 EOS，以及二者同时满足的完整成功。"""
    if len(records) != len(outputs) or not records:
        raise ValueError('生成结果必须与非空评估集一一对应')
    items = []
    for record, output in zip(records, outputs):
        exact = output['generated_text'] == record['answer']
        items.append({'record_id': record['record_id'], 'actual': output['generated_text'],
                      'stop_reason': output['stop_reason'], 'text_exact': exact,
                      'complete_exact': exact and output['stop_reason'] == 'eos'})
    return {'sample_count': len(items),
            'text_exact_count': sum(r['text_exact'] for r in items),
            'complete_exact_count': sum(r['complete_exact'] for r in items),
            'eos_count': sum(r['stop_reason'] == 'eos' for r in items), 'items': items}


def evaluate_all(model, tokenizer, evaluation_sets, batches):
    """固定贪心、16 项上限；保留逐题原始输出与停止原因，不保存大体积候选轨迹。"""
    before = parameter_digest(model)
    losses = measure_losses(model, batches)
    results = {}
    for name, records in evaluation_sets.items():
        outputs = [generate(model, tokenizer, r['prompt'], greedy=True, max_new_tokens=16)
                   for r in records]
        results[name] = {'loss': losses[name],
                         'valid_target_count': sum(int((y != -100).sum()) for _, y in batches[name]),
                         **score_generations(records, outputs)}
    if parameter_digest(model) != before:
        raise RuntimeError('评估不应更新模型参数')
    return results


def sample_training_batch(records, tokenizer, sampler, *, batch_size,
                          replay_records=None, replay_sampler=None):
    """复用两种课程标签构造器；混训把 12 个答案目标与 4 段完整文本目标合批。

    两类输入都为 [B,32]；cat 后共 16 条，train_step 按整批有效 token 平均。
    4/16 是样本比例，不是损失权重；完整正文通常比问答的有效目标多。
    """
    if replay_records is not None and (batch_size != 16 or replay_sampler is None):
        raise ValueError('本轮混训固定 batch=16，且需要独立的原正文抽样器')
    qa_count = 12 if replay_records is not None else min(batch_size, len(records))
    selected = sampler.sample(records, qa_count)
    x, y = make_sft_batch(selected, tokenizer)
    selection = {'sft_record_ids': [r['record_id'] for r in selected], 'pretrain_record_ids': [],
                 'sft_valid_targets': int((y != -100).sum()), 'pretrain_valid_targets': 0}
    if replay_records is not None:
        replay = replay_sampler.sample(replay_records, 4)
        px, py = make_pretrain_batch(replay, tokenizer)
        selection['pretrain_record_ids'] = [r['record_id'] for r in replay]
        selection['pretrain_valid_targets'] = int((py != -100).sum())
        x, y = torch.cat((x, px)), torch.cat((y, py))
    return x, y, selection


def fit_trial(initial, tokenizer, records, batches, *, learning_rate, seed, steps, batch_size,
              replay_records=None):
    """从相同参数副本出发；第一轮只改学习率，第二轮只按固定配比替换训练样本。"""
    torch.manual_seed(seed)
    model = copy.deepcopy(initial)
    sampler = random.Random(seed)
    replay_sampler = random.Random(seed) if replay_records is not None else None
    sampled = hashlib.sha256()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, betas=(.9, .99),
                                 eps=1e-8, weight_decay=.01)
    history = [{'step': 0, 'losses': measure_losses(model, batches)}]
    budget = {'sft_examples': 0, 'pretrain_examples': 0,
              'sft_valid_targets': 0, 'pretrain_valid_targets': 0}
    replay_fractions = []
    start = time.perf_counter()
    for step in range(1, steps + 1):
        x, y, selection = sample_training_batch(records, tokenizer, sampler, batch_size=batch_size,
                                                replay_records=replay_records, replay_sampler=replay_sampler)
        # 记录整个批次序列的摘要，可以检查两组并未使用不同抽样。
        ids = selection['sft_record_ids'] if replay_records is None else {
            key: selection[key] for key in ('sft_record_ids', 'pretrain_record_ids')}
        sampled.update((json.dumps(ids) + '\n').encode('utf-8'))
        for category in ('sft', 'pretrain'):
            budget[category + '_examples'] += len(selection[category + '_record_ids'])
            budget[category + '_valid_targets'] += selection[category + '_valid_targets']
        replay_fractions.append(selection['pretrain_valid_targets'] /
                                (selection['sft_valid_targets'] + selection['pretrain_valid_targets']))
        train_step(model, x, y, optimizer, clip_norm=1., observe_token=tokenizer.stoi['小'])
        if step % 50 == 0 or step == steps:
            history.append({'step': step, 'losses': measure_losses(model, batches)})
    drift_squared = sum(float((after.detach().double() - before.detach().double()).square().sum())
                        for before, after in zip(initial.parameters(), model.parameters()))
    initial_squared = sum(float(p.detach().double().square().sum()) for p in initial.parameters())
    budget.update({'pretrain_token_fraction_over_all_steps': budget['pretrain_valid_targets'] /
                   (budget['sft_valid_targets'] + budget['pretrain_valid_targets']),
                   'mean_pretrain_token_fraction_per_step': sum(replay_fractions) / steps,
                   'min_pretrain_token_fraction_per_step': min(replay_fractions),
                   'max_pretrain_token_fraction_per_step': max(replay_fractions)})
    return model, {'history': history, 'training_and_loss_evaluation_seconds': time.perf_counter() - start,
                   'sampled_batches_sha256': sampled.hexdigest(), 'training_budget': budget,
                   'parameter_displacement_l2': math.sqrt(drift_squared),
                   'relative_parameter_displacement_l2': math.sqrt(drift_squared / initial_squared)}


def run_experiment(checkpoint=DEFAULT_CHECKPOINT, *, steps=300, seeds=(42, 43, 44), batch_size=16):
    """执行两轮共三组实验并返回报告；本函数不写任何文件。

    正式入口固定 300 步、三个种子、batch=16；函数参数允许测试缩短更新次数。
    三个种子只改变 SFT 抽样，预训练起点始终相同，不能当作三次预训练复现。
    """
    if steps <= 0 or batch_size <= 0 or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('步数、批量应为正数，种子应非空且互不重复')
    if batch_size != 16:
        raise ValueError('三组比较固定 batch=16；混训比例为 12 条问答与 4 条原正文')
    checkpoint = Path(checkpoint).resolve()
    checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    torch.set_num_threads(1)
    initial, tokenizer, metadata = load_checkpoint(checkpoint)
    if metadata.get('stage') != 'pretrain':
        raise ValueError('保留实验必须从预训练检查点开始')
    raw_groups, manifest, source = load_run_data(checkpoint.parent, tokenizer, metadata['dataset_hash'])
    evaluation_sets = build_evaluation_sets(raw_groups)
    batches = prepare_batches(evaluation_sets, tokenizer, batch_size)
    design = {
        'protocol_rounds': [
            {'round': 1, 'intervention': '仅将 SFT 学习率从 0.001 降为 0.0001，其余配置与数据不变',
             'selection': '在运行第一轮前固定这两个值，不用留出题挑选学习率或训练步数',
             'hypothesis': '减小每步参数调整可能减轻对熟悉续写的扰动，但也可能减慢问答学习'},
            {'round': 2, 'intervention': '学习率回到 0.001；每批 16 条改为 12 条问答 + 4 条原预训练正文',
             'selection': '作者观察到第一轮低学习率保留续写却损失留出问答后，只追加此固定配比，没有搜索更多比例',
             'hypothesis': '同时给旧正文直接损失约束，可能在学习问答时保留旧行为',
             'evaluation_status': '沿用已看过的评估题进行开发验证；没有独立的最终测试集'},
        ],
        'steps': steps, 'batch_size': batch_size, 'seeds': list(seeds),
        'conditions': {name: {'learning_rate': lr, 'strategy': strategy, 'protocol_round': round_id}
                       for name, lr, strategy, round_id in CONDITIONS},
        'mix_config': {'sft_examples_per_step': 12, 'pretrain_examples_per_step': 4,
                       'samplers': '两个独立 random.Random(seed)，分别从各自训练池无放回抽样，跨步可重复',
                       'loss_weighting': '不另设权重；整批有效 token 平均，实际比例见各 trial.training_budget'},
        'all_parameters_trainable': True,
        'optimizer': {'name': 'AdamW', 'betas': [.9, .99], 'eps': 1e-8,
                      'weight_decay': .01, 'clip_norm': 1., 'fresh_state_each_trial': True},
        'generation': {'greedy': True, 'max_new_tokens': 16, 'eos_id': 2},
        'loss': '交叉熵按有效 token 加权；所有组仅计目标后缀字符与 EOS，忽略前缀及 padding',
        'primary_success': '生成文本与完整目标后缀一致，且 stop_reason 为 eos',
    }
    trained_text = ''.join(r['text'] for r in raw_groups['pretrain_train']) + ''.join(
        r['prompt'] + r['answer'] for r in raw_groups['sft_train'])
    held_out_text = ''.join(r['prompt'] for r in raw_groups['sft_val'])
    evaluation = {
        'sha256': content_hash(evaluation_sets),
        'groups': {name: {'sample_count': len(records), 'sha256': content_hash(records),
                          'valid_target_count': sum(int((y != -100).sum()) for _, y in batches[name]),
                          'records': records} for name, records in evaluation_sets.items()},
        'held_out_prompt_characters_absent_from_training': sorted(set(held_out_text) - set(trained_text)),
        'limits': [
            '旧续写来自预训练训练集，测试已学行为的保留，不是未见文本泛化。',
            '8 条留出问答共用已知人物事实；最未在预训练或 SFT 训练文本出现，句式与字符变化混在一起。',
            '只有一个预训练检查点；三个 SFT 种子仅观察批次抽样敏感性，不代表大模型或自然语言总体。',
            '两个学习率均固定 300 步，比较的是相同步数下的结果，没有搜索各自最优训练预算。',
            '混训减少了每步问答数，增加了正文及总有效 token；相同步数不等于相同问答曝光量或计算量。',
            '第二轮设计参考过第一轮评估结果；这组题继续用于开发验证，不能充当独立最终测试。',
            '因果解释限于本次固定干预；参数位移是描述性记录，未定位具体导致退化的参数。',
        ],
    }
    report = {
        'schema_version': 1, 'kind': 'sft_retention_experiment',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'design': design, 'design_and_evaluation_sha256': content_hash({'design': design, 'sets': evaluation_sets}),
        'provenance': {
            'checkpoint': checkpoint.relative_to(ROOT).as_posix() if checkpoint.is_relative_to(ROOT) else str(checkpoint),
            'checkpoint_file_sha256': checkpoint_hash, 'parent_parameter_sha256': parameter_digest(initial),
            'checkpoint_metadata': {k: metadata[k] for k in ('stage', 'seed', 'steps', 'learning_rate',
                                                           'batch_size', 'dataset_hash') if k in metadata},
            'data_source': source, 'data_manifest': manifest, 'model_config': asdict(initial.config),
            'parameter_count': sum(p.numel() for p in initial.parameters()),
            'environment': {'python': sys.version.split()[0], 'torch': str(torch.__version__),
                            'platform': platform.platform(), 'machine': platform.machine(),
                            'device': 'cpu', 'dtype': 'float32', 'threads': torch.get_num_threads()},
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
                'lessons/retention_experiment.py', 'tiny_lm/data.py', 'tiny_lm/train.py',
                'tiny_lm/generate.py', 'tiny_lm/losses.py', 'tiny_lm/model.py',
                'tiny_lm/layers.py', 'tiny_lm/tokenizer.py', 'tiny_lm/checkpoint.py')},
        },
        'evaluation': evaluation,
        'before_sft': evaluate_all(initial, tokenizer, evaluation_sets, batches), 'trials': [],
    }
    # 先完整执行第一轮，再执行固定第二轮；过程不读取评估分数来改变任何超参数。
    for protocol_round in (1, 2):
        for seed in seeds:
            for condition, learning_rate, strategy, round_id in CONDITIONS:
                if round_id != protocol_round:
                    continue
                model, details = fit_trial(initial, tokenizer, raw_groups['sft_train'], batches,
                                          learning_rate=learning_rate, seed=seed, steps=steps,
                                          batch_size=batch_size, replay_records=(raw_groups['pretrain_train']
                                          if strategy == 'mixed_replay' else None))
                scores = evaluate_all(model, tokenizer, evaluation_sets, batches)
                report['trials'].append({'condition': condition, 'learning_rate': learning_rate, 'seed': seed,
                                         'strategy': strategy, 'protocol_round': protocol_round,
                                         'parameter_sha256': parameter_digest(model), **details, 'evaluation': scores})
                counts = ' '.join(f'{name}={scores[name]["complete_exact_count"]}/{scores[name]["sample_count"]}'
                                  for name in GROUPS)
                print(f'{condition} round={protocol_round} lr={learning_rate:g} seed={seed} {counts}', flush=True)
    report['provenance']['checkpoint_unchanged'] = (
        hashlib.sha256(checkpoint.read_bytes()).hexdigest() == checkpoint_hash)
    if not report['provenance']['checkpoint_unchanged']:
        raise RuntimeError('原始检查点在实验期间发生变化，请核查后重跑')
    return report


def write_report(path, report):
    """只写指定 JSON；拒绝覆盖原始实验记录和课程数据目录。"""
    path = Path(path).resolve()
    for protected in (ROOT / 'artifacts/first_run', ROOT / 'artifacts/transfer_run', ROOT / 'data'):
        if path.is_relative_to(protected):
            raise ValueError('不能覆盖原始实验记录或课程数据，请另选 --out 路径')
    if path.suffix.lower() != '.json':
        raise ValueError('--out 必须是 .json 文件路径')
    export_trace(path, report)


def inspect_report(path):
    """显示分子/分母与损失，完整逐题输出仍保存在同一报告中。"""
    report = json.loads(Path(path).read_text(encoding='utf-8'))
    print('完整成功 = 文本完全一致且正常产生 EOS；损失只计目标后缀与 EOS。')
    print('阶段 / 种子          训练问答        留出问答        熟悉续写')
    rows = [('微调前', report['before_sft'])] + [
        (f'{r["condition"]}/{r["seed"]}', r['evaluation']) for r in report['trials']]
    for label, scores in rows:
        cells = [f'{scores[g]["complete_exact_count"]}/{scores[g]["sample_count"]}' for g in GROUPS]
        print(f'{label:<22} ' + ' | '.join(cells))
        print('  loss: ' + ' | '.join(f'{scores[g]["loss"]:.6f}' for g in GROUPS))
    print('评估集 SHA-256:', report['evaluation']['sha256'])
    print('限制：最未进入训练文本；旧续写是熟悉模板；三个种子只改变微调抽样。')
    print('第二轮在看过第一轮结果后固定混训比例；沿用题目是开发验证，不是独立最终测试。')


def main(argv=None):
    """无参数或 --inspect 为只读；显式 --out 才开始完整实验，默认保护原始产物。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect', action='store_true', help='只读查看 --out 指定报告或随课报告')
    parser.add_argument('--checkpoint', type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument('--out', type=Path, help='新实验 JSON；与 --inspect 同用时指定要查看的 JSON')
    args = parser.parse_args(argv)
    if args.inspect or args.out is None:
        inspect_report(args.out or DEFAULT_REPORT)
        return
    # 在训练前验证输出路径；不为了检查可写性提前创建或截断文件。
    output = args.out.resolve()
    if output.suffix.lower() != '.json' or any(output.is_relative_to(p) for p in (
            ROOT / 'artifacts/first_run', ROOT / 'artifacts/transfer_run', ROOT / 'data')):
        parser.error('--out 应为原始实验和课程数据目录以外的 .json 文件')
    report = run_experiment(args.checkpoint)
    write_report(output, report)
    inspect_report(output)
    print('报告已保存：', output)


if __name__ == '__main__':
    main()

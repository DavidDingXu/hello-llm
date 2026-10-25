"""导出真实首步重放与原训练日志，供离线页面解释训练全过程。

首步从已保存的 initial.pt 重放；长程曲线只采用原日志的采样点。
没有保存的中间权重不会被插值或编造成动画帧，也不改写 first_run。
运行：python -m lessons.training_replay --run artifacts/first_run --out artifacts/training_replay.json
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from unittest.mock import patch

import torch

from tiny_lm.checkpoint import load_checkpoint
from tiny_lm.data import course_data_hash, load_run_data, make_pretrain_batch, make_sft_batch
from tiny_lm.losses import token_loss
from tiny_lm.trace import export_trace, parameter_digest
from tiny_lm.train import train_step

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / 'artifacts/first_run'
STAGES = ('initial', 'pretrain', 'sft')


def _display_path(path):
    """工程内用相对路径；读者指定的工程外运行目录保留绝对路径。"""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _file_digests(paths):
    """记录原文件字节摘要；参数的内存重放与磁盘检查点分别核对。"""
    return {_display_path(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def _describe_example(x, y, tokenizer):
    """展开一个样本的每个位置；-100 是评分约定，不能拿来查词表。"""
    inputs, targets = x.tolist(), y.tolist()
    return {'input_ids': inputs, 'input_tokens': [tokenizer.itos[i] for i in inputs],
            'target_ids': targets,
            'target_tokens': [tokenizer.itos[i] if i != -100 else '忽略' for i in targets],
            'loss_mask': [i != -100 for i in targets],
            'valid_target_count': sum(i != -100 for i in targets),
            'valid_target_indices': [i for i, target in enumerate(targets) if target != -100],
            'eos_target_positions': [i for i, target in enumerate(targets) if target == 2],
            'padding_positions': [i for i, token in enumerate(inputs) if token == 0]}


def _gradient_summary(parameters):
    """统计全部参数梯度；长向量长度与任意一个坐标的梯度不是一回事。"""
    gradients = [p.grad.detach() for p in parameters if p.grad is not None]
    norm = torch.linalg.vector_norm(torch.stack([torch.linalg.vector_norm(g) for g in gradients]))
    return {'norm': float(norm), 'tensors_with_gradient': len(gradients),
            'coordinates_with_gradient': sum(g.numel() for g in gradients),
            'nonzero_coordinates': sum(int(torch.count_nonzero(g)) for g in gradients),
            'all_finite': all(bool(torch.isfinite(g).all()) for g in gradients)}


def _first_step(records, directory, seed, batch_size, learning_rate):
    """沿生产 train_step 路径重放首步，在前向、裁剪与更新边界读取状态。"""
    model, tokenizer, _ = load_checkpoint(directory / 'initial.pt')
    # 与原 _fit 一致：独立的 Python 抽样器，种子、批大小和学习率读自该次日志。
    selected = random.Random(seed).sample(records, min(batch_size, len(records)))
    x, y = make_pretrain_batch(selected, tokenizer)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, betas=(.9, .99),
                                 eps=1e-8, weight_decay=.01)
    observed_row = tokenizer.stoi['小']
    before_weights = {name: p.detach().clone() for name, p in model.named_parameters()}
    digests = {'initial': parameter_digest(model)}
    # 选一个有效位置；不依赖特定人物、句式或字符，换合法 FACTS/种子仍可重放。
    last_valid = int((y[0] != -100).nonzero()[-1])
    position = min(7, last_valid)
    captured = {'shape_trace': [{'name': 'input', 'shape': list(x.shape),
                                 'dtype': str(x.dtype)}]}

    def capture_layer(name):
        def capture(module, inputs, output):
            captured['shape_trace'].append({'name': name, 'shape': list(output.shape),
                                             'representative_position': position,
                                             'first_four_values': output[0, position, :4].detach().tolist()})
        return capture

    def capture_forward(module, inputs, output):
        # hook 仅复制这次真实前向的结果，不替换输出，不改变梯度路径。
        captured['logits'] = output.detach().clone()
        capture_layer('logits')(module, inputs, output)
        digests['after_forward'] = parameter_digest(module)

    original_clip = torch.nn.utils.clip_grad_norm_

    def capture_clip(parameters, max_norm, *args, **kwargs):
        # 这里已完成 backward、尚未裁剪，所有 .grad 都可读取；参数仍应未变。
        parameters = list(parameters)
        digests['after_backward'] = parameter_digest(model)
        captured['gradient_before'] = _gradient_summary(parameters)
        captured['observed_gradient_before'] = float(model.embedding.weight.grad[observed_row, 0])
        # 仍调用 PyTorch 原裁剪函数；包裹它只为在同一训练步骤中捕获两个时点。
        result = original_clip(parameters, max_norm, *args, **kwargs)
        digests['after_clip'] = parameter_digest(model)
        captured['gradient_after'] = _gradient_summary(parameters)
        return result

    handles = [model.register_forward_hook(capture_forward),
               model.embedding.register_forward_hook(capture_layer('embedding')),
               model.final_norm.register_forward_hook(capture_layer('final_norm'))]
    handles += [block.register_forward_hook(capture_layer(f'block{i + 1}'))
                for i, block in enumerate(model.blocks)]
    try:
        with patch.object(torch.nn.utils, 'clip_grad_norm_', capture_clip):
            observation = train_step(model, x, y, optimizer, clip_norm=1., observe_token=observed_row)
    finally:
        for handle in handles:
            handle.remove()
    digests['after_optimizer'] = parameter_digest(model)

    # 整批损失来自原 train_step；为页面只展开第一条样本的 32×79 分数。
    logits = captured['logits']
    loss = token_loss(logits, y)
    representative = _describe_example(x[0], y[0], tokenizer)
    representative.update({'sample_index': 0, 'record': selected[0]})
    scores = logits[0, position]
    probabilities = scores.softmax(-1)
    target = int(y[0, position])
    probability = float(probabilities[target])
    changed = [int(torch.count_nonzero(p.detach() != before_weights[name]))
               for name, p in model.named_parameters()]
    before_norm = observation['grad_norm_before_clip']
    after_norm = captured['gradient_after']['norm']
    checks = {'forward_keeps_parameters': digests['initial'] == digests['after_forward'],
              'backward_keeps_parameters': digests['initial'] == digests['after_backward'],
              'clipping_keeps_parameters': digests['initial'] == digests['after_clip'],
              'optimizer_changes_parameters': digests['initial'] != digests['after_optimizer'],
              'loss_matches_captured_logits': math.isclose(float(loss), observation['batch_loss'],
                                                          rel_tol=0., abs_tol=1e-7)}
    if not all(checks.values()):
        raise RuntimeError('训练重放的状态变化时点不符合预期')
    return {'source': 'replayed_from_saved_initial_checkpoint',
            'checkpoint': _display_path(directory / 'initial.pt'), 'seed': seed,
            'sampling': f'random.Random({seed}).sample；只从 pretrain_train 抽取 {len(selected)} 条',
            'optimizer': {'name': 'AdamW', 'learning_rate': learning_rate, 'betas': [.9, .99],
                          'eps': 1e-8, 'weight_decay': .01},
            'batch': {'record_ids': [r['record_id'] for r in selected],
                      'records': selected, 'representative': representative},
            'shapes': {'input': list(x.shape), 'input_ids': list(x.shape), 'targets': list(y.shape),
                       'embedding': captured['shape_trace'][1]['shape'],
                       'block_outputs': [row['shape'] for row in captured['shape_trace']
                                         if row['name'].startswith('block')],
                       'logits': list(logits.shape), 'loss': list(loss.shape)},
            'forward': {'representative_logits': logits[0].tolist(),
                        'shape_trace': captured['shape_trace']},
            'loss': observation['batch_loss'], 'valid_target_count': int((y != -100).sum()),
            'target_probability': {'sample_index': 0, 'position': position,
                                   'input_token': tokenizer.itos[int(x[0, position])],
                                   'target_id': target, 'target_token': tokenizer.itos[target],
                                   'context_ids': x[0, :position + 1].tolist(),
                                   'context_tokens': [tokenizer.itos[i] for i in x[0, :position + 1]],
                                   'context_text': tokenizer.decode(x[0, :position + 1].tolist()),
                                   'logits': scores.tolist(), 'probabilities': probabilities.tolist(),
                                   'probability': probability,
                                   'negative_log_probability': -math.log(probability)},
            'gradient_norm': {'before_clip': before_norm, 'after_clip': after_norm,
                              'max_norm': 1., 'clip_scale': min(1., 1. / (before_norm + 1e-6))},
            'gradient_before_clip': captured['gradient_before'],
            'gradient_after_clip': captured['gradient_after'],
            'observed_parameter': {'name': 'embedding.weight', 'token': '小', 'row': observed_row,
                                   'column': 0, 'value_before': observation['observed_parameter_before'],
                                   'gradient_before_clip': captured['observed_gradient_before'],
                                   'gradient_after_clip': observation['observed_gradient_after_clip'],
                                   'value_after': observation['observed_parameter_after'],
                                   'update': observation['observed_update'],
                                   'scope': '这里只观察一个坐标，优化器仍更新全部模型参数。'},
            'aggregate_parameter_change': {'total_tensors': len(changed),
                                           'changed_tensors': sum(n > 0 for n in changed),
                                           'total_coordinates': sum(p.numel() for p in model.parameters()),
                                           'changed_coordinates': sum(changed)},
            'parameter_digests': digests, 'checks': checks}


def _prefix_comparisons(directory, groups):
    """固定两个前缀，用三阶段权重分别计算；原始评分分布与生成分布分开保存。"""
    # 同课程第一条文本与问答共享首条事实；提示与目标从当前样本中取得。
    question = groups['sft_train'][0]
    first_text = groups['pretrain_train'][0]['text']
    continuation = first_text[:-len(question['answer'])]
    prefixes = [{'id': 'continuation', 'prompt': continuation,
                 'expected_next_token': question['answer'][0],
                 'stages': {}},
                {'id': 'question', 'prompt': question['prompt'],
                 'expected_next_token': question['answer'][0], 'stages': {}}]
    for stage in STAGES:
        model, tokenizer, _ = load_checkpoint(directory / f'{stage}.pt')
        before = parameter_digest(model)
        for prefix in prefixes:
            ids = tokenizer.encode(prefix['prompt'], add_bos=True)
            if 3 in ids:
                raise ValueError('当前样本含检查点词表外字符，不能用 UNK 冒充原输入')
            inputs = torch.tensor([ids])
            with torch.no_grad():
                logits = model(inputs)
                scores = logits[0, -1]
                raw = scores.softmax(-1)  # 训练损失面对的完整 79 项分布。
                allowed = scores.clone()
                allowed[[0, 1, 3]] = float('-inf')
                generation = allowed.softmax(-1)  # 贪心生成屏蔽 PAD/BOS/UNK，保留 EOS。
            target = tokenizer.stoi[prefix['expected_next_token']]
            prefix.update({'input_ids': ids, 'input_tokens': [tokenizer.itos[i] for i in ids],
                           'expected_next_id': target})
            values, indices = generation.topk(5)
            prefix['stages'][stage] = {'shape': list(logits.shape), 'logits': scores.tolist(),
                                       'raw_probabilities': raw.tolist(),
                                       'generation_probabilities': generation.tolist(),
                                       'expected_next_probability': float(raw[target]),
                                       'expected_next_generation_probability': float(generation[target]),
                                       'top_candidates': [{'id': i, 'token': tokenizer.itos[i],
                                                           'probability': p}
                                                          for i, p in zip(indices.tolist(), values.tolist())],
                                       'parameter_digest': before}
        if parameter_digest(model) != before:
            raise RuntimeError('固定权重前向改变了参数')
    return prefixes


def _validate_sources(directory, histories, comparison, dataset_hash):
    """核对阶段来源与采样终点，避免把同名却不同次实验的文件拼成一条经历。"""
    digests, metadata, configs, vocabularies = {}, {}, [], []
    for stage in STAGES:
        model, tokenizer, meta = load_checkpoint(directory / f'{stage}.pt')
        digests[stage], metadata[stage] = parameter_digest(model), meta
        configs.append(asdict(model.config))
        vocabularies.append(tokenizer.itos)
        if meta.get('stage') != stage:
            raise ValueError(f'{stage}.pt 的阶段标记不一致')
        saved = comparison.get(stage, {})
        if saved.get('parameter_sha256') != digests[stage]:
            raise ValueError(f'{stage} 的生成记录与检查点参数来源不一致')
        if saved.get('training_steps') != meta.get('steps', 0):
            raise ValueError(f'{stage} 的生成记录与检查点步数不一致')
    if any(config != configs[0] for config in configs[1:]) or any(v != vocabularies[0] for v in vocabularies[1:]):
        raise ValueError('三个阶段必须使用相同的课程模型配置与词表')
    for stage in ('pretrain', 'sft'):
        log, history = histories[stage]['metadata'], histories[stage]['history']
        steps = log['steps']
        expected = [0, *range(50, steps + 1, 50)]
        if expected[-1] != steps:
            expected.append(steps)
        if steps <= 0 or [row['step'] for row in history] != expected:
            raise ValueError(f'{stage} 日志采样步数与结束步数不一致')
        if metadata[stage].get('steps') != steps or metadata[stage].get('history') != history:
            raise ValueError(f'{stage} 检查点与日志的历史/结束步数不一致')
        if any(metadata[stage].get(key) != log.get(key)
               for key in ('seed', 'batch_size', 'learning_rate')):
            raise ValueError(f'{stage} 检查点与日志的抽样/优化器配置不一致')
    for source in (metadata['sft'], histories['sft']['metadata']):
        if source.get('parent_parameter_sha256') != digests['pretrain']:
            raise ValueError('SFT 父参数与该目录 pretrain.pt 不一致')
    sources = list(metadata.values()) + [histories[stage]['metadata'] for stage in ('pretrain', 'sft')]
    if any(source.get('dataset_hash') != dataset_hash for source in sources):
        raise ValueError('回放数据与检查点/日志的数据摘要不一致，不能重放原批次')


def build_training_replay(run_directory=FIRST):
    """构建可直接嵌入 HTML 的普通数据；只有 CLI 最后一步才写出目标 JSON。"""
    torch.set_num_threads(1)
    directory = Path(run_directory).resolve()
    paths = [directory / f'{stage}.pt' for stage in STAGES]
    paths += [directory / name for name in ('pretrain_log.json', 'sft_log.json',
                                       'generation_comparison.json')]
    initial, tokenizer, metadata = load_checkpoint(directory / 'initial.pt')
    groups, manifest, data_source = load_run_data(directory, tokenizer, metadata['dataset_hash'])
    if data_source == 'run_snapshot':
        paths += [directory / 'data' / name
                  for name in ('manifest.json', 'vocab.json', *manifest['files'])]
    files_before = _file_digests(paths)
    model_info = {'config': asdict(initial.config), 'vocabulary': tokenizer.itos,
                  'parameter_count': sum(p.numel() for p in initial.parameters())}
    histories = {}
    for stage in ('pretrain', 'sft'):
        source = json.loads((directory / f'{stage}_log.json').read_text(encoding='utf-8'))
        # 不补齐中间步、不平滑、不推算中间权重；历史数组与原日志逐项相同。
        histories[stage] = {'source': _display_path(directory / f'{stage}_log.json'),
                            'metadata': {k: v for k, v in source.items() if k != 'history'},
                            'history': source['history'], 'sampling_interval_steps': 50,
                            'sampled_from_original_log': True, 'interpolated': False,
                            'intermediate_checkpoints_saved': False}
    comparison = json.loads((directory / 'generation_comparison.json').read_text(encoding='utf-8'))
    _validate_sources(directory, histories, comparison, course_data_hash(manifest))
    sft_record = groups['sft_train'][0]
    x, y = make_sft_batch([sft_record], tokenizer)
    sft_example = _describe_example(x[0], y[0], tokenizer)
    prefix_length = 1 + len(tokenizer.encode(sft_record['prompt']))
    sft_example.update({'record': sft_record, 'prefix_length': prefix_length,
                        'first_answer_index': prefix_length - 1,
                        'shapes': {'input_ids': list(x.shape), 'targets': list(y.shape)}})
    report = {'schema_version': 1, 'kind': 'training_replay', 'model': model_info,
              'first_step': _first_step(groups['pretrain_train'], directory,
                                        histories['pretrain']['metadata']['seed'],
                                        histories['pretrain']['metadata']['batch_size'],
                                        histories['pretrain']['metadata']['learning_rate']),
              'histories': histories,
              'sft_example': sft_example, 'prefix_comparisons': _prefix_comparisons(directory, groups),
              'saved_generation_comparison': comparison}
    files_after = _file_digests(paths)
    if files_before != files_after:
        raise RuntimeError('原始检查点、日志或数据快照文件发生变化')
    report['provenance'] = {'notes': [
        '首步由保存的初始权重重放，批次与 AdamW 设置沿用原训练入口；仅在内存更新一次。',
        '长程曲线仅含原日志每 50 步及最后一步的采样，首步重放不是原日志保存的一帧。',
        '原实验没有保存中间训练权重，不虚构逐帧参数；只比较已存的三个阶段。',
        '训练损失按全体有效下一字目标平均，包含 EOS，忽略 -100；不屏蔽输出候选。',
        '单坐标观察与全部参数的更新范围分开记录；原运行目录文件保持原样。',
        ('批次读取该运行的 data 快照；四组记录、词表和清单均已与检查点核验。'
         if data_source == 'run_snapshot' else
         '该旧运行没有 data 快照；当前生成器的记录摘要和词表与检查点一致，才允许重建批次。')],
        'run_directory': _display_path(directory),
        'lineage_verified': True, 'dataset_source': data_source,
        'dataset_directory': _display_path(directory / 'data') if data_source == 'run_snapshot' else None,
        'dataset_hash': course_data_hash(manifest), 'dataset_hash_matches_sources': True,
        'environment': {'python': sys.version.split()[0], 'torch': str(torch.__version__),
                        'device': 'cpu', 'dtype': 'float32', 'threads': torch.get_num_threads()},
        'file_sha256_before': files_before, 'file_sha256_after': files_after,
        'original_files_unchanged': True}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=FIRST,
                        help='含 initial/pretrain/sft 权重及完整训练日志的同配置运行目录')
    parser.add_argument('--out', type=Path, default=ROOT / 'artifacts/training_replay.json')
    args = parser.parse_args()
    report = build_training_replay(args.run)
    export_trace(args.out, report)
    first = report['first_step']
    print(json.dumps({'report': str(args.out), 'loss': first['loss'],
                      'valid_target_count': first['valid_target_count'],
                      'gradient_norm': first['gradient_norm'],
                      'observed_parameter': first['observed_parameter'],
                      'checks': first['checks'],
                      'original_files_unchanged': report['provenance']['original_files_unchanged']},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

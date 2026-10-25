"""运行预训练与监督微调（SFT），保存权重、损失记录和生成对照；默认使用 CPU。

B 为样本数，T 为输入位置数，V 为词表大小；x[B,T] 是输入编号，
y[B,T] 是下一字符标签，-100 表示该位置不计损失。前向算分数和损失，
反向算梯度，optimizer.step() 才更新参数；验证和生成都不更新参数。
"""
import argparse
import copy
from dataclasses import asdict
import json
import platform
import random
import sys
import time
from pathlib import Path

import torch

from .checkpoint import load_checkpoint, save_checkpoint
from .data import (build_records, course_data_hash, load_run_data, make_pretrain_batch,
                   make_sft_batch, write_course_data)
from .generate import generate
from .losses import token_loss
from .model import ModelConfig, TinyLM
from .tokenizer import CharTokenizer
from .trace import export_trace, parameter_digest
from .teaching import add_observation_arguments, observe_lesson


def train_step(model, x, y, optimizer, clip_norm=1., observe_token=0):
    """原地完成一次更新，返回损失、梯度范数及一个词向量参数的变化。

    x/y 均为 [B,T]，模型输出 [B,T,V]。batch_loss 是更新前本批的损失；
    观察点为 embedding[observe_token,0]，它是一个可调参数，不是输入编号。
    """
    model.train()
    # 清空上一步梯度，防止本次 backward 把新梯度继续加到旧值上。
    optimizer.zero_grad(set_to_none=True)
    logits = model(x)
    loss = token_loss(logits, y)
    # backward 只把梯度写入各参数的 .grad，尚未改变参数值。
    loss.backward()
    # 裁剪会统一缩小过大的梯度，不直接改参数；返回值是裁剪前的总范数。
    grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), clip_norm)
    parameter = model.embedding.weight
    old_value = parameter[observe_token, 0].item()
    gradient = parameter.grad[observe_token, 0].item()
    # 优化器在这里读取裁剪后的梯度及自身状态，执行真正的参数更新。
    optimizer.step()
    new_value = parameter[observe_token, 0].item()
    return {'batch_loss': loss.item(), 'grad_norm_before_clip': float(grad_norm),
            'observed_parameter_before': old_value, 'observed_gradient_after_clip': gradient,
            'observed_parameter_after': new_value, 'observed_update': new_value - old_value}


@torch.no_grad()
def evaluate(model, batches):
    """返回所有批次有效标签的平均损失；不建梯度图、不反向、不更新。

    eval() 切换层的运行模式，no_grad 才负责关闭梯度记录；结束后恢复原模式。
    按有效 token 数加权，避免短批次或大量 -100 的批次获得过高权重。
    """
    was_training = model.training
    model.eval()
    total_loss, total_tokens = 0., 0
    try:
        for x, y in batches:
            count = int((y != -100).sum())
            if count:
                total_loss += token_loss(model(x), y).item() * count
                total_tokens += count
    finally:
        model.train(was_training)
    if not total_tokens:
        raise ValueError('评估没有有效标签')
    return total_loss / total_tokens


def _batches(records, tokenizer, builder, batch_size):
    """按原记录顺序分批，由 builder 生成 (x,y)，供整组数据的固定评估使用。"""
    return [builder(records[i:i + batch_size], tokenizer) for i in range(0, len(records), batch_size)]


def _fit(model, tokenizer, records, validation, builder, *, steps, learning_rate, seed,
         batch_size=16):
    """对传入模型执行 steps 次更新，返回训练/验证历史和耗时秒数。

    builder 决定标签如何构造；优化器始终接收全部模型参数，验证记录不送入更新。
    每一步随机抽一批训练记录，每 50 步及最后一步评估完整训练集与验证集。
    """
    sampler = random.Random(seed)
    train_batches = _batches(records, tokenizer, builder, batch_size)
    val_batches = _batches(validation, tokenizer, builder, batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, betas=(.9, .99),
                                 eps=1e-8, weight_decay=.01)
    # AdamW 会保留梯度的一阶/二阶移动统计，并执行权重衰减；更新不只是 -lr*grad。
    observe_token = tokenizer.stoi['小']
    history = [{'step': 0, 'train_loss': evaluate(model, train_batches),
                'val_loss': evaluate(model, val_batches)}]
    start = time.perf_counter()
    for step in range(1, steps + 1):
        batch = sampler.sample(records, min(batch_size, len(records)))
        x, y = builder(batch, tokenizer)
        observation = train_step(model, x, y, optimizer, observe_token=observe_token)
        if step % 50 == 0 or step == steps:
            # train_loss/val_loss 使用更新后的参数；observation 中 batch_loss 来自更新前。
            row = {'step': step, 'train_loss': evaluate(model, train_batches),
                   'val_loss': evaluate(model, val_batches), **observation}
            history.append(row)
            print(f"step={step:4d} train={row['train_loss']:.4f} val={row['val_loss']:.4f}",
                  flush=True)
    return history, time.perf_counter() - start


def _environment():
    """记录运行版本与数值环境，便于比较实验；这些字段不参与模型计算。"""
    return {'python': sys.version.split()[0], 'torch': str(torch.__version__),
            'platform': platform.platform(), 'machine': platform.machine(),
            'device': 'cpu', 'dtype': 'float32', 'threads': torch.get_num_threads()}


def run_pretrain(directory, steps=1000, seed=42, batch_size=16):
    """从随机初值训练正文续写，保存初值/预训练权重及记录，返回预训练权重路径。

    训练目标覆盖正文所有有效的下一字符位置；先用独立副本检查小批次能否学会，
    再让原模型训练完整训练集，留出模板只用于验证。
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    groups, tokenizer = build_records(), CharTokenizer.for_course()
    model = TinyLM(ModelConfig(vocab_size=tokenizer.vocab_size))
    manifest = write_course_data(directory / 'data', groups, tokenizer)
    dataset_hash = course_data_hash(manifest)
    metadata = {'stage': 'initial', 'seed': seed, 'dataset_hash': dataset_hash,
                'environment': _environment(), 'config': asdict(model.config)}
    save_checkpoint(directory / 'initial.pt', model, tokenizer, metadata)
    # 同一前缀可能接不同人物，所以小批次损失也不必降到绝对零。
    # smoke_model 是副本；此处的 240 次更新不会改变后面完整训练的初始参数。
    smoke_records = [r for r in groups['pretrain_train'] if r['template_id'] == 3][:4]
    smoke_model = copy.deepcopy(model)
    smoke_optimizer = torch.optim.AdamW(smoke_model.parameters(), lr=.003, weight_decay=.01)
    sx, sy = make_pretrain_batch(smoke_records, tokenizer)
    smoke_initial = evaluate(smoke_model, [(sx, sy)])
    for _ in range(240):
        train_step(smoke_model, sx, sy, smoke_optimizer)
    smoke_final = evaluate(smoke_model, [(sx, sy)])
    export_trace(directory / 'small_batch.json', {'records': smoke_records, 'steps': 240,
                 'initial_loss': smoke_initial, 'final_loss': smoke_final})
    if smoke_final >= .1:
        raise RuntimeError(f'先解决训练链路：四条长记录过拟合 loss={smoke_final:.5f}')
    history, seconds = _fit(model, tokenizer, groups['pretrain_train'], groups['pretrain_val'],
                             make_pretrain_batch, steps=steps, learning_rate=.003,
                             seed=seed, batch_size=batch_size)
    metadata.update({'stage': 'pretrain', 'steps': steps, 'learning_rate': .003,
                     'batch_size': batch_size, 'seconds': seconds, 'history': history})
    save_checkpoint(directory / 'pretrain.pt', model, tokenizer, metadata)
    export_trace(directory / 'pretrain_log.json', metadata)
    export_trace(directory / 'xor.json', __import__('tiny_lm.tensor_mlp', fromlist=['train_xor']).train_xor())
    model.eval()
    text = '早上，小丁喜欢红色的苹果。'
    ids = torch.tensor([tokenizer.encode(text, add_bos=True)])
    with torch.no_grad():
        _, trace = model(ids, return_trace=True)
    export_trace(directory / 'forward_trace.json', {'kind': 'teaching_run', 'stage': 'pretrain',
                 'input_text': text, 'parameter_sha256': parameter_digest(model), 'trace': trace})
    return directory / 'pretrain.pt'


def run_sft(checkpoint, directory, steps=300, seed=42, batch_size=16):
    """载入预训练权重，以问答记录做全量监督微调，返回 SFT 权重路径。

    make_sft_batch 只让答案及 EOS 产生直接损失；这不等于冻结提示词的计算路径。
    课程入口沿用预训练运行的数据快照，避免两阶段混用不同事实；
    全部模型参数仍由 _fit 更新，没有加入 LoRA 等额外适配参数。
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    model, tokenizer, parent = load_checkpoint(checkpoint)
    parent_hash = parameter_digest(model)
    groups, _, _ = load_run_data(Path(checkpoint).parent, tokenizer, parent['dataset_hash'])
    if (directory / 'data').exists():
        load_run_data(directory, tokenizer, parent['dataset_hash'])
    else:
        write_course_data(directory / 'data', groups, tokenizer)
    history, seconds = _fit(model, tokenizer, groups['sft_train'], groups['sft_val'], make_sft_batch,
                             steps=steps, learning_rate=.001, seed=seed, batch_size=batch_size)
    report = {'stage': 'sft', 'seed': seed, 'steps': steps, 'learning_rate': .001,
              'batch_size': batch_size, 'seconds': seconds, 'environment': _environment(),
              'parent_parameter_sha256': parent_hash, 'dataset_hash': parent['dataset_hash'],
              'history': history, 'answers': {}}
    for group in ['sft_train', 'sft_val']:
        # 贪心生成用于检查完整答案是否一致；这是推理，不再利用正确答案更新模型。
        answers = []
        for sample in groups[group]:
            result = generate(model, tokenizer, sample['prompt'], greedy=True)
            answers.append({'record_id': sample['record_id'], 'prompt': sample['prompt'],
                            'expected': sample['answer'], 'actual': result['generated_text'],
                            'exact_match': result['generated_text'] == sample['answer'],
                            'stop_reason': result['stop_reason']})
        report['answers'][group] = answers
        report[group + '_exact_match'] = sum(r['exact_match'] for r in answers) / len(answers)
    save_checkpoint(directory / 'sft.pt', model, tokenizer, report)
    export_trace(directory / 'sft_log.json', report)
    return directory / 'sft.pt'


def compare_stages(directory):
    """用同一组提示词比较初值、预训练、SFT 权重的贪心输出，返回对照字典。

    参数摘要在生成前后必须相同，用来核对推理没有悄悄修改模型权重。
    若同目录有预训练和SFT，先核对SFT确实从这份预训练参数继续得到。
    """
    directory = Path(directory)
    prompts = ['早上，小丁喜欢', '晚上，小周拿着', '问：小丁喜欢什么水果？\n答：',
               '问：小周喜欢什么水果？\n答：']
    comparison = {}
    for stage in ['initial', 'pretrain', 'sft']:
        path = directory / f'{stage}.pt'
        if not path.exists():
            continue
        model, tokenizer, metadata = load_checkpoint(path)
        before = parameter_digest(model)
        if stage == 'sft' and 'pretrain' in comparison:
            # 文件同名不代表属于同一次实验；重做预训练后可能还留着旧SFT。
            if metadata.get('parent_parameter_sha256') != comparison['pretrain']['parameter_sha256']:
                raise ValueError('sft.pt的父参数与本目录pretrain.pt不一致；请从当前预训练权重重做微调，或使用新的输出目录')
        runs = [generate(model, tokenizer, prompt, greedy=True) for prompt in prompts]
        assert parameter_digest(model) == before
        comparison[stage] = {'parameter_sha256': before, 'outputs': runs,
                             'training_steps': metadata.get('steps', 0)}
    export_trace(directory / 'generation_comparison.json', comparison)
    return comparison


def main(argv=None):
    """命令行入口；--smoke 缩短更新次数，训练和保存流程仍会实际执行。"""
    parser = argparse.ArgumentParser(description='最小教学模型：实际预训练、SFT 和运行记录')
    parser.add_argument('--out', type=Path, default=Path('artifacts/my_run'))
    parser.add_argument('--stage', choices=['all', 'pretrain', 'sft'], default='all')
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--pretrain-steps', type=int, default=1000)
    parser.add_argument('--sft-steps', type=int, default=300)
    parser.add_argument('--smoke', action='store_true')
    add_observation_arguments(parser)
    args = parser.parse_args(argv)
    if min(args.pretrain_steps, args.sft_steps) <= 0:
        parser.error('更新步数应为正数')
    if args.stage in ('all', 'pretrain'):
        with observe_lesson(17, verbose=args.verbose, step=args.step):
            checkpoint = run_pretrain(args.out, steps=100 if args.smoke else args.pretrain_steps)
    else:
        if args.checkpoint is None:
            parser.error('SFT 需要 --checkpoint 指向预训练权重')
        checkpoint = args.checkpoint
    if args.stage in ('all', 'sft'):
        with observe_lesson(19, verbose=args.verbose, step=args.step):
            run_sft(checkpoint, args.out, steps=30 if args.smoke else args.sft_steps)
    comparison = compare_stages(args.out)
    print(json.dumps({stage: [r['generated_text'] for r in item['outputs']]
                      for stage, item in comparison.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

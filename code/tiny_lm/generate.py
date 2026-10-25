"""逐字符自回归生成：把新选中的编号接回输入，再预测下一项，不更新参数。

输入每次只有一个样本；T 为当前前缀长度，V 为词表大小。
这里没有 KV cache（历史键/内容向量缓存），每一步都会重新计算整个前缀。
"""

import torch


@torch.no_grad()
def generate(model, tokenizer, prompt, max_new_tokens=8, greedy=False, temperature=.8, seed=42):
    """从 prompt 生成至多 max_new_tokens 项，返回文本、编号、候选概率和停止原因。

    greedy=True 每次取最高分；否则按温度调整后的概率抽样。seed 固定本次抽样序列。
    EOS、上下文长度上限、新增项数上限都可结束生成；不截断旧前缀来继续生成。
    """
    if max_new_tokens < 0 or (not greedy and temperature <= 0):
        raise ValueError('新增长度不能为负，采样温度必须为正')
    # BOS=1 也占一个上下文位置；提示词不先补 EOS，否则会提前表达“已经结束”。
    tokens = [1] + tokenizer.encode(prompt)
    if 3 in tokens:
        raise ValueError('输入包含教学词表以外的字符；请使用水果小世界的已知字符')
    if len(tokens) > model.config.max_seq_len:
        raise ValueError('提示词已超过上下文长度')
    device = next(model.parameters()).device
    generator = torch.Generator(device=device).manual_seed(seed)
    generated, steps = [], []
    stop_reason = 'max_new_tokens'
    was_training = model.training
    # eval() 管运行模式，装饰器 no_grad 管梯度记录；两者都不会自行更新参数。
    model.eval()
    try:
        for index in range(max_new_tokens):
            if len(tokens) >= model.config.max_seq_len:
                stop_reason = 'context_limit'
                break
            inputs = torch.tensor([tokens], dtype=torch.long, device=device)
            # 输入 [1,T] 得到分数 [1,T,V]；只用最后一个位置的 V 个分数预测新字符。
            logits = model(inputs)[0, -1].clone()
            # 不输出 PAD=0、BOS=1、UNK=3；EOS=2 仍可被选中并触发停止。
            logits[[0, 1, 3]] = float('-inf')
            # softmax 的最后一轴是候选字符轴；贪心选择时温度不参与计算。
            probabilities = (logits if greedy else logits / temperature).softmax(-1)
            selected = int(probabilities.argmax() if greedy else
                           torch.multinomial(probabilities, 1, generator=generator).item())
            top_values, top_ids = probabilities.topk(min(5, len(probabilities)))
            steps.append({'step': index, 'input_ids': list(tokens), 'selected_id': selected,
                          'selected_token': tokenizer.itos[selected],
                          'top_candidates': [{'token': tokenizer.itos[i], 'id': i, 'probability': p}
                                             for i, p in zip(top_ids.tolist(), top_values.tolist())]})
            tokens.append(selected)
            if selected == 2:
                # EOS 记入 steps，但不加入可见的 generated_text。
                stop_reason = 'eos'
                break
            generated.append(selected)
    finally:
        # 即使生成中报错，也恢复调用前的训练/评估模式。
        model.train(was_training)
    return {'prompt': prompt, 'generated_text': tokenizer.decode(generated),
            'generated_ids': generated, 'stop_reason': stop_reason, 'steps': steps,
            'greedy': greedy, 'temperature': None if greedy else temperature, 'seed': seed}

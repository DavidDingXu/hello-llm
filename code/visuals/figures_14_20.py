"""第14—20讲原创机制图；只消费逐讲trace，不训练或改写实验记录。"""
import math

from figure_tools import *


PALE = {'input': '#ECF3FB', 'param': '#F1ECF7',
        'output': '#E9F4F1', 'grad': '#FAEDF2'}


def route(points, color='line', width=3, head=True):
    path = 'M' + ' L'.join(f'{x} {y}' for x, y in points)
    marker = f' marker-end="url(#a-{color})"' if head else ''
    return f'<path d="{path}" fill="none" stroke="{C[color]}" stroke-width="{width}"{marker}/>'


def panel(x, y, w, h, title, value=None, color='input', size=34):
    result = rect(x, y, w, h, PALE.get(color, 'light'), color)
    if value is None:
        return result + text(x + w / 2, y + h / 2 + size * .34,
                             title, size, color, 'middle')
    title_size, title_y, value_y = (30, 33, h - 12) if h < 105 else (32, 40, h - 24)
    return result + text(x + w / 2, y + title_y, title, title_size, color, 'middle') + text(
        x + w / 2, y + value_y, value, size, 'ink', 'middle')


def vector(x, y, values, width=648, color='input', size=34, precision=3, gutter=7):
    cell = width / len(values)
    result = ''
    for i, value in enumerate(values):
        label = f'{value:.{precision}f}'.rstrip('0').rstrip('.') if isinstance(value, float) else str(value)
        result += rect(x + i * cell, y, cell - gutter, 66, PALE.get(color, 'light'), color, r=6)
        result += text(x + (i + .5) * cell - gutter / 2, y + 45, label, size, 'ink', 'middle')
    return result


def number(value, digits=6):
    return f'{value:.{digits}f}'


def chart(history, x, y, width, height, max_y, max_step, ticks_y, ticks_x):
    """坐标轴与每个原始评估点；无插值平滑。"""
    result = text(x - 56, y - 18, '损失', 30, 'muted')
    for tick in ticks_y:
        py = y + height * (1 - tick / max_y)
        result += line(x, py, x + width, py, 'line', 1)
        result += text(x - 15, py + 11, tick, 30, 'muted', 'end')
    for tick in ticks_x:
        px = x + width * tick / max_step
        result += line(px, y + height, px, y + height + 10)
        result += text(px, y + height + 47, tick, 30, 'muted', 'middle')
    result += line(x, y, x, y + height, 'muted')
    result += line(x, y + height, x + width, y + height, 'muted')
    for key, color in [('train_loss', 'output'), ('val_loss', 'grad')]:
        points = [(x + width * row['step'] / max_step,
                   y + height * (1 - row[key] / max_y)) for row in history]
        result += route(points, color, 3.5, False)
        for px, py in points:
            result += f'<circle cx="{px}" cy="{py}" r="4.5" fill="{C[color]}"/>'
    result += text(x + width / 2, y + height + 94, '参数更新次数', 32, 'ink', 'middle')
    return result


def legend(y):
    return (line(150, y - 10, 205, y - 10, 'output', 4) + text(220, y, '训练', 32, 'output')
            + line(390, y - 10, 445, y - 10, 'grad', 4) + text(460, y, '留出', 32, 'grad'))


def figure14():
    d = read(14)
    assert all(math.isclose(u * g, z, abs_tol=1e-12)
               for u, g, z in zip(d['up'], d['gate'], d['product']))
    s = panel(240, 150, 240, 72, 'x = [1, 2]', color='input', size=36)
    s += route([(360, 222), (360, 243), (186, 243), (186, 264)], 'input')
    s += route([(360, 243), (534, 243), (534, 264)], 'input')
    s += panel(36, 268, 300, 92, 'up 投影', 'W_up [4,2]', 'param', 32)
    s += panel(384, 268, 300, 92, 'gate 投影', 'W_gate [4,2]', 'param', 32)
    s += text(186, 410, '产生内容 u', 32, 'input', 'middle')
    s += text(534, 410, 'SiLU 后产生乘数 g', 30, 'ink', 'middle')
    s += line(36, 440, 684, 440)
    s += text(36, 488, '蓝：u　青：相乘后的 z', 32)
    zero, unit = 410, 88
    effects = ['变号', '归零', '幅度变小', '幅度变大']
    for i, (u, g, z) in enumerate(zip(d['up'], d['gate'], d['product'])):
        top = 545 + i * 158
        factor = f'({g:.3f})' if g < 0 else f'{g:.3f}'.rstrip('0').rstrip('.')
        equation = f'{fmt(u)} × {factor} ≈ {z:.3f}' if g != 0 else f'{fmt(u)} × 0 = 0'
        s += text(36, top, equation, 32)
        s += text(684, top, effects[i], 30, 'output', 'end')
        s += line(zero, top + 18, zero, top + 100, 'muted', 2)
        # 所有行使用同一零点与同一刻度；负数向左，不把符号藏进文本里。
        for offset, value, label, color in [(32, u, 'u', 'input'), (76, z, 'z', 'output')]:
            s += text(62, top + offset + 17, label, 30, color)
            endpoint = zero + value * unit
            s += rect(min(zero, endpoint), top + offset,
                      abs(endpoint - zero), 22, color, r=2)
            if value == 0:
                s += f'<circle cx="{zero}" cy="{top+offset+11}" r="5" fill="{C[color]}"/>'
    baseline = 1143
    s += line(zero - 2 * unit, baseline, zero + 3 * unit, baseline, 'muted', 2)
    for tick in range(-2, 4):
        x = zero + tick * unit
        s += line(x, baseline, x, baseline + 9, 'muted')
        s += text(x, baseline + 43, str(tick).replace('-', '−'), 30, 'muted', 'middle')
    s += text(360, 1234, '四行共用刻度；负值向左，正值向右', 30, 'ink', 'middle')
    s += arrow(360, 1260, 360, 1290, 'output')
    s += panel(60, 1305, 600, 76, 'down：z₁+z₃，z₂+z₄', color='param', size=34)
    s += arrow(360, 1385, 360, 1422, 'output')
    s += vector(145, 1438, d['output'], width=430, color='output', size=38)
    s += text(360, 1560, '图中保留3位小数，计算使用完整精度', 30, 'muted', 'middle')
    save('14-swiglu', '01-机制', svg(
        '四个乘数，四种数值变化', '同次手算 · 先逐项相乘，再投影回两维', s, 1610))

    def linear(xs, weights):
        return [sum(a * b for a, b in zip(xs, row)) for row in weights]

    def ffn(xs):
        u, a = linear(xs, d['W_up']), linear(xs, d['W_gate'])
        g = [v / (1 + math.exp(-v)) for v in a]
        return linear([u[i] * g[i] for i in range(len(u))], d['W_down'])

    samples = [[1., 2.], [2., 1.], [-1., 1.]]
    changed = [10., -3.]
    s = text(360, 180, '同一个样本的三个位置', 36, 'ink', 'middle')
    for i, sample in enumerate(samples):
        px = 36 + i * 228
        s += text(px + 96, 240, f'位置 {i}', 34, 'input', 'middle')
        value = f'[{fmt(sample[0])}, {fmt(sample[1])}]'
        s += panel(px, 265, 192, 82, value, color='input')
        s += arrow(px + 96, 350, px + 96, 440, 'input')
        s += panel(px, 450, 192, 82, '同一个FFN', color='param', size=32)
        s += arrow(px + 96, 535, px + 96, 610, 'output')
        values = ffn(sample)
        s += rect(px, 620, 192, 128, PALE['output'], 'output')
        s += lines(px + 96, 666, [f'{v:.3f}' for v in values], 34, 48, 'output', 'middle')
    s += line(132, 410, 588, 410, 'param', 3)
    s += text(360, 390, '共享三组 W', 34, 'param', 'middle')
    s += text(36, 825, f'只改位置2：{samples[2]} → {changed}', 32, 'input')
    s += text(36, 885, '位置0的输出仍为', 34)
    s += text(360, 950, '[' + ', '.join(f'{v:.3f}' for v in d['output']) + ']', 42, 'output', 'middle')
    s += line(36, 1005, 684, 1005)
    s += text(360, 1070, '正式模型：64 → 128 → 64', 36, 'ink', 'middle')
    s += text(360, 1140, '3 × 64 × 128 = 24,576 参数', 34, 'param', 'middle')
    save('14-swiglu', '02-验证', svg(
        '每个位置，独立经过同一FFN', '逐位置计算 · 不读取另一个位置的输入', s, 1200))


def figure15():
    d = read(15)
    s = ''
    for i, (value, px) in enumerate(zip(d['x'], [190, 530])):
        s += panel(px - 105, 165, 210, 80, fmt(value), color='input', size=40)
        s += arrow(px, 245, px, 310, 'input')
        s += panel(px - 105, 320, 210, 80, f'{fmt(value)}² = {fmt(value * value)}', color='ink')
        s += route([(px, 400), (px, 430), (360, 430), (360, 465)], 'line')
    squares = [v * v for v in d['x']]
    mean_square = sum(squares) / len(squares)
    average_label = '平均：(' + '+'.join(fmt(v) for v in squares) + f')/{len(squares)}'
    s += panel(180, 470, 360, 85, average_label, fmt(mean_square), 'ink', 36)
    s += arrow(360, 555, 360, 615)
    s += panel(180, 625, 360, 110, '加 eps，再开方', number(d['rms']), 'ink', 40)
    for value, px in zip(d['x'], [190, 530]):
        edge = 45 if px == 190 else 675
        s += route([(px - 100 if px == 190 else px + 100, 205), (edge, 205),
                    (edge, 835), (px - 47 if px == 190 else px + 47, 835)], 'input')
        s += route([(360, 735), (360, 785), (px, 785), (px, 804)], 'line')
        s += circle(px, 835, 30, '÷', 'ink', 38)
        s += text(px, 930, '× g' + str(1 if px == 190 else 2), 36, 'param', 'middle')
        s += text(px, 985, '初值为1', 32, 'param', 'middle')
        s += arrow(px, 865, px, 890, 'output')
        s += arrow(px, 1005, px, 1050, 'output')
    s += vector(75, 1070, d['normalized'], width=570, color='output', size=38, precision=6)
    s += text(360, 1210, '两项比例仍为 3 : 4', 36, 'ink', 'middle')
    s += text(360, 1270, '平均值 ≈ ' + number(d['mean_after']), 34, 'ink', 'middle')
    save('15-residual-and-rmsnorm', '01-机制', svg(
        '按均方根缩放，不减均值', f'手算 · x={d["x"]} · eps=10⁻⁵ · g初值为1', s, 1330))

    s = panel(240, 160, 240, 80, '[3, 4]', color='input', size=40)
    s += route([(240, 200), (90, 200), (90, 560), (325, 560)], 'input')
    s += route([(480, 200), (565, 200), (565, 290)], 'input')
    s += panel(450, 300, 230, 90, 'F(x)=2x', color='param')
    s += arrow(565, 390, 565, 435, 'output')
    s += panel(450, 445, 230, 80, str([int(v) for v in d['residual_branch']]), color='output')
    s += route([(565, 525), (565, 560), (395, 560)], 'output')
    s += circle(360, 560, 34, '+', 'ink', 44)
    s += text(115, 390, '直路 ×1', 34, 'input')
    s += text(360, 420, '支路 ×2', 34, 'param', 'middle')
    s += arrow(360, 595, 360, 640, 'output')
    s += panel(220, 650, 280, 80, str([int(v) for v in d['residual_output']]), color='output', size=40)
    s += text(360, 800, 'L=y₁+y₂ 时，dL/dx=[3,3]', 34, 'grad', 'middle')
    s += line(36, 845, 684, 845)
    s += text(36, 900, '完整块：归一发生在支路入口', 34)
    for top, first, second, symbol in [(965, 'Norm₁', 'Attention', 'x'),
                                        (1190, 'Norm₂', 'FFN', 'h')]:
        s += panel(36, top, 90, 74, symbol, color='input', size=36)
        s += arrow(126, top + 37, 164, top + 37, 'input')
        s += box(170, top, 165, 74, first, 'ink', 32)
        s += arrow(335, top + 37, 370, top + 37)
        s += box(375, top, 210, 74, second, 'ink', 32)
        s += arrow(585, top + 37, 620, top + 37, 'output')
        s += circle(652, top + 37, 30, '+', 'ink', 36)
        s += route([(80, top), (80, top - 36), (652, top - 36), (652, top + 7)], 'input')
    s += route([(652, 1032), (652, 1110), (80, 1110), (80, 1180)], 'output')
    s += arrow(652, 1257, 652, 1325, 'output')
    s += text(605, 1340, 'y', 40, 'output')
    save('15-residual-and-rmsnorm', '02-验证', svg(
        '残差保留了一条直路', '手算：x+2x · 下半图：完整Pre-Norm块', s, 1390))


def figure16():
    d = read(16)
    shapes = dict(d['shapes'])
    stages = [('ids', '输入编号', 'input'), ('embedding', 'Embedding', 'param'),
              ('block1', '模型块1', 'ink'), ('block2', '模型块2', 'ink'),
              ('norm', '最后RMSNorm', 'ink'), ('logits', '输出投影 → logits', 'output')]
    s = text(360, 170, d['text'], 34, 'input', 'middle')
    for i, (key, label, color) in enumerate(stages):
        top = 215 + i * 178
        shape = '[' + ','.join(str(v) for v in shapes[key]) + ']'
        s += panel(160, top, 400, 120, label, shape, color, 38)
        if i < len(stages) - 1:
            s += arrow(360, top + 120, 360, top + 168, 'output' if key == 'norm' else 'line')
    s += text(360, 1280, '每个位置保留一行79项候选分数', 34, 'output', 'middle')
    save('16-transformer', '01-机制', svg(
        '文字进入，候选分数出来', '真实前向 · pretrain · 1个样本 · 14个位置', s, 1340))

    s = ''
    names = {'embedding': 'Embedding', 'block1': '第一块', 'block2': '第二块', 'norm': '最后RMSNorm'}
    for i, row in enumerate(d['coordinates_first4']):
        top = 200 + 180 * i
        s += text(36, top - 20, names[row['name']], 34)
        s += vector(36, top, row['values'], color='output' if i == 3 else 'input')
        if i < 3:
            s += arrow(360, top + 75, 360, top + 130)
    s += line(36, 860, 684, 860)
    config = d['config']; v, width = config['vocab_size'], config['d_model']
    f, layers_count = config['d_ff'], config['n_layers']
    one_block = 4 * width * width + 3 * width * f + 2 * width
    parts = [(v * width, 'input'), (one_block, 'output'),
             (one_block, 'output'), (width, 'param'), (v * width, 'input')]
    x = 36
    for count, color in parts:
        part_width = 648 * count / d['parameter_count']
        s += rect(x, 935, part_width, 68, color, 'line', r=0)
        x += part_width
    s += text(360, 910, '参数组成', 36, 'ink', 'middle')
    s += text(360, 1070, f'两个块：2 × {one_block:,}', 36, 'output', 'middle')
    s += text(360, 1130, f'输入表 + 输出头：2 × {v * width:,}', 34, 'input', 'middle')
    s += text(360, 1190, f'最后归一：{width}', 34, 'param', 'middle')
    s += text(360, 1280, f'合计 {d["parameter_count"]:,}', 48, 'ink', 'middle', 600)
    save('16-transformer', '02-验证', svg(
        '沿位置7，追踪真实数值', '“欢” · 只显示坐标0–3 · 全部64项参与计算', s, 1340))


def figure17():
    d = read(17); run = d['pretrain']; last = run['history'][-1]
    s = panel(36, 165, 300, 110, '训练：256条', '4套句式', 'input', 34)
    s += panel(384, 165, 300, 110, '留出：64条', '另1套句式', 'grad', 34)
    s += route([(186, 275), (186, 315), (360, 315), (360, 350)], 'input')
    s += panel(160, 360, 400, 80, '随机取16条 → x,y', color='input')
    stages = [(510, 'model(x) → logits', 'param'),
              (660, '平均有效目标损失', 'ink'),
              (810, '反向 → 裁剪梯度≤1', 'grad'),
              (960, 'AdamW → 参数更新', 'param')]
    for top, label, color in stages:
        s += arrow(360, top - 70, 360, top - 10, 'line')
        s += panel(160, top, 400, 80, label, color=color)
    s += route([(160, 1000), (65, 1000), (65, 550), (150, 550)], 'param', 4)
    s += text(90, 1130, f'{run["steps"]}次更新', 36, 'param')
    s += panel(160, 1190, 400, 100, '每50步：完整评估', 'train / val', 'ink', 36)
    s += arrow(360, 1040, 360, 1180, 'line')
    s += route([(534, 275), (665, 275), (665, 1240), (570, 1240)], 'grad')
    s += text(360, 1350, '评估只读，不修改参数', 34, 'muted', 'middle')
    save('17-pretraining', '01-机制', svg(
        '一批数据，触发一次更新', '实跑 · batch16 · lr0.003 · 单线程CPU', s, 1400))

    s = legend(170)
    s += chart(run['history'], 100, 225, 540, 455, 6.5, run['steps'], [0, 2, 4, 6], [0, 500, 1000])
    first = run['history'][0]
    s += text(36, 840, f'训练：{first["train_loss"]:.3f} → {last["train_loss"]:.3f}', 36, 'output')
    s += text(36, 905, f'留出：{first["val_loss"]:.3f} → {last["val_loss"]:.3f}', 36, 'grad')
    s += line(36, 955, 684, 955)
    s += text(36, 1010, '第1000步：“小”行，第0项', 34)
    s += panel(36, 1050, 240, 110, '更新前', number(last['observed_parameter_before'], 7), 'param', 30)
    s += panel(444, 1050, 240, 110, '更新后', number(last['observed_parameter_after'], 7), 'param', 30)
    s += arrow(285, 1105, 435, 1105, 'param', 4)
    s += text(360, 1080, 'AdamW', 30, 'param', 'middle')
    s += text(36, 1230, f'裁剪后梯度：{number(last["observed_gradient_after_clip"], 7)}', 34, 'grad')
    s += text(36, 1300, f'实际更新：{last["observed_update"]:+.8f}', 34, 'param')
    save('17-pretraining', '02-验证', svg(
        '训练下降，留出却变差', '真实原始点 · 每50次更新评估 · 未平滑', s, 1360))


def figure18():
    d = read(18); run = d['greedy']
    fixed = panel(36, 145, 648, 60, f'同一组权重 θ，{len(run["steps"])}次前向都不变', color='param', size=34)
    s = fixed
    s += phase(0, text(36, 250, '起始前缀：' + run['prompt'], 34, 'input')
               + text(36, 290, 'T含BOS；绿色文字是已生成部分', 30, 'muted'))
    prefix = ''
    for i, step in enumerate(run['steps']):
        top = 325 + i * 135
        token = step['selected_token']; shown = 'EOS' if token == '<eos>' else token
        selected_p = next(item['probability'] for item in step['top_candidates']
                          if item['id'] == step['selected_id'])
        row = text(36, top + 36, f'T={len(step["input_ids"])}', 28, 'muted')
        row += rect(125, top, 430, 60, PALE['input'], 'input')
        row += text(132, top + 40, run['prompt'], 32, 'input')
        row += text(132 + len(run['prompt']) * 32, top + 40, prefix, 32, 'output')
        row += arrow(560, top + 30, 593, top + 30, 'output')
        row += circle(633, top + 30, 34, shown, 'output', 30 if shown == 'EOS' else 38)
        row += text(140, top + 108, 'p', 30, 'output')
        row += rect(190, top + 82, 195, 18, 'light', r=2)
        row += rect(190, top + 82, 195 * selected_p, 18, 'output', r=2)
        row += text(555, top + 108, number(selected_p), 30, 'output', 'end')
        if i > 0:
            row += route([(633, top - 71), (633, top - 18), (540, top - 18), (540, top - 3)], 'output', 2.5)
        if token != '<eos>':
            prefix += token
        else:
            row += text(360, 1338, 'EOS → 停止，不显示为文字', 34, 'output', 'middle')
        s += phase(i + 1, row)
    save('18-generation', '01-机制', svg(
        '每次追加，再用同一组权重', '真实轨迹 · pretrain · 贪心 · 最多新增8项', s, 1400))

    candidates = run['steps'][0]['top_candidates']
    winner, small = candidates[0], candidates[1:]
    remaining = 1 - winner['probability']
    unlisted = 1 - sum(item['probability'] for item in candidates)
    assert 0 < unlisted < remaining < 1
    # 局部图自带独立横轴；不把放大后的条长冒充整行概率的占比。
    limit = math.ceil(max(item['probability'] for item in small) / .00005) * .00005
    s = text(36, 175, '当前前缀：' + run['prompt'], 32, 'input')
    s += text(36, 246, winner['token'] + '：' + number(winner['probability']), 44, 'output', weight=600)
    s += rect(36, 281, 648, 40, 'light', r=3)
    s += rect(36, 281, 648 * winner['probability'], 40, 'output', r=3)
    s += text(36, 372, '其余候选合计 ≈ ' + number(remaining), 34)
    # 标出完整概率条末端的剩余部分，再引到放大区。
    s += rect(673, 269, 15, 64, 'none', 'grad', r=2)
    s += route([(681, 338), (681, 407), (625, 447)], 'grad', 2.5)
    s += rect(36, 447, 648, 495, 'light', 'line', r=12)
    s += text(60, 504, '局部放大：其余概率最高的4项', 32, 'ink', weight=600)
    for i, item in enumerate(small):
        top = 547 + i * 72
        s += text(65, top + 25, item['token'], 36, 'input')
        s += rect(145, top + 5, 350, 24, '#E2E7EC', r=2)
        s += rect(145, top + 5, 350 * item['probability'] / limit, 24, 'output', r=2)
        s += text(665, top + 27, number(item['probability']), 30, 'output', 'end')
    s += line(145, 851, 495, 851, 'muted')
    s += text(145, 895, '0', 30, 'muted', 'middle')
    s += text(495, 895, number(limit), 30, 'muted', 'middle')
    s += text(60, 932, '放大区横轴仍是实际概率', 30, 'muted')
    s += text(36, 1000, '未列候选合计 ≈ ' + number(unlisted), 32)
    s += line(36, 1042, 684, 1042)
    s += text(36, 1102, '同一权重，采样温度0.8', 34)
    for i, sample in enumerate(d['sampling']):
        s += text(36, 1165 + i * 70, f'seed={sample["seed"]}', 32, 'ink')
        s += text(290, 1165 + i * 70, sample['generated_text'], 34, 'output')
    s += text(360, 1320, '不同种子，也可能选到同一串字', 34, 'ink', 'middle')
    save('18-generation', '02-验证', svg(
        '小概率藏在哪里？放大看一次', '真实记录 · 放大区使用自己的横轴', s, 1380))


def figure19():
    d = read(19); ex = d['mask_example']; first = ex['prefix_len'] - 1
    s = phase(0, panel(36, 165, 345, 90, 'BOS + prompt', f'{ex["prefix_len"]}项', 'input', 34)
              + panel(393, 165, 185, 90, '答案', f'{len(ex["record"]["answer"])}项', 'output', 34)
              + panel(590, 165, 94, 90, 'EOS', '1项', 'output', 30))
    xs, cell = 40, 80
    input_top, target_top = 390, 650
    indices = list(range(13, 21))
    part = text(36, 325, '位置13–20：输入与标签错开一项', 34)
    for col, index in enumerate(indices):
        px = xs + col * cell
        part += text(px + 36, 365, index, 30, 'muted', 'middle')
        part += rect(px, input_top, 73, 70, PALE['input'], 'input', r=5)
        part += text(px + 36, input_top + 47, ex['x_tokens'][index], 34, 'input', 'middle')
        part += arrow(px + 36, 465, px + 36, 505)
        part += arrow(px + 36, 595, px + 36, target_top - 10, 'output')
        target = '：' if index < first else ex['y_tokens'][index]
        target = 'EOS' if target == '<eos>' else target
        part += rect(px, target_top, 73, 70, PALE['output'], 'output', r=5)
        part += text(px + 36, target_top + 47, target, 28 if target == 'EOS' else 34, 'output', 'middle')
    part += panel(40, 515, 633, 70, '完整前向 · 因果可见范围保留', color='ink', size=34)
    s += phase(1, part)
    mask = rect(xs, target_top, 73, 70, 'light', 'line', r=5)
    mask += text(xs + 36, target_top + 46, '忽略', 30, 'muted', 'middle')
    mask += rect(xs + cell - 3, target_top - 4, 79, 78, 'none', 'grad', r=6)
    mask += text(36, 815, f'首个答案：L−1 = {first}', 36, 'grad')
    mask += text(36, 875, 'prompt目标忽略，输入仍参与计算', 34, 'muted')
    s += phase(2, mask)
    loss_part = ''
    for col in range(1, 8):
        loss_part += arrow(xs + col * cell + 36, 725, xs + col * cell + 36, 745, 'grad', 2)
    loss_part += line(156, 750, 636, 750, 'grad', 2)
    loss_part += route([(636, 750), (702, 750), (702, 920), (360, 920), (360, 935)], 'grad', 2.5)
    loss_part += panel(200, 945, 320, 85, f'{ex["valid_count"]}个目标 → 平均损失', color='grad', size=32)
    s += phase(3, loss_part)
    gradient = route([(360, 1030), (360, 1075), (590, 1075), (590, 1130)], 'grad', 4)
    gradient += panel(420, 1140, 264, 80, '计分位置表示', '从冒号位置起', color='output', size=24)
    gradient += panel(36, 1140, 264, 80, 'prompt位置表示', color='input', size=30)
    gradient += arrow(410, 1180, 310, 1180, 'grad', 4)
    gradient += text(360, 1110, '经注意力上下文路径', 32, 'grad', 'middle')
    gradient += arrow(168, 1220, 168, 1270, 'grad')
    gradient += panel(36, 1280, 400, 70, 'Embedding参数可获梯度', color='param', size=32)
    s += phase(4, gradient)
    save('19-fine-tuning', '01-机制', svg(
        '答案从哪一个标签开始', '真实SFT样本 · −100只屏蔽目标，不删除输入', s, 1400))

    report = d['sft']; history = report['history']
    train_answers = report['answers']['sft_train']
    val_answers = report['answers']['sft_val']
    train_correct = sum(row['exact_match'] for row in train_answers)
    val_correct = sum(row['exact_match'] for row in val_answers)
    s = legend(175) + chart(history, 100, 220, 540, 300, 4.5, 300, [0, 2, 4], [0, 150, 300])
    s += text(36, 675, f'精确匹配：训练{train_correct}/{len(train_answers)}', 36, 'output')
    for i, row in enumerate(train_answers):
        px = 42 + (i % 8) * 80
        py = 705 + (i // 8) * 47
        color = 'output' if row['exact_match'] else 'grad'
        s += rect(px, py, 65, 39, PALE[color], color, r=5)
        s += text(px + 32, py + 30, '✓' if row['exact_match'] else '×', 32, color, 'middle')
    s += text(36, 900, f'留出{val_correct}/{len(val_answers)}：同一事实，另一问法', 36, 'grad')
    for i, row in enumerate(val_answers):
        px = 42 + i * 80
        color = 'output' if row['exact_match'] else 'grad'
        s += rect(px, 930, 65, 51, PALE[color], color, r=5)
        s += text(px + 32, 968, '✓' if row['exact_match'] else '×', 34, color, 'middle')
    failures = [row for row in val_answers if not row['exact_match']]
    detail = ('未匹配示例：' + failures[0]['actual'] if failures
              else '本次留出题全部匹配；仍需检验新问法')
    s += text(36, 1045, detail, 32, 'grad' if failures else 'output')
    s += line(36, 1095, 684, 1095)
    before = d['comparison']['pretrain']['outputs'][0]
    after = d['comparison']['sft']['outputs'][0]
    s += text(36, 1155, '续写：' + before['prompt'], 34, 'input')
    s += panel(36, 1190, 300, 110, '预训练', before['generated_text'], 'output', 32)
    s += panel(384, 1190, 300, 110, 'SFT', after['generated_text'], 'grad', 32)
    s += arrow(343, 1245, 376, 1245, 'line')
    save('19-fine-tuning', '02-验证', svg(
        '问答与续写，分别检查', '真实答案损失 · 相同贪心设置 · 最多新增8项', s, 1360))


def figure20():
    d = read(20)
    observed = read(17)['pretrain']['history'][-1]
    s = ''
    headings = [(175, '1  前向：输入变成分数', 'input'),
                (475, '2  反向：损失变成梯度', 'grad'),
                (775, '3  更新：优化器改变参数', 'param'),
                (1075, '4  生成：权重固定，输入变长', 'output')]
    for top, label, color in headings:
        s += text(36, top, label, 36, color)
        if top > 175:
            s += line(36, top - 60, 684, top - 60)
    for px, label, value, color in [(36, '编号', '[B,T]', 'input'),
                                   (270, '表示', '[B,T,64]', 'ink'),
                                   (504, '分数', '[B,T,79]', 'output')]:
        s += panel(px, 220, 180, 110, label, value, color, 30)
    s += arrow(222, 275, 264, 275, 'input') + arrow(456, 275, 498, 275, 'output')
    s += text(360, 385, '参数W参与计算，尚未修改', 34, 'param', 'middle')
    for px, label, value, color in [(36, '参数W', '未修改', 'param'),
                                   (270, '参数梯度', 'dL/dW', 'grad'),
                                   (504, '损失', 'L', 'grad')]:
        s += panel(px, 520, 180, 110, label, value or '无step', color, 32)
    s += arrow(498, 575, 456, 575, 'grad', 4) + arrow(264, 575, 222, 575, 'grad', 4)
    s += text(360, 685, '沿前向计算的依赖关系回传', 34, 'grad', 'middle')
    s += panel(36, 820, 210, 110, '旧参数', f'{observed["observed_parameter_before"]:.7f}', 'param', 32)
    s += panel(285, 820, 150, 110, 'AdamW', 'step()', 'param', 30)
    s += panel(474, 820, 210, 110, '新参数', f'{observed["observed_parameter_after"]:.7f}', 'param', 32)
    s += arrow(250, 875, 280, 875, 'param') + arrow(440, 875, 469, 875, 'param')
    s += text(360, 985, '梯度 + 历史状态 → 实际更新', 34, 'param', 'middle')
    for px, label, value, color in [(36, '已有前缀', 'T项', 'input'),
                                   (270, '相同W', '前向', 'param'),
                                   (504, '选一个字', '红', 'output')]:
        s += panel(px, 1120, 180, 110, label, value, color, 34)
    s += arrow(222, 1175, 264, 1175, 'input') + arrow(456, 1175, 498, 1175, 'output')
    s += route([(594, 1230), (594, 1295), (126, 1295), (126, 1235)], 'output', 4)
    s += text(360, 1355, '追加到输入，下次T+1', 34, 'output', 'middle')
    save('20-full-workflow', '01-机制', svg(
        '四种过程，改变的数不同', '前向 / 反向 / 更新 / 生成，分别追踪', s, 1400))

    vocab = json.loads((CODE / 'data/vocab.json').read_text(encoding='utf-8'))['tokens']
    s = text(36, 175, '① 只改未来位置8', 36)
    positions = [6, 7, 8, 9]
    for i, index in enumerate(positions):
        s += text(160 + i * 130, 225, index, 30, 'muted', 'middle')
    for row, ids in enumerate([d['ids'][0], d['variant_ids'][0]]):
        top = 255 + row * 140
        for i, index in enumerate(positions):
            px = 100 + i * 130
            color = 'grad' if index == d['future_change']['position'] else 'input'
            s += panel(px, top, 120, 75, vocab[ids[index]], color=color, size=40)
    s += arrow(420, 335, 420, 385, 'grad')
    future = d['future_change']
    s += text(360, 515, '比较logits的最大绝对差值', 32, 'ink', 'middle')
    s += panel(36, 535, 300, 120, '前缀0–7', fmt(future['prefix_max_difference']), 'output', 40)
    s += panel(384, 535, 300, 120, '后缀8–13', f'{future["suffix_max_difference"]:.6f}', 'input', 38)
    s += text(360, 720, '不可见未来变化，前缀保持相同', 34, 'ink', 'middle')
    s += line(36, 770, 684, 770)
    s += text(36, 835, '② 把首个答案也忽略', 36)
    ex = read(19)['mask_example']; boundary = d['mask_boundary']
    start = boundary['first_answer_index']
    targets = ex['y_tokens'][start:start + boundary['valid_before']]
    for row in range(2):
        top = 900 + 145 * row
        for i, target in enumerate(targets):
            px = 80 + i * 80
            ignored = row == 1 and i == 0
            color = 'muted' if ignored else 'output'
            s += rect(px, top, 71, 65, 'light' if ignored else PALE['output'], 'line' if ignored else 'output', r=5)
            shown = '×' if ignored else ('EOS' if target == '<eos>' else target)
            s += text(px + 35, top + 44, shown, 28 if shown == 'EOS' else 36, color, 'middle')
        loss_key = 'loss_before' if row == 0 else 'loss_after'
        count_key = 'valid_before' if row == 0 else 'valid_after'
        s += text(360, top + 114, f'{boundary[count_key]}个目标，loss={boundary[loss_key]:.6f}', 34, 'ink', 'middle')
    direction = '低' if boundary['loss_after'] < boundary['loss_before'] else '高'
    s += text(360, 1275, f'少算一道题，损失反而略{direction}', 36, 'grad', 'middle')
    s += text(360, 1340, '先检查标签，再解释曲线', 34, 'ink', 'middle')
    save('20-full-workflow', '02-验证', svg(
        '主动改条件，检查计算路径', '真实修改实验 · 随机参数 · seed=42', s, 1400))


if __name__ == '__main__':
    for build in (figure14, figure15, figure16, figure17, figure18, figure19, figure20):
        build()

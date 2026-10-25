"""补足正文的推导图与构造反例：梯度、形状、概率、位置与真实前向。

先生成SVG，再由现有静态渲染脚本转成PNG。只读课程记录与预训练权重，
不训练、不覆盖首次实验。每幅图使用同一套输入蓝、参数紫、结果青、梯度红。
"""
import json
import math

from figure_tools import (C, CODE, arrow, box, circle, line, lines, rect,
                          save, svg, text)


def gradient_fork():
    """沿用第05讲习题的数，展开同一隐藏值被使用两次的计算图。"""
    s = text(36, 174, 'y = h₁ − h₂ + h₁；目标仍为1', 34)
    s += circle(206, 276, 48, '1', 'input', 42)
    s += text(206, 216, '同一个 h₁', 32, 'input', 'middle')
    s += circle(552, 276, 48, '2', 'input', 42)
    s += text(552, 216, 'h₂', 32, 'input', 'middle')
    # 一个源分叉到两个使用位置；复制计算路径，不复制可训练参数。
    for x in (108, 314):
        s += arrow(206, 328, x, 399, 'input')
        s += box(x - 82, 414, 164, 76, '+ h₁', 'input', 36)
        s += arrow(x, 500, 330, 578, 'input')
    s += box(470, 414, 164, 76, '− h₂', 'ink', 36)
    s += arrow(552, 328, 552, 399, 'input')
    s += arrow(552, 500, 390, 578, 'line')
    s += circle(360, 615, 42, '0', 'output', 40)
    s += text(360, 704, '损失 L = (0−1)² = 1', 36, 'output', 'middle')
    s += line(36, 754, 684, 754)
    s += text(36, 816, '反向：从 y 收到 −2', 36, 'grad', weight=600)
    s += text(36, 872, '两个 +h₁ 的局部变化率都是1', 32, 'muted')
    for x in (150, 570):
        s += circle(x, 974, 46, '−2', 'grad', 38)
        s += arrow(x, 1028, 315 if x < 360 else 405, 1120, 'grad')
    s += text(150, 914, '第一条路径', 30, 'grad', 'middle')
    s += text(570, 914, '第二条路径', 30, 'grad', 'middle')
    s += circle(360, 1165, 44, '+', 'grad', 42)
    s += text(360, 1262, 'dL/dh₁ = −2 + (−2) = −4', 36, 'grad', 'middle')
    save('05-backpropagation', '03-同一数的两条梯度', svg(
        '一个数走两条路，梯度要相加', '沿用文末第二题；此图不更新参数', s, 1320))


def broadcast_mismatch():
    """构造四项全对的预测，画出一维目标导致的16项错误配对。"""
    values = [0, 1, 1, 0]
    errors = [[(prediction - target) ** 2 for target in values]
              for prediction in values]
    total = sum(sum(row) for row in errors)
    assert total == 8 and total / 16 == .5
    assert sum(errors[i][i] for i in range(4)) == 0
    s = text(36, 178, '列：一维目标被当成一行', 34, 'input')
    s += text(36, 232, '行：每行一个预测', 32, 'input')
    for column, target in enumerate(values):
        s += text(248 + column * 108, 278, target, 36, 'input', 'middle')
    for row, prediction in enumerate(values):
        y = 305 + row * 95
        s += text(36, y + 54, f'预测{row}={prediction}', 30, 'input')
        for column, error in enumerate(errors[row]):
            x = 198 + column * 108
            s += rect(x, y, 100, 84, '#D6E8E7' if error else 'light',
                      'input' if row == column else None, r=4)
            s += text(x + 50, y + 56, error, 38, 'ink', 'middle')
    s += text(36, 740, '每格 = 该行预测与该列目标的平方误差', 30)
    s += text(36, 798, '蓝框：本来应当一一配对的四格', 32, 'input')
    s += line(36, 840, 684, 840)
    s += text(36, 908, '错配后：8 ÷ 16 = 0.5', 38, 'output', weight=600)
    s += text(36, 980, '正确配对：0 ÷ 4 = 0', 38, 'output', weight=600)
    s += text(36, 1045, '预测没错，算损失时配错了题', 32, 'muted')
    save('06-training-loop', '03-预测全对损失却不为零', svg(
        '四道题，被误算成了十六道', '构造例：预测与正确目标都是 [0,1,1,0]', s, 1100))


def rotation_components():
    """将[2,1]的两条分量分别旋转，用同一坐标图逐项合成[1,2]。"""
    a, b, cosine, sine = 2., 1., .8, .6
    horizontal = (a * cosine, a * sine)
    vertical = (-b * sine, b * cosine)
    result = tuple(x + y for x, y in zip(horizontal, vertical))
    assert math.isclose(cosine ** 2 + sine ** 2, 1.)
    assert all(math.isclose(x, y) for x, y in zip(result, (1., 2.)))
    assert math.isclose(sum(x * x for x in result), a * a + b * b)
    s = text(360, 180, '[2,1] = [2,0] + [0,1]', 36, 'input', 'middle')
    s += text(360, 235, '两条分量，转过同一个角', 32, 'ink', 'middle')
    cx, cy, scale = 300, 625, 145
    point = lambda pair: (cx + scale * pair[0], cy - scale * pair[1])
    s += arrow(100, cy, 670, cy, 'muted', 2)
    s += arrow(cx, 700, cx, 275, 'muted', 2)
    s += text(670, 710, '横坐标', 29, 'muted', 'end')
    s += text(280, 288, '纵坐标', 29, 'muted', 'end')
    s += text(cx - 18, cy + 34, '0', 28, 'muted', 'end')
    for value in (1, 2):
        x, y = cx + scale * value, cy - scale * value
        s += line(x, cy - 5, x, cy + 5, 'muted', 2)
        s += text(x, cy + 40, value, 28, 'muted', 'middle')
        s += line(cx - 5, y, cx + 5, y, 'muted', 2)
        s += text(cx - 17, y + 10, value, 28, 'muted', 'end')
    hx, hy = point(horizontal)
    vx, vy = point(vertical)
    rx, ry = point(result)
    s += line(hx, hy, rx, ry, 'line', 2, '6 6')
    s += line(vx, vy, rx, ry, 'line', 2, '6 6')
    s += arrow(cx, cy, hx, hy, 'input', 4)
    s += arrow(cx, cy, vx, vy, 'ink', 4)
    s += arrow(cx, cy, rx, ry, 'output', 4)
    s += text(660, 424, '横向2转后', 30, 'input', 'end')
    s += text(660, 478, '[1.6,1.2]', 32, 'input', 'end')
    s += text(36, 490, '纵向1转后', 30, 'ink')
    s += text(36, 550, '[−0.6,0.8]', 32, 'ink')
    s += text(rx + 20, ry - 12, '[1,2]', 36, 'output', weight=600)
    s += text(36, 747, '虚线：把一条箭头接到另一条的末端', 30, 'muted')
    s += line(36, 780, 684, 780)
    s += text(36, 835, '横向2的贡献', 32, 'input', weight=600)
    s += text(36, 887, '[2×0.8, 2×0.6] = [1.6,1.2]', 32, 'input')
    s += text(36, 960, '纵向1的贡献', 32, 'ink', weight=600)
    s += text(36, 1012, '[−1×0.6, 1×0.8] = [−0.6,0.8]', 32)
    s += text(36, 1085, '合起来：[1.6−0.6, 1.2+0.8] = [1,2]', 32,
              'output', weight=600)
    save('13-rope', '04-旋转公式里的两条分量', svg(
        '旋转公式，来自两条箭头相加', '构造角：cosα=0.8，sinα=0.6', s, 1150))


def sequence_probability():
    """条件概率树和面积条共同表示0.5×0.25，不假设两步独立。"""
    first, second = .5, .25
    joint = first * second
    assert joint == .125
    s = box(228, 164, 264, 74, '已有前文', 'input', 36)
    s += arrow(292, 247, 182, 365, 'output')
    s += arrow(428, 247, 550, 365, 'line')
    s += text(180, 310, '0.5', 36, 'output', 'middle')
    s += text(550, 310, '0.5', 36, 'muted', 'middle')
    s += box(62, 378, 232, 74, '接“苹”', 'output', 36)
    s += box(430, 378, 232, 74, '接其他项', 'muted', 34)
    s += lines(545, 530, ['沿“苹”这一支', '再预测“果”'], 28, 44, 'output', 'middle')
    s += arrow(150, 460, 100, 602, 'output')
    s += arrow(218, 460, 342, 602, 'line')
    s += text(90, 575, '0.25', 36, 'output', 'middle')
    s += text(352, 575, '0.75', 36, 'muted', 'middle')
    s += box(25, 620, 170, 74, '接“果”', 'output', 36)
    s += box(260, 620, 220, 74, '接其他项', 'muted', 34)
    s += text(110, 760, '整条路径', 30, 'muted', 'middle')
    s += text(110, 810, '0.125', 42, 'output', 'middle', 600)
    s += text(370, 760, '另一条路径', 30, 'muted', 'middle')
    s += text(370, 810, '0.375', 42, 'muted', 'middle')
    s += line(36, 852, 684, 852)
    s += text(36, 912, '整段占一半里的四分之一', 36, weight=600)
    # 条带先分为一半，再将第一半分为1/4与3/4，宽度表达相乘关系。
    s += rect(36, 956, 648, 88, '#E8EDF3', r=0)
    s += rect(36, 956, 324, 88, '#C9DBEE', r=0)
    s += rect(36, 956, 81, 88, 'output', r=0)
    s += line(360, 943, 360, 1055, 'input', 3)
    s += text(36, 1107, '青色：0.5 × 0.25 = 0.125', 36, 'output')
    s += text(36, 1180, '−ln(0.125) = −ln(0.5) − ln(0.25)', 31)
    s += text(36, 1236, '整段负对数 = 两步负对数相加', 34, 'grad')
    save('09-training-targets', '03-接续概率的分流', svg(
        '一段接续的概率，沿路径相乘', '构造概率；第二步以已接上“苹”为条件', s, 1290))


def heads_motivation():
    """用可达线段说明固定V的一套比例限制，再画两个独立的配比。"""
    s = text(36, 176, '固定 V₀=[1,0]，V₁=[0,2]', 34)
    x0, y0, width, height = 128, 626, 465, 325
    px = lambda value: x0 + width * value
    py = lambda value: y0 - height * value / 2
    s += arrow(x0, y0, 642, y0, 'ink', 2)
    s += arrow(x0, y0, x0, 250, 'ink', 2)
    s += text(642, 708, '第1坐标', 30, 'ink', 'end')
    s += text(130, 253, '第2坐标', 30)
    s += line(px(0), py(2), px(1), py(0), 'input', 6)
    for a, b, label in ((0, 2, '[0,2]'), (1, 0, '[1,0]')):
        s += circle(px(a), py(b), 7, color='input')
        s += text(px(a) + (14 if a == 0 else -6), py(b) - 20 if a == 0 else y0 + 42,
                  label, 30, 'input', 'start' if a == 0 else 'end')
    s += line(px(.8), py(0), px(.8), py(1.6), 'param', 2, '6 6')
    s += circle(px(.8), py(.4), 9, color='input')
    s += text(px(.8) - 24, py(.4) + 52, '[0.8,0.4]', 30, 'input', 'end')
    s += circle(px(.8), py(1.6), 12, color='grad')
    s += text(px(.8) - 14, py(1.6) - 25, '目标 [0.8,1.6]', 32, 'grad', 'end')
    s += text(36, 747, '一套比例，只能落在蓝线上', 36, 'input', weight=600)
    s += text(36, 805, '要第1项为0.8，第2项只能为0.4', 32)
    s += line(36, 848, 684, 848)
    s += text(36, 911, '两组坐标，各自选择比例', 36, weight=600)
    for i, (a, result, color) in enumerate(((.8, .8, 'input'), (.2, 1.6, 'param'))):
        y = 956 + i * 182
        s += text(36, y + 35, f'头{i}', 34, color)
        s += rect(142, y, 330 * a, 62, color, r=0)
        s += rect(142 + 330 * a, y, 330 * (1-a), 62, '#DCE2E9', r=0)
        s += text(142, y + 111, f'比例 [{a:.1f},{1-a:.1f}]', 32, color)
        s += text(625, y + 43, result, 42, color, 'middle', 600)
        s += arrow(492, y + 31, 560, y + 31, color)
    s += text(360, 1347, '拼接得到 [0.8,1.6]', 40, 'output', 'middle', 600)
    save('12-multi-head-attention', '03-一套比例的限制', svg(
        '同一套比例，满足不了两项要求', '固定V的构造例子；实际各头还学习自己的投影', s, 1410))


def signed_color(value, maximum):
    """正负同时用色相、符号表达；深浅只表示相对数值大小。"""
    base = (24, 123, 121) if value >= 0 else (128, 86, 165)
    alpha = .08 + .72 * min(1., abs(value) / max(maximum, 1e-12))
    return '#' + ''.join(f'{round(255+(c-255)*alpha):02x}' for c in base)


def model_sections(data):
    """正文展开64个坐标和一个候选的64项乘加，全部取实际前向数据。"""
    trace, position = data['trace'], 7
    rows = [('查表后', trace['embedding'][0][position]),
            ('第二块后', trace['blocks'][1]['block_output'][0][position])]
    maximum = max(abs(v) for _, values in rows for v in values)
    token_id = trace['ids'][0][position]
    assert data['tokens'][token_id] == '欢'
    s = text(36, 175, f'固定位置7：“欢” / 编号{token_id}', 36, 'input', weight=600)
    s += text(36, 230, '同一份预训练权重；每格是一个坐标', 32)
    # 使用同一色阶；8×8仅是排版，不是把64维变成了二维表示。
    for panel, (title, values) in enumerate(rows):
        top = 296 + panel * 690
        s += text(36, top, title + ' · 64项', 36, weight=600)
        for coordinate, value in enumerate(values):
            x, y = 48 + coordinate % 8 * 78, top + 34 + coordinate // 8 * 61
            s += rect(x, y, 73, 56, signed_color(value, maximum), r=2)
            s += text(x + 36, y + 39, coordinate, 27, 'ink', 'middle')
        s += text(36, top + 586, '前4项：' + '，'.join(f'{v:+.3f}' for v in values[:4]), 31)
    s += text(36, 1631, f'同一色阶：−{maximum:.2f} 到 +{maximum:.2f}', 32, 'muted')
    s += text(36, 1690, '紫色为负，青色为正；格内数字是索引', 31)
    s += text(36, 1745, '8×8仅为排版，仍是一条64维向量', 31, 'muted')
    save('16-transformer', '04-一个位置的64项变化', svg(
        '还是同一个“欢”，64项数已改变', '真实预训练前向；两个面板使用共同色阶', s, 1800))

    normalized = trace['normalized'][0][position]
    red = data['tokens'].index('红')
    weights = data['output_weights'][red]
    products = [a*b for a, b in zip(normalized, weights)]
    stored = trace['logits'][0][position][red]
    assert abs(sum(products)-stored) < 1e-4
    s = text(36, 174, f'候选“红”：取输出矩阵第{red}行', 34, 'param')
    s += text(36, 230, '64个坐标分别乘权重，再全部相加', 32)
    # 用完整64项的有符号贡献图；零线之上为正，之下为负。
    maximum = max(abs(v) for v in products)
    left, right, zero, scale = 112, 668, 545, 165/maximum
    s += line(left, zero, right, zero, 'ink', 2)
    s += line(left, 366, left, zero + 25, 'muted', 2)
    for value in (0, maximum/2, maximum):
        y = zero-value*scale
        s += text(left-14, y+8, f'{value:.2f}', 24, 'muted', 'end')
        if value:
            s += line(left, y, right, y, 'line', 1)
    for coordinate, value in enumerate(products):
        x = left + coordinate * (right-left) / 64
        y = zero - max(0, value) * scale
        s += rect(x, y, 6.2, max(1, abs(value)*scale),
                  'output' if value >= 0 else 'param', r=0)
    s += text(36, 324, '一根柱 = 一项 hᵢ × W红,ᵢ', 32)
    for i in (0, 15, 31, 47, 63):
        s += text(left + (i+.5)*(right-left)/64, 595, i, 28, 'muted', 'middle')
    s += text(36, 655, '横轴：坐标0—63；纵向：有符号贡献', 30, 'muted')
    s += line(36, 698, 684, 698)
    s += text(36, 761, '只展开第0项', 36, weight=600)
    s += text(36, 825, f'h₀ = {normalized[0]:+.6f}', 38, 'input')
    s += text(36, 885, f'W红,₀ = {weights[0]:+.6f}', 38, 'param')
    s += text(36, 945, f'乘积 = {products[0]:+.6f}', 38, 'output')
    s += text(36, 1035, f'64项之和 = {stored:.6f}', 42, 'output', weight=600)
    s += text(36, 1100, '这还是分数；79个分数一起做Softmax', 31)
    scores = trace['logits'][0][position]
    maximum_score = max(scores)
    probability = math.exp(stored - maximum_score) / sum(
        math.exp(score - maximum_score) for score in scores)
    s += text(36, 1162, f'才得到“红”的概率 ≈ {probability:.6f}', 34, 'output')
    save('16-transformer', '05-一个候选的64项乘加', svg(
        '“红”的高分，来自64项乘加', '真实数值；正贡献在零线上方，负贡献在下方', s, 1220))


def order_comparison():
    """回到第13讲开头的换序题，位置固定，只交换两组K及对应V。"""
    import torch
    from tiny_lm.rope import apply_rope

    # 查询内容不变；最后一个查询位于位置2，三个键都属于可见范围。
    q = torch.tensor([[[[1., 0.]] * 3]], dtype=torch.float64)
    k = torch.tensor([[[[1., 0.], [0., 1.], [1., 1.]]]], dtype=torch.float64)
    v = torch.tensor([[1., 0.], [0., 2.], [1., 2.]], dtype=torch.float64)
    positions, order = torch.arange(3), torch.tensor([1, 0, 2])
    outputs = []
    for use_rope in (False, True):
        pair = []
        for swapped in (False, True):
            keys, values = (k[:, :, order], v[order]) if swapped else (k, v)
            rq, rk = apply_rope(q, keys, positions) if use_rope else (q, keys)
            weights = ((rq @ rk.transpose(-2, -1))[0, 0, -1] / math.sqrt(2)).softmax(-1)
            pair.append((weights @ values).tolist())
        outputs.append(pair)
    assert torch.allclose(torch.tensor(outputs[0][0]), torch.tensor(outputs[0][1]))
    assert not torch.allclose(torch.tensor(outputs[1][0]), torch.tensor(outputs[1][1]))

    s = text(36, 174, '上：原序；下：前两项内容交换', 34)
    contents = [('A', '[1,0]', '[1,0]', 'input'),
                ('B', '[0,1]', '[0,2]', 'param'),
                ('C', '[1,1]', '[1,2]', 'output')]
    for i in range(3):
        center = 138 + 216 * i
        s += text(center, 230, f'位置{i}', 32, 'muted', 'middle')
        s += text(center, 274, f'{i}弧度', 30, 'muted', 'middle')
    for row, order_values in enumerate(((0, 1, 2), (1, 0, 2))):
        y = 300 + row * 210
        for position, item in enumerate(order_values):
            name, key, value, color = contents[item]
            left = 36 + 216 * position
            s += rect(left, y, 200, 140, '#FFFFFF', color)
            s += text(left + 100, y + 38, f'内容{name}', 32, color, 'middle', 600)
            s += text(left + 100, y + 83, 'K ' + key, 30, color, 'middle')
            s += text(left + 100, y + 123, 'V ' + value, 30, color, 'middle')
    # 交叉线表示两组内容换位；原来各位置的角度仍保留在各自的格子。
    s += arrow(138, 450, 354, 500, 'input')
    s += arrow(354, 450, 138, 500, 'param')
    s += arrow(570, 450, 570, 500, 'output')
    s += text(36, 708, 'K、V一起换位，位置角度不搬家', 32)
    s += line(36, 747, 684, 747)
    for index, title in enumerate(('不加位置旋转', '按所在位置旋转Q、K')):
        y = 809 + index * 230
        color = 'muted' if index == 0 else 'output'
        s += text(36, y, title, 36, 'ink', weight=600)
        for row, label in enumerate(('原序', '换序')):
            value = outputs[index][row]
            s += text(36, y + 63 + row * 58, label, 32, color)
            s += text(210, y + 63 + row * 58,
                      f'[{value[0]:.4f}, {value[1]:.4f}]', 38, color)
        if index == 0:
            s += text(36, y + 177, '两次汇总仍然相同', 31, 'muted')
        else:
            s += text(36, y + 177, '相同内容换了位置，汇总也变了', 31, 'output')
    save('13-rope', '03-换序后再算一次', svg(
        '交换前文，旋转后不再相同', '构造例子；最后一个查询仍在位置2', s, 1280))


def context_comparison(expected_digest):
    """同一预训练权重只改一个人名，观察同一个“欢”的表示与候选分布。"""
    import hashlib
    import torch
    from tiny_lm.checkpoint import load_checkpoint
    from tiny_lm.trace import parameter_digest

    checkpoint = CODE / 'artifacts/first_run/pretrain.pt'
    checkpoint_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    model, tokenizer, metadata = load_checkpoint(checkpoint)
    assert metadata['stage'] == 'pretrain'
    assert parameter_digest(model) == expected_digest
    results = []
    for prefix in ('早上，小丁喜欢', '早上，小周喜欢'):
        ids = torch.tensor([tokenizer.encode(prefix, add_bos=True)])
        with torch.no_grad():
            logits, trace = model(ids, return_trace=True)
        results.append({
            'prefix': prefix,
            'embedding': trace['embedding'][0, -1].tolist(),
            'block': trace['blocks'][-1]['block_output'][0, -1].tolist(),
            'probabilities': {c: float(logits[0, -1].softmax(-1)[tokenizer.stoi[c]])
                              for c in ('红', '黄')},
        })
    assert results[0]['embedding'] == results[1]['embedding']
    assert results[0]['block'] != results[1]['block']
    assert results[0]['probabilities']['红'] > .99
    assert results[1]['probabilities']['黄'] > .99
    # 制图只有只读前向，没有反向和更新；原权重的内存值、文件字节均保持原样。
    assert parameter_digest(model) == expected_digest
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == checkpoint_sha

    s = text(36, 174, '只把“丁”换成“周”', 36, 'input', weight=600)
    for i, result in enumerate(results):
        s += text(36 + 348 * i, 239, result['prefix'], 32, 'input')
        s += arrow(186 + 348 * i, 310, 186 + 348 * i, 349, 'input')
    s += text(360, 296, f'最后一个输入都是“欢” / ID{tokenizer.stoi["欢"]}', 32, 'input', 'middle')
    s += rect(36, 362, 648, 111, '#F1F6FB', 'input')
    s += text(360, 405, '查表：取出完全相同的一行', 34, 'input', 'middle')
    first_four = '，'.join(f'{v:+.3f}' for v in results[0]['embedding'][:4])
    s += text(360, 451, '前4项：' + first_four, 29, 'input', 'middle')
    s += text(36, 534, '经过两个模型块后', 36, weight=600)
    maximum = max(abs(v) for result in results for v in result['block'])
    for panel, result in enumerate(results):
        for coordinate, value in enumerate(result['block']):
            x = 48 + panel * 348 + coordinate % 8 * 29
            y = 572 + coordinate // 8 * 29
            s += rect(x, y, 27, 27, signed_color(value, maximum), r=1)
    for i, name in enumerate(('小丁前文', '小周前文')):
        s += text(164 + 348 * i, 840, name, 30, 'input', 'middle')
    s += text(36, 884, '每边64格；共用色阶 ±' + f'{maximum:.2f}', 31, 'muted')
    s += text(36, 928, '青色为正，紫色为负；仍是同一输入位置', 30, 'muted')
    s += line(36, 970, 684, 970)
    s += text(36, 1016, '最后RMSNorm → 词表投影 → Softmax', 32, weight=600)
    for panel, result in enumerate(results):
        left = 36 + panel * 348
        for row, candidate in enumerate(('红', '黄')):
            y = 1083 + row * 140
            value = result['probabilities'][candidate]
            s += text(left, y, f'候选“{candidate}”', 31)
            s += rect(left, y + 20, 280, 20, '#EEF1F5', r=0)
            s += rect(left, y + 20, 280 * value, 20, 'output', r=0)
            s += text(left, y + 88, f'{100 * value:.4f}%', 36, 'output', weight=600)
    s += text(36, 1380, '同一份参数，前文改变了下一字分布', 32, 'output')
    save('16-transformer', '06-同一个欢不同的前文', svg(
        '同一个“欢”，两种前文', '真实预训练权重；两次都只做前向', s, 1440))


def transfer_comparison():
    """从实际重训记录画出数据、参数和输出之间的因果关系。"""
    record = json.loads((CODE / 'artifacts/transfer_check.json').read_text(encoding='utf-8'))
    case = record['checks'][0]
    assert case['stage'] == 'pretrain'
    assert all(item['after'] == item['expected'] and item['stop_reason'] == 'eos'
               for item in record['checks'])
    s = text(36, 182, '两次都输入：' + case['prompt'], 34, 'input')
    s += box(36, 244, 282, 96, '原预训练权重', 'param', 32)
    s += arrow(330, 292, 379, 292, 'param')
    s += text(406, 306, case['before'], 36, 'output', weight=600)
    s += text(36, 394, '只改数据，已保存的参数不会跟着变', 32, 'muted')
    s += line(36, 438, 684, 438)
    s += text(36, 500, '交换后的训练事实', 36, 'input', weight=600)
    for index, (name, color, fruit) in enumerate(record['facts_after']):
        s += text(36, 562 + index * 52, f'{name} → {color}的{fruit}', 34, 'input')
    s += arrow(178, 636, 178, 689, 'input')
    s += box(36, 705, 282, 96, '重新训练', 'grad', 36)
    s += lines(365, 742, ['新目标产生梯度', '优化器调整参数'], 30, 48, 'grad')
    s += arrow(178, 815, 178, 867, 'grad')
    s += box(36, 885, 282, 96, '新预训练权重', 'param', 32)
    s += arrow(330, 933, 379, 933, 'param')
    s += text(406, 947, case['after'], 36, 'output', weight=600)
    s += text(36, 1040, '再用开头同一句输入，接续才改变', 32, 'output')
    s += line(36, 1080, 684, 1080)
    s += text(36, 1140, f"词表仍为{record['vocab_size']}项，参数仍为{record['parameter_count']:,}个", 32)
    s += text(36, 1196, '改变的是参数的数值，网络尺寸不变', 32, 'muted')
    save('20-full-workflow', '04-换一份事实', svg(
        '改了数据，旧答案不会自动变', '实际实验：同一初值，重做1000步预训练', s, 1250))


def main():
    from model_xray import load_data
    gradient_fork()
    broadcast_mismatch()
    rotation_components()
    sequence_probability()
    heads_motivation()
    # 图与解剖台共用只读数据入口，不另存可失效的中间JSON副本。
    data = load_data()
    model_sections(data)
    order_comparison()
    context_comparison(data['parameter_sha256'])
    transfer_comparison()


if __name__ == '__main__':
    main()

"""第 02—06 讲的机制图源；只读取已保存的逐讲 trace，不运行训练。"""
from figure_tools import *


ANIMATION_PHASES = {
    '04-gradients/01-机制': {
        0: '输入与权重进入乘法', 1: '得到预测',
        2: '预测减去目标', 3: '差值平方得到损失',
    },
    '04-gradients/02-验证': {
        0: '损失曲线与当前参数点', 1: '当前位置的导数切线',
        2: '学习率决定参数移动距离', 3: '重新计算小步更新后的损失',
        4: '对照较大学习率的新落点与损失',
    },
    '05-backpropagation/01-机制': {
        0: '固定参数，算完选中路径的前向数值', 1: '标出各段局部变化率',
        2: '逆序相乘，得到选中权重梯度',
        3: '全网络梯度就绪后，展示选中权重的更新',
    },
    '05-backpropagation/02-验证': {
        0: '全部参数梯度保持就绪', 1: '统一应用同一学习率',
        2: '全部新参数写回', 3: '用新参数重新前向并计算损失',
    },
}


def path(points, color='line', width=3, dash=None, head=False):
    value = ' '.join(('M' if i == 0 else 'L') + f'{x:.2f} {y:.2f}'
                     for i, (x, y) in enumerate(points))
    return (f'<path d="{value}" fill="none" stroke="{C.get(color, color)}" '
            f'stroke-width="{width}" stroke-linejoin="round" '
            + (f'stroke-dasharray="{dash}" ' if dash else '')
            + (f'marker-end="url(#a-{color})" ' if head else '') + '/>')


def dot(x, y, color='output', radius=8, hollow=False):
    return (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" '
            f'fill="{"white" if hollow else C[color]}" '
            f'stroke="{C[color]}" stroke-width="3"/>')


def vector(x, y, values, color='input', cell_w=108, cell_h=74, size=36):
    tint = {'input': '#EDF3FA', 'param': '#F3EEF8',
            'output': '#EBF5F3', 'grad': '#FAEFF3'}.get(color, 'light')
    return matrix(x, y, [values], cell_w=cell_w, cell_h=cell_h,
                  colors=[[tint] * len(values)], fmt=fmt, size=size)


def values_matrix(x, y, values, color='param', cell_w=110, cell_h=74, size=34):
    tint = {'input': '#EDF3FA', 'param': '#F3EEF8',
            'output': '#EBF5F3', 'grad': '#FAEFF3'}.get(color, 'light')
    return matrix(x, y, values, cell_w=cell_w, cell_h=cell_h,
                  colors=[[tint] * len(row) for row in values], fmt=fmt, size=size)


def number_box(x, y, w, h, label, value, color='ink'):
    return (rect(x, y, w, h, '#FFFFFF', color)
            + text(x + w / 2, y + 38, label, 30, color, 'middle')
            + text(x + w / 2, y + h - 20, value, 40, color, 'middle', 600))


def axis(x0, y0, x1, y1, xlabel, ylabel, ylabel_y=None, ylabel_anchor='start'):
    return (arrow(x0, y0, x1, y0, 'ink', 2)
            + arrow(x0, y0, x0, y1, 'ink', 2)
            + text(x1, y0 - 18, xlabel, 32, 'ink', 'end')
            + text(x0 - 8, y1 - 22 if ylabel_y is None else ylabel_y,
                   ylabel, 32, 'ink', ylabel_anchor))


def lesson02():
    d = read(2)
    s = ''
    for i, left in enumerate((56, 396)):
        center = left + 108
        s += text(center, 176, f'输出 y{i + 1}', 36, 'output', 'middle', 600)
        s += text(left, 232, '同一输入 x', 32, 'input')
        s += vector(left, 252, d['x'])
        s += text(center, 372, '×  对应位置相乘', 30, 'muted', 'middle')
        s += text(left, 422, f'W 第 {i + 1} 行', 32, 'param')
        s += vector(left, 442, d['W'][i], 'param')
        for j in range(len(d['x'])):
            px = left + 52 + j * 108
            s += arrow(px, 528, px, 588, 'line')
        s += text(left, 630, '乘积', 32)
        s += vector(left, 650, d['products'][i], 'ink')
        total = sum(d['products'][i])
        for j in range(len(d['x'])):
            s += arrow(left + 52 + j * 108, 734, center, 804, 'line')
        s += circle(center, 850, 46, fmt(total), 'ink', 38)
        s += text(center, 930, f'+ b{i + 1} = +({fmt(d["b"][i])})', 32,
                  'param', 'middle')
        s += arrow(center, 950, center, 1008, 'param')
        s += circle(center, 1062, 52, fmt(d['output'][i]), 'output', 42)
    s += line(360, 185, 360, 1144, 'line', 1)
    save('02-vectors-and-matrices', '01-机制',
         svg('一行权重，算出一项输出', '两组参数读取同一份输入，分别求和', s, 1190))

    s = text(36, 180, 'X：样本按行放', 36, 'input', weight=600)
    for j in range(len(d['x'])):
        s += text(235 + j * 130, 232, f'输入 {j + 1}', 32, 'input', 'middle')
    for i in range(len(d['batch'])):
        s += text(36, 292 + i * 82, f'样本 {i + 1}', 32, 'input')
    s += values_matrix(170, 254, d['batch'], 'input', 130, 82, 38)
    s += text(490, 294, '[B,D]', 34, 'input')
    s += text(36, 480, 'W.T：每列对应一项输出', 36, 'param', weight=600)
    wt = [list(row) for row in zip(*d['W'])]
    for j in range(len(wt[0])):
        s += text(235 + j * 130, 532, f'输出 {j + 1}', 32, 'param', 'middle')
    for i in range(len(wt)):
        s += text(36, 592 + i * 82, f'输入 {i + 1}', 32, 'input')
    s += values_matrix(170, 554, wt, 'param', 130, 82, 38)
    s += text(490, 592, '[D,O]', 34, 'param')
    s += text(36, 798, 'Y = X @ W.T + b', 38, 'ink', weight=600)
    s += text(36, 850, '同一组 b 加到每一行', 32, 'param')
    s += vector(450, 800, d['b'], 'param', 102, 74)
    for j in range(len(d['output'])):
        s += text(235 + j * 130, 948, f'输出 {j + 1}', 32, 'output', 'middle')
    for i in range(len(d['batch'])):
        s += text(36, 1008 + i * 82, f'样本 {i + 1}', 32, 'input')
    s += values_matrix(170, 970, d['batch_output'], 'output', 130, 82, 38)
    s += text(490, 1010, '[B,O]', 34, 'output')
    s += text(36, 1222, 'B：样本数   D：输入项数   O：输出项数', 30, 'muted')
    save('02-vectors-and-matrices', '02-验证',
         svg('多放一份样本，参数仍共用', '行列的位置与轴名一起读', s, 1280))


def lesson03():
    d = read(3)
    row = d['rows'][1]
    x1, x2 = row['x']
    z = [x1 - x2, x2 - x1]
    s = text(190, 180, 'x₁', 34, 'input', 'middle')
    s += text(530, 180, 'x₂', 34, 'input', 'middle')
    s += circle(190, 245, 48, x1, 'input', 40)
    s += circle(530, 245, 48, x2, 'input', 40)
    for target in (180, 540):
        s += arrow(190, 295, target, 390, 'line')
        s += arrow(530, 295, target, 390, 'line')
    s += box(36, 402, 288, 90, f'x₁−x₂ = {fmt(z[0])}', 'ink', 34)
    s += box(396, 402, 288, 90, f'x₂−x₁ = {fmt(z[1])}', 'ink', 34)
    for i, cx in enumerate((180, 540)):
        s += arrow(cx, 502, cx, 565, 'line')
        s += box(cx - 120, 578, 240, 82, 'ReLU', 'ink', 36)
        s += arrow(cx, 674, cx, 740, 'line')
        s += circle(cx, 797, 50, row['h'][i], 'output', 42)
        s += text(cx, 890, f'h{i + 1}', 34, 'output', 'middle')
        s += arrow(cx, 920, 360, 1010, 'line')
    s += circle(360, 1062, 50, row['y'], 'output', 42)
    s += text(360, 1160, 'y = h₁ + h₂', 38, 'output', 'middle')
    save('03-nonlinearity', '01-机制',
         svg('先截去负半边，再把两支相加', '手工构造；每个节点保留前向数值', s, 1230))

    s = text(36, 180, '四条输入，四个目标', 36, weight=600)
    sx, sy = lambda v: 170 + 390 * v, lambda v: 574 - 300 * v
    s += axis(120, 620, 656, 214, 'x₁', 'x₂', ylabel_y=238, ylabel_anchor='end')
    for value in sorted(set(r['x'][0] for r in d['rows'])):
        s += text(sx(value), 668, value, 32, anchor='middle')
        s += text(92, sy(value) + 10, value, 32, anchor='end')
        s += line(sx(value), 250, sx(value), 620, 'line', 1, '5 6')
        s += line(120, sy(value), 620, sy(value), 'line', 1, '5 6')
    for r in d['rows']:
        px, py = sx(r['x'][0]), sy(r['x'][1])
        fill = C['output'] if r['target'] else '#FFFFFF'
        s += f'<circle cx="{px}" cy="{py}" r="28" fill="{fill}" stroke="{C["output"]}" stroke-width="3"/>'
        s += text(px, py + 12, r['target'], 34,
                  '#FFFFFF' if r['target'] else 'output', 'middle', 600)
    s += text(650, 714, '圆点内是目标，网络输出与之相同', 30, 'muted', 'end')
    s += text(36, 792, '两条分支怎样合成 |d|', 36, weight=600)
    s += line(280, 830, 326, 830, 'param', 4, '10 5')
    s += text(340, 840, 'h₁', 32, 'param')
    s += line(430, 830, 476, 830, 'input', 4, '3 7')
    s += text(490, 840, 'h₂', 32, 'input')
    fx = lambda v: 360 + v * 240
    fy = lambda v: 1200 - v * 280
    s += axis(88, 1200, 670, 886, '差值 d', '输出')
    values = sorted({r['x'][0] - r['x'][1] for r in d['rows']})
    for value in values:
        s += text(fx(value), 1252, value, 32, anchor='middle')
    s += text(62, fy(1) + 10, max(r['y'] for r in d['rows']), 32, anchor='end')
    dense = [values[0] + (values[-1] - values[0]) * i / 80 for i in range(81)]
    s += path([(fx(v), fy(abs(v))) for v in dense], 'output', 11)
    s += path([(fx(v), fy(max(0, v))) for v in dense], 'param', 4, '10 5')
    s += path([(fx(v), fy(max(0, -v))) for v in dense], 'input', 4, '3 7')
    s += line(100, 1320, 146, 1320, 'output', 8)
    s += text(162, 1330, 'h₁+h₂ = |d|', 34, 'output')
    s += text(430, 1330, 'd = x₁−x₂', 32)
    save('03-nonlinearity', '02-验证',
         svg('两个分支，满足四个目标', '上图看两项输入，下图看它们的差值', s, 1380))


def lesson04():
    d = read(4)
    error = d['prediction'] - d['target']
    s = phase(0, number_box(50, 200, 230, 116, '输入 x', fmt(d['x']), 'input')
              + number_box(440, 200, 230, 116, '权重 w', fmt(d['w']), 'param')
              + arrow(165, 332, 330, 430, 'input')
              + arrow(555, 332, 390, 430, 'param'))
    s += phase(1, circle(360, 466, 45, '×', 'ink', 38)
               + arrow(360, 520, 360, 580, 'line')
               + number_box(245, 594, 230, 116, '预测 x×w', fmt(d['prediction']), 'output'))
    s += phase(2, number_box(36, 790, 220, 116, '差值', fmt(error), 'ink')
               + number_box(464, 790, 220, 116, '目标', fmt(d['target']), 'ink')
               + arrow(360, 725, 360, 800, 'line')
               + circle(360, 848, 38, '−', 'ink', 38)
               + arrow(450, 848, 410, 848, 'line')
               + arrow(310, 848, 270, 848, 'line'))
    s += phase(3, arrow(146, 922, 330, 1010, 'line')
               + text(100, 1000, '平方', 34)
               + number_box(245, 1026, 230, 116, '损失 L', fmt(d['loss']), 'output'))
    save('04-gradients', '01-机制',
         svg('先有目标，才能算损失', '输入固定；观察权重怎样改变预测', s, 1220))

    px = lambda w: 100 + w / 6.2 * 550
    py = lambda loss: 820 - loss / 40 * 580
    s = axis(100, 820, 670, 220, 'w', '损失 L')
    for loss in (0, 16, 32, 40):
        s += line(100, py(loss), 650, py(loss), 'line', 1, '5 6')
        s += text(80, py(loss) + 10, loss, 30, anchor='end')
    for w in (0, 1, 3, 6):
        s += line(px(w), 820, px(w), 828, 'ink', 2)
        s += text(px(w), 872, w, 32, anchor='middle')
    points = [(px(r['w']), py(r['loss'])) for r in d['curve'] if 0 <= r['w'] <= 6.2]
    s += phase(0, path(points, 'ink', 4)
               + dot(px(d['w']), py(d['loss']), 'input', 9)
               + text(260, 550, f'w={fmt(d["w"])}，L={fmt(d["loss"])}', 32, 'input')
               + line(px(d['w']) + 12, py(d['loss']) - 8, 250, 560, 'input', 2)
               + text(360, 184, f'L(w) = ({fmt(d["x"])}w−{fmt(d["target"])})²', 38, anchor='middle'))
    tangent = [(w, d['loss'] + d['gradient'] * (w - d['w'])) for w in (.32, 1.9)]
    s += phase(1, path([(px(w), py(l)) for w, l in tangent], 'grad', 4, '9 6')
               + text(130, 330, f'dL/dw = {fmt(d["gradient"])}', 36, 'grad')
               + text(130, 380, '当前位置的切线', 32, 'grad'))
    good, bad = d['updates']
    s += phase(2, line(px(d['w']), 900, px(d['w']), 936, 'input', 2)
               + arrow(px(d['w']), 925, px(good['w']), 925, 'output', 4)
               + text(36, 994, f'η={fmt(good["lr"])} → w={fmt(good["w"])}', 36, 'output'))
    s += phase(3, line(px(good['w']), py(good['loss']), px(good['w']), 910, 'output', 2, '5 5')
               + dot(px(good['w']), py(good['loss']), 'output', 10)
               + text(270, 660, f'L={fmt(good["loss"])}', 36, 'output')
               + line(px(good['w']) + 10, py(good['loss']) - 10, 260, 670, 'output', 2))
    s += phase(4, line(px(d['w']), 1080, px(d['w']), 1114, 'input', 2)
               + arrow(px(d['w']), 1100, px(bad['w']), 1100, 'grad', 4)
               + line(px(bad['w']), py(bad['loss']), px(bad['w']), 1085, 'grad', 2, '5 5')
               + dot(px(bad['w']), py(bad['loss']), 'grad', 10)
               + text(420, 284, f'w={fmt(bad["w"])}', 34, 'grad')
               + text(420, 330, f'L={fmt(bad["loss"])}', 34, 'grad')
               + text(36, 1172, f'η={fmt(bad["lr"])} → w={fmt(bad["w"])}', 36, 'grad')
               + text(36, 1240, '同一局部方向，步长不同，落点不同', 32, 'muted'))
    save('04-gradients', '02-验证',
         svg('方向相同，步长会改变结果', '横轴是参数；箭头长度由学习率决定', s, 1300))


def lesson05():
    d = read(5)
    p, cache, g = d['params'], d['cache'], d['gradients']
    selected = p['W1'][0][1]
    other = cache['z'][0] - d['x'][1] * selected
    out_other = cache['h'][1] * p['W2'][0][1] + p['b2'][0]
    dy = 2 * (d['prediction'] - d['target'])
    # 初次出场只画已经讲过的前向；梯度与更新留到后面的图。
    first = box(176, 154, 368, 74,
                '输入 [' + ', '.join(fmt(value) for value in d['x']) + ']', 'input', 34)
    first += arrow(288, 240, 186, 292, 'input')
    first += arrow(432, 240, 534, 292, 'input')
    for hidden, left in ((0, 36), (1, 384)):
        weights = p['W1'][hidden]
        first += text(left + 150, 342,
                      f'权重 [{fmt(weights[0])}, {fmt(weights[1])}]',
                      32, 'param', 'middle')
        calculation = (f'{fmt(d["x"][0])}×{fmt(weights[0])}'
                       f'+{fmt(d["x"][1])}×{fmt(weights[1])}'
                       f'+{fmt(p["b1"][hidden])}={fmt(cache["z"][hidden])}')
        first += text(left + 150, 398, calculation, 30, 'ink', 'middle')
        first += box(left, 438, 300, 76,
                     f'ReLU({fmt(cache["z"][hidden])}) = {fmt(cache["h"][hidden])}',
                     'output', 32)
        first += text(left + 150, 568,
                      f'h{("₁", "₂")[hidden]} = {fmt(cache["h"][hidden])}',
                      36, 'output', 'middle')
        first += arrow(left + 150, 590, 304 if hidden == 0 else 416,
                       688, 'output')
        first += text(left + 100 if hidden == 0 else left + 200, 644,
                      f'×({fmt(p["W2"][0][hidden])})', 32, 'param', 'middle')
    first += circle(360, 720, 48, fmt(d['prediction']), 'output', 40)
    first += text(360, 820, f'两路相加，再加输出偏置{fmt(p["b2"][0])}',
                  32, 'ink', 'middle')
    first += arrow(360, 842, 360, 904, 'line')
    first += text(490, 894, f'(y−{fmt(d["target"])})²', 32, 'ink')
    first += number_box(220, 925, 280, 112, '损失 L', fmt(d['loss']), 'output')
    save('05-backpropagation', '04-先把前向算完',
         svg('沿隐藏层算出输出 −1、损失 4', '固定输入与参数，沿箭头往下算', first, 1090))
    forward = (text(156, 174, 'W1[0][1]', 34, 'param', 'middle')
               + box(36, 198, 240, 84, fmt(selected), 'param', 40)
               + text(540, 174, '输入 x₂', 34, 'input', 'middle')
               + box(430, 198, 220, 84, fmt(d['x'][1]), 'input', 40)
               + arrow(156, 298, 330, 340, 'param')
               + arrow(540, 298, 390, 340, 'input')
               + circle(360, 354, 30, '×', 'ink', 32)
               + arrow(360, 396, 360, 432, 'line')
               + text(440, 434, fmt(selected * d['x'][1]), 34)
               + box(36, 438, 180, 82, f'其余项 {fmt(other)}', 'ink', 30)
               + arrow(230, 480, 300, 480, 'line')
               + text(270, 464, '+', 30)
               + circle(360, 480, 48, fmt(cache['z'][0]), 'ink', 40)
               + text(422, 492, 'z₁', 34, 'ink')
               + arrow(360, 542, 360, 578, 'line')
               + box(260, 594, 200, 76, 'ReLU', 'ink', 34)
               + arrow(360, 686, 360, 714, 'line')
               + circle(360, 766, 48, fmt(cache['h'][0]), 'output', 40)
               + text(280, 776, 'h₁', 34, 'output', 'end')
               + arrow(360, 828, 360, 890, 'line')
               + text(280, 867, f'权重 {fmt(p["W2"][0][0])}', 30, 'param', 'end')
               + box(36, 900, 180, 82, f'−h₂={fmt(out_other)}', 'ink', 30)
               + arrow(230, 941, 300, 941, 'line')
               + text(270, 925, '+', 30)
               + circle(360, 941, 48, fmt(d['prediction']), 'output', 40)
               + text(422, 951, 'y', 34, 'output')
               + arrow(360, 1004, 360, 1064, 'line')
               + text(280, 1050, f'(y−{fmt(d["target"])})²', 30, 'ink', 'end')
               + number_box(260, 1080, 200, 112, '损失 L', fmt(d['loss']), 'output'))
    s = phase(0, forward)
    s += phase(1, text(397, 1050, f'2(y−{fmt(d["target"])})', 30, 'grad')
               + text(397, 867, f'×{fmt(p["W2"][0][0])}', 32, 'grad')
               + text(397, 716, '×1', 32, 'grad')
               + text(284, 315, f'×{fmt(d["x"][1])}', 32, 'grad'))
    s += phase(2, arrow(530, 1128, 530, 966, 'grad', 4)
               + text(555, 1050, fmt(dy), 36, 'grad')
               + arrow(530, 917, 530, 790, 'grad', 4)
               + text(555, 867, fmt(dy * p['W2'][0][0]), 36, 'grad')
               + arrow(530, 744, 530, 505, 'grad', 4)
               + text(555, 645, fmt(g['b1'][0]), 36, 'grad')
               + path([(530, 456), (530, 394), (390, 394), (382, 377)], 'grad', 4, head=True)
               + path([(330, 362), (160, 320), (160, 286)], 'grad', 4, head=True)
               + text(156, 384, fmt(g['W1'][0][1]), 36, 'grad', 'middle')
               + text(360, 1250, f'{fmt(dy)} × 1 × 1 × {fmt(d["x"][1])} = {fmt(g["W1"][0][1])}',
                      38, 'grad', 'middle'))
    # 同一条路径在解释链式法则后再出现，暂不展示参数写回。
    save('05-backpropagation', '05-反向追一条路径',
         svg('沿刚才的路径，反着乘回来', '前向数值保留；莓红箭头求局部变化率', s, 1300))
    s += phase(3, text(360, 1332,
                      f'{fmt(selected)} − {fmt(d["lr"])}×({fmt(g["W1"][0][1])}) = {fmt(d["updated_params"]["W1"][0][1])}',
                      36, 'param', 'middle'))
    save('05-backpropagation', '01-机制',
         svg(f'一条权重路径，怎样得到 {fmt(g["W1"][0][1])}', '灰色顺向算数值；莓红反向算梯度', s, 1400))

    def groups(values, y, color, prefix):
        a = text(170, y - 56, f'{prefix}W1', 36, color)
        a += text(490, y - 56, f'{prefix}b1', 36, color)
        for j in range(len(d['x'])):
            a += text(222 + j * 110, y - 12, f'x{j + 1}', 30, 'input', 'middle')
        for i in range(len(values['W1'])):
            a += text(114, y + 46 + i * 74, f'h{i + 1}', 32, anchor='end')
        a += values_matrix(170, y, values['W1'], color)
        a += values_matrix(490, y, [[v] for v in values['b1']], color)
        a += text(170, y + 214, f'{prefix}W2', 36, color)
        a += text(490, y + 214, f'{prefix}b2', 36, color)
        for j in range(len(values['W2'][0])):
            a += text(222 + j * 110, y + 258, f'h{j + 1}', 30, 'output', 'middle')
        a += text(114, y + 318, 'y', 32, anchor='end')
        a += values_matrix(170, y + 274, values['W2'], color)
        a += values_matrix(490, y + 274, [values['b2']], color)
        return a

    s = phase(0, groups(g, 250, 'grad', '∇'))
    s += phase(1, text(360, 700, f'新参数 = 旧参数 − {fmt(d["lr"])}×梯度', 34,
                      'param', 'middle')
               + arrow(360, 728, 360, 772, 'param', 4))
    s += phase(2, groups(d['updated_params'], 868, 'param', ''))
    s += phase(3, text(360, 1280, f'y={d["updated_prediction"]:.4f}', 38, 'output', 'middle')
               + text(360, 1344, f'L={d["updated_loss"]:.8f}', 38, 'output', 'middle'))
    save('05-backpropagation', '02-验证',
         svg('全部梯度齐备，再统一更新', '矩阵列对应输入，行对应本层输出', s, 1400))


def lesson06():
    d = read(6)
    xor = d['xor']
    initial = xor['history'][0]
    samples = [r['x'] for r in read(3)['rows']]
    b, din = len(samples), len(samples[0])
    hidden = len(xor['initial_params']['W1'])
    out = len(xor['initial_params']['W2'])
    s = box(215, 170, 290, 86, 'zero_grad()', 'grad', 36)
    s += text(360, 302, '清空上一次梯度', 32, 'grad', 'middle')
    s += arrow(360, 324, 360, 370, 'line')
    s += text(36, 408, f'X [{b},{din}]', 34, 'input')
    s += values_matrix(36, 434, samples, 'input', 72, 62, 34)
    s += text(352, 408, 'forward', 36, 'ink', 'middle')
    s += box(236, 470, 236, 110, f'H [{b},{hidden}]', 'output', 36)
    s += arrow(188, 535, 220, 535, 'line')
    s += arrow(488, 535, 520, 535, 'line')
    s += text(548, 408, f'y [{b},{out}]', 34, 'output')
    s += values_matrix(542, 434, [[v] for v in initial['predictions']], 'output', 125, 62, 32)
    s += text(352, 626, f'W1 [{hidden},{din}]', 30, 'param', 'middle')
    s += text(352, 674, f'W2 [{out},{hidden}]', 30, 'param', 'middle')
    s += arrow(360, 684, 360, 734, 'line')
    s += number_box(210, 750, 300, 112, '本批 MSE', f'{initial["loss"]:.5f}', 'output')
    s += arrow(360, 878, 360, 928, 'grad')
    s += text(360, 974, f'backward：∇W1 [{hidden},{din}]', 34, 'grad', 'middle')
    grad_symbols = [[f'g{i+1}{j+1}' for j in range(din)] for i in range(hidden)]
    s += values_matrix(274, 998, grad_symbols, 'grad', 86, 55, 32)
    s += arrow(360, 1232, 360, 1268, 'grad')
    s += text(360, 1322, f'SGD：W1 ← W1−{fmt(xor["learning_rate"])}∇W1', 34, 'param', 'middle')
    s += text(360, 1374, '其余参数同样更新', 30, 'muted', 'middle')
    s += path([(590, 1306), (684, 1306), (684, 213), (523, 213)], 'param', 3, head=True)
    save('06-training-loop', '01-机制',
         svg('一圈训练里，哪些数在变', '前向算数值，反向算梯度，step 改参数', s, 1400))

    px = lambda step: 108 + step / xor['steps'] * 540
    py = lambda loss: 706 - loss / .5 * 460
    s = axis(108, 706, 670, 220, '更新步数', 'MSE')
    for loss in (0, .25, .5):
        s += line(108, py(loss), 650, py(loss), 'line', 1, '5 6')
        s += text(88, py(loss) + 10, fmt(loss), 30, anchor='end')
    for step in (0, 100, 200, xor['steps']):
        s += text(px(step), 756, step, 30, anchor='middle')
    s += line(px(0), py(initial['loss']), px(xor['steps']), py(initial['loss']), 'muted', 3, '9 7')
    s += path([(px(r['step']), py(r['loss'])) for r in xor['history']], 'output', 4)
    s += dot(px(0), py(initial['loss']), 'output', 7)
    s += text(180, 330, f'{initial["loss"]:.5f}', 34, 'output')
    s += dot(px(xor['steps']), py(xor['final_loss']), 'output', 7)
    s += text(405, 626, f'{xor["final_loss"]:.2e}', 34, 'output')
    s += line(36, 806, 100, 806, 'output', 4)
    s += text(114, 816, '更新参数', 32, 'output')
    s += line(360, 806, 424, 806, 'muted', 3, '9 7')
    s += text(438, 816, '固定参数', 32, 'muted')
    s += text(36, 906, '四项输出怎样移动', 36, weight=600)
    qy = lambda value: 1230 - value * 250
    s += arrow(92, 1286, 670, 1286, 'ink', 2)
    s += arrow(92, 1286, 92, 956, 'ink', 2)
    for value in (0, 1):
        s += line(92, qy(value), 662, qy(value), 'line', 1, '5 5')
        s += text(66, qy(value) + 10, value, 32, anchor='end')
    s += text(36, 950, '预测', 32)
    for i, sample in enumerate(samples):
        cx = 150 + i * 156
        before, after = initial['predictions'][i], xor['predictions'][i]
        s += arrow(cx - 20, qy(before), cx + 20, qy(after), 'output', 3)
        s += dot(cx - 20, qy(before), 'input', 8, True)
        s += dot(cx + 20, qy(after), 'output', 9)
        s += text(cx, 1330, f'({sample[0]},{sample[1]})', 32, anchor='middle')
    s += text(360, 1376, f'空心：初始；实心：{xor["steps"]} 步', 30, 'muted', 'middle')
    save('06-training-loop', '02-验证',
         svg('更新参数后，四项预测靠近目标', '真实 PyTorch 记录；固定参数作同轴对照', s, 1400))


if __name__ == '__main__':
    lesson02()
    lesson03()
    lesson04()
    lesson05()
    lesson06()

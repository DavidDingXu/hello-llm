"""第 07—13 讲的可编辑机制图；数值读取同次课程 trace。"""
import math

from figure_tools import *


def number(value, digits=4):
    if value is None:
        return '−∞'
    return f'{value:.{digits}f}'.rstrip('0').rstrip('.') or '0'


def pair(values, digits=3):
    return '[' + ', '.join(number(v, digits) for v in values) + ']'


def label(x, y, value, color='ink', size=32):
    return text(x, y, value, size, color)


def row(values, y, colors=None, digits=4, x=36, width=216, height=64):
    result = ''
    for i, value in enumerate(values):
        value = number(value, digits) if isinstance(value, (float, int)) else value
        result += box(x + i * width, y, width - 10, height, value,
                      colors[i] if colors else 'output', 34)
    return result


def arrow_row(y1, y2, count=3, x=36, width=216, color='line'):
    return ''.join(arrow(x + (i + .5) * width - 5, y1,
                         x + (i + .5) * width - 5, y2, color)
                   for i in range(count))


def attention_axes(y, values, label_value, mask=False, x=164, cell_w=162,
                   cell_h=65, digits=4):
    result = text(36, y-72, label_value, 34, 'ink', weight=600)
    result += text(x + 1.5 * cell_w, y-27, 'K：被读取位置', 30,
                   'muted', 'middle')
    result += text(36, y + 92, 'Q', 32, 'input')
    for i in range(3):
        result += text(x + (i+.5)*cell_w, y+24, i, 30, 'muted', 'middle')
        result += text(90, y+66+i*cell_h, i, 30, 'muted', 'middle')
    colors = [['#E8EBEF' if mask and c > r else '#F3F6F9'
               for c in range(3)] for r in range(3)]
    result += matrix(x, y+42, values, cell_w=cell_w, cell_h=cell_h,
                     colors=colors, fmt=lambda v: number(v, digits), size=32)
    return result


def probability_bars(values, x=145, base=1170, scale=280, spacing=170,
                     color='output', bar_width=70):
    result = ''
    for i, value in enumerate(values):
        left = x+i*spacing
        result += rect(left, base-value*scale, bar_width, value*scale,
                       color, r=2)
        result += text(left+bar_width/2, base+48, ['红', '黄', '绿'][i],
                       32, 'ink', 'middle')
        result += text(left+bar_width/2, base-value*scale-16,
                       number(value, 3), 32, color, 'middle')
    return result


def cartesian(cx, cy, radius=120):
    result = circle(cx, cy, radius, color='line')
    result += arrow(cx-radius-20, cy, cx+radius+30, cy, 'muted', 2)
    result += arrow(cx, cy+radius+20, cx, cy-radius-30, 'muted', 2)
    result += text(cx+radius+24, cy+35, 'x', 30, 'muted', 'middle')
    result += text(cx-24, cy-radius-20, 'y', 30, 'muted', 'middle')
    result += text(cx-22, cy+35, '0', 28, 'muted', 'middle')
    return result


def vector(cx, cy, angle, radius=120, color='output', dash=False):
    end_x = cx+radius*math.cos(angle)
    end_y = cy-radius*math.sin(angle)
    if dash:
        return line(cx, cy, end_x, end_y, color, 3, '7 6')
    return arrow(cx, cy, end_x, end_y, color, 4)


def lesson07():
    d = read(7)
    folder = '07-embeddings'
    s = label(36, 169, '真实字符词表：79 项', 'input')
    for i, (token, index) in enumerate(zip(d['tokens'], d['ids'])):
        x = 36+i*93
        s += box(x, 197, 84, 64, token, 'input', 36)
        s += arrow(x+42, 269, x+42, 309, 'input')
        s += box(x, 320, 84, 64, index, 'input', 34)
    s += label(36, 439, '独立手算表 E [4,2]', 'param', 36)
    s += text(36, 484, '下表的 0—3 是演示项编号', 30, 'muted')
    table = d['toy_table']
    colors = [['#EFE5F5']*2 if i == 2 else ['light']*2 for i in range(4)]
    s += matrix(330, 552, table, cell_w=140, cell_h=70,
                colors=colors, fmt=number, size=36)
    s += text(400, 525, '坐标0', 30, 'muted', 'middle')
    s += text(540, 525, '坐标1', 30, 'muted', 'middle')
    for i in range(4):
        s += text(295, 597+70*i, i, 32, 'param', 'middle')
    s += box(36, 700, 140, 68, 'ID = 2', 'input', 34)
    s += arrow(185, 734, 275, 734, 'input')
    s += arrow(470, 845, 470, 898, 'param')
    s += box(300, 911, 330, 70, pair(table[2]), 'output', 38)
    s += text(36, 1046, '序列 [2,1,2] 逐位置取行', 34, 'ink')
    for i, index in enumerate(d['toy_ids']):
        x = 36+i*216
        s += box(x, 1082, 206, 62, f'ID {index}', 'input', 34)
        s += arrow(x+103, 1152, x+103, 1194, 'param')
        s += box(x, 1206, 206, 70, pair(table[index]), 'output', 34)
    save(folder, '01-机制', svg('文字先编号，再查参数表',
         '构造示例 · 输入编号与可训练向量分开', s, 1340))

    s = text(36, 170, '输入：[2,1,2]；L 为输出坐标之和', 32)
    s += text(36, 222, '每次读取的梯度贡献都是 [1,1]', 32, 'muted')
    s += text(36, 294, '同一参数行 E[2]', 36, 'param', weight=600)
    s += box(45, 330, 240, 76, '位置0：[1,1]', 'grad', 32)
    s += box(45, 456, 240, 76, '位置2：[1,1]', 'grad', 32)
    s += arrow(300, 368, 402, 427, 'grad')
    s += arrow(300, 494, 402, 443, 'grad')
    s += box(420, 394, 235, 86, pair(d['toy_gradient'][2]), 'grad', 40)
    s += text(420, 536, '两条路径相加', 32, 'grad')
    s += text(36, 645, '参数行 E[1]', 36, 'param', weight=600)
    s += box(45, 682, 240, 76, '位置1：[1,1]', 'grad', 32)
    s += arrow(300, 720, 405, 720, 'grad')
    s += box(420, 678, 235, 86, pair(d['toy_gradient'][1]), 'grad', 40)
    s += line(36, 822, 684, 822)
    s += text(36, 884, 'E[0]、E[3] 未被读取', 34, 'muted')
    s += text(36, 941, '梯度均为 [0,0]', 36, 'ink')
    save(folder, '02-验证', svg('重复读取，梯度回到同一行',
         '构造示例 · 编号不求导，参数表可求导', s, 1010))

    # 沿用同一小表；把批次轴画成两个平面，避免用立体方块遮住实际数字。
    batches = [d['toy_ids'], [1, 2, 1]]
    s = text(36, 183, '[B,T,D] = [2,3,2]', 40, 'ink', weight=600)
    s += text(36, 238, '2条样本 × 3个位置 × 2个坐标', 32, 'muted')
    for sample, ids in enumerate(batches):
        top = 310 + sample * 405
        s += text(36, top, f'样本{sample}：编号 {ids}', 34, 'input', weight=600)
        for coordinate in range(2):
            s += text(355 + coordinate * 150, top + 66,
                      f'坐标{coordinate}', 30, 'muted', 'middle')
        values = [table[index] for index in ids]
        colors = [['light']*2 for _ in ids]
        if sample == 1:
            colors[2][0] = '#DCEFED'
        s += matrix(280, top + 92, values, cell_w=150, cell_h=74,
                    colors=colors, fmt=number, size=38)
        for position, index in enumerate(ids):
            s += text(36, top + 141 + position * 74,
                      f'位置{position} / ID{index}', 30, 'input')
    s += line(36, 1074, 684, 1074)
    s += text(36, 1135, '先选样本1，再选位置2、坐标0', 32)
    s += text(36, 1197, 'batch_vectors[1,2,0] = 0', 38, 'output', weight=600)
    save(folder, '03-三个轴怎样数', svg('三个索引，才能取到这一个数',
         '仍用刚才的四行小表；每个向量仍为二维', s, 1260))


def lesson08():
    d = read(8)
    folder = '08-softmax'
    s = label(36, 174, '词表候选', 'muted')
    s += ''.join(text(139+216*i, 226, token, 36, 'input', 'middle')
                 for i, token in enumerate(('红', '黄', '绿')))
    s += row(d['logits'], 253, ['input']*3)
    s += text(36, 395, '逐项 exp', 34, 'ink')
    s += arrow_row(325, 350)
    s += row(d['exp'], 410, ['param']*3, digits=4)
    s += text(360, 537, '总和 = 1 + e + e² ≈ 11.10734', 32, 'ink', 'middle')
    s += arrow_row(555, 590)
    s += text(36, 628, '每项除以同一个总和', 34)
    s += row(d['probabilities'], 665, digits=6)
    s += text(36, 800, '概率', 34, 'output')
    s += line(90, 870, 90, 1170, 'muted')
    s += line(90, 1170, 663, 1170, 'muted')
    for value in (0, .5, 1):
        y = 1170-value*280
        s += text(76, y+10, number(value), 28, 'muted', 'end')
        s += line(90, y, 663, y, 'line', 1)
    s += probability_bars(d['probabilities'])
    s += text(360, 1285, '三项非负，和为 1', 36, 'output', 'middle')
    save(folder, '01-机制', svg('从分数到完整概率分布',
         '构造示例 · 沿候选轴计算 Softmax', s, 1340))

    s = text(36, 177, '整体加 1000：相对差距没变', 36, 'ink', weight=600)
    s += row(d['logits'], 220, ['input']*3)
    s += arrow_row(292, 334)
    s += row(d['shifted_scores'], 347, ['param']*3)
    s += text(360, 472, '两行 Softmax 完全相同', 34, 'output', 'middle')
    s += row(d['probabilities'], 512, digits=4)
    s += line(36, 625, 684, 625)
    s += text(36, 687, '只把第三项 2 → 3', 36, 'ink', weight=600)
    s += text(36, 743, '蓝：原分布　青：第三项提高后', 30, 'muted')
    base, scale = 1110, 280
    s += line(95, 810, 95, base, 'muted')+line(95, base, 680, base, 'muted')
    for i, (before, after) in enumerate(zip(d['probabilities'], d['variant_probabilities'])):
        left = 140+i*180
        label_positions = [base-before*scale-16, base-after*scale-16]
        if abs(label_positions[0]-label_positions[1]) < 44:
            upper = 0 if label_positions[0] < label_positions[1] else 1
            label_positions[upper] = label_positions[1-upper]-44
        for j, (value, offset, color) in enumerate(((before, 0, 'input'), (after, 62, 'output'))):
            s += rect(left+offset, base-value*scale, 48, value*scale, color, r=2)
            # 数值比柱子宽：旧值向左靠、新值向右靠，避免字压到相邻柱上。
            s += text(left+(48 if j == 0 else 62), label_positions[j],
                       number(value, 3), 32, color, 'end' if j == 0 else 'start')
        s += text(left+55, base+48, ('红', '黄', '绿')[i], 32, 'ink', 'middle')
    s += text(360, 1231, '分母也变了，前两项概率下降', 34, 'ink', 'middle')
    save(folder, '02-验证', svg('分数没变，概率怎么降了？',
         '构造示例 · 分数差决定相对比例', s, 1290))


def lesson09():
    d = read(9)
    folder = '09-training-targets'
    example = d['shift_example']
    s = text(36, 174, '短片段：苹果。', 36, 'input')
    s += text(36, 232, '完整序列', 32, 'muted')
    complete = ['BOS', '苹', '果', '。', 'EOS']
    for i, value in enumerate(complete):
        s += box(36+i*130, 262, 120, 72, value, 'input', 34)
        if i < 4:
            s += arrow(158+i*130, 298, 164+i*130, 298, 'input', 2)
    s += text(36, 402, 'x：去掉末项，再右侧填充', 34)
    s += text(36, 596, 'y：去掉首项，同列就是答案', 34)
    x_names = ['BOS', '苹', '果', '。', 'PAD', 'PAD']
    y_names = ['苹', '果', '。', 'EOS', '−100', '−100']
    for i in range(6):
        x = 36+i*108
        color = 'input' if i < 4 else 'muted'
        s += text(x+49, 453, i, 30, 'muted', 'middle')
        s += box(x, 476, 100, 72, x_names[i], color, 32)
        s += arrow(x+50, 614, x+50, 640, 'output' if i < 4 else 'line')
        s += box(x, 656, 100, 72, y_names[i], 'output' if i < 4 else 'muted', 32)
        s += text(x+50, 787, example['x'][0][i], 32, 'input', 'middle')
        s += text(x+50, 839, example['y'][0][i], 32, 'output' if i < 4 else 'muted', 'middle')
    s += line(36, 881, 684, 881)
    s += text(36, 941, '前四列：4 道有效训练题', 36, 'output')
    s += text(36, 1000, 'EOS 计分；−100 不是词表项', 34)
    save(folder, '01-机制', svg('文字错一格，就给出了答案',
         '构造示例 · 每个位置预测下一个字符', s, 1070))

    s = text(36, 173, '正确答案概率 p → 损失 −ln(p)', 34)
    left, right, top, bottom = 125, 650, 245, 665
    s += arrow(left, bottom, right+15, bottom, 'muted', 2)
    s += arrow(left, bottom, left, top-25, 'muted', 2)
    s += text(55, 224, '损失', 32, 'muted')
    s += text(right+35, 718, 'p', 34, 'muted')
    for p in (.25, .5, 1):
        x = left+p*(right-left)
        s += text(x, bottom+44, number(p, 2), 28, 'muted', 'middle')
    for loss in (0, 1, 2, 3):
        y = bottom-loss/3.5*(bottom-top)
        s += text(left-20, y+10, loss, 28, 'muted', 'end')
        s += line(left, y, right, y, 'line', 1)
    points = []
    for i in range(3, 101):
        p = i/100
        points.append((left+p*(right-left), bottom+math.log(p)/3.5*(bottom-top)))
    s += '<polyline points="'+' '.join(f'{x},{y}' for x, y in points)+'" fill="none" stroke="'+C['output']+'" stroke-width="4"/>'
    for p, annotation, dx, dy in ((.25, '1.3863', 18, -18), (.5, '0.6931', 24, -20)):
        x, y = left+p*(right-left), bottom+math.log(p)/3.5*(bottom-top)
        s += circle(x, y, 7, color='output')
        s += text(x+dx, y+dy, annotation, 30, 'output')
    s += text(36, 797, '有效位置求平均，填充不参与', 36)
    cells = [('0.693147', 'output'), ('1.386294', 'output'), ('−100', 'muted'), ('−100', 'muted')]
    for i, (value, color) in enumerate(cells):
        s += box(36+i*164, 845, 154, 70, value, color, 32 if i < 2 else 34)
        if i >= 2:
            s += line(42+i*164, 851, 182+i*164, 909, 'muted', 2)
    s += text(360, 1002, '(0.693147 + 1.386294) ÷ 2', 34, 'ink', 'middle')
    s += text(360, 1081, '= 1.039721', 40, 'output', 'middle')
    s += text(360, 1152, '添加更多填充，平均值不变', 32, 'muted', 'middle')
    save(folder, '02-验证', svg('概率越低，负对数损失越大',
         '构造示例 · 先逐位置计分，再平均有效项', s, 1220))


def lesson10():
    d = read(10)
    folder = '10-attention'
    p0 = text(36, 172, 'Q 的位置0', 34, 'input')
    p0 += box(36, 235, 210, 76, pair(d['q'][0]), 'input', 36)
    p0 += text(365, 172, 'K：三个位置', 34, 'input')
    p0 += matrix(410, 200, d['k'], cell_w=110, cell_h=66, fmt=number, size=34)
    for i in range(3):
        p0 += text(379, 244+66*i, i, 30, 'muted', 'middle')
        p0 += arrow(255, 273, 348, 235+66*i, 'input', 2)
    p1 = text(36, 443, '点积 [1,0,1]，再除以 √2', 34)
    p1 += row(d['scores'][0], 478, ['input']*3, digits=4)
    p2 = arrow_row(553, 604)
    p2 += text(36, 644, '沿 K 位置做 Softmax', 34)
    p2 += row(d['weights'][0], 678, digits=4)
    p3 = arrow_row(752, 820, color='output')
    p3 += text(36, 857, '分别乘对应的 V', 34)
    p3 += row([pair(v, 2) for v in d['v']], 888, ['input']*3)
    weighted = [[a*value for value in v] for a, v in zip(d['weights'][0], d['v'])]
    p3 += arrow_row(962, 1001, color='output')
    for i, value in enumerate(weighted):
        x, y = 36+216*i, 1015
        p3 += rect(x, y, 206, 104, '#FFFFFF', 'output')
        p3 += text(x+103, y+41, number(value[0], 3), 34, 'output', 'middle')
        p3 += text(x+103, y+86, number(value[1], 3), 34, 'output', 'middle')
        p3 += line(x+18, y+12, x+11, y+12, 'output')
        p3 += line(x+11, y+12, x+11, y+92, 'output')
        p3 += line(x+11, y+92, x+18, y+92, 'output')
        p3 += line(x+188, y+12, x+195, y+12, 'output')
        p3 += line(x+195, y+12, x+195, y+92, 'output')
        p3 += line(x+195, y+92, x+188, y+92, 'output')
    p4 = ''.join(arrow(139+216*i, 1130, 360, 1190, 'output', 2) for i in range(3))
    p4 += text(360, 1235, '逐坐标相加', 34, 'ink', 'middle')
    p4 += box(100, 1260, 520, 78, pair(d['output'][0], 4), 'output', 38)
    s = ''.join(phase(i, part) for i, part in enumerate((p0, p1, p2, p3, p4)))
    save(folder, '01-机制', svg('一行注意力，完整算一次',
         '构造示例 · 先允许读取全部三个位置', s, 1400))

    s = attention_axes(215, d['weights'], 'Q、K 固定：注意力比例不变')
    s += text(36, 561, '只改 V 的位置2', 36, 'ink', weight=600)
    s += box(45, 601, 255, 76, pair(d['v'][2]), 'input', 38)
    s += arrow(320, 639, 390, 639, 'output')
    s += box(410, 601, 255, 76, pair(d['variant_v'][2]), 'input', 38)
    s += text(45, 769, '修改前 output', 32, 'muted')
    s += text(390, 769, '修改后 output', 32, 'muted')
    s += matrix(45, 805, d['output'], cell_w=145, cell_h=70,
                fmt=lambda v: number(v, 3), size=32)
    s += matrix(390, 805, d['variant_output'], cell_w=145, cell_h=70,
                fmt=lambda v: number(v, 3), size=32)
    delta = [b-a for a, b in zip(d['output'][0], d['variant_output'][0])]
    s += text(36, 1110, '位置0增量 = 0.4011 × [2,0]', 34)
    s += box(120, 1152, 480, 76, pair(delta, 4), 'output', 38)
    save(folder, '02-验证', svg('比例不变，汇总内容可以变',
         '构造示例 · 比例来自 Q/K，内容来自 V', s, 1300))


def lesson11():
    d, unmasked = read(11), read(10)
    folder = '11-causal-mask'
    p0 = attention_axes(224, unmasked['scores'], '缩放后的 scores')
    p1 = ''
    for r in range(3):
        for c in range(r+1, 3):
            x, y = 164+c*162, 266+r*65
            p1 += rect(x, y, 157, 60, '#E4E8ED', r=4)
            p1 += text(x+78, y+42, '−∞', 36, 'muted', 'middle')
    p1 += text(36, 541, '未来格先置 −∞', 36, 'muted')
    p2 = arrow(405, 474, 405, 577, 'output')
    p2 += attention_axes(675, d['weights'], 'Softmax 后：未来比例为 0', mask=True)
    p3 = text(36, 1001, '同一份 V', 34, 'input')
    p3 += text(416, 1001, '因果汇总输出', 34, 'output')
    p3 += matrix(60, 1038, d['v'], cell_w=100, cell_h=66,
                 fmt=number, size=34)
    p3 += arrow(285, 1134, 374, 1134, 'output')
    p3 += matrix(405, 1038, d['output'], cell_w=140, cell_h=66,
                 fmt=lambda v: number(v, 3), size=32)
    s = ''.join(phase(i, part) for i, part in enumerate((p0, p1, p2, p3)))
    save(folder, '01-机制', svg('先屏蔽未来，再归一化',
         '构造示例 · 行为 Q，列为 K 的位置', s, 1300))

    s = text(36, 178, '输入 X：仅替换最后一个位置', 34)
    s += row([pair(v) for v in d['q']], 224, ['input']*3)
    s += text(139, 337, '位置0', 32, 'muted', 'middle')
    s += text(355, 337, '位置1', 32, 'muted', 'middle')
    s += text(571, 337, '位置2', 32, 'muted', 'middle')
    s += arrow_row(353, 411, color='input')
    s += row([pair(v) for v in d['changed_last_qk']], 425,
             ['input', 'input', 'grad'])
    s += text(36, 575, '因果约束下，前两行输出', 36)
    s += text(54, 646, '替换前', 32, 'muted')+text(405, 646, '替换后', 32, 'muted')
    s += matrix(45, 684, d['output'][:2], cell_w=145, cell_h=82,
                fmt=lambda v: number(v, 3), size=32)
    s += matrix(390, 684, d['changed_output'][:2], cell_w=145, cell_h=82,
                fmt=lambda v: number(v, 3), size=32)
    s += text(360, 916, '前缀最大差 = 0', 40, 'output', 'middle')
    s += line(36, 977, 684, 977)
    open_delta = max(abs(a-b) for before, after in zip(unmasked['output'][:2], d['unmasked_changed_output'][:2])
                     for a, b in zip(before, after))
    s += text(36, 1038, '移除掩码：未来就能影响前缀', 34)
    s += text(360, 1120, f'前缀最大差 ≈ {number(open_delta, 4)}', 38, 'grad', 'middle')
    save(folder, '02-验证', svg('改掉未来，检查前缀是否变化',
         '构造示例 · 参数固定，不做反向或更新', s, 1210))


def join_heads(values):
    return [[*values[0][0][t], *values[0][1][t]] for t in range(3)]


def probability_label(value):
    if 0 < value < .001:
        return '<0.001'
    if .9995 <= value < 1:
        return '≈1'
    return number(value, 3)


def lesson12():
    d = read(12)
    folder = '12-multi-head-attention'
    original = [[int(v) for v in row_values] for row_values in d['x'][0]]
    p0 = text(36, 162, '索引 X [B,T,D] = [1,3,4]', 32, 'input')
    p0 += matrix(120, 190, original, cell_w=125, cell_h=52, size=34)
    p1 = ''
    for h, x in ((0, 60), (1, 415)):
        p1 += arrow(280 if h == 0 else 485, 359, x+100, 430, 'input')
        p1 += text(x, 466, f'头{h}：全部位置', 32, 'input')
        p1 += matrix(x, 489, d['split'][0][h], cell_w=100, cell_h=52,
                     fmt=number, size=34)
    p1 += text(360, 697, '[B,H,T,d] = [1,2,3,2]', 32, 'input', 'middle')
    # 正文讲到拆头时，只显示格子的去向，不提前引入投影与汇总。
    save(folder, '04-只看格子怎样拆', svg('把特征分开，位置一个不少',
         '只重排坐标；每个头都保留全部位置', p0 + p1, 760))
    p2 = text(36, 758, '投影后：Q位置1，列为K位置', 32, 'ink')
    for key in range(3):
        p2 += text(210+180*key, 805, key, 32, 'muted', 'middle')
    for h, y in ((0, 825), (1, 908)):
        p2 += text(36, y+40, f'头{h}', 32, 'input')
        p2 += matrix(120, y, [d['projected_weights'][0][h][1]],
                     cell_w=180, cell_h=58, fmt=probability_label, size=34)
    p2 += text(36, 1004, '按各头比例汇总 V', 32)
    for h, x in ((0, 48), (1, 396)):
        p2 += box(x, 1030, 277, 62, pair(d['projected_context'][0][h][1]),
                   'output', 32)
    merged = join_heads(d['projected_context'])
    p3 = arrow(184, 1098, 190, 1155, 'output')+arrow(535, 1098, 520, 1155, 'output')
    p3 += matrix(48, 1165, [merged[1]], cell_w=157, cell_h=59,
                 fmt=lambda v: number(v, 3), size=30)
    p4 = arrow(360, 1230, 360, 1288, 'param')
    p4 += rect(296, 1240, 128, 42, '#FFFFFF')
    p4 += text(360, 1272, 'Wo', 32, 'param', 'middle')
    p4 += matrix(48, 1300, [d['projected_output'][0][1]], cell_w=157,
                 cell_h=59, fmt=lambda v: number(v, 3), size=30)
    # 下半段等正文讲完投影与各头比例后再展示，数值仍来自同一次记录。
    save(folder, '05-两头汇总再拼回', svg('各头读完，按位置拼回',
         '同一查询位置1；显示值经过舍入',
         '<g transform="translate(0,-595)">' + p2 + p3 + p4 + '</g>', 820))
    s = ''.join(phase(i, part) for i, part in enumerate((p0, p1, p2, p3, p4)))
    save(folder, '01-机制', svg('拆头、独立汇总、拼回',
         '构造示例 · 上半看索引，下半看真实投影值', s, 1400))

    batch = join_heads(d['projected_context'])
    reference = join_heads(d['projected_reference'])
    s = text(36, 180, '一次批量计算', 36, 'input', weight=600)
    s += text(36, 238, '[1,2,3,2] → 按位置拼接', 32, 'muted')
    s += matrix(60, 280, batch, cell_w=152, cell_h=76,
                fmt=lambda v: number(v, 3), size=32)
    s += text(360, 603, '同一数值，同一坐标', 36, 'output', 'middle')
    s += text(36, 702, '逐头循环，再 stack', 36, 'input', weight=600)
    s += text(36, 760, '头0、头1各算完，再恢复头轴', 32, 'muted')
    s += matrix(60, 802, reference, cell_w=152, cell_h=76,
                fmt=lambda v: number(v, 3), size=32)
    s += text(360, 1127, '最大差 = '+number(d['per_head_max_difference']),
               40, 'output', 'middle')
    s += text(360, 1193, '同乘 Wo 后，最终输出也一致', 32, 'ink', 'middle')
    save(folder, '02-验证', svg('批量计算与逐头计算对照',
         '同一输入、同一参数，只改变计算组织', s, 1260))


def lesson13():
    d = read(13)
    folder = '13-rope'
    p0 = text(36, 176, '示意：四分之一圈', 34, 'muted')
    p0 += cartesian(210, 402, 120)
    p0 += vector(210, 402, 0, 120, 'input')
    p0 += text(36, 589, '原向量 [1,0]', 32, 'input')
    p1 = vector(210, 402, math.pi/2, 120)
    p1 += text(36, 648, 'π/2 弧度 → [0,1]', 34, 'output')
    p2 = text(392, 176, '实际：位置1', 34, 'ink')
    p2 += cartesian(533, 402, 120)
    p2 += vector(533, 402, 0, 120, 'input', True)
    p2 += vector(533, 402, 1, 120)
    tip_x, tip_y = 533+120*math.cos(1), 402-120*math.sin(1)
    p2 += line(tip_x, tip_y, tip_x, 402, 'output', 2, '5 5')
    p2 += line(533, tip_y, tip_x, tip_y, 'output', 2, '5 5')
    p2 += text(392, 589, '角度 = 1 × 1', 32)
    p2 += text(392, 648, '= 1 弧度', 34, 'output')
    p3 = line(36, 711, 684, 711)
    p3 += text(36, 776, '1 弧度 ≈ 57.3°，并非 90°', 36)
    p3 += text(36, 844, 'a′ = a cosα − b sinα', 34)
    p3 += text(36, 901, 'b′ = a sinα + b cosα', 34)
    p3 += box(78, 962, 564, 85, pair(d['first_pair_pos1'], 6), 'output', 38)
    p3 += text(360, 1120, '位置1：cos(1)、sin(1)', 34, 'output', 'middle')
    p3 += text(360, 1190, 'Q/K 旋转，V 不旋转', 34, 'muted', 'middle')
    s = ''.join(phase(i, part) for i, part in enumerate((p0, p1, p2, p3)))
    save(folder, '01-机制', svg('旋转后，每个坐标怎样算',
         '构造示例 · 先认识旋转，再使用真实角度', s, 1260))

    s = text(36, 176, '位置 [0,1] → [7,8]', 36)
    for cx, angles, title in ((200, (0, 1), '原位置'), (530, (7, 8), '共同加7')):
        s += cartesian(cx, 367, 100)
        s += vector(cx, 367, angles[0], 100, 'input')
        s += vector(cx, 367, angles[1], 100, 'output')
        s += text(cx, 536, title, 34, 'ink', 'middle')
    s += text(360, 605, '夹角差仍为1弧度；长度仍为1', 32, 'muted', 'middle')
    s += text(360, 672, '两次点积 ≈ '+number(d['dots'][0][0][0][1], 6),
               38, 'output', 'middle')
    s += line(36, 724, 684, 724)
    s += text(36, 785, '只改距离：点积并不单调下降', 34)
    left, right, middle, amplitude = 90, 660, 1050, 140
    s += arrow(left, middle, right+10, middle, 'muted', 2)
    s += arrow(left, middle+amplitude+15, left, middle-amplitude-25, 'muted', 2)
    s += text(left-15, middle-amplitude+8, '1', 28, 'muted', 'end')
    s += text(left-15, middle+amplitude+8, '−1', 28, 'muted', 'end')
    points = [(left+i/100*(right-left)/8, middle-math.cos(i/100)*amplitude)
              for i in range(801)]
    s += '<polyline points="'+' '.join(f'{x},{y}' for x, y in points)+'" fill="none" stroke="'+C['output']+'" stroke-width="4"/>'
    for distance, delta in ((1, -25), (2, 36), (7, -25)):
        x, y = left+distance/8*(right-left), middle-math.cos(distance)*amplitude
        s += circle(x, y, 6, color='output')
        s += text(x+5, y+delta, number(math.cos(distance), 3), 32,
                   'output', 'middle')
        s += text(x, middle+amplitude+51, distance, 30, 'muted', 'middle')
    s += text(684, middle+amplitude+51, '距离', 30, 'muted', 'end')
    s += text(360, 1324, '固定 q=k=[1,0]：点积 = cos(距离)', 32, 'ink', 'middle')
    save(folder, '02-验证', svg('共同平移保留点积',
         '构造示例 · 固定内容，只改变位置', s, 1390))


if __name__ == '__main__':
    for build in (lesson07, lesson08, lesson09, lesson10, lesson11,
                  lesson12, lesson13):
        build()

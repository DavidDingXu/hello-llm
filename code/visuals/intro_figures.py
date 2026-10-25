"""介绍、开篇与结课的图；展示成果、连接和参数状态。"""
import json

from figure_tools import CODE, arrow, box, line, rect, save, svg, text


def finished_model():
    """从保留的生成记录取文字，分别展示续写与问答任务。"""
    record = json.loads((CODE / 'artifacts/first_run/generation_comparison.json').read_text(encoding='utf-8'))
    continuation = record['pretrain']['outputs'][0]
    answer = record['sft']['outputs'][2]
    content = ''
    for top, title, sample in (
        (176, '预训练后：给半句话，接着写', continuation),
        (752, '问答微调后：给问题，接着答', answer),
    ):
        content += text(36, top, title, 36, 'ink', weight=600)
        content += text(60, top + 65, '你输入', 32, 'input')
        if '\n' in sample['prompt']:
            content += rect(48, top + 88, 624, 126, '#F2F6FB', r=8)
            for row, value in enumerate(sample['prompt'].splitlines()):
                content += text(68, top + 135 + row * 47, value, 34, 'input')
            model_y = top + 260
        else:
            content += box(48, top + 88, 624, 80, sample['prompt'], 'input', 38)
            model_y = top + 214
        content += arrow(360, model_y - 40, 360, model_y - 9, 'line')
        content += box(112, model_y, 496, 80, '模型计算，再选下一个字', 'param', 36)
        content += arrow(360, model_y + 87, 360, model_y + 120, 'output')
        # 每格保留一个实际选中的字符；分格显示这句话由多次选择组成。
        chars = sample['generated_text']
        assert len(chars) == 6
        for i, char in enumerate(chars):
            content += box(73 + i * 96, model_y + 132, 94, 76, char, 'output', 42)
        content += text(360, model_y + 258, '每次选一项，接回输入，再继续', 32, 'output', 'middle')
    content += line(36, 688, 684, 688)
    content += text(360, 1325, '真实输出；换成新问法，仍可能答错。', 30, 'muted', 'middle')
    return svg('最终，你会造出什么？', '同一个网络，经过两段训练。', content, 1370)


def learning_route():
    """完整目录按手机单列阅读；讲次与主题只从发布信息取值。"""
    metadata = json.loads(
        (CODE / 'visuals/reading_site/course.zh.json').read_text(encoding='utf-8')
    )
    lessons = {
        int(article['id']): article
        for article in metadata['articles']
        if str(article['id']).isdigit() and 1 <= int(article['id']) <= 20
    }
    if sorted(lessons) != list(range(1, 21)):
        raise ValueError('目录需要包含第01—20讲')

    # 单行保留正式标题的主题；完整标题在正文的可展开目录中呈现。
    stages = (
        ('第一阶段', 1, 6, ('手算梯度，更新网络参数', '让小网络学会四条规则')),
        ('第二阶段', 7, 9, ('做出字符预测基线', '看见它读不到前文的限制')),
        ('第三阶段', 10, 16, ('手写各组件，组装完整模型', '追完一条真实前向计算')),
        ('第四阶段', 17, 20, ('从随机权重走到续写与问答', '完成排错对照和独立迁移')),
    )
    content = ''
    y = 150
    for index, (name, first, last, outcomes) in enumerate(stages):
        module = lessons[first]['module']
        if any(lessons[number]['module'] != module for number in range(first, last + 1)):
            raise ValueError(f'{name}的目录分组与发布信息不一致')
        title = module.split('、', 1)[1]
        content += f'<g data-stage="{index + 1}">'
        content += text(36, y + 25, name, 28, 'muted')
        content += text(684, y + 25, f'{first:02d}—{last:02d}讲', 28, 'muted', 'end')
        content += text(36, y + 77, title, 38, 'ink', weight=600)
        content += line(36, y + 98, 684, y + 98)
        for row, number in enumerate(range(first, last + 1)):
            baseline = y + 144 + row * 58
            topic = lessons[number]['title'].split('｜', 1)[1].split('：', 1)[0]
            content += f'<g data-lesson="{number:02d}">'
            content += text(40, baseline, f'{number:02d}', 34, 'input')
            content += text(116, baseline, topic, 36, 'ink')
            content += '</g>'

        result_y = y + 128 + (last - first + 1) * 58
        content += rect(36, result_y, 648, 142, '#F2F7F6', r=8)
        content += text(58, result_y + 35, '阶段成果', 28, 'output', weight=600)
        for row, outcome in enumerate(outcomes):
            content += text(58, result_y + 80 + row * 43, outcome, 32, 'output')
        content += '</g>'
        if index < len(stages) - 1:
            content += arrow(360, result_y + 157, 360, result_y + 187)
        y = result_y + 216

    height = y - 28
    return svg('20讲，手写一个小语言模型', '四个阶段，沿着同一个项目往前走。', content, height)


def generation_and_learning():
    content = text(36, 174, '生成：选中的字，接回输入', 36, 'output', weight=600)
    content += box(85, 220, 505, 76, '早上，小丁喜欢', 'input', 36)
    content += arrow(337, 301, 337, 340)
    content += box(137, 350, 400, 86, '模型 · 参数固定', 'param', 36)
    content += arrow(337, 441, 337, 479)
    for i, label in enumerate(('红', '黄', '…')):
        content += box(137 + i * 142, 490, 124, 72, label,
                       'output' if i == 0 else 'line', 38)
    content += text(337, 604, '给候选算分，这次选中“红”', 32, 'muted', 'middle')
    content += arrow(337, 619, 337, 651, 'output')
    content += box(85, 663, 505, 76, '早上，小丁喜欢红', 'input', 36)
    content += ('<path d="M596 701 H650 V258 H599" fill="none" '
                'stroke="#187B79" stroke-width="3" marker-end="url(#a-output)"/>')
    content += text(610, 462, '再', 32, 'output', 'middle')
    content += text(610, 504, '算', 32, 'output', 'middle')
    content += text(610, 546, '一', 32, 'output', 'middle')
    content += text(610, 588, '次', 32, 'output', 'middle')
    content += line(36, 788, 684, 788)
    content += text(36, 852, '训练：已知答案，用错误调参数', 36, 'param', weight=600)
    content += box(48, 904, 286, 76, '早上，小丁喜欢', 'input', 30)
    content += box(412, 904, 260, 76, '已知下一字：红', 'input', 30)
    content += arrow(191, 985, 191, 1024)
    content += arrow(542, 985, 542, 1024)
    content += box(48, 1036, 286, 78, '模型算出预测', 'param', 34)
    content += box(412, 1036, 260, 78, '计算错误', 'output', 34)
    content += arrow(339, 1075, 400, 1075, 'output')
    content += ('<path d="M542 1120 V1180 H191 V1126" fill="none" '
                'stroke="#8056A5" stroke-width="3" marker-end="url(#a-param)"/>')
    content += text(366, 1235, '沿计算找影响，调整模型里的数', 32, 'param', 'middle')
    return svg('一句话，怎样接着写出来？', '候选只画三项；实际词表有79项。', content, 1290)


def update_box(y, title, detail, repeats):
    content = rect(36, y, 648, 210, 'light')
    content += text(60, y + 47, title, 36, 'ink', weight=600)
    content += text(60, y + 89, detail, 30, 'input')
    for x, label in ((60, '预测'), (220, '评分'), (380, '反向'), (540, '更新')):
        content += box(x, y + 104, 110, 58, label, 'output', 32)
    for x in (175, 335, 495):
        content += arrow(x, y + 133, x + 33, y + 133, 'output')
    content += text(360, y + 201, repeats, 27, 'muted', 'middle')
    return content


def whole_journey():
    content = box(130, 165, 460, 85, '随机初值 · 92,352个参数', 'param', 34)
    content += arrow(360, 255, 360, 291, 'param')
    content += update_box(302, '第17讲 · 文本预训练', '256条短句；给有效的下一字目标评分', '反复更新1,000次')
    content += arrow(360, 517, 360, 553, 'param')
    content += box(130, 564, 460, 85, '保存预训练权重', 'param', 36)
    content += arrow(360, 654, 360, 690, 'param')
    content += update_box(701, '第19讲 · 监督微调', '24条问答；只给答案与EOS评分', '继续更新300次；本栏更新全部参数')
    content += arrow(360, 916, 360, 952, 'param')
    content += box(130, 963, 460, 85, '保存微调权重', 'param', 36)
    content += line(36, 1090, 684, 1090)
    content += text(36, 1145, '第18讲 · 任取一份权重，固定参数生成', 32, 'output', weight=600)
    content += box(36, 1178, 184, 68, '给定前文', 'input', 32)
    content += arrow(225, 1212, 259, 1212, 'output')
    content += box(271, 1178, 180, 68, '选下一项', 'output', 32)
    content += arrow(456, 1212, 490, 1212, 'output')
    content += box(502, 1178, 182, 68, '接回输入', 'input', 32)
    content += text(360, 1302, '网络结构没换；训练改参数，生成加文字。', 30, 'muted', 'middle')
    return svg('同一网络，两次训练', '下一段训练，接着使用上一段保存的参数。', content, 1345)


if __name__ == '__main__':
    save('intro', '01-最终做出什么', finished_model())
    save('intro', '02-学习路线', learning_route())
    save('00-introduction', '01-生成与学习', generation_and_learning())
    save('20-full-workflow', '03-全流程', whole_journey())

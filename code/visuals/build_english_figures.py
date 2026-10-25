"""Build English figures from the existing editable SVG / native plot sources.

No image generation or bitmap editing is used. Model tokens, samples, numerical
data and Chinese source figures are unchanged. English display text lives in
english_figure_texts.tsv. Run from any directory with the course environment:

    python visuals/build_english_figures.py
    python visuals/build_english_figures.py --animations

Requires the existing Pillow / Matplotlib / NumPy environment, Node.js,
rsvg-convert and FFmpeg. Temporary frame files are removed after encoding.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
COLUMN = HERE.parents[1]
ARTICLES = COLUMN / 'chapters'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
CJK = re.compile(r'[\u4e00-\u9fff]')
FONT = "Arial,'Hiragino Sans GB','Microsoft YaHei','Noto Sans CJK SC',sans-serif"
TABLE = HERE / 'english_figure_texts.tsv'
TRANSLATIONS = dict(line.split('\t', 1) for line in TABLE.read_text(encoding='utf-8').splitlines()
                    if '\t' in line and not line.startswith('#'))
# These are actual characters, input fragments, facts or recorded outputs.
# Keeping them is essential: translating them would change the model example.
PRESERVED = {
    '后', '喜', '小', '时', '丁', '果', '欢', '的', '答', '答：', '紫', '红',
    '绿', '色', '苹', '草', '香', '黄', '早上，小周喜欢', '早上，小丁喜欢',
    '早上，小丁喜欢红色的苹果。', '红色', '红色的', '红色的苹', '红色的苹果',
    '红色的苹果。', '黄色的香蕉。', '周绿色的草莓。',
    '小周 → 红色的苹果', '小丁 → 黄色的香蕉', '问：小丁喜欢什么水果？',
}
OUTLINED = {
    '01-neuron/04-ReLU怎样处理正负数.svg',
    '01-neuron/08-激活函数增加了什么.svg',
    '04-gradients/03-两个参数的损失曲面.svg',
    '19-fine-tuning/03-微调取舍.svg',
}


def recorded_label(value: str) -> str | None:
    """Translate the label around recorded values without copying stale numbers."""
    for pattern, replacement in (
        (r'前4项：(.*)', lambda m: 'First 4: ' + m[1].replace('，', ', ')),
        (r'同一色阶：(.*) 到 (.*)', r'Shared scale: \1 to \2'),
        (r'每边(\d+)格；共用色阶 ±([\d.]+)', r'\1 values each; shared color scale ±\2'),
        (r'固定位置(\d+)：“([^”]+)” / 编号(\d+)', r'Fixed position \1: “\2” / ID\3'),
        (r'最后一个输入都是“([^”]+)” / ID(\d+)', r'Both end with “\1” / ID\2'),
        (r'候选“([^”]+)”：取输出矩阵第(\d+)行', r'Candidate “\1”: output-matrix row \2'),
        (r'W红,₀ = ([+−\-]?[\d.]+)', r'W红,₀ = \1'),
        (r'乘积 = ([+−\-]?[\d.]+)', r'Product = \1'),
        (r'64项之和 = ([+−\-]?[\d.]+)', r'Sum of 64 terms = \1'),
        (r'才得到“红”的概率 ≈ ([\d.]+)', r'to get P(“红”) ≈ \1'),
        (r'训练：([\d.]+) → ([\d.]+)', r'Train: \1 → \2'),
        (r'留出：([\d.]+) → ([\d.]+)', r'Held out: \1 → \2'),
        (r'裁剪后梯度：([+−\-]?[\d.]+)', r'Clipped gradient: \1'),
        (r'实际更新：([+−\-]?[\d.]+)', r'Actual update: \1'),
        (r'同一组权重 θ，(\d+)次前向都不变', r'Same θ for all \1 forward passes'),
        (r'红：([\d.]+)', r'红: \1'),
        (r'其余候选合计 ≈ ([\d.]+)', r'All other candidates ≈ \1'),
        (r'未列候选合计 ≈ ([\d.]+)', r'Unlisted candidates ≈ \1'),
        (r'精确匹配：训练(\d+)/(\d+)', r'Exact match: train \1/\2'),
        (r'留出(\d+)/(\d+)：同一事实，另一问法', r'Held out \1/\2: same facts, new wording'),
        (r'未匹配示例：(.*)', r'Unmatched example: \1'),
        (r'(\d+)个目标，loss=([\d.]+)', r'\1 targets, loss=\2'),
    ):
        if re.fullmatch(pattern, value):
            return re.sub(pattern, replacement, value)
    return None


def translated(value: str) -> str:
    label = recorded_label(value)
    if label is not None:
        return label
    if value in TRANSLATIONS:
        return TRANSLATIONS[value]
    if value in PRESERVED or not CJK.search(value):
        return value
    for pattern, replacement in (
        (r'特征(\d+)、(\d+)', r'Features \1, \2'),
        (r'特征(\d+)', r'F\1'),
        (r'位置(\d+)', r'Pos \1'),
        (r'头(\d+)', r'Head \1'),
        (r'位置差：([\d.]+)格', r'Position gap: \1'),
        (r'原始点积：(-?[\d.]+)', r'Raw dot product: \1'),
    ):
        if re.fullmatch(pattern, value):
            return re.sub(pattern, replacement, value)
    raise ValueError(f'Untranslated display text: {value!r}')


def localname(element):
    return element.tag.split('}')[-1] if isinstance(element.tag, str) else ''


def number(value, default=0):
    match = re.match(r'^\s*(-?[\d.]+)', value or '')
    return float(match[1]) if match else default


def style_dict(element):
    return dict(part.split(':', 1) for part in element.get('style', '').split(';') if ':' in part)


def font_size(element):
    style = style_dict(element)
    if element.get('font-size'):
        return number(element.get('font-size'), 32)
    if 'font-size' in style:
        return number(style['font-size'], 32)
    match = re.search(r'([\d.]+)px', style.get('font', ''))
    return float(match[1]) if match else 32


def anchor(element):
    return element.get('text-anchor', style_dict(element).get('text-anchor', 'start')).strip()


@lru_cache(maxsize=128)
def font(size, chinese=False, bold=False):
    choices = (['/System/Library/Fonts/Hiragino Sans GB.ttc',
                'C:/Windows/Fonts/msyh.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
               if chinese else (['/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                                 'C:/Windows/Fonts/arialbd.ttf',
                                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else []) + ['/System/Library/Fonts/Supplemental/Arial.ttf',
                                'C:/Windows/Fonts/arial.ttf',
                                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for choice in choices:
        if Path(choice).exists():
            return ImageFont.truetype(choice, int(round(size * 4)))
    raise RuntimeError('Install a Latin font and a CJK font before rendering figures.')


def width(value, size, chinese_style=False, bold=False):
    if chinese_style:
        return font(size, True).getlength(value) / 4
    return sum(font(size, bool(CJK.search(chunk)), bold).getlength(chunk) / 4
               for chunk in re.findall(r'[\u4e00-\u9fff]+|[^\u4e00-\u9fff]+', value))


def text_bounds(element, value, size):
    x, y = number(element.get('x')), number(element.get('y'))
    w = width(value, size, chinese_style=True)
    a = anchor(element)
    left = x - w / 2 if a == 'middle' else x - w if a == 'end' else x
    return left, y - size * .82, left + w, y + size * .15


def set_size(element, size):
    element.set('font-size', f'{size:.2f}'.rstrip('0').rstrip('.'))
    style = style_dict(element)
    if 'font' in style:
        style['font'] = re.sub(r'[\d.]+px', f'{size:g}px', style['font'], count=1)
        style['font'] = re.sub(r"'Hiragino Sans GB'", 'Arial', style['font'])
    if 'font-size' in style:
        style['font-size'] = f'{size:g}px'
    if style:
        element.set('style', ';'.join(f'{k}:{v}' for k, v in style.items()))


def wrap_words(value, max_width, size, bold=False):
    lines = []
    current = ''
    for word in value.split():
        candidate = (current + ' ' + word).strip()
        if current and width(candidate, size, bold=bold) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def translate_svg(markup: str, source_name: str, *, footer=True):
    root = ET.fromstring(markup)
    view = [float(v) for v in root.get('viewBox').split()]
    canvas_w, canvas_h = view[2:]
    # First-lesson static figures have a 1.5× wrapper around a 720-unit layout.
    mini = canvas_w == 1080 and 'scale(1.5)' in markup
    layout_w = 720 if mini else canvas_w
    parents = {child: parent for parent in root.iter() for child in parent}
    texts = [e for e in root.iter() if localname(e) == 'text']
    old = {id(e): ''.join(e.itertext()) for e in texts}
    sizes = {id(e): font_size(e) for e in texts}
    bounds = {id(e): text_bounds(e, old[id(e)], sizes[id(e)]) for e in texts}
    rects = [e for e in root.iter() if localname(e) == 'rect' and
             number(e.get('width')) < layout_w * .98]
    warnings = []
    if source_name == 'intro/03-输入与微调.svg':
        colors = {'#f6faf5':'#FFFFFF', '#18343d':'#222A35',
                  '#3269ae':'#3267A4', '#8052ac':'#8056A5',
                  '#c55216':'#8056A5', '#236b57':'#187B79',
                  '#607177':'#606C7B', '#cfddd6':'#C5CDD7'}
        for e in root.iter():
            for attribute in ('fill', 'stroke'):
                if e.get(attribute) in colors:
                    e.set(attribute, colors[e.get(attribute)])
    # The flow legend originally occupies only the left two thirds of its
    # canvas. Spread it across the 1080-unit English animation canvas.
    if canvas_w == 1080 and canvas_h == 1500:
        for e in texts:
            if number(e.get('y')) == 1480:
                if old[id(e)] == '参数': e.set('x', '466')
                if old[id(e)] == '输出': e.set('x', '806')
                set_size(e, 42)
                sizes[id(e)] = 42
        for e in root.iter():
            if localname(e) == 'path':
                d = e.get('d', '')
                if d == 'M300 1468 H330': e.set('d', 'M420 1468 H450')
                if d == 'M536 1468 H566': e.set('d', 'M760 1468 H790')
        bounds = {id(e): text_bounds(e, old[id(e)], sizes[id(e)]) for e in texts}
    # Replace the old vertical four-character instruction with one English label.
    if source_name.endswith('00-introduction/01-生成与学习.svg'):
        for e in list(texts):
            if old[id(e)] in {'再', '算', '一', '次'}:
                if old[id(e)] == '再':
                    e.text = 'Repeat'
                    e.set('x', '615'); e.set('y', '538')
                    e.set('transform', 'rotate(-90 615 538)')
                    set_size(e, 28)
                else:
                    parents[e].remove(e)
                texts.remove(e)
    for e in root.iter():
        if e.get('font-family'):
            e.set('font-family', FONT)
        if localname(e) == 'style' and e.text:
            e.text = re.sub(r'font-family:[^;}]+', f'font-family:{FONT}', e.text)
    for e in texts:
        original = old[id(e)]
        value = translated(original)
        if source_name.startswith('12-') and original in {'头0', '头1'}:
            value = 'H0' if original == '头0' else 'H1'
        if source_name.endswith('20-full-workflow/03-全流程.svg'):
            if original == '预测': value = 'Predict'
            if original == '反向': value = 'Grad'
        if source_name.endswith('17-pretraining/01-机制.svg') and original == '每50步：完整评估':
            value = 'Full eval every 50 steps'
        if value == original:
            continue
        for child in list(e):
            e.remove(child)
        e.text = value
        if not e.get('x') or not e.get('y'):
            continue
        x, y, size = number(e.get('x')), number(e.get('y')), sizes[id(e)]
        a = anchor(e)
        bold = number(e.get('font-weight', '400')) >= 600
        left, right = 22.0, layout_w - 22.0
        if source_name.endswith('16-transformer/03-公开模型.svg'):
            # Matplotlib uses a 432pt coordinate system and its own transform.
            # The source is regenerated below to avoid fitting rotated labels.
            continue
        containing = []
        for r in rects:
            rx, ry, rw, rh = (number(r.get(k)) for k in ('x', 'y', 'width', 'height'))
            if rx <= x <= rx + rw and ry + size * .45 <= y <= ry + rh - 2:
                containing.append((rw * rh, rx + 10, rx + rw - 10, rh))
        if containing:
            _, left, right, _ = min(containing)
        # Preserve space between labels that share a row, even in different phases.
        for other in texts:
            if other is e or abs(number(other.get('y')) - y) > min(size, sizes[id(other)]) * .36:
                continue
            l, _, r, _ = bounds[id(other)]
            ox = number(other.get('x'))
            if a == 'middle' and anchor(other) == 'middle' and abs(ox-x) > 1:
                if ox > x: right = min(right, (x+ox)/2 - 8)
                else: left = max(left, (x+ox)/2 + 8)
            elif ox > x + 1 and l > x:
                right = min(right, l - 12)
            elif ox < x - 1 and r < x:
                left = max(left, r + 12)
        available = (2 * min(x - left, right - x) if a == 'middle'
                     else x - left if a == 'end' else right - x)
        available = max(available, 45)
        requested = width(value, size, bold=bold)
        if requested <= available:
            continue
        # Keep labels readable. Dense labels may wrap within their existing box.
        minimum = max(24, size * .76) if size >= 28 else size * .88
        # Font hinting rounds pixel sizes; reserve 2% so rounding cannot turn
        # an otherwise valid one-line heading into an unnecessary second line.
        fitted = max(minimum, size * available / max(requested, 1) * .98)
        set_size(e, fitted)
        if width(value, fitted, bold=bold) > available + 1:
            pieces = wrap_words(value, available, fitted, bold=bold)
            if len(pieces) <= 2 and all(width(line, fitted, bold=bold) <= available + 1 for line in pieces):
                e.text = None
                e.set('y', f'{y - (len(pieces)-1) * fitted * .53:g}')
                for index, line in enumerate(pieces):
                    t = ET.SubElement(e, f'{{{NS}}}tspan', {'x': e.get('x'), 'dy': '0' if index == 0 else f'{fitted*1.08:g}'})
                    t.text = line
                warnings.append({'text': value, 'action': 'wrapped', 'x': x, 'y': y, 'width': available})
            else:
                warnings.append({'text': value, 'action': 'needs-review', 'x': x, 'y': y, 'width': available})
    # Accessibility title is translated independently of the visible SVG title.
    display = next(((''.join(e.itertext())) for e in texts if ''.join(e.itertext()).strip()), 'Course diagram')
    root.set('aria-label', display)
    root.set('lang', 'en')
    # An English explanation makes deliberately retained Chinese examples explicit.
    visible_cjk = any(CJK.search(''.join(e.itertext())) for e in texts)
    if footer and visible_cjk:
        extra = 70 if canvas_w == 720 else 90
        root.set('viewBox', f'0 0 {canvas_w:g} {canvas_h+extra:g}')
        root.set('width', '1080')
        root.set('height', str(round(1080 * (canvas_h+extra) / canvas_w)))
        note = ET.SubElement(root, f'{{{NS}}}g', {'font-family': FONT})
        ET.SubElement(note, f'{{{NS}}}rect', {'x':'0','y':f'{canvas_h:g}', 'width':f'{canvas_w:g}', 'height':f'{extra:g}', 'fill':'white'})
        line = ET.SubElement(note, f'{{{NS}}}text', {'x':f'{canvas_w/2:g}', 'y':f'{canvas_h+extra*.62:g}', 'font-size': '24' if canvas_w==720 else '34', 'fill':'#606C7B','text-anchor':'middle'})
        line.text = 'Chinese text is kept from the original example.'
    return ET.tostring(root, encoding='unicode'), warnings


def render(svg: Path, png: Path | None = None, width=1080):
    subprocess.run(['rsvg-convert', '--width', str(width), '--output', str(png or svg.with_suffix('.png')), str(svg)], check=True)


def native_plot_figures():
    """Run original plotting functions into temp dirs, then translate Text artists.

    Intercepting Figure.savefig before the original function closes its figure
    preserves every curve, value, axis, random seed and experiment record.
    Only labels, layout and SVG text output change.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    import make_plots
    import loss_surface
    import retention_figure
    import reference_figures
    plot_text = {
        'ReLU：输入是 z':'ReLU: input z', '输入 z':'Input z', '输出':'Output',
        '转折发生在 z = 0':'The bend is at z = 0',
        '整个神经元：输入是 x':'Full neuron: input x', '只乘加：0':'Affine only: 0',
        '目标：1':'Target: 1', '输入 x':'Input x',
        '先算 z=x-1；转折移到 x=1':'z=x−1 moves the bend to x=1',
        '权重 w':'Weight w', '偏置 b':'Bias b', '损失 L':'Loss L',
        '两个参数，决定同一个损失':'Two parameters, one loss',
        'b=0：前面只改w的曲线':'b=0: vary w only',
        'w、b一起更新的路径':'Update w and b together',
        '起点 L=16':'Start: L=16', '一起更新后 L=0':'After update: L=0',
        '原学习率\n0.001':'Original LR\n0.001',
        '小学习率\n0.0001':'Lower LR\n0.0001',
        '12问答\n＋4原正文':'12 Q&A\n+ 4 old texts',
        '保住旧续写之后':'Retaining familiar text',
        '新问法还需要单独检验':'does not guarantee new answers',
        '熟悉续写 · 每次256题':'Familiar continuations · 256 each',
        '留出问答 · 每次8题':'Held-out Q&A · 8 each',
        '种子42':'Seed 42', '种子43':'Seed 43', '种子44':'Seed 44',
        '正确＝文本完全一致，并且选到EOS':'Correct = exact text match and EOS',
        '同一预训练权重 · 300步 · 每批16条':'Same pretrained weights · 300 steps · batch 16',
    }
    original_savefig = Figure.savefig
    written = set()
    def english_savefig(fig, fname, *args, **kwargs):
        source = Path(fname)
        if source.suffix != '.svg':
            return
        if source.name in written:
            return
        written.add(source.name)
        folder = ('01-neuron' if source.stem.startswith(('04-ReLU', '08-激活')) else
                  '04-gradients' if source.stem.startswith('03-两个') else
                  '19-fine-tuning' if source.stem.startswith('03-微调') else
                  '16-transformer')
        out = ARTICLES / folder / 'images/en' / source.name
        out.parent.mkdir(parents=True, exist_ok=True)
        for artist in fig.findobj(Text):
            value = artist.get_text()
            english = plot_text.get(value, TRANSLATIONS.get(value, value))
            if CJK.search(english) and value not in PRESERVED:
                raise ValueError(f'Untranslated plot label {value!r}')
            artist.set_text(english)
            artist.set_fontfamily('DejaVu Sans')
            artist.set_fontweight('bold' if number(str(artist.get_fontweight())) >= 600 else 'normal')
        if folder == '01-neuron':
            for ax in fig.axes:
                ax.yaxis.label.set_fontsize(18)
                ax.yaxis.set_label_coords(-.10, .5)
                ax.yaxis.label.set_rotation(90)
            for artist in fig.texts:
                if artist.get_position()[1] < .1:
                    artist.set_fontsize(18)
        elif folder == '04-gradients':
            for artist in fig.findobj(Text):
                if artist.get_text().startswith(('Start:', 'After update:')):
                    artist.set_fontsize(12)
        elif folder == '19-fine-tuning':
            for artist in fig.texts:
                if artist.get_text() == 'Retaining familiar text': artist.set_fontsize(23)
                elif artist.get_position()[1] > .8: artist.set_fontsize(17)
                elif artist.get_position()[1] < .1: artist.set_fontsize(13)
            for ax in fig.axes:
                ax.set_xticks(range(3), ['Original LR\n0.001', 'Lower LR\n0.0001', '12 Q&A\n+ 4 old texts'])
                ax.title.set_fontsize(17)
                ax.tick_params(axis='x', labelsize=15)
                for label in ax.get_xticklabels():
                    label.set_fontfamily('DejaVu Sans')
            for legend in fig.legends:
                for label in legend.get_texts(): label.set_fontsize(14)
        elif folder == '16-transformer':
            for artist in fig.texts:
                if artist.get_fontsize() >= 20: artist.set_fontsize(20)
                elif len(artist.get_text()) > 45: artist.set_fontsize(14)
            for ax in fig.axes:
                ax.xaxis.label.set_fontsize(16); ax.yaxis.label.set_fontsize(16)
        plt.rcParams['svg.fonttype'] = 'none'
        original_savefig(fig, out, facecolor='white')
        render(out)
    Figure.savefig = english_savefig
    try:
        with tempfile.TemporaryDirectory(prefix='llm-english-plots-') as work:
            make_plots.IMAGES = Path(work)
            make_plots.style()
            make_plots.relu()
            make_plots.activation_need()
            loss_surface.static_figure(Path(work), loss_surface.read(4))
            retention_figure.IMAGES = Path(work)
            retention_figure.main()
            # The public-model heatmap has rotated native plot labels.
            # main also calls the SVG helper for the KV-cache figure; that
            # figure is already translated above, so suppress its original write.
            original_reference_save = reference_figures.save
            reference_figures.save = lambda *a, **kw: None
            try:
                reference_figures.main()
            finally:
                reference_figures.save = original_reference_save
    finally:
        Figure.savefig = original_savefig
        plt.close('all')


def static_figures():
    report = {}
    for source in sorted(ARTICLES.glob('*/images/*.svg')):
        key = f'{source.parent.parent.name}/{source.name}'
        if key in OUTLINED or key == '16-transformer/03-公开模型.svg':
            continue
        markup, warnings = translate_svg(source.read_text(encoding='utf-8'), key)
        out = source.parent / 'en' / source.name
        out.parent.mkdir(exist_ok=True)
        out.write_text(markup, encoding='utf-8')
        render(out)
        if warnings:
            report[key] = warnings
    native_plot_figures()
    return report


def referenced_images():
    refs = []
    for article in sorted(ARTICLES.glob('*/README.md')):
        for target in re.findall(r'!\[[^]]*\]\(([^)]+)\)', article.read_text(encoding='utf-8')):
            if not target.startswith(('http:', 'https:', 'data:')):
                refs.append((article.parent / target).resolve())
    return refs


def audit(strict=False):
    refs = referenced_images()
    missing = [str(p.relative_to(COLUMN)) for p in set(refs) if not (p.parent/'en'/p.name).exists()]
    assets = list(ARTICLES.glob('*/images/en/*'))
    errors = []
    checked = 0
    for source in sorted(ARTICLES.glob('*/images/*.svg')):
        target = source.parent/'en'/source.name
        if not target.exists():
            errors.append(f'Missing SVG: {target.relative_to(COLUMN)}')
            continue
        src, dst = ET.parse(source).getroot(), ET.parse(target).getroot()
        src_phases = Counter(e.get('data-phase') for e in src.iter() if e.get('data-phase') is not None)
        dst_phases = Counter(e.get('data-phase') for e in dst.iter() if e.get('data-phase') is not None)
        if src_phases != dst_phases:
            errors.append(f'Changed phase groups: {source.name}')
        before = Counter(''.join(e.itertext()) for e in src.iter() if localname(e)=='text')
        after = Counter(''.join(e.itertext()) for e in dst.iter() if localname(e)=='text')
        for value, count in before.items():
            if value in PRESERVED or (value.strip() and not CJK.search(value)):
                if after[value] < count:
                    errors.append(f'Changed sample / numeric text: {source.parent.parent.name}/{source.name}: {value}')
        checked += 1
    durations = {}
    for p in assets:
        if p.suffix == '.png':
            with Image.open(p) as im:
                if im.width != 1080: errors.append(f'Unexpected PNG width: {p}')
                im.verify()
        elif p.suffix == '.gif':
            with Image.open(p) as im:
                duration = 0
                for frame in range(im.n_frames):
                    im.seek(frame)
                    duration += im.info.get('duration', 0)
                durations[p.parents[2].name] = duration/1000
                if im.n_frames < 2 or duration <= 0:
                    errors.append(f'Invalid animation: {p}')
            original = p.parent.parent/p.name
            with Image.open(original) as im:
                original_duration = 0
                for frame in range(im.n_frames):
                    im.seek(frame)
                    original_duration += im.info.get('duration',0)
                if abs(original_duration-duration) > 100:
                    errors.append(f'Animation timing differs: {p.parents[2].name}')
    report = {'references': len(refs), 'unique_referenced_assets': len(set(refs)),
              'referenced_png': sum(p.suffix == '.png' for p in set(refs)),
              'referenced_gif': sum(p.suffix == '.gif' for p in set(refs)),
              'english_svg': sum(p.suffix == '.svg' for p in assets),
              'english_png': sum(p.suffix == '.png' for p in assets),
              'english_gif': sum(p.suffix == '.gif' for p in assets),
              'english_mp4': sum(p.suffix == '.mp4' for p in assets),
              'svg_content_checks': checked, 'gif_duration_seconds': durations,
              'missing': sorted(missing), 'errors':errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if strict and (missing or errors):
        raise SystemExit(1)
    return report


def build_animations():
    """Use the exact existing frame math and phase timings at GIF frame rate."""
    scenes = json.loads((HERE/'animation/course-scenes.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='llm-english-frames-') as work_name:
        work = Path(work_name)
        # Geometric movement uses the original native frame generators. This
        # temporary bridge only chooses frames; translate_svg handles labels.
        bridge = work / 'frames.mjs'
        bridge.write_text('''
import {writeFile,mkdir,readFile} from 'node:fs/promises';
import path from 'node:path';
import {svg} from SOURCE_NEURON;
import {headSplitFrame,ropeFrame} from SOURCE_MECHANISMS;
const work=process.argv[2];
const data=JSON.parse(await readFile(DATA,'utf8'));
for(const [id,total,draw] of [
  [1,420,f=>svg('flow',data,Math.min(5,Math.floor(f/70)),Math.min(1,(f%70)/45))],
  [12,360,headSplitFrame],[13,300,ropeFrame]]) {
  const dir=path.join(work,'raw-'+id);await mkdir(dir);
  for(let f=0;f<total;f+=3)
    await writeFile(path.join(dir,String(f/3).padStart(5,'0')+'.svg'),draw(f));
}
'''.replace('SOURCE_NEURON', json.dumps((HERE/'animation/src/neuron.mjs').as_uri()))
            .replace('SOURCE_MECHANISMS', json.dumps((HERE/'animation/src/mechanisms.mjs').as_uri()))
            .replace('DATA', json.dumps(str(HERE/'animation/src/lesson01.json'))), encoding='utf-8')
        subprocess.run(['node', str(bridge), str(work)], check=True)
        jobs = [{'number':1,'folder':'01-neuron'}] + scenes
        for job in jobs:
            n, folder = job['number'], job['folder']
            target = ARTICLES/folder/'images/en'
            target.mkdir(exist_ok=True)
            frame_dir = work / f'render-{n}'
            frame_dir.mkdir()
            raws = sorted((work/f'raw-{n}').glob('*.svg')) if n in (1,12,13) else []
            if raws:
                for index, source in enumerate(raws):
                    markup, warnings = translate_svg(source.read_text(encoding='utf-8'), f'animation-{n}', footer=False)
                    if any(row['action']=='needs-review' for row in warnings):
                        raise ValueError(f'Animation {n} has text overflow: {warnings}')
                    svg = frame_dir/f'{index:05d}.svg'
                    svg.write_text(markup, encoding='utf-8')
                    render(svg, width=720 if n==1 else 648)
                    svg.unlink()
            else:
                frames = job['frames']
                # Same two-second stages and final two-second hold as Course.tsx.
                for index in range((len(frames)+1)*20):
                    stage = min(len(frames)-1,index//20)
                    current = frames[stage]
                    source = COLUMN / current['figure']
                    markup = (source.parent/'en'/source.name).read_text(encoding='utf-8')
                    phases = set(map(int,re.findall(r'data-phase="(\d+)"',markup)))
                    progress = min(1,(index*3-stage*60)/14)
                    css = ''.join(f'[data-phase="{p}"]{{opacity:{1 if p<current["phase"] else .12+progress*.88 if p==current["phase"] else .12:g}}}' for p in phases)
                    markup = markup.replace('</defs>',f'</defs><style>{css}</style>')
                    svg = frame_dir/f'{index:05d}.svg'
                    svg.write_text(markup, encoding='utf-8')
                    render(svg,width=648)
                    svg.unlink()
            name = '07-神经元六步计算' if n==1 else '过程'
            # Encode both formats before replacing either existing English file.
            gif,mp4 = work/f'{n}.gif',work/f'{n}.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                            '-framerate','10','-i',str(frame_dir/'%05d.png'),
                            '-filter_complex','split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
                            '-loop','0',str(gif)],check=True)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                            '-framerate','10','-i',str(frame_dir/'%05d.png'),
                            '-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2',
                            '-c:v','libx264','-pix_fmt','yuv420p','-crf','20',
                            '-movflags','+faststart',str(mp4)],check=True)
            shutil.copyfile(gif,target/f'{name}.gif')
            shutil.copyfile(mp4,target/f'{name}.mp4')
            print(f'English animation {n:02d}: {len(list(frame_dir.glob("*.png")))/10:g}s',flush=True)
            shutil.rmtree(frame_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--animations', action='store_true', help='Also regenerate all nine GIFs')
    parser.add_argument('--only-animations', action='store_true')
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--report', type=Path, help='Optional review report (prefer a temp directory)')
    args = parser.parse_args()
    if args.audit:
        return audit(strict=True)
    warnings = {} if args.only_animations else static_figures()
    if args.animations or args.only_animations:
        build_animations()
    result = audit()
    if args.report:
        args.report.write_text(json.dumps({'assets':result,'layout_review':warnings},ensure_ascii=False,indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()

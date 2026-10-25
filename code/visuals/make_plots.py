"""绘制明确标识的数学例子与真实日志；训练曲线不平滑、不补造数据点。"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

CODE = Path(__file__).resolve().parents[1]
COLUMN = CODE.parent
IMAGES = COLUMN / 'chapters/01-neuron/images'
BG, INK, TEAL, PURPLE, BLUE = '#FFFFFF', '#222A35', '#187B79', '#8056A5', '#3267A4'


def setup_font():
    candidates = [Path('/System/Library/Fonts/Hiragino Sans GB.ttc'),
                  Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts/msyh.ttc']
    for candidate in candidates:
        if candidate.exists():
            font_manager.fontManager.addfont(str(candidate))
            plt.rcParams['font.family'] = font_manager.FontProperties(fname=candidate).get_name()
            return
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ['Noto Sans CJK SC', 'Microsoft YaHei', 'PingFang SC', 'Heiti SC']:
        if name in available:
            plt.rcParams['font.family'] = name
            return
    raise RuntimeError('请安装或指定一款中文字体后再制图；不使用缺字方框代替。')


def style():
    setup_font()
    plt.rcParams.update({'figure.facecolor': BG, 'axes.facecolor': BG,
                         'text.color': INK, 'axes.labelcolor': INK,
                         'xtick.color': INK, 'ytick.color': INK,
                         'axes.edgecolor': '#A3ACB8', 'font.size': 26,
                         'font.weight': 300, 'axes.labelweight': 300, 'axes.titleweight': 300,
                         'axes.unicode_minus': False, 'svg.fonttype': 'path'})


def relu():
    example = json.loads((CODE / 'artifacts/lesson01.json').read_text(encoding='utf-8'))['activation_example']
    fig = plt.figure(figsize=(6, 6), dpi=180)
    fig.text(.06, .94, 'ReLU：输入是 z', fontsize=24)
    ax = fig.add_axes([.17, .22, .78, .58])
    z = np.linspace(-1.5, 1.6, 311)
    ax.plot(z, np.maximum(0, z), color=TEAL, lw=2.5)
    ax.scatter(example['relu']['before_relu'], example['relu']['outputs'],
               facecolors=BG, edgecolors=TEAL, linewidths=2, s=85, zorder=4)
    ax.annotate('-1 → 0', (-1, 0), xytext=(-1.3, .8), color=TEAL, fontsize=22,
                arrowprops={'arrowstyle': '->', 'color': TEAL, 'lw': 1.3})
    ax.annotate('1 → 1', (1, 1), xytext=(.18, 1.32), color=TEAL, fontsize=22,
                arrowprops={'arrowstyle': '->', 'color': TEAL, 'lw': 1.3})
    ax.set(xlim=(-1.5, 1.6), ylim=(-.2, 1.6), xticks=[-1, 0, 1], yticks=[0, 1])
    ax.set_xlabel('输入 z', fontsize=22)
    ax.set_ylabel('输出', rotation=0, labelpad=18, fontsize=22)
    ax.tick_params(labelsize=22)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.14)
    fig.text(.15, .045, '转折发生在 z = 0', fontsize=22, color=TEAL)
    for suffix in ['png', 'svg']:
        fig.savefig(IMAGES / ('04-ReLU怎样处理正负数.' + suffix), dpi=180)
    plt.close(fig)


def activation_need():
    example = json.loads((CODE / 'artifacts/lesson01.json').read_text(encoding='utf-8'))['activation_example']
    fig = plt.figure(figsize=(6, 6), dpi=180)
    fig.text(.06, .94, '整个神经元：输入是 x', fontsize=24)
    ax = fig.add_axes([.17, .22, .78, .58])
    x = np.linspace(-.2, 2.25, 491)
    affine, nonlinear = example['affine'], example['relu']
    ax.plot(x, affine['weight'] * x + affine['bias'], color=BLUE, ls='--', lw=2.5)
    ax.plot(x, np.maximum(0, nonlinear['weight'] * x + nonlinear['bias']), color=PURPLE, lw=2.5)
    ax.scatter(example['inputs'], example['targets'], facecolors=BG, edgecolors=TEAL,
               linewidths=2, s=90, zorder=5)
    ax.scatter([2], [affine['outputs'][-1]], color=BLUE, marker='x', s=85, lw=2, zorder=5)
    ax.vlines(2, 0, 1, color='#A3ACB8', ls=':', lw=1.3)
    ax.text(0, .65, '只乘加：0', color=BLUE, fontsize=22)
    ax.annotate('目标：1', (2, 1), xytext=(.95, 1.25), color=TEAL, fontsize=22,
                arrowprops={'arrowstyle': '->', 'color': TEAL, 'lw': 1.3})
    ax.set(xlim=(-.25, 2.3), ylim=(-.2, 1.6), xticks=[0, 1, 2], yticks=[0, 1])
    ax.set_xlabel('输入 x', fontsize=22)
    ax.set_ylabel('输出', rotation=0, labelpad=18, fontsize=22)
    ax.tick_params(labelsize=22)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.14)
    fig.text(.06, .045, '先算 z=x-1；转折移到 x=1', fontsize=22, color=PURPLE)
    for suffix in ['png', 'svg']:
        fig.savefig(IMAGES / ('08-激活函数增加了什么.' + suffix), dpi=180)
    plt.close(fig)


def training():
    log = json.loads((CODE / 'artifacts/first_run/pretrain_log.json').read_text(encoding='utf-8'))
    fig, ax = plt.subplots(figsize=(12, 8), dpi=120)
    fig.subplots_adjust(left=.12, right=.95, top=.76, bottom=.19)
    fig.text(.05, .94, '真实预训练：训练集与留出集', fontsize=30)
    fig.text(.05, .865, '相同评估方式，保留两组原始记录。', fontsize=24, color='#606C7B')
    history = log['history']
    for key, label, color in [('train_loss', '训练集', BLUE), ('val_loss', '留出集', PURPLE)]:
        ax.plot([r['step'] for r in history], [r[key] for r in history], color=color,
                marker='o', ms=4, lw=2, linestyle='--' if key=='val_loss' else '-', label=label)
    ax.set(xlabel='参数更新次数', ylabel='预测错误的损失', xlim=(0, 1000), ylim=(0, 7))
    ax.legend(frameon=False, loc='upper right', fontsize=22)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(alpha=.14)
    fig.text(.05, .055, '实跑日志：pretrain_log.json · seed 42 · CPU · 每 50 步评估一次',
             fontsize=19, color='#606C7B')
    destination = CODE / 'artifacts/first_run/预训练曲线.png'
    fig.savefig(destination, dpi=120)
    plt.close(fig)


if __name__ == '__main__':
    IMAGES.mkdir(parents=True, exist_ok=True)
    style()
    relu()
    activation_need()
    training()
    print('ReLU 数学图、非线性能力对照与真实预训练曲线已生成。')

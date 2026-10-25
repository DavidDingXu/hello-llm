"""从固定三方法、三种子的真实记录绘制微调取舍，不补造或挑选数据点。"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from make_plots import setup_font

CODE = Path(__file__).resolve().parents[1]
IMAGES = CODE.parent / 'chapters/19-fine-tuning/images'


def main():
    report = json.loads((CODE / 'artifacts/retention_experiment.json').read_text(encoding='utf-8'))
    setup_font()
    plt.rcParams.update({'font.size': 16, 'font.weight': 300, 'axes.titleweight': 300, 'axes.unicode_minus': False,
                         'svg.fonttype': 'path', 'text.color': '#222A35',
                         'axes.labelcolor': '#222A35', 'xtick.color': '#222A35',
                         'ytick.color': '#606C7B'})
    methods = ['original_lr', 'lower_lr', 'mixed_replay']
    labels = ['原学习率\n0.001', '小学习率\n0.0001', '12问答\n＋4原正文']
    seeds = [42, 43, 44]
    colors = ['#3267A4', '#8056A5', '#187B79']
    markers = ['o', '^', 's']
    fig, axes = plt.subplots(2, 1, figsize=(6, 10.2), dpi=180)
    fig.subplots_adjust(left=.15, right=.95, top=.75, bottom=.20, hspace=.75)
    fig.text(.06, .953, '保住旧续写之后', fontsize=23, weight=600)
    fig.text(.06, .906, '新问法还需要单独检验', fontsize=19, color='#187B79')
    title_artists = []
    for ax, group, title in zip(axes, ['old_continuation', 'sft_val'],
                                ['熟悉续写 · 每次256题', '留出问答 · 每次8题']):
        for i, seed in enumerate(seeds):
            values = []
            for method in methods:
                trial = next(t for t in report['trials'] if t['condition'] == method and t['seed'] == seed)
                result = trial['evaluation'][group]
                values.append(100 * result['complete_exact_count'] / result['sample_count'])
            ax.scatter([x + (i - 1) * .14 for x in range(3)], values,
                       marker=markers[i], s=60, color=colors[i], zorder=3, label=f'种子{seed}')
        title_artists.append(ax.set_title(title, loc='left', fontsize=18, pad=15))
        ax.set(xlim=(-.45, 2.45), ylim=(-3, 106), yticks=[0, 25, 50, 75, 100])
        ax.set_yticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=14)
        ax.set_xticks(range(3), labels, fontsize=15)
        ax.tick_params(axis='both', length=0, pad=8)
        ax.grid(axis='y', color='#DDE2E8', linewidth=.8)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.spines['bottom'].set_color('#C5CDD7')
    handles, legend_labels = axes[0].get_legend_handles_labels()
    legend = fig.legend(handles, legend_labels, loc='upper center', bbox_to_anchor=(.54, .865),
               ncol=3, frameon=False, fontsize=12, handletextpad=.2, columnspacing=.7)
    fig.text(.08, .058, '正确＝文本完全一致，并且选到EOS', fontsize=14)
    fig.text(.08, .025, '同一预训练权重 · 300步 · 每批16条', fontsize=13, color='#606C7B')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    assert not legend.get_window_extent(renderer).overlaps(title_artists[0].get_window_extent(renderer))
    for extension in ('png', 'svg'):
        fig.savefig(IMAGES / f'03-微调取舍.{extension}', dpi=180, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()

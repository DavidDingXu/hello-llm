"""第04讲：将同一平方损失绘制成供正文及媒体使用的静态三维曲面。

两个地面坐标是可调参数 w、b，高度是损失；不把高维模型画成空间物体。
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from figure_tools import COLUMN, read
from make_plots import style


def static_figure(directory, sample):
    """用本讲的输入、目标与初值绘图，保留 b=0 这条原有损失曲线。"""
    x, target, start = sample['x'], sample['target'], sample['w']
    style()
    plt.rcParams.update({'font.size': 15, 'mathtext.fontset': 'dejavusans'})
    w = np.linspace(0, 4, 25)
    b = np.linspace(-1, 3, 25)
    ww, bb = np.meshgrid(w, b)
    losses = (x * ww + bb - target) ** 2
    fig = plt.figure(figsize=(7.2, 7.6), dpi=150, facecolor='white')
    ax = fig.add_subplot(111, projection='3d', computed_zorder=False)
    ax.plot_surface(ww, bb, losses, color='#E1D8EB', alpha=.3,
                    linewidth=.3, edgecolor='#B7ADBF', shade=False, zorder=1)
    # b固定为0的截线，正是前面单独改变w时画出的抛物线。
    ax.plot(w, np.zeros_like(w), (x * w - target) ** 2,
            color='#3267A4', linewidth=3.5, zorder=3)
    initial_loss = (x * start - target) ** 2
    gw, gb = 2 * (x * start - target) * x, 2 * (x * start - target)
    # 在同一旧参数处算好两项梯度，再一起更新；路径高度仍由同一损失算出。
    t = np.linspace(0, .1, 40)
    path_w, path_b = start - t * gw, -t * gb
    path_loss = (x * path_w + path_b - target) ** 2
    ax.plot(path_w, path_b, path_loss, color='#187B79', linewidth=4, zorder=4)
    ax.plot([start, start], [0, 0], [0, initial_loss], color='#B4495A', linestyle=':', zorder=4)
    ax.scatter([start], [0], [initial_loss], color='#B4495A', s=70, depthshade=False, zorder=5)
    ax.scatter([path_w[-1]], [path_b[-1]], [path_loss[-1]],
               color='#187B79', s=70, depthshade=False, zorder=5)
    ax.text(start, 0, initial_loss + 4, f'起点 L={initial_loss:g}', color='#B4495A', fontsize=14, zorder=6)
    ax.text(path_w[-1], path_b[-1], 4, f'一起更新后 L={round(path_loss[-1], 6):g}', color='#187B79', fontsize=14, zorder=6)
    ax.set(xlim=(0, 4), ylim=(-1, 3), zlim=(0, 50))
    ax.set_xlabel('权重 w', fontsize=18, labelpad=14)
    ax.set_ylabel('偏置 b', fontsize=18, labelpad=14)
    ax.set_zlabel('损失 L', fontsize=18, labelpad=5)
    ax.set_xticks([0, 1, 2, 3, 4])
    ax.set_yticks([-1, 0, 1, 2, 3])
    ax.set_zticks([0, 16, 32, 48])
    ax.tick_params(labelsize=12)
    ax.view_init(elev=27, azim=-120)
    ax.set_box_aspect((1, 1, .9))
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((1, 1, 1, 0))
        axis._axinfo['grid']['color'] = '#E1E5EB'
    fig.suptitle('两个参数，决定同一个损失', fontsize=24, x=.5, y=.97,
                 color='#222A35', fontweight=600)
    fig.text(.5, .865, f'L = ({x:g}w + b - {target:g})²', ha='center', fontsize=22,
             color='#222A35', fontfamily='DejaVu Sans', fontweight=400)
    fig.legend(handles=[Line2D([0], [0], color='#3267A4', linewidth=3,
                             label='b=0：前面只改w的曲线'),
                        Line2D([0], [0], color='#187B79', linewidth=3,
                               label='w、b一起更新的路径')],
               loc='lower center', frameon=False, fontsize=14, bbox_to_anchor=(.5, .015))
    fig.subplots_adjust(left=.10, right=.93, bottom=.14, top=.81)
    fig.savefig(directory / '03-两个参数的损失曲面.png', facecolor='white')
    fig.savefig(directory / '03-两个参数的损失曲面.svg', facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    sample = read(4)
    directory = COLUMN / 'chapters/04-gradients/images'
    static_figure(directory, sample)
    # Interactive pages are generated bilingually by tensor3d/surface-build.mjs.

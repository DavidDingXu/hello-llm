"""公开权重实测图：注意力热图与KV缓存增长，读取保存的实际记录。"""
import json
from pathlib import Path
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from figure_tools import COLUMN, CODE, svg, text, rect, line, arrow, save, C


def main():
    record=json.loads((CODE/'artifacts/reference/qwen3_trace.json').read_text(encoding='utf-8'))
    choices=['/System/Library/Fonts/Hiragino Sans GB.ttc','C:/Windows/Fonts/msyh.ttc']
    font_path=next((p for p in choices if Path(p).exists()),None)
    if font_path:
        font_manager.fontManager.addfont(font_path)
        font=font_manager.FontProperties(fname=font_path).get_name()
    else:font='Noto Sans CJK SC'
    plt.rcParams.update({'font.family':font,'font.weight':300,'axes.unicode_minus':False,
                         'svg.fonttype':'none','font.size':21,'axes.spines.top':False,
                         'axes.spines.right':False,'text.color':C['ink'],'axes.labelcolor':C['ink']})
    weights=np.array(record['runs'][0]['attention_head0'])
    fig,ax=plt.subplots(figsize=(6,7.5),dpi=180)
    fig.subplots_adjust(left=.17,right=.88,top=.78,bottom=.26)
    image=ax.imshow(weights,vmin=0,vmax=1,cmap='Blues',aspect='equal',interpolation='nearest')
    ax.set_xticks([0,4,8,12,15]);ax.set_yticks([0,4,8,12,15]);ax.tick_params(labelsize=18,length=0,pad=8)
    ax.set_xlabel('被读取的位置 K',fontsize=22,labelpad=14)
    ax.set_ylabel('查询位置 Q',fontsize=22,labelpad=12)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.axhline(14.5,color=C['output'],lw=1.5);ax.axhline(15.5,color=C['output'],lw=1.5)
    fig.text(.08,.94,'公开权重的一次真实注意力',fontsize=24)
    fig.text(.08,.875,'Qwen3-0.6B · 第1层，第1头',fontsize=20,color=C['muted'])
    cax=fig.add_axes([.90,.32,.023,.34]);bar=fig.colorbar(image,cax=cax,ticks=[0,.5,1]);bar.ax.tick_params(labelsize=16,length=0)
    fig.text(.08,.075,'颜色越深，当前行分配的比例越大',fontsize=19,color=C['muted'])
    fig.text(.08,.025,'右上角为 0：前面的位置不能读未来',fontsize=19,color=C['muted'])
    directory=COLUMN/'chapters/16-transformer/images'
    fig.savefig(directory/'03-公开模型.png',facecolor='white')
    fig.savefig(directory/'03-公开模型.svg',facecolor='white')
    plt.close(fig)
    content=''
    for i,row in enumerate(record['runs']):
        base=200+i*250;n=row['cache_key_shape'][2];q=row['input_shape'][1]
        content+=text(36,base,'先读完整提示词' if i==0 else f'再输入一个新 token（第{i}次）',34)
        content+=text(36,base+53,f'新 Q：{q} 行    K/V 缓存：{n} 行',32,'muted')
        width=31
        for j in range(n):
            fill='#EBF5F3' if i==0 or j>=n-q else '#EDF3FA'
            stroke='output' if i==0 or j>=n-q else 'input'
            content+=rect(36+j*width,base+82,width-3,52,fill,stroke,4)
        content+=text(36,base+189,f'本次选中：{row["selected_token"]}',36,'output')
    content+=text(36,1235,'已算过的 K/V 留下，新的一行追加进来',32,'muted')
    content+=text(36,1290,'实际缓存：[1,8,位置数,128]',32,'input')
    save('18-generation','03-KV缓存',svg('新查询只算一行，旧 K/V 继续复用',
         '同一份公开权重，连续四次真实前向',content,1360))


if __name__=='__main__':main()

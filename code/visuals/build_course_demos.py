"""从有阶段标记的同一幅 SVG 生成离线步进页；与导出动画共用图元。"""
import json
from pathlib import Path
import re
from figure_tools import COLUMN, read

STEPS = {
 4:['损失曲线与当前参数点','当前位置的导数切线','学习率决定参数移动距离','小步更新后重新计算损失','对照较大学习率的新落点'],
 5:['保存选中路径的前向数值','标出各段局部变化率','逆序相乘，得到选中权重梯度','算齐全部参数的梯度','统一应用同一学习率','写回全部新参数','用新参数重新前向并计算损失'],
 10:['选出查询向量与各行K','点积后除以头宽度的平方根','Softmax把这一行归一化','用各比例乘对应V','逐坐标求和，得到新向量'],
 11:['读取原始分数表','把未来分数设为负无穷','Softmax后未来权重为0','只汇总可读取位置的V'],
 12:['逐位置读取四个特征','沿特征轴分成两个头','投影后各头独立计算注意力','按原位置拼接两个头的结果','输出投影混合各头的特征'],
 13:['从原点读取向量坐标','入门示意：旋转四分之一圈','真实频率：位置1旋转1弧度','按两坐标公式核对旋转结果'],
 18:[],
 19:['拼接提示词、答案与结束标记','对齐下一字符的输入与标签','忽略提示词标签，保留答案与EOS','七个有效目标汇入平均损失','梯度仍能沿上下文路径传回提示词']}

# 步进页保留静态计算分镜；这两组导出动画另用逐帧几何，不随重建丢失画幅。
MOTION = {
 12:{'motion_height':1800,'motion_summary':['索引格子同步移动，沿特征分组','每个头保留全部位置','按原位置拼回，数值不变']},
 13:{'motion_height':1800,'motion_summary':['Q位置1，K位置0，点积cos(1)','两个位置一起后移3格，点积不变','只让K前移一格，点积变为cos(2)']}}


STYLE='''*{box-sizing:border-box}body{margin:0;background:#fff;color:#222A35;font:17px/1.7 'Hiragino Sans GB','PingFang SC','Microsoft YaHei',Arial,sans-serif}main{max-width:940px;margin:auto;padding:32px 28px}header{display:flex;gap:22px;align-items:center;flex-wrap:wrap}h1{font-size:25px;margin:16px 0}a{color:#187B79;text-underline-offset:4px}.layout{display:grid;grid-template-columns:minmax(0,620px) 230px;gap:28px;align-items:start}.figure{width:100%;min-width:0}.figure svg{display:block;width:100%;height:auto}.controls{position:sticky;top:20px;padding:20px 0}button{font:inherit;min-height:44px;padding:7px 14px;border:1px solid #C5CDD7;background:white;color:#222A35;border-radius:6px;cursor:pointer}button:disabled{opacity:.35;cursor:default}button.primary{background:#187B79;color:white;border-color:#187B79}.buttons{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0}input[type=range]{width:100%;accent-color:#187B79}#caption{min-height:88px;color:#606C7B}.note{font-size:14px;color:#606C7B}@media(max-width:700px){main{padding:18px 18px}.layout{display:flex;flex-direction:column-reverse;gap:12px}.controls{position:static;width:100%;padding:0}#caption{min-height:0;margin:8px 0}.buttons{margin:12px 0}h1{font-size:22px}.note{margin:8px 0}}'''


def build():
    manifest=[]
    for number,captions in STEPS.items():
        folder=next((COLUMN/'chapters').glob(f'{number:02d}-*'))
        primary='02-验证.svg' if number==4 else '01-机制.svg'
        path=folder/'images'/primary
        selections=[]
        if number==5:
            selections=[(path,stage) for stage in [0,1,2]]
            selections += [(folder/'images/02-验证.svg',stage) for stage in range(4)]
        else:
            markup=path.read_text(encoding='utf-8')
            stages=sorted(set(map(int,re.findall(r'data-phase="(\d+)"',markup))))
            selections=[(path,stage) for stage in stages]
        if number==18:
            record=read(18)['greedy']
            captions=['读取前缀，模型参数保持固定']
            captions += [f'第 {i+1} 步：读取 {len(row["input_ids"])} 个编号，选出 {row["selected_token"]}' for i,row in enumerate(record['steps'])]
        if len(captions)!=len(selections):raise ValueError(f'{number}阶段说明数目不匹配')
        frames=[{'figure':str(p.relative_to(COLUMN)),'phase':phase,'caption':caption}
                for (p,phase),caption in zip(selections,captions)]
        payload_frames=[{**frame,'markup':(COLUMN/frame['figure']).read_text(encoding='utf-8')} for frame in frames]
        height=max(int(re.search(r'height="(\d+)"',f['markup']).group(1)) for f in payload_frames)
        phases=list(range(len(frames)))
        labels=captions
        title=next(line[2:] for line in (folder/'README.md').read_text(encoding='utf-8').splitlines() if line.startswith('# '))
        payload=json.dumps({'frames':payload_frames,'phases':phases,'labels':labels},ensure_ascii=False).replace('</','<\\/')
        page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 逐步演示</title><style>{STYLE}</style></head><body><main><header><a href="index.html">← 回到文章</a><a href="images/过程.mp4">清晰版动画</a><a href="{path.relative_to(folder)}">完整静态图</a></header><h1>{title}</h1><div class="layout"><div id="figure" class="figure"></div><section class="controls" aria-label="步骤控制"><label for="step">步骤 <span id="counter"></span></label><input id="step" type="range" min="0" max="{len(phases)-1}" value="0"><p id="caption" aria-live="polite"></p><div class="buttons"><button id="previous">上一步</button><button id="next">下一步</button><button id="play" class="primary">播放</button><button id="restart">重来</button></div><p class="note">数字与文章一致。可拖动步骤条，或暂停逐项核对。</p></section></div></main><script id="data" type="application/json">{payload}</script><script>
const data=JSON.parse(document.getElementById('data').textContent);
const figure=document.getElementById('figure');
const slider=document.getElementById('step'),caption=document.getElementById('caption');
let step=0,timer=null;
function show(index){{step=Math.max(0,Math.min(data.phases.length-1,index));slider.value=step;figure.innerHTML=data.frames[step].markup;document.getElementById('counter').textContent=`${{step+1}} / ${{data.phases.length}}`;caption.textContent=data.labels[step];for(const group of figure.querySelectorAll('[data-phase]')){{group.style.opacity=Number(group.dataset.phase)<=data.frames[step].phase?'1':'.12';}}document.getElementById('previous').disabled=step===0;document.getElementById('next').disabled=step===data.phases.length-1;}}
function stop(){{clearInterval(timer);timer=null;document.getElementById('play').textContent='播放';}}
slider.addEventListener('input',()=>{{stop();show(Number(slider.value));}});
document.getElementById('previous').onclick=()=>{{stop();show(step-1);}};
document.getElementById('next').onclick=()=>{{stop();show(step+1);}};
document.getElementById('restart').onclick=()=>{{stop();show(0);}};
document.getElementById('play').onclick=()=>{{if(timer){{stop();return;}}if(step===data.phases.length-1)show(0);document.getElementById('play').textContent='暂停';timer=setInterval(()=>{{if(step>=data.phases.length-1)stop();else show(step+1);}},2000);}};
show(0);
</script></body></html>'''
        (folder/'walkthrough.html').write_text(page,encoding='utf-8')
        manifest.append({'number':number,'folder':folder.name,'figure':str(path.relative_to(COLUMN)),
                         'height':height,'phases':phases,'frames':frames,'captions':labels,
                         **MOTION.get(number,{})})
    target=COLUMN/'code/visuals/animation/course-scenes.json'
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(manifest)} 个离线逐步演示已生成。')


if __name__=='__main__':build()

"""把真实训练回放数据嵌入离线页面；浏览器只展示记录，不在后台训练。

先运行 python -m lessons.training_replay，再执行本文件。
生成器读取已保存的训练记录，并生成可离线阅读的回放页面。
"""
import json

from figure_tools import CODE, COLUMN


HTML = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>一条短句，怎样改变模型？ · 训练全过程回放</title>
<style>
:root{color-scheme:light;--ink:#222A35;--muted:#606C7B;--line:#DDE2E8;--blue:#3267A4;--purple:#8056A5;--teal:#187B79;--red:#B4495A}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font:17px/1.8 'Hiragino Sans GB','PingFang SC','Microsoft YaHei',Arial,sans-serif}main{max-width:1040px;margin:auto;padding:40px 36px 60px}a{color:var(--teal);text-underline-offset:4px}small,.muted{color:var(--muted)}h1{font-size:34px;line-height:1.4;margin:20px 0 14px}h2{font-size:26px;line-height:1.5;margin:0 0 18px}h3{font-size:18px;margin:26px 0 8px}p{margin:14px 0}strong{color:#155F61;font-weight:650}code,.number{font-family:Menlo,Consolas,'Hiragino Sans GB',monospace;font-variant-numeric:tabular-nums}code{font-size:.9em;overflow-wrap:anywhere}.intro{max-width:760px}.phases{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin:28px 0;color:var(--purple);font-size:16px}.phases span{border-bottom:2px solid #D9CAE6;padding:3px 0}.phases b{color:#9BA7B4;font-weight:400}button{font:inherit;cursor:pointer;line-height:1.5;color:var(--ink);background:white;border:1px solid #B6C3CA;border-radius:4px;padding:9px 14px}button:disabled{opacity:.4;cursor:default}button:focus-visible,input:focus-visible{outline:3px solid var(--blue);outline-offset:3px}.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:28px 0 22px}.steps button{font-size:15px;text-align:left;padding:10px}.steps button span{color:var(--muted);font-size:12px;display:block}.steps button[aria-current=step]{background:#EDF6F5;border-color:var(--teal);color:var(--teal)}.stage{border-top:2px solid var(--teal);padding:28px 0 8px;min-height:440px}.eyebrow{display:block;color:var(--teal);font-size:14px;margin-bottom:10px}.sample{font-size:26px;line-height:1.7;background:#F4F7FB;padding:20px 24px;color:var(--blue);margin:22px 0}.flow{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0}.flow .node{padding:14px 18px;border:1px solid var(--line);font-size:16px;line-height:1.6}.flow .node small{display:block;font-size:13px}.flow .arrow{font-size:24px;color:#9BA7B4}.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin:24px 0}.metrics>div{padding:14px 0;border-top:1px solid var(--line)}.metrics small{display:block;font-size:14px}.metrics output{display:block;font-size:25px;color:var(--purple);overflow-wrap:anywhere;font-variant-numeric:tabular-nums}.formula{font-size:23px;color:var(--purple);margin:24px 0}.formula span{display:inline-block}.scroll-table{overflow:auto;max-width:100%;margin:22px 0}table{width:100%;border-collapse:collapse;font-size:15px}th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}th{font-weight:500;color:var(--muted);white-space:nowrap}td{font-variant-numeric:tabular-nums}.ignored{color:#929CAA}.target{color:var(--teal);font-weight:600}.token{display:inline-block;padding:3px 8px;background:#EDF2F8;color:var(--blue);margin:3px;font-size:16px}.bar-row{display:grid;grid-template-columns:70px 1fr 90px;align-items:center;gap:14px;margin:10px 0;font-size:16px}.bar-track{height:12px;background:#F0F2F6}.bar{height:100%;background:#9EB9D9;min-width:1px}.bar-row.correct .bar{background:var(--teal)}.bar-row.correct{color:var(--teal)}.bar-row .number{text-align:right;font-size:14px}.notice{border-left:3px solid var(--purple);padding:6px 18px;margin:24px 0;color:var(--muted);font-size:15px}.check{color:var(--teal)}.toolbar{display:flex;flex-wrap:wrap;gap:10px;margin:24px 0}.toolbar .primary{background:var(--teal);color:white;border-color:var(--teal)}.toolbar .right{margin-left:auto}input[type=range]{display:block;width:100%;accent-color:var(--teal);margin:18px 0}.chart{width:100%;height:260px;display:block;margin:20px 0}.legend{display:flex;gap:22px;font-size:14px}.legend span:before{content:'';display:inline-block;width:24px;height:3px;background:var(--color);vertical-align:middle;margin-right:6px}.compare{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin:24px 0}.compare>div{border-top:2px solid #D9CAE6;padding-top:12px}.compare h3{margin:0 0 10px;font-size:17px;color:var(--purple)}.generated{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--teal);font-size:20px}.compare small{display:block;font-size:13px}footer{font-size:14px;border-top:1px solid var(--line);padding-top:22px;margin-top:30px;color:var(--muted)}details{margin:16px 0}summary{cursor:pointer;color:var(--teal)}.hash{font-size:12px;overflow-wrap:anywhere}#progress{font-size:14px;color:var(--muted);align-self:center}
@media(max-width:640px){main{padding:24px 20px 44px}h1{font-size:28px}h2{font-size:24px}.steps{grid-template-columns:repeat(2,1fr)}.steps button{padding:8px 10px}.steps button span{display:inline;margin-right:8px}.stage{padding-top:22px}.sample{font-size:22px;padding:16px}.metrics{gap:12px}.metrics output{font-size:21px}.metrics small{font-size:12px}.compare{grid-template-columns:1fr;gap:18px}.bar-row{grid-template-columns:48px 1fr 74px;gap:10px}.bar-row .number{font-size:12px}.formula{font-size:19px}.flow{gap:8px}.flow .node{padding:10px 12px;font-size:14px}.toolbar{gap:8px}button{font-size:15px}.toolbar .right{margin-left:0}th,td{padding:8px}.phases{font-size:14px;gap:8px}}
@media(max-width:640px){.flow{flex-direction:column;align-items:stretch}.flow .arrow{align-self:center;transform:rotate(90deg);line-height:1.1}}
</style></head><body><main>
<small>从零手写大模型 · 真实实验回放</small>
<h1>一条短句，怎样改变模型？</h1>
<p class="intro">先跟着一批数据走完一次更新，再看同一个网络经过1,000次预训练、300次问答微调，写出的文字有什么变化。</p>
<div class="phases"><span>随机初值</span><b>→</b><span>文本预训练 × 1,000</span><b>→</b><span>问答微调 × 300</span></div>
<nav class="steps" aria-label="训练阶段"></nav>
<section class="stage" id="stage" aria-labelledby="stage-title"></section>
<div class="toolbar"><button id="previous">← 上一步</button><button id="next" class="primary">下一步 →</button><span id="progress"></span><button id="restart" class="right">从头再看</button></div>
<footer>数字来自配套工程的92,352参数教学模型。第一个更新步由保存的初始权重重放；长程曲线来自原训练日志，每50次更新记录一次。未保存的中间权重没有被补画。页面展示已经计算好的记录，不会在浏览器里训练。<p><a href="https://github.com/DavidDingXu/hello-llm/blob/main/code/lessons/training_replay.py">重放代码</a> · <a href="https://github.com/DavidDingXu/hello-llm/blob/main/code/artifacts/training_replay.json">原始数值</a> · <a href="https://daviddingxu.github.io/hello-llm/">其他演示</a></p></footer>
</main><script>
'use strict';
const DATA=__DATA__;
const names=['拿到数据','编码与标签','前向计算','计算损失','反向与裁剪','更新参数','重复训练','保存与生成','问答微调','三阶段对照'];
const labels=['一条短句进入一批数据','输入和正确答案，错开一个位置','同一批输入，算出每个位置的候选分数','用正确下一字的概率来评分','沿计算路径，求出参数的梯度','优化器执行后，参数才改变','重复这套步骤，共更新1,000次','把学到的参数保存，再加载来生成','换成问答数据，继续训练同一个网络','同一提示词，比较三份真实权重'];
let current=0,historyIndex=0,comparisonIndex=0;
const $=id=>document.getElementById(id),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(n,d=6)=>Number(n).toFixed(d),pct=n=>Number(n)>0&&Number(n)<.00001?'＜0.001%':(Number(n)*100).toFixed(3)+'%';
const lossText=n=>Number(n)>0&&Number(n)<.0001?'＜0.0001':fmt(n,4);
const metrics=rows=>'<div class="metrics">'+rows.map(([label,value])=>`<div><small>${esc(label)}</small><output>${esc(value)}</output></div>`).join('')+'</div>';
const note=s=>`<p class="notice">${s}</p>`;
const header=i=>`<span class="eyebrow">${String(i+1).padStart(2,'0')} / ${names.length} · ${names[i]}</span><h2 id="stage-title">${labels[i]}</h2>`;
function table(rows){return '<div class="scroll-table"><table><thead><tr><th>位置</th><th>输入</th><th>输入编号</th><th>下一字目标</th><th>目标编号</th></tr></thead><tbody>'+rows.map(r=>`<tr class="${r.ignored?'ignored':''}"><td>${r.position}</td><td>${esc(r.input_token)}</td><td>${r.input_id}</td><td class="${r.ignored?'':'target'}">${r.ignored?'不计损失':esc(r.target_token)}</td><td>${r.target_id}</td></tr>`).join('')+'</tbody></table></div>';}
function candidates(items,target){const max=Math.max(...items.map(c=>c.probability));return items.map(c=>`<div class="bar-row ${c.token===target?'correct':''}"><span>${esc(c.token)}</span><div class="bar-track"><div class="bar" style="width:${c.probability/max*100}%"></div></div><span class="number">${pct(c.probability)}</span></div>`).join('');}
// 所有展示层字段在这里适配导出记录；不重新拟合曲线或制造中间参数。
__NORMALIZE__
function firstSample(){return `<div class="sample">${esc(firstText)}</div>`;}
function forwardDetail(){
 const titles={embedding:'查表之后',block1:'模型块1之后',block2:'模型块2之后',final_norm:'末端归一化之后',logits:'词表输出分数'};
 const rows=f.forward.shape_trace.filter(row=>row.first_four_values);
 return '<details><summary>展开同一位置经过各层的真实数值</summary><p>均取输入位置'+target.position+'。向量只列前4个坐标；末行已投影到词表，含义变成前4个候选的分数。</p><div class="scroll-table"><table><thead><tr><th>读取位置</th><th>张量形状</th><th>前4个数</th></tr></thead><tbody>'+rows.map(row=>`<tr><td>${titles[row.name]}</td><td>[${row.shape.join(', ')}]</td><td class="number">${row.first_four_values.map(n=>fmt(n,4)).join(', ')}</td></tr>`).join('')+'</tbody></table></div></details>';
}
function curve(stage){
 const rows=H[stage],isSft=stage==='sft',id=isSft?'sft-history':'pretrain-history';
 if(historyIndex>=rows.length)historyIndex=0;
 return `<div class="legend"><span style="--color:#187B79">训练集平均损失</span><span style="--color:#B4495A">留出集平均损失</span></div><svg class="chart" id="loss-chart" role="img" aria-label="随更新次数变化的训练与留出平均损失"></svg><label for="${id}">查看${isSft?'微调':'预训练'}记录：<output id="history-label"></output><input id="${id}" type="range" min="0" max="${rows.length-1}" step="1" value="${historyIndex}"></label><div id="history-values"></div>`;
}
function drawCurve(stage){
 const rows=H[stage],svg=$('loss-chart'),width=Math.max(300,svg.getBoundingClientRect().width),height=260;
 const left=40,right=18,top=22,bottom=35,maxStep=rows.at(-1).step,maxLoss=Math.max(...rows.flatMap(r=>[r.train_loss,r.val_loss]))*1.08;
 const x=n=>left+(width-left-right)*n/maxStep,y=n=>height-bottom-(height-top-bottom)*n/maxLoss;
 svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
 let drawing=`<path d="M ${left} ${top} V ${height-bottom} H ${width-right}" fill="none" stroke="#9BA7B4"/>`;
 for(const value of [0,Math.ceil(maxLoss/2),Math.floor(maxLoss)])drawing+=`<text x="${left-8}" y="${y(value)+4}" text-anchor="end" font-size="13" fill="#606C7B">${value}</text>`;
 drawing+=`<text x="${left}" y="${height-8}" font-size="13" fill="#606C7B">0步</text><text x="${width-right}" y="${height-8}" text-anchor="end" font-size="13" fill="#606C7B">${maxStep}步</text>`;
 for(const [key,color] of [['train_loss','#187B79'],['val_loss','#B4495A']]){
  drawing+=`<polyline points="${rows.map(r=>`${x(r.step)},${y(r[key])}`).join(' ')}" fill="none" stroke="${color}" stroke-width="2.5"/>`;
  const row=rows[historyIndex];drawing+=`<circle cx="${x(row.step)}" cy="${y(row[key])}" r="5" fill="${color}" stroke="white" stroke-width="2"/>`;
 }
 svg.innerHTML=drawing;
 const row=rows[historyIndex];$('history-label').value=`第${row.step}步`;
 $('history-values').innerHTML=metrics([['更新次数',row.step],['训练损失',lossText(row.train_loss)],['留出损失',lossText(row.val_loss)]]);
}
function comparison(){
 const entry=prefixes[comparisonIndex],titles={initial:'随机初值',pretrain:'预训练后',sft:'问答微调后'};
 let markup=`<div class="toolbar"><button id="continuation" ${comparisonIndex===0?'aria-pressed="true"':''}>看续写</button><button id="question" ${comparisonIndex===1?'aria-pressed="true"':''}>看问答</button></div><div class="sample">${esc(entry.prompt).replace(/\n/g,'<br>')}</div><p>同一前文下，正确下一字“${esc(entry.expected_next_token)}”获得的概率：</p><div class="compare">`;
 for(const stage of ['initial','pretrain','sft']){const row=entry.stages[stage],result=saved[stage].outputs.find(r=>r.prompt===entry.prompt);markup+=`<div><h3>${titles[stage]}</h3><p class="formula">${pct(row.expected_next_probability)}</p><small>这份权重实际贪心写出：</small><p class="generated">${esc(result.generated_text)}</p><small>${result.stop_reason==='eos'?'选中EOS，结束':'达到本次生成字数上限'}</small></div>`;}
 return markup+'</div>'+note('这里显示的是当前一次前向的原始Softmax概率；实际生成另屏蔽PAD、BOS和UNK。每段文字都由对应检查点重新生成后保存，失败输出也保留。');
}
const scenes=[
 ()=>firstSample()+`<p>它是这次重放抽中的第一个样本。同一批共有<strong>${batchSize}条</strong>短句，抽样种子与原训练程序相同。整份预训练集有256条，留出集有64条。</p>`+metrics([['批内短句',batchSize],['每条补齐到',inputShape[1]+'个位置'],['模型可调参数',parameterCount]])+note('后续数字来自整批数据。图中只展开其中一条，便于逐个字符对齐；不会把一条样本的损失冒充整批损失。'),
 ()=>firstSample()+`<p>先加入BOS与EOS。输入去掉最后一项，标签去掉第一项：看到BOS猜首字，看到一个字猜后一个字。短句末尾补PAD，相应标签用−100排除。</p>`+table(pretrainRows)+note(`这一批总共有${validCount}个有效目标。表中的−100只表示不评分，不是词表中的一个字。`),
 ()=>`<p>输入编号先查成向量，再经过两个相同结构的模型块。每个位置最终得到79项分数，分别对应词表中的79个候选。</p><div class="flow"><div class="node">输入编号<small>[${inputShape.join(', ')}]</small></div><span class="arrow">→</span><div class="node">Embedding<small>[${embeddingShape.join(', ')}]</small></div><span class="arrow">→</span><div class="node">模型块 × 2<small>读取可见前文，变换表示</small></div><span class="arrow">→</span><div class="node">词表分数<small>[${logitsShape.join(', ')}]</small></div></div><h3>挑一个位置打开看</h3><p>${esc(targetDescription)}。正确下一字是“<strong>${esc(targetToken)}</strong>”。下列概率由这次真实前向的分数计算：</p>`+candidates(targetCandidates,targetToken)+forwardDetail()+note('这一阶段只使用现有参数计算输出。尚未评分、反向或执行优化器，参数摘要保持不变。'),
 ()=>`<p>正确下一字“${esc(targetToken)}”的概率为<strong>${pct(targetProbability)}</strong>。它自己的损失为：</p><p class="formula"><span>−ln(${fmt(targetProbability)})</span><span> = ${fmt(targetLoss,4)}</span></p><p>其他有效位置也各有一个正确目标。把这批${validCount}项损失取平均，才得到本次用于反向传播的批次损失。</p>`+metrics([['单个位置损失',fmt(targetLoss,4)],['有效目标数',validCount],['整批平均损失',fmt(batchLoss,4)]])+note('训练时，正确答案来自已准备好的样本；模型不需要先写完一整段文字，才知道这一批错了多少。'),
 ()=>`<p>执行<code>loss.backward()</code>，得到每个可调参数的梯度。下面只放大“小”的词向量第一个坐标；它的梯度汇总了整批损失经过该参数的路径。</p>`+metrics([['该参数当前值',fmt(parameter.value_before,8)],['裁剪前梯度',fmt(parameter.gradient_before_clip,8)],['裁剪后梯度',fmt(parameter.gradient_after_clip,8)]])+`<p>全体梯度的总范数从<strong>${fmt(gradient.before_clip,4)}</strong>变为<strong>${fmt(gradient.after_clip,4)}</strong>，裁剪阈值为${gradient.max_norm}。</p><p class="check">前向后、反向后、裁剪后：模型参数摘要都与初始摘要一致。</p>`+note('梯度记录“怎样改”的方向与幅度线索。反向和裁剪都没有执行真正的参数更新。'),
 ()=>`<p>同一个参数：<code>embedding.weight[${parameter.row}, ${parameter.column}]</code>，对应“小”的词向量第一个坐标。优化器现在执行<code>step()</code>。</p>`+metrics([['更新前',fmt(parameter.value_before,8)],['更新后',fmt(parameter.value_after,8)],['实际改变量',fmt(parameter.update,8)]])+`<p>这一步使用AdamW，学习率为0.003。优化器还维护梯度统计并处理权重衰减，因此实际改变量应从记录读取，不能直接套用单纯SGD的<code>−学习率×梯度</code>。</p><p class="check">执行优化器后，模型参数摘要发生改变。</p>`+note('这只是92,352个参数中的一个观察点；其余可训练参数也参加同一优化器更新。完成这一步后，下一批使用更新后的参数重新计算。'),
 ()=>`<p>每次重新抽一批数据，重复“前向→损失→反向→更新”。下面每个点都是原日志中记录的一次整组评估，没有补造中间训练结果。</p>`+curve('pretrain')+note('留出题同时改变了句式，并含训练正文没有出现过的“在、面、前”。红线表现不能只归因于句式变化。滑动选择的是日志记录，不会加载某个未保存的中间权重。'),
 ()=>`<div class="flow"><div class="node">预训练参数<small>1,000次更新之后</small></div><span class="arrow">→</span><div class="node">pretrain.pt<small>配置＋词表＋参数</small></div><span class="arrow">→</span><div class="node">重新加载<small>前向→选下一字→追加</small></div></div><p>输入“早上，小丁喜欢”，预训练检查点实际写出了：</p><div class="sample">${esc(saved.pretrain.outputs[0].generated_text)}</div><p>这时没有标准答案参与损失计算，也不执行反向和优化器。生成每一步的输入在变，模型参数固定。</p>`+note('这里用的是保存并重新加载的真实权重。得到这句话，说明这个小实验能完成相应续写；不代表它已经具备通用对话能力。'),
 ()=>`<p>加载预训练权重，换成“问题＋答案”的样本。结构与92,352个可训练参数都不变；直接评分的目标改为答案和EOS，问题位置用−100排除。</p><div class="sample">${esc(sftPrompt).replace(/\n/g,'<br>')}<strong>${esc(sftAnswer)}</strong></div>`+table(sftRows)+`<p>仍然重复同一个训练循环，共300次更新：</p>`+curve('sft')+note('问题依然在前向输入中，也能经答案损失获得梯度。留出问法额外含训练正文未出现的“最”，需要结合这个差异解读留出表现。'),
 ()=>comparison()+`<p>两次训练修改的是同一网络的参数；生成只使用选定的那一份参数。微调改善某种提问方式后，也可能损伤原先的续写。这三列可以一起核对。</p>`
];
function render(){
 $('stage').innerHTML=header(current)+scenes[current]();
 document.querySelectorAll('.steps button').forEach((button,i)=>{if(i===current)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');});
 $('previous').disabled=current===0;$('next').disabled=current===names.length-1;$('progress').textContent=`${current+1} / ${names.length}`;
 if(current===6||current===8){const kind=current===6?'pretrain':'sft';drawCurve(kind);$(kind+'-history').addEventListener('input',e=>{historyIndex=Number(e.target.value);drawCurve(kind);});}
 if(current===9){$('continuation').addEventListener('click',()=>{comparisonIndex=0;render();});$('question').addEventListener('click',()=>{comparisonIndex=1;render();});}
}
document.querySelector('.steps').innerHTML=names.map((name,i)=>`<button data-stage="${i}"><span>${String(i+1).padStart(2,'0')}</span>${name}</button>`).join('');
document.querySelectorAll('.steps button').forEach((button,i)=>button.addEventListener('click',()=>{current=i;historyIndex=0;render();}));
$('previous').addEventListener('click',()=>{current--;historyIndex=0;render();});$('next').addEventListener('click',()=>{current++;historyIndex=0;render();});$('restart').addEventListener('click',()=>{current=0;historyIndex=0;comparisonIndex=0;render();});
addEventListener('resize',()=>{if(current===6||current===8)drawCurve(current===6?'pretrain':'sft');});render();
</script></body></html>'''


# 用真实记录的字段生成展示变量；schema由配套数据导出器明确管理。
NORMALIZE = r'''
const f=DATA.first_step,rep=f.batch.representative;
const firstText=rep.record.text,batchSize=f.batch.record_ids.length;
const inputShape=f.shapes.input_ids,logitsShape=f.shapes.logits;
const embeddingShape=f.forward.shape_trace.find(row=>row.name==='embedding').shape;
const parameterCount=DATA.model.parameter_count,validCount=f.valid_target_count;
const parameter=f.observed_parameter,gradient=f.gradient_norm,batchLoss=f.loss;
const target=f.target_probability,targetToken=target.target_token;
const targetProbability=target.probability,targetLoss=target.negative_log_probability;
const targetDescription=`输入位置${target.position}当前读到“${target.input_token}”，可见前文是“${rep.input_tokens.slice(1,target.position+1).join('')}”`;
const targetCandidates=target.probabilities.map((probability,id)=>({id,token:DATA.model.vocabulary[id],probability})).sort((a,b)=>b.probability-a.probability).slice(0,5);
if(!targetCandidates.some(row=>row.id===target.target_id))targetCandidates.push({id:target.target_id,token:targetToken,probability:targetProbability});
function exampleRows(example){
 // 展开全部有效输入与第一个补齐位置，其余PAD同理，不靠省略改动评分边界。
 const last=example.eos_target_positions[0]+1;
 return example.input_ids.slice(0,last+1).map((id,i)=>({position:i,input_id:id,input_token:example.input_tokens[i],target_id:example.target_ids[i],target_token:example.target_tokens[i],ignored:!example.loss_mask[i]}));
}
const pretrainRows=exampleRows(rep),sftRows=exampleRows(DATA.sft_example);
const sftPrompt=DATA.sft_example.record.prompt,sftAnswer=DATA.sft_example.record.answer;
const H={pretrain:DATA.histories.pretrain.history,sft:DATA.histories.sft.history};
const prefixes=DATA.prefix_comparisons,saved=DATA.saved_generation_comparison;
'''


def build():
    """读已有JSON并生成独立HTML，不改检查点和训练记录。"""
    data = json.loads((CODE / 'artifacts/training_replay.json').read_text(encoding='utf-8'))
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace('</', '<\\/')
    markup = HTML.replace('__DATA__', payload).replace('__NORMALIZE__', NORMALIZE)
    (COLUMN / 'chapters/20-full-workflow/training-replay.html').write_text(markup, encoding='utf-8')


if __name__ == '__main__':
    build()

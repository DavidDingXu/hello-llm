import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import {calculate, svg} from './animation/src/neuron.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const code = path.resolve(here, '..');
const article = path.resolve(code, '../chapters/01-neuron');
const images = path.join(article, 'images');
await mkdir(images, {recursive: true});
const example = JSON.parse(await readFile(path.join(code, 'artifacts/lesson01.json'), 'utf8'));
assert.equal(calculate(example).output, example.output);
for (const variant of example.variants) assert.equal(calculate(variant).output, variant.output);
await writeFile(path.join(here, 'animation/src/lesson01.json'), JSON.stringify(example, null, 2)+'\n');
const figures = {roles:'01-输入与参数', products:'02-两条乘法路径',
  chain:'06-连接两个神经元', flow:'07-完整计算', network:'09-从神经元到神经网络'};
for (const [kind, name] of Object.entries(figures)) await writeFile(path.join(images, name+'.svg'), svg(kind,example));

const engine = (await readFile(path.join(here, 'animation/src/neuron.mjs'), 'utf8')).replace(/^export /gm, '');
const html = `<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>神经元计算实验 · 好好用 AI</title>
<style>
:root{color-scheme:light;--bg:#FFFFFF;--ink:#222A35;--muted:#606C7B;--green:#187B79;--parameter:#8056A5;--blue:#3267A4}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'Hiragino Sans GB','PingFang SC','Microsoft YaHei',Arial,sans-serif;line-height:1.7}main{max-width:1160px;margin:auto;padding:38px 36px 60px}.brand{font-size:13px;letter-spacing:.13em;color:var(--green)}h1{font-size:clamp(26px,3.6vw,36px);letter-spacing:-.04em;line-height:1.3;margin:22px 0 14px}p{margin:10px 0}.intro{max-width:750px;color:var(--muted)}.workbench{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:44px;margin-top:34px;align-items:start}.picture{border-top:1px solid var(--ink);padding-top:14px}#scene svg{display:block;width:100%;height:auto}button{font:inherit;font-size:14px;border:1px solid #BEC6D1;border-radius:4px;padding:9px 14px;background:transparent;color:var(--ink);cursor:pointer}button:hover{background:#F1F5FC}button:focus-visible,input:focus-visible{outline:3px solid #8056A5;outline-offset:4px}button:disabled{opacity:.4;cursor:default}.primary{background:var(--green);color:white;border-color:var(--green)}.primary:hover{background:#155F61}.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}.step{font-size:14px;color:var(--muted);margin:0 0 12px}.reading{border-top:1px solid var(--ink);padding:18px 0 24px}.reading small{display:block;font-size:13px;color:var(--muted)}#answer{font-size:70px;line-height:1.25;color:var(--green);font-weight:650;font-variant-numeric:tabular-nums}#equation{font-size:17px;overflow-wrap:anywhere}.controls h2{font-size:18px;margin:18px 0 12px}.controls h2 span{font-weight:400;font-size:13px;color:var(--muted)}label{display:grid;grid-template-columns:1fr 44px;gap:8px;margin-top:14px;font-size:15px}label output{text-align:right;font-weight:650;font-variant-numeric:tabular-nums}input[type=range]{grid-column:1/-1;width:100%;margin:0;height:28px;accent-color:var(--blue)}.parameters input{accent-color:var(--parameter)}.parameters{border-top:1px solid #DDE2E8;margin-top:20px;padding-top:4px}.presets{border-top:1px solid #DDE2E8;margin-top:26px;padding-top:12px;display:flex;gap:8px;flex-wrap:wrap}.note{font-size:13px;color:var(--muted);margin-top:18px}.explanation{margin-top:28px;padding:22px 0;border-top:1px solid #DDE2E8;max-width:820px}.explanation strong{color:var(--green)}footer{font-size:12px;color:var(--muted);margin-top:30px}a{color:var(--green)}@media(max-width:750px){main{padding:24px 20px 40px}.workbench{grid-template-columns:1fr;gap:26px;margin-top:24px}.controls{display:grid;grid-template-columns:1fr 1fr;gap:0 20px}.reading,.presets,.note{grid-column:1/-1}.parameters{margin:0;border:0;padding:0}.controls h2{margin-top:8px}.picture{max-width:600px}.reading{display:grid;grid-template-columns:100px 1fr;gap:0 20px}.reading small{grid-column:1/-1}#answer{font-size:60px}#equation{align-self:center;font-size:16px}h1{margin-top:18px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
<main><div class="brand">好好用 AI / 从零手写大模型 · 第 01 讲</div>
<h1>一个神经元，逐步计算。</h1>
<p class="intro">先跟着数字走一遍，再亲手改数。蓝色是本次输入，紫色是函数的参数，青色是输出。直接在页面改数即可，无须安装 Python。</p>
<div class="workbench"><section class="picture" aria-label="神经元计算过程">
<div class="toolbar"><button id="restart">从头看</button><button id="prev">上一步</button><button class="primary" id="next">下一步</button><button id="play">自动播放</button></div>
<p class="step" id="stepLabel" aria-live="polite"></p><div id="scene"></div></section>
<aside class="controls" aria-label="修改输入和参数"><div class="reading" aria-live="polite"><small>这组数的完整计算结果</small><div id="answer">4</div><div id="equation"></div></div>
<section><h2>本次输入 <span>送进函数的数据</span></h2>
<label for="x1">第一项 x₁<output id="x1v" for="x1">2</output><input id="x1" type="range" min="-4" max="4" step="1" value="2"></label>
<label for="x2">第二项 x₂<output id="x2v" for="x2">1</output><input id="x2" type="range" min="-4" max="4" step="1" value="1"></label></section>
<section class="parameters"><h2>函数的参数 <span>规定怎样计算</span></h2>
<label for="w1">第一条权重 w₁<output id="w1v" for="w1">1</output><input id="w1" type="range" min="-4" max="4" step="1" value="1"></label>
<label for="w2">第二条权重 w₂<output id="w2v" for="w2">3</output><input id="w2" type="range" min="-4" max="4" step="1" value="3"></label>
<label for="b">偏置 b<output id="bv" for="b">-1</output><input id="b" type="range" min="-8" max="8" step="1" value="-1"></label></section>
<div class="presets" aria-label="对照实验"><button data-preset="0">原始例子</button><button data-preset="1">只改输入 → 7</button><button data-preset="2">只改偏置 → 5</button><button data-preset="3">负数经过 ReLU</button></div>
<p class="note">拖动参数是在手动做实验。训练需要根据误差自动更新参数，后面的文章再一步步实现。</p></aside></div>
<div class="explanation"><strong>这一小段，真的会算就够了。</strong><p>两条路径各做一次乘法，把结果相加，再加偏置，最后经过 ReLU：正数保留，负数变成 0，0 仍然是 0。图中的淡色节点表示后面还没走到的步骤。</p><p>试一试：只把第二项输入从 1 改成 2，其他数保持原样。多出来的 1 会先乘权重 3，所以输出增加 3。</p></div>
<footer>本页也可以保存后离线打开。<a href="index.html">返回本讲</a></footer></main>
<script>${engine}
const initial=${JSON.stringify(example)};
const ids=['x1','x2','w1','w2','b'];
let stage=0,timer=null;
const get=id=>document.getElementById(id);
function state(){return {inputs:[+get('x1').value,+get('x2').value],weights:[+get('w1').value,+get('w2').value],bias:+get('b').value};}
function draw(){const d=state(),c=calculate(d);get('scene').innerHTML=svg('flow',d,stage);get('answer').textContent=fmt(c.output);get('equation').textContent='ReLU('+fmt(d.inputs[0])+' × ('+fmt(d.weights[0])+') + '+fmt(d.inputs[1])+' × ('+fmt(d.weights[1])+') + ('+fmt(d.bias)+')) = '+fmt(c.output);get('stepLabel').textContent=(stage+1)+' / 6 · '+steps[stage];get('prev').disabled=stage===0;get('next').disabled=stage===5;ids.forEach(id=>get(id+'v').value=get(id).value);}
function pause(){clearInterval(timer);timer=null;get('play').textContent='自动播放';get('play').setAttribute('aria-pressed','false');}
get('prev').onclick=()=>{pause();stage=Math.max(0,stage-1);draw();};
get('next').onclick=()=>{pause();stage=Math.min(5,stage+1);draw();};
get('restart').onclick=()=>{pause();stage=0;draw();};
get('play').onclick=()=>{if(timer){pause();return;}if(stage===5)stage=0;draw();get('play').textContent='暂停播放';get('play').setAttribute('aria-pressed','true');timer=setInterval(()=>{stage=Math.min(5,stage+1);draw();if(stage===5)pause();},2300);};
ids.forEach(id=>get(id).addEventListener('input',()=>{pause();stage=5;draw();}));
document.querySelectorAll('[data-preset]').forEach(button=>button.onclick=()=>{pause();const n=+button.dataset.preset;const d=n===0?initial:initial.variants[n-1];const values=[...d.inputs,...d.weights,d.bias];ids.forEach((id,i)=>get(id).value=values[i]);stage=5;draw();});
draw();
</script></html>`;
await writeFile(path.join(article, 'walkthrough.html'), html);
console.log('第 01 讲数值核对通过；SVG、共享数据和离线交互页已生成。');

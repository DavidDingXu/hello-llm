// 精确教材图：SVG、动画和离线演示共用；前向阶段不改参数。
export const palette = {
  bg:'#FFFFFF', ink:'#222A35', muted:'#606C7B', line:'#8F9BA8',
  input:'#3267A4', inputLight:'#F1F5FC', parameter:'#8056A5',
  parameterLight:'#F7F2FB', output:'#187B79', outputLight:'#EFF8F7',
};
export const steps=['输入与参数','第一条乘法','第二条乘法','两个乘积相加','加上偏置','经过 ReLU，得到输出'];
export const figureHeights={roles:975,products:900,chain:900,flow:1500,network:1095};
export function calculate(d){
  const {inputs:x,weights:w,bias:b}=d;
  if(x.length!==2||w.length!==2||![...x,...w,b].every(Number.isFinite))throw new Error('需要两个有限数值输入、两个权重和一个偏置。');
  const products=[x[0]*w[0],x[1]*w[1]],sum=products[0]+products[1],z=sum+b;
  return {products,sum,z,output:Math.max(0,z)};
}
export const fmt=n=>Number.isInteger(n)?String(n):String(Number(n.toFixed(3)));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const tx=(x,y,text,size=44,fill=palette.ink,anchor='middle',weight=400)=>`<text x="${x}" y="${y}" text-anchor="${anchor}" fill="${fill}" font-size="${size}" font-weight="${weight}">${esc(text)}</text>`;
const math=(x,y,text,size=60,fill=palette.ink,anchor='middle')=>`<text class="math" x="${x}" y="${y}" text-anchor="${anchor}" fill="${fill}" font-size="${size}">${esc(text)}</text>`;
const line=(d,color=palette.line,width=2.8,arrow=true)=>`<path d="${d}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"${arrow?' marker-end="url(#arrow)"':''}/>`;
const round=(x,y,w,h,fill,stroke=palette.ink,r=8)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="2.2"/>`;
const circle=(x,y,r,value,fill='#FFF',stroke=palette.ink,size=64)=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="2.4"/>`+math(x,y+size*.3,value,size,stroke);
const pill=(x,y,w,h,value,fill,color=palette.ink,size=54)=>round(x,y,w,h,fill,color)+math(x+w/2,y+h/2+size*.3,value,size,color);
const group=(visible,content)=>`<g opacity="${visible?1:.12}">${content}</g>`;
function header(title,subtitle){
  return tx(48,78,title,52,palette.ink,'start',500)+tx(48,143,subtitle,50,palette.muted,'start');
}
function legend(y){
  return line(`M64 ${y-12} H94`,palette.input,5,false)+tx(110,y,'输入',50,palette.input,'start')+
    line(`M300 ${y-12} H330`,palette.parameter,5,false)+tx(346,y,'参数',50,palette.parameter,'start')+
    line(`M536 ${y-12} H566`,palette.output,5,false)+tx(582,y,'输出',50,palette.output,'start');
}
function wrap(body,height,title){
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 ${height}" role="img" aria-label="${esc(title)}"><defs><marker id="arrow" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M1 1 L10 6 L1 11" fill="none" stroke="context-stroke" stroke-width="1.5"/></marker></defs><style>text{font-family:'Hiragino Sans GB','PingFang SC','Microsoft YaHei',Arial,sans-serif;font-variant-numeric:tabular-nums}.math{font-weight:400;font-variant-numeric:tabular-nums}</style><rect width="1080" height="${height}" fill="${palette.bg}"/>${body}</svg>`;
}
// 静态图以 720 单位排版，再放大到 1080 像素导出；关键标签至少 36 单位。
function miniHeader(title){return tx(30,56,title,36,palette.ink,'start',500);}
function roles(d){
  const c=calculate(d);
  let s=miniHeader('输入、参数与输出');
  s+=tx(35,120,'输入 x',36,palette.input,'start')+pill(35,145,255,150,`[${d.inputs.map(fmt).join(', ')}]`,palette.inputLight,palette.input,54);
  s+=tx(380,120,'参数 w、b',36,palette.parameter,'start')+round(380,145,305,150,palette.parameterLight,palette.parameter);
  s+=math(532,205,`w = [${d.weights.map(fmt).join(', ')}]`,38,palette.parameter)+math(532,263,`b = ${fmt(d.bias)}`,38,palette.parameter);
  s+=line('M160 310 V335 H260 V350',palette.input)+line('M532 310 V335 H470 V350',palette.parameter);
  s+=round(125,365,470,100,'#FFF')+tx(360,427,'按参数计算',40);
  s+=line('M360 480 V525',palette.output)+tx(205,593,'输出 y',36,palette.output)+pill(300,545,180,80,fmt(c.output),palette.outputLight,palette.output,54);
  return s;
}
function products(d){
  const c=calculate(d);
  let s=miniHeader('各自相乘，得到两个乘积');
  for(let i=0;i<2;i++){
    const x=180+i*360;
    s+=tx(x,125,`输入 x${i===0?'₁':'₂'}`,36,palette.input)+circle(x,200,44,fmt(d.inputs[i]),palette.inputLight,palette.input,56);
    s+=line(`M${x} 265 V320`,palette.input);
    s+=pill(x-83,340,166,80,`× ${fmt(d.weights[i])}`,palette.parameterLight,palette.parameter,48);
    s+=tx(x+108,394,`w${i===0?'₁':'₂'}`,36,palette.parameter,'start');
    s+=line(`M${x} 440 V475`)+circle(x,540,43,fmt(c.products[i]),'#FFF',palette.ink,54);
  }
  return s;
}
function chain(d){
  const c=calculate(d),second=Math.max(0,c.output*.5+1);
  let s=miniHeader('输出，成为下一个组件的输入');
  s+=tx(30,110,`神经元 1：接收 [${d.inputs.map(fmt).join(', ')}]`,36,palette.ink,'start');
  s+=round(30,135,660,135,'#FFF');
  s+=math(360,195,`${fmt(d.inputs[0])}×${fmt(d.weights[0])} + ${fmt(d.inputs[1])}×${fmt(d.weights[1])} + (${fmt(d.bias)}) = ${fmt(c.z)}`,38);
  s+=tx(360,248,`ReLU 后输出 ${fmt(c.output)}`,36,palette.output);
  s+=line('M360 290 V350',palette.output)+tx(400,334,`读取 ${fmt(c.output)}`,36,palette.output,'start');
  s+=tx(30,402,`神经元 2：接收 [${fmt(c.output)}]`,36,palette.ink,'start');
  s+=round(30,430,660,135,'#FFF');
  s+=math(360,490,`${fmt(c.output)} × 0.5 + 1 = ${fmt(c.output*.5+1)}`,42)+tx(360,543,`ReLU 后输出 ${fmt(second)}`,36,palette.output);
  return s;
}
function network(){
  let s=miniHeader('把神经元按层连接');
  s+=tx(75,130,'输入层',36,palette.input)+tx(350,130,'隐藏层',36)+tx(640,130,'输出层',36);
  const nodes={x1:{x:75,y:250,r:36},x2:{x:75,y:460,r:36},
    a:{x:350,y:250,r:60},b:{x:350,y:460,r:60},c:{x:640,y:355,r:60}};
  const edges=[['x1','a'],['x1','b'],['x2','a'],['x2','b'],['a','c'],['b','c']];
  for(const [from,to] of edges){
    const a=nodes[from],b=nodes[to],dx=b.x-a.x,dy=b.y-a.y,length=Math.hypot(dx,dy);
    const sx=a.x+dx/length*(a.r+10),sy=a.y+dy/length*(a.r+10);
    const ex=b.x-dx/length*(b.r+10),ey=b.y-dy/length*(b.r+10);
    s+=line(`M${sx} ${sy} L${ex} ${ey}`,palette.line,2.8);
  }
  s+=circle(75,250,36,'x₁',palette.inputLight,palette.input,44)+circle(75,460,36,'x₂',palette.inputLight,palette.input,44);
  for(const [key,name] of [['a','A'],['b','B'],['c','C']]){
    const {x,y,r}=nodes[key];
    s+=tx(x,y-80,`神经元 ${name}`,36);
    s+=`<circle cx="${x}" cy="${y}" r="${r}" fill="${palette.outputLight}" stroke="${palette.output}" stroke-width="2.4"/>`;
    s+=tx(x,y-8,'乘加',36,palette.output)+tx(x,y+36,'ReLU',36,palette.output);
  }
  s+=tx(497,259,'A 输出',36,palette.output)+tx(497,485,'B 输出',36,palette.output);
  s+=line('M640 435 V490',palette.output)+tx(640,540,'输出 y',36,palette.output);
  s+=tx(30,620,'每条输入连接：1 个权重',36,palette.parameter,'start');
  s+=tx(30,685,'每个计算节点：1 个偏置',36,palette.parameter,'start');
  return s;
}
function flow(d,step=5,progress=1){
  const c=calculate(d);
  let s=header(steps[step],'读输入和参数，计算新的数值。');
  for(let i=0;i<2;i++){
    const x=280+i*520,active=step>=i+1;
    s+=tx(x,235,`输入 x${i===0?'₁':'₂'}`,54,palette.input)+circle(x,330,59,fmt(d.inputs[i]),palette.inputLight,palette.input,70);
    s+=pill(x-100,470,200,92,`× ${fmt(d.weights[i])}`,palette.parameterLight,palette.parameter,66)+tx(x+122,532,`w${i===0?'₁':'₂'}`,54,palette.parameter,'start');
    s+=group(active,line(`M${x} 412 V446`,palette.input)+line(`M${x} 585 V625`));
    s+=group(active,circle(x,710,59,fmt(c.products[i]))+math(x,825,`${fmt(d.inputs[i])} × ${fmt(d.weights[i])}`,54,palette.muted));
    if(step===i+1&&progress<.7){const y=420+Math.min(progress/.7,1)*200;s+=`<circle cx="${x}" cy="${y}" r="8" fill="${palette.input}"/>`;}
  }
  s+=group(step>=3,line('M365 710 H456')+line('M715 710 H624')+circle(540,710,59,fmt(c.sum))+math(540,610,`${fmt(c.products[0])} + ${fmt(c.products[1])}`,54,palette.muted));
  s+=group(step>=4,line('M540 795 V930')+circle(540,1015,59,fmt(c.z))+
    pill(790,970,235,90,`b = ${fmt(d.bias)}`,palette.parameterLight,palette.parameter,48)+line('M765 1015 H624',palette.parameter)+math(230,1035,`${fmt(c.sum)} + (${fmt(d.bias)})`,54));
  s+=group(step>=5,line('M540 1100 V1210',palette.output)+pill(200,1250,680,110,`ReLU(${fmt(c.z)}) = ${fmt(c.output)}`,palette.outputLight,palette.output,62)+tx(540,1430,c.z>=0?'非负数保留，得到输出。':'负数归零，得到输出。',54,palette.output));
  s+=legend(1480);
  return s;
}
export function svg(figure,d,step=5,progress=1){
  const fns={roles,products,chain,flow,network};
  if(!fns[figure])throw new Error(`未知图解：${figure}`);
  const title=figure==='flow'?steps[step]:figure==='network'?'两个输入、两个中间神经元与一个输出神经元的连接':'一个神经元的计算图';
  const body=fns[figure](d,step,progress);
  return wrap(figure==='flow'?body:`<g transform="scale(1.5)">${body}</g>`,figureHeights[figure],title);
}

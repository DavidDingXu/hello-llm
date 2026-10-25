// 两个构造例的逐帧几何。帧号决定全部状态，跳转或重渲染不会改变结果。
const C = {ink:'#222A35', muted:'#606C7B', blue:'#3267A4', teal:'#187B79', line:'#C5CDD7'};
const font = 'Hiragino Sans GB,PingFang SC,Microsoft YaHei,Arial,sans-serif';
const escape = value => String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const text = (x,y,value,size=32,color=C.ink,anchor='start',weight=400) =>
  `<text x='${x}' y='${y}' font-size='${size}' fill='${color}' text-anchor='${anchor}' font-weight='${weight}'>${escape(value)}</text>`;
const line = (x1,y1,x2,y2,color=C.line,width=2,dash='') =>
  `<path d='M${x1} ${y1} L${x2} ${y2}' fill='none' stroke='${color}' stroke-width='${width}' stroke-dasharray='${dash}'/>`;
const rect = (x,y,w,h,fill='white',stroke=C.line,r=6) =>
  `<rect x='${x}' y='${y}' width='${w}' height='${h}' fill='${fill}' stroke='${stroke}' stroke-width='2' rx='${r}'/>`;
const clamp = value => Math.max(0,Math.min(1,value));
const smooth = value => {const p=clamp(value);return p*p*(3-2*p);};
const svg = (title,subtitle,body) => `<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1800' viewBox='0 0 720 1200' role='img' aria-label='${escape(title)}'>
<defs>${['blue','teal','muted'].map(name=>`<marker id='arrow-${name}' viewBox='0 0 12 12' refX='10' refY='6' markerWidth='15' markerHeight='15' markerUnits='userSpaceOnUse' orient='auto'><path d='M0 0 L12 6 L0 12 Z' fill='${C[name]}'/></marker>`).join('')}</defs>
<rect width='720' height='1200' fill='white'/><g font-family='${font}' font-variant-numeric='tabular-nums'>${text(36,60,title,38,C.ink,'start',600)}${text(36,110,subtitle,28,C.muted)}${body}</g></svg>`;

export function headSplitState(frame) {
  const time=frame/30;
  const blend=time<5 ? smooth((time-2)/3) : time<8 ? 1 : 1-smooth((time-8)/2);
  const tiles=Array.from({length:12},(_,value)=>{
    const position=Math.floor(value/4),feature=value%4,head=Math.floor(feature/2);
    const original={x:130+feature*118,y:236+position*98};
    const split={x:(head===0?70:422)+(feature%2)*118,y:760+position*98};
    return {value,position,feature,head,x:original.x+(split.x-original.x)*blend,
      y:original.y+(split.y-original.y)*blend,original,split};
  });
  return {time,blend,tiles};
}

export function headSplitFrame(frame) {
  const {time,blend,tiles}=headSplitState(frame);
  const caption=time<2?'原数组：3个位置，每处4个特征':time<5?'沿特征轴分开，格子里的数不变':time<8?'每个头仍然拥有位置0、1、2':'按位置拼回，恢复原来的顺序';
  let s=text(36,174,caption,32);
  for(let feature=0;feature<4;feature++)s+=text(183+feature*118,216,`特征${feature}`,27,C.muted,'middle');
  for(let position=0;position<3;position++)s+=text(98,289+position*98,`位置${position}`,28,C.muted,'end');
  for(const tile of tiles) {
    s+=rect(tile.original.x,tile.original.y,106,82,'#F4F6F9','#E4E9EF');
    s+=rect(tile.split.x,tile.split.y,106,82,'#F4F6F9','#E4E9EF');
  }
  for(let head=0;head<2;head++) {
    const cx=head===0?182:534,color=head===0?C.blue:C.teal;
    s+=text(cx,1083,`头${head}`,36,color,'middle',600);
    s+=text(cx,1128,`特征${head*2}、${head*2+1}`,29,color,'middle');
    for(let position=0;position<3;position++)s+=text(head===0?38:390,813+position*98,position,29,C.muted,'middle');
  }
  // 所有格子同步移动：行距始终相同，途中也不会互相遮挡。
  for(const tile of tiles) {
    const color=tile.head===0?C.blue:C.teal;
    s+=rect(tile.x,tile.y,106,82,tile.head===0?'#ECF3FB':'#E9F4F1',color);
    s+=text(tile.x+53,tile.y+55,tile.value,43,color,'middle',600);
  }
  // 移动时说明放在图外；静止时才显示位置1的局部核对。
  if(blend===1) {
    s+=text(360,705,'位置1：头0拿[4,5]，头1拿[6,7]',30,C.ink,'middle');
    s+=text(38,745,'位置',26,C.muted,'middle')+text(390,745,'位置',26,C.muted,'middle');
  }
  s+=text(360,1180,'这里只拆和拼：没有投影，也没有求和',28,C.muted,'middle');
  return svg('格子拆开，再按位置拼回','构造例 · 索引0—11 · 重排不增加参数',s);
}

export function ropeState(frame) {
  const time=frame/30;
  const shift=3*smooth((time-2)/2);
  const moveKey=smooth((time-6)/1.25);
  const qPosition=1+shift,kPosition=shift-moveKey;
  const q=[Math.cos(qPosition),Math.sin(qPosition)];
  const k=[Math.cos(kPosition),Math.sin(kPosition)];
  return {time,qPosition,kPosition,q,k,difference:qPosition-kPosition,dot:q[0]*k[0]+q[1]*k[1]};
}

export function ropeFrame(frame) {
  const d=ropeState(frame),cx=360,cy=446,radius=190;
  let s='';
  const stage=d.time<2?'先相差1格':d.time<6?'两个位置一起后移3格':'只把K再往前移1格';
  const positions=d.time<2?'Q在位置1，K在位置0':d.time<4?'Q：1→4；K：0→3':d.time<6?'Q在位置4，K在位置3':d.time<7.25?'Q仍在4；K：3→2':'Q在位置4，K在位置2';
  s+=text(36,184,stage,36,C.ink,'start',600)+text(36,234,positions,32,C.muted);
  s+=`<circle cx='${cx}' cy='${cy}' r='${radius}' fill='#F8FAFC' stroke='${C.line}' stroke-width='2'/>`;
  s+=line(cx-radius-30,cy,cx+radius+30,cy,C.line)+line(cx,cy+radius+30,cx,cy-radius-30,C.line);
  // 点积只取决于两根单位箭头的相对转角；绿色弧线跟随这段转角。
  const a=d.kPosition,b=d.qPosition,arc=80;
  s+=`<path d='M${cx+arc*Math.cos(a)} ${cy-arc*Math.sin(a)} A${arc} ${arc} 0 0 0 ${cx+arc*Math.cos(b)} ${cy-arc*Math.sin(b)}' fill='none' stroke='${C.teal}' stroke-width='5'/>`;
  for(const [name,v,color] of [['Q',d.q,C.blue],['K',d.k,C.teal]]) {
    const x=cx+radius*v[0],y=cy-radius*v[1];
    s+=`<path d='M${cx} ${cy} L${x} ${y}' fill='none' stroke='${C[color===C.blue?'blue':'teal']}' stroke-width='6' marker-end='url(#arrow-${name==='Q'?'blue':'teal'})'/>`;
    // 顶部留给位置说明；箭头转到上方时，Q/K标签留在圆图范围内。
    const labelY=Math.max(cy-radius+32,y+(v[1]>=0?-12:35));
    s+=text(x+(v[0]>=0?18:-18),labelY,name,34,color,v[0]>=0?'start':'end',600);
  }
  s+=text(360,713,`位置差：${d.difference.toFixed(2)}格`,36,C.ink,'middle');
  s+=text(360,777,`原始点积：${d.dot.toFixed(4)}`,43,C.teal,'middle',600);
  const zero=360,unit=245;
  s+=line(zero-unit,895,zero+unit,895,C.line,3);
  for(const value of [-1,0,1])s+=line(zero+value*unit,883,zero+value*unit,915,C.muted)+text(zero+value*unit,958,value,30,C.muted,'middle');
  s+=rect(Math.min(zero,zero+d.dot*unit),853,Math.abs(d.dot)*unit,39,C.teal,C.teal,2);
  s+=text(360,1031,d.time<6?'一起转动时，位置差和点积保持不变':'只改一个位置，位置差和点积一起改变',30,C.ink,'middle');
  s+=text(36,1112,'第一对频率为1；点积=cos(位置差)',30,C.ink);
  s+=text(36,1168,'尚未缩放或做Softmax；V没有参与旋转',28,C.muted);
  return svg('一起转动，为什么分数不变？','构造例 · 旋转前Q、K都为[1,0]',s);
}

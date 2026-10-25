/* 从原始 SVG 重排网页横向版；保留所有内容节点，不修改图中数值和文字。
 * 只在元素之间的留白处分栏，不跨越箭头、曲线或文本；手机继续用原竖图。
 */
const fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'../..');
const requestedFolders = new Set(process.argv.slice(2));
(async()=>{
 const browser=await chromium.launch({headless:true});const page=await browser.newPage();const report=[];
 try{
  const folders=await fs.readdir(path.join(root,'chapters'));
  for(const folder of folders){
   if(requestedFolders.size && !requestedFolders.has(folder))continue;
   for(const lang of ['', 'en']){
    const dir=path.join(root,'chapters',folder,'images',lang);
    let names;try{names=(await fs.readdir(dir)).filter(n=>n.endsWith('.svg'))}catch{continue}
    for(const name of names){
     const file=path.join(dir,name);await page.goto(pathToFileURL(file).href);
     const result=await page.evaluate((english)=>{
      const original=document.querySelector('svg');if(!original)return {skip:'no-svg'};
      const vb=original.viewBox.baseVal;const width=vb.width,height=vb.height;
      if(height/width<1.25||width!==720)return {skip:'already-wide-or-custom'};
      const group=Array.from(original.children).find(x=>x.tagName==='g');if(!group)return {skip:'no-content-group'};
      // 动画分期只作标记；静态图保留所有阶段，展开无样式/变换的语义分组再寻找留白。
      for(const g of Array.from(group.querySelectorAll('g')).reverse()){
        if(Array.from(g.attributes).every(a=>a.name.startsWith('data-'))){g.replaceWith(...Array.from(g.childNodes));}
      }
      const elements=Array.from(group.children).map(el=>{const b=el.getBBox();return {el,b:{x:b.x,y:b.y,width:b.width,height:b.height}}});
      const header=elements.filter(x=>x.b.y+x.b.height<=135);
      const rest=elements.filter(x=>!header.includes(x));
      // 纵向无箭头分隔线属于装饰；允许在各栏中连续保留其相交部分。
      const divider=x=>['line','path'].includes(x.el.tagName)&&!x.el.hasAttribute('marker-end')&&x.b.width===0&&x.b.height>400;
      const solids=rest.filter(x=>!divider(x));
      // Keep section headings with the next content block, not at the foot of a panel.
      const keepTogether=solids.filter(x=>x.el.tagName==='text'&&Number(x.el.getAttribute('font-weight'))>=600)
        .map(heading=>{const following=solids.filter(x=>x.b.y>=heading.b.y+heading.b.height)
          .sort((a,b)=>a.b.y-b.b.y)[0];return following?{top:heading.b.y,bottom:following.b.y+following.b.height}:null})
        .filter(Boolean);
      let choices=[];
      for(let cut=height*.38;cut<=height*.64;cut+=2){
       const intersects=solids.some(x=>x.b.y<cut+9&&x.b.y+x.b.height>cut-9)
         ||keepTogether.some(x=>x.top<cut+9&&x.bottom>cut-9);
       if(!intersects)choices.push({cut,score:Math.abs((height+135)/2-cut)});
      }
      if(!choices.length)return {skip:'no-safe-break'};
      const cut=choices.sort((a,b)=>a.score-b.score)[0].cut;
      const top=Math.min(135,...rest.map(x=>x.b.y))-4;
      const bottom=Math.max(height,...rest.map(x=>x.b.y+x.b.height))+4;
      const bands=[[top,cut],[cut,bottom]];
      const newWidth=1504,newHeight=Math.max(cut-top,bottom-cut)+205;
      const clone=original.cloneNode(false);clone.setAttribute('viewBox',`0 0 ${newWidth} ${newHeight}`);clone.setAttribute('width',newWidth);clone.setAttribute('height',newHeight);
      clone.setAttribute('data-web-layout','two-panels');clone.setAttribute('data-source-viewbox',`0 0 ${width} ${height}`);
      const ns=original.namespaceURI;const make=(tag,attrs)=>{const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,String(v));return e};
      for(const defs of original.querySelectorAll(':scope > defs'))clone.append(defs.cloneNode(true));
      clone.append(make('rect',{width:newWidth,height:newHeight,fill:'white'}));
      const content=group.cloneNode(false);clone.append(content);
      for(const x of header)content.append(x.el.cloneNode(true));
      const hint=make('text',{x:1468,y:60,fill:'#606C7B','font-size':24,'text-anchor':'end'});hint.textContent=english?'Read 1 → 2':'从左向右阅读 ① → ②';content.append(hint);
      let copied=header.length;
      bands.forEach(([start,end],index)=>{
       const offset=index*784;
       const panel=make('g',{transform:`translate(${offset},${185-start})`});content.append(panel);
       const label=make('text',{x:offset+36,y:157,fill:'#187B79','font-size':28,'font-weight':600});label.textContent=index===0?'①':'②';content.append(label);
       for(const x of rest){
        if(divider(x)){
         const y1=Math.max(start,x.b.y),y2=Math.min(end,x.b.y+x.b.height);
         if(y2>y1){const line=make('line',{x1:x.b.x,x2:x.b.x,y1,y2,stroke:x.el.getAttribute('stroke')||'#C5CDD7','stroke-width':x.el.getAttribute('stroke-width')||1});panel.append(line)}
        }else if((x.b.y+x.b.height/2>=start)&&(x.b.y+x.b.height/2<end)){
         panel.append(x.el.cloneNode(true));copied++;
        }
       }
      });
      const separator=make('line',{x1:752,y1:140,x2:752,y2:newHeight-20,stroke:'#DDE2E8','stroke-width':1});content.append(separator);
      const expected=elements.filter(x=>!divider(x)).length;
      if(copied!==expected)throw Error('SVG content lost: '+copied+'/'+expected);
      const originalText=elements.filter(x=>!divider(x)).map(x=>x.el.textContent).join('');
      const outputText=header.map(x=>x.el.textContent).join('')+bands.map(([a,b])=>rest.filter(x=>!divider(x)&&x.b.y+x.b.height/2>=a&&x.b.y+x.b.height/2<b).map(x=>x.el.textContent).join('')).join('');
      // 元素顺序可因原作者分支绘制顺序改变，完整文本节点多重集合仍必须一致。
      const sourceLabels=Array.from(group.querySelectorAll('text')).map(x=>x.textContent).sort();
      const targetLabels=Array.from(clone.querySelectorAll('text')).map(x=>x.textContent).filter(x=>x!==hint.textContent&&x!=='①'&&x!=='②').sort();
      if(JSON.stringify(sourceLabels)!==JSON.stringify(targetLabels))throw Error('SVG labels changed');
      document.body?.append(clone);
      const overflow=Array.from(clone.querySelectorAll('text')).some(x=>{const b=x.getBBox();return b.width>newWidth});
      return {svg:new XMLSerializer().serializeToString(clone),width:newWidth,height:newHeight,cut,elements:expected,labels:sourceLabels.length,overflow};
     },lang==='en');
     if(result.svg){await fs.mkdir(path.join(dir,'web'),{recursive:true});await fs.writeFile(path.join(dir,'web',name),result.svg);delete result.svg}
     else {await fs.rm(path.join(dir,'web',name),{force:true});}
     report.push({source:path.relative(root,file),...result});
    }
   }
  }
  await fs.mkdir(path.join(root,'_build'),{recursive:true});
  await fs.writeFile(path.join(root,'_build/figure-layouts.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({generated:report.filter(x=>x.cut).length,skipped:report.filter(x=>x.skip).reduce((a,x)=>(a[x.skip]=(a[x.skip]||0)+1,a),{})}));
 }finally{await browser.close()}
})();

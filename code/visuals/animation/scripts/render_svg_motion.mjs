// 与Remotion共用逐帧SVG；本机无法启动无头浏览器时直接栅格化，不改模型数据。
import {headSplitFrame, ropeFrame} from '../src/mechanisms.mjs';
import {readFile, mkdtemp, mkdir, copyFile, rm} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const column=path.resolve(root,'../../..');
const requested=process.argv.slice(2).map(Number);
const scenes=JSON.parse(await readFile(path.join(root,'course-scenes.json'),'utf8'));
const backward=scenes.find(scene=>scene.number===5);
const backwardFrames=await Promise.all(backward.frames.map(async scene=>({
  markup:await readFile(path.join(column,scene.figure),'utf8'),phase:scene.phase})));
function backwardFrame(frame) {
  // 沿用CourseProcess的分阶段规则，只同步运算框配色，不改变原来的计算分镜。
  const index=Math.min(backwardFrames.length-1,Math.floor(frame/60));
  const current=backwardFrames[index],progress=Math.min(1,(frame-index*60)/14);
  const phases=[...new Set([...current.markup.matchAll(/data-phase="(\d+)"/g)].map(m=>Number(m[1])))];
  const css=phases.map(phase=>`[data-phase="${phase}"]{opacity:${phase<current.phase?1:phase===current.phase?.12+progress*.88:.12}}`).join('');
  return current.markup.replace('</defs>',`</defs><style>${css}</style>`);
}
const jobs=[{number:5,folder:'05-backpropagation',frames:(backwardFrames.length+1)*60,height:1400,draw:backwardFrame},
  {number:12,folder:'12-multi-head-attention',frames:360,height:1200,draw:headSplitFrame},
  {number:13,folder:'13-rope',frames:300,height:1200,draw:ropeFrame}];
if(requested.some(n=>![5,12,13].includes(n)))throw new Error('此入口支持第05、12、13讲的逐帧SVG动图');
const work=await mkdtemp(path.join(tmpdir(),'course-geometry-'));
try {
  for(const job of jobs.filter(j=>!requested.length||requested.includes(j.number))) {
    const frames=path.join(work,String(job.number));await mkdir(frames);
    for(let frame=0;frame<job.frames;frame++) {
      execFileSync('rsvg-convert',['--width','720','--output',path.join(frames,String(frame).padStart(5,'0')+'.png')],
        {input:job.draw(frame),maxBuffer:1024*1024});
    }
    const mp4=path.join(work,job.number+'.mp4'),gif=path.join(work,job.number+'.gif');
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-framerate','30',
      '-i',path.join(frames,'%05d.png'),'-c:v','libx264','-pix_fmt','yuv420p',
      '-crf','20','-movflags','+faststart',mp4],{stdio:'inherit'});
    execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-i',mp4,'-filter_complex',
      'fps=10,scale=648:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
      '-loop','0',gif],{stdio:'inherit'});
    // 两种格式都编码成功后才更新正文素材，中途失败时原成品仍可使用。
    const target=path.join(column,'chapters',job.folder,'images');
    await copyFile(mp4,path.join(target,'过程.mp4'));
    await copyFile(gif,path.join(target,'过程.gif'));
    console.log(`${job.folder}：720×${job.height} / 30fps / ${job.frames/30}秒，GIF同步完成`);
  }
} finally {
  await rm(work,{recursive:true,force:true});
}

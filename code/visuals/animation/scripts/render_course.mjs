import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill, renderMedia} from '@remotion/renderer';
import {readFile, readdir, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const column=path.resolve(root,'../../..');
process.chdir(root);
const requested=process.argv.filter(s=>/^\d{2}$/.test(s));
const introOnly=process.argv.includes('--intro');
const include=n=>!introOnly&&(!requested.length||requested.includes(String(n).padStart(2,'0')));
const scenes=JSON.parse(await readFile(path.join(root,'course-scenes.json'),'utf8'));
const work=await mkdtemp(path.join(tmpdir(),'course-remotion-'));
let browser;
try {
 const serveUrl=await bundle({entryPoint:path.join(root,'src/index.ts'),outDir:path.join(work,'bundle')});
 browser=await openBrowser('chrome');
 if(!process.argv.includes('--only-motion')) {
  const folders=(await readdir(path.join(column,'chapters'))).filter(s=>(/^\d\d-/.test(s)&&!s.startsWith('01-'))||s==='intro').sort();
  for(const folder of folders) {
   if(folder==='intro') {
    if(requested.length&&!introOnly)continue;
   } else if(!include(Number(folder.slice(0,2))))continue;
   const directory=path.join(column,'chapters',folder,'images');
   const names=(await readdir(directory)).filter(s=>/^\d\d-.*\.svg$/.test(s)).sort();
   for(const name of names) {
    let markup=await readFile(path.join(directory,name),'utf8');
    const rootTag=markup.match(/<svg\b[^>]*>/s)[0];
    const viewbox=rootTag.match(/viewBox="([^"]+)"/)[1].trim().split(/\s+/).map(Number);
    const height=Math.round(1080*viewbox[3]/viewbox[2]);
    const normalized=rootTag.replace(/width="[^"]+"/,'width="1080"').replace(/height="[^"]+"/,`height="${height}"`);
    markup=markup.replace(rootTag,normalized);
    const inputProps={markup,height,phases:[0]};
    const composition=await selectComposition({serveUrl,id:'CourseFigure',inputProps,puppeteerInstance:browser});
    await renderStill({serveUrl,composition,inputProps,output:path.join(directory,name.replace(/\.svg$/,'.png')),
      imageFormat:'png',overwrite:true,puppeteerInstance:browser});
   }
   console.log('静态图:',folder);
  }
 }
 if(!process.argv.includes('--only-stills')) {
  for(const scene of scenes) {
   if(!include(scene.number))continue;
   const markup=await readFile(path.join(column,scene.figure),'utf8');
   const frames=await Promise.all(scene.frames.map(async f=>({markup:await readFile(path.join(column,f.figure),'utf8'),phase:f.phase})));
   const inputProps={markup,height:scene.motion_height??scene.height,phases:scene.phases,frames,number:scene.number};
   const composition=await selectComposition({serveUrl,id:'CourseProcess',inputProps,puppeteerInstance:browser});
   const directory=path.join(column,'chapters',scene.folder,'images');
   const mp4=path.join(directory,'过程.mp4');
   await renderMedia({serveUrl,composition,inputProps,codec:'h264',pixelFormat:'yuv420p',
     outputLocation:mp4,scale:2/3,concurrency:2,overwrite:true,puppeteerInstance:browser});
   execFileSync('ffmpeg',['-hide_banner','-loglevel','error','-y','-i',mp4,'-filter_complex',
     'fps=10,scale=648:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
     '-loop','0',path.join(directory,'过程.gif')],{stdio:'inherit'});
   console.log('动画:',scene.folder,composition.durationInFrames/composition.fps+'s');
  }
 }
}finally {
 if(browser)await browser.close({silent:true});
 await rm(work,{recursive:true,force:true});
}

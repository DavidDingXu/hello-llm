import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderStill, renderMedia} from '@remotion/renderer';
import {mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const images=path.resolve(root, '../../../chapters/01-neuron/images');
const work=await mkdtemp(path.join(tmpdir(), 'neuron-remotion-'));
const onlyNetwork=process.argv.includes('--only-network');
let browser;
try {
  const serveUrl=await bundle({entryPoint:path.join(root,'src/index.ts'),outDir:path.join(work,'bundle')});
  browser=await openBrowser('chrome');
  const figures={roles:'01-输入与参数',products:'02-两条乘法路径',
    chain:'06-连接两个神经元',flow:'07-完整计算',network:'09-从神经元到神经网络'};
  for(const [figure,name] of Object.entries(figures)) {
    if(onlyNetwork && figure!=='network') continue;
    if(process.argv.includes('--only-flow') && figure!=='flow') continue;
    const inputProps={figure};
    const composition=await selectComposition({serveUrl,id:'NeuronFigure',inputProps,puppeteerInstance:browser});
    await renderStill({serveUrl,composition,inputProps,output:path.join(images,name+'.png'),
      imageFormat:'png',overwrite:true,puppeteerInstance:browser});
    console.log('PNG:',name);
  }
  if(!onlyNetwork){
  const film=await selectComposition({serveUrl,id:'NeuronFlow',puppeteerInstance:browser});
  let reported=-1;
  await renderMedia({serveUrl,composition:film,codec:'h264',pixelFormat:'yuv420p',
    outputLocation:path.join(images,'07-神经元六步计算.mp4'),scale:2/3,concurrency:2,
    overwrite:true,puppeteerInstance:browser,onProgress:({progress})=>{
      const bucket=Math.floor(progress*5);if(bucket!==reported){reported=bucket;console.log('视频:',bucket*20+'%');}
    }});
  console.log('14 秒无声动画已导出。');
  }
} finally {
  if(browser) await browser.close({silent:true});
  await rm(work,{recursive:true,force:true});
}

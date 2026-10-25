import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { COPY } from './xray-copy.mjs';
import { validateData } from './xray-model.mjs';

if (!process.argv[2]) throw new Error('Use python visuals/model3d.py to load and verify saved pretrained weights.');
const here = new URL('./', import.meta.url);
const data = JSON.parse(await readFile(process.argv[2], 'utf8'));
validateData(data);
const template = await readFile(new URL('xray-page.template', here), 'utf8');
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
await build({
  entryPoints: [fileURLToPath(new URL('xray-view.mjs', here))],
  outfile: fileURLToPath(new URL('../reading_site/model3d.js', here)),
  bundle: true, minify: true, format: 'iife', target: ['es2020'], legalComments: 'inline', logLevel: 'warning',
  banner: { js: '/* Three.js 0.186.1 (MIT); see tensor3d-LICENSE.txt. Generated from visuals/tensor3d/xray-view.mjs. */' },
});
for (const lang of ['zh', 'en']) {
  const strings = COPY[lang];
  const payload = JSON.stringify({ lang, ...data }).replaceAll('<', '\\u003c');
  const extra = { language: lang === 'zh' ? 'zh-CN' : 'en', article: lang === 'en' ? 'index.en.html' : 'index.html',
    staticPath: `images/${lang === 'en' ? 'en/' : ''}04-一个位置的64项变化.png` };
  const page = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === 'payload') return payload;
    if (!(key in strings) && !(key in extra)) throw new Error(`Missing text ${lang}.${key}`);
    return escape(extra[key] ?? strings[key]);
  });
  await writeFile(new URL(`../../../chapters/16-transformer/lab3d${lang === 'en' ? '.en' : ''}.html`, here), page);
}
console.log('Lesson 16: verified saved weights, bilingual offline 3D pages, and model3d.js rebuilt.');

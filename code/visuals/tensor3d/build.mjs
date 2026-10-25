// Build once; readers need neither Node nor network access, including file://.
import { build } from 'esbuild';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { COPY } from './copy.mjs';
import { cellsFromRecord } from './model.mjs';

const here = new URL('./', import.meta.url);
const record = JSON.parse(await readFile(new URL('../../artifacts/lessons/l12.json', here)));
cellsFromRecord(record); // Reject stale/mismatched records before publishing a visual.
const data = { x: record.x, split: record.split, merged: record.merged };
const template = await readFile(new URL('./page.template', here), 'utf8');
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

await build({
  entryPoints: [fileURLToPath(new URL('./view.mjs', here))],
  outfile: fileURLToPath(new URL('../reading_site/tensor3d.js', here)),
  bundle: true, minify: true, format: 'iife', target: ['es2020'],
  legalComments: 'inline', logLevel: 'warning',
  banner: { js: '/* Three.js 0.186.1 (MIT); see tensor3d-LICENSE.txt. Generated from visuals/tensor3d/. */' }
});
await writeFile(new URL('../reading_site/tensor3d-LICENSE.txt', here), await readFile(new URL('./node_modules/three/LICENSE', here)));

for (const lang of ['zh', 'en']) {
  const strings = COPY[lang];
  const payload = JSON.stringify({ lang, record: data }).replaceAll('<', '\\u003c');
  const page = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === 'payload') return payload;
    if (key === 'article') return lang === 'en' ? 'index.en.html' : 'index.html';
    if (key === 'staticPath') return `images/${lang === 'en' ? 'en/' : ''}04-只看格子怎样拆.png`;
    if (!(key in strings)) throw new Error(`Missing text: ${key}`);
    return escape(strings[key]);
  });
  const filename = lang === 'en' ? 'lab3d.en.html' : 'lab3d.html';
  const target = new URL(`../../../chapters/12-multi-head-attention/${filename}`, here);
  await mkdir(new URL('./', target), { recursive: true });
  await writeFile(target, page);
}
console.log('Lesson 12: bilingual 3D lab and offline bundle rebuilt from l12.json.');

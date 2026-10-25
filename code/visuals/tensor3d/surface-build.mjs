// Rebuild with: node visuals/tensor3d/surface-build.mjs. All reader assets are local IIFEs.
import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { COPY } from './surface-copy.mjs';
import { validateRecord } from './surface-model.mjs';
const here = new URL('./', import.meta.url);
const record = validateRecord(JSON.parse(await readFile(new URL('../../artifacts/lessons/l04.json', here))));
if (record.x !== 2 || record.w !== 1 || record.target !== 6) throw new Error('Lesson 04 copy expects the saved x=2, w=1, target=6 example; update the copy with the data.');
const template = await readFile(new URL('./surface-page.template', here), 'utf8');
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
await build({ entryPoints: [fileURLToPath(new URL('./surface-view.mjs', here))], outfile: fileURLToPath(new URL('../reading_site/surface3d.js', here)), bundle: true, minify: true, format: 'iife', target: ['es2020'], legalComments: 'inline', logLevel: 'warning', banner: { js: '/* Three.js 0.186.1 (MIT); see tensor3d-LICENSE.txt. Generated from tensor3d/surface-view.mjs. */' } });
for (const lang of ['zh', 'en']) {
  const strings = COPY[lang], extra = { article: `index${lang === 'en' ? '.en' : ''}.html`, staticPath: `images/${lang === 'en' ? 'en/' : ''}03-两个参数的损失曲面.png` };
  const page = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === 'payload') return JSON.stringify({ lang, record: { x: record.x, w: record.w, target: record.target } }).replaceAll('<', '\\u003c');
    if (!(key in strings) && !(key in extra)) throw new Error(`Missing surface text: ${lang}.${key}`);
    return escape(extra[key] ?? strings[key]);
  });
  await writeFile(new URL(`../../../chapters/04-gradients/lab3d${lang === 'en' ? '.en' : ''}.html`, here), page);
}
console.log('Lesson 04: verified l04.json, bilingual offline Three.js loss surface and surface3d.js rebuilt.');

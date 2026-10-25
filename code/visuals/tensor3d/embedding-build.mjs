import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { COPY } from './embedding-copy.mjs';
import { validateData } from './embedding-model.mjs';

const here = new URL('./', import.meta.url);
const data = JSON.parse(await readFile(new URL('../../artifacts/lessons/l07.json', here), 'utf8'));
validateData(data);
const template = await readFile(new URL('embedding-page.template', here), 'utf8');
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
await build({
  entryPoints: [fileURLToPath(new URL('embedding-view.mjs', here))],
  outfile: fileURLToPath(new URL('../reading_site/embedding3d.js', here)),
  bundle: true, minify: true, format: 'iife', target: ['es2020'], legalComments: 'inline', logLevel: 'warning',
  banner: { js: '/* Three.js 0.186.1 (MIT); see tensor3d-LICENSE.txt. Generated from visuals/tensor3d/embedding-view.mjs. */' },
});
for (const lang of ['zh', 'en']) {
  const strings = COPY[lang], payload = JSON.stringify({ lang, ...data }).replaceAll('<', '\\u003c');
  const extra = { language: lang === 'zh' ? 'zh-CN' : 'en', article: lang === 'en' ? 'index.en.html' : 'index.html',
    staticPath: `images/${lang === 'en' ? 'en/' : ''}03-三个轴怎样数.png` };
  const page = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === 'payload') return payload;
    if (!(key in strings) && !(key in extra)) throw new Error(`Missing text ${lang}.${key}`);
    return escape(extra[key] ?? strings[key]);
  });
  await writeFile(new URL(`../../../chapters/07-embeddings/lab3d${lang === 'en' ? '.en' : ''}.html`, here), page);
}
console.log('Lesson 07: saved hand calculation verified; bilingual offline Embedding 3D pages rebuilt.');

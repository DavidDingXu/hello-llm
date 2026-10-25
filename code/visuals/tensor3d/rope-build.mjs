import { build } from 'esbuild';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { COPY } from './rope-copy.mjs';
import { frequencies, verifyRecord } from './rope-model.mjs';

const here = new URL('./', import.meta.url);
const record = JSON.parse(await readFile(new URL('../../artifacts/lessons/l13.json', here), 'utf8'));
const configSource = await readFile(new URL('../../tiny_lm/model.py', here), 'utf8');
const scalar = name => {
  const match = configSource.match(new RegExp(`\\b${name}:\\s*(?:int|float)\\s*=\\s*([0-9.eE+-]+)`));
  if (!match) throw new Error(`Missing course configuration ${name}`);
  return Number(match[1]);
};
const theta = scalar('rope_theta'), formalWidth = scalar('d_model') / scalar('n_heads'), maximum = scalar('max_seq_len') - 1;
verifyRecord(record, theta, formalWidth);
const seedQ = record.q[0][0][0], seedK = record.k[0][0][0];
if (seedQ.length !== 2 || seedK.length !== 2) throw new Error('The teaching preset requires the saved 2D content pair.');
const data = { theta, formalWidth, maximum, q: [...seedQ, ...seedQ], k: [...seedK, ...seedK], v: [...seedQ, ...seedQ],
  frequencies: frequencies(formalWidth, theta), source: 'l13.json + tiny_lm/rope.py + ModelConfig' };
const template = await readFile(new URL('rope-page.template', here), 'utf8');
const escape = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
await build({
  entryPoints: [fileURLToPath(new URL('rope-view.mjs', here))], outfile: fileURLToPath(new URL('../reading_site/rope3d.js', here)),
  bundle: true, minify: true, format: 'iife', target: ['es2020'], legalComments: 'inline', logLevel: 'warning',
  banner: { js: '/* Three.js 0.186.1 (MIT); see tensor3d-LICENSE.txt. Generated from visuals/tensor3d/rope-view.mjs. */' },
});
for (const lang of ['zh', 'en']) {
  const strings = COPY[lang], payload = JSON.stringify({ lang, ...data }).replaceAll('<', '\\u003c');
  const extra = { language: lang === 'zh' ? 'zh-CN' : 'en', maximum, article: lang === 'en' ? 'index.en.html' : 'index.html', staticPath: `images/${lang === 'en' ? 'en/' : ''}01-机制.png` };
  const page = template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === 'payload') return payload;
    if (!(key in strings) && !(key in extra)) throw new Error(`Missing text ${lang}.${key}`);
    return escape(extra[key] ?? strings[key]);
  });
  await writeFile(new URL(`../../../chapters/13-rope/lab3d${lang === 'en' ? '.en' : ''}.html`, here), page);
}
console.log('Lesson 13: saved-record verification, bilingual offline RoPE pages, and rope3d.js rebuilt.');

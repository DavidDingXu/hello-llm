import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { cellsFromRecord, indexAt, shapeAt, positionAt } from './model.mjs';

const record = JSON.parse(await readFile(new URL('../../artifacts/lessons/l12.json', import.meta.url)));

test('every displayed cell follows the saved PyTorch split and merged results', () => {
  const cells = cellsFromRecord(record);
  assert.equal(cells.length, 12);
  for (const cell of cells) {
    const [b, h, t, d] = indexAt(cell, 2);
    assert.equal(record.split[b][h][t][d], cell.value);
    const [mb, mt, md] = indexAt(cell, 4);
    assert.equal(record.merged[mb][mt][md], cell.value);
  }
});

test('the tracked 4 moves to head 0, position 1; axes retain their meanings', () => {
  const cell = cellsFromRecord(record).find(c => c.value === 4);
  assert.deepEqual(indexAt(cell, 0), [0, 1, 0]);
  assert.deepEqual(indexAt(cell, 1), [0, 1, 0, 0]);
  assert.deepEqual(indexAt(cell, 2), [0, 0, 1, 0]);
  assert.deepEqual(indexAt(cell, 3), [0, 1, 0, 0]);
  assert.deepEqual(indexAt(cell, 4), [0, 1, 0]);
  assert.deepEqual(shapeAt(record, 2), [1, 2, 3, 2]);
});

test('each stage has distinct spatial slots and merging restores the original layout', () => {
  const cells = cellsFromRecord(record);
  for (let stage = 0; stage < 5; stage++) {
    assert.equal(new Set(cells.map(c => JSON.stringify(positionAt(c, stage)))).size, 12);
  }
  for (const cell of cells) assert.deepEqual(positionAt(cell, 0), positionAt(cell, 4));
});

test('bad or stale records are rejected rather than silently showing invented values', () => {
  const bad = structuredClone(record);
  bad.split[0][0][1][0] = 999;
  assert.throws(() => cellsFromRecord(bad), /split/);
});

test('both generated labs show the current saved lesson data', async () => {
  for (const name of ['lab3d.html', 'lab3d.en.html']) {
    const page = await readFile(new URL(`../../../chapters/12-multi-head-attention/${name}`, import.meta.url), 'utf8');
    const embedded = JSON.parse(page.match(/<script id="tensor-data" type="application\/json">(.*?)<\/script>/s)[1]);
    assert.deepEqual(embedded.record, { x: record.x, split: record.split, merged: record.merged });
  }
});

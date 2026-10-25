import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateData, initialBatch, batchValues, inspectCell, replaceId } from './embedding-model.mjs';

const data = JSON.parse(await readFile(new URL('../../artifacts/lessons/l07.json', import.meta.url), 'utf8'));

test('uses the saved lesson 07 vocabulary and reproduces its lookup result', () => {
  assert.equal(validateData(data), true);
  assert.deepEqual(data.tokens.map(token => data.vocab.indexOf(token)), data.ids);
  assert.deepEqual(batchValues(data, initialBatch(data))[0], data.toy_selected);
});

test('two independent sequences preserve the batch, position and feature axes', () => {
  const ids = initialBatch(data), values = batchValues(data, ids);
  assert.deepEqual(ids, [[2, 1, 2], [1, 2, 1]]);
  assert.deepEqual(values, [[[1, 1], [0, 1], [1, 1]], [[0, 1], [1, 1], [0, 1]]]);
  const cell = inspectCell(data, ids, 1, 2, 0);
  assert.equal(cell.id, 1); assert.equal(cell.value, 0);
  assert.deepEqual(cell.address, [1, 2, 0]);
});

test('repeated IDs select one shared parameter row across positions and batches', () => {
  const ids = initialBatch(data), cell = inspectCell(data, ids, 0, 0, 1);
  assert.deepEqual(cell.row, [1, 1]);
  assert.deepEqual(cell.matches, [[0, 0], [0, 2], [1, 1]]);
  for (const [b, t] of cell.matches) assert.deepEqual(batchValues(data, ids)[b][t], cell.row);
});

test('changing an input ID replaces only its output row and leaves the table fixed', () => {
  const ids = initialBatch(data), original = JSON.stringify(data);
  const edited = replaceId(data, ids, 1, 2, 3);
  assert.deepEqual(ids, [[2, 1, 2], [1, 2, 1]]);
  assert.deepEqual(edited, [[2, 1, 2], [1, 2, 3]]);
  assert.deepEqual(batchValues(data, edited)[1], [[0, 1], [1, 1], [-1, 2]]);
  assert.equal(inspectCell(data, edited, 1, 2, 0).value, -1);
  assert.equal(JSON.stringify(data), original);
});

test('rejects invalid table indices and a corrupted saved hand calculation', () => {
  const ids = initialBatch(data);
  assert.throws(() => replaceId(data, ids, 0, 0, 27), /ID/i);
  assert.throws(() => inspectCell(data, ids, 2, 0, 0), /batch/i);
  assert.throws(() => inspectCell(data, ids, 0, 3, 0), /position/i);
  assert.throws(() => inspectCell(data, ids, 0, 0, 2), /feature/i);
  const broken = structuredClone(data); broken.toy_selected[0][0] = 10;
  assert.throws(() => validateData(broken), /saved/i);
});

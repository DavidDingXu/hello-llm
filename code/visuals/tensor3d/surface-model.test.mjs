import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateRecord, evaluate, updateParameters, sampleUpdate, domainFor } from './surface-model.mjs';
const record = JSON.parse(await readFile(new URL('../../artifacts/lessons/l04.json', import.meta.url)));
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} ≠ ${expected}`);
test('the visual uses the saved lesson values and rejects stale numerical records', () => {
  validateRecord(record);
  assert.throws(() => validateRecord({ ...record, loss: 17 }));
  for (const row of record.curve) close(evaluate(record, row.w, 0).loss, row.loss);
});
test('weight-only updates reproduce both saved learning-rate comparisons', () => {
  for (const expected of record.updates) {
    const result = updateParameters(record, { w: record.w, b: 0 }, expected.lr, false);
    close(result.w, expected.w); close(result.b, 0);
    close(evaluate(record, result.w, result.b).prediction, expected.prediction);
    close(evaluate(record, result.w, result.b).loss, expected.loss);
  }
});
test('both parameters use gradients from the same old point', () => {
  const start = { w: 1, b: 0 };
  const small = updateParameters(record, start, .1, true);
  close(small.w, 2.6); close(small.b, .8); close(evaluate(record, small.w, small.b).loss, 0);
  const large = updateParameters(record, start, .3, true);
  close(large.w, 5.8); close(large.b, 2.4); close(evaluate(record, large.w, large.b).loss, 64);
  assert.deepEqual(start, { w: 1, b: 0 });
});
test('the update path recomputes loss between endpoints and captures an overshoot', () => {
  const start = { w: 1, b: 0 }, end = updateParameters(record, start, .3, true);
  const path = sampleUpdate(record, start, end, 96);
  assert.equal(path.length, 97); close(path[0].loss, 16); close(path.at(-1).loss, 64);
  path.forEach(point => close(point.loss, evaluate(record, point.w, point.b).loss));
  assert.ok(Math.min(...path.map(point => point.loss)) < .01);
  assert.notEqual(path[48].loss, (16 + 64) / 2);
});
test('plot and slider domains include escaped parameters and all prior endpoints', () => {
  let point = { w: 1, b: 0 }; const history = [point];
  for (let i = 0; i < 5; i++) { point = updateParameters(record, point, .3, true); history.push(point); }
  const domain = domainFor(record, point, history);
  history.forEach(p => { assert.ok(p.w >= domain.w[0] && p.w <= domain.w[1]); assert.ok(p.b >= domain.b[0] && p.b <= domain.b[1]); });
  for (const w of domain.w) for (const b of domain.b) assert.ok(evaluate(record, w, b).loss <= domain.maxLoss + 1e-8);
});
test('zero loss has zero gradient and invalid values cannot poison the scene', () => {
  const value = evaluate(record, 3, 0); close(value.gw, 0); close(value.gb, 0);
  assert.deepEqual(updateParameters(record, { w: 3, b: 0 }, .3, true), { w: 3, b: 0 });
  assert.throws(() => updateParameters(record, { w: 1, b: 0 }, Infinity, true));
  assert.throws(() => evaluate(record, NaN, 0));
});

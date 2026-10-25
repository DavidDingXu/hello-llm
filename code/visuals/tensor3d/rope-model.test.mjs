import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { frequencies, rotate, evaluate, compare, verifyRecord } from './rope-model.mjs';
const record = JSON.parse(await readFile(new URL('../../artifacts/lessons/l13.json', import.meta.url), 'utf8'));
const near = (a, b, epsilon = 1e-12) => assert.ok(Math.abs(a - b) < epsilon, `${a} != ${b}`);
const vectorNear = (a, b) => { assert.equal(a.length, b.length); a.forEach((value, i) => near(value, b[i])); };
const q = [1, 0, 1, 0], k = [1, 0, 1, 0], v = [2, -1, .3, .5];

test('rotation reproduces every saved Q/K row and dot product in lesson 13', () => {
  assert.equal(verifyRecord(record, 10000, 32), true);
  for (let i = 0; i < 3; i++) {
    vectorNear(rotate(record.q[0][0][i], record.positions[i]), record.rotated_q[0][0][i]);
    vectorNear(rotate(record.k[0][0][i], record.positions[i]), record.rotated_k[0][0][i]);
    for (let j = 0; j < 3; j++) near(evaluate([1, 0], [1, 0], [2, 3], i, j).score, record.dots[0][0][i][j]);
  }
});

test('d=4 uses two independent planes at frequencies 1 and 0.01, preserving coordinate order', () => {
  vectorNear(frequencies(4), [1, .01]);
  vectorNear(rotate(q, 1), [.5403023058681398, .8414709848078965, .9999500004166653, .009999833334166664]);
  vectorNear(rotate([2, 1], Math.atan2(.6, .8)), [1, 2]);
  vectorNear(rotate([3, 4], Math.PI / 2), [-4, 3]);
  vectorNear(frequencies(32), record.frequencies_d32);
});

test('full dot product is the sum of the two plane contributions; V is unchanged', () => {
  const result = evaluate(q, k, v, 1, 0);
  assert.equal(result.qRot.length, 4); assert.equal(result.kRot.length, 4);
  near(result.pairs[0].dot, .5403023058681398);
  near(result.pairs[1].dot, .9999500004166653);
  near(result.score, 1.540252306284805);
  assert.deepEqual(result.v, v); assert.notEqual(result.v, v);
  vectorNear(result.pairs[1].qBefore, [1, 0]);
});

test('every pair and the full vector preserve length for arbitrary content and positions', () => {
  const content = [2, 1, -3, 4];
  for (const position of [0, 1, 10, 31, -3]) {
    const rotated = rotate(content, position);
    near(Math.hypot(...rotated), Math.sqrt(30));
    near(Math.hypot(...rotated.slice(0, 2)), Math.sqrt(5));
    near(Math.hypot(...rotated.slice(2)), 5);
  }
});

test('common translation preserves the dot product for unequal content as well as identical content', () => {
  for (const [a, b] of [[q, k], [[2, 1, -3, 4], [-1, .3, 2, 1]]]) {
    for (const m of [0, 1, 7, 20]) for (const n of [0, 2, 8, 18]) {
      const result = compare(a, b, v, m, n, m + 3, n + 3);
      near(result.before.score, result.after.score);
      near(result.error, 0);
    }
  }
});

test('changing only K position changes this example and the captured comparison stays fixed', () => {
  const result = compare(q, k, v, 1, 0, 1, 1);
  near(result.before.score, 1.540252306284805); near(result.after.score, 2);
  assert.ok(result.error > .45);
  evaluate(q, k, v, 15, 3);
  assert.equal(result.before.m, 1); assert.equal(result.before.n, 0);
  assert.equal(result.after.m, 1); assert.equal(result.after.n, 1);
  near(result.before.score, 1.540252306284805);
});

test('rejects odd width, mismatched vectors, invalid positions, and corrupted saved rotation', () => {
  assert.throws(() => rotate([1, 2, 3], 1), /even/i);
  assert.throws(() => evaluate(q, [1, 0], v, 0, 1), /shape/i);
  assert.throws(() => rotate(q, NaN), /position/i);
  assert.throws(() => frequencies(4, 0), /theta/i);
  const broken = structuredClone(record); broken.rotated_q[0][0][1][0] += .01;
  assert.throws(() => verifyRecord(broken, 10000, 32), /saved/i);
});

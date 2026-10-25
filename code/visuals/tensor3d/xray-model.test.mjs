import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { STAGES, validateData, stageValues, inspectCoordinate, projection, attentionRead } from './xray-model.mjs';

// Use the saved-weight page, not a second hand-authored numeric fixture.
const page = await readFile(new URL('../../../chapters/16-transformer/model-inspector.html', import.meta.url), 'utf8');
const data = JSON.parse(page.match(/<script id="model-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const close = (a, b, tolerance = 1e-5) => assert.ok(Math.abs(a - b) < tolerance, `${a} ≠ ${b}`);

test('saved record has 14 positions, 64 internal coordinates, and a separate 79-candidate axis', () => {
  assert.equal(validateData(data), true);
  assert.equal(STAGES.length, 9);
  assert.equal(stageValues(data, 0, 7).length, 64);
  assert.equal(stageValues(data, 8, 7).length, 79);
  assert.equal(data.tokens[data.trace.ids[0][7]], '欢');
});

test('every attention residual equals its two saved branches at every position and coordinate', () => {
  for (const stage of [2, 5]) for (let p = 0; p < 14; p++) for (let c = 0; c < 64; c++) {
    const item = inspectCoordinate(data, stage, p, c);
    close(item.left + item.right, item.value);
    close(item.value, stageValues(data, stage, p)[c]);
  }
});

test('final RMSNorm uses all 64 squares, epsilon, and the matching learned scale', () => {
  for (let p = 0; p < 14; p++) for (let c = 0; c < 64; c++) {
    const x = data.trace.blocks[1].block_output[0][p];
    const item = inspectCoordinate(data, 7, p, c);
    const rms = Math.sqrt(x.reduce((sum, value) => sum + value * value, 0) / 64 + data.norm_eps);
    close(item.denominator, rms);
    close(item.value, x[c] / rms * data.final_scale[c]);
    close(item.value, data.trace.normalized[0][p][c]);
  }
});

test('candidate score is a signed sum of exactly 64 products and probabilities normalize over 79', () => {
  for (let p = 0; p < 14; p++) {
    const result = projection(data, p, 55);
    assert.equal(result.probabilities.length, 79);
    close(result.probabilities.reduce((a, b) => a + b, 0), 1, 1e-12);
    for (let candidate = 0; candidate < 79; candidate++) {
      const output = projection(data, p, candidate);
      assert.equal(output.products.length, 64);
      close(output.products.reduce((a, b) => a + b, 0), data.trace.logits[0][p][candidate], 1e-4);
      close(output.score, data.trace.logits[0][p][candidate]);
    }
  }
});

test('real attention retains causal zeroes and expands the selected V coordinate', () => {
  for (let block = 0; block < 2; block++) for (let head = 0; head < 2; head++) for (let p = 0; p < 14; p++) {
    const read = attentionRead(data, block, head, p, 13);
    assert.equal(read.items.length, 14);
    close(read.items.reduce((sum, item) => sum + item.weight, 0), 1);
    read.items.forEach((item, index) => {
      assert.equal(item.blocked, index > p);
      if (index > p) assert.equal(item.weight, 0);
      close(item.product, data.trace.blocks[block].weights[0][head][p][index] * data.trace.blocks[block].v[0][head][index][13]);
    });
    close(read.value, read.items.reduce((sum, item) => sum + item.product, 0));
  }
});

test('validation rejects a mismatched output matrix or a future attention leak', () => {
  const output = structuredClone(data); output.output_weights[55][0] += 1;
  assert.throws(() => validateData(output), /projection/i);
  const leak = structuredClone(data); leak.trace.blocks[0].weights[0][0][0][1] = .1;
  assert.throws(() => validateData(leak), /causal/i);
});

// Pure record inspection; no training or browser-side parameter updates.
export const STAGES = [
  { key: 'embedding', kind: 'embedding' },
  { key: 'output', kind: 'attention', block: 0 },
  { key: 'after_attention', kind: 'residual', block: 0 },
  { key: 'block_output', kind: 'feedforward', block: 0 },
  { key: 'output', kind: 'attention', block: 1 },
  { key: 'after_attention', kind: 'residual', block: 1 },
  { key: 'block_output', kind: 'feedforward', block: 1 },
  { key: 'normalized', kind: 'normalization' },
  { key: 'logits', kind: 'projection' },
];
export function stageValues(data, stage, position) {
  const descriptor = STAGES[stage];
  const source = descriptor.block === undefined ? data.trace : data.trace.blocks[descriptor.block];
  return source[descriptor.key][0][position];
}
export function inspectCoordinate(data, stage, position, coordinate) {
  const descriptor = STAGES[stage], value = stageValues(data, stage, position)[coordinate];
  if (descriptor.kind === 'residual' || descriptor.kind === 'feedforward') {
    const block = data.trace.blocks[descriptor.block];
    const left = (descriptor.kind === 'residual' ? block.input : block.after_attention)[0][position][coordinate];
    const right = descriptor.kind === 'residual' ? block.output[0][position][coordinate] : value - left;
    return { value, left, right, derived: descriptor.kind === 'feedforward' };
  }
  if (descriptor.kind === 'normalization') {
    const vector = data.trace.blocks[1].block_output[0][position];
    const meanSquare = vector.reduce((sum, x) => sum + x * x, 0) / vector.length;
    return { value, input: vector[coordinate], scale: data.final_scale[coordinate], meanSquare,
      denominator: Math.sqrt(meanSquare + data.norm_eps) };
  }
  return { value };
}
export function projection(data, position, candidate) {
  const scores = data.trace.logits[0][position], maximum = Math.max(...scores);
  const exponents = scores.map(score => Math.exp(score - maximum));
  const denominator = exponents.reduce((a, b) => a + b, 0);
  const products = data.trace.normalized[0][position].map((x, coordinate) => x * data.output_weights[candidate][coordinate]);
  return { score: scores[candidate], products, probabilities: exponents.map(value => value / denominator) };
}
export function attentionRead(data, block, head, position, coordinate) {
  const record = data.trace.blocks[block], weights = record.weights[0][head][position];
  const items = weights.map((weight, source) => {
    const value = record.v[0][head][source][coordinate];
    return { source, weight, value, product: weight * value, blocked: source > position };
  });
  return { items, value: items.reduce((sum, item) => sum + item.product, 0) };
}
export function validateData(data) {
  const { trace, output_weights: matrix } = data, positions = trace.ids[0].length;
  const fail = message => { throw new Error(`Invalid saved forward record: ${message}`); };
  const near = (a, b, tolerance = 1e-5) => Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) < tolerance;
  if (positions !== 14 || trace.blocks.length !== 2 || data.tokens.length !== 79 || matrix.length !== 79) fail('shape');
  for (let p = 0; p < positions; p++) {
    for (let stage = 0; stage < STAGES.length; stage++) {
      const vector = stageValues(data, stage, p);
      if (vector.length !== (stage === 8 ? 79 : 64) || !vector.every(Number.isFinite)) fail('coordinate width');
    }
    for (let block = 0; block < 2; block++) {
      const record = trace.blocks[block];
      const expectedInput = block === 0 ? trace.embedding[0][p] : trace.blocks[block - 1].block_output[0][p];
      expectedInput.forEach((value, c) => { if (!near(value, record.input[0][p][c])) fail('block input'); });
      for (let c = 0; c < 64; c++) {
        if (!near(record.input[0][p][c] + record.output[0][p][c], record.after_attention[0][p][c])) fail('residual');
      }
      for (let head = 0; head < record.weights[0].length; head++) {
        const weights = record.weights[0][head][p];
        if (weights.some((value, source) => source > p && value !== 0)) fail('causal mask');
        if (!near(weights.reduce((a, b) => a + b, 0), 1)) fail('attention probability sum');
        const scores = record.scores[0][head][p].slice(0, p + 1), max = Math.max(...scores);
        const sum = scores.reduce((total, score) => total + Math.exp(score - max), 0);
        scores.forEach((score, source) => { if (!near(weights[source], Math.exp(score - max) / sum)) fail('attention softmax'); });
      }
    }
    for (let c = 0; c < 64; c++) {
      const item = inspectCoordinate(data, 7, p, c);
      if (!near(item.input / item.denominator * item.scale, item.value)) fail('RMSNorm');
    }
    for (let candidate = 0; candidate < 79; candidate++) {
      if (matrix[candidate].length !== 64) fail('projection width');
      const output = projection(data, p, candidate);
      if (!near(output.products.reduce((a, b) => a + b, 0), output.score, 1e-4)) fail('projection weights mismatch');
    }
  }
  return true;
}

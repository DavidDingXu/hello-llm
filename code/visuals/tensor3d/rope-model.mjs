// Numerical inspection of adjacent-coordinate RoPE; no training or learned state.
export function frequencies(width, theta = 10000) {
  if (!Number.isInteger(width) || width < 2 || width % 2) throw new Error('RoPE requires positive even width');
  if (!Number.isFinite(theta) || theta <= 0) throw new Error('RoPE theta must be positive');
  return Array.from({ length: width / 2 }, (_, i) => theta ** (-2 * i / width));
}
export function rotate(vector, position, theta = 10000) {
  if (!Number.isFinite(position)) throw new Error('RoPE position must be finite');
  if (!vector.every(Number.isFinite)) throw new Error('RoPE coordinates must be finite');
  return frequencies(vector.length, theta).flatMap((frequency, i) => {
    const angle = position * frequency, cosine = Math.cos(angle), sine = Math.sin(angle);
    const [a, b] = vector.slice(i * 2, i * 2 + 2);
    return [a * cosine - b * sine, a * sine + b * cosine];
  });
}
export function evaluate(q, k, v, m, n, theta = 10000) {
  if (q.length !== k.length || q.length !== v.length) throw new Error('Q/K/V shape mismatch');
  const qRot = rotate(q, m, theta), kRot = rotate(k, n, theta);
  const pairs = frequencies(q.length, theta).map((frequency, index) => {
    const start = index * 2, end = start + 2;
    return { index, coordinates: [start, start + 1], frequency, angleQ: m * frequency, angleK: n * frequency,
      qBefore: q.slice(start, end), kBefore: k.slice(start, end), q: qRot.slice(start, end), k: kRot.slice(start, end),
      dot: qRot[start] * kRot[start] + qRot[start + 1] * kRot[start + 1] };
  });
  return { m, n, difference: n - m, qRot, kRot, v: [...v], pairs,
    score: pairs.reduce((sum, pair) => sum + pair.dot, 0), normQ: Math.hypot(...qRot), normK: Math.hypot(...kRot) };
}
export function compare(q, k, v, m, n, nextM, nextN, theta = 10000) {
  const before = evaluate(q, k, v, m, n, theta), after = evaluate(q, k, v, nextM, nextN, theta);
  return { before, after, error: Math.abs(after.score - before.score) };
}
export function verifyRecord(record, theta = 10000, formalWidth = 32) {
  const near = (actual, expected) => {
    if (!Number.isFinite(actual) || !Number.isFinite(expected) || Math.abs(actual - expected) > 1e-12) throw new Error('Saved lesson 13 record does not match RoPE');
  };
  frequencies(formalWidth, theta).forEach((frequency, i) => near(frequency, record.frequencies_d32[i]));
  record.positions.forEach((position, i) => {
    const q = record.q[0][0][i], k = record.k[0][0][i];
    const rq = rotate(q, position, theta), rk = rotate(k, position, theta);
    rq.forEach((value, c) => near(value, record.rotated_q[0][0][i][c]));
    rk.forEach((value, c) => near(value, record.rotated_k[0][0][i][c]));
    near(Math.hypot(...q), record.norm_before[0][0][i]);
    near(Math.hypot(...rq), record.norm_after[0][0][i]);
    record.positions.forEach((keyPosition, j) => {
      near(evaluate(q, record.k[0][0][j], q, position, keyPosition, theta).score, record.dots[0][0][i][j]);
      near(evaluate(q, record.k[0][0][j], q, position + 7, keyPosition + 7, theta).score, record.shifted_dots[0][0][i][j]);
    });
  });
  return true;
}

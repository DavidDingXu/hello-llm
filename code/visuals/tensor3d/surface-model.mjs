// Pure numerical model shared by the renderer, build validation and regression tests.
const finite = (...values) => {
  if (!values.every(Number.isFinite)) throw new RangeError('Surface values must be finite.');
};
const close = (a, b) => Math.abs(a - b) <= 1e-8 * Math.max(1, Math.abs(a), Math.abs(b));
export function evaluate(record, w, b) {
  finite(record.x, record.target, w, b);
  const prediction = record.x * w + b, error = prediction - record.target;
  const loss = error * error, gw = 2 * error * record.x, gb = 2 * error;
  finite(prediction, loss, gw, gb);
  return { prediction, error, loss, gw, gb };
}
export function updateParameters(record, point, rate, both = true) {
  finite(rate);
  if (rate < 0) throw new RangeError('The learning rate must be nonnegative.');
  const { gw, gb } = evaluate(record, point.w, point.b);
  // Both derivatives are from the same old point; never recalculate gb after changing w.
  const next = { w: point.w - rate * gw, b: both ? point.b - rate * gb : point.b };
  evaluate(record, next.w, next.b);
  return next;
}
export function sampleUpdate(record, from, to, count = 64) {
  if (!Number.isInteger(count) || count < 2) throw new RangeError('At least two path intervals are required.');
  return Array.from({ length: count + 1 }, (_, i) => {
    const t = i / count, w = from.w + (to.w - from.w) * t, b = from.b + (to.b - from.b) * t;
    return { w, b, loss: evaluate(record, w, b).loss };
  });
}
export function domainFor(record, point, history = []) {
  const points = [point, ...history];
  points.forEach(p => evaluate(record, p.w, p.b));
  const ws = [0, 4, ...points.map(p => p.w)], bs = [-1, 3, ...points.map(p => p.b)];
  const padded = values => {
    const minimum = Math.min(...values), maximum = Math.max(...values), pad = Math.max(.35, (maximum - minimum) * .08);
    return [minimum - pad, maximum + pad];
  };
  const w = padded(ws), b = padded(bs);
  const maxLoss = Math.max(1, ...w.flatMap(weight => b.map(bias => evaluate(record, weight, bias).loss)));
  return { w, b, maxLoss };
}
export function validateRecord(record) {
  const initial = evaluate(record, record.w, 0);
  for (const key of ['prediction', 'loss']) if (!close(initial[key], record[key])) throw new Error(`l04.json ${key} does not match the surface.`);
  if (!close(initial.gw, record.gradient)) throw new Error('l04.json gradient does not match the surface.');
  for (const row of record.updates) {
    const point = updateParameters(record, { w: record.w, b: 0 }, row.lr, false), value = evaluate(record, point.w, point.b);
    if (!close(point.w, row.w) || !close(value.prediction, row.prediction) || !close(value.loss, row.loss)) throw new Error('l04.json update does not match the surface.');
  }
  for (const row of record.curve) if (!close(evaluate(record, row.w, 0).loss, row.loss)) throw new Error('l04.json curve does not match the surface.');
  return record;
}

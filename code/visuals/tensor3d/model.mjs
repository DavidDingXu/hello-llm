// Coordinates describe tensor indexing, not physical positions or semantic features.
export function cellsFromRecord(record) {
  const heads = record.split[0].length;
  const width = record.x[0][0].length;
  if (record.x.length !== 1 || width % heads) throw new Error('Expected one batch and divisible width');
  const cells = record.x.flatMap((batch, b) => batch.flatMap((row, t) => row.map((value, feature) => {
    const d = width / heads, h = Math.floor(feature / d), coordinate = feature % d;
    if (record.split[b][h][t][coordinate] !== value) throw new Error('Saved split does not match input');
    if (record.merged[b][t][feature] !== value) throw new Error('Saved merged does not match input');
    return { value, b, t, feature, h, d: coordinate, width, heads,
      positions: batch.length, headWidth: d };
  })));
  return cells;
}

export function indexAt(cell, stage) {
  const { b, t, feature, h, d } = cell;
  if (stage === 0 || stage === 4) return [b, t, feature];
  return stage === 2 ? [b, h, t, d] : [b, t, h, d];
}

export function shapeAt(record, stage) {
  const b = record.x.length, t = record.x[0].length, width = record.x[0][0].length;
  const h = record.split[0].length, d = width / h;
  if (stage === 0 || stage === 4) return [b, t, width];
  return stage === 2 ? [b, h, t, d] : [b, t, h, d];
}

export function positionAt(cell, stage) {
  const { t, feature, h, d, width, positions, heads, headWidth } = cell;
  if (stage === 0 || stage === 4) return [(feature - (width - 1) / 2) * 1.3, ((positions - 1) / 2 - t) * 1.3, 0];
  const x = (d - (headWidth - 1) / 2) * 1.3;
  // View axes are the last three tensor axes: right, up, depth. Batch 0 is fixed.
  return stage === 2
    ? [x, ((heads - 1) / 2 - h) * 2.1, ((positions - 1) / 2 - t) * 1.8]
    : [x, ((positions - 1) / 2 - t) * 1.3, (h - (heads - 1) / 2) * 2.1];
}

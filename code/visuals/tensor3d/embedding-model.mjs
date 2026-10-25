// The saved hand calculation is the sole source of table values and token IDs.
const index = (value, length, axis) => {
  if (!Number.isInteger(value) || value < 0 || value >= length) throw new RangeError(`Invalid ${axis} index`);
};

export function validateData(data) {
  if (!Array.isArray(data.toy_table) || data.toy_table.length !== 4 ||
      data.toy_table.some(row => row.length !== 2 || row.some(value => !Number.isFinite(value)))) {
    throw new Error('Invalid saved embedding table');
  }
  if (data.vocab.length !== data.vocab_size || data.tokens.some((token, i) => data.vocab[data.ids[i]] !== token)) {
    throw new Error('Invalid saved vocabulary');
  }
  const selected = data.toy_ids.map(id => { index(id, data.toy_table.length, 'ID'); return data.toy_table[id]; });
  if (JSON.stringify(selected) !== JSON.stringify(data.toy_selected)) throw new Error('Saved lookup differs from table');
  return true;
}

export function initialBatch(data) {
  // The second sequence is the article's example: swap the first two demo IDs.
  const [a, b] = data.toy_ids;
  return [data.toy_ids.slice(), data.toy_ids.map(id => id === a ? b : a)];
}

export function batchValues(data, ids) {
  return ids.map(sample => sample.map(id => {
    index(id, data.toy_table.length, 'ID');
    return data.toy_table[id].slice();
  }));
}

export function inspectCell(data, ids, batch, position, feature) {
  index(batch, ids.length, 'batch'); index(position, ids[batch].length, 'position');
  const id = ids[batch][position]; index(id, data.toy_table.length, 'ID');
  const row = data.toy_table[id]; index(feature, row.length, 'feature');
  const matches = [];
  ids.forEach((sample, b) => sample.forEach((candidate, t) => { if (candidate === id) matches.push([b, t]); }));
  return { id, row: row.slice(), value: row[feature], address: [batch, position, feature], matches };
}

export function replaceId(data, ids, batch, position, id) {
  index(id, data.toy_table.length, 'ID'); inspectCell(data, ids, batch, position, 0);
  return ids.map((sample, b) => sample.map((old, t) => b === batch && t === position ? id : old));
}

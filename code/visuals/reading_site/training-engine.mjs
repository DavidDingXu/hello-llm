// The model and gradient graph are exported from the course's PyTorch implementation.
const runtimeBase = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.30.0/dist/';
const manifestURL = new URL('./training/model.json', import.meta.url);
const probes = [
  {prompt: '早上，小丁喜欢', limit: 8},
  {prompt: '问：小丁喜欢什么水果？\n答：', limit: 8},
  {prompt: '问：小丁最喜欢的水果是什么？\n答：', limit: 8},
  {prompt: '早上，小丁选了', limit: 16},
];

export function readableSamples(data) {
  return Object.fromEntries(Object.entries(data.groups).map(([group, records]) => [group,
    records.map(record => group.startsWith('sft')
      ? {record_id: record.record_id, prompt: record.prompt, answer: record.answer}
      : {record_id: record.record_id, text: record.ids.filter(id => id >= 4).map(id => data.tokens[id]).join('')})]));
}

function sampleError(code, edit = {}, extra = {}) {
  throw Object.assign(new Error(code), {sampleError: {code, group: edit?.group,
    record_id: edit?.record_id, ...extra}});
}

export function applySampleEdits(data, edits = [], maxLength = 32) {
  if (!Array.isArray(edits) || edits.length > 280) sampleError('INVALID_SAMPLE');
  const groups = {...data.groups}, raw = readableSamples(data);
  const vocabulary = new Map(data.tokens.map((token, index) => [token, index]));
  const seen = new Set();
  for (const edit of edits) {
    if (!edit || !['pretrain_train', 'sft_train'].includes(edit.group)) sampleError('READ_ONLY_GROUP', edit);
    const {group, record_id: id} = edit, index = data.groups[group].findIndex(row => row.record_id === id);
    if (index < 0 || seen.has(group + ':' + id)) sampleError('INVALID_SAMPLE', edit);
    seen.add(group + ':' + id);
    const sft = group === 'sft_train', values = {};
    for (const field of sft ? ['prompt', 'answer'] : ['text']) {
      if (typeof edit[field] !== 'string' || !edit[field].trim()) sampleError('EMPTY_SAMPLE', edit, {field});
      values[field] = edit[field].replaceAll('\r\n', '\n');
    }
    const text = sft ? values.prompt + values.answer : values.text;
    const characters = Array.from(text);
    const unknown = [...new Set(characters.filter(character => !vocabulary.has(character)))];
    if (unknown.length) sampleError('UNKNOWN_CHARACTER', edit, {characters: unknown.slice(0, 8),
      field: Object.keys(values).find(field => Array.from(values[field]).some(character => !vocabulary.has(character)))});
    if (characters.length + 1 > maxLength) sampleError('TOO_LONG', edit, {limit: maxLength - 1,
      field: sft && Array.from(values.prompt).length < maxLength ? 'answer' : sft ? 'prompt' : 'text'});
    const heldOut = [...raw.pretrain_val.map(row => row.text), ...raw.sft_val.map(row => row.prompt)];
    if (heldOut.some(example => text.includes(example))) {
      sampleError('VALIDATION_OVERLAP', edit, {field: sft ? 'prompt' : 'text'});
    }
    const tokens = [1, ...characters.map(character => vocabulary.get(character)), 2];
    const ids = tokens.slice(0, -1), targets = tokens.slice(1);
    // The last prompt token predicts the first answer character; that target stays scored.
    if (sft) targets.fill(-100, 0, Array.from(values.prompt).length);
    while (ids.length < maxLength) { ids.push(0); targets.push(-100); }
    if (groups[group] === data.groups[group]) groups[group] = [...groups[group]];
    groups[group][index] = {...data.groups[group][index], ...values, text, ids, targets};
  }
  return groups;
}

export function adamStep(parameters, gradients, iteration, learningRate, settings) {
  let squared = 0;
  for (const gradient of gradients) for (const value of gradient) squared += value * value;
  const norm = Math.sqrt(squared);
  if (!Number.isFinite(norm)) throw new Error('NON_FINITE');
  const scale = Math.min(1, settings.clip_norm / (norm + 1e-6));
  const [beta1, beta2] = settings.betas;
  const correction1 = 1 - beta1 ** iteration, correction2 = 1 - beta2 ** iteration;
  parameters.forEach((parameter, index) => {
    const gradient = gradients[index];
    for (let i = 0; i < gradient.length; i++) {
      const value = gradient[i] * scale;
      parameter.moment[i] = beta1 * parameter.moment[i] + (1 - beta1) * value;
      parameter.variance[i] = beta2 * parameter.variance[i] + (1 - beta2) * value * value;
      const mean = parameter.moment[i] / correction1;
      const variance = parameter.variance[i] / correction2;
      parameter.values[i] = parameter.values[i] * (1 - learningRate * settings.weight_decay)
        - learningRate * mean / (Math.sqrt(variance) + settings.eps);
    }
  });
  return norm;
}

function optionsFor(options, manifest) {
  if (!['quick', 'pretrain', 'sft', 'pipeline'].includes(options.mode)) throw new Error('INVALID_OPTIONS');
  const stages = options.mode === 'pipeline' ? ['pretrain', 'sft'] : [options.mode];
  return stages.map((stage, i) => {
    const steps = Number(i ? options.sftSteps : options.steps);
    const learningRate = Number(i ? options.sftLearningRate : options.learningRate);
    if (!Number.isInteger(steps) || steps < 1 || steps > manifest.max_steps
        || !Number.isFinite(learningRate) || learningRate < 0.000001 || learningRate > 0.1) {
      throw new Error('INVALID_OPTIONS');
    }
    return {...manifest.presets[stage], stage, steps, learning_rate: learningRate};
  });
}

export class TrainingEngine {
  static async create() {
    const response = await fetch(manifestURL);
    if (!response.ok) throw new Error('LOAD_FAILED');
    const manifest = await response.json();
    const read = async name => {
      const response = await fetch(new URL(name, manifestURL));
      if (!response.ok) throw new Error('LOAD_FAILED');
      const buffer = await response.arrayBuffer();
      if (buffer.byteLength !== manifest.files[name].bytes) throw new Error('ASSET_MISMATCH');
      if (globalThis.crypto?.subtle) {
        const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', buffer)),
          value => value.toString(16).padStart(2, '0')).join('');
        if (hash !== manifest.files[name].sha256) throw new Error('ASSET_MISMATCH');
      }
      return buffer;
    };
    const [ort, training, evaluation, initial, pretrained, data] = await Promise.all([
      import(runtimeBase + 'ort.wasm.min.mjs'), read('train-step.onnx'), read('evaluate.onnx'),
      read('initial.f32'), read('pretrained.f32'), read('data.json'),
    ]);
    ort.env.wasm.numThreads = 1;
    ort.env.wasm.wasmPaths = runtimeBase;
    const sessionOptions = {executionProviders: ['wasm'], graphOptimizationLevel: 'all'};
    const session = await ort.InferenceSession.create(training, sessionOptions);
    const evaluator = await ort.InferenceSession.create(evaluation, sessionOptions);
    return new TrainingEngine(ort, manifest, JSON.parse(new TextDecoder().decode(data)),
      new Float32Array(initial), new Float32Array(pretrained), session, evaluator);
  }

  constructor(ort, manifest, data, initial, pretrained, session, evaluator) {
    Object.assign(this, {ort, manifest, data, initial, pretrained, session, evaluator});
  }

  reset(start) {
    const values = (start === 'sft' ? this.pretrained : this.initial).slice();
    this.parameters = this.manifest.parameters.map(parameter => ({...parameter,
      values: values.subarray(parameter.offset, parameter.offset + parameter.length),
      moment: new Float32Array(parameter.length), variance: new Float32Array(parameter.length),
    }));
  }

  batch(records) {
    const {batch_size: batch, sequence_length: positions} = this.manifest;
    if (!records.length || records.length > batch) throw new Error('INVALID_BATCH');
    const ids = new BigInt64Array(batch * positions);
    const targets = new BigInt64Array(batch * positions).fill(-100n);
    let count = 0;
    records.forEach((record, row) => {
      record.ids.forEach((value, index) => ids[row * positions + index] = BigInt(value));
      record.targets.forEach((value, index) => {
        targets[row * positions + index] = BigInt(value);
        if (value !== -100) count++;
      });
    });
    if (!count) throw new Error('INVALID_BATCH');
    return {ids, targets, count};
  }

  async calculate(session, batch) {
    const {Tensor} = this.ort;
    const shape = [this.manifest.batch_size, this.manifest.sequence_length];
    const feeds = Object.fromEntries(this.parameters.map(p => [p.input, new Tensor('float32', p.values, p.shape)]));
    feeds.ids = new Tensor('int64', batch.ids, shape);
    feeds.targets = new Tensor('int64', batch.targets, shape);
    try { return await session.run(feeds); }
    finally { Object.values(feeds).forEach(tensor => tensor.dispose()); }
  }

  async evaluate(records) {
    let total = 0, count = 0;
    for (let offset = 0; offset < records.length; offset += this.manifest.batch_size) {
      const batch = this.batch(records.slice(offset, offset + this.manifest.batch_size));
      const result = await this.calculate(this.evaluator, batch);
      total += result.loss.data[0] * batch.count; count += batch.count;
      Object.values(result).forEach(tensor => tensor.dispose());
    }
    const loss = total / count;
    if (!Number.isFinite(loss)) throw new Error('NON_FINITE');
    return loss;
  }

  async generate(prompt, limit = 8) {
    const {tokens} = this.data;
    const ids = [1, ...Array.from(prompt).map(character => tokens.indexOf(character))];
    if (ids.some(value => value < 0 || value === 3) || ids.length > this.manifest.sequence_length) {
      throw new Error('UNKNOWN_PROMPT');
    }
    let text = '', stop = 'max_new_tokens';
    for (let step = 0; step < limit; step++) {
      if (ids.length > this.manifest.sequence_length) { stop = 'context_limit'; break; }
      // One live row, with unscored padding rows to match the exported graph's batch shape.
      const labels = Array(ids.length).fill(-100); labels[0] = 2;
      const result = await this.calculate(this.evaluator, this.batch([{ids, targets: labels}]));
      const start = (ids.length - 1) * tokens.length;
      let selected = 2;
      for (let index = 2; index < tokens.length; index++) {
        if (index !== 3 && result.logits.data[start + index] > result.logits.data[start + selected]) selected = index;
      }
      Object.values(result).forEach(tensor => tensor.dispose());
      ids.push(selected);
      if (selected === 2) { stop = 'eos'; break; }
      text += tokens[selected];
    }
    return {prompt, text, stop, max_new_tokens: limit};
  }

  async generateAll() {
    const outputs = [];
    for (const probe of probes) outputs.push(await this.generate(probe.prompt, probe.limit));
    return outputs;
  }

  async run(options, onProgress) {
    const recipes = optionsFor(options, this.manifest);
    const edits = options.sampleEdits || [];
    const groups = applySampleEdits(this.data, edits, this.manifest.sequence_length);
    const allowedGroups = options.mode === 'pipeline' ? ['pretrain_train', 'sft_train']
      : [options.mode === 'sft' ? 'sft_train' : 'pretrain_train'];
    if (edits.some(edit => !allowedGroups.includes(edit.group))) sampleError('INVALID_SAMPLE');
    const readable = readableSamples({...this.data, groups});
    this.reset(options.mode);
    const started = performance.now();
    const report = {mode: options.mode, model_sources: this.manifest.sources, recipes,
      optimizer: this.manifest.optimizer, batch_shape: [this.manifest.batch_size, this.manifest.sequence_length],
      history: {}, generations: {initial: await this.generateAll()}, edited_outputs: [],
      data: {modified: edits.length, edits, source_sha256: this.manifest.files['data.json'].sha256, samples: {}}};
    onProgress({type: 'initial', generations: report.generations.initial});
    for (const recipe of recipes) {
      const {stage, steps, learning_rate: learningRate} = recipe;
      const key = stage === 'quick' ? 'pretrain' : stage;
      let training = groups[key + '_train'], validation = groups[key + '_val'];
      if (stage === 'quick') { training = training.slice(0, 4); validation = validation.slice(0, 4); }
      for (const [suffix, selected] of [['_train', training], ['_val', validation]]) {
        const ids = new Set(selected.map(row => row.record_id));
        report.data.samples[key + suffix] = readable[key + suffix].filter(row => ids.has(row.record_id));
      }
      // Each training stage uses a fresh optimizer, as _fit does in tiny_lm/train.py.
      this.parameters.forEach(p => { p.moment.fill(0); p.variance.fill(0); });
      const history = report.history[stage] = [];
      const record = async step => {
        const trainLoss = await this.evaluate(training), valLoss = await this.evaluate(validation);
        const point = {step, train_loss: trainLoss, val_loss: valLoss}; history.push(point);
        const generations = await this.generateAll();
        report.generations[stage] = generations;
        onProgress({type: 'snapshot', stage, steps, point, generations});
      };
      onProgress({type: 'stage', stage, steps, training: training.length, validation: validation.length});
      await record(0);
      for (let step = 1; step <= steps; step++) {
        const records = stage === 'quick' ? training
          : this.data.schedules[stage][step - 1].map(index => training[index]);
        const result = await this.calculate(this.session, this.batch(records));
        try {
          if (!Number.isFinite(result.loss.data[0])) throw new Error('NON_FINITE');
          const gradients = this.parameters.map((_, index) => result['grad_' + index].data);
          adamStep(this.parameters, gradients, step, learningRate, this.manifest.optimizer);
        } finally { Object.values(result).forEach(tensor => tensor.dispose()); }
        const interval = stage === 'quick' ? 10 : 50;
        if (step % interval === 0 || step === steps) await record(step);
        if (step % 5 === 0) {
          onProgress({type: 'progress', stage, step, steps});
          await new Promise(resolve => setTimeout(resolve, 0));
        }
      }
      if (stage === 'sft') {
        onProgress({type: 'checking'});
        report.answers = {};
        for (const group of ['sft_train', 'sft_val']) {
          const answers = [];
          for (const record of groups[group]) {
            const output = await this.generate(record.prompt, Array.from(record.answer).length + 1);
            answers.push({record_id: record.record_id, prompt: record.prompt,
              expected: record.answer, actual: output.text, stop: output.stop,
              exact_match: output.text === record.answer && output.stop === 'eos'});
          }
          report.answers[group] = answers;
        }
        onProgress({type: 'answers', answers: report.answers});
      }
      for (const edit of edits.filter(item => item.group === key + '_train').slice(0, 3)) {
        const record = readable[key + '_train'].find(row => row.record_id === edit.record_id);
        let prompt, expected, output;
        if (stage === 'sft') {
          prompt = record.prompt; expected = record.answer;
          const checked = report.answers.sft_train.find(row => row.record_id === record.record_id);
          output = {text: checked.actual, stop: checked.stop};
        } else {
          const characters = Array.from(record.text), split = Math.min(7, Math.floor(characters.length / 2));
          prompt = characters.slice(0, split).join(''); expected = characters.slice(split).join('');
          output = await this.generate(prompt, Array.from(expected).length + 1);
        }
        report.edited_outputs.push({stage, record_id: record.record_id, prompt, expected,
          actual: output.text, stop: output.stop});
      }
      if (report.edited_outputs.length) onProgress({type: 'edited', examples: report.edited_outputs});
    }
    report.elapsed_ms = performance.now() - started;
    return report;
  }
}

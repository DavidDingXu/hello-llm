// The model and gradient graph are exported from the course's PyTorch implementation.
const runtimeBase = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.30.0/dist/';
const manifestURL = new URL('./training/model.json', import.meta.url);
const probes = [
  {prompt: '早上，小丁喜欢', limit: 8},
  {prompt: '问：小丁喜欢什么水果？\n答：', limit: 8},
  {prompt: '问：小丁最喜欢的水果是什么？\n答：', limit: 8},
  {prompt: '早上，小丁选了', limit: 16},
];

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
    if (ids.some(value => value < 0 || value === 3) || ids.length >= this.manifest.sequence_length) {
      throw new Error('UNKNOWN_PROMPT');
    }
    let text = '', stop = 'max_new_tokens';
    for (let step = 0; step < limit; step++) {
      if (ids.length >= this.manifest.sequence_length) { stop = 'context_limit'; break; }
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
    this.reset(options.mode);
    const started = performance.now();
    const report = {mode: options.mode, model_sources: this.manifest.sources, recipes,
      optimizer: this.manifest.optimizer, batch_shape: [this.manifest.batch_size, this.manifest.sequence_length],
      history: {}, generations: {initial: await this.generateAll()}};
    onProgress({type: 'initial', generations: report.generations.initial});
    for (const recipe of recipes) {
      const {stage, steps, learning_rate: learningRate} = recipe;
      const key = stage === 'quick' ? 'pretrain' : stage;
      let training = this.data.groups[key + '_train'], validation = this.data.groups[key + '_val'];
      if (stage === 'quick') { training = training.slice(0, 4); validation = validation.slice(0, 4); }
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
          for (const record of this.data.groups[group]) {
            const output = await this.generate(record.prompt);
            answers.push({record_id: record.record_id, prompt: record.prompt,
              expected: record.answer, actual: output.text, stop: output.stop,
              exact_match: output.text === record.answer && output.stop === 'eos'});
          }
          report.answers[group] = answers;
        }
        onProgress({type: 'answers', answers: report.answers});
      }
    }
    report.elapsed_ms = performance.now() - started;
    return report;
  }
}

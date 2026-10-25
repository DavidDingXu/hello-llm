// Pyodide is loaded only after the reader presses Run. Keep work off the UI thread.
const runtimeURL = 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
let python;
let busy = false;
const limit = 50000;

self.onmessage = async ({data}) => {
  if (busy || data.type !== 'run') return;
  busy = true;
  let output = '', truncated = false;
  const append = text => {
    const remaining = limit - output.length;
    if (remaining > 0) output += (String(text) + '\n').slice(0, remaining);
    if (remaining <= String(text).length) truncated = true;
  };
  let globals, started = false;
  try {
    if (!python) {
      self.postMessage({type: 'loading'});
      const {loadPyodide} = await import(runtimeURL + 'pyodide.mjs');
      python = await loadPyodide({indexURL: runtimeURL, stdout: append, stderr: append});
      python.FS.mkdirTree('/course/tiny_lm');
      await python.runPythonAsync('import sys\nsys.path.insert(0, "/course")');
    }
    python.setStdout({batched: append});
    python.setStderr({batched: append});
    for (const [name, source] of Object.entries(data.modules)) {
      if (!['__init__.py', 'scalar.py', 'manual_mlp.py'].includes(name)) throw new Error('Unexpected course module');
      python.FS.writeFile('/course/tiny_lm/' + name, source);
    }
    await python.runPythonAsync('import sys\nfor name in list(sys.modules):\n    if name == "tiny_lm" or name.startswith("tiny_lm."):\n        del sys.modules[name]');
    globals = python.toPy({__name__: '__main__'});
    output = ''; truncated = false;
    started = true;
    self.postMessage({type: 'running'});
    await python.runPythonAsync(data.code, {globals});
    self.postMessage({type: 'result', output, truncated});
  } catch (error) {
    self.postMessage({type: 'error', phase: started ? 'execution' : 'loading', output, truncated, error: String(error).slice(0, 12000)});
  } finally {
    globals?.destroy();
    busy = false;
  }
};

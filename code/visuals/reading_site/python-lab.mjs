const lab = document.querySelector('.python-lab');
if (lab && location.protocol !== 'file:' && typeof Worker !== 'undefined') {
  const english = document.documentElement.lang === 'en';
  const t = (zh, en) => english ? en : zh;
  const code = lab.querySelector('.lab-code'), output = lab.querySelector('.lab-output');
  const run = lab.querySelector('.lab-run'), stop = lab.querySelector('.lab-stop');
  const reset = lab.querySelector('.lab-reset'), status = lab.querySelector('.lab-status');
  const fields = [...lab.querySelectorAll('[data-variable]')];
  const initial = code.value, values = fields.map(field => field.value);
  let worker, timer, active = false, epoch = 0, codeEdited = false;
  let editor;
  import(new URL('./code-editor.mjs' + new URL(import.meta.url).search, import.meta.url))
    .then(({enhanceCodeEditor}) => { editor = enhanceCodeEditor(code); })
    .catch(() => {
      const help = lab.querySelector('.lab-editor-help');
      if (help) help.textContent = t('基础编辑模式：Tab 切换焦点。修改后点击运行，或按 Ctrl / ⌘ + Enter。', 'Basic editor: Tab moves focus. Run after editing, or press Ctrl / ⌘ + Enter.');
    });
  const pendingFields = new Set();
  function showStatus(message) {
    status.textContent = (codeEdited ? t('以编辑器代码为准。', 'Using the edited code. ') : '') + message;
  }
  function setBusy(value) {
    active = value; run.disabled = value; stop.disabled = !value;
    reset.disabled = value; code.readOnly = value;
    fields.forEach(field => field.disabled = value);
    lab.setAttribute('aria-busy', String(value));
  }
  function finish(message) { clearTimeout(timer); setBusy(false); showStatus(message); }
  function terminate(message) {
    epoch++; worker?.terminate(); worker = null;
    finish(message);
  }
  function applyField(field) {
    if (!field.checkValidity() || !field.value) return false;
    const assignment = new RegExp('^' + field.dataset.variable + '\\s*=.*$', 'm');
    if (!assignment.test(code.value)) {
      status.textContent = t('代码中的对应赋值已移除，请直接编辑代码或恢复示例。', 'This assignment was removed. Edit the code directly or reset the example.');
      return false;
    }
    code.value = code.value.replace(assignment, field.dataset.variable + ' = ' + field.value);
    editor?.refresh();
    pendingFields.delete(field);
    status.textContent = t('参数已写入代码，点击运行查看结果。', 'Parameter updated in the code. Run to see the result.');
    return true;
  }
  fields.forEach(field => {
    field.addEventListener('input', () => { codeEdited = false; pendingFields.add(field); });
    field.addEventListener('change', () => {
      codeEdited = false; pendingFields.add(field);
      if (!field.reportValidity()) return;
      applyField(field);
    });
  });
  // After a direct code edit, reflect simple assignments without rewriting the reader’s code.
  code.addEventListener('input', () => {
    codeEdited = true; pendingFields.clear();
    fields.forEach(field => {
      const value = code.value.match(new RegExp('^' + field.dataset.variable + '\\s*=\\s*(-?[\\d.eE+]+|True|False)\\s*(?:#.*)?$', 'm'))?.[1];
      if (value !== undefined) field.value = value;
    });
    showStatus(t('参数栏只同步可识别的简单赋值；点击运行查看结果。', 'Controls reflect simple assignments only. Run to see the result.'));
  });
  code.addEventListener('keydown', event => {
    if (event.isComposing || event.keyCode === 229) return;
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); run.click(); }
  });
  reset.addEventListener('click', () => {
    codeEdited = false; pendingFields.clear();
    code.value = initial; fields.forEach((field, index) => field.value = values[index]);
    editor?.refresh();
    output.textContent = t('等待运行…', 'Ready to run…');
    status.textContent = t('已恢复本讲示例。', 'Chapter example restored.');
  });
  stop.addEventListener('click', () => terminate(t('已停止，可以修改代码后重新运行。', 'Stopped. Edit the code and run again.')));
  lab.querySelector('.lab-download').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([code.value], {type: 'text/x-python;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'hello-llm-experiment.py';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = t('已下载当前代码；本地运行时请放在仓库的 code/ 目录。', 'Downloaded the current code. Run it from the repository’s code/ directory.');
  });
  run.addEventListener('click', async () => {
    if (active) return;
    if (!codeEdited) {
      for (const field of fields) {
        if (!field.checkValidity()) {
          status.textContent = t('请填写有效的参数后再运行；尚未执行代码。', 'Enter valid parameters before running. The code has not run.');
          field.reportValidity(); field.focus(); return;
        }
      }
      for (const field of pendingFields) {
        if (!applyField(field)) {
          lab.querySelector('.lab-editor').open = true; code.focus(); return;
        }
      }
    }
    if (code.value.length > 100000) { status.textContent = t('请将实验控制在 100 KB 以内。', 'Keep this experiment under 100 KB.'); return; }
    setBusy(true); output.textContent = '';
    showStatus(t('正在准备 Python，首次加载可能需要几十秒…', 'Preparing Python. The first load can take a little while…'));
    const token = ++epoch;
    timer = setTimeout(() => terminate(t('Python 加载超时。检查网络后重试；文章和逐步演示仍可阅读。', 'Python loading timed out. Check your connection and retry; the chapter and walkthrough remain available.')), 45000);
    try {
      const response = await fetch(new URL('./python-modules.json', import.meta.url));
      if (!response.ok) throw new Error('Course modules: HTTP ' + response.status);
      const modules = await response.json();
      if (token !== epoch) return;
      if (!worker) worker = new Worker(new URL('./python-worker.mjs', import.meta.url), {type: 'module'});
      worker.onerror = () => {
        if (token === epoch) terminate(t('Python 未能启动。请检查网络后重试，或下载代码在本地运行。', 'Python could not start. Check your connection and retry, or download the code to run locally.'));
      };
      worker.onmessage = ({data}) => {
        if (token !== epoch) return;
        if (data.type === 'loading') return;
        if (data.type === 'running') {
          clearTimeout(timer);
          showStatus(t('正在运行…', 'Running…'));
          timer = setTimeout(() => terminate(t('已达到 8 秒上限，运行已停止。减少循环次数后重试。', 'Stopped after 8 seconds. Reduce the loop count and retry.')), 8000);
          return;
        }
        output.textContent = data.output || '';
        if (data.truncated) output.textContent += '\n' + t('（输出已截断，最多显示 50,000 字符。）', '(Output truncated at 50,000 characters.)');
        if (data.type === 'error') {
          output.textContent += '\n' + data.error;
          if (data.phase === 'loading') {
            terminate(t('Python 加载失败，请检查网络后重试。', 'Python could not load. Check your connection and retry.'));
          } else if (data.error.includes('ModuleNotFoundError')) {
            finish(t('此网页实验提供 Python 标准库和本讲函数。PyTorch 等其他依赖请在本地 Python 环境中运行。', 'This experiment provides the Python standard library and the chapter’s functions. Run PyTorch and other dependencies in a local Python environment.'));
          } else {
            finish(t('代码未运行完成，请查看错误并修改后重试。', 'The code did not finish. Check the error, edit and retry.'));
          }
        } else {
          if (!output.textContent) output.textContent = t('运行完成，没有打印输出。可以用 print(...) 查看数值。', 'Finished without printed output. Use print(...) to inspect values.');
          finish(t('运行完成，可以继续修改并比较结果。', 'Finished. Change the code and compare the next result.'));
        }
      };
      worker.postMessage({type: 'run', code: code.value, modules});
    } catch (error) {
      if (token !== epoch) return;
      output.textContent = String(error);
      terminate(t('加载失败。请通过学习站地址打开页面，并检查网络后重试。', 'Loading failed. Open this page through the learning-site URL and check your connection.'));
    }
  });
  addEventListener('pagehide', () => terminate(active
    ? t('离开页面后，运行已停止。可以重新运行。', 'Execution stopped when you left the page. You can run it again.')
    : status.textContent));
  setBusy(false);
  lab.querySelector('.lab-download').disabled = false;
}

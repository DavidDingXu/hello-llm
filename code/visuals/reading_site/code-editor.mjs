// A visual layer over a real textarea: execution, selection and copying use plain text.
const keywords = new Set(('False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case').split(' '));
const builtins = new Set(('abs all any bool bytes callable chr dict enumerate filter float format frozenset getattr hasattr hash hex id input int isinstance issubclass iter len list map max min next object open ord pow print property range repr reversed round set slice sorted str sum super tuple type vars zip Exception ValueError TypeError RuntimeError').split(' '));
const identifier = /[A-Za-z_\u00a0-\uffff][\w\u00a0-\uffff]*/y;
const number = /(?:0[xX][\da-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|(?:\d[\d_]*(?:\.[\d_]*)?|\.\d[\d_]*)(?:[eE][+-]?\d[\d_]*)?)[jJ]?/y;
const stringStart = /[rRuUbBfF]{0,2}(['"])/y;

export function tokenizePython(source) {
  const tokens = [];
  let index = 0, nameNext = false;
  function add(type, end) {
    const text = source.slice(index, end), previous = tokens.at(-1);
    if (previous?.type === type) previous.text += text;
    else tokens.push({type, text});
    index = end;
  }
  while (index < source.length) {
    const character = source[index];
    if (character === '#') {
      const end = source.indexOf('\n', index);
      add('comment', end < 0 ? source.length : end); continue;
    }
    stringStart.lastIndex = index;
    const opening = stringStart.exec(source);
    if (opening) {
      const quote = opening[1], quoteAt = stringStart.lastIndex - 1;
      const triple = source.slice(quoteAt, quoteAt + 3) === quote.repeat(3);
      const delimiter = quote.repeat(triple ? 3 : 1);
      let end = quoteAt + delimiter.length;
      while (end < source.length) {
        if (source[end] === '\\') { end = Math.min(source.length, end + 2); continue; }
        if (source.startsWith(delimiter, end)) { end += delimiter.length; break; }
        if (!triple && source[end] === '\n') break;
        end++;
      }
      add('string', end); nameNext = false; continue;
    }
    identifier.lastIndex = index;
    const word = identifier.exec(source);
    if (word) {
      const value = word[0];
      add(keywords.has(value) ? 'keyword' : builtins.has(value) ? 'builtin' : nameNext ? 'name' : 'plain', identifier.lastIndex);
      nameNext = value === 'def' || value === 'class'; continue;
    }
    number.lastIndex = index;
    const numeric = number.exec(source);
    if (numeric) { add('number', number.lastIndex); nameNext = false; continue; }
    add('plain', index + 1);
    if (!/\s/.test(character)) nameNext = false;
  }
  return tokens;
}

export function indentSelection(source, start, end, unindent = false) {
  const lineStart = start === 0 ? 0 : source.lastIndexOf('\n', start - 1) + 1;
  if (start === end && !unindent) {
    const spaces = ' '.repeat(4 - (start - lineStart) % 4);
    return {start, end, text: spaces, selectionStart: start + spaces.length, selectionEnd: start + spaces.length};
  }
  const lastPosition = end > start && source[end - 1] === '\n' ? end - 1 : end;
  let blockEnd = source.indexOf('\n', lastPosition);
  if (blockEnd < 0) blockEnd = source.length;
  const lines = source.slice(lineStart, blockEnd).split('\n');
  const deltas = [];
  const changed = lines.map(line => {
    const removed = unindent ? (line.match(/^(?:\t| {1,4})/)?.[0].length || 0) : 0;
    deltas.push(unindent ? -removed : 4);
    return unindent ? line.slice(removed) : '    ' + line;
  }).join('\n');
  return {start: lineStart, end: blockEnd, text: changed,
    selectionStart: Math.max(lineStart, start + deltas[0]),
    selectionEnd: Math.max(lineStart, end + deltas.reduce((sum, delta) => sum + delta, 0))};
}

export function newlineEdit(source, start, end) {
  const lineStart = start === 0 ? 0 : source.lastIndexOf('\n', start - 1) + 1;
  const before = source.slice(lineStart, start);
  const indentation = before.match(/^[ \t]*/)[0];
  const code = tokenizePython(before).filter(token => token.type !== 'comment').map(token => token.text).join('').trimEnd();
  const text = '\n' + indentation + (code.endsWith(':') ? '    ' : '');
  return {start, end, text, selectionStart: start + text.length, selectionEnd: start + text.length};
}

export function enhanceCodeEditor(textarea) {
  if (textarea.closest('.lab-code-editor')) return null;
  const wrapper = document.createElement('div'); wrapper.className = 'lab-code-editor';
  const gutter = document.createElement('div'); gutter.className = 'lab-code-gutter';
  gutter.setAttribute('aria-hidden', 'true');
  const numbers = document.createElement('pre'); numbers.className = 'lab-code-lines';
  gutter.append(numbers);
  const input = document.createElement('div'); input.className = 'lab-code-input';
  const highlight = document.createElement('pre'); highlight.className = 'lab-code-highlight';
  highlight.setAttribute('aria-hidden', 'true');
  textarea.before(wrapper); wrapper.append(gutter, input); input.append(highlight, textarea);
  if (!getComputedStyle(wrapper).getPropertyValue('--editor-bg').trim()) {
    wrapper.replaceWith(textarea);
    throw new Error('Editor styling is unavailable');
  }
  textarea.wrap = 'off';
  let composing = false, tabMovesFocus = false, frame = 0;
  let lineCount = 1, visibleNumbers = '';

  function syncScroll() {
    highlight.style.width = textarea.clientWidth + 'px';
    highlight.style.height = textarea.clientHeight + 'px';
    highlight.scrollTop = textarea.scrollTop; highlight.scrollLeft = textarea.scrollLeft;
    const lineHeight = parseFloat(getComputedStyle(textarea).lineHeight);
    const first = Math.min(lineCount - 1, Math.floor(textarea.scrollTop / lineHeight));
    const end = Math.min(lineCount, first + Math.ceil(textarea.clientHeight / lineHeight) + 1);
    const next = Array.from({length: end - first}, (_, index) => first + index + 1).join('\n');
    if (next !== visibleNumbers) { numbers.textContent = next; visibleNumbers = next; }
    gutter.style.height = textarea.clientHeight + 'px';
    numbers.style.transform = `translateY(${first * lineHeight - textarea.scrollTop}px)`;
  }
  function refresh() {
    cancelAnimationFrame(frame); frame = 0;
    const plain = composing || textarea.value.length > 100000;
    wrapper.classList.toggle('code-editor-plain', plain);
    lineCount = textarea.value.split('\n').length;
    wrapper.style.setProperty('--editor-line-digits', Math.max(2, String(lineCount).length));
    if (plain) { syncScroll(); return; }
    const fragment = document.createDocumentFragment();
    for (const token of tokenizePython(textarea.value)) {
      if (token.type === 'plain') fragment.append(document.createTextNode(token.text));
      else {
        const span = document.createElement('span'); span.className = 'py-' + token.type;
        span.textContent = token.text; fragment.append(span);
      }
    }
    // Pre ignores its terminal newline; the extra one keeps the last empty input line aligned.
    if (textarea.value.endsWith('\n')) fragment.append(document.createTextNode('\n'));
    highlight.replaceChildren(fragment); syncScroll();
  }
  function scheduleRefresh() {
    if (!frame) frame = requestAnimationFrame(refresh);
  }
  function replace(edit) {
    const scrollTop = textarea.scrollTop, scrollLeft = textarea.scrollLeft;
    if (textarea.value.slice(edit.start, edit.end) === edit.text) return;
    textarea.setSelectionRange(edit.start, edit.end);
    // Native insertion keeps browser undo history; setRangeText is the plain-text fallback.
    let inserted = false;
    try { inserted = typeof document.execCommand === 'function' && document.execCommand('insertText', false, edit.text); }
    catch (_) { /* Plain-text insertion below also works when a browser disallows the command. */ }
    if (!inserted) {
      textarea.setRangeText(edit.text, edit.start, edit.end, 'preserve');
      textarea.dispatchEvent(new Event('input', {bubbles: true}));
    }
    textarea.setSelectionRange(edit.selectionStart, edit.selectionEnd);
    textarea.scrollTop = scrollTop; textarea.scrollLeft = scrollLeft; refresh();
  }
  textarea.addEventListener('input', scheduleRefresh);
  textarea.addEventListener('scroll', syncScroll, {passive: true});
  gutter.addEventListener('wheel', event => {
    const top = textarea.scrollTop, left = textarea.scrollLeft;
    const unit = event.deltaMode === 1 ? parseFloat(getComputedStyle(textarea).lineHeight)
      : event.deltaMode === 2 ? textarea.clientHeight : 1;
    textarea.scrollTop += event.deltaY * unit;
    textarea.scrollLeft += event.deltaX * unit;
    if (textarea.scrollTop !== top || textarea.scrollLeft !== left) {
      event.preventDefault(); syncScroll();
    }
  }, {passive: false});
  textarea.addEventListener('compositionstart', () => { composing = true; refresh(); });
  textarea.addEventListener('compositionend', () => { composing = false; refresh(); });
  textarea.addEventListener('blur', () => { tabMovesFocus = false; });
  textarea.addEventListener('keydown', event => {
    if (event.isComposing || composing || event.keyCode === 229 || textarea.readOnly) return;
    if (event.key === 'Escape') { tabMovesFocus = true; event.preventDefault(); event.stopPropagation(); return; }
    if (event.key === 'Tab' && !event.ctrlKey && !event.metaKey && !event.altKey) {
      if (tabMovesFocus) { tabMovesFocus = false; return; }
      event.preventDefault();
      replace(indentSelection(textarea.value, textarea.selectionStart, textarea.selectionEnd, event.shiftKey));
    } else if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey) {
      event.preventDefault(); replace(newlineEdit(textarea.value, textarea.selectionStart, textarea.selectionEnd));
    } else { tabMovesFocus = false; }
  });
  if (typeof ResizeObserver === 'function') {
    const observer = new ResizeObserver(syncScroll); observer.observe(textarea);
  } else { addEventListener('resize', syncScroll); }
  textarea.closest('details')?.addEventListener('toggle', syncScroll);
  refresh();
  return {refresh};
}

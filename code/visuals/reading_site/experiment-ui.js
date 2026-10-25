/* Local, progressive presentation controls. No training or mathematical changes. */
(() => {
  'use strict';
  // file:// embeds cannot access each other's documents. Ask the host to close
  // its workspace; it validates that the message came from the active iframe.
  if (window.parent !== window) {
    const returnToArticle = () => window.parent.postMessage({ type: 'hello-llm:close-experiment' }, '*');
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); returnToArticle(); }
    });
    document.addEventListener('click', event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const link = event.target.closest('a[href]');
      if (!link) return;
      const target = new URL(link.href);
      if (target.origin === location.origin && /\/(?:course\/(?:intro|end|\d{2})(?:\.en)?\.html|index(?:\.en)?\.html|README(?:\.en)?\.md)$/.test(decodeURIComponent(target.pathname))) {
        event.preventDefault(); returnToArticle();
      }
    });
  }
  if (window.parent !== window && document.querySelector('main#lab, main#surface-lab')) document.body.classList.add('embedded-three');
  const figure = document.getElementById('figure');
  const layout = document.querySelector('main > .layout');
  if (!figure || !layout || !figure.querySelector('svg') || !layout.querySelector('.controls')) return;
  document.body.classList.add('demo-step');
  const english = document.documentElement.lang.startsWith('en');
  const t = (zh, en) => english ? en : zh;
  const panel = document.createElement('div'); panel.className = 'diagram-panel';
  figure.before(panel); panel.append(figure);
  const toolbar = document.createElement('div'); toolbar.className = 'diagram-toolbar';
  toolbar.setAttribute('aria-label', t('图解视图', 'Diagram view'));
  const counter = document.createElement('span'); counter.className = 'diagram-zoom';
  let scale = 1, fitMode = true, readableMode = true;
  // The loss plot's axes and tick labels belong to every step. Keep them together.
  const allowsFocus = !/^04\b/.test(document.querySelector('h1')?.textContent || '');
  let focusMode = allowsFocus;
  const originalViews = new WeakMap();
  function dimensions() {
    const svg = figure.querySelector('svg');
    if (!svg) return null;
    if (!originalViews.has(svg)) originalViews.set(svg, svg.getAttribute('viewBox'));
    svg.setAttribute('viewBox', originalViews.get(svg));
    if (focusMode) {
      const groups = Array.from(svg.querySelectorAll('[data-phase]'));
      const phase = Math.max(...groups.filter(group => Number(group.style.opacity || 1) >= .99).map(group => Number(group.dataset.phase)));
      const boxes = groups.filter(group => Number(group.dataset.phase) === phase || Number(group.dataset.phase) === phase - 1)
        .map(group => group.getBBox()).filter(box => box.width && box.height);
      if (boxes.length) {
        let left = Math.min(...boxes.map(box => box.x)) - 34, top = Math.min(...boxes.map(box => box.y)) - 28;
        let right = Math.max(...boxes.map(box => box.x + box.width)) + 34;
        let bottom = Math.max(...boxes.map(box => box.y + box.height)) + 28;
        // A fixed caption may intersect the focused stages even though it is not
        // a phase group. Include the whole caption, never a clipped text fragment.
        const fixed = Array.from(svg.querySelectorAll('text')).filter(text => !text.closest('[data-phase]'));
        const included = new Set();
        let expanded = true;
        while (expanded) {
          expanded = false;
          for (const text of fixed) {
            if (included.has(text)) continue;
            const box = text.getBBox();
            if (box.x < right + 4 && box.x + box.width > left - 4 && box.y < bottom + 4 && box.y + box.height > top - 4) {
              included.add(text); expanded = true;
              left = Math.min(left, box.x - 12); top = Math.min(top, box.y - 12);
              right = Math.max(right, box.x + box.width + 12); bottom = Math.max(bottom, box.y + box.height + 12);
            }
          }
        }
        svg.setAttribute('viewBox', `${left} ${top} ${right - left} ${bottom - top}`);
      }
      groups.forEach(group => { group.style.visibility = Number(group.dataset.phase) === phase || Number(group.dataset.phase) === phase - 1 ? '' : 'hidden'; });
    } else {
      svg.querySelectorAll('[data-phase]').forEach(group => { group.style.visibility = ''; });
    }
    const view = svg.viewBox.baseVal;
    return { svg, view, width: view.width || svg.width.baseVal.value, height: view.height || svg.height.baseVal.value };
  }
  function readableScale(d) {
    const sizes = Array.from(d.svg.querySelectorAll('text')).filter(element => {
      const group = element.closest('[data-phase]');
      if (getComputedStyle(element).visibility === 'hidden' || group && Number(group.style.opacity || 1) < .99) return false;
      const box = element.getBBox();
      return box.x < d.view.x + d.width && box.x + box.width > d.view.x && box.y < d.view.y + d.height && box.y + box.height > d.view.y;
    }).map(element => parseFloat(getComputedStyle(element).fontSize)).filter(size => size > 0);
    return sizes.length ? 12 / Math.min(...sizes) : 0;
  }
  function revealStep(d) {
    const groups = Array.from(d.svg.querySelectorAll('[data-phase]')).filter(group => Number(group.style.opacity || 1) >= .99);
    const phase = Math.max(...groups.map(group => Number(group.dataset.phase)));
    const boxes = groups.filter(group => Number(group.dataset.phase) === phase).map(group => group.getBBox()).filter(box => box.width && box.height);
    if (!boxes.length) { figure.scrollTo(0, 0); return; }
    const left = Math.min(...boxes.map(box => box.x)), top = Math.min(...boxes.map(box => box.y));
    const right = Math.max(...boxes.map(box => box.x + box.width)), bottom = Math.max(...boxes.map(box => box.y + box.height));
    // Keep the current step visible when readable type makes the graphic taller
    // than the workspace. The surrounding diagram remains available by scrolling.
    figure.scrollTo(Math.max(0, (left - d.view.x) * scale - Math.max(16, (figure.clientWidth - (right - left) * scale) / 2)),
      Math.max(0, (top - d.view.y) * scale - Math.max(16, (figure.clientHeight - (bottom - top) * scale) / 2)));
  }
  function draw(fit, reveal = false) {
    const d = dimensions(); if (!d || !d.width || !d.height) return;
    if (fit) {
      scale = Math.min(figure.clientWidth / d.width, figure.clientHeight / d.height);
      if (readableMode) scale = Math.max(scale, readableScale(d));
    }
    scale = Math.max(.06, Math.min(scale, 2));
    figure.style.setProperty('--figure-width', `${d.width * scale}px`);
    figure.style.setProperty('--figure-height', `${d.height * scale}px`);
    counter.textContent = `${Math.round(scale * 100)}%`;
    hint.hidden = d.width * scale <= figure.clientWidth + 1 && d.height * scale <= figure.clientHeight + 1;
    if (reveal && readableMode) revealStep(d);
  }
  function button(label, action, aria) {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = label;
    if (aria) b.setAttribute('aria-label', aria);
    b.addEventListener('click', action); toolbar.append(b); return b;
  }
  const modeButton = button(focusMode ? t('查看全图', 'Full diagram') : t('聚焦步骤', 'Focus step'), () => {
    focusMode = !focusMode; fitMode = true; readableMode = focusMode;
    modeButton.textContent = focusMode ? t('查看全图', 'Full diagram') : t('聚焦步骤', 'Focus step');
    draw(true, true); if (!readableMode) figure.scrollTo(0, 0);
  });
  modeButton.hidden = !allowsFocus;
  button(t('适应窗口', 'Fit diagram'), () => { fitMode = true; readableMode = false; draw(true); figure.scrollTo(0, 0); });
  button('＋', () => { fitMode = false; scale *= 1.35; draw(false); }, t('放大图解', 'Zoom in'));
  button('−', () => { fitMode = false; scale /= 1.35; draw(false); }, t('缩小图解', 'Zoom out'));
  const hint = document.createElement('span'); hint.className = 'diagram-scroll-hint';
  hint.textContent = t('图内可上下左右滚动', 'Scroll within the diagram');
  figure.tabIndex = 0;
  figure.setAttribute('aria-label', t('当前步骤图解，可在区域内滚动查看', 'Current step diagram; scroll within this region'));
  toolbar.append(hint, counter); panel.append(toolbar);
  const note = layout.querySelector('.note');
  if (note) {
    const details = document.createElement('details'); details.className = 'experiment-note';
    const summary = document.createElement('summary'); summary.textContent = t('说明', 'About this lab');
    note.before(details); details.append(summary, note);
  }
  const observer = new ResizeObserver(() => draw(fitMode)); observer.observe(figure);
  new MutationObserver(() => { fitMode = true; readableMode = focusMode || !allowsFocus; draw(true, true); }).observe(figure, { childList: true });
  draw(true, true);
})();

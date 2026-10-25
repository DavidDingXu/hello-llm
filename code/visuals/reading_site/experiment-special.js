/* Compact workspaces for the four standalone labs. Calculation and event handlers stay in their source pages. */
(() => {
  'use strict';
  const start = () => {
    const main = document.querySelector('main');
    if (!main || main.dataset.specialWorkspace) return;
    const $ = (selector, root = document) => root.querySelector(selector);
    const english = document.documentElement.lang.startsWith('en');
    const text = (zh, en) => english ? en : zh;
    const make = (tag, className, content) => {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (content) element.textContent = content;
      return element;
    };
    const details = (label, nodes, parent = main) => {
      const fold = make('details', 'special-details');
      fold.append(make('summary', '', label));
      const content = make('div', 'special-details-content');
      nodes.filter(Boolean).forEach(node => content.append(node));
      fold.append(content);
      parent.append(fold);
      return fold;
    };
    const field = (label, className = '') => {
      const wrapper = make('label', `special-picker ${className}`.trim());
      const select = make('select');
      wrapper.append(make('span', '', label), select);
      return { wrapper, select };
    };
    const activate = kind => {
      main.dataset.specialWorkspace = kind;
      document.body.classList.add('special-experiment', `special-${kind}`);
    };
    const fitRegion = (element, minimum, maximum = 720, desktopOnly = false) => {
      const fit = () => {
        if (desktopOnly && innerWidth <= 700) { element.style.removeProperty('--special-region-height'); return; }
        const top = element.getBoundingClientRect().top + scrollY;
        element.style.setProperty('--special-region-height', `${Math.max(minimum, Math.min(maximum, innerHeight - top - 72))}px`);
      };
      addEventListener('resize', fit);
      requestAnimationFrame(fit);
    };
    const scrollHint = (region, toolbar) => {
      const hint = make('span', 'special-scroll-hint', text('区域内滚动 ↓', 'Scroll here ↓'));
      hint.setAttribute('aria-hidden', 'true');
      toolbar.append(hint);
      const sync = () => { hint.hidden = region.scrollHeight <= region.clientHeight + 2; };
      new ResizeObserver(sync).observe(region);
      new MutationObserver(sync).observe(region, { childList: true, subtree: true });
      requestAnimationFrame(sync);
    };
    // The original controls are kept, with their event listeners. The selector is another way to reach them.
    const mirrorButtons = (container, select, selector, active) => {
      const sync = () => {
        const buttons = [...container.querySelectorAll(selector)];
        select.replaceChildren(...buttons.map((button, index) => {
          const option = make('option', '', button.getAttribute('aria-label') || [...button.childNodes].map(node => node.textContent.trim()).filter(Boolean).join(' '));
          option.value = String(index);
          option.selected = active(button);
          return option;
        }));
      };
      select.addEventListener('change', () => container.querySelectorAll(selector)[Number(select.value)]?.click());
      new MutationObserver(sync).observe(container, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-current', 'aria-pressed', 'class'] });
      sync();
    };

    if ($('#scene') && $('#x1') && $('.workbench')) {
      activate('neuron');
      const picture = $('.picture'), controls = $('.controls'), scene = $('#scene');
      const reference = details(text('实验说明、对照例子与来源', 'Instructions, presets and sources'), [$('.brand'), $('.intro'), $('.presets'), $('.note'), $('.explanation'), $('footer')]);
      reference.classList.add('special-reference');
      const figureTools = make('div', 'special-figure-tools');
      const focus = make('button', '', text('当前步骤', 'Current step'));
      const full = make('button', '', text('完整计算图', 'Full diagram'));
      focus.type = full.type = 'button';
      let fullDiagram = false;
      const focusFigure = () => {
        const svg = $('svg', scene);
        if (!svg) return;
        const step = Math.max(0, (parseInt($('#stepLabel').textContent, 10) || 1) - 1);
        const boxes = ['70 170 960 470', '80 180 920 680', '80 180 920 680', '120 550 840 330', '120 875 930 280', '140 1140 800 320'];
        svg.setAttribute('viewBox', fullDiagram ? '0 0 1080 1500' : boxes[step]);
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        focus.setAttribute('aria-pressed', String(!fullDiagram));
        full.setAttribute('aria-pressed', String(fullDiagram));
        scene.classList.toggle('special-full-diagram', fullDiagram);
      };
      focus.addEventListener('click', () => { fullDiagram = false; focusFigure(); });
      full.addEventListener('click', () => { fullDiagram = true; focusFigure(); });
      figureTools.append(focus, full);
      picture.insertBefore(figureTools, scene);
      new MutationObserver(focusFigure).observe(scene, { childList: true });
      focusFigure();
      const picker = field(text('调整哪一个数', 'Adjust a value'), 'special-neuron-picker');
      const labels = [...controls.querySelectorAll('label[for]')];
      const sections = [...controls.querySelectorAll(':scope > section')];
      labels.forEach((label, index) => {
        const labelText = label.childNodes[0].textContent.trim();
        const option = make('option', '', labelText);
        option.value = String(index);
        picker.select.append(option);
      });
      controls.insertBefore(picker.wrapper, sections[0]);
      const compact = matchMedia('(max-width:700px)');
      const syncParameters = () => {
        labels.forEach((label, index) => label.classList.toggle('special-unselected', compact.matches && index !== Number(picker.select.value)));
        sections.forEach(section => section.classList.toggle('special-empty-section', compact.matches && !section.querySelector('label:not(.special-unselected)')));
      };
      compact.addEventListener('change', syncParameters);
      picker.select.addEventListener('change', syncParameters);
      syncParameters();
      fitRegion(scene, 210, 480, true);
      return;
    }

    if ($('#surface') && $('#both-step')) {
      activate('surface');
      const graph = $('.canvas-wrap'), stats = $('.stats'), controls = $('.controls');
      const viewTools = $('#left').parentElement, updateTools = $('#both-step').parentElement;
      const reset = $('#reset');
      const explanatory = [...main.children].filter(node => node.matches('small, p:not(#gradient):not(#change), footer'));
      const reference = details(text('公式、视角与实验说明', 'Formula, view controls and instructions'), [...explanatory, viewTools, $('#gradient'), reset]);
      reference.classList.add('special-reference');
      const workbench = make('div', 'special-surface-workbench');
      const visual = make('section', 'special-surface-visual');
      visual.setAttribute('aria-label', text('损失曲面', 'Loss surface'));
      const panel = make('section', 'special-surface-panel');
      panel.setAttribute('aria-label', text('参数、更新与结果', 'Parameters, update and result'));
      visual.append(graph);
      panel.append(stats, controls, updateTools, $('#change'));
      workbench.append(visual, panel);
      main.insertBefore(workbench, reference);
      return;
    }

    if ($('#model-data') && $('#rail') && $('#coordinate-value')) {
      activate('xray');
      const sample = $('.sample'), workspace = $('.workspace'), instrument = $('.instrument');
      const reference = details(text('实验说明、完整位置和层次、来源', 'Instructions, all positions and layers, sources'), [$('.eyebrow'), $('.lead'), $('.status'), $('.sample-top'), $('#tokens'), $('#visibility'), $('#rail'), $('footer')]);
      reference.classList.add('special-reference');
      // Original button lists remain available in the expanded instructions.
      const position = field(text('输入位置', 'Input position'));
      const layer = field(text('模型层次', 'Model layer'));
      sample.append(position.wrapper, layer.wrapper);
      mirrorButtons($('#tokens'), position.select, 'button', button => button.classList.contains('active'));
      mirrorButtons($('#rail'), layer.select, 'button', button => button.classList.contains('active'));
      workspace.insertBefore($('.step-controls'), instrument);
      const dataView = make('div', 'special-xray-data');
      const readout = make('div', 'special-xray-readout');
      const coordinate = field(text('坐标', 'Coordinate'));
      for (let index = 0; index < 64; index++) {
        const option = make('option', '', String(index));
        option.value = String(index);
        coordinate.select.append(option);
      }
      const inspector = $('.inspector');
      const coordinateDetails = details(text('坐标计算与说明', 'Coordinate calculation and notes'), [$('#coordinate-detail'), $('#coordinate-explain'), $('#live')], inspector);
      coordinateDetails.classList.add('special-coordinate-details');
      readout.append(coordinate.wrapper, inspector);
      const values = make('div', 'special-xray-values');
      values.append($('#vector-view'), $('#output-view'));
      dataView.append(readout, values);
      instrument.insertBefore(dataView, $('.relation'));
      const relation = $('.relation');
      details(text('这一步怎样计算', 'How this step is calculated'), [$('#stage-description'), relation, $('#attention')], instrument);
      coordinate.select.addEventListener('change', () => {
        const index = Number(coordinate.select.value);
        const output = !$('#output-view').classList.contains('hidden');
        const target = output ? $('#projection').querySelectorAll('rect')[index] : $('#grid').querySelectorAll('button')[index];
        target?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        instrument.scrollTop = 0;
        coordinate.select.focus({ preventScroll: true });
      });
      let lastStage = $('#stage-title').textContent;
      const syncCoordinate = () => {
        const stageTitle = $('#stage-title').textContent;
        if (lastStage !== stageTitle) { instrument.scrollTop = 0; lastStage = stageTitle; }
        const active = $('#grid').querySelector('.cell.active');
        if (active && !$('#vector-view').classList.contains('hidden')) coordinate.select.value = String([...$('#grid').children].indexOf(active));
        else {
          const rects = [...$('#projection').querySelectorAll('rect')];
          const index = rects.findIndex(rect => rect.hasAttribute('stroke'));
          if (index >= 0) coordinate.select.value = String(index);
        }
      };
      new MutationObserver(syncCoordinate).observe(instrument, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-pressed'] });
      syncCoordinate();
      instrument.setAttribute('tabindex', '0');
      instrument.setAttribute('aria-label', text('当前层的数值与详情，可在区域内滚动', 'Current layer values and details; scroll within this region'));
      fitRegion(instrument, 185);
      scrollHint(instrument, $('.step-controls'));
      return;
    }

    if ($('#stage') && $('.steps') && $('#progress')) {
      activate('replay');
      const stage = $('#stage'), steps = $('.steps'), toolbar = $('#previous').parentElement;
      const reference = details(text('回放说明、全部阶段与来源', 'Replay instructions, all stages and sources'), [$('main > small'), $('.intro'), $('.phases'), steps, $('#restart'), $('footer')]);
      reference.classList.add('special-reference');
      const shell = make('div', 'special-replay-workspace');
      const phase = field(text('训练阶段', 'Training stage'));
      mirrorButtons(steps, phase.select, 'button', button => button.getAttribute('aria-current') === 'step');
      shell.append(phase.wrapper, toolbar, stage);
      main.insertBefore(shell, reference);
      stage.setAttribute('tabindex', '0');
      stage.setAttribute('aria-label', text('当前阶段内容，可在区域内滚动', 'Current stage content; scroll within this region'));
      fitRegion(stage, 180);
      scrollHint(stage, toolbar);
      // Render replaces only stage.innerHTML. Keeping the scroll position at its start avoids opening a new stage halfway down.
      let lastTitle = $('#stage-title')?.textContent;
      new MutationObserver(() => {
        const title = $('#stage-title')?.textContent;
        if (title !== lastTitle) { stage.scrollTop = 0; lastTitle = title; }
      }).observe(stage, { childList: true });
    }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();

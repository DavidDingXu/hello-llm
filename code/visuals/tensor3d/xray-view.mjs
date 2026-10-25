import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { COPY } from './xray-copy.mjs';
import { STAGES, stageValues, inspectCoordinate, projection, attentionRead } from './xray-model.mjs';

const data = JSON.parse(document.getElementById('model-data').textContent);
const text = COPY[data.lang], english = data.lang === 'en';
const word = (zh, en) => english ? en : zh;
const $ = id => document.getElementById(id), root = $('lab'), canvas = $('scene'), viewport = $('viewport');
const ids = data.trace.ids[0], query = new URLSearchParams(location.hash.slice(1));
const clamp = (value, max, fallback) => Number.isInteger(value) && value >= 0 && value <= max ? value : fallback;
let position = clamp(Number(query.get('p') ?? 7), 13, 7);
let stage = clamp(Number(query.get('stage') ?? 0), 8, 0);
let coordinate = clamp(Number(query.get('c') ?? 0), 63, 0);
let candidate = clamp(Number(query.get('candidate') ?? data.tokens.indexOf('红')), 78, 55);
let mode = query.get('view') === 'overview' ? 'overview' : 'focus';
let tab = stage === 8 ? 'output' : 'coordinates';
let head = 0, headCoordinate = 0, sourcePosition = 0;
let orbit = false, active = true, frame = 0, renderer, scene, camera, controls;
let layers = [], selectedOutline, selectedLabel;
const darkMode = matchMedia('(prefers-color-scheme: dark)');
let dark = false;
const visibleToken = token => token === '\n' ? '↵' : token.startsWith('<') ? token.slice(1, -1).toUpperCase() : token;
const signed = (value, digits = 5) => `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
const percent = value => value < .00001 ? '<0.001%' : `${(value * 100).toFixed(3)}%`;

function readTheme() {
  try {
    const parentTheme = window.parent !== window ? window.parent.document.documentElement.dataset.theme : null;
    const theme = parentTheme || localStorage.getItem('haohai-tinylm-theme');
    if (theme === 'light' || theme === 'dark') return theme === 'dark';
  } catch { /* OS preference works when the parent or localStorage is unavailable. */ }
  return darkMode.matches;
}
function applyTheme() {
  dark = readTheme(); document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (scene) {
    scene.background.set(dark ? '#1d2530' : '#ffffff');
    layers.forEach((layer, i) => {
      layer.title.material.map.dispose();
      layer.title.material.map = labelTexture(`${i + 1}  ${text.shortStages[i]}`, false);
      layer.frame.material.color.set(dark ? '#56677d' : '#b9c9dd');
    });
    selectedOutline.material.color.set(dark ? '#e9f0fb' : '#233448');
    updateScene();
  }
  renderCoordinates(); requestRender();
}

function option(value, label) { const item = document.createElement('option'); item.value = value; item.textContent = label; return item; }
ids.forEach((id, i) => $('position').append(option(i, `${i} · ${visibleToken(data.tokens[id])}`)));
text.stages.forEach((label, i) => $('stage').append(option(i, `${i + 1}. ${label}`)));
data.tokens.forEach((token, i) => $('candidate').append(option(i, `${i} · ${visibleToken(token)}`)));
$('digest').textContent = data.parameter_sha256;

const gridButtons = Array.from({ length: 64 }, (_, c) => {
  const button = document.createElement('button');
  const index = document.createElement('b'), value = document.createElement('span');
  button.append(index, value); button.addEventListener('click', () => chooseCoordinate(c));
  $('coordinate-grid').append(button); return button;
});
const attentionButtons = ids.map((id, source) => {
  const button = document.createElement('button'); button.className = 'attention-bar';
  const amount = document.createElement('strong'), bar = document.createElement('span'); bar.className = 'bar';
  const token = document.createElement('span'); token.textContent = visibleToken(data.tokens[id]);
  const index = document.createElement('small'); index.textContent = source;
  button.append(amount, bar, token, index);
  button.addEventListener('click', () => { sourcePosition = source; renderAttention(); });
  $('attention-bars').append(button); return button;
});
const candidateButtons = Array.from({ length: 5 }, () => {
  const button = document.createElement('button'); button.className = 'candidate-row';
  const token = document.createElement('strong'), track = document.createElement('span'); track.className = 'track';
  const fill = document.createElement('span'); fill.className = 'fill'; track.append(fill);
  const probability = document.createElement('small'); button.append(token, track, probability);
  button.addEventListener('click', () => { candidate = Number(button.dataset.candidate); sync(); });
  $('top-candidates').append(button); return button;
});
function saveState() {
  try { history.replaceState(null, '', `#p=${position}&stage=${stage}&c=${coordinate}&candidate=${candidate}&view=${mode}`); }
  catch { /* Some file:// hosts restrict history. The controls still work. */ }
}
function tint(value, maximum) {
  const base = value >= 0 ? [24, 123, 121] : [128, 86, 165];
  const paper = dark ? [29, 37, 48] : [255, 255, 255];
  const amount = (dark ? .18 : .05) + (dark ? .58 : .40) * Math.min(1, Math.abs(value) / Math.max(maximum, 1e-12));
  return `rgb(${base.map((channel, i) => Math.round(paper[i] + (channel - paper[i]) * amount)).join(',')})`;
}
function renderReadout() {
  const item = inspectCoordinate(data, stage, position, coordinate), descriptor = STAGES[stage];
  $('readout-address').textContent = `${visibleToken(data.tokens[ids[position]])} · p=${position} · ${stage === 8 ? `vocab=${candidate}` : `c=${coordinate}`}`;
  $('readout-note').textContent = text.descriptions[stage];
  $('readout-extra').textContent = `${stage + 1} / 9`;
  $('readout-value').textContent = signed(item.value);
  if (stage === 0) $('equation').textContent = `E[${ids[position]}, ${coordinate}] = ${signed(item.value)}`;
  else if (descriptor.kind === 'residual' || descriptor.kind === 'feedforward') {
    $('equation').textContent = `${signed(item.left)} + (${signed(item.right)}) = ${signed(item.value)}`;
  } else if (stage === 7) {
    $('equation').textContent = `${signed(item.input)} ÷ ${item.denominator.toFixed(5)} × ${item.scale.toFixed(5)}`;
  } else if (stage === 8) {
    const result = projection(data, position, candidate);
    $('readout-value').textContent = signed(result.score);
    $('readout-extra').textContent = `P(${visibleToken(data.tokens[candidate])}) ${percent(result.probabilities[candidate])}`;
    $('equation').textContent = `Σ(i=0…63) h[i] × W[${candidate},i] = ${signed(result.score)}`;
  } else $('equation').textContent = `Attention(RMSNorm(x))[${coordinate}] = ${signed(item.value)}`;
}
function renderCoordinates() {
  const values = stage === 8 ? projection(data, position, candidate).products : stageValues(data, stage, position);
  const max = Math.max(...values.map(Math.abs));
  $('coordinate-note').textContent = stage === 8 ? text.productNote : text.axisNote;
  $('product-equation').hidden = stage !== 8;
  if (stage === 8) {
    const h = data.trace.normalized[0][position][coordinate], w = data.output_weights[candidate][coordinate];
    $('product-equation').textContent = `c=${coordinate}: ${signed(h)} × ${signed(w)} = ${signed(h * w)}`;
  }
  gridButtons.forEach((button, c) => {
    button.firstElementChild.textContent = c;
    button.lastElementChild.textContent = signed(values[c], 2);
    button.style.background = tint(values[c], max);
    button.setAttribute('aria-pressed', String(c === coordinate));
    button.setAttribute('aria-label', `${text.coordinate} ${c}, ${signed(values[c], 7)}`);
  });
}
function renderAttention() {
  const block = STAGES[stage].block ?? 0;
  const read = attentionRead(data, block, head, position, headCoordinate);
  attentionButtons.forEach((button, source) => {
    const item = read.items[source];
    button.firstElementChild.textContent = item.blocked ? '×' : `${(item.weight * 100).toFixed(item.weight < .1 ? 1 : 0)}%`;
    button.children[1].style.height = `${Math.max(2, item.weight * 65)}px`;
    button.children[1].classList.toggle('blocked', item.blocked);
    button.setAttribute('aria-pressed', String(source === sourcePosition));
    button.setAttribute('aria-label', `${word('来源位置', 'Source position')} ${source}, ${visibleToken(data.tokens[ids[source]])}, ${percent(item.weight)}${item.blocked ? `, ${word('因果屏蔽', 'causally masked')}` : ''}`);
  });
  const item = read.items[sourcePosition];
  $('attention-equation').textContent = `${word('块', 'Block')} ${block + 1}, head=${head}, V c=${headCoordinate}\n` +
    `${word('来源', 'Source')} ${sourcePosition}: ${item.weight.toFixed(5)} × ${signed(item.value)} = ${signed(item.product)}\n` +
    `Σ(source=0…${position}) weight × V = ${signed(read.value)}`;
}
function renderOutput() {
  const result = projection(data, position, candidate), ranked = result.probabilities.map((p, i) => ({ p, i })).sort((a, b) => b.p - a.p);
  candidateButtons.forEach((button, rank) => {
    const { p, i } = ranked[rank]; button.dataset.candidate = i;
    button.firstElementChild.textContent = visibleToken(data.tokens[i]);
    button.children[1].firstElementChild.style.width = `${p * 100}%`;
    button.lastElementChild.textContent = percent(p);
    button.setAttribute('aria-pressed', String(candidate === i));
    button.setAttribute('aria-label', `${text.candidate} ${visibleToken(data.tokens[i])}, ${percent(p)}`);
  });
  $('candidate').value = candidate;
  $('candidate-equation').textContent = `vocab[${candidate}] = ${visibleToken(data.tokens[candidate])}\n` +
    `${word('分数', 'Score')} ${signed(result.score)} → Softmax(79) → ${percent(result.probabilities[candidate])}`;
}
function sync() {
  $('position').value = position; $('stage').value = stage; $('coordinate').value = coordinate;
  $('previous').disabled = stage === 0; $('next').disabled = stage === 8;
  $('coordinate-previous').disabled = coordinate === 0; $('coordinate-next').disabled = coordinate === 63;
  $('shape').textContent = stage === 8 ? '[1, 14, 79]' : '[1, 14, 64]';
  $('axis-note').textContent = stage === 8 ? text.outputAxis : text.axisNote;
  $('scale-label').textContent = `±${Math.max(...stageValues(data, stage, position).map(Math.abs)).toFixed(2)}`;
  $('scene-tip').textContent = mode === 'overview' ? text.overviewHint : text.focusHint;
  $('overview').setAttribute('aria-pressed', String(mode === 'overview'));
  $('focus').setAttribute('aria-pressed', String(mode === 'focus'));
  for (const name of ['coordinates', 'attention', 'output']) {
    $(`tab-${name}`).setAttribute('aria-selected', String(name === tab));
    $(`tab-${name}`).tabIndex = name === tab ? 0 : -1;
    $(`panel-${name}`).hidden = name !== tab;
  }
  renderReadout(); renderCoordinates(); renderAttention(); renderOutput();
  $('status').textContent = `${text.stages[stage]}, p=${position}, c=${coordinate}`;
  if (scene) updateScene();
  saveState(); requestRender();
}
function chooseCoordinate(value) { coordinate = clamp(value, 63, coordinate); sync(); }
function setStage(value) {
  stage = clamp(value, 8, stage); tab = stage === 8 ? 'output' : 'coordinates';
  sync(); if (mode === 'focus') fitCamera();
}
function setTab(value) {
  tab = value;
  if (value === 'output') stage = 8;
  if (value === 'attention' && STAGES[stage].block === undefined) stage = 1;
  sync(); if (mode === 'focus') fitCamera();
}
$('position').addEventListener('change', event => { position = Number(event.target.value); sync(); });
$('stage').addEventListener('change', event => setStage(Number(event.target.value)));
$('coordinate').addEventListener('change', event => chooseCoordinate(Number(event.target.value)));
$('coordinate-previous').addEventListener('click', () => chooseCoordinate(coordinate - 1));
$('coordinate-next').addEventListener('click', () => chooseCoordinate(coordinate + 1));
$('previous').addEventListener('click', () => setStage(stage - 1));
$('next').addEventListener('click', () => setStage(stage + 1));
$('head').addEventListener('change', event => { head = Number(event.target.value); renderAttention(); });
$('head-coordinate').addEventListener('change', event => { headCoordinate = clamp(Number(event.target.value), 31, headCoordinate); event.target.value = headCoordinate; renderAttention(); });
$('candidate').addEventListener('change', event => { candidate = Number(event.target.value); sync(); });
$('show-products').addEventListener('click', () => { setTab('coordinates'); $('tab-coordinates').focus(); });
const tabNames = ['coordinates', 'attention', 'output'];
for (const name of tabNames) {
  $(`tab-${name}`).addEventListener('click', () => setTab(name));
  $(`tab-${name}`).addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (tabNames.indexOf(name) + (event.key === 'ArrowRight' ? 1 : 2)) % 3;
    setTab(tabNames[index]); $(`tab-${tabNames[index]}`).focus();
  });
}
for (const view of ['overview', 'focus']) $(view).addEventListener('click', () => { mode = view; sync(); fitCamera(); });

function labelTexture(value, highlight = false) {
  const label = document.createElement('canvas'); label.width = 768; label.height = 96;
  const context = label.getContext('2d');
  context.font = '600 36px Arial, "PingFang SC", sans-serif'; context.textAlign = 'center'; context.textBaseline = 'middle';
  context.fillStyle = highlight ? (dark ? '#e9f0fb' : '#233448') : (dark ? '#a8b5c6' : '#56677d');
  context.fillText(value, 384, 48);
  const texture = new THREE.CanvasTexture(label); texture.colorSpace = THREE.SRGBColorSpace; return texture;
}
function sprite(value, scale = 4.8, highlight = false) {
  const item = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTexture(value, highlight), depthTest: false, depthWrite: false }));
  item.scale.set(scale, scale / 8, 1); item.renderOrder = 5; return item;
}
function requestRender() {
  if (renderer && active && !document.hidden && !frame) frame = requestAnimationFrame(() => {
    frame = 0; if (active && !document.hidden) renderer.render(scene, camera);
  });
}
function cellTransform(index, count, value, max) {
  const columns = count === 79 ? 10 : 8, rows = Math.ceil(count / columns);
  const depth = .08 + .38 * Math.min(1, Math.abs(value) / Math.max(max, 1e-12));
  return { x: (index % columns - (columns - 1) / 2) * .56,
    y: ((rows - 1) / 2 - Math.floor(index / columns)) * .56, z: depth / 2, depth };
}
function updateScene() {
  const transform = new THREE.Object3D(), color = new THREE.Color();
  layers.forEach((layer, i) => {
    const values = stageValues(data, i, position), max = Math.max(...values.map(Math.abs));
    layer.group.visible = mode === 'overview' || i === stage;
    layer.group.position.set(mode === 'overview' ? i * 1.0 : 0, mode === 'overview' ? i * .16 : 0, mode === 'overview' ? -i * 1.24 : 0);
    layer.frame.material.opacity = i === stage ? 1 : .35;
    values.forEach((value, index) => {
      const cell = cellTransform(index, values.length, value, max);
      transform.position.set(cell.x, cell.y, cell.z); transform.scale.set(.48, .48, cell.depth); transform.updateMatrix();
      layer.mesh.setMatrixAt(index, transform.matrix);
      color.set(value >= 0 ? '#187b79' : '#8056a5');
      color.lerp(new THREE.Color(dark ? '#536579' : '#e5eaf2'), .66 * (1 - Math.abs(value) / Math.max(max, 1e-12)));
      layer.mesh.setColorAt(index, color);
    });
    layer.mesh.instanceMatrix.needsUpdate = true; layer.mesh.instanceColor.needsUpdate = true;
    layer.mesh.computeBoundingSphere();
    if (i === stage) {
      const index = stage === 8 ? candidate : coordinate;
      const cell = cellTransform(index, values.length, values[index], max);
      selectedOutline.position.copy(layer.group.position).add(new THREE.Vector3(cell.x, cell.y, cell.z));
      selectedOutline.scale.set(.52, .52, cell.depth + .045);
      selectedLabel.position.copy(selectedOutline.position).add(new THREE.Vector3(0, .42, .22));
      selectedLabel.material.map.dispose(); selectedLabel.material.map = labelTexture(`${stage === 8 ? 'vocab' : 'c'}=${index}`, true);
      selectedLabel.scale.set(1.6, .2, 1);
      $('scale-label').textContent = `±${max.toFixed(2)}`;
    }
  });
}
function fitCamera() {
  if (!camera || !controls) return;
  const center = mode === 'overview' ? new THREE.Vector3(4, .7, -4.9) : new THREE.Vector3(0, .15, .1);
  const radius = mode === 'overview' ? 9.0 : stage === 8 ? 3.9 : 3.25;
  const halfFov = Math.min(THREE.MathUtils.degToRad(camera.fov / 2), Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect));
  const distance = radius / Math.sin(halfFov);
  const direction = mode === 'overview' ? new THREE.Vector3(.56, .38, 1).normalize() : new THREE.Vector3(.30, .25, 1).normalize();
  camera.position.copy(center).addScaledVector(direction, distance); camera.near = .1; camera.far = 160; camera.updateProjectionMatrix();
  controls.target.copy(center); camera.lookAt(center); controls.update(); requestRender();
}
function resize() {
  if (!renderer) return;
  const { width, height } = viewport.getBoundingClientRect(); if (width < 1 || height < 1) return;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix();
  fitCamera();
}
function setOrbit(value) {
  orbit = value; if (controls) controls.enabled = orbit;
  // OrbitControls writes touch-action:none on construction. Restore vertical page pan explicitly.
  canvas.style.touchAction = orbit ? 'none' : 'pan-y';
  viewport.classList.toggle('is-orbit', orbit); $('orbit').setAttribute('aria-pressed', String(orbit));
}
$('orbit').addEventListener('click', () => setOrbit(!orbit));
$('reset-view').addEventListener('click', () => { setOrbit(false); fitCamera(); });
function fail3D() {
  if (frame) cancelAnimationFrame(frame); frame = 0;
  controls?.dispose(); controls = null; renderer?.dispose(); renderer = null;
  viewport.classList.add('failed'); root.dataset.renderState = 'fallback';
  $('orbit').disabled = true; $('reset-view').disabled = true; $('status').textContent = text.fallback;
}
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene(); scene.background = new THREE.Color(dark ? '#1d2530' : '#ffffff');
  camera = new THREE.PerspectiveCamera(45, 1, .1, 160);
  scene.add(new THREE.AmbientLight('#ffffff', 2.2));
  const light = new THREE.DirectionalLight('#ffffff', 3.2); light.position.set(4, 8, 10); scene.add(light);
  controls = new OrbitControls(camera, canvas); controls.enableDamping = false;
  controls.minDistance = 4; controls.maxDistance = 70; controls.addEventListener('change', requestRender); setOrbit(false);
  const geometry = new THREE.BoxGeometry(1, 1, 1);
  layers = STAGES.map((descriptor, i) => {
    const group = new THREE.Group(), count = i === 8 ? 79 : 64;
    const mesh = new THREE.InstancedMesh(geometry, new THREE.MeshStandardMaterial({ roughness: .75, metalness: 0 }), count);
    mesh.userData.stage = i; group.add(mesh);
    const frame = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(i === 8 ? 5.8 : 4.7, 4.7, .03)), new THREE.LineBasicMaterial({ color: '#b9c9dd', transparent: true }));
    frame.position.z = -.065; group.add(frame);
    const title = sprite(`${i + 1}  ${text.shortStages[i]}`, i === 8 ? 5.7 : 4.9);
    title.position.set(0, 2.65, 0); group.add(title); scene.add(group); return { group, mesh, frame, title };
  });
  selectedOutline = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: '#233448', depthTest: false }));
  selectedOutline.renderOrder = 9; scene.add(selectedOutline);
  selectedLabel = sprite('c=0', 1.6, true); scene.add(selectedLabel);
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2(); let down;
  canvas.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; });
  canvas.addEventListener('pointerup', event => {
    if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 6) return;
    const bounds = canvas.getBoundingClientRect();
    pointer.set((event.clientX - bounds.left) / bounds.width * 2 - 1, -(event.clientY - bounds.top) / bounds.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(layers.filter(layer => layer.group.visible).map(layer => layer.mesh), false)[0];
    if (!hit) return;
    stage = hit.object.userData.stage;
    if (stage === 8) { candidate = hit.instanceId; tab = 'output'; } else { coordinate = hit.instanceId; tab = 'coordinates'; }
    sync();
  });
  canvas.addEventListener('keydown', event => {
    const deltas = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -8, ArrowDown: 8 };
    if (event.key in deltas) {
      event.preventDefault();
      if (stage === 8) { candidate = Math.max(0, Math.min(78, candidate + deltas[event.key])); sync(); }
      else chooseCoordinate(Math.max(0, Math.min(63, coordinate + deltas[event.key])));
    } else if (event.key === 'PageUp' || event.key === 'PageDown') {
      event.preventDefault(); setStage(stage + (event.key === 'PageUp' ? -1 : 1));
    } else if (event.key === 'Home') { event.preventDefault(); setOrbit(false); fitCamera(); }
  });
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); fail3D(); });
  root.dataset.renderState = 'ready';
} catch { fail3D(); }

darkMode.addEventListener('change', applyTheme);
window.addEventListener('storage', event => { if (event.key === 'haohai-tinylm-theme') applyTheme(); });
try {
  if (window.parent !== window) new MutationObserver(applyTheme).observe(window.parent.document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
} catch { /* A cross-origin embed follows local/OS theme instead. */ }
new ResizeObserver(resize).observe(viewport);
new IntersectionObserver(entries => {
  active = entries[0].isIntersecting;
  if (!active && frame) { cancelAnimationFrame(frame); frame = 0; }
  if (active) requestRender();
}, { threshold: 0 }).observe(viewport);
document.addEventListener('visibilitychange', () => {
  if (document.hidden && frame) { cancelAnimationFrame(frame); frame = 0; }
  if (!document.hidden) requestRender();
});
applyTheme(); sync(); resize();

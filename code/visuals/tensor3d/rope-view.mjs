import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { COPY } from './rope-copy.mjs';
import { evaluate, compare } from './rope-model.mjs';

const data = JSON.parse(document.getElementById('rope-data').textContent), text = COPY[data.lang];
const english = data.lang === 'en', word = (zh, en) => english ? en : zh;
const $ = id => document.getElementById(id), root = $('lab'), viewport = $('viewport'), canvas = $('scene');
const query = new URLSearchParams(location.hash.slice(1));
const bounded = (value, maximum, fallback) => Number.isInteger(value) && value >= 0 && value <= maximum ? value : fallback;
let m = bounded(Number(query.get('m') ?? 1), data.maximum, 1), n = bounded(Number(query.get('n') ?? 0), data.maximum, 0);
let selected = bounded(Number(query.get('pair') ?? 0), 1, 0), mode = query.get('view') === 'focus' ? 'focus' : 'both';
let tab = 'coordinates', comparison = null, comparisonKind = 'common';
let renderer, scene, camera, controls, planes = [], frame = 0, active = true, dark = false, orbit = false;
const darkMode = matchMedia('(prefers-color-scheme: dark)');
const signed = (value, digits = 6) => `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
const vector = values => `[${values.map(value => signed(value, innerWidth <= 350 ? 3 : 5)).join(', ')}]`;
const current = () => evaluate(data.q, data.k, data.v, m, n, data.theta);

function readTheme() {
  try {
    const parentTheme = window.parent !== window ? window.parent.document.documentElement.dataset.theme : null;
    const theme = parentTheme || localStorage.getItem('haohai-tinylm-theme');
    if (theme === 'light' || theme === 'dark') return theme === 'dark';
  } catch { /* The OS theme works when parent or storage access is restricted. */ }
  return darkMode.matches;
}
function palette() { return dark ? { q: '#99bde9', k: '#75cbbf', axis: '#66788c', ink: '#e5eaf1', selected: '#c6a0e8', paper: '#1d2530' }
  : { q: '#3267a4', k: '#187b79', axis: '#b1bdcb', ink: '#4c6078', selected: '#8056a5', paper: '#ffffff' }; }
function applyTheme() {
  dark = readTheme(); document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (scene) {
    const colors = palette(); scene.background.set(colors.paper);
    planes.forEach((plane, i) => {
      plane.q.setColor(new THREE.Color(colors.q)); plane.k.setColor(new THREE.Color(colors.k));
      plane.axes.material.color.set(colors.axis); plane.original.material.color.set(colors.axis);
      plane.labels.forEach(label => { label.material.map.dispose(); label.material.map = labelTexture(label.userData.text); });
    });
    updateScene();
  }
  if (!renderer) renderFallback(); requestRender();
}
function save() {
  try { history.replaceState(null, '', `#m=${m}&n=${n}&pair=${selected}&view=${mode}`); }
  catch { /* Controls also work on hosts that restrict file:// history. */ }
}
function setTab(value) {
  tab = value;
  for (const name of ['coordinates', 'comparison', 'formal']) {
    $(`tab-${name}`).setAttribute('aria-selected', String(tab === name));
    $(`tab-${name}`).tabIndex = tab === name ? 0 : -1;
    $(`panel-${name}`).hidden = tab !== name;
  }
}
function renderComparison() {
  $('comparison-empty').hidden = Boolean(comparison); $('comparison-values').hidden = !comparison;
  if (!comparison) return;
  for (const name of ['before', 'after']) {
    const result = comparison[name];
    $(`${name}-score`).textContent = signed(result.score);
    $(`${name}-position`).textContent = `m=${result.m}, n=${result.n}, n−m=${result.difference}`;
    $(`${name}-pairs`).textContent = result.pairs.map(pair => signed(pair.dot, 5)).join(' + ');
  }
  $('comparison-result').textContent = comparisonKind === 'common' ? text.commonResult : text.differentResult;
  $('comparison-error').textContent = `${text.error}: ${comparison.error.toExponential(3)}`;
}
function renderCoordinates(result) {
  const pair = result.pairs[selected];
  for (let i = 0; i < 2; i++) $(`pair-${i}`).setAttribute('aria-pressed', String(selected === i));
  $('pair-title').textContent = `${text.pair} ${selected} · c${selected * 2}, c${selected * 2 + 1}`;
  $('frequency').textContent = `ω=${pair.frequency} ${text.radians}`;
  $('q-angle').textContent = `αQ = ${m} × ${pair.frequency} = ${pair.angleQ.toFixed(4)} rad`;
  $('k-angle').textContent = `αK = ${n} × ${pair.frequency} = ${pair.angleK.toFixed(4)} rad`;
  $('q-coordinates').textContent = `${vector(pair.qBefore)} → ${vector(pair.q)}`;
  $('k-coordinates').textContent = `${vector(pair.kBefore)} → ${vector(pair.k)}`;
  $('pair-equation').textContent = `${text.pairDot}\n${signed(pair.q[0], 5)} × ${signed(pair.k[0], 5)} + ${signed(pair.q[1], 5)} × ${signed(pair.k[1], 5)} = ${signed(pair.dot)}`;
  $('norms').textContent = `${text.norm}: Q ${Math.hypot(...pair.qBefore).toFixed(5)} → ${Math.hypot(...pair.q).toFixed(5)} · K ${Math.hypot(...pair.kBefore).toFixed(5)} → ${Math.hypot(...pair.k).toFixed(5)}`;
}
function sync() {
  const result = current();
  for (const [id, value] of [['position-m', m], ['range-m', m], ['position-n', n], ['range-n', n]]) $(id).value = value;
  $('common-shift').disabled = m + 3 > data.maximum || n + 3 > data.maximum;
  $('only-k').disabled = n + 1 > data.maximum;
  $('score').textContent = signed(result.score);
  $('score-equation').textContent = `${signed(result.pairs[0].dot)} + (${signed(result.pairs[1].dot)}) = ${signed(result.score)}`;
  $('position-difference').textContent = `n−m = ${n - m}`;
  $('v-values').textContent = `[${data.v.join(',')}] → [${result.v.join(',')}]`;
  $('both').setAttribute('aria-pressed', String(mode === 'both')); $('focus').setAttribute('aria-pressed', String(mode === 'focus'));
  renderCoordinates(result); renderComparison();
  if (scene) updateScene(); if (!renderer) renderFallback();
  $('status').textContent = `m=${m}, n=${n}, ${text.pair} ${selected}, Q·K=${signed(result.score)}`;
  save(); requestRender();
}
function choosePair(value) {
  selected = bounded(value, 1, selected); setTab('coordinates'); sync(); if (mode === 'focus') fitCamera();
}
function movePosition(which, value) {
  const previous = which === 'm' ? m : n;
  const next = bounded(Number(value), data.maximum, previous);
  if (which === 'm') m = next; else n = next;
  sync();
}
for (const which of ['m', 'n']) {
  $(`range-${which}`).addEventListener('input', event => movePosition(which, event.target.value));
  $(`position-${which}`).addEventListener('input', event => { if (event.target.value !== '') movePosition(which, event.target.value); });
  $(`position-${which}`).addEventListener('change', event => movePosition(which, event.target.value));
}
$('common-shift').addEventListener('click', () => {
  if (m + 3 > data.maximum || n + 3 > data.maximum) return;
  comparison = compare(data.q, data.k, data.v, m, n, m + 3, n + 3, data.theta); comparisonKind = 'common';
  m += 3; n += 3; setTab('comparison'); sync();
});
$('only-k').addEventListener('click', () => {
  if (n + 1 > data.maximum) return;
  comparison = compare(data.q, data.k, data.v, m, n, m, n + 1, data.theta); comparisonKind = 'difference';
  n++; setTab('comparison'); sync();
});
$('reset').addEventListener('click', () => { m = 1; n = 0; selected = 0; comparison = null; mode = 'both'; setTab('coordinates'); setOrbit(false); sync(); fitCamera(); });
for (const view of ['both', 'focus']) $(view).addEventListener('click', () => { mode = view; sync(); fitCamera(); });
for (let i = 0; i < 2; i++) $(`pair-${i}`).addEventListener('click', () => choosePair(i));
const tabs = ['coordinates', 'comparison', 'formal'];
for (const name of tabs) {
  $(`tab-${name}`).addEventListener('click', () => setTab(name));
  $(`tab-${name}`).addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? 2 : (tabs.indexOf(name) + (event.key === 'ArrowRight' ? 1 : 2)) % 3;
    setTab(tabs[index]); $(`tab-${tabs[index]}`).focus();
  });
}
data.frequencies.forEach((frequency, index) => {
  const row = document.createElement('tr');
  for (const value of [index, `${index * 2}, ${index * 2 + 1}`, frequency >= .01 ? frequency.toFixed(6) : frequency.toExponential(6)]) {
    const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
  }
  $('frequency-table').append(row);
});

function renderFallback() {
  const result = current(), colors = palette();
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.setAttribute('viewBox', mode === 'focus' ? '0 0 300 220' : '0 0 600 220');
  svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', text.fallback);
  const defs = document.createElementNS(ns, 'defs');
  defs.innerHTML = `<marker id="q-tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10Z" fill="${colors.q}"/></marker><marker id="k-tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0L10,5L0,10Z" fill="${colors.k}"/></marker>`;
  svg.append(defs);
  result.pairs.forEach((pair, i) => {
    if (mode === 'focus' && i !== selected) return;
    const x = mode === 'focus' ? 150 : 150 + i * 300, y = 118, radius = 66;
    const group = document.createElementNS(ns, 'g'); group.setAttribute('tabindex', '0'); group.setAttribute('role', 'button'); group.setAttribute('aria-label', i === 0 ? text.pair0 : text.pair1);
    group.innerHTML = `<circle cx="${x}" cy="${y}" r="${radius}" fill="none" stroke="${selected === i ? colors.selected : colors.axis}" stroke-width="${selected === i ? 2 : 1}"/><path d="M${x - 77},${y}H${x + 77}M${x},${y - 77}V${y + 77}" stroke="${colors.axis}" stroke-width=".8"/><path d="M${x},${y}h${radius}" stroke="${colors.axis}" stroke-dasharray="4 3"/><text x="${x}" y="27" text-anchor="middle" font-size="12" fill="${colors.ink}">${text.pair} ${i} · c${i * 2},c${i * 2 + 1} · ω=${pair.frequency}</text>`;
    for (const [name, values, color] of [['q', pair.q, colors.q], ['k', pair.k, colors.k]]) {
      const line = document.createElementNS(ns, 'line');
      for (const [key, value] of Object.entries({ x1: x, y1: y, x2: x + values[0] * radius, y2: y - values[1] * radius, stroke: color, 'stroke-width': 3, 'marker-end': `url(#${name}-tip)` })) line.setAttribute(key, value);
      group.append(line);
    }
    group.addEventListener('click', () => choosePair(i));
    group.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choosePair(i); } });
    svg.append(group);
  });
  $('fallback').replaceChildren(svg);
}
function labelTexture(value) {
  const source = document.createElement('canvas'); source.width = 768; source.height = 96;
  const context = source.getContext('2d'); context.font = '500 34px Arial, "PingFang SC", sans-serif';
  context.textAlign = 'center'; context.textBaseline = 'middle'; context.fillStyle = palette().ink; context.fillText(value, 384, 48);
  const texture = new THREE.CanvasTexture(source); texture.colorSpace = THREE.SRGBColorSpace; return texture;
}
function sprite(value, width) {
  const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTexture(value), depthTest: false, depthWrite: false }));
  label.userData.text = value; label.scale.set(width, width / 8, 1); label.renderOrder = 6; return label;
}
function requestRender() {
  if (renderer && active && !document.hidden && !frame) frame = requestAnimationFrame(() => {
    frame = 0; if (active && !document.hidden) renderer.render(scene, camera);
  });
}
function updateScene() {
  const result = current(), colors = palette();
  planes.forEach((plane, i) => {
    plane.group.visible = mode === 'both' || i === selected;
    const compact = innerWidth <= 700 && innerHeight <= 650;
    plane.labels[0].position.y = compact ? 1.05 : 1.55;
    plane.labels[2].visible = !compact;
    plane.group.position.set(mode === 'both' ? (i === 0 ? -1.65 : 1.65) : 0, 0, mode === 'both' ? (i === 0 ? .4 : -.4) : 0);
    plane.circle.material.color.set(i === selected ? colors.selected : colors.axis);
    plane.surface.material.color.set(dark ? '#273241' : '#f4f7fc');
    plane.q.setDirection(new THREE.Vector3(result.pairs[i].q[0], result.pairs[i].q[1], 0).normalize());
    plane.k.setDirection(new THREE.Vector3(result.pairs[i].k[0], result.pairs[i].k[1], 0).normalize());
  });
}
function fitCamera() {
  if (!camera || !controls) return;
  const halfTangent = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  const width = mode === 'both' ? 6.6 : 3.2, height = 3.8;
  const distance = Math.max(height / (2 * halfTangent), width / (2 * halfTangent * camera.aspect)) * 1.05;
  controls.target.set(0, .1, 0); camera.position.copy(controls.target).addScaledVector(new THREE.Vector3(.18, .30, 1).normalize(), distance);
  camera.lookAt(controls.target); camera.updateProjectionMatrix(); controls.update(); requestRender();
}
function resize() {
  if (!renderer) return;
  const { width, height } = viewport.getBoundingClientRect(); if (width < 1 || height < 1) return;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75)); renderer.setSize(width, height, false);
  camera.aspect = width / height; updateScene(); renderCoordinates(current()); fitCamera();
}
function setOrbit(value) {
  orbit = value; if (controls) controls.enabled = orbit;
  // OrbitControls writes none at initialization, even when subsequently disabled.
  canvas.style.touchAction = orbit ? 'none' : 'pan-y'; viewport.classList.toggle('is-orbit', orbit);
  $('orbit').setAttribute('aria-pressed', String(orbit));
}
$('orbit').addEventListener('click', () => setOrbit(!orbit));
$('reset-view').addEventListener('click', () => { setOrbit(false); fitCamera(); });
function fail3D() {
  if (frame) cancelAnimationFrame(frame); frame = 0;
  controls?.dispose(); controls = null; renderer?.dispose(); renderer = null;
  viewport.classList.add('failed'); root.dataset.renderState = 'fallback';
  $('orbit').disabled = true; $('reset-view').disabled = true; renderFallback();
  $('status').textContent = text.fallback;
}
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'low-power' });
  renderer.outputColorSpace = THREE.SRGBColorSpace; scene = new THREE.Scene(); scene.background = new THREE.Color('#ffffff');
  camera = new THREE.PerspectiveCamera(43, 1, .1, 100);
  controls = new OrbitControls(camera, canvas); controls.enableDamping = false; controls.minDistance = 2.5; controls.maxDistance = 25;
  controls.addEventListener('change', requestRender); setOrbit(false);
  planes = [0, 1].map(i => {
    const group = new THREE.Group();
    const surface = new THREE.Mesh(new THREE.PlaneGeometry(2.65, 2.65), new THREE.MeshBasicMaterial({ color: '#f4f7fc', side: THREE.DoubleSide, transparent: true, opacity: .65, depthWrite: false }));
    surface.position.z = -.035; surface.userData.pair = i; group.add(surface);
    const circlePoints = Array.from({ length: 97 }, (_, j) => new THREE.Vector3(Math.cos(j / 96 * 2 * Math.PI), Math.sin(j / 96 * 2 * Math.PI), 0));
    const circle = new THREE.Line(new THREE.BufferGeometry().setFromPoints(circlePoints), new THREE.LineBasicMaterial({ color: '#b1bdcb' })); group.add(circle);
    const axes = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-1.18, 0, 0), new THREE.Vector3(1.18, 0, 0), new THREE.Vector3(0, -1.18, 0), new THREE.Vector3(0, 1.18, 0)]), new THREE.LineBasicMaterial({ color: '#b1bdcb', transparent: true, opacity: .6 })); group.add(axes);
    const original = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, .01), new THREE.Vector3(1, 0, .01)]), new THREE.LineDashedMaterial({ color: '#b1bdcb', dashSize: .05, gapSize: .035 })); original.computeLineDistances(); group.add(original);
    const q = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, .025), 1, '#3267a4', .12, .08);
    const k = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, .05), 1, '#187b79', .12, .08);
    group.add(q, k);
    const title = sprite(`${text.pair} ${i} · ω=${current().pairs[i].frequency}`, 3.0); title.position.set(0, 1.55, 0);
    const axisX = sprite(`c${i * 2}`, .7); axisX.position.set(1.30, -.14, 0);
    const axisY = sprite(`c${i * 2 + 1}`, .7); axisY.position.set(.15, 1.25, 0);
    group.add(title, axisX, axisY); scene.add(group);
    return { group, surface, q, k, circle, axes, original, labels: [title, axisX, axisY] };
  });
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2(); let down;
  canvas.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; });
  canvas.addEventListener('pointerup', event => {
    if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 6) return;
    const bounds = canvas.getBoundingClientRect(); pointer.set((event.clientX - bounds.left) / bounds.width * 2 - 1, -(event.clientY - bounds.top) / bounds.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(planes.filter(plane => plane.group.visible).map(plane => plane.surface), false)[0];
    if (hit) choosePair(hit.object.userData.pair);
  });
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); fail3D(); });
  root.dataset.renderState = 'ready';
} catch { fail3D(); }
canvas.addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); choosePair(event.key === 'ArrowLeft' ? 0 : 1); }
  else if (event.key === 'ArrowUp' || event.key === 'ArrowDown') { event.preventDefault(); const delta = event.key === 'ArrowUp' ? 1 : -1; movePosition(event.shiftKey ? 'm' : 'n', Math.max(0, Math.min(data.maximum, (event.shiftKey ? m : n) + delta))); }
  else if (event.key === 'Home') { event.preventDefault(); setOrbit(false); fitCamera(); }
});
darkMode.addEventListener('change', applyTheme);
window.addEventListener('storage', event => { if (event.key === 'haohai-tinylm-theme') applyTheme(); });
try { if (window.parent !== window) new MutationObserver(applyTheme).observe(window.parent.document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); } catch { /* Cross-origin parents use local/OS theme. */ }
new ResizeObserver(resize).observe(viewport);
new IntersectionObserver(entries => { active = entries[0].isIntersecting; if (!active && frame) { cancelAnimationFrame(frame); frame = 0; } if (active) requestRender(); }, { threshold: 0 }).observe(viewport);
document.addEventListener('visibilitychange', () => { if (document.hidden && frame) { cancelAnimationFrame(frame); frame = 0; } if (!document.hidden) requestRender(); });
setTab(tab); applyTheme(); sync(); resize();

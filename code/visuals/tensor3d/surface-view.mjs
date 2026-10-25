import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { COPY } from './surface-copy.mjs';
import { evaluate, updateParameters, sampleUpdate, domainFor } from './surface-model.mjs';
const { lang, record } = JSON.parse(document.getElementById('surface-data').textContent);
const text = COPY[lang], $ = id => document.getElementById(id);
const root = $('surface-lab'), viewport = $('surface-viewport'), canvas = $('surface-scene');
const darkPreference = matchMedia('(prefers-color-scheme: dark)');
let point = { w: record.w, b: 0 }, rate = .1, history = [], domain;
let renderer, scene, camera, controls, group, frame = 0, active = true;
const fmt = value => Math.abs(value) < 1e-10 ? '0' : Math.abs(value) >= 1e6 ? value.toExponential(4) : Number(value.toFixed(6)).toString();
const fill = (pattern, values) => pattern.replace(/\{(\w+)\}/g, (_, key) => values[key]);
function parentTheme() {
  try {
    if (parent !== window && ['light', 'dark'].includes(parent.document.documentElement.dataset.theme)) return parent.document.documentElement.dataset.theme;
    const saved = localStorage.getItem('haohai-tinylm-theme');
    if (['light', 'dark'].includes(saved)) return saved;
  } catch { /* file URLs and cross-origin embeds can restrict storage or parent access. */ }
  return darkPreference.matches ? 'dark' : 'light';
}
function applyTheme() {
  const theme = parentTheme();
  if (document.documentElement.dataset.theme !== theme) document.documentElement.dataset.theme = theme;
}
applyTheme();
const isDark = () => document.documentElement.dataset.theme === 'dark';
function allEndpoints() { return history.flatMap(row => [row.from, row.to]); }
function ui() {
  const value = evaluate(record, point.w, point.b);
  domain = domainFor(record, point, allEndpoints());
  for (const key of ['w', 'b']) {
    const number = $(key), slider = $(key + '-range');
    if (document.activeElement !== number) number.value = String(point[key]);
    slider.min = String(domain[key][0]); slider.max = String(domain[key][1]); slider.value = String(point[key]);
    slider.setAttribute('aria-valuetext', `${key} = ${fmt(point[key])}`);
  }
  $('learning-rate').value = String(rate);
  $('prediction').value = fmt(value.prediction); $('loss').value = fmt(value.loss); $('updates').value = String(history.length);
  $('gradient').textContent = `∂L/∂w = ${fmt(value.gw)} · ∂L/∂b = ${fmt(value.gb)}`;
  $('domain').value = `w ∈ [${domain.w.map(fmt).join(', ')}] · b ∈ [${domain.b.map(fmt).join(', ')}] · L ∈ [0, ${fmt(domain.maxLoss)}]`;
  $('history').replaceChildren(...history.map((row, index) => {
    const tr = document.createElement('tr');
    const columns = [index + 1, `${row.both ? 'w + b' : 'w'} · η ${row.rate}`, `(${fmt(row.from.w)}, ${fmt(row.from.b)}) → (${fmt(row.to.w)}, ${fmt(row.to.b)})`, `${fmt(row.before)} → ${fmt(row.after)}`];
    columns.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
    return tr;
  }));
  $('empty-history').hidden = history.length > 0;
  rebuild();
}
function message(value) { $('change').textContent = value; }
function edit(key, input) {
  if (input.value.trim() === '') return;
  const value = Number(input.value);
  if (value === point[key]) return;
  try {
    const next = { ...point, [key]: value };
    evaluate(record, next.w, next.b); domainFor(record, next);
    point = next; history = []; message(text.manual); ui();
  } catch { message(text.invalid); }
}
for (const key of ['w', 'b']) {
  $(key).addEventListener('input', event => edit(key, event.target));
  $(key).addEventListener('change', event => { edit(key, event.target); event.target.value = String(point[key]); });
  $(key + '-range').addEventListener('input', event => edit(key, event.target));
}
$('learning-rate').addEventListener('change', event => { rate = Number(event.target.value); message(fill(text.changedRate, { rate })); });
function update(both) {
  try {
    const from = { ...point }, to = updateParameters(record, from, rate, both);
    const before = evaluate(record, from.w, from.b).loss, after = evaluate(record, to.w, to.b).loss;
    domainFor(record, to, [...allEndpoints(), from]);
    history.push({ from, to, before, after, rate, both }); point = to;
    const trend = after < before - 1e-9 ? text.down : after > before + 1e-9 ? text.up : text.same;
    message(fill(text.update, { step: history.length, before: fmt(before), after: fmt(after), trend })); ui();
  } catch { message(text.invalid); }
}
$('weight-step').addEventListener('click', () => update(false));
$('both-step').addEventListener('click', () => update(true));
$('reset').addEventListener('click', () => { point = { w: record.w, b: 0 }; history = []; message(text.start); ui(); });
function requestRender() {
  if (renderer && active && !document.hidden && !frame) frame = requestAnimationFrame(() => { frame = 0; renderer?.render(scene, camera); });
}
function disposeObject(object) {
  object.traverse(child => {
    child.geometry?.dispose();
    for (const material of child.material ? Array.isArray(child.material) ? child.material : [child.material] : []) { material.map?.dispose(); material.dispose(); }
  });
}
function addLine(points, color, opacity = 1, dashed = false) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = dashed ? new THREE.LineDashedMaterial({ color, dashSize: .12, gapSize: .09, transparent: opacity < 1, opacity }) : new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthTest: false, depthWrite: false });
  const line = new THREE.Line(geometry, material); if (dashed) line.computeLineDistances();
  line.renderOrder = 3; group.add(line); return line;
}
function label(value, position, color, size = .34) {
  const bitmap = document.createElement('canvas'); bitmap.width = 512; bitmap.height = 96;
  const ctx = bitmap.getContext('2d'); ctx.clearRect(0, 0, 512, 96); ctx.font = "500 52px 'PingFang SC','Microsoft YaHei',Arial,sans-serif";
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = color; ctx.fillText(value, 256, 48, 500);
  const texture = new THREE.CanvasTexture(bitmap); texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false, depthWrite: false }));
  const visibleHeight = camera.top - camera.bottom;
  const screenSize = (viewport.clientWidth < 420 ? 10 : 12) * visibleHeight / viewport.clientHeight * 96 / 52 * size / .34;
  sprite.position.copy(position); sprite.scale.set(screenSize * 512 / 96, screenSize, 1); sprite.renderOrder = 8; group.add(sprite);
}
function world(w, b, loss = 0) {
  return new THREE.Vector3((w - domain.w[0]) / (domain.w[1] - domain.w[0]) * 7 - 3.5, loss / domain.maxLoss * 4.2, (b - domain.b[0]) / (domain.b[1] - domain.b[0]) * 6 - 3);
}
function dot(position, color, radius = .08) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 16, 12), new THREE.MeshBasicMaterial({ color, depthTest: false, depthWrite: false, transparent: true }));
  mesh.position.copy(position); mesh.renderOrder = 7; group.add(mesh);
}
function rebuild() {
  if (!renderer || !domain) return;
  if (group) { scene.remove(group); disposeObject(group); }
  group = new THREE.Group(); scene.add(group);
  const ink = isDark() ? '#cad5e3' : '#606c7b', surfaceLow = new THREE.Color(isDark() ? '#465775' : '#dce4f0'), surfaceHigh = new THREE.Color(isDark() ? '#b99acb' : '#b198ca');
  const positions = [], colors = [], indices = [], count = 40;
  for (let i = 0; i <= count; i++) for (let j = 0; j <= count; j++) {
    const w = domain.w[0] + (domain.w[1] - domain.w[0]) * i / count, b = domain.b[0] + (domain.b[1] - domain.b[0]) * j / count;
    const loss = evaluate(record, w, b).loss, p = world(w, b, loss), color = surfaceLow.clone().lerp(surfaceHigh, loss / domain.maxLoss);
    positions.push(...p.toArray()); colors.push(color.r, color.g, color.b);
    if (i < count && j < count) { const a = i * (count + 1) + j, c = a + count + 1; indices.push(a, c, a + 1, c, c + 1, a + 1); }
  }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3)); geometry.setIndex(indices); geometry.computeVertexNormals();
  group.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, transparent: true, opacity: isDark() ? .69 : .73, depthWrite: false })));
  group.add(new THREE.LineSegments(new THREE.WireframeGeometry(geometry), new THREE.LineBasicMaterial({ color: isDark() ? '#9b88b2' : '#aa9cb9', transparent: true, opacity: .2 })));
  // Floor grid and three labeled axes use linear scales. Normalization only fits their displayed ranges.
  for (let i = 0; i <= 4; i++) {
    const w = domain.w[0] + (domain.w[1] - domain.w[0]) * i / 4, b = domain.b[0] + (domain.b[1] - domain.b[0]) * i / 4;
    addLine([world(w, domain.b[0]), world(w, domain.b[1])], ink, .2);
    addLine([world(domain.w[0], b), world(domain.w[1], b)], ink, .2);
  }
  const origin = world(domain.w[0], domain.b[0]);
  addLine([origin, world(domain.w[1], domain.b[0])], ink, .8);
  addLine([origin, world(domain.w[0], domain.b[1])], ink, .8);
  addLine([origin, world(domain.w[0], domain.b[0], domain.maxLoss)], ink, .8);
  label('w', world(domain.w[1], domain.b[0]).add(new THREE.Vector3(.1, -.24, 0)), ink);
  label('b', world(domain.w[0], domain.b[1]).add(new THREE.Vector3(0, -.24, .1)), ink);
  label('L', world(domain.w[0], domain.b[0], domain.maxLoss).add(new THREE.Vector3(.15, -.2, 0)), ink);
  // b=0 slice: the exact scalar loss from lesson 04, sampled across the current w domain.
  addLine(Array.from({ length: 129 }, (_, i) => { const w = domain.w[0] + (domain.w[1] - domain.w[0]) * i / 128; return world(w, 0, evaluate(record, w, 0).loss); }), '#5086c5');
  for (const row of history) {
    const samples = sampleUpdate(record, row.from, row.to, 64);
    const points = samples.map(p => world(p.w, p.b, p.loss));
    // A tube makes the 64 sampled intervals visible on a small display; its center follows the same polyline.
    class SampledPath extends THREE.Curve {
      getPoint(t, target = new THREE.Vector3()) {
        const at = t * (points.length - 1), index = Math.min(points.length - 2, Math.floor(at));
        return target.copy(points[index]).lerp(points[index + 1], at - index);
      }
    }
    const pathMesh = new THREE.Mesh(new THREE.TubeGeometry(new SampledPath(), 64, .025, 6, false), new THREE.MeshBasicMaterial({ color: '#23998a', depthTest: false, depthWrite: false, transparent: true }));
    pathMesh.renderOrder = 5; group.add(pathMesh);
    dot(world(row.from.w, row.from.b, row.before), '#23998a', .055);
  }
  const value = evaluate(record, point.w, point.b), ground = world(point.w, point.b), current = world(point.w, point.b, value.loss);
  addLine([ground, current], '#df6371', .8, true); dot(current, '#df6371', .11);
  label(`L = ${fmt(value.loss)}`, current.clone().add(new THREE.Vector3(.2, .34, 0)), isDark() ? '#ffb0ba' : '#b4495a');
  const direction = new THREE.Vector3(-value.gw / (domain.w[1] - domain.w[0]) * 7, 0, -value.gb / (domain.b[1] - domain.b[0]) * 6);
  if (direction.length() > 1e-10) {
    direction.normalize(); ground.y = .035;
    const arrow = new THREE.ArrowHelper(direction, ground, 1.1, '#c39129', .2, .13);
    arrow.traverse(child => { if (child.material) { child.material.transparent = true; child.material.depthTest = child.material.depthWrite = false; child.renderOrder = 6; } });
    group.add(arrow);
    label('−∇L', ground.clone().addScaledVector(direction, .7).add(new THREE.Vector3(0, .22, 0)), isDark() ? '#f6cc72' : '#a57516', .3);
  }
  requestRender();
}
function fit() {
  if (!renderer) return;
  const width = viewport.clientWidth, height = viewport.clientHeight;
  if (!width || !height) return;
  const halfHeight = Math.max(4.1, 5.5 * height / width), halfWidth = halfHeight * width / height;
  camera.left = -halfWidth; camera.right = halfWidth; camera.top = halfHeight; camera.bottom = -halfHeight; camera.updateProjectionMatrix();
  renderer.setSize(width, height, false); rebuild(); requestRender();
}
function fixedView() {
  if (!camera) return;
  camera.position.set(10, 8, 12); controls.target.set(0, 1.7, 0); camera.zoom = 1; camera.updateProjectionMatrix(); controls.update();
  controls.enabled = false; canvas.style.touchAction = 'pan-y'; viewport.classList.remove('is-orbit');
  $('orbit').setAttribute('aria-pressed', 'false'); $('orbit').textContent = text.orbit; requestRender();
}
function failed() {
  root.dataset.renderState = 'fallback'; viewport.classList.add('failed');
  $('orbit').disabled = $('reset-view').disabled = true;
  controls?.dispose(); const old = renderer; renderer = null; old?.dispose();
  if (frame) cancelAnimationFrame(frame); frame = 0;
}
ui();
try {
  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true }); renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  scene = new THREE.Scene(); camera = new THREE.OrthographicCamera(-7, 7, 4.1, -4.1, .1, 100);
  controls = new OrbitControls(camera, canvas); controls.enabled = false; controls.enableDamping = false; controls.enablePan = false; controls.enableZoom = false;
  controls.minPolarAngle = .15; controls.maxPolarAngle = Math.PI / 2 - .04; controls.addEventListener('change', requestRender);
  canvas.style.touchAction = 'pan-y'; fixedView(); fit(); rebuild(); root.dataset.renderState = 'ready';
  $('orbit').addEventListener('click', () => {
    controls.enabled = !controls.enabled; canvas.style.touchAction = controls.enabled ? 'none' : 'pan-y';
    viewport.classList.toggle('is-orbit', controls.enabled); $('orbit').setAttribute('aria-pressed', String(controls.enabled)); $('orbit').textContent = controls.enabled ? text.fixed : text.orbit;
  });
  $('reset-view').addEventListener('click', fixedView);
  canvas.addEventListener('keydown', event => {
    if (event.key === 'Home') { event.preventDefault(); fixedView(); return; }
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const spherical = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
    if (event.key === 'ArrowLeft') spherical.theta -= .15; if (event.key === 'ArrowRight') spherical.theta += .15;
    if (event.key === 'ArrowUp') spherical.phi -= .1; if (event.key === 'ArrowDown') spherical.phi += .1;
    spherical.phi = THREE.MathUtils.clamp(spherical.phi, .15, Math.PI / 2 - .04);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical)); controls.update(); requestRender();
  });
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); failed(); });
  new ResizeObserver(fit).observe(viewport);
} catch { failed(); }
new MutationObserver(rebuild).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
darkPreference.addEventListener('change', applyTheme); addEventListener('storage', applyTheme);
try { if (parent !== window) new MutationObserver(applyTheme).observe(parent.document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); } catch { /* Cross-origin embeds follow their own preference. */ }
new IntersectionObserver(entries => { active = entries[0].isIntersecting; if (active) requestRender(); }).observe(viewport);
document.addEventListener('visibilitychange', requestRender);
addEventListener('pagehide', event => {
  if (frame) cancelAnimationFrame(frame); frame = 0;
  if (!event.persisted) { controls?.dispose(); if (group) disposeObject(group); renderer?.dispose(); }
});
addEventListener('pageshow', requestRender);

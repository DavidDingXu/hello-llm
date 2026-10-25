import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { COPY } from './copy.mjs';
import { cellsFromRecord, indexAt, positionAt, shapeAt } from './model.mjs';

const { lang, record } = JSON.parse(document.getElementById('tensor-data').textContent);
const text = COPY[lang], cells = cellsFromRecord(record);
const $ = id => document.getElementById(id);
const root = $('lab'), viewport = $('viewport'), canvas = $('scene');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const darkMode = matchMedia('(prefers-color-scheme: dark)');
const query = new URLSearchParams(location.hash.slice(1));
const bounded = (value, max, fallback) => Number.isInteger(value) && value >= 0 && value <= max ? value : fallback;
let stage = bounded(Number(query.get('step') ?? 0), 4, 0);
let selected = bounded(Number(query.get('cell') ?? 4), cells.length - 1, 4);
let playing = false, timer, active = true, renderer, controls, scene, camera;
let meshes = [], frame = 0, transition;

function isDark() {
  try {
    const theme = window.parent !== window ? window.parent.document.documentElement.dataset.theme
      : localStorage.getItem('haohai-tinylm-theme');
    if (theme === 'dark' || theme === 'light') return theme === 'dark';
  } catch { /* Respect the OS preference if storage or the parent is unavailable. */ }
  return darkMode.matches;
}
function applyTheme() {
  document.documentElement.dataset.theme = isDark() ? 'dark' : 'light';
}
applyTheme();

// The table is the keyboard/touch path and remains usable without a GPU.
const stepButtons = text.steps.map((label, i) => {
  const b = document.createElement('button');
  const number = document.createElement('b'); number.textContent = i + 1;
  b.append(number, document.createTextNode(label));
  b.addEventListener('click', () => { stop(); setStage(i); });
  $('steps').append(b); return b;
});
const cellButtons = cells.map((cell, i) => {
  const option = document.createElement('option'); option.value = i; option.textContent = cell.value;
  $('cell-picker').append(option);
  const b = document.createElement('button'); b.dataset.head = cell.h;
  const value = document.createElement('strong'); value.textContent = cell.value;
  const index = document.createElement('small');
  b.append(value, index); b.addEventListener('click', () => choose(i));
  $('cell-table').append(b); return b;
});
function saveState() {
  try { history.replaceState(null, '', `#step=${stage}&cell=${selected}`); } catch { /* file URLs may restrict history. */ }
}
function syncUI() {
  const cell = cells[selected];
  $('cell-picker').value = String(selected);
  $('shape').textContent = `[${shapeAt(record, stage).join(', ')}]`;
  $('tracked').textContent = cell.value;
  $('original-index').textContent = `X[${indexAt(cell, 0).join(',')}]`;
  const name = stage === 2 ? 'heads' : stage === 4 ? 'merged' : 'X';
  $('current-index').textContent = `${name}[${indexAt(cell, stage).join(',')}]`;
  $('step-title').textContent = `${stage + 1}. ${text.steps[stage]}`;
  $('description').textContent = text.descriptions[stage];
  $('code').textContent = text.codes[stage];
  $('progress').textContent = `${stage + 1} / 5`;
  $('previous').disabled = stage === 0; $('next').disabled = stage === 4;
  stepButtons.forEach((b, i) => i === stage ? b.setAttribute('aria-current', 'step') : b.removeAttribute('aria-current'));
  cellButtons.forEach((b, i) => {
    b.setAttribute('aria-pressed', String(i === selected));
    b.lastElementChild.textContent = `[${indexAt(cells[i], stage).join(',')}]`;
    b.setAttribute('aria-label', `${text.value} ${cells[i].value}, ${text.index} ${indexAt(cells[i], stage).join(', ')}`);
  });
  ['x', 'y', 'z'].forEach((axis, i) => $( `axis-${axis}`).textContent = text.axes[stage][i]);
  if (meshes.length) updateHighlight();
  saveState();
}
function choose(i) { selected = i; syncUI(); requestRender(); }
$('cell-picker').addEventListener('change', event => choose(Number(event.target.value)));
function stop() { playing = false; clearTimeout(timer); $('play').textContent = text.play; }
function schedule() {
  clearTimeout(timer);
  if (!playing || !active || document.hidden) return;
  timer = setTimeout(() => { if (stage === 4) stop(); else { setStage(stage + 1); schedule(); } }, 2600);
}
function setStage(i, animate = true) {
  stage = bounded(i, 4, stage);
  if (meshes.length) {
    const from = meshes.map(m => m.position.clone());
    const to = cells.map(c => new THREE.Vector3(...positionAt(c, stage)));
    transition = animate && !reducedMotion.matches && active ? { from, to, start: performance.now() } : null;
    if (!transition) meshes.forEach((m, j) => m.position.copy(to[j]));
  }
  syncUI(); requestRender();
}
$('previous').addEventListener('click', () => { stop(); setStage(stage - 1); });
$('next').addEventListener('click', () => { stop(); setStage(stage + 1); });
$('restart').addEventListener('click', () => { stop(); setStage(0); });
$('play').addEventListener('click', () => {
  if (playing) return stop();
  if (stage === 4) setStage(0);
  playing = true; $('play').textContent = text.pause; schedule();
});

function labelSprite(value) {
  const label = document.createElement('canvas'); label.width = label.height = 128;
  const ctx = label.getContext('2d'); ctx.clearRect(0, 0, 128, 128);
  ctx.font = '600 68px Arial, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ffffff'; ctx.fillText(String(value), 64, 66);
  const texture = new THREE.CanvasTexture(label); texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, depthTest: false, depthWrite: false });
  const sprite = new THREE.Sprite(material); sprite.scale.set(.65, .65, 1); sprite.renderOrder = 10;
  sprite.position.z = .31;
  return sprite;
}
function updateHighlight() {
  meshes.forEach((m, i) => {
    m.userData.outline.visible = i === selected;
    m.material.emissive.set(i === selected ? '#172c3e' : '#000000');
  });
}
function requestRender() {
  if (renderer && active && !document.hidden && !frame) frame = requestAnimationFrame(render);
}
function render(now) {
  frame = 0;
  if (transition) {
    const fraction = Math.min(1, Math.max(0, (now - transition.start) / 650));
    const t = fraction * fraction * (3 - 2 * fraction);
    meshes.forEach((m, i) => m.position.lerpVectors(transition.from[i], transition.to[i], t));
    if (fraction === 1) transition = null;
  }
  renderer.render(scene, camera);
  if (transition) requestRender();
}
function fitCamera() {
  const width = viewport.clientWidth, height = viewport.clientHeight;
  if (!width || !height || !renderer) return;
  // A bounding sphere keeps every cell in frame at both named viewing angles.
  const halfHeight = Math.max(3.25, 3.45 * height / width);
  const halfWidth = halfHeight * width / height;
  camera.left = -halfWidth; camera.right = halfWidth;
  camera.top = halfHeight; camera.bottom = -halfHeight; camera.updateProjectionMatrix();
  renderer.setSize(width, height, false); requestRender();
}
function setView(front = false) {
  camera.position.set(...(front ? [0, 0, 14] : [7, 5, 12]));
  controls.target.set(0, 0, 0); camera.zoom = 1;
  camera.updateProjectionMatrix(); controls.update(); requestRender();
}
function failed() {
  stop(); transition = null;
  root.dataset.renderState = 'fallback'; viewport.classList.add('failed');
  $('status').textContent = text.fallback;
  document.querySelectorAll('.view-controls button').forEach(b => b.disabled = true);
  if (frame) cancelAnimationFrame(frame); frame = 0;
  controls?.dispose(); renderer?.dispose(); renderer = null;
}

syncUI();
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  scene = new THREE.Scene();
  camera = new THREE.OrthographicCamera(-5, 5, 3.25, -3.25, .1, 100);
  controls = new OrbitControls(camera, canvas);
  controls.enabled = false; controls.enablePan = false;
  // OrbitControls sets inline touch-action:none even while disabled.
  // Restore native page scrolling until the reader explicitly enables rotation.
  canvas.style.touchAction = 'pan-y';
  controls.minZoom = .7; controls.maxZoom = 1.5;
  controls.minPolarAngle = .4; controls.maxPolarAngle = Math.PI - .4;
  controls.addEventListener('change', requestRender);
  scene.add(new THREE.AmbientLight('#ffffff', 2));
  const light = new THREE.DirectionalLight('#ffffff', 2.5); light.position.set(4, 8, 12); scene.add(light);
  const geometry = new THREE.BoxGeometry(.95, .95, .48);
  const edges = new THREE.EdgesGeometry(new THREE.BoxGeometry(1.04, 1.04, .57));
  const edgeMaterial = new THREE.LineBasicMaterial({ color: isDark() ? '#f6f8fa' : '#17222e' });
  meshes = cells.map((cell, i) => {
    const material = new THREE.MeshStandardMaterial({ color: cell.h === 0 ? '#507fb8' : '#238779', roughness: .8 });
    const mesh = new THREE.Mesh(geometry, material); mesh.userData.cell = i;
    mesh.position.set(...positionAt(cell, stage));
    const outline = new THREE.LineSegments(edges, edgeMaterial);
    outline.visible = i === selected; mesh.userData.outline = outline; mesh.add(outline);
    mesh.add(labelSprite(cell.value)); scene.add(mesh); return mesh;
  });
  updateHighlight(); setView(); fitCamera();
  root.dataset.renderState = 'ready'; $('status').textContent = text.ready;
  new ResizeObserver(fitCamera).observe(viewport);
  const raycaster = new THREE.Raycaster();
  let down;
  canvas.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; });
  canvas.addEventListener('pointerup', event => {
    if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 6) { down = null; return; }
    down = null;
    const rect = canvas.getBoundingClientRect();
    const pointer = new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(meshes, false)[0];
    if (hit) choose(hit.object.userData.cell);
  });
  canvas.addEventListener('pointercancel', () => { down = null; });
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); failed(); });
  $('orbit').addEventListener('click', () => {
    controls.enabled = !controls.enabled;
    canvas.style.touchAction = controls.enabled ? 'none' : 'pan-y';
    viewport.classList.toggle('is-orbit', controls.enabled);
    $('orbit').setAttribute('aria-pressed', String(controls.enabled));
    $('orbit').textContent = controls.enabled ? text.fixed : text.orbit;
    $('status').textContent = controls.enabled ? text.orbitHelp : text.ready;
  });
  $('reset-view').addEventListener('click', () => setView());
  $('front').addEventListener('click', () => setView(true));
  $('angle').addEventListener('click', () => setView());
  function zoom(scale) { camera.zoom = THREE.MathUtils.clamp(camera.zoom * scale, .7, 1.5); camera.updateProjectionMatrix(); requestRender(); }
  $('zoom-in').addEventListener('click', () => zoom(1.1));
  $('zoom-out').addEventListener('click', () => zoom(1 / 1.1));
  function themeChanged() { applyTheme(); edgeMaterial.color.set(isDark() ? '#f6f8fa' : '#17222e'); requestRender(); }
  darkMode.addEventListener('change', themeChanged);
  window.addEventListener('storage', themeChanged);
  try {
    if (window.parent !== window) new MutationObserver(themeChanged).observe(window.parent.document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  } catch { /* Cross-origin embeds follow their own OS theme. */ }
} catch { failed(); }

function settle() {
  if (transition) { meshes.forEach((m, i) => m.position.copy(transition.to[i])); transition = null; }
  if (frame) cancelAnimationFrame(frame); frame = 0;
}
new IntersectionObserver(entries => {
  active = entries[0].isIntersecting;
  if (active) { requestRender(); schedule(); } else { clearTimeout(timer); settle(); }
}).observe(viewport);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { clearTimeout(timer); settle(); } else { requestRender(); schedule(); }
});
reducedMotion.addEventListener('change', () => { settle(); requestRender(); });
window.addEventListener('pagehide', event => {
  stop(); settle();
  if (!event.persisted) {
    controls?.dispose();
    scene?.traverse(object => {
      object.geometry?.dispose();
      if (object.material) { object.material.map?.dispose(); object.material.dispose(); }
    });
    renderer?.dispose();
  }
});
window.addEventListener('pageshow', () => requestRender());
window.addEventListener('hashchange', () => {
  const params = new URLSearchParams(location.hash.slice(1));
  selected = bounded(Number(params.get('cell') ?? 4), cells.length - 1, 4);
  stop(); setStage(bounded(Number(params.get('step') ?? 0), 4, 0), false);
});

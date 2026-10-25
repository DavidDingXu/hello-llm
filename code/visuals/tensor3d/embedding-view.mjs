import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { COPY } from './embedding-copy.mjs';
import { validateData, initialBatch, inspectCell, replaceId } from './embedding-model.mjs';

const $ = id => document.getElementById(id), root = $('lab'), viewport = $('viewport'), canvas = $('scene');
const data = JSON.parse($('embedding-data').textContent); validateData(data);
const text = COPY[data.lang], english = data.lang === 'en', word = (zh, en) => english ? en : zh;
let ids = initialBatch(data), batch = 0, position = 0, feature = 0, dark = false, orbit = false;
let renderer, scene, camera, controls, selectedOutline, frame = 0, active = true;
const cells = [], labels = [], darkMode = matchMedia('(prefers-color-scheme: dark)');
const palette = ['#3267a4', '#8056a5', '#187b79', '#aa7928'];
const number = value => String(value).replace('-', '−');

function choose(b, t, d, focus = false) {
  inspectCell(data, ids, b, t, d); batch = b; position = t; feature = d; sync();
  if (focus) outputButtons[b][t][d].focus();
}
function cellKeys(event, b, t, d) {
  const key = event.key;
  if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home'].includes(key)) return;
  event.preventDefault();
  if (key === 'Home') { setOrbit(false); fitCamera(); return; }
  if (key === 'ArrowLeft') d = Math.max(0, d - 1);
  if (key === 'ArrowRight') d = Math.min(1, d + 1);
  if (key === 'ArrowUp') t = Math.max(0, t - 1);
  if (key === 'ArrowDown') t = Math.min(2, t + 1);
  if (key === 'PageUp') b = Math.max(0, b - 1);
  if (key === 'PageDown') b = Math.min(1, b + 1);
  choose(b, t, d, event.currentTarget !== canvas);
}
const tokenButtons = ids.map((sample, b) => {
  const section = document.createElement('div'); section.className = 'sample-input';
  const title = document.createElement('span'); title.className = 'sample-label'; title.textContent = `${text.sample} ${b}`;
  const row = document.createElement('div'); row.className = 'token-row'; section.append(title, row); $('input-samples').append(section);
  return sample.map((_, t) => {
    const button = document.createElement('button'), small = document.createElement('small'), value = document.createElement('span');
    button.type = 'button'; small.textContent = `T=${t}`; button.append(small, value); row.append(button);
    button.addEventListener('click', () => choose(b, t, feature));
    button.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault(); const nextB = Math.max(0, Math.min(1, b + (event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0)));
      const nextT = Math.max(0, Math.min(2, t + (event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0)));
      choose(nextB, nextT, feature); tokenButtons[nextB][nextT].focus();
    }); return button;
  });
});
const tableButtons = data.toy_table.map((values, id) => {
  const button = document.createElement('button'); button.type = 'button'; button.className = 'table-row';
  const title = document.createElement('b'); title.textContent = `ID ${id}`; button.append(title);
  values.forEach(value => { const span = document.createElement('span'); span.textContent = number(value); button.append(span); });
  button.setAttribute('aria-label', `${text.row} ${id}, [${values.join(', ')}]. ${text.tableHint}`);
  button.addEventListener('click', () => { ids = replaceId(data, ids, batch, position, id); sync(); }); $('table').append(button); return button;
});
function createOutputs(target) {
  return ids.map((sample, b) => {
    const section = document.createElement('div'); section.className = 'output-sample';
    const title = document.createElement('h3'); title.textContent = `B=${b} · [T,D]=[3,2]`;
    const grid = document.createElement('div'); grid.className = 'output-grid'; section.append(title, grid); target.append(section);
    return sample.map((_, t) => data.toy_table[0].map((__, d) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'out-cell';
      const small = document.createElement('small'); small.textContent = `${t},${d}`;
      const value = document.createElement('span'); button.append(small, value); grid.append(button);
      button.addEventListener('click', () => choose(b, t, d)); button.addEventListener('keydown', event => cellKeys(event, b, t, d));
      return button;
    }));
  });
}
const outputButtons = createOutputs($('output-cells')), fallbackButtons = createOutputs($('fallback-cells'));
const vocabButtons = data.tokens.map((token, i) => {
  const button = document.createElement('button'); button.type = 'button'; button.textContent = `${token} → ${data.ids[i]}`;
  button.addEventListener('click', () => {
    vocabButtons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    $('vocab-status').textContent = `${word('字符', 'Character')} “${token}” → ${word('真实词表编号', 'real vocabulary ID')} ${data.vocab.indexOf(token)}. ${text.vocabNote}`;
  }); $('vocab').append(button); return button;
});

function sync() {
  const item = inspectCell(data, ids, batch, position, feature);
  $('batch').value = batch; $('position').value = position;
  for (let d = 0; d < 2; d++) $('feature-' + d).setAttribute('aria-pressed', String(d === feature));
  tokenButtons.forEach((sample, b) => sample.forEach((button, t) => {
    button.lastElementChild.textContent = `ID ${ids[b][t]}`;
    button.setAttribute('aria-pressed', String(b === batch && t === position));
    button.classList.toggle('shared', ids[b][t] === item.id);
    button.setAttribute('aria-label', `${text.sample} ${b}, T ${t}, ID ${ids[b][t]}`);
  }));
  tableButtons.forEach((button, id) => {
    button.setAttribute('aria-pressed', String(id === item.id));
    [...button.querySelectorAll('span')].forEach((span, d) => span.classList.toggle('current-feature', id === item.id && d === feature));
  });
  $('address').textContent = `out[${batch},${position},${feature}] = E[${item.id},${feature}]`;
  $('value').textContent = number(item.value); $('vector').textContent = `[${item.row.map(number).join(', ')}]`;
  $('repeat-note').textContent = `${text.repeated}: ID ${item.id} → ${item.matches.map(([b, t]) => `[${b},${t}]`).join(' · ')}`;
  for (const buttons of [outputButtons, fallbackButtons]) buttons.forEach((sample, b) => sample.forEach((row, t) => row.forEach((button, d) => {
    const value = data.toy_table[ids[b][t]][d]; button.lastElementChild.textContent = number(value);
    button.classList.toggle('shared', ids[b][t] === item.id);
    button.setAttribute('aria-pressed', String(b === batch && t === position && d === feature));
    button.setAttribute('aria-label', `B ${b}, T ${t}, D ${d}, ID ${ids[b][t]}, ${word('数值', 'value')} ${value}`);
  })));
  $('status').textContent = `${text.sample} ${batch}, T ${position}, D ${feature}. ID ${item.id} → ${item.value}. ${text.unchanged}`;
  if (scene) updateScene();
}
$('batch').addEventListener('change', event => choose(Number(event.target.value), position, feature));
$('position').addEventListener('change', event => choose(batch, Number(event.target.value), feature));
for (let d = 0; d < 2; d++) $('feature-' + d).addEventListener('click', () => choose(batch, position, d));
$('reset').addEventListener('click', () => { ids = initialBatch(data); choose(0, 0, 0); });
canvas.addEventListener('keydown', event => cellKeys(event, batch, position, feature));

function readTheme() {
  try {
    const theme = (window.parent !== window ? window.parent.document.documentElement.dataset.theme : null) || localStorage.getItem('haohai-tinylm-theme');
    if (theme === 'dark' || theme === 'light') return theme === 'dark';
  } catch { /* A standalone or cross-origin page uses the OS preference. */ }
  return darkMode.matches;
}
function applyTheme() {
  dark = readTheme(); document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  if (!scene) return;
  scene.background.set(dark ? '#1d2530' : '#ffffff');
  selectedOutline.material.color.set(dark ? '#f1f5fc' : '#233448');
  for (const label of labels) refreshLabel(label, label.value);
  requestRender();
}
function labelTexture(value, color) {
  const label = document.createElement('canvas'), context = label.getContext('2d');
  const font = '600 64px Arial, "PingFang SC", sans-serif'; context.font = font;
  label.width = Math.max(64, Math.ceil(context.measureText(value).width) + 24); label.height = 96;
  context.font = font; context.textAlign = 'center'; context.textBaseline = 'middle';
  context.fillStyle = color || (dark ? '#e5eaf1' : '#233448'); context.fillText(value, label.width / 2, 48);
  const texture = new THREE.CanvasTexture(label); texture.colorSpace = THREE.SRGBColorSpace; return texture;
}
function addLabel(value, at, width = 1.1, color = undefined) {
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTexture(value, color), depthTest: false, depthWrite: false }));
  const size = sprite.material.map.image;
  sprite.scale.set(width * .6 * size.width / size.height, width * .6, 1); sprite.position.copy(at); sprite.renderOrder = 6; scene.add(sprite);
  const label = { sprite, value, color, width }; labels.push(label); return label;
}
function refreshLabel(label, value) {
  label.value = value; label.sprite.material.map.dispose(); label.sprite.material.map = labelTexture(value, label.color);
  const image = label.sprite.material.map.image;
  label.sprite.scale.set(label.width * .6 * image.width / image.height, label.width * .6, 1);
}
function locationFor(b, t, d) { return new THREE.Vector3((d - .5) * 1.18, (1 - t) * 1.05, (b - .5) * 3.35); }
function requestRender() {
  if (!renderer || !active || document.hidden || frame) return;
  frame = requestAnimationFrame(() => { frame = 0; if (renderer && active && !document.hidden) renderer.render(scene, camera); });
}
function updateScene() {
  const currentId = ids[batch][position];
  cells.forEach(cell => {
    const id = ids[cell.b][cell.t], value = data.toy_table[id][cell.d];
    cell.mesh.material.color.set(palette[id]); cell.mesh.material.opacity = id === currentId ? .85 : .32;
    if (cell.label.value !== number(value)) {
      refreshLabel(cell.label, number(value));
    }
  });
  selectedOutline.position.copy(locationFor(batch, position, feature)); requestRender();
}
function fitCamera() {
  if (!camera || !renderer) return;
  camera.position.set(8, 5, 10); camera.lookAt(0, 0, 0); camera.updateMatrixWorld();
  const aspect = Math.max(1, viewport.clientWidth) / Math.max(1, viewport.clientHeight);
  const points = [];
  for (const x of [-1.8, 1.8]) for (const y of [-1.85, 2]) for (const z of [-2.15, 2.15]) points.push(new THREE.Vector3(x, y, z).applyMatrix4(camera.matrixWorldInverse));
  const minX = Math.min(...points.map(p => p.x)), maxX = Math.max(...points.map(p => p.x));
  const minY = Math.min(...points.map(p => p.y)), maxY = Math.max(...points.map(p => p.y));
  const half = Math.max((maxY - minY) / 2 + .30, ((maxX - minX) / 2 + .30) / aspect);
  const midX = (minX + maxX) / 2, midY = (minY + maxY) / 2;
  camera.left = midX - half * aspect; camera.right = midX + half * aspect; camera.top = midY + half; camera.bottom = midY - half;
  camera.updateProjectionMatrix(); controls?.target.set(0, 0, 0); controls?.update(); requestRender();
}
function resize() {
  if (!renderer || !viewport.clientWidth || !viewport.clientHeight) return;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75)); renderer.setSize(viewport.clientWidth, viewport.clientHeight, false); fitCamera();
}
function setOrbit(value) {
  orbit = value; if (controls) controls.enabled = orbit;
  canvas.style.touchAction = orbit ? 'none' : 'pan-y'; viewport.classList.toggle('is-orbit', orbit);
  $('orbit').setAttribute('aria-pressed', String(orbit));
}
$('orbit').addEventListener('click', () => setOrbit(!orbit));
$('reset-view').addEventListener('click', () => { setOrbit(false); fitCamera(); });
function fallback() {
  if (frame) cancelAnimationFrame(frame); frame = 0; controls?.dispose(); controls = null; renderer?.dispose(); renderer = null;
  viewport.classList.add('failed'); root.dataset.renderState = 'fallback';
  $('orbit').disabled = true; $('reset-view').disabled = true; $('status').textContent = text.fallback;
}
applyTheme(); sync();
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene(); scene.background = new THREE.Color(dark ? '#1d2530' : '#ffffff');
  camera = new THREE.OrthographicCamera(-5, 5, 4, -4, .1, 100);
  scene.add(new THREE.AmbientLight('#ffffff', 2.8));
  const light = new THREE.DirectionalLight('#ffffff', 2.1); light.position.set(4, 7, 9); scene.add(light);
  controls = new OrbitControls(camera, canvas); controls.enableDamping = false; controls.enablePan = false; controls.enableZoom = false;
  controls.addEventListener('change', requestRender); setOrbit(false);
  const geometry = new THREE.BoxGeometry(.74, .74, .38);
  for (let b = 0; b < 2; b++) {
    addLabel(`B=${b}`, new THREE.Vector3(0, 1.75, (b - .5) * 3.35), .7);
    for (let t = 0; t < 3; t++) {
      addLabel(`T${t}`, locationFor(b, t, 0).add(new THREE.Vector3(-.79, 0, .25)), .65);
      for (let d = 0; d < 2; d++) {
        const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: palette[ids[b][t]], roughness: .82, transparent: true, opacity: .75 }));
        mesh.position.copy(locationFor(b, t, d)); mesh.userData = { b, t, d }; scene.add(mesh);
        const label = addLabel(number(data.toy_table[ids[b][t]][d]), mesh.position.clone().add(new THREE.Vector3(0, .02, .29)), .88);
        cells.push({ b, t, d, mesh, label });
      }
    }
    for (let d = 0; d < 2; d++) addLabel(`D${d}`, locationFor(b, 2, d).add(new THREE.Vector3(0, -.60, .25)), .65);
  }
  const start = new THREE.Vector3(-1.6, -1.72, -1.95);
  for (const [end, title, color] of [[new THREE.Vector3(1.85, -1.72, -1.95), 'D', '#3267a4'], [new THREE.Vector3(-1.6, 1.85, -1.95), 'T', '#8056a5'], [new THREE.Vector3(-1.6, -1.72, 2.15), 'B', '#187b79']]) {
    const arrow = new THREE.ArrowHelper(end.clone().sub(start).normalize(), start, end.distanceTo(start), color, .16, .10); scene.add(arrow);
    addLabel(title, end.clone().add(new THREE.Vector3(.13, .13, 0)), .65);
  }
  selectedOutline = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(.82, .82, .45)), new THREE.LineBasicMaterial({ color: dark ? '#f1f5fc' : '#233448', depthTest: false }));
  selectedOutline.renderOrder = 9; scene.add(selectedOutline);
  const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2(); let down;
  canvas.addEventListener('pointerdown', event => { down = [event.clientX, event.clientY]; });
  canvas.addEventListener('pointerup', event => {
    if (!down || Math.hypot(event.clientX - down[0], event.clientY - down[1]) > 6) return;
    const bounds = canvas.getBoundingClientRect(); pointer.set((event.clientX - bounds.left) / bounds.width * 2 - 1, -(event.clientY - bounds.top) / bounds.height * 2 + 1);
    raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects(cells.map(cell => cell.mesh), false)[0];
    if (hit) { const { b, t, d } = hit.object.userData; choose(b, t, d); }
  });
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); fallback(); });
  root.dataset.renderState = 'ready'; updateScene(); resize();
} catch { fallback(); }

darkMode.addEventListener('change', applyTheme);
window.addEventListener('storage', event => { if (event.key === 'haohai-tinylm-theme') applyTheme(); });
try { if (window.parent !== window) new MutationObserver(applyTheme).observe(window.parent.document.documentElement, { attributes: true, attributeFilter: ['data-theme'] }); } catch { /* OS theme remains available. */ }
new ResizeObserver(resize).observe(viewport);
new IntersectionObserver(entries => { active = entries[0].isIntersecting; if (!active && frame) { cancelAnimationFrame(frame); frame = 0; } if (active) requestRender(); }).observe(viewport);
document.addEventListener('visibilitychange', () => { if (document.hidden && frame) { cancelAnimationFrame(frame); frame = 0; } if (!document.hidden) requestRender(); });

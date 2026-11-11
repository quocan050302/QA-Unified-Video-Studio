// three3d.js — canh 3D (Three.js) cung phong cach: nguoi que den vien sang, nha cua so sang den, suong mu, mau theo mood.
// Dung trong shot: registerShot('s010', { kind: '3d', init(T, info) {...; return { stage }}, draw(s, t, info, T) {...}, overlay(g, t, info, s) {...} })
// Don vi: met. Nguoi que cao ~1.75 m, nhin ve huong +x.
import * as THREE from 'three';
import { E, mood, hex, rng, lerp, clamp, ease, UI } from './core.js';

let R = null;              // WebGLRenderer dung chung
export function renderer(w, h) {
  if (!R) {
    const c = document.createElement('canvas');
    R = new THREE.WebGLRenderer({ canvas: c, antialias: true, preserveDrawingBuffer: true, alpha: false });
    R.outputColorSpace = THREE.SRGBColorSpace; R.toneMapping = THREE.NoToneMapping;
  }
  if (R.domElement.width !== w || R.domElement.height !== h) R.setSize(w, h, false);
  return R;
}
const col = (c) => new THREE.Color(...hex(c).map((v) => v / 255)).convertSRGBToLinear();
const lam = (c, o = {}) => new THREE.MeshLambertMaterial({ color: col(c), emissive: col(c).multiplyScalar(0.22), flatShading: true, ...o });
const basic = (c, o = {}) => new THREE.MeshBasicMaterial({ color: col(c), ...o });

function gradTex(stops) {
  const c = document.createElement('canvas'); c.width = 4; c.height = 256; const g = c.getContext('2d');
  const gr = g.createLinearGradient(0, 0, 0, 256); stops.forEach((s, i) => gr.addColorStop(i / (stops.length - 1), s)); g.fillStyle = gr; g.fillRect(0, 0, 4, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
let _glowTex = null;
function glowTex() {
  if (_glowTex) return _glowTex;
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128); _glowTex = new THREE.CanvasTexture(c); return _glowTex;
}

// ---------- san khau
export function stage(o = {}) {
  const M = mood(o.mood || 'dusk');
  const scene = new THREE.Scene();
  scene.background = gradTex(M.sky);                              // troi theo mood (tren -> duoi)
  const fogC = col(o.fogColor || M.fog);
  scene.fog = new THREE.Fog(fogC, (o.fog || [18, 90])[0], (o.fog || [18, 90])[1]);
  const camera = new THREE.PerspectiveCamera(o.fov || 38, E.W / E.H, 0.1, 600);
  scene.add(new THREE.HemisphereLight(col(M.sky[2]), col(M.floor), o.ambient ?? 1.6));
  const key = new THREE.DirectionalLight(col(M.key), o.keyIntensity ?? 2.6);
  key.position.set(...(o.keyPos || [-20, 14, -30])); scene.add(key);
  const fill = new THREE.DirectionalLight(col(M.sky[1]), 0.8); fill.position.set(15, 10, 20); scene.add(fill);
  const st = { scene, camera, M, key, add: (...objs) => { objs.forEach((x) => scene.add(x)); return objs[0]; } };
  if (o.sun !== false) { const s = sprite(M.sun, o.sunSize || 26, 0.9); s.position.set(...(o.sunPos || [-60, 8, -140])); scene.add(s); }
  return st;
}
export function render(st, w, h) {
  const r = renderer(w, h); st.camera.aspect = E.W / E.H; st.camera.updateProjectionMatrix(); r.render(st.scene, st.camera); return r.domElement;
}
export function dispose(st) { st.scene.traverse((o) => { o.geometry?.dispose?.(); if (o.material) [].concat(o.material).forEach((m) => { m.map?.dispose?.(); m.dispose?.(); }); }); }

// ---------- hinh khoi co ban
export const box = (w, h, d, c, o = {}) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), o.basic ? basic(c, o.mat) : lam(c, o.mat)); m.position.set(o.x || 0, (o.y ?? h / 2), o.z || 0); return m; };
export const cyl = (rt, rb, h, c, o = {}) => { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, o.seg || 12), lam(c, o.mat)); m.position.set(o.x || 0, (o.y ?? h / 2), o.z || 0); return m; };
export const sphere = (r, c, o = {}) => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, o.seg || 16, o.seg || 12), o.basic ? basic(c) : lam(c)); m.position.set(o.x || 0, o.y || 0, o.z || 0); return m; };
export function ground(w, d, c, o = {}) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), lam(c)); m.rotation.x = -Math.PI / 2; m.position.y = o.y || 0;
  if (o.lines) { const g = new THREE.Group(); g.add(m); for (let x = -w / 2; x <= w / 2; x += o.lines) { const l = box(0.08, 0.01, d, o.lineColor || '#c8b890', { y: (o.y || 0) + 0.01, x, basic: true, mat: { transparent: true, opacity: 0.35 } }); g.add(l); } return g; }
  return m;
}
// quang sang (sprite cong sang)
export function sprite(c, size, opacity = 0.8) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: col(c), transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  s.scale.set(size, size, 1); return s;
}
// mat phang tu phat sang (cua so, man hinh)
export function pane(w, h, c, o = {}) { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), basic(c, { transparent: o.opacity !== undefined, opacity: o.opacity ?? 1 })); m.position.set(o.x || 0, o.y || 0, o.z || 0); if (o.ry) m.rotation.y = o.ry; return m; }

// toa nha co luoi cua so sang den (texture ve bang canvas)
export function building(w, h, d, o = {}) {
  const M = mood(o.mood || 'dusk'), color = o.color || M.wall, lit = o.lit || M.practical, r = rng(o.seed || 1);
  const cols = o.cols || Math.max(2, Math.round(w / 2.4)), rows = o.rows || Math.max(2, Math.round(h / 3));
  const c = document.createElement('canvas'); c.width = 256; c.height = Math.round(256 * h / w); const g = c.getContext('2d');
  g.fillStyle = color; g.fillRect(0, 0, c.width, c.height);
  const cw = c.width / cols, rh = c.height / rows;
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) { const on = r() < (o.litChance ?? 0.45); g.fillStyle = on ? lit : '#0d0a12'; g.globalAlpha = on ? 0.75 + r() * 0.25 : 0.7; g.fillRect(i * cw + cw * 0.22, j * rh + rh * 0.25, cw * 0.56, rh * 0.5); }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const side = new THREE.MeshLambertMaterial({ map: tex, emissive: col('#ffffff'), emissiveMap: tex, emissiveIntensity: 0.55 });
  const plain = lam(color);
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), [side, side, plain, plain, side, side]);
  m.position.set(o.x || 0, h / 2, o.z || 0); if (o.ry) m.rotation.y = o.ry; return m;
}
export function lamp(o = {}) {
  const M = mood(o.mood || 'dusk'), c = o.color || M.practical, g = new THREE.Group();
  g.add(cyl(0.06, 0.08, 4.2, M.dark)); const arm = box(0.9, 0.08, 0.08, M.dark, { y: 4.15, x: 0.4 }); g.add(arm);
  const bulb = sphere(0.14, c, { x: 0.8, y: 4.05, basic: true }); g.add(bulb);
  const s = sprite(c, 3.2, 0.9); s.position.set(0.8, 4.0, 0); g.add(s);
  const pl = new THREE.PointLight(col(c), o.intensity ?? 8, 12, 1.6); pl.position.set(0.8, 3.9, 0); g.add(pl);
  const pool = new THREE.Mesh(new THREE.CircleGeometry(2.6, 32), new THREE.MeshBasicMaterial({ map: glowTex(), color: col(c), transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false }));
  pool.rotation.x = -Math.PI / 2; pool.position.set(0.8, 0.02, 0); g.add(pool);
  g.position.set(o.x || 0, 0, o.z || 0); return g;
}
export function tree(o = {}) { const M = mood(o.mood || 'dusk'), g = new THREE.Group(), s = o.s || 1; g.add(cyl(0.12 * s, 0.16 * s, 2 * s, M.dark)); [[0, 2.6, 0, 1.1], [-0.6, 2.2, 0.2, 0.8], [0.6, 2.25, -0.2, 0.85]].forEach(([x, y, z, r]) => g.add(sphere(r * s, shade3(M.dark, 0.05), { x: x * s, y: y * s, z: z * s, seg: 8 }))); g.position.set(o.x || 0, 0, o.z || 0); return g; }
const shade3 = (c, k) => { const v = hex(c).map((x) => clamp(x + k * 255, 0, 255)); return `rgb(${v.join(',')})`; };
export function car(o = {}) {
  const c = o.color || '#1a1418', g = new THREE.Group();
  g.add(box(4, 0.7, 1.8, c, { y: 0.65 })); g.add(box(2.2, 0.65, 1.6, c, { y: 1.3, x: -0.2 }));
  [[-1.3, 0.85], [1.3, 0.85], [-1.3, -0.85], [1.3, -0.85]].forEach(([x, z]) => { const w = cyl(0.35, 0.35, 0.3, '#0a080c', { y: 0.35, x, z }); w.rotation.x = Math.PI / 2; g.add(w); });
  if (o.lights !== false) { [-0.6, 0.6].forEach((z) => { const s = sprite('#ffe9b0', 1.4, 0.8); s.position.set(2.05, 0.75, z); g.add(s); const r = sprite('#ff4040', 0.8, 0.7); r.position.set(-2.05, 0.75, z); g.add(r); }); }
  g.position.set(o.x || 0, 0, o.z || 0); g.rotation.y = o.ry || 0; return g;
}
export function stars(count = 400, o = {}) {
  const r = rng(o.seed || 3), pos = []; for (let i = 0; i < count; i++) { const a = r() * Math.PI * 2, el = 0.15 + r() * 1.2, d = 300; pos.push(Math.cos(a) * Math.cos(el) * d, Math.sin(el) * d, Math.sin(a) * Math.cos(el) * d); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 1.4, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.8 }));
}
// khan dai dam dong (instanced)
export function crowd(o = {}) {
  const { rows = 6, perRow = 40, width = 40, step = 1.2, rise = 0.8, z0 = 0, color = '#15101a', seed = 4 } = o, r = rng(seed);
  const n = rows * perRow, head = new THREE.InstancedMesh(new THREE.SphereGeometry(0.22, 8, 6), lam(color), n), body = new THREE.InstancedMesh(new THREE.BoxGeometry(0.5, 0.7, 0.35), lam(color), n);
  const m = new THREE.Matrix4(); let k = 0;
  for (let j = 0; j < rows; j++) for (let i = 0; i < perRow; i++) { const x = -width / 2 + (i + r() * 0.5) * (width / perRow), y = j * rise, z = z0 + j * step; m.makeTranslation(x, y + 1.25, z); head.setMatrixAt(k, m); m.makeTranslation(x, y + 0.75, z); body.setMatrixAt(k, m); k++; }
  const g = new THREE.Group(); g.add(head, body); return g;
}

// ---------- nguoi que 3D
const PO = {
  stand: { lA: [0.05, -0.05], rA: [-0.05, 0.05], lL: [0, 0.03], rL: [0, -0.03] },
  wave: { lA: [0.05, -0.05], rA: [2.6, 0.2], lL: [0, 0.03], rL: [0, -0.03] },
  cheer: { lA: [2.8, -0.3], rA: [2.8, 0.3], lL: [0, 0.05], rL: [0, -0.05] },
  point: { lA: [0.05, -0.05], rA: [1.5, 0.1], lL: [0, 0.03], rL: [0, -0.03] },
};
// arms/legs: [goc nang ra truoc (rad), goc dang ngang]
export function figure(outfit = {}, o = {}) {
  const M = mood(o.mood || 'dusk'), ink = UI.ink, s = (o.s || 1) * (outfit.kid ? 0.72 : 1), grp = new THREE.Group();
  const rimC = o.rim || M.rim, parts = [];
  const limb = (len, r, c) => { const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 8), lam(c)); m.geometry.translate(0, -len / 2, 0); return m; };
  const torsoC = outfit.top && outfit.top !== 'none' ? (outfit.top === 'labcoat' ? '#ece8e0' : outfit.color || '#d64a33') : ink;
  const hip = new THREE.Group(); hip.position.y = 0.9; grp.add(hip);
  const torso = limb(0.5, outfit.top && outfit.top !== 'none' ? 0.15 : 0.07, torsoC); torso.rotation.z = Math.PI; torso.position.y = 0.0; hip.add(torso); parts.push(torso);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 20, 16), lam(ink)); head.position.y = 0.82; hip.add(head); parts.push(head);
  // mat: 2 mat trang + mieng, quay ve +x
  const eyeM = basic('#fbf6ee'); [-0.07, 0.07].forEach((z) => { const e = new THREE.Mesh(new THREE.SphereGeometry(0.032, 8, 6), eyeM); e.scale.set(0.5, 1.3, 1); e.position.set(0.18, 0.86, z); hip.add(e); });
  const mouth = new THREE.Mesh(new THREE.TorusGeometry(0.05, 0.012, 6, 12, Math.PI), eyeM); mouth.position.set(0.185, 0.77, 0); mouth.rotation.set(0, Math.PI / 2, Math.PI); hip.add(mouth);
  if (outfit.head === 'cap' || outfit.head === 'beanie') { const hc = outfit.headColor || outfit.color; const cap = new THREE.Mesh(new THREE.SphereGeometry(0.205, 16, 10, 0, Math.PI * 2, 0, Math.PI / 2.2), lam(hc)); cap.position.y = 0.86; hip.add(cap); if (outfit.head === 'cap') { const b = box(0.2, 0.02, 0.22, hc, { y: 0.9, x: 0.2 }); hip.add(b); } }
  const arm = (side) => { const sh = new THREE.Group(); sh.position.set(0, 0.55, side * 0.2); const a = limb(0.52, outfit.top === 'hoodie' || outfit.top === 'labcoat' || outfit.top === 'tracksuit' ? 0.075 : 0.05, outfit.top === 'hoodie' || outfit.top === 'tracksuit' || outfit.top === 'labcoat' ? torsoC : ink); sh.add(a); hip.add(sh); parts.push(a); return sh; };
  const leg = (side) => { const h = new THREE.Group(); h.position.set(0, 0, side * 0.08); const l = limb(0.78, 0.06, outfit.legs || ink); h.add(l); hip.add(h); parts.push(l); return h; };
  const L = { lA: arm(-1), rA: arm(1), lL: leg(-1), rL: leg(1) };
  // vien sang: ban sao phong to mat sau, mau rim
  const rimMat = new THREE.MeshBasicMaterial({ color: col(rimC), side: THREE.BackSide, transparent: true, opacity: o.rimOpacity ?? 0.9 });
  parts.forEach((p) => { const h = new THREE.Mesh(p.geometry, rimMat); h.scale.setScalar(1.12); p.add(h); });
  const setPose = (name, t = 0) => {
    let P = PO[name] || PO.stand;
    if (name === 'walk' || name === 'run') { const k = name === 'run' ? 1 : 0.5, ph = t * Math.PI * 2 * (name === 'run' ? 1.5 : 0.9), sw = Math.sin(ph) * k; P = { lA: [-sw, -0.05], rA: [sw, 0.05], lL: [sw, 0.03], rL: [-sw, -0.03] }; hip.position.y = 0.9 + Math.abs(Math.cos(ph)) * 0.04 * k; }
    for (const k of Object.keys(L)) { L[k].rotation.z = P[k][0]; L[k].rotation.x = P[k][1] + (k === 'lA' ? 0.18 : k === 'rA' ? -0.18 : 0); }
  };
  setPose(o.pose || 'stand');
  grp.scale.setScalar(s); grp.position.set(o.x || 0, 0, o.z || 0); grp.rotation.y = o.ry || 0;
  grp.userData.setPose = setPose;
  // bong tiep dat
  const sh = new THREE.Mesh(new THREE.CircleGeometry(0.45, 20), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.35, depthWrite: false })); sh.rotation.x = -Math.PI / 2; sh.position.y = 0.01; grp.add(sh);
  return grp;
}

// ---------- may quay
// xoay quanh diem target: goc tu `from` den `to` (rad) trong `dur` giay
export function orbit(cam, t, o = {}) {
  const { target = [0, 1, 0], radius = 8, height = 2.5, from = -0.6, to = 0.4, dur = 4, lift = 0 } = o;
  const k = ease.inOut(clamp(t / dur)), a = lerp(from, to, k);
  cam.position.set(target[0] + Math.cos(a) * radius, target[1] + height + lift * k, target[2] + Math.sin(a) * radius); cam.lookAt(...target);
}
// bay theo keyframe: [[t, {pos:[x,y,z], look:[x,y,z], fov}], ...]
export function dolly(cam, t, keys) {
  let a = keys[0], b = keys[keys.length - 1];
  for (let i = 1; i < keys.length; i++) if (t <= keys[i][0]) { a = keys[i - 1]; b = keys[i]; break; }
  const k = ease.inOut(clamp((t - a[0]) / Math.max(1e-6, b[0] - a[0])));
  const L = (p, q) => p.map((v, i) => lerp(v, q[i], k));
  cam.position.set(...L(a[1].pos, b[1].pos)); cam.lookAt(...L(a[1].look, b[1].look));
  if (a[1].fov) { cam.fov = lerp(a[1].fov, b[1].fov ?? a[1].fov, k); cam.updateProjectionMatrix(); }
}
export { THREE };

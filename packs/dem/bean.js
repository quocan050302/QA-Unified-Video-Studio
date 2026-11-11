// bean.js — nhan vat dau tron mau kem (nguoi hung, ban be, co gai) va "giong noi" (bong den phat sang).
//   bean(g, x, yChan, chieuCao, o)
// o: who (preset trong CAST) | pose | face | facing (1 nhin phai, -1 nhin trai) | look (-1..1 lech mat) | t (giay, cho chop mat / tho)
//    walk / run (toc do chu ky, 0 = dung) | rot (nghieng ca nguoi, rad) | hold: 'phone' | 'umbrella' | 'book' | 'ball' | 'bag'
//    headband | hood | cap (mau) | hair: 'bob' | scarf (mau) | shirt (mau than) | tears | sweat | bags (quang tham) | glowFace (mau anh man hinh hat len mat)
//    shadow: true -> ve thanh bong den "giong noi" (dung preset 'voice')
import { E, clamp, lerp, ease, noise, rng, alpha, shade, radGrad } from '/engine/core.js';
import { PAL, accent, light } from './ink.js';

export const CAST = {
  hero:    { skin: PAL.hero },
  band:    { skin: PAL.hero, headband: true },                         // nguoi hung khi tap luyen (bang do mau nhan)
  hoodie:  { skin: PAL.hero, hood: true },                             // nguoi hung mac hoodie (mu ha xuong sau co, dau tron tron nhu doi thu)
  hooded:  { skin: PAL.hero, hood: 'up' },                             // hoodie trum mu len dau (canh dem, nghien)
  friend:  { skin: PAL.friend1, cap: PAL.capY },
  friend2: { skin: PAL.friend2, cap: PAL.capB },
  friend3: { skin: PAL.friend1, cap: PAL.capR },
  girl:    { skin: PAL.girlSkin, hair: 'bob', scarf: PAL.scarf, shirt: PAL.coat },
  mom:     { skin: PAL.friend1, hair: 'bun', shirt: '#7b6a8a' },
  dad:     { skin: PAL.friend2, glasses: true, shirt: '#4d5a6e' },
  kid:     { skin: PAL.hero, kid: true },
  ghost:   { skin: PAL.hero, ghost: true },                            // ban cu mo nhat (hoi tuong)
  voice:   { shadow: true },                                           // "giong noi" — cam do
};

// tu the: goc tuyet doi (rad) cua [canh tay, cang tay] / [dui, cang chan]; 0 = thang xuong, + = ve phia mat nhin.
// F = tay/chan gan (phia truoc), B = phia sau. lean = nghieng than, drop = ha hong (ngoi), head = [dx, dy] dau lech
export const POSES = {
  stand:    { aF: [0.1, 0.05], aB: [-0.1, -0.05], lF: [0.02, 0], lB: [-0.02, 0] },
  relaxed:  { aF: [0.18, 0.3], aB: [-0.15, -0.05], lF: [0.08, 0], lB: [-0.06, 0] },
  slump:    { aF: [0.25, 0.2], aB: [0.15, 0.1], lF: [0.04, 0], lB: [-0.02, 0], lean: 0.14, head: [3, 4] },
  phone:    { aF: [0.55, 2.5], aB: [0.35, 2.2], lF: [0.03, 0], lB: [-0.03, 0], head: [1, 2], lean: 0.05, hand: 'front' },
  reach:    { aF: [1.35, 1.45], aB: [-0.1, -0.05], lF: [0.05, 0], lB: [-0.05, 0], lean: 0.1 },
  point:    { aF: [1.45, 1.5], aB: [-0.1, -0.05], lF: [0.02, 0], lB: [-0.02, 0] },
  wave:     { aF: [2.4, 2.9], aB: [-0.1, -0.05], lF: [0.02, 0], lB: [-0.02, 0] },
  cheer:    { aF: [2.7, 2.95], aB: [-2.7, -2.95], lF: [0.1, 0], lB: [-0.1, 0] },
  fist:     { aF: [0.35, 2.6], aB: [-0.1, -0.05], lF: [0.05, 0], lB: [-0.05, 0] },
  headhold: { aF: [2.1, -2.6], aB: [-2.1, 2.6], lF: [0.03, 0], lB: [-0.03, 0], head: [0, 3] },
  facepalm: { aF: [0.9, 2.9], aB: [-0.1, -0.05], lF: [0.02, 0], lB: [-0.02, 0], head: [2, 4], lean: 0.08 },
  arms:     { aF: [0.6, -1.3], aB: [-0.6, 1.3], lF: [0.04, 0], lB: [-0.04, 0] },          // khoanh tay
  shrug:    { aF: [0.7, 2.0], aB: [-0.7, -2.0], lF: [0.04, 0], lB: [-0.04, 0] },
  hug:      { aF: [0.5, 1.9], aB: [0.4, 1.7], lF: [0.04, 0], lB: [-0.04, 0], lean: 0.06 },  // om nguoi / om gang tay
  guard:    { aF: [0.6, 2.7], aB: [0.4, 2.5], lF: [0.35, -0.1], lB: [-0.35, 0.05], lean: 0.08, drop: 4 },   // the dam boc
  punch:    { aF: [1.55, 1.55], aB: [0.4, 2.5], lF: [0.35, -0.1], lB: [-0.35, 0.05], lean: 0.18, drop: 4 },
  lift:     { aF: [2.95, 3.1], aB: [-2.95, -3.1], lF: [0.25, 0], lB: [-0.25, 0], drop: 3 },                // nang ta qua dau
  sit:      { aF: [0.35, 1.3], aB: [0.2, 1.2], lF: [1.5, 0.05], lB: [1.45, 0.0], drop: 15, lean: -0.05 },  // ngoi ghe / mep giuong
  sitphone: { aF: [0.6, 2.5], aB: [0.4, 2.3], lF: [1.5, 0.05], lB: [1.45, 0], drop: 15, lean: 0.12, head: [2, 3] },
  sitdesk:  { aF: [1.0, 1.55], aB: [0.9, 1.5], lF: [1.5, 0.05], lB: [1.45, 0], drop: 15, lean: 0.22 },     // cui viet / doc
  sitsad:   { aF: [0.5, 1.5], aB: [0.4, 1.4], lF: [1.5, 0.05], lB: [1.45, 0], drop: 15, lean: 0.3, head: [3, 6] },
  knees:    { aF: [0.9, 1.8], aB: [0.8, 1.7], lF: [2.3, -0.15], lB: [2.2, -0.2], drop: 26, lean: 0.25, head: [3, 4] },   // ngoi bo goi duoi dat
  kneel:    { aF: [0.3, 0.2], aB: [0.1, 0.1], lF: [1.4, -0.1], lB: [0.0, -1.5], drop: 13, lean: 0.15, head: [2, 4] },
  crouch:   { aF: [0.9, 1.6], aB: [0.7, 1.5], lF: [1.6, -0.3], lB: [1.2, -0.6], drop: 12, lean: 0.35 },
  climb:    { aF: [0.6, 1.4], aB: [-0.5, -0.2], lF: [1.0, 0.1], lB: [-0.3, 0.0], lean: 0.2, drop: 3 },
  open:     { aF: [1.3, 1.25], aB: [-0.1, -0.05], lF: [0.25, 0], lB: [-0.2, 0], lean: 0.12 },     // day cua
  umbrella: { aF: [0.55, 2.55], aB: [-0.1, -0.05], lF: [0.02, 0], lB: [-0.02, 0], hand: 'front' },
  carry:    { aF: [0.5, 1.6], aB: [0.4, 1.5], lF: [0.03, 0], lB: [-0.03, 0] },             // om do vat truoc nguc
};

const lerpPose = (a, b, k) => {
  const L = (x, y) => (Array.isArray(x) ? x.map((v, i) => lerp(v, y[i], k)) : lerp(x ?? 0, y ?? 0, k));
  const o = {}; for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) { if (key === 'hand') { o.hand = k < 0.5 ? a.hand : b.hand; continue; } o[key] = L(a[key] ?? (Array.isArray(b[key]) ? b[key].map(() => 0) : 0), b[key] ?? (Array.isArray(a[key]) ? a[key].map(() => 0) : 0)); }
  return o;
};
export function poseOf(name, from, k) { const p = POSES[name] || (typeof name === 'object' ? name : POSES.stand); return from ? lerpPose(POSES[from] || from, p, k) : p; }

// chu ky di / chay
function gait(p, t, speed, run) {
  const ph = t * speed * Math.PI * 2, s = Math.sin(ph), c = Math.cos(ph), amp = run ? 0.75 : 0.42;
  const bend = run ? 1.1 : 0.5;
  return { ...p, lF: [s * amp, s * amp - Math.max(0, -c) * bend], lB: [-s * amp, -s * amp - Math.max(0, c) * bend],
    aF: [-s * (run ? 0.7 : 0.35), -s * (run ? 0.7 : 0.35) + (run ? 1.5 : 0.25)], aB: [s * (run ? 0.7 : 0.35), s * (run ? 0.7 : 0.35) + (run ? 1.5 : 0.25)],
    lean: (p.lean || 0) + (run ? 0.18 : 0.03), bounce: Math.abs(s) * (run ? 2.2 : 1.1) };
}

const seg2 = (x, y, a1, l1, a2, l2, f) => { const ex = x + Math.sin(a1) * l1 * f, ey = y + Math.cos(a1) * l1; return [[x, y], [ex, ey], [ex + Math.sin(a2) * l2 * f, ey + Math.cos(a2) * l2]]; };
function limb(g, pts, w, fill, edge, lw) {
  g.lineCap = 'round'; g.lineJoin = 'round';
  const path = () => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); g.quadraticCurveTo(pts[1][0], pts[1][1], (pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2); g.lineTo(pts[2][0], pts[2][1]); };
  if (edge) { path(); g.lineWidth = w + lw * 2; g.strokeStyle = edge; g.stroke(); }
  path(); g.lineWidth = w; g.strokeStyle = fill; g.stroke();
}
function dot(g, x, y, r, fill, edge, lw) { g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fillStyle = fill; g.fill(); if (edge) { g.lineWidth = lw; g.strokeStyle = edge; g.stroke(); } }

export function bean(g, x, y, h, o = {}) {
  const pre = CAST[o.who] || {}; o = { ...pre, ...o };
  const U = h / 100, f = o.facing ?? 1, t = o.t || 0, sh = !!o.shadow;
  const skin = sh ? '#050507' : (o.skin || PAL.hero), edge = sh ? alpha(o.glow || accent(), 0.85) : (o.edge || PAL.heroLine), lw = sh ? Math.max(1.2, 0.9 * U) : Math.max(1.6, 2.2 * U / 2.4);
  const glowC = o.glow || (sh ? accent() : null);
  let p = poseOf(o.pose || 'stand', o.fromPose, o.poseK ?? 1);
  if (o.walk || o.run) p = gait(p, t, o.walk || o.run, !!o.run);
  const breathe = Math.sin(t * 2.1 + (o.seed || 0)) * 0.6 * U;
  const drop = (p.drop || 0) * U - (p.bounce || 0) * U * -1 * 0, bounce = (p.bounce || 0) * U;
  g.save(); g.translate(x, y);
  if (o.rot) g.rotate(o.rot);
  if (o.scale) g.scale(o.scale, o.scale);
  if (sh && glowC) { // vong sang duoi chan + vien phat sang
    g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = radGrad(g, 0, 0, 0, 30 * U, [[0, alpha(glowC, 0.25)], [1, alpha(glowC, 0)]]); g.scale(1, 0.22); g.beginPath(); g.arc(0, 0, 30 * U, 0, Math.PI * 2); g.fill(); g.restore();
    g.save(); g.strokeStyle = glowC; g.lineWidth = 1.6 * U; g.shadowColor = glowC; g.shadowBlur = 8 * U; g.beginPath(); g.ellipse(0, 0, 20 * U, 4.2 * U, 0, 0, Math.PI * 2); g.stroke(); g.restore();
  }
  const hipY = -30 * U + drop - bounce, lean = p.lean || 0;
  const neck = [Math.sin(lean) * 32 * U * f, hipY - Math.cos(lean) * 32 * U];
  const sx = (k) => neck[0] + (k * 9 * U) * Math.cos(lean), shY = neck[1] + 3 * U + breathe * 0.4;
  const hx = neck[0] + ((p.head?.[0] || 0) + Math.sin(lean) * 14) * U * f, hy = neck[1] - 15 * U + (p.head?.[1] || 0) * U + breathe * 0.5;
  const R = (o.kid ? 16.5 : 18.5) * U;
  const legW = 8 * U, armW = 6.4 * U;
  const hipF = [2.5 * U * f, hipY], hipB = [-2.5 * U * f, hipY];
  // chan: [goc dui, goc cang chan] tuyet doi
  const leg = (side, ang) => seg2(side[0], side[1], ang[0], 15 * U, ang[1] ?? ang[0], 15.5 * U, f);
  const arm = (k, ang) => seg2(sx(k), shY, ang[0], 12.5 * U, ang[1], 12 * U, f);
  const pal = { skin, edge, lw };
  const glowSil = (fn) => { if (sh && glowC) { g.save(); g.shadowColor = glowC; g.shadowBlur = 26 * U; fn(); g.restore(); } fn(); };
  const drawArm = (pts, front) => { limb(g, pts, armW, skin, edge, lw); const hd = pts[2]; dot(g, hd[0], hd[1], 4.2 * U, skin, edge, lw); if (front && o.hold && o.hold !== 'none') holdItem(g, hd[0], hd[1], U, f, o.hold, t, o); };
  const aB = arm(-1 * f, p.aB || [0, 0]), aF = arm(1 * f, p.aF || [0, 0]);
  glowSil(() => {
    // tay sau, chan
    drawArm(aB, false);
    const lb = leg(hipB, p.lB || [0, 0]), lf = leg(hipF, p.lF || [0, 0]);
    limb(g, lb, legW, sh ? skin : shade(skin, -0.05), edge, lw); limb(g, lf, legW, skin, edge, lw);
    if (o.shoes) for (const L of [lb, lf]) { g.beginPath(); g.ellipse(L[2][0] + 2 * U * f, L[2][1] - 1 * U, 5 * U, 2.6 * U, 0, 0, Math.PI * 2); g.fillStyle = o.shoes; g.fill(); }
    // than (bao tron)
    const tw = 12.5 * U, bw = 14 * U;
    g.save(); g.translate(neck[0], neck[1]); g.rotate(lean * f);
    g.beginPath(); g.moveTo(-tw, 2 * U); g.bezierCurveTo(-tw - 1 * U, 14 * U, -bw - 1 * U, 26 * U, -bw + 2 * U, 31 * U); g.quadraticCurveTo(0, 34 * U, bw - 2 * U, 31 * U); g.bezierCurveTo(bw + 1 * U, 26 * U, tw + 1 * U, 14 * U, tw, 2 * U); g.quadraticCurveTo(0, -3 * U, -tw, 2 * U); g.closePath();
    g.fillStyle = sh ? skin : (o.hood ? PAL.hood : o.shirt || skin); g.fill(); if (edge) { g.lineWidth = lw; g.strokeStyle = o.hood || o.shirt ? shade(o.hood ? PAL.hood : o.shirt, -0.35) : edge; g.stroke(); }
    if (!sh && !o.hood && !o.shirt) { g.save(); g.clip(); g.fillStyle = alpha(PAL.heroShade, 0.55); g.fillRect(-bw * f * 1.0 - (f > 0 ? 0 : 0), -5 * U, bw * 0.7 * -f, 40 * U); g.restore(); }
    if (o.hood) { g.beginPath(); g.moveTo(-3 * U, 6 * U); g.lineTo(-3 * U, 12 * U); g.moveTo(3 * U, 6 * U); g.lineTo(3 * U, 12 * U); g.lineWidth = 0.9 * U; g.strokeStyle = '#2e3036'; g.stroke(); g.beginPath(); g.roundRect(-8 * U, 20 * U, 16 * U, 7 * U, 2 * U); g.strokeStyle = '#44474e'; g.stroke(); }
    if (o.hood && o.hood !== 'up') { g.beginPath(); g.ellipse(-1.5 * U * f, 1.5 * U, tw * 0.95, 5.2 * U, 0, 0, Math.PI * 2); g.fillStyle = PAL.hoodDark; g.fill(); g.lineWidth = lw; g.strokeStyle = '#2e3036'; g.stroke(); }
    if (o.scarf) { g.beginPath(); g.roundRect(-tw - 1 * U, -1 * U, tw * 2 + 2 * U, 6 * U, 3 * U); g.fillStyle = o.scarf; g.fill(); g.beginPath(); g.roundRect(3 * U * f, 3 * U, 5 * U, 12 * U, 2 * U); g.fill(); }
    g.restore();
    // dau
    head(g, hx, hy, R, { ...o, U, f, t, pal });
    // tay truoc
    drawArm(aF, true);
  });
  // anh sang man hinh hat len mat
  if (o.glowFace) light(g, hx + 10 * U * f, hy + 6 * U, R * 2.4, o.glowFace, 0.32);
  g.restore();
  return { head: [x + hx, y + hy], R, hand: [x + aF[2][0], y + aF[2][1]], handB: [x + aB[2][0], y + aB[2][1]] };
}

// ---------- dau + mat
export const FACES = ['neutral', 'tired', 'sleepy', 'sleep', 'sad', 'cry', 'worried', 'scared', 'shock', 'angry', 'determined', 'effort', 'smile', 'happy', 'smirk', 'empty', 'guilty', 'bloodshot', 'haunted', 'grin'];
export function head(g, x, y, R, o = {}) {
  const U = o.U || R / 17, f = o.f ?? o.facing ?? 1, t = o.t || 0, sh = !!o.shadow, pal = o.pal || { skin: o.skin || PAL.hero, edge: PAL.heroLine, lw: 2 };
  const look = (o.look ?? 0.25) * f;
  // mu trum (sau dau)
  if (o.hood === 'up') { g.beginPath(); g.ellipse(x - 1.5 * U * f, y + 1 * U, R * 1.28, R * 1.22, 0, 0, Math.PI * 2); g.fillStyle = PAL.hood; g.fill(); g.lineWidth = pal.lw; g.strokeStyle = PAL.hoodDark; g.stroke(); }
  if (o.hair === 'bob' && !sh) { g.beginPath(); g.ellipse(x, y + 1 * U, R * 1.12, R * 1.08, 0, Math.PI * 0.92, Math.PI * 2.08); g.lineTo(x + R * 1.12, y + R * 0.75); g.lineTo(x - R * 1.12, y + R * 0.75); g.closePath(); g.fillStyle = PAL.hair; g.fill(); }
  if (o.hair === 'bun' && !sh) { dot(g, x - 2 * U * f, y - R * 1.05, R * 0.38, '#5a4a40'); }
  g.beginPath(); g.arc(x, y, R, 0, Math.PI * 2); g.fillStyle = pal.skin; g.fill();
  if (pal.edge) { g.lineWidth = pal.lw; g.strokeStyle = pal.edge; g.stroke(); }
  if (!sh) { // bong mem nua sau
    g.save(); g.beginPath(); g.arc(x, y, R - pal.lw / 2, 0, Math.PI * 2); g.clip(); g.fillStyle = alpha(PAL.heroShade, 0.38); g.beginPath(); g.arc(x + R * 0.28 * f, y - R * 0.05, R * 1.02, 0, Math.PI * 2); g.rect(x - R * 2, y - R * 2, R * 4, R * 4); g.fill('evenodd'); g.restore();
  }
  if (o.hood === 'up') { g.beginPath(); g.arc(x - 1.5 * U * f, y + 1 * U, R * 1.16, Math.PI * (f > 0 ? 0.55 : 0.45) - 0.0, Math.PI * (f > 0 ? 0.55 : 0.45) + 0.001); g.save(); g.beginPath(); g.ellipse(x - 1.5 * U * f, y + 1 * U, R * 1.28, R * 1.22, 0, 0, Math.PI * 2); g.ellipse(x + 0.5 * U * f, y + 0.5 * U, R * 1.0, R * 1.02, 0, 0, Math.PI * 2); g.fillStyle = PAL.hood; g.fill('evenodd'); g.restore(); }
  if (o.hood === 'up' && !sh) { g.save(); g.beginPath(); g.arc(x, y, R - pal.lw / 2, 0, Math.PI * 2); g.clip(); g.beginPath(); g.ellipse(x - 2 * U * f, y - R * 1.05, R * 1.25, R * 0.55, 0, 0, Math.PI * 2); g.fillStyle = PAL.hood; g.fill(); g.lineWidth = 1.4 * U; g.strokeStyle = PAL.hoodDark; g.stroke(); g.restore(); }
  if (o.hair === 'bob' && !sh) { g.beginPath(); g.ellipse(x, y - R * 0.18, R * 1.02, R * 0.78, 0, Math.PI, Math.PI * 2); g.lineTo(x + R * 1.0, y - R * 0.12); g.quadraticCurveTo(x, y - R * 0.32, x - R * 1.0, y - R * 0.12); g.closePath(); g.fillStyle = PAL.hair; g.fill(); }
  if (o.cap && !sh) { g.beginPath(); g.ellipse(x, y - R * 0.3, R * 1.02, R * 0.85, 0, Math.PI, Math.PI * 2); g.closePath(); g.fillStyle = o.cap; g.fill(); g.beginPath(); g.ellipse(x + R * 0.75 * f, y - R * 0.32, R * 0.62, R * 0.14, 0, 0, Math.PI * 2); g.fill(); g.lineWidth = 1.2 * U; g.strokeStyle = shade(o.cap, -0.35); g.stroke(); }
  if (o.headband && !sh) { const c = o.bandColor || accent(); g.save(); g.beginPath(); g.arc(x, y, R - pal.lw / 2, 0, Math.PI * 2); g.clip(); g.fillStyle = c; g.fillRect(x - R, y - R * 0.62, R * 2, R * 0.28); g.restore(); g.fillStyle = c; g.beginPath(); g.moveTo(x - R * 0.95 * f, y - R * 0.5); g.quadraticCurveTo(x - R * 1.45 * f, y - R * 0.6 + Math.sin(t * 9) * 3 * U, x - R * 1.7 * f, y - R * 0.25 + Math.sin(t * 9 + 1) * 3 * U); g.lineTo(x - R * 1.62 * f, y - R * 0.12); g.quadraticCurveTo(x - R * 1.35 * f, y - R * 0.35, x - R * 0.95 * f, y - R * 0.33); g.closePath(); g.fill(); }
  if (o.glasses && !sh) { g.lineWidth = 1.4 * U; g.strokeStyle = '#2a2a2e'; for (const k of [-1, 1]) { g.beginPath(); g.arc(x + (k * 0.42 + look * 0.3) * R, y - R * 0.02, R * 0.22, 0, Math.PI * 2); g.stroke(); } }
  face(g, x, y, R, o.face || 'neutral', { ...o, look, U, f, t, sh });
}

function face(g, x, y, R, name, o) {
  const { U, t, sh } = o, look = o.look;
  const ex = (k) => x + (k * 0.38 + look * 0.32) * R, ey = y - R * 0.02, er = R * 0.2;
  const ink = sh ? null : '#2a2826', line = sh ? (o.glow || accent()) : '#4a463f';
  const blinkCycle = (t + (o.seed || 0) * 1.3) % 3.7, blink = !sh && blinkCycle < 0.12 ? 1 : 0;
  const F = {
    neutral: { lid: 0.12, brow: 0 }, tired: { lid: 0.5, brow: -0.05, bags: 1 }, sleepy: { lid: 0.75, brow: 0 }, sleep: { lid: 1, brow: 0, mouth: 'flat' },
    sad: { lid: 0.35, brow: -0.35, mouth: 'frown' }, cry: { lid: 0.3, brow: -0.45, mouth: 'wobble', tears: 1 }, worried: { lid: 0.1, brow: -0.3, mouth: 'flat', sweat: 1 },
    scared: { lid: 0, brow: -0.45, mouth: 'wobble', sweat: 1, small: 1 }, shock: { lid: 0, brow: -0.2, mouth: 'o', small: 1 }, angry: { lid: 0.3, brow: 0.5, mouth: 'frown' },
    determined: { lid: 0.32, brow: 0.42, mouth: 'flat' }, effort: { lid: 0.4, brow: 0.55, mouth: 'teeth', sweat: 1 }, smile: { lid: 0.15, brow: -0.05, mouth: 'smile' },
    happy: { lid: 0, brow: -0.1, mouth: 'open', eyes: 'arc' }, smirk: { lid: 0.35, brow: 0.2, mouth: 'smirk' }, empty: { lid: 0.45, brow: 0, mouth: 'flat', bags: 1, dead: 1 },
    guilty: { lid: 0.4, brow: -0.35, mouth: 'flat', look: -0.6 }, bloodshot: { lid: 0.05, brow: -0.25, mouth: 'frown', blood: 1, small: 1 }, haunted: { lid: 0.3, brow: -0.2, mouth: 'flat', blood: 1 }, grin: { mouth: 'grin', eyes: 'slit' },
  }[name] || { lid: 0.12 };
  if (sh || name === 'grin') { // bong den: mat la vet sang cong, mieng cuoi rong
    g.save(); g.strokeStyle = line; g.shadowColor = line; g.shadowBlur = 10 * U; g.lineWidth = 2.6 * U; g.lineCap = 'round';
    for (const k of [-1, 1]) { g.beginPath(); g.moveTo(ex(k) - er * 1.0, ey - er * 0.1 + k * 0); g.quadraticCurveTo(ex(k), ey - er * (sh && name === 'angry' ? -0.6 : 0.9), ex(k) + er * 1.0, ey + er * 0.1); g.stroke(); }
    if (name !== 'sad') { g.beginPath(); g.moveTo(x - R * 0.42 + look * R * 0.25, y + R * 0.36); g.quadraticCurveTo(x + look * R * 0.25, y + R * 0.78, x + R * 0.42 + look * R * 0.25, y + R * 0.36); g.stroke(); }
    else { g.beginPath(); g.moveTo(x - R * 0.3, y + R * 0.55); g.quadraticCurveTo(x, y + R * 0.38, x + R * 0.3, y + R * 0.55); g.stroke(); }
    g.restore(); return;
  }
  const lid = Math.max(F.lid || 0, blink), lk = (F.look ?? 0) * R * 0.08;
  for (const k of [-1, 1]) {
    const cx = ex(k), cy = ey;
    if (F.bags) { g.beginPath(); g.ellipse(cx, cy + er * 0.55, er * 1.1, er * 0.75, 0, 0, Math.PI); g.fillStyle = 'rgba(110,80,110,0.35)'; g.fill(); }
    if (F.eyes === 'arc') { g.beginPath(); g.arc(cx, cy + er * 0.3, er * 0.75, Math.PI * 1.1, Math.PI * 1.9); g.lineWidth = 2 * U; g.strokeStyle = ink; g.stroke(); continue; }
    if (lid >= 0.98) { g.beginPath(); g.moveTo(cx - er * 0.9, cy + er * 0.2); g.quadraticCurveTo(cx, cy + er * 0.7, cx + er * 0.9, cy + er * 0.2); g.lineWidth = 1.8 * U; g.strokeStyle = ink; g.stroke(); continue; }
    const blood = F.blood || o.bloodshot;
    if (blood && !F.bags) { g.beginPath(); g.ellipse(cx, cy + er * 0.55, er * 1.15, er * 0.8, 0, 0, Math.PI); g.fillStyle = 'rgba(70,40,55,0.45)'; g.fill(); }
    g.beginPath(); g.ellipse(cx, cy, er, er * 1.05, 0, 0, Math.PI * 2); g.fillStyle = blood ? '#f6d4d4' : '#ffffff'; g.fill(); g.lineWidth = 1.2 * U; g.strokeStyle = '#6d685e'; g.stroke();
    if (F.bags || F.dead || blood) { g.save(); g.beginPath(); g.ellipse(cx, cy, er, er * 1.05, 0, 0, Math.PI * 2); g.clip(); g.strokeStyle = blood ? 'rgba(200,55,65,0.75)' : 'rgba(220,90,90,0.5)'; g.lineWidth = (blood ? 0.55 : 0.8) * U; for (const sd of blood ? [-1, 1] : [-1]) for (let i = 0; i < (blood ? 4 : 3); i++) { const yy = cy + (i - 1.5) * er * 0.38; g.beginPath(); g.moveTo(cx + sd * er, yy); g.quadraticCurveTo(cx + sd * er * 0.72, yy + er * 0.12 * (i % 2 ? 1 : -1), cx + sd * er * 0.5, yy + er * 0.05); g.stroke(); } g.restore(); }
    const pr = er * (F.small ? 0.32 : 0.48);
    dot(g, cx + look * er * 0.45 + lk, cy + er * 0.12, pr, '#1e1c1b');
    if (!F.dead) dot(g, cx + look * er * 0.45 + lk + pr * 0.35, cy + er * 0.12 - pr * 0.35, pr * 0.3, '#ffffff');
    if (lid > 0.02) { g.save(); g.beginPath(); g.ellipse(cx, cy, er + 0.6, er * 1.05 + 0.6, 0, 0, Math.PI * 2); g.clip(); g.fillStyle = o.pal?.skin || PAL.hero; g.fillRect(cx - er - 2, cy - er * 1.1 - 1, er * 2 + 4, er * 2.1 * lid + 1); g.beginPath(); g.moveTo(cx - er, cy - er * 1.05 + er * 2.1 * lid); g.lineTo(cx + er, cy - er * 1.05 + er * 2.1 * lid); g.lineWidth = 1.5 * U; g.strokeStyle = '#6d685e'; g.stroke(); g.restore(); }
    // long may: b > 0 = cau (dau trong cup xuong), b < 0 = buon (dau trong nhuong len)
    const b = F.brow || 0, by = cy - er * 1.55, inner = cx - k * er * 0.85, outer = cx + k * er * 0.9;
    g.beginPath(); g.moveTo(outer, by - b * er * 0.45); g.lineTo(inner, by + b * er * 0.9);
    g.lineWidth = 1.7 * U; g.strokeStyle = '#3d3a35'; g.lineCap = 'round'; g.stroke();
  }
  // mieng
  const mx = x + look * R * 0.28, my = y + R * 0.47, mw = R * 0.22;
  g.lineWidth = 1.9 * U; g.strokeStyle = '#3d3a35'; g.lineCap = 'round';
  const m = F.mouth || 'flat';
  if (m === 'flat') { g.beginPath(); g.moveTo(mx - mw * 0.8, my); g.lineTo(mx + mw * 0.8, my); g.stroke(); }
  if (m === 'frown') { g.beginPath(); g.moveTo(mx - mw, my + mw * 0.35); g.quadraticCurveTo(mx, my - mw * 0.45, mx + mw, my + mw * 0.35); g.stroke(); }
  if (m === 'smile') { g.beginPath(); g.moveTo(mx - mw, my - mw * 0.15); g.quadraticCurveTo(mx, my + mw * 0.65, mx + mw, my - mw * 0.15); g.stroke(); }
  if (m === 'smirk') { g.beginPath(); g.moveTo(mx - mw * 0.8, my + mw * 0.1); g.quadraticCurveTo(mx + mw * 0.3, my + mw * 0.25, mx + mw, my - mw * 0.35); g.stroke(); }
  if (m === 'o') { g.beginPath(); g.ellipse(mx, my + mw * 0.2, mw * 0.45, mw * 0.6, 0, 0, Math.PI * 2); g.fillStyle = '#4a2f2c'; g.fill(); }
  if (m === 'open') { g.beginPath(); g.moveTo(mx - mw, my - mw * 0.1); g.quadraticCurveTo(mx, my + mw * 1.2, mx + mw, my - mw * 0.1); g.closePath(); g.fillStyle = '#5a3430'; g.fill(); }
  if (m === 'teeth') { g.beginPath(); g.roundRect(mx - mw * 1.1, my - mw * 0.35, mw * 2.2, mw * 0.8, mw * 0.25); g.fillStyle = '#ffffff'; g.fill(); g.stroke(); g.beginPath(); g.moveTo(mx - mw * 1.1, my + mw * 0.05); g.lineTo(mx + mw * 1.1, my + mw * 0.05); g.lineWidth = 1 * U; g.stroke(); }
  if (m === 'wobble') { g.beginPath(); g.moveTo(mx - mw, my + mw * 0.2); for (let i = 1; i <= 6; i++) g.lineTo(mx - mw + (i / 6) * mw * 2, my + mw * 0.2 + (i % 2 ? -1 : 1) * mw * 0.18); g.stroke(); }
  if (F.tears || o.tears) for (const k of [-1, 1]) { const tx = ex(k) + k * er * 0.2, ty = ey + er * 1.2 + ((t * 0.9 + k * 0.3) % 1) * R * 0.5; g.beginPath(); g.moveTo(tx, ty - R * 0.12); g.quadraticCurveTo(tx + R * 0.07, ty, tx, ty + R * 0.06); g.quadraticCurveTo(tx - R * 0.07, ty, tx, ty - R * 0.12); g.fillStyle = 'rgba(140,200,255,0.9)'; g.fill(); }
  if (F.sweat || o.sweat) { const sx = x + R * 0.82 * (o.f > 0 ? -1 : 1), sy = y - R * 0.45 + Math.sin(t * 3) * 1.5; g.beginPath(); g.moveTo(sx, sy - R * 0.16); g.quadraticCurveTo(sx + R * 0.1, sy + R * 0.02, sx, sy + R * 0.08); g.quadraticCurveTo(sx - R * 0.1, sy + R * 0.02, sx, sy - R * 0.16); g.fillStyle = 'rgba(150,205,255,0.95)'; g.fill(); }
}

// do vat cam tay
function holdItem(g, x, y, U, f, what, t, o) {
  if (what === 'phone') {
    g.save(); g.translate(x + 1 * U * f, y - 4 * U); g.rotate(-0.15 * f);
    g.beginPath(); g.roundRect(-3.2 * U, -6.5 * U, 6.4 * U, 12 * U, 1.2 * U); g.fillStyle = '#1b1c20'; g.fill(); g.lineWidth = 0.8 * U; g.strokeStyle = '#8b8e96'; g.stroke();
    const sc = o.screen || PAL.screen; g.fillStyle = sc; g.fillRect(-2.5 * U, -5.6 * U, 5 * U, 10.2 * U); g.restore();
    light(g, x + 3 * U * f, y - 6 * U, 26 * U, o.screen || PAL.screen, 0.38);
  } else if (what === 'umbrella') {
    const top = y - 36 * U; g.save(); g.strokeStyle = '#3a3a3a'; g.lineWidth = 1.2 * U; g.beginPath(); g.moveTo(x, y + 4 * U); g.lineTo(x, top); g.stroke();
    g.beginPath(); g.moveTo(x - 30 * U, top + 6 * U); g.quadraticCurveTo(x, top - 22 * U, x + 30 * U, top + 6 * U); for (let i = 3; i >= -3; i--) g.quadraticCurveTo(x + (i + 0.5) * 10 * U - 5 * U, top + 1 * U, x + i * 10 * U - 0 * U, top + 6 * U); g.closePath(); g.fillStyle = o.umbrellaColor || '#f2c230'; g.fill(); g.lineWidth = 1 * U; g.strokeStyle = '#a07c15'; g.stroke(); g.restore();
  } else if (what === 'book') { g.save(); g.translate(x, y - 2 * U); g.fillStyle = '#e8b33c'; g.fillRect(-6 * U, -8 * U, 9 * U, 11 * U); g.fillStyle = '#4e6b52'; g.fillRect(-6 * U, -8 * U, 2 * U, 11 * U); g.restore(); }
  else if (what === 'ball') { dot(g, x + 3 * U * f, y + 2 * U, 5.5 * U, '#e07b2f', '#6a3510', 0.8 * U); }
  else if (what === 'bag') { g.save(); g.fillStyle = '#24262c'; g.beginPath(); g.roundRect(x - 4 * U, y, 12 * U, 14 * U, 2 * U); g.fill(); g.restore(); }
  else if (what === 'cup') { g.save(); g.fillStyle = '#f2efe9'; g.beginPath(); g.roundRect(x - 3 * U, y - 6 * U, 6 * U, 7 * U, 1.2 * U); g.fill(); g.restore(); }
}

// dau nam tren goi (nguoi trong chan): goc nghieng rot
export function lyingHead(g, x, y, R, o = {}) { g.save(); g.translate(x, y); g.rotate(o.rot ?? -0.35); head(g, 0, 0, R, { ...CAST[o.who || 'hero'], ...o, U: R / 17, f: o.facing ?? 1 }); g.restore(); }
// ban tay to (can canh cam dien thoai, viet so...)
export function bigHand(g, x, y, s, o = {}) {
  g.save(); g.translate(x, y); g.rotate(o.rot || 0); const skin = o.skin || PAL.hero, ed = PAL.heroLine;
  // canh tay (tay ao xam neu co)
  g.fillStyle = o.sleeve || skin; g.beginPath(); g.roundRect(-s * 0.32, 0, s * 0.64, s * 3, s * 0.3); g.fill(); g.lineWidth = s * 0.03; g.strokeStyle = o.sleeve ? shade(o.sleeve, -0.3) : ed; g.stroke();
  g.fillStyle = skin; g.beginPath(); g.ellipse(0, 0, s * 0.42, s * 0.5, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = ed; g.stroke();
  if (o.thumb !== false) { g.beginPath(); g.ellipse(s * 0.15, -s * 0.55, s * 0.16, s * 0.42, 0.25, 0, Math.PI * 2); g.fill(); g.stroke(); }
  g.restore();
}

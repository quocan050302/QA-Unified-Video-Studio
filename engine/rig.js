// rig.js — nguoi que: khung xuong 11 diem, trang phuc, mat va bieu cam, mat to can canh.
// Don vi rig: dau ban kinh 26, chieu cao ~205. Goc toa do = diem cham dat giua hai chan, y am = len tren.
import { E, UI, clamp, lerp, ease, prog, seg, circle, poly, alpha, shade, hex, css, noise } from './core.js';

// ---------------- tu the ----------------
// moi tu the: hip, neck, head, eN/hN (khuyu/ban tay gan), eF/hF (xa), kN/fN (goi/ban chan gan), kF/fF (xa). x duong = huong mat nhin.
const P = (o) => o;
export const POSES = {
  stand:      P({ hip: [0, -92], neck: [0, -150], head: [2, -180], eN: [7, -121], hN: [9, -93], eF: [-5, -121], hF: [-7, -94], kN: [5, -46], fN: [5, 0], kF: [-5, -46], fF: [-7, 0] }),
  relaxed:    P({ hip: [0, -92], neck: [-1, -150], head: [1, -180], eN: [10, -122], hN: [5, -95], eF: [-9, -121], hF: [-6, -95], kN: [8, -46], fN: [12, 0], kF: [-8, -46], fF: [-14, 0] }),
  talk:       P({ hip: [0, -92], neck: [1, -150], head: [4, -180], eN: [16, -120], hN: [36, -128], eF: [-6, -121], hF: [-8, -94], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-10, 0] }),
  explain:    P({ hip: [0, -92], neck: [1, -150], head: [4, -180], eN: [20, -122], hN: [44, -136], eF: [-14, -122], hF: [-26, -128], kN: [7, -46], fN: [10, 0], kF: [-7, -46], fF: [-12, 0] }),
  point:      P({ hip: [0, -92], neck: [2, -150], head: [5, -180], eN: [26, -140], hN: [56, -146], eF: [-6, -121], hF: [-8, -94], kN: [7, -46], fN: [10, 0], kF: [-6, -46], fF: [-9, 0] }),
  pointUp:    P({ hip: [0, -92], neck: [1, -150], head: [4, -181], eN: [18, -168], hN: [26, -204], eF: [-6, -121], hF: [-8, -94], kN: [6, -46], fN: [7, 0], kF: [-6, -46], fF: [-8, 0] }),
  wave:       P({ hip: [0, -92], neck: [0, -150], head: [3, -180], eN: [22, -160], hN: [30, -196], eF: [-6, -121], hF: [-8, -94], kN: [5, -46], fN: [5, 0], kF: [-5, -46], fF: [-7, 0] }),
  cheer:      P({ hip: [0, -94], neck: [0, -152], head: [2, -183], eN: [18, -172], hN: [26, -208], eF: [-18, -172], hF: [-24, -208], kN: [8, -47], fN: [12, 0], kF: [-8, -47], fF: [-12, 0] }),
  handsOnHead:P({ hip: [0, -92], neck: [0, -150], head: [2, -180], eN: [26, -166], hN: [10, -196], eF: [-24, -166], hF: [-8, -198], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  crossArms:  P({ hip: [0, -92], neck: [0, -150], head: [2, -180], eN: [12, -124], hN: [-8, -128], eF: [-10, -126], hF: [10, -130], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  think:      P({ hip: [0, -92], neck: [1, -150], head: [4, -180], eN: [16, -124], hN: [14, -166], eF: [-6, -121], hF: [8, -122], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  shrug:      P({ hip: [0, -92], neck: [0, -148], head: [2, -178], eN: [24, -136], hN: [40, -150], eF: [-22, -136], hF: [-38, -150], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  holdFront:  P({ hip: [0, -92], neck: [1, -150], head: [4, -180], eN: [16, -124], hN: [32, -132], eF: [8, -124], hF: [28, -128], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  phone:      P({ hip: [0, -92], neck: [2, -149], head: [7, -177], eN: [16, -122], hN: [24, -148], eF: [-4, -122], hF: [-6, -94], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  sad:        P({ hip: [0, -90], neck: [4, -144], head: [10, -170], eN: [9, -116], hN: [10, -88], eF: [-2, -116], hF: [-2, -88], kN: [5, -45], fN: [5, 0], kF: [-5, -45], fF: [-7, 0] }),
  facepalm:   P({ hip: [0, -91], neck: [3, -147], head: [8, -175], eN: [22, -138], hN: [16, -172], eF: [-5, -120], hF: [-7, -93], kN: [6, -46], fN: [8, 0], kF: [-6, -46], fF: [-8, 0] }),
  ready:      P({ hip: [0, -80], neck: [10, -134], head: [16, -162], eN: [24, -110], hN: [34, -120], eF: [-6, -110], hF: [8, -116], kN: [20, -42], fN: [18, 0], kF: [-16, -40], fF: [-26, 0] }),
  crouch:     P({ hip: [-6, -56], neck: [10, -108], head: [18, -136], eN: [22, -82], hN: [34, -58], eF: [4, -82], hF: [14, -52], kN: [26, -40], fN: [14, 0], kF: [18, -34], fF: [-10, 0] }),
  sit:        P({ hip: [0, -72], neck: [2, -130], head: [5, -160], eN: [12, -100], hN: [30, -84], eF: [-2, -100], hF: [16, -80], kN: [40, -74], fN: [40, 0], kF: [34, -72], fF: [30, 0] }),
  sitBack:    P({ hip: [-4, -72], neck: [-14, -128], head: [-12, -158], eN: [-2, -100], hN: [18, -84], eF: [-20, -100], hF: [-8, -80], kN: [36, -76], fN: [44, 0], kF: [30, -74], fF: [34, 0] }),
  kneel:      P({ hip: [0, -60], neck: [4, -118], head: [7, -148], eN: [12, -90], hN: [16, -64], eF: [-2, -90], hF: [0, -62], kN: [24, -30], fN: [26, 0], kF: [-4, 0], fF: [-36, 0] }),
  jump:       P({ hip: [0, -112], neck: [2, -170], head: [4, -200], eN: [22, -184], hN: [30, -214], eF: [-18, -184], hF: [-26, -212], kN: [16, -80], fN: [6, -50], kF: [-10, -80], fF: [-22, -56] }),
  fall:       P({ hip: [0, -60], neck: [-30, -100], head: [-46, -120], eN: [-6, -110], hN: [10, -132], eF: [-40, -72], hF: [-30, -44], kN: [30, -70], fN: [52, -40], kF: [22, -40], fF: [40, -10] }),
  lie:        P({ hip: [0, -14], neck: [-58, -16], head: [-88, -20], eN: [-36, -6], hN: [-14, -4], eF: [-40, -24], hF: [-22, -30], kN: [44, -14], fN: [88, -10], kF: [44, -22], fF: [86, -20] }),
};
const KEYS = Object.keys(POSES.stand);
export function blendPose(a, b, k) { const o = {}; for (const key of KEYS) o[key] = [lerp(a[key][0], b[key][0], k), lerp(a[key][1], b[key][1], k)]; return o; }
const asPose = (p) => (typeof p === 'string' ? POSES[p] : p);
// posesAt(t, [[0,'stand'],[0.6,'point']], 0.3) — chuyen tu the theo thoi gian, moi lan chuyen dai `blend` giay
export function posesAt(t, list, blend = 0.3) {
  let cur = asPose(list[0][1]);
  for (let i = 1; i < list.length; i++) {
    const [ti, p] = list[i];
    if (t >= ti) cur = blendPose(cur, asPose(p), ease.inOut(clamp((t - ti) / blend)));
  }
  return cur;
}
// tho nhe de nhan vat khong dung im
export function breathe(pose, t, amt = 1, seed = 1) {
  pose = asPose(pose); const b = Math.sin(t * 2.2 + seed) * 1.6 * amt, sway = noise(t * 0.6, seed) * 1.5 * amt;
  const o = { ...pose };
  for (const k of ['neck', 'head', 'eN', 'hN', 'eF', 'hF']) o[k] = [pose[k][0] + sway, pose[k][1] + b * (k === 'head' ? 1.2 : 1)];
  return o;
}
// buoc di / chay: phase tang theo thoi gian (di: t*2PI*0.9, chay: t*2PI*1.5)
export function walkPose(phase, { run = false } = {}) {
  const s = Math.sin(phase), c = Math.cos(phase), A = run ? 1.7 : 1;
  const lean = run ? 12 : 3, hipY = -92 + Math.abs(c) * (run ? 6 : 3) - (run ? 6 : 0);
  const leg = (sg) => { const sw = s * sg; const fx = sw * 26 * A, lift = Math.max(0, -Math.cos(phase + (sg > 0 ? 0 : Math.PI))) * 18 * A; return { k: [fx * 0.6 + 6 * A * (lift > 4 ? 1 : 0.3), -46 - lift * 0.4], f: [fx, -lift * 0.6] }; };
  const n = leg(1), f = leg(-1);
  const arm = (sg) => { const sw = -s * sg; return { e: [lean * 0.6 + sw * 12 * A, -122], h: [lean * 0.6 + sw * 24 * A + (run ? 10 : 0), run ? -112 - Math.abs(sw) * 8 : -96] }; };
  const an = arm(1), af = arm(-1);
  return { hip: [0, hipY], neck: [lean, hipY - 58], head: [lean + 3, hipY - 88], eN: an.e, hN: an.h, eF: af.e, hF: af.h, kN: n.k, fN: n.f, kF: f.k, fF: f.f };
}

// ---------------- mat & bieu cam ----------------
// eyes: dot | big | happy | closed | sleepy | wide | angry | sad | x ; mouth: smile | grin | open | o | flat | frown | smirk | wavy | none ; brows
const EXPR = {
  neutral:   { eyes: 'dot', mouth: 'smile', m: 0.25 },
  smile:     { eyes: 'dot', mouth: 'smile', m: 0.6 },
  happy:     { eyes: 'happy', mouth: 'smile', m: 0.8 },
  joy:       { eyes: 'happy', mouth: 'grin', m: 1 },
  surprised: { eyes: 'big', mouth: 'o', m: 0.5 },
  shocked:   { eyes: 'wide', mouth: 'open', m: 1, brows: 'up' },
  scared:    { eyes: 'wide', mouth: 'wavy', m: 0.7, brows: 'worried' },
  worried:   { eyes: 'dot', mouth: 'frown', m: 0.4, brows: 'worried' },
  nervous:   { eyes: 'dot', mouth: 'wavy', m: 0.5, brows: 'worried' },
  angry:     { eyes: 'angry', mouth: 'frown', m: 0.6, brows: 'angry' },
  determined:{ eyes: 'angry', mouth: 'flat', m: 0.5, brows: 'angry' },
  sad:       { eyes: 'sad', mouth: 'frown', m: 0.7, brows: 'worried' },
  cry:       { eyes: 'closed', mouth: 'frown', m: 1, brows: 'worried', tears: true },
  smirk:     { eyes: 'sleepy', mouth: 'smirk', m: 0.8, brows: 'smug' },
  sleepy:    { eyes: 'sleepy', mouth: 'flat', m: 0.3 },
  thinking:  { eyes: 'dot', mouth: 'flat', m: 0.4, look: [0.5, -0.6] },
  confused:  { eyes: 'dot', mouth: 'wavy', m: 0.4, brows: 'confused' },
  awe:       { eyes: 'big', mouth: 'open', m: 0.6, sparkle: true },
  calm:      { eyes: 'closed', mouth: 'smile', m: 0.4 },
  deadpan:   { eyes: 'sleepy', mouth: 'flat', m: 0.5 },
};
export const EXPRESSIONS = Object.keys(EXPR);

// face(g, cx, cy, r, opts): ve mat len dau tron tam (cx,cy) ban kinh r. dir: 1 nhin phai, -1 trai, 0 chinh dien.
export function face(g, cx, cy, r, o = {}) {
  const ex = EXPR[o.expr || 'neutral'] || EXPR.neutral;
  const dir = o.dir ?? 0, look = o.look || ex.look || [0, 0], white = o.color || '#fbf6ee';
  const ox = cx + dir * r * 0.32 + look[0] * r * 0.08, oy = cy + r * 0.02 + look[1] * r * 0.06;
  const sp = r * (dir ? 0.30 : 0.36), ey = oy - r * 0.12, er = r * 0.13;
  const eyesX = [ox - sp + dir * r * 0.04, ox + sp + dir * r * 0.04];
  const blink = o.blink;
  g.save();
  // mat
  eyesX.forEach((x, i) => {
    const far = dir !== 0 && ((dir > 0 && i === 0) || (dir < 0 && i === 1));
    const sx = far ? 0.78 : 1;
    if (blink || ex.eyes === 'closed') { seg(g, [[x - er * sx, ey + er * 0.2], [x + er * sx, ey + er * 0.2]], r * 0.07, white); return; }
    switch (ex.eyes) {
      case 'happy': g.beginPath(); g.arc(x, ey + er * 0.4, er * sx, Math.PI * 1.1, Math.PI * 1.9); g.lineWidth = r * 0.075; g.lineCap = 'round'; g.strokeStyle = white; g.stroke(); break;
      case 'sleepy': { g.beginPath(); g.ellipse(x, ey + er * 0.25, er * 1.05 * sx, er * 0.55, 0, 0, Math.PI); g.fillStyle = white; g.fill(); seg(g, [[x - er * 1.15 * sx, ey + er * 0.2], [x + er * 1.15 * sx, ey + er * 0.2]], r * 0.05, white); break; }
      case 'big': case 'wide': { const k = ex.eyes === 'wide' ? 1.55 : 1.3; circle(g, x, ey, er * k * sx, white); circle(g, x + look[0] * er * 0.3 + dir * er * 0.25, ey + look[1] * er * 0.3, er * k * 0.42, UI.ink); break; }
      case 'angry': { g.beginPath(); g.ellipse(x, ey + er * 0.2, er * sx, er * 0.8, 0, 0, Math.PI * 2); g.fillStyle = white; g.fill(); break; }
      case 'sad': { g.beginPath(); g.ellipse(x, ey + er * 0.25, er * 0.9 * sx, er * 0.9, 0, 0, Math.PI * 2); g.fillStyle = white; g.fill(); break; }
      default: { g.beginPath(); g.ellipse(x, ey, er * 0.95 * sx, er * 1.15, 0, 0, Math.PI * 2); g.fillStyle = white; g.fill(); }
    }
    if (ex.sparkle) { circle(g, x + er * 0.35, ey - er * 0.4, er * 0.28, UI.ink); circle(g, x + er * 0.35, ey - er * 0.4, er * 0.16, '#ffffff'); }
  });
  // long may (lam cho cam xuc ro hon)
  if (ex.brows) {
    const bw = r * 0.06, by = ey - er * 1.9;
    eyesX.forEach((x, i) => {
      const s = i === 0 ? -1 : 1; let a = [x - er * 1.1, by], b = [x + er * 1.1, by];
      if (ex.brows === 'angry') { a = [x - er * 1.1, by - s * er * 0.45]; b = [x + er * 1.1, by + s * er * 0.45]; }
      if (ex.brows === 'worried') { a = [x - er * 1.1, by + s * er * 0.4]; b = [x + er * 1.1, by - s * er * 0.4]; }
      if (ex.brows === 'up') { a = [x - er, by - er * 0.6]; b = [x + er, by - er * 0.6]; }
      if (ex.brows === 'smug') { a = [x - er * 1.1, by + er * 0.35]; b = [x + er * 1.1, by + er * 0.05]; }
      if (ex.brows === 'confused') { const d = i === 0 ? -0.6 : 0.4; a = [x - er, by + er * d]; b = [x + er, by - er * d]; }
      seg(g, [a, b], bw, white);
    });
  }
  // mieng
  const mx = ox + dir * r * 0.05, my = oy + r * 0.3, mw = r * 0.3 * (dir ? 0.85 : 1), lw = r * 0.07;
  const talk = clamp(o.talk || 0);
  g.lineCap = 'round'; g.lineJoin = 'round'; g.strokeStyle = white; g.fillStyle = white; g.lineWidth = lw;
  if (talk > 0.05) {
    g.beginPath(); g.ellipse(mx, my, mw * (0.5 + 0.2 * talk), r * (0.04 + 0.13 * talk), 0, 0, Math.PI * 2); g.fill();
  } else {
    const m = ex.m;
    switch (ex.mouth) {
      case 'smile': g.beginPath(); g.moveTo(mx - mw, my - r * 0.02); g.quadraticCurveTo(mx, my + r * 0.2 * m, mx + mw, my - r * 0.02); g.stroke(); break;
      case 'grin': g.beginPath(); g.moveTo(mx - mw * 1.1, my - r * 0.04); g.quadraticCurveTo(mx, my + r * 0.34, mx + mw * 1.1, my - r * 0.04); g.closePath(); g.fill(); break;
      case 'open': g.beginPath(); g.ellipse(mx, my + r * 0.04, mw * 0.55, r * 0.17, 0, 0, Math.PI * 2); g.fill(); break;
      case 'o': circle(g, mx, my + r * 0.02, r * 0.09, white); break;
      case 'flat': g.beginPath(); g.moveTo(mx - mw * 0.75, my); g.lineTo(mx + mw * 0.75, my); g.stroke(); break;
      case 'frown': g.beginPath(); g.moveTo(mx - mw * 0.8, my + r * 0.06); g.quadraticCurveTo(mx, my - r * 0.12 * m, mx + mw * 0.8, my + r * 0.06); g.stroke(); break;
      case 'smirk': g.beginPath(); g.moveTo(mx - mw * 0.8, my + r * 0.02); g.quadraticCurveTo(mx + mw * 0.2, my + r * 0.12, mx + mw * 0.9, my - r * 0.1); g.stroke(); break;
      case 'wavy': g.beginPath(); g.moveTo(mx - mw * 0.8, my); for (let i = 1; i <= 4; i++) g.lineTo(mx - mw * 0.8 + i * mw * 0.4, my + (i % 2 ? -1 : 1) * r * 0.045); g.stroke(); break;
    }
  }
  if (ex.tears) { g.fillStyle = alpha('#9fd0ff', 0.9); eyesX.forEach((x) => { g.beginPath(); g.ellipse(x, ey + er * 2.2, er * 0.35, er * 0.7, 0, 0, Math.PI * 2); g.fill(); }); }
  g.restore();
}

// ---------------- trang phuc phu kien dau ----------------
function headwear(g, hx, hy, R, o, f, ink) {
  const c = o.headColor || o.color || '#d64a33';
  switch (o.head) {
    case 'cap': case 'capBack': {
      const back = o.head === 'capBack' ? -1 : 1;
      g.beginPath(); g.arc(hx, hy - R * 0.36, R * 1.0, Math.PI * 1.0, Math.PI * 2.0); g.closePath(); g.fillStyle = c; g.fill();
      g.beginPath(); g.ellipse(hx + f * back * R * 0.95, hy - R * 0.42, R * 0.78, R * 0.15, 0, 0, Math.PI * 2); g.fillStyle = shade(c, -0.15); g.fill(); break;
    }
    case 'beanie': {
      g.beginPath(); g.arc(hx, hy - R * 0.42, R * 1.02, Math.PI * 1.0, Math.PI * 2.0); g.lineTo(hx + R * 1.02, hy - R * 0.42); g.closePath(); g.fillStyle = c; g.fill();
      g.beginPath(); g.ellipse(hx, hy - R * 0.42, R * 1.02, R * 0.4, 0, Math.PI, Math.PI * 2); g.fill();
      g.beginPath(); g.roundRect(hx - R * 1.08, hy - R * 0.62, R * 2.16, R * 0.32, R * 0.12); g.fillStyle = shade(c, -0.18); g.fill();
      circle(g, hx - f * R * 0.15, hy - R * 1.42, R * 0.14, shade(c, 0.1)); break;
    }
    case 'fedora': {
      g.beginPath(); g.ellipse(hx, hy - R * 0.62, R * 1.55, R * 0.2, 0, 0, Math.PI * 2); g.fillStyle = c; g.fill();
      g.beginPath(); g.roundRect(hx - R * 0.85, hy - R * 1.35, R * 1.7, R * 0.78, [R * 0.4, R * 0.4, 2, 2]); g.fill();
      g.fillStyle = shade(c, 0.25); g.fillRect(hx - R * 0.85, hy - R * 0.78, R * 1.7, R * 0.14); break;
    }
    case 'headband': g.beginPath(); g.roundRect(hx - R * 1.02, hy - R * 0.62, R * 2.04, R * 0.3, R * 0.1); g.fillStyle = c; g.fill(); break;
    case 'bun': circle(g, hx - f * R * 0.55, hy - R * 0.95, R * 0.42, ink); break;
    case 'ponytail': { seg(g, [[hx - f * R * 0.9, hy - R * 0.4], [hx - f * R * 1.5, hy + R * 0.2], [hx - f * R * 1.3, hy + R * 0.7]], R * 0.36, ink); break; }
    case 'hood': break; // ve trong torso
    case 'curly': for (let i = 0; i < 7; i++) circle(g, hx + (i - 3) * R * 0.3, hy - R * 0.92 + Math.abs(i - 3) * R * 0.08, R * 0.26, c === '#d64a33' ? ink : c); break;
  }
}
function eyewear(g, hx, hy, R, o, dir) {
  if (!o.face) return;
  const ox = hx + dir * R * 0.32, ey = hy - R * 0.1, sp = R * (dir ? 0.3 : 0.36);
  if (o.face === 'glasses') { g.lineWidth = R * 0.07; g.strokeStyle = o.faceColor || '#e8e2d6'; [ox - sp, ox + sp].forEach((x) => { g.beginPath(); g.arc(x + dir * R * 0.04, ey, R * 0.24, 0, Math.PI * 2); g.stroke(); }); seg(g, [[ox - sp + R * 0.24, ey], [ox + sp - R * 0.2, ey]], R * 0.05, o.faceColor || '#e8e2d6'); }
  if (o.face === 'sunglasses') { g.fillStyle = '#05050a'; [ox - sp, ox + sp].forEach((x) => { g.beginPath(); g.roundRect(x - R * 0.26 + dir * R * 0.04, ey - R * 0.14, R * 0.52, R * 0.3, R * 0.1); g.fill(); }); seg(g, [[ox - sp, ey - R * 0.05], [ox + sp, ey - R * 0.05]], R * 0.06, '#05050a'); }
}

// ---------------- ve nhan vat ----------------
// drawFigure(g, { x, y, s, facing, pose, outfit, expr, talk, blink, look, rim:{color,dir:[dx,dy],w}, alpha, shadow, trail, prop, dim })
export function drawFigure(g, o) {
  const pose = asPose(o.pose || 'stand'), s = (o.s ?? 1) * (o.outfit?.kid ? 0.72 : 1), f = o.facing ?? 1;
  if (o.trail) { const tr = o.trail; for (let i = tr.count || 4; i >= 1; i--) drawFigure(g, { ...o, trail: null, x: o.x + (tr.dx ?? -40) * i * s * f, alpha: (o.alpha ?? 1) * 0.12 * (1 - i / ((tr.count || 4) + 1)) * 2, rim: null, shadow: false }); }
  g.save(); g.globalAlpha *= o.alpha ?? 1;
  if (o.shadow !== false) { g.fillStyle = 'rgba(0,0,0,0.35)'; g.beginPath(); g.ellipse(o.x, o.y + 2 * s, 44 * s, 8 * s, 0, 0, Math.PI * 2); g.fill(); }
  g.translate(o.x, o.y); if (o.rot) g.rotate(o.rot); g.scale(s * f, s);
  const rim = o.rim;
  if (rim) {
    const w = (rim.w ?? 4.5) / s, d = rim.dir || [0, -1], L = Math.hypot(d[0], d[1]) || 1;
    g.save(); g.translate((d[0] / L) * w * f, (d[1] / L) * w); body(g, pose, o, rim.color, rim.color, true); g.restore();
  }
  body(g, pose, o, null, null, false);
  g.restore();
}
// nguoi que trong toa do rig (da scale, lat theo facing)
function body(g, p, o, mono, monoFar, isRim) {
  const out = o.outfit || {}, ink = mono || (o.dim ? '#1a1520' : UI.ink), far = monoFar || UI.inkFar;
  const col = (c) => mono || c;
  const R = 26, LW = 12, TW = 15;
  const top = out.top || 'none', tc = out.color || '#d64a33';
  // tay chan phia xa
  seg(g, [p.hip, p.kF, p.fF], LW, far); seg(g, [p.fF, [p.fF[0] + 9, p.fF[1]]], LW, far);
  seg(g, [p.neck, p.eF, p.hF], LW - 1, far);
  if (top === 'hoodie' || top === 'tracksuit' || top === 'labcoat' || top === 'suit' || top === 'trench') seg(g, [lerp2(p.neck, p.eF, 0.2), p.eF, lerp2(p.eF, p.hF, 0.85)], LW + 5, col(shade(top === 'labcoat' ? '#e8e4dc' : top === 'suit' || top === 'trench' ? (out.color || '#2b2a33') : tc, -0.35)));
  // ao khoac dai (ve truoc chan gan)
  if (top === 'labcoat' || top === 'trench') { const c2 = top === 'labcoat' ? '#ece8e0' : (out.color || '#2b2a33'); poly(g, [[p.neck[0] - 12, p.neck[1] + 4], [p.neck[0] + 12, p.neck[1] + 4], [p.hip[0] + 20, p.hip[1] + 46], [p.hip[0] - 20, p.hip[1] + 46]], col(c2)); }
  if (top === 'dress') poly(g, [[p.neck[0] - 10, p.neck[1] + 6], [p.neck[0] + 10, p.neck[1] + 6], [p.hip[0] + 30, p.hip[1] + 40], [p.hip[0] - 30, p.hip[1] + 40]], col(tc));
  // chan gan
  const legC = out.legs ? col(out.legs) : ink;
  seg(g, [p.hip, p.kN, p.fN], LW, legC); seg(g, [p.fN, [p.fN[0] + 10, p.fN[1]]], LW, ink);
  // than
  seg(g, [p.hip, p.neck], TW, ink);
  if (top === 'hoodie' || top === 'tracksuit' || top === 'jersey' || top === 'tshirt' || top === 'suit' || top === 'labcoat' || top === 'trench') {
    const c = top === 'labcoat' ? '#ece8e0' : top === 'suit' || top === 'trench' ? (out.color || '#2b2a33') : tc;
    const len = top === 'tshirt' || top === 'jersey' ? 0.9 : 1.08;
    const hb = lerp2(p.neck, p.hip, len);
    poly(g, [[p.neck[0] - 13, p.neck[1] + 2], [p.neck[0] + 13, p.neck[1] + 2], [hb[0] + 16, hb[1]], [hb[0] - 16, hb[1]]], col(c));
    g.beginPath(); g.ellipse(p.neck[0], p.neck[1] + 4, 14, 7, 0, 0, Math.PI * 2); g.fillStyle = col(c); g.fill();
    if (!isRim) {
      if (top === 'hoodie') { seg(g, [[p.neck[0] + 4, p.neck[1] + 8], [p.neck[0] + 5, p.neck[1] + 34]], 2.6, '#f4efe6'); seg(g, [[p.neck[0] + 10, p.neck[1] + 8], [p.neck[0] + 11, p.neck[1] + 30]], 2.6, '#f4efe6'); }
      if (top === 'suit') { poly(g, [[p.neck[0] + 4, p.neck[1] + 4], [p.neck[0] + 9, p.neck[1] + 4], [p.neck[0] + 7, p.neck[1] + 34]], out.color2 || '#7a1f2b'); }
      if (top === 'jersey' && out.number) { g.fillStyle = '#ffffff'; g.font = '700 16px "Baloo 2"'; g.textAlign = 'center'; g.fillText(String(out.number), p.neck[0], p.neck[1] + 34); }
    }
  }
  // tay gan
  seg(g, [p.neck, p.eN, p.hN], LW - 1, ink);
  if (top === 'hoodie' || top === 'tracksuit' || top === 'labcoat' || top === 'suit' || top === 'trench') { const c = top === 'labcoat' ? '#ece8e0' : top === 'suit' || top === 'trench' ? (out.color || '#2b2a33') : tc; seg(g, [lerp2(p.neck, p.eN, 0.15), p.eN, lerp2(p.eN, p.hN, 0.85)], LW + 6, col(c)); }
  if (top === 'tshirt' || top === 'jersey') seg(g, [lerp2(p.neck, p.eN, 0.1), lerp2(p.neck, p.eN, 0.6)], LW + 6, col(tc));
  if (out.gloves) { circle(g, p.hN[0], p.hN[1], 8, col(out.gloves)); }
  // dau
  const hx = p.head[0], hy = p.head[1];
  if (top === 'hoodie' && out.head === 'hood') { circle(g, hx - 3, hy + 2, R * 1.2, col(tc)); }
  else if (top === 'hoodie') { g.beginPath(); g.ellipse(p.neck[0] - 9, p.neck[1] - 2, 13, 11, -0.5, 0, Math.PI * 2); g.fillStyle = col(shade(tc, -0.12)); g.fill(); }
  seg(g, [p.neck, [hx * 0.6, hy + R * 0.9]], TW - 2, ink);
  circle(g, hx, hy, R, ink);
  if (top === 'hoodie' && out.head === 'hood' && !isRim) { g.beginPath(); g.arc(hx - 3, hy + 2, R * 1.2, Math.PI * 0.75, Math.PI * 1.65); g.lineWidth = 6; g.strokeStyle = shade(tc, -0.2); g.stroke(); }
  if (!isRim && !o.noFace) {
    // mat (dat trong toa do rig: facing da lat, nen dir=1 la phia truoc)
    const sc = 1; g.save(); g.translate(hx, hy); g.scale(1 / 1, 1);
    // tranh chu bi lat: mat doi xung nen lat ok
    face(g, 0, 0, R, { expr: o.expr, talk: o.talk, blink: o.blink, look: o.look, dir: o.front ? 0 : 1 });
    eyewear(g, 0, 0, R, out, o.front ? 0 : 1);
    g.restore();
  }
  headwear(g, hx, hy, R, out, 1, mono || ink);
  if (o.prop && !isRim) prop(g, o.prop, p);
}
const lerp2 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k)];
function prop(g, name, p) {
  const [x, y] = p.hN;
  switch (name) {
    case 'phone': g.save(); g.translate(x + 2, y - 6); g.rotate(-0.25); g.fillStyle = '#15131a'; g.beginPath(); g.roundRect(-7, -14, 14, 26, 3); g.fill(); g.fillStyle = '#9fd0ff'; g.globalAlpha *= 0.9; g.fillRect(-5, -11, 10, 19); g.restore(); break;
    case 'cup': g.fillStyle = '#f2ece2'; g.beginPath(); g.roundRect(x - 7, y - 16, 14, 16, 3); g.fill(); break;
    case 'paper': g.save(); g.translate(x + 8, y - 10); g.rotate(-0.15); g.fillStyle = '#f4efe6'; g.fillRect(-12, -16, 24, 30); g.fillStyle = '#b9b2a6'; for (let i = 0; i < 4; i++) g.fillRect(-8, -10 + i * 6, 16, 2); g.restore(); break;
    case 'ball': circle(g, x + 4, y - 8, 12, '#f4f1ea'); break;
    case 'folder': g.save(); g.translate(x + 6, y - 6); g.rotate(-0.1); g.fillStyle = '#7a4a26'; g.fillRect(-16, -12, 32, 24); g.restore(); break;
    case 'cane': seg(g, [[x, y], [x + 6, 0]], 4, '#8a5a32'); break;
    case 'flashlight': seg(g, [[x, y], [x + 18, y - 4]], 7, '#2a2a30'); break;
  }
}
// vi tri dau trong toa do canh (de dat hieu ung quanh dau)
export function headPos(o) {
  const pose = asPose(o.pose || 'stand'), s = (o.s ?? 1) * (o.outfit?.kid ? 0.72 : 1), f = o.facing ?? 1;
  return [o.x + pose.head[0] * s * f, o.y + pose.head[1] * s, 26 * s];
}

// ---------------- mat to can canh ----------------
// bigFace(g, cx, cy, r, { outfit, expr, talk, blink, look, rimColor, rimSide:-1|1, tilt, dir })
export function bigFace(g, cx, cy, r, o = {}) {
  const out = o.outfit || {}, tc = out.color || '#d64a33', top = out.top || 'hoodie';
  g.save(); g.translate(cx, cy); g.rotate(o.tilt || 0);
  const shoulder = top === 'labcoat' ? '#ece8e0' : top === 'suit' || top === 'trench' ? (out.color || '#2b2a33') : top === 'none' ? UI.ink : tc;
  // vai va co
  g.beginPath(); g.ellipse(0, r * 1.75, r * 1.55, r * 0.95, 0, Math.PI, Math.PI * 2); g.fillStyle = shoulder; g.fill();
  if (top === 'hoodie') { seg(g, [[-r * 0.22, r * 0.95], [-r * 0.2, r * 1.6]], r * 0.045, '#f4efe6'); seg(g, [[r * 0.22, r * 0.95], [r * 0.2, r * 1.6]], r * 0.045, '#f4efe6'); }
  if (out.head === 'hood') { circle(g, 0, r * 0.08, r * 1.2, tc); }
  seg(g, [[0, r * 0.6], [0, r * 1.2]], r * 0.32, UI.ink);
  // vien sang
  const side = o.rimSide ?? -1, rc = o.rimColor || '#ffd3a0';
  g.save(); g.translate(side * r * 0.06, -r * 0.05); circle(g, 0, 0, r * 1.0, rc); g.restore();
  circle(g, 0, 0, r, UI.ink);
  face(g, 0, 0, r, { expr: o.expr, talk: o.talk, blink: o.blink, look: o.look, dir: o.dir ?? 0 });
  eyewear(g, 0, 0, r, out, o.dir ?? 0);
  headwear(g, 0, 0, r, out, o.dir >= 0 ? 1 : -1, UI.ink);
  g.restore();
}

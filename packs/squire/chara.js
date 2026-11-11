// chara.js (pack squire) — nhan vat dau tron trang: dau to (~38% chieu cao), than nho, tay ong, gang trang,
// trang phuc + mu giap theo thoi dai. soldier(g, x, y, h, o): x,y = chan cham dat; h = chieu cao toi dinh dau (khong tinh mu).
// o = { preset, face, look(-1..1), flip, pose, talk(0..1), t, blink, helmet, visor, hair, beard, body, tabard, charge, colors..., shield, weapon, kid, lod }
import { E, clamp, lerp, ease, noise, shade, alpha } from './ink.js';
import { OUT, PAL, shape, rect, ellipse, circ, blob, polyS, line, tube, celShade, darker, lighter, smoothPath } from './ink.js';

// ====================================================================================== MAT
// mat: eyes, brows, mouth, blush, tears, sweat
export const FACES = {
  neutral:   { eyes: 'dot', brows: 'flat', mouth: 'flat' },
  calm:      { eyes: 'dot', brows: 'soft', mouth: 'smile' },
  happy:     { eyes: 'happy', brows: 'up', mouth: 'grin', blush: true },
  laugh:     { eyes: 'happy', brows: 'up', mouth: 'shout', blush: true },
  smile:     { eyes: 'dot', brows: 'soft', mouth: 'smile', blush: true },
  proud:     { eyes: 'closed', brows: 'up', mouth: 'smile', blush: true },
  sad:       { eyes: 'dot', brows: 'sad', mouth: 'frown' },
  cry:       { eyes: 'wide', brows: 'sad', mouth: 'wail', tears: true },
  worried:   { eyes: 'open', brows: 'sad', mouth: 'wavy', sweat: true },
  scared:    { eyes: 'wide', brows: 'sad', mouth: 'teeth', sweat: true },
  shock:     { eyes: 'wide', brows: 'up', mouth: 'o' },
  surprised: { eyes: 'open', brows: 'up', mouth: 'o' },
  angry:     { eyes: 'dot', brows: 'angry', mouth: 'teeth' },
  shout:     { eyes: 'dot', brows: 'angry', mouth: 'shout' },
  bored:     { eyes: 'half', brows: 'flat', mouth: 'frown' },
  smug:      { eyes: 'half', brows: 'smug', mouth: 'smirk' },
  determined:{ eyes: 'dot', brows: 'angry', mouth: 'flat' },
  confused:  { eyes: 'open', brows: 'confused', mouth: 'wavy' },
  tired:     { eyes: 'half', brows: 'sad', mouth: 'o', sweat: true },
  pain:      { eyes: 'squint', brows: 'sad', mouth: 'teeth', sweat: true },
  dead:      { eyes: 'x', brows: 'none', mouth: 'o' },
  sleep:     { eyes: 'closed', brows: 'soft', mouth: 'flat' },
  wink:      { eyes: 'wink', brows: 'smug', mouth: 'smile' },
  think:     { eyes: 'side', brows: 'confused', mouth: 'flat' },
};

function eye(g, x, y, R, kind, lw, look, blinkK, side) {
  const ex = look * R * 0.07;
  const closed = blinkK > 0.5 && ['dot', 'open', 'wide', 'half', 'side'].includes(kind);
  if (closed) { line(g, [[x - R * 0.1, y], [x + R * 0.1, y]], { lw: lw * 0.9 }); return; }
  if (kind === 'dot' || kind === 'side') {
    const dx = kind === 'side' ? R * 0.06 : 0;
    ellipse(g, x + ex + dx, y, R * 0.065, R * 0.095, { fill: OUT, lw: 0 });
    circ(g, x + ex + dx - R * 0.02, y - R * 0.035, R * 0.022, { fill: '#fff', lw: 0 });
  } else if (kind === 'open' || kind === 'wide') {
    const r = kind === 'wide' ? R * 0.17 : R * 0.135;
    circ(g, x, y, r, { fill: '#fff', lw: lw * 0.8 });
    circ(g, x + ex * 1.4, y + r * 0.08, r * (kind === 'wide' ? 0.32 : 0.45), { fill: OUT, lw: 0 });
  } else if (kind === 'half') {
    ellipse(g, x + ex, y + R * 0.025, R * 0.07, R * 0.07, { fill: OUT, lw: 0 });
    g.save(); g.fillStyle = PAL.skin; g.fillRect(x - R * 0.14, y - R * 0.12, R * 0.28, R * 0.11); g.restore();
    line(g, [[x - R * 0.12, y - R * 0.01], [x + R * 0.12, y - R * 0.01]], { lw: lw * 0.9 });
  } else if (kind === 'happy') {
    line(g, [[x - R * 0.11, y + R * 0.03], [x, y - R * 0.07], [x + R * 0.11, y + R * 0.03]], { lw: lw * 0.95 });
  } else if (kind === 'closed') {
    line(g, [[x - R * 0.11, y - R * 0.01], [x, y + R * 0.05], [x + R * 0.11, y - R * 0.01]], { lw: lw * 0.95 });
  } else if (kind === 'squint') {
    const s = side < 0 ? 1 : -1;
    line(g, [[x - R * 0.1 * s, y - R * 0.07], [x + R * 0.08 * s, y], [x - R * 0.1 * s, y + R * 0.07]], { lw: lw * 0.95 });
  } else if (kind === 'x') {
    line(g, [[x - R * 0.08, y - R * 0.08], [x + R * 0.08, y + R * 0.08]], { lw: lw * 0.9 }); line(g, [[x + R * 0.08, y - R * 0.08], [x - R * 0.08, y + R * 0.08]], { lw: lw * 0.9 });
  } else if (kind === 'wink') {
    if (side < 0) line(g, [[x - R * 0.11, y], [x, y - R * 0.06], [x + R * 0.11, y]], { lw: lw * 0.95 });
    else eye(g, x, y, R, 'dot', lw, look, 0, side);
  }
}
function brow(g, x, y, R, kind, lw, side) {
  // side -1 = mat trai (nguoi xem), 1 = mat phai. in = dau trong (gan mui), out = dau ngoai
  const H = { flat: [0, 0, 0], soft: [0.01, -0.02, 0.01], up: [-0.03, -0.07, -0.03], sad: [-0.07, -0.05, 0.03], angry: [0.05, 0, -0.05], smug: side < 0 ? [0, 0, 0] : [-0.01, -0.04, -0.07], confused: side < 0 ? [-0.06, -0.06, -0.03] : [0.02, 0.02, 0.02] }[kind];
  if (!H) return;
  const xin = x - side * R * 0.11, xout = x + side * R * 0.13;
  line(g, [[xin, y + H[0] * R], [x + side * R * 0.01, y + H[1] * R], [xout, y + H[2] * R]], { lw: lw * 1.05 });
}
function mouth(g, x, y, R, kind, lw, talk) {
  const k = clamp(talk || 0);
  if (k > 0.15 && ['flat', 'smile', 'frown', 'wavy', 'smirk'].includes(kind)) kind = k > 0.6 ? 'talkBig' : 'talk';
  switch (kind) {
    case 'flat': line(g, [[x - R * 0.08, y], [x + R * 0.08, y]], { lw: lw * 0.85 }); break;
    case 'smile': line(g, [[x - R * 0.1, y - R * 0.02], [x, y + R * 0.045], [x + R * 0.1, y - R * 0.02]], { lw: lw * 0.85 }); break;
    case 'frown': line(g, [[x - R * 0.09, y + R * 0.035], [x, y - R * 0.02], [x + R * 0.09, y + R * 0.035]], { lw: lw * 0.85 }); break;
    case 'smirk': line(g, [[x - R * 0.08, y + R * 0.01], [x + R * 0.04, y + R * 0.02], [x + R * 0.11, y - R * 0.04]], { lw: lw * 0.85 }); break;
    case 'wavy': line(g, [[x - R * 0.11, y + R * 0.01], [x - R * 0.055, y - R * 0.025], [x, y + R * 0.01], [x + R * 0.055, y - R * 0.025], [x + R * 0.11, y + R * 0.01]], { lw: lw * 0.75 }); break;
    case 'o': ellipse(g, x, y + R * 0.01, R * 0.055, R * 0.07, { fill: PAL.mouth, lw: lw * 0.75 }); break;
    case 'talk': shape(g, (c) => { c.moveTo(x - R * 0.09, y - R * 0.01); c.quadraticCurveTo(x, y - R * 0.03, x + R * 0.09, y - R * 0.01); c.quadraticCurveTo(x, y + R * 0.1, x - R * 0.09, y - R * 0.01); }, { fill: PAL.mouth, lw: lw * 0.75 }); break;
    case 'talkBig': case 'grin': case 'shout': case 'wail': {
      const w = kind === 'shout' || kind === 'wail' ? 0.15 : kind === 'grin' ? 0.13 : 0.1, h = kind === 'shout' || kind === 'wail' ? 0.2 : kind === 'grin' ? 0.13 : 0.12;
      const top = kind === 'wail' ? y + R * 0.02 : y - R * 0.03;
      shape(g, (c) => {
        if (kind === 'wail') { c.moveTo(x - R * w, top + R * h * 0.75); c.quadraticCurveTo(x, top - R * h * 0.6, x + R * w, top + R * h * 0.75); c.quadraticCurveTo(x, top + R * h * 1.1, x - R * w, top + R * h * 0.75); }
        else { c.moveTo(x - R * w, top); c.quadraticCurveTo(x, top - R * 0.02, x + R * w, top); c.quadraticCurveTo(x + R * w * 0.9, top + R * h * 1.2, x, top + R * h); c.quadraticCurveTo(x - R * w * 0.9, top + R * h * 1.2, x - R * w, top); }
      }, { fill: PAL.mouth, lw: lw * 0.75, inner: (c) => { ellipse(c, x, top + R * h * 1.05, R * w * 0.62, R * h * 0.45, { fill: PAL.tongue, lw: 0 }); } });
      break;
    }
    case 'teeth': {
      const w = R * 0.15, h = R * 0.09;
      shape(g, (c) => c.roundRect(x - w, y - h * 0.6, w * 2, h * 1.3, h * 0.5), { fill: '#fff', lw: lw * 0.75, inner: (c) => { for (let i = -2; i <= 2; i++) line(c, [[x + i * w * 0.36, y - h], [x + i * w * 0.36, y + h]], { lw: lw * 0.45 }); line(c, [[x - w, y + h * 0.05], [x + w, y + h * 0.05]], { lw: lw * 0.45 }); } });
      break;
    }
  }
}
// ve khuon mat trong dau (cx,cy,R)
export function face(g, cx, cy, R, o = {}) {
  const f = typeof o.face === 'object' ? o.face : (FACES[o.face] || FACES.neutral), lw = o.lw, look = o.look || 0;
  const ox = look * R * 0.22, ey = cy + (o.eyeY ?? 0.02) * R, sp = R * 0.33;
  const blinkK = o.blink ?? blinkAt(o.t || 0, o.seed || 0);
  if (f.blush) { ellipse(g, cx - sp - R * 0.05 + ox, ey + R * 0.2, R * 0.12, R * 0.07, { fill: alpha(PAL.blush, 0.8), lw: 0 }); ellipse(g, cx + sp + R * 0.05 + ox, ey + R * 0.2, R * 0.12, R * 0.07, { fill: alpha(PAL.blush, 0.8), lw: 0 }); }
  if (o.freckles) for (const s of [-1, 1]) for (let i = 0; i < 3; i++) circ(g, cx + s * (sp + R * 0.02) + ox + (i - 1) * R * 0.06, ey + R * 0.2 + (i % 2) * R * 0.03, R * 0.016, { fill: '#c9845a', lw: 0 });
  eye(g, cx - sp + ox, ey, R, f.eyes, lw, look, blinkK, -1); eye(g, cx + sp + ox, ey, R, f.eyes, lw, look, blinkK, 1);
  if (f.brows !== 'none' && !o.noBrows) { brow(g, cx - sp + ox, ey - R * 0.2, R, f.brows, lw, -1); brow(g, cx + sp + ox, ey - R * 0.2, R, f.brows, lw, 1); }
  const my = cy + R * 0.42;
  if (o.beard) beard(g, cx + ox * 0.6, my, R, o);
  if (!o.mouthHidden) mouth(g, cx + ox * 0.7, my, R, f.mouth, lw, o.talk);
  if (o.mustache) mustache(g, cx + ox * 0.7, my - R * 0.1, R, o.hairColor || PAL.hair, lw, o.mustache);
  if (f.tears) for (const s of [-1, 1]) { shape(g, (c) => { const x = cx + s * sp + ox, y = ey + R * 0.16; c.moveTo(x, y); c.quadraticCurveTo(x + s * R * 0.08, y + R * 0.25, x, y + R * 0.32); c.quadraticCurveTo(x - s * R * 0.06, y + R * 0.22, x, y); }, { fill: '#9fd3f2', lw: lw * 0.6 }); }
  if (f.sweat) shape(g, (c) => { const x = cx + R * 0.72, y = cy - R * 0.42; c.moveTo(x, y - R * 0.12); c.quadraticCurveTo(x + R * 0.09, y + R * 0.03, x, y + R * 0.05); c.quadraticCurveTo(x - R * 0.09, y + R * 0.03, x, y - R * 0.12); }, { fill: '#bfe4f7', lw: lw * 0.6 });
}
export function blinkAt(t, seed = 0) { const per = 3.1 + (seed % 7) * 0.37, ph = (t + seed * 0.71) % per; return ph < 0.12 ? 1 : 0; }
function mustache(g, x, y, R, col, lw, kind) {
  const w = R * (kind === 'big' ? 0.3 : 0.22), h = R * 0.1;
  shape(g, (c) => { c.moveTo(x, y - h * 0.4); c.bezierCurveTo(x + w * 0.5, y - h * 1.2, x + w * 1.1, y - h * 0.2, x + w, y + h * 0.9); c.bezierCurveTo(x + w * 0.6, y + h * 0.3, x + w * 0.3, y + h * 0.6, x, y + h * 0.35); c.bezierCurveTo(x - w * 0.3, y + h * 0.6, x - w * 0.6, y + h * 0.3, x - w, y + h * 0.9); c.bezierCurveTo(x - w * 1.1, y - h * 0.2, x - w * 0.5, y - h * 1.2, x, y - h * 0.4); }, { fill: col, lw: lw * 0.75 });
}
function beard(g, x, y, R, o) {
  const col = o.hairColor || PAL.hair, lw = o.lw, kind = o.beard;
  if (kind === 'stubble') return;
  const w = R * (kind === 'full' ? 0.62 : 0.45), d = R * (kind === 'full' ? 0.5 : kind === 'long' ? 0.7 : 0.34);
  shape(g, (c) => { c.moveTo(x - w, y - R * 0.22); c.quadraticCurveTo(x - w * 0.95, y + d * 0.8, x, y + d); c.quadraticCurveTo(x + w * 0.95, y + d * 0.8, x + w, y - R * 0.22); c.quadraticCurveTo(x, y + R * 0.08, x - w, y - R * 0.22); }, { fill: col, lw: lw * 0.8 });
}

// ====================================================================================== DAU + MU
// helmet: nasal | coif | bucket | bascinet | kettle | sallet | crown | montefortino | attic | kabuto | jingasa | m1 | brodie | cap | kepi | peaked | sailor | riot | hood | turban | none
// hair: short | bowl | long | braid | curly | bald | bun | topknot | side | none
export function head(g, cx, cy, R, o = {}) {
  const lw = o.lw ?? Math.max(1.2, R * 0.075), O = { ...o, lw };
  const hl = o.helmet || 'none';
  // toc/sau mu (ve truoc dau)
  if (o.hair === 'long' || o.hair === 'braid') blob(g, [[cx - R * 0.95, cy - R * 0.2], [cx - R * 0.9, cy + R * 1.1], [cx - R * 0.3, cy + R * 1.2], [cx + R * 0.3, cy + R * 1.2], [cx + R * 0.9, cy + R * 1.1], [cx + R * 0.95, cy - R * 0.2], [cx, cy - R * 1.05]], { fill: o.hairColor || PAL.hairDark, lw });
  if (o.hair === 'braid') tube(g, [[cx + R * 0.55, cy + R * 0.7], [cx + R * 0.62, cy + R * 1.3], [cx + R * 0.55, cy + R * 1.9]], R * 0.22, o.hairColor || PAL.hairDark, lw);
  if (hl === 'coif' || o.coif) coifBack(g, cx, cy, R, O);
  if (hl === 'kabuto') kabutoBack(g, cx, cy, R, O);
  if (hl === 'hood') blob(g, [[cx - R * 1.18, cy + R * 0.6], [cx - R * 1.12, cy - R * 0.55], [cx, cy - R * 1.28], [cx + R * 1.12, cy - R * 0.55], [cx + R * 1.18, cy + R * 0.6], [cx, cy + R * 1.1]], { fill: o.hoodColor || PAL.brown, lw });
  // dau
  shape(g, (c) => c.arc(cx, cy, R, 0, Math.PI * 2), { fill: o.skin || PAL.skin, lw, inner: (c) => {
    celShade(c, cx, cy, R, alpha(PAL.skinShade, 0.85), -0.28, 0.08, 1.02);
    if (o.beard === 'stubble' || o.stubble) { c.save(); c.strokeStyle = alpha(OUT, 0.35); c.lineWidth = lw * 0.35; for (let i = -6; i <= 6; i++) { const a = Math.PI / 2 + i * 0.13, x0 = cx + Math.cos(a) * R * 0.78, y0 = cy + Math.sin(a) * R * 0.78; c.beginPath(); c.moveTo(x0, y0); c.lineTo(x0, y0 - R * 0.13); c.stroke(); } c.restore(); }
  } });
  // toc tren dau
  hairTop(g, cx, cy, R, o.hair, o.hairColor || PAL.hair, lw, hl);
  // mat
  const covered = hl === 'bucket' || (hl === 'bascinet' && o.visor === 'down') || hl === 'riotDown';
  if (!covered) face(g, cx, cy, R, { ...O, mouthHidden: o.mouthHidden || (hl === 'bascinet' && o.bevor !== false) || hl === 'sallet' });
  // mu
  helmetFront(g, cx, cy, R, hl, O);
}
function hairTop(g, cx, cy, R, hair, col, lw, hl) {
  if (!hair || hair === 'none' || hair === 'bald') return;
  const hidden = ['nasal', 'bucket', 'bascinet', 'kettle', 'sallet', 'montefortino', 'attic', 'kabuto', 'm1', 'brodie', 'riot', 'riotDown', 'hood', 'coif', 'jingasa', 'turban'].includes(hl);
  if (hidden && hair !== 'side') return;
  if (hair === 'short' || hair === 'side' || hair === 'curly' || hair === 'long' || hair === 'braid' || hair === 'bun' || hair === 'topknot') {
    const lo = hair === 'side' ? 0.15 : -0.25;
    shape(g, (c) => { c.moveTo(cx - R * 1.0, cy + R * lo); c.bezierCurveTo(cx - R * 1.1, cy - R * 1.2, cx + R * 1.1, cy - R * 1.2, cx + R * 1.0, cy + R * lo); c.bezierCurveTo(cx + R * 0.7, cy - R * 0.55, cx + R * 0.1, cy - R * 0.5, cx - R * 0.15, cy - R * 0.75); c.bezierCurveTo(cx - R * 0.4, cy - R * 0.45, cx - R * 0.8, cy - R * 0.55, cx - R * 1.0, cy + R * lo); }, { fill: col, lw });
    if (hair === 'curly') for (let i = 0; i < 7; i++) { const a = Math.PI + 0.25 + i * 0.45; circ(g, cx + Math.cos(a) * R * 0.95, cy + Math.sin(a) * R * 0.95, R * 0.2, { fill: col, lw: lw * 0.8 }); }
    if (hair === 'bun') circ(g, cx, cy - R * 1.05, R * 0.3, { fill: col, lw });
    if (hair === 'topknot') { rect(g, cx - R * 0.12, cy - R * 1.32, R * 0.24, R * 0.36, { fill: col, lw, r: R * 0.08 }); }
  } else if (hair === 'bowl') {
    shape(g, (c) => { c.moveTo(cx - R * 1.04, cy - R * 0.05); c.bezierCurveTo(cx - R * 1.1, cy - R * 1.25, cx + R * 1.1, cy - R * 1.25, cx + R * 1.04, cy - R * 0.05); c.lineTo(cx - R * 1.04, cy - R * 0.05); }, { fill: col, lw });
  }
}
function coifBack(g, cx, cy, R, o) {
  // mu luoi trum dau, lo mat oval
  const lw = o.lw;
  shape(g, (c) => {
    c.moveTo(cx - R * 1.28, cy + R * 1.15); c.bezierCurveTo(cx - R * 1.35, cy - R * 0.2, cx - R * 1.05, cy - R * 1.28, cx, cy - R * 1.3);
    c.bezierCurveTo(cx + R * 1.05, cy - R * 1.28, cx + R * 1.35, cy - R * 0.2, cx + R * 1.28, cy + R * 1.15); c.closePath();
  }, { fill: PAL.mail, lw, inner: (c) => { mailPattern(c, cx - R * 1.4, cy - R * 1.4, R * 2.8, R * 2.8, R * 0.16, lw); celShade(c, cx, cy, R * 1.3, alpha(PAL.mailDark, 0.5), -0.3, 0.05, 1.02); } });
}
function coifFront(g, cx, cy, R, o) {
  // vien lo mat (mat ra oval) — ve vong vai luoi o duoi cam
  const lw = o.lw;
  shape(g, (c) => { c.ellipse(cx, cy + R * 0.1, R * 1.25, R * 1.12, 0, 0, Math.PI * 2); c.ellipse(cx, cy + R * 0.08, R * 0.82, R * 0.9, 0, 0, Math.PI * 2, true); }, { fill: PAL.mail, lw, rule: 'evenodd', inner: (c) => mailPattern(c, cx - R * 1.4, cy - R * 1.2, R * 2.8, R * 2.6, R * 0.16, lw) });
}
// luoi giap: hoa van vong xich lap lai (pattern), dinh theo nhan vat (khong troi khi nhan vat di)
const MAILTILE = new Map();
function mailTile(N, base) {
  const k = N + '|' + base; if (MAILTILE.has(k)) return MAILTILE.get(k);
  const c = document.createElement('canvas'); c.width = N; c.height = Math.round(N * 0.8); const x = c.getContext('2d');
  x.fillStyle = darker(base, 0.1); x.fillRect(0, 0, c.width, c.height);
  const ring = (cx, cy) => { x.beginPath(); x.ellipse(cx, cy, N * 0.52, N * 0.36, 0, 0, Math.PI * 2); x.lineWidth = N * 0.24; x.strokeStyle = darker(base, 0.22); x.stroke(); x.lineWidth = N * 0.16; x.strokeStyle = lighter(base, 0.06); x.stroke(); x.beginPath(); x.ellipse(cx, cy, N * 0.52, N * 0.36, 0, Math.PI * 1.05, Math.PI * 1.6); x.lineWidth = N * 0.07; x.strokeStyle = lighter(base, 0.35); x.stroke(); };
  const H = c.height;
  for (const yy of [0, H]) for (const xx of [0, N]) ring(xx, yy);
  for (const xx of [-N / 2, N / 2, N * 1.5]) ring(xx, H / 2);
  MAILTILE.set(k, c); return c;
}
export function mailFill(g, s, base = PAL.mail) {
  // s = khoang cach vong (don vi logic hien tai)
  const m = g.getTransform(), sc = Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) || 1;
  const N = Math.max(4, Math.min(48, Math.round(s * sc)));
  if (s * sc < 3.2) return darker(base, 0.06);
  const p = g.createPattern(mailTile(N, base), 'repeat');
  p.setTransform(new DOMMatrix().scale(s / N));
  return p;
}
export function mailPattern(c, x, y, w, h, s, lw) {
  c.save(); c.fillStyle = mailFill(c, s * 0.55); c.fillRect(x - s, y - s, w + 2 * s, h + 2 * s); c.restore();
}
function kabutoBack(g, cx, cy, R, o) {
  // shikoro: phan che gay loe ra 2 ben, nhieu lop
  const lw = o.lw, col = o.lacing || PAL.red;
  for (let i = 3; i >= 0; i--) { const y = cy - R * 0.25 + i * R * 0.22, w = R * (1.25 + i * 0.12); shape(g, (c) => { c.moveTo(cx - w, y + R * 0.3); c.quadraticCurveTo(cx, y - R * 0.25, cx + w, y + R * 0.3); c.lineTo(cx + w * 0.95, y + R * 0.48); c.quadraticCurveTo(cx, y - R * 0.05, cx - w * 0.95, y + R * 0.48); c.closePath(); }, { fill: i % 2 ? col : PAL.black, lw: lw * 0.9 }); }
}
function steelDome(g, path, o, base = PAL.steel, dark = PAL.steelDark) {
  shape(g, path, { fill: base, lw: o.lw, inner: (c) => {
    const b = c.canvas ? null : null; // eslint
    c.fillStyle = alpha(dark, 0.6); c.fillRect(o.cx + o.R * 0.2, o.cy - o.R * 3, o.R * 3, o.R * 6);
    c.globalAlpha = 0.75; line(c, [[o.cx - o.R * 0.55, o.cy - o.R * 0.55], [o.cx - o.R * 0.25, o.cy - o.R * 0.92]], { lw: o.R * 0.1, ink: '#fff' }); c.globalAlpha = 1;
  } });
}
function helmetFront(g, cx, cy, R, hl, o) {
  const lw = o.lw, M = { ...o, cx, cy, R };
  const metal = o.metal || (['montefortino', 'attic'].includes(hl) ? PAL.bronze : PAL.steel), metalD = o.metalDark || (['montefortino', 'attic'].includes(hl) ? PAL.bronzeDark : PAL.steelDark);
  switch (hl) {
    case 'coif': coifFront(g, cx, cy, R, o); break;
    case 'nasal': {
      coifFront(g, cx, cy, R, o);
      steelDome(g, (c) => { c.moveTo(cx - R * 1.06, cy - R * 0.22); c.bezierCurveTo(cx - R * 0.95, cy - R * 0.9, cx - R * 0.3, cy - R * 1.35, cx, cy - R * 1.62); c.bezierCurveTo(cx + R * 0.3, cy - R * 1.35, cx + R * 0.95, cy - R * 0.9, cx + R * 1.06, cy - R * 0.22); c.closePath(); }, M, metal, metalD);
      rect(g, cx - R * 1.1, cy - R * 0.4, R * 2.2, R * 0.24, { fill: o.band || PAL.gold, lw, r: R * 0.06 });
      rect(g, cx - R * 0.08, cy - R * 0.2, R * 0.16, R * 0.5, { fill: metal, lw: lw * 0.85, r: R * 0.05 });
      if (o.knob !== false) circ(g, cx, cy - R * 1.6, R * 0.08, { fill: o.band || PAL.gold, lw: lw * 0.8 });
      break;
    }
    case 'spangen': { // mu chop co nan vang (William)
      coifFront(g, cx, cy, R, o);
      steelDome(g, (c) => { c.moveTo(cx - R * 1.15, cy - R * 0.3); c.bezierCurveTo(cx - R * 1.05, cy - R * 1.1, cx - R * 0.3, cy - R * 1.4, cx, cy - R * 1.55); c.bezierCurveTo(cx + R * 0.3, cy - R * 1.4, cx + R * 1.05, cy - R * 1.1, cx + R * 1.15, cy - R * 0.3); c.closePath(); }, M);
      for (const s of [-0.55, 0, 0.55]) line(g, [[cx + s * R * 0.25, cy - R * 1.5], [cx + s * R * 1.5, cy - R * 0.35]], { lw: R * 0.12, ink: PAL.gold });
      rect(g, cx - R * 1.2, cy - R * 0.45, R * 2.4, R * 0.24, { fill: PAL.gold, lw, r: R * 0.06 });
      for (let i = -2; i <= 2; i++) rect(g, cx + i * R * 0.42 - R * 0.05, cy - R * 0.38, R * 0.1, R * 0.1, { fill: i % 2 ? PAL.blue : PAL.red, lw: 0, r: 2 });
      circ(g, cx, cy - R * 1.55, R * 0.1, { fill: PAL.gold, lw: lw * 0.8 });
      break;
    }
    case 'bucket': { // mu thung (great helm)
      shape(g, (c) => c.roundRect(cx - R * 1.06, cy - R * 1.12, R * 2.12, R * 2.15, [R * 0.5, R * 0.5, R * 0.18, R * 0.18]), { fill: metal, lw, inner: (c) => {
        c.fillStyle = alpha(metalD, 0.55); c.fillRect(cx + R * 0.35, cy - R * 2, R * 2, R * 4);
        c.globalAlpha = 0.7; line(c, [[cx - R * 0.7, cy + R * 0.5], [cx - R * 0.7, cy - R * 0.7]], { lw: R * 0.1, ink: '#fff' }); c.globalAlpha = 1;
      } });
      rect(g, cx - R * 0.95, cy - R * 0.2, R * 0.82, R * 0.2, { fill: OUT, lw: 0, r: R * 0.08 }); rect(g, cx + R * 0.13, cy - R * 0.2, R * 0.82, R * 0.2, { fill: OUT, lw: 0, r: R * 0.08 });
      const lk = (o.look || 0) * R * 0.1; circ(g, cx - R * 0.5 + lk, cy - R * 0.1, R * 0.07, { fill: '#fff', lw: 0 }); circ(g, cx + R * 0.55 + lk, cy - R * 0.1, R * 0.07, { fill: '#fff', lw: 0 });
      rect(g, cx - R * 0.08, cy - R * 0.25, R * 0.16, R * 1.15, { fill: o.cross || metal, lw: lw * 0.7, r: R * 0.04 });
      for (let i = 0; i < 6; i++) circ(g, cx + R * (0.35 + (i % 3) * 0.18), cy + R * (0.35 + Math.floor(i / 3) * 0.2), R * 0.04, { fill: OUT, lw: 0 });
      break;
    }
    case 'bascinet': { // mu tron co mat na lat (visor 'up' | 'down'), bevor che cam
      steelDome(g, (c) => { c.moveTo(cx - R * 1.12, cy + R * 0.35); c.bezierCurveTo(cx - R * 1.25, cy - R * 0.9, cx - R * 0.6, cy - R * 1.42, cx + R * 0.05, cy - R * 1.38); c.bezierCurveTo(cx + R * 0.8, cy - R * 1.32, cx + R * 1.25, cy - R * 0.8, cx + R * 1.12, cy + R * 0.35); c.lineTo(cx + R * 0.86, cy + R * 0.3); c.bezierCurveTo(cx + R * 0.9, cy - R * 0.55, cx + R * 0.4, cy - R * 0.72, cx, cy - R * 0.72); c.bezierCurveTo(cx - R * 0.4, cy - R * 0.72, cx - R * 0.9, cy - R * 0.55, cx - R * 0.86, cy + R * 0.3); c.closePath(); }, M);
      if (o.bevor !== false) shape(g, (c) => { c.moveTo(cx - R * 0.95, cy + R * 0.18); c.lineTo(cx + R * 0.95, cy + R * 0.18); c.quadraticCurveTo(cx + R * 1.0, cy + R * 1.0, cx, cy + R * 1.08); c.quadraticCurveTo(cx - R * 1.0, cy + R * 1.0, cx - R * 0.95, cy + R * 0.18); }, { fill: metal, lw, inner: (c) => { c.fillStyle = alpha(metalD, 0.5); c.fillRect(cx + R * 0.3, cy, R, R * 1.2); line(c, [[cx - R * 0.95, cy + R * 0.42], [cx + R * 0.95, cy + R * 0.42]], { lw: lw * 0.6 }); for (let i = 0; i < 4; i++) circ(c, cx + R * (0.15 + i * 0.13), cy + R * 0.7, R * 0.035, { fill: OUT, lw: 0 }); } });
      if (o.visor === 'down') {
        shape(g, (c) => { c.moveTo(cx - R * 0.9, cy - R * 0.55); c.quadraticCurveTo(cx, cy - R * 0.85, cx + R * 0.9, cy - R * 0.55); c.lineTo(cx + R * 0.95, cy + R * 0.3); c.quadraticCurveTo(cx + R * 0.3, cy + R * 0.5, cx, cy + R * 0.75); c.quadraticCurveTo(cx - R * 0.3, cy + R * 0.5, cx - R * 0.95, cy + R * 0.3); c.closePath(); }, { fill: metal, lw, inner: (c) => { c.fillStyle = alpha(metalD, 0.5); c.fillRect(cx + R * 0.25, cy - R, R, R * 2); } });
        rect(g, cx - R * 0.78, cy - R * 0.2, R * 0.6, R * 0.12, { fill: OUT, lw: 0, r: R * 0.05 }); rect(g, cx + R * 0.18, cy - R * 0.2, R * 0.6, R * 0.12, { fill: OUT, lw: 0, r: R * 0.05 });
        for (let i = 0; i < 5; i++) circ(g, cx + R * (0.15 + (i % 2) * 0.14), cy + R * (0.12 + i * 0.07), R * 0.03, { fill: OUT, lw: 0 });
      } else if (o.visor !== 'none') {
        // mat na lat len tren dinh (hinh so 8 dung)
        g.save(); g.translate(cx + R * 0.42, cy - R * 1.08); g.rotate(-0.22);
        shape(g, (c) => c.roundRect(-R * 0.46, -R * 0.62, R * 0.92, R * 1.0, [R * 0.4, R * 0.4, R * 0.25, R * 0.25]), { fill: lighter(metal, 0.08), lw, inner: (c) => { c.fillStyle = alpha(metalD, 0.45); c.fillRect(R * 0.12, -R, R, R * 2); } });
        rect(g, -R * 0.12, -R * 0.45, R * 0.24, R * 0.3, { fill: OUT, lw: 0, r: R * 0.1 }); rect(g, -R * 0.12, -R * 0.08, R * 0.24, R * 0.3, { fill: OUT, lw: 0, r: R * 0.1 });
        for (let i = 0; i < 6; i++) circ(g, R * (0.26 + (i % 2) * 0.09), -R * 0.1 + Math.floor(i / 2) * R * 0.1, R * 0.025, { fill: OUT, lw: 0 });
        g.restore();
        circ(g, cx + R * 0.92, cy - R * 0.45, R * 0.07, { fill: PAL.gold, lw: lw * 0.7 });
      }
      if (o.plume) { const pc = o.plume === true ? PAL.blue : o.plume; shape(g, (c) => { c.moveTo(cx + R * 0.1, cy - R * 1.32); c.quadraticCurveTo(cx - R * 0.2, cy - R * 2.1, cx - R * 0.8, cy - R * 2.0); c.quadraticCurveTo(cx - R * 0.25, cy - R * 1.75, cx - R * 0.08, cy - R * 1.35); }, { fill: pc, lw: lw * 0.8 }); }
      break;
    }
    case 'kettle': {
      steelDome(g, (c) => { c.moveTo(cx - R * 0.95, cy - R * 0.42); c.bezierCurveTo(cx - R * 0.95, cy - R * 1.35, cx + R * 0.95, cy - R * 1.35, cx + R * 0.95, cy - R * 0.42); c.closePath(); }, M);
      shape(g, (c) => c.ellipse(cx, cy - R * 0.4, R * 1.55, R * 0.22, 0, 0, Math.PI * 2), { fill: lighter(metal, 0.05), lw });
      line(g, [[cx - R * 0.95, cy - R * 0.62], [cx + R * 0.95, cy - R * 0.62]], { lw: lw * 0.6 });
      break;
    }
    case 'sallet': {
      steelDome(g, (c) => { c.moveTo(cx - R * 1.1, cy + R * 0.1); c.bezierCurveTo(cx - R * 1.2, cy - R * 1.3, cx + R * 1.1, cy - R * 1.4, cx + R * 1.2, cy - R * 0.2); c.lineTo(cx + R * 1.5, cy + R * 0.25); c.lineTo(cx + R * 1.0, cy + R * 0.2); c.lineTo(cx + R * 0.95, cy - R * 0.1); c.lineTo(cx - R * 0.95, cy - R * 0.1); c.closePath(); }, M);
      rect(g, cx - R * 0.8, cy - R * 0.28, R * 1.6, R * 0.1, { fill: OUT, lw: 0, r: 3 });
      break;
    }
    case 'crown': {
      const y = cy - R * 0.78, w = R * 0.85;
      shape(g, (c) => { c.moveTo(cx - w, y + R * 0.2); c.lineTo(cx - w, y - R * 0.28); c.lineTo(cx - w * 0.6, y - R * 0.05); c.lineTo(cx - w * 0.3, y - R * 0.42); c.lineTo(cx, y - R * 0.08); c.lineTo(cx + w * 0.3, y - R * 0.42); c.lineTo(cx + w * 0.6, y - R * 0.05); c.lineTo(cx + w, y - R * 0.28); c.lineTo(cx + w, y + R * 0.2); c.closePath(); }, { fill: PAL.gold, lw, inner: (c) => { c.fillStyle = alpha(PAL.goldDark, 0.6); c.fillRect(cx + w * 0.3, y - R, w, R * 1.5); } });
      for (const s of [-0.5, 0, 0.5]) circ(g, cx + s * w, y + R * 0.02, R * 0.07, { fill: s ? PAL.blue : PAL.red, lw: lw * 0.5 });
      break;
    }
    case 'montefortino': case 'attic': {
      const att = hl === 'attic';
      // ma che hai ben (cheek guards)
      for (const s of [-1, 1]) { g.save(); shape(g, (c) => { c.moveTo(cx + s * R * 0.78, cy - R * 0.15); c.quadraticCurveTo(cx + s * R * 1.12, cy + R * 0.1, cx + s * R * 0.95, cy + R * 0.62); c.quadraticCurveTo(cx + s * R * 0.75, cy + R * 0.55, cx + s * R * 0.62, cy + R * 0.1); c.closePath(); }, { fill: metal, lw }); for (let i = 0; i < 3; i++) circ(g, cx + s * R * (0.84 - i * 0.03), cy + R * (0.0 + i * 0.18), R * 0.055, { fill: lighter(metal, 0.1), lw: lw * 0.55 }); g.restore(); }
      steelDome(g, (c) => { c.moveTo(cx - R * 1.06, cy - R * 0.12); c.bezierCurveTo(cx - R * 1.08, cy - R * 1.32, cx + R * 1.08, cy - R * 1.32, cx + R * 1.06, cy - R * 0.12); c.quadraticCurveTo(cx, cy - R * 0.32, cx - R * 1.06, cy - R * 0.12); c.closePath(); }, M, metal, metalD);
      shape(g, (c) => { c.moveTo(cx - R * 1.12, cy - R * 0.08); c.quadraticCurveTo(cx, cy - R * 0.36, cx + R * 1.12, cy - R * 0.08); c.lineTo(cx + R * 1.12, cy + R * 0.02); c.quadraticCurveTo(cx, cy - R * 0.24, cx - R * 1.12, cy + R * 0.02); c.closePath(); }, { fill: lighter(metal, 0.08), lw: lw * 0.85 });
      if (!att) { rect(g, cx - R * 0.07, cy - R * 1.32, R * 0.14, R * 0.18, { fill: metal, lw: lw * 0.8, r: 2 }); circ(g, cx, cy - R * 1.36, R * 0.12, { fill: metal, lw: lw * 0.8 }); }
      const fe = o.feathers ?? (att ? 0 : 0);
      for (let i = 0; i < fe; i++) { const s = i - (fe - 1) / 2, base = [cx + s * R * 0.32, cy - R * 0.98 + Math.abs(s) * R * 0.08]; feather(g, base[0], base[1], R * (1.0 - Math.abs(s) * 0.1), s * 0.35, (o.featherColors || [PAL.white, OUT, PAL.white])[i % 3], lw); }
      if (att || o.crest) { const cc = o.crest && o.crest !== true ? o.crest : PAL.red; shape(g, (c) => { c.moveTo(cx - R * 1.0, cy - R * 0.7); c.bezierCurveTo(cx - R * 0.8, cy - R * 2.0, cx + R * 0.9, cy - R * 2.05, cx + R * 1.25, cy - R * 0.55); c.quadraticCurveTo(cx + R * 0.6, cy - R * 1.25, cx - R * 1.0, cy - R * 0.7); }, { fill: cc, lw, inner: (c) => { c.strokeStyle = alpha(OUT, 0.35); c.lineWidth = lw * 0.4; for (let i = 0; i < 9; i++) { c.beginPath(); c.moveTo(cx - R * 0.8 + i * R * 0.22, cy - R * 1.75); c.lineTo(cx - R * 0.7 + i * R * 0.24, cy - R * 0.9); c.stroke(); } } }); }
      break;
    }
    case 'kabuto': {
      steelDome(g, (c) => { c.moveTo(cx - R * 1.08, cy - R * 0.28); c.bezierCurveTo(cx - R * 1.1, cy - R * 1.35, cx + R * 1.1, cy - R * 1.35, cx + R * 1.08, cy - R * 0.28); c.closePath(); }, M, PAL.black, '#1a1514');
      for (let i = -3; i <= 3; i++) line(g, [[cx + i * R * 0.12, cy - R * 1.12], [cx + i * R * 0.3, cy - R * 0.35]], { lw: lw * 0.4, ink: '#5a5050' });
      rect(g, cx - R * 1.14, cy - R * 0.42, R * 2.28, R * 0.2, { fill: o.lacing || PAL.red, lw: lw * 0.9, r: R * 0.05 });
      // kuwagata (sung vang chu V)
      for (const s of [-1, 1]) shape(g, (c) => { c.moveTo(cx + s * R * 0.08, cy - R * 0.5); c.quadraticCurveTo(cx + s * R * 0.75, cy - R * 1.2, cx + s * R * 0.55, cy - R * 2.1); c.quadraticCurveTo(cx + s * R * 0.55, cy - R * 1.2, cx + s * R * 0.0, cy - R * 0.55); c.closePath(); }, { fill: PAL.gold, lw: lw * 0.9 });
      circ(g, cx, cy - R * 0.5, R * 0.13, { fill: PAL.gold, lw: lw * 0.8 });
      break;
    }
    case 'jingasa': {
      shape(g, (c) => { c.moveTo(cx - R * 1.45, cy - R * 0.38); c.quadraticCurveTo(cx, cy - R * 1.55, cx + R * 1.45, cy - R * 0.38); c.quadraticCurveTo(cx, cy - R * 0.62, cx - R * 1.45, cy - R * 0.38); }, { fill: o.metal || PAL.black, lw });
      circ(g, cx, cy - R * 0.85, R * 0.16, { fill: PAL.gold, lw: lw * 0.6 });
      break;
    }
    case 'm1': case 'brodie': {
      const brim = hl === 'brodie' ? 1.5 : 1.22;
      shape(g, (c) => { c.moveTo(cx - R * brim, cy - R * 0.28); c.bezierCurveTo(cx - R * 1.15, cy - R * 1.45, cx + R * 1.15, cy - R * 1.45, cx + R * brim, cy - R * 0.28); c.quadraticCurveTo(cx, cy - R * 0.5, cx - R * brim, cy - R * 0.28); }, { fill: o.metal || PAL.camo1, lw, inner: (c) => {
        if (o.camo !== false) { const sp = [[-0.6, -0.8, 0.28], [0.1, -1.05, 0.24], [0.55, -0.6, 0.3], [-0.2, -0.55, 0.2], [0.85, -0.9, 0.18], [-0.95, -0.45, 0.18]]; sp.forEach(([a, b, r], i) => ellipse(c, cx + a * R, cy + b * R, r * R, r * R * 0.7, { fill: [PAL.camo2, PAL.camo3, '#7a5a3a'][i % 3], lw: 0, rot: i })); }
        c.fillStyle = alpha('#000', 0.18); c.fillRect(cx + R * 0.35, cy - R * 2, R * 2, R * 3);
      } });
      if (o.net) { g.save(); g.strokeStyle = alpha(OUT, 0.4); g.lineWidth = lw * 0.3; for (let i = -4; i <= 4; i++) { g.beginPath(); g.moveTo(cx + i * R * 0.25 - R * 0.4, cy - R * 1.2); g.lineTo(cx + i * R * 0.25 + R * 0.4, cy - R * 0.35); g.stroke(); } g.restore(); }
      break;
    }
    case 'cap': case 'kepi': case 'peaked': case 'sailor': {
      const col = o.capColor || (hl === 'sailor' ? PAL.white : PAL.olive);
      if (hl === 'peaked') {
        shape(g, (c) => { c.moveTo(cx - R * 1.0, cy - R * 0.55); c.quadraticCurveTo(cx - R * 1.3, cy - R * 1.25, cx, cy - R * 1.28); c.quadraticCurveTo(cx + R * 1.3, cy - R * 1.25, cx + R * 1.0, cy - R * 0.55); c.closePath(); }, { fill: col, lw });
        rect(g, cx - R * 0.98, cy - R * 0.72, R * 1.96, R * 0.24, { fill: o.band || PAL.red, lw: lw * 0.85, r: R * 0.05 });
        shape(g, (c) => { c.moveTo(cx - R * 0.95, cy - R * 0.5); c.quadraticCurveTo(cx, cy - R * 0.2, cx + R * 0.95, cy - R * 0.5); c.quadraticCurveTo(cx, cy - R * 0.4, cx - R * 0.95, cy - R * 0.5); }, { fill: PAL.black, lw: lw * 0.85 });
        circ(g, cx, cy - R * 0.85, R * 0.12, { fill: o.badge || PAL.gold, lw: lw * 0.6 });
      } else if (hl === 'sailor') {
        shape(g, (c) => c.ellipse(cx, cy - R * 0.9, R * 0.95, R * 0.32, 0, 0, Math.PI * 2), { fill: col, lw });
        rect(g, cx - R * 0.72, cy - R * 0.92, R * 1.44, R * 0.36, { fill: col, lw: lw * 0.85, r: R * 0.12 });
        rect(g, cx - R * 0.72, cy - R * 0.72, R * 1.44, R * 0.14, { fill: o.band || PAL.navy, lw: lw * 0.6, r: 2 });
      } else {
        // mu luoi trai mem / sajkaca
        shape(g, (c) => { c.moveTo(cx - R * 1.02, cy - R * 0.42); c.bezierCurveTo(cx - R * 1.0, cy - R * 1.3, cx + R * 1.1, cy - R * 1.32, cx + R * 1.05, cy - R * 0.42); c.closePath(); }, { fill: col, lw, inner: (c) => { c.fillStyle = alpha('#000', 0.15); c.fillRect(cx + R * 0.3, cy - R * 2, R * 2, R * 2); } });
        shape(g, (c) => { c.moveTo(cx - R * 1.05, cy - R * 0.45); c.quadraticCurveTo(cx - R * 0.2, cy - R * 0.18, cx + R * 1.3, cy - R * 0.36); c.quadraticCurveTo(cx, cy - R * 0.62, cx - R * 1.05, cy - R * 0.45); }, { fill: darker(col, 0.1), lw: lw * 0.85 });
        circ(g, cx, cy - R * 0.8, R * 0.13, { fill: o.badge || '#e3e0d5', lw: lw * 0.6, inner: (c) => circ(c, cx, cy - R * 0.8, R * 0.07, { fill: o.badge2 || PAL.red, lw: 0 }) });
      }
      break;
    }
    case 'riot': case 'riotDown': {
      steelDome(g, (c) => { c.moveTo(cx - R * 1.1, cy + R * 0.15); c.bezierCurveTo(cx - R * 1.2, cy - R * 1.35, cx + R * 1.2, cy - R * 1.35, cx + R * 1.1, cy + R * 0.15); c.closePath(); }, M, PAL.navy, '#1d2338');
      shape(g, (c) => c.roundRect(cx - R * 0.95, cy - R * 0.5, R * 1.9, R * (hl === 'riotDown' ? 1.3 : 0.4), R * 0.2), { fill: alpha('#cfe4f2', 0.45), lw: lw * 0.8 });
      break;
    }
    case 'turban': {
      blob(g, [[cx - R * 1.05, cy - R * 0.3], [cx - R * 0.95, cy - R * 1.05], [cx, cy - R * 1.35], [cx + R * 0.95, cy - R * 1.05], [cx + R * 1.05, cy - R * 0.3], [cx, cy - R * 0.5]], { fill: o.capColor || PAL.white, lw });
      line(g, [[cx - R * 0.9, cy - R * 0.6], [cx + R * 0.2, cy - R * 1.2]], { lw: lw * 0.5 }); line(g, [[cx - R * 0.6, cy - R * 0.45], [cx + R * 0.8, cy - R * 0.95]], { lw: lw * 0.5 });
      break;
    }
  }
}
function feather(g, x, y, L, rot, col, lw) {
  g.save(); g.translate(x, y); g.rotate(rot);
  shape(g, (c) => { c.moveTo(0, 0); c.bezierCurveTo(-L * 0.22, -L * 0.35, -L * 0.18, -L * 0.8, 0, -L * 1.05); c.bezierCurveTo(L * 0.18, -L * 0.8, L * 0.22, -L * 0.35, 0, 0); }, { fill: col, lw: lw * 0.8 });
  line(g, [[0, -L * 0.05], [0, -L * 0.9]], { lw: lw * 0.4, ink: col === OUT ? '#6b605a' : alpha(OUT, 0.5) });
  g.restore();
}

// ====================================================================================== HUY HIEU
// charge: lion | fleur | cross | crossW | stripe | chevron | quarter | star | eagle | bars | lightning | wings | spqr | rose | none
export function charge(g, kind, x, y, s, col, col2, lw = 3) {
  if (!kind || kind === 'none') return;
  g.save(); g.translate(x, y);
  switch (kind) {
    case 'lion': {
      // su tu dung (rampant): bom tua gai, 2 chan truoc gio vuot, duoi cong chu S co chom long
      g.scale(s / 100, s / 100); const L = lw * 100 / s * 0.6, dk = darker(col, 0.18);
      tube(g, [[12, 16], [30, 10], [36, -8], [30, -22]], 5, col, L * 0.8);
      blob(g, [[30, -22], [36, -30], [27, -36], [22, -28], [26, -22]], { fill: col, lw: L * 0.8 });
      tube(g, [[6, 22], [-2, 34], [-12, 42]], 9, col, L * 0.8); tube(g, [[12, 20], [18, 34], [10, 44]], 9, dk, L * 0.8);
      blob(g, [[-6, -12], [8, -12], [17, 2], [14, 20], [4, 26], [-6, 18], [-9, 2]], { fill: col, lw: L });
      tube(g, [[0, -6], [-16, 2], [-26, -4]], 7.5, dk, L * 0.8); tube(g, [[-4, -10], [-20, -16], [-28, -26]], 8, col, L * 0.8);
      for (const [x, y] of [[-28, -26], [-26, -4], [-12, 42], [10, 44]]) circ(g, x, y, 4.6, { fill: col, lw: L * 0.7 });
      const mp = []; for (let i = 0; i < 18; i++) { const an = i / 18 * Math.PI * 2, r = i % 2 ? 12 : 17; mp.push([-10 + Math.cos(an) * r, -28 + Math.sin(an) * r]); }
      polyS(g, mp, { fill: dk, lw: L * 0.8 });
      circ(g, -11, -28, 9.5, { fill: col, lw: L * 0.8 });
      polyS(g, [[-20, -26], [-12, -24], [-19, -20]], { fill: '#5a1a14', lw: L * 0.5 });
      circ(g, -12, -32, 1.8, { fill: OUT, lw: 0 });
      break;
    }
    case 'fleur': {
      g.scale(s / 100, s / 100); const L = lw * 100 / s * 0.6;
      blob(g, [[0, -46], [12, -24], [6, 6], [0, 12], [-6, 6], [-12, -24]], { fill: col, lw: L });
      for (const k of [-1, 1]) blob(g, [[k * 4, 4], [k * 26, -6], [k * 40, -24], [k * 34, 6], [k * 16, 18]], { fill: col, lw: L });
      rect(g, -22, 10, 44, 9, { fill: col, lw: L, r: 3 });
      polyS(g, [[-6, 19], [6, 19], [3, 40], [-3, 40]], { fill: col, lw: L });
      break;
    }
    case 'cross': rect(g, -s * 0.12, -s * 0.48, s * 0.24, s * 0.96, { fill: col, lw: 0, r: 1 }); rect(g, -s * 0.48, -s * 0.12, s * 0.96, s * 0.24, { fill: col, lw: 0, r: 1 }); break;
    case 'crossW': rect(g, -s * 0.12, -s * 2, s * 0.24, s * 4, { fill: col, lw: 0, r: 0 }); rect(g, -s * 2, -s * 0.12, s * 4, s * 0.24, { fill: col, lw: 0, r: 0 }); break;
    case 'stripe': g.rotate(-0.6); rect(g, -s * 2, -s * 0.15, s * 4, s * 0.3, { fill: col, lw: 0, r: 0 }); break;
    case 'bars': for (let i = -1; i <= 1; i++) rect(g, -s * 2, i * s * 0.32 - s * 0.08, s * 4, s * 0.16, { fill: col, lw: 0, r: 0 }); break;
    case 'chevron': g.lineWidth = s * 0.22; g.strokeStyle = col; g.beginPath(); g.moveTo(-s * 0.9, s * 0.35); g.lineTo(0, -s * 0.3); g.lineTo(s * 0.9, s * 0.35); g.stroke(); break;
    case 'quarter': g.fillStyle = col; g.fillRect(-s * 2, -s * 2, s * 2, s * 2); g.fillRect(0, 0, s * 2, s * 2); break;
    case 'star': { g.beginPath(); for (let i = 0; i < 10; i++) { const r = i % 2 ? s * 0.2 : s * 0.46, a = -Math.PI / 2 + i * Math.PI / 5; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.closePath(); g.fillStyle = col; g.fill(); break; }
    case 'eagle': { g.scale(s / 100, s / 100); const L = lw * 100 / s * 0.6; blob(g, [[0, -30], [10, -20], [8, 10], [0, 30], [-8, 10], [-10, -20]], { fill: col, lw: L }); for (const k of [-1, 1]) blob(g, [[k * 6, -12], [k * 44, -34], [k * 40, -6], [k * 30, 10], [k * 8, 6]], { fill: col, lw: L }); circ(g, 0, -34, 9, { fill: col, lw: L }); break; }
    case 'lightning': { g.scale(s / 100, s / 100); const L = lw * 100 / s * 0.6; polyS(g, [[-8, -44], [10, -44], [2, -8], [16, -8], [-10, 44], [-2, 4], [-16, 4]], { fill: col, lw: L }); break; }
    case 'wings': { g.scale(s / 100, s / 100); const L = lw * 100 / s * 0.6; for (const k of [-1, 1]) blob(g, [[k * 4, 0], [k * 40, -26], [k * 46, -6], [k * 34, 12], [k * 10, 10]], { fill: col, lw: L }); circ(g, 0, 2, 9, { fill: col2 || col, lw: L }); break; }
    case 'boss': circ(g, 0, 0, s * 0.22, { fill: col, lw }); break;
    case 'rose': for (let i = 0; i < 5; i++) { const a = i * Math.PI * 0.4; circ(g, Math.cos(a) * s * 0.18, Math.sin(a) * s * 0.18, s * 0.16, { fill: col, lw: lw * 0.6 }); } circ(g, 0, 0, s * 0.1, { fill: PAL.gold, lw: lw * 0.6 }); break;
    case 'sun': for (let i = 0; i < 12; i++) { g.save(); g.rotate(i * Math.PI / 6); polyS(g, [[0, -s * 0.46], [s * 0.07, -s * 0.22], [-s * 0.07, -s * 0.22]], { fill: col, lw: 0 }); g.restore(); } circ(g, 0, 0, s * 0.22, { fill: col, lw: 0 }); break;
    case 'circle': circ(g, 0, 0, s * 0.3, { fill: col, lw }); circ(g, 0, 0, s * 0.12, { fill: col2 || '#fff', lw: 0 }); break;
  }
  g.restore();
}

// ====================================================================================== KHIEN
// shield: { type: kite | heater | scutum | round | pavise | buckler | riot, color, color2, charge, chargeColor, rim, boss, arrows: N }
export function shield(g, x, y, s, o = {}) {
  const type = o.type || 'heater', col = o.color || PAL.red, lw = o.lw ?? Math.max(1.2, s * 0.035), rim = o.rim || PAL.gold;
  g.save(); g.translate(x, y); g.rotate(o.rot || 0); if (o.flip) g.scale(-1, 1);
  const P = {
    kite: (c) => { c.moveTo(0, -s * 0.5); c.bezierCurveTo(s * 0.4, -s * 0.5, s * 0.36, -s * 0.05, 0, s * 0.62); c.bezierCurveTo(-s * 0.36, -s * 0.05, -s * 0.4, -s * 0.5, 0, -s * 0.5); },
    heater: (c) => { c.moveTo(-s * 0.36, -s * 0.42); c.lineTo(s * 0.36, -s * 0.42); c.bezierCurveTo(s * 0.38, s * 0.05, s * 0.2, s * 0.32, 0, s * 0.46); c.bezierCurveTo(-s * 0.2, s * 0.32, -s * 0.38, s * 0.05, -s * 0.36, -s * 0.42); },
    scutum: (c) => c.ellipse(0, 0, s * 0.33, s * 0.5, 0, 0, Math.PI * 2),
    round: (c) => c.arc(0, 0, s * 0.42, 0, Math.PI * 2),
    buckler: (c) => c.arc(0, 0, s * 0.22, 0, Math.PI * 2),
    pavise: (c) => { c.moveTo(-s * 0.3, -s * 0.5); c.lineTo(s * 0.3, -s * 0.5); c.lineTo(s * 0.34, s * 0.5); c.lineTo(-s * 0.34, s * 0.5); c.closePath(); },
    riot: (c) => c.roundRect(-s * 0.3, -s * 0.5, s * 0.6, s * 1.0, s * 0.08),
  }[type];
  if (o.back) { shape(g, P, { fill: o.backColor || PAL.wood, lw, inner: (c) => { for (let i = -3; i <= 3; i++) line(c, [[i * s * 0.1, -s], [i * s * 0.1, s]], { lw: lw * 0.4, a: 0.5 }); rect(c, -s * 0.06, -s * 0.2, s * 0.12, s * 0.4, { fill: PAL.leather, lw: lw * 0.6 }); } }); g.restore(); return; }
  shape(g, P, { fill: col, lw, inner: (c) => {
    if (o.charge) charge(c, o.charge, o.chargeX ?? 0, o.chargeY ?? (type === 'kite' ? -s * 0.08 : 0), (o.chargeS ?? 0.62) * s, o.chargeColor || PAL.yellow, o.color2, lw * 0.8);
    if (type === 'scutum') { rect(c, -s * 0.05, -s * 0.5, s * 0.1, s, { fill: darker(col, 0.12), lw: lw * 0.6, r: 0 }); }
    if (type === 'riot') { c.fillStyle = alpha('#fff', 0.25); c.fillRect(-s * 0.3, -s * 0.5, s * 0.6, s * 0.4); label(c, 'POLICE', 0, -s * 0.3, { size: s * 0.1, font: '"Be Vietnam Pro"', weight: 800, color: '#fff' }); }
    // bong cel
    c.fillStyle = alpha('#000', 0.14); c.beginPath(); c.ellipse(s * 0.45, 0, s * 0.38, s * 0.8, 0, 0, Math.PI * 2); c.fill();
    c.globalAlpha = 0.55; line(c, [[-s * 0.22, -s * 0.3], [-s * 0.26, -s * 0.05]], { lw: lw * 1.2, ink: '#fff' }); c.globalAlpha = 1;
  } });
  if (o.rim !== false && (type === 'scutum' || type === 'round' || o.rimLine)) { g.save(); g.beginPath(); P(g); g.lineWidth = lw * 2.2; g.strokeStyle = rim; g.stroke(); g.lineWidth = lw; g.strokeStyle = OUT; g.stroke(); g.restore(); }
  if (o.boss || type === 'round' || type === 'scutum') circ(g, 0, 0, s * (type === 'scutum' ? 0.09 : 0.08), { fill: o.bossColor || PAL.steelLight, lw: lw * 0.8 });
  for (let i = 0; i < (o.arrows || 0); i++) { const ax = (noise(i * 3.1) * 0.4) * s, ay = (noise(i * 7.7) * 0.5) * s; arrowStuck(g, ax, ay, s * 0.45, -0.6 + noise(i) * 0.5, lw); }
  g.restore();
}
export function arrowStuck(g, x, y, L, rot, lw) {
  g.save(); g.translate(x, y); g.rotate(rot);
  line(g, [[0, 0], [-L, 0]], { lw: lw * 1.6, ink: OUT }); line(g, [[0, 0], [-L, 0]], { lw: lw * 0.7, ink: PAL.wood });
  polyS(g, [[-L, 0], [-L - L * 0.18, -L * 0.1], [-L - L * 0.1, 0], [-L - L * 0.18, L * 0.1]], { fill: PAL.white, lw: lw * 0.5 });
  g.restore();
}

// ====================================================================================== VU KHI
// weapon: sword | spear | pilum | pollaxe | axe | mace | bow | crossbow | lance | rifle | pistol | katana | naginata | flag | torch | staff | hammer | dagger | none
export function weapon(g, kind, hx, hy, L, ang, o = {}) {
  if (!kind || kind === 'none') return;
  const lw = o.lw ?? Math.max(1.2, L * 0.02);
  g.save(); g.translate(hx, hy); g.rotate(ang); // truc +y = huong luoi (tu tay di ra)
  const shaft = (a, b, w, col = PAL.wood) => tube(g, [[0, a], [0, b]], w, col, lw);
  switch (kind) {
    case 'sword': case 'katana': case 'dagger': {
      const l = kind === 'dagger' ? L * 0.45 : L, kat = kind === 'katana';
      shaft(-l * 0.18, l * 0.02, l * 0.06, kat ? PAL.black : PAL.leather);
      rect(g, kat ? -l * 0.07 : -l * 0.16, l * 0.0, kat ? l * 0.14 : l * 0.32, l * 0.05, { fill: PAL.gold, lw: lw * 0.8, r: l * 0.02 });
      shape(g, (c) => { c.moveTo(-l * 0.045, l * 0.05); c.lineTo(l * 0.045, l * 0.05); c.lineTo(l * (kat ? 0.035 : 0.04), l * 0.92); c.lineTo(0, l * 1.0); c.lineTo(-l * 0.04, l * 0.92); c.closePath(); }, { fill: PAL.steelLight, lw: lw * 0.9, inner: (c) => line(c, [[0, l * 0.1], [0, l * 0.9]], { lw: lw * 0.4, a: 0.4 }) });
      circ(g, 0, -l * 0.2, l * 0.045, { fill: PAL.gold, lw: lw * 0.7 });
      break;
    }
    case 'spear': case 'pilum': case 'lance': case 'naginata': case 'pike': {
      const back = kind === 'lance' ? L * 0.25 : L * 0.35, front = kind === 'pike' ? L * 1.6 : L;
      shaft(-back, front * 0.86, kind === 'lance' ? L * 0.06 : L * 0.035, kind === 'lance' ? (o.color || PAL.white) : PAL.wood);
      if (kind === 'pilum') { tube(g, [[0, front * 0.62], [0, front * 0.95]], L * 0.016, PAL.steel, lw * 0.8); polyS(g, [[0, front * 1.02], [-L * 0.025, front * 0.94], [L * 0.025, front * 0.94]], { fill: PAL.steelLight, lw: lw * 0.7 }); }
      else if (kind === 'naginata') shape(g, (c) => { c.moveTo(-L * 0.02, front * 0.84); c.quadraticCurveTo(L * 0.09, front * 0.95, L * 0.02, front * 1.12); c.lineTo(-L * 0.03, front * 0.86); c.closePath(); }, { fill: PAL.steelLight, lw: lw * 0.8 });
      else if (kind === 'lance') { polyS(g, [[0, front], [-L * 0.03, front * 0.88], [L * 0.03, front * 0.88]], { fill: PAL.steel, lw: lw * 0.8 }); shape(g, (c) => { c.moveTo(-L * 0.08, L * 0.08); c.lineTo(L * 0.08, L * 0.08); c.lineTo(L * 0.035, L * 0.3); c.lineTo(-L * 0.035, L * 0.3); c.closePath(); }, { fill: o.color || PAL.white, lw: lw * 0.8 }); }
      else shape(g, (c) => { c.moveTo(0, front * 1.02); c.quadraticCurveTo(L * 0.05, front * 0.92, L * 0.02, front * 0.84); c.lineTo(-L * 0.02, front * 0.84); c.quadraticCurveTo(-L * 0.05, front * 0.92, 0, front * 1.02); }, { fill: PAL.steelLight, lw: lw * 0.8 });
      if (o.pennant) { polyS(g, [[0, front * 0.78], [L * 0.22, front * 0.74], [0, front * 0.66]], { fill: o.pennant, lw: lw * 0.6 }); }
      break;
    }
    case 'pollaxe': case 'axe': case 'hammer': case 'mace': {
      const l = kind === 'pollaxe' ? L * 1.15 : L * 0.7;
      shaft(-l * 0.25, l * 0.9, L * 0.035, PAL.wood);
      if (kind === 'pollaxe' || kind === 'axe') shape(g, (c) => { c.moveTo(-L * 0.02, l * 0.68); c.quadraticCurveTo(-L * 0.24, l * 0.66, -L * 0.26, l * 0.84); c.quadraticCurveTo(-L * 0.2, l * 0.92, -L * 0.02, l * 0.86); c.closePath(); }, { fill: PAL.steelLight, lw: lw * 0.85 });
      if (kind === 'pollaxe' || kind === 'hammer') rect(g, L * 0.0, l * 0.71, L * 0.12, L * 0.09, { fill: PAL.steel, lw: lw * 0.8, r: 2 });
      if (kind === 'pollaxe') polyS(g, [[0, l * 1.05], [-L * 0.025, l * 0.88], [L * 0.025, l * 0.88]], { fill: PAL.steelLight, lw: lw * 0.7 });
      if (kind === 'mace') { circ(g, 0, l * 0.88, L * 0.09, { fill: PAL.steel, lw: lw * 0.8 }); }
      break;
    }
    case 'bow': {
      g.save(); g.lineCap = 'round';
      shape(g, (c) => { c.moveTo(-L * 0.6, 0); c.quadraticCurveTo(0, L * 0.45, L * 0.6, 0); }, { fill: null, lw: lw * 3.4, ink: OUT });
      shape(g, (c) => { c.moveTo(-L * 0.6, 0); c.quadraticCurveTo(0, L * 0.45, L * 0.6, 0); }, { fill: null, lw: lw * 1.6, ink: PAL.wood });
      line(g, [[-L * 0.6, 0], [L * 0.6, 0]], { lw: lw * 0.5, ink: '#efe6d0' });
      g.restore(); break;
    }
    case 'crossbow': {
      shaft(-L * 0.1, L * 0.55, L * 0.06, PAL.wood);
      shape(g, (c) => { c.moveTo(-L * 0.34, L * 0.38); c.quadraticCurveTo(0, L * 0.6, L * 0.34, L * 0.38); }, { fill: null, lw: lw * 2.5 });
      line(g, [[-L * 0.34, L * 0.38], [0, L * 0.3], [L * 0.34, L * 0.38]], { lw: lw * 0.5, ink: '#efe6d0' });
      break;
    }
    case 'rifle': case 'musket': case 'pistol': {
      const l = kind === 'pistol' ? L * 0.35 : L;
      shape(g, (c) => { c.moveTo(-l * 0.06, -l * 0.25); c.lineTo(l * 0.06, -l * 0.25); c.lineTo(l * 0.05, l * 0.25); c.lineTo(-l * 0.05, l * 0.3); c.closePath(); }, { fill: PAL.wood, lw: lw * 0.9 });
      tube(g, [[0, l * 0.2], [0, l * 0.95]], l * 0.035, PAL.black, lw * 0.8);
      if (o.bayonet) polyS(g, [[0, l * 1.15], [-l * 0.02, l * 0.95], [l * 0.02, l * 0.95]], { fill: PAL.steelLight, lw: lw * 0.6 });
      break;
    }
    case 'flag': case 'banner': {
      shaft(-L * 0.4, L * 1.2, L * 0.035, PAL.wood);
      g.save(); g.translate(0, L * 1.18); g.rotate(-Math.PI / 2);
      const fl = o.flag || {}, fw = L * 0.6, fh = L * 0.42, wv = Math.sin((o.t || 0) * 4) * L * 0.03;
      shape(g, (c) => { c.moveTo(0, 0); c.quadraticCurveTo(fw * 0.5, wv, fw, 0); c.lineTo(fw, fh); c.quadraticCurveTo(fw * 0.5, fh + wv, 0, fh); c.closePath(); }, { fill: fl.color || PAL.red, lw: lw * 0.8, inner: (c) => charge(c, fl.charge, fw / 2, fh / 2, fh * 0.6, fl.chargeColor || PAL.yellow, null, lw * 0.7) });
      g.restore(); circ(g, 0, L * 1.22, L * 0.04, { fill: PAL.gold, lw: lw * 0.6 });
      break;
    }
    case 'torch': {
      shaft(-L * 0.05, L * 0.4, L * 0.05, PAL.wood);
      const f = 1 + Math.sin((o.t || 0) * 13) * 0.08;
      shape(g, (c) => { c.moveTo(-L * 0.07, L * 0.42); c.quadraticCurveTo(-L * 0.1, L * 0.55 * f, 0, L * 0.68 * f); c.quadraticCurveTo(L * 0.1, L * 0.55 * f, L * 0.07, L * 0.42); c.closePath(); }, { fill: '#f6a43a', lw: lw * 0.7, inner: (c) => ellipse(c, 0, L * 0.47, L * 0.035, L * 0.08, { fill: '#ffe38a', lw: 0 }) });
      break;
    }
    case 'staff': shaft(-L * 0.3, L * 1.0, L * 0.04, PAL.wood); break;
    case 'shovel': case 'spade': { shaft(-L * 0.25, L * 0.72, L * 0.04, PAL.wood); rect(g, -L * 0.1, -L * 0.3, L * 0.2, L * 0.06, { fill: PAL.wood, lw: lw * 0.8, r: 2 }); shape(g, (c) => { c.moveTo(-L * 0.11, L * 0.7); c.lineTo(L * 0.11, L * 0.7); c.lineTo(L * 0.12, L * 0.95); c.quadraticCurveTo(0, L * 1.05, -L * 0.12, L * 0.95); c.closePath(); }, { fill: PAL.steel, lw: lw * 0.9, inner: (c) => line(c, [[-L * 0.06, L * 0.75], [-L * 0.06, L * 0.95]], { lw: lw * 0.6, ink: '#fff', a: 0.5 }) }); break; }
    case 'pickaxe': case 'dolabra': { shaft(-L * 0.25, L * 0.8, L * 0.04, PAL.wood); shape(g, (c) => { c.moveTo(-L * 0.3, L * 0.72); c.quadraticCurveTo(0, L * 0.82, L * 0.3, L * 0.7); c.lineTo(L * 0.28, L * 0.82); c.quadraticCurveTo(0, L * 0.9, -L * 0.24, L * 0.84); c.closePath(); }, { fill: PAL.steel, lw: lw * 0.9 }); break; }
    case 'saw': { rect(g, -L * 0.05, -L * 0.1, L * 0.1, L * 0.22, { fill: PAL.wood, lw, r: 2 }); shape(g, (c) => { c.moveTo(-L * 0.08, L * 0.12); c.lineTo(L * 0.08, L * 0.12); c.lineTo(L * 0.05, L * 0.75); c.lineTo(-L * 0.1, L * 0.75); c.closePath(); }, { fill: PAL.steelLight, lw: lw * 0.8 }); break; }
    case 'stake': shaft(-L * 0.4, L * 0.6, L * 0.06, PAL.wood); polyS(g, [[-L * 0.035, L * 0.6], [L * 0.035, L * 0.6], [0, L * 0.75]], { fill: PAL.wood, lw: lw * 0.8 }); break;
    case 'pot': { ellipse(g, 0, L * 0.25, L * 0.2, L * 0.16, { fill: PAL.bronze, lw }); line(g, [[-L * 0.18, L * 0.12], [0, -L * 0.02], [L * 0.18, L * 0.12]], { lw: lw * 0.8 }); break; }
    case 'basket': { shape(g, (c) => { c.moveTo(-L * 0.22, L * 0.05); c.lineTo(L * 0.22, L * 0.05); c.lineTo(L * 0.17, L * 0.4); c.lineTo(-L * 0.17, L * 0.4); c.closePath(); }, { fill: PAL.rope, lw, inner: (c) => { for (let i = 0; i < 4; i++) line(c, [[-L * 0.3, L * (0.1 + i * 0.09)], [L * 0.3, L * (0.1 + i * 0.09)]], { lw: lw * 0.5, a: 0.5 }); for (let i = -2; i <= 2; i++) line(c, [[i * L * 0.08, 0], [i * L * 0.07, L * 0.45]], { lw: lw * 0.5, a: 0.5 }); } }); break; }
    case 'scroll': { rect(g, -L * 0.18, 0, L * 0.36, L * 0.45, { fill: PAL.parchment, lw, r: 4, inner: (c) => { for (let i = 0; i < 4; i++) line(c, [[-L * 0.12, L * (0.1 + i * 0.08)], [L * 0.12, L * (0.1 + i * 0.08)]], { lw: lw * 0.4, a: 0.5 }); } }); break; }
    case 'pouch': { blob(g, [[-L * 0.14, 0], [L * 0.14, 0], [L * 0.2, L * 0.24], [0, L * 0.32], [-L * 0.2, L * 0.24]], { fill: PAL.leather, lw }); break; }
    case 'grenade': { ellipse(g, 0, L * 0.12, L * 0.1, L * 0.13, { fill: PAL.olive, lw, inner: (c) => { for (let i = -1; i <= 1; i++) line(c, [[-L, L * 0.12 + i * L * 0.06], [L, L * 0.12 + i * L * 0.06]], { lw: lw * 0.5, a: 0.5 }); } }); break; }
  }
  g.restore();
}

// ====================================================================================== THAN
// body: tunic | mail | plate | brig | gambeson | robe | toga | roman | samurai | uniform | sailor | suit | dress | apron | peasant | bare
// tabard: true -> ao choang huy hieu tren giap (mau tabard, charge)
export const POSES = {
  //          [vai trai, khuyu trai, vai phai, khuyu phai] do (0 = buong thang xuong, + = gio ra ngoai/len)
  stand:   [12, 6, 12, 6], idle: [10, 10, 14, 4], wave: [12, 6, 150, 25], point: [12, 6, 92, 0], pointUp: [12, 6, 150, -5],
  shrug:   [55, 85, 55, 85], present: [12, 6, 60, 40], armsUp: [150, 10, 150, 10], cheer: [140, 30, 12, 6], think: [12, 6, 40, 140],
  hips:    [45, -95, 45, -95], fist: [20, 120, 20, 120], salute: [12, 6, 120, 150], cower: [130, 120, 130, 120], facepalm: [12, 6, 70, 150],
  hold:    [40, 55, 40, 55], carry: [25, 80, 25, 80], guard: [35, 70, 110, 35], thrust: [30, 60, 80, -5], raise: [30, 60, 160, 10],
  shoot:   [80, 0, 70, 70], draw: [85, 0, 80, 130], aim: [70, 40, 75, 55], cross: [40, 125, 40, 125], beg: [60, 70, 60, 70], stop: [12, 6, 75, 75],
  march:   [12, 6, 12, 6], walk: [12, 6, 12, 6], lunge: [70, 40, 60, 50], push: [75, 55, 70, 55], brace: [60, 70, 40, 80], wide: [20, 10, 20, 10], run: [40, 70, 40, 70], kneel: [12, 6, 12, 6], sit: [30, 60, 30, 60], ride: [30, 55, 30, 55], fall: [120, 20, 100, 30],
  scratch: [12, 6, 140, 150], hug: [70, 60, 70, 60], hand: [12, 6, 50, 30],
};
const D2R = Math.PI / 180;
function armPts(sx, sy, s, sh, el, u, L) {
  // s = -1 trai (nguoi xem), 1 phai. goc tinh tu huong xuong, quay ra ngoai
  const a1 = sh * D2R, a2 = (sh + el) * D2R;
  const ex = sx + s * Math.sin(a1) * L, ey = sy + Math.cos(a1) * L;
  const hx = ex + s * Math.sin(a2) * L, hy = ey + Math.cos(a2) * L;
  return [[sx, sy], [ex, ey], [hx, hy], a2];
}
export function hand(g, x, y, r, o = {}) {
  const lw = o.lw, col = o.gauntlet ? PAL.steelLight : (o.glove || '#ffffff');
  circ(g, x, y, r, { fill: col, lw });
  if (o.thumb !== false) ellipse(g, x + (o.s || 1) * r * 0.75, y - r * 0.45, r * 0.38, r * 0.3, { fill: col, lw: lw * 0.8, rot: 0.6 * (o.s || 1) });
  if (o.gauntlet) line(g, [[x - r * 0.6, y - r * 0.1], [x + r * 0.6, y - r * 0.1]], { lw: lw * 0.5 });
}

export const CAST = {};
const K = (o) => o;
Object.assign(CAST, {
  // --- trung co chau Au
  norman:     K({ helmet: 'nasal', body: 'mail', skirt: 0.8, legs: 'cloth', legColor: '#6b4a33', shield: { type: 'kite', color: PAL.red, charge: 'cross', chargeColor: PAL.yellow }, weapon: 'sword', beard: 'stubble' }),
  william:    K({ helmet: 'spangen', body: 'mail', skirt: 0.8, legs: 'cloth', legColor: '#6b4a33', shield: { type: 'kite', color: PAL.red, charge: 'lion', chargeColor: PAL.yellow }, weapon: 'sword' }),
  saxon:      K({ helmet: 'nasal', band: PAL.steel, body: 'mail', skirt: 0.7, tunicColor: PAL.green, legs: 'cloth', legColor: PAL.brown, shield: { type: 'round', color: PAL.green, charge: 'cross', chargeColor: PAL.cream }, weapon: 'axe', beard: 'full', hairColor: PAL.ginger }),
  viking:     K({ helmet: 'nasal', band: PAL.steel, body: 'tunic', tunicColor: PAL.blue, legs: 'cloth', shield: { type: 'round', color: '#e0c890', charge: 'cross', chargeColor: PAL.red }, weapon: 'axe', beard: 'full', hairColor: PAL.ginger }),
  knight12:   K({ helmet: 'bucket', body: 'mail', tabard: true, tabardColor: PAL.yellow, charge: 'lion', chargeColor: PAL.red, skirt: 0.85, legs: 'mail', shield: { type: 'heater', color: PAL.yellow, charge: 'lion', chargeColor: PAL.red }, weapon: 'sword' }),
  knight13:   K({ helmet: 'coif', body: 'mail', tabard: true, tabardColor: PAL.yellow, charge: 'lion', chargeColor: PAL.red, skirt: 0.85, legs: 'mail', shield: { type: 'heater', color: PAL.yellow, charge: 'lion', chargeColor: PAL.red }, weapon: 'sword' }),
  knight14:   K({ helmet: 'bascinet', visor: 'up', body: 'mail', tabard: true, tabardColor: PAL.yellow, charge: 'lion', chargeColor: PAL.red, skirt: 0.55, arms: 'plate', legs: 'plate', weapon: 'sword' }),
  knight15:   K({ helmet: 'bascinet', visor: 'up', body: 'plate', arms: 'plate', legs: 'plate', tabard: true, tabardColor: PAL.yellow, charge: 'lion', chargeColor: PAL.red, skirt: 0.35, weapon: 'pollaxe', gauntlet: true }),
  whiteArmor: K({ helmet: 'bascinet', visor: 'up', body: 'plate', arms: 'plate', legs: 'plate', skirt: 0.3, weapon: 'pollaxe', gauntlet: true }),
  frenchKnight: K({ helmet: 'bascinet', visor: 'up', body: 'plate', arms: 'plate', legs: 'plate', tabard: true, tabardColor: PAL.blue, charge: 'fleur', chargeColor: PAL.yellow, skirt: 0.35, weapon: 'sword', gauntlet: true }),
  frenchKnight2: K({ helmet: 'bascinet', visor: 'down', body: 'plate', arms: 'plate', legs: 'plate', tabard: true, tabardColor: PAL.blue, charge: 'quarter', chargeColor: PAL.yellow, skirt: 0.35, weapon: 'sword', gauntlet: true }),
  englishArcher: K({ helmet: 'kettle', body: 'gambeson', tunicColor: '#e8e0cc', tabard: true, tabardColor: '#f2ede2', charge: 'crossW', chargeColor: PAL.red, skirt: 0.55, legs: 'cloth', legColor: PAL.red, weapon: 'bow', mustache: 'big', hairColor: PAL.hair }),
  crossbowman: K({ helmet: 'kettle', body: 'gambeson', tunicColor: PAL.red, tabard: true, tabardColor: '#e8e3d4', charge: 'crossW', chargeColor: PAL.red, skirt: 0.5, legs: 'cloth', legColor: PAL.white, weapon: 'crossbow', mustache: 'normal', scarf: PAL.green }),
  king:       K({ helmet: 'crown', hair: 'long', hairColor: PAL.hair, beard: 'full', body: 'robe', tunicColor: PAL.blue, charge: 'fleur', chargeColor: PAL.yellow, skirt: 1, legs: 'cloth', legColor: PAL.blueDark, cape: PAL.red }),
  henry:      K({ helmet: 'bascinet', visor: 'none', bevor: false, crownOn: true, body: 'plate', arms: 'plate', legs: 'plate', tabard: true, tabardColor: PAL.red, charge: 'quarter', chargeColor: PAL.blue, skirt: 0.4, weapon: 'pollaxe', gauntlet: true }),
  peasant:    K({ hair: 'bowl', hairColor: PAL.hair, body: 'tunic', tunicColor: PAL.green, legs: 'cloth', legColor: PAL.brown, skirt: 0.5, beard: 'stubble' }),
  smith:      K({ hair: 'curly', hairColor: PAL.ginger, beard: 'full', body: 'apron', tunicColor: PAL.green, legs: 'cloth', legColor: PAL.brown, weapon: 'hammer' }),
  monk:       K({ helmet: 'hood', hoodColor: PAL.brown, body: 'robe', tunicColor: PAL.brown, skirt: 1, legs: 'cloth', legColor: PAL.brownDark }),
  lady:       K({ hair: 'long', hairColor: PAL.hairDark, body: 'dress', tunicColor: PAL.blue, skirt: 1 }),
  // --- La Ma / Latin
  hastatus:   K({ helmet: 'montefortino', feathers: 3, body: 'roman', tunicColor: PAL.red, legs: 'bare', shield: { type: 'scutum', color: PAL.red, charge: 'lightning', chargeColor: PAL.yellow }, weapon: 'spear' }),
  princeps:   K({ helmet: 'montefortino', feathers: 3, featherColors: [PAL.red, OUT, PAL.red], body: 'roman', tunicColor: PAL.red, legs: 'bare', mustache: 'big', shield: { type: 'scutum', color: PAL.red, charge: 'wings', chargeColor: PAL.yellow }, weapon: 'pilum' }),
  triarius:   K({ helmet: 'attic', body: 'roman', mail: true, tunicColor: PAL.red, legs: 'bare', beard: 'full', hairColor: PAL.grey, shield: { type: 'scutum', color: PAL.red, charge: 'sun', chargeColor: PAL.yellow }, weapon: 'spear' }),
  latin:      K({ helmet: 'montefortino', feathers: 2, body: 'roman', tunicColor: PAL.blue, legs: 'bare', shield: { type: 'round', color: PAL.blue, charge: 'circle', chargeColor: PAL.white, rim: PAL.gold }, weapon: 'spear' }),
  latinOld:   K({ helmet: 'montefortino', feathers: 0, body: 'roman', tunicColor: PAL.blue, legs: 'bare', beard: 'full', hairColor: PAL.grey, shield: { type: 'round', color: PAL.blue, charge: 'circle', chargeColor: PAL.white }, weapon: 'spear' }),
  velites:    K({ hair: 'short', hairColor: PAL.hair, body: 'tunic', tunicColor: '#d9c9a5', legs: 'bare', shield: { type: 'buckler', color: PAL.red }, weapon: 'spear' }),
  legionary:  K({ helmet: 'montefortino', crest: PAL.red, body: 'roman', mail: true, tunicColor: PAL.red, legs: 'bare', shield: { type: 'scutum', color: PAL.red, charge: 'wings', chargeColor: PAL.yellow }, weapon: 'pilum' }),
  senator:    K({ hair: 'short', hairColor: PAL.hairDark, body: 'toga', tunicColor: PAL.white, sash: PAL.crimson, legs: 'bare', skirt: 1 }),
  priest:     K({ helmet: 'hood', hoodColor: PAL.white, body: 'toga', tunicColor: PAL.white, sash: PAL.red, skirt: 1 }),
  consul:     K({ helmet: 'attic', crest: PAL.red, body: 'roman', tunicColor: PAL.crimson, cape: PAL.red, legs: 'bare', beard: 'stubble', weapon: 'sword' }),
  greek:      K({ helmet: 'attic', crest: PAL.blue, body: 'roman', tunicColor: PAL.blue, legs: 'bare', shield: { type: 'round', color: PAL.bronze, charge: 'star', chargeColor: PAL.red }, weapon: 'pike' }),
  spartan:    K({ helmet: 'attic', crest: PAL.red, body: 'roman', tunicColor: PAL.crimson, cape: PAL.red, legs: 'bare', shield: { type: 'round', color: PAL.bronze, charge: 'lightning', chargeColor: PAL.red }, weapon: 'spear', beard: 'full' }),
  // --- Nhat
  samurai:    K({ helmet: 'kabuto', body: 'samurai', tunicColor: PAL.black, lacing: PAL.red, legs: 'samurai', mustache: 'big', hairColor: PAL.hair, weapon: 'katana' }),
  ashigaru:   K({ helmet: 'jingasa', body: 'samurai', tunicColor: '#5c4a3c', lacing: PAL.blue, legs: 'cloth', legColor: '#3c3d48', weapon: 'spear' }),
  ronin:      K({ hair: 'topknot', hairColor: PAL.hairDark, body: 'robe', tunicColor: '#4b4f63', legs: 'cloth', legColor: '#2f3240', weapon: 'katana', beard: 'stubble' }),
  // --- the ky 19-20
  serbSoldier: K({ helmet: 'cap', capColor: PAL.olive, body: 'uniform', tunicColor: PAL.olive, legs: 'cloth', legColor: PAL.olive, boots: PAL.brown, weapon: 'rifle', mustache: 'big' }),
  ww1Brit:    K({ helmet: 'brodie', camo: false, metal: '#7d7a55', body: 'uniform', tunicColor: PAL.khaki, legs: 'cloth', legColor: PAL.khaki, weapon: 'rifle' }),
  ww2us:      K({ helmet: 'm1', body: 'uniform', tunicColor: PAL.camo1, camo: true, legs: 'cloth', legColor: PAL.camo1, weapon: 'rifle' }),
  ww2usOlive: K({ helmet: 'm1', camo: false, metal: PAL.olive, body: 'uniform', tunicColor: PAL.olive, legs: 'cloth', legColor: PAL.oliveDark, weapon: 'rifle' }),
  ww2jp:      K({ helmet: 'cap', capColor: PAL.khaki, badge: PAL.gold, badge2: PAL.gold, body: 'uniform', tunicColor: PAL.khaki, legs: 'cloth', legColor: PAL.khakiDark, weapon: 'rifle' }),
  ww2de:      K({ helmet: 'm1', camo: false, metal: '#5d6459', body: 'uniform', tunicColor: '#6b7262', legs: 'cloth', legColor: '#5a6052', weapon: 'rifle' }),
  officer:    K({ helmet: 'peaked', capColor: PAL.olive, band: PAL.red, body: 'uniform', tunicColor: PAL.olive, legs: 'cloth', legColor: PAL.oliveDark, mustache: 'big', medals: true }),
  officerJP:  K({ helmet: 'peaked', capColor: PAL.white, band: PAL.black, body: 'uniform', tunicColor: PAL.white, legs: 'cloth', legColor: PAL.white, medals: true }),
  sailor:     K({ helmet: 'sailor', body: 'sailor', tunicColor: PAL.white, legs: 'cloth', legColor: PAL.navy }),
  pilot:      K({ helmet: 'cap', capColor: PAL.brown, body: 'uniform', tunicColor: PAL.leather, legs: 'cloth', legColor: PAL.khaki, scarf: PAL.white }),
  nurse:      K({ hair: 'bun', hairColor: PAL.hairDark, body: 'dress', tunicColor: PAL.white, apronCross: true, skirt: 0.9 }),
  // --- hien dai
  modern:     K({ hair: 'short', hairColor: PAL.hair, body: 'tunic', tunicColor: PAL.blue, legs: 'cloth', legColor: '#3a4256' }),
  police:     K({ helmet: 'riot', body: 'uniform', tunicColor: PAL.navy, legs: 'cloth', legColor: PAL.navy, shield: { type: 'riot', color: '#bcd3e2' }, chestText: 'POLICE' }),
  scientist:  K({ hair: 'side', hairColor: PAL.grey, body: 'robe', tunicColor: PAL.white, skirt: 0.7, glasses: true, mustache: 'normal', hairColor2: PAL.grey }),
  you:        K({ helmet: 'bascinet', visor: 'up', body: 'plate', arms: 'plate', legs: 'plate', tabard: true, tabardColor: PAL.yellow, charge: 'lion', chargeColor: PAL.red, skirt: 0.35, gauntlet: true }),
});

// ve than (torso + vay + chan) — tra ve diem vai va hong
// ---------- dang di: chan cham dat that (IK 2 doan), khong truot
// walkMode: 'side' (di ngang, buoc theo quang duong that) | 'front' (buoc tai cho / tien ve phia may quay)
// walkPhase: so chu ky buoc (side: quang_duong / (2 * buoc); front: thoi gian * nhip)
export const STEP = 17;                         // do dai 1 buoc (don vi u = h/100)
export function ik2(hx, hy, fx, fy, L1, L2, bend = 1) {
  let dx = fx - hx, dy = fy - hy, d = Math.hypot(dx, dy); const m = (L1 + L2) * 0.999;
  if (d > m) { fx = hx + dx / d * m; fy = hy + dy / d * m; dx = fx - hx; dy = fy - hy; d = m; }
  d = Math.max(d, Math.abs(L1 - L2) + 0.01);
  const a = Math.acos(clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1)), th = Math.atan2(dy, dx) - bend * a;
  return [[hx, hy], [hx + Math.cos(th) * L1, hy + Math.sin(th) * L1], [fx, fy]];
}
export function walkInfo(o) {
  const mode = o.walkMode || (o.walk || ['walk', 'march', 'run'].includes(o.pose) ? (o.pose === 'march' ? 'front' : 'front') : null);
  if (!mode) return null;
  const run = o.pose === 'run';
  const p = o.walkPhase ?? ((o.t || 0) * (run ? 1.6 : 0.95));
  const f = ((p % 1) + 1) % 1;
  const bob = mode === 'side' ? -(1 - Math.cos(4 * Math.PI * f)) / 2 * (run ? 3 : 1.6) : -Math.abs(Math.sin(2 * Math.PI * f)) * 1.2;
  return { mode, f, run, bob, swing: Math.sin(2 * Math.PI * f) };
}
function footSide(f, S, lift) {
  // f 0..0.5: chan tru (dat, lui dan ve sau); 0.5..1: chan vung (nhac len, dua ra truoc)
  if (f < 0.5) { const k = f / 0.5; return [lerp(S / 2, -S / 2, k), 0]; }
  const k = (f - 0.5) / 0.5, e = (1 - Math.cos(Math.PI * k)) / 2; return [lerp(-S / 2, S / 2, e), -Math.sin(Math.PI * k) * lift];
}
function legs(g, u, o, lw, t) {
  const kind = o.legs || 'cloth', col = kind === 'plate' ? PAL.steel : kind === 'mail' ? PAL.mail : kind === 'bare' ? (o.skin || PAL.skin) : kind === 'samurai' ? (o.legColor || '#3c3d48') : (o.legColor || PAL.brown);
  const pose = o.pose || 'stand', hip = (o._hip ?? -30) * u, w = (o._legW ?? 6.6) * u, L1 = (Math.abs(o._hip ?? -30) - 3.2 + 1.5) / 2 * u, L2 = L1, fy0 = -3.2 * u;
  const W = o._walk;
  const bc = kind === 'plate' ? PAL.steel : o.boots || (kind === 'bare' ? PAL.leather : PAL.brownDark);
  const legsList = []; // {pts, side: 'L'|'R', shoe: 'front'|'side', far}
  if (W && W.mode === 'side') {
    const S = (W.run ? 1.5 : 1) * STEP * u, lift = (W.run ? 9 : 5.5) * u;
    for (const [off, far] of [[0.5, true], [0, false]]) {
      const [fx, fyy] = footSide((W.f + off) % 1, S, lift);
      const hx = far ? -2.2 * u : 2.2 * u;
      legsList.push({ pts: ik2(hx, hip + W.bob * u, fx + hx * 0.3, fy0 + fyy, L1, L2, 1), shoe: 'side', far });
    }
  } else if (W && W.mode === 'front') {
    for (const [s, off] of [[-1, 0], [1, 0.5]]) {
      const ff = (W.f + off) % 1, lift = Math.max(0, Math.sin(2 * Math.PI * ff)) * (W.run ? 8 : 5) * u;
      const hx = s * 6.5 * u, fx = s * 7 * u;
      legsList.push({ pts: ik2(hx, hip + W.bob * u, fx, fy0 - lift, L1, L2, s > 0 ? -0.35 : 0.35), shoe: 'front', s });
    }
  } else if (pose === 'kneel') {
    legsList.push({ pts: [[-6 * u, hip + 6 * u], [-15 * u, hip + 9 * u], [-15 * u, fy0]], shoe: 'front', s: -1 });
    legsList.push({ pts: [[6 * u, hip + 6 * u], [9 * u, fy0 + 1 * u], [19 * u, fy0 + 1 * u]], shoe: 'side' });
  } else if (pose === 'sit') {
    for (const s of [-1, 1]) legsList.push({ pts: [[s * 6 * u, hip], [s * 9 * u, hip + 2 * u], [s * 9 * u, fy0]], shoe: 'front', s });
  } else if (pose === 'ride') {
    legsList.push({ pts: [[7 * u, hip], [12 * u, hip + 10 * u], [9 * u, -6 * u]], shoe: 'front', s: 1 });
  } else if (pose === 'lunge' || pose === 'push' || pose === 'brace') {
    // chan truoc gap goi, chan sau duoi thang (day khien, xo dua)
    legsList.push({ pts: ik2(-4 * u, hip + 2 * u, -20 * u, fy0, L1, L2, -1), shoe: 'side', far: true, back: true });
    legsList.push({ pts: ik2(4 * u, hip + 2 * u, 15 * u, fy0, L1, L2, 1), shoe: 'side' });
  } else if (pose === 'wide' || pose === 'guard') {
    for (const s of [-1, 1]) legsList.push({ pts: ik2(s * 6.5 * u, hip, s * 11 * u, fy0, L1, L2, -s * 0.4), shoe: 'front', s });
  } else {
    for (const s of [-1, 1]) legsList.push({ pts: ik2(s * 6.2 * u, hip, s * 7.2 * u, fy0, L1, L2, -s * 0.3), shoe: 'front', s });
  }
  for (const Lg of legsList) {
    const P = Lg.pts, c2 = Lg.far ? darker(col, 0.1) : col;
    tube(g, P, w, c2, lw);
    if (kind === 'plate') circ(g, P[1][0], P[1][1], w * 0.68, { fill: Lg.far ? PAL.steel : PAL.steelLight, lw: lw * 0.8 });
    if (kind === 'samurai') { const m = P[0]; rect(g, m[0] - w * 1.1, m[1], w * 2.2, 10 * u, { fill: o.lacing || PAL.red, lw: lw * 0.8, r: 2 }); }
    const f = P[2], b2 = Lg.far ? darker(bc, 0.08) : bc;
    if (Lg.shoe === 'side') { const dir = Lg.back ? 1 : 1; shape(g, (c) => c.roundRect(f[0] - 3.5 * u, f[1] - 2.2 * u, 11 * u * dir, 5.6 * u, [2 * u, 4.5 * u, 2 * u, 1.5 * u]), { fill: b2, lw: lw * 0.9 }); }
    else { const s = Lg.s || (f[0] < 0 ? -1 : 1); shape(g, (c) => c.roundRect(f[0] - 5.5 * u + s * 1.6 * u, f[1] - 2.2 * u, 11 * u, 5.6 * u, [4 * u, 4 * u, 1.5 * u, 1.5 * u]), { fill: b2, lw: lw * 0.9 }); }
    if (kind === 'bare') line(g, [[P[1][0] - 3 * u, P[1][1] + 6 * u], [P[1][0] + 3 * u, P[1][1] + 9 * u]], { lw: lw * 0.6, ink: PAL.leather });
  }
}
function torso(g, u, o, lw, t) {
  const body = o.body || 'tunic', top = -59 * u, hip = -30 * u, skirtY = hip + (o.skirt ?? 0.4) * (['robe', 'dress', 'toga'].includes(o.body) ? 24 : 15) * u, wT = 13.5 * u, wB = 16 * u;
  const base = { mail: PAL.mail, plate: PAL.steel, gambeson: o.tunicColor || '#e3d9c2', robe: o.tunicColor || PAL.brown, toga: o.tunicColor || PAL.white, roman: o.tunicColor || PAL.red, samurai: o.tunicColor || PAL.black, uniform: o.tunicColor || PAL.olive, sailor: PAL.white, dress: o.tunicColor || PAL.blue, apron: o.tunicColor || PAL.green }[body] || o.tunicColor || PAL.green;
  const path = (c, bot = skirtY, flare = 1) => { c.moveTo(-wT - 0.5 * u, top + 7 * u); c.quadraticCurveTo(-wT, top, -wT + 7 * u, top); c.lineTo(wT - 7 * u, top); c.quadraticCurveTo(wT, top, wT + 0.5 * u, top + 7 * u); c.lineTo(wB * flare, bot); c.quadraticCurveTo(0, bot + 2 * u, -wB * flare, bot); c.closePath(); };
  if (o.cape) shape(g, (c) => { c.moveTo(-wT - 2 * u, top + 2 * u); c.lineTo(wT + 2 * u, top + 2 * u); c.lineTo(wB + 6 * u, -3 * u); c.lineTo(-wB - 6 * u, -3 * u); c.closePath(); }, { fill: o.cape, lw });
  // lop duoi: ao giap / ao
  const flare = body === 'robe' || body === 'dress' || body === 'toga' ? 1.25 : 1.06;
  shape(g, (c) => path(c, skirtY, flare), { fill: base, lw, inner: (c) => {
    if (body === 'mail' || o.mail) { c.fillStyle = PAL.mail; c.fillRect(-wB * 2, top, wB * 4, 80 * u); mailPattern(c, -wB * 1.4, top, wB * 2.8, 60 * u, 4.2 * u, lw); }
    if (body === 'plate') { c.fillStyle = alpha(PAL.steelDark, 0.5); c.fillRect(4 * u, top, 30 * u, 60 * u); hiliteC(c, [[-9 * u, top + 6 * u], [-9 * u, top + 22 * u]], u); for (let i = 0; i < 3; i++) line(c, [[-wB * 1.2, hip - 2 * u + i * 4 * u], [wB * 1.2, hip - 2 * u + i * 4 * u]], { lw: lw * 0.6 }); }
    if (body === 'gambeson') { for (let i = -3; i <= 3; i++) line(c, [[i * 4.5 * u, top], [i * 4.8 * u, skirtY + 4 * u]], { lw: lw * 0.4, a: 0.5 }); }
    if (body === 'roman') { if (!o.mail) { rect(c, -8 * u, top + 6 * u, 16 * u, 14 * u, { fill: PAL.bronze, lw: lw * 0.8, r: 2 * u, inner: (cc) => { circ(cc, -3.5 * u, top + 11 * u, 1.6 * u, { fill: PAL.bronzeDark, lw: 0 }); circ(cc, 3.5 * u, top + 11 * u, 1.6 * u, { fill: PAL.bronzeDark, lw: 0 }); circ(cc, 0, top + 16 * u, 1.6 * u, { fill: PAL.bronzeDark, lw: 0 }); } }); } for (let i = -3; i <= 3; i++) line(c, [[i * 4.2 * u, hip], [i * 4.6 * u, skirtY + 2 * u]], { lw: lw * 0.45, a: 0.45 }); }
    if (body === 'samurai') { for (let i = 0; i < 5; i++) { rect(c, -wB * 1.2, top + 8 * u + i * 7 * u, wB * 2.4, 5.5 * u, { fill: i % 2 ? (o.lacing || PAL.red) : base, lw: lw * 0.5, r: 1 }); } }
    if (body === 'uniform') { line(c, [[0, top + 2 * u], [0, skirtY]], { lw: lw * 0.5 }); for (let i = 0; i < 3; i++) circ(c, 1.8 * u, top + 9 * u + i * 8 * u, 1.1 * u, { fill: PAL.gold, lw: 0 }); for (const s of [-1, 1]) rect(c, s * 9 * u - 4 * u, top + 8 * u, 8 * u, 6 * u, { fill: darker(base, 0.06), lw: lw * 0.5, r: 1 }); if (o.camo) { [[-8, 20, 5], [6, 30, 6], [-4, 40, 4], [9, 15, 4]].forEach(([a, b, r], i) => ellipse(c, a * u, top + b * u, r * u, r * 0.7 * u, { fill: [PAL.camo2, PAL.camo3][i % 2], lw: 0, rot: i })); } if (o.medals) for (let i = 0; i < 3; i++) rect(c, -11 * u + i * 3.2 * u, top + 7 * u, 2.6 * u, 3 * u, { fill: [PAL.red, PAL.blue, PAL.gold][i], lw: lw * 0.3, r: 0 }); }
    if (body === 'sailor') { shape(c, (cc) => { cc.moveTo(-wT, top); cc.lineTo(wT, top); cc.lineTo(wT * 0.7, top + 10 * u); cc.lineTo(0, top + 16 * u); cc.lineTo(-wT * 0.7, top + 10 * u); cc.closePath(); }, { fill: PAL.navy, lw: lw * 0.6 }); }
    if (body === 'toga') { shape(c, (cc) => { cc.moveTo(-wT, top); cc.lineTo(-wT + 8 * u, top); cc.lineTo(wB * 1.3, skirtY); cc.lineTo(wB * 0.6, skirtY); cc.closePath(); }, { fill: o.sash || PAL.crimson, lw: lw * 0.6 }); }
    if (body === 'apron') { rect(c, -10 * u, top + 6 * u, 20 * u, 50 * u, { fill: PAL.leather, lw: lw * 0.7, r: 2 * u }); }
    if (o.apronCross) { rect(c, -9 * u, top + 8 * u, 18 * u, 40 * u, { fill: '#fff', lw: lw * 0.6, r: 2 * u }); charge(c, 'cross', 0, top + 18 * u, 9 * u, PAL.red); }
    if (o.chestText) label(c, o.chestText, 0, top + 14 * u, { size: 5 * u, font: '"Be Vietnam Pro"', weight: 800, color: '#fff', caps: true });
    c.fillStyle = alpha('#000', 0.12); c.fillRect(wT * 0.45, top, wT * 2, 70 * u);
  } });
  // ao choang huy hieu
  if (o.tabard) {
    const tb = o.tabardColor || PAL.yellow, tY = hip + (o.skirt ?? 0.4) * (['robe', 'dress', 'toga'].includes(o.body) ? 24 : 15) * u - 1 * u;
    shape(g, (c) => { c.moveTo(-wT + 2 * u, top + 1 * u); c.lineTo(wT - 2 * u, top + 1 * u); c.lineTo(wB * 0.98, tY); c.quadraticCurveTo(0, tY + 2 * u, -wB * 0.98, tY); c.closePath(); }, { fill: tb, lw, inner: (c) => {
      if (o.charge === 'quarter') { c.fillStyle = o.chargeColor || PAL.blue; c.fillRect(-wB, top, wB, (tY - top) / 2); c.fillRect(0, top + (tY - top) / 2, wB, (tY - top) / 2); charge(c, 'fleur', -wB / 2, top + (tY - top) * 0.25, 7 * u, PAL.yellow, null, lw * 0.5); charge(c, 'lion', wB / 2, top + (tY - top) * 0.25, 9 * u, PAL.yellow, null, lw * 0.5); charge(c, 'lion', -wB / 2, top + (tY - top) * 0.75, 9 * u, PAL.yellow, null, lw * 0.5); charge(c, 'fleur', wB / 2, top + (tY - top) * 0.75, 7 * u, PAL.yellow, null, lw * 0.5); }
      else charge(c, o.charge, 0, top + (tY - top) * 0.42, (o.chargeS || 0.75) * 26 * u, o.chargeColor || PAL.red, null, lw * 0.6);
      c.fillStyle = alpha('#000', 0.1); c.fillRect(wT * 0.5, top, wT * 2, 70 * u);
    } });
  }
  // that lung
  if (!['robe', 'toga', 'dress', 'sailor'].includes(body) || o.belt) { rect(g, -wB * 0.98, hip - 5 * u, wB * 1.96, 4.5 * u, { fill: o.beltColor || PAL.leather, lw: lw * 0.8, r: 1 }); circ(g, 0, hip - 2.8 * u, 2.4 * u, { fill: PAL.gold, lw: lw * 0.6 }); }
  if (o.scarf) { shape(g, (c) => { c.moveTo(-10 * u, top + 1 * u); c.quadraticCurveTo(0, top + 6 * u, 10 * u, top + 1 * u); c.lineTo(8 * u, top + 5 * u); c.lineTo(4 * u, top + 16 * u); c.lineTo(0, top + 15 * u); c.lineTo(2 * u, top + 6 * u); c.quadraticCurveTo(-4 * u, top + 6 * u, -10 * u, top + 4 * u); c.closePath(); }, { fill: o.scarf, lw: lw * 0.8 }); }
  // vai giap
  if (o.arms === 'plate' || body === 'plate') for (const s of [-1, 1]) ellipse(g, s * (wT - 1 * u), top + 4 * u, 7 * u, 6 * u, { fill: PAL.steelLight, lw: lw * 0.9 });
  if (body === 'samurai') for (const s of [-1, 1]) rect(g, s * (wT + 1 * u) - 6 * u, top + 1 * u, 12 * u, 13 * u, { fill: o.lacing || PAL.red, lw: lw * 0.85, r: 2 * u, inner: (c) => { for (let i = 1; i < 4; i++) line(c, [[s * (wT + 1 * u) - 6 * u, top + 1 * u + i * 3.2 * u], [s * (wT + 1 * u) + 6 * u, top + 1 * u + i * 3.2 * u]], { lw: lw * 0.4 }); } });
}
function hiliteC(c, pts, u) { c.save(); c.globalAlpha = 0.6; line(c, pts, { lw: 2.2 * u, ink: '#fff' }); c.restore(); }

function arm(g, u, o, lw, s, sh, el, held) {
  const sx = s * 12.2 * u, sy = -54 * u, Lseg = 12.5 * u;
  const [S, Eb, H, ang] = armPts(sx, sy, s, sh, el, u, Lseg);
  const kind = o.arms || (o.body === 'plate' ? 'plate' : o.body === 'mail' || o.mail ? 'mail' : 'cloth');
  const col = kind === 'plate' ? PAL.steel : kind === 'mail' ? PAL.mail : (o.sleeve || (o.body === 'roman' || o.body === 'toga' ? (o.skin || PAL.skin) : ({ gambeson: o.tunicColor || '#e3d9c2', uniform: o.tunicColor || PAL.olive, robe: o.tunicColor || PAL.brown, samurai: o.lacing || PAL.red, sailor: PAL.white, dress: o.tunicColor || PAL.blue }[o.body] || o.tunicColor || PAL.green)));
  if (held && held.before) held.before(H, ang);
  tube(g, [S, Eb, H], 7.5 * u, col, lw);
  if (kind === 'plate') { circ(g, Eb[0], Eb[1], 4.6 * u, { fill: PAL.steelLight, lw: lw * 0.8 }); }
  if (held && held.mid) held.mid(H, ang);
  hand(g, H[0], H[1], 5.3 * u, { lw, s, gauntlet: o.gauntlet, glove: o.glove });
  return { S, E: Eb, H, ang };
}

// LOD thap: hinh nho tit (dam dong xa) — chi dau + mu + than khoi
function soldierLowHood(g, x, y, h, o) {
  const u = h / 100, lw = Math.max(0.8, h * 0.012), HW = 21 * u;
  g.save(); g.translate(x, y); if (o.flip) g.scale(-1, 1);
  if (o.shield) shield(g, -20 * u, -38 * u, 60 * u, { ...o.shield, lw, rot: -0.1 });
  rect(g, -11 * u, -13 * u, 9 * u, 13 * u, { fill: o.legColor || '#6b4a33', lw, r: 2 * u }); rect(g, 2 * u, -13 * u, 9 * u, 13 * u, { fill: o.legColor || '#6b4a33', lw, r: 2 * u });
  shape(g, (c) => { c.moveTo(-HW, -80 * u); c.lineTo(-HW * 1.02, -24 * u); c.quadraticCurveTo(-HW, -11 * u, -HW * 0.9, -11 * u); c.lineTo(HW * 0.9, -11 * u); c.quadraticCurveTo(HW, -11 * u, HW * 1.02, -24 * u); c.lineTo(HW, -80 * u); c.closePath(); }, { fill: PAL.mail, lw, inner: (c) => { c.fillStyle = alpha('#2a2030', 0.16); c.fillRect(HW * 0.4, -100 * u, HW, 100 * u); } });
  rect(g, -12 * u, -76 * u, 24 * u, 15 * u, { fill: '#f3e0d6', lw: lw * 0.8, r: 4 * u });
  for (const s2 of [-1, 1]) circ(g, s2 * 5.5 * u, -69 * u, 2.6 * u, { fill: '#fff', lw: lw * 0.6, inner: (c) => circ(c, s2 * 5.5 * u, -69 * u, 1 * u, { fill: OUT, lw: 0 }) });
  shape(g, (c) => { c.moveTo(-HW * 1.03, -79 * u); c.bezierCurveTo(-HW * 1.05, -93 * u, -HW * 0.55, -101 * u, 0, -103 * u); c.bezierCurveTo(HW * 0.55, -101 * u, HW * 1.05, -93 * u, HW * 1.03, -79 * u); c.closePath(); }, { fill: PAL.steel, lw });
  rect(g, -HW * 1.04, -82.5 * u, HW * 2.08, 5 * u, { fill: o.band || PAL.gold, lw: lw * 0.8, r: 1 });
  rect(g, -1.5 * u, -80 * u, 3 * u, 14 * u, { fill: PAL.steelLight, lw: lw * 0.7, r: 1 });
  rect(g, -HW * 0.98, -30 * u, HW * 1.96, 3 * u, { fill: PAL.leather, lw: lw * 0.7, r: 0 });
  g.restore();
}
function soldierLow(g, x, y, h, o) {
  if (['nasal', 'coif', 'spangen'].includes(o.helmet) && o.body === 'mail') return soldierLowHood(g, x, y, h, o);
  const u = h / 100, lw = Math.max(0.8, h * 0.012);
  g.save(); g.translate(x, y); if (o.flip) g.scale(-1, 1);
  const tc = o.tabard ? (o.tabardColor || PAL.yellow) : ({ mail: PAL.mail, plate: PAL.steel, roman: o.tunicColor || PAL.red, uniform: o.tunicColor || PAL.olive }[o.body] || o.tunicColor || PAL.green);
  rect(g, -14 * u, -60 * u, 28 * u, 52 * u, { fill: tc, lw, r: 6 * u });
  { const W = walkInfo(o); const la = W ? Math.max(0, W.swing) * 4 * u : 0, ra = W ? Math.max(0, -W.swing) * 4 * u : 0, sx = W && W.mode === 'side' ? W.swing * 5 * u : 0; rect(g, -10 * u + sx, -10 * u - la, 8 * u, 10 * u, { fill: PAL.brownDark, lw: lw * 0.8, r: 2 * u }); rect(g, 2 * u - sx, -10 * u - ra, 8 * u, 10 * u, { fill: PAL.brownDark, lw: lw * 0.8, r: 2 * u }); }
  if (o.weapon && ['spear', 'pilum', 'pike', 'lance', 'flag', 'pollaxe'].includes(o.weapon)) line(g, [[16 * u, -10 * u], [16 * u, -130 * u]], { lw: Math.max(1, 2.5 * u), ink: PAL.woodDark });
  head(g, 0, -81 * u, 19 * u, { ...o, lw, face: o.face || 'neutral', t: o.t });
  if (o.shield) shield(g, 9 * u, -36 * u, 46 * u, { ...o.shield, lw });
  g.restore();
}

// ====================================================================================== NHAN VAT DAY DU
export function soldier(g, x, y, h, o = {}) {
  o = { ...(CAST[o.preset] || {}), ...o };
  if (o.lod === 'low' || (o.lod !== 'high' && h < 70)) return soldierLow(g, x, y, h, o);
  const u = h / 100, lw = o.lw ?? Math.max(1.4, h * 0.011), t = o.t || 0;
  const pose = POSES[o.pose] ? o.pose : 'stand';
  let [lsh, lel, rsh, rel] = o.armsAng || POSES[pose];
  const W = walkInfo(o); o._walk = W;
  if (W && !o.noSwing) { const k = W.swing * (W.mode === 'side' ? 20 : 9) * (W.run ? 1.6 : 1); lsh += k; rsh -= k; }
  if (o.gesture) { const k = Math.sin(t * 2.2) * 6; rsh += k; rel -= k * 0.5; }
  const br = (W ? W.bob : Math.sin(t * 1.7 + (o.seed || 0)) * 0.6) * u;
  g.save(); g.translate(x, y); if (o.flip) g.scale(-1, 1); if (o.rot) g.rotate(o.rot); if (W && W.mode === 'side') g.rotate(W.run ? 0.09 : 0.035); if (['push', 'lunge'].includes(o.pose)) g.rotate(0.13); if (o.pose === 'brace') g.rotate(-0.06);
  if (o.kid) g.scale(0.78, 0.78);
  // khien deo sau lung / kiem ben hong
  const sh = o.shield, wp = o.weapon;
  if (o.sheath) tube(g, [[-12 * u, -24 * u], [-22 * u, -4 * u]], 3 * u, PAL.leather, lw);
  const slung = ['rifle', 'musket'].includes(wp) && o.weaponAng === undefined && rsh < 60;
  if (slung) weapon(g, wp, 17 * u, -26 * u, (o.weaponLen || 50) * u, Math.PI - 0.1, { lw, t, bayonet: o.bayonet });
  const hood = ['nasal', 'coif', 'spangen'].includes(o.helmet) && (o.body === 'mail') && o.hoodStyle !== false;
  const plateK = ['bascinet', 'bucket'].includes(o.helmet) && (o.body === 'plate' || o.arms === 'plate' || o.legs === 'plate' || o.body === 'mail') && o.plateStyle !== false;
  if (plateK) { o._hip = -17; o._legW = 5.2; if (o.legs !== 'plate') o.legs = o.legs || 'mail'; }
  if (hood) { o._hip = -13; o._legW = 7; }
  if (hood && sh && !sh.front && o.pose !== 'guard') shield(g, (sh.x ?? -21) * u, (sh.y ?? -38) * u + br, (sh.s || (sh.type === 'kite' ? 62 : 44)) * u, { ...sh, lw, rot: sh.rot ?? -0.1 });
  legs(g, u, o, lw, t);
  if (W && W.mode === 'side' && o.look === undefined) o.look = 0.75;
  if (hood) { const r = hoodKnight(g, u, o, lw, t, W, [lsh, lel, rsh, rel], br); g.restore(); return { x, y, h, head: [x, y - 67 * u + br], R: 21 * u, hand: r }; }
  if (plateK) { const r = plateKnight(g, u, o, lw, t, W, [lsh, lel, rsh, rel], br); g.restore(); return { x, y, h, head: [x, y - 62 * u + br], R: 16 * u, hand: r }; }
  // tay sau (trai nguoi xem) — cam khien
  const sTilt = sh ? (sh.type === 'kite' ? 0.0 : 0) : 0;
  g.save(); g.translate(0, br);
  const leftHeld = { mid: null };
  const side = W && W.mode === 'side';
  if (side) { g.save(); g.scale(0.84, 1); }
  const L = arm(g, u, o, lw, -1, lsh, lel, null);
  torso(g, u, o, lw, t);
  if (side) g.restore();
  // dau
  const R = 19 * u, hx = (o.lean || 0) * u + (W && W.mode === 'side' ? 1.5 * u : 0), hy = -78 * u;
  head(g, hx, hy, R, { ...o, lw, t, talk: o.talk });
  if (o.crownOn) helmetCrownSmall(g, hx, hy, R, lw);
  if (o.glasses) { for (const s of [-1, 1]) circ(g, hx + s * R * 0.33 + (o.look || 0) * R * 0.22, hy + R * 0.02, R * 0.17, { fill: alpha('#fff', 0.25), lw: lw * 0.6 }); line(g, [[hx - R * 0.16, hy], [hx + R * 0.16, hy]], { lw: lw * 0.5 }); }
  // khien o tay trai (truoc than)
  const shieldFront = sh && !sh.back && o.shieldSide !== 'right';
  // tay phai + vu khi
  const wL = o.weaponLen || ({ sword: 34, katana: 36, dagger: 34, spear: 62, pilum: 60, pike: 62, lance: 70, naginata: 60, pollaxe: 50, axe: 50, hammer: 40, mace: 40, bow: 40, crossbow: 44, rifle: 50, musket: 54, pistol: 40, flag: 60, banner: 60, torch: 34, staff: 70, scroll: 30, pouch: 24, grenade: 22 }[wp] || 40);
  let wAng = o.weaponAng;
  const right = arm(g, u, o, lw, 1, rsh, rel, {
    before: (H, ang) => {
      if (!wp || slung) return;
      let a = wAng; if (a === undefined) { a = ['spear', 'pilum', 'pike', 'lance', 'naginata', 'flag', 'banner', 'staff', 'pollaxe', 'torch'].includes(wp) && rsh < 60 ? Math.PI : (wp === 'bow' ? Math.PI / 2 : wp === 'rifle' && rsh < 60 ? Math.PI * 0.92 : wp === 'sword' && rsh < 40 ? -0.35 : -ang); }
      if (wp === 'bow') weapon(g, wp, H[0], H[1], wL * u, a, { lw, t });
      else weapon(g, wp, H[0], H[1], wL * u, a, { lw, t, flag: o.flag, pennant: o.pennant, color: o.lanceColor, bayonet: o.bayonet });
    },
  });
  if (shieldFront) {
    const sz = (sh.s || ({ kite: 52, heater: 40, scutum: 62, round: 42, buckler: 26, pavise: 70, riot: 70 }[sh.type] || 40)) * u;
    const sxp = (sh.x ?? (o.pose === 'guard' ? 2 : ['push', 'lunge', 'brace'].includes(o.pose) ? 10 : -14)) * u, syp = (sh.y ?? -38) * u;
    shield(g, sxp, syp + br, sz, { ...sh, lw, rot: sh.rot ?? (o.pose === 'guard' ? 0 : -0.06) });
  }
  if (sh && sh.back) shield(g, -16 * u, -40 * u, 40 * u, { ...sh, lw, back: true });
  g.restore();
  g.restore();
  return { x, y, h, head: [x + (o.flip ? -hx : hx), y + hy + br], R, hand: right.H };
}
// ====================================================================================== HIEP SI AO LUOI (than + mu trum lien 1 khoi)
// Hinh dang hat dau: mu nhon co dai vang dinh tan + song mui, mu luoi trum lien than, o mat chu nhat bo tron chi lo mat (mieng bi tam che co day buoc),
// ao luoi dai toi goi, that lung + khoa vong, kiem deo ben hong, tay ong luoi co bao da o co tay, gang trang, chan ngan giay nau.
function hoodKnight(g, u, o, lw, t, W, A, br) {
  const [lsh, lel, rsh, rel] = A, side = W && W.mode === 'side';
  g.save(); g.translate(0, br);
  if (side) { g.save(); g.scale(0.9, 1); }
  const HW = 21 * u, top = -76 * u, hem = -12 * u, base = o.mailColor || PAL.mail;
  // vat ao duoi (mau ao trong) lo duoi gau luoi
  shape(g, (c) => { c.moveTo(-HW * 0.98, hem - 3 * u); c.lineTo(HW * 0.98, hem - 3 * u); c.lineTo(HW * 0.95, hem + 3.2 * u); c.quadraticCurveTo(0, hem + 4.5 * u, -HW * 0.95, hem + 3.2 * u); c.closePath(); }, { fill: o.tunicColor || PAL.redDark, lw });
  // than + mu trum: 1 khoi
  const sY = -52 * u;
  const body = (c) => { c.moveTo(-HW * 0.88, sY - 4 * u); c.quadraticCurveTo(-HW * 0.94, -30 * u, -HW * 0.98, hem); c.quadraticCurveTo(0, hem + 2.5 * u, HW * 0.98, hem); c.quadraticCurveTo(HW * 0.94, -30 * u, HW * 0.88, sY - 4 * u); c.closePath(); };
  shape(g, body, { fill: mailFill(g, 1.8 * u, base), lw, inner: (c) => { c.fillStyle = alpha('#2a2030', 0.16); c.fillRect(HW * 0.42, sY - 10 * u, HW, 90 * u); line(c, [[0, -28 * u], [0, hem + 2 * u]], { lw: lw * 0.7 }); } });
  if (o.tabard) { const tb = o.tabardColor || PAL.yellow, tT = -50 * u, tB = hem - 1 * u;
    shape(g, (c) => { c.moveTo(-HW * 0.8, tT); c.lineTo(HW * 0.8, tT); c.lineTo(HW * 0.9, tB); c.quadraticCurveTo(0, tB + 2 * u, -HW * 0.9, tB); c.closePath(); }, { fill: tb, lw, inner: (c) => { charge(c, o.charge, 0, tT + (tB - tT) * 0.36, (o.chargeS || 0.95) * 24 * u, o.chargeColor || PAL.red, null, lw * 0.6); c.fillStyle = alpha('#000', 0.1); c.fillRect(HW * 0.4, tT, HW, 60 * u); } }); }
  // that lung + kiem
  const by = -29 * u;
  if (o.weapon === 'sword' || o.sheathed) { g.save(); g.translate(-13 * u, by + 1 * u); g.rotate(0.12); tube(g, [[0, 0], [0, 24 * u]], 2.6 * u, PAL.leatherDark, lw); rect(g, -1.6 * u, 21.5 * u, 3.2 * u, 3.4 * u, { fill: PAL.gold, lw: lw * 0.7, r: 1 }); g.restore(); }
  shape(g, (c) => { c.moveTo(-HW * 1.05, by - 1.8 * u); c.quadraticCurveTo(0, by - 0.6 * u, HW * 1.05, by - 1.8 * u); c.lineTo(HW * 1.05, by + 1.8 * u); c.quadraticCurveTo(0, by + 3 * u, -HW * 1.05, by + 1.8 * u); c.closePath(); }, { fill: o.beltColor || PAL.leather, lw });
  ring2(g, -1 * u, by + 0.6 * u, 2.2 * u, lw);
  if (o.weapon === 'sword' || o.sheathed) { g.save(); g.translate(-13 * u, by + 1 * u); g.rotate(0.12); rect(g, -4.5 * u, -1.6 * u, 9 * u, 1.8 * u, { fill: PAL.gold, lw: lw * 0.8, r: 0.6 * u }); tube(g, [[0, -1.6 * u], [0, -6.5 * u]], 1.8 * u, PAL.leather, lw * 0.8); circ(g, 0, -7.5 * u, 1.4 * u, { fill: PAL.gold, lw: lw * 0.7 }); g.restore(); }
  if (side) g.restore();
  // tay (ca 2 ve truoc than, men theo hong)
  const armOne = (sgn, shA, elA, hold) => {
    const sx = sgn * 18.6 * u, sy = -50 * u, L = 12 * u;
    const [S, Eb, H] = armPts(sx, sy, sgn, shA, elA, u, L);
    const mf = mailFill(g, 1.8 * u, base);
    tube(g, [S, Eb, H], 6 * u, mf, lw);
    // bao co tay bang da
    const dx = H[0] - Eb[0], dy = H[1] - Eb[1], d = Math.hypot(dx, dy) || 1, cx0 = H[0] - dx / d * 3.6 * u, cy0 = H[1] - dy / d * 3.6 * u;
    tube(g, [[cx0 - dx / d * 2.4 * u, cy0 - dy / d * 2.4 * u], [cx0 + dx / d * 0.8 * u, cy0 + dy / d * 0.8 * u]], 7.2 * u, o.cuff || '#8c3a2b', lw * 0.9);
    if (hold) hold(H);
    glove(g, H[0], H[1], 3.6 * u, lw, sgn, Math.atan2(H[1] - Eb[1], H[0] - Eb[0]));
    return H;
  };
  // tay trai: tu the mac dinh dat tay len chuoi kiem
  const leftA = (o.pose === 'stand' || !o.pose) && (o.weapon === 'sword' || o.sheathed) ? [2, -50] : [lsh, lel];
  armOne(-1, leftA[0], leftA[1]);
  let H2;
  const wp = o.weapon && o.weapon !== 'sword' ? o.weapon : ((o.pose || 'stand') !== 'stand' && o.weapon === 'sword' && !o.sheathed ? 'sword' : null);
  H2 = armOne(1, rsh, rel, wp ? (H) => { const a = o.weaponAng ?? (['spear', 'pilum', 'pike', 'lance', 'flag', 'banner', 'staff', 'pollaxe'].includes(wp) && rsh < 60 ? Math.PI : wp === 'bow' ? Math.PI / 2 : -(rsh + rel) * Math.PI / 180); weapon(g, wp, H[0], H[1], (o.weaponLen || ({ sword: 34, spear: 62, lance: 70, axe: 50, bow: 40, flag: 60, pollaxe: 50, torch: 34 }[wp] || 40)) * u, a, { lw, t, flag: o.flag, pennant: o.pennant }); } : null);
  const drawHead = () => {
  // mu trum luoi: khoi tron day bo cong o cam (lo duong cong cam), rong bang mu
  const hood = (c) => { c.moveTo(-HW, top); c.lineTo(-HW * 1.03, sY - 10 * u); c.bezierCurveTo(-HW * 1.02, sY + 1 * u, -HW * 0.6, sY + 2.4 * u, 0, sY + 2.4 * u); c.bezierCurveTo(HW * 0.6, sY + 2.4 * u, HW * 1.02, sY + 1 * u, HW * 1.03, sY - 10 * u); c.lineTo(HW, top); c.closePath(); };
  shape(g, hood, { fill: mailFill(g, 1.8 * u, base), lw, inner: (c) => { c.fillStyle = alpha('#2a2030', 0.16); c.fillRect(HW * 0.42, top - 10 * u, HW, 90 * u); } });
  // o mat
  const fwx = 12.8 * u, fy0 = -77.5 * u, fy1 = -60 * u;
  shape(g, (c) => { c.moveTo(-fwx, fy0); c.lineTo(fwx, fy0); c.lineTo(fwx, fy1 - 6 * u); c.quadraticCurveTo(fwx, fy1, fwx - 6 * u, fy1); c.lineTo(-fwx + 6 * u, fy1); c.quadraticCurveTo(-fwx, fy1, -fwx, fy1 - 6 * u); c.closePath(); }, { fill: o.skin || '#f3e0d6', lw, inner: (c) => {
    c.fillStyle = alpha('#c9a9a4', 0.55); c.fillRect(-fwx, fy0, fwx * 2, 2.4 * u); c.fillRect(-fwx, fy0, 2.2 * u, 30 * u);
    const F = FACES[o.face] || (typeof o.face === 'object' ? o.face : FACES.neutral);
    face(c, (o.look || 0) * 1.2 * u, -68.6 * u, 20 * u, { ...o, lw, mouthHidden: true, face: { ...F, eyes: F.eyes === 'dot' || F.eyes === 'open' ? 'wide' : F.eyes }, eyeY: 0, t });
  } });
  // tam che mieng: mep duoi o mat + day buoc
  line(g, [[-fwx + 1 * u, fy1 - 0.3 * u], [fwx - 1 * u, fy1 - 0.3 * u]], { lw: lw * 2.2, ink: OUT });
  line(g, [[-fwx + 1.4 * u, fy1 - 0.3 * u], [fwx - 1.4 * u, fy1 - 0.3 * u]], { lw: lw * 1.1, ink: PAL.leather });
  line(g, [[fwx - 3 * u, fy1 - 1 * u], [fwx + 2.2 * u, fy1 + 2.2 * u]], { lw: lw * 0.9, ink: PAL.leather }); line(g, [[fwx - 2.4 * u, fy1 - 0.4 * u], [fwx + 1.2 * u, fy1 - 3 * u]], { lw: lw * 0.9, ink: PAL.leather });
  if (o.helmet === 'coif') {
    shape(g, (c) => { c.moveTo(-HW * 1.0, -76 * u); c.bezierCurveTo(-HW * 1.04, -96 * u, -HW * 0.5, -100 * u, 0, -100 * u); c.bezierCurveTo(HW * 0.5, -100 * u, HW * 1.04, -96 * u, HW * 1.0, -76 * u); c.closePath(); }, { fill: mailFill(g, 1.8 * u, base), lw: 0, inner: (c) => { c.fillStyle = alpha('#2a2030', 0.16); c.fillRect(HW * 0.42, -110 * u, HW, 40 * u); } });
    g.save(); g.beginPath(); g.moveTo(-HW * 1.0, -76 * u); g.bezierCurveTo(-HW * 1.04, -96 * u, -HW * 0.5, -100 * u, 0, -100 * u); g.bezierCurveTo(HW * 0.5, -100 * u, HW * 1.04, -96 * u, HW * 1.0, -76 * u); g.lineWidth = lw; g.strokeStyle = OUT; g.lineCap = 'round'; g.stroke(); g.restore();
    return;
  }
  // mu nhon
  const bandY = -80 * u, bandH = 5 * u, apex = -103 * u, metal = o.metal || PAL.steel;
  shape(g, (c) => { c.moveTo(-HW * 1.03, bandY + 1 * u); c.bezierCurveTo(-HW * 1.05, -93 * u, -HW * 0.55, -101 * u, 0, apex); c.bezierCurveTo(HW * 0.55, -101 * u, HW * 1.05, -93 * u, HW * 1.03, bandY + 1 * u); c.closePath(); }, { fill: metal, lw, inner: (c) => {
    c.fillStyle = alpha(PAL.steelDark, 0.45); c.beginPath(); c.moveTo(1 * u, apex); c.bezierCurveTo(HW * 0.6, -101 * u, HW * 1.12, -93 * u, HW * 1.12, bandY + 2 * u); c.lineTo(1.5 * u, bandY + 2 * u); c.closePath(); c.fill();
    line(c, [[0, apex + 1 * u], [0, bandY]], { lw: lw * 0.5, ink: alpha(OUT, 0.5) });
    c.globalAlpha = 0.6; line(c, [[-HW * 0.55, -84 * u], [-HW * 0.28, -94 * u]], { lw: 1.4 * u, ink: '#fff' }); c.globalAlpha = 1;
    if (o.helmet === 'spangen') for (const k of [-0.55, 0.55]) line(c, [[k * 3 * u, apex + 2 * u], [k * HW * 1.6, bandY]], { lw: 2.2 * u, ink: PAL.gold });
  } });
  shape(g, (c) => c.roundRect(-HW * 1.04, bandY - bandH / 2, HW * 2.08, bandH, 1.2 * u), { fill: o.band || PAL.gold, lw, inner: (c) => { c.fillStyle = alpha(PAL.goldDark, 0.45); c.fillRect(HW * 0.4, bandY - bandH, HW, bandH * 2); for (let i = -4; i <= 4; i++) circ(c, i * HW * 0.23, bandY, 0.75 * u, { fill: lighter(o.band || PAL.gold, 0.25), lw: lw * 0.45 }); } });
  // song mui
  shape(g, (c) => c.roundRect(-1.6 * u, bandY - 1 * u, 3.2 * u, 16 * u, 0.8 * u), { fill: PAL.steelLight, lw, inner: (c) => { c.fillStyle = alpha(PAL.steelDark, 0.6); c.fillRect(0.2 * u, bandY - 2 * u, 2 * u, 20 * u); } });
  };
  drawHead();
  if (o.shield && (o.shield.front || o.pose === 'guard')) shield(g, (o.shield.x ?? -4) * u, (o.shield.y ?? -36) * u, (o.shield.s || 56) * u, { ...o.shield, lw, rot: o.shield.rot ?? 0 });
  if (o.crownOn) helmetCrownSmall(g, 0, -86 * u, 18 * u, lw);
  g.restore();
  return H2;
}
// gang trang co ngon (kieu kenh mau): long ban tay + 3 ngon cong + ngon cai
export function glove(g, x, y, r, lw, s, ang, col = '#ffffff') {
  g.save(); g.translate(x, y); g.rotate(ang - Math.PI / 2);
  shape(g, (c) => { c.roundRect(-r, -r * 0.9, r * 2, r * 1.9, r * 0.7); }, { fill: col, lw, inner: (c) => { for (const k of [-0.45, 0.05, 0.5]) line(c, [[k * r, r * 0.95], [k * r, r * 0.25]], { lw: lw * 0.5 }); c.fillStyle = alpha('#9aa0b0', 0.25); c.fillRect(r * 0.3, -r, r, r * 2); } });
  ellipse(g, s * r * 1.0, -r * 0.05, r * 0.45, r * 0.32, { fill: col, lw: lw * 0.85, rot: s * 0.8 });
  g.restore();
}
// ====================================================================================== HIEP SI GIAP TAM (mu tron lon trum dau, mat na lat len, tam che cam)
function plateKnight(g, u, o, lw, t, W, A, br) {
  const [lsh, lel, rsh, rel] = A, side = W && W.mode === 'side', ST = PAL.steel, SL = PAL.steelLight, SD = PAL.steelDark;
  g.save(); g.translate(0, br);
  // than: ao choang huy hieu (tabard) tren giap
  if (side) { g.save(); g.scale(0.88, 1); }
  const tTop = -50 * u, tBot = o.tabard === false ? -20 * u : -15 * u - (o.skirt ?? 0.35) * 8 * u, wT = 11.5 * u, wB = 12.5 * u;
  shape(g, (c) => c.roundRect(-wT + 1 * u, tTop, (wT - 1 * u) * 2, -22 * u - tTop, 3 * u), { fill: ST, lw }); // giap than duoi ao
  if (o.tabard !== false) {
    const tb = o.tabardColor || PAL.yellow;
    shape(g, (c) => { c.moveTo(-wT, tTop + 2 * u); c.quadraticCurveTo(-wT, tTop, -wT + 3 * u, tTop); c.lineTo(wT - 3 * u, tTop); c.quadraticCurveTo(wT, tTop, wT, tTop + 2 * u); c.lineTo(wB, tBot); c.lineTo(-wB, tBot); c.closePath(); }, { fill: tb, lw, inner: (c) => {
      if (o.charge === 'quarter') { const cc = o.chargeColor || PAL.blue, mid = (tTop + tBot) / 2; c.fillStyle = cc; c.fillRect(-wB, tTop, wB, mid - tTop); c.fillRect(0, mid, wB, tBot - mid); charge(c, 'lion', wB / 2, (tTop + mid) / 2, 9 * u, PAL.yellow, null, lw * 0.5); charge(c, 'fleur', -wB / 2, (mid + tBot) / 2, 7 * u, PAL.yellow, null, lw * 0.5); charge(c, 'fleur', -wB / 2, (tTop + mid) / 2, 7 * u, PAL.yellow, null, lw * 0.5); charge(c, 'lion', wB / 2, (mid + tBot) / 2, 9 * u, PAL.yellow, null, lw * 0.5); }
      else charge(c, o.charge, 0, tTop + (tBot - tTop) * 0.4, (o.chargeS || 0.98) * 22 * u, o.chargeColor || PAL.red, null, lw * 0.6);
      c.fillStyle = alpha('#000', 0.1); c.fillRect(wT * 0.5, tTop, wT, 60 * u);
    } });
  }
  const by = tBot - 5 * u; rect(g, -wB * 1.02, by - 1.6 * u, wB * 2.04, 3.2 * u, { fill: o.beltColor || PAL.leather, lw: lw * 0.9, r: 1 }); circ(g, 0, by, 1.4 * u, { fill: PAL.gold, lw: lw * 0.6 });
  if (side) g.restore();
  // tay: ong thep manh, couter tron o khuyu, gang thep co ngon
  const armOne = (sgn, shA, elA, hold) => {
    const sx = sgn * 12.5 * u, sy = -48 * u, L = 10.5 * u;
    const [S, Eb, H] = armPts(sx, sy, sgn, shA, elA, u, L);
    tube(g, [S, Eb], 4.6 * u, ST, lw); tube(g, [Eb, H], 4.4 * u, ST, lw);
    circ(g, Eb[0], Eb[1], 2.7 * u, { fill: SL, lw: lw * 0.9, inner: (c) => circ(c, Eb[0], Eb[1], 1 * u, { fill: SD, lw: 0 }) });
    if (hold) hold(H);
    glove(g, H[0], H[1], 3.1 * u, lw, sgn, Math.atan2(H[1] - Eb[1], H[0] - Eb[0]), o.gauntlet === false ? '#ffffff' : '#e6e3df');
    return H;
  };
  const upL = lsh > 95, upR = rsh > 95;
  if (!upL) armOne(-1, lsh, lel);
  const wp = o.weapon;
  const rightArm = () => armOne(1, rsh, rel, wp ? (H) => { const a = o.weaponAng ?? (['spear', 'pilum', 'pike', 'lance', 'flag', 'banner', 'staff', 'pollaxe', 'torch'].includes(wp) && rsh < 60 ? Math.PI : wp === 'bow' ? Math.PI / 2 : wp === 'sword' && rsh < 40 ? -0.35 : -(rsh + rel) * Math.PI / 180); weapon(g, wp, H[0], H[1], (o.weaponLen || ({ sword: 30, spear: 56, lance: 64, pollaxe: 46, axe: 44, flag: 56, torch: 30 }[wp] || 36)) * u, a, { lw, t, flag: o.flag, pennant: o.pennant, color: o.lanceColor }); } : null);
  let H2 = upR ? null : rightArm();
  // vai: tam giap nho nhieu lop
  for (const sg of [-1, 1]) shape(g, (c) => c.roundRect(sg * 12.5 * u - 5.5 * u, -52 * u, 11 * u, 7 * u, [3 * u, 3 * u, 2 * u, 2 * u]), { fill: SL, lw: lw * 0.9, inner: (c) => { line(c, [[sg * 12.5 * u - 6 * u, -48.5 * u], [sg * 12.5 * u + 6 * u, -48.5 * u]], { lw: lw * 0.5 }); c.fillStyle = alpha(SD, 0.4); c.fillRect(sg * 12.5 * u, -53 * u, 6 * u, 9 * u); } });
  // dau
  const hx = (o.look || 0) * 0.6 * u, cy = -63 * u, R = 15 * u;
  circ(g, hx * 0.3, cy, R, { fill: o.skin || PAL.skin, lw, inner: (c) => celShade(c, hx * 0.3, cy, R, alpha(PAL.skinShade, 0.85), -0.28, 0.08, 1.02) });
  const hl = o.helmet;
  const F = typeof o.face === 'object' ? o.face : (FACES[o.face] || FACES.neutral);
  if (hl === 'bascinet' && o.visor !== 'down') face(g, hx, cy + 0.5 * u, 17 * u, { ...o, lw, face: F, mouthHidden: !!(o.bevor === false ? false : F.mouth === 'flat'), eyeY: 0.05, t });
  // mu tron lon (bascinet): vom to trum dau, 2 ben xuong toi ham, chua lo mat
  if (hl === 'bascinet') {
    shape(g, (c) => { c.moveTo(-23 * u, -53 * u); c.bezierCurveTo(-27 * u, -72 * u, -22 * u, -97 * u, 0, -99 * u); c.bezierCurveTo(22 * u, -97 * u, 27 * u, -72 * u, 23 * u, -53 * u); c.lineTo(16.5 * u, -53 * u); c.bezierCurveTo(17.5 * u, -62 * u, 15 * u, -71 * u, 0, -71.5 * u); c.bezierCurveTo(-15 * u, -71 * u, -17.5 * u, -62 * u, -16.5 * u, -53 * u); c.closePath(); }, { fill: SL, lw, inner: (c) => {
      c.fillStyle = alpha(SD, 0.42); c.beginPath(); c.moveTo(6 * u, -99 * u); c.bezierCurveTo(26 * u, -96 * u, 30 * u, -70 * u, 25 * u, -50 * u); c.lineTo(12 * u, -50 * u); c.bezierCurveTo(16 * u, -68 * u, 14 * u, -88 * u, 6 * u, -99 * u); c.fill();
      c.globalAlpha = 0.75; line(c, [[-17 * u, -66 * u], [-15 * u, -84 * u], [-8 * u, -93 * u]], { lw: 1.3 * u, ink: '#fff' }); c.globalAlpha = 1;
    } });
    circ(g, 17.5 * u, -66 * u, 1.3 * u, { fill: PAL.gold, lw: lw * 0.6 });
    // tam che cam (bevor)
    if (o.bevor !== false) shape(g, (c) => c.roundRect(-10.5 * u, -55.5 * u, 21 * u, 9 * u, [1.5 * u, 1.5 * u, 2.5 * u, 2.5 * u]), { fill: SL, lw, inner: (c) => { c.fillStyle = alpha(SD, 0.4); c.fillRect(3 * u, -56 * u, 12 * u, 10 * u); line(c, [[-10.5 * u, -51.5 * u], [10.5 * u, -51.5 * u]], { lw: lw * 0.55, a: 0.6 }); } });
    if (o.visor === 'down') {
      shape(g, (c) => { c.moveTo(-16 * u, -71 * u); c.quadraticCurveTo(0, -75 * u, 16 * u, -71 * u); c.lineTo(17 * u, -56 * u); c.quadraticCurveTo(8 * u, -52 * u, 0, -50 * u); c.quadraticCurveTo(-8 * u, -52 * u, -17 * u, -56 * u); c.closePath(); }, { fill: ST, lw, inner: (c) => { c.fillStyle = alpha(SD, 0.4); c.fillRect(2 * u, -76 * u, 16 * u, 30 * u); } });
      rect(g, -11 * u, -66.5 * u, 8.5 * u, 2.2 * u, { fill: OUT, lw: 0, r: 1 * u }); rect(g, 2.5 * u, -66.5 * u, 8.5 * u, 2.2 * u, { fill: OUT, lw: 0, r: 1 * u });
      for (let i = 0; i < 6; i++) circ(g, (3 + (i % 3) * 2.2) * u, (-60 + Math.floor(i / 3) * 2.2) * u, 0.55 * u, { fill: OUT, lw: 0 });
    } else if (o.visor !== 'none') {
      // mat na lat len: tam lon bo tron tren dinh, 2 khe doc (hinh so 8), lo tho
      g.save(); g.translate(7 * u, -89 * u); g.rotate(0.2);
      shape(g, (c) => c.roundRect(-12 * u, -10 * u, 24 * u, 20 * u, [5 * u, 7 * u, 4 * u, 4 * u]), { fill: lighter(ST, 0.06), lw, inner: (c) => { c.fillStyle = alpha(SD, 0.4); c.fillRect(4 * u, -12 * u, 10 * u, 24 * u); c.fillStyle = alpha('#fff', 0.5); c.fillRect(-11 * u, 4 * u, 22 * u, 1.2 * u); } });
      for (const yy of [-6.5, 0.5]) shape(g, (c) => c.roundRect(-3.4 * u, yy * u, 3.6 * u, 6 * u, 1.8 * u), { fill: PAL.steelDark, lw: lw * 0.8 });
      for (let i = 0; i < 6; i++) circ(g, (3 + (i % 2) * 2) * u, (-5 + Math.floor(i / 2) * 2) * u, 0.55 * u, { fill: OUT, lw: 0 });
      g.restore();
      if (o.plume) { const pc = o.plume === true ? PAL.yellow : o.plume; shape(g, (c) => { c.moveTo(2 * u, -98 * u); c.quadraticCurveTo(12 * u, -108 * u, 24 * u, -104 * u); c.quadraticCurveTo(14 * u, -101 * u, 6 * u, -96 * u); c.closePath(); }, { fill: pc, lw: lw * 0.8 }); }
    }
  } else if (hl === 'bucket') {
    shape(g, (c) => c.roundRect(-18 * u, -86 * u, 36 * u, 36 * u, [9 * u, 9 * u, 3 * u, 3 * u]), { fill: SL, lw, inner: (c) => { c.fillStyle = alpha(SD, 0.42); c.fillRect(7 * u, -90 * u, 14 * u, 44 * u); c.globalAlpha = 0.7; line(c, [[-13 * u, -56 * u], [-13 * u, -78 * u]], { lw: 1.4 * u, ink: '#fff' }); c.globalAlpha = 1; } });
    rect(g, -15 * u, -70 * u, 13 * u, 3.4 * u, { fill: OUT, lw: 0, r: 1.4 * u }); rect(g, 2 * u, -70 * u, 13 * u, 3.4 * u, { fill: OUT, lw: 0, r: 1.4 * u });
    const lk = (o.look || 0) * 1.5 * u; circ(g, -8 * u + lk, -68.3 * u, 1.1 * u, { fill: '#fff', lw: 0 }); circ(g, 8.5 * u + lk, -68.3 * u, 1.1 * u, { fill: '#fff', lw: 0 });
    rect(g, -1.3 * u, -71 * u, 2.6 * u, 19 * u, { fill: o.cross || ST, lw: lw * 0.7, r: 0.6 * u });
    for (let i = 0; i < 6; i++) circ(g, (5 + (i % 3) * 2.4) * u, (-61 + Math.floor(i / 3) * 2.6) * u, 0.6 * u, { fill: OUT, lw: 0 });
  }
  if (upL) armOne(-1, lsh, lel);
  if (upR) H2 = rightArm();
  if (o.crownOn) helmetCrownSmall(g, 0, -95 * u, 16 * u, lw);
  if (o.shield && !o.shield.back) { const sh = o.shield; shield(g, (sh.x ?? (o.pose === 'guard' ? 2 : -12)) * u, (sh.y ?? -34) * u, (sh.s || ({ kite: 46, heater: 34, round: 36 }[sh.type] || 34)) * u, { ...sh, lw, rot: sh.rot ?? -0.06 }); }
  g.restore();
  return H2;
}
function ring2(g, x, y, r, lw) { g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.lineWidth = r * 0.75 + lw * 2; g.strokeStyle = OUT; g.stroke(); g.lineWidth = r * 0.75; g.strokeStyle = PAL.gold; g.stroke(); g.restore(); }
function helmetCrownSmall(g, cx, cy, R, lw) {
  const y = cy - R * 1.32, w = R * 0.8;
  shape(g, (c) => { c.moveTo(cx - w, y + R * 0.2); c.lineTo(cx - w, y - R * 0.2); c.lineTo(cx - w * 0.5, y); c.lineTo(cx, y - R * 0.3); c.lineTo(cx + w * 0.5, y); c.lineTo(cx + w, y - R * 0.2); c.lineTo(cx + w, y + R * 0.2); c.closePath(); }, { fill: PAL.gold, lw });
}
import { label } from './ink.js';

// can canh ban than (phan ung): bust(g, x, y, R, o) — dau ban kinh R o tam (x,y), vai ben duoi
export function bust(g, x, y, R, o = {}) {
  const sh = o.shield; o = { ...(CAST[o.preset] || {}), ...o }; if (sh === null) o.shield = null;
  const h = R / 0.19; // tuong duong chieu cao nhan vat
  soldier(g, x, y + 78 * h / 100, h, { ...o, lod: 'high' });
}

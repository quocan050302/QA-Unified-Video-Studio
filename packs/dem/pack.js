// pack.js — bo phong cach "dem": phim ngan hoat hinh KHONG LOI DOC ve ky luat, cam do, lam lai tu dau (kieu kenh self-improvement).
// Nen toi, net manh sang, nhan vat dau tron mau kem, "giong noi" la bong den phat sang mau nhan, chu ke chuyen trang,
// chu cam do viet tay mau nhan, bo dem DAY N goc trai. config.json: "pack": "dem", "accent": "red" | "pink" | "amber" | "teal".
import { E } from '/engine/core.js';
import './templates.js';
export * from './ink.js';
export * from './bean.js';
export * from './sets.js';
export * from './phone.js';
export * from './templates.js';
export { thumb } from './thumb.js';
export { img, E } from '/engine/core.js';

function css(href) { return new Promise((r) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; l.onload = r; l.onerror = r; document.head.appendChild(l); }); }
export async function init(E) {
  await Promise.all(['comic-neue/700.css', 'comic-neue/400.css', 'caveat/700.css', 'luckiest-guy/400.css', 'be-vietnam-pro/700.css'].map((f) => css('/node_modules/@fontsource/' + f)));
  await Promise.all([document.fonts.load('700 40px "Comic Neue"', 'Day after day.'), document.fonts.load('700 40px "Caveat"', 'just one more'), document.fonts.load('400 40px "Luckiest Guy"', 'WAKE UP.'), document.fonts.load('700 40px "Be Vietnam Pro"', 'Seen')]);
  if (!E.cfg.style || E.cfg.style === 'dusk') E.cfg.style = 'flat';
  if (E.cfg.bars === null || E.cfg.bars === undefined) E.cfg.bars = E.vertical ? 'none' : 'scope';
  if (!E.cfg.captionStyle) E.cfg.captionStyle = 'dem';
}
// phim khong loi doc: khong co phu de tu dong (chu ke chuyen nam trong tung canh)
export function captions() {}

import { thumb } from '/packs/squire/pack.js';
// Thumbnail video dai: nen canh mo + nhan vat lon + 1 ky hieu do + 1-3 chu trang vien den
thumb({
  bg: 'plain', time: 'sunset',
  back: [{ preset: 'hastatus', rows: 3, cols: 16, x0: 0, x1: 0.62, yFront: 0.86, yBack: 0.7, hFront: 0.2, hBack: 0.1 }],
  hero: { preset: 'hastatus', x: 0.73, y: 0.5, R: 0.21, face: 'tired', pose: 'hold', weapon: 'shovel', shield: null },
  symbols: [{ kind: 'arrow', x: 0.2, y: 0.5, to: [0.42, 0.72], r: 0.2 }],
  title: ['EVERY', 'NIGHT?'], tx: 0.27, ty: 0.17, tsize: 0.2,
});

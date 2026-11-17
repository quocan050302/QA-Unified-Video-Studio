// thumb.js — Original Squire Roman Thumbnail for KH-03.0 Pilot
import { thumb } from '/packs/squire/pack.js';

thumb({
  bg: 'roman_training_yard',
  time: 'dawn',
  seed: 17,
  blur: 6,
  heroes: [
    {
      preset: 'hastatus',
      full: true,
      x: 0.70,
      y: 1.03,
      h: 0.72,
      flip: true,
      face: 'shock',
      look: 0.6,
      romanMasterPolish: true,
      shield: { type: 'scutum', color: '#c9473a', rim: '#e7b04a', charge: 'lightning', chargeColor: '#efc23f', x: -10, y: -38, s: 62 },
    },
    {
      preset: 'princeps',
      full: true,
      x: 0.24,
      y: 1.02,
      h: 0.68,
      face: 'sternNod',
      look: 0.55,
      romanMasterPolish: true,
    },
  ],
  symbols: [
    { kind: 'wooden_practice_spear', x: 0.47, y: 0.58, r: 0.34, ang: -Math.PI * 0.48 },
  ],
  title: ['LAST GAP', 'SHIELD WALL'],
  tx: 0.50,
  ty: 0.11,
  tsize: 0.135,
  tgap: 0.145,
});

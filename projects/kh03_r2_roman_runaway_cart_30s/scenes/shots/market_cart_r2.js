// market_cart_r2.js — Fail-Closed Runtime 2D Scene Binder for KH-03.0.R2 (roman_action_director_v2).
// Strictly 2D Canvas via renderScriptShotFrame() -> renderRomanAction2D(). Zero Three.js.
import { registerShot, E } from '/engine/core.js';
import { renderScriptShotFrame } from '/packs/squire/pack.js';

registerShot('SH01', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (0.0 + lt)); } });
registerShot('SH02', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (2.292 + lt)); } });
registerShot('SH03', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (5.292 + lt)); } });
registerShot('SH04', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (6.458 + lt)); } });
registerShot('SH05', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (7.875 + lt)); } });
registerShot('SH06', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (10.25 + lt)); } });
registerShot('SH07', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (12.083 + lt)); } });
registerShot('SH08', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (13.917 + lt)); } });
registerShot('SH09', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (15.25 + lt)); } });
registerShot('SH10', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (16.875 + lt)); } });
registerShot('SH11', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (18.5 + lt)); } });
registerShot('SH12', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (19.833 + lt)); } });
registerShot('SH13', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (21.375 + lt)); } });
registerShot('SH14', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (23.583 + lt)); } });
registerShot('SH15', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (25.542 + lt)); } });
registerShot('SH16', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (27.5 + lt)); } });

for (const s of (E.shots || [])) {
  if (s?.id && !['SH01', 'SH02', 'SH03', 'SH04', 'SH05', 'SH06', 'SH07', 'SH08', 'SH09', 'SH10', 'SH11', 'SH12', 'SH13', 'SH14', 'SH15', 'SH16'].includes(s.id)) {
    registerShot(s.id, { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (s.start + lt)); } });
  }
}

// gate_message_r1.js — Runtime 2D Scene Binder for KH-03.0.R1 Script-Driven Film.
// 100% 2D Canvas via Production Squire renderScriptShotFrame(). Zero Three.js.
import { registerShot, E } from '/engine/core.js';
import { renderScriptShotFrame } from '/packs/squire/pack.js';

registerShot('SH01', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (0.0 + lt)); } });
registerShot('SH02', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (1.5833 + lt)); } });
registerShot('SH03', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (4.4167 + lt)); } });
registerShot('SH04', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (7.25 + lt)); } });
registerShot('SH05', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (9.1667 + lt)); } });
registerShot('SH06', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (10.75 + lt)); } });
registerShot('SH07', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (12.875 + lt)); } });
registerShot('SH08', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (15.0 + lt)); } });
registerShot('SH09', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (16.7917 + lt)); } });
registerShot('SH10', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (18.6667 + lt)); } });
registerShot('SH11', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (20.25 + lt)); } });
registerShot('SH12', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (23.0833 + lt)); } });
registerShot('SH13', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (25.7917 + lt)); } });
registerShot('SH14', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (27.0833 + lt)); } });
registerShot('SH15', { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (28.5 + lt)); } });

// Also bind any dynamically injected shot_plan shots cleanly at runtime:
for (const s of (E.shots || [])) {
  if (s?.id && !['SH01', 'SH02', 'SH03', 'SH04', 'SH05', 'SH06', 'SH07', 'SH08', 'SH09', 'SH10', 'SH11', 'SH12', 'SH13', 'SH14', 'SH15'].includes(s.id)) {
    registerShot(s.id, { draw(g, lt, info) { renderScriptShotFrame(g, info?.globalT ?? (s.start + lt)); } });
  }
}

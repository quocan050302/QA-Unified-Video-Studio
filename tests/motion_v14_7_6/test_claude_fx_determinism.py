"""Real determinism, alpha-bounds, and voice/camera separation tests for V14.7.6 Phase D (Claude Motion Assist)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_node(js: str) -> dict:
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    return json.loads(proc.stdout.strip())


def test_claude_provenance_and_license_present() -> None:
    lic = REPO_ROOT / "integrations" / "claude_motion" / "LICENSE"
    prov = REPO_ROOT / "integrations" / "claude_motion" / "SOURCE_PROVENANCE.json"
    assert lic.exists() and "Copyright (c) 2026 Hanif (@hanifproduktif)" in lic.read_text(encoding="utf-8")
    data = json.loads(prov.read_text(encoding="utf-8"))
    assert data["upstream_commit_sha"] == "4ddb8c80fdec96dc9f55d4b9bdee60bde6f0134b"
    assert data["license"] == "MIT"
    assert data["demo_characters_copied"] is False


def test_claude_seed_determinism_alpha_bounds_and_feature_flag() -> None:
    js = """
import {
  rng, eOut, eIn, eIO, eBack, exposure,
  burstParticles, landDust, ring, afterimages, applyHarborInteractionFX
} from './integrations/claude_motion/adapter.js';

function makeMockCtx() {
  const ops = [];
  const stack = [];
  const ctx = {
    globalAlpha: 1.0,
    fillStyle: '#000',
    strokeStyle: '#000',
    lineWidth: 1,
    lineCap: 'butt',
    minAlphaSeen: 1.0,
    maxAlphaSeen: 1.0,
    alphaOutOfBounds: false,
    save() { stack.push(this.globalAlpha); },
    restore() { this.globalAlpha = stack.length ? stack.pop() : 1.0; },
    beginPath() {},
    moveTo(x, y) { ops.push(['M', +x.toFixed(4), +y.toFixed(4), +this.globalAlpha.toFixed(4)]); },
    lineTo(x, y) { ops.push(['L', +x.toFixed(4), +y.toFixed(4), +this.globalAlpha.toFixed(4)]); },
    ellipse(x, y, rx, ry) {
      if (this.globalAlpha < 0 || this.globalAlpha > 1 || Number.isNaN(this.globalAlpha)) this.alphaOutOfBounds = true;
      this.minAlphaSeen = Math.min(this.minAlphaSeen, this.globalAlpha);
      this.maxAlphaSeen = Math.max(this.maxAlphaSeen, this.globalAlpha);
      ops.push(['E', +x.toFixed(4), +y.toFixed(4), +rx.toFixed(4), +ry.toFixed(4), +this.globalAlpha.toFixed(4)]);
    },
    stroke() {
      if (this.globalAlpha < 0 || this.globalAlpha > 1 || Number.isNaN(this.globalAlpha)) this.alphaOutOfBounds = true;
    },
    fill() {
      if (this.globalAlpha < 0 || this.globalAlpha > 1 || Number.isNaN(this.globalAlpha)) this.alphaOutOfBounds = true;
    },
    fillRect(x, y, w, h) {
      if (this.globalAlpha < 0 || this.globalAlpha > 1 || Number.isNaN(this.globalAlpha)) this.alphaOutOfBounds = true;
      ops.push(['R', +x.toFixed(4), +y.toFixed(4), +w.toFixed(4), +h.toFixed(4), +this.globalAlpha.toFixed(4)]);
    },
    createRadialGradient() { return { addColorStop() {} }; },
    ops,
  };
  return ctx;
}

const events = [
  { kind: 'foot_slip_spray', t0: 1.0, x: 420, y: 810, seed: 77 },
  { kind: 'lantern_gust_embers', t0: 1.05, x: 460, y: 690, seed: 88 },
  { kind: 'beacon_relight_pulse', t0: 1.1, x: 960, y: 280, seed: 99 },
];

// Feature flag 'none' => strict zero FX
const ctxNone = makeMockCtx();
const noneCount = applyHarborInteractionFX(ctxNone, { fxProfile: 'none', realT: 1.18, events, seed: 1476 });

// Forward vs reverse evaluation order => identical draw trace
const times = [1.02, 1.12, 1.24, 1.38];
const traceForward = {};
for (const t of times) {
  const c = makeMockCtx();
  applyHarborInteractionFX(c, { fxProfile: 'subtle_harbor_fx', realT: t, events, seed: 1476 });
  afterimages(c, t, (cc, pastT) => cc.ellipse(pastT * 100, 300, 10, 10), { n: 3, alpha: 0.3 });
  traceForward[t] = { ops: JSON.stringify(c.ops), alphaOutOfBounds: c.alphaOutOfBounds, finalAlpha: c.globalAlpha };
}
const traceReverse = {};
for (const t of [...times].reverse()) {
  const c = makeMockCtx();
  applyHarborInteractionFX(c, { fxProfile: 'subtle_harbor_fx', realT: t, events, seed: 1476 });
  afterimages(c, t, (cc, pastT) => cc.ellipse(pastT * 100, 300, 10, 10), { n: 3, alpha: 0.3 });
  traceReverse[t] = { ops: JSON.stringify(c.ops), alphaOutOfBounds: c.alphaOutOfBounds, finalAlpha: c.globalAlpha };
}

// Seeded RNG & exposure checks
const r1 = rng(1476), r2 = rng(1476);
const seq1 = [r1(), r1(), r1(), r1()];
const seq2 = [r2(), r2(), r2(), r2()];

console.log(JSON.stringify({
  noneCount,
  noneOpsLen: ctxNone.ops.length,
  rngEqual: JSON.stringify(seq1) === JSON.stringify(seq2),
  tracesEqual: times.every((t) => JSON.stringify(traceForward[t]) === JSON.stringify(traceReverse[t])),
  anyAlphaOutOfBounds: Object.values(traceForward).some((x) => x.alphaOutOfBounds || x.finalAlpha !== 1.0),
  eOutEnd: eOut(1),
  eInStart: eIn(0),
  eIOHalf: eIO(0.5),
  eBackEnd: eBack(1),
  twosAt0_05: exposure(0.05, 'twos', 24),
  onesAt0_05: exposure(0.05, 'ones', 24),
}));
"""
    res = _run_node(js)
    assert res["noneCount"] == 0 and res["noneOpsLen"] == 0
    assert res["rngEqual"] is True
    assert res["tracesEqual"] is True
    assert res["anyAlphaOutOfBounds"] is False
    assert abs(res["eOutEnd"] - 1.0) < 1e-9
    assert abs(res["eInStart"] - 0.0) < 1e-9
    assert abs(res["eIOHalf"] - 0.5) < 1e-9
    assert abs(res["eBackEnd"] - 1.0) < 1e-9
    assert abs(res["twosAt0_05"] - 0.0) < 1e-9
    assert abs(res["onesAt0_05"] - 0.05) < 1e-9


def test_separated_action_timewarp_never_freezes_voice_or_camera_cuts() -> None:
    js = """
import { createSeparatedActionClock, convertSoundCuesToRealTime } from './integrations/claude_motion/adapter.js';

const clock = createSeparatedActionClock({
  shotStartSec: 14.0,
  shotEndSec: 18.0,
  stops: [[15.2, 0.08], [16.4, 0.06]],
  fxProfile: 'subtle_harbor_fx',
});

let voiceAlwaysExact = true;
let cameraAlwaysExact = true;
let monotonicAction = true;
let prevAction = 14.0;
let frozenFrames = 0;

for (let i = 0; i <= 96; i++) {
  const realT = 14.0 + (i / 24);
  if (Math.abs(clock.voiceTime(realT) - realT) > 1e-12) voiceAlwaysExact = false;
  if (Math.abs(clock.cameraTime(realT) - realT) > 1e-12) cameraAlwaysExact = false;
  const actT = clock.actionTime(realT);
  if (actT + 1e-9 < prevAction) monotonicAction = false;
  prevAction = actT;
  if (clock.isActionFrozen(realT)) frozenFrames++;
}

const cues = convertSoundCuesToRealTime(
  [{ id: 'slip', time: 15.2 }, { id: 'catch_rail', time: 16.5 }],
  clock,
);

console.log(JSON.stringify({
  enabled: clock.enabled,
  voiceAlwaysExact,
  cameraAlwaysExact,
  monotonicAction,
  frozenFrames,
  startExact: Math.abs(clock.actionTime(14.0) - 14.0) < 1e-9,
  endExact: Math.abs(clock.actionTime(18.0) - 18.0) < 1e-9,
  cues,
}));
"""
    res = _run_node(js)
    assert res["enabled"] is True
    assert res["voiceAlwaysExact"] is True
    assert res["cameraAlwaysExact"] is True
    assert res["monotonicAction"] is True
    assert res["frozenFrames"] >= 2
    assert res["startExact"] is True
    assert res["endExact"] is True
    # Cue at 16.5 in action time occurs after first 0.08s + second 0.06s holds -> shifted forward in real time!
    assert res["cues"][1]["real_time"] > res["cues"][1]["action_time"]

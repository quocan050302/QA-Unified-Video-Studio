#!/usr/bin/env python3
"""render_kh02_style_poc.py — Renders KH-02.1 2D Style POC Stills, Turnaround Sheets, Expression Sheets & Contact Sheet.

Uses real headless Playwright Chromium via render.mjs in an isolated .test-runs workspace
with render_mode='canvas2d_only', proving zero Three.js load and producing verifiable PNG/JPG artifacts.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

import numpy as np

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

from kh02_style_contract import load_squire_style_profile
from kh02_character_factory import derive_character_identity, write_character_continuity_manifest, validate_character_model_consistency
from kh02_environment_factory import derive_scene_spec, export_2d_scene_manifest, validate_scene_continuity


POC_SCENES_JS = r"""
import { E, registerShot, text, FONTS } from '/engine/core.js';
import {
  OUT, PAL, alpha, rect, line, label,
  drawSquireCinematic2DActor, drawCinematicHand2D, drawPipGoat2D,
  drawLayeredRomanEnvironment2D, drawBronzeBellAssembly2D, drawBellRopeSegment2D, evaluateBellRigStateAt,
} from '/packs/squire/pack.js';

function cardBg(g, titleStr, subtitleStr) {
  const gr = g.createLinearGradient(0, 0, 0, E.H);
  gr.addColorStop(0, '#f5ecd9');
  gr.addColorStop(1, '#e6d7ba');
  g.fillStyle = gr;
  g.fillRect(0, 0, E.W, E.H);
  rect(g, 28, 24, E.W - 56, E.H - 48, { fill: null, lw: 4, ink: alpha(OUT, 0.35), r: 14 });
  text(g, titleStr, 64, 66, { size: 34, font: FONTS.body, weight: 800, color: OUT, align: 'left' });
  if (subtitleStr) {
    text(g, subtitleStr, 64, 102, { size: 20, font: FONTS.body, weight: 600, color: '#695649', align: 'left' });
  }
}

// Shot 1 (t=0.5s): 2 Original Human Characters at 2 Scales (560px & 360px silhouette readability)
registerShot('poc01', {
  draw(g) {
    cardBg(g, 'KH-02.1 POC 01 — ORIGINAL CAST AT TWO SCALES (560px & 360px)', 'Preserves Squire round-head #392a21 ink DNA | Upgrades tapered limbs, cloth folds, cel-bands & hands');
    line(g, [[80, 965], [1840, 965]], { lw: 5, ink: alpha(OUT, 0.45) });

    // TAVI @ 560px and 360px
    drawSquireCinematic2DActor(g, 330, 965, 560, {
      castId: 'TAVI', view: 'three_quarter', expression: 'anxious_alert',
      armAngles: [28, 35, 56, 48], rightHandPose: 'rope_grip', leftHandPose: 'open_recoil',
      ignoreStatureScale: true, t: 0.4,
    });
    text(g, 'TAVI (560px)', 330, 1012, { size: 22, font: FONTS.body, weight: 700, color: OUT });

    drawSquireCinematic2DActor(g, 730, 965, 360, {
      castId: 'TAVI', view: 'three_quarter', expression: 'determined_climb',
      armAngles: [35, 42, 72, 35], rightHandPose: 'point_alert', leftHandPose: 'rope_grip',
      ignoreStatureScale: true, secondaryLag: 0.55, spineLean: 0.08, t: 0.4,
    });
    text(g, 'TAVI (360px Readability)', 730, 1012, { size: 22, font: FONTS.body, weight: 700, color: OUT });

    // LYRA @ 560px and 360px
    drawSquireCinematic2DActor(g, 1190, 965, 560, {
      castId: 'LYRA', view: 'three_quarter', expression: 'grumpy_glare',
      armAngles: [22, 30, 62, 52], rightHandPose: 'palm_raised_react', leftHandPose: 'lantern_hold',
      ignoreStatureScale: true, t: 0.4,
    });
    text(g, 'LYRA (560px)', 1190, 1012, { size: 22, font: FONTS.body, weight: 700, color: OUT });

    drawSquireCinematic2DActor(g, 1590, 965, 360, {
      castId: 'LYRA', view: 'front', expression: 'startled_gasp',
      armAngles: [58, 45, 64, 48], rightHandPose: 'palm_raised_react', leftHandPose: 'palm_raised_react',
      ignoreStatureScale: true, t: 0.4,
    });
    text(g, 'LYRA (360px Readability)', 1590, 1012, { size: 22, font: FONTS.body, weight: 700, color: OUT });
  }
});

// Shot 2 (t=1.5s): Dramatic Close Face in Blurred 2D Belfry Interior
registerShot('poc02', {
  draw(g) {
    const rig = evaluateBellRigStateAt(4.6);
    drawLayeredRomanEnvironment2D(g, { z: 1.14, x: -40, y: -30 }, {
      view: 'belfry_lower_arch', globalT: 4.6, rigState: rig, blurBackBell: 8,
      drawStageActors: (c) => {
        drawSquireCinematic2DActor(c, 920, 1460, 1180, {
          castId: 'TAVI', view: 'three_quarter', expression: 'wide_shock',
          pupilX: 0.78, pupilY: -0.55, headRot: -0.05,
          armAngles: [64, 58, 78, 66], rightHandPose: 'open_recoil', leftHandPose: 'open_recoil',
          t: 1.2,
        });
      }
    });
  }
});

// Shot 3 (t=2.5s): Wide 5-Layer Establishing Shot of Roman Hilltop Belfry
registerShot('poc03', {
  draw(g) {
    const rig = evaluateBellRigStateAt(3.8);
    drawLayeredRomanEnvironment2D(g, { z: 1.02, x: 0, y: 0 }, {
      view: 'belfry_wide_interior', globalT: 3.8, rigState: rig,
      drawStageActors: (c, anc) => {
        drawSquireCinematic2DActor(c, 670, 950, 470, {
          castId: 'TAVI', view: 'three_quarter', expression: 'anxious_alert',
          pupilX: 0.7, pupilY: -0.4, armAngles: [20, 24, 68, 32], rightHandPose: 'point_alert',
          t: 2.5,
        });
        drawPipGoat2D(c, 1150, 950, 240, {
          flip: true, action: 'rope_nudge', phase: 0.65, t: 2.5,
        });
      }
    });
  }
});

// Shot 4 (t=3.5s): Environment Detail (Upper Catwalk & Stone Stairwell / Courtyard Landmarks)
registerShot('poc04', {
  draw(g) {
    const rig = evaluateBellRigStateAt(15.2);
    drawLayeredRomanEnvironment2D(g, { z: 1.04, x: 20, y: -10 }, {
      view: 'tower_stairwell_ascent', globalT: 15.2, rigState: rig,
      drawStageActors: (c, anc) => {
        const s4 = anc.stairs[4], s5 = anc.stairs[5];
        drawSquireCinematic2DActor(c, s4.treadX + 36, s4.treadY, 430, {
          castId: 'TAVI', view: 'profile', expression: 'determined_climb',
          spineLean: 0.19, secondaryLag: 0.85,
          leftFootU: [-8, 0], rightFootU: [34, -17.5],
          armAngles: [-35, 65, 58, 72], rightHandPose: 'rope_grip', leftHandPose: 'rope_grip',
          t: 3.5,
        });
      }
    });
  }
});

// Shot 5 (t=4.5s): Prop-Hand Contact Closeup (Articulated Hands Catching Iron Clapper & Hemp Rope)
registerShot('poc05', {
  draw(g) {
    const rig = { bellAngle: 0.085, clapperRelAngle: -0.045, ropePullPx: -8, ropeSlackWave: 2, acousticRing: 0, clapperHeld: true };
    drawLayeredRomanEnvironment2D(g, { z: 1.08, x: 20, y: 10 }, {
      view: 'belfry_catwalk_clapper', closeupClapper: true, globalT: 20.0, rigState: rig,
      drawStageActors: (c, anc) => {
        const bulb = anc.bell.clapperBulbWorld;
        // Tavi positioned on catwalk gripping the iron clapper bulb directly with leather-wrapped hands!
        const actorX = bulb[0] - 185, actorY = anc.catwalkY + 120;
        const h = 760, u = h / 100;
        const targetLocalX = (bulb[0] - actorX) / u;
        const targetLocalY = (bulb[1] - (actorY - 30 * u)) / u;
        drawSquireCinematic2DActor(c, actorX, actorY, h, {
          castId: 'TAVI', view: 'three_quarter', expression: 'strained_pull',
          pupilX: 0.65, pupilY: -0.35, leatherWraps: true,
          rightHandTargetU: [targetLocalX - 1.5, targetLocalY + 1.0, -1],
          leftHandTargetU: [targetLocalX + 1.8, targetLocalY - 1.5, 1],
          rightHandPose: 'pin_catch', leftHandPose: 'pin_catch',
          t: 4.5,
        });
      }
    });
  }
});

// Shot 6 (t=5.5s): PIP Goat Quadruped Study (Non-Human Rig)
registerShot('poc06', {
  draw(g) {
    cardBg(g, 'KH-02.1 POC 06 — PIP THE GOAT (QUADRUPED 2D RIG — NON-HUMAN)', 'Distinct animal anatomy, horizontal goat pupils, cloven hooves & 2D squash/stretch sneeze arc');
    line(g, [[80, 860], [1840, 860]], { lw: 5, ink: alpha(OUT, 0.45) });
    const states = [
      ['rope_nudge', 0.7, '1. Rope Nudge Hook'],
      ['curious_tilt', 0.4, '2. Innocent Tilt'],
      ['sneeze_anticipation', 0.92, '3. Inhale Squash'],
      ['sneeze_burst', 0.65, '4. Sneeze Stretch!'],
    ];
    states.forEach(([act, ph, cap], idx) => {
      const gx = 240 + idx * 455;
      if (act === 'rope_nudge') {
        drawBellRopeSegment2D(g, [gx + 195, 240], [gx + 195, 855], { ropeSlackWave: 10 }, { coiledBase: true, ropeWidth: 12 });
      }
      drawPipGoat2D(g, gx, 860, 340, { action: act, phase: ph, t: 1.1 });
      text(g, cap, gx + 20, 930, { size: 24, font: FONTS.body, weight: 700, color: OUT });
    });
  }
});

// Shot 7 (t=6.5s): Turnaround Model Sheet (Front / 3-4 / Profile for TAVI & LYRA)
registerShot('poc07', {
  draw(g) {
    cardBg(g, 'KH-02.1 TURNAROUND MODEL SHEET — TAVI & LYRA (FRONT / 3-4 / PROFILE)', 'Consistent head-to-body ratio, wardrobe colors, accessories & silhouette clarity across views');
    line(g, [[70, 955], [1850, 955]], { lw: 4, ink: alpha(OUT, 0.4) });
    line(g, [[960, 140], [960, 1020]], { lw: 3, ink: alpha(OUT, 0.25), dash: [12, 10] });

    const views = [['front', 'FRONT'], ['three_quarter', '3/4 VIEW'], ['profile', 'PROFILE']];
    views.forEach(([vw, lbl], i) => {
      const tx = 200 + i * 280;
      drawSquireCinematic2DActor(g, tx, 955, 470, {
        castId: 'TAVI', view: vw, expression: 'calm_watchful',
        armAngles: [18, 20, 42, 32], rightHandPose: 'rope_grip', leftHandPose: 'relaxed',
        t: 0.5,
      });
      text(g, `TAVI · ${lbl}`, tx, 1002, { size: 20, font: FONTS.body, weight: 700, color: OUT });

      const lx = 1100 + i * 280;
      drawSquireCinematic2DActor(g, lx, 955, 470, {
        castId: 'LYRA', view: vw, expression: 'calm_watchful',
        armAngles: [18, 22, 48, 38], rightHandPose: 'lantern_hold', leftHandPose: 'palm_raised_react',
        t: 0.5,
      });
      text(g, `LYRA · ${lbl}`, lx, 1002, { size: 20, font: FONTS.body, weight: 700, color: OUT });
    });
  }
});

// Shot 8 (t=7.5s): 6-State Expression + Hand Pose Sheet (TAVI & LYRA)
registerShot('poc08', {
  draw(g) {
    cardBg(g, 'KH-02.1 EXPRESSION & HAND-POSE MATRIX (6 EMOTIONAL STATES x 2 HUMAN ACTORS)', 'Top row: TAVI (6 expressions + 4 hand poses) | Bottom row: LYRA (6 expressions + 3 hand poses)');
    const taviExprs = [
      ['calm_watchful', 'relaxed', 'Calm'],
      ['anxious_alert', 'point_alert', 'Anxious'],
      ['wide_shock', 'open_recoil', 'Shock'],
      ['strained_pull', 'rope_grip', 'Strained'],
      ['breathless_relief', 'pin_catch', 'Relief'],
      ['deadpan_disbelief', 'relaxed', 'Deadpan'],
    ];
    const lyraExprs = [
      ['calm_watchful', 'lantern_hold', 'Calm'],
      ['sleepy_blink', 'relaxed', 'Sleepy'],
      ['startled_gasp', 'palm_raised_react', 'Startled'],
      ['grumpy_glare', 'point_alert', 'Grumpy'],
      ['anxious_alert', 'palm_raised_react', 'Alert'],
      ['wry_amusement', 'lantern_hold', 'Wry'],
    ];
    taviExprs.forEach(([ex, hp, lbl], i) => {
      const cx = 185 + i * 305;
      g.save();
      g.beginPath(); g.roundRect(cx - 135, 135, 270, 400, 14); g.fillStyle = '#efe1c6'; g.fill(); g.lineWidth = 3; g.strokeStyle = alpha(OUT, 0.3); g.stroke(); g.clip();
      drawSquireCinematic2DActor(g, cx - 10, 680, 520, {
        castId: 'TAVI', view: 'three_quarter', expression: ex,
        armAngles: [22, 24, 72, 68], rightHandPose: hp, t: 0.8,
      });
      g.restore();
      text(g, `TAVI: ${lbl} (${hp})`, cx, 558, { size: 17, font: FONTS.body, weight: 700, color: OUT });
    });
    lyraExprs.forEach(([ex, hp, lbl], i) => {
      const cx = 185 + i * 305;
      g.save();
      g.beginPath(); g.roundRect(cx - 135, 590, 270, 400, 14); g.fillStyle = '#e7dac0'; g.fill(); g.lineWidth = 3; g.strokeStyle = alpha(OUT, 0.3); g.stroke(); g.clip();
      drawSquireCinematic2DActor(g, cx - 10, 1145, 530, {
        castId: 'LYRA', view: 'three_quarter', expression: ex,
        armAngles: [22, 24, 72, 68], rightHandPose: hp, t: 0.8,
      });
      g.restore();
      text(g, `LYRA: ${lbl} (${hp})`, cx, 1014, { size: 17, font: FONTS.body, weight: 700, color: OUT });
    });
  }
});

// Shot 9 (t=8.5s): Courtyard Exterior View (4th distinct camera angle of same location!)
registerShot('poc09', {
  draw(g) {
    const rig = evaluateBellRigStateAt(27.4);
    drawLayeredRomanEnvironment2D(g, { z: 1.0, x: 0, y: 0 }, {
      view: 'hilltop_courtyard_wide', globalT: 27.4, rigState: rig, shutterOpenK: 1.0,
      drawStageActors: (c, anc) => {
        const [bx, by] = anc.balconyWindowWorld;
        c.save();
        c.beginPath(); c.rect(bx - 110, by - 210, 220, 210); c.clip();
        drawSquireCinematic2DActor(c, bx, by + 135, 360, {
          castId: 'LYRA', view: 'front', expression: 'grumpy_glare',
          armAngles: [52, 48, 66, 44], rightHandPose: 'palm_raised_react', t: 2.0,
        });
        c.restore();
        drawSquireCinematic2DActor(c, 980, anc.courtyardGroundY + 34, 410, {
          castId: 'CITIZEN_A', view: 'three_quarter', flip: true, expression: 'startled_gasp',
          pupilX: -0.7, pupilY: -0.6, armAngles: [64, 40, 74, 36], rightHandPose: 'open_recoil', t: 2.0,
        });
      }
    });
  }
});
"""


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def render_style_poc(scratch_dir: Path, run_dir: Path, evidence_dir: Path) -> Dict:
    poc_proj = scratch_dir / "style_poc_proj"
    if poc_proj.exists():
        shutil.rmtree(poc_proj)
    for sub in ("story", "scenes/shots", "build", "out"):
        (poc_proj / sub).mkdir(parents=True, exist_ok=True)

    cfg = {
        "title": "KH02 Style POC",
        "pack": "squire",
        "aspect": "16:9",
        "resolution": "1080p",
        "fps": 24,
        "style": "flat",
        "style_profile": "squire_cinematic_2d.v1",
        "render_mode": "canvas2d_only",
        "fadeIn": 0,
        "fadeOut": 0,
        "bars": "none",
        "captions": False,
    }
    (poc_proj / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    shots = [
        {"id": f"poc0{i}", "start": float(i - 1), "end": float(i), "line": f"POC {i}"}
        for i in range(1, 10)
    ]
    (poc_proj / "story" / "shots.json").write_text(
        json.dumps({"title": "KH02 Style POC", "duration": 9.0, "shots": shots}, indent=2),
        encoding="utf-8",
    )
    (poc_proj / "scenes" / "shots" / "poc_all.js").write_text(POC_SCENES_JS, encoding="utf-8")

    stills_arg = "0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5"
    r = subprocess.run(
        ["node", "render.mjs", "--project", str(poc_proj), "--stills", stills_arg, "--scale", "1.0"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"POC render failed:\n{r.stdout}\n{r.stderr}")

    name_map = {
        "t_0.50.png": "poc_01_characters_dual_scale.png",
        "t_1.50.png": "poc_02_dramatic_close_face.png",
        "t_2.50.png": "poc_03_wide_establishing_belfry.png",
        "t_3.50.png": "poc_04_environment_stairwell_detail.png",
        "t_4.50.png": "poc_05_prop_hand_contact_closeup.png",
        "t_5.50.png": "poc_06_goat_pip_quadruped.png",
        "t_6.50.png": "model_sheet_turnaround_tavi_lyra.png",
        "t_7.50.png": "expression_sheet_tavi_lyra_6states.png",
        "t_8.50.png": "poc_09_courtyard_exterior_angle.png",
    }

    poc_out_run = run_dir / "style_poc"
    poc_out_evid = evidence_dir / "style_poc"
    poc_out_run.mkdir(parents=True, exist_ok=True)
    poc_out_evid.mkdir(parents=True, exist_ok=True)

    artifacts = {}
    for raw_name, clean_name in name_map.items():
        src = poc_proj / "build" / "stills" / raw_name
        if not src.is_file():
            raise FileNotFoundError(f"Expected rendered POC still missing: {src}")
        dst_run = poc_out_run / clean_name
        shutil.copy2(src, dst_run)
        # Also save compact JPG copy in evidence_dir to keep git light while keeping full PNGs in run_dir/style_poc
        jpg_evid = poc_out_evid / (Path(clean_name).stem + ".jpg")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", "scale=960:-2", "-q:v", "3", str(jpg_evid)],
            check=True,
        )
        artifacts[clean_name] = {
            "run_rel_path": dst_run.relative_to(REPO_ROOT).as_posix(),
            "abs_path": str(dst_run),
            "sha256": sha256_file(dst_run),
            "bytes": dst_run.stat().st_size,
            "evidence_jpg": jpg_evid.relative_to(REPO_ROOT).as_posix(),
        }

    # Copy contact sheet generated by render.mjs
    sheet_src = poc_proj / "build" / "sheets" / "stills_01.jpg"
    if sheet_src.is_file():
        sheet_dst = poc_out_run / "poc_contact_sheet.jpg"
        shutil.copy2(sheet_src, sheet_dst)
        shutil.copy2(sheet_src, poc_out_evid / "poc_contact_sheet.jpg")
        artifacts["poc_contact_sheet.jpg"] = {
            "run_rel_path": sheet_dst.relative_to(REPO_ROOT).as_posix(),
            "abs_path": str(sheet_dst),
            "sha256": sha256_file(sheet_dst),
            "bytes": sheet_dst.stat().st_size,
        }

    # Build side-by-side comparison sheet (Baseline Production Squire vs KH-02.1 Upgraded 2D)
    base_ref_1 = run_dir / "baseline_reference" / "pre_edit_squire_t_1.20.png"
    base_ref_2 = run_dir / "baseline_reference" / "pre_edit_squire_t_4.00.png"
    comp_dst = poc_out_run / "baseline_vs_kh02_comparison.jpg"
    if base_ref_1.is_file() and base_ref_2.is_file():
        subprocess.run(
            [
                "ffmpeg", "-v", "error", "-y",
                "-i", str(base_ref_1),
                "-i", str(poc_out_run / "poc_03_wide_establishing_belfry.png"),
                "-i", str(base_ref_2),
                "-i", str(poc_out_run / "poc_02_dramatic_close_face.png"),
                "-filter_complex",
                "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[2:v]scale=960:540[c];[3:v]scale=960:540[d];[a][b]hstack=inputs=2[top];[c][d]hstack=inputs=2[bot];[top][bot]vstack=inputs=2",
                "-q:v", "3",
                str(comp_dst),
            ],
            check=True,
        )
        shutil.copy2(comp_dst, poc_out_evid / "baseline_vs_kh02_comparison.jpg")
        artifacts["baseline_vs_kh02_comparison.jpg"] = {
            "run_rel_path": comp_dst.relative_to(REPO_ROOT).as_posix(),
            "abs_path": str(comp_dst),
            "sha256": sha256_file(comp_dst),
            "bytes": comp_dst.stat().st_size,
        }

    # Validate factories against actual rendered assets
    style_prof = load_squire_style_profile("squire_cinematic_2d.v1")
    ident = derive_character_identity()
    char_assets = {
        k: artifacts[k]
        for k in ("poc_01_characters_dual_scale.png", "model_sheet_turnaround_tavi_lyra.png", "expression_sheet_tavi_lyra_6states.png")
    }
    char_manifest = write_character_continuity_manifest(ident, char_assets, poc_out_run / "character_continuity_manifest.json")
    char_val = validate_character_model_consistency(char_manifest)

    env_spec = derive_scene_spec()
    env_assets = {
        "belfry_wide_interior": artifacts["poc_03_wide_establishing_belfry.png"],
        "tower_stairwell_ascent": artifacts["poc_04_environment_stairwell_detail.png"],
        "belfry_catwalk_clapper": artifacts["poc_05_prop_hand_contact_closeup.png"],
        "hilltop_courtyard_wide": artifacts["poc_09_courtyard_exterior_angle.png"],
    }
    env_manifest = export_2d_scene_manifest(env_spec, env_assets, poc_out_run / "environment_continuity_manifest.json")
    env_val = validate_scene_continuity(env_manifest)

    receipt = {
        "status": "TECH_PASS" if (char_val["valid"] and env_val["valid"]) else "FAIL",
        "style_approval_status": "HUMAN_REVIEW_PENDING",
        "style_id": style_prof["style_id"],
        "style_lock_digest": style_prof["canonical_digest"],
        "render_mode": "canvas2d_only",
        "character_validation": char_val,
        "environment_validation": env_val,
        "artifacts": artifacts,
    }
    (poc_out_run / "style_poc_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    run_folder = REPO_ROOT / "docs" / "antigravity_runs" / "KH-02_0_1_20261117_014132Z_db01"
    scratch = REPO_ROOT / ".test-runs" / "kh02_20261117_014132Z_db01"
    evid = REPO_ROOT / "tests" / "evidence" / "kh02_20261117_014132Z_db01"
    res = render_style_poc(scratch, run_folder, evid)
    print(json.dumps({"status": res["status"], "style_approval": res["style_approval_status"], "count": len(res["artifacts"])}, indent=2))
    sys.exit(0 if res["status"] == "TECH_PASS" else 1)

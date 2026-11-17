#!/usr/bin/env python3
"""test_style_lock.py — Unit, Contract, Negative-Mutation & False-Positive-Guard Suite for KH-03.0."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_e2e_regression import is_supported_qa_branch
from tools.kh03_baseline_comparator import compare_roman_identity_geometry
from tools.kh03_preview_director import compile_roman_training_beats
from tools.kh03_reference_audit import assert_no_reused_demo_assets, collect_user_style_reference
from tools.kh03_style_lock import (
    compute_roman_style_digest,
    load_roman_master_style,
    resolve_roman_variant,
    validate_roman_style_contract,
)
from tools.validator import validate_project


def test_load_and_digest_roman_master_style() -> None:
    sb = load_roman_master_style("roman_squire_master.v1")
    digest = compute_roman_style_digest(sb)
    assert digest == sb["canonical_digest"]
    res = validate_roman_style_contract(sb)
    assert res["valid"] is True
    assert res["digest_verified"] is True
    # Subjective style sign-off must NEVER be auto-approved by code
    assert res["style_approved"] == "HUMAN_REVIEW_PENDING"


def test_reject_modern2d_or_unknown_style_id() -> None:
    with pytest.raises(ValueError, match="roman_squire_master.v1"):
        load_roman_master_style("modern2d_cinematic.v1")
    with pytest.raises(ValueError, match="roman_squire_master.v1"):
        load_roman_master_style("kh02_tavi_lyra")


def test_mutation_style_digest_and_palette_tamper() -> None:
    sb = load_roman_master_style()

    # Mutant 1: Digest tamper / unrecorded edit
    m_digest = copy.deepcopy(sb)
    m_digest["geometric_invariants"]["head_radius_u"] = 14.0
    r1 = validate_roman_style_contract(m_digest)
    assert r1["valid"] is False
    assert any("digest mismatch" in e.lower() or "head radius" in e.lower() for e in r1["errors"])

    # Mutant 2: Recomputed digest with forbidden palette drift (#392a21 -> #000000)
    m_pal = copy.deepcopy(sb)
    m_pal["palette_lock"]["OUT"] = "#000000"
    m_pal["canonical_digest"] = compute_roman_style_digest(m_pal)
    r2 = validate_roman_style_contract(m_pal)
    assert r2["valid"] is False
    assert any("OUT" in e for e in r2["errors"])

    # Mutant 3: Bare-hair helmet swap on Roman soldier
    m_helm = copy.deepcopy(sb)
    m_helm["locked_character_archetypes"]["rookie_hastatus"]["helmet"] = "none"
    m_helm["canonical_digest"] = compute_roman_style_digest(m_helm)
    r3 = validate_roman_style_contract(m_helm)
    assert r3["valid"] is False
    assert any("helmet" in e.lower() for e in r3["errors"])


def test_resolve_roman_variant_family_lock() -> None:
    v_rookie = resolve_roman_variant("rookie")
    assert v_rookie["archetype_id"] == "rookie_hastatus"
    assert v_rookie["squire_preset_params"]["helmet"] == "montefortino"
    assert v_rookie["squire_preset_params"]["shield"]["type"] == "scutum"

    with pytest.raises(ValueError):
        resolve_roman_variant("tavi")
    with pytest.raises(ValueError):
        resolve_roman_variant("rookie", era="medieval_norman")
    with pytest.raises(ValueError):
        resolve_roman_variant("rookie", environment_id="bell_tower_plaza")


def test_user_reference_audit_honesty(tmp_path: Path) -> None:
    missing = collect_user_style_reference([tmp_path / "DOES_NOT_EXIST.png"])
    assert missing["status"] == "USER_SCREENSHOT_REFERENCE_UNAVAILABLE"
    assert missing["sha256"] is None
    assert missing["forbid_video_frame_ingest"] is True

    fake_ref = tmp_path / "KH-03-ROMAN-ORIGINAL-STYLE-REFERENCE-ONLY.png"
    Image.new("RGB", (64, 64), (201, 71, 58)).save(fake_ref)
    present = collect_user_style_reference([fake_ref])
    assert present["status"] == "USER_SCREENSHOT_REFERENCE_AVAILABLE"
    assert len(present["sha256"]) == 64
    assert present["forbid_video_frame_ingest"] is True


def test_mutation_recycled_demo_asset_and_forbidden_tokens(tmp_path: Path) -> None:
    proj = tmp_path / "clean_proj"
    (proj / "story").mkdir(parents=True)
    (proj / "scenes" / "shots").mkdir(parents=True)
    (proj / "config.json").write_text('{"pack":"squire","render_mode":"canvas2d_only"}\n', encoding="utf-8")
    (proj / "story" / "shots.json").write_text('{"duration":3.0,"shots":[{"id":"S1","start":0,"end":3}]}\n', encoding="utf-8")
    (proj / "scenes" / "shots" / "S1.js").write_text("export const ok = 1;\n", encoding="utf-8")

    clean_res = assert_no_reused_demo_assets(proj)
    assert clean_res["passed"] is True

    # Mutant A: Forbidden KH-02 character token ("tavi" / "bell_before_sunrise")
    (proj / "scenes" / "shots" / "S1.js").write_text("const hero = 'tavi_bell_before_sunrise';\n", encoding="utf-8")
    m_tok = assert_no_reused_demo_assets(proj)
    assert m_tok["passed"] is False
    assert any("tavi" in e.lower() or "bell_before_sunrise" in e.lower() for e in m_tok["errors"])

    # Restore clean JS, inject Mutant B: external bitmap plate in anh/
    (proj / "scenes" / "shots" / "S1.js").write_text("export const ok = 1;\n", encoding="utf-8")
    (proj / "anh").mkdir()
    Image.new("RGB", (32, 32), (255, 0, 0)).save(proj / "anh" / "stolen_screenshot.png")
    m_anh = assert_no_reused_demo_assets(proj)
    assert m_anh["passed"] is False
    assert any("bitmap" in e.lower() or "anh" in e.lower() for e in m_anh["errors"])

    # Mutant C: Byte-identical copy of legacy squire-mau file
    for f in (proj / "anh").iterdir():
        f.unlink()
    (proj / "story" / "copied.json").write_bytes((REPO_ROOT / "projects" / "squire-mau" / "config.json").read_bytes())
    m_hash = assert_no_reused_demo_assets(proj)
    assert m_hash["passed"] is False
    assert any("reused demo" in e.lower() for e in m_hash["errors"])


def test_mutation_3d_guard_missing_scene_and_bad_timestamp(tmp_path: Path) -> None:
    proj = tmp_path / "kh03_guard_proj"
    (proj / "story").mkdir(parents=True)
    (proj / "scenes" / "shots").mkdir(parents=True)
    (proj / "config.json").write_text(
        json.dumps({"pack": "squire", "aspect": "16:9", "resolution": "1080p", "render_mode": "canvas2d_only"}),
        encoding="utf-8",
    )
    (proj / "scenes" / "shots" / "only.js").write_text(
        "import { registerShot } from '/engine/core.js';\nregisterShot('SH01', { draw(g, lt, info) {} });\n",
        encoding="utf-8",
    )
    (proj / "story" / "shots.json").write_text(
        json.dumps({"duration": 3.0, "shots": [{"id": "SH01", "start": 0.0, "end": 3.0}]}),
        encoding="utf-8",
    )
    assert validate_project(proj)["status"] == "PASS"

    # Mutant 1: Inject kind: '3d' in shots.json
    (proj / "story" / "shots.json").write_text(
        json.dumps({"duration": 3.0, "shots": [{"id": "SH01", "kind": "3d", "start": 0.0, "end": 3.0}]}),
        encoding="utf-8",
    )
    rep_3d = validate_project(proj)
    assert rep_3d["status"] == "BLOCKED"
    assert any("KH03_2D_ONLY_VIOLATION" in e for e in rep_3d["fatal_errors"])

    # Legacy compatibility guard: when render_mode is NOT canvas2d_only, 3D is NOT blocked by KH03 guard
    (proj / "config.json").write_text(
        json.dumps({"pack": "squire", "aspect": "16:9", "resolution": "1080p"}),
        encoding="utf-8",
    )
    rep_legacy = validate_project(proj)
    assert not any("KH03_2D_ONLY_VIOLATION" in e for e in rep_legacy["fatal_errors"])

    # Restore canvas2d_only and inject Mutant 2: missing scene registration
    (proj / "config.json").write_text(
        json.dumps({"pack": "squire", "aspect": "16:9", "resolution": "1080p", "render_mode": "canvas2d_only"}),
        encoding="utf-8",
    )
    (proj / "story" / "shots.json").write_text(
        json.dumps({"duration": 3.0, "shots": [{"id": "SH_MISSING_99", "start": 0.0, "end": 3.0}]}),
        encoding="utf-8",
    )
    rep_miss = validate_project(proj)
    assert rep_miss["status"] == "BLOCKED"
    assert "SH_MISSING_99" in rep_miss["missing_ids"]

    # Mutant 3: Bad overlapping timestamp (start >= end)
    (proj / "story" / "shots.json").write_text(
        json.dumps({"duration": 3.0, "shots": [{"id": "SH01", "start": 2.5, "end": 1.0}]}),
        encoding="utf-8",
    )
    rep_ts = validate_project(proj)
    assert rep_ts["status"] == "BLOCKED"
    assert len(rep_ts["timeline_errors"]) > 0


def test_compare_roman_identity_geometry_and_silhouette_mutant(tmp_path: Path) -> None:
    def make_soldier_card(polish: bool = False, swap_silhouette: bool = False) -> Path:
        im = Image.new("RGB", (640, 360), (210, 195, 165))
        d = ImageDraw.Draw(im)
        if swap_silhouette:
            # Drastic non-Roman blue rectangle silhouette mutant
            d.rectangle([220, 60, 440, 330], fill=(40, 90, 200), outline=(0, 0, 0), width=4)
        else:
            # Bronze Montefortino dome, ivory head, #392a21 outline, white glove, red scutum
            d.ellipse([280, 70, 360, 140], fill=(211, 162, 78), outline=(57, 42, 33), width=4)
            d.ellipse([286, 100, 354, 168], fill=(244, 237, 225), outline=(57, 42, 33), width=4)
            d.polygon([(315, 40), (325, 40), (322, 72), (318, 72)], fill=(255, 255, 255))
            d.ellipse([255, 155, 335, 295], fill=(201, 71, 58), outline=(57, 42, 33), width=4)
            d.ellipse([342, 205, 366, 229], fill=(255, 255, 255), outline=(57, 42, 33), width=3)
            if polish:
                d.line([(290, 96), (350, 96)], fill=(255, 242, 198), width=2)
        out = tmp_path / ("swap.png" if swap_silhouette else ("after.png" if polish else "before.png"))
        im.save(out)
        return out

    bg = tmp_path / "bg.png"
    Image.new("RGB", (640, 360), (210, 195, 165)).save(bg)
    p_before = make_soldier_card(polish=False)
    p_after = make_soldier_card(polish=True)
    p_swap = make_soldier_card(swap_silhouette=True)

    good = compare_roman_identity_geometry(p_before, p_after, bg_only_png=bg, roi_box=(200, 20, 440, 340))
    assert good["passed"] is True
    assert good["silhouette_iou"] >= 0.99
    assert good["style_approved"] == "HUMAN_REVIEW_PENDING"

    bad = compare_roman_identity_geometry(p_before, p_swap, bg_only_png=bg, roi_box=(200, 20, 440, 340))
    assert bad["passed"] is False
    assert len(bad["errors"]) > 0


def test_js_rig_camera_and_cut_mutants_plus_false_positive_guards(tmp_path: Path) -> None:
    """Execute real ES module evaluation of roman_master/{motion,character_state,camera} with mutants & FP guards."""
    loader_mjs = tmp_path / "root_loader.mjs"
    repo_uri = REPO_ROOT.as_uri().rstrip("/")
    loader_mjs.write_text(
        f"""export async function resolve(specifier, context, nextResolve) {{
  if (specifier.startsWith('/engine/') || specifier.startsWith('/packs/')) {{
    return nextResolve('{repo_uri}' + specifier, context);
  }}
  return nextResolve(specifier, context);
}}
""",
        encoding="utf-8",
    )
    char_url = (REPO_ROOT / "packs" / "squire" / "roman_master" / "character_state.js").as_uri()
    cam_url = (REPO_ROOT / "packs" / "squire" / "roman_master" / "camera.js").as_uri()
    probe_mjs = tmp_path / "probe_roman_master.mjs"

    probe_mjs.write_text(
        f"""import {{ romanActorAt, validateRomanMasterRigAnchors }} from '{char_url}';
import {{ evaluateRomanCameraAt, validateRomanCameraCut }} from '{cam_url}';

const beat = {{
  start: 12.0,
  end: 15.0,
  actors: {{
    rookie: {{
      archetypeId: 'rookie_hastatus',
      hFrac: 0.58,
      xFrac: 0.56,
      yFrac: 0.93,
      leftFootXKeys: [[0, 0.52, 'hold'], [3, 0.52, 'hold']],
      rightFootXKeys: [[0, 0.60, 'hold'], [3, 0.60, 'hold']],
      shieldOffsetU: [4.0, -38.0],
      rightHandU: [14.0, -36.5],
      weapon: 'spear',
    }},
  }},
}};

const validPose = romanActorAt(13.5, beat, 'rookie', {{ W: 1920, H: 1080 }});
const okRig = validateRomanMasterRigAnchors(validPose, {{
  requirePlantedFeet: true,
  requireWeapon: 'spear',
  spearAnchorWorld: validPose.rightHandWorld,
}});

// Mutant 1: Broken shield grip (detached 85px away)
const mutShield = {{
  ...validPose,
  shieldGrip: {{ ...validPose.shieldGrip, gripDriftPx: 85.0 }},
}};
const resShield = validateRomanMasterRigAnchors(mutShield);

// Mutant 2: Broken spear contact (hand 48px from spear shaft)
const resSpear = validateRomanMasterRigAnchors(validPose, {{
  spearAnchorWorld: [validPose.rightHandWorld[0] + 48, validPose.rightHandWorld[1]],
}});

// Mutant 3: Foot skate (8.5px drift during planted stance)
const mutFoot = {{
  ...validPose,
  footPlant: {{ ...validPose.footPlant, leftDriftPx: 8.5 }},
}};
const resFoot = validateRomanMasterRigAnchors(mutFoot, {{ requirePlantedFeet: true }});

// Mutant 4: Actor teleport across same-anchor join (240px jump)
const prevPose = {{ ...validPose, rootWorld: [validPose.rootWorld[0] - 240, validPose.rootWorld[1]] }};
const resTeleport = validateRomanMasterRigAnchors(validPose, {{ prevPose, sameWorldAnchor: true }});

// Mutant 5: Unlocked actor identity swap
let identityKilled = false;
try {{
  romanActorAt(1.0, {{ start: 0, end: 2, actors: {{ bad: {{ archetypeId: 'kh02_tavi_hero' }} }} }}, 'bad');
}} catch (e) {{
  identityKilled = String(e).includes('KH03_STYLE_LOCK_VIOLATION');
}}

// Mutant 6: Unmotivated shield-gap teleport across cut + 180-degree axis flip + 3x identical framing
const ledger = {{
  recentFramings: [
    {{ framingScale: 'medium', trajectory: 'static' }},
    {{ framingScale: 'medium', trajectory: 'static' }},
  ],
  shots: {{
    SH02: {{ endState: {{ gapState: 'OPEN_SLIVER', rookieHelmet: 'montefortino_3_feathers', rookieShield: 'red_scutum_gold_rim', snaggedSpear: false }} }},
    SH03_BAD: {{ startState: {{ gapState: 'SEALED_TIGHT', rookieHelmet: 'montefortino_3_feathers', rookieShield: 'red_scutum_gold_rim', snaggedSpear: false }} }},
    SH05_VALID: {{ startState: {{ gapState: 'OPEN_SLIVER', rookieHelmet: 'montefortino_3_feathers', rookieShield: 'red_scutum_gold_rim', snaggedSpear: false }} }},
  }},
}};
const badCut = validateRomanCameraCut(
  {{ shotId: 'SH02', stageAxisSign: 1, framingScale: 'medium', trajectory: 'static' }},
  {{ shotId: 'SH03_BAD', stageAxisSign: -1, framingScale: 'medium', trajectory: 'static' }},
  ledger
);

// FALSE-POSITIVE GUARD 1: Valid cinematic cut jump (wide -> close insert) on consistent axis & ledger MUST PASS!
const validCut = validateRomanCameraCut(
  {{ shotId: 'SH02', stageAxisSign: 1, framingScale: 'wide_geography', trajectory: 'pan_left_to_right' }},
  {{ shotId: 'SH05_VALID', stageAxisSign: 1, framingScale: 'macro_physics_insert', trajectory: 'snap_push' }},
  {{ ...ledger, recentFramings: [{{ framingScale: 'wide_geography', trajectory: 'pan_left_to_right' }}] }}
);

// FALSE-POSITIVE GUARD 2: Legitimate 8-frame dramatic hold in SH07 [2.25..2.58s] keeps pose stable & valid!
const holdBeat = {{
  start: 18.5,
  end: 23.0,
  actors: {{
    instructor: {{
      archetypeId: 'instructor_princeps',
      hFrac: 0.48,
      xFrac: 0.26,
      yFrac: 0.91,
      headNodKeys: [[0.0, 0.0, 'c1'], [2.25, 0.0, 'hold'], [2.58, 0.0, 'hold'], [2.95, 3.4, 'c1']],
      phaseKeys: [[0.0, 'settle'], [2.25, 'hold'], [2.60, 'reaction']],
    }},
  }},
}};
const holdA = romanActorAt(18.5 + 2.30, holdBeat, 'instructor', {{ W: 1920, H: 1080 }});
const holdB = romanActorAt(18.5 + 2.50, holdBeat, 'instructor', {{ W: 1920, H: 1080 }});
const holdValid = holdA.phase === 'hold' && holdB.phase === 'hold' && Math.abs(holdA.headNodU - holdB.headNodU) < 1e-6 && validateRomanMasterRigAnchors(holdA).valid;

console.log(JSON.stringify({{
  okRig: okRig.valid,
  shieldKilled: !resShield.valid,
  spearKilled: !resSpear.valid,
  footKilled: !resFoot.valid,
  teleportKilled: !resTeleport.valid,
  identityKilled,
  badCutKilled: !badCut.valid && badCut.errors.length >= 2,
  validCutPassed: validCut.valid,
  holdGuardPassed: holdValid,
}}));
""",
        encoding="utf-8",
    )

    reg_arg = f"import {{ register }} from 'node:module'; register('{loader_mjs.as_uri()}');"
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", f"{reg_arg} await import('{probe_mjs.as_uri()}');"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Node probe failed: {proc.stderr}"
    out = proc.stdout.strip()
    data = json.loads(out)
    assert data["okRig"] is True
    assert data["shieldKilled"] is True
    assert data["spearKilled"] is True
    assert data["footKilled"] is True
    assert data["teleportKilled"] is True
    assert data["identityKilled"] is True
    assert data["badCutKilled"] is True
    assert data["validCutPassed"] is True
    assert data["holdGuardPassed"] is True


def test_supported_qa_branch_compatibility() -> None:
    assert is_supported_qa_branch("Production") is True
    assert is_supported_qa_branch("fix/Image-Shot") is True
    assert is_supported_qa_branch("feat/modern-2d-cinematic") is True
    assert is_supported_qa_branch("feat/roman-2d-master") is True
    assert is_supported_qa_branch("wip/unverified-hack") is False
    assert is_supported_qa_branch("") is False


def test_compile_roman_training_beats_contract() -> None:
    beats = compile_roman_training_beats()
    assert len(beats) == 9
    assert beats[0]["start"] == 0.0
    assert beats[-1]["end"] == 30.0
    assert len({b["framing_scale"] for b in beats}) >= 7

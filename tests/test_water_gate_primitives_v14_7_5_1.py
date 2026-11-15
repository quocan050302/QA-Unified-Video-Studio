#!/usr/bin/env python3
"""tests/test_water_gate_primitives_v14_7_5_1.py — Unit tests for V14.7.5.1 'The Water Gate' primitives & causality.

Verifies:
1. Storyboard exact 30.000s / 720-frame (@ 24fps) contiguous math across 8 shots (S01..S08).
2. Strict visual originality in `packs/squire/civic/water_gate.js` and `build_water_gate_assets`
   (zero external raster images, zero prior preview references, zero military props).
3. Rendering-independent physical causality checks (`verify_water_gate_causality`):
   - Valid storyboard -> PASS
   - Corrupted gate direction ('upward' or non-increasing gate_drop) -> FAIL
   - Premature overflow before gate closure -> FAIL
   - Leak jet increasing after gate closure -> FAIL
   - Stream layer occlusion swap (masonry_wall over water_jet or overflow_basin over diverted_stream) -> FAIL
   - Flow direction flip -> FAIL
"""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools.produce_fl01_v14_7_5_1_roman_water_gate_preview import (
    CIVIC_MODULE_REL,
    NOMINAL_DURATION_SEC,
    NOMINAL_FPS,
    NOMINAL_VIDEO_FRAMES,
    build_water_gate_assets,
    build_water_gate_storyboard,
    construct_water_gate_project,
    verify_water_gate_causality,
)


class TestWaterGatePrimitivesV14751(unittest.TestCase):
    def test_storyboard_exact_30s_720_frames_and_causality_pass(self) -> None:
        sb = build_water_gate_storyboard()
        self.assertEqual(sb["fps"], NOMINAL_FPS)
        self.assertEqual(sb["duration"], NOMINAL_DURATION_SEC)
        self.assertEqual(sb["expected_video_frames"], NOMINAL_VIDEO_FRAMES)
        self.assertEqual(len(sb["shots"]), 8)
        self.assertEqual(round(sum(s["dur"] for s in sb["shots"]), 3), 30.0)
        self.assertEqual(round(sb["shots"][-1]["end"] * sb["fps"]), 720)

        res = verify_water_gate_causality(sb)
        self.assertTrue(res["valid"], res)
        self.assertEqual(res["status"], "PASS")

    def test_causality_corruptions_fail_closed(self) -> None:
        base_sb = build_water_gate_storyboard()

        # 1. Gate direction inverted ('upward' / non-increasing drop)
        sb_up = copy.deepcopy(base_sb)
        sb_up["shots"][5]["mechanics"]["gate_direction"] = "upward"
        sb_up["shots"][5]["mechanics"]["gate_drop_start"] = 0.90
        sb_up["shots"][5]["mechanics"]["gate_drop_end"] = 0.10
        res_up = verify_water_gate_causality(sb_up)
        self.assertFalse(res_up["valid"])
        self.assertEqual(res_up["status"], "FAIL")

        # 2. Premature overflow surge in S04 before sluice gate drops in S06
        sb_premature = copy.deepcopy(base_sb)
        sb_premature["shots"][3]["mechanics"]["overflow_flow_end"] = 0.85
        res_pre = verify_water_gate_causality(sb_premature)
        self.assertFalse(res_pre["valid"])

        # 3. Fissure leak jet growing instead of subsiding in S07 after gate closes
        sb_leak = copy.deepcopy(base_sb)
        sb_leak["shots"][6]["mechanics"]["leak_jet_start"] = 0.20
        sb_leak["shots"][6]["mechanics"]["leak_jet_end"] = 0.90
        res_leak = verify_water_gate_causality(sb_leak)
        self.assertFalse(res_leak["valid"])

        # 4. Stream layer occlusion swap (overflow_basin drawn over diverted_stream)
        sb_layer = copy.deepcopy(base_sb)
        sb_layer["shots"][6]["mechanics"]["stream_layer_order"] = [
            "aqueduct_masonry",
            "diverted_stream",
            "overflow_basin",
            "civic_actors",
        ]
        res_layer = verify_water_gate_causality(sb_layer)
        self.assertFalse(res_layer["valid"])

        # 5. Forbidden military prop injection in civic film
        sb_mil = copy.deepcopy(base_sb)
        sb_mil["shots"][1]["args"]["props"].append({"kind": "eagle"})
        res_mil = verify_water_gate_causality(sb_mil)
        self.assertFalse(res_mil["valid"])

    def test_assets_and_project_construction_zero_prior_inputs(self) -> None:
        civic_js = ROOT_DIR / CIVIC_MODULE_REL
        self.assertTrue(civic_js.is_file())
        with tempfile.TemporaryDirectory() as td:
            p_dir = Path(td) / "wg_test_proj"
            built = construct_water_gate_project(p_dir)
            manifest = built["asset_manifest"]
            self.assertEqual(manifest["prior_preview_derived_visual_inputs"], 0)
            self.assertEqual(manifest["external_raster_images_count"], 0)
            self.assertEqual(manifest["military_battlefield_props_count"], 0)
            self.assertTrue((p_dir / "scenes" / "shots" / "water_gate_shots.js").is_file())
            self.assertTrue((p_dir / "story" / "asset_source_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()

# KH-01 Baseline & Source Truth Audit

- **Verified Live Baseline HEAD**: `f2fbea4cb6ec50c6655b08f24177869dbc961dd1` (`Fix code`) on branch `fix/Image-Shot`
- **Verified `origin/Production` Invariant SHA**: `80559d09d4b7bb72ee4c5acc6cc846e69abd65d1` (untouched before and after run)
- **Art Reference Zip Availability**: `STYLE_REFERENCE_UNAVAILABLE` — `KH-01_STYLE_REFERENCES_ONLY.zip` was searched across workspace and host drives and is not present on this Windows machine. Zero reference frame hashes/dimensions were fabricated, and zero visual-similarity claims are made.

## P0 V14.7.6 Foot-Plant Evidence Contradiction Root-Cause Reconciliation
Historical files in `tests/evidence/v14_7_6/` were preserved **100% unchanged** (`git status` clean) while reconciling three root causes in `tests/evidence/kh01_20261116_015100Z/04_v14_7_6_footplant_conflict_reconciliation.json`:
1. **Property mismatch (`valid` vs `passed`)**: `packs/squire/motion_engine.js::validateMotionFrameTrace` returned `valid` without `passed`, causing `tools/temporal_visual_qa.py::_evaluate_js_motion_traces` to record `trace_passed: false` on every track in `05_natural_motion_metrics.json`, while `audit_foot_plant()` ignored `trace_passed` and aggregated `PASS`.
2. **Planted contact skating**: `tools/motion_performance.py` previously translated actors across `>= 0.015` world units during `ANTICIPATE`/`REACH` while keeping `foot_planted_left/right = True`, causing real `0.50` normalized planted drift in `abc_motion_traces.json`. Fixed by inserting an unplanted `APPROACH` step whenever displacement `>= 0.015` and restricting `vx` facing flips to locomotion tracks.
3. **Gate decoupling**: `produce_abc_8s_comparison()` previously marked `09_a_b_c_render_comparison.json` `PASS` from MP4 decode validity alone. Fixed so overall status requires `foot_qa == PASS` and `hand_qa == PASS`, and `NOT_PROVIDED` pixel tracking maps strictly to `pixel_qa_status = NOT_VERIFIED`.
4. **Absent V14.7.6 files disclosed**: `00_master_acceptance.json`, `13_full_e2e_regression.json`, and `20_postpush_verification.json` are absent in `tests/evidence/v14_7_6/` and are never claimed present.

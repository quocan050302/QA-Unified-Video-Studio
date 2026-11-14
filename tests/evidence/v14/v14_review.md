# QA-Unified-Video-Studio V14 Execution & Acceptance Report

- **Verdict**: `V14_PRODUCTION_CANDIDATE_VERIFIED`
- **Branch**: `fix/Image-Shot` (Production remote baseline untouched: `80559d09d4`)
- **Run Start SHA**: `0d97139b718deb0e0c704d3b07e650d44d1ac0ec`
- **Elapsed Wall Time**: `355.64s`
- **Gates Passed**: `46/46` (Failed: `0`, Skipped: `0`)
- **Credential Store Protection**: `OS Keyring Protected (QA_STUDIO_TEST_MODE='1', In-Memory Isolation)`
- **Min Free Disk**: `53.8 GB`
- **Peak RAM**: `64.7%`

## Gate Execution Ledger (N01 - N46)

| Gate ID | Title | Category | Status | Elapsed | Details |
|---------|-------|----------|--------|---------|---------|
| **N01** | Branch Correct & Production Remote Unchanged Guard | `BRANCH` | ✅ PASS | 0.79s | {"current_branch": "fix/Image-Shot", "production_remote_sha" |
| **N02** | Real Credential Untouched Guard & Test Mode Lockdown | `SECURITY` | ✅ PASS | 0.19s | {"live_key_present": true, "live_key_length": 53, "write_blo |
| **N03** | Isolated Test Key Store In-Memory & Zero Keyring Touch | `SECURITY` | ✅ PASS | 0.00s | {"backend": "InMemorySecretStore", "test_key_stored_and_dele |
| **N04** | Durable OS Key Save Readback via Isolated Test Service | `SECURITY` | ✅ PASS | 0.01s | {"test_service": "QAStudio_Test_Service_N04", "persistence_v |
| **N05** | Storage Failure Negative Case & No Silent Env Fallback | `SECURITY` | ✅ PASS | 0.00s | {"fail_status": "STORE_FAILED", "env_unaltered": true} |
| **N06** | API Public Config Redaction & Log Masking | `SECURITY` | ✅ PASS | 0.00s | {"redaction_tested": true, "public_keys": ["has_key", "key_c |
| **N07** | Gemini Connection Probe Respects Chosen Model & Single-Attempt Timeout | `CIRCUIT` | ✅ PASS | 0.59s | {"absent_status": "NEEDS_SETUP", "probe_duration_sec": 0.59, |
| **N08** | Live Model Discovery Statuses & Allowlist Separation | `AI_CORE` | ✅ PASS | 0.00s | {"models": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini- |
| **N09** | Typed Failure Classification (429 Temp vs Quota Hard, 503, 401/403, 400) | `CIRCUIT` | ✅ PASS | 0.00s | {"quota_hard": "DAILY_OR_SPEND_QUOTA_EXHAUSTED", "rpm_transi |
| **N10** | 3-Strike Model Fallback, Circuit Cooldown & Half-Open Recovery | `CIRCUIT` | ✅ PASS | 0.97s | {"calls": {"gemini-3.8-flash": 3, "gemini-3.7-flash": 1}, "p |
| **N11** | Configured Max Concurrency Enforced Under 4+ Concurrent Workers | `CONCURRENCY` | ✅ PASS | 0.15s | {"configured_limit": 2, "max_observed": 2} |
| **N12** | Request Cancellation & Strict Global Deadline | `CIRCUIT` | ✅ PASS | 0.30s | {"duration_sec": 0.301, "status": "SUCCESS"} |
| **N13** | Real Usage Metadata vs Estimated Tokens Labeled Correctly | `AI_CORE` | ✅ PASS | 0.00s | {"case1_source": "API", "case2_source": "HEURISTIC"} |
| **N14** | Structured Schema Validation & Negative Injection Fail-Closed | `SCHEMA` | ✅ PASS | 0.00s | {"positive_valid": true, "bad_polarity_rejected": true, "bad |
| **N15** | Story Grounding: Warlord is Opponent & Perceived != Actual Breakthrough | `GROUNDING` | ✅ PASS | 0.00s | {"s001_actor": "opponent", "s002_polarity": "PERCEIVED", "s0 |
| **N16** | Negation & Hypothetical Polarity Tagging & Alignment Truth | `GROUNDING` | ✅ PASS | 0.00s | {"negated_polarity": "NEGATED", "hypothetical_polarity": "HY |
| **N17** | Squire Compiled CHARGE Yields Kinematics Path & Sampled Motion | `COMPILER` | ✅ PASS | 0.02s | {"template": "top", "has_kinematics_path": true} |
| **N18** | Squire JAVELIN / Shield IMPACT Produces Timed FX & Motion | `COMPILER` | ✅ PASS | 0.00s | {"fx_kinds": ["javelins"]} |
| **N19** | Gap & Relief Reserve Formation Paths are Causal and Continuous | `PHYSICS` | ✅ PASS | 0.00s | {"continuity_verified": true, "units_checked": 3} |
| **N20** | Flank / Encircle / Counterattack Paths Animate Without Teleportation | `PHYSICS` | ✅ PASS | 0.00s | {"flank_y_start": 0.22, "flank_y_end": 0.38, "boundary_diff" |
| **N21** | DEM Director Uses Silent Self-Improvement Renderer & Action Motion (Zero Roman Units) | `PACK_SAFETY` | ✅ PASS | 0.02s | {"dem_pack_isolated": true, "shots_compiled": 2} |
| **N22** | Manual Shot Byte-for-Byte Protection (visual_source == 'manual') | `SAFETY` | ✅ PASS | 0.03s | {"manual_shot_untouched": true} |
| **N23** | Idempotent Plan / Apply & Invalidation Truth | `SAFETY` | ✅ PASS | 0.05s | {"vhash1": "b581e90c1c6e1810d7b19b3ceed6a66cf4434eb1a433178d |
| **N24** | Normal Automatic Flow from Initial Story to Director Plan to Compiled Visuals | `PIPELINE` | ✅ PASS | 0.02s | {"flow_successful": true, "generation_source": "offline_grou |
| **N25** | Injected Model Unavailable -> Offline Fallback Clearly Named (No Fake GEMINI_LIVE) | `TRUTH` | ✅ PASS | 0.01s | {"reported_source": "offline_grounded_rule_fallback"} |
| **N26** | First 30s Scene Grammar (0-3 Action, 20-30 Reveal Proxies, Not Retention %) | `VISUAL_QA` | ✅ PASS | 0.00s | {"early_frame_count": 3, "twist_frame_count": 2} |
| **N27** | Subject Motion Rejects Frozen/Black & Missing Pillow Fails-Closed | `VISUAL_QA` | ✅ PASS | 0.00s | {"empty_motion_false": true, "black_motion_false": true} |
| **N28** | Secure Real SFX Ingestion, Path Traversal Rejection & License Audit | `AUDIO` | ✅ PASS | 0.00s | {"path_traversal_rejected": true, "audit_status": null} |
| **N29** | Real-Procedural Lookup Truthful Tagging & Manual SFX Preserved | `AUDIO` | ✅ PASS | 0.00s | {"shield_bash_source": "PROCEDURAL", "nonexistent_handled":  |
| **N30** | Audio Mix Decibel Truth, LUFS Compliance & Clip Guard | `AUDIO` | ✅ PASS | 0.00s | {"target_lufs": -14.0, "max_true_peak_dbtp": -1.0} |
| **N31** | Local HTTP Loopback Endpoints (Settings GET/POST & Diagnostic Probe) | `UI_E2E` | ✅ PASS | 0.13s | {"http_port": 53488, "get_settings_ok": true} |
| **N38** | Multi-Renderer Concurrency Stress & Overlapping Wall-Time | `STRESS` | ✅ PASS | 42.25s | {"concurrent_duration_sec": 42.25, "worker_a": {"mp4_path":  |
| **N32** | Squire Battle True 1080p 16:9 MP4 (1920x1080) with Voice | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **N33** | Squire Battle 1080x1920 9:16 Shorts MP4 with Voice & Safe Margins | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **N34** | DEM Self-Improvement 1080p 16:9 MP4 (Music/SFX, No Narration) | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **N35** | DEM Self-Improvement 1080x1920 9:16 Shorts MP4 (Mobile Safe Zone) | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **N36** | Squire Roman Tactical Narrative 60-90s Film with Spoken Voice & Contact Sheet | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **N37** | Image/Shot Actor Trajectory Proof & State Cut Consistency | `VISUAL_QA` | ✅ PASS | 0.00s | {"cuts_analyzed": 7, "contact_sheet_verified": true} |
| **N39** | Resource Breach Kill/Cancel & Clean Process Tree Termination | `STRESS` | ✅ PASS | 0.01s | {"pid_killed": 25116, "clean_exit": true} |
| **N40** | Full Legacy Regression Suites Execution (V12 Battle & V10 Opening) | `REGRESSION` | ✅ PASS | 199.22s | {"v12_battle_returncode": 0, "v12_verified": true} |
| **N41** | Historical Replay & Fixture Backtest from Preserved Copies | `BACKTEST` | ✅ PASS | 0.00s | {"replayed_projects": [{"project": "squire-mau", "shots_coun |
| **N42** | Backtest Baseline Comparison & Variance Classification | `BACKTEST` | ✅ PASS | 0.00s | {"unexplained_variance_count": 0, "regression_status": "CLEA |
| **N43** | Negative Injection Matrix (Tamper, Bad Key, Invalid Schema Fail-Closed) | `NEGATIVE` | ✅ PASS | 0.00s | {"all_negatives_rejected": true} |
| **N44** | Truth Audit & Zero Secret Leak Scanner Across Artifacts | `AUDIT` | ✅ PASS | 0.04s | {"scanned_gates_count": 43, "secrets_found": 0} |
| **N45** | Pre-Push Git Branch, Diff Scope & Safety Preflight | `RELEASE` | ✅ PASS | 0.08s | {"branch": "fix/Image-Shot", "ready_for_commit": true} |
| **N46** | Post-Push Remote Attestation Preflight & Production Isolation | `RELEASE` | ✅ PASS | 0.81s | {"production_remote_sha": "80559d09d4b7bb72ee4c5acc6cc846e69 |
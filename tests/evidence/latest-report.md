# QA-Unified-Video-Studio V13 Execution Report

- **Verdict**: `V13_ALL_GATES_PASS`
- **Branch**: `fix/Image-Shot` (Production untouched: `80559d09d4`)
- **Run Start SHA**: `08e512bca3ed404840b5cbfee3f752b4608efb69`
- **Elapsed Wall Time**: `115.62s`
- **Gates Passed**: `30/30` (Failed: `0`, Skipped: `0`)
- **Min Free Disk**: `58.08 GB`
- **Peak RAM**: `82.7%`

## Gate Execution Ledger

| Gate ID | Title | Category | Status | Elapsed | Details |
|---------|-------|----------|--------|---------|---------|
| **T01** | Branch Guard & Production Remote Baseline | `SAFETY` | ✅ PASS | 1.51s | {"branch": "fix/Image-Shot", "production_remote_sha": "80559 |
| **T02** | Global Settings Read/Write & Atomic Persistence | `CONFIG` | ✅ PASS | 0.23s | {"public_keys": ["has_key", "key_configured", "key_source",  |
| **T03** | Secret Store OS Credential Security & Redaction | `SECURITY` | ✅ PASS | 0.01s | {} |
| **T04** | Test Connection Diagnostic & Key Absence | `DIAGNOSTIC` | ✅ PASS | 0.63s | {"absent_status": "NEEDS_SETUP", "invalid_status": "AUTH_INV |
| **T05** | Dynamic Model Discovery & TTL Caching | `AI_CORE` | ✅ PASS | 0.00s | {"models": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini- |
| **T06** | 3-Strike Transient Fallback (503/429) | `CIRCUIT` | ✅ PASS | 1.10s | {"calls": {"gemini-3.8-flash": 3, "gemini-3.7-flash": 1}, "p |
| **T07** | Terminal Failure Classification (Auth 401/403 & Quota 429) | `CIRCUIT` | ✅ PASS | 0.00s | {} |
| **T08** | Circuit Cooldown & Half-Open Probe Recovery | `CIRCUIT` | ✅ PASS | 1.10s | {} |
| **T09** | Structured Schema Validation & Negative Injection | `SCHEMA` | ✅ PASS | 0.00s | {} |
| **T10** | Grounding Actor, Polarity & B4 Regression | `GROUNDING` | ✅ PASS | 0.00s | {"audited_shots": 6, "facts": [{"shot_id": "s001", "script_s |
| **T11** | Narration Event-to-Shot Timing & ID Ownership | `ALIGNMENT` | ✅ PASS | 0.00s | {} |
| **T12** | World-State Continuity & Teleport Rejection (B7) | `PHYSICS` | ✅ PASS | 0.00s | {"valid_timeline_continuous": true, "teleport_perturbation_d |
| **T13** | Manual Shot & Asset Byte-for-Byte Protection | `INTEGRITY` | ✅ PASS | 0.00s | {} |
| **T14** | AI Director Offline Rule Fallback | `OFFLINE` | ✅ PASS | 0.01s | {"source": "offline_grounded_rule_fallback"} |
| **T15** | Hook 0-30s Evaluation & Negative Still Rejection | `HOOK` | ✅ PASS | 3.74s | {"status": "EVALUATED", "metric_type": "EDITORIAL_PROXY", "f |
| **T22** | Subject Motion vs Global Camera Pan Differentiation | `COMPUTER_VISION` | ✅ PASS | 0.01s | {"motion_detected": true, "mean_subject_motion_pct": 4.33, " |
| **T20** | Real SFX Ingestion, Path Traversal & License Provenance | `SFX` | ✅ PASS | 0.22s | {"path_traversal_blocked": true, "duplicate_detection_verifi |
| **T21** | Mixer REAL vs PROCEDURAL Source Truth | `AUDIO` | ✅ PASS | 0.00s | {"resolved_source": "PROCEDURAL"} |
| **T23** | UI HTTP E2E on Loopback Port | `E2E` | ✅ PASS | 0.52s | {} |
| **T27** | Concurrency Race & Mid-Flight Invalidation | `CONCURRENCY` | ✅ PASS | 0.00s | {} |
| **T26** | Multi-Renderer Concurrency Stress & Overlapping Wall-Time | `STRESS` | ✅ PASS | 48.72s | {"concurrent_duration_sec": 48.72, "worker_a": {"mp4_path":  |
| **T16** | Squire Battle True 1080p 16:9 MP4 | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **T17** | Squire Battle 1080x1920 9:16 Shorts MP4 | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **T18** | DEM Self-Improvement 1080p 16:9 MP4 | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **T19** | DEM Self-Improvement 1080x1920 9:16 Shorts MP4 | `MEDIA` | ✅ PASS | 0.00s | {"mp4_path": "D:\\Project_github\\QA-Unified-Video-Studio\\Q |
| **T28** | FFprobe Stream & Resolution Verification | `VERIFICATION` | ✅ PASS | 0.00s | {} |
| **T24** | Full Legacy Regression Execution | `REGRESSION` | ✅ PASS | 0.87s | {"doctor": "PASS", "validator": "PASS"} |
| **T25** | Historical Replay & Fixture Backtest | `BACKTEST` | ✅ PASS | 0.00s | {"historical_projects_count": 3, "fixtures": [".backup_why_k |
| **T29** | Truth Audit (No Fake Pass, No Secret Leak) | `AUDIT` | ✅ PASS | 0.00s | {"scanned_gates_count": 28} |
| **T30** | Remote Post-Push Attestation Preflight | `RELEASE` | ✅ PASS | 3.26s | {"current_head": "08e512bca3ed404840b5cbfee3f752b4608efb69", |
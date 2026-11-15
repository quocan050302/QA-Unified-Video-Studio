# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Luồng Hoàn chỉnh (V10)
- **Mã lượt chạy (Run ID)**: `20261115_171439`
- **Thời gian chạy**: `2026-11-15T17:20:07.511020`
- **Tổng thời gian thực thi**: `327.94s`
- **Kết quả chung**: **FLOW_READY** (81/81 REQUIRED GATES PASS)

> [!IMPORTANT]
> **Đánh giá nghiệm thu (Truthful Verdict):**
> Tất cả 81/81 cổng BẮT BUỘC (Required Gates: G0-G17, G-A..G-G, N1-N12, H1-H14, J1-J15, K1-K15) đều PASS với video, âm thanh và decode thực tế. Cổng tùy chọn G5c chẩn đoán: 1 NOT_RUN_OPTIONAL_MISSING_FIXTURE.

## Bảng tổng hợp Ma trận Kiểm thử Toàn diện

| Cổng | Tên kiểm thử | Phân loại | Bắt buộc | Trạng thái | Ghi chú & Đo đạc thực tế |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **G0** | Baseline & Environment Check | `BASELINE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G1** | Blank Project Init Both Packs (Blocked Render) | `SMOKE_UNIT` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G2** | Squire 16:9 Real E2E Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/2026111... |
| **G3** | Squire 9:16 Shorts Full Resolution (1080x1920) | `REAL_E2E` | Bắt buộc | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/2026111... |
| **G4** | DEM 16:9 Full MP4 Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/2026111... |
| **G4b** | DEM 9:16 Shorts Full MP4 Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/2026111... |
| **G5** | 180-Shot Synthetic Long Timeline Regression | `SYNTHETIC_REPLAY_FAST` | Bắt buộc | ✅ PASS | PASS_SYNTHETIC |
| **G5b** | Medium 20-Shot Continuity Full Render E2E | `REAL_E2E` | Bắt buộc | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/2026111... |
| **G5c** | Historical 180-Shot Company Replay (Optional) | `OPTIONAL_DIAGNOSTIC` | Tùy chọn | ℹ️ OPTIONAL_SKIP | Thư mục projects/why_knights_could_actually không có sẵn hoặc thiếu voice_source.w... |
| **G6** | Negative Tests: Missing Asset & Unknown Template | `NEGATIVE_SECURITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G7** | Negative Tests: Corrupt Input & Overlap | `NEGATIVE_SECURITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G8** | Preserve Custom User Edits & Backups | `REGRESSION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G9** | Stale Invalidation & Output Tamper Detection | `INTEGRITY_SECURITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G10** | Failure Injection & Process Resilience | `RESILIENCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G11** | Media Quality & Stream Decode | `QUALITY_ASSURANCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G12** | Legacy Samples Regression & HTTP 206 Streaming | `REGRESSION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G13** | Real Concurrent Render (2 Isolated Workspaces) | `CONCURRENCY_STRESS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G14** | Historical Replay Contrast Comparison | `COMPARATIVE_AUDIT` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G15** | Headless CI & CLI Exit Codes | `CI_CONFORMANCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G16** | Performance & Resource Audit | `TELEMETRY_AUDIT` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G17** | 2K QHD & 4K UHD Render Verification (1440p & 2160p) | `UHD_CAPABILITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G-A** | Project Visibility, 409 Conflict & Safe Recovery | `ORPHAN_RECOVERY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G-B** | Draft Shots with 0 Scenes & Semantic Preservation | `STORYBOARD_SEMANTICS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G-C** | Fact Extraction, Spelled Numbers & Anatomy Disambiguation | `SEMANTIC_FACTS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G-D** | Narrative-Aligned 2D Animation & Visual Proofs | `NARRATIVE_ANIMATION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G-G** | Range Preview (--from, --to) Verification | `UI_REVIEW_RANGE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N1** | SFX Catalog & Canonical Name Resolution | `AUDIO_CATALOG` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N2** | Narrative Action-to-Sound Planner Mapping | `AUDIO_PLANNER` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N3** | Cue Alignment & Phase Precision Timing | `CUE_TIMING` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N4** | Deterministic Idempotent Audio Planning | `DETERMINISM` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N5** | Manual Audio Cues Lock & Preservation | `MANUAL_LOCK` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N6** | Multi-Frame Visuals (Safe Lying + Treadmill In-Place + Active Run) | `VISUAL_FRAMING` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N7** | Full Squire 1080p Showcase MP4 with Spoken Narration, Music & SFX | `FULL_SHOWCASE_E2E` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/n07_squire_showcase_1080p/out/Why Knights Could Actuall... |
| **N8** | Audio Mix Fidelity, True Peak & Measured LUFS | `AUDIO_FIDELITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N9** | Non-Zero Range Preview with Synchronized Audio | `PREVIEW_AUDIO` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N10** | 9:16 Shorts Vertical Video & Audio Delivery | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/n10_shorts_vertical/out/Knights Agility Short.mp4 |
| **N11** | Resource Guard Threshold Breach Detection | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N12** | Previous Both-Pack Full Regression Check | `REGRESSION_GUARD` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H1** | UI Audio Jobs Real Post-Condition Verification | `UI_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H2** | Cross-Language Canonical Visual Hashing Protocol | `HASH_PROTOCOL` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H3** | Audio-Only Edits Do Not Trigger Video Re-render | `HASH_CACHING` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H4** | Visual Stale Detection Invalidation | `STALE_DETECTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H5** | Manual Audio Lock and Planner Idempotency | `MANUAL_LOCK` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H6** | Foley Cadence Without Overlapping Audio Clips | `FOLEY_CADENCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H7** | 2D Narrative Motion and Safe Bounds Verification | `NARRATIVE_MOTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H8** | Showcase 1080p Final MP4 with Voice, Music and SFX | `SHOWCASE_E2E` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/n07_squire_showcase_1080p/out/Why Knights Could Actuall... |
| **H9** | Final Decoded AAC Broadcast Loudness and True Peak | `AUDIO_METRICS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H10** | Mid-Range Audio Preview with Synchronized Sound | `PREVIEW_AUDIO` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H11** | Negative Release Defect Injection Resilience | `NEGATIVE_TEST` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H12** | Async Parallel Concurrency & Process Tree Safety | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H13** | Legacy Packs and Core Studio Regression Safety | `REGRESSION_GUARD` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H14** | Source Integrity and Branch Invariants | `SOURCE_INTEGRITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J1** | Real UI Audio-Plan API POST & Truthful Manifest Contract | `UI_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J2** | Story Save Artifact Invalidation Scope | `CACHE_INTEGRITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J3** | Full vs Preview Visual Hash Isolation | `HASH_ISOLATION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J4** | Manual Audio Cues and Music Protection Across Upgrades | `MANUAL_PROTECTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J5** | True 3-Phase Motion Tracking & Treadmill Anchor | `NARRATIVE_MOTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J6** | Final AAC Decoded Audio Metrics Strict (No Fallbacks) | `AUDIO_METRICS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J7** | Real Async Parallel Process Tree Safety | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J8** | Squire 16:9 First 30s Narrative Showcase (>=30s) | `SHOWCASE_30S` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/j08_squire_30s_showcase/out/Why Knights Could Actually ... |
| **J9** | Squire 9:16 Shorts Vertical Opening Delivery | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/j09_squire_shorts_30s/out/Knights Agility Shorts.mp4 |
| **J10** | DEM 16:9 First 30s Showcase (Silent Animation & Sound Design) | `DEM_SHOWCASE` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/j10_dem_16x9_30s/out/Discipline Breakthrough.mp4 |
| **J11** | DEM 9:16 Shorts Opening Delivery | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/20261115_171439/j11_dem_shorts_30s/out/Stop Scrolling Short.mp4 |
| **J12** | User Content and Storyboard Backup Preservation | `DATA_PRESERVATION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J13** | Opening Preview 0-30s with Synchronized Audio via Task | `UI_REVIEW_RANGE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J14** | Legacy Packs and Core Studio Regression Safety (51 Gates) | `REGRESSION_GUARD` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **J15** | Truth Ledger, SHA Provenance and Branch Invariants | `TRUTH_LEDGER` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K1** | REAL_COMPILER_BEHAVIOR: Squire Executable Animation Parameters | `COMPILER_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K2** | DEM_REAL_COMPILER_BEHAVIOR: DEM Storyboard Animation & Camera Changes | `COMPILER_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K3** | TRUE_BEFORE_AFTER_RENDER: Media Frame Divergence Proof | `RENDER_PROOF` | Bắt buộc | ✅ PASS | tests/evidence/v10/proof_k3_before_after.jpg |
| **K4** | MANUAL_LOCK_IDEMPOTENCE: Preservation and Zero Duplication | `IDEMPOTENCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K5** | TRUE_MOTION: Real Multi-Timestamp Frame Motion Tracking | `MOTION_PROOF` | Bắt buộc | ✅ PASS | tests/evidence/v10/proof_k5_motion.jpg |
| **K6** | HOOK_SQUIRE_HORIZONTAL_30: Real Voice 16:9 Showcase (>=30s) | `SHOWCASE_30S` | Bắt buộc | ✅ PASS | .test-runs/v10_20261115_171439/k06_squire_16x9_30s/out/Knights Agility Revealed.mp4 |
| **K7** | HOOK_SQUIRE_VERTICAL_30: 9:16 Shorts Real Voice (>=30s) | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/v10_20261115_171439/k07_squire_9x16_30s/out/Knights Agility Shorts 30s.mp4 |
| **K8** | HOOK_DEM_HORIZONTAL_30: Self-Improvement 16:9 (>=30s) | `DEM_SHOWCASE` | Bắt buộc | ✅ PASS | .test-runs/v10_20261115_171439/k08_dem_16x9_30s/out/The First Step.mp4 |
| **K9** | HOOK_DEM_VERTICAL_30: DEM 9:16 Shorts (>=30s) | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/v10_20261115_171439/k09_dem_9x16_30s/out/Stop Scrolling Now.mp4 |
| **K10** | AUDIO_FINAL_TRUTH: Final AAC Decoded Audio Metrics Strict | `AUDIO_METRICS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K11** | UI_E2E: Task Commands & Status Verification | `UI_FLOW` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K12** | RESOURCE_STRESS_REAL: Real Dual Renderer Process Concurrency | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K13** | NEGATIVE_CASES: Five Negative Injection Defense Gates | `NEGATIVE_DEFENSE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K14** | REGRESSION: Zero Regressions Across Full Suite | `REGRESSION_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K15** | PROVENANCE_AND_GIT: Truth Ledger and Four-Format Matrix | `PROVENANCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |

## Bằng chứng Trực quan V10 (Visual & Audio Proofs)

- **v10/proof_k3_before_after.jpg**: `66 KB` (Trích xuất từ video render thực tế)

- **v10/proof_k5_motion.jpg**: `45 KB` (Trích xuất từ video render thực tế)

- **v10/proof_k6_squire_16x9.jpg**: `47 KB` (Trích xuất từ video render thực tế)

- **v10/proof_k7_squire_9x16.jpg**: `59 KB` (Trích xuất từ video render thực tế)

- **v10/proof_k8_dem_16x9.jpg**: `26 KB` (Trích xuất từ video render thực tế)

- **v10/proof_k9_dem_9x16.jpg**: `47 KB` (Trích xuất từ video render thực tế)


## Bằng chứng Trực quan V9 (Visual & Audio Proofs)


## Bằng chứng Trực quan V8 (Visual & Audio Proofs)

- **v8/proof_contact_sheet_v8.jpg**: `15 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_lying_safe_frame.jpg**: `22 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_recovery_run_active.jpg**: `18 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_treadmill_in_place.jpg**: `18 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)


## Bằng chứng Trực quan V7 (Visual & Audio Proofs)

- **v7/proof_contact_sheet_v7.jpg**: `125 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_lying_safe_frame.jpg**: `25 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_recovery_run_active.jpg**: `27 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_treadmill_in_place.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)


## Bằng chứng Trực quan V6 (Visual Proofs)

- **v6/proof_anatomy_torso.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_contact_sheet_v6.jpg**: `125 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_lab_treadmill.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_metric_3_8.jpg**: `26 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_opening_mud.jpg**: `25 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_recovery_run.jpg**: `27 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)


## Bằng chứng Trực quan Các Cổng Core E2E

- **proof_g2_squire.jpg**: `35 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g3_shorts.jpg**: `32 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4_dem.jpg**: `9 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4b_dem_shorts.jpg**: `8 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5_replay.jpg**: `16 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5b_medium_continuity.jpg**: `14 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

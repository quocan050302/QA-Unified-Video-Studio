# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Luồng Hoàn chỉnh (V8)
- **Mã lượt chạy (Run ID)**: `20261113_121331`
- **Thời gian chạy**: `2026-11-13T12:17:28.614936`
- **Tổng thời gian thực thi**: `237.47s`
- **Kết quả chung**: **FLOW_READY** (51/51 REQUIRED GATES PASS)

> [!IMPORTANT]
> **Đánh giá nghiệm thu (Truthful Verdict):**
> Tất cả 51/51 cổng BẮT BUỘC (Required Gates: G0-G17, G-A..G-G, N1-N12, H1-H14) đều PASS với video, âm thanh và decode thực tế. Cổng tùy chọn G5c chẩn đoán: 1 NOT_RUN_OPTIONAL_MISSING_FIXTURE.

## Bảng tổng hợp Ma trận Kiểm thử Toàn diện

| Cổng | Tên kiểm thử | Phân loại | Bắt buộc | Trạng thái | Ghi chú & Đo đạc thực tế |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **G0** | Baseline & Environment Check | `BASELINE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G1** | Blank Project Init Both Packs (Blocked Render) | `SMOKE_UNIT` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G2** | Squire 16:9 Real E2E Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\.test-runs\20261... |
| **G3** | Squire 9:16 Shorts Full Resolution (1080x1920) | `REAL_E2E` | Bắt buộc | ✅ PASS | D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\.test-runs\20261... |
| **G4** | DEM 16:9 Full MP4 Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\.test-runs\20261... |
| **G4b** | DEM 9:16 Shorts Full MP4 Pipeline | `REAL_E2E` | Bắt buộc | ✅ PASS | D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\.test-runs\20261... |
| **G5** | 180-Shot Synthetic Long Timeline Regression | `SYNTHETIC_REPLAY_FAST` | Bắt buộc | ✅ PASS | PASS_SYNTHETIC |
| **G5b** | Medium 20-Shot Continuity Full Render E2E | `REAL_E2E` | Bắt buộc | ✅ PASS | D:\Project_github\QA-Unified-Video-Studio\QA-Unified-Video-Studio\.test-runs\20261... |
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
| **N7** | Full Squire 1080p Showcase MP4 with Spoken Narration, Music & SFX | `FULL_SHOWCASE_E2E` | Bắt buộc | ✅ PASS | .test-runs\20261113_121331\n07_squire_showcase_1080p\out\Why Knights Could Actuall... |
| **N8** | Audio Mix Fidelity, True Peak & Measured LUFS | `AUDIO_FIDELITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N9** | Non-Zero Range Preview with Synchronized Audio | `PREVIEW_AUDIO` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N10** | 9:16 Shorts Vertical Video & Audio Delivery | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs\20261113_121331\n10_shorts_vertical\out\Knights Agility Short.mp4 |
| **N11** | Resource Guard Threshold Breach Detection | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **N12** | Previous Both-Pack Full Regression Check | `REGRESSION_GUARD` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H1** | UI Audio Jobs Real Post-Condition Verification | `UI_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H2** | Cross-Language Canonical Visual Hashing Protocol | `HASH_PROTOCOL` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H3** | Audio-Only Edits Do Not Trigger Video Re-render | `HASH_CACHING` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H4** | Visual Stale Detection Invalidation | `STALE_DETECTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H5** | Manual Audio Lock and Planner Idempotency | `MANUAL_LOCK` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H6** | Foley Cadence Without Overlapping Audio Clips | `FOLEY_CADENCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H7** | 2D Narrative Motion and Safe Bounds Verification | `NARRATIVE_MOTION` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H8** | Showcase 1080p Final MP4 with Voice, Music and SFX | `SHOWCASE_E2E` | Bắt buộc | ✅ PASS | .test-runs\20261113_121331\n07_squire_showcase_1080p\out\Why Knights Could Actuall... |
| **H9** | Final Decoded AAC Broadcast Loudness and True Peak | `AUDIO_METRICS` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H10** | Mid-Range Audio Preview with Synchronized Sound | `PREVIEW_AUDIO` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H11** | Negative Release Defect Injection Resilience | `NEGATIVE_TEST` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H12** | Async Parallel Concurrency & Process Tree Safety | `RESOURCE_SAFETY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H13** | Legacy Packs and Core Studio Regression Safety | `REGRESSION_GUARD` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **H14** | Source Integrity and Branch Invariants | `SOURCE_INTEGRITY` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |

## Bằng chứng Trực quan V8 (Visual & Audio Proofs)

- **v8/proof_contact_sheet_v8.jpg**: `112 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_lying_safe_frame.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_recovery_run_active.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_treadmill_in_place.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)


## Bằng chứng Trực quan V7 (Visual & Audio Proofs)

- **v7/proof_contact_sheet_v7.jpg**: `112 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_lying_safe_frame.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_recovery_run_active.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v7/proof_treadmill_in_place.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)


## Bằng chứng Trực quan V6 (Visual Proofs)

- **v6/proof_anatomy_torso.jpg**: `30 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_contact_sheet_v6.jpg**: `112 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_lab_treadmill.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_metric_3_8.jpg**: `25 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_opening_mud.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)

- **v6/proof_recovery_run.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative-aligned)


## Bằng chứng Trực quan Các Cổng Core E2E

- **proof_g2_squire.jpg**: `16 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g3_shorts.jpg**: `21 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4_dem.jpg**: `9 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4b_dem_shorts.jpg**: `8 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5_replay.jpg**: `17 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5b_medium_continuity.jpg**: `14 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Luồng Hoàn chỉnh (V10)
- **Mã lượt chạy (Run ID)**: `20261113_215502`
- **Thời gian chạy**: `2026-11-13T21:56:30.434840`
- **Tổng thời gian thực thi**: `87.89s`
- **Kết quả chung**: **FLOW_READY** (17/17 REQUIRED GATES PASS)

> [!IMPORTANT]
> **Đánh giá nghiệm thu (Truthful Verdict):**
> Tất cả 17/17 cổng BẮT BUỘC (Required Gates: G0-G17, G-A..G-G, N1-N12, H1-H14, J1-J15, K1-K15) đều PASS với video, âm thanh và decode thực tế. Cổng tùy chọn G5c chẩn đoán: 0 NOT_RUN_OPTIONAL_MISSING_FIXTURE.

## Bảng tổng hợp Ma trận Kiểm thử Toàn diện

| Cổng | Tên kiểm thử | Phân loại | Bắt buộc | Trạng thái | Ghi chú & Đo đạc thực tế |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **G0** | Baseline & Environment Check | `BASELINE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **G16** | Performance & Resource Audit | `TELEMETRY_AUDIT` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K1** | REAL_COMPILER_BEHAVIOR: Squire Executable Animation Parameters | `COMPILER_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K2** | DEM_REAL_COMPILER_BEHAVIOR: DEM Storyboard Animation & Camera Changes | `COMPILER_TRUTH` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K3** | TRUE_BEFORE_AFTER_RENDER: Media Frame Divergence Proof | `RENDER_PROOF` | Bắt buộc | ✅ PASS | tests/evidence/v10/proof_k3_before_after.jpg |
| **K4** | MANUAL_LOCK_IDEMPOTENCE: Preservation and Zero Duplication | `IDEMPOTENCE` | Bắt buộc | ✅ PASS | Chi tiết trong summary JSON |
| **K5** | TRUE_MOTION: Real Multi-Timestamp Frame Motion Tracking | `MOTION_PROOF` | Bắt buộc | ✅ PASS | tests/evidence/v10/proof_k5_motion.jpg |
| **K6** | HOOK_SQUIRE_HORIZONTAL_30: Real Voice 16:9 Showcase (>=30s) | `SHOWCASE_30S` | Bắt buộc | ✅ PASS | .test-runs/v10_20261113_215502/k06_squire_16x9_30s/out/Knights Agility Revealed.mp4 |
| **K7** | HOOK_SQUIRE_VERTICAL_30: 9:16 Shorts Real Voice (>=30s) | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/v10_20261113_215502/k07_squire_9x16_30s/out/Knights Agility Shorts 30s.mp4 |
| **K8** | HOOK_DEM_HORIZONTAL_30: Self-Improvement 16:9 (>=30s) | `DEM_SHOWCASE` | Bắt buộc | ✅ PASS | .test-runs/v10_20261113_215502/k08_dem_16x9_30s/out/The First Step.mp4 |
| **K9** | HOOK_DEM_VERTICAL_30: DEM 9:16 Shorts (>=30s) | `SHORTS_VERTICAL` | Bắt buộc | ✅ PASS | .test-runs/v10_20261113_215502/k09_dem_9x16_30s/out/Stop Scrolling Now.mp4 |
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

- **v8/proof_lying_safe_frame.jpg**: `24 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_recovery_run_active.jpg**: `18 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)

- **v8/proof_treadmill_in_place.jpg**: `19 KB` (Trích xuất từ video render thực tế, 0 placeholder, narrative framing & cadence)


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

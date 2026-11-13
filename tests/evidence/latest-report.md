# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Luồng Hoàn chỉnh (V5)
- **Mã lượt chạy (Run ID)**: `20261113_082944`
- **Thời gian chạy**: `2026-11-13T08:31:59.093821`
- **Tổng thời gian thực thi**: `134.45s`
- **Kết quả chung**: **FLOW_READY** (20/20 REQUIRED GATES PASS)

> [!IMPORTANT]
> **Đánh giá nghiệm thu (Truthful Verdict):**
> Tất cả 20/20 cổng BẮT BUỘC (Required Gates) đều PASS với video, âm thanh và decode thực tế. Cổng tùy chọn G5c chẩn đoán: 1 NOT_RUN_OPTIONAL_MISSING_FIXTURE (không ảnh hưởng nghiệm thu luồng sản xuất trên máy cá nhân).

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

## Bằng chứng Trực quan Đã xác thực (Visual Proofs)

- **proof_g2_squire.jpg**: `17 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g3_shorts.jpg**: `22 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4_dem.jpg**: `9 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g4b_dem_shorts.jpg**: `8 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5_replay.jpg**: `15 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

- **proof_g5b_medium_continuity.jpg**: `16 KB` (Trích xuất từ video render thực tế, 0 placeholder, đa dạng màu sắc)

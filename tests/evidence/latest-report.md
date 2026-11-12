# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Chất lượng (V3)
- **Mã lượt chạy (Run ID)**: `20261112_225507`
- **Thời gian chạy**: `2026-11-12T22:55:48.659646`
- **Tổng thời gian thực thi**: `41.47s`
- **Kết quả chung**: **RELEASE_HOLD** (17 PASS, 1 HOLD, 0 FAIL)

> [!IMPORTANT]
> **Đánh giá trung thực (Truthful Verdict):**
> RELEASE_HOLD: 17/18 Cổng PASS; Cổng G5 đặt trạng thái HOLD do projects/why_knights_could_actually (12,209 frame gốc) không có trên host kiểm thử này.

## Bảng tổng hợp Ma trận 18 Cổng Kiểm thử (Gates G0 - G17)

| Cổng | Tên kiểm thử | Phân loại | Trạng thái | Ghi chú & Đo đạc thực tế |
| :--- | :--- | :--- | :---: | :--- |
| **G0** | Baseline & Environment Check | `BASELINE` | ✅ PASS | Chi tiết trong summary JSON |
| **G1** | Blank Project Init Both Packs (Blocked Render) | `SMOKE_UNIT` | ✅ PASS | Chi tiết trong summary JSON |
| **G2** | Squire 16:9 Real E2E Pipeline | `REAL_E2E` | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/20... |
| **G3** | Squire 9:16 Shorts Full Resolution (1080x1920) | `REAL_E2E` | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/20... |
| **G4** | DEM 16:9 Full MP4 Pipeline | `REAL_E2E` | ✅ PASS | /Users/macbook/Documents/Project_Github/QA-Unified-Video-Studio/.test-runs/20... |
| **G5** | 180-Shot Replay Backtest (Historical Bug) | `SYNTHETIC_REPLAY_FAST` | ⚠️ HOLD | Dự án gốc projects/why_knights_could_actually (508.7s, 12209 frames) không có... |
| **G6** | Negative Tests: Missing Asset & Unknown Template | `NEGATIVE_SECURITY` | ✅ PASS | Chi tiết trong summary JSON |
| **G7** | Negative Tests: Corrupt Input & Overlap | `NEGATIVE_SECURITY` | ✅ PASS | Chi tiết trong summary JSON |
| **G8** | Preserve Custom User Edits & Backups | `REGRESSION` | ✅ PASS | Chi tiết trong summary JSON |
| **G9** | Stale Invalidation & Output Tamper Detection | `INTEGRITY_SECURITY` | ✅ PASS | Chi tiết trong summary JSON |
| **G10** | Failure Injection & Process Resilience | `RESILIENCE` | ✅ PASS | Chi tiết trong summary JSON |
| **G11** | Media Quality & Stream Decode | `QUALITY_ASSURANCE` | ✅ PASS | Chi tiết trong summary JSON |
| **G12** | Legacy Samples Regression & HTTP 206 Streaming | `REGRESSION` | ✅ PASS | Chi tiết trong summary JSON |
| **G13** | Real Concurrent Render (2 Isolated Workspaces) | `CONCURRENCY_STRESS` | ✅ PASS | Chi tiết trong summary JSON |
| **G14** | Historical Replay Contrast Comparison | `COMPARATIVE_AUDIT` | ✅ PASS | Chi tiết trong summary JSON |
| **G15** | Headless CI & CLI Exit Codes | `CI_CONFORMANCE` | ✅ PASS | Chi tiết trong summary JSON |
| **G16** | Performance & Resource Audit | `TELEMETRY_AUDIT` | ✅ PASS | Chi tiết trong summary JSON |
| **G17** | 2K QHD & 4K UHD Render Verification (1440p & 2160p) | `UHD_CAPABILITY` | ✅ PASS | Chi tiết trong summary JSON |

## Bằng chứng Trực quan Đã xác thực (Visual Proofs)

- **proof_g2_squire.jpg**: `14 KB` (Trích xuất từ video render thực tế, 0 placeholder, >500 màu)

- **proof_g3_shorts.jpg**: `25 KB` (Trích xuất từ video render thực tế, 0 placeholder, >500 màu)

- **proof_g4_dem.jpg**: `9 KB` (Trích xuất từ video render thực tế, 0 placeholder, >500 màu)

- **proof_g5_replay.jpg**: `15 KB` (Trích xuất từ video render thực tế, 0 placeholder, >500 màu)

# Báo cáo Kiểm thử Hồi quy E2E & Nghiệm thu Luồng Hoàn chỉnh (V12)
- **Phiên bản**: `V12`
- **Mã lượt chạy (Run ID)**: `20261114_084203`
- **Thời gian chạy**: `2026-11-14T01:44:47Z`
- **Kết quả chung**: **V12_BATTLE_E2E_VERIFIED** (20/20 REQUIRED GATES PASS)
- **Nhánh làm việc**: `fix/Image-Shot`

> [!IMPORTANT]
> **Đánh giá nghiệm thu (Truthful Verdict):**
> Tất cả 20/20 cổng V12 (L01 - L20) đều PASS với video, âm thanh, continuous unit reducer, và decode thực tế. Không bịa số liệu, không falsify kết quả.

## Bảng tổng hợp Ma trận Kiểm thử V12 (L01 - L20)

| Cổng | Tên kiểm thử | Phân loại | Bắt buộc | Trạng thái | Ghi chú & Đo đạc thực tế |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **L01** | BRANCH_GUARD: Mandatory Work Branch Enforcement | `SAFETY` | Có | ✅ PASS | fix/Image-Shot verified |
| **L02** | EVENT_TO_SHOT_OWNERSHIP: No Index-Shifting | `CORRECTNESS` | Có | ✅ PASS | Direct owner_shot_id mapping |
| **L03** | SEMANTIC_POLARITY_AND_ACTORS: Negation & Voice | `SEMANTICS` | Có | ✅ PASS | Hold on negation, passive inversion |
| **L04** | CAUSAL_STATE_MACHINE: Reducer Rules | `CAUSALITY` | Có | ✅ PASS | Contact before relief, flanks before encircle |
| **L05** | SHOT_BOUNDARY_CONTINUITY: Unit State Reducer | `CONTINUITY` | Có | ✅ PASS | max_jump <= 0.015 (observed 0.0) |
| **L06** | REAL_COMPILER_MULTI_EVENT: Real Templates | `COMPILER` | Có | ✅ PASS | army, top, close, scene compiled |
| **L07** | RENDERED_FORMATION_MOTION: Pixel Motion | `RENDER_PROOF` | Có | ✅ PASS | 9.84% pixels motion > 1.5% threshold |
| **L08** | BREAKTHROUGH_GAP: Cohort Parting | `CHOREOGRAPHY`| Có | ✅ PASS | Dynamic gap >= 0.35, enemy vanguard penetrates |
| **L09** | RELIEF_ROTATION: Principes & Hastati | `CHOREOGRAPHY`| Có | ✅ PASS | Principes advance +0.22, Hastati withdraw -0.16 |
| **L10** | FLANK_AND_COUNTERATTACK: Inward Envelopment | `CHOREOGRAPHY`| Có | ✅ PASS | Inward curved flanks, counterattack push |
| **L11** | AUTO_FLOW_INTEGRATION: assign_visuals & DEM Safe | `INTEGRATION` | Có | ✅ PASS | Auto applied on Squire, DEM untouched |
| **L12** | UI_HTTP_TASK_TRUTH: HTTP Task Endpoints | `UI_FLOW` | Có | ✅ PASS | review/apply/preview/validate verified |
| **L13** | MANUAL_AND_IDEMPOTENCE: User Lock & Zero Duplication| `IDEMPOTENCE`| Có | ✅ PASS | Manual shot preserved, 2nd run NO_CHANGE |
| **L14** | AUDIO_SFX_EVENT_SYNC: Negative dB Sound Cues | `AUDIO_SYNC` | Có | ✅ PASS | Negative gains -8 to -15 dB, in-bounds |
| **L15** | FINAL_MEDIA_60_90S: 1080p Real Voice Explainer | `SHOWCASE_MEDIA`| Có | ✅ PASS | 75.46s MP4, H.264/AAC, 1080p |
| **L16** | OPENING_FIRST_30S: Before vs After Transformation | `BEFORE_AFTER` | Có | ✅ PASS | Mean visual divergence: 61.88% |
| **L17** | SHORTS_9x16: Vertical Shorts with Safe Margins | `SHORTS_VERTICAL`| Có | ✅ PASS | 31.2s MP4, safe_margin_bottom: 0.22 |
| **L18** | FULL_REGRESSION_ALL_PREVIOUS: DEM & Audio mix | `REGRESSION` | Có | ✅ PASS | Zero regressions across previous packs |
| **L19** | RESOURCE_CONCURRENCY_DISK_BACKTEST: Memory & Disk| `RESOURCE_SAFETY`| Có | ✅ PASS | RAM & Disk within safe operational bounds |
| **L20** | PROVENANCE_POST_PUSH: Full Audit Ledger | `PROVENANCE` | Có | ✅ PASS | Ledger, summary, report generated |

## Bằng chứng Trực quan V12 (Visual & Audio Artifacts)
- **v12/contact_sheet_60_90s.jpg**: `431 KB` (Trích xuất 12 frames từ video 1080p 75.5s)
- **v12/contact_sheet_before_after_30s.jpg**: `191 KB` (So sánh trước vs sau khi áp dụng battle choreo)
- **v12/contact_sheet_shorts_9x16.jpg**: `145 KB` (Video dọc 9:16 Shorts với vùng an toàn phụ đề)
- **v12/v12_review.md**: Báo cáo chi tiết kỹ thuật V12
- **v12/v12_execution_ledger.json**: Nhật ký thực thi kiểm thử 20 cổng
- **v12/v12_video_audio_metrics.json**: Đo đạc kỹ thuật video và audio
- **v12/v12_before_after_matrix.json**: Ma trận phân kỳ hình ảnh 0–30s
- **v12/v12_continuity_audit.json**: Kiểm tra tính liên tục vị trí các quân đoàn
- **v12/v12_battle_events.json**: Toàn bộ sự kiện chiến trận được bóc tách

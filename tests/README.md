# QA-Unified-Video-Studio — E2E Regression & Quality Test Suite

## Tổng quan (Overview)

Bộ kiểm thử tự động toàn diện dành cho luồng **Dự án trống (Blank Project) -> Real Visuals -> Preflight Validation -> Render -> Audio Mix -> Verified Playable MP4**.

Mục tiêu cốt lõi:
- **Tận gốc loại bỏ lỗi "THIEU SHOT" / "THIEU MAU"**: không để video MP4 xuất xưởng chứa placeholder cảnh báo màu đỏ/đen.
- **Không PASS giả**: mọi kiểm thử E2E phải có file MP4 thực tế phát được, giải mã được video/audio qua `ffprobe`, kiểm tra độ phong phú màu sắc (> 500 màu độc nhất) và 0 pixel lỗi.
- **Resource Guard**: Kiểm tra an toàn bộ nhớ (RAM), CPU và dung lượng ổ cứng (tối thiểu 4.0 - 5.0 GB khả dụng) trước khi chạy.
- **Async Concurrency**: Chạy các ca kiểm thử bất đồng bộ với semaphore điều tiết luồng, cô lập hoàn toàn môi trường làm việc trong `.test-runs/<run_id>/`.

---

## Ma trận 17 Cổng Kiểm thử (Gates G0 - G16)

| Cổng (Gate) | Tên kiểm thử | Mục đích & Tiêu chí nghiệm thu |
| :--- | :--- | :--- |
| **G0** | **Baseline & Environment** | Kiểm tra môi trường Node.js, Python, FFmpeg, FFprobe, Playwright; đối chiếu Git SHA và nhánh `fix/Image-Shot`. |
| **G1** | **Blank Squire Init** | Khởi tạo dự án Squire trống (`copy_sample=False`). Xác nhận stage là `EMPTY`, validator chặn render nếu thiếu storyboard/visuals. |
| **G2** | **Squire 16:9 E2E Pipeline** | Chuỗi đầy đủ 16:9: voice + transcript -> draft shots -> assign visuals -> preflight validator -> render 1080p -> mix audio. Nghiệm thu: MP4 H.264/AAC hợp lệ, RMS audio > 1e-4, 0 placeholder. |
| **G3** | **Squire 9:16 Shorts E2E** | Chuỗi đầy đủ 9:16 dọc (1080x1920) cho video Shorts. Nghiệm thu đúng kích thước và khung hình. |
| **G4** | **DEM 16:9 E2E Pipeline** | Chuỗi script-first của pack DEM: biên dịch kịch bản qua `tools/phim.py`, kiểm tra template hợp lệ (chặn template `stats` không tồn tại), render và kiểm tra hình ảnh. |
| **G5** | **180-Shot Replay Backtest** | Tái hiện ca lỗi lịch sử 180 shot (508.7s) mô phỏng `why_knights_could_actually`. Xác nhận `assign_visuals` gán toàn bộ 180 shot, preflight 100% PASS, fast check render 0 lỗi. |
| **G6** | **Negative: Missing Asset & Template** | Kiểm tra từ chối an toàn: shot có template không xác định hoặc file ảnh thiếu bị validator chặn đứng với exit code != 0. |
| **G7** | **Negative: Corrupt Input & Overlap** | JSON hỏng cú pháp, thời gian âm/chồng lấn shot, hoặc template không thuộc pack bị chặn ngay từ bước preflight. |
| **G8** | **Preserve Custom Edits** | Bảo toàn các chỉnh sửa thủ công của người dùng (`visual_source: "manual"`, custom args) khi chạy lại `assign_visuals`. Tự động tạo bản backup có timestamp. |
| **G9** | **Stale / Artifact Invalidation** | Khi kịch bản thay đổi, intermediate trong `build/` và proof bị vô hiệu hóa; file video hoàn thiện trong `out/*.mp4` được bảo vệ an toàn (chuyển trạng thái `OUTPUT_STALE`). |
| **G10** | **Failure Injection & Resilience** | Giả lập worker/render bị hủy giữa chừng; đảm bảo hệ thống báo lỗi trung thực (exit code != 0), dọn dẹp file `.partial.mp4`, không tạo file MP4 giả. |
| **G11** | **Media Quality & Visual Inspection** | Trích xuất khung hình và phân tích pixel bằng numpy: xác nhận 0 pixel đỏ placeholder `#f04444`, 0 màn hình đen `#1a0f14`, độ đa dạng màu > 500 màu. |
| **G12** | **Legacy Samples & HTTP Streaming** | Kiểm tra hồi quy các mẫu có sẵn: `squire-mau` (24 shots PASS), `selfimprove-mau` (30 shots PASS). Kiểm tra phát trực tuyến video HTTP 206 Partial Content (Range header). |
| **G13** | **Concurrency & Workspace Isolation** | Chạy nhiều dự án render song song; xác nhận không xung đột tài nguyên, không ghi đè dữ liệu chéo giữa các workspace. |
| **G14** | **Historical Contrast Comparison** | So sánh đối chiếu trực tiếp: Luồng cũ (draft thiếu visual -> 180 shot THIEU SHOT) vs Luồng mới (tự động gán visual chuẩn xác -> render sạch 100%). |
| **G15** | **Headless CI & CLI Exit Codes** | Kiểm tra hoạt động không cần màn hình đồ họa (headless), xuất định dạng JSON chuẩn qua `--json` cho CI/CD. |
| **G16** | **Performance & Resource Audit** | Đo đạc thời gian thực thi (Fast Check ~10s vs Full Check), kiểm soát mức sử dụng RAM và dung lượng ổ cứng. |

---

## Hướng dẫn chạy kiểm thử (How to Run)

### 1. Kiểm tra an toàn tài nguyên (Resource Guard)
```bash
python3 scripts/resource_guard.py
```

### 2. Chạy toàn bộ ma trận hồi quy E2E (G0 - G16)
```bash
python3 scripts/run_e2e_regression.py
```

### 3. Kiểm tra bằng chứng đầu ra (Evidence)
Kết quả kiểm thử được tự động ghi nhận tại:
- `tests/evidence/latest-summary.json`: Báo cáo chi tiết dạng JSON có thể tích hợp CI.
- `tests/evidence/latest-report.md`: Báo cáo nghiệm thu Markdown trực quan.
- `tests/evidence/proof_*.jpg`: Các khung hình chụp thực tế từ các video đã render.


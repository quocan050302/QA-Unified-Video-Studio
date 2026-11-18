# FAILURE LEDGER — KH-03.0.R2 (`20261117_094557Z_0fd8`)

Ghi nhận trung thực mọi lỗi kỹ thuật thực tế phát hiện trong quá trình xây dựng & kiểm thử KH-03.0.R2 và cách khắc phục tận gốc (không nới lỏng assertion):

1. **FFmpeg 9.0.2 deprecated flag (`-vsync 0`)**
   - **Triệu chứng**: `tools/kh03_perceptual_qa.py` khi hiệu chỉnh trên MP4 R1 báo lỗi exit code từ FFmpeg 9.0.2.
   - **Nguyên nhân**: FFmpeg 9 bỏ flag `-vsync 0`.
   - **Cách sửa**: Đổi sang `-fps_mode passthrough`. Hiệu chỉnh R1 PASS (`105` frames decoded).

2. **Stale Perceptual QA frame cache across distinct MP4s**
   - **Triệu chứng**: `test_perceptual_qa_catches_zoom_spam_duplicates_and_subtitle_only_motion` thất bại ở case thứ 3 (`pos_varied.mp4` nhận `stage_mad = 0.0` từ ảnh PNG giải mã của `neg_dup.mp4` cùng thư mục `tmp_path`).
   - **Nguyên nhân**: `sample_rendered_frames` ghi chung vào `build/perceptual_frames/f_0000.png` không gắn chữ ký MP4.
   - **Cách sửa**: Gắn hash `(path|size|mtime_ns)[:12]` vào thư mục cache từng MP4 + truyền cache riêng per `build_perceptual_review_packet`.

3. **Unescaped apostrophe in `thumb.js` & missing companion metadata JSONs**
   - **Triệu chứng**: `render.mjs --check` báo `SyntaxError` trên `'WOULDN'T STOP!'` và cảnh báo `404 Required` cho 4 file `roman_master_style_ref.json`, `environment_bible.json`, `props.json`, `storyboard.json`.
   - **Cách sửa**: Quote bằng `json.dumps()` trong `_generate_r2_thumb_js` và xuất đủ 4 JSON khi build project R2. Kết quả `render.mjs --check` sạch `0` lỗi, `0` 404.

4. **Pronoun/clause splitting & TTS stretch budget on Story A/B/C**
   - **Triệu chứng**: Bản nháp đầu tiên của Story A dài `44.44s` vượt ngưỡng `1.15x`; tách dấu `,` với từ ngắn gây rơi liên từ `"and"`; `"kept walking"` khớp trùng giữa `actor.walk_stride` và `actor.deadpan_walk_unaffected`.
   - **Cách sửa**: Siết `split_line_clauses_v2` chỉ tách khi mọi vế `>= 4` từ có động từ hữu hạn; gán `"kept walking"` duy nhất cho `actor.deadpan_walk_unaffected` (`requires loaf_on_helmet`); tinh gọn lời thoại đạt `30.578s` (`global_tempo_scale = 1.0606x`).

5. **Visual composition defects spotted on contact sheets**
   - **Triệu chứng**: Crowd đè sau Baker Lucius ở `SH02`, bóng bầu dục nâu che vùng phụ đề `SH06`, xe sát lò ở `SH10`, mép ghế chạm chân nhân vật ở `forum_courtyard SH04`.
   - **Cách sửa**: Chỉnh `market_env.js` và `action_registry.js`, render lại toàn bộ và duyệt lại qua `contact_sheet_all_shots.jpg`.

6. **Validation harness issues (`G02` `window.E`, `G14` `QA_RUN_ID` & stale `v10_*` folder, overnight task stall)**
   - **Triệu chứng**: `G02` đọc `window.E` (`undefined` do ES module); `G14` lỗi `ValueError` vì `QA_RUN_ID` chứa chữ hoa `'Z'`, lần sau lỗi `K2 NO_RENDERABLE_CHANGE` do thư mục `.test-runs/v10_r2*` còn sót; tác vụ `task-1344` treo qua đêm.
   - **Cách sửa**: Sửa `G02` đọc `/proj/story/shot_plan.json` qua fetch + network check; dùng `run_tag` chữ thường ngẫu nhiên và dọn sạch `v10_r2*`; rút clip `real20` xuống `30` frame/clip (`1.25s`) & bật log `flush=True`. Kết quả `task-1370` đạt `17/17` technical gates `PASS` (`FLOW_READY 81/81` ở `G14`).

- **Fixture vắng mặt trung thực**: `company_180_real_videos` ghi rõ `NOT_RUN_MISSING_FIXTURE` (không tồn tại trong workspace).

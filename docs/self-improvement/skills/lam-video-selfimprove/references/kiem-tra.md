# Xem trước, xuất bản cuối, kiểm tra

## Xuất
- **Quét lỗi nhanh:** `node render.mjs --project projects/<slug> --check --scale 0.25` — liệt kê cảnh lỗi.
- **Ảnh tổng hợp:** `node render.mjs --project projects/<slug> --sheet --scale 0.5 --at 0.75` — 1 khung mỗi cảnh, lấy ở 75% thời lượng cảnh để chữ đã hiện đủ. Chỉ vẽ vài cảnh: `--ids b07,b08`. Đổi điểm lấy khung: `--at 0.3`.
- **Xem trước có tiếng:** chạy `python tools/mix.py --project projects/<slug> --no-video` trước, rồi `node render.mjs --project projects/<slug> --from 0 --to 30 --scale 0.5` → `build/preview.mp4`.
- **Bản cuối:**
  ```bash
  nohup node render.mjs --project projects/<slug> > projects/<slug>/build/render.log 2>&1 &
  ```
- **Trộn âm:** `python tools/mix.py --project projects/<slug>` → `out/<tiêu đề>.mp4`.
- **Tốc độ tham khảo:** bộ `dem` vẽ bằng CPU (render.mjs tự chọn khi dự án có `pack`): khoảng 20 khung/giây ở 1080p trên máy cloud 2 nhân → phim 3 phút mất 3–5 phút. 720p nhanh gấp đôi. Máy nhiều nhân: thêm `--workers 4`.

## Danh sách kiểm tra (mỗi ảnh tổng hợp)
- [ ] Không có khung "THIEU MAU", "THIEU SHOT" hay chữ đỏ "LOI".
- [ ] Hình khớp mô tả cảnh trong file 01. Chữ đúng nguyên văn file 01.
- [ ] Chữ kể chuyện không đè lên mặt nhân vật, đọc rõ trên nền (không nằm trên vùng sáng chói).
- [ ] Chữ cám dỗ nằm cạnh bóng đen, không đè lên nhân vật chính.
- [ ] Bộ đếm đúng số theo từng cảnh, cú sụp đúng cảnh, sau cú sụp các cảnh sau giữ số mới.
- [ ] Nhân vật chính cùng preset (hoặc đổi đúng chỗ đã ghi trong `bible.md`). Bóng đen dùng đúng màu nhấn.
- [ ] Mỗi cảnh có chuyển động (máy đẩy, nhân vật đi, chữ gõ, bộ đếm chạy). Không cảnh nào đứng im quá 6 giây.
- [ ] Không quá 3 cảnh liền cùng bố cục, trừ chuỗi lặp cố ý (phòng ngủ qua các ngày).
- [ ] 9:16: nhân vật và chữ trong khoảng giữa, không sát mép.
- [ ] Âm thanh: có nhạc, có SFX khi bóng đen nói và ở cú sụp, có 1 khoảnh khắc im lặng, tổng khoảng −14 LUFS.
- [ ] Thumbnail: chữ 1–4 từ, không che mặt, không cắt mép; ảnh AI đúng nhân vật mẫu.

## Lỗi thường gặp
- **"THIEU MAU xxx":** `tpl` gõ sai tên. Xem `mau-canh.md`.
- **Nhân vật đứng sai chỗ / lơ lửng:** `x` dùng mốc không có trong bối cảnh (vd `bed.sit` ở `city`). Dùng số 0..1.
- **Chữ hiện font mặc định:** thiếu gói font. Chạy `npm install` trong `h2-2d-studio` (cần `@fontsource/comic-neue`, `caveat`, `luckiest-guy`).
- **"Khong nap duoc pack dem":** thiếu `packs/dem`. Chép lại kit.
- **"Khong khoi dong duoc player":** `shots.json` hoặc `config.json` sai cú pháp JSON.
- **Không có tiếng / mix báo "khong co nhac 'sad'":** chưa chạy `python audio/build_audio.py` sau khi cài bộ `dem`.
- **Video dài/ngắn sai:** `story.duration` phải bằng `end` của cảnh cuối; `phim.py --force` tạo lại nếu chưa lên hình.
- **Xuất rất chậm (vài giây mỗi khung):** đang chạy GPU giả lập. Thêm `--gl auto` vào lệnh render.
- **Windows:** đặt đường dẫn có dấu cách trong ngoặc kép. Dùng `python` hoặc `py -3`.

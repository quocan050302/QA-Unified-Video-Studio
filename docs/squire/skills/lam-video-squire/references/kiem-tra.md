# Xem trước, xuất bản cuối, kiểm tra

## Xuất
- **Quét lỗi nhanh:** `node render.mjs --project projects/<slug> --check --scale 0.25`. Lệnh liệt kê cảnh lỗi và ảnh AI còn thiếu.
- **Ảnh tổng hợp:** `node render.mjs --project projects/<slug> --sheet --scale 0.4 --at 0.8`. Lệnh vẽ 1 khung mỗi cảnh, lấy ở 80% thời lượng cảnh để nhãn đã hiện đủ.
  - Chỉ vẽ một số cảnh: thêm `--ids s010,s011`.
- **Xem trước:** `node render.mjs --project projects/<slug> --from 0 --to 30 --scale 0.5`, ra file `build/preview.mp4` (có voice).
- **Bản cuối:** chạy nền rồi đọc log định kỳ:
  ```bash
  nohup node render.mjs --project projects/<slug> > projects/<slug>/build/render.log 2>&1 &
  ```
  Log in số khung mỗi giây và thời gian còn lại.
- **Trộn âm:** `python tools/mix.py --project projects/<slug>`, ra file `out/<tiêu đề>.mp4`.
- **Tốc độ tham khảo:**
  - Máy cloud 2 nhân, 1080p: khoảng 6–8 khung/giây, tức 3–5 phút xuất cho 1 phút video.
  - Cảnh bản đồ được lưu đệm thành ảnh nên không chậm hơn cảnh khác.
  - 720p nhanh hơn khoảng 2 lần.
  - Máy bàn nhiều nhân: thêm `--workers 4` để nhanh hơn nữa.

## Danh sách kiểm tra (mỗi ảnh tổng hợp)
- [ ] Không có khung "THIẾU MẪU", "THIẾU SHOT", "THIẾU ẢNH" hay chữ đỏ "LOI".
- [ ] Hình khớp câu đọc. Nhãn hiện đúng chữ được đọc.
- [ ] Chữ tiếng Việt đủ dấu, không tràn mép (cách mép ít nhất 6%), không đè lên mặt nhân vật.
- [ ] Mỗi cảnh 1 ý chính, tối đa 3 nhãn.
- [ ] Màu nhân vật đúng như `story/bible.md`. Người dẫn chuyện luôn áo xanh nhạt.
- [ ] Ảnh AI đúng phong cách (viền đen, phẳng, pastel), không có chữ hay logo, không lệch tông giữa các ảnh.
- [ ] Bản đồ đúng vùng, ghim đúng chỗ, có Hoàng Sa và Trường Sa (Việt Nam) khi thấy Biển Đông.
- [ ] Đa dạng: không quá 3 cảnh liền cùng mẫu, trừ chuỗi liệt kê cố ý.
- [ ] Không cảnh nào đứng yên quá 8 giây mà không có gì mới hiện ra.
- [ ] 9:16: chủ thể ở giữa, không có gì quan trọng nằm dưới phụ đề.
- [ ] Âm thanh: lời rõ, nhạc nhỏ, SFX thưa, tổng khoảng −14 LUFS.

## Lỗi thường gặp
- **"THIẾU MẪU xxx":** `tpl` gõ sai tên. Xem danh sách mẫu trong `mau-canh.md`.
- **"THIẾU ẢNH A0xx":** chưa có file trong `projects/<slug>/anh/`. Chạy lại `tools/import_anh.py --dir` hoặc chép ảnh vào, tên file là mã ảnh.
- **Nhãn không hiện:** cụm chữ trong `at` không khớp lời đọc. Mở `timeline/words.json` xem chữ thật, hoặc ghi số giây.
- **Chữ hiện font mặc định, mất dấu:** thiếu gói font. Chạy `npm install` trong `h2-2d-studio`.
- **"Khong nap duoc pack squire":** thiếu `packs/squire`, `packs/doodle` (bản đồ dùng chung) hoặc gói `world-atlas`, `topojson-client`. Chép lại kit rồi `npm install`.
- **"Khong khoi dong duoc player":** `shots.json` hoặc `config.json` sai cú pháp JSON.
- **Video dài hoặc ngắn hơn voice:** `story.duration` phải bằng `end` của cảnh cuối.
- **Voice lệch câu:** xem `timeline/transcript.txt`. Chế độ mỗi đoạn một file: số file voice phải bằng số đoạn trong file 02, tên file có số thứ tự. Nếu tool tạo nhiều file hơn số đoạn, thì Auto Split còn để các dấu `. , ; : ! ?`: chỉ để lại `|` rồi tạo lại. Chế độ file gộp: câu nào lệch thì sửa `start` trong `timeline/lines.json`, hoặc thêm `--whisper small --lang vi`.
- **Windows:** đặt đường dẫn có dấu cách trong ngoặc kép. Dùng `python` hoặc `py -3` thay cho `python3`.

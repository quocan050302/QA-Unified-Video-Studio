# H2 Self-Improvement Studio

Làm **phim hoạt hình ngắn không lời đọc** (2–4 phút, tiếng Anh) kiểu các kênh "An Animated Short Film" về kỷ luật, cám dỗ, nghiện điện thoại, trì hoãn, làm lại từ đầu.

- **Video vẽ 100% bằng code**: nền tối nét mảnh sáng, nhân vật đầu tròn màu kem, bóng đen cám dỗ phát sáng, chữ kể chuyện trắng, chữ cám dỗ viết tay, bộ đếm `DAY N`, điện thoại (feed, chat, email), đồng hồ, lịch, sổ tay, thẻ kết, màn xin đăng ký. Không cần voice, không cần ảnh AI trong video.
- **Thumbnail**: 1 ảnh AI theo prompt khoá nhân vật + chữ tiêu đề do code vẽ.
- **Âm thanh**: nhạc piano / drone / nhạc lên và SFX tự tạo (không bản quyền), chuẩn −14 LUFS.

## Hai lệnh
- **/kich-ban-selfimprove `<đề tài>`**: viết `01-PHIM` (kịch bản cảnh: thời lượng, cảnh, bộ đếm, nhạc, SFX, chữ), `02-PACKAGE` (10 tiêu đề, 3 phương án thumbnail, mô tả, tag), `03-THUMB-PROMPT` (prompt ảnh AI). Gọi không ghi gì để được gợi ý 10 đề tài (có quét kênh đối thủ). Làm được `PART 2`, `X VS Y`.
- **/lam-video-selfimprove**: từ file `01-PHIM`, dựng phim hoàn chỉnh + thumbnail.

## Quy trình
1. `/kich-ban-selfimprove <đề tài>` → nhận file 01–03.
2. (Lần đầu) tạo ảnh nhân vật mẫu `T00` trong Google Flow; mỗi video tạo `T01` có gắn T00 làm ảnh tham chiếu.
3. `/lam-video-selfimprove` + file `01-PHIM` (+ `T01.png`). Claude cài studio (lần đầu), dựng nháp, cho bạn duyệt ảnh tổng hợp và bản xem trước 30 giây, rồi xuất video.

## Cài đặt lần đầu (Claude tự làm)
ffmpeg, Node.js + gói (bộ vẽ, font Comic Neue / Caveat / Luckiest Guy), Chromium chạy ngầm, Python numpy/scipy/soundfile, rồi tạo thư viện SFX và nhạc. Khoảng 400 MB. Không cần API key. Dùng chung thư mục `h2-2d-studio/` với các gói H2 khác.

## Tốc độ
Bộ vẽ chạy bằng CPU: phim 3 phút 1080p mất khoảng 3–5 phút trên máy cloud 2 nhân.

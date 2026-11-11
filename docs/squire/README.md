# H2 Squire Studio

**Dạng ngách:** 2D thuần · render bằng CPU (không cần card) · không cần ảnh AI (kể cả thumbnail) · làm được cả video dài 16:9 và Short 9:16.

Làm video YouTube **lịch sử quân sự hoạt hình bằng tiếng Anh**: hiệp sĩ, La Mã, samurai, Viking, thế chiến. Phong cách hoạt hình vector: nhân vật đầu tròn trắng, viền nâu đen dày, giáp và trang phục đúng thời đại, ngựa, đội hình hàng trăm lính, nền mờ sâu kiểu máy ảnh, mưa, mưa tên, sơ đồ khối quân nhìn từ trên, bản đồ giấy da.

Tất cả do code tự vẽ: nhân vật (hơn 50 bộ trang phục có sẵn), ngựa, đội hình, nền (đồng cỏ, ruộng bùn, đồng bụi La Mã, lâu đài, xưởng, lều, nhà thờ, chiến hào, biển, thành phố), sơ đồ, bản đồ, bảng phấn, màn soi, chữ, thumbnail. Nhạc và SFX cũng tự tạo bằng code (ngựa hí, vó ngựa, đấu kiếm, va khiên, mưa tên, kèn trận, trống, sấm, súng...), không bản quyền.

## Hai lệnh
- **/kich-ban-squire:** luôn hỏi làm **Video dài** (9–11 phút, giọng "you" nhập vai người lính) hay **Short** (60–75 giây, chuyện một con người). Xuất:
  - `01-SCRIPT`: bản đọc liền mạch.
  - `02-VOICE`: chữ trơn, đoạn ngăn bằng `|` để tool voice tự tách mỗi đoạn 1 file.
  - `03-HINH`: kế hoạch hình (chặng, nhân vật, màu phe, sơ đồ, nhạc, SFX, nguồn).
  - `05-TIEU-DE`: 10 tiêu đề, 3 phương án thumbnail (có sẵn tham số vẽ), mô tả, tag.

  Gọi lệnh mà không ghi gì thì được gợi ý 10 đề tài (có quét kênh đối thủ).
- **/lam-video-squire:** từ voice, dựng video hoàn chỉnh: hình, nhạc, SFX, phụ đề (Short), thumbnail (video dài). Âm lượng chuẩn −14 LUFS. Video dài 16:9 không phụ đề; Short 9:16 phụ đề 1–3 chữ IN HOA trắng.

## Quy trình
1. Gõ `/kich-ban-squire <đề tài>`, chọn Video dài hoặc Short, nhận các file 01, 02, 03, 05.
2. Đưa `02-VOICE-<slug>.txt` vào tool tạo voice (1 giọng nam trầm tiếng Anh), bật **Auto Split** chỉ để ký tự `|`, xuất mỗi đoạn 1 file (`1.mp3`, `2.mp3`...). Hoặc đọc gộp thành 1 file.
3. Gõ `/lam-video-squire`, chọn đúng mục. Claude cài studio (lần đầu), ghép voice, lên cảnh, cho bạn duyệt ảnh tổng hợp và bản xem trước 30 giây, rồi xuất video + thumbnail.

## Cài đặt lần đầu (Claude tự làm)
Claude tự cài ffmpeg, Node.js và các gói (bộ vẽ, font chữ, dữ liệu bản đồ), Chromium chạy ngầm, Python numpy/scipy/soundfile, rồi tạo thư viện SFX và nhạc. Tổng khoảng 400 MB. Không cần API key.

Nếu đã cài plugin H2 khác thì các plugin dùng chung thư mục `h2-2d-studio`.

## Tốc độ
- Máy cloud 2 nhân: khoảng 4 khung/giây ở 1080p → video 9,5 phút khoảng 45–60 phút; Short 70 giây khoảng 5–8 phút. 720p nhanh gấp đôi.
- Máy tính nhiều nhân nhanh hơn vài lần.

**Dựng bằng card đồ hoạ (Windows):** khi dựng, Claude hỏi bạn muốn dựng bản cuối trên máy của bạn hay trên cloud. Chọn máy thì Claude chép vài file vào thư mục dự án, bạn bấm đúp `DUNG-VIDEO-....bat` là máy tự dựng bằng Edge và card đồ hoạ.

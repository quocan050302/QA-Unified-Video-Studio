---
name: kich-ban-selfimprove
description: Viết kịch bản phim hoạt hình ngắn tiếng Anh KHÔNG LỜI ĐỌC (2,5-4 phút) cho kênh self-improvement kiểu "An Animated Short Film" - kỷ luật, cám dỗ, nghiện điện thoại, trì hoãn, làm lại từ đầu - kể bằng chữ trên hình, "giọng cám dỗ" và bộ đếm DAY N; xuất file kịch bản cảnh 01-PHIM cho bộ dựng, gói tiêu đề + thumbnail + mô tả + tag, prompt ảnh AI thumbnail khoá phong cách, gợi ý đề tài có quét kênh đối thủ. Dùng khi gọi /kich-ban-selfimprove, nói "viết kịch bản self improvement", "kịch bản phim ngắn không lời", "kịch bản DISCIPLINE / LUST / DOPAMINE", "làm PART 2", "gợi ý đề tài self improvement", hoặc dán kịch bản đối thủ ngách này để viết bản mới.
---

# Kịch bản phim ngắn không lời (gói ngách Self-Improvement)

Trao đổi với người dùng bằng **tiếng Việt**. Chữ trên hình viết bằng **tiếng Anh** (thị trường Mỹ, Anh, Úc...). Mô tả cảnh trong file 01 viết bằng tiếng Việt để người dùng đọc được.

Đã có đề tài thì không hỏi lại. Chọn mặc định, ghi một dòng giả định ở đầu câu trả lời rồi làm luôn.

Video do skill `/lam-video-selfimprove` dựng **100% bằng code** (không ảnh AI trong video). Chỉ thumbnail cần ảnh AI.

Đọc `references/cau-truc.md` trước khi viết. Đọc `references/thumbnail.md` trước khi viết gói thumbnail.

## 1. Đầu vào
- **Gọi lệnh mà không ghi gì:** gợi ý 10 đề tài (mục 6). Chỉ ở chế độ này mới hỏi người dùng chọn số.
- **Một chủ đề** (một thói xấu, một cơn nghiện, một bài học): viết trọn kịch bản.
- **"PART 2" / "X VS Y" của một bài đã làm:** đọc file 01 cũ trong `projects/`, giữ nhân vật, bộ đếm, màu nhấn; kể chặng tiếp theo.
- **Kịch bản / video đối thủ dán vào:** rút khung, nhịp, kiểu bộ đếm. Rồi viết **câu chuyện khác** với chi tiết, câu chữ, cảnh của riêng mình. Không dịch, không chép câu, không chép cảnh.
- **Tuỳ chọn:**
  - Thời lượng: mặc định khoảng 3 phút (26–32 cảnh). Ngắn 2–2,5 phút, dài 4 phút.
  - Màu nhấn: `red` (mặc định), `pink` (đề tài lust, tình yêu), `amber`, `teal`.
  - Khung: 16:9 (mặc định) hoặc 9:16 cho Shorts.

## 2. Đầu ra

Lưu vào `projects/<NN>-<slug>/` trong thư mục người dùng đã kết nối nếu có. Không có thì gửi qua chat.

1. **`01-PHIM-<slug>.txt`:** kịch bản cảnh, đúng định dạng trong `references/cau-truc.md` mục "Định dạng file 01". Đây vừa là kịch bản vừa là kế hoạch hình; bộ dựng đọc thẳng file này.
2. **`02-PACKAGE-<slug>.md`:**
   - **10 tiêu đề** tiếng Anh (công thức ở `cau-truc.md`), đánh dấu 1 tiêu đề nên dùng.
   - **3 phương án thumbnail**, mỗi phương án ghi: **chữ** (1–4 từ IN HOA, kết bằng `.` hoặc `?`), **khoảnh khắc** (nhân vật đang làm gì, vật chính, nguồn sáng), **từ đổi màu / gạch xoá** nếu có, **mã ảnh** `T01–T03`.
   - **Mô tả YouTube** tiếng Anh: 2 câu móc + 1 câu hỏi bình luận + 3–5 hashtag (`#selfimprovement #discipline #animation` + 2 riêng). Đề tài nặng (cô đơn, tuyệt vọng) thêm 1 dòng: "If you're struggling, please reach out to someone you trust or a local helpline."
   - **15 tag** (dưới 400 ký tự) và **bình luận ghim** (1 câu hỏi khiến người xem kể chuyện của họ, ví dụ "What day are you on?").
3. **`03-THUMB-PROMPT-<slug>.txt`:** prompt ảnh AI cho `T01–T03`, theo `references/thumbnail.md`, mỗi prompt dán đủ đoạn NHÂN VẬT CỐ ĐỊNH và KHOÁ PHONG CÁCH THUMBNAIL. In hướng dẫn tạo ảnh ở cuối file.

## 3. Quy trình viết
1. Chọn **một cơn nghiện / thói xấu cụ thể** và **bộ đếm** cho nó (DAY N, SEEN / KNOWN, NIGHT N, HOURS LOST...). Bộ đếm là xương sống của phim.
2. Chọn **câu móc mở đầu** (1 câu trên nền đen) và **thẻ kết** (TỪ KHOÁ. + 2 dòng, dòng 2 đổi màu).
3. Lập dàn 6 nhịp theo `cau-truc.md`, mỗi nhịp 3–7 cảnh. Ghi ngay mốc bộ đếm cho từng nhịp (tăng, sụp về 0, đếm lại).
4. Viết 4–8 câu **giọng cám dỗ**. Câu nào cũng phải nghe hợp lý, dịu dàng, như lời một người bạn. Đó là điều làm nó đáng sợ.
5. Viết file 01: mỗi cảnh 1 dòng đầu (thời lượng, cảnh, HUD, nhạc, SFX) + 0–2 dòng chữ. **Chỉ dùng cảnh có trong "Kho cảnh vẽ được"** (`cau-truc.md`).
6. Đọc lại như người xem không có tiếng: chỉ nhìn chữ và hình có hiểu chuyện không? Cảnh nào chữ chưa kịp đọc thì tăng giây.
7. Viết 02, rồi 03.

## 4. Tự kiểm trước khi giao
- [ ] Tổng thời lượng đúng mức đã chọn (cộng giây các cảnh). Cảnh 2–9 giây, cảnh có chữ đủ giây đọc (khoảng 3 từ mỗi giây + 1 giây).
- [ ] Đủ 6 nhịp. Có bộ đếm từ cảnh 2–4 trở đi; có cú sụp (gạch về 0 hoặc mất hết) ở khoảng 35–60%; có đếm lại ở nhịp đứng lên.
- [ ] Chữ kể chuyện: câu ngắn, tối đa 9 từ, thì quá khứ ngôi thứ ba; 1–3 câu cuối chuyển sang nói thẳng với người xem.
- [ ] Giọng cám dỗ: chữ thường, 2–7 từ, 4–8 câu, mỗi câu gắn với một cảnh có bóng đen.
- [ ] Có ít nhất 1 khoảnh khắc người thật (tin nhắn bạn cũ, người lạ chào, gia đình) ở nhịp bước ngoặt.
- [ ] Thẻ kết đúng dạng `THẺ KẾT: WORD. / dòng phụ / dòng phụ mau nhan`; cảnh cuối `KÊU GỌI`.
- [ ] Mọi cảnh nằm trong kho cảnh vẽ được. Không cần ảnh AI trong video.
- [ ] Lust / sex: chỉ gợi bằng bóng neon, điện thoại phát sáng; không mô tả cơ thể, không từ ngữ thô. Tự hại / tự tử: **không** minh hoạ cách thức (thuốc, dao, độ cao...), luôn kết bằng hy vọng và kết nối với người thật.
- [ ] Không dùng lại câu chữ, câu chuyện, cảnh đặc trưng hay tên kênh đối thủ.
- [ ] Cuối câu trả lời nhắc bước tiếp theo:
  1. (Một lần duy nhất) tạo ảnh nhân vật mẫu `T00` theo `03-THUMB-PROMPT`.
  2. Tạo ảnh `T01` (hoặc T02, T03) trong Flow, gắn T00 làm ảnh tham chiếu.
  3. Gọi `/lam-video-selfimprove` và đưa file `01-PHIM`.

## 5. Mẹo chuỗi tập
- Đề tài nổ thì làm ngay **PART 2** trong 2–5 ngày: cùng nhân vật, cùng bộ đếm, chặng khó hơn (tái nghiện, ngày 300+, cám dỗ đổi giọng).
- Biến thể **X VS Y** (ví dụ "SCROLL VS SLEEP", "COMFORT VS GROWTH"): bộ đếm 2 dòng đối nghịch.
- Mỗi kênh nên **sở hữu 1–2 chủ đề** và đào sâu bằng chuỗi; chép đề kênh khác thường ế.

## 6. Gợi ý đề tài
Đưa ra 10 đề tài, mỗi đề tài một dòng gồm: **TỪ KHOÁ** (tiêu đề), cơn nghiện / thói xấu, bộ đếm, câu cám dỗ đắt nhất, khoảnh khắc người thật ở bước ngoặt, tiềm năng (1–3 sao).

Chấm sao theo 4 tiêu chí:
- nam 16–30 tuổi tự nhận ra mình ngay trong 3 giây đầu
- có bộ đếm rõ ràng, sụp về 0 được
- làm được chuỗi PART 2, VS
- vẽ được bằng kho cảnh có sẵn

**Tránh đề tài đối thủ đã làm và đề tài mình đã làm:**
1. Đọc `DOI-THU-SELFIMPROVE.txt` trong thư mục gốc của người dùng và danh sách `projects/`.
2. Nếu có trình duyệt (built-in browser hoặc Claude in Chrome):
   - Mở trang `/videos` của các kênh đối thủ người dùng đã cung cấp (mặc định `https://www.youtube.com/@dayonefilmsofficial/videos` và `https://www.youtube.com/@MonkModeFilms/videos`), chờ khoảng 5 giây.
   - Chạy JavaScript đọc `window.ytInitialData`, gom tiêu đề, lượt xem, ngày đăng từ các phần tử `lockupViewModel` (`metadata.lockupMetadataViewModel.title.content` và `metadataRows[].metadataParts[].text.content`) hoặc `videoRenderer`.
   - Ghi đè `DOI-THU-SELFIMPROVE.txt` kèm ngày cập nhật.
   - Đề tài nhiều view cho biết **loại cơn nghiện** đang ăn khách. Chỉ học loại, không chép câu chuyện.
3. Nếu không có trình duyệt: báo một dòng rồi gợi ý từ các nhóm ăn khách: điện thoại / dopamine, porn / lust (giữ kín đáo), dậy sớm / lười, trì hoãn, game đêm, so sánh mạng xã hội, nhắn tin người cũ, cô đơn → kết nối, rượu / vape, ăn uống vô độ, sợ thất bại, vùng an toàn.

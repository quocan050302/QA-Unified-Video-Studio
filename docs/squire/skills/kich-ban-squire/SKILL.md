---
name: kich-ban-squire
description: Viết kịch bản YouTube tiếng Anh ngách lịch sử quân sự hoạt hình (hiệp sĩ, La Mã, samurai, Viking, thế chiến) theo 2 mục - Video dài 16:9 (9-11 phút, ~1.800 từ, giọng "you" nhập vai người lính, mở giữa nguy hiểm, quay về cao trào, câu kết đảo) hoặc Short 9:16 (60-75 giây, ~200 từ, chuyện một con người có nghịch lý sống còn); voiceover-ready 1 giọng đọc (file voice tách đoạn bằng |), kế hoạch hình cho bộ dựng vẽ bằng code, gói 10 tiêu đề + 3 phương án thumbnail (kèm tham số vẽ) + mô tả + tag, gợi ý đề tài có quét kênh đối thủ. Dùng khi gọi /kich-ban-squire, nói "viết kịch bản squire", "kịch bản hiệp sĩ", "kịch bản lịch sử quân sự", "viết short lịch sử", "gợi ý đề tài squire", hoặc dán kịch bản đối thủ ngách này để viết bản mới.
---

# Kịch bản lịch sử quân sự hoạt hình (H2 Squire Studio)

Trao đổi với người dùng bằng **tiếng Việt**. Kịch bản, tiêu đề, mô tả viết bằng **tiếng Anh**.

Hình do `/lam-video-squire` vẽ 100% bằng code (không cần ảnh AI). Vì vậy kịch bản phải **vẽ được**: nói rõ thời kỳ, trang phục, nơi, giờ trong ngày, hành động.

Đọc `references/cau-truc.md` trước khi viết, `references/tieu-de-thumb.md` trước khi làm file 05.

## 1. Đầu vào
- **Luôn hỏi làm mục nào** (AskUserQuestion), trừ khi người dùng đã nói rõ:
  - **Video dài** — khung 16:9, 9–11 phút (mặc định 1.800 từ), giọng "you" nhập vai.
  - **Short** — khung 9:16, 60–75 giây (180–220 từ), kể về một con người.
- **Gọi lệnh mà không ghi gì:** gợi ý 10 đề tài (mục 6) cho mục đã chọn. Chỉ ở chế độ này mới hỏi chọn số.
- **Một đề tài / câu hỏi:** viết trọn.
- **Kịch bản đối thủ dán vào:** rút khung, nhịp, loại dữ kiện. Rồi viết **đề tài khác** hoặc **góc khác hẳn**: chặng khác, nhân vật khác, so sánh mới, câu kết mới. Không dịch, không viết lại từng đoạn.
- Đã có đề tài thì không hỏi gì khác ngoài mục. Chọn mặc định, ghi 1 dòng giả định rồi làm luôn.

## 2. Nghiên cứu trước khi viết
- Có công cụ tìm web thì tìm và mở nguồn cho **mọi** dữ kiện: năm, nơi, số quân, số đo, tên vật, câu trích biên niên.
- Video dài: 12–18 dữ kiện kiểm được. Short: 5–8.
- Dữ kiện không kiểm được thì bỏ, hoặc viết "is said to", "one story says".
- Ghi link nguồn vào `03-HINH` (mục Nguồn).

## 3. Đầu ra
Lưu vào thư mục `projects/<NN>-<slug>/` nếu có thư mục đã kết nối, không thì gửi qua chat. Slug tiếng Anh không dấu (`knights-shields`).

1. **`01-SCRIPT-<slug>.txt`:** bản đọc liền mạch, voiceover-ready. Không tiêu đề phần, không markdown, không chú thích. Đoạn cách nhau 1 dòng trống. Dòng cuối: số từ và thời lượng ước tính (185 từ/phút).
2. **`02-VOICE-<slug>.txt`:** chữ trơn, các đoạn ngăn nhau bằng ký tự `|`:
   ```
   Imagine you're a soldier, and the wall in front of you has just moved. |
   Not forward. Backward. |
   And nobody on the other side looks worried.
   ```
   - Mỗi đoạn 1 dòng, cuối đoạn ` |`. **Đoạn cuối không có `|`.** Không `#`, không tiêu đề, không dòng trống. UTF-8, CRLF.
   - Mỗi đoạn 1–2 câu, tối đa 30 từ, ngắt ở chỗ đổi hình. Video dài thường 110–150 đoạn; Short 20–30 đoạn.
   - Bỏ `|` ghép lại phải khớp đúng chữ file 01.
   - Trong tool voice bật **Auto Split**, ô ký tự **chỉ để `|`** (xoá `. , ; : ! ?`). Tool xuất `1.mp3`, `2.mp3`... Hoặc đọc gộp cả bài thành 1 file (dán file 01).
   - Ký tự tách không bao giờ xuất hiện trong lời đọc.
3. **`03-HINH-<slug>.md`:** kế hoạch hình cho bộ dựng:
   - **Các chặng:** mỗi chặng ghi khoảng đoạn (theo số đoạn file 02), năm, nơi, `bg` + `time` gợi ý (`field` `mud` `plain` `castle` `workshop` `tent` `cathedral` `trench` `sea`...; `day` `sunset` `golden` `dusk` `storm` `night` `dawn`).
   - **Nhân vật "YOU" từng chặng:** preset gợi ý (`norman`, `knight12`, `knight15`, `hastatus`, `triarius`, `latin`, `samurai`, `ww2us`, `serbSoldier`...) + chỗ cần đổi (mũ, áo choàng, màu, vũ khí). Danh sách preset trong `mau-canh.md` của `/lam-video-squire`.
   - **Phe ta / phe địch:** màu khiên, huy hiệu, cờ cố định.
   - **Nhân vật phụ** (vua, tướng, thầy tu, thợ rèn): preset + đặc điểm trang phục. Không mô tả mặt người thật.
   - **Cảnh sơ đồ / bản đồ / bảng phấn / màn soi** cần có: đoạn số mấy, vẽ gì (khối quân nào đi đâu, vùng bản đồ nào, so sánh số nào).
   - **Nhạc theo phần** (`roman medieval war suspense somber victory ancient`) + mục **Tắt nhạc** (1–3 số đoạn).
   - **SFX gợi ý** ở các đoạn có hành động (ngựa, kiếm, mưa tên, kèn, trống, mưa, sấm).
   - **Nguồn.**
4. **`05-TIEU-DE-<slug>.md`:** theo `references/tieu-de-thumb.md`:
   - Video dài: 10 tiêu đề (★ 2 cái khuyên dùng), **3 phương án thumbnail** mỗi cái kèm khối code `thumb({...})` đầy đủ, mô tả YouTube (có chapters), 15–25 tag.
   - Short: 5 tiêu đề, mô tả ngắn + hashtag.

(Không có file 04: ngách này không dùng ảnh AI.)

## 4. Cách viết
1. Chốt mục (dài / short), câu hỏi trung tâm và **câu trả lời bất ngờ** trong 1 câu.
2. Video dài: chọn **trận cao trào** (cảnh mở bài sẽ quay lại), 3–5 chặng dẫn tới đó, **1 luật lặp lại**, **1 hiểu lầm** để đánh đổ, phần hậu truyện tới hiện đại, câu kết đảo. Short: chọn 1 con người, hook có con số/nghịch lý, 3–4 lần leo thang, cú đảo, kết cục.
3. Viết theo khung trong `cau-truc.md`, đúng tỉ lệ từng nhịp.
4. Đọc lại như giọng AI: câu nào dài quá, tên nào khó đọc, số nào chưa viết chữ thì sửa.
5. Cắt đoạn ra file 02. Viết 03, rồi 05.

## 5. Tự kiểm trước khi giao
- [ ] Đúng mục: dài 1.700–2.000 từ (hoặc theo yêu cầu) / short 180–220 từ.
- [ ] Dài: đủ 9 nhịp, mở giữa nguy hiểm và quay lại đúng cảnh đó ở cao trào, có luật lặp lại nhắc 2 lần, có câu kết đảo. Short: hook trong câu đầu, có cú đảo.
- [ ] Không xin đăng ký, không "in this video".
- [ ] Dữ kiện có nguồn trong 03; không bịa người, câu trích, con số.
- [ ] Mỗi câu vẽ được (thời kỳ, trang phục, nơi, giờ rõ ràng).
- [ ] Số viết chữ, không ký hiệu, không ngoặc đơn.
- [ ] File 02: mỗi đoạn 1 dòng kết thúc ` |` (trừ đoạn cuối), không dòng trống; ghép lại khớp file 01.
- [ ] File 05 (dài) có 3 phương án thumbnail kèm code `thumb()`, chữ thumbnail 1–3 từ, không lặp tiêu đề.
- [ ] Không dùng lại đề tài, so sánh, câu chữ của kênh đối thủ; không nhắc tên kênh đối thủ.
- [ ] Cuối câu trả lời nhắc bước tiếp: (1) đưa file 02 vào tool voice, Auto Split ký tự `|`, xuất mỗi đoạn 1 file (hoặc đọc gộp); (2) gọi `/lam-video-squire` và chọn đúng mục (dài 16:9 / short 9:16).

## 6. Gợi ý đề tài
Đưa 10 đề tài cho mục đã chọn. Mỗi đề tài 1 dòng: tiêu đề tiếng Anh · câu trả lời bất ngờ 1 câu · (dài) trận cao trào + các chặng / (short) nhân vật + cú đảo · tiềm năng 1–3 sao.

Chấm sao: (1) vật/chiến thuật/ người ai cũng từng thấy trong phim; (2) có nghịch lý rõ; (3) có trận hoặc khoảnh khắc kể thành cảnh được; (4) vẽ được bằng bộ nhân vật sẵn có (trung cổ, La Mã, Nhật, thế chiến).

**Quét đối thủ trước khi gợi ý:**
1. Đọc `DOI-THU-SQUIRE.txt` ở thư mục gốc của người dùng (nếu có) và danh sách `projects/` (đề tài đã làm).
2. Có trình duyệt (built-in browser hoặc Claude in Chrome):
   - Mở `https://www.youtube.com/@SquireExplains/videos` (video dài) và `.../shorts` (short), hoặc kênh người dùng chỉ định. Chờ ~3 giây.
   - Chạy JavaScript đọc `window.ytInitialData` → tab đang chọn → `richGridRenderer.contents[].richItemRenderer.content`: video dài lấy `lockupViewModel` (các trường `content` đầu tiên: tiêu đề, lượt xem, ngày), short lấy `shortsLockupViewModel` (`primaryText.content`, `secondaryText.content`).
   - Ghi đè `DOI-THU-SQUIRE.txt` (ngày cập nhật, tiêu đề, lượt xem).
   - Học **loại** đề tài đang ăn khách, **không chép đề tài**.
3. Không có trình duyệt: báo 1 dòng, gợi ý dựa trên loại đề tài ăn khách: "Why [lính/vũ khí] stopped/never...", "Why [đội hình] was a death trap", người không thể chết / người duy nhất / người bị phạt vì quá giỏi / người giả làm ai đó / người chiến đấu khi chiến tranh đã hết.

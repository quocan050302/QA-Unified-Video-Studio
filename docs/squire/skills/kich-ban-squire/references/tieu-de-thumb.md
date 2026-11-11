# Tiêu đề, thumbnail, mô tả, tag

## Tiêu đề (tiếng Anh, Title Case, 5–10 từ)
Ba công thức chính (đo từ kênh mẫu, video bùng view đều theo một trong ba):
1. **Why + [vật/việc ai cũng thấy trong phim] + [nghịch lý]** — dạng "Why [Soldiers] Stopped [Doing X]", "Why [Doing X] Was a Death Trap".
2. **The [tuổi/vai] Who [điều không thể]** / **What Happened to [người duy nhất...]?** — hợp Short.
3. **How [bên yếu, có số] [thắng / thoát] [bên mạnh, có số]** — "How [N] [Men] Held Off [N] [Enemies]".

Luật:
- **Đúng 1 từ IN HOA** để nhấn (NEVER, HATED, DIED, ENTIRE, ACTUALLY...), có thể không có.
- "?" khi là câu hỏi; "..." khi bỏ lửng (Short).
- Không giật tít sai sự thật. Không tên kênh.
- Gói 10 tiêu đề: 4 theo công thức 1, 3 theo công thức 2, 3 theo công thức 3 (hoặc biến thể), đánh dấu ★ cho 2 cái khuyên dùng.

## Thumbnail (chỉ video dài) — vẽ bằng code, ghi sẵn tham số `thumb()`
Công thức:
- **1 nhân vật bán thân lớn** một bên (R 0.18–0.24, chiếm 35–50% khung), biểu cảm rõ (bored/chán đời, shock, scared, angry, cry, smug).
- **1 ký hiệu đỏ** đối diện: biển cấm đè lên vật (`ban` + `thing`), mũi tên khối đỏ chỉ vào điểm mấu chốt, dấu ? đỏ phát sáng, sao nổ VS, đôi mắt trong bóng tối.
- **1–3 từ IN HOA** trắng, viền đen dày, bóng đổ, ở góc trên (đối diện nhân vật): một lời phán hoặc câu hỏi cụt ("USELESS.", "WHAT WENT WRONG?", "NO ESCAPE", "TOO LATE?"). **Không lặp lại tiêu đề.**
- **Nền**: cảnh trong video, mờ mạnh, sáng; hoặc chia đôi chéo 2 màu (đỏ / xám xanh) cho dạng so sánh, đối đầu.

Mỗi bài đưa **3 phương án**, mỗi phương án gồm: mô tả 1 dòng + khối code `thumb({...})` đầy đủ để `/lam-video-squire` dán thẳng vào `scenes/shots/thumb.js`. Ví dụ:
```js
thumb({
  bg: 'mud', time: 'storm', blur: 9,
  back: [{ preset: 'frenchKnight', rows: 3, cols: 14, x0: 0, x1: 0.6, yFront: 0.86, yBack: 0.7, hFront: 0.2, hBack: 0.1 }],
  hero: { preset: 'knight15', x: 0.74, y: 0.5, R: 0.22, face: 'scared', shield: null },
  symbols: [{ kind: 'q', x: 0.3, y: 0.62, r: 0.13 }],
  title: ['TOO', 'HEAVY?'], tx: 0.3, ty: 0.16, tsize: 0.2,
});
```
Preset, biểu cảm, mũ, ký hiệu: xem `mau-canh.md` của `/lam-video-squire`.

## Mô tả YouTube (tiếng Anh)
- 2–3 câu mở có từ khoá chính (tên trận, thời kỳ, loại lính) + câu hỏi của video.
- 3–5 mốc thời gian (chapters) nếu video dài.
- 1 dòng nguồn tham khảo chính (tên sách / bảo tàng).
- 3 hashtag: `#history #military #<thời kỳ>`.

## Tag (15–25 tag, tiếng Anh)
Từ khoá chính, tên trận, thời kỳ, loại lính, "animated history", "history explained", "medieval history"... không tên kênh khác.

## Short
- Tiêu đề theo công thức 2 hoặc 3, ≤ 60 ký tự, có thể thêm "..." cuối.
- Mô tả 1–2 câu + `#shorts #history #<chủ đề>`.
- Không cần thumbnail.

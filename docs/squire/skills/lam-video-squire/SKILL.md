---
name: lam-video-squire
description: Dựng video YouTube tiếng Anh ngách lịch sử quân sự hoạt hình (hiệp sĩ, La Mã, samurai, thế chiến, "Why Knights...", "The Soldier Who...") 100% bằng code - nhân vật đầu tròn trắng viền nâu đen, giáp và trang phục theo thời đại, ngựa, đội hình đông người, nền mờ sâu, mưa, mưa tên, sơ đồ khối quân nhìn từ trên, bản đồ giấy da, bảng phấn, màn soi; nhạc + SFX tự tạo (ngựa hí, vó ngựa, đấu kiếm, mưa tên, kèn trận); video dài 16:9 không phụ đề hoặc Short 9:16 phụ đề 1-3 chữ; thumbnail vẽ bằng code. Dùng khi gọi /lam-video-squire, nói "dựng video squire", "dựng video hiệp sĩ", "dựng video lịch sử quân sự", "dựng short", "làm bản xem trước", "sửa cảnh s0xx", "làm thumbnail".
---

# Dựng video lịch sử quân sự hoạt hình (H2 Squire Studio)

Nói chuyện với người dùng bằng **tiếng Việt**, ngắn gọn, không dùng thuật ngữ lập trình. Lời đọc và chữ trên hình là **tiếng Anh**.

Toàn bộ hình **vẽ bằng code** (canvas): nhân vật, ngựa, đội hình, nền, sơ đồ, bản đồ, chữ, thumbnail. Không cần ảnh AI. Chromium chạy ngầm chụp từng khung, ffmpeg ghép video.

**Tài nguyên trong skill này:**

- `kit/`: bộ dựng dùng chung H2 2D Studio: `render.mjs`, `engine/`, `packs/squire/` (bộ phong cách của ngách), `packs/doodle/` (dữ liệu bản đồ dùng chung), `tools/`, `audio/`, `projects/squire-mau/` (dự án mẫu đủ các loại cảnh + thumbnail mẫu).
- `references/cai-dat.md`: cài đặt lần đầu.
- `references/phong-cach.md`: luật hình của ngách. **Đọc trước khi lên cảnh.**
- `references/mau-canh.md`: toàn bộ mẫu cảnh, nhân vật, mũ, vũ khí, khiên, đồ vật, thumbnail.
- `references/am-thanh.md`: nhạc, SFX riêng của ngách, DROP.
- `references/kiem-tra.md`: xem trước, xuất bản cuối, danh sách kiểm tra.
- `references/dung-bang-card.md`: dựng bản cuối bằng card đồ hoạ trên máy Windows.

## Luật vàng
1. **Giữ nguyên lời đọc.** Mỗi cảnh minh hoạ đúng câu đang đọc, nghĩa đen trước.
2. **Dùng mẫu, không viết code từng cảnh.** Mỗi cảnh ghi `tpl` + `args` trong `story/shots.json`.
3. **Nhân vật "YOU" xuyên suốt**, đúng trang phục từng chặng; màu phe ta / phe địch cố định cả video.
4. **Vẽ nháp, nhìn, sửa, rồi mới xuất.** Luôn mở ảnh tổng hợp ra xem.
5. **3 điểm dừng hỏi người dùng:**
   - Lựa chọn ban đầu.
   - Ảnh tổng hợp 2 phút đầu (Short: toàn bộ).
   - Bản xem trước 30 giây.

   Nếu người dùng vắng: dùng mặc định, ghi rõ giả định, rồi làm tiếp.

## Bước 1: Nhận đầu vào

Hỏi **một lần** bằng AskUserQuestion, bỏ câu người dùng đã trả lời:

- **Làm mục nào** (luôn hỏi, trừ khi đã rõ):
  - **Video dài**: khung **16:9**, không phụ đề, 9–11 phút.
  - **Short**: khung **9:16**, phụ đề 1–3 chữ IN HOA trắng, 60–75 giây.
- **Voice**, một trong 2 dạng:
  - **Mỗi đoạn một file** (khuyên dùng): thư mục voice mà tool tạo từ `02-VOICE-<slug>.txt` bằng Auto Split ký tự `|` (`1.mp3`, `2.mp3`...). Kèm file 02.
  - **Một file gộp cả bài** (ElevenLabs, Minimax...): kèm file 01 hoặc 02.
- **Độ phân giải:** 1080p (mặc định) hoặc 720p (nhanh hơn ~2 lần).
- **Nơi dựng bản cuối:** card đồ hoạ trên máy người dùng (nhanh; cần máy đang mở và bấm đúp 1 file `.bat`) hoặc cloud (không cần máy, chậm hơn). **Luôn hỏi.** Xem `references/dung-bang-card.md`.
- **Nhạc nền:** nhạc tự tạo của ngách (mặc định, rất nhỏ) hoặc file nhạc của người dùng.
- **Tiêu đề video** (lấy từ file 05 nếu có).

## Bước 2: Cài hoặc kiểm tra studio
Làm theo `references/cai-dat.md`:
1. Chép `kit/` vào thư mục làm việc thành `h2-2d-studio/`. Đã có thì chỉ chép đè `engine/ packs/ tools/ audio/*.py render.mjs player.html package.json`. **Không** ghi đè `projects/` của người dùng (trừ `projects/squire-mau`).
2. `npm install`.
3. `python tools/doctor.py` (phải có dòng "Nhạc + SFX riêng của pack squire: OK"; thiếu thì `python audio/build_audio.py`).
4. Tự kiểm bằng `projects/squire-mau`.

## Bước 3: Dự án, voice, cắt cảnh

Chạy trong `h2-2d-studio/`. Dùng `python3` nếu `python` không phải Python 3.

```bash
# video dai
python tools/new_project.py --name <slug> --title "<tieu de>" --pack squire --lang en --style flat
# short
python tools/new_project.py --name <slug> --title "<tieu de>" --pack squire --lang en --style flat --aspect 9:16 --captions

# moi doan mot file voice (file 02 tach bang |). --drop: so doan tat nhac (muc "Tat nhac" trong 03-HINH)
python tools/prep_voice.py --project projects/<slug> --voice-dir "<thu muc voice>" --lines "<02-VOICE-<slug>.txt>" [--drop 57,112]
# hoac mot file gop ca bai
python tools/prep_voice.py --project projects/<slug> --single "<voice.mp3>" --script "<01-SCRIPT-<slug>.txt>"

# cat canh theo nhip doi thu
python tools/draft_shots.py --project projects/<slug> --min 1.4 --max 3.8      # video dai (trung vi ~2,4 giay)
python tools/draft_shots.py --project projects/<slug> --min 0.8 --max 2.6      # short (trung vi ~1,5 giay)
```
- Sau `new_project`, mở `config.json`: video dài đặt `"captions": false`; Short `"captions": true`. Đặt `"music": {"enabled": true, "gainDb": -15}` (Short −13).
- Mở `timeline/transcript.txt` kiểm tra: đủ khối, đúng chữ, thời lượng hợp lý.

## Bước 4: Lên hình cho từng cảnh

Đọc `references/phong-cach.md` và `references/mau-canh.md`, đọc file `03-HINH` của kịch bản (nếu có), rồi:

1. **Viết `story/bible.md`:**
   - Các chặng (thời kỳ / tuyến quân) và preset "YOU" của từng chặng, kèm ghi đè trang phục.
   - Phe ta / phe địch: preset, màu khiên, huy hiệu, cờ. Giữ cố định.
   - Nền và `time` từng chặng (ví dụ: 1066 `field` `sunset`; Agincourt `mud` `storm`).
   - Các cảnh sơ đồ / bản đồ cần có.
   - Kế hoạch nhạc theo phần + mục Tắt nhạc.
2. **Điền `tpl` + `args` cho mọi cảnh** trong `story/shots.json`, theo lô 40–60 cảnh. Mỗi cảnh có `tpl`, `args` cụ thể, `in` (`cut`, `fade` khi đổi chặng), `sfx` khi có hành động.
   - Tỉ lệ gợi ý: `scene` 40–50%, `close` 15–20%, `army` 8–12%, `top`/`plan`/`map` 10–15%, `item`/`board`/`xray`/`frame`/`split`/`title` phần còn lại.
   - Không quá 3 cảnh liền cùng mẫu và cùng khung hình; đổi cỡ cảnh (toàn – trung – cận) liên tục như phim.
   - Short: cảnh đầu (0–2 giây) phải là hình hành động mạnh nhất (cận mặt sốc, nổ, ngựa chồm), có `shake` hoặc `fx`.
3. **Xem ngay sau mỗi lô:**
   ```bash
   node render.mjs --project projects/<slug> --sheet --scale 0.4 --at 0.8
   ```
   Mở từng `build/sheets/sheet_XX.jpg`, sửa cảnh lỗi, bố cục chật, chữ đè mặt.
4. **Lô đầu (khoảng 2 phút; Short: toàn bộ)** gửi ảnh tổng hợp cho người dùng duyệt hướng hình rồi mới làm tiếp.

## Bước 5: Âm thanh
Đọc `references/am-thanh.md`:
- **Nhạc:** chọn theo chặng: `roman` (cổ đại), `medieval` (trung cổ), `war` (trận), `suspense` (chờ đợi, phục kích), `somber` (sau trận), `victory`, `ancient`. Nhạc rất nhỏ (−15).
- **SFX bám hình**, dày vừa: ngựa → `horse_neigh`/`hooves_*`; va chạm → `shield_bash`, `sword_clash`; mưa tên → `arrow_volley`; mưa → `rain_loop` −14 suốt đoạn; sơ đồ/bản đồ → `page_turn`; câu chốt → `sting_low` hoặc DROP.
- Nghe thử: `python tools/mix.py --project projects/<slug> --no-video`.

## Bước 6: Xem trước, xuất bản cuối, giao
1. Quét lỗi: `node render.mjs --project projects/<slug> --check --scale 0.25`.
2. Xem trước: `node render.mjs --project projects/<slug> --from 0 --to 30 --scale 0.5` → gửi `build/preview.mp4`.
3. Bản cuối (nếu chọn cloud):
   ```bash
   nohup node render.mjs --project projects/<slug> > projects/<slug>/build/render.log 2>&1 &
   ```
   Đọc log vài phút một lần, báo thời gian còn lại. Tốc độ đo được: máy cloud 2 nhân ~4 khung/giây ở 1080p (video 9,5 phút ~45–60 phút; Short 70 giây ~5–8 phút). Máy nhiều nhân thêm `--workers 4`.
4. Trộn âm: `python tools/mix.py --project projects/<slug>` → `out/<tiêu đề>.mp4` ở −14 LUFS.
5. **Thumbnail (chỉ video dài):**
   - Lấy phương án thumbnail trong file `05-TIEU-DE` (đã ghi sẵn tham số `thumb()`); không có thì tự thiết kế theo công thức: 1 nhân vật bán thân lớn một bên (35–50% khung) + 1 ký hiệu đỏ (biển cấm đè lên vật, mũi tên đỏ, dấu ? đỏ phát sáng, sao nổ VS) + 1–3 chữ IN HOA trắng viền đen ở góc trên + nền cảnh mờ.
   - Viết `scenes/shots/thumb.js` (mẫu trong `references/mau-canh.md`, ví dụ trong `projects/squire-mau/scenes/shots/thumb.js`), chạy `node render.mjs --project projects/<slug> --thumb` → `out/thumbnail.png`.
   - Mở ảnh kiểm tra: chữ không che mặt, đọc được khi thu nhỏ, ký hiệu đỏ rõ. Làm 2–3 phương án nếu người dùng muốn chọn.
   - Short không cần thumbnail riêng (YouTube lấy khung trong video).
6. **Kiểm cuối:** thời lượng khớp voice, có âm thanh, ảnh tổng hợp 1 khung mỗi 15 giây trông đúng; Short có phụ đề, không có gì quan trọng nằm dưới phụ đề. Gửi MP4 và thumbnail, nói rõ nơi lưu. Có thư mục đã kết nối thì ghi file vào đó.

## Dựng bản cuối bằng card đồ hoạ (khi người dùng chọn card ở Bước 1)
Đọc `references/dung-bang-card.md`. Tóm tắt:
1. Mọi việc trước bản cuối vẫn làm trên cloud: dự án, lên cảnh, ảnh tổng hợp, xem trước 30 giây, thumbnail.
2. Thay bước chạy nền `render.mjs` bản cuối bằng `python tools/goi_may.py --project projects/<slug> --out /mnt/user-data/outputs/<slug>-may`. Lệnh tự trộn tiếng và đóng gói thành các zip ≤ 25 MB kèm `DUNG-VIDEO-<SLUG>.bat`.
3. Chép tất cả file đó cùng thumbnail vào thư mục dự án trên máy người dùng bằng `device_commit_files`. Bảo người dùng bấm đúp file `.bat`.
4. Cứ 30–60 giây chép `render-log.txt` lên cloud (`device_stage_files`) đọc tiến độ: số khung/giây, thời gian còn lại, `XONG` hay `LOI`.
5. Xong thì kiểm tra file mp4: có hình và tiếng, thời lượng khớp voice. Báo người dùng.

## Sửa theo góp ý
- **Theo mã cảnh** (`s045: cho ngựa phi`): sửa `args` cảnh đó, xem lại `--sheet --ids s045`, dựng lại đoạn đó bằng `--from/--to`.
- **Đổi trang phục cả chặng:** sửa `story/bible.md` rồi sửa đồng loạt các cảnh của chặng.
- **Thumbnail:** sửa `thumb.js`, chạy lại `--thumb`.
- **Xin danh sách cảnh:** đọc `story/shots.json`, in mã cảnh, giây bắt đầu, câu đọc.

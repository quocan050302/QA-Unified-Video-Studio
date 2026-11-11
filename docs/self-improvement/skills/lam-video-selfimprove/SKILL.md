---
name: lam-video-selfimprove
description: Dựng phim hoạt hình ngắn KHÔNG LỜI ĐỌC kiểu kênh self-improvement ("An Animated Short Film") 100% bằng code - nền tối nét mảnh sáng, nhân vật đầu tròn màu kem, bóng đen cám dỗ phát sáng, chữ kể chuyện trắng, chữ cám dỗ viết tay màu nhấn, bộ đếm DAY N, điện thoại / đồng hồ / lịch cận cảnh, nhạc piano + SFX tự tạo - từ file kịch bản cảnh 01-PHIM; xuất MP4 16:9 hoặc 9:16 và thumbnail (ảnh AI + chữ code). Dùng khi gọi /lam-video-selfimprove, nói "dựng phim self improvement", "dựng video không lời", "dựng phim DISCIPLINE / TOMORROW...", "làm bản xem trước", "sửa cảnh b0xx", "làm thumbnail".
---

# Dựng phim ngắn không lời (H2 Studio, gói ngách Self-Improvement)

Nói chuyện với người dùng bằng **tiếng Việt**, ngắn gọn, không dùng thuật ngữ lập trình.

Toàn bộ hình **vẽ bằng code** (canvas, Chromium chạy ngầm chụp từng khung, ffmpeg ghép video). Không cần voice, không cần ảnh AI trong video. Chỉ thumbnail dùng 1 ảnh AI (`T01`) do người dùng tạo theo `03-THUMB-PROMPT`.

**Tài nguyên trong skill này:**
- `kit/`: bộ dựng dùng chung với các gói H2. Gồm `render.mjs`, `engine/`, `packs/dem/` (bộ phong cách của ngách này), `tools/` (có `phim.py`), `audio/`, `projects/selfimprove-mau/` (dự án mẫu đủ mọi mẫu cảnh).
- `references/cai-dat.md`: cài đặt lần đầu.
- `references/phong-cach.md`: luật hình của ngách. **Đọc trước khi lên cảnh.**
- `references/mau-canh.md`: toàn bộ mẫu cảnh, nhân vật, tư thế, boi cảnh và tham số.
- `references/am-thanh.md`: nhạc, SFX.
- `references/kiem-tra.md`: xem trước, xuất bản cuối, danh sách kiểm tra.

## Luật vàng
1. **Giữ nguyên chữ và thời lượng trong file 01.** Muốn đổi chữ thì hỏi người dùng.
2. **Dùng mẫu cảnh, không viết code từng cảnh.** Mỗi cảnh là `tpl` + `args` trong `story/shots.json`. Chỉ cảnh đặc biệt mới viết code (`scenes/shots/<id>.js`).
3. **Nhân vật nhất quán:** cùng preset (`hoodie`, `band`, `hero`) và màu nhấn suốt phim, ghi trong `story/bible.md`.
4. **Vẽ nháp, nhìn, sửa, rồi mới xuất.** Luôn mở ảnh tổng hợp ra xem trước khi xuất.
5. **3 điểm dừng hỏi người dùng:**
   - Lựa chọn ban đầu (gồm nơi dựng bản cuối: card hay cloud).
   - Ảnh tổng hợp toàn phim (lô đầu).
   - Bản xem trước 30 giây có tiếng.

   Nếu người dùng vắng: dùng mặc định, ghi rõ đã giả định gì, rồi làm tiếp.

## Bước 1: Nhận đầu vào
Hỏi một lần, bỏ qua câu người dùng đã trả lời:
- **File `01-PHIM-<slug>.txt`** (từ `/kich-ban-selfimprove`). Không có thì đề nghị viết bằng lệnh đó.
- **Khung:** 16:9 (mặc định, có dải đen điện ảnh) hoặc 9:16 (Shorts, không dải đen).
- **Màu nhấn:** lấy từ dòng `ACCENT` trong file 01; mặc định `red`.
- **Độ phân giải:** 1080p (mặc định) hoặc 720p.
- **Nơi dựng bản cuối:** card đồ hoạ trên máy người dùng (nhanh, vài phút; cần máy đang mở, có thư mục đã kết nối và bấm đúp 1 file `.bat`) hoặc cloud (không cần máy, chậm hơn nhiều). **Luôn hỏi**, kể cả khi người dùng đã trả lời các câu khác. Xem `references/dung-bang-card.md`.
- **Ảnh thumbnail `T01.png`** (không bắt buộc lúc đầu, cần ở bước cuối).
- **Tiêu đề video.**

## Bước 2: Cài hoặc kiểm tra studio
Làm theo `references/cai-dat.md`:
1. Chép `kit/` vào thư mục làm việc thành `h2-2d-studio/`. Đã có thì chỉ chép đè `engine/ packs/ tools/ audio/*.py render.mjs player.html package.json`. **Không** ghi đè `projects/`.
2. `npm install`.
3. `python tools/doctor.py` → đến khi `SAN SANG`.
4. `python audio/build_audio.py` (tạo SFX và nhạc, kể cả nhạc riêng của ngách).
5. Tự kiểm bằng `projects/selfimprove-mau`.

## Bước 3: Dự án và bản nháp tự động
Chạy trong `h2-2d-studio/`. Dùng `python3` nếu `python` không phải Python 3.

```bash
python tools/new_project.py --name <slug> --title "<tiêu đề>" --pack dem --style flat --lang en [--aspect 9:16] [--resolution 720p]
python tools/phim.py --project projects/<slug> --phim "<01-PHIM-<slug>.txt>"
node render.mjs --project projects/<slug> --sheet --scale 0.5 --at 0.75
```
- `phim.py` đọc file 01 → `story/shots.json`: thời lượng từng cảnh, chữ (tự xếp giờ hiện), bộ đếm, nhạc, SFX, **đoán sẵn** mẫu cảnh, bối cảnh, nhân vật từ mô tả tiếng Việt. Có cảnh báo nếu chữ không đủ giờ đọc.
- Bản nháp tự động chỉ là khởi điểm. Bước 4 mới làm cho đẹp.

## Bước 4: Lên hình cho từng cảnh
Đọc `references/phong-cach.md` và `references/mau-canh.md`, rồi:
1. **Viết `story/bible.md`:** preset nhân vật chính (và lúc nào đổi: hoodie → băng đô khi tập), bạn bè / cô gái / gia đình, màu nhấn, bộ đếm, các bối cảnh lặp lại (cùng phòng ngủ thì cùng `setArgs`: lịch, đèn, laptop), kế hoạch máy quay.
2. **Sửa `args` của mọi cảnh trong `story/shots.json`** theo mô tả `scene`:
   - Bối cảnh + `setArgs` (giờ đồng hồ, lịch tháng mấy tô bao nhiêu ô, đèn, trời).
   - `actors`: ai, ở đâu (`x` số hoặc mốc `bed.sit`, `desk.seat`, `bus.seat`, `bench`, `top`...), tư thế, biểu cảm, `faceAt`/`poseAt` đổi theo giây, `walk`/`run`. Cảnh có chữ cám dỗ (`~`) phải có `who: "voice"`.
   - Nằm trong chăn: dùng `bed` (không dùng actor).
   - `cam`: đẩy chậm vào chủ thể (`from` → `to`, zoom 1.0 → 1.15–1.4). Cảnh cảm xúc đẩy vào mặt.
   - `fx`: `shards` khi bóng đen vỡ, `flash` ở bước ngoặt, `pulse` ở cú sụp, `speed` khi chạy, `zzz`, `embers`, `rain`.
   - Chuyển cảnh: `in: {"type": "dip"}` giữa các nhịp lớn, còn lại `cut`.
3. **Xem ngay:** `node render.mjs --project projects/<slug> --sheet --scale 0.5 --at 0.75`, mở từng `build/sheets/sheet_XX.jpg`, sửa cảnh lỗi: chữ đè mặt, nhân vật ra ngoài khung, bóng đen che mất nhân vật chính.
4. Gửi ảnh tổng hợp cho người dùng duyệt (điểm dừng 2).

## Bước 5: Âm thanh
Đọc `references/am-thanh.md`. Phim không lời nên **nhạc và SFX là giọng kể**:
- Nhạc theo nhịp: `sad` (mở, sa ngã) → `dark` (đáy, `gainDb` −3) → `none` 1 cảnh lặng sau câu đau nhất → `hope` (bước ngoặt) → `rise` (đứng lên) → `resolve` (thẻ kết).
- SFX dày hơn ngách có lời: mỗi 1–2 cảnh một tiếng; `tempt_swell` / `tempt_whisper` mỗi lần bóng đen nói; `sting_low` hoặc `boom_deep` ở cú sụp; `glass_shatter` khi bóng đen vỡ.
- Nghe thử: `python tools/mix.py --project projects/<slug> --no-video`.

## Bước 6: Xem trước, xuất bản cuối, giao
1. **Quét lỗi:** `node render.mjs --project projects/<slug> --check --scale 0.25`.
2. **Xem trước 30 giây có tiếng:**
   ```bash
   python tools/mix.py --project projects/<slug> --no-video
   node render.mjs --project projects/<slug> --from 0 --to 30 --scale 0.5
   ```
   Gửi `build/preview.mp4` (điểm dừng 3).
3. **Bản cuối:**
   ```bash
   nohup node render.mjs --project projects/<slug> > projects/<slug>/build/render.log 2>&1 &
   ```
   (Người dùng chọn **card** ở Bước 1 thì không chạy lệnh này: làm theo mục *Dựng bản cuối bằng card đồ hoạ* bên dưới.)
   Phim 3 phút 1080p mất khoảng 3–5 phút trên máy cloud 2 nhân (bộ `dem` vẽ bằng CPU, không cần GPU). Đọc log và báo thời gian còn lại.
4. **Trộn âm:** `python tools/mix.py --project projects/<slug>` → `out/<tiêu đề>.mp4`, −14 LUFS.
5. **Thumbnail:** chép `T01.png` vào `projects/<slug>/anh/`, viết `scenes/shots/thumb.js`:
   ```js
   import { thumb } from '/packs/dem/pack.js';
   thumb({ img: 'T01', title: 'WAKE UP.' });
   // 2 dòng, đổi màu 1 từ:   thumb({ img: 'T01', lines: ['JUST ONE', 'MORE.'], accent: ['MORE.'] });
   // gạch xoá số:           thumb({ img: 'T01', title: 'DAY 412 0.', strike: '412', accent: ['0.'] });
   ```
   Chạy `node render.mjs --project projects/<slug> --thumb` → `out/thumbnail.png`. Mở ra kiểm: chữ không che mặt, không cắt mép. Chưa có ảnh AI thì lệnh vẽ cảnh mẫu bằng code để xem bố cục chữ (không dùng làm thumbnail thật).
6. **Kiểm cuối** theo `references/kiem-tra.md`, gửi MP4 + thumbnail, ghi vào thư mục người dùng nếu có.

## Dựng bản cuối bằng card đồ hoạ (khi người dùng chọn card ở Bước 1)
Đọc `references/dung-bang-card.md`. Tóm tắt:
1. Mọi việc trước bản cuối vẫn làm trên cloud: dự án, voice, lên cảnh, ảnh tổng hợp, xem trước 30 giây, thumbnail.
2. Thay bước chạy nền `render.mjs` bản cuối (và bước trộn âm sau đó) bằng lệnh `python tools/goi_may.py --project projects/<slug> --out /mnt/user-data/outputs/<slug>-may`. Lệnh này tự trộn tiếng và đóng gói thành các zip ≤ 25 MB kèm `DUNG-VIDEO-<SLUG>.bat`.
3. Chép tất cả file đó cùng thumbnail vào thư mục dự án trên máy người dùng bằng `device_commit_files` (tối đa 100 MB mỗi lần gọi; file nào bị từ chối thì `SendUserFile` trước rồi chép bằng `fileUuid`). Bảo người dùng bấm đúp file `.bat`.
4. Cứ 30–60 giây chép `render-log.txt` lên cloud (`device_stage_files`) để đọc tiến độ: card nào đang dùng, số khung/giây, thời gian còn lại, `XONG` hay `LOI`.
5. Xong thì kiểm tra file mp4: có hình và tiếng, thời lượng khớp voice. Báo người dùng tốc độ và thời gian dựng thật.

## Sửa theo góp ý
- **Theo mã cảnh** ("b07: cho bóng đen ngồi trên giường"): sửa `args` cảnh đó, xem lại bằng `--sheet --ids b07`, dựng đoạn đó bằng `--from/--to`.
- **Đổi chữ hoặc thời lượng:** sửa file 01 rồi chạy lại `phim.py --force` **chỉ khi chưa lên hình**; đã lên hình thì sửa trực tiếp `texts` / `start` / `end` trong `shots.json` (cảnh sau phải dời theo, `duration` = `end` cảnh cuối).
- **Làm bản 9:16 từ phim 16:9:** tạo dự án mới `--aspect 9:16`, chép `story/shots.json`, xem tổng hợp và chỉnh `x` nhân vật về giữa.

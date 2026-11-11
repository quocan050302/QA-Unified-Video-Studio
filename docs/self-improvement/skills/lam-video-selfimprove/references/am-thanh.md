# Âm thanh (phim không lời)

`tools/mix.py` dựng toàn bộ âm thanh từ `story/shots.json`. Không có `timeline/voice.wav` thì chỉ trộn **nhạc + SFX**, rồi chuẩn hoá tổng −14 LUFS (chuẩn YouTube) và ghép vào `build/video_silent.mp4` thành `out/<tiêu đề>.mp4`.

Phim không lời nên nhạc to và rõ hơn ngách có giọng đọc: đối thủ để nhạc là xương sống cảm xúc, có khoảnh khắc **im lặng** hẳn.

## Nhạc nền (`"music"` trong shots.json)
Các đoạn liền nhau `{ "start", "end", "bed", "gainDb" }`. `phim.py` tự tạo từ cột `NHẠC` của file 01.

| bed | dùng khi | mô tả |
|---|---|---|
| `sad` | mở đầu, sa ngã | piano chậm từng nốt + pad mỏng (Am, 64 bpm) |
| `dark` | đáy, cám dỗ thắng | drone trầm + nhịp tim + chuông xa. Nên `gainDb: -3` |
| `hope` | bước ngoặt, khoảnh khắc người thật | pad sáng + chuông (F, 76 bpm) |
| `rise` | đứng lên, tập luyện, montage | piano rải + nhịp + trống nhẹ (Am, 96 bpm) |
| `resolve` | thẻ kết | hợp âm trưởng ấm, piano (C, 70 bpm) |
| `tension` `emotional` `mystery` `wonder` `curious` `triumph` | dự phòng | nhạc chung của bộ dựng |
| `none` | im lặng | sau câu đau nhất, trước thẻ kết, màn đen mở đầu |

- Nhạc vào/ra dần 1,2 giây. `"notes": "DROP"` trong một cảnh = tắt nhạc êm trong cảnh đó.
- To/nhỏ chung: `config.music.gainDb` (mặc định −15). Phim không lời có thể để −12 đến −10. Đổi 2–3 dB mỗi lần.
- Nhạc riêng của người dùng: `config.json` → `"music": { "enabled": true, "file": "input/<tên>.mp3", "gainDb": -12 }`.
- Mọi nhạc tạo bằng code (`audio/music.py`, `packs/dem/audio.py`), không bản quyền.

## Hiệu ứng (`"sfx"` từng cảnh)
`[{ "at": <giây từ đầu cảnh>, "name": "<tên>", "gain": -8 }]` — `phim.py` tự tạo từ cột `SFX` (`tên@giây`).

**Riêng ngách** (`packs/dem/audio.py`): `alarm_beep` `alarm_long` (báo thức bíp), `glass_shatter` (bóng đen vỡ), `rain_loop` (8 giây mưa), `notif_msg` (tin nhắn đến), `msg_sent` (gửi tin), `punch_bag`, `boom_deep` (cú sụp), `tempt_swell` (cám dỗ trồi lên), `tempt_whisper` (thì thầm), `clock_tick` (4 giây tích tắc), `footsteps`, `door_open`, `breath_in`, `sting_low` (cú sụp, nặng), `page_flip`.

**Chung:** `whoosh_fast whoosh_mid whoosh_long whoosh_tiny whoosh_reverse impact_heavy impact_light impact_punch flash_hit slowmo_ring ding_high ding_soft ting_idea pop pop_low tick ui_click type_key typing_2s riser_2s riser_4s downer heartbeat glitch thud_soft phone_ring phone_vibrate crowd_cheer`.

Quy ước:
- Bóng đen nói: `tempt_swell` (lần đầu, câu mạnh) hoặc `tempt_whisper` (câu nhẹ) ngay lúc chữ bắt đầu gõ.
- Cú sụp bộ đếm: `sting_low` hoặc `boom_deep` đúng giây `reset.at`.
- Montage lịch / bộ đếm: `page_flip` hoặc `tick` 2–3 lần; feed lướt: `whoosh_mid`.
- Bước ngoặt: `notif_msg` (tin nhắn người thật) hoặc `breath_in` rồi im.
- Đứng lên: `riser_2s` → `impact_light`; tập: `punch_bag`, `footsteps`.
- Bóng đen vỡ: `glass_shatter` cùng giây với `fx: shards`.
- Mức: UI nhỏ −12 đến −16, thường −6 đến −10, khoảnh khắc lớn −3 đến −6 (`config.sfx.gainDb` cộng thêm, mặc định −4). Không chồng quá 2 tiếng.

## Kiểm tra
`ffmpeg -i out/<file>.mp4 -af ebur128 -f null -` → Integrated khoảng −14 LUFS. Nghe 3–4 đoạn: nhạc không rè trầm, SFX đúng nhịp chữ, có ít nhất 1 khoảnh khắc im lặng.

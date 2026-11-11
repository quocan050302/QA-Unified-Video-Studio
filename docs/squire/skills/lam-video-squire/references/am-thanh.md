# Âm thanh (ngách lịch sử quân sự)

`tools/mix.py` dựng toàn bộ âm thanh từ `story/shots.json`: voice chuẩn khoảng −16 LUFS, nhạc nền thấp hơn voice, SFX theo từng cảnh, rồi chuẩn hoá tổng −14 LUFS và ghép vào `build/video_silent.mp4` thành `out/<tiêu đề>.mp4`.

Đo từ kênh mẫu: nhạc/không khí **rất nhỏ**, nằm dưới giọng khoảng 12–15 dB; SFX **dày vừa, bám hình** (mưa, tên bay, kiếm chạm, ngựa hí, hò hét).

## Nhạc nền (`"music"` trong shots.json)
Các đoạn liền nhau `{start, end, bed, gainDb}`. Đặt `config.json` → `"music": {"enabled": true, "gainDb": -15}`.

Nhạc riêng của ngách (tự tạo bằng code, không bản quyền):

| bed | Dùng khi |
|---|---|
| `medieval` | Trung cổ châu Âu, kể chuyện bình thường (đàn gảy + trống khung) |
| `roman` | La Mã, Hy Lạp, cổ đại (kèn trầm + trống khung) |
| `war` | Trận đánh, xung phong, cao trào (trống dồn) |
| `suspense` | Chờ đợi, phục kích, "something is waiting" (nhịp gảy căng) |
| `somber` | Sau trận, cái chết, buồn (pad trầm) |
| `victory` | Chiến thắng, kết có hậu |
| `ancient` | Bí ẩn cổ xưa, mở đầu chậm |

Nhạc chung vẫn dùng được: `curious`, `mystery`, `wonder`, `tension`, `sad`, `dark`, `triumph`, `none`.

- Đổi nhạc ở bước ngoặt: đổi thời kỳ, vào trận cao trào, câu trả lời, phần hậu truyện. Thường 60–150 giây một lần.
- **DROP:** ghi `"notes": "DROP"` vào cảnh cần tắt nhạc (khoảnh khắc lặng nhất: người chết, câu chốt). 1–3 lần mỗi video.
- Short: 1 bed suốt bài (thường `suspense` hoặc `war`), `gainDb` −13.

## Hiệu ứng (`"sfx"` từng cảnh)
`[{"at": <giây tính từ đầu cảnh>, "name": "<tên>", "gain": -8}]`.

Bộ riêng của ngách:

| Tên | Tiếng |
|---|---|
| `horse_neigh`, `horse_snort` | ngựa hí, ngựa khịt mũi |
| `hooves_walk`, `hooves_gallop` | vó ngựa đi bộ / phi (4 giây) |
| `sword_clash`, `sword_draw`, `shield_bash`, `spear_hit` | kiếm chạm, rút kiếm, va khiên, giáo đâm |
| `armor_clank`, `chainmail` | giáp kêu khi bước, giáp lưới xào xạc |
| `arrow_whoosh`, `arrow_thunk`, `arrow_volley` | một mũi tên bay, tên cắm, cả loạt mưa tên (3 giây) |
| `javelin_throw` | lao bay rồi cắm |
| `battle_roar`, `battle_far` | hò hét xung phong gần / trận xa |
| `war_horn`, `horn_roman`, `drum_hit`, `drum_march` | tù và trận, kèn La Mã, trống đánh 1 tiếng, trống hành quân |
| `thunder`, `wind_loop`, `rain_loop`, `mud_step`, `splash` | sấm, gió, mưa, lội bùn, té nước |
| `musket_shot`, `cannon`, `explosion` | súng hoả mai, đại bác, nổ (thời cận đại, thế chiến) |
| `fire_crackle`, `bell_toll`, `coin_drop`, `page_turn` | lửa trại, chuông nhà thờ, tiền rơi, lật giấy (bản đồ, sơ đồ) |

Bộ chung: `whoosh_fast whoosh_mid whoosh_long pop tick ding_soft ting_idea impact_light impact_heavy riser_2s downer heartbeat sting_low crowd_cheer footsteps door_open`...

Quy ước:
- Cảnh có hành động nhìn thấy được thì có tiếng: ngựa xuất hiện → `horse_neigh` hoặc `hooves_*`; lính va nhau → `shield_bash` + `sword_clash`; mưa tên → `arrow_volley`; trời mưa → `rain_loop` (gain −14) suốt đoạn.
- Mở sơ đồ / bản đồ giấy → `page_turn`. Mũi tên đỏ hiện → `whoosh_tiny`. Chữ to hiện → `impact_light`.
- Câu chốt đắt → `sting_low` hoặc DROP nhạc.
- Mức: nền (mưa, gió, trận xa) −14 đến −18; thường −6 đến −10; khoảnh khắc lớn −3 đến −5. Tối đa 2 tiếng chồng nhau, để lời sạch.
- Mật độ: video dài khoảng 1 tiếng mỗi 4–6 giây (đoạn trận dày hơn). Short 1 tiếng mỗi 2–3 giây.

## Kiểm tra
`ffmpeg -i out/<file>.mp4 -af ebur128 -f null -` → khoảng −14 LUFS. Nghe 3–4 đoạn: lời rõ, nhạc không lấn, SFX đúng nhịp hình.

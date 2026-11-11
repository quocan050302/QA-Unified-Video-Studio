# Mẫu cảnh của bộ `dem`

Mỗi cảnh trong `story/shots.json`: `{ "id", "start", "end", "tpl", "args", "in", "sfx", "notes" }`.
- **Toạ độ** `x`, `y`: số 0..1 = tỉ lệ khung (0.5 = giữa); số > 1.5 = px trên khung 1920×1080. **Cỡ** `h`, `s`: 0..1 = tỉ lệ chiều cao khung.
- **Thời gian** `at`, `dur`, `out`: giây tính từ đầu cảnh.
- Thiếu mẫu / sai tên → khung đỏ "THIEU MAU". Xem mọi mẫu trong `projects/selfimprove-mau`.

## Lớp phủ chung (mọi mẫu)

### `texts` — chữ
```json
"texts": [
  { "kind": "narr", "t": "Tomorrow sounded reasonable.", "at": 0.4, "dur": 4.2 },
  { "kind": "tempt", "t": "start tomorrow.", "at": 0.6 },
  { "kind": "say", "t": "hi.", "who": "girl", "at": 1.0 },
  { "kind": "big", "t": "3 hours later...", "at": 0.3 }
]
```
- `narr`: chữ kể chuyện trắng, cỡ 58 (dọc 64). `pos`: `top` (mặc định) | `bottom` | `center`; hoặc `x`, `y`. `type: true` = gõ từng chữ. `emph: {"zero": "#ffb03b"}` = tô màu 1 từ. Ở mẫu `phone`, chữ kể chuyện tự đặt bên phải điện thoại.
- `tempt`: giọng cám dỗ, chữ viết tay màu nhấn, tự gõ từng chữ, tự đặt trên đầu bóng đen (hoặc bên cạnh nếu sát mép trên). Muốn đặt tay: `x`, `y`. `"\n"` để xuống dòng. `size` nhỏ dần ở nhịp "yếu dần" (62 → 44 → 30), `color` mờ dần (`"#ffb03b88"`).
- `say`: bong bóng trắng nhỏ trên đầu người nói (`who`: preset của actor; mặc định người đầu tiên).
- `big`: chữ nhấn rất to (112), trắng viền xám nổi, giữa màn — dùng cho câu chốt trên màn đen.
- `sign`: chữ viết tay tự do (`x`, `y`, `size`, `color`).

### `hud` — bộ đếm góc trái
```json
"hud": { "rows": [ { "label": "DAY", "n": 47 } ] }
"hud": { "rows": [ { "label": "DAY", "from": 3, "to": 30, "at": 0.3, "dur": 4 } ] }          // đếm dần
"hud": { "rows": [ { "label": "DAY", "n": 412, "reset": { "at": 1.5, "to": 0 } } ] }          // gạch về 0, số mới màu nhấn
"hud": { "rows": [ { "label": "SEEN", "n": 1388, "accent": true }, { "label": "KNOWN", "n": 0 } ] }
```
Số tự có dấu phẩy nghìn (`comma: false` để tắt).

### `cam` — máy quay
`"cam": { "from": [x, y, zoom], "to": [x, y, zoom], "at": 0, "dur": <hết cảnh>, "ease": "sine" | "linear" }` — `x, y` là điểm nhìn (0..1). Mặc định đẩy rất nhẹ (zoom 1 → 1.05). `"shake": [{ "at": 1.6, "amt": 1, "dur": 0.45 }]` rung máy.

### `fx` — hiệu ứng
`[{ "kind": ..., "at": giây, "dur": giây, "x", "y", "color" }]`
- `shards`: bóng đen vỡ thành mảnh sáng (mặc định ở vị trí bóng đen). Đi kèm `out` của actor voice cùng giây.
- `flash`: chớp trắng. `pulse`: viền đập nhịp màu nhấn (`speed`, `a`). `dark`: tối dần (`a`). `glitch`: nhiễu sọc.
- `speed`: vệt tốc độ (chạy, đấm; `dir` 1 / -1). `zzz`: chữ z bay. `embers`: tàn lửa bay lên. `rain`, `dust`: mưa, bụi. `spot`: đốm sáng (`r`, `color`).

### `lights` — đèn thêm
`[{ "x": 0.7, "y": 0.6, "r": 0.3, "color": "#ffc56b", "a": 0.35 }]`

### `vignette`: số 0..1 (mặc định 0.5) hoặc `false`.

## `scene` — bối cảnh + nhân vật + bóng đen
```json
{ "tpl": "scene", "args": {
  "set": "bedroom",
  "setArgs": { "clock": "5:00", "ring": true, "calendar": { "month": "OCT", "fill": 12, "mode": "x" }, "lamp": true, "laptop": true, "sky": "moon" },
  "bed": { "face": "sleep", "faceAt": [[1.2, "tired"]], "arm": { "at": 1.5 }, "zzz": true },
  "actors": [
    { "who": "hoodie", "x": "bed.sit", "pose": "sitphone", "hold": "phone", "face": "tired", "glowFace": "#9fb6ff" },
    { "who": "voice", "x": 0.62, "pose": "reach", "facing": -1, "at": 0.5, "out": 4.0 }
  ],
  "cam": { "from": [0.5, 0.55, 1.1], "to": [0.45, 0.55, 1.25] },
  "texts": [ { "kind": "tempt", "t": "one more.", "at": 0.8 } ]
} }
```

### Bối cảnh (`set`) và `setArgs`
| set | setArgs | mốc đặt nhân vật |
|---|---|---|
| `bedroom` | `clock` ("3:17"), `ring`, `blink`, `calendar` {month, fill, mode `x`/`fill`, color} hoặc `false`, `lamp`, `laptop` (true / "off"), `sky` (`moon` `dawn` `rain` `night` `dark` `day`), `window: false`, `desk: false`, `door`, `doorOpen` (0..1), `bedX` | `bed.sit` (mép giường), `bed.head`, `desk.seat` (ghế bàn), `clock` |
| `city` | `time` (`dusk` `night` `dawn` `day`), `birds`, `lamps` [x...], `scroll` (đường chạy trôi) | — |
| `street` | `neonDoor` (x, cửa cám dỗ phát sáng), `busstop: false`, `busX`, `lampX`, `rain: false` | `bus.seat`, `neon` |
| `lockers` | `board: false`, `boardX` | — |
| `classroom` | `sky`, `board` (chữ trên bảng), `desks` [x...] | — |
| `court` | `hoopX`, `benchX` | `bench` |
| `cafe` | `lampX` | `table.left`, `table.right` |
| `gym` | `bag: false`, `bagX`, `swing`, `barbell`, `barbellX`, `spot` | — |
| `stairs` | `top: false`, `topColor` | `step:0` … `step:8` |
| `hill` | — | `top` (đỉnh đồi) |
| `mirror` | `mirrorX` | `mirror` |
| `kitchen` | `sky`, `lamp` | — |
| `doorway` | `doorX`, `doorOpen` | `door` |
| `void` | `spot` (x đèn rọi) | — |
| `black` | — | — |
Chung: `gy` (mặt sàn 0..1), `dim` (0..1 làm tối).

### `bed` — nhân vật nằm trong chăn
`{ "who": "hero", "face": "sleep", "faceAt": [[giây, mặt]], "look", "rot", "arm": true | { "at", "dur" } (với tay về đồng hồ), "zzz": true }`. Chỉ dùng với `set: bedroom`.

### `actors` — nhân vật
| khoá | ý nghĩa |
|---|---|
| `who` | `hero` (trần), `band` (băng đô màu nhấn), `hoodie` (hoodie xám, mũ hạ sau cổ, đầu tròn trơn — mặc định), `hooded` (trùm mũ lên đầu, chỉ khi cảnh cần), `friend` `friend2` `friend3` (mũ vàng / xanh / đỏ), `girl` (tóc bob, khăn vàng), `mom`, `dad`, `kid`, `ghost` (mờ), `voice` (bóng đen cám dỗ) |
| `x`, `y` | vị trí chân (số hoặc mốc bối cảnh) |
| `h` | chiều cao (mặc định 0.42; voice 0.48) |
| `pose`, `poseAt` | tư thế; `poseAt: [[1.5, "cheer"]]` đổi theo giây |
| `face`, `faceAt` | biểu cảm (voice mặc định `grin`) |
| `facing` | 1 nhìn phải, -1 nhìn trái. `look` -1..1 lệch mắt, `lookAt` |
| `walk` / `run` | `{ "to": 0.8, "at": 0, "dur": 4, "speed": 0.9 }` — tự quay mặt theo hướng đi |
| `hold` | `phone` (màn hình phát sáng; `screen` màu), `umbrella`, `book`, `ball`, `bag`, `cup` |
| `glowFace` | màu ánh sáng hắt lên mặt (điện thoại `#9fb6ff`, cảm dỗ = màu nhấn) |
| `at`, `out`, `fade` | hiện ở giây, biến mất ở giây (mờ dần trong `fade`) |
| `behind` | vẽ sau giường / nhân vật khác |
| `scale`, `rot`, `z`, `seed` | phóng, nghiêng, thứ tự vẽ, lệch nhịp chớp mắt |
| `tears`, `sweat`, `shoes`, `bloodshot` | nước mắt, mồ hôi, màu giày, mắt đỏ gân máu |

**Tư thế (`pose`):** `stand relaxed slump phone reach point wave cheer fist headhold facepalm arms shrug hug guard punch lift sit sitphone sitdesk sitsad knees kneel crouch climb open umbrella carry`.
**Biểu cảm (`face`):** `neutral tired sleepy sleep sad cry worried scared shock angry determined effort smile happy smirk empty guilty bloodshot haunted grin`. `bloodshot` / `haunted` = lòng trắng hồng, gân đỏ, quầng thâm (thức đêm, nghiện, kiệt sức). Thêm `"bloodshot": true` vào actor (hoặc mẫu `face`) để giữ mắt đỏ với bất kỳ biểu cảm nào.

## `phone` — điện thoại cận cảnh, 2 tay cầm
Chung: `bg` (bối cảnh mờ phía sau, vd `"bedroom"`), `setArgs`, `hands` (false để ẩn tay; mặc định 4 ngón tay trái ôm mép + ngón cái phải có tay áo), `thumb` (ngón cái nhún như đang lướt), `tilt`, `clock` (giờ thanh trạng thái), `sleeve` (màu tay áo), `h`, `x`, `y`.
| `screen` | args riêng |
|---|---|
| `feed` | `posts`: danh sách ảnh bài đăng minh hoạ, mỗi lần 1 bài, giữ `hold` giây (1.1; lướt nhanh 0.5–0.7) rồi vuốt lên. Ảnh có sẵn: `ramen car burger pizza sneakers dog cat beach mountain sunset gym watch money game coffee city party selfie girl donut cake` (`girl` = bóng neon kín đáo, `neon` đổi màu). `style: "blocks"` = kiểu khối màu mờ cũ |
| `reel` | `art` (1 ảnh minh hoạ như feed, đặt giữa màn), `from` (giây đang xem), `total` (tổng giây), `speed`, `color` |
| `chat` | `name`, `avatar` (màu), `messages: [{ "text", "me": true/false, "at" }]` (trước tin đến có dấu "đang gõ"), `seen` (giây hiện "Seen"), `keyboard`, `draft` + `draftAt` (gõ dở trong ô nhập) |
| `email` | `rows: [{ "from", "subject", "preview", "hl": true }]` hoặc `from`, `subject`, `preview` |
| `lock` | `time`, `date`, `notes: [{ "app", "text", "at" }]` |
| `counter` | `n`, `label` ("CLEAN STREAK"), `color` |
| `off` | `reflect` (bóng mặt mờ trên màn tắt) |

## `clock` — đồng hồ báo thức to
`{ "time": "11:59", "timeAt": [[1.6, "12:00"]], "ring": true, "blink": true, "color": "#ff3b30", "s": 0.55 }`

## `calendar` — lịch to
`{ "month": "NOV", "from": 0, "to": 24, "mode": "x" | "fill", "at": 0.3, "dur": 3, "reset": { "at": 3.5 }, "color" }`

## `face` — cận mặt (từ ngực lên)
`{ "who": "hoodie", "face": "guilty", "faceAt": [[2, "cry"]], "bloodshot": true, "look": -0.3, "lookAt", "pose", "hold", "tears", "sweat", "glowFace": "#9fb6ff", "bg": "bedroom", "setArgs", "actors": [voice...], "lights" }`

## `note` — sổ tay, tay viết chữ
`{ "text": "day 1.\nno phone before noon.", "at": 0.3, "cps": 9, "sleeve" }`

## `black` — nền đen + chữ
`{ "texts": [...], "dust": true, "cy": 0.43, "line": true }` — chữ to **giữa màn** (kiểu kênh mẫu): dòng `narr` cỡ 78, dòng `big` cỡ 112 chữ trắng viền xám nổi; các dòng không ghi `y` tự xếp dọc quanh `cy`. `line` = vạch ngắn màu nhấn phát sáng ở đáy (mặc định bật, `false` để tắt). Không có vignette; bộ đếm chỉ hiện nếu ghi `hud`.

## `card` — thẻ kết
`{ "word": "TOMORROW.", "part": "PART 2", "sub": "Tomorrow is a place.", "sub2": "Nobody lives there.", "sub2At": 3.0, "type": true, "typeDur": 1.2, "size" }` — từ khoá gõ từng chữ, gạch chân màu nhấn, `sub` trắng, `sub2` màu nhấn.

## `cta` — xin like / subscribe
`{ "line": "If this hit, like and subscribe.", "line2": "Day 1 starts tonight.", "who": "hoodie" }` — nút LIKE, SUBSCRIBE có con trỏ bấm, nhân vật vẫy tay.

## Thumbnail (`scenes/shots/thumb.js`)
`thumb({ img: 'T01', title | lines, accent: [từ], strike: 'số', y: 0.16, size, arc, rot, align: 'left', x, focus: [x, y], crop })` — font tròn cực đậm, trắng, viền đen dày, bóng đổ; từ trong `accent` đổi màu nhấn; `strike` gạch xoá một từ.

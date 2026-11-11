# Mẫu cảnh của pack `squire`

Mỗi cảnh trong `story/shots.json`: `{ "id", "start", "end", "line", "tpl": "<mẫu>", "args": {...}, "in": {"type": "cut"|"fade"}, "sfx": [...] }`.

Quy ước chung:
- `x`, `y`: 0..1 = tỉ lệ khung (0.5 = giữa). `h`, `R`, `s`: 0..1 = tỉ lệ **chiều cao** khung.
- `at`: số giây tính từ đầu cảnh, hoặc **cụm chữ** trong lời đọc (`"at": "shovel"`) để hiện đúng lúc đọc tới.
- Mọi mẫu có máy quay: `move` (`in` mặc định | `out` | `left` | `right` | `up` | `down` | `still`), `moveAmt` (0.035), `zoom: [x, y, độ_zoom, từ, kéo_dài]`, `shake` + `shakeAt`.
- Mọi mẫu nhận lớp phủ chung: `signs`, `arrows`, `marks`, `labels` (xem cuối file).

## Nhân vật (`people[]`, `front[]`, `backPeople[]`, `others[]`)
```json
{ "preset": "knight15", "x": 0.5, "y": 0.93, "h": 0.6, "pose": "stand", "face": "worried",
  "faceAt": [["arrows", "scared"]], "poseAt": [[1.2, "cower"]], "look": 0.5, "flip": false, "talk": true,
  "walk": true, "from": 0.1, "to": 0.6, "dur": 2, "enter": "left", "exit": "arrows", "jump": 0.5, "fall": "down", "tremble": true,
  "weapon": "sword", "shield": {"type": "heater", "color": "#efc23f", "charge": "lion", "chargeColor": "#c9473a"},
  "helmet": "bascinet", "visor": "down", "horse": {"color": "grey", "gait": "walk", "cloth": {"color": "#efc23f", "charge": "lion"}} }
```
- `y` là chân chạm đất. `flip: true` quay sang trái. `look` −1..1 liếc mắt.
- **Đi lại (chân chạm đất thật, không trượt):**
  - `"walk": true` → đi ngang theo hướng mặt (đổi hướng bằng `flip` hoặc `dir: -1`), tự di chuyển qua khung, bước chân tính theo quãng đường nên bàn chân đứng yên trên đất khi đang trụ. `speed` (mặc định 1) chỉnh nhanh chậm.
  - `"from": 0.2, "to": 0.8` → đi tới điểm, tự quay đúng hướng.
  - `"pose": "run"` → chạy (bước dài, người đổ về trước).
  - `"walk": "front"` hoặc `"pose": "march"` → bước tại chỗ / tiến về phía máy quay (đội hình hành quân).
  - Không dùng `walk` mà nhân vật đứng yên giữa cảnh thì đừng ghi `walk` (chân sẽ đứng).
- Ngựa: `horse.gait` `walk` / `gallop` tự di chuyển ngang, móng chạm đất theo nhịp 4 chân thật; `horse.travel: false` để đứng yên (chỉ dùng khi ngựa bị che chân).
- Ghi đè bất kỳ thuộc tính trang phục nào của preset: `helmet`, `visor` (`up`|`down`|`none`), `body`, `tabard`, `tabardColor`, `charge`, `chargeColor`, `tunicColor`, `legs`, `legColor`, `hair`, `hairColor`, `beard` (`stubble`|`short`|`full`|`long`), `mustache` (`normal`|`big`), `freckles`, `glasses`, `cape`, `scarf`, `gauntlet`, `kid`.
- `weapon: null` bỏ vũ khí, `shield: null` bỏ khiên.
- **Hai kiểu dáng vẽ riêng (giống kênh mẫu), tự bật theo mũ:**
  - **Hiệp sĩ áo lưới** (`helmet` `nasal` / `spangen` / `coif` + `body: "mail"`; preset `norman`, `william`, `knight12`...`knight13`): mũ và thân liền một khối hình hạt đậu, ô mặt chỉ lộ mắt, tấm che miệng có dây buộc, tay áo lưới có bao da ở cổ tay, găng trắng có ngón, khiên diều cầm sau lưng một bên, tay trái đặt lên chuôi kiếm. `shield.front: true` để cầm khiên phía trước. `mailColor`, `cuff`, `tunicColor` (vạt áo dưới), `tabard` có huy hiệu. Tắt kiểu này: `hoodStyle: false`.
  - **Hiệp sĩ giáp tấm** (`helmet` `bascinet` / `bucket`; preset `knight14`, `knight15`, `whiteArmor`, `frenchKnight`, `henry`, `you`): mũ vòm to trùm đầu, mặt nạ lật lớn trên đỉnh (`visor: "up" | "down" | "none"`), tấm che cằm (`bevor: false` để bỏ), vai giáp nhỏ, tay thép mảnh có khớp tròn ở khuỷu, găng thép có ngón, áo choàng huy hiệu ngắn (`tabard: false` để bỏ). `plume: true | "<màu>"` thêm lông chim. Tắt kiểu này: `plateStyle: false`.
- `horse`: nhân vật cưỡi ngựa. `color`: `brown` `bay` `grey` `white` `black` `chestnut` `dun`; `gait`: `stand` `walk` `gallop` `rear`; `dapple`, `cloth` (áo phủ ngựa), `saddle`, `neigh: true` (há miệng hí), `face`: `calm` (mí khép nửa, kiểu kênh mẫu) `angry` `scared`; `blaze: false` bỏ vệt trắng trên mặt, `socks: true` cổ chân trắng, `muzzle` màu mõm.

**Preset** (`CAST`):

| Nhóm | Preset |
|---|---|
| Trung cổ | `norman`, `william` (mũ có nan vàng), `saxon`, `viking`, `knight12` (mũ thùng), `knight13` (mũ lưới), `knight14`, `knight15` (giáp tấm + áo huy hiệu, mũ mặt nạ lật), `whiteArmor`, `frenchKnight`, `frenchKnight2` (mặt nạ đóng), `henry` (giáp + vương miện), `king`, `englishArcher`, `crossbowman`, `peasant`, `smith`, `monk`, `lady`, `you` |
| La Mã, Hy Lạp | `hastatus` (lính trẻ, 3 lông vũ), `princeps`, `triarius` (lính già, mũ mào đỏ), `latin`, `latinOld`, `velites`, `legionary`, `senator`, `priest`, `consul`, `greek`, `spartan` |
| Nhật | `samurai`, `ashigaru`, `ronin` |
| Cận đại, thế chiến | `serbSoldier`, `ww1Brit`, `ww2us` (rằn ri), `ww2usOlive`, `ww2jp`, `ww2de`, `officer`, `officerJP`, `sailor`, `pilot`, `nurse` |
| Hiện đại | `modern`, `police`, `scientist` |

**Tư thế** (`pose`): `stand idle wave point pointUp shrug present armsUp cheer think hips fist salute cower facepalm hold carry guard thrust raise shoot draw aim cross beg stop march walk run kneel sit fall scratch hug hand lunge push brace wide` (`push`/`lunge`: chân trước gập gối chân sau duỗi, người đổ về trước, khiên đẩy ra — cảnh xô đẩy hàng khiên; `brace`: tì người chống đỡ; `wide`: đứng dạng chân).

**Biểu cảm** (`face`): `neutral calm happy laugh smile proud sad cry worried scared shock surprised angry shout bored smug determined confused tired pain dead sleep wink think`.

**Mũ** (`helmet`): `nasal spangen coif bucket bascinet kettle sallet crown montefortino attic kabuto jingasa m1 brodie cap peaked sailor riot riotDown hood turban none`. **Tóc**: `short bowl long braid curly bald bun topknot side`.

**Vũ khí** (`weapon`): `sword katana dagger spear pilum pike lance naginata pollaxe axe hammer mace bow crossbow rifle musket pistol flag torch staff shovel pickaxe saw stake pot basket scroll pouch grenade`. Súng trường khi buông tay tự đeo sau lưng.

**Khiên** (`shield.type`): `kite heater scutum round buckler pavise riot`. **Huy hiệu** (`charge`): `lion fleur cross crossW stripe bars chevron quarter star eagle lightning wings sun circle rose boss`.

## `scene` — cảnh chính (dùng nhiều nhất)
```json
{ "tpl": "scene", "args": { "bg": "field", "time": "sunset", "bgOpts": {"trees": 2, "bushes": 5, "castle": true, "tents": 3, "flags": true, "mud": false},
  "blur": 6, "back": [ <doi hinh> ], "mid": [ <doi hinh net> ], "people": [ ... ], "front": [ ... ], "props": [ ... ],
  "fx": [{"kind": "rain"}, {"kind": "volley", "at": "arrows", "n": 40}], "tint": ["#ff9a5a", 0.08], "dark": 0.1 } }
```
- `bg`: `field` (đồng cỏ, đồi, hàng cây), `mud` (ruộng cày bùn lầy, có vũng nước), `plain` (đồng bụi vàng kiểu La Mã, núi lửa, thông dù), `castle` (tường đá trong lâu đài: `banner`, `window`, `torch`, `door`), `hall` (sảnh cột), `workshop` (xưởng gỗ), `tent` (trong lều chỉ huy, đèn lồng), `cathedral`, `trench` (chiến hào), `sea`, `underwater`, `sky`, `city`, `paper`, `color`.
- `bgOpts` cho nền ngoài trời: `groundY` (0.66), `path` (đường đất uốn qua đồng), `pebbles` (số sỏi, 10), `tufts` (số bụi cỏ, 34), `patches` (mảng đất, 3), `trees`, `bushes`, `castle`, `castleX`, `tents`, `flags` (true hoặc `[{x, color, charge}]`), `volcano`, `mud`, `wet`, `sun`, `sunX`, `clouds`, `flowers`, `patches`, `seed`.
- `back`: đội hình phía sau (bị mờ cùng nền). `mid`: đội hình nét đứng sau nhân vật chính. `front`: người tiền cảnh to và mờ (nhìn qua vai), ví dụ `{"preset": "norman", "x": 0.12, "y": 1.3, "h": 0.9, "flip": true}`.
- `fx`: `rain` (`n`, `a`), `volley` (mưa tên rơi: `at`, `n`, `x0 x1 y0 y1`, `dir`), `javelins`, `stuck` (tên cắm đất), `dust`, `smoke` (`x`, `y`), `rays` (tia nắng), `flash`, `thunder`.

## `army` — đội hình đông người
```json
{ "tpl": "army", "args": { "preset": "hastatus", "presets": ["hastatus", "princeps"], "rows": 4, "cols": 9, "march": 1, "flip": false,
  "face": "determined", "flags": [{"col": 0.5, "row": 0.8, "kind": "eagle"}], "enemy": "latin", "bg": "plain", "time": "golden" } }
```
- Mặc định 1 khối quân to phía trước + hàng quân địch nhỏ ở xa. Thay bằng `mid` / `back` để tự xếp.

**Đội hình** (dùng trong `back`, `mid`, `army`): `{ preset | presets[], rows, cols, x0, x1, yFront, yBack, hFront, hBack, spread, march (bước tại chỗ / tiến về máy quay), advance (tiến ngang, ví dụ 0.02 = 2% khung mỗi giây, chân bước đúng quãng đường), flip, face, faces[], weapon, gaps: [cột bỏ trống], skipFront, flags: [{col, row, kind: 'eagle'|'vexillum', color}], seed }`. Hàng xa tự vẽ đơn giản cho nhanh.

## `close` — cận mặt / bán thân
```json
{ "tpl": "close", "args": { "preset": "knight15", "face": "scared", "faceAt": [["mud", "pain"]], "talk": false, "x": 0.5, "y": 0.48, "R": 0.24,
  "look": 0, "pose": "stand", "keepShield": false, "bg": "mud", "time": "storm", "back": [ <doi hinh> ], "others": [{"preset": "norman", "x": 0.15, "R": 0.16, "face": "bored"}], "fx": [{"kind": "rain"}] } }
```
- Mặc định bỏ khiên cho thấy rõ người; `keepShield: true` để giữ (kiểu nấp sau khiên).
- Dùng cho câu phản ứng, câu hỏi tu từ, nhân vật nói.

## `top` — sơ đồ nhìn từ trên (khối quân chạy)
```json
{ "tpl": "top", "args": { "ground": {"color": "#c9ad7a", "grass": true, "rocks": false},
  "blocks": [{"x": 0.3, "y": 0.5, "w": 0.06, "h": 0.14, "cell": 0.024, "side": "blue", "face": 1, "path": [["gaps", 0.2, 0.5]], "fade": ["dies", 1.5], "tired": true, "spears": true}],
  "zones": [{"x": 0.5, "y": 0.5, "w": 0.6, "h": 0.7, "color": "#6e4a2c", "at": "fort", "dur": 1.5, "dashed": false}],
  "dust": [{"x": 0.4, "y": 0.5, "s": 0.12, "at": 1}], "fog": [0.55, 0.8], "arrows": [{"from": [0.6, 0.5], "to": [0.85, 0.5], "at": "push"}] } }
```
- Khối quân tự xếp dày theo `cell` (cỡ 1 lính, mặc định 0.024); ghi `cols`/`rows` nếu muốn đếm đúng số.
- `side`: `blue red grey purple gold green`. `face`: 1 nhìn phải, −1 nhìn trái. `path`: `[[thời_điểm, x, y], ...]` cho khối quân di chuyển. `fog`: dải bụi che (như "behind them, all you see is dust").

## `plan` — khối chữ nhật trên tờ giấy (giải thích đội hình)
`{ "paper": "parchment"|"notebook", "blocks": [{x,y,w,h,side,at,path,cols,rows}], "zones", "arrows", "labels" }` — khối mặc định kiểu chữ nhật kẻ ô.

## `map` — bản đồ giấy da trên bàn gỗ (địa lý thật)
```json
{ "tpl": "map", "args": { "view": [5, 36, 24, 47], "places": [{"text": "Rome", "lon": 12.5, "lat": 41.9, "at": "Rome"}],
  "routes": [{"pts": [[12.5, 41.9], [15.5, 40.6], [21.5, 39.8]], "at": "Greece", "dur": 1.2}],
  "troops": [{"lon": 14.4, "lat": 40.8, "side": "red", "at": 1}], "mountains": [{"lon": 14.43, "lat": 40.82, "s": 0.06, "label": "Vesuvius"}] } }
```
- `view`: `[kinh_độ_trái, vĩ_độ_dưới, kinh_độ_phải, vĩ_độ_trên]` hoặc tên: `europe`, `mideast`, `japan`, `china`, `world`... Tên địa danh viết tiếng Anh, IN HOA tự động.

## `board` — bảng phấn so sánh
`{ "title": "ENERGY", "bars": [{"label": "ARROW", "v": 1, "at": 0}, {"label": "MUSKET BALL", "v": 10, "at": "musket"}], "mult": {"text": "x10", "x": 0.5, "y": 0.45, "at": "ten times"}, "curve": [[0.2,0.75],[0.5,0.3]] }`

## `xray` — màn soi xanh (vết thương, bên trong)
`{ "hit": {"at": "arrow", "dx": -0.25, "dy": 0.25, "ang": -0.4}, "label": "ARROWHEAD" }`

## `frame` — khung tranh / vật treo tường
`{ "bg": "castle"|"wood", "people": [...], "props": [...], "arrows": [...] }` — như giải thích "áo giáp lớn dần" bằng hình nhân trong khung.

## `item` — cận cảnh đồ vật trên nền mờ
`{ "thing": {"kind": "shield", "type": "kite", "s": 0.62, "charge": "lion", "anim": "pop"}, "props": [...], "bg": "castle", "time": "day", "sway": true }`

**Đồ vật** (`props[].kind`, `thing.kind`): `shield pavise sword spear pilum pollaxe axe bow crossbow rifle musket torch katana lance mace hammer dagger naginata shovel pickaxe saw stake pot basket scroll pouch grenade flag standard eagle tent tree pine cypress bush castle cloud helmet (helmet: <kiểu>) gauntlet arrow arrowhead arrows sack barrel rock campfire chest coin seal easel anvil lantern cart car cauldron skull soldier horse`.
- Thuộc tính chung: `x, y, s, at, anim (pop|drop|grow|spin|float), rot, flip, top: true (vẽ trên người), gone: <at> (biến mất), ghost: true (để lại viền nét đứt trắng)`.

## `split` — chia đôi chéo (so sánh 2 phe / 2 giả thuyết, chỉ 16:9)
`{ "left": {"color": "#b94a3c" | "bg": "field", "people": [...], "props": [...]}, "right": {...}, "slant": 0.08, "labels": [...] }`

## `title` — chữ to giữa khung (hiếm dùng: tên trận, biệt danh, năm)
`{ "text": "AGINCOURT\n1415", "sub": "...", "bg": "mud", "time": "storm", "dim": 0.25 }`

## `black` — màn đen (kết, cắt im lặng)

## Lớp phủ chung
- `signs`: biển giấy kem chữ IN HOA viết tay, có đuôi nhọn: `[{"text": "YOU", "x": 0.5, "y": 0.15, "at": 0.3, "size": 40, "tail": "down"|null}]`.
- `arrows`: mũi tên khối đỏ `{"from": [x,y], "to": [x,y], "at", "w", "color"}`; cong `{"kind": "curve", "pts": [[x,y],...]}`; nét `{"kind": "line", "dash": true}`.
- `marks`: `q` (dấu ? đỏ, `glow`), `!`, `ban` (biển cấm), `circle` (khoanh đỏ), `dashed` (viền nét đứt), `sparks` (tia lửa va chạm), `x`.
- `labels`: chữ to kiểu thumbnail (trắng viền đen): `{"text": "30 KG", "x", "y", "size": 90, "at", "rot", "color"}`; `kind: "chalk"` (chữ phấn), `kind: "sign"` (chữ tay nâu).

## Thumbnail (`scenes/shots/thumb.js`)
```js
import { thumb } from '/packs/squire/pack.js';
thumb({
  bg: 'field', time: 'day', bgOpts: { tents: 4, flags: true }, blur: 9,
  back: [{ preset: 'frenchKnight', rows: 2, cols: 12, x0: 0, x1: 0.6, yFront: 0.85, yBack: 0.72, hFront: 0.2, hBack: 0.12 }],
  hero: { preset: 'knight13', x: 0.74, y: 0.5, R: 0.21, face: 'bored', pose: 'present', shield: null },
  symbols: [{ kind: 'ban', x: 0.27, y: 0.66, r: 0.2, thing: { kind: 'shield', type: 'heater', color: '#3e64a3' } }],
  title: ['NO SHIELD?'], tx: 0.3, ty: 0.16, tsize: 0.2,
});
```
- `hero` (bán thân, `R` 0.18–0.24) hoặc `heroes: [...]` (thêm `full: true, h` để vẽ cả người). `mid`: đội hình nét.
- `symbols`: `ban` (kèm `thing` bị cấm), `arrow` (`to: [x, y]`), `q`, `!`, `vs`, `eyes` (mắt trong bóng tối), hoặc bất kỳ đồ vật nào. `overSymbols` vẽ đè lên nhân vật.
- `title`: 1–2 dòng (chuỗi hoặc `{text, x, y, size, color, rot}`); `tx`, `ty`, `tgap`, `tsize`, `tcolor`, `trot`.
- `split: { left: '#c9473a' | {bg, time}, right: ..., slant }` cho thumbnail đối đầu 2 nửa.

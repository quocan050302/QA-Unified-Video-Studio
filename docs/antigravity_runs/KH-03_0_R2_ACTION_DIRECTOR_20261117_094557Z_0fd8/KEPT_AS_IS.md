# KEPT AS IS — Protected Legacy & R0/R1 Surfaces (KH-03.0.R2)

Các tệp/thư mục sau **KHÔNG BỊ SỬA ĐỔI** so với baseline `c0c239e36ed6cb2bf9365d3bd74d6d4bfa5cf0be` để bảo toàn 100% style Squire Roman gốc, kiến trúc WebGL/3D legacy và tính tương thích ngược R0/R1:

| Đường dẫn | Vai trò | Trạng thái |
|---|---|---|
| `visual_styles/roman_squire_master/v1/style_bible.json` | Master style contract (`1d3209a7...`) | Kept intact (`0` bytes diff) |
| `tools/kh03_style_lock.py` | Runtime & compile style lock verifier | Kept intact |
| `engine/core.js` | Shared timeline/shot/blur engine | Kept intact (`0` bytes diff) |
| `engine/player.js` | Browser player + synchronous `lastShotError` reject | Kept intact (`0` bytes diff) |
| `engine/three3d.js` | Legacy 3D support (never loaded by R2) | Kept intact (`0` bytes diff) |
| `packs/squire/chara.js`, `ink.js`, `world.js`, `army.js`, `horse.js`, `templates.js` | Core Production Squire drawing primitives | Kept intact |
| `packs/squire/roman_master/gate_city_env.js`, `camera.js`, `environment.js`, `motion.js` | R0/R1 scenes, camera spline, motion helpers | Kept intact |
| `projects/kh03_roman_last_gap_30s` | KH-03.0 original baseline pilot + MP4 | Kept intact (regression checked) |
| `projects/kh03_r1_roman_gate_message_30s` | KH-03.0.R1 pilot (`script_beat_director_v1`) | Kept intact (regression checked) |
| `projects/squire-mau`, `projects/selfimprove-mau`, `packs/dem` | Existing Production template projects | Kept intact |
| `origin/Production`, `origin/fix/Image-Shot`, `origin/feat/modern-2d-cinematic` | Protected remote git branches | Untouched & verified |

# Cài đặt studio (một lần cho mỗi máy / thư mục làm việc)

Bộ dựng là một bộ công cụ nhỏ Node + Python nằm trong thư mục `kit/` của skill `lam-video-2d`. Phải chép ra một thư mục làm việc có quyền ghi, vì thư mục plugin có thể chỉ đọc và studio cần `node_modules`, dự án và file xuất bên cạnh.

## 1. Tìm kit
- `kit/` nằm trong thư mục gốc của skill này.
- Nếu không rõ đường dẫn: `find / -path "*lam-video-2d/kit/render.mjs" 2>/dev/null | head -1` (Linux/macOS/máy ảo Cowork) hoặc PowerShell: `Get-ChildItem -Recurse -Filter render.mjs -Path $HOME\.claude | Select-Object -First 1`.

## 2. Chọn nơi làm việc và chép
- Dùng thư mục người dùng đã kết nối nếu có (ví dụ `D:\whatif`), không thì thư mục làm việc hiện tại. Tạo `h2-2d-studio/` ở đó.
- Đã có `h2-2d-studio/render.mjs` → đã cài, sang bước 4. **Không bao giờ ghi đè `projects/` của người dùng.**
- Chép toàn bộ `kit/` vào: `cp -r "<kit>/." h2-2d-studio/` (bash) hoặc `Copy-Item -Recurse "<kit>\*" h2-2d-studio\` (PowerShell).
- Nếu phiên làm việc chạy trên máy cloud (không có shell trên máy người dùng): cài và dựng ở máy cloud, chỉ chép video thành phẩm về thư mục của người dùng.

## 3. Cài phụ thuộc
Báo người dùng một danh sách ngắn: ffmpeg (ghép hình/tiếng), Node.js + gói (bộ vẽ, font viết tay tiếng Việt, dữ liệu bản đồ thế giới, Three.js), Chromium chạy ngầm (vẽ từng khung), numpy/scipy/soundfile (tạo tiếng và nhạc).

| Cần | Windows | macOS | Linux |
|---|---|---|---|
| ffmpeg + ffprobe | `winget install --id Gyan.FFmpeg -e` (mở terminal mới) | `brew install ffmpeg` | `sudo apt-get install -y ffmpeg` |
| Node.js ≥ 18 | `winget install OpenJS.NodeJS.LTS` | `brew install node` | gói của distro / nodesource |
| Python ≥ 3.9 | python.org | `brew install python` | gói của distro |
| Gói JS | `npm install` (trong h2-2d-studio) | như trên | như trên |
| Chromium | `npx playwright install chromium` | như trên | như trên (`npx playwright install-deps chromium` nếu thiếu thư viện) |
| Gói Python | `python -m pip install numpy scipy soundfile` | như trên | thêm `--break-system-packages` nếu Python bị quản lý |
| Tiếng + nhạc | `python audio/build_audio.py` (tạo khoảng 80 SFX và 18 nền nhạc, trong đó có bộ riêng của ngách: ngựa hí, vó ngựa, đấu kiếm, mưa tên, kèn trận, trống; khoảng 1–2 phút) | như trên | như trên |

Hoặc chạy `python tools/doctor.py --install` để tự cài phần còn thiếu.

## 4. Kiểm tra và tự thử
1. `python tools/doctor.py` (dùng `python3` nếu `python` không phải Python 3, `py -3` trên một số máy Windows). Lặp lại đến khi mọi dòng là OK.
2. Tự thử: `node render.mjs --project projects/squire-mau --sheet --scale 0.4 --at 0.8`. Phải ghi ra `projects/squire-mau/build/sheets/sheet_01.jpg` và `sheet_02.jpg` (lính La Mã hành quân, cận mặt, đội hình đông người, sơ đồ nhìn từ trên, sơ đồ trên giấy, chia đôi, đồ vật cận cảnh, chữ to). Rồi `node render.mjs --project projects/squire-mau --thumb` ra `out/thumbnail.png`. Mở ảnh kiểm tra, rồi xoá `build/` và `out/` của dự án mẫu.
3. Không bắt buộc Whisper: mốc thời gian lấy từ voice mỗi dòng một file — chính xác nhất. Chỉ khi dùng một file gộp cả bài mới nên cài thêm `python -m pip install faster-whisper` (cần mạng tới huggingface.co lần đầu) để dùng `--whisper small --lang vi`.

## Ghi chú
- Máy không GPU (máy chủ Linux, máy ảo Cowork): Chromium tự dùng SwiftShader, chạy được nhưng chậm hơn.
- Dung lượng: ~400 MB cho node_modules + Chromium, cộng file xuất (video 10 phút 1080p khoảng 150–300 MB).
- Cập nhật plugin hoặc dùng chung với gói ngách khác: chép `engine/ packs/ tools/ render.mjs player.html package.json` mới đè lên bản cài cũ rồi `npm install`, giữ nguyên `projects/`. Mọi gói ngách H2 dùng chung một thư mục `h2-2d-studio/`.

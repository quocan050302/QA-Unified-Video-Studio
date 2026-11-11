# Cài đặt studio (một lần cho mỗi máy / thư mục làm việc)

Bộ dựng là một bộ công cụ nhỏ Node + Python nằm trong thư mục `kit/` của skill `lam-video-selfimprove`. Phải chép ra một thư mục làm việc có quyền ghi, vì thư mục plugin có thể chỉ đọc và studio cần `node_modules`, dự án và file xuất bên cạnh.

## 1. Tìm kit
- `kit/` nằm trong thư mục gốc của skill này.
- Nếu không rõ đường dẫn: `find / -path "*lam-video-selfimprove/kit/render.mjs" 2>/dev/null | head -1` (Linux/macOS/máy ảo Cowork) hoặc PowerShell: `Get-ChildItem -Recurse -Filter render.mjs -Path $HOME\.claude | Select-Object -First 1`.

## 2. Chọn nơi làm việc và chép
- Dùng thư mục người dùng đã kết nối nếu có (ví dụ `D:\whatif`), không thì thư mục làm việc hiện tại. Tạo `h2-2d-studio/` ở đó.
- Đã có `h2-2d-studio/render.mjs` (cài từ gói ngách khác): chép đè `engine/ packs/ tools/ audio/*.py render.mjs player.html package.json` từ kit mới, chép thêm `projects/selfimprove-mau`, rồi chạy lại bước 3 (`npm install` để thêm font mới, `audio/build_audio.py` để tạo nhạc riêng). **Không bao giờ ghi đè `projects/` khác của người dùng.**
- Chép toàn bộ `kit/` vào: `cp -r "<kit>/." h2-2d-studio/` (bash) hoặc `Copy-Item -Recurse "<kit>\*" h2-2d-studio\` (PowerShell).
- Nếu phiên làm việc chạy trên máy cloud (không có shell trên máy người dùng): cài và dựng ở máy cloud, chỉ chép video thành phẩm về thư mục của người dùng.

## 3. Cài phụ thuộc
Báo người dùng một danh sách ngắn: ffmpeg (ghép hình/tiếng), Node.js + gói (bộ vẽ, font chữ kể chuyện Comic Neue, chữ viết tay Caveat, chữ thumbnail Luckiest Guy, dữ liệu bản đồ, Three.js), Chromium chạy ngầm (vẽ từng khung), numpy/scipy/soundfile (tạo tiếng và nhạc).

| Cần | Windows | macOS | Linux |
|---|---|---|---|
| ffmpeg + ffprobe | `winget install --id Gyan.FFmpeg -e` (mở terminal mới) | `brew install ffmpeg` | `sudo apt-get install -y ffmpeg` |
| Node.js ≥ 18 | `winget install OpenJS.NodeJS.LTS` | `brew install node` | gói của distro / nodesource |
| Python ≥ 3.9 | python.org | `brew install python` | gói của distro |
| Gói JS | `npm install` (trong h2-2d-studio) | như trên | như trên |
| Chromium | `npx playwright install chromium` | như trên | như trên (`npx playwright install-deps chromium` nếu thiếu thư viện) |
| Gói Python | `python -m pip install numpy scipy soundfile` | như trên | thêm `--break-system-packages` nếu Python bị quản lý |
| Tiếng + nhạc | `python audio/build_audio.py` (tạo khoảng 47 SFX và 11 nền nhạc, kể cả nhạc riêng của ngách; khoảng 1 phút) | như trên | như trên |

Hoặc chạy `python tools/doctor.py --install` để tự cài phần còn thiếu.

## 4. Kiểm tra và tự thử
1. `python tools/doctor.py` (dùng `python3` nếu `python` không phải Python 3, `py -3` trên một số máy Windows). Lặp lại đến khi mọi dòng là OK.
2. Tự thử: `node render.mjs --project projects/selfimprove-mau --sheet --scale 0.4 --at 0.8`. Phải ghi ra `projects/selfimprove-mau/build/sheets/sheet_01.jpg`, `sheet_02.jpg` đủ các mẫu: phòng ngủ có bóng đen phát sáng, bộ đếm DAY, phố mưa, điện thoại chat / feed / email, đồng hồ, lịch, cận mặt, sổ tay, thẻ kết, màn xin đăng ký. Mở ảnh xem chữ đúng font (chữ kể chuyện tròn, chữ cám dỗ viết tay), rồi xoá thư mục `build/` của dự án mẫu.
3. Ngách này **không cần voice, không cần Whisper**.

## Ghi chú
- Máy không GPU (máy chủ Linux, máy ảo Cowork): bộ `dem` vẽ bằng CPU, không cần GPU, xuất khoảng 20 khung/giây ở 1080p.
- Dung lượng: ~400 MB cho node_modules + Chromium, cộng file xuất (phim 3 phút 1080p khoảng 20–40 MB).
- Cập nhật plugin hoặc dùng chung với gói ngách khác: chép `engine/ packs/ tools/ render.mjs player.html package.json` mới đè lên bản cài cũ rồi `npm install`, giữ nguyên `projects/`. Mọi gói ngách H2 dùng chung một thư mục `h2-2d-studio/`.

# Dựng bản cuối bằng card đồ hoạ trên máy người dùng

Máy cloud chỉ có 2 nhân và không có card đồ hoạ. Máy Windows có card rời thì nhanh hơn nhiều lần, nhất là cảnh 3D.

Số đo thật: video 8 phút 46 giây, 1080p, thế giới 3D terrain. Máy cloud dựng khoảng 3 khung/giây ở 540p, ước tính 2–3 tiếng cho bản 1080p. Máy RTX 5060 dựng 75–94 khung/giây ở 1080p, xong trong 2,8 phút.

Ngách vẽ 2D (như ngách này: nhân vật vector, đội hình, nền mờ) phần lớn do bộ xử lý vẽ. Card giúp ít hơn, nhưng máy bàn nhiều nhân vẫn nhanh hơn cloud vài lần.

## Khi nào hỏi
Ở **Bước 1 (Nhận đầu vào)**, hỏi chung với các câu khác (AskUserQuestion):

> Dựng bản cuối ở đâu?
> - **Card đồ hoạ trên máy bạn (khuyên dùng nếu máy có card rời):** nhanh, chỉ vài phút. Cần máy đang mở, đang liên kết với Claude, và bạn bấm đúp 1 file `.bat`.
> - **Cloud:** không cần máy của bạn, nhưng chậm (khoảng 3–5 phút cho mỗi phút video 1080p, cảnh 3D lâu hơn).

Không có thư mục nào trên máy người dùng được kết nối (không có công cụ `device_*`) thì chỉ dựng được trên cloud. Báo người dùng một dòng.

Người dùng vắng mặt (chạy theo lịch) thì dùng cloud và ghi rõ giả định.

## Phần nào làm ở đâu
| Việc | Nơi làm |
|---|---|
| Cài studio, dự án, voice, lên cảnh, ảnh tổng hợp, xem trước 30 giây | **Cloud.** Claude chỉ nhìn được ảnh trên cloud. |
| Trộn âm thanh (`mix.py`) | Cloud. `goi_may.py` tự làm. |
| Thumbnail | Cloud (`--thumb`), rồi chép về thư mục dự án. |
| **Bản cuối (vẽ từng khung + mã hoá)** | **Máy người dùng, bằng card đồ hoạ.** |
| Ghép hình + tiếng | Máy người dùng (file `.bat` tự làm). |

## Cách làm (sau khi người dùng duyệt bản xem trước)
1. Đóng gói, chạy trong `h2-2d-studio/` trên cloud:
   ```bash
   python tools/goi_may.py --project projects/<slug> --out /mnt/user-data/outputs/<slug>-may
   ```
   - Tự trộn âm thanh nếu chưa có `build/mix.wav`. Sửa shots/âm thanh sau khi trộn thì thêm `--remix`.
   - Ra các file `<slug>-may-1.zip` (2, 3…), mỗi file tối đa 25 MB, cùng `DUNG-VIDEO-<SLUG>.bat` và `_ghep-<slug>.ps1`.
2. Chép **tất cả** file trong `<slug>-may/` cùng thumbnail vào thư mục dự án trên máy người dùng bằng `device_commit_files`. Thư mục dự án là nơi có file kịch bản 01–05. Mỗi lần chép tối đa 50 file, mỗi file tối đa 30 MB.
3. Báo người dùng bằng lời đơn giản: "Mở thư mục dự án, bấm đúp **DUNG-VIDEO-<SLUG>.bat**, đừng tắt cửa sổ đến khi hiện chữ XONG."
   - Lần đầu, file `.bat` tự cài Node.js và ffmpeg qua winget nếu máy chưa có. Máy có thể hỏi quyền quản trị, bảo người dùng bấm Yes.
   - Bộ dựng nằm chung ở `%LOCALAPPDATA%\h2-2d-studio-gpu` cho mọi ngách. Lần sau `npm install` chỉ mất vài giây.
   - Trình vẽ là Edge có sẵn trên Windows. Mở không được thì thử Chrome, rồi tới Chromium. **Không** chạy `npx playwright install` vì lệnh này có thể treo trên Windows.
4. Theo dõi: cứ 30–60 giây gọi `device_stage_files` để chép `render-log.txt` từ thư mục dự án lên cloud, rồi đọc phần cuối file.
   - Dòng `Card do hoa dang dung: ANGLE (NVIDIA ...)`, `(AMD ...)` hoặc `(Intel ...)` là đang dùng card. Dòng `SwiftShader` là KHÔNG dùng được card.
   - Dòng `xxx/yyy khung  zz khung/giay ... con lai ~n phut` là tiến độ. Báo người dùng thời gian còn lại.
   - Dòng `XONG` là đã xong. Dòng `LOI` là có lỗi: đọc log, sửa, đóng gói lại.
5. Kiểm tra: `device_list_dir` thấy file `<tiêu đề>.mp4`. Chép nó lên cloud (tối đa 400 MB), chạy `ffprobe` xem có hình và tiếng, thời lượng khớp voice, rồi rút 4 khung ra xem.
6. Báo người dùng: tên file, thời lượng, tốc độ và thời gian dựng. Liệt kê những file có thể xoá: các `*-may-*.zip`, `.bat`, `.ps1`, `render-log.txt`.

## Xử lý sự cố
| Hiện tượng | Cách xử lý |
|---|---|
| Đứng ở bước cài Node/ffmpeg | Winget đang chờ bấm đồng ý (cửa sổ quyền quản trị ẩn sau). Bảo người dùng tìm cửa sổ đó, bấm Yes. |
| Log ghi `khong mo duoc msedge/chrome/chromium` | Máy thiếu cả Edge lẫn Chrome. Bảo cài Chrome rồi bấm đúp lại. |
| Tốc độ dưới 10 khung/giây, log ghi SwiftShader | Card không được dùng. Bảo cập nhật driver card đồ hoạ. Laptop thì cắm sạc và chọn chế độ hiệu năng cao. Hoặc chuyển sang cloud. |
| Log ghi `[404]` hoặc `Failed to load resource` | Bình thường. Đó là file không cần dùng tới. Bỏ qua. |
| Có `LOI` sau dòng render | Đọc lỗi trong log. Thường do thiếu file trong zip: đóng gói lại, chép lại, bấm đúp lại. |
| Sửa vài cảnh sau khi đã dựng | Sửa trên cloud, chạy lại `goi_may.py`, chép lại các zip, bấm đúp lại. Không cần cài gì thêm. |

## Ảnh hưởng
- Hình giống bản cloud, vì cùng một mã vẽ. Bản dùng card bật khử răng cưa (`aa`) nên cạnh mượt hơn.
- Trong lúc dựng, máy chạy hết công suất vài phút. Không chơi game hay dựng video khác cùng lúc. Laptop sẽ nóng lên.
- Máy tắt, ngủ hoặc mất liên kết thì không theo dõi được. Bảo người dùng bấm đúp lại, việc dựng chạy lại từ đầu.

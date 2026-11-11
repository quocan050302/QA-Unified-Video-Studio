# Luật hình ngách Self-Improvement (bộ `dem`)

Học từ các kênh "An Animated Short Film" dẫn đầu ngách. Chỉ học **phong cách và nhịp**, mọi hình đều do code của mình vẽ.

## Cấu hình dự án
- `config.json`: `"pack": "dem"`, `"style": "flat"`, `"accent": "red" | "pink" | "amber" | "teal"` (lấy từ file 01).
- 16:9 tự có **dải đen điện ảnh 2.39:1** (`"bars": "scope"`). Mọi chữ, bộ đếm tự nằm trong vùng hình. Muốn bỏ: `"bars": "none"`.
- 9:16: không dải đen, chữ to hơn, nhân vật đặt giữa (`x` 0.35–0.65).

## Màu và nét
- Nền rất tối (#141418 → #1d1e24). Đồ vật tô phẳng xám xanh tối, **nét viền mảnh màu sáng** (#c9ccd4). Không viền đen dày.
- Nhân vật màu kem #ece6d6, nét xám mảnh, bóng mềm nửa sau.
- Ánh sáng là các vầng tròn mềm: đèn bàn vàng, màn hình xanh, trăng, cửa neon. Mỗi cảnh **1 nguồn sáng chính**.
- **Màu nhấn chỉ dùng cho:** bóng đen cám dỗ, chữ cám dỗ, số bộ đếm sau khi sụp, gạch chân thẻ kết, dòng phụ 2 thẻ kết, băng đô khi tập. Không tô màu nhấn lên vật khác.

## Nhân vật
- Nhân vật chính giống đối thủ: **đầu tròn trơn màu kem, không tóc, không đội gì trên đầu**. `hoodie` là mũ hạ sau cổ; chỉ dùng `hooded` (trùm mũ) khi cảnh thật sự cần.
- Đề tài thức đêm / nghiện / kiệt sức: dùng mắt đỏ gân máu (`face: "bloodshot"` hoặc `"bloodshot": true`) ở các cảnh đáy và cận mặt, giống thumbnail.
- Nhân vật chính 1 preset suốt phim: `hoodie` (nghiện, đêm), chuyển `band` khi bắt đầu tập luyện (nhịp đứng lên) — đó là dấu hiệu thay đổi. Hoặc `hero` trần cho đề tài kỷ luật.
- **Bóng đen (`voice`)**: luôn cao hơn nhân vật chính một chút, đứng sau / cạnh / ngồi trên giường, cười (`grin`). Nhịp sa ngã: to, gần, tay đặt lên vai (`reach`). Nhịp đứng lên: nhỏ dần (`scale` 0.8 → 0.5), mờ dần (`out`), cuối cùng vỡ (`fx: shards` + `glass_shatter`).
- Bạn bè đội mũ màu, cô gái tóc bob khăn vàng: chỉ xuất hiện ở khoảnh khắc người thật (bước ngoặt), luôn trong ánh sáng ấm.

## Bố cục
- Nhân vật chính ở 1/3 trái hoặc phải, không đứng chính giữa trừ cảnh cô đơn (`void`, `hill`).
- Chữ kể chuyện ở trên, không đè lên mặt. Nếu đè, đặt `pos: "bottom"`.
- Chữ cám dỗ cạnh bóng đen, không đè lên mặt nhân vật chính.
- Bộ đếm luôn ở góc trên trái, cùng cỡ, cùng chỗ suốt phim.

## Máy quay và nhịp
- **Mọi cảnh đều có chuyển động**: đẩy chậm (`cam` zoom 1.0 → 1.1–1.3), nhân vật thở / chớp mắt (tự động), bóng đen nhịp sáng, chữ gõ.
- Cảnh 3–8 giây; montage (lịch, bộ đếm chạy, chạy bộ) 4–6 giây; khoảnh khắc lặng 4–6 giây trên nền đen hoặc cận mặt.
- Lặp lại **cùng một bố cục phòng ngủ** 4–8 lần trong phim, chỉ đổi giờ đồng hồ, lịch, ánh sáng, vị trí bóng đen → người xem thấy thời gian trôi.
- Cắt cứng là chính. `dip` (mờ đen 0,5–0,7 giây) giữa các nhịp lớn. `flash` 1 lần ở bước ngoặt.

## Cận cảnh
- Điện thoại: chiếm gần hết chiều cao, 2 tay cầm, chữ kể chuyện tự đặt bên phải. Feed lướt nhanh cho "nghiện", chat cho "người thật", email cho "cái giá".
- Đồng hồ / lịch: dùng cho thời gian trôi và cú sụp (`timeAt`, `reset`).
- Cận mặt: dùng 2–4 lần mỗi phim, ở câu đau nhất và lúc quyết định.

## Nội dung nhạy cảm
- Lust: chỉ màn hình phát sáng, khối màu mờ, bóng neon. Không vẽ cơ thể, không chữ thô.
- Tự hại / tự tử: không minh hoạ thuốc, dao, độ cao, dây. Chọn hình ẩn dụ (bóng tối, căn phòng trống) và luôn kết bằng ánh sáng, người thật.

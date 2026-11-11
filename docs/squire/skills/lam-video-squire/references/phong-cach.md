# Phong cách hình: hoạt hình vector lịch sử quân sự

Học từ kênh dẫn đầu ngách: hoạt hình vector cắt lớp, nhân vật đầu tròn trắng, viền nâu đen dày, màu phẳng có một tầng bóng, nền mờ sâu kiểu máy ảnh. Người xem **là** người lính trong truyện ("you"), nên hình luôn bám một nhân vật chính đi qua từng chặng.

## Nguyên tắc
1. **Nhân vật "YOU" là trục.** Mỗi chặng (thời kỳ, tuyến quân) có một nhân vật chính mặc đúng trang phục chặng đó. Lần đầu xuất hiện gắn biển `YOU` (`signs`). Nhân vật này chiếm 50–70% số cảnh.
2. **Nói gì vẽ nấy.** "your armour is a shirt of little iron rings" → cận giáp lưới. "The wall doesn't move" → đội hình khiên. "He pushes up his helmet" → cận mặt, `poseAt` đổi tư thế.
3. **Chiều sâu kiểu máy ảnh:**
   - Nền luôn mờ (`blur` 5–7 px với `scene`, 12–14 px với `close` và `item`).
   - Đám đông phía sau đặt trong `back` (bị mờ cùng nền).
   - Tiền cảnh có thể thêm 1–2 lính đứng che góc trong `front` (mờ, to) cho cảnh nhìn qua vai.
4. **Ánh sáng theo giờ** (`time`): `day`, `sunset`, `golden` (La Mã, sa mạc, bụi), `dusk`, `storm` (mưa), `night`, `dawn`. Cả một chặng giữ cùng một `time` để liền mạch; đổi `time` khi truyện đổi giờ (sáng → tối sau trận).
5. **Nhân vật:**
   - Đầu tròn trắng to, mắt chấm, lông mày nét, má hồng khi vui, râu nâu khi già.
   - Biểu cảm đổi theo lời (`faceAt`): sợ, ngạc nhiên, cáu, chán, mệt, khóc, cười.
   - Nhân vật nói (vua, tướng, thầy tu) bật `talk: true`.
   - Không vẽ mặt người thật; vua chúa, tướng lĩnh chỉ nhận ra qua trang phục, vương miện, huy hiệu.
6. **Huy hiệu là màu đội.** Phe ta và phe địch phải khác màu khiên/áo choàng rõ ràng (ví dụ ta vàng-sư tử đỏ, địch xanh-hoa huệ vàng; La Mã đỏ, Latin xanh). Giữ cố định suốt video, ghi vào `story/bible.md`.
7. **Sơ đồ cho chiến thuật.** Khi lời giải thích cách quân di chuyển ("cut into fifteen blocks, with small gaps") thì dùng `top` (nhìn từ trên, khối quân chạy) hoặc `plan` (khối chữ nhật trên giấy) với mũi tên đỏ. Cứ 60–90 giây nên có 1 cảnh sơ đồ ở đoạn chiến thuật.
8. **Bản đồ giấy da** (`map`) khi nhắc tới nơi chốn, đường hành quân. Bảng phấn (`board`) cho so sánh số đo. Màn soi xanh (`xray`) cho vết thương, bên trong cơ thể.
9. **Chữ trên hình rất ít.** Video dài không có phụ đề. Chỉ có biển chữ giấy kem IN HOA (`signs`: tên phe, "YOU", tên nơi) và thỉnh thoảng chữ to kiểu thumbnail (`labels`) cho từ khoá. Tối đa 1–2 chữ mỗi cảnh.
10. **Nhịp cắt** (đo từ kênh mẫu):
    - Video dài: 13–22 cảnh mỗi phút, trung vị 2,4 giây. `draft_shots --min 1.4 --max 3.8`.
    - Short: 29–38 cảnh mỗi phút, trung vị 1,5 giây. `draft_shots --min 0.8 --max 2.6`.
    - Cao trào trận đánh cắt nhanh hơn; cảnh hoàng hôn sau trận giữ lâu (5–8 giây).
11. **Đi lại phải chạm đất:** ai di chuyển thì dùng `walk: true` hoặc `from`/`to` (không tự trượt nhân vật bằng `enter`/`exit` khi họ đang đi bộ). Đội hình đi ngang dùng `advance`, đi về phía máy quay dùng `march`. Ngựa dùng `gait: walk/gallop`. Kênh mẫu cho nhân vật đi qua khung chứ không đứng bước tại chỗ.
12. **Chuyển động trong cảnh:** máy đẩy chậm (`move: in`, `moveAmt` 0.03–0.05) hoặc lia ngang đội hình (`move: left/right`); nhân vật chớp mắt, thở, nhép miệng tự động; lính hành quân (`march`), ngựa phi (`gait: gallop`), mưa, mưa tên (`fx`), khói, bụi. Rung máy (`shake`) khi va chạm lớn.
13. **Chuyển cảnh:** cắt thẳng là chính. `fade` khi đổi thời kỳ hoặc sang ngày mới.

## Bảng màu chính (`PAL`)
- Viền: nâu đen `#392a21`. Da: kem `#f4ede1`, bóng tím xám.
- Kim loại: thép `#b9b5b3` / tối `#8f8986`; giáp lưới `#9a938f`; đồng `#d3a24e`; vàng `#e7b04a`.
- Huy hiệu: đỏ `#c9473a`, xanh `#3e64a3`, vàng `#efc23f`, xanh lá `#5d7f3a`, trắng `#f7f3ea`.
- Đất: cỏ `#86a046`, bùn `#6e5038`, cát vàng bụi `#b8a35e`; giấy da `#e9d8ad`.

## Short 9:16
- Chủ thể ở giữa, đầu nhân vật ở 25–45% chiều cao khung; không đặt gì quan trọng ở dải 60–72% (phụ đề).
- Nhân vật cao `h` 0.32–0.42; cận mặt `R` 0.11–0.14.
- Phụ đề bật sẵn: 1–3 chữ IN HOA trắng siêu đậm, viền đen, ở 66% chiều cao.
- `split` chỉ dùng cho 16:9; Short thì dùng 2 cảnh `close` nối nhau.

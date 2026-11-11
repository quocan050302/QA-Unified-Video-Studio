# Thumbnail: ảnh AI liền khối + chữ code

Thumbnail của ngách **khác hẳn hình trong video**: video là vector phẳng nét mảnh, còn thumbnail là **tranh hoạt hình nét đậm, đổ bóng mềm, ánh sáng điện ảnh, nền gần đen**.

- **AI vẽ cả cảnh**: nhân vật + vật chính + nguồn sáng + nền, trong một ảnh liền khối.
- **Code chỉ vẽ chữ**: 1–4 từ IN HOA trắng rất đậm, viền đen, bóng đổ, nằm trên cùng. Mọi prompt đều ghi "No text".
- **Giữ nhân vật giống nhau qua mọi video**: tạo ảnh nhân vật mẫu `T00` **một lần**, lưu lại, mỗi lần tạo thumbnail gắn T00 làm ảnh tham chiếu (Flow: Ingredients / thêm ảnh với Nano Banana).

## Công thức một thumbnail ăn khách
1. **Chữ** 1–4 từ, kết bằng `.` (mệnh lệnh / khẳng định: "WAKE UP.", "STAY.", "LOG OFF.") hoặc `?` ("WHAT IF?", "WHY NOT ME?"). Chữ là câu của cám dỗ, của nhân vật, hoặc cái giá — **không** lặp lại tiêu đề.
2. Có thể **đổi màu 1 từ** sang màu nhấn ("JUST ONE / MORE.") hoặc **gạch xoá một số** ("DAY 412 0.").
3. **Biểu cảm cực mạnh**: sợ, tuyệt vọng, gồng sức, giận dữ quyết tâm, khóc.
4. **Một vật kể chuyện** + **một nguồn sáng**: điện thoại phát sáng, đồng hồ 5:00 đỏ, đèn bàn, cửa neon, ánh tuyết.
5. Nhân vật to, cận từ ngực trở lên, chiếm nửa dưới. **Trên cùng 25% để trống, tối** cho chữ.
6. Bóng đen cám dỗ (nếu có) đứng sau / bên cạnh, cười, viền neon.

## NHÂN VẬT CỐ ĐỊNH (dán vào mọi prompt thumbnail)
```
MAIN CHARACTER (always identical): a simple cartoon young man with a big perfectly round bald head in warm cream color, no hair, no ears, no nose, large round white eyes with small black pupils and dark reddish eye bags, thin dark eyebrows, small expressive mouth, smooth cream skin with soft cel shading, simple rounded body and mitten-like hands, wearing a plain charcoal-grey hoodie with the hood down.
```
Biến thể khi cần (thay câu cuối): "shirtless, sweaty, with a red headband" (tập luyện) · "with the dark hood up" (đêm, nghiện).

**MẮT ĐỎ GÂN MÁU** (đề tài thức đêm, nghiện điện thoại / porn, kiệt sức, sợ hãi — thêm câu này sau NHÂN VẬT CỐ ĐỊNH):
```
His eyes are bloodshot: pinkish-red whites with thin red veins, tiny shrunken pupils, heavy dark purple bags under the eyes.
```
Đề tài kỷ luật / quyết tâm thì bỏ câu này, giữ mắt trắng.

**BÓNG ĐEN CÁM DỖ** (thêm khi cảnh có cám dỗ):
```
THE VOICE: a tall pitch-black shadow figure with the same round head, featureless except glowing crescent eyes and a wide glowing grin, outlined by a thin neon <ACCENT> rim light with a soft neon glow.
```
`<ACCENT>` thay bằng màu nhấn của phim: red / hot pink / amber / teal.

## KHOÁ PHONG CÁCH THUMBNAIL (dán cuối mọi prompt thumbnail)
```
Dramatic cartoon illustration for a YouTube thumbnail. Clean bold black outlines, smooth cel shading with soft gradients, cinematic lighting from one strong light source, deep near-black background with very high contrast, saturated color only in the light and glow, crisp digital finish (NOT flat vector, NOT anime, NOT realistic, NOT watercolor, no paper texture). Wide 16:9, the character large and close to the camera from the chest up, filling the lower 70% of the frame; keep the top 25% dark and empty for a title. No text, no letters, no numbers, no watermark, no logo, no gore.
```

## Ảnh nhân vật mẫu T00 (tạo 1 lần, dùng mãi)
```
### T00 | NHÂN VẬT MẪU
Character reference sheet on a plain dark grey background: the same character shown three times side by side, front view, three-quarter view and side view, neutral expression, full upper body. <NHÂN VẬT CỐ ĐỊNH> Bold cartoon, clean black outlines, soft cel shading, no text.
```

## Định dạng file `03-THUMB-PROMPT-<slug>.txt`
```
### T01 | WAKE UP. | đồng hồ 5:00 đỏ
The character lying in a dark bed, face half-buried in the pillow, one eye wide open in panic, reaching toward a glowing red digital alarm clock showing 5:00 on the nightstand; red light spilling across his face, cold blue moonlight from a window behind. <NHÂN VẬT CỐ ĐỊNH> <KHOÁ PHONG CÁCH THUMBNAIL>
```
- Dòng tiêu đề: `### T0x | <CHỮ THUMBNAIL> | <ghi chú ngắn>`.
- Thân prompt tiếng Anh 2–3 câu: tư thế, biểu cảm, vật chính, nguồn sáng, nền. Rồi **chép đầy đủ** NHÂN VẬT CỐ ĐỊNH (+ BÓNG ĐEN nếu cần) và KHOÁ PHONG CÁCH.
- Chủ đề lust: người phụ nữ **chỉ** là đường viền neon mờ, không chi tiết cơ thể ("only a faint glowing neon outline silhouette of a woman, no details, fully non-explicit").
- Không minh hoạ tự hại, thuốc, vũ khí, máu.

## Hướng dẫn người dùng (in cuối file 03)
1. Lần đầu: tạo `T00` (Flow → Images, Nano Banana / Imagen, 16:9 hoặc 1:1). Chọn ảnh đẹp nhất, lưu lại làm ảnh tham chiếu dùng mãi.
2. Mỗi video: dán prompt T01 (và T02, T03 nếu muốn thử), **gắn ảnh T00 làm ảnh tham chiếu**, tạo 2–4 ảnh, chọn ảnh có mặt nhân vật rõ, nền tối, trên cùng trống.
3. Đặt tên file bằng mã (`T01.png`) rồi đưa cho `/lam-video-selfimprove`. Code sẽ đặt chữ đúng font, đúng màu.
4. Ảnh có chữ lạ, logo hoặc nhân vật lệch mẫu thì tạo lại.

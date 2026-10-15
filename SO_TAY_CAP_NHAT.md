# SỔ TAY HƯỚNG DẪN CẬP NHẬT CODE & QUẢN TRỊ HỆ THỐNG APP CHUNG

> **Tài khoản PythonAnywhere:** `rappervint`  
> **Tên miền web:** `https://rappervint.pythonanywhere.com`  
> **Kho GitHub:** `https://github.com/rappervint/appchung`  
> **Thư mục code trên máy tính:** `E:\appchung`

---

## I. QUY TRÌNH SỬA CODE / THÊM APP HẰNG NGÀY (CHỈ MẤT 10 GIÂY)

Từ nay, bạn **KHÔNG BAO GIỜ** cần xóa Web, không cần nén ZIP tải lên tải xuống nữa. 
Mỗi khi bạn sửa giao diện, sửa tính năng hoặc nhờ AI viết thêm code, bạn chỉ cần làm đúng **2 bước** sau:

### BƯỚC 1: Đẩy code mới từ máy tính lên GitHub
Trong VS Code, bạn mở cửa sổ Terminal / PowerShell (phím tắt `Ctrl + ~`), gõ 3 dòng:

```powershell
git add .
git commit -m "Ghi chu noi dung ban vua sua"
git push
```
*(Code mới trên máy bạn đã bay thẳng lên kho GitHub an toàn)*

---

### BƯỚC 2: Cập nhật lên web PythonAnywhere
1. Đăng nhập vào [PythonAnywhere.com](https://www.pythonanywhere.com).
2. Vào menu **Consoles** -> Bấm vào **Bash** (hoặc mở cửa sổ Bash đang có sẵn).
3. Gõ đúng 2 dòng:
   ```bash
   cd ~/appchung
   git pull
   ```
4. Sang tab **Web** -> Bấm nút to màu xanh: **"Reload rappervint.pythonanywhere.com"**.

👉 **Xong!** Mở trang web `https://rappervint.pythonanywhere.com` lên thưởng thức bản mới!

---

## II. DỮ LIỆU BÁN HÀNG, BÁO CÁO, THU CHI CÓ BỊ MẤT KHÔNG?

> **TRẢ LỜI: HOÀN TOÀN KHÔNG BỊ MẤT!**

Hệ thống đã được thiết lập file bảo vệ `.gitignore`:
- Các file cơ sở dữ liệu (`tiem_lap_do.db`, `doanhthu_den.db`, `finance.db`) đang chạy trên PythonAnywhere sẽ **không bao giờ bị ghi đè hay bị xóa** khi bạn chạy lệnh `git pull`.
- Khách hàng hay nhân viên nhập đơn bán hàng, ghi sổ thu chi trên web trực tuyến vẫn còn nguyên 100%.

---

## III. NẾU SAU NÀY BẠN MUỐN THÊM MỘT ỨNG DỤNG MỚI NỮA THÌ SAO?

Hệ thống đã có sẵn kiến trúc cắm rút tự động (Plug-and-play). Bạn có 2 cách cực dễ:

### Cách A: Dùng nút bấm trên giao diện web (Siêu nhanh)
1. Vào trang chủ cổng tổng: `https://rappervint.pythonanywhere.com`
2. Bấm vào nút màu xanh **+ Thêm App Mới** ở góc phải trên.
3. Điền:
   - **Mã định danh App:** vd `kho`
   - **Tên hiển thị:** vd `Quản Lý Kho Hàng`
   - **Đường dẫn URL:** vd `/kho/`
   - **Mô tả:** vd `Theo dõi nhập xuất tồn kho`
   - **Icon:** vd `fas fa-boxes` (hoặc icon tùy thích)
4. Bấm **Tạo App Ngay**. Hệ thống sẽ tự động tạo thư mục `app_kho` với đầy đủ code mẫu, menu và tự nạp vào trang chủ!

### Cách B: Tạo thư mục thủ công trên máy tính
1. Trong thư mục `E:\appchung`, copy thư mục mẫu `app_mau` thành tên mới, ví dụ: `app_nhanvien`.
2. Mở file `apps_config.json`, thêm 1 dòng khai báo app mới.
3. Đẩy code lên GitHub (`git add .` -> `git commit` -> `git push`).
4. Lên PythonAnywhere kéo về (`git pull`) rồi bấm **Reload Web** là xong!

---

## IV. BẢNG TRA CỨU CÁC LỖI THƯỜNG GẶP & CÁCH SỬA

| Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Gõ `git push` báo `fatal: Authentication failed`** | GitHub đổi mật khẩu hoặc cần xác thực | Trong VS Code sẽ hiện hộp thoại "Sign in with browser", chỉ cần bấm vào đó để đăng nhập lại là xong. |
| **Gõ `git pull` trên PythonAnywhere báo `Password for ...`** | Kho GitHub đang bị đổi sang Private | Vào GitHub -> `Settings` -> Kéo xuống dưới cùng -> chọn `Change visibility` -> Đổi sang `Public`. |
| **Web PythonAnywhere báo "Something went wrong" (Lỗi 500)** | Có lỗi cú pháp trong file code Python vừa sửa | Vào tab **Web** trên PythonAnywhere -> kéo xuống mục **Log files** -> bấm vào link **Error log** để xem dòng code nào bị lỗi. |
| **Chạy app nội bộ trên máy tính (offline)** | Cần chạy mạng nội bộ trong tiệm không có mạng internet | Click đúp vào file `Chay_App_Chung.bat` tại `E:\appchung`. App sẽ mở bằng địa chỉ `http://appchung.local:5000` hoặc IP của máy. |

---
*Tài liệu này được lưu trực tiếp tại file: `E:\appchung\SO_TAY_CAP_NHAT.md` để bạn mở ra xem bất cứ lúc nào!*


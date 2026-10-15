# HƯỚNG DẪN: SỬA CODE & THÊM ỨNG DỤNG MỚI (KHÔNG CẦN XÓA WEB)

Hệ thống **TRẦN BÌNH AUTO** hiện tại đã được nâng cấp lên **Kiến trúc phân hệ động (Dynamic Apps)**. Bạn có thể thêm 5, 10 hay bao nhiêu app tùy thích vào hệ thống mà **tuyệt đối KHÔNG BAO GIỜ cần xóa web app** trên PythonAnywhere!

---

## PHẦN 1: CÁCH SỬA CODE BẰNG VS CODE & CẬP NHẬT LÊN PYTHONANYWHERE

Khi bạn cùng Antigravity sửa code trên máy tính (sửa tính năng, thêm giao diện, chỉnh sửa bảng giá...), bạn chỉ cần làm 2 bước cực kỳ nhanh:

### Bước 1: Nén các file đã sửa
- Nếu chỉ sửa 1 hoặc vài file (ví dụ file `app.py` hoặc file `index.html`), bạn chỉ cần nén đúng các file đó thành file `update.zip`.
- Hoặc bạn có thể nén toàn bộ thư mục `appchung` thành `appchung.zip` như trước.

### Bước 2: Tải lên và kích hoạt (Mất 15 giây)
1. Vào tab **Files** trên PythonAnywhere ➔ Bấm **Upload a file** để tải `appchung.zip` (hoặc `update.zip`) lên.
2. Sang tab **Consoles** ➔ Mở **Bash**, gõ lệnh giải nén đè:
   ```bash
   unzip -o appchung.zip -d appchung
   ```
3. Chạy lệnh kích hoạt ngay trong Bash:
   ```bash
   touch /var/www/rappervint_pythonanywhere_com_wsgi.py
   ```
   *(Hoặc vào tab **Web** bấm nút xanh **Reload**)*.

👉 **Xong ngay lập tức!** Mọi dữ liệu bán hàng, doanh thu và thu chi trong các file SQLite (`.db`) vẫn **giữ nguyên vẹn 100%**, không bị mất mát hay xáo trộn.

---

## PHẦN 2: CÁCH DÙNG NÚT "➕ THÊM PHÂN HỆ MỚI" TRÊN GIAO DIỆN WEB

Ngay trên giao diện Trang Chủ Hub ([**https://rappervint.pythonanywhere.com**](https://rappervint.pythonanywhere.com) hoặc `http://localhost:5000`):

1. Bấm vào nút **"➕ Thêm Phân Hệ Mới"** (ở đầu trang hoặc thẻ cộng ở cuối danh sách).
2. Một bảng hiện ra, bạn chỉ cần điền:
   - **Tên Ứng Dụng**: Ví dụ `Quản Lý Bảo Dưỡng`, `Chấm Công Nhân Viên`, `Khách Hàng CRM`...
   - **Mã Định Danh (ID)**: Hệ thống sẽ tự động tạo từ không dấu (ví dụ: `baoduong`, `chamcong`). Đường dẫn web sẽ là `/baoduong/`.
   - **Biểu tượng (Icon)**: Chọn hình cờ lê, xe ô tô, lịch hẹn, ví tiền...
   - **Màu sắc**: Chọn màu xanh lá, vàng cam, tím, xanh dương...
   - **Mô tả & Tính năng**: Gõ vài dòng giới thiệu phân hệ.
   - **Tải lên mã nguồn .zip (Tùy chọn)**: Nếu bạn đã viết sẵn app thì upload file zip lên; nếu chưa có thì hệ thống sẽ **tự động sao chép từ khung mẫu `app_mau`** tạo ra ngay 1 app hoàn chỉnh cho bạn!
3. Bấm **"Tạo Phân Hệ Ngay"**:
   - Thẻ app mới sẽ xuất hiện ngay lập tức trên màn hình chính!
   - Ứng dụng mới hoạt động độc lập với cơ sở dữ liệu SQLite riêng, không sợ ảnh hưởng đến các app khác.

---

## PHẦN 3: CÁCH THÊM APP BẰNG ANTIGRAVITY TRÊN VS CODE

Nếu bạn muốn yêu cầu Antigravity viết 1 ứng dụng mới hoàn chỉnh (ví dụ: *"Tạo cho tôi app Quản Lý Lịch Hẹn Bảo Dưỡng"*):

1. **Antigravity sẽ tạo một thư mục mới** dạng `app_<tên_app>` (ví dụ `app_baoduong`) trong thư mục `E:\appchung`.
2. **Khai báo vào file `apps_config.json`**:
   Chỉ cần thêm 1 đoạn cấu hình vào `apps_config.json`:
   ```json
   {
     "id": "baoduong",
     "name": "Lịch Hẹn Bảo Dưỡng",
     "prefix": "/baoduong",
     "module": "app_baoduong",
     "blueprint_var": "baoduong_bp",
     "desc": "Theo dõi lịch hẹn thay dầu, bảo dưỡng định kỳ cho khách.",
     "icon": "bi-calendar-check",
     "theme_color": "blue",
     "status": "active",
     "features": [
       "Nhắc lịch bảo dưỡng tự động",
       "Quản lý trạng thái tiếp nhận xe"
     ]
   }
   ```
3. Sau đó bạn chỉ cần tải lên PythonAnywhere và bấm **Reload** là phân hệ mới tự động chạy, không cần cấu hình lại WSGI!


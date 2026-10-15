# HƯỚNG DẪN TỪ A-Z: XÓA APP CŨ VÀ CÀI ĐẶT LẠI TRÊN PYTHONANYWHERE (HỢP NHẤT 3 ỨNG DỤNG)

Hệ thống hợp nhất **3 ứng dụng trong 1** của bạn gồm:
- 🏠 **Trang chủ chọn App**: `https://<ten_tai_khoan>.pythonanywhere.com/`
- 📦 **Bán Hàng & Kho**: `https://<ten_tai_khoan>.pythonanywhere.com/banhang/`
- 💡 **Báo Cáo Doanh Thu Đèn**: `https://<ten_tai_khoan>.pythonanywhere.com/den/`
- 💰 **Sổ Quản Lý Thu Chi**: `https://<ten_tai_khoan>.pythonanywhere.com/thuchi/`

---

## PHẦN 1: DỌN DẸP SẠCH SẼ APP CŨ TRÊN PYTHONANYWHERE

Để tránh bị lỗi lồng thư mục hoặc xung đột mã nguồn cũ, hãy làm sạch tài khoản trước:

### Bước 1.1: Xóa Web App cũ
1. Đăng nhập vào [pythonanywhere.com](https://www.pythonanywhere.com/).
2. Vào tab **Web** trên thanh menu trên cùng.
3. Cuộn xuống cuối trang, nhìn vào nút **Delete <ten_tai_khoan>.pythonanywhere.com** màu đỏ ➔ Bấm vào và chọn **OK** để xóa web app cũ đi.

### Bước 1.2: Xóa thư mục code cũ
1. Vào tab **Consoles** ➔ Chọn **Bash** (hoặc mở console có sẵn).
2. Dán lệnh này vào và nhấn **Enter** để xóa sạch thư mục cũ:
   ```bash
   rm -rf /home/rappervint/appchung /home/rappervint/appchung.zip
   ```
*(Sau lệnh này, tài khoản của bạn hoàn toàn sạch sẽ như mới).*

---

## PHẦN 2: NÉN FILE TRÊN MÁY TÍNH VÀ TẢI LÊN

### Bước 2.1: Nén file đúng cách (RẤT QUAN TRỌNG ĐỂ KHÔNG BỊ LỒNG THƯ MỤC)
1. Mở thư mục `E:\appchung` trên máy tính của bạn.
2. Nhấn tổ hợp phím **Ctrl + A** để chọn TẤT CẢ các thư mục và tệp bên trong:
   - `app_banhang`
   - `app_baocao_den`
   - `app_thuchi`
   - `templates`
   - `app.py`
   - `wsgi.py`
   - `requirements.txt`
   - `Chay_App_Chung.bat`
3. Nhấp **chuột phải** vào một tệp bất kỳ đã chọn ➔ Chọn **Send to** ➔ **Compressed (zipped) folder** (hoặc dùng WinRAR/7-Zip) ➔ Đặt tên file là `appchung.zip`.

### Bước 2.2: Tải lên và giải nén trên PythonAnywhere
1. Trên trang PythonAnywhere, vào tab **Files**.
2. Ở cột bên phải **Upload a file**, bấm **Choose File** ➔ Chọn file `appchung.zip` bạn vừa nén ➔ Bấm nút **Upload**.
3. Vào tab **Consoles** ➔ Mở **Bash** và chạy 2 lệnh sau:
   ```bash
   unzip appchung.zip -d appchung
   pip install -r appchung/requirements.txt
   ```
*(Đợi khoảng 30 giây đến 1 phút để giải nén và kiểm tra cài đặt thư viện)*.

---

## PHẦN 3: TẠO WEB APP MỚI VÀ CẤU HÌNH WSGI

### Bước 3.1: Tạo Web App mới
1. Vào tab **Web** trên thanh menu.
2. Bấm nút màu xanh **Add a new web app**.
3. Bấm **Next**.
4. Chọn **Manual configuration** *(Lưu ý: KHÔNG chọn Flask)*.
5. Chọn phiên bản Python: Chọn **Python 3.10**.
6. Bấm **Next** cho đến khi hoàn tất tạo Web App.

### Bước 3.2: Điền đường dẫn thư mục code
Cuộn chuột xuống phần **Code**:
- **Source code**: Điền chính xác:
  ```text
  /home/rappervint/appchung
  ```
- **Working directory**: Điền chính xác:
  ```text
  /home/rappervint/appchung
  ```

### Bước 3.3: Cấu hình file WSGI
1. Vẫn ở phần **Code**, nhìn vào mục **WSGI configuration file** ➔ Bấm vào đường link màu xanh dạng:
   `/var/www/rappervint_pythonanywhere_com_wsgi.py`
2. Trình soạn thảo file mở ra:
   - Nhấn **Ctrl + A** rồi bấm **Backspace / Delete** để xóa sạch toàn bộ nội dung mẫu có sẵn.
   - Dán chính xác đoạn mã sau vào:

```python
import sys
import os

# Thư mục gốc chứa dự án hợp nhất của bạn
path = '/home/rappervint/appchung'
if path not in sys.path:
    sys.path.insert(0, path)

os.chdir(path)

# Nạp ứng dụng Flask tổng hợp
from app import application
```

3. Bấm nút **Save** màu xanh lá ở góc trên bên phải để lưu.

---

## PHẦN 4: BẬT HTTPS & HOÀN TẤT

1. Quay lại tab **Web**.
2. Cuộn xuống phần **Security** ➔ Bật công tắc **Force HTTPS** sang **Enabled** (để có chứng chỉ bảo mật ổ khóa xanh SSL miễn phí).
3. Cuộn lên trên cùng ➔ Bấm nút to màu xanh lá cây **Reload rappervint.pythonanywhere.com**.
4. Truy cập ngay vào địa chỉ:
   👉 [**https://rappervint.pythonanywhere.com**](https://rappervint.pythonanywhere.com)

🎉 **Chúc mừng bạn! Cả 3 ứng dụng bây giờ đã chạy 24/7 mượt mà trên cùng một tên miền duy nhất.**

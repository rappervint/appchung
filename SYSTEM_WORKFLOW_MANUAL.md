# KIẾN TRÚC HỆ THỐNG VÀ QUY TRÌNH VẬN HÀNH APP CHUNG (SYSTEM BLUEPRINT & WORKFLOW MANUAL)
> **Dành cho:** Người dùng & AI Assistant (Antigravity) đọc hiểu và tái hiện chuẩn xác 100% mọi quy trình tích hợp, cấu hình và triển khai.
> **Ngày cập nhật:** 2026-10-15  
> **Người sở hữu:** `rappervint`  
> **Tên miền Online:** `https://rappervint.pythonanywhere.com`  
> **Kho lưu trữ GitHub:** `https://github.com/rappervint/appchung` (Public/Private repo)  
> **Thư mục Local:** `E:\appchung`

---

## I. TỔNG QUAN KIẾN TRÚC HỆ THỐNG (ARCHITECTURE OVERVIEW)

Hệ thống là một **Hub Flask Đa Ứng Dụng (Multi-Tenant Hub)** hoạt động theo mô hình Module hóa (Plug-and-play) thông qua Flask `Blueprint`.

```
E:\appchung\ (hoặc /home/rappervint/appchung)
│── app.py                   # Master Flask App, Dynamic Blueprint Loader, Hub APIs, mDNS
│── wsgi.py                  # Điểm khởi chạy WSGI cho PythonAnywhere
│── apps_config.json         # Danh mục cấu hình đăng ký các app con
│── requirements.txt         # Danh mục thư viện Python
│── Chay_App_Chung.bat       # Script khởi chạy mạng nội bộ offline (mDNS, LAN IP)
│── .gitignore               # CHẶN đẩy các file *.db, *.zip, __pycache__ lên GitHub
│── templates\
│   └── portal.html          # Giao diện Cổng Tổng (Hub Portal) & Modal thêm app
│── app_mau\                 # Thư mục APP MẪU CHUẨN để clone khi tạo app mới
│   ├── __init__.py
│   ├── app.py               # Blueprint mẫu
│   └── templates\mau_index.html
│── app_banhang\             # App 1: Bán hàng (URL: /banhang/) -> DB: tiem_lap_do.db
│── app_baocao_den\          # App 2: Báo cáo đèn (URL: /den/) -> DB: doanhthu_den.db
│── app_thuchi\              # App 3: Quản lý Thu chi (URL: /thuchi/) -> DB: finance.db
└── SO_TAY_CAP_NHAT.md       # Sổ tay tóm tắt nhanh cho người dùng
```

---

## II. QUY TẮC CƠ SỞ DỮ LIỆU & AN TOÀN DỮ LIỆU (DATABASE SAFETY)

1. **Vị trí các file Database SQLite:**
   - App Bán hàng: `app_banhang/tiem_lap_do.db`
   - App Báo cáo đèn: `app_baocao_den/doanhthu_den.db`
   - App Quản lý Thu chi: `app_thuchi/finance.db`
2. **Nguyên tắc bảo vệ dữ liệu:**
   - File `.gitignore` đã chặn mọi file `*.db`.
   - Khi đẩy code từ máy lên GitHub (`git push`) hay kéo code về máy chủ (`git pull`), **tất cả file SQLite `.db` trên PythonAnywhere KHÔNG BAO GIỜ BỊ GHI ĐÈ HAY XÓA**.
   - Dù người dùng có xóa sạch file `.db` trên máy tính `E:\`, dữ liệu thực tế đang chạy trên PythonAnywhere vẫn an toàn tuyệt đối.
3. **Sao lưu Database về máy tính:**
   - Vào PythonAnywhere -> tab **Files** -> vào thư mục app -> bấm vào file `.db` để tải về máy tính lưu trữ dự phòng.

---

## III. QUY TRÌNH NẠP / THÊM MỘT APP MỚI VÀO CỔNG TỔNG (HOW TO ADD A NEW APP)

Khi người dùng hoặc AI muốn tích hợp thêm 1 app mới (ví dụ: `app_kho`), thực hiện chuẩn xác theo các bước sau:

### Cách 1: Nạp bằng code (Dành cho AI & Lập trình viên)
1. **Bước 1: Tạo thư mục app mới**
   - Copy toàn bộ cấu trúc từ `app_mau/` thành thư mục mới, ví dụ: `app_kho/`.
   - Bên trong `app_kho/app.py`:
     ```python
     from flask import Blueprint, render_template

     # Khởi tạo Blueprint với url_prefix riêng biệt
     app_kho_bp = Blueprint(
         'kho', 
         __name__, 
         template_folder='templates',
         static_folder='static',
         url_prefix='/kho'
     )

     @app_kho_bp.route('/')
     def index():
         return render_template('kho_index.html')
     ```
2. **Bước 2: Đăng ký vào `apps_config.json`**
   Thêm khối cấu hình vào danh sách `apps`:
   ```json
   {
     "id": "kho",
     "name": "Quản Lý Kho Hàng",
     "folder": "app_kho",
     "entry_module": "app_kho.app",
     "blueprint_name": "app_kho_bp",
     "url_prefix": "/kho",
     "icon": "fas fa-boxes",
     "description": "Theo dõi xuất nhập tồn kho hàng hóa",
     "color": "#10b981",
     "active": true
   }
   ```
3. **Bước 3: Tự động tải:**
   File `app.py` chính đã có hàm `register_dynamic_apps()` tự động quét `apps_config.json` và đăng ký blueprint khi Flask khởi động. Không cần sửa `app.py` chính.

### Cách 2: Nạp nhanh qua Giao diện Web
1. Truy cập `https://rappervint.pythonanywhere.com` (hoặc `http://localhost:5000` trên máy).
2. Bấm nút **"+ Thêm App Mới"** trên góc phải.
3. Nhập ID (`kho`), Tên (`Quản Lý Kho Hàng`), URL (`/kho/`), Mô tả và Icon.
4. Bấm **"Tạo App Ngay"**: API `/api/hub/add-app` sẽ tự động nhân bản thư mục mẫu `app_mau`, tạo cấu hình vào `apps_config.json` và kích hoạt ngay lập tức.

---

## IV. QUY TRÌNH CẬP NHẬT CODE LÊN MÁY CHỦ (GIT DEPLOYMENT WORKFLOW)

Quy trình chuẩn hóa 2 bước không cần xóa web, không cần nén ZIP:

### Bước 1: Đẩy code từ máy tính lên GitHub (VS Code Terminal / PowerShell)
```powershell
git add .
git commit -m "Mo ta noi dung sua chua hoac them app"
git push
```

### Bước 2: Cập nhật trên PythonAnywhere (Bash Console)
1. Mở cửa sổ **Bash** trên PythonAnywhere:
   ```bash
   cd ~/appchung
   git pull
   ```
2. Nếu có cài thêm thư viện mới trong `requirements.txt`:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Vào tab **Web** trên giao diện PythonAnywhere -> Bấm nút màu xanh:
   **"Reload rappervint.pythonanywhere.com"**

---

## V. CẤU HÌNH PYTHONANYWHERE CHUẨN XÁC (DÀNH CHO KHỞI TẠO HOẶC KHÔI PHỤC)

Nếu trong tương lai cần cài đặt lại từ đầu trên một tài khoản PythonAnywhere mới:

1. **Clone mã nguồn từ GitHub:**
   ```bash
   git clone https://github.com/rappervint/appchung.git
   pip3 install -r appchung/requirements.txt
   ```
2. **Cấu hình tab Web:**
   - **Source code:** `/home/rappervint/appchung`
   - **Working directory:** `/home/rappervint/appchung`
   - **WSGI configuration file (`/var/www/rappervint_pythonanywhere_com_wsgi.py`):**
     ```python
     import sys
     import os

     path = '/home/rappervint/appchung'
     if path not in sys.path:
         sys.path.insert(0, path)

     from app import app as application
     ```

---

## VI. HƯỚNG DẪN DÀNH CHO AI ASSISTANT (ANTIGRAVITY INSTRUCTIONS)

Khi người dùng yêu cầu Antigravity hỗ trợ trong tương lai, AI cần tuân thủ nghiêm ngặt các chỉ thị sau:
1. **Đọc file này trước tiên** để nắm cấu trúc hệ thống, tránh đề xuất các phương pháp nén ZIP thủ công hay xóa web làm lại.
2. **Bảo toàn dữ liệu:** Không bao giờ tạo script hoặc lệnh ghi đè vào các file SQLite (`tiem_lap_do.db`, `doanhthu_den.db`, `finance.db`).
3. **Tuân thủ quy chuẩn Blueprint:** Mọi app thêm mới bắt buộc phải đóng gói dưới dạng Flask `Blueprint` có `url_prefix` riêng biệt và khai báo trong `apps_config.json`.
4. **Tối ưu hiệu năng PythonAnywhere:** Sử dụng cơ chế Lazy Import (import `pandas`, `openpyxl` bên trong các hàm xử lý tính toán hoặc xuất Excel) để tránh timeout khởi động ứng dụng trên gói tài khoản miễn phí.


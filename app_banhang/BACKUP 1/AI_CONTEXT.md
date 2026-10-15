# 📋 HỒ SƠ DỰ ÁN DÀNH CHO AI (AI CONTEXT SPECIFICATION)

> **Mục đích tài liệu:** Tài liệu này chứa toàn bộ kiến trúc, cơ sở dữ liệu, quy tắc logic và quy chuẩn giao diện của phần mềm. Hãy đính kèm tệp này hoặc dán nội dung này vào ô chat của bất kỳ AI nào (ChatGPT, Claude, Gemini, DeepSeek, Cursor...) mỗi khi cần AI hiểu dự án để tiếp tục viết thêm tính năng hoặc sửa lỗi.

---

## 1. TỔNG QUAN DỰ ÁN
* **Tên ứng dụng:** Phần Mềm Quản Lý Lắp Đồ Xe & Tra Cứu Bảo Hành ("Tiệm Lắp Đồ Dùm").
* **Mục đích:** Quản lý hóa đơn lắp đặt phụ kiện đồ chơi ô tô/xe máy, quản lý danh mục bảng giá, theo dõi thời hạn bảo hành theo biển số xe/SĐT, sao lưu và xuất báo cáo Excel.
* **Mô hình hoạt động:** Web App cục bộ (Local / mạng LAN nội bộ) chạy trên nền tảng Flask nhẹ, giao diện tương tác qua trình duyệt máy tính & điện thoại cùng mạng Wi-Fi.

---

## 2. CÔNG NGHỆ SỬ DỤNG (TECH STACK)
* **Backend:** Python 3.10+, Framework Flask.
* **Database:** SQLite (`tiem_lap_do.db`).
* **Frontend:** Single-Page Application (HTML5, Bootstrap 5.3, Bootstrap Icons 1.11, Vanilla JavaScript).
* **Xử lý Excel:** `pandas`, `openpyxl`.
* **Phong cách UI:** Apple macOS Dark Acrylic (Dark Mode sang trọng, không dùng hiệu ứng blur gây lag).

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN
```text
phanmenban hang/
├── app.py                     # Server Flask chính, xử lý API và Database
├── chay_phan_mem.bat          # File chạy nhanh server trên Windows
├── tiem_lap_do.db             # Cơ sở dữ liệu SQLite
├── import_data.py             # Script nạp dữ liệu lịch sử hóa đơn từ file Excel
├── import_hang_hoa.py         # Script nạp danh mục hàng hóa & giá từ Excel
├── AI_CONTEXT.md              # Hồ sơ dự án cung cấp cho các AI
├── templates/
│   └── index.html             # Giao diện duy nhất của toàn bộ hệ thống
```

---

## 4. CƠ SỞ DỮ LIỆU (DATABASE SCHEMA - SQLITE)

### Bảng 1: `orders` (Hóa đơn / Đơn khách)
* `id` (INTEGER, PK, AUTOINCREMENT): Mã đơn hàng.
* `customer_name` (TEXT): Tên khách hàng.
* `phone` (TEXT): Số điện thoại khách.
* `license_plate` (TEXT): Biển số xe (Ví dụ: `51H-123.45`).
* `install_date` (TEXT): Ngày lắp đặt theo định dạng `YYYY-MM-DD`.
* `total_price` (REAL): Tổng tiền thực thu của đơn sau giảm giá.
* **Chỉ mục (Indexes):**
  * `idx_orders_plate` trên `license_plate`
  * `idx_orders_phone` trên `phone`

### Bảng 2: `order_items` (Chi tiết các món trong đơn)
* `id` (INTEGER, PK, AUTOINCREMENT): Mã định danh dòng chi tiết.
* `order_id` (INTEGER, FK -> `orders.id`): Liên kết đến hóa đơn.
* `item_name` (TEXT): Tên món phụ kiện / dịch vụ (kèm ghi chú giảm giá nếu có).
* `price` (REAL): Đơn giá của món (nếu là dòng giảm giá tổng hóa đơn thì lưu giá trị âm).
* `warranty_months` (INTEGER): Số tháng bảo hành (0 nếu không bảo hành).
* **Chỉ mục (Indexes):**
  * `idx_order_items_oid` trên `order_id`

### Bảng 3: `products` (Kho danh mục & Bảng giá tham chiếu)
* `id` (INTEGER, PK, AUTOINCREMENT): Mã món trong kho.
* `name` (TEXT, UNIQUE): Tên món đồ chơi / dịch vụ.
* `price` (REAL): Giá bán tiêu chuẩn (VNĐ).
* `warranty_months` (INTEGER): Thời gian bảo hành tiêu chuẩn (tháng).
* **Chỉ mục (Indexes):**
  * `idx_products_name` trên `name`

---

## 5. DANH SÁCH API ENDPOINTS (`app.py`)

1. **`GET /`** -> Trả về giao diện chính `templates/index.html`.
2. **`GET /api/products?q={tu_khoa}`**
   * Lấy danh sách sản phẩm gợi ý tự động hoặc bảng giá.
   * Giới hạn: tối đa 30 kết quả khi tìm kiếm, 100 kết quả khi xem tất cả.
   * Có cơ chế dự phòng: nếu bảng `products` trống, tự động gom nhóm từ `order_items`.
3. **`POST /api/order`**
   * Payload JSON: `{ plate, name, phone, date, items: [{name, price, warranty}, ...] }`
   * Lưu hóa đơn và lưu các dòng phụ kiện vào database bằng transaction.
4. **`GET /api/search?q={bien_so_hoac_sdt}`**
   * Tìm kiếm đơn hàng khớp biển số hoặc số điện thoại.
   * Chống N+1 query: dùng gom nhóm `WHERE order_id IN (...)`.
   * Tự động tính ngày hết hạn (`exp`) và trạng thái (`✅ Còn BH` / `❌ Hết BH` / `-`).
5. **`GET /api/backup`** -> Tải trực tiếp file `tiem_lap_do.db`.
6. **`GET /api/export`** -> Xuất báo cáo danh sách hóa đơn ra file Excel `.xlsx`.
7. **`POST /api/import`** -> Nạp file Excel danh sách đơn vào hệ thống.

---

## 6. QUY TẮC NGHIỆP VỤ & LOGIC ĐẶC THÙ (BUSINESS RULES)

### A. Nhập tiền thông minh & chống lỗi gõ tiếng Việt Windows/Telex
* **Ô nhập tiền:** Không dùng `type="number"` vì bị lỗi nuốt phím khi bật Unikey/EVKey gõ tiếng Việt. Dùng `type="text"`.
* **Hỗ trợ gõ tắt đơn vị:**
  * `1000k` / `1000nghin` -> `1,000,000 VNĐ`
  * `1tr` / `1.5tr` / `1m` -> `1,000,000 VNĐ` / `1,500,000 VNĐ`
  * Tự động định dạng phân tách dấu phẩy hàng nghìn khi blur ra ngoài (`1.000.000`).

### B. Giảm giá món & Giảm bill tổng
* **Hỗ trợ cú pháp:** Nhập số tiền cụ thể (`50k`, `200000`) hoặc phần trăm (`5%`, `10%`).
* **Giảm giá món:** Trừ trực tiếp vào giá món đó, kèm tag ghi chú `(Giảm 10%)`.
* **Giảm bill tổng:** Tạo 1 dòng ảo trong hóa đơn với `price` âm để lưu chuẩn vào lịch sử.

### C. Logic tính hạn bảo hành
* Dùng hàm cộng tháng chuẩn lịch (`add_months`), xử lý triệt để trường hợp ngày 31 nhảy sang tháng có 28, 29 hoặc 30 ngày bằng `calendar.monthrange`.
* Nếu ngày hết hạn $\ge$ ngày hiện tại -> `✅ Còn BH`, ngược lại -> `❌ Hết BH`.

### D. Tự động điền giá khi chọn món (Auto-suggest)
* Khi gõ tên món vào ô `#item_name`, hệ thống tìm trong danh mục `productsDb` đã tải sẵn. Nếu trùng tên, tự động điền giá bán và số tháng bảo hành mà không cần gõ thủ công.

---

## 7. QUY CHUẨN GIAO DIỆN & HIỆU NĂNG (PERFORMANCE GUIDELINES)

> ⚠️ **ĐẶC BIỆT LƯU Ý KHI CODE GIAO DIỆN CHO DỰ ÁN NÀY:**
1. **TUYỆT ĐỐI KHÔNG DÙNG `backdrop-filter: blur(...)` LỒNG NHAU:**
   * Trình duyệt trên Windows (Chrome, Edge) bị tụt FPS thê thảm và lag đơ gõ phím nếu dùng `backdrop-filter` trên các container lớn.
   * Sử dụng mã màu Dark Mode thuần cao cấp: `--mac-window-bg: #141724;`, `--mac-card-bg: #1b1f2e;` kết hợp viền mảnh `1px solid rgba(255,255,255,0.08)`.
2. **Cuộn danh sách mượt mà (60–120 FPS):**
   * Các thẻ danh sách (`.order-card`) phải có thuộc tính `contain: content;`.
   * Không dùng `transition: all` hay hiệu ứng dịch chuyển tọa độ `transform: translateY` khi hover qua danh sách nhiều phần tử.
3. **Tìm kiếm thời gian thực phải có Debounce:**
   * Mọi ô input tìm kiếm (như `#search_price_q`) phải áp dụng hàm hoãn `setTimeout(fn, 200)` (Debounce) để tránh spam request làm đơ trình duyệt.

---

## 8. MẪU PROMPT KHI YÊU CẦU AI HỖ TRỢ VIẾT CODE

Mỗi khi mở một cuộc trò chuyện mới với bất kỳ AI nào, hãy gửi đoạn mở đầu sau:

```markdown
Tôi đang phát triển phần mềm "Tiệm Lắp Đồ Dùm" (Flask + SQLite + HTML5 macOS Dark theme). 
Dưới đây là tài liệu kiến trúc toàn diện của dự án (đính kèm tệp AI_CONTEXT.md).

Hãy đọc kỹ tài liệu này trước. Yêu cầu của tôi hôm nay là:
[MÔ TẢ TÍNH NĂNG HOẶC LỖI BẠN CẦN LÀM Ở ĐÂY, VÍ DỤ: Thêm tính năng in hóa đơn PDF khổ 80mm khi bấm lưu đơn]

Yêu cầu kỹ thuật:
- Giữ nguyên phong cách Dark Mode và quy chuẩn Zero-lag (không dùng backdrop-filter).
- Viết code hoàn chỉnh, có giải thích các vị trí cần thay thế trong app.py hoặc templates/index.html.
```


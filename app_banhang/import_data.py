import sqlite3
import pandas as pd
import re
import math
import os

DB_NAME = "tiem_lap_do.db"
FILE_NAME = "TỔNG HỢP - 2022 - 2026.xlsx"

# Hàm bóc tách số tháng bảo hành từ chữ (Ví dụ: "12 tháng", "5 năm")
def parse_warranty(w_str):
    if pd.isna(w_str):
        return 0
    w_str = str(w_str).lower()
    match = re.search(r'(\d+)\s*(tháng|năm)', w_str)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        return val * 12 if unit == 'năm' else val
    return 0

# Hàm làm sạch chuỗi và xử lý số điện thoại
def clean_str(val):
    if pd.isna(val): return ""
    if isinstance(val, float) and val.is_integer(): 
        val = int(val)
    return str(val).strip()

def run_import():
    if not os.path.exists(FILE_NAME):
        print(f"LỖI: Không tìm thấy file '{FILE_NAME}'. Hãy copy nó vào cùng thư mục với script này.")
        return

    # Khởi tạo Database nếu chưa có
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_name TEXT,
                    phone TEXT, license_plate TEXT, install_date TEXT, total_price REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, item_name TEXT,
                    price REAL, warranty_months INTEGER, FOREIGN KEY(order_id) REFERENCES orders(id))""")
    
    print("Đang đọc file Excel (Có thể mất vài chục giây vì dữ liệu lớn)...")
    xls = pd.ExcelFile(FILE_NAME)
    sheets_to_import = ['2022', '2023', '2024-2025', '2026']
    
    total_orders = 0
    total_items = 0

    for sheet in sheets_to_import:
        if sheet not in xls.sheet_names:
            continue
            
        print(f"Đang xử lý dữ liệu năm: {sheet}...")
        df = pd.read_excel(xls, sheet_name=sheet)
        
        # Gom nhóm các dòng dữ liệu có chung Mã Hóa Đơn
        grouped = df.groupby('Mã hóa đơn')
        
        for ma_hd, group in grouped:
            first_row = group.iloc[0]
            
            # Xử lý ngày tháng
            date_val = first_row.get('Thời gian', pd.NaT)
            install_date = str(date_val)[:10] if not pd.isna(date_val) else "2022-01-01"
                
            # Xử lý Biển số (Dùng cột Mã khách hàng)
            plate = clean_str(first_row.get('Mã khách hàng', ''))
            if not plate: plate = "KHÔNG RÕ"
                
            # Xử lý Tên và SĐT (Tự động bù số 0 nếu bị Excel cắt mất)
            name = clean_str(first_row.get('Tên khách hàng', ''))
            phone = clean_str(first_row.get('Điện thoại', ''))
            if phone.startswith(('3','7','8','9')): 
                phone = "0" + phone
            
            items = []
            order_total = 0
            
            # Bóc tách từng món đồ trong Hóa đơn
            for _, row in group.iterrows():
                item_name = clean_str(row.get('Tên hàng', ''))
                if not item_name: continue
                
                price = row.get('Thành tiền', 0)
                price = float(price) if not pd.isna(price) else 0.0
                
                # Bóc tách số tháng bảo hành nếu cột này tồn tại
                war = parse_warranty(row.get('Bảo hành', '')) if 'Bảo hành' in row else 0
                
                items.append((item_name, price, war))
                order_total += price
            
            # Lưu Hóa đơn vào DataBase
            if items:
                c.execute("""INSERT INTO orders (customer_name, phone, license_plate, install_date, total_price) 
                             VALUES (?, ?, ?, ?, ?)""", (name, phone, plate, install_date, order_total))
                order_id = c.lastrowid
                total_orders += 1
                
                for it in items:
                    c.execute("""INSERT INTO order_items (order_id, item_name, price, warranty_months) 
                                 VALUES (?, ?, ?, ?)""", (order_id, it[0], it[1], it[2]))
                    total_items += 1
                
    conn.commit()
    conn.close()
    print(f"\n✅ HOÀN TẤT! Đã chuyển đổi thành công {total_orders:,} đơn hàng và {total_items:,} món đồ chơi.")
    print("Bây giờ bạn có thể mở web app lên để tra cứu.")

if __name__ == "__main__":
    run_import()
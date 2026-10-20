def clean_phone_number(val):
    if not val:
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    # Bỏ dấu chấm, dấu phẩy thừa nếu có
    if s.endswith('.'):
        s = s[:-1]
    # Nếu là số điện thoại 9 chữ số (bị Excel cắt mất số 0 ở đầu)
    if s and not s.startswith('0') and len(s) in (9, 10) and s.isdigit():
        s = '0' + s
    return s

import os
import io
import csv
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "tiem_lap_do.db")

def parse_plate_and_name(customer_code, customer_name):
    """
    MePOS lưu Biển số vào Mã khách hàng hoặc Tên khách hàng:
    Ví dụ: customer_code = '63A-123.10', customer_name = 'CHÚ LỘC - CAMRY 1008'
    Hoặc customer_code = 'KH000002', customer_name = 'FORTUNER 2015'
    """
    plate = (customer_code or "").strip().upper()
    name = (customer_name or "").strip()
    
    # Nếu customer_code không phải biển số xe (bắt đầu bằng KH...), kiểm tra trong tên
    if not plate or plate.startswith("KH"):
        # Thử tìm xem tên khách có định dạng biển số không (vd 51H-123.45)
        import re
        m = re.search(r'\b(\d{2}[A-Z]\-?\d{3,5}\.?\d{0,2})\b', name.upper())
        if m:
            plate = m.group(1)
        elif not plate or plate.startswith("KH"):
            plate = name.split(" - ")[0].strip() if " - " in name else name

    # Nếu trong tên có gạch nối: CHÚ LỘC - CAMRY 1008 -> Tên là CHÚ LỘC (hoặc giữ nguyên)
    return plate, name

def import_mepos_invoices(csv_content_or_filepath):
    """
    Nhập thông minh file xuất hóa đơn từ MePOS / Excel vào database tiem_lap_do.db:
    1. Không bị trùng lặp đơn hàng (kiểm tra theo Mã hóa đơn HD-... hoặc Biển số + Giờ + Tổng tiền).
    2. Cập nhật tồn kho sản phẩm tương ứng trong bảng products (nếu có mã hàng SP...).
    3. Tra cứu thời hạn bảo hành từ bảng products để gán tự động vào từng món trong đơn.
    """
    if os.path.exists(csv_content_or_filepath):
        with open(csv_content_or_filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            content = f.read()
    else:
        content = csv_content_or_filepath

    # Hỗ trợ cả file CSV ngăn cách bằng dấu phẩy
    f_io = io.StringIO(content)
    reader = csv.DictReader(f_io)
    
    orders_grouped = {}
    row_count = 0
    
    for r in reader:
        inv_code = (r.get('Mã hóa đơn') or r.get('Mã đơn hàng') or r.get('HD') or '').strip()
        if not inv_code:
            continue
            
        row_count += 1
        time_str = (r.get('Thời gian') or r.get('Thời gian tạo') or r.get('Ngày') or '').strip()
        # Chuẩn hóa ngày YYYY-MM-DD
        date_str = ""
        if time_str:
            try:
                date_str = time_str.split(' ')[0]
            except Exception:
                date_str = time_str
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        cust_code = (r.get('Mã khách hàng') or '').strip()
        cust_name = (r.get('Tên khách hàng') or '').strip()
        phone = clean_phone_number(r.get('Điện thoại') or '')
        note = (r.get('Ghi chú') or '').strip()
        
        # Tiền hàng
        try:
            total_price = float(r.get('Khách cần trả') or r.get('Tổng tiền hàng') or r.get('Khách đã trả') or 0)
        except Exception:
            total_price = 0.0

        plate, full_name = parse_plate_and_name(cust_code, cust_name)

        if inv_code not in orders_grouped:
            orders_grouped[inv_code] = {
                'inv_code': inv_code,
                'plate': plate,
                'name': full_name,
                'phone': phone,
                'date_str': date_str,
                'time_str': time_str,
                'note': note,
                'total_price': total_price,
                'items': []
            }

        # Item info
        item_code = (r.get('Mã hàng') or '').strip()
        item_name = (r.get('Tên hàng') or '').strip()
        if not item_name:
            continue

        try:
            qty = int(float(r.get('Số lượng') or 1))
        except Exception:
            qty = 1

        try:
            orig_price = float(r.get('Đơn giá') or 0)
        except Exception:
            orig_price = 0.0

        try:
            final_price = float(r.get('Giá bán') or r.get('Thành tiền') or orig_price)
        except Exception:
            final_price = orig_price

        item_note = (r.get('Ghi chú hàng hóa') or '').strip()
        if item_note and item_note not in item_name:
            item_display = f"{item_name} ({item_note})"
        else:
            item_display = item_name

        orders_grouped[inv_code]['items'].append({
            'code': item_code,
            'name': item_display,
            'orig_name': item_name,
            'qty': qty,
            'orig_price': orig_price,
            'price': final_price
        })

    if not orders_grouped:
        return {"status": "error", "msg": "Không tìm thấy dữ liệu hóa đơn hợp lệ trong file!"}

    # Bắt đầu ghi vào SQLite tiem_lap_do.db
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()

    # Tạo bảng map bảo hành và trừ tồn kho từ products
    c.execute("SELECT code, name, warranty_months, stock FROM products")
    prod_cache = {}
    for p_code, p_name, p_war, p_stock in c.fetchall():
        if p_code:
            prod_cache[p_code.upper()] = (p_war or 0, p_stock or 0)
        if p_name:
            prod_cache[p_name.upper()] = (p_war or 0, p_stock or 0)

    inserted_orders = 0
    skipped_orders = 0
    inserted_items = 0

    for inv_code, o in orders_grouped.items():
        # Kiểm tra chống trùng lặp: Đã có đơn cùng biển số + cùng ngày + cùng số tiền chưa?
        c.execute("""SELECT id FROM orders 
                     WHERE (license_plate = ? OR customer_name = ?) 
                       AND install_date = ? 
                       AND ABS(total_price - ?) < 1""", 
                  (o['plate'], o['name'], o['date_str'], o['total_price']))
        existing = c.fetchone()
        if existing:
            skipped_orders += 1
            continue

        # Thêm đơn mới
        c.execute("""INSERT INTO orders (customer_name, phone, license_plate, install_date, total_price)
                     VALUES (?, ?, ?, ?, ?)""",
                  (o['name'], o['phone'], o['plate'], o['date_str'], o['total_price']))
        order_id = c.lastrowid
        inserted_orders += 1

        for it in o['items']:
            war_m = 12 # Mặc định 12 tháng nếu không tìm thấy
            # Tra cứu bảo hành từ bảng products
            p_key = it['code'].upper() if it['code'] else it['orig_name'].upper()
            if p_key in prod_cache:
                war_m = prod_cache[p_key][0]
            elif 'BÓNG LED' in it['name'].upper() or 'BI GẦM' in it['name'].upper() or 'BI LED' in it['name'].upper():
                war_m = 24
            elif 'TIỀN CÔNG' in it['name'].upper() or 'DỊCH VỤ' in it['name'].upper():
                war_m = 0

            unit_price = it['price'] / it['qty'] if it['qty'] > 0 else it['price']

            c.execute("""INSERT INTO order_items (order_id, item_name, price, warranty_months, orig_price, unit_price, qty)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (order_id, it['name'], it['price'], war_m, it['orig_price'], unit_price, it['qty']))
            inserted_items += 1

            # Tự động trừ tồn kho trong bảng products nếu khớp mã hàng hoặc tên hàng
            if it['code']:
                c.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE UPPER(code) = UPPER(?)", (it['qty'], it['code']))
            else:
                c.execute("UPDATE products SET stock = MAX(0, stock - ?) WHERE UPPER(name) = UPPER(?)", (it['qty'], it['orig_name']))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "msg": f"Đã nhập thành công {inserted_orders} đơn hàng ({inserted_items} món đồ). Đã bỏ qua {skipped_orders} đơn trùng lặp!",
        "inserted_orders": inserted_orders,
        "inserted_items": inserted_items,
        "skipped_orders": skipped_orders
    }

if __name__ == "__main__":
    sample_file = os.path.join(BASE_DIR, "mepos_invoices_sample.csv")
    res = import_mepos_invoices(sample_file)
    print("Result:", res)


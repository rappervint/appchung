import sqlite3
import pandas as pd
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "tiem_lap_do.db")
FILE_NAME = os.path.join(BASE_DIR, "TỔNG HỢP - 2022 - 2026.xlsx")

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

def clean_val(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() == "nan" else s

def sync_from_excel():
    if not os.path.exists(FILE_NAME):
        return {"status": "error", "msg": f"Không tìm thấy file Excel: {FILE_NAME}"}

    print(f"Đang đọc Sheet 'HÀNG HÓA' từ file '{FILE_NAME}'...")
    xls = pd.ExcelFile(FILE_NAME)
    if 'HÀNG HÓA' not in xls.sheet_names:
        return {"status": "error", "msg": "Không tìm thấy Sheet 'HÀNG HÓA' trong file Excel!"}

    df = pd.read_excel(xls, sheet_name='HÀNG HÓA')

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Tạo lại bảng products chuẩn 100% theo cấu trúc cột của Sheet HÀNG HÓA trong Excel
    c.execute("DROP TABLE IF EXISTS products")
    c.execute("""CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT DEFAULT 'Hàng hóa',
                    category TEXT DEFAULT '',
                    code TEXT UNIQUE,
                    name TEXT,
                    price REAL DEFAULT 0,
                    cost_price REAL DEFAULT 0,
                    stock INTEGER DEFAULT 0,
                    warranty_months INTEGER DEFAULT 0,
                    warranty_raw TEXT DEFAULT '',
                    created_at TEXT DEFAULT ''
                )""")

    rows_to_insert = []
    for idx, row in df.iterrows():
        name = clean_val(row.get('Tên hàng', ''))
        if not name:
            continue

        item_type = clean_val(row.get('Loại hàng', 'Hàng hóa')) or 'Hàng hóa'
        category = clean_val(row.get('Nhóm hàng(3 Cấp)', ''))
        code = clean_val(row.get('Mã hàng', ''))
        if not code:
            code = f"AUTO_{idx+1}"

        raw_price = row.get('Giá bán', 0)
        try:
            price = float(raw_price) if not pd.isna(raw_price) else 0.0
        except Exception:
            price = 0.0

        raw_cost = row.get('Giá vốn', 0)
        try:
            cost_price = float(raw_cost) if not pd.isna(raw_cost) else 0.0
        except Exception:
            cost_price = 0.0

        raw_stock = row.get('Tồn kho', 0)
        try:
            stock = int(round(float(raw_stock))) if not pd.isna(raw_stock) else 0
        except Exception:
            stock = 0

        war_raw = clean_val(row.get('Bảo hành', ''))
        war_months = parse_warranty(war_raw)
        created_at = clean_val(row.get('Thời gian tạo', ''))

        rows_to_insert.append((
            item_type, category, code, name, price, cost_price, stock, war_months, war_raw, created_at
        ))

    c.executemany("""INSERT INTO products 
                     (item_type, category, code, name, price, cost_price, stock, warranty_months, warranty_raw, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows_to_insert)

    c.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_code ON products(code)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_stock ON products(stock)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
    conn.commit()

    total_rows = len(rows_to_insert)
    total_stock = sum(r[6] for r in rows_to_insert)
    conn.close()

    msg = f"Đã đồng bộ chuẩn 100% từ Excel: {total_rows} mặt hàng, Tổng tồn kho: {total_stock:,} cái!"
    print("✅ " + msg)
    return {"status": "success", "msg": msg, "total_rows": total_rows, "total_stock": total_stock}

if __name__ == "__main__":
    sync_from_excel()
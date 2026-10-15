"""
Script nạp lại toàn bộ dữ liệu từ DOANH THU DEN.xlsx vào SQLite.
Chạy: python import_excel.py
Lưu ý: Script sẽ XÓA sạch DB cũ và nạp lại từ đầu.
"""

import os, re, sqlite3
from datetime import datetime, date
import pandas as pd

DB_FILE    = 'doanhthu_den.db'
EXCEL_FILE = 'DOANH THU DEN.xlsx'

# ─────────────────────────────────────────────────────────────────────────────
# Bảng ánh xạ tên sheet → (month, year)
# Xử lý tất cả biến thể tên: "Tháng 8", "THÁNG 924", "THÁNG625", "tháng 7"...
# ─────────────────────────────────────────────────────────────────────────────

SHEET_MAP = {
    # Năm 2022 (không có năm trong tên sheet)
    'Tháng 8':   (8,  2022),
    'Tháng 9':   (9,  2022),
    'THÁNG 10':  (10, 2022),
    'THÁNG 11':  (11, 2022),
    'THÁNG 12':  (12, 2022),
    # Năm 2023 (không có năm trong tên sheet)
    'THÁNG 1':   (1,  2023),
    'THÁNG 2':   (2,  2023),
    'THÁNG 3':   (3,  2023),
    'THÁNG 4':   (4,  2023),
    'THÁNG 5':   (5,  2023),
    'THÁNG 6':   (6,  2023),
    'tháng 7':   (7,  2023),
    # Sheet đặc biệt: tên 727 nhưng thực tế 07/2026
    'THÁNG727':  (7,  2026),
}


def decode_sheet_name(sheet_name: str):
    """
    Trả về (month, year) từ tên sheet.
    Ưu tiên tra bảng SHEET_MAP, sau đó dùng regex.
    """
    # 1. Tra bảng cố định
    if sheet_name in SHEET_MAP:
        return SHEET_MAP[sheet_name]

    # 2. Regex: tách số tháng và năm khỏi tên sheet
    # Chuẩn hóa: bỏ "THÁNG", "tháng", khoảng trắng, rồi lấy số
    s = sheet_name.upper().replace("THÁNG", "").replace(" ", "").strip()

    # Dạng: MMYY hoặc MMMYY (VD: 824 → 8/24, 1024 → 10/24, 0924 → 9/24)
    m = re.match(r'^0?(\d{1,2})(\d{2})$', s)
    if m:
        month = int(m.group(1))
        year  = 2000 + int(m.group(2))
        if 1 <= month <= 12:
            return month, year

    return None, None


def detect_price_col(header_row):
    """Phát hiện chỉ số cột GIÁ BÁN từ header."""
    h = [str(x).strip().upper() for x in header_row]
    # Sheet cũ: có cột GIÁ NHẬP → GIÁ BÁN ở index 7
    if 'GIÁ NHẬP' in h:
        return 7
    # Sheet mới: GIÁ BÁN ở index 6
    return 6


def parse_date(raw):
    """Chuyển đổi ô ngày tháng sang chuỗi YYYY-MM-DD."""
    if pd.isna(raw):
        return None
    if isinstance(raw, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(raw).strftime('%Y-%m-%d')
    s = str(raw).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d/%m%Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def make_fallback_date(month, year):
    """Ngày mặc định khi dòng không có ngày: mùng 15 của tháng đó."""
    return f'{year:04d}-{month:02d}-15'


# ─────────────────────────────────────────────────────────────────────────────
# Main import
# ─────────────────────────────────────────────────────────────────────────────

def run_import():
    if not os.path.exists(EXCEL_FILE):
        print(f'❌ Không tìm thấy file: {EXCEL_FILE}')
        return

    # Xóa DB cũ, tạo lại
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f'🗑  Đã xóa DB cũ: {DB_FILE}')

    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    cur.execute('''
        CREATE TABLE orders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date    TEXT    NOT NULL,
            product_name  TEXT    NOT NULL,
            customer_name TEXT,
            car_model     TEXT,
            quantity      INTEGER DEFAULT 1,
            price_k       INTEGER NOT NULL,
            sheet_origin  TEXT
        )
    ''')
    conn.commit()

    xls         = pd.ExcelFile(EXCEL_FILE)
    total_rows  = 0
    skip_sheets = []

    for sheet in xls.sheet_names:
        # Bỏ qua sheet rác
        sn_up = sheet.upper().strip()
        if sn_up.startswith('NEW') or sn_up == 'SHEET1' or sn_up == '':
            skip_sheets.append(sheet)
            continue

        month, year = decode_sheet_name(sheet)
        if month is None:
            print(f'  ⚠️  Bỏ qua (không nhận ra): [{sheet}]')
            skip_sheets.append(sheet)
            continue

        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet, header=None)

        # Cần ít nhất 4 dòng (tiêu đề + header + ≥1 dòng data)
        if len(df) < 4:
            skip_sheets.append(sheet)
            continue

        # Header ở dòng index=2, data bắt đầu từ index=3
        header_row    = df.iloc[2].values
        price_col_idx = detect_price_col(header_row)

        fallback_date = make_fallback_date(month, year)
        last_date     = fallback_date
        last_cust     = ''
        last_car      = ''
        inserted      = 0

        for i in range(3, len(df)):
            row = df.iloc[i]

            # Tên sản phẩm (cột 2) — bắt buộc
            prod = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
            if not prod or prod.upper() in ('NAN', 'STT', 'TỔNG CỘNG', 'TỔNG'):
                continue

            # Bỏ qua dòng tổng kết / tiêu đề lặp
            try:
                float(prod)   # nếu tên SP là số thuần → dòng tổng kết
                continue
            except ValueError:
                pass

            # Ngày (cột 1)
            parsed = parse_date(row.iloc[1])
            if parsed:
                last_date = parsed
            # Nếu ngày trống → giữ nguyên last_date (combo)

            # Khách hàng (cột 3)
            raw_cust = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ''
            if raw_cust and raw_cust.upper() not in ('NAN', ''):
                last_cust = raw_cust.upper()

            # Loại xe (cột 4)
            raw_car = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
            if raw_car and raw_car.upper() not in ('NAN', ''):
                last_car = raw_car.upper()

            # Số lượng (cột 5)
            qty = 1
            raw_qty = row.iloc[5]
            if pd.notna(raw_qty):
                m_q = re.search(r'\d+', str(raw_qty))
                if m_q:
                    qty = int(m_q.group(0))

            # Giá bán
            if price_col_idx >= len(row) or pd.isna(row.iloc[price_col_idx]):
                # Thử cột 6 nếu cột 7 rỗng (sheet cũ nhưng thiếu GIÁ NHẬP)
                alt_idx = 6 if price_col_idx == 7 else None
                if alt_idx and alt_idx < len(row) and pd.notna(row.iloc[alt_idx]):
                    price_col_idx_use = alt_idx
                else:
                    continue
            else:
                price_col_idx_use = price_col_idx

            try:
                price_k = int(float(row.iloc[price_col_idx_use]))
            except (ValueError, TypeError):
                continue

            if price_k <= 0:
                continue

            cur.execute('''
                INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (last_date, prod.upper(), last_cust, last_car, qty, price_k, sheet))
            inserted += 1

        total_rows += inserted
        print(f'  ✅ [{sheet:15s}] → {month:02d}/{year} | {inserted:3d} dòng')

    conn.commit()
    conn.close()

    print()
    print(f'─' * 50)
    print(f'🎉 Hoàn tất! Đã nạp tổng cộng {total_rows} dòng vào DB.')
    if skip_sheets:
        print(f'   (Bỏ qua {len(skip_sheets)} sheet: {skip_sheets})')


if __name__ == '__main__':
    run_import()


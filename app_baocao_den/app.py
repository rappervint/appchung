"""
╔══════════════════════════════════════════════════════════════╗
║         QUẢN LÝ & BÁO CÁO DOANH THU ĐÈN — app.py           ║
║                                                              ║
║  Cách chạy:  python app.py                                   ║
║  Truy cập :  http://127.0.0.1:5000                           ║
║                                                              ║
║  Yêu cầu  :  pip install flask pandas openpyxl               ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import re
import sqlite3
import logging
from datetime import datetime, date

import json
from flask import Blueprint, Flask, render_template, request, jsonify, redirect

# ── Thư mục gốc dự án: đảm bảo tìm đúng file ngay cả khi chạy trên WSGI / PythonAnywhere ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
den_bp = Blueprint('den', __name__, template_folder='templates')

DB_FILE           = os.path.join(BASE_DIR, 'doanhthu_den.db')
EXCEL_FILE        = os.path.join(BASE_DIR, 'DOANH THU DEN.xlsx')
EXPORT_EXCEL_FILE = os.path.join(BASE_DIR, 'DOANH THU DEN_CAPNHAT.xlsx')

# ── Nút bấm nhanh (Tối ưu theo số liệu thực tế cửa hàng) ───────
QUICK_PRODUCTS = [
    # GẦM F10 SERIES (Bán chạy nhất)
    {"name": "F10 TURBO",   "price": 5100, "cat": "F10"},
    {"name": "F10 PRO",     "price": 5500, "cat": "F10"},
    {"name": "F10 HYPER",   "price": 5500, "cat": "F10"},
    {"name": "F10 NEW 2.0", "price": 3900, "cat": "F10"},
    # NAOEVO SERIES (Lắp nhiều nhất)
    {"name": "NAOEVO S6",   "price": 1800, "cat": "NAOEVO"},
    {"name": "NAOEVO S3",   "price": 1500, "cat": "NAOEVO"},
    {"name": "NAOEVO S8",   "price": 2500, "cat": "NAOEVO"},
    {"name": "NAOEVO S9",   "price": 2800, "cat": "NAOEVO"},
    # BI LED PHA & DÒNG CAO CẤP
    {"name": "M30 ULTRA",   "price": 5500, "cat": "KHÁC"},
    {"name": "M40 ULTRA",   "price": 6500, "cat": "KHÁC"},
    {"name": "V20 BASE",    "price": 5850, "cat": "KHÁC"},
    {"name": "G1 TURBO",    "price": 6200, "cat": "KHÁC"},
    {"name": "XLIGHT 301",  "price": 4500, "cat": "KHÁC"},
    {"name": "F150 PRO",    "price": 6000, "cat": "KHÁC"},
    {"name": "M20 ULTRA",   "price": 3100, "cat": "KHÁC"},
    {"name": "MÍ LED",      "price": 1800, "cat": "KHÁC"},
]

QUICK_CARS = [
    "VF3", "VIOS", "ACCENT", "XPANDER", "INNOVA",
    "FORTUNER", "CAMRY", "RANGER", "VF5", "I10", "ELANTRA", "CITY"
]


# ── Helpers ────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn


def parse_sheet_period(sheet_name):
    """Dịch tên sheet cũ (VD: THÁNG 724, THÁNG626, THÁNG727) → ngày mặc định."""
    s = sheet_name.upper().replace("THÁNG", "").replace(" ", "").strip()
    m = re.match(r'^(\d{1,2})(\d{2})$', s)
    if m:
        month = int(m.group(1))
        year  = 2000 + int(m.group(2))
        if year == 2027 and month == 7:   # Sheet THÁNG727 thực tế là 07/2026
            year = 2026
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}-15"
    return None


def get_cycle_dates(year, month):
    """Trả về (start_date, end_date) cho kỳ báo cáo 09/MM → 08/MM+1."""
    start_date = f"{year:04d}-{month:02d}-09"
    if month == 12:
        end_date = f"{year + 1:04d}-01-08"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-08"
    return start_date, end_date


def get_current_cycle():
    """Ngày 1-8: thuộc kỳ tháng trước. Ngày 9+: thuộc kỳ tháng này."""
    today = date.today()
    if today.day <= 8:
        if today.month == 1:
            return today.year - 1, 12
        return today.year, today.month - 1
    return today.year, today.month


# ── Bảng ánh xạ tên sheet cũ sang tháng / năm ───────────────────
SHEET_MAP = {
    'Tháng 8':   (8,  2022),
    'Tháng 9':   (9,  2022),
    'THÁNG 10':  (10, 2022),
    'THÁNG 11':  (11, 2022),
    'THÁNG 12':  (12, 2022),
    'THÁNG 1':   (1,  2023),
    'THÁNG 2':   (2,  2023),
    'THÁNG 3':   (3,  2023),
    'THÁNG 4':   (4,  2023),
    'THÁNG 5':   (5,  2023),
    'THÁNG 6':   (6,  2023),
    'tháng 7':   (7,  2023),
    'THÁNG727':  (7,  2026),
}

def decode_sheet_name(sheet_name: str):
    """Xác định (tháng, năm) từ tên sheet trong file Excel."""
    if sheet_name in SHEET_MAP:
        return SHEET_MAP[sheet_name]
    s = str(sheet_name).upper().replace("THÁNG", "").replace(" ", "").strip()
    m = re.match(r'^0?(\d{1,2})(\d{2})$', s)
    if m:
        month = int(m.group(1))
        year  = 2000 + int(m.group(2))
        if 1 <= month <= 12:
            return month, year
    return None, None


def run_internal_excel_import():
    """Tự động nạp Excel tích hợp sẵn trong app.py (hoạt động độc lập không cần file import_excel.py ngoài)."""
    if not os.path.exists(EXCEL_FILE):
        return

    import pandas as pd
    try:
        xls = pd.ExcelFile(EXCEL_FILE)
    except Exception as e:
        print(f"⚠️ Không đọc được file Excel {EXCEL_FILE}: {e}", flush=True)
        return

    conn = get_db()
    cur  = conn.cursor()
    total_rows = 0

    for sheet in xls.sheet_names:
        sn_up = str(sheet).upper().strip()
        if sn_up.startswith('NEW') or sn_up in ('SHEET1', ''):
            continue

        month, year = decode_sheet_name(sheet)
        if month is None:
            continue

        try:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet, header=None)
        except Exception:
            continue

        if len(df) < 4:
            continue

        header_row = [str(x).strip().upper() for x in df.iloc[2].values]
        price_col_idx = 7 if 'GIÁ NHẬP' in header_row else 6

        fallback_date = f"{year:04d}-{month:02d}-15"
        last_date = fallback_date
        last_cust = ''
        last_car  = ''

        for i in range(3, len(df)):
            row = df.iloc[i]
            prod = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ''
            if not prod or prod.upper() in ('NAN', 'STT', 'TỔNG CỘNG', 'TỔNG'):
                continue

            try:
                float(prod)
                continue
            except ValueError:
                pass

            # Ngày
            raw_d = row.iloc[1]
            if pd.notna(raw_d):
                if isinstance(raw_d, (datetime, date, pd.Timestamp)):
                    last_date = pd.Timestamp(raw_d).strftime('%Y-%m-%d')
                else:
                    s_d = str(raw_d).strip()
                    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d/%m%Y'):
                        try:
                            last_date = datetime.strptime(s_d, fmt).strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            pass

            # Khách hàng
            if pd.notna(row.iloc[3]):
                c = str(row.iloc[3]).strip()
                if c and c.upper() != 'NAN':
                    last_cust = c.upper()

            # Loại xe
            if pd.notna(row.iloc[4]):
                car = str(row.iloc[4]).strip()
                if car and car.upper() != 'NAN':
                    last_car = car.upper()

            # Số lượng
            qty = 1
            if pd.notna(row.iloc[5]):
                m_q = re.search(r'\d+', str(row.iloc[5]))
                if m_q:
                    qty = int(m_q.group(0))

            # Cột giá
            use_idx = price_col_idx
            if use_idx >= len(row) or pd.isna(row.iloc[use_idx]):
                if price_col_idx == 7 and len(row) > 6 and pd.notna(row.iloc[6]):
                    use_idx = 6
                else:
                    continue

            try:
                price_k = int(float(row.iloc[use_idx]))
            except (ValueError, TypeError):
                continue

            if price_k <= 0:
                continue

            cur.execute('''
                INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (last_date, prod.upper(), last_cust, last_car, qty, price_k, sheet))
            total_rows += 1

    conn.commit()
    conn.close()
    if total_rows > 0:
        print(f"🎉 [Khởi tạo tự động] Đã nạp thành công {total_rows} đơn hàng từ Excel vào SQLite!", flush=True)


# ── Khởi tạo DB & nạp Excel an toàn ───────────────────────────
def init_db_and_import_excel():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
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

    cur.execute('SELECT COUNT(*) FROM orders')
    cnt = cur.fetchone()[0]
    conn.close()

    # Nếu DB chưa có dữ liệu và file Excel có tồn tại, tự nạp trực tiếp bằng hàm nội bộ
    if cnt == 0 and os.path.exists(EXCEL_FILE):
        try:
            run_internal_excel_import()
        except Exception as e:
            print(f"⚠️ Lỗi khi nạp dữ liệu từ file Excel: {e}", flush=True)


# ── KHỞI CHẠY KHỞI TẠO NGAY KHI NẠP MODULE (Cho WSGI / PythonAnywhere) ──
# Đảm bảo bảng orders luôn tồn tại và dữ liệu luôn sẵn sàng ngay cả khi chạy qua WSGI server
try:
    init_db_and_import_excel()
except Exception as _e:
    print(f"⚠️ Lỗi khởi tạo DB ban đầu: {_e}", flush=True)



# ══════════════════════════════════════════════════════════════
#  LOG THEO DÕI THIẾT BỊ TRUY CẬP (BẰNG TIẾNG VIỆT)
# ══════════════════════════════════════════════════════════════
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_client_device_name(user_agent, ip):
    ua = (user_agent or '').lower()
    if 'iphone' in ua:
        dev = "📱 iPhone"
    elif 'ipad' in ua:
        dev = "📱 Máy tính bảng iPad"
    elif 'android' in ua:
        dev = "📱 Điện thoại Android"
    elif 'windows' in ua:
        dev = "💻 Máy tính Windows"
    elif 'macintosh' in ua or 'mac os' in ua:
        dev = "💻 Máy tính Mac"
    else:
        dev = "📱 Thiết bị di động"

    if ip in ('127.0.0.1', '::1', 'localhost'):
        return f"{dev} [Máy tính chủ]"
    return f"{dev} [IP: {ip}]"


@den_bp.before_request
def log_user_access():
    path = request.path
    if path in ('/favicon.ico', '/robots.txt') or path.startswith('/static'):
        return

    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')
    dev_name = get_client_device_name(ua, ip)
    now_str = datetime.now().strftime("%H:%M:%S")

    if path == '/':
        print(f"  🔔 [{now_str}] {dev_name} -> 🌐 Vừa mở giao diện ứng dụng", flush=True)
    elif path == '/api/save_batch':
        print(f"  💾 [{now_str}] {dev_name} -> ✅ Vừa LƯU TOÀN BỘ ĐƠN HÀNG vào hệ thống!", flush=True)
    elif path == '/api/save_order':
        print(f"  ✏️ [{now_str}] {dev_name} -> 📝 Vừa lưu/sửa một đơn hàng", flush=True)
    elif path.startswith('/api/delete_order'):
        print(f"  🗑️ [{now_str}] {dev_name} -> ❌ Vừa xóa một đơn hàng khỏi báo cáo", flush=True)
    elif path == '/api/sync_excel':
        print(f"  🔄 [{now_str}] {dev_name} -> 📊 Vừa bấm đồng bộ dữ liệu ra Excel", flush=True)
    elif path.startswith('/api/search'):
        q = request.args.get('q', '')
        if q:
            print(f"  🔍 [{now_str}] {dev_name} -> 🔎 Đang tra cứu lịch sử: '{q}'", flush=True)
    elif path.startswith('/api/report'):
        m = request.args.get('month', '')
        y = request.args.get('year', '')
        if m and y:
            print(f"  📊 [{now_str}] {dev_name} -> 📈 Xem báo cáo Tháng {int(m):02d}/{y}", flush=True)


# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@den_bp.route('/')
def index():
    cur_year, cur_month = get_current_cycle()
    conn = get_db()
    cur  = conn.cursor()

    # Nếu kỳ hiện tại chưa có đơn nào, kiểm tra xem có kỳ trước nào có dữ liệu không
    cur.execute("""
        SELECT COUNT(*) FROM orders 
        WHERE order_date >= ? AND order_date <= ?
    """, get_cycle_dates(cur_year, cur_month))
    cur_has_data = (cur.fetchone()[0] or 0) > 0

    if not cur_has_data:
        cur.execute("SELECT MAX(order_date) FROM orders")
        latest_date_row = cur.fetchone()
        if latest_date_row and latest_date_row[0]:
            try:
                ld = datetime.strptime(latest_date_row[0], "%Y-%m-%d")
                if ld.day <= 8:
                    cur_month = 12 if ld.month == 1 else ld.month - 1
                    cur_year  = ld.year - 1 if ld.month == 1 else ld.year
                else:
                    cur_month = ld.month
                    cur_year  = ld.year
            except Exception:
                pass

    cur.execute("SELECT DISTINCT product_name  FROM orders WHERE product_name  != '' ORDER BY product_name")
    all_products  = [r[0] for r in cur.fetchall() if r[0]]

    cur.execute("SELECT DISTINCT customer_name FROM orders WHERE customer_name != '' ORDER BY customer_name")
    all_customers = [r[0] for r in cur.fetchall() if r[0]]

    cur.execute("SELECT DISTINCT car_model     FROM orders WHERE car_model     != '' ORDER BY car_model")
    all_cars      = [r[0] for r in cur.fetchall() if r[0]]

    # Tạo bản đồ giá sản phẩm để tự động điền khi người dùng chọn/nhập tên
    product_price_map = {p['name']: p['price'] for p in QUICK_PRODUCTS}
    cur.execute("""
        SELECT product_name, CAST(ROUND(AVG(price_k / MAX(quantity, 1))) AS INTEGER)
        FROM orders
        WHERE product_name != '' AND price_k > 0
        GROUP BY product_name
    """)
    for p_name, avg_p in cur.fetchall():
        if p_name and p_name not in product_price_map and avg_p:
            product_price_map[p_name] = avg_p

    conn.close()

    return render_template(
        'den_index.html',
        today       = date.today().strftime("%Y-%m-%d"),
        today_vn    = date.today().strftime("%d/%m/%Y"),
        cur_year    = cur_year,
        cur_month   = cur_month,
        all_products   = all_products,
        all_customers  = all_customers,
        all_cars       = all_cars,
        product_price_map_json = json.dumps(product_price_map, ensure_ascii=False),
    )


@den_bp.route('/api/report')
def api_report():
    month = int(request.args.get('month'))
    year  = int(request.args.get('year'))
    start_date, end_date = get_cycle_dates(year, month)

    # Tháng trước
    prev_month = 12 if month == 1 else month - 1
    prev_year  = year - 1 if month == 1 else year
    prev_start, prev_end = get_cycle_dates(prev_year, prev_month)

    # Tháng sau
    next_month = 1 if month == 12 else month + 1
    next_year  = year + 1 if month == 12 else year
    next_start, next_end = get_cycle_dates(next_year, next_month)

    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        SELECT id, order_date, product_name, customer_name, car_model, quantity, price_k
        FROM   orders
        WHERE  order_date >= ? AND order_date <= ?
        ORDER  BY order_date ASC, id ASC
    ''', (start_date, end_date))
    rows = [dict(r) for r in cur.fetchall()]

    # Doanh thu tháng trước
    cur.execute('''
        SELECT COALESCE(SUM(price_k), 0)
        FROM   orders
        WHERE  order_date >= ? AND order_date <= ?
    ''', (prev_start, prev_end))
    prev_total_k = cur.fetchone()[0]

    # Doanh thu tháng sau
    cur.execute('''
        SELECT COALESCE(SUM(price_k), 0)
        FROM   orders
        WHERE  order_date >= ? AND order_date <= ?
    ''', (next_start, next_end))
    next_total_k = cur.fetchone()[0]
    conn.close()

    total_k      = 0
    total_qty    = 0
    car_visits   = set()
    prod_counter = {}

    for r in rows:
        try:
            r['date_vn'] = datetime.strptime(r['order_date'], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            r['date_vn'] = r['order_date']
        total_k  += r['price_k']
        total_qty += r['quantity']
        car_visits.add(f"{r['order_date']}_{r['customer_name']}_{r['car_model']}")
        prod_counter[r['product_name']] = prod_counter.get(r['product_name'], 0) + r['quantity']

    total_vnd  = total_k * 1000
    prev_vnd   = prev_total_k * 1000
    next_vnd   = next_total_k * 1000
    unique_cars = len(car_visits)
    avg_per_car = int(total_vnd / unique_cars) if unique_cars > 0 else 0

    # So với tháng trước
    if prev_vnd > 0:
        diff_p = total_vnd - prev_vnd
        pct_p  = diff_p / prev_vnd * 100
        sign_p = "+" if diff_p >= 0 else ""
        color_p = "#86efac" if diff_p >= 0 else "#fca5a5"
        diff_prev_text = f"◀ So với T.{prev_month:02d}: <b style='color:{color_p};'>{sign_p}{pct_p:.1f}%</b> ({sign_p}{diff_p:,.0f} đ)".replace(",", ".")
    else:
        diff_prev_text = f"◀ So với T.{prev_month:02d}: Chưa có số liệu"

    # So với tháng sau
    if next_vnd > 0:
        diff_n = total_vnd - next_vnd
        pct_n  = diff_n / next_vnd * 100
        sign_n = "+" if diff_n >= 0 else ""
        color_n = "#86efac" if diff_n >= 0 else "#fca5a5"
        diff_next_text = f"▶ So với T.{next_month:02d}: <b style='color:{color_n};'>{sign_n}{pct_n:.1f}%</b> ({sign_n}{diff_n:,.0f} đ)".replace(",", ".")
    else:
        diff_next_text = f"▶ So với T.{next_month:02d}: Chưa có số liệu"

    top3     = sorted(prod_counter.items(), key=lambda x: x[1], reverse=True)[:3]
    top_html = "<br>".join(
        [f"• {k}: <span style='color:#1e40af'>{v} bộ</span>" for k, v in top3]
    )

    return jsonify({
        "start_vn":        datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y"),
        "end_vn":          datetime.strptime(end_date,   "%Y-%m-%d").strftime("%d/%m/%Y"),
        "rows":            rows,
        "total_vnd":       total_vnd,
        "total_qty":       total_qty,
        "unique_cars":     unique_cars,
        "avg_per_car":     avg_per_car,
        "diff_prev_text":  diff_prev_text,
        "diff_next_text":  diff_next_text,
        "diff_text":       f"{diff_prev_text}<br>{diff_next_text}",
        "top_products_html": top_html,
    })


@den_bp.route('/api/analytics')
def api_analytics():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        SELECT order_date, product_name, customer_name, car_model, quantity, price_k
        FROM   orders
        ORDER  BY order_date ASC
    ''')
    rows = cur.fetchall()
    conn.close()

    m_data = {}
    y_data = {}
    prod_rev = {}
    car_rev = {}

    all_time_vnd  = 0
    all_time_qty  = 0
    all_time_cars = set()

    for r in rows:
        try:
            d = datetime.strptime(r['order_date'], "%Y-%m-%d")
            if d.day <= 8:
                cy = d.year - 1 if d.month == 1 else d.year
                cm = 12 if d.month == 1 else d.month - 1
            else:
                cy, cm = d.year, d.month
        except Exception:
            continue

        vnd   = r['price_k'] * 1000
        qty   = r['quantity']
        visit = f"{r['order_date']}_{r['customer_name']}_{r['car_model']}"

        all_time_vnd += vnd
        all_time_qty += qty
        all_time_cars.add(visit)

        # Tháng
        m_key = (cy, cm)
        if m_key not in m_data:
            m_data[m_key] = {'vnd': 0, 'qty': 0, 'cars': set()}
        m_data[m_key]['vnd'] += vnd
        m_data[m_key]['qty'] += qty
        m_data[m_key]['cars'].add(visit)

        # Năm
        if cy not in y_data:
            y_data[cy] = {
                'vnd': 0, 'qty': 0, 'cars': set(), 
                'months': {}, 'months_detail': {}, 
                'prods': {}, 'cars_model': {}
            }
        y_data[cy]['vnd'] += vnd
        y_data[cy]['qty'] += qty
        y_data[cy]['cars'].add(visit)
        y_data[cy]['months'][cm] = y_data[cy]['months'].get(cm, 0) + vnd

        if cm not in y_data[cy]['months_detail']:
            y_data[cy]['months_detail'][cm] = {'vnd': 0, 'qty': 0, 'cars': set()}
        y_data[cy]['months_detail'][cm]['vnd'] += vnd
        y_data[cy]['months_detail'][cm]['qty'] += qty
        y_data[cy]['months_detail'][cm]['cars'].add(visit)

        # Sản phẩm
        p_name = (r['product_name'] or '').strip()
        if p_name:
            if p_name not in prod_rev:
                prod_rev[p_name] = {'vnd': 0, 'qty': 0}
            prod_rev[p_name]['vnd'] += vnd
            prod_rev[p_name]['qty'] += qty

            if p_name not in y_data[cy]['prods']:
                y_data[cy]['prods'][p_name] = {'vnd': 0, 'qty': 0}
            y_data[cy]['prods'][p_name]['vnd'] += vnd
            y_data[cy]['prods'][p_name]['qty'] += qty

        # Dòng xe
        c_name = (r['car_model'] or '').strip().upper()
        if c_name:
            if c_name not in car_rev:
                car_rev[c_name] = {'vnd': 0, 'count': 0}
            car_rev[c_name]['vnd'] += vnd
            car_rev[c_name]['count'] += 1

            if c_name not in y_data[cy]['cars_model']:
                y_data[cy]['cars_model'][c_name] = {'vnd': 0, 'count': 0}
            y_data[cy]['cars_model'][c_name]['vnd'] += vnd
            y_data[cy]['cars_model'][c_name]['count'] += 1

    if not y_data:
        return jsonify({"empty": True})

    # Tìm năm cao nhất / thấp nhất
    sorted_years = sorted(y_data.items(), key=lambda x: x[1]['vnd'], reverse=True)
    best_year_item = sorted_years[0]
    worst_year_item = sorted_years[-1]

    best_year = {
        "year": best_year_item[0],
        "total_vnd": best_year_item[1]['vnd'],
        "qty": best_year_item[1]['qty'],
        "cars": len(best_year_item[1]['cars'])
    }
    worst_year = {
        "year": worst_year_item[0],
        "total_vnd": worst_year_item[1]['vnd'],
        "qty": worst_year_item[1]['qty'],
        "cars": len(worst_year_item[1]['cars'])
    }

    # Tìm tháng cao nhất / thấp nhất (chỉ xét các tháng có doanh thu > 0)
    m_with_rev = [item for item in m_data.items() if item[1]['vnd'] > 0]
    sorted_months = sorted(m_with_rev, key=lambda x: x[1]['vnd'], reverse=True)
    best_m_item = sorted_months[0]
    worst_m_item = sorted_months[-1]

    best_month = {
        "month": best_m_item[0][1],
        "year": best_m_item[0][0],
        "month_str": f"Tháng {best_m_item[0][1]:02d}/{best_m_item[0][0]}",
        "total_vnd": best_m_item[1]['vnd'],
        "qty": best_m_item[1]['qty'],
        "cars": len(best_m_item[1]['cars'])
    }
    worst_month = {
        "month": worst_m_item[0][1],
        "year": worst_m_item[0][0],
        "month_str": f"Tháng {worst_m_item[0][1]:02d}/{worst_m_item[0][0]}",
        "total_vnd": worst_m_item[1]['vnd'],
        "qty": worst_m_item[1]['qty'],
        "cars": len(worst_m_item[1]['cars'])
    }

    # Danh sách từng năm theo thứ tự thời gian & chi tiết từng năm
    all_years = sorted(y_data.keys())
    yearly_summary = []
    by_year = {}

    for y in all_years:
        info = y_data[y]
        m_detail = info['months_detail']

        valid_m = [(m, data) for m, data in m_detail.items() if data['vnd'] > 0]
        if valid_m:
            b_m_tuple = max(valid_m, key=lambda x: x[1]['vnd'])
            w_m_tuple = min(valid_m, key=lambda x: x[1]['vnd'])
            b_m_info = {
                "month": b_m_tuple[0],
                "month_str": f"Tháng {b_m_tuple[0]:02d}/{y}",
                "total_vnd": b_m_tuple[1]['vnd'],
                "qty": b_m_tuple[1]['qty'],
                "cars": len(b_m_tuple[1]['cars'])
            }
            w_m_info = {
                "month": w_m_tuple[0],
                "month_str": f"Tháng {w_m_tuple[0]:02d}/{y}",
                "total_vnd": w_m_tuple[1]['vnd'],
                "qty": w_m_tuple[1]['qty'],
                "cars": len(w_m_tuple[1]['cars'])
            }
            b_m_str = f"T.{b_m_tuple[0]:02d} ({b_m_tuple[1]['vnd']:,.0f} đ)".replace(",", ".")
            w_m_str = f"T.{w_m_tuple[0]:02d} ({w_m_tuple[1]['vnd']:,.0f} đ)".replace(",", ".")
        else:
            b_m_info = {"month": 0, "month_str": "--", "total_vnd": 0, "qty": 0, "cars": 0}
            w_m_info = {"month": 0, "month_str": "--", "total_vnd": 0, "qty": 0, "cars": 0}
            b_m_str = "--"
            w_m_str = "--"

        yearly_summary.append({
            "year": y,
            "total_vnd": info['vnd'],
            "qty": info['qty'],
            "cars": len(info['cars']),
            "best_month": b_m_str,
            "worst_month": w_m_str
        })

        months_12 = []
        for m in range(1, 13):
            m_item = m_detail.get(m, {'vnd': 0, 'qty': 0, 'cars': set()})
            months_12.append({
                "month": m,
                "month_str": f"Tháng {m:02d}",
                "total_vnd": m_item['vnd'],
                "qty": m_item['qty'],
                "cars": len(m_item['cars']),
                "is_best": (b_m_info['month'] == m and m_item['vnd'] > 0),
                "is_worst": (w_m_info['month'] == m and m_item['vnd'] > 0)
            })

        year_top_products = [
            {"name": k, "total_vnd": v['vnd'], "qty": v['qty']}
            for k, v in sorted(info['prods'].items(), key=lambda x: x[1]['vnd'], reverse=True)[:6]
        ]

        year_top_cars = [
            {"model": k, "count": v['count'], "total_vnd": v['vnd']}
            for k, v in sorted(info['cars_model'].items(), key=lambda x: x[1]['count'], reverse=True)[:6]
        ]

        by_year[str(y)] = {
            "year": y,
            "total_vnd": info['vnd'],
            "qty": info['qty'],
            "cars": len(info['cars']),
            "best_month": b_m_info,
            "worst_month": w_m_info,
            "months_12": months_12,
            "top_products": year_top_products,
            "top_cars": year_top_cars
        }

    # Ma trận doanh thu 12 tháng của các năm cho biểu đồ so sánh
    monthly_matrix = {
        "years": all_years,
        "months": [f"Tháng {m:02d}" for m in range(1, 13)],
        "series": {}
    }
    for y in all_years:
        monthly_matrix["series"][str(y)] = [
            y_data[y]['months'].get(m, 0) for m in range(1, 13)
        ]

    # Top 5 tháng cao nhất
    top_5_months = []
    for rank, (m_k, val) in enumerate(sorted_months[:5], 1):
        top_5_months.append({
            "rank": rank,
            "month_str": f"Tháng {m_k[1]:02d}/{m_k[0]}",
            "total_vnd": val['vnd'],
            "qty": val['qty'],
            "cars": len(val['cars'])
        })

    # Top 6 sản phẩm doanh thu cao nhất
    top_products = [
        {"name": k, "total_vnd": v['vnd'], "qty": v['qty']}
        for k, v in sorted(prod_rev.items(), key=lambda x: x[1]['vnd'], reverse=True)[:6]
    ]

    # Top 6 dòng xe làm đèn nhiều nhất
    top_cars = [
        {"model": k, "count": v['count'], "total_vnd": v['vnd']}
        for k, v in sorted(car_rev.items(), key=lambda x: x[1]['count'], reverse=True)[:6]
    ]

    avg_monthly_vnd = int(all_time_vnd / max(len(m_with_rev), 1))

    return jsonify({
        "all_time_vnd": all_time_vnd,
        "all_time_qty": all_time_qty,
        "all_time_cars": len(all_time_cars),
        "total_active_months": len(m_with_rev),
        "avg_monthly_vnd": avg_monthly_vnd,
        "best_year": best_year,
        "worst_year": worst_year,
        "best_month": best_month,
        "worst_month": worst_month,
        "yearly_summary": yearly_summary,
        "monthly_matrix": monthly_matrix,
        "top_5_months": top_5_months,
        "top_products": top_products,
        "top_cars": top_cars,
        "by_year": by_year,
        "years": all_years,
    })


@den_bp.route('/api/save_order', methods=['POST'])
def api_save_order():
    data          = request.json
    order_id      = data.get('id')
    order_date    = data['order_date']
    product_name  = data['product_name']
    customer_name = data.get('customer_name', '')
    car_model     = data.get('car_model', '')
    quantity      = int(data.get('quantity', 1))
    price_k       = int(data['price_k'])

    conn = get_db()
    cur  = conn.cursor()
    if order_id:
        cur.execute('''
            UPDATE orders
            SET order_date=?, product_name=?, customer_name=?, car_model=?, quantity=?, price_k=?
            WHERE id=?
        ''', (order_date, product_name, customer_name, car_model, quantity, price_k, order_id))
    else:
        cur.execute('''
            INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_date, product_name, customer_name, car_model, quantity, price_k))
    conn.commit()
    conn.close()

    # Xác định kỳ báo cáo của ngày vừa nhập (mùng 9 → mùng 8)
    d = datetime.strptime(order_date, "%Y-%m-%d")
    if d.day <= 8:
        c_month = 12 if d.month == 1 else d.month - 1
        c_year  = d.year - 1 if d.month == 1 else d.year
    else:
        c_month = d.month
        c_year  = d.year

    return jsonify({"success": True, "cycle_month": c_month, "cycle_year": c_year})


@den_bp.route('/api/save_batch', methods=['POST'])
def api_save_batch():
    """Lưu toàn bộ danh sách đơn hàng nháp vào database cùng lúc."""
    items = request.json.get('items', [])
    if not items:
        return jsonify({"success": False, "message": "Danh sách đơn trống!"})

    conn = get_db()
    cur  = conn.cursor()
    last_date = None

    for item in items:
        order_date    = item['order_date']
        product_name  = item['product_name'].strip().upper()
        customer_name = item.get('customer_name', '').strip().upper()
        car_model     = item.get('car_model', '').strip().upper()
        quantity      = int(item.get('quantity', 1))
        price_k       = int(item['price_k'])
        last_date     = order_date

        cur.execute('''
            INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_date, product_name, customer_name, car_model, quantity, price_k))

    conn.commit()
    conn.close()

    # Xác định kỳ báo cáo theo ngày của đơn
    c_month, c_year = get_current_cycle()
    if last_date:
        try:
            d = datetime.strptime(last_date, "%Y-%m-%d")
            if d.day <= 8:
                c_month = 12 if d.month == 1 else d.month - 1
                c_year  = d.year - 1 if d.month == 1 else d.year
            else:
                c_month = d.month
                c_year  = d.year
        except Exception:
            pass

    return jsonify({
        "success": True,
        "count": len(items),
        "cycle_month": c_month,
        "cycle_year": c_year
    })



@den_bp.route('/api/delete_order/<int:order_id>', methods=['DELETE'])
def api_delete_order(order_id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@den_bp.route('/api/search')
def api_search():
    q    = f"%{request.args.get('q', '').upper()}%"
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('''
        SELECT order_date, product_name, customer_name, car_model, price_k
        FROM   orders
        WHERE  UPPER(customer_name) LIKE ?
           OR  UPPER(car_model)     LIKE ?
           OR  UPPER(product_name)  LIKE ?
        ORDER  BY order_date DESC
        LIMIT  25
    ''', (q, q, q))
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            d['date_vn'] = datetime.strptime(d['order_date'], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            d['date_vn'] = d['order_date']
        rows.append(d)
    conn.close()
    return jsonify(rows)


@den_bp.route('/api/sync_excel', methods=['POST'])
def api_sync_excel():
    """Ghi toàn bộ dữ liệu DB ra file Excel (tạo mới nếu chưa có)."""
    try:
        import openpyxl
        target_file = EXCEL_FILE if os.path.exists(EXCEL_FILE) else EXPORT_EXCEL_FILE
        wb = openpyxl.load_workbook(target_file) if os.path.exists(target_file) else openpyxl.Workbook()

        conn = get_db()
        cur  = conn.cursor()

        for year in [2025, 2026]:
            for month in range(1, 13):
                s_date, e_date = get_cycle_dates(year, month)
                cur.execute('''
                    SELECT order_date, product_name, customer_name, car_model, quantity, price_k
                    FROM   orders
                    WHERE  order_date >= ? AND order_date <= ?
                    ORDER  BY order_date ASC, id ASC
                ''', (s_date, e_date))
                rows = cur.fetchall()
                if not rows:
                    continue

                sheet_name = f"THÁNG{month}{str(year)[2:]}"
                variants   = [sheet_name,
                              f"THÁNG {month}{str(year)[2:]}",
                              f"THÁNG {month:02d}{str(year)[2:]}"]

                if year == 2026 and month == 7 and "THÁNG727" in wb.sheetnames:
                    ws = wb["THÁNG727"]
                    ws.delete_rows(1, ws.max_row)
                else:
                    found = next((v for v in variants if v in wb.sheetnames), None)
                    if found:
                        ws = wb[found]
                        ws.delete_rows(1, ws.max_row)
                    else:
                        ws = wb.create_sheet(title=sheet_name)

                ws.append([f"DOANH THU ĐÈN THÁNG {month:02d}/{year}", "", "", "", "", "", ""])
                ws.append(["", "", "", "", "", "", ""])
                ws.append(["STT", "NGÀY", "TÊN SẢN PHẨM", "TÊN KHÁCH HÀNG", "LOẠI XE", "SỐ LƯỢNG", "GIÁ BÁN"])

                total_k = 0
                for idx, r in enumerate(rows, 1):
                    total_k += r['price_k']
                    ws.append([idx, r['order_date'], r['product_name'],
                               r['customer_name'], r['car_model'], r['quantity'], r['price_k']])
                ws.append(["", "", "", "", "", "TỔNG (VNĐ):", total_k * 1000])

        conn.close()
        wb.save(target_file)
        return jsonify({"success": True, "message": f"Đã đồng bộ thành công vào file {target_file}!"})

    except PermissionError:
        return jsonify({"success": False,
                        "message": f"File {EXCEL_FILE} đang mở trên Excel! Hãy tắt Excel rồi thử lại."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
#  Lệnh chạy: python app.py
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import socket
    import atexit
    init_db_and_import_excel()

    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    local_ip = get_local_ip()

    # Đăng ký mDNS tên miền nội bộ baocaoden.local cho cả điện thoại & máy tính
    zeroconf_obj = None
    try:
        from zeroconf import IPVersion, Zeroconf, ServiceInfo
        info = ServiceInfo(
            "_http._tcp.local.",
            "baocaoden._http._tcp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=5000,
            properties={"app": "doanhthu_den"},
            server="baocaoden.local.",
        )
        zeroconf_obj = Zeroconf(ip_version=IPVersion.V4Only)
        zeroconf_obj.register_service(info)
        atexit.register(zeroconf_obj.close)
    except Exception:
        pass

    print()
    print("=" * 72)
    print("       💡 ỨNG DỤNG QUẢN LÝ & BÁO CÁO DOANH THU ĐÈN")
    print("=" * 72)
    print("  🌐 ĐỊA CHỈ TRUY CẬP (Chọn 1 trong các đường dẫn sau):")
    print("  ----------------------------------------------------------------------")
    print("  📱 TRÊN ĐIỆN THOẠI (Kết nối cùng mạng WiFi):")
    print("     👉 Tên miền dễ nhớ :  http://baocaoden.local:5000")
    print(f"     👉 Hoặc địa chỉ IP :  http://{local_ip}:5000")
    print()
    print("  💻 TRÊN MÁY TÍNH NÀY:")
    print("     👉 Đường dẫn nhanh :  http://localhost:5000")
    print("     👉 Hoặc tên miền   :  http://baocaoden.local:5000")
    print("  ----------------------------------------------------------------------")
    print("  ⌨️  BẢNG PHÍM TẮT & THAO TÁC NHANH:")
    print("     • [Ctrl + C]      : Dừng / Tắt ứng dụng an toàn")
    print("     • [F5] / [Ctrl+R] : Tải lại trang trên trình duyệt")
    print("     • [Bôi đen chuột] : Sao chép đường link ở trên")
    print("  ----------------------------------------------------------------------")
    print("  📡 NHẬT KÝ KẾT NỐI (Mỗi thiết bị truy cập sẽ báo bằng tiếng Việt bên dưới):")
    print("=" * 72)
    print("", flush=True)

    standalone_app = Flask(__name__)
    standalone_app.register_blueprint(den_bp, url_prefix='/den')
    @standalone_app.route('/')
    def root():
        return redirect('/den/')
    standalone_app.run(debug=True, port=5000, host='0.0.0.0', use_reloader=False)
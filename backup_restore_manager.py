import os
import shutil
import sqlite3
import zipfile
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

DB_PATHS = {
    'tiem_lap_do.db': os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db'),
    'finance.db': os.path.join(BASE_DIR, 'app_thuchi', 'finance.db'),
    'doanhthu_den.db': os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db'),
    'gara_knowledge.db': os.path.join(BASE_DIR, 'gara_knowledge.db'),
}

def create_auto_snapshot():
    """Tạo bản sao lưu dự phòng tự động trước khi thực hiện bất kỳ lệnh nạp/khôi phục nào."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    snap_dir = os.path.join(BACKUP_DIR, f"auto_snapshot_{ts}")
    os.makedirs(snap_dir, exist_ok=True)
    
    copied = []
    for name, path in DB_PATHS.items():
        if os.path.exists(path):
            dst = os.path.join(snap_dir, name)
            shutil.copy2(path, dst)
            copied.append(name)
    return snap_dir, copied

def create_full_backup_zip():
    """Tạo file nén Zip chứa toàn bộ 4 cơ sở dữ liệu của gara để người dùng tải về máy tính."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"backup_gara_tranbinh_{ts}.zip"
    zip_path = os.path.join(BACKUP_DIR, zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, path in DB_PATHS.items():
            if os.path.exists(path):
                zf.write(path, arcname=arcname)

    return zip_path, zip_name

def sync_vpos_bak(bak_file_path):
    """
    Đồng bộ dữ liệu từ file backup VPOS (.bak SQLite):
    - Cập nhật đúng 100% giá bán, giá vốn, tồn kho, bảo hành, phân loại sản phẩm.
    - Cập nhật danh bạ khách hàng.
    - Bổ sung các đơn hàng mới nhất chưa có trong hệ thống (KHÔNG XÓA ĐƠN HÀNG CŨ).
    - Dữ liệu Thu Chi (finance.db) và Doanh Thu Đèn (doanhthu_den.db) được bảo toàn tuyệt đối.
    """
    main_db = DB_PATHS['tiem_lap_do.db']
    if not os.path.exists(main_db):
        return {"success": False, "message": "Không tìm thấy cơ sở dữ liệu tiem_lap_do.db."}

    conn_bak = sqlite3.connect(bak_file_path)
    conn_bak.row_factory = sqlite3.Row
    c_bak = conn_bak.cursor()

    conn_main = sqlite3.connect(main_db)
    conn_main.row_factory = sqlite3.Row
    c_main = conn_main.cursor()

    # 1. Cập nhật sản phẩm
    c_bak.execute("SELECT * FROM [Product]")
    bak_products = c_bak.fetchall()

    updated_count = 0
    inserted_count = 0

    for p in bak_products:
        p_code = p['product_code']
        p_name = p['product_name']
        p_cat = p['category'] or p['group'] or ''
        p_type = 'Hàng hóa' if p['type'] == 'product' else 'Dịch vụ'
        p_price = float(p['sell_price'] or 0)
        p_cost = float(p['cost_price'] or 0)
        p_stock = int(round(p['stock'] or 0))
        p_war = int(round(p['warranty_months'] or 0))
        p_war_raw = f"{p_war} tháng" if p_war > 0 else ""
        created_at = p['created_at'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        c_main.execute("SELECT id FROM products WHERE code = ?", (p_code,))
        row = c_main.fetchone()
        if row:
            c_main.execute("""
                UPDATE products 
                SET name = ?, category = ?, item_type = ?, price = ?, cost_price = ?, stock = ?, warranty_months = ?, warranty_raw = ?
                WHERE code = ?
            """, (p_name, p_cat, p_type, p_price, p_cost, p_stock, p_war, p_war_raw, p_code))
            updated_count += 1
        else:
            c_main.execute("SELECT id FROM products WHERE name = ?", (p_name,))
            row_n = c_main.fetchone()
            if row_n:
                c_main.execute("""
                    UPDATE products 
                    SET code = ?, category = ?, item_type = ?, price = ?, cost_price = ?, stock = ?, warranty_months = ?, warranty_raw = ?
                    WHERE id = ?
                """, (p_code, p_cat, p_type, p_price, p_cost, p_stock, p_war, p_war_raw, row_n['id']))
                updated_count += 1
            else:
                c_main.execute("""
                    INSERT INTO products (item_type, category, code, name, price, cost_price, stock, warranty_months, warranty_raw, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (p_type, p_cat, p_code, p_name, p_price, p_cost, p_stock, p_war, p_war_raw, str(created_at)))
                inserted_count += 1

    conn_main.commit()

    # 2. Cập nhật khách hàng
    c_main.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_code TEXT UNIQUE,
            customer_name TEXT,
            phone TEXT,
            phone2 TEXT,
            address TEXT,
            current_debt REAL DEFAULT 0,
            total_sales REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    c_bak.execute("SELECT * FROM [Customer]")
    bak_cust = c_bak.fetchall()
    cust_synced = 0
    cust_phone_map = {}
    for c in bak_cust:
        if c['customer_code']:
            cust_phone_map[c['customer_code']] = c['phone'] or ''
        c_main.execute("""
            INSERT INTO customers (customer_code, customer_name, phone, phone2, address, current_debt, total_sales, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_code) DO UPDATE SET
                customer_name = excluded.customer_name,
                phone = excluded.phone,
                phone2 = excluded.phone2,
                address = excluded.address,
                current_debt = excluded.current_debt,
                total_sales = excluded.total_sales
        """, (
            c['customer_code'],
            c['customer_name'],
            c['phone'] or '',
            c['phone2'] or '',
            c['address'] or '',
            float(c['current_debt'] or 0),
            float(c['total_sales'] or 0),
            str(c['created_at'] or '')
        ))
        cust_synced += 1

    conn_main.commit()

    # 3. Đồng bộ đơn hàng mới từ VPOS
    c_bak.execute("SELECT * FROM [Order] WHERE status != 'cancelled' ORDER BY date ASC")
    bak_orders = c_bak.fetchall()

    orders_added = 0
    items_added = 0

    for o in bak_orders:
        o_id = o['id']
        c_code = o['customer_code'] or ''
        c_name = o['customer_name'] or ''
        phone = cust_phone_map.get(c_code, '')
        total_price = float(o['total'] or 0)
        
        raw_date = str(o['date'] or '')
        install_date = raw_date[:10] if len(raw_date) >= 10 else raw_date
        
        plate = c_code if re.search(r'\d{2}[A-Z]', c_code) else ''
        if not plate:
            m_pl = re.search(r'\b(\d{2}[A-Z][0-9\.\-\s]+)\b', c_name)
            if m_pl:
                plate = m_pl.group(1).strip()
        if not plate:
            plate = c_code

        c_main.execute("""
            SELECT id FROM orders 
            WHERE (license_plate = ? OR customer_name = ?) AND install_date = ? AND ABS(total_price - ?) < 1
        """, (plate, c_name, install_date, total_price))
        found_order = c_main.fetchone()
        
        if not found_order:
            c_main.execute("""
                INSERT INTO orders (customer_name, phone, license_plate, install_date, total_price)
                VALUES (?, ?, ?, ?, ?)
            """, (c_name, phone, plate, install_date, total_price))
            new_order_id = c_main.lastrowid
            orders_added += 1

            c_bak.execute("SELECT * FROM [OrderItem] WHERE order_id = ?", (o_id,))
            bak_items = c_bak.fetchall()
            for item in bak_items:
                i_name = item['product_name']
                i_unit_price = float(item['unit_price'] or 0)
                i_line_total = float(item['line_total'] or 0)
                i_qty = int(round(item['qty'] or 1))
                i_war = int(round(item['warranty_months'] or 0))

                c_main.execute("""
                    INSERT INTO order_items (order_id, item_name, price, warranty_months, orig_price, unit_price, qty)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (new_order_id, i_name, i_line_total, i_war, i_unit_price, i_unit_price, i_qty))
                items_added += 1

    conn_main.commit()

    # 4. Dọn dẹp gara_knowledge.db nếu có quy định trùng
    try:
        conn_gk = sqlite3.connect(DB_PATHS['gara_knowledge.db'])
        c_gk = conn_gk.cursor()
        c_gk.execute("DELETE FROM gara_memory WHERE id = 13 OR topic LIKE '%F10%' OR clean_topic LIKE '%f10%'")
        conn_gk.commit()
        conn_gk.close()
    except Exception:
        pass

    conn_bak.close()
    conn_main.close()

    return {
        "success": True,
        "type": "vpos_bak",
        "message": f"Nạp thành công dữ liệu VPOS: Cập nhật {updated_count} sản phẩm ({inserted_count} SP mới), đồng bộ {cust_synced} khách hàng, bổ sung {orders_added} hóa đơn mới.",
        "stats": {
            "products_updated": updated_count,
            "products_inserted": inserted_count,
            "customers_synced": cust_synced,
            "orders_added": orders_added,
            "items_added": items_added
        }
    }

def restore_uploaded_file(file_path):
    """
    Xử lý nạp / khôi phục file được tải lên (tự động phát hiện Zip toàn bộ, file VPOS .bak, hoặc file .db).
    Luôn tạo bản sao lưu snapshot tự động trước khi thao tác!
    """
    snap_dir, snap_files = create_auto_snapshot()

    # Kiểm tra nếu là file ZIP
    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path, 'r') as zf:
            namelist = zf.namelist()
            restored = []
            for arcname in namelist:
                base_arc = os.path.basename(arcname)
                if base_arc in DB_PATHS:
                    dest = DB_PATHS[base_arc]
                    with zf.open(arcname) as src, open(dest, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    restored.append(base_arc)

            return {
                "success": True,
                "type": "full_zip",
                "message": f"Đã khôi phục thành công các cơ sở dữ liệu từ file Zip: {', '.join(restored)}.",
                "snapshot": snap_dir
            }

    # Kiểm tra nếu là file SQLite (.bak hoặc .db)
    try:
        conn = sqlite3.connect(file_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]
        conn.close()
    except Exception as e:
        return {"success": False, "message": f"File không phải cơ sở dữ liệu SQLite hoặc Zip hợp lệ: {e}"}

    # Phân loại theo cấu trúc bảng:
    # 1. File VPOS backup (.bak)
    if 'Product' in tables and 'Customer' in tables:
        res = sync_vpos_bak(file_path)
        res["snapshot"] = snap_dir
        return res

    # 2. File Sổ Thu Chi (finance.db)
    if 'transactions' in tables and 'periods' in tables:
        dest = DB_PATHS['finance.db']
        shutil.copy2(file_path, dest)
        return {
            "success": True,
            "type": "finance_db",
            "message": "Đã khôi phục thành công cơ sở dữ liệu Sổ Quản Lý Thu Chi (finance.db).",
            "snapshot": snap_dir
        }

    # 3. File Báo Cáo Doanh Thu Đèn (doanhthu_den.db)
    if 'orders' in tables:
        # Kiểm tra xem có cột sheet_origin hoặc product_name không
        conn = sqlite3.connect(file_path)
        cols = [col[1] for col in conn.cursor().execute("PRAGMA table_info(orders)").fetchall()]
        conn.close()
        if 'product_name' in cols or 'sheet_origin' in cols:
            dest = DB_PATHS['doanhthu_den.db']
            shutil.copy2(file_path, dest)
            return {
                "success": True,
                "type": "den_db",
                "message": "Đã khôi phục thành công cơ sở dữ liệu Báo Cáo Doanh Thu Đèn (doanhthu_den.db).",
                "snapshot": snap_dir
            }

    # 4. File Bán Hàng & Kho (tiem_lap_do.db)
    if 'products' in tables and 'orders' in tables and 'order_items' in tables:
        dest = DB_PATHS['tiem_lap_do.db']
        shutil.copy2(file_path, dest)
        return {
            "success": True,
            "type": "banhang_db",
            "message": "Đã khôi phục thành công cơ sở dữ liệu Bán Hàng & Kho (tiem_lap_do.db).",
            "snapshot": snap_dir
        }

    return {"success": False, "message": f"Không nhận diện được bảng phù hợp trong file (các bảng tìm thấy: {', '.join(tables[:5])})."}


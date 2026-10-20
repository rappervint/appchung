import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Chuẩn hóa số điện thoại trong tiem_lap_do.db
db_paths = [
    '/home/rappervint/appchung/app_banhang/tiem_lap_do.db',
    os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
]

for db_path in db_paths:
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT id, phone FROM orders WHERE phone != ''")
            rows = c.fetchall()

            fixed = 0
            for oid, phone in rows:
                p = str(phone).strip()
                changed = False
                if p.endswith('.0'):
                    p = p[:-2]
                    changed = True
                if p and not p.startswith('0') and len(p) in (9, 10) and p.isdigit():
                    p = '0' + p
                    changed = True
                if changed:
                    c.execute("UPDATE orders SET phone = ? WHERE id = ?", (p, oid))
                    fixed += 1

            conn.commit()
            conn.close()
            print(f"DONE: Da sua thanh cong {fixed} so dien thoai trong {db_path}!")
            break
        except Exception as e:
            print(f"Loi sua SDT {db_path}: {e}")

# 2. Xóa khoản chi 2026đ do test câu lệnh trước đó trong finance.db
finance_paths = [
    '/home/rappervint/appchung/app_thuchi/finance.db',
    os.path.join(BASE_DIR, 'app_thuchi', 'finance.db')
]

for fpath in finance_paths:
    if os.path.exists(fpath):
        try:
            fconn = sqlite3.connect(fpath)
            fc = fconn.cursor()
            fc.execute("DELETE FROM transactions WHERE amount = 2026 OR note LIKE '%cẩm tuyền%' OR note LIKE '%cam tuyen%' OR note LIKE '%v20 base%'")
            deleted = fc.rowcount
            fconn.commit()
            fconn.close()
            if deleted > 0:
                print(f"DONE: Da xoa {deleted} giao dich thu/chi nhap sai trong {fpath}!")
        except Exception as e:
            print(f"Loi don dep finance.db {fpath}: {e}")

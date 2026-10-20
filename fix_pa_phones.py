import sqlite3

db_path = '/home/rappervint/appchung/app_banhang/tiem_lap_do.db'
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
print(f"DONE: Da sua thanh cong {fixed} so dien thoai tren PythonAnywhere!")

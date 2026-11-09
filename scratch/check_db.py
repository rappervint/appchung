import sqlite3

conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("SELECT id, topic, keywords, price_info FROM gara_memory WHERE keywords LIKE '%phan tich%' OR keywords LIKE '%6tr%' OR topic LIKE '%Xe 7%'")
rows = c.fetchall()
print(f"Polluted rows found: {len(rows)}")
for r in rows:
    print(f"ID: {r[0]} | Topic: {r[1][:50]} | Kws: {r[2]}")


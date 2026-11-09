import sys
sys.path.insert(0, '.')
import knowledge_base

q = "da nappa xe 4 chỗ giá sao"
clean = knowledge_base.remove_accents(q).lower()
feat = knowledge_base.extract_knowledge_features(clean)
print("Features of query:", feat)

# Let's inspect rows in gara_memory for nappa
import sqlite3
conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("SELECT id, topic, clean_topic, keywords FROM gara_memory WHERE clean_topic LIKE '%nappa%'")
for r in c.fetchall():
    print(r)
    m_feat = knowledge_base.extract_knowledge_features(f"{r[2]} {r[3]}")
    print("  Row feat:", m_feat)


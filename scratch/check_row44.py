import sys
sys.path.insert(0, '.')
import knowledge_base
import sqlite3

conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("SELECT id, topic, clean_topic, keywords, raw_content FROM gara_memory WHERE id = 44")
r = c.fetchone()
print("ID 44 topic:", r[1])
print("clean_topic:", r[2])
print("keywords:", r[3])
text_to_extract = f"{r[2]} {r[4]} {r[3]}"
m_feat = knowledge_base.extract_knowledge_features(text_to_extract)
print("m_feat:", m_feat)

# Let's check topic and keywords ONLY:
feat_core = knowledge_base.extract_knowledge_features(f"{r[2]} {r[3]}")
print("feat_core (without raw_content):", feat_core)


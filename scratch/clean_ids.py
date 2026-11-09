import sqlite3
import json

conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("UPDATE gara_memory SET keywords = 'da simili 7 cho, boc da simili 7 cho, san simili 7 cho, gia da simili 7 cho' WHERE id = 31")
c.execute("UPDATE gara_memory SET keywords = 'da cong nghiep 4 cho, boc da cong nghiep 4 cho, da cn 4 cho, gia da cong nghiep 4 cho' WHERE id = 35")
conn.commit()

# Also sync to knowledge_seed.json
c.execute("SELECT topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply FROM gara_memory")
all_mem = c.fetchall()
conn.close()

seed_list = []
for r in all_mem:
    seed_list.append({
        "topic": r[0], "clean_topic": r[1], "keywords": r[2], "raw_content": r[3],
        "price_info": r[4], "options_info": r[5], "formatted_reply": r[6]
    })
with open('knowledge_seed.json', 'w', encoding='utf-8') as f_s:
    json.dump(seed_list, f_s, ensure_ascii=False, indent=2)

print('Updated ID 31 and 35 and exported knowledge_seed.json successfully')


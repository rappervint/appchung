import sys
sys.path.insert(0, '.')
import knowledge_base
import sqlite3

q = "da nappa xe 4 chỗ giá sao"
clean = knowledge_base.remove_accents(q).lower()
q_feat = knowledge_base.extract_knowledge_features(clean)

conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("SELECT id, topic, clean_topic, keywords, raw_content, formatted_reply FROM gara_memory ORDER BY id DESC")
rows = c.fetchall()
conn.close()

for r in rows:
    mem_id, topic, clean_topic, keywords_str, raw_content, formatted_reply = r
    m_feat = knowledge_base.extract_knowledge_features(f"{clean_topic} {raw_content} {keywords_str}")

    # Check rule 2, 3, etc.
    if q_feat['subject'] != 'other' and m_feat['subject'] != 'other':
        if q_feat['subject'] != m_feat['subject']:
            continue

    if 'cheap' in q_feat['qualifiers']:
        if 'cheap' not in m_feat['qualifiers']:
            continue

    if 'suv' in q_feat['qualifiers'] and 'suv' not in m_feat['qualifiers']:
        continue
    if 'sedan' in q_feat['qualifiers'] and 'sedan' not in m_feat['qualifiers']:
        continue

    if 'mat_duc_lo' in m_feat['qualifiers'] and 'mat_duc_lo' not in q_feat['qualifiers']:
        continue

    mat_tags = {'mat_simili', 'mat_nappa', 'mat_cong_nghiep'}
    q_mats = q_feat['qualifiers'] & mat_tags
    m_mats = m_feat['qualifiers'] & mat_tags
    if q_mats and m_mats and not (q_mats & m_mats):
        continue

    kws = [k.strip() for k in keywords_str.split(',') if k.strip()]
    if any(len(k) >= 4 and k in clean for k in kws):
        print(f"Row {mem_id} ({topic}) MATCHED step 4!")
        break
    else:
        print(f"Row {mem_id} ({topic}) did NOT match step 4")


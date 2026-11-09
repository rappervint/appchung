import sys
sys.path.insert(0, '.')
import knowledge_base
import sqlite3

q = "da nappa xe 4 chỗ giá sao"
clean = knowledge_base.remove_accents(q).lower()
q_feat = knowledge_base.extract_knowledge_features(clean)

conn = sqlite3.connect('gara_knowledge.db')
c = conn.cursor()
c.execute("SELECT id, topic, clean_topic, keywords, raw_content, formatted_reply FROM gara_memory WHERE id in (37, 44)")
for r in c.fetchall():
    mem_id, topic, clean_topic, keywords_str, raw_content, formatted_reply = r
    m_feat = knowledge_base.extract_knowledge_features(f"{clean_topic} {raw_content} {keywords_str}")
    print(f"Checking row {mem_id}: {topic}")

    # Step 4 check:
    kws = [k.strip() for k in keywords_str.split(',') if k.strip()]
    matches = [k for k in kws if len(k) >= 4 and k in clean]
    print(f"  Keywords in clean: {matches}")
    if matches:
        print("  MATCHED in step 4!")
        continue

    # Step 5:
    stop_words = {
        'cho', 'toi', 'minh', 'em', 'anh', 'chi', 'bac', 'muon', 'hoi', 'la', 'gi', 'the', 'nao', 
        'sao', 'co', 'khong', 'voi', 'thi', 'va', 'gia', 'bao', 'nhieu', 'tien', 'bao gia', 'phi', 
        'chi phi', 'ton', 'tam', 'khoang', 'xin', 'tu van', 'xe', 'chiec', 'khi', 'cho toi hoi', 'ad', 'shop'
    }
    import re
    q_tokens = set(re.findall(r'\w+', clean)) - stop_words
    m_tokens = set(re.findall(r'\w+', clean_topic)) - stop_words
    kw_tokens = set(re.findall(r'\w+', keywords_str)) - stop_words
    print(f"  q_tokens: {q_tokens}")
    print(f"  m_tokens: {m_tokens}")
    print(f"  kw_tokens: {kw_tokens}")
    if q_tokens and kw_tokens:
        kw_overlap = q_tokens & kw_tokens
        print(f"  kw_overlap: {kw_overlap}")
        print(f"  len overlap / len q: {len(kw_overlap) / len(q_tokens)}")


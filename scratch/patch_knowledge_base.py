with open('knowledge_base.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    # TỰ ĐỘNG ĐỒNG BỘ TRI THỨC TỪ KNOWLEDGE_SEED.JSON (DÀNH CHO PYTHONANYWHERE / MÁY MỚI):
    try:
        import json
        seed_path = os.path.join(os.path.dirname(__file__), 'knowledge_seed.json')
        if os.path.exists(seed_path):
            with open(seed_path, 'r', encoding='utf-8') as f_seed:
                seed_data = json.load(f_seed)
            for item in seed_data:
                c.execute("SELECT id FROM gara_memory WHERE clean_topic = ?", (item.get('clean_topic', ''),))
                if not c.fetchone():
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    c.execute('''
                        INSERT INTO gara_memory (topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('topic', ''),
                        item.get('clean_topic', ''),
                        item.get('keywords', ''),
                        item.get('raw_content', ''),
                        item.get('price_info', ''),
                        item.get('options_info', ''),
                        item.get('formatted_reply', ''),
                        now_str, now_str
                    ))
            conn.commit()
    except Exception as e_seed:
        print(f"[KnowledgeBase] Lỗi đồng bộ knowledge_seed.json: {e_seed}")"""

replacement = """    # TỰ ĐỘNG ĐỒNG BỘ TRI THỨC TỪ KNOWLEDGE_SEED.JSON (DÀNH CHO PYTHONANYWHERE / MÁY MỚI):
    try:
        # Tự động dọn dẹp các bản ghi cũ bị ô nhiễm từ khóa
        c.execute("DELETE FROM gara_memory WHERE keywords LIKE '%phan tich%' OR keywords LIKE '%sau nay%' OR keywords LIKE '%cap nhat nay%' OR keywords LIKE '%de sau nay%' OR clean_topic LIKE '%phan tich%'")
        conn.commit()

        import json
        seed_path = os.path.join(os.path.dirname(__file__), 'knowledge_seed.json')
        if os.path.exists(seed_path):
            with open(seed_path, 'r', encoding='utf-8') as f_seed:
                seed_data = json.load(f_seed)
            for item in seed_data:
                c.execute("SELECT id FROM gara_memory WHERE clean_topic = ?", (item.get('clean_topic', ''),))
                row = c.fetchone()
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if row:
                    c.execute('''
                        UPDATE gara_memory 
                        SET keywords = ?, price_info = ?, options_info = ?, formatted_reply = ?, raw_content = ?, updated_at = ?
                        WHERE id = ?
                    ''', (
                        item.get('keywords', ''),
                        item.get('price_info', ''),
                        item.get('options_info', ''),
                        item.get('formatted_reply', ''),
                        item.get('raw_content', ''),
                        now_str,
                        row[0]
                    ))
                else:
                    c.execute('''
                        INSERT INTO gara_memory (topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get('topic', ''),
                        item.get('clean_topic', ''),
                        item.get('keywords', ''),
                        item.get('raw_content', ''),
                        item.get('price_info', ''),
                        item.get('options_info', ''),
                        item.get('formatted_reply', ''),
                        now_str, now_str
                    ))
            conn.commit()
    except Exception as e_seed:
        print(f"[KnowledgeBase] Lỗi đồng bộ knowledge_seed.json: {e_seed}")"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('knowledge_base.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")


with open('ai_assistant.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """    else:
        # FALLBACK NẾU GEMINI API KHÔNG KHẢ DỤNG:
        topic = re.sub(r'^(cho tôi hỏi|tôi muốn hỏi|hỏi|cho hỏi|tư vấn|báo giá|khi tôi hỏi)\\s*[:,\\s]*', '', raw_query, flags=re.I).strip()
        topic = topic[:60].strip() or "Tư Vấn Dịch Vụ Gara"
        topic = topic[0].upper() + topic[1:]
        clean_topic = remove_accents(topic).lower()

        clean_core = re.sub(r'\x08(?:cho|toi|minh|em|anh|muon|hoi|cho toi hoi|tu van|bao gia|gia)\x08', '', clean_q).strip()
        words = clean_core.split()
        if len(words) >= 2:
            keywords = " ".join(words)
        else:
            keywords = clean_topic"""

replacement = """    else:
        # FALLBACK NẾU GEMINI API KHÔNG KHẢ DỤNG VÀ KHÔNG PHẢI BẢNG GIÁ:
        topic = re.sub(r'(?i)^(?:cho tôi hỏi|tôi muốn hỏi|hỏi|cho hỏi|tư vấn|báo giá|khi tôi hỏi)\\s*[:,\\s]*', '', raw_query).strip()
        topic = re.sub(r'(?i)\\b(?:phân tích|thêm mấy hàng|thêm mặt hàng|ghi nhớ lại vào hệ thống|để sau này tôi hỏi giá lại|cho giá chính xác từng món|cập nhật giá này vào hệ thống|để sau này trả lời tôi cho chính xác)\\b', '', topic).strip()
        topic = topic[:60].strip() or "Tư Vấn Dịch Vụ Gara"
        topic = topic[0].upper() + topic[1:]
        clean_topic = remove_accents(topic).lower()

        # Làm sạch tuyệt đối các từ khóa nhận diện, loại bỏ hoàn toàn các từ rác đơn lẻ
        clean_core = re.sub(r'(?i)\\b(?:phan\\s*tich|them\\s*may\\s*hang|them\\s*mat\\s*hang|ghi\\s*nho|he\\s*thong|sau\\s*nay|chinh\\s*xac|cap\\s*nhat|luu\\s*vao|tra\\s*loi\\s*toi|cho\\s*toi\\s*hoi|tu\\s*van|bao\\s*gia|khi\\s*toi\\s*hoi|toi\\s*muon\\s*hoi|gia|cho|toi|minh|em|anh|muon|hoi)\\b', ' ', clean_q).strip()
        clean_words = [w for w in clean_core.split() if len(w) >= 3 and not re.match(r'^\\d+[a-z]*$', w)]
        if len(clean_words) >= 2:
            keywords = " ".join(clean_words[:4])
        else:
            keywords = clean_topic"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('ai_assistant.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")


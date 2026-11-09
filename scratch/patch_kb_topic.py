with open('knowledge_base.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """            if ratio_m >= 0.75 or ratio_q >= 0.7 or (len(overlap) >= 2 and ratio_m >= 0.6):
                return {
                    "type": "success",
                    "module": "knowledge_retrieved",
                    "message": formatted_reply
                }

        if q_tokens and kw_tokens:
            kw_overlap = q_tokens & kw_tokens
            if len(kw_overlap) >= 2 and (len(kw_overlap) / len(q_tokens) >= 0.6 or len(kw_overlap) >= len(q_tokens)):
                return {
                    "type": "success",
                    "module": "knowledge_retrieved",
                    "message": formatted_reply
                }"""

replacement = """            if ratio_m >= 0.75 or ratio_q >= 0.7 or (len(overlap) >= 2 and ratio_m >= 0.6):
                return {
                    "type": "success",
                    "module": "knowledge_retrieved",
                    "memory_id": mem_id,
                    "topic": topic,
                    "clean_topic": clean_topic,
                    "keywords": keywords_str,
                    "message": formatted_reply
                }

        if q_tokens and kw_tokens:
            kw_overlap = q_tokens & kw_tokens
            if len(kw_overlap) >= 2 and (len(kw_overlap) / len(q_tokens) >= 0.6 or len(kw_overlap) >= len(q_tokens)):
                return {
                    "type": "success",
                    "module": "knowledge_retrieved",
                    "memory_id": mem_id,
                    "topic": topic,
                    "clean_topic": clean_topic,
                    "keywords": keywords_str,
                    "message": formatted_reply
                }"""

c_crlf = c.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in c_crlf:
    c_crlf = c_crlf.replace(target_norm, replacement_norm, 1)
    with open('knowledge_base.py', 'w', encoding='utf-8') as f:
        f.write(c_crlf)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")


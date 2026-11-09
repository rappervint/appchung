import sys
sys.path.insert(0, '.')
import knowledge_base

test_cases = [
    "sàn simili 7 chỗ",
    "da simili 7 chỗ bao nhiêu",
    "da nappa xe 4 chỗ giá sao",
    "đục lỗ da nappa thêm bao nhiêu",
    "bảng giá bọc ghế da ô tô"
]

for q in test_cases:
    clean = knowledge_base.remove_accents(q).lower()
    res = knowledge_base.query_learned_knowledge(clean, q)
    if res:
        print(f"PASS: '{q}' -> [{res.get('topic')}]")
        print("      " + res.get('message').split('\n')[0][:70])
    else:
        print(f"FAIL: '{q}' -> Not found!")


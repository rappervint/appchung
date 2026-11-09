import sys
sys.path.insert(0, '.')
import knowledge_base

queries = [
    "màn hình giá rẻ",
    "film 3m giá rẻ",
    "màn hình 10 triệu",
    "bọc ghế da giá rẻ"
]

for q in queries:
    clean = knowledge_base.remove_accents(q).lower()
    res = knowledge_base.query_learned_knowledge(clean, q)
    if res:
        print(f"'{q}' -> [{res.get('topic')}]")
    else:
        print(f"'{q}' -> None (Gemini handles naturally)")


import sys
sys.path.insert(0, '.')
import knowledge_base

q = "màn hình giá rẻ"
clean = knowledge_base.remove_accents(q).lower()
res = knowledge_base.query_learned_knowledge(clean, q)
print(res)


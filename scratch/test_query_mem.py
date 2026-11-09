import sys
sys.path.insert(0, '.')
import knowledge_base

query = "sàn simili 7 chỗ"
clean = knowledge_base.remove_accents(query).lower()
feat = knowledge_base.extract_knowledge_features(clean)
print("Features of query:", feat)

res = knowledge_base.query_learned_knowledge(clean, query)
print("Result of query_learned_knowledge:")
if res:
    print("Found! ID:", res.get("memory_id"), "Topic:", res.get("topic"))
    print("Reply:", res.get("message")[:120])
else:
    print("None found!")

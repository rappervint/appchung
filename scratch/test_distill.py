import sys
sys.path.insert(0, '.')
import json
import gemini_engine

user_query = """Xe 7 chỗ :
Da simili : 6tr
Da công nghiệp : 7tr5
Da nappa : 12tr
Xe 4 chỗ :
Da simili : 3tr5
Da công nghiệp : 6tr
Da nappa : 9tr5

Riêng da nappa đục lỗ công nghệ được , +1tr vào giá sản phẩm.
phân tích, sau đó cập nhật giá này vào hệ thống để sau nay trả lời tôi cho chính xác"""

reply_text = """Dạ, em đã nắm rất rõ và ghi nhớ chính xác bảng giá bọc da ghế mới nhất của gara vào hệ thống rồi ạ!
Em xin tổng hợp lại bảng giá chuẩn vừa được cập nhật:
🚗 Xe 7 Chỗ:
- Da Simili: 6.000.000 đ
- Da công nghiệp: 7.500.000 đ
- Da Nappa: 12.000.000 đ
🚗 Xe 4 / 5 Chỗ:
- Da Simili: 3.500.000 đ
- Da công nghiệp: 6.000.000 đ
- Da Nappa: 9.500.000 đ"""

print("Testing distill_knowledge_with_gemini...")
res = gemini_engine.distill_knowledge_with_gemini(user_query, reply_text)
print("Result:")
print(json.dumps(res, ensure_ascii=False, indent=2))


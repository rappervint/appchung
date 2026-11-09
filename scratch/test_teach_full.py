import sys
sys.path.insert(0, '.')
import json
import ai_assistant

user_query = """Xe 7 chỗ :
Da simili : 6tr
Da công nghiệp : 7tr5
Da nappa : 12tr
Xe 4 chỗ :
Da simili : 3tr5
Da công nghiệp : 6tr
Da nappa : 9tr5

Riêng da nappa đục lỗ công nghệ được , +1tr vào giá sản phẩm.
phân tích và thêm mây hàng, ghi nhớ lại vào hệ thống, để sau nay tôi hỏi giá lại thì cho giá chính xác từng món"""

reply_text = """Dạ em đã ghi nhớ toàn bộ bảng giá bọc ghế da cho cả xe 4 chỗ và 7 chỗ (bao gồm tùy chọn đục lỗ công nghệ +1 triệu cho da Nappa) vào bộ nhớ hệ thống của gara Trần Bình Auto rồi ạ!
🚗 Xe 7 Chỗ:
- Da Simili: 6.000.000 đ
- Da công nghiệp: 7.500.000 đ
- Da Nappa: 12.000.000 đ
🚗 Xe 4 / 5 Chỗ:
- Da Simili: 3.500.000 đ
- Da công nghiệp: 6.000.000 đ
- Da Nappa: 9.500.000 đ"""

ok, info = ai_assistant.teach_system_from_gemini(user_query, reply_text)
print("ok:", ok)
print("info:")
print(json.dumps(info, ensure_ascii=False, indent=2))


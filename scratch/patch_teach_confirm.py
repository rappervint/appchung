with open('ai_assistant.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = """            ok, top, kws, _ = teach_system_from_gemini(q_saved, reply_saved)
            if ok:
                return {
                    "type": "success",
                    "module": "knowledge",
                    "message": (
                        f"🎓 **GEMINI ĐÃ DẠY THÀNH CÔNG VÀO BỘ NÃO AI HỆ THỐNG!**\\n"
                        f"─────────────────────────────────────────\\n"
                        f"• 📌 **Chủ đề đã học:** **{top}**\\n"
                        f"• 🔑 **Từ khóa nhận diện:** `{kws}`\\n"
                        f"• ⚡ **Tốc độ phản hồi lần sau:** `< 0.003 giây` (AI hệ thống tự trả lời ngay, không cần gọi lại Gemini)\\n"
                        f"─────────────────────────────────────────\\n"
                        f"👉 Bất cứ khi nào anh hỏi lại câu này (hoặc tương tự), AI hệ thống sẽ tự động trả lời chính xác ngay lập tức!"
                    )
                }
            else:
                return {
                    "type": "error",
                    "message": "⚠️ Gặp lỗi khi lưu tri thức vào hệ thống. Vui lòng thử lại."
                }"""

replacement = """            ok, info = teach_system_from_gemini(q_saved, reply_saved)
            if ok and isinstance(info, dict):
                cat = info.get('category_name', 'Dịch Vụ Gara')
                items = info.get('items', [])
                trigs = info.get('triggers', [])
                trig_sample = "`, `".join(trigs)

                item_lines = []
                for idx, it in enumerate(items[:8], 1):
                    p_str = f" — *{it['price']}*" if it.get('price') else ""
                    item_lines.append(f"  {idx}. **{it['topic']}**{p_str}")

                items_text = "\\n".join(item_lines) if item_lines else f"  • {cat}"

                msg_done = (
                    f"🎓 **GEMINI ĐÃ CHUYỂN HÓA & DẠY THÀNH CÔNG VÀO BỘ NÃO AI HỆ THỐNG!**\\n"
                    f"─────────────────────────────────────────\\n"
                    f"• 📂 **Phân nhóm:** **{cat}**\\n"
                    f"• 🧩 **Bóc tách thông minh ({len(items)} hạng mục độc lập):**\\n"
                    f"{items_text}\\n"
                    f"• 🛡️ **Từ khóa nhận diện chuẩn (Chống ô nhiễm 100%):**\\n"
                    f"  `{trig_sample}`\\n"
                    f"• ⚡ **Tốc độ phản hồi:** `< 0.003 giây` (AI hệ thống tự trả lời ngay cho từng món hoặc bảng giá chung)\\n"
                    f"─────────────────────────────────────────\\n"
                    f"👉 Bất cứ khi nào anh hoặc khách hỏi về bất kỳ hạng mục nào, AI hệ thống sẽ hiểu và trả lời chính xác ngay lập tức!"
                )
                return {
                    "type": "success",
                    "module": "knowledge",
                    "message": msg_done
                }
            else:
                return {
                    "type": "error",
                    "message": "⚠️ Gặp lỗi khi lưu tri thức vào hệ thống. Vui lòng thử lại."
                }"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open('ai_assistant.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")


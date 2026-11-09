import re
import unicodedata

def remove_accents(input_str):
    if not input_str:
        return ""
    s = unicodedata.normalize('NFD', input_str)
    s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'D')

def parse_price_str(val_str):
    s = remove_accents(val_str).lower().replace(' ', '')
    m_tr = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:tr|trieu)', s)
    if m_tr:
        num = float(m_tr.group(1).replace(',', '.'))
        return f"{int(num * 1_000_000):,} đ"
    m_k = re.search(r'(\d+)\s*k', s)
    if m_k:
        num = int(m_k.group(1))
        return f"{num * 1_000:,} đ"
    m_d = re.search(r'(\d+)', s)
    if m_d:
        num = int(m_d.group(1))
        if num < 100:
            return f"{num * 1_000_000:,} đ"
        return f"{num:,} đ"
    return val_str.strip()

def rule_based_table_distill(text, reply_text=""):
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    items = []
    current_section = ""
    car_seats = ""

    for line in lines:
        clean_l = remove_accents(line).lower()
        # Bỏ các dòng mệnh lệnh của người dùng
        if any(cmd in clean_l for cmd in [
            'phan tich', 'them may hang', 'them mat hang', 'ghi nho', 'he thong',
            'sau nay', 'chinh xac', 'cap nhat', 'luu vao', 'tra loi toi'
        ]):
            continue

        # Phát hiện mục xe
        m_car = re.search(r'xe\s*(\d+)\s*cho', clean_l)
        if m_car:
            car_seats = f"{m_car.group(1)} chỗ"
            current_section = f"xe {m_car.group(1)} chỗ"
            continue

        # Phát hiện dòng da + giá: e.g. "Da simili : 6tr"
        m_item = re.match(r'^(da\s+[\w\s]+|simili|nappa|cong nghiep)[\s:=–-]+(\+?\d+[\w\s,.]*)', line, re.I)
        if m_item:
            mat_raw = m_item.group(1).strip()
            price_raw = m_item.group(2).strip()
            formatted_price = parse_price_str(price_raw)
            clean_mat = remove_accents(mat_raw).lower()
            
            seats_str = car_seats or "ô tô"
            seats_num = re.search(r'\d+', seats_str).group(0) if re.search(r'\d+', seats_str) else ""
            topic = f"Bọc ghế {mat_raw} xe {seats_str}".strip()
            
            # Triggers thông minh, chống ô nhiễm tuyệt đối
            triggers = []
            if seats_num:
                triggers.append(f"{clean_mat} {seats_num} cho")
                triggers.append(f"boc {clean_mat} {seats_num} cho")
                triggers.append(f"boc da {clean_mat} {seats_num} cho")
                triggers.append(f"gia {clean_mat} {seats_num} cho")
                if "simili" in clean_mat:
                    triggers.append(f"san simili {seats_num} cho")
            else:
                triggers.append(f"boc {clean_mat}")
                triggers.append(f"gia {clean_mat}")

            item_reply = f"🚗 **DỊCH VỤ BỌC GHẾ {mat_raw.upper()} (XE {seats_str.upper()}):**\n• Mức giá hoàn thiện: **{formatted_price}** trọn gói tại Gara Trần Bình Auto."
            items.append({
                "topic": topic,
                "price": formatted_price,
                "triggers": list(dict.fromkeys(triggers)),
                "reply": item_reply
            })
            continue

        # Phát hiện tùy chọn phụ như đục lỗ: "Riêng da nappa đục lỗ công nghệ được , +1tr vào giá sản phẩm."
        if 'duc lo' in clean_l and ('nappa' in clean_l or 'da' in clean_l):
            m_p = re.search(r'([+]\s*\d+\s*(?:tr|trieu|k|nghin)?)', clean_l)
            add_p = parse_price_str(m_p.group(1)) if m_p else "+1.000.000 đ"
            items.append({
                "topic": "Tùy chọn da Nappa đục lỗ công nghệ",
                "price": add_p,
                "triggers": ["da nappa duc lo", "cong nghe duc lo nappa", "duc lo da nappa", "boc da nappa duc lo"],
                "reply": f"✨ **TÙY CHỌN ĐỤC LỖ CÔNG NGHỆ (DA NAPPA):**\n• Phụ phí: **{add_p}** cộng thêm vào giá sản phẩm."
            })

    if not items:
        return None

    clean_summary = reply_text.strip() if reply_text else "Bảng giá bọc da ô tô chuẩn gara Trần Bình Auto."
    return {
        "domain": "seat_floor",
        "category_name": "Bọc Ghế Da Ô Tô",
        "items": items,
        "master_summary": {
            "topic": "Bảng giá bọc ghế da ô tô Trần Bình Auto",
            "triggers": ["bang gia boc da ghe", "boc ghe da oto", "gia boc da xe", "boc da oto bao nhieu", "gia boc ghe da"],
            "reply": clean_summary
        }
    }

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

res = rule_based_table_distill(user_query)
print("Items parsed:", len(res['items']))
for it in res['items']:
    print(f"[{it['topic']}] -> Price: {it['price']} | Triggers: {it['triggers']}")


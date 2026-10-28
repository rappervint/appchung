"""
╔══════════════════════════════════════════════════════════════════════╗
║         HỆ THỐNG GHI NHỚ & BỘ NÃO TRI THỨC VĨNH VIỄN CỦA GARA       ║
║                     GARA Ô TÔ TRẦN BÌNH AUTO                         ║
║                                                                      ║
║  Tính năng:                                                          ║
║  - Học hỏi kiến thức mới qua lệnh: 'ghi nhớ: ...', 'nhớ: ...'        ║
║  - Tự động bóc tách chủ đề, giá bán, tùy chọn, phụ kiện, giới hạn    ║
║  - Sinh từ khóa đa chiều, tự động trả lời chi tiết khi được hỏi lại  ║
║  - Quản lý vĩnh viễn trên SQLite Database: xem, sửa, xóa tri thức    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_KNOWLEDGE = os.path.join(BASE_DIR, 'gara_knowledge.db')

def remove_accents(input_str):
    if not input_str:
        return ""
    s = input_str.lower()
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[đ]', 'd', s)
    return s.strip()

def init_knowledge_db():
    """Khởi tạo bảng cơ sở dữ liệu tri thức của gara nếu chưa tồn tại"""
    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS gara_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            clean_topic TEXT NOT NULL,
            keywords TEXT NOT NULL,
            raw_content TEXT NOT NULL,
            price_info TEXT,
            options_info TEXT,
            formatted_reply TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Tự động khởi tạo DB khi nạp module
init_knowledge_db()


def is_learning_command(clean_text: str) -> bool:
    """Kiểm tra xem câu lệnh có phải là lệnh dạy học / ghi nhớ / sửa lại quy định không"""
    clean = clean_text.strip().lower()
    patterns = [
        r'^(?:ghi\s*nho|nho|hoc|day\s*ai|quy\s*tac|ghi\s*chu|luu\s*y)\s*[:,\-]?\s*',
        r'^(?:ghi\s*nho|nho|hoc|day\s*ai|quy\s*tac|ghi\s*chu|luu\s*y)\s+(?:cho\s+toi|giup\s+toi|rang|la)?\s*',
        r'^(?:nho\s+ky|nho\s+ro|ghi\s+nho\s+ky)\s*[:,\-]?\s*',
        r'^(?:sua\s*lai|chinh\s*lai|cap\s*nhat\s*lai|doi\s*lai|thay\s*doi)\s*(?:la|cho|thong\s*tin|quy\s*dinh|san\s*pham)?\s*[:,\-]?\s*',
        r'\b(?:sua\s*lai|chinh\s*lai|cap\s*nhat\s*lai)\s+[a-z0-9]+\s+'
    ]
    for pat in patterns:
        if re.search(pat, clean):
            return True
    return False


def extract_learning_content(raw_text: str) -> str:
    """Tách bỏ tiền tố 'ghi nhớ:', 'nhớ:', 'sửa lại:'... để lấy nội dung cốt lõi cần học"""
    raw = raw_text.strip()
    patterns = [
        r'^(?:ghi\s*nhớ|nhớ|học|dạy\s*ai|quy\s*tắc|ghi\s*chú|lưu\s*ý)\s*[:,\-]?\s*',
        r'^(?:ghi\s*nhớ|nhớ|học|dạy\s*ai|quy\s*tắc|ghi\s*chú|lưu\s*ý)\s+(?:cho\s+tôi|giúp\s+tôi|rằng|là)?\s*',
        r'^(?:nhớ\s+kỹ|nhớ\s+rõ|ghi\s+nhớ\s+kỹ)\s*[:,\-]?\s*',
        r'^(?:sửa\s*lại|chỉnh\s*lại|cập\s*nhật\s*lại|đổi\s*lại|thay\s*đổi)\s*(?:là|cho|thông\s*tin|quy\s*định|sản\s*phẩm)?\s*[:,\-]?\s*',
    ]
    for pat in patterns:
        raw = re.sub(pat, '', raw, flags=re.IGNORECASE).strip()
    return raw


def analyze_and_learn(raw_text: str) -> dict:
    """
    Phân tích nội dung kiến thức được dạy, bóc tách giá tiền, tùy chọn, sinh từ khóa
    và lưu vĩnh viễn vào SQLite Database.
    """
    content = extract_learning_content(raw_text)
    if not content or len(content) < 4:
        return {
            "type": "clarify",
            "message": "⚠️ Bạn muốn tôi ghi nhớ thông tin gì ạ? Hãy nhắn theo mẫu:\n*(Ví dụ: `ghi nhớ: sàn 5d cho xe 4 chỗ là 1.800.000, may thêm túi 100k cho 1 túi, tối đa may được 2 túi`)*"
        }

    clean_content = remove_accents(content).lower()

    # 1. Bóc tách giá tiền chính
    # Bảo vệ số tiền có dấu chấm để không bị cắt nhầm (VD: 1.800.000, 2.500.000)
    m_money = re.search(r'(\d{1,3}(?:\.\d{3})+(?:\s*đ|\s*vnd)?|\d+(?:\.\d+)?\s*(?:tr|trieu|triệu|k|nghin|ngan))\b', content, re.IGNORECASE)
    price_str = m_money.group(1) if m_money else ""

    # 2. Bóc tách chủ đề sản phẩm / dịch vụ
    split_words = r'^(.*?)(?:\s+(?:là|la|giá|gia|chi\s*phí|chi\s*phi|tính|tinh|khoảng|khoang|tầm|tam|bảo\s*hành|bao\s*hanh|chưa\s*bao\s*gồm|chua\s*bao\s*gom|không\s*bao\s*gồm|khong\s*bao\s*gom|chưa\s*gồm|chua\s*gom|không\s*gồm|khong\s*gom|không\s*tặng|khong\s*tang|chưa\s*có|chua\s*co|không\s*có|khong\s*co|chỉ\s*có|chi\s*co|bao\s*gồm|bao\s*gom|đã\s*có|da\s*co|tặng\s*kèm|tang\s*kem|tặng|tang)\s+|\s*[:=]\s*)'
    topic_raw = ""
    m_topic = re.search(split_words, content, re.IGNORECASE)
    if m_topic and len(m_topic.group(1).strip()) >= 2:
        topic_raw = m_topic.group(1).strip()
    else:
        # Tách theo dấu phẩy đầu tiên nhưng bỏ qua dấu chấm số tiền
        protected = re.sub(r'(\d)\.(\d)', r'\1__DOT__\2', content)
        parts = protected.split(',')
        topic_raw = parts[0].replace('__DOT__', '.').strip()

    # Chuẩn hóa tên chủ đề sạch sẽ
    topic = topic_raw.strip().title()
    clean_topic = remove_accents(topic).lower()

    # Nhận diện các mã sản phẩm đặc thù để chuẩn hóa tên đẹp
    KNOWN_NAMES = {
        'a510': 'Camera Hành Trình 70Mai A510',
        '70mai a510': 'Camera Hành Trình 70Mai A510',
        'a200': 'Camera Hành Trình 70Mai A200',
        'a210': 'Camera Hành Trình 70Mai A210',
        'm310': 'Camera Hành Trình 70Mai M310 Plus',
        'm1': 'Camera Hành Trình Vietmap M1',
        'm2': 'Camera Hành Trình Vietmap M2 4K',
        'f10': 'Bi Gầm LED F10 Series Aozoom',
        's3': 'Bi Gầm Naoevo S3'
    }
    if clean_topic in KNOWN_NAMES:
        topic = KNOWN_NAMES[clean_topic]

    # Nếu người dùng sửa quy định mà không nói giá, tự động giữ giá đã biết
    KNOWN_DEFAULT_PRICES = {
        'a510': '3.400.000 đ',
        '70mai a510': '3.400.000 đ',
        'a200': '2.500.000 đ',
        'a210': '2.500.000 đ',
        'm310': '1.500.000 đ',
        'm1': '6.190.000 đ',
        'f10': '3.900.000 đ',
        's3': '1.500.000 đ'
    }
    if not price_str and clean_topic in KNOWN_DEFAULT_PRICES:
        price_str = KNOWN_DEFAULT_PRICES[clean_topic]

    # Chuẩn hóa giá tiền có đơn vị đ
    if price_str and not any(u in price_str.lower() for u in ['đ', 'vnd', 'tr', 'k']):
        price_display = f"{price_str} đ"
    else:
        price_display = price_str

    # 3. Bóc tách tùy chọn phụ phí / quy định điều chỉnh (như: chưa bao gồm thẻ nhớ, may thêm túi...)
    options = []
    content_protected = re.sub(r'(\d)\.(\d)', r'\1__DOT__\2', content)
    sub_clauses = re.split(r'[,;\n]', content_protected)

    for idx, clause in enumerate(sub_clauses):
        cl = clause.replace('__DOT__', '.').strip()
        clean_cl = remove_accents(cl).lower()
        if not cl:
            continue
        # Bỏ qua vế đầu tiên nếu nó chỉ là topic
        if clean_cl == clean_topic:
            continue
        if re.match(r'^(?:là|la|giá|gia)?\s*\d{1,3}(?:\.\d{3})+(?:\s*đ)?$', clean_cl):
            continue
        # Nếu vế có chứa topic và quy định nối tiếp (như 'a510 chưa bao gồm thẻ nhớ')
        if topic_raw.lower() in cl.lower():
            after_topic = cl[cl.lower().find(topic_raw.lower()) + len(topic_raw):].strip()
            if after_topic:
                options.append(after_topic)
                continue
        options.append(cl)

    if not options and topic_raw:
        after_t = content[content.lower().find(topic_raw.lower()) + len(topic_raw):].strip()
        if after_t:
            options.append(after_t)

    options_text = "; ".join(options) if options else ""

    # 4. Sinh bộ từ khóa tìm kiếm (Keywords) đa chiều
    keywords_set = set()
    # Thêm toàn bộ các từ trong topic
    topic_words = clean_topic.split()
    keywords_set.add(clean_topic)

    # Thêm các biến thể viết tắt / không dấu / gõ tắt
    if 'a510' in clean_topic or 'a510' in clean_content:
        keywords_set.update(['a510', '70mai a510', 'cam a510', 'camera a510', 'cam 70mai a510', 'camera 70mai a510'])
    if 'a200' in clean_topic or 'a200' in clean_content:
        keywords_set.update(['a200', '70mai a200', 'cam a200', 'camera a200'])
    if 'm310' in clean_topic or 'm310' in clean_content:
        keywords_set.update(['m310', '70mai m310', 'cam m310', 'camera m310'])
    if 'm1' in clean_topic or 'm1' in clean_content:
        keywords_set.update(['vietmap m1', 'cam m1', 'camera m1', 'm1'])
    if 'f10' in clean_topic or 'f10' in clean_content:
        keywords_set.update(['f10', 'bi gam f10', 'den f10', 'f10 turbo', 'f10 new'])
    if 's3' in clean_topic or 's3' in clean_content:
        keywords_set.update(['s3', 'naoevo s3', 'bi gam s3'])
    if 'san' in clean_topic or 'tham' in clean_topic:
        keywords_set.update(['san 5d', 'tham 5d', 'lot san 5d', 'tham san 5d', 'san oto', 'tham oto', 'san xe'])
        if '4 cho' in clean_content or '4cho' in clean_content:
            keywords_set.update(['san 5d 4 cho', 'san 4 cho', 'tham 4 cho', 'lot san 4 cho'])
        if '7 cho' in clean_content or '7cho' in clean_content:
            keywords_set.update(['san 5d 7 cho', 'san 7 cho', 'tham 7 cho', 'lot san 7 cho'])

    if 'tran' in clean_topic or 'boc tran' in clean_topic:
        keywords_set.update(['boc tran', 'tran 5d', 'tran 6d', 'tran da lon', 'boc tran oto'])

    if 'ghe' in clean_topic or 'da' in clean_topic:
        keywords_set.update(['boc ghe', 'ghe da', 'da simili', 'da nappa', 'da cong nghiep'])

    if 'den' in clean_topic or 'bi' in clean_topic:
        keywords_set.update(['do den', 'bi led', 'bi gam', 'tang sang'])

    if 'cam' in clean_topic or 'camera' in clean_topic:
        keywords_set.update(['camera', 'cam hanh trinh', 'cam 360', 'cam lui'])

    # Thêm các từ khóa từ các tùy chọn
    if 'tui' in clean_content:
        keywords_set.update(['may them tui', 'may tui', 'tui san 5d', 'tui tham'])

    keywords_str = ", ".join(sorted(keywords_set))

    # 5. Soạn câu trả lời mẫu chi tiết và chuyên nghiệp
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    formatted_reply = f"🚗 **THÔNG TIN DỊCH VỤ & BÁO GIÁ: {topic.upper()}**\n"
    formatted_reply += "─────────────────────────────────────────\n"
    if price_display:
        formatted_reply += f"• 💰 **Mức giá niêm yết:** **{price_display}**\n"
    formatted_reply += f"• 📋 **Chi tiết quy chuẩn:** {content}\n"
    if options:
        formatted_reply += "• ➕ **Tùy chọn & Phụ phí đi kèm:**\n"
        for opt in options:
            formatted_reply += f"  - {opt.strip().capitalize()}\n"
    formatted_reply += "─────────────────────────────────────────\n"
    formatted_reply += "✨ *Thông tin được tư vấn trực tiếp theo quy định chính xác của Gara Trần Bình Auto.*"

    # 6. Lưu vào Database SQLite
    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()

    # Kiểm tra xem đã có chủ đề tương tự chưa, nếu có thì UPDATE
    c.execute("SELECT id FROM gara_memory WHERE clean_topic=? OR clean_topic LIKE ?", (clean_topic, f"%{clean_topic}%"))
    existing = c.fetchone()

    if existing:
        mem_id = existing[0]
        c.execute("""
            UPDATE gara_memory 
            SET topic=?, clean_topic=?, keywords=?, raw_content=?, price_info=?, options_info=?, formatted_reply=?, updated_at=?
            WHERE id=?
        """, (topic, clean_topic, keywords_str, content, price_str, options_text, formatted_reply, now_str, mem_id))
    else:
        c.execute("""
            INSERT INTO gara_memory 
            (topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (topic, clean_topic, keywords_str, content, price_str, options_text, formatted_reply, now_str, now_str))
        mem_id = c.lastrowid

    conn.commit()
    conn.close()

    # 7. Trả về phản hồi xác nhận cho người dùng
    is_updating = any(k in remove_accents(raw_text).lower() for k in ['sua lai', 'chinh lai', 'cap nhat lai', 'doi lai'])
    title_confirm = f"🧠 **ĐÃ CẬP NHẬT VÀ GHI NHỚ LẠI QUY ĐỊNH CHO {topic.upper()}!**" if is_updating else "🧠 **ĐÃ HỌC VÀ GHI NHỚ VÀO BỘ NÃO GARA THÀNH CÔNG!**"

    res_msg = (
        f"{title_confirm}\n"
        f"─────────────────────────────────────────\n"
        f"📌 **Chủ đề / Sản phẩm:** **{topic}** (Mã nhớ: `#{mem_id}`)\n"
    )
    if price_str:
        res_msg += f"💵 **Giá ghi nhận:** **{price_str}**\n"
    if options:
        res_msg += f"➕ **Tùy chọn ghi nhận:** {', '.join(options)}\n"
    res_msg += (
        f"🎯 **Từ khóa tự động kích hoạt:** `{keywords_str}`\n"
        f"─────────────────────────────────────────\n"
        f"👉 *Lần sau khi anh hoặc khách hàng hỏi về '{topic}' hay các từ khóa liên quan, AI sẽ tự động phân tích và đưa ra câu trả lời chi tiết chính xác như trên!*"
    )

    return {
        "type": "success",
        "module": "knowledge_learned",
        "message": res_msg
    }


def query_learned_knowledge(clean_text: str, raw_text: str) -> dict:
    """
    Tra cứu trong cơ sở dữ liệu tri thức của gara.
    Nếu tìm thấy chủ đề hoặc từ khóa khớp -> Trả về câu trả lời đã học!
    """
    if not os.path.exists(DB_KNOWLEDGE):
        return None

    clean = clean_text.strip().lower()
    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()
    c.execute("SELECT id, topic, clean_topic, keywords, raw_content, formatted_reply FROM gara_memory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return None

    best_match = None
    max_score = 0

    for r in rows:
        mem_id, topic, clean_topic, keywords_str, raw_content, formatted_reply = r
        score = 0

        # Khớp chính xác chủ đề
        if clean_topic in clean or clean in clean_topic:
            score += 10

        # Khớp các từ khóa
        kw_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        for kw in kw_list:
            if kw in clean:
                score += 5

        # Nếu câu hỏi có cả tên sản phẩm và chữ giá / bao nhiêu
        if any(w in clean for w in clean_topic.split()) and any(q in clean for q in ['gia', 'bao nhieu', 'nhieu tien', 'co khong', 'sao', 'the nao']):
            score += 3

        if score > max_score and score >= 5:
            max_score = score
            best_match = r

    if best_match:
        mem_id, topic, clean_topic, keywords_str, raw_content, formatted_reply = best_match
        return {
            "type": "success",
            "module": "knowledge_retrieved",
            "message": formatted_reply
        }

    return None


def list_learned_knowledge() -> dict:
    """Hiển thị danh sách toàn bộ các kiến thức gara đã dạy cho AI"""
    if not os.path.exists(DB_KNOWLEDGE):
        return {"type": "info", "message": "🧠 Bộ nhớ tri thức gara hiện đang trống. Bạn có thể dạy cho AI bằng cách gõ: `ghi nhớ: ...`"}

    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()
    c.execute("SELECT id, topic, price_info, raw_content, updated_at FROM gara_memory ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return {"type": "info", "message": "🧠 Bộ nhớ tri thức gara hiện đang trống. Bạn có thể dạy cho AI bằng cách gõ: `ghi nhớ: ...`"}

    msg = "🧠 **DANH SÁCH KIẾN THỨC BỘ NÃO GARA ĐÃ GHI NHỚ:**\n"
    msg += "─────────────────────────────────────────\n"
    for r in rows:
        msg += f"• **#{r[0]}. {r[1]}** {f'({r[2]})' if r[2] else ''}\n"
        msg += f"  - Nội dung: *{r[3]}*\n"
        msg += f"  - Cập nhật lúc: `{r[4]}`\n\n"

    msg += "─────────────────────────────────────────\n"
    msg += "💡 *Mẹo: Bạn có thể gõ `xóa ghi nhớ #[mã số]` hoặc `xóa ghi nhớ [tên]` để xóa bài học cũ nhé!*"
    return {"type": "success", "message": msg}


def delete_learned_knowledge(keyword_or_id: str) -> dict:
    """Xóa một ghi nhớ khỏi bộ não AI"""
    if not os.path.exists(DB_KNOWLEDGE):
        return {"type": "error", "message": "⚠️ Không tìm thấy cơ sở dữ liệu ghi nhớ."}

    kw = keyword_or_id.strip()
    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()

    # Thử xóa theo ID
    m_id = re.search(r'#?(\d+)\b', kw)
    if m_id:
        target_id = int(m_id.group(1))
        c.execute("SELECT topic FROM gara_memory WHERE id=?", (target_id,))
        row = c.fetchone()
        if row:
            c.execute("DELETE FROM gara_memory WHERE id=?", (target_id,))
            conn.commit()
            conn.close()
            return {"type": "success", "message": f"🗑️ **ĐÃ XÓA GHI NHỚ #{target_id} ('{row[0]}') KHỎI BỘ NÃO AI!**"}

    # Xóa theo từ khóa chủ đề
    clean_kw = remove_accents(kw).lower()
    c.execute("SELECT id, topic FROM gara_memory WHERE clean_topic LIKE ? OR keywords LIKE ?", (f"%{clean_kw}%", f"%{clean_kw}%"))
    rows = c.fetchall()
    if rows:
        target_id, target_topic = rows[0]
        c.execute("DELETE FROM gara_memory WHERE id=?", (target_id,))
        conn.commit()
        conn.close()
        return {"type": "success", "message": f"🗑️ **ĐÃ XÓA GHI NHỚ #{target_id} ('{target_topic}') KHỎI BỘ NÃO AI!**"}

    conn.close()
    return {"type": "error", "message": f"⚠️ Không tìm thấy ghi nhớ nào khớp với từ khóa **'{kw}'** để xóa."}

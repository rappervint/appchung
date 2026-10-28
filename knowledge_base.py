"""
╔══════════════════════════════════════════════════════════════════════╗
║         HỆ THỐNG GHI NHỚ & BỘ NÃO TRI THỨC VĨNH VIỄN CỦA GARA       ║
║                     GARA Ô TÔ TRẦN BÌNH AUTO                         ║
║                                                                      ║
║  Tính năng:                                                          ║
║  - Tự động chuẩn hóa mọi định dạng tiền tệ VN: 3tr5 -> 3.500.000 đ    ║
║  - BẢO TỒN NGUYÊN VẸN 100% THÔNG SỐ KỸ THUẬT CATALOG KHI ĐỔI GIÁ      ║
║  - Tự động lọc sạch tên chủ đề (không bao giờ để 'Giá A510')          ║
║  - Học hỏi kiến thức mới qua lệnh: 'ghi nhớ: ...', 'sửa lại: ...'    ║
║  - Ghi nhớ vĩnh viễn trên SQLite Database: gara_knowledge.db         ║
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

# ─────────────────────────────────────────────────────────────────────────────
# 1. BỘ CHUYỂN ĐỔI TIỀN TỆ VIỆT NAM THÔNG MINH (3tr5 -> 3.500.000 đ)
# ─────────────────────────────────────────────────────────────────────────────

def parse_vietnamese_currency(text: str) -> tuple:
    """
    Nhận diện và chuẩn hóa mọi cách nói tiền tệ của người Việt:
    - '3tr5', '3tr500', '3 triệu 5', '3 triệu rưỡi' -> ('3.500.000 đ', 3500000)
    - '1tr8', '1 triệu 8' -> ('1.800.000 đ', 1800000)
    - '4tr2', '4.2tr' -> ('4.200.000 đ', 4200000)
    - '350k', '350 ngàn' -> ('350.000 đ', 350000)
    - '3.500.000', '3500000' -> ('3.500.000 đ', 3500000)
    Trả về: (formatted_str, numeric_value)
    """
    if not text:
        return "", 0

    s = text.lower().strip()
    s_no_acc = remove_accents(s)

    # 1. Dạng triệu có phần thập phân hoặc số lẻ: "3tr5", "3tr500", "3 triệu 5", "3trieu5"
    m_tr_split = re.search(r'\b(\d+)\s*(?:tr|trieu|triệu)\s*(\d{1,3})\b', s)
    if m_tr_split:
        trieu = int(m_tr_split.group(1))
        le_str = m_tr_split.group(2)
        if len(le_str) == 1:
            tram_nghin = int(le_str) * 100000
        elif len(le_str) == 2:
            tram_nghin = int(le_str) * 10000
        else:
            tram_nghin = int(le_str) * 1000
        total = trieu * 1000000 + tram_nghin
        return f"{total:,}".replace(',', '.') + " đ", total

    # 2. Dạng "triệu rưỡi": "3 triệu rưỡi", "3tr rưỡi"
    m_ruoi = re.search(r'\b(\d+)\s*(?:tr|trieu|triệu)\s*(?:ruoi|rưỡi)\b', s_no_acc)
    if m_ruoi:
        total = int(m_ruoi.group(1)) * 1000000 + 500000
        return f"{total:,}".replace(',', '.') + " đ", total

    # 3. Dạng thập phân triệu: "3.5tr", "3,5tr", "3.5 triệu", "3,5 trieu"
    m_tr_dec = re.search(r'\b(\d+)[.,](\d+)\s*(?:tr|trieu|triệu)\b', s)
    if m_tr_dec:
        val = float(f"{m_tr_dec.group(1)}.{m_tr_dec.group(2)}")
        total = int(round(val * 1000000))
        return f"{total:,}".replace(',', '.') + " đ", total

    # 4. Dạng triệu tròn: "3tr", "3 triệu", "4trieu"
    m_tr_round = re.search(r'\b(\d+)\s*(?:tr|trieu|triệu)\b', s)
    if m_tr_round:
        total = int(m_tr_round.group(1)) * 1000000
        return f"{total:,}".replace(',', '.') + " đ", total

    # 5. Dạng nghìn k: "350k", "350 nghìn", "350 ngàn", "3400k"
    m_k = re.search(r'\b(\d+)\s*(?:k|nghin|nghìn|ngan|ngàn)\b', s)
    if m_k:
        total = int(m_k.group(1)) * 1000
        return f"{total:,}".replace(',', '.') + " đ", total

    # 6. Dạng số có dấu chấm hàng nghìn: "3.500.000", "3.400.000 đ"
    m_dot = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\s*(?:đ|vnd|dong|đồng)?\b', s)
    if m_dot:
        raw_num = m_dot.group(1).replace('.', '')
        total = int(raw_num)
        return f"{total:,}".replace(',', '.') + " đ", total

    # 7. Dạng số nguyên lớn thuần túy: "3500000"
    m_raw = re.search(r'\b(\d{6,9})\s*(?:đ|vnd|dong|đồng)?\b', s)
    if m_raw:
        total = int(m_raw.group(1))
        return f"{total:,}".replace(',', '.') + " đ", total

    return "", 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. TỪ ĐIỂN BẢO TỒN THÔNG SỐ SẢN PHẨM CATALOG (CATALOG_SPECS)
# Đảm bảo khi người dùng sửa giá hoặc đổi quà tặng, 100% thông số kỹ thuật,
# cảm biến, camera, tính năng gốc KHÔNG BAO GIỜ BỊ XÓA!
# ─────────────────────────────────────────────────────────────────────────────

CATALOG_SPECS = {
    'a510': {
        'clean_key': 'a510',
        'formal_title': 'CAMERA HÀNH TRÌNH 70MAI A510 (SONY STARVIS 2)',
        'topic': 'Camera Hành Trình 70Mai A510',
        'default_price': '3.400.000 đ',
        'specs_desc': 'Trước 3K + Sau, cảm biến Sony Starvis 2 quay đêm siêu sáng, HDR, tích hợp GPS ADAS',
        'note': 'Chưa bao gồm thẻ nhớ (Gara có sẵn thẻ nhớ SanDisk/Kioxia chuyên dụng 32GB/64GB/128GB tốc độ cao).',
        'warranty': '12 tháng chính hãng 1 đổi 1, miễn phí công lắp đặt đi dây âm thẩm mỹ.',
        'keywords': ['a510', '70mai a510', 'cam a510', 'camera a510', 'cam 70mai a510', 'camera 70mai a510', 'starvis 2', 'sony starvis 2']
    },
    'a200': {
        'clean_key': 'a200',
        'formal_title': 'CAMERA HÀNH TRÌNH 70MAI A200 2K',
        'topic': 'Camera Hành Trình 70Mai A200',
        'default_price': '2.500.000 đ',
        'specs_desc': '2 mắt ghi hình Trước + Sau Full HD, góc nhìn rộng 130 độ, quay đêm rõ nét',
        'note': 'Tặng kèm thẻ nhớ 32GB chính hãng.',
        'warranty': '12 tháng chính hãng 1 đổi 1, bao trọn công lắp đặt đi dây âm thẩm mỹ.',
        'keywords': ['a200', '70mai a200', 'cam a200', 'camera a200', 'cam 70mai a200']
    },
    'a210': {
        'clean_key': 'a210',
        'formal_title': 'CAMERA HÀNH TRÌNH 70MAI A210 (TRƯỚC + SAU)',
        'topic': 'Camera Hành Trình 70Mai A210',
        'default_price': '2.500.000 đ',
        'specs_desc': '2 mắt ghi hình Trước + Sau Full HD, màn hình IPS hiển thị sắc nét',
        'note': 'Tặng thẻ nhớ 32GB tốc độ cao.',
        'warranty': '12 tháng chính hãng 1 đổi 1, miễn phí lắp đặt.',
        'keywords': ['a210', '70mai a210', 'cam a210', 'camera a210']
    },
    'm310': {
        'clean_key': 'm310',
        'formal_title': 'CAMERA HÀNH TRÌNH 70MAI M310 PLUS',
        'topic': 'Camera Hành Trình 70Mai M310 Plus',
        'default_price': '1.500.000 đ',
        'specs_desc': 'Ghi hình trước 2K QHD, thiết kế siêu nhỏ gọn giấu kín sau gương chiếu hậu, kết nối Wi-Fi điện thoại',
        'note': 'Tặng thẻ nhớ 32GB.',
        'warranty': '12 tháng chính hãng 1 đổi 1.',
        'keywords': ['m310', '70mai m310', 'cam m310', 'camera m310']
    },
    'a800se': {
        'clean_key': 'a800se',
        'formal_title': 'CAMERA HÀNH TRÌNH 70MAI A800SE (4K TRƯỚC + SAU)',
        'topic': 'Camera Hành Trình 70Mai A800SE',
        'default_price': '3.600.000 đ',
        'specs_desc': 'Ghi hình 4K Ultra HD trước + Sau Full HD, cảm biến cao cấp',
        'note': 'Bản thường 3.6tr | Bản SpeedEye (có cảnh báo giao thông) 4.8tr. Tặng thẻ 64GB.',
        'warranty': '12 tháng 1 đổi 1.',
        'keywords': ['a800se', 'a800', '70mai a800se', 'speedeye']
    },
    'm1': {
        'clean_key': 'm1',
        'formal_title': 'CAMERA HÀNH TRÌNH VIETMAP SPEEDMAP M1',
        'topic': 'Camera Hành Trình Vietmap M1',
        'default_price': '6.190.000 đ',
        'specs_desc': 'Cảnh báo tốc độ giới hạn trên từng cung đường, đọc biển báo giao thông, hiển thị tốc độ trên video',
        'note': 'Bản Trước + Sau (tặng thẻ 64GB + Bản quyền Vietmap Live trọn đời). Bản mắt trước: 5.190.000 đ.',
        'warranty': '12 tháng chính hãng toàn quốc.',
        'keywords': ['vietmap m1', 'cam m1', 'camera m1', 'm1', 'speedmap m1']
    },
    'f10': {
        'clean_key': 'f10',
        'formal_title': 'BI GẦM LED AOZOOM F10 SERIES (CHÍNH HÃNG)',
        'topic': 'Bi Gầm LED Aozoom F10',
        'default_price': '3.900.000 đ',
        'specs_desc': 'Ánh sáng bám đường siêu mạnh, mặt cắt thẳng chống chói xe đối diện, chống nước IP68 tuyệt đối',
        'note': 'F10 New: 3.9tr | F10 3 Màu (phá sương): 4.2tr | F10 Turbo V2 (trợ pha laser): 5.1tr.',
        'warranty': '3 năm (36 tháng) chính hãng đổi mới, tặng dưỡng zin theo từng dòng xe.',
        'keywords': ['f10', 'bi gam f10', 'den f10', 'f10 new', 'f10 turbo', 'aozoom f10']
    },
    's3': {
        'clean_key': 's3',
        'formal_title': 'BI GẦM LED NAOEVO S3',
        'topic': 'Bi Gầm Naoevo S3',
        'default_price': '1.500.000 đ',
        'specs_desc': 'Bi gầm LED phân khúc giá rẻ ngon bổ rẻ, sáng gấp 3 lần bóng halogen zin',
        'note': 'Bao công lắp đặt giắc cắm zin.',
        'warranty': '12 tháng chính hãng.',
        'keywords': ['s3', 'naoevo s3', 'bi gam s3', 'den s3']
    },
    'san_5d': {
        'clean_key': 'san 5d',
        'formal_title': 'THẢM LÓT SÀN 5D / 6D Ô TÔ CAO CẤP',
        'topic': 'Thảm Lót Sàn 5D/6D',
        'default_price': '1.800.000 đ',
        'specs_desc': 'Cắt may CNC chuẩn form 100% theo từng đời xe, da PU 5 lớp chống nước, chống cháy, dễ vệ sinh',
        'note': 'Xe 4 chỗ: 1.800.000 đ | Xe 7 chỗ: 2.300.000 đ. Tùy chọn may thêm túi để đồ phụ phí 100k/túi (tối đa 2 túi).',
        'warranty': 'Bảo hành đường may 2 năm.',
        'keywords': ['san 5d', 'tham 5d', 'lot san 5d', 'tham san 5d', 'san 6d', 'tham 6d']
    }
}


def find_catalog_product(text_clean: str):
    """Tìm sản phẩm catalog khớp trong văn bản"""
    for key, spec in CATALOG_SPECS.items():
        if key in text_clean:
            return spec
        for kw in spec['keywords']:
            if kw in text_clean:
                return spec
    return None


def clean_topic_name(raw_topic: str) -> str:
    """Loại bỏ sạch các chữ thừa ('giá', 'bảng giá', 'sản phẩm') để tên sản phẩm luôn tinh gọn chuẩn xác"""
    t = raw_topic.strip()
    # Bỏ các từ tiền tố thừa
    clean_prefix = [
        r'^(?:giá|gia|bảng\s*giá|bang\s*gia|chi\s*phí|chi\s*phi|tiền|tien)\s+(?:của|cho|về|xe)?\s*',
        r'^(?:sản\s*phẩm|san\s*pham|mặt\s*hàng|mat\s*hang|món|mon)\s*',
        r'^(?:quy\s*định|quy\s*dinh|chính\s*sách|chinh\s*sach)\s+(?:cho|về|của)?\s*'
    ]
    for pat in clean_prefix:
        t = re.sub(pat, '', t, flags=re.IGNORECASE).strip()
    return t


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

init_knowledge_db()


def is_learning_command(clean_text: str) -> bool:
    """Kiểm tra xem câu lệnh có phải là lệnh dạy học / ghi nhớ / sửa lại giá / quy định không"""
    clean = clean_text.strip().lower()

    # Nhận diện các câu lệnh sửa giá / quy định sản phẩm cụ thể
    if any(k in clean for k in ['sua lai gia', 'sua gia lai', 'sua lai', 'chinh lai', 'cap nhat lai gia', 'doi lai gia', 'doi gia thanh', 'sua gia thanh']):
        return True

    patterns = [
        r'^(?:ghi\s*nho|nho|hoc|day\s*ai|quy\s*tac|ghi\s*chu|luu\s*y)\s*[:,\-]?\s*',
        r'^(?:ghi\s*nho|nho|hoc|day\s*ai|quy\s*tac|ghi\s*chu|luu\s*y)\s+(?:cho\s+toi|giup\s+toi|rang|la)?\s*',
        r'^(?:nho\s+ky|nho\s+ro|ghi\s+nho\s+ky)\s*[:,\-]?\s*',
        r'^(?:sua\s*lai|chinh\s*lai|cap\s*nhat\s*lai|doi\s*lai|thay\s*doi)\s*(?:la|cho|thong\s*tin|quy\s*dinh|san\s*pham|gia)?\s*[:,\-]?\s*',
        r'\b(?:sua\s*lai|chinh\s*lai|cap\s*nhat\s*lai|doi\s*lai)\s+[a-z0-9]+\s+'
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
        r'^(?:sửa\s*lại\s*giá|sửa\s*giá\s*lại|sửa\s*lại|chỉnh\s*lại|cập\s*nhật\s*lại|đổi\s*lại|thay\s*đổi)\s*(?:là|cho|thông\s*tin|quy\s*định|sản\s*phẩm|giá)?\s*[:,\-]?\s*',
    ]
    for pat in patterns:
        raw = re.sub(pat, '', raw, flags=re.IGNORECASE).strip()
    return raw


def analyze_and_learn(raw_text: str) -> dict:
    """
    Phân tích nội dung kiến thức được dạy:
    1. Tự động chuyển đổi các dạng tiền tệ tự nhiên: '3tr5' -> '3.500.000 đ' (3500000)
    2. Nếu là sản phẩm Catalog (như 70mai A510, F10, M1...):
       BẢO TỒN NGUYÊN VẸN 100% CẤU HÌNH, THÔNG SỐ KỸ THUẬT, CẢM BIẾN VÀ CHẾ ĐỘ BẢO HÀNH!
    3. Làm sạch chủ đề, không để dính chữ thừa ('Giá A510' -> 'Camera Hành Trình 70Mai A510').
    4. Cập nhật đồng bộ vào database SQLite vĩnh viễn.
    """
    content = extract_learning_content(raw_text)
    if not content or len(content) < 2:
        return {
            "type": "clarify",
            "message": "⚠️ Bạn muốn tôi ghi nhớ hoặc sửa đổi thông tin gì ạ? Hãy nhắn theo mẫu:\n*(Ví dụ: `sửa lại giá a510 giá 3tr5`, `ghi nhớ: sàn 5d 4 chỗ là 1.8tr`)*"
        }

    clean_content = remove_accents(content).lower()

    # 1. BÓC TÁCH VÀ CHUẨN HÓA TIỀN TỆ THÔNG MINH
    price_display, price_num = parse_vietnamese_currency(content)

    # 2. BÓC TÁCH CHỦ ĐỀ SẢN PHẨM / DỊCH VỤ
    split_words = r'^(.*?)(?:\s+(?:là|la|giá|gia|chi\s*phí|chi\s*phi|tính|tinh|khoảng|khoang|tầm|tam|bảo\s*hành|bao\s*hanh|chưa\s*bao\s*gồm|chua\s*bao\s*gom|không\s*bao\s*gồm|khong\s*bao\s*gom|chưa\s*gồm|chua\s*gom|không\s*gồm|khong\s*gom|không\s*tặng|khong\s*tang|chưa\s*có|chua\s*co|không\s*có|khong\s*co|chỉ\s*có|chi\s*co|bao\s*gồm|bao\s*gom|đã\s*có|da\s*co|tặng\s*kèm|tang\s*kem|tặng|tang)\s+|\s*[:=]\s*)'
    topic_raw = ""
    m_topic = re.search(split_words, content, re.IGNORECASE)
    if m_topic and len(m_topic.group(1).strip()) >= 2:
        topic_raw = m_topic.group(1).strip()
    else:
        protected = re.sub(r'(\d)\.(\d)', r'\1__DOT__\2', content)
        parts = protected.split(',')
        topic_raw = parts[0].replace('__DOT__', '.').strip()

    # Loại bỏ sạch các chữ thừa ("giá", "bảng giá")
    cleaned_t = clean_topic_name(topic_raw)
    if not cleaned_t:
        cleaned_t = topic_raw

    topic = cleaned_t.strip().title()
    clean_topic = remove_accents(topic).lower()

    # 3. KIỂM TRA XEM CÓ THUỘC CATALOG SẢN PHẨM GỐC CỦA GARA KHÔNG
    catalog_item = find_catalog_product(clean_topic) or find_catalog_product(clean_content)

    # Nếu phát hiện thuộc Catalog sản phẩm chính thống:
    if catalog_item:
        formal_topic = catalog_item['topic']
        formal_title = catalog_item['formal_title']
        clean_catalog_key = catalog_item['clean_key']

        # Dùng giá mới nếu người dùng cung cấp (ví dụ 3.500.000 đ), nếu không thì giữ giá mặc định
        active_price = price_display if price_display else catalog_item['default_price']

        # Tách các lưu ý / yêu cầu bổ sung từ câu lệnh nếu có
        # (Ví dụ: "chưa bao gồm thẻ nhớ", "tặng thẻ 64gb")
        custom_note = catalog_item['note']
        if any(w in clean_content for w in ['chua bao gom the', 'chua the', 'khong the', 'khong kem the']):
            custom_note = "Chưa bao gồm thẻ nhớ (Gara có sẵn thẻ nhớ SanDisk/Kioxia chuyên dụng 32GB/64GB/128GB tốc độ cao)."
        elif any(w in clean_content for w in ['tang the 64gb', 'tang the 64', 'the 64gb']):
            custom_note = "Tặng kèm thẻ nhớ 64GB chuyên dụng tốc độ cao."
        elif any(w in clean_content for w in ['tang the 32gb', 'the 32gb']):
            custom_note = "Tặng kèm thẻ nhớ 32GB chuyên dụng."

        # SOẠN CÂU TRẢ LỜI MẪU: BẢO TỒN NGUYÊN VẸN 100% THÔNG SỐ KỸ THUẬT GỐC!
        formatted_reply = (
            f"📹 **{formal_title}:**\n"
            f"• **Giá trọn gói:** **{active_price}** ({catalog_item['specs_desc']})\n"
            f"• **Lưu ý:** {custom_note}\n"
            f"• **Bảo hành:** {catalog_item['warranty']}"
        )

        # Bộ từ khóa đầy đủ cho sản phẩm catalog
        keywords_set = set(catalog_item['keywords'])
        keywords_set.add(clean_catalog_key)
        keywords_set.add(remove_accents(formal_topic).lower())
        keywords_str = ", ".join(sorted(keywords_set))

        # Lưu vào SQLite
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_KNOWLEDGE)
        c = conn.cursor()

        # Tìm và xóa sạch mọi bản ghi cũ hoặc biến thể (như 'gia a510', 'a510') để tránh trùng lặp
        c.execute("""
            DELETE FROM gara_memory 
            WHERE clean_topic=? OR clean_topic LIKE ? OR clean_topic LIKE ?
        """, (clean_catalog_key, f"%{clean_catalog_key}%", f"%gia {clean_catalog_key}%"))

        c.execute("""
            INSERT INTO gara_memory 
            (topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (formal_topic, clean_catalog_key, keywords_str, content, active_price, custom_note, formatted_reply, now_str, now_str))
        mem_id = c.lastrowid
        conn.commit()
        conn.close()

        # Đồng bộ cập nhật giá vào Kho Hàng nếu có sản phẩm tương ứng trong banhang.db
        try:
            db_banhang = os.path.join(BASE_DIR, 'banhang.db')
            if os.path.exists(db_banhang) and price_num > 0:
                conn_bh = sqlite3.connect(db_banhang)
                c_bh = conn_bh.cursor()
                c_bh.execute("UPDATE products SET price=? WHERE name LIKE ? OR code LIKE ?", 
                             (price_num, f"%{clean_catalog_key}%", f"%{clean_catalog_key}%"))
                conn_bh.commit()
                conn_bh.close()
        except Exception:
            pass

        return {
            "type": "success",
            "module": "knowledge_learned",
            "message": (
                f"🧠 **ĐÃ CẬP NHẬT VÀ GHI NHỚ LẠI QUY ĐỊNH CHO {formal_topic.upper()}!**\n"
                f"─────────────────────────────────────────\n"
                f"📌 **Sản phẩm:** **{formal_topic}** (Mã nhớ: `#{mem_id}`)\n"
                f"💵 **Giá mới ghi nhận:** **{active_price}**\n"
                f"⚙️ **Thông số bảo tồn:** {catalog_item['specs_desc']}\n"
                f"📝 **Lưu ý / Quà tặng:** {custom_note}\n"
                f"🎯 **Từ khóa tự động:** `{keywords_str}`\n"
                f"─────────────────────────────────────────\n"
                f"👉 *Lần sau khi anh hoặc khách hàng hỏi về '{clean_catalog_key}' hay 'giá {clean_catalog_key}', AI sẽ tự động báo giá {active_price} kèm ĐẦY ĐỦ THÔNG SỐ KỸ THUẬT CHUẨN XÁC NHẤT!*"
            )
        }

    # 4. NẾU LÀ KIẾN THỨC MỚI KHÁC (KHÔNG THUỘC CATALOG CỐ ĐỊNH)
    # Bóc tách các tùy chọn phụ kiện
    options = []
    content_protected = re.sub(r'(\d)\.(\d)', r'\1__DOT__\2', content)
    sub_clauses = re.split(r'[,;\n]', content_protected)

    for clause in sub_clauses:
        cl = clause.replace('__DOT__', '.').strip()
        clean_cl = remove_accents(cl).lower()
        if not cl or clean_cl == clean_topic:
            continue
        if re.match(r'^(?:là|la|giá|gia)?\s*[\d\.\,]+\s*(?:đ|vnd|tr|k)?$', clean_cl):
            continue
        options.append(cl)

    options_text = "; ".join(options) if options else ""

    # Sinh từ khóa tự động
    keywords_set = set()
    keywords_set.add(clean_topic)
    for word in clean_topic.split():
        if len(word) >= 2:
            keywords_set.add(word)
    keywords_str = ", ".join(sorted(keywords_set))

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

    conn = sqlite3.connect(DB_KNOWLEDGE)
    c = conn.cursor()
    c.execute("SELECT id FROM gara_memory WHERE clean_topic=? OR clean_topic LIKE ?", (clean_topic, f"%{clean_topic}%"))
    existing = c.fetchone()

    if existing:
        mem_id = existing[0]
        c.execute("""
            UPDATE gara_memory 
            SET topic=?, clean_topic=?, keywords=?, raw_content=?, price_info=?, options_info=?, formatted_reply=?, updated_at=?
            WHERE id=?
        """, (topic, clean_topic, keywords_str, content, price_display, options_text, formatted_reply, now_str, mem_id))
    else:
        c.execute("""
            INSERT INTO gara_memory 
            (topic, clean_topic, keywords, raw_content, price_info, options_info, formatted_reply, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (topic, clean_topic, keywords_str, content, price_display, options_text, formatted_reply, now_str, now_str))
        mem_id = c.lastrowid

    conn.commit()
    conn.close()

    return {
        "type": "success",
        "module": "knowledge_learned",
        "message": (
            f"🧠 **ĐÃ HỌC VÀ GHI NHỚ VÀO BỘ NÃO GARA THÀNH CÔNG!**\n"
            f"─────────────────────────────────────────\n"
            f"📌 **Chủ đề:** **{topic}** (Mã nhớ: `#{mem_id}`)\n"
            f"💵 **Giá ghi nhận:** **{price_display or 'Theo tư vấn'}**\n"
            f"🎯 **Từ khóa kích hoạt:** `{keywords_str}`\n"
            f"─────────────────────────────────────────\n"
            f"👉 *Lần sau khi hỏi về '{topic}', AI sẽ tự động tư vấn đầy đủ quy định chính xác!*"
        )
    }


def query_learned_knowledge(clean_text: str, raw_text: str) -> dict:
    """
    Tra cứu trong cơ sở dữ liệu tri thức của gara.
    Nếu tìm thấy chủ đề hoặc từ khóa khớp -> Trả về câu trả lời đã học!
    """
    if not os.path.exists(DB_KNOWLEDGE):
        return None

    clean = clean_text.strip().lower()
    clean_no_gia = clean.replace('gia', '').replace('bao nhieu', '').replace('nhieu tien', '').strip()

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

        # Khớp chính xác clean_topic
        if clean_topic == clean or clean_topic == clean_no_gia:
            score += 25
        elif clean_topic in clean or clean in clean_topic:
            score += 15

        # Khớp từ khóa
        kw_list = [k.strip() for k in keywords_str.split(',') if k.strip()]
        for kw in kw_list:
            if kw == clean or kw == clean_no_gia:
                score += 20
            elif re.search(r'\b' + re.escape(kw) + r'\b', clean):
                score += 10
            elif kw in clean:
                score += 5

        if score > max_score and score >= 10:
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

def extract_product_keyword(text):
    """Bóc tách từ khóa sản phẩm bất chấp có dấu, không dấu, câu hỏi, dấu chấm hỏi"""
    clean = re.sub(r'[^\w\s]', ' ', text)
    remove_patterns = [
        r'gia\s+bao\s+nhieu', r'bao\s+nhieu\s+tien', r'bao\s+nhieu', r'nhieu\s+tien',
        r'giá\s+bao\s+nhiêu', r'bao\s+nhiêu\s+tiền', r'bao\s+nhiêu', r'nhiêu\s+tiền',
        r'ton\s+kho', r'tồn\s+kho', r'gia\s+ban', r'giá\s+bán', r'gia\s+von', r'giá\s+vốn',
        r'con\s+hang\s+khong', r'còn\s+hàng\s+không', r'con\s+hang', r'còn\s+hàng',
        r'het\s+hang', r'hết\s+hàng', r'bao\s+gia', r'báo\s+giá',
        r'cho\s+toi\s+hoi', r'cho\s+tôi\s+hỏi', r'hoi\s+gia', r'hỏi\s+giá',
        r'xem\s+gia', r'xem\s+giá', r'gia\s+sao', r'giá\s+sao',
        r'gia', r'giá', r'kho', r'mon', r'món', r'cai', r'cái', r'bo', r'bộ',
        r'khong', r'không', r'vay', r'vậy', r'a', r'ạ', r'ha', r'hả', r'tien', r'tiền'
    ]
    for pat in remove_patterns:
        clean = re.sub(r'(?i)\b' + pat + r'\b', ' ', clean)
    return ' '.join(clean.split()).strip()

"""
╔══════════════════════════════════════════════════════════════════════╗
║        TRỢ LÝ AI ĐIỀU HÀNH GARA Ô TÔ TRẦN BÌNH AUTO (ai_assistant.py) ║
║                                                                      ║
║  Tính năng tối ưu chuyên sâu:                                        ║
║  - HỎI ĐÁP TỪNG BƯỚC THÔNG MINH (CONVERSATIONAL WIZARD):             ║
║    + Khi nhắn "chi": Hỏi Số tiền ➔ Ngày chi ➔ Lý do ➔ Tự lưu sổ chi  ║
║    + Khi nhắn "doanh thu đèn": Hỏi Tên đèn ➔ Ngày lắp ➔ Số lượng     ║
║      ➔ Giá bán ➔ Giảm giá ➔ Khách/Biển số ➔ Xe ➔ Tự lưu báo cáo đèn  ║
║  - NHẬP 1 PHÁT XONG NGAY: "anh Cường accent f10 new 3900",           ║
║    "chi 350k tiền cơm trưa", combo nhiều món đèn cùng lúc            ║
║  - THỐNG KÊ DOANH SỐ ĐÈN: "doanh thu đèn tháng này", "đơn hôm nay"   ║
║  - HOÀN TÁC / HỦY ĐƠN: "hủy đơn đèn vừa nhập", "xóa đơn vừa tạo"     ║
║  - Tra cứu bảo hành theo biển số xe/SĐT, tồn kho & giá bán sản phẩm  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import sqlite3
from datetime import datetime, timedelta, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_BANHANG = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
DB_DEN = os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db')
DB_THUCHI = os.path.join(BASE_DIR, 'app_thuchi', 'finance.db')

try:
    import gemini_engine
    GEMINI_AVAILABLE = True
except Exception as e:
    gemini_engine = None
    GEMINI_AVAILABLE = False

try:
    import knowledge_base
    KNOWLEDGE_AVAILABLE = True
except Exception as e:
    knowledge_base = None
    KNOWLEDGE_AVAILABLE = False

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

def extract_date(text):
    """Trích xuất ngày tháng linh hoạt từ câu tiếng Việt, trả về (YYYY-MM-DD, clean_text)"""
    now = datetime.now()
    clean = text

    # Hôm nay
    if re.search(r'\b(hom nay|hôm nay)\b', text, re.IGNORECASE):
        d_str = now.strftime('%Y-%m-%d')
        clean = re.sub(r'\b(hom nay|hôm nay)\b', ' ', clean, flags=re.IGNORECASE)
        return d_str, clean

    # Hôm qua
    if re.search(r'\b(hom qua|hôm qua)\b', text, re.IGNORECASE):
        d_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        clean = re.sub(r'\b(hom qua|hôm qua)\b', ' ', clean, flags=re.IGNORECASE)
        return d_str, clean

    # Ngày DD/MM/YYYY hoặc DD/MM/YY hoặc DD/MM hoặc DD-MM-YYYY
    m = re.search(r'(?:ngay|ngày)?\s*\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text, re.IGNORECASE)
    if m:
        try:
            day = int(m.group(1))
            month = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else now.year
            if year < 100:
                year += 2000
            if 1 <= month <= 12 and 1 <= day <= 31:
                d_str = f"{year:04d}-{month:02d}-{day:02d}"
                clean = clean[:m.start()] + ' ' + clean[m.end():]
                return d_str, clean
        except:
            pass

    return now.strftime('%Y-%m-%d'), clean

def parse_month_year(text):
    """
    Trích xuất (month, year) cực kỳ linh hoạt từ câu tiếng Việt:
    - tháng 7/2026, t7/2026, 7/2026, 07/2025 -> (7, 2026)
    - tháng 7 năm 2026, thang 7 2025 -> (7, 2025)
    - tháng 7, t7, thg 7 -> (7, None) (Thiếu thông tin năm!)
    - năm 2025, 2026 -> (None, 2025)
    - hôm nay, hôm qua, tháng này, kỳ này -> các hằng số nhận diện
    """
    if not text:
        return None, None
    clean = remove_accents(text).lower().strip()

    if any(k in clean for k in ['hom nay', 'today']):
        return 'today', None
    if any(k in clean for k in ['hom qua', 'yesterday']):
        return 'yesterday', None
    if any(k in clean for k in ['thang nay', 'ky nay', 'hien tai']):
        return 'current_cycle', None

    month = None
    year = None

    # 1. Dạng Month / Year: "tháng 7/2026", "t7/2026", "7/2026", "07/2025", "thang 7 - 2024"
    m_my = re.search(r'\b(?:thang|thg|t)?\s*([0-1]?\d)[/-](202\d)\b', clean)
    if m_my:
        val_m = int(m_my.group(1))
        val_y = int(m_my.group(2))
        if 1 <= val_m <= 12:
            return val_m, val_y

    # 2. Dạng "tháng 7 năm 2026", "tháng 7 năm 26", "thang 7 2025"
    m_my2 = re.search(r'\b(?:thang|thg|t)\s*([0-1]?\d)\s+(?:nam\s+)?(202\d|\d{2})\b', clean)
    if m_my2:
        val_m = int(m_my2.group(1))
        raw_y = m_my2.group(2)
        val_y = int(raw_y) if len(raw_y) == 4 else (2000 + int(raw_y))
        if 1 <= val_m <= 12:
            return val_m, val_y

    # 3. Chỉ có năm: "năm 2025", "năm 2026"
    m_year_only = re.search(r'\b(?:nam\s+)?(202[0-9])\b', clean)
    if m_year_only and not re.search(r'\b(?:thang|thg|t)\b', clean):
        return None, int(m_year_only.group(1))

    # 4. Chỉ có tháng: "tháng 7", "tháng 07", "t7", "thg 7"
    m_m_only = re.search(r'\b(?:thang|thg|t)\s*([0-1]?\d)\b', clean)
    if m_m_only:
        val_m = int(m_m_only.group(1))
        if 1 <= val_m <= 12:
            month = val_m

    # Kiểm tra xem có năm đi kèm ở vị trí khác trong câu không
    if month is not None:
        m_y_any = re.search(r'\b(?:nam\s+)?(202[0-9])\b', clean)
        if m_y_any:
            year = int(m_y_any.group(1))

    return month, year

def parse_vietnamese_money(text, default_thousands=True):
    """
    Phân tích số tiền tiếng Việt cực kỳ linh hoạt và chuẩn xác:
    - Nhập có chữ 'k' ở sau (350k, 3900k, 50k, 2.5k, 500 nghin): AI tự hiểu và nhân thêm 1000
    - Nhập triệu (1.5tr, 1tr5, 2trieu, 2m): nhân 1.000.000
    - Nhập dấu chấm phân cách hàng nghìn: 350.000 -> 350,000
    - Nhập số >= 10000: 350000 -> 350,000
    - Nhập số trần < 10000 trong ngữ cảnh tiền (350, 3900, 50): tự hiểu là nghìn (nhân 1000)
    """
    if not text:
        return 0

    t = re.sub(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', ' ', str(text))
    t = re.sub(r'\b20[2-3]\d\b', ' ', t)
    clean = remove_accents(t).lower().replace(',', '.')

    # 1. Định dạng x tr y (VD: 1tr5, 2tr350)
    m_tr_split = re.search(r'(\d+)\s*tr\s*(\d+)\b', clean)
    if m_tr_split:
        main_tr = int(m_tr_split.group(1))
        dec = m_tr_split.group(2)
        dec_val = int(dec) * (10 ** (6 - len(dec))) if len(dec) <= 6 else 0
        return main_tr * 1000000 + dec_val

    # 2. Định dạng triệu (VD: 1.5tr, 2trieu, 2m)
    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|triệu|m)\b', clean)
    if m_tr:
        return int(round(float(m_tr.group(1)) * 1000000))

    # 3. ĐỊNH DẠNG CHỮ K Ở SAU (350k, 3900k, 50k, 2.5k, nghìn, ngàn) -> TỰ HIỂU VÀ NHÂN THÊM 1000
    m_k = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|nghin|ngan|nghìn|ngàn)\b', clean)
    if m_k:
        return int(round(float(m_k.group(1)) * 1000))

    # 4. Định dạng dấu chấm phân cách hàng nghìn (VD: 350.000, 3.900.000)
    m_dot = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\b', t)
    if m_dot:
        return int(m_dot.group(1).replace('.', ''))

    # 5. Định dạng số lớn >= 10000 (VD: 350000, 1500000)
    m_num_long = re.search(r'\b(\d{5,10})\b', clean)
    if m_num_long:
        return int(m_num_long.group(1))

    # 6. Có từ khóa tiền phía trước (VD: chi 350, thu 500, giá 3900)
    m_kw = re.search(r'(?:thu|chi|gia|giá|tiền|tien|giam|giảm|bot|bớt)\s+(\d{1,4})\b', clean)
    if m_kw:
        val = int(m_kw.group(1))
        return val * 1000 if val < 10000 else val

    # 7. Số thuần túy (VD: '350', '3900', '50')
    m_num = re.search(r'\b(\d{1,4})\b', clean)
    if m_num:
        val = int(m_num.group(1))
        if default_thousands and val < 10000:
            return val * 1000
        return val

    return 0

KNOWN_PRODUCT_CODES = {
    'A310', 'M310', 'A210', 'A200', 'A500', 'A510', 'A800', 'A810', 'M300', 'M500', 'S410', 'T800', 'X200',
    'KC01', 'S720', 'R440', 'TS2K', 'TS5K', 'M1', 'M2', 'C25', 'C26',
    'V20', 'F10', 'S3', 'S6', 'S8', 'S9', 'M10', 'M20', 'M30', 'M40', 'G1', 'CB150', 'F150',
    'BS10', 'D4', 'S150', 'S170', 'S200', 'S300', 'GT2K', 'GC6', 'NC6', 'B10'
}

def extract_license_plate(text):
    clean = text.upper().strip()
    clean_no_prefix = re.sub(r'^(?:XE|BIEN\s*SO|BIEN|BKS|SO\s*XE)\s+', '', clean, flags=re.IGNORECASE).strip()

    # Loại trừ ngay nếu trùng mã sản phẩm / camera / phụ kiện đã biết
    if clean in KNOWN_PRODUCT_CODES or clean_no_prefix in KNOWN_PRODUCT_CODES:
        return ""

    # 1. Biển số đầy đủ chuẩn VN: 63A-187.30, 63A - 187.30, 63A18730, 63LD-001.23, 51H-1234...
    m = re.search(r'\b(\d{2}[A-Z]{1,2}(?:\s*[\-\.]\s*|\s*)[0-9]{3,5}(?:[\.\s\-][0-9]{1,2})?)\b', clean)
    if m:
        return m.group(1).strip()

    # 2. Định dạng số xe có dấu chấm/gạch: 014.92, 187.30, 005.67 (3 số + . + 2 số)
    m = re.search(r'\b([0-9]{3}[\.\-\s][0-9]{2})\b', clean)
    if m:
        return m.group(1).strip()

    # 3. Biển số có sê-ri chữ cái và 5 số có định dạng: A-187.30, A.187.30 (bắt buộc có định dạng 3 số . 2 số để tránh nhầm mã SP như A310)
    m = re.search(r'\b([A-Z]{1,2}[\-\.][0-9]{3}[\.\-\s][0-9]{2})\b', clean)
    if m:
        return m.group(1).strip()

    # 4. Gõ tắt 4 hoặc 5 số cuối của biển số xe (VD: 01492, 18730, 48985, 00567...)
    m = re.search(r'\b([0-9]{4,5})\b', clean_no_prefix)
    if m:
        val = m.group(1).strip()
        if len(val) == 4 and val in ['2020', '2021', '2022', '2023', '2024', '2025', '2026']:
            if not any(k in clean.lower() for k in ['xe', 'bien', 'so xe', 'tra cuu']):
                return ""
        return val

    return ""

def clean_plate_raw(plate_str):
    if not plate_str:
        return ""
    return re.sub(r'[^A-Z0-9]', '', plate_str.upper())

def extract_phone(text):
    m = re.search(r'\b(0[35789]\d{8})\b', text)
    return m.group(1) if m else ""

COMMON_CAR_MODELS = {
    'vios', 'soluto', 'xpander', 'innova', 'camry', 'altis', 'accent', 'elantra',
    'cerato', 'k3', 'k5', 'morning', 'i10', 'city', 'civic', 'crv', 'brv', 'hrv', 'brio', 'accord',
    'cross', 'corolla', 'veloz', 'avanza', 'fortuner', 'everest', 'ranger', 'raptor', 'transit', 'ecosport', 'territory', 'explorer',
    'tucson', 'santafe', 'creta', 'stargazer', 'custin', 'palisade', 'sonet', 'seltos', 'carnival', 'sedona', 'sorento', 'sportage', 'carens',
    'vf3', 'vf5', 'vf6', 'vf7', 'vf8', 'vf9', 'e34', 'vfe34', 'fadil', 'luxa', 'luxsa',
    'attrage', 'outlander', 'triton', 'pajero', 'destinator', 'xforce',
    'cx3', 'cx30', 'cx5', 'cx8', 'mazda2', 'mazda3', 'mazda6', 'bt50',
    'almera', 'navara', 'xtrail', 'terra', 'sunny',
    'xl7', 'ertiga', 'swift', 'ciaz', 'carry',
    'forester', 'outback', 'peugeot', '2008', '3008', '5008', '408',
    'mg5', 'zs', 'hs', 'traiblazer', 'colorado', 'cruze', 'spark', 'lacetti', 'captiva', 'orlando',
    'solati', 'hino', 'dmax', 'mux', 'wigo', 'rush', 'hilux', 'yaris', 'c200', 'c300'
}

def extract_customer_search_intent(text):
    """
    Nhận diện ý định tra cứu thông tin khách hàng cực kỳ thông minh:
    - Nhập tên kèm đại từ nhân xưng: anh, chị, cô, chú, bác, em, dì, dượng, cậu, mợ, thím, thầy, bạn, ông, bà, cụ, khách hàng, khách, chủ xe, a, c, e
    - Nhập tên kèm dòng xe (dù có hoặc không có đại từ): 'anh toàn soluto', 'toàn soluto', 'anh toàn vios', 'toàn vios'
    - Cú pháp đảo: 'xe soluto anh toàn', 'xe vios của anh toàn'
    - Tiền tố linh hoạt: tìm, kiểm tra, tra cứu, check, xem, sđt, số điện thoại, xe của...
    """
    if not text:
        return None
    raw = text.strip()
    clean = remove_accents(raw).lower().strip()

    sub_text = re.sub(r'[,:;!?]+', ' ', clean)
    sub_text = re.sub(r'\s+', ' ', sub_text).strip()

    # Bỏ tiền tố tìm kiếm / sđt / xem xe nếu có
    sub_text = re.sub(r'^(?:tim(?:\s*kiem)?|kiem\s*tra|tra\s*cuu|check|xem|thong\s*tin(?:\s*ve)?|sdt(?:\s*cua)?|so\s*dien\s*thoai(?:\s*cua)?|so\s*dt(?:\s*cua)?|don\s*(?:hang)?(?:\s*cua)?)\s+', '', sub_text).strip()

    # Pattern A: xe [dòng xe] (của)? (anh/chị/...)? [tên khách] (VD: xe soluto anh toàn, xe vios của anh toàn)
    m_car_first = re.match(r'^(?:xe(?:\s*cua)?)\s+([a-zA-Z0-9\-_]+)\s+(?:cua\s+)?(?:(anh|chi|co|chu|bac|em|di|duong|cau|mo|thim|thay|ban|ong|ba|cu|a|c|e)\s+)?([a-zA-ZÀ-ỹ0-9\s\-_]+)$', sub_text)
    if m_car_first:
        car_kw = m_car_first.group(1).strip()
        hon = (m_car_first.group(2) or '').strip()
        name_raw = m_car_first.group(3).strip()
        name_tokens = [t for t in re.split(r'\s+', name_raw) if t]
        if name_tokens:
            return {
                'has_honorific': bool(hon),
                'honorific': hon,
                'name': name_tokens[0],
                'extra': [car_kw] + name_tokens[1:],
                'raw_query': f'{name_tokens[0]} {car_kw}',
                'all_tokens': [name_tokens[0], car_kw]
            }

    # Bỏ tiền tố xe / xe của nếu có
    sub_text = re.sub(r'^(?:xe(?:\s*cua)?)\s+', '', sub_text).strip()

    # Pattern B: Có đại từ nhân xưng (VD: 'anh toàn soluto', 'anh toàn vios', 'chị mỹ vios')
    full_hon = r'khach\s+hang|khach|chu\s+xe|anh|chi|co|chu|bac|em|di|duong|cau|mo|thim|thay|ban|ong|ba|cu'
    m_hon = re.match(rf'^({full_hon})\s+([a-zA-Z0-9\s\.\-_]+)$', sub_text)
    if not m_hon:
        # Đại từ viết tắt a, c, e (bắt buộc theo sau là chữ cái)
        m_short = re.match(r'^(a|c|e)\s+([a-zA-Z][a-zA-Z0-9\s\.\-_]*)$', sub_text)
        if m_short:
            m_hon = m_short

    # Danh sách từ dừng tuyệt đối KHÔNG PHẢI là tên khách hàng
    STOP_WORDS_FOR_NAME = {
        'nhung', 'cac', 'loai', 'san', 'pham', 'hang', 'the', 'duoc', 'khong', 'may',
        'bao', 'nao', 'chua', 'camera', 'cam', 'den', 'bi', 'bong', 'pha', 'gam',
        'phim', 'film', 'ghe', 'da', 'tien', 'phi', 'don', 'doanh', 'thu', 'chi',
        'tra', 'mua', 'ban', 'sua', 'xe', 'oto', 'auto', 'gara', 'quy', 'ket', 'so', 'du', 'ton'
    }

    if m_hon:
        hon = m_hon.group(1).strip()
        rest = m_hon.group(2).strip()

        # 1. Bảo vệ chống nhận nhầm từ "CÓ" (dấu sắc) thành đại từ "cô":
        if hon == 'co' and re.search(r'\b(có|cỏ|cỗ)\b', raw, re.IGNORECASE):
            return None

        # 2. Bảo vệ chống nhận nhầm hành động "CHI" tiền thành đại từ "chị":
        if hon in ('chi', 'c') and re.search(r'\b(\d+\s*(?:k|tr|trieu|m|nghin|ngan|vnd|d|\$)?|tien|com|xang|mat\s*bang|chi\s*phi|ung|nop)\b', rest, re.IGNORECASE):
            return None

        rest = re.sub(r'\b(nhe|dum|giup|voi|ha|ko|khong|a)\b$', '', rest).strip()
        tokens = [t for t in re.split(r'\s+', rest) if t]
        if not tokens:
            return None

        # Loại bỏ các từ đệm nối giữa tên và xe như: di, xe, chay, lai, chiec, con
        clean_tokens = [tokens[0]]
        for t in tokens[1:]:
            if t not in ('di', 'xe', 'chay', 'lai', 'chiec', 'con'):
                clean_tokens.append(t)

        first_token = clean_tokens[0].lower() if clean_tokens else ''
        # Tên khách hàng phải là chuỗi chữ cái hợp lệ (không chứa số), không nằm trong danh sách từ dừng
        if clean_tokens and re.match(r'^[a-zA-ZÀ-ỹ]+$', clean_tokens[0]) and first_token not in STOP_WORDS_FOR_NAME:
            return {
                'has_honorific': True,
                'honorific': hon,
                'name': clean_tokens[0],
                'extra': clean_tokens[1:],
                'raw_query': rest,
                'all_tokens': clean_tokens
            }

    # Pattern C: Không có đại từ nhưng có [Tên khách] [Dòng xe] (VD: 'toàn soluto', 'toàn vios', 'mỹ vios')
    tokens = [t for t in re.split(r'\s+', sub_text) if t]
    if len(tokens) >= 2 and tokens[0].isalpha():
        ignore_words = {'gia', 'bao', 'ban', 'con', 'het', 'muon', 'can', 'hoi', 'tim', 'nhap', 'xem', 'camera', 'cam', 'man', 'hinh', 'den', 'bi', 'bong', 'dan', 'phim', 'film'}
        if tokens[0] not in ignore_words and (tokens[1] in COMMON_CAR_MODELS or any(c in tokens[1] for c in ['vios', 'soluto', 'xpander', 'innova', 'camry', 'altis', 'accent', 'veloz', 'rush'])):
            clean_extra = [t for t in tokens[1:] if t not in ('di', 'xe', 'chay', 'lai', 'chiec', 'con')]
            return {
                'has_honorific': False,
                'honorific': '',
                'name': tokens[0],
                'extra': clean_extra,
                'raw_query': sub_text,
                'all_tokens': tokens
            }

    return None

# ── DANH MỤC ĐÈN THỰC TẾ & BẢNG GIÁ NIÊM YẾT TẠI GARA (k = nghìn đồng) ──
LAMP_CATALOG = [
    # Dòng V20 Series
    (r'\bv20\s*base\b', 'V20 BASE', 0),
    (r'\bv20\s*ultra\b|\bv20l\b|\bv20\b', 'BI LED V20', 0),
    # Dòng S Series
    (r'\b(?:xlight|naoevo)?\s*s3\s*pro\b|\bs3\s*pro\b', 'S3 PRO', 0),
    (r'\b(?:xlight|naoevo)?\s*s3\b|\bs3\b', 'S3', 0),
    (r'\b(?:xlight|naoevo)?\s*s6\s*pro\b|\bs6\s*pro\b', 'S6 PRO', 0),
    (r'\b(?:xlight|naoevo)?\s*s6\b|\bs6\b', 'S6', 0),
    (r'\b(?:xlight|naoevo)?\s*s8\s*pro\b|\bs8\s*pro\b', 'S8 PRO', 0),
    (r'\b(?:xlight|naoevo)?\s*s8\b|\bs8\b', 'S8', 0),
    (r'\b(?:xlight|naoevo)?\s*s9\s*pro\b|\bs9\s*pro\b', 'S9 PRO', 0),
    (r'\b(?:xlight|naoevo)?\s*s9\b|\bs9\b', 'S9', 0),
    # Dòng F10 Series
    (r'\bf10\s*pro\s*v2\b|\bf10\s*pro\b', 'F10 PRO V2', 0),
    (r'\bf10\s*turbo\b', 'F10 TURBO', 0),
    (r'\bf10\s*hyper\b|\bf10\s*heyper\b', 'F10 HYPER', 0),
    (r'\bf10\s*new\s*2\.?0\b|\bf10\s*new\b|\bf10\s*2\.?0\b|\bf10\b', 'F10 NEW 2.0', 0),
    (r'\bf10\s*3\s*mau\b|\bf10\s*ba\s*mau\b', 'F10 BA MÀU', 0),
    # Dòng M Series
    (r'\bm10\s*ultra\b|\bm10\b', 'M10 ULTRA', 0),
    (r'\bm20\s*ultra\b|\bm20\b', 'M20 ULTRA', 0),
    (r'\bm30\s*ultra\b|\bm30\b', 'M30 ULTRA', 0),
    (r'\bm40\s*ultra\b|\bm40\b', 'M40 ULTRA', 0),
    # Dòng Titan & GTR
    (r'\btitan\s*gold\b', 'TITAN GOLD', 0),
    (r'\btitan\s*black\b', 'TITAN BLACK', 0),
    (r'\btitan\s*platinum\b', 'TITAN PLATINUM', 0),
    (r'\bg1\s*turbo\b', 'G1 TURBO', 0),
    (r'\bxlight\s*301\b|\b301\b', 'XLIGHT 301', 0),
    (r'\bf150\s*pro\b|\bf150\b', 'F150 PRO', 0),
    (r'\bcb150\b', 'CB150', 0),
    # Mí LED & Vòng BM
    (r'\b(?:led\s*mi|mi\s*led|led\s*deo|mi\s*deo)\b', 'MÍ LED', 0),
    (r'\bvong\s*bm\b|\bvòng\s*bm\b', 'VÒNG BM', 0),
    (r'\bvong\s*angel\b|\bvòng\s*angel\b', 'VÒNG ANGEL', 0),
]

CAR_MODELS_LIST = [
    'DESTINATOR', 'FORTUNER', 'CARNIVAL', 'EVEREST', 'TERRITORY', 'STARGAZER', 'FORESTER', 'OUTLANDER',
    'XPANDER', 'INNOVA', 'SOLATI', 'TRANSIT', 'SANTAFE', 'TUCSON', 'CERATO', 'SORENTO', 'SEDONA',
    'ACCENT', 'ELANTRA', 'RANGER', 'CAMRY', 'MAZDA 3', 'MAZDA 2', 'MORNING', 'ERTIGA', 'CUSTIN',
    'VIOS', 'CITY', 'KONA', 'CROSS', 'HILUX', 'RAIZE', 'CRETA', 'SELTOS', 'SONET', 'MPV7',
    'VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9', 'CX5', 'CX8', 'BRV', 'CRV', 'MG5', 'I10', 'XL7', 'K3',
    'SOLUTO', 'ATTRAGE', 'VELOZ', 'AVANZA', 'ALTIS', 'RUSH', 'WIGO', 'ALMERA', 'CIVIC', 'ACCORD',
    'LUX A', 'LUX SA', 'FADIL', 'TRITON', 'NAVARA', 'BT50', 'PAJERO', 'SWIFT', 'TRAILBLAZER', 'COLORADO',
    'CRUZE', 'SPARK', 'LACETTI', 'CAPTIVA', 'ORLANDO', 'PEUGEOT 2008', 'PEUGEOT 3008', 'PEUGEOT 5008',
    'PEUGEOT', 'ZS', 'HS', 'DMAX', 'MUX', 'C200', 'C300'
]

def extract_car_from_text(text):
    """Bóc tách chính xác dòng xe từ văn bản hoặc chuỗi tên khách"""
    if not text:
        return ""
    for c in CAR_MODELS_LIST:
        pattern = r'\b' + re.escape(c) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return c
    return ""

def clean_customer_name(name_raw, found_car=""):
    """Làm sạch tên khách hàng, loại bỏ dòng xe hoặc ký tự thừa nếu bị dính vào tên"""
    if not name_raw:
        return ""
    name = name_raw.strip()
    if found_car:
        name = re.sub(r'[-\s/–(]*' + re.escape(found_car) + r'[\s/–)]*', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'[-\s/–]+$', '', name).strip()
    name = re.sub(r'^[-\s/–]+', '', name).strip()
    return name.title() if name else ""

def get_lamp_price_from_memory(lamp_name: str) -> int:
    """
    Tra cứu chuẩn xác mức giá bán của sản phẩm từ CƠ SỞ DỮ LIỆU GARA:
    Ưu tiên số 1: Bảng products trong app_banhang/tiem_lap_do.db (Kho hàng bán hàng thực tế)
    Ưu tiên số 2: Bảng gara_memory trong gara_knowledge.db (Quy định chủ gara dạy)
    Ưu tiên số 3: Lịch sử đơn hàng gần nhất (doanhthu_den.db hoặc tiem_lap_do.db)
    Tuyệt đối không tự suy diễn nếu không có trong dữ liệu!
    """
    if not lamp_name:
        return 0

    norm_name = lamp_name.strip()
    norm_upper = norm_name.upper()

    variants = [norm_upper]
    if '3 MÀU' in norm_upper:
        variants.extend([norm_upper.replace('3 MÀU', 'BA MÀU'), norm_upper.replace('3 MÀU', '(3 MÀU)')])
    elif 'BA MÀU' in norm_upper:
        variants.extend([norm_upper.replace('BA MÀU', '3 MÀU'), norm_upper.replace('BA MÀU', '(3 MÀU)')])
    if '3 MAU' in norm_upper:
        variants.extend([norm_upper.replace('3 MAU', 'BA MAU'), norm_upper.replace('3 MAU', '(3 MAU)')])
    elif 'BA MAU' in norm_upper:
        variants.extend([norm_upper.replace('BA MAU', '3 MAU'), norm_upper.replace('BA MAU', '(3 MAU)')])
    variants = list(dict.fromkeys(variants))

    # 1. ƯU TIÊN SỐ 1: BẢNG PRODUCTS TRONG TIEM_LAP_DO.DB (KHO HÀNG CHÍNH THỐNG)
    try:
        for v in variants:
            prods = search_product_in_catalog(v)
            if prods:
                p_val = prods[0].get('price', 0)
                if p_val and p_val > 0:
                    return int(round(p_val / 1000))
    except Exception:
        pass

    # 2. ƯU TIÊN SỐ 2: GARA_MEMORY (TRI THỨC QUY ĐỊNH GARA)
    if os.path.exists(DB_KNOWLEDGE):
        try:
            import knowledge_base
            conn_k = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
            c_k = conn_k.cursor()
            for v in variants:
                clean = knowledge_base.remove_accents(v).lower()
                c_k.execute("""
                    SELECT price_info FROM gara_memory 
                    WHERE clean_topic=? OR clean_topic LIKE ? OR keywords LIKE ?
                    ORDER BY id DESC LIMIT 1
                """, (clean, f"%{clean}%", f"%{clean}%"))
                row_k = c_k.fetchone()
                if row_k and row_k[0]:
                    p_str, p_num = knowledge_base.parse_vietnamese_currency(row_k[0])
                    if p_num > 0:
                        conn_k.close()
                        return int(round(p_num / 1000))
            conn_k.close()
        except Exception:
            pass

    # 3. ƯU TIÊN SỐ 3: LỊCH SỬ ĐƠN HÀNG DOANHTHU_DEN.DB
    db_den = os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db')
    if os.path.exists(db_den):
        try:
            conn_d = sqlite3.connect(db_den, timeout=5)
            c_d = conn_d.cursor()
            for v in variants:
                c_d.execute("SELECT price_k FROM orders WHERE UPPER(product_name)=? OR UPPER(product_name) LIKE ? ORDER BY id DESC LIMIT 1", (v, f"%{v}%"))
                row_d = c_d.fetchone()
                if row_d and row_d[0] and row_d[0] > 0:
                    conn_d.close()
                    return int(row_d[0])
            conn_d.close()
        except Exception:
            pass

    return 0


def search_product_in_catalog(query: str):
    """
    Tra cứu sản phẩm thông minh trong kho hàng (app_banhang/tiem_lap_do.db):
    1. Tìm chính xác theo mã sản phẩm hoặc tên sản phẩm
    2. Tìm kiếm LIKE theo cụm từ
    3. Tìm kiếm theo tokens đặc trưng (giữ nguyên '2.0', 'v2', '360', '4k', bỏ qua từ đệm như 'bi', 'đèn', 'led', 'gầm')
    """
    if not query or not query.strip():
        return []
        
    db_p = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
    if not os.path.exists(db_p):
        return []
        
    conn = sqlite3.connect(db_p, timeout=5)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    q = query.strip()
    
    # 1. Tìm chính xác
    c.execute("SELECT id, code, name, price, cost_price, stock, warranty_months FROM products WHERE UPPER(code)=UPPER(?) OR UPPER(name)=UPPER(?)", (q, q))
    rows = c.fetchall()
    if rows:
        conn.close()
        return [dict(r) for r in rows]
        
    # 2. Tìm LIKE
    c.execute("SELECT id, code, name, price, cost_price, stock, warranty_months FROM products WHERE UPPER(code) LIKE ? OR UPPER(name) LIKE ?", (f"%{q}%", f"%{q}%"))
    rows = c.fetchall()
    if rows:
        conn.close()
        return [dict(r) for r in rows]
        
    # 3. Tìm theo tokens
    raw_tokens = [t for t in re.split(r'[\s,]+', q.upper()) if t]
    stop_words = {'BI', 'DEN', 'LED', 'GAM', 'PHA', 'BO', 'CAP', 'CHO', 'XE', 'GIA', 'SUA', 'LAI', 'THANH', 'DOI', 'CHINH', 'CAPNHAT'}
    meaningful = [t for t in raw_tokens if t not in stop_words]
    
    if meaningful:
        clauses = " AND ".join(["UPPER(name) LIKE ?" for _ in meaningful])
        params = [f"%{t}%" for t in meaningful]
        # Ưu tiên sản phẩm có từ khóa đầu tiên ở gần đầu tên
        c.execute(f"""
            SELECT id, code, name, price, cost_price, stock, warranty_months 
            FROM products 
            WHERE {clauses}
            ORDER BY (CASE WHEN UPPER(name) LIKE ? THEN 0 ELSE 1 END), id DESC
        """, [f"%{meaningful[0]}%"] + params)
        rows = c.fetchall()
        if rows:
            conn.close()
            return [dict(r) for r in rows]

    conn.close()
    return []

def lookup_customer_and_car_by_identifier(identifier: str):
    """
    Tra cứu thông tin khách hàng và dòng xe dựa vào Biển số xe hoặc Số điện thoại.
    Tìm kiếm thông minh trong cả 2 cơ sở dữ liệu:
    1. app_banhang/tiem_lap_do.db (Lịch sử lắp đồ & dịch vụ gara hơn 8.500 đơn)
    2. app_baocao_den/doanhthu_den.db (Lịch sử nâng cấp đèn)
    """
    if not identifier:
        return {"found": False, "customer_name": "", "car_model": "", "phone": "", "license_plate": "", "source": ""}

    ident = identifier.strip()
    clean_p = clean_plate_raw(ident)
    is_phone = bool(re.search(r'\b(0[35789]\d{8})\b', ident))
    phone_clean = re.sub(r'\D', '', ident) if is_phone else ""

    result = {
        "found": False,
        "customer_name": "",
        "car_model": "",
        "phone": "",
        "license_plate": "",
        "source": ""
    }

    # 1. Tra cứu trong app_banhang/tiem_lap_do.db
    if os.path.exists(DB_BANHANG):
        try:
            conn = sqlite3.connect(DB_BANHANG, timeout=5)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # 1.0 Tra cứu trong bảng customers (danh bạ khách hàng đồng bộ từ VPOS)
            c_rows = []
            if is_phone and phone_clean:
                c.execute("""
                    SELECT customer_code, customer_name, phone, phone2, address
                    FROM customers
                    WHERE phone LIKE ? OR phone2 LIKE ?
                    LIMIT 1
                """, (f"%{phone_clean}%", f"%{phone_clean}%"))
                c_rows = c.fetchall()
            elif clean_p and len(clean_p) >= 4:
                c.execute("""
                    SELECT customer_code, customer_name, phone, phone2, address
                    FROM customers
                    WHERE REPLACE(REPLACE(REPLACE(REPLACE(UPPER(customer_code), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                       OR REPLACE(REPLACE(REPLACE(REPLACE(UPPER(customer_name), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                    LIMIT 1
                """, (f"%{clean_p}%", f"%{clean_p}%"))
                c_rows = c.fetchall()

            for cr in c_rows:
                c_name = (cr['customer_name'] or '').strip()
                c_plate = (cr['customer_code'] or '').strip()
                c_phone = (cr['phone'] or cr['phone2'] or '').strip()
                found_car = extract_car_from_text(c_name)
                cleaned_name = clean_customer_name(c_name, found_car)
                if cleaned_name or found_car:
                    result["found"] = True
                    result["customer_name"] = cleaned_name or c_name
                    result["car_model"] = found_car
                    result["phone"] = c_phone
                    result["license_plate"] = c_plate if re.search(r'\d{2}[A-Z]', c_plate) else ident
                    result["source"] = "customers_vpos"
                    conn.close()
                    return result

            rows = []
            if is_phone:
                c.execute("""
                    SELECT id, customer_name, phone, license_plate
                    FROM orders
                    WHERE phone LIKE ?
                    ORDER BY id DESC LIMIT 5
                """, (f"%{phone_clean}%",))
                rows = c.fetchall()
            elif clean_p and len(clean_p) >= 4:
                c.execute("""
                    SELECT id, customer_name, phone, license_plate
                    FROM orders
                    WHERE REPLACE(REPLACE(REPLACE(REPLACE(UPPER(license_plate), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                    ORDER BY id DESC LIMIT 5
                """, (f"%{clean_p}%",))
                rows = c.fetchall()

            for r in rows:
                c_name = (r['customer_name'] or '').strip()
                c_plate = (r['license_plate'] or '').strip()
                c_phone = (r['phone'] or '').strip()

                found_car = extract_car_from_text(c_name)
                if not found_car:
                    c.execute("SELECT item_name FROM order_items WHERE order_id = ?", (r['id'],))
                    items = c.fetchall()
                    for it in items:
                        c_in_item = extract_car_from_text(it['item_name'])
                        if c_in_item:
                            found_car = c_in_item
                            break

                cleaned_name = clean_customer_name(c_name, found_car)
                if cleaned_name or found_car:
                    result["found"] = True
                    result["customer_name"] = cleaned_name
                    result["car_model"] = found_car
                    result["phone"] = c_phone
                    result["license_plate"] = c_plate or ident
                    result["source"] = "tiem_lap_do"
                    conn.close()
                    return result

            conn.close()
        except Exception:
            pass

    # 2. Tra cứu trong app_baocao_den/doanhthu_den.db
    if os.path.exists(DB_DEN):
        try:
            conn = sqlite3.connect(DB_DEN, timeout=5)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            query_cond = f"%{clean_p}%" if clean_p else f"%{ident}%"
            c.execute("""
                SELECT id, customer_name, car_model
                FROM orders
                WHERE REPLACE(REPLACE(REPLACE(REPLACE(UPPER(customer_name), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                   OR REPLACE(REPLACE(REPLACE(REPLACE(UPPER(car_model), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                ORDER BY id DESC LIMIT 5
            """, (query_cond, query_cond))
            rows = c.fetchall()

            for r in rows:
                c_name = (r['customer_name'] or '').strip()
                c_car = (r['car_model'] or '').strip()
                found_car = extract_car_from_text(c_car) or extract_car_from_text(c_name) or c_car
                cleaned_name = clean_customer_name(c_name, found_car)

                if clean_p and clean_plate_raw(cleaned_name) == clean_p:
                    cleaned_name = ""

                if cleaned_name or found_car:
                    result["found"] = True
                    result["customer_name"] = cleaned_name
                    result["car_model"] = found_car
                    result["license_plate"] = ident
                    result["source"] = "doanhthu_den"
                    conn.close()
                    return result

            conn.close()
        except Exception:
            pass

    return result

def get_current_cycle():
    """Chu kỳ báo cáo đèn 9 đến 8 hàng tháng"""
    today = date.today()
    if today.day <= 8:
        if today.month == 1:
            return today.year - 1, 12
        return today.year, today.month - 1
    return today.year, today.month

def get_cycle_dates(year, month):
    start_date = f"{year:04d}-{month:02d}-09"
    if month == 12:
        end_date = f"{year + 1:04d}-01-08"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-08"
    return start_date, end_date

# ─────────────────────────────────────────────────────────────────────────────
# BỘ NHỚ HỘI THOẠI HỎI ĐÁP TỪNG BƯỚC (WIZARD CONVERSATIONAL STATE)
# ─────────────────────────────────────────────────────────────────────────────
WIZARD_SESSIONS = {}
LAST_CONSULTED_TOPIC = {}

def detect_consulted_product(text_clean: str) -> str:
    """Nhận diện sản phẩm đang được nhắc tới trong câu hỏi / câu lệnh"""
    PROD_MAP = [
        ('a510', 'a510'), ('70mai a510', 'a510'),
        ('a200', 'a200'), ('70mai a200', 'a200'),
        ('a210', 'a210'), ('70mai a210', 'a210'),
        ('m310', 'm310'), ('70mai m310', 'm310'),
        ('a800se', 'a800se'), ('a800', 'a800se'),
        ('vietmap m1', 'm1'), ('cam m1', 'm1'), ('m1', 'm1'),
        ('vietmap m2', 'm2'), ('m2', 'm2'),
        ('f10 turbo', 'f10'), ('bi gam f10', 'f10'), ('den f10', 'f10'), ('f10', 'f10'),
        ('naoevo s3', 's3'), ('bi gam s3', 's3'), ('s3', 's3'),
        ('san 5d', 'san 5d'), ('tham 5d', 'san 5d'), ('lot san 5d', 'san 5d'),
        ('bs10', 'bs10'), ('icar d4', 'd4'),
        ('s150', 'winca s150'), ('b10lite', 'bravo b10')
    ]
    for pattern, key in PROD_MAP:
        if re.search(r'\b' + re.escape(pattern) + r'\b', text_clean):
            return key
    return ""

def commit_thuchi_transaction(payload):
    """Thực thi ghi khoản thu/chi vào Database sau khi người dùng đã xác nhận"""
    trans_type = payload['trans_type']
    amount = payload['amount']
    note = payload['note']
    date_str = payload['date_str']

    if not os.path.exists(DB_THUCHI):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu sổ thu chi!"}

    try:
        conn = sqlite3.connect(DB_THUCHI, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT id, name FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1")
        p = c.fetchone()
        if not p:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO periods (name, start_date, status) VALUES ('Kỳ tự động AI', ?, 'active')", (now_str,))
            period_id = c.lastrowid
            period_name = "Kỳ tự động AI"
        else:
            period_id = p['id']
            period_name = p['name']

        now_str = f"{date_str} {datetime.now().strftime('%H:%M:%S')}"
        c.execute("INSERT INTO transactions (period_id, type, amount, note, created_at) VALUES (?, ?, ?, ?, ?)",
                  (period_id, trans_type, amount, note.capitalize(), now_str))
        conn.commit()

        c.execute("SELECT SUM(CASE WHEN type='thu' THEN amount ELSE -amount END) FROM transactions WHERE period_id = ?", (period_id,))
        balance = c.fetchone()[0] or 0
        conn.close()

        action_icon = "💸 ĐÃ GHI KHOẢN CHI" if trans_type == 'chi' else "💰 ĐÃ GHI KHOẢN THU"
        amount_k_str = f"{amount//1000:,}k" if amount >= 1000 else f"{amount:,}đ"
        return {
            "type": "success",
            "module": "thuchi",
            "message": f"✅ {action_icon} THÀNH CÔNG!\n\n"
                       f"• **Phân loại:** {trans_type.upper()}\n"
                       f"• **Số tiền:** **{amount:,.0f} đ** ({amount_k_str})\n"
                       f"• **Nội dung:** {note.capitalize()}\n"
                       f"• **Ngày ghi nhận:** {date_str}\n"
                       f"• **Kỳ ghi nhận:** {period_name}\n"
                       f"• **Số dư quỹ kỳ này hiện tại:** **{balance:,.0f} đ**\n\n"
                       f"👉 [Bấm vào đây để mở Sổ Thu Chi](/thuchi/)"
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi ghi sổ thu chi: {str(e)}"}


def commit_baocao_den_order(payload):
    """Thực thi ghi đơn báo cáo đèn vào Database sau khi người dùng đã xác nhận"""
    items = payload['items']
    cust_name = payload['cust_name']
    found_car = payload['found_car']
    plate = payload['plate']
    order_date = payload['order_date']
    discount_k = payload.get('discount_k', 0)
    total_base_k = payload.get('total_base_k', 0)
    total_final_k = payload.get('total_final_k', 0)

    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        saved_ids = []
        cust_record = f"{cust_name} ({plate})" if (plate and plate not in cust_name) else cust_name
        for it in items:
            c.execute("""
                INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                VALUES (?, ?, ?, ?, ?, ?, 'AI_ASSISTANT')
            """, (order_date, it['product_name'], cust_record, found_car or 'XE Ô TÔ', it['quantity'], it['final_price_k']))
            saved_ids.append(c.lastrowid)
        conn.commit()
        conn.close()

        item_lines = []
        for i, it in enumerate(items, 1):
            qty_label = f"{it['quantity']} bộ " if it['quantity'] > 1 else ""
            default_tag = " *(Giá niêm yết tự động)*" if it.get('is_default') else ""
            base_str = f"{it['base_price_k']*1000:,.0f} đ ({it['base_price_k']:,}k){default_tag}"
            if it['discount_k'] > 0:
                final_str = f"{it['final_price_k']*1000:,.0f} đ ({it['final_price_k']:,}k)"
                item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: {base_str} ➔ Sau giảm: **{final_str}**")
            else:
                item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: **{base_str}**")

        items_text = "\n".join(item_lines)
        total_base_str = f"{total_base_k*1000:,.0f} đ ({total_base_k:,}k)"
        total_final_str = f"{total_final_k*1000:,.0f} đ ({total_final_k:,}k)"
        discount_text = f"\n• **Giảm giá:** -{discount_k*1000:,.0f} đ (-{discount_k:,}k)" if discount_k > 0 else ""

        id_text = f"#{saved_ids[0]}" if len(saved_ids) == 1 else f"#{saved_ids[0]} - #{saved_ids[-1]} ({len(saved_ids)} món)"

        return {
            "type": "success",
            "module": "den",
            "message": (
                f"💡 **ĐÃ XÁC NHẬN & GHI NHẬN ĐƠN BÁO CÁO ĐÈN THÀNH CÔNG!**\n\n"
                f"• **Mã đơn:** {id_text}\n"
                f"• **Khách hàng:** **{cust_name}**\n"
                f"• **Dòng xe:** {found_car or 'Chưa rõ dòng xe'}\n"
                + (f"• **Biển số:** {plate}\n" if plate else "")
                + f"• **Ngày ghi nhận:** {order_date}\n\n"
                f"📦 **Chi tiết các món ({len(items)} món):**\n"
                f"{items_text}\n"
                + (f"• **Tổng tiền gốc:** {total_base_str}\n" if discount_k > 0 else "")
                + discount_text
                + f"\n• 💰 **DOANH THU THỰC THU:** **{total_final_str}**\n\n"
                f"👉 [Bấm vào đây để xem Báo Cáo Doanh Thu Đèn](/den/)\n"
                f"*(Nếu muốn hủy, gõ 'hủy đơn vừa nhập' để hoàn tác ngay)*"
            )
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi lưu báo cáo đèn: {str(e)}"}


def execute_confirmed_action(action_type, payload, session_id="default_user"):
    """Thực thi hành động sau khi người dùng đã xác nhận đồng ý"""
    if action_type == 'update_product_price':
        prod_id = payload.get('product_id')
        new_price = payload.get('new_price', 0)
        name = payload.get('name', '')
        code = payload.get('code', '')
        old_price = payload.get('old_price', 0)

        conn_up = sqlite3.connect(DB_BANHANG)
        c_up = conn_up.cursor()
        c_up.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, prod_id))
        c_up.execute("SELECT stock FROM products WHERE id = ?", (prod_id,))
        row_st = c_up.fetchone()
        stock = row_st[0] if row_st else 0
        conn_up.commit()
        conn_up.close()

        # Xóa các rule tri thức cũ có thể xung đột
        try:
            conn_k = sqlite3.connect(os.path.join(BASE_DIR, 'gara_knowledge.db'), timeout=5)
            c_k = conn_k.cursor()
            c_k.execute("DELETE FROM gara_memory WHERE clean_topic LIKE ? OR keywords LIKE ?", 
                        (f"%{remove_accents(name).lower()}%", f"%{code.lower()}%"))
            conn_k.commit()
            conn_k.close()
        except Exception:
            pass

        return {
            "type": "success",
            "message": (
                f"✅ **ĐÃ CẬP NHẬT GIÁ THÀNH CÔNG VÀO PHẦN MỀM BÁN HÀNG!**\n"
                f"─────────────────────────────────────────\n"
                f"• 📦 **Sản phẩm:** **{name}** (Mã: `{code}`)\n"
                f"• 💰 **Giá cũ:** {old_price:,.0f} đ ➔ **Giá mới: {new_price:,.0f} đ**\n"
                f"• 📊 **Tồn kho hiện tại:** {stock}\n"
                f"─────────────────────────────────────────\n"
                f"👉 Mức giá mới đã có hiệu lực ngay lập tức trong toàn bộ phần mềm bán hàng và trợ lý AI!"
            )
        }

    if action_type == 'learn_knowledge':
        raw_text = payload.get('raw_text', '')
        if knowledge_base:
            return knowledge_base.analyze_and_learn(raw_text)
        return {"type": "error", "message": "Module tri thức chưa sẵn sàng."}

    elif action_type == 'delete_knowledge':
        kw = payload.get('keyword_or_id', '')
        if knowledge_base:
            return knowledge_base.delete_learned_knowledge(kw)
        return {"type": "error", "message": "Module tri thức chưa sẵn sàng."}

    elif action_type == 'thuchi':
        return commit_thuchi_transaction(payload)

    elif action_type == 'baocao_den':
        return commit_baocao_den_order(payload)

    elif action_type == 'admin_edit_order':
        kwargs = payload.get('kwargs', {})
        if gemini_engine:
            res_txt = gemini_engine.sua_don_hang(**kwargs)
            return {"type": "success", "message": f"✅ **ĐÃ XÁC NHẬN SỬA ĐƠN THÀNH CÔNG!**\n\n{res_txt}"}
        return {"type": "error", "message": "Gemini engine chưa sẵn sàng."}

    elif action_type == 'admin_delete_order':
        order_id = payload.get('order_id')
        if gemini_engine:
            res_txt = gemini_engine.xoa_don_hang(order_id)
            return {"type": "success", "message": f"✅ **ĐÃ XÁC NHẬN XÓA ĐƠN THÀNH CÔNG!**\n\n{res_txt}"}
        return {"type": "error", "message": "Gemini engine chưa sẵn sàng."}

    elif action_type == 'admin_update_stock':
        kwargs = payload.get('kwargs', {})
        if gemini_engine:
            res_txt = gemini_engine.cap_nhat_kho_hang(**kwargs)
            return {"type": "success", "message": f"✅ **ĐÃ XÁC NHẬN CẬP NHẬT KHO THÀNH CÔNG!**\n\n{res_txt}"}
        return {"type": "error", "message": "Gemini engine chưa sẵn sàng."}

    return {"type": "error", "message": "Không nhận diện được hành động cần thực thi."}

def handle_wizard_step(user_text, session_id):
    """Xử lý từng câu trả lời của người dùng trong phiên phỏng vấn AI (kèm bước xác nhận)"""
    session = WIZARD_SESSIONS.get(session_id)
    if not session:
        return None

    clean = remove_accents(user_text).strip().lower()

    # Cho phép thoát / hủy bất kỳ lúc nào
    if clean in ['huy', 'hủy', 'cancel', 'thoat', 'thoát', 'dung', 'dừng', 'stop']:
        del WIZARD_SESSIONS[session_id]
        return {
            "type": "info",
            "message": "🛑 **ĐÃ HỦY PHIÊN NHẬP LIỆU TỪNG BƯỚC!**\nKhông có dữ liệu nào được lưu. Bạn có thể bắt đầu lại bất cứ lúc nào."
        }

    flow = session.get('flow')
    step = session.get('step')
    data = session.get('data')

    # ═════════════════════════════════════════════════════════════════════════
    # FLOW XÁC NHẬN TOÀN DIỆN (UNIVERSAL CONFIRMATION INTERCEPTOR)
    # Áp dụng cho MỌI thao tác: Ghi nhớ, Sửa giá, Thu chi, Đơn đèn, Sửa/Xóa đơn
    # ═════════════════════════════════════════════════════════════════════════
    if flow == 'confirm_action':
        is_confirm = clean in [
            'ok', 'okie', 'oke', 'yes', 'y', 'co', 'có', 'luu', 'lưu',
            'xac nhan', 'xác nhận', 'dong y', 'đồng ý', 'them', 'thêm', 'duoc', 'được', '1',
            'dung', 'đúng', 'chinh xac', 'chính xác', 'thuc hien', 'thực hiện', 'ok / luu', 'ok/luu'
        ] or clean.startswith('ok')

        is_cancel = clean in ['huy', 'hủy', 'khong', 'không', 'no', 'cancel', 'thoi', 'thôi', 'dung', 'dừng', 'stop', 'k']

        if is_confirm:
            action_type = session.get('action_type')
            payload = session.get('payload', {})
            del WIZARD_SESSIONS[session_id]
            return execute_confirmed_action(action_type, payload, session_id)
        elif is_cancel:
            del WIZARD_SESSIONS[session_id]
            return {
                "type": "info",
                "message": "🛑 **ĐÃ HỦY THAO TÁC!**\nKhông có bất kỳ dữ liệu nào bị thay đổi trong hệ thống."
            }
        else:
            del WIZARD_SESSIONS[session_id]
            return None

    # ═════════════════════════════════════════════════════════════════════════
    # FLOW BỔ SUNG THÔNG TIN CÒN THIẾU KHI XE MỚI / CHƯA CÓ TRONG HỆ THỐNG GARA
    # ═════════════════════════════════════════════════════════════════════════
    if flow == 'lamp_fill_missing':
        pending = session.get('pending_payload', {})
        items = pending.get('items', [])
        plate = pending.get('plate', '')
        phone = pending.get('phone', '')
        order_date = pending.get('order_date', datetime.now().strftime('%Y-%m-%d'))
        discount_k = pending.get('discount_k', 0)
        total_base_k = pending.get('total_base_k', 0)
        total_final_k = pending.get('total_final_k', 0)
        found_car = pending.get('found_car', '')

        # Bóc tách dòng xe từ câu trả lời của người dùng nếu có
        user_ans = user_text.strip()
        ans_car = ''
        for c in CAR_MODELS_LIST:
            m_c = re.search(r'(?:cho\s+xe\s+|xe\s+)?\b' + re.escape(c) + r'\b', user_ans, re.IGNORECASE)
            if m_c:
                ans_car = c
                user_ans = user_ans[:m_c.start()] + ' ' + user_ans[m_c.end():]
                break

        if ans_car:
            found_car = ans_car

        # Phần còn lại là tên khách hàng
        cust_name = re.sub(r'^(?:tên\s*là|ten\s*la|khách\s*là|khach\s*la|tên|ten|khách|khach)\s*', '', user_ans, flags=re.IGNORECASE).strip()
        cust_name = re.sub(r'[-\s/–]+$', '', cust_name).strip()
        cust_name = re.sub(r'^[-\s/–]+', '', cust_name).strip()
        cust_name = cust_name.title() if cust_name else "KHÁCH LẺ"

        # Định dạng các món đèn
        item_lines = []
        for i, it in enumerate(items, 1):
            qty_label = f"{it['quantity']} bộ " if it['quantity'] > 1 else ""
            default_tag = " *(Giá niêm yết tự động)*" if it.get('is_default') else ""
            base_str = f"{it['base_price_k']*1000:,.0f} đ ({it['base_price_k']:,}k){default_tag}"
            if it.get('discount_k', 0) > 0:
                final_str = f"{it['final_price_k']*1000:,.0f} đ ({it['final_price_k']:,}k)"
                item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: {base_str} ➔ Sau giảm: **{final_str}**")
            else:
                item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: **{base_str}**")

        items_text = "\n".join(item_lines)
        total_final_str = f"{total_final_k*1000:,.0f} đ ({total_final_k:,}k)"

        confirm_msg = (
            f"❓ **XÁC NHẬN TẠO ĐƠN VÀO SỔ BÁO CÁO DOANH THU ĐÈN:**\n"
            f"───────────────────────────────────────\n"
            f"• 👤 **Khách hàng:** **{cust_name}**\n"
            f"• 🚗 **Dòng xe:** **{found_car or 'Chưa rõ dòng xe'}**\n"
            + (f"• 🚘 **Biển số:** **{plate}**\n" if plate else "")
            + (f"• 📞 **Số điện thoại:** **{phone}**\n" if phone else "")
            + f"• 📦 **Sản phẩm lắp đặt:**\n{items_text}\n"
            + f"• 💰 **DOANH THU THỰC THU:** **{total_final_str}**\n"
            + f"• 📅 **Ngày lắp:** **{order_date}** *(Hôm nay theo đồng hồ hệ thống)*\n"
            f"───────────────────────────────────────\n"
            f"👉 Anh có chắc chắn muốn **LƯU ĐƠN HÀNG NÀY** vào hệ thống không?\n\n"
            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào Báo Cáo Đèn | Nhắn **'hủy'** để bỏ qua)*"
        )

        WIZARD_SESSIONS[session_id] = {
            'flow': 'confirm_action',
            'action_type': 'baocao_den',
            'payload': {
                'items': items,
                'cust_name': cust_name,
                'found_car': found_car,
                'plate': plate,
                'phone': phone,
                'order_date': order_date,
                'discount_k': discount_k,
                'total_base_k': total_base_k,
                'total_final_k': total_final_k
            }
        }
        return {
            "type": "clarify",
            "message": confirm_msg
        }

    # ══════════════════════════════════════════
    # FLOW 0: HỎI LẠI NĂM KHI THIẾU THÔNG TIN (BÁO CÁO ĐÈN)
    # ══════════════════════════════════════════
    if flow == 'ask_year_den':
        target_month = session.get('month', 7)
        m_parsed, y_parsed = parse_month_year(user_text)
        chosen_year = y_parsed
        if not chosen_year:
            m_short_y = re.search(r'\b(202[0-9]|2[2-9])\b', clean)
            if m_short_y:
                val = int(m_short_y.group(1))
                chosen_year = val if val > 100 else (2000 + val)

        if not chosen_year:
            avail_years = get_available_years_for_cycle_month(target_month)
            return {
                "type": "clarify",
                "message": (
                    f"⚠️ Chưa nhận diện được năm. Bạn muốn xem tháng {target_month} của năm nào?\n"
                    f"*(Ví dụ gõ: {', '.join(str(y) for y in avail_years)} hoặc gõ `hủy` để thoát)*"
                )
            }

        del WIZARD_SESSIONS[session_id]
        return generate_baocao_den_cycle_report(chosen_year, target_month)



    # ══════════════════════════════════════════
    # FLOW 1: WIZARD CHI (SỔ THU CHI)
    # ══════════════════════════════════════════
    if flow == 'chi':
        # Bước 1: Số tiền chi (Nhận chữ k tự hiểu nhân thêm 1000)
        if step == 1:
            amount = parse_vietnamese_money(user_text, default_thousands=True)
            if amount <= 0:
                return {
                    "type": "clarify",
                    "message": "⚠️ Chưa nhận diện được số tiền. Bạn vui lòng nhập lại số tiền chi (Ví dụ: `350k`, `1.5tr`, `150.000`... hoặc gõ `hủy` để thoát):"
                }
            data['amount'] = amount
            session['step'] = 2
            amount_k_str = f"{amount//1000:,}k" if amount >= 1000 else f"{amount:,}đ"
            return {
                "type": "clarify",
                "message": (
                    f"💸 Số tiền chi: **{amount:,.0f} đ** ({amount_k_str})\n\n"
                    f"📅 **BƯỚC 2/3: THỜI GIAN / NGÀY CHI**\n"
                    f"Khoản chi này vào ngày nào?\n"
                    f"*(Gõ **'0'** hoặc **'hôm nay'** để lấy ngày hiện tại, hoặc nhập VD: `20/10/2026`, `hôm qua`...)*"
                )
            }

        # Bước 2: Thời gian / Ngày chi
        elif step == 2:
            if clean in ['0', 'hom nay', 'hôm nay', 'nay', '']:
                date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str, _ = extract_date(user_text)
            data['date'] = date_str
            session['step'] = 3
            return {
                "type": "clarify",
                "message": (
                    f"📅 Ngày chi: **{date_str}**\n\n"
                    f"📝 **BƯỚC 3/3: NỘI DUNG / LÝ DO CHI**\n"
                    f"Lý do / nội dung chi là gì?\n"
                    f"*(Ví dụ: Tiền cơm trưa, mua xăng, tiền mặt bằng, tiền điện...)*"
                )
            }

        # Bước 3: Lý do / Nội dung chi ➔ CHUYỂN SANG BƯỚC XÁC NHẬN (CONFIRM)
        elif step == 3:
            note = user_text.strip()
            if not note or note == '0':
                note = "Chi nhanh qua Trợ lý AI"
            data['note'] = note
            session['step'] = 'confirm'

            amount = data['amount']
            amount_k_str = f"{amount//1000:,}k" if amount >= 1000 else f"{amount:,}đ"
            return {
                "type": "clarify",
                "message": (
                    f"📋 **XÁC NHẬN KHOẢN CHI**\n"
                    f"───────────────────────────\n"
                    f"• 💸 **Số tiền:** **{amount:,.0f} đ** ({amount_k_str})\n"
                    f"• 📅 **Thời gian:** **{data['date']}**\n"
                    f"• 📝 **Nội dung / Lý do:** **{note}**\n"
                    f"───────────────────────────\n"
                    f"❓ **Bạn có xác nhận lưu khoản chi này vào Sổ Thu Chi không?**\n\n"
                    f"👉 Gõ **'ok'**, **'lưu'**, **'có'** hoặc **'xác nhận'** để thêm vào sổ.\n"
                    f"👉 Gõ **'hủy'** hoặc **'không'** để hủy bỏ."
                )
            }

        # Bước Xác Nhận Khoản Chi ➔ LƯU DATABASE HOẶC HỦY
        elif step == 'confirm':
            # Người dùng xác nhận lưu
            is_confirm = clean in [
                'ok', 'okie', 'oke', 'yes', 'y', 'co', 'có', 'luu', 'lưu',
                'xac nhan', 'xác nhận', 'dong y', 'đồng ý', 'them', 'thêm', 'duoc', 'được', '1'
            ] or clean.startswith('ok')

            if is_confirm:
                amount = data['amount']
                date_str = data['date']
                note = data['note']
                del WIZARD_SESSIONS[session_id]

                if not os.path.exists(DB_THUCHI):
                    return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu sổ thu chi!"}

                try:
                    conn = sqlite3.connect(DB_THUCHI, timeout=10)
                    c = conn.cursor()
                    c.execute("SELECT id, name FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1")
                    p = c.fetchone()
                    if not p:
                        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        c.execute("INSERT INTO periods (name, start_date, status) VALUES ('Kỳ tự động AI', ?, 'active')", (now_str,))
                        period_id = c.lastrowid
                        period_name = "Kỳ tự động AI"
                    else:
                        period_id = p[0]
                        period_name = p[1]

                    created_at = f"{date_str} {datetime.now().strftime('%H:%M:%S')}"
                    c.execute("INSERT INTO transactions (period_id, type, amount, note, created_at) VALUES (?, 'chi', ?, ?, ?)",
                              (period_id, amount, note.capitalize(), created_at))
                    conn.commit()

                    c.execute("SELECT SUM(CASE WHEN type='thu' THEN amount ELSE -amount END) FROM transactions WHERE period_id = ?", (period_id,))
                    balance = c.fetchone()[0] or 0
                    conn.close()

                    amount_k_str = f"{amount//1000:,}k" if amount >= 1000 else f"{amount:,}đ"
                    return {
                        "type": "success",
                        "module": "thuchi",
                        "message": (
                            f"✅ **ĐÃ XÁC NHẬN & GHI KHOẢN CHI THÀNH CÔNG!**\n\n"
                            f"• **Phân loại:** CHI\n"
                            f"• **Số tiền:** **{amount:,.0f} đ** ({amount_k_str})\n"
                            f"• **Nội dung:** {note.capitalize()}\n"
                            f"• **Ngày ghi nhận:** {date_str}\n"
                            f"• **Kỳ ghi nhận:** {period_name}\n"
                            f"• 💰 **Số dư quỹ kỳ này:** **{balance:,.0f} đ**\n\n"
                            f"👉 [Bấm vào đây để mở Sổ Thu Chi](/thuchi/)"
                        )
                    }
                except Exception as e:
                    return {"type": "error", "message": f"Lỗi lưu sổ chi: {str(e)}"}

            elif clean in ['khong', 'không', 'no', 'k']:
                del WIZARD_SESSIONS[session_id]
                return {
                    "type": "info",
                    "message": "🛑 **ĐÃ HỦY KHOẢN CHI!**\nKhông có dữ liệu nào được lưu vào Sổ Thu Chi."
                }
            else:
                amount = data['amount']
                return {
                    "type": "clarify",
                    "message": (
                        f"⚠️ Vui lòng xác nhận:\n"
                        f"• Gõ **'ok'** hoặc **'lưu'** để ghi khoản chi **{amount:,.0f} đ** vào sổ.\n"
                        f"• Gõ **'hủy'** để hủy bỏ phiên nhập này."
                    )
                }

    # ══════════════════════════════════════════
    # FLOW ASK LAMP PRICE: HỎI GIÁ SẢN PHẨM KHI CHƯA CÓ GIÁ TRONG HỆ THỐNG
    # ══════════════════════════════════════════
    elif flow == 'ask_lamp_price':
        p_num = 0
        try:
            import knowledge_base
            p_str, p_val = knowledge_base.parse_vietnamese_currency(user_text)
            if p_val > 0:
                p_num = p_val
        except Exception:
            pass
        if p_num <= 0:
            p_val = parse_vietnamese_money(user_text, default_thousands=True)
            if p_val > 0:
                p_num = p_val
        if p_num <= 0:
            return {
                "type": "clarify",
                "message": "⚠️ Em chưa nhận diện được số tiền. Vui lòng nhập mức giá (Ví dụ: `4500k`, `3tr5`, `3.500.000`... hoặc gõ `hủy`):"
            }
        price_k = int(p_num / 1000)
        raw_text = data.get('raw_text', '')
        del WIZARD_SESSIONS[session_id]
        augmented_text = f"{raw_text} {price_k}k"
        return handle_baocao_den(augmented_text, remove_accents(augmented_text).lower(), session_id=session_id)

    # FLOW 2: WIZARD DOANH THU ĐÈN
    # ══════════════════════════════════════════
    elif flow == 'den':
        # Bước 1: Tên đèn / Sản phẩm
        if step == 1:
            matched_name = ''
            matched_default = 3500
            for pat, cname, dprice in LAMP_CATALOG:
                if re.search(pat, user_text, re.IGNORECASE):
                    matched_name = cname
                    matched_default = dprice
                    break
            if not matched_name:
                matched_name = user_text.strip().upper()
                matched_name = re.sub(r'^(?:LẮP|LAP|GẮN|GAN|ĐÈN|DEN|BI)\s+', '', matched_name).strip()

            if not matched_name or len(matched_name) < 2:
                return {
                    "type": "clarify",
                    "message": "⚠️ Chưa nhận diện được tên đèn. Bạn lắp loại đèn nào? (Ví dụ: `F10 Turbo`, `S3`, `V20 Base`, `M40`... hoặc gõ `hủy`):"
                }

            data['product_name'] = matched_name
            data['default_price_k'] = matched_default
            session['step'] = 2
            return {
                "type": "clarify",
                "message": (
                    f"💡 Đèn: **{matched_name}**\n\n"
                    f"📅 **BƯỚC 2/7: THỜI GIAN / NGÀY LẮP**\n"
                    f"Ngày lắp đặt là ngày nào?\n"
                    f"*(Gõ **'0'** hoặc **'hôm nay'** để lấy ngày hiện tại, hoặc nhập VD: `20/10/2026`, `hôm qua`...)*"
                )
            }

        # Bước 2: Thời gian / Ngày lắp
        elif step == 2:
            if clean in ['0', 'hom nay', 'hôm nay', 'nay', '']:
                date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str, _ = extract_date(user_text)
            data['date'] = date_str
            session['step'] = 3
            return {
                "type": "clarify",
                "message": (
                    f"📅 Ngày lắp: **{date_str}**\n\n"
                    f"📦 **BƯỚC 3/7: SỐ LƯỢNG**\n"
                    f"Số lượng lắp mấy bộ / cặp?\n"
                    f"*(Gõ số lượng, VD: `1`, `2`, `3`... Bấm **'0'** hoặc **'1'** là 1 bộ)*"
                )
            }

        # Bước 3: Số lượng
        elif step == 3:
            m = re.search(r'\d+', user_text)
            qty = int(m.group(0)) if m else 1
            if qty <= 0: qty = 1
            data['quantity'] = qty
            session['step'] = 4
            sug_price_k = data['default_price_k'] * qty
            return {
                "type": "clarify",
                "message": (
                    f"📦 Số lượng: **{qty} bộ**\n\n"
                    f"💰 **BƯỚC 4/7: GIÁ BÁN / GIÁ GỐC**\n"
                    f"Giá bán là bao nhiêu?\n"
                    f"*(Giá niêm yết gợi ý: **{sug_price_k*1000:,.0f} đ ({sug_price_k:,}k)**. Gõ **'0'** để dùng giá niêm yết, hoặc nhập số tiền có chữ k như `3900k`, `6.5tr`...)*"
                )
            }

        # Bước 4: Giá bán / Giá gốc (Có chữ k tự hiểu nhân thêm 1000)
        elif step == 4:
            sug_price_k = data['default_price_k'] * data['quantity']
            if clean in ['0', '', 'niem yet', 'niêm yết']:
                base_price_k = sug_price_k
            else:
                p_val = parse_vietnamese_money(user_text, default_thousands=True)
                if p_val > 0:
                    base_price_k = int(round(p_val / 1000))
                else:
                    base_price_k = sug_price_k

            data['base_price_k'] = base_price_k
            session['step'] = 5
            return {
                "type": "clarify",
                "message": (
                    f"💰 Giá gốc: **{base_price_k*1000:,.0f} đ ({base_price_k:,}k)**\n\n"
                    f"🏷️ **BƯỚC 5/7: GIẢM GIÁ / CHIẾT KHẤU**\n"
                    f"Có giảm giá hoặc bớt cho khách không?\n"
                    f"*(Nếu **không giảm**, gõ **'0'** hoặc **'không'**. Nếu có giảm, nhập VD: `200k`, `500k`, `50k`, `1tr`...)*"
                )
            }

        # Bước 5: Giảm giá / Chiết khấu (Hỗ trợ cả phần trăm % và số tiền k / triệu)
        elif step == 5:
            base_k = data.get('base_price_k', 0)
            
            # 1. Nhận diện phần trăm: '10%', 'giảm 10%', '10 phan tram', '5%'
            m_pct = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:%|phan\s*tram|phần\s*trăm)', user_text, re.IGNORECASE)
            
            if m_pct:
                pct = float(m_pct.group(1).replace(',', '.'))
                discount_k = int(round(base_k * pct / 100))
                data['discount_pct'] = pct
            elif clean in ['0', 'không', 'khong', 'k', 'ko', '', 'ko giam', 'khong giam', 'khong bot', 'k giam']:
                discount_k = 0
                data['discount_pct'] = 0
            else:
                p_val = parse_vietnamese_money(user_text, default_thousands=True)
                if p_val > 0:
                    discount_k = int(round(p_val / 1000))
                else:
                    discount_k = 0
                data['discount_pct'] = 0

            data['discount_k'] = discount_k
            session['step'] = 6
            if discount_k > 0:
                pct_str = f" ({data['discount_pct']:.0f}%)" if data.get('discount_pct', 0) > 0 else ""
                disc_label = f"-{discount_k*1000:,.0f} đ (-{discount_k:,}k){pct_str}"
            else:
                disc_label = "0 đ (Không giảm)"

            return {
                "type": "clarify",
                "message": (
                    f"🏷️ Giảm giá: **{disc_label}**\n\n"
                    f"👤 **BƯỚC 6/7: TÊN KHÁCH HOẶC BIỂN SỐ XE**\n"
                    f"Tên khách hàng hoặc Biển số xe là gì?\n"
                    f"*(Ví dụ: `Anh Cường`, `Chị Lan`, `63A-123.45`, `Mua về`, `Xe đi xét`... Nếu không có gõ **'0'**)*"
                )
            }

        # Bước 6: Tên khách / Biển số xe
        elif step == 6:
            plate = extract_license_plate(user_text)
            if clean in ['0', '']:
                cust_name = plate if plate else 'KHÁCH LẺ'
            else:
                cust_name = user_text.strip().title()
                cust_name = re.sub(r'\bThay\b', 'Thầy', cust_name, flags=re.IGNORECASE)
                cust_name = re.sub(r'\bChi\b', 'Chị', cust_name, flags=re.IGNORECASE)
                cust_name = re.sub(r'\bChu\b', 'Chú', cust_name, flags=re.IGNORECASE)
                cust_name = re.sub(r'\bBac\b', 'Bác', cust_name, flags=re.IGNORECASE)

            data['customer_name'] = cust_name
            data['plate'] = plate
            session['step'] = 7
            return {
                "type": "clarify",
                "message": (
                    f"👤 Khách: **{cust_name}**" + (f" (Biển số: {plate})" if plate else "") + "\n\n"
                    f"🚗 **BƯỚC 7/7: LOẠI XE / DÒNG XE**\n"
                    f"Lắp cho xe gì?\n"
                    f"*(Ví dụ: `Camry`, `Accent`, `Vios`, `Innova`, `VF3`, `Solati`... Nếu không rõ gõ **'0'**)*"
                )
            }

        # Bước 7: Dòng xe ➔ CHUYỂN SANG BƯỚC XÁC NHẬN (CONFIRM)
        elif step == 7:
            if clean in ['0', '']:
                car_model = 'XE Ô TÔ'
            else:
                matched_car = ''
                for c in CAR_MODELS_LIST:
                    if re.search(r'\b' + c + r'\b', user_text, re.IGNORECASE):
                        matched_car = c
                        break
                car_model = matched_car if matched_car else user_text.strip().upper()

            data['car_model'] = car_model
            final_price_k = max(0, data['base_price_k'] - data['discount_k'])
            data['final_price_k'] = final_price_k
            session['step'] = 'confirm'

            qty_label = f"{data['quantity']} bộ " if data['quantity'] > 1 else ""
            base_str = f"{data['base_price_k']*1000:,.0f} đ ({data['base_price_k']:,}k)"
            final_str = f"{final_price_k*1000:,.0f} đ ({final_price_k:,}k)"
            pct_str = f" ({data['discount_pct']:.0f}%)" if data.get('discount_pct', 0) > 0 else ""
            disc_text = f"\n• 🏷️ **Giảm giá:** -{data['discount_k']*1000:,.0f} đ (-{data['discount_k']:,}k){pct_str}" if data['discount_k'] > 0 else "\n• 🏷️ **Giảm giá:** 0 đ (Không giảm)"
            plate_text = f" (Biển số: {data['plate']})" if data['plate'] else ""

            return {
                "type": "clarify",
                "message": (
                    f"📋 **XÁC NHẬN ĐƠN BÁO CÁO DOANH THU ĐÈN**\n"
                    f"───────────────────────────\n"
                    f"• 💡 **Sản phẩm:** **{qty_label}{data['product_name']}**\n"
                    f"• 👤 **Khách hàng:** **{data['customer_name']}**{plate_text}\n"
                    f"• 🚗 **Dòng xe:** **{data['car_model']}**\n"
                    f"• 📅 **Ngày lắp:** **{data['date']}**\n"
                    f"• 💵 **Giá gốc:** {base_str}{disc_text}\n"
                    f"• 💰 **DOANH THU THỰC THU:** **{final_str}**\n"
                    f"───────────────────────────\n"
                    f"❓ **Bạn có xác nhận thêm đơn này vào Báo Cáo Doanh Thu Đèn không?**\n\n"
                    f"👉 Gõ **'ok'**, **'lưu'**, **'có'** hoặc **'xác nhận'** để thêm vào báo cáo.\n"
                    f"👉 Gõ **'hủy'** hoặc **'không'** để hủy bỏ."
                )
            }

        # Bước Xác Nhận Đơn Đèn ➔ LƯU DATABASE HOẶC HỦY
        elif step == 'confirm':
            is_confirm = clean in [
                'ok', 'okie', 'oke', 'yes', 'y', 'co', 'có', 'luu', 'lưu',
                'xac nhan', 'xác nhận', 'dong y', 'đồng ý', 'them', 'thêm', 'duoc', 'được', '1'
            ] or clean.startswith('ok')

            if is_confirm:
                final_price_k = data['final_price_k']
                del WIZARD_SESSIONS[session_id]

                if not os.path.exists(DB_DEN):
                    return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

                try:
                    conn = sqlite3.connect(DB_DEN, timeout=10)
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                        VALUES (?, ?, ?, ?, ?, ?, 'AI_ASSISTANT')
                    """, (data['date'], data['product_name'], data['customer_name'], data['car_model'], data['quantity'], final_price_k))
                    order_id = c.lastrowid
                    conn.commit()
                    conn.close()

                    qty_label = f"{data['quantity']} bộ " if data['quantity'] > 1 else ""
                    base_str = f"{data['base_price_k']*1000:,.0f} đ ({data['base_price_k']:,}k)"
                    final_str = f"{final_price_k*1000:,.0f} đ ({final_price_k:,}k)"
                    disc_text = f"\n• **Giảm giá:** -{data['discount_k']*1000:,.0f} đ (-{data['discount_k']:,}k)" if data['discount_k'] > 0 else ""

                    return {
                        "type": "success",
                        "module": "den",
                        "message": (
                            f"✅ **ĐÃ XÁC NHẬN & GHI NHẬN ĐƠN ĐÈN THÀNH CÔNG!**\n\n"
                            f"• **Mã đơn:** #{order_id}\n"
                            f"• **Sản phẩm:** **{qty_label}{data['product_name']}**\n"
                            f"• **Khách hàng:** **{data['customer_name']}**\n"
                            f"• **Dòng xe:** {data['car_model']}\n"
                            + (f"• **Biển số:** {data['plate']}\n" if data['plate'] else "")
                            + f"• **Ngày ghi nhận:** {data['date']}\n"
                            + f"• **Giá gốc:** {base_str}\n"
                            + disc_text
                            + f"\n• 💰 **DOANH THU THỰC THU:** **{final_str}**\n\n"
                            f"👉 [Bấm vào đây để xem Báo Cáo Doanh Thu Đèn](/den/)\n"
                            f"*(Nếu nhập nhầm, gõ 'hủy đơn vừa nhập' để hoàn tác ngay)*"
                        )
                    }
                except Exception as e:
                    return {"type": "error", "message": f"Lỗi lưu báo cáo đèn: {str(e)}"}

            elif clean in ['khong', 'không', 'no']:
                del WIZARD_SESSIONS[session_id]
                return {
                    "type": "info",
                    "message": "🛑 **ĐÃ HỦY ĐƠN ĐÈN!**\nKhông có dữ liệu nào được lưu vào hệ thống."
                }
            else:
                final_str = f"{data['final_price_k']*1000:,.0f} đ ({data['final_price_k']:,}k)"
                return {
                    "type": "clarify",
                    "message": (
                        f"⚠️ Vui lòng xác nhận:\n"
                        f"• Gõ **'ok'** hoặc **'lưu'** để thêm đơn đèn **{data['product_name']}** ({final_str}) vào hệ thống.\n"
                        f"• Gõ **'hủy'** để hủy bỏ phiên nhập này."
                    )
                }

    # ══════════════════════════════════════════
    # FLOW 3: WIZARD LÀM RÕ Ý ĐỊNH (CLARIFICATION DIALOGUE)
    # ══════════════════════════════════════════
    elif flow == 'clarify':
        del WIZARD_SESSIONS[session_id]
        candidates = data.get('candidates', {})

        # Nếu chọn số 1-9
        if clean in ['1', 'so 1', 'goi 1']:
            return process_ai_command(candidates.get('1', 'tu van film'), session_id)
        elif clean in ['2', 'so 2', 'goi 2']:
            return process_ai_command(candidates.get('2', 'boc ghe da'), session_id)
        elif clean in ['3', 'so 3', 'goi 3']:
            return process_ai_command(candidates.get('3', 'boc tran oto'), session_id)
        elif clean in ['4', 'so 4', 'goi 4']:
            return process_ai_command(candidates.get('4', 'man hinh android'), session_id)
        elif clean in ['5', 'so 5', 'goi 5']:
            return process_ai_command(candidates.get('5', 'cam hanh trinh'), session_id)
        elif clean in ['6', 'so 6', 'goi 6']:
            return process_ai_command(candidates.get('6', 'android box'), session_id)
        elif clean in ['7', 'so 7', 'goi 7']:
            return process_ai_command(candidates.get('7', 'tu van ppf'), session_id)
        elif clean in ['8', 'so 8', 'goi 8']:
            return process_ai_command('doanh thu den', session_id)
        elif clean in ['9', 'so 9', 'goi 9']:
            return process_ai_command('chi', session_id)

        # Nếu đồng ý gợi ý ("đúng rồi", "ừ", "phải", "ok", "yes")
        elif clean in ['dung', 'dung roi', 'u', 'uh', 'phai', 'chuan', 'ok', 'yes', 'y', 'chinh xac']:
            hint_action = data.get('hint_action')
            if hint_action:
                return process_ai_command(hint_action, session_id)
            return process_ai_command('tu van film', session_id)

        # Nếu người dùng trả lời bằng câu hỏi / thông tin mới
        else:
            return process_ai_command(user_text, session_id)
    return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. NHẬP BÁO CÁO DOANH THU ĐÈN TỐI ƯU SIÊU TỐC (ONE-SHOT)
# ─────────────────────────────────────────────────────────────────────────────

def handle_baocao_den(raw_text, clean_text, session_id='default_user'):
    """
    Xử lý lệnh ghi đơn báo cáo doanh thu đèn tối ưu tuyệt đối (One-shot command):
    - Bóc tách theo bất kỳ trật tự câu chữ nào: [Khách] [Xe] [Đèn] [Giá] hoặc [Đèn] [Xe] [Khách]
    - Tự động tra cứu giá niêm yết nếu người dùng quên gõ giá
    - Tự động nhận diện số lượng: '2 bộ s3', '2 cái f10'
    - Hỗ trợ các khách hàng đặc biệt: 'mua về', 'xe đi xét', 'thầy đức', 'chú ba'
    - Hỗ trợ combo nhiều món & tự động phân bổ chiết khấu / giảm giá
    """
    is_den = bool(re.search(r'\b(den|bi|bi gam|bi led|bi pha|f10|naoevo|s3|s6|s8|s9|turbo|hyper|v20|m30|m40|titan|bong|pha|gam|m10|m20|f150|cb150)\b', clean_text))
    if not is_den:
        return None

    is_pure_query = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean_text)) and \
                    not bool(re.search(r'\b(lap|gan|do|thay|ban|don|nhap)\b', clean_text))
    if is_pure_query:
        return None

    # GUARDRAIL BẢO VỆ: Chỉ ghi nhận đơn khi có dấu hiệu lên đơn rõ ràng (hành động, khách, xe, biển số hoặc giá tiền độc lập)
    has_action = bool(re.search(r'\b(lap|gan|thay|do|ban|len don|nhap don|ghi don|don den|nhap)\b', clean_text))
    has_special = bool(re.search(r'\b(mua ve|xe di xet|giao tho|xe bai)\b', clean_text))
    has_plate = bool(re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5})\b', raw_text.upper()))
    has_customer = bool(re.search(r'\b(anh|chi|chu|bac|em|thay|co|khach|chu xe)\s+[a-zA-ZÀ-ỹ]+', raw_text, re.IGNORECASE))
    has_explicit_price = bool(re.search(r'\s+(\d{3,5})\b', clean_text)) or bool(re.search(r'\b\d+(?:[.,]\d+)?\s*(?:k|tr|trieu|triệu|nghin|ngàn)\b', clean_text))

    is_order_intent = has_action or has_special or has_plate or has_customer or (has_explicit_price and len(clean_text.split()) >= 3)
    if not is_order_intent:
        return None

    text = raw_text.strip()

    # 1. Biển số xe
    m_plate = re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5}(?:\.[0-9]{1,2})?)\b', text.upper())
    plate = m_plate.group(1).strip() if m_plate else ''
    if plate:
        text = text.replace(m_plate.group(0), ' ')

    # 1.1 Số điện thoại (bóc tách và xóa khỏi text để không bị hiểu nhầm thành giá tiền)
    phone = extract_phone(text)
    if phone:
        text = text.replace(phone, ' ')

    # 1.2 Bỏ các tiền tố lệnh như "nhập đơn", "lên đơn", "ghi đơn", "đơn đèn" khỏi text
    text = re.sub(r'\b(?:nhập\s*đơn|nhap\s*don|lên\s*đơn|len\s*don|ghi\s*đơn|ghi\s*don|đơn\s*đèn|don\s*den)\b', ' ', text, flags=re.IGNORECASE)

    # 2. Ngày ghi nhận
    order_date, text = extract_date(text)

    # 3. Dòng xe
    found_car = ''
    for c in CAR_MODELS_LIST:
        m_c = re.search(r'(?:cho\s+xe\s+|xe\s+)?\b' + re.escape(c) + r'\b', text, re.IGNORECASE)
        if m_c:
            found_car = c
            text = text[:m_c.start()] + ' ' + text[m_c.end():]
            break

    # 4. Giảm giá
    discount_k = 0
    m_disc = re.search(r'(?:giảm\s*giá|giam\s*gia|giảm|giam|bớt|bot|chiết\s*khấu|chiet\s*khau)\s*([0-9.,]+(?:\s*(?:tr|trieu|triệu|k|%))?)', text, re.IGNORECASE)
    disc_is_pct = False
    disc_pct_val = 0
    if m_disc:
        disc_val_str = m_disc.group(1).strip()
        val_clean = disc_val_str.replace(',', '.')
        m_num = re.search(r'(\d+(?:\.\d+)?)', val_clean)
        if m_num:
            val = float(m_num.group(1))
            if '%' in disc_val_str:
                disc_is_pct = True
                disc_pct_val = val
            elif 'tr' in disc_val_str or 'trieu' in disc_val_str:
                discount_k = int(val * 1000)
            elif val >= 100000:
                discount_k = int(val / 1000)
            else:
                discount_k = int(val)
        text = text[:m_disc.start()] + ' ' + text[m_disc.end():]

    # 5. Khách hàng đặc biệt
    cust_special = ''
    special_custs = [('MUA VỀ', r'\b(?:mua\s+ve|mua\s+về)\b'),
                     ('XE ĐI XÉT', r'\b(?:xe\s+di\s+xet|xe\s+đi\s+xét)\b'),
                     ('GIAO THỢ', r'\b(?:giao\s+tho|giao\s+thợ)\b'),
                     ('XE BÃI', r'\b(?:xe\s+bai|xe\s+bãi)\b')]
    for ctag, cpat in special_custs:
        m_sc = re.search(cpat, text, re.IGNORECASE)
        if m_sc:
            cust_special = ctag
            text = text[:m_sc.start()] + ' ' + text[m_sc.end():]
            break

    # 6. Tách từng món đèn trong câu
    text = re.sub(r'(?<=\d)\s+(?=(?:đèn|den|bi|bóng|bong|pha|gầm|gam|v20|f10|s3|s6|s8|s9|m30|m40|titan))', ', ', text, flags=re.IGNORECASE)
    chunks = [ch.strip() for ch in re.split(r'[,;\n]|\b(?:và|cong|\+)\b', text) if ch.strip()]

    items = []
    cust_candidates = []

    for chunk in chunks:
        c = re.sub(r'^(?:lắp|lap|gắn|gan|thay|bán|ban|độ|do|cho|nhập|nhap|lên|len|ghi)\s+', '', chunk, flags=re.IGNORECASE).strip()
        if not c:
            continue

        qty = 1
        m_qty = re.search(r'\b(\d+)\s*(?:bộ|bo|cặp|cap|cái|cai|hộp|hop)\b', c, re.IGNORECASE)
        if m_qty:
            qty = int(m_qty.group(1))
            c = c[:m_qty.start()] + ' ' + c[m_qty.end():]

        # 1. BƯỚC 1: NHẬN DIỆN TÊN ĐÈN TRƯỚC HẾT TRONG LAMP_CATALOG (Tránh nhầm số version 2.0, 3.0 thành giá tiền)
        matched_name = ''
        matched_default = 0
        leftover = c

        # Sắp xếp theo độ dài tên chuẩn hóa giảm dần để match F10 NEW 2.0 trước F10
        sorted_catalog = sorted(LAMP_CATALOG, key=lambda x: len(x[1]), reverse=True)
        for pat, cname, _ in sorted_catalog:
            m_l = re.search(pat, c, re.IGNORECASE)
            if m_l:
                matched_name = cname
                # Tách cụm tên đèn ra, phần còn lại mới tìm giá tiền & tên khách
                leftover = c[:m_l.start()] + ' ' + c[m_l.end():]
                break

        # 2. BƯỚC 2: TÌM GIÁ TIỀN TRONG PHẦN CÒN LẠI (Hoặc toàn bộ c nếu chưa khớp tên đèn catalog)
        target_for_price = (leftover if matched_name else c).strip()
        price_k = 0
        is_default_price = False

        m_p = re.search(r'(?:giá|gia)?\s*(\d+(?:[.,]\d+)?)\s*(tr|trieu|triệu|k|nghin|ngàn)?(?:\s*đ|\s*vnd)?$', target_for_price, re.IGNORECASE)
        if m_p:
            num_str = m_p.group(1).replace(',', '.')
            unit = (m_p.group(2) or '').lower()
            val = float(num_str)
            has_kw = bool(re.search(r'\b(giá|gia)\b', m_p.group(0), re.IGNORECASE))
            has_unit = bool(unit)

            # BẢO VỆ TUYỆT ĐỐI:
            # Nếu KHÔNG CÓ đơn vị (unit) và KHÔNG CÓ từ "giá":
            # - Không nhận số thập phân nhỏ (như 2.0, 3.0, 1.5...) làm tiền triệu!
            # - Chỉ nhận số nguyên >= 50 (như 350, 1500, 3900, 4500)
            is_valid_price = False
            if has_unit or has_kw:
                is_valid_price = True
            elif '.' in num_str or ',' in num_str:
                if val >= 100000:
                    is_valid_price = True
            elif val >= 50:
                is_valid_price = True

            if is_valid_price and val < 10000000:
                if unit in ['tr', 'trieu', 'triệu']:
                    price_k = int(val * 1000)
                elif unit in ['k', 'nghin', 'ngàn']:
                    price_k = int(val)
                elif val >= 100000:
                    price_k = int(val / 1000)
                elif val >= 100:
                    price_k = int(val)
                elif has_kw and val > 0 and val < 50:
                    price_k = int(val * 1000)
                else:
                    price_k = int(val)
                # Xóa phần giá tiền khỏi target_for_price
                target_for_price = target_for_price[:m_p.start()] + ' ' + target_for_price[m_p.end():]

        # 3. BƯỚC 3: TÁCH TÊN KHÁCH HOẶC TÊN ĐÈN NẾU CHƯA MATCH CATALOG
        clean_left = re.sub(r'\b(lắp|lap|gắn|gan|thay|độ|do|bán|ban|cho|đèn|den|bi|gầm|gam|pha|xe|nhập|nhap|đơn|don|lên|len|ghi|giá|gia)\b', ' ', target_for_price, flags=re.IGNORECASE)
        clean_left = ' '.join(clean_left.split()).strip()

        if not matched_name:
            matched_name = clean_left.upper() if clean_left else c.upper()
        else:
            if clean_left and len(clean_left) >= 2:
                clean_norm = remove_accents(clean_left).lower()
                is_num_or_money = bool(re.match(r'^\d+(?:[.,]\d+)?\s*(?:k|tr|trieu|triệu|d|đ|vnd)?$', clean_norm))
                if not is_num_or_money and clean_norm not in {'nhap don', 'nhap', 'don', 'len don', 'ghi don', 'don den', 'gia', 'xe', 'lap', 'gan'}:
                    cust_candidates.append(clean_left)

        # 4. BƯỚC 4: TRA CỨU GIÁ TRONG HỆ THỐNG GARA (TRI THỨC HOẶC KHO HÀNG)
        mem_price = get_lamp_price_from_memory(matched_name or c)
        if mem_price > 0:
            matched_default = mem_price

        if price_k == 0:
            if matched_default > 0:
                price_k = matched_default * qty
                is_default_price = True
            else:
                # SẢN PHẨM CHƯA CÓ GIÁ TRONG HỆ THỐNG GARA:
                # TUYỆT ĐỐI KHÔNG TỰ TIỆN CHO GIÁ MẶC ĐỊNH! HỎI NGƯỜI DÙNG GIÁ THỰC TẾ!
                WIZARD_SESSIONS[session_id] = {
                    'flow': 'ask_lamp_price',
                    'step': 1,
                    'data': {
                        'matched_name': matched_name,
                        'qty': qty,
                        'cust_special': cust_special,
                        'cust_candidates': cust_candidates,
                        'plate': plate,
                        'found_car': found_car,
                        'discount_k': discount_k,
                        'disc_is_pct': disc_is_pct,
                        'disc_pct_val': disc_pct_val,
                        'order_date': order_date,
                        'raw_text': raw_text
                    }
                }
                return {
                    "type": "clarify",
                    "message": (
                        f"⚠️ Sản phẩm **{matched_name}** chưa có giá trong hệ thống gara.\n"
                        f"─────────────────────────────────────────\n"
                        f"Anh/chị lắp loại đèn này cho khách với giá bao nhiêu ạ?\n"
                        f"*(Ví dụ: `4500k`, `3tr5`, `3.500.000`... hoặc gõ `hủy` để thoát)*"
                    )
                }

        items.append({
            'product_name': matched_name,
            'quantity': qty,
            'base_price_k': price_k,
            'is_default': is_default_price
        })

    if not items:
        return None

    cust_name = cust_special
    if not cust_name and cust_candidates:
        cust_name = cust_candidates[0].strip().title()

    # Tự động tra cứu thông tin khách hàng và dòng xe từ Biển số hoặc Số điện thoại
    auto_detected_cust = False
    phone = extract_phone(raw_text)
    if plate or phone:
        lookup_res = lookup_customer_and_car_by_identifier(plate or phone)
        if lookup_res.get('found'):
            if not cust_name or cust_name in ['KHÁCH LẺ', plate]:
                c_found = lookup_res.get('customer_name')
                if c_found:
                    cust_name = c_found
                    auto_detected_cust = True
            if not found_car:
                found_car = lookup_res.get('car_model') or ''
            if not phone and lookup_res.get('phone'):
                phone = lookup_res['phone']

    total_base_k = sum(it['base_price_k'] for it in items)
    if disc_is_pct:
        discount_k = int(round(total_base_k * (disc_pct_val / 100)))

    allocated = 0
    for i, it in enumerate(items):
        if i == len(items) - 1:
            disc = discount_k - allocated
        else:
            disc = round(discount_k * (it['base_price_k'] / total_base_k)) if total_base_k > 0 else 0
            allocated += disc
        it['discount_k'] = disc
        it['final_price_k'] = max(0, it['base_price_k'] - disc)

    total_final_k = sum(it['final_price_k'] for it in items)

    # Nếu không tìm thấy tên từ số xe (hoặc số điện thoại) và người dùng chưa cung cấp tên khách:
    if not cust_name and (plate or phone) and not cust_special:
        id_label = f"Biển số `{plate}`" if plate else f"SĐT `{phone}`"
        matched_item_names = ", ".join(f"**{it['product_name']}**" for it in items)
        clarify_msg = (
            f"🔍 **CHƯA CÓ THÔNG TIN KHÁCH HÀNG:**\n"
            f"───────────────────────────────────────\n"
            f"• 🚘 {id_label} chưa có hồ sơ trong gara (khách mới đến lần đầu).\n"
            f"• 📦 Đèn lắp: {matched_item_names}\n"
            f"• 💰 Doanh thu: **{total_final_k*1000:,.0f} đ** ({total_final_k:,}k)\n"
            f"───────────────────────────────────────\n"
            f"👉 Anh/chị vui lòng cho em xin **Tên khách hàng** và **Dòng xe** để em điền vào đơn nhé!\n"
            f"*(Ví dụ gõ: `Anh Tuấn Vios` hoặc `Chị Mai Accent` | Gõ `hủy` để bỏ qua)*"
        )
        WIZARD_SESSIONS[session_id] = {
            'flow': 'lamp_fill_missing',
            'action_type': 'baocao_den',
            'pending_payload': {
                'items': items,
                'plate': plate,
                'phone': phone,
                'order_date': order_date,
                'discount_k': discount_k,
                'disc_is_pct': disc_is_pct,
                'disc_pct_val': disc_pct_val,
                'found_car': found_car,
                'total_base_k': total_base_k,
                'total_final_k': total_final_k
            }
        }
        return {
            "type": "clarify",
            "message": clarify_msg
        }

    if not cust_name:
        cust_name = plate if plate else (found_car if found_car else 'KHÁCH LẺ')

    cust_name = re.sub(r'\bThay\b', 'Thầy', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChi\b', 'Chị', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChu\b', 'Chú', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bBac\b', 'Bác', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bEm\b', 'Em', cust_name, flags=re.IGNORECASE)

    item_lines = []
    for i, it in enumerate(items, 1):
        qty_label = f"{it['quantity']} bộ " if it['quantity'] > 1 else ""
        default_tag = " *(Giá niêm yết tự động)*" if it.get('is_default') else ""
        base_str = f"{it['base_price_k']*1000:,.0f} đ ({it['base_price_k']:,}k){default_tag}"
        if it['discount_k'] > 0:
            final_str = f"{it['final_price_k']*1000:,.0f} đ ({it['final_price_k']:,}k)"
            item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: {base_str} ➔ Sau giảm: **{final_str}**")
        else:
            item_lines.append(f"  {i}. **{qty_label}{it['product_name']}**: **{base_str}**")

    items_text = "\n".join(item_lines)
    total_final_str = f"{total_final_k*1000:,.0f} đ ({total_final_k:,}k)"

    cust_tag = " *(Hồ sơ tự nhận diện)*" if auto_detected_cust else ""
    confirm_msg = (
        f"❓ **XÁC NHẬN TẠO ĐƠN VÀO SỔ BÁO CÁO DOANH THU ĐÈN:**\n"
        f"───────────────────────────────────────\n"
        f"• 👤 **Khách hàng:** **{cust_name}**{cust_tag}\n"
        f"• 🚗 **Dòng xe:** **{found_car or 'Chưa rõ dòng xe'}**\n"
        + (f"• 🚘 **Biển số:** **{plate}**\n" if plate else "")
        + (f"• 📞 **Số điện thoại:** **{phone}**\n" if phone else "")
        + f"• 📦 **Sản phẩm lắp đặt:**\n{items_text}\n"
        + f"• 💰 **DOANH THU THỰC THU:** **{total_final_str}**\n"
        + f"• 📅 **Ngày lắp:** **{order_date}** *(Hôm nay theo đồng hồ hệ thống)*\n"
        f"───────────────────────────────────────\n"
        f"👉 Anh có chắc chắn muốn **LƯU ĐƠN HÀNG NÀY** vào hệ thống không?\n\n"
        f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào Báo Cáo Đèn | Nhắn **'hủy'** để bỏ qua)*"
    )

    WIZARD_SESSIONS[session_id] = {
        'flow': 'confirm_action',
        'action_type': 'baocao_den',
        'payload': {
            'items': items,
            'cust_name': cust_name,
            'found_car': found_car,
            'plate': plate,
            'phone': phone,
            'order_date': order_date,
            'discount_k': discount_k,
            'total_base_k': total_base_k,
            'total_final_k': total_final_k
        }
    }
    return {
        "type": "clarify",
        "message": confirm_msg
    }

# ─────────────────────────────────────────────────────────────────────────────
# 2. XÓA / HOÀN NGUYÊN ĐƠN ĐÈN VỪA NHẬP NHẦM
# ─────────────────────────────────────────────────────────────────────────────

def handle_undo_last_lamp_order(raw_text, clean_text):
    """Hủy nhanh đơn đèn vừa nhập bởi AI nếu người dùng gõ nhầm"""
    is_undo = bool(re.search(r'\b(xoa don|huy don|xoa don vua nhap|huy don vua nhap|xoa vua roi|huy vua roi|undo)\b', clean_text))
    if not is_undo:
        return None

    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("""
            SELECT id, order_date, product_name, customer_name, car_model, quantity, price_k
            FROM orders
            WHERE sheet_origin = 'AI_ASSISTANT'
            ORDER BY id DESC LIMIT 3
        """)
        recent_rows = c.fetchall()

        if not recent_rows:
            conn.close()
            return {"type": "info", "message": "🔎 Hiện không tìm thấy đơn đèn nào do Trợ Lý AI vừa tạo để xóa."}

        last_id = recent_rows[0]['id']
        c.execute("DELETE FROM orders WHERE id = ?", (last_id,))
        conn.commit()
        conn.close()

        r = recent_rows[0]
        return {
            "type": "success",
            "module": "den",
            "message": (
                f"🗑️ **ĐÃ HỦY THÀNH CÔNG ĐƠN ĐÈN VỪA NHẬP!**\n\n"
                f"• **Mã đơn đã xóa:** #{r['id']}\n"
                f"• **Khách hàng:** {r['customer_name']}\n"
                f"• **Dòng xe:** {r['car_model']}\n"
                f"• **Sản phẩm:** {r['quantity']}x {r['product_name']}\n"
                f"• **Doanh thu đã giảm:** -{r['price_k']*1000:,.0f} đ (-{r['price_k']:,}k)\n\n"
                f"👉 [Kiểm tra lại Danh Sách Báo Cáo Đèn](/den/)"
            )
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi xóa đơn đèn: {str(e)}"}

# ─────────────────────────────────────────────────────────────────────────────
# 3. TRA CỨU THỐNG KÊ DOANH SỐ ĐÈN TỰ NHIÊN
# ─────────────────────────────────────────────────────────────────────────────

def get_available_years_for_cycle_month(month):
    """Lấy danh sách các năm có phát sinh đơn hàng trong chu kỳ tháng này"""
    if not os.path.exists(DB_DEN):
        return []
    try:
        conn = sqlite3.connect(DB_DEN, timeout=5)
        c = conn.cursor()
        available_years = []
        for y in [2026, 2025, 2024, 2023, 2022]:
            s, e = get_cycle_dates(y, month)
            c.execute("SELECT 1 FROM orders WHERE order_date >= ? AND order_date <= ? LIMIT 1", (s, e))
            if c.fetchone():
                available_years.append(y)
        conn.close()
        return available_years
    except:
        return []

def generate_baocao_den_cycle_report(year, month):
    """Xuất báo cáo doanh thu đèn chi tiết theo kỳ tháng/năm chu kỳ 9-8"""
    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        s, e = get_cycle_dates(year, month)

        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(price_k), 0)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (s, e))
        row = c.fetchone()
        orders_cnt = row[0] or 0
        total_qty = row[1] or 0
        total_k = row[2] or 0

        c.execute("""
            SELECT COUNT(DISTINCT customer_name || '_' || car_model)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (s, e))
        car_cnt = c.fetchone()[0] or 0

        c.execute("""
            SELECT product_name, SUM(quantity), SUM(price_k)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
            GROUP BY product_name
            ORDER BY SUM(quantity) DESC, SUM(price_k) DESC LIMIT 5
        """, (s, e))
        top_prods = c.fetchall()
        conn.close()

        s_d, s_m = s.split('-')[2], s.split('-')[1]
        e_d, e_m = e.split('-')[2], e.split('-')[1]

        msg = (
            f"💡 **BÁO CÁO DOANH THU ĐÈN — KỲ THÁNG {month:02d}/{year}**\n"
            f"*(Tính từ ngày {s_d}/{s_m} đến {e_d}/{e_m})*\n\n"
            f"• 💰 **Tổng doanh thu:** **{total_k*1000:,.0f} đ** ({total_k:,}k)\n"
            f"• 📦 **Tổng số bộ đèn đã lắp:** **{total_qty} bộ** ({orders_cnt} dòng đơn)\n"
            f"• 🚗 **Số lượt xe phục vụ:** **{car_cnt} xe**\n\n"
        )
        if top_prods:
            msg += f"🔥 **TOP ĐÈN BÁN CHẠY NHẤT KỲ {month:02d}/{year}:**\n"
            for i, p in enumerate(top_prods, 1):
                p_name = p[0]
                p_qty = p[1]
                p_money = (p[2] or 0) * 1000
                msg += f"  {i}. **{p_name}**: {p_qty} bộ — **{p_money:,.0f} đ**\n"
        else:
            msg += "• *(Chưa có dữ liệu đơn hàng trong kỳ này)*\n"

        msg += f"\n👉 [Mở Báo Cáo Đèn kỳ {month:02d}/{year} trên trình duyệt](/den/?month={month}&year={year})"
        return {"type": "success", "module": "den", "message": msg}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi xuất báo cáo đèn: {str(e)}"}

def generate_baocao_den_year_report(year):
    """Xuất báo cáo tổng kết doanh thu đèn cả năm"""
    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}
    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(price_k), 0)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        orders_cnt, total_qty, total_k = c.fetchone()

        c.execute("""
            SELECT COUNT(DISTINCT customer_name || '_' || car_model)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        car_cnt = c.fetchone()[0] or 0

        c.execute("""
            SELECT product_name, SUM(quantity), SUM(price_k)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
            GROUP BY product_name
            ORDER BY SUM(quantity) DESC, SUM(price_k) DESC LIMIT 5
        """, (start_date, end_date))
        top_prods = c.fetchall()
        conn.close()

        if orders_cnt == 0:
            return {
                "type": "info",
                "message": f"📊 Chưa tìm thấy dữ liệu doanh thu đèn trong năm **{year}**."
            }

        reply = (
            f"💡 **TỔNG KẾT DOANH THU ĐÈN NĂM {year}**\n"
            f"*(Cả năm {year} từ 01/01/{year} đến 31/12/{year})*\n\n"
            f"• 💰 **Tổng doanh thu cả năm:** **{total_k*1000:,.0f} đ** ({total_k:,}k)\n"
            f"• 📦 **Tổng số bộ đèn đã lắp:** **{total_qty} bộ** ({orders_cnt} lượt đơn)\n"
            f"• 🚗 **Số lượt xe nâng cấp đèn:** **{car_cnt} xe**\n\n"
        )

        if top_prods:
            reply += f"🔥 **TOP 5 DÒNG ĐÈN BÁN CHẠY NHẤT NĂM {year}:**\n"
            for i, p in enumerate(top_prods, 1):
                p_name = p[0]
                p_qty = p[1]
                p_money = (p[2] or 0) * 1000
                reply += f"  {i}. **{p_name}**: {p_qty} bộ — **{p_money:,.0f} đ**\n"
            reply += "\n"

        reply += f"👉 [Mở Báo Cáo Đèn chi tiết trên hệ thống](/den/)"
        return {"type": "success", "module": "den", "message": reply}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi tổng kết năm: {str(e)}"}

def generate_baocao_den_today_report():
    """Báo cáo danh sách đơn đèn lắp đặt trong ngày hôm nay"""
    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}
    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')
        c.execute("""
            SELECT id, product_name, customer_name, car_model, quantity, price_k
            FROM orders
            WHERE order_date = ?
            ORDER BY id DESC
        """, (today_str,))
        today_rows = c.fetchall()
        conn.close()

        msg = f"🕒 **DANH SÁCH ĐƠN ĐÈN LẮP HÔM NAY ({datetime.now().strftime('%d/%m/%Y')}):**\n\n"
        if today_rows:
            tot = sum(r[5] for r in today_rows) * 1000
            msg += f"• Tổng số đơn: **{len(today_rows)} đơn**\n"
            msg += f"• Doanh thu hôm nay: **{tot:,.0f} đ**\n\n"
            for r in today_rows:
                msg += f"  • #{r[0]}: **{r[4]}x {r[1]}** — Xe: {r[3]} ({r[2]}) ➔ **{r[5]*1000:,.0f} đ**\n"
        else:
            msg += "• Chưa có đơn đèn nào được ghi nhận trong hôm nay.\n"
        msg += "\n👉 [Mở Báo Cáo Đèn](/den/)"
        return {"type": "success", "module": "den", "message": msg}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi lấy đơn hôm nay: {str(e)}"}

def handle_baocao_den_stats(raw_text, clean_text, session_id="default_user"):
    """Báo cáo thống kê chuyên sâu về doanh thu đèn chu kỳ 9-8 (hỗ trợ hỏi lại năm nếu thiếu thông tin)"""
    is_stat = bool(re.search(r'\b(doanh thu den|doanh so den|bao cao den|ban duoc bao nhieu den|may xe den|don den hom nay|top den|den ban chay)\b', clean_text)) or \
              (any(k in clean_text for k in ['doanh thu', 'doanh so', 'bao cao']) and any(k in clean_text for k in ['den', 'bi', 'gam', 'pha', 'bong']))
    if not is_stat:
        return None

    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    month, year = parse_month_year(clean_text)

    # 1. Nếu hỏi hôm nay
    if month == 'today' or 'hom nay' in clean_text:
        return generate_baocao_den_today_report()

    # 2. Nếu người dùng chỉ nói tháng (ví dụ: 'tháng 7', 'tổng doanh thu đèn tháng 7') mà THIẾU THÔNG TIN NĂM
    if isinstance(month, int) and year is None:
        avail_years = get_available_years_for_cycle_month(month)
        if avail_years:
            WIZARD_SESSIONS[session_id] = {'flow': 'ask_year_den', 'month': month, 'step': 1, 'data': {}}
            buttons_hint = "\n".join([f"• `Tháng {month}/{y}` *(hoặc gõ `{y}`)*" for y in avail_years])
            return {
                "type": "clarify",
                "message": (
                    f"💡 Bạn muốn xem báo cáo doanh thu đèn **tháng {month} của năm nào** ạ?\n"
                    f"─────────────────────────────────────────\n"
                    f"Hệ thống Báo Cáo Đèn ghi nhận dữ liệu tháng {month} các năm: **{', '.join(str(y) for y in avail_years)}**.\n\n"
                    f"👉 *Bạn vui lòng chọn hoặc gõ năm cần xem:*\n{buttons_hint}"
                )
            }
        else:
            return {
                "type": "info",
                "message": f"📊 Chưa tìm thấy dữ liệu doanh thu đèn cho **Tháng {month}** trong hệ thống."
            }

    # 3. Nếu người dùng chỉ định cả tháng và năm (ví dụ: 'tháng 7 năm 2026', 'tháng 7/2025', 't7-2024')
    if isinstance(month, int) and isinstance(year, int):
        return generate_baocao_den_cycle_report(year, month)

    # 4. Nếu người dùng chỉ định cả năm (ví dụ: 'năm 2025', 'doanh thu đèn 2025')
    if month is None and isinstance(year, int):
        return generate_baocao_den_year_report(year)

    # 5. Mặc định: Tháng này / Kỳ hiện tại
    cy, cm = get_current_cycle()
    return generate_baocao_den_cycle_report(cy, cm)
# ─────────────────────────────────────────────────────────────────────────────
# 4. SỔ THU CHI (ONE-SHOT)
# ─────────────────────────────────────────────────────────────────────────────

def handle_thuchi(raw_text, clean_text, session_id='default_user'):
    """Xử lý lệnh ghi sổ thu hoặc chi (One-shot) - Bảo vệ tuyệt đối không ghi nhầm câu hỏi doanh thu hay báo cáo"""
    if any(k in clean_text for k in ['lap den', 'gan den', 'bi led', 'bi gam', 'v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'naoevo', 'titan']):
        return None

    # CHẶN NGAY các câu hỏi tra cứu, báo cáo doanh thu, tồn quỹ hoặc câu hỏi nghi vấn:
    is_explicit_record = bool(re.search(r'\b(ghi\s*chi|ghi\s*thu|phieu\s*chi|phieu\s*thu|lap\s*phieu|tao\s*phieu|nhap\s*chi|nhap\s*thu)\b', clean_text))
    if not is_explicit_record:
        # Nếu là câu hỏi doanh thu, số lượng đơn, báo cáo, tồn quỹ
        if re.search(r'\b(doanh\s*thu|doanh\s*so|tong\s*thu|bao\s*cao|thong\s*ke|ban\s*duoc|kiem\s*duoc|may\s*don|bao\s*nhieu\s*don|so\s*don|ton\s*quy|so\s*du|quy\s*tien|quy\s*con|tien\s*trong\s*ket|ket\s*tien)\b', clean_text):
            return None
        # Nếu có từ để hỏi nghi vấn
        if re.search(r'\b(bao\s*nhieu|may|sao|the\s*nao|chua|ha|ko|khong)\b', clean_text):
            return None

    has_honorific_chi = bool(re.search(r'\b(chị|chi)\s+([a-zA-ZÀ-ỹ]+)', raw_text, re.IGNORECASE))
    is_explicit_chi = bool(re.search(r'\b(ghi\s*chi|phiếu\s*chi|phieu\s*chi|tiền\s*chi|tien\s*chi|chi\s*tiền|chi\s*tien|chi\s+\d+|chi\s+phi|tam\s*ung|ung\s*tien|tra\s+tien|nop\s+tien|tien\s+an|com|xang|mat\s+bang)\b', clean_text))

    is_chi = is_explicit_chi or (bool(re.search(r'\b(chi\s+\d+|chi\s+[a-zA-Z0-9\.]+(?:k|tr|trieu)|chi\s+tien|tien\s*com|tien\s*xang|tam\s*ung|tra|mua|dong|nop|ung|ung truoc|xuat tien|tien an|com|xang|mat bang|phi)\b', clean_text)) and not has_honorific_chi)
    
    # Chỉ nhận diện THU khi có hành động ghi nhận tiền cụ thể, tuyệt đối không nhận cụm 'doanh thu' hay 'thu' mơ hồ
    is_explicit_thu = bool(re.search(r'\b(ghi\s*thu|phieu\s*thu|thu\s*tien|khach\s*(?:tra|nop|coc|thanh\s*toan)|thu\s*coc|nap\s*(?:tien|vao\s*quy)|tien\s*ve)\b', clean_text))
    is_thu = is_explicit_thu or (bool(re.search(r'\b(thu\s+\d+|thu\s+[a-zA-Z0-9\.]+(?:k|tr|trieu)|thu\s+tien|nhan\s+tien)\b', clean_text)) and not bool(re.search(r'\bdoanh\s*thu\b', clean_text)))
    
    trans_type = 'chi' if is_chi else ('thu' if is_thu else None)
    if not trans_type:
        return None

    amount = parse_vietnamese_money(raw_text)
    if amount <= 0:
        return {
            "type": "clarify",
            "message": f"Tôi nhận ra bạn muốn ghi nhận khoản **{trans_type.upper()}**, nhưng chưa rõ số tiền. Ví dụ: *'chi 500k tiền cơm'* hoặc *'thu 1.5tr tiền cọc'*."
        }

    date_str, note_raw = extract_date(raw_text)
    note = note_raw
    note = re.sub(r'\b(ghi\s*)?(thu|chi|tra|nop|mua)\b', '', note, flags=re.IGNORECASE)
    note = re.sub(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|m|k|nghin|ngan)?\b', '', note, flags=re.IGNORECASE)
    note = re.sub(r'[,.\-]', ' ', note)
    note = ' '.join(note.split()).strip()
    if not note:
        note = "Ghi nhanh qua trợ lý AI"

    amount_k_str = f"{amount//1000:,}k" if amount >= 1000 else f"{amount:,}đ"
    action_label = "KHOẢN CHI" if trans_type == 'chi' else "KHOẢN THU"
    action_icon = "💸" if trans_type == 'chi' else "💰"

    confirm_msg = (
        f"❓ **XÁC NHẬN GHI SỔ THU CHI ({action_label}):**\n"
        f"───────────────────────────\n"
        f"• {action_icon} **Phân loại:** **{trans_type.upper()}**\n"
        f"• 💰 **Số tiền:** **{amount:,.0f} đ** ({amount_k_str})\n"
        f"• 📝 **Nội dung:** **{note.capitalize()}**\n"
        f"• 📅 **Ngày phát sinh:** **{date_str}**\n"
        f"───────────────────────────\n"
        f"👉 Anh có chắc chắn muốn **LƯU KHOẢN NÀY VÀO SỔ QUỸ** không?\n\n"
        f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào Báo Cáo Đèn | Nhắn **'hủy'** để bỏ qua)*"
    )

    WIZARD_SESSIONS[session_id] = {
        'flow': 'confirm_action',
        'action_type': 'thuchi',
        'payload': {
            'trans_type': trans_type,
            'amount': amount,
            'note': note,
            'date_str': date_str
        }
    }
    return {
        "type": "clarify",
        "message": confirm_msg
    }

# ─────────────────────────────────────────────────────────────────────────────
# 5. TRA CỨU BẢO HÀNH & ĐƠN HÀNG
# ─────────────────────────────────────────────────────────────────────────────

def handle_search_warranty_and_orders(raw_text, clean_text):
    """Tra cứu bảo hành và lịch sử đơn hàng theo biển số xe, SĐT, tên khách (Hỗ trợ đại từ nhân xưng linh hoạt và hiển thị đầy đủ SĐT)"""
    is_search = bool(re.search(r'\b(tim|kiem tra|tra cuu|check|xem|bao hanh|lich su|don hang|sdt|so dien thoai|dien thoai|chu xe)\b', clean_text))
    plate = extract_license_plate(raw_text)
    phone = extract_phone(raw_text)
    cust_intent = extract_customer_search_intent(raw_text)

    if not (plate or phone or is_search or cust_intent):
        return None

    search_query = plate if plate else (phone if phone else "")
    if not search_query:
        if cust_intent:
            search_query = cust_intent.get('raw_query', '')
        else:
            m = re.search(r'(?:tim|tra cuu|check|kiem tra|bao hanh|xe|sdt|so dien thoai|dien thoai|chu xe)\s+([a-zA-Z0-9\-\.\s]+)', clean_text)
            if m:
                search_query = m.group(1).strip()

    if not search_query or len(search_query) < 2:
        return {
            "type": "clarify",
            "message": "🔍 Bạn muốn tra cứu thông tin bảo hành, chủ xe hoặc SĐT cho **Biển số xe**, **Số điện thoại** hay **Tên khách hàng** nào? (Ví dụ: *'tra cứu biển số 63A-187.30'* hoặc *'sđt xe 63A-192.37'* hoặc *'chị Mỹ Vios'*)"
        }

    clean_q = clean_plate_raw(search_query)
    clean_phone_q = re.sub(r'\D', '', search_query)
    is_asking_phone = any(k in clean_text for k in ['sdt', 'so dien thoai', 'dien thoai', 'phone', 'so dt', 'lien he', 'goi cho'])

    grouped = {}

    # 1. Tra cứu trong phần mềm Bán Hàng & Kho
    if os.path.exists(DB_BANHANG):
        try:
            conn = sqlite3.connect(DB_BANHANG, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            if cust_intent:
                target_name = cust_intent['name']
                extra = cust_intent['extra']
                hon = cust_intent['honorific']

                c.execute("""
                    SELECT id, customer_name, phone, license_plate, install_date, total_price 
                    FROM orders 
                    WHERE customer_name IS NOT NULL AND customer_name != ''
                    ORDER BY install_date DESC
                """)
                orders = c.fetchall()

                for o in orders:
                    c_name = (o['customer_name'] or '').strip()
                    c_plate = (o['license_plate'] or '').strip()
                    clean_c_name = remove_accents(c_name).lower()
                    clean_c_plate = clean_plate_raw(c_plate)

                    # Bắt buộc khớp tên cốt lõi
                    if not re.search(r'\b' + re.escape(target_name) + r'\b', clean_c_name):
                        continue

                    key = clean_c_plate if clean_c_plate and clean_c_plate not in ('KHONGRO',) else clean_c_name
                    
                    phone_val = (o['phone'] or '').strip()
                    if not phone_val and clean_c_plate and clean_c_plate not in ('', 'KHONGRO'):
                        c.execute("""
                            SELECT phone FROM orders 
                            WHERE replace(replace(replace(replace(UPPER(license_plate), '-', ''), '.', ''), ' ', ''), '_', '') = ?
                              AND phone IS NOT NULL AND phone != '' 
                            LIMIT 1
                        """, (clean_c_plate,))
                        p_row = c.fetchone()
                        if p_row and p_row[0]:
                            phone_val = p_row[0].strip()

                    oid = o['id']
                    c.execute("SELECT item_name, price, warranty_months, qty FROM order_items WHERE order_id = ?", (oid,))
                    items = c.fetchall()

                    if key not in grouped:
                        score = 10
                        if re.search(r'\b' + re.escape(target_name) + r'\b', clean_c_name):
                            score += 20
                        
                        # Khớp chính xác tên ngay sau đại từ (VD: 'Cô Mỹ - ...', 'Chị Mỹ - ...')
                        if re.search(rf'^(?:anh|chi|co|chu|bac|em|di|duong|cau|mo|thim|thay|ban|ong|ba|cu|a|c|e)\s+{re.escape(target_name)}(?:\s*[-/(]|\s*$)', clean_c_name):
                            score += 25

                        # Khớp đại từ nhân xưng người dùng nhập
                        if hon in ['anh', 'a'] and (clean_c_name.startswith('anh ') or clean_c_name.startswith('a ')):
                            score += 15
                        elif hon in ['chi', 'c'] and (clean_c_name.startswith('chi ') or clean_c_name.startswith('c ')):
                            score += 15
                        elif hon == 'co' and clean_c_name.startswith('co '):
                            score += 15
                        elif hon == 'chu' and clean_c_name.startswith('chu '):
                            score += 15
                        elif hon == 'bac' and clean_c_name.startswith('bac '):
                            score += 15
                        elif hon in ['em', 'e'] and (clean_c_name.startswith('em ') or clean_c_name.startswith('e ')):
                            score += 15
                        elif clean_c_name.startswith(hon + ' '):
                            score += 15

                        matched_extra = False
                        if extra:
                            for ex in extra:
                                if re.search(r'\b' + re.escape(ex), clean_c_name) or (clean_c_plate and ex in clean_c_plate.lower()):
                                    score += 50
                                    matched_extra = True

                        grouped[key] = {
                            "source": "Bán hàng & Kho",
                            "plate": c_plate,
                            "name": c_name,
                            "phone": phone_val,
                            "score": score,
                            "matched_extra": matched_extra,
                            "visits": []
                        }
                    elif not grouped[key]["phone"] and phone_val:
                        grouped[key]["phone"] = phone_val

                    grouped[key]["visits"].append({
                        "order_id": oid,
                        "date": o['install_date'],
                        "total": o['total_price'] or 0,
                        "items": [dict(it) for it in items]
                    })

            else:
                valid_phone_filter = f"%{clean_phone_q}%" if len(clean_phone_q) >= 9 else "__NO_PHONE_MATCH__"
                c.execute("""
                    SELECT id, customer_name, phone, license_plate, install_date, total_price 
                    FROM orders 
                    WHERE replace(replace(replace(replace(UPPER(license_plate), '-', ''), '.', ''), ' ', ''), '_', '') LIKE ?
                       OR license_plate LIKE ? 
                       OR replace(replace(replace(replace(phone, '-', ''), '.', ''), ' ', ''), '_', '') LIKE ? 
                       OR phone LIKE ?
                       OR customer_name LIKE ?
                    ORDER BY install_date DESC LIMIT 10
                """, (f"%{clean_q}%", f"%{search_query}%", valid_phone_filter, valid_phone_filter, f"%{search_query}%"))
                orders = c.fetchall()

                for o in orders:
                    c_plate = (o['license_plate'] or '').strip()
                    c_name = (o['customer_name'] or '').strip()
                    key = (clean_plate_raw(c_plate) if c_plate and c_plate not in ('KHÔNG RÕ',) else c_name) or f"ORDER_{o['id']}"
                    
                    phone_val = (o['phone'] or '').strip()
                    if not phone_val and c_plate and c_plate not in ('', 'KHÔNG RÕ'):
                        c.execute("""
                            SELECT phone FROM orders 
                            WHERE replace(replace(replace(replace(UPPER(license_plate), '-', ''), '.', ''), ' ', ''), '_', '') = ?
                              AND phone IS NOT NULL AND phone != '' 
                            LIMIT 1
                        """, (clean_plate_raw(c_plate),))
                        p_row = c.fetchone()
                        if p_row and p_row[0]:
                            phone_val = p_row[0].strip()

                    oid = o['id']
                    c.execute("SELECT item_name, price, warranty_months, qty FROM order_items WHERE order_id = ?", (oid,))
                    items = c.fetchall()

                    if key not in grouped:
                        grouped[key] = {
                            "source": "Bán hàng & Kho",
                            "plate": c_plate,
                            "name": c_name,
                            "phone": phone_val,
                            "score": 10,
                            "matched_extra": False,
                            "visits": []
                        }
                    elif not grouped[key]["phone"] and phone_val:
                        grouped[key]["phone"] = phone_val

                    grouped[key]["visits"].append({
                        "order_id": oid,
                        "date": o['install_date'],
                        "total": o['total_price'] or 0,
                        "items": [dict(it) for it in items]
                    })
            conn.close()
        except Exception:
            pass

    # 2. Tra cứu trong Báo Cáo Đèn
    if os.path.exists(DB_DEN):
        try:
            conn = sqlite3.connect(DB_DEN, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            if cust_intent:
                target_name = cust_intent['name']
                extra = cust_intent['extra']
                hon = cust_intent['honorific']

                c.execute("""
                    SELECT id, order_date, product_name, customer_name, car_model, price_k
                    FROM orders
                    WHERE customer_name IS NOT NULL AND customer_name != ''
                    ORDER BY order_date DESC
                """)
                den_orders = c.fetchall()

                for r in den_orders:
                    c_name = (r['customer_name'] or '').strip()
                    c_model = (r['car_model'] or '').strip()
                    clean_c_name = remove_accents(c_name).lower()
                    clean_c_model = remove_accents(c_model).lower()

                    if not re.search(r'\b' + re.escape(target_name) + r'\b', clean_c_name):
                        continue

                    # Thử hợp nhất vào khách hàng đã có trong phần mềm Bán Hàng (nếu cùng tên và trùng model xe)
                    found_group = None
                    norm_model = re.sub(r'[\s\-_]', '', clean_c_model)
                    model_key = re.sub(r'\d+', '', norm_model)
                    model_words = [w for w in re.split(r'\s+', clean_c_model) if len(w) >= 3 and not w.isdigit()]
                    candidate_groups = []
                    for g in grouped.values():
                        clean_g_name = remove_accents(g['name']).lower()
                        norm_g_name = re.sub(r'[\s\-_]', '', clean_g_name)
                        if re.search(r'\b' + re.escape(target_name) + r'\b', clean_g_name):
                            if (len(model_key) >= 3 and model_key in norm_g_name) or (model_words and any(w in clean_g_name for w in model_words)):
                                candidate_groups.append(g)

                    if candidate_groups:
                        c_hon = clean_c_name.split()[0] if clean_c_name else ""
                        best_g = candidate_groups[0]
                        for cand in candidate_groups:
                            clean_cand_name = remove_accents(cand['name']).lower()
                            if c_hon and clean_cand_name.startswith(c_hon + ' '):
                                best_g = cand
                                break
                        found_group = best_g

                    if found_group:
                        found_group["visits"].append({
                            "order_id": f"ĐÈN-{r['id']}",
                            "date": r['order_date'],
                            "total": (r['price_k'] or 0) * 1000,
                            "items": [{"item_name": r['product_name'], "price": (r['price_k'] or 0) * 1000, "warranty_months": 24, "qty": 1}]
                        })
                        continue

                    key = f"DEN_{c_name}_{c_model}"
                    den_phone = ""
                    den_plate = c_model

                    if key not in grouped:
                        score = 10
                        if re.search(r'\b' + re.escape(target_name) + r'\b', clean_c_name):
                            score += 20
                        if re.search(rf'^(?:anh|chi|co|chu|bac|em|di|duong|cau|mo|thim|thay|ban|ong|ba|cu|a|c|e)\s+{re.escape(target_name)}(?:\s*[-/(]|\s*$)', clean_c_name):
                            score += 25
                        if hon in ['anh', 'a'] and (clean_c_name.startswith('anh ') or clean_c_name.startswith('a ')):
                            score += 15
                        elif hon in ['chi', 'c'] and (clean_c_name.startswith('chi ') or clean_c_name.startswith('c ')):
                            score += 15
                        elif hon == 'co' and clean_c_name.startswith('co '):
                            score += 15
                        elif hon == 'chu' and clean_c_name.startswith('chu '):
                            score += 15
                        elif hon == 'bac' and clean_c_name.startswith('bac '):
                            score += 15
                        elif hon in ['em', 'e'] and (clean_c_name.startswith('em ') or clean_c_name.startswith('e ')):
                            score += 15
                        elif clean_c_name.startswith(hon + ' '):
                            score += 15

                        matched_extra = False
                        if extra:
                            for ex in extra:
                                if re.search(r'\b' + re.escape(ex), clean_c_name) or (clean_c_model and ex in clean_c_model):
                                    score += 50
                                    matched_extra = True

                        grouped[key] = {
                            "source": "Báo cáo Đèn",
                            "plate": den_plate,
                            "name": c_name,
                            "phone": den_phone,
                            "score": score,
                            "matched_extra": matched_extra,
                            "visits": []
                        }
                    grouped[key]["visits"].append({
                        "order_id": f"ĐÈN-{r['id']}",
                        "date": r['order_date'],
                        "total": (r['price_k'] or 0) * 1000,
                        "items": [{"item_name": r['product_name'], "price": (r['price_k'] or 0) * 1000, "warranty_months": 24, "qty": 1}]
                    })

            else:
                c.execute("""
                    SELECT id, order_date, product_name, customer_name, car_model, price_k
                    FROM orders
                    WHERE customer_name LIKE ? OR car_model LIKE ?
                    ORDER BY order_date DESC LIMIT 5
                """, (f"%{search_query}%", f"%{search_query}%"))
                den_orders = c.fetchall()
                
                for r in den_orders:
                    c_name = (r['customer_name'] or '').strip()
                    c_model = (r['car_model'] or '').strip()
                    key = f"DEN_{c_name}_{c_model}"
                    
                    den_phone = ""
                    den_plate = c_model
                    if os.path.exists(DB_BANHANG):
                        try:
                            conn_bh = sqlite3.connect(DB_BANHANG, timeout=5)
                            c_bh = conn_bh.cursor()
                            c_bh.execute("SELECT phone, license_plate FROM orders WHERE UPPER(customer_name) = ? AND phone != '' LIMIT 1", (c_name.upper(),))
                            bh_match = c_bh.fetchone()
                            if bh_match:
                                den_phone = bh_match[0] or ""
                                if bh_match[1]:
                                    den_plate = f"{c_model} ({bh_match[1]})"
                            conn_bh.close()
                        except Exception:
                            pass

                    if key not in grouped:
                        grouped[key] = {
                            "source": "Báo cáo Đèn",
                            "plate": den_plate,
                            "name": c_name,
                            "phone": den_phone,
                            "score": 10,
                            "matched_extra": False,
                            "visits": []
                        }
                    grouped[key]["visits"].append({
                        "order_id": r['id'],
                        "date": r['order_date'],
                        "total": (r['price_k'] or 0) * 1000,
                        "items": [{"item_name": r['product_name'], "price": (r['price_k'] or 0) * 1000, "warranty_months": 24, "qty": 1}]
                    })
            conn.close()
        except Exception:
            pass

    if not grouped:
        display_q = raw_text.strip() if cust_intent else search_query
        return {
            "type": "info",
            "message": f"🔎 Không tìm thấy đơn hàng hoặc thông tin khách hàng nào khớp với từ khóa **'{display_q}'**.\nBạn vui lòng kiểm tra lại biển số xe, số điện thoại hoặc tên khách nhé!"
        }

    # Nếu có cust_intent: Ưu tiên ứng viên khớp matched_extra nếu user gõ kèm xe
    candidate_list = list(grouped.values())
    if cust_intent and cust_intent.get('extra'):
        extra_matches = [c for c in candidate_list if c.get('matched_extra')]
        if extra_matches:
            candidate_list = extra_matches

    # Sắp xếp theo score và số lần đến làm xe
    candidate_list.sort(key=lambda x: (x.get('score', 0), len(x.get('visits', []))), reverse=True)
    top_candidates = candidate_list[:3]

    display_q = raw_text.strip() if cust_intent else search_query
    res_text = f"🔍 **KẾT QUẢ TRA CỨU KHÁCH HÀNG / BẢO HÀNH: '{display_q.upper()}'**\n\n"

    for info in top_candidates:
        plate_str = info['plate'] if info['plate'] else 'Chưa lưu biển số'
        name_str = info['name'] if info['name'] else 'Khách lẻ'
        phone_str = info['phone'].strip() if info.get('phone') else ''
        
        if phone_str:
            phone_badge = f"📞 **Số điện thoại:** **{phone_str}**"
        else:
            phone_badge = "📞 **Số điện thoại:** *(Chưa lưu SĐT trên hệ thống)*"

        res_text += f"👤 **Chủ xe / Khách hàng:** **{name_str}**\n"
        res_text += f"🚗 **Biển số xe:** **{plate_str}** | {phone_badge}\n"
        
        total_spent = sum(v['total'] for v in info['visits'])
        num_visits = len(info['visits'])
        res_text += f"💰 **Tổng chi tiêu:** **{total_spent:,.0f} đ** ({num_visits} lần làm xe)\n"
        res_text += f"📋 **Lịch sử phụ kiện & Hạn bảo hành:**\n"

        for v in info['visits']:
            res_text += f"  📅 *Ngày {v['date']} (Đơn #{v['order_id']} - {v['total']:,.0f} đ):*\n"
            if v['items']:
                for it in v['items']:
                    war = it.get('warranty_months', 0)
                    war_badge = f"🛡️ BH {war} tháng" if war > 0 else "Không BH"
                    res_text += f"    • {it['item_name']}: {it['price']:,.0f} đ ({war_badge})\n"
            else:
                res_text += f"    • (Không có chi tiết từng món)\n"
        res_text += "──────────────────────────\n"

    res_text += f"\n👉 [Mở tab Tra cứu trên phần mềm Bán hàng](/banhang/)"
    return {"type": "success", "message": res_text}

# ─────────────────────────────────────────────────────────────────────────────
# 6. TRA CỨU TỒN KHO & GIÁ BÁN
# ─────────────────────────────────────────────────────────────────────────────

def handle_stock_and_price(raw_text, clean_text, require_explicit_intent=False):
    """
    Tra cứu sản phẩm trong kho hàng cực kỳ thông minh (Fuzzy Search):
    - Người dùng chỉ cần gõ bất kỳ từ ngữ nào (VD: '70mai', 'm310', 'blam', 'vincar', 'sub 10', 'innova 2026')
    - Không cần phải gõ đúng 100% tên hàng
    - Tìm không dấu, có dấu, tìm theo mã SP..., nhóm hàng, tên hàng
    - Tự động sắp xếp sản phẩm còn tồn kho và có độ khớp cao nhất lên đầu
    """
    if 'texpad' in clean_text and '360' in clean_text:
        return {
            "type": "info",
            "module": "banhang",
            "message": (
                "⚠️ **THÔNG BÁO TỪ TRẦN BÌNH AUTO:**\n"
                "Hiện tại dòng **Camera 360 TexPad gara đã ngừng kinh doanh**.\n\n"
                "👉 Gara khuyên dùng các dòng Camera 360 độ thế hệ mới đang có sẵn hàng:\n"
                "• **Camera 360 Owin (VF3, XForce, Mazda, CRV...):** **8.5tr - 16.1tr** *(Cắm giắc zin 100%, cảm biến Sony siêu nét)*\n"
                "• **Camera 360 DCT (T1 Pro / T2 Pro):** **12.8tr - 15.8tr** *(Dòng cam 360 nét nhất hiện nay)*\n"
                "• **Màn hình liền Cam 360 WINCA S170+ / S300+:** **10.5tr - 15.5tr**"
            )
        }

    if not os.path.exists(DB_BANHANG):
        return None

    raw_q = raw_text.strip()
    if not raw_q or len(raw_q) < 2:
        return None

    # Tách từ khóa
    clean_q = remove_accents(raw_q).lower()
    stop_words = [
        'tim', 'kiem', 'tra', 'check', 'xem', 'hoi', 'gia', 'ban', 'bao', 'nhieu', 
        'tien', 'kho', 'con', 'hang', 'khong', 'ko', 'a', 'ha', 'san', 'pham', 'mat',
        'co', 'cho', 'minh', 'em', 'toi', 'biet', 'chua', 'hang', 'cho'
    ]
    tokens = [t for t in re.split(r'[\s\-_\.,/]+', clean_q) if t and t not in stop_words]
    if not tokens:
        tokens = [t for t in re.split(r'[\s\-_\.,/]+', clean_q) if t]
    if not tokens:
        return None

    # Nếu từ khóa chỉ là 1 từ thông dụng chung chung (không phải tên sản phẩm) -> Tránh tìm bừa
    common_general_words = {'da', 'xe', 'dung', 'cho', 'lam', 'oto', 'goi', 'gia', 'ban', 'toi', 'minh', 'em', 'anh', 'muon', 'can', 'hoi'}
    if len(tokens) == 1 and tokens[0] in common_general_words:
        return None

    try:
        conn = sqlite3.connect(DB_BANHANG, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT id, code, name, category, price, cost_price, stock, warranty_months, warranty_raw FROM products")
        all_prods = c.fetchall()
        conn.close()

        results = []
        clean_full_q = ' '.join(tokens)

        for p in all_prods:
            p_name = p['name'] or ''
            p_code = p['code'] or ''
            p_cat = p['category'] or ''

            p_name_clean = remove_accents(p_name).lower()
            p_code_clean = p_code.lower()
            p_cat_clean = remove_accents(p_cat).lower()
            
            score = 0
            
            # 1. Khớp mã hàng chính xác hoặc một phần mã
            if clean_full_q == p_code_clean:
                score += 1000
            elif clean_full_q in p_code_clean:
                score += 600

            # 2. Khớp nguyên cụm từ người dùng gõ trong tên hàng
            if clean_full_q in p_name_clean:
                score += 400
            elif clean_q in p_name_clean:
                score += 350

            # 3. Khớp từng token (từ rời rạc)
            matched_count = 0
            for tok in tokens:
                if len(tok) == 1 and not tok.isdigit():
                    continue
                if tok in p_name_clean:
                    matched_count += 1
                elif tok in p_cat_clean or tok in p_code_clean:
                    matched_count += 0.5

            if len(tokens) > 0:
                if matched_count == len(tokens):
                    score += 250 + matched_count * 15
                elif matched_count > 0:
                    score += matched_count * 30

            # Điểm ưu tiên nếu còn tồn kho
            if score >= 30:
                if p['stock'] and p['stock'] > 0:
                    score += 20
                results.append((score, dict(p)))

        results.sort(key=lambda x: x[0], reverse=True)
        min_thresh = 50 if require_explicit_intent else 100
        top_matches = [r[1] for r in results[:6] if r[0] >= min_thresh]

        if not top_matches:
            if require_explicit_intent:
                return {"type": "info", "message": f"📦 Không tìm thấy mặt hàng nào khớp với từ khóa: **'{raw_q}'** trong kho."}
            return None

        reply = f"🏷️ **BÁO GIÁ SẢN PHẨM: '{raw_q.upper()}'**\n\n"

        for p in top_matches:
            war_m = p['warranty_months'] or 0
            war_badge = f"{war_m} tháng" if war_m > 0 else (p['warranty_raw'] or 'Theo nhà sản xuất')
            cat_label = f"📁 *{p['category']}*\n" if p['category'] else ""

            stock_val = p.get('stock') or 0
            stock_badge = f"🟢 Còn hàng: **{int(stock_val)}**" if stock_val > 0 else "🔴 *Tạm hết hàng*"

            reply += f"• **{p['name']}** `({p['code'] or 'SP'})`\n"
            if cat_label:
                reply += f"  {cat_label}"
            reply += f"  - 💰 Giá bán: **{p['price']:,.0f} đ** | 🛡️ BH: **{war_badge}** | {stock_badge}\n\n"

        reply += "👉 [Xem danh sách kho hàng](/banhang/)"
        return {
            "type": "success",
            "module": "banhang",
            "message": reply
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi tra cứu mặt hàng kho: {str(e)}"}

def parse_time_scope(text):
    """
    Trích xuất đa chiều: Phạm vi thời gian (nhiều tháng, năm, hôm nay), Scope phân hệ (cửa hàng, bán hàng, đèn), Ý định đếm đơn
    - Hỗ trợ câu hỏi nhiều tháng: 'tháng 7, tháng 8, 2026', 'tháng 7, 8 năm 2026', 'tháng 7 và 8', 'từ tháng 7 đến tháng 9'
    - Hỗ trợ câu hỏi cả năm: 'doanh thu cả năm 2025 là bao nhiêu'
    - Hỗ trợ câu hỏi số lượng đơn hàng: 'tháng 8 năm 2026 bán được bao nhiêu đơn', 'tháng 7 bán được mấy đơn'
    - Phân biệt cực kỳ thông minh giữa giới từ 'đến' (từ ... đến ...) và sản phẩm 'đèn' (nâng cấp ánh sáng)
    """
    clean = remove_accents(text).lower().strip()

    # 1. Trích xuất năm (4 chữ số dạng 202x)
    year = None
    m_y = re.search(r'\b(?:nam\s+)?(202\d)\b', clean)
    if m_y:
        year = int(m_y.group(1))

    # 2. Hôm nay / Hôm qua
    if any(k in clean for k in ['hom nay', 'today']):
        return {'period': 'today', 'months': [], 'year': year, 'scope': 'all', 'is_order_count': False}
    if any(k in clean for k in ['hom qua', 'yesterday']):
        return {'period': 'yesterday', 'months': [], 'year': year, 'scope': 'all', 'is_order_count': False}

    # 3. Trích xuất tháng:
    months = []
    # Dạng dải tháng: 'từ tháng X đến tháng Y'
    m_range = re.search(r'\btu\s+(?:thang\s+)?(\d{1,2})\s+den\s+(?:thang\s+)?(\d{1,2})\b', clean)
    if m_range:
        start_m = int(m_range.group(1))
        end_m = int(m_range.group(2))
        if 1 <= start_m <= end_m <= 12:
            months = list(range(start_m, end_m + 1))
    else:
        # Dạng combo: 'tháng 7, 8' hoặc 'tháng 7 và 8' hoặc 'tháng 7, 8, 9'
        m_combo = re.search(r'\b(?:thang|thg|t)\s*(\d{1,2})(?:\s*(?:[,&]|va)\s*(\d{1,2}))+', clean)
        if m_combo:
            nums = re.findall(r'\b(\d{1,2})\b', m_combo.group(0))
            for n in nums:
                v = int(n)
                if 1 <= v <= 12 and v not in months:
                    months.append(v)

        # Dạng liệt kê riêng rẽ: 'tháng 7, tháng 8', 't7, t8'
        for m in re.finditer(r'\b(?:thang|thg|t)\s*([0-1]?\d)\b', clean):
            val = int(m.group(1))
            if 1 <= val <= 12 and val not in months:
                months.append(val)

        # Dạng mm/yyyy
        for m in re.finditer(r'\b([0-1]?\d)[/-](202\d)\b', clean):
            val = int(m.group(1))
            y_val = int(m.group(2))
            if 1 <= val <= 12 and val not in months:
                months.append(val)
            if not year:
                year = y_val

    # 4. Scope phân hệ (Phân biệt cẩn trọng giữa giới từ 'đến' và sản phẩm 'đèn'):
    has_lamp = False
    if re.search(r'\b(đèn|bi\s*led|bi\s*gầm|độ\s*đèn|đèn\s*pha|bóng)\b', text, re.IGNORECASE):
        has_lamp = True
    else:
        # Nếu câu không dấu, loại trừ các ngữ cảnh 'từ ... đến ...' hoặc 'đến tháng/ngày'
        clean_no_range = re.sub(r'\btu\s+.*?\s+den\b', ' ', clean)
        clean_no_range = re.sub(r'\bden\s+(?:thang|ngay|nam|\d)\b', ' ', clean_no_range)
        if re.search(r'\b(den|bi|gam|pha|bong)\b', clean_no_range) and not any(k in clean for k in ['den pin', 'den ban']):
            has_lamp = True

    scope = 'all'
    if has_lamp and not any(k in clean for k in ['cua hang', 'toan bo', 'tong hop', 'gara', 'ban hang']):
        scope = 'den'
    elif any(k in clean for k in ['ban hang', 'kho', 'phu kien']):
        scope = 'banhang'

    # 5. Ý định đếm số lượng đơn hàng:
    is_order_count = bool(re.search(r'\b(may don|bao nhieu don|so don|don hang)\b', clean))

    period = 'months' if months else ('year' if year else ('current_cycle' if any(k in clean for k in ['thang nay', 'ky nay', 'hien tai']) else 'unknown'))
    return {
        'period': period,
        'months': sorted(months),
        'year': year,
        'scope': scope,
        'is_order_count': is_order_count
    }


def handle_revenue_and_store_stats(raw_text, clean_text, session_id="default_user"):
    """
    BỘ ĐIỀU PHỐI BÁO CÁO DOANH THU & TỒN QUỸ & ĐƠN HÀNG TOÀN DIỆN:
    1. Tồn quỹ / Két tiền mặt hiện tại: 'tồn quỹ hiện tại còn bao nhiêu', 'số dư quỹ'
    2. Doanh thu nhiều tháng: 'tổng doanh thu của cửa hàng tháng 7, tháng 8, 2026 là bao nhiêu?'
    3. Doanh thu 1 tháng: 'tháng 7 năm 2026 doanh thu bao nhiêu', 'doanh thu bán hàng tháng 8/2026'
    4. Doanh thu thiếu thông tin năm: 'tháng 7 bán được mấy đơn', 'tháng 7 doanh thu bao nhiêu' -> Hỏi lại năm kèm số liệu năm 2026
    5. Doanh thu cả năm: 'doanh thu cả năm 2025 là bao nhiêu'
    6. Số lượng đơn hàng: 'tháng 8 năm 2026 bán được bao nhiêu đơn'
    7. Thống kê hôm nay / hôm qua: 'hôm nay bán được bao nhiêu tiền', 'hôm nay chi bao nhiêu'
    """
    # ═════════════════════════════════════════════════════════════════════
    # A. Ý ĐỊNH TRA CỨU TỒN QUỸ / KÉT TIỀN MẶT
    # ═════════════════════════════════════════════════════════════════════
    is_cash_balance = bool(re.search(r'\b(ton\s*quy|so\s*du\s*quy|quy\s*tien|tien\s*trong\s*ket|ket\s*tien|quy\s*con|so\s*du\s*hien\s*tai)\b', clean_text)) or \
                      (bool(re.search(r'\b(con\s*bao\s*nhieu\s*tien|so\s*du)\b', clean_text)) and not any(k in clean_text for k in ['ban', 'den', 'gia', 'don']))
    if is_cash_balance:
        if not os.path.exists(DB_THUCHI):
            return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Sổ Thu Chi!"}
        try:
            conn = sqlite3.connect(DB_THUCHI, timeout=10)
            c = conn.cursor()
            c.execute("SELECT id, name FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            p = c.fetchone()
            if not p:
                return {"type": "info", "message": "Hiện tại chưa có kỳ thu chi nào đang mở (active)."}
            period_id, period_name = p[0], p[1]
            c.execute("SELECT SUM(CASE WHEN type='thu' THEN amount ELSE 0 END), SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) FROM transactions WHERE period_id = ?", (period_id,))
            row = c.fetchone()
            inc = row[0] or 0
            exp = row[1] or 0
            bal = inc - exp
            conn.close()
            return {
                "type": "success",
                "module": "thuchi",
                "message": (
                    f"💰 **BÁO CÁO TỒN QUỸ TIỀN MẶT GARA ({period_name}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"• 📈 Tổng thu trong kỳ: **+{inc:,.0f} đ**\n"
                    f"• 📉 Tổng chi trong kỳ: **-{exp:,.0f} đ**\n"
                    f"• 💵 **TỒN QUỸ (SỐ DƯ HIỆN TẠI):** **{bal:,.0f} đ**\n\n"
                    f"👉 [Bấm vào đây để mở Sổ Thu Chi xem chi tiết](/thuchi/)"
                )
            }
        except Exception as e:
            return {"type": "error", "message": f"Lỗi kiểm tra tồn quỹ: {str(e)}"}

    # ═════════════════════════════════════════════════════════════════════
    # B. KIỂM TRA Ý ĐỊNH BÁO CÁO / THỐNG KÊ DOANH THU HOẶC ĐƠN HÀNG
    # ═════════════════════════════════════════════════════════════════════
    is_stat_query = bool(re.search(r'\b(doanh\s*thu|doanh\s*so|tong\s*thu|bao\s*cao|tong\s*ket|ban\s*duoc|kiem\s*duoc|may\s*don|bao\s*nhieu\s*don|so\s*don|don\s*hang)\b', clean_text)) or \
                    ('ban' in clean_text and 'bao nhieu' in clean_text) or ('doanh thu' in clean_text)

    ts = parse_time_scope(raw_text)
    if not is_stat_query and ts['period'] == 'unknown':
        return None

    # B1. HÔM NAY / HÔM QUA
    if ts['period'] in ('today', 'yesterday'):
        target_date = datetime.now().date() if ts['period'] == 'today' else (datetime.now().date() - timedelta(days=1))
        target_str = target_date.strftime('%Y-%m-%d')
        date_display = target_date.strftime('%d/%m/%Y')
        title_time = "HÔM NAY" if ts['period'] == 'today' else "HÔM QUA"

        # Nếu hỏi chi hôm nay:
        if 'chi' in clean_text and not any(k in clean_text for k in ['ban', 'doanh thu', 'doanh so']):
            exp_today = 0
            if os.path.exists(DB_THUCHI):
                try:
                    conn = sqlite3.connect(DB_THUCHI, timeout=5)
                    c = conn.cursor()
                    c.execute("SELECT SUM(amount) FROM transactions WHERE type='chi' AND created_at LIKE ?", (f"{target_str}%",))
                    r = c.fetchone()
                    exp_today = r[0] or 0
                    conn.close()
                except: pass
            return {
                "type": "success",
                "module": "thuchi",
                "message": (
                    f"💸 **TỔNG CHI TIỀN {title_time} ({date_display}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Số tiền chi ra: **{exp_today:,.0f} đ**\n\n"
                    f"👉 [Xem Sổ Thu Chi](/thuchi/)"
                )
            }

        # Doanh số bán hàng & Đèn hôm nay:
        orders_bh, rev_bh = 0, 0
        if os.path.exists(DB_BANHANG):
            try:
                conn = sqlite3.connect(DB_BANHANG, timeout=5)
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date = ?", (target_str,))
                r = c.fetchone()
                orders_bh = r[0] or 0
                rev_bh = r[1] or 0
                conn.close()
            except: pass

        orders_den, qty_den, rev_den = 0, 0, 0
        if os.path.exists(DB_DEN):
            try:
                conn = sqlite3.connect(DB_DEN, timeout=5)
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k * 1000) FROM orders WHERE order_date = ?", (target_str,))
                r = c.fetchone()
                orders_den = r[0] or 0
                qty_den = r[1] or 0
                rev_den = r[2] or 0
                conn.close()
            except: pass

        tot_rev = rev_bh + rev_den
        tot_orders = orders_bh + orders_den
        return {
            "type": "success",
            "message": (
                f"📊 **BÁO CÁO DOANH THU TOÀN CỬA HÀNG {title_time} ({date_display}):**\n"
                f"─────────────────────────────────────────\n"
                f"💰 **TỔNG DOANH SỐ {title_time}:** **{tot_rev:,.0f} đ** *({tot_orders} đơn hàng)*\n\n"
                f"• 📦 **Bán Hàng Phụ Kiện:** **{rev_bh:,.0f} đ** ({orders_bh} đơn)\n"
                f"• 💡 **Báo Cáo Đèn:** **{rev_den:,.0f} đ** ({orders_den} đơn / {qty_den} bộ)\n\n"
                f"👉 [Xem Bán Hàng](/banhang/) | [Xem Báo Cáo Đèn](/den/) | [Xem Sổ Thu Chi](/thuchi/)"
            )
        }

    # B2. HỎI DOANH THU CẢ NĂM (Ví dụ: 'doanh thu cả năm 2025 là bao nhiêu')
    if ts['period'] == 'year' and ts['year']:
        target_year = ts['year']
        cnt_bh, rev_bh = 0, 0
        if os.path.exists(DB_BANHANG):
            try:
                conn = sqlite3.connect(DB_BANHANG, timeout=5)
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date LIKE ?", (f"{target_year}%",))
                r = c.fetchone()
                cnt_bh = r[0] or 0
                rev_bh = r[1] or 0
                conn.close()
            except: pass

        cnt_den, qty_den, rev_den = 0, 0, 0
        if os.path.exists(DB_DEN):
            try:
                conn = sqlite3.connect(DB_DEN, timeout=5)
                c = conn.cursor()
                c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k * 1000) FROM orders WHERE order_date LIKE ?", (f"{target_year}%",))
                r = c.fetchone()
                cnt_den = r[0] or 0
                qty_den = r[1] or 0
                rev_den = r[2] or 0
                conn.close()
            except: pass

        if ts['scope'] == 'banhang':
            return {
                "type": "success",
                "message": (
                    f"📦 **BÁO CÁO DOANH THU BÁN HÀNG CẢ NĂM {target_year}:**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Tổng doanh số: **{rev_bh:,.0f} đ**\n"
                    f"• Tổng số đơn hàng: **{cnt_bh} đơn**\n\n"
                    f"👉 [Xem chi tiết Bán Hàng](/banhang/)"
                )
            }
        elif ts['scope'] == 'den':
            return {
                "type": "success",
                "message": (
                    f"💡 **BÁO CÁO DOANH THU ĐÈN CẢ NĂM {target_year}:**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Tổng doanh số: **{rev_den:,.0f} đ**\n"
                    f"• Tổng số đơn: **{cnt_den} đơn** ({qty_den} bộ đèn)\n\n"
                    f"👉 [Xem chi tiết Báo Cáo Đèn](/den/)"
                )
            }
        else:
            tot_rev = rev_bh + rev_den
            tot_cnt = cnt_bh + cnt_den
            return {
                "type": "success",
                "message": (
                    f"📊 **BÁO CÁO TỔNG DOANH THU TOÀN CỬA HÀNG NĂM {target_year}:**\n"
                    f"─────────────────────────────────────────\n"
                    f"💰 **TỔNG DOANH THU CẢ NĂM {target_year}:** **{tot_rev:,.0f} đ** *({tot_cnt} đơn hàng)*\n\n"
                    f"• 📦 **Bán Hàng Phụ Kiện:** **{rev_bh:,.0f} đ** ({cnt_bh} đơn)\n"
                    f"• 💡 **Báo Cáo Đèn:** **{rev_den:,.0f} đ** ({cnt_den} đơn / {qty_den} bộ)\n\n"
                    f"👉 [Xem Bán Hàng](/banhang/) | [Xem Báo Cáo Đèn](/den/)"
                )
            }

    # B3. HỎI THEO THÁNG (ĐA THÁNG HOẶC 1 THÁNG)
    if ts['months']:
        # Nếu chỉ có 1 tháng và THIẾU NĂM (Ví dụ: 'tháng 7 bán được mấy đơn', 'tháng 7 doanh thu bao nhiêu'):
        if len(ts['months']) == 1 and ts['year'] is None:
            m_target = ts['months'][0]
            # Tính dữ liệu năm 2026 (năm gần nhất)
            preview_yr = 2026
            m_str = f"{preview_yr}-{m_target:02d}"
            cnt_bh, rev_bh = 0, 0
            if os.path.exists(DB_BANHANG):
                try:
                    conn = sqlite3.connect(DB_BANHANG, timeout=5)
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date LIKE ?", (f"{m_str}%",))
                    r = c.fetchone()
                    cnt_bh = r[0] or 0
                    rev_bh = r[1] or 0
                    conn.close()
                except: pass

            cnt_den, qty_den, rev_den = 0, 0, 0
            if os.path.exists(DB_DEN):
                try:
                    conn = sqlite3.connect(DB_DEN, timeout=5)
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k * 1000) FROM orders WHERE order_date LIKE ?", (f"{m_str}%",))
                    r = c.fetchone()
                    cnt_den = r[0] or 0
                    qty_den = r[1] or 0
                    rev_den = r[2] or 0
                    conn.close()
                except: pass

            tot_rev = rev_bh + rev_den
            tot_cnt = cnt_bh + cnt_den
            order_text = f"**{tot_cnt} đơn**" if ts['is_order_count'] else f"**{tot_rev:,.0f} đ** ({tot_cnt} đơn)"

            return {
                "type": "clarify",
                "message": (
                    f"💡 Bạn muốn xem dữ liệu **Tháng {m_target} của năm nào** ạ?\n"
                    f"─────────────────────────────────────────\n"
                    f"Hệ thống ghi nhận dữ liệu Tháng {m_target} các năm: **2024, 2025, 2026**.\n"
                    f"👉 *Bạn có thể gõ rõ hơn, ví dụ: `tháng {m_target} năm 2026` hoặc gõ số năm `2026`.*\n\n"
                    f"📊 **Số liệu tạm tính Tháng {m_target}/{preview_yr} (năm gần nhất):**\n"
                    f"• Tổng toàn cửa hàng: {order_text}\n"
                    f"  - 📦 Bán Hàng: {rev_bh:,.0f} đ ({cnt_bh} đơn)\n"
                    f"  - 💡 Đèn: {rev_den:,.0f} đ ({cnt_den} đơn / {qty_den} bộ)"
                )
            }

        # Nếu có năm (hoặc nhiều tháng thì mặc định lấy 2026 nếu không nói năm)
        year_target = ts['year'] if ts['year'] else 2026
        months_list = sorted(ts['months'])

        total_bh_rev = 0
        total_bh_orders = 0
        total_den_rev = 0
        total_den_orders = 0
        total_den_qty = 0

        detail_lines = []

        for m in months_list:
            m_str = f"{year_target}-{m:02d}"
            cnt_bh, rev_bh = 0, 0
            if os.path.exists(DB_BANHANG):
                try:
                    conn = sqlite3.connect(DB_BANHANG, timeout=5)
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date LIKE ?", (f"{m_str}%",))
                    r = c.fetchone()
                    cnt_bh = r[0] or 0
                    rev_bh = r[1] or 0
                    conn.close()
                except: pass

            cnt_den, qty_den, rev_den = 0, 0, 0
            if os.path.exists(DB_DEN):
                try:
                    conn = sqlite3.connect(DB_DEN, timeout=5)
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k * 1000) FROM orders WHERE order_date LIKE ?", (f"{m_str}%",))
                    r = c.fetchone()
                    cnt_den = r[0] or 0
                    qty_den = r[1] or 0
                    rev_den = r[2] or 0
                    conn.close()
                except: pass

            total_bh_rev += rev_bh
            total_bh_orders += cnt_bh
            total_den_rev += rev_den
            total_den_orders += cnt_den
            total_den_qty += qty_den

            m_tot_rev = rev_bh + rev_den
            m_tot_cnt = cnt_bh + cnt_den

            if ts['scope'] == 'banhang':
                detail_lines.append(f"🔹 **Tháng {m:02d}/{year_target}:** **{rev_bh:,.0f} đ** ({cnt_bh} đơn bán hàng)")
            elif ts['scope'] == 'den':
                detail_lines.append(f"🔹 **Tháng {m:02d}/{year_target}:** **{rev_den:,.0f} đ** ({cnt_den} đơn / {qty_den} bộ đèn)")
            else:
                detail_lines.append(
                    f"🔹 **Tháng {m:02d}/{year_target}:** **{m_tot_rev:,.0f} đ** ({m_tot_cnt} đơn)\n"
                    f"   • Bán Hàng Phụ Kiện: **{rev_bh:,.0f} đ** ({cnt_bh} đơn)\n"
                    f"   • Báo Cáo Đèn: **{rev_den:,.0f} đ** ({cnt_den} đơn / {qty_den} bộ)"
                )

        grand_tot_rev = total_bh_rev + total_den_rev
        grand_tot_cnt = total_bh_orders + total_den_orders

        months_str = " & ".join(f"Tháng {m}" for m in months_list)

        # Nếu người dùng hỏi số lượng đơn hàng:
        if ts['is_order_count']:
            if ts['scope'] == 'banhang':
                reply = (
                    f"📦 **SỐ LƯỢNG ĐƠN BÁN HÀNG ({months_str}/{year_target}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Tổng số đơn: **{total_bh_orders} đơn hàng** (Doanh thu: **{total_bh_rev:,.0f} đ**)\n\n"
                    + "\n".join(detail_lines) + "\n\n"
                    f"👉 [Xem chi tiết Bán Hàng](/banhang/)"
                )
            elif ts['scope'] == 'den':
                reply = (
                    f"💡 **SỐ LƯỢNG ĐƠN ĐÈN ({months_str}/{year_target}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Tổng số đơn: **{total_den_orders} đơn** ({total_den_qty} bộ đèn | Doanh thu: **{total_den_rev:,.0f} đ**)\n\n"
                    + "\n".join(detail_lines) + "\n\n"
                    f"👉 [Xem chi tiết Báo Cáo Đèn](/den/)"
                )
            else:
                reply = (
                    f"📊 **SỐ LƯỢNG ĐƠN TOÀN CỬA HÀNG ({months_str}/{year_target}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"📦 **TỔNG SỐ ĐƠN:** **{grand_tot_cnt} đơn hàng** *(Doanh thu: **{grand_tot_rev:,.0f} đ**)*\n\n"
                    f"📋 **CHI TIẾT THEO TỪNG THÁNG:**\n"
                    + "\n".join(detail_lines) + "\n"
                    f"─────────────────────────────────────────\n"
                    f"🏆 **TỔNG KẾT THEO PHÂN HỆ:**\n"
                    f"• 📦 Bán Hàng Phụ Kiện: **{total_bh_orders} đơn** ({total_bh_rev:,.0f} đ)\n"
                    f"• 💡 Báo Cáo Đèn: **{total_den_orders} đơn** ({total_den_qty} bộ | {total_den_rev:,.0f} đ)\n\n"
                    f"👉 [Xem Bán Hàng](/banhang/) | [Xem Báo Cáo Đèn](/den/)"
                )
            return {"type": "success", "message": reply}

        # Nếu người dùng hỏi doanh thu:
        if ts['scope'] == 'banhang':
            reply = (
                f"📦 **BÁO CÁO DOANH THU BÁN HÀNG ({months_str}/{year_target}):**\n"
                f"─────────────────────────────────────────\n"
                f"💰 **TỔNG DOANH SỐ:** **{total_bh_rev:,.0f} đ** *({total_bh_orders} đơn hàng)*\n\n"
                + "\n".join(detail_lines) + "\n\n"
                f"👉 [Xem chi tiết Bán Hàng](/banhang/)"
            )
        elif ts['scope'] == 'den':
            reply = (
                f"💡 **BÁO CÁO DOANH THU ĐÈN ({months_str}/{year_target}):**\n"
                f"─────────────────────────────────────────\n"
                f"💰 **TỔNG DOANH SỐ:** **{total_den_rev:,.0f} đ** *({total_den_orders} đơn / {total_den_qty} bộ)*\n\n"
                + "\n".join(detail_lines) + "\n\n"
                f"👉 [Xem chi tiết Báo Cáo Đèn](/den/)"
            )
        else:
            reply = (
                f"📊 **BÁO CÁO TỔNG DOANH THU CỬA HÀNG ({months_str}/{year_target}):**\n"
                f"─────────────────────────────────────────\n"
                f"💰 **TỔNG DOANH THU TOÀN CỬA HÀNG:** **{grand_tot_rev:,.0f} đ** *({grand_tot_cnt} đơn)*\n\n"
                f"📋 **CHI TIẾT THEO TỪNG THÁNG:**\n"
                + "\n".join(detail_lines) + "\n"
                f"─────────────────────────────────────────\n"
                f"🏆 **TỔNG KẾT THEO PHÂN HỆ ({months_str}/{year_target}):**\n"
                f"• 📦 **Bán Hàng Phụ Kiện:** **{total_bh_rev:,.0f} đ** ({total_bh_orders} đơn)\n"
                f"• 💡 **Nâng Cấp Ánh Sáng (Đèn):** **{total_den_rev:,.0f} đ** ({total_den_orders} đơn / {total_den_qty} bộ)\n\n"
                f"👉 [Xem Bán Hàng](/banhang/) | [Xem Báo Cáo Đèn](/den/) | [Xem Sổ Thu Chi](/thuchi/)"
            )
        return {"type": "success", "message": reply}

    return None


def handle_summary_stats(raw_text, clean_text):
    """Báo cáo tổng hợp số dư quỹ, doanh thu hôm nay"""
    is_stat = bool(re.search(r'\b(tong ket|so du|con bao nhieu tien|quy tien|doanh thu|hom nay|bao cao nhanh)\b', clean_text))
    if not is_stat:
        return None

    balance_str = "0 đ"
    income_str = "0 đ"
    expense_str = "0 đ"
    period_name = "Chưa có kỳ"

    if os.path.exists(DB_THUCHI):
        try:
            conn = sqlite3.connect(DB_THUCHI, timeout=10)
            c = conn.cursor()
            c.execute("SELECT id, name FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1")
            p = c.fetchone()
            if p:
                period_name = p[1]
                c.execute("SELECT SUM(CASE WHEN type='thu' THEN amount ELSE 0 END), SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) FROM transactions WHERE period_id = ?", (p[0],))
                row = c.fetchone()
                inc = row[0] or 0
                exp = row[1] or 0
                income_str = f"{inc:,.0f} đ"
                expense_str = f"{exp:,.0f} đ"
                balance_str = f"{(inc - exp):,.0f} đ"
            conn.close()
        except:
            pass

    today_str = datetime.now().strftime('%Y-%m-%d')
    orders_count = 0
    orders_total = 0
    if os.path.exists(DB_BANHANG):
        try:
            conn = sqlite3.connect(DB_BANHANG, timeout=10)
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date = ?", (today_str,))
            r = c.fetchone()
            orders_count = r[0] or 0
            orders_total = r[1] or 0
            conn.close()
        except:
            pass

    msg = f"📊 **BÁO CÁO TỔNG QUAN HỆ THỐNG TRẦN BÌNH AUTO**\n\n"
    msg += f"💰 **SỔ QUỸ TIỀN MẶT ({period_name}):**\n"
    msg += f"• Tổng thu: **+{income_str}**\n"
    msg += f"• Tổng chi: **-{expense_str}**\n"
    msg += f"• **SỐ DƯ QUỸ HIỆN CÒN:** **{balance_str}**\n\n"
    msg += f"📦 **ĐƠN BÁN HÀNG HÔM NAY ({datetime.now().strftime('%d/%m/%Y')}):**\n"
    msg += f"• Số đơn ra hôm nay: **{orders_count} đơn**\n"
    msg += f"• Tổng doanh số: **{orders_total:,.0f} đ**\n\n"
    msg += "👉 [Xem Sổ Thu Chi](/thuchi/) | [Xem Bán Hàng](/banhang/) | [Xem Báo Cáo Đèn](/den/)"
    return {"type": "success", "message": msg}

# ─────────────────────────────────────────────────────────────────────────────
# 6.5. CHUYÊN GIA TƯ VẤN DỊCH VỤ GARA (PHIM CÁCH NHIỆT, TRẦN, MÀN HÌNH, BOX, CAM, GHẾ DA)
# ─────────────────────────────────────────────────────────────────────────────

# -*- coding: utf-8 -*-
import re

def handle_gara_consultation(raw_text, clean_text):
    """
    TRỢ LÝ TƯ VẤN BÁN HÀNG TẬP TRUNG & NGẮN GỌN - GARA TRẦN BÌNH AUTO:
    Trả lời ĐÚNG TRỌNG TÂM - CỰC KỲ SÚC TÍCH - KHÔNG DÔNG DÀI
    """

    # ═════════════════════════════════════════════════════════════════════════
    # 0. MẪU TIN NHẮN BÁO GIÁ SOẠN SẴN GỬI KHÁCH (COPY - PASTE GỬI ZALO/FB)
    # ═════════════════════════════════════════════════════════════════════════
    is_template = bool(re.search(r'\b(mau|mau bao gia|mau tin nhan|script|gui khach|mau gui|tin nhan bao gia)\b', clean_text))
    if is_template:
        if any(k in clean_text for k in ['film', 'phim', 'cach nhiet']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📋 **MẪU TIN NHẮN BÁO GIÁ PHIM CÁCH NHIỆT (GỬI KHÁCH):**\n"
                    "Dạ em gửi Anh/Chị bảng giá phim cách nhiệt chính hãng chống nóng tại **Trần Bình Auto**:\n"
                    "• **Ntech Tiêu Chuẩn + Kính lái Ceramax:** Sedan **5.6tr** | SUV **6.1tr** (BH 10 năm - Bán chạy)\n"
                    "• **Ntech Cao Cấp + Kính lái Ceramax:** Sedan **6.5tr** | SUV **7.4tr** (BH 10 năm)\n"
                    "• **Ceramax Diamond Full Xe (Men gốm siêu cách nhiệt):** Sedan **9.5tr** | SUV **11.3tr** (BH 15 năm)\n"
                    "• **3M Crystalline Mỹ (200 lớp quang học):** Sedan **10.8tr - 14.8tr** | SUV **12.5tr - 17.6tr** (BH 10 năm)\n"
                    "🎁 *Ưu đãi:* Tặng 100% công lột phim cũ và vệ sinh keo sạch (500k). Kính lái đạt chuẩn đăng kiểm >50% VLT.\n"
                    "👉 Xe mình là dòng xe gì để em xếp lịch phục vụ chu đáo nhất ạ?"
                )
            }
        if any(k in clean_text for k in ['man hinh', 'man', 'dvd', 'cam 360']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📋 **MẪU BÁO GIÁ MÀN HÌNH ANDROID (GỬI KHÁCH):**\n"
                    "Dạ em gửi Anh/Chị bảng giá màn hình Android thông minh chính hãng:\n"
                    "• **Bravo B10 Lite:** **5.5tr** (Tặng Vietmap Live 2 năm + Mặt dưỡng theo xe)\n"
                    "• **Winca S150+:** **6.5tr** (Tặng Vietmap Live 2 năm + Sim 4G + Cam lùi AHD)\n"
                    "• **Gotech GT2K New:** **9.6tr** (Màn 2K chống lóa, BH 2 năm 1 đổi 1)\n"
                    "• **Màn hình liền Cam 360 độ:** Winca S170+ Pro **11.8tr** | Gotech GC360 **12.9tr**\n"
                    "🔧 Cắm giắc zin 100% giữ bảo hành hãng. Anh/Chị cho em xin đời xe để chọn mặt dưỡng chuẩn nhé!"
                )
            }
        if any(k in clean_text for k in ['cam', 'hanh trinh', 'camera']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📋 **MẪU BÁO GIÁ CAMERA HÀNH TRÌNH (GỬI KHÁCH):**\n"
                    "• **Vietmap M1 2K (Trước + Sau):** **6.19tr** *(Luôn hiển thị tốc độ giới hạn + Báo phạt nguội - Bán chạy nhất)*\n"
                    "• **Vietmap M2 4K:** **8.98tr** *(Xem video & định vị từ xa qua 4G 24/24)*\n"
                    "• **70mai A200 2K:** **2.5tr** (Trước + Sau, tặng thẻ 32GB - Ngon bổ rẻ)\n"
                    "• **70mai A510 3K:** **3.4tr** (Cảm biến Sony Starvis 2 quay đêm siêu sáng, tặng thẻ 64GB)\n"
                    "• **70mai A800SE 4K:** **3.6tr** (Bản 4K trước sau, tặng thẻ 64GB)\n"
                    "🎁 Miễn phí công lắp đặt đi dây âm kín thẩm mỹ 100% tại gara ạ!"
                )
            }

    # ═════════════════════════════════════════════════════════════════════════
    # 1. KỊCH BẢN XỬ LÝ TỪ CHỐI (NGẮN GỌN - ĐÚNG Ý)
    # ═════════════════════════════════════════════════════════════════════════
    if any(k in clean_text for k in ['che dat', 'dat qua', 'sao dat the', 'gia cao the']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "🎯 **KỊCH BẢN TƯ VẤN KHI KHÁCH CHÊ ĐẮT:**\n"
                "1. Khẳng định: *'Bên em làm trọn gói cắm giắc zin 100%, bảo hành điện tử chính hãng từ 2 - 15 năm lỗi là 1 đổi 1 ạ.'*\n"
                "2. Quà tặng: Tặng công lột keo cũ 500k; lắp màn hình tặng cam lùi, mặt dưỡng và Vietmap Live 2 năm.\n"
                "3. Hạ bậc khéo léo: Khách chê 3M đắt ➔ Chuyển qua **Ntech + Kính lái Ceramax (chỉ 5.6tr - 6.1tr)** vừa mát vừa tiết kiệm một nửa tiền!"
            )
        }

    if any(k in clean_text for k in ['dang kiem', 'kiem dinh', 'co bi phat khong', 'bi bat khong']) or ('do xuyen sang' in clean_text and not any(m in clean_text for m in ['nr', 'nr5', 'nr15', 'nr25', 'nr35', 'cr50', 'ceramax'])):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "🔍 **QUY ĐỊNH ĐĂNG KIỂM PHIM CÁCH NHIỆT MỚI:**\n"
                "• **Kính Lái:** Quy định mới yêu cầu độ xuyên sáng **> 50%**. Gara dùng **CR50BLK (50%)** và **CeraMAX 50 (59.7%)** bao đăng kiểm 100% toàn quốc! (Gara không nhập CR40BLK).\n"
                "• **Kính Sườn & Hậu:** Tự do dán màu tối để riêng tư và chống chói, đăng kiểm không cấm."
            )
        }

    if any(k in clean_text for k in ['mat bao hanh', 'mat zin', 'cat day', 'cat trich']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "🛡️ **CAM KẾT BẢO HÀNH ZIN XE:**\n"
                "• 100% sử dụng **giắc cắm zin chuyên dụng theo xe**, tuyệt đối KHÔNG cắt trích dây điện.\n"
                "• Đấu nguồn qua cầu chì phụ Fuse Tap an toàn, bảo lưu 100% chế độ bảo hành của hãng xe."
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 2. SO SÁNH SẢN PHẨM (TRẢ LỜI ĐÚNG TRỌNG TÂM)
    # ═════════════════════════════════════════════════════════════════════════
    is_compare = bool(re.search(r'\b(so sanh|nen chon|nen lap|nen dung|khac nhau|loai nao hon|loai nao tot|nen mua)\b', clean_text))
    
    if is_compare and any(k in clean_text for k in ['box', 'android box']) and any(k in clean_text for k in ['man hinh', 'man']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚖️ **NÊN LẮP MÀN HÌNH HAY ANDROID BOX?**\n"
                "• **Chọn Android Box (6tr - 8.4tr):** Khi xe đời mới màn hình zin to đẹp, loa hay, muốn giữ zin 100% chỉ cần cắm USB/Type-C.\n"
                "• **Chọn Màn Hình Android (5.5tr - 11.8tr):** Khi xe màn hình bé/cũ, hoặc muốn **lắp Camera 360 độ toàn cảnh** xóa điểm mù."
            )
        }

    if is_compare and any(k in clean_text for k in ['70mai', 'xiaomi']) and any(k in clean_text for k in ['vietmap']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚖️ **CHỌN CAMERA 70MAI HAY VIETMAP?**\n"
                "• **Chọn Vietmap (M1 giá 6.19tr):** Chuyên gia cảnh báo tốc độ giới hạn, nhắc phạt nguội, cấm vượt chuẩn nhất VN cho ai hay đi tỉnh/cao tốc.\n"
                "• **Chọn 70mai (A200 2.5tr, A510 3.4tr):** Chuyên gia độ nét (2K-3K), cảm biến Sony quay đêm sáng rõ, giá mềm hơn."
            )
        }

    if is_compare and any(k in clean_text for k in ['da', 'ghe', 'boc ghe', 'simili', 'cong nghiep', 'nappa']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚖️ **SO SÁNH CÁC LOẠI DA BỌC GHẾ:**\n"
                "• **Da Simili (3.5tr - 6tr):** Giá rẻ, chống nước tốt, thích hợp xe chạy dịch vụ.\n"
                "• **Da Công Nghiệp (6tr - 7.5tr - Bán chạy nhất):** Mềm mịn, không mùi, bền 4-5 năm, tối ưu cho xe gia đình.\n"
                "• **Da Nappa (9.5tr - 12tr):** Cực êm ái, mát tay, đẳng cấp xe sang (đục lỗ thoát khí +1tr)."
            )
        }

    if is_compare and any(k in clean_text for k in ['3m', 'crystalline']) and any(k in clean_text for k in ['ceramax', 'ntech']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚖️ **SO SÁNH: 3M CRYSTALLINE VS CERAMAX DIAMOND:**\n"
                "• **3M Crystalline Mỹ (10.8tr - 17.6tr):** 200 lớp quang học, thương hiệu số 1 toàn cầu, chống chói ban đêm tốt nhất, BH 10 năm.\n"
                "• **CeraMAX Diamond (9.5tr - 11.3tr):** Men gốm sinh học cản hồng ngoại IR 99.1%, giá tiết kiệm hơn 30-40%, BH 15 năm dài nhất thị trường."
            )
        }

    # So sánh các dòng 3M (Ceramic NR vs Ceramic IR vs Crystalline)
    if is_compare and ('3m' in clean_text or 'nr' in clean_text) and any(k in clean_text for k in ['nr', 'hybrid', 'ir', 'crystalline']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚖️ **SO SÁNH 3 DÒNG PHIM 3M CHÍNH HÃNG MỸ:**\n"
                "1️⃣ **3M Ceramic NR (Ceramic Hybrid - Giá tốt nhất):**\n"
                "  • Trọn gói: MiniCar **5.9tr** | Sedan **7.9tr** | SUV **9.5tr** (Kính lái dán lẻ: **2.6tr**)\n"
                "  • Công nghệ men gốm lai phản xạ nhiệt (Nano Ceramic + Nano Reflective), cản nhiệt TSER đến 69%, giảm chói tới 93%.\n"
                "  • Tông màu tối tăng độ riêng tư cabin, bảo hành điện tử chính hãng 10 năm.\n"
                "2️⃣ **3M Ceramic IR (Men gốm cao cấp):**\n"
                "  • Trọn gói: Sedan **9.0tr** | SUV **10.5tr**. Độ trong suốt cao hơn, cản hồng ngoại IR vượt trội.\n"
                "3️⃣ **3M Crystalline (Đỉnh cao quang học 200 lớp):**\n"
                "  • Trọn gói: Sedan **10.8tr - 14.8tr** | SUV **12.5tr - 17.6tr** (Kính lái CR50BLK: **5.7tr**)\n"
                "  • Chống chói ban đêm và đi mưa rõ nhất thế giới, cản IR 98% tuyệt đối."
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 3. HỎI SẢN PHẨM / VỊ TRÍ CỤ THỂ (TRẢ LỜI NGAY TRONG 3-5 DÒNG)
    # ═════════════════════════════════════════════════════════════════════════

    # 3.1. Kính lái CeraMAX 50 (HỎI RIÊNG KÍNH LÁI CERAMAX)
    if bool(re.search(r'\b(kinh lai ceramax|lai ceramax|ceramax 50|gia kinh lai ceramax)\b', clean_text)) and not any(k in clean_text for k in ['ket hop', 'suon', 'ntech', 'con lai']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **KÍNH LÁI CERAMAX 50 (MEN GỐM CAO CẤP):**\n"
                "• **Giá dán lẻ:** **3.300.000 đ**\n"
                "• **Thông số kỹ thuật:** Xuyên sáng `59.7%` (rất trong, an toàn đi đêm) | Cắt tia hồng ngoại IR `99.1%` (cực mát) | Cắt UV `99.9%`\n"
                "• **Bảo hành:** **15 năm chính hãng**\n"
                "• **Đăng kiểm:** Đạt chuẩn lưu hành (>50% độ truyền sáng)."
            )
        }

    # 3.2. Kính lái 3M (HỎI RIÊNG KÍNH LÁI 3M: CÓ 2 LOẠI 2.6TR VÀ 5.7TR)
    is_single_3m_windshield = (
        bool(re.search(r'\b(cr50|cr50blk|cr 50)\b', clean_text)) or
        (bool(re.search(r'\b(kinh lai 3m|lai 3m|gia le kinh lai 3m|kinh 3m truoc|3m kinh lai)\b', clean_text)) and not any(k in clean_text for k in ['ket hop', 'suon', 'ntech', 'con lai', 'ceramax'])) or
        ('3m' in clean_text and any(k in clean_text for k in ['lai', 'kinh truoc']) and any(k in clean_text for k in ['2.6', '2tr6', '2600', 're', 'gia re']))
    )
    if is_single_3m_windshield:
        is_asking_cheap = any(k in clean_text for k in ['re', '2.6', '2tr6', '2600', 'ceramic', 'tiet kiem'])
        is_asking_cr50 = any(k in clean_text for k in ['cr50', 'cr50blk', 'crystalline', 'cao cap', 'dinh cao', '5.7', '5tr7'])

        if is_asking_cheap and not is_asking_cr50:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **KÍNH LÁI 3M CERAMIC (BẢN TIẾT KIỆM / GIÁ RẺ):**\n"
                    "• **Giá dán lẻ:** **2.600.000 đ**\n"
                    "• **Công nghệ:** Men gốm Nano Ceramic chính hãng 3M USA\n"
                    "• **Thông số:** Xuyên sáng `50% - 60%` (chuẩn kiểm định mới) | Cắt IR `80% - 85%` | Cắt UV `99%` | Không cản sóng ETC/GPS\n"
                    "• **Bảo hành:** **10 năm điện tử chính hãng 3M USA**\n"
                    "👉 Phù hợp cho khách thích thương hiệu 3M Mỹ nhưng muốn chi phí tiết kiệm, kinh tế!"
                )
            }
        elif is_asking_cr50 and not is_asking_cheap:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **KÍNH LÁI 3M CRYSTALLINE CR50BLK (MỸ - CAO CẤP NHẤT):**\n"
                    "• **Giá dán lẻ:** **5.700.000 đ**\n"
                    "• **Thông số:** Xuyên sáng `50%` (chuẩn kiểm định mới) | Cắt IR `98%` | Cắt UV `99.9%` | Giảm lóa `34%`\n"
                    "• **Bảo hành:** **10 năm điện tử chính hãng 3M USA**\n"
                    "• **Đăng kiểm:** Dùng mã CR50BLK đạt chuẩn >50% VLT, gara không nhập mã CR40BLK.\n"
                    "💡 *Mẹo:* Nếu khách cần loại 3M kính lái giá rẻ hơn, gara có thêm mã **3M Ceramic kính lái: 2.600.000 đ**."
                )
            }
        else:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **BÁO GIÁ KÍNH LÁI 3M CHÍNH HÃNG MỸ (2 LỰA CHỌN):**\n"
                    "1️⃣ **3M Ceramic Kính Lái (Bản Tiết Kiệm):** **2.600.000 đ**\n"
                    "  • Công nghệ men gốm Nano Ceramic, xuyên sáng >50% đạt chuẩn đăng kiểm, cắt UV 99%, không cản sóng ETC/GPS.\n"
                    "  • Bảo hành 10 năm điện tử 3M.\n"
                    "2️⃣ **3M Crystalline CR50BLK (Bản Đỉnh Cao Nhất):** **5.700.000 đ**\n"
                    "  • Công nghệ quang học 200 lớp độc quyền 3M USA, cắt tia hồng ngoại IR `98%`, cản nhiệt tuyệt đối, giảm chói 34%.\n"
                    "  • Mã CR50BLK xuyên sáng 50% bao đăng kiểm toàn quốc (gara không nhập CR40BLK).\n"
                    "🎁 Tặng 100% công lột keo cũ và vệ sinh sạch sẽ (trị giá 500k)."
                )
            }

    # 3.2.b. TRA CỨU CHI TIẾT DÒNG 3M CERAMIC NR / CERAMIC HYBRID (NR5, NR15, NR25, NR35)
    is_3m_nr_query = bool(re.search(r'\b(nr5|nr15|nr25|nr35|nr 5|nr 15|nr 25|nr 35|ceramic nr|ceramic hybrid|3m nr|3m hybrid)\b', clean_text))
    if is_3m_nr_query:
        # Nếu hỏi riêng mã NR35
        if 'nr35' in clean_text or ('nr 35' in clean_text):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **MÃ PHIM 3M CERAMIC NR35 (CHUYÊN KÍNH LÁI):**\n"
                    "• **Giá dán lẻ kính lái:** **2.600.000 đ** (BH 10 năm điện tử 3M)\n"
                    "• **Độ truyền sáng (VLT):** `43%` (trong vừa, quan sát rõ ngày và đêm)\n"
                    "• **Tổng cản nhiệt (TSER):** `51%` | **Cản hồng ngoại (IRR):** `79%` (IRER 58%)\n"
                    "• **Cản tia cực tím (UVR):** `99%` | **Giảm độ chói:** `52%`\n"
                    "• **Ưu điểm:** Công nghệ lai Nano Ceramic + Nano Reflective không cản sóng GPS, VETC, Bluetooth, Android Box."
                )
            }
        # Nếu hỏi riêng mã NR5
        if 'nr5' in clean_text or ('nr 5' in clean_text):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **MÃ PHIM 3M CERAMIC NR5 (SIÊU TỐI - RIÊNG TƯ - CHỐNG NÓNG ĐỈNH):**\n"
                    "• **Vị trí khuyên dùng:** Kính sườn sau, kính hậu, cửa sổ trời (KHÔNG dán kính lái)\n"
                    "• **Giá dán lẻ:** Kính sườn **1.700.000 đ/cặp** | Kính hậu **1.900.000 đ** | Cửa sổ trời **850.000 đ**\n"
                    "• **Độ truyền sáng (VLT):** `7%` (rất tối từ ngoài nhìn vào, bên trong nhìn ra rõ)\n"
                    "• **Tổng cản nhiệt (TSER):** `69%` (cao nhất dòng NR) | **Cản hồng ngoại (IRR):** `91%` (IRER 68%)\n"
                    "• **Giảm chói lóa:** `93%` | **Cắt tia UV:** `99%` | **Bảo hành:** 10 năm chính hãng."
                )
            }
        # Nếu hỏi riêng mã NR15
        if 'nr15' in clean_text or ('nr 15' in clean_text):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **MÃ PHIM 3M CERAMIC NR15 (KÍNH SƯỜN & KÍNH HẬU TIÊU CHUẨN):**\n"
                    "• **Vị trí khuyên dùng:** Kính sườn trước/sau, kính hậu (cân bằng cách nhiệt & riêng tư)\n"
                    "• **Giá dán lẻ:** Kính sườn **1.700.000 đ/cặp** | Kính hậu **1.900.000 đ**\n"
                    "• **Độ truyền sáng (VLT):** `14%` | **Tổng cản nhiệt (TSER):** `65%`\n"
                    "• **Cản hồng ngoại (IRR):** `86%` (IRER 66%) | **Giảm chói:** `84%` | **Cắt UV:** `99%`\n"
                    "• **Bảo hành:** 10 năm điện tử chính hãng 3M."
                )
            }
        # Nếu hỏi riêng mã NR25
        if 'nr25' in clean_text or ('nr 25' in clean_text):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **MÃ PHIM 3M CERAMIC NR25 (KÍNH SƯỜN CHO NGƯỜI THÍCH SÁNG):**\n"
                    "• **Vị trí khuyên dùng:** Kính sườn trước (giúp nhìn gương chiếu hậu ban đêm rõ ràng), sườn sau\n"
                    "• **Giá dán lẻ:** Kính sườn **1.700.000 đ/cặp**\n"
                    "• **Độ truyền sáng (VLT):** `29%` | **Tổng cản nhiệt (TSER):** `59%`\n"
                    "• **Cản hồng ngoại (IRR):** `86%` (IRER 63%) | **Giảm chói:** `68%` | **Cắt UV:** `99%`\n"
                    "• **Bảo hành:** 10 năm điện tử chính hãng 3M."
                )
            }
        # Hỏi riêng kính sườn 3M NR
        if any(k in clean_text for k in ['suon', 'kinh suon']) and not any(k in clean_text for k in ['hau', 'lai', 'tron xe']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **KÍNH SƯỜN 3M CERAMIC NR (CHÍNH HÃNG 3M USA):**\n"
                    "• **Giá dán lẻ:** **1.700.000 đ / cặp** (Sedan 4 cánh = 2 cặp = 3.4tr)\n"
                    "• **Tùy chọn phối mã khuyên dùng:**\n"
                    "  - Sườn trước: Đi mã `NR25` (xuyên sáng 29%) để quan sát gương chiếu hậu ban đêm rõ ràng.\n"
                    "  - Sườn sau: Đi mã `NR15` (xuyên sáng 14%) hoặc `NR5` (xuyên sáng 7%) để chống nóng tối đa và riêng tư tuyệt đối.\n"
                    "• **Bảo hành:** 10 năm điện tử 3M chính hãng."
                )
            }

        # Hỏi riêng kính hậu / kính sau 3M NR
        if any(k in clean_text for k in ['hau', 'kinh hau', 'kinh sau', 'lung']) and not any(k in clean_text for k in ['lai', 'suon', 'tron xe']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **KÍNH HẬU / KÍNH SAU 3M CERAMIC NR:**\n"
                    "• **Giá dán lẻ:** **1.900.000 đ**\n"
                    "• **Mã phim khuyên dùng:** `NR15` (cản nhiệt 65%) hoặc `NR5` (cản nhiệt 69%, giảm chói 93% khi xe sau chiếu pha).\n"
                    "• **Bảo hành:** 10 năm điện tử chính hãng 3M."
                )
            }

        # Hỏi riêng cửa sổ trời 3M NR
        if any(k in clean_text for k in ['cua so troi', 'sunroof', 'panorama']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **CỬA SỔ TRỜI 3M CERAMIC NR:**\n"
                    "• **Giá dán lẻ:** **850.000 đ**\n"
                    "• **Mã phim khuyên dùng:** `NR5` (chống nóng đỉnh cao TSER 69%, giảm chói 93% ngăn tia nắng gắt trên nóc xe rọi xuống cabin).\n"
                    "• **Bảo hành:** 10 năm điện tử chính hãng 3M."
                )
            }

        # Hỏi tổng quan dòng 3M Ceramic NR / Ceramic Hybrid
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **PHIM CÁCH NHIỆT 3M CERAMIC NR (CERAMIC HYBRID THẾ HỆ MỚI):**\n"
                "• **Công nghệ:** Lai giữa men gốm Nano Ceramic + Nano Reflective phản xạ nhiệt, tản nhiệt cực nhanh.\n"
                "• **Bảng giá trọn xe:**\n"
                "  - **MiniCar (VF3, Morning, i10):** **5.900.000 đ**\n"
                "  - **Sedan (4 - 5 chỗ):** **7.900.000 đ**\n"
                "  - **SUV (7 chỗ):** **9.500.000 đ**\n"
                "• **Giá dán lẻ từng vị trí:**\n"
                "  - Kính lái (NR35): **2.600.000 đ** (VLT 43%, TSER 51%, cản UV 99%)\n"
                "  - Kính sườn (NR25/15/5): **1.700.000 đ/cặp** | Kính hậu: **1.900.000 đ** | Cửa sổ trời: **850.000 đ**\n"
                "• **4 Mã phim phối xe:**\n"
                "  - `NR35` (Lái): Xuyên sáng 43%, cản nhiệt 51%\n"
                "  - `NR25` (Sườn trước sáng): Xuyên sáng 29%, cản nhiệt 59%\n"
                "  - `NR15` (Sườn tối vừa): Xuyên sáng 14%, cản nhiệt 65%\n"
                "  - `NR5` (Sườn sau/hậu siêu tối riêng tư): Xuyên sáng 7%, cản nhiệt 69%, giảm chói 93%\n"
                "🎁 Miễn phí 100% công lột keo cũ 500k. Kích hoạt bảo hành điện tử 3M e-Warranty 10 năm toàn quốc."
            )
        }

    # 3.3. Hỏi riêng Kính Sườn / Kính Hậu Ceramax
    if bool(re.search(r'\b(suon ceramax|kinh suon ceramax|hau ceramax|kinh hau ceramax)\b', clean_text)) and not any(k in clean_text for k in ['3m', 'ntech']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **KÍNH SƯỜN & HẬU CERAMAX DIAMOND:**\n"
                "• **Kính sườn (20/10/05):** **2.000.000 đ / cặp** (Sedan 2 cặp: 4.000.000 đ)\n"
                "• **Kính hậu:** **2.200.000 đ**  |  **Ô chết khoang sau SUV:** **1.800.000 đ**\n"
                "• **Thông số & BH:** Cắt tia IR đến `99.1%`, cản UV `99.9%`, bảo hành **15 năm chính hãng**."
            )
        }

    # 3.4. Hỏi riêng Kính Sườn / Kính Hậu Ntech
    if bool(re.search(r'\b(suon ntech|kinh suon ntech|hau ntech|kinh hau ntech)\b', clean_text)) and not any(k in clean_text for k in ['3m', 'ceramax', 'lai']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **KÍNH SƯỜN & HẬU NTECH (HÀN QUỐC - BH 10 NĂM):**\n"
                "• **Bản Tiêu Chuẩn:** Sườn trước **700k** | Sườn sau **700k** | Hậu **900k** | Ô chết SUV **500k**\n"
                "• **Bản Cao Cấp:** Sườn trước **1.000k** | Sườn sau **1.000k** | Hậu **1.200k** | Ô chết SUV **900k**"
            )
        }

    # 3.5. Gói riêng Ntech Tiêu Chuẩn full xe
    if bool(re.search(r'\b(ntech tieu chuan|goi ntech tieu chuan)\b', clean_text)) and not any(k in clean_text for k in ['3m']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **GÓI NTECH TIÊU CHUẨN + KÍNH LÁI CERAMAX (BÁN CHẠY NHẤT):**\n"
                "• **Xe Sedan (4 - 5 chỗ):** **5.600.000 đ**\n"
                "• **Xe SUV (7 chỗ):** **6.100.000 đ**\n"
                "• *Cấu hình:* Kính lái CeraMAX 50 gốm sinh học + Sườn và Hậu Ntech Tiêu Chuẩn tối màu riêng tư mát mẻ. Bảo hành 10 năm."
            )
        }

    # 3.6. Gói riêng Ntech Cao Cấp full xe
    if bool(re.search(r'\b(ntech cao cap|goi ntech cao cap)\b', clean_text)) and not any(k in clean_text for k in ['3m']):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **GÓI NTECH CAO CẤP + KÍNH LÁI CERAMAX:**\n"
                "• **Xe Sedan (4 - 5 chỗ):** **6.500.000 đ**\n"
                "• **Xe SUV (7 chỗ):** **7.400.000 đ**\n"
                "• *Cấu hình:* Kính lái CeraMAX 50 + Sườn và Hậu Ntech Cao Cấp tăng cường cản nhiệt và giảm lóa. Bảo hành 10 năm."
            )
        }

    # 3.7. Gói riêng CeraMAX Diamond full xe
    if bool(re.search(r'\b(ceramax diamond|ceramax full|full ceramax)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "💎 **GÓI SIÊU CÁCH NHIỆT CERAMAX DIAMOND FULL XE:**\n"
                "• **Xe Sedan (4 - 5 chỗ):** **9.500.000 đ**\n"
                "• **Xe SUV (7 chỗ):** **11.300.000 đ**\n"
                "• *Đặc tính:* Men gốm sinh học 100% full xe, cản hồng ngoại IR 99.1%, cản UV 99.9%. Bảo hành chính hãng **15 NĂM**."
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 4. TƯ VẤN CÁC GÓI KẾT HỢP PHIM CÁCH NHIỆT (CUSTOM COMBINED TINT PACKAGES)
    # ═════════════════════════════════════════════════════════════════════════
    is_combine_tint = (
        bool(re.search(r'\b(ket hop|va con lai|con lai|di cung|ghep|mix|phoi)\b', clean_text)) and
        any(k in clean_text for k in ['film', 'phim', 'kinh', 'cach nhiet']) and
        any(k in clean_text for k in ['3m', 'ntech', 'ceramax', 'lai 3m'])
    ) or (
        bool(re.search(r'\b(kinh lai|lai)\s*(?:3m|ceramax)\b', clean_text)) and
        bool(re.search(r'\b(?:suon|hau|con lai|than xe)?\s*(?:ntech|ceramax)\b', clean_text))
    ) or (
        '3m' in clean_text and 'ntech' in clean_text
    )

    if is_combine_tint:
        is_ntech_cc = any(k in clean_text for k in ['cao cap', 'cc'])
        is_ntech_tc = any(k in clean_text for k in ['tieu chuan', 'tc'])

        # Kính lái 3M + Sườn Ntech
        if '3m' in clean_text and ('ntech' in clean_text or 'con lai' in clean_text):
            is_cheap_3m = any(k in clean_text for k in ['re', '2.6', '2tr6', '2600', 'ceramic', 'tiet kiem'])
            if is_cheap_3m:
                return {
                    "type": "success",
                    "module": "dichvu",
                    "message": (
                        "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M CERAMIC (2.6TR) + SƯỜN & HẬU NTECH:**\n"
                        "• **+ Sườn & Hậu Ntech Tiêu Chuẩn:** Sedan **4.900.000 đ** | SUV **5.400.000 đ**\n"
                        "• **+ Sườn & Hậu Ntech Cao Cấp:** Sedan **5.800.000 đ** | SUV **6.700.000 đ**\n"
                        "🎁 Tặng 100% công lột phim cũ và vệ sinh keo sạch (500k). Kính lái 3M BH 10 năm, sườn Ntech BH 10 năm."
                    )
                }
            if is_ntech_cc:
                return {
                    "type": "success",
                    "module": "dichvu",
                    "message": (
                        "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M CR50BLK + SƯỜN & HẬU NTECH CAO CẤP**\n"
                        "• **Sedan (4 - 5 chỗ):** **8.500.000 đ** *(Niêm yết: 8.9tr - Giảm 400k)*\n"
                        "  *(Lái 3M CR50BLK 5.7tr + Sườn trước Ntech CC 1tr + Sườn sau 1tr + Hậu 1.2tr)*\n"
                        "• **SUV (7 chỗ):** **9.300.000 đ** *(Niêm yết: 9.8tr - Giảm 500k)*\n"
                        "  *(Lái 3M 5.7tr + Sườn hậu Ntech CC 3.2tr + Ô chết 900k)*\n"
                        "💡 *Tùy chọn tiết kiệm:* Nếu đổi sang **kính lái 3M Ceramic (2.6tr)** thì trọn gói chỉ còn: Sedan **5.8tr** | SUV **6.7tr**.\n"
                        "🎁 *Ưu đãi:* Tặng 100% công lột keo cũ (500k). Kính lái 3M BH 10 năm Mỹ, sườn Ntech BH 10 năm."
                    )
                }
            elif is_ntech_tc:
                return {
                    "type": "success",
                    "module": "dichvu",
                    "message": (
                        "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M CR50BLK + SƯỜN & HẬU NTECH TIÊU CHUẨN**\n"
                        "• **Sedan (4 - 5 chỗ):** **7.600.000 đ** *(Niêm yết: 8.0tr)*\n"
                        "• **SUV (7 chỗ):** **8.000.000 đ** *(Niêm yết: 8.5tr)*\n"
                        "💡 *Tùy chọn tiết kiệm:* Nếu đổi sang **kính lái 3M Ceramic (2.6tr)** thì trọn gói chỉ còn: Sedan **4.9tr** | SUV **5.4tr**.\n"
                        "🎁 Tặng 100% công lột keo cũ 500k. Kính lái 3M BH 10 năm, sườn Ntech BH 10 năm."
                    )
                }
            else:
                return {
                    "type": "success",
                    "module": "dichvu",
                    "message": (
                        "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M + SƯỜN & HẬU NTECH:**\n"
                        "1️⃣ **Kính lái 3M Crystalline CR50BLK (Đỉnh cao):**\n"
                        "  • + Sườn Ntech Cao Cấp: Sedan **8.5tr** | SUV **9.3tr**\n"
                        "  • + Sườn Ntech Tiêu Chuẩn: Sedan **7.6tr** | SUV **8.0tr**\n"
                        "2️⃣ **Kính lái 3M Ceramic (Bản tiết kiệm 2.6tr):**\n"
                        "  • + Sườn Ntech Cao Cấp: Sedan **5.8tr** | SUV **6.7tr**\n"
                        "  • + Sườn Ntech Tiêu Chuẩn: Sedan **4.9tr** | SUV **5.4tr**\n"
                        "🎁 Tặng 100% công lột phim cũ và vệ sinh keo sạch sẽ (trị giá 500k)."
                    )
                }

        # Kính lái 3M + Sườn Ceramax
        elif '3m' in clean_text and 'ceramax' in clean_text:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M CR50BLK + SƯỜN & HẬU CERAMAX DIAMOND:**\n"
                    "• **Sedan (4 - 5 chỗ):** **11.200.000 đ** *(Niêm yết: 11.9tr)*\n"
                    "• **SUV (7 chỗ):** **12.900.000 đ** *(Niêm yết: 13.7tr)*\n"
                    "• *Đặc tính:* Kính lái quang học 3M Crystalline Mỹ + Sườn hậu men gốm Ceramax cản IR 99.1%."
                )
            }

    # ═════════════════════════════════════════════════════════════════════════
    # 5. TRA CỨU TỪNG THIẾT BỊ CỤ THỂ (3-4 DÒNG TẬP TRUNG)
    # ═════════════════════════════════════════════════════════════════════════

    # Tra cứu các sản phẩm camera hành trình (A510, M310, A200, A210, A800SE, Vietmap M1, M2...)
    cam_match = re.search(r'\b(a510|70mai a510|m310|a310|70mai m310|a200|70mai a200|a210|70mai a210|a800se|a800|vietmap m1|cam m1|m1|vietmap m2|cam m2|m2)\b', clean_text)
    if cam_match:
        c_key = cam_match.group(1).upper()
        # 1. Tra cứu trong gara_memory (tri thức gara)
        try:
            import knowledge_base
            res_km = knowledge_base.query_learned_knowledge(clean_text, raw_text)
            if res_km:
                return res_km
        except Exception:
            pass

        # 2. Tra cứu trong kho hàng products (tiem_lap_do.db)
        try:
            db_p = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
            if os.path.exists(db_p):
                conn_p = sqlite3.connect(db_p, timeout=5)
                c_p = conn_p.cursor()
                c_p.execute("SELECT name, price, stock FROM products WHERE UPPER(name) LIKE ? ORDER BY id DESC LIMIT 1", (f"%{c_key}%",))
                row_p = c_p.fetchone()
                conn_p.close()
                if row_p:
                    p_name, p_price, p_stock = row_p
                    p_pr_str = f"{p_price:,.0f} đ" if p_price else "Liên hệ"
                    st_str = f"Sẵn hàng ({p_stock} cái)" if (p_stock and p_stock > 0) else "Tạm hết hàng"
                    return {
                        "type": "success",
                        "module": "dichvu",
                        "message": (
                            f"📹 **THÔNG TIN KHO HÀNG GARA: {p_name}**\n"
                            f"─────────────────────────────────────────\n"
                            f"• 💰 **Giá bán niêm yết:** **{p_pr_str}**\n"
                            f"• 📦 **Tình trạng tồn kho:** {st_str}\n"
                            f"• 🔧 Miễn phí công lắp đặt đi dây âm thẩm mỹ tại gara."
                        )
                    }
        except Exception:
            pass

        # 3. Nếu chưa có trong hệ thống: Báo rõ ràng, không tự tiện bịa giá!
        return {
            "type": "info",
            "module": "dichvu",
            "message": (
                f"📹 **THÔNG TIN SẢN PHẨM: {c_key}**\n"
                f"─────────────────────────────────────────\n"
                f"⚠️ Sản phẩm này hiện chưa có thông tin giá niêm yết trong hệ thống gara.\n"
                f"👉 Anh/chị chủ gara có thể cập nhật giá vào kho hàng hoặc nhắn:\n"
                f"*(Ví dụ: `sửa lại giá {c_key.lower()} giá 3tr5`)* để AI ghi nhớ nhé!"
            )
        }

    # Android Box Vietmap BS10
    if bool(re.search(r'\b(bs10|vietmap bs10|box bs10)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📦 **ANDROID BOX VIETMAP BS10 (CẮM ZIN MÀN XE):**\n"
                "• **Bản Ram 4GB / 64GB:** **7.000.000 đ**\n"
                "• **Bản Ram 6GB / 128GB:** **8.400.000 đ** *(Bán chạy nhất - Cực mượt)*\n"
                "• **Bản Ram 8GB / 128GB:** **9.500.000 đ** *(Khủng nhất phân khúc)*\n"
                "• Tích hợp Vietmap Live dẫn đường báo phạt nguội + Định vị xe từ xa qua điện thoại."
            )
        }

    # Android Box iCar D4
    if bool(re.search(r'\b(icar d4|box d4|d4)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📦 **ANDROID BOX ICAR D4 (GIỌNG NÓI KIKI):**\n"
                "• 🔥 **Giá KM hiện tại:** **6.000.000 đ** *(Giá gốc niêm yết: 7.500.000 đ - Giảm 1.5tr)*\n"
                "• Cắm cổng USB/Type-C giữ zin màn xe, điều khiển giọng nói tiếng Việt mượt mà."
            )
        }

    # Màn hình Winca S150+
    if bool(re.search(r'\b(s150|winca s150|s150\+)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📺 **MÀN HÌNH ANDROID WINCA S150+:**\n"
                "• **Giá trọn gói:** **6.500.000 đ**\n"
                "• **Quà tặng:** Mặt dưỡng theo xe + Vietmap Live 2 năm + Sim 4G + Tùy chọn tặng Cam Lùi hoặc Cam Hành Trình\n"
                "• ⚠️ *Lưu ý:* Không tặng thẻ nhớ, tư vấn đổi tặng Cam Lùi hoặc giảm 300k."
            )
        }

    # Màn hình Bravo B10lite
    if bool(re.search(r'\b(bravo|b10lite|b10 lite|b10)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📺 **MÀN HÌNH BRAVO B10 LITE:**\n"
                "• **Giá trọn gói:** **5.500.000 đ** (Tặng mặt dưỡng theo xe + Bản quyền Vietmap Live 2 năm)."
            )
        }

    # Màn hình Gotech GT2K
    if bool(re.search(r'\b(gt2k|gt 2k)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📺 **MÀN HÌNH GOTECH GT2K (ĐỘ PHÂN GIẢI 2K - BH 2 NĂM):**\n"
                "• Màn đơn: GT2K New **9.6tr** | GT2K Pro **11.9tr** | GT2K Max **14.5tr**\n"
                "• Màn liền Cam 360: GT2K 360 **14.9tr** | GT2K 360 Pro **17.9tr** | GT2K 360 Max **19.6tr**"
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # TƯ VẤN & BÁO GIÁ ĐÈN GẦM / BI GẦM LED / BI PHA (TRẦN BÌNH AUTO)
    # ═════════════════════════════════════════════════════════════════════════
    is_f10_query = bool(re.search(r'\b(f10|f10\s*turbo|f10\s*new|f10\s*pro|f10\s*hyper|bi\s*gam\s*f10|den\s*gam\s*f10|den\s*f10)\b', clean_text)) and \
                   not bool(re.search(r'\b(lap|gan|thay|ban|don|nhap)\b', clean_text)) and not bool(re.search(r'\b\d{4}\b', clean_text))
    if is_f10_query:
        p_new = get_lamp_price_from_memory("F10 NEW 2.0") or 3900
        p_3m = get_lamp_price_from_memory("F10 BA MÀU") or 4200
        p_tb = get_lamp_price_from_memory("F10 TURBO") or 5100
        p_hp = get_lamp_price_from_memory("F10 HYPER") or 5500
        p_pro = get_lamp_price_from_memory("F10 PRO") or 5500

        p_new_txt = f"{p_new*1000:,.0f} đ"
        p_3m_txt = f"{p_3m*1000:,.0f} đ"
        p_tb_txt = f"{p_tb*1000:,.0f} đ"
        p_hp_txt = f"{p_hp*1000:,.0f} đ"
        p_pro_txt = f"{p_pro*1000:,.0f} đ"

        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "💡 **BÁO GIÁ BI GẦM F10 SERIES (CHÍNH HÃNG - BÁN CHẠY SỐ 1):**\n"
                "─────────────────────────────────────────\n"
                "Bi gầm LED F10 là dòng bi gầm quốc dân tăng sáng gấp 5-7 lần đèn halogen zin, gom cắt chuẩn không chói mắt:\n\n"
                f"• **Bi gầm F10 New 2.0 (Bản tiêu chuẩn):** **{p_new_txt}**\n"
                "  - Công suất 35W/40W, ánh sáng trắng ấm bám đường cực tốt.\n"
                f"• **Bi gầm F10 Ba Màu (3000K / 4300K / 5500K):** **{p_3m_txt}**\n"
                "  - Đổi màu linh hoạt bằng công tắc gầm zin: Vàng đậm (phá sương/mưa bão) - Vàng nắng (hỗn hợp) - Trắng (đi phố).\n"
                f"• **Bi gầm F10 Turbo V2 (Mới nhất - Công suất khủng):** **{p_tb_txt}**\n"
                "  - Tích hợp tâm pha trợ lực cực xa, độ phủ rộng ngang đỉnh cao.\n"
                f"• **Bi gầm F10 Hyper 2.0 (5000K):** **{p_hp_txt}**\n"
                "  - Nhiệt màu 5000K chuẩn mịn mắt, mặt cắt sắc nét, bám đường mưa tuyệt hảo.\n"
                f"• **Bi gầm F10 Pro V2 (3 màu cao cấp):** **{p_pro_txt}**\n"
                "─────────────────────────────────────────\n"
                "🎁 **Ưu đãi & Chính sách lắp đặt tại Trần Bình Auto:**\n"
                "• Tặng kèm pát zin theo từng dòng xe, cắm giắc chuyển đổi không cắt trích dây zin.\n"
                "• Bảo hành chính hãng 2 năm (1 đổi 1).\n"
                "• Căn chỉnh góc chiếu chuẩn đăng kiểm toàn quốc.\n"
                "👉 *Bạn đang đi dòng xe gì để gara kiểm tra pát zin và tư vấn mẫu phù hợp nhất nhé!*"
            )
        }

    is_general_fog_light = bool(re.search(r'\b(den\s*gam|bi\s*gam|do\s*den|do\s*bi|cac\s*loai\s*bi\s*gam|cac\s*loai\s*den\s*gam|tu\s*van\s*den\s*gam|tu\s*van\s*bi\s*gam|gia\s*den\s*gam|gia\s*bi\s*gam|den\s*gam\s*loai\s*nao)\b', clean_text)) or \
                           (bool(re.search(r'\b(s3|s6|s8|s9|naoevo|v20|m30|m40)\b', clean_text)) and not bool(re.search(r'\b(lap|gan|thay|ban|don|nhap)\b', clean_text)) and not bool(re.search(r'\b\d{4}\b', clean_text)))
    if is_general_fog_light:
        p_s3 = get_lamp_price_from_memory("S3") or 1500
        p_new = get_lamp_price_from_memory("F10 NEW 2.0") or 3900
        p_3m = get_lamp_price_from_memory("F10 BA MÀU") or 4200
        p_tb = get_lamp_price_from_memory("F10 TURBO") or 5100
        p_v20 = get_lamp_price_from_memory("V20") or 5850

        p_s3_txt = f"{p_s3*1000:,.0f} đ"
        p_new_txt = f"{p_new*1000:,.0f} đ"
        p_3m_txt = f"{p_3m*1000:,.0f} đ"
        p_tb_txt = f"{p_tb*1000:,.0f} đ"
        p_v20_txt = f"{p_v20*1000:,.0f} đ"

        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "💡 **BÁO GIÁ & TƯ VẤN CÁC DÒNG BI GẦM Ô TÔ (TRẦN BÌNH AUTO):**\n"
                "─────────────────────────────────────────\n"
                "Gara có đầy đủ các phân khúc Bi gầm LED chính hãng tăng sáng từ 4 - 7 lần, bao đăng kiểm:\n\n"
                "🌟 **1. PHÂN KHÚC TIẾT KIỆM (1.5tr - 3.0tr) - DÒNG NAOEVO S-SERIES:**\n"
                f"• **Naoevo S3:** **{p_s3_txt}** *(Ngon bổ rẻ, tăng sáng gấp 3 lần halogen)*\n"
                "• **Naoevo S6 / S6 Pro:** **1.800.000 đ - 2.000.000 đ**\n"
                "• **Naoevo S8 / S9 Pro:** **2.500.000 đ - 3.000.000 đ**\n\n"
                "🌟 **2. PHÂN KHÚC QUỐC DÂN BÁN CHẠY NHẤT (3.9tr - 5.5tr) - BI GẦM F10:**\n"
                f"• **F10 New 2.0:** **{p_new_txt}** (Gom sáng nét, bám đường)\n"
                f"• **F10 Ba Màu (3000K/4300K/5500K):** **{p_3m_txt}** *(Chuyên đi mưa phá sương)*\n"
                f"• **F10 Turbo V2:** **{p_tb_txt}** *(Công suất khủng có trợ pha)*\n"
                "• **F10 Hyper / F10 Pro V2:** **5.500.000 đ**\n\n"
                "🌟 **3. PHÂN KHÚC CAO CẤP & BI PHA LED:**\n"
                f"• **Bi LED Pha V20 Ultra / V20 Base:** **{p_v20_txt}**\n"
                "• **Bi gầm M30 Ultra / M40 Ultra:** **5.500.000 đ - 6.500.000 đ**\n"
                "• **Titan Gold / Titan Black:** **5.500.000 đ - 6.750.000 đ**\n"
                "─────────────────────────────────────────\n"
                "🎁 Lắp đặt pát zin 100%, cắm giắc chuyên dụng, bảo hành 2 năm 1 đổi 1.\n"
                "👉 *Bạn muốn lắp cho xe gì và thường đi đường phố hay đi đường đèo/sương mù nhiều ạ?*"
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # TƯ VẤN THÔNG MINH CHO XE ĐIỆN QUỐC DÂN VINFAST VF3
    # ═════════════════════════════════════════════════════════════════════════
    is_vf3 = any(k in clean_text for k in ['vf3', 'vf 3', 'vinfast vf3'])
    if is_vf3:
        # A. Khách hỏi Camera 360 cho VF3:
        if any(k in clean_text for k in ['360', 'cam 360', 'camera 360']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📷 **BÁO GIÁ CAMERA 360 ĐỘ CHO VINFAST VF3 (TRẦN BÌNH AUTO):**\n"
                    "─────────────────────────────────────────\n"
                    "Dòng xe VinFast VF3 có 2 phương án nâng cấp Camera 360 độ toàn cảnh tối ưu nhất:\n\n"
                    "🔹 **PHƯƠNG ÁN 1: CAMERA 360 RỜI CẮM ZIN MÀN HÌNH THEO XE (GIỮ NGUYÊN MÀN GỐC)**\n"
                    "• **Camera 360 OWIN (Bản cho VF3):** **8.500.000 đ** *(Khuyên dùng nhất - Không CarPlay)*\n"
                    "  - Bản có tích hợp Apple CarPlay: **9.500.000 đ**\n"
                    "  - Cắm giắc zin 100%, tích hợp thẳng vào màn hình zin của xe VF3.\n"
                    "  - Mắt cam Sony quay đêm siêu nét, tự động bật góc nhìn khi xi nhan, lùi hoặc chạy chậm dưới 20km/h.\n"
                    "  - Bảo hành chính hãng 2 năm.\n"
                    "• **Camera 360 MHU cho VF3 (Lắp zin chuẩn hãng):** **13.900.000 đ**\n\n"
                    "🔹 **PHƯƠNG ÁN 2: MÀN HÌNH ANDROID LIỀN CAMERA 360 (VỪA GIẢI TRÍ VỪA XÓA ĐIỂM MÙ)**\n"
                    "• **Màn hình WINCA Android liền Cam 360 cho VF3:** **10.500.000 đ** *(Ngon bổ rẻ - Bán chạy)*\n"
                    "  - Trọn bộ gồm Màn hình Android cảm ứng + 4 mắt Cam 360 toàn cảnh.\n"
                    "  - Xem YouTube ngầm, dẫn đường Vietmap Live cảnh báo tốc độ phạt nguội.\n"
                    "• **Màn hình GOTECH VF3 360 / GBA VF3 360:** **19.900.000 đ - 20.000.000 đ** *(Cao cấp màn 2K)*\n"
                    "• **Màn hình dài VF3 kiểu Mercedes (Kèm Cam 360):** **17.500.000 đ**\n"
                    "─────────────────────────────────────────\n"
                    "🎁 **Cam kết tại gara:** Tặng công căn chỉnh bạt chuẩn xác, cắm giắc zin 100% không cắt trích dây, an toàn tuyệt đối cho hệ thống điện xe VF3!"
                )
            }

        # B. Khách hỏi Màn hình Android cho VF3:
        if any(k in clean_text for k in ['man hinh', 'man', 'dvd', 'android']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📺 **BÁO GIÁ MÀN HÌNH ANDROID CHO VINFAST VF3:**\n"
                    "• **WINCA Android cho VF3 (Màn đơn):** **7.500.000 đ** (Tặng Vietmap Live 2 năm + Sim 4G)\n"
                    "• **Màn HTD ODO cho VF3 (Có cảm ứng + Tặng 2 mắt cam lề):** **7.500.000 đ**\n"
                    "• **WINCA Android liền Camera 360 cho VF3:** **10.500.000 đ** *(Bán chạy nhất)*\n"
                    "• **Màn dài VF3 kiểu Mercedes (Ram 4/32):** **17.500.000 đ**\n"
                    "• **GOTECH VF3 360 (Màn 2K cao cấp):** **19.900.000 đ**\n"
                    "🔧 Cắm giắc zin theo xe 100%, bảo hành 2 năm chính hãng."
                )
            }

        # C. Khách hỏi Đèn / Nâng cấp ánh sáng cho VF3:
        if any(k in clean_text for k in ['den', 'bi led', 'bi gam', 'den tron', 'xi nhan', 'mi led']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "💡 **GÓI NÂNG CẤP ĐÈN & ÁNH SÁNG CHO VINFAST VF3:**\n"
                    "• **Bi gầm LED F10 Turbo / S3:** **3.900.000 đ - 4.500.000 đ** *(Tăng sáng gấp 5 lần đèn zin, đi mưa phá sương cực đỉnh)*\n"
                    "• **Mặt Calang đèn tròn VF3 (Mẫu V4):** **16.000.000 đ** *(Phong cách Defender siêu hầm hố)*\n"
                    "• **Mí LED VF3 full chuyển màu RGB:** **2.500.000 đ**\n"
                    "• **Đèn xi nhan G63 cho VF3:** **5.500.000 đ**\n"
                    "• **Đèn hậu VF3 Custom:** **3.500.000 đ - 10.000.000 đ**\n"
                    "• **Led cánh chim / Led logo VinFast:** **1.500.000 đ - 1.800.000 đ**"
                )
            }

        # D. Khách hỏi Bọc ghế da cho VF3:
        if bool(re.search(r'\b(ghe|boc\s*ghe|ghe\s*da|da\s*ghe|nappa|simili|ghe\s*dien)\b', clean_text)) or \
           (bool(re.search(r'\bda\b', clean_text)) and not bool(re.search(r'\b(dan|danh|dan\s*phim|dan\s*film|dan\s*kinh)\b', clean_text))):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "💺 **BÁO GIÁ BỌC GHẾ DA & GHẾ ĐIỆN CHO VINFAST VF3:**\n"
                    "• **Da Simili tiêu chuẩn:** **3.500.000 đ**\n"
                    "• **Da Công Nghiệp cao cấp:** **6.000.000 đ** *(Mềm mát, bền 4-5 năm)*\n"
                    "• **Da Nappa chuẩn xe sang:** **9.500.000 đ**\n"
                    "• **Da ghế LAVOR CN Milan:** **8.000.000 đ** | **LAVOR Nappa Lux:** **10.500.000 đ**\n"
                    "• **Ghế điện VF3 (UniSeat / GBA):** **16.000.000 đ** *(Chỉnh điện đa hướng cực kỳ êm ái)*"
                )
            }

        # E. Khách hỏi Phụ kiện / Đồ chơi ngoại thất cho VF3:
        if any(k in clean_text for k in ['phu kien', 'do choi', 'cop truoc', 'gia noc', 'phuoc', 'cua hit', 'vo lang']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "🚗 **TOP PHỤ KIỆN & ĐỒ CHƠI ĐỘ ĐẸP CHO VINFAST VF3:**\n"
                    "• **Cốp trước VF3 (EasyCop):** **5.500.000 đ** *(Thêm khoang chứa đồ phía trước)*\n"
                    "• **Cửa hít X-Win VF3:** **9.500.000 đ** *(Đóng cửa êm ái nhẹ nhàng)*\n"
                    "• **Giá nóc nguyên khối lắp zin:** **5.000.000 đ - 7.000.000 đ**\n"
                    "• **Phuộc TEIN Basic / Phuộc HT25:** **4.500.000 đ - 12.600.000 đ** *(Khắc phục bồng bềnh)*\n"
                    "• **Vô lăng Carbon / Nappa:** **2.000.000 đ - 6.500.000 đ**\n"
                    "• **Thang treo hông + Cốp đồ treo hông:** **6.000.000 đ - 6.500.000 đ**"
                )
            }

        # F. Bảng giá dán Phim cách nhiệt cho VF3 (chỉ khi hỏi về phim, kính hoặc hỏi chung vf3):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "⚡ **BẢNG GIÁ DÁN PHIM CÁCH NHIỆT VINFAST VF3:**\n"
                "1. Nano Ceramic (Đài Loan): **1.8tr** (BH 1 năm)\n"
                "2. Ceramax + Ntech Tiêu Chuẩn: **4.5tr** (BH 10 năm - Bán chạy)\n"
                "3. Ceramax + Ntech Cao Cấp: **5.0tr** (BH 10 năm)\n"
                "4. 3M Ceramic Hybrid: **6.0tr**\n"
                "5. Ceramax Full xe: **7.0tr** (BH 15 năm)\n"
                "6. 3M Crystalline Cr60/50 + Ir15: **9.3tr** (BH 10 năm)\n"
                "7. 3M Crystalline Cr60/50 + Cr20: **11.9tr** (BH 10 năm)\n"
                "🎁 Tặng 100% công lột phim cũ và vệ sinh keo sạch (500k)."
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # CAMERA 360 ĐỘ QUAN SÁT TOÀN CẢNH (MỌI DÒNG XE)
    # ═════════════════════════════════════════════════════════════════════════
    is_cam360 = bool(re.search(r'\b(cam\s*360|camera\s*360|cam360|camera360|360\s*do|toan\s*canh|xoa\s*diem\s*mu)\b', clean_text))
    if is_cam360:
        # Nếu khách hỏi dòng TexPad 360:
        if 'texpad' in clean_text:
            return {
                "type": "info",
                "module": "dichvu",
                "message": (
                    "⚠️ **THÔNG BÁO TỪ TRẦN BÌNH AUTO:**\n"
                    "Hiện tại dòng **Camera 360 TexPad gara đã ngừng kinh doanh**.\n\n"
                    "👉 Gara khuyên dùng các dòng Camera 360 độ thế hệ mới độ nét cao và ổn định hơn:\n"
                    "• **Camera 360 Owin (Sony AHD / Pro):** **8.5tr - 16.1tr** *(Cắm giắc zin màn theo xe, mắt cam Sony quay đêm cực nét, BH 2 năm)*\n"
                    "• **Camera 360 DCT (T1 Pro / T2 Pro):** **12.8tr - 15.8tr** *(Dòng cam 360 sắc nét hàng đầu)*\n"
                    "• **Màn hình Android liền Cam 360 WINCA S170+:** **11.8tr** *(Vừa xem YouTube vừa quan sát toàn cảnh 360)*"
                )
            }

        res = "📷 **BÁO GIÁ CAMERA 360 ĐỘ TOÀN CẢNH CHÍNH HÃNG:**\n"
        res += "─────────────────────────────────────────\n"
        res += "Gara Trần Bình Auto cung cấp 2 giải pháp Camera 360 độ xóa điểm mù tối ưu:\n\n"
        res += "📱 **1. MÀN HÌNH ANDROID LIỀN CAMERA 360 (KHUYÊN DÙNG NHẤT):**\n"
        res += "• **Gotech G360 (9 - 10 inch):** **10.400.000 đ** *(Màn HD, tặng Sim 4G + Vietmap Live)*\n"
        res += "• **Winca S170+ Pro 360:** **11.800.000 đ** *(Màn QLED 2K siêu nét, bán chạy số 1)*\n"
        res += "• **Gotech GC360:** **12.900.000 đ** | **Gotech GT2K 360:** **14.900.000 đ**\n"
        res += "• **Winca S200+ Pro 360:** **13.500.000 đ** | **S300+ Pro 360 (2K):** **15.500.000 đ**\n"
        res += "• **Gotech GT2K 360 Pro:** **17.900.000 đ** | **GT2K 360 Max:** **19.600.000 đ**\n\n"
        res += "🔄 **2. CAMERA 360 RỜI CẮM ZIN MÀN HÌNH GỐC THEO XE:**\n"
        res += "• **Camera 360 Owin (Bản cho VF3, XForce, Mazda, CRV, CX5...):** **8.5tr - 16.1tr** *(Cảm biến Sony ban đêm siêu sáng)*\n"
        res += "• **Camera 360 DCT (T1 Pro / T2 Pro / T3 Pro):** **12.8tr - 18.8tr** *(Ghi hình 4 hướng lúc tắt máy)*\n"
        res += "• **Camera 360 ICAR Elliview (M11 / V5):** **15.8tr - 16.8tr**\n"
        res += "─────────────────────────────────────────\n"
        res += "🎁 Tặng công lắp đặt đi dây âm thẩm mỹ và căn chỉnh bạt chuẩn xác tại gara.\n"
        res += "👉 *Bạn đang đi xe gì và đời nào để gara tư vấn giải pháp cắm giắc zin chuẩn nhất nhé!*"
        return {"type": "success", "module": "dichvu", "message": res}

    # Bọc da Nappa
    if bool(re.search(r'\b(nappa|da nappa)\b', clean_text)) and not is_compare:
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "💺 **BỌC GHẾ DA NAPPA CAO CẤP (CHUẨN XE SANG):**\n"
                "• **Xe 4 - 5 chỗ:** **9.500.000 đ**\n"
                "• **Xe 7 chỗ:** **12.000.000 đ**\n"
                "• 💡 *Tùy chọn:* Dập đục lỗ công nghệ vi điểm thoát khí lưng ghế: **+1.000.000 đ**."
            )
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 6. TÍNH COMBO ĐA DỊCH VỤ TỰ ĐỘNG
    # ═════════════════════════════════════════════════════════════════════════
    is_combo = bool(re.search(r'\b(combo|cung luc|vua lam|tron goi|goi combo)\b', clean_text)) or \
               (clean_text.count('+') >= 1 or (any(k in clean_text for k in ['man hinh', 'winca', 'bravo']) and any(k in clean_text for k in ['ghe da', 'boc ghe', 'boc tran', 'phim', 'film'])))

    if is_combo:
        combo_items = []
        total_price = 0

        if 'winca' in clean_text or 's150' in clean_text:
            combo_items.append(("Màn hình Winca S150+", 6500000))
            total_price += 6500000
        elif 'bravo' in clean_text or 'b10' in clean_text:
            combo_items.append(("Màn hình Bravo B10lite", 5500000))
            total_price += 5500000
        elif 's170' in clean_text:
            combo_items.append(("Màn hình liền Cam 360 Winca S170+", 11800000))
            total_price += 11800000

        if any(k in clean_text for k in ['ghe', 'boc ghe']):
            if 'nappa' in clean_text:
                p = 12000000 if '7' in clean_text else 9500000
                combo_items.append((f"Bọc ghế da Nappa ({'7 chỗ' if '7' in clean_text else '4 chỗ'})", p))
                total_price += p
            elif 'simili' in clean_text:
                p = 6000000 if '7' in clean_text else 3500000
                combo_items.append((f"Bọc ghế da Simili ({'7 chỗ' if '7' in clean_text else '4 chỗ'})", p))
                total_price += p
            else:
                p = 7500000 if '7' in clean_text else 6000000
                combo_items.append((f"Bọc ghế da Công nghiệp ({'7 chỗ' if '7' in clean_text else '4 chỗ'})", p))
                total_price += p

        if any(k in clean_text for k in ['tran', 'boc tran']):
            if 'nilong' in clean_text or 'nilon' in clean_text:
                p = 800000 if '7' in clean_text else 500000
                combo_items.append((f"Bọc trần Nilong ({'7 chỗ' if '7' in clean_text else '4 chỗ'})", p))
                total_price += p
            else:
                p = 1800000 if '7' in clean_text else 1300000
                combo_items.append((f"Bọc trần da Kim Cương ({'7 chỗ' if '7' in clean_text else '4 chỗ'})", p))
                total_price += p

        if len(combo_items) >= 2:
            discount = 500000 if total_price < 12000000 else 1000000
            final_price = total_price - discount
            res = "🎁 **BÁO GIÁ GÓI COMBO NÂNG CẤP XE:**\n"
            for item, p in combo_items:
                res += f"• {item}: **{p:,.0f} đ**\n"
            res += f"💵 Tổng niêm yết: ~~{total_price:,.0f} đ~~ ➔ 🔥 **Giá Combo: {final_price:,.0f} đ** *(Giảm {discount:,.0f} đ)*"
            return {"type": "success", "module": "dichvu", "message": res}

    # ═════════════════════════════════════════════════════════════════════════
    # 7. TƯ VẤN THEO NGÂN SÁCH (NGẮN GỌN)
    # ═════════════════════════════════════════════════════════════════════════
    m_budget = re.search(r'\b(?:tam|khoang|ngan sach|co|tam gia|duoi)\s*(\d+)\s*(tr|trieu|k|m)?\b', clean_text)
    if m_budget and any(k in clean_text for k in ['nen lam gi', 'lap gi', 'do gi', 'nang cap', 'tu van']):
        val = int(m_budget.group(1))
        unit = m_budget.group(2) or ''
        b_mil = val / 1000.0 if unit == 'k' else float(val)

        if b_mil <= 3:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    f"💡 **TƯ VẤN XE TẦM {b_mil:g} TRIỆU:**\n"
                    "• Cam hành trình 70mai A200 2K: **2.5tr** (Trước + Sau, tặng thẻ 32GB)\n"
                    "• Bọc trần da kim cương: 4 chỗ **1.3tr** | 7 chỗ **1.8tr**\n"
                    "• Dán phim Nano Ceramic: 4 chỗ **2.0tr** | SUV **2.2tr**"
                )
            }
        elif b_mil <= 7:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    f"💡 **TƯ VẤN XE TẦM {b_mil:g} TRIỆU (ĐÁNG TIỀN NHẤT):**\n"
                    "• Phim Ntech + Kính lái Ceramax: **5.6tr - 6.1tr** (BH 10 năm)\n"
                    "• Màn hình Winca S150+: **6.5tr** hoặc Bravo B10lite **5.5tr**\n"
                    "• Android Box iCar D4: Sale **6.0tr** (Cắm giắc zin)\n"
                    "• Cam Vietmap M1 2K: **6.19tr** (Báo tốc độ phạt nguội)\n"
                    "• Bọc ghế da công nghiệp 4 chỗ: **6.0tr**"
                )
            }
        else:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    f"💡 **TƯ VẤN XE TẦM {b_mil:g} TRIỆU TRỞ LÊN:**\n"
                    "• Màn hình liền Cam 360 Winca S170+ Pro: **11.8tr**\n"
                    "• Phim Ceramax Diamond men gốm full xe: Sedan **9.5tr** | SUV **11.3tr**\n"
                    "• Bọc ghế da Nappa chuẩn xe sang: 4 chỗ **9.5tr** | 7 chỗ **12.0tr**"
                )
            }

    # ═════════════════════════════════════════════════════════════════════════
    # 8. BẢNG GIÁ THEO NHÓM DỊCH VỤ (TINH GỌN TỐI ĐA)
    # ═════════════════════════════════════════════════════════════════════════

    # 8.1. BỌC TRẦN Ô TÔ
    is_tran = ('tran' in clean_text) and any(k in clean_text for k in ['boc', 'da', 'nilong', 'nilon', 'kim cuong', '5d', '6d', 'xe', 'oto', 'gia', 'tu van', 'lam', 'dan'])
    if is_tran:
        if 'vf5' in clean_text or 'vf 5' in clean_text:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "⚠️ **LƯU Ý XE VINFAST VF5:**\n"
                    "• Trần da kim cương: 4 chỗ giá **1.300.000 đ**\n"
                    "• 🛑 **Trần Nilong: Gara KHÔNG NHẬN BỌC NILONG CHO XE VF5** (nỉ zin VF5 không ăn keo nilong, rất dễ bong tróc)!"
                )
            }

        if any(k in clean_text for k in ['nilong', 'nilon']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "🛡️ **GIÁ BỌC TRẦN NILONG (GIỮ NỈ ZIN):**\n"
                    "• Xe 4 - 5 chỗ: **500.000 đ**  |  Xe 7 chỗ: **800.000 đ**\n"
                    "⚠️ Gara không nhận bọc nilong cho VinFast VF5."
                )
            }

        if any(k in clean_text for k in ['kim cuong', '5d', '6d', 'da']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "💎 **GIÁ BỌC TRẦN DA KIM CƯƠNG (5D/6D CÁCH NHIỆT):**\n"
                    "• Xe 4 - 5 chỗ: **1.300.000 đ**  |  Xe 7 chỗ: **1.800.000 đ**\n"
                    "*(Chống nóng trần, dễ lau chùi, sang trọng)*"
                )
            }

        res = "✨ **BẢNG BÁO GIÁ BỌC TRẦN Ô TÔ:**\n"
        res += "• **Trần Da Kim Cương 5D/6D:** 4 chỗ **1.300.000 đ** | 7 chỗ **1.800.000 đ**\n"
        res += "• **Trần Nilong:** 4 chỗ **500.000 đ** | 7 chỗ **800.000 đ**\n"
        res += "⚠️ *Lưu ý: Không nhận bọc trần nilong cho dòng xe VinFast VF5.*"
        return {"type": "success", "module": "dichvu", "message": res}

    # 8.2. PHIM CÁCH NHIỆT Ô TÔ (TỔNG QUÁT)
    is_film = bool(re.search(r'\b(film|phim|cach\s*nhiet|dan\s*kinh|ceramax|ntech|3m\s*cr|crystalline|cr50|cr50blk|cr40|nano\s*ceramic)\b', clean_text)) and not bool(re.search(r'\bppf\b', clean_text))
    if is_film:
        # Nếu hỏi riêng dòng 3M
        if any(k in clean_text for k in ['3m', 'crystalline']) and not any(k in clean_text for k in ['ntech', 'ceramax', 'ket hop', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "☀️ **BÁO GIÁ PHIM CÁCH NHIỆT 3M CHÍNH HÃNG MỸ (BH 10 NĂM):**\n"
                    "• **Dán lẻ kính lái 3M Ceramic (Tiết kiệm):** **2.600.000 đ** *(Bao đăng kiểm >50%)*\n"
                    "• **Dán lẻ kính lái 3M Crystalline CR50BLK (Đỉnh cao):** **5.700.000 đ** *(Cắt IR 98%)*\n"
                    "• **3M Ceramic Hybrid:** Sedan **7.900.000 đ** | SUV **9.500.000 đ**\n"
                    "• **3M Ceramic IR:** Sedan **9.000.000 đ** | SUV **10.500.000 đ**\n"
                    "• **3M Crystalline Hybrid (Lái CR50 + Sườn NR):** Sedan **10.800.000 đ** | SUV **12.500.000 đ**\n"
                    "• **3M Crystalline CR BLK (Lái CR50 + Sườn CR15/35):** Sedan **14.800.000 đ** | SUV **17.600.000 đ**\n"
                    "🎁 Tặng 100% công lột phim cũ và vệ sinh keo sạch sẽ (500k)."
                )
            }

        # Nếu hỏi riêng dòng Ceramax
        if any(k in clean_text for k in ['ceramax']) and not any(k in clean_text for k in ['3m', 'ket hop', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "💎 **BÁO GIÁ PHIM MEN GỐM CERAMAX (BH 15 NĂM CHÍNH HÃNG):**\n"
                    "• **Kính Lái CeraMAX 50 (dán lẻ):** **3.300.000 đ** *(Cắt IR 99.1%, xuyên sáng 59.7%)*\n"
                    "• **Ceramax + Ntech Tiêu Chuẩn (Bán chạy):** Sedan **5.600.000 đ** | SUV **6.100.000 đ**\n"
                    "• **Ceramax + Ntech Cao Cấp:** Sedan **6.500.000 đ** | SUV **7.400.000 đ**\n"
                    "• **Ceramax Diamond Full Xe (Men gốm 100%):** Sedan **9.500.000 đ** | SUV **11.300.000 đ**\n"
                    "🎁 Tặng 100% công lột phim cũ và vệ sinh keo sạch sẽ (500k)."
                )
            }

        res = "☀️ **BẢNG GIÁ PHIM CÁCH NHIỆT Ô TÔ (TRẦN BÌNH AUTO):**\n"
        res += "1️⃣ **Ntech Tiêu Chuẩn + Kính lái Ceramax (Bán chạy):** Sedan **5.6tr** | SUV **6.1tr** (BH 10 năm)\n"
        res += "2️⃣ **Ntech Cao Cấp + Kính lái Ceramax:** Sedan **6.5tr** | SUV **7.4tr** (BH 10 năm)\n"
        res += "3️⃣ **Ceramax Diamond Full xe (Men gốm 99% IR):** Sedan **9.5tr** | SUV **11.3tr** (BH 15 năm)\n"
        res += "4️⃣ **3M Crystalline Mỹ (200 lớp quang học):** Sedan **10.8tr - 14.8tr** | SUV **12.5tr - 17.6tr** (BH 10 năm)\n"
        res += "5️⃣ **Nano Ceramic (Tiết kiệm):** Sedan **2.0tr** | SUV **2.2tr**\n"
        res += "🎁 *Ưu đãi:* Tặng 100% công lột phim cũ và vệ sinh keo sạch sẽ (trị giá 500k).\n"
        res += "👉 Kính lái dùng CR50BLK / Ceramax 50 độ xuyên sáng > 50% bao đăng kiểm."
        return {"type": "success", "module": "dichvu", "message": res}

    # 8.3. MÀN HÌNH ANDROID & MÀN HÌNH LIỀN CAM 360
    is_manhinh = bool(re.search(r'\b(man\s*hinh|dvd|android\s*auto|gotech|winca|bravo|gt2k|gt11|b10lite|s150|s170|gtp4|gc360|g360)\b', clean_text))
    if is_manhinh:
        # Nếu hỏi riêng dòng Winca
        if any(k in clean_text for k in ['winca']) and not any(k in clean_text for k in ['gotech', 'bravo', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📺 **BÁO GIÁ MÀN HÌNH ANDROID WINCA:**\n"
                    "• **Winca S150+ (Màn đơn):** **6.500.000 đ** *(Tặng mặt dưỡng + Vietmap Live 2 năm + Sim 4G + Cam lùi)*\n"
                    "• **Winca S170+ Pro 360 (Liền Cam 360 toàn cảnh):** **11.800.000 đ** *(Tặng Sim 4G + USB 64GB + Vietmap Live)*\n"
                    "🔧 Cắm giắc zin 100% theo xe, bảo hành 2 năm chính hãng."
                )
            }

        # Nếu hỏi riêng dòng Gotech
        if any(k in clean_text for k in ['gotech']) and not any(k in clean_text for k in ['winca', 'bravo', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📺 **BÁO GIÁ MÀN HÌNH GOTECH (MÀN 2K CHỐNG LÓA - BH 2 NĂM):**\n"
                    "📱 **Dòng Màn Đơn:**\n"
                    "• GT2K New: **9.6tr** | GT2K Pro: **11.9tr** | GT11.5i: **12.8tr** | GT2K Max: **14.5tr**\n"
                    "🔄 **Dòng Liền Cam 360:**\n"
                    "• G360: **10.4tr** | GC360: **12.9tr** | GT2K 360: **14.9tr** | GT2K 360 Pro: **17.9tr**\n"
                    "🎁 Tặng mặt dưỡng, Vietmap Live, Sim 4G."
                )
            }

        res = "📺 **BÁO GIÁ MÀN HÌNH ANDROID CHÍNH HÃNG:**\n"
        res += "• **Bravo B10 Lite:** **5.500.000 đ** (Tặng mặt dưỡng + Vietmap Live 2 năm)\n"
        res += "• **Winca S150+:** **6.500.000 đ** (Tặng Vietmap Live 2 năm + Sim 4G + Cam lùi)\n"
        res += "• **GTP4 Plus:** **7.900.000 đ**\n"
        res += "• **Gotech GT2K New:** **9.600.000 đ** | GT2K Pro **11.900.000 đ** | GT11.5i **12.800.000 đ**\n"
        res += "🔄 **Màn hình liền Cam 360 toàn cảnh:**\n"
        res += "• Gotech G360: **10.4tr** | Winca S170+ Pro 360: **11.8tr** | Gotech GC360: **12.9tr** | GT2K 360: **14.9tr**\n"
        res += "⚠️ *Lưu ý:* Bên màn hình không còn tặng thẻ nhớ, đổi qua tặng cam lùi hoặc giảm 300k."
        return {"type": "success", "module": "dichvu", "message": res}

    # 8.4. ANDROID BOX
    is_box = bool(re.search(r'\b(android\s*box|box\s*oto|box\s*xe|icar\s*d4|vietmap\s*bs10|bs10|gb4|gb7|gb9|htd\s*d12se)\b', clean_text))
    if is_box:
        res = "📦 **BÁO GIÁ ANDROID BOX CHÍNH HÃNG (GIỮ ZIN MÀN XE):**\n"
        res += "• **HTD D12SE:** **5.000.000 đ**\n"
        res += "• **Gotech GB4:** **5.400.000 đ** | **Gotech GB7:** **6.800.000 đ** | **GB9:** **9.800.000 đ**\n"
        res += "• **iCar D4:** ~~7.5tr~~ ➔ 🔥 *Sale còn: **6.000.000 đ*** (Giọng nói Kiki)\n"
        res += "• **Vietmap BS10:** Bản 4/64: **7.0tr** | Bản 6/128: **8.4tr** | Bản 8/128: **9.5tr**\n"
        res += "💡 Cắm giắc USB/Type-C có ngay Vietmap Live báo phạt nguội + Youtube ngầm."
        return {"type": "success", "module": "dichvu", "message": res}

    # 8.5. CAMERA HÀNH TRÌNH
    is_cam = bool(re.search(r'\b(cam\s*hanh\s*trinh|camera\s*hanh\s*trinh|70mai|vietmap|a510|a800se|s720|r440|s860|the\s*nho)\b', clean_text)) or \
             (bool(re.search(r'\b(cam|camera)\b', clean_text)) and any(w in clean_text for w in ['loai', 'cac', 'nhung', 'nao', 'tu van', 'gia', 'bao gia', 'co nhung', 'lap', 'gan', 'muon', 'can', 'co']))
    if is_cam:
        if any(k in clean_text for k in ['the nho', 'usb']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "💾 **GIÁ THẺ NHỚ & USB BÁN LẺ:**\n"
                    "• Thẻ nhớ 32GB: **300.000 đ**\n"
                    "• Thẻ nhớ 64GB: **400.000 đ**\n"
                    "• USB 32GB: **350.000 đ**\n"
                    "• Cam hành trình Android rời cắm màn hình: **800.000 đ**."
                )
            }

        # Nếu hỏi riêng dòng 70mai (Chỉ trả về danh sách tổng hợp khi hỏi chung chung, không hỏi mã cụ thể)
        has_specific_70mai = any(m in clean_text for m in ['a210', 'a200', 'a510', 'a800', 'm310', '310', 'm500', 's410', 'omni', 't400', 't800'])
        if any(k in clean_text for k in ['70mai', 'xiaomi']) and not has_specific_70mai and not any(k in clean_text for k in ['vietmap', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📹 **BÁO GIÁ CAMERA HÀNH TRÌNH 70MAI (XIAOMI):**\n"
                    "• **70mai 310 Plus (Trước - Thẻ 32GB):** **1.500.000 đ**\n"
                    "• **70mai A200 2K (Trước + Sau - Thẻ 32GB):** **2.500.000 đ** *(Ngon bổ rẻ)*\n"
                    "• **70mai M500 (Trước - Bộ nhớ 32GB):** **2.800.000 đ**\n"
                    "• **70mai A510 3K (Trước + Sau - Thẻ 64GB):** **3.400.000 đ** *(Sony Starvis 2 - Bán chạy)*\n"
                    "• **70mai A800SE 4K (Trước + Sau - Thẻ 64GB):** Bản thường **3.6tr** | Bản SpeedEye **4.8tr**\n"
                    "• **Cam gương S410 (Tích hợp lùi - Thẻ 32GB):** **4.150.000 đ**\n"
                    "• **70mai Omni 360 xoay tròn:** 32GB **3.9tr** | 64GB **4.2tr**\n"
                    "• **70mai T400:** 32GB **4.2tr** | 64GB **4.5tr**\n"
                    "🎁 Miễn phí công lắp đặt đi dây âm kín tại gara."
                )
            }

        # Nếu hỏi riêng dòng Vietmap (Chỉ trả về danh sách khi không hỏi mã cụ thể)
        has_specific_vietmap = any(m in clean_text for m in ['m1', 'm2', 's720', 'r440', 's860', 'bs10', 'kc01', 'speedmap'])
        if any(k in clean_text for k in ['vietmap']) and not has_specific_vietmap and not any(k in clean_text for k in ['70mai', 'so sanh']):
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "📹 **BÁO GIÁ CAMERA HÀNH TRÌNH VIETMAP (CẢNH BÁO GIAO THÔNG):**\n"
                    "• **Vietmap M1 2K (Trước + Sau):** **6.190.000 đ** *(Luôn báo tốc độ giới hạn + Phạt nguội - Bán chạy nhất)*\n"
                    "• **Vietmap M2 4K (Trước + Sau):** **8.980.000 đ** *(Tặng SIM 12 tháng xem từ xa qua 4G)*\n"
                    "• **Vietmap S720 (Trước + Sau):** **3.900.000 đ**\n"
                    "• **Vietmap R440 Cam Gương (Trước + Sau):** **3.990.000 đ**\n"
                    "• **Vietmap S860 (Trước + Sau):** **4.590.000 đ**\n"
                    "🎁 Tặng thẻ nhớ chính hãng, miễn phí đi dây âm kín tại gara."
                )
            }

        res = "📹 **BÁO GIÁ CAMERA HÀNH TRÌNH CHÍNH HÃNG:**\n"
        res += "🌟 **Dòng Vietmap (Cảnh báo tốc độ & phạt nguội):**\n"
        res += "• **Vietmap M1 2K (Trước + Sau):** **6.190.000 đ** *(Bán chạy nhất)*\n"
        res += "• **Vietmap M2 4K (Trước + Sau):** **8.980.000 đ** *(Tặng SIM 12 tháng xem từ xa)*\n"
        res += "• Vietmap S720: **3.9tr** | Cam gương R440: **3.99tr** | S860: **4.59tr**\n"
        res += "🌟 **Dòng 70mai Xiaomi (Độ nét cao):**\n"
        res += "• 70mai 310 Plus (Trước): **1.5tr** | A200 2K (Trước+Sau): **2.5tr** | M500: **2.8tr**\n"
        res += "• 70mai A510 3K (Trước+Sau, Sony Starvis 2): **3.4tr** | A800SE 4K: **3.6tr** | A800SE SpeedEye: **4.8tr**\n"
        res += "• Cam gương S410: **4.15tr** | Omni 360 xoay tròn: **3.9tr - 4.2tr**"
        return {"type": "success", "module": "dichvu", "message": res}

    # 8.6. BỌC GHẾ DA Ô TÔ
    is_gheda = ('tran' not in clean_text) and (
        ('ghe' in clean_text and any(k in clean_text for k in ['da', 'boc', 'may', 'thay', 'lam', 'gia', 'tu van', 'xe', 'oto'])) or
        any(k in clean_text for k in ['boc ghe', 'ghe da', 'da ghe', 'may ghe', 'thay da', 'thay ghe', 'lam ghe', 'boc da', 'nappa', 'simili', 'da cong nghiep', 'gia boc ghe', 'boc nem', 'nem da'])
    )
    if is_gheda:
        is_4c = any(k in clean_text for k in ['4', '5', 'sedan', 'hatchback'])
        is_7c = any(k in clean_text for k in ['7', 'suv', 'mpv'])

        if is_4c and not is_7c:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "🚗 **BÁO GIÁ BỌC GHẾ DA XE 4 - 5 CHỖ:**\n"
                    "• **Da Simili:** **3.500.000 đ** (Tiết kiệm, chống nước)\n"
                    "• **Da Công Nghiệp cao cấp:** **6.000.000 đ** (Mềm mát, bền 4-5 năm - Bán chạy nhất)\n"
                    "• **Da Nappa cao cấp:** **9.500.000 đ** (Chuẩn xe sang, đục lỗ thoát khí +1.000.000 đ)."
                )
            }

        if is_7c and not is_4c:
            return {
                "type": "success",
                "module": "dichvu",
                "message": (
                    "🚐 **BÁO GIÁ BỌC GHẾ DA XE 7 CHỖ:**\n"
                    "• **Da Simili:** **6.000.000 đ**\n"
                    "• **Da Công Nghiệp cao cấp:** **7.500.000 đ** (Mềm mát, bền 4-5 năm)\n"
                    "• **Da Nappa cao cấp:** **12.000.000 đ** (Chuẩn xe sang, đục lỗ thoát khí +1.000.000 đ)."
                )
            }

        res = "💺 **BÁO GIÁ BỌC GHẾ DA Ô TÔ (TRẦN BÌNH AUTO):**\n"
        res += "• **Da Simili:** 4 chỗ **3.500.000 đ** | 7 chỗ **6.000.000 đ**\n"
        res += "• **Da Công Nghiệp:** 4 chỗ **6.000.000 đ** | 7 chỗ **7.500.000 đ** *(Bán chạy nhất)*\n"
        res += "• **Da Nappa:** 4 chỗ **9.500.000 đ** | 7 chỗ **12.000.000 đ** *(Đục lỗ thoát khí +1.000.000 đ)*"
        return {"type": "success", "module": "dichvu", "message": res}

    return None


# ─────────────────────────────────────────────────────────────────────────────
# 7. CHUYÊN GIA TƯ VẤN PHIM BẢO VỆ SƠN PPF (AX FILM, 3M, TECKWRAP)
# ─────────────────────────────────────────────────────────────────────────────

PPF_DATA = {
    "AX_FILM": {
        "brand": "AX Film",
        "warranty_note": "Bảo hành 2.5 - 10 năm chống rạn nứt, phồng rộp, ố vàng. Bảo hiểm vật liệu 01 năm cho dòng PPF X Series chính hãng.",
        "packages": [
            {"name": "AX Film G Series", "thick": "7.5 Mil", "war": "2.5 năm", "sedan": 20000000, "suv": 22000000, "mpv": 25000000, "desc": "Gói tiêu chuẩn tiết kiệm, bảo vệ sơn chống trầy xước nhẹ và đá dăm văng."},
            {"name": "AX Film K Series (NEW)", "thick": "8.0 Mil", "war": "05 năm", "sedan": 26900000, "suv": 29600000, "mpv": 33000000, "desc": "Dòng mới ra mắt độ dày 8.0 Mil tăng cường chịu lực, tự phục hồi xước xoáy, độ bóng cao."},
            {"name": "AX Film X Series (NEW)", "thick": "9.0 Mil", "war": "08 năm", "sedan": 45000000, "suv": 49500000, "mpv": 54500000, "desc": "Dòng cao cấp 9.0 Mil cực kỳ bền bỉ, chống ố vàng vượt trội, tặng kèm gói bảo hiểm vật liệu 01 năm chính hãng."},
            {"name": "AX Film M Series (Nhám Mờ)", "thick": "7.5 Mil", "war": "05 năm", "sedan": 60000000, "suv": 66000000, "mpv": 75000000, "desc": "Dòng phim mờ (Matte) cao cấp, tạo hiệu ứng sơn nhám mờ như siêu xe, chống bám bẩn tuyệt đối."},
            {"name": "AX Film S Series (Đỉnh Cao)", "thick": "9.5 Mil", "war": "10 năm", "sedan": 90000000, "suv": 99000000, "mpv": 119000000, "desc": "Dòng đỉnh cao siêu cấp độ dày khủng 9.5 Mil, bảo hành 10 năm, độ trong suốt quang học và bảo vệ tối đa."}
        ]
    },
    "3M": {
        "brand": "3M Scotchgard Paint Protection Film (USA)",
        "warranty_note": "Bảo hành điện tử chính hãng 3M từ 5 - 10 năm. Thương hiệu bảo vệ sơn số 1 toàn cầu.",
        "packages": [
            {"name": "3M 50 Gloss Series", "thick": "7.3 Mil", "war": "5 năm", "sedan": 38000000, "suv": 44000000, "mpv": 51000000, "desc": "Phim bóng tiêu chuẩn 3M, tự phục hồi vết xước nhẹ dưới ánh nắng hoặc nhiệt độ."},
            {"name": "3M 100 Gloss Series", "thick": "7.5 Mil", "war": "7 năm", "sedan": 69000000, "suv": 76000000, "mpv": 84000000, "desc": "Dòng bán chạy nhất của 3M, độ bóng sâu, kháng ố vàng, kháng hóa chất tẩy rửa cực tốt."},
            {"name": "3M 150 Gloss Series", "thick": "7.5 Mil", "war": "10 năm", "sedan": 85000000, "suv": 92000000, "mpv": 102000000, "desc": "Dòng cao cấp bảo hành 10 năm, bề mặt siêu mịn chống bám nước lá sen, duy trì độ mới trọn đời xe."},
            {"name": "3M 200 Gloss Series", "thick": "7.9 Mil", "war": "10 năm", "sedan": 102000000, "suv": 110000000, "mpv": 122000000, "desc": "Dòng siêu cao cấp nhất của 3M độ dày 7.9 Mil, chống chịu va đập mạnh, độ bóng gương hoàn hảo."}
        ],
        "parts": [
            ("Nắp capo", 11000000, "Vùng đầu xe dễ bị đá dăm văng"),
            ("Cản trước", 12000000, "Bộ phận va quẹt nhiều nhất khi đi phố"),
            ("Cản sau", 15000000, "Bảo vệ đuôi xe khi lùi hoặc xe sau quẹt"),
            ("4 Cửa xe", 12000000, "Chống trầy xước mép cửa và bề mặt hông xe"),
            ("Đèn trước (Pha)", 3000000, "Chống ố vàng, rạn chân chim và đá bắn vỡ mặt đèn"),
            ("Đèn sau (Hậu)", 3000000, "Bảo vệ bề mặt mica đèn luôn trong bóng"),
            ("Gương chiếu hậu", 2000000, "Vị trí nhô ra ngoài dễ va quẹt xe máy"),
            ("4 Hõm / Tay nắm cửa", 12000000, "Bảo vệ hõm và tay nắm chống xước móng tay/nhẫn"),
            ("Cốp xe", 2500000, "Chống trầy xước khi bốc dỡ vali đồ đạc"),
            ("Bệ bước chân", 3500000, "Chống trầy xước giày dép khi lên xuống xe"),
            ("Cột B (Trụ bóng)", 2500000, "Chống xước dăm bề mặt bóng piano"),
            ("Nóc xe", 8000000, "Bảo vệ nóc chống phân chim, nhựa cây, axit mưa")
        ]
    },
    "TECKWRAP": {
        "brand": "TeckWrap PPF Professional (USA)",
        "warranty_note": "Bảo hành chính hãng 4 - 7 năm. Độ bền bỉ và độ bóng gương hàng đầu từ Mỹ.",
        "packages": [
            {"name": "TeckWrap V75 ACCESS", "thick": "7.4 Mil", "war": "4 năm", "sedan": 25000000, "suv": 27000000, "mpv": 29000000, "desc": "Bảo vệ sơn chi phí tiết kiệm, truyền sáng ≥88%, hiệu ứng lá sen, độ bóng tiêu chuẩn, chống xước và phục hồi tốt."},
            {"name": "TeckWrap X75 CORE", "thick": "7.5 Mil", "war": "4 năm", "sedan": 28000000, "suv": 30000000, "mpv": 33000000, "desc": "Bảo vệ tiêu chuẩn độ bóng tốt, ngăn UV ≥95%, hiệu ứng lá sen tốt, chống xước & phục hồi xước tốt."},
            {"name": "TeckWrap G75 TITAN", "thick": "7.5 Mil", "war": "6 năm", "sedan": 37000000, "suv": 40000000, "mpv": 44000000, "desc": "Bảo vệ hoàn hảo, siêu bóng vượt trội, ngăn UV ≥95%, lá sen rất tốt, chống xước & phục hồi rất tốt."},
            {"name": "TeckWrap S75+ ELITE", "thick": "7.5 Mil", "war": "7 năm", "sedan": 45000000, "suv": 50000000, "mpv": 55000000, "desc": "Bảo vệ hoàn hảo bền bỉ, ngăn UV ≥95%, độ bóng tuyệt đối, chống xước và tự phục hồi cực tốt."}
        ]
    }
}

def handle_ppf_consultation(raw_text, clean_text):
    """
    Chuyên gia tư vấn dán Phim bảo vệ sơn PPF (AX Film, 3M, TeckWrap):
    - Báo giá theo hãng (AX Film, 3M, TeckWrap)
    - Báo giá theo kiểu xe (Sedan, SUV, MPV)
    - Báo giá dán chi tiết từng phần (Capo, Cản trước, Đèn, Cửa...)
    - Tư vấn phân khúc theo túi tiền và thông số kỹ thuật (độ dày mil, UV, lá sen, tự phục hồi)
    """
    is_ppf = bool(re.search(r'\b(ppf|ppfilm|ax\s*film|teckwrap|teck\s*wrap|3m\s*ppf|scotchgard|bao\s*ve\s*son|phim\s*bao\s*ve|dan\s*phim\s*son|dan\s*ppf)\b', clean_text)) or \
             (any(k in clean_text for k in ['dan capo', 'dan den', 'dan can truoc', 'dan 4 cua', 'dan guong', 'dan noc']) and not any(k in clean_text for k in ['do den', 'bi led', 'bi gam']))

    if not is_ppf:
        return None

    # 1. Khách hỏi giá DÁN LẺ TỪNG PHẦN (Chi tiết)
    is_part_query = any(k in clean_text for k in [
        'tung phan', 'chi tiet', 'le', 'capo', 'can truoc', 'can sau', 'cua', 'den', 
        'guong', 'hom cua', 'tay nam', 'cop', 'be buoc', 'cot b', 'noc'
    ]) and not any(k in clean_text for k in ['full', 'nguyen xe', 'toan bo xe'])

    if is_part_query and any(k in clean_text for k in ['gia', 'bao nhieu', 'nhieu tien', 'bang gia', 'dan', 'het']):
        specific_part = None
        for p_name, p_price, p_note in PPF_DATA["3M"]["parts"]:
            p_clean = remove_accents(p_name).lower()
            if any(tok in clean_text for tok in p_clean.split() if len(tok) >= 3):
                specific_part = (p_name, p_price, p_note)
                break

        res = "🛡️ **BẢNG GIÁ DÁN PPF TỪNG PHẦN (DÒNG 3M 100 GLOSS SERIES CAO CẤP)**\n"
        res += "*(Bảo hành chính hãng 3M 7 năm - Độ bóng gương sâu, chống ố vàng & đá dăm)*\n"
        res += "───────────────────────────\n"
        if specific_part:
            res += f"🎯 **VỊ TRÍ BẠN ĐANG HỎI:**\n"
            res += f"👉 **{specific_part[0]}:** **{specific_part[1]:,.0f} đ** *({specific_part[2]})*\n\n"
            res += "📋 **BẢNG GIÁ CÁC VỊ TRÍ KHÁC TRÊN XE:**\n"

        for p_name, p_price, p_note in PPF_DATA["3M"]["parts"]:
            res += f"• **{p_name}:** **{p_price:,.0f} đ** *({p_note})*\n"
        res += "───────────────────────────\n"
        res += "💡 *Lời khuyên: Nếu chưa đủ ngân sách dán full xe, bạn nên ưu tiên gói **Bảo Vệ Đầu Xe (Nắp Capo + Cản Trước + Cặp Đèn Pha = 26 triệu)** vì đây là nơi chịu 85% nguy cơ va quẹt và đá dăm văng khi chạy trên đường!*\n"
        return {"type": "success", "module": "ppf", "message": res}

    # 2. Khách hỏi riêng HÃNG AX FILM
    if any(k in clean_text for k in ['ax film', 'ax', 'g series', 'k series', 'x series', 'm series', 's series']):
        res = "🛡️ **BẢNG GIÁ DÁN PPF CHÍNH HÃNG AX FILM (Áp dụng từ 15/06/2025)**\n"
        res += f"*(Chính sách: {PPF_DATA['AX_FILM']['warranty_note']})*\n"
        res += "───────────────────────────\n"
        for pkg in PPF_DATA["AX_FILM"]["packages"]:
            res += f"🔹 **{pkg['name']}** (Độ dày: **{pkg['thick']}** | BH: **{pkg['war']}**)\n"
            res += f"  - 🚗 Sedan: **{pkg['sedan']:,.0f} đ** | SUV: **{pkg['suv']:,.0f} đ** | MPV: **{pkg['mpv']:,.0f} đ**\n"
            res += f"  - *Đặc tính:* {pkg['desc']}\n\n"
        res += "───────────────────────────\n"
        res += "💡 **Ưu đãi đặc biệt:** Dòng **PPF X Series (9.0 Mil)** được tặng kèm **gói Bảo Hiểm Vật Liệu Phim 01 năm chính hãng AX Film** (thay thế phim mới khi có sự cố va chạm)!"
        return {"type": "success", "module": "ppf", "message": res}

    # 3. Khách hỏi riêng HÃNG 3M SCOTCHGARD
    if any(k in clean_text for k in ['3m', 'scotchgard', '50 gloss', '100 gloss', '150 gloss', '200 gloss']):
        res = "🛡️ **BẢNG GIÁ DÁN PPF CHÍNH HÃNG 3M SCOTCHGARD (USA)**\n"
        res += f"*(Chính sách: {PPF_DATA['3M']['warranty_note']})*\n"
        res += "───────────────────────────\n"
        res += "📋 **1. BẢNG GIÁ DÁN FULL XE:**\n"
        for pkg in PPF_DATA["3M"]["packages"]:
            res += f"🔹 **{pkg['name']}** (Độ dày: **{pkg['thick']}** | BH: **{pkg['war']}**)\n"
            res += f"  - 🚗 Sedan: **{pkg['sedan']:,.0f} đ** | SUV: **{pkg['suv']:,.0f} đ** | MPV: **{pkg['mpv']:,.0f} đ**\n"
            res += f"  - *Đặc tính:* {pkg['desc']}\n\n"
        res += "───────────────────────────\n"
        res += "📋 **2. BẢNG GIÁ BÁN LẺ TỪNG PHẦN (DÒNG 100 GLOSS SERIES):**\n"
        for p_name, p_price, _ in PPF_DATA["3M"]["parts"][:6]:
            res += f"• {p_name}: **{p_price:,.0f} đ**  |  "
        res += f"\n👉 Gõ *'giá ppf từng phần'* để xem bảng giá lẻ chi tiết tất cả các vị trí."
        return {"type": "success", "module": "ppf", "message": res}

    # 4. Khách hỏi riêng HÃNG TECKWRAP USA
    if any(k in clean_text for k in ['teckwrap', 'teck wrap', 'v75', 'x75', 'g75', 's75']):
        res = "🛡️ **BẢNG GIÁ VÀ THÔNG SỐ KỸ THUẬT PPF TECKWRAP (USA)**\n"
        res += f"*(Chính sách: {PPF_DATA['TECKWRAP']['warranty_note']})*\n"
        res += "───────────────────────────\n"
        for pkg in PPF_DATA["TECKWRAP"]["packages"]:
            res += f"🔹 **{pkg['name']}** (Độ dày: **{pkg['thick']}** | BH: **{pkg['war']}**)\n"
            res += f"  - 🚗 Sedan: **{pkg['sedan']:,.0f} đ** | SUV: **{pkg['suv']:,.0f} đ** | MPV: **{pkg['mpv']:,.0f} đ**\n"
            res += f"  - *Thông số & Tính năng:* {pkg['desc']}\n\n"
        res += "───────────────────────────\n"
        res += "💡 **Ưu điểm TeckWrap:** Độ bóng sâu gương như tráng gốm Ceramic, tự lành vết xước khi tiếp xúc nhiệt ấm và ngăn tia UV tuyệt đối ≥95% chống bạc màu sơn zin."
        return {"type": "success", "module": "ppf", "message": res}

    # 5. Khách hỏi theo DÒNG XE CỤ THỂ (Sedan, SUV, MPV)
    is_sedan = bool(re.search(r'\b(sedan|vios|accent|city|camry|mazda 3|mazda 6|civic|k3|cerato|altis|c200|c300|e200|e300|bmw 3|bmw 5)\b', clean_text))
    is_suv = bool(re.search(r'\b(suv|cuv|cx5|cx-5|cx8|crv|cr-v|tucson|santafe|santa fe|everest|fortuner|seltos|creta|territory|cross|corolla cross)\b', clean_text))
    is_mpv = bool(re.search(r'\b(mpv|carnival|custin|innova|xpander|stargazer|veloz|avanza|carens|sedona)\b', clean_text))

    if is_sedan or is_suv or is_mpv:
        car_type = "sedan" if is_sedan else ("suv" if is_suv else "mpv")
        car_title = "SEDAN (Xe 4-5 chỗ)" if car_type == "sedan" else ("SUV / CUV (Xe gầm cao)" if car_type == "suv" else "MPV / 7 CHỖ CỠ LỚN")

        res = f"🛡️ **BẢNG SO SÁNH GIÁ DÁN PPF FULL XE CHO DÒNG {car_title}**\n"
        res += "───────────────────────────\n"
        res += "🟢 **1. PHÂN KHÚC TIẾT KIỆM (DƯỚI 30 TRIỆU):**\n"
        res += f"• **AX Film G Series (7.5 Mil - BH 2.5 năm):** **{PPF_DATA['AX_FILM']['packages'][0][car_type]:,.0f} đ**\n"
        res += f"• **TeckWrap V75 Access (7.4 Mil - BH 4 năm):** **{PPF_DATA['TECKWRAP']['packages'][0][car_type]:,.0f} đ**\n"
        res += f"• **AX Film K Series (8.0 Mil - BH 5 năm):** **{PPF_DATA['AX_FILM']['packages'][1][car_type]:,.0f} đ**\n"
        res += f"• **TeckWrap X75 Core (7.5 Mil - BH 4 năm):** **{PPF_DATA['TECKWRAP']['packages'][1][car_type]:,.0f} đ**\n\n"

        res += "🟡 **2. PHÂN KHÚC TẦM TRUNG - BÁN CHẠY NHẤT (35 - 55 TRIỆU):**\n"
        res += f"• **TeckWrap G75 Titan (Siêu bóng - BH 6 năm):** **{PPF_DATA['TECKWRAP']['packages'][2][car_type]:,.0f} đ**\n"
        res += f"• **3M 50 Gloss Series (Chính hãng 3M - BH 5 năm):** **{PPF_DATA['3M']['packages'][0][car_type]:,.0f} đ**\n"
        res += f"• **TeckWrap S75+ Elite (Bóng tuyệt đối - BH 7 năm):** **{PPF_DATA['TECKWRAP']['packages'][3][car_type]:,.0f} đ**\n"
        res += f"• **AX Film X Series (9.0 Mil Siêu Bền - BH 8 năm + Bảo hiểm 1 năm):** **{PPF_DATA['AX_FILM']['packages'][2][car_type]:,.0f} đ**\n\n"

        res += "🟣 **3. PHÂN KHÚC CAO CẤP & ĐỈNH CAO (TRÊN 60 TRIỆU):**\n"
        res += f"• **AX Film M Series (Nhám Mờ Matte sang trọng - BH 5 năm):** **{PPF_DATA['AX_FILM']['packages'][3][car_type]:,.0f} đ**\n"
        res += f"• **3M 100 Gloss Series (Dòng bán chạy nhất của 3M - BH 7 năm):** **{PPF_DATA['3M']['packages'][1][car_type]:,.0f} đ**\n"
        res += f"• **3M 150 Gloss Series (Cao cấp - BH 10 năm):** **{PPF_DATA['3M']['packages'][2][car_type]:,.0f} đ**\n"
        res += f"• **AX Film S Series (9.5 Mil Đỉnh Cao - BH 10 năm):** **{PPF_DATA['AX_FILM']['packages'][4][car_type]:,.0f} đ**\n"
        res += f"• **3M 200 Gloss Series (Đỉnh cao nhất 3M - BH 10 năm):** **{PPF_DATA['3M']['packages'][3][car_type]:,.0f} đ**\n\n"
        res += "👉 Bạn muốn tư vấn kỹ hơn về thương hiệu nào (AX Film, 3M hay TeckWrap)?"
        return {"type": "success", "module": "ppf", "message": res}

    # 6. KHÁCH HỎI TƯ VẤN CHUNG VỀ PPF
    res = "🛡️ **CHUYÊN GIA TƯ VẤN PHIM BẢO VỆ SƠN Ô TÔ (PPF) - TRẦN BÌNH AUTO**\n\n"
    res += "Gara hiện phân phối & thi công chính hãng **3 thương hiệu PPF hàng đầu thế giới**:\n\n"
    
    res += "🌟 **1. AX FILM (Công nghệ tiên tiến - Bền bỉ vượt trội):**\n"
    res += "• **G Series (7.5 Mil - BH 2.5 năm):** từ **20.000.000 đ**\n"
    res += "• **K Series (8.0 Mil - BH 5 năm):** từ **26.900.000 đ** *(Khuyên dùng phân khúc phổ thông)*\n"
    res += "• **X Series (9.0 Mil - BH 8 năm):** từ **45.000.000 đ** *(Tặng kèm Bảo hiểm vật liệu 01 năm)*\n"
    res += "• **M Series Phim Mờ (7.5 Mil - BH 5 năm):** từ **60.000.000 đ**\n"
    res += "• **S Series Siêu Cấp (9.5 Mil - BH 10 năm):** từ **90.000.000 đ**\n\n"

    res += "🌟 **2. TECKWRAP USA (Chuyên gia Wrap & PPF Mỹ):**\n"
    res += "• **V75 Access (7.4 Mil - BH 4 năm):** từ **25.000.000 đ**\n"
    res += "• **X75 Core (7.5 Mil - BH 4 năm):** từ **28.000.000 đ**\n"
    res += "• **G75 Titan Siêu Bóng (7.5 Mil - BH 6 năm):** từ **37.000.000 đ** *(Rất được ưa chuộng)*\n"
    res += "• **S75+ Elite Bền Bỉ (7.5 Mil - BH 7 năm):** từ **45.000.000 đ**\n\n"

    res += "🌟 **3. 3M SCOTCHGARD (Thương hiệu số 1 toàn cầu - USA):**\n"
    res += "• **3M 50 Gloss (BH 5 năm):** từ **38.000.000 đ**\n"
    res += "• **3M 100 Gloss (BH 7 năm):** từ **69.000.000 đ**\n"
    res += "• **3M 150 Gloss (BH 10 năm):** từ **85.000.000 đ**\n"
    res += "• **3M 200 Gloss (BH 10 năm):** từ **102.000.000 đ**\n"
    res += "• *Có gói dán lẻ từng bộ phận:* Capo (11tr), Cản trước (12tr), Cặp đèn pha (3tr), 4 Cửa (12tr)...\n\n"

    res += "───────────────────────────\n"
    res += "🎯 **LỜI KHUYÊN TƯ VẤN NHANH:**\n"
    res += "• **Tài chính vừa phải (25 - 30tr):** Chọn **AX Film K Series (26.9tr)** hoặc **TeckWrap X75 Core (28tr)**.\n"
    res += "• **Cần độ bóng siêu sâu & kháng ố vàng (37 - 50tr):** Chọn **TeckWrap G75 Titan (37tr)** hoặc **AX Film X Series 9.0 Mil (45tr)**.\n"
    res += "• **Yêu cầu thương hiệu đỉnh cao & bảo hành 7-10 năm:** Chọn **3M 100 Gloss** hoặc **AX Film S Series**.\n"
    res += "• **Chỉ muốn bảo vệ điểm va quẹt:** Chọn dán gói đầu xe gồm **Nắp Capo + Cản Trước + Cặp Đèn**.\n\n"
    res += "👉 Bạn đang chạy dòng xe gì (Sedan, SUV hay MPV) để tôi báo giá chính xác nhất?"

    return {"type": "success", "module": "ppf", "message": res}

# ─────────────────────────────────────────────────────────────────────────────
# ĐIỀU PHỐI VIÊN CHÍNH (MAIN DISPATCHER)
# ─────────────────────────────────────────────────────────────────────────────

def ask_clarification(raw_text, clean_text, session_id):
    """
    Chủ động hỏi lại người dùng khi AI chưa hiểu rõ ý định,
    phân tích manh mối ngữ cảnh và đưa ra các lựa chọn để người dùng chọn nhanh.
    """
    hint_action = None
    hint_name = None

    if any(k in clean_text for k in ['da', 'ghe', 'nem', 'boc da', 'lot ghe']):
        hint_action = 'boc ghe da'
        hint_name = 'Bọc Ghế Da Ô Tô'
    elif any(k in clean_text for k in ['tran', 'la phong', 'nilon', 'nilong', 'kim cuong']):
        hint_action = 'boc tran'
        hint_name = 'Bọc Trần Ô Tô'
    elif any(k in clean_text for k in ['film', 'phim', 'kinh', 'cach nhiet', 'chong nong']):
        hint_action = 'tu van film'
        hint_name = 'Dán Phim Cách Nhiệt Ô Tô'
    elif any(k in clean_text for k in ['man', 'dvd', 'android', 'winca', 'gotech', 'bravo']):
        hint_action = 'man hinh'
        hint_name = 'Màn Hình Android & Cam 360'
    elif any(k in clean_text for k in ['cam', 'camera', 'hanh trinh', 'toc do', 'phat nguoi']):
        hint_action = 'cam hanh trinh'
        hint_name = 'Camera Hành Trình'
    elif any(k in clean_text for k in ['box', 'man zin']):
        hint_action = 'android box'
        hint_name = 'Android Box Ô Tô'
    elif any(k in clean_text for k in ['ppf', 'son', 'tray', 'keo']):
        hint_action = 'tu van ppf'
        hint_name = 'Dán Phim PPF Bảo Vệ Sơn'

    candidates = {
        '1': 'tu van film',
        '2': 'boc ghe da',
        '3': 'boc tran',
        '4': 'man hinh',
        '5': 'cam hanh trinh',
        '6': 'android box',
        '7': 'tu van ppf',
        '8': 'doanh thu den',
        '9': 'chi'
    }

    WIZARD_SESSIONS[session_id] = {
        'flow': 'clarify',
        'step': 1,
        'data': {
            'hint_action': hint_action,
            'hint_name': hint_name,
            'candidates': candidates,
            'raw_q': raw_text
        }
    }

    if hint_name:
        msg = f"🤔 **Tôi chưa hiểu rõ ý bạn về: '{raw_text}'.**\n"
        msg += f"Có phải bạn đang muốn hỏi về **{hint_name}** không ạ?\n\n"
        msg += f"👉 Gõ **'đúng rồi'** hoặc **'ừ'** để tôi tư vấn ngay.\n"
        msg += f"👉 Hoặc chọn số dịch vụ bên dưới:\n"
    else:
        msg = f"🤔 **Dạ, bạn muốn Trần Bình Auto tư vấn về dịch vụ nào ạ?**\n\n"

    msg += "1️⃣ **Dán Phim Cách Nhiệt** *(3M, Ceramax, Ntech)*\n"
    msg += "2️⃣ **Bọc Ghế Da Ô Tô** *(Simili, Da Công Nghiệp, Nappa)*\n"
    msg += "3️⃣ **Bọc Trần Ô Tô** *(Kim Cương 5D/6D, Nilong)*\n"
    msg += "4️⃣ **Màn Hình Android & Cam 360** *(Winca, Gotech, Bravo)*\n"
    msg += "5️⃣ **Camera Hành Trình** *(Vietmap M1, 70mai A510/A200)*\n"
    msg += "6️⃣ **Android Box** *(Vietmap BS10, iCar D4)*\n"
    msg += "7️⃣ **Dán Phim PPF Bảo Vệ Sơn Xe**\n"
    msg += "8️⃣ **Nhập Đơn Báo Cáo Đèn** | 9️⃣ **Ghi Sổ Chi**\n\n"
    msg += "*(Bạn có thể gõ số `1`, `2`... hoặc gõ chi tiết câu hỏi để tôi trả lời chính xác nhất nhé!)*"

    return {"type": "clarify", "message": msg}


def parse_and_execute_admin_command(raw, clean, session_id='default_user'):
    """Xử lý siêu tốc các thao tác quản trị trực tiếp trên Database nội bộ (< 0.005 giây)"""
    # 0. Tự động nhận diện và lưu API Key Gemini mới khi người dùng gửi trong chat
    m_key = re.search(r'\b(AIzaSy[A-Za-z0-9_-]{33}|AQ\.[A-Za-z0-9_-]{40,65})\b', raw)
    if m_key:
        new_key = m_key.group(1)
        cfg = {"api_key": new_key, "preferred_model": "gemini-3.5-flash-lite", "fallback_model": "gemini-3.5-flash", "enabled": True}
        try:
            if gemini_engine:
                with open(gemini_engine.CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                gemini_engine.DEFAULT_API_KEY = new_key
                gemini_engine.GEMINI_CLIENT = None
                gemini_engine.GEMINI_SESSIONS.clear()
            return {
                "type": "success",
                "message": (
                    f"🔑 **ĐÃ LƯU & KÍCH HOẠT API KEY GEMINI MỚI THÀNH CÔNG!**\n"
                    f"─────────────────────────────────────────\n"
                    f"• Key: `{new_key[:8]}...{new_key[-4:]}`\n"
                    f"• Model siêu tốc: **Gemini 3.5 Flash Lite** (Phản hồi < 1.5s)\n"
                    f"👉 Toàn bộ các tính năng AI thông minh thế hệ mới đã sẵn sàng phục vụ anh!"
                )
            }
        except Exception as e:
            return {"type": "error", "message": f"Lỗi lưu API Key: {str(e)}"}

    # 1. Chỉnh sửa đơn hàng siêu tốc
    if any(k in clean for k in ['sua don', 'chinh don', 'doi don']):
        m_id = re.search(r'(?:don|don den|don ban hang|don hang|ma)?\s*#?(\d{3,6})\b', clean)
        if m_id and gemini_engine:
            order_id = int(m_id.group(1))
            new_cust = ""
            m_cust = re.search(r'(?:doi|thanh|sang)?\s*(?:ten khach|khach hang|khach)\s*(?:la|thanh|sang)?\s*([^,\.\n]+?)(?:\s+(?:sdt|so dien thoai|bien so|xe|dong xe|gia|ngay)|$)', clean)
            if m_cust:
                new_cust = m_cust.group(1).strip().title()

            new_car = ""
            m_car = re.search(r'(?:xe|dong xe)\s*(?:la|thanh|sang)?\s*([A-Za-z0-9\s]+?)(?:\s+(?:sdt|bien so|gia|ngay)|$)', clean)
            if m_car:
                new_car = m_car.group(1).strip().upper()

            new_phone = ""
            m_phone = re.search(r'\b(0[35789]\d{8})\b', raw)
            if m_phone:
                new_phone = m_phone.group(1)

            new_plate = ""
            m_plate = re.search(r'\b(\d{2}[A-Za-z]\s*[-.]?\s*\d{3,5}(?:\.\d{2})?)\b', raw)
            if m_plate:
                new_plate = m_plate.group(1).upper()

            changes = []
            if new_cust: changes.append(f"Tên khách mới: **{new_cust}**")
            if new_car: changes.append(f"Dòng xe mới: **{new_car}**")
            if new_phone: changes.append(f"SĐT mới: **{new_phone}**")
            if new_plate: changes.append(f"Biển số mới: **{new_plate}**")
            change_txt = "\n".join([f"  - {c}" for c in changes]) if changes else "Cập nhật thông tin chi tiết đơn hàng"

            confirm_msg = (
                f"❓ **XÁC NHẬN CHỈNH SỬA ĐƠN HÀNG #{order_id}:**\n"
                f"─────────────────────────────────────────\n"
                f"• Mã đơn: **#{order_id}**\n"
                f"• Các thông tin điều chỉnh:\n{change_txt}\n"
                f"─────────────────────────────────────────\n"
                f"👉 Anh có chắc chắn muốn **CẬP NHẬT ĐƠN HÀNG NÀY** không?\n\n"
                f"*(Bấm **[✅ OK / Lưu]** hoặc gõ **'ok'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"
            )

            WIZARD_SESSIONS[session_id] = {
                'flow': 'confirm_action',
                'action_type': 'admin_edit_order',
                'payload': {
                    'kwargs': {
                        'ma_don_hang': order_id,
                        'ten_khach_moi': new_cust,
                        'dong_xe_moi': new_car,
                        'sdt_moi': new_phone,
                        'bien_so_moi': new_plate
                    }
                }
            }
            return {"type": "clarify", "message": confirm_msg}

    # 2. Cập nhật tồn kho sản phẩm siêu tốc
    if any(k in clean for k in ['cap nhat kho', 'ton kho', 'nhap kho', 'sua kho']):
        m_code = re.search(r'\b(SP\d+|A\d+|M\d+|F10|S\d+)\b', raw, re.IGNORECASE)
        m_qty = re.search(r'(?:thanh|con|la|so luong)\s*(\d{1,4})\s*(?:cai|bo|chiec)?\b', clean)
        if m_code and m_qty and gemini_engine:
            code = m_code.group(1).upper()
            qty = int(m_qty.group(1))
            confirm_msg = (
                f"❓ **XÁC NHẬN CẬP NHẬT TỒN KHO:**\n"
                f"─────────────────────────────────────────\n"
                f"• Sản phẩm: **{code}**\n"
                f"• Tồn kho điều chỉnh: **{qty}** bộ / chiếc\n"
                f"─────────────────────────────────────────\n"
                f"👉 Anh có muốn **LƯU SỐ LƯỢNG NÀY VÀO KHO HÀNG** không?\n\n"
                f"*(Bấm **[✅ OK / Lưu]** hoặc gõ **'ok'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"
            )
            WIZARD_SESSIONS[session_id] = {
                'flow': 'confirm_action',
                'action_type': 'admin_update_stock',
                'payload': {'kwargs': {'ma_hoac_ten_sp': code, 'ton_kho_moi': qty}}
            }
            return {"type": "clarify", "message": confirm_msg}

    # 3. Xóa đơn hàng siêu tốc
    if any(k in clean for k in ['xoa don', 'huy don']):
        m_id = re.search(r'(?:don|ma)?\s*#?(\d{3,6})\b', clean)
        if m_id and gemini_engine:
            order_id = int(m_id.group(1))
            confirm_msg = (
                f"⚠️ **CẢNH BÁO: XÁC NHẬN XÓA ĐƠN HÀNG #{order_id}:**\n"
                f"─────────────────────────────────────────\n"
                f"Thao tác này sẽ xóa vĩnh viễn đơn hàng **#{order_id}** khỏi hệ thống dữ liệu!\n"
                f"─────────────────────────────────────────\n"
                f"👉 Anh có chắc chắn muốn **XÓA ĐƠN HÀNG NÀY** không?\n\n"
                f"*(Bấm **[✅ OK / Lưu]** hoặc gõ **'ok'** để xóa | Bấm **[🛑 Hủy]** để hủy bỏ)*"
            )
            WIZARD_SESSIONS[session_id] = {
                'flow': 'confirm_action',
                'action_type': 'admin_delete_order',
                'payload': {'order_id': order_id}
            }
            return {"type": "clarify", "message": confirm_msg}

    return None

def _process_ai_command_internal(user_text, session_id="default_user"):
    """Hàm xử lý mọi câu lệnh từ người dùng gửi qua bong bóng chat AI"""
    if not user_text or not user_text.strip():
        return {
            "type": "clarify",
            "message": "Xin chào! Tôi là **Trợ Lý AI Trần Bình Auto** 🤖.\nTôi có thể giúp bạn:\n\n"
                       "1. **Ghi Sổ Chi Từng Bước:** Nhắn *'chi'* để AI hỏi lần lượt Số tiền ➔ Ngày ➔ Lý do.\n"
                       "2. **Nhập Đơn Đèn Từng Bước:** Nhắn *'doanh thu đèn'* để AI hỏi Tên đèn ➔ Ngày ➔ Số lượng ➔ Giá ➔ Giảm giá ➔ Khách/Biển số ➔ Loại xe.\n"
                       "3. **Nhập 1 Phát Xong Ngay:** *'anh Cường accent f10 new 3900'*, *'chi 350k tiền cơm'*...\n"
                       "4. **Báo Cáo Doanh Số Đèn:** *'doanh thu đèn tháng này'*, *'đơn đèn hôm nay'*, *'top đèn bán chạy'*\n"
                       "5. **Hủy Đơn Đèn Vừa Nhập:** *'hủy đơn đèn vừa nhập'*, *'xóa đơn vừa tạo'*\n\n"
                       "Hãy gõ câu lệnh bạn muốn thực hiện nhé!"
        }

    raw = user_text.strip()
    clean = remove_accents(raw).lower()

    # Nếu câu hỏi quá ngắn hoặc mơ hồ chung chung -> Chủ động hỏi lại làm rõ
    if clean in ['tu van', 'bao gia', 'cho hoi', 'cho toi hoi', 'bang gia', 'dich vu', 'gara co lam gi', 'do xe', 'nang cap xe', 'hoi gia', 'tu van xe', 'xe']:
        return ask_clarification(raw, clean, session_id)

    # ═════════════════════════════════════════════════════════════════════
    # 0. NẾU ĐANG TRONG PHIÊN HỎI ĐÁP TỪNG BƯỚC (WIZARD ACTIVE)
    # ═════════════════════════════════════════════════════════════════════
    if session_id in WIZARD_SESSIONS:
        res = handle_wizard_step(raw, session_id)
        if res:
            return res

    # ═════════════════════════════════════════════════════════════════════
    # ═════════════════════════════════════════════════════════════════════
    # 0.05. CẬP NHẬT / SỬA GIÁ SẢN PHẨM TRỰC TIẾP TRONG KHO (TIEM_LAP_DO.DB)
    # LỆNH: "sửa giá f10 new 2.0 thành 4500", "sửa lại giá a510 giá 3tr5", "đổi giá..."
    # ═════════════════════════════════════════════════════════════════════
    is_price_edit_intent = (
        any(k in clean for k in ['sua gia', 'sua lai gia', 'doi gia', 'cap nhat gia', 'chinh gia']) or         (any(k in clean for k in ['sua lai', 'doi lai', 'chinh lai', 'sua', 'doi', 'chinh', 'cap nhat']) and any(k in clean for k in ['thanh', 'la', 'gia', 'vnd', 'dong', 'k', 'tr', 'trieu', 'nghin', 'ngan']))
    ) and not bool(re.search(r'\b(?:don|ma don|#\d+)\b', clean))

    if is_price_edit_intent:
        from knowledge_base import parse_vietnamese_currency
        p_disp, p_val = parse_vietnamese_currency(raw)
        if p_val > 0:
            prod_txt = raw
            for pat in [
                r'^(?:sửa\s*(?:lại\s*)?giá|sửa\s*giá\s*lại|đổi\s*(?:lại\s*)?giá|đổi\s*giá\s*lại|chỉnh\s*(?:lại\s*)?giá|chỉnh\s*giá\s*lại|cập\s*nhật\s*(?:lại\s*)?giá|cập\s*nhật\s*giá\s*lại|sửa\s*lại|chỉnh\s*lại|cập\s*nhật\s*lại|đổi\s*lại|sửa|đổi|chỉnh|cập\s*nhật)\s*',
            ]:
                prod_txt = re.sub(pat, '', prod_txt, flags=re.IGNORECASE).strip()

            for pat in [
                r'\s+(?:thành|thanh|là|la|giá|gia|giá\s*bán|gia\s*ban)\s+.*$',
                r'\s*[:=]\s*.*$',
                r'\s+\d+(?:[.,]\d+)?\s*(?:tr|trieu|triệu|k|nghin|nghìn|vnd|đ|dong|đồng).*$',
                r'\s+\d{3,7}\s*$',
            ]:
                prod_txt = re.sub(pat, '', prod_txt, flags=re.IGNORECASE).strip()

            if prod_txt:
                found_prods = search_product_in_catalog(prod_txt)
                if found_prods:
                    target_prod = found_prods[0]
                    confirm_msg = (
                        f"❓ **XÁC NHẬN CẬP NHẬT GIÁ SẢN PHẨM:**\n"
                        f"─────────────────────────────────────────\n"
                        f"• 📦 **Sản phẩm:** **{target_prod['name']}**\n"
                        f"• 🏷️ **Mã sản phẩm:** `{target_prod['code']}`\n"
                        f"• 💰 **Giá niêm yết hiện tại:** **{target_prod['price']:,.0f} đ**\n"
                        f"• 🚀 **Mức giá cập nhật mới:** **{p_val:,.0f} đ**\n"
                        f"• 📊 **Tồn kho hiện tại:** {target_prod['stock']}\n"
                        f"─────────────────────────────────────────\n"
                        f"👉 Anh có chắc chắn muốn lưu mức giá mới **{p_val:,.0f} đ** cho sản phẩm này vào hệ thống bán hàng không?\n\n"
                        f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'**, **'lưu'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"
                    )
                    WIZARD_SESSIONS[session_id] = {
                        'flow': 'confirm_action',
                        'action_type': 'update_product_price',
                        'payload': {
                            'product_id': target_prod['id'],
                            'code': target_prod['code'],
                            'name': target_prod['name'],
                            'old_price': target_prod['price'],
                            'new_price': p_val
                        }
                    }
                    return {"type": "clarify", "message": confirm_msg}

    # ═════════════════════════════════════════════════════════════════════
    # 0.1. DẠY HỌC & GHI NHỚ TRI THỨC VÀO BỘ NÃO GARA (PERSISTENT MEMORY)
    # ═════════════════════════════════════════════════════════════════════
    if KNOWLEDGE_AVAILABLE and knowledge_base:
        if knowledge_base.is_learning_command(clean):
            preview = getattr(knowledge_base, 'prepare_learning_preview', lambda x: None)(raw)
            if preview and preview.get('message'):
                WIZARD_SESSIONS[session_id] = {
                    'flow': 'confirm_action',
                    'action_type': 'learn_knowledge',
                    'payload': {'raw_text': raw}
                }
                return {
                    "type": "clarify",
                    "message": preview['message']
                }
            return knowledge_base.analyze_and_learn(raw)

        if clean in ['xem bo nho', 'danh sach ghi nho', 'da nho gi', 'bo nho ai', 'nho nhung gi', 'tri thuc gara']:
            return knowledge_base.list_learned_knowledge()

        if any(k in clean for k in ['xoa ghi nho', 'quen ghi nho', 'xoa bai hoc']):
            confirm_msg = (
                f"❓ **XÁC NHẬN XÓA GHI NHỚ TRI THỨC:**\n"
                f"─────────────────────────────────────────\n"
                f"Anh có chắc chắn muốn xóa bài học tri thức liên quan đến **'{raw}'** khỏi bộ não AI không?\n"
                f"─────────────────────────────────────────\n"
                f"👉 *(Bấm **[✅ OK / Lưu]** hoặc gõ **'ok'** để xóa | Bấm **[🛑 Hủy]** để bỏ qua)*"
            )
            WIZARD_SESSIONS[session_id] = {
                'flow': 'confirm_action',
                'action_type': 'delete_knowledge',
                'payload': {'keyword_or_id': raw}
            }
            return {"type": "clarify", "message": confirm_msg}

    # ═════════════════════════════════════════════════════════════════════
    # 1. KÍCH HOẠT WIZARD SỔ CHI KHI CHỈ NHẮN "CHI" HOẶC "GHI CHI"
    # ═════════════════════════════════════════════════════════════════════
    if clean in ['chi', 'ghi chi', 'nhap chi', 'phieu chi', 'so chi', 'tao phieu chi']:
        WIZARD_SESSIONS[session_id] = {'flow': 'chi', 'step': 1, 'data': {}}
        return {
            "type": "clarify",
            "message": (
                "💸 **BƯỚC 1/3: SỐ TIỀN CHI**\n"
                "───────────────────────────\n"
                "Bạn muốn chi bao nhiêu tiền?\n"
                "*(Ví dụ: `350k`, `1.5tr`, `150.000`... hoặc gõ `hủy` để thoát)*"
            )
        }

    # ═════════════════════════════════════════════════════════════════════
    # 2. KÍCH HOẠT WIZARD DOANH THU ĐÈN KHI NHẮN "DOANH THU ĐÈN" / "NHẬP ĐÈN"
    # ═════════════════════════════════════════════════════════════════════
    if clean in ['doanh thu den', 'nhap den', 'nhap don den', 'bao cao den', 'ghi don den', 'nhap bao cao den', 'len don den']:
        WIZARD_SESSIONS[session_id] = {'flow': 'den', 'step': 1, 'data': {}}
        return {
            "type": "clarify",
            "message": (
                "💡 **NHẬP BÁO CÁO DOANH THU ĐÈN (HỎI ĐÁP TỪNG BƯỚC)**\n"
                "───────────────────────────────────────\n"
                "🔧 **BƯỚC 1/7: TÊN ĐÈN / SẢN PHẨM**\n"
                "Bạn lắp loại đèn nào cho khách?\n"
                "*(Ví dụ: `F10 Turbo`, `S3`, `S6`, `V20 Base`, `M40 Ultra`, `Titan Gold`... hoặc gõ `hủy` để thoát)*"
            )
        }

    # ═════════════════════════════════════════════════════════════════════
    # 2.3. FAST-TRACK ADMIN ENGINE: XỬ LÝ SIÊU TỐC LỆNH QUẢN TRỊ (< 0.005s)
    # ═════════════════════════════════════════════════════════════════════
    res_admin = parse_and_execute_admin_command(raw, clean, session_id=session_id)
    if res_admin:
        return res_admin

    # Nếu câu lệnh phức tạp, chuyển cho Gemini 3.5 Flash xử lý
    if GEMINI_AVAILABLE and gemini_engine and gemini_engine.is_admin_or_edit_intent(clean):
        res_gemini = gemini_engine.ask_gemini(raw, session_id=session_id)
        if res_gemini and res_gemini.get('message'):
            return res_gemini
        status_msg = getattr(gemini_engine, 'get_key_status_message', lambda: '')()
        if status_msg:
            return {"type": "warning", "message": status_msg}

    # Nếu người dùng hỏi về tình trạng Gemini hoặc thắc mắc về AI
    if any(k in clean for k in ['gemini', 'key gemini', 'sao gemini', 'kiem tra gemini', 'test gemini']):
        if GEMINI_AVAILABLE and gemini_engine:
            if not getattr(gemini_engine, 'DEFAULT_API_KEY', None):
                return {
                    "type": "warning",
                    "message": (
                        "⚠️ **CHƯA CÓ API KEY GEMINI TRÊN MÁY CHỦ NÀY!**\n"
                        "─────────────────────────────────────────\n"
                        "Để kích hoạt Gemini 3.5 Flash, anh chỉ cần **dán trực tiếp mã API Key** (dạng `AQ...` hoặc `AIzaSy...`) vào khung chat này!\n"
                        "Hệ thống sẽ tự nhận diện và kích hoạt ngay tức thì."
                    )
                }

            res_gemini = gemini_engine.ask_gemini(raw, session_id=session_id)
            if res_gemini and res_gemini.get('message'):
                return res_gemini
            status_msg = getattr(gemini_engine, 'get_key_status_message', lambda: '')()
            if status_msg:
                return {"type": "warning", "message": status_msg}
            return {
                "type": "warning",
                "message": (
                    "⚠️ **ĐANG KẾT NỐI GEMINI NHƯNG CHƯA NHẬN ĐƯỢC PHẢN HỒI**\n"
                    "─────────────────────────────────────────\n"
                    "Vui lòng kiểm tra lại kết nối mạng trên máy chủ hoặc thử dán lại mã API Key vào khung chat."
                )
            }
        else:
            return {
                "type": "warning",
                "message": (
                    "⚠️ **MÁY CHỦ CHƯA NẠP ĐƯỢC GEMINI ENGINE!**\n"
                    "─────────────────────────────────────────\n"
                    "Vui lòng chạy lệnh: `pip install --user google-genai` và kiểm tra tệp `gemini_engine.py`."
                )
            }

    # ═════════════════════════════════════════════════════════════════════
    # 2.2. TRA CỨU TRI THỨC TỰ ĐỘNG TỪ BỘ NHỚ GARA ĐÃ HỌC (< 0.003s)
    # ═════════════════════════════════════════════════════════════════════
    if KNOWLEDGE_AVAILABLE and knowledge_base:
        res_learned = knowledge_base.query_learned_knowledge(clean, raw)
        if res_learned:
            return res_learned

    # ═════════════════════════════════════════════════════════════════════
    # 2.3.5. TRÍ TUỆ SUY LUẬN & PHÂN TÍCH CHUYÊN SÂU GEMINI (DEEP REASONING)
    # Khi người dùng hỏi so sánh, phân tích, tại sao, tư vấn phương án, đánh giá...
    # ═════════════════════════════════════════════════════════════════════
    is_reasoning = any(k in clean for k in [
        'so sanh', 'phan tich', 'giai thich', 'tai sao', 'vi sao', 'ly do', 'nen chon',
        'co nen', 'uu diem', 'nhuoc diem', 'khac nhau the nao', 'khac gi nhau',
        'danh gia', 'kinh nghiem', 'chia se', 'loai nao tot hon', 'tu van giup',
        'tu van cho toi', 'phuong an nao'
    ])
    if is_reasoning and GEMINI_AVAILABLE and gemini_engine:
        res_gemini = gemini_engine.ask_gemini(raw, session_id=session_id)
        if res_gemini and res_gemini.get('message'):
            return res_gemini

    # ═════════════════════════════════════════════════════════════════════
    # 2.4. CHUYÊN GIA TƯ VẤN DỊCH VỤ GARA (PHIM CÁCH NHIỆT, TRẦN, MÀN HÌNH, BOX, CAM, GHẾ DA)
    # ═════════════════════════════════════════════════════════════════════
    res_gara = handle_gara_consultation(raw, clean)
    if res_gara:
        return res_gara

    # ═════════════════════════════════════════════════════════════════════
    # 2.5. CHUYÊN GIA TƯ VẤN PHIM BẢO VỆ SƠN PPF (AX FILM, 3M, TECKWRAP)
    # ═════════════════════════════════════════════════════════════════════
    if any(k in clean for k in ['ppf', 'ax film', 'teckwrap', 'teck wrap', 'bao ve son', 'dan film', 'dan phim', 'dan keo xe', 'dan capo', 'dan can truoc', 'dan den pha']):
        res = handle_ppf_consultation(raw, clean)
        if res:
            return res

    # 3. Hủy / Xóa đơn đèn vừa nhập nhầm
    if any(k in clean for k in ['xoa don', 'huy don', 'undo']):
        res = handle_undo_last_lamp_order(raw, clean)
        if res:
            return res

    # 4. Thống kê & Báo cáo doanh thu toàn cửa hàng / Tồn quỹ / Đơn hàng (ƯU TIÊN TUYỆT ĐỐI)
    res_stats = handle_revenue_and_store_stats(raw, clean, session_id)
    if res_stats:
        return res_stats

    # 4.2. Thống kê & Báo cáo chuyên sâu doanh số đèn chu kỳ 9-8 (kỳ tháng, hôm nay, top bán chạy)
    if any(k in clean for k in ['doanh thu den', 'doanh so den', 'bao cao den', 'ban duoc bao nhieu den', 'may xe den', 'don den hom nay', 'top den', 'den ban chay']) or \
       (any(k in clean for k in ['doanh thu', 'doanh so', 'bao cao']) and any(k in clean for k in ['den', 'bi', 'gam', 'pha', 'bong'])):
        res = handle_baocao_den_stats(raw, clean, session_id)
        if res:
            return res

    # 5. Tra cứu giá bán & tồn kho (nếu là câu hỏi giá thuần túy)
    is_asking_price = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean)) or \
                      (bool(re.search(r'\b(gia|gia ban)\b', clean)) and not bool(re.search(r'\b(lap|gan|do|thay|nhap|don)\b', clean)) and not bool(re.search(r'\bgia\s+\d+', clean)))
    if is_asking_price:
        res = handle_stock_and_price(raw, clean)
        if res:
            return res

    # 6. Tra cứu bảo hành / đơn hàng theo biển số, SĐT hoặc tên khách có đại từ nhân xưng
    is_order_creation = bool(re.search(r'\b(?:nhap don|len don|ghi don|don den|lap|gan|thay|do)\b', clean))
    has_lamp_keyword = any(k in clean for k in ['v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'hyper', 'titan', 'naoevo', '301', 'f150', 'cb150'])
    if not is_order_creation and (extract_license_plate(raw) or extract_phone(raw) or extract_customer_search_intent(raw) or any(k in clean for k in ['bao hanh', 'tra cuu', 'tim xe', 'check xe'])) and not has_lamp_keyword:
        res = handle_search_warranty_and_orders(raw, clean)
        if res:
            return res

    # 7. Nhập Đơn Báo Cáo Đèn (ƯU TIÊN CAO khi có mã đèn hoặc hành động nhập đơn / lắp đặt)
    if is_order_creation or has_lamp_keyword or (any(k in clean for k in ['lap', 'gan', 'do', 'thay', 'ban', 'nhap', 'len', 'ghi']) and any(k in clean for k in ['den', 'bi', 'bong', 'pha', 'gam', 'don'])):
        res = handle_baocao_den(raw, clean, session_id=session_id)
        if res:
            return res

    # 8. Sổ thu chi (thu, chi, tiền ăn, tiền xăng...)
    if any(k in clean for k in ['thu', 'chi', 'tra tien', 'mua', 'dong tien', 'nop', 'ung']):
        res = handle_thuchi(raw, clean, session_id=session_id)
        if res:
            return res

    # 9. Fallback Tra cứu bảo hành / đơn
    res = handle_search_warranty_and_orders(raw, clean)
    if res:
        return res

    # 10. Fallback Tra cứu kho
    res = handle_stock_and_price(raw, clean)
    if res:
        return res

    # 11. Thống kê tổng hợp hệ thống
    res = handle_summary_stats(raw, clean)
    if res:
        return res

    # 11.5. HỎI ĐÁP MỞ & PHÂN TÍCH CHUYÊN SÂU (GEMINI 3.5 FLASH)
    if GEMINI_AVAILABLE and gemini_engine:
        res_gemini = gemini_engine.ask_gemini(raw, session_id=session_id)
        if res_gemini and res_gemini.get('message'):
            return res_gemini
        status_msg = getattr(gemini_engine, 'get_key_status_message', lambda: '')()
        if status_msg and any(k in clean for k in ['gemini', 'thong minh', 'sao ko', 'sao khong', 'sao chua']):
            return {"type": "warning", "message": status_msg}

    # 12. Chủ động hỏi lại người dùng để làm rõ ý và phục vụ chính xác
    return ask_clarification(raw, clean, session_id)


def process_ai_command(user_text, session_id="default_user"):
    """Bọc bộ xử lý lệnh để tự động duy trì lịch sử hội thoại liên tục cho Gemini và bảo toàn ngữ cảnh sản phẩm."""
    if not user_text:
        return _process_ai_command_internal(user_text, session_id=session_id)

    raw = user_text.strip()
    clean = remove_accents(raw).lower()

    # 1. BẢO VỆ NGỮ CẢNH HỘI THOẠI:
    # Nếu người dùng nói "sửa giá lại thành...", "đổi giá thành...", "sửa lại thành..."
    # mà không ghi tên sản phẩm, nhưng câu liền trước vừa tra cứu / nói về một sản phẩm (ví dụ A510):
    is_price_edit_intent = any(k in clean for k in ['sua gia', 'sua lai gia', 'doi gia', 'cap nhat gia', 'chinh gia']) or \
                           (any(k in clean for k in ['sua lai', 'doi lai', 'chinh lai']) and any(k in clean for k in ['thanh', 'la', 'gia', 'vnd', 'dong', 'k', 'tr']))
    has_order_indicator = bool(re.search(r'\b(?:don|don hang|ma don|#\d+)\b', clean))

    if is_price_edit_intent and not has_order_indicator:
        prod_in_query = detect_consulted_product(clean)
        if not prod_in_query and session_id in LAST_CONSULTED_TOPIC:
            last_item = LAST_CONSULTED_TOPIC[session_id]
            last_key = last_item.get('key', '')
            if last_key:
                from knowledge_base import parse_vietnamese_currency
                p_display, p_num = parse_vietnamese_currency(raw)
                if p_display:
                    raw = f"sửa lại giá {last_key} giá {p_display}"
                else:
                    raw = f"sửa lại giá {last_key} {raw}"
                clean = remove_accents(raw).lower()

    # 2. Thực thi xử lý câu lệnh
    res = _process_ai_command_internal(raw, session_id=session_id)

    # 3. Ghi nhớ sản phẩm vừa tra cứu / phản hồi vào bộ nhớ ngữ cảnh của session
    detected_prod = detect_consulted_product(clean)
    if not detected_prod and res and isinstance(res, dict) and res.get('message'):
        res_clean = remove_accents(res['message']).lower()
        detected_prod = detect_consulted_product(res_clean)

    if detected_prod:
        LAST_CONSULTED_TOPIC[session_id] = {'key': detected_prod, 'time': datetime.now()}

    # 4. Lưu vào lịch sử hội thoại đa lượt của Gemini
    if res and isinstance(res, dict) and res.get('message') and gemini_engine:
        try:
            gemini_engine.append_to_history(session_id, user_text, res['message'])
        except Exception as e:
            pass
    return res

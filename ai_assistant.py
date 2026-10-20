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
║  - Xử lý siêu tốc mọi cú pháp nhập Đơn Báo Cáo Doanh Thu Đèn:        ║
║    + Gõ tắt cực ngắn: "anh cường accent f10 new 3900"                ║
║    + Tự động điền giá niêm yết nếu quên gõ giá: "vf5 s3 anh hòa"     ║
║    + Khách mua về / xe đi xét: "mua về raize m20 2500"               ║
║    + Nhận diện số lượng: "2 bộ s3 vf3 anh hiếu 3000"                 ║
║    + Nhập combo nhiều món cùng lúc & tự chia giảm giá                ║
║  - Tra cứu thống kê doanh thu đèn chu kỳ 9-8 và đơn lắp hôm nay      ║
║  - Hủy / xóa đơn đèn vừa nhập nhầm tức thì                           ║
║  - Ghi sổ Thu / Chi, tra cứu bảo hành, tồn kho & giá bán sản phẩm    ║
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

def parse_vietnamese_money(text):
    """
    Phân tích số tiền tiếng Việt cực kỳ linh hoạt:
    500k -> 500000
    1.5tr / 1,5tr / 1.5trieu / 1tr5 -> 1500000
    2tr -> 2000000
    500 nghin / 500 ngàn -> 500000
    350000 -> 350000
    """
    if not text:
        return 0

    t = re.sub(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', ' ', text)
    t = re.sub(r'\b20[2-3]\d\b', ' ', t)
    clean = remove_accents(t).replace(',', '.')

    m_tr_split = re.search(r'(\d+)\s*tr\s*(\d+)\b', clean)
    if m_tr_split:
        main_tr = int(m_tr_split.group(1))
        dec = m_tr_split.group(2)
        dec_val = int(dec) * (10 ** (6 - len(dec))) if len(dec) <= 6 else 0
        return main_tr * 1000000 + dec_val

    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|triệu|m)\b', clean)
    if m_tr:
        return int(float(m_tr.group(1)) * 1000000)

    m_k = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|nghin|ngan|nghìn|ngàn)\b', clean)
    if m_k:
        return int(float(m_k.group(1)) * 1000)

    m_dot = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\b', t)
    if m_dot:
        return int(m_dot.group(1).replace('.', ''))

    m_num = re.search(r'\b(\d{4,10})\b', clean)
    if m_num:
        val = int(m_num.group(1))
        return val

    m_small = re.search(r'(?:thu|chi|gia|giá|tiền|tien)\s+(\d{1,3})\b', clean)
    if m_small:
        val = int(m_small.group(1))
        return val * 1000

    return 0

def extract_license_plate(text):
    clean = text.upper()
    m = re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5}(?:\.[0-9]{1,2})?)\b', clean)
    if m:
        return m.group(1).strip()
    return ""

def clean_plate_raw(plate_str):
    if not plate_str:
        return ""
    return re.sub(r'[^A-Z0-9]', '', plate_str.upper())

def extract_phone(text):
    m = re.search(r'\b(0[35789]\d{8})\b', text)
    return m.group(1) if m else ""

# ── DANH MỤC ĐÈN THỰC TẾ & BẢNG GIÁ NIÊM YẾT TẠI GARA (k = nghìn đồng) ──
LAMP_CATALOG = [
    # Dòng V20 Series
    (r'\bv20\s*base\b', 'V20 BASE', 6500),
    (r'\bv20\s*ultra\b|\bv20l\b|\bv20\b', 'BI LED V20', 5850),
    # Dòng Naoevo / X-Light S Series
    (r'\b(?:xlight|naoevo)?\s*s3\s*pro\b|\bs3\s*pro\b', 'XLIGHT S3 PRO', 1500),
    (r'\b(?:xlight|naoevo)?\s*s3\b|\bs3\b', 'NAOEVO S3', 1500),
    (r'\b(?:xlight|naoevo)?\s*s6\s*pro\b|\bs6\s*pro\b', 'NAOEVO S6 PRO', 2000),
    (r'\b(?:xlight|naoevo)?\s*s6\b|\bs6\b', 'NAOEVO S6', 1800),
    (r'\b(?:xlight|naoevo)?\s*s8\s*pro\b|\bs8\s*pro\b', 'NAOEVO S8 PRO', 2800),
    (r'\b(?:xlight|naoevo)?\s*s8\b|\bs8\b', 'NAOEVO S8', 2500),
    (r'\b(?:xlight|naoevo)?\s*s9\s*pro\b|\bs9\s*pro\b', 'NAOEVO S9 PRO', 3000),
    (r'\b(?:xlight|naoevo)?\s*s9\b|\bs9\b', 'NAOEVO S9', 2800),
    # Dòng Bi Gầm F10 Series (Bán chạy nhất)
    (r'\bf10\s*pro\s*v2\b|\bf10\s*pro\b', 'F10 PRO V2', 5500),
    (r'\bf10\s*turbo\b', 'F10 TURBO', 5100),
    (r'\bf10\s*hyper\b|\bf10\s*heyper\b', 'F10 HYPER', 5500),
    (r'\bf10\s*new\s*2\.?0\b|\bf10\s*new\b|\bf10\s*2\.?0\b|\bf10\b', 'F10 NEW 2.0', 3900),
    (r'\bf10\s*3\s*mau\b|\bf10\s*ba\s*mau\b', 'F10 BA MÀU', 4500),
    # Dòng M Series
    (r'\bm10\s*ultra\b|\bm10\b', 'M10 ULTRA', 2500),
    (r'\bm20\s*ultra\b|\bm20\b', 'M20 ULTRA', 3100),
    (r'\bm30\s*ultra\b|\bm30\b', 'M30 ULTRA', 5500),
    (r'\bm40\s*ultra\b|\bm40\b', 'M40 ULTRA', 6500),
    # Dòng Titan & GTR
    (r'\btitan\s*gold\b', 'TITAN GOLD', 6750),
    (r'\btitan\s*black\b', 'TITAN BLACK', 5500),
    (r'\btitan\s*platinum\b', 'TITAN PLATINUM', 8500),
    (r'\bg1\s*turbo\b', 'G1 TURBO', 6200),
    (r'\bxlight\s*301\b|\b301\b', 'XLIGHT 301', 4500),
    (r'\bf150\s*pro\b|\bf150\b', 'F150 PRO', 6000),
    (r'\bcb150\b', 'CB150', 3800),
    # Mí LED & Vòng BM
    (r'\b(?:led\s*mi|mi\s*led|led\s*deo|mi\s*deo)\b', 'MÍ LED', 1800),
    (r'\bvong\s*bm\b|\bvòng\s*bm\b', 'VÒNG BM', 1500),
    (r'\bvong\s*angel\b|\bvòng\s*angel\b', 'VÒNG ANGEL', 1200),
]

# Danh mục đầy đủ các dòng xe tại Việt Nam
CAR_MODELS_LIST = [
    'DESTINATOR', 'FORTUNER', 'CARNIVAL', 'EVEREST', 'TERRITORY', 'STARGAZER', 'FORESTER', 'OUTLANDER',
    'XPANDER', 'INNOVA', 'SOLATI', 'TRANSIT', 'SANTAFE', 'TUCSON', 'CERATO', 'SORENTO', 'SEDONA',
    'ACCENT', 'ELANTRA', 'RANGER', 'CAMRY', 'MAZDA 3', 'MAZDA 2', 'MORNING', 'ERTIGA', 'CUSTIN',
    'VIOS', 'CITY', 'KONA', 'CROSS', 'HILUX', 'RAIZE', 'CRETA', 'SELTOS', 'SONET', 'MPV7',
    'VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9', 'CX5', 'CX8', 'BRV', 'CRV', 'MG5', 'I10', 'XL7', 'K3'
]

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
# 1. NHẬP BÁO CÁO DOANH THU ĐÈN TỐI ƯU SIÊU TỐC
# ─────────────────────────────────────────────────────────────────────────────

def handle_baocao_den(raw_text, clean_text):
    """
    Xử lý lệnh ghi đơn báo cáo doanh thu đèn tối ưu tuyệt đối:
    - Bóc tách theo bất kỳ trật tự câu chữ nào: [Khách] [Xe] [Đèn] [Giá] hoặc [Đèn] [Xe] [Khách]
    - Tự động tra cứu giá niêm yết nếu người dùng quên gõ giá
    - Tự động nhận diện số lượng: '2 bộ s3', '2 cái f10'
    - Hỗ trợ các khách hàng đặc biệt: 'mua về', 'xe đi xét', 'thầy đức', 'chú ba'
    - Hỗ trợ combo nhiều món & tự động phân bổ chiết khấu / giảm giá
    """
    # Nhận diện xem câu có mã đèn hoặc từ khóa làm đèn không
    is_den = bool(re.search(r'\b(den|bi|bi gam|bi led|bi pha|f10|naoevo|s3|s6|s8|s9|turbo|hyper|v20|m30|m40|titan|bong|pha|gam|m10|m20|f150|cb150)\b', clean_text))
    if not is_den:
        return None

    # Nếu chỉ đang hỏi giá hoặc hỏi tồn kho thuần túy
    is_pure_query = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean_text)) and \
                    not bool(re.search(r'\b(lap|gan|do|thay|ban|don|nhap)\b', clean_text))
    if is_pure_query:
        return None

    text = raw_text.strip()

    # 1. Biển số xe
    m_plate = re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5}(?:\.[0-9]{1,2})?)\b', text.upper())
    plate = m_plate.group(1).strip() if m_plate else ''
    if plate:
        text = text.replace(m_plate.group(0), ' ')

    # 2. Ngày ghi nhận
    order_date, text = extract_date(text)

    # 3. Dòng xe (bóc tách và xóa khỏi text để không nhầm thành tên khách)
    found_car = ''
    for c in CAR_MODELS_LIST:
        m_c = re.search(r'(?:cho\s+xe\s+|xe\s+)?\b' + c + r'\b', text, re.IGNORECASE)
        if m_c:
            found_car = c
            text = text[:m_c.start()] + ' ' + text[m_c.end():]
            break

    # 4. Giảm giá (chiết khấu / bớt tiền)
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

    # 5. Khách hàng đặc biệt (Mua về, Xe đi xét, Giao thợ...)
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
        c = re.sub(r'^(?:lắp|lap|gắn|gan|thay|bán|ban|độ|do|cho)\s+', '', chunk, flags=re.IGNORECASE).strip()
        if not c:
            continue

        # Số lượng
        qty = 1
        m_qty = re.search(r'\b(\d+)\s*(?:bộ|bo|cặp|cap|cái|cai|hộp|hop)\b', c, re.IGNORECASE)
        if m_qty:
            qty = int(m_qty.group(1))
            c = c[:m_qty.start()] + ' ' + c[m_qty.end():]

        # Bóc giá trong từng món
        m_p = re.search(r'(?:giá|gia)?\s*(\d+(?:[.,]\d+)?)\s*(tr|trieu|triệu|k|nghin|ngàn)?(?:\s*đ|\s*vnd)?$', c, re.IGNORECASE)
        price_k = 0
        raw_name = c
        is_default_price = False
        if m_p:
            num_str = m_p.group(1).replace(',', '.')
            unit = (m_p.group(2) or '').lower()
            val = float(num_str)
            if unit in ['tr', 'trieu', 'triệu']:
                price_k = int(val * 1000)
            elif unit in ['k', 'nghin', 'ngàn']:
                price_k = int(val)
            elif val >= 100000:
                price_k = int(val / 1000)
            elif val >= 100:
                price_k = int(val)
            elif val > 0 and val < 50:
                price_k = int(val * 1000)
            else:
                price_k = int(val)
            raw_name = c[:m_p.start()].strip()
            raw_name = re.sub(r'\b(giá|gia)\b\s*$', '', raw_name, flags=re.IGNORECASE).strip()

        # Nhận diện tên đèn theo Catalog
        matched_name = ''
        matched_default = 3500
        for pat, cname, dprice in LAMP_CATALOG:
            m_l = re.search(pat, raw_name, re.IGNORECASE)
            if m_l:
                matched_name = cname
                matched_default = dprice
                # Bất kỳ từ ngữ nào nằm trước hoặc sau tên đèn đều là tên khách hàng
                leftover = raw_name[:m_l.start()] + ' ' + raw_name[m_l.end():]
                clean_left = re.sub(r'\b(lắp|lap|gắn|gan|thay|độ|do|bán|ban|cho|đèn|den|bi|gầm|gam|pha|xe)\b', ' ', leftover, flags=re.IGNORECASE)
                clean_left = ' '.join(clean_left.split()).strip()
                if clean_left and len(clean_left) >= 2:
                    cust_candidates.append(clean_left)
                break

        if not matched_name:
            matched_name = raw_name.upper()

        if price_k == 0:
            price_k = matched_default * qty
            is_default_price = True

        items.append({
            'product_name': matched_name,
            'quantity': qty,
            'base_price_k': price_k,
            'is_default': is_default_price
        })

    if not items:
        return None

    # Xác định tên khách
    cust_name = cust_special
    if not cust_name and cust_candidates:
        cust_name = cust_candidates[0].strip().title()
    if not cust_name:
        cust_name = plate if plate else (found_car if found_car else 'KHÁCH LẺ')

    # Chuẩn hóa từ xưng hô khách
    cust_name = re.sub(r'\bThay\b', 'Thầy', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChi\b', 'Chị', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChu\b', 'Chú', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bBac\b', 'Bác', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bEm\b', 'Em', cust_name, flags=re.IGNORECASE)

    # Phân bổ giảm giá
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

    # Lưu trực tiếp vào database doanhthu_den.db
    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        saved_ids = []
        for it in items:
            c.execute("""
                INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                VALUES (?, ?, ?, ?, ?, ?, 'AI_ASSISTANT')
            """, (order_date, it['product_name'], cust_name, found_car or 'XE Ô TÔ', it['quantity'], it['final_price_k']))
            saved_ids.append(c.lastrowid)
        conn.commit()
        conn.close()

        # Soạn phản hồi chi tiết, trực quan
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
                f"💡 **ĐÃ GHI NHẬN ĐƠN BÁO CÁO ĐÈN THÀNH CÔNG!**\n\n"
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
                f"*(Nếu nhập nhầm, gõ 'hủy đơn vừa nhập' để hoàn tác ngay)*"
            )
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi lưu báo cáo đèn: {str(e)}"}

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

        # Tìm đơn gần nhất do AI_ASSISTANT tạo
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

        # Xóa đơn gần nhất
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

def handle_baocao_den_stats(raw_text, clean_text):
    """Báo cáo thống kê chuyên sâu về doanh thu đèn chu kỳ 9-8 và danh sách lắp hôm nay"""
    is_stat = bool(re.search(r'\b(doanh thu den|doanh so den|bao cao den|ban duoc bao nhieu den|may xe den|don den hom nay|top den|den ban chay)\b', clean_text))
    if not is_stat:
        return None

    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()

        # Kỳ hiện tại (mùng 9 đến mùng 8)
        cy, cm = get_current_cycle()
        start_date, end_date = get_cycle_dates(cy, cm)

        # 1. Thống kê kỳ này
        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(price_k), 0)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        row = c.fetchone()
        order_count = row[0] or 0
        total_qty = row[1] or 0
        total_k = row[2] or 0

        # Số lượt xe độc lập
        c.execute("""
            SELECT COUNT(DISTINCT customer_name || '_' || car_model)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        car_count = c.fetchone()[0] or 0

        # 2. Đơn lắp hôm nay
        today_str = datetime.now().strftime('%Y-%m-%d')
        c.execute("""
            SELECT id, product_name, customer_name, car_model, quantity, price_k
            FROM orders
            WHERE order_date = ?
            ORDER BY id DESC
        """, (today_str,))
        today_rows = c.fetchall()

        # 3. Top đèn bán chạy trong kỳ
        c.execute("""
            SELECT product_name, SUM(quantity), SUM(price_k)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
            GROUP BY product_name
            ORDER BY SUM(quantity) DESC, SUM(price_k) DESC LIMIT 5
        """, (start_date, end_date))
        top_prods = c.fetchall()
        conn.close()

        # Soạn phản hồi
        reply = (
            f"💡 **BÁO CÁO DOANH THU ĐÈN — KỲ THÁNG {cm:02d}/{cy}**\n"
            f"*(Tính từ ngày {start_date.split('-')[2]}/{start_date.split('-')[1]} đến {end_date.split('-')[2]}/{end_date.split('-')[1]})*\n\n"
            f"• 💰 **Tổng doanh thu:** **{total_k*1000:,.0f} đ** ({total_k:,}k)\n"
            f"• 📦 **Tổng số bộ đèn đã lắp:** **{total_qty} bộ** ({order_count} dòng đơn)\n"
            f"• 🚗 **Số lượt xe phục vụ:** **{car_count} xe**\n\n"
        )

        # Danh sách hôm nay
        if today_rows:
            reply += f"🕒 **ĐƠN ĐÈN LẮP HÔM NAY ({datetime.now().strftime('%d/%m/%Y')} - {len(today_rows)} đơn):**\n"
            for r in today_rows:
                reply += f"  • #{r[0]}: **{r[4]}x {r[1]}** — Xe: {r[3]} ({r[2]}) ➔ **{r[5]*1000:,.0f} đ**\n"
            reply += "\n"
        else:
            reply += f"🕒 **Hôm nay ({datetime.now().strftime('%d/%m/%Y')}):** Chưa có đơn đèn nào được ghi nhận.\n\n"

        # Top đèn bán chạy
        if top_prods:
            reply += "🔥 **TOP ĐÈN BÁN CHẠY NHẤT KỲ NÀY:**\n"
            for i, p in enumerate(top_prods, 1):
                reply += f"  {i}. **{p[0]}**: {p[1]} bộ — Doanh số: {p[2]*1000:,.0f} đ\n"
            reply += "\n"

        reply += "👉 [Bấm vào đây để mở Báo Cáo Doanh Thu Đèn chi tiết](/den/)"
        return {"type": "success", "module": "den", "message": reply}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi tra cứu báo cáo đèn: {str(e)}"}

# ─────────────────────────────────────────────────────────────────────────────
# 4. SỔ THU CHI
# ─────────────────────────────────────────────────────────────────────────────

def handle_thuchi(raw_text, clean_text):
    """Xử lý lệnh ghi sổ thu hoặc chi"""
    if any(k in clean_text for k in ['lap den', 'gan den', 'bi led', 'bi gam', 'v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'naoevo', 'titan']):
        return None

    has_honorific_chi = bool(re.search(r'\b(chị|chi)\s+([a-zA-ZÀ-ỹ]+)', raw_text, re.IGNORECASE))
    is_explicit_chi = bool(re.search(r'\b(ghi\s*chi|phiếu\s*chi|phieu\s*chi|tiền\s*chi|tien\s*chi|chi\s*tiền|chi\s*tien|chi\s+\d+|chi\s+phi|tam\s*ung|ung\s*tien|tra\s+tien|nop\s+tien|tien\s+an|com|xang|mat\s+bang)\b', clean_text))

    is_chi = is_explicit_chi or (bool(re.search(r'\b(chi|tra|mua|dong|nop|ung|ung truoc|xuat tien|tien an|com|xang|mat bang|phi)\b', clean_text)) and not has_honorific_chi)
    is_thu = bool(re.search(r'\b(thu|nhan|thu tien|khach tra|nap|vao quy|tien ve)\b', clean_text))
    
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
        return {
            "type": "success",
            "module": "thuchi",
            "message": f"{action_icon} THÀNH CÔNG!\n\n"
                       f"• **Phân loại:** {trans_type.upper()}\n"
                       f"• **Số tiền:** **{amount:,.0f} đ**\n"
                       f"• **Nội dung:** {note.capitalize()}\n"
                       f"• **Ngày:** {date_str}\n"
                       f"• **Kỳ ghi nhận:** {period_name}\n"
                       f"• **Số dư quỹ kỳ này hiện tại:** **{balance:,.0f} đ**\n\n"
                       f"👉 [Bấm vào đây để mở Sổ Thu Chi](/thuchi/)"
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi ghi sổ thu chi: {str(e)}"}

# ─────────────────────────────────────────────────────────────────────────────
# 5. TRA CỨU BẢO HÀNH & ĐƠN HÀNG
# ─────────────────────────────────────────────────────────────────────────────

def handle_search_warranty_and_orders(raw_text, clean_text):
    """Tra cứu bảo hành và lịch sử đơn hàng theo biển số xe, SĐT, tên khách"""
    is_search = bool(re.search(r'\b(tim|kiem tra|tra cuu|check|xem|bao hanh|lich su|don hang)\b', clean_text))
    plate = extract_license_plate(raw_text)
    phone = extract_phone(raw_text)

    if not (plate or phone or is_search):
        return None

    search_query = plate if plate else (phone if phone else "")
    if not search_query:
        m = re.search(r'(?:tim|tra cuu|check|kiem tra|bao hanh|xe)\s+([a-zA-Z0-9\-\.\s]+)', clean_text)
        if m:
            search_query = m.group(1).strip()

    if not search_query or len(search_query) < 2:
        return {
            "type": "clarify",
            "message": "🔍 Bạn muốn tra cứu bảo hành hoặc đơn hàng cho **Biển số xe**, **Số điện thoại** hay **Tên khách hàng** nào? (Ví dụ: *'tra cứu biển số 63A-123.10'* hoặc *'bảo hành xe 51H'*)"
        }

    results = []
    if os.path.exists(DB_BANHANG):
        try:
            conn = sqlite3.connect(DB_BANHANG, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            clean_q = clean_plate_raw(search_query)
            c.execute("""
                SELECT id, customer_name, phone, license_plate, install_date, total_price 
                FROM orders 
                WHERE replace(replace(replace(UPPER(license_plate), '-', ''), '.', ''), ' ', '') LIKE ?
                   OR license_plate LIKE ? 
                   OR phone LIKE ? 
                   OR customer_name LIKE ?
                ORDER BY install_date DESC LIMIT 5
            """, (f"%{clean_q}%", f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            orders = c.fetchall()

            for o in orders:
                oid = o['id']
                c.execute("SELECT item_name, price, warranty_months, qty FROM order_items WHERE order_id = ?", (oid,))
                items = c.fetchall()
                results.append({
                    "source": "Bán hàng & Kho",
                    "id": oid,
                    "plate": o['license_plate'],
                    "name": o['customer_name'],
                    "phone": o['phone'],
                    "date": o['install_date'],
                    "total": o['total_price'],
                    "items": [dict(it) for it in items]
                })
            conn.close()
        except Exception:
            pass

    if os.path.exists(DB_DEN):
        try:
            conn = sqlite3.connect(DB_DEN, timeout=10)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT id, order_date, product_name, customer_name, car_model, price_k
                FROM orders
                WHERE customer_name LIKE ? OR car_model LIKE ?
                ORDER BY order_date DESC LIMIT 5
            """, (f"%{search_query}%", f"%{search_query}%"))
            for r in c.fetchall():
                results.append({
                    "source": "Báo cáo Đèn",
                    "id": r['id'],
                    "plate": "",
                    "name": r['customer_name'],
                    "phone": "",
                    "date": r['order_date'],
                    "total": r['price_k'] * 1000,
                    "items": [{"item_name": r['product_name'], "price": r['price_k'] * 1000, "warranty_months": 24, "qty": 1}]
                })
            conn.close()
        except Exception:
            pass

    if not results:
        return {
            "type": "info",
            "message": f"🔎 Không tìm thấy đơn hàng hoặc thông tin bảo hành nào khớp với từ khóa **'{search_query}'**.\nBạn vui lòng kiểm tra lại biển số xe hoặc số điện thoại nhé!"
        }

    res_text = f"🔍 **KẾT QUẢ TRA CỨU CHO TỪ KHÓA: '{search_query.upper()}'**\n\n"
    for r in results:
        res_text += f"🚗 **Xe/Khách:** {r['name']} ({r['plate'] or 'Không ghi biển số'})\n"
        res_text += f"📅 **Ngày lắp:** {r['date']} | 💰 **Tổng thanh toán:** {r['total']:,.0f} đ\n"
        res_text += f"📦 **Các món phụ kiện & Bảo hành:**\n"
        for it in r['items']:
            war = it.get('warranty_months', 0)
            war_badge = f"🛡️ BH {war} tháng" if war > 0 else "Không BH"
            res_text += f"  - {it['item_name']}: {it['price']:,.0f} đ ({war_badge})\n"
        res_text += "──────────────────────────\n"

    res_text += f"\n👉 [Mở tab Tra cứu trên phần mềm Bán hàng](/banhang/)"
    return {"type": "success", "message": res_text}

# ─────────────────────────────────────────────────────────────────────────────
# 6. TRA CỨU TỒN KHO & GIÁ BÁN
# ─────────────────────────────────────────────────────────────────────────────

def handle_stock_and_price(raw_text, clean_text):
    """Tra cứu tồn kho & giá bán sản phẩm thông minh"""
    is_stock = bool(re.search(r'\b(ton kho|gia ban|con hang|het hang|bao nhieu tien|gia von|kho|gia|bao gia|nhieu tien|bao nhieu|nhieu)\b', clean_text))
    if not is_stock:
        return None

    kw = extract_product_keyword(raw_text)
    if not kw or len(kw) < 2:
        return {
            "type": "clarify",
            "message": "📦 Bạn muốn tra cứu **giá bán** hoặc **tồn kho** của sản phẩm nào? (Ví dụ: *'f10 pro giá bao nhiêu'*, *'giá f10 turbo'*, *'tồn kho vietmap'*)"
        }

    if not os.path.exists(DB_BANHANG):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu kho hàng!"}

    try:
        conn = sqlite3.connect(DB_BANHANG, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT code, name, category, price, cost_price, stock, warranty_months 
            FROM products 
            WHERE UPPER(name) LIKE ? OR UPPER(code) LIKE ?
            ORDER BY stock DESC LIMIT 6
        """, (f"%{kw.upper()}%", f"%{kw.upper()}%"))
        rows = c.fetchall()

        if not rows:
            tokens = [t.strip() for t in kw.split() if len(t.strip()) >= 2]
            if len(tokens) >= 2:
                conditions = " AND ".join(["UPPER(name) LIKE ?" for _ in tokens])
                params = [f"%{t.upper()}%" for t in tokens]
                c.execute(f"""
                    SELECT code, name, category, price, cost_price, stock, warranty_months 
                    FROM products 
                    WHERE {conditions}
                    ORDER BY stock DESC LIMIT 6
                """, params)
                rows = c.fetchall()

        if not rows:
            first_token = kw.split()[0]
            if len(first_token) >= 2:
                c.execute("""
                    SELECT code, name, category, price, cost_price, stock, warranty_months 
                    FROM products 
                    WHERE UPPER(name) LIKE ?
                    ORDER BY stock DESC LIMIT 6
                """, (f"%{first_token.upper()}%",))
                rows = c.fetchall()

        conn.close()

        if not rows:
            return {"type": "info", "message": f"📦 Không tìm thấy sản phẩm nào khớp với: **'{kw}'** trong kho hàng."}

        reply = f"📦 **KHO HÀNG & BẢNG GIÁ KHỚP VỚI: '{kw.upper()}'**\n\n"
        for p in rows:
            stock_badge = f"🟢 Còn {p['stock']} cái" if p['stock'] > 0 else "🔴 HẾT HÀNG"
            reply += f"• **{p['name']}** ({p['code'] or 'SP'})\n"
            reply += f"  - Giá bán lẻ: **{p['price']:,.0f} đ** | Giá vốn: {p['cost_price']:,.0f} đ\n"
            reply += f"  - Tồn kho: **{stock_badge}** | Bảo hành: **{p['warranty_months']} tháng**\n\n"
        reply += "👉 [Bấm vào đây để mở Danh Mục Kho Hàng](/banhang/)"
        return {"type": "success", "message": reply}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi tra cứu kho: {str(e)}"}

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
# ĐIỀU PHỐI VIÊN CHÍNH (MAIN DISPATCHER)
# ─────────────────────────────────────────────────────────────────────────────

def process_ai_command(user_text):
    """Hàm xử lý mọi câu lệnh từ người dùng gửi qua bong bóng chat AI"""
    if not user_text or not user_text.strip():
        return {
            "type": "clarify",
            "message": "Xin chào! Tôi là **Trợ Lý AI Trần Bình Auto** 🤖.\nTôi có thể giúp bạn:\n\n"
                       "1. **Nhập Đơn Báo Cáo Đèn:** Gõ cực ngắn *'anh Cường accent f10 new 3900'*, *'vf3 s3 anh khoa'*, hoặc combo *'chị Lan v20 base 6500, s3 1500 giảm 500k'*\n"
                       "2. **Thống Kê Doanh Số Đèn:** *'doanh thu đèn tháng này'*, *'đơn đèn hôm nay'*, *'top đèn bán chạy'*\n"
                       "3. **Hủy Đơn Đèn Nhập Nhầm:** *'hủy đơn đèn vừa nhập'*, *'xóa đơn vừa tạo'*\n"
                       "4. **Ghi sổ Thu / Chi:** *'chi 350k tiền cơm'*, *'thu 2tr tiền cọc'*...\n"
                       "5. **Tra Cứu Bảo Hành:** *'tra cứu xe 63A-394.65'*, *'kiểm tra bảo hành anh Sang'*\n"
                       "6. **Tra Cứu Giá & Tồn Kho:** *'giá bi led v20'*, *'tồn kho f10'*...\n\n"
                       "Hãy gõ câu lệnh bạn muốn thực hiện nhé!"
        }

    raw = user_text.strip()
    clean = remove_accents(raw)

    # 1. Hủy / Xóa đơn đèn vừa nhập nhầm (Ưu tiên số 1 để thợ có thể sửa sai ngay)
    if any(k in clean for k in ['xoa don', 'huy don', 'undo']):
        res = handle_undo_last_lamp_order(raw, clean)
        if res:
            return res

    # 2. Thống kê & Báo cáo doanh số đèn (kỳ tháng, hôm nay, top bán chạy)
    if any(k in clean for k in ['doanh thu den', 'doanh so den', 'bao cao den', 'ban duoc bao nhieu den', 'may xe den', 'don den hom nay', 'top den', 'den ban chay']):
        res = handle_baocao_den_stats(raw, clean)
        if res:
            return res

    # 3. Tra cứu giá bán & tồn kho (nếu là câu hỏi giá thuần túy)
    is_asking_price = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean)) or \
                      (bool(re.search(r'\b(gia|gia ban)\b', clean)) and not bool(re.search(r'\b(lap|gan|do|thay|nhap|don)\b', clean)) and not bool(re.search(r'\bgia\s+\d+', clean)))
    if is_asking_price:
        res = handle_stock_and_price(raw, clean)
        if res:
            return res

    # 4. Tra cứu bảo hành / đơn hàng theo biển số hoặc SĐT
    has_lamp_keyword = any(k in clean for k in ['v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'hyper', 'titan', 'naoevo', '301', 'f150', 'cb150'])
    if (extract_license_plate(raw) or extract_phone(raw) or any(k in clean for k in ['bao hanh', 'tra cuu', 'tim xe', 'check xe'])) and not has_lamp_keyword:
        res = handle_search_warranty_and_orders(raw, clean)
        if res:
            return res

    # 5. Nhập Đơn Báo Cáo Đèn (ƯU TIÊN CAO NHẤT khi có mã đèn)
    if has_lamp_keyword or (any(k in clean for k in ['lap', 'gan', 'do', 'thay', 'ban']) and any(k in clean for k in ['den', 'bi', 'bong', 'pha', 'gam'])):
        res = handle_baocao_den(raw, clean)
        if res:
            return res

    # 6. Sổ thu chi (thu, chi, tiền ăn, tiền xăng...)
    if any(k in clean for k in ['thu', 'chi', 'tra tien', 'mua', 'dong tien', 'nop', 'ung']):
        res = handle_thuchi(raw, clean)
        if res:
            return res

    # 7. Fallback Tra cứu bảo hành / đơn
    res = handle_search_warranty_and_orders(raw, clean)
    if res:
        return res

    # 8. Fallback Tra cứu kho
    res = handle_stock_and_price(raw, clean)
    if res:
        return res

    # 9. Thống kê tổng hợp hệ thống
    res = handle_summary_stats(raw, clean)
    if res:
        return res

    # 10. Fallback thông minh
    return {
        "type": "help",
        "message": f"🤖 Tôi chưa hiểu rõ câu lệnh: *'{raw}'*.\n\n"
                   f"**Bạn có thể thử các mẫu lệnh độ đèn tiện lợi sau:**\n"
                   f"• *'anh Cường accent f10 new 3900'* (Nhập đơn cực nhanh)\n"
                   f"• *'thầy Đức vios s6 2000'* (Tự nhận diện khách & xe)\n"
                   f"• *'vf5 s3 anh Hòa'* (Tự động áp dụng giá niêm yết 1.5tr)\n"
                   f"• *'2 bộ s3 vf3 anh Hiếu 3000'* (Nhận diện số lượng)\n"
                   f"• *'doanh thu đèn tháng này'* (Xem doanh số kỳ đối soát)\n"
                   f"• *'đơn đèn hôm nay'* (Xem danh sách các xe làm đèn)\n"
                   f"• *'hủy đơn đèn vừa nhập'* (Xóa đơn nhập nhầm)"
    }

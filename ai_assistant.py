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
║  Tính năng:                                                          ║
║  - Xử lý ngôn ngữ tự nhiên tiếng Việt, từ viết tắt, sai chính tả      ║
║  - Ra lệnh ghi sổ thu chi (thu/chi, gõ tắt k, tr, số tiền)           ║
║  - Ra lệnh nhập đơn báo cáo đèn (bi led, bi gầm, f10, s3, v20...)     ║
║  - Hỗ trợ combo nhiều món đèn cùng lúc, phân bổ giảm giá tự động     ║
║  - Tra cứu bảo hành, lịch sử đơn hàng theo biển số xe/SĐT/tên khách  ║
║  - Tra cứu tồn kho & giá bán sản phẩm                                ║
║  - Thống kê doanh số, số dư quỹ tiền mặt hiện tại                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import sqlite3
from datetime import datetime, timedelta

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
    Tự động loại bỏ ngày tháng để không nhầm năm 2026 thành 2026đ
    """
    if not text:
        return 0

    # Bỏ ngày tháng trước khi parse tiền
    t = re.sub(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', ' ', text)
    t = re.sub(r'\b20[2-3]\d\b', ' ', t)
    clean = remove_accents(t).replace(',', '.')

    # 1. Tách kiểu 1tr5 -> 1.500.000
    m_tr_split = re.search(r'(\d+)\s*tr\s*(\d+)\b', clean)
    if m_tr_split:
        main_tr = int(m_tr_split.group(1))
        dec = m_tr_split.group(2)
        dec_val = int(dec) * (10 ** (6 - len(dec))) if len(dec) <= 6 else 0
        return main_tr * 1000000 + dec_val

    # 2. Triệu: 1.5tr, 2tr, 3trieu
    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|triệu|m)\b', clean)
    if m_tr:
        return int(float(m_tr.group(1)) * 1000000)

    # 3. Nghìn: 500k, 50k, 120nghin, 120ngan
    m_k = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|nghin|ngan|nghìn|ngàn)\b', clean)
    if m_k:
        return int(float(m_k.group(1)) * 1000)

    # 4. Chuỗi số có dấu chấm ngăn cách: 1.500.000 hoặc 500.000
    m_dot = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\b', t)
    if m_dot:
        return int(m_dot.group(1).replace('.', ''))

    # 5. Số nguyên liên tục >= 1000
    m_num = re.search(r'\b(\d{4,10})\b', clean)
    if m_num:
        val = int(m_num.group(1))
        return val

    # 6. Viết tắt sổ thu chi: chi 50 (nghĩa là 50k) nếu số nhỏ hơn 1000
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

# Danh mục đèn thông dụng & bảng giá niêm yết mặc định (k = nghìn đồng)
LAMP_CATALOG = [
    (r'\bv20\s*base\b', 'V20 BASE', 6500),
    (r'\bv20\s*ultra\b|\bv20l\b|\bv20\b', 'BI LED V20', 5850),
    (r'\b(?:xlight|naoevo)?\s*s3\s*pro\b|\bs3\s*pro\b', 'XLIGHT S3 PRO', 1500),
    (r'\b(?:xlight|naoevo)?\s*s3\b|\bs3\b', 'NAOEVO S3', 1500),
    (r'\b(?:xlight|naoevo)?\s*s6\s*pro\b|\bs6\s*pro\b', 'NAOEVO S6 PRO', 2000),
    (r'\b(?:xlight|naoevo)?\s*s6\b|\bs6\b', 'NAOEVO S6', 1800),
    (r'\b(?:xlight|naoevo)?\s*s8\s*pro\b|\bs8\s*pro\b', 'NAOEVO S8 PRO', 2800),
    (r'\b(?:xlight|naoevo)?\s*s8\b|\bs8\b', 'NAOEVO S8', 2500),
    (r'\b(?:xlight|naoevo)?\s*s9\s*pro\b|\bs9\s*pro\b', 'NAOEVO S9 PRO', 3000),
    (r'\b(?:xlight|naoevo)?\s*s9\b|\bs9\b', 'NAOEVO S9', 2800),
    (r'\bf10\s*pro\s*v2\b|\bf10\s*pro\b', 'F10 PRO V2', 5500),
    (r'\bf10\s*turbo\b', 'F10 TURBO', 5100),
    (r'\bf10\s*hyper\b|\bf10\s*heyper\b', 'F10 HYPER', 5500),
    (r'\bf10\s*new\s*2\.?0\b|\bf10\s*new\b|\bf10\s*2\.?0\b|\bf10\b', 'F10 NEW 2.0', 3900),
    (r'\bm30\s*ultra\b|\bm30\b', 'M30 ULTRA', 5500),
    (r'\bm40\s*ultra\b|\bm40\b', 'M40 ULTRA', 6500),
    (r'\bm20\s*ultra\b|\bm20\b', 'M20 ULTRA', 3100),
    (r'\btitan\s*gold\b', 'TITAN GOLD', 6750),
    (r'\btitan\s*black\b', 'TITAN BLACK', 5500),
    (r'\btitan\s*platinum\b', 'TITAN PLATINUM', 8500),
    (r'\bg1\s*turbo\b', 'G1 TURBO', 6200),
    (r'\bxlight\s*301\b|\b301\b', 'XLIGHT 301', 4500),
    (r'\bf150\s*pro\b|\bf150\b', 'F150 PRO', 6000),
    (r'\b(?:led\s*mi|mi\s*led|led\s*deo)\b', 'MÍ LED', 1800),
]

CAR_MODELS_LIST = [
    'VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9', 'XPANDER', 'INNOVA', 'VIOS', 'ACCENT', 'CITY', 
    'FORTUNER', 'CAMRY', 'RANGER', 'CARNIVAL', 'EVEREST', 'KONA', 'ELANTRA', 'MG5', 'TERRITORY', 
    'BRV', 'CRV', 'MAZDA 3', 'MAZDA 2', 'CX5', 'CX8', 'HILUX', 'CROSS', 'MORNING', 'I10', 'SOLATI',
    'SANTAFE', 'TUCSON', 'CERATO', 'K3', 'SORENTO', 'SEDONA', 'TRANSIT'
]

# ─────────────────────────────────────────────────────────────────────────────
# CÁC HÀM XỬ LÝ CHUYÊN BIỆT THEO Ý ĐỊNH (INTENTS)
# ─────────────────────────────────────────────────────────────────────────────

def handle_baocao_den(raw_text, clean_text):
    """
    Xử lý lệnh ghi đơn báo cáo doanh thu đèn thông minh:
    - Hỗ trợ đơn 1 món hoặc COMBO nhiều món đèn cùng lúc
    - Tự động nhận diện khách hàng, dòng xe, biển số, ngày lắp
    - Tự động nhận diện giảm giá (chiết khấu) và phân bổ công bằng vào các món
    - Lưu trực tiếp vào database doanhthu_den.db (báo cáo chu kỳ 9-8)
    """
    # Nhận biết đơn đèn
    is_den = bool(re.search(r'\b(den|bi|bi gam|bi led|bi pha|f10|naoevo|s3|s6|s8|s9|turbo|hyper|v20|m30|m40|titan|bong|pha|gam)\b', clean_text))
    has_action = bool(re.search(r'\b(lap|gan|ban|do|thay|nhap|ghi|don|len)\b', clean_text))
    has_target = bool(re.search(r'\b(cho xe|xe|khach|anh|chi|chu|bac|em|co)\b', clean_text)) or bool(extract_license_plate(raw_text))
    has_specific_price = bool(re.search(r'(?:giá|gia)\s+\d+', raw_text, re.IGNORECASE))

    if not is_den:
        return None

    # Nếu câu chỉ hỏi giá / tồn kho mà không có hành động hoặc số tiền cụ thể -> không phải đơn đèn
    if bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho)\b', clean_text)) and not has_action:
        return None

    if not (has_action or has_target or has_specific_price):
        return None

    working_text = raw_text.strip()

    # 1. Ngày ghi nhận
    order_date, working_text = extract_date(working_text)

    # 2. Biển số xe
    plate = extract_license_plate(working_text)
    if plate:
        working_text = working_text.replace(plate, ' ')

    # 3. Khách hàng (bóc tách xưng hô + tên: Chị Cẩm Tuyền, Anh Hoàng, Chú Ba...)
    cust_name = ""
    m_cust = re.search(r'(?:(chị|chi|anh|chú|chu|bác|bac|em|cô|co|khách|khach)\s+([a-zA-ZÀ-ỹ\s]+?))(?=\s+(?:lắp|lap|gắn|gan|độ|do|mua|lấy|thay|xe|cho xe|giá|gia|\d|,|$))', working_text, re.IGNORECASE)
    if m_cust:
        honorific = m_cust.group(1).title()
        cname_part = m_cust.group(2).strip().upper()
        cust_name = f"{honorific} {cname_part}"
        working_text = working_text[:m_cust.start()] + ' ' + working_text[m_cust.end():]

    # 4. Dòng xe
    found_car = ""
    for c in CAR_MODELS_LIST:
        if re.search(r'\b' + c + r'\b', working_text, re.IGNORECASE):
            found_car = c
            working_text = re.sub(r'(?:cho\s+xe\s+|xe\s+)?\b' + c + r'\b', ' ', working_text, flags=re.IGNORECASE)
            break

    if not cust_name:
        cust_name = plate if plate else (found_car if found_car else 'KHÁCH LẺ')

    # 5. Giảm giá (chiết khấu / bớt tiền)
    discount_k = 0
    m_disc = re.search(r'(?:giảm\s*giá|giam\s*gia|giảm|giam|bớt|bot|chiết\s*khấu|chiet\s*khau)\s*([0-9.,]+(?:\s*(?:tr|trieu|triệu|k|%))?)', working_text, re.IGNORECASE)
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
        working_text = working_text[:m_disc.start()] + ' ' + working_text[m_disc.end():]

    # 6. Tách từng món đèn trong câu
    # Chèn dấu phẩy ngăn cách nếu người dùng gõ liền không có dấu phẩy
    working_text = re.sub(r'(?<=\d)\s+(?=(?:đèn|den|bi|bóng|bong|pha|gầm|gam|v20|f10|s3|s6|s8|s9|m30|m40|titan))', ', ', working_text, flags=re.IGNORECASE)
    chunks = [c.strip() for c in re.split(r'[,;\n]|\b(?:và|cong|\+)\b', working_text) if c.strip()]

    items = []
    for chunk in chunks:
        c = re.sub(r'^(?:lắp|lap|gắn|gan|thay|bán|ban|độ|do)\s+', '', chunk, flags=re.IGNORECASE).strip()
        if not c:
            continue

        # Bóc giá trong từng món
        m_p = re.search(r'(?:giá|gia)?\s*(\d+(?:[.,]\d+)?)\s*(tr|trieu|triệu|k|nghin|ngàn)?(?:\s*đ|\s*vnd)?$', c, re.IGNORECASE)
        price_k = 0
        raw_name = c
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

        # Chuẩn hóa tên sản phẩm theo Catalog
        matched_name = raw_name.upper()
        matched_default_price = 3500
        for pat, cname, dprice in LAMP_CATALOG:
            if re.search(pat, raw_name, re.IGNORECASE):
                matched_name = cname
                matched_default_price = dprice
                break

        if price_k == 0:
            price_k = matched_default_price

        items.append({
            'raw_name': raw_name.upper(),
            'product_name': matched_name,
            'base_price_k': price_k
        })

    if not items:
        return None

    # Tính chiết khấu phần trăm nếu có
    total_base_k = sum(it['base_price_k'] for it in items)
    if disc_is_pct:
        discount_k = int(round(total_base_k * (disc_pct_val / 100)))

    # Phân bổ giảm giá vào từng món để sum(final_price_k) chính xác bằng thực thu
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

    # Ghi nhận vào DB doanhthu_den.db
    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        saved_ids = []
        for it in items:
            c.execute("""
                INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
                VALUES (?, ?, ?, ?, 1, ?, 'AI_ASSISTANT')
            """, (order_date, it['product_name'], cust_name, found_car or 'XE Ô TÔ', it['final_price_k']))
            saved_ids.append(c.lastrowid)
        conn.commit()
        conn.close()

        # Soạn phản hồi trực quan, chi tiết
        item_lines = []
        for i, it in enumerate(items, 1):
            base_str = f"{it['base_price_k']*1000:,.0f} đ ({it['base_price_k']:,}k)"
            if it['discount_k'] > 0:
                final_str = f"{it['final_price_k']*1000:,.0f} đ ({it['final_price_k']:,}k)"
                item_lines.append(f"  {i}. **{it['product_name']}**: {base_str} ➔ Sau giảm: **{final_str}**")
            else:
                item_lines.append(f"  {i}. **{it['product_name']}**: **{base_str}**")

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
                f"👉 [Bấm vào đây để xem Báo Cáo Doanh Thu Đèn](/den/)"
            )
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi lưu báo cáo đèn: {str(e)}"}

def handle_thuchi(raw_text, clean_text):
    """Xử lý lệnh ghi sổ thu hoặc chi"""
    # Tuyệt đối không xử lý nếu là câu lệnh làm đèn
    if any(k in clean_text for k in ['lap den', 'gan den', 'bi led', 'bi gam', 'v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'naoevo', 'titan']):
        return None

    # Phân biệt xưng hô "chị Lan", "chị Cẩm Tuyền" với động từ "chi tiền":
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

    # Trích xuất nội dung ghi chú (bỏ các từ khóa thu/chi/số tiền/ngày tháng)
    date_str, note_raw = extract_date(raw_text)
    note = note_raw
    note = re.sub(r'\b(ghi\s*)?(thu|chi|tra|nop|mua)\b', '', note, flags=re.IGNORECASE)
    note = re.sub(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|m|k|nghin|ngan)?\b', '', note, flags=re.IGNORECASE)
    note = re.sub(r'[,.\-]', ' ', note)
    note = ' '.join(note.split()).strip()
    if not note:
        note = "Ghi nhanh qua trợ lý AI"

    # Ghi vào database finance.db
    if not os.path.exists(DB_THUCHI):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu sổ thu chi!"}

    try:
        conn = sqlite3.connect(DB_THUCHI, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Lấy kỳ đang hoạt động
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

        # Tính lại số dư hiện tại của kỳ
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
    # 1. Tra cứu trong Phân hệ Bán Hàng (tiem_lap_do.db)
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

    # 2. Tra cứu trong Phân hệ Báo Cáo Đèn (doanhthu_den.db)
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
                       "1. **Ghi sổ Thu / Chi:** *'chi 350k tiền cơm'*, *'thu 2tr tiền cọc'*...\n"
                       "2. **Ghi Báo Cáo Đèn:** *'lắp F10 Turbo xe Camry 63A-123.45 giá 5.1tr'* hoặc combo *'chị Cẩm Tuyền lắp v20 base giá 6500, đèn s3 giá 1500, giảm giá 1200'*\n"
                       "3. **Tra Cứu Bảo Hành & Đơn:** *'tra cứu biển số 63A-394.65'*, *'kiểm tra bảo hành anh Sang'*\n"
                       "4. **Tra Cứu Giá & Tồn Kho:** *'giá bi led v20'*, *'tồn kho vietmap'*\n"
                       "5. **Báo Cáo Nhanh:** *'tổng kết sổ quỹ'*, *'doanh thu hôm nay'*\n\n"
                       "Hãy gõ câu lệnh bạn muốn thực hiện nhé!"
        }

    raw = user_text.strip()
    clean = remove_accents(raw)

    # 1. Thử xử lý Tra cứu tồn kho & Giá bán trước NẾU người dùng hỏi giá hoặc tồn kho
    is_asking_price = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean)) or \
                      (bool(re.search(r'\b(gia|gia ban)\b', clean)) and not bool(re.search(r'\b(lap|gan|do|thay|nhap|don)\b', clean)) and not bool(re.search(r'\bgia\s+\d+', clean)))
    if is_asking_price:
        res = handle_stock_and_price(raw, clean)
        if res:
            return res

    # 2. Thử xử lý Tra cứu bảo hành / đơn hàng (nếu có biển số/SĐT hoặc từ khóa tra cứu bảo hành)
    has_lamp_install = any(k in clean for k in ['lap', 'gan', 'do']) and any(k in clean for k in ['den', 'bi', 'f10', 'v20', 's3', 's6', 's8', 's9', 'turbo', 'hyper'])
    if (extract_license_plate(raw) or extract_phone(raw) or any(k in clean for k in ['bao hanh', 'tra cuu', 'tim xe', 'check xe'])) and not has_lamp_install:
        res = handle_search_warranty_and_orders(raw, clean)
        if res:
            return res

    # 3. Thử xử lý Báo cáo đèn & Lắp đèn (ƯU TIÊN HÀNG ĐẦU khi có model đèn hoặc hành động lắp ráp đèn)
    is_lamp_intent = any(k in clean for k in ['v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'hyper', 'titan', 'naoevo', 'bao cao den']) or \
                     (any(k in clean for k in ['lap', 'gan', 'do', 'thay', 'ban']) and any(k in clean for k in ['den', 'bi', 'bong', 'pha', 'gam']))
    if is_lamp_intent:
        res = handle_baocao_den(raw, clean)
        if res:
            return res

    # 4. Thử xử lý Sổ thu chi (thu, chi, tiền ăn, tiền xăng...)
    if any(k in clean for k in ['thu', 'chi', 'tra tien', 'mua', 'dong tien', 'nop', 'ung']):
        res = handle_thuchi(raw, clean)
        if res:
            return res

    # 5. Fallback Báo cáo đèn nếu có từ đèn / bi
    res = handle_baocao_den(raw, clean)
    if res:
        return res

    # 6. Fallback Tra cứu bảo hành / đơn
    res = handle_search_warranty_and_orders(raw, clean)
    if res:
        return res

    # 7. Fallback Tra cứu kho
    res = handle_stock_and_price(raw, clean)
    if res:
        return res

    # 8. Thử xử lý Thống kê tổng hợp
    res = handle_summary_stats(raw, clean)
    if res:
        return res

    # 9. Fallback thông minh: hướng dẫn người dùng
    return {
        "type": "help",
        "message": f"🤖 Tôi chưa hiểu rõ câu lệnh: *'{raw}'*.\n\n"
                   f"**Bạn có thể thử các mẫu câu tiện lợi sau:**\n"
                   f"• *'chi 150k tiền xăng xe'* (Tự ghi sổ chi)\n"
                   f"• *'thu 1tr2 khách cọc làm đèn'* (Tự ghi sổ thu)\n"
                   f"• *'chị Cẩm Tuyền lắp v20 base giá 6500, đèn s3 giá 1500, giảm giá 1200'* (Tự ghi báo cáo đèn combo)\n"
                   f"• *'lắp bi gầm F10 xe Innova 63A-123.45'* (Tự ghi báo cáo đèn)\n"
                   f"• *'tra cứu xe 63A-394.65'* (Xem lịch sử & hạn bảo hành)\n"
                   f"• *'giá bán bóng s3'* (Tra cứu kho & giá vốn)\n"
                   f"• *'tổng kết quỹ'* (Xem số dư tiền mặt hiện tại)"
    }

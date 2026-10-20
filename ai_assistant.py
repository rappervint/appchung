def extract_product_keyword(text):
    """Bóc tách từ khóa sản phẩm bất chấp có dấu, không dấu, câu hỏi, dấu chấm hỏi"""
    # 1. Bỏ dấu câu
    clean = re.sub(r'[^\w\s]', ' ', text)
    
    # 2. Danh sách các cụm từ hỏi giá / tồn kho (cả có dấu lẫn không dấu)
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
║  - Ra lệnh nhập đơn báo cáo đèn (bi led, bi gầm, f10, s3...)         ║
║  - Ra lệnh tạo đơn bán hàng & phụ kiện                               ║
║  - Tra cứu bảo hành, lịch sử đơn hàng theo biển số xe/SĐT/tên khách  ║
║  - Tra cứu tồn kho & giá bán sản phẩm                                ║
║  - Thống kê doanh số, số dư quỹ tiền mặt hiện tại                    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_BANHANG = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
DB_DEN = os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db')
DB_THUCHI = os.path.join(BASE_DIR, 'app_thuchi', 'finance.db')

# Bản đồ chuẩn hóa từ viết tắt & tiếng Việt không dấu / lỗi gõ phím
SYNONYMS = {
    # Thu chi
    'chi': ['chi', 'tra', 'mua', 'dong', 'nop', 'ung', 'ung truoc', 'xuat tien', 'tien an', 'tien com', 'xang', 'mat bang'],
    'thu': ['thu', 'nhan', 'thu tien', 'khach tra', 'nap', 'vao quy', 'tien ve'],
    # Đèn
    'den': ['den', 'bi', 'bi gam', 'bi led', 'bi pha', 'f10', 's3', 's6', 's8', 's9', 'turbo', 'hyper', 'pro', 'v20', 'm30', 'm40', 'titan'],
    # Tra cứu
    'tracuu': ['tra cuu', 'tim', 'kiem tra', 'check', 'xem', 'bao hanh', 'don hang', 'khach hang', 'bien so', 'sdt'],
    # Tồn kho
    'tonkho': ['ton kho', 'gia ban', 'con hang', 'het hang', 'bao nhieu', 'gia goc', 'gia von'],
    # Thống kê
    'thongke': ['thong ke', 'doanh thu', 'tong ket', 'so du', 'con bao nhieu', 'quy', 'quy tien']
}

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

def parse_vietnamese_money(text):
    """
    Phân tích số tiền tiếng Việt cực kỳ linh hoạt:
    500k -> 500000
    1.5tr / 1,5tr / 1.5trieu -> 1500000
    2tr -> 2000000
    500 nghin / 500 ngàn -> 500000
    350000 -> 350000
    """
    clean = remove_accents(text).replace(',', '.')
    
    # 1. Triệu: 1.5tr, 2tr, 3trieu
    m_tr = re.search(r'(\d+(?:\.\d+)?)\s*(?:tr|trieu|m)\b', clean)
    if m_tr:
        return int(float(m_tr.group(1)) * 1000000)
        
    # 2. Nghìn: 500k, 50k, 120nghin, 120ngan
    m_k = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|nghin|ngan)\b', clean)
    if m_k:
        return int(float(m_k.group(1)) * 1000)

    # 3. Chuỗi số có dấu chấm ngăn cách: 1.500.000 hoặc 500.000
    m_dot = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\b', text)
    if m_dot:
        return int(m_dot.group(1).replace('.', ''))

    # 4. Số nguyên liên tục >= 1000
    m_num = re.search(r'\b(\d{4,10})\b', clean)
    if m_num:
        return int(m_num.group(1))

    # 5. Trong sổ thu chi hay gõ tắt: chi 50 (nghĩa là 50k) nếu số nhỏ hơn 1000
    m_small = re.search(r'(?:thu|chi|gia)\s+(\d{1,3})\b', clean)
    if m_small:
        val = int(m_small.group(1))
        # Nếu nhập 50, 100, 200 mà trước đó là thu/chi -> ngầm định tính theo nghìn đồng (k)
        return val * 1000

    return 0

def extract_license_plate(text):
    """
    Nhận diện biển số xe ô tô / xe máy:
    63A-123.45, 63A12345, 51H-999.88, 66A-526.04, 71A 22726
    """
    clean = text.upper()
    # Mẫu biển số chuẩn: 2 số + 1 chữ cái + [dấu cách/gạch] + 4-5 số
    m = re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5}(?:\.[0-9]{2})?)\b', clean)
    if m:
        plate = m.group(1).replace(' ', '-')
        return plate
    return ""

def extract_phone(text):
    """
    Tìm số điện thoại (10 số bắt đầu bằng 03, 05, 07, 08, 09)
    """
    m = re.search(r'\b(0[35789]\d{8})\b', text)
    return m.group(1) if m else ""

# ─────────────────────────────────────────────────────────────────────────────
# CÁC HÀM XỬ LÝ CHUYÊN BIỆT THEO Ý ĐỊNH (INTENTS)
# ─────────────────────────────────────────────────────────────────────────────

def handle_thuchi(raw_text, clean_text):
    """Xử lý lệnh ghi sổ thu hoặc chi"""
    is_chi = bool(re.search(r'\b(chi|tra|mua|dong|nop|ung|ung truoc|xuat tien|tien an|com|xang|mat bang|phi)\b', clean_text))
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

    # Trích xuất nội dung ghi chú (bỏ các từ khóa thu/chi/số tiền)
    note = raw_text
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

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
                       f"• **Kỳ ghi nhận:** {period_name}\n"
                       f"• **Số dư quỹ kỳ này hiện tại:** **{balance:,.0f} đ**\n\n"
                       f"👉 [Bấm vào đây để mở Sổ Thu Chi](/thuchi/)"
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi ghi sổ thu chi: {str(e)}"}

def handle_baocao_den(raw_text, clean_text):
    """Xử lý lệnh ghi đơn báo cáo doanh thu đèn"""
    # Dấu hiệu nhận biết đơn đèn
    is_den = bool(re.search(r'\b(den|bi gam|bi led|bi pha|f10|naoevo|s3|s6|s8|s9|turbo|hyper|v20|m30|m40|titan)\b', clean_text))
    has_action = bool(re.search(r'\b(lap|gan|ban|do|thay|nhap|ghi)\b', clean_text))
    
    if not (is_den and (has_action or 'cho xe' in clean_text or 'khach' in clean_text or parse_vietnamese_money(raw_text) > 0)):
        return None

    plate = extract_license_plate(raw_text)
    amount = parse_vietnamese_money(raw_text)

    # Nhận diện dòng xe (VF3, VF5, Inova, Camry, Vios, Fortuner, Xpander...)
    car_models = ['VF3', 'VF5', 'VF6', 'VF7', 'VF8', 'VF9', 'XPANDER', 'INNOVA', 'VIOS', 'ACCENT', 'CITY', 
                  'FORTUNER', 'CAMRY', 'RANGER', 'CARNIVAL', 'EVEREST', 'KONA', 'ELANTRA', 'MG5', 'TERRITORY', 'BRV']
    found_car = ""
    for car in car_models:
        if car.lower() in clean_text:
            found_car = car
            break

    # Nhận diện mã đèn
    lamp_models = [
        ('F10 TURBO', ['f10 turbo', 'turbo']),
        ('F10 PRO', ['f10 pro', 'pro v2']),
        ('F10 HYPER', ['f10 hyper', 'hyper']),
        ('F10 NEW 2.0', ['f10 new', 'f10 2.0', 'f10']),
        ('NAOEVO S3 PRO', ['s3 pro', 's3']),
        ('NAOEVO S6', ['s6']),
        ('NAOEVO S8', ['s8']),
        ('NAOEVO S9', ['s9']),
        ('BI LED V20 BASE', ['v20 base', 'v20']),
        ('BI LED M30 ULTRA', ['m30']),
        ('BI LED M40 ULTRA', ['m40']),
        ('TITAN GOLD', ['titan gold', 'titan']),
    ]
    found_lamp = "BI LED"
    for lamp_name, keywords in lamp_models:
        if any(kw in clean_text for kw in keywords):
            found_lamp = lamp_name
            break

    # Giá mặc định nếu không nói giá
    default_prices = {
        'F10 TURBO': 5100,
        'F10 PRO': 5500,
        'F10 HYPER': 5500,
        'F10 NEW 2.0': 3900,
        'NAOEVO S3 PRO': 1500,
        'NAOEVO S6': 1800,
        'NAOEVO S8': 2500,
        'NAOEVO S9': 2800,
        'BI LED V20 BASE': 5850,
        'BI LED M30 ULTRA': 5500,
        'BI LED M40 ULTRA': 6500,
        'TITAN GOLD': 6750
    }
    if amount <= 0:
        price_k = default_prices.get(found_lamp, 3500)
        amount = price_k * 1000
    else:
        price_k = int(amount / 1000)

    # Tên khách
    cust_name = plate if plate else (found_car if found_car else "KHÁCH LẺ")
    m_cust = re.search(r'(?:khach|anh|chi|chu)\s+([a-zA-ZÀ-ỹ0-9\s]+?)(?:xe|lap|den|gia|\d|$)', raw_text, re.IGNORECASE)
    if m_cust:
        cand = m_cust.group(0).strip().upper()
        if len(cand) < 30:
            cust_name = cand

    today_str = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists(DB_DEN):
        return {"type": "error", "message": "Chưa tìm thấy cơ sở dữ liệu Báo Cáo Đèn!"}

    try:
        conn = sqlite3.connect(DB_DEN, timeout=10)
        c = conn.cursor()
        c.execute("""
            INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin)
            VALUES (?, ?, ?, ?, ?, ?, 'AI_ASSISTANT')
        """, (today_str, found_lamp, cust_name, found_car or 'XE Ô TÔ', 1, price_k))
        conn.commit()
        order_id = c.lastrowid
        conn.close()

        return {
            "type": "success",
            "module": "den",
            "message": f"💡 ĐÃ GHI NHẬN ĐƠN BÁO CÁO ĐÈN THÀNH CÔNG!\n\n"
                       f"• **Mã đơn:** #{order_id}\n"
                       f"• **Sản phẩm:** **{found_lamp}**\n"
                       f"• **Khách hàng:** {cust_name}\n"
                       f"• **Dòng xe:** {found_car or 'Chưa rõ dòng xe'}\n"
                       f"• **Biển số:** {plate or 'Chưa ghi'}\n"
                       f"• **Doanh thu:** **{amount:,.0f} đ** ({price_k:,}k)\n"
                       f"• **Ngày lắp:** {today_str}\n\n"
                       f"👉 [Bấm vào đây để xem Báo Cáo Doanh Thu Đèn](/den/)"
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi lưu báo cáo đèn: {str(e)}"}

def handle_search_warranty_and_orders(raw_text, clean_text):
    """Tra cứu bảo hành và lịch sử đơn hàng theo biển số xe, SĐT, tên khách"""
    is_search = bool(re.search(r'\b(tim|kiem tra|tra cuu|check|xem|bao hanh|lich su|don hang)\b', clean_text))
    plate = extract_license_plate(raw_text)
    phone = extract_phone(raw_text)

    # Nếu có biển số xe hoặc SĐT hoặc có từ khóa tra cứu
    if not (plate or phone or is_search):
        return None

    search_query = plate if plate else (phone if phone else "")
    if not search_query:
        # Lấy từ sau từ tra cứu / tìm
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
            
            # Tìm trong orders
            c.execute("""
                SELECT id, customer_name, phone, license_plate, install_date, total_price 
                FROM orders 
                WHERE license_plate LIKE ? OR phone LIKE ? OR customer_name LIKE ?
                ORDER BY install_date DESC LIMIT 5
            """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
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
        except Exception as e:
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
        except Exception as e:
            pass

    if not results:
        return {
            "type": "info",
            "message": f"🔎 Không tìm thấy đơn hàng hoặc thông tin bảo hành nào khớp với từ khóa **'{search_query}'**.\nBạn vui lòng kiểm tra lại biển số xe hoặc số điện thoại nhé!"
        }

    # Tổng hợp phản hồi cho khách
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
    """Tra cứu tồn kho & giá bán sản phẩm thông minh (hiểu câu hỏi tự nhiên: f10 pro giá bao nhiêu, có còn hàng không...)"""
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

        # 1. Thử tìm chính xác cụm từ trước
        c.execute("""
            SELECT code, name, category, price, cost_price, stock, warranty_months 
            FROM products 
            WHERE UPPER(name) LIKE ? OR UPPER(code) LIKE ?
            ORDER BY stock DESC LIMIT 6
        """, (f"%{kw.upper()}%", f"%{kw.upper()}%"))
        rows = c.fetchall()

        # 2. Nếu không ra, tách từng từ khóa (token match: VD 'f10' và 'pro')
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

        # 3. Nếu vẫn chưa có, tìm theo từ đầu tiên
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

    # Lấy số dư thu chi
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

    # Lấy tổng đơn bán hàng hôm nay
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
                       "2. **Ghi Báo Cáo Đèn:** *'lắp F10 Turbo xe Camry 63A-123.45 giá 5.1tr'*\n"
                       "3. **Tra Cứu Bảo Hành & Đơn:** *'tra cứu biển số 63A-394.65'*, *'kiểm tra bảo hành anh Sang'*\n"
                       "4. **Tra Cứu Giá & Tồn Kho:** *'giá bi led v20'*, *'tồn kho vietmap'*\n"
                       "5. **Báo Cáo Nhanh:** *'tổng kết sổ quỹ'*, *'doanh thu hôm nay'*\n\n"
                       "Hãy gõ câu lệnh bạn muốn thực hiện nhé!"
        }

    raw = user_text.strip()
    clean = remove_accents(raw)

    # 1. Thử xử lý Tra cứu bảo hành / đơn hàng trước (nếu có biển số/SĐT)
    if extract_license_plate(raw) or extract_phone(raw) or any(k in clean for k in ['bao hanh', 'tra cuu', 'tim xe', 'check xe']):
        res = handle_search_warranty_and_orders(raw, clean)
        if res:
            return res

    # 2. Thử xử lý Giá bán & tồn kho (nếu có từ giá, tồn, kho)
    if any(k in clean for k in ['ton kho', 'con hang', 'het hang', 'kho']) or (any(k in clean for k in ['gia', 'bao gia']) and not any(k in clean for k in ['lap', 'gan', 'do', 'ban', 'thay', 'cho xe', 'khach'])): 
        res = handle_stock_and_price(raw, clean)
        if res:
            return res

    # 3. Thử xử lý Sổ thu chi (thu, chi, tiền ăn, tiền xăng...)
    if any(k in clean for k in ['thu', 'chi', 'tra tien', 'mua', 'dong tien', 'nop', 'ung']):
        res = handle_thuchi(raw, clean)
        if res:
            return res

    # 4. Thử xử lý Báo cáo đèn (lắp đèn, gắn bi...)
    res = handle_baocao_den(raw, clean)
    if res:
        return res

    # 5. Fallback tra cứu bảo hành / đơn
    res = handle_search_warranty_and_orders(raw, clean)
    if res:
        return res

    # 6. Fallback tra cứu kho
    res = handle_stock_and_price(raw, clean)
    if res:
        return res

    # 5. Thử xử lý Thống kê tổng hợp
    res = handle_summary_stats(raw, clean)
    if res:
        return res

    # 6. Fallback thông minh: hướng dẫn người dùng
    return {
        "type": "help",
        "message": f"🤖 Tôi chưa hiểu rõ câu lệnh: *'{raw}'*.\n\n"
                   f"**Bạn có thể thử các mẫu câu tiện lợi sau:**\n"
                   f"• *'chi 150k tiền xăng xe'* (Tự ghi sổ chi)\n"
                   f"• *'thu 1tr2 khách cọc làm đèn'* (Tự ghi sổ thu)\n"
                   f"• *'lắp bi gầm F10 xe Innova 63A-123.45'* (Tự ghi báo cáo đèn)\n"
                   f"• *'tra cứu xe 63A-394.65'* (Xem lịch sử & hạn bảo hành)\n"
                   f"• *'giá bán bóng s3'* (Tra cứu kho & giá vốn)\n"
                   f"• *'tổng kết quỹ'* (Xem số dư tiền mặt hiện tại)"
    }

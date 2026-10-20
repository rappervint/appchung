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
# BỘ NHỚ HỘI THOẠI HỎI ĐÁP TỪNG BƯỚC (WIZARD CONVERSATIONAL STATE)
# ─────────────────────────────────────────────────────────────────────────────
WIZARD_SESSIONS = {}

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

    flow = session['flow']
    step = session['step']
    data = session['data']

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

        # Bước 5: Giảm giá / Chiết khấu (Có chữ k tự hiểu nhân thêm 1000)
        elif step == 5:
            if clean in ['0', 'không', 'khong', 'k', 'ko', '', 'ko giam', 'khong giam']:
                discount_k = 0
            else:
                p_val = parse_vietnamese_money(user_text, default_thousands=True)
                if p_val > 0:
                    discount_k = int(round(p_val / 1000))
                else:
                    discount_k = 0

            data['discount_k'] = discount_k
            session['step'] = 6
            disc_label = f"-{discount_k*1000:,.0f} đ (-{discount_k:,}k)" if discount_k > 0 else "0 đ (Không giảm)"
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
            disc_text = f"\n• 🏷️ **Giảm giá:** -{data['discount_k']*1000:,.0f} đ (-{data['discount_k']:,}k)" if data['discount_k'] > 0 else "\n• 🏷️ **Giảm giá:** 0 đ (Không giảm)"
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

    return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. NHẬP BÁO CÁO DOANH THU ĐÈN TỐI ƯU SIÊU TỐC (ONE-SHOT)
# ─────────────────────────────────────────────────────────────────────────────

def handle_baocao_den(raw_text, clean_text):
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

    text = raw_text.strip()

    # 1. Biển số xe
    m_plate = re.search(r'\b(\d{2}[A-Z]{1,2}[\s\-]?[0-9]{3,5}(?:\.[0-9]{1,2})?)\b', text.upper())
    plate = m_plate.group(1).strip() if m_plate else ''
    if plate:
        text = text.replace(m_plate.group(0), ' ')

    # 2. Ngày ghi nhận
    order_date, text = extract_date(text)

    # 3. Dòng xe
    found_car = ''
    for c in CAR_MODELS_LIST:
        m_c = re.search(r'(?:cho\s+xe\s+|xe\s+)?\b' + c + r'\b', text, re.IGNORECASE)
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
        c = re.sub(r'^(?:lắp|lap|gắn|gan|thay|bán|ban|độ|do|cho)\s+', '', chunk, flags=re.IGNORECASE).strip()
        if not c:
            continue

        qty = 1
        m_qty = re.search(r'\b(\d+)\s*(?:bộ|bo|cặp|cap|cái|cai|hộp|hop)\b', c, re.IGNORECASE)
        if m_qty:
            qty = int(m_qty.group(1))
            c = c[:m_qty.start()] + ' ' + c[m_qty.end():]

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

        matched_name = ''
        matched_default = 3500
        for pat, cname, dprice in LAMP_CATALOG:
            m_l = re.search(pat, raw_name, re.IGNORECASE)
            if m_l:
                matched_name = cname
                matched_default = dprice
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

    cust_name = cust_special
    if not cust_name and cust_candidates:
        cust_name = cust_candidates[0].strip().title()
    if not cust_name:
        cust_name = plate if plate else (found_car if found_car else 'KHÁCH LẺ')

    cust_name = re.sub(r'\bThay\b', 'Thầy', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChi\b', 'Chị', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bChu\b', 'Chú', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bBac\b', 'Bác', cust_name, flags=re.IGNORECASE)
    cust_name = re.sub(r'\bEm\b', 'Em', cust_name, flags=re.IGNORECASE)

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

        cy, cm = get_current_cycle()
        start_date, end_date = get_cycle_dates(cy, cm)

        c.execute("""
            SELECT COUNT(*), COALESCE(SUM(quantity), 0), COALESCE(SUM(price_k), 0)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        row = c.fetchone()
        order_count = row[0] or 0
        total_qty = row[1] or 0
        total_k = row[2] or 0

        c.execute("""
            SELECT COUNT(DISTINCT customer_name || '_' || car_model)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
        """, (start_date, end_date))
        car_count = c.fetchone()[0] or 0

        today_str = datetime.now().strftime('%Y-%m-%d')
        c.execute("""
            SELECT id, product_name, customer_name, car_model, quantity, price_k
            FROM orders
            WHERE order_date = ?
            ORDER BY id DESC
        """, (today_str,))
        today_rows = c.fetchall()

        c.execute("""
            SELECT product_name, SUM(quantity), SUM(price_k)
            FROM orders
            WHERE order_date >= ? AND order_date <= ?
            GROUP BY product_name
            ORDER BY SUM(quantity) DESC, SUM(price_k) DESC LIMIT 5
        """, (start_date, end_date))
        top_prods = c.fetchall()
        conn.close()

        reply = (
            f"💡 **BÁO CÁO DOANH THU ĐÈN — KỲ THÁNG {cm:02d}/{cy}**\n"
            f"*(Tính từ ngày {start_date.split('-')[2]}/{start_date.split('-')[1]} đến {end_date.split('-')[2]}/{end_date.split('-')[1]})*\n\n"
            f"• 💰 **Tổng doanh thu:** **{total_k*1000:,.0f} đ** ({total_k:,}k)\n"
            f"• 📦 **Tổng số bộ đèn đã lắp:** **{total_qty} bộ** ({order_count} dòng đơn)\n"
            f"• 🚗 **Số lượt xe phục vụ:** **{car_count} xe**\n\n"
        )

        if today_rows:
            reply += f"🕒 **ĐƠN ĐÈN LẮP HÔM NAY ({datetime.now().strftime('%d/%m/%Y')} - {len(today_rows)} đơn):**\n"
            for r in today_rows:
                reply += f"  • #{r[0]}: **{r[4]}x {r[1]}** — Xe: {r[3]} ({r[2]}) ➔ **{r[5]*1000:,.0f} đ**\n"
            reply += "\n"
        else:
            reply += f"🕒 **Hôm nay ({datetime.now().strftime('%d/%m/%Y')}):** Chưa có đơn đèn nào được ghi nhận.\n\n"

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
# 4. SỔ THU CHI (ONE-SHOT)
# ─────────────────────────────────────────────────────────────────────────────

def handle_thuchi(raw_text, clean_text):
    """Xử lý lệnh ghi sổ thu hoặc chi (One-shot)"""
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

def process_ai_command(user_text, session_id="default_user"):
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

    # ═════════════════════════════════════════════════════════════════════
    # 0. NẾU ĐANG TRONG PHIÊN HỎI ĐÁP TỪNG BƯỚC (WIZARD ACTIVE)
    # ═════════════════════════════════════════════════════════════════════
    if session_id in WIZARD_SESSIONS:
        res = handle_wizard_step(raw, session_id)
        if res:
            return res

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

    # 3. Hủy / Xóa đơn đèn vừa nhập nhầm
    if any(k in clean for k in ['xoa don', 'huy don', 'undo']):
        res = handle_undo_last_lamp_order(raw, clean)
        if res:
            return res

    # 4. Thống kê & Báo cáo doanh số đèn (kỳ tháng, hôm nay, top bán chạy)
    if any(k in clean for k in ['doanh thu den', 'doanh so den', 'bao cao den', 'ban duoc bao nhieu den', 'may xe den', 'don den hom nay', 'top den', 'den ban chay']):
        res = handle_baocao_den_stats(raw, clean)
        if res:
            return res

    # 5. Tra cứu giá bán & tồn kho (nếu là câu hỏi giá thuần túy)
    is_asking_price = bool(re.search(r'\b(bao nhieu|nhieu tien|hoi gia|xem gia|bao gia|con hang|ton kho|het hang)\b', clean)) or \
                      (bool(re.search(r'\b(gia|gia ban)\b', clean)) and not bool(re.search(r'\b(lap|gan|do|thay|nhap|don)\b', clean)) and not bool(re.search(r'\bgia\s+\d+', clean)))
    if is_asking_price:
        res = handle_stock_and_price(raw, clean)
        if res:
            return res

    # 6. Tra cứu bảo hành / đơn hàng theo biển số hoặc SĐT
    has_lamp_keyword = any(k in clean for k in ['v20', 'f10', 's3', 's6', 's8', 's9', 'm30', 'm40', 'turbo', 'hyper', 'titan', 'naoevo', '301', 'f150', 'cb150'])
    if (extract_license_plate(raw) or extract_phone(raw) or any(k in clean for k in ['bao hanh', 'tra cuu', 'tim xe', 'check xe'])) and not has_lamp_keyword:
        res = handle_search_warranty_and_orders(raw, clean)
        if res:
            return res

    # 7. Nhập Đơn Báo Cáo Đèn (ƯU TIÊN CAO khi có mã đèn hoặc hành động lắp đặt)
    if has_lamp_keyword or (any(k in clean for k in ['lap', 'gan', 'do', 'thay', 'ban']) and any(k in clean for k in ['den', 'bi', 'bong', 'pha', 'gam'])):
        res = handle_baocao_den(raw, clean)
        if res:
            return res

    # 8. Sổ thu chi (thu, chi, tiền ăn, tiền xăng...)
    if any(k in clean for k in ['thu', 'chi', 'tra tien', 'mua', 'dong tien', 'nop', 'ung']):
        res = handle_thuchi(raw, clean)
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

    # 12. Fallback thông minh
    return {
        "type": "help",
        "message": f"🤖 Tôi chưa hiểu rõ câu lệnh: *'{raw}'*.\n\n"
                   f"**Bạn có thể thử:**\n"
                   f"• Gõ *'chi'* để AI hỏi từng bước số tiền, ngày, lý do.\n"
                   f"• Gõ *'doanh thu đèn'* để AI hỏi từng bước lên đơn đèn.\n"
                   f"• Hoặc gõ nhanh: *'anh Cường accent f10 new 3900'*, *'chi 350k tiền cơm'*."
    }

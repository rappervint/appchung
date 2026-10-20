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

def handle_stock_and_price(raw_text, clean_text, require_explicit_intent=False):
    """
    Tra cứu sản phẩm trong kho hàng cực kỳ thông minh (Fuzzy Search):
    - Người dùng chỉ cần gõ bất kỳ từ ngữ nào (VD: '70mai', 'm310', 'blam', 'vincar', 'sub 10', 'innova 2026')
    - Không cần phải gõ đúng 100% tên hàng
    - Tìm không dấu, có dấu, tìm theo mã SP..., nhóm hàng, tên hàng
    - Tự động sắp xếp sản phẩm còn tồn kho và có độ khớp cao nhất lên đầu
    """
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
        top_matches = [r[1] for r in results[:6] if r[0] >= 30]

        if not top_matches:
            if require_explicit_intent:
                return {"type": "info", "message": f"📦 Không tìm thấy mặt hàng nào khớp với từ khóa: **'{raw_q}'** trong kho."}
            return None

        reply = f"🏷️ **BÁO GIÁ SẢN PHẨM: '{raw_q.upper()}'**\n\n"

        for p in top_matches:
            war_m = p['warranty_months'] or 0
            war_badge = f"{war_m} tháng" if war_m > 0 else (p['warranty_raw'] or 'Theo nhà sản xuất')
            cat_label = f"📁 *{p['category']}*\n" if p['category'] else ""

            reply += f"• **{p['name']}** `({p['code'] or 'SP'})`\n"
            if cat_label:
                reply += f"  {cat_label}"
            reply += f"  - 💰 Giá bán: **{p['price']:,.0f} đ** | 🛡️ Bảo hành: **{war_badge}**\n\n"

        reply += "👉 [Xem danh sách kho hàng](/banhang/)"
        return {
            "type": "success",
            "module": "banhang",
            "message": reply
        }
    except Exception as e:
        return {"type": "error", "message": f"Lỗi tra cứu mặt hàng kho: {str(e)}"}

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

    if any(k in clean_text for k in ['dang kiem', 'kiem dinh', 'do xuyen sang', 'co bi phat khong', 'bi bat khong']):
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

    # 3.2. Kính lái 3M Crystalline CR50BLK (HỎI RIÊNG KÍNH LÁI 3M)
    is_single_3m_windshield = (
        bool(re.search(r'\b(cr50|cr50blk|cr 50)\b', clean_text)) or
        (bool(re.search(r'\b(kinh lai 3m|lai 3m|gia le kinh lai 3m)\b', clean_text)) and not any(k in clean_text for k in ['ket hop', 'suon', 'ntech', 'con lai', 'ceramax']))
    )
    if is_single_3m_windshield:
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "☀️ **KÍNH LÁI 3M CRYSTALLINE CR50BLK (MỸ):**\n"
                "• **Giá dán lẻ:** **5.700.000 đ**\n"
                "• **Thông số:** Xuyên sáng `50%` (chuẩn kiểm định mới) | Cắt IR `98%` | Cắt UV `99.9%` | Giảm lóa `34%`\n"
                "• **Bảo hành:** **10 năm điện tử chính hãng 3M USA**\n"
                "• **Đăng kiểm:** Dùng mã CR50BLK đạt chuẩn >50% VLT, gara không nhập mã CR40BLK."
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
                        "🎁 Tặng 100% công lột keo cũ 500k. Kính lái 3M BH 10 năm, sườn Ntech BH 10 năm."
                    )
                }
            else:
                return {
                    "type": "success",
                    "module": "dichvu",
                    "message": (
                        "☀️ **GÓI KẾT HỢP: KÍNH LÁI 3M CR50BLK + SƯỜN & HẬU NTECH:**\n"
                        "• **Bản Ntech Cao Cấp (Khuyên dùng):** Sedan **8.5tr** | SUV **9.3tr**\n"
                        "• **Bản Ntech Tiêu Chuẩn (Tiết kiệm):** Sedan **7.6tr** | SUV **8.0tr**\n"
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

    # Vietmap M1
    if bool(re.search(r'\b(m1|vietmap m1|cam m1)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📹 **CAMERA HÀNH TRÌNH VIETMAP M1 (2 MẮT TRƯỚC + SAU):**\n"
                "• **Giá trọn gói:** **6.190.000 đ** (Trước 2K + Sau Full HD)\n"
                "• **Tính năng độc quyền:** Màn hình luôn báo tốc độ giới hạn + Cảnh báo camera phạt nguội, cấm vượt\n"
                "• **Quà tặng:** Tặng thẻ nhớ chính hãng, miễn phí đi dây nguồn âm kín tại gara."
            )
        }

    # Vietmap M2
    if bool(re.search(r'\b(m2|vietmap m2|cam m2)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📹 **CAMERA HÀNH TRÌNH VIETMAP M2 (4K - XEM TỪ XA):**\n"
                "• **Giá trọn gói:** **8.980.000 đ**\n"
                "• **Tính năng:** Mắt trước 4K, **tặng SIM 12 tháng** xem video trực tiếp & định vị xe từ xa qua điện thoại."
            )
        }

    # 70mai A510
    if bool(re.search(r'\b(a510|70mai a510)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📹 **CAMERA HÀNH TRÌNH 70MAI A510 (SONY STARVIS 2):**\n"
                "• **Giá trọn gói:** **3.400.000 đ** (Trước 3K + Sau, cảm biến Sony quay đêm siêu sáng)\n"
                "• **Quà tặng:** Tặng thẻ nhớ 64GB, tích hợp GPS hiển thị tốc độ."
            )
        }

    # 70mai A800SE
    if bool(re.search(r'\b(a800se|a800)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📹 **CAMERA HÀNH TRÌNH 70MAI A800SE (4K TRƯỚC + SAU):**\n"
                "• **Bản thường:** **3.600.000 đ** *(Tặng thẻ 64GB)*\n"
                "• **Bản SpeedEye (Có cảnh báo giao thông):** **4.800.000 đ** *(Tặng thẻ 64GB)*"
            )
        }

    # 70mai A200
    if bool(re.search(r'\b(a200|70mai a200)\b', clean_text)):
        return {
            "type": "success",
            "module": "dichvu",
            "message": (
                "📹 **CAMERA HÀNH TRÌNH 70MAI A200 2K:**\n"
                "• **Giá trọn gói:** **2.500.000 đ** (Gồm mắt Trước + Sau Full HD, tặng thẻ 32GB - Ngon bổ rẻ nhất)."
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

    # Phim cách nhiệt riêng cho VinFast VF3
    if any(k in clean_text for k in ['vf3', 'vf 3', 'vinfast vf3']):
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
    is_cam = bool(re.search(r'\b(cam\s*hanh\s*trinh|camera\s*hanh\s*trinh|70mai|vietmap|a510|a800se|s720|r440|s860|the\s*nho)\b', clean_text))
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

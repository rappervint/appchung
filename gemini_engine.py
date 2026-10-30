"""

╔══════════════════════════════════════════════════════════════════════╗

║         HỆ THỐNG TRỢ LÝ AI ĐIỀU HÀNH THÔNG MINH GEMINI FLASH         ║

║                    GARA Ô TÔ TRẦN BÌNH AUTO                          ║

║                                                                      ║

║  Tích hợp Google Gemini 3.5 Flash / Automatic Function Calling (AFC) ║

║  - Quản trị thông minh: Chỉnh sửa đơn hàng, Cập nhật kho, Sửa khách  ║

║  - Tra cứu đa chiều: Bảo hành biển số, SĐT, Tên khách + Dòng xe      ║

║  - Quản lý sổ thu chi, doanh thu đèn, tư vấn phụ kiện & kỹ thuật     ║

║  - Tự động duy trì ngữ cảnh đa lượt (Multi-turn conversational state)║

╚══════════════════════════════════════════════════════════════════════╝

"""



import os

import re

import json

import sqlite3

from datetime import datetime, timedelta



try:

    from google import genai

    from google.genai import types

    GENAI_AVAILABLE = True

except ImportError:

    GENAI_AVAILABLE = False



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_BANHANG = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')

DB_DEN = os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db')

DB_THUCHI = os.path.join(BASE_DIR, 'app_thuchi', 'finance.db')



# Danh mục nhận diện tên đèn chuẩn hóa (Tất cả giá lấy động 100% từ kho dữ liệu tiem_lap_do.db)

LAMP_CATALOG = [

    (r'\bv20\s*base\b', 'V20 BASE', 0),

    (r'\bv20\s*ultra\b|\bv20l\b|\bv20\b', 'BI LED V20', 0),

    (r'\b(?:xlight|naoevo)?\s*s3\s*pro\b|\bs3\s*pro\b', 'XLIGHT S3 PRO', 0),

    (r'\b(?:xlight|naoevo)?\s*s3\b|\bs3\b', 'NAOEVO S3', 0),

    (r'\b(?:xlight|naoevo)?\s*s6\s*pro\b|\bs6\s*pro\b', 'NAOEVO S6 PRO', 0),

    (r'\b(?:xlight|naoevo)?\s*s6\b|\bs6\b', 'NAOEVO S6', 0),

    (r'\b(?:xlight|naoevo)?\s*s8\s*pro\b|\bs8\s*pro\b', 'NAOEVO S8 PRO', 0),

    (r'\b(?:xlight|naoevo)?\s*s8\b|\bs8\b', 'NAOEVO S8', 0),

    (r'\b(?:xlight|naoevo)?\s*s9\s*pro\b|\bs9\s*pro\b', 'NAOEVO S9 PRO', 0),

    (r'\b(?:xlight|naoevo)?\s*s9\b|\bs9\b', 'NAOEVO S9', 0),

    (r'\bf10\s*pro\s*v2\b|\bf10\s*pro\b', 'F10 PRO V2', 0),

    (r'\bf10\s*turbo\b', 'F10 TURBO', 0),

    (r'\bf10\s*hyper\b|\bf10\s*heyper\b', 'F10 HYPER', 0),

    (r'\bf10\s*new\s*2\.?0\b|\bf10\s*new\b|\bf10\s*2\.?0\b|\bf10\b', 'F10 NEW 2.0', 0),

    (r'\bf10\s*3\s*mau\b|\bf10\s*ba\s*mau\b', 'F10 BA MÀU', 0),

    (r'\bm10\s*ultra\b|\bm10\b', 'M10 ULTRA', 0),

    (r'\bm20\s*ultra\b|\bm20\b', 'M20 ULTRA', 0),

    (r'\bm30\s*ultra\b|\bm30\b', 'M30 ULTRA', 0),

    (r'\bm40\s*ultra\b|\bm40\b', 'M40 ULTRA', 0),

    (r'\btitan\s*gold\b', 'TITAN GOLD', 0),

    (r'\btitan\s*black\b', 'TITAN BLACK', 0),

    (r'\btitan\s*platinum\b', 'TITAN PLATINUM', 0),

    (r'\b(?:titan\s*)?f1\s*turbo\s*s\b', 'TITAN F1 TURBO S', 0),

    (r'\b(?:titan\s*)?f1\s*turbo\b', 'TITAN F1 TURBO', 0),

    (r'\b(?:titan\s*)?f1\s*gt\b', 'TITAN F1 GT', 0),

    (r'\bg1\s*turbo\b', 'G1 TURBO', 0),

    (r'\bxlight\s*301\b|\b301\b', 'XLIGHT 301', 0),

    (r'\bf150\s*pro\b|\bf150\b', 'F150 PRO', 0),

    (r'\bcb150\b', 'CB150', 0),

]



CONFIG_FILE = os.path.join(BASE_DIR, 'gemini_config.json')



def load_gemini_config():

    cfg = {

        "api_key": "",

        "preferred_model": "gemini-3.5-flash-lite",

        "fallback_model": "gemini-3.5-flash",

        "enabled": True

    }

    if os.path.exists(CONFIG_FILE):

        try:

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:

                loaded = json.load(f)

                cfg.update(loaded)

        except Exception as e:

            print(f"[GeminiEngine] Lỗi đọc gemini_config.json: {e}")

    env_key = os.environ.get("GEMINI_API_KEY")

    if env_key:

        cfg["api_key"] = env_key

    return cfg



def save_gemini_config(cfg: dict):

    try:

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:

            json.dump(cfg, f, indent=2, ensure_ascii=False)

        global CURRENT_CONFIG, DEFAULT_API_KEY, AVAILABLE_MODELS

        CURRENT_CONFIG = cfg

        DEFAULT_API_KEY = cfg.get("api_key", "")

        p_model = cfg.get("preferred_model") or cfg.get("model") or "gemini-3.5-flash-lite"

        f_model = cfg.get("fallback_model", "gemini-3.5-flash")

        AVAILABLE_MODELS = [p_model] if p_model == f_model else [p_model, f_model]

        return True

    except Exception as e:

        print(f"[GeminiEngine] Lỗi lưu gemini_config.json: {e}")

        return False



def get_available_gemini_models():

    """Lấy danh sách các model Gemini hỗ trợ cho API Key hiện tại và model đang kích hoạt."""

    cfg = load_gemini_config()

    active = cfg.get("preferred_model") or cfg.get("model") or "gemini-3.5-flash-lite"

    

    curated = [

        {

            "id": "gemini-3.5-flash-lite",

            "name": "Gemini 3.5 Flash-Lite",

            "badge": "Khuyên Dùng / Siêu Tốc",

            "tag": "lite",

            "desc": "Tốc độ xử lý nhanh nhất (< 0.5s), tiết kiệm token tối đa, tối ưu cho việc chốt đơn, tra cứu giá & giao tiếp gara hàng ngày.",

            "speed": "⚡ Cực Nhanh (~0.4s)",

            "cost": "🪙 Rất Thấp",

            "recommended": True

        },

        {

            "id": "gemini-3.5-flash",

            "name": "Gemini 3.5 Flash",

            "badge": "Thông Minh & Đa Năng",

            "tag": "flash",

            "desc": "Mô hình cân bằng hoàn hảo giữa trí tuệ nhân tạo thế hệ mới và tốc độ phản hồi cao. Xử lý tốt các câu lệnh phức tạp.",

            "speed": "🚀 Nhanh (~0.8s)",

            "cost": "🪙 Thấp",

            "recommended": False

        },

        {

            "id": "gemini-2.5-flash",

            "name": "Gemini 2.5 Flash",

            "badge": "Ổn Định Thế Hệ 2.5",

            "tag": "stable",

            "desc": "Phiên bản tiền nhiệm ổn định cao, nhận diện lệnh tự nhiên và function calling chuẩn xác.",

            "speed": "⏱️ Trung Bình (~1.1s)",

            "cost": "🪙 Tiết Kiệm",

            "recommended": False

        },

        {

            "id": "gemini-2.5-pro",

            "name": "Gemini 2.5 Pro",

            "badge": "Chuyên Gia Phân Tích",

            "tag": "pro",

            "desc": "Dành cho các câu hỏi phân tích chuyên sâu, so sánh chi tiết phương án kỹ thuật xe, độ bền vật liệu hoặc báo cáo tổng hợp phức tạp.",

            "speed": "🧠 Sâu (~2.2s)",

            "cost": "💎 Cao",

            "recommended": False

        },

        {

            "id": "gemini-3.7-flash",

            "name": "Gemini 3.7 Flash",

            "badge": "Công Nghệ Mới Nhất",

            "tag": "hybrid",

            "desc": "Thế hệ thử nghiệm mới nhất của Google hỗ trợ khả năng suy luận động Hybrid Reasoning.",

            "speed": "🔥 Nhanh (~0.9s)",

            "cost": "🪙 Vừa Phải",

            "recommended": False

        }

    ]

    return {

        "active_model": active,

        "models": curated,

        "api_key_configured": bool(cfg.get("api_key"))

    }



def switch_preferred_model(new_model_id: str) -> dict:

    """Đổi model Gemini đang dùng tức thì không cần restart máy chủ."""

    if not new_model_id:

        return {"success": False, "message": "Mã model không hợp lệ"}

    cfg = load_gemini_config()

    cfg["preferred_model"] = new_model_id

    cfg["model"] = new_model_id

    save_gemini_config(cfg)

    

    # Reset chat sessions cache

    global GEMINI_SESSIONS, REST_CHAT_HISTORY

    GEMINI_SESSIONS.clear()

    REST_CHAT_HISTORY.clear()

    

    return {

        "success": True,

        "active_model": new_model_id,

        "message": f"Đã chuyển sang model **{new_model_id}** thành công!"

    }



CURRENT_CONFIG = load_gemini_config()

DEFAULT_API_KEY = CURRENT_CONFIG.get("api_key", "")

AVAILABLE_MODELS = [

    CURRENT_CONFIG.get("preferred_model") or CURRENT_CONFIG.get("model") or "gemini-3.5-flash-lite",

    CURRENT_CONFIG.get("fallback_model", "gemini-3.5-flash")

]



def is_admin_or_edit_intent(clean_text: str) -> bool:

    """Nhận diện các câu lệnh quản trị: sửa đơn, cập nhật kho, đổi thông tin khách, xóa đơn..."""

    edit_keywords = [

        'sua don', 'chinh don', 'doi ten khach', 'doi sdt', 'sua sdt', 'doi so dien thoai',

        'sua so dien thoai', 'sua bien so', 'doi bien so', 'doi ngay', 'sua ngay', 'doi xe',

        'sua xe', 'doi gia', 'sua gia', 'sua mon', 'doi mon', 'cap nhat kho', 'sua kho',

        'chinh kho', 'doi gia ban', 'sua gia ban', 'doi gia von', 'sua gia von', 'ton kho ma',

        'cap nhat thong tin', 'doi thong tin', 'sua thong tin', 'xoa don', 'huy don'

    ]

    return any(k in clean_text for k in edit_keywords)



# Lưu trữ Client và phiên chat của Gemini theo session_id để giữ ngữ cảnh hội thoại

GEMINI_CLIENT = None

GEMINI_SESSIONS = {}

CURRENT_ACTIVE_SESSION_ID = "default_user"

CURRENT_USER_MESSAGE = ""



def set_current_session(session_id: str, user_message: str = ""):

    global CURRENT_ACTIVE_SESSION_ID, CURRENT_USER_MESSAGE

    CURRENT_ACTIVE_SESSION_ID = session_id or "default_user"

    if user_message:

        CURRENT_USER_MESSAGE = user_message



def find_product_in_inventory(kw: str, context_text: str = ""):

    """Tra cứu sản phẩm cực kỳ thông minh trong kho hàng (tiem_lap_do.db).

    Khớp mã SP, tên chính xác, tìm kiếm mở rộng, và so khớp tổ hợp từ lóng (F10 New 2.0 <-> F10 2.0 NEW).

    """

    if not os.path.exists(DB_BANHANG):

        return None

    try:

        conn = sqlite3.connect(DB_BANHANG, timeout=5)

        c = conn.cursor()

        c.execute("SELECT id, code, name, price, cost_price, stock, warranty_months FROM products")

        all_rows = c.fetchall()

        conn.close()

    except Exception:

        return None



    if not all_rows:

        return None



    kw_clean = kw.strip()

    if not kw_clean and not context_text:

        return None



    # 1. Khớp mã sản phẩm chính xác

    if kw_clean:

        for r in all_rows:

            if r[1].upper() == kw_clean.upper():

                return r



    # 2. Khớp chuỗi con trong tên

    if kw_clean:

        for r in all_rows:

            if kw_clean.lower() in r[2].lower():

                return r



    # 3. Sử dụng search_product_in_catalog của ai_assistant

    if kw_clean:

        try:

            from ai_assistant import search_product_in_catalog

            prods = search_product_in_catalog(kw_clean)

            if prods:

                tp = prods[0]

                for r in all_rows:

                    if r[0] == tp['id']:

                        return r

        except Exception:

            pass



    # 4. So khớp độ tương đồng tập từ (Token Overlap)

    def score_overlap(text, target):

        t_tokens = set(re.findall(r'[a-zA-Z0-9]+', text.lower()))

        r_tokens = set(re.findall(r'[a-zA-Z0-9]+', target.lower()))

        return len(t_tokens.intersection(r_tokens))



    best_r = None

    best_score = 0

    if kw_clean:

        for r in all_rows:

            sc = score_overlap(kw_clean, r[2])

            if sc > best_score:

                best_score = sc

                best_r = r



        if best_score >= 2:

            return best_r



    # 5. Thử tìm trên toàn bộ câu lệnh của người dùng nếu có

    if context_text and context_text != kw:

        try:

            from ai_assistant import search_product_in_catalog

            prods = search_product_in_catalog(context_text)

            if prods:

                tp = prods[0]

                for r in all_rows:

                    if r[0] == tp['id']:

                        return r

        except Exception:

            pass

        for r in all_rows:

            sc = score_overlap(context_text, r[2])

            if sc > best_score:

                best_score = sc

                best_r = r

        if best_score >= 2:

            return best_r



    return best_r if best_score >= 1 else None



def get_gemini_client():

    global GEMINI_CLIENT

    if GEMINI_CLIENT is None and GENAI_AVAILABLE:

        api_key = DEFAULT_API_KEY

        if api_key:

            GEMINI_CLIENT = genai.Client(api_key=api_key)

    return GEMINI_CLIENT



# ─────────────────────────────────────────────────────────────────────────────

# 1. BỘ CÔNG CỤ THAO TÁC CƠ SỞ DỮ LIỆU DÀNH CHO GEMINI (TOOLS / FUNCTIONS)

# ─────────────────────────────────────────────────────────────────────────────



def sua_don_hang(

    ma_don_hang: int,

    loai_don: str = "auto",

    ten_khach_moi: str = "",

    sdt_moi: str = "",

    bien_so_moi: str = "",

    dong_xe_moi: str = "",

    ten_san_pham_moi: str = "",

    gia_tien_moi: float = 0,

    ngay_moi: str = "",

    confirmed: bool = False

) -> str:

    """Chỉnh sửa thông tin đơn hàng đã có trong hệ thống (cả đơn Bán Hàng/Lắp Đồ và đơn Báo Cáo Doanh Thu Đèn).



    Args:

        ma_don_hang: Mã số đơn hàng cần sửa (ví dụ: 8585, 8114, 747, 728).

        loai_don: Phân hệ đơn hàng ('auto' để tự động tìm, hoặc 'banhang', 'den').

        ten_khach_moi: Tên khách hàng mới (nếu muốn đổi).

        sdt_moi: Số điện thoại mới của khách (nếu muốn đổi).

        bien_so_moi: Biển số xe mới (nếu muốn đổi).

        dong_xe_moi: Dòng xe mới (nếu muốn đổi).

        ten_san_pham_moi: Tên sản phẩm / đèn mới (nếu muốn đổi món hàng).

        gia_tien_moi: Giá tiền / tổng tiền mới (VNĐ cho bán hàng, hoặc nghìn đồng nếu là đơn đèn).

        ngay_moi: Ngày lắp đặt hoặc ngày ghi nhận mới (định dạng YYYY-MM-DD).

        confirmed: Cờ xác nhận người dùng đã đồng ý thực thi sửa đổi.

    """

    updated_info = []



    # 1. Thử tìm và sửa trong Báo Cáo Doanh Thu Đèn

    if loai_don in ("auto", "den") and os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        c.execute("SELECT id, order_date, product_name, customer_name, car_model, quantity, price_k FROM orders WHERE id=?", (ma_don_hang,))

        row = c.fetchone()

        if row:

            fields_to_update = []

            vals = []

            if ten_khach_moi:

                fields_to_update.append("customer_name=?")

                vals.append(ten_khach_moi.strip())

                updated_info.append(f"Khách hàng: **{row[3]}** ➔ **{ten_khach_moi}**")

            if dong_xe_moi:

                fields_to_update.append("car_model=?")

                vals.append(dong_xe_moi.strip().upper())

                updated_info.append(f"Dòng xe: **{row[4]}** ➔ **{dong_xe_moi.upper()}**")

            if ten_san_pham_moi:

                fields_to_update.append("product_name=?")

                vals.append(ten_san_pham_moi.strip().upper())

                updated_info.append(f"Tên đèn/sản phẩm: **{row[2]}** ➔ **{ten_san_pham_moi.upper()}**")

            if gia_tien_moi > 0:

                p_k = int(gia_tien_moi / 1000) if gia_tien_moi > 50000 else int(gia_tien_moi)

                fields_to_update.append("price_k=?")

                vals.append(p_k)

                updated_info.append(f"Đơn giá đèn: **{row[6]:,}k** ➔ **{p_k:,}k** ({p_k * 1000:,} đ)")

            if ngay_moi:

                clean_ngay = ngay_moi.strip()

                try:

                    from ai_assistant import extract_date

                    d_p, _ = extract_date(ngay_moi)

                    if d_p:

                        clean_ngay = d_p

                except Exception:

                    pass

                fields_to_update.append("order_date=?")

                vals.append(clean_ngay)

                updated_info.append(f"Ngày ghi nhận: **{row[1]}** ➔ **{clean_ngay}**")



            if fields_to_update:

                if not confirmed:

                    conn.close()

                    try:

                        from ai_assistant import WIZARD_SESSIONS

                        WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                            'flow': 'confirm_action',

                            'action_type': 'admin_edit_order',

                            'payload': {

                                'kwargs': {

                                    'ma_don_hang': ma_don_hang,

                                    'loai_don': 'den',

                                    'ten_khach_moi': ten_khach_moi,

                                    'sdt_moi': sdt_moi,

                                    'bien_so_moi': bien_so_moi,

                                    'dong_xe_moi': dong_xe_moi,

                                    'ten_san_pham_moi': ten_san_pham_moi,

                                    'gia_tien_moi': gia_tien_moi,

                                    'ngay_moi': ngay_moi,

                                    'confirmed': True

                                },

                                'original_prompt': CURRENT_USER_MESSAGE

                            }

                        }

                    except Exception as e:

                        print(f"[GeminiEngine] Lỗi đăng ký confirm sửa đơn đèn: {e}")



                    return (

                        f"❓ **XÁC NHẬN SỬA ĐƠN BÁO CÁO ĐÈN #{ma_don_hang}:**\n"

                        f"─────────────────────────────────────────\n"

                        f"• 📋 **Đơn gốc:** {row[3]} - {row[4]} (Đèn: {row[2]})\n"

                        + "\n".join([f"• {u}" for u in updated_info]) + "\n"

                        f"─────────────────────────────────────────\n"

                        f"👉 Anh có chắc chắn muốn lưu thông tin sửa đổi này vào đơn hàng không?\n\n"

                        f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'**, **'lưu'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"

                    )



                vals.append(ma_don_hang)

                c.execute(f"UPDATE orders SET {', '.join(fields_to_update)} WHERE id=?", vals)

                conn.commit()

                conn.close()

                return (

                    f"✅ **ĐÃ CẬP NHẬT THÀNH CÔNG ĐƠN BÁO CÁO ĐÈN #{ma_don_hang}!**\n"

                    f"─────────────────────────────────────────\n"

                    + "\n".join([f"• {u}" for u in updated_info]) +

                    f"\n👉 Dữ liệu đã đồng bộ tức thì vào phần mềm Báo Cáo Doanh Thu Đèn."

                )

            conn.close()



    # 2. Thử tìm và sửa trong Bán Hàng & Lắp Đồ

    if loai_don in ("auto", "banhang") and os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        c.execute("SELECT id, customer_name, phone, license_plate, install_date, total_price FROM orders WHERE id=?", (ma_don_hang,))

        row = c.fetchone()

        if row:

            fields_to_update = []

            vals = []

            if ten_khach_moi:

                fields_to_update.append("customer_name=?")

                vals.append(ten_khach_moi.strip().upper())

                updated_info.append(f"Tên khách hàng: **{row[1]}** ➔ **{ten_khach_moi.upper()}**")

            if sdt_moi:

                clean_phone = re.sub(r'[^0-9]', '', sdt_moi)

                fields_to_update.append("phone=?")

                vals.append(clean_phone)

                updated_info.append(f"Số điện thoại: **{row[2]}** ➔ **{clean_phone}**")

            if bien_so_moi:

                clean_plate = bien_so_moi.strip().upper()

                fields_to_update.append("license_plate=?")

                vals.append(clean_plate)

                updated_info.append(f"Biển số xe: **{row[3]}** ➔ **{clean_plate}**")

            if ngay_moi:

                clean_ngay = ngay_moi.strip()

                try:

                    from ai_assistant import extract_date

                    d_p, _ = extract_date(ngay_moi)

                    if d_p:

                        clean_ngay = d_p

                except Exception:

                    pass

                fields_to_update.append("install_date=?")

                vals.append(clean_ngay)

                updated_info.append(f"Ngày lắp đặt: **{row[4]}** ➔ **{clean_ngay}**")

            if gia_tien_moi > 0:

                p_val = gia_tien_moi if gia_tien_moi > 10000 else gia_tien_moi * 1000

                fields_to_update.append("total_price=?")

                vals.append(p_val)

                updated_info.append(f"Tổng tiền đơn hàng: **{row[5]:,.0f} đ** ➔ **{p_val:,.0f} đ**")



            if ten_san_pham_moi:

                updated_info.append(f"Đổi sản phẩm sang: **{ten_san_pham_moi}**")



            if fields_to_update or ten_san_pham_moi:

                if not confirmed:

                    conn.close()

                    try:

                        from ai_assistant import WIZARD_SESSIONS

                        WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                            'flow': 'confirm_action',

                            'action_type': 'admin_edit_order',

                            'payload': {

                                'kwargs': {

                                    'ma_don_hang': ma_don_hang,

                                    'loai_don': 'banhang',

                                    'ten_khach_moi': ten_khach_moi,

                                    'sdt_moi': sdt_moi,

                                    'bien_so_moi': bien_so_moi,

                                    'dong_xe_moi': dong_xe_moi,

                                    'ten_san_pham_moi': ten_san_pham_moi,

                                    'gia_tien_moi': gia_tien_moi,

                                    'ngay_moi': ngay_moi,

                                    'confirmed': True

                                },

                                'original_prompt': CURRENT_USER_MESSAGE

                            }

                        }

                    except Exception as e:

                        print(f"[GeminiEngine] Lỗi đăng ký confirm sửa đơn bán hàng: {e}")



                    return (

                        f"❓ **XÁC NHẬN SỬA ĐƠN BÁN HÀNG #{ma_don_hang}:**\n"

                        f"─────────────────────────────────────────\n"

                        f"• 📋 **Đơn gốc:** {row[1]} - Biển số: {row[3]} ({row[4]})\n"

                        + "\n".join([f"• {u}" for u in updated_info]) + "\n"

                        f"─────────────────────────────────────────\n"

                        f"👉 Anh có chắc chắn muốn lưu thông tin sửa đổi này vào đơn hàng không?\n\n"

                        f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'**, **'lưu'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"

                    )



                if ten_san_pham_moi:

                    c.execute("UPDATE order_items SET item_name=? WHERE order_id=?", (ten_san_pham_moi.strip(), ma_don_hang))

                if fields_to_update:

                    vals.append(ma_don_hang)

                    c.execute(f"UPDATE orders SET {', '.join(fields_to_update)} WHERE id=?", vals)

                conn.commit()

                conn.close()

                return (

                    f"✅ **ĐÃ CẬP NHẬT THÀNH CÔNG ĐƠN BÁN HÀNG #{ma_don_hang}!**\n"

                    f"─────────────────────────────────────────\n"

                    + "\n".join([f"• {u}" for u in updated_info]) +

                    f"\n👉 Dữ liệu đã đồng bộ tức thì vào phần mềm Bán Hàng & Lắp Đồ."

                )

            conn.close()



    return f"⚠️ Không tìm thấy đơn hàng mã #{ma_don_hang} trong hệ thống Bán Hàng hoặc Báo Cáo Đèn. Bạn kiểm tra lại mã đơn giúp em nhé!"





def xoa_don_hang(ma_don_hang: int, loai_don: str = "auto", confirmed: bool = False) -> str:

    """Xóa hoặc hủy một đơn hàng khỏi hệ thống (cả Bán Hàng và Báo Cáo Đèn).



    Args:

        ma_don_hang: Mã số đơn hàng cần xóa (ví dụ: 747, 8585).

        loai_don: 'auto', 'den' hoặc 'banhang'.

        confirmed: Cờ xác nhận người dùng đã đồng ý xóa.

    """

    # 1. Thử xóa bên Báo Cáo Đèn

    if loai_don in ("auto", "den") and os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        c.execute("SELECT id, product_name, customer_name, car_model, price_k, order_date FROM orders WHERE id=?", (ma_don_hang,))

        row = c.fetchone()

        if row:

            if not confirmed:

                conn.close()

                try:

                    from ai_assistant import WIZARD_SESSIONS

                    WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                        'flow': 'confirm_action',

                        'action_type': 'admin_delete_order',

                        'payload': {

                            'order_id': ma_don_hang,

                            'loai_don': 'den',

                            'confirmed': True,

                            'original_prompt': CURRENT_USER_MESSAGE

                        }

                    }

                except Exception as e:

                    print(f"[GeminiEngine] Lỗi đăng ký confirm xóa đơn đèn: {e}")



                return (

                    f"⚠️ **XÁC NHẬN XÓA ĐƠN BÁO CÁO ĐÈN #{ma_don_hang}:**\n"

                    f"─────────────────────────────────────────\n"

                    f"• 📋 **Phân hệ:** Báo Cáo Doanh Thu Đèn\n"

                    f"• 💡 **Sản phẩm:** {row[1]} ({row[4]}k)\n"

                    f"• 👤 **Khách hàng:** {row[2]} ({row[3]})\n"

                    f"• 📅 **Ngày lắp:** {row[5]}\n"

                    f"─────────────────────────────────────────\n"

                    f"🚨 **CẢNH BÁO BẢO TOÀN DỮ LIỆU:** Thao tác này sẽ gỡ bỏ đơn hàng vĩnh viễn khỏi sổ sách!\n\n"

                    f"👉 Anh có chắc chắn muốn XÓA đơn hàng này không?\n\n"

                    f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để xóa | Bấm **[🛑 Hủy]** để giữ lại đơn)*"

                )



            c.execute("DELETE FROM orders WHERE id=?", (ma_don_hang,))

            conn.commit()

            conn.close()

            return f"🗑️ **ĐÃ XÓA THÀNH CÔNG ĐƠN ĐÈN #{ma_don_hang}!**\n• Món: {row[1]} ({row[4]}k)\n• Khách: {row[2]} ({row[3]})\n👉 Đơn hàng đã được gỡ bỏ khỏi Sổ Doanh Thu Đèn."

        conn.close()



    # 2. Thử xóa bên Bán Hàng

    if loai_don in ("auto", "banhang") and os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        c.execute("SELECT id, customer_name, license_plate, total_price, install_date FROM orders WHERE id=?", (ma_don_hang,))

        row = c.fetchone()

        if row:

            if not confirmed:

                conn.close()

                try:

                    from ai_assistant import WIZARD_SESSIONS

                    WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                        'flow': 'confirm_action',

                        'action_type': 'admin_delete_order',

                        'payload': {

                            'order_id': ma_don_hang,

                            'loai_don': 'banhang',

                            'confirmed': True,

                            'original_prompt': CURRENT_USER_MESSAGE

                        }

                    }

                except Exception as e:

                    print(f"[GeminiEngine] Lỗi đăng ký confirm xóa đơn bán hàng: {e}")



                return (

                    f"⚠️ **XÁC NHẬN XÓA ĐƠN BÁN HÀNG #{ma_don_hang}:**\n"

                    f"─────────────────────────────────────────\n"

                    f"• 📋 **Phân hệ:** Bán Hàng & Lắp Đồ Phụ Kiện\n"

                    f"• 👤 **Khách hàng:** {row[1]} - Biển số: {row[2]}\n"

                    f"• 💰 **Tổng tiền:** {row[3]:,.0f} đ\n"

                    f"• 📅 **Ngày lắp:** {row[4]}\n"

                    f"─────────────────────────────────────────\n"

                    f"🚨 **CẢNH BÁO BẢO TOÀN DỮ LIỆU:** Thao tác này sẽ gỡ bỏ đơn hàng vĩnh viễn khỏi hệ thống bán hàng!\n\n"

                    f"👉 Anh có chắc chắn muốn XÓA đơn hàng này không?\n\n"

                    f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để xóa | Bấm **[🛑 Hủy]** để giữ lại đơn)*"

                )



            c.execute("DELETE FROM order_items WHERE order_id=?", (ma_don_hang,))

            c.execute("DELETE FROM orders WHERE id=?", (ma_don_hang,))

            conn.commit()

            conn.close()

            return f"🗑️ **ĐÃ XÓA THÀNH CÔNG ĐƠN BÁN HÀNG #{ma_don_hang}!**\n• Khách: {row[1]} - Biển số: {row[2]}\n• Tổng tiền: {row[3]:,.0f} đ\n👉 Đơn hàng và các món phụ kiện đã được gỡ hoàn toàn."

        conn.close()



    return f"⚠️ Không tìm thấy đơn hàng mã #{ma_don_hang} để xóa. Bạn kiểm tra lại mã giúp em nhé!"





def cap_nhat_kho_hang(

    ma_hoac_ten_sp: str,

    ton_kho_moi: int = -999,

    gia_ban_moi: float = 0,

    gia_von_moi: float = 0,

    thoi_han_bao_hanh_thang: int = -999,

    confirmed: bool = False

) -> str:

    """Cập nhật số lượng tồn kho, giá bán, giá vốn hoặc thời hạn bảo hành của sản phẩm trong kho.



    Args:

        ma_hoac_ten_sp: Mã sản phẩm (ví dụ: 'SP2734853', 'A310') hoặc tên sản phẩm.

        ton_kho_moi: Số lượng tồn kho mới (nếu muốn điều chỉnh tồn kho).

        gia_ban_moi: Giá bán lẻ mới (VNĐ).

        gia_von_moi: Giá vốn nhập vào mới (VNĐ).

        thoi_han_bao_hanh_thang: Thời gian bảo hành tính theo tháng (ví dụ: 12, 24).

        confirmed: Cờ xác nhận người dùng đã đồng ý thực thi sửa đổi kho.

    """

    if not os.path.exists(DB_BANHANG):

        return "⚠️ Không tìm thấy cơ sở dữ liệu kho hàng."



    conn = sqlite3.connect(DB_BANHANG)

    c = conn.cursor()



    kw = ma_hoac_ten_sp.strip()

    target_prod = find_product_in_inventory(kw, CURRENT_USER_MESSAGE)

    if not target_prod:

        return f"⚠️ Không tìm thấy sản phẩm nào khớp với từ khóa **'{kw}'** trong kho hàng."



    prod_id, code, name, old_price, old_cost, old_stock, old_warranty = target_prod



    fields = []

    vals = []

    changes = []



    if ton_kho_moi != -999:

        fields.append("stock=?")

        vals.append(ton_kho_moi)

        changes.append(f"Tồn kho: từ **{old_stock}** ➔ **{ton_kho_moi}**")



    if gia_ban_moi > 0:

        p_val = gia_ban_moi if gia_ban_moi > 10000 else gia_ban_moi * 1000

        fields.append("price=?")

        vals.append(p_val)

        changes.append(f"Giá bán: từ **{old_price:,.0f} đ** ➔ **{p_val:,.0f} đ**")



    if gia_von_moi > 0:

        c_val = gia_von_moi if gia_von_moi > 10000 else gia_von_moi * 1000

        fields.append("cost_price=?")

        vals.append(c_val)

        changes.append(f"Giá vốn: từ **{old_cost:,.0f} đ** ➔ **{c_val:,.0f} đ**")



    if thoi_han_bao_hanh_thang != -999:

        fields.append("warranty_months=?")

        vals.append(thoi_han_bao_hanh_thang)

        changes.append(f"Bảo hành: từ **{old_warranty} tháng** ➔ **{thoi_han_bao_hanh_thang} tháng**")



    if not fields:

        conn.close()

        return f"📦 **THÔNG TIN SẢN PHẨM HIỆN TẠI:**\n• Mã: **{code}** | Tên: **{name}**\n• Tồn kho: **{old_stock}**\n• Giá bán: **{old_price:,.0f} đ** | Giá vốn: **{old_cost:,.0f} đ**\n• Bảo hành: **{old_warranty} tháng**\n👉 Bạn muốn cập nhật số lượng tồn kho hay điều chỉnh giá bán nào ạ?"



    if not confirmed:

        conn.close()

        try:

            from ai_assistant import WIZARD_SESSIONS

            WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                'flow': 'confirm_action',

                'action_type': 'admin_update_stock',

                'payload': {

                    'code': code,

                    'name': name,

                    'new_price': gia_ban_moi,

                    'raw_product_kw': ma_hoac_ten_sp,

                    'kwargs': {

                        'ma_hoac_ten_sp': code,

                        'ton_kho_moi': ton_kho_moi,

                        'gia_ban_moi': gia_ban_moi,

                        'gia_von_moi': gia_von_moi,

                        'thoi_han_bao_hanh_thang': thoi_han_bao_hanh_thang,

                        'confirmed': True

                    },

                    'original_prompt': CURRENT_USER_MESSAGE

                }

            }

        except Exception as e:

            print(f"[GeminiEngine] Lỗi đăng ký confirm kho: {e}")



        return (

            f"❓ **XÁC NHẬN CẬP NHẬT DỮ LIỆU KHO HÀNG:**\n"

            f"─────────────────────────────────────────\n"

            f"• 📦 **Sản phẩm:** **{name}** (Mã: `{code}`)\n"

            + "\n".join([f"• {ch}" for ch in changes]) + "\n"

            f"• 📊 **Tồn kho hiện tại:** {old_stock} | **Bảo hành:** {old_warranty} tháng\n"

            f"─────────────────────────────────────────\n"

            f"👉 Anh có chắc chắn muốn lưu các thay đổi này vào phần mềm Bán Hàng không?\n\n"

            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'**, **'lưu'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"

        )



    vals.append(prod_id)

    c.execute(f"UPDATE products SET {', '.join(fields)} WHERE id=?", vals)

    conn.commit()

    conn.close()



    return (

        f"📦 **ĐÃ CẬP NHẬT KHO HÀNG THÀNH CÔNG!**\n"

        f"─────────────────────────────────────────\n"

        f"• Sản phẩm: **{name}** (Mã: `{code}`)\n"

        + "\n".join([f"• {ch}" for ch in changes]) +

        f"\n👉 Tồn kho & giá mới đã được áp dụng ngay trên toàn hệ thống."

    )





def cap_nhat_thong_tin_khach_hang(

    dinh_danh_cu: str,

    ten_moi: str = "",

    sdt_moi: str = "",

    bien_so_moi: str = "",

    confirmed: bool = False

) -> str:

    """Cập nhật thông tin khách hàng (Tên, Số điện thoại, Biển số xe) đồng bộ trên tất cả đơn hàng đã lưu.



    Args:

        dinh_danh_cu: Biển số xe cũ (ví dụ '63A-187.30'), Số điện thoại cũ (ví dụ '0906648540'), hoặc Tên khách cũ.

        ten_moi: Tên mới cần đổi.

        sdt_moi: Số điện thoại mới cần đổi.

        bien_so_moi: Biển số xe mới cần đổi.

        confirmed: Cờ xác nhận người dùng đã đồng ý.

    """

    kw = dinh_danh_cu.strip().upper()

    total_updated = 0



    # Kiểm tra số lượng đơn khớp trước

    matches_bh = 0

    if os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM orders WHERE UPPER(license_plate) LIKE ? OR phone LIKE ? OR UPPER(customer_name) LIKE ?", (f"%{kw}%", f"%{kw}%", f"%{kw}%"))

        matches_bh = c.fetchone()[0] or 0

        conn.close()



    matches_den = 0

    if os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM orders WHERE UPPER(customer_name) LIKE ?", (f"%{kw}%",))

        matches_den = c.fetchone()[0] or 0

        conn.close()



    total_matches = matches_bh + matches_den

    if total_matches == 0:

        return f"⚠️ Không tìm thấy khách hàng nào khớp với định danh **'{dinh_danh_cu}'** để cập nhật."



    changes = []

    if ten_moi: changes.append(f"Tên khách mới: **{ten_moi.upper()}**")

    if sdt_moi: changes.append(f"Số điện thoại mới: **{sdt_moi}**")

    if bien_so_moi: changes.append(f"Biển số xe mới: **{bien_so_moi.upper()}**")



    if not confirmed:

        try:

            from ai_assistant import WIZARD_SESSIONS

            WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                'flow': 'confirm_action',

                'action_type': 'admin_update_customer',

                'payload': {

                    'kwargs': {

                        'dinh_danh_cu': dinh_danh_cu,

                        'ten_moi': ten_moi,

                        'sdt_moi': sdt_moi,

                        'bien_so_moi': bien_so_moi,

                        'confirmed': True

                    },

                    'original_prompt': CURRENT_USER_MESSAGE

                }

            }

        except Exception as e:

            print(f"[GeminiEngine] Lỗi đăng ký confirm khách: {e}")



        return (

            f"❓ **XÁC NHẬN ĐỒNG BỘ THÔNG TIN KHÁCH HÀNG ({total_matches} đơn liên quan):**\n"

            f"─────────────────────────────────────────\n"

            f"• 🔍 **Hồ sơ tìm thấy:** `{dinh_danh_cu}` ({total_matches} đơn hàng)\n"

            + "\n".join([f"• {ch}" for ch in changes]) + "\n"

            f"─────────────────────────────────────────\n"

            f"👉 Anh có chắc chắn muốn cập nhật đồng bộ cho {total_matches} đơn hàng này không?\n\n"

            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để cập nhật | Bấm **[🛑 Hủy]** để bỏ qua)*"

        )



    # 1. Cập nhật trong Bán Hàng

    if os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        c.execute("""

            SELECT id, customer_name, phone, license_plate 

            FROM orders 

            WHERE UPPER(license_plate) LIKE ? OR phone LIKE ? OR UPPER(customer_name) LIKE ?

        """, (f"%{kw}%", f"%{kw}%", f"%{kw}%"))

        rows = c.fetchall()



        for r in rows:

            o_id = r[0]

            fields = []

            vals = []

            if ten_moi:

                fields.append("customer_name=?")

                vals.append(ten_moi.strip().upper())

            if sdt_moi:

                fields.append("phone=?")

                vals.append(re.sub(r'[^0-9]', '', sdt_moi))

            if bien_so_moi:

                fields.append("license_plate=?")

                vals.append(bien_so_moi.strip().upper())

            if fields:

                vals.append(o_id)

                c.execute(f"UPDATE orders SET {', '.join(fields)} WHERE id=?", vals)

                total_updated += 1

        conn.commit()

        conn.close()



    # 2. Cập nhật trong Báo Cáo Đèn

    if os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        c.execute("SELECT id, customer_name FROM orders WHERE UPPER(customer_name) LIKE ?", (f"%{kw}%",))

        rows_den = c.fetchall()

        if ten_moi:

            for r in rows_den:

                c.execute("UPDATE orders SET customer_name=? WHERE id=?", (ten_moi.strip(), r[0]))

                total_updated += 1

        conn.commit()

        conn.close()



    return (

        f"👤 **ĐÃ CẬP NHẬT THÔNG TIN KHÁCH HÀNG THÀNH CÔNG!**\n"

        f"─────────────────────────────────────────\n"

        f"• Số đơn hàng đồng bộ: **{total_updated} đơn**\n"

        + "\n".join([f"• {ch}" for ch in changes]) +

        f"\n👉 Toàn bộ lịch sử bảo hành và doanh thu đã được liên kết đồng nhất."

    )

    if ten_moi: changes.append(f"Tên khách: **{ten_moi.upper()}**")

    if sdt_moi: changes.append(f"Số điện thoại: **{sdt_moi}**")

    if bien_so_moi: changes.append(f"Biển số xe: **{bien_so_moi.upper()}**")



    return (

        f"👤 **ĐÃ CẬP NHẬT THÔNG TIN KHÁCH HÀNG THÀNH CÔNG!**\n"

        f"─────────────────────────────────────────\n"

        f"• Định danh gốc: `{dinh_danh_cu}`\n"

        + "\n".join([f"• {ch}" for ch in changes]) +

        f"\n• Tổng số đơn hàng đã đồng bộ dữ liệu: **{total_updated} đơn**\n"

        f"👉 Lịch sử bảo hành và thông tin khách hàng đã được làm mới chuẩn xác."

    )





def tra_cuu_khach_hang_va_bao_hanh(tu_khoa: str) -> str:

    """Tra cứu bảo hành, lịch sử lắp đặt phụ kiện, dòng xe của khách hàng theo Biển số xe, SĐT hoặc Tên khách kèm dòng xe.



    Args:

        tu_khoa: Biển số xe (ví dụ '63A-187.30', '18730'), Số điện thoại, hoặc Tên khách + Dòng xe (ví dụ 'Toàn Soluto', 'Toàn Vios').

    """

    kw = tu_khoa.strip().upper()

    results = []



    # 1. Tra trong Bán Hàng & Lắp Đồ

    if os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        c.execute("""

            SELECT o.id, o.customer_name, o.phone, o.license_plate, o.install_date, o.total_price,

                   GROUP_CONCAT(i.item_name || ' (BH ' || i.warranty_months || 'T)', '; ')

            FROM orders o

            LEFT JOIN order_items i ON o.id = i.order_id

            WHERE UPPER(o.license_plate) LIKE ? OR o.phone LIKE ? OR UPPER(o.customer_name) LIKE ?

            GROUP BY o.id

            ORDER BY o.install_date DESC LIMIT 5

        """, (f"%{kw}%", f"%{kw}%", f"%{kw}%"))

        rows = c.fetchall()

        for r in rows:

            results.append({

                "module": "Bán Hàng / Lắp Đồ",

                "id": r[0],

                "name": r[1],

                "phone": r[2],

                "plate": r[3],

                "date": r[4],

                "total": f"{r[5]:,.0f} đ" if r[5] else "0 đ",

                "items": r[6] or "Không có chi tiết món"

            })

        conn.close()



    # 2. Tra trong Báo Cáo Doanh Thu Đèn

    if os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        c.execute("""

            SELECT id, order_date, product_name, customer_name, car_model, quantity, price_k

            FROM orders

            WHERE UPPER(customer_name) LIKE ? OR UPPER(car_model) LIKE ?

            ORDER BY order_date DESC LIMIT 5

        """, (f"%{kw}%", f"%{kw}%"))

        for r in c.fetchall():

            results.append({

                "module": "Báo Cáo Đèn",

                "id": r[0],

                "name": r[3],

                "phone": "Theo hồ sơ đèn",

                "plate": r[4] or "Xe chưa ghi biển",

                "date": r[1],

                "total": f"{r[6]:,}k ({r[6] * 1000:,} đ)",

                "items": f"Đèn {r[2]} (SL: {r[5]})"

            })

        conn.close()



    if not results:

        return f"🔍 Không tìm thấy thông tin bảo hành hay đơn hàng nào khớp với từ khóa **'{tu_khoa}'**."



    res_str = f"🔍 **KẾT QUẢ TRA CỨU HỒ SƠ & BẢO HÀNH CHO '{tu_khoa}':**\n"

    res_str += "─────────────────────────────────────────\n"

    for idx, r in enumerate(results, 1):

        res_str += (

            f"**{idx}. [{r['module']}] Đơn #{r['id']}**\n"

            f"  • Khách hàng: **{r['name']}**\n"

            f"  • Biển số / Xe: **{r['plate']}** | SĐT: **{r['phone']}**\n"

            f"  • Ngày lắp: **{r['date']}** | Tổng tiền: **{r['total']}**\n"

            f"  • Phụ kiện: {r['items']}\n\n"

        )

    return res_str.strip()





def tra_cuu_san_pham_kho_hang(tu_khoa: str) -> str:

    """Tra cứu tồn kho, giá bán lẻ, giá vốn, hạn bảo hành của sản phẩm, camera, phụ kiện, màn hình, đèn.



    Args:

        tu_khoa: Tên sản phẩm, mã sản phẩm hoặc dòng sản phẩm (ví dụ 'A310', 'Vietmap M1', 'F10', 'Ceramax').

    """

    if not os.path.exists(DB_BANHANG):

        return "⚠️ Không tìm thấy cơ sở dữ liệu kho hàng."



    conn = sqlite3.connect(DB_BANHANG)

    c = conn.cursor()

    kw = tu_khoa.strip().upper()

    c.execute("""

        SELECT code, name, category, price, cost_price, stock, warranty_months

        FROM products

        WHERE UPPER(code) LIKE ? OR UPPER(name) LIKE ? OR UPPER(category) LIKE ?

        ORDER BY stock DESC LIMIT 6

    """, (f"%{kw}%", f"%{kw}%", f"%{kw}%"))

    rows = c.fetchall()

    conn.close()



    if not rows:

        tp = find_product_in_inventory(tu_khoa, CURRENT_USER_MESSAGE)

        if tp:

            rows = [(tp[1], tp[2], '', tp[3], tp[4], tp[5], tp[6])]



    if not rows:

        return f"📦 Không tìm thấy sản phẩm nào khớp với **'{tu_khoa}'** trong kho."



    res = f"📦 **THÔNG TIN SẢN PHẨM & TỒN KHO CHO '{tu_khoa}':**\n"

    res += "─────────────────────────────────────────\n"

    for r in rows:

        res += (

            f"• **{r[1]}** (Mã: `{r[0]}`)\n"

            f"  - Tồn kho: **{r[5]}** | Bảo hành: **{r[6]} tháng**\n"

            f"  - Giá bán: **{r[3]:,.0f} đ** | Giá vốn: **{r[4]:,.0f} đ**\n"

        )

    return res.strip()





def thong_ke_doanh_thu(

    loai_thong_ke: str = "tat_ca",

    thang: int = 0,

    nam: int = 0,

    ngay_cu_the: str = ""

) -> str:

    """Báo cáo thống kê doanh thu toàn gara, doanh thu bán hàng, doanh thu đèn chu kỳ 9-8, và tình hình thu chi tài chính.



    Args:

        loai_thong_ke: 'tat_ca', 'den', 'banhang', hoặc 'thuchi'.

        thang: Tháng cần thống kê (1-12). Nếu không có, tính kỳ/tháng hiện tại.

        nam: Năm cần thống kê (ví dụ 2026, 2025). Nếu không truyền, mặc định năm hiện tại.

        ngay_cu_the: Ngày cụ thể YYYY-MM-DD (nếu muốn xem hôm nay hoặc ngày bất kỳ).

    """

    try:

        thang = int(thang) if (thang and str(thang).isdigit()) else 0

    except Exception:

        thang = 0

    try:

        nam = int(nam) if (nam and str(nam).isdigit()) else 0

    except Exception:

        nam = 0



    now = datetime.now()

    cur_year = nam if nam > 0 else now.year



    total_den_rev = 0

    total_den_qty = 0

    den_orders_count = 0



    if os.path.exists(DB_DEN):

        conn = sqlite3.connect(DB_DEN)

        c = conn.cursor()

        if ngay_cu_the:

            c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k) FROM orders WHERE order_date=?", (ngay_cu_the,))

        elif thang > 0:

            prev_m = 12 if thang == 1 else thang - 1

            prev_y = cur_year - 1 if thang == 1 else cur_year

            d_start = f"{prev_y:04d}-{prev_m:02d}-09"

            d_end = f"{cur_year:04d}-{thang:02d}-08"

            c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k) FROM orders WHERE order_date >= ? AND order_date <= ?", (d_start, d_end))

        else:

            c.execute("SELECT COUNT(*), SUM(quantity), SUM(price_k) FROM orders")



        row = c.fetchone()

        if row and row[0]:

            den_orders_count = row[0] or 0

            total_den_qty = row[1] or 0

            total_den_rev = (row[2] or 0) * 1000

        conn.close()



    total_bh_rev = 0

    bh_orders_count = 0



    if os.path.exists(DB_BANHANG):

        conn = sqlite3.connect(DB_BANHANG)

        c = conn.cursor()

        if ngay_cu_the:

            c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date=?", (ngay_cu_the,))

        elif thang > 0:

            m_str = f"{cur_year:04d}-{thang:02d}%"

            c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE install_date LIKE ?", (m_str,))

        else:

            c.execute("SELECT COUNT(*), SUM(total_price) FROM orders")

        row = c.fetchone()

        if row and row[0]:

            bh_orders_count = row[0] or 0

            total_bh_rev = row[1] or 0

        conn.close()



    total_chi = 0

    total_thu = 0

    if os.path.exists(DB_THUCHI):

        conn = sqlite3.connect(DB_THUCHI)

        c = conn.cursor()

        if ngay_cu_the:

            c.execute("SELECT type, SUM(amount) FROM transactions WHERE created_at LIKE ? GROUP BY type", (f"{ngay_cu_the}%",))

        elif thang > 0:

            m_str = f"{cur_year:04d}-{thang:02d}%"

            c.execute("SELECT type, SUM(amount) FROM transactions WHERE created_at LIKE ? GROUP BY type", (m_str,))

        else:

            c.execute("SELECT type, SUM(amount) FROM transactions GROUP BY type")

        for t_type, amt in c.fetchall():

            if t_type == 'chi': total_chi = amt or 0

            elif t_type == 'thu': total_thu = amt or 0

        conn.close()



    time_label = f"ngày {ngay_cu_the}" if ngay_cu_the else (f"Tháng {thang}/{cur_year}" if thang > 0 else f"Năm {cur_year}")

    res = f"📊 **BÁO CÁO TÀI CHÍNH & DOANH THU GARA ({time_label.upper()}):**\n"

    res += "─────────────────────────────────────────\n"

    res += f"💡 **Doanh thu Báo Cáo Đèn (Chu kỳ 9-8):** **{total_den_rev:,.0f} đ** ({den_orders_count} đơn, {total_den_qty} bộ đèn)\n"

    res += f"📦 **Doanh thu Bán Hàng & Lắp Đồ:** **{total_bh_rev:,.0f} đ** ({bh_orders_count} đơn)\n"

    res += f"💵 **Tổng chi phí xuất quỹ:** **{total_chi:,.0f} đ**\n"

    res += f"💰 **Tổng thu vào sổ quỹ:** **{total_thu:,.0f} đ**\n"

    res += f"⭐ **TỔNG DOANH THU TOÀN GARA:** **{total_den_rev + total_bh_rev:,.0f} đ**"

    return res





def ghi_so_thu_chi(

    loai: str,

    so_tien: int,

    noi_dung: str,

    ngay: str = "",

    confirmed: bool = False

) -> str:

    """Ghi nhanh khoản chi hoặc thu vào sổ quỹ tài chính.



    Args:

        loai: 'chi' hoặc 'thu'.

        so_tien: Số tiền VNĐ (ví dụ 100000, 350000).

        noi_dung: Lý do hoặc nội dung chi/thu (ví dụ 'mua đồ ăn trưa', 'mua băng keo', 'khách tip').

        ngay: Ngày phát sinh (YYYY-MM-DD), nếu để trống lấy ngày hôm nay.

        confirmed: Cờ xác nhận người dùng đã đồng ý ghi sổ.

    """

    if not os.path.exists(DB_THUCHI):

        return "⚠️ Không tìm thấy cơ sở dữ liệu sổ thu chi."



    final_date = ""

    if ngay:

        if re.match(r'^\d{4}-\d{2}-\d{2}$', ngay.strip()):

            final_date = ngay.strip()

        else:

            try:

                from ai_assistant import extract_date

                d_p, _ = extract_date(ngay)

                if d_p:

                    final_date = d_p

            except Exception:

                pass



    if not final_date and CURRENT_USER_MESSAGE:

        try:

            from ai_assistant import extract_date

            d_p, _ = extract_date(CURRENT_USER_MESSAGE)

            if d_p:

                final_date = d_p

        except Exception:

            pass



    if not final_date:

        final_date = datetime.now().strftime("%Y-%m-%d")



    now_date = final_date

    clean_type = 'chi' if 'chi' in loai.lower() else 'thu'



    if not confirmed:

        try:

            from ai_assistant import WIZARD_SESSIONS

            WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                'flow': 'confirm_action',

                'action_type': 'thuchi',

                'payload': {

                    'trans_type': clean_type,

                    'amount': so_tien,

                    'note': noi_dung,

                    'date_str': now_date,

                    'original_prompt': CURRENT_USER_MESSAGE

                }

            }

        except Exception as e:

            print(f"[GeminiEngine] Lỗi đăng ký confirm thu chi: {e}")



        amount_k_str = f"{so_tien//1000:,}k" if so_tien >= 1000 else f"{so_tien:,}đ"

        type_label = "KHOẢN CHI TIỀN" if clean_type == 'chi' else "KHOẢN THU TIỀN"

        type_icon = "💸" if clean_type == 'chi' else "💵"

        return (

            f"❓ **XÁC NHẬN GHI SỔ THU CHI ({type_label}):**\n"

            f"─────────────────────────────────────────\n"

            f"• {type_icon} **Phân loại:** **{type_label}**\n"

            f"• 💰 **Số tiền:** **{so_tien:,.0f} đ** ({amount_k_str})\n"

            f"• 📝 **Nội dung / Lý do:** **{noi_dung}**\n"

            f"• 📅 **Ngày ghi nhận:** **{now_date}**\n"

            f"─────────────────────────────────────────\n"

            f"👉 Anh có chắc chắn muốn ghi {type_label.lower()} này vào Sổ Thu Chi không?\n\n"

            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào sổ | Nhắn **'hủy'** để bỏ qua)*"

        )



    now_time = datetime.now().strftime("%H:%M:%S")

    created_at = f"{now_date} {now_time}"



    conn = sqlite3.connect(DB_THUCHI)

    c = conn.cursor()

    c.execute("SELECT id FROM periods WHERE status='open' ORDER BY id DESC LIMIT 1")

    p_row = c.fetchone()

    period_id = p_row[0] if p_row else 1



    c.execute(

        "INSERT INTO transactions (type, amount, created_at, note, period_id) VALUES (?, ?, ?, ?, ?)",

        (clean_type, so_tien, created_at, noi_dung.strip(), period_id)

    )

    t_id = c.lastrowid

    conn.commit()

    conn.close()



    icon = "💸" if clean_type == 'chi' else "💵"

    label = "KHOẢN CHI TIỀN" if clean_type == 'chi' else "KHOẢN THU TIỀN"

    return (

        f"{icon} **ĐÃ GHI VÀO SỔ {label} THÀNH CÔNG!**\n"

        f"─────────────────────────────────────────\n"

        f"• Mã phiếu: **#{t_id}**\n"

        f"• Số tiền: **{so_tien:,.0f} đ**\n"

        f"• Nội dung: **{noi_dung}**\n"

        f"• Ngày ghi: **{now_date}**\n"

        f"👉 Số dư sổ quỹ đã được cập nhật tự động."

    )





def len_don_bao_cao_den_nhanh(

    ten_den: str,

    bien_so_xe: str = "",

    so_dien_thoai: str = "",

    khach_hang: str = "",

    dong_xe: str = "",

    gia_tien_k: int = 0,

    so_luong: int = 1,

    ngay: str = "",

    confirmed: bool = False

) -> str:

    """Lên đơn nhanh vào Sổ Báo Cáo Doanh Thu Đèn khi khách hàng chốt đơn lắp đèn.

    Tự động lấy giá niêm yết nếu không nhập giá, tự động tra cứu khách hàng & xe từ biển số / SĐT.

    """

    if not os.path.exists(DB_DEN):

        return "⚠️ Không tìm thấy cơ sở dữ liệu Báo Cáo Đèn."



    # 1. Tự động lấy giá chuẩn xác từ kho hàng tiem_lap_do.db hoặc lịch sử gara

    p_k = int(gia_tien_k / 1000) if gia_tien_k > 50000 else int(gia_tien_k)

    matched_name = ten_den.strip().upper()

    is_default_price = False



    for pat, cname, _ in LAMP_CATALOG:

        if re.search(pat, ten_den, re.IGNORECASE):

            matched_name = cname

            break



    if p_k <= 0:

        try:

            from ai_assistant import get_lamp_price_from_memory

            mem_price = get_lamp_price_from_memory(matched_name or ten_den)

            if mem_price > 0:

                p_k = mem_price

                is_default_price = True

        except Exception:

            pass



    # Nếu vẫn không có giá trong kho và lịch sử, BẮT BUỘC DỪNG LẠI HỎI GIÁ NGƯỜI DÙNG!

    if p_k <= 0:

        return (

            f"MISSING_PRICE: Sản phẩm '{matched_name or ten_den}' chưa có giá trong hệ thống dữ liệu gara.\n"

            f"👉 Hãy dừng lại và hỏi người dùng mức giá thực tế cho sản phẩm này, tuyệt đối không tự ý cho giá!"

        )



    # 2. Tự động bù thông tin xe / biển số từ ngữ cảnh câu nói nếu Gemini bỏ sót

    if not bien_so_xe and CURRENT_USER_MESSAGE:

        try:

            from ai_assistant import extract_license_plate

            m_p = extract_license_plate(CURRENT_USER_MESSAGE)

            if m_p:

                bien_so_xe = m_p

        except Exception:

            pass



    if (not dong_xe or dong_xe in ["Chưa rõ dòng xe", ""]) and CURRENT_USER_MESSAGE:

        try:

            from ai_assistant import CAR_MODELS_LIST

            for cm in CAR_MODELS_LIST:

                if re.search(r'\b' + re.escape(cm) + r'\b', CURRENT_USER_MESSAGE, re.IGNORECASE):

                    dong_xe = cm.upper()

                    break

        except Exception:

            pass



    # 3. Tự động tra cứu khách hàng và xe từ biển số hoặc SĐT

    identifier = bien_so_xe.strip() or so_dien_thoai.strip()

    auto_found = False

    if identifier:

        try:

            from ai_assistant import lookup_customer_and_car_by_identifier

            cust_info = lookup_customer_and_car_by_identifier(identifier)

            if cust_info.get("found"):

                auto_found = True

                if not khach_hang or khach_hang.upper() in ["KHÁCH LẺ", "CHƯA RÕ", ""]:

                    khach_hang = cust_info.get("customer_name") or khach_hang

                if not dong_xe or dong_xe.upper() in ["CHƯA RÕ DÒNG XE", "CHƯA RÕ", ""]:

                    dong_xe = cust_info.get("car_model") or dong_xe

                if not so_dien_thoai and cust_info.get("phone"):

                    so_dien_thoai = cust_info.get("phone")

            else:

                # Không tìm thấy thông tin từ biển số / SĐT (xe mới)

                if not khach_hang or khach_hang.upper() in ["KHÁCH LẺ", "CHƯA RÕ", ""]:

                    return (

                        f"MISSING_INFO: Xe mang biển số / SĐT '{identifier}' chưa có thông tin trong hồ sơ gara (đây là xe/khách mới đến lần đầu).\n"

                        f"Đèn lắp: {matched_name} (Giá niêm yết: {p_k*1000:,.0f} đ).\n"

                        f"👉 Hãy dừng lại và hỏi người dùng Tên khách hàng và Dòng xe để bổ sung vào đơn đèn!"

                    )

        except Exception as e_lk:

            pass



    if not khach_hang:

        khach_hang = "KHÁCH LẺ"

    if not dong_xe:

        dong_xe = "Chưa rõ dòng xe"



    # 4. Chuẩn hóa ngày lắp đặt thông minh

    final_date = ""

    if ngay:

        if re.match(r'^\d{4}-\d{2}-\d{2}$', ngay.strip()):

            final_date = ngay.strip()

        else:

            try:

                from ai_assistant import extract_date

                d_p, _ = extract_date(ngay)

                if d_p:

                    final_date = d_p

            except Exception:

                pass



    if not final_date and CURRENT_USER_MESSAGE:

        try:

            from ai_assistant import extract_date

            d_p, _ = extract_date(CURRENT_USER_MESSAGE)

            if d_p:

                final_date = d_p

        except Exception:

            pass



    if not final_date:

        final_date = datetime.now().strftime("%Y-%m-%d")



    order_date = final_date

    cust_record = f"{khach_hang} ({bien_so_xe})" if (bien_so_xe and bien_so_xe not in khach_hang) else khach_hang



    if not confirmed:

        try:

            from ai_assistant import WIZARD_SESSIONS

            WIZARD_SESSIONS[CURRENT_ACTIVE_SESSION_ID] = {

                'flow': 'confirm_action',

                'action_type': 'baocao_den',

                'payload': {

                    'items': [{'product_name': matched_name, 'quantity': so_luong, 'final_price_k': p_k, 'base_price_k': p_k, 'discount_k': 0}],

                    'cust_name': cust_record,

                    'found_car': dong_xe.strip().upper(),

                    'plate': bien_so_xe,

                    'phone': so_dien_thoai,

                    'order_date': order_date,

                    'discount_k': 0,

                    'total_base_k': p_k * so_luong,

                    'total_final_k': p_k * so_luong,

                    'original_prompt': CURRENT_USER_MESSAGE

                }

            }

        except Exception as e:

            print(f"[GeminiEngine] Lỗi đăng ký confirm đơn đèn: {e}")



        default_note = " *(Giá niêm yết tự động)*" if is_default_price else ""

        tag_auto = " *(Hồ sơ tự nhận diện)*" if auto_found else ""

        return (

            f"❓ **XÁC NHẬN TẠO ĐƠN VÀO SỔ BÁO CÁO DOANH THU ĐÈN:**\n"

            f"───────────────────────────────────────\n"

            f"• 👤 **Khách hàng:** **{khach_hang}**{tag_auto}\n"

            f"• 🚗 **Dòng xe:** **{dong_xe.upper()}**\n"

            + (f"• 🚘 **Biển số:** **{bien_so_xe}**\n" if bien_so_xe else "")

            + (f"• 📞 **Số điện thoại:** **{so_dien_thoai}**\n" if so_dien_thoai else "")

            + f"• 📦 **Sản phẩm lắp đặt:**\n  1. **{matched_name}**: **{p_k * 1000:,.0f} đ ({p_k:,}k)**{default_note}\n"

            f"• 💰 **DOANH THU THỰC THU:** **{p_k * so_luong * 1000:,.0f} đ**\n"

            f"• 📅 **Ngày lắp:** **{order_date}**" + (" *(Hôm nay)*" if order_date == datetime.now().strftime('%Y-%m-%d') else "") + "\n"

            f"───────────────────────────────────────\n"

            f"👉 Anh có chắc chắn muốn **LƯU ĐƠN HÀNG NÀY** vào hệ thống không?\n\n"

            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào Báo Cáo Đèn | Nhắn **'hủy'** để bỏ qua)*"

        )



    conn = sqlite3.connect(DB_DEN)

    c = conn.cursor()

    c.execute(

        "INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin) VALUES (?, ?, ?, ?, ?, ?, ?)",

        (order_date, matched_name, cust_record, dong_xe.strip().upper(), so_luong, p_k, "AI_GEMINI_DIRECT")

    )

    new_id = c.lastrowid

    conn.commit()

    conn.close()



    default_note = " *(Giá niêm yết tự động)*" if is_default_price else ""

    tag_auto = " *(Hồ sơ tự nhận diện)*" if auto_found else ""

    return (

        f"💡 **ĐÃ GHI NHẬN ĐƠN BÁO CÁO ĐÈN THÀNH CÔNG!**\n"

        f"─────────────────────────────────────────\n"

        f"• Mã đơn: **#{new_id}**\n"

        f"• Khách hàng: **{khach_hang}**{tag_auto}\n"

        + (f"• Biển số xe: **{bien_so_xe}**\n" if bien_so_xe else "")

        + (f"• Số điện thoại: **{so_dien_thoai}**\n" if so_dien_thoai else "")

        + f"• Dòng xe: **{dong_xe.upper()}**\n"

        f"• Đèn lắp: **{matched_name}** (SL: {so_luong})\n"

        f"• Doanh thu: **{p_k * 1000:,.0f} đ** ({p_k:,}k){default_note}\n"

        f"• Ngày ghi: **{order_date}**\n"

        f"👉 [Bấm vào đây để xem Báo Cáo Doanh Thu Đèn](/den/)"

    )



# Danh sách Tools cung cấp cho Gemini



def ghi_nho_tri_thuc_gara(noi_dung_ghi_nho: str) -> str:

    """Ghi nhớ một kiến thức, quy định, chính sách, hoặc bảng giá mới vào bộ não tri thức vĩnh viễn của gara.



    Args:

        noi_dung_ghi_nho: Toàn bộ nội dung cần ghi nhớ (ví dụ: 'sàn 5d cho xe 4 chỗ là 1.800.000, may thêm túi 100k, tối đa 2 túi').

    """

    try:

        import knowledge_base

        res = knowledge_base.analyze_and_learn(noi_dung_ghi_nho)

        return res.get("message", "Đã ghi nhớ thành công.")

    except Exception as e:

        return f"Lỗi khi lưu tri thức: {e}"





def sua_quy_dinh_san_pham(ten_san_pham: str, quy_dinh_moi: str) -> str:

    """Cập nhật hoặc sửa đổi quy định, quà tặng, thẻ nhớ, bảo hành của một sản phẩm/dịch vụ cụ thể trong gara.



    Args:

        ten_san_pham: Tên sản phẩm cần sửa đổi (ví dụ: 'A510', '70mai A510', 'F10', 'M1').

        quy_dinh_moi: Quy định hoặc điều chỉnh mới (ví dụ: 'chưa bao gồm thẻ nhớ', 'không tặng thẻ nhớ', 'bảo hành 3 năm').

    """

    try:

        import knowledge_base

        res = knowledge_base.analyze_and_learn(f"sửa lại {ten_san_pham} {quy_dinh_moi}")

        return res.get("message", "Đã cập nhật quy định thành công.")

    except Exception as e:

        return f"Lỗi khi cập nhật quy định: {e}"





def tra_cuu_tri_thuc_gara(chu_de_hoac_tu_khoa: str) -> str:

    """Tra cứu các quy định, bảng giá đặc thù, kiến thức riêng mà chủ gara đã dạy cho AI trong bộ nhớ.



    Args:

        chu_de_hoac_tu_khoa: Từ khóa hoặc tên sản phẩm cần tra cứu (ví dụ: 'sàn 5d', 'a510', 'bọc trần').

    """

    try:

        import knowledge_base

        clean_kw = knowledge_base.remove_accents(chu_de_hoac_tu_khoa).lower()

        res = knowledge_base.query_learned_knowledge(clean_kw, chu_de_hoac_tu_khoa)

        if res:

            return res.get("message", "")

        return f"Chưa có ghi nhớ đặc biệt nào cho '{chu_de_hoac_tu_khoa}' trong bộ não gara."

    except Exception as e:

        return f"Lỗi tra cứu tri thức: {e}"



GARA_TOOLS = [

    sua_don_hang,

    xoa_don_hang,

    cap_nhat_kho_hang,

    cap_nhat_thong_tin_khach_hang,

    tra_cuu_khach_hang_va_bao_hanh,

    tra_cuu_san_pham_kho_hang,

    thong_ke_doanh_thu,

    ghi_so_thu_chi,

    len_don_bao_cao_den_nhanh,

    ghi_nho_tri_thuc_gara,

    sua_quy_dinh_san_pham,

    tra_cuu_tri_thuc_gara

]



# ─────────────────────────────────────────────────────────────────────────────

# 2. SYSTEM INSTRUCTION - HƯỚNG DẪN ĐIỀU HÀNH CHUYÊN SÂU DÀNH CHO GEMINI

# ─────────────────────────────────────────────────────────────────────────────



SYSTEM_PROMPT = """

Bạn là Trợ Lý AI Điều Hành Toàn Diện của Gara Ô Tô Trần Bình Auto (Trần Bình Auto).

Bạn được cấp quyền kiểm soát thông minh: tra cứu dữ liệu, quản trị kho hàng, chỉnh sửa thông tin đơn hàng, cập nhật thông tin khách hàng, ghi sổ thu chi và tư vấn dịch vụ gara chuẩn xác.



╔══════════════════════════════════════════════════════════════════════╗

║               QUY TẮC BẢO VỆ NGỮ CẢNH HỘI THOẠI ĐA LƯỢT              ║

╚══════════════════════════════════════════════════════════════════════╝

1. GHI NHỚ NGỮ CẢNH CÂU TRƯỚC: Luôn chú ý sản phẩm, dịch vụ, khách hàng hoặc đơn hàng vừa được nhắc đến ở lượt chat trước đó.

2. SỬA GIÁ / SỬA QUY ĐỊNH SẢN PHẨM: Khi người dùng nói "sửa giá lại thành...", "đổi giá thành...", "sửa lại thành..." ngay sau khi vừa nói về một sản phẩm/dịch vụ (như A510, F10, Sàn 5D...):

   ➔ ĐÂY LÀ YÊU CẦU CẬP NHẬT GIÁ SẢN PHẨM HOẶC BẢNG GIÁ DỊCH VỤ ĐÓ.

   ➔ Bạn PHẢI gọi hàm `sua_quy_dinh_san_pham` và `cap_nhat_kho_hang` để cập nhật giá mới cho sản phẩm vừa nói!

   ➔ TUYỆT ĐỐI KHÔNG HỎI MÃ ĐƠN HÀNG khi người dùng không hề nhắc đến từ "đơn"!

3. HỎI NỐI TIẾP: Nếu câu trước vừa nói về sản phẩm A mà câu sau hỏi "bảo hành bao lâu?", "lắp xe gì?", "có mấy màu?", hãy hiểu là đang hỏi về sản phẩm A!



╔══════════════════════════════════════════════════════════════════════╗

║                    QUY TẮC SỬ DỤNG CÔNG CỤ (TOOLS)                   ║

╚══════════════════════════════════════════════════════════════════════╝

1. CHỈNH SỬA ĐƠN HÀNG: Khi người dùng muốn sửa thông tin đơn hàng (đổi tên khách, sửa số điện thoại, sửa biển số, đổi dòng xe, sửa ngày, sửa tiền), bạn PHẢI gọi hàm `sua_don_hang`.

2. XÓA / HỦY ĐƠN: Khi người dùng yêu cầu xóa hoặc hủy đơn hàng theo mã số, hãy gọi hàm `xoa_don_hang`.

3. QUẢN LÝ KHO HÀNG: Khi người dùng muốn cập nhật tồn kho, tăng/giảm số lượng sản phẩm, hoặc đổi giá bán/giá vốn, hãy gọi hàm `cap_nhat_kho_hang`.

4. CẬP NHẬT THÔNG TIN KHÁCH HÀNG: Khi người dùng muốn đổi tên, SĐT hoặc biển số xe cho khách hàng đã có lịch sử, hãy gọi hàm `cap_nhat_thong_tin_khach_hang`.

5. TRA CỨU BẢO HÀNH & LỊCH SỬ XE: Khi hỏi về xe đã làm gì, biển số xe, SĐT khách, hãy gọi `tra_cuu_khach_hang_va_bao_hanh`.

6. TRA CỨU TỒN KHO & GIÁ SẢN PHẨM: Khi hỏi "tồn kho...", "giá sản phẩm...", hãy gọi `tra_cuu_san_pham_kho_hang`.

7. BÁO CÁO DOANH THU & TÀI CHÍNH: Khi hỏi doanh thu, hãy gọi `thong_ke_doanh_thu`.

8. GHI SỔ THU CHI: Khi có lệnh "chi..." hoặc "thu...", hãy gọi `ghi_so_thu_chi`.



10. GHI NHỚ TRI THỨC GARA: Khi người dùng muốn dạy AI ghi nhớ kiến thức/bảng giá mới ('ghi nhớ...', 'nhớ...'), hãy gọi `ghi_nho_tri_thuc_gara`.

11. SỬA ĐỔI QUY ĐỊNH SẢN PHẨM: Khi người dùng muốn sửa lại quy định, quà tặng, thẻ nhớ của sản phẩm ('sửa lại a510 chưa bao gồm thẻ nhớ', 'chỉnh lại...'), hãy gọi `sua_quy_dinh_san_pham`.

12. TRA CỨU TRI THỨC GARA: Khi khách hoặc người dùng hỏi về sản phẩm đã được dạy (như 'sàn 5d', 'a510 quy định mới...'), hãy gọi `tra_cuu_tri_thuc_gara`.

9. LÊN ĐƠN BÁO CÁO ĐÈN THÔNG MINH TỪ BIỂN SỐ XE / SĐT:

   - Khi người dùng ra lệnh lắp đèn hoặc nhập đơn đèn (ví dụ: "nhập đơn f10 new 63A-187.30", "lắp s3 0921889919", "lắp f10 xe 63A-187.30"):

     ➔ Bạn CHỈ CẦN gọi hàm `len_don_bao_cao_den_nhanh` với `ten_den` và `bien_so_xe` (hoặc `so_dien_thoai`).

     ➔ Hàm sẽ TỰ ĐỘNG lấy giá niêm yết và TỰ ĐỘNG tra cứu thông tin khách hàng, dòng xe từ lịch sử gara!

   - ⚠️ ĐẶC BIỆT KHI KHÔNG TÌM THẤY TÊN TỪ SỐ XE / SĐT (MISSING_INFO):

     ➔ Nếu hàm trả về `MISSING_INFO` (xe mới chưa có hồ sơ và người dùng chưa nói tên khách):

     ➔ Bạn PHẢI DỪNG LẠI và hỏi người dùng Tên khách hàng và Dòng xe để điền vào đơn!

     ➔ Tuyệt đối không tự bịa thông tin hay gán 'KHÁCH LẺ' khi xe chưa có tên khách!

   - ⚠️ LƯU Ý BẢO VỆ: Nếu người dùng CHỈ gõ tên đèn để hỏi giá hoặc tư vấn (như "f10", "f10 turbo", "đèn gầm"), TUYỆT ĐỐI KHÔNG LÊN ĐƠN, mà hãy trả lời tư vấn & báo giá chi tiết!



╔══════════════════════════════════════════════════════════════════════╗

║               KIẾN THỨC NGHIỆP VỤ & BÁO GIÁ GARA CHÍNH HÃNG          ║

╚══════════════════════════════════════════════════════════════════════╝

• CAMERA 360 ĐỘ:

  - Phân loại rõ ràng:

    + Camera 360 rời cắm giắc zin màn hình gốc theo xe (giữ zin 100%): Camera 360 Owin (8.5tr - 16.1tr, mắt cam Sony ban đêm siêu nét, bản cho VF3 không CarPlay 8.5tr, có CarPlay 9.5tr), DCT T1/T2 Pro (12.8tr - 15.8tr).

    + Màn hình Android liền Cam 360 độ: Winca S170+ (10.5tr - 11.8tr - bán chạy), Gotech GC360 / GT2K 360 (12.9tr - 19.9tr).

  - ⛔ ĐẶC BIỆT: Gara ĐÃ NGỪNG KINH DOANH dòng Camera 360 TexPad!



╔══════════════════════════════════════════════════════════════════════╗

║        CÁC CẤM CHẾ BẢO VỆ DỮ LIỆU BẮT BUỘC DÀNH CHO GEMINI (SẮT ĐÁ)   ║

╚══════════════════════════════════════════════════════════════════════╝

1. NGUYÊN TẮC BẢO VỆ DỮ LIỆU TUYỆT ĐỐI - HỎI TRƯỚC LÀM SAU:

   - Mọi hành vi làm thay đổi dữ liệu (Thêm đơn đèn, Sửa đơn hàng, Xóa đơn hàng, Cập nhật kho/giá, Đổi thông tin khách hàng, Ghi sổ thu chi) BẮT BUỘC PHẢI QUA BƯỚC HỎI XÁC NHẬN.

   - Khi gọi các tool thao tác dữ liệu (`len_don_bao_cao_den_nhanh`, `sua_don_hang`, `xoa_don_hang`, `cap_nhat_kho_hang`, `cap_nhat_thong_tin_khach_hang`, `ghi_so_thu_chi`), hệ thống sẽ trả về phiếu xác nhận.

   - TUYỆT ĐỐI KHÔNG tự ý báo "đã cập nhật thành công" hay "đã lưu" khi người dùng chưa bấm nút [✅ OK / Lưu] hoặc nhắn 'ok'!

2. CẤM XÓA HAY GHI ĐÈ HÀNG LOẠT DỮ LIỆU LỊCH SỬ:

   - Dữ liệu bán hàng, doanh thu đèn và sổ thu chi là tài sản kế toán quan trọng nhất của gara. Tuyệt đối cấm xóa hay ghi đè toàn bộ dữ liệu.

   - Chỉ được sửa hoặc xóa đúng 1 đơn hàng cụ thể khi người dùng có chỉ định rõ ràng mã đơn (ví dụ: #750).

3. CẤM BỊA ĐẶT THÔNG TIN / GIÁ CẢ / NGÀY THÁNG (NĂM 2026):

   - Thời gian thực tế hiện tại là năm 2026 (Hôm nay: 29/10/2026).

   - Khi câu lệnh có ngày tháng (ví dụ: "vào ngày 13/8/2026", "ngày 13/08", "hôm qua"), BẮT BUỘC PHẢI TRUYỀN ĐÚNG NGÀY ĐÓ vào tham số `ngay` (ví dụ: 2026-08-13). TUYỆT ĐỐI CẤM BỎ QUÊN NGÀY ĐỂ MẶC ĐỊNH LÀ HÔM NAY!

   - Không được tự ý cho giá nếu hệ thống chưa có. Phải dừng lại hỏi người dùng.

   - Không được tự ý bịa tên khách nếu xe mới chưa có lịch sử. Phải dừng lại hỏi người dùng.

4. PHÂN BIỆT RÕ RÀNG GIỮA "TẠO ĐƠN ĐÈN" VÀ "BÁO CÁO DOANH THU":

   - Khi câu nói có từ hành động: "lắp", "gắn", "thay", "độ", "lên cặp", "nhập đơn", "vào đơn", kể cả có kèm ngày tháng năm (ví dụ: "lắp f1 turbo s cho xe city 63a36001 vào ngày 13/8/2026"): ĐÂY LÀ HÀNH ĐỘNG TẠO ĐƠN HÀNG! PHẢI GỌI `len_don_bao_cao_den_nhanh`.

   - TUYỆT ĐỐI CẤM gọi `thong_ke_doanh_thu` cho những câu lệnh tạo đơn này.

   - Tool `thong_ke_doanh_thu` CHỈ ĐƯỢC GỌI khi người dùng rõ ràng HỎI XEM BÁO CÁO: "doanh thu tháng...", "thống kê tháng...", "hôm nay bán được bao nhiêu"...



╔══════════════════════════════════════════════════════════════════════╗

║        QUY TẮC BẢO VỆ GIÁ CẢ & CẤM SUY DIỄN THÔNG TIN (SẮT ĐÁ)        ║

╚══════════════════════════════════════════════════════════════════════╝

1. TUYỆT ĐỐI CẤM TỰ TIỆN CHO GIÁ HOẶC BỊA ĐẶT GIÁ SẢN PHẨM:

   - Thời gian thực tế hiện tại của hệ thống gara là năm 2026 (Hôm nay: 29/10/2026).

   - Khi người dùng hỏi giá hoặc tra cứu sản phẩm (như "f10 2.0", "f10 new", "m1"): Bạn PHẢI gọi tool `tra_cuu_san_pham_kho_hang` để lấy giá và tồn kho thực tế từ cơ sở dữ liệu `tiem_lap_do.db`. TUYỆT ĐỐI KHÔNG BỊA GIÁ 3.9tr hay bất kỳ con số nào!

   - Khi người dùng ra lệnh lên đơn / nhập đơn đèn mà không nói giá (ví dụ "nhập đơn f10 new 2.0 63A18730"): Bạn CHỈ CẦN gọi tool `len_don_bao_cao_den_nhanh`. Tool sẽ TỰ ĐỘNG tra cứu giá bán từ kho hàng và lịch sử đơn hàng, đồng thời TỰ ĐỘNG tra cứu khách hàng và dòng xe từ biển số / SĐT.

   - NẾU SẢN PHẨM HOÀN TOÀN CHƯA CÓ TRONG HỆ THỐNG VÀ NGƯỜI DÙNG CHƯA NÓI GIÁ (hoặc tool trả về MISSING_PRICE):

     BẮT BUỘC DỪNG LẠI VÀ HỎI NGƯỜI DÙNG: "Dạ sản phẩm [Tên sản phẩm] hiện chưa có thông tin giá niêm yết trong hệ thống dữ liệu của gara. Anh/chị cho em xin mức giá thực tế để em cập nhật nhé!"

   - NẾU BIỂN SỐ XE HOẶC SĐT CHƯA CÓ TRONG HỒ SƠ VÀ NGƯỜI DÙNG CHƯA NÓI TÊN KHÁCH (tool trả về MISSING_INFO):

     BẮT BUỘC DỪNG LẠI VÀ HỎI TÊN KHÁCH HÀNG VÀ DÒNG XE. Tuyệt đối không tự suy diễn hoặc bịa tên khách!

2. TUYỆT ĐỐI CẤM TỰ SUY DIỄN THƯƠNG HIỆU & THÔNG SỐ KỸ THUẬT:

   - Nếu người dùng chỉ nói "F10", cấm tự gắn "Aozoom F10" nếu trong cơ sở dữ liệu hoặc yêu cầu người dùng không nói chữ Aozoom.

   - Không tự bịa thông số kỹ thuật (bảo hành 3 năm, chống nước IP68...) nếu cơ sở dữ liệu gara không có thông tin này.

   - Tuyệt đối trung thực 100% với dữ liệu thực tế tại gara Trần Bình Auto.

3. PHÂN BIỆT RÕ LỆNH SỬA GIÁ SẢN PHẨM VÀ SỬA ĐƠN HÀNG:

   - Khi người dùng nói "sửa giá lại thành...", "sửa giá f10 new 2.0 thành 4500", "sửa lại giá [tên sản phẩm] giá [tiền]": ĐÂY LÀ LỆNH CẬP NHẬT GIÁ SẢN PHẨM TRONG KHO. Bạn PHẢI gọi `cap_nhat_kho_hang` để cập nhật giá mới!

   - TUYỆT ĐỐI KHÔNG HỎI MÃ ĐƠN HÀNG khi người dùng không nhắc đến chữ "đơn"!

4. HỌC VÀ NHẬN DIỆN MỌI KHẨU NGỮ, TỪ LÓNG & CÁCH DIỄN ĐẠT ĐƠN HÀNG ĐÈN GARA:

   - Các từ lóng & hành động: "nhập đơn", "lên đơn", "lắp", "gắn", "thay", "độ", "lên cặp", "vào cặp", "bắn cặp", "múc đôi bi", "vừa làm xong xe...", "chốt đơn cho...", "bán cặp f10 mua về tự ráp"...

   - Mọi trật tự câu từ:

     + Biển số trước: "xe 63A18730 lắp f10 new 2.0"

     + Khách trước: "anh Tuấn vios lên cặp f10 new 4tr2"

     + Đèn trước: "f10 new 2.0 63A18730", "s3 vf3 1tr5"

     + Kèm ngày cụ thể: "lắp f1 turbo s cho xe city 63a36001 vào ngày 13/8/2026"

   - Khi gặp các câu này: PHẢI gọi tool `len_don_bao_cao_den_nhanh` để tạo đơn, TUYỆT ĐỐI KHÔNG BÁO CÁO DOANH THU TOÀN CỬA HÀNG!



• PHIM CÁCH NHIỆT CHỐNG NÓNG:

  - 3M Crystalline Mỹ (200 lớp quang học): Kính lái CR50BLK (5.7tr), trọn gói Sedan (10.8tr - 14.8tr), SUV (12.5tr - 17.6tr).

  - 3M Ceramic NR / IR: Kính lái dán lẻ 2.6tr, trọn gói Sedan 7.9tr - 9.0tr.

  - CeraMAX Diamond (Men gốm sinh học BH 15 năm): Kính lái CeraMAX 50 (3.3tr, xuyên sáng 59.7%, cắt IR 99.1%), trọn gói 9.5tr - 11.3tr.

  - Ntech Hàn Quốc (Kính lái CeraMAX + Sườn Ntech): 5.6tr - 6.5tr (Bán chạy nhất).

  - Đăng kiểm: Gara dùng kính lái CR50BLK và CeraMAX 50 đạt chuẩn >50% VLT, bao đăng kiểm 100%.



• GÓI PHỤ KIỆN ĐỘ XE VINFAST VF3:

  - Cam 360 Owin cắm giắc zin màn hình gốc: 8.5tr (không CarPlay) / 9.5tr (có CarPlay).

  - Màn hình Android WINCA liền Cam 360: 10.5tr. Màn WINCA đơn: 7.5tr.

  - Cốp trước EasyCop: 5.5tr. Cửa hít X-Win: 9.5tr.

  - Bi gầm F10 Turbo / S3: 3.9tr - 4.5tr. Mặt calang đèn tròn V4: 16tr. Bọc ghế da Nappa: 9.5tr.



• LƯU Ý ĐẶC THÙ:

  - Xe VinFast VF5 gara KHÔNG nhận bọc trần nilong.



╔══════════════════════════════════════════════════════════════════════╗

║                     PHONG CÁCH PHẢN HỒI                              ║

╚══════════════════════════════════════════════════════════════════════╝

- Xưng "em" gọi "anh/chị" hoặc xưng "Trợ lý Trần Bình Auto". Lịch sự, nhã nhặn, am hiểu sâu sắc đồ chơi ô tô.

- Trình bày dạng bullet points, bôi đậm tiêu điểm, có icon trực quan.

- Khi người dùng hỏi thiếu thông tin quan trọng (ví dụ hỏi doanh thu nhưng không nói tháng mấy/năm nào, hoặc muốn sửa đơn mà không nói mã đơn nào), hãy chủ động hỏi lại một cách tinh tế.

"""



def get_or_create_gemini_chat(session_id: str = "default_user", model_name: str = None):

    """Tạo hoặc lấy lại phiên chat của Gemini có bộ nhớ ngữ cảnh và tools."""

    if not GENAI_AVAILABLE:

        return None



    client = get_gemini_client()

    if not client:

        return None



    target_model = model_name or AVAILABLE_MODELS[0]

    session_key = f"{session_id}_{target_model}"



    if session_key in GEMINI_SESSIONS:

        return GEMINI_SESSIONS[session_key]



    try:

        chat = client.chats.create(

            model=target_model,

            config=types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                tools=GARA_TOOLS,

                max_output_tokens=600,

                temperature=0.2

            )

        )

        GEMINI_SESSIONS[session_key] = chat

        return chat

    except Exception as e:

        print(f"[GeminiEngine] Lỗi khởi tạo chat session ({target_model}): {e}")

        return None





LAST_KEY_ERROR = None



def get_key_status_message() -> str:

    global LAST_KEY_ERROR

    if LAST_KEY_ERROR == "API_KEY_LEAKED_403":

        return (

            "⚠️ **API KEY GEMINI ĐÃ BỊ GOOGLE KHÓA BẢO MẬT (403 PERMISSION_DENIED)**\n"

            "─────────────────────────────────────────\n"

            "Google phát hiện mã API Key trước đó bị lộ công khai trên internet nên đã tự động vô hiệu hóa.\n"

            "Vì lý do này, AI tạm thời chưa thể gọi được trí tuệ Gemini 3.5 Flash mà đang chạy bằng bộ lọc cục bộ.\n\n"

            "👉 **CÁCH KÍCH HOẠT LẠI TRONG 30 GIÂY (HOÀN TOÀN MIỄN PHÍ):**\n"

            "1. Anh truy cập: https://aistudio.google.com/app/apikey\n"

            "2. Bấm nút **'Create API Key'**\n"

            "3. Sao chép mã (bắt đầu bằng `AIzaSy...`) rồi **dán trực tiếp vào khung chat này**!\n"

            "Hệ thống sẽ tự nhận diện, lưu an toàn vào máy và bật Gemini ngay lập tức!"

        )

    return ""





import urllib.request





# ─────────────────────────────────────────────────────────────────────────────

# 1.5. BỘ CÔNG CỤ TOOLS REST API & TỰ ĐỘNG THỰC THI (FUNCTION CALLING ENGINE)

# ─────────────────────────────────────────────────────────────────────────────



TOOL_DISPATCH = {

    "sua_don_hang": sua_don_hang,

    "xoa_don_hang": xoa_don_hang,

    "cap_nhat_kho_hang": cap_nhat_kho_hang,

    "cap_nhat_thong_tin_khach_hang": cap_nhat_thong_tin_khach_hang,

    "tra_cuu_khach_hang_va_bao_hanh": tra_cuu_khach_hang_va_bao_hanh,

    "tra_cuu_san_pham_kho_hang": tra_cuu_san_pham_kho_hang,

    "thong_ke_doanh_thu": thong_ke_doanh_thu,

    "ghi_so_thu_chi": ghi_so_thu_chi,

    "len_don_bao_cao_den_nhanh": len_don_bao_cao_den_nhanh,

    "ghi_nho_tri_thuc_gara": ghi_nho_tri_thuc_gara,

    "sua_quy_dinh_san_pham": sua_quy_dinh_san_pham,

    "tra_cuu_tri_thuc_gara": tra_cuu_tri_thuc_gara,

}



REST_TOOLS_DECLARATIONS = [

    {

        "name": "sua_don_hang",

        "description": "Chỉnh sửa thông tin đơn hàng đã có trong hệ thống (đổi tên khách, đổi số điện thoại, sửa biển số, đổi xe, sửa ngày, sửa tiền)",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "ma_don_hang": {"type": "INTEGER", "description": "Mã đơn hàng cần sửa (ví dụ: 747, 729)"},

                "loai_don": {"type": "STRING", "description": "Loại đơn ('banhang', 'den', hoặc 'auto')"},

                "ten_khach_moi": {"type": "STRING", "description": "Tên khách mới"},

                "sdt_moi": {"type": "STRING", "description": "Số điện thoại mới"},

                "bien_so_moi": {"type": "STRING", "description": "Biển số xe mới"},

                "dong_xe_moi": {"type": "STRING", "description": "Dòng xe mới (ví dụ: Accent, Vios, CX5)"},

                "ten_san_pham_moi": {"type": "STRING", "description": "Tên sản phẩm mới"},

                "gia_tien_moi": {"type": "NUMBER", "description": "Giá tiền mới (VNĐ)"},

                "ngay_moi": {"type": "STRING", "description": "Ngày mới YYYY-MM-DD"}

            },

            "required": ["ma_don_hang"]

        }

    },

    {

        "name": "xoa_don_hang",

        "description": "Xóa hoặc hủy một đơn hàng theo mã đơn trong phần mềm bán hàng hoặc báo cáo đèn",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "ma_don_hang": {"type": "INTEGER", "description": "Mã đơn hàng cần xóa"},

                "loai_don": {"type": "STRING", "description": "Loại đơn ('auto', 'den', 'banhang')"}

            },

            "required": ["ma_don_hang"]

        }

    },

    {

        "name": "cap_nhat_kho_hang",

        "description": "Cập nhật số lượng tồn kho, giá bán lẻ hoặc giá vốn của sản phẩm trong kho hàng",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "ma_hoac_ten_sp": {"type": "STRING", "description": "Mã sản phẩm (SP...) hoặc tên sản phẩm"},

                "ton_kho_moi": {"type": "INTEGER", "description": "Số lượng tồn kho mới"},

                "gia_ban_moi": {"type": "NUMBER", "description": "Giá bán lẻ mới (VNĐ)"},

                "gia_von_moi": {"type": "NUMBER", "description": "Giá vốn nhập mới (VNĐ)"}

            },

            "required": ["ma_hoac_ten_sp"]

        }

    },

    {

        "name": "cap_nhat_thong_tin_khach_hang",

        "description": "Cập nhật đổi tên, số điện thoại hoặc biển số xe cho khách hàng đã có lịch sử",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "dinh_danh_cu": {"type": "STRING", "description": "Biển số xe cũ, SĐT cũ hoặc tên khách cũ để tìm kiếm"},

                "ten_moi": {"type": "STRING", "description": "Tên khách mới"},

                "sdt_moi": {"type": "STRING", "description": "Số điện thoại mới"},

                "bien_so_moi": {"type": "STRING", "description": "Biển số mới"}

            },

            "required": ["dinh_danh_cu"]

        }

    },

    {

        "name": "tra_cuu_khach_hang_va_bao_hanh",

        "description": "Tra cứu lịch sử làm dịch vụ, sửa chữa, bảo hành theo biển số xe, SĐT hoặc tên khách",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "tu_khoa": {"type": "STRING", "description": "Biển số xe (ví dụ '63A-187.30'), Số điện thoại hoặc tên khách"}

            },

            "required": ["tu_khoa"]

        }

    },

    {

        "name": "tra_cuu_san_pham_kho_hang",

        "description": "Tra cứu giá bán và số lượng tồn kho của các sản phẩm phụ kiện trong kho",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "tu_khoa": {"type": "STRING", "description": "Tên hoặc mã sản phẩm (ví dụ: 'F10', 'A510', 'taplo', 'bóng led')"}

            },

            "required": ["tu_khoa"]

        }

    },

    {

        "name": "thong_ke_doanh_thu",

        "description": "Chỉ dùng khi người dùng HỎI XEM báo cáo, doanh thu, số đơn, thống kê bán hàng hoặc tài chính (ví dụ: 'doanh thu tháng này', 'báo cáo tháng 8', 'hôm nay bán được bao nhiêu'). TUYỆT ĐỐI CẤM GỌI KHI NGƯỜI DÙNG RA LỆNH LẮP ĐẶT, GẮN ĐÈN HOẶC TẠO ĐƠN HÀNG (đối với lệnh lắp đèn hãy gọi len_don_bao_cao_den_nhanh).",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "loai_thong_ke": {"type": "STRING", "description": "'tat_ca', 'den', 'banhang', 'thuchi'"},

                "thang": {"type": "INTEGER", "description": "Tháng cần xem (1-12)"},

                "nam": {"type": "INTEGER", "description": "Năm cần xem (ví dụ 2026)"},

                "ngay_cu_the": {"type": "STRING", "description": "Ngày cụ thể YYYY-MM-DD"}

            }

        }

    },

    {

        "name": "ghi_so_thu_chi",

        "description": "Ghi phiếu thu tiền hoặc phiếu chi tiền vào sổ quỹ tài chính của gara",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "loai": {"type": "STRING", "description": "'chi' hoặc 'thu'"},

                "so_tien": {"type": "INTEGER", "description": "Số tiền (VNĐ, ví dụ: 350000)"},

                "noi_dung": {"type": "STRING", "description": "Lý do / mục đích chi hoặc thu"},

                "ngay": {"type": "STRING", "description": "Ngày phát sinh YYYY-MM-DD"}

            },

            "required": ["loai", "so_tien", "noi_dung"]

        }

    },

    {

        "name": "len_don_bao_cao_den_nhanh",

        "description": "Lên đơn nhanh vào Sổ Báo Cáo Doanh Thu Đèn khi khách hàng chốt đơn lắp đèn. Tự động lấy giá niêm yết và tra cứu khách hàng/dòng xe theo biển số xe hoặc SĐT",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "ten_den": {"type": "STRING", "description": "Tên sản phẩm đèn (F10 New, F10 Turbo, S3, V20...)"},

                "bien_so_xe": {"type": "STRING", "description": "Biển số xe (ví dụ: 63A-187.30, 66A-489.85)"},

                "so_dien_thoai": {"type": "STRING", "description": "Số điện thoại khách hàng nếu có"},

                "khach_hang": {"type": "STRING", "description": "Tên khách hàng nếu có"},

                "dong_xe": {"type": "STRING", "description": "Dòng xe (Accent, Vios, VF3...)"},

                "gia_tien_k": {"type": "INTEGER", "description": "Giá thu thực tế theo k (ví dụ: 3900 cho 3.9tr, truyền 0 để tự lấy giá niêm yết)"},

                "so_luong": {"type": "INTEGER", "description": "Số lượng bộ đèn (mặc định 1)"},

                "ngay": {"type": "STRING", "description": "Ngày lắp đặt (ví dụ: '2026-08-13', '13/8/2026', 'ngày 13/08'). Luôn bóc tách chính xác từ câu lệnh, không được bỏ qua."}

            },

            "required": ["ten_den"]

        }

    },

    {

        "name": "ghi_nho_tri_thuc_gara",

        "description": "Ghi nhớ một kiến thức, quy định, chính sách, hoặc bảng giá mới vào bộ não tri thức vĩnh viễn của gara",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "noi_dung_ghi_nho": {"type": "STRING", "description": "Nội dung cần ghi nhớ"}

            },

            "required": ["noi_dung_ghi_nho"]

        }

    },

    {

        "name": "sua_quy_dinh_san_pham",

        "description": "Cập nhật hoặc sửa đổi quy định, quà tặng, thẻ nhớ của một sản phẩm trong gara",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "ten_san_pham": {"type": "STRING", "description": "Tên sản phẩm"},

                "quy_dinh_moi": {"type": "STRING", "description": "Quy định mới (ví dụ: 'chưa bao gồm thẻ nhớ')"}

            },

            "required": ["ten_san_pham", "quy_dinh_moi"]

        }

    },

    {

        "name": "tra_cuu_tri_thuc_gara",

        "description": "Tra cứu các quy định, bảng giá đặc thù mà chủ gara đã dạy cho AI trong bộ nhớ",

        "parameters": {

            "type": "OBJECT",

            "properties": {

                "chu_de_hoac_tu_khoa": {"type": "STRING", "description": "Chủ đề cần tra cứu"}

            },

            "required": ["chu_de_hoac_tu_khoa"]

        }

    }

]





def append_to_history(session_id: str, user_text: str, reply_text: str):

    """Lưu trữ một lượt đối đáp (user, model) vào lịch sử ngữ cảnh của session để Gemini luôn nhớ liên tục."""

    if not session_id:

        session_id = "default_user"

    if session_id not in REST_CHAT_HISTORY:

        REST_CHAT_HISTORY[session_id] = []

    hist = REST_CHAT_HISTORY[session_id]

    hist.append({"role": "user", "parts": [{"text": user_text}]})

    hist.append({"role": "model", "parts": [{"text": reply_text}]})

    if len(hist) > 16:

        REST_CHAT_HISTORY[session_id] = hist[-16:]



REST_CHAT_HISTORY = {}



def ask_gemini_rest(message: str, session_id: str = "default_user") -> dict:
    """Xử lý Gemini trực tiếp qua chuẩn REST API của Google có hỗ trợ Function Calling tự động & Token Tracking.
    Hoạt động 100% trên mọi nền tảng (PythonAnywhere, VPS, Docker, Windows, Linux)
    mà không cần bất kỳ thư viện bên ngoài nào.
    """
    global LAST_KEY_ERROR
    set_current_session(session_id, user_message=message)
    cfg = load_gemini_config()
    api_key = cfg.get("api_key") or DEFAULT_API_KEY
    if not api_key:
        return None

    if session_id not in REST_CHAT_HISTORY:
        REST_CHAT_HISTORY[session_id] = []
    
    history = REST_CHAT_HISTORY[session_id]
    history.append({"role": "user", "parts": [{"text": message}]})
    if len(history) > 12:
        history = history[-12:]
        REST_CHAT_HISTORY[session_id] = history

    active_model = cfg.get("preferred_model") or cfg.get("model") or "gemini-3.5-flash-lite"
    candidate_models = [active_model]
    for m in AVAILABLE_MODELS:
        if m and m not in candidate_models:
            candidate_models.append(m)

    for model_name in candidate_models:
        clean_model = model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
        
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "tools": [{"function_declarations": REST_TOOLS_DECLARATIONS}],
            "contents": history,
            "generationConfig": {
                "maxOutputTokens": 800,
                "temperature": 0.2
            }
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                
                # Trích xuất Token Usage từ Google API
                u_meta = res_data.get("usageMetadata", {})
                p_tok = u_meta.get("promptTokenCount", 0)
                c_tok = u_meta.get("candidatesTokenCount", 0)
                t_tok = u_meta.get("totalTokenCount", p_tok + c_tok)

                candidates = res_data.get("candidates", [])
                if not candidates:
                    continue
                
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    continue
                
                first_part = parts[0]

                # 1. Nếu Gemini yêu cầu gọi Tool (Function Calling)
                if "functionCall" in first_part:
                    fn_name = first_part["functionCall"].get("name")
                    fn_args = first_part["functionCall"].get("args", {})
                    tool_fn = TOOL_DISPATCH.get(fn_name)
                    
                    if tool_fn:
                        try:
                            tool_result = tool_fn(**fn_args)
                        except Exception as e_fn:
                            tool_result = f"Lỗi thực thi công cụ {fn_name}: {e_fn}"
                    else:
                        tool_result = f"Không tìm thấy công cụ {fn_name}"

                    # Ghi nhận Token Usage
                    try:
                        import token_tracker
                        token_tracker.record_token_usage(clean_model, p_tok, c_tok, t_tok)
                    except Exception:
                        pass

                    usage_dict = {
                        "model": clean_model,
                        "prompt_tokens": p_tok,
                        "response_tokens": c_tok,
                        "total_tokens": t_tok
                    }

                    # ═════════════════════════════════════════════════════════════════
                    # CẤM CHẾ BẢO VỆ DỮ LIỆU: BẮT BUỘC HỎI XÁC NHẬN - CHƯA ĐƯỢC PHÉP LƯU
                    # ═════════════════════════════════════════════════════════════════
                    if isinstance(tool_result, str) and (tool_result.startswith("❓") or tool_result.startswith("⚠️")):
                        history.append(content)
                        history.append({"role": "model", "parts": [{"text": tool_result}]})
                        LAST_KEY_ERROR = None
                        return {
                            "type": "clarify",
                            "module": "gemini_assistant",
                            "message": tool_result,
                            "usage": usage_dict
                        }

                    if isinstance(tool_result, str) and (tool_result.startswith("MISSING_PRICE:") or tool_result.startswith("MISSING_INFO:")):
                        clean_msg = tool_result.split(":", 1)[1].strip()
                        history.append(content)
                        history.append({"role": "model", "parts": [{"text": clean_msg}]})
                        LAST_KEY_ERROR = None
                        return {
                            "type": "clarify",
                            "module": "gemini_assistant",
                            "message": f"⚠️ {clean_msg}",
                            "usage": usage_dict
                        }

                    # Gửi kết quả Tool về lại Gemini để tổng hợp câu trả lời hoàn chỉnh (vòng 2)
                    history.append(content)
                    history.append({
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": fn_name,
                                "response": {"result": tool_result}
                            }
                        }]
                    })

                    payload_followup = {
                        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "tools": [{"function_declarations": REST_TOOLS_DECLARATIONS}],
                        "contents": history,
                        "generationConfig": {
                            "maxOutputTokens": 800,
                            "temperature": 0.2
                        }
                    }

                    try:
                        req_f = urllib.request.Request(
                            url,
                            data=json.dumps(payload_followup).encode("utf-8"),
                            headers={"Content-Type": "application/json"}
                        )
                        with urllib.request.urlopen(req_f, timeout=15) as resp_f:
                            res_f = json.loads(resp_f.read().decode("utf-8"))
                            u_f = res_f.get("usageMetadata", {})
                            p_tok += u_f.get("promptTokenCount", 0)
                            c_tok += u_f.get("candidatesTokenCount", 0)
                            t_tok += u_f.get("totalTokenCount", 0)

                            # Cập nhật lại token tổng cho vòng 2
                            try:
                                import token_tracker
                                token_tracker.record_token_usage(clean_model, p_tok, c_tok, t_tok)
                            except Exception:
                                pass

                            usage_dict["prompt_tokens"] = p_tok
                            usage_dict["response_tokens"] = c_tok
                            usage_dict["total_tokens"] = t_tok

                            cands_f = res_f.get("candidates", [])
                            if cands_f:
                                parts_f = cands_f[0].get("content", {}).get("parts", [])
                                txt_f = "\n".join([p.get("text", "") for p in parts_f if "text" in p]).strip()
                                if txt_f:
                                    history.append({"role": "model", "parts": [{"text": txt_f}]})
                                    LAST_KEY_ERROR = None
                                    return {
                                        "type": "success",
                                        "module": "gemini_assistant",
                                        "message": txt_f,
                                        "usage": usage_dict
                                    }
                    except Exception as e_f:
                        print(f"[GeminiEngine-REST] Lỗi vòng 2 functionResponse: {e_f}")

                    # Fallback trả thẳng kết quả Tool nếu vòng 2 gặp trục trặc
                    LAST_KEY_ERROR = None
                    return {
                        "type": "success",
                        "module": "gemini_assistant",
                        "message": str(tool_result),
                        "usage": usage_dict
                    }

                # 2. Nếu Gemini trả lời văn bản thông thường
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                reply_text = "\n".join(text_parts).strip()
                if reply_text:
                    history.append({"role": "model", "parts": [{"text": reply_text}]})
                    LAST_KEY_ERROR = None
                    try:
                        import token_tracker
                        token_tracker.record_token_usage(clean_model, p_tok, c_tok, t_tok)
                    except Exception:
                        pass
                    return {
                        "type": "success",
                        "module": "gemini_assistant",
                        "message": reply_text,
                        "usage": {
                            "model": clean_model,
                            "prompt_tokens": p_tok,
                            "response_tokens": c_tok,
                            "total_tokens": t_tok
                        }
                    }

        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            print(f"[GeminiEngine-REST] Lỗi HTTP {e.code} với model {clean_model}: {err_body[:150]}")
            if e.code == 403 or "leaked" in err_body.lower() or "permission_denied" in err_body.lower():
                LAST_KEY_ERROR = "API_KEY_LEAKED_403"
            elif e.code == 400 and ("invalid" in err_body.lower() or "api_key" in err_body.lower()):
                LAST_KEY_ERROR = "API_KEY_INVALID"
            continue
        except Exception as e:
            print(f"[GeminiEngine-REST] Lỗi kết nối model {clean_model}: {str(e)[:120]}")
            continue

    return None



def ask_gemini(message: str, session_id: str = "default_user") -> dict:

    """Xử lý câu lệnh hội thoại / điều khiển thông qua Gemini Flash với cơ chế Model Cascade.

    Hỗ trợ cả Google GenAI SDK (nếu có) lẫn Direct REST API (zero-dependency).

    """

    global LAST_KEY_ERROR

    set_current_session(session_id, user_message=message)



    # 1. Thử qua Google GenAI SDK nếu có

    if GENAI_AVAILABLE:

        for model_name in AVAILABLE_MODELS:

            chat = get_or_create_gemini_chat(session_id, model_name)

            if not chat:

                continue



            try:

                response = chat.send_message(message)

                text_resp = response.text or ""

                if text_resp.strip():

                    LAST_KEY_ERROR = None

                    return {

                        "type": "success",

                        "module": "gemini_assistant",

                        "message": text_resp.strip()

                    }

            except Exception as e:

                err_str = str(e)

                print(f"[GeminiEngine-SDK] Model {model_name} gặp lỗi: {err_str[:120]}")

                if "leaked" in err_str.lower() or "403" in err_str or "permission_denied" in err_str.lower():

                    LAST_KEY_ERROR = "API_KEY_LEAKED_403"

                elif "invalid" in err_str.lower() and "key" in err_str.lower():

                    LAST_KEY_ERROR = "API_KEY_INVALID"

                session_key = f"{session_id}_{model_name}"

                if session_key in GEMINI_SESSIONS:

                    del GEMINI_SESSIONS[session_key]

                continue



    # 2. Fallback sang Zero-Dependency REST API (hoạt động 100% trên PythonAnywhere mà không cần pip install)

    return ask_gemini_rest(message, session_id)


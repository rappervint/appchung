"""
auto_learner.py: HỆ THỐNG TỰ HỌC & HUẤN LUYỆN AI NỘI BỘ TỪ GEMINI
------------------------------------------------------------------
Gara Ô Tô Trần Bình Auto (Trần Bình Auto)

Chức năng:
1. Khi Gemini thực hiện thành công các mệnh lệnh (lên đơn đèn, sửa giá kho, ghi sổ thu chi, sửa/xóa đơn, đổi thông tin khách...):
   - Tự động bóc tách từ lóng, tên viết tắt, biệt danh sản phẩm (Ví dụ: "f1 turbo s" -> "TITAN F1 TURBO S", "f10 2.0 new" -> "Bi gầm F10 2.0 NEW")
   - Tự động học cấu trúc câu lệnh người dùng thường dùng (Pattern & Syntax Signature)
   - Lưu trữ vĩnh viễn vào SQLite (gara_knowledge.db)
2. FAST-PATH SIÊU TỐC (< 10ms):
   - Khi người dùng gửi câu lệnh tương tự hoặc dùng lại các từ ngữ đã học:
   - AI nội bộ nhận diện và sinh phiếu xác nhận NGAY LẬP TỨC mà KHÔNG CẦN gọi sang Google Gemini
   - Tăng tốc độ phản hồi gấp 100-300 lần (từ 2-3 giây giảm xuống còn ~5 mili-giây)
3. HOẠT ĐỘNG HOÀN TOÀN ĐỘC LẬP KHI MẤT MẠNG HOẶC KHÔNG CÒN GEMINI:
   - Càng trò chuyện và làm việc nhiều với Gemini, AI nội bộ càng thông minh lên và tích lũy tri thức riêng cho gara.
"""

import os
import re
import json
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_KNOWLEDGE = os.path.join(BASE_DIR, 'gara_knowledge.db')
DB_BANHANG = os.path.join(BASE_DIR, 'app_banhang', 'tiem_lap_do.db')
DB_DEN = os.path.join(BASE_DIR, 'app_baocao_den', 'doanhthu_den.db')
DB_THUCHI = os.path.join(BASE_DIR, 'app_thuchi', 'finance.db')

def remove_accents(input_str: str) -> str:
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
# 1. KHỞI TẠO BẢNG CƠ SỞ DỮ LIỆU TỰ HỌC (SQLITE)
# ─────────────────────────────────────────────────────────────────────────────

def init_learner_db():
    """Khởi tạo các bảng lưu trữ tri thức tự học trong gara_knowledge.db"""
    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()

        # Bảng 1: Biệt danh / từ lóng / tên viết tắt sản phẩm đã học
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,       -- 'lamp', 'product', 'car'
                alias TEXT NOT NULL,          -- Ví dụ: 'f1 turbo s', 'f10 new 2.0'
                canonical_name TEXT NOT NULL, -- Tên chuẩn: 'TITAN F1 TURBO S'
                canonical_code TEXT,          -- Mã SP: 'SP2734774'
                canonical_price REAL DEFAULT 0,
                hit_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                UNIQUE(category, alias)
            )
        """)

        # Bảng 2: Mẫu câu lệnh đã học (Patterns)
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent TEXT NOT NULL,         -- 'baocao_den', 'admin_update_stock', 'thuchi', 'sua_don', 'xoa_don'
                sample_prompt TEXT NOT NULL,  -- Câu lệnh gốc người dùng gõ
                clean_prompt TEXT NOT NULL,
                template_signature TEXT NOT NULL, -- Mẫu khái quát: 'lắp {lamp} cho xe {car} {plate} vào ngày {date}'
                extracted_data TEXT NOT NULL, -- JSON dữ liệu trích xuất thành công
                hit_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL
            )
        """)

        # Bảng 3: Đối thoại & giải đáp đã học từ Gemini
        c.execute("""
            CREATE TABLE IF NOT EXISTS learned_dialogues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                clean_question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                hit_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AutoLearner] Lỗi khởi tạo DB: {e}")

init_learner_db()

# Bộ nhớ đệm trong RAM để tra cứu < 0.1ms
CACHED_ALIASES = {}

def reload_aliases_cache():
    """Nạp toàn bộ biệt danh đã học vào RAM để tra cứu siêu tốc"""
    global CACHED_ALIASES
    if not os.path.exists(DB_KNOWLEDGE):
        return
    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()
        c.execute("SELECT category, alias, canonical_name, canonical_code, canonical_price FROM learned_aliases")
        rows = c.fetchall()
        conn.close()

        new_cache = {'lamp': {}, 'product': {}, 'car': {}}
        for cat, alias, cname, ccode, cprice in rows:
            if cat not in new_cache:
                new_cache[cat] = {}
            new_cache[cat][alias.lower().strip()] = {
                'canonical_name': cname,
                'canonical_code': ccode,
                'canonical_price': cprice
            }
        CACHED_ALIASES = new_cache

        # Đồng bộ vào LAMP_CATALOG của ai_assistant và gemini_engine nếu có
        sync_learned_lamps_to_catalog()
    except Exception as e:
        print(f"[AutoLearner] Lỗi tải cache alias: {e}")

def sync_learned_lamps_to_catalog():
    """Tự động bổ sung các đèn đã học vào LAMP_CATALOG runtime"""
    lamps = CACHED_ALIASES.get('lamp', {})
    if not lamps:
        return

    try:
        import ai_assistant
        import gemini_engine

        for alias, info in lamps.items():
            cname = info['canonical_name']
            p_k = int(info['canonical_price'] // 1000) if info['canonical_price'] > 1000 else int(info['canonical_price'])
            pat = r'\b' + re.escape(alias) + r'\b'

            # Kiểm tra xem đã có trong ai_assistant.LAMP_CATALOG chưa
            if hasattr(ai_assistant, 'LAMP_CATALOG'):
                exists = any(re.search(pat, p[0]) or p[1] == cname and alias in p[0] for p in ai_assistant.LAMP_CATALOG)
                if not exists:
                    ai_assistant.LAMP_CATALOG.insert(0, (pat, cname, p_k))

            # Kiểm tra xem đã có trong gemini_engine.LAMP_CATALOG chưa
            if hasattr(gemini_engine, 'LAMP_CATALOG'):
                exists = any(re.search(pat, p[0]) or p[1] == cname and alias in p[0] for p in gemini_engine.LAMP_CATALOG)
                if not exists:
                    gemini_engine.LAMP_CATALOG.insert(0, (pat, cname, p_k))
    except Exception as e:
        pass

reload_aliases_cache()

# ─────────────────────────────────────────────────────────────────────────────
# 2. HỌC TẬP TỪ THÀNH CÔNG CỦA GEMINI (TEACHING / LEARNING LOGIC)
# ─────────────────────────────────────────────────────────────────────────────

def learn_alias(category: str, raw_alias: str, canonical_name: str, canonical_code: str = "", canonical_price: float = 0):
    """Ghi nhận một từ lóng / tên viết tắt / biệt danh mới cho sản phẩm hoặc xe"""
    clean_al = remove_accents(raw_alias).lower().strip()
    clean_al = re.sub(r'^(?:bộ|đôi|cặp|bi|đèn)\s+', '', clean_al).strip()
    if not clean_al or len(clean_al) < 2:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()
        c.execute("""
            INSERT INTO learned_aliases (category, alias, canonical_name, canonical_code, canonical_price, hit_count, created_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(category, alias) DO UPDATE SET
                canonical_name=excluded.canonical_name,
                canonical_code=excluded.canonical_code,
                canonical_price=CASE WHEN excluded.canonical_price > 0 THEN excluded.canonical_price ELSE learned_aliases.canonical_price END,
                hit_count=learned_aliases.hit_count + 1,
                last_used_at=excluded.last_used_at
        """, (category, clean_al, canonical_name, canonical_code, canonical_price, now_str, now_str))
        conn.commit()
        conn.close()

        # Nạp lại RAM cache
        reload_aliases_cache()
    except Exception as e:
        print(f"[AutoLearner] Lỗi lưu alias: {e}")

def learn_pattern(intent: str, sample_prompt: str, template_sig: str, extracted_data: dict):
    """Ghi nhận một mẫu câu lệnh người dùng đã thực hiện thành công"""
    if not sample_prompt or len(sample_prompt.strip()) < 3:
        return

    clean_p = remove_accents(sample_prompt).lower().strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_json = json.dumps(extracted_data, ensure_ascii=False)

    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()
        c.execute("SELECT id, hit_count FROM learned_patterns WHERE clean_prompt=? AND intent=?", (clean_p, intent))
        row = c.fetchone()
        if row:
            c.execute("UPDATE learned_patterns SET hit_count=hit_count+1, last_used_at=?, extracted_data=? WHERE id=?",
                      (now_str, data_json, row[0]))
        else:
            c.execute("""
                INSERT INTO learned_patterns (intent, sample_prompt, clean_prompt, template_signature, extracted_data, hit_count, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """, (intent, sample_prompt, clean_p, template_sig, data_json, now_str, now_str))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AutoLearner] Lỗi lưu pattern: {e}")

def learn_from_successful_action(action_type: str, payload: dict):
    """
    HÀM ĐÓN ĐẦU ĐỂ DẠY LẠI AI NỘI BỘ:
    Được gọi ngay khi một hành động được xác nhận và thực thi thành công!
    Tự động suy diễn và nạp tri thức vào não AI nội bộ.
    """
    original_prompt = payload.get('original_prompt') or payload.get('sample_prompt') or ''
    if not original_prompt:
        return

    clean_p = remove_accents(original_prompt).lower().strip()

    # 1. HỌC TỪ ĐƠN BÁO CÁO ĐÈN (baocao_den)
    if action_type == 'baocao_den':
        items = payload.get('items', [])
        found_car = payload.get('found_car', '')
        plate = payload.get('plate', '')
        order_date = payload.get('order_date', '')

        for it in items:
            cname = it.get('product_name', '')
            final_k = it.get('final_price_k', 0)
            if cname:
                # Tìm phần đại diện cho tên đèn trong original_prompt
                # Ví dụ: 'lắp f1 turbo s cho xe city 63a36001 vào ngày 13/8/2026'
                # Sau khi gỡ bỏ xe, biển số, ngày, hành động, còn lại 'f1 turbo s'
                rem = clean_p
                for act in ['nhap don', 'len don', 'tao don', 'ghi don', 'chot don', 'lap', 'gan', 'thay', 'do', 'cho xe', 'cho', 'xe', 'con', 'vao ngay', 'vao', 'ngay', 'thang', 'nam', 'mua', 'ban', 'anh', 'chi', 'chu', 'bac']:
                    rem = re.sub(r'\b' + re.escape(act) + r'\b', ' ', rem)
                if plate:
                    rem = re.sub(r'\b' + re.escape(remove_accents(plate).lower()) + r'\b', ' ', rem)
                if found_car:
                    rem = re.sub(r'\b' + re.escape(remove_accents(found_car).lower()) + r'\b', ' ', rem)
                # Gỡ các ngày số dạng 13/8/2026 hay 13/08
                rem = re.sub(r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', ' ', rem)
                rem = re.sub(r'\b\d{1,2}\s*(?:thang|tháng|thg|t)\s*\d{1,2}(?:\s*(?:nam|năm)\s*\d{2,4})?\b', ' ', rem)
                rem = re.sub(r'^(?:cho|vao|xe|con)\s+', '', rem).strip()
                rem = re.sub(r'\s+(?:cho|vao|xe|con)$', '', rem).strip()
                rem = re.sub(r'\s+', ' ', rem).strip()

                if rem and len(rem) >= 2:
                    learn_alias('lamp', rem, cname, canonical_price=final_k * 1000)

                # Sinh template signature
                template_sig = clean_p
                if plate:
                    template_sig = re.sub(r'\b' + re.escape(remove_accents(plate).lower()) + r'\b', '{plate}', template_sig)
                if found_car:
                    template_sig = re.sub(r'\b' + re.escape(remove_accents(found_car).lower()) + r'\b', '{car}', template_sig)
                if rem:
                    template_sig = re.sub(r'\b' + re.escape(rem) + r'\b', '{lamp}', template_sig)

                learn_pattern(
                    intent='baocao_den',
                    sample_prompt=original_prompt,
                    template_sig=template_sig,
                    extracted_data={
                        'canonical_lamp': cname,
                        'price_k': final_k,
                        'car': found_car,
                        'plate': plate,
                        'date': order_date
                    }
                )

    # 2. HỌC TỪ CẬP NHẬT KHO HÀNG / GIÁ SẢN PHẨM (admin_update_stock / update_product_price)
    elif action_type in ('admin_update_stock', 'update_product_price'):
        kwargs = payload.get('kwargs', {})
        code = payload.get('code') or kwargs.get('ma_hoac_ten_sp', '')
        name = payload.get('name') or payload.get('matched_name', '')
        new_price = payload.get('new_price') or kwargs.get('gia_ban_moi', 0)
        raw_kw = payload.get('raw_product_kw', '')

        if name:
            if raw_kw:
                learn_alias('product', raw_kw, name, canonical_code=code, canonical_price=new_price)

            # Bóc tách tên sản phẩm trong câu
            rem = clean_p
            for act in ['sua lai gia', 'sua gia', 'doi gia', 'chinh gia', 'cap nhat gia', 'sua', 'doi', 'chinh', 'cap nhat', 'thanh', 'la', 'gia']:
                rem = re.sub(r'\b' + re.escape(act) + r'\b', ' ', rem)
            rem = re.sub(r'\b\d+(?:[.,]\d+)?\s*(?:tr|trieu|triệu|k|nghin|nghìn|vnd|đ|dong|đồng)?\b', ' ', rem)
            rem = re.sub(r'\s+', ' ', rem).strip()

            if rem and len(rem) >= 2:
                learn_alias('product', rem, name, canonical_code=code, canonical_price=new_price)

            learn_pattern(
                intent='admin_update_stock',
                sample_prompt=original_prompt,
                template_sig="sửa giá {product} thành {price}",
                extracted_data={
                    'canonical_name': name,
                    'code': code,
                    'new_price': new_price
                }
            )

    # 3. HỌC TỪ SỔ THU CHI (thuchi)
    elif action_type == 'thuchi':
        trans_type = payload.get('trans_type', 'chi')
        amount = payload.get('amount', 0)
        note = payload.get('note', '')
        date_str = payload.get('date_str', '')

        learn_pattern(
            intent='thuchi',
            sample_prompt=original_prompt,
            template_sig=f"{trans_type} {{amount}} {{note}}",
            extracted_data={
                'trans_type': trans_type,
                'amount': amount,
                'note': note,
                'date_str': date_str
            }
        )

    # 4. HỌC TỪ SỬA ĐƠN HÀNG / XÓA ĐƠN HÀNG (admin_edit_order / admin_delete_order)
    elif action_type in ('admin_edit_order', 'admin_delete_order'):
        learn_pattern(
            intent=action_type,
            sample_prompt=original_prompt,
            template_sig=clean_p,
            extracted_data=payload
        )

# ─────────────────────────────────────────────────────────────────────────────
# 3. BỘ SUY LUẬN SIÊU TỐC NỘI BỘ (FAST-PATH MATCHER < 10MS)
# ─────────────────────────────────────────────────────────────────────────────

def fast_match_learned_intent(raw_text: str, clean_text: str, session_id: str = "default_user") -> dict:
    """
    KIỂM TRA & XỬ LÝ SIÊU TỐC TỪ TRI THỨC ĐÃ HỌC:
    Được gọi TRƯỚC KHI gửi request sang Gemini!
    Nếu câu lệnh khớp với bất kỳ tri thức / từ lóng / mẫu câu nào đã học:
    -> Tự động nhận diện và trả về Phiếu Xác Nhận NGAY LẬP TỨC (thời gian xử lý ~5ms)!
    -> Tiết kiệm 100% thời gian chờ mạng và hoạt động được ngay cả khi Gemini offline.
    """
    if not raw_text or len(raw_text.strip()) < 2:
        return None

    clean = clean_text.strip().lower()

    # BẢO VỆ: Nếu là xác nhận hoặc hủy -> Để WIZARD_SESSIONS tiếp quản
    if clean in ['ok', 'luu', 'huy', 'cancel', 'dung', 'dong y', 'xac nhan']:
        return None

    # ═════════════════════════════════════════════════════════════════════════
    # FAST-PATH 1: LÊN ĐƠN BÁO CÁO ĐÈN (baocao_den)
    # Nhận diện khi người dùng ra lệnh lắp / gắn / thay / độ / nhập đơn đèn
    # ═════════════════════════════════════════════════════════════════════════
    is_lamp_order_intent = bool(re.search(r'\b(?:lap|gan|thay|do|nhap\s*don|len\s*don|tao\s*don|ghi\s*don|chot\s*don|ban\s*cap|len\s*cap|vao\s*cap|muc\s*doi)\b', clean))

    if is_lamp_order_intent:
        matched_lamp = None
        matched_price_k = 0

        # 1. Tra trong CACHED_ALIASES ('lamp') trước
        lamp_aliases = CACHED_ALIASES.get('lamp', {})
        for alias, info in sorted(lamp_aliases.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r'\b' + re.escape(alias) + r'\b', clean):
                matched_lamp = info['canonical_name']
                matched_price_k = int(info['canonical_price'] // 1000) if info['canonical_price'] > 1000 else int(info['canonical_price'])
                break

        # 2. Tra trong LAMP_CATALOG
        if not matched_lamp:
            try:
                from ai_assistant import LAMP_CATALOG
                for pat, cname, def_p in LAMP_CATALOG:
                    if re.search(pat, clean):
                        matched_lamp = cname
                        matched_price_k = def_p
                        break
            except Exception:
                pass

        if matched_lamp:
            # Bóc tách biển số xe
            plate = ""
            try:
                from ai_assistant import extract_license_plate
                plate = extract_license_plate(raw_text) or ""
            except Exception:
                pass

            # Bóc tách số điện thoại
            phone = ""
            try:
                from ai_assistant import extract_phone
                phone = extract_phone(raw_text) or ""
            except Exception:
                pass

            # Bóc tách ngày lắp đặt
            order_date = ""
            try:
                from ai_assistant import extract_date
                d_p, _ = extract_date(raw_text)
                order_date = d_p if d_p else datetime.now().strftime("%Y-%m-%d")
            except Exception:
                order_date = datetime.now().strftime("%Y-%m-%d")

            # Bóc tách dòng xe
            found_car = ""
            try:
                from ai_assistant import CAR_MODELS_LIST
                for c in CAR_MODELS_LIST:
                    if re.search(r'\b' + re.escape(c) + r'\b', clean, re.IGNORECASE):
                        found_car = c.upper()
                        break
            except Exception:
                pass

            # Tra cứu hồ sơ khách hàng & xe tự động từ biển số / SĐT
            cust_name = ""
            auto_found = False
            identifier = plate or phone
            if identifier:
                try:
                    from ai_assistant import lookup_customer_and_car_by_identifier
                    cust_info = lookup_customer_and_car_by_identifier(identifier)
                    if cust_info.get("found"):
                        auto_found = True
                        cust_name = cust_info.get("customer_name") or cust_name
                        if not found_car and cust_info.get("car_model"):
                            found_car = cust_info.get("car_model").upper()
                        if not phone and cust_info.get("phone"):
                            phone = cust_info.get("phone")
                except Exception:
                    pass

            # Nếu chưa có giá, tra cứu giá từ bộ nhớ
            if matched_price_k <= 0:
                try:
                    from ai_assistant import get_lamp_price_from_memory
                    p_mem = get_lamp_price_from_memory(matched_lamp)
                    if p_mem > 0:
                        matched_price_k = p_mem
                except Exception:
                    pass

            # Nếu vẫn không có giá niêm yết -> Bắt buộc hỏi lại giá
            if matched_price_k <= 0:
                return {
                    "type": "clarify",
                    "module": "fast_learner",
                    "message": f"⚠️ Sản phẩm **{matched_lamp}** hiện chưa có giá niêm yết trong hệ thống.\nAnh cho em xin mức giá thực tế để hoàn tất đơn hàng nhé!"
                }

            # Nếu xe mới chưa có tên khách và người dùng chưa nói tên khách -> Dừng lại hỏi thông tin
            if not cust_name and not plate and not phone:
                # Nếu câu không có bất kỳ định danh xe nào
                return None  # Nhường cho Gemini hoặc bộ máy hỏi đáp

            if not cust_name:
                cust_name = "KHÁCH LẺ"
            if not found_car:
                found_car = "CHƯA RÕ DÒNG XE"

            cust_record = f"{cust_name} ({plate})" if (plate and plate not in cust_name) else cust_name

            # Đăng ký phiên xác nhận WIZARD_SESSIONS
            from ai_assistant import WIZARD_SESSIONS
            WIZARD_SESSIONS[session_id] = {
                'flow': 'confirm_action',
                'action_type': 'baocao_den',
                'payload': {
                    'items': [{'product_name': matched_lamp, 'quantity': 1, 'final_price_k': matched_price_k, 'base_price_k': matched_price_k, 'discount_k': 0}],
                    'cust_name': cust_record,
                    'found_car': found_car,
                    'plate': plate,
                    'phone': phone,
                    'order_date': order_date,
                    'discount_k': 0,
                    'total_base_k': matched_price_k,
                    'total_final_k': matched_price_k,
                    'original_prompt': raw_text
                }
            }

            tag_auto = " *(Hồ sơ tự nhận diện)*" if auto_found else ""
            is_today = (order_date == datetime.now().strftime("%Y-%m-%d"))
            date_tag = " *(Hôm nay)*" if is_today else ""

            msg = (
                f"⚡ **[AI NỘI BỘ XỬ LÝ SIÊU TỐC - ĐÃ HỌC TỪ GEMINI]**\n"
                f"❓ **XÁC NHẬN TẠO ĐƠN VÀO SỔ BÁO CÁO DOANH THU ĐÈN:**\n"
                f"───────────────────────────────────────\n"
                f"• 👤 **Khách hàng:** **{cust_name}**{tag_auto}\n"
                f"• 🚗 **Dòng xe:** **{found_car}**\n"
                + (f"• 🚘 **Biển số:** **{plate}**\n" if plate else "")
                + (f"• 📞 **Số điện thoại:** **{phone}**\n" if phone else "")
                + f"• 📦 **Sản phẩm lắp đặt:**\n  1. **{matched_lamp}**: **{matched_price_k*1000:,.0f} đ ({matched_price_k:,}k)** *(Giá niêm yết tự động)*\n"
                f"• 💰 **DOANH THU THỰC THU:** **{matched_price_k*1000:,.0f} đ**\n"
                f"• 📅 **Ngày lắp:** **{order_date}**{date_tag}\n"
                f"───────────────────────────────────────\n"
                f"👉 Anh có chắc chắn muốn **LƯU ĐƠN HÀNG NÀY** vào hệ thống không?\n\n"
                f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào Báo Cáo Đèn | Nhắn **'hủy'** để bỏ qua)*"
            )

            return {
                "type": "clarify",
                "module": "fast_learner",
                "message": msg
            }

    # ═════════════════════════════════════════════════════════════════════════
    # FAST-PATH 2: CẬP NHẬT GIÁ SẢN PHẨM TRONG KHO (admin_update_stock)
    # Lệnh: "sửa giá f10 new 2.0 thành 4500", "đổi giá a510 thành 3tr5"
    # ═════════════════════════════════════════════════════════════════════════
    is_price_edit_intent = (
        any(k in clean for k in ['sua gia', 'sua lai gia', 'doi gia', 'cap nhat gia', 'chinh gia']) or \
        (any(k in clean for k in ['sua lai', 'doi lai', 'chinh lai']) and any(k in clean for k in ['thanh', 'la', 'gia', 'vnd', 'dong', 'k', 'tr']))
    ) and not bool(re.search(r'\b(?:don|ma don|#\d+)\b', clean))

    if is_price_edit_intent:
        from knowledge_base import parse_vietnamese_currency
        p_disp, p_val = parse_vietnamese_currency(raw_text)
        if p_val > 0:
            # Tra cứu sản phẩm trong kho thông qua bộ nhớ đã học
            prod_kw = raw_text
            for pat in [
                r'^(?:sửa\s*(?:lại\s*)?giá|sửa\s*giá\s*lại|đổi\s*(?:lại\s*)?giá|đổi\s*giá\s*lại|chỉnh\s*(?:lại\s*)?giá|chỉnh\s*giá\s*lại|cập\s*nhật\s*(?:lại\s*)?giá|cập\s*nhật\s*giá\s*lại|sửa\s*lại|chỉnh\s*lại|cập\s*nhật\s*lại|đổi\s*lại|sửa|đổi|chỉnh|cập\s*nhật)\s*',
            ]:
                prod_kw = re.sub(pat, '', prod_kw, flags=re.IGNORECASE).strip()

            for pat in [
                r'\s+(?:thành|thanh|là|la|giá|gia|giá\s*bán|gia\s*ban)\s+.*$',
                r'\s*[:=]\s*.*$',
                r'\s+\d+(?:[.,]\d+)?\s*(?:tr|trieu|triệu|k|nghin|nghìn|vnd|đ|dong|đồng).*$',
                r'\s+\d{3,7}\s*$',
            ]:
                prod_kw = re.sub(pat, '', prod_kw, flags=re.IGNORECASE).strip()

            if prod_kw:
                try:
                    from gemini_engine import find_product_in_inventory
                    target_prod = find_product_in_inventory(prod_kw, raw_text)
                    if target_prod:
                        prod_id, code, name, old_price, old_cost, old_stock, old_warranty = target_prod

                        from ai_assistant import WIZARD_SESSIONS
                        WIZARD_SESSIONS[session_id] = {
                            'flow': 'confirm_action',
                            'action_type': 'admin_update_stock',
                            'payload': {
                                'kwargs': {
                                    'ma_hoac_ten_sp': code,
                                    'ton_kho_moi': -999,
                                    'gia_ban_moi': p_val,
                                    'gia_von_moi': 0,
                                    'thoi_han_bao_hanh_thang': -999,
                                    'confirmed': True
                                },
                                'name': name,
                                'code': code,
                                'new_price': p_val,
                                'original_prompt': raw_text,
                                'raw_product_kw': prod_kw
                            }
                        }

                        msg = (
                            f"⚡ **[AI NỘI BỘ XỬ LÝ SIÊU TỐC - ĐÃ HỌC TỪ GEMINI]**\n"
                            f"❓ **XÁC NHẬN CẬP NHẬT DỮ LIỆU KHO HÀNG:**\n"
                            f"─────────────────────────────────────────\n"
                            f"• 📦 **Sản phẩm:** **{name}** (Mã: `{code}`)\n"
                            f"• Giá bán: từ **{old_price:,.0f} đ** ➔ **{p_val:,.0f} đ**\n"
                            f"• 📊 **Tồn kho hiện tại:** {old_stock} | **Bảo hành:** {old_warranty} tháng\n"
                            f"─────────────────────────────────────────\n"
                            f"👉 Anh có chắc chắn muốn lưu các thay đổi này vào phần mềm Bán Hàng không?\n\n"
                            f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'**, **'lưu'** để thực hiện | Bấm **[🛑 Hủy]** để bỏ qua)*"
                        )
                        return {
                            "type": "clarify",
                            "module": "fast_learner",
                            "message": msg
                        }
                except Exception:
                    pass

    # ═════════════════════════════════════════════════════════════════════════
    # FAST-PATH 3: GHI SỔ THU CHI (thuchi)
    # Lệnh: "chi 350k mua cơm trưa", "thu 500k tiền khách tip"
    # ═════════════════════════════════════════════════════════════════════════
    is_thuchi_cmd = bool(re.search(r'^(?:vừa\s+|da\s+)?(chi|thu)\s+.*', clean)) and \
                    not any(k in clean for k in ['doanh thu', 'doanh so', 'tong ket', 'bao nhieu', 'may don'])

    if is_thuchi_cmd:
        try:
            from knowledge_base import parse_vietnamese_currency
            p_disp, p_val = parse_vietnamese_currency(raw_text)
            if p_val > 0:
                clean_type = 'chi' if clean.startswith('chi') or ' chi ' in clean else 'thu'

                # Bóc tách nội dung chi
                note = raw_text
                note = re.sub(r'^(?:vừa\s+|đã\s+)?(?:chi|thu)\s+', '', note, flags=re.IGNORECASE).strip()
                note = re.sub(r'\b\d+(?:[.,]\d+)?\s*(?:tr|trieu|triệu|k|nghin|nghìn|vnd|đ|dong|đồng)?\b', '', note, flags=re.IGNORECASE).strip()
                note = re.sub(r'^(?:tiền|cho|về|khoản)?\s*', '', note, flags=re.IGNORECASE).strip()
                if not note:
                    note = f"Khoản {clean_type} ngày {datetime.now().strftime('%d/%m')}"

                # Bóc tách ngày
                date_str = ""
                from ai_assistant import extract_date
                d_p, _ = extract_date(raw_text)
                date_str = d_p if d_p else datetime.now().strftime("%Y-%m-%d")

                from ai_assistant import WIZARD_SESSIONS
                WIZARD_SESSIONS[session_id] = {
                    'flow': 'confirm_action',
                    'action_type': 'thuchi',
                    'payload': {
                        'trans_type': clean_type,
                        'amount': p_val,
                        'note': note.capitalize(),
                        'date_str': date_str,
                        'original_prompt': raw_text
                    }
                }

                type_label = "KHOẢN CHI TIỀN" if clean_type == 'chi' else "KHOẢN THU TIỀN"
                type_icon = "💸" if clean_type == 'chi' else "💵"
                amount_k_str = f"{p_val//1000:,}k" if p_val >= 1000 else f"{p_val:,}đ"

                msg = (
                    f"⚡ **[AI NỘI BỘ XỬ LÝ SIÊU TỐC - ĐÃ HỌC TỪ GEMINI]**\n"
                    f"❓ **XÁC NHẬN GHI SỔ THU CHI ({type_label}):**\n"
                    f"─────────────────────────────────────────\n"
                    f"• {type_icon} **Phân loại:** **{type_label}**\n"
                    f"• 💰 **Số tiền:** **{p_val:,.0f} đ** ({amount_k_str})\n"
                    f"• 📝 **Nội dung / Lý do:** **{note.capitalize()}**\n"
                    f"• 📅 **Ngày ghi nhận:** **{date_str}**\n"
                    f"─────────────────────────────────────────\n"
                    f"👉 Anh có chắc chắn muốn ghi {type_label.lower()} này vào Sổ Thu Chi không?\n\n"
                    f"*(Bấm nút **[✅ OK / Lưu]** hoặc nhắn **'ok'** để ghi vào sổ | Nhắn **'hủy'** để bỏ qua)*"
                )
                return {
                    "type": "clarify",
                    "module": "fast_learner",
                    "message": msg
                }
        except Exception:
            pass

    return None

# ─────────────────────────────────────────────────────────────────────────────
# 4. BÁO CÁO & THỐNG KÊ DANH SÁCH TRI THỨC ĐÃ TỰ HỌC
# ─────────────────────────────────────────────────────────────────────────────

def get_learning_stats() -> dict:
    """Lấy số liệu thống kê về quá trình tự học của AI nội bộ"""
    if not os.path.exists(DB_KNOWLEDGE):
        return {"total_aliases": 0, "total_patterns": 0, "total_memories": 0}

    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM learned_aliases")
        tot_al = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM learned_patterns")
        tot_pat = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM gara_memory")
        tot_mem = c.fetchone()[0] or 0
        conn.close()
        return {
            "total_aliases": tot_al,
            "total_patterns": tot_pat,
            "total_memories": tot_mem
        }
    except Exception:
        return {"total_aliases": 0, "total_patterns": 0, "total_memories": 0}

def list_learned_skills() -> dict:
    """Hiển thị danh sách toàn bộ từ lóng, biệt danh và mẫu lệnh AI nội bộ đã tự học từ Gemini"""
    if not os.path.exists(DB_KNOWLEDGE):
        return {"type": "info", "message": "🧠 Bộ não tự học của AI hiện đang sẵn sàng tiếp thu các câu lệnh mới!"}

    try:
        conn = sqlite3.connect(DB_KNOWLEDGE, timeout=5)
        c = conn.cursor()
        c.execute("SELECT category, alias, canonical_name, hit_count, last_used_at FROM learned_aliases ORDER BY hit_count DESC, id DESC LIMIT 20")
        aliases = c.fetchall()

        c.execute("SELECT intent, sample_prompt, hit_count, last_used_at FROM learned_patterns ORDER BY hit_count DESC, id DESC LIMIT 10")
        patterns = c.fetchall()
        conn.close()

        msg = "🧠 **BỘ NÃO TỰ HỌC CỦA AI NỘI BỘ GARA (ĐÃ HỌC TỪ GEMINI):**\n"
        msg += "─────────────────────────────────────────\n"
        msg += "⚡ *Các câu lệnh này AI nội bộ đã hiểu và tự thực hiện tức thì (< 0.01s) mà không cần hỏi Gemini:*\n\n"

        if aliases:
            msg += "📌 **Từ lóng & Biệt danh sản phẩm đã học:**\n"
            for cat, al, cname, hits, u_at in aliases:
                cat_tag = "Đèn" if cat == 'lamp' else "Sản phẩm"
                msg += f"• `{al}` ➔ **{cname}** *({cat_tag} - Dùng {hits} lần)*\n"
            msg += "\n"

        if patterns:
            msg += "📋 **Mẫu câu lệnh người dùng đã thuần thục:**\n"
            for it, sp, hits, u_at in patterns:
                msg += f"• *\"{sp}\"* ({it} - {hits} lần)\n"
            msg += "\n"

        if not aliases and not patterns:
            msg += "Hiện tại AI chưa tích lũy lệnh nào. Khi anh trò chuyện và tạo đơn cùng Gemini, AI sẽ tự động ghi nhớ ngay!\n"

        msg += "─────────────────────────────────────────\n"
        msg += "💡 *Mỗi lần anh thực hiện thành công lệnh qua Gemini, AI nội bộ sẽ tự động nâng cấp độ thông minh lên ngay lập tức.*"
        return {"type": "success", "message": msg}
    except Exception as e:
        return {"type": "error", "message": f"Lỗi truy xuất bộ nhớ tự học: {e}"}

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

CURRENT_CONFIG = load_gemini_config()
DEFAULT_API_KEY = CURRENT_CONFIG.get("api_key", "")
# Danh sách model siêu tốc: Gemini 3.5 Flash Lite và Gemini 3.5 Flash
AVAILABLE_MODELS = [
    CURRENT_CONFIG.get("preferred_model", "gemini-3.5-flash-lite"),
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
    ngay_moi: str = ""
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
                updated_info.append(f"Khách hàng: **{ten_khach_moi}**")
            if dong_xe_moi:
                fields_to_update.append("car_model=?")
                vals.append(dong_xe_moi.strip().upper())
                updated_info.append(f"Dòng xe: **{dong_xe_moi.upper()}**")
            if ten_san_pham_moi:
                fields_to_update.append("product_name=?")
                vals.append(ten_san_pham_moi.strip().upper())
                updated_info.append(f"Tên đèn/sản phẩm: **{ten_san_pham_moi.upper()}**")
            if gia_tien_moi > 0:
                p_k = int(gia_tien_moi / 1000) if gia_tien_moi > 50000 else int(gia_tien_moi)
                fields_to_update.append("price_k=?")
                vals.append(p_k)
                updated_info.append(f"Đơn giá đèn: **{p_k:,}k** ({p_k * 1000:,} đ)")
            if ngay_moi:
                fields_to_update.append("order_date=?")
                vals.append(ngay_moi.strip())
                updated_info.append(f"Ngày ghi nhận: **{ngay_moi}**")

            if fields_to_update:
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
                updated_info.append(f"Tên khách hàng: **{ten_khach_moi.upper()}**")
            if sdt_moi:
                clean_phone = re.sub(r'[^0-9]', '', sdt_moi)
                fields_to_update.append("phone=?")
                vals.append(clean_phone)
                updated_info.append(f"Số điện thoại: **{clean_phone}**")
            if bien_so_moi:
                clean_plate = bien_so_moi.strip().upper()
                fields_to_update.append("license_plate=?")
                vals.append(clean_plate)
                updated_info.append(f"Biển số xe: **{clean_plate}**")
            if ngay_moi:
                fields_to_update.append("install_date=?")
                vals.append(ngay_moi.strip())
                updated_info.append(f"Ngày lắp đặt: **{ngay_moi}**")
            if gia_tien_moi > 0:
                p_val = gia_tien_moi if gia_tien_moi > 10000 else gia_tien_moi * 1000
                fields_to_update.append("total_price=?")
                vals.append(p_val)
                updated_info.append(f"Tổng tiền đơn hàng: **{p_val:,.0f} đ**")

            if ten_san_pham_moi:
                c.execute("UPDATE order_items SET item_name=? WHERE order_id=?", (ten_san_pham_moi.strip(), ma_don_hang))
                updated_info.append(f"Sản phẩm / Món lắp: **{ten_san_pham_moi}**")

            if fields_to_update or ten_san_pham_moi:
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


def xoa_don_hang(ma_don_hang: int, loai_don: str = "auto") -> str:
    """Xóa hoặc hủy một đơn hàng khỏi hệ thống (cả Bán Hàng và Báo Cáo Đèn).

    Args:
        ma_don_hang: Mã số đơn hàng cần xóa (ví dụ: 747, 8585).
        loai_don: 'auto', 'den' hoặc 'banhang'.
    """
    # 1. Thử xóa bên Báo Cáo Đèn
    if loai_don in ("auto", "den") and os.path.exists(DB_DEN):
        conn = sqlite3.connect(DB_DEN)
        c = conn.cursor()
        c.execute("SELECT id, product_name, customer_name, car_model, price_k FROM orders WHERE id=?", (ma_don_hang,))
        row = c.fetchone()
        if row:
            c.execute("DELETE FROM orders WHERE id=?", (ma_don_hang,))
            conn.commit()
            conn.close()
            return f"🗑️ **ĐÃ XÓA THÀNH CÔNG ĐƠN ĐÈN #{ma_don_hang}!**\n• Món: {row[1]} ({row[4]}k)\n• Khách: {row[2]} ({row[3]})\n👉 Đơn hàng đã được gỡ bỏ khỏi Sổ Doanh Thu Đèn."
        conn.close()

    # 2. Thử xóa bên Bán Hàng
    if loai_don in ("auto", "banhang") and os.path.exists(DB_BANHANG):
        conn = sqlite3.connect(DB_BANHANG)
        c = conn.cursor()
        c.execute("SELECT id, customer_name, license_plate, total_price FROM orders WHERE id=?", (ma_don_hang,))
        row = c.fetchone()
        if row:
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
    thoi_han_bao_hanh_thang: int = -999
) -> str:
    """Cập nhật số lượng tồn kho, giá bán, giá vốn hoặc thời hạn bảo hành của sản phẩm trong kho.

    Args:
        ma_hoac_ten_sp: Mã sản phẩm (ví dụ: 'SP2734853', 'A310') hoặc tên sản phẩm.
        ton_kho_moi: Số lượng tồn kho mới (nếu muốn điều chỉnh tồn kho).
        gia_ban_moi: Giá bán lẻ mới (VNĐ).
        gia_von_moi: Giá vốn nhập vào mới (VNĐ).
        thoi_han_bao_hanh_thang: Thời gian bảo hành tính theo tháng (ví dụ: 12, 24).
    """
    if not os.path.exists(DB_BANHANG):
        return "⚠️ Không tìm thấy cơ sở dữ liệu kho hàng."

    conn = sqlite3.connect(DB_BANHANG)
    c = conn.cursor()

    kw = ma_hoac_ten_sp.strip()
    c.execute("SELECT id, code, name, price, cost_price, stock, warranty_months FROM products WHERE UPPER(code)=UPPER(?) OR UPPER(name) LIKE UPPER(?) LIMIT 5", (kw, f"%{kw}%"))
    rows = c.fetchall()

    if not rows:
        conn.close()
        return f"⚠️ Không tìm thấy sản phẩm nào khớp với từ khóa **'{kw}'** trong kho hàng."

    target_prod = rows[0]
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
    bien_so_moi: str = ""
) -> str:
    """Cập nhật thông tin khách hàng (Tên, Số điện thoại, Biển số xe) đồng bộ trên tất cả đơn hàng đã lưu.

    Args:
        dinh_danh_cu: Biển số xe cũ (ví dụ '63A-187.30'), Số điện thoại cũ (ví dụ '0906648540'), hoặc Tên khách cũ.
        ten_moi: Tên mới cần đổi.
        sdt_moi: Số điện thoại mới cần đổi.
        bien_so_moi: Biển số xe mới cần đổi.
    """
    kw = dinh_danh_cu.strip().upper()
    total_updated = 0

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

    if total_updated == 0:
        return f"⚠️ Không tìm thấy khách hàng nào khớp với định danh **'{dinh_danh_cu}'** để cập nhật."

    changes = []
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
    ngay: str = ""
) -> str:
    """Ghi nhanh khoản chi hoặc thu vào sổ quỹ tài chính.

    Args:
        loai: 'chi' hoặc 'thu'.
        so_tien: Số tiền VNĐ (ví dụ 100000, 350000).
        noi_dung: Lý do hoặc nội dung chi/thu (ví dụ 'mua đồ ăn trưa', 'mua băng keo', 'khách tip').
        ngay: Ngày phát sinh (YYYY-MM-DD), nếu để trống lấy ngày hôm nay.
    """
    if not os.path.exists(DB_THUCHI):
        return "⚠️ Không tìm thấy cơ sở dữ liệu sổ thu chi."

    now_date = ngay if ngay else datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    created_at = f"{now_date} {now_time}"

    conn = sqlite3.connect(DB_THUCHI)
    c = conn.cursor()
    c.execute("SELECT id FROM periods WHERE status='open' ORDER BY id DESC LIMIT 1")
    p_row = c.fetchone()
    period_id = p_row[0] if p_row else 1

    clean_type = 'chi' if 'chi' in loai.lower() else 'thu'
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
    gia_tien_k: int,
    khach_hang: str = "KHÁCH LẺ",
    dong_xe: str = "Chưa rõ dòng xe",
    so_luong: int = 1,
    ngay: str = ""
) -> str:
    """Lên đơn nhanh vào Sổ Báo Cáo Doanh Thu Đèn khi khách hàng chốt đơn lắp đèn.

    Args:
        ten_den: Tên sản phẩm đèn (ví dụ: 'F10 NEW 2.0', 'F10 TURBO', 'S3', 'M40 ULTRA').
        gia_tien_k: Giá thu thực tế theo đơn vị nghìn đồng (ví dụ 3900 cho 3.9 triệu, 5100 cho 5.1 triệu).
        khach_hang: Tên khách hàng (ví dụ 'Anh Cường', 'Anh Hùng', hoặc 'KHÁCH LẺ').
        dong_xe: Dòng xe của khách (ví dụ 'ACCENT', 'VIOS', 'VF3').
        so_luong: Số lượng bộ đèn (mặc định 1).
        ngay: Ngày lắp đặt (YYYY-MM-DD), nếu trống lấy hôm nay.
    """
    if not os.path.exists(DB_DEN):
        return "⚠️ Không tìm thấy cơ sở dữ liệu Báo Cáo Đèn."

    order_date = ngay if ngay else datetime.now().strftime("%Y-%m-%d")
    p_k = int(gia_tien_k / 1000) if gia_tien_k > 50000 else int(gia_tien_k)

    conn = sqlite3.connect(DB_DEN)
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (order_date, product_name, customer_name, car_model, quantity, price_k, sheet_origin) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (order_date, ten_den.strip().upper(), khach_hang.strip(), dong_xe.strip().upper(), so_luong, p_k, "AI_GEMINI_DIRECT")
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return (
        f"💡 **ĐÃ GHI NHẬN ĐƠN BÁO CÁO ĐÈN THÀNH CÔNG!**\n"
        f"─────────────────────────────────────────\n"
        f"• Mã đơn: **#{new_id}**\n"
        f"• Khách hàng: **{khach_hang}** | Xe: **{dong_xe.upper()}**\n"
        f"• Đèn lắp: **{ten_den.upper()}** (SL: {so_luong})\n"
        f"• Doanh thu: **{p_k * 1000:,.0f} đ** ({p_k:,}k)\n"
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
9. LÊN ĐƠN BÁO CÁO ĐÈN: Khi người dùng chốt bán hoặc lắp đèn cụ thể cho khách/xe kèm giá tiền (ví dụ: "anh Cường accent f10 new 3900"), hãy gọi `len_don_bao_cao_den_nhanh`.
   ⚠️ LƯU Ý BẢO VỆ: Nếu người dùng CHỈ gõ tên đèn để hỏi giá hoặc tư vấn (như "f10", "f10 turbo", "đèn gầm"), TUYỆT ĐỐI KHÔNG LÊN ĐƠN, mà hãy trả lời tư vấn & báo giá chi tiết!

╔══════════════════════════════════════════════════════════════════════╗
║               KIẾN THỨC NGHIỆP VỤ & BÁO GIÁ GARA CHÍNH HÃNG          ║
╚══════════════════════════════════════════════════════════════════════╝
• CAMERA 360 ĐỘ:
  - Phân loại rõ ràng:
    + Camera 360 rời cắm giắc zin màn hình gốc theo xe (giữ zin 100%): Camera 360 Owin (8.5tr - 16.1tr, mắt cam Sony ban đêm siêu nét, bản cho VF3 không CarPlay 8.5tr, có CarPlay 9.5tr), DCT T1/T2 Pro (12.8tr - 15.8tr).
    + Màn hình Android liền Cam 360 độ: Winca S170+ (10.5tr - 11.8tr - bán chạy), Gotech GC360 / GT2K 360 (12.9tr - 19.9tr).
  - ⛔ ĐẶC BIỆT: Gara ĐÃ NGỪNG KINH DOANH dòng Camera 360 TexPad!

• ĐÈN GẦM / BI GẦM NÂNG CẤP ÁNH SÁNG:
  - Bi Gầm LED F10 Series (Chính hãng Aozoom - Bán chạy số 1):
    + F10 New 2.0 (Tiêu chuẩn): 3.900.000 đ
    + F10 Ba Màu (3000K/4300K/5500K - Chuyên phá sương): 4.200.000 đ - 4.500.000 đ
    + F10 Turbo V2 (Công suất khủng có trợ pha): 5.100.000 đ - 6.000.000 đ
    + F10 Hyper 2.0 / F10 Pro V2: 5.500.000 đ
  - Phân khúc khác: Naoevo S3 (1.5tr), S6 (1.8tr - 2tr), Bi LED Pha V20/V20 Ultra (5.85tr - 6.5tr), M30/M40 Ultra (5.5tr - 6.5tr), Titan Gold (6.75tr).

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

REST_CHAT_HISTORY = {}

def ask_gemini_rest(message: str, session_id: str = "default_user") -> dict:
    """Xử lý Gemini trực tiếp qua chuẩn REST API của Google (Zero-Dependency).
    Hoạt động 100% trên mọi nền tảng (PythonAnywhere, VPS, Docker, Windows, Linux)
    mà không cần bất kỳ thư viện bên ngoài nào.
    """
    global LAST_KEY_ERROR
    api_key = DEFAULT_API_KEY
    if not api_key:
        return None

    if session_id not in REST_CHAT_HISTORY:
        REST_CHAT_HISTORY[session_id] = []
    
    history = REST_CHAT_HISTORY[session_id]
    history.append({"role": "user", "parts": [{"text": message}]})
    if len(history) > 12:
        history = history[-12:]
        REST_CHAT_HISTORY[session_id] = history

    for model_name in AVAILABLE_MODELS:
        clean_model = model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
        
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
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
                
                candidates = res_data.get("candidates", [])
                if not candidates:
                    continue
                
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    continue
                
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                reply_text = "\n".join(text_parts).strip()
                
                if reply_text:
                    history.append({"role": "model", "parts": [{"text": reply_text}]})
                    LAST_KEY_ERROR = None
                    return {
                        "type": "success",
                        "module": "gemini_assistant",
                        "message": reply_text
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

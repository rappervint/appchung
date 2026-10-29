import re
from ai_assistant import process_ai_command

test_cases = [
    # 1. Câu lệnh từ ảnh 1 của khách
    ("nhập đơn f10 new 2.0 63A18730", "ORDER", ["F10 NEW 2.0", "63A18730", "4,500,000", "Tuyết Nguyễn"]),
    
    # 2. Câu lệnh từ ảnh 3 của khách (kèm ngày cụ thể)
    ("lắp f1 turbo s cho xe city 63a36001 vào ngày 13/8/2026", "ORDER", ["TITAN F1 TURBO S", "63A36001", "CITY", "2026-08-13"]),
    
    # 3. Câu lệnh đảo trật tự, từ lóng 'lên cặp', giá viết tắt 4tr2
    ("anh Tuấn vios lên cặp f10 new 4tr2", "ORDER", ["Anh Tuấn", "VIOS", "F10 NEW 2.0", "4,200,000"]),
    
    # 4. Câu lệnh phức tạp, ngày hôm qua, thu 6 triệu
    ("thay cặp bi gầm cho anh dũng xe camry f10 turbo v2 thu 6 triệu ngày hôm qua", "ORDER", ["Anh Dũng", "CAMRY", "F10 TURBO", "6,000,000"]),
    
    # 5. Câu lệnh qua trợ lý ảo giọng nói có từ đệm
    ("alo trợ lý ơi ghi giúp anh đơn bi gầm f10 new 2.0 cho xe 63A18730 nhé", "ORDER", ["F10 NEW 2.0", "63A18730", "Tuyết Nguyễn", "4,500,000"]),
    
    # 6. Khẩu ngữ gara: 'bắn cặp ... vào con ...'
    ("bắn cặp f10 new vào con vios 63A18730 thu 4tr5", "ORDER", ["F10 NEW 2.0", "63A18730", "4,500,000"]),
    
    # 7. Khẩu ngữ gara: 'vừa làm xong xe ... bi f10 new 4500k'
    ("vừa làm xong xe 63A-18730 bi f10 new 4500k", "ORDER", ["F10 NEW 2.0", "18730", "4,500,000"]),
    
    # 8. Khách đặc biệt: 'mua về tự ráp'
    ("bán cặp f10 new cho thợ mua về tự ráp 3tr5", "ORDER", ["F10 NEW 2.0", "MUA VỀ", "3,500,000"]),
    
    # 9. Đèn S3, biển số, ngày cụ thể
    ("xe 63A18730 độ bi gầm s3 1500k ngày 20/10/2026", "ORDER", ["S3", "63A18730", "1,500,000", "2026-10-20"]),
    
    # 10. Chốt đơn chú Bảy fortuner
    ("chốt đơn bi gầm f10 pro v2 cho chú bảy fortuner", "ORDER", ["Chú Bảy", "FORTUNER", "F10 PRO", "5,500,000"]),
    
    # 11. Bóc tách SĐT, đèn V20, không được biến 'bóng' thành tên khách
    ("0909123456 thay bóng v20 giá 5tr5", "ORDER", ["0909123456", "V20", "5,500,000"]),
    
    # 12. Titan F1 GT xe Ranger thu 4 triệu rưỡi
    ("lên đôi bi titan f1 gt cho xe ranger 63C12345 thu 4 triệu rưỡi", "ORDER", ["TITAN F1 GT", "RANGER", "63C12345", "4,500,000"]),
    
    # 13. Khẩu ngữ 'múc cặp bi led gầm g1 turbo...'
    ("múc cặp bi led gầm g1 turbo cho anh hoàng 0912345678 giá 6tr2", "ORDER", ["G1 TURBO", "Anh Hoàng", "0912345678", "6,200,000"]),
    
    # 14. Vắn tắt: đèn + biển số
    ("f10 new 2.0 63A18730", "ORDER", ["F10 NEW 2.0", "63A18730", "Tuyết Nguyễn"]),
    
    # 15. Vắn tắt: đèn + xe + giá
    ("s3 vf3 1tr5", "ORDER", ["S3", "VF3", "1,500,000"]),
    
    # 16. Hỏi giá / tư vấn thuần túy từ ảnh 2 của khách (KHÔNG ĐƯỢC TẠO ĐƠN)
    ("f10 2.0", "CONSULT", ["BÁO GIÁ BI GẦM F10", "4,500,000"]),
    
    # 17. Tư vấn thuần túy (KHÔNG ĐƯỢC TẠO ĐƠN)
    ("tư vấn bi gầm f10", "CONSULT", ["BÁO GIÁ BI GẦM F10"]),
    
    # 18. Hỏi giá bao nhiêu (KHÔNG ĐƯỢC TẠO ĐƠN)
    ("bi gầm f10 giá bao nhiêu", "STOCK", ["F10"]),
    
    # 19. Báo cáo doanh thu đèn tháng 8/2026 (KHÔNG ĐƯỢC TẠO ĐƠN)
    ("doanh thu đèn tháng 8/2026", "REPORT", ["DOANH THU", "ĐÈN"]),
    
    # 20. Báo cáo doanh thu toàn cửa hàng tháng 8 năm 2026 (KHÔNG ĐƯỢC TẠO ĐƠN)
    ("tháng 8 năm 2026 bán được bao nhiêu đơn", "REPORT", ["BÁO CÁO", "Tháng 8/2026"])
]

print("=" * 70)
print(f"BẮT ĐẦU CHẠY KIỂM THỬ {len(test_cases)} TÌNH HUỐNG THỰC TẾ GARA Ô TÔ")
print("=" * 70)

all_passed = True
for idx, (cmd, expected_type, expected_keywords) in enumerate(test_cases, 1):
    res = process_ai_command(cmd, session_id=f"test_session_{idx}")
    msg = res.get('message', '') if res else ''
    
    passed = True
    reasons = []
    
    if expected_type == "ORDER":
        if "XÁC NHẬN TẠO ĐƠN" not in msg and "CHƯA CÓ THÔNG TIN KHÁCH HÀNG" not in msg:
            passed = False
            reasons.append("Không nhận diện đúng ý định tạo đơn đèn!")
    elif expected_type == "CONSULT":
        if "XÁC NHẬN TẠO ĐƠN" in msg:
            passed = False
            reasons.append("Lỗi: Câu hỏi tư vấn nhưng lại kích hoạt tạo đơn!")
    elif expected_type == "REPORT":
        if "XÁC NHẬN TẠO ĐƠN" in msg:
            passed = False
            reasons.append("Lỗi: Câu hỏi báo cáo nhưng lại kích hoạt tạo đơn!")
            
    for kw in expected_keywords:
        if kw.lower() not in msg.lower():
            passed = False
            reasons.append(f"Thiếu thông tin quan trọng: '{kw}'")
            
    status = "✅ PASS" if passed else "❌ FAIL"
    if not passed:
        all_passed = False
    print(f"[{idx:02d}] {status} | Lệnh: '{cmd}'")
    if not passed:
        print(f"     => Lý do: {', '.join(reasons)}")
        print(f"     => Phản hồi thực tế: {msg[:160]}...")

print("=" * 70)
if all_passed:
    print("🎉 TẤT CẢ 20 TÌNH HUỐNG ĐỀU ĐẠT CHUẨN 100%! AI HOẠT ĐỘNG HOÀN HẢO!")
else:
    print("⚠️ CÒN TÌNH HUỐNG CẦN TINH CHỈNH TIẾP.")
print("=" * 70)

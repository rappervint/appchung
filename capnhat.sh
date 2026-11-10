#!/bin/bash
# ==============================================================================
# SCRIPT CẬP NHẬT TỰ ĐỘNG SIÊU TỐC CHO PYTHONANYWHERE
# Chạy lệnh: ~/capnhat.sh hoặc ./capnhat.sh
# Tác dụng: Kéo code mới nhất từ GitHub + Khởi động lại (Reload) Web app ngay lập tức!
# ==============================================================================

echo "=================================================="
echo "🚀 ĐANG CẬP NHẬT HỆ THỐNG APP CHUNG TỪ GITHUB..."
echo "=================================================="

# 1. Chuyển vào thư mục dự án (hỗ trợ cả tài khoản vint và rappervint)
if [ -d "/home/vint/appchung" ]; then
    cd /home/vint/appchung
elif [ -d "/home/rappervint/appchung" ]; then
    cd /home/rappervint/appchung
fi

# 2. Kéo code mới nhất từ nhánh main trên GitHub (tự động xóa xung đột tạm thời)
rm -f token_usage.json
git checkout -- knowledge_seed.json 2>/dev/null || true
git fetch origin main
git reset --hard origin/main

# Tự động đồng bộ tri thức chuẩn từ knowledge_seed.json
python3 -c "import knowledge_base; knowledge_base.init_knowledge_db()" 2>/dev/null || true

# Tự động sửa các số điện thoại bị lỗi .0 trong database cũ nếu có
python3 fix_pa_phones.py 2>/dev/null || true

# 3. Chạm vào file WSGI để PythonAnywhere tự động Reload web (không cần bấm chuột trên web)
[ -f /var/www/vint_pythonanywhere_com_wsgi.py ] && touch /var/www/vint_pythonanywhere_com_wsgi.py
[ -f /var/www/rappervint_pythonanywhere_com_wsgi.py ] && touch /var/www/rappervint_pythonanywhere_com_wsgi.py

echo "=================================================="
echo "🎉 CẬP NHẬT HOÀN TẤT VÀ ĐÃ RELOAD WEB THÀNH CÔNG!"
echo "👉 Truy cập ngay kiểm tra app!"
echo "=================================================="

#!/bin/bash
# ==============================================================================
# SCRIPT CẬP NHẬT TỰ ĐỘNG SIÊU TỐC CHO PYTHONANYWHERE
# Chạy lệnh: ~/capnhat.sh hoặc ./capnhat.sh
# Tác dụng: Kéo code mới nhất từ GitHub + Khởi động lại (Reload) Web app ngay lập tức!
# ==============================================================================

echo "=================================================="
echo "🚀 ĐANG CẬP NHẬT HỆ THỐNG APP CHUNG TỪ GITHUB..."
echo "=================================================="

# 1. Chuyển vào thư mục dự án
cd /home/rappervint/appchung || exit 1

# 2. Kéo code mới nhất từ nhánh main trên GitHub
git pull origin main

# 3. Chạm vào file WSGI để PythonAnywhere tự động Reload web (không cần bấm chuột trên web)
touch /var/www/rappervint_pythonanywhere_com_wsgi.py

echo "=================================================="
echo "🎉 CẬP NHẬT HOÀN TẤT VÀ ĐÃ RELOAD WEB THÀNH CÔNG!"
echo "👉 Truy cập ngay: https://rappervint.pythonanywhere.com"
echo "=================================================="


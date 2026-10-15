@echo off
chcp 65001 >nul
title HE THONG QUAN LY TONG HOP - TRẦN BÌNH AUTO
color 1F

:: Chuyen ve dung thu muc goc chua ung dung
cd /d "%~dp0"

cls
echo.
echo  ==========================================================================
echo         🚗 HỆ THỐNG QUẢN LÝ GARA Ô TÔ TRẦN BÌNH AUTO (HỢP NHẤT 3 ỨNG DỤNG)
echo  ==========================================================================
echo.
echo    [1] Máy chủ đang khởi động trên máy tính của bạn...
echo    [2] Trình duyệt sẽ tự động mở trang chủ sau 2 giây...
echo.
echo  --------------------------------------------------------------------------
echo    🌐 TÊN MIỀN TRUY CẬP NỘI BỘ (ĐIỆN THOẠI / IPAD / MÁY TÍNH CÙNG WI-FI):
echo  --------------------------------------------------------------------------
echo    👉 Cổng chính Hub :  http://appchung.local:5000
echo    👉 Bán Hàng & Kho :  http://appchung.local:5000/banhang/
echo    👉 Doanh Thu Đèn  :  http://appchung.local:5000/den/
echo    👉 Sổ Thu Chi     :  http://appchung.local:5000/thuchi/
echo.
echo    💻 Máy tính này   :  http://localhost:5000
echo  --------------------------------------------------------------------------
echo    ⌨️  BẢNG PHÍM TẮT THAO TÁC:
echo  --------------------------------------------------------------------------
echo    • [Ctrl + C]      : Dừng / Tắt máy chủ an toàn
echo    • [F5] / [Ctrl+R] : Tải lại trang web trên trình duyệt
echo    • [Bôi đen chuột] : Sao chép đường link truy cập
echo  ==========================================================================
echo.

:: Tu dong mo trinh duyet sau 2 giay
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: Khoi chay Flask server
python -u app.py

if %errorlevel% neq 0 (
    echo.
    echo  [!] May chu da dung lai hoac gap su co.
    echo.
    pause
)

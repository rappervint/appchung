@echo off
chcp 65001 >nul
title DOANH THU DEN - SERVER
color 1F

:: Chuyen ve thu muc goc chua ung dung
cd /d "%~dp0"

:: Tu dong mo trinh duyet sau 2 giay
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: Khoi chay Flask app voi unbuffered logging
python -u app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Ung dung da dung lai.
    pause
)

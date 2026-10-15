"""
╔══════════════════════════════════════════════════════════════════════╗
║              WSGI CONFIGURATION FILE CHO PYTHONANYWHERE             ║
║                                                                      ║
║  Trong tab Web trên PythonAnywhere, click vào link WSGI file và      ║
║  dán nội dung tương tự bên dưới (thay username bằng tên của bạn)     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import sys
import os

# Đường dẫn thư mục mã nguồn dự án trên PythonAnywhere
# Ví dụ: /home/ten_tai_khoan/appchung
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Import WSGI application từ app.py
from app import application


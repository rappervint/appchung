"""
╔══════════════════════════════════════════════════════════════════════╗
║        TRẦN BÌNH AUTO — HỆ THỐNG QUẢN LÝ TẬP TRUNG ĐA PHÂN HỆ       ║
║                                                                      ║
║  Chạy cục bộ:  python app.py  hoặc click đúp Chay_App_Chung.bat     ║
║  Truy cập   :  http://localhost:5000 hoặc tên miền .local           ║
║                                                                      ║
║  Tự động nạp App động (Dynamic Plug & Play) qua apps_config.json    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import json
import socket
import shutil
import zipfile
import threading
import logging
import importlib
from datetime import datetime

# Đảm bảo các thư mục con có thể import lẫn nhau
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file

# Khởi tạo Flask Application chính
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.config['SECRET_KEY'] = 'gara-oto-tiem-lap-do-secret-key-2026'
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB

# Ẩn bớt log mặc định của werkzeug
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

CONFIG_PATH = os.path.join(BASE_DIR, 'apps_config.json')

def load_apps_config():
    if not os.path.exists(CONFIG_PATH):
        return []
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi đọc apps_config.json: {e}")
        return []

def save_apps_config(apps):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(apps, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Lỗi lưu apps_config.json: {e}")
        return False

# ── NẠP CÁC BLUEPRINT ĐỘNG THEO CẤU HÌNH ──
REGISTERED_APPS = []

def register_dynamic_apps():
    global REGISTERED_APPS
    REGISTERED_APPS = []
    apps = load_apps_config()

    for item in apps:
        if item.get('status') == 'disabled':
            continue
        mod_name = item.get('module')
        if not mod_name:
            # Ứng dụng tích hợp sẵn (ví dụ Trợ lý AI Gara /chat)
            REGISTERED_APPS.append(item)
            continue
        bp_var = item.get('blueprint_var', 'bp')
        prefix = item.get('prefix')
        init_func = item.get('init_func', 'init_db')

        try:
            # Import module động (nếu đã nạp thì reload)
            if mod_name in sys.modules:
                mod = importlib.reload(sys.modules[mod_name])
            else:
                mod = importlib.import_module(mod_name)
            
            # Khởi tạo database nếu có
            if hasattr(mod, init_func):
                try:
                    getattr(mod, init_func)()
                except Exception as db_err:
                    print(f"Lưu ý DB {mod_name}: {db_err}")

            # Đăng ký Blueprint vào Flask app
            if hasattr(mod, bp_var):
                bp = getattr(mod, bp_var)
                if bp.name not in app.blueprints:
                    app._got_first_request = False
                    app.register_blueprint(bp, url_prefix=prefix)
                REGISTERED_APPS.append(item)
                print(f"  ✅ Đã nạp thành công phân hệ: {item.get('name')} ({prefix})")
        except Exception as err:
            print(f"  ⚠️ Không thể nạp phân hệ [{mod_name}]: {err}")

# Khởi chạy nạp các app ban đầu
register_dynamic_apps()

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
    return response

# ── LOG KẾT NỐI THEO DÕI THIẾT BỊ TRUY CẬP (TIẾNG VIỆT) ──
def get_device_info(ua, ip):
    ua_lower = (ua or '').lower()
    dev = "Máy tính"
    if 'iphone' in ua_lower: dev = "📱 iPhone"
    elif 'ipad' in ua_lower: dev = "📱 iPad"
    elif 'android' in ua_lower: dev = "📱 Điện thoại Android"
    elif 'macintosh' in ua_lower or 'mac os' in ua_lower: dev = "💻 Máy tính Mac"
    elif 'windows' in ua_lower: dev = "💻 Máy tính Windows"
    
    if ip in ('127.0.0.1', '::1', 'localhost'):
        return f"{dev} [Máy Chủ]"
    return f"{dev} [IP: {ip}]"

@app.before_request
def log_access():
    path = request.path
    if path in ('/favicon.ico', '/robots.txt') or path.startswith('/static') or path.startswith('/api/hub/'):
        return

    ip = request.remote_addr or '127.0.0.1'
    ua = request.headers.get('User-Agent', '')
    dev_name = get_device_info(ua, ip)
    now_str = datetime.now().strftime("%H:%M:%S")

    if path == '/':
        print(f"  🔔 [{now_str}] {dev_name} -> 🏠 Mở Trang Chủ Hub Trung Tâm", flush=True)
    elif path == '/banhang/' or path == '/banhang':
        print(f"  📦 [{now_str}] {dev_name} -> 🏷️ Mở Bán Hàng & Kho", flush=True)
    elif path == '/den/' or path == '/den':
        print(f"  💡 [{now_str}] {dev_name} -> ⚡ Mở Báo Cáo Doanh Thu Đèn", flush=True)
    elif path == '/thuchi/' or path == '/thuchi':
        print(f"  💰 [{now_str}] {dev_name} -> 💵 Mở Sổ Quản Lý Thu Chi", flush=True)
    elif path.startswith('/chat') or path.startswith('/ai'):
        print(f"  ✨ [{now_str}] {dev_name} -> 🤖 Mở Trợ Lý AI Gara", flush=True)

# ── CỔNG ĐIỀU HƯỚNG TRUNG TÂM (HUB PORTAL) ──
@app.route('/')
def portal():
    apps = load_apps_config()
    return render_template('portal.html', apps=apps)

# ── GIAO DIỆN CHAT TRỢ LÝ AI CHUẨN GEMINI (FULLSCREEN GEMINI UI) ──
@app.route('/chat')
@app.route('/chat/')
@app.route('/ai')
@app.route('/ai/')
def page_gemini_chat():
    return render_template('gemini_chat.html')

# ── API QUẢN TRỊ ỨNG DỤNG (THÊM / BẬT TẮT / XÓA) ──

@app.route('/api/hub/add-app', methods=['POST'])
def api_add_app():
    name = request.form.get('name', '').strip()
    app_id = request.form.get('id', '').strip().lower()
    desc = request.form.get('desc', '').strip()
    icon = request.form.get('icon', 'bi-app-indicator').strip()
    theme_color = request.form.get('theme_color', 'blue').strip()
    features_raw = request.form.get('features', '').strip()

    if not name or not app_id:
        return jsonify({'success': False, 'message': 'Vui lòng nhập Tên ứng dụng và Mã định danh ID!'}), 400

    # Chuẩn hóa prefix và module
    prefix = f"/{app_id}"
    module_name = f"app_{app_id}"
    target_dir = os.path.join(BASE_DIR, module_name)

    # Xử lý mã nguồn app
    uploaded_file = request.files.get('zip_file')
    if uploaded_file and uploaded_file.filename:
        # Giải nén file zip vào thư mục app
        try:
            os.makedirs(target_dir, exist_ok=True)
            with zipfile.ZipFile(uploaded_file, 'r') as zf:
                zf.extractall(target_dir)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Lỗi giải nén file zip: {str(e)}'}), 500
    elif not os.path.exists(target_dir):
        # Tự động tạo thư mục app mới từ mẫu app_mau
        mau_dir = os.path.join(BASE_DIR, 'app_mau')
        if os.path.exists(mau_dir):
            try:
                shutil.copytree(mau_dir, target_dir)
                # Tự đổi tên blueprint trong app.py của app mới
                new_app_file = os.path.join(target_dir, 'app.py')
                if os.path.exists(new_app_file):
                    with open(new_app_file, 'r', encoding='utf-8') as f:
                        c = f.read()
                    c = c.replace("mau_bp = Blueprint('mau'", f"{app_id}_bp = Blueprint('{app_id}'")
                    c = c.replace("mau_bp", f"{app_id}_bp")
                    with open(new_app_file, 'w', encoding='utf-8') as f:
                        f.write(c)
                # Tự đổi __init__.py
                new_init_file = os.path.join(target_dir, '__init__.py')
                if os.path.exists(new_init_file):
                    with open(new_init_file, 'w', encoding='utf-8') as f:
                        f.write(f"from .app import {app_id}_bp, init_db\n")
            except Exception as e:
                print(f"Lỗi tạo app từ mẫu: {e}")

    # Xử lý các gạch đầu dòng tính năng
    features = [f.strip() for f in features_raw.split('\n') if f.strip()]
    if not features:
        features = ["Tự động khởi tạo giao diện chuẩn", "Lưu trữ dữ liệu SQLite độc lập", "Hỗ trợ chạy trên cả điện thoại & máy tính"]

    # Đọc cấu hình hiện tại và thêm vào
    apps = load_apps_config()
    # Kiểm tra xem ID đã tồn tại chưa
    existing = next((a for a in apps if a.get('id') == app_id), None)
    if existing:
        existing.update({
            'name': name,
            'desc': desc,
            'icon': icon,
            'theme_color': theme_color,
            'features': features,
            'status': 'active'
        })
    else:
        new_entry = {
            'id': app_id,
            'name': name,
            'prefix': prefix,
            'module': module_name,
            'blueprint_var': f"{app_id}_bp",
            'init_func': 'init_db',
            'desc': desc or f"Phân hệ {name} dành riêng cho cửa hàng.",
            'icon': icon,
            'theme_color': theme_color,
            'status': 'active',
            'features': features
        }
        apps.append(new_entry)

    save_apps_config(apps)

    # Nạp ngay blueprint vào Flask runtime
    register_dynamic_apps()

    # Chạm vào wsgi.py nếu có để kích hoạt reload trên server PythonAnywhere
    try:
        wsgi_file = os.path.join(BASE_DIR, 'wsgi.py')
        if os.path.exists(wsgi_file):
            os.utime(wsgi_file, None)
    except Exception:
        pass

    return jsonify({'success': True, 'message': f'Đã đăng ký phân hệ "{name}" thành công!', 'prefix': prefix})

@app.route('/api/hub/toggle-app/<app_id>', methods=['POST'])
def api_toggle_app(app_id):
    apps = load_apps_config()
    target = next((a for a in apps if a.get('id') == app_id), None)
    if not target:
        return jsonify({'success': False, 'message': 'Không tìm thấy ứng dụng'}), 404
    
    new_status = 'disabled' if target.get('status') == 'active' else 'active'
    target['status'] = new_status
    save_apps_config(apps)
    return jsonify({'success': True, 'new_status': new_status})

@app.route('/api/hub/delete-app/<app_id>', methods=['POST'])
def api_delete_app(app_id):
    apps = load_apps_config()
    apps = [a for a in apps if a.get('id') != app_id]
    save_apps_config(apps)
    return jsonify({'success': True, 'message': 'Đã xóa khỏi danh sách Hub!'})

# Biến WSGI chuẩn cho PythonAnywhere

# ── API TRỢ LÝ AI ĐIỀU HÀNH TOÀN DIỆN (AI ASSISTANT) ──
@app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
def api_ai_chat():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json or {}
    if not data and request.form:
        data = request.form.to_dict()
    message = data.get('message', '').strip()
    session_id = data.get('session_id', 'default_user')
    image_data = data.get('image', None)
    file_timestamp = data.get('file_timestamp', None)
    if not image_data and request.files:
        f = request.files.get('image') or request.files.get('file')
        if f:
            import base64
            img_b = f.read()
            image_data = f"data:{f.content_type};base64,{base64.b64encode(img_b).decode('utf-8')}"
    try:
        from ai_assistant import process_ai_command
        result = process_ai_command(message, session_id=session_id, image_data=image_data, file_timestamp=file_timestamp)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'type': 'error',
            'message': f'Lỗi hệ thống trợ lý AI: {str(e)}'
        }), 500

@app.route('/api/ai/models', methods=['GET'])
def api_ai_models():
    """Lấy danh sách các model Gemini hỗ trợ và model đang kích hoạt."""
    try:
        import gemini_engine
        return jsonify(gemini_engine.get_available_gemini_models())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/models/select', methods=['POST'])
def api_ai_models_select():
    """Đổi model Gemini đang kích hoạt tức thì không cần restart máy chủ."""
    data = request.json or {}
    model_id = data.get('model', '').strip()
    try:
        import gemini_engine
        res = gemini_engine.switch_preferred_model(model_id)
        return jsonify(res)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/ai/usage', methods=['GET'])
def api_ai_usage():
    """Lấy thống kê chi tiết tài nguyên & số token Gemini đã sử dụng."""
    try:
        import token_tracker
        return jsonify(token_tracker.get_token_summary())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/usage/reset', methods=['POST'])
def api_ai_usage_reset():
    """Đặt lại bộ đếm token theo yêu cầu người dùng."""
    try:
        import token_tracker
        res = token_tracker.reset_token_stats()
        return jsonify(res)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ═════════════════════════════════════════════════════════════════════
# ── TRUNG TÂM SAO LƯU & NẠP LẠI DỮ LIỆU (BACKUP & RESTORE) ──
# ═════════════════════════════════════════════════════════════════════
@app.route('/api/backup/download', methods=['GET'])
def api_backup_download():
    """Tạo và tải về file Zip sao lưu toàn bộ 4 cơ sở dữ liệu của gara."""
    try:
        import backup_restore_manager
        zip_path, zip_name = backup_restore_manager.create_full_backup_zip()
        return send_file(zip_path, as_attachment=True, download_name=zip_name)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi tạo bản sao lưu: {str(e)}'
        }), 500

@app.route('/api/backup/restore', methods=['POST'])
def api_backup_restore():
    """Nạp lại dữ liệu từ file được tải lên (.bak VPOS, .zip, .db)."""
    if 'backup_file' not in request.files:
        return jsonify({'success': False, 'message': 'Vui lòng chọn file dữ liệu để nạp.'}), 400

    file = request.files['backup_file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'Chưa có file nào được chọn.'}), 400

    try:
        import backup_restore_manager
        safe_fname = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
        temp_name = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_fname}"
        temp_path = os.path.join(backup_restore_manager.BACKUP_DIR, temp_name)
        file.save(temp_path)

        res = backup_restore_manager.restore_uploaded_file(temp_path)

        # Xóa file tạm
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        return jsonify(res)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Lỗi trong quá trình nạp dữ liệu: {str(e)}'
        }), 500

application = app

# ── HÀM LẤY IP NỘI BỘ WI-FI / MẠNG LAN ──
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# ── ĐĂNG KÝ PHÁT SÓNG TÊN MIỀN NỘI BỘ (mDNS) ──
PORT_80_ACTIVE = False

def start_network_services():
    global PORT_80_ACTIVE
    lan_ip = get_lan_ip()

    try:
        from werkzeug.serving import make_server
        srv80 = make_server("0.0.0.0", 80, app, threaded=True)
        t80 = threading.Thread(target=srv80.serve_forever, daemon=True)
        t80.start()
        PORT_80_ACTIVE = True
    except Exception:
        PORT_80_ACTIVE = False

    try:
        import atexit
        from zeroconf import IPVersion, Zeroconf, ServiceInfo
        zc = Zeroconf(ip_version=IPVersion.V4Only)
        atexit.register(zc.close)
        
        target_port = 80 if PORT_80_ACTIVE else 5000
        addr_bytes = [socket.inet_aton(lan_ip)]
        
        services = [
            ("AppChung._http._tcp.local.", "appchung.local.", "appchung"),
            ("TiemLapDo._http._tcp.local.", "tiemlapdo.local.", "tiemlapdo"),
            ("BaoCaoDen._http._tcp.local.", "baocaoden.local.", "baocaoden"),
            ("ThuChi._http._tcp.local.", "thuchi.local.", "thuchi"),
        ]
        for s_type, s_server, s_prop in services:
            try:
                info = ServiceInfo(
                    "_http._tcp.local.",
                    s_type,
                    addresses=addr_bytes,
                    port=target_port,
                    properties={"app": s_prop},
                    server=s_server
                )
                zc.register_service(info)
            except Exception:
                pass
    except Exception:
        pass


if __name__ == '__main__':
    lan_ip = get_lan_ip()
    hostname = socket.gethostname().lower()
    start_network_services()
    
    port_str = "" if PORT_80_ACTIVE else ":5000"

    print("\n" + "=" * 74)
    print("       🚗 HỆ THỐNG QUẢN LÝ GARA Ô TÔ TỔNG HỢP — MÁY CHỦ NỘI BỘ")
    print("=" * 74)
    print("  🌐 ĐỊA CHỈ TRUY CẬP TỪ THIẾT BỊ KHÁC (ĐIỆN THOẠI / IPAD / MÁY TÍNH CÙNG WI-FI):")
    print("  ------------------------------------------------------------------------")
    print(f"  👉 Tên miền chính dễ nhớ :  http://appchung.local{port_str}")
    print(f"  👉 Tên miền Bán Hàng     :  http://tiemlapdo.local{port_str}")
    print(f"  👉 Tên miền Báo Cáo Đèn  :  http://baocaoden.local{port_str}")
    print(f"  👉 Tên miền Sổ Thu Chi   :  http://thuchi.local{port_str}")
    print(f"  👉 Tên theo máy tính     :  http://{hostname}.local{port_str}")
    print(f"  👉 Hoặc địa chỉ IP WiFi  :  http://{lan_ip}{port_str}")
    print("  ------------------------------------------------------------------------")
    print("  💻 TRUY CẬP TRÊN CHÍNH MÁY TÍNH NÀY:")
    print("  ------------------------------------------------------------------------")
    print("  🏠 Trang chủ chọn App   :  http://localhost:5000/")
    print("  📦 Phần mềm Bán Hàng    :  http://localhost:5000/banhang/")
    print("  💡 Báo Cáo Doanh Thu Đèn:  http://localhost:5000/den/")
    print("  💰 Sổ Quản Lý Thu Chi   :  http://localhost:5000/thuchi/")
    print("  ------------------------------------------------------------------------")
    print("  ⌨️  BẢNG PHÍM TẮT & THAO TÁC NHANH:")
    print("  ------------------------------------------------------------------------")
    print("  • [Ctrl + C]      : Dừng / Tắt máy chủ an toàn")
    print("  • [F5] / [Ctrl+R] : Tải lại trang web trên trình duyệt")
    print("  • [Bôi đen chuột] : Sao chép bất kỳ đường link nào ở trên")
    print("  ========================================================================")
    print("  📡 NHẬT KÝ HOẠT ĐỘNG THIẾT BỊ (Mỗi lượt vào sẽ báo bên dưới):")
    print("  " + "-" * 72, flush=True)

    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

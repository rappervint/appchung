from flask import Blueprint, Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

# Đảm bảo đường dẫn file database chính xác dù chạy ở đâu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'finance.db')

thuchi_bp = Blueprint('thuchi', __name__, template_folder='templates')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # 1. Tạo bảng periods (Kỳ thu chi)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            status TEXT NOT NULL DEFAULT 'active'
        )
    ''')

    # 2. Tạo bảng transactions (Giao dịch thu chi)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period_id INTEGER,
            type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # 3. Migration nếu bảng transactions cũ thiếu cột
    cursor = conn.execute("PRAGMA table_info(transactions)")
    cols = [row['name'] for row in cursor.fetchall()]
    if 'note' not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN note TEXT DEFAULT ''")
    if 'period_id' not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN period_id INTEGER")

    # 4. Đảm bảo luôn có 1 kỳ đang hoạt động (active)
    active_period = conn.execute("SELECT * FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
    if not active_period:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        display_date = datetime.now().strftime('%d/%m/%Y')
        cur = conn.execute("INSERT INTO periods (name, start_date, status) VALUES (?, ?, 'active')",
                           (f"Kỳ 1 ({display_date})", now_str))
        active_period_id = cur.lastrowid
    else:
        active_period_id = active_period['id']

    # Gán period_id cho các giao dịch cũ chưa thuộc kỳ nào (nếu có)
    conn.execute("UPDATE transactions SET period_id = ? WHERE period_id IS NULL", (active_period_id,))
    conn.commit()
    conn.close()

init_db()

def get_current_period(conn):
    period = conn.execute("SELECT * FROM periods WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
    if not period:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        display_date = datetime.now().strftime('%d/%m/%Y')
        # Đếm tổng số kỳ để đặt tên
        count = conn.execute("SELECT COUNT(*) FROM periods").fetchone()[0]
        cur = conn.execute("INSERT INTO periods (name, start_date, status) VALUES (?, ?, 'active')",
                           (f"Kỳ {count + 1} ({display_date})", now_str))
        conn.commit()
        period = conn.execute("SELECT * FROM periods WHERE id = ?", (cur.lastrowid,)).fetchone()
    return period

@thuchi_bp.route('/')
def index():
    conn = get_db_connection()
    current_period = get_current_period(conn)

    # Lấy danh sách giao dịch của kỳ hiện tại
    current_rows = conn.execute(
        'SELECT * FROM transactions WHERE period_id = ? ORDER BY created_at DESC, id DESC',
        (current_period['id'],)
    ).fetchall()

    # Thống kê nhanh kỳ hiện tại
    current_income = sum(r['amount'] for r in current_rows if r['type'] == 'thu')
    current_expense = sum(r['amount'] for r in current_rows if r['type'] == 'chi')
    current_balance = current_income - current_expense

    # Lấy dữ liệu cho Tab Báo Cáo: tất cả các kỳ và giao dịch của từng kỳ
    all_periods = conn.execute('SELECT * FROM periods ORDER BY id DESC').fetchall()
    report_periods = []
    total_all_income = 0
    total_all_expense = 0

    for p in all_periods:
        p_rows = conn.execute(
            'SELECT * FROM transactions WHERE period_id = ? ORDER BY created_at DESC, id DESC',
            (p['id'],)
        ).fetchall()
        p_income = sum(r['amount'] for r in p_rows if r['type'] == 'thu')
        p_expense = sum(r['amount'] for r in p_rows if r['type'] == 'chi')
        p_balance = p_income - p_expense

        total_all_income += p_income
        total_all_expense += p_expense

        report_periods.append({
            'period': p,
            'transactions': p_rows,
            'income': p_income,
            'expense': p_expense,
            'balance': p_balance,
            'count': len(p_rows)
        })

    conn.close()

    now_str = datetime.now().strftime('%Y-%m-%dT%H:%M')

    return render_template(
        'thuchi_index.html',
        current_period=current_period,
        current_transactions=current_rows,
        current_income=current_income,
        current_expense=current_expense,
        current_balance=current_balance,
        report_periods=report_periods,
        total_all_income=total_all_income,
        total_all_expense=total_all_expense,
        total_all_balance=total_all_income - total_all_expense,
        now_str=now_str
    )

@thuchi_bp.route('/add', methods=['POST'])
def add():
    t_type = request.form.get('type')
    amount_raw = request.form.get('amount', '').replace(',', '').replace('.', '').strip()
    note = request.form.get('note', '').strip()
    date_val = request.form.get('created_at')

    if not date_val:
        date_val = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        date_val = date_val.replace('T', ' ')
        if len(date_val) == 16:
            date_val += ':00'

    if amount_raw.isdigit() and t_type in ['thu', 'chi']:
        conn = get_db_connection()
        current_period = get_current_period(conn)
        conn.execute(
            'INSERT INTO transactions (period_id, type, amount, note, created_at) VALUES (?, ?, ?, ?, ?)',
            (current_period['id'], t_type, int(amount_raw), note, date_val)
        )
        conn.commit()
        conn.close()

    return redirect(url_for('thuchi.index'))

@thuchi_bp.route('/edit/<int:id>', methods=['POST'])
def edit(id):
    t_type = request.form.get('type')
    amount_raw = request.form.get('amount', '').replace(',', '').replace('.', '').strip()
    note = request.form.get('note', '').strip()
    date_val = request.form.get('created_at')

    if date_val:
        date_val = date_val.replace('T', ' ')
        if len(date_val) == 16:
            date_val += ':00'

    if amount_raw.isdigit() and t_type in ['thu', 'chi']:
        conn = get_db_connection()
        conn.execute(
            'UPDATE transactions SET type = ?, amount = ?, note = ?, created_at = ? WHERE id = ?',
            (t_type, int(amount_raw), note, date_val, id)
        )
        conn.commit()
        conn.close()

    return redirect(url_for('thuchi.index'))

@thuchi_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('thuchi.index'))

@thuchi_bp.route('/end-period', methods=['POST'])
def end_period():
    conn = get_db_connection()
    current_period = get_current_period(conn)
    now_dt = datetime.now()
    end_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')

    # Đóng kỳ hiện tại vào ngày giờ bấm nút
    conn.execute(
        "UPDATE periods SET end_date = ?, status = 'closed' WHERE id = ?",
        (end_str, current_period['id'])
    )

    # Đếm số kỳ đã có để tạo tên kỳ mới
    total_periods = conn.execute("SELECT COUNT(*) FROM periods").fetchone()[0]
    new_name = f"Kỳ {total_periods + 1} ({now_dt.strftime('%d/%m/%Y')})"

    # Tạo kỳ mới với trạng thái active (bảng trắng mới)
    conn.execute(
        "INSERT INTO periods (name, start_date, status) VALUES (?, ?, 'active')",
        (new_name, end_str)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('thuchi.index'))

if __name__ == '__main__':
    standalone_app = Flask(__name__)
    standalone_app.register_blueprint(thuchi_bp, url_prefix='/thuchi')
    @standalone_app.route('/')
    def root():
        return redirect('/thuchi/')
    standalone_app.run(host='0.0.0.0', port=5000, debug=True)
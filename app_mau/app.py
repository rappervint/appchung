from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')

# Thay 'mau' bằng tên định danh app của bạn
mau_bp = Blueprint('mau', __name__, template_folder='templates')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS demo_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@mau_bp.route('/')
def index():
    conn = get_db()
    items = conn.execute('SELECT * FROM demo_items ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('mau_index.html', items=items)

@mau_bp.route('/add', methods=['POST'])
def add_item():
    title = request.form.get('title', '').strip()
    note = request.form.get('note', '').strip()
    if title:
        conn = get_db()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO demo_items (title, note, created_at) VALUES (?, ?, ?)', (title, note, now_str))
        conn.commit()
        conn.close()
    return redirect(url_for('mau.index'))


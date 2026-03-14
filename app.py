from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# Use /tmp for database on Render (writable directory)
DB_PATH = '/tmp/expenses.db' if os.environ.get('RENDER') else 'expenses.db'

# ─── Database Setup ───────────────────────────────────────────

def init_db():
    """Create the expenses table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            amount    REAL    NOT NULL,
            category  TEXT    NOT NULL,
            date      TEXT    NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Routes ───────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    category = request.args.get('category')
    conn = get_db()
    cursor = conn.cursor()

    if category and category != 'all':
        cursor.execute('SELECT * FROM expenses WHERE category = ? ORDER BY id DESC', (category,))
    else:
        cursor.execute('SELECT * FROM expenses ORDER BY id DESC')

    rows = cursor.fetchall()
    conn.close()
    return jsonify({'success': True, 'expenses': [dict(row) for row in rows]})


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data     = request.get_json()
    name     = data.get('name', '').strip()
    amount   = data.get('amount')
    category = data.get('category', '').strip()
    date     = data.get('date', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    if not amount or float(amount) <= 0:
        return jsonify({'success': False, 'error': 'Valid amount is required'}), 400
    if category not in ['food', 'rent', 'transport', 'health', 'other']:
        return jsonify({'success': False, 'error': 'Invalid category'}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO expenses (name, amount, category, date) VALUES (?, ?, ?, ?)',
        (name, float(amount), category, date)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({'success': True, 'expense': {'id': new_id, 'name': name, 'amount': float(amount), 'category': category, 'date': date}}), 201


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM expenses WHERE id = ?', (expense_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'Expense not found'}), 404
    cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Expense deleted'})


@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT SUM(amount), COUNT(*) FROM expenses')
    total, count = cursor.fetchone()
    total = total or 0

    cursor.execute('SELECT name, amount FROM expenses ORDER BY amount DESC LIMIT 1')
    largest = cursor.fetchone()

    cursor.execute('SELECT category, SUM(amount) as total FROM expenses GROUP BY category')
    categories = {row['category']: row['total'] for row in cursor.fetchall()}

    conn.close()

    from datetime import datetime
    day_of_month = datetime.now().day
    daily_avg = round(total / day_of_month, 2) if day_of_month > 0 else 0

    return jsonify({
        'success': True,
        'summary': {
            'total': round(total, 2),
            'count': count,
            'daily_avg': daily_avg,
            'largest': dict(largest) if largest else None,
            'categories': categories
        }
    })


# ─── Run ──────────────────────────────────────────────────────

init_db()

if __name__ == '__main__':
    print("✅ Database initialized")
    print("🚀 SpendWise backend running at http://127.0.0.1:5000")
    app.run(debug=True)

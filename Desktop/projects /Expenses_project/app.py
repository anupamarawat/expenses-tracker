
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime
import sqlite3
import os
import csv

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_PATH = "expenses.db"

# --------------------------
# Database Initialization
# --------------------------
def init_db():
    if not os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense TEXT,
                    amount REAL,
                    category TEXT,
                    date TEXT,
                    added_by TEXT
                )
            """)
            c.execute("INSERT INTO users VALUES (?, ?)", ("DefaultUser", "password"))
            conn.commit()

init_db()

# --------------------------
# Utility Function
# --------------------------
def query_db(query, args=(), one=False):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv

# --------------------------
# Routes
# --------------------------
@app.route('/')
def home():
    return redirect(url_for('login'))

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash("Username and password required!", "danger")
            return redirect(url_for('signup'))
        existing = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
        if existing:
            flash("User already exists!", "warning")
            return redirect(url_for('signup'))
        query_db("INSERT INTO users (username, password) VALUES (?, ?)", [username, password])
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash("Username and password required!", "danger")
            return redirect(url_for('login'))
        user = query_db("SELECT * FROM users WHERE username = ? AND password = ?", [username, password], one=True)
        if user:
            flash(f"Welcome, {username}!", "success")
            return redirect(url_for('dashboard', username=username))
        else:
            flash("Invalid credentials!", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

# Dashboard
@app.route('/dashboard/<username>')
def dashboard(username):
    expenses = query_db("SELECT * FROM expenses WHERE added_by = ?", [username])
    return render_template('dashboard.html', username=username, expenses=expenses)

# Add Expense
@app.route('/add_expense/<username>', methods=['POST'])
def add_expense(username):
    try:
        expense = request.form['expense'].strip()
        amount = float(request.form['amount'])
        category = request.form['category'].strip()
        date = request.form['date'].strip() or datetime.now().strftime("%Y-%m-%d")
        if not expense or amount <= 0 or not category:
            flash("Please fill all fields correctly.", "danger")
            return redirect(url_for('dashboard', username=username))
        query_db(
            "INSERT INTO expenses (expense, amount, category, date, added_by) VALUES (?, ?, ?, ?, ?)",
            [expense, amount, category, date, username]
        )
        flash("Expense added successfully!", "success")
    except Exception as e:
        flash(f"Error adding expense: {str(e)}", "danger")
    return redirect(url_for('dashboard', username=username))

# Edit Expense
@app.route('/edit_expense/<int:id>/<username>', methods=['GET', 'POST'])
def edit_expense(id, username):
    expense = query_db("SELECT * FROM expenses WHERE id = ?", [id], one=True)
    if not expense:
        flash("Expense not found!", "danger")
        return redirect(url_for('dashboard', username=username))
    if request.method == 'POST':
        try:
            new_expense = request.form['expense'].strip()
            amount = float(request.form['amount'])
            category = request.form['category'].strip()
            date = request.form['date'].strip() or datetime.now().strftime("%Y-%m-%d")
            query_db(
                "UPDATE expenses SET expense = ?, amount = ?, category = ?, date = ? WHERE id = ?",
                [new_expense, amount, category, date, id]
            )
            flash("Expense updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating expense: {str(e)}", "danger")
        return redirect(url_for('dashboard', username=username))
    return render_template('edit_expense.html', expense=expense, username=username)

# Delete Expense
@app.route('/delete_expense/<int:id>/<username>')
def delete_expense(id, username):
    query_db("DELETE FROM expenses WHERE id = ?", [id])
    flash("Expense deleted successfully!", "success")
    return redirect(url_for('dashboard', username=username))

# Export CSV
@app.route('/export_csv/<username>')
def export_csv(username):
    expenses = query_db("SELECT * FROM expenses WHERE added_by = ?", [username])
    filename = f"{username}_expenses.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID', 'Expense', 'Amount', 'Category', 'Date'])
        for e in expenses:
            writer.writerow([e['id'], e['expense'], e['amount'], e['category'], e['date']])
    return send_file(filename, as_attachment=True)

# Analytics
@app.route('/analytics/<username>')
def analytics(username):
    expenses = query_db("SELECT * FROM expenses WHERE added_by = ?", [username])
    category_totals = {}
    for e in expenses:
        category_totals[e['category']] = category_totals.get(e['category'], 0) + e['amount']
    categories = list(category_totals.keys())
    totals = list(category_totals.values())
    return render_template('analytics.html', username=username, categories=categories, totals=totals)

# Run
if __name__ == "__main__":
    app.run(debug=True)

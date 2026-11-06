"""Local-only plaintext comparison for authorized database and packet evidence."""
import html
import sqlite3
from pathlib import Path
from flask import Flask, redirect, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "insecure_comparison.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)

def initialize_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS demo_records (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, salary TEXT, phone TEXT)")

initialize_database()

@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        values = tuple(request.form.get(field, "") for field in ("name", "email", "password", "salary", "phone"))
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute("INSERT INTO demo_records (name, email, password, salary, phone) VALUES (?, ?, ?, ?, ?)", values)
        return redirect(url_for("database_view"))
    return """<h1>Intentionally Insecure Local Comparison</h1><p>Use only these fabricated values. Never expose this server to a network.</p><form method="post"><label>Name <input name="name" value="Synthetic Employee"></label><br><label>Email <input name="email" value="synthetic@example.invalid"></label><br><label>Password <input name="password" value="fabricated-password"></label><br><label>Salary <input name="salary" value="50000"></label><br><label>Phone <input name="phone" value="+254700000000"></label><br><button type="submit">Store fabricated plaintext record</button></form>"""

@app.route("/database")
def database_view():
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute("SELECT * FROM demo_records ORDER BY id DESC").fetchall()
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return "<h1>Plaintext Comparison Database</h1><p>All values below are fabricated and intentionally readable.</p><table border='1'><tr><th>ID</th><th>Name</th><th>Email</th><th>Password</th><th>Salary</th><th>Phone</th></tr>" + body + "</table><p><a href='/'>Add another</a></p>"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)

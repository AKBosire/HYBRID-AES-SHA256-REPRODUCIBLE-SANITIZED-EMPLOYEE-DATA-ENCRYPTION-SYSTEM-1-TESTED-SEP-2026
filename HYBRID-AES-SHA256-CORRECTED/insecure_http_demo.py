"""Local-only plaintext comparison for authorized database and packet evidence."""
import html
import sqlite3
from pathlib import Path
from flask import Flask, redirect, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "insecure_comparison.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)

FIRST_NAMES = (
    "Amina", "Baraka", "Chebet", "David", "Esther", "Faith", "Grace", "Hassan", "Irene", "James",
    "Kamau", "Lilian", "Mercy", "Njeri", "Ochieng", "Peter", "Quinter", "Rose", "Samuel", "Wanjiku",
)
LAST_NAMES = ("Achieng", "Atieno", "Cheruiyot", "Kamau", "Kipchoge", "Maina", "Mwangi", "Naliaka", "Odhiambo", "Wambui")
POSITIONS = (
    ("Systems Analyst", "ICT"), ("Software Developer", "ICT"),
    ("Network Engineer", "ICT"), ("Database Administrator", "ICT"),
    ("HR Officer", "Human Resources"), ("Accountant", "Finance"),
    ("Financial Analyst", "Finance"), ("Marketing Specialist", "Marketing"),
    ("Project Coordinator", "Operations"), ("Customer Support Officer", "Customer Service"),
)
STREETS = ("Ngong Road", "Kenyatta Avenue", "Moi Avenue", "Tom Mboya Street", "Uhuru Highway")
CITIES = ("Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret")


def fabricated_record(number):
    first = FIRST_NAMES[(number - 1) % len(FIRST_NAMES)]
    last = LAST_NAMES[((number - 1) // len(FIRST_NAMES) + number - 1) % len(LAST_NAMES)]
    position, department = POSITIONS[(number - 1) % len(POSITIONS)]
    year = 1980 + ((number * 7) % 18)
    month = ((number * 5) % 12) + 1
    day = ((number * 11) % 28) + 1
    return (
        number, f"{first} {last} [Fictional]", f"employee{number:03d}@example.invalid",
        f"Demo@Employee{number:03d}!", f"+254700{number:06d}", f"{year:04d}-{month:02d}-{day:02d}",
        position, str(42000 + number * 350), department,
        f"Plot {number}, {STREETS[(number - 1) % len(STREETS)]}, {CITIES[(number - 1) % len(CITIES)]} [Fictional]",
        f"+254711{number:06d}",
    )

def initialize_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS demo_records "
            "(id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, phone TEXT, "
            "dob TEXT, position TEXT, salary TEXT, department TEXT, address TEXT, emergency_contact TEXT)"
        )
        existing = {row[1] for row in connection.execute("PRAGMA table_info(demo_records)")}
        for column in ("dob", "position", "department", "address", "emergency_contact"):
            if column not in existing:
                connection.execute(f"ALTER TABLE demo_records ADD COLUMN {column} TEXT")
        # Reset only the disposable insecure comparison table to 50 fixed records.
        connection.execute("DELETE FROM demo_records")
        connection.executemany(
            "INSERT INTO demo_records "
            "(id, name, email, password, phone, dob, position, salary, department, address, emergency_contact) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [fabricated_record(number) for number in range(1, 51)],
        )

initialize_database()

@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        fields = (
            "name", "email", "password", "phone", "dob", "position",
            "salary", "department", "address", "emergency_contact",
        )
        values = tuple(request.form.get(field, "") for field in fields)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                "UPDATE demo_records SET name=?, email=?, password=?, phone=?, dob=?, position=?, "
                "salary=?, department=?, address=?, emergency_contact=? WHERE id=50", values
            )
        return redirect(url_for("database_view"))
    return """<h1>Intentionally Insecure Local Comparison</h1>
    <p>Use only these fabricated values. Never expose this server to a network.</p>
    <form method="post" enctype="application/x-www-form-urlencoded">
      <label>Name <input name="name" value="Amina Wanjiku [Fictional]"></label><br>
      <label>Email <input name="email" value="employee050@example.invalid"></label><br>
      <label>Password <input name="password" value="Demo@Employee050!"></label><br>
      <label>Phone <input name="phone" value="+254700000050"></label><br>
      <label>Date of birth <input name="dob" value="1985-05-15"></label><br>
      <label>Position <input name="position" value="Systems Analyst"></label><br>
      <label>Salary <input name="salary" value="55000"></label><br>
      <label>Department <input name="department" value="ICT"></label><br>
      <label>Address <input name="address" value="Plot 50, Ngong Road, Nairobi [Fictional]"></label><br>
      <label>Emergency contact <input name="emergency_contact" value="+254711000050"></label><br>
      <button type="submit">Transmit fabricated record 50 using HTTP</button>
    </form>"""

@app.route("/database")
def database_view():
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            "SELECT id, name, email, password, phone, dob, position, salary, department, address, emergency_contact "
            "FROM demo_records ORDER BY id DESC"
        ).fetchall()
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    return """<style>
    body{font-family:Arial,sans-serif;margin:24px;background:#f4f7fb;color:#1f2937}
    h1{color:#174a7e}.notice{background:#fff3cd;border-left:5px solid #e0a800;padding:12px;margin-bottom:16px}
    .table-wrap{overflow-x:auto;background:white;padding:10px;box-shadow:0 2px 10px #ccd}
    table{border-collapse:collapse;width:100%;font-size:13px}th{background:#174a7e;color:white}
    th,td{border:1px solid #c7d1dc;padding:7px;text-align:left;white-space:nowrap}tr:nth-child(even){background:#eef4fa}
    </style><h1>Plaintext Comparison Database — 50 Fabricated Company Records</h1>
    <div class='notice'><strong>Controlled laboratory evidence:</strong> every record is fictional and intentionally stored in readable plaintext.</div>
    <div class='table-wrap'><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Password</th><th>Phone</th><th>Date of birth</th><th>Position</th><th>Salary</th><th>Department</th><th>Address</th><th>Emergency contact</th></tr>""" + body + "</table></div><p><a href='/'>Open fabricated HTTP submission form</a></p>"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)

import csv
import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
for directory in (DATA_DIR, RESULTS_DIR, UPLOAD_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "employees.db"))
KEY_PATH = Path(os.environ.get("FERNET_KEY_PATH", DATA_DIR / "fernet.key"))
SERVER_METRICS_PATH = RESULTS_DIR / "server_login_metrics.csv"
ADMIN_HASH_PATH = DATA_DIR / "admin_password.hash"
ALERT_RPS_THRESHOLD = float(os.environ.get("ALERT_RPS_THRESHOLD", "70"))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

_metrics_lock = threading.Lock()
_request_times = deque()


def _load_or_create_fernet():
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(Fernet.generate_key())
        print(f"Generated a local Fernet key at {KEY_PATH}. Do not publish this file.")
    return Fernet(KEY_PATH.read_bytes())


fernet = _load_or_create_fernet()


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, login_email TEXT UNIQUE, email TEXT, password TEXT,
                dob TEXT, position TEXT, salary TEXT, phone TEXT, address TEXT,
                department TEXT, hire_date TEXT, emergency_contact TEXT,
                profile_picture TEXT, country TEXT, bio TEXT, linkedin TEXT,
                twitter TEXT
            )
            """
        )


initialize_database()


def encrypt_value(value):
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8") if value else None


def decrypt_value(value):
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8") if value else None


def sha256_digest(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def observed_request_rate():
    now = time.perf_counter()
    with _metrics_lock:
        _request_times.append(now)
        while _request_times and _request_times[0] < now - 1.0:
            _request_times.popleft()
        return len(_request_times)


def append_server_metric(row):
    fieldnames = [
        "timestamp_utc", "auth_result", "sha256_time_ms",
        "request_processing_time_ms", "observed_requests_per_second",
        "alert_triggered",
    ]
    with _metrics_lock:
        exists = SERVER_METRICS_PATH.exists()
        with SERVER_METRICS_PATH.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if not exists:
                writer.writeheader()
            writer.writerow(row)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required(view_function):
    @wraps(view_function)
    def protected_view(*args, **kwargs):
        if not session.get("admin_authenticated"):
            flash("Administrator authentication is required.", "warning")
            return redirect(url_for("admin_login"))
        return view_function(*args, **kwargs)
    return protected_view


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"status": "ok", "timestamp_utc": datetime.now(timezone.utc).isoformat()}


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        plain_email = request.form["email"]
        encrypted = {
            field: encrypt_value(request.form.get(field, ""))
            for field in (
                "name", "email", "dob", "position", "salary", "phone",
                "address", "department", "hire_date", "emergency_contact",
                "country", "bio", "linkedin", "twitter",
            )
        }
        profile_picture = None
        uploaded = request.files.get("profile_picture")
        if uploaded and allowed_file(uploaded.filename):
            filename = f"{secrets.token_hex(4)}_{secure_filename(uploaded.filename)}"
            uploaded.save(UPLOAD_DIR / filename)
            profile_picture = encrypt_value(filename)

        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO employees
                    (name, login_email, email, password, dob, position, salary,
                     phone, address, department, hire_date, emergency_contact,
                     profile_picture, country, bio, linkedin, twitter)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        encrypted["name"], plain_email, encrypted["email"],
                        sha256_digest(request.form["password"]), encrypted["dob"],
                        encrypted["position"], encrypted["salary"], encrypted["phone"],
                        encrypted["address"], encrypted["department"],
                        encrypted["hire_date"], encrypted["emergency_contact"],
                        profile_picture, encrypted["country"], encrypted["bio"],
                        encrypted["linkedin"], encrypted["twitter"],
                    ),
                )
        except sqlite3.IntegrityError:
            flash("That synthetic login email is already registered.", "danger")
            return render_template("register.html"), 409

        flash("Employee registered successfully.", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        request_started = time.perf_counter_ns()
        rate = observed_request_rate()
        with get_connection() as connection:
            employee = connection.execute(
                "SELECT * FROM employees WHERE login_email = ?",
                (request.form.get("email", ""),),
            ).fetchone()

        hash_started = time.perf_counter_ns()
        submitted_digest = sha256_digest(request.form.get("password", ""))
        sha_time_ms = (time.perf_counter_ns() - hash_started) / 1_000_000
        authenticated = bool(employee and secrets.compare_digest(submitted_digest, employee["password"]))

        if authenticated:
            session["employee_id"] = employee["id"]
            # Local prototype verification avoids publishing email credentials.
            session["verification_code"] = os.environ.get("LOCAL_VERIFICATION_CODE", "123456")
            auth_result = "accepted"
            response = redirect(url_for("validate_code"))
        else:
            auth_result = "rejected"
            flash("Invalid login credentials.", "danger")
            response = render_template("login.html")

        total_time_ms = (time.perf_counter_ns() - request_started) / 1_000_000
        if request.headers.get("X-Evidence-Capture") != "1":
            append_server_metric({
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "auth_result": auth_result,
                "sha256_time_ms": f"{sha_time_ms:.6f}",
                "request_processing_time_ms": f"{total_time_ms:.6f}",
                "observed_requests_per_second": rate,
                "alert_triggered": str(rate >= ALERT_RPS_THRESHOLD).lower(),
            })
        return response
    return render_template("login.html")


@app.route("/validate_code", methods=["GET", "POST"])
def validate_code():
    if request.method == "POST":
        if secrets.compare_digest(
            request.form.get("code", ""), session.get("verification_code", "")
        ):
            return redirect(url_for("employee_view"))
        flash("Invalid verification code.", "danger")
    return render_template("validate_code.html")


def decrypt_employee(row):
    output = {"id": row["id"], "login_email": row["login_email"], "password": "SHA-256 digest retained"}
    for field in (
        "name", "email", "dob", "position", "salary", "phone", "address",
        "department", "hire_date", "emergency_contact", "profile_picture",
        "country", "bio", "linkedin", "twitter",
    ):
        try:
            output[field] = decrypt_value(row[field]) if row[field] else None
        except InvalidToken:
            output[field] = "INVALID OR MODIFIED TOKEN"
    return output


@app.route("/employee_view")
def employee_view():
    employee_id = session.get("employee_id")
    if not employee_id:
        return redirect(url_for("login"))
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if not row:
        return redirect(url_for("login"))
    return render_template("view.html", **decrypt_employee(row))


@app.route("/database")
@admin_required
def database_view():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM employees").fetchall()
        columns = [item[1] for item in connection.execute("PRAGMA table_info(employees)")]
    return render_template("database.html", columns=columns, rows=rows)


@app.route("/admin/encrypted")
@admin_required
def admin_encrypted_view():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM employees").fetchall()
        columns = [item[1] for item in connection.execute("PRAGMA table_info(employees)")]
    return render_template("admin_encrypted.html", title="Encrypted Database Records", columns=columns, rows=rows)


@app.route("/admin/decrypted")
@admin_required
def admin_decrypted_view():
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM employees").fetchall()
    decrypted_rows = [decrypt_employee(row) for row in rows]
    columns = list(decrypted_rows[0]) if decrypted_rows else []
    return render_template("admin_decrypted.html", columns=columns, rows=decrypted_rows)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not ADMIN_HASH_PATH.exists():
            flash("Run 'py setup_admin.py' before using the administrator views.", "danger")
        elif check_password_hash(ADMIN_HASH_PATH.read_text(encoding="utf-8").strip(), request.form.get("password", "")):
            session.clear()
            session["admin_authenticated"] = True
            return redirect(url_for("admin_encrypted_view"))
        else:
            flash("Invalid administrator password.", "danger")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/ddos_dashboard")
def ddos_dashboard():
    summary_path = RESULTS_DIR / "latest_summary.json"
    if not summary_path.exists():
        return "<h1>No measured results yet</h1><p>Run: python workload_experiment.py --suite</p>"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return render_template("measured_dashboard.html", summary=summary)


def run_with_tls():
    cert_path = Path(os.environ.get("TLS_CERT_PATH", DATA_DIR / "cert.pem"))
    private_key_path = Path(os.environ.get("TLS_KEY_PATH", DATA_DIR / "key.pem"))
    if not cert_path.exists() or not private_key_path.exists():
        raise SystemExit(
            "TLS certificate files are missing. Generate local test files using "
            "the command provided in README.md. Never commit the private key."
        )
    app.run(
        host="127.0.0.1", port=5000,
        ssl_context=(str(cert_path), str(private_key_path)),
        debug=False, threaded=True, use_reloader=False,
    )


if __name__ == "__main__":
    run_with_tls()

"""Create a local hashed administrator password without storing plaintext."""
from getpass import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash

target = Path(__file__).resolve().parent / "data" / "admin_password.hash"
target.parent.mkdir(parents=True, exist_ok=True)
first = getpass("Create administrator password (minimum 12 characters): ")
second = getpass("Enter it again: ")
if len(first) < 12:
    raise SystemExit("Password not saved: use at least 12 characters.")
if first != second:
    raise SystemExit("Password not saved: the two entries did not match.")
target.write_text(generate_password_hash(first), encoding="utf-8")
print("Administrator password hash saved. The plaintext password was not stored.")

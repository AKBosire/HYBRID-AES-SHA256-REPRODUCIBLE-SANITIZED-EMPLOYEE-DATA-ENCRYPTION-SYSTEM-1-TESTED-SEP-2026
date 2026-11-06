import hashlib
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATA_DIR / "employees.db"
KEY_PATH = DATA_DIR / "fernet.key"
RECORD_COUNT = 50


def main():
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(Fernet.generate_key())
    fernet = Fernet(KEY_PATH.read_bytes())

    def encrypt(value):
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    with sqlite3.connect(DATABASE_PATH) as connection:
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
        for number in range(1, RECORD_COUNT + 1):
            login_email = f"employee{number:03d}@example.invalid"
            values = (
                encrypt(f"Synthetic Employee {number:03d}"),
                login_email,
                encrypt(login_email),
                hashlib.sha256(f"SyntheticPassword{number:03d}!".encode()).hexdigest(),
                encrypt(f"19{70 + number % 25:02d}-{1 + number % 12:02d}-{1 + number % 27:02d}"),
                encrypt(("Trainer", "Administrator", "Technician", "Accountant")[number % 4]),
                encrypt(str(30000 + number * 750)),
                encrypt(f"+254700{number:06d}"),
                encrypt(f"Synthetic Address {number:03d}"),
                encrypt(("ICT", "Finance", "Registry", "Human Resources")[number % 4]),
                encrypt(f"20{15 + number % 10:02d}-{1 + number % 12:02d}-01"),
                encrypt(f"+254711{number:06d}"),
                None,
                encrypt("Kenya"),
                encrypt("Fabricated record created solely for controlled prototype testing."),
                encrypt(""), encrypt(""),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO employees
                (name, login_email, email, password, dob, position, salary, phone,
                 address, department, hire_date, emergency_contact, profile_picture,
                 country, bio, linkedin, twitter)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
    print(f"Created or refreshed {RECORD_COUNT} deterministic synthetic records in {DATABASE_PATH}.")


if __name__ == "__main__":
    main()

import re
from getpass import getpass

from werkzeug.security import generate_password_hash
from app import get_db


def create_admin():
    print("\n===== DevSolve Administrator Setup =====")

    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()

    if not name:
        print("Name cannot be empty.")
        return

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        print("Please enter a valid email address.")
        return

    password = getpass("Create password (at least 12 characters): ")
    confirm_password = getpass("Confirm password: ")

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    try:
        with get_db() as db:
            existing = db.execute(
                "SELECT id FROM admins WHERE email = ?",
                (email,)
            ).fetchone()

            if existing:
                print("An administrator with this email already exists.")
                return

            db.execute(
                """
                INSERT INTO admins (name, email, password_hash)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(password)
                )
            )

        print(f"\nSuccess! Administrator account created for {name}.")

    except Exception:
        print("Something went wrong while creating the account.")
        raise


if __name__ == "__main__":
    create_admin()

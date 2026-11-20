
from werkzeug.security import generate_password_hash
from getpass import getpass
import mysql.connector
from mysql.connector import Error

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Akshaya@123",
    "database": "farmer_market"
}

print("=== Farm2Market Lab Staff Account Creation ===")

name = input("Enter lab staff full name: ").strip()
email = input("Enter lab staff email: ").strip().lower()
password = getpass("Create lab staff password (minimum 6 characters): ")

if not name or not email or len(password) < 6:
    print("Please enter valid details. Password must have at least 6 characters.")
    raise SystemExit

conn = None

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor()

    password_hash = generate_password_hash(password)

    cur.execute(
        """
        INSERT INTO users (name, email, password_hash, role)
        VALUES (%s, %s, %s, 'lab')
        """,
        (name, email, password_hash)
    )

    conn.commit()
    print("Lab staff account created successfully!")

except Error as exc:
    if conn:
        conn.rollback()
    print("Could not create account:", exc)

finally:
    if conn and conn.is_connected():
        conn.close()

import pickle
import os
import hashlib
import requests

# 🔴 HIGH: Unsafe deserialization
def load_user_session(session_data):
    return pickle.loads(session_data)

# 🟠 MEDIUM: Weak password hashing
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# 🔴 HIGH: Command injection vulnerability
def backup_database(db_name):
    os.system(f"pg_dump {db_name} > backup.sql")

# 🟠 MEDIUM: Path traversal vulnerability
def read_user_file(filename):
    with open(f"/var/uploads/{filename}", 'r') as f:
        return f.read()

# 🔴 HIGH: SQL injection (simulated)
def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    # cursor.execute(query)
    return query  # Would execute in real scenario

# 🟠 MEDIUM: No exception handling
def process_order(order_id):
    order = get_order(order_id)
    payment = charge_card(order.total)
    update_inventory(order.items)
    send_confirmation_email(order.user_email)
    return True

def get_order(order_id):
    return {"total": 100, "items": ["item1"], "user_email": "user@example.com"}

def charge_card(amount):
    return True

def update_inventory(items):
    pass

def send_confirmation_email(email):
    pass

# 🔴 HIGH: Hardcoded secrets
API_KEY = "12345-secret-key-67890"
DATABASE_PASSWORD = "admin123"

def connect_to_api():
    return requests.get(
        "https://api.example.com/data",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )

# 🟠 MEDIUM: Race condition
counter = 0

def increment_counter():
    global counter
    counter += 1
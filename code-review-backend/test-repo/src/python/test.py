import pickle
import os
import hashlib

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

# 🔴 HIGH: SQL injection
def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    return cursor.fetchone()

# 🟠 MEDIUM: No exception handling
def process_order(order_id):
    order = get_order(order_id)
    payment = charge_card(order.total)
    update_inventory(order.items)
    send_confirmation_email(order.user_email)
    return True

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
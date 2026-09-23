import sqlite3
import time
import urllib.request
import hashlib
import secrets
from datetime import datetime, timedelta

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

DB_NAME = "offline_transaction.db"

conn = sqlite3.connect(DB_NAME, timeout=15)
conn.execute("PRAGMA busy_timeout = 15000")
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# ==========================================================
# SECURITY HELPERS
# ==========================================================

def hash_value(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def verify_value(value, stored_value):
    return secrets.compare_digest(hash_value(value), stored_value)

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================================
# DATABASE RETRY
# ==========================================================

def execute_with_retry(sql, parameters=(), retries=3):
    for attempt in range(retries):
        try:
            cursor.execute(sql, parameters)
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" not in str(e).lower() or attempt == retries - 1:
                raise
            time.sleep(0.5)
    return False

# ==========================================================
# CREATE TABLES / MIGRATION
# ==========================================================

def add_column_if_missing(table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
        except sqlite3.OperationalError:
            pass

def create_tables():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            transaction_pin TEXT NOT NULL,
            balance REAL DEFAULT 5000,
            reserved_balance REAL DEFAULT 0,
            created_at TEXT,
            profile_photo TEXT,
            personal_information TEXT
        )
    """)

    add_column_if_missing("users", "profile_photo", "TEXT")
    add_column_if_missing("users", "personal_information", "TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchants (
            merchant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    add_column_if_missing("merchants", "email", "TEXT")
    add_column_if_missing("merchants", "password", "TEXT")
    add_column_if_missing("merchants", "business_address", "TEXT")
    add_column_if_missing("merchants", "status", "TEXT DEFAULT 'Active'")
    add_column_if_missing("merchants", "profile_photo", "TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            merchant_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            transaction_status TEXT NOT NULL,
            sync_status TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (customer_id) REFERENCES users(user_id),
            FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id)
        )
    """)

    add_column_if_missing("transactions", "updated_at", "TEXT")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_status_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    cursor.execute("SELECT transaction_id FROM transactions WHERE updated_at IS NULL")
    rows = cursor.fetchall()
    if rows:
        cursor.executemany(
            "UPDATE transactions SET updated_at = transaction_date WHERE transaction_id = ?",
            rows
        )
        conn.commit()

# ==========================================================
# DEMO SEEDING
# ==========================================================

def seed_demo_merchants():
    cursor.execute("SELECT COUNT(*) FROM merchants")
    count = cursor.fetchone()[0]

    if count == 0:
        now = now_text()
        merchants = [
            ("ABC Store", "9000000001", "abc@payflow.demo", hash_value("merchant123"), 0, now, "Main Market", "Active"),
            ("XYZ Mart", "9000000002", "xyz@payflow.demo", hash_value("merchant123"), 0, now, "Central Road", "Active"),
            ("Fresh Market", "9000000003", "fresh@payflow.demo", hash_value("merchant123"), 0, now, "Green Street", "Active")
        ]
        cursor.executemany("""
            INSERT INTO merchants 
            (merchant_name, phone, email, password, balance, created_at, business_address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, merchants)
        conn.commit()
    else:
        demo_data = [
            ("9000000001", "abc@payflow.demo", "merchant123", "Main Market"),
            ("9000000002", "xyz@payflow.demo", "merchant123", "Central Road"),
            ("9000000003", "fresh@payflow.demo", "merchant123", "Green Street")
        ]
        for phone, email, password, address in demo_data:
            cursor.execute("""
                UPDATE merchants
                SET email = COALESCE(NULLIF(email, ''), ?),
                    password = COALESCE(NULLIF(password, ''), ?),
                    business_address = COALESCE(NULLIF(business_address, ''), ?),
                    status = COALESCE(NULLIF(status, ''), 'Active')
                WHERE phone = ?
            """, (email, hash_value(password), address, phone))
        conn.commit()

def seed_admin():
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO admins (username, password, created_at)
            VALUES (?, ?, ?)
        """, ("admin", hash_value("admin123"), now_text()))
        conn.commit()

# ==========================================================
# USER FUNCTIONS
# ==========================================================

def register_user(name, phone, email, password, pin):
    try:
        cursor.execute("""
            INSERT INTO users 
            (full_name, phone, email, password, transaction_pin, balance, reserved_balance, created_at, profile_photo)
            VALUES (?, ?, ?, ?, ?, 5000, 0, ?, ?)
        """, (name, phone, email, hash_value(password), hash_value(pin), now_text(), None))
        conn.commit()
        return True, "Registration Successful!"
    except sqlite3.IntegrityError:
        return False, "Phone number or Email already exists."

def login_user(phone, password):
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    if not user:
        return None

    if user[4] == password:
        cursor.execute("UPDATE users SET password = ? WHERE user_id = ?", (hash_value(password), user[0]))
        conn.commit()
        return get_user(user[0])

    if verify_value(password, user[4]):
        return user
    return None

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def update_profile(user_id, name, email, password, transaction_pin, profile_photo):
    try:
        cursor.execute("""
            UPDATE users 
            SET full_name = ?, email = ?, password = ?, transaction_pin = ?, profile_photo = ?
            WHERE user_id = ?
        """, (name, email, hash_value(password), hash_value(transaction_pin), profile_photo, user_id))
        conn.commit()
        return True, "Profile updated successfully."
    except sqlite3.IntegrityError:
        return False, "Email already exists."

# ==========================================================
# MERCHANT FUNCTIONS (FIXED COLUMN MAPPING)
# ==========================================================

def get_merchants():
    cursor.execute("SELECT merchant_id, merchant_name FROM merchants WHERE status = 'Active' ORDER BY merchant_name")
    return cursor.fetchall()

def register_merchant(name, phone, email, password, address):
    try:
        cursor.execute("""
            INSERT INTO merchants 
            (merchant_name, phone, email, password, balance, created_at, business_address, status, profile_photo)
            VALUES (?, ?, ?, ?, 0, ?, ?, 'Active', NULL)
        """, (name, phone, email, hash_value(password), now_text(), address))
        conn.commit()
        return True, "Merchant registration successful."
    except sqlite3.IntegrityError:
        return False, "Phone number or Email already exists."

def get_merchant(merchant_id):
    cursor.execute("PRAGMA table_info(merchants)")
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute("SELECT * FROM merchants WHERE merchant_id = ?", (merchant_id,))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(zip(columns, row))
    # Returns in fixed reliable order:
    # 0: id, 1: name, 2: phone, 3: email, 4: balance, 5: address, 6: status, 7: created_at, 8: profile_photo
    return (
        data.get("merchant_id"),
        data.get("merchant_name"),
        data.get("phone"),
        data.get("email") or "",
        float(data.get("balance") or 0.0),
        data.get("business_address") or "",
        data.get("status") or "Active",
        data.get("created_at") or "",
        data.get("profile_photo") or None
    )

def login_merchant(phone, password):
    cursor.execute("PRAGMA table_info(merchants)")
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute("SELECT * FROM merchants WHERE phone = ? AND status = 'Active'", (phone,))
    row = cursor.fetchone()
    if not row:
        return None
    data = dict(zip(columns, row))
    stored_pwd = data.get("password")

    if stored_pwd == password:
        cursor.execute("UPDATE merchants SET password = ? WHERE merchant_id = ?", (hash_value(password), data["merchant_id"]))
        conn.commit()
        return get_merchant(data["merchant_id"])

    if stored_pwd and verify_value(password, stored_pwd):
        return get_merchant(data["merchant_id"])
    return None

def update_merchant_profile(merchant_id, name, email, password, address, profile_photo=None):
    try:
        if password:
            cursor.execute("""
                UPDATE merchants
                SET merchant_name = ?, email = ?, password = ?, business_address = ?, profile_photo = ?
                WHERE merchant_id = ?
            """, (name, email, hash_value(password), address, profile_photo, merchant_id))
        else:
            cursor.execute("""
                UPDATE merchants
                SET merchant_name = ?, email = ?, business_address = ?, profile_photo = ?
                WHERE merchant_id = ?
            """, (name, email, address, profile_photo, merchant_id))
        conn.commit()
        return True, "Merchant profile updated successfully."
    except sqlite3.IntegrityError:
        return False, "Email already exists."
    except Exception as e:
        return False, str(e)

# ==========================================================
# TRANSACTION PROCESSING
# ==========================================================

def generate_transaction_id():
    while True:
        transaction_id = f"OFF{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(10000):04d}"
        cursor.execute("SELECT 1 FROM transactions WHERE transaction_id = ?", (transaction_id,))
        if cursor.fetchone() is None:
            return transaction_id

def record_status_change(transaction_id, old_status, new_status, changed_by):
    cursor.execute("""
        INSERT INTO transaction_status_history 
        (transaction_id, old_status, new_status, changed_at, changed_by)
        VALUES (?, ?, ?, ?, ?)
    """, (transaction_id, old_status, new_status, now_text(), changed_by))

def update_transaction_status(transaction_id, new_status, changed_by):
    cursor.execute("SELECT transaction_status FROM transactions WHERE transaction_id = ?", (transaction_id,))
    row = cursor.fetchone()
    if not row:
        return False
    old_status = row[0]
    if old_status == new_status:
        return True

    cursor.execute("""
        UPDATE transactions 
        SET transaction_status = ?, updated_at = ? 
        WHERE transaction_id = ?
    """, (new_status, now_text(), transaction_id))

    record_status_change(transaction_id, old_status, new_status, changed_by)
    return True

def get_transaction_status_history(transaction_id):
    cursor.execute("""
        SELECT old_status, new_status, changed_at, changed_by
        FROM transaction_status_history
        WHERE transaction_id = ?
        ORDER BY history_id ASC
    """, (transaction_id,))
    return cursor.fetchall()

def create_offline_transaction(user_id, merchant_id, amount, pin):
    cursor.execute("SELECT transaction_pin, balance, reserved_balance FROM users WHERE user_id = ?", (user_id,))
    customer = cursor.fetchone()
    if not customer:
        return False, "Customer not found."

    saved_pin, balance, reserved = customer
    if not verify_value(pin, saved_pin):
        if saved_pin != pin:
            return False, "Incorrect Transaction PIN."
        cursor.execute("UPDATE users SET transaction_pin = ? WHERE user_id = ?", (hash_value(pin), user_id))

    available = balance - reserved
    if amount > available:
        return False, f"Insufficient Balance.\nAvailable balance: ₹{available:.2f}"

    cursor.execute("SELECT merchant_id FROM merchants WHERE merchant_id = ? AND status = 'Active'", (merchant_id,))
    if not cursor.fetchone():
        return False, "Merchant is not active."

    transaction_id = generate_transaction_id()
    try:
        cursor.execute("UPDATE users SET reserved_balance = reserved_balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("""
            INSERT INTO transactions 
            (transaction_id, customer_id, merchant_id, amount, transaction_date, transaction_type, transaction_status, sync_status, updated_at)
            VALUES (?, ?, ?, ?, ?, 'Offline', 'Pending Sync', 'Pending Sync', ?)
        """, (transaction_id, user_id, merchant_id, amount, now_text(), now_text()))

        record_status_change(transaction_id, None, "Pending Sync", f"Customer:{user_id}")
        conn.commit()
        return True, transaction_id
    except Exception as e:
        conn.rollback()
        return False, str(e)

# ==========================================================
# NETWORK & SYNC ENGINE
# ==========================================================

def is_network_available(timeout=2):
    test_urls = ("https://www.google.com/generate_204", "https://www.microsoft.com/")
    for url in test_urls:
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "PayFlow/1.0"})
            with urllib.request.urlopen(req, timeout=timeout):
                return True
        except Exception:
            continue
    return False

def get_pending_transactions(user_id):
    cursor.execute("""
        SELECT transaction_id, amount, transaction_date, transaction_status
        FROM transactions
        WHERE customer_id = ? AND sync_status = 'Pending Sync' AND transaction_status = 'Pending Sync'
        ORDER BY transaction_date DESC
    """, (user_id,))
    return cursor.fetchall()

def sync_transactions(user_id):
    if not is_network_available():
        return False, "Network unavailable."

    pending = get_pending_transactions(user_id)
    if not pending:
        return False, "No transactions pending synchronization."

    synced_count = 0
    try:
        for txn in pending:
            transaction_id = txn[0]
            cursor.execute("""
                SELECT sync_status, transaction_status FROM transactions
                WHERE transaction_id = ? AND customer_id = ?
            """, (transaction_id, user_id))
            existing = cursor.fetchone()
            if not existing or existing[0] != "Pending Sync" or existing[1] != "Pending Sync":
                continue

            update_transaction_status(transaction_id, "Pending Merchant Approval", f"Sync:{user_id}")
            cursor.execute("""
                UPDATE transactions
                SET sync_status = 'Synced', updated_at = ?
                WHERE transaction_id = ? AND customer_id = ? AND sync_status = 'Pending Sync'
            """, (now_text(), transaction_id, user_id))

            if cursor.rowcount == 1:
                synced_count += 1

        conn.commit()
        if synced_count:
            return True, f"{synced_count} transaction(s) synchronized."
        return False, "No new transactions were synchronized."
    except Exception as e:
        conn.rollback()
        return False, str(e)

# ==========================================================
# SETTLEMENT (APPROVE / REJECT)
# ==========================================================

def approve_transaction(transaction_id, merchant_id=None):
    if merchant_id is None:
        cursor.execute("SELECT customer_id, merchant_id, amount, transaction_status FROM transactions WHERE transaction_id = ?", (transaction_id,))
    else:
        cursor.execute("SELECT customer_id, merchant_id, amount, transaction_status FROM transactions WHERE transaction_id = ? AND merchant_id = ?", (transaction_id, merchant_id))
    
    txn = cursor.fetchone()
    if not txn:
        return False, "Transaction not found."

    customer_id, txn_merchant_id, amount, status = txn
    if status not in ("Pending Merchant Approval", "Pending Sync"):
        return False, f"Cannot approve from status: {status}"

    try:
        cursor.execute("""
            UPDATE users SET balance = balance - ?, reserved_balance = reserved_balance - ?
            WHERE user_id = ? AND reserved_balance >= ?
        """, (amount, amount, customer_id, amount))
        if cursor.rowcount != 1:
            conn.rollback()
            return False, "Reserved balance validation failed."

        cursor.execute("UPDATE merchants SET balance = balance + ? WHERE merchant_id = ?", (amount, txn_merchant_id))
        actor = "Admin" if merchant_id is None else f"Merchant:{txn_merchant_id}"
        update_transaction_status(transaction_id, "Completed", actor)
        cursor.execute("UPDATE transactions SET sync_status = 'Synced', updated_at = ? WHERE transaction_id = ?", (now_text(), transaction_id))
        conn.commit()
        return True, f"{transaction_id} completed successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)

def reject_transaction(transaction_id, merchant_id=None):
    if merchant_id is None:
        cursor.execute("SELECT customer_id, merchant_id, amount, transaction_status FROM transactions WHERE transaction_id = ?", (transaction_id,))
    else:
        cursor.execute("SELECT customer_id, merchant_id, amount, transaction_status FROM transactions WHERE transaction_id = ? AND merchant_id = ?", (transaction_id, merchant_id))
    
    txn = cursor.fetchone()
    if not txn:
        return False, "Transaction not found."

    customer_id, txn_merchant_id, amount, status = txn
    if status not in ("Pending Merchant Approval", "Pending Sync"):
        return False, f"Cannot reject from status: {status}"

    try:
        cursor.execute("""
            UPDATE users SET reserved_balance = reserved_balance - ?
            WHERE user_id = ? AND reserved_balance >= ?
        """, (amount, customer_id, amount))
        if cursor.rowcount != 1:
            conn.rollback()
            return False, "Reserved balance validation failed."

        actor = "Admin" if merchant_id is None else f"Merchant:{txn_merchant_id}"
        update_transaction_status(transaction_id, "Rejected", actor)
        cursor.execute("UPDATE transactions SET sync_status = 'Synced', updated_at = ? WHERE transaction_id = ?", (now_text(), transaction_id))
        conn.commit()
        return True, f"{transaction_id} rejected. Reserved amount released."
    except Exception as e:
        conn.rollback()
        return False, str(e)

# ==========================================================
# QUERIES & ADMIN STATS
# ==========================================================

def get_transaction_history(user_id):
    cursor.execute("""
        SELECT t.transaction_id, m.merchant_name, t.amount, t.transaction_date, t.transaction_status, t.sync_status, t.updated_at
        FROM transactions t
        JOIN merchants m ON t.merchant_id = m.merchant_id
        WHERE t.customer_id = ?
        ORDER BY t.transaction_date DESC
    """, (user_id,))
    return cursor.fetchall()

def get_transaction_details(transaction_id, customer_id=None):
    if customer_id is None:
        cursor.execute("""
            SELECT t.transaction_id, u.full_name, u.phone, m.merchant_name, t.amount, t.transaction_date, t.transaction_type, t.transaction_status, t.sync_status, t.updated_at
            FROM transactions t
            JOIN users u ON t.customer_id = u.user_id
            JOIN merchants m ON t.merchant_id = m.merchant_id
            WHERE t.transaction_id = ?
        """, (transaction_id,))
    else:
        cursor.execute("""
            SELECT t.transaction_id, u.full_name, u.phone, m.merchant_name, t.amount, t.transaction_date, t.transaction_type, t.transaction_status, t.sync_status, t.updated_at
            FROM transactions t
            JOIN users u ON t.customer_id = u.user_id
            JOIN merchants m ON t.merchant_id = m.merchant_id
            WHERE t.transaction_id = ? AND t.customer_id = ?
        """, (transaction_id, customer_id))
    return cursor.fetchone()

def get_merchant_requests(merchant_id=None):
    base = """
        SELECT t.transaction_id, u.full_name, u.phone, m.merchant_name, t.amount, t.transaction_date, t.transaction_status, t.sync_status
        FROM transactions t
        JOIN users u ON t.customer_id = u.user_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
        WHERE t.sync_status = 'Synced' AND t.transaction_status = 'Pending Merchant Approval'
    """
    if merchant_id is not None:
        base += " AND t.merchant_id = ? ORDER BY t.transaction_date DESC"
        cursor.execute(base, (merchant_id,))
    else:
        base += " ORDER BY t.transaction_date DESC"
        cursor.execute(base)
    return cursor.fetchall()

def get_merchant_history(merchant_id):
    cursor.execute("""
        SELECT t.transaction_id, u.full_name, u.phone, t.amount, t.transaction_date, t.transaction_status, t.sync_status, t.updated_at
        FROM transactions t
        JOIN users u ON t.customer_id = u.user_id
        WHERE t.merchant_id = ?
        ORDER BY t.transaction_date DESC
    """, (merchant_id,))
    return cursor.fetchall()

def login_admin(username, password):
    cursor.execute("SELECT admin_id, username FROM admins WHERE username = ? AND password = ?", (username, hash_value(password)))
    return cursor.fetchone()

def get_admin_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM merchants")
    merchants = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions")
    transactions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_status = 'Pending Sync'")
    pending_sync = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_status = 'Pending Merchant Approval'")
    pending_approval = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_status = 'Completed'")
    completed = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE transaction_status = 'Rejected'")
    rejected = cursor.fetchone()[0]

    return (users, merchants, transactions, pending_sync, pending_approval, completed, rejected)

def get_all_transactions(status=None):
    sql = """
        SELECT t.transaction_id, u.full_name, u.phone, m.merchant_name, t.amount, t.transaction_date, t.transaction_status, t.sync_status, t.updated_at
        FROM transactions t
        JOIN users u ON t.customer_id = u.user_id
        JOIN merchants m ON t.merchant_id = m.merchant_id
    """
    if status and status != "All":
        sql += " WHERE t.transaction_status = ? ORDER BY t.transaction_date DESC"
        cursor.execute(sql, (status,))
    else:
        sql += " ORDER BY t.transaction_date DESC"
        cursor.execute(sql)
    return cursor.fetchall()

def get_all_users():
    cursor.execute("SELECT user_id, full_name, phone, email, balance, reserved_balance, created_at FROM users ORDER BY created_at DESC")
    return cursor.fetchall()

def get_all_merchants():
    cursor.execute("PRAGMA table_info(merchants)")
    columns = [col[1] for col in cursor.fetchall()]
    cursor.execute("SELECT * FROM merchants ORDER BY created_at DESC")
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(zip(columns, r))
        result.append((
            d.get("merchant_id"),
            d.get("merchant_name"),
            d.get("phone"),
            d.get("email") or "",
            float(d.get("balance") or 0.0),
            d.get("business_address") or "",
            d.get("status") or "Active",
            d.get("created_at") or ""
        ))
    return result

def update_merchant_status(merchant_id, status):
    if status not in ("Active", "Suspended"):
        return False, "Invalid merchant status."
    cursor.execute("UPDATE merchants SET status = ? WHERE merchant_id = ?", (status, merchant_id))
    conn.commit()
    return (cursor.rowcount > 0), f"Merchant status changed to {status}."

create_tables()
seed_demo_merchants()
seed_admin()
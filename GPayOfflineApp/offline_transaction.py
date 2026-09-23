import tkinter as tk
from tkinter import messagebox, filedialog
import sqlite3
from datetime import datetime
import os

# ==========================================================
# PILLOW
# ==========================================================

try:
    from PIL import Image, ImageTk, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ==========================================================
# DATABASE
# ==========================================================

conn = sqlite3.connect(
    "offline_transaction.db",
    timeout=15
)

conn.execute("PRAGMA busy_timeout = 15000")

cursor = conn.cursor()


def execute_with_retry(sql, parameters=(), retries=3):
    import time

    for attempt in range(retries):
        try:
            cursor.execute(sql, parameters)
            conn.commit()
            return True

        except sqlite3.OperationalError as e:

            if (
                "database is locked" not in str(e).lower()
                or attempt == retries - 1
            ):
                raise

            time.sleep(0.5)

    return False


# ==========================================================
# CREATE TABLES
# ==========================================================

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
            profile_photo TEXT
        )
    """)

    # Add profile_photo to old database if it does not exist
    try:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN profile_photo TEXT"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS merchants (
            merchant_id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)

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
            FOREIGN KEY (customer_id)
                REFERENCES users(user_id),
            FOREIGN KEY (merchant_id)
                REFERENCES merchants(merchant_id)
        )
    """)

    conn.commit()


create_tables()


# ==========================================================
# DEMO MERCHANTS
# ==========================================================

def seed_demo_merchants():

    cursor.execute(
        "SELECT COUNT(*) FROM merchants"
    )

    count = cursor.fetchone()[0]

    if count == 0:

        merchants = [
            (
                "ABC Store",
                "9000000001",
                0,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ),
            (
                "XYZ Mart",
                "9000000002",
                0,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ),
            (
                "Fresh Market",
                "9000000003",
                0,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        ]

        cursor.executemany("""
            INSERT INTO merchants
            (
                merchant_name,
                phone,
                balance,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, merchants)

        conn.commit()


seed_demo_merchants()


# ==========================================================
# MAIN WINDOW
# ==========================================================

root = tk.Tk()

root.title(
    "Offline Transaction Management System"
)

root.geometry("900x750")

root.resizable(False, False)

current_user = None


# ==========================================================
# CLEAR SCREEN
# ==========================================================

def clear_screen():

    for widget in root.winfo_children():
        widget.destroy()


# ==========================================================
# HEADER
# ==========================================================

def create_header(title):

    header = tk.Frame(
        root,
        bg="#1f6f4a",
        height=80
    )

    header.pack(
        fill="x"
    )

    tk.Label(
        header,
        text=title,
        font=("Arial", 20, "bold"),
        bg="#1f6f4a",
        fg="white"
    ).pack(
        pady=20
    )


# ==========================================================
# WELCOME SCREEN
# ==========================================================

def welcome_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    tk.Label(
        root,
        text="OFF PAY",
        font=("Arial", 25, "bold"),
        fg="#1f6f4a",
        bg="white"
    ).pack(
        pady=(130, 15)
    )

    tk.Label(
        root,
        text="Offline Transaction Management System",
        font=("Arial", 14),
        fg="gray",
        bg="white"
    ).pack()

    tk.Label(
        root,
        text="Secure Transaction • Offline Support",
        font=("Arial", 11),
        fg="#555555",
        bg="white"
    ).pack(
        pady=15
    )

    tk.Button(
        root,
        text="GET STARTED",
        font=("Arial", 13, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=22,
        height=2,
        command=role_selection_screen
    ).pack(
        pady=50
    )


# ==========================================================
# ROLE SELECTION
# ==========================================================

def role_selection_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "SELECT USER TYPE"
    )

    tk.Label(
        root,
        text="Select your role",
        font=("Arial", 14),
        bg="white"
    ).pack(
        pady=40
    )

    tk.Button(
        root,
        text="CUSTOMER",
        font=("Arial", 13, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=25,
        height=2,
        command=customer_options_screen
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="MERCHANT",
        font=("Arial", 13, "bold"),
        bg="#555555",
        fg="white",
        width=25,
        height=2,
        command=lambda: messagebox.showinfo(
            "Coming Soon",
            "Merchant module will be added in the next phase."
        )
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="ADMIN",
        font=("Arial", 13, "bold"),
        bg="#555555",
        fg="white",
        width=25,
        height=2,
        command=lambda: messagebox.showinfo(
            "Coming Soon",
            "Admin module will be added in a later phase."
        )
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="MERCHANT DEMO",
        font=("Arial", 12, "bold"),
        bg="#2d8a5f",
        fg="white",
        width=25,
        height=2,
        command=merchant_demo_screen
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=welcome_screen
    ).pack(
        pady=30
    )


# ==========================================================
# CUSTOMER OPTIONS
# ==========================================================

def customer_options_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "CUSTOMER"
    )

    tk.Label(
        root,
        text="Welcome",
        font=("Arial", 20, "bold"),
        bg="white"
    ).pack(
        pady=80
    )

    tk.Button(
        root,
        text="REGISTER",
        font=("Arial", 13, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=25,
        height=2,
        command=customer_registration_screen
    ).pack(
        pady=15
    )

    tk.Button(
        root,
        text="LOGIN",
        font=("Arial", 13, "bold"),
        bg="#2d8a5f",
        fg="white",
        width=25,
        height=2,
        command=customer_login_screen
    ).pack(
        pady=15
    )

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=role_selection_screen
    ).pack(
        pady=30
    )


# ==========================================================
# CUSTOMER REGISTRATION
# ==========================================================

def customer_registration_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "CUSTOMER REGISTRATION"
    )

    form = tk.Frame(
        root,
        bg="white"
    )

    form.pack(
        pady=20
    )

    tk.Label(
        form,
        text="Full Name",
        bg="white"
    ).pack(
        anchor="w"
    )

    name_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    name_entry.pack(
        pady=(5, 10)
    )

    tk.Label(
        form,
        text="Phone Number",
        bg="white"
    ).pack(
        anchor="w"
    )

    phone_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    phone_entry.pack(
        pady=(5, 10)
    )

    tk.Label(
        form,
        text="Email",
        bg="white"
    ).pack(
        anchor="w"
    )

    email_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    email_entry.pack(
        pady=(5, 10)
    )

    tk.Label(
        form,
        text="Password",
        bg="white"
    ).pack(
        anchor="w"
    )

    password_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 11)
    )

    password_entry.pack(
        pady=(5, 10)
    )

    tk.Label(
        form,
        text="4 Digit Transaction PIN",
        bg="white"
    ).pack(
        anchor="w"
    )

    pin_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 11)
    )

    pin_entry.pack(
        pady=(5, 20)
    )


    def register_customer():

        name = name_entry.get().strip()
        phone = phone_entry.get().strip()
        email = email_entry.get().strip()
        password = password_entry.get().strip()
        pin = pin_entry.get().strip()

        if not all([
            name,
            phone,
            email,
            password,
            pin
        ]):

            messagebox.showerror(
                "Error",
                "Please fill all fields."
            )

            return

        if len(phone) != 10 or not phone.isdigit():

            messagebox.showerror(
                "Error",
                "Enter a valid 10 digit phone number."
            )

            return

        if "@" not in email or "." not in email:

            messagebox.showerror(
                "Error",
                "Enter a valid email address."
            )

            return

        if len(pin) != 4 or not pin.isdigit():

            messagebox.showerror(
                "Error",
                "Transaction PIN must be 4 digits."
            )

            return

        try:

            cursor.execute("""
                INSERT INTO users
                (
                    full_name,
                    phone,
                    email,
                    password,
                    transaction_pin,
                    balance,
                    reserved_balance,
                    created_at,
                    profile_photo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                phone,
                email,
                password,
                pin,
                5000,
                0,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                None
            ))

            conn.commit()

            messagebox.showinfo(
                "Success",
                "Registration Successful!\n\n"
                "Starting Balance: ₹5000"
            )

            customer_login_screen()

        except sqlite3.IntegrityError:

            messagebox.showerror(
                "Error",
                "Phone number or Email already exists."
            )


    tk.Button(
        root,
        text="REGISTER",
        font=("Arial", 12, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=22,
        height=2,
        command=register_customer
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="Already Registered? LOGIN",
        bg="white",
        command=customer_login_screen
    ).pack()

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_options_screen
    ).pack(
        pady=15
    )


# ==========================================================
# CUSTOMER LOGIN
# ==========================================================

def customer_login_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "CUSTOMER LOGIN"
    )

    form = tk.Frame(
        root,
        bg="white"
    )

    form.pack(
        pady=100
    )

    tk.Label(
        form,
        text="Phone Number",
        bg="white"
    ).pack(
        anchor="w"
    )

    phone_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 12)
    )

    phone_entry.pack(
        pady=(5, 20)
    )

    tk.Label(
        form,
        text="Password",
        bg="white"
    ).pack(
        anchor="w"
    )

    password_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 12)
    )

    password_entry.pack(
        pady=(5, 30)
    )


    def login_customer():

        global current_user

        phone = phone_entry.get().strip()
        password = password_entry.get().strip()

        if not phone or not password:

            messagebox.showerror(
                "Error",
                "Please enter Phone Number and Password."
            )

            return

        if len(phone) != 10 or not phone.isdigit():

            messagebox.showerror(
                "Error",
                "Enter a valid 10 digit phone number."
            )

            return

        cursor.execute("""
            SELECT *
            FROM users
            WHERE phone = ?
            AND password = ?
        """, (
            phone,
            password
        ))

        user = cursor.fetchone()

        if user:

            current_user = user

            customer_dashboard()

        else:

            messagebox.showerror(
                "Login Failed",
                "Invalid Phone Number or Password."
            )


    tk.Button(
        root,
        text="LOGIN",
        font=("Arial", 12, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=22,
        height=2,
        command=login_customer
    ).pack()

    tk.Button(
        root,
        text="Don't have an account? REGISTER",
        bg="white",
        command=customer_registration_screen
    ).pack(
        pady=15
    )

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_options_screen
    ).pack()


# ==========================================================
# PROFILE SETTINGS
# ==========================================================

def profile_settings_screen():

    global current_user

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "PROFILE SETTINGS"
    )

    # Get current user
    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
    """, (
        current_user[0],
    ))

    user = cursor.fetchone()

    if not user:

        messagebox.showerror(
            "Error",
            "User profile not found."
        )

        customer_dashboard()

        return

    current_user = user

    # ======================================================
    # PHOTO
    # ======================================================

    photo_frame = tk.Frame(
        root,
        bg="white"
    )

    photo_frame.pack(
        pady=15
    )

    photo_label = tk.Label(
        photo_frame,
        bg="#eeeeee",
        width=120,
        height=120
    )

    photo_label.pack()

    existing_photo = None

    if len(user) > 9:
        existing_photo = user[9]

    photo_data = {
        "path": existing_photo,
        "image": None
    }


    def display_photo(path):

        if not PIL_AVAILABLE:

            photo_label.config(
                text="No Photo\n\nInstall Pillow",
                font=("Arial", 11),
                fg="gray"
            )

            return

        if path and os.path.exists(path):

            try:

                image = Image.open(path)

                image = ImageOps.fit(
                    image,
                    (120, 120)
                )

                image = image.convert(
                    "RGB"
                )

                photo = ImageTk.PhotoImage(
                    image
                )

                photo_label.config(
                    image=photo,
                    text=""
                )

                photo_label.image = photo

                photo_data["image"] = photo

            except Exception:

                photo_label.config(
                    image="",
                    text="Unable to load photo",
                    font=("Arial", 10),
                    fg="gray"
                )

        else:

            photo_label.config(
                image="",
                text="NO PHOTO",
                font=("Arial", 11),
                fg="gray"
            )


    display_photo(
        existing_photo
    )


    # ======================================================
    # CHOOSE PHOTO FROM PC
    # ======================================================

    def choose_photo():

        if not PIL_AVAILABLE:

            messagebox.showerror(
                "Pillow Required",
                "Pillow is not installed.\n\n"
                "Run this command:\n\n"
                "pip install pillow"
            )

            return

        file_path = filedialog.askopenfilename(
            title="Choose Profile Photo",
            filetypes=[
                (
                    "Image Files",
                    "*.jpg *.jpeg *.png *.webp *.bmp *.gif"
                ),
                (
                    "JPG / JPEG",
                    "*.jpg *.jpeg"
                ),
                (
                    "PNG",
                    "*.png"
                ),
                (
                    "All Files",
                    "*.*"
                )
            ]
        )

        if file_path:

            photo_data["path"] = file_path

            display_photo(
                file_path
            )


    tk.Button(
        root,
        text="📷 CHOOSE PHOTO FROM PC",
        font=("Arial", 11, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=27,
        height=2,
        command=choose_photo
    ).pack(
        pady=5
    )

    tk.Label(
        root,
        text="Select photo from your PC / Gallery",
        font=("Arial", 9),
        fg="gray",
        bg="white"
    ).pack(
        pady=(0, 10)
    )


    # ======================================================
    # PROFILE FORM
    # ======================================================

    form = tk.Frame(
        root,
        bg="white"
    )

    form.pack(
        pady=5
    )

    # Full Name
    tk.Label(
        form,
        text="Full Name",
        bg="white"
    ).pack(
        anchor="w"
    )

    name_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    name_entry.insert(
        0,
        user[1]
    )

    name_entry.pack(
        pady=(3, 7)
    )


    # Phone
    tk.Label(
        form,
        text="Phone Number",
        bg="white"
    ).pack(
        anchor="w"
    )

    phone_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    phone_entry.insert(
        0,
        user[2]
    )

    phone_entry.config(
        state="readonly"
    )

    phone_entry.pack(
        pady=(3, 7)
    )


    # Email
    tk.Label(
        form,
        text="Email",
        bg="white"
    ).pack(
        anchor="w"
    )

    email_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    email_entry.insert(
        0,
        user[3]
    )

    email_entry.pack(
        pady=(3, 7)
    )


    # New Password
    tk.Label(
        form,
        text="New Password",
        bg="white"
    ).pack(
        anchor="w"
    )

    password_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 11)
    )

    password_entry.pack(
        pady=(3, 7)
    )


    # New PIN
    tk.Label(
        form,
        text="New Transaction PIN",
        bg="white"
    ).pack(
        anchor="w"
    )

    pin_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 11)
    )

    pin_entry.pack(
        pady=(3, 10)
    )


    # ======================================================
    # SAVE PROFILE
    # ======================================================

    def save_profile():

        global current_user

        name = name_entry.get().strip()
        email = email_entry.get().strip()
        new_password = password_entry.get().strip()
        new_pin = pin_entry.get().strip()

        if not name or not email:

            messagebox.showerror(
                "Error",
                "Full Name and Email are required."
            )

            return

        if "@" not in email or "." not in email:

            messagebox.showerror(
                "Error",
                "Enter a valid email address."
            )

            return

        if new_password:

            password = new_password

        else:

            password = user[4]

        if new_pin:

            if (
                len(new_pin) != 4
                or not new_pin.isdigit()
            ):

                messagebox.showerror(
                    "Error",
                    "Transaction PIN must be 4 digits."
                )

                return

            transaction_pin = new_pin

        else:

            transaction_pin = user[5]


        try:

            cursor.execute("""
                UPDATE users
                SET
                    full_name = ?,
                    email = ?,
                    password = ?,
                    transaction_pin = ?,
                    profile_photo = ?
                WHERE user_id = ?
            """, (
                name,
                email,
                password,
                transaction_pin,
                photo_data["path"],
                user[0]
            ))

            conn.commit()

            cursor.execute("""
                SELECT *
                FROM users
                WHERE user_id = ?
            """, (
                user[0],
            ))

            current_user = cursor.fetchone()

            messagebox.showinfo(
                "Success",
                "Profile updated successfully."
            )

            customer_dashboard()

        except sqlite3.IntegrityError:

            messagebox.showerror(
                "Error",
                "Email already exists."
            )


    tk.Button(
        root,
        text="SAVE CHANGES",
        font=("Arial", 12, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=25,
        height=2,
        command=save_profile
    ).pack(
        pady=7
    )

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_dashboard
    ).pack(
        pady=5
    )


# ==========================================================
# GENERATE TRANSACTION ID
# ==========================================================

def generate_transaction_id():

    cursor.execute(
        "SELECT COUNT(*) FROM transactions"
    )

    count = cursor.fetchone()[0] + 1

    return (
        f"OFF"
        f"{datetime.now().strftime('%Y%m%d')}"
        f"{count:04d}"
    )


# ==========================================================
# OFFLINE TRANSACTION
# ==========================================================

def offline_transaction_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "OFFLINE PAYMENT"
    )

    form = tk.Frame(
        root,
        bg="white"
    )

    form.pack(
        pady=20
    )

    tk.Label(
        form,
        text="Select Merchant",
        bg="white",
        font=("Arial", 11)
    ).pack(
        anchor="w"
    )

    cursor.execute("""
        SELECT
            merchant_id,
            merchant_name
        FROM merchants
        ORDER BY merchant_name
    """)

    merchants = cursor.fetchall()

    merchant_map = {}

    for merchant in merchants:

        merchant_id = merchant[0]
        merchant_name = merchant[1]

        merchant_map[
            f"{merchant_name} (ID: M{merchant_id:03d})"
        ] = merchant_id

    merchant_var = tk.StringVar()

    merchant_values = list(
        merchant_map.keys()
    )

    merchant_menu = tk.OptionMenu(
        form,
        merchant_var,
        *merchant_values
    )

    merchant_menu.config(
        width=30,
        font=("Arial", 10)
    )

    merchant_menu.pack(
        pady=(5, 15)
    )


    tk.Label(
        form,
        text="Payment Amount (₹)",
        bg="white",
        font=("Arial", 11)
    ).pack(
        anchor="w"
    )

    amount_entry = tk.Entry(
        form,
        width=35,
        font=("Arial", 11)
    )

    amount_entry.pack(
        pady=(5, 15)
    )


    tk.Label(
        form,
        text="Transaction PIN",
        bg="white",
        font=("Arial", 11)
    ).pack(
        anchor="w"
    )

    pin_entry = tk.Entry(
        form,
        width=35,
        show="*",
        font=("Arial", 11)
    )

    pin_entry.pack(
        pady=(5, 20)
    )


    def create_offline_transaction():

        selected = merchant_var.get().strip()
        amount_text = amount_entry.get().strip()
        pin = pin_entry.get().strip()

        if not selected or not amount_text or not pin:

            messagebox.showerror(
                "Error",
                "Please fill all fields."
            )

            return

        try:

            amount = float(
                amount_text
            )

        except ValueError:

            messagebox.showerror(
                "Error",
                "Enter a valid payment amount."
            )

            return

        if amount <= 0:

            messagebox.showerror(
                "Error",
                "Payment amount must be greater than ₹0."
            )

            return

        if amount > 2000:

            messagebox.showerror(
                "Limit Exceeded",
                "Maximum offline transaction amount is ₹2000."
            )

            return

        if (
            len(pin) != 4
            or not pin.isdigit()
        ):

            messagebox.showerror(
                "Error",
                "Transaction PIN must be 4 digits."
            )

            return

        cursor.execute("""
            SELECT
                transaction_pin,
                balance,
                reserved_balance
            FROM users
            WHERE user_id = ?
        """, (
            current_user[0],
        ))

        customer = cursor.fetchone()

        if not customer:

            messagebox.showerror(
                "Error",
                "Customer not found."
            )

            return

        if customer[0] != pin:

            messagebox.showerror(
                "Authentication Failed",
                "Incorrect Transaction PIN."
            )

            return

        available = (
            customer[1]
            - customer[2]
        )

        if amount > available:

            messagebox.showerror(
                "Insufficient Balance",
                f"Available balance: ₹{available:.2f}"
            )

            return

        merchant_id = merchant_map[
            selected
        ]

        transaction_id = (
            generate_transaction_id()
        )

        cursor.execute("""
            UPDATE users
            SET reserved_balance =
                reserved_balance + ?
            WHERE user_id = ?
        """, (
            amount,
            current_user[0]
        ))

        cursor.execute("""
            INSERT INTO transactions
            (
                transaction_id,
                customer_id,
                merchant_id,
                amount,
                transaction_date,
                transaction_type,
                transaction_status,
                sync_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            current_user[0],
            merchant_id,
            amount,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "Offline",
            "Pending Sync",
            "Pending Sync"
        ))

        conn.commit()

        messagebox.showinfo(
            "Offline Transaction Recorded",
            f"Transaction ID: {transaction_id}\n\n"
            f"Amount: ₹{amount:.2f}\n"
            f"Status: Pending Sync\n\n"
            "The amount has been reserved."
        )

        customer_dashboard()


    tk.Button(
        root,
        text="CONFIRM OFFLINE PAYMENT",
        font=("Arial", 12, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=28,
        height=2,
        command=create_offline_transaction
    ).pack(
        pady=10
    )

    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_dashboard
    ).pack(
        pady=10
    )


# ==========================================================
# SYNC TRANSACTIONS
# ==========================================================

def sync_transactions_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "SYNC TRANSACTIONS"
    )

    cursor.execute("""
        SELECT
            transaction_id,
            amount,
            transaction_date,
            transaction_status
        FROM transactions
        WHERE customer_id = ?
        AND sync_status = 'Pending Sync'
        ORDER BY transaction_date DESC
    """, (
        current_user[0],
    ))

    pending = cursor.fetchall()

    if not pending:

        tk.Label(
            root,
            text="No Pending Transactions",
            font=("Arial", 15, "bold"),
            bg="white"
        ).pack(
            pady=80
        )

    else:

        tk.Label(
            root,
            text=(
                f"{len(pending)} transaction(s) "
                "waiting for synchronization"
            ),
            font=("Arial", 12),
            bg="white"
        ).pack(
            pady=20
        )

        for txn in pending:

            tk.Label(
                root,
                text=(
                    f"{txn[0]} | "
                    f"₹{txn[1]:.2f} | "
                    f"{txn[2]}"
                ),
                bg="white",
                font=("Arial", 10)
            ).pack(
                pady=4
            )


        def synchronize():

            for txn in pending:

                cursor.execute("""
                    UPDATE transactions
                    SET
                        transaction_status =
                            'Pending Merchant Approval',
                        sync_status = 'Synced'
                    WHERE transaction_id = ?
                    AND customer_id = ?
                    AND sync_status = 'Pending Sync'
                """, (
                    txn[0],
                    current_user[0]
                ))

            conn.commit()

            messagebox.showinfo(
                "Synchronization Successful",
                "Pending transactions have been synchronized.\n"
                "They are now waiting for merchant approval."
            )

            customer_dashboard()


        tk.Button(
            root,
            text="SYNCHRONIZE NOW",
            font=("Arial", 12, "bold"),
            bg="#2d8a5f",
            fg="white",
            width=25,
            height=2,
            command=synchronize
        ).pack(
            pady=25
        )


    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_dashboard
    ).pack(
        pady=15
    )


# ==========================================================
# TRANSACTION HISTORY
# ==========================================================

def transaction_history_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "TRANSACTION HISTORY"
    )

    cursor.execute("""
        SELECT
            t.transaction_id,
            m.merchant_name,
            t.amount,
            t.transaction_date,
            t.transaction_status,
            t.sync_status
        FROM transactions t
        JOIN merchants m
            ON t.merchant_id = m.merchant_id
        WHERE t.customer_id = ?
        ORDER BY t.transaction_date DESC
    """, (
        current_user[0],
    ))

    transactions = cursor.fetchall()

    if not transactions:

        tk.Label(
            root,
            text="No transactions found.",
            font=("Arial", 13),
            bg="white"
        ).pack(
            pady=80
        )

    else:

        container = tk.Frame(
            root,
            bg="white"
        )

        container.pack(
            pady=15
        )

        for txn in transactions:

            text = (
                f"ID: {txn[0]}\n"
                f"Merchant: {txn[1]}\n"
                f"Amount: ₹{txn[2]:.2f}\n"
                f"Date: {txn[3]}\n"
                f"Status: {txn[4]}\n"
                f"Sync: {txn[5]}"
            )

            tk.Label(
                container,
                text=text,
                justify="left",
                anchor="w",
                bg="#f4f4f4",
                padx=15,
                pady=8,
                width=42
            ).pack(
                pady=5
            )


    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=customer_dashboard
    ).pack(
        pady=10
    )


# ==========================================================
# MERCHANT DEMO
# ==========================================================

def merchant_demo_screen():

    clear_screen()

    root.configure(
        bg="white"
    )

    create_header(
        "MERCHANT PANEL"
    )

    tk.Label(
        root,
        text="Merchant Transaction Requests",
        font=("Arial", 14, "bold"),
        bg="white"
    ).pack(
        pady=15
    )

    cursor.execute("""
        SELECT
            t.transaction_id,
            u.full_name,
            u.phone,
            m.merchant_name,
            t.amount,
            t.transaction_date
        FROM transactions t
        JOIN users u
            ON t.customer_id = u.user_id
        JOIN merchants m
            ON t.merchant_id = m.merchant_id
        WHERE t.sync_status = 'Synced'
        AND t.transaction_status =
            'Pending Merchant Approval'
        ORDER BY t.transaction_date DESC
    """)

    requests = cursor.fetchall()

    if not requests:

        tk.Label(
            root,
            text="No pending merchant requests.",
            bg="white",
            font=("Arial", 12)
        ).pack(
            pady=60
        )

    else:

        for request in requests:

            (
                txn_id,
                customer_name,
                phone,
                merchant_name,
                amount,
                txn_date
            ) = request

            frame = tk.Frame(
                root,
                bg="#f4f4f4",
                padx=10,
                pady=10
            )

            frame.pack(
                pady=5,
                padx=20,
                fill="x"
            )

            tk.Label(
                frame,
                text=(
                    f"{txn_id}\n"
                    f"Customer: {customer_name}\n"
                    f"Mobile: {phone[:2]}XXXXXX{phone[-2:]}\n"
                    f"Merchant: {merchant_name}\n"
                    f"Amount: ₹{amount:.2f}\n"
                    f"Date: {txn_date}"
                ),
                justify="left",
                bg="#f4f4f4"
            ).pack()


            def approve(tid=txn_id):

                cursor.execute("""
                    SELECT
                        customer_id,
                        merchant_id,
                        amount
                    FROM transactions
                    WHERE transaction_id = ?
                """, (
                    tid,
                ))

                txn = cursor.fetchone()

                if not txn:
                    return

                customer_id = txn[0]
                merchant_id = txn[1]
                amount = txn[2]

                cursor.execute("""
                    UPDATE users
                    SET
                        balance = balance - ?,
                        reserved_balance =
                            reserved_balance - ?
                    WHERE user_id = ?
                """, (
                    amount,
                    amount,
                    customer_id
                ))

                cursor.execute("""
                    UPDATE merchants
                    SET balance = balance + ?
                    WHERE merchant_id = ?
                """, (
                    amount,
                    merchant_id
                ))

                cursor.execute("""
                    UPDATE transactions
                    SET
                        transaction_status = 'Completed',
                        sync_status = 'Synced'
                    WHERE transaction_id = ?
                """, (
                    tid,
                ))

                conn.commit()

                messagebox.showinfo(
                    "Transaction Accepted",
                    f"{tid} completed successfully."
                )

                merchant_demo_screen()


            def reject(tid=txn_id):

                cursor.execute("""
                    SELECT
                        customer_id,
                        amount
                    FROM transactions
                    WHERE transaction_id = ?
                """, (
                    tid,
                ))

                txn = cursor.fetchone()

                if not txn:
                    return

                customer_id = txn[0]
                amount = txn[1]

                cursor.execute("""
                    UPDATE users
                    SET reserved_balance =
                        reserved_balance - ?
                    WHERE user_id = ?
                """, (
                    amount,
                    customer_id
                ))

                cursor.execute("""
                    UPDATE transactions
                    SET
                        transaction_status = 'Rejected',
                        sync_status = 'Synced'
                    WHERE transaction_id = ?
                """, (
                    tid,
                ))

                conn.commit()

                messagebox.showinfo(
                    "Transaction Rejected",
                    f"{tid} rejected.\n"
                    "Reserved amount released."
                )

                merchant_demo_screen()


            buttons = tk.Frame(
                frame,
                bg="#f4f4f4"
            )

            buttons.pack(
                pady=8
            )

            tk.Button(
                buttons,
                text="ACCEPT",
                bg="#1f6f4a",
                fg="white",
                width=10,
                command=approve
            ).pack(
                side="left",
                padx=5
            )

            tk.Button(
                buttons,
                text="REJECT",
                bg="#555555",
                fg="white",
                width=10,
                command=reject
            ).pack(
                side="left",
                padx=5
            )


    tk.Button(
        root,
        text="← BACK",
        bg="white",
        command=welcome_screen
    ).pack(
        pady=15
    )


# ==========================================================
# CUSTOMER DASHBOARD
# ==========================================================

def customer_dashboard():

    global current_user

    clear_screen()

    root.configure(
        bg="white"
    )

    # Refresh user
    cursor.execute("""
        SELECT *
        FROM users
        WHERE user_id = ?
    """, (
        current_user[0],
    ))

    current_user = cursor.fetchone()

    if not current_user:

        welcome_screen()

        return

    create_header(
        "OFFLINE TRANSACTION"
    )


    # ======================================================
    # PROFILE PHOTO
    # ======================================================

    photo_container = tk.Frame(
        root,
        bg="white"
    )

    photo_container.pack(
        pady=(12, 3)
    )

    photo_path = None

    if len(current_user) > 9:
        photo_path = current_user[9]

    dashboard_photo = None

    if (
        PIL_AVAILABLE
        and photo_path
        and os.path.exists(photo_path)
    ):

        try:

            image = Image.open(
                photo_path
            )

            image = ImageOps.fit(
                image,
                (70, 70)
            )

            image = image.convert(
                "RGB"
            )

            dashboard_photo = ImageTk.PhotoImage(
                image
            )

            photo_label = tk.Label(
                photo_container,
                image=dashboard_photo,
                bg="white"
            )

            photo_label.image = dashboard_photo

            photo_label.pack()

        except Exception:

            tk.Label(
                photo_container,
                text="👤",
                font=("Arial", 35),
                bg="white"
            ).pack()

    else:

        tk.Label(
            photo_container,
            text="👤",
            font=("Arial", 35),
            bg="white"
        ).pack()


    # ======================================================
    # GREETING
    # ======================================================

    tk.Label(
        root,
        text=f"Hello, {current_user[1]} 👋",
        font=("Arial", 17, "bold"),
        bg="white"
    ).pack(
        pady=8
    )


    # ======================================================
    # BALANCE
    # ======================================================

    balance = current_user[6]

    reserved = current_user[7]

    available = (
        balance - reserved
    )

    balance_frame = tk.Frame(
        root,
        bg="#e8f5ee",
        padx=30,
        pady=15
    )

    balance_frame.pack(
        pady=8
    )

    tk.Label(
        balance_frame,
        text="AVAILABLE BALANCE",
        font=("Arial", 11, "bold"),
        bg="#e8f5ee",
        fg="#1f6f4a"
    ).pack()

    tk.Label(
        balance_frame,
        text=f"₹ {available:.2f}",
        font=("Arial", 24, "bold"),
        bg="#e8f5ee",
        fg="#1f6f4a"
    ).pack(
        pady=5
    )

    tk.Label(
        balance_frame,
        text=f"Reserved Amount: ₹ {reserved:.2f}",
        font=("Arial", 10),
        bg="#e8f5ee"
    ).pack()


    # ======================================================
    # OFFLINE TRANSACTION
    # ======================================================

    tk.Button(
        root,
        text="OFFLINE TRANSACTION",
        font=("Arial", 12, "bold"),
        bg="#1f6f4a",
        fg="white",
        width=28,
        height=2,
        command=offline_transaction_screen
    ).pack(
        pady=6
    )


    # ======================================================
    # SYNC
    # ======================================================

    tk.Button(
        root,
        text="SYNC TRANSACTIONS",
        font=("Arial", 12),
        bg="#2d8a5f",
        fg="white",
        width=28,
        height=2,
        command=sync_transactions_screen
    ).pack(
        pady=6
    )


    # ======================================================
    # HISTORY
    # ======================================================

    tk.Button(
        root,
        text="TRANSACTION HISTORY",
        font=("Arial", 12),
        bg="#555555",
        fg="white",
        width=28,
        height=2,
        command=transaction_history_screen
    ).pack(
        pady=6
    )


    # ======================================================
    # PROFILE SETTINGS
    # ======================================================

    tk.Button(
        root,
        text="PROFILE SETTINGS",
        font=("Arial", 12, "bold"),
        bg="#3478a8",
        fg="white",
        width=28,
        height=2,
        command=profile_settings_screen
    ).pack(
        pady=6
    )


    # ======================================================
    # LOGOUT
    # ======================================================

    def logout():

        global current_user

        current_user = None

        welcome_screen()


    tk.Button(
        root,
        text="LOGOUT",
        font=("Arial", 10),
        bg="white",
        command=logout
    ).pack(
        pady=12
    )


# ==========================================================
# START APPLICATION
# ==========================================================

welcome_screen()

root.mainloop()

conn.close()
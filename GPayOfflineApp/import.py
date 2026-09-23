import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image, ImageTk

# ==========================================================
# PAYFLOW - OFFLINE TRANSACTION APPLICATION
# Python + Tkinter + SQLite + OpenCV
# ==========================================================

# ---------------- DATABASE ----------------

db = sqlite3.connect("payflow.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person TEXT NOT NULL,
    amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT,
    date TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    account_no TEXT NOT NULL,
    balance REAL NOT NULL
)
""")

db.commit()

# ---------------- SETTINGS ----------------

BALANCE = 12345.67

BG = "#F6F8FC"
WHITE = "#FFFFFF"
BLUE = "#1769E0"
LIGHT_BLUE = "#EAF2FF"
TEXT = "#202124"
GRAY = "#6B7280"
GREEN = "#16A34A"
RED = "#DC2626"
BORDER = "#E1E5EA"


# ==========================================================
# MAIN APPLICATION
# ==========================================================

class PayFlowApp:

    def __init__(self, root):
        self.root = root
        self.root.title("PayFlow - Offline Transaction")
        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)
        self.root.configure(bg=BG)

        # OpenCV Camera Attributes
        self.cap = None
        self.camera_active = False

        self.create_sidebar()
        self.create_main_area()
        self.show_home()

    # ======================================================
    # BASIC FUNCTIONS
    # ======================================================

    def clear_screen(self):
        self.stop_camera()
        for widget in self.main.winfo_children():
            widget.destroy()

    def create_label(self, parent, text, size=12, bold=False, fg=TEXT, bg=WHITE):
        return tk.Label(
            parent,
            text=text,
            font=("Arial", size, "bold" if bold else "normal"),
            fg=fg,
            bg=bg
        )

    def create_card(self, parent):
        return tk.Frame(
            parent,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

    def create_button(self, parent, text, command, bg=WHITE, fg=TEXT):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Arial", 11, "bold"),
            bg=bg,
            fg=fg,
            activebackground=LIGHT_BLUE,
            activeforeground=BLUE,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=18,
            pady=9
        )

    # ======================================================
    # SIDEBAR
    # ======================================================

    def create_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=WHITE, width=280)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = tk.Frame(self.sidebar, bg=WHITE)
        logo.pack(fill="x", padx=35, pady=(30, 35))

        self.create_label(logo, "G", 34, True, BLUE, WHITE).pack(side="left")
        self.create_label(logo, "Pay", 30, False, "#5F6368", WHITE).pack(side="left")

        self.menu = [
            ("⌂", "Home", self.show_home),
            ("₹", "Payments", self.show_payment),
            ("▦", "Scan QR", self.show_qr),
            ("☷", "Transactions", self.show_transactions),
            ("♜", "Bank Accounts", self.show_banks),
            ("▤", "Bills & Recharge", self.show_bills),
            ("▣", "Passes", self.show_passes),
            ("☆", "Offers", self.show_offers),
            ("♙", "Profile", self.show_profile)
        ]

        self.menu_buttons = {}

        for icon, name, command in self.menu:
            button = tk.Button(
                self.sidebar,
                text=f"  {icon}     {name}",
                command=command,
                anchor="w",
                font=("Arial", 12),
                bg=WHITE,
                fg=TEXT,
                activebackground=LIGHT_BLUE,
                activeforeground=BLUE,
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=20,
                pady=12
            )
            button.pack(fill="x", padx=18, pady=2)
            self.menu_buttons[name] = button

    def set_active(self, active):
        for name, button in self.menu_buttons.items():
            if name == active:
                button.configure(bg=LIGHT_BLUE, fg=BLUE, font=("Arial", 12, "bold"))
            else:
                button.configure(bg=WHITE, fg=TEXT, font=("Arial", 12))

    def create_main_area(self):
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

    def header(self, title, back=False):
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", padx=40, pady=(28, 18))

        if back:
            self.create_button(header, "←", self.show_home, BG, TEXT).pack(side="left", padx=(0, 10))

        self.create_label(header, title, 25, True, TEXT, BG).pack(side="left")
        self.create_label(header, "●  Anzalana", 11, True, TEXT, BG).pack(side="right")

    # ======================================================
    # HOME & WORKING SEARCH BAR
    # ======================================================

    def show_home(self):
        self.clear_screen()
        self.set_active("Home")
        self.header("Welcome to PayFlow")

        search_frame = tk.Frame(self.main, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        search_frame.pack(fill="x", padx=40, pady=(0, 20))

        tk.Label(search_frame, text="🔍", font=("Arial", 12), bg=WHITE, fg=GRAY).pack(side="left", padx=(15, 5))

        self.search_entry = tk.Entry(search_frame, font=("Arial", 12), fg=TEXT, bg=WHITE, relief="flat", bd=0)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=12)
        
        # Placeholder functionality
        self.search_entry.insert(0, "Pay by name or phone number...")
        self.search_entry.config(fg=GRAY)

        def on_focus_in(event):
            if self.search_entry.get() == "Pay by name or phone number...":
                self.search_entry.delete(0, tk.END)
                self.search_entry.config(fg=TEXT)

        def on_focus_out(event):
            if not self.search_entry.get().strip():
                self.search_entry.insert(0, "Pay by name or phone number...")
                self.search_entry.config(fg=GRAY)

        self.search_entry.bind("<FocusIn>", on_focus_in)
        self.search_entry.bind("<FocusOut>", on_focus_out)
        self.search_entry.bind("<KeyRelease>", self.filter_search)
        self.search_entry.bind("<Return>", self.execute_search_action)

        quick = tk.Frame(self.main, bg=BG)
        quick.pack(fill="x", padx=40)

        actions = [
            ("▦", "Scan QR", self.show_qr),
            ("₹", "Pay", self.show_payment),
            ("▯", "Phone", self.show_payment),
            ("♜", "Bank", self.show_banks)
        ]

        for icon, name, command in actions:
            card = self.create_card(quick)
            card.pack(side="left", fill="both", expand=True, padx=6)
            self.create_label(card, icon, 28, True, BLUE, WHITE).pack(pady=(15, 3))
            self.create_button(card, name, command).pack()

        balance = tk.Frame(self.main, bg=BLUE)
        balance.pack(fill="x", padx=40, pady=22)

        self.create_label(balance, "Available Balance", 13, False, WHITE, BLUE).pack(anchor="w", padx=25, pady=(18, 2))
        self.create_label(balance, "₹ 12,345.67", 31, True, WHITE, BLUE).pack(anchor="w", padx=25)

        self.create_button(balance, "Check Balance", self.show_balance, WHITE, BLUE).pack(anchor="w", padx=25, pady=(8, 18))

        self.create_label(self.main, "Recent Transactions", 18, True, TEXT, BG).pack(anchor="w", padx=40, pady=(0, 8))

        # Dynamic container for filtered search results
        self.recent_card = self.create_card(self.main)
        self.recent_card.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self.show_recent()

    def filter_search(self, event=None):
        query = self.search_entry.get().strip()
        if query == "Pay by name or phone number...":
            query = ""
        self.show_recent(filter_query=query)

    def execute_search_action(self, event=None):
        query = self.search_entry.get().strip()
        if query and query != "Pay by name or phone number...":
            self.show_payment(preset_receiver=query)

    def show_recent(self, filter_query=""):
        for widget in self.recent_card.winfo_children():
            widget.destroy()

        if filter_query:
            cursor.execute("""
            SELECT person, amount, status, date
            FROM transactions
            WHERE person LIKE ? OR note LIKE ?
            ORDER BY id DESC
            """, (f"%{filter_query}%", f"%{filter_query}%"))
        else:
            cursor.execute("""
            SELECT person, amount, status, date
            FROM transactions
            ORDER BY id DESC
            LIMIT 5
            """)
            
        rows = cursor.fetchall()

        if not rows and not filter_query:
            rows = [
                ("Rohit Sharma", 500, "Paid", "Today, 09:30 AM"),
                ("Meera Patil", 300, "Received", "Today, 08:45 AM"),
                ("Amit Kumar", 250, "Paid", "Yesterday, 07:30 PM"),
                ("Priya Singh", 450, "Paid", "Yesterday, 06:15 PM")
            ]

        if not rows and filter_query:
            no_res = tk.Frame(self.recent_card, bg=WHITE)
            no_res.pack(fill="both", expand=True, pady=30)
            self.create_label(no_res, f"No transactions matching '{filter_query}'", 11, False, GRAY, WHITE).pack()
            self.create_button(
                no_res, f"Pay to '{filter_query}'",
                lambda: self.show_payment(preset_receiver=filter_query),
                BLUE, WHITE
            ).pack(pady=10)
            return

        for person, amount, status, date in rows:
            row = tk.Frame(self.recent_card, bg=WHITE)
            row.pack(fill="x", padx=20, pady=5)

            initials = "".join(x[0] for x in person.split()[:2])

            tk.Label(
                row, text=initials, font=("Arial", 10, "bold"),
                fg=BLUE, bg="#EEF2FF", width=4, height=2
            ).pack(side="left", padx=8)

            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", fill="x", expand=True)

            self.create_label(info, person, 11, True, TEXT, WHITE).pack(anchor="w")
            self.create_label(info, status, 9, False, GREEN if status == "Received" else GRAY, WHITE).pack(anchor="w")

            self.create_label(row, f"₹{amount:,.2f}", 11, True, BLUE, WHITE).pack(side="left", padx=35)
            self.create_button(row, "Pay Again", lambda p=person: self.show_payment(preset_receiver=p), WHITE, BLUE).pack(side="right", padx=10)

        if not filter_query:
            self.create_button(self.recent_card, "View All Transactions", self.show_transactions, WHITE, BLUE).pack(pady=8)

    # ======================================================
    # PAYMENT
    # ======================================================

    def show_payment(self, preset_receiver="", preset_note="", preset_amount=""):
        self.clear_screen()
        self.set_active("Payments")
        self.header("Pay / Send Money", True)

        form = self.create_card(self.main)
        form.pack(fill="x", padx=40)

        self.create_label(form, "➤", 35, True, BLUE, WHITE).pack(pady=(25, 0))
        self.create_label(form, "Send Money", 24, True, TEXT, WHITE).pack()
        self.create_label(form, "Enter details to send money", 11, False, GRAY, WHITE).pack(pady=(3, 20))

        inside = tk.Frame(form, bg=WHITE)
        inside.pack(fill="x", padx=150)

        self.create_label(inside, "Receiver Name / UPI ID", 10, False, GRAY, WHITE).pack(anchor="w")
        self.receiver = tk.Entry(inside, font=("Arial", 13), relief="solid", bd=1)
        self.receiver.pack(fill="x", ipady=11, pady=(3, 15))

        if preset_receiver:
            self.receiver.insert(0, preset_receiver)

        self.create_label(inside, "Amount (₹)", 10, False, GRAY, WHITE).pack(anchor="w")
        self.amount = tk.Entry(inside, font=("Arial", 13), relief="solid", bd=1)
        self.amount.pack(fill="x", ipady=11, pady=(3, 15))

        if preset_amount:
            self.amount.insert(0, preset_amount)

        self.create_label(inside, "Note (Optional)", 10, False, GRAY, WHITE).pack(anchor="w")
        self.note = tk.Entry(inside, font=("Arial", 13), relief="solid", bd=1)
        self.note.pack(fill="x", ipady=11, pady=(3, 20))

        if preset_note:
            self.note.insert(0, preset_note)

        self.create_button(inside, "➤  Pay Now", self.make_payment, BLUE, WHITE).pack(fill="x", pady=(0, 25))

        contacts = self.create_card(self.main)
        contacts.pack(fill="x", padx=40, pady=18)

        self.create_label(contacts, "Recent Contacts", 14, True, TEXT, WHITE).pack(anchor="w", padx=20, pady=15)

        people = ["Rohit Sharma", "Meera Patil", "Amit Kumar", "Priya Singh"]
        row = tk.Frame(contacts, bg=WHITE)
        row.pack(fill="x", padx=15, pady=10)

        for person in people:
            self.create_button(
                row, person, lambda p=person: self.select_person(p), WHITE, TEXT
            ).pack(side="left", fill="x", expand=True, padx=5)

    def select_person(self, person):
        self.receiver.delete(0, tk.END)
        self.receiver.insert(0, person)

    def make_payment(self):
        person = self.receiver.get().strip()
        amount_text = self.amount.get().strip()
        note = self.note.get().strip()

        if not person:
            messagebox.showwarning("Required", "Please enter receiver name.")
            return

        try:
            amount = float(amount_text)
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid amount.")
            return

        if amount <= 0:
            messagebox.showerror("Invalid Amount", "Amount must be greater than zero.")
            return

        if amount > BALANCE:
            messagebox.showerror("Insufficient Balance", "Insufficient balance.")
            return

        date = datetime.now().strftime("%d %b %Y, %I:%M %p")

        cursor.execute("""
        INSERT INTO transactions
        (person, amount, transaction_type, status, note, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (person, amount, "Paid", "Success", note, date))

        db.commit()

        self.show_success(person, amount, date)

    def show_success(self, person, amount, date):
        self.clear_screen()
        self.set_active("Payments")
        self.header("Payment Successful", True)

        card = self.create_card(self.main)
        card.pack(fill="both", expand=True, padx=200, pady=35)

        self.create_label(card, "✓", 70, True, GREEN, WHITE).pack(pady=(45, 10))
        self.create_label(card, "Payment Successful", 24, True, TEXT, WHITE).pack()
        self.create_label(card, f"₹ {amount:,.2f}", 34, True, TEXT, WHITE).pack(pady=15)
        self.create_label(card, f"Paid to {person}", 13, False, TEXT, WHITE).pack()
        self.create_label(card, date, 10, False, GRAY, WHITE).pack(pady=8)

        self.create_label(
            card,
            "UPI Transaction ID: " + datetime.now().strftime("PF%Y%m%d%H%M%S"),
            9, False, GRAY, WHITE
        ).pack()

        self.create_button(card, "Back to Home", self.show_home, BLUE, WHITE).pack(pady=25)

    # ======================================================
    # AUTOMATIC QR SCANNER
    # ======================================================

    def show_qr(self):
        self.clear_screen()
        self.set_active("Scan QR")
        self.header("Scan QR Code", True)

        card = self.create_card(self.main)
        card.pack(fill="both", expand=True, padx=150, pady=20)

        self.qr_label = tk.Label(card, bg="#000000", width=420, height=300)
        self.qr_label.pack(pady=(20, 10))

        self.create_label(card, "Scan QR Code", 20, True, TEXT, WHITE).pack()
        self.create_label(card, "Align QR code inside camera frame or upload image from gallery", 10, False, GRAY, WHITE).pack(pady=5)

        btn_frame = tk.Frame(card, bg=WHITE)
        btn_frame.pack(pady=15)

        self.create_button(btn_frame, "📷 Restart Camera", self.start_camera, BLUE, WHITE).pack(side="left", padx=8)
        self.create_button(btn_frame, "🖼️ Import Gallery", self.import_qr_image, WHITE, BLUE).pack(side="left", padx=8)
        self.create_button(btn_frame, "Manual Payment", self.show_payment, WHITE, TEXT).pack(side="left", padx=8)

        self.start_camera()

    def start_camera(self):
        self.stop_camera()
        
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Webcam access denied or used by another application.")
            return

        self.camera_active = True
        self.detector = cv2.QRCodeDetector()
        self.update_camera_feed()

    def stop_camera(self):
        self.camera_active = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def update_camera_feed(self):
        if self.camera_active and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                data, bbox, _ = self.detector.detectAndDecode(frame)

                if data:
                    self.stop_camera()
                    self.process_qr_data(data)
                    return

                height, width, _ = frame.shape
                cv2.rectangle(
                    frame,
                    (int(width * 0.2), int(height * 0.2)),
                    (int(width * 0.8), int(height * 0.8)),
                    (224, 105, 23),
                    2
                )

                cv2_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2_image).resize((420, 300))
                imgtk = ImageTk.PhotoImage(image=img)
                self.qr_label.imgtk = imgtk
                self.qr_label.configure(image=imgtk)

            self.root.after(30, self.update_camera_feed)

    def import_qr_image(self):
        self.stop_camera()
        file_path = filedialog.askopenfilename(
            title="Select QR Code Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")]
        )

        if file_path:
            img = cv2.imread(file_path)
            if img is None:
                messagebox.showerror("Error", "Could not load selected image.")
                return

            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img)

            if data:
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_img).resize((420, 300))
                imgtk = ImageTk.PhotoImage(image=pil_img)
                self.qr_label.imgtk = imgtk
                self.qr_label.configure(image=imgtk)

                self.process_qr_data(data)
            else:
                messagebox.showwarning("QR Reader", "No valid QR code detected in selected image.")

    def process_qr_data(self, qr_text):
        receiver = qr_text
        amount = ""

        if "upi://" in qr_text:
            params = qr_text.split("?")[-1].split("&")
            for param in params:
                if param.startswith("pn="):
                    receiver = param.split("=")[1].replace("%20", " ")
                elif param.startswith("pa=") and not receiver:
                    receiver = param.split("=")[1]
                elif param.startswith("am="):
                    amount = param.split("=")[1]

        messagebox.showinfo("QR Code Scanned", f"Scanned Payee: {receiver}\nRedirecting...")
        self.show_payment(preset_receiver=receiver, preset_amount=amount)

    # ======================================================
    # OTHER SECTIONS
    # ======================================================

    def show_balance(self):
        self.clear_screen()
        self.set_active("Bank Accounts")
        self.header("Account Balance", True)

        card = self.create_card(self.main)
        card.pack(fill="x", padx=150, pady=40)

        self.create_label(card, "State Bank of India", 14, True, TEXT, WHITE).pack(anchor="w", padx=30, pady=(25, 3))
        self.create_label(card, "A/c •• 1234", 10, False, GRAY, WHITE).pack(anchor="w", padx=30)
        self.create_label(card, "₹ 12,345.67", 31, True, TEXT, WHITE).pack(anchor="w", padx=30, pady=20)

        self.create_button(
            card,
            "Refresh Balance",
            lambda: messagebox.showinfo("Balance", "Available Balance: ₹12,345.67"),
            BLUE, WHITE
        ).pack(anchor="w", padx=30, pady=(0, 25))

    def show_banks(self):
        self.clear_screen()
        self.set_active("Bank Accounts")
        self.header("Bank Accounts")

        cursor.execute("SELECT name, account_no, balance FROM bank_accounts")
        banks = cursor.fetchall()

        if not banks:
            defaults = [
                ("State Bank of India", "A/c •• 1234", 12345.67),
                ("HDFC Bank", "A/c •• 5678", 8765.43),
                ("ICICI Bank", "A/c •• 9012", 5432.10),
                ("Axis Bank", "A/c •• 3456", 3250.00)
            ]
            cursor.executemany("INSERT INTO bank_accounts (name, account_no, balance) VALUES (?, ?, ?)", defaults)
            db.commit()
            banks = defaults

        for name, account, balance in banks:
            card = self.create_card(self.main)
            card.pack(fill="x", padx=90, pady=6)

            self.create_label(card, "♜", 25, True, BLUE, WHITE).pack(side="left", padx=20, pady=15)

            info = tk.Frame(card, bg=WHITE)
            info.pack(side="left")

            self.create_label(info, name, 12, True, TEXT, WHITE).pack(anchor="w")
            self.create_label(info, account, 10, False, GRAY, WHITE).pack(anchor="w")

            formatted_balance = f"₹{balance:,.2f}" if isinstance(balance, (int, float)) else str(balance)
            self.create_label(card, formatted_balance, 12, True, BLUE, WHITE).pack(side="right", padx=25)

        self.create_button(self.main, "+ Add Bank Account", self.open_add_bank_window, BLUE, WHITE).pack(anchor="w", padx=90, pady=20)

    def open_add_bank_window(self):
        top = tk.Toplevel(self.root)
        top.title("Add New Bank Account")
        top.geometry("400x450")
        top.configure(bg=WHITE)
        top.grab_set()

        self.create_label(top, "Add Bank Account", 16, True, TEXT, WHITE).pack(pady=20)

        self.create_label(top, "Bank Name", 10, False, GRAY, WHITE).pack(anchor="w", padx=40)
        bank_name_entry = tk.Entry(top, font=("Arial", 12), relief="solid", bd=1)
        bank_name_entry.pack(fill="x", padx=40, ipady=6, pady=(3, 15))

        self.create_label(top, "Account Number (4 digits)", 10, False, GRAY, WHITE).pack(anchor="w", padx=40)
        acc_no_entry = tk.Entry(top, font=("Arial", 12), relief="solid", bd=1)
        acc_no_entry.pack(fill="x", padx=40, ipady=6, pady=(3, 15))

        self.create_label(top, "Initial Balance (₹)", 10, False, GRAY, WHITE).pack(anchor="w", padx=40)
        balance_entry = tk.Entry(top, font=("Arial", 12), relief="solid", bd=1)
        balance_entry.pack(fill="x", padx=40, ipady=6, pady=(3, 20))

        self.create_button(
            top, "Save Bank Account",
            lambda: self.save_bank_account(bank_name_entry.get(), acc_no_entry.get(), balance_entry.get(), top),
            BLUE, WHITE
        ).pack(fill="x", padx=40, pady=10)

    def save_bank_account(self, name, acc_no, balance, window):
        if not name or not acc_no or not balance:
            messagebox.showwarning("Warning", "All fields are required!", parent=window)
            return

        try:
            bal_float = float(balance)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid numeric balance.", parent=window)
            return

        acc_str = f"A/c •• {acc_no[-4:]}"

        cursor.execute("INSERT INTO bank_accounts (name, account_no, balance) VALUES (?, ?, ?)", (name, acc_str, bal_float))
        db.commit()

        messagebox.showinfo("Success", "Bank account added successfully!", parent=window)
        window.destroy()
        self.show_banks()

    def show_transactions(self):
        self.clear_screen()
        self.set_active("Transactions")
        self.header("Transaction History")

        card = self.create_card(self.main)
        card.pack(fill="both", expand=True, padx=40, pady=10)

        headers = ["Person", "Amount", "Type", "Status", "Date"]

        for column, heading in enumerate(headers):
            self.create_label(card, heading, 10, True, TEXT, WHITE).grid(row=0, column=column, padx=25, pady=15, sticky="w")

        cursor.execute("""
        SELECT person, amount, transaction_type, status, date
        FROM transactions
        ORDER BY id DESC
        """)
        rows = cursor.fetchall()

        if not rows:
            self.create_label(card, "No transactions yet.", 12, False, GRAY, WHITE).grid(row=1, column=0, columnspan=5, pady=30)

        for row_index, row in enumerate(rows, start=1):
            for column, value in enumerate(row):
                if column == 1:
                    value = f"₹{value:,.2f}"

                color = GREEN if column == 3 and value == "Success" else TEXT

                self.create_label(card, value, 10, column == 1, color, WHITE).grid(
                    row=row_index, column=column, padx=25, pady=10, sticky="w"
                )

    def show_bills(self):
        self.clear_screen()
        self.set_active("Bills & Recharge")
        self.header("Bills & Recharge")

        services = [
            "Mobile Recharge", "DTH Recharge", "Electricity", "Water",
            "Gas", "Broadband", "Education", "Postpaid"
        ]

        grid = tk.Frame(self.main, bg=BG)
        grid.pack(fill="both", expand=True, padx=70, pady=20)

        for index, service in enumerate(services):
            card = self.create_card(grid)
            card.grid(row=index // 4, column=index % 4, padx=10, pady=10, sticky="nsew")

            self.create_label(card, "₹", 30, True, BLUE, WHITE).pack(pady=(20, 5))
            self.create_label(card, service, 11, True, TEXT, WHITE).pack()

            self.create_button(card, "Pay", lambda s=service: self.open_bill_payment(s), BLUE, WHITE).pack(pady=15)

        for column in range(4):
            grid.columnconfigure(column, weight=1)

    def open_bill_payment(self, service_name, note=""):
        self.show_payment(preset_receiver=service_name, preset_note=note)

    def show_passes(self):
        self.clear_screen()
        self.set_active("Passes")
        self.header("Passes")

        passes = [
            "Flight Tickets", "Train Tickets", "Bus Tickets",
            "Movie Tickets", "Events", "Loyalty Cards"
        ]

        for item in passes:
            card = self.create_card(self.main)
            card.pack(fill="x", padx=100, pady=6)

            self.create_label(card, "▣   " + item, 13, True, TEXT, WHITE).pack(side="left", padx=25, pady=18)
            self.create_button(card, "View", lambda x=item: self.open_pass_details(x), WHITE, BLUE).pack(side="right", padx=20)

    def open_pass_details(self, pass_name):
        self.clear_screen()
        self.set_active("Passes")
        self.header(pass_name, True)

        card = self.create_card(self.main)
        card.pack(fill="both", expand=True, padx=150, pady=30)

        self.create_label(card, "▣", 50, True, BLUE, WHITE).pack(pady=(30, 10))
        self.create_label(card, pass_name, 20, True, TEXT, WHITE).pack()
        self.create_label(card, "No active passes found for " + pass_name, 11, False, GRAY, WHITE).pack(pady=10)

        self.create_button(card, "Book / Add New", lambda: self.open_bill_payment(pass_name), BLUE, WHITE).pack(pady=20)

    def show_offers(self):
        self.clear_screen()
        self.set_active("Offers")
        self.header("Offers")

        self.notification_frame = tk.Frame(self.main, bg=BG)
        self.notification_frame.pack(fill="x", padx=100, pady=(0, 10))

        offers = [
            ("Flat ₹50 Cashback", "Applicable on transactions over ₹200", "CB50", "Send Money"),
            ("₹100 Off on DTH Recharge", "Use code DTH100 on your next recharge", "DTH100", "DTH Recharge"),
            ("20% Off on Shopping", "Valid at selected retail partner stores", "SHOP20", "Scan QR"),
            ("₹75 Cashback on Bills", "Applicable on Electricity & Water bill payments", "BILLS75", "Bills & Recharge")
        ]

        for title, desc, code, action in offers:
            card = self.create_card(self.main)
            card.pack(fill="x", padx=100, pady=7)

            self.create_label(card, "★", 26, True, BLUE, WHITE).pack(side="left", padx=20, pady=15)

            info = tk.Frame(card, bg=WHITE)
            info.pack(side="left", fill="x", expand=True)

            self.create_label(info, title, 13, True, TEXT, WHITE).pack(anchor="w")
            self.create_label(info, desc, 10, False, GRAY, WHITE).pack(anchor="w")

            self.create_button(
                card, "Apply Offer", lambda t=title, c=code, a=action: self.redeem_offer(t, c, a), BLUE, WHITE
            ).pack(side="right", padx=20)

    def redeem_offer(self, title, code, action):
        for widget in self.notification_frame.winfo_children():
            widget.destroy()

        banner = tk.Frame(self.notification_frame, bg="#E8F0FE", highlightbackground=BLUE, highlightthickness=1)
        banner.pack(fill="x", ipady=10, ipadx=15)

        msg_label = tk.Label(
            banner,
            text=f"✓  Offer Applied! '{title}' activated using code '{code}'. Redirecting...",
            font=("Arial", 11, "bold"),
            fg=BLUE,
            bg="#E8F0FE"
        )
        msg_label.pack(side="left", padx=10)

        def redirect():
            if action == "Send Money":
                self.show_payment(preset_note=f"Offer Code: {code}")
            elif action == "DTH Recharge":
                self.open_bill_payment("DTH Recharge", note=f"Applied Code: {code}")
            elif action == "Scan QR":
                self.show_qr()
            elif action == "Bills & Recharge":
                self.show_bills()

        self.root.after(1200, redirect)

    def show_profile(self):
        self.clear_screen()
        self.set_active("Profile")
        self.header("Profile")

        card = self.create_card(self.main)
        card.pack(fill="x", padx=170, pady=30)

        self.create_label(card, "♙", 60, True, BLUE, WHITE).pack(pady=(25, 5))
        self.create_label(card, "Anzalana", 22, True, TEXT, WHITE).pack()
        self.create_label(card, "anzalana@example.com", 10, False, GRAY, WHITE).pack(pady=5)

        options = [
            "Personal Information", "Payment Methods", "Addresses",
            "Invite Friends", "Settings", "Help & Feedback"
        ]

        for option in options:
            self.create_button(
                card, option, lambda x=option: messagebox.showinfo(x, f"{x} selected."), WHITE, TEXT
            ).pack(fill="x", padx=25, pady=2)


# ==========================================================
# START APPLICATION
# ==========================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = PayFlowApp(root)

    def close_application():
        app.stop_camera()
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close_application)
    root.mainloop()
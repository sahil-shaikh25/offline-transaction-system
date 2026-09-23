import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sqlite3
import hashlib

try:
    from PIL import Image, ImageTk, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import backend

# ==========================================================
# OFFPAY - THEME & INITIALIZATION
# ==========================================================

BG = "#F2F7F6"
WHITE = "#FFFFFF"
NAVY = "#0B2320"
NAVY_2 = "#123832"
PRIMARY = "#0FA98D"
PRIMARY_DARK = "#0C8672"
PRIMARY_LIGHT = "#E1F7F1"
TEXT = "#10241F"
MUTED = "#6C7A77"
BORDER = "#DCE7E3"
SUCCESS = "#1E9E5A"
SUCCESS_LIGHT = "#E4F8EC"
DANGER = "#D2483F"
DANGER_LIGHT = "#FCEAE8"
WARNING = "#C98A1C"
WARNING_LIGHT = "#FCF1DD"
INFO = "#3172C4"
INFO_LIGHT = "#EAF1FB"

FONT = "Segoe UI"

root = tk.Tk()
root.title("OffPay - Offline Transaction Management System")
root.geometry("1000x720")
root.minsize(900, 650)
root.configure(bg=BG)

current_user = None
current_merchant = None
current_admin = None
selected_profile_photo = None
selected_merchant_photo = None
merchant_map = {}
network_monitor_job = None
last_network_state = None

# ==========================================================
# DIRECT DB FALLBACK FOR MERCHANT UPDATE
# ==========================================================

def safe_update_merchant_profile(merchant_id, name, email, password, address, photo=None):
    if hasattr(backend, "update_merchant_profile"):
        return backend.update_merchant_profile(merchant_id, name, email, password, address, photo)
    try:
        c = sqlite3.connect("offline_transaction.db")
        cur = c.cursor()
        if password:
            hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
            cur.execute("""
                UPDATE merchants 
                SET merchant_name = ?, email = ?, password = ?, business_address = ?, profile_photo = ?
                WHERE merchant_id = ?
            """, (name, email, hashed, address, photo, merchant_id))
        else:
            cur.execute("""
                UPDATE merchants 
                SET merchant_name = ?, email = ?, business_address = ?, profile_photo = ?
                WHERE merchant_id = ?
            """, (name, email, address, photo, merchant_id))
        c.commit()
        c.close()
        return True, "Merchant profile updated successfully."
    except Exception as e:
        return False, str(e)

# ==========================================================
# COMMON UI HELPERS & SMOOTH SCROLLING
# ==========================================================

def clear_screen():
    stop_network_monitor()
    try:
        root.unbind_all("<MouseWheel>")
        root.unbind_all("<Button-4>")
        root.unbind_all("<Button-5>")
    except Exception:
        pass
    for widget in root.winfo_children():
        widget.destroy()

def make_label(parent, text="", size=11, weight="normal", color=TEXT, bg=None, **kwargs):
    if bg is None:
        bg = parent.cget("bg") if "bg" in parent.keys() else WHITE
    return tk.Label(parent, text=text, font=(FONT, size, weight), fg=color, bg=bg, **kwargs)

def card(parent, bg=WHITE, padx=20, pady=18):
    return tk.Frame(parent, bg=bg, highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1, bd=0, padx=padx, pady=pady)

def create_button(parent, text, command, width=None, bg=PRIMARY, fg=WHITE, height=1, font_size=10, padx=18, pady=10):
    btn = tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=PRIMARY_DARK if bg == PRIMARY else bg,
        activeforeground=fg, font=(FONT, font_size, "bold"),
        relief="flat", bd=0, cursor="hand2", padx=padx, pady=pady, highlightthickness=0
    )
    if width:
        btn.configure(width=width)
    return btn

def create_entry(parent, show=None, width=34):
    wrapper = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightcolor=PRIMARY, highlightthickness=1)
    entry = tk.Entry(wrapper, font=(FONT, 11), fg=TEXT, bg=WHITE, insertbackground=PRIMARY, relief="flat", bd=0, show=show, width=width)
    entry.pack(fill="x", padx=12, pady=9)
    return wrapper, entry

def label_text(parent, text):
    make_label(parent, text, 9, "bold", MUTED, bg=parent.cget("bg")).pack(anchor="w", pady=(10, 5))

def status_color(status):
    if status == "Completed":
        return SUCCESS
    if status in ("Rejected", "Failed", "Expired", "Suspended"):
        return DANGER
    if status in ("Pending Merchant Approval", "Pending Sync"):
        return WARNING
    return MUTED

def status_bg(status):
    if status == "Completed":
        return SUCCESS_LIGHT
    if status in ("Rejected", "Failed", "Expired", "Suspended"):
        return DANGER_LIGHT
    if status in ("Pending Merchant Approval", "Pending Sync"):
        return WARNING_LIGHT
    return INFO_LIGHT

def status_badge(parent, status):
    return tk.Label(parent, text=f"  {status}  ", font=(FONT, 9, "bold"), fg=status_color(status), bg=status_bg(status), padx=5, pady=3)

def masked_phone(phone):
    phone = str(phone)
    if len(phone) >= 4:
        return phone[:2] + "XXXXXX" + phone[-2:]
    return "XXXXXX"

def current_user_id():
    return current_user[0] if current_user else None

def current_merchant_id():
    return current_merchant[0] if current_merchant else None

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def make_scrollable(parent, bg=BG):
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    content = tk.Frame(canvas, bg=bg)
    window_id = canvas.create_window((0, 0), window=content, anchor="nw")

    def configure_content(event=None):
        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def configure_canvas(event):
        canvas.itemconfigure(window_id, width=event.width)

    content.bind("<Configure>", configure_content)
    canvas.bind("<Configure>", configure_canvas)

    def _on_mousewheel(event):
        try:
            if canvas.winfo_exists():
                if event.delta:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                elif event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
        except Exception:
            pass

    root.bind_all("<MouseWheel>", _on_mousewheel)
    root.bind_all("<Button-4>", _on_mousewheel)
    root.bind_all("<Button-5>", _on_mousewheel)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return content

def page_header(parent, title, subtitle="", back_command=None):
    header = tk.Frame(parent, bg=WHITE, height=82)
    header.pack(fill="x")
    header.pack_propagate(False)

    if back_command:
        create_button(header, "‹", back_command, bg=WHITE, fg=NAVY, font_size=22, padx=12, pady=1).pack(side="left", padx=(20, 5), pady=20)

    box = tk.Frame(header, bg=WHITE)
    box.pack(side="left", fill="y", padx=12 if back_command else 25)
    make_label(box, title, 18, "bold", TEXT, bg=WHITE).pack(anchor="w", pady=(17, 0))
    if subtitle:
        make_label(box, subtitle, 9, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(2, 0))

def nav_button(parent, text, command, active=False):
    bg = PRIMARY if active else NAVY_2
    return create_button(parent, text, command, bg=bg, fg=WHITE, font_size=9, padx=16, pady=9)

def info_stat(parent, title, value, icon=""):
    c = card(parent, WHITE, 15, 14)
    make_label(c, f"{icon}  {title}", 9, "bold", MUTED, bg=WHITE).pack(anchor="w")
    make_label(c, str(value), 20, "bold", TEXT, bg=WHITE).pack(anchor="w", pady=(6, 0))
    return c

def load_profile_photo(path, size=100):
    if not path or not os.path.exists(path) or not PIL_AVAILABLE:
        return None
    try:
        image = Image.open(path).convert("RGB")
        image = ImageOps.fit(image, (size, size))
        return ImageTk.PhotoImage(image)
    except Exception:
        return None

# ==========================================================
# NETWORK MONITOR
# ==========================================================

def stop_network_monitor():
    global network_monitor_job
    if network_monitor_job is not None:
        try:
            root.after_cancel(network_monitor_job)
        except Exception:
            pass
        network_monitor_job = None

def start_network_monitor():
    stop_network_monitor()
    check_network_and_auto_sync()

def check_network_and_auto_sync():
    global network_monitor_job, last_network_state
    if current_user is None:
        network_monitor_job = None
        return

    try:
        online = backend.is_network_available()
        if online and not last_network_state:
            success, _ = backend.sync_transactions(current_user[0])
            if success:
                dashboard()
        last_network_state = online
    except Exception:
        last_network_state = False

    network_monitor_job = root.after(5000, check_network_and_auto_sync)

# ==========================================================
# WELCOME & ROLE SELECTION
# ==========================================================

def welcome_screen():
    global current_user, current_merchant, current_admin, last_network_state
    clear_screen()
    current_user = None
    current_merchant = None
    current_admin = None
    last_network_state = None

    root.configure(bg=BG)
    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True)

    left = tk.Frame(main, bg=NAVY, width=420)
    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    brand = tk.Frame(left, bg=NAVY)
    brand.pack(fill="x", padx=35, pady=(35, 20))

    tk.Label(brand, text="O", font=(FONT, 30, "bold"), fg=WHITE, bg=PRIMARY, width=2, height=1).pack(side="left")
    make_label(brand, "OffPay", 25, "bold", WHITE, bg=NAVY).pack(side="left", padx=12)

    make_label(
        left,
        "Pay smarter.\nEven when you're offline.",
        23, "bold", WHITE, bg=NAVY,
        justify="left", wraplength=350
    ).pack(anchor="w", padx=35, pady=(25, 12))

    make_label(
        left,
        "A secure offline transaction management\nsystem with automatic synchronization.",
        10, "normal", "#B7BDD0", bg=NAVY,
        justify="left", wraplength=350
    ).pack(anchor="w", padx=35, pady=(0, 20))

    for text in [
        "✓  Secure transaction processing",
        "✓  Offline transaction support",
        "✓  Automatic synchronization",
        "✓  Customer, Merchant & Admin roles"
    ]:
        make_label(left, text, 10, "normal", "#DCE0EC", bg=NAVY).pack(anchor="w", padx=35, pady=5)

    make_label(
        left, "OFFLINE TRANSACTION MANAGEMENT SYSTEM",
        8, "bold", "#7F88A4", bg=NAVY
    ).pack(anchor="w", padx=35, side="bottom", pady=25)

    right = tk.Frame(main, bg=BG)
    right.pack(side="left", fill="both", expand=True)

    content = tk.Frame(right, bg=BG)
    content.place(relx=0.5, rely=0.5, anchor="center")

    make_label(content, "Welcome to OffPay", 28, "bold", TEXT, bg=BG).pack(anchor="w")
    make_label(content, "Offline payments, simplified.", 12, "normal", MUTED, bg=BG).pack(anchor="w", pady=(7, 28))

    welcome_card = card(content, WHITE, 28, 25)
    welcome_card.pack(fill="x")
    make_label(welcome_card, "Get started", 17, "bold", TEXT, bg=WHITE).pack(anchor="w")
    make_label(welcome_card, "Choose your account type to continue.", 10, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(4, 20))
    create_button(welcome_card, "GET STARTED", role_selection).pack(fill="x")

    make_label(content, "Secure Transaction  •  Offline Support", 9, "normal", MUTED, bg=BG).pack(pady=22)

def role_selection():
    clear_screen()
    page_header(root, "Choose your role", "Select how you want to use OffPay")
    content = make_scrollable(root)

    make_label(content, "Account type", 22, "bold", TEXT, bg=BG).pack(anchor="w", padx=55, pady=(45, 5))
    make_label(content, "Continue with the appropriate dashboard.", 10, "normal", MUTED, bg=BG).pack(anchor="w", padx=55, pady=(0, 25))

    roles = [
        ("CUSTOMER", "Register, login and make offline payments.", customer_options, "01"),
        ("MERCHANT", "Manage payment requests and merchant history.", merchant_options, "02"),
        ("ADMIN", "Monitor transactions and manage the system.", admin_login_screen, "03")
    ]

    for title, desc, command, number in roles:
        c = card(content, WHITE, 22, 18)
        c.pack(fill="x", padx=55, pady=8)
        tk.Label(c, text=number, font=(FONT, 10, "bold"), fg=PRIMARY, bg=PRIMARY_LIGHT, padx=10, pady=8).pack(side="left")
        info = tk.Frame(c, bg=WHITE)
        info.pack(side="left", fill="x", expand=True, padx=15)
        make_label(info, title, 13, "bold", TEXT, bg=WHITE).pack(anchor="w")
        make_label(info, desc, 9, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(3, 0))
        create_button(c, "OPEN  →", command, bg=PRIMARY_LIGHT, fg=PRIMARY, padx=12, pady=8).pack(side="right")

    create_button(content, "BACK", welcome_screen, bg=NAVY_2, padx=30, pady=9).pack(padx=55, pady=25, anchor="w")

# ==========================================================
# CUSTOMER WORKFLOW
# ==========================================================

def customer_options():
    clear_screen()
    page_header(root, "Customer", "Customer account access", role_selection)
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True)

    box = card(content, WHITE, 35, 30)
    box.place(relx=0.5, rely=0.43, anchor="center", relwidth=0.65)
    make_label(box, "Customer account", 21, "bold", TEXT, bg=WHITE).pack(anchor="w")
    make_label(box, "Create a new account or continue to your dashboard.", 10, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(5, 25))

    create_button(box, "REGISTER", registration_screen).pack(fill="x", pady=5)
    create_button(box, "LOGIN", login_screen, bg=NAVY_2).pack(fill="x", pady=5)
    create_button(box, "BACK", role_selection, bg="#E9EBF2", fg=TEXT).pack(fill="x", pady=(18, 0))

def registration_screen():
    clear_screen()
    page_header(root, "Create customer account", "Enter your details to register", customer_options)
    content = make_scrollable(root)

    form = card(content, WHITE, 30, 25)
    form.pack(padx=70, pady=35, fill="x")

    label_text(form, "FULL NAME")
    _, name_entry = create_entry(form)
    name_entry.master.pack(fill="x")

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")

    label_text(form, "EMAIL")
    _, email_entry = create_entry(form)
    email_entry.master.pack(fill="x")

    label_text(form, "PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    label_text(form, "4 DIGIT TRANSACTION PIN")
    _, pin_entry = create_entry(form, show="*")
    pin_entry.master.pack(fill="x")

    def register():
        name, phone, email, pwd, pin = name_entry.get().strip(), phone_entry.get().strip(), email_entry.get().strip(), password_entry.get().strip(), pin_entry.get().strip()
        if not all((name, phone, email, pwd, pin)):
            messagebox.showerror("Error", "Please fill all fields.")
            return
        if not phone.isdigit() or len(phone) != 10:
            messagebox.showerror("Error", "Phone must be exactly 10 digits.")
            return
        if "@" not in email or "." not in email:
            messagebox.showerror("Error", "Enter valid email.")
            return
        if len(pwd) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be exactly 4 digits.")
            return

        success, message = backend.register_user(name, phone, email, pwd, pin)
        if success:
            messagebox.showinfo("Success", "Registration Successful!\nStarting Balance: ₹5000")
            login_screen()
        else:
            messagebox.showerror("Registration Failed", message)

    create_button(form, "CREATE ACCOUNT", register).pack(fill="x", pady=(25, 8))
    create_button(form, "BACK", customer_options, bg="#E9EBF2", fg=TEXT).pack(fill="x")

def login_screen():
    clear_screen()
    page_header(root, "Welcome back", "Login to your customer account", customer_options)
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True)

    form = card(content, WHITE, 35, 30)
    form.place(relx=0.5, rely=0.43, anchor="center", relwidth=0.62)

    make_label(form, "Customer Login", 21, "bold", TEXT, bg=WHITE).pack(anchor="w")
    make_label(form, "Use your registered phone number and password.", 10, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(4, 20))

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")

    label_text(form, "PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    def login():
        global current_user
        phone, pwd = phone_entry.get().strip(), password_entry.get().strip()
        if not phone or not pwd:
            messagebox.showerror("Error", "Please fill credentials.")
            return
        user = backend.login_user(phone, pwd)
        if user:
            current_user = user
            start_network_monitor()
            dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid credentials.")

    create_button(form, "LOGIN", login).pack(fill="x", pady=(22, 8))
    create_button(form, "CREATE NEW ACCOUNT", registration_screen, bg=PRIMARY_LIGHT, fg=PRIMARY).pack(fill="x")
    create_button(form, "BACK", customer_options, bg="#E9EBF2", fg=TEXT).pack(fill="x", pady=(8, 0))

def dashboard():
    global current_user
    if not current_user:
        login_screen()
        return

    updated = backend.get_user(current_user[0])
    if updated:
        current_user = updated

    clear_screen()

    # Navbar
    navbar = tk.Frame(root, bg=NAVY, height=68)
    navbar.pack(fill="x")
    navbar.pack_propagate(False)

    brand = tk.Frame(navbar, bg=NAVY)
    brand.pack(side="left", padx=(22, 10))
    tk.Label(brand, text="O", font=(FONT, 16, "bold"), fg=WHITE, bg=PRIMARY, width=2).pack(side="left", pady=15)
    make_label(brand, "OffPay", 14, "bold", WHITE, bg=NAVY).pack(side="left", padx=8, pady=15)

    nav_area = tk.Frame(navbar, bg=NAVY)
    nav_area.pack(side="left", padx=6)
    nav_button(nav_area, "⌂ Dashboard", dashboard, True).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "⇄ Pay Offline", offline_transaction).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "↻ Sync", sync_transactions_screen).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "☷ History", transaction_history).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "◉ Profile", profile_settings).pack(side="left", padx=3, pady=14)

    actions_area = tk.Frame(navbar, bg=NAVY)
    actions_area.pack(side="right", padx=20)
    create_button(actions_area, "LOGOUT", customer_logout, bg="#9F3140", font_size=9, padx=14, pady=9).pack(side="right", pady=14)

    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True)

    top = tk.Frame(main, bg=WHITE, height=64)
    top.pack(fill="x")
    top.pack_propagate(False)
    make_label(top, "Dashboard", 17, "bold", TEXT, bg=WHITE).pack(side="left", padx=30)

    online = backend.is_network_available()
    tk.Label(top, text="●  ONLINE" if online else "●  OFFLINE", font=(FONT, 9, "bold"),
             fg=SUCCESS if online else DANGER, bg=SUCCESS_LIGHT if online else DANGER_LIGHT, padx=12, pady=6).pack(side="right", padx=25)

    content = make_scrollable(main)

    balance = float(current_user[6])
    reserved = float(current_user[7])
    available = balance - reserved

    welcome = tk.Frame(content, bg=BG)
    welcome.pack(fill="x", padx=30, pady=(25, 15))
    make_label(welcome, f"Hello, {current_user[1]} 👋", 22, "bold", TEXT, bg=BG).pack(anchor="w")

    balance_card = tk.Frame(content, bg=PRIMARY, padx=25, pady=22)
    balance_card.pack(fill="x", padx=30, pady=5)
    top_row = tk.Frame(balance_card, bg=PRIMARY)
    top_row.pack(fill="x")
    make_label(top_row, "AVAILABLE BALANCE", 9, "bold", "#DCD5FF", bg=PRIMARY).pack(side="left")
    make_label(top_row, "OffPay Wallet", 9, "bold", "#DCD5FF", bg=PRIMARY).pack(side="right")
    make_label(balance_card, f"₹ {available:,.2f}", 28, "bold", WHITE, bg=PRIMARY).pack(anchor="w", pady=(7, 5))
    make_label(balance_card, f"Wallet ₹{balance:,.2f}  •  Reserved ₹{reserved:,.2f}", 9, "normal", "#DDD8F8", bg=PRIMARY).pack(anchor="w")

    make_label(content, "Quick actions", 14, "bold", TEXT, bg=BG).pack(anchor="w", padx=30, pady=(20, 10))
    actions = tk.Frame(content, bg=BG)
    actions.pack(fill="x", padx=30)

    for icon, title, cmd in [("⇄", "Send Money", offline_transaction), ("↻", "Sync", sync_transactions_screen), ("☷", "History", transaction_history), ("◉", "Profile", profile_settings)]:
        a = card(actions, WHITE, 12, 12)
        a.pack(side="left", fill="both", expand=True, padx=4)
        a.configure(cursor="hand2")
        lbl_icon = tk.Label(a, text=icon, font=(FONT, 18, "bold"), fg=PRIMARY, bg=PRIMARY_LIGHT, width=2, pady=5, cursor="hand2")
        lbl_icon.pack()
        lbl_title = make_label(a, title, 9, "bold", TEXT, bg=WHITE, cursor="hand2")
        lbl_title.pack(pady=(7, 0))
        for w in (a, lbl_icon, lbl_title):
            w.bind("<Button-1>", lambda e, c=cmd: c())

    make_label(content, "Recent transactions", 14, "bold", TEXT, bg=BG).pack(anchor="w", padx=30, pady=(25, 10))
    history = backend.get_transaction_history(current_user[0])
    recent_box = tk.Frame(content, bg=BG)
    recent_box.pack(fill="x", padx=30, pady=(0, 10))

    if not history:
        empty = card(recent_box, WHITE, 20, 25)
        empty.pack(fill="x")
        make_label(empty, "No transactions yet.", 10, "normal", MUTED, bg=WHITE).pack()
    else:
        for tid, mname, amount, date, status, _, _ in history[:10]:
            row = tk.Frame(recent_box, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", pady=4)
            tk.Label(row, text="₹", font=(FONT, 12, "bold"), fg=PRIMARY, bg=PRIMARY_LIGHT, width=3, pady=8).pack(side="left", padx=12, pady=10)
            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", fill="x", expand=True, pady=9)
            make_label(info, mname, 10, "bold", TEXT, bg=WHITE).pack(anchor="w")
            make_label(info, f"{tid}  •  {date}", 8, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(2, 0))

            r_side = tk.Frame(row, bg=WHITE)
            r_side.pack(side="right", padx=14, pady=8)
            make_label(r_side, f"₹{float(amount):,.2f}", 10, "bold", TEXT, bg=WHITE).pack(anchor="e")
            status_badge(r_side, status).pack(anchor="e", pady=(3, 0))

    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def customer_logout():
    global current_user
    current_user = None
    stop_network_monitor()
    welcome_screen()

def profile_settings():
    global selected_profile_photo, current_user
    if not current_user:
        login_screen()
        return

    clear_screen()
    page_header(root, "Profile settings", "Manage your customer account", dashboard)
    content = make_scrollable(root)

    user = backend.get_user(current_user[0])
    form = card(content, WHITE, 30, 25)
    form.pack(padx=70, pady=20, fill="x")

    photo_area = tk.Frame(form, bg=WHITE)
    photo_area.pack(fill="x", pady=(0, 10))

    img_box = tk.Frame(photo_area, width=100, height=100, bg=PRIMARY_LIGHT)
    img_box.pack_propagate(False)
    img_box.pack(anchor="center")

    photo_label = tk.Label(img_box, text="👤", font=(FONT, 34), fg=PRIMARY, bg=PRIMARY_LIGHT)
    photo_label.pack(fill="both", expand=True)

    saved_photo = user[9] if len(user) > 9 else None
    if saved_photo:
        photo = load_profile_photo(saved_photo, 100)
        if photo:
            photo_label.configure(image=photo, text="")
            photo_label.image = photo

    selected_profile_photo = saved_photo

    def choose_photo():
        global selected_profile_photo
        if not PIL_AVAILABLE:
            messagebox.showwarning("Pillow Required", "Install Pillow: python -m pip install pillow")
            return
        path = filedialog.askopenfilename(title="Select Profile Photo", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if path:
            selected_profile_photo = path
            photo = load_profile_photo(path, 100)
            if photo:
                photo_label.configure(image=photo, text="")
                photo_label.image = photo

    create_button(photo_area, "CHOOSE PROFILE PHOTO", choose_photo, bg=PRIMARY_LIGHT, fg=PRIMARY, padx=16, pady=6).pack(pady=(8, 0))

    label_text(form, "FULL NAME")
    _, name_entry = create_entry(form)
    name_entry.master.pack(fill="x")
    name_entry.insert(0, user[1])

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")
    phone_entry.insert(0, user[2])
    phone_entry.configure(state="readonly")

    label_text(form, "EMAIL")
    _, email_entry = create_entry(form)
    email_entry.master.pack(fill="x")
    email_entry.insert(0, user[3])

    label_text(form, "NEW PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    label_text(form, "NEW TRANSACTION PIN")
    _, pin_entry = create_entry(form, show="*")
    pin_entry.master.pack(fill="x")

    def save_profile():
        name, email, pwd, pin = name_entry.get().strip(), email_entry.get().strip(), password_entry.get().strip(), pin_entry.get().strip()
        if not name or not email:
            messagebox.showerror("Error", "Name and email are required.")
            return
        if "@" not in email or "." not in email:
            messagebox.showerror("Error", "Enter a valid email.")
            return
        if not pwd or len(pwd) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be exactly 4 digits.")
            return

        success, message = backend.update_profile(user[0], name, email, pwd, pin, selected_profile_photo)
        if success:
            globals()["current_user"] = backend.get_user(user[0])
            messagebox.showinfo("Success", message)
            dashboard()
        else:
            messagebox.showerror("Update Failed", message)

    create_button(form, "SAVE CHANGES", save_profile).pack(fill="x", pady=(22, 8))
    create_button(form, "BACK TO DASHBOARD", dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x")
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def offline_transaction():
    if not current_user:
        login_screen()
        return

    clear_screen()
    page_header(root, "Send money", "Create an offline transaction", dashboard)
    content = make_scrollable(root)

    user = backend.get_user(current_user[0])
    available_balance = float(user[6]) - float(user[7])

    balance_card = tk.Frame(content, bg=PRIMARY, padx=25, pady=18)
    balance_card.pack(fill="x", padx=60, pady=25)
    make_label(balance_card, "AVAILABLE BALANCE", 9, "bold", "#DDD8F8", bg=PRIMARY).pack(anchor="w")
    make_label(balance_card, f"₹{available_balance:,.2f}", 24, "bold", WHITE, bg=PRIMARY).pack(anchor="w", pady=(5, 0))

    form = card(content, WHITE, 30, 25)
    form.pack(fill="x", padx=60, pady=5)

    merchants = backend.get_merchants()
    merchant_map.clear()
    merchant_values = [f"{m[1]}  (ID: M{m[0]:03d})" for m in merchants]
    for m in merchants:
        merchant_map[f"{m[1]}  (ID: M{m[0]:03d})"] = m[0]

    label_text(form, "SELECT MERCHANT")
    merchant_var = tk.StringVar()
    if merchant_values:
        merchant_var.set(merchant_values[0])
        merchant_menu = tk.OptionMenu(form, merchant_var, *merchant_values)
        merchant_menu.config(bg=WHITE, font=(FONT, 10), relief="flat", highlightthickness=1, highlightbackground=BORDER)
        merchant_menu.pack(fill="x", pady=(0, 5))
    else:
        make_label(form, "No active merchants available.", 10, "normal", DANGER, bg=WHITE).pack(anchor="w", pady=10)

    label_text(form, "PAYMENT AMOUNT")
    _, amount_entry = create_entry(form)
    amount_entry.master.pack(fill="x")
    make_label(form, "Maximum offline transaction: ₹2000", 8, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(4, 0))

    label_text(form, "TRANSACTION PIN")
    _, pin_entry = create_entry(form, show="*")
    pin_entry.master.pack(fill="x")

    def make_payment():
        if not merchant_values:
            messagebox.showerror("Error", "No active merchant available.")
            return
        amt_text, pin = amount_entry.get().strip(), pin_entry.get().strip()
        try:
            amount = float(amt_text)
        except ValueError:
            messagebox.showerror("Error", "Enter a valid numeric amount.")
            return

        if amount <= 0 or amount > 2000:
            messagebox.showerror("Error", "Amount must be between ₹1 and ₹2000.")
            return
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be exactly 4 digits.")
            return

        mid = merchant_map[merchant_var.get()]
        success, result = backend.create_offline_transaction(current_user[0], mid, amount, pin)
        if success:
            messagebox.showinfo("Transaction Created", f"Transaction ID: {result}\nAmount: ₹{amount:.2f}\nStatus: Pending Sync")
            dashboard()
        else:
            messagebox.showerror("Transaction Failed", result)

    create_button(form, "MAKE PAYMENT", make_payment).pack(fill="x", pady=(22, 8))
    create_button(form, "BACK", dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x")
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def sync_transactions_screen():
    if not current_user:
        login_screen()
        return

    clear_screen()
    page_header(root, "Sync transactions", "Synchronize offline payments when network is available", dashboard)
    content = make_scrollable(root)

    online = backend.is_network_available()
    tk.Label(content, text="●  ONLINE - Network available" if online else "●  OFFLINE - No internet connection",
             font=(FONT, 10, "bold"), fg=SUCCESS if online else DANGER, bg=SUCCESS_LIGHT if online else DANGER_LIGHT, padx=16, pady=8).pack(anchor="w", padx=60, pady=25)

    pending = backend.get_pending_transactions(current_user[0])
    if not pending:
        empty = card(content, WHITE, 25, 35)
        empty.pack(fill="x", padx=60, pady=10)
        make_label(empty, "✓", 30, "bold", SUCCESS, bg=WHITE).pack()
        make_label(empty, "Everything is synchronized.", 13, "bold", TEXT, bg=WHITE).pack(pady=(8, 3))
    else:
        make_label(content, f"{len(pending)} transaction(s) pending", 14, "bold", TEXT, bg=BG).pack(anchor="w", padx=60, pady=(0, 10))
        for tid, amt, date, status in pending:
            c = card(content, WHITE, 18, 15)
            c.pack(fill="x", padx=60, pady=5)
            row = tk.Frame(c, bg=WHITE)
            row.pack(fill="x")
            make_label(row, tid, 11, "bold", TEXT, bg=WHITE).pack(side="left")
            status_badge(row, status).pack(side="right")
            make_label(c, f"₹{float(amt):,.2f}  •  {date}", 10, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(8, 0))

        def sync_now():
            ok, msg = backend.sync_transactions(current_user[0])
            if ok:
                messagebox.showinfo("Sync Successful", msg)
            else:
                messagebox.showwarning("Sync Result", msg)
            sync_transactions_screen()

        if online:
            create_button(content, "SYNCHRONIZE NOW", sync_now).pack(fill="x", padx=60, pady=22)

    create_button(content, "BACK TO DASHBOARD", dashboard, bg="#E9EBF2", fg=TEXT).pack(padx=60, pady=10, fill="x")
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def transaction_history():
    if not current_user:
        login_screen()
        return

    clear_screen()
    page_header(root, "Transaction history", "View all your transactions", dashboard)
    content = make_scrollable(root)

    history = backend.get_transaction_history(current_user[0])
    if not history:
        empty = card(content, WHITE, 25, 35)
        empty.pack(fill="x", padx=60, pady=35)
        make_label(empty, "No transactions found.", 13, "bold", TEXT, bg=WHITE).pack()
    else:
        for tid, mname, amt, date, status, sync, _ in history:
            c = card(content, WHITE, 18, 15)
            c.pack(fill="x", padx=60, pady=5)
            top = tk.Frame(c, bg=WHITE)
            top.pack(fill="x")
            make_label(top, mname, 11, "bold", TEXT, bg=WHITE).pack(side="left")
            make_label(top, f"₹{float(amt):,.2f}", 11, "bold", TEXT, bg=WHITE).pack(side="right")
            make_label(c, f"{tid}  •  {date}", 9, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(5, 4))

            bottom = tk.Frame(c, bg=WHITE)
            bottom.pack(fill="x")
            status_badge(bottom, status).pack(side="left")
            make_label(bottom, f"Sync: {sync}", 8, "normal", MUTED, bg=WHITE).pack(side="left", padx=10)
            create_button(bottom, "VIEW STATUS", lambda t=tid: show_transaction_status(t), bg="#E9EBF2", fg=TEXT, padx=10, pady=5, font_size=8).pack(side="right")

    create_button(content, "BACK TO DASHBOARD", dashboard, bg="#E9EBF2", fg=TEXT).pack(padx=60, pady=20, fill="x")
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def show_transaction_status(transaction_id):
    details = backend.get_transaction_details(transaction_id, current_user[0])
    if not details:
        messagebox.showerror("Error", "Transaction not found.")
        return
    history = backend.get_transaction_status_history(transaction_id)
    text = f"Transaction: {details[0]}\nMerchant: {details[3]}\nAmount: ₹{details[4]:.2f}\nCurrent Status: {details[7]}\nSync Status: {details[8]}\nLast Updated: {details[9]}\n\nSTATUS FLOW:\n"
    for old, new, changed_at, by in history:
        text += f"• {old if old else 'Initiated'} → {new} ({changed_at} by {by})\n"
    messagebox.showinfo("Transaction Status", text)

# ==========================================================
# MERCHANT WORKFLOW
# ==========================================================

def merchant_options():
    clear_screen()
    page_header(root, "Merchant", "Merchant account access", role_selection)
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True)

    box = card(content, WHITE, 35, 30)
    box.place(relx=0.5, rely=0.43, anchor="center", relwidth=0.65)
    make_label(box, "Merchant account", 21, "bold", TEXT, bg=WHITE).pack(anchor="w")
    make_label(box, "Register your business or login to manage payments.", 10, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(5, 25))

    create_button(box, "MERCHANT REGISTER", merchant_registration_screen).pack(fill="x", pady=5)
    create_button(box, "MERCHANT LOGIN", merchant_login_screen, bg=NAVY_2).pack(fill="x", pady=5)
    create_button(box, "BACK", role_selection, bg="#E9EBF2", fg=TEXT).pack(fill="x", pady=(18, 0))

def merchant_registration_screen():
    clear_screen()
    page_header(root, "Merchant registration", "Register your business", merchant_options)
    content = make_scrollable(root)

    form = card(content, WHITE, 30, 25)
    form.pack(padx=70, pady=30, fill="x")

    label_text(form, "BUSINESS / MERCHANT NAME")
    _, name_entry = create_entry(form)
    name_entry.master.pack(fill="x")

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")

    label_text(form, "EMAIL")
    _, email_entry = create_entry(form)
    email_entry.master.pack(fill="x")

    label_text(form, "PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    label_text(form, "BUSINESS ADDRESS")
    _, address_entry = create_entry(form)
    address_entry.master.pack(fill="x")

    def register():
        name, phone, email, pwd, addr = name_entry.get().strip(), phone_entry.get().strip(), email_entry.get().strip(), password_entry.get().strip(), address_entry.get().strip()
        if not all((name, phone, email, pwd, addr)):
            messagebox.showerror("Error", "All fields are required.")
            return
        if not phone.isdigit() or len(phone) != 10:
            messagebox.showerror("Error", "Phone must be 10 digits.")
            return
        if len(pwd) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return

        success, message = backend.register_merchant(name, phone, email, pwd, addr)
        if success:
            messagebox.showinfo("Success", message)
            merchant_login_screen()
        else:
            messagebox.showerror("Registration Failed", message)

    create_button(form, "REGISTER MERCHANT", register).pack(fill="x", pady=(22, 8))
    create_button(form, "BACK", merchant_options, bg="#E9EBF2", fg=TEXT).pack(fill="x")
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def merchant_login_screen():
    clear_screen()
    page_header(root, "Merchant login", "Login to your merchant dashboard", merchant_options)
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True)

    form = card(content, WHITE, 35, 30)
    form.place(relx=0.5, rely=0.43, anchor="center", relwidth=0.62)
    make_label(form, "Merchant Login", 21, "bold", TEXT, bg=WHITE).pack(anchor="w")

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")

    label_text(form, "PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    def login():
        global current_merchant
        m = backend.login_merchant(phone_entry.get().strip(), password_entry.get().strip())
        if m:
            current_merchant = m
            merchant_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid credentials or suspended.")

    create_button(form, "LOGIN", login).pack(fill="x", pady=(22, 8))
    create_button(form, "REGISTER", merchant_registration_screen, bg=PRIMARY_LIGHT, fg=PRIMARY).pack(fill="x")
    create_button(form, "BACK", merchant_options, bg="#E9EBF2", fg=TEXT).pack(fill="x", pady=(8, 0))

def merchant_dashboard():
    global current_merchant
    current_merchant = backend.get_merchant(current_merchant[0])
    if not current_merchant:
        merchant_options()
        return

    clear_screen()
    navbar = tk.Frame(root, bg=NAVY, height=68)
    navbar.pack(fill="x")
    navbar.pack_propagate(False)

    brand = tk.Frame(navbar, bg=NAVY)
    brand.pack(side="left", padx=(22, 10))
    tk.Label(brand, text="O", font=(FONT, 16, "bold"), fg=WHITE, bg=PRIMARY, width=2).pack(side="left", pady=15)
    make_label(brand, "OffPay", 14, "bold", WHITE, bg=NAVY).pack(side="left", padx=8, pady=15)

    nav_area = tk.Frame(navbar, bg=NAVY)
    nav_area.pack(side="left", padx=6)
    nav_button(nav_area, "⌂ Dashboard", merchant_dashboard, True).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "◉ Pending Requests", merchant_pending_requests).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "☷ History", merchant_history).pack(side="left", padx=3, pady=14)
    nav_button(nav_area, "◌ Profile", merchant_profile).pack(side="left", padx=3, pady=14)

    create_button(navbar, "LOGOUT", merchant_logout, bg="#9F3140", font_size=9, padx=14, pady=9).pack(side="right", padx=20, pady=14)

    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True)

    top = tk.Frame(main, bg=WHITE, height=64)
    top.pack(fill="x")
    top.pack_propagate(False)
    make_label(top, "Merchant Dashboard", 17, "bold", TEXT, bg=WHITE).pack(side="left", padx=30)

    content = make_scrollable(main)
    make_label(content, f"Welcome, {current_merchant[1]}", 22, "bold", TEXT, bg=BG).pack(anchor="w", padx=30, pady=(25, 3))

    bal = tk.Frame(content, bg=PRIMARY, padx=25, pady=22)
    bal.pack(fill="x", padx=30, pady=15)
    make_label(bal, "MERCHANT WALLET BALANCE", 9, "bold", "#DDD8F8", bg=PRIMARY).pack(anchor="w")
    make_label(bal, f"₹ {safe_float(current_merchant[4]):,.2f}", 27, "bold", WHITE, bg=PRIMARY).pack(anchor="w", pady=(5, 0))

    requests = backend.get_merchant_requests(current_merchant[0])
    stats = tk.Frame(content, bg=BG)
    stats.pack(fill="x", padx=30, pady=10)
    info_stat(stats, "Pending Claims", len(requests), "◷").pack(side="left", fill="both", expand=True, padx=4)
    info_stat(stats, "Terminal ID", f"M{current_merchant[0]:03d}", "◉").pack(side="left", fill="both", expand=True, padx=4)

    create_button(content, "VIEW PENDING TRANSACTION REQUESTS", merchant_pending_requests).pack(fill="x", padx=30, pady=4)
    create_button(content, "VIEW TRANSACTION HISTORY", merchant_history, bg=NAVY_2).pack(fill="x", padx=30, pady=4)
    create_button(content, "EDIT MERCHANT PROFILE", merchant_profile, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=30, pady=4)
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def merchant_pending_requests():
    clear_screen()
    page_header(root, "Pending requests", "Approve or reject incoming offline transactions", merchant_dashboard)
    content = make_scrollable(root)

    requests = backend.get_merchant_requests(current_merchant[0])
    if not requests:
        empty = card(content, WHITE, 25, 35)
        empty.pack(fill="x", padx=60, pady=35)
        make_label(empty, "✓", 30, "bold", SUCCESS, bg=WHITE).pack()
        make_label(empty, "No transactions waiting for approval.", 12, "bold", TEXT, bg=WHITE).pack(pady=(7, 0))
    else:
        for tid, cname, phone, _, amount, date, status, sync in requests:
            c = card(content, WHITE, 20, 18)
            c.pack(fill="x", padx=60, pady=6)
            top = tk.Frame(c, bg=WHITE)
            top.pack(fill="x")
            make_label(top, tid, 11, "bold", TEXT, bg=WHITE).pack(side="left")
            status_badge(top, status).pack(side="right")
            make_label(c, f"Customer: {cname} ({masked_phone(phone)})", 9, "normal", TEXT, bg=WHITE).pack(anchor="w", pady=(8, 2))
            make_label(c, f"Amount: ₹{float(amount):,.2f}", 13, "bold", TEXT, bg=WHITE).pack(anchor="w", pady=(2, 2))

            btns = tk.Frame(c, bg=WHITE)
            btns.pack(fill="x", pady=(12, 0))

            def approve(t=tid):
                ok, msg = backend.approve_transaction(t, current_merchant[0])
                if ok:
                    messagebox.showinfo("Approved", msg)
                else:
                    messagebox.showerror("Error", msg)
                merchant_pending_requests()

            def reject(t=tid):
                ok, msg = backend.reject_transaction(t, current_merchant[0])
                if ok:
                    messagebox.showinfo("Rejected", msg)
                else:
                    messagebox.showerror("Error", msg)
                merchant_pending_requests()

            create_button(btns, "ACCEPT", approve, bg=SUCCESS, padx=16, pady=7).pack(side="left", fill="x", expand=True, padx=(0, 4))
            create_button(btns, "REJECT", reject, bg=DANGER, padx=16, pady=7).pack(side="left", fill="x", expand=True, padx=(4, 0))

    create_button(content, "BACK", merchant_dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=60, pady=20)
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def merchant_history():
    clear_screen()
    page_header(root, "Merchant transaction history", "View completed requests", merchant_dashboard)
    content = make_scrollable(root)

    history = backend.get_merchant_history(current_merchant[0])
    if not history:
        empty = card(content, WHITE, 25, 35)
        empty.pack(fill="x", padx=60, pady=35)
        make_label(empty, "No transactions found.", 12, "bold", TEXT, bg=WHITE).pack()
    else:
        for tid, cname, phone, amount, date, status, sync, _ in history:
            c = card(content, WHITE, 18, 15)
            c.pack(fill="x", padx=60, pady=5)
            row = tk.Frame(c, bg=WHITE)
            row.pack(fill="x")
            make_label(row, cname, 11, "bold", TEXT, bg=WHITE).pack(side="left")
            make_label(row, f"₹{float(amount):,.2f}", 11, "bold", TEXT, bg=WHITE).pack(side="right")
            make_label(c, f"{tid}  •  {date}", 9, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(5, 5))
            status_badge(c, status).pack(anchor="w")

    create_button(content, "BACK", merchant_dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=60, pady=20)
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

# ==========================================================
# MERCHANT PROFILE (FIXED 100PX COMPACT AVATAR & FULL VISIBILITY)
# ==========================================================

def merchant_profile():
    global current_merchant, selected_merchant_photo
    clear_screen()
    page_header(root, "Merchant Profile", "Manage your business account information", merchant_dashboard)
    content = make_scrollable(root)

    merchant = backend.get_merchant(current_merchant_id())
    if not merchant:
        messagebox.showerror("Error", "Merchant not found.")
        merchant_options()
        return

    form = card(content, WHITE, 30, 20)
    form.pack(fill="x", padx=70, pady=20)

    # Photo Upload Section (Compact 100x100px Container)
    photo_area = tk.Frame(form, bg=WHITE)
    photo_area.pack(fill="x", pady=(0, 10))

    img_box = tk.Frame(photo_area, width=100, height=100, bg=PRIMARY_LIGHT)
    img_box.pack_propagate(False)
    img_box.pack(anchor="center")

    photo_label = tk.Label(img_box, text="🏢", font=(FONT, 34), fg=PRIMARY, bg=PRIMARY_LIGHT)
    photo_label.pack(fill="both", expand=True)

    saved_photo = merchant[8] if len(merchant) > 8 else None
    if saved_photo:
        photo = load_profile_photo(saved_photo, 100)
        if photo:
            photo_label.configure(image=photo, text="")
            photo_label.image = photo

    selected_merchant_photo = saved_photo

    def choose_merchant_photo():
        global selected_merchant_photo
        if not PIL_AVAILABLE:
            messagebox.showwarning("Pillow Required", "Install Pillow: python -m pip install pillow")
            return
        path = filedialog.askopenfilename(title="Select Merchant Photo", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp")])
        if path:
            selected_merchant_photo = path
            photo = load_profile_photo(path, 100)
            if photo:
                photo_label.configure(image=photo, text="")
                photo_label.image = photo

    create_button(photo_area, "CHOOSE PROFILE PHOTO", choose_merchant_photo, bg=PRIMARY_LIGHT, fg=PRIMARY, padx=16, pady=6).pack(pady=(8, 0))

    info_hdr = tk.Frame(form, bg=WHITE)
    info_hdr.pack(fill="x", pady=(5, 10))
    make_label(info_hdr, str(merchant[1]), 18, "bold", TEXT, bg=WHITE).pack(anchor="w")
    balance_val = safe_float(merchant[4])
    make_label(info_hdr, f"Merchant ID: M{merchant[0]:03d}   •   Balance: ₹{balance_val:,.2f}", 9, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=(2, 0))

    tk.Frame(form, bg=BORDER, height=1).pack(fill="x", pady=12)

    # Form Fields
    label_text(form, "BUSINESS / MERCHANT NAME")
    _, name_entry = create_entry(form)
    name_entry.master.pack(fill="x")
    name_entry.insert(0, str(merchant[1]))

    label_text(form, "PHONE NUMBER")
    _, phone_entry = create_entry(form)
    phone_entry.master.pack(fill="x")
    phone_entry.insert(0, str(merchant[2]))
    phone_entry.configure(state="readonly")

    label_text(form, "EMAIL")
    _, email_entry = create_entry(form)
    email_entry.master.pack(fill="x")
    email_entry.insert(0, str(merchant[3] or ""))

    label_text(form, "NEW PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    label_text(form, "BUSINESS ADDRESS")
    _, address_entry = create_entry(form)
    address_entry.master.pack(fill="x")
    address_entry.insert(0, str(merchant[5] or ""))

    def save_merchant_profile():
        name = name_entry.get().strip()
        email = email_entry.get().strip()
        password = password_entry.get().strip()
        address = address_entry.get().strip()

        if not name or not email or not address:
            messagebox.showerror("Error", "Name, email and business address are required.")
            return
        if password and len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return

        success, message = safe_update_merchant_profile(
            merchant[0], name, email, password, address, selected_merchant_photo
        )
        if success:
            globals()["current_merchant"] = backend.get_merchant(merchant[0])
            messagebox.showinfo("Success", message)
            merchant_dashboard()
        else:
            messagebox.showerror("Update Failed", message)

    create_button(form, "SAVE CHANGES", save_merchant_profile).pack(fill="x", pady=(20, 8))
    create_button(form, "BACK TO DASHBOARD", merchant_dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x")
    
    # 80px bottom safe space for clear footer visibility
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def merchant_logout():
    global current_merchant
    current_merchant = None
    welcome_screen()

# ==========================================================
# ADMIN WORKFLOW
# ==========================================================

def admin_login_screen():
    clear_screen()
    page_header(root, "Admin login", "System administrator access", role_selection)
    content = tk.Frame(root, bg=BG)
    content.pack(fill="both", expand=True)

    form = card(content, WHITE, 35, 30)
    form.place(relx=0.5, rely=0.43, anchor="center", relwidth=0.62)
    make_label(form, "System Administrator", 21, "bold", TEXT, bg=WHITE).pack(anchor="w")

    label_text(form, "USERNAME")
    _, username_entry = create_entry(form)
    username_entry.master.pack(fill="x")

    label_text(form, "PASSWORD")
    _, password_entry = create_entry(form, show="*")
    password_entry.master.pack(fill="x")

    tk.Label(form, text="Default Demo: admin / admin123", fg=MUTED, bg=WHITE, font=(FONT, 8)).pack(anchor="w", pady=8)

    def login():
        global current_admin
        a = backend.login_admin(username_entry.get().strip(), password_entry.get().strip())
        if a:
            current_admin = a
            admin_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid admin credentials.")

    create_button(form, "LOGIN", login).pack(fill="x", pady=(15, 8))
    create_button(form, "BACK", role_selection, bg="#E9EBF2", fg=TEXT).pack(fill="x")

def admin_dashboard():
    global current_admin
    if not current_admin:
        admin_login_screen()
        return

    clear_screen()
    page_header(root, "Admin dashboard", "System overview and management", admin_login_screen)
    content = make_scrollable(root)

    stats = backend.get_admin_stats()
    grid = tk.Frame(content, bg=BG)
    grid.pack(fill="x", padx=45, pady=20)

    cards_data = [
        ("Customers", stats[0], INFO), ("Merchants", stats[1], PRIMARY),
        ("Transactions", stats[2], TEXT), ("Pending Sync", stats[3], WARNING),
        ("Pending Approval", stats[4], WARNING), ("Completed", stats[5], SUCCESS),
        ("Rejected", stats[6], DANGER),
    ]

    for i, (title, val, accent) in enumerate(cards_data):
        c = tk.Frame(grid, bg=WHITE, highlightbackground=BORDER, highlightthickness=1, padx=15, pady=14)
        c.grid(row=i // 2, column=i % 2, sticky="nsew", padx=5, pady=5)
        grid.grid_columnconfigure(i % 2, weight=1)
        tk.Frame(c, bg=accent, width=4).pack(side="left", fill="y", padx=(0, 12))
        make_label(c, title, 9, "bold", MUTED, bg=WHITE).pack(anchor="w")
        make_label(c, str(val), 20, "bold", TEXT, bg=WHITE).pack(anchor="w", pady=(4, 0))

    make_label(content, "Management", 14, "bold", TEXT, bg=BG).pack(anchor="w", padx=50, pady=(15, 10))
    create_button(content, "TRANSACTION MONITORING", admin_transactions).pack(fill="x", padx=50, pady=4)
    create_button(content, "MANAGE MERCHANTS", admin_merchants, bg=NAVY_2).pack(fill="x", padx=50, pady=4)
    create_button(content, "VIEW CUSTOMERS", admin_users, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=50, pady=4)
    create_button(content, "LOGOUT", admin_logout, bg=DANGER).pack(fill="x", padx=50, pady=(20, 30))
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def admin_transactions():
    clear_screen()
    page_header(root, "Transaction monitoring", "Monitor system-wide transaction status", admin_dashboard)
    content = make_scrollable(root)

    filter_bar = tk.Frame(content, bg=WHITE)
    filter_bar.pack(fill="x", padx=45, pady=20)
    make_label(filter_bar, "FILTER BY STATUS", 8, "bold", MUTED, bg=WHITE).pack(side="left", padx=15)

    filter_var = tk.StringVar(value="All")
    menu = tk.OptionMenu(filter_bar, filter_var, "All", "Pending Sync", "Pending Merchant Approval", "Completed", "Rejected")
    menu.config(width=25, bg=WHITE, relief="flat", highlightthickness=1, highlightbackground=BORDER)
    menu.pack(side="left", padx=5, pady=12)

    list_frame = tk.Frame(content, bg=BG)
    list_frame.pack(fill="both", expand=True, padx=45)

    def refresh():
        for w in list_frame.winfo_children():
            w.destroy()
        txns = backend.get_all_transactions(filter_var.get())
        if not txns:
            empty = card(list_frame, WHITE, 25, 30)
            empty.pack(fill="x", pady=10)
            make_label(empty, "No transactions found.", 11, "bold", TEXT, bg=WHITE).pack()
            return

        for tid, cname, phone, mname, amount, date, status, sync, upd in txns:
            c = card(list_frame, WHITE, 16, 14)
            c.pack(fill="x", pady=5)
            top = tk.Frame(c, bg=WHITE)
            top.pack(fill="x")
            make_label(top, tid, 10, "bold", TEXT, bg=WHITE).pack(side="left")
            make_label(top, f"₹{float(amount):,.2f}", 10, "bold", TEXT, bg=WHITE).pack(side="right")
            make_label(c, f"{cname} → {mname}", 9, "normal", TEXT, bg=WHITE).pack(anchor="w", pady=(6, 2))
            make_label(c, f"Customer: {masked_phone(phone)}  •  {date}", 8, "normal", MUTED, bg=WHITE).pack(anchor="w")
            status_badge(c, status).pack(anchor="w", pady=(7, 3))

            actions_box = tk.Frame(c, bg=WHITE)
            actions_box.pack(fill="x", pady=(6, 0))

            def details(t=tid):
                history = backend.get_transaction_status_history(t)
                text = f"Status Trail for {t}:\n\n"
                for o, n, at, by in history:
                    text += f"• {o if o else 'Init'} → {n} ({at} by {by})\n"
                messagebox.showinfo("Status History", text)

            create_button(actions_box, "STATUS HISTORY", details, bg="#E9EBF2", fg=TEXT, padx=10, pady=5, font_size=8).pack(side="right", padx=(4, 0))

            if status in ("Pending Merchant Approval", "Pending Sync"):
                def admin_appr(t=tid):
                    ok, msg = backend.approve_transaction(t, merchant_id=None)
                    if ok:
                        messagebox.showinfo("Approved", msg)
                    else:
                        messagebox.showerror("Error", msg)
                    refresh()

                def admin_rej(t=tid):
                    ok, msg = backend.reject_transaction(t, merchant_id=None)
                    if ok:
                        messagebox.showinfo("Rejected", msg)
                    else:
                        messagebox.showerror("Error", msg)
                    refresh()

                create_button(actions_box, "REJECT", admin_rej, bg=DANGER, padx=12, pady=5, font_size=8).pack(side="right", padx=(4, 0))
                create_button(actions_box, "APPROVE", admin_appr, bg=SUCCESS, padx=12, pady=5, font_size=8).pack(side="right", padx=(4, 0))

    filter_var.trace_add("write", lambda *args: refresh())
    create_button(content, "REFRESH", refresh, bg=PRIMARY_LIGHT, fg=PRIMARY, padx=18, pady=8).pack(anchor="e", padx=45, pady=(0, 8))
    refresh()
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def admin_merchants():
    clear_screen()
    page_header(root, "Merchant management", "Approve or suspend merchant terminals", admin_dashboard)
    content = make_scrollable(root)
    merchants = backend.get_all_merchants()

    list_frame = tk.Frame(content, bg=BG)
    list_frame.pack(fill="both", expand=True, padx=45, pady=20)

    for mid, mname, phone, email, bal, _, status, _ in merchants:
        c = card(list_frame, WHITE, 16, 12)
        c.pack(fill="x", pady=4)
        top = tk.Frame(c, bg=WHITE)
        top.pack(fill="x")
        make_label(top, f"M{mid:03d} - {mname}", 11, "bold", TEXT, bg=WHITE).pack(side="left")
        status_badge(top, status).pack(side="right")
        make_label(c, f"Phone: {phone} | Balance: ₹{float(bal):,.2f}", 8, "normal", MUTED, bg=WHITE).pack(anchor="w", pady=2)

        def toggle(m=mid, s=status):
            new_s = "Suspended" if s == "Active" else "Active"
            ok, msg = backend.update_merchant_status(m, new_s)
            if ok:
                messagebox.showinfo("Success", msg)
                admin_merchants()

        create_button(c, "SUSPEND" if status == "Active" else "ACTIVATE", toggle,
                      bg=DANGER if status == "Active" else SUCCESS, font_size=8, padx=8, pady=4).pack(anchor="e")

    create_button(content, "BACK", admin_dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=45, pady=15)
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def admin_users():
    clear_screen()
    page_header(root, "Customer registry", "Inspect platform customer accounts", admin_dashboard)
    content = make_scrollable(root)
    users = backend.get_all_users()

    list_frame = tk.Frame(content, bg=BG)
    list_frame.pack(fill="both", expand=True, padx=45, pady=20)

    for uid, name, phone, email, bal, res, reg in users:
        c = card(list_frame, WHITE, 14, 10)
        c.pack(fill="x", pady=4)
        top = tk.Frame(c, bg=WHITE)
        top.pack(fill="x")
        make_label(top, f"UID: {uid} - {name}", 10, "bold", TEXT, bg=WHITE).pack(side="left")
        make_label(top, f"Available: ₹{(bal - res):,.2f}", 10, "bold", PRIMARY, bg=WHITE).pack(side="right")
        make_label(c, f"Phone: {phone} | Email: {email} | Hold: ₹{res:,.2f} | Enrolled: {reg}", 8, "normal", MUTED, bg=WHITE).pack(anchor="w")

    create_button(content, "BACK", admin_dashboard, bg="#E9EBF2", fg=TEXT).pack(fill="x", padx=45, pady=15)
    tk.Frame(content, bg=BG, height=80).pack(fill="x")

def admin_logout():
    global current_admin
    current_admin = None
    welcome_screen()

# ==========================================================
# BOOTSTRAP INITIALIZATION
# ==========================================================

if __name__ == "__main__":
    welcome_screen()
    root.mainloop()
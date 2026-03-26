"""
IND AS 12 – Income Tax (Deferred Tax) Tool
==========================================
Single-file Python application using Tkinter + SQLite.
All 11 modules included:
  1. Login          6. Loss/Unabsorbed Dep.
  2. Company/FY     7. Net DTA/DTL Summary
  3. Opening Bal.   8. Future Profitability
  4. Tax Rate       9. Journal Entries
  5. Particulars   10. DTA/DTL Flow Table
                   11. Day/Night Mode
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
import os
import hashlib
from datetime import datetime, date
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & DB PATH
# ─────────────────────────────────────────────────────────────────────────────
APP_TITLE = "IND AS 12 – Income Tax (Deferred Tax) Tool"
DB_PATH = Path(__file__).parent / "ind_as12_data.db"

FINANCIAL_YEARS = [
    "2019-20", "2020-21", "2021-22", "2022-23",
    "2023-24", "2024-25", "2025-26", "2026-27",
]

ASSESSMENT_YEARS = [
    "AY 2019-20", "AY 2020-21", "AY 2021-22", "AY 2022-23",
    "AY 2023-24", "AY 2024-25", "AY 2025-26", "AY 2026-27", "AY 2027-28",
]

SAMPLE_PARTICULARS = [
    "Depreciation Difference (WDV vs SLM)",
    "Provision for Doubtful Debts",
    "Bonus / Leave Encashment Payable",
    "Gratuity Provision",
    "Deferred Revenue",
    "Prepaid Expenses",
    "Other Timing Differences",
]

# Tax rate presets
TAX_RATE_PRESETS = {
    "Domestic – 25% + SC + Cess (25.168%)": 25.168,
    "Domestic – 22% + SC + Cess (25.168% on lower base)": 25.168,
    "New Regime – Sec.115BAA (22% + SC + Cess = 25.168%)": 25.168,
    "New Regime – Sec.115BAB (15% + SC + Cess = 17.01%)": 17.01,
    "MAT – Sec.115JB (15% + SC + Cess = 17.472%)": 17.472,
    "Custom": 0.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# THEME ENGINE
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg":          "#F4F6FA",
        "panel":       "#FFFFFF",
        "sidebar":     "#1A2340",
        "sidebar_fg":  "#C8D3F5",
        "sidebar_sel": "#2E4080",
        "accent":      "#3A6FF7",
        "accent2":     "#22C55E",
        "danger":      "#EF4444",
        "warning":     "#F59E0B",
        "fg":          "#1E2A42",
        "fg2":         "#6B7280",
        "border":      "#E2E8F0",
        "entry_bg":    "#FFFFFF",
        "entry_fg":    "#1E2A42",
        "tbl_head":    "#EEF2FF",
        "tbl_odd":     "#F9FAFB",
        "tbl_even":    "#FFFFFF",
        "tbl_sel":     "#DBEAFE",
        "btn":         "#3A6FF7",
        "btn_fg":      "#FFFFFF",
        "btn2":        "#22C55E",
        "btn2_fg":     "#FFFFFF",
        "card":        "#FFFFFF",
        "card_bdr":    "#E2E8F0",
        "title_fg":    "#1E2A42",
        "sub_fg":      "#6B7280",
    },
    "dark": {
        "bg":          "#0F1623",
        "panel":       "#1A2340",
        "sidebar":     "#0D1220",
        "sidebar_fg":  "#A0AEC0",
        "sidebar_sel": "#2E4080",
        "accent":      "#3A6FF7",
        "accent2":     "#22C55E",
        "danger":      "#EF4444",
        "warning":     "#F59E0B",
        "fg":          "#E2E8F0",
        "fg2":         "#94A3B8",
        "border":      "#2D3A55",
        "entry_bg":    "#243050",
        "entry_fg":    "#E2E8F0",
        "tbl_head":    "#1E2D4F",
        "tbl_odd":     "#182033",
        "tbl_even":    "#1A2340",
        "tbl_sel":     "#2E4080",
        "btn":         "#3A6FF7",
        "btn_fg":      "#FFFFFF",
        "btn2":        "#22C55E",
        "btn2_fg":     "#FFFFFF",
        "card":        "#1A2340",
        "card_bdr":    "#2D3A55",
        "title_fg":    "#E2E8F0",
        "sub_fg":      "#94A3B8",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE LAYER
# ─────────────────────────────────────────────────────────────────────────────

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and seed default data."""
    with get_conn() as conn:
        c = conn.cursor()

        # Users
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                pw_hash  TEXT NOT NULL
            )
        """)
        c.execute("""
            INSERT OR IGNORE INTO users (username, pw_hash)
            VALUES ('admin', ?)
        """, (_hash("admin123"),))

        # App preferences
        c.execute("""
            CREATE TABLE IF NOT EXISTS app_prefs (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        c.execute("INSERT OR IGNORE INTO app_prefs VALUES ('theme','light')")

        # Companies
        c.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                pan        TEXT,
                created_at TEXT DEFAULT (date('now'))
            )
        """)

        # Financial Years per company
        c.execute("""
            CREATE TABLE IF NOT EXISTS financial_years (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy         TEXT NOT NULL,
                year_end   TEXT NOT NULL,
                UNIQUE(company_id, fy)
            )
        """)

        # Opening balances per company+FY
        c.execute("""
            CREATE TABLE IF NOT EXISTS opening_balances (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy_id      INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
                opening_dta REAL DEFAULT 0,
                opening_dtl REAL DEFAULT 0,
                UNIQUE(company_id, fy_id)
            )
        """)

        # Tax rates per company+FY
        c.execute("""
            CREATE TABLE IF NOT EXISTS tax_rates (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy_id      INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
                rate       REAL NOT NULL DEFAULT 25.168,
                UNIQUE(company_id, fy_id)
            )
        """)

        # DTA/DTL Particulars
        c.execute("""
            CREATE TABLE IF NOT EXISTS particulars (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id     INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy_id          INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
                particular     TEXT NOT NULL,
                book_value     REAL DEFAULT 0,
                tax_value      REAL DEFAULT 0,
                timing_diff    REAL DEFAULT 0,
                nature         TEXT DEFAULT 'DTA',
                dta_dtl_amount REAL DEFAULT 0
            )
        """)

        # Losses / Unabsorbed Depreciation
        c.execute("""
            CREATE TABLE IF NOT EXISTS losses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy_id           INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
                assessment_year TEXT NOT NULL,
                loss_type       TEXT DEFAULT 'Business Loss',
                loss_amount     REAL DEFAULT 0,
                carry_fwd_yrs   INTEGER DEFAULT 8,
                expiry_year     TEXT,
                dta_amount      REAL DEFAULT 0
            )
        """)

        # Future profitability assessment
        c.execute("""
            CREATE TABLE IF NOT EXISTS future_profitability (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                fy_id      INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
                can_profit INTEGER DEFAULT 1,
                remarks    TEXT,
                UNIQUE(company_id, fy_id)
            )
        """)

        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def fmt_inr(amount: float) -> str:
    """Format a number in Indian notation with ₹ prefix."""
    negative = amount < 0
    amount = abs(amount)
    s = f"{amount:,.2f}"
    # Convert western comma-separated to Indian system
    parts = s.split(".")
    integer_part = parts[0].replace(",", "")
    decimal_part = parts[1] if len(parts) > 1 else "00"
    # Indian grouping: last 3 then groups of 2
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        integer_part = ",".join(groups) + "," + last3
    result = f"₹{integer_part}.{decimal_part}"
    return f"({result})" if negative else result


def get_pref(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_prefs WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_pref(key: str, value: str):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO app_prefs VALUES (?,?)", (key, value))
        conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SCROLLABLE FRAME HELPER
# ─────────────────────────────────────────────────────────────────────────────

class ScrollFrame(tk.Frame):
    """A frame with an embedded vertical scrollbar."""

    def __init__(self, parent, bg, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.vbar   = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind_all("<MouseWheel>", self._on_scroll)

    def _on_inner(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfig(self._win_id, width=e.width)

    def _on_scroll(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")


# ─────────────────────────────────────────────────────────────────────────────
# STYLED WIDGETS FACTORY
# ─────────────────────────────────────────────────────────────────────────────

class UI:
    """Build consistently themed widgets."""

    def __init__(self, theme: dict):
        self.t = theme

    def label(self, parent, text, font=("Helvetica", 10), fg_key="fg", **kw):
        return tk.Label(parent, text=text, font=font,
                        bg=kw.pop("bg", self.t["panel"]),
                        fg=self.t[fg_key], **kw)

    def entry(self, parent, textvariable=None, width=20, **kw):
        e = tk.Entry(parent, textvariable=textvariable, width=width,
                     bg=self.t["entry_bg"], fg=self.t["entry_fg"],
                     insertbackground=self.t["entry_fg"],
                     relief="flat", bd=4, font=("Helvetica", 10), **kw)
        return e

    def button(self, parent, text, command, color_key="btn", fg_key="btn_fg", **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=self.t[color_key], fg=self.t[fg_key],
                         font=("Helvetica", 10, "bold"),
                         relief="flat", cursor="hand2",
                         padx=12, pady=6, **kw)

    def frame(self, parent, bg_key="panel", **kw):
        return tk.Frame(parent, bg=self.t[bg_key], **kw)

    def section(self, parent, title):
        """A titled card-like container."""
        f = tk.Frame(parent, bg=self.t["card"],
                     highlightbackground=self.t["card_bdr"],
                     highlightthickness=1)
        tk.Label(f, text=title,
                 font=("Helvetica", 11, "bold"),
                 bg=self.t["card"], fg=self.t["accent"]).pack(
            anchor="w", padx=12, pady=(10, 4))
        tk.Frame(f, bg=self.t["border"], height=1).pack(fill="x", padx=12)
        return f

    def tree(self, parent, columns, heights=8):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background=self.t["tbl_odd"],
                        fieldbackground=self.t["tbl_odd"],
                        foreground=self.t["fg"],
                        rowheight=28,
                        font=("Helvetica", 9))
        style.configure("Custom.Treeview.Heading",
                        background=self.t["tbl_head"],
                        foreground=self.t["fg"],
                        font=("Helvetica", 9, "bold"),
                        relief="flat")
        style.map("Custom.Treeview",
                  background=[("selected", self.t["tbl_sel"])],
                  foreground=[("selected", self.t["fg"])])
        tv = ttk.Treeview(parent, columns=columns, show="headings",
                          height=heights, style="Custom.Treeview",
                          selectmode="browse")
        tv.tag_configure("odd",  background=self.t["tbl_odd"])
        tv.tag_configure("even", background=self.t["tbl_even"])
        tv.tag_configure("dta",  foreground="#22C55E")
        tv.tag_configure("dtl",  foreground="#F59E0B")
        tv.tag_configure("net_pos", foreground="#3A6FF7", font=("Helvetica", 9, "bold"))
        tv.tag_configure("net_neg", foreground="#EF4444", font=("Helvetica", 9, "bold"))
        return tv


# ─────────────────────────────────────────────────────────────────────────────
# SCREEN BASE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class Screen(tk.Frame):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, bg=app.theme["panel"])

    @property
    def ui(self) -> UI:
        return self.app.ui_factory

    @property
    def t(self):
        return self.app.theme


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN SCREEN
# ─────────────────────────────────────────────────────────────────────────────

class LoginScreen(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent, bg="#1A2340")
        self.on_success = on_success
        self._build()

    def _build(self):
        # Centering container
        outer = tk.Frame(self, bg="#1A2340")
        outer.place(relx=0.5, rely=0.5, anchor="center")

        # Logo / Title
        tk.Label(outer, text="⚖️", font=("Helvetica", 48),
                 bg="#1A2340", fg="#3A6FF7").pack(pady=(0, 8))
        tk.Label(outer, text="IND AS 12",
                 font=("Helvetica", 26, "bold"),
                 bg="#1A2340", fg="#FFFFFF").pack()
        tk.Label(outer, text="Income Tax – Deferred Tax Tool",
                 font=("Helvetica", 11),
                 bg="#1A2340", fg="#94A3B8").pack(pady=(0, 24))

        # Card
        card = tk.Frame(outer, bg="#243050",
                        highlightbackground="#3A6FF7",
                        highlightthickness=2)
        card.pack(padx=20, ipadx=20, ipady=20)

        tk.Label(card, text="Sign In", font=("Helvetica", 14, "bold"),
                 bg="#243050", fg="#E2E8F0").pack(pady=(16, 12))

        # Username
        tk.Label(card, text="Username", font=("Helvetica", 9),
                 bg="#243050", fg="#94A3B8").pack(anchor="w", padx=24)
        self._user = tk.Entry(card, font=("Helvetica", 11), width=26,
                              bg="#1A2340", fg="#E2E8F0",
                              insertbackground="#E2E8F0",
                              relief="flat", bd=6)
        self._user.pack(padx=24, pady=(2, 10))
        self._user.insert(0, "admin")

        # Password
        tk.Label(card, text="Password", font=("Helvetica", 9),
                 bg="#243050", fg="#94A3B8").pack(anchor="w", padx=24)
        self._pw = tk.Entry(card, font=("Helvetica", 11), width=26,
                            show="●", bg="#1A2340", fg="#E2E8F0",
                            insertbackground="#E2E8F0",
                            relief="flat", bd=6)
        self._pw.pack(padx=24, pady=(2, 4))
        self._pw.bind("<Return>", lambda _: self._login())

        self._err = tk.Label(card, text="", font=("Helvetica", 9),
                             bg="#243050", fg="#EF4444")
        self._err.pack(pady=(4, 8))

        tk.Button(card, text="LOGIN", command=self._login,
                  bg="#3A6FF7", fg="#FFFFFF",
                  font=("Helvetica", 11, "bold"),
                  relief="flat", cursor="hand2",
                  width=22, pady=8).pack(padx=24, pady=(0, 20))

        # Footer
        tk.Label(outer, text="Default: admin / admin123",
                 font=("Helvetica", 9), bg="#1A2340",
                 fg="#4B5563").pack(pady=8)

    def _login(self):
        user = self._user.get().strip()
        pw   = self._pw.get().strip()
        if not user or not pw:
            self._err.config(text="Please enter username and password.")
            return
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username=? AND pw_hash=?",
                (user, _hash(pw))
            ).fetchone()
        if row:
            self.on_success(user)
        else:
            self._err.config(text="Invalid username or password.")


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY & FINANCIAL YEAR SCREEN
# ─────────────────────────────────────────────────────────────────────────────

class CompanyScreen(Screen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        t = self.t
        sf = ScrollFrame(self, bg=t["bg"])
        sf.pack(fill="both", expand=True)
        body = sf.inner

        # Page header
        hdr = tk.Frame(body, bg=t["accent"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="🏢  Company & Financial Year Management",
                 font=("Helvetica", 13, "bold"),
                 bg=t["accent"], fg="#FFFFFF").pack(side="left", padx=20, pady=12)

        pad = tk.Frame(body, bg=t["bg"])
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Left: Add company form ──────────────────────────────────────────
        left = tk.Frame(pad, bg=t["bg"])
        left.pack(side="left", fill="y", padx=(0, 16))

        sec1 = self.ui.section(left, "➕  Add / Edit Company")
        sec1.pack(fill="x", pady=(0, 12))

        form = tk.Frame(sec1, bg=t["card"])
        form.pack(fill="x", padx=12, pady=10)

        tk.Label(form, text="Company Name *", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=0, column=0, sticky="w", pady=4)
        self._cname = tk.StringVar()
        self.ui.entry(form, textvariable=self._cname, width=30).grid(
            row=1, column=0, sticky="ew", padx=(0, 8))

        tk.Label(form, text="PAN / Tax ID", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=2, column=0, sticky="w", pady=(8, 2))
        self._pan = tk.StringVar()
        self.ui.entry(form, textvariable=self._pan, width=30).grid(
            row=3, column=0, sticky="ew", padx=(0, 8))

        btn_row = tk.Frame(sec1, bg=t["card"])
        btn_row.pack(fill="x", padx=12, pady=(0, 12))
        self.ui.button(btn_row, "💾  Save Company", self._save_company).pack(side="left", padx=(0, 8))
        self.ui.button(btn_row, "🗑  Delete", self._delete_company,
                       color_key="danger").pack(side="left")

        # Financial Year section
        sec2 = self.ui.section(left, "📅  Add Financial Year")
        sec2.pack(fill="x", pady=(0, 12))

        fy_form = tk.Frame(sec2, bg=t["card"])
        fy_form.pack(fill="x", padx=12, pady=10)

        tk.Label(fy_form, text="Select Financial Year", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=0, column=0, sticky="w")
        self._fy_var = tk.StringVar(value=FINANCIAL_YEARS[-2])
        cb = ttk.Combobox(fy_form, textvariable=self._fy_var,
                          values=FINANCIAL_YEARS, width=18, state="readonly")
        cb.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        btn_row2 = tk.Frame(sec2, bg=t["card"])
        btn_row2.pack(fill="x", padx=12, pady=(0, 12))
        self.ui.button(btn_row2, "➕  Add FY", self._add_fy).pack(side="left")

        # ── Right: Tables ──────────────────────────────────────────────────
        right = tk.Frame(pad, bg=t["bg"])
        right.pack(side="left", fill="both", expand=True)

        # Companies table
        sec3 = self.ui.section(right, "🏢  Companies")
        sec3.pack(fill="x", pady=(0, 12))

        cols = ("ID", "Company Name", "PAN", "Created On")
        self._ctree = self.ui.tree(sec3, cols, heights=6)
        self._ctree.heading("ID", text="#")
        self._ctree.heading("Company Name", text="Company Name")
        self._ctree.heading("PAN", text="PAN / Tax ID")
        self._ctree.heading("Created On", text="Created On")
        self._ctree.column("ID", width=40, anchor="center")
        self._ctree.column("Company Name", width=200)
        self._ctree.column("PAN", width=130)
        self._ctree.column("Created On", width=110, anchor="center")
        self._ctree.pack(fill="x", padx=12, pady=(8, 12))
        self._ctree.bind("<<TreeviewSelect>>", self._on_company_select)

        self.ui.button(sec3, "✅  Set Active Company",
                       self._set_active).pack(anchor="w", padx=12, pady=(0, 12))

        # FY table
        sec4 = self.ui.section(right, "📅  Financial Years for Selected Company")
        sec4.pack(fill="both", expand=True)

        fy_cols = ("ID", "Financial Year", "Year End Date")
        self._fytree = self.ui.tree(sec4, fy_cols, heights=5)
        self._fytree.heading("ID", text="#")
        self._fytree.heading("Financial Year", text="Financial Year")
        self._fytree.heading("Year End Date", text="Year End Date")
        self._fytree.column("ID", width=40, anchor="center")
        self._fytree.column("Financial Year", width=130, anchor="center")
        self._fytree.column("Year End Date", width=130, anchor="center")
        self._fytree.pack(fill="x", padx=12, pady=(8, 4))
        self._fytree.bind("<<TreeviewSelect>>", self._on_fy_select)

        self.ui.button(sec4, "✅  Set Active FY",
                       self._set_active_fy).pack(anchor="w", padx=12, pady=(0, 12))

        self._sel_company_id = None
        self._sel_fy_id = None
        self._load_companies()

    # ── data actions ────────────────────────────────────────────────────────

    def _load_companies(self):
        for row in self._ctree.get_children():
            self._ctree.delete(row)
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM companies ORDER BY name").fetchall()
        for i, r in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self._ctree.insert("", "end",
                               values=(r["id"], r["name"], r["pan"] or "—", r["created_at"]),
                               tags=(tag,))

    def _save_company(self):
        name = self._cname.get().strip()
        if not name:
            messagebox.showwarning("Input Error", "Company name is required.")
            return
        pan = self._pan.get().strip()
        with get_conn() as conn:
            if self._sel_company_id:
                conn.execute("UPDATE companies SET name=?, pan=? WHERE id=?",
                             (name, pan, self._sel_company_id))
            else:
                conn.execute("INSERT INTO companies (name,pan) VALUES (?,?)", (name, pan))
            conn.commit()
        self._load_companies()
        self._cname.set(""); self._pan.set("")
        self._sel_company_id = None

    def _delete_company(self):
        if not self._sel_company_id:
            messagebox.showinfo("Select", "Please select a company first.")
            return
        if messagebox.askyesno("Confirm", "Delete this company and ALL associated data?"):
            with get_conn() as conn:
                conn.execute("DELETE FROM companies WHERE id=?", (self._sel_company_id,))
                conn.commit()
            self._sel_company_id = None
            self._load_companies()

    def _on_company_select(self, _=None):
        sel = self._ctree.selection()
        if not sel:
            return
        vals = self._ctree.item(sel[0])["values"]
        self._sel_company_id = vals[0]
        self._cname.set(vals[1])
        self._pan.set(vals[2] if vals[2] != "—" else "")
        self._load_fy(vals[0])

    def _load_fy(self, company_id):
        for row in self._fytree.get_children():
            self._fytree.delete(row)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM financial_years WHERE company_id=? ORDER BY fy",
                (company_id,)).fetchall()
        for i, r in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self._fytree.insert("", "end",
                                values=(r["id"], r["fy"], r["year_end"]),
                                tags=(tag,))

    def _add_fy(self):
        if not self._sel_company_id:
            messagebox.showinfo("Select", "Please select a company first.")
            return
        fy = self._fy_var.get()
        # Derive year-end date: e.g. "2024-25" → "31-Mar-2025"
        try:
            end_yr = int(fy.split("-")[0]) + 1
            ye = f"31-Mar-{end_yr}"
        except Exception:
            ye = "31-Mar-?????"
        with get_conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO financial_years (company_id,fy,year_end) VALUES (?,?,?)",
                    (self._sel_company_id, fy, ye))
                conn.commit()
            except sqlite3.IntegrityError:
                messagebox.showinfo("Duplicate", f"FY {fy} already exists for this company.")
                return
        self._load_fy(self._sel_company_id)

    def _on_fy_select(self, _=None):
        sel = self._fytree.selection()
        if sel:
            self._sel_fy_id = self._fytree.item(sel[0])["values"][0]

    def _set_active(self):
        if not self._sel_company_id:
            messagebox.showinfo("Select", "Please select a company first.")
            return
        self.app.active_company_id = self._sel_company_id
        vals = self._ctree.item(self._ctree.selection()[0])["values"]
        self.app.active_company_name = vals[1]
        self.app.update_status_bar()
        messagebox.showinfo("Active", f"Active company set to: {vals[1]}")

    def _set_active_fy(self):
        if not self._sel_fy_id:
            messagebox.showinfo("Select", "Please select a financial year first.")
            return
        vals = self._fytree.item(self._fytree.selection()[0])["values"]
        self.app.active_fy_id = self._sel_fy_id
        self.app.active_fy = vals[1]
        self.app.update_status_bar()
        messagebox.showinfo("Active", f"Active FY set to: {vals[1]}")


# ─────────────────────────────────────────────────────────────────────────────
# OPENING BALANCES SCREEN
# ─────────────────────────────────────────────────────────────────────────────

class OpeningBalancesScreen(Screen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        t = self.t
        hdr = tk.Frame(self, bg=t["accent"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📂  Opening Balances – DTA / DTL",
                 font=("Helvetica", 13, "bold"),
                 bg=t["accent"], fg="#FFFFFF").pack(side="left", padx=20, pady=12)

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        sec = self.ui.section(body, "Enter Opening Balances for Active Company + FY")
        sec.pack(fill="x", pady=12)

        form = tk.Frame(sec, bg=t["card"])
        form.pack(fill="x", padx=16, pady=14)

        def lbl(r, text):
            tk.Label(form, text=text, font=("Helvetica", 10),
                     bg=t["card"], fg=t["fg"]).grid(row=r, column=0, sticky="w", pady=6, padx=(0, 20))

        def ent(r):
            v = tk.StringVar(value="0.00")
            e = self.ui.entry(form, textvariable=v, width=22)
            e.grid(row=r, column=1, sticky="w")
            return v

        lbl(0, "Opening DTA (Deferred Tax Asset)  ₹")
        self._odta = ent(0)
        lbl(1, "Opening DTL (Deferred Tax Liability) ₹")
        self._odtl = ent(1)

        # Note
        note = tk.Frame(sec, bg=t["card"])
        note.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(note, text="ℹ️  These are carried-forward balances from the previous financial year.",
                 font=("Helvetica", 9), bg=t["card"], fg=t["fg2"]).pack(anchor="w")

        btn_row = tk.Frame(sec, bg=t["card"])
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        self.ui.button(btn_row, "💾  Save Opening Balances", self._save).pack(side="left")
        self.ui.button(btn_row, "🔄  Load Saved", self._load).pack(side="left", padx=8)

        self._status = tk.Label(body, text="", font=("Helvetica", 10),
                                bg=t["bg"], fg=t["accent2"])
        self._status.pack(anchor="w", pady=8)

        self._load()

    def _check_context(self) -> bool:
        if not self.app.active_company_id or not self.app.active_fy_id:
            messagebox.showwarning("No Context",
                                   "Please set an Active Company and Financial Year first.")
            return False
        return True

    def _load(self):
        if not self.app.active_company_id or not self.app.active_fy_id:
            return
        with get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM opening_balances WHERE company_id=? AND fy_id=?",
                (self.app.active_company_id, self.app.active_fy_id)).fetchone()
        if row:
            self._odta.set(f"{row['opening_dta']:.2f}")
            self._odtl.set(f"{row['opening_dtl']:.2f}")
            self._status.config(text="✅  Saved balances loaded.")
        else:
            self._odta.set("0.00")
            self._odtl.set("0.00")
            self._status.config(text="No saved balances found for this FY.")

    def _save(self):
        if not self._check_context():
            return
        try:
            dta = float(self._odta.get())
            dtl = float(self._odtl.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric amounts.")
            return
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO opening_balances (company_id, fy_id, opening_dta, opening_dtl)
                VALUES (?,?,?,?)
                ON CONFLICT(company_id,fy_id) DO UPDATE
                SET opening_dta=excluded.opening_dta, opening_dtl=excluded.opening_dtl
            """, (self.app.active_company_id, self.app.active_fy_id, dta, dtl))
            conn.commit()
        self._status.config(text="✅  Opening balances saved successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# TAX RATE SCREEN
# ─────────────────────────────────────────────────────────────────────────────

class TaxRateScreen(Screen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        t = self.t
        hdr = tk.Frame(self, bg=t["accent"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📊  Tax Rate Configuration",
                 font=("Helvetica", 13, "bold"),
                 bg=t["accent"], fg="#FFFFFF").pack(side="left", padx=20, pady=12)

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        sec = self.ui.section(body, "Set Applicable Tax Rate for Active Company + FY")
        sec.pack(fill="x", pady=12)

        frm = tk.Frame(sec, bg=t["card"])
        frm.pack(fill="x", padx=16, pady=14)

        tk.Label(frm, text="Quick Select Regime:", font=("Helvetica", 10),
                 bg=t["card"], fg=t["fg"]).grid(row=0, column=0, sticky="w", pady=4)

        self._preset = tk.StringVar(value=list(TAX_RATE_PRESETS.keys())[0])
        cb = ttk.Combobox(frm, textvariable=self._preset,
                          values=list(TAX_RATE_PRESETS.keys()),
                          width=48, state="readonly")
        cb.grid(row=0, column=1, padx=8, pady=4, sticky="w")
        cb.bind("<<ComboboxSelected>>", self._on_preset)

        tk.Label(frm, text="Effective Tax Rate (%):", font=("Helvetica", 10),
                 bg=t["card"], fg=t["fg"]).grid(row=1, column=0, sticky="w", pady=(10, 4))
        self._rate_var = tk.StringVar(value="25.168")
        self.ui.entry(frm, textvariable=self._rate_var, width=14).grid(
            row=1, column=1, sticky="w", padx=8, pady=(10, 4))

        # Info box
        info_frame = tk.Frame(sec, bg=t["tbl_head"],
                              highlightbackground=t["accent"],
                              highlightthickness=1)
        info_frame.pack(fill="x", padx=16, pady=8)
        info_text = (
            "Applicable Rates (FY 2024-25):\n"
            "  • Sec. 115BAA (22% + 10% SC + 4% Cess) = 25.168%\n"
            "  • Sec. 115BAB (15% + 10% SC + 4% Cess) = 17.01%\n"
            "  • MAT u/s 115JB (15% + SC + Cess)       = 17.472%\n"
            "  • Regular (30% + SC + Cess)              = 34.944%"
        )
        tk.Label(info_frame, text=info_text, font=("Courier", 9),
                 bg=t["tbl_head"], fg=t["fg"], justify="left").pack(
            anchor="w", padx=12, pady=8)

        btn_row = tk.Frame(sec, bg=t["card"])
        btn_row.pack(fill="x", padx=16, pady=(0, 14))
        self.ui.button(btn_row, "💾  Save Tax Rate", self._save).pack(side="left")
        self.ui.button(btn_row, "🔄  Load Saved", self._load_rate).pack(side="left", padx=8)

        self._status = tk.Label(body, text="", font=("Helvetica", 10),
                                bg=t["bg"], fg=t["accent2"])
        self._status.pack(anchor="w", pady=8)
        self._load_rate()

    def _on_preset(self, _=None):
        rate = TAX_RATE_PRESETS.get(self._preset.get(), 0.0)
        if rate > 0:
            self._rate_var.set(f"{rate:.3f}")

    def _load_rate(self):
        if not self.app.active_company_id or not self.app.active_fy_id:
            return
        with get_conn() as conn:
            row = conn.execute(
                "SELECT rate FROM tax_rates WHERE company_id=? AND fy_id=?",
                (self.app.active_company_id, self.app.active_fy_id)).fetchone()
        if row:
            self._rate_var.set(f"{row['rate']:.3f}")
            self._status.config(text="✅  Saved rate loaded.")

    def _save(self):
        if not self.app.active_company_id or not self.app.active_fy_id:
            messagebox.showwarning("No Context",
                                   "Please set an Active Company and Financial Year first.")
            return
        try:
            rate = float(self._rate_var.get())
            if not (0 < rate < 100):
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid tax rate (0–100).")
            return
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO tax_rates (company_id, fy_id, rate)
                VALUES (?,?,?)
                ON CONFLICT(company_id,fy_id) DO UPDATE SET rate=excluded.rate
            """, (self.app.active_company_id, self.app.active_fy_id, rate))
            conn.commit()
        self._status.config(text=f"✅  Tax rate {rate:.3f}% saved for this FY.")


# ─────────────────────────────────────────────────────────────────────────────
# PARTICULARS SCREEN  (DTA / DTL on timing differences)
# ─────────────────────────────────────────────────────────────────────────────

class ParticularsScreen(Screen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._sel_id = None
        self._build()

    # ── layout ──────────────────────────────────────────────────────────────

    def _build(self):
        t = self.t
        hdr = tk.Frame(self, bg=t["accent"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📋  Particulars – DTA / DTL on Timing Differences",
                 font=("Helvetica", 13, "bold"),
                 bg=t["accent"], fg="#FFFFFF").pack(side="left", padx=20, pady=12)

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # ── entry form (top half) ────────────────────────────────────────────
        sec = self.ui.section(body, "Add / Edit Particular")
        sec.pack(fill="x", pady=(0, 12))

        frm = tk.Frame(sec, bg=t["card"])
        frm.pack(fill="x", padx=14, pady=10)

        # Row 0: Particular name + Nature
        tk.Label(frm, text="Particular Description *", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=0, column=0, sticky="w", padx=(0, 20))
        tk.Label(frm, text="Nature", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=0, column=1, sticky="w")

        self._part_var = tk.StringVar()
        cb_part = ttk.Combobox(frm, textvariable=self._part_var,
                               values=SAMPLE_PARTICULARS, width=40)
        cb_part.grid(row=1, column=0, sticky="ew", padx=(0, 20), pady=4)

        self._nature_var = tk.StringVar(value="DTL")
        nat_cb = ttk.Combobox(frm, textvariable=self._nature_var,
                              values=["DTA", "DTL"], width=8, state="readonly")
        nat_cb.grid(row=1, column=1, sticky="w", pady=4)
        nat_cb.bind("<<ComboboxSelected>>", self._recalc)

        # Row 2: Book value / Tax value / Timing diff
        tk.Label(frm, text="Book Value (₹)", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=2, column=0, sticky="w", pady=(8, 2))
        tk.Label(frm, text="Tax Value (₹)", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=2, column=1, sticky="w", pady=(8, 2))
        tk.Label(frm, text="Timing Diff (₹)", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=2, column=2, sticky="w",
                                                  padx=(20, 0), pady=(8, 2))
        tk.Label(frm, text="DTA / DTL Amt (₹)", font=("Helvetica", 9),
                 bg=t["card"], fg=t["fg2"]).grid(row=2, column=3, sticky="w",
                                                  padx=(16, 0), pady=(8, 2))

        self._bv = tk.StringVar(value="0.00")
        self._tv = tk.StringVar(value="0.00")
        self._td = tk.StringVar(value="0.00")
        self._amt = tk.StringVar(value="0.00")

        bv_e = self.ui.entry(frm, textvariable=self._bv, width=16)
        tv_e = self.ui.entry(frm, textvariable=self._tv, width=16)
        bv_e.grid(row=3, column=0, sticky="w", padx=(0, 20), pady=2)
        tv_e.grid(row=3, column=1, sticky="w", pady=2)
        bv_e.bind("<FocusOut>", self._recalc)
        tv_e.bind("<FocusOut>", self._recalc)

        self.ui.entry(frm, textvariable=self._td, width=16,
                      state="readonly").grid(row=3, column=2, padx=(20, 0), pady=2)
        self.ui.entry(frm, textvariable=self._amt, width=16,
                      state="readonly").grid(row=3, column=3, padx=(16, 0), pady=2)

        # Buttons
        btn_row = tk.Frame(sec, bg=t["card"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        self.ui.button(btn_row, "➕  Add",    self._add).pack(side="left", padx=(0, 8))
        self.ui.button(btn_row, "✏️  Update", self._update).pack(side="left", padx=(0, 8))
        self.ui.button(btn_row, "🗑  Delete", self._delete,
                       color_key="danger").pack(side="left")

        # ── table (bottom half) ──────────────────────────────────────────────
        sec2 = self.ui.section(body, "Particulars List")
        sec2.pack(fill="both", expand=True)

        cols = ("ID", "Particular", "Book Val", "Tax Val", "Timing Diff", "Nature", "Amt (₹)")
        self._tree = self.ui.tree(sec2, cols, heights=10)
        widths = [40, 260, 110, 110, 110, 60, 120]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w,
                              anchor="center" if col not in ("Particular",) else "w")
        vsb = ttk.Scrollbar(sec2, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tree.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Totals row
        self._tot_lbl = tk.Label(sec2, text="", font=("Helvetica", 10, "bold"),
                                 bg=t["card"], fg=t["accent"])
        self._tot_lbl.pack(anchor="e", padx=14, pady=(0, 10))

        self._load()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _get_rate(self) -> float:
        if not self.app.active_company_id or not self.app.active_fy_id:
            return 0.0
        with get_conn() as conn:
            row = conn.execute(
                "SELECT rate FROM tax_rates WHERE company_id=? AND fy_id=?",
                (self.app.active_company_id, self.app.active_fy_id)).fetchone()
        return row["rate"] if row else 0.0

    def _recalc(self, _=None):
        try:
            bv = float(self._bv.get())
            tv = float(self._tv.get())
        except ValueError:
            return
        # Timing diff: Book – Tax
        td = bv - tv
        # Nature drives sign
        nature = self._nature_var.get()
        # For DTL timing diff should be Book > Tax (accelerated tax dep)
        # For DTA timing diff should be Book < Tax (slower tax dep)
        rate = self._get_rate()
        amt = abs(td) * rate / 100
        self._td.set(f"{td:.2f}")
        self._amt.set(f"{amt:.2f}")

    def _load(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        if not self.app.active_company_id or not self.app.active_fy_id:
            return
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM particulars WHERE company_id=? AND fy_id=? ORDER BY id",
                (self.app.active_company_id, self.app.active_fy_id)).fetchall()
        total_dta = total_dtl = 0.0
        for i, r in enumerate(rows):
            tag = ("even" if i % 2 == 0 else "odd",
                   r["nature"].lower())
            self._tree.insert("", "end",
                              values=(r["id"], r["particular"],
                                      f"{r['book_value']:.2f}",
                                      f"{r['tax_value']:.2f}",
                                      f"{r['timing_diff']:.2f}",
                                      r["nature"],
                                      f"{r['dta_dtl_amount']:.2f}"),
                              tags=tag)
            if r["nature"] == "DTA":
                total_dta += r["dta_dtl_amount"]
            else:
                total_dtl += r["dta_dtl_amount"]
        self._tot_lbl.config(
            text=f"Total DTA: {fmt_inr(total_dta)}   |   Total DTL: {fmt_inr(total_dtl)}")

    def _check(self) -> bool:
        if not self.app.active_company_id or not self.app.active_fy_id:
            messagebox.showwarning("No Context",
                                   "Please set Active Company + FY first.")
            return False
        if not self._part_var.get().strip():
            messagebox.showwarning("Input", "Particular description is required.")
            return False
        return True

    def _add(self):
        if not self._check():
            return
        self._recalc()
        try:
            bv  = float(self._bv.get())
            tv  = float(self._tv.get())
            td  = float(self._td.get())
            amt = float(self._amt.get())
        except ValueError:
            messagebox.showerror("Input", "Enter valid numbers.")
            return
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO particulars
                   (company_id,fy_id,particular,book_value,tax_value,timing_diff,nature,dta_dtl_amount)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (self.app.active_company_id, self.app.active_fy_id,
                 self._part_var.get().strip(), bv, tv, td,
                 self._nature_var.get(), amt))
            conn.commit()
        self._load()
        self._clear()

    def _update(self):
        if not self._sel_id:
            messagebox.showinfo("Select", "Select a row to update.")
            return
        self._recalc()
        try:
            bv  = float(self._bv.get())
            tv  = float(self._tv.get())
            td  = float(self._td.get())
            amt = float(self._amt.get())
        except ValueError:
            messagebox.showerror("Input", "Enter valid numbers.")
            return
        with get_conn() as conn:
            conn.execute(
                """UPDATE particulars SET particular=?,book_value=?,tax_value=?,
                   timing_diff=?,nature=?,dta_dtl_amount=? WHERE id=?""",
                (self._part_var.get().strip(), bv, tv, td,
                 self._nature_var.get(), amt, self._sel_id))
            conn.commit()
        self._load()
        self._clear()

    def _delete(self):
        if not self._sel_id:
            messagebox.showinfo("Select", "Select a row to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this particular?"):
            with get_conn() as conn:
                conn.execute("DELETE FROM particulars WHERE id=?", (self._sel_id,))
                conn.commit()
            self._sel_id = None
            self._load()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self._sel_id = vals[0]
        self._part_var.set(vals[1])
        self._bv.set(str(vals[2]))
        self._tv.set(str(vals[3]))
        self._td.set(str(vals[4]))
        self._nature_var.set(vals[5])
        self._amt.set(str(vals[6]))

    def _clear(self):
        self._sel_id = None
        self._part_var.set("")
        self._bv.set("0.00"); self._tv.set("0.00")
        self._td.set("0.00"); self._amt.set("0.00")
        self._nature_var.set("DTL")


# ─────────────────────────────────────────────────────────────────────────────
# LOSS & UNABSORBED DEPRECIATION SCREEN
# ─────────────────────────────────────────────────────────────────────────────

class LossScreen(Screen):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._sel_id = None
        self._build()

    def _build(self):
        t = self.t
        hdr = tk.Frame(self, bg=t["warning"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📉  Loss & Unabsorbed Depreciation – DTA (Year-wise)",
                 font=("Helvetica", 13, "bold"),
                 bg=t["warning"], fg="#FFFFFF").pack(side="left", padx=20, pady=12)

        body = tk.Frame(self, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Entry section
        sec = self.ui.section(body, "Add Entry")
        sec.pack(fill="x", pady=(0, 12))

        frm = tk.Frame(sec, bg=t["card"])
        frm.pack(fill="x", padx=14, pady=10)

        # Row labels
        labels = ["Assessment Year", "Loss Type", "Loss Amount (₹)",
                  "Carry Fwd (Yrs)", "Expiry Year", "DTA Amount (₹)"]
        for j, lbl in enumerate(labels):
            tk.Label(frm, text=lbl, font=("Helvetica", 9),
                     bg=t["card"], fg=t["fg2"]).grid(row=0, column=j,
                                                      sticky="w", padx=(0, 12))

        self._ay = tk.StringVar(value=ASSESSMENT_YEARS[-2])
        ay_cb = ttk.Combobox(frm, textvariable=self._ay,
                             values=ASSESSMENT_YEARS, width=12, state="readonly")
        ay_cb.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=4)

        self._ltype = tk.StringVar(value="Business Loss")
        lt_cb = ttk.Combobox(frm, textvariable=self._ltype,
                             values=["Business Loss", "Unabsorbed Depreciation"],
                             width=22, state="readonly")
        lt_cb.grid(row=1, column=1, sticky="w", padx=(0, 12), pady=4)
        lt_cb.bind("<<ComboboxSelected>>", self._recalc_loss)

        self._loss_amt = tk.StringVar(value="0.00")
        self._cfwd = tk.StringVar(value="8")
        self._expiry = tk.StringVar(value="")
        self._dta_amt = tk.StringVar(value="0.00")

        la_e = self.ui.entry(frm, textvariable=self._loss_amt, width=14)
        la_e.grid(row=1, column=2, padx=(0, 12), pady=4)
        la_e.bind("<FocusOut>", self._recalc_loss)

        cf_e = self.ui.entry(frm, textvariable=self._cfwd, width=8)
        cf_e.grid(row=1, column=3, padx=(0, 12), pady=4)
        cf_e.bind("<FocusOut>", self._recalc_loss)

        self.ui.entry(frm, textvariable=self._expiry, width=10,
                      state="readonly").grid(row=1, column=4, padx=(0, 12), pady=4)
        self.ui.entry(frm, textvariable=self._dta_amt, width=14,
                      state="readonly").grid(row=1, column=5, pady=4)

        # Ay bind to update expiry
        ay_cb.bind("<<ComboboxSelected>>", self._recalc_loss)

        btn_row = tk.Frame(sec, bg=t["card"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))
        self.ui.button(btn_row, "➕  Add",    self._add).pack(side="left", padx=(0, 8))
        self.ui.button(btn_row, "✏️  Update", self._update).pack(side="left", padx=(0, 8))
        self.ui.button(btn_row, "🗑  Delete", self._delete,
                       color_key="danger").pack(side="left")

        # Info note
        note_frame = tk.Frame(sec, bg=t["tbl_head"],
                              highlightbackground=t["border"], highlightthickness=1)
        note_frame.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(note_frame,
                 text=("ℹ️  Business Loss: 8 years carry forward  •  "
                       "Unabsorbed Depreciation: Unlimited (set 99 years)  •  "
                       "DTA recognised only if Future Profit expected (Ind AS 12 Para 35)"),
                 font=("Helvetica", 9), bg=t["tbl_head"], fg=t["fg2"],
                 wraplength=860, justify="left").pack(anchor="w", padx=10, pady=6)

        # Table
        sec2 = self.ui.section(body, "Year-wise Loss / Depreciation Summary")
        sec2.pack(fill="both", expand=True)

        cols = ("ID", "Asmt Year", "Type", "Loss Amt", "CF Yrs", "Expiry", "DTA")
        self._tree = self.ui.tree(sec2, cols, heights=9)
        widths = [40, 100, 200, 120, 70, 90, 120]
        anchors = ["center", "center", "w", "e", "center", "center", "e"]
        for col, w, a in zip(cols, widths, anchors):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor=a)
        vsb = ttk.Scrollbar(sec2, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 4), pady=8)
        self._tree.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._tot_lbl = tk.Label(sec2, text="", font=("Helvetica", 10, "bold"),
                                 bg=t["card"], fg=t["accent2"])
        self._tot_lbl.pack(anchor="e", padx=14, pady=(0, 10))

        self._load()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _get_rate(self) -> float:
        if not self.app.active_company_id or not self.app.active_fy_id:
            return 0.0
        with get_conn() as conn:
            row = conn.execute(
                "SELECT rate FROM tax_rates WHERE company_id=? AND fy_id=?",
                (self.app.active_company_id, self.app.active_fy_id)).fetchone()
        return row["rate"] if row else 0.0

    def _recalc_loss(self, _=None):
        """Recalculate expiry year and DTA amount."""
        ay_str = self._ay.get()  # e.g. "AY 2024-25"
        try:
            start_yr = int(ay_str.split()[-1].split("-")[0])
        except Exception:
            start_yr = 2024
        try:
            cf = int(self._cfwd.get())
        except ValueError:
            cf = 8
        expiry_yr = start_yr + cf
        self._expiry.set(f"AY {expiry_yr}-{str(expiry_yr+1)[-2:]}")

        lt = self._ltype.get()
        if lt == "Unabsorbed Depreciation":
            self._cfwd.set("99")
            self._expiry.set("Unlimited")

        try:
            loss = float(self._loss_amt.get())
        except ValueError:
            loss = 0.0
        rate = self._get_rate()
        self._dta_amt.set(f"{loss * rate / 100:.2f}")

    def _load(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        if not self.app.active_company_id or not self.app.active_fy_id:
            return
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM losses WHERE company_id=? AND fy_id=? ORDER BY assessment_year",
                (self.app.active_company_id, self.app.active_fy_id)).fetchall()
        total_dta = 0.0
        for i, r in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"
            self._tree.insert("", "end",
                              values=(r["id"], r["assessment_year"], r["loss_type"],
                                      fmt_inr(r["loss_amount"]),
                                      r["carry_fwd_yrs"],
                                      r["expiry_year"],
                                      fmt_inr(r["dta_amount"])),
                              tags=(tag, "dta"))
            total_dta += r["dta_amount"]
        self._tot_lbl.config(text=f"Total DTA from Losses/Dep: {fmt_inr(total_dta)}")

    def _add(self):
        if not self.app.active_company_id or not self.app.active_fy_id:
            messagebox.showwarning("No Context", "Set Active Company + FY first.")
            return
        self._recalc_loss()
        try:
            loss = float(self._loss_amt.get())
            cf   = int(self._cfwd.get())
            dta  = float(self._dta_amt.get())
        except ValueError:
            messagebox.showerror("Input", "Enter valid numbers.")
            return
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO losses
                   (company_id,fy_id,assessment_year,loss_type,loss_amount,
                    carry_fwd_yrs,expiry_year,dta_amount)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (self.app.active_company_id, self.app.active_fy_id,
                 self._ay.get(), self._ltype.get(), loss, cf,
                 self._expiry.get(), dta))
            conn.commit()
        self._load()
        self._clear()

    def _update(self):
        if not self._sel_id:
            messagebox.showinfo("Select", "Select a row to update.")
            return
        self._recalc_loss()
        try:
            loss = float(self._loss_amt.get())
            cf   = int(self._cfwd.get())
            dta  = float(self._dta_amt.get())
        except ValueError:
            messagebox.showerror("Input", "Enter valid numbers.")
            return
        with get_conn() as conn:
            conn.execute(
                """UPDATE losses SET assessment_year=?,loss_type=?,loss_amount=?,
                   carry_fwd_yrs=?,expiry_year=?,dta_amount=? WHERE id=?""",
                (self._ay.get(), self._ltype.get(), loss, cf,
                 self._expiry.get(), dta, self._sel_id))
            conn.commit()
        self._load(); self._clear()

    def _delete(self):
        if not self._sel_id:
            messagebox.showinfo("Select", "Select a row.")
            return
        if messagebox.askyesno("Confirm", "Delete this entry?"):
            with get_conn() as conn:
                conn.execute("DELETE FROM losses WHERE id=?", (self._sel_id,))
                conn.commit()
            self._sel_id = None; self._load()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0])["values"]
        self._sel_id = vals[0]
        self._ay.set(vals[1])
        self._ltype.set(vals[2])
        # strip ₹ and commas from stored Indian format
        def parse_inr(s):
            return s.replace("₹", "").replace(",", "").replace("(", "-").replace(")", "")
        self._loss_amt.set(parse_inr(str(vals[3])))
        self._cfwd.set(str(vals[4]))
        self._expiry.set(str(vals[5]))
        self._dta_amt.set(parse_inr(str(vals[6])))

    def _clear(self):
        self._sel_id = None
        self._ay.set(ASSESSMENT_YEARS[-2])
        self._ltype.set("Business Loss")
        self._loss_amt.set("0.00"); self._cfwd.set("8")
        self._expiry.set(""); self._dta_amt.set("0.00")

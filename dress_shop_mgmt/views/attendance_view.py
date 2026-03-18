import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from views.shared_widgets import (
    DatePickerButton, MonthYearPickerButton, enable_smooth_scroll
)

THEME = {
    "primary":    "#0B1120", # Navy Blue
    "primary_dk": "#1E293B", # Dark Navy
    "secondary":  "#B91C1C", # Red
    "secondary_dk": "#991B1B", # Dark Red
    "bg_page":    "#F1F5F9",
    "bg_card":    "#FFFFFF",
    "text_main":  "#0F172A",
    "text_muted": "#475569",
    "border":     "#CBD5E1",
    "dark":       "#0F172A",
}

STATUS_LABELS  = {"P": "Present", "A": "Absent", "PL": "Paid Leave", "HD": "Half Day Present"}
STATUS_COLORS  = {"P": "#D1FAE5", "A": "#FEE2E2", "PL": "#FEF3C7", "HD": "#DBEAFE"}
STATUS_ICONS   = {"P": "✅", "A": "❌", "PL": "🏖", "HD": "🌓"}

class AttendanceView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db
        self.img_tk = None
        self._build_ui()
        self._refresh_emp_list()
        self._load_table()

    def _build_ui(self):
        # ── TOP BUTTON (Toggle History) ──
        top_btn_frame = tk.Frame(self, bg=THEME["bg_page"], pady=10)
        top_btn_frame.pack(side="top", fill="x", padx=20)
        
        self.toggle_btn = tk.Button(top_btn_frame, text="View Employee History & Photos", bg=THEME["secondary"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=8, cursor="hand2", command=self._toggle_history)
        self.toggle_btn.pack(side="right")

        # ── TOP: Cards Structure to Mark Attendance ──
        self.top_frame = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=20)
        self.top_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))
        self.top_frame.config(highlightbackground=THEME["primary"], highlightthickness=2)

        header = tk.Frame(self.top_frame, bg=THEME["bg_card"])
        header.pack(fill="x")
        
        tk.Label(header, text="📋 Mark Attendance", font=("Segoe UI Variable Display", 15, "bold"), fg=THEME["primary"], bg=THEME["bg_card"]).pack(side="left")

        # Date Picker for Mark Attendance
        f_dt = tk.Frame(header, bg=THEME["bg_card"])
        f_dt.pack(side="right")
        tk.Label(f_dt, text="Select Date:", font=("Segoe UI Semibold", 10), bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(side="left", padx=5)
        self._date_picker = DatePickerButton(f_dt, initial_date=datetime.now().date(), bg=THEME["bg_card"], command=self._on_mark_date_changed)
        self._date_picker.pack(side="left")

        # Employee Cards Area
        self.cards_canvas = tk.Canvas(self.top_frame, bg=THEME["bg_card"], bd=0, highlightthickness=0)
        sc = ttk.Scrollbar(self.top_frame, orient="vertical", command=self.cards_canvas.yview)
        self.cards_canvas.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        self.cards_canvas.pack(side="top", fill="both", expand=True, pady=(15, 0))

        self.cards_frame = tk.Frame(self.cards_canvas, bg=THEME["bg_card"])
        self.cards_win = self.cards_canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        
        def _on_card_frame_cfg(e):
            self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))
        def _on_canvas_cfg(e):
            self.cards_canvas.itemconfig(self.cards_win, width=e.width)
            
        self.cards_frame.bind("<Configure>", _on_card_frame_cfg)
        self.cards_canvas.bind("<Configure>", _on_canvas_cfg)
        enable_smooth_scroll(self.cards_canvas)

        # ── BOTTOM: Filter & History (Initially Hidden) ──
        self.bot_frame = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=10)
        self.bot_frame.config(highlightbackground=THEME["secondary"], highlightthickness=2)

        fbar = tk.Frame(self.bot_frame, bg=THEME["bg_card"])
        fbar.pack(side="top", fill="x", pady=(0, 10))

        tk.Label(fbar, text="🔍 Filter History:", font=("Segoe UI Semibold", 10, "bold"), bg=THEME["bg_card"], fg=THEME["secondary"]).pack(side="left", padx=(0, 10))
        
        tk.Label(fbar, text="Month/Year:", font=("Segoe UI Semibold", 9), bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(side="left", padx=(5, 5))
        self._filter_my = MonthYearPickerButton(fbar, initial_year=datetime.now().year, initial_month=datetime.now().month, bg=THEME["bg_card"])
        self._filter_my.pack(side="left")

        tk.Label(fbar, text="Employee:", font=("Segoe UI Semibold", 9), bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(side="left", padx=(15, 5))
        self.hist_emp_cb = ttk.Combobox(fbar, width=25, state="readonly", font=("Segoe UI", 10))
        self.hist_emp_cb.pack(side="left")
        
        self.hist_emp_cb.bind("<<ComboboxSelected>>", self._load_table_if_ready)

        tk.Button(fbar, text="Search", bg=THEME["primary"], fg="white", font=("Segoe UI", 9, "bold"), bd=0, padx=10, cursor="hand2", command=self._load_table).pack(side="left", padx=10)
        
        # Area for photo and table
        self.content_frame = tk.Frame(self.bot_frame, bg=THEME["bg_card"])
        self.content_frame.pack(side="top", fill="both", expand=True)

        self.photo_frame = tk.Frame(self.content_frame, bg=THEME["bg_card"], width=150, padx=10)
        self.photo_frame.pack(side="left", fill="y")
        self.photo_label = tk.Label(self.photo_frame, text="Select Employee", bg="#F1F5F9", font=("Segoe UI Semibold", 9), fg=THEME["text_muted"], width=18, height=8, relief="solid", bd=1)
        self.photo_label.pack(side="top", pady=10)
        self.emp_name_label = tk.Label(self.photo_frame, text="", bg=THEME["bg_card"], font=("Segoe UI", 11, "bold"), fg=THEME["primary"])
        self.emp_name_label.pack(side="top", pady=5)

        cols = ("Name", "Date", "Status", "Perm Hours")
        self.tree = ttk.Treeview(self.content_frame, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.column("Name", width=150, anchor="w")
        self.tree.column("Date", width=120)
        self.tree.column("Status", width=150)
        self.tree.column("Perm Hours", width=100)
        self.tree.pack(side="left", fill="both", expand=True, padx=10)

        for code in STATUS_COLORS:
            self.tree.tag_configure(code, background=STATUS_COLORS[code])
            
        tree_sc = ttk.Scrollbar(self.content_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sc.set)
        tree_sc.pack(side="right", fill="y")
        
        self.history_visible = False

    def _toggle_history(self):
        self.history_visible = not self.history_visible
        if self.history_visible:
            self.bot_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 20))
            self.toggle_btn.config(text="Hide Employee History", bg=THEME["primary"])
        else:
            self.bot_frame.pack_forget()
            self.toggle_btn.config(text="View Employee History & Photos", bg=THEME["secondary"])
            
    def _load_table_if_ready(self, *args):
        # Optional: auto load table when combo box changes
        self._load_table()
        
    def _on_mark_date_changed(self):
        self._refresh_emp_list()

    def _refresh_emp_list(self):
        conn = self.db.get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT emp_id, name, designation FROM employees ORDER BY name")
        self._employees = cur.fetchall()
        
        items = [f"{r['emp_id']} | {r['name']}" for r in self._employees]
        self.hist_emp_cb["values"] = ["ALL EMPLOYEES"] + items
        if not self.hist_emp_cb.get():
            self.hist_emp_cb.set("ALL EMPLOYEES")
            
        for w in self.cards_frame.winfo_children():
            w.destroy()
            
        date = self._date_picker.get_date_str()
        
        row_frame = None
        col_count = 0
        
        for emp in self._employees:
            eid = emp["emp_id"]
            name = emp["name"]
            desg = emp["designation"] or "Staff"
            
            cur.execute("SELECT status FROM attendance WHERE emp_id=? AND date=?", (eid, date))
            record = cur.fetchone()
            
            card_bg = "#F8FAFC"
            status_text = "Not Marked"
            status_color = THEME["text_muted"]
            
            if record:
                st = record["status"]
                card_bg = STATUS_COLORS.get(st, card_bg)
                status_text = f"{STATUS_ICONS.get(st, '')} {STATUS_LABELS.get(st, st)}"
                if st == "P": status_color = "#047857"
                elif st == "A": status_color = "#B91C1C"
                elif st == "HD": status_color = "#1D4ED8"
                elif st == "PL": status_color = "#D97706"

            if col_count % 2 == 0:
                row_frame = tk.Frame(self.cards_frame, bg=THEME["bg_card"])
                row_frame.pack(fill="x", pady=8)
            col_count += 1
                
            card = tk.Frame(row_frame, bg=card_bg, highlightbackground=THEME["border"], highlightthickness=1, cursor="hand2", width=300, height=90)
            card.pack(side="left", padx=15, fill="both", expand=True)
            card.pack_propagate(False)
            
            def make_handler(e_id=eid, e_name=name):
                return lambda ev: self._show_mark_popup(e_id, e_name)
                
            card.bind("<Button-1>", make_handler())
            
            inner = tk.Frame(card, bg=card_bg)
            inner.place(relx=0.5, rely=0.5, anchor="center")
            tk.Label(inner, text=name, font=("Segoe UI", 13, "bold"), bg=card_bg, fg=THEME["text_main"]).pack()
            tk.Label(inner, text=desg, font=("Segoe UI", 10), bg=card_bg, fg=THEME["primary"]).pack()
            tk.Label(inner, text=status_text, font=("Segoe UI Semibold", 10), bg=card_bg, fg=status_color).pack(pady=(5,0))
            
            for child in inner.winfo_children():
                child.bind("<Button-1>", make_handler())
            inner.bind("<Button-1>", make_handler())

        conn.close()

    def _show_mark_popup(self, emp_id, emp_name):
        date = self._date_picker.get_date_str()
        
        pop = tk.Toplevel(self)
        pop.title(f"Mark Attendance")
        pop.geometry("350x280")
        pop.transient(self.winfo_toplevel())
        pop.grab_set()
        pop.configure(bg=THEME["bg_card"], padx=20, pady=20)
        
        pop.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - 175
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - 150
        pop.geometry(f"+{x}+{y}")
        
        tk.Label(pop, text=f"Employee: {emp_name}", font=("Segoe UI Semibold", 12), bg=THEME["bg_card"], fg=THEME["primary"]).pack(anchor="w")
        tk.Label(pop, text=f"Date: {date}", font=("Segoe UI", 10), bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w", pady=(0, 15))
        
        def _save_att(code):
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM attendance WHERE emp_id=? AND date=?", (emp_id, date))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE attendance SET status=? WHERE id=?", (code, existing["id"]))
            else:
                cur.execute("INSERT INTO attendance (emp_id, date, status, permission_hours) VALUES (?,?,?,0)", (emp_id, date, code))
            conn.commit()
            conn.close()
            pop.destroy()
            self._refresh_emp_list()
            self._load_table()
            
        btn_frame = tk.Frame(pop, bg=THEME["bg_card"])
        btn_frame.pack(fill="both", expand=True)
        
        codes = [("P", "Present"), ("HD", "Half Day Present"), ("PL", "Paid Leave"), ("A", "Absent")]
        for code, label in codes:
            b = tk.Button(btn_frame, text=f"{STATUS_ICONS[code]} {label}", bg=STATUS_COLORS[code], font=("Segoe UI", 10, "bold"), bd=1, cursor="hand2", command=lambda c=code: _save_att(c))
            b.pack(fill="x", pady=5, ipady=4)
            
    def _load_table(self, *args):
        for row in self.tree.get_children():
            self.tree.delete(row)

        emp_f = self.hist_emp_cb.get()
        y = self._filter_my.get_year()
        m = self._filter_my.get_month()
        patt = f"{y}-{m}%"

        conn = self.db.get_connection()
        cur  = conn.cursor()

        query = """SELECT a.id, e.name, a.date, a.status, a.permission_hours 
                   FROM attendance a 
                   JOIN employees e ON a.emp_id = e.emp_id 
                   WHERE a.date LIKE ?"""
        params = [patt]
        
        eid = None
        if emp_f and emp_f != "ALL EMPLOYEES":
            eid = int(emp_f.split(" | ")[0].strip())
            query += " AND a.emp_id = ?"
            params.append(eid)
            
        query += " ORDER BY a.date DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # Determine photo to display
        if eid:
            cur.execute("SELECT name, photo_path FROM employees WHERE emp_id=?", (eid,))
            emp_info = cur.fetchone()
            if emp_info:
                self.emp_name_label.config(text=emp_info["name"])
                photo_path = emp_info["photo_path"]
                self._update_photo(photo_path)
            else:
                self.emp_name_label.config(text="ALL EMPLOYEES")
                self._update_photo(None)
        else:
            self.emp_name_label.config(text="ALL EMPLOYEES")
            self._update_photo(None)

        conn.close()

        for r in rows:
            code = r["status"]
            display = f"{STATUS_ICONS.get(code,'')} {STATUS_LABELS.get(code, code)}"
            perm = r["permission_hours"] if r["permission_hours"] else "-"
            self.tree.insert("", "end", values=(r["name"], r["date"], display, perm), tags=(code,))
            
    def _update_photo(self, photo_path):
        self.img_tk = None
        if photo_path and os.path.exists(photo_path) and PIL_AVAILABLE:
            try:
                img = Image.open(photo_path)
                img.thumbnail((120, 120))
                self.img_tk = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.img_tk, text="")
            except Exception as e:
                self.photo_label.config(image="", text="[Photo Error]")
        else:
            self.photo_label.config(image="", text="[No Photo]")

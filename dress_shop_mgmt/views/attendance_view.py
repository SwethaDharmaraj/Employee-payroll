import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from views.shared_widgets import DatePickerButton, MonthYearPickerButton, enable_smooth_scroll

THEME = {
    "primary": "#3B28F5",
    "primary_dark": "#2719B8",
    "page_bg": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFD",
    "border": "#D9E2EF",
    "text": "#13233F",
    "muted": "#64748B",
    "success": "#12B981",
    "warning": "#F59E0B",
    "info": "#3B82F6",
    "danger": "#FF4D4F",
}

STATUS_META = {
    "P": {"label": "Present", "accent": THEME["success"], "soft": "#E9FBF3"},
    "HD": {"label": "Half-day", "accent": THEME["warning"], "soft": "#FFF5E6"},
    "PL": {"label": "Paid Leave", "accent": THEME["info"], "soft": "#EEF5FF"},
    "A": {"label": "Absent", "accent": THEME["danger"], "soft": "#FFF0F0"},
}


class AttendanceView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["page_bg"])
        self.db = db
        self._employees = []
        self._status_by_emp = {}
        self._draft_status_by_emp = {}
        self._row_widgets = {}
        self._avatar_cache = {}
        self.img_tk = None
        self.history_visible = False

        self._build_ui()
        self._refresh_emp_list()
        self._load_table()

    def _build_ui(self):
        self.pack_propagate(False)

        page = tk.Frame(self, bg=THEME["page_bg"])
        page.pack(fill="both", expand=True, padx=18, pady=16)

        self._build_toolbar(page)
        self._build_stats(page)
        self._build_employee_table(page)
        self._build_footer(page)
        self._build_history_panel(page)

    def _build_toolbar(self, parent):
        bar = tk.Frame(parent, bg=THEME["page_bg"])
        bar.pack(fill="x", pady=(0, 16))

        date_shell = tk.Frame(
            bar,
            bg=THEME["surface"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        date_shell.pack(side="left")

        tk.Button(
            date_shell,
            text="‹",
            command=lambda: self._shift_date(-1),
            bg=THEME["surface"],
            fg=THEME["text"],
            font=("Segoe UI", 18),
            bd=0,
            cursor="hand2",
            padx=8,
        ).pack(side="left")

        self._date_picker = DatePickerButton(
            date_shell,
            initial_date=datetime.now().date(),
            on_change=lambda _d: self._on_mark_date_changed(),
            bg=THEME["surface"],
        )
        self._date_picker.pack(side="left", padx=6)

        tk.Button(
            date_shell,
            text="›",
            command=lambda: self._shift_date(1),
            bg=THEME["surface"],
            fg=THEME["text"],
            font=("Segoe UI", 18),
            bd=0,
            cursor="hand2",
            padx=8,
        ).pack(side="left")

        right = tk.Frame(bar, bg=THEME["page_bg"])
        right.pack(side="right")

        search_shell = tk.Frame(
            right,
            bg=THEME["surface"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=12,
            pady=6,
        )
        search_shell.pack(side="left", padx=(0, 12))

        tk.Label(
            search_shell,
            text="⌕",
            bg=THEME["surface"],
            fg="#94A3B8",
            font=("Segoe UI", 15),
        ).pack(side="left", padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_employee_rows())
        self.search_entry = tk.Entry(
            search_shell,
            textvariable=self.search_var,
            width=28,
            bd=0,
            font=("Segoe UI", 11),
            bg=THEME["surface"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
        )
        self.search_entry.pack(side="left")
        self.search_entry.insert(0, "Search employee...")
        self.search_entry.config(fg="#94A3B8")
        self.search_entry.bind("<FocusIn>", self._clear_search_placeholder)
        self.search_entry.bind("<FocusOut>", self._restore_search_placeholder)

        self.save_btn = tk.Button(
            right,
            text="Save Attendance",
            command=self._save_attendance,
            bg=THEME["primary"],
            fg="white",
            activebackground=THEME["primary_dark"],
            activeforeground="white",
            font=("Segoe UI Semibold", 11),
            bd=0,
            cursor="hand2",
            padx=24,
            pady=12,
        )
        self.save_btn.pack(side="left")

    def _build_stats(self, parent):
        stats = tk.Frame(parent, bg=THEME["page_bg"])
        stats.pack(fill="x", pady=(0, 16))

        self.stat_vars = {
            "total": tk.StringVar(value="0"),
            "present": tk.StringVar(value="0"),
            "leave": tk.StringVar(value="0"),
            "absent": tk.StringVar(value="0"),
        }

        cards = [
            ("TOTAL EMPLOYEES", self.stat_vars["total"], THEME["text"]),
            ("PRESENT TODAY", self.stat_vars["present"], THEME["success"]),
            ("ON LEAVE", self.stat_vars["leave"], THEME["info"]),
            ("ABSENT", self.stat_vars["absent"], THEME["danger"]),
        ]

        for idx, (title, var, accent) in enumerate(cards):
            card = tk.Frame(
                stats,
                bg=THEME["surface"],
                highlightbackground=THEME["border"],
                highlightthickness=1,
                padx=18,
                pady=18,
            )
            card.grid(row=0, column=idx, padx=(0, 14 if idx < 3 else 0), sticky="nsew")
            tk.Frame(card, bg=accent, width=5, height=92).place(x=0, y=0)
            tk.Label(
                card,
                text=title,
                font=("Segoe UI Semibold", 10),
                bg=THEME["surface"],
                fg="#5D7493",
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=var,
                font=("Segoe UI Variable Display", 25, "bold"),
                bg=THEME["surface"],
                fg=accent,
            ).pack(anchor="w", pady=(8, 0))

        for idx in range(4):
            stats.columnconfigure(idx, weight=1)

    def _build_employee_table(self, parent):
        table_card = tk.Frame(
            parent,
            bg=THEME["surface"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        table_card.pack(fill="both", expand=True)

        header = tk.Frame(table_card, bg=THEME["surface"], pady=14, padx=18)
        header.pack(fill="x")
        tk.Label(
            header, text="EMPLOYEE", font=("Segoe UI Semibold", 10), bg=THEME["surface"], fg="#5D7493"
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header, text="ID & DEPT", font=("Segoe UI Semibold", 10), bg=THEME["surface"], fg="#5D7493"
        ).grid(row=0, column=1, sticky="w", padx=(24, 0))
        tk.Label(
            header, text="MARK ATTENDANCE", font=("Segoe UI Semibold", 10), bg=THEME["surface"], fg="#5D7493"
        ).grid(row=0, column=2, sticky="w", padx=(24, 0))
        header.columnconfigure(0, weight=4)
        header.columnconfigure(1, weight=2)
        header.columnconfigure(2, weight=5)

        ttk.Separator(table_card, orient="horizontal").pack(fill="x")

        list_holder = tk.Frame(table_card, bg=THEME["surface"])
        list_holder.pack(fill="both", expand=True)

        self.rows_canvas = tk.Canvas(
            list_holder,
            bg=THEME["surface"],
            bd=0,
            highlightthickness=0,
        )
        self.rows_canvas.pack(side="left", fill="both", expand=True)

        row_scroll = ttk.Scrollbar(list_holder, orient="vertical", command=self.rows_canvas.yview)
        row_scroll.pack(side="right", fill="y")
        self.rows_canvas.configure(yscrollcommand=row_scroll.set)

        self.rows_frame = tk.Frame(self.rows_canvas, bg=THEME["surface"])
        self.rows_window = self.rows_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind(
            "<Configure>", lambda _e: self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all"))
        )
        self.rows_canvas.bind(
            "<Configure>", lambda e: self.rows_canvas.itemconfigure(self.rows_window, width=e.width)
        )
        enable_smooth_scroll(self.rows_canvas)

        self.table_note = tk.Label(
            table_card,
            text='* Changes are auto-drafted. Click "Save Attendance" to finalize.',
            font=("Segoe UI", 10, "italic"),
            bg=THEME["surface"],
            fg="#64748B",
            padx=18,
            pady=12,
        )
        self.table_note.pack(anchor="w")

    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=THEME["page_bg"], pady=14)
        footer.pack(fill="x")

        left = tk.Frame(footer, bg=THEME["page_bg"])
        left.pack(side="left")
        self.toggle_btn = tk.Button(
            left,
            text="View Employee History",
            bg=THEME["surface"],
            fg=THEME["text"],
            activebackground=THEME["surface_alt"],
            activeforeground=THEME["text"],
            font=("Segoe UI Semibold", 10),
            bd=0,
            cursor="hand2",
            padx=14,
            pady=10,
            command=self._toggle_history,
        )
        self.toggle_btn.pack(side="left")

        right = tk.Frame(footer, bg=THEME["page_bg"])
        right.pack(side="right")

        tk.Button(
            right,
            text="Cancel",
            command=self._cancel_drafts,
            bg=THEME["page_bg"],
            fg=THEME["muted"],
            activebackground=THEME["page_bg"],
            activeforeground=THEME["text"],
            font=("Segoe UI Semibold", 11),
            bd=0,
            cursor="hand2",
            padx=12,
            pady=10,
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            right,
            text="Save & Finalize Attendance",
            command=self._save_attendance,
            bg=THEME["primary"],
            fg="white",
            activebackground=THEME["primary_dark"],
            activeforeground="white",
            font=("Segoe UI Semibold", 11),
            bd=0,
            cursor="hand2",
            padx=26,
            pady=14,
        ).pack(side="left")

    def _build_history_panel(self, parent):
        self.bot_frame = tk.Frame(
            parent,
            bg=THEME["surface"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=20,
            pady=18,
        )

        fbar = tk.Frame(self.bot_frame, bg=THEME["surface"])
        fbar.pack(fill="x", pady=(0, 12))

        tk.Label(
            fbar,
            text="Attendance History",
            font=("Segoe UI Variable Display", 14, "bold"),
            bg=THEME["surface"],
            fg=THEME["text"],
        ).pack(side="left")

        filters = tk.Frame(fbar, bg=THEME["surface"])
        filters.pack(side="right")

        tk.Label(filters, text="Month/Year", font=("Segoe UI", 9), bg=THEME["surface"], fg=THEME["muted"]).pack(
            side="left", padx=(0, 6)
        )
        self._filter_my = MonthYearPickerButton(
            filters,
            initial_year=datetime.now().year,
            initial_month=datetime.now().month,
            bg=THEME["surface"],
        )
        self._filter_my.pack(side="left")

        tk.Label(filters, text="Employee", font=("Segoe UI", 9), bg=THEME["surface"], fg=THEME["muted"]).pack(
            side="left", padx=(14, 6)
        )
        self.hist_emp_cb = ttk.Combobox(filters, width=24, state="readonly", font=("Segoe UI", 10))
        self.hist_emp_cb.pack(side="left")
        self.hist_emp_cb.bind("<<ComboboxSelected>>", self._load_table_if_ready)

        tk.Button(
            filters,
            text="Search",
            command=self._load_table,
            bg=THEME["primary"],
            fg="white",
            font=("Segoe UI Semibold", 10),
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
        ).pack(side="left", padx=(12, 0))

        content = tk.Frame(self.bot_frame, bg=THEME["surface"])
        content.pack(fill="both", expand=True)

        self.photo_frame = tk.Frame(content, bg=THEME["surface"], width=180)
        self.photo_frame.pack(side="left", fill="y", padx=(0, 14))
        self.photo_frame.pack_propagate(False)

        self.photo_label = tk.Label(
            self.photo_frame,
            text="[No Photo]",
            bg=THEME["surface_alt"],
            fg=THEME["muted"],
            font=("Segoe UI Semibold", 10),
            width=16,
            height=8,
            relief="solid",
            bd=1,
        )
        self.photo_label.pack(pady=(6, 8))

        self.emp_name_label = tk.Label(
            self.photo_frame,
            text="ALL EMPLOYEES",
            bg=THEME["surface"],
            fg=THEME["text"],
            font=("Segoe UI Semibold", 11),
            wraplength=160,
            justify="center",
        )
        self.emp_name_label.pack()

        cols = ("Name", "Date", "Status", "Perm Hours")
        self.tree = ttk.Treeview(content, columns=cols, show="headings", height=8)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("Name", width=180, anchor="w")
        self.tree.column("Date", width=110, anchor="center")
        self.tree.column("Status", width=140, anchor="center")
        self.tree.column("Perm Hours", width=90, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        for code, meta in STATUS_META.items():
            self.tree.tag_configure(code, background=meta["soft"])

        tree_sc = ttk.Scrollbar(content, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sc.set)
        tree_sc.pack(side="right", fill="y")

    def _clear_search_placeholder(self, _event):
        if self.search_entry.get() == "Search employee..." and self.search_entry.cget("fg") == "#94A3B8":
            self.search_entry.delete(0, "end")
            self.search_entry.config(fg=THEME["text"])

    def _restore_search_placeholder(self, _event):
        if not self.search_entry.get().strip():
            self.search_entry.delete(0, "end")
            self.search_entry.insert(0, "Search employee...")
            self.search_entry.config(fg="#94A3B8")

    def _get_search_term(self):
        text = self.search_var.get().strip()
        if text == "Search employee..." and self.search_entry.cget("fg") == "#94A3B8":
            return ""
        return text.lower()

    def _shift_date(self, days):
        current = self._date_picker.selected_date
        self._date_picker.set_date(current + timedelta(days=days))
        self._on_mark_date_changed()

    def _toggle_history(self):
        self.history_visible = not self.history_visible
        if self.history_visible:
            self.bot_frame.pack(fill="both", expand=False, pady=(0, 14))
            self.toggle_btn.config(text="Hide Employee History")
        else:
            self.bot_frame.pack_forget()
            self.toggle_btn.config(text="View Employee History")

    def _load_table_if_ready(self, *_args):
        self._load_table()

    def _on_mark_date_changed(self):
        self._refresh_emp_list()

    def _refresh_emp_list(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT emp_id, name, designation, photo_path, phone FROM employees ORDER BY emp_id ASC")
        self._employees = cur.fetchall()

        items = [f"{row['emp_id']} | {row['name']}" for row in self._employees]
        self.hist_emp_cb["values"] = ["ALL EMPLOYEES"] + items
        if not self.hist_emp_cb.get():
            self.hist_emp_cb.set("ALL EMPLOYEES")

        selected_date = self._date_picker.get_date_str()
        cur.execute("SELECT emp_id, status FROM attendance WHERE date=?", (selected_date,))
        self._status_by_emp = {row["emp_id"]: row["status"] for row in cur.fetchall()}
        conn.close()

        self._draft_status_by_emp = dict(self._status_by_emp)
        self._render_employee_rows()
        self._update_stats()
        self._load_table()

    def _render_employee_rows(self):
        for child in self.rows_frame.winfo_children():
            child.destroy()
        self._row_widgets = {}

        search = self._get_search_term()
        visible = 0

        for emp in self._employees:
            haystack = f"{emp['name']} {emp['designation'] or ''} {emp['emp_id']}".lower()
            if search and search not in haystack:
                continue
            visible += 1
            self._build_employee_row(emp)

        if visible == 0:
            empty = tk.Label(
                self.rows_frame,
                text="No employees match this search.",
                font=("Segoe UI", 11),
                bg=THEME["surface"],
                fg=THEME["muted"],
                pady=28,
            )
            empty.pack(fill="x")

    def _build_employee_row(self, emp):
        row = tk.Frame(self.rows_frame, bg=THEME["surface"], padx=18, pady=14)
        row.pack(fill="x")
        ttk.Separator(self.rows_frame, orient="horizontal").pack(fill="x")

        left = tk.Frame(row, bg=THEME["surface"])
        left.grid(row=0, column=0, sticky="w")

        avatar = self._make_avatar(left, emp)
        avatar.pack(side="left", padx=(0, 14))

        info = tk.Frame(left, bg=THEME["surface"])
        info.pack(side="left")
        tk.Label(
            info,
            text=emp["name"],
            font=("Segoe UI Semibold", 12),
            bg=THEME["surface"],
            fg=THEME["text"],
        ).pack(anchor="w")
        secondary = emp["phone"] or (emp["designation"] or "Team Member")
        tk.Label(
            info,
            text=secondary,
            font=("Segoe UI", 10),
            bg=THEME["surface"],
            fg=THEME["muted"],
        ).pack(anchor="w", pady=(2, 0))

        meta = tk.Frame(row, bg=THEME["surface"])
        meta.grid(row=0, column=1, sticky="w", padx=(24, 0))
        tk.Label(
            meta,
            text=f"EMP-{emp['emp_id']:04d}",
            font=("Segoe UI Semibold", 12),
            bg=THEME["surface"],
            fg=THEME["text"],
        ).pack(anchor="w")
        tk.Label(
            meta,
            text=emp["designation"] or "General Staff",
            font=("Segoe UI", 10),
            bg=THEME["surface"],
            fg=THEME["muted"],
        ).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(row, bg=THEME["surface"])
        actions.grid(row=0, column=2, sticky="w", padx=(24, 0))

        buttons = {}
        for code in ("P", "HD", "PL", "A"):
            btn = tk.Button(
                actions,
                text=STATUS_META[code]["label"],
                command=lambda c=code, eid=emp["emp_id"]: self._set_status(eid, c),
                font=("Segoe UI Semibold", 10),
                bd=1,
                cursor="hand2",
                padx=14,
                pady=8,
                width=10,
            )
            btn.pack(side="left", padx=(0, 10))
            buttons[code] = btn

        row.columnconfigure(0, weight=4)
        row.columnconfigure(1, weight=2)
        row.columnconfigure(2, weight=5)

        self._row_widgets[emp["emp_id"]] = buttons
        self._apply_row_status_style(emp["emp_id"])

    def _make_avatar(self, parent, emp):
        photo_path = emp["photo_path"]
        if photo_path and os.path.exists(photo_path) and PIL_AVAILABLE:
            try:
                img = Image.open(photo_path)
                img.thumbnail((44, 44))
                key = (photo_path, os.path.getmtime(photo_path))
                if key not in self._avatar_cache:
                    self._avatar_cache[key] = ImageTk.PhotoImage(img)
                return tk.Label(parent, image=self._avatar_cache[key], bg=THEME["surface"])
            except Exception:
                pass

        initials = "".join(part[:1].upper() for part in emp["name"].split()[:2]) or "E"
        avatar = tk.Label(
            parent,
            text=initials,
            font=("Segoe UI Semibold", 11),
            bg="#E7ECFF",
            fg=THEME["primary"],
            width=4,
            height=2,
        )
        return avatar

    def _set_status(self, emp_id, code):
        self._draft_status_by_emp[emp_id] = code
        self._apply_row_status_style(emp_id)
        self._update_stats()

    def _apply_row_status_style(self, emp_id):
        current = self._draft_status_by_emp.get(emp_id)
        btns = self._row_widgets.get(emp_id, {})
        for code, btn in btns.items():
            meta = STATUS_META[code]
            selected = code == current
            btn.config(
                bg=meta["accent"] if selected else THEME["surface"],
                fg="white" if selected else meta["accent"],
                activebackground=meta["accent"],
                activeforeground="white",
                highlightbackground=meta["accent"],
                highlightcolor=meta["accent"],
                relief="solid",
            )

    def _update_stats(self):
        total = len(self._employees)
        present = 0
        leave = 0
        absent = 0

        for status in self._draft_status_by_emp.values():
            if status in ("P", "HD"):
                present += 1
            elif status == "PL":
                leave += 1
            elif status == "A":
                absent += 1

        self.stat_vars["total"].set(str(total))
        self.stat_vars["present"].set(str(present))
        self.stat_vars["leave"].set(str(leave))
        self.stat_vars["absent"].set(str(absent))

        dirty = self._draft_status_by_emp != self._status_by_emp
        self.save_btn.config(text="Save Attendance*" if dirty else "Save Attendance")

    def _cancel_drafts(self):
        self._draft_status_by_emp = dict(self._status_by_emp)
        for emp_id in self._row_widgets:
            self._apply_row_status_style(emp_id)
        self._update_stats()

    def _save_attendance(self):
        changed = {
            emp_id: status
            for emp_id, status in self._draft_status_by_emp.items()
            if self._status_by_emp.get(emp_id) != status
        }
        if not changed:
            messagebox.showinfo("Attendance", "There are no attendance changes to save.", parent=self.winfo_toplevel())
            return

        date = self._date_picker.get_date_str()
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            for emp_id, code in changed.items():
                cur.execute("SELECT id FROM attendance WHERE emp_id=? AND date=?", (emp_id, date))
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE attendance SET status=?, permission_hours=0 WHERE id=?", (code, existing["id"]))
                else:
                    cur.execute(
                        "INSERT INTO attendance (emp_id, date, status, permission_hours) VALUES (?,?,?,0)",
                        (emp_id, date, code),
                    )
            conn.commit()
        finally:
            conn.close()

        self._status_by_emp = dict(self._draft_status_by_emp)
        self._update_stats()
        self._load_table()
        messagebox.showinfo("Attendance Saved", f"Attendance for {date} has been updated.", parent=self.winfo_toplevel())

    def _load_table(self, *_args):
        for row in self.tree.get_children():
            self.tree.delete(row)

        emp_filter = self.hist_emp_cb.get()
        year = self._filter_my.get_year()
        month = self._filter_my.get_month()
        pattern = f"{year}-{month}%"

        conn = self.db.get_connection()
        cur = conn.cursor()

        query = """
            SELECT a.id, e.name, a.date, a.status, a.permission_hours
            FROM attendance a
            JOIN employees e ON a.emp_id = e.emp_id
            WHERE a.date LIKE ?
        """
        params = [pattern]

        selected_emp = None
        if emp_filter and emp_filter != "ALL EMPLOYEES":
            selected_emp = int(emp_filter.split(" | ")[0].strip())
            query += " AND a.emp_id = ?"
            params.append(selected_emp)

        query += " ORDER BY a.date DESC, e.name ASC"
        cur.execute(query, params)
        rows = cur.fetchall()

        if selected_emp:
            cur.execute("SELECT name, photo_path FROM employees WHERE emp_id=?", (selected_emp,))
            emp_info = cur.fetchone()
            if emp_info:
                self.emp_name_label.config(text=emp_info["name"])
                self._update_photo(emp_info["photo_path"])
            else:
                self.emp_name_label.config(text="ALL EMPLOYEES")
                self._update_photo(None)
        else:
            self.emp_name_label.config(text="ALL EMPLOYEES")
            self._update_photo(None)

        conn.close()

        for row in rows:
            code = row["status"]
            label = STATUS_META.get(code, {"label": code})["label"]
            perm = row["permission_hours"] if row["permission_hours"] else "-"
            self.tree.insert("", "end", values=(row["name"], row["date"], label, perm), tags=(code,))

    def _update_photo(self, photo_path):
        self.img_tk = None
        if photo_path and os.path.exists(photo_path) and PIL_AVAILABLE:
            try:
                img = Image.open(photo_path)
                img.thumbnail((120, 120))
                self.img_tk = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.img_tk, text="", width=120, height=120)
                return
            except Exception:
                pass
        self.photo_label.config(image="", text="[No Photo]", width=16, height=8)

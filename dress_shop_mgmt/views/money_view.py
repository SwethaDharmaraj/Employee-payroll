import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from views.shared_widgets import (
    CalendarPopup, DatePickerButton, enable_smooth_scroll
)

THEME = {
    "primary":    "#1D4ED8",
    "primary_dk": "#1E40AF",
    "secondary":  "#3B82F6",
    "bg_page":    "#F1F5F9",
    "bg_card":    "#FFFFFF",
    "text_main":  "#0F172A",
    "text_muted": "#475569",
    "border":     "#CBD5E1",
    "success":    "#10B981",
    "dark":       "#0F172A",
    "warning":    "#F59E0B",
    "danger":     "#EF4444",
}

DENOMS = [10, 20, 50, 100, 200]


class MoneyView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db

        # --- Internal States ---
        self._total1 = 0.0
        self._total2 = 0.0
        self._shortage = 0.0
        self._finalized = 0.0

        # Column 2: Opening Count (Previous Day - Auto-fetched)
        self.opening_vars = {d: tk.IntVar(value=0) for d in DENOMS}
        # Column 3: Closing Count (Today's Count - User Input)
        self.closing_vars = {d: tk.StringVar(value="0") for d in DENOMS}

        # Additional Inputs
        self.total_sales_var = tk.StringVar(value="0")
        self.cash_received_var = tk.StringVar(value="0")  # ₹500 Notes amount
        self.upi_gpay_var = tk.StringVar(value="0")
        self.expenses_var = tk.StringVar(value="0")

        # Breakdown Text
        self.total1_txt = tk.StringVar(value="Total1 = (Cash In - Cash Out) = ₹0")
        self.total2_txt = tk.StringVar(value="Total2 = (Sales - (GPay + 500s)) = ₹0")
        self.shortage_txt = tk.StringVar(value="Shortage = (Total2 + Total1) = ₹0")
        self.final_txt = tk.StringVar(value="Final = (Shortage - Expenses) = ₹0")

        self.diff_labels = {}
        self.cash_in_labels = {}
        self.cash_out_labels = {}

        # Track all entry widgets for Enter-key navigation
        self._all_entries = []

        # Selected date
        self._selected_date = datetime.now().date()

        self._build_ui()
        self._load_data()

    # ── Helper: Create a styled entry with focus effects ─────────────────────
    def _styled_entry(self, parent, textvariable, width=12, justify="center",
                      font=("Segoe UI", 11), track=True, **kw):
        wrapper = tk.Frame(parent, bg="#E2E8F0", padx=2, pady=2)

        e = tk.Entry(wrapper, textvariable=textvariable, font=font, width=width,
                     justify=justify, bd=0, bg="#F8FAFC",
                     insertbackground=THEME["primary"],
                     selectbackground=THEME["primary"],
                     selectforeground="white", **kw)
        e.pack(ipady=6, padx=1, pady=1)

        def _focus_in(_):
            wrapper.config(bg=THEME["primary"])
            e.config(bg="white")

        def _focus_out(_):
            wrapper.config(bg="#E2E8F0")
            e.config(bg="#F8FAFC")

        e.bind("<FocusIn>", _focus_in)
        e.bind("<FocusOut>", _focus_out)

        if track:
            self._all_entries.append(e)

        e.bind("<Return>", self._focus_next_entry)
        e.bind("<KP_Enter>", self._focus_next_entry)

        return wrapper, e

    def _focus_next_entry(self, event):
        widget = event.widget
        if widget in self._all_entries:
            idx = self._all_entries.index(widget)
            nxt = (idx + 1) % len(self._all_entries)
            self._all_entries[nxt].focus_set()
            self._all_entries[nxt].select_range(0, "end")
            self._ensure_visible(self._all_entries[nxt])
        return "break"

    def _ensure_visible(self, widget):
        try:
            self.canvas.update_idletasks()
            wy = widget.winfo_rooty() - self.scrollable_frame.winfo_rooty()
            canvas_h = self.canvas.winfo_height()
            top_frac = self.canvas.yview()[0]
            total_h = self.scrollable_frame.winfo_reqheight()
            top_px = top_frac * total_h
            bottom_px = top_px + canvas_h
            if wy < top_px + 40:
                self.canvas.yview_moveto((wy - 40) / total_h)
            elif wy > bottom_px - 80:
                self.canvas.yview_moveto((wy - canvas_h + 80) / total_h)
        except:
            pass

    # ── Section Header Helper ────────────────────────────────────────────────
    def _section_header(self, parent, icon, title, subtitle=None):
        hdr = tk.Frame(parent, bg=THEME["bg_card"])
        hdr.pack(fill="x", pady=(0, 12))

        tk.Label(hdr, text=icon, font=("Segoe UI", 18),
                 bg=THEME["bg_card"]).pack(side="left", padx=(0, 10))

        txt_f = tk.Frame(hdr, bg=THEME["bg_card"])
        txt_f.pack(side="left")
        tk.Label(txt_f, text=title,
                 font=("Segoe UI Variable Display", 13, "bold"),
                 bg=THEME["bg_card"], fg=THEME["text_main"]).pack(anchor="w")
        if subtitle:
            tk.Label(txt_f, text=subtitle,
                     font=("Segoe UI", 8),
                     bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w")

        accent = tk.Frame(parent, bg=THEME["primary"], height=2)
        accent.pack(fill="x", pady=(0, 8))
        return hdr

    # ── Calendar Date Picker ─────────────────────────────────────────────────
    def _on_date_picked(self, picked_date):
        self._selected_date = picked_date
        self._load_data()

    # ── Build UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Scrollable Canvas ──
        self.canvas = tk.Canvas(self, bg=THEME["bg_page"],
                                highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                        command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg_page"])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Enable smooth scrolling
        enable_smooth_scroll(self.canvas)

        container = self.scrollable_frame

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 1: TOP HEADER BAR
        # ══════════════════════════════════════════════════════════════════════
        header_card = tk.Frame(container, bg=THEME["bg_card"], padx=28, pady=18)
        header_card.pack(fill="x", padx=16, pady=(12, 8))
        header_card.config(highlightbackground=THEME["border"],
                           highlightthickness=1)

        # Left: Title
        title_f = tk.Frame(header_card, bg=THEME["bg_card"])
        title_f.pack(side="left")
        tk.Label(title_f, text="🏧",
                 font=("Segoe UI", 24),
                 bg=THEME["bg_card"]).pack(side="left", padx=(0, 12))
        t_txt = tk.Frame(title_f, bg=THEME["bg_card"])
        t_txt.pack(side="left")
        tk.Label(t_txt, text="Cashier Box Management",
                 font=("Segoe UI Variable Display", 16, "bold"),
                 bg=THEME["bg_card"], fg=THEME["text_main"]).pack(anchor="w")
        tk.Label(t_txt, text="Manage daily denomination counts, sales & cash flow",
                 font=("Segoe UI", 9),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w")

        # Right: Date Picker & Actions
        action_f = tk.Frame(header_card, bg=THEME["bg_card"])
        action_f.pack(side="right")

        # Date picker button
        self._date_picker = DatePickerButton(
            action_f, initial_date=self._selected_date,
            on_change=self._on_date_picked, bg=THEME["bg_card"])
        self._date_picker.pack(pady=(0, 8))

        # Action buttons row
        btn_row = tk.Frame(action_f, bg=THEME["bg_card"])
        btn_row.pack()

        btn_style = {"bd": 0, "cursor": "hand2",
                     "font": ("Segoe UI Semibold", 9),
                     "fg": "white", "padx": 14, "pady": 7}

        tk.Button(btn_row, text="🔄 Sync Day",
                  command=self._load_data,
                  bg=THEME["dark"],
                  activebackground="#334155", **btn_style).pack(
            side="left", padx=(0, 6))

        tk.Button(btn_row, text="📜 History",
                  command=self._show_history,
                  bg=THEME["secondary"],
                  activebackground="#4F46E5", **btn_style).pack(side="left")

        # Hidden date entry (used internally by _load_data and _save_record)
        self.date_ent = tk.Entry(action_f)
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 2: DENOMINATION TABLE
        # ══════════════════════════════════════════════════════════════════════
        table_card = tk.Frame(container, bg=THEME["bg_card"], padx=24, pady=20)
        table_card.pack(fill="x", padx=16, pady=8)
        table_card.config(highlightbackground=THEME["border"],
                          highlightthickness=1)

        self._section_header(table_card, "💵", "Denomination Counter",
                             "Opening (auto-fetched) vs Closing (your input)")

        col_configs = [
            ("Denomination",       14, "w"),
            ("Opening (Prev Day)", 14, "center"),
            ("Closing (Today)",    14, "center"),
            ("Difference",         12, "center"),
            ("Cash In (+)",        14, "center"),
            ("Cash Out (−)",       14, "center"),
        ]

        thead = tk.Frame(table_card, bg="#F0F4F8", pady=2)
        thead.pack(fill="x", pady=(0, 2))
        thead.columnconfigure(tuple(range(6)), weight=1)
        for ci, (txt, w, anc) in enumerate(col_configs):
            tk.Label(thead, text=txt,
                     font=("Segoe UI Semibold", 9),
                     bg="#F0F4F8", fg=THEME["text_muted"],
                     width=w, anchor=anc, pady=10).grid(
                row=0, column=ci, sticky="ew", padx=2)

        for ri, d in enumerate(DENOMS):
            stripe_bg = "#FAFBFC" if ri % 2 == 0 else THEME["bg_card"]
            row = tk.Frame(table_card, bg=stripe_bg)
            row.pack(fill="x")
            row.columnconfigure(tuple(range(6)), weight=1)

            badge_f = tk.Frame(row, bg=stripe_bg)
            badge_f.grid(row=0, column=0, sticky="ew", padx=2, pady=6)
            tk.Label(badge_f, text=f"  ₹{d}  ",
                     font=("Segoe UI Black", 11),
                     bg=THEME["dark"], fg="white",
                     pady=3, padx=8).pack(pady=4)

            tk.Label(row, textvariable=self.opening_vars[d],
                     font=("Segoe UI Semibold", 11),
                     bg=stripe_bg, fg=THEME["secondary"],
                     width=14).grid(row=0, column=1, sticky="ew", padx=2)

            cf = tk.Frame(row, bg=stripe_bg)
            cf.grid(row=0, column=2, sticky="ew", padx=2)
            entry_wrap, _ = self._styled_entry(
                cf, self.closing_vars[d], width=10,
                font=("Segoe UI Bold", 11))
            entry_wrap.pack(pady=4)
            self.closing_vars[d].trace_add("write",
                                           lambda *a: self._recalculate())

            dl = tk.Label(row, text="0",
                          font=("Segoe UI Semibold", 11),
                          bg=stripe_bg, fg=THEME["text_muted"], width=12)
            dl.grid(row=0, column=3, sticky="ew", padx=2)
            self.diff_labels[d] = dl

            ci_lbl = tk.Label(row, text="—",
                              font=("Segoe UI Bold", 11),
                              bg=stripe_bg, fg=THEME["success"], width=14)
            ci_lbl.grid(row=0, column=4, sticky="ew", padx=2)
            self.cash_in_labels[d] = ci_lbl

            co_lbl = tk.Label(row, text="—",
                              font=("Segoe UI Bold", 11),
                              bg=stripe_bg, fg=THEME["danger"], width=14)
            co_lbl.grid(row=0, column=5, sticky="ew", padx=2)
            self.cash_out_labels[d] = co_lbl

            tk.Frame(table_card, bg=THEME["border"], height=1).pack(fill="x")

        ft = tk.Frame(table_card, bg="#EEF2FF", pady=12)
        ft.pack(fill="x", pady=(4, 0))
        ft.columnconfigure(tuple(range(6)), weight=1)

        tk.Label(ft, text="", width=14,
                 bg="#EEF2FF").grid(row=0, column=0, sticky="ew")
        tk.Label(ft, text="", width=14,
                 bg="#EEF2FF").grid(row=0, column=1, sticky="ew")
        tk.Label(ft, text="", width=14,
                 bg="#EEF2FF").grid(row=0, column=2, sticky="ew")
        tk.Label(ft, text="TOTALS ➔",
                 font=("Segoe UI Black", 10),
                 bg="#EEF2FF", fg=THEME["text_main"],
                 width=12).grid(row=0, column=3, sticky="ew")

        self.sum_in_lbl = tk.Label(ft, text="₹0",
                                    font=("Segoe UI Black", 11),
                                    bg="#EEF2FF", fg=THEME["success"],
                                    width=14)
        self.sum_in_lbl.grid(row=0, column=4, sticky="ew")

        self.sum_out_lbl = tk.Label(ft, text="₹0",
                                     font=("Segoe UI Black", 11),
                                     bg="#EEF2FF", fg=THEME["danger"],
                                     width=14)
        self.sum_out_lbl.grid(row=0, column=5, sticky="ew")

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 3: LOWER AREA – Side by Side
        # ══════════════════════════════════════════════════════════════════════
        lower = tk.Frame(container, bg=THEME["bg_page"])
        lower.pack(fill="x", padx=16, pady=8)
        lower.columnconfigure(0, weight=1)
        lower.columnconfigure(1, weight=1)

        ic = tk.Frame(lower, bg=THEME["bg_card"], padx=24, pady=20)
        ic.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ic.config(highlightbackground=THEME["border"], highlightthickness=1)

        self._section_header(ic, "📦", "Operational Figures",
                             "Enter today's sales and payment info")

        field_defs = [
            ("💰 Total Daily Sales",          self.total_sales_var,    "#10B981"),
            ("💵 Cash Received (₹500 Notes)",  self.cash_received_var, "#F59E0B"),
            ("📱 UPI / GPay Amount",           self.upi_gpay_var,      "#6366F1"),
            ("🧾 Operational Expenses",        self.expenses_var,       "#EF4444"),
        ]

        for label_text, var, accent_color in field_defs:
            f = tk.Frame(ic, bg=THEME["bg_card"], pady=6)
            f.pack(fill="x")

            lbl_f = tk.Frame(f, bg=THEME["bg_card"])
            lbl_f.pack(side="left", fill="x", expand=True)
            tk.Label(lbl_f, text="●",
                     font=("Segoe UI", 8),
                     bg=THEME["bg_card"], fg=accent_color).pack(
                side="left", padx=(0, 8))
            tk.Label(lbl_f, text=label_text,
                     font=("Segoe UI Semibold", 10),
                     bg=THEME["bg_card"], fg=THEME["text_main"]).pack(
                side="left")

            ew, _ = self._styled_entry(f, var, width=14, justify="right",
                                       font=("Segoe UI Bold", 12))
            ew.pack(side="right")
            var.trace_add("write", lambda *a: self._recalculate())

        rc = tk.Frame(lower, bg=THEME["bg_card"], padx=24, pady=20)
        rc.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        rc.config(highlightbackground=THEME["border"], highlightthickness=1)

        self._section_header(rc, "📊", "Visualized Calculation",
                             "Step-by-step breakdown of today's result")

        calc_colors = [
            (self.total1_txt,   THEME["secondary"]),
            (self.total2_txt,   THEME["primary"]),
            (self.shortage_txt, "#7C3AED"),
            (self.final_txt,    THEME["dark"]),
        ]

        for var, color in calc_colors:
            line_f = tk.Frame(rc, bg="#F8FAFC", padx=14, pady=10, bd=0)
            line_f.pack(fill="x", pady=4)
            line_f.config(highlightbackground="#E2E8F0", highlightthickness=1)

            tk.Frame(line_f, bg=color, width=4).pack(
                side="left", fill="y", padx=(0, 10))

            tk.Label(line_f, textvariable=var,
                     font=("Consolas", 10, "bold"),
                     bg="#F8FAFC", fg=color,
                     anchor="w", justify="left").pack(fill="x")

        self.res_box = tk.Frame(rc, bg="#94A3B8", padx=24, pady=18)
        self.res_box.pack(fill="x", pady=(14, 0))

        res_inner = tk.Frame(self.res_box, bg="#94A3B8")
        res_inner.pack()
        tk.Label(res_inner, text="✦  FINALIZED RESULT  ✦",
                 font=("Segoe UI Black", 10, "bold"),
                 bg="#94A3B8", fg="white").pack(pady=(0, 4))
        self.res_val_lbl = tk.Label(res_inner, text="₹0.00",
                                     font=("Segoe UI Variable Display", 28,
                                           "bold"),
                                     bg="#94A3B8", fg="white")
        self.res_val_lbl.pack()

        # ══════════════════════════════════════════════════════════════════════
        # SECTION 4: SAVE BUTTON
        # ══════════════════════════════════════════════════════════════════════
        save_f = tk.Frame(container, bg=THEME["bg_page"], padx=16)
        save_f.pack(fill="x", pady=(8, 20))

        save_btn = tk.Button(
            save_f,
            text="💾   SAVE TODAY'S DATA  &  SYNC TO NEXT DAY",
            command=self._save_record,
            bg=THEME["primary"], fg="white",
            font=("Segoe UI Variable Display", 13, "bold"),
            bd=0, pady=16, cursor="hand2",
            activebackground=THEME["primary_dk"],
            activeforeground="white")
        save_btn.pack(fill="x")

        save_btn.bind("<Enter>",
                      lambda e: save_btn.config(bg=THEME["primary_dk"]))
        save_btn.bind("<Leave>",
                      lambda e: save_btn.config(bg=THEME["primary"]))

    # ── Canvas Handler ───────────────────────────────────────────────────────
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOGIC – COMPLETELY UNCHANGED BELOW THIS LINE
    # ═══════════════════════════════════════════════════════════════════════════

    def _safe_float(self, var):
        try: return float(str(var.get()).replace(",", ""))
        except: return 0.0

    def _safe_int(self, var):
        try: return int(str(var.get()))
        except: return 0

    def _recalculate(self):
        # 1. Table Math
        sum_in = 0.0
        sum_out = 0.0
        for d in DENOMS:
            opening = self.opening_vars[d].get()  # Yesterday
            closing = self._safe_int(self.closing_vars[d])  # Today
            diff = closing - opening
            equiv = diff * d

            cl = THEME["success"] if diff > 0 else (
                THEME["danger"] if diff < 0 else THEME["text_muted"])
            self.diff_labels[d].config(text=f"{diff:+,}", fg=cl)

            ci = equiv if equiv > 0 else 0
            co = abs(equiv) if equiv < 0 else 0
            self.cash_in_labels[d].config(
                text=f"₹{ci:,}" if ci > 0 else "—")
            self.cash_out_labels[d].config(
                text=f"₹{co:,}" if co > 0 else "—")

            sum_in += ci
            sum_out += co

        self.sum_in_lbl.config(text=f"₹{sum_in:,.0f}")
        self.sum_out_lbl.config(text=f"₹{sum_out:,.0f}")

        # 2. Formula Breakdown Text
        self._total1 = sum_in - sum_out
        self.total1_txt.set(
            f"Total 1 = (Cash In ₹{sum_in:,.0f} - Cash Out ₹{sum_out:,.0f})"
            f"\n        = ₹{self._total1:,.2f}")

        sales = self._safe_float(self.total_sales_var)
        cash_rec = self._safe_float(self.cash_received_var)  # 500s
        upi = self._safe_float(self.upi_gpay_var)
        expenses = self._safe_float(self.expenses_var)

        self._total2 = sales - (upi + cash_rec)
        self.total2_txt.set(
            f"Total 2 = (Sales ₹{sales:,.0f} - (GPay ₹{upi:,.0f}"
            f" + 500s ₹{cash_rec:,.0f}))"
            f"\n        = ₹{self._total2:,.2f}")

        self._shortage = self._total1 - self._total2
        self.shortage_txt.set(
            f"Shortage = (Total 1 ₹{self._total1:,.2f}"
            f" - Total 2 ₹{self._total2:,.2f})"
            f"\n           = ₹{self._shortage:,.2f}")

        self._finalized = self._shortage - expenses
        self.final_txt.set(
            f"Final    = (Shortage ₹{self._shortage:,.2f}"
            f" - Expenses ₹{expenses:,.2f})"
            f"\n           = ₹{self._finalized:,.2f}")

        self.res_val_lbl.config(text=f"₹{self._finalized:,.2f}")

        # 3. Dynamic Coloring
        color = THEME["success"] if self._finalized > 0 else (
            THEME["danger"] if self._finalized < 0 else "#64748B")
        self.res_box.config(bg=color)
        for w in self.res_box.winfo_children():
            w.config(bg=color)
            for ww in w.winfo_children():
                ww.config(bg=color)

    def _load_data(self):
        # Sync the hidden date_ent with the selected date
        self._selected_date = self._date_picker.selected_date
        self.date_ent.delete(0, "end")
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))

        date_str = self.date_ent.get().strip()
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT closing_10, closing_20, closing_50, closing_100,"
            " closing_200 FROM cashier_records WHERE date < ?"
            " ORDER BY date DESC LIMIT 1", (date_str,))
        prev = cur.fetchone()

        cur.execute("SELECT * FROM cashier_records WHERE date=?",
                    (date_str,))
        today = cur.fetchone()
        conn.close()

        if prev:
            for d in DENOMS:
                self.opening_vars[d].set(prev[f"closing_{d}"])
        else:
            for d in DENOMS:
                self.opening_vars[d].set(0)

        if today:
            for d in DENOMS:
                self.closing_vars[d].set(str(today[f"closing_{d}"]))
            self.total_sales_var.set(str(today["total_sales"]))
            self.cash_received_var.set(str(today["cash_received_500"]))
            self.upi_gpay_var.set(str(today["upi_gpay"]))
            self.expenses_var.set(str(today["expenses"]))
        else:
            for d in DENOMS:
                self.closing_vars[d].set("0")
            self.total_sales_var.set("0")
            self.cash_received_var.set("0")
            self.upi_gpay_var.set("0")
            self.expenses_var.set("0")

        self._recalculate()

    def _save_record(self):
        self._selected_date = self._date_picker.selected_date
        self.date_ent.delete(0, "end")
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))

        date_str = self.date_ent.get().strip()
        self._recalculate()

        data = {
            "date": date_str,
            "total_sales": self._safe_float(self.total_sales_var),
            "cash_received_500": self._safe_float(self.cash_received_var),
            "upi_gpay": self._safe_float(self.upi_gpay_var),
            "expenses": self._safe_float(self.expenses_var),
            "total1": self._total1,
            "total2": self._total2,
            "shortage": self._shortage,
            "finalized_amount": self._finalized
        }
        for d in DENOMS:
            data[f"opening_{d}"] = self.opening_vars[d].get()
            data[f"closing_{d}"] = self._safe_int(self.closing_vars[d])

        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cols = ", ".join(data.keys())
            places = ", ".join(["?"] * len(data))
            upd = ", ".join([f"{k}=excluded.{k}"
                             for k in data.keys() if k != "date"])
            cur.execute(
                f"INSERT INTO cashier_records ({cols}) VALUES ({places})"
                f" ON CONFLICT(date) DO UPDATE SET {upd}",
                list(data.values()))
            conn.commit()
            messagebox.showinfo(
                "Saved ✔",
                f"Record for {date_str} saved!\n"
                "Counts will automatically sync when you load the next date.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def _show_history(self):
        win = tk.Toplevel(self)
        win.title("Historical Records")
        win.geometry("1100x600")
        win.configure(bg=THEME["bg_page"])

        top = tk.Frame(win, bg=THEME["bg_card"], padx=20, pady=15)
        top.pack(fill="x")

        tk.Label(top, text="From:", bg=THEME["bg_card"]).pack(side="left")
        s = tk.Entry(top, width=12)
        s.pack(side="left", padx=5)
        s.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))

        tk.Label(top, text="To:", bg=THEME["bg_card"]).pack(
            side="left", padx=10)
        e = tk.Entry(top, width=12)
        e.pack(side="left", padx=5)
        e.insert(0, datetime.now().strftime("%Y-%m-%d"))

        def load():
            for r in tree.get_children():
                tree.delete(r)
            conn = self.db.get_connection()
            rows = conn.execute(
                "SELECT * FROM cashier_records WHERE date BETWEEN ? AND ?"
                " ORDER BY date DESC",
                (s.get(), e.get())).fetchall()
            conn.close()
            for r in rows:
                tree.insert("", "end", values=(
                    r["date"],
                    f"₹{r['total_sales']:,}",
                    f"₹{r['shortage']:,}",
                    f"₹{r['finalized_amount']:,}"))

        tk.Button(top, text="🔍 Look Up", command=load,
                  bg=THEME["dark"], fg="white", bd=0,
                  padx=20, pady=7).pack(side="left", padx=20)

        cols = ("Date", "Total Sales", "Shortage", "Final Amount")
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=200, anchor="center")
        tree.pack(fill="both", expand=True, padx=25, pady=25)

        def select(evt):
            sel = tree.selection()
            if not sel:
                return
            picked_str = tree.item(sel[0])["values"][0]
            picked = datetime.strptime(str(picked_str), "%Y-%m-%d").date()
            self._date_picker.set_date(picked)
            self._selected_date = picked
            self._load_data()
            win.destroy()

        tree.bind("<Double-1>", select)
        load()

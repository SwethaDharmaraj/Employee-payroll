import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

from views.shared_widgets import DatePickerButton, enable_smooth_scroll

THEME = {
    "primary": "#0F766E",
    "primary_dk": "#115E59",
    "secondary": "#0EA5E9",
    "bg_page": "#F3F7F9",
    "bg_card": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "text_main": "#102A43",
    "text_muted": "#64748B",
    "border": "#D8E3EC",
    "success": "#16A34A",
    "dark": "#0F172A",
    "warning": "#D97706",
    "danger": "#DC2626",
}


class MoneyView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db
        self._selected_date = datetime.now().date()
        self._all_entries = []

        self.total_sales_var = tk.StringVar(value="0")
        self.gpay_sales_var = tk.StringVar(value="0")
        self.taken_500_var = tk.StringVar(value="0")
        self.expenses_var = tk.StringVar(value="0")
        self.actual_cash_var = tk.StringVar(value="0")
        self.opening_cash_var = tk.StringVar(value="0")

        self.cash_sales_txt = tk.StringVar(value="Rs 0.00")
        self.expected_cash_txt = tk.StringVar(value="Rs 0.00")
        self.difference_txt = tk.StringVar(value="Rs 0.00")
        self.next_opening_txt = tk.StringVar(value="Rs 0.00")
        self.status_txt = tk.StringVar(value="No loss or gain")

        self.calc_line1 = tk.StringVar(value="cash_sales = total_sales - gpay_sales = Rs 0.00")
        self.calc_line2 = tk.StringVar(value="expected_cash = opening_cash + cash_sales - taken_500 - expenses = Rs 0.00")
        self.calc_line3 = tk.StringVar(value="difference = actual_cash - expected_cash = Rs 0.00")
        self.calc_line4 = tk.StringVar(value="next_opening_cash = actual_cash = Rs 0.00")

        self._build_ui()
        self._load_data()

    def _styled_entry(self, parent, textvariable, width=16, justify="right", font=("Segoe UI", 12), track=True):
        wrapper = tk.Frame(parent, bg=THEME["border"], padx=2, pady=2)
        entry = tk.Entry(
            wrapper,
            textvariable=textvariable,
            font=font,
            width=width,
            justify=justify,
            bd=0,
            bg=THEME["surface_alt"],
            fg=THEME["text_main"],
            insertbackground=THEME["primary"],
        )
        entry.pack(ipady=8, padx=1, pady=1, fill="x")

        def _focus_in(_event):
            wrapper.config(bg=THEME["primary"])
            entry.config(bg="white")
            if entry.cget("state") != "readonly":
                entry.after(1, lambda: (entry.select_range(0, "end"), entry.icursor("end")))

        def _focus_out(_event):
            wrapper.config(bg=THEME["border"])
            entry.config(bg=THEME["surface_alt"])

        entry.bind("<FocusIn>", _focus_in)
        entry.bind("<FocusOut>", _focus_out)
        if track:
            self._all_entries.append(entry)
        entry.bind("<Return>", self._focus_next_entry)
        entry.bind("<KP_Enter>", self._focus_next_entry)
        return wrapper

    def _focus_next_entry(self, event):
        widget = event.widget
        if widget in self._all_entries:
            idx = self._all_entries.index(widget)
            nxt = self._all_entries[(idx + 1) % len(self._all_entries)]
            nxt.focus_set()
            nxt.select_range(0, "end")
        return "break"

    def _safe_float(self, var):
        try:
            return float(str(var.get()).replace(",", "").strip())
        except Exception:
            return 0.0

    def _section_title(self, parent, title, subtitle):
        wrap = tk.Frame(parent, bg=THEME["bg_card"])
        wrap.pack(fill="x", pady=(0, 12))
        tk.Label(
            wrap,
            text=title,
            font=("Segoe UI Variable Display", 15, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_main"],
        ).pack(anchor="w")
        tk.Label(
            wrap,
            text=subtitle,
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(3, 0))

    def _build_ui(self):
        self.canvas = tk.Canvas(self, bg=THEME["bg_page"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME["bg_page"])
        self.scrollable_frame.bind(
            "<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        enable_smooth_scroll(self.canvas)

        container = self.scrollable_frame

        header = tk.Frame(container, bg=THEME["bg_card"], padx=26, pady=20)
        header.pack(fill="x", padx=16, pady=(14, 8))
        header.config(highlightbackground=THEME["border"], highlightthickness=1)

        title_side = tk.Frame(header, bg=THEME["bg_card"])
        title_side.pack(side="left")
        tk.Label(
            title_side,
            text="Vault & Cash Tracker",
            font=("Segoe UI Variable Display", 18, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_main"],
        ).pack(anchor="w")
        tk.Label(
            title_side,
            text="Daily cash flow based only on opening cash, sales, 500s taken, expenses, and actual cash.",
            font=("Segoe UI", 9),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(4, 0))

        action_side = tk.Frame(header, bg=THEME["bg_card"])
        action_side.pack(side="right")
        self._date_picker = DatePickerButton(
            action_side,
            initial_date=self._selected_date,
            on_change=self._on_date_picked,
            bg=THEME["bg_card"],
        )
        self._date_picker.pack(pady=(0, 8))

        btn_row = tk.Frame(action_side, bg=THEME["bg_card"])
        btn_row.pack()
        tk.Button(
            btn_row,
            text="Sync Day",
            command=self._load_data,
            bg=THEME["dark"],
            fg="white",
            activebackground="#334155",
            activeforeground="white",
            font=("Segoe UI Semibold", 9),
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            btn_row,
            text="History",
            command=self._show_history,
            bg=THEME["secondary"],
            fg="white",
            activebackground="#0284C7",
            activeforeground="white",
            font=("Segoe UI Semibold", 9),
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side="left")

        self.date_ent = tk.Entry(action_side)
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))

        top = tk.Frame(container, bg=THEME["bg_page"])
        top.pack(fill="x", padx=16, pady=8)
        top.columnconfigure(0, weight=5)
        top.columnconfigure(1, weight=4)

        inputs_card = tk.Frame(top, bg=THEME["bg_card"], padx=24, pady=22)
        inputs_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        inputs_card.config(highlightbackground=THEME["border"], highlightthickness=1)
        self._section_title(inputs_card, "Daily Inputs", "Enter the six values for the selected day.")

        fields = [
            ("Opening Cash", self.opening_cash_var, True),
            ("Total Sales", self.total_sales_var, False),
            ("GPay Sales", self.gpay_sales_var, False),
            ("Taken 500", self.taken_500_var, False),
            ("Expenses", self.expenses_var, False),
            ("Actual Cash", self.actual_cash_var, False),
        ]

        for label_text, var, readonly in fields:
            row = tk.Frame(inputs_card, bg=THEME["bg_card"], pady=6)
            row.pack(fill="x")
            tk.Label(
                row,
                text=label_text,
                font=("Segoe UI Semibold", 10),
                bg=THEME["bg_card"],
                fg=THEME["text_main"],
            ).pack(side="left")
            wrap = self._styled_entry(row, var, track=not readonly)
            wrap.pack(side="right")
            if readonly:
                entry = wrap.winfo_children()[0]
                entry.config(state="readonly", readonlybackground="#EDF2F7", fg=THEME["text_main"])
            else:
                var.trace_add("write", lambda *_a: self._recalculate())

        note = tk.Label(
            inputs_card,
            text="Opening cash is auto-filled from the previous day's actual cash.",
            font=("Segoe UI", 9, "italic"),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        )
        note.pack(anchor="w", pady=(10, 0))

        outputs_card = tk.Frame(top, bg=THEME["bg_card"], padx=24, pady=22)
        outputs_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        outputs_card.config(highlightbackground=THEME["border"], highlightthickness=1)
        self._section_title(outputs_card, "Calculated Outputs", "These values follow your exact formula.")

        self.output_value_labels = {}
        outputs = [
            ("Cash Sales", self.cash_sales_txt, THEME["success"]),
            ("Expected Cash", self.expected_cash_txt, THEME["secondary"]),
            ("Difference", self.difference_txt, THEME["warning"]),
            ("Next Day Opening", self.next_opening_txt, THEME["dark"]),
        ]
        for label_text, var, color in outputs:
            box = tk.Frame(outputs_card, bg=THEME["surface_alt"], padx=16, pady=14)
            box.pack(fill="x", pady=(0, 10))
            box.config(highlightbackground=THEME["border"], highlightthickness=1)
            tk.Label(
                box,
                text=label_text,
                font=("Segoe UI Semibold", 10),
                bg=THEME["surface_alt"],
                fg=THEME["text_muted"],
            ).pack(anchor="w")
            value_label = tk.Label(
                box,
                textvariable=var,
                font=("Segoe UI Variable Display", 20, "bold"),
                bg=THEME["surface_alt"],
                fg=color,
            )
            value_label.pack(anchor="w", pady=(6, 0))
            self.output_value_labels[label_text] = value_label

        self.result_box = tk.Frame(outputs_card, bg="#94A3B8", padx=18, pady=16)
        self.result_box.pack(fill="x", pady=(6, 0))
        tk.Label(
            self.result_box,
            text="Difference Interpretation",
            font=("Segoe UI Black", 10),
            bg="#94A3B8",
            fg="white",
        ).pack()
        self.status_label = tk.Label(
            self.result_box,
            textvariable=self.status_txt,
            font=("Segoe UI Variable Display", 20, "bold"),
            bg="#94A3B8",
            fg="white",
        )
        self.status_label.pack(pady=(4, 0))

        calc_card = tk.Frame(container, bg=THEME["bg_card"], padx=24, pady=22)
        calc_card.pack(fill="x", padx=16, pady=8)
        calc_card.config(highlightbackground=THEME["border"], highlightthickness=1)
        self._section_title(calc_card, "Calculation Flow", "The page follows the exact sequence you specified.")

        for var, color in (
            (self.calc_line1, THEME["success"]),
            (self.calc_line2, THEME["secondary"]),
            (self.calc_line3, THEME["warning"]),
            (self.calc_line4, THEME["dark"]),
        ):
            line = tk.Frame(calc_card, bg=THEME["surface_alt"], padx=14, pady=12)
            line.pack(fill="x", pady=4)
            line.config(highlightbackground=THEME["border"], highlightthickness=1)
            tk.Frame(line, bg=color, width=4).pack(side="left", fill="y", padx=(0, 10))
            tk.Label(
                line,
                textvariable=var,
                font=("Consolas", 10, "bold"),
                bg=THEME["surface_alt"],
                fg=color,
                anchor="w",
                justify="left",
            ).pack(fill="x")

        save_f = tk.Frame(container, bg=THEME["bg_page"], padx=16)
        save_f.pack(fill="x", pady=(8, 20))
        save_btn = tk.Button(
            save_f,
            text="SAVE DAILY CASH RECORD",
            command=self._save_record,
            bg=THEME["primary"],
            fg="white",
            activebackground=THEME["primary_dk"],
            activeforeground="white",
            font=("Segoe UI Variable Display", 13, "bold"),
            bd=0,
            pady=16,
            cursor="hand2",
        )
        save_btn.pack(fill="x")

    def _on_date_picked(self, picked_date):
        self._selected_date = picked_date
        self._load_data()

    def _recalculate(self):
        opening_cash = self._safe_float(self.opening_cash_var)
        total_sales = self._safe_float(self.total_sales_var)
        gpay_sales = self._safe_float(self.gpay_sales_var)
        taken_500 = self._safe_float(self.taken_500_var)
        expenses = self._safe_float(self.expenses_var)
        actual_cash = self._safe_float(self.actual_cash_var)

        cash_sales = total_sales - gpay_sales
        expected_cash = opening_cash + cash_sales - taken_500 - expenses
        difference = actual_cash - expected_cash
        next_opening_cash = actual_cash

        self.cash_sales_txt.set(f"Rs {cash_sales:,.2f}")
        self.expected_cash_txt.set(f"Rs {expected_cash:,.2f}")
        self.difference_txt.set(f"Rs {difference:,.2f}")
        self.next_opening_txt.set(f"Rs {next_opening_cash:,.2f}")

        self.calc_line1.set(
            f"cash_sales = total_sales ({total_sales:,.2f}) - gpay_sales ({gpay_sales:,.2f}) = Rs {cash_sales:,.2f}"
        )
        self.calc_line2.set(
            f"expected_cash = opening_cash ({opening_cash:,.2f}) + cash_sales ({cash_sales:,.2f}) - taken_500 ({taken_500:,.2f}) - expenses ({expenses:,.2f}) = Rs {expected_cash:,.2f}"
        )
        self.calc_line3.set(
            f"difference = actual_cash ({actual_cash:,.2f}) - expected_cash ({expected_cash:,.2f}) = Rs {difference:,.2f}"
        )
        self.calc_line4.set(
            f"next_opening_cash = actual_cash ({actual_cash:,.2f}) = Rs {next_opening_cash:,.2f}"
        )

        if difference > 0:
            status_text = "Extra Cash"
            color = THEME["success"]
        elif difference < 0:
            status_text = "Missing Cash"
            color = THEME["danger"]
        else:
            status_text = "No Loss / Gain"
            color = "#64748B"

        self.status_txt.set(status_text)
        self.result_box.config(bg=color)
        for child in self.result_box.winfo_children():
            child.config(bg=color)

        self.output_value_labels["Difference"].config(fg=color)
        self.output_value_labels["Cash Sales"].config(fg=THEME["success"])
        self.output_value_labels["Expected Cash"].config(fg=THEME["secondary"])
        self.output_value_labels["Next Day Opening"].config(fg=THEME["dark"])

    def _load_data(self):
        self._selected_date = self._date_picker.selected_date
        self.date_ent.delete(0, "end")
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))
        date_str = self.date_ent.get().strip()

        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT actual_cash, finalized_amount FROM cashier_records WHERE date < ? ORDER BY date DESC LIMIT 1",
            (date_str,),
        )
        prev = cur.fetchone()

        cur.execute("SELECT * FROM cashier_records WHERE date=?", (date_str,))
        today = cur.fetchone()
        conn.close()

        previous_actual = 0.0
        if prev:
            previous_actual = prev["actual_cash"] if "actual_cash" in prev.keys() else prev["finalized_amount"]
            previous_actual = previous_actual or 0.0

        if today:
            opening_val = today["opening_cash"] if "opening_cash" in today.keys() else previous_actual
            self.opening_cash_var.set(str(opening_val or 0))
            self.total_sales_var.set(str(today["total_sales"] or 0))
            gpay = today["gpay_sales"] if "gpay_sales" in today.keys() else today["upi_gpay"]
            taken_500 = today["taken_500"] if "taken_500" in today.keys() else today["cash_received_500"]
            actual_cash = today["actual_cash"] if "actual_cash" in today.keys() else today["finalized_amount"]
            self.gpay_sales_var.set(str(gpay or 0))
            self.taken_500_var.set(str(taken_500 or 0))
            self.expenses_var.set(str(today["expenses"] or 0))
            self.actual_cash_var.set(str(actual_cash or 0))
        else:
            self.opening_cash_var.set(str(previous_actual or 0))
            self.total_sales_var.set("0")
            self.gpay_sales_var.set("0")
            self.taken_500_var.set("0")
            self.expenses_var.set("0")
            self.actual_cash_var.set("0")

        self._recalculate()

    def _save_record(self):
        self._selected_date = self._date_picker.selected_date
        self.date_ent.delete(0, "end")
        self.date_ent.insert(0, self._selected_date.strftime("%Y-%m-%d"))
        date_str = self.date_ent.get().strip()

        self._recalculate()

        opening_cash = self._safe_float(self.opening_cash_var)
        total_sales = self._safe_float(self.total_sales_var)
        gpay_sales = self._safe_float(self.gpay_sales_var)
        taken_500 = self._safe_float(self.taken_500_var)
        expenses = self._safe_float(self.expenses_var)
        actual_cash = self._safe_float(self.actual_cash_var)
        cash_sales = total_sales - gpay_sales
        expected_cash = opening_cash + cash_sales - taken_500 - expenses
        difference = actual_cash - expected_cash
        next_opening_cash = actual_cash

        data = {
            "date": date_str,
            "opening_cash": opening_cash,
            "total_sales": total_sales,
            "gpay_sales": gpay_sales,
            "taken_500": taken_500,
            "expenses": expenses,
            "actual_cash": actual_cash,
            "cash_sales": cash_sales,
            "expected_cash": expected_cash,
            "difference": difference,
            "next_opening_cash": next_opening_cash,
            "upi_gpay": gpay_sales,
            "cash_received_500": taken_500,
            "total1": cash_sales,
            "total2": expected_cash,
            "shortage": difference,
            "finalized_amount": actual_cash,
        }

        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cols = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            updates = ", ".join([f"{k}=excluded.{k}" for k in data.keys() if k != "date"])
            cur.execute(
                f"INSERT INTO cashier_records ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT(date) DO UPDATE SET {updates}",
                list(data.values()),
            )
            conn.commit()
            messagebox.showinfo(
                "Saved",
                f"Record for {date_str} saved.\nNext day opening cash will now follow this day's actual cash.",
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def _show_history(self):
        win = tk.Toplevel(self)
        win.title("Cash Tracking History")
        win.geometry("1180x620")
        win.configure(bg=THEME["bg_page"])

        top = tk.Frame(win, bg=THEME["bg_card"], padx=20, pady=15)
        top.pack(fill="x")

        tk.Label(top, text="From:", bg=THEME["bg_card"]).pack(side="left")
        start = tk.Entry(top, width=12)
        start.pack(side="left", padx=5)
        start.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))

        tk.Label(top, text="To:", bg=THEME["bg_card"]).pack(side="left", padx=10)
        end = tk.Entry(top, width=12)
        end.pack(side="left", padx=5)
        end.insert(0, datetime.now().strftime("%Y-%m-%d"))

        cols = (
            "Date",
            "Opening Cash",
            "Cash Sales",
            "Expected Cash",
            "Actual Cash",
            "Difference",
        )
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=180, anchor="center")
        tree.pack(fill="both", expand=True, padx=25, pady=25)

        def load():
            for row in tree.get_children():
                tree.delete(row)
            conn = self.db.get_connection()
            rows = conn.execute(
                "SELECT date, opening_cash, cash_sales, expected_cash, actual_cash, difference "
                "FROM cashier_records WHERE date BETWEEN ? AND ? ORDER BY date DESC",
                (start.get(), end.get()),
            ).fetchall()
            conn.close()
            for row in rows:
                tree.insert(
                    "",
                    "end",
                    values=(
                        row["date"],
                        f"Rs {row['opening_cash']:,.2f}",
                        f"Rs {row['cash_sales']:,.2f}",
                        f"Rs {row['expected_cash']:,.2f}",
                        f"Rs {row['actual_cash']:,.2f}",
                        f"Rs {row['difference']:,.2f}",
                    ),
                )

        tk.Button(
            top,
            text="Look Up",
            command=load,
            bg=THEME["dark"],
            fg="white",
            bd=0,
            padx=20,
            pady=7,
        ).pack(side="left", padx=20)

        def select(_event):
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

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from views.shared_widgets import (
    DatePickerButton, MonthYearPickerButton
)

THEME = {
    "primary":    "#1D4ED8",
    "primary_dk": "#1E40AF",
    "bg_page":    "#F1F5F9",
    "bg_card":    "#FFFFFF",
    "text_main":  "#0F172A",
    "text_muted": "#475569",
    "border":     "#CBD5E1",
    "success":    "#10B981",
    "danger":     "#EF4444",
    "dark":       "#0F172A",
}

class ExpenseView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db
        self._editing_id = None
        self._build_ui()
        self._refresh_emp_list()
        self._load_table()

    def _build_ui(self):
        # LEFT – form
        left = tk.Frame(self, bg=THEME["bg_page"], width=420)
        left.pack(side="left", fill="y", padx=(0,30))
        left.pack_propagate(False)

        card = tk.Frame(left, bg=THEME["bg_card"], padx=35, pady=28)
        card.pack(fill="both", expand=True)
        card.config(highlightbackground=THEME["border"], highlightthickness=1)

        self.form_title = tk.Label(card, text="💸  Add Expense",
                                    font=("Segoe UI Variable Display", 16, "bold"),
                                    bg=THEME["bg_card"], fg=THEME["text_main"])
        self.form_title.pack(anchor="w", pady=(0,18))

        def field(lbl, default=""):
            tk.Label(card, text=lbl, font=("Segoe UI Semibold", 8),
                     bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w", pady=(8,0))
            f = tk.Frame(card, bg="#F8FAFC", pady=1)
            f.pack(fill="x", pady=(3,2))
            e = tk.Entry(f, font=("Segoe UI", 11), bd=0, bg="#F8FAFC")
            e.pack(fill="x", padx=10, ipady=7)
            if default:
                e.insert(0, default)
            tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x", pady=(0,6))
            return e

        tk.Label(card, text="EMPLOYEE", font=("Segoe UI Semibold", 8),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w", pady=(8,0))
        f0 = tk.Frame(card, bg="#F8FAFC")
        f0.pack(fill="x", pady=(3,2))
        self.emp_cb = ttk.Combobox(f0, state="readonly", font=("Segoe UI", 10))
        self.emp_cb.pack(fill="x", padx=10, ipady=4)
        tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x", pady=(0,6))

        # Date – Calendar Picker
        tk.Label(card, text="DATE", font=("Segoe UI Semibold", 8),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w", pady=(8,0))
        self._date_picker = DatePickerButton(
            card, initial_date=datetime.now().date(), bg=THEME["bg_card"])
        self._date_picker.pack(fill="x", pady=(3, 2))
        tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x", pady=(0,6))

        self.amount_ent = field("AMOUNT (₹)")
        self.reason_ent = field("REASON / DESCRIPTION")

        # Buttons
        tk.Button(card, text="✔  SAVE EXPENSE",
                  command=self._save_expense,
                  bg=THEME["primary"], fg="white",
                  font=("Segoe UI Variable Text", 10, "bold"),
                  bd=0, pady=12, cursor="hand2",
                  activebackground=THEME["primary_dk"]).pack(fill="x", pady=(10,4))

        row2 = tk.Frame(card, bg=THEME["bg_card"])
        row2.pack(fill="x")
        tk.Button(row2, text="✖  Clear", command=self._clear_form,
                  bg="#F8FAFC", fg=THEME["text_muted"],
                  font=("Segoe UI", 9), bd=0, pady=8,
                  cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0,4))
        tk.Button(row2, text="🗑  Delete", command=self._delete_expense,
                  bg=THEME["danger"], fg="white",
                  font=("Segoe UI", 9), bd=0, pady=8,
                  cursor="hand2").pack(side="left", fill="x", expand=True)

        # Monthly total widget
        self.total_lbl = tk.Label(card, text="",
                                   font=("Segoe UI Variable Display", 13, "bold"),
                                   bg=THEME["bg_card"], fg=THEME["primary"])
        self.total_lbl.pack(pady=(16,0))

        # RIGHT – table
        right = tk.Frame(self, bg=THEME["bg_card"])
        right.pack(side="right", fill="both", expand=True)
        right.config(highlightbackground=THEME["border"], highlightthickness=1)

        # Filter bar
        fbar = tk.Frame(right, bg="#F8FAFC", pady=12, padx=20)
        fbar.pack(side="top", fill="x")
        tk.Label(fbar, text="Filter", font=("Segoe UI Semibold", 9),
                 bg="#F8FAFC", fg=THEME["text_muted"]).pack(side="left")

        self.f_emp_cb = ttk.Combobox(fbar, width=25, state="readonly")
        self.f_emp_cb.pack(side="left", padx=8)

        # Month-Year filter picker
        self._filter_my = MonthYearPickerButton(
            fbar,
            initial_year=datetime.now().year,
            initial_month=datetime.now().month,
            on_change=lambda y, m: self._load_table(),
            bg="#F8FAFC")
        self._filter_my.pack(side="left", padx=4)

        tk.Button(fbar, text="🔍 Filter", command=self._load_table,
                  bg=THEME["dark"], fg="white",
                  font=("Segoe UI", 9, "bold"), bd=0,
                  padx=14, pady=5, cursor="hand2").pack(side="left", padx=10)

        self.total_right_lbl = tk.Label(fbar, text="",
                                         font=("Segoe UI Semibold", 10),
                                         bg="#F8FAFC", fg=THEME["danger"])
        self.total_right_lbl.pack(side="right")

        # Table
        cols = ("ID", "Employee", "Date", "Amount (₹)", "Reason")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        widths    = [50, 160, 110, 120, 250]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        self.tree.column("ID", anchor="center")
        self.tree.column("Amount (₹)", anchor="e")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        sc = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        sc.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sc.set)

        # Enter-key navigation
        self._all_entries = [self.emp_cb, self.amount_ent, self.reason_ent]
        def _focus_next(e):
            w = e.widget
            if w in self._all_entries:
                idx = self._all_entries.index(w)
                nxt = self._all_entries[(idx + 1) % len(self._all_entries)]
                nxt.focus_set()
                try: nxt.select_range(0, "end")
                except: pass
            return "break"
        for w in self._all_entries:
            w.bind("<Return>", _focus_next)
            w.bind("<KP_Enter>", _focus_next)

    def _refresh_emp_list(self):
        conn = self.db.get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT emp_id, name FROM employees ORDER BY name")
        self._emps = cur.fetchall()
        conn.close()
        items = [f"{r['emp_id']} – {r['name']}" for r in self._emps]
        self.emp_cb["values"] = items
        self.f_emp_cb["values"] = ["ALL EMPLOYEES"] + items
        self.f_emp_cb.set("ALL EMPLOYEES")

    def _save_expense(self):
        emp_sel = self.emp_cb.get()
        if not emp_sel:
            messagebox.showwarning("Select", "Please select an employee.")
            return
        emp_id = int(emp_sel.split(" – ")[0])
        date   = self._date_picker.get_date_str()
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Date Error", "Use YYYY-MM-DD format.")
            return
        try:
            amount = float(self.amount_ent.get())
        except ValueError:
            messagebox.showerror("Amount Error", "Amount must be a number.")
            return
        reason    = self.reason_ent.get().strip()
        month_yr  = datetime.strptime(date, "%Y-%m-%d").strftime("%m-%Y")

        conn = self.db.get_connection()
        if self._editing_id:
            conn.execute(
                "UPDATE expenses SET emp_id=?, date=?, reason=?, amount=?, month_year=? WHERE id=?",
                (emp_id, date, reason, amount, month_yr, self._editing_id)
            )
        else:
            conn.execute(
                "INSERT INTO expenses (emp_id, date, reason, amount, month_year) VALUES (?,?,?,?,?)",
                (emp_id, date, reason, amount, month_yr)
            )
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", f"Expense of ₹{amount:,.2f} saved.")
        self._clear_form()
        self._load_table()

    def _delete_expense(self):
        if not self._editing_id:
            messagebox.showwarning("Select", "Click a row first.")
            return
        if messagebox.askyesno("Delete", "Delete this expense?"):
            conn = self.db.get_connection()
            conn.execute("DELETE FROM expenses WHERE id=?", (self._editing_id,))
            conn.commit()
            conn.close()
            self._clear_form()
            self._load_table()

    def _clear_form(self):
        self._editing_id = None
        self.form_title.config(text="💸  Add Expense")
        self.emp_cb.set("")
        self._date_picker.set_date(datetime.now().date())
        self.amount_ent.delete(0,"end")
        self.reason_ent.delete(0,"end")

    def _load_table(self, *args):
        for row in self.tree.get_children():
            self.tree.delete(row)
        year   = self._filter_my.get_year()
        month  = self._filter_my.get_month()
        my_str = f"{month}-{year}"
        emp_f  = self.f_emp_cb.get()

        conn = self.db.get_connection()
        cur  = conn.cursor()

        if emp_f == "ALL EMPLOYEES" or not emp_f:
            cur.execute(
                '''SELECT ex.id, e.name, ex.date, ex.amount, ex.reason
                   FROM expenses ex JOIN employees e ON ex.emp_id=e.emp_id
                   WHERE ex.month_year=? ORDER BY ex.date DESC''',
                (my_str,)
            )
        else:
            eid = int(emp_f.split(" – ")[0])
            cur.execute(
                '''SELECT ex.id, e.name, ex.date, ex.amount, ex.reason
                   FROM expenses ex JOIN employees e ON ex.emp_id=e.emp_id
                   WHERE ex.emp_id=? AND ex.month_year=? ORDER BY ex.date DESC''',
                (eid, my_str)
            )

        rows  = cur.fetchall()
        total = 0.0
        for r in rows:
            total += r["amount"]
            self.tree.insert("", "end", values=(
                r["id"], r["name"], r["date"], f"₹{r['amount']:,.2f}", r["reason"] or "-"
            ))
        conn.close()
        self.total_right_lbl.config(text=f"Total: ₹{total:,.2f} | {len(rows)} records")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0])["values"]
        eid_from_table = vals[0]
        name = vals[1]
        date = vals[2]
        amount = str(vals[3]).replace("₹","").replace(",","").strip()
        reason = vals[4]

        self._editing_id = eid_from_table
        self.form_title.config(text=f"✏  Editing Expense #{eid_from_table}")

        # Set employee combobox
        for item in self.emp_cb["values"]:
            if name in item:
                self.emp_cb.set(item)
                break

        # Set date picker
        try:
            d = datetime.strptime(str(date), "%Y-%m-%d").date()
            self._date_picker.set_date(d)
        except:
            pass

        self.amount_ent.delete(0,"end")
        self.amount_ent.insert(0, amount)
        self.reason_ent.delete(0,"end")
        if reason != "-":
            self.reason_ent.insert(0, reason)

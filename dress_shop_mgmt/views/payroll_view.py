import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from views.shared_widgets import MonthYearPickerButton

THEME = {
    "primary":    "#1D4ED8",
    "primary_dk": "#1E40AF",
    "bg_page":    "#F1F5F9",
    "bg_card":    "#FFFFFF",
    "text_main":  "#0F172A",
    "text_muted": "#475569",
    "border":     "#CBD5E1",
    "success":    "#10B981",
    "dark":       "#0F172A",
}

class PayrollView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        # ─ CONTROL BAR ─
        ctrl = tk.Frame(self, bg=THEME["bg_card"], padx=30, pady=20)
        ctrl.pack(side="top", fill="x", pady=(0,20))
        ctrl.config(highlightbackground=THEME["border"], highlightthickness=1)

        tk.Label(ctrl, text="💰  Payroll Engine",
                 font=("Segoe UI Variable Display", 16, "bold"),
                 bg=THEME["bg_card"], fg=THEME["text_main"]).pack(side="left", padx=(0,30))

        # Month-Year Picker
        sel = tk.Frame(ctrl, bg=THEME["bg_card"])
        sel.pack(side="left")

        tk.Label(sel, text="PERIOD",
                 font=("Segoe UI Semibold", 8),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(anchor="w")

        self._my_picker = MonthYearPickerButton(
            sel,
            initial_year=datetime.now().year,
            initial_month=datetime.now().month,
            on_change=lambda y, m: self._load_table(),
            bg=THEME["bg_card"])
        self._my_picker.pack(pady=(3, 0))

        tk.Button(ctrl, text="⚙  CALCULATE ALL PAYROLL",
                  command=self._calculate_all,
                  bg=THEME["primary"], fg="white",
                  font=("Segoe UI Variable Text", 10, "bold"),
                  bd=0, padx=24, pady=10, cursor="hand2",
                  activebackground=THEME["primary_dk"]).pack(side="right", padx=(0,10))

        tk.Button(ctrl, text="🔍  View Month",
                  command=self._load_table,
                  bg=THEME["dark"], fg="white",
                  font=("Segoe UI", 9, "bold"),
                  bd=0, padx=18, pady=10, cursor="hand2").pack(side="right", padx=(0,6))

        # ─ FORMULA INFO ─
        info = tk.Frame(self, bg="#FFF7ED", padx=20, pady=10)
        info.pack(fill="x", pady=(0,16))
        tk.Label(info,
                 text="📐 Formula: Net Salary = (Present + Paid Leave + Present w/Permission + Half Day/2) × (Base Salary ÷ 30)  −  Monthly Expenses",
                 font=("Segoe UI", 9), bg="#FFF7ED", fg="#92400E").pack(anchor="w")

        # ─ TABLE ─
        table_card = tk.Frame(self, bg=THEME["bg_card"])
        table_card.pack(fill="both", expand=True)
        table_card.config(highlightbackground=THEME["border"], highlightthickness=1)

        cols = ("Emp ID", "Employee Name", "Base Salary", "Payable Days",
                "Day Salary", "Gross", "Deductions", "Net Salary")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings")
        widths = [60, 180, 110, 100, 100, 110, 110, 120]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        self.tree.column("Emp ID", anchor="center")
        self.tree.column("Payable Days", anchor="center")
        self.tree.column("Net Salary", anchor="e")
        self.tree.column("Gross", anchor="e")
        self.tree.column("Deductions", anchor="e")
        self.tree.column("Day Salary", anchor="e")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        sc = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        sc.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sc.set)

        # Total bar
        tot_bar = tk.Frame(table_card, bg="#F8FAFC", padx=25, pady=14)
        tot_bar.pack(side="bottom", fill="x")
        self.net_total_lbl = tk.Label(tot_bar, text="",
                                       font=("Segoe UI Variable Display", 13, "bold"),
                                       bg="#F8FAFC", fg=THEME["success"])
        self.net_total_lbl.pack(side="left")
        tk.Button(tot_bar, text="📄  SALARY SLIP",
                  command=self._show_slip,
                  bg=THEME["dark"], fg="white",
                  font=("Segoe UI Variable Text", 10, "bold"),
                  bd=0, padx=30, pady=10, cursor="hand2").pack(side="right")

    def _calculate_all(self):
        year  = self._my_picker.get_year()
        month = self._my_picker.get_month()
        my    = f"{month}-{year}"

        conn = self.db.get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT emp_id FROM employees")
        emp_ids = [r["emp_id"] for r in cur.fetchall()]
        conn.close()

        if not emp_ids:
            messagebox.showwarning("No Employees", "Please add employees first.")
            return

        for eid in emp_ids:
            self.db.compute_payroll(eid, my)

        messagebox.showinfo("Done", f"Payroll calculated for all employees for {month}/{year}.")
        self._load_table()

    def _load_table(self, *args):
        for row in self.tree.get_children():
            self.tree.delete(row)
        month = self._my_picker.get_month()
        year  = self._my_picker.get_year()
        my    = f"{month}-{year}"

        conn = self.db.get_connection()
        cur  = conn.cursor()
        cur.execute(
            '''SELECT p.emp_id, e.name, p.base_salary, p.payable_days,
                      p.one_day_salary, p.total_expenses, p.net_salary
               FROM payroll p JOIN employees e ON p.emp_id=e.emp_id
               WHERE p.month_year=? ORDER BY e.name''',
            (my,)
        )
        rows = cur.fetchall()
        conn.close()

        net_total = 0.0
        for r in rows:
            gross = r["payable_days"] * r["one_day_salary"]
            net_total += r["net_salary"]
            self.tree.insert("", "end", values=(
                r["emp_id"],
                r["name"],
                f"₹{r['base_salary']:,.2f}",
                f"{r['payable_days']:g}",
                f"₹{r['one_day_salary']:,.2f}",
                f"₹{gross:,.2f}",
                f"₹{r['total_expenses']:,.2f}",
                f"₹{r['net_salary']:,.2f}",
            ))

        self.net_total_lbl.config(
            text=f"Total Net Payable ({month}/{year}): ₹{net_total:,.2f}  |  {len(rows)} employees"
        )

    def _on_select(self, event):
        pass  # Row just used for slip

    def _show_slip(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Row", "Click on an employee row first.")
            return
        vals = list(self.tree.item(sel[0])["values"])

        def clean(v):
            return float(str(v).replace("₹","").replace(",","").strip())

        emp_id    = vals[0]
        name      = vals[1]
        base_sal  = clean(vals[2])
        p_days    = float(vals[3])
        one_day   = clean(vals[4])
        gross     = clean(vals[5])
        deduct    = clean(vals[6])
        net       = clean(vals[7])
        month     = self._my_picker.get_month()
        year      = self._my_picker.get_year()

        top = tk.Toplevel(self, bg=THEME["bg_card"])
        top.title(f"Salary Slip – {name}")
        top.geometry("500x700")
        top.resizable(False, False)
        top.grab_set()

        c = tk.Frame(top, bg=THEME["bg_card"], padx=50, pady=40)
        c.pack(fill="both", expand=True)

        # Header
        tk.Label(c, text="AADAI UDAI",
                 font=("Segoe UI Variable Display", 22, "bold"),
                 bg=THEME["bg_card"], fg=THEME["primary"]).pack()
        tk.Label(c, text="BOUTIQUE ERP  •  SALARY STATEMENT",
                 font=("Segoe UI Semibold", 9),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(pady=(0,30))

        tk.Frame(c, bg=THEME["border"], height=1).pack(fill="x")
        tk.Label(c, text=f"Month: {month} / {year}",
                 font=("Segoe UI Semibold", 10),
                 bg=THEME["bg_card"], fg=THEME["text_main"]).pack(pady=10)
        tk.Frame(c, bg=THEME["border"], height=1).pack(fill="x")

        items = [
            ("Employee Name",           name),
            ("Employee ID",             str(emp_id)),
            ("Base Monthly Salary",     f"₹{base_sal:,.2f}"),
            ("One Day Salary (÷ 30)",   f"₹{one_day:,.2f}"),
            ("Payable Days (P+PL+PP)",  f"{p_days:g} days"),
            ("Gross Earnings",          f"₹{gross:,.2f}"),
            ("Monthly Deductions",      f"₹{deduct:,.2f}"),
        ]
        for label, val in items:
            row = tk.Frame(c, bg=THEME["bg_card"])
            row.pack(fill="x", pady=7)
            tk.Label(row, text=label,
                     font=("Segoe UI Semibold", 9),
                     bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(side="left")
            tk.Label(row, text=val,
                     font=("Segoe UI Semibold", 10),
                     bg=THEME["bg_card"], fg=THEME["text_main"]).pack(side="right")

        tk.Frame(c, bg=THEME["border"], height=1).pack(fill="x", pady=16)
        tk.Label(c, text="NET SALARY",
                 font=("Segoe UI Variable Display", 14, "bold"),
                 bg=THEME["bg_card"], fg=THEME["success"]).pack()
        tk.Label(c, text=f"₹ {net:,.2f}",
                 font=("Segoe UI Variable Display", 32, "bold"),
                 bg=THEME["bg_card"], fg=THEME["text_main"]).pack(pady=(5,30))
        tk.Label(c, text="Confidential | Aadai Udai Boutique ERP",
                 font=("Segoe UI", 8, "italic"),
                 bg=THEME["bg_card"], fg="#CBD5E1").pack(side="bottom", pady=10)

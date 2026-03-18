import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os, shutil

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from views.shared_widgets import DatePickerButton, enable_smooth_scroll

THEME = {
    "primary":    "#B91C1C", # Red
    "primary_dk": "#991B1B", # Dark Red
    "secondary":  "#FCA5A5", # Light Red
    "bg_page":    "#F1F5F9", # Light Gray/White
    "bg_card":    "#FFFFFF", # White card
    "text_main":  "#0F172A", # Dark text
    "text_muted": "#475569", # Muted dark text
    "border":     "#CBD5E1", # Light border
    "success":    "#10B981",
    "danger":     "#EF4444",
    "dark":       "#0F172A",
}

class EmployeeView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db   = db
        self.selected_photo_path = ""
        self.editing_emp_id      = None
        self.img_tk              = None
        self._setup_ui()
        self.load_employees()

    # ─────────────────────── UI BUILD ────────────────────────────────────────
    def _setup_ui(self):
        # ── LEFT: scrollable form panel ──
        left_outer = tk.Frame(self, bg=THEME["bg_page"], width=465)
        left_outer.pack(side="left", fill="y", padx=(0, 28))
        left_outer.pack_propagate(False)

        # Canvas + scrollbar for vertical scroll
        canvas = tk.Canvas(left_outer, bg=THEME["bg_page"], bd=0,
                           highlightthickness=0)
        v_scroll = ttk.Scrollbar(left_outer, orient="vertical",
                                  command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Inner frame rendered inside canvas
        self._form_frame = tk.Frame(canvas, bg=THEME["bg_card"],
                                     padx=30, pady=22)
        self._form_frame.config(highlightbackground=THEME["border"],
                                highlightthickness=1)
        _win = canvas.create_window((0, 0), window=self._form_frame,
                                     anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(_win, width=event.width)

        self._form_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Smooth scrolling
        enable_smooth_scroll(canvas)

        self._build_form(self._form_frame)

        # ── RIGHT: employee list ──
        right = tk.Frame(self, bg=THEME["bg_card"])
        right.pack(side="right", fill="both", expand=True)
        right.config(highlightbackground=THEME["border"], highlightthickness=1)
        self._build_list(right)

    # ─────────────────── FORM (inside scrollable canvas) ─────────────────────
    def _build_form(self, parent):
        f = parent   # alias

        self._form_title = tk.Label(
            f, text="➕  Register New Staff",
            font=("Segoe UI Variable Display", 15, "bold"),
            bg=THEME["bg_card"], fg=THEME["text_main"])
        self._form_title.pack(anchor="w", pady=(0, 16))

        # Helper to create labelled entry
        def _field(label, default="", show=""):
            tk.Label(f, text=label, font=("Segoe UI Semibold", 8),
                     bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(
                anchor="w", pady=(8, 0))
            row = tk.Frame(f, bg="#F8FAFC", pady=1)
            row.pack(fill="x", pady=(2, 0))
            ent = tk.Entry(row, font=("Segoe UI", 11), bd=0,
                           bg="#F8FAFC", show=show)
            ent.pack(fill="x", padx=10, ipady=6)
            if default:
                ent.insert(0, default)
            tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x",
                                                             pady=(0, 4))
            return ent

        def _combo_field(label, vals):
            tk.Label(f, text=label, font=("Segoe UI Semibold", 8),
                     bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(
                anchor="w", pady=(8, 0))
            row = tk.Frame(f, bg="#F8FAFC")
            row.pack(fill="x", pady=(2, 0))
            cb = ttk.Combobox(row, values=vals, state="readonly",
                              font=("Segoe UI", 10))
            cb.pack(fill="x", padx=10, ipady=4)
            cb.set(vals[0])
            tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x",
                                                            pady=(0, 4))
            return cb

        self.name_ent   = _field("FULL NAME")
        self.gender_cb  = _combo_field("GENDER", ["Male", "Female", "Other"])
        self.phone_ent  = _field("PHONE NUMBER")
        self.desg_ent   = _field("DESIGNATION / ROLE")
        self.salary_ent = _field("BASE MONTHLY SALARY (₹)")

        # Joining Date – Calendar Picker
        tk.Label(f, text="JOINING DATE", font=("Segoe UI Semibold", 8),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(
            anchor="w", pady=(8, 0))
        self._join_picker = DatePickerButton(
            f, initial_date=datetime.now().date(), bg=THEME["bg_card"])
        self._join_picker.pack(fill="x", pady=(2, 0))
        tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(0, 4))

        self.addr_ent   = _field("ADDRESS")

        # Photo
        tk.Label(f, text="PROFILE PHOTO",
                 font=("Segoe UI Semibold", 8),
                 bg=THEME["bg_card"], fg=THEME["text_muted"]).pack(
            anchor="w", pady=(10, 4))
        self.photo_frame = tk.Frame(
            f, bg="#F8FAFC",
            highlightbackground=THEME["border"], highlightthickness=1,
            height=100)
        self.photo_frame.pack(fill="x", pady=(0, 14))
        self.photo_frame.pack_propagate(False)
        self.photo_lbl = tk.Label(
            self.photo_frame, text="📷  Click to upload photo",
            font=("Segoe UI", 8), cursor="hand2",
            bg="#F8FAFC", fg=THEME["text_muted"])
        self.photo_lbl.pack(fill="both", expand=True)
        self.photo_lbl.bind("<Button-1>", lambda _e: self._upload_photo())

        # ── Action buttons ──
        tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(6, 10))

        self._btn_enroll = tk.Button(
            f, text="✔  ENROLL NEW STAFF",
            command=self._save_employee,
            bg=THEME["primary"], fg="white",
            font=("Segoe UI Variable Text", 10, "bold"),
            bd=0, pady=11, cursor="hand2",
            activebackground=THEME["primary_dk"])
        self._btn_enroll.pack(fill="x", pady=(0, 5))

        row2 = tk.Frame(f, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 4))
        tk.Button(row2, text="💾  Update Record",
                  command=self._update_employee,
                  bg=THEME["dark"], fg="white",
                  font=("Segoe UI", 9),
                  bd=0, pady=9, cursor="hand2").pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(row2, text="🗑  Delete",
                  command=self._delete_employee,
                  bg=THEME["danger"], fg="white",
                  font=("Segoe UI", 9),
                  bd=0, pady=9, cursor="hand2").pack(
            side="left", fill="x", expand=True)

        tk.Button(f, text="✖  Clear Form",
                  command=self._clear_form,
                  bg="#ECFDF5", fg=THEME["success"],
                  font=("Segoe UI Semibold", 9),
                  bd=0, pady=6, cursor="hand2").pack(fill="x")

    # ─────────────────────── LIST PANEL ──────────────────────────────────────
    def _build_list(self, parent):
        # Search bar
        sbar = tk.Frame(parent, bg="#F8FAFC", pady=12, padx=18)
        sbar.pack(side="top", fill="x")
        tk.Label(sbar, text="🔍  Search:",
                 font=("Segoe UI Semibold", 9),
                 bg="#F8FAFC", fg=THEME["text_muted"]).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace("w",
            lambda *_: self.load_employees(self._search_var.get()))
        tk.Entry(sbar, textvariable=self._search_var,
                 font=("Segoe UI", 10), bd=0, bg="white",
                 highlightthickness=1,
                 highlightbackground=THEME["border"]).pack(
            side="left", padx=10, fill="x", expand=True, ipady=5)

        # Row count
        self._count_lbl = tk.Label(
            parent, text="",
            font=("Segoe UI", 8),
            bg=THEME["bg_card"], fg=THEME["text_muted"])
        self._count_lbl.pack(anchor="e", padx=18, pady=(4, 0))

        # Treeview
        cols   = ("ID", "Name", "Gender", "Designation",
                  "Base Salary", "Joining Date", "Phone")
        widths = [50,   170,    80,        130,
                  110,         110,           110]
        self.tree = ttk.Treeview(parent, columns=cols,
                                  show="headings", selectmode="browse")
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")
        self.tree.column("ID",         anchor="center", width=50)
        self.tree.column("Base Salary", anchor="e",     width=110)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

        sc = ttk.Scrollbar(parent, orient="vertical",
                           command=self.tree.yview)
        sc.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sc.set)

        # Enter-key navigation for form
        self._all_entries = [self.name_ent, self.gender_cb, self.phone_ent, 
                             self.desg_ent, self.salary_ent, self.addr_ent]
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

    # ─────────────────────── HELPERS ─────────────────────────────────────────
    def _upload_photo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")])
        if not path:
            return
        self.selected_photo_path = path
        if PIL_AVAILABLE:
            try:
                img = Image.open(path)
                img.thumbnail((90, 90))
                self.img_tk = ImageTk.PhotoImage(img)
                self.photo_lbl.config(image=self.img_tk, text="")
            except Exception as ex:
                messagebox.showerror("Photo Error", str(ex))
        else:
            self.photo_lbl.config(text=f"✔ {os.path.basename(path)}")

    def _copy_photo(self):
        if not self.selected_photo_path:
            return ""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(base_dir, "assets", "photos")
            os.makedirs(dest_dir, exist_ok=True)
            ext  = os.path.splitext(self.selected_photo_path)[1]
            dest = os.path.join(
                dest_dir,
                f"emp_{datetime.now().strftime('%Y%j%H%M%S')}{ext}")
            shutil.copy2(self.selected_photo_path, dest)
            return dest
        except Exception:
            return ""

    def _get_form(self):
        return {
            "name":        self.name_ent.get().strip(),
            "gender":      self.gender_cb.get(),
            "phone":       self.phone_ent.get().strip(),
            "designation": self.desg_ent.get().strip(),
            "salary":      self.salary_ent.get().strip(),
            "join_date":   self._join_picker.get_date_str(),
            "address":     self.addr_ent.get().strip(),
        }

    def _validate(self, d):
        if not d["name"]:
            messagebox.showwarning("Required", "Full Name is required.")
            return False
        if not d["salary"]:
            messagebox.showwarning("Required", "Base Salary is required.")
            return False
        try:
            float(d["salary"])
        except ValueError:
            messagebox.showerror("Invalid", "Salary must be a number.")
            return False
        return True

    # ─────────────────────── CRUD ─────────────────────────────────────────────
    def _save_employee(self):
        d = self._get_form()
        if not self._validate(d):
            return
        photo = self._copy_photo()
        conn  = self.db.get_connection()
        conn.execute(
            "INSERT INTO employees "
            "(name, gender, phone, designation, base_salary, "
            " joining_date, address, photo_path) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (d["name"], d["gender"], d["phone"], d["designation"],
             float(d["salary"]), d["join_date"], d["address"], photo)
        )
        conn.commit()
        conn.close()
        messagebox.showinfo("Enrolled  ✔",
                            f"{d['name']} has been enrolled successfully!")
        self._clear_form()
        self.load_employees()

    def _update_employee(self):
        if not self.editing_emp_id:
            messagebox.showwarning(
                "No Selection",
                "Please click a row in the table to select an employee first.")
            return
        d = self._get_form()
        if not self._validate(d):
            return
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE employees SET name=?, gender=?, phone=?, designation=?, "
            "base_salary=?, joining_date=?, address=? WHERE emp_id=?",
            (d["name"], d["gender"], d["phone"], d["designation"],
             float(d["salary"]), d["join_date"], d["address"],
             self.editing_emp_id)
        )
        if self.selected_photo_path:
            photo = self._copy_photo()
            if photo:
                conn.execute(
                    "UPDATE employees SET photo_path=? WHERE emp_id=?",
                    (photo, self.editing_emp_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Updated  ✔", "Employee record updated.")
        self._clear_form()
        self.load_employees()

    def _delete_employee(self):
        if not self.editing_emp_id:
            messagebox.showwarning(
                "No Selection",
                "Please click a row in the table first.")
            return
        if messagebox.askyesno(
                "Confirm Delete",
                "This will permanently delete the employee and ALL their "
                "attendance, expenses and payroll records. Continue?"):
            conn = self.db.get_connection()
            conn.execute(
                "DELETE FROM employees WHERE emp_id=?",
                (self.editing_emp_id,))
            conn.commit()
            conn.close()
            self._clear_form()
            self.load_employees()

    def _clear_form(self):
        self.editing_emp_id      = None
        self.selected_photo_path = ""
        self._form_title.config(text="➕  Register New Staff")
        for ent in (self.name_ent, self.phone_ent, self.desg_ent,
                    self.salary_ent, self.addr_ent):
            ent.delete(0, "end")
        self._join_picker.set_date(datetime.now().date())
        self.gender_cb.set("Male")
        self.photo_lbl.config(image="", text="📷  Click to upload photo")
        self.img_tk = None

    # ─────────────────────── LOAD TABLE ──────────────────────────────────────
    def load_employees(self, search=""):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = self.db.get_connection()
        cur  = conn.cursor()
        if search:
            cur.execute(
                "SELECT emp_id, name, gender, designation, base_salary, "
                "joining_date, phone FROM employees "
                "WHERE name LIKE ? OR designation LIKE ? ORDER BY name",
                (f"%{search}%", f"%{search}%"))
        else:
            cur.execute(
                "SELECT emp_id, name, gender, designation, base_salary, "
                "joining_date, phone FROM employees ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            self.tree.insert("", "end", values=(
                r["emp_id"],
                r["name"],
                r["gender"] or "-",
                r["designation"] or "-",
                f"₹{r['base_salary']:,.0f}",
                r["joining_date"] or "-",
                r["phone"] or "-",
            ))
        self._count_lbl.config(text=f"{len(rows)} employee(s) found")

    # ─────────────────────── SELECT ROW ──────────────────────────────────────
    def _on_row_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        eid = self.tree.item(sel[0])["values"][0]
        conn = self.db.get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE emp_id=?", (eid,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return

        self.editing_emp_id      = eid
        self.selected_photo_path = ""
        self._form_title.config(text=f"✏  Editing: {r['name']}")

        for ent, key in (
            (self.name_ent,   "name"),
            (self.phone_ent,  "phone"),
            (self.desg_ent,   "designation"),
            (self.addr_ent,   "address"),
        ):
            ent.delete(0, "end")
            ent.insert(0, r[key] or "")

        self.salary_ent.delete(0, "end")
        self.salary_ent.insert(0, str(r["base_salary"]))

        # Set joining date picker
        jd = r["joining_date"] or ""
        if jd:
            try:
                d = datetime.strptime(jd, "%Y-%m-%d").date()
                self._join_picker.set_date(d)
            except:
                pass

        self.gender_cb.set(r["gender"] or "Male")

        # Show photo if available
        photo = r["photo_path"]
        if photo and os.path.exists(str(photo)) and PIL_AVAILABLE:
            try:
                img = Image.open(photo)
                img.thumbnail((90, 90))
                self.img_tk = ImageTk.PhotoImage(img)
                self.photo_lbl.config(image=self.img_tk, text="")
            except Exception:
                pass

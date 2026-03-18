import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import shutil

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from views.shared_widgets import DatePickerButton, enable_smooth_scroll

THEME = {
    "primary": "#B91C1C",
    "primary_dk": "#991B1B",
    "secondary": "#FCA5A5",
    "bg_page": "#F1F5F9",
    "bg_card": "#FFFFFF",
    "text_main": "#0F172A",
    "text_muted": "#475569",
    "border": "#CBD5E1",
    "success": "#10B981",
    "danger": "#EF4444",
    "dark": "#0F172A",
}


class EmployeeView(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=THEME["bg_page"])
        self.db = db
        self.selected_photo_path = ""
        self.editing_emp_id = None
        self.img_tk = None
        self._detail_img_tk = None
        self._menu_emp_id = None
        self._setup_ui()
        self.load_employees()

    def _setup_ui(self):
        left_outer = tk.Frame(self, bg=THEME["bg_page"], width=465)
        left_outer.pack(side="left", fill="y", padx=(0, 28))
        left_outer.pack_propagate(False)

        canvas = tk.Canvas(left_outer, bg=THEME["bg_page"], bd=0, highlightthickness=0)
        v_scroll = ttk.Scrollbar(left_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._form_frame = tk.Frame(canvas, bg=THEME["bg_card"], padx=30, pady=22)
        self._form_frame.config(highlightbackground=THEME["border"], highlightthickness=1)
        form_window = canvas.create_window((0, 0), window=self._form_frame, anchor="nw")

        def _on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(form_window, width=event.width)

        self._form_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        enable_smooth_scroll(canvas)

        self._build_form(self._form_frame)

        right = tk.Frame(self, bg=THEME["bg_card"])
        right.pack(side="right", fill="both", expand=True)
        right.config(highlightbackground=THEME["border"], highlightthickness=1)
        self._build_list(right)

    def _build_form(self, parent):
        f = parent

        self._form_title = tk.Label(
            f,
            text="Register New Staff",
            font=("Segoe UI Variable Display", 15, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_main"],
        )
        self._form_title.pack(anchor="w", pady=(0, 16))

        def _field(label, default="", show=""):
            tk.Label(
                f,
                text=label,
                font=("Segoe UI Semibold", 8),
                bg=THEME["bg_card"],
                fg=THEME["text_muted"],
            ).pack(anchor="w", pady=(8, 0))
            row = tk.Frame(f, bg="#F8FAFC", pady=1)
            row.pack(fill="x", pady=(2, 0))
            ent = tk.Entry(row, font=("Segoe UI", 11), bd=0, bg="#F8FAFC", show=show)
            ent.pack(fill="x", padx=10, ipady=6)
            if default:
                ent.insert(0, default)
            tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(0, 4))
            return ent

        def _combo_field(label, vals):
            tk.Label(
                f,
                text=label,
                font=("Segoe UI Semibold", 8),
                bg=THEME["bg_card"],
                fg=THEME["text_muted"],
            ).pack(anchor="w", pady=(8, 0))
            row = tk.Frame(f, bg="#F8FAFC")
            row.pack(fill="x", pady=(2, 0))
            cb = ttk.Combobox(row, values=vals, state="readonly", font=("Segoe UI", 10))
            cb.pack(fill="x", padx=10, ipady=4)
            cb.set(vals[0])
            tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(0, 4))
            return cb

        self.name_ent = _field("FULL NAME")
        self.gender_cb = _combo_field("GENDER", ["Male", "Female", "Other"])
        self.phone_ent = _field("PHONE NUMBER")
        self.desg_ent = _field("DESIGNATION / ROLE")
        self.salary_ent = _field("BASE MONTHLY SALARY (Rs)")

        tk.Label(
            f,
            text="JOINING DATE",
            font=("Segoe UI Semibold", 8),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(8, 0))
        self._join_picker = DatePickerButton(f, initial_date=datetime.now().date(), bg=THEME["bg_card"])
        self._join_picker.pack(fill="x", pady=(2, 0))
        tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(0, 4))

        self.addr_ent = _field("ADDRESS")

        tk.Label(
            f,
            text="PROFILE PHOTO",
            font=("Segoe UI Semibold", 8),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(10, 4))
        self.photo_frame = tk.Frame(
            f,
            bg="#F8FAFC",
            highlightbackground=THEME["border"],
            highlightthickness=1,
            height=100,
        )
        self.photo_frame.pack(fill="x", pady=(0, 14))
        self.photo_frame.pack_propagate(False)
        self.photo_lbl = tk.Label(
            self.photo_frame,
            text="Click to upload photo",
            font=("Segoe UI", 8),
            cursor="hand2",
            bg="#F8FAFC",
            fg=THEME["text_muted"],
        )
        self.photo_lbl.pack(fill="both", expand=True)
        self.photo_lbl.bind("<Button-1>", lambda _e: self._upload_photo())

        tk.Frame(f, bg=THEME["border"], height=1).pack(fill="x", pady=(6, 10))

        self._btn_enroll = tk.Button(
            f,
            text="ENROLL NEW STAFF",
            command=self._save_employee,
            bg=THEME["primary"],
            fg="white",
            font=("Segoe UI Variable Text", 10, "bold"),
            bd=0,
            pady=11,
            cursor="hand2",
            activebackground=THEME["primary_dk"],
        )
        self._btn_enroll.pack(fill="x", pady=(0, 5))

        row2 = tk.Frame(f, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 4))
        tk.Button(
            row2,
            text="Update Record",
            command=self._update_employee,
            bg=THEME["dark"],
            fg="white",
            font=("Segoe UI", 9),
            bd=0,
            pady=9,
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(
            row2,
            text="Delete",
            command=self._delete_employee,
            bg=THEME["danger"],
            fg="white",
            font=("Segoe UI", 9),
            bd=0,
            pady=9,
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            f,
            text="Clear Form",
            command=self._clear_form,
            bg="#ECFDF5",
            fg=THEME["success"],
            font=("Segoe UI Semibold", 9),
            bd=0,
            pady=6,
            cursor="hand2",
        ).pack(fill="x")

    def _build_list(self, parent):
        sbar = tk.Frame(parent, bg="#F8FAFC", pady=12, padx=18)
        sbar.pack(side="top", fill="x")
        tk.Label(
            sbar,
            text="Search:",
            font=("Segoe UI Semibold", 9),
            bg="#F8FAFC",
            fg=THEME["text_muted"],
        ).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace("w", lambda *_: self.load_employees(self._search_var.get()))
        tk.Entry(
            sbar,
            textvariable=self._search_var,
            font=("Segoe UI", 10),
            bd=0,
            bg="white",
            highlightthickness=1,
            highlightbackground=THEME["border"],
        ).pack(side="left", padx=10, fill="x", expand=True, ipady=5)

        self._count_lbl = tk.Label(
            parent,
            text="",
            font=("Segoe UI", 8),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        )
        self._count_lbl.pack(anchor="e", padx=18, pady=(4, 0))

        cols = ("ID", "Name", "Gender", "Designation", "Base Salary", "Joining Date", "Phone")
        widths = [50, 170, 80, 130, 110, 110, 110]
        self.tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
        for col, width in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w")
        self.tree.column("ID", anchor="center", width=50)
        self.tree.column("Base Salary", anchor="e", width=110)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<ButtonRelease-1>", self._on_row_left_click)
        self.tree.bind("<Button-3>", self._on_row_right_click)

        self._row_menu = tk.Menu(self, tearoff=0)
        self._row_menu.add_command(label="Update", command=self._menu_update_employee)
        self._row_menu.add_command(label="Delete", command=self._menu_delete_employee)

        sc = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        sc.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sc.set)

        self._all_entries = [self.name_ent, self.gender_cb, self.phone_ent, self.desg_ent, self.salary_ent, self.addr_ent]

        def _focus_next(event):
            widget = event.widget
            if widget in self._all_entries:
                idx = self._all_entries.index(widget)
                nxt = self._all_entries[(idx + 1) % len(self._all_entries)]
                nxt.focus_set()
                try:
                    nxt.select_range(0, "end")
                except Exception:
                    pass
            return "break"

        for widget in self._all_entries:
            widget.bind("<Return>", _focus_next)
            widget.bind("<KP_Enter>", _focus_next)

    def _upload_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")])
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
            self.photo_lbl.config(text=os.path.basename(path))

    def _copy_photo(self):
        if not self.selected_photo_path:
            return ""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dest_dir = os.path.join(base_dir, "assets", "photos")
            os.makedirs(dest_dir, exist_ok=True)
            ext = os.path.splitext(self.selected_photo_path)[1]
            dest = os.path.join(dest_dir, f"emp_{datetime.now().strftime('%Y%j%H%M%S')}{ext}")
            shutil.copy2(self.selected_photo_path, dest)
            return dest
        except Exception:
            return ""

    def _get_employee_record(self, emp_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        row = cur.fetchone()
        conn.close()
        return row

    def _resolve_photo_path(self, photo_path):
        if not photo_path:
            return None

        candidate = str(photo_path)
        if os.path.exists(candidate):
            return candidate

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alt_candidate = os.path.join(base_dir, candidate)
        if os.path.exists(alt_candidate):
            return alt_candidate

        photos_dir = os.path.join(base_dir, "assets", "photos", os.path.basename(candidate))
        if os.path.exists(photos_dir):
            return photos_dir

        return None

    def _get_form(self):
        return {
            "name": self.name_ent.get().strip(),
            "gender": self.gender_cb.get(),
            "phone": self.phone_ent.get().strip(),
            "designation": self.desg_ent.get().strip(),
            "salary": self.salary_ent.get().strip(),
            "join_date": self._join_picker.get_date_str(),
            "address": self.addr_ent.get().strip(),
        }

    def _validate(self, data):
        if not data["name"]:
            messagebox.showwarning("Required", "Full Name is required.")
            return False
        if not data["salary"]:
            messagebox.showwarning("Required", "Base Salary is required.")
            return False
        try:
            float(data["salary"])
        except ValueError:
            messagebox.showerror("Invalid", "Salary must be a number.")
            return False
        return True

    def _save_employee(self):
        data = self._get_form()
        if not self._validate(data):
            return
        photo = self._copy_photo()
        conn = self.db.get_connection()
        conn.execute(
            "INSERT INTO employees "
            "(name, gender, phone, designation, base_salary, joining_date, address, photo_path) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                data["name"],
                data["gender"],
                data["phone"],
                data["designation"],
                float(data["salary"]),
                data["join_date"],
                data["address"],
                photo,
            ),
        )
        conn.commit()
        conn.close()
        messagebox.showinfo("Enrolled", f"{data['name']} has been enrolled successfully!")
        self._clear_form()
        self.load_employees()

    def _update_employee(self):
        if not self.editing_emp_id:
            messagebox.showwarning("No Selection", "Please right-click an employee and choose Update first.")
            return
        data = self._get_form()
        if not self._validate(data):
            return
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE employees SET name=?, gender=?, phone=?, designation=?, "
            "base_salary=?, joining_date=?, address=? WHERE emp_id=?",
            (
                data["name"],
                data["gender"],
                data["phone"],
                data["designation"],
                float(data["salary"]),
                data["join_date"],
                data["address"],
                self.editing_emp_id,
            ),
        )
        if self.selected_photo_path:
            photo = self._copy_photo()
            if photo:
                conn.execute("UPDATE employees SET photo_path=? WHERE emp_id=?", (photo, self.editing_emp_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Updated", "Employee record updated.")
        self._clear_form()
        self.load_employees()

    def _delete_employee(self):
        if not self.editing_emp_id:
            messagebox.showwarning("No Selection", "Please right-click an employee and choose Delete first.")
            return
        if messagebox.askyesno(
            "Confirm Delete",
            "This will permanently delete the employee and ALL their attendance, expenses and payroll records. Continue?",
        ):
            conn = self.db.get_connection()
            conn.execute("DELETE FROM employees WHERE emp_id=?", (self.editing_emp_id,))
            conn.commit()
            conn.close()
            self._clear_form()
            self.load_employees()

    def _clear_form(self):
        self.editing_emp_id = None
        self.selected_photo_path = ""
        self._form_title.config(text="Register New Staff")
        for ent in (self.name_ent, self.phone_ent, self.desg_ent, self.salary_ent, self.addr_ent):
            ent.delete(0, "end")
        self._join_picker.set_date(datetime.now().date())
        self.gender_cb.set("Male")
        self.photo_lbl.config(image="", text="Click to upload photo")
        self.img_tk = None

    def load_employees(self, search=""):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = self.db.get_connection()
        cur = conn.cursor()
        if search:
            cur.execute(
                "SELECT emp_id, name, gender, designation, base_salary, joining_date, phone "
                "FROM employees WHERE name LIKE ? OR designation LIKE ? ORDER BY name",
                (f"%{search}%", f"%{search}%"),
            )
        else:
            cur.execute(
                "SELECT emp_id, name, gender, designation, base_salary, joining_date, phone "
                "FROM employees ORDER BY name"
            )
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    row["emp_id"],
                    row["name"],
                    row["gender"] or "-",
                    row["designation"] or "-",
                    f"Rs {row['base_salary']:,.0f}",
                    row["joining_date"] or "-",
                    row["phone"] or "-",
                ),
            )
        self._count_lbl.config(text=f"{len(rows)} employee(s) found")

    def _fill_form_for_employee(self, emp_id):
        record = self._get_employee_record(emp_id)
        if not record:
            return

        self.editing_emp_id = emp_id
        self.selected_photo_path = ""
        self._form_title.config(text=f"Editing: {record['name']}")

        for ent, key in (
            (self.name_ent, "name"),
            (self.phone_ent, "phone"),
            (self.desg_ent, "designation"),
            (self.addr_ent, "address"),
        ):
            ent.delete(0, "end")
            ent.insert(0, record[key] or "")

        self.salary_ent.delete(0, "end")
        self.salary_ent.insert(0, str(record["base_salary"]))

        join_date = record["joining_date"] or ""
        if join_date:
            try:
                self._join_picker.set_date(datetime.strptime(join_date, "%Y-%m-%d").date())
            except Exception:
                pass

        self.gender_cb.set(record["gender"] or "Male")

        photo = self._resolve_photo_path(record["photo_path"])
        if photo and PIL_AVAILABLE:
            try:
                img = Image.open(photo)
                img.thumbnail((90, 90))
                self.img_tk = ImageTk.PhotoImage(img)
                self.photo_lbl.config(image=self.img_tk, text="")
            except Exception:
                self.photo_lbl.config(image="", text="Click to upload photo")
                self.img_tk = None
        else:
            self.photo_lbl.config(image="", text="Click to upload photo")
            self.img_tk = None

    def _show_employee_slip(self, emp_id):
        record = self._get_employee_record(emp_id)
        if not record:
            return

        pop = tk.Toplevel(self)
        pop.title(f"Employee Details - {record['name']}")
        pop.transient(self.winfo_toplevel())
        pop.grab_set()
        pop.configure(bg=THEME["bg_page"])
        pop.geometry("560x520")
        pop.resizable(False, False)

        card = tk.Frame(
            pop,
            bg=THEME["bg_card"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            padx=24,
            pady=22,
        )
        card.pack(fill="both", expand=True, padx=18, pady=18)

        tk.Label(
            card,
            text="Employee Detail Slip",
            font=("Segoe UI Variable Display", 18, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_main"],
        ).pack(anchor="w")
        tk.Label(
            card,
            text=f"Employee ID: EMP-{record['emp_id']:04d}",
            font=("Segoe UI", 10),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(4, 18))

        top = tk.Frame(card, bg=THEME["bg_card"])
        top.pack(fill="x", pady=(0, 18))

        photo_holder = tk.Frame(
            top,
            bg="#F8FAFC",
            highlightbackground=THEME["border"],
            highlightthickness=1,
            width=150,
            height=170,
        )
        photo_holder.pack(side="left")
        photo_holder.pack_propagate(False)

        self._detail_img_tk = None
        photo_path = self._resolve_photo_path(record["photo_path"])
        if photo_path and PIL_AVAILABLE:
            try:
                img = Image.open(photo_path)
                img.thumbnail((135, 155))
                self._detail_img_tk = ImageTk.PhotoImage(img)
                tk.Label(photo_holder, image=self._detail_img_tk, bg="#F8FAFC").pack(expand=True)
            except Exception:
                tk.Label(photo_holder, text="No Photo", bg="#F8FAFC", fg=THEME["text_muted"]).pack(expand=True)
        else:
            tk.Label(photo_holder, text="No Photo", bg="#F8FAFC", fg=THEME["text_muted"]).pack(expand=True)

        summary = tk.Frame(top, bg=THEME["bg_card"])
        summary.pack(side="left", fill="both", expand=True, padx=(20, 0))
        tk.Label(
            summary,
            text=record["name"] or "-",
            font=("Segoe UI Variable Display", 20, "bold"),
            bg=THEME["bg_card"],
            fg=THEME["text_main"],
        ).pack(anchor="w")
        tk.Label(
            summary,
            text=record["designation"] or "Staff Member",
            font=("Segoe UI Semibold", 11),
            bg=THEME["bg_card"],
            fg=THEME["primary"],
        ).pack(anchor="w", pady=(6, 0))
        tk.Label(
            summary,
            text=f"Joined on {record['joining_date'] or '-'}",
            font=("Segoe UI", 10),
            bg=THEME["bg_card"],
            fg=THEME["text_muted"],
        ).pack(anchor="w", pady=(8, 0))

        details = tk.Frame(card, bg=THEME["bg_card"])
        details.pack(fill="both", expand=True)

        def slip_row(label, value):
            row = tk.Frame(details, bg="#F8FAFC", padx=14, pady=12)
            row.pack(fill="x", pady=(0, 10))
            row.config(highlightbackground=THEME["border"], highlightthickness=1)
            tk.Label(
                row,
                text=label,
                font=("Segoe UI Semibold", 9),
                bg="#F8FAFC",
                fg=THEME["text_muted"],
                anchor="w",
                width=14,
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                row,
                text=value,
                font=("Segoe UI", 11),
                bg="#F8FAFC",
                fg=THEME["text_main"],
                anchor="w",
                justify="left",
                wraplength=320,
            ).grid(row=0, column=1, sticky="w", padx=(18, 0))
            row.columnconfigure(0, minsize=140)
            row.columnconfigure(1, weight=1)

        slip_row("Full Name", record["name"] or "-")
        slip_row("Gender", record["gender"] or "-")
        slip_row("Phone", record["phone"] or "-")
        slip_row("Designation", record["designation"] or "-")
        slip_row("Base Salary", f"Rs {float(record['base_salary'] or 0):,.0f}")
        slip_row("Address", record["address"] or "-")

        tk.Button(
            card,
            text="Close",
            command=pop.destroy,
            bg=THEME["primary"],
            fg="white",
            activebackground=THEME["primary_dk"],
            activeforeground="white",
            font=("Segoe UI Semibold", 10),
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(anchor="e", pady=(8, 0))

    def _tree_emp_id_from_event(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return None
        self.tree.selection_set(row_id)
        values = self.tree.item(row_id).get("values", [])
        if not values:
            return None
        return values[0]

    def _on_row_left_click(self, event):
        emp_id = self._tree_emp_id_from_event(event)
        if emp_id is not None:
            self._show_employee_slip(emp_id)

    def _on_row_right_click(self, event):
        emp_id = self._tree_emp_id_from_event(event)
        if emp_id is None:
            return
        self._menu_emp_id = emp_id
        self._row_menu.tk_popup(event.x_root, event.y_root)
        self._row_menu.grab_release()

    def _menu_update_employee(self):
        if self._menu_emp_id is not None:
            self._fill_form_for_employee(self._menu_emp_id)

    def _menu_delete_employee(self):
        if self._menu_emp_id is None:
            return
        self._fill_form_for_employee(self._menu_emp_id)
        self._delete_employee()

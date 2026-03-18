"""
Shared UI widgets used across all views:
  - CalendarPopup      : A sleek calendar date picker (Jan 2026 – Dec 2040)
  - MonthYearPicker    : A month+year picker button with popup
  - enable_smooth_scroll : Helper to add smooth scroll to any existing canvas
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import calendar as cal_mod

# ── Date range limits ────────────────────────────────────────────────────────
MIN_YEAR = 2026
MAX_YEAR = 2040

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


# ═══════════════════════════════════════════════════════════════════════════════
#  CALENDAR POPUP  (full date picker: Jan 2026 → Dec 2040)
# ═══════════════════════════════════════════════════════════════════════════════
class CalendarPopup(tk.Toplevel):
    """Borderless calendar popup for picking a day."""

    def __init__(self, parent, selected_date=None, callback=None):
        super().__init__(parent)
        self.overrideredirect(True)
        self.callback = callback
        self.configure(bg=THEME["dark"])
        self.attributes("-topmost", True)

        if selected_date:
            self._year = selected_date.year
            self._month = selected_date.month
        else:
            now = datetime.now()
            self._year = now.year
            self._month = now.month

        # Clamp to allowed range
        self._year = max(MIN_YEAR, min(MAX_YEAR, self._year))

        self._selected = selected_date

        border = tk.Frame(self, bg=THEME["border"], padx=1, pady=1)
        border.pack(fill="both", expand=True)
        self._inner = tk.Frame(border, bg=THEME["bg_card"])
        self._inner.pack(fill="both", expand=True)

        self._build()

        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty() + parent.winfo_height() + 4

        # Keep popup on screen
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        pw = self.winfo_reqwidth()
        ph = self.winfo_reqheight()
        if px + pw > sw:
            px = sw - pw - 8
        if py + ph > sh:
            py = parent.winfo_rooty() - ph - 4

        self.geometry(f"+{px}+{py}")
        self.bind("<FocusOut>", lambda e: self.after(150, self._check_focus))
        self.focus_set()

    def _check_focus(self):
        try:
            fw = self.focus_get()
            if fw is None or not str(fw).startswith(str(self)):
                self.destroy()
        except:
            self.destroy()

    def _build(self):
        for w in self._inner.winfo_children():
            w.destroy()

        # ── Navigation Bar ──
        nav = tk.Frame(self._inner, bg=THEME["dark"], pady=8, padx=6)
        nav.pack(fill="x")

        can_prev = not (self._year == MIN_YEAR and self._month == 1)
        can_next = not (self._year == MAX_YEAR and self._month == 12)

        prev_btn = tk.Button(nav, text="◀", command=self._prev_month,
                             bg=THEME["dark"], fg="white" if can_prev else "#475569",
                             font=("Segoe UI", 12, "bold"), bd=0,
                             activebackground=THEME["primary"],
                             cursor="hand2" if can_prev else "",
                             state="normal" if can_prev else "disabled",
                             width=3)
        prev_btn.pack(side="left", padx=2)

        month_name = cal_mod.month_name[self._month]
        tk.Label(nav, text=f"{month_name}  {self._year}",
                 font=("Segoe UI Semibold", 11),
                 bg=THEME["dark"], fg="white").pack(side="left", expand=True)

        next_btn = tk.Button(nav, text="▶", command=self._next_month,
                             bg=THEME["dark"], fg="white" if can_next else "#475569",
                             font=("Segoe UI", 12, "bold"), bd=0,
                             activebackground=THEME["primary"],
                             cursor="hand2" if can_next else "",
                             state="normal" if can_next else "disabled",
                             width=3)
        next_btn.pack(side="right", padx=2)

        # ── Day-of-week headers ──
        dow = tk.Frame(self._inner, bg="#F0F4F8", pady=4)
        dow.pack(fill="x")
        for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
            tk.Label(dow, text=d, font=("Segoe UI Semibold", 8),
                     bg="#F0F4F8", fg=THEME["text_muted"],
                     width=4).pack(side="left", padx=1)

        # ── Day Grid ──
        grid = tk.Frame(self._inner, bg=THEME["bg_card"], padx=4, pady=4)
        grid.pack(fill="both")

        weeks = cal_mod.monthcalendar(self._year, self._month)
        today = datetime.now().date()

        for week in weeks:
            wf = tk.Frame(grid, bg=THEME["bg_card"])
            wf.pack(fill="x")
            for day in week:
                if day == 0:
                    tk.Label(wf, text="", width=4, height=2,
                             bg=THEME["bg_card"]).pack(side="left", padx=1, pady=1)
                else:
                    d = datetime(self._year, self._month, day).date()
                    is_today = (d == today)
                    is_sel = (self._selected and d == self._selected)

                    if is_sel:
                        bg, fg = THEME["primary"], "white"
                    elif is_today:
                        bg, fg = "#EEF2FF", THEME["secondary"]
                    else:
                        bg, fg = THEME["bg_card"], THEME["text_main"]

                    btn = tk.Button(
                        wf, text=str(day), width=4, height=1,
                        bg=bg, fg=fg,
                        font=("Segoe UI", 9,
                              "bold" if is_today or is_sel else "normal"),
                        bd=0, cursor="hand2",
                        activebackground=THEME["primary"],
                        activeforeground="white",
                        command=lambda dd=day: self._pick(dd))
                    btn.pack(side="left", padx=1, pady=1)

                    if not is_sel:
                        btn.bind("<Enter>",
                                 lambda e, b=btn: b.config(bg="#FFE4E6"))
                        btn.bind("<Leave>",
                                 lambda e, b=btn, bg_=bg: b.config(bg=bg_))

        # ── Today shortcut ──
        tf = tk.Frame(self._inner, bg=THEME["bg_card"], pady=6)
        tf.pack(fill="x")
        tk.Button(tf, text="● Today", command=self._pick_today,
                  bg=THEME["bg_card"], fg=THEME["primary"],
                  font=("Segoe UI Semibold", 9), bd=0,
                  cursor="hand2",
                  activeforeground=THEME["primary_dk"]).pack()

    def _prev_month(self):
        if self._year == MIN_YEAR and self._month == 1:
            return
        if self._month == 1:
            self._month = 12
            self._year -= 1
        else:
            self._month -= 1
        self._build()

    def _next_month(self):
        if self._year == MAX_YEAR and self._month == 12:
            return
        if self._month == 12:
            self._month = 1
            self._year += 1
        else:
            self._month += 1
        self._build()

    def _pick(self, day):
        picked = datetime(self._year, self._month, day).date()
        if self.callback:
            self.callback(picked)
        self.destroy()

    def _pick_today(self):
        today = datetime.now().date()
        if self.callback:
            self.callback(today)
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  MONTH-YEAR PICKER POPUP (Jan 2026 → Dec 2040)
# ═══════════════════════════════════════════════════════════════════════════════
class MonthYearPopup(tk.Toplevel):
    """Popup to pick a month+year (no day)."""

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def __init__(self, parent, selected_year=None, selected_month=None,
                 callback=None):
        super().__init__(parent)
        self.overrideredirect(True)
        self.callback = callback
        self.configure(bg=THEME["dark"])
        self.attributes("-topmost", True)

        self._year = selected_year or datetime.now().year
        self._year = max(MIN_YEAR, min(MAX_YEAR, self._year))
        self._sel_month = selected_month  # 1-12

        border = tk.Frame(self, bg=THEME["border"], padx=1, pady=1)
        border.pack(fill="both", expand=True)
        self._inner = tk.Frame(border, bg=THEME["bg_card"])
        self._inner.pack(fill="both", expand=True)

        self._build()

        self.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty() + parent.winfo_height() + 4
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        pw = self.winfo_reqwidth()
        ph = self.winfo_reqheight()
        if px + pw > sw:
            px = sw - pw - 8
        if py + ph > sh:
            py = parent.winfo_rooty() - ph - 4
        self.geometry(f"+{px}+{py}")

        self.bind("<FocusOut>", lambda e: self.after(150, self._check_focus))
        self.focus_set()

    def _check_focus(self):
        try:
            fw = self.focus_get()
            if fw is None or not str(fw).startswith(str(self)):
                self.destroy()
        except:
            self.destroy()

    def _build(self):
        for w in self._inner.winfo_children():
            w.destroy()

        # ── Year navigation ──
        nav = tk.Frame(self._inner, bg=THEME["dark"], pady=8, padx=6)
        nav.pack(fill="x")

        can_prev = self._year > MIN_YEAR
        can_next = self._year < MAX_YEAR

        tk.Button(nav, text="◀", command=self._prev_year,
                  bg=THEME["dark"],
                  fg="white" if can_prev else "#475569",
                  font=("Segoe UI", 12, "bold"), bd=0,
                  activebackground=THEME["primary"],
                  cursor="hand2" if can_prev else "",
                  state="normal" if can_prev else "disabled",
                  width=3).pack(side="left", padx=2)

        tk.Label(nav, text=str(self._year),
                 font=("Segoe UI Semibold", 13, "bold"),
                 bg=THEME["dark"], fg="white").pack(side="left", expand=True)

        tk.Button(nav, text="▶", command=self._next_year,
                  bg=THEME["dark"],
                  fg="white" if can_next else "#475569",
                  font=("Segoe UI", 12, "bold"), bd=0,
                  activebackground=THEME["primary"],
                  cursor="hand2" if can_next else "",
                  state="normal" if can_next else "disabled",
                  width=3).pack(side="right", padx=2)

        # ── Month Grid (4 × 3) ──
        grid = tk.Frame(self._inner, bg=THEME["bg_card"], padx=8, pady=8)
        grid.pack(fill="both")

        now = datetime.now()
        for i, m_name in enumerate(self.MONTHS):
            m_num = i + 1
            r, c = divmod(i, 4)

            is_sel = (self._sel_month == m_num and
                      self._year == (self._year))
            is_current = (m_num == now.month and self._year == now.year)

            if is_sel:
                bg, fg = THEME["primary"], "white"
            elif is_current:
                bg, fg = "#EEF2FF", THEME["secondary"]
            else:
                bg, fg = THEME["bg_card"], THEME["text_main"]

            btn = tk.Button(grid, text=m_name, width=6, height=2,
                            bg=bg, fg=fg,
                            font=("Segoe UI", 9,
                                  "bold" if is_sel or is_current else "normal"),
                            bd=0, cursor="hand2",
                            activebackground=THEME["primary"],
                            activeforeground="white",
                            command=lambda mn=m_num: self._pick(mn))
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="ew")

            if not is_sel:
                btn.bind("<Enter>",
                         lambda e, b=btn: b.config(bg="#FFE4E6"))
                btn.bind("<Leave>",
                         lambda e, b=btn, bg_=bg: b.config(bg=bg_))

        grid.columnconfigure((0, 1, 2, 3), weight=1)

    def _prev_year(self):
        if self._year > MIN_YEAR:
            self._year -= 1
            self._build()

    def _next_year(self):
        if self._year < MAX_YEAR:
            self._year += 1
            self._build()

    def _pick(self, month_num):
        if self.callback:
            self.callback(self._year, month_num)
        self.destroy()


# ═══════════════════════════════════════════════════════════════════════════════
#  DATE PICKER BUTTON  (click to open CalendarPopup)
# ═══════════════════════════════════════════════════════════════════════════════
class DatePickerButton(tk.Frame):
    """A button that displays the selected date and opens a calendar on click.

    Attributes:
        selected_date: the currently selected datetime.date
    """

    def __init__(self, parent, initial_date=None, on_change=None, **kw):
        super().__init__(parent, bg=kw.get("bg", THEME["bg_card"]))
        self.selected_date = initial_date or datetime.now().date()
        self._on_change = on_change

        self._btn = tk.Button(
            self,
            text=self._format_date(),
            command=self._open,
            bg="#F8FAFC", fg=THEME["text_main"],
            font=("Segoe UI Semibold", 11),
            bd=0, cursor="hand2",
            activebackground="#EEF2FF",
            padx=14, pady=7,
            highlightbackground=THEME["border"], highlightthickness=1)
        self._btn.pack(fill="x")

        self._btn.bind("<Enter>",
                       lambda e: self._btn.config(bg="#EEF2FF"))
        self._btn.bind("<Leave>",
                       lambda e: self._btn.config(bg="#F8FAFC"))

    def _format_date(self):
        return f"  📅  {self.selected_date.strftime('%d  %b  %Y')}  ▾  "

    def _open(self):
        CalendarPopup(self._btn, self.selected_date, self._picked)

    def _picked(self, d):
        self.selected_date = d
        self._btn.config(text=self._format_date())
        if self._on_change:
            self._on_change(d)

    def get_date_str(self):
        """Return string in YYYY-MM-DD format."""
        return self.selected_date.strftime("%Y-%m-%d")

    def set_date(self, d):
        """Programmatically set the date (datetime.date)."""
        self.selected_date = d
        self._btn.config(text=self._format_date())


# ═══════════════════════════════════════════════════════════════════════════════
#  MONTH-YEAR PICKER BUTTON
# ═══════════════════════════════════════════════════════════════════════════════
class MonthYearPickerButton(tk.Frame):
    """A button showing selected month+year; opens MonthYearPopup on click."""

    MONTH_NAMES = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def __init__(self, parent, initial_year=None, initial_month=None,
                 on_change=None, **kw):
        super().__init__(parent, bg=kw.get("bg", THEME["bg_card"]))
        self.sel_year = initial_year or datetime.now().year
        self.sel_month = initial_month or datetime.now().month
        self._on_change = on_change

        self._btn = tk.Button(
            self,
            text=self._format(),
            command=self._open,
            bg="#F8FAFC", fg=THEME["text_main"],
            font=("Segoe UI Semibold", 11),
            bd=0, cursor="hand2",
            activebackground="#EEF2FF",
            padx=14, pady=7,
            highlightbackground=THEME["border"], highlightthickness=1)
        self._btn.pack(fill="x")

        self._btn.bind("<Enter>",
                       lambda e: self._btn.config(bg="#EEF2FF"))
        self._btn.bind("<Leave>",
                       lambda e: self._btn.config(bg="#F8FAFC"))

    def _format(self):
        mn = self.MONTH_NAMES[self.sel_month]
        return f"  📆  {mn}  {self.sel_year}  ▾  "

    def _open(self):
        MonthYearPopup(self._btn, self.sel_year, self.sel_month, self._picked)

    def _picked(self, year, month):
        self.sel_year = year
        self.sel_month = month
        self._btn.config(text=self._format())
        if self._on_change:
            self._on_change(year, month)

    def get_year(self):
        return str(self.sel_year)

    def get_month(self):
        return f"{self.sel_month:02d}"

    def set(self, year, month):
        self.sel_year = year
        self.sel_month = month
        self._btn.config(text=self._format())



def enable_smooth_scroll(canvas):
    """
    Patch an existing tk.Canvas to have robust smooth scrolling.
    Handles high-precision touchpads and both directions (Up/Down).
    """

    canvas._v = 0.0      # Velocity
    canvas._acc = 0.0    # Fractional accumulator
    canvas._running = False

    def _on_mousewheel(event):
        # Determine delta
        delta = 0
        if hasattr(event, "num") and event.num in (4, 5):
            delta = -1 if event.num == 4 else 1
        elif hasattr(event, "delta") and event.delta:
            # Windows/macOS: delta + is Up, - is Down
            # We want delta -1 for Up, +1 for Down
            delta = -event.delta / 120.0
        
        if delta == 0:
            return

        # Add to velocity with higher sensitivity
        canvas._v += delta * 16.0
        
        if not canvas._running:
            canvas._running = True
            _animate()

    def _animate():
        try:
            # Check if we should stop
            if abs(canvas._v) < 0.05 and abs(canvas._acc) < 0.5:
                canvas._v = 0.0
                canvas._acc = 0.0
                canvas._running = False
                return

            # Apply velocity to accumulator
            canvas._acc += canvas._v
            
            # Use ROUNDING instead of truncation for symmetric behavior
            # This ensures Up (-0.6 -> -1) and Down (0.6 -> 1) work equally
            steps = int(round(canvas._acc))
            if steps != 0:
                canvas.yview_scroll(steps, "units")
                canvas._acc -= steps

            # Friction (decay) - slightly reduced for smoother finish
            canvas._v *= 0.8
            
            # Fast refresh for buttery smooth motion
            canvas.after(10, _animate)
        except:
            canvas._running = False

    # Bind to the canvas itself
    canvas.bind("<MouseWheel>", _on_mousewheel, add="+")
    canvas.bind("<Button-4>", _on_mousewheel, add="+")
    canvas.bind("<Button-5>", _on_mousewheel, add="+")

    def _bind_to_all(widget):
        try:
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            widget.bind("<Button-4>", _on_mousewheel, add="+")
            widget.bind("<Button-5>", _on_mousewheel, add="+")
        except:
            pass
        for child in widget.winfo_children():
            _bind_to_all(child)

    # Re-bind periodically to catch new widgets
    def _periodic():
        _bind_to_all(canvas)
        canvas.after(1500, _periodic)

    _periodic()

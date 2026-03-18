import sqlite3
import os
import shutil
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="dress_shop.db"):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # 1. Employees
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                emp_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                gender      TEXT,
                phone       TEXT,
                address     TEXT,
                designation TEXT,
                base_salary REAL NOT NULL DEFAULT 0,
                joining_date TEXT,
                photo_path  TEXT
            )
        ''')

        # 2. Attendance
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id           INTEGER NOT NULL,
                date             TEXT NOT NULL,
                status           TEXT NOT NULL DEFAULT 'A',
                permission_hours REAL DEFAULT 0,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
            )
        ''')
        # Add UNIQUE index if not exists (handles old DB without UNIQUE constraint)
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_att_emp_date
            ON attendance(emp_id, date)
        ''')

        # 3. Expenses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id     INTEGER NOT NULL,
                date       TEXT NOT NULL,
                reason     TEXT,
                amount     REAL NOT NULL DEFAULT 0,
                month_year TEXT NOT NULL,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
            )
        ''')

        # 4. Payroll
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payroll (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id         INTEGER NOT NULL,
                month_year     TEXT NOT NULL,
                payable_days   REAL DEFAULT 0,
                base_salary    REAL DEFAULT 0,
                one_day_salary REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                net_salary     REAL DEFAULT 0,
                calculated_at  TEXT,
                FOREIGN KEY (emp_id) REFERENCES employees(emp_id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_payroll_emp_month
            ON payroll(emp_id, month_year)
        ''')

        # 5. New Cashier Box Records
        cursor.execute('DROP TABLE IF EXISTS cashier_expenses')
        cursor.execute('DROP TABLE IF EXISTS cash_records')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cashier_records (
                date               TEXT PRIMARY KEY,
                opening_10         INTEGER DEFAULT 0,
                opening_20         INTEGER DEFAULT 0,
                opening_50         INTEGER DEFAULT 0,
                opening_100        INTEGER DEFAULT 0,
                opening_200        INTEGER DEFAULT 0,
                closing_10         INTEGER DEFAULT 0,
                closing_20         INTEGER DEFAULT 0,
                closing_50         INTEGER DEFAULT 0,
                closing_100        INTEGER DEFAULT 0,
                closing_200        INTEGER DEFAULT 0,
                total_sales        REAL DEFAULT 0,
                cash_received_500  REAL DEFAULT 0,
                upi_gpay           REAL DEFAULT 0,
                expenses           REAL DEFAULT 0,
                total1             REAL DEFAULT 0,
                total2             REAL DEFAULT 0,
                shortage           REAL DEFAULT 0,
                finalized_amount   REAL DEFAULT 0,
                opening_cash       REAL DEFAULT 0,
                gpay_sales         REAL DEFAULT 0,
                taken_500          REAL DEFAULT 0,
                actual_cash        REAL DEFAULT 0,
                cash_sales         REAL DEFAULT 0,
                expected_cash      REAL DEFAULT 0,
                difference         REAL DEFAULT 0,
                next_opening_cash  REAL DEFAULT 0
            )
        ''')

        # 6. Backup Logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT,
                backup_path TEXT,
                status      TEXT
            )
        ''')

        conn.commit()

        # ── MIGRATIONS: add columns to old databases ──────────────────────────
        self._migrate(cursor, conn)

        conn.commit()
        conn.close()

    def _migrate(self, cursor, conn):
        """Safely add new columns to existing tables if they don't exist yet."""
        def add_col(table, col, typedef):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")
                conn.commit()
            except Exception:
                pass  # column already exists

        # cashier_records: no migrations needed for fresh start
        add_col("cashier_records", "opening_cash", "REAL DEFAULT 0")
        add_col("cashier_records", "gpay_sales", "REAL DEFAULT 0")
        add_col("cashier_records", "taken_500", "REAL DEFAULT 0")
        add_col("cashier_records", "actual_cash", "REAL DEFAULT 0")
        add_col("cashier_records", "cash_sales", "REAL DEFAULT 0")
        add_col("cashier_records", "expected_cash", "REAL DEFAULT 0")
        add_col("cashier_records", "difference", "REAL DEFAULT 0")
        add_col("cashier_records", "next_opening_cash", "REAL DEFAULT 0")

        # employees: ensure all columns exist
        add_col("employees", "designation", "TEXT")
        add_col("employees", "address",     "TEXT")

    # ── Payroll computation ───────────────────────────────────────────────────
    def compute_payroll(self, emp_id, month_year):
        """(Re)compute & upsert payroll for one employee for one month (MM-YYYY)."""
        parts = month_year.split("-")
        mm, yyyy = parts[0], parts[1]
        date_pattern = f"{yyyy}-{mm}%"

        conn = self.get_connection()
        cur  = conn.cursor()

        cur.execute("SELECT base_salary FROM employees WHERE emp_id=?", (emp_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return
        base_salary = row["base_salary"]

        cur.execute(
            "SELECT SUM(CASE "
            "  WHEN status IN ('P','PL','PP') THEN 1 "
            "  WHEN status = 'HD' THEN 0.5 "
            "  ELSE 0 END) AS cnt FROM attendance "
            "WHERE emp_id=? AND date LIKE ?",
            (emp_id, date_pattern)
        )
        row = cur.fetchone()
        payable_days = row["cnt"] if row["cnt"] is not None else 0

        # Calculate penalty based on permission hours (1 day absent per 12 hours)
        cur.execute(
            "SELECT COALESCE(SUM(permission_hours), 0) AS tot_perm FROM attendance "
            "WHERE emp_id=? AND date LIKE ?",
            (emp_id, date_pattern)
        )
        tot_perm = cur.fetchone()["tot_perm"]
        penalty_days = int(tot_perm // 12)
        payable_days = max(0, payable_days - penalty_days)

        cur.execute(
            "SELECT COALESCE(SUM(amount),0) AS tot FROM expenses "
            "WHERE emp_id=? AND month_year=?",
            (emp_id, month_year)
        )
        total_expenses = cur.fetchone()["tot"]

        one_day_salary = base_salary / 30.0
        net_salary     = (payable_days * one_day_salary) - total_expenses
        now_str        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Use INSERT OR REPLACE via the unique index
        cur.execute(
            "SELECT id FROM payroll WHERE emp_id=? AND month_year=?",
            (emp_id, month_year)
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                '''UPDATE payroll SET payable_days=?, base_salary=?, one_day_salary=?,
                                     total_expenses=?, net_salary=?, calculated_at=?
                   WHERE id=?''',
                (payable_days, base_salary, one_day_salary,
                 total_expenses, net_salary, now_str, existing["id"])
            )
        else:
            cur.execute(
                '''INSERT INTO payroll
                   (emp_id, month_year, payable_days, base_salary, one_day_salary,
                    total_expenses, net_salary, calculated_at)
                   VALUES (?,?,?,?,?,?,?,?)''',
                (emp_id, month_year, payable_days, base_salary,
                 one_day_salary, total_expenses, net_salary, now_str)
            )
        conn.commit()
        conn.close()

    # ── Backup ────────────────────────────────────────────────────────────────
    def backup_database(self):
        try:
            import pandas as pd
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            # Create or update a single permanent Excel backup file
            dest = os.path.join(backup_dir, "dress_shop_backup.xlsx")
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get all table names in the database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]
            
            # Write each table to a different sheet in the Excel file
            with pd.ExcelWriter(dest, engine='openpyxl') as writer:
                for table in tables:
                    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                    df.to_excel(writer, sheet_name=table, index=False)
            
            # Log the successful backup
            conn.execute(
                "INSERT INTO backup_logs (timestamp, backup_path, status) VALUES (?,?,?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), dest, "Success")
            )
            conn.commit()
            conn.close()
            return True, dest
        except PermissionError:
            return False, "The Excel backup file is currently open in another program (like Microsoft Excel).\n\nPlease CLOSE the Excel file and try backing up again!"
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    db = DatabaseManager()
    print("Database ready:", db.db_path)

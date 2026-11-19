import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH

class DataManager:
    def __init__(self):
        self._init()

    def _connect(self):
        return sqlite3.connect(DB_PATH)

    def _init(self):
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, waktu TEXT, survey TEXT, period TEXT,
                status TEXT, total_open INTEGER, jumlah_diambil INTEGER, validasi TEXT, error TEXT
            )""")
            con.execute("""CREATE TABLE IF NOT EXISTS master_data (
                row_json TEXT NOT NULL
            )""")

    def load_master(self):
        with self._connect() as con:
            rows = con.execute("SELECT row_json FROM master_data").fetchall()
        if not rows:
            return pd.DataFrame()
        import json
        return pd.DataFrame([json.loads(x[0]) for x in rows])

    def replace_master(self, df):
        import json
        records = df.where(pd.notna(df), None).to_dict(orient="records")
        with self._connect() as con:
            con.execute("DELETE FROM master_data")
            con.executemany("INSERT INTO master_data(row_json) VALUES (?)",
                            [(json.dumps(r, ensure_ascii=False, default=str),) for r in records])

    def add_log(self, survey, period, status, total, taken, validation, error):
        with self._connect() as con:
            con.execute("""INSERT INTO sync_logs
            (waktu,survey,period,status,total_open,jumlah_diambil,validasi,error)
            VALUES (?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(timespec="seconds"), survey, period, status, total, taken, validation, error))

    def load_logs(self):
        with self._connect() as con:
            return pd.read_sql_query("SELECT * FROM sync_logs ORDER BY id DESC", con)

    def latest_sync(self):
        logs = self.load_logs()
        if logs.empty:
            return None
        return str(logs.iloc[0]["waktu"])

def import_records(self, df):
    """Merge user-collected page rows, preserving unique assignment rows."""
    existing = self.load_master()
    combined = pd.concat([existing, df], ignore_index=True) if not existing.empty else df.copy()
    key = "ID Assignment" if "ID Assignment" in combined.columns else ("ID SBR" if "ID SBR" in combined.columns else None)
    if key:
        combined = combined.drop_duplicates(subset=[key], keep="last")
    else:
        combined = combined.drop_duplicates(keep="last")
    self.replace_master(combined)
    return len(combined)

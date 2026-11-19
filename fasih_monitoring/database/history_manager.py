import sqlite3
import pandas as pd
from datetime import datetime
from config import DB_PATH

class HistoryManager:
    def __init__(self):
        with sqlite3.connect(DB_PATH) as con:
            con.execute('''CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id TEXT, sbr_id TEXT,
                business_name TEXT, region TEXT, status TEXT, captured_at TEXT
            )''')

    def record_snapshot(self, df):
        # Catat assignment baru atau perubahan status saja; snapshot berulang tidak menambah histori.
        with sqlite3.connect(DB_PATH) as con:
            for _, row in df.iterrows():
                assignment = str(row.get("ID Assignment", row.get("ID SBR", "")))
                if not assignment or assignment == "nan":
                    assignment = str(row.get("Nama Komersial", "")) + "|" + str(row.get("Alamat", ""))
                status = str(row.get("Status Assignment", "OPEN"))
                previous = con.execute(
                    "SELECT status FROM status_history WHERE assignment_id=? ORDER BY id DESC LIMIT 1",
                    (assignment,)
                ).fetchone()
                if previous is None or previous[0] != status:
                    con.execute('''INSERT INTO status_history
                        (assignment_id,sbr_id,business_name,region,status,captured_at)
                        VALUES (?,?,?,?,?,?)''',
                        (assignment, str(row.get("ID SBR","")), str(row.get("Nama Komersial","")),
                         str(row.get("Kabupaten/Kota","")), status, datetime.now().isoformat(timespec="seconds")))

    def load(self):
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query("SELECT * FROM status_history ORDER BY id DESC", con)

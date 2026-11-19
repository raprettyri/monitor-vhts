import sqlite3
import json
import pandas as pd
from datetime import datetime
from config import DB_PATH


class HistoryManager:
    def __init__(self):
        with sqlite3.connect(DB_PATH) as con:
            con.execute('''CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id TEXT, sbr_id TEXT, business_name TEXT,
                region TEXT, status TEXT, captured_at TEXT
            )''')
            con.execute('''CREATE TABLE IF NOT EXISTS snapshot_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL, survey TEXT, period TEXT,
                total_open INTEGER, wilayah_json TEXT, unknown_count INTEGER
            )''')

    def record_snapshot(self, df):
        # Catat assignment baru/perubahan status (log detail lama tetap dipertahankan).
        with sqlite3.connect(DB_PATH) as con:
            for _, row in df.iterrows():
                assignment = str(row.get("ID Assignment", row.get("Kode Identitas", row.get("ID SBR", ""))))
                if not assignment or assignment == "nan":
                    assignment = str(row.get("Nama Komersial", "")) + "|" + str(row.get("Alamat", ""))
                status = str(row.get("Status Assignment", "OPEN"))
                previous = con.execute(
                    "SELECT status FROM status_history WHERE assignment_id=? ORDER BY id DESC LIMIT 1",
                    (assignment,),
                ).fetchone()
                if previous is None or previous[0] != status:
                    con.execute('''INSERT INTO status_history
                        (assignment_id,sbr_id,business_name,region,status,captured_at)
                        VALUES (?,?,?,?,?,?)''',
                        (assignment, str(row.get("ID SBR", "")),
                         str(row.get("Nama Komersial", "")),
                         str(row.get("Kabupaten/Kota", "")), status,
                         datetime.now().isoformat(timespec="seconds")))

    def record_snapshot_summary(self, df, survey, period):
        counts = {}
        if "Kabupaten/Kota" in df.columns:
            counts = df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI").value_counts().to_dict()
        unknown = int(counts.get("BELUM TERIDENTIFIKASI", 0))
        with sqlite3.connect(DB_PATH) as con:
            con.execute('''INSERT INTO snapshot_history
                (captured_at,survey,period,total_open,wilayah_json,unknown_count)
                VALUES (?,?,?,?,?,?)''',
                (datetime.now().isoformat(timespec="seconds"), survey, period,
                 int(len(df)), json.dumps(counts, ensure_ascii=False), unknown))


    def load_snapshots(self):
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query(
                """
                SELECT
                    captured_at AS Waktu,
                    survey AS Survei,
                    period AS Periode,
                    total_open AS Total_OPEN,
                    unknown_count AS Belum_Teridentifikasi
                FROM snapshot_history
                ORDER BY id DESC
                """,
                con
            )


    def load(self):
        with sqlite3.connect(DB_PATH) as con:
            return pd.read_sql_query("SELECT * FROM status_history ORDER BY id DESC", con)

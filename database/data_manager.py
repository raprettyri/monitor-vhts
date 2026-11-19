import sqlite3
import json
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT, survey TEXT, period TEXT, status TEXT,
                total_open INTEGER, jumlah_diambil INTEGER,
                validasi TEXT, error TEXT
            )""")
            con.execute("CREATE TABLE IF NOT EXISTS master_data (row_json TEXT NOT NULL)")

    def load_master(self):
        with self._connect() as con:
            rows = con.execute("SELECT row_json FROM master_data").fetchall()
        return pd.DataFrame([json.loads(x[0]) for x in rows]) if rows else pd.DataFrame()

    def replace_master(self, df):
        records = df.where(pd.notna(df), None).to_dict(orient="records")
        with self._connect() as con:
            con.execute("DELETE FROM master_data")
            con.executemany(
                "INSERT INTO master_data(row_json) VALUES (?)",
                [(json.dumps(r, ensure_ascii=False, default=str),) for r in records],
            )

    @staticmethod
    def _identity(row):
        # ID Assignment adalah identitas paling spesifik. Jika tidak ada,
        # gunakan ID SBR; terakhir gunakan kombinasi nama usaha dan alamat.
        for col in ("ID Assignment", "Kode Identitas", "ID SBR"):
            val = str(row.get(col, "")).strip()
            if val and val.lower() not in ("nan", "none", "-"):
                return f"{col}:{val}"
        return (
            "BIZ:"
            + str(row.get("Nama Komersial", "")).strip().lower()
            + "|"
            + str(row.get("Alamat", "")).strip().lower()
        )

    def replace_import(self, df, survey, period, source_files):
        """Replace snapshot untuk survei+periode terpilih; periode lain tetap dipertahankan."""
        incoming = df.copy()
        incoming["Nama Survei"] = survey
        incoming["Periode"] = period
        imported_at = datetime.now().isoformat(timespec="seconds")
        incoming["Waktu Scraping"] = imported_at

        # Hilangkan duplikat di dalam batch upload; baris terakhir dipakai.
        incoming["_dedup_key"] = incoming.apply(self._identity, axis=1)
        incoming = incoming.drop_duplicates(subset=["_dedup_key"], keep="last")
        incoming = incoming.drop(columns=["_dedup_key"])

        existing = self.load_master()
        if not existing.empty:
            # Jangan sentuh data survei/periode lain.
            keep = ~(
                existing.get("Nama Survei", pd.Series(index=existing.index, dtype=str)).eq(survey)
                & existing.get("Periode", pd.Series(index=existing.index, dtype=str)).eq(period)
            )
            preserved = existing.loc[keep].copy()
            combined = pd.concat([preserved, incoming], ignore_index=True)
        else:
            combined = incoming

        self.replace_master(combined)
        self.add_log(
            survey,
            period,
            "BERHASIL DIPERBARUI (REPLACE SNAPSHOT)",
            len(incoming),
            len(incoming),
            f"Snapshot menggantikan data aktif. File: {', '.join(source_files)}",
            "",
        )
        return len(incoming), len(combined)

    def reset_period(self, survey, period):
        """Hapus data aktif hanya untuk survei dan periode yang dipilih."""
        existing = self.load_master()
        if existing.empty:
            removed = 0
        else:
            survey_col = existing.get("Nama Survei", pd.Series(index=existing.index, dtype=str))
            period_col = existing.get("Periode", pd.Series(index=existing.index, dtype=str))
            target = survey_col.eq(survey) & period_col.eq(period)
            removed = int(target.sum())
            self.replace_master(existing.loc[~target].copy())

        self.add_log(
            survey, period, "RESET DATA AKTIF", removed, 0,
            "Data aktif periode dihapus oleh pengguna; riwayat snapshot tetap disimpan.", ""
        )
        return removed

    def add_log(self, survey, period, status, total, taken, validation, error):
        with self._connect() as con:
            con.execute(
                """INSERT INTO sync_logs
                (waktu,survey,period,status,total_open,jumlah_diambil,validasi,error)
                VALUES (?,?,?,?,?,?,?,?)""",
                (datetime.now().isoformat(timespec="seconds"), survey, period,
                 status, total, taken, validation, error),
            )

    def load_logs(self):
        with self._connect() as con:
            return pd.read_sql_query("SELECT * FROM sync_logs ORDER BY id DESC", con)

    def latest_sync(self):
        logs = self.load_logs()
        return str(logs.iloc[0]["waktu"]) if not logs.empty else None

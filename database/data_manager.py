import json
from datetime import datetime

import pandas as pd

from config import get_worksheet


MASTER_HEADERS = ["row_json"]
LOG_HEADERS = [
    "id", "waktu", "survey", "period", "status", "total_open",
    "jumlah_diambil", "validasi", "error",
]


def _clean_value(value):
    """Ubah nilai pandas/numpy menjadi nilai JSON yang aman."""
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


class DataManager:
    """Pengganti DataManager SQLite dengan Google Sheets.

    Nama method dan bentuk hasilnya dipertahankan agar pemanggilan dari app.py
    yang sudah ada tetap kompatibel.
    """

    def __init__(self):
        self.master_ws = get_worksheet("MASTER_DATA", MASTER_HEADERS)
        self.logs_ws = get_worksheet("LOG_UPDATE", LOG_HEADERS)

    def load_master(self):
        values = self.master_ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame()

        records = []
        for row in values[1:]:
            if not row or not row[0].strip():
                continue
            try:
                records.append(json.loads(row[0]))
            except (json.JSONDecodeError, TypeError):
                # Jangan diam-diam mengabaikan data rusak.
                raise RuntimeError(
                    "Ada baris row_json yang tidak valid pada tab MASTER_DATA. "
                    "Periksa data sebelum melakukan upload ulang."
                )
        return pd.DataFrame(records) if records else pd.DataFrame()

    def replace_master(self, df):
        """Ganti seluruh isi MASTER_DATA dengan DataFrame yang diberikan."""
        if df is None:
            df = pd.DataFrame()

        records = []
        if not df.empty:
            safe_df = df.astype(object).where(pd.notna(df), None)
            records = safe_df.to_dict(orient="records")

        rows = [["row_json"]]
        rows.extend([
            [json.dumps(
                {key: _clean_value(value) for key, value in record.items()},
                ensure_ascii=False,
                default=str,
            )]
            for record in records
        ])

        # Satu kali clear lalu tulis ulang agar data snapshot tidak bertumpuk.
        self.master_ws.clear()
        self.master_ws.update(values=rows, range_name="A1", value_input_option="RAW")

    @staticmethod
    def _identity(row):
        # ID Assignment paling spesifik; fallback mengikuti implementasi lama.
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
        """Ganti snapshot hanya untuk kombinasi survei dan periode terpilih."""
        incoming = df.copy()
        incoming["Nama Survei"] = survey
        incoming["Periode"] = period
        imported_at = datetime.now().isoformat(timespec="seconds")
        incoming["Waktu Scraping"] = imported_at

        incoming["_dedup_key"] = incoming.apply(self._identity, axis=1)
        incoming = incoming.drop_duplicates(subset=["_dedup_key"], keep="last")
        incoming = incoming.drop(columns=["_dedup_key"])

        existing = self.load_master()
        if not existing.empty:
            survey_col = existing.get("Nama Survei", pd.Series(index=existing.index, dtype=str))
            period_col = existing.get("Periode", pd.Series(index=existing.index, dtype=str))
            keep = ~(survey_col.eq(survey) & period_col.eq(period))
            combined = pd.concat([existing.loc[keep].copy(), incoming], ignore_index=True)
        else:
            combined = incoming

        # Simpan snapshot baru dahulu. Jika penulisan gagal, exception diteruskan
        # sehingga app.py dapat menampilkan pesan gagal, bukan sukses palsu.
        self.replace_master(combined)
        source_names = ", ".join(source_files or [])
        self.add_log(
            survey,
            period,
            "BERHASIL DIPERBARUI (REPLACE SNAPSHOT)",
            len(incoming),
            len(incoming),
            f"Snapshot menggantikan data aktif. File: {source_names}",
            "",
        )
        return len(incoming), len(combined)

    def reset_period(self, survey, period):
        """Hapus data aktif hanya untuk survei dan periode terpilih."""
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
            survey,
            period,
            "RESET DATA AKTIF",
            removed,
            0,
            "Data aktif periode dihapus oleh pengguna; riwayat snapshot tetap disimpan.",
            "",
        )
        return removed

    def add_log(self, survey, period, status, total, taken, validation, error):
        current = self.load_logs()
        next_id = int(current["id"].max()) + 1 if not current.empty else 1
        self.logs_ws.append_row(
            [
                next_id,
                datetime.now().isoformat(timespec="seconds"),
                survey,
                period,
                status,
                total,
                taken,
                validation,
                error,
            ],
            value_input_option="RAW",
        )

    def load_logs(self):
        values = self.logs_ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=LOG_HEADERS)
        df = pd.DataFrame(values[1:], columns=LOG_HEADERS)
        for col in ("id", "total_open", "jumlah_diambil"):
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df.sort_values("id", ascending=False).reset_index(drop=True)

    def latest_sync(self):
        logs = self.load_logs()
        return str(logs.iloc[0]["waktu"]) if not logs.empty else None

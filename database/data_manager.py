import json
import time
from datetime import datetime

import pandas as pd

from config import get_worksheet

MASTER_HEADERS = ["row_json"]
LOG_HEADERS = [
    "id", "waktu", "survey", "period", "status", "total_open",
    "jumlah_diambil", "validasi", "error",
]

CACHE_TTL_SECONDS = 45


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


def _retry_api(call, *args, **kwargs):
    """Retry terbatas untuk throttling sementara dari Google Sheets API."""
    delays = (2, 4, 8, 15)
    for attempt in range(len(delays) + 1):
        try:
            return call(*args, **kwargs)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # gspread.APIError pada beberapa versi menyimpan code di exc.code.
            if status is None:
                status = getattr(exc, "code", None)
            if status not in (429, 500, 502, 503, 504) or attempt == len(delays):
                raise
            time.sleep(delays[attempt])


class DataManager:
    """Google Sheets backend dengan cache pendek untuk mengurangi read requests."""

    def __init__(self):
        self.master_ws = get_worksheet("MASTER_DATA", MASTER_HEADERS)
        self.logs_ws = get_worksheet("LOG_UPDATE", LOG_HEADERS)
        self._master_cache = None
        self._master_cache_at = 0.0
        self._logs_cache = None
        self._logs_cache_at = 0.0

    def _invalidate_master(self):
        self._master_cache = None
        self._master_cache_at = 0.0

    def _invalidate_logs(self):
        self._logs_cache = None
        self._logs_cache_at = 0.0

    def load_master(self, force_refresh=False):
        now = time.monotonic()
        if (
            not force_refresh
            and self._master_cache is not None
            and now - self._master_cache_at < CACHE_TTL_SECONDS
        ):
            return self._master_cache.copy(deep=True)

        values = _retry_api(self.master_ws.get_all_values)
        if len(values) <= 1:
            result = pd.DataFrame()
        else:
            records = []
            for row in values[1:]:
                if not row or not row[0].strip():
                    continue
                try:
                    records.append(json.loads(row[0]))
                except (json.JSONDecodeError, TypeError):
                    raise RuntimeError(
                        "Ada baris row_json yang tidak valid pada tab MASTER_DATA. "
                        "Periksa data sebelum melakukan upload ulang."
                    )
            result = pd.DataFrame(records) if records else pd.DataFrame()

        self._master_cache = result.copy(deep=True)
        self._master_cache_at = time.monotonic()
        return result

    def replace_master(self, df):
        """Ganti MASTER_DATA; cache dibersihkan hanya setelah penulisan berhasil."""
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

        # Tulis seluruh kolom A dalam SATU permintaan update.
        # Baris kosong di belakang menghapus sisa snapshot lama tanpa clear() terpisah.
        # Dengan demikian, kegagalan update tidak didahului pengosongan sheet.
        target_rows = max(int(self.master_ws.row_count), len(rows))
        if target_rows > int(self.master_ws.row_count):
            _retry_api(self.master_ws.resize, rows=target_rows)

        padded_rows = rows + [[""]] * (target_rows - len(rows))
        _retry_api(
            self.master_ws.update,
            values=padded_rows,
            range_name=f"A1:A{target_rows}",
            value_input_option="RAW",
        )
        self._invalidate_master()

    @staticmethod
    def _identity(row):
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
        incoming = df.copy()
        incoming["Nama Survei"] = survey
        incoming["Periode"] = period
        incoming["Waktu Scraping"] = datetime.now().isoformat(timespec="seconds")

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
        _retry_api(
            self.logs_ws.append_row,
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
        self._invalidate_logs()

    def load_logs(self, force_refresh=False):
        now = time.monotonic()
        if (
            not force_refresh
            and self._logs_cache is not None
            and now - self._logs_cache_at < CACHE_TTL_SECONDS
        ):
            return self._logs_cache.copy(deep=True)

        values = _retry_api(self.logs_ws.get_all_values)
        if len(values) <= 1:
            result = pd.DataFrame(columns=LOG_HEADERS)
        else:
            result = pd.DataFrame(values[1:], columns=LOG_HEADERS)
            for col in ("id", "total_open", "jumlah_diambil"):
                result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)
            result = result.sort_values("id", ascending=False).reset_index(drop=True)

        self._logs_cache = result.copy(deep=True)
        self._logs_cache_at = time.monotonic()
        return result

    def latest_sync(self):
        logs = self.load_logs()
        return str(logs.iloc[0]["waktu"]) if not logs.empty else None

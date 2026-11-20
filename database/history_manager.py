import json
import time
from datetime import datetime

import pandas as pd

from config import get_worksheet


STATUS_HEADERS = [
    "id", "assignment_id", "sbr_id", "business_name", "region", "status", "captured_at"
]
SNAPSHOT_HEADERS = [
    "id", "captured_at", "survey", "period", "total_open", "wilayah_json", "unknown_count"
]

CACHE_TTL_SECONDS = 45


def _retry_api(call, *args, **kwargs):
    delays = (2, 4, 8, 15)
    for attempt in range(len(delays) + 1):
        try:
            return call(*args, **kwargs)
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is None:
                status = getattr(exc, "code", None)
            if status not in (429, 500, 502, 503, 504) or attempt == len(delays):
                raise
            time.sleep(delays[attempt])


class HistoryManager:
    """Penyimpanan riwayat status dan snapshot pada Google Sheets."""

    def __init__(self):
        self.status_ws = get_worksheet("HISTORI_STATUS", STATUS_HEADERS)
        self.snapshot_ws = get_worksheet("SNAPSHOT_HISTORY", SNAPSHOT_HEADERS)
        self._status_cache = None
        self._status_cache_at = 0.0
        self._snapshot_cache = None
        self._snapshot_cache_at = 0.0

    @staticmethod
    def _records(worksheet, headers):
        values = _retry_api(worksheet.get_all_values)
        if len(values) <= 1:
            return []
        return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:] if any(row)]

    def _load_status_records(self, force_refresh=False):
        now = time.monotonic()
        if not force_refresh and self._status_cache is not None and now - self._status_cache_at < CACHE_TTL_SECONDS:
            return [dict(row) for row in self._status_cache]
        records = self._records(self.status_ws, STATUS_HEADERS)
        self._status_cache = [dict(row) for row in records]
        self._status_cache_at = time.monotonic()
        return records

    def _load_snapshot_records(self, force_refresh=False):
        now = time.monotonic()
        if not force_refresh and self._snapshot_cache is not None and now - self._snapshot_cache_at < CACHE_TTL_SECONDS:
            return [dict(row) for row in self._snapshot_cache]
        records = self._records(self.snapshot_ws, SNAPSHOT_HEADERS)
        self._snapshot_cache = [dict(row) for row in records]
        self._snapshot_cache_at = time.monotonic()
        return records

    def record_snapshot(self, df):
        """Catat assignment baru/perubahan status; riwayat sebelumnya dipertahankan."""
        existing = self._load_status_records()
        latest_status = {}
        max_id = 0
        for record in existing:
            assignment = str(record.get("assignment_id", ""))
            try:
                max_id = max(max_id, int(record.get("id") or 0))
            except (TypeError, ValueError):
                pass
            if assignment:
                # Baris terakhir pada sheet adalah catatan terbaru untuk ID tersebut.
                latest_status[assignment] = str(record.get("status", ""))

        captured_at = datetime.now().isoformat(timespec="seconds")
        new_rows = []
        for _, row in df.iterrows():
            assignment = str(
                row.get("ID Assignment", row.get("Kode Identitas", row.get("ID SBR", "")))
            ).strip()
            if not assignment or assignment.lower() in ("nan", "none"):
                assignment = str(row.get("Nama Komersial", "")) + "|" + str(row.get("Alamat", ""))

            status = str(row.get("Status Assignment", "OPEN"))
            if latest_status.get(assignment) != status:
                max_id += 1
                new_rows.append([
                    max_id,
                    assignment,
                    str(row.get("ID SBR", "")),
                    str(row.get("Nama Komersial", "")),
                    str(row.get("Kabupaten/Kota", "")),
                    status,
                    captured_at,
                ])
                latest_status[assignment] = status

        if new_rows:
            _retry_api(self.status_ws.append_rows, new_rows, value_input_option="RAW")
            self._status_cache = None
            self._status_cache_at = 0.0

    def record_snapshot_summary(self, df, survey, period):
        counts = {}
        if "Kabupaten/Kota" in df.columns:
            counts = (
                df["Kabupaten/Kota"]
                .fillna("BELUM TERIDENTIFIKASI")
                .replace("", "BELUM TERIDENTIFIKASI")
                .value_counts()
                .to_dict()
            )
        unknown = int(counts.get("BELUM TERIDENTIFIKASI", 0))

        existing = self._load_snapshot_records()
        max_id = 0
        for record in existing:
            try:
                max_id = max(max_id, int(record.get("id") or 0))
            except (TypeError, ValueError):
                pass

        _retry_api(self.snapshot_ws.append_row,
            [
                max_id + 1,
                datetime.now().isoformat(timespec="seconds"),
                survey,
                period,
                int(len(df)),
                json.dumps(counts, ensure_ascii=False),
                unknown,
            ],
            value_input_option="RAW",
        )
        self._snapshot_cache = None
        self._snapshot_cache_at = 0.0

    def load_snapshots(self):
        records = self._load_snapshot_records()
        if not records:
            return pd.DataFrame(columns=[
                "Waktu", "Survei", "Periode", "Total_OPEN", "Belum_Teridentifikasi"
            ])
        df = pd.DataFrame(records)
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0)
        df["total_open"] = pd.to_numeric(df["total_open"], errors="coerce").fillna(0).astype(int)
        df["unknown_count"] = pd.to_numeric(df["unknown_count"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values("id", ascending=False)
        return df.rename(columns={
            "captured_at": "Waktu",
            "survey": "Survei",
            "period": "Periode",
            "total_open": "Total_OPEN",
            "unknown_count": "Belum_Teridentifikasi",
        })[["Waktu", "Survei", "Periode", "Total_OPEN", "Belum_Teridentifikasi"]].reset_index(drop=True)

    def load(self):
        records = self._load_status_records()
        if not records:
            return pd.DataFrame(columns=STATUS_HEADERS)
        df = pd.DataFrame(records)
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        return df.sort_values("id", ascending=False).reset_index(drop=True)

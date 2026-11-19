import json
from datetime import datetime

import pandas as pd

from config import get_worksheet


STATUS_HEADERS = [
    "id", "assignment_id", "sbr_id", "business_name", "region", "status", "captured_at"
]
SNAPSHOT_HEADERS = [
    "id", "captured_at", "survey", "period", "total_open", "wilayah_json", "unknown_count"
]


class HistoryManager:
    """Penyimpanan riwayat status dan snapshot pada Google Sheets."""

    def __init__(self):
        self.status_ws = get_worksheet("HISTORI_STATUS", STATUS_HEADERS)
        self.snapshot_ws = get_worksheet("SNAPSHOT_HISTORY", SNAPSHOT_HEADERS)

    @staticmethod
    def _records(worksheet, headers):
        values = worksheet.get_all_values()
        if len(values) <= 1:
            return []
        return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:] if any(row)]

    def record_snapshot(self, df):
        """Catat assignment baru/perubahan status; riwayat sebelumnya dipertahankan."""
        existing = self._records(self.status_ws, STATUS_HEADERS)
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
            self.status_ws.append_rows(new_rows, value_input_option="RAW")

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

        existing = self._records(self.snapshot_ws, SNAPSHOT_HEADERS)
        max_id = 0
        for record in existing:
            try:
                max_id = max(max_id, int(record.get("id") or 0))
            except (TypeError, ValueError):
                pass

        self.snapshot_ws.append_row(
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

    def load_snapshots(self):
        records = self._records(self.snapshot_ws, SNAPSHOT_HEADERS)
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
        records = self._records(self.status_ws, STATUS_HEADERS)
        if not records:
            return pd.DataFrame(columns=STATUS_HEADERS)
        df = pd.DataFrame(records)
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        return df.sort_values("id", ascending=False).reset_index(drop=True)

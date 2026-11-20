"""Konfigurasi aplikasi Monitoring OPEN VHTS 2026.

Penyimpanan utama menggunakan Google Sheets. Konfigurasi folder lokal tetap
tersedia agar modul lain (misalnya worker/status Playwright) tidak rusak.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
PROFILE_DIR = DATA_DIR / "playwright_profile"

# Dipertahankan untuk kompatibilitas modul lama. DataManager dan HistoryManager
# versi Google Sheets tidak lagi membaca/menulis file SQLite ini.
DB_PATH = DATA_DIR / "monitoring.sqlite3"
STATUS_PATH = DATA_DIR / "worker_status.json"
FASIH_URL = "https://fasih-sm.bps.go.id/"
DEFAULT_SURVEY = "VHTS 2026"
DEFAULT_PERIOD = "10 OKTOBER"

for folder in (DATA_DIR, LOG_DIR, PROFILE_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def _read_secret(name, default=None):
    """Baca Streamlit Secrets; fallback ke environment variable untuk lokal."""
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        if value is not None:
            return value
    except Exception:
        pass
    return os.environ.get(name, default)


def _build_spreadsheet():
    """Buat koneksi spreadsheet dari secrets."""
    import gspread

    spreadsheet_id = _read_secret("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise RuntimeError(
            "SPREADSHEET_ID belum diatur. Tambahkan ID spreadsheet pada "
            "Streamlit Secrets (atau environment variable lokal)."
        )

    credentials_info = None
    try:
        import streamlit as st
        credentials_info = dict(st.secrets["gcp_service_account"])
    except Exception:
        raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        if raw_json:
            import json
            credentials_info = json.loads(raw_json)

    if not credentials_info:
        raise RuntimeError(
            "Kredensial gcp_service_account belum ditemukan. Atur pada "
            ".streamlit/secrets.toml atau Streamlit Cloud > App settings > Secrets."
        )

    client = gspread.service_account_from_dict(credentials_info)
    return client.open_by_key(str(spreadsheet_id))


try:
    import streamlit as st
    get_spreadsheet = st.cache_resource(show_spinner=False)(_build_spreadsheet)
except Exception:
    get_spreadsheet = _build_spreadsheet


def get_worksheet(title, headers):
    """Ambil/buat worksheet dan pastikan header sesuai kontrak aplikasi."""
    import gspread

    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=max(1000, len(headers) + 1),
            cols=max(20, len(headers)),
        )

    current_headers = worksheet.row_values(1)
    if not current_headers:
        worksheet.update(values=[headers], range_name="A1")
    elif current_headers != list(headers):
        raise RuntimeError(
            f"Header tab '{title}' tidak sesuai. Header yang diharapkan: "
            f"{', '.join(headers)}. Header saat ini: {', '.join(current_headers)}. "
            "Periksa tab tersebut sebelum melanjutkan agar data tidak tertimpa."
        )
    return worksheet

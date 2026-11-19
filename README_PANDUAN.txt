MIGRASI DATABASE MONITORING OPEN VHTS 2026 KE GOOGLE SHEETS

File pengganti:
1. config.py
2. data_manager.py
3. history_manager.py

PENTING:
- Simpan salinan/backup tiga file lama sebelum mengganti.
- config.py mempertahankan DB_PATH, DATA_DIR, LOG_DIR, PROFILE_DIR,
  STATUS_PATH, FASIH_URL, DEFAULT_SURVEY, dan DEFAULT_PERIOD untuk kompatibilitas.
- DataManager dan HistoryManager versi ini tidak lagi memakai SQLite.
- Tab Google Sheets akan dibuat otomatis bila belum ada, dengan nama:
  MASTER_DATA, LOG_UPDATE, HISTORI_STATUS, SNAPSHOT_HISTORY.
- Jangan ubah nama/header tab setelah aplikasi mulai digunakan.

DEPENDENSI requirements.txt:
Tambahkan:
gspread>=6.1
google-auth>=2.0

SECRETS:
Tambahkan SPREADSHEET_ID dan [gcp_service_account] pada
.streamlit/secrets.toml (lokal) serta Streamlit Cloud > App settings > Secrets.

Catatan kompatibilitas:
Versi ini mempertahankan nama method yang ada pada file SQLite yang diberikan.
Sebelum deploy, jalankan tes lokal dan periksa apakah app.py memanggil method
lain di luar method yang dipertahankan tersebut.

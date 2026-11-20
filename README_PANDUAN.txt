PATCH MONITORING FASIH-SM — SEMUA STATUS

Isi patch:
- app.py: menerima snapshot seluruh status, menampilkan ringkasan status, rekap status per kabupaten/kota, grafik komposisi, dan filter status untuk detail.
- database/history_manager.py: label jumlah pada riwayat snapshot menjadi Total_Data (nama kolom worksheet lama tetap dipertahankan agar kompatibel).

CARA PAKAI:
1. Di FASIH-SM, buka Data dan ubah dropdown status dari OPEN menjadi SEMUA.
2. Unduh SELURUH halaman JSON untuk filter SEMUA. Jangan hanya unduh halaman pertama.
3. Di dashboard, upload seluruh JSON hasil pengambilan yang sama.
4. Centang konfirmasi dan klik "Ganti Snapshot Semua Status dengan Data Terbaru".
5. Periksa total dan rekap per status setelah dashboard refresh.

PENTING:
- Jangan upload satu status per satu sebagai proses pembaruan terpisah. Fungsi replace_import mengganti seluruh snapshot aktif untuk survei/periode tersebut. Jika upload OPEN lalu upload DRAFT, snapshot DRAFT akan menggantikan OPEN.
- Upload SEMUA satu kali agar seluruh status tersimpan bersama.
- Patch menerima URL FASIH dengan status=ALL, status=SEMUA, atau tanpa parameter status. File yang URL-nya secara eksplisit berisi status=OPEN / DRAFT / status tunggal akan ditolak untuk mencegah snapshot parsial.
- Kolom Status pada tabel JSON wajib ada. Baris tanpa status valid tidak diikutkan.
- MASTER_DATA dan riwayat yang sudah ada tidak perlu dihapus. Upload SEMUA pertama kali akan mengganti snapshot aktif survei/periode terpilih dengan seluruh status.
- Pertahankan file lain seperti config.py, database/data_manager.py, utils/, requirements.txt, dan .streamlit/secrets.toml yang sudah ada. Jangan commit secrets.toml ke GitHub.

FILE YANG DIGANTI:
- app.py
- database/history_manager.py

Tes sintaks Python: berhasil.
Koneksi ke Google Sheets dan format URL filter SEMUA harus diverifikasi saat deployment.

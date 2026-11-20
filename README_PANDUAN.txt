PATCH OPTIMASI GOOGLE SHEETS - MONITOR-VHTS

Isi paket:
- app.py
- config.py
- database/data_manager.py
- database/history_manager.py
- database/__init__.py

Tujuan:
1. Mengurangi pembacaan Google Sheets berulang saat Streamlit rerun.
2. Menyimpan objek manager/koneksi selama proses aplikasi hidup.
3. Cache pembacaan MASTER_DATA, LOG_UPDATE, HISTORI_STATUS, SNAPSHOT_HISTORY selama 45 detik.
4. Menghapus cache setelah data terkait berhasil ditulis.
5. Retry terbatas untuk HTTP 429/500/502/503/504.
6. Mengganti pola clear()+update() pada MASTER_DATA menjadi satu update kolom A
   yang juga menulis baris kosong di belakang, agar tidak ada langkah clear terpisah.

CARA MEMASANG:
1. Backup folder project/repository monitor-vhts terlebih dahulu.
2. Ganti file-file pada repository dengan file yang ada di paket ini:
   - app.py di folder utama
   - config.py di folder utama
   - data_manager.py di folder database
   - history_manager.py di folder database
   - pastikan database/__init__.py ada
3. Jangan mengubah Streamlit Secrets dan jangan mengunggah secrets.toml ke GitHub.
4. Commit dan push perubahan ke branch main.
5. Tunggu Streamlit Cloud selesai melakukan redeploy, lalu buka aplikasi.

CATATAN:
- Struktur worksheet dan header yang digunakan tetap sama.
- Cache berlaku paling lama 45 detik. Setelah upload/reset berhasil, cache yang
  bersangkutan langsung dibersihkan agar tampilan berikutnya membaca data terbaru.
- Jika masih terjadi 429, aplikasi mencoba ulang dengan jeda bertahap. Retry bukan
  pengganti kuota API; jika trafik tinggi, jeda cache dapat ditambah.
- Google Sheets tetap menjadi penyimpanan utama. Jangan hapus worksheet yang ada.
- Lakukan pengujian upload kecil/terkontrol setelah deploy. Jangan menguji dengan
  menghapus data produksi.

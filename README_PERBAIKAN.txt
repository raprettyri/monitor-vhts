PERBAIKAN KONTRAS DASHBOARD MONITOR-VHTS

Isi paket:
- app.py: versi dashboard dengan override CSS kontras lebih kuat dan warna Plotly eksplisit.
- .streamlit/config.toml: memaksa tema Streamlit menjadi light agar widget/tabel tidak memakai warna tema gelap.

Pemasangan:
1. Ekstrak ZIP.
2. Ganti app.py di root repository monitor-vhts.
3. Salin folder .streamlit ke root repository (gabungkan bila sudah ada; jangan hapus secrets.toml).
4. Jika .streamlit/config.toml sudah ada, backup dahulu lalu gabungkan pengaturan theme di atas. Jangan menimpa secrets.toml.
5. Commit dan push ke branch main.
6. Tunggu Streamlit redeploy, lalu hard refresh Ctrl+F5.

Tidak mengubah database, Google Sheets, mekanisme upload, reset, maupun histori.

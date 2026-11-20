PERBAIKAN KONTRAS TAMPILAN MONITOR-VHTS

Penyebab: warna teks sidebar dan area uploader mengikuti warna tema Streamlit/browser,
sementara latar belakang sudah dipaksa menjadi terang. Akibatnya teks menjadi pucat dan
sulit dibaca.

File dalam patch ini:
- app.py: CSS warna sidebar, label, selectbox, tombol, dan file uploader diperjelas.

Pemasangan:
1. Ekstrak ZIP.
2. Ganti app.py di repository monitor-vhts dengan app.py dari patch ini.
3. Commit dan push ke branch main melalui GitHub Desktop.
4. Tunggu Streamlit Cloud selesai redeploy, lalu refresh browser.

Tidak perlu mengubah Google Sheets, Secrets, atau file database.

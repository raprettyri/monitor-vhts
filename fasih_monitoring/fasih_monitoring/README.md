# Monitoring Progres Pendataan FASIH-SM — BPS Provinsi Aceh

Aplikasi lokal Streamlit + Playwright untuk memonitor data berstatus OPEN dari FASIH-SM.

## Status implementasi dan batasan

- Dashboard, database SQLite, ekspor Excel, log sinkronisasi, dan kerangka Playwright sudah disiapkan.
- Login SSO dilakukan manual oleh pengguna. Aplikasi tidak menyimpan password dan tidak melewati MFA/CAPTCHA.
- Struktur DOM FASIH-SM belum dapat diperiksa dari lingkungan pembuatan proyek ini. Karena itu, navigasi menggunakan locator berbasis teks/role sebagai titik awal dan akan berhenti dengan pesan yang jelas jika elemen tidak ditemukan.
- **Jangan menganggap scraper sudah tervalidasi terhadap situs produksi** sampai pengujian manual berhasil dan jumlah hasil sama dengan angka OPEN pada FASIH-SM.
- Pemetaan kabupaten/kota tidak ditebak dari alamat. Jika kolom wilayah belum ditemukan, data ditandai `BELUM TERIDENTIFIKASI`.
- Penyimpanan awal menggunakan SQLite lokal. Google Sheets dapat diaktifkan setelah kredensial layanan resmi disiapkan.

## Instalasi Windows

1. Ekstrak ZIP ke folder kerja, misalnya `C:\fasih_monitoring`.
2. Buka Command Prompt/PowerShell di folder tersebut.
3. Buat virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Instal dependensi dan browser:

```powershell
pip install -r requirements.txt
playwright install chromium
```

5. Jalankan aplikasi:

```powershell
streamlit run app.py
```

## Cara menggunakan

1. Klik **Login FASIH-SM** pada sidebar.
2. Chromium akan terbuka. Login manual melalui SSO BPS.
3. Setelah halaman FASIH-SM terbuka dan login selesai, worker mendeteksi halaman aplikasi dan menutup browser. Profil browser persisten disimpan lokal di `data/playwright_profile`.
4. Klik **Update Data Sekarang**.
5. Scraper membuka kembali profil browser, lalu mencoba memilih VHTS 2026 → 10 OKTOBER → Data → Status Assignment OPEN.
6. Periksa log dan validasi jumlah hasil terhadap angka OPEN di situs.

Jika login selesai tetapi worker belum mendeteksi status autentikasi, buka terminal tempat Streamlit berjalan dan periksa `logs/worker.log` serta `data/worker_status.json`.

## Inspeksi DOM

Sebelum mengandalkan scraping, jalankan:

```powershell
python -m scraper.inspect_fasih
```

Perintah ini membuka browser dengan profil persisten dan menyimpan snapshot DOM setelah login ke `logs/fasih_dom.html`. Buka file tersebut untuk memeriksa nama elemen, role, label, tabel, pagination, dan letak variabel wilayah. Jangan mengubah selector berdasarkan tebakan.

## Data dan keamanan

- Profil browser dan database disimpan di folder lokal `data/`.
- Jangan mengirim folder `data/playwright_profile` kepada orang lain.
- Jangan commit profil browser, database berisi data operasional, atau rahasia ke Git.
- Untuk komputer bersama, batasi akses akun Windows dan folder proyek.
- Gunakan hanya data yang memang boleh diakses dan diproses sesuai kebijakan BPS.

## Catatan teknis

FASIH-SM dapat mengubah struktur halaman, label, pagination, atau mekanisme pemuatan data. Bila locator tidak cocok, scraper akan berhenti; lakukan inspeksi DOM ulang lalu sesuaikan `scraper/navigation.py` dan `scraper/fasih_scraper.py`.

Google Sheets belum diaktifkan secara default. Untuk mengaktifkannya, siapkan service account resmi, berikan akses spreadsheet kepada akun layanan, simpan kredensial di lokasi aman, lalu implementasikan konektor di `database/google_sheets.py`.


## Mode koleksi dari Chrome biasa (tanpa otomasi browser)

Jika browser otomasi Playwright ditolak oleh halaman Bot Detected, gunakan kolektor yang dijalankan oleh pengguna di Chrome biasa:

1. Buka `chrome://extensions`.
2. Aktifkan **Developer mode**.
3. Klik **Load unpacked**.
4. Pilih folder `chrome_extension` di dalam project.
5. Buka FASIH-SM melalui Chrome biasa dan login seperti biasa.
6. Pilih VHTS 2026 → 10 OKTOBER → Data → Status Assignment → OPEN.
7. Klik ikon ekstensi **FASIH-SM Table Collector**, lalu klik **Ambil tabel halaman ini**.
8. Simpan file JSON yang diunduh.
9. Ulangi pada setiap halaman FASIH-SM (pindah halaman dilakukan manual).
10. Pada dashboard Streamlit, unggah semua JSON melalui bagian **Impor hasil koleksi Chrome**, lalu klik **Gabungkan hasil halaman**.

Mode ini tetap mengambil data dari tabel HTML yang dirender FASIH-SM (scraping DOM), tetapi dilakukan pada tab Chrome biasa atas tindakan eksplisit pengguna. Ekstensi tidak mengotomatiskan login, tidak mengubah fingerprint browser, tidak menembus proteksi, dan tidak mengklik pagination. Jika FASIH-SM memakai grid yang tidak terdeteksi oleh ekstensi, perlu inspeksi DOM dan penyesuaian selector yang sesuai.

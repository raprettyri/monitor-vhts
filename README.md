# FASIH-SM Monitoring — Mode Upload JSON

## Konsep penggunaan
Dashboard tidak lagi membuka browser, login SSO, atau menjalankan scraping Playwright. Pengguna melakukan login dan navigasi FASIH-SM secara manual di Chrome, mengambil tabel tiap halaman dengan ekstensi Chrome, lalu mengunggah semua JSON ke dashboard.

## Menjalankan dashboard
1. Instal Python 3.10+.
2. Buka folder project di VS Code.
3. Terminal: `py -m venv .venv`
4. Aktifkan: `.venv\Scripts\activate`
5. Instal: `pip install -r requirements.txt`
6. Jalankan: `streamlit run app.py`

## Memasang ekstensi Chrome
1. Buka `chrome://extensions`.
2. Aktifkan Developer mode.
3. Klik Load unpacked dan pilih folder `chrome_extension`.
4. Login FASIH-SM melalui Chrome biasa.
5. Pilih VHTS 2026 → 10 OKTOBER → Data → Status Assignment OPEN.
6. Pada setiap halaman tabel, klik ekstensi lalu Ambil tabel halaman ini. Simpan tiap file JSON.
7. Setelah semua halaman selesai, buka dashboard, pilih semua JSON sekaligus, centang konfirmasi survei/periode/status, lalu klik Proses dan tampilkan monitoring.

## Pengolahan data
- File JSON diperiksa sumber URL dan keberadaan tabel.
- Baris selain OPEN dibuang.
- Duplikasi digabung menggunakan ID Assignment, lalu ID SBR, atau nama usaha+alamat sebagai fallback.
- Data disimpan ke SQLite lokal. Impor berikutnya menggabungkan data dengan data lama untuk survei dan periode yang sama.
- Rekap 23 kabupaten/kota Aceh dibuat dari kolom wilayah bila tersedia, atau dicoba dikenali dari teks alamat. Baris yang tidak bisa dikenali ditandai BELUM TERIDENTIFIKASI agar tidak salah klasifikasi.
- Riwayat impor dan perubahan status disimpan.

## Catatan
Ekstensi hanya membaca tabel yang dirender pada tab FASIH-SM aktif setelah pengguna memilih filter OPEN. Pagination dilakukan manual: pindah halaman, lalu ambil JSON lagi. Pastikan semua halaman telah dikoleksi sebelum mengimpor. Angka OPEN pada badge dapat merupakan total keseluruhan, bukan jumlah per halaman; jangan menjumlahkannya berulang dari setiap file.


## Penentuan Kabupaten/Kota dari Kode Identitas

Dashboard memetakan wilayah dari **empat digit pertama kode identitas FASIH-SM**.
Contoh `11710300026711968-2fa32df0-0518-488f-8ca7-6045c1ec5b32` memiliki
prefix `1171`, sehingga dipetakan ke **Kota Banda Aceh**. Kolom `Kode Wilayah`
ditampilkan di detail data untuk memudahkan audit. Jika kode tidak dikenal,
aplikasi mencoba kolom kabupaten/kota atau alamat sebagai fallback.

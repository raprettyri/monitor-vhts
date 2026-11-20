PATCH TAMPILAN DASHBOARD MONITORING FASIH-SM

Isi paket:
- app.py: tampilan dashboard yang diperbarui.

Yang berubah:
1. Tema terang dengan palet biru BPS, aksen status, header gradasi, dan kartu ringkasan membulat.
2. Kartu status lebih ringkas dan tidak lagi membuat satu kartu melebar memenuhi satu baris.
3. Peringkat kabupaten/kota otomatis diurutkan dari jumlah terbesar ke terkecil.
4. Filter grafik: Semua status (total) atau satu status tertentu. Jika memilih OPEN, kabupaten/kota diurutkan berdasarkan jumlah OPEN terbanyak.
5. Grafik horizontal lebih rapi, hover menampilkan jumlah, dan klik segmen grafik menampilkan status, kabupaten/kota, serta jumlah assignment yang dipilih.
6. Fungsi upload, penggantian snapshot, Google Sheets, ekspor, dan riwayat tetap dipertahankan.

CARA MEMASANG:
- Ekstrak ZIP.
- Ganti app.py pada folder utama repository monitor-vhts.
- Jangan menghapus atau mengganti file lain.
- Commit dan Push ke branch main melalui GitHub Desktop.
- Tunggu Streamlit Community Cloud selesai redeploy.

CATATAN:
- Interaksi klik grafik menggunakan fitur seleksi Plotly pada Streamlit (tersedia pada Streamlit versi modern; requirements proyek sebelumnya menggunakan streamlit>=1.36).
- Klik salah satu segmen warna pada grafik untuk menampilkan jumlah status dan kabupaten/kota. Arahkan kursor untuk melihat rincian tooltip.

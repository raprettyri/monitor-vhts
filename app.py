import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from database.data_manager import DataManager
from database.history_manager import HistoryManager
from utils.wilayah import ACEH_REGENCIES, infer_wilayah, extract_kode_wilayah
from utils.export import make_excel


st.set_page_config(
    page_title="Monitoring FASIH-SM | BPS Aceh",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """<style>
    .block-container{padding-top:1.2rem;max-width:1550px}
    .main-title{font-size:1.8rem;font-weight:750;color:#07549a;margin:0}
    .sub-title{color:#64748b;margin-top:.2rem}
    .metric-card{background:#f4f8fc;border:1px solid #e3edf7;border-radius:12px;padding:14px 16px}
    .metric-label{font-size:.82rem;color:#64748b}
    .metric-value{font-size:1.7rem;font-weight:750;color:#0b4f8a}
    </style>""",
    unsafe_allow_html=True,
)


db = DataManager()
history = HistoryManager()

st.markdown(
    '<p class="main-title">MONITORING PROGRES PENDATAAN FASIH-SM</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-title">BPS PROVINSI ACEH · Monitoring status assignment OPEN</p>',
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR: FILTER DAN RESET DATA AKTIF
# ============================================================
with st.sidebar:
    st.subheader("Pengaturan Monitoring")
    survey = st.selectbox("Nama survei", ["VHTS 2026"], index=0)
    period = st.selectbox("Periode", ["10 OKTOBER"], index=0)
    st.caption("Periode FASIH-SM: 01–30 November 2026")

    st.divider()
    st.markdown("**Alur pembaruan data**")
    st.markdown(
        "1. Login FASIH-SM melalui Chrome.\n"
        "2. Pilih VHTS 2026 → 10 OKTOBER → Data → OPEN.\n"
        "3. Unduh JSON untuk seluruh halaman melalui ekstensi.\n"
        "4. Upload semua JSON terbaru di dashboard.\n"
        "5. Klik **Ganti Snapshot OPEN**."
    )
    st.info(
        "Dashboard tidak melakukan login atau scraping otomatis. "
        "Data diperbarui dari JSON yang diunduh manual."
    )

    st.divider()
    st.markdown("**Reset data aktif**")
    confirm_reset = st.checkbox(
        f"Saya yakin ingin menghapus data aktif {survey} – {period}",
        key="confirm_reset_active",
    )
    if st.button(
        "🗑️ Reset Data Aktif",
        disabled=not confirm_reset,
        use_container_width=True,
    ):
        removed = db.reset_period(survey, period)
        st.success(f"{removed} baris data aktif berhasil direset. Riwayat snapshot tetap disimpan.")
        st.rerun()


# ============================================================
# UPLOAD DAN GANTI SNAPSHOT
# ============================================================
st.subheader("Perbarui data OPEN")
st.write(
    "Upload seluruh file JSON dari semua halaman FASIH-SM untuk satu kali pengambilan. "
    "Data aktif survei/periode terpilih akan **diganti** dengan hasil terbaru, "
    "bukan ditambahkan ke data lama."
)

uploads = st.file_uploader(
    "Pilih semua file JSON hasil ekstensi Chrome",
    type=["json"],
    accept_multiple_files=True,
    key="json_upload",
)
confirmed = st.checkbox(
    "Saya memastikan semua file berasal dari FASIH-SM, survei VHTS 2026, "
    "periode 10 OKTOBER, status assignment OPEN, dan mencakup seluruh halaman.",
    key="confirm_snapshot",
)

if st.button(
    "🔄 Ganti Snapshot OPEN dengan Data Terbaru",
    type="primary",
    disabled=not uploads or not confirmed,
):
    try:
        imported = []
        rejected = []
        source_names = []

        for uploaded_file in uploads:
            try:
                payload = json.load(uploaded_file)
                url = str(payload.get("url", ""))

                if "fasih-sm.bps.go.id" not in url.lower():
                    rejected.append(f"{uploaded_file.name}: URL bukan FASIH-SM")
                    continue
                if payload.get("page_text_has_open_filter") is False:
                    rejected.append(f"{uploaded_file.name}: indikator filter OPEN tidak ditemukan")
                    continue
                if payload.get("page_text_has_survey") is False:
                    rejected.append(f"{uploaded_file.name}: survei VHTS 2026 tidak terdeteksi")
                    continue
                if payload.get("page_text_has_period") is False:
                    rejected.append(f"{uploaded_file.name}: periode 10 OKTOBER tidak terdeteksi")
                    continue

                tables = payload.get("tables", [])
                rows_in_file = 0
                for table in tables:
                    headers = table.get("headers", [])
                    for row in table.get("rows", []):
                        if len(headers) == len(row) and any(str(v).strip() for v in row):
                            imported.append(dict(zip(headers, row)))
                            rows_in_file += 1

                if rows_in_file:
                    source_names.append(uploaded_file.name)
                else:
                    rejected.append(f"{uploaded_file.name}: tidak ada baris tabel yang terbaca")

            except Exception as exc:
                rejected.append(f"{uploaded_file.name}: JSON tidak valid ({exc})")

        if rejected:
            st.warning("File berikut tidak diproses:")
            for message in rejected:
                st.write(f"- {message}")

        if not imported:
            st.error("Tidak ada data valid. Snapshot lama tidak diubah.")
        elif rejected:
            st.error(
                "Pembaruan dibatalkan karena ada file yang gagal dibaca. "
                "Periksa file tersebut dan upload ulang semua halaman agar snapshot tidak parsial."
            )
        else:
            frame = pd.DataFrame(imported)

            # Normalisasi nama kolom dari JSON ekstensi.
            rename = {}
            for col in frame.columns:
                low = str(col).strip().lower()
                if low in ("nama komersial", "nama usaha", "nama perusahaan"):
                    rename[col] = "Nama Komersial"
                elif low in ("id sbr", "idsbr"):
                    rename[col] = "ID SBR"
                elif low in ("id assignment", "assignment id"):
                    rename[col] = "ID Assignment"
                elif low in ("kode identitas", "identitas", "identity code"):
                    rename[col] = "Kode Identitas"
                elif low in ("alamat", "alamat usaha"):
                    rename[col] = "Alamat"
                elif low in ("kabupaten/kota", "kabupaten kota", "kab/kota", "kabupaten", "kota"):
                    rename[col] = "Kabupaten/Kota"
                elif low in ("status", "status assignment"):
                    rename[col] = "Status Assignment"

            frame = frame.rename(columns=rename)

            # File diambil dari filter OPEN. Jika kolom status ada, validasi tetap dilakukan.
            if "Status Assignment" not in frame.columns:
                frame["Status Assignment"] = "OPEN"
            frame["Status Assignment"] = frame["Status Assignment"].astype(str).str.strip().str.upper()
            frame = frame[frame["Status Assignment"].eq("OPEN")].copy()

            if frame.empty:
                st.error("Tidak ditemukan baris OPEN. Snapshot lama tetap dipertahankan.")
            else:
                frame["Kode Wilayah"] = frame.apply(extract_kode_wilayah, axis=1)
                frame["Kabupaten/Kota"] = frame.apply(infer_wilayah, axis=1)

                # Validasi jumlah baris sebelum menimpa snapshot lama.
                if len(frame) == 0:
                    st.error("Data kosong setelah validasi. Snapshot lama tidak diubah.")
                else:
                    imported_count, total_saved = db.replace_import(
                        frame, survey, period, source_names
                    )
                    history.record_snapshot(frame)
                    history.record_snapshot_summary(frame, survey, period)

                    unknown = int((frame["Kabupaten/Kota"] == "BELUM TERIDENTIFIKASI").sum())
                    st.success(
                        f"Snapshot berhasil diperbarui: {imported_count:,} data OPEN aktif "
                        f"dari {len(source_names)} file. Data lama untuk survei/periode ini "
                        f"telah digantikan."
                    )
                    if unknown:
                        st.warning(f"{unknown} data masih BELUM TERIDENTIFIKASI.")
                    st.rerun()

    except Exception as exc:
        st.error(f"Pembaruan gagal. Snapshot lama seharusnya tetap dipertahankan. Detail: {exc}")


# ============================================================
# MEMUAT DATA AKTIF
# ============================================================
st.divider()
df = db.load_master()

if df.empty:
    st.info("Belum ada data aktif. Upload JSON terbaru untuk memulai monitoring.")
    snapshots = history.load_snapshots()
    if not snapshots.empty:
        with st.expander("Riwayat snapshot sebelumnya"):
            st.dataframe(snapshots, use_container_width=True, hide_index=True)
    st.stop()

if "Nama Survei" in df.columns:
    df = df[df["Nama Survei"].eq(survey)]
if "Periode" in df.columns:
    df = df[df["Periode"].eq(period)]

if "Status Assignment" in df.columns:
    open_df = df[df["Status Assignment"].astype(str).str.upper().eq("OPEN")].copy()
else:
    open_df = df.copy()

open_count = len(open_df)
latest = db.latest_sync()


def metric(label, value):
    shown = f"{value:,}" if isinstance(value, (int, float)) else str(value)
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{shown}</div></div>',
        unsafe_allow_html=True,
    )


c1, c2, c3, c4 = st.columns(4)
with c1:
    metric("TOTAL DATA OPEN", open_count)
with c2:
    identified = (
        open_df.loc[open_df["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI", "Kabupaten/Kota"].nunique()
        if "Kabupaten/Kota" in open_df.columns else 0
    )
    metric("KAB/KOTA TERIDENTIFIKASI", identified)
with c3:
    unknown_count = (
        int((open_df["Kabupaten/Kota"] == "BELUM TERIDENTIFIKASI").sum())
        if "Kabupaten/Kota" in open_df.columns else open_count
    )
    metric("BELUM TERIDENTIFIKASI", unknown_count)
with c4:
    metric("PEMBARUAN TERAKHIR", latest or "—")


# ============================================================
# REKAP PER KABUPATEN/KOTA
# ============================================================
st.divider()
st.subheader("Monitoring OPEN per Kabupaten/Kota")

if "Kabupaten/Kota" not in open_df.columns:
    open_df["Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"

counts = open_df.groupby("Kabupaten/Kota").size().rename("OPEN").reset_index()
summary = pd.DataFrame({"Kabupaten/Kota": ACEH_REGENCIES}).merge(
    counts, how="left", on="Kabupaten/Kota"
)
summary["OPEN"] = summary["OPEN"].fillna(0).astype(int)
unknown = int((open_df["Kabupaten/Kota"] == "BELUM TERIDENTIFIKASI").sum())
if unknown:
    summary = pd.concat(
        [summary, pd.DataFrame([{"Kabupaten/Kota": "BELUM TERIDENTIFIKASI", "OPEN": unknown}])],
        ignore_index=True,
    )
summary = summary.sort_values("OPEN", ascending=False, kind="stable").reset_index(drop=True)
summary.insert(0, "No", range(1, len(summary) + 1))

left, right = st.columns([1.1, 1])
with left:
    st.dataframe(summary, use_container_width=True, hide_index=True, height=540)
with right:
    chart = summary[summary["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI"].sort_values("OPEN")
    fig = px.bar(
        chart, x="OPEN", y="Kabupaten/Kota", orientation="h", text="OPEN",
        title="Jumlah OPEN per Kabupaten/Kota", color="OPEN",
        color_continuous_scale=["#b9d8f2", "#07549a"],
    )
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=5, r=5, t=50, b=5))
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# DETAIL DATA DAN EKSPOR
# ============================================================
st.divider()
st.subheader("Detail Data OPEN")
col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("Cari nama usaha / ID SBR", placeholder="Ketik kata kunci...")
with col2:
    areas = ["Semua"] + sorted(open_df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI").unique().tolist())
    selected = st.selectbox("Filter kabupaten/kota", areas)

detail = open_df.copy()
if search:
    detail = detail[detail.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
if selected != "Semua":
    detail = detail[detail["Kabupaten/Kota"].eq(selected)]

visible_cols = [
    col for col in [
        "Kabupaten/Kota", "Kode Wilayah", "Kode Identitas", "ID Assignment",
        "ID SBR", "Nama Komersial", "Alamat", "Status Assignment", "Petugas", "Tanggal Update"
    ] if col in detail.columns
]
st.dataframe(detail[visible_cols] if visible_cols else detail, use_container_width=True, hide_index=True, height=430)

if not detail.empty:
    excel = make_excel(summary, detail, db.load_logs(), history.load())
    st.download_button(
        "⬇️ Unduh laporan Excel", data=excel,
        file_name=f"monitoring_{survey.replace(' ', '_')}_{period.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# Backup data aktif agar pengguna bisa menyimpan salinan di luar hosting.
backup_json = open_df.to_json(orient="records", force_ascii=False, indent=2)
st.download_button(
    "💾 Unduh backup data aktif (JSON)",
    data=backup_json,
    file_name=f"backup_{survey.replace(' ', '_')}_{period.replace(' ', '_')}.json",
    mime="application/json",
)


# ============================================================
# RIWAYAT SNAPSHOT DAN RIWAYAT IMPOR
# ============================================================
st.divider()
st.subheader("Riwayat pembaruan monitoring")
snapshots = history.load_snapshots()
if snapshots.empty:
    st.caption("Belum ada riwayat snapshot.")
else:
    st.dataframe(snapshots, use_container_width=True, hide_index=True)

with st.expander("Riwayat impor dan reset"):
    logs = db.load_logs()
    if logs.empty:
        st.caption("Belum ada riwayat impor.")
    else:
        st.dataframe(logs, use_container_width=True, hide_index=True)

import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs

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


@st.cache_resource(show_spinner=False)
def get_managers():
    """Pertahankan koneksi dan cache manager antar-rerun Streamlit."""
    return DataManager(), HistoryManager()


db, history = get_managers()

st.markdown(
    '<p class="main-title">MONITORING PROGRES PENDATAAN FASIH-SM</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-title">BPS PROVINSI ACEH · Monitoring seluruh status assignment</p>',
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
        "2. Pilih VHTS 2026 → 10 OKTOBER → Data → SEMUA.\n"
        "3. Unduh JSON untuk seluruh halaman melalui ekstensi.\n"
        "4. Upload semua JSON terbaru di dashboard.\n"
        "5. Klik **Ganti Snapshot Semua Status**."
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
st.subheader("Perbarui data seluruh status")
st.write(
    "Di FASIH-SM, pilih filter **SEMUA** (bukan hanya OPEN), lalu unduh seluruh halaman JSON. "
    "Upload semua file hasil satu kali pengambilan. Data aktif survei/periode terpilih akan "
    "**diganti seluruhnya** dengan snapshot terbaru yang mencakup semua status."
)

uploads = st.file_uploader(
    "Pilih semua file JSON hasil ekstensi Chrome",
    type=["json"],
    accept_multiple_files=True,
    key="json_upload",
)
confirmed = st.checkbox(
    "Saya memastikan semua file berasal dari FASIH-SM, survei VHTS 2026, "
    "periode 10 OKTOBER, filter status SEMUA, dan mencakup seluruh halaman.",
    key="confirm_snapshot",
)

if st.button(
    "🔄 Ganti Snapshot Semua Status dengan Data Terbaru",
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
                # Tolak file yang URL-nya secara eksplisit masih memakai filter status tunggal.
                # Untuk filter SEMUA, FASIH umumnya memakai status=ALL atau tanpa parameter status.
                status_params = parse_qs(urlparse(url).query).get("status", [])
                selected_status = status_params[0].strip().upper() if status_params else ""
                if selected_status not in ("", "ALL", "SEMUA", "ALL_STATUS"):
                    rejected.append(
                        f"{uploaded_file.name}: URL masih memakai filter status '{selected_status}'. "
                        "Pilih SEMUA di FASIH-SM lalu unduh ulang seluruh halaman."
                    )
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

            # Semua baris status harus memiliki status yang terbaca.
            if "Status Assignment" not in frame.columns:
                st.error(
                    "Kolom Status tidak ditemukan pada JSON. Snapshot lama tetap dipertahankan. "
                    "Pastikan ekstensi mengunduh tabel yang memuat kolom Status."
                )
                st.stop()

            frame["Status Assignment"] = (
                frame["Status Assignment"].astype(str).str.strip().str.upper()
            )
            frame = frame[
                frame["Status Assignment"].notna()
                & frame["Status Assignment"].ne("")
                & ~frame["Status Assignment"].isin(["NAN", "NONE", "-"])
            ].copy()

            if frame.empty:
                st.error("Tidak ditemukan baris dengan status valid. Snapshot lama tetap dipertahankan.")
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
                        f"Snapshot berhasil diperbarui: {imported_count:,} data dari seluruh status "
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
    st.info("Belum ada data aktif. Upload JSON terbaru dengan filter SEMUA untuk memulai monitoring.")
    snapshots = history.load_snapshots()
    if not snapshots.empty:
        with st.expander("Riwayat snapshot sebelumnya"):
            st.dataframe(snapshots, use_container_width=True, hide_index=True)
    st.stop()

if "Nama Survei" in df.columns:
    df = df[df["Nama Survei"].eq(survey)]
if "Periode" in df.columns:
    df = df[df["Periode"].eq(period)]

if "Status Assignment" not in df.columns:
    df["Status Assignment"] = "TIDAK DIKETAHUI"
df["Status Assignment"] = (
    df["Status Assignment"].fillna("TIDAK DIKETAHUI").astype(str).str.strip().str.upper()
)
df.loc[df["Status Assignment"].isin(["", "NAN", "NONE", "-"]), "Status Assignment"] = "TIDAK DIKETAHUI"

status_counts = (
    df.groupby("Status Assignment").size().sort_values(ascending=False).rename("Jumlah")
)
total_count = len(df)
latest = db.latest_sync()


def metric(label, value):
    shown = f"{value:,}" if isinstance(value, (int, float)) else str(value)
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{shown}</div></div>',
        unsafe_allow_html=True,
    )


st.subheader("Ringkasan seluruh status assignment")
st.caption("Jumlah data berdasarkan status terakhir yang tercatat pada snapshot FASIH-SM.")

status_items = list(status_counts.items())
for start_idx in range(0, len(status_items), 4):
    row_items = status_items[start_idx:start_idx + 4]
    metric_cols = st.columns(len(row_items))
    for col, (status_name, amount) in zip(metric_cols, row_items):
        with col:
            metric(status_name, int(amount))

c1, c2, c3 = st.columns(3)
with c1:
    metric("TOTAL SELURUH DATA", total_count)
with c2:
    identified = (
        df.loc[df["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI", "Kabupaten/Kota"].nunique()
        if "Kabupaten/Kota" in df.columns else 0
    )
    metric("KAB/KOTA TERIDENTIFIKASI", identified)
with c3:
    metric("PEMBARUAN TERAKHIR", latest or "—")


# ============================================================
# REKAP PER KABUPATEN/KOTA DAN STATUS
# ============================================================
st.divider()
st.subheader("Rekap status per Kabupaten/Kota")

if "Kabupaten/Kota" not in df.columns:
    df["Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"
df["Kabupaten/Kota"] = df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI")
df.loc[df["Kabupaten/Kota"].astype(str).str.strip().eq(""), "Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"

status_order = [
    "OPEN",
    "DRAFT",
    "SUBMITTED BY PENCACAH",
    "APPROVED BY PENGAWAS",
    "COMPLETED BY ADMIN KABUPATEN",
]
present_statuses = [x for x in status_order if x in df["Status Assignment"].unique()]
present_statuses += sorted(
    x for x in df["Status Assignment"].unique()
    if x not in present_statuses
)

pivot = (
    df.groupby(["Kabupaten/Kota", "Status Assignment"])
    .size()
    .unstack(fill_value=0)
)
pivot = pivot.reindex(index=ACEH_REGENCIES, fill_value=0)
if "BELUM TERIDENTIFIKASI" in df["Kabupaten/Kota"].values:
    pivot.loc["BELUM TERIDENTIFIKASI"] = (
        df[df["Kabupaten/Kota"] == "BELUM TERIDENTIFIKASI"]
        .groupby(["Kabupaten/Kota", "Status Assignment"])
        .size()
        .unstack(fill_value=0)
        .iloc[0]
    )
pivot = pivot.reindex(columns=present_statuses, fill_value=0)
pivot["TOTAL"] = pivot.sum(axis=1)
pivot = pivot.sort_values("TOTAL", ascending=False, kind="stable")
pivot_display = pivot.reset_index()
pivot_display.insert(0, "No", range(1, len(pivot_display) + 1))
summary = pivot_display.copy()

left, right = st.columns([1.15, 1])
with left:
    st.dataframe(pivot_display, use_container_width=True, hide_index=True, height=540)
with right:
    chart_data = (
        df.groupby(["Kabupaten/Kota", "Status Assignment"])
        .size().reset_index(name="Jumlah")
    )
    chart_data = chart_data[chart_data["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI"]
    fig = px.bar(
        chart_data,
        x="Jumlah",
        y="Kabupaten/Kota",
        color="Status Assignment",
        orientation="h",
        title="Komposisi status per Kabupaten/Kota",
        barmode="stack",
    )
    fig.update_layout(margin=dict(l=5, r=5, t=50, b=5), legend_title_text="Status")
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# DETAIL DATA DAN EKSPOR
# ============================================================
st.divider()
st.subheader("Detail Data Assignment")
col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("Cari nama usaha / ID SBR", placeholder="Ketik kata kunci...")
with col2:
    areas = ["Semua"] + sorted(df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI").unique().tolist())
    selected = st.selectbox("Filter kabupaten/kota", areas)

status_filter = st.selectbox("Filter status assignment", ["Semua"] + present_statuses)
detail = df.copy()
if status_filter != "Semua":
    detail = detail[detail["Status Assignment"].eq(status_filter)]
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
backup_json = df.to_json(orient="records", force_ascii=False, indent=2)
st.download_button(
    "💾 Unduh backup seluruh status (JSON)",
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

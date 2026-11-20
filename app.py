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
    :root { --bps-blue:#07549a; --bps-blue-2:#1676bd; --bps-gold:#f5a623; }
    .stApp { background: #f3f7fb; color: #19344f; }
    [data-testid="stHeader"] { background: rgba(243,247,251,.88); }
    [data-testid="stSidebar"] { background: #eaf1f8 !important; border-right:1px solid #dce7f1; }
    /* Pastikan teks sidebar terbaca pada tema browser/Streamlit apa pun. */
    [data-testid="stSidebar"], [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
      color:#19344f !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
      background:#fff !important; border-color:#cbd9e6 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] input { color:#19344f !important; }
    [data-testid="stSidebar"] button {
      color:#fff !important; background:#07549a !important; border-color:#07549a !important;
    }
    [data-testid="stSidebar"] button * { color:#fff !important; }
    .block-container { padding-top:1.35rem; padding-bottom:3rem; max-width:1580px; }
    /* Samakan warna label dan area upload dengan tema terang. */
    .stApp, .stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"] { color:#19344f; }
    [data-testid="stFileUploader"] section {
      background:#fff !important; border:1px dashed #a9bfd3 !important; border-radius:14px !important;
    }
    [data-testid="stFileUploader"] section *,
    [data-testid="stFileUploader"] small { color:#36536e !important; }
    [data-testid="stFileUploader"] button {
      color:#07549a !important; background:#eef5fb !important; border:1px solid #cbddec !important;
    }
    [data-testid="stFileUploader"] button * { color:#07549a !important; }
    h1,h2,h3 { color:#153b5c; letter-spacing:-.025em; }
    .hero { background:linear-gradient(115deg,#063b70 0%,#07549a 58%,#1682c5 100%);
      color:white; padding:25px 30px; border-radius:22px; margin:0 0 24px 0;
      box-shadow:0 12px 30px rgba(7,84,154,.16); }
    .hero-title {font-size:1.75rem; font-weight:800; letter-spacing:-.03em; margin:0; color:#fff;}
    .hero-sub {font-size:.94rem; color:rgba(255,255,255,.82); margin:.45rem 0 0 0;}
    .section-kicker {font-size:.78rem; font-weight:750; color:#5680a3; text-transform:uppercase; letter-spacing:.09em; margin-bottom:4px;}
    .section-note {color:#71869a; font-size:.9rem; margin-top:-5px; margin-bottom:14px;}
    .status-grid {display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:12px; margin:12px 0 18px 0;}
    .status-card {background:linear-gradient(145deg,#fff 0%,#f8fbfe 100%); border:1px solid #e0eaf3;
      border-radius:17px; padding:17px 19px; box-shadow:0 5px 16px rgba(25,62,94,.055); min-height:105px;}
    .status-name {font-size:.76rem; line-height:1.35; color:#607c95; font-weight:700; letter-spacing:.025em;}
    .status-value {font-size:1.85rem; line-height:1.2; color:#07549a; font-weight:800; margin-top:9px;}
    .summary-strip {display:flex; flex-wrap:wrap; gap:10px; margin:8px 0 22px 0;}
    .summary-pill {background:#fff; border:1px solid #e0eaf3; border-radius:14px; padding:12px 16px; flex:1 1 180px;}
    .summary-pill-label {font-size:.76rem; color:#70869b; font-weight:650;}
    .summary-pill-value {font-size:1.25rem; color:#153f65; font-weight:800; margin-top:3px;}
    div[data-testid="stDataFrame"] {border:1px solid #e1eaf2; border-radius:15px; overflow:hidden;}
    div[data-testid="stPlotlyChart"] {background:#fff; border:1px solid #e1eaf2; border-radius:17px; padding:8px; box-shadow:0 5px 16px rgba(25,62,94,.045);}
    div[data-testid="stDownloadButton"] button {border-radius:12px;}
    div.stButton > button {border-radius:12px; font-weight:650;}
    hr {border-color:#dce7f1;}
    /* FINAL OVERRIDES: paksa kontras tinggi pada tema Streamlit light. */
    .stApp .hero, .stApp .hero p, .stApp .hero .hero-title,
    .stApp .hero .hero-sub { color:#ffffff !important; }
    .stApp .hero .hero-sub { color:rgba(255,255,255,.92) !important; }
    .stApp [data-testid="stSidebar"],
    .stApp [data-testid="stSidebar"] *,
    .stApp [data-testid="stSidebar"] p,
    .stApp [data-testid="stSidebar"] span,
    .stApp [data-testid="stSidebar"] label,
    .stApp [data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] * {
      color:#173b5b !important;
    }
    .stApp [data-testid="stSidebar"] [data-baseweb="select"] > div,
    .stApp [data-testid="stSidebar"] [data-baseweb="select"] input {
      background:#ffffff !important; color:#173b5b !important;
    }
    .stApp [data-testid="stSidebar"] [data-baseweb="select"] svg { fill:#173b5b !important; }
    .stApp [data-testid="stSidebar"] [data-testid="stAlert"] *,
    .stApp [data-testid="stSidebar"] [data-testid="stAlert"] p {
      color:#173b5b !important;
    }
    .stApp [data-testid="stWidgetLabel"] *,
    .stApp [data-testid="stMarkdownContainer"] p,
    .stApp .stCaption, .stApp small { color:#294b68 !important; }
    .stApp [data-baseweb="select"] > div {
      background:#ffffff !important; border-color:#cbd9e6 !important;
    }
    .stApp [data-baseweb="select"] *,
    .stApp [data-baseweb="input"] input,
    .stApp [data-baseweb="textarea"] textarea { color:#173b5b !important; }
    .stApp [data-baseweb="select"] svg { fill:#173b5b !important; }
    .stApp [data-testid="stDataFrame"] {
      background:#ffffff !important; color:#173b5b !important;
    }
    .stApp [data-testid="stPlotlyChart"] { background:#ffffff !important; }
    .stApp [data-testid="stPlotlyChart"] .js-plotly-plot,
    .stApp [data-testid="stPlotlyChart"] .plot-container { background:#ffffff !important; }
    .stApp div[data-testid="stButton"] button,
    .stApp div[data-testid="stDownloadButton"] button {
      color:#173b5b !important; background:#ffffff !important;
      border:1px solid #9fb7cc !important;
    }
    .stApp div[data-testid="stButton"] button[kind="primary"] {
      color:#ffffff !important; background:#07549a !important; border-color:#07549a !important;
    }
    @media (max-width:700px) { .hero {padding:20px;border-radius:17px;} .hero-title{font-size:1.35rem;} }
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_managers():
    """Pertahankan koneksi dan cache manager antar-rerun Streamlit."""
    return DataManager(), HistoryManager()


db, history = get_managers()

st.markdown(
    '<div class="hero"><p class="hero-title">MONITORING PROGRES PENDATAAN FASIH-SM</p>'
    '<p class="hero-sub">BPS PROVINSI ACEH &nbsp;·&nbsp; Pemantauan seluruh status assignment secara terpadu</p></div>',
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
        f'<div class="summary-pill"><div class="summary-pill-label">{label}</div>'
        f'<div class="summary-pill-value">{shown}</div></div>',
        unsafe_allow_html=True,
    )


st.markdown('<div class="section-kicker">Ringkasan</div>', unsafe_allow_html=True)
st.subheader("Seluruh status assignment")
st.markdown(
    '<div class="section-note">Jumlah assignment berdasarkan status terakhir yang tercatat pada snapshot FASIH-SM.</div>',
    unsafe_allow_html=True,
)

# Status ditampilkan sebagai kartu ringkas yang responsif, tidak memanjang memenuhi satu baris.
status_colors = {
    "OPEN": "#f2a900",
    "DRAFT": "#8495a7",
    "SUBMITTED BY PENCACAH": "#3996c7",
    "APPROVED BY PENGAWAS": "#7b70c9",
    "COMPLETED BY ADMIN KABUPATEN": "#269b78",
}
status_cards = []
for status_name, amount in status_counts.items():
    accent = status_colors.get(status_name, "#1676bd")
    status_cards.append(
        f'<div class="status-card" style="border-top:4px solid {accent}">'
        f'<div class="status-name">{status_name}</div>'
        f'<div class="status-value">{int(amount):,}</div></div>'
    )
st.markdown('<div class="status-grid">' + ''.join(status_cards) + '</div>', unsafe_allow_html=True)

identified = (
    df.loc[df["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI", "Kabupaten/Kota"].nunique()
    if "Kabupaten/Kota" in df.columns else 0
)
st.markdown('<div class="summary-strip">', unsafe_allow_html=True)
metric("TOTAL SELURUH DATA", total_count)
metric("KAB/KOTA TERIDENTIFIKASI", identified)
metric("PEMBARUAN TERAKHIR", latest or "—")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# REKAP PER KABUPATEN/KOTA DAN STATUS
# ============================================================
st.divider()
st.markdown('<div class="section-kicker">Sebaran wilayah</div>', unsafe_allow_html=True)
st.subheader("Peringkat Kabupaten/Kota")
st.markdown(
    '<div class="section-note">Urutan otomatis dari jumlah terbanyak ke paling sedikit. Pilih status untuk melihat peringkat khusus status tersebut.</div>',
    unsafe_allow_html=True,
)

if "Kabupaten/Kota" not in df.columns:
    df["Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"
df["Kabupaten/Kota"] = df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI")
df.loc[df["Kabupaten/Kota"].astype(str).str.strip().eq(""), "Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"

status_order = [
    "OPEN", "DRAFT", "SUBMITTED BY PENCACAH", "APPROVED BY PENGAWAS",
    "COMPLETED BY ADMIN KABUPATEN",
]
present_statuses = [x for x in status_order if x in df["Status Assignment"].unique()]
present_statuses += sorted(x for x in df["Status Assignment"].unique() if x not in present_statuses)

pivot = (
    df.groupby(["Kabupaten/Kota", "Status Assignment"])
    .size().unstack(fill_value=0)
)
pivot = pivot.reindex(index=ACEH_REGENCIES, fill_value=0)
if "BELUM TERIDENTIFIKASI" in df["Kabupaten/Kota"].values:
    unknown_row = (
        df[df["Kabupaten/Kota"] == "BELUM TERIDENTIFIKASI"]
        .groupby(["Kabupaten/Kota", "Status Assignment"]).size().unstack(fill_value=0)
    )
    if not unknown_row.empty:
        pivot.loc["BELUM TERIDENTIFIKASI"] = unknown_row.iloc[0]
pivot = pivot.reindex(columns=present_statuses, fill_value=0)
pivot["TOTAL"] = pivot.sum(axis=1)

chart_status = st.selectbox(
    "Tampilkan peringkat berdasarkan",
    ["Semua status (total)"] + present_statuses,
    key="chart_status_filter",
)
rank_column = "TOTAL" if chart_status == "Semua status (total)" else chart_status
ranked = pivot.sort_values(rank_column, ascending=False, kind="stable")
ranked = ranked[ranked[rank_column] > 0]

left, right = st.columns([1.02, 1.25], gap="large")
with left:
    st.markdown("**Peringkat data**")
    ranked_display = ranked.reset_index().rename(columns={"index": "Kabupaten/Kota"})
    ranked_display.insert(0, "Peringkat", range(1, len(ranked_display) + 1))
    st.dataframe(ranked_display, use_container_width=True, hide_index=True, height=510)
    summary = ranked_display.copy()

with right:
    st.markdown("**Grafik jumlah assignment**")
    if chart_status == "Semua status (total)":
        chart_data = (
            df.groupby(["Kabupaten/Kota", "Status Assignment"])
            .size().reset_index(name="Jumlah")
        )
        chart_data = chart_data[chart_data["Kabupaten/Kota"].isin(ranked.index)]
        order_regions = ranked.index.tolist()
        fig = px.bar(
            chart_data, x="Jumlah", y="Kabupaten/Kota", color="Status Assignment",
            orientation="h", barmode="stack", category_orders={"Kabupaten/Kota": order_regions},
            custom_data=["Status Assignment", "Jumlah"],
            color_discrete_map=status_colors,
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Status: %{customdata[0]}<br>Jumlah: %{customdata[1]}<extra></extra>",
            marker_line_width=0,
        )
        chart_title = "Total seluruh status per Kabupaten/Kota"
    else:
        chart_data = ranked[[chart_status]].reset_index()
        chart_data.columns = ["Kabupaten/Kota", "Jumlah"]
        chart_data = chart_data[chart_data["Jumlah"] > 0]
        fig = px.bar(
            chart_data, x="Jumlah", y="Kabupaten/Kota", orientation="h",
            custom_data=["Kabupaten/Kota", "Jumlah"],
            color_discrete_sequence=[status_colors.get(chart_status, "#1676bd")],
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Jumlah: %{x}<extra></extra>",
            marker_line_width=0,
        )
        chart_title = f"Jumlah status {chart_status} per Kabupaten/Kota"

    fig.update_layout(
        title=dict(text=chart_title, font=dict(size=15, color="#234866")),
        height=510, margin=dict(l=8, r=18, t=58, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff",
        font=dict(color="#48647d", size=11),
        xaxis=dict(title=dict(text="Jumlah assignment", font=dict(color="#294b68")),
                   tickfont=dict(color="#294b68"), gridcolor="#e4edf5", zeroline=False),
        yaxis=dict(title="", tickfont=dict(color="#294b68"), autorange="reversed",
                   categoryorder="array", categoryarray=ranked.index.tolist()),
        legend=dict(title=dict(text="Status", font=dict(color="#294b68")),
                    font=dict(color="#294b68", size=11),
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0),
        bargap=.28,
    )
    selection = st.plotly_chart(
        fig, use_container_width=True, key="region_status_chart",
        on_select="rerun", selection_mode="points",
    )
    selected_points = selection.selection.points if selection and hasattr(selection, "selection") else []
    if selected_points:
        point = selected_points[-1]
        region = point.get("y") or (point.get("customdata", [None])[0] if point.get("customdata") else "")
        custom = point.get("customdata") or []
        if chart_status == "Semua status (total)":
            selected_status = custom[0] if len(custom) > 0 else "Status terpilih"
            selected_amount = custom[1] if len(custom) > 1 else point.get("x", 0)
        else:
            selected_status = chart_status
            selected_amount = point.get("x", custom[1] if len(custom) > 1 else 0)
        st.info(f"Dipilih: **{selected_status}** · **{region}** · **{int(selected_amount):,} assignment**")
    else:
        st.caption("Arahkan kursor untuk melihat jumlah. Klik salah satu bagian batang grafik untuk menampilkan jumlah status dan wilayah yang dipilih.")


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

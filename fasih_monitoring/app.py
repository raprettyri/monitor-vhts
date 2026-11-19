import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from pathlib import Path

from database.data_manager import DataManager
from database.history_manager import HistoryManager
from scraper.launcher import start_login, start_scrape, read_worker_status
from utils.wilayah import ACEH_REGENCIES
from utils.export import make_excel

st.set_page_config(page_title="Monitoring FASIH-SM | BPS Aceh", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.3rem; max-width: 1500px;}
.main-title {font-size: 1.8rem; font-weight: 750; color: #07549a; margin-bottom: 0;}
.sub-title {color: #64748b; font-size: .95rem; margin-top: .15rem;}
.metric-card {background: #f4f8fc; border: 1px solid #e3edf7; border-radius: 12px; padding: 15px 17px;}
.metric-label {font-size: .82rem; color: #64748b;}
.metric-value {font-size: 1.75rem; font-weight: 750; color: #0b4f8a;}
div[data-testid="stDataFrame"] {border: 1px solid #e5e7eb; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

db = DataManager()
history = HistoryManager()
st.markdown('<p class="main-title">MONITORING PROGRES PENDATAAN FASIH-SM</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">BPS PROVINSI ACEH · Monitoring status assignment OPEN</p>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://www.bps.go.id/assets/images/logo-bps.png", width=115)
    st.subheader("Pengaturan Monitoring")
    survey = st.selectbox("Nama survei", ["VHTS 2026"], index=0)
    period = st.selectbox("Periode", ["10 OKTOBER"], index=0)
    st.caption("Rentang periode: 01–30 November 2026")
    st.divider()
    st.markdown("**Koneksi FASIH-SM**")
    status = read_worker_status()
    if status.get("login") == "authenticated":
        st.success("Sesi login terdeteksi")
    elif status.get("login") == "running":
        st.info("Browser login sedang berjalan")
    else:
        st.warning("Belum ada konfirmasi sesi login")
    if st.button("🔐 Login FASIH-SM", use_container_width=True):
        ok, msg = start_login()
        st.toast(msg, icon="ℹ️" if ok else "⚠️")
    if st.button("🔄 Update Data Sekarang", type="primary", use_container_width=True):
        ok, msg = start_scrape(survey, period)
        st.toast(msg, icon="ℹ️" if ok else "⚠️")
    st.caption("Login dilakukan manual melalui SSO BPS. Jangan membagikan profil browser kepada orang lain.")
    st.divider()
    st.markdown("**Status proses terakhir**")
    worker = read_worker_status()
    st.caption(f"Tahap: {worker.get('stage', '—')}")
    st.caption(worker.get("message", "Belum ada aktivitas."))
    if st.button("Perbarui status proses", use_container_width=True):
        st.rerun()

st.caption(f"Survei: **{survey}**　|　Periode: **{period}**　|　Status fokus: **OPEN**")

df = db.load_master()
if df.empty:
    st.info("Belum ada data hasil scraping. Klik **Login FASIH-SM**, selesaikan login SSO pada browser yang terbuka, lalu klik **Update Data Sekarang**.")
    st.markdown("#### Tahapan pengambilan data")
    st.write("1. Login SSO BPS secara manual.  2. Scraper memilih VHTS 2026.  3. Scraper memilih periode 10 OKTOBER.  4. Scraper membuka Data dan memfilter OPEN.  5. Hasil divalidasi sebelum disimpan.")
    st.stop()

if "Nama Survei" in df:
    df = df[df["Nama Survei"].fillna(survey).eq(survey)]
if "Periode" in df:
    df = df[df["Periode"].fillna(period).eq(period)]

open_df = df[df.get("Status Assignment", pd.Series(["OPEN"]*len(df))).astype(str).str.upper().eq("OPEN")].copy()
total = len(df)
open_count = len(open_df)
latest = db.latest_sync()

def metric(label, value):
    shown = f"{value:,}" if isinstance(value, (int, float)) else str(value)
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{shown}</div></div>', unsafe_allow_html=True)

c1,c2,c3,c4 = st.columns(4)
with c1: metric("TOTAL DATA TERSIMPAN", total)
with c2: metric("DATA OPEN", open_count)
with c3: metric("WILAYAH TERidentifikasi".upper(), open_df.get("Kabupaten/Kota", pd.Series(dtype=str)).replace("", pd.NA).dropna().nunique())
with c4: metric("TERAKHIR SINKRONISASI", latest or "—")

st.divider()
st.subheader("Monitoring OPEN per Kabupaten/Kota")
if "Kabupaten/Kota" not in open_df:
    open_df["Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"
counts = open_df.groupby("Kabupaten/Kota").size().rename("OPEN").reset_index()
summary = pd.DataFrame({"Kabupaten/Kota": ACEH_REGENCIES}).merge(counts, how="left", on="Kabupaten/Kota")
summary["OPEN"] = summary["OPEN"].fillna(0).astype(int)
unknown = int(open_df["Kabupaten/Kota"].eq("BELUM TERIDENTIFIKASI").sum())
summary = pd.concat([summary, pd.DataFrame([{"Kabupaten/Kota":"BELUM TERIDENTIFIKASI","OPEN":unknown}])], ignore_index=True)
summary = summary.sort_values("OPEN", ascending=False, kind="stable").reset_index(drop=True)
summary.insert(0, "No", range(1, len(summary)+1))
summary["Total Target"] = "—"
summary["Persentase OPEN"] = "—"
summary = summary[["No","Kabupaten/Kota","Total Target","OPEN","Persentase OPEN"]]
left, right = st.columns([1.15, 1])
with left:
    st.dataframe(summary, use_container_width=True, hide_index=True, height=520)
with right:
    fig = px.bar(summary[summary["Kabupaten/Kota"] != "BELUM TERIDENTIFIKASI"].sort_values("OPEN"),
                 x="OPEN", y="Kabupaten/Kota", orientation="h",
                 title="Jumlah OPEN per Kabupaten/Kota", text="OPEN",
                 color="OPEN", color_continuous_scale=["#b9d8f2","#07549a"])
    fig.update_layout(showlegend=False, coloraxis_showscale=False, margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig, use_container_width=True)
    if unknown:
        st.warning(f"{unknown} data belum dapat diidentifikasi kabupaten/kotanya.")

st.divider()
st.subheader("Detail Data OPEN")
col1, col2 = st.columns([2,1])
with col1:
    search = st.text_input("Cari nama usaha / ID SBR", placeholder="Ketik kata kunci...")
with col2:
    areas = ["Semua"] + sorted(open_df["Kabupaten/Kota"].fillna("BELUM TERIDENTIFIKASI").unique().tolist())
    selected_area = st.selectbox("Filter kabupaten/kota", areas)
detail = open_df.copy()
if search:
    mask = detail.astype(str).apply(lambda s: s.str.contains(search, case=False, na=False)).any(axis=1)
    detail = detail[mask]
if selected_area != "Semua":
    detail = detail[detail["Kabupaten/Kota"].eq(selected_area)]
display_cols = [c for c in ["Kabupaten/Kota","ID SBR","Nama Komersial","Alamat","Status Assignment","Petugas","Tanggal Update"] if c in detail.columns]
st.dataframe(detail[display_cols] if display_cols else detail, use_container_width=True, hide_index=True, height=420)

if not detail.empty:
    excel = make_excel(summary, detail, db.load_logs(), history.load())
    st.download_button("⬇️ Unduh laporan Excel", data=excel,
                       file_name=f"monitoring_fasih_{survey.replace(' ','_')}_{period.replace(' ','_')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Riwayat sinkronisasi"):
    logs = db.load_logs()
    if logs.empty:
        st.caption("Belum ada riwayat.")
    else:
        st.dataframe(logs, use_container_width=True, hide_index=True)

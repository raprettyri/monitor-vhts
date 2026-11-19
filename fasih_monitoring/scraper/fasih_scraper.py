import re
import pandas as pd
from datetime import datetime
from scraper.browser import open_context, is_authenticated
from scraper.navigation import select_survey, select_period, open_data_page, select_assignment_status, NavigationError
from database.data_manager import DataManager
from database.history_manager import HistoryManager
from utils.wilayah import normalize_wilayah

EXPECTED_SURVEY = "VHTS 2026"
EXPECTED_PERIOD = "10 OKTOBER"

def _read_count(page):
    # Extract count adjacent to OPEN label if rendered in text. Manual confirmation remains required.
    body = page.locator("body").inner_text()
    match = re.search(r"OPEN\s+(\d+)", body, re.I)
    if not match:
        match = re.search(r"(\d+)\s+OPEN", body, re.I)
    return int(match.group(1)) if match else None

def _extract_table(page):
    tables = page.locator("table")
    if tables.count() == 0:
        raise NavigationError("Tabel HTML tidak ditemukan. FASIH-SM mungkin menggunakan grid virtual; lakukan inspeksi DOM.")
    table = tables.first
    headers = [x.strip() for x in table.locator("thead th").all_inner_texts()]
    if not headers:
        raise NavigationError("Header tabel tidak terbaca.")
    rows = []
    for tr in table.locator("tbody tr").all():
        cells = [x.strip() for x in tr.locator("td").all_inner_texts()]
        if cells:
            rows.append(dict(zip(headers, cells)))
    return rows

def _next_page(page):
    candidates = [
        page.get_by_role("button", name=re.compile(r"next|berikutnya|selanjutnya", re.I)),
        page.locator('button[aria-label*="next" i]'),
    ]
    for group in candidates:
        try:
            if group.count() and group.last.is_enabled():
                group.last.click()
                page.wait_for_timeout(1000)
                return True
        except Exception:
            pass
    return False

def scrape_all_open_data(survey=EXPECTED_SURVEY, period=EXPECTED_PERIOD):
    pw, context, page = open_context(headless=False)
    try:
        if not is_authenticated(page):
            raise NavigationError("Sesi SSO belum aktif. Klik Login FASIH-SM dan selesaikan login manual.")
        select_survey(page, survey)
        select_period(page, period)
        open_data_page(page)
        select_assignment_status(page, "OPEN")
        expected = _read_count(page)
        rows, seen_pages = [], set()
        for _ in range(500):
            signature = page.locator("body").inner_text()[:1000]
            if signature in seen_pages:
                raise NavigationError("Pagination berulang; proses dihentikan untuk mencegah duplikasi.")
            seen_pages.add(signature)
            rows.extend(_extract_table(page))
            if not _next_page(page):
                break
        else:
            raise NavigationError("Melebihi batas 500 halaman; proses dihentikan.")
        df = pd.DataFrame(rows)
        if df.empty:
            raise NavigationError("Scraping menghasilkan 0 baris. Data lama tidak akan ditimpa.")
        # Normalize known headers cautiously; actual FASIH headers may need mapping after DOM inspection.
        rename = {}
        for col in df.columns:
            low = col.strip().lower()
            if low in ["nama komersial", "nama usaha"]: rename[col] = "Nama Komersial"
            elif low in ["id sbr", "idsbr"]: rename[col] = "ID SBR"
            elif low in ["alamat", "alamat usaha"]: rename[col] = "Alamat"
            elif low in ["kabupaten/kota", "kabupaten kota", "kab/kota", "kabupaten"]: rename[col] = "Kabupaten/Kota"
            elif low in ["status", "status assignment"]: rename[col] = "Status Assignment"
            elif low in ["id assignment", "assignment id"]: rename[col] = "ID Assignment"
        df = df.rename(columns=rename)
        if "Kabupaten/Kota" not in df:
            df["Kabupaten/Kota"] = "BELUM TERIDENTIFIKASI"
        else:
            df["Kabupaten/Kota"] = df["Kabupaten/Kota"].map(normalize_wilayah)
        if "Status Assignment" not in df:
            df["Status Assignment"] = "OPEN"
        if not df["Status Assignment"].astype(str).str.upper().eq("OPEN").all():
            raise NavigationError("Hasil tabel memuat status selain OPEN; data ditolak.")
        df["Nama Survei"] = survey
        df["Periode"] = period
        df["Waktu Scraping"] = datetime.now().isoformat(timespec="seconds")
        if expected is not None and len(df) != expected:
            raise NavigationError(f"Validasi gagal: jumlah hasil {len(df)} berbeda dari angka OPEN FASIH-SM {expected}. Data tidak disimpan.")
        if "ID Assignment" in df and df["ID Assignment"].notna().any():
            df = df.drop_duplicates(subset=["ID Assignment"])
        else:
            df = df.drop_duplicates()
        DataManager().replace_master(df)
        HistoryManager().record_snapshot(df)
        DataManager().add_log(survey, period, "BERHASIL", expected, len(df), "LOLOS" if expected == len(df) else "TIDAK TERSEDIA", "")
        return len(df)
    except Exception as exc:
        DataManager().add_log(survey, period, "GAGAL", None, 0, "GAGAL", str(exc))
        raise
    finally:
        context.close()
        pw.stop()

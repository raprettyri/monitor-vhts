import argparse
import json
import time
import traceback
from datetime import datetime

from config import STATUS_PATH, FASIH_URL, LOG_DIR
from scraper.browser import open_context, is_authenticated
from scraper.fasih_scraper import scrape_all_open_data

WORKER_LOG = LOG_DIR / "worker.log"

def log(message):
    stamp = datetime.now().isoformat(timespec="seconds")
    with WORKER_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {message}\n")

def write_status(state, message, scrape=None, stage=None):
    payload = {
        "login": state,
        "message": message,
        "stage": stage or state,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "scrape": scrape,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"STATUS {state} | {message}")

def login_worker():
    pw = context = None
    try:
        write_status("running", "Membuka browser FASIH-SM...", stage="Membuka browser")
        pw, context, page = open_context(headless=False)
        page.goto(FASIH_URL, wait_until="domcontentloaded", timeout=60000)
        write_status("running", "Browser terbuka. Silakan selesaikan login SSO BPS secara manual.", stage="Menunggu login SSO")
        deadline = time.time() + 600

        while time.time() < deadline:
            if page.is_closed():
                raise RuntimeError("Tab browser tertutup sebelum status login dapat diperiksa.")
            # IMPORTANT: do not call page.goto() in this polling loop.
            if is_authenticated(page, navigate=False):
                write_status("authenticated", "Login FASIH-SM terdeteksi. Profil sesi tersimpan.", stage="Login berhasil")
                # Give persistent context a moment to flush profile/session state.
                time.sleep(2)
                return
            time.sleep(2)

        write_status("expired", "Waktu tunggu login habis. Klik Login FASIH-SM untuk mencoba kembali.", stage="Login kedaluwarsa")
    except Exception as exc:
        detail = traceback.format_exc()
        log("LOGIN ERROR: " + detail)
        write_status("error", f"Login worker error: {type(exc).__name__}: {exc}", stage="Login gagal")
    finally:
        try:
            if context:
                context.close()
        except Exception as exc:
            log(f"Context close warning: {exc}")
        try:
            if pw:
                pw.stop()
        except Exception as exc:
            log(f"Playwright stop warning: {exc}")

def scrape_worker(survey, period):
    try:
        write_status("scraping", "Memulai scraping FASIH-SM...", stage="Memulai")
        log(f"SCRAPE START survey={survey!r} period={period!r}")
        n = scrape_all_open_data(survey, period)
        write_status("authenticated", f"Scraping selesai. {n} baris berhasil divalidasi dan disimpan.", scrape=n, stage="Selesai")
        log(f"SCRAPE SUCCESS rows={n}")
    except Exception as exc:
        detail = traceback.format_exc()
        log("SCRAPE ERROR: " + detail)
        write_status("error", f"Scraping gagal: {type(exc).__name__}: {exc}. Periksa logs/worker.log.", stage="Scraping gagal")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["login", "scrape"], required=True)
    parser.add_argument("--survey", default="VHTS 2026")
    parser.add_argument("--period", default="10 OKTOBER")
    args = parser.parse_args()
    if args.mode == "login":
        login_worker()
    else:
        scrape_worker(args.survey, args.period)

if __name__ == "__main__":
    main()

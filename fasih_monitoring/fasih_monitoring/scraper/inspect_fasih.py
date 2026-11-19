from pathlib import Path
from scraper.browser import open_context, is_authenticated
from config import LOG_DIR, FASIH_URL

def main():
    pw, context, page = open_context(headless=False)
    try:
        page.goto(FASIH_URL, wait_until="domcontentloaded", timeout=60000)
        print("Login SSO secara manual jika diminta. Setelah masuk, tekan Enter pada terminal ini.")
        input()
        page.goto(FASIH_URL, wait_until="domcontentloaded", timeout=60000)
        html = page.content()
        out = LOG_DIR / "fasih_dom.html"
        out.write_text(html, encoding="utf-8")
        print(f"Snapshot DOM disimpan: {out}")
        print("URL:", page.url)
        print("Judul:", page.title())
    finally:
        context.close()
        pw.stop()

if __name__ == "__main__":
    main()

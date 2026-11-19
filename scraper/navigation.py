from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

class NavigationError(RuntimeError):
    pass

def click_text(page, text, *, exact=True, timeout=15000):
    loc = page.get_by_text(text, exact=exact).first
    try:
        loc.wait_for(state="visible", timeout=timeout)
        loc.click()
        page.wait_for_timeout(1200)
    except Exception as exc:
        raise NavigationError(f"Gagal menemukan/mengklik teks '{text}'. Perlu inspeksi DOM FASIH-SM. Detail: {exc}") from exc

def select_survey(page, survey_name="VHTS 2026"):
    # Survey selector layout may change; do not continue unless active label is confirmed.
    click_text(page, survey_name)
    body = page.locator("body").inner_text()
    if survey_name.lower() not in body.lower():
        raise NavigationError(f"Konfirmasi survei '{survey_name}' tidak ditemukan.")

def select_period(page, period_name="10 OKTOBER"):
    click_text(page, period_name)
    body = page.locator("body").inner_text()
    if period_name.lower() not in body.lower():
        raise NavigationError(f"Konfirmasi periode '{period_name}' tidak ditemukan.")

def open_data_page(page):
    click_text(page, "Data")
    try:
        page.get_by_text("Data hasil pendataan", exact=False).wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError:
        # A visible table header can be a valid alternative; do not silently continue on empty page.
        if not page.get_by_text("Status Assignment", exact=False).count():
            raise NavigationError("Menu Data belum terkonfirmasi. Periksa DOM dan navigasi.")

def select_assignment_status(page, status="OPEN"):
    # The FASIH dropdown is custom. Click its visible label, then choose exact option.
    label = page.get_by_text("Status Assignment", exact=False).first
    try:
        label.wait_for(state="visible", timeout=15000)
        label.click()
        page.get_by_text(status, exact=True).last.click(timeout=10000)
        page.wait_for_timeout(1800)
    except Exception as exc:
        raise NavigationError(f"Gagal menerapkan filter status '{status}'. Perlu inspeksi DOM. Detail: {exc}") from exc
    if not page.get_by_text(status, exact=True).count():
        raise NavigationError(f"Filter '{status}' tidak terkonfirmasi.")

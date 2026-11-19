from playwright.sync_api import sync_playwright
from config import PROFILE_DIR, FASIH_URL

LOGIN_URL_HINTS = ("login", "sso", "auth", "oauth", "signin")
LOGIN_TEXT_HINTS = ("sign in", "login", "masuk dengan", "single sign on", "masuk", "username")

def open_context(headless=False):
    """Open a persistent Chromium context. The profile contains sensitive SSO session data."""
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        viewport={"width": 1440, "height": 950},
    )
    page = context.pages[0] if context.pages else context.new_page()
    return pw, context, page

def is_authenticated(page, navigate=True):
    """Check session state. Set navigate=False while a user is completing SSO."""
    try:
        if page.is_closed():
            return False
        if navigate:
            page.goto(FASIH_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(1800)
        if page.is_closed():
            return False
        url = (page.url or "").lower()
        if any(hint in url for hint in LOGIN_URL_HINTS):
            return False
        body = (page.locator("body").inner_text(timeout=8000) or "").lower()
        if any(hint in body for hint in LOGIN_TEXT_HINTS):
            # Login words can exist in generic pages; URL is the stronger signal.
            if any(hint in url for hint in LOGIN_URL_HINTS):
                return False
        return any(x in body for x in ("surveys", "survei", "ringkasan", "lookup", "dasbor", "data hasil pendataan"))
    except Exception:
        # SSO redirects and page reloads can briefly invalidate a locator.
        return False

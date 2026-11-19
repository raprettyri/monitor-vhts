import subprocess
import sys
import json
from config import BASE_DIR, STATUS_PATH, LOG_DIR

def _launch(args):
    try:
        # Keep worker output in a file instead of discarding stderr/stdout.
        log_file = (LOG_DIR / "worker_console.log").open("a", encoding="utf-8")
        flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if sys.platform == "win32" else 0
        subprocess.Popen(
            [sys.executable, "-m", "scraper.worker", *args],
            cwd=str(BASE_DIR),
            creationflags=flags,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            close_fds=True,
        )
        return True, "Worker dijalankan. Pantau status proses di dashboard dan logs/worker.log."
    except Exception as exc:
        return False, f"Gagal menjalankan worker: {type(exc).__name__}: {exc}"

def start_login():
    return _launch(["--mode", "login"])

def start_scrape(survey, period):
    return _launch(["--mode", "scrape", "--survey", survey, "--period", period])

def read_worker_status():
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"login": "unknown", "message": "Belum ada aktivitas.", "stage": "Belum dimulai"}

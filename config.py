from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
PROFILE_DIR = DATA_DIR / "playwright_profile"
DB_PATH = DATA_DIR / "monitoring.sqlite3"
STATUS_PATH = DATA_DIR / "worker_status.json"
FASIH_URL = "https://fasih-sm.bps.go.id/"
DEFAULT_SURVEY = "VHTS 2026"
DEFAULT_PERIOD = "10 OKTOBER"

for folder in (DATA_DIR, LOG_DIR, PROFILE_DIR):
    folder.mkdir(parents=True, exist_ok=True)

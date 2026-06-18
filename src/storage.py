import json
from config import DATA_DIR, DATA_FILE


def load_reminders():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def save_reminders(reminders):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(reminders, indent=2))

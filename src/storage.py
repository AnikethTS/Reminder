import json
import os
import sys

from config import DATA_DIR, DATA_FILE


def load_reminders():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return []
    if not DATA_FILE.exists():
        return []
    try:
        raw = DATA_FILE.read_text()
    except (OSError, UnicodeError):
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _quarantine(raw)
        return []
    if not isinstance(data, list):
        _quarantine(raw)
        return []

    cleaned = [item for item in data if isinstance(item, dict)]
    if len(cleaned) != len(data):
        save_reminders(cleaned)
    return cleaned


def save_reminders(reminders):
    """Write via a temp file so a crash cannot leave a half-written JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(reminders, indent=2) + "\n"
    tmp = DATA_FILE.with_name(DATA_FILE.name + ".tmp")
    tmp.write_text(payload)
    os.replace(tmp, DATA_FILE)


def _quarantine(raw):
    backup = DATA_FILE.with_name(DATA_FILE.name + ".bak")
    try:
        backup.write_text(raw)
    except OSError as exc:
        print(f"[Remainders] could not back up {DATA_FILE.name}: {exc}", file=sys.stderr)
        return
    print(
        f"[Remainders] {DATA_FILE.name} is invalid; kept a copy at {backup.name}",
        file=sys.stderr,
    )

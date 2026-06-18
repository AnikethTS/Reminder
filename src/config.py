from pathlib import Path

APP_NAME               = "Remainders"
CHECK_INTERVAL_SECONDS = 30
MISSED_WINDOW_HOURS    = 24   # fire reminders missed within this window on startup

DATA_DIR  = Path.home() / ".local" / "share" / "remainders"
DATA_FILE = DATA_DIR / "reminders.json"
ICON_DIR  = DATA_DIR / "icons"
ICON_PATH = str(ICON_DIR / "remainders.png")
LOCK_FILE = DATA_DIR / "remainders.lock"

ALARM_SOUND = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"

SNOOZE_OPTIONS = [
    (5,  "5 min"),
    (10, "10 min"),
    (30, "30 min"),
    (60, "1 hour"),
]

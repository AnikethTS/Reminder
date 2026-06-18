from pathlib import Path

APP_NAME = "Remainders"
CHECK_INTERVAL_SECONDS = 30

DATA_DIR  = Path.home() / ".local" / "share" / "remainders"
DATA_FILE = DATA_DIR / "reminders.json"
ICON_DIR  = DATA_DIR / "icons"
ICON_PATH = str(ICON_DIR / "remainders.png")

ALARM_SOUND = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"

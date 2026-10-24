import shutil
import subprocess
from pathlib import Path

from config import ALARM_SOUND


def play_sound():
    """Play the alarm sound without blocking. Tries paplay, then aplay."""
    if not Path(ALARM_SOUND).is_file():
        return
    player = shutil.which("paplay") or shutil.which("aplay")
    if not player:
        return
    cmd = [player, "-q", ALARM_SOUND] if "aplay" in player else [player, ALARM_SOUND]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return

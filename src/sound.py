import shutil
import subprocess
from config import ALARM_SOUND


def play_sound():
    """Play the alarm sound non-blocking. Tries paplay (PulseAudio) then aplay."""
    player = shutil.which("paplay") or shutil.which("aplay")
    if not player:
        return
    cmd = [player, ALARM_SOUND]
    if "aplay" in player:
        cmd = [player, "-q", ALARM_SOUND]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

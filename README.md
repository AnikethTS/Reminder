# Remainders

A lightweight system tray reminder app for Ubuntu / GNOME, written in Python + GTK3.

Remainders lives in the top bar as a clock icon and also provides a full GUI window. It uses minimal RAM (~46 MB), plays a sound when reminders fire, and auto-starts on login.

---

## Features

- **System tray icon** — clock icon in the top bar with a quick-add menu
- **Main GUI window** — full reminder list with enable switches and delete buttons
- **Add / Edit / Delete** reminders with title, message, date, time, and repeat
- **Repeat modes** — None, Daily, Weekly, Monthly
- **Alarm sound** — plays `alarm-clock-elapsed.oga` on reminder fire
- **Snooze popup** — 5 min / 10 min / 30 min / 1 hour snooze options
- **Overdue badge** — red dot on the tray icon when a reminder is active
- **Missed reminders** — fires reminders missed while the app was off (up to 24 h)
- **Single-instance guard** — prevents duplicate tray icons
- **Auto-starts on login** via GNOME autostart

---

## Requirements

- Ubuntu 22.04+ (or any GNOME-based distro with AppIndicator support)
- Python 3.10+
- GTK3 + PyGObject (`python3-gi`)
- AyatanaAppIndicator3 (`gir1.2-ayatanaappindicator3-0.1`)
- libnotify (`gir1.2-notify-0.7`)
- pycairo (`python3-cairo`)
- PulseAudio (`paplay`)

Install all dependencies at once:

```bash
sudo apt install python3-gi gir1.2-ayatanaappindicator3-0.1 \
    gir1.2-notify-0.7 python3-cairo libnotify-bin \
    gnome-shell-extension-appindicator
```

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/Remainders.git
cd Remainders
bash install.sh
```

`install.sh` will:
1. Install the app icon at all standard sizes into `~/.local/share/icons/`
2. Create a desktop entry so Remainders appears in the app launcher
3. Set up autostart so it launches on every login
4. Start the app immediately

---

## Usage

| Action | How |
|---|---|
| Open the window | Click the clock icon → **Open Remainders**, or search "Remainders" in the app launcher |
| Add a reminder | Click **+** in the header bar, or tray → **Add Reminder…** |
| Edit a reminder | Click any row in the list |
| Delete a reminder | Click the trash icon on the row |
| Enable / disable | Toggle the switch on the row |
| Snooze | When a popup fires, choose 5 / 10 / 30 min or 1 hour |
| Close window | Click ✕ — the app keeps running in the tray |
| Quit completely | Tray → **Quit** |

---

## Project Structure

```
Remainders/
├── remainders.py       # Entry point
├── install.sh          # One-step installer
├── assets/
│   └── remainders.svg  # Scalable app icon
└── src/
    ├── app.py          # RemindersApp — tray indicator, menu, check loop
    ├── window.py       # MainWindow — GTK GUI window
    ├── dialogs.py      # AddDialog, ReminderPopup
    ├── storage.py      # load / save JSON
    ├── icon.py         # Cairo tray icon renderer
    ├── sound.py        # paplay alarm sound
    └── config.py       # Paths and constants
```

Reminders are stored as JSON at `~/.local/share/remainders/reminders.json`.

---

## Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes
4. Open a pull request

---

## Author

**Aniketh TS**

## License

MIT License — see [LICENSE](LICENSE) for details.

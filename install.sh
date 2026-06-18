#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SCRIPT_DIR/remainders.py"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/remainders.desktop"

chmod +x "$APP"

mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Remainders
Comment=Lightweight system tray reminder app
Exec=python3 $APP
Icon=appointment-soon
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

echo "Installed autostart entry: $DESKTOP_FILE"
echo "Starting Remainders now..."
nohup python3 "$APP" >/tmp/remainders.log 2>&1 &
echo "Running (PID $!). Check the top bar for the clock icon."

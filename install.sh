#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SCRIPT_DIR/remainders.py"
SVG_SRC="$SCRIPT_DIR/assets/remainders.svg"

ICONS_DIR="$HOME/.local/share/icons/hicolor"
APPS_DIR="$HOME/.local/share/applications"
AUTOSTART_DIR="$HOME/.config/autostart"

chmod +x "$APP"

echo "Installing icon..."
mkdir -p "$ICONS_DIR/scalable/apps"
cp "$SVG_SRC" "$ICONS_DIR/scalable/apps/remainders.svg"

python3 - "$ICONS_DIR" <<'PYEOF'
import sys, os, cairo, math

icons_dir = sys.argv[1]

def render(size, path):
    s   = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(s)
    ctx.set_operator(cairo.OPERATOR_CLEAR); ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)

    cx, cy = size / 2, size * 0.60
    r = size * 0.36
    blue = (0.21, 0.52, 0.89)

    ctx.set_source_rgb(*blue)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_width(r * 0.18)
    ctx.move_to(cx - r * 0.52, cy - r * 0.68)
    ctx.line_to(cx - r * 0.80, cy - r * 1.00)
    ctx.stroke()
    ctx.move_to(cx + r * 0.52, cy - r * 0.68)
    ctx.line_to(cx + r * 0.80, cy - r * 1.00)
    ctx.stroke()

    ctx.set_source_rgb(*blue)
    ctx.arc(cx, cy, r, 0, 2 * math.pi); ctx.fill()

    ctx.set_source_rgb(1, 1, 1)
    ctx.arc(cx, cy, r * 0.80, 0, 2 * math.pi); ctx.fill()

    ctx.set_source_rgb(*blue)
    ctx.set_line_width(r * 0.16)
    ctx.move_to(cx, cy); ctx.line_to(cx, cy - r * 0.55); ctx.stroke()

    ctx.set_line_width(r * 0.11)
    ctx.move_to(cx, cy); ctx.line_to(cx + r * 0.52, cy); ctx.stroke()

    ctx.arc(cx, cy, r * 0.10, 0, 2 * math.pi); ctx.fill()

    s.write_to_png(path)

for size in (16, 32, 48, 64, 128, 256):
    d = os.path.join(icons_dir, f'{size}x{size}', 'apps')
    os.makedirs(d, exist_ok=True)
    render(size, os.path.join(d, 'remainders.png'))
    print(f'  {size}x{size} ✓')
PYEOF

gtk-update-icon-cache -f -t "$ICONS_DIR" 2>/dev/null || true

echo "Installing app launcher entry..."
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/remainders.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Remainders
GenericName=Reminder App
Comment=Lightweight system tray reminder app for Ubuntu
Exec=python3 $APP
Icon=remainders
Categories=Utility;
Keywords=reminder;alarm;notification;clock;
StartupNotify=false
EOF

update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Installing autostart entry..."
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/remainders.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Remainders
Comment=Lightweight system tray reminder app
Exec=python3 $APP
Icon=remainders
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "Done! Installed to:"
echo "  App launcher : $APPS_DIR/remainders.desktop"
echo "  Autostart    : $AUTOSTART_DIR/remainders.desktop"
echo "  Icons        : $ICONS_DIR/{16,32,48,64,128,256}x*/apps/remainders.png"
echo ""
echo "Starting Remainders..."
nohup python3 "$APP" >/tmp/remainders.log 2>&1 &
echo "Running (PID $!). Look for the clock in the top bar."

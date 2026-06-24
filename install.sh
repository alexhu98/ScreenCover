#!/usr/bin/env bash
#
# Install ScreenCover as a desktop application on Zorin OS / GNOME so it can be
# searched in the Activities/Apps menu and pinned to the taskbar.
#
# Usage:  ./install.sh        (install for the current user)
#         ./install.sh --uninstall
#
set -euo pipefail

# Absolute path to this repository (where the script lives).
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$APP_DIR/screencover.py"
ICON_PATH="$APP_DIR/screencover.png"   # optional; falls back to a theme icon

DEST_DIR="$HOME/.local/share/applications"
DEST_FILE="$DEST_DIR/screencover.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$DEST_FILE"
    update-desktop-database "$DEST_DIR" 2>/dev/null || true
    echo "Removed $DEST_FILE"
    exit 0
fi

mkdir -p "$DEST_DIR"

# Use the bundled icon if present, otherwise a generic theme icon.
if [[ -f "$ICON_PATH" ]]; then
    icon="$ICON_PATH"
else
    icon="video-display"
fi

sed -e "s|__APP_PATH__|$APP_PATH|g" \
    -e "s|__ICON_PATH__|$icon|g" \
    "$APP_DIR/screencover.desktop" > "$DEST_FILE"

chmod +x "$DEST_FILE"
update-desktop-database "$DEST_DIR" 2>/dev/null || true

echo "Installed launcher: $DEST_FILE"
echo "Open the Apps menu, search 'ScreenCover', right-click its icon -> 'Pin to Taskbar'."

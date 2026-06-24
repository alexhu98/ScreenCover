#!/usr/bin/env bash
#
# Uninstall ScreenCover: remove the desktop launcher and the global keyboard
# shortcut installed by install.sh. Does not touch the repository itself.
#
# Usage:  ./uninstall.sh
#
set -euo pipefail

DEST_DIR="$HOME/.local/share/applications"
DEST_FILE="$DEST_DIR/screencover.desktop"

MK_SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
KB_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/screencover/"

# Remove the launcher.
if [[ -f "$DEST_FILE" ]]; then
    rm -f "$DEST_FILE"
    echo "Removed launcher: $DEST_FILE"
else
    echo "No launcher found at $DEST_FILE"
fi
update-desktop-database "$DEST_DIR" 2>/dev/null || true

# Remove the global keyboard shortcut from the media-keys list.
if command -v gsettings >/dev/null 2>&1; then
    list="$(gsettings get "$MK_SCHEMA" custom-keybindings 2>/dev/null || echo '[]')"
    [[ "$list" == "@as []" || -z "$list" ]] && list="[]"
    new="$(python3 - "$KB_PATH" "$list" <<'PY'
import ast, sys
path, raw = sys.argv[1], sys.argv[2]
try:
    items = ast.literal_eval(raw)
except Exception:
    items = []
items = [p for p in items if p != path]
print("[" + ", ".join("'%s'" % p for p in items) + "]")
PY
)"
    gsettings set "$MK_SCHEMA" custom-keybindings "$new"
    echo "Removed global keyboard shortcut."
else
    echo "gsettings not found; skipped shortcut removal."
fi

# Refresh the icon cache so the launcher disappears cleanly.
gtk-update-icon-cache -f "$HOME/.local/share/icons" 2>/dev/null || true

echo "ScreenCover uninstalled."

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
ICON_PATH="$APP_DIR/screencover.svg"   # custom icon; falls back to a theme icon

# The desktop/taskbar launches without an interactive shell, so pyenv is not
# initialized and a bare "python3" there can resolve to a different Python that
# lacks tkinter (the app would crash instantly). run.sh initializes pyenv before
# launching, so the GUI uses the same interpreter as an interactive terminal.
RUN_PATH="$APP_DIR/run.sh"
chmod +x "$RUN_PATH" "$APP_PATH" 2>/dev/null || true

DEST_DIR="$HOME/.local/share/applications"
DEST_FILE="$DEST_DIR/screencover.desktop"

# Global keyboard shortcut (override with e.g. SHORTCUT='<Super>b' ./install.sh)
SHORTCUT="${SHORTCUT:-<Control><Super><Alt>b}"
# Delay (seconds) used by the launcher's "Cover after N seconds" action.
DELAY="${DELAY:-1}"
MK_SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
KB_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/screencover/"
KB_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"

# Register/unregister the custom shortcut path in the media-keys list.
register_shortcut() {
    local add="$1"   # "yes" to add, "no" to remove
    command -v gsettings >/dev/null 2>&1 || return 0

    local list
    list="$(gsettings get "$MK_SCHEMA" custom-keybindings 2>/dev/null || echo "@as []")"
    [[ "$list" == "@as []" || -z "$list" ]] && list="[]"

    # Strip the entry if present, then re-add when requested (idempotent).
    python3 - "$add" "$KB_PATH" "$list" <<'PY' > /tmp/.sc_kb_list
import ast, sys
add, path, raw = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    items = ast.literal_eval(raw)
except Exception:
    items = []
items = [p for p in items if p != path]
if add == "yes":
    items.append(path)
print("[" + ", ".join("'%s'" % p for p in items) + "]")
PY
    gsettings set "$MK_SCHEMA" custom-keybindings "$(cat /tmp/.sc_kb_list)"
    rm -f /tmp/.sc_kb_list
}

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$DEST_FILE"
    update-desktop-database "$DEST_DIR" 2>/dev/null || true
    register_shortcut no
    echo "Removed $DEST_FILE and the global shortcut."
    exit 0
fi

mkdir -p "$DEST_DIR"

# Warn early if launching through the wrapper cannot import tkinter (the GUI
# toolkit). This exercises the same pyenv-initialized path the launcher uses.
if ! "$RUN_PATH" --check-tk 2>/dev/null; then
    echo "WARNING: the launch wrapper's Python cannot import tkinter."
    echo "         Install it (e.g. 'sudo apt install python3-tk', or for pyenv"
    echo "         rebuild Python with tk support) or the launcher will not start."
fi

# Use the bundled icon if present, otherwise a generic theme icon.
if [[ -f "$ICON_PATH" ]]; then
    icon="$ICON_PATH"
else
    icon="video-display"
fi

sed -e "s|__RUN__|$RUN_PATH|g" \
    -e "s|__ICON_PATH__|$icon|g" \
    -e "s|__DELAY__|$DELAY|g" \
    "$APP_DIR/screencover.desktop" > "$DEST_FILE"

chmod +x "$DEST_FILE"
update-desktop-database "$DEST_DIR" 2>/dev/null || true

# Install the global keyboard shortcut.
if command -v gsettings >/dev/null 2>&1; then
    register_shortcut yes
    gsettings set "$KB_SCHEMA:$KB_PATH" name 'ScreenCover'
    gsettings set "$KB_SCHEMA:$KB_PATH" command "$RUN_PATH"
    gsettings set "$KB_SCHEMA:$KB_PATH" binding "$SHORTCUT"
    echo "Global shortcut set to: $SHORTCUT"
else
    echo "gsettings not found; skipped the global shortcut."
fi

echo "Installed launcher: $DEST_FILE (delay action: ${DELAY}s)"
echo "Launching via: $RUN_PATH (pyenv-aware)"
echo "Open the Apps menu, search 'ScreenCover', right-click its icon -> 'Pin to Taskbar'."

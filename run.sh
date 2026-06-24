#!/usr/bin/env bash
#
# Launch wrapper for ScreenCover.
#
# The desktop/taskbar launches without an interactive shell, so pyenv is not
# initialized and a bare "python3" can resolve to a different interpreter
# (often one without tkinter) that crashes instantly. Initializing pyenv here
# makes the GUI launch use the same Python as an interactive terminal.
#
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Used by install.sh to verify tkinter is importable via this same launch path.
if [[ "${1:-}" == "--check-tk" ]]; then
    exec python3 -c 'import tkinter'
fi

exec python3 "$DIR/screencover.py" "$@"

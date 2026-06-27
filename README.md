# ScreenCover

Blank all screens, like a screen saver but allow applications to run in the background.

## What it does

By default ScreenCover **turns the displays off** (via the X11 DPMS extension,
`xset dpms force off`) so the panels go truly dark and save power — while a
borderless **black** cover is layered over each connected monitor underneath
(it is built and tested for multi-monitor setups, e.g. 3 screens). Unlike a real
screen saver it does **not** pause the machine — applications keep running in the
background; only the monitors' power state changes. Pass **`--blank`** to keep
the displays **on** under the black cover instead of powering them off.

Press **any key** (the **Shift** key included), click anywhere, or **move the
mouse** past a small threshold to **minimize** the covers — which also **wakes
the displays** — and use your desktop normally; the app keeps running. Once the
whole computer has been **idle for 15 minutes** (configurable, see below) the
covers return and the displays turn back off automatically. Press **Esc** to
quit the app for good.

Only **one instance** runs at a time. Launching ScreenCover again — from the
taskbar icon, the global shortcut, or the menu — does **not** start a duplicate:
it tells the running instance to **re-cover the screens immediately**, so the
launch gesture doubles as a "cover now" button.

## Requirements

- Python 3.8+
- [`screeninfo`](https://pypi.org/project/screeninfo/) for true multi-monitor
  coverage (optional, but recommended). Without it the app falls back to the
  single virtual screen that tkinter reports.
- An **X11** session for the idle re-cover feature. Idle time is read from the
  X11 XScreenSaver extension (no extra Python package), falling back to the
  `xprintidle` command if the extension is unavailable (`sudo apt-get install
  xprintidle`). Without either, the covers stay minimized after the first
  dismiss instead of returning.
- **`xset`** (from `x11-xserver-utils`, usually preinstalled) with **DPMS**
  enabled, for the default display power-off. If `xset` is missing or DPMS is
  unavailable, ScreenCover automatically falls back to the black overlay (the
  same as `--blank`).

```bash
pip install -r requirements.txt
```

`tkinter` ships with most Python installations. On Debian/Ubuntu you may need:

```bash
sudo apt-get install python3-tk
```

## Usage

```bash
python screencover.py
```

All displays turn off (with a black cover behind them). Hit any key or click to
wake the screens and minimize the cover; both return after 15 minutes of
computer-wide idle. Press Esc to quit. To keep the displays **on** under a plain
black cover instead of powering them off, use `--blank`:

```bash
python screencover.py --blank
```

Change the idle delay with `--idle-timeout MINUTES` (e.g. `--idle-timeout 0.25`
re-covers after ~15 seconds, handy for testing):

```bash
python screencover.py --idle-timeout 10
```

## Pin to the taskbar (Zorin OS / GNOME)

```bash
./install.sh
```

This installs a desktop launcher (with the bundled `screencover.svg` icon — a
muted night-sky badge that stays legible in dark mode) to
`~/.local/share/applications`. Then open the **Apps menu**, search
**"ScreenCover"**, right-click the icon and choose **"Pin to Taskbar"** /
**"Add to Favorites"**.

The launcher runs the app through `run.sh`, which initializes **pyenv** before
launching. The desktop/taskbar starts apps without an interactive shell, so a
bare `python3` there can resolve to a system Python without `tkinter` and crash
instantly — the wrapper makes the GUI use the same interpreter as your terminal.
`install.sh` warns at install time if that interpreter can't import `tkinter`.

## Global keyboard shortcut

`install.sh` also registers a global shortcut (default **`Ctrl+Super+Alt+B`**)
that launches ScreenCover from anywhere. Override the binding:

```bash
SHORTCUT='<Super>b' ./install.sh
```

The launcher also gets a right-click **"Cover after N seconds"** action. Set the
delay (default **1s**) at install time, and combine settings freely:

```bash
DELAY=5 SHORTCUT='<Super>b' ./install.sh
```

You can also run with a delay directly: `python screencover.py --delay 5`.

## Uninstall

```bash
./uninstall.sh
```

Removes the launcher and the global keyboard shortcut and refreshes the icon
cache. (`./install.sh --uninstall` does the same.)

# ScreenCover

Cover all screens with black canvas, like a screen saver but allow applications to run in the background.

## What it does

ScreenCover opens a borderless, full-screen **black** window on every connected
monitor (it is built and tested for multi-monitor setups, e.g. 3 screens). The
covers sit on top of everything, but unlike a real screen saver they do **not**
pause the machine — applications keep running in the background.

Press **any key** (the **Shift** key included) or click anywhere to dismiss all
covers and exit immediately.

## Requirements

- Python 3.8+
- [`screeninfo`](https://pypi.org/project/screeninfo/) for true multi-monitor
  coverage (optional, but recommended). Without it the app falls back to the
  single virtual screen that tkinter reports.

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

All screens go black. Hit any key or click to exit.

## Pin to the taskbar (Zorin OS / GNOME)

```bash
./install.sh
```

This installs a desktop launcher (with the bundled `screencover.svg` icon — a
bright badge that stays visible in dark mode) to
`~/.local/share/applications`. Then open the **Apps menu**, search
**"ScreenCover"**, right-click the icon and choose **"Pin to Taskbar"** /
**"Add to Favorites"**.

## Global keyboard shortcut

`install.sh` also registers a global shortcut (default **`Ctrl+Super+Alt+B`**)
that launches ScreenCover from anywhere. Override the binding:

```bash
SHORTCUT='<Super>b' ./install.sh
```

The launcher also gets a right-click **"Cover after N seconds"** action. Set the
delay (default 3s) at install time, and combine settings freely:

```bash
DELAY=5 SHORTCUT='<Super>b' ./install.sh
```

You can also run with a delay directly: `python screencover.py --delay 5`.

Remove the launcher and shortcut with `./install.sh --uninstall`.

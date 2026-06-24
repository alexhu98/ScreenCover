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

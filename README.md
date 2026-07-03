# ScreenCover

Blank all screens, like a screen saver but allow applications to run in the background.

## What it does

ScreenCover blanks the screens in **two stages**:

1. **Blank** — once the computer has been **idle for 15 minutes** (configurable),
   a borderless **black** cover is layered over every connected monitor with the
   displays still on (built and tested for multi-monitor setups, e.g. 3 screens).
2. **Off** — if the cover is not dismissed for a further **45 minutes**
   (configurable), the displays are **powered off** via the X11 DPMS extension
   (`xset dpms force off`) so the panels go truly dark and save power.

Unlike a real screen saver it does **not** pause the machine — applications keep
running in the background; only the monitors' power state changes. Pass
**`--blank`** to skip stage 2 and only ever blank the screens.

Press **any key** (the **Shift** key included), click anywhere, or **move the
mouse** past a small threshold to **minimize** the cover — which also **wakes the
displays** if they were off — and use your desktop normally; the app keeps
running. The two-stage cover then returns automatically after the next idle
period. Press **Esc** to quit the app for good.

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

The screens blank after 15 minutes of computer-wide idle, then the displays
power off 45 minutes after that. Hit any key or click to wake the screens and
minimize the cover. Press Esc to quit.

To **never** power the displays off (only ever blank), use `--blank`:

```bash
python screencover.py --blank
```

Tune the two stages with `--idle-timeout MINUTES` (when to blank) and
`--off-delay MINUTES` (how long after blanking to power off). Small values are
handy for testing — e.g. blank after ~6 s, power off ~6 s later:

```bash
python screencover.py --idle-timeout 0.1 --off-delay 0.1
```

## Command-line options

| Option | Argument | Default | Description |
| --- | --- | --- | --- |
| `-d`, `--delay` | `SECONDS` | `0` | Wait this many seconds before covering the screens after launch. |
| `-i`, `--idle-timeout` | `MINUTES` | `15` | Blank the screens (show the black cover) after the computer has been idle this many minutes. |
| `--off-delay` | `MINUTES` | `45` | Power the displays off (via DPMS) this many minutes after the screens blank. Ignored when `--blank` is set. |
| `--blank` | — | off (powers off) | Only ever blank the screens; never power the displays off (skip the off stage). |
| `--no-initial-cover` | — | off (covers on launch) | Do **not** cover the screens on launch; start minimized and only cover after the idle timeout. Meant for autostart on login so signing in does not blank the screen. |
| `--debug` | — | off | Print diagnostic events (idle, motion, cover/minimize, power-off) to stderr. |
| `-h`, `--help` | — | — | Show the help message and exit. |

`SECONDS` and `MINUTES` accept fractions (e.g. `--idle-timeout 0.25` ≈ 15
seconds). All defaults assume the standard two-stage flow: blank at 15 minutes
idle, then displays off 45 minutes later.

Examples:

```bash
python screencover.py                            # blank at 15 min, off at 60 min
python screencover.py --idle-timeout 10          # blank at 10 min, off at 55 min
python screencover.py --idle-timeout 5 --off-delay 30   # blank at 5 min, off at 35 min
python screencover.py --blank                    # only ever blank; never power off
python screencover.py --delay 5                  # cover 5 seconds after launch
python screencover.py --no-initial-cover         # don't cover on launch; wait for idle (autostart)
python screencover.py --idle-timeout 0.1 --off-delay 0.1 --debug   # fast test
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

## Autostart on login (Zorin OS / GNOME)

To have ScreenCover start automatically every time you log in — without
forgetting to launch it — install a **login autostart entry**:

```bash
./install.sh --autostart
```

This writes `~/.config/autostart/screencover.desktop`, which GNOME/Zorin runs
**after** you log in and your graphical session is up (so `DISPLAY` and
`XAUTHORITY` are already set for you). The entry launches with
**`--no-initial-cover`**, so **logging in does not blank your screen** — the app
just runs quietly in the background and shows the first cover only after the
normal idle timeout (15 minutes by default). Remove it again with
`./install.sh --uninstall`.

> **Why not `cron`?** ScreenCover is an X11 GUI app. A `cron @reboot` job runs
> before your desktop session exists, with no `DISPLAY`/`XAUTHORITY` and a
> minimal `PATH`, so tkinter fails to connect to a display. Autostart entries
> fire *inside* your session, after X is up, which is exactly what a
> login-launched GUI app needs.

If you prefer to write the entry yourself instead of using `--autostart`, create
`~/.config/autostart/screencover.desktop` with (use the absolute path to
`run.sh`):

```ini
[Desktop Entry]
Type=Application
Name=ScreenCover
Exec=/absolute/path/to/ScreenCover/run.sh --no-initial-cover
Terminal=false
X-GNOME-Autostart-enabled=true
```

Note the difference from `--delay`: `--delay N` still covers the screen (just
`N` seconds after launch), whereas `--no-initial-cover` never covers on launch
and waits for the idle timeout — the right choice for autostart. You can combine
it with the timing flags, e.g. `run.sh --no-initial-cover --idle-timeout 10`.

## Keyboard shortcuts

**Global shortcut (launch / cover now):** **`Ctrl+Super+Alt+B`** — this is the
default registered by `install.sh`. Press it from anywhere to launch ScreenCover,
or to re-cover the screens immediately if it is already running. (`Super` is the
Windows/⊞ key.)

**While the screens are covered:**

| Key / action | Effect |
| --- | --- |
| `Esc` | Quit ScreenCover |
| Any other key, mouse click, or mouse move (> ~30 px) | Wake the displays and minimize the cover |

`install.sh` registers the global shortcut as a GNOME custom keybinding.
Override the binding at install time:

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

Removes the launcher, the login autostart entry (if installed), and the global
keyboard shortcut, and refreshes the icon cache. (`./install.sh --uninstall`
does the same.)

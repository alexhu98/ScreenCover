#!/usr/bin/env python3
"""ScreenCover.

Cover every connected screen with a black canvas, like a screen saver, while
allowing applications to keep running in the background.

The app opens one borderless, full-screen black window per monitor. Any key
(the Shift key included) or mouse click *minimizes* the covers so the desktop
is usable again; the app keeps running and re-covers every screen once the
whole computer has been idle for the configured time (15 minutes by default).
Press Ctrl+Q to quit.
"""

from __future__ import annotations

import ctypes
import tkinter as tk


class _XScreenSaverInfo(ctypes.Structure):
    """Mirror of the X11 ``XScreenSaverInfo`` struct (only ``idle`` is read)."""

    _fields_ = [
        ("window", ctypes.c_ulong),
        ("state", ctypes.c_int),
        ("kind", ctypes.c_int),
        ("since", ctypes.c_ulong),
        ("idle", ctypes.c_ulong),
        ("event_mask", ctypes.c_ulong),
    ]


# Cached XScreenSaver handles so each idle poll is cheap. ``None`` means "not
# tried yet"; ``False`` means "unavailable, use the fallback".
_xss_state = None


def _init_xss():
    """Open the X display and allocate XScreenSaver state, or return ``False``."""
    try:
        xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
        xss = ctypes.cdll.LoadLibrary("libXss.so.1")

        xlib.XOpenDisplay.restype = ctypes.c_void_p
        xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        xlib.XDefaultRootWindow.restype = ctypes.c_ulong
        xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XScreenSaverInfo)
        xss.XScreenSaverQueryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(_XScreenSaverInfo),
        ]

        dpy = xlib.XOpenDisplay(None)
        if not dpy:
            return False
        root = xlib.XDefaultRootWindow(dpy)
        info = xss.XScreenSaverAllocInfo()
        return (xss, dpy, root, info)
    except Exception:
        return False


def _xprintidle_ms():
    """Fallback: parse idle milliseconds from the ``xprintidle`` command."""
    try:
        import subprocess

        out = subprocess.run(
            ["xprintidle"], capture_output=True, text=True, timeout=2
        )
        if out.returncode == 0:
            return int(out.stdout.strip())
    except Exception:
        pass
    return None


def system_idle_ms():
    """Return whole-system idle time in milliseconds, or ``None`` if unknown.

    Uses the X11 XScreenSaver extension via ``ctypes`` (no extra Python
    dependency). Falls back to the ``xprintidle`` command when the extension
    cannot be loaded or queried.
    """
    global _xss_state

    if _xss_state is None:
        _xss_state = _init_xss()

    if _xss_state:
        try:
            xss, dpy, root, info = _xss_state
            xss.XScreenSaverQueryInfo(dpy, root, info)
            return int(info.contents.idle)
        except Exception:
            # Query failed (e.g. display went away); drop the cached handles
            # and let the fallback try from here on.
            _xss_state = False

    return _xprintidle_ms()


def get_monitors():
    """Return a list of (x, y, width, height) tuples, one per monitor.

    Uses the optional ``screeninfo`` package when available so that every
    physical monitor is covered. Falls back to the single virtual screen that
    plain tkinter reports when ``screeninfo`` is not installed.
    """
    try:
        from screeninfo import get_monitors as _get_monitors

        monitors = [(m.x, m.y, m.width, m.height) for m in _get_monitors()]
        if monitors:
            return monitors
    except Exception:
        # screeninfo missing or failed (e.g. no display backend); fall back.
        pass

    root = tk.Tk()
    root.withdraw()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.destroy()
    return [(0, 0, width, height)]


class ScreenCover:
    """Black, full-screen cover spanning all monitors.

    Behaves like a screen saver: user input minimizes the covers (letting the
    desktop and background apps be used), and the covers return once the whole
    computer has been idle for ``idle_timeout_ms``. Ctrl+Q quits.
    """

    # Ignore input for this long after launch (and after each re-cover) so the
    # keystroke/click that started the app (Enter from the menu, the taskbar
    # click, the global shortcut's modifier keys) does not immediately dismiss
    # the cover.
    ARM_DELAY_MS = 600

    # How often to check system idle time while minimized.
    POLL_INTERVAL_MS = 2000

    def __init__(self, idle_timeout_ms=15 * 60 * 1000):
        self.idle_timeout_ms = idle_timeout_ms

        self.root = tk.Tk()
        self.root.withdraw()  # The root stays hidden; covers are Toplevels.

        self.armed = False
        self.covered = True
        self.idle_unavailable = False  # True once we've given up on idle polls.
        self.windows = []
        for x, y, width, height in get_monitors():
            self.windows.append(self._make_cover(x, y, width, height))

    def _make_cover(self, x, y, width, height):
        win = tk.Toplevel(self.root)
        win.configure(background="black", cursor="none")
        win.overrideredirect(True)  # No title bar / borders.
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.attributes("-topmost", True)

        # A black filler so the window is solid black even before mapping.
        canvas = tk.Canvas(
            win, background="black", highlightthickness=0, borderwidth=0
        )
        canvas.pack(fill="both", expand=True)

        # Ctrl+Q quits; any other key (modifier keys such as Shift included) or
        # mouse click minimizes. The more specific Control-q binding wins over
        # the generic <Key> binding, so Esc and friends fall through to
        # minimize.
        win.bind("<Control-q>", self.quit)
        win.bind("<Control-Q>", self.quit)
        for sequence in ("<Key>", "<Shift_L>", "<Shift_R>", "<Button>"):
            win.bind(sequence, self._on_activity)

        return win

    def _on_activity(self, event=None):
        if not self.armed:
            return  # Swallow the launch keystroke/click.
        # Ignore a bare Control press: it arrives as its own <Key> event just
        # before the Q in Ctrl+Q, and minimizing here would steal the quit.
        if getattr(event, "keysym", None) in ("Control_L", "Control_R"):
            return
        self.minimize()

    def minimize(self):
        """Hide every cover so the desktop is usable; poll for idle to return."""
        if not self.covered:
            return
        self.covered = False
        self.armed = False
        try:
            self.windows[0].grab_release()
        except tk.TclError:
            pass
        for win in self.windows:
            try:
                win.withdraw()
            except tk.TclError:
                pass
        if not self.idle_unavailable:
            self.root.after(self.POLL_INTERVAL_MS, self._poll_idle)

    def _poll_idle(self):
        if self.covered:
            return
        idle = system_idle_ms()
        if idle is None:
            # No idle backend available; stop polling rather than busy-loop.
            # The covers stay minimized until the app is quit or relaunched.
            self.idle_unavailable = True
            return
        if idle >= self.idle_timeout_ms:
            self.cover()
        else:
            self.root.after(self.POLL_INTERVAL_MS, self._poll_idle)

    def cover(self):
        """Re-show every cover, grab input, and re-arm after a short delay."""
        if self.covered:
            return
        self.covered = True
        for win in self.windows:
            try:
                win.deiconify()
                win.attributes("-topmost", True)
            except tk.TclError:
                pass
        if self.windows:
            self.windows[0].after(100, self._take_focus)
            self.windows[0].after(self.ARM_DELAY_MS, self._arm)

    def quit(self, _event=None):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        if self.windows:
            # Grab all keyboard + pointer input. Borderless (override-redirect)
            # windows are not given keyboard focus by the window manager, so
            # without a grab only mouse clicks arrive and key presses are lost.
            self.windows[0].after(100, self._take_focus)
            # Arm the input handlers only after the launch input has settled.
            self.windows[0].after(self.ARM_DELAY_MS, self._arm)
        self.root.mainloop()

    def _take_focus(self):
        win = self.windows[0]
        try:
            win.focus_force()
            win.grab_set_global()
        except tk.TclError:
            pass

    def _arm(self):
        self.armed = True


def main():
    import argparse
    import time

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        default=0,
        metavar="SECONDS",
        help="wait this many seconds before covering the screens (default: 0)",
    )
    parser.add_argument(
        "-i",
        "--idle-timeout",
        type=float,
        default=15,
        metavar="MINUTES",
        help="re-cover the screens after the computer is idle this many "
        "minutes (default: 15)",
    )
    args = parser.parse_args()

    if args.delay > 0:
        time.sleep(args.delay)

    ScreenCover(idle_timeout_ms=int(args.idle_timeout * 60 * 1000)).run()


if __name__ == "__main__":
    main()

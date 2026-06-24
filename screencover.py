#!/usr/bin/env python3
"""ScreenCover.

Cover every connected screen with a black canvas, like a screen saver, while
allowing applications to keep running in the background.

The app opens one borderless, full-screen black window per monitor. Press any
key (the Shift key included) or click anywhere to dismiss every cover and exit.
"""

from __future__ import annotations

import tkinter as tk


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
    """Black, full-screen cover spanning all monitors."""

    # Ignore input for this long after launch so the keystroke/click that
    # started the app (Enter from the menu, the taskbar click, the global
    # shortcut's modifier keys) does not immediately dismiss the cover.
    ARM_DELAY_MS = 600

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # The root stays hidden; covers are Toplevels.

        self.armed = False
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

        # Exit on any key (modifier keys such as Shift included) or mouse click.
        for sequence in ("<Key>", "<Shift_L>", "<Shift_R>", "<Button>"):
            win.bind(sequence, self.exit)

        return win

    def exit(self, _event=None):
        if not self.armed:
            return  # Swallow the launch keystroke/click.
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
            # Arm the exit handlers only after the launch input has settled.
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
    args = parser.parse_args()

    if args.delay > 0:
        time.sleep(args.delay)

    ScreenCover().run()


if __name__ == "__main__":
    main()

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

    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # The root stays hidden; covers are Toplevels.

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
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        # Make sure a cover has keyboard focus so key presses are captured.
        if self.windows:
            self.windows[0].after(100, self.windows[0].focus_force)
        self.root.mainloop()


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

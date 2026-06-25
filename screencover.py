#!/usr/bin/env python3
"""ScreenCover.

Cover every connected screen with a black canvas, like a screen saver, while
allowing applications to keep running in the background.

The app opens one borderless, full-screen black window per monitor. Any key
(the Shift key included), a mouse click, or moving the mouse past a small
threshold *minimizes* the covers so the desktop is usable again; the app keeps
running and re-covers every screen once the whole computer has been idle for the
configured time (15 minutes by default). Press Esc to quit.

Only one instance runs at a time, and while running it keeps a minimized window
so the taskbar shows a running indicator. Launching ScreenCover again (from the
global shortcut or the menu), or clicking its taskbar icon, re-covers the screens
on the running instance instead of opening a duplicate.
"""

from __future__ import annotations

import ctypes
import errno
import os
import socket
import sys
import tkinter as tk


# Opt-in diagnostics: enabled by --debug. When off, _log is a no-op.
DEBUG = False


def _log(msg):
    if DEBUG:
        print("[screencover] %s" % msg, file=sys.stderr, flush=True)


# Abstract-namespace UNIX socket used as a single-instance lock and a "re-cover"
# signal channel. The leading NUL byte puts it in Linux's abstract namespace, so
# the name is released automatically when the process dies (no stale lock files,
# no PID-reuse races). Per-user so two desktop users do not clash.
def _instance_addr():
    return f"\0screencover-{os.getuid()}"


def try_become_primary():
    """Claim the single-instance lock.

    Returns a bound, non-blocking datagram socket if we are the first instance,
    or ``None`` if another instance already owns the lock (or the lock cannot be
    used, e.g. on a non-Linux platform — in which case we simply run without the
    guard rather than crash).
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.bind(_instance_addr())
    except OSError as exc:
        sock.close()
        if exc.errno == errno.EADDRINUSE:
            return None  # Another instance holds the lock.
        return None  # Abstract sockets unsupported, etc.; degrade gracefully.
    sock.setblocking(False)
    return sock


def signal_existing_instance():
    """Tell the already-running instance to re-cover the screens."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        client.sendto(b"cover", _instance_addr())
    except OSError:
        pass
    finally:
        client.close()


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
            _log("XScreenSaver: XOpenDisplay(None) returned NULL")
            return False
        root = xlib.XDefaultRootWindow(dpy)
        info = xss.XScreenSaverAllocInfo()
        _log("XScreenSaver: initialized OK")
        return (xss, dpy, root, info)
    except Exception as exc:
        _log("XScreenSaver: init failed: %r" % (exc,))
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
        _log("xprintidle: exit %s, stderr=%r" % (out.returncode, out.stderr))
    except Exception as exc:
        _log("xprintidle: failed: %r" % (exc,))
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
        except Exception as exc:
            # Query failed (e.g. display went away); drop the cached handles
            # and let the fallback try from here on.
            _log("XScreenSaver: query failed: %r" % (exc,))
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
    computer has been idle for ``idle_timeout_ms``. Esc quits.
    """

    # Ignore input for this long after launch (and after each re-cover) so the
    # keystroke/click that started the app (Enter from the menu, the taskbar
    # click, the global shortcut's modifier keys) does not immediately dismiss
    # the cover.
    ARM_DELAY_MS = 600

    # How often to check system idle time while minimized.
    POLL_INTERVAL_MS = 2000

    # How often to check for a re-cover signal from a relaunched instance.
    IPC_POLL_MS = 250

    # Minimize once the pointer moves more than this many pixels from where it
    # was when the first motion after arming arrived. A small threshold (rather
    # than any motion) keeps tiny jitter from dismissing the cover.
    MOTION_THRESHOLD_PX = 30

    def __init__(self, idle_timeout_ms=15 * 60 * 1000, ipc_sock=None):
        self.idle_timeout_ms = idle_timeout_ms
        self.ipc_sock = ipc_sock

        self.root = tk.Tk(className="ScreenCover")
        self.root.withdraw()  # Root stays hidden; covers + tracker are Toplevels.

        # A dedicated, WM-managed tracker window gives the taskbar a running
        # indicator (the dot) while ScreenCover is alive. It is kept minimized so
        # it is never visible on screen. Crucially it is a SIBLING of the covers
        # (both Toplevels of the hidden root), so iconifying it never disturbs
        # the covers' input grab -- iconifying the root *master* would cascade to
        # the covers and break motion/key capture. ``class_`` sets WM_CLASS to
        # "Screencover", which the shell matches against the launcher's
        # StartupWMClass; "Screencover" is already in Tk's normalized form
        # (lowercased then first letter capitalized), so it survives verbatim.
        self.tracker = tk.Toplevel(self.root, class_="Screencover")
        self.tracker.title("ScreenCover")
        self.tracker.bind("<Map>", self._on_tracker_mapped)
        self.tracker.iconify()

        self.armed = False
        self.covered = True
        self.idle_unavailable = False  # True once we've given up on idle polls.
        # Baseline pointer position, set from the first motion event after the
        # cover arms; motion past the threshold from here minimizes. Reset to
        # ``None`` on every arm.
        self._pointer_anchor = None
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

        # Esc quits; any other key (modifier keys such as Shift and Control,
        # and combos like Ctrl+Q, included) or mouse click minimizes. The more
        # specific Escape binding wins over the generic <Key> binding.
        win.bind("<Escape>", self.quit)
        for sequence in ("<Key>", "<Shift_L>", "<Shift_R>", "<Button>"):
            win.bind(sequence, self._on_activity)
        # Pointer motion minimizes too, but only past a threshold (see
        # _on_motion) so a tiny jitter does not dismiss the cover.
        win.bind("<Motion>", self._on_motion)

        return win

    def _on_activity(self, _event=None):
        if not self.armed:
            return  # Swallow the launch keystroke/click.
        self.minimize()

    def _on_tracker_mapped(self, event=None):
        # The tracker maps at startup and whenever its taskbar icon is clicked.
        # Always snap it straight back to minimized so no blank window lingers.
        # Iconifying the tracker is safe: it is a sibling of the covers, so it
        # does not touch their grab (re-minimizing emits only <Unmap>, no loop).
        if event is not None and event.widget is not self.tracker:
            return  # Ignore Map events bubbling from child widgets.
        _log("tracker <Map> (covered=%s)" % self.covered)
        self.tracker.iconify()
        if not self.covered:
            self.cover()  # Restored from minimized via the icon -> cover now.

    def _on_motion(self, event):
        if not self.armed:
            return
        # Anchor on the first motion event after arming so the baseline and the
        # comparison use the same coordinate source (event root coordinates),
        # then minimize once the pointer leaves the threshold box around it.
        if self._pointer_anchor is None:
            self._pointer_anchor = (event.x_root, event.y_root)
            _log("motion: anchor set at %s" % (self._pointer_anchor,))
            return
        ax, ay = self._pointer_anchor
        dx, dy = event.x_root - ax, event.y_root - ay
        _log("motion: at (%s,%s) delta (%s,%s)" % (event.x_root, event.y_root, dx, dy))
        if abs(dx) >= self.MOTION_THRESHOLD_PX or abs(dy) >= self.MOTION_THRESHOLD_PX:
            self.minimize()

    def minimize(self):
        """Hide every cover so the desktop is usable; poll for idle to return."""
        if not self.covered:
            return
        _log("minimize")
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
            _log("idle: no backend available; giving up (will not re-cover)")
            self.idle_unavailable = True
            return
        _log("idle: %s ms (timeout %s ms)" % (idle, self.idle_timeout_ms))
        if idle >= self.idle_timeout_ms:
            self.cover()
        else:
            self.root.after(self.POLL_INTERVAL_MS, self._poll_idle)

    def cover(self):
        """Re-show every cover, grab input, and re-arm after a short delay."""
        if self.covered:
            return
        _log("cover")
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

    def _poll_ipc(self):
        """Re-cover if a relaunched instance signalled us, then reschedule."""
        signalled = False
        try:
            while True:
                self.ipc_sock.recv(64)  # Drain every pending datagram.
                signalled = True
        except BlockingIOError:
            pass
        except OSError:
            pass
        if signalled:
            # cover() is a no-op while already covered, so this only has an
            # effect when we are currently minimized.
            self.cover()
        self.root.after(self.IPC_POLL_MS, self._poll_ipc)

    def quit(self, _event=None):
        if self.ipc_sock is not None:
            try:
                self.ipc_sock.close()
            except OSError:
                pass
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
        if self.ipc_sock is not None:
            self.root.after(self.IPC_POLL_MS, self._poll_ipc)
        self.root.mainloop()

    def _take_focus(self):
        win = self.windows[0]
        try:
            win.focus_force()
            win.grab_set_global()
            _log("grab_set_global on cover[0] OK")
        except tk.TclError as exc:
            _log("grab/focus failed: %r" % (exc,))

    def _arm(self):
        # Reset the motion baseline; _on_motion re-establishes it from the first
        # motion event after arming, so movement is measured from the moment the
        # cover became dismissable rather than from launch.
        self._pointer_anchor = None
        self.armed = True
        _log("armed")


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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print diagnostic events (idle, motion, cover/minimize) to stderr",
    )
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    # Claim the single-instance lock before anything visible (and before the
    # delay sleep) so a double-launch during the delay is still caught.
    server = try_become_primary()
    if server is None:
        signal_existing_instance()
        print("ScreenCover is already running; re-covering the screens.")
        return

    if args.delay > 0:
        time.sleep(args.delay)

    ScreenCover(
        idle_timeout_ms=int(args.idle_timeout * 60 * 1000), ipc_sock=server
    ).run()


if __name__ == "__main__":
    main()

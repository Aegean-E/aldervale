"""Terminal control: VT100 setup, non-blocking key input and frame output.

Supports Windows (ctypes + msvcrt) and POSIX (termios + select) with the same
key vocabulary, and degrades to a no-input stream when stdin is not a TTY.
"""

import ctypes
import os
import shutil
import sys

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
RESET_SGR = "\x1b[0m"
CLEAR_SCREEN = "\x1b[2J"
HOME = "\x1b[H"
ALT_SCREEN_ON = "\x1b[?1049h"
ALT_SCREEN_OFF = "\x1b[?1049l"

_WIN = sys.platform == "win32"

_SPECIAL = {
    "up": "up",
    "down": "down",
    "right": "right",
    "left": "left",
    "\r": "enter",
    "\n": "enter",
    "\x1b": "esc",
    " ": "space",
    "\x7f": "backspace",
    "\x08": "backspace",
    "\t": "tab",
    "P": "f1",
    "Q": "f2",
    "R": "f3",
    "S": "f4",
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
    "H": "home",
    "F": "end",
}

_NUMPAD = {
    "H": "up",
    "P": "down",
    "K": "left",
    "M": "right",
    "G": "home",
    "O": "end",
    "R": "insert",
    "S": "delete",
}


class TerminalError(RuntimeError):
    """Raised when the terminal cannot render the game at all."""


class Terminal:
    """Raw-mode ANSI terminal wrapper with non-blocking key reads."""

    def __init__(self, color=True, use_alt_screen=True):
        self.color = color
        self.use_alt_screen = use_alt_screen
        self._is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        self._old_out_mode = None
        self._old_termios = None
        self._open = False
        self._pending = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()

    def start(self):
        if self._open:
            return
        if _WIN:
            self._open_windows()
        elif self._is_tty:
            import termios
            import tty

            self._old_termios = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
        self._open = True
        seq = HIDE_CURSOR
        if self.use_alt_screen:
            seq = ALT_SCREEN_ON + seq
        self.write(seq + CLEAR_SCREEN + HOME)
        self.flush()

    def _open_windows(self):
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)) == 0:
            raise TerminalError(
                "What: no console output handle is available.\n"
                "Why: ALDERVALE draws with ANSI escapes and needs a real console.\n"
                "Fix: run it inside Windows Terminal, Terminal.app, or any VT100 xterm."
            )
        self._old_out_mode = mode.value
        vt = mode.value | 0x0004
        if kernel32.SetConsoleMode(h_out, vt) == 0:
            raise TerminalError(
                "What: this console refuses virtual-terminal (ANSI) mode.\n"
                "Why: legacy consoles cannot position the cursor per character cell.\n"
                "Fix: run the game in Windows Terminal or a modern terminal emulator."
            )

    def close(self):
        if not self._open:
            return
        self._open = False
        tail = SHOW_CURSOR + RESET_SGR
        if self.use_alt_screen:
            tail = ALT_SCREEN_OFF + tail
        try:
            self.write(tail)
            self.flush()
        finally:
            if self._old_out_mode is not None:
                ctypes.windll.kernel32.SetConsoleMode(
                    ctypes.windll.kernel32.GetStdHandle(-11), self._old_out_mode
                )
                self._old_out_mode = None
            elif self._old_termios is not None:
                import termios

                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_termios)
                self._old_termios = None

    def size(self):
        try:
            sz = shutil.get_terminal_size(fallback=(120, 40))
        except OSError:
            sz = shutil.get_terminal_size(fallback=(120, 40))
        return max(20, sz.columns), max(10, sz.lines)

    def write(self, text):
        sys.stdout.write(text)

    def flush(self):
        sys.stdout.flush()

    def set_title(self, title):
        if self.color or True:
            self.write("\x1b]0;%s\x07" % title)

    def read_key(self):
        """Return one normalized key token or None; never blocks."""
        if self._pending:
            return self._pending.pop(0)
        if not self._is_tty:
            return None
        if _WIN:
            import msvcrt

            if not msvcrt.kbhit():
                return None
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                if not msvcrt.kbhit():
                    return None
                ext = msvcrt.getwch()
                return _NUMPAD.get(ext)
            if ch == "\x1b":
                if msvcrt.kbhit():
                    nxt = msvcrt.getwch()
                    if nxt == "[" or nxt == "O":
                        if msvcrt.kbhit():
                            return _SPECIAL.get(msvcrt.getwch())
                        return "esc"
                    self._pending.append(nxt)
                return "esc"
            return _SPECIAL.get(ch, ch.lower() if ch.isprintable() else None)
        import select

        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return None
        ch = os.read(sys.stdin.fileno(), 1).decode("utf-8", "replace")
        if ch == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], 0.02)
            if ready:
                nxt = os.read(sys.stdin.fileno(), 1).decode("utf-8", "replace")
                if nxt in ("[", "O"):
                    ready2, _, _ = select.select([sys.stdin], [], [], 0.02)
                    if ready2:
                        code = os.read(sys.stdin.fileno(), 1).decode("utf-8", "replace")
                        return _SPECIAL.get(code)
                    return "esc"
                self._pending.append(nxt)
            return "esc"
        return _SPECIAL.get(ch, ch.lower() if ch.isprintable() else None)

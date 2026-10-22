"""Terminal control: VT100 setup, polled key input and frame output.

Supports Windows (ctypes ReadConsoleInputW for true key-down/up tracking)
and POSIX (termios + select with a hold-expiry window) with the same key
vocabulary, and degrades to a no-input stream when stdin is not a TTY.
poll() returns (pressed, held): tokens pressed since the last call and
tokens currently held, which is what a game loop needs.
"""

import ctypes
import os
import shutil
import sys
import time

HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
RESET_SGR = "\x1b[0m"
CLEAR_SCREEN = "\x1b[2J"
HOME = "\x1b[H"
ALT_SCREEN_ON = "\x1b[?1049h"
ALT_SCREEN_OFF = "\x1b[?1049l"

_WIN = sys.platform == "win32"

_HOLD_EXPIRY = 0.45

_VK_TOKENS = {
    0x25: "left", 0x26: "up", 0x27: "right", 0x28: "down",
    0x08: "backspace", 0x09: "tab", 0x0D: "enter", 0x1B: "esc",
    0x20: "space", 0x10: "shift",
    0x70: "f1", 0x71: "f2", 0x72: "f3", 0x73: "f4",
    0xBB: "+", 0xBD: "-",
}

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


def _mouse_event(x, y, buttons, flags):
    """Normalize a Windows MOUSE_EVENT_RECORD into a game mouse token."""
    if flags & 0x0004:
        delta = (buttons >> 16) & 0xFFFF
        if delta > 0x7FFF:
            delta -= 0x10000
        return ("wheel", x, y, 0, 1 if delta > 0 else -1)
    if flags & 0x0002:
        return ("ldown", x, y, buttons, 0)
    if flags & 0x0001:
        return ("move", x, y, buttons, 0)
    if buttons & 0x0001:
        return ("ldown", x, y, buttons, 0)
    if buttons & 0x0002:
        return ("rdown", x, y, buttons, 0)
    return ("up", x, y, buttons, 0)


def vk_token(vk, ch):
    """Map a Windows virtual-key code to a game key token, or None."""
    tok = _VK_TOKENS.get(vk)
    if tok:
        return tok
    if 0x41 <= vk <= 0x5A:
        return chr(vk + 32)
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if ch and ch.isprintable() and ch != " ":
        return ch.lower()
    return None


class TerminalError(RuntimeError):
    """Raised when the terminal cannot render the game at all."""


class Terminal:
    """Raw-mode ANSI terminal wrapper with polled held-key input."""

    def __init__(self, color=True, use_alt_screen=True):
        self.color = color
        self.use_alt_screen = use_alt_screen
        self._is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        self._old_out_mode = None
        self._old_termios = None
        self._open = False
        self._pending = []
        self._held = set()
        self._last_seen = {}
        self._pressed_buf = []
        self._h_in = None
        self._h_out = None
        self._irec = None
        self._csbi = None
        self._kb_fallback = False
        self._kb_misses = 0
        self._mouse_buf = []
        self._old_in_mode = None

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
        kernel32.GetStdHandle.restype = ctypes.c_void_p
        kernel32.GetConsoleMode.argtypes = [ctypes.c_void_p,
                                            ctypes.POINTER(ctypes.c_uint32)]
        kernel32.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        h_out = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not h_out or kernel32.GetConsoleMode(h_out, ctypes.byref(mode)) == 0:
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
        self._init_win_input()

    def _init_win_input(self):
        from ctypes import wintypes

        class COORD(ctypes.Structure):
            _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]

        class KEY_EVENT_RECORD(ctypes.Structure):
            _fields_ = [("bKeyDown", wintypes.BOOL),
                        ("wRepeatCount", wintypes.WORD),
                        ("wVirtualKeyCode", wintypes.WORD),
                        ("wVirtualScanCode", wintypes.WORD),
                        ("uChar", wintypes.WCHAR),
                        ("dwControlKeyState", wintypes.DWORD)]

        class MOUSE_EVENT_RECORD(ctypes.Structure):
            _fields_ = [("dwMousePosition", COORD),
                        ("dwButtonState", wintypes.DWORD),
                        ("dwControlKeyState", wintypes.DWORD),
                        ("dwEventFlags", wintypes.DWORD)]

        class _EVENT(ctypes.Union):
            _fields_ = [("KeyEvent", KEY_EVENT_RECORD),
                        ("MouseEvent", MOUSE_EVENT_RECORD)]

        class INPUT_RECORD(ctypes.Structure):
            _fields_ = [("EventType", wintypes.WORD),
                        ("Event", _EVENT)]

        class SMALL_RECT(ctypes.Structure):
            _fields_ = [("Left", wintypes.SHORT), ("Top", wintypes.SHORT),
                        ("Right", wintypes.SHORT), ("Bottom", wintypes.SHORT)]

        class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
            _fields_ = [("dwSize", COORD),
                        ("dwCursorPosition", COORD),
                        ("wAttributes", wintypes.WORD),
                        ("srWindow", SMALL_RECT),
                        ("dwMaximumWindowSize", COORD)]

        kernel32 = ctypes.windll.kernel32
        h_in = kernel32.GetStdHandle(-10)
        h_out = kernel32.GetStdHandle(-11)
        if not h_in or not h_out:
            self._irec = None
            return
        if kernel32.GetFileType(h_in) != 2:
            self._irec = None
            return
        in_mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h_in, ctypes.byref(in_mode)) == 0:
            self._irec = None
            return
        new_in = (in_mode.value | 0x0010 | 0x0080) & ~0x0040
        if kernel32.SetConsoleMode(h_in, new_in) != 0:
            self._old_in_mode = in_mode.value
        kernel32.GetNumberOfConsoleInputEvents.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        kernel32.GetNumberOfConsoleInputEvents.restype = ctypes.c_int
        kernel32.ReadConsoleInputW.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(INPUT_RECORD), ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32)]
        kernel32.ReadConsoleInputW.restype = ctypes.c_int
        kernel32.GetConsoleScreenBufferInfo.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO)]
        kernel32.GetConsoleScreenBufferInfo.restype = ctypes.c_int
        self._h_in = h_in
        self._h_out = h_out
        self._irec = INPUT_RECORD
        self._csbi = CONSOLE_SCREEN_BUFFER_INFO

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
            if self._old_in_mode is not None and self._h_in:
                ctypes.windll.kernel32.SetConsoleMode(self._h_in,
                                                      self._old_in_mode)
                self._old_in_mode = None
            elif self._old_termios is not None:
                import termios

                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_termios)
                self._old_termios = None

    def size(self):
        if _WIN and self._csbi is not None:
            info = self._csbi()
            if ctypes.windll.kernel32.GetConsoleScreenBufferInfo(
                    self._h_out, ctypes.byref(info)):
                rect = info.srWindow
                cols = rect.Right - rect.Left + 1
                rows = rect.Bottom - rect.Top + 1
                if cols > 0 and rows > 0:
                    return max(20, cols), max(10, rows)
        try:
            sz = shutil.get_terminal_size(fallback=(120, 40))
        except OSError:
            sz = shutil.get_terminal_size(fallback=(120, 40))
        return max(20, sz.columns), max(10, sz.lines)

    def take_mouse(self):
        """Drain queued mouse events: (kind, x, y, buttons, wheel)."""
        events = self._mouse_buf
        self._mouse_buf = []
        return events

    def poll(self):
        """Return (pressed, held): new key tokens and currently held ones."""
        if not self._is_tty:
            return [], set()
        if _WIN and self._irec is not None and not self._kb_fallback:
            kernel32 = ctypes.windll.kernel32
            n = ctypes.c_uint32()
            while kernel32.GetNumberOfConsoleInputEvents(
                    self._h_in, ctypes.byref(n)) and n.value:
                buf = (self._irec * n.value)()
                got = ctypes.c_uint32()
                if not kernel32.ReadConsoleInputW(self._h_in, buf, n.value,
                                                  ctypes.byref(got)):
                    break
                for rec in buf[:got.value]:
                    if rec.EventType == 1:
                        kev = rec.Event.KeyEvent
                        tok = vk_token(kev.wVirtualKeyCode, kev.uChar)
                        if not tok:
                            continue
                        if kev.bKeyDown:
                            if tok not in self._held:
                                self._pressed_buf.append(tok)
                            self._held.add(tok)
                            self._last_seen[tok] = time.monotonic()
                        else:
                            self._held.discard(tok)
                    elif rec.EventType == 2:
                        mev = rec.Event.MouseEvent
                        self._mouse_buf.append(_mouse_event(
                            mev.dwMousePosition.X, mev.dwMousePosition.Y,
                            mev.dwButtonState, mev.dwEventFlags))
                    elif rec.EventType == 4:
                        self._mouse_buf.append(("resize", 0, 0, 0, 0))
            if not self._pressed_buf:
                try:
                    import msvcrt

                    if msvcrt.kbhit():
                        self._kb_misses += 1
                        if self._kb_misses >= 3:
                            self._kb_fallback = True
                except (ImportError, OSError):
                    self._kb_fallback = True
            else:
                self._kb_misses = 0
            if not self._kb_fallback:
                pressed = self._pressed_buf
                self._pressed_buf = []
                return pressed, set(self._held)
        now = time.monotonic()
        while True:
            k = self.read_key()
            if k is None:
                break
            if k not in self._held:
                self._pressed_buf.append(k)
            self._held.add(k)
            self._last_seen[k] = now
        for k in list(self._held):
            if self._last_seen.get(k, 0.0) < now - _HOLD_EXPIRY:
                self._held.discard(k)
        pressed = self._pressed_buf
        self._pressed_buf = []
        return pressed, set(self._held)

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

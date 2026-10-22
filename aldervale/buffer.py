"""Char-cell frame buffer: per-cell glyph, 24-bit colour and depth, diff flush.

The screen is the single rendering surface for the whole game: the voxel
terrain, baked 3D sprites, sky and HUD all write here, then flush() emits only
the cells that changed since the previous frame.
"""

FAR = 1.0e9
NEAREST = -1.0
RAMP = " .,:;-=+*#%@"
_RAMP_INDEX = {ch: i for i, ch in enumerate(RAMP)}


def pack_rgb(r, g, b):
    """Pack float channels into 0xRRGGBB, clamping overflow to 0..255."""
    if r > 255.0:
        r = 255.0
    elif r < 0.0:
        r = 0.0
    if g > 255.0:
        g = 255.0
    elif g < 0.0:
        g = 0.0
    if b > 255.0:
        b = 255.0
    elif b < 0.0:
        b = 0.0
    return (int(r) << 16) | (int(g) << 8) | int(b)


def unpack_rgb(c):
    return (c >> 16) & 255, (c >> 8) & 255, c & 255


def lerp_color(c1, c2, t):
    r1, g1, b1 = unpack_rgb(c1)
    r2, g2, b2 = unpack_rgb(c2)
    return pack_rgb(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)


def scale_color(c, k):
    return pack_rgb(((c >> 16) & 255) * k, ((c >> 8) & 255) * k, (c & 255) * k)


class Screen:
    """A w x h grid of characters with colour, depth and diff-based output."""

    def __init__(self, w, h, color=True):
        self.w = w
        self.h = h
        self.color = color
        self.clear()
        self._prev_chars = ["\x00" * w for _ in range(h)]
        self._prev_fg = [[-1] * w for _ in range(h)]

    def clear(self):
        w, h = self.w, self.h
        self.chars = [[" "] * w for _ in range(h)]
        self.fg = [[0] * w for _ in range(h)]
        self.depth = [[FAR] * w for _ in range(h)]

    def invalidate(self):
        self._prev_chars = ["\x00" * self.w for _ in range(self.h)]
        self._prev_fg = [[-1] * self.w for _ in range(self.h)]

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, ch, color, depth=NEAREST):
        if 0 <= x < self.w and 0 <= y < self.h:
            drow = self.depth[y]
            if depth <= drow[x]:
                drow[x] = depth
                self.chars[y][x] = ch
                self.fg[y][x] = color

    def fill_row(self, y, ch, color, depth=FAR):
        if 0 <= y < self.h:
            row = self.chars[y]
            frow = self.fg[y]
            drow = self.depth[y]
            for x in range(self.w):
                row[x] = ch
                frow[x] = color
                drow[x] = depth

    def text(self, x, y, s, color):
        if y < 0 or y >= self.h:
            return
        row = self.chars[y]
        frow = self.fg[y]
        drow = self.depth[y]
        for i, ch in enumerate(s):
            px = x + i
            if 0 <= px < self.w:
                row[px] = ch
                frow[px] = color
                drow[px] = NEAREST

    def text_centered(self, y, s, color):
        self.text((self.w - len(s)) // 2, y, s, color)

    def box(self, x, y, w, h, color, fill=" "):
        if fill != " ":
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.set(xx, yy, fill, color)
        for xx in range(x, x + w):
            self.set(xx, y, "-", color)
            self.set(xx, y + h - 1, "-", color)
        for yy in range(y + 1, y + h - 1):
            self.set(x, yy, "|", color)
            self.set(x + w - 1, yy, "|", color)
        self.set(x, y, "+", color)
        self.set(x + w - 1, y, "+", color)
        self.set(x, y + h - 1, "+", color)
        self.set(x + w - 1, y + h - 1, "+", color)

    def blit(self, sprite, cx, bottom_row, target_rows, tint=(1.0, 1.0, 1.0), depth=FAR,
             flash=None, alpha=1.0):
        """Draw a baked sprite anchored at (cx, bottom_row) scaled to target_rows."""
        if target_rows < 1 or alpha <= 0.01:
            return
        sh, sw = sprite.h, sprite.w
        if sh < 1 or sw < 1:
            return
        target_cols = max(1.0, target_rows * sw / sh)
        x0 = int(cx - target_cols * 0.5)
        y0 = int(bottom_row - target_rows)
        tr, tg, tb = tint
        fl = flash[0] if flash else 0.0
        fr, fgc, fb = flash[1] if flash else (0, 0, 0)
        step_x = sw / target_cols
        step_y = sh / target_rows
        downsample = target_rows < sh - 0.5
        lev_rows = sprite.lev if downsample else None
        for ty in range(int(target_rows)):
            sy = int(ty * step_y)
            if sy >= sh:
                sy = sh - 1
            srow = sprite.chars[sy]
            prow = sprite.colors[sy]
            sy2 = sy + 1 if downsample and sy + 1 < sh else sy
            py = y0 + ty
            if py < 0 or py >= self.h:
                continue
            crow = self.chars[py]
            cfrow = self.fg[py]
            cdrow = self.depth[py]
            for txi in range(int(target_cols)):
                sx = int(txi * step_x)
                if sx >= sw:
                    sx = sw - 1
                if downsample:
                    sx2 = sx + 1 if sx + 1 < sw else sx
                    levs = []
                    cols = []
                    chars4 = []
                    for yy in (sy, sy2):
                        lr = lev_rows[yy]
                        cr = sprite.chars[yy]
                        pr = sprite.colors[yy]
                        lv = lr[sx]
                        if lv >= 0:
                            levs.append(lv)
                            cols.append(pr[sx])
                            chars4.append(cr[sx])
                        lv = lr[sx2]
                        if lv >= 0:
                            levs.append(lv)
                            cols.append(pr[sx2])
                            chars4.append(cr[sx2])
                    if not levs:
                        continue
                    if len(levs) == 4:
                        mean = (levs[0] + levs[1] + levs[2] + levs[3]) * 0.25
                        ch = RAMP[int(mean + 0.5)]
                        best = 0
                        for i in range(1, 4):
                            if levs[i] > levs[best]:
                                best = i
                        c = cols[best]
                    else:
                        best = 0
                        for i in range(1, len(levs)):
                            if levs[i] > levs[best]:
                                best = i
                        ch = chars4[best]
                        c = cols[best]
                else:
                    ch = srow[sx]
                    if ch == " ":
                        continue
                    c = prow[sx]
                if alpha < 0.99 and ((txi * 73 + ty * 151) & 255) > alpha * 255:
                    continue
                px = x0 + txi
                if px < 0 or px >= self.w:
                    continue
                if depth > cdrow[px]:
                    continue
                r = ((c >> 16) & 255) * tr
                g = ((c >> 8) & 255) * tg
                b = (c & 255) * tb
                if fl > 0.0:
                    r += (fr - r) * fl
                    g += (fgc - g) * fl
                    b += (fb - b) * fl
                crow[px] = ch
                cfrow[px] = pack_rgb(r, g, b)
                cdrow[px] = depth

    def frame_text(self):
        return "\n".join("".join(row) for row in self.chars)

    def flush(self, term):
        """Emit only changed cells; returns the number of bytes written."""
        parts = []
        ap = parts.append
        prev_c = self._prev_chars
        prev_f = self._prev_fg
        color = self.color
        for y in range(self.h):
            crow = self.chars[y]
            frow = self.fg[y]
            row_s = "".join(crow)
            prow = prev_c[y]
            pfrow = prev_f[y]
            if row_s == prow and frow == pfrow:
                continue
            x = 0
            w = self.w
            while x < w:
                if crow[x] == prow[x] and frow[x] == pfrow[x]:
                    x += 1
                    continue
                xs = x
                buf = []
                last_fg = -1
                while x < w and (crow[x] != prow[x] or frow[x] != pfrow[x]):
                    if color and frow[x] != last_fg:
                        c = frow[x]
                        buf.append("\x1b[38;2;%d;%d;%dm" %
                                   ((c >> 16) & 255, (c >> 8) & 255, c & 255))
                        last_fg = frow[x]
                    buf.append(crow[x])
                    x += 1
                ap("\x1b[%d;%dH%s" % (y + 1, xs + 1, "".join(buf)))
            prev_c[y] = row_s
            prev_f[y] = frow[:]
        if not parts:
            return 0
        payload = "".join(parts)
        if color:
            payload += "\x1b[0m"
        term.write(payload)
        term.flush()
        return len(payload)

    def stats(self):
        filled = sum(1 for row in self.chars for ch in row if ch != " ")
        return filled

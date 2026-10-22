"""Procedural island heightfield with biome colours, baked light and water.

One deterministic pass builds three aligned grids (height, packed RGB colour
with slope light baked in, and a light byte for the ASCII ramp) plus a path
mask the world generator uses to keep trees off the roads.
"""

import math
from array import array

from .buffer import pack_rgb
from .noise import fbm, rand01

SUN = (0.42, 0.78, 0.46)

_DEEP = pack_rgb(24, 46, 74)
_SAND = pack_rgb(196, 178, 128)
_GRASS1 = pack_rgb(88, 128, 60)
_GRASS2 = pack_rgb(70, 106, 52)
_FOREST = pack_rgb(56, 86, 46)
_DIRT = pack_rgb(142, 116, 78)
_ROCK = pack_rgb(128, 126, 122)
_ROCK_D = pack_rgb(100, 98, 96)
_SNOW = pack_rgb(228, 230, 238)
_FLOWERS = (
    pack_rgb(224, 196, 84),
    pack_rgb(208, 120, 140),
    pack_rgb(196, 150, 220),
    pack_rgb(230, 230, 240),
)


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


class Terrain:
    """A square island world grid sampled at one unit per cell."""

    def __init__(self, seed, size=320, water=1.4, octaves=4,
                 village=None, castle=None, camp=None):
        self.seed = seed
        self.W = size
        self.water = water
        half = size * 0.5
        if village is None:
            village = (int(size * 0.50), int(size * 0.68))
        if castle is None:
            castle = (int(size * 0.47), int(size * 0.22))
        if camp is None:
            camp = (int(size * 0.80), int(size * 0.55))
        self.village = village
        self.castle = castle
        self.camp = camp
        self.heights = []
        self.colors = []
        self.lights = []
        self.path_mask = bytearray(size * size)
        self._generate(octaves, half)

    def _generate(self, octaves, half):
        W = self.W
        seed = self.seed
        vx, vz = self.village
        kx, kz = self.castle
        cx, cz = self.camp
        grass_mix = []
        forest = []
        gres = 2
        gw = W // gres + 1
        for z in range(gw):
            for x in range(gw):
                grass_mix.append(fbm(x * 0.075, z * 0.075, seed + 3, 2))
                forest.append(fbm(x * 0.045, z * 0.045, seed + 11, 2))
        heights = self.heights
        for z in range(W):
            row = array("f", bytes(4 * W))
            for x in range(W):
                h = (fbm(x * 0.021, z * 0.021, seed, octaves) - 0.34) * 24.0
                d = ((x - half) ** 2 + (z - half) ** 2) ** 0.5 / half
                if d < 0.62:
                    core = _smooth((0.62 - d) / 0.62)
                    h += core * 5.0
                if d > 0.70:
                    fall = _smooth(min(1.0, (d - 0.70) / 0.42))
                    h -= fall * fall * 26.0
                if z < W * 0.30:
                    zone = _smooth(1.0 - z / (W * 0.30))
                    m = fbm(x * 0.013, z * 0.013, seed + 31, 2)
                    h += zone * m * m * 15.0
                dkh = ((x - kx) ** 2 + (z - kz) ** 2) ** 0.5
                if dkh < 26.0:
                    bump = 1.0 - dkh / 26.0
                    h += bump * bump * 8.5
                row[x] = h
            heights.append(row)
        v_target = 4.4
        for z in range(vz - 34, vz + 34):
            if z < 0 or z >= W:
                continue
            for x in range(vx - 34, vx + 34):
                if x < 0 or x >= W:
                    continue
                d = ((x - vx) ** 2 + (z - vz) ** 2) ** 0.5
                if d < 34.0:
                    w = _smooth(1.0 - d / 34.0) * 0.92
                    heights[z][x] += (v_target - heights[z][x]) * w
        for z in range(cz - 16, cz + 16):
            if z < 0 or z >= W:
                continue
            for x in range(cx - 16, cx + 16):
                if x < 0 or x >= W:
                    continue
                d = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if d < 16.0:
                    w = _smooth(1.0 - d / 16.0) * 0.6
                    target = heights[cz][cx] if 0 <= cz < W and 0 <= cx < W else 4.0
                    heights[z][x] += (target - heights[z][x]) * w
        self._stamp_path((vx, vz + 4), (kx, kz + 15))
        self._stamp_path((vx + 6, vz + 2), (cx - 8, cz + 4))
        self._stamp_ring(vx, vz, 9.0)
        self._paint(grass_mix, forest, gres)

    def _stamp_disk(self, x, z, r):
        W = self.W
        ir = int(r) + 1
        for zz in range(int(z) - ir, int(z) + ir + 1):
            if zz < 0 or zz >= W:
                continue
            for xx in range(int(x) - ir, int(x) + ir + 1):
                if xx < 0 or xx >= W:
                    continue
                if (xx - x) ** 2 + (zz - z) ** 2 <= r * r:
                    self.path_mask[zz * W + xx] = 1

    def _stamp_path(self, a, b):
        ax, az = a
        bx, bz = b
        mx, mz = (ax + bx) * 0.5 + (bz - az) * 0.18, (az + bz) * 0.5 - (bx - ax) * 0.18
        length = ((bx - ax) ** 2 + (bz - az) ** 2) ** 0.5
        steps = max(2, int(length * 1.5))
        for i in range(steps + 1):
            t = i / steps
            t2 = t * t
            t1 = 1.0 - t
            px = t1 * t1 * ax + 2 * t1 * t * mx + t2 * t2 * bx
            pz = t1 * t1 * az + 2 * t1 * t * mz + t2 * t2 * bz
            self._stamp_disk(px, pz, 2.2)

    def _stamp_ring(self, cx, cz, r):
        rr = r - 1.2
        steps = int(2 * 3.14159265 * r)
        for i in range(steps):
            a = i * 2 * 3.14159265 / steps
            self._stamp_disk(cx + math.cos(a) * rr, cz + math.sin(a) * rr, 1.1)

    def _paint(self, grass_mix, forest, gres):
        W = self.W
        water = self.water
        path = self.path_mask
        sxx, szz = SUN[0], SUN[2]
        nn = (sxx * sxx + szz * szz) ** 0.5
        sxx, szz = sxx / nn, szz / nn
        for z in range(W):
            hrow = self.heights[z]
            hup = self.heights[z - 1] if z > 0 else hrow
            hdn = self.heights[z + 1] if z < W - 1 else hrow
            crow = array("i", bytes(4 * W))
            lrow = array("B", bytes(W))
            for x in range(W):
                h = hrow[x]
                hl = hup[x] if z > 0 else h
                hr = hdn[x] if z < W - 1 else h
                dx = (hrow[x + 1] if x < W - 1 else h) - (hrow[x - 1] if x > 0 else h)
                dz = hr - hl
                nl = (dx * dx + dz * dz) ** 0.5
                if nl > 1e-6:
                    lx, lz = -dx / (nl * 2.0), -dz / (nl * 2.0)
                    light = 0.52 + 0.48 * max(0.0, lx * sxx + lz * szz)
                else:
                    light = 1.0
                gm = grass_mix[(z // gres) * (W // gres + 1) + x // gres]
                fo = forest[(z // gres) * (W // gres + 1) + x // gres]
                if h <= water + 0.75:
                    c = _SAND
                else:
                    c = _GRASS1 if gm > 0.5 else _GRASS2
                    if fo > 0.60 and x > W * 0.35:
                        c = _FOREST
                    if h > 15.0:
                        t = min(1.0, (h - 15.0) / 5.0)
                        c = _lerp_packed(c, _SNOW, t)
                    if nl > 2.1:
                        c = _ROCK if gm > 0.5 else _ROCK_D
                if path[z * W + x]:
                    c = _DIRT
                rv = rand01(x, z, self.seed + 77)
                if rv < 0.004 and c in (_GRASS1, _GRASS2):
                    c = _FLOWERS[int(rand01(x, z, self.seed + 91) * 3.999)]
                k = light if h > water else 0.8
                crow[x] = pack_rgb(
                    min(255, ((c >> 16) & 255) * k),
                    min(255, ((c >> 8) & 255) * k),
                    min(255, (c & 255) * k),
                )
                lrow[x] = max(0, min(255, int(light * 255)))
            self.colors.append(crow)
            self.lights.append(lrow)
        self._smooth_lights()


    def _smooth_lights(self):
        """Blur the char-luminance grid so ground glyphs read as coherent shade."""
        W = self.W
        src = self.lights
        out = []
        for z in range(W):
            cur = src[z]
            prev = src[z - 1] if z > 0 else cur
            nxt = src[z + 1] if z < W - 1 else cur
            row = array("B", bytes(W))
            for x in range(W):
                xm = x - 1 if x > 0 else x
                xp = x + 1 if x < W - 1 else x
                v = (prev[xm] + 2 * prev[x] + prev[xp]
                     + 2 * (cur[xm] + 2 * cur[x] + cur[xp])
                     + nxt[xm] + 2 * nxt[x] + nxt[xp]) // 16
                row[x] = v
            out.append(row)
        self.lights = out

    def in_bounds(self, x, z):
        return 0 <= int(x) < self.W and 0 <= int(z) < self.W

    def height(self, x, z):
        ix, iz = int(x), int(z)
        if 0 <= ix < self.W and 0 <= iz < self.W:
            return self.heights[iz][ix]
        return self.water - 3.0

    def color(self, x, z):
        ix, iz = int(x), int(z)
        if 0 <= ix < self.W and 0 <= iz < self.W:
            return self.colors[iz][ix]
        return _DEEP

    def light(self, x, z):
        ix, iz = int(x), int(z)
        if 0 <= ix < self.W and 0 <= iz < self.W:
            return self.lights[iz][ix] / 255.0
        return 0.5

    def is_path(self, x, z):
        ix, iz = int(x), int(z)
        if 0 <= ix < self.W and 0 <= iz < self.W:
            return self.path_mask[iz * self.W + ix] == 1
        return False

    def walkable(self, x, z):
        if not self.in_bounds(x, z):
            return False
        ix, iz = int(x), int(z)
        h = self.heights[iz][ix]
        if h <= self.water + 0.12:
            return False
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if abs(self.heights[iz + dz][ix + dx] - h) > 1.5:
                return False
        return True

    def forest_at(self, x, z):
        ix, iz = int(x), int(z)
        W = self.W
        if not (0 <= ix < W and 0 <= iz < W):
            return False
        gres = 2
        fo = fbm((ix // gres) * 0.045, (iz // gres) * 0.045, self.seed + 11, 2)
        return fo > 0.60 and ix > W * 0.35


def _lerp_packed(c1, c2, t):
    return pack_rgb(
        ((c1 >> 16) & 255) + (((c2 >> 16) & 255) - ((c1 >> 16) & 255)) * t,
        ((c1 >> 8) & 255) + (((c2 >> 8) & 255) - ((c1 >> 8) & 255)) * t,
        (c1 & 255) + ((c2 & 255) - (c1 & 255)) * t,
    )

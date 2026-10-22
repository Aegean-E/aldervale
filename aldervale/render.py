"""Scene renderer: animated sky, voxel-marched terrain and billboard sprites.

The terrain uses a column ray-march over the heightfield (front-to-back with a
per-column hidden-row buffer and per-cell depth), then entities are blitted
far-to-near as depth-tested billboards with fog and day/night tinting.
"""

import math

from .buffer import pack_rgb, FAR
from .mesh import RAMP
from .noise import fbm, rand01

FOV = 1.22
MAX_DIST = 230.0
FOG_START = 55.0

SKY_ZENITH_DAY = pack_rgb(88, 140, 204)
SKY_HORIZON_DAY = pack_rgb(168, 200, 226)
SKY_ZENITH_NIGHT = pack_rgb(7, 9, 20)
SKY_HORIZON_NIGHT = pack_rgb(24, 28, 46)
SKY_DAWN = pack_rgb(224, 138, 84)
SUN_COLOR = pack_rgb(255, 238, 188)
MOON_COLOR = pack_rgb(208, 216, 238)
STAR_COLOR = pack_rgb(198, 208, 238)
CLOUD_DAY = pack_rgb(228, 234, 242)
CLOUD_NIGHT = pack_rgb(52, 58, 78)
WATER_DEEP = pack_rgb(22, 48, 80)
WATER_LIT = pack_rgb(66, 122, 162)

_SIN64 = [math.sin(i * math.pi / 32.0) for i in range(64)]
_CLOUDS = None
_CLOUD_W = 256
_CLOUD_H = 26


def _clouds():
    global _CLOUDS
    if _CLOUDS is None:
        _CLOUDS = []
        for y in range(_CLOUD_H):
            row = []
            for x in range(_CLOUD_W):
                v = fbm(x * 0.045, y * 0.11, 909, 3)
                v += (1.0 - y / _CLOUD_H) * 0.06
                row.append(v)
            _CLOUDS.append(row)
    return _CLOUDS


class Camera:
    """View parameters plus precomputed per-column ray angles."""

    __slots__ = ("x", "y", "z", "yaw", "pitch", "w", "h", "f", "fy", "horizon",
                 "col_angle", "dist")

    def __init__(self, w, h, x, z, y, yaw, pitch=0.30, dist=7.0):
        self.w, self.h = w, h
        self.x, self.y, self.z = x, y, z
        self.yaw = yaw
        self.pitch = pitch
        self.dist = dist
        self.f = (w * 0.5) / math.tan(FOV * 0.5)
        self.fy = self.f * 0.5
        horizon = int(h * 0.5 - math.tan(pitch) * self.fy)
        self.horizon = max(3, min(h - 3, horizon))
        half_tan = math.tan(FOV * 0.5)
        self.col_angle = [math.atan((x - w * 0.5 + 0.5) / (w * 0.5) * half_tan)
                          for x in range(w)]


class Env:
    """Per-frame atmosphere derived from the world clock."""

    __slots__ = ("t", "day_t", "daylight", "night", "warm", "ambient", "fog",
                 "zenith", "horizon_col", "sun_el")

    def __init__(self, day_t, t):
        self.t = t
        self.day_t = day_t
        phase = day_t * 2.0 * math.pi
        sun_el = math.sin(phase)
        self.sun_el = sun_el
        daylight = max(0.0, min(1.0, (sun_el + 0.1) * 2.6))
        self.daylight = daylight
        self.night = 1.0 - daylight
        self.warm = max(0.0, 1.0 - abs(sun_el) * 2.8)
        zen = _mix(SKY_ZENITH_NIGHT, SKY_ZENITH_DAY, daylight)
        hor = _mix(SKY_HORIZON_NIGHT, SKY_HORIZON_DAY, daylight)
        hor = _mix(hor, SKY_DAWN, self.warm * 0.6)
        zen = _mix(zen, SKY_DAWN, self.warm * 0.18)
        self.zenith = zen
        self.horizon_col = hor
        self.fog = hor
        ar = 0.36 + 0.64 * daylight
        ag = 0.40 + 0.58 * daylight
        ab = 0.55 + 0.39 * daylight
        wk = self.warm * 0.5
        self.ambient = (min(1.1, ar * (1.0 + wk * 0.1)), ag * (1.0 - wk * 0.04),
                        ab * (1.0 - wk * 0.1))


def _mix(c1, c2, t):
    if t <= 0.0:
        return c1
    if t >= 1.0:
        return c2
    return pack_rgb(
        ((c1 >> 16) & 255) + (((c2 >> 16) & 255) - ((c1 >> 16) & 255)) * t,
        ((c1 >> 8) & 255) + (((c2 >> 8) & 255) - ((c1 >> 8) & 255)) * t,
        (c1 & 255) + ((c2 & 255) - (c1 & 255)) * t,
    )


def render_scene(screen, world, cam, env):
    """Draw sky, terrain, entities and fireflies into the screen buffer."""
    _sky(screen, cam, env)
    _terrain(screen, world.terrain, cam, env)
    _entities(screen, world, cam, env)
    if env.night > 0.15:
        _fireflies(screen, world, cam, env)


def _sky(screen, cam, env):
    w, h = screen.w, screen.h
    chars, fg, depth = screen.chars, screen.fg, screen.depth
    horizon = cam.horizon
    zenith, horc = env.zenith, env.horizon_col
    zr, zg, zb = (zenith >> 16) & 255, (zenith >> 8) & 255, zenith & 255
    hr, hgc, hb = (horc >> 16) & 255, (horc >> 8) & 255, horc & 255
    rows = max(1, horizon)
    row_colors = []
    for y in range(min(horizon, h)):
        t = y / rows
        t2 = t * t * (3.0 - 2.0 * t)
        row_colors.append(pack_rgb(hr + (zr - hr) * t2, hgc + (zg - hgc) * t2,
                                   hb + (zb - hb) * t2))
    for y in range(min(horizon, h)):
        col = row_colors[y]
        crow = chars[y]
        frow = fg[y]
        drow = depth[y]
        tt = y / rows
        fill = 0.20 + 0.42 * (1.0 - tt)
        fill2 = fill * 0.5
        for x in range(w):
            v = (x * 53 + y * 131 + ((x >> 2) * 29)) & 255
            fv = fill * 255.0
            if v < fv:
                crow[x] = ":" if v < fill2 * 255.0 else "."
            else:
                crow[x] = " "
            frow[x] = col
            drow[x] = FAR
    if env.night > 0.05:
        alpha = env.night
        for i in range(110):
            if rand01(i, 3, 42) > alpha:
                continue
            az = rand01(i, 1, 42) * 6.28318
            el = 0.06 + rand01(i, 2, 42) * 0.85
            rel = az - cam.yaw
            while rel > math.pi:
                rel -= 6.28318
            while rel < -math.pi:
                rel += 6.28318
            if abs(rel) > FOV * 0.62:
                continue
            col = int(w * 0.5 + math.tan(rel) / math.tan(FOV * 0.5) * w * 0.5)
            row = int(horizon - el * cam.fy * 0.85)
            if 0 <= col < w and 0 <= row < horizon:
                bright = rand01(i, 4, 42)
                chars[row][col] = "+" if bright > 0.8 else "."
                fg[row][col] = STAR_COLOR
    sun_az = 2.35
    _disc(screen, cam, sun_az, env.sun_el * 0.6 + 0.05, 4, SUN_COLOR, "@#")
    moon_el = -env.sun_el * 0.6 + 0.05
    if env.night > 0.2 and moon_el > -0.05:
        _disc(screen, cam, sun_az + math.pi, moon_el, 3, MOON_COLOR, "@%")
    _clouds_draw(screen, cam, env)


def _disc(screen, cam, az, el, radius, color, chars_pair):
    w = screen.w
    rel = az - cam.yaw
    while rel > math.pi:
        rel -= 6.28318
    while rel < -math.pi:
        rel += 6.28318
    if abs(rel) > FOV * 0.75 or el < -0.1:
        return
    col = int(w * 0.5 + math.tan(rel) / math.tan(FOV * 0.5) * w * 0.5)
    row = int(cam.horizon - el * cam.fy)
    r2 = radius * radius
    for dy in range(-radius - 1, radius + 2):
        for dx in range(-radius - 1, radius + 2):
            d2 = dx * dx + dy * dy * 2.6
            px, py = col + dx, row + dy
            if 0 <= px < screen.w and 0 <= py < screen.h:
                if d2 <= r2 * 0.45:
                    screen.chars[py][px] = chars_pair[0]
                    screen.fg[py][px] = color
                elif d2 <= r2:
                    screen.chars[py][px] = chars_pair[1]
                    screen.fg[py][px] = color


def _clouds_draw(screen, cam, env):
    clouds = _clouds()
    w, h = screen.w, screen.h
    horizon = cam.horizon
    chars, fg = screen.chars, screen.fg
    drift = int(env.t * 1.4)
    ccol = _mix(CLOUD_NIGHT, CLOUD_DAY, env.daylight)
    top = max(0, horizon - int(horizon * 0.9))
    for y in range(top, max(top, horizon - 1)):
        ty = int((horizon - y) / max(1.0, horizon) * _CLOUD_H * 1.7)
        if ty >= _CLOUD_H:
            continue
        crow = clouds[ty]
        crow_chars = chars[y]
        frow = fg[y]
        for x in range(w):
            v = crow[(x + drift) & 255]
            if v > 0.54:
                d = (v - 0.54) * 3.2
                if ((x * 7 + y * 13) & 15) < d * 16:
                    crow_chars[x] = "," if d < 0.5 else (":" if d < 0.9 else "~")
                    frow[x] = ccol


def _terrain(screen, ter, cam, env):
    w, h = screen.w, screen.h
    chars, fg, depth = screen.chars, screen.fg, screen.depth
    heights, colors, lights = ter.heights, ter.colors, ter.lights
    W = ter.W
    water = ter.water
    camx, camy, camz = cam.x, cam.y, cam.z
    yaw = cam.yaw
    horizon = cam.horizon
    fy = cam.fy
    col_angle = cam.col_angle
    t = env.t
    ar, ag, ab = env.ambient
    fogc = env.fog
    fgr = ((fogc >> 16) & 255) / 255.0
    fgg = ((fogc >> 8) & 255) / 255.0
    fgb = (fogc & 255) / 255.0
    fog_end = MAX_DIST * 0.96
    inv_fog = 1.0 / (fog_end - FOG_START)
    n_ramp = len(RAMP) - 1
    sin64 = _SIN64
    wdr, wdg, wdb = (WATER_DEEP >> 16) & 255, (WATER_DEEP >> 8) & 255, WATER_DEEP & 255
    wlr, wlg, wlb = (WATER_LIT >> 16) & 255, (WATER_LIT >> 8) & 255, WATER_LIT & 255
    water_hi = water + 0.03
    foam_hi = water + 0.55
    for x in range(w):
        ang = yaw + col_angle[x]
        dx = math.sin(ang)
        dz = math.cos(ang)
        hidden = h
        z = 0.6
        step = 0.34
        stag = 0
        while z < MAX_DIST and hidden > 0:
            wx = camx + dx * z
            wz = camz + dz * z
            if 0.0 <= wx < W - 1.0 and 0.0 <= wz < W - 1.0:
                ix = int(wx)
                iz = int(wz)
                gh = heights[iz][ix]
            else:
                gh = water - 2.5
            dy = gh - camy
            py = int(horizon - dy / z * fy)
            if py < hidden:
                fog = z - FOG_START
                if fog <= 0.0:
                    fog = 0.0
                else:
                    fog *= inv_fog
                    if fog > 1.0:
                        fog = 1.0
                inv_f = 1.0 - fog
                if gh <= water_hi:
                    sp = sin64[int(wx * 3.1 + wz * 1.7 + t * 5.0) & 63]
                    k = (sp + 1.0) * 0.5
                    r = (wdr + (wlr - wdr) * k) * inv_f + fgr * fog * 255.0
                    g = (wdg + (wlg - wdg) * k) * inv_f + fgg * fog * 255.0
                    b = (wdb + (wlb - wdb) * k) * inv_f + fgb * fog * 255.0
                    packed = pack_rgb(r, g, b)
                    if sp > 0.45:
                        chs = ("~", "~", "-", "~")
                    elif sp > -0.15:
                        chs = ("-", "-", "~", "-")
                    else:
                        chs = (".", "-", ".", "-")
                else:
                    c = colors[iz][ix]
                    lum = lights[iz][ix] * 0.0039
                    r = ((c >> 16) & 255) * ar * inv_f + fgr * fog * 255.0
                    g = ((c >> 8) & 255) * ag * inv_f + fgg * fog * 255.0
                    b = (c & 255) * ab * inv_f + fgb * fog * 255.0
                    packed = pack_rgb(r, g, b)
                    ci = int(lum * n_ramp * 0.9)
                    if gh <= foam_hi:
                        chs = ("~", "-", "~", "-")
                    else:
                        ca = ci - 1 if ci > 0 else 0
                        cb = ci + 1 if ci < n_ramp else n_ramp
                        chs = (RAMP[ci], RAMP[ca], RAMP[cb], RAMP[ci])
                crow0, crow1, crow2, crow3 = chs
                frow = fg
                seg = (int(wx) * 196613 ^ int(wz) * 30103) & 3
                for y in range(py, hidden):
                    depth[y][x] = z
                    m = (seg ^ y) & 3
                    if m == 0:
                        chars[y][x] = crow0
                    elif m == 1:
                        chars[y][x] = crow1
                    elif m == 2:
                        chars[y][x] = crow2
                    else:
                        chars[y][x] = crow3
                    frow[y][x] = packed
                hidden = py
                stag = 0
            else:
                stag += 1
                if stag > 55 and hidden <= horizon:
                    break
            z += step
            step *= 1.0135


def _entities(screen, world, cam, env):
    sin_y = math.sin(cam.yaw)
    cos_y = math.cos(cam.yaw)
    half_tan = math.tan(FOV * 0.5)
    ar, ag, ab = env.ambient
    fogc = env.fog
    fgr = ((fogc >> 16) & 255) / 255.0
    fgg = ((fogc >> 8) & 255) / 255.0
    fgb = (fogc & 255) / 255.0
    fog_end = MAX_DIST * 0.96
    inv_fog = 1.0 / (fog_end - FOG_START)
    vis = []
    max_d2 = MAX_DIST * MAX_DIST
    for ent in world.entities:
        dx = ent.x - cam.x
        dz = ent.z - cam.z
        if dx * dx + dz * dz > max_d2:
            continue
        depth_z = dx * sin_y + dz * cos_y
        if depth_z < 0.7:
            continue
        side = dx * cos_y - dz * sin_y
        lim = depth_z * half_tan * 1.35 + 8.0
        if side < -lim or side > lim:
            continue
        vis.append((depth_z, side, ent))
    vis.sort(key=lambda e: -e[0])
    atlas = world.atlas
    for depth_z, side, ent in vis:
        rows = ent.height * ent.scale / depth_z * cam.fy
        gy = ent.ground_y + ent.y_off
        bottom = cam.horizon - (gy - cam.y) / depth_z * cam.fy
        if bottom < -2 or bottom - rows > cam.h + 2:
            continue
        col = cam.w * 0.5 + side / depth_z * cam.f
        fog = depth_z - FOG_START
        if fog <= 0.0:
            fog = 0.0
        else:
            fog *= inv_fog
            if fog > 1.0:
                fog = 1.0
        tr = ar * (1.0 - fog) + fgr * fog
        tg = ag * (1.0 - fog) + fgg * fog
        tb = ab * (1.0 - fog) + fgb * fog
        frame = atlas.yaw_frame(ent.yaw, cam.yaw)
        sprite = atlas.get(ent.model, ent.pose, frame)
        if sprite is None:
            continue
        if rows < 1.2:
            py = int(bottom)
            if 0 <= py < screen.h and 0 <= int(col) < screen.w:
                screen.set(int(col), py, "." if rows < 0.7 else ":", sprite.colors[0][0],
                           depth_z)
            continue
        flash = ent.flash_color if ent.flash > 0.0 else None
        screen.blit(sprite, col, bottom, rows, tint=(tr, tg, tb), depth=depth_z,
                    flash=flash)
        if sprite.glow is not None and env.night > 0.12:
            screen.blit(sprite.glow, col, bottom, rows, tint=(1.0, 1.0, 0.9),
                        depth=depth_z, alpha=min(0.95, env.night * 1.1))


def _fireflies(screen, world, cam, env):
    sin_y = math.sin(cam.yaw)
    cos_y = math.cos(cam.yaw)
    t = env.t
    for i, (fx, fz, phase) in enumerate(world.fireflies):
        wx = fx + math.sin(t * 0.7 + phase) * 1.2
        wz = fz + math.cos(t * 0.5 + phase * 1.3) * 1.2
        wy = world.terrain.height(wx, wz) + 0.8 + math.sin(t * 1.3 + phase) * 0.4
        dx = wx - cam.x
        dz = wz - cam.z
        depth_z = dx * sin_y + dz * cos_y
        if depth_z < 0.8 or depth_z > 60.0:
            continue
        side = dx * cos_y - dz * sin_y
        col = int(cam.w * 0.5 + side / depth_z * cam.f)
        row = int(cam.horizon - (wy - cam.y) / depth_z * cam.fy)
        if 0 <= col < screen.w and 0 <= row < screen.h:
            blink = math.sin(t * 3.0 + phase * 7.0)
            if blink > 0.1:
                screen.set(col, row, "o" if blink > 0.7 else ".",
                           pack_rgb(200, 255, 130), depth_z)

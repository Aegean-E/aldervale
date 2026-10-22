"""Low-poly mesh construction and the mesh-to-ASCII sprite baker.

Models are built from boxes, cones, cylinders and spheres, then baked into
char-cell sprites: perspective projection, backface culling, per-face Lambert
shading mapped onto a luminance ramp, z-buffered scanline rasterisation and a
deterministic dither that breaks banding into pixel-like grain.
"""

import math

from . import math3d as m3
from .buffer import _RAMP_INDEX, pack_rgb, RAMP

AMBIENT = 0.34
LIGHT_DIR = m3.normalize((0.30, 0.60, 0.62))
OUTLINE_CHAR = ":"
OUTLINE_DARKEN = 0.55
_INF = float("inf")


class Sprite:
    """A baked char-cell image with per-cell packed RGB colour."""

    __slots__ = ("chars", "colors", "lev", "w", "h", "glow")

    def __init__(self, chars, colors, lev=None, glow=None):
        self.chars = chars
        self.colors = colors
        self.w = len(chars[0]) if chars else 0
        self.h = len(chars)
        if lev is None:
            lev = [[_RAMP_INDEX.get(ch, 0) if ch != " " else -1 for ch in row]
                   for row in chars]
        self.lev = lev
        self.glow = glow

    def filled(self):
        return sum(1 for row in self.chars for ch in row if ch != " ")


class Mesh:
    """Static geometry: vertices plus quad faces with colour and emissive flag."""

    __slots__ = ("verts", "faces")

    def __init__(self, verts, faces):
        self.verts = verts
        self.faces = faces


class MeshBuilder:
    """Assembles transformed primitives into one Mesh."""

    def __init__(self):
        self._verts = []
        self._faces = []
        self._fc = 0

    def build(self):
        return Mesh(self._verts, self._faces)

    def _quad(self, p0, p1, p2, p3, color, emissive, smooth=False):
        base = len(self._verts)
        self._verts.extend((p0, p1, p2, p3))
        self._fc += 1
        j = ((self._fc * 137 + 41) & 15) - 7
        r = min(255, max(0, ((color >> 16) & 255) + j))
        g = min(255, max(0, ((color >> 8) & 255) + j))
        b = min(255, max(0, (color & 255) + j))
        self._faces.append((base, base + 1, base + 2, base + 3,
                            pack_rgb(r, g, b), emissive, smooth))

    def quad(self, p0, p1, p2, p3, color, emissive=False):
        self._quad(p0, p1, p2, p3, color, emissive)

    def _rot(self, ry, rx, rz, pivot):
        mats = []
        if ry:
            mats.append(m3.rot_y_matrix(ry))
        if rx:
            mats.append(m3.rot_x_matrix(rx))
        if rz:
            mats.append(m3.rot_z_matrix(rz))
        if not mats:
            return None
        m = mats[0]
        for mm in mats[1:]:
            m = m3.mat_mul(mm, m)
        return m, pivot

    def box(self, cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0, rz=0.0,
            pivot=None, emissive=False):
        """Axis-aligned box, optionally rotated about a pivot point."""
        if pivot is None:
            pivot = (cx, cy, cz)
        rp = self._rot(ry, rx, rz, pivot)
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5

        def pt(x, y, z):
            p = (cx + x, cy + y, cz + z)
            if rp is not None:
                d = m3.sub(p, rp[1])
                d = m3.mat_vec(rp[0], d)
                p = m3.add(d, rp[1])
            return p

        x0, x1 = -hx, hx
        y0, y1 = -hy, hy
        z0, z1 = -hz, hz
        c = (
            pt(x0, y0, z0), pt(x1, y0, z0), pt(x1, y1, z0), pt(x0, y1, z0),
            pt(x0, y0, z1), pt(x1, y0, z1), pt(x1, y1, z1), pt(x0, y1, z1),
        )
        self._quad(c[4], c[5], c[6], c[7], color, emissive)
        self._quad(c[1], c[0], c[3], c[2], color, emissive)
        self._quad(c[5], c[1], c[2], c[6], color, emissive)
        self._quad(c[0], c[4], c[7], c[3], color, emissive)
        self._quad(c[7], c[6], c[2], c[3], color, emissive)
        self._quad(c[0], c[1], c[5], c[4], color, emissive)

    def cone(self, cx, y0, cz, r, h, seg=7, color=0x808080, ry=0.0, rx=0.0,
             rz=0.0, pivot=None, emissive=False):
        """Tapered tube from a base ring to a near-point apex ring."""
        if pivot is None:
            pivot = (cx, y0, cz)
        rp = self._rot(ry, rx, rz, pivot)
        top, bot = [], []
        for i in range(seg):
            a = i * 2.0 * math.pi / seg
            ca, sa = math.cos(a), math.sin(a)
            top.append((cx + ca * r * 0.12, y0 + h, cz + sa * r * 0.12))
            bot.append((cx + ca * r, y0, cz + sa * r))
        if rp is not None:
            top = [self._tp(p, rp) for p in top]
            bot = [self._tp(p, rp) for p in bot]
        for i in range(seg):
            j = (i + 1) % seg
            self._quad(bot[i], bot[j], top[j], top[i], color, emissive, True)

    def cylinder(self, cx, y0, cz, r, h, seg=8, color=0x808080, axis="y",
                 ry=0.0, rx=0.0, rz=0.0, pivot=None, emissive=False):
        if pivot is None:
            pivot = (cx, y0, cz)
        rp = self._rot(ry, rx, rz, pivot)
        lo, hi = [], []
        for i in range(seg):
            a = i * 2.0 * math.pi / seg
            ca, sa = math.cos(a) * r, math.sin(a) * r
            if axis == "y":
                lo.append((cx + ca, y0, cz + sa))
                hi.append((cx + ca, y0 + h, cz + sa))
            elif axis == "x":
                lo.append((cx, y0 + ca, cz + sa))
                hi.append((cx + h, y0 + ca, cz + sa))
            else:
                lo.append((cx + ca, y0 + ca, cz))
                hi.append((cx + ca, y0 + ca, cz + h))
        if rp is not None:
            lo = [self._tp(p, rp) for p in lo]
            hi = [self._tp(p, rp) for p in hi]
        for i in range(seg):
            j = (i + 1) % seg
            self._quad(lo[i], lo[j], hi[j], hi[i], color, emissive, True)

    def sphere(self, cx, cy, cz, rx, ry, rz, seg=7, rings=4, color=0x808080,
               emissive=False):
        lat0, lat1 = -1.15, 1.15
        for i in range(rings):
            la = lat0 + (lat1 - lat0) * i / rings
            lb = lat0 + (lat1 - lat0) * (i + 1) / rings
            ca, sa = math.cos(la), math.sin(la)
            cb, sb = math.cos(lb), math.sin(lb)
            for j in range(seg):
                a0 = j * 2.0 * math.pi / seg
                a1 = (j + 1) * 2.0 * math.pi / seg
                p00 = (cx + math.cos(a0) * rx * ca, cy + sa * ry, cz + math.sin(a0) * rz * ca)
                p01 = (cx + math.cos(a1) * rx * ca, cy + sa * ry, cz + math.sin(a1) * rz * ca)
                p10 = (cx + math.cos(a0) * rx * cb, cy + sb * ry, cz + math.sin(a0) * rz * cb)
                p11 = (cx + math.cos(a1) * rx * cb, cy + sb * ry, cz + math.sin(a1) * rz * cb)
                self._quad(p10, p11, p01, p00, color, emissive, True)

    @staticmethod
    def _tp(p, rp):
        d = m3.sub(p, rp[1])
        return m3.add(m3.mat_vec(rp[0], d), rp[1])

    def merge(self, mesh, matrix=None, offset=(0.0, 0.0, 0.0), pivot=(0.0, 0.0, 0.0)):
        """Append mesh, optionally transformed about pivot then translated."""
        base = len(self._verts)
        for p in mesh.verts:
            q = m3.sub(p, pivot)
            if matrix is not None:
                q = m3.mat_vec(matrix, q)
            q = m3.add(q, pivot)
            self._verts.append((q[0] + offset[0], q[1] + offset[1], q[2] + offset[2]))
        for f in mesh.faces:
            self._faces.append((base + f[0], base + f[1], base + f[2], base + f[3],
                                f[4], f[5], f[6]))
            self._fc += 1


def _raster_tri(chars, colors, zbuf, cw, ch, tri, color, ramp, n_ramp):
    """Scanline-fill one projected triangle: z-test plus Gouraud luminance."""
    tri = sorted(tri, key=lambda p: p[1])
    (x0, y0, d0, l0), (x1, y1, d1, l1), (x2, y2, d2, l2) = tri
    if y2 - y0 < 1e-7:
        return
    ys = max(0, int(math.ceil(y0 - 0.5)))
    ye = min(ch - 1, int(y2 + 0.5))
    y01 = y1 - y0 if y1 - y0 else 1e-7
    y12 = y2 - y1 if y2 - y1 else 1e-7
    y02 = y2 - y0
    scale = n_ramp - 1
    for y in range(ys, ye + 1):
        py = y + 0.5
        if py < y0 or py > y2:
            continue
        ta = (py - y0) / y02
        xa = x0 + (x2 - x0) * ta
        da = d0 + (d2 - d0) * ta
        la = l0 + (l2 - l0) * ta
        if py < y1:
            tb = (py - y0) / y01
            xb = x0 + (x1 - x0) * tb
            db = d0 + (d1 - d0) * tb
            lb = l0 + (l1 - l0) * tb
        else:
            tb = (py - y1) / y12
            xb = x1 + (x2 - x1) * tb
            db = d1 + (d2 - d1) * tb
            lb = l1 + (l2 - l1) * tb
        if xb < xa:
            xa, xb, da, db, la, lb = xb, xa, db, da, lb, la
        xs = max(0, int(math.ceil(xa - 0.5)))
        xe = min(cw - 1, int(xb + 0.5))
        if xe < xs:
            continue
        span = (xb - xa) if (xb - xa) > 1e-7 else 1e-7
        row = y * cw
        for x in range(xs, xe + 1):
            t = (x + 0.5 - xa) / span
            d = da + (db - da) * t
            idx = row + x
            if d < zbuf[idx]:
                zbuf[idx] = d
                lum = la + (lb - la) * t
                ci = int(lum * scale)
                if ci < 0:
                    ci = 0
                elif ci >= n_ramp:
                    ci = n_ramp - 1
                chars[idx] = ramp[ci]
                colors[idx] = color


def bake_sprite(mesh, yaw=0.0, pitch=0.30, dist=9.0, f=140.0, aspect=0.5,
                canvas=(64, 44), light=None, ramp=RAMP, crop=True):
    """Bake a mesh into a Sprite viewed from yaw/pitch at the given scale.

    The virtual camera sits on +Z looking at the model; f is the focal scale
    in cells per world unit at distance `dist`.
    """
    cw, ch = canvas
    cx, cy = cw * 0.5, ch * 0.5
    L = light or LIGHT_DIR
    n_ramp = len(ramp)
    matrix = m3.mat_mul(m3.rot_x_matrix(pitch), m3.rot_y_matrix(yaw))
    rotated = [m3.mat_vec(matrix, v) for v in mesh.verts]
    proj = []
    for tv in rotated:
        d = dist - tv[2]
        if d < 0.5:
            d = 0.5
        proj.append((cx + tv[0] / d * f, cy - tv[1] / d * f * aspect, d))
    has_em = any(f_[5] for f_ in mesh.faces)
    chars = [" "] * (cw * ch)
    colors = [0] * (cw * ch)
    zbuf = [_INF] * (cw * ch)
    gchars = gcolors = gzbuf = None
    if has_em:
        gchars = [" "] * (cw * ch)
        gcolors = [0] * (cw * ch)
        gzbuf = [_INF] * (cw * ch)
    smooth_normals = _smooth_normals(mesh)
    for face in mesh.faces:
        ia, ib, ic, idd, col, em, smooth = face
        n = m3.face_normal(rotated[ia], rotated[ib], rotated[ic])
        if n[2] <= 0.02:
            continue
        face_lum = AMBIENT + (1.0 - AMBIENT) * max(0.0, m3.dot(n, L))
        if smooth:
            lums = []
            for vi in (ia, ib, ic, idd):
                vn = smooth_normals.get(mesh.verts[vi])
                if vn is None:
                    vl = face_lum
                else:
                    rn = m3.mat_vec(matrix, m3.normalize(vn))
                    vl = AMBIENT + (1.0 - AMBIENT) * max(0.0, m3.dot(rn, L))
                lums.append(vl)
        else:
            lums = [face_lum, face_lum, face_lum, face_lum]
        if em:
            lums = [max(v, 0.88) for v in lums]
        k = 0.42 + 0.58 * face_lum
        fc = pack_rgb(
            min(255, ((col >> 16) & 255) * k),
            min(255, ((col >> 8) & 255) * k),
            min(255, (col & 255) * k),
        )
        p0, p1, p2, p3 = proj[ia], proj[ib], proj[ic], proj[idd]
        t0 = (p0[0], p0[1], p0[2], lums[0])
        t1 = (p1[0], p1[1], p1[2], lums[1])
        t2 = (p2[0], p2[1], p2[2], lums[2])
        t3 = (p3[0], p3[1], p3[2], lums[3])
        _raster_tri(chars, colors, zbuf, cw, ch, (t0, t1, t2), fc, ramp, n_ramp)
        _raster_tri(chars, colors, zbuf, cw, ch, (t0, t2, t3), fc, ramp, n_ramp)
        if em and gchars is not None:
            gl = pack_rgb(
                min(255, ((col >> 16) & 255) * 1.05),
                min(255, ((col >> 8) & 255) * 1.05),
                min(255, (col & 255) * 1.05),
            )
            g0 = (t0[0], t0[1], t0[2], 0.95)
            g1 = (t1[0], t1[1], t1[2], 0.95)
            g2 = (t2[0], t2[1], t2[2], 0.95)
            g3 = (t3[0], t3[1], t3[2], 0.95)
            _raster_tri(gchars, gcolors, gzbuf, cw, ch, (g0, g1, g2), gl, ramp, n_ramp)
            _raster_tri(gchars, gcolors, gzbuf, cw, ch, (g0, g2, g3), gl, ramp, n_ramp)
    _outline(chars, colors, cw, ch)
    box = _crop_bounds(chars, cw, ch) if crop else (0, 0, cw, ch)
    main = _pack_grid(chars, colors, cw, ch, box)
    glow = None
    if gchars is not None:
        glow = _pack_grid(gchars, gcolors, cw, ch, box)
    main.glow = glow
    return main


def _smooth_normals(mesh):
    """Position-keyed vertex normals of smooth faces, for Gouraud shading."""
    acc = {}
    for face in mesh.faces:
        if len(face) < 7 or not face[6]:
            continue
        ia, ib, ic, idd = face[0], face[1], face[2], face[3]
        n = m3.face_normal(mesh.verts[ia], mesh.verts[ib], mesh.verts[ic])
        for vi in (ia, ib, ic, idd):
            key = mesh.verts[vi]
            a = acc.get(key)
            if a is None:
                acc[key] = [n[0], n[1], n[2]]
            else:
                a[0] += n[0]
                a[1] += n[1]
                a[2] += n[2]
    return acc


def _outline(chars, colors, cw, ch):
    """Darken the silhouette edge so models read as shapes, not noise."""
    marks = []
    for y in range(ch):
        row = y * cw
        up = row - cw
        down = row + cw
        for x in range(cw):
            idx = row + x
            if chars[idx] == " ":
                continue
            if ((x == 0 or chars[idx - 1] == " ")
                    or (x == cw - 1 or chars[idx + 1] == " ")
                    or (y == 0 or chars[up + x] == " ")
                    or (y == ch - 1 or chars[down + x] == " ")):
                marks.append(idx)
    for idx in marks:
        c = colors[idx]
        chars[idx] = OUTLINE_CHAR
        colors[idx] = pack_rgb(((c >> 16) & 255) * OUTLINE_DARKEN,
                               ((c >> 8) & 255) * OUTLINE_DARKEN,
                               (c & 255) * OUTLINE_DARKEN)


def _crop_bounds(chars, cw, ch):
    """Bounding box (x0, y0, x1, y1) of non-space cells, or a 1x1 fallback."""
    x0, y0, x1, y1 = cw, ch, -1, -1
    for y in range(ch):
        row = y * cw
        for x in range(cw):
            if chars[row + x] != " ":
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
                if y < y0:
                    y0 = y
                if y > y1:
                    y1 = y
    if x1 < x0:
        return 0, 0, 1, 1
    return x0, y0, x1 + 1, y1 + 1


def _pack_grid(chars, colors, cw, ch, box):
    """Slice flat buffers into row-lists limited to the given crop box."""
    x0, y0, x1, y1 = box
    out_chars = []
    out_colors = []
    for y in range(y0, y1):
        base = y * cw
        out_chars.append("".join(chars[base + x] for x in range(x0, x1)))
        out_colors.append([colors[base + x] for x in range(x0, x1)])
    return Sprite(out_chars, out_colors)

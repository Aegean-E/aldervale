"""Deterministic integer-hash value noise and fractal sums (no random module)."""

_MASK = 0xFFFFFFFF
_INV32 = 1.0 / 4294967296.0


def hash2i(ix, iy, seed):
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & _MASK
    n = (n ^ (n >> 13)) & _MASK
    n = (n * 1274126177) & _MASK
    n = (n ^ (n >> 16)) & _MASK
    return n


def rand01(ix, iy, seed):
    return hash2i(ix, iy, seed) * _INV32


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise(x, y, seed):
    ix, iy = int(x), int(y)
    fx, fy = _smooth(x - ix), _smooth(y - iy)
    a = rand01(ix, iy, seed)
    b = rand01(ix + 1, iy, seed)
    c = rand01(ix, iy + 1, seed)
    d = rand01(ix + 1, iy + 1, seed)
    ab = a + (b - a) * fx
    cd = c + (d - c) * fx
    return ab + (cd - ab) * fy


def fbm(x, y, seed, octaves=4, lacunarity=2.0, gain=0.5):
    total = 0.0
    amp = 1.0
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += value_noise(x * freq, y * freq, seed) * amp
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm

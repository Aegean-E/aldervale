"""Every 3D model in the realm: actors, creatures, flora and architecture.

All builders return a MeshBuilder mesh in metres with the ground at y=0 and
the model facing +Z. Actors take a pose dict (limb angles); props take a seed
or frame for deterministic variation and animation.
"""

import math

from . import math3d as m3
from .buffer import pack_rgb
from .mesh import MeshBuilder


def C(r, g, b):
    return pack_rgb(r, g, b)


STEEL = C(198, 203, 212)
STEEL_D = C(150, 156, 168)
IRON = C(84, 88, 96)
BLUE = C(46, 76, 126)
BLUE_D = C(33, 55, 92)
GOLD = C(216, 180, 82)
GOLD_D = C(172, 138, 52)
LEATHER = C(116, 82, 48)
LEATHER_D = C(88, 62, 34)
PLUME = C(168, 44, 50)
BONE = C(228, 224, 208)
BONE_D = C(182, 178, 160)
SKIN = C(214, 178, 142)
HAIR_D = C(58, 46, 36)
WOOD = C(124, 88, 52)
WOOD_D = C(92, 64, 36)
PLASTER = C(224, 216, 198)
STRAW = C(198, 160, 88)
STONE = C(138, 136, 132)
STONE_D = C(108, 106, 102)
ROOF = C(96, 104, 118)
GREEN1 = C(66, 104, 52)
GREEN2 = C(52, 88, 44)
GREEN_D = C(40, 70, 36)
TRUNK = C(98, 74, 48)
TRUNK_D = C(76, 56, 36)
PINE = C(48, 86, 54)
PINE_D = C(38, 70, 44)
GREY_FUR = C(124, 122, 130)
GREY_FUR_D = C(94, 92, 100)
RED_CLOTH = C(160, 42, 50)
DARKRED = C(96, 26, 32)
RUST = C(152, 118, 80)
EMBER = C(244, 150, 60)
FLAME = C(242, 128, 36)
FLAME_HI = C(255, 214, 80)
CRYSTAL = C(120, 220, 255)
POTION_C = C(212, 62, 74)
VILE_GREEN = C(58, 78, 62)
EYE_DARK = C(24, 20, 16)


def _dead_wrap(b, rx=-1.45, dz=-0.3):
    inner = b.build()
    out = MeshBuilder()
    out.merge(inner, matrix=m3.rot_x_matrix(rx), pivot=(0.0, 0.12, 0.0),
              offset=(0.0, 0.02, dz))
    return out


def knight(pose=None, palette=None):
    """An armoured warrior with sword and shield; pose drives limb angles."""
    p = dict(leg_l=0.0, leg_r=0.0, arm_l=0.0, arm_r=0.0, sword=0.0, lean=0.0,
             dead=0.0)
    if pose:
        p.update(pose)
    pal = dict(steel=STEEL, steel_d=STEEL_D, trim=BLUE, trim_d=BLUE_D, gold=GOLD,
               leather=LEATHER, plume=PLUME, blade=STEEL)
    if palette:
        pal.update(palette)
    b = MeshBuilder()
    lean = p["lean"]
    for side, key in ((-1.0, "leg_l"), (1.0, "leg_r")):
        ang = p[key]
        hip = (0.13 * side, 0.88, 0.0)
        b.box(0.13 * side, 0.66, 0.0, 0.17, 0.44, 0.19, pal["steel_d"], rx=ang, pivot=hip)
        b.box(0.13 * side, 0.24, 0.01, 0.15, 0.44, 0.16, pal["steel"], rx=ang * 1.12, pivot=hip)
        b.box(0.13 * side, 0.47, 0.10, 0.14, 0.10, 0.07, pal["steel"], rx=ang * 1.12, pivot=hip)
        b.box(0.13 * side, 0.07, 0.10, 0.17, 0.14, 0.30, pal["leather"], rx=ang * 1.12, pivot=hip)
    lp = (0.0, 0.9, 0.0)

    def part(cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0, rz=0.0, emissive=False):
        b.box(cx, cy, cz, sx, sy, sz, color, ry=ry, rx=rx + lean, rz=rz,
              pivot=lp, emissive=emissive)

    part(0.0, 0.92, 0.0, 0.50, 0.10, 0.31, pal["leather"])
    part(0.0, 0.92, 0.158, 0.10, 0.06, 0.02, pal["gold"])
    part(0.0, 1.18, 0.0, 0.50, 0.56, 0.31, pal["steel"])
    part(0.0, 1.17, 0.158, 0.34, 0.50, 0.02, pal["trim"])
    part(0.0, 0.965, 0.160, 0.35, 0.07, 0.025, pal["gold"])
    part(0.0, 1.24, 0.162, 0.06, 0.06, 0.02, pal["gold"])
    part(0.0, 1.31, 0.162, 0.035, 0.05, 0.02, pal["gold"])
    part(0.0, 1.17, 0.162, 0.035, 0.05, 0.02, pal["gold"])
    part(-0.075, 1.24, 0.162, 0.05, 0.035, 0.02, pal["gold"])
    part(0.075, 1.24, 0.162, 0.05, 0.035, 0.02, pal["gold"])
    part(0.0, 1.17, -0.158, 0.34, 0.50, 0.02, pal["trim_d"])
    part(-0.32, 1.41, 0.0, 0.22, 0.16, 0.27, pal["steel_d"], ry=0.16)
    part(0.32, 1.41, 0.0, 0.22, 0.16, 0.27, pal["steel_d"], ry=-0.16)
    arm_l = p["arm_l"]
    arm_r = p["arm_r"]
    for side, ang in ((-1.0, arm_l), (1.0, arm_r)):
        sh = (0.33 * side, 1.36, 0.0)
        b.box(0.35 * side, 1.18, 0.0, 0.14, 0.36, 0.16, pal["steel_d"], rx=ang, pivot=sh)
        b.box(0.36 * side, 0.95, 0.01, 0.15, 0.32, 0.17, pal["steel"], rx=ang * 1.15, pivot=sh)
    part(0.0, 1.56, 0.01, 0.27, 0.27, 0.27, pal["steel"])
    part(0.0, 1.57, 0.147, 0.19, 0.05, 0.01, EYE_DARK)
    part(0.0, 1.75, 0.0, 0.05, 0.14, 0.31, pal["plume"])
    part(0.0, 1.81, -0.11, 0.05, 0.20, 0.16, pal["plume"], rz=-0.25)
    sw = _sword(pal)
    hand = m3.add((0.34, 1.36, 0.0), m3.mat_vec(m3.rot_x_matrix(arm_r), (0.0, -0.44, 0.04)))
    b.merge(sw, matrix=m3.rot_x_matrix(arm_r + p["sword"]), offset=hand)
    shl = (0.33, 1.36, 0.0)
    b.box(-0.45, 1.14, 0.05, 0.06, 0.52, 0.42, pal["trim_d"], ry=0.12,
          rx=arm_l * 0.6, pivot=shl)
    b.box(-0.485, 1.14, 0.05, 0.012, 0.38, 0.10, pal["gold"], ry=0.12,
          rx=arm_l * 0.6, pivot=shl)
    b.box(-0.485, 1.22, 0.05, 0.012, 0.10, 0.30, pal["gold"], ry=0.12,
          rx=arm_l * 0.6, pivot=shl)
    if p["dead"] > 0.0:
        return _dead_wrap(b).build()
    return b.build()


def _sword(pal, blade_len=0.95, blade_w=0.10, blade=None):
    s = MeshBuilder()
    s.box(0.0, -0.02, 0.0, 0.05, 0.18, 0.06, pal.get("leather", LEATHER_D))
    s.box(0.0, -0.12, 0.0, 0.06, 0.05, 0.07, pal.get("gold", GOLD_D))
    s.box(0.0, 0.08, 0.0, 0.18, 0.05, 0.08, pal.get("gold", GOLD_D))
    s.box(0.0, 0.08 + blade_len * 0.5, 0.0, 0.045, blade_len, blade_w,
          blade if blade is not None else pal.get("blade",
                                                  pal.get("steel", STEEL)))
    return s.build()


def guard(pose=None):
    """A castle guard with spear and heraldic tabard."""
    p = dict(idle=0.0)
    if pose:
        p.update(pose)
    pal = dict(trim=C(120, 34, 36), trim_d=C(88, 24, 28), plume=C(220, 200, 120))
    b = MeshBuilder()
    inner = knight({"leg_l": 0.0, "leg_r": 0.0, "arm_l": -0.25, "arm_r": 0.25},
                   palette=pal)
    b.merge(inner)
    spear = MeshBuilder()
    spear.box(0.0, -0.85, 0.0, 0.045, 1.9, 0.045, WOOD_D)
    spear.cone(0.0, 0.1, 0.0, 0.045, 0.34, 5, STEEL_D)
    sp = spear.build()
    hand = (0.40, 1.02, 0.06)
    b.merge(sp, matrix=m3.rot_x_matrix(0.12), offset=hand)
    return b.build()


def wolf(pose=None):
    """A grey wolf; diagonal-gait legs and a lunge pose."""
    p = dict(leg_fl=0.0, leg_fr=0.0, leg_rl=0.0, leg_rr=0.0, lunge=0.0,
             dead=0.0)
    if pose:
        p.update(pose)
    b = MeshBuilder()
    body_rx = -0.28 * p["lunge"]
    bp = (0.0, 0.52, 0.0)

    def part(cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0):
        b.box(cx, cy, cz, sx, sy, sz, color, ry=ry, rx=rx + body_rx, pivot=bp)

    part(0.0, 0.55, 0.0, 0.30, 0.30, 0.92, GREY_FUR)
    part(0.0, 0.60, 0.26, 0.32, 0.33, 0.34, GREY_FUR_D)
    part(0.0, 0.72, -0.05, 0.26, 0.07, 0.72, GREY_FUR_D)
    part(0.0, 0.67, 0.58, 0.24, 0.22, 0.26, GREY_FUR)
    part(0.0, 0.62, 0.74, 0.12, 0.11, 0.16, GREY_FUR_D)
    b.box(-0.07, 0.82, 0.50, 0.06, 0.11, 0.05, GREY_FUR_D)
    b.box(0.07, 0.82, 0.50, 0.06, 0.11, 0.05, GREY_FUR_D)
    b.box(-0.07, 0.70, 0.705, 0.05, 0.05, 0.02, EYE_DARK)
    b.box(0.07, 0.70, 0.705, 0.05, 0.05, 0.02, EYE_DARK)
    b.box(0.0, 0.66, -0.56, 0.09, 0.09, 0.46, GREY_FUR, rx=0.45,
          pivot=(0.0, 0.62, -0.40))
    lunge_f = 1.0 * p["lunge"]
    for x, z, key in ((-0.11, 0.34, "leg_fl"), (0.11, 0.34, "leg_fr"),
                      (-0.11, -0.36, "leg_rl"), (0.11, -0.36, "leg_rr")):
        ang = p[key] * (1.0 - lunge_f) + lunge_f * (1.2 if z > 0 else -1.0)
        b.box(x, 0.32, z, 0.09, 0.62, 0.11, GREY_FUR_D, rx=ang,
              pivot=(x, 0.62, z))
    if p["dead"] > 0.0:
        return _dead_wrap(b, rx=-1.5, dz=-0.2).build()
    return b.build()


def skeleton(pose=None, captain=False):
    """A rattling skeleton; the captain is larger, crowned and caped."""
    p = dict(leg_l=0.0, leg_r=0.0, arm_l=0.0, arm_r=0.0, sword=0.0, lean=0.0,
             dead=0.0)
    if pose:
        p.update(pose)
    s = 1.35 if captain else 1.0
    b = MeshBuilder()
    lean = p["lean"]
    for side, key in ((-1.0, "leg_l"), (1.0, "leg_r")):
        ang = p[key]
        hip = (0.11 * s * side, 0.9 * s, 0.0)
        b.box(0.11 * s * side, 0.46 * s, 0.0, 0.08 * s, 0.88 * s, 0.08 * s,
              BONE, rx=ang, pivot=hip)
    lp = (0.0, 0.9 * s, 0.0)

    def part(cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0, rz=0.0, emissive=False):
        b.box(cx, cy, cz, sx, sy, sz, color, ry=ry, rx=rx + lean, rz=rz,
              pivot=lp, emissive=emissive)

    part(0.0, 0.94 * s, 0.0, 0.30 * s, 0.14 * s, 0.16 * s, BONE_D)
    part(0.0, 1.18 * s, 0.0, 0.34 * s, 0.42 * s, 0.20 * s, BONE)
    for i in range(3):
        part(0.0, (1.05 + i * 0.11) * s, 0.105 * s, 0.30 * s, 0.035 * s,
             0.012 * s, BONE_D)
    arm_l = p["arm_l"]
    arm_r = p["arm_r"]
    for side, ang in ((-1.0, arm_l), (1.0, arm_r)):
        sh = (0.22 * s * side, 1.34 * s, 0.0)
        b.box(0.24 * s * side, 1.0 * s, 0.01, 0.07 * s, 0.72 * s, 0.07 * s,
              BONE, rx=ang, pivot=sh)
    part(0.0, 1.52 * s, 0.01, 0.20 * s, 0.20 * s, 0.20 * s, BONE)
    part(0.0, 1.53 * s, 0.106 * s, 0.05 * s, 0.05 * s, 0.01 * s, EYE_DARK)
    part(-0.05 * s, 1.53 * s, 0.106 * s, 0.04 * s, 0.04 * s, 0.01 * s, EYE_DARK)
    part(0.05 * s, 1.53 * s, 0.106 * s, 0.04 * s, 0.04 * s, 0.01 * s, EYE_DARK)
    part(0.0, 1.42 * s, 0.05 * s, 0.13 * s, 0.06 * s, 0.12 * s, BONE_D)
    if captain:
        part(0.0, 1.62 * s, 0.0, 0.05 * s, 0.05 * s, 0.26 * s, BONE_D)
        for hx in (-0.09, 0.0, 0.09):
            b.cone(hx * s, 1.60 * s, 0.0, 0.035 * s, 0.22 * s, 5,
                   C(150, 130, 96), rz=0.5 if hx else 0.0, rx=0.5 if not hx else 0.0,
                   ry=0.5 if hx else 0.0)
        part(0.0, 1.22 * s, -0.14 * s, 0.5 * s, 0.72 * s, 0.025 * s, DARKRED)
        part(0.0, 1.5 * s, -0.14 * s, 0.42 * s, 0.14 * s, 0.028 * s, C(70, 18, 22))
        great = _sword(dict(steel=RUST, steel_d=RUST, trim=GOLD_D, gold=GOLD_D,
                            leather=LEATHER_D, blade=C(168, 160, 148)),
                       blade_len=1.25 * s, blade_w=0.15 * s)
        hand = m3.add((0.26 * s, 1.34 * s, 0.0),
                      m3.mat_vec(m3.rot_x_matrix(arm_r), (0.0, -0.4 * s, 0.03)))
        b.merge(great, matrix=m3.rot_x_matrix(arm_r + p["sword"]), offset=hand)
    else:
        rust = _sword(dict(steel=RUST, steel_d=RUST, trim=IRON, gold=IRON,
                           leather=LEATHER_D, blade=RUST), blade_len=0.8,
                      blade_w=0.09)
        hand = m3.add((0.26, 1.34, 0.0),
                      m3.mat_vec(m3.rot_x_matrix(arm_r), (0.0, -0.42, 0.03)))
        b.merge(rust, matrix=m3.rot_x_matrix(arm_r + p["sword"]), offset=hand)
    if p["dead"] > 0.0:
        return _dead_wrap(b, rx=-1.5, dz=-0.2).build()
    return b.build()


def bandit(pose=None):
    """A hooded road-agent with a dagger."""
    p = dict(leg_l=0.0, leg_r=0.0, arm_l=0.0, arm_r=0.0, sword=0.0, lean=0.0,
             dead=0.0)
    if pose:
        p.update(pose)
    tunic = C(98, 76, 52)
    hood = C(70, 56, 40)
    b = MeshBuilder()
    lean = p["lean"]
    for side, key in ((-1.0, "leg_l"), (1.0, "leg_r")):
        ang = p[key]
        hip = (0.12 * side, 0.88, 0.0)
        b.box(0.12 * side, 0.46, 0.0, 0.14, 0.84, 0.15, LEATHER_D, rx=ang, pivot=hip)
        b.box(0.12 * side, 0.06, 0.08, 0.15, 0.12, 0.26, C(52, 40, 28), rx=ang, pivot=hip)
    lp = (0.0, 0.9, 0.0)

    def part(cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0):
        b.box(cx, cy, cz, sx, sy, sz, color, ry=ry, rx=rx + lean, pivot=lp)

    part(0.0, 1.14, 0.0, 0.44, 0.5, 0.27, tunic)
    part(0.0, 0.92, 0.0, 0.44, 0.09, 0.28, LEATHER_D)
    part(0.2, 0.98, 0.15, 0.1, 0.12, 0.03, C(160, 130, 70))
    for side, ang in ((-1.0, p["arm_l"]), (1.0, p["arm_r"])):
        sh = (0.28 * side, 1.32, 0.0)
        b.box(0.29 * side, 1.12, 0.0, 0.12, 0.34, 0.14, tunic, rx=ang, pivot=sh)
        b.box(0.30 * side, 0.88, 0.01, 0.11, 0.3, 0.13, SKIN, rx=ang * 1.15, pivot=sh)
    part(0.0, 1.52, 0.0, 0.22, 0.24, 0.22, hood)
    part(0.0, 1.5, 0.12, 0.14, 0.13, 0.02, EYE_DARK)
    part(0.0, 1.66, -0.03, 0.26, 0.1, 0.26, hood)
    dag = _sword(dict(steel=STEEL, steel_d=STEEL, trim=IRON, gold=IRON,
                      leather=LEATHER_D), blade_len=0.34, blade_w=0.06)
    hand = m3.add((0.28, 1.32, 0.0),
                  m3.mat_vec(m3.rot_x_matrix(p["arm_r"]), (0.0, -0.4, 0.03)))
    b.merge(dag, matrix=m3.rot_x_matrix(p["arm_r"] + p["sword"]), offset=hand)
    if p["dead"] > 0.0:
        return _dead_wrap(b, rx=-1.5, dz=-0.2).build()
    return b.build()


def villager(pose=None, variant=0, role="peasant"):
    """Robed elder, smith or peasant; variant picks clothes and hair."""
    p = dict(leg_l=0.0, leg_r=0.0, lean=0.0)
    if pose:
        p.update(pose)
    tunics = {0: C(168, 130, 84), 1: C(128, 116, 72), 2: C(150, 92, 66)}
    robes = {"elder": C(112, 108, 134), "smith": C(120, 88, 60)}
    tunic = robes.get(role, tunics[variant % 3])
    hair = (HAIR_D, C(120, 92, 58), C(200, 198, 190))[variant % 3]
    b = MeshBuilder()
    lean = p["lean"] + p["leg_l"] * 0.12
    if role in ("elder", "smith"):
        b.cylinder(0.0, 0.02, 0.0, 0.34, 1.3, 8, tunic)
    else:
        for side, key in ((-1.0, "leg_l"), (1.0, "leg_r")):
            ang = p[key]
            hip = (0.12 * side, 0.88, 0.0)
            b.box(0.12 * side, 0.46, 0.0, 0.14, 0.84, 0.15, LEATHER_D, rx=ang, pivot=hip)
            b.box(0.12 * side, 0.06, 0.08, 0.15, 0.12, 0.26, C(52, 40, 28), rx=ang, pivot=hip)
    lp = (0.0, 0.9, 0.0)

    def part(cx, cy, cz, sx, sy, sz, color, ry=0.0, rx=0.0):
        b.box(cx, cy, cz, sx, sy, sz, color, ry=ry, rx=rx + lean, pivot=lp)

    part(0.0, 1.14, 0.0, 0.44, 0.48, 0.27, tunic)
    for side in (-1.0, 1.0):
        sh = (0.27 * side, 1.32, 0.0)
        b.box(0.28 * side, 1.1, 0.0, 0.12, 0.34, 0.14, tunic, rx=p["leg_r"] * 0.4 * -side,
              pivot=sh)
        b.box(0.29 * side, 0.86, 0.01, 0.10, 0.28, 0.12,
              SKIN if role == "smith" else tunic, rx=p["leg_r"] * 0.5 * -side, pivot=sh)
    part(0.0, 1.52, 0.0, 0.21, 0.23, 0.21, SKIN)
    part(-0.045, 1.55, 0.107, 0.035, 0.03, 0.01, EYE_DARK)
    part(0.045, 1.55, 0.107, 0.035, 0.03, 0.01, EYE_DARK)
    part(0.0, 1.62, -0.02, 0.23, 0.09, 0.23, hair)
    if role == "elder":
        part(0.0, 1.4, 0.09, 0.15, 0.3, 0.07, C(222, 220, 214))
        part(0.0, 1.58, 0.02, 0.24, 0.16, 0.24, C(200, 198, 190))
        staff = MeshBuilder()
        staff.box(0.0, 0.0, 0.0, 0.05, 1.7, 0.05, WOOD_D)
        staff.sphere(0.0, 1.74, 0.0, 0.07, 0.07, 0.07, 5, 3, CRYSTAL, emissive=True)
        b.merge(staff.build(), offset=(0.36, 0.0, 0.08))
    elif role == "smith":
        part(0.0, 1.12, 0.145, 0.3, 0.44, 0.015, C(70, 60, 54))
        part(0.0, 1.42, 0.08, 0.16, 0.14, 0.06, HAIR_D)
        ham = MeshBuilder()
        ham.box(0.0, 0.55, 0.0, 0.05, 0.62, 0.05, WOOD_D)
        ham.box(0.0, 0.92, 0.0, 0.24, 0.12, 0.12, IRON)
        b.merge(ham.build(), offset=(0.38, 0.0, 0.1))
    else:
        part(0.0, 1.4, 0.07, 0.12, 0.1, 0.05, tunic)
        if variant == 0:
            b.cone(0.0, 1.62, 0.0, 0.35, 0.13, 8, STRAW)
    return b.build()


def chicken(pose=None):
    """A village chicken with peck and walk poses."""
    p = dict(peck=0.0, leg=0.0)
    if pose:
        p.update(pose)
    b = MeshBuilder()
    body = C(232, 230, 222)
    b.box(0.0, 0.17, 0.0, 0.15, 0.15, 0.21, body)
    b.box(0.0, 0.24, -0.13, 0.09, 0.13, 0.08, C(214, 210, 200), rx=0.5,
          pivot=(0.0, 0.2, -0.08))
    hy = 0.26 if p["peck"] < 0.5 else 0.14
    b.box(0.0, hy + 0.06, 0.13, 0.09, 0.1, 0.09, body)
    b.box(0.0, hy + 0.05, 0.19, 0.04, 0.03, 0.06, C(230, 178, 60))
    b.box(0.0, hy + 0.12, 0.12, 0.02, 0.05, 0.06, C(190, 50, 50))
    for side in (-1.0, 1.0):
        b.box(0.04 * side, 0.05, 0.0, 0.02, 0.1, 0.02, C(230, 178, 60),
              rx=p["leg"] * side, pivot=(0.04 * side, 0.1, 0.0))
    return b.build()


def wyvern(frame=0):
    """The wyvern circling the castle; two wing frames."""
    b = MeshBuilder()
    flap = 0.5 if frame == 0 else -0.3
    b.box(0.0, 0.0, 0.0, 0.34, 0.30, 1.25, VILE_GREEN)
    b.box(0.0, 0.14, 0.62, 0.22, 0.2, 0.4, VILE_GREEN, rx=-0.35,
          pivot=(0.0, 0.1, 0.55))
    b.box(0.0, 0.38, 0.92, 0.18, 0.16, 0.3, C(64, 84, 66))
    b.box(0.0, 0.36, 1.1, 0.1, 0.08, 0.18, C(50, 66, 52))
    b.box(-0.06, 0.46, 0.86, 0.03, 0.16, 0.03, C(58, 46, 40), rx=-0.6)
    b.box(0.06, 0.46, 0.86, 0.03, 0.16, 0.03, C(58, 46, 40), rx=-0.6)
    for i, (sz, sy, sx) in enumerate(((-0.5, 0.13, 0.13), (-0.95, 0.1, 0.09),
                                      (-1.35, 0.07, 0.06))):
        b.box(0.0, 0.02 + i * 0.05, sz, sx, sy, 0.55, VILE_GREEN,
              rx=0.15 + i * 0.12, pivot=(0.0, 0.0, sz + 0.27))
    for side in (-1.0, 1.0):
        b.box(0.2 * side, 0.1, 0.35, 0.5, 0.06, 0.12, C(50, 66, 52),
              rz=flap * side, pivot=(0.12 * side, 0.12, 0.35))
        b.box(0.62 * side, 0.1 + flap * 0.7, 0.28, 0.85, 0.03, 0.5,
              C(84, 104, 78), rz=flap * 0.7 * side, pivot=(0.2 * side, 0.1, 0.35))
    return b.build()


def tree_oak(seed=0, sway=0):
    """A broad oak; seed varies canopy layout, sway animates it."""
    from .noise import rand01
    b = MeshBuilder()
    b.cylinder(0.0, 0.0, 0.0, 0.2, 1.5, 6, TRUNK)
    b.box(0.0, 0.05, 0.0, 0.52, 0.12, 0.52, TRUNK_D)
    off = sway * 0.14
    blobs = []
    for i in range(4):
        a = rand01(i, seed, 5) * 6.283
        r = 0.25 + rand01(i, seed, 9) * 0.5
        blobs.append((math.cos(a) * r + off, 1.9 + rand01(i, seed, 13) * 0.9,
                      math.sin(a) * r + off * 0.6,
                      0.75 + rand01(i, seed, 17) * 0.5))
    for x, y, z, r in blobs:
        b.sphere(x, y, z, r, r * 0.82, r, 7, 4, GREEN1 if r > 1.0 else GREEN2)
    b.sphere(off * 1.4, 2.6, off, 1.05, 0.9, 1.05, 7, 4, GREEN_D)
    return b.build()


def tree_pine(seed=0, sway=0):
    from .noise import rand01
    b = MeshBuilder()
    h = 1.2 + rand01(0, seed, 3) * 0.5
    b.cylinder(0.0, 0.0, 0.0, 0.17, h, 6, TRUNK)
    off = sway * 0.1
    tiers = ((1.05, 1.3), (0.8, 1.1), (0.52, 0.95))
    y = h - 0.25
    for i, (r, th) in enumerate(tiers):
        b.cone(off * (i + 1) * 0.4, y, off * (i + 1) * 0.3, r, th, 7,
               PINE if i < 2 else PINE_D)
        y += th * 0.72
    return b.build()


def tree_birch(seed=0, sway=0):
    from .noise import rand01
    b = MeshBuilder()
    b.cylinder(0.0, 0.0, 0.0, 0.11, 2.3, 5, C(198, 198, 188))
    off = sway * 0.16
    b.sphere(off, 2.6, 0.0, 0.72, 0.8, 0.72, 6, 3, C(120, 150, 76))
    b.sphere(off * 0.6, 3.1, 0.15, 0.5, 0.55, 0.5, 6, 3, C(104, 136, 68))
    return b.build()


def tree_dead(seed=0):
    from .noise import rand01
    b = MeshBuilder()
    b.cylinder(0.0, 0.0, 0.0, 0.13, 2.1, 5, C(104, 92, 80))
    for i in range(3):
        a = rand01(i, seed, 21) * 6.283
        y = 1.1 + rand01(i, seed, 25) * 0.8
        b.box(math.cos(a) * 0.3, y, math.sin(a) * 0.3, 0.08, 0.7, 0.08,
              C(96, 84, 72), rz=0.7 * math.cos(a), rx=0.7 * math.sin(a),
              pivot=(0.0, y, 0.0))
    return b.build()


def bush(seed=0):
    b = MeshBuilder()
    b.sphere(0.0, 0.32, 0.0, 0.68, 0.45, 0.68, 6, 3, GREEN2)
    b.sphere(0.3, 0.25, 0.15, 0.4, 0.3, 0.4, 5, 3, GREEN_D)
    return b.build()


def rock(seed=0, big=False):
    from .noise import rand01
    b = MeshBuilder()
    s = 1.0 if big else 0.5
    for i in range(3):
        x = (rand01(i, seed, 31) - 0.5) * 0.6 * s
        z = (rand01(i, seed, 33) - 0.5) * 0.6 * s
        b.box(x, 0.2 * s + i * 0.08, z, (0.8 - i * 0.15) * s, (0.5 + i * 0.1) * s,
              (0.7 - i * 0.1) * s, STONE if i % 2 == 0 else STONE_D,
              ry=rand01(i, seed, 35) * 1.5)
    return b.build()


def house(variant=0):
    """A timber-framed cottage; windows glow warm at night (emissive)."""
    b = MeshBuilder()
    mirror = -1.0 if variant == 1 else 1.0
    scale = 0.85 if variant == 2 else 1.0
    wall = STONE if variant == 2 else PLASTER
    b.box(0.0, 0.45, 0.0, 5.0 * scale, 0.9, 4.2 * scale, STONE_D)
    b.box(0.0, 1.5, 0.0, 4.6 * scale, 1.7, 3.8 * scale, wall)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            b.box(sx * 2.2 * scale, 1.5, sz * 1.8 * scale, 0.2, 1.8, 0.2, WOOD_D)
    b.box(0.0, 2.32, 1.9 * scale, 4.6 * scale, 0.16, 0.14, WOOD_D)
    b.box(0.9 * scale * mirror, 1.15, 1.93 * scale, 0.95, 1.5, 0.1, WOOD)
    b.box(0.45 * scale * mirror, 1.15, 1.94 * scale, 0.08, 1.4, 0.06, WOOD_D)
    for wx in (-1.55, 1.0):
        if variant == 1 and wx > 0:
            wx = 1.75
        b.box(wx * scale * mirror, 1.62, 1.91 * scale, 0.62, 0.62, 0.06,
              C(96, 82, 62))
        b.box(wx * scale * mirror, 1.62, 1.94 * scale, 0.5, 0.5, 0.03,
              C(255, 196, 110), emissive=True)
        b.box((wx - 0.38) * scale * mirror, 1.62, 1.92 * scale, 0.1, 0.7, 0.08, WOOD_D)
    ridge = 3.42
    b.box(0.0, 2.85, 1.02 * scale, 5.4 * scale, 0.16, 2.9 * scale, STRAW,
          rx=0.54, pivot=(0.0, ridge, 0.0))
    b.box(0.0, 2.85, -1.02 * scale, 5.4 * scale, 0.16, 2.9 * scale, STRAW,
          rx=-0.54, pivot=(0.0, ridge, 0.0))
    b.box(0.0, ridge, 0.0, 5.5 * scale, 0.14, 0.24, WOOD_D)
    for sx in (-1.0, 1.0):
        b.quad((sx * 2.3 * scale, 0.9, -1.9 * scale), (sx * 2.3 * scale, 0.9, 1.9 * scale),
               (sx * 2.3 * scale, ridge - 0.05, 0.0), (sx * 2.3 * scale, ridge - 0.05, 0.0),
               wall)
    b.box(1.5 * scale * mirror, ridge - 0.5, -0.7 * scale, 0.5, 1.4, 0.5, STONE_D)
    return b.build()


def well():
    b = MeshBuilder()
    b.cylinder(0.0, 0.0, 0.0, 0.85, 0.8, 8, STONE)
    b.cylinder(0.0, 0.72, 0.0, 0.62, 0.1, 8, C(28, 30, 36))
    for sx in (-1.0, 1.0):
        b.box(sx * 0.72, 1.3, 0.0, 0.13, 1.05, 0.13, WOOD_D)
    b.box(0.0, 1.48, 0.0, 1.7, 0.09, 0.09, WOOD, ry=1.5708)
    b.box(0.0, 1.88, 0.55, 1.9, 0.12, 1.3, STRAW, rx=0.62, pivot=(0.0, 2.15, 0.0))
    b.box(0.0, 1.88, -0.55, 1.9, 0.12, 1.3, STRAW, rx=-0.62, pivot=(0.0, 2.15, 0.0))
    b.box(0.0, 1.05, 0.0, 0.22, 0.24, 0.22, WOOD)
    return b.build()


def fence():
    b = MeshBuilder()
    b.box(0.0, 0.5, 0.0, 1.8, 0.09, 0.07, WOOD_D)
    b.box(0.0, 0.82, 0.0, 1.8, 0.09, 0.07, WOOD_D)
    for px in (-0.8, 0.0, 0.8):
        b.box(px, 0.5, 0.0, 0.12, 1.0, 0.12, WOOD)
        b.cone(px, 1.0, 0.0, 0.09, 0.16, 4, WOOD)
    return b.build()


def cart():
    b = MeshBuilder()
    b.box(0.0, 0.72, 0.0, 2.2, 0.16, 1.3, WOOD)
    for sz in (-1.0, 1.0):
        b.box(0.0, 0.94, sz * 0.62, 2.2, 0.34, 0.08, WOOD_D)
    b.box(0.0, 1.0, 0.0, 2.0, 0.28, 1.1, STRAW)
    for sx in (-1.0, 1.0):
        b.cylinder(sx * 1.12, 0.05, 0.0, 0.55, 0.12, 8, WOOD_D, axis="x")
    for sx in (-1.0, 1.0):
        b.box(sx * 0.5, 0.62, 1.45, 0.08, 0.08, 1.1, WOOD_D, rx=-0.18,
              pivot=(sx * 0.5, 0.7, 0.9))
    return b.build()


def anvil():
    b = MeshBuilder()
    b.box(0.0, 0.22, 0.0, 0.5, 0.44, 0.5, WOOD_D)
    b.box(0.0, 0.58, 0.0, 0.66, 0.26, 0.28, IRON)
    b.box(0.45, 0.58, 0.0, 0.4, 0.16, 0.2, IRON, rz=-0.25, pivot=(0.28, 0.6, 0.0))
    return b.build()


def haystack():
    b = MeshBuilder()
    b.cone(0.0, 0.0, 0.0, 1.0, 1.5, 8, C(214, 182, 92))
    b.cone(0.0, 0.5, 0.0, 0.7, 0.9, 7, C(198, 168, 82))
    return b.build()


def campfire(frame=0):
    """A crackling fire; frame 0-3 wobbles the flame cones (emissive)."""
    b = MeshBuilder()
    for i in range(6):
        a = i * 1.047
        b.box(math.cos(a) * 0.55, 0.07, math.sin(a) * 0.55, 0.2, 0.14, 0.2,
              STONE_D, ry=a)
    for i in range(3):
        b.box(0.0, 0.12, 0.0, 0.14, 0.14, 0.95, WOOD_D,
              ry=i * 2.094 + 0.4, rx=0.06)
    wob = (0.0, 0.06, -0.05, 0.03)[frame % 4]
    b.cone(wob * 0.5, 0.12, wob, 0.3, 0.52 + wob, 6, FLAME)
    b.cone(wob, 0.14, -wob * 0.4, 0.17, 0.72 + wob * 0.8, 5, FLAME_HI, emissive=True)
    b.box(0.2, 0.05, -0.2, 0.08, 0.08, 0.08, EMBER, emissive=True)
    b.box(-0.24, 0.05, 0.16, 0.07, 0.07, 0.07, EMBER, emissive=True)
    return b.build()


def chest(opened=False):
    b = MeshBuilder()
    b.box(0.0, 0.28, 0.0, 0.92, 0.56, 0.58, WOOD)
    for sx in (-1.0, 1.0):
        b.box(sx * 0.22, 0.28, 0.0, 0.1, 0.58, 0.6, C(62, 64, 70))
    b.box(0.0, 0.42, 0.3, 0.13, 0.15, 0.06, GOLD_D)
    if opened:
        b.box(0.0, 0.62, -0.28, 0.92, 0.13, 0.56, WOOD_D, rx=-1.85,
              pivot=(0.0, 0.56, -0.27))
        b.sphere(0.0, 0.5, 0.05, 0.16, 0.1, 0.16, 5, 3, GOLD, emissive=True)
    else:
        b.box(0.0, 0.6, 0.0, 0.92, 0.12, 0.58, WOOD_D)
    return b.build()


def shrine():
    b = MeshBuilder()
    b.box(0.0, 0.12, 0.0, 2.4, 0.24, 2.4, STONE)
    b.box(0.0, 0.34, 0.0, 1.8, 0.24, 1.8, STONE_D)
    for sx in (-1.0, 1.0):
        b.box(sx * 0.62, 0.95, -0.55, 0.22, 1.05, 0.22, STONE)
    b.box(0.0, 1.52, -0.55, 1.7, 0.2, 0.26, STONE_D)
    b.box(0.0, 0.62, 0.15, 0.5, 0.32, 0.5, STONE_D)
    b.cone(0.0, 0.98, 0.15, 0.17, 0.24, 5, CRYSTAL, emissive=True)
    b.cone(0.0, 0.74, 0.15, 0.17, -0.2, 5, CRYSTAL, emissive=True)
    return b.build()


def banner(frame=0):
    """A tower banner; two wave frames."""
    b = MeshBuilder()
    b.cylinder(0.0, 0.0, 0.0, 0.05, 2.3, 5, WOOD_D)
    b.box(0.0, 2.26, 0.0, 0.16, 0.16, 0.16, GOLD_D)
    w = (0.0, 0.1)[frame % 2]
    for i, seg in enumerate((0.66, 0.5, 0.36)):
        b.box(0.0, 2.0 - i * 0.56, 0.02 + w * (i + 1) * 0.12, 0.05, seg, 0.55,
              RED_CLOTH, rx=w * (i + 1) * 0.3, pivot=(0.0, 2.28 - i * 0.56, 0.02))
    b.box(0.0, 1.86, 0.06 + w * 0.24, 0.06, 0.22, 0.2, GOLD)
    return b.build()


def castle():
    """The showpiece: curtain walls, merlons, corner towers, keep and gate."""
    b = MeshBuilder()
    half = 11.0
    for sz in (-1.0, 1.0):
        b.box(0.0, 2.25, sz * half, 2 * half, 4.5, 1.4, STONE)
    for sx in (-1.0, 1.0):
        b.box(sx * half, 2.25, 0.0, 1.4, 4.5, 2 * half - 1.4, STONE)
    for sz in (-1.0, 1.0):
        for i in range(-4, 5):
            b.box(i * 2.4, 4.85, sz * half, 1.1, 0.7, 1.5, STONE_D)
    for sx in (-1.0, 1.0):
        for i in range(-4, 5):
            b.box(sx * half, 4.85, i * 2.4, 1.5, 0.7, 1.1, STONE_D)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            b.cylinder(sx * half, 0.0, sz * half, 2.3, 9.0, 8, STONE)
            b.cone(sx * half, 9.0, sz * half, 2.75, 3.4, 8, ROOF)
            b.box(sx * half, 9.4, sz * half, 0.06, 2.0, 0.06, WOOD_D)
    b.box(0.0, 4.6, 0.0, 6.4, 9.2, 6.4, STONE)
    b.box(0.0, 9.2, 0.0, 7.0, 0.5, 7.0, STONE_D)
    b.cylinder(0.0, 0.0, 0.0, 1.9, 12.5, 8, STONE_D)
    b.cone(0.0, 12.5, 0.0, 2.35, 3.0, 8, ROOF)
    for sx in (-1.0, 1.0):
        b.cylinder(sx * 4.4, 0.0, half, 1.7, 6.5, 7, STONE)
        b.cone(sx * 4.4, 6.5, half, 2.1, 2.6, 7, ROOF)
    b.box(0.0, 2.4, half, 5.6, 4.8, 1.3, STONE)
    b.box(0.0, 1.35, half + 0.68, 2.6, 2.7, 0.16, C(44, 38, 32))
    for i in range(-1, 2):
        b.box(i * 0.8, 1.35, half + 0.72, 0.12, 2.6, 0.1, C(70, 62, 52))
    b.box(0.0, 0.06, half + 2.6, 3.0, 0.12, 3.6, WOOD_D)
    b.box(0.0, 4.95, half + 0.3, 5.8, 0.35, 1.8, STONE_D)
    for sx in (-1.0, 1.0):
        b.box(sx * 2.2, 6.7, half, 0.9, 1.5, 0.9, STONE_D)
    return b.build()


def pickup(kind):
    """Ground loot: gold, potion, pelt, bone or the quest amulet."""
    b = MeshBuilder()
    if kind == "gold":
        for i, (x, z) in enumerate(((0, 0), (0.14, 0.06), (-0.12, 0.1),
                                    (0.05, -0.13), (-0.07, -0.05))):
            b.box(x, 0.05 + (i == 0) * 0.05, z, 0.13, 0.09, 0.13, GOLD if i % 2 else GOLD_D,
                  ry=i * 0.7)
    elif kind == "potion":
        b.sphere(0.0, 0.12, 0.0, 0.11, 0.13, 0.11, 5, 3, POTION_C)
        b.cylinder(0.0, 0.22, 0.0, 0.04, 0.1, 5, C(180, 170, 150))
        b.box(0.0, 0.33, 0.0, 0.07, 0.05, 0.07, LEATHER_D)
        b.sphere(0.0, 0.12, 0.06, 0.03, 0.03, 0.03, 3, 2, C(255, 190, 190),
                 emissive=True)
    elif kind == "pelt":
        b.box(0.0, 0.04, 0.0, 0.42, 0.06, 0.5, C(146, 106, 66))
        b.box(0.0, 0.08, -0.12, 0.3, 0.05, 0.2, C(160, 120, 76))
    elif kind == "bone":
        b.cylinder(-0.1, 0.05, 0.0, 0.045, 0.34, 5, BONE, axis="x", rz=0.5)
        b.sphere(-0.28, 0.09, 0.08, 0.06, 0.06, 0.06, 4, 2, BONE)
        b.sphere(-0.28, 0.09, -0.08, 0.06, 0.06, 0.06, 4, 2, BONE)
    else:
        b.cylinder(0.0, 0.28, 0.0, 0.17, 0.05, 7, GOLD, emissive=True)
        b.sphere(0.0, 0.26, 0.0, 0.07, 0.07, 0.07, 5, 3, C(255, 120, 110),
                 emissive=True)
    return b.build()

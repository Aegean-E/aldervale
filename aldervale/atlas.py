"""Sprite atlas: bakes every (model, pose, yaw) combination at load time.

The atlas is the bridge between the 3D model library and the fast billboard
renderer: meshes are baked once into char-cell sprites at sixteen yaw steps,
then the game only ever picks frames and scales them.
"""

import inspect
import math

from . import models
from .mesh import bake_sprite

YAW_STEPS = 16
BAKE_PITCH = 0.30
BAKE_DIST = 9.0


def _spec(builder, poses, size, height, cells=16, dist=BAKE_DIST, kwargs=None):
    return dict(builder=builder, poses=poses, size=size, height=height,
                cells=cells, dist=dist, kwargs=kwargs or {})


WALK = [
    {"leg_l": 0.55, "leg_r": -0.55, "arm_l": -0.38, "arm_r": 0.38},
    {"leg_l": 0.18, "leg_r": -0.18, "arm_l": -0.12, "arm_r": 0.12},
    {"leg_l": -0.55, "leg_r": 0.55, "arm_l": 0.38, "arm_r": -0.38},
    {"leg_l": -0.18, "leg_r": 0.18, "arm_l": 0.12, "arm_r": -0.12},
]
WOLF_WALK = [
    {"leg_fl": 0.5, "leg_fr": -0.5, "leg_rl": -0.5, "leg_rr": 0.5},
    {"leg_fl": -0.5, "leg_fr": 0.5, "leg_rl": 0.5, "leg_rr": -0.5},
]

MODEL_SPECS = {
    "knight": _spec(models.knight, {
        "idle": {},
        "walk0": WALK[0], "walk1": WALK[1], "walk2": WALK[2], "walk3": WALK[3],
        "atk0": {"arm_r": -2.3, "sword": 0.35, "lean": -0.14, "leg_l": 0.3, "arm_l": 0.5},
        "atk1": {"arm_r": 0.95, "sword": 0.5, "lean": 0.3, "leg_l": 0.5, "leg_r": -0.35, "arm_l": -0.4},
        "atk2": {"arm_r": 0.35, "sword": 0.2, "lean": 0.12, "arm_l": -0.2},
        "dead": {"dead": 1.0},
    }, size=(1.5, 2.1), height=1.95, cells=30),
    "guard": _spec(models.guard, {"idle": {}}, size=(1.5, 2.3), height=2.05, cells=30),
    "wolf": _spec(models.wolf, {
        "idle": {},
        "walk0": WOLF_WALK[0], "walk1": WOLF_WALK[1],
        "atk": {"lunge": 1.0}, "dead": {"dead": 1.0},
    }, size=(1.1, 1.1), height=1.0, cells=30),
    "skeleton": _spec(models.skeleton, {
        "idle": {},
        "walk0": WALK[0], "walk1": WALK[1],
        "atk": {"arm_r": -2.0, "sword": 0.45, "lean": -0.12, "arm_l": 0.4},
        "dead": {"dead": 1.0},
    }, size=(1.4, 2.0), height=1.9, cells=30),
    "captain": _spec(models.skeleton, {
        "idle": {}, "walk0": WALK[0], "walk1": WALK[1],
        "atk": {"arm_r": -2.1, "sword": 0.5, "lean": -0.15, "arm_l": 0.5},
        "dead": {"dead": 1.0},
    }, size=(1.9, 2.7), height=2.6, cells=30, kwargs={"captain": True}),
    "bandit": _spec(models.bandit, {
        "idle": {},
        "walk0": WALK[0], "walk1": WALK[1],
        "atk": {"arm_r": -1.7, "sword": 0.55, "lean": 0.22, "arm_l": -0.3},
        "dead": {"dead": 1.0},
    }, size=(1.4, 1.95), height=1.85, cells=30),
    "elder": _spec(models.villager, {
        "idle": {}, "walk0": {"leg_l": 0.3, "lean": 0.05},
        "walk1": {"leg_l": -0.3, "lean": -0.05},
    }, size=(1.2, 1.95), height=1.9, cells=28, kwargs={"role": "elder"}),
    "smith": _spec(models.villager, {
        "idle": {}, "walk0": {"leg_l": 0.3, "lean": 0.05},
        "walk1": {"leg_l": -0.3, "lean": -0.05},
    }, size=(1.2, 1.9), height=1.85, cells=28, kwargs={"role": "smith"}),
    "peasant0": _spec(models.villager, {
        "idle": {}, "walk0": WALK[0], "walk1": WALK[1],
    }, size=(1.3, 1.9), height=1.8, cells=28, kwargs={"variant": 0}),
    "peasant1": _spec(models.villager, {
        "idle": {}, "walk0": WALK[0], "walk1": WALK[1],
    }, size=(1.3, 1.9), height=1.8, cells=28, kwargs={"variant": 1}),
    "peasant2": _spec(models.villager, {
        "idle": {}, "walk0": WALK[0], "walk1": WALK[1],
    }, size=(1.3, 1.9), height=1.8, cells=28, kwargs={"variant": 2}),
    "chicken": _spec(models.chicken, {
        "idle": {}, "walk0": {"leg": 0.6}, "walk1": {"leg": -0.6},
        "peck": {"peck": 1.0},
    }, size=(0.5, 0.5), height=0.42, cells=28),
    "wyvern": _spec(models.wyvern, {
        "fly0": {"frame": 0}, "fly1": {"frame": 1},
    }, size=(3.0, 1.6), height=1.5, cells=10),
    "tree_oak": _spec(models.tree_oak, {
        "sway0": {"sway": 0.0}, "sway1": {"sway": 1.0},
    }, size=(5.5, 4.4), height=3.7, cells=10),
    "tree_pine": _spec(models.tree_pine, {
        "sway0": {"sway": 0.0}, "sway1": {"sway": 1.0},
    }, size=(4.0, 4.2), height=3.5, cells=10),
    "tree_birch": _spec(models.tree_birch, {
        "sway0": {"sway": 0.0}, "sway1": {"sway": 1.0},
    }, size=(3.4, 3.8), height=3.3, cells=10),
    "tree_dead": _spec(models.tree_dead, {
        "idle": {},
    }, size=(2.6, 2.6), height=2.4, cells=10),
    "bush": _spec(models.bush, {"idle": {}}, size=(1.7, 0.9), height=0.75, cells=10),
    "rock_s": _spec(models.rock, {"idle": {}}, size=(1.2, 0.8), height=0.65, cells=10),
    "rock_b": _spec(models.rock, {"idle": {}}, size=(2.2, 1.4), height=1.15, cells=10,
                    kwargs={"big": True}),
    "house0": _spec(models.house, {"idle": {}}, size=(6.2, 4.6), height=4.3, cells=9),
    "house1": _spec(models.house, {"idle": {}}, size=(6.2, 4.6), height=4.3, cells=9,
                    kwargs={"variant": 1}),
    "house2": _spec(models.house, {"idle": {}}, size=(5.4, 4.0), height=3.7, cells=9,
                    kwargs={"variant": 2}),
    "well": _spec(models.well, {"idle": {}}, size=(2.4, 2.6), height=2.4, cells=10),
    "fence": _spec(models.fence, {"idle": {}}, size=(2.0, 1.3), height=1.15, cells=10),
    "cart": _spec(models.cart, {"idle": {}}, size=(2.6, 1.5), height=1.35, cells=10),
    "anvil": _spec(models.anvil, {"idle": {}}, size=(1.2, 0.9), height=0.8, cells=12),
    "haystack": _spec(models.haystack, {"idle": {}}, size=(2.2, 1.8), height=1.6, cells=9),
    "campfire": _spec(models.campfire, {
        "fire0": {"frame": 0}, "fire1": {"frame": 1},
        "fire2": {"frame": 2}, "fire3": {"frame": 3},
    }, size=(1.3, 1.0), height=0.8, cells=12),
    "chest_c": _spec(models.chest, {"idle": {}}, size=(1.1, 0.8), height=0.72, cells=14),
    "chest_o": _spec(models.chest, {"idle": {}}, size=(1.1, 0.8), height=0.72, cells=14,
                     kwargs={"opened": True}),
    "shrine": _spec(models.shrine, {"idle": {}}, size=(2.6, 1.9), height=1.75, cells=10),
    "banner0": _spec(models.banner, {"idle": {"frame": 0}}, size=(0.8, 2.5),
                     height=2.35, cells=12),
    "banner1": _spec(models.banner, {"idle": {"frame": 1}}, size=(0.8, 2.5),
                     height=2.35, cells=12),
    "gold": _spec(models.pickup, {"idle": {}}, size=(0.5, 0.3), height=0.22, cells=16,
                  kwargs={"kind": "gold"}),
    "potion": _spec(models.pickup, {"idle": {}}, size=(0.4, 0.5), height=0.4, cells=16,
                    kwargs={"kind": "potion"}),
    "pelt": _spec(models.pickup, {"idle": {}}, size=(0.6, 0.3), height=0.16, cells=16,
                  kwargs={"kind": "pelt"}),
    "bone": _spec(models.pickup, {"idle": {}}, size=(0.6, 0.3), height=0.2, cells=16,
                  kwargs={"kind": "bone"}),
    "amulet": _spec(models.pickup, {"idle": {}}, size=(0.5, 0.5), height=0.45, cells=16,
                    kwargs={"kind": "amulet"}),
    "castle": _spec(models.castle, {"idle": {}}, size=(27.0, 15.5), height=14.0,
                    cells=6, dist=40.0),
}


class SpriteAtlas:
    """Baked sprite frames lookup: (model_key, pose_name) -> [yaw frames]."""

    def __init__(self, yaw_steps=YAW_STEPS):
        self.yaw_steps = yaw_steps
        self.frames = {}
        self.heights = {}
        for key, spec in MODEL_SPECS.items():
            self.heights[key] = spec["height"]

    def build(self, progress=None, keys=None):
        total = len(MODEL_SPECS) if keys is None else len(keys)
        done = 0
        for key, spec in MODEL_SPECS.items():
            if keys is not None and key not in keys:
                continue
            cells = spec["cells"]
            dist = spec["dist"]
            f = cells * dist
            sw, sh = spec["size"]
            cw = int(sw * cells * 1.5) + 10
            chh = int(sh * cells * 0.5 * 1.5) + 10
            for pose_name, pose_kwargs in spec["poses"].items():
                kw = dict(spec["kwargs"])
                params = inspect.signature(spec["builder"]).parameters
                if "pose" in params:
                    mesh = spec["builder"](pose=dict(pose_kwargs), **kw)
                else:
                    kw.update(pose_kwargs)
                    mesh = spec["builder"](**kw)
                baked = []
                for i in range(self.yaw_steps):
                    yaw = i * 2.0 * math.pi / self.yaw_steps
                    baked.append(bake_sprite(mesh, yaw=yaw, pitch=BAKE_PITCH,
                                             dist=dist, f=f, aspect=0.5,
                                             canvas=(cw, chh)))
                self.frames[(key, pose_name)] = baked
            done += 1
            if progress:
                progress(key, done / total)
        return self

    def get(self, model, pose, frame):
        row = self.frames.get((model, pose))
        if row is None:
            row = self.frames.get((model, "idle"))
        if not row:
            return None
        return row[frame % len(row)]

    def yaw_frame(self, ent_yaw, cam_yaw):
        rel = ent_yaw - cam_yaw - math.pi
        frame = math.floor(rel / (2.0 * math.pi) * self.yaw_steps + 0.5)
        return int(frame) % self.yaw_steps

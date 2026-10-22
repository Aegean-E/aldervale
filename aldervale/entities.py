"""World entities: props, pickups, ambient life and AI-driven actors."""

import math

from .story import CAST


class Entity:
    """Anything the renderer draws as a billboard."""

    __slots__ = ("eid", "model", "pose", "x", "z", "yaw", "height", "scale",
                 "y_off", "ground_y", "flash", "flash_color", "name", "solid",
                 "radius")

    def __init__(self, eid, model, x, z, height, yaw=0.0, scale=1.0,
                 y_off=0.0, pose="idle", name=None, solid=False, radius=0.6):
        self.eid = eid
        self.model = model
        self.pose = pose
        self.x = x
        self.z = z
        self.yaw = yaw
        self.height = height
        self.scale = scale
        self.y_off = y_off
        self.ground_y = 0.0
        self.flash = 0.0
        self.flash_color = None
        self.name = name
        self.solid = solid
        self.radius = radius


class Prop(Entity):
    """Static scenery."""

    __slots__ = ()


class Pickup(Entity):
    """Ground loot bobbing gently; gold is collected by walking over it."""

    __slots__ = ("item_id", "amount", "bob", "quest")

    def __init__(self, eid, item_id, amount, x, z, height, quest=False):
        super().__init__(eid, _pickup_model(item_id), x, z, height,
                         radius=0.5)
        self.item_id = item_id
        self.amount = amount
        self.bob = (eid_hash(eid) % 100) / 100.0 * 6.28
        self.quest = quest


def _pickup_model(item_id):
    return {"gold": "gold", "potion": "potion", "pelt": "pelt",
            "bone": "bone", "amulet": "amulet"}.get(item_id, "gold")


def eid_hash(eid):
    n = 0
    for ch in eid:
        n = (n * 131 + ord(ch)) & 0xFFFF
    return n


class Chest(Entity):
    """A loot chest; opening swaps the sprite and grants contents once."""

    __slots__ = ("opened", "loot")

    def __init__(self, eid, x, z, loot):
        super().__init__(eid, "chest_c", x, z, 0.72, solid=True, radius=0.7,
                         name="Chest")
        self.opened = False
        self.loot = loot


class Actor(Entity):
    """A creature or person with stats and a simple state machine."""

    __slots__ = ("kind", "hp", "max_hp", "atk", "dfn", "speed", "xp_reward",
                 "state", "target_x", "target_z", "home_x", "home_z",
                 "home_r", "aggro_r", "attack_range", "attack_dmg",
                 "cooldown", "windup_t", "anim_t", "moving", "drops",
                 "dead_t", "ai_kind", "flight_angle")

    def __init__(self, eid, model, x, z, height, *, kind, hp, atk, dfn,
                 speed, xp_reward, aggro_r, attack_range, attack_dmg,
                 home_r=10.0, scale=1.0, drops=None, ai_kind="hostile",
                 name=None, radius=None):
        super().__init__(eid, model, x, z, height, scale=scale, name=name,
                         solid=True, radius=0.55 * scale)
        if radius is not None:
            self.radius = radius
        self.kind = kind
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.dfn = dfn
        self.speed = speed
        self.xp_reward = xp_reward
        self.aggro_r = aggro_r
        self.attack_range = attack_range
        self.attack_dmg = attack_dmg
        self.home_x = x
        self.home_z = z
        self.home_r = home_r
        self.state = "idle"
        self.target_x = x
        self.target_z = z
        self.cooldown = 0.0
        self.windup_t = 0.0
        self.anim_t = 0.0
        self.moving = False
        self.drops = drops or {}
        self.dead_t = 0.0
        self.ai_kind = ai_kind
        self.flight_angle = 0.0

    @property
    def dead(self):
        return self.state == "dead"


class Player(Actor):
    """The hero: an Actor plus inventory, stamina and quest-facing state."""

    __slots__ = ("inventory", "attack_t", "attack_done", "hurt_t",
                 "shrine_cd", "level", "xp", "stamina", "max_stamina")

    def __init__(self, eid, x, z):
        super().__init__(eid, "knight", x, z, 1.95, kind="player", hp=46,
                         atk=6, dfn=1, speed=3.8, xp_reward=0, aggro_r=0.0,
                         attack_range=2.0, attack_dmg=0, home_r=0.0,
                         ai_kind="player", name=CAST["player"]["name"])
        from .rules import Inventory
        self.inventory = Inventory()
        self.attack_t = -1.0
        self.attack_done = False
        self.hurt_t = 0.0
        self.shrine_cd = 0.0
        self.level = 1
        self.xp = 0
        self.stamina = 100
        self.max_stamina = 100

    @property
    def attacking(self):
        return self.attack_t >= 0.0


def move_actor(actor, dx, dz, world, dt):
    """Move with terrain, water and solid-entity collision; updates ground."""
    ter = world.terrain
    nx = actor.x + dx * dt
    nz = actor.z + dz * dt
    if ter.walkable(nx, actor.z):
        actor.x = nx
    if ter.walkable(actor.x, nz):
        actor.z = nz
    for other in world.entities:
        if other is actor or not other.solid or getattr(other, "dead", False):
            continue
        ddx = actor.x - other.x
        ddz = actor.z - other.z
        rr = actor.radius + other.radius
        d2 = ddx * ddx + ddz * ddz
        if 0.0001 < d2 < rr * rr:
            d = math.sqrt(d2)
            push = (rr - d) * 0.5
            actor.x += ddx / d * push
            actor.z += ddz / d * push
    actor.ground_y = ter.height(actor.x, actor.z)


def face_towards(actor, tx, tz):
    actor.yaw = math.atan2(tx - actor.x, tz - actor.z)


def update_actor(actor, dt, world, env):
    """Run one actor's AI state machine for this frame."""
    player = world.player
    if actor.state == "dead":
        actor.dead_t += dt
        return
    actor.anim_t += dt
    actor.flash = max(0.0, actor.flash - dt * 3.5)
    if actor.ai_kind == "player":
        return
    if actor.ai_kind == "wyvern":
        actor.flight_angle += dt * 0.22
        cx, cz = world.terrain.castle
        actor.x = cx + math.cos(actor.flight_angle) * 30.0
        actor.z = cz + math.sin(actor.flight_angle) * 30.0
        actor.yaw = actor.flight_angle + math.pi / 2.0
        actor.y_off = 17.0 + math.sin(actor.flight_angle * 3.0) * 2.0
        actor.pose = "fly0" if int(world.time * 3.0) % 2 == 0 else "fly1"
        actor.ground_y = world.terrain.height(actor.x, actor.z)
        return
    if actor.ai_kind == "chicken":
        _update_chicken(actor, dt, world)
        return
    if actor.ai_kind == "villager":
        _update_villager(actor, dt, world)
        return
    dist_p = math.hypot(player.x - actor.x, player.z - actor.z)
    night_boost = 1.5 if env.night > 0.5 else 1.0
    aggro = actor.aggro_r * night_boost if actor.kind == "skeleton" else actor.aggro_r
    if actor.state == "idle":
        actor.pose = "idle"
        actor.moving = False
        if dist_p < aggro and not player.dead:
            actor.state = "chase"
        elif actor.anim_t > 4.0:
            actor.anim_t = 0.0
            actor.state = "wander"
            actor.target_x = actor.home_x + (world.rng.random() - 0.5) * actor.home_r * 2
            actor.target_z = actor.home_z + (world.rng.random() - 0.5) * actor.home_r * 2
    elif actor.state == "wander":
        _walk_to(actor, actor.target_x, actor.target_z, world, dt, 0.55)
        if dist_p < aggro and not player.dead:
            actor.state = "chase"
        elif math.hypot(actor.target_x - actor.x, actor.target_z - actor.z) < 0.8:
            actor.state = "idle"
            actor.anim_t = 0.0
    elif actor.state == "chase":
        if player.dead or dist_p > aggro * 2.2:
            actor.state = "return"
        elif dist_p <= actor.attack_range:
            actor.state = "windup"
            actor.windup_t = 0.0
            face_towards(actor, player.x, player.z)
        else:
            _walk_to(actor, player.x, player.z, world, dt, 1.0)
        if actor.kind == "wolf" and actor.hp < actor.max_hp * 0.22:
            actor.state = "return"
    elif actor.state == "windup":
        actor.moving = False
        actor.pose = "atk"
        actor.windup_t += dt
        if actor.windup_t > 0.55:
            actor.windup_t = 0.0
            actor.cooldown = 1.15 + world.rng.random() * 0.7
            if dist_p <= actor.attack_range + 0.5 and not player.dead:
                world.hit_player(actor.attack_dmg, actor)
            actor.state = "recover"
    elif actor.state == "recover":
        actor.moving = False
        actor.pose = "idle"
        actor.cooldown -= dt
        if actor.cooldown <= 0.0:
            actor.state = "chase" if dist_p < aggro * 2.2 else "return"
    elif actor.state == "return":
        _walk_to(actor, actor.home_x, actor.home_z, world, dt, 0.8)
        if math.hypot(actor.home_x - actor.x, actor.home_z - actor.z) < 1.0:
            actor.state = "idle"
            actor.hp = min(actor.max_hp, actor.hp + 2)


def _walk_to(actor, tx, tz, world, dt, speed_factor):
    dx, dz = tx - actor.x, tz - actor.z
    d = math.hypot(dx, dz)
    if d < 0.05:
        actor.moving = False
        return
    face_towards(actor, tx, tz)
    move_actor(actor, dx / d * actor.speed * speed_factor,
               dz / d * actor.speed * speed_factor, world, dt)
    actor.moving = True
    step = int(actor.anim_t * 6.0) % 2
    actor.pose = "walk0" if step == 0 else "walk1"


def _update_chicken(actor, dt, world):
    player = world.player
    flee = math.hypot(player.x - actor.x, player.z - actor.z)
    if flee < 3.0:
        _walk_to(actor, actor.x * 2 - player.x, actor.z * 2 - player.z,
                 world, dt, 1.2)
        actor.pose = "peck" if int(actor.anim_t * 8.0) % 2 else "walk0"
        return
    if actor.state == "idle":
        actor.pose = "peck" if int(actor.anim_t * 1.5) % 3 == 0 else "idle"
        actor.moving = False
        if actor.anim_t > 3.0:
            actor.anim_t = 0.0
            actor.state = "wander"
            actor.target_x = actor.home_x + (world.rng.random() - 0.5) * 8.0
            actor.target_z = actor.home_z + (world.rng.random() - 0.5) * 8.0
    else:
        _walk_to(actor, actor.target_x, actor.target_z, world, dt, 0.4)
        if math.hypot(actor.target_x - actor.x, actor.target_z - actor.z) < 0.5:
            actor.state = "idle"
            actor.anim_t = 0.0


def _update_villager(actor, dt, world):
    if actor.state == "idle":
        actor.pose = "idle"
        actor.moving = False
        if actor.anim_t > 6.0:
            actor.anim_t = 0.0
            actor.state = "wander"
            actor.target_x = actor.home_x + (world.rng.random() - 0.5) * 14.0
            actor.target_z = actor.home_z + (world.rng.random() - 0.5) * 14.0
    else:
        _walk_to(actor, actor.target_x, actor.target_z, world, dt, 0.45)
        if math.hypot(actor.target_x - actor.x, actor.target_z - actor.z) < 0.8:
            actor.state = "idle"
            actor.anim_t = 0.0

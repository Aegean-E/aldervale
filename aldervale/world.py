"""The world of Aldervale: generation, simulation, quests and persistence."""

import json
import math
import os
import random
from pathlib import Path

from . import entities as ent
from .buffer import pack_rgb
from .rules import (ITEMS, Inventory, damage_roll, xp_for_level)
from .terrain import Terrain

DAY_LENGTH = 300.0
GOLD_COLOR = pack_rgb(232, 196, 90)
HURT_COLOR = pack_rgb(226, 84, 74)
HEAL_COLOR = pack_rgb(120, 220, 130)
INFO_COLOR = pack_rgb(200, 210, 230)
XP_COLOR = pack_rgb(150, 190, 255)
QUEST_COLOR = pack_rgb(240, 210, 120)

VILLAGER_NAMES = ("Mira of the Mill", "Old Tam", "Wren the Herder")


class World:
    """Owns terrain, entities, the player, quests and the world clock."""

    def __init__(self, seed, atlas, day_length=DAY_LENGTH, terrain_size=None):
        self.seed = seed
        self.atlas = atlas
        self.day_length = day_length
        self.rng = random.Random(seed * 7919 + 13)
        if terrain_size is None:
            self.terrain = Terrain(seed)
        else:
            self.terrain = Terrain(seed, size=terrain_size, octaves=3)
        self.entities = []
        self.player = None
        self.quest = "none"
        self.time = 0.0
        self.day_t = 0.20
        self.messages = []
        self.damage_numbers = []
        self.fireflies = []
        self.kills = set()
        self.collected = set()
        self.opened_chests = set()
        self.victory_shown = False
        self.deaths = 0
        self._eid = 0
        self._generate()

    def _next_eid(self):
        self._eid += 1
        return "e%d" % self._eid

    def _generate(self):
        ter = self.terrain
        rng = self.rng
        vx, vz = ter.village
        kx, kz = ter.castle
        cx, cz = ter.camp
        self.player = ent.Player("player", vx, vz + 6)
        self.player.ground_y = ter.height(vx, vz + 6)
        self.player.inventory.add("gold", 30)
        self.player.inventory.add("potion", 1)
        self._spawn_village(vx, vz)
        self._spawn_castle(kx, kz)
        self._spawn_forest()
        self._spawn_camp(cx, cz)
        for i in range(46):
            for _ in range(8):
                fx = vx + (rng.random() - 0.5) * 190.0
                fz = vz - 10.0 + (rng.random() - 0.5) * 120.0
                if ter.forest_at(fx, fz):
                    self.fireflies.append((fx, fz, rng.random() * 6.28))
                    break

    def _walkable_near(self, x, z, radius=14.0):
        ter = self.terrain
        if ter.walkable(x, z):
            return x, z
        for r in range(1, int(radius) + 1):
            for a in range(8):
                ang = a * 0.785 + r * 0.4
                nx = x + math.cos(ang) * r
                nz = z + math.sin(ang) * r
                if ter.walkable(nx, nz):
                    return nx, nz
        return x, z

    def _add(self, entity):
        entity.ground_y = self.terrain.height(entity.x, entity.z)
        self.entities.append(entity)
        return entity

    def _spawn_village(self, vx, vz):
        rng = self.rng
        self._add(ent.Prop(self._next_eid(), "well", vx, vz - 2, 2.4,
                           solid=True, radius=1.1, name="Well"))
        self._add(ent.Prop(self._next_eid(), "shrine", vx - 11, vz - 7, 1.75,
                           solid=True, radius=1.4, name="Shrine"))
        houses = (
            ("house0", 10, -7, -0.35), ("house1", -9, 4, 0.25),
            ("house2", 11, 7, -0.2), ("house0", -6, -13, 0.15),
            ("house1", 3, 13, 0.05),
        )
        for model, dx, dz, yaw in houses:
            hx, hz = self._walkable_near(vx + dx, vz + dz, 10.0)
            self._add(ent.Prop(self._next_eid(), model, hx, hz, 4.3, yaw=yaw,
                               solid=True, radius=2.6))
        self._add(ent.Prop(self._next_eid(), "anvil", vx + 13, vz + 3, 0.8,
                           solid=True, radius=0.6, name="Anvil"))
        self._add(ent.Prop(self._next_eid(), "cart", vx - 14, vz + 2, 1.35,
                           yaw=0.5, solid=True, radius=1.6))
        for dx, dz in ((-16, -6), (17, 10)):
            self._add(ent.Prop(self._next_eid(), "haystack", vx + dx, vz + dz,
                               1.6, solid=True, radius=1.2))
        for i in range(10):
            ang = i * 0.628
            fx = vx + math.cos(ang) * 10.5
            fz = vz - 2 + math.sin(ang) * 10.5
            if not self.terrain.is_path(fx, fz):
                self._add(ent.Prop(self._next_eid(), "fence", fx, fz, 1.15,
                                   yaw=ang + 1.57))
        self._add(ent.Prop(self._next_eid(), "campfire", vx - 2, vz + 6, 0.8,
                           name="Village Fire"))
        elder = ent.Actor(self._next_eid(), "elder", vx - 9, vz - 5, 1.9,
                          kind="villager", hp=30, atk=2, dfn=0, speed=1.2,
                          xp_reward=0, aggro_r=0, attack_range=0,
                          attack_dmg=0, ai_kind="villager",
                          name="Elder Quill")
        self._add(elder)
        smith = ent.Actor(self._next_eid(), "smith", vx + 11, vz + 3, 1.85,
                          kind="villager", hp=40, atk=4, dfn=1, speed=1.3,
                          xp_reward=0, aggro_r=0, attack_range=0,
                          attack_dmg=0, ai_kind="villager",
                          name="Bram the Smith")
        smith.yaw = 2.6
        self._add(smith)
        for i in range(3):
            px, pz = self._walkable_near(vx + rng.uniform(-12, 12),
                                         vz + rng.uniform(-10, 10))
            self._add(ent.Actor(self._next_eid(), "peasant%d" % i, px, pz,
                                1.8, kind="villager", hp=25, atk=2, dfn=0,
                                speed=1.4, xp_reward=0, aggro_r=0,
                                attack_range=0, attack_dmg=0,
                                ai_kind="villager",
                                name=VILLAGER_NAMES[i]))
        for i in range(4):
            px, pz = self._walkable_near(vx + rng.uniform(-8, 8),
                                         vz + rng.uniform(-6, 8))
            self._add(ent.Actor(self._next_eid(), "chicken", px, pz, 0.42,
                                kind="chicken", hp=4, atk=0, dfn=0,
                                speed=1.8, xp_reward=0, aggro_r=0,
                                attack_range=0, attack_dmg=0, home_r=8.0,
                                ai_kind="chicken", radius=0.25))
        for dx, dz in ((-4, 3.2), (5, -3.6)):
            self._add(ent.Pickup(self._next_eid(), "potion", 1,
                                 vx + dx, vz + dz, 0.4))

    def _spawn_castle(self, kx, kz):
        self._add(ent.Prop(self._next_eid(), "castle", kx, kz, 14.0,
                           solid=True, radius=13.0, name="Aldercastle"))
        for sx in (-1.0, 1.0):
            guard = ent.Actor(self._next_eid(), "guard", kx + sx * 5.2,
                              kz + 14.0, 2.05, kind="guard", hp=60, atk=8,
                              dfn=4, speed=2.0, xp_reward=0, aggro_r=0,
                              attack_range=0, attack_dmg=0, ai_kind="guard",
                              name="Gate Guard")
            guard.yaw = 0.0
            self._add(guard)
        for sx, sz in ((-1, 1), (1, 1)):
            b = ent.Prop(self._next_eid(), "banner0",
                         kx + sx * 11.0, kz + sz * 11.0, 2.35)
            b.y_off = 9.0
            self._add(b)
        keep_banner = ent.Prop(self._next_eid(), "banner0", kx, kz, 2.35)
        keep_banner.y_off = 12.4
        self._add(keep_banner)
        wyv = ent.Actor(self._next_eid(), "wyvern", kx + 30, kz, 1.5,
                        kind="wyvern", hp=1, atk=0, dfn=0, speed=0,
                        xp_reward=0, aggro_r=0, attack_range=0, attack_dmg=0,
                        ai_kind="wyvern", radius=0.0)
        self._add(wyv)

    def _spawn_forest(self):
        ter = self.terrain
        rng = self.rng
        vx, vz = ter.village
        kx, kz = ter.castle
        cx, cz = ter.camp
        trees = 0
        gz = 10
        while gz < ter.W - 10 and trees < 240:
            gx = 10
            while gx < ter.W - 10 and trees < 240:
                x = gx + rng.uniform(-1.2, 1.2)
                z = gz + rng.uniform(-1.2, 1.2)
                gx += 3
                if not ter.forest_at(x, z) or ter.is_path(x, z):
                    continue
                if math.hypot(x - vx, z - vz) < 26 or math.hypot(x - kx, z - kz) < 30 \
                        or math.hypot(x - cx, z - cz) < 18:
                    continue
                if not ter.walkable(x, z):
                    continue
                r = rng.random()
                if r < 0.45:
                    model, h = "tree_oak", 3.7
                elif r < 0.75:
                    model, h = "tree_pine", 3.5
                elif r < 0.92:
                    model, h = "tree_birch", 3.3
                else:
                    model, h = "tree_dead", 2.4
                scale = 0.8 + rng.random() * 0.45
                self._add(ent.Prop(self._next_eid(), model, x, z, h,
                                   scale=scale, solid=True, radius=0.5))
                trees += 1
            gz += 3
        placed = 0
        tries = 0
        while placed < 26 and tries < 400:
            tries += 1
            x = 20 + rng.random() * (ter.W - 40)
            z = 20 + rng.random() * (ter.W - 40)
            if not ter.walkable(x, z) or ter.is_path(x, z):
                continue
            if math.hypot(x - vx, z - vz) < 20 or math.hypot(x - kx, z - kz) < 26:
                continue
            model = "rock_b" if rng.random() < 0.3 else "rock_s"
            h = 1.15 if model == "rock_b" else 0.65
            self._add(ent.Prop(self._next_eid(), model, x, z, h,
                               scale=0.8 + rng.random() * 0.4, solid=True,
                               radius=0.5))
            placed += 1
        for i in range(6):
            for _ in range(10):
                wx = cx + (rng.random() - 0.5) * 70.0
                wz = cz + (rng.random() - 0.5) * 70.0
                if ter.forest_at(wx, wz) and ter.walkable(wx, wz):
                    wolf = ent.Actor(self._next_eid(), "wolf", wx, wz, 1.0,
                                     kind="wolf", hp=22, atk=6, dfn=1,
                                     speed=3.6, xp_reward=14, aggro_r=9.0,
                                     attack_range=1.3, attack_dmg=7,
                                     home_r=16.0,
                                     drops={"pelt": 0.8, "gold": 0.5},
                                     name="Grey Wolf")
                    self._add(wolf)
                    break
        midx, midz = (vx + cx) * 0.5, (vz + cz) * 0.5
        for i in range(4):
            bx, bz = self._walkable_near(midx + (rng.random() - 0.5) * 26,
                                         midz + (rng.random() - 0.5) * 26)
            self._add(ent.Actor(self._next_eid(), "bandit", bx, bz, 1.85,
                                kind="bandit", hp=30, atk=8, dfn=2, speed=3.2,
                                xp_reward=22, aggro_r=11.0, attack_range=1.5,
                                attack_dmg=9, home_r=14.0,
                                drops={"gold": 0.9, "potion": 0.25},
                                name="Road Bandit"))

    def _spawn_camp(self, cx, cz):
        rng = self.rng
        self._add(ent.Prop(self._next_eid(), "campfire", cx, cz, 0.8,
                           name="Dead Fire"))
        for i in range(7):
            ang = i * 0.897 + 0.4
            sx, sz = self._walkable_near(cx + math.cos(ang) * 7.5,
                                         cz + math.sin(ang) * 7.5, 6.0)
            skel = ent.Actor(self._next_eid(), "skeleton", sx, sz, 1.9,
                             kind="skeleton", hp=26, atk=7, dfn=1, speed=2.9,
                             xp_reward=18, aggro_r=10.0, attack_range=1.5,
                             attack_dmg=8, home_r=12.0,
                             drops={"bone": 0.9, "gold": 0.6},
                             name="Restless Bones")
            skel.yaw = ang + math.pi
            self._add(skel)
        captain = ent.Actor(self._next_eid(), "captain", cx, cz - 3.5, 2.6,
                            kind="captain", hp=110, atk=13, dfn=4, speed=2.6,
                            xp_reward=120, aggro_r=13.0, attack_range=2.0,
                            attack_dmg=13, home_r=10.0, scale=1.0,
                            drops={"gold": 1.0}, name="The Bone Captain")
        captain.yaw = math.pi
        self._add(captain)
        chest = ent.Chest(self._next_eid(), cx + 4.5, cz + 3.0,
                          {"gold": 140, "potion": 2})
        self._add(chest)
        for dx, dz in ((-6, 4), (7, -5)):
            self._add(ent.Pickup(self._next_eid(), "potion", 1,
                                 cx + dx, cz + dz, 0.4))

    def update(self, dt, env):
        """Advance the world clock, every actor and transient state."""
        self.time += dt
        self.day_t = (0.20 + self.time / self.day_length) % 1.0
        player = self.player
        player.anim_t += dt
        player.flash = max(0.0, player.flash - dt * 3.5)
        player.hurt_t = max(0.0, player.hurt_t - dt)
        player.shrine_cd = max(0.0, player.shrine_cd - dt)
        if player.attacking:
            player.attack_t += dt
            if player.attack_t < 0.16:
                player.pose = "atk0"
            elif player.attack_t < 0.30:
                player.pose = "atk1"
                if not player.attack_done:
                    self.resolve_player_swing()
                    player.attack_done = True
            elif player.attack_t < 0.55:
                player.pose = "atk2"
            else:
                player.attack_t = -1.0
                player.pose = "idle"
        elif player.moving:
            step = int(player.anim_t * 7.0) % 4
            player.pose = "walk%d" % step
        else:
            player.pose = "idle"
        fire_idx = int(self.time * 8.0) % 4
        sway = int(self.time * 0.8)
        picked_up = []
        for e in self.entities:
            if isinstance(e, ent.Actor):
                ent.update_actor(e, dt, self, env)
            elif isinstance(e, ent.Pickup):
                e.y_off = 0.04 + math.sin(self.time * 2.2 + e.bob) * 0.06
                if e.item_id == "gold" and not player.dead:
                    if math.hypot(player.x - e.x, player.z - e.z) < 0.95:
                        player.inventory.add("gold", e.amount)
                        self.add_message("+%d gold" % e.amount, GOLD_COLOR)
                        self.collected.add(e.eid)
                        picked_up.append(id(e))
            elif isinstance(e, ent.Chest):
                if e.opened:
                    e.model = "chest_o"
            if e.model == "campfire":
                e.pose = "fire%d" % ((fire_idx + ent.eid_hash(e.eid)) % 4)
            elif e.model.startswith("tree_") and e.model != "tree_dead":
                e.pose = "sway%d" % ((sway + ent.eid_hash(e.eid)) % 2)
            elif e.model.startswith("banner"):
                e.model = "banner%d" % ((sway + ent.eid_hash(e.eid)) % 2)
        self.entities = [e for e in self.entities
                         if id(e) not in picked_up
                         and not (getattr(e, "dead", False)
                                  and getattr(e, "dead_t", 0.0) > 6.0
                                  and e is not player)]
        for m in self.messages:
            m[2] += dt
        self.messages = [m for m in self.messages if m[2] < 7.0][-6:]
        for d in self.damage_numbers:
            d["t"] += dt
            d["y"] += dt * 1.2
        self.damage_numbers = [d for d in self.damage_numbers if d["t"] < 1.0]

    def add_message(self, text, color=INFO_COLOR):
        self.messages.append([text, color, 0.0])

    def add_damage_number(self, x, z, y, text, color):
        self.damage_numbers.append({"x": x, "z": z, "y": y, "text": text,
                                    "color": color, "t": 0.0})

    def resolve_player_swing(self):
        player = self.player
        inv = player.inventory
        atk = inv.total_atk(player.atk)
        fx, fz = math.sin(player.yaw), math.cos(player.yaw)
        hit_any = False
        for e in self.entities:
            if not isinstance(e, ent.Actor) or e.dead or e is player:
                continue
            if e.ai_kind in ("villager", "chicken", "guard", "wyvern"):
                continue
            dx, dz = e.x - player.x, e.z - player.z
            d = math.hypot(dx, dz)
            reach = 2.1 + e.radius
            if d > reach:
                continue
            dot = (dx * fx + dz * fz) / (d if d > 0.01 else 1.0)
            if dot < 0.42:
                continue
            dmg = damage_roll(atk, e.dfn, self.rng)
            e.hp -= dmg
            e.flash = 1.0
            e.flash_color = (0.7, pack_rgb(255, 230, 230))
            hit_any = True
            self.add_damage_number(e.x, e.z, e.ground_y + e.height * 0.8,
                                   str(dmg), pack_rgb(255, 220, 160))
            if e.state in ("idle", "wander", "return"):
                e.state = "chase"
            nx = e.x + fx * 0.7
            nz = e.z + fz * 0.7
            if self.terrain.walkable(nx, nz):
                e.x, e.z = nx, nz
            if e.hp <= 0:
                self.kill_actor(e)
        if not hit_any:
            self.add_message("The blade whistles through empty air.",
                             INFO_COLOR)

    def kill_actor(self, actor):
        actor.state = "dead"
        actor.pose = "dead"
        actor.dead_t = 0.0
        actor.moving = False
        self.kills.add(actor.eid)
        levels = self._give_xp(actor.xp_reward)
        self.add_message("%s falls!" % (actor.name or "The foe"),
                         pack_rgb(220, 200, 170))
        if levels:
            self.add_message("Level up! You are now level %d." %
                             self.player.level, XP_COLOR)
        rng = self.rng
        for item_id, chance in actor.drops.items():
            if rng.random() < chance:
                if item_id == "gold":
                    amount = 8 + int(rng.random() * 26)
                    self._add_drop(ent.Pickup(self._next_eid(), "gold",
                                              amount, actor.x + 0.4,
                                              actor.z + 0.3, 0.22))
                else:
                    self._add_drop(ent.Pickup(self._next_eid(), item_id, 1,
                                              actor.x + 0.4, actor.z + 0.3,
                                              0.35))
        if actor.kind == "captain":
            self._add_drop(ent.Pickup(self._next_eid(), "amulet", 1,
                                      actor.x, actor.z, 0.45, quest=True))
            self.add_message("The Suncrest Amulet clatters free!",
                             QUEST_COLOR)

    def _add_drop(self, pickup):
        pickup.ground_y = self.terrain.height(pickup.x, pickup.z)
        self.entities.append(pickup)

    def _give_xp(self, amount):
        p = self.player
        p.xp += amount
        levels = 0
        while p.xp >= xp_for_level(p.level):
            p.xp -= xp_for_level(p.level)
            p.level += 1
            p.max_hp += 8
            p.atk = int(p.atk * 1.18) + 1
            p.hp = min(p.max_hp, p.hp + p.max_hp // 3)
            levels += 1
        return levels

    def hit_player(self, dmg, attacker):
        player = self.player
        if player.dead:
            return
        total = damage_roll(dmg, player.inventory.total_dfn(player.dfn),
                            self.rng)
        player.hp -= total
        player.hurt_t = 0.4
        player.flash = 1.0
        player.flash_color = (0.8, pack_rgb(255, 90, 80))
        self.add_damage_number(player.x, player.z,
                               player.ground_y + 2.0, "-%d" % total,
                               HURT_COLOR)
        if player.hp <= 0:
            player.hp = 0
            player.state = "dead"
            self.deaths += 1
            self.add_message("You fall beneath %s's blow..." %
                             (attacker.name or "the foe"), HURT_COLOR)

    def shrine_pray(self):
        player = self.player
        if player.shrine_cd > 0.0:
            self.add_message("The shrine's light is gathering (%d s)." %
                             int(player.shrine_cd), INFO_COLOR)
            return False
        player.shrine_cd = 45.0
        player.hp = min(player.max_hp, player.hp + player.max_hp // 2)
        self.add_message("Warmth flows through you. The vale watches over "
                         "you.", HEAL_COLOR)
        return True

    def respawn_player(self):
        player = self.player
        vx, vz = self.terrain.village
        player.x, player.z = vx, vz + 4
        player.yaw = math.pi
        player.hp = player.max_hp
        player.state = "idle"
        player.stamina = player.max_stamina
        lost = int(player.inventory.count("gold") * 0.15)
        if lost:
            player.inventory.remove("gold", lost)
            self.add_message("You awaken at the shrine, %d gold lighter." %
                             lost, INFO_COLOR)
        else:
            self.add_message("You awaken at the village shrine.", INFO_COLOR)
        player.ground_y = self.terrain.height(player.x, player.z)

    def interact_target(self):
        """Nearest interactable entity in front of the player."""
        player = self.player
        fx, fz = math.sin(player.yaw), math.cos(player.yaw)
        best = None
        best_d = 2.6
        for e in self.entities:
            if e.model == "shrine":
                usable = True
            elif isinstance(e, ent.Actor):
                usable = e.ai_kind in ("villager", "guard")
            elif isinstance(e, ent.Chest):
                usable = not e.opened
            elif isinstance(e, ent.Pickup):
                usable = e.item_id != "gold"
            else:
                usable = False
            if not usable:
                continue
            dx, dz = e.x - player.x, e.z - player.z
            d = math.hypot(dx, dz)
            if d > best_d or d < 0.001:
                continue
            dot = (dx * fx + dz * fz) / d
            if dot < 0.35:
                continue
            best = e
            best_d = d
        return best

    def npc_talk(self, npc):
        """Build the dialogue payload for an NPC based on quest state."""
        if npc.name == "Elder Quill":
            return self._elder_talk()
        if npc.name == "Bram the Smith":
            return {
                "name": npc.name,
                "pages": [
                    "Bram wipes soot from his brow. 'Steel keeps the vale "
                    "standing, ser. Buy something before the dead do.'",
                ],
                "choices": [("Browse wares", "shop"), ("Farewell", "close")],
            }
        if npc.ai_kind == "guard":
            return {
                "name": npc.name or "Gate Guard",
                "pages": [
                    "'Halt! ...Ah, a villager. Mind the east road, ser. "
                    "The old camp stirs at night.'",
                    "'The Captain wears our lord's stolen crown. No blade "
                    "here has the reach for him.'",
                ],
                "choices": [("Farewell", "close")],
            }
        pages = {
            "Mira of the Mill": [
                "'The wolves grow bold since the fires went out in the east "
                "camp, ser.'",
                "'Elder Quill has been praying at the shrine for a champion. "
                "Perhaps... you?'",
            ],
            "Old Tam": [
                "'I remember when the Suncrest hung above the hearth. The "
                "vale was warm then.'",
                "'The Bone Captain keeps it now, they say, deep in the old "
                "camp.'",
            ],
            "Wren the Herder": [
                "'My chickens fret when the wyvern circles. So do I, if I'm "
                "honest.'",
                "'Gold buys Bram's steel. Steel buys tomorrow.'",
            ],
        }.get(npc.name, ["'Fine weather for the vale, ser.'"])
        return {"name": npc.name, "pages": pages,
                "choices": [("Farewell", "close")]}

    def _elder_talk(self):
        if self.quest == "none":
            return {
                "name": "Elder Quill",
                "pages": [
                    "The elder leans on his glowing staff. 'Ser Alaric. The "
                    "Suncrest Amulet, heart of our vale, was stolen by the "
                    "Bone Captain.'",
                    "'His camp squats in the eastern woods. Slay him, bring "
                    "the amulet home, and Aldervale will never forget you.'",
                ],
                "choices": [("I will bring it home.", "quest_accept"),
                            ("I need to think.", "close")],
            }
        if self.quest == "active":
            return {
                "name": "Elder Quill",
                "pages": [
                    "'The Captain's camp lies east, past the wolves. Keep "
                    "your blade sharp and your blood in.'",
                ],
                "choices": [("Farewell", "close")],
            }
        if self.quest == "return":
            return {
                "name": "Elder Quill",
                "pages": [
                    "The elder's eyes shine as you hold up the Suncrest "
                    "Amulet. 'Blessed be this day!'",
                    "'Aldervale owes you a hero's debt. Take this gold, and "
                    "our gratitude, forever.'",
                ],
                "choices": [("Return the amulet.", "quest_complete")],
            }
        return {
            "name": "Elder Quill",
            "pages": ["'The vale is warm again, thanks to you. Rest, hero of "
                      "Aldervale.'"],
            "choices": [("Farewell", "close")],
        }

    def npc_choice(self, action):
        if action == "quest_accept":
            self.quest = "active"
            self.add_message("Quest accepted: The Suncrest Amulet.",
                             QUEST_COLOR)
            return "close"
        if action == "quest_complete":
            self.quest = "done"
            player = self.player
            player.inventory.add("gold", 250)
            self._give_xp(150)
            self.add_message("Quest complete! +250 gold, +150 xp.",
                             QUEST_COLOR)
            self.victory_shown = False
            return "victory"
        return "close"

    def pickup_item(self, pickup):
        player = self.player
        player.inventory.add(pickup.item_id, pickup.amount)
        self.collected.add(pickup.eid)
        self.entities.remove(pickup)
        if pickup.item_id == "amulet":
            self.quest = "return"
            self.add_message("You take the Suncrest Amulet. Return to Elder "
                             "Quill!", QUEST_COLOR)
        else:
            item = ITEMS.get(pickup.item_id)
            name = item.name if item else pickup.item_id
            self.add_message("Picked up %s x%d." % (name, pickup.amount),
                             INFO_COLOR)

    def open_chest(self, chest):
        chest.opened = True
        self.opened_chests.add(chest.eid)
        for item_id, amount in chest.loot.items():
            self.player.inventory.add(item_id, amount)
            item = ITEMS.get(item_id, None)
            label = item.name if item else item_id
            self.add_message("The chest holds %s x%d." % (label, amount),
                             GOLD_COLOR)
        chest.model = "chest_o"

    def buy(self, item_id):
        player = self.player
        item = ITEMS[item_id]
        if player.inventory.count("gold") < item.price:
            self.add_message("Not enough gold for %s." % item.name,
                             HURT_COLOR)
            return False
        player.inventory.remove("gold", item.price)
        player.inventory.add(item_id, 1)
        if item.kind == "weapon" and item.atk > ITEMS[player.inventory.weapon].atk:
            player.inventory.weapon = item_id
            self.add_message("Equipped %s." % item.name, HEAL_COLOR)
        elif item.kind == "armor" and item.dfn > ITEMS[player.inventory.armor].dfn:
            player.inventory.armor = item_id
            self.add_message("Equipped %s." % item.name, HEAL_COLOR)
        else:
            self.add_message("Bought %s." % item.name, INFO_COLOR)
        return True

    def sell(self, item_id):
        player = self.player
        if player.inventory.count(item_id) <= 0:
            return False
        player.inventory.remove(item_id, 1)
        price = max(1, ITEMS[item_id].price // 2)
        player.inventory.add("gold", price)
        self.add_message("Sold %s for %d gold." % (ITEMS[item_id].name, price),
                         GOLD_COLOR)
        return True

    def quest_objective(self):
        if self.quest == "active":
            return "Slay the Bone Captain at the old camp (east)"
        if self.quest == "return":
            return "Return the Suncrest Amulet to Elder Quill"
        if self.quest == "done":
            return "The vale is at peace - roam on"
        return "Speak with Elder Quill in the village (north of the well)"

    def save(self, path):
        """Persist world state atomically (temp file, fsync, replace)."""
        p = self.player
        data = {
            "schema": 1,
            "seed": self.seed,
            "time": self.time,
            "day_t": self.day_t,
            "quest": self.quest,
            "kills": sorted(self.kills),
            "collected": sorted(self.collected),
            "opened_chests": sorted(self.opened_chests),
            "deaths": self.deaths,
            "player": {
                "x": p.x, "z": p.z, "yaw": p.yaw, "hp": p.hp,
                "max_hp": p.max_hp, "atk": p.atk, "dfn": p.dfn,
                "level": p.level, "xp": p.xp, "gold": p.inventory.count("gold"),
                "stamina": p.stamina,
                "weapon": p.inventory.weapon, "armor": p.inventory.armor,
                "counts": {k: v for k, v in p.inventory.counts.items()},
            },
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp_save")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path, atlas, terrain_size=None):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        world = cls(data["seed"], atlas, terrain_size=terrain_size)
        world.time = data["time"]
        world.day_t = data["day_t"]
        world.quest = data["quest"]
        world.kills = set(data["kills"])
        world.collected = set(data["collected"])
        world.opened_chests = set(data["opened_chests"])
        world.deaths = data.get("deaths", 0)
        pd = data["player"]
        p = world.player
        p.x, p.z, p.yaw = pd["x"], pd["z"], pd["yaw"]
        p.hp, p.max_hp = pd["hp"], pd["max_hp"]
        p.atk, p.dfn = pd["atk"], pd["dfn"]
        p.level, p.xp = pd["level"], pd["xp"]
        p.stamina = pd["stamina"]
        p.inventory = Inventory(pd.get("weapon", "rusty_sword"),
                                pd.get("armor", "tunic"))
        p.inventory.counts = dict(pd.get("counts", {}))
        p.ground_y = world.terrain.height(p.x, p.z)
        world.entities = [e for e in world.entities
                          if e.eid not in world.kills
                          and e.eid not in world.collected]
        for e in world.entities:
            if isinstance(e, ent.Chest) and e.eid in world.opened_chests:
                e.opened = True
                e.model = "chest_o"
        return world

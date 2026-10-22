"""Game shell: states, input, camera, main loop, demo autopilot."""

import math
import os
import time

from . import hud
from .atlas import SpriteAtlas
from .buffer import Screen
from .entities import move_actor
from .render import Camera, Env, render_scene
from .rules import ITEMS, WEAPON_ORDER, ARMOR_ORDER
from .term import Terminal
from .world import World

SAVE_NAME = "saves/aldervale.json"


class Game:
    """Drives one play session from title screen to victory."""

    def __init__(self, seed=7, width=None, height=None, fps=30, color=True,
                 demo_secs=None, benchmark=False, save_path=SAVE_NAME,
                 terrain_size=None):
        self.seed = seed
        self.terrain_size = terrain_size
        self.fps_cap = fps
        self.color = color
        self.demo_secs = demo_secs
        self.benchmark = benchmark
        self.save_path = save_path
        self.term = None
        self.screen = None
        self.world = None
        self.atlas = None
        self.state = "title"
        self.running = True
        self.cam_yaw = math.pi
        self.cam_dist = 6.0
        self.cam = None
        self.menu_sel = 0
        self.dialogue = None
        self.dlg_page = 0
        self.dlg_choice = 0
        self.shop_mode = "buy"
        self.shop_sel = 0
        self.shop_message = ""
        self.inv_message = ""
        self.victory_t = 0.0
        self.show_map = True
        self.fps = 0
        self._frames = 0
        self._fps_t = 0.0
        self._term_size = (0, 0)
        self._resize_check = 0
        self._load_progress = []
        self.cam_y = 6.0
        self.cam_pitch = 0.30
        self.walk_target = None
        self._drag = None
        self.dt = 0.016
        self.help_from = "play"
        self.w = width or 132
        self.h = height or 60

    def boot(self, term, progress=None):
        """Bake sprites and build the world; call before run()."""
        self.term = term
        self.atlas = SpriteAtlas()
        self.atlas.build(progress=progress or (lambda k, f: None))
        self.world = World(self.seed, self.atlas,
                           terrain_size=self.terrain_size)
        self._open_screen()

    def _open_screen(self):
        if self.term is not None:
            tw, th = self.term.size()
            self.w = min(max(tw, 40), 260)
            self.h = min(max(th - 1, 20), 110)
        self.screen = Screen(self.w, self.h, color=self.color)
        self._term_size = (self.w, self.h)
        self.cam = None

    def _ensure_camera(self):
        if self.cam is None or self.cam.w != self.w or self.cam.h != self.h:
            self._update_camera(force=True)

    def _update_camera(self, force=False):
        w = self.world
        p = w.player
        if self.state == "title":
            ang = w.time * 0.10
            kx, kz = w.terrain.castle
            cx = kx + math.sin(ang) * 58.0
            cz = kz + math.cos(ang) * 58.0
            cy = w.terrain.height(cx, cz) + 12.0
            yaw = ang + math.pi / 2.0
            self.cam = Camera(self.w, self.h, cx, cz, cy, yaw, pitch=0.24)
            return
        fx = math.sin(self.cam_yaw)
        fz = math.cos(self.cam_yaw)
        cx = p.x - fx * self.cam_dist
        cz = p.z - fz * self.cam_dist
        ground = w.terrain.height(cx, cz)
        target_y = max(ground + 2.9, p.ground_y + 2.3)
        if self.cam is None or force or self.cam.w != self.w or \
                self.cam.h != self.h:
            self.cam_y = target_y
        else:
            self.cam_y += (target_y - self.cam_y) * min(1.0, 0.18)
        self.cam = Camera(self.w, self.h, cx, cz, self.cam_y, self.cam_yaw,
                          pitch=self.cam_pitch, dist=self.cam_dist)

    def run(self):
        """Main loop until the player quits or the demo expires."""
        last = time.monotonic()
        demo_end = None
        if self.demo_secs is not None:
            demo_end = time.monotonic() + self.demo_secs
        while self.running:
            now = time.monotonic()
            dt = min(0.05, now - last)
            last = now
            self.dt = dt
            self._poll_resize()
            self._handle_keys()
            if self.demo_secs is not None:
                self._demo_steer(dt)
                if now >= demo_end:
                    self.running = False
            env = Env(self.world.day_t, self.world.time)
            if self.state in ("play", "title", "dead"):
                self.world.update(dt, env)
            self._sync_death()
            if self.world.quest == "done" and not self.world.victory_shown:
                self.world.victory_shown = True
                self.victory_t = 0.0
            if self.world.victory_shown:
                self.victory_t += dt
            self._render(env)
            self._tick_fps(now)
            frame_budget = 1.0 / self.fps_cap
            elapsed = time.monotonic() - now
            if elapsed < frame_budget and self.term is not None:
                time.sleep(frame_budget - elapsed)
        return 0

    def _sync_death(self):
        """Enter the dead game state once the player actor has fallen."""
        if self.state == "play" and self.world.player.dead:
            self.state = "dead"

    def _tick_fps(self, now):
        self._frames += 1
        if now - self._fps_t >= 1.0:
            self.fps = self._frames
            self._frames = 0
            self._fps_t = now

    def _poll_resize(self):
        if self.term is None:
            return
        self._resize_check -= 1
        if self._resize_check > 0:
            return
        self._resize_check = 20
        tw, th = self.term.size()
        nw = min(max(tw, 40), 260)
        nh = min(max(th - 1, 20), 110)
        if (nw, nh) != self._term_size:
            self.w, self.h = nw, nh
            self._open_screen()

    def _demo_steer(self, dt):
        self.state = "play"
        p = self.world.player
        p.moving = False
        self.cam_yaw += dt * 0.18

    def _handle_keys(self):
        if self.term is None:
            return
        pressed, held = self.term.poll()
        if self.state == "play":
            for ev in self.term.take_mouse():
                self._on_mouse(ev)
        if pressed:
            start_state = self.state
            for key in pressed:
                handler = getattr(self, "_key_%s" % self.state, None)
                if handler:
                    handler(key)
                if self.state != start_state:
                    break
        if self.state == "play":
            self._apply_movement_held(held)

    def _on_mouse(self, ev):
        kind, col, row, buttons, wheel = ev
        if kind == "resize":
            self._resize_check = 0
            return
        if kind == "wheel":
            if wheel > 0:
                self.cam_dist = max(3.5, self.cam_dist - 0.8)
            else:
                self.cam_dist = min(15.0, self.cam_dist + 0.8)
            return
        if kind == "rdown":
            self._drag = (col, row)
            self._click_pending = None
            return
        if kind == "up":
            if self._click_pending is not None:
                px, py = self._click_pending
                if abs(col - px) <= 2 and abs(row - py) <= 2:
                    self._click_at(col, row)
                self._click_pending = None
            self._drag = None
            return
        if kind == "move":
            if self._click_pending is not None:
                px, py = self._click_pending
                if abs(col - px) > 2 or abs(row - py) > 2:
                    self._click_pending = None
            if self._drag is not None:
                dx = col - self._drag[0]
                dy = row - self._drag[1]
                self.cam_yaw += dx * 0.045
                self.cam_pitch = max(0.12, min(0.62,
                                            self.cam_pitch + dy * 0.012))
            self._drag = (col, row) if (buttons & 0x2) else None
            return
        if kind == "ldown":
            if self._drag is None:
                self._click_pending = (col, row)
            return

    def pick_world(self, col, row):
        """Screen cell to a world point using the depth buffer."""
        if self.cam is None or not (0 <= col < self.w and 0 <= row < self.h):
            return None
        depth = self.screen.depth[row][col]
        if not (0.7 <= depth < 1.0e8):
            return None
        ang = self.cam.yaw + self.cam.col_angle[col]
        return (self.cam.x + math.sin(ang) * depth,
                self.cam.z + math.cos(ang) * depth)

    def _click_at(self, col, row):
        p = self.world.player
        if p.dead or p.attacking:
            return
        point = self.pick_world(col, row)
        if point is None:
            return
        tx, tz = point
        best = None
        best_d = 2.6
        for e in self.world.entities:
            if getattr(e, "kind", "") not in ("wolf", "bandit", "skeleton",
                                              "captain"):
                continue
            if getattr(e, "dead", False):
                continue
            d = math.hypot(e.x - tx, e.z - tz)
            if d < best_d:
                best = e
                best_d = d
        if best is not None:
            reach = 2.2 + best.radius
            if math.hypot(best.x - p.x, best.z - p.z) <= reach:
                p.yaw = math.atan2(best.x - p.x, best.z - p.z)
                self._try_attack()
                self.walk_target = None
                return
            self.walk_target = (best.x, best.z)
            return
        self.walk_target = (tx, tz)

    def _apply_movement_held(self, held):
        """Continuous movement, turning and sprint from held key tokens."""
        p = self.world.player
        if p.dead or p.attacking:
            p.moving = False
            return
        fwd = 0.0
        side = 0.0
        if "w" in held or "up" in held:
            fwd += 1.0
        if "s" in held or "down" in held:
            fwd -= 1.0
        if "d" in held:
            side += 1.0
        if "a" in held:
            side -= 1.0
        if "left" in held:
            self.cam_yaw -= 2.2 * self.dt
        if "right" in held:
            self.cam_yaw += 2.2 * self.dt
        if self.walk_target is not None:
            if fwd != 0.0 or side != 0.0:
                self.walk_target = None
            else:
                tx, tz = self.walk_target
                dx = tx - p.x
                dz = tz - p.z
                dist = math.hypot(dx, dz)
                if dist < 0.5:
                    self.walk_target = None
                    target = self.world.interact_target()
                    if target is not None:
                        self._try_interact()
                    self._movement(0.0, 0.0, False)
                    return
                fx = math.sin(self.cam_yaw)
                fz = math.cos(self.cam_yaw)
                fwd = (dx * fx + dz * fz) / dist
                side = (dx * fz - dz * fx) / dist
        self._movement(fwd, side, "shift" in held)

    def _movement(self, fwd, side, sprint):
        p = self.world.player
        if p.dead or p.attacking:
            p.moving = False
            return
        speed = p.speed * (1.45 if sprint and p.stamina > 1 else 1.0)
        if sprint and (fwd != 0.0 or side != 0.0):
            p.stamina = max(0.0, p.stamina - 16.0 * self.dt)
        else:
            p.stamina = min(p.max_stamina, p.stamina + 11.0 * self.dt)
        if fwd == 0.0 and side == 0.0:
            p.moving = False
            return
        fx = math.sin(self.cam_yaw)
        fz = math.cos(self.cam_yaw)
        dx = (fx * fwd + fz * side)
        dz = (fz * fwd - fx * side)
        d = math.hypot(dx, dz)
        if d < 1e-6:
            p.moving = False
            return
        dx, dz = dx / d, dz / d
        p.yaw = math.atan2(dx, dz)
        move_actor(p, dx * speed, dz * speed, self.world, self.dt)
        p.moving = True

    def _try_attack(self):
        p = self.world.player
        if p.attacking or p.dead or p.stamina < 12:
            return
        self.walk_target = None
        p.stamina -= 12
        p.attack_t = 0.0
        p.attack_done = False

    def _try_interact(self):
        w = self.world
        self.walk_target = None
        target = w.interact_target()
        if target is None:
            return
        if target.model == "shrine":
            w.shrine_pray()
        elif hasattr(target, "item_id"):
            w.pickup_item(target)
        elif hasattr(target, "opened"):
            w.open_chest(target)
        elif getattr(target, "ai_kind", "") in ("villager", "guard"):
            self.dialogue = w.npc_talk(target)
            self.dialogue["_npc"] = target.eid
            self.dlg_page = 0
            self.dlg_choice = 0
            self.state = "dialogue"

    def _use_potion(self):
        p = self.world.player
        if p.inventory.count("potion") <= 0:
            self.inv_message = "No potions left."
            return
        if p.hp >= p.max_hp:
            self.inv_message = "You are already hale."
            return
        p.inventory.remove("potion", 1)
        p.hp = min(p.max_hp, p.hp + ITEMS["potion"].heal)
        self.world.add_message("You drink a healing draught (+%d HP)." %
                               ITEMS["potion"].heal, hud.GREEN)

    def _equip_best(self):
        inv = self.world.player.inventory
        changed = False
        for wid in WEAPON_ORDER:
            if inv.count(wid) and ITEMS[wid].atk > ITEMS[inv.weapon].atk:
                inv.weapon = wid
                changed = True
        for aid in ARMOR_ORDER:
            if inv.count(aid) and ITEMS[aid].dfn > ITEMS[inv.armor].dfn:
                inv.armor = aid
                changed = True
        self.inv_message = ("Equipped your best gear." if changed
                            else "You already wear your best.")

    def _key_play(self, key):
        if key == "esc":
            self.state = "pause"
            self.menu_sel = 0
            return
        if key == "i":
            self.state = "inventory"
            self.inv_message = ""
            return
        if key in ("h", "f1"):
            self.help_from = "play"
            self.state = "help"
            return
        if key == "m":
            self.show_map = not self.show_map
            return
        if key == "space":
            self._try_attack()
            return
        if key in ("e", "enter"):
            self._try_interact()
            return
        if key in ("+", "="):
            self.cam_dist = max(3.5, self.cam_dist - 0.7)
            return
        if key == "-":
            self.cam_dist = min(13.0, self.cam_dist + 0.7)
            return

    def _key_title(self, key):
        if key == "n":
            self.world = World(self.seed, self.atlas,
                               terrain_size=self.terrain_size)
            self.state = "play"
        elif key == "c":
            if os.path.exists(self.save_path):
                self.world = World.load(self.save_path, self.atlas)
                self.state = "play"
            else:
                self.world = World(self.seed, self.atlas,
                                   terrain_size=self.terrain_size)
                self.state = "play"
        elif key in ("h", "f1"):
            self.help_from = "title"
            self.state = "help"
        elif key == "q":
            self.running = False

    def _key_dialogue(self, key):
        dlg = self.dialogue
        n_pages = len(dlg["pages"])
        if key == "esc":
            self.state = "play"
            return
        if self.dlg_page < n_pages - 1:
            if key in ("space", "enter"):
                self.dlg_page += 1
            return
        choices = dlg["choices"]
        if key in ("up", "w"):
            self.dlg_choice = (self.dlg_choice - 1) % len(choices)
        elif key in ("down", "s"):
            self.dlg_choice = (self.dlg_choice + 1) % len(choices)
        elif key in ("space", "enter"):
            label, action = choices[self.dlg_choice]
            if action == "shop":
                self.state = "shop"
                self.shop_mode = "buy"
                self.shop_sel = 0
                self.shop_message = ""
                return
            result = self.world.npc_choice(action)
            if result == "victory":
                self.state = "play"
                self.victory_t = 0.0
            else:
                self.state = "play"
        elif key in ("1", "2", "3", "4"):
            idx = int(key) - 1
            if idx < len(choices):
                self.dlg_choice = idx

    def _key_shop(self, key):
        from .rules import SHOP_STOCK
        w = self.world
        if key == "esc":
            self.state = "play"
            return
        if key == "tab":
            self.shop_mode = "buy" if self.shop_mode == "sell" else "sell"
            self.shop_sel = 0
            return
        if self.shop_mode == "buy":
            n = len(SHOP_STOCK)
            if key in ("up", "w"):
                self.shop_sel = (self.shop_sel - 1) % n
            elif key in ("down", "s"):
                self.shop_sel = (self.shop_sel + 1) % n
            elif key in ("space", "enter"):
                item_id = SHOP_STOCK[self.shop_sel]
                if w.buy(item_id):
                    self.shop_message = "Bought %s." % ITEMS[item_id].name
                else:
                    self.shop_message = "You cannot afford that."
        else:
            sellables = [iid for iid, cnt in
                         sorted(w.player.inventory.counts.items())
                         if cnt > 0 and iid != "amulet"]
            if not sellables:
                return
            n = len(sellables)
            if key in ("up", "w"):
                self.shop_sel = (self.shop_sel - 1) % n
            elif key in ("down", "s"):
                self.shop_sel = (self.shop_sel + 1) % n
            elif key in ("space", "enter"):
                iid = sellables[self.shop_sel]
                if w.sell(iid):
                    self.shop_message = "Sold %s." % ITEMS[iid].name
                    self.shop_sel = max(0, self.shop_sel - 1)

    def _key_inventory(self, key):
        if key in ("i", "esc"):
            self.state = "play"
        elif key == "u":
            self._use_potion()
        elif key == "e":
            self._equip_best()

    def _key_help(self, key):
        if key is not None:
            self.state = self.help_from

    def _key_pause(self, key):
        if key == "esc" or key == "c":
            self.state = "play"
        elif key in ("up", "w"):
            self.menu_sel = (self.menu_sel - 1) % 4
        elif key in ("down", "s"):
            self.menu_sel = (self.menu_sel + 1) % 4
        elif key in ("space", "enter"):
            if self.menu_sel == 0:
                self.state = "play"
            elif self.menu_sel == 1:
                self.world.save(self.save_path)
                self.state = "title"
            elif self.menu_sel == 2:
                self.help_from = "pause"
                self.state = "help"
            else:
                self.running = False

    def _key_dead(self, key):
        if key is not None:
            self.world.respawn_player()
            self.state = "play"

    def _render(self, env):
        self._ensure_camera()
        self._update_camera()
        scr = self.screen
        render_scene(scr, self.world, self.cam, env)
        if self.state == "title":
            hud.draw_title(scr, self.world, self.cam, env, self.menu_sel,
                           os.path.exists(self.save_path))
        else:
            hud.draw_world_overlays(scr, self.world, self.cam)
            hud.draw_hud(scr, self.world, env, self.fps, self.show_map)
            hud.draw_hurt_vignette(scr, self.world)
            if self.world.victory_shown:
                hud.draw_victory(scr, self.world, self.victory_t)
            if self.state == "dialogue":
                hud.draw_dialogue(scr, self.world, self.dialogue,
                                  self.dlg_page, self.dlg_choice)
            elif self.state == "shop":
                hud.draw_shop(scr, self.world, self.shop_mode, self.shop_sel,
                              self.shop_message)
            elif self.state == "inventory":
                hud.draw_inventory(scr, self.world, self.inv_message)
            elif self.state == "help":
                hud.draw_help(scr)
            elif self.state == "pause":
                hud.draw_pause(scr, self.menu_sel)
            if self.world.player.dead and self.state != "pause":
                hud.draw_death(scr, self.world)
        if self.term is not None:
            scr.flush(self.term)

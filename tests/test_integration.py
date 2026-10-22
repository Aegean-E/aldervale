"""Integration tier: world generation, quest chain, rendering and the CLI."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, ".")

from aldervale.atlas import SpriteAtlas
from aldervale.buffer import Screen
from aldervale.game import Game
from aldervale.render import Camera, Env, render_scene
from aldervale.terrain import Terrain
from aldervale.world import World

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMALL = 72


def _tiny_atlas():
    return SpriteAtlas().build(keys=["knight", "rock_s", "gold"])


class TestTerrain(unittest.TestCase):
    def test_deterministic(self):
        a = Terrain(11, size=SMALL, octaves=3)
        b = Terrain(11, size=SMALL, octaves=3)
        for z in (5, 20, 40, 60):
            for x in (5, 20, 40, 60):
                self.assertEqual(a.height(x, z), b.height(x, z))

    def test_village_flattened_and_walkable(self):
        t = Terrain(11, size=SMALL, octaves=3)
        vx, vz = t.village
        h_center = t.height(vx, vz)
        for dx, dz in ((0, 0), (3, 0), (-3, 2), (1, -4)):
            self.assertLess(abs(t.height(vx + dx, vz + dz) - h_center), 1.6)
        self.assertTrue(t.walkable(vx, vz))

    def test_island_has_sea_at_corners(self):
        t = Terrain(11, size=SMALL, octaves=3)
        W = t.W
        for x, z in ((2, 2), (W - 3, 2), (2, W - 3), (W - 3, W - 3)):
            self.assertLessEqual(t.height(x, z), t.water)

    def test_path_exists_between_village_and_castle(self):
        t = Terrain(11, size=SMALL, octaves=3)
        vx, vz = t.village
        kx, kz = t.castle
        steps = 30
        hits = 0
        for i in range(steps + 1):
            f = i / steps
            if t.is_path(vx + (kx - vx) * f, vz + (kz - vz) * f):
                hits += 1
        self.assertGreater(hits, 3)


class _FakeWorld:
    pass


class TestRenderScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.terrain = Terrain(11, size=SMALL, octaves=3)
        cls.atlas = _tiny_atlas()

    def _world_with_entities(self):
        w = _FakeWorld()
        w.terrain = self.terrain
        w.atlas = self.atlas
        w.fireflies = []
        w.entities = []
        ter = self.terrain
        vx, vz = ter.village
        for i, model in enumerate(("knight", "rock_s", "knight")):
            w.entities.append(SimpleNamespace(
                model=model, pose="idle", x=vx + i * 2.0, z=vz - 4.0,
                yaw=math.pi, height=1.95, scale=1.0, y_off=0.0,
                ground_y=ter.height(vx + i * 2.0, vz - 4.0), flash=0.0,
                flash_color=None))
        return w

    def test_scene_fills_screen_with_sky_on_top(self):
        w = self._world_with_entities()
        scr = Screen(64, 30, color=True)
        vx, vz = self.terrain.village
        cam = Camera(64, 30, vx, vz + 14,
                     self.terrain.height(vx, vz + 14) + 3.2, math.pi)
        env = Env(0.25, 5.0)
        render_scene(scr, w, cam, env)
        self.assertGreater(scr.stats(), 300)
        top = "".join(scr.chars[0])
        self.assertIn(top[2], " .:,")

    def test_night_darkens_and_lights_fireflies(self):
        w = self._world_with_entities()
        w.fireflies = [(self.terrain.village[0] + 2,
                        self.terrain.village[1] - 2, 0.7)]
        scr = Screen(64, 30, color=True)
        vx, vz = self.terrain.village
        cam = Camera(64, 30, vx, vz + 14,
                     self.terrain.height(vx, vz + 14) + 3.2, math.pi)
        render_scene(scr, w, cam, Env(0.75, 5.0))
        day = Env(0.25, 5.0)
        self.assertLess(Env(0.75, 5.0).ambient[0], day.ambient[0])

    def test_entities_occluded_behind_terrain_depth(self):
        w = self._world_with_entities()
        scr = Screen(64, 30, color=True)
        vx, vz = self.terrain.village
        cam = Camera(64, 30, vx, vz + 14,
                     self.terrain.height(vx, vz + 14) + 3.2, math.pi)
        render_scene(scr, w, cam, Env(0.25, 5.0))
        self.assertIsNotNone(scr.depth[15])


class TestWorldSim(unittest.TestCase):
    def _world(self):
        return World(3, None, terrain_size=SMALL)

    def test_deterministic_generation(self):
        a = self._world()
        b = self._world()
        self.assertEqual(len(a.entities), len(b.entities))
        for ea, eb in zip(a.entities, b.entities):
            self.assertEqual(ea.eid, eb.eid)
            self.assertEqual((ea.x, ea.z), (eb.x, eb.z))

    def test_spawns_present(self):
        w = World(3, None)
        kinds = [getattr(e, "kind", None) for e in w.entities]
        self.assertEqual(kinds.count("captain"), 1)
        self.assertEqual(kinds.count("wolf"), 6)
        self.assertEqual(kinds.count("skeleton"), 7)
        self.assertEqual(kinds.count("villager"), 5)
        self.assertEqual(kinds.count("chicken"), 4)
        self.assertEqual(kinds.count("wyvern"), 1)
        models = [e.model for e in w.entities]
        self.assertIn("castle", models)
        self.assertIn("shrine", models)

    def test_full_quest_chain(self):
        w = self._world()
        self.assertEqual(w.quest, "none")
        self.assertEqual(w.npc_choice("quest_accept"), "close")
        self.assertEqual(w.quest, "active")
        captain = next(e for e in w.entities
                       if getattr(e, "kind", "") == "captain")
        p = w.player
        p.x = captain.x
        p.z = captain.z - 1.2
        p.yaw = 0.0
        captain.hp = 1
        captain.aggro_r = 0.0
        p.attack_t = 0.0
        p.attack_done = False
        env = Env(0.25, 0.0)
        for _ in range(24):
            w.update(1.0 / 30.0, env)
        self.assertIn(captain.eid, w.kills)
        amulet = next(e for e in w.entities
                      if getattr(e, "item_id", None) == "amulet")
        w.pickup_item(amulet)
        self.assertEqual(w.quest, "return")
        self.assertEqual(w.npc_choice("quest_complete"), "victory")
        self.assertEqual(w.quest, "done")
        self.assertGreaterEqual(w.player.inventory.count("gold"), 280)
        self.assertGreaterEqual(w.player.level, 2)

    def test_save_load_roundtrip(self):
        w = self._world()
        w.player.inventory.add("gold", 123)
        gold_total = w.player.inventory.count("gold")
        w.player.x += 3.0
        w.quest = "active"
        path = os.path.join(self.get_temp_dir(), "save.json")
        w.save(path)
        w2 = World.load(path, None, terrain_size=SMALL)
        self.assertEqual(w2.player.inventory.count("gold"), gold_total)
        self.assertAlmostEqual(w2.player.x, w.player.x, places=4)
        self.assertEqual(w2.quest, "active")
        self.assertEqual(len(w2.entities), len(w.entities))

    def get_temp_dir(self):
        d = tempfile.mkdtemp(prefix="aldervale_test_")
        self.addCleanup(lambda: _rmtree(d))
        return d

    def test_interact_and_shrine(self):
        w = self._world()
        p = w.player
        elder = next(e for e in w.entities
                     if getattr(e, "name", None) == "Elder Quill")
        p.x = elder.x + 0.8
        p.z = elder.z
        p.yaw = -math.pi / 2
        self.assertIs(w.interact_target(), elder)
        p.hp = 10
        shrine = next(e for e in w.entities if e.model == "shrine")
        p.x = shrine.x + 1.0
        p.z = shrine.z
        p.yaw = -math.pi / 2
        self.assertIs(w.interact_target(), shrine)
        self.assertTrue(w.shrine_pray())
        self.assertFalse(w.shrine_pray())
        self.assertGreater(p.hp, 10)

    def test_chest_loot(self):
        w = self._world()
        chest = next(e for e in w.entities if hasattr(e, "opened"))
        gold_before = w.player.inventory.count("gold")
        w.open_chest(chest)
        self.assertTrue(chest.opened)
        self.assertGreater(w.player.inventory.count("gold"), gold_before)
        self.assertEqual(chest.model, "chest_o")


def _rmtree(d):
    import shutil
    shutil.rmtree(d, ignore_errors=True)


class TestGameShell(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game(seed=3, width=80, height=40,
                        save_path=os.path.join(tempfile.gettempdir(),
                                               "av_test_save.json"))
        cls.game.term = None
        cls.game.atlas = _tiny_atlas()
        cls.game.world = World(3, cls.game.atlas)
        cls.game._open_screen()
        cls.game._ensure_camera()
        cls.game.state = "play"
        cls.game._dt = 1.0 / 30.0

    def _render_once(self):
        env = Env(self.game.world.day_t, self.game.world.time)
        self.game._render(env)
        return self.game.screen

    def test_movement_changes_position(self):
        g = self.game
        p = g.world.player
        z0 = p.z
        g.cam_yaw = math.pi
        g._movement(1.0, 0.0, False)
        g.world.update(1.0 / 30.0, Env(0.25, 0.0))
        self.assertLess(p.z, z0)
        self.assertTrue(p.moving)

    def test_attack_kills_wounded_wolf(self):
        g = self.game
        w = g.world
        p = w.player
        wolf = next(e for e in w.entities
                    if getattr(e, "kind", "") == "wolf")
        wolf.hp = 1
        wolf.aggro_r = 0.0
        wolf.state = "idle"
        p.x = wolf.x
        p.z = wolf.z - 1.0
        p.yaw = 0.0
        p.attack_t = -1.0
        g._try_attack()
        self.assertTrue(p.attacking)
        env = Env(0.25, 0.0)
        for _ in range(20):
            w.update(1.0 / 30.0, env)
        self.assertIn(wolf.eid, w.kills)

    def test_state_transitions(self):
        g = self.game
        g._key_play("i")
        self.assertEqual(g.state, "inventory")
        g._key_inventory("esc")
        self.assertEqual(g.state, "play")
        g._key_play("h")
        self.assertEqual(g.state, "help")
        g._key_help("x")
        self.assertEqual(g.state, "play")
        g._key_play("esc")
        self.assertEqual(g.state, "pause")
        g._key_pause("c")
        self.assertEqual(g.state, "play")

    def test_potion_use_heals(self):
        g = self.game
        p = g.world.player
        p.inventory.add("potion", 1)
        p.hp = 5
        g._use_potion()
        self.assertEqual(p.inventory.count("potion"), 1)
        self.assertEqual(p.hp, p.max_hp)

    def test_render_frame_smoke(self):
        scr = self._render_once()
        self.assertGreater(scr.stats(), 500)

    def test_save_and_load_via_game(self):
        g = self.game
        g.world.player.inventory.add("gold", 55)
        gold_total = g.world.player.inventory.count("gold")
        g.world.save(g.save_path)
        loaded = World.load(g.save_path, g.atlas)
        self.assertEqual(loaded.player.inventory.count("gold"), gold_total)
        os.remove(g.save_path)


class TestCliSubprocess(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "aldervale", *args],
            cwd=PROJECT, capture_output=True, text=True, timeout=120)

    def test_version(self):
        r = self._run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ALDERVALE", r.stdout)

    def test_unknown_flag_is_misuse(self):
        r = self._run("--bogus")
        self.assertEqual(r.returncode, 2)

    def test_headless_demo(self):
        r = self._run("--demo", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("demo:", r.stdout)

    def test_screenshot_writes_frame(self):
        d = tempfile.mkdtemp(prefix="aldervale_shot_")
        self.addCleanup(lambda: _rmtree(d))
        path = os.path.join(d, "vista.txt")
        r = self._run("--screenshot", path)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertGreater(len(lines), 40)
        self.assertTrue(all(len(line) > 40 for line in lines[:5]))


class TestReviewFixes(unittest.TestCase):
    """Regressions for defects found in the aldervale code review."""

    def _world(self):
        return World(3, None, terrain_size=SMALL)

    def test_gold_pickups_collected_same_frame(self):
        from aldervale.entities import Pickup
        w = self._world()
        p = w.player
        w._add_drop(Pickup("gold_a", "gold", 5, p.x, p.z, 0.22))
        w._add_drop(Pickup("gold_b", "gold", 7, p.x, p.z, 0.22))
        w.update(1.0 / 30.0, Env(0.25, 0.0))
        self.assertIn("gold_a", w.collected)
        self.assertIn("gold_b", w.collected)
        self.assertEqual(p.inventory.count("gold"), 30 + 5 + 7)

    def test_hud_bars_do_not_overlap(self):
        w = self._world()
        from aldervale import hud
        scr = Screen(110, 50, color=True)
        hud.draw_hud(scr, w, Env(0.25, 0.0), 60)
        row = "".join(scr.chars[scr.h - 4])
        p = w.player
        self.assertIn("%d/%d" % (p.hp, p.max_hp), row,
                      "HP readout overwritten by the stamina bar")
        hp = row.find("HP")
        stam = row.find("Stam")
        xp = row.find("XP")
        pot = row.find("Pot")
        self.assertLess(hp, stam)
        self.assertLess(stam, xp)
        self.assertLess(xp, pot)

    def test_death_transitions_to_dead_state(self):
        from aldervale.entities import Actor
        w = self._world()
        game = Game(seed=3, terrain_size=SMALL, width=80, height=40)
        game.term = None
        game.atlas = None
        game.world = w
        game._open_screen()
        game._ensure_camera()
        game.state = "play"
        p = w.player
        p.hp = 1
        attacker = Actor("att", "wolf", p.x, p.z + 1.0, 1.0, kind="wolf",
                         hp=10, atk=5, dfn=0, speed=1.0, xp_reward=0,
                         aggro_r=0.0, attack_range=1.0, attack_dmg=50,
                         name="Test Wolf")
        w.hit_player(50, attacker)
        self.assertTrue(p.dead)
        game._sync_death()
        self.assertEqual(game.state, "dead")
        game._key_dead("x")
        self.assertEqual(game.state, "play")
        self.assertEqual(p.hp, p.max_hp)


    def test_gate_guards_spawn_as_twins(self):
        w = World(3, None)
        guards = [e for e in w.entities if getattr(e, "ai_kind", "") == "guard"]
        self.assertEqual(len(guards), 2)
        self.assertEqual({g.name for g in guards},
                         {"Ser Aldous", "Ser Aldric"})
        for g in guards:
            payload = w.npc_talk(g)
            self.assertIn(payload["name"], ("Ser Aldous", "Ser Aldric"))
            self.assertTrue(payload["pages"])

    def test_npc_talk_delegates_to_story(self):
        from aldervale import story
        w = self._world()
        elder = next(e for e in w.entities
                     if getattr(e, "name", None) == "Elder Quill")
        self.assertEqual(w.npc_talk(elder),
                         story.dialogue_for("Elder Quill", w.quest))


class TestLaunchers(unittest.TestCase):
    """The one-click run buttons: PLAY.bat, run.sh and the VS Code config."""

    def test_play_bat_version_fastpath(self):
        if sys.platform != "win32":
            self.skipTest("PLAY.bat is Windows-only")
        r = subprocess.run(
            ["cmd", "/c", os.path.join(PROJECT, "PLAY.bat"), "--version"],
            cwd=PROJECT, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ALDERVALE", r.stdout)

    def test_run_sh_targets_module(self):
        with open(os.path.join(PROJECT, "run.sh"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("python3 -m aldervale", content)
        self.assertIn("python -m aldervale", content)

    def test_play_bat_wt_directory_has_no_trailing_backslash(self):
        with open(os.path.join(PROJECT, "PLAY.bat"),
                  encoding="utf-8", errors="replace") as f:
            content = f.read()
        self.assertNotIn('-d "%~dp0"', content,
                         "trailing backslash escapes the quote and wt "
                         "swallows the whole command line as -d")
        self.assertIn('-d "%CD%"', content)

    def test_vscode_launch_configs(self):
        with open(os.path.join(PROJECT, ".vscode", "launch.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
        names = [c["name"] for c in data["configurations"]]
        self.assertIn("ALDERVALE: Play", names)
        for cfg in data["configurations"]:
            self.assertEqual(cfg["module"], "aldervale")
            self.assertEqual(cfg["cwd"], "${workspaceFolder}")


if __name__ == "__main__":
    unittest.main()

"""Unit tier: fast in-process checks for the pure engine core."""

import io
import sys
import unittest
from contextlib import redirect_stderr

sys.path.insert(0, ".")

from aldervale import math3d as m3
from aldervale import models
from aldervale.atlas import SpriteAtlas
from aldervale.buffer import FAR, NEAREST, Screen, pack_rgb
from aldervale.mesh import RAMP, MeshBuilder, bake_sprite
from aldervale.noise import fbm, value_noise
from aldervale.rules import (ARMOR_ORDER, ITEMS, WEAPON_ORDER, Inventory,
                             damage_roll, xp_for_level)
from aldervale.entities import eid_hash
from aldervale.hud import wrap_text

import random


class FakeTerm:
    def __init__(self):
        self.written = []
        self.flushes = 0

    def write(self, s):
        self.written.append(s)

    def flush(self):
        self.flushes += 1


class TestNoise(unittest.TestCase):
    def test_deterministic_and_bounded(self):
        a = [value_noise(x * 0.3, y * 0.3, 5) for x in range(8)
             for y in range(8)]
        b = [value_noise(x * 0.3, y * 0.3, 5) for x in range(8)
             for y in range(8)]
        self.assertEqual(a, b)
        for v in a:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_fbm_smooth(self):
        v1 = fbm(1.0, 1.0, 9, 3)
        v2 = fbm(1.05, 1.0, 9, 3)
        self.assertLess(abs(v1 - v2), 0.1)
        self.assertGreaterEqual(v1, 0.0)
        self.assertLessEqual(v1, 1.0)


class TestMath3d(unittest.TestCase):
    def test_rot_y_maps_front(self):
        v = m3.mat_vec(m3.rot_y_matrix(0.5), (0.0, 0.0, 1.0))
        self.assertAlmostEqual(v[0], 0.479426, places=5)
        self.assertAlmostEqual(v[1], 0.0, places=5)
        self.assertAlmostEqual(v[2], 0.877582, places=5)

    def test_identity(self):
        m = (1, 0, 0, 0, 1, 0, 0, 0, 1)
        self.assertEqual(m3.mat_vec(m, (1, 2, 3)), (1.0, 2.0, 3.0))

    def test_face_normal_unit_and_direction(self):
        n = m3.face_normal((0, 0, 0), (1, 0, 0), (0, 1, 0))
        self.assertAlmostEqual(n[2], 1.0, places=5)
        self.assertAlmostEqual(m3.length(n), 1.0, places=5)


class TestScreen(unittest.TestCase):
    def test_set_respects_bounds_and_depth(self):
        s = Screen(10, 6, color=False)
        s.set(2, 2, "#", 1, depth=5.0)
        s.set(2, 2, "o", 1, depth=6.0)
        self.assertEqual(s.chars[2][2], "#")
        s.set(2, 2, "o", 1, depth=4.0)
        self.assertEqual(s.chars[2][2], "o")
        s.set(-1, 0, "x", 1)
        s.set(0, 99, "x", 1)
        self.assertEqual(s.stats(), 1)

    def test_text_overrides_with_nearest_depth(self):
        s = Screen(20, 5, color=False)
        s.set(3, 1, "#", 1, depth=2.0)
        s.text(0, 1, "hello", 1)
        self.assertEqual("".join(s.chars[1][:5]), "hello")
        self.assertEqual(s.depth[1][3], NEAREST)

    def test_box_draws_frame(self):
        s = Screen(20, 8, color=False)
        s.box(2, 2, 8, 4, 1)
        self.assertEqual(s.chars[2][2], "+")
        self.assertEqual(s.chars[2][9], "+")
        self.assertEqual(s.chars[5][2], "+")
        self.assertEqual(s.chars[3][2], "|")

    def test_blit_scales_and_occludes(self):
        mesh = models.rock(seed=1)
        sp = bake_sprite(mesh, yaw=0.0, dist=9.0, f=120.0, aspect=0.5,
                         canvas=(30, 20))
        self.assertGreater(sp.filled(), 4)
        s = Screen(40, 24, color=False)
        s.fill_row(20, "#", 1, depth=1.0)
        s.blit(sp, 20.0, 22.0, 8.0, depth=2.0)
        filled = sum(1 for row in s.chars for ch in row if ch not in " #")
        self.assertGreater(filled, 4)

    def test_flush_diff_second_frame_small(self):
        s = Screen(30, 10, color=True)
        term = FakeTerm()
        s.text(0, 0, "alpha", 1)
        s.text(0, 5, "beta", 2)
        n1 = s.flush(term)
        n2 = s.flush(term)
        self.assertEqual(n2, 0)
        s.text(0, 0, "zzzzz", 1)
        n3 = s.flush(term)
        self.assertLess(n3, n1)
        self.assertTrue(any("zzzzz" in w for w in term.written))

    def test_frame_text_rows(self):
        s = Screen(5, 2, color=False)
        s.text(0, 0, "abcde", 1)
        self.assertEqual(s.frame_text(), "abcde\n     ")


class TestMesh(unittest.TestCase):
    def test_box_face_count(self):
        b = MeshBuilder()
        b.box(0, 0, 0, 1, 1, 1, 0x808080)
        mesh = b.build()
        self.assertEqual(len(mesh.verts), 24)
        self.assertEqual(len(mesh.faces), 6)

    def test_cone_and_sphere_face_counts(self):
        b = MeshBuilder()
        b.cone(0, 0, 0, 1.0, 1.0, seg=6)
        b.sphere(2, 0, 0, 1, 1, 1, seg=5, rings=3)
        mesh = b.build()
        self.assertEqual(len(mesh.faces), 6 + 5 * 3)

    def test_bake_sprite_chars_in_ramp(self):
        sp = bake_sprite(models.rock(seed=2), yaw=1.0, dist=9.0, f=100.0,
                         aspect=0.5, canvas=(26, 18))
        for row in sp.chars:
            for ch in row:
                self.assertIn(ch, RAMP)
        self.assertGreater(sp.filled(), 3)

    def test_bake_yaw_frames_differ(self):
        mesh = models.tree_pine(seed=1)
        a = bake_sprite(mesh, yaw=0.0, dist=9.0, f=60.0, aspect=0.5,
                        canvas=(40, 26))
        b = bake_sprite(mesh, yaw=2.0, dist=9.0, f=60.0, aspect=0.5,
                        canvas=(40, 26))
        self.assertNotEqual(a.chars, b.chars)

    def test_emissive_glow_separate(self):
        sp = bake_sprite(models.campfire(frame=1), yaw=0.0, dist=9.0,
                         f=140.0, aspect=0.5, canvas=(30, 22))
        self.assertIsNotNone(sp.glow)
        self.assertGreater(sp.glow.filled(), 0)
        plain = bake_sprite(models.rock(seed=3), yaw=0.0, dist=9.0,
                            f=100.0, aspect=0.5, canvas=(24, 16))
        self.assertIsNone(plain.glow)


class TestAtlas(unittest.TestCase):
    def test_yaw_frame_wraparound(self):
        atlas = SpriteAtlas()
        self.assertEqual(atlas.yaw_frame(0.0, 0.0),
                         atlas.yaw_frame(6.28318, 0.0))
        self.assertEqual(len(set(atlas.yaw_frame(a, 0.0)
                                 for a in (0, 1, 2, 3, 4, 5))), 6)

    def test_heights_registered(self):
        atlas = SpriteAtlas()
        self.assertGreater(atlas.heights["castle"], 10)
        self.assertLess(atlas.heights["chicken"], 1)


class TestRules(unittest.TestCase):
    def test_damage_roll_bounds(self):
        rng = random.Random(1)
        for _ in range(50):
            d = damage_roll(10, 2, rng)
            self.assertGreaterEqual(d, 1)
            self.assertLessEqual(d, 14)

    def test_damage_roll_defence_reduces(self):
        rng = random.Random(2)
        low = sum(damage_roll(10, 0, rng) for _ in range(30))
        high = sum(damage_roll(10, 8, rng) for _ in range(30))
        self.assertGreater(low, high)

    def test_xp_curve_monotonic(self):
        levels = [xp_for_level(l) for l in range(1, 10)]
        self.assertEqual(levels, sorted(levels))
        self.assertGreater(levels[-1], levels[0])

    def test_inventory_ops(self):
        inv = Inventory()
        inv.add("potion", 3)
        inv.remove("potion", 1)
        self.assertEqual(inv.count("potion"), 2)
        inv.remove("potion", 5)
        self.assertEqual(inv.count("potion"), 0)
        self.assertEqual(inv.weapon_atk(), ITEMS["rusty_sword"].atk)
        self.assertEqual(inv.armor_dfn(), ITEMS["tunic"].dfn)

    def test_item_ordering_sensible(self):
        atks = [ITEMS[w].atk for w in WEAPON_ORDER]
        self.assertEqual(atks, sorted(atks))
        dfns = [ITEMS[a].dfn for a in ARMOR_ORDER]
        self.assertEqual(dfns, sorted(dfns))


class TestHudHelpers(unittest.TestCase):
    def test_wrap_text(self):
        lines = wrap_text("the quick brown fox jumps over the lazy dog", 12)
        for line in lines:
            self.assertLessEqual(len(line), 12)
        self.assertEqual(" ".join(lines),
                         "the quick brown fox jumps over the lazy dog")

    def test_eid_hash_stable(self):
        self.assertEqual(eid_hash("e12"), eid_hash("e12"))
        self.assertNotEqual(eid_hash("e12"), eid_hash("e13"))


class TestCliValidation(unittest.TestCase):
    def _run(self, argv):
        from aldervale.__main__ import run
        err = io.StringIO()
        with redirect_stderr(err):
            code = run(argv)
        return code, err.getvalue()

    def test_bad_fps_refused(self):
        code, err = self._run(["--fps", "3"])
        self.assertEqual(code, 1)
        self.assertIn("What:", err)
        self.assertIn("Why:", err)
        self.assertIn("Fix:", err)

    def test_bad_width_refused(self):
        code, _ = self._run(["--width", "9999"])
        self.assertEqual(code, 1)

    def test_bad_demo_seconds_refused(self):
        code, _ = self._run(["--demo", "-2"])
        self.assertEqual(code, 1)


class TestReviewRegressions(unittest.TestCase):
    """Regressions for defects found in the aldervale code review."""

    def test_pack_rgb_clamps_channels(self):
        self.assertEqual(pack_rgb(300, 280, 290), pack_rgb(255, 255, 255))
        self.assertEqual(pack_rgb(-5, -1, 0), 0)
        self.assertEqual(pack_rgb(255.6, 254.9, 0.4), pack_rgb(255, 254, 0))

    def test_water_fog_reaches_fog_colour(self):
        from types import SimpleNamespace

        from aldervale.buffer import unpack_rgb
        from aldervale.render import Camera, Env, _terrain
        W = 64
        water = 1.4
        ter = SimpleNamespace(
            W=W, water=water,
            heights=[[water - 2.0] * W for _ in range(W)],
            colors=[[0x408030] * W for _ in range(W)],
            lights=[[200] * W for _ in range(W)],
        )
        scr = Screen(48, 24, color=True)
        cam = Camera(48, 24, 32.0, 32.0, water + 9.0, 0.0)
        env = Env(0.25, 3.0)
        _terrain(scr, ter, cam, env)
        row = cam.horizon
        r, g, b = unpack_rgb(scr.fg[row][24])
        fr, fgc, fb = unpack_rgb(env.fog)
        self.assertLess(abs(r - fr), 40, "water red channel misses fog")
        self.assertLess(abs(g - fgc), 40, "water green channel misses fog")
        self.assertLess(abs(b - fb), 40, "water blue channel misses fog")

    def test_terminal_min_width_clamped(self):
        from aldervale.game import Game

        class TinyTerm:
            def size(self):
                return (30, 20)

        g = Game(seed=1)
        g.term = TinyTerm()
        g._open_screen()
        self.assertGreaterEqual(g.w, 40)
        self.assertLessEqual(g.w, 260)

    def test_terminal_uses_large_viewport(self):
        from aldervale.game import Game

        class BigTerm:
            def size(self):
                return (250, 106)

        g = Game(seed=1)
        g.term = BigTerm()
        g._open_screen()
        self.assertEqual(g.w, 250)
        self.assertEqual(g.h, 105)


class TestStoryData(unittest.TestCase):
    """The story module is the single source of narrative truth."""

    def test_cast_entries_are_complete(self):
        from aldervale.story import CAST
        for key, entry in CAST.items():
            if isinstance(entry, tuple):
                for member in entry:
                    self.assertIn("name", member)
                    self.assertIn("model", member)
            else:
                self.assertIn("name", entry)
                self.assertIn("model", entry)

    def test_gate_guards_are_the_twins(self):
        from aldervale.story import CAST
        names = {g["name"] for g in CAST["guards"]}
        self.assertEqual(names, {"Ser Aldous", "Ser Aldric"})

    def test_dialogue_for_every_villager(self):
        from aldervale.story import CAST, dialogue_for
        for villager in CAST["villagers"]:
            payload = dialogue_for(villager["name"], "none")
            self.assertEqual(payload["name"], villager["name"])
            self.assertTrue(payload["pages"])
            self.assertIn(("Farewell", "close"), payload["choices"])

    def test_elder_dialogue_covers_quest_states(self):
        from aldervale.story import dialogue_for
        for state in ("none", "active", "return", "done"):
            payload = dialogue_for("Elder Quill", state)
            self.assertTrue(payload["pages"])
        offered = dialogue_for("Elder Quill", "none")
        self.assertIn("quest_accept", [a for _, a in offered["choices"]])
        returned = dialogue_for("Elder Quill", "return")
        self.assertIn("quest_complete", [a for _, a in returned["choices"]])

    def test_quest_objectives_cover_states(self):
        from aldervale.story import QUEST_OBJECTIVES
        self.assertEqual(set(QUEST_OBJECTIVES),
                         {"none", "active", "return", "done"})
        for text in QUEST_OBJECTIVES.values():
            self.assertTrue(text)

    def test_guard_dialogue_carries_twin_name(self):
        from aldervale.story import guard_dialogue
        payload = guard_dialogue("Ser Aldous")
        self.assertEqual(payload["name"], "Ser Aldous")
        self.assertTrue(payload["pages"])

    def test_player_name_single_source(self):
        from aldervale.entities import Player
        from aldervale.story import CAST
        self.assertEqual(Player("player", 0.0, 0.0).name,
                         CAST["player"]["name"])


if __name__ == "__main__":
    unittest.main()

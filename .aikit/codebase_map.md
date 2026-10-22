# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `20`
- **Total Classes**: `45`
- **Total Top-Level Functions**: `107`
- **Total Class Methods**: `243`
- **Total Source Lines**: `6178`

---

## 📦 Modules & Exported Symbols

### [`aldervale/__init__.py`](aldervale/__init__.py)
> *ALDERVALE: a 2.5D medieval RPG rendered entirely in tiny ASCII cells.*

**Size**: `3` lines (`99` bytes)

---

### [`aldervale/__main__.py`](aldervale/__main__.py)
> *ALDERVALE command line entry point.*

**Size**: `185` lines (`6728` bytes)

**Functions:**
- `def _build_parser()`
- `def _fail(what, why, fix)`
- `def run(argv)`
- `def _play(game, demo)`
- `def _screenshot(game, path)` - *Render one scripted vista to a plain text file (no terminal).*
- `def _benchmark(game)`
- `def _headless_demo(game, secs)` - *Non-interactive demo parity for pipes and CI (PRINCIPLE-015).*

---

### [`aldervale/atlas.py`](aldervale/atlas.py)
> *Sprite atlas: bakes every (model, pose, yaw) combination at load time.*

**Size**: `197` lines (`9270` bytes)

**Classes:**
- `class SpriteAtlas` - *Baked sprite frames lookup: (model_key, pose_name) -> [yaw frames].*
  - Method `.__init__(yaw_steps)`
  - Method `.build(progress, keys)`
  - Method `.get(model, pose, frame)`
  - Method `.yaw_frame(ent_yaw, cam_yaw)`

**Functions:**
- `def _spec(builder, poses, size, height, cells, dist, kwargs)`

---

### [`aldervale/buffer.py`](aldervale/buffer.py)
> *Char-cell frame buffer: per-cell glyph, 24-bit colour and depth, diff flush.*

**Size**: `220` lines (`7184` bytes)

**Classes:**
- `class Screen` - *A w x h grid of characters with colour, depth and diff-based output.*
  - Method `.__init__(w, h, color)`
  - Method `.clear()`
  - Method `.invalidate()`
  - Method `.in_bounds(x, y)`
  - Method `.set(x, y, ch, color, depth)`
  - Method `.fill_row(y, ch, color, depth)`
  - Method `.text(x, y, s, color)`
  - Method `.text_centered(y, s, color)`
  - Method `.box(x, y, w, h, color, fill)`
  - Method `.blit(sprite, cx, bottom_row, target_rows, tint, depth, flash, alpha)` - *Draw a baked sprite anchored at (cx, bottom_row) scaled to target_rows.*
  - Method `.frame_text()`
  - Method `.flush(term)` - *Emit only changed cells; returns the number of bytes written.*
  - Method `.stats()`

**Functions:**
- `def pack_rgb(r, g, b)` - *Pack float channels into 0xRRGGBB, clamping overflow to 0..255.*
- `def unpack_rgb(c)`
- `def lerp_color(c1, c2, t)`
- `def scale_color(c, k)`

---

### [`aldervale/entities.py`](aldervale/entities.py)
> *World entities: props, pickups, ambient life and AI-driven actors.*

**Size**: `310` lines (`10903` bytes)

**Classes:**
- `class Entity` - *Anything the renderer draws as a billboard.*
  - Method `.__init__(eid, model, x, z, height, yaw, scale, y_off, pose, name, solid, radius)`
- `class Prop` - *Static scenery.*
- `class Pickup` - *Ground loot bobbing gently; gold is collected by walking over it.*
  - Method `.__init__(eid, item_id, amount, x, z, height, quest)`
- `class Chest` - *A loot chest; opening swaps the sprite and grants contents once.*
  - Method `.__init__(eid, x, z, loot)`
- `class Actor` - *A creature or person with stats and a simple state machine.*
  - Method `.__init__(eid, model, x, z, height, *, kind, hp, atk, dfn, speed, xp_reward, aggro_r, attack_range, attack_dmg, home_r, scale, drops, ai_kind, name, radius)`
  - Property `.dead`
- `class Player` - *The hero: an Actor plus inventory, stamina and quest-facing state.*
  - Method `.__init__(eid, x, z)`
  - Property `.attacking`

**Functions:**
- `def _pickup_model(item_id)`
- `def eid_hash(eid)`
- `def move_actor(actor, dx, dz, world, dt)` - *Move with terrain, water and solid-entity collision; updates ground.*
- `def face_towards(actor, tx, tz)`
- `def update_actor(actor, dt, world, env)` - *Run one actor's AI state machine for this frame.*
- `def _walk_to(actor, tx, tz, world, dt, speed_factor)`
- `def _update_chicken(actor, dt, world)`
- `def _update_villager(actor, dt, world)`

---

### [`aldervale/game.py`](aldervale/game.py)
> *Game shell: states, input, camera, main loop, demo autopilot.*

**Size**: `577` lines (`20321` bytes)

**Classes:**
- `class Game` - *Drives one play session from title screen to victory.*
  - Method `.__init__(seed, width, height, fps, color, demo_secs, benchmark, save_path, terrain_size)`
  - Method `.boot(term, progress)` - *Bake sprites and build the world; call before run().*
  - Method `._open_screen()`
  - Method `._ensure_camera()`
  - Method `._update_camera(force)`
  - Method `.run()` - *Main loop until the player quits or the demo expires.*
  - Method `._sync_death()` - *Enter the dead game state once the player actor has fallen.*
  - Method `._tick_fps(now)`
  - Method `._poll_resize()`
  - Method `._demo_steer(dt)`
  - Method `._handle_keys()`
  - Method `._on_mouse(ev)`
  - Method `.pick_world(col, row)` - *Screen cell to a world point using the depth buffer.*
  - Method `._click_at(col, row)`
  - Method `._apply_movement_held(held)` - *Continuous movement, turning and sprint from held key tokens.*
  - Method `._movement(fwd, side, sprint)`
  - Method `._try_attack()`
  - Method `._try_interact()`
  - Method `._use_potion()`
  - Method `._equip_best()`
  - Method `._key_play(key)`
  - Method `._key_title(key)`
  - Method `._key_dialogue(key)`
  - Method `._key_shop(key)`
  - Method `._key_inventory(key)`
  - Method `._key_help(key)`
  - Method `._key_pause(key)`
  - Method `._key_dead(key)`
  - Method `._render(env)`

---

### [`aldervale/hud.py`](aldervale/hud.py)
> *HUD and menu rendering: bars, minimap, dialogue, shop, inventory, titles.*

**Size**: `369` lines (`14570` bytes)

**Classes:**
- `class ItemStub`
  - Method `.__init__(item_id)`

**Functions:**
- `def wrap_text(text, width)`
- `def bar(screen, x, y, width, label, cur, mx, color, show_num)` - *An ASCII gauge: label, hashed fill and numeric readout.*
- `def draw_hud(screen, world, env, fps, show_map)`
- `def draw_minimap(screen, world)` - *Coarse terrain map with entity markers, top-right.*
- `def project_marker(screen, world, cam, wx, wy, wz)` - *World position to screen cell; returns (col, row) or None.*
- `def draw_world_overlays(screen, world, cam)` - *Damage numbers and the interaction prompt, anchored in the world.*
- `def draw_dialogue(screen, world, dlg, page, choice_idx)` - *Bottom dialogue box with the current page and choices.*
- `def draw_shop(screen, world, mode, sel, message)`
- `def draw_inventory(screen, world, message)`
- `def draw_help(screen)`
- `def draw_title(screen, world, cam, env, menu_sel, has_save)`
- `def draw_death(screen, world)`
- `def draw_pause(screen, sel)`
- `def draw_victory(screen, world, t)`
- `def draw_hurt_vignette(screen, world)`

---

### [`aldervale/math3d.py`](aldervale/math3d.py)
> *Pure tuple-based 3D math for the sprite baker (bake-time only, not per-frame).*

**Size**: `73` lines (`1505` bytes)

**Functions:**
- `def add(a, b)`
- `def sub(a, b)`
- `def scale(v, s)`
- `def dot(a, b)`
- `def cross(a, b)`
- `def length(v)`
- `def normalize(v)`
- `def rot_y_matrix(a)`
- `def rot_x_matrix(a)`
- `def rot_z_matrix(a)`
- `def mat_vec(m, v)`
- `def mat_mul(a, b)`
- `def face_normal(p0, p1, p2)`

---

### [`aldervale/mesh.py`](aldervale/mesh.py)
> *Low-poly mesh construction and the mesh-to-ASCII sprite baker.*

**Size**: `363` lines (`13121` bytes)

**Classes:**
- `class Sprite` - *A baked char-cell image with per-cell packed RGB colour.*
  - Method `.__init__(chars, colors, glow)`
  - Method `.filled()`
- `class Mesh` - *Static geometry: vertices plus quad faces with colour and emissive flag.*
  - Method `.__init__(verts, faces)`
- `class MeshBuilder` - *Assembles transformed primitives into one Mesh.*
  - Method `.__init__()`
  - Method `.build()`
  - Method `._quad(p0, p1, p2, p3, color, emissive)`
  - Method `.quad(p0, p1, p2, p3, color, emissive)`
  - Method `._rot(ry, rx, rz, pivot)`
  - Method `.box(cx, cy, cz, sx, sy, sz, color, ry, rx, rz, pivot, emissive)` - *Axis-aligned box, optionally rotated about a pivot point.*
  - Method `.cone(cx, y0, cz, r, h, seg, color, ry, rx, rz, pivot, emissive)` - *Tapered tube from a base ring to a near-point apex ring.*
  - Method `.cylinder(cx, y0, cz, r, h, seg, color, axis, ry, rx, rz, pivot, emissive)`
  - Method `.sphere(cx, cy, cz, rx, ry, rz, seg, rings, color, emissive)`
  - Method `._tp(p, rp)`
  - Method `.merge(mesh, matrix, offset, pivot)` - *Append mesh, optionally transformed about pivot then translated.*

**Functions:**
- `def _raster_tri(chars, colors, zbuf, cw, ch, tri, color, lum, ramp, n_ramp)` - *Scanline-fill one projected triangle with z-test and ramp dithering.*
- `def bake_sprite(mesh, yaw, pitch, dist, f, aspect, canvas, light, ramp, crop)` - *Bake a mesh into a Sprite viewed from yaw/pitch at the given scale.*
- `def _outline(chars, colors, cw, ch)` - *Darken the silhouette edge so models read as shapes, not noise.*
- `def _crop_bounds(chars, cw, ch)` - *Bounding box (x0, y0, x1, y1) of non-space cells, or a 1x1 fallback.*
- `def _pack_grid(chars, colors, cw, ch, box)` - *Slice flat buffers into row-lists limited to the given crop box.*

---

### [`aldervale/models.py`](aldervale/models.py)
> *Every 3D model in the realm: actors, creatures, flora and architecture.*

**Size**: `685` lines (`28225` bytes)

**Functions:**
- `def C(r, g, b)`
- `def _dead_wrap(b, rx, dz)`
- `def knight(pose, palette)` - *An armoured warrior with sword and shield; pose drives limb angles.*
- `def _sword(pal, blade_len, blade_w, blade)`
- `def guard(pose)` - *A castle guard with spear and heraldic tabard.*
- `def wolf(pose)` - *A grey wolf; diagonal-gait legs and a lunge pose.*
- `def skeleton(pose, captain)` - *A rattling skeleton; the captain is larger, crowned and caped.*
- `def bandit(pose)` - *A hooded road-agent with a dagger.*
- `def villager(pose, variant, role)` - *Robed elder, smith or peasant; variant picks clothes and hair.*
- `def chicken(pose)` - *A village chicken with peck and walk poses.*
- `def wyvern(frame)` - *The wyvern circling the castle; two wing frames.*
- `def tree_oak(seed, sway)` - *A broad oak; seed varies canopy layout, sway animates it.*
- `def tree_pine(seed, sway)`
- `def tree_birch(seed, sway)`
- `def tree_dead(seed)`
- `def bush(seed)`
- `def rock(seed, big)`
- `def house(variant)` - *A timber-framed cottage; windows glow warm at night (emissive).*
- `def well()`
- `def fence()`
- `def cart()`
- `def anvil()`
- `def haystack()`
- `def campfire(frame)` - *A crackling fire; frame 0-3 wobbles the flame cones (emissive).*
- `def chest(opened)`
- `def shrine()`
- `def banner(frame)` - *A tower banner; two wave frames.*
- `def castle()` - *The showpiece: curtain walls, merlons, corner towers, keep and gate.*
- `def pickup(kind)` - *Ground loot: gold, potion, pelt, bone or the quest amulet.*

---

### [`aldervale/noise.py`](aldervale/noise.py)
> *Deterministic integer-hash value noise and fractal sums (no random module).*

**Size**: `45` lines (`1081` bytes)

**Functions:**
- `def hash2i(ix, iy, seed)`
- `def rand01(ix, iy, seed)`
- `def _smooth(t)`
- `def value_noise(x, y, seed)`
- `def fbm(x, y, seed, octaves, lacunarity, gain)`

---

### [`aldervale/render.py`](aldervale/render.py)
> *Scene renderer: animated sky, voxel-marched terrain and billboard sprites.*

**Size**: `420` lines (`15032` bytes)

**Classes:**
- `class Camera` - *View parameters plus precomputed per-column ray angles.*
  - Method `.__init__(w, h, x, z, y, yaw, pitch, dist)`
- `class Env` - *Per-frame atmosphere derived from the world clock.*
  - Method `.__init__(day_t, t)`

**Functions:**
- `def _clouds()`
- `def _mix(c1, c2, t)`
- `def render_scene(screen, world, cam, env)` - *Draw sky, terrain, entities and fireflies into the screen buffer.*
- `def _sky(screen, cam, env)`
- `def _disc(screen, cam, az, el, radius, color, chars_pair)`
- `def _clouds_draw(screen, cam, env)`
- `def _terrain(screen, ter, cam, env)`
- `def _entities(screen, world, cam, env)`
- `def _fireflies(screen, world, cam, env)`

---

### [`aldervale/rules.py`](aldervale/rules.py)
> *Pure RPG rules: items, stats, XP, damage and inventory (no side effects).*

**Size**: `102` lines (`3529` bytes)

**Classes:**
- `class ItemDef` - *An immutable item definition; instances live in ITEMS.*
- `class Inventory` - *Item counts plus the equipped weapon and armor ids.*
  - Method `.add(item_id, n)`
  - Method `.remove(item_id, n)`
  - Method `.count(item_id)`
  - Method `.weapon_atk()`
  - Method `.armor_dfn()`
  - Method `.total_atk(base_atk)`
  - Method `.total_dfn(base_dfn)`

**Functions:**
- `def _i(id_, name, kind, **kw)`
- `def xp_for_level(level)`
- `def damage_roll(atk, dfn, rng)` - *Attack power versus defence; never zero, mildly random.*

---

### [`aldervale/story.py`](aldervale/story.py)
> *Story data: the Chronicle's cast, dialogue and quest text as pure data.*

**Size**: `170` lines (`5755` bytes)

**Functions:**
- `def dialogue_for(name, quest_state)` - *Dialogue payload for a named speaker at the given quest state.*
- `def guard_dialogue(name)` - *Dialogue payload for a gate guard, carrying the twin's own name.*

---

### [`aldervale/term.py`](aldervale/term.py)
> *Terminal control: VT100 setup, polled key input and frame output.*

**Size**: `419` lines (`14941` bytes)

**Classes:**
- `class TerminalError` - *Raised when the terminal cannot render the game at all.*
- `class Terminal` - *Raw-mode ANSI terminal wrapper with polled held-key input.*
  - Method `.__init__(color, use_alt_screen)`
  - Method `.__enter__()`
  - Method `.__exit__(*exc)`
  - Method `.start()`
  - Method `._open_windows()`
  - Method `._init_win_input()`
  - Method `.close()`
  - Method `.size()`
  - Method `.take_mouse()` - *Drain queued mouse events: (kind, x, y, buttons, wheel).*
  - Method `.poll()` - *Return (pressed, held): new key tokens and currently held ones.*
  - Method `.write(text)`
  - Method `.flush()`
  - Method `.set_title(title)`
  - Method `.read_key()` - *Return one normalized key token or None; never blocks.*

**Functions:**
- `def _mouse_event(x, y, buttons, flags)` - *Normalize a Windows MOUSE_EVENT_RECORD into a game mouse token.*
- `def vk_token(vk, ch)` - *Map a Windows virtual-key code to a game key token, or None.*

---

### [`aldervale/terrain.py`](aldervale/terrain.py)
> *Procedural island heightfield with biome colours, baked light and water.*

**Size**: `264` lines (`9529` bytes)

**Classes:**
- `class Terrain` - *A square island world grid sampled at one unit per cell.*
  - Method `.__init__(seed, size, water, octaves, village, castle, camp)`
  - Method `._generate(octaves, half)`
  - Method `._stamp_disk(x, z, r)`
  - Method `._stamp_path(a, b)`
  - Method `._stamp_ring(cx, cz, r)`
  - Method `._paint(grass_mix, forest, gres)`
  - Method `.in_bounds(x, z)`
  - Method `.height(x, z)`
  - Method `.color(x, z)`
  - Method `.light(x, z)`
  - Method `.is_path(x, z)`
  - Method `.walkable(x, z)`
  - Method `.forest_at(x, z)`

**Functions:**
- `def _smooth(t)`
- `def _lerp_packed(c1, c2, t)`

---

### [`aldervale/world.py`](aldervale/world.py)
> *The world of Aldervale: generation, simulation, quests and persistence.*

**Size**: `672` lines (`28550` bytes)

**Classes:**
- `class World` - *Owns terrain, entities, the player, quests and the world clock.*
  - Method `.__init__(seed, atlas, day_length, terrain_size)`
  - Method `._next_eid()`
  - Method `._generate()`
  - Method `._walkable_near(x, z, radius)`
  - Method `._add(entity)`
  - Method `._spawn_village(vx, vz)`
  - Method `._spawn_castle(kx, kz)`
  - Method `._spawn_forest()`
  - Method `._spawn_camp(cx, cz)`
  - Method `.update(dt, env)` - *Advance the world clock, every actor and transient state.*
  - Method `.add_message(text, color)`
  - Method `.add_damage_number(x, z, y, text, color)`
  - Method `.resolve_player_swing()`
  - Method `.kill_actor(actor)`
  - Method `._add_drop(pickup)`
  - Method `._give_xp(amount)`
  - Method `.hit_player(dmg, attacker)`
  - Method `.shrine_pray()`
  - Method `.respawn_player()`
  - Method `.interact_target()` - *Nearest interactable entity in front of the player.*
  - Method `.npc_talk(npc)` - *Build the dialogue payload for an NPC based on quest state.*
  - Method `.npc_choice(action)`
  - Method `.pickup_item(pickup)`
  - Method `.open_chest(chest)`
  - Method `.buy(item_id)`
  - Method `.sell(item_id)`
  - Method `.quest_objective()`
  - Method `.save(path)` - *Persist world state atomically (temp file, fsync, replace).*
  - Method `.load(path, atlas, terrain_size)`

---

### [`tests/__init__.py`](tests/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`tests/test_aldervale.py`](tests/test_aldervale.py)
> *Unit tier: fast in-process checks for the pure engine core.*

**Size**: `412` lines (`14912` bytes)

**Classes:**
- `class FakeTerm`
  - Method `.__init__()`
  - Method `.write(s)`
  - Method `.flush()`
- `class TestNoise`
  - Method `.test_deterministic_and_bounded()`
  - Method `.test_fbm_smooth()`
- `class TestMath3d`
  - Method `.test_rot_y_maps_front()`
  - Method `.test_identity()`
  - Method `.test_face_normal_unit_and_direction()`
- `class TestScreen`
  - Method `.test_set_respects_bounds_and_depth()`
  - Method `.test_text_overrides_with_nearest_depth()`
  - Method `.test_box_draws_frame()`
  - Method `.test_blit_scales_and_occludes()`
  - Method `.test_flush_diff_second_frame_small()`
  - Method `.test_frame_text_rows()`
- `class TestMesh`
  - Method `.test_box_face_count()`
  - Method `.test_cone_and_sphere_face_counts()`
  - Method `.test_bake_sprite_chars_in_ramp()`
  - Method `.test_bake_yaw_frames_differ()`
  - Method `.test_emissive_glow_separate()`
- `class TestAtlas`
  - Method `.test_yaw_frame_wraparound()`
  - Method `.test_heights_registered()`
- `class TestRules`
  - Method `.test_damage_roll_bounds()`
  - Method `.test_damage_roll_defence_reduces()`
  - Method `.test_xp_curve_monotonic()`
  - Method `.test_inventory_ops()`
  - Method `.test_item_ordering_sensible()`
- `class TestHudHelpers`
  - Method `.test_wrap_text()`
  - Method `.test_eid_hash_stable()`
- `class TestCliValidation`
  - Method `._run(argv)`
  - Method `.test_bad_fps_refused()`
  - Method `.test_bad_width_refused()`
  - Method `.test_bad_demo_seconds_refused()`
- `class TestReviewRegressions` - *Regressions for defects found in the aldervale code review.*
  - Method `.test_pack_rgb_clamps_channels()`
  - Method `.test_water_fog_reaches_fog_colour()`
  - Method `.test_terminal_min_width_clamped()`
  - Method `.test_terminal_uses_large_viewport()`
- `class TestStoryData` - *The story module is the single source of narrative truth.*
  - Method `.test_cast_entries_are_complete()`
  - Method `.test_gate_guards_are_the_twins()`
  - Method `.test_dialogue_for_every_villager()`
  - Method `.test_elder_dialogue_covers_quest_states()`
  - Method `.test_quest_objectives_cover_states()`
  - Method `.test_guard_dialogue_carries_twin_name()`
  - Method `.test_player_name_single_source()`
- `class TestMouseAndOutline` - *Mouse event normalization and sprite silhouette outlines.*
  - Method `.test_mouse_event_normalization()`
  - Method `.test_bake_sprite_has_silhouette_outline()`
  - Method `.test_bake_flat_face_is_one_glyph()`

---

### [`tests/test_integration.py`](tests/test_integration.py)
> *Integration tier: world generation, quest chain, rendering and the CLI.*

**Size**: `692` lines (`23500` bytes)

**Classes:**
- `class TestTerrain`
  - Method `.test_deterministic()`
  - Method `.test_village_flattened_and_walkable()`
  - Method `.test_island_has_sea_at_corners()`
  - Method `.test_path_exists_between_village_and_castle()`
- `class _FakeWorld`
- `class TestRenderScene`
  - Method `.setUpClass()`
  - Method `._world_with_entities()`
  - Method `.test_scene_fills_screen_with_sky_on_top()`
  - Method `.test_night_darkens_and_lights_fireflies()`
  - Method `.test_entities_occluded_behind_terrain_depth()`
- `class TestWorldSim`
  - Method `._world()`
  - Method `.test_deterministic_generation()`
  - Method `.test_spawns_present()`
  - Method `.test_full_quest_chain()`
  - Method `.test_save_load_roundtrip()`
  - Method `.get_temp_dir()`
  - Method `.test_interact_and_shrine()`
  - Method `.test_chest_loot()`
- `class TestGameShell`
  - Method `.setUpClass()`
  - Method `._render_once()`
  - Method `.test_movement_changes_position()`
  - Method `.test_attack_kills_wounded_wolf()`
  - Method `.test_state_transitions()`
  - Method `.test_potion_use_heals()`
  - Method `.test_render_frame_smoke()`
  - Method `.test_save_and_load_via_game()`
- `class TestCliSubprocess`
  - Method `._run(*args)`
  - Method `.test_version()`
  - Method `.test_unknown_flag_is_misuse()`
  - Method `.test_headless_demo()`
  - Method `.test_screenshot_writes_frame()`
- `class TestReviewFixes` - *Regressions for defects found in the aldervale code review.*
  - Method `._world()`
  - Method `.test_gold_pickups_collected_same_frame()`
  - Method `.test_hud_bars_do_not_overlap()`
  - Method `.test_death_transitions_to_dead_state()`
  - Method `.test_gate_guards_spawn_as_twins()`
  - Method `.test_npc_talk_delegates_to_story()`
- `class TestLaunchers` - *The one-click run buttons: PLAY.bat, run.sh and the VS Code config.*
  - Method `.test_play_bat_version_fastpath()`
  - Method `.test_run_sh_targets_module()`
  - Method `.test_play_bat_wt_directory_has_no_trailing_backslash()`
  - Method `.test_vscode_launch_configs()`
- `class TestHeldControls` - *Movement must respond to held keys polled every frame.*
  - Method `.setUpClass()`
  - Method `._tick(held, n)`
  - Method `.test_w_moves_player_forward()`
  - Method `.test_arrow_up_moves_and_left_turns()`
  - Method `.test_a_d_strafe()`
  - Method `.test_shift_sprints()`
  - Method `.test_space_press_attacks()`
- `class FakePollTerm`
  - Method `.__init__()`
  - Method `.queue_press(keys)`
  - Method `.queue_mouse(events)`
  - Method `.poll()`
  - Method `.take_mouse()`
  - Method `.write(text)`
  - Method `.flush()`
  - Method `.size()`
- `class TestMouse` - *Mouse orbit, zoom, pick, walk-to and click-to-attack.*
  - Method `._game()`
  - Method `.test_right_drag_orbits_and_tilts()`
  - Method `.test_wheel_zooms()`
  - Method `.test_pick_rejects_sky()`
  - Method `.test_click_sets_walk_target()`
  - Method `.test_walk_target_carries_player()`
  - Method `.test_click_near_enemy_attacks()`
- `class TestTitleFlow` - *Starting a new game from the title screen through the poll path.*
  - Method `.test_new_game_starts_from_title()`
  - Method `.test_continue_without_save_starts_world()`

**Functions:**
- `def _tiny_atlas()`
- `def _rmtree(d)`

---

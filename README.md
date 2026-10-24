# aldervale

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/Aegean-E/AIKit)

ALDERVALE - a 2.5D medieval RPG rendered entirely in tiny ASCII cells. Low-poly
3D models (knights, wolves, a walled castle) are baked into shaded character
sprites, marched over a voxel heightfield with fog, day/night light and water,
and composited with a full RPG on top: quests, combat, loot, shops, saves.
Standard library only; no dependencies, no assets, no build step.

## 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10 or newer (standard library only) and a
  dark-theme terminal that supports 24-bit colour (Windows Terminal, Terminal.app
  or any modern xterm). PLAY.bat opens a dedicated maximized Windows Terminal
  window, and the renderer scales with the window up to 260x110 cells - a bigger
  window or a smaller font (Ctrl+Minus) buys more detail, and at tiny glyphs the
  screen reads as pixel art.
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover
  ```
- **Run something now** (under 10 seconds):
  ```bash
  PLAY.bat    # Windows: double-click it in Explorer - one click, no typing
  ./run.sh    # macOS and Linux
  python -m aldervale --demo 9      # hands-free attract mode
  python -m aldervale --screenshot vista.txt && type vista.txt
  python -m aldervale               # play (WASD, SPACE, E, I, H)
  ```

  In VS Code, open the project folder and press F5 (or the Run button) -
  `ALDERVALE: Play` and `ALDERVALE: Demo` configurations are included.

### AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status aldervale` |
| Phase 4: every gate | `python aikit.py check aldervale` |
| Repair memory and map, then check | `python aikit.py fix aldervale` |
| Resume an interrupted task | `python aikit.py resume aldervale` |

## The Tale

The Suncrest Amulet, hearth-stone of the vale, was stolen by the Bone Captain
and now squats in the old camp beyond the eastern woods. Elder Quill waits by
the village shrine; Bram hammers steel at his forge; wolves and worse patrol
the trees. Slay the Captain, bring the amulet home, and Aldervale will call
you hero. Full cycle: talk, accept, fight, loot, equip, buy, return, victory.

That is the tale the villagers tell. The true canon - the First Fire, the
eleven Keepers, the Captain's grief, the wyvern's vigil, and where the saga
goes next - is written in **LORE.md**, the Chronicle of the vale. Every story
change to the game builds on it, and **ADAPTATION.md** maps every canon
element to the exact file that owns it.

## Controls

| Key | Action |
|---|---|
| W S or Up Down | walk forward / back |
| A D | sidestep left / right |
| Left / Right | turn the camera |
| Right-drag mouse | orbit and tilt the camera (full 3D look) |
| Left-click | walk to a point; talk to what you reach; attack a foe in reach |
| Mouse wheel | zoom the camera |
| Hold Shift | sprint (drains stamina) |
| SPACE | swing your sword |
| E or Enter | talk / open chest / pick up / pray at shrine |
| I | inventory (U use potion, E equip best) |
| M | toggle minimap |
| H or F1 | help |
| + / - | zoom the camera (keys) |
| ESC | pause (save & quit from there) |

## Command Line

```text
python -m aldervale [--seed N] [--width W] [--height H] [--fps N]
                    [--demo [SECS]] [--benchmark] [--no-color]
                    [--screenshot PATH] [--save PATH] [--version]
```

`--demo` runs a non-interactive attract mode (also works piped, for CI);
`--benchmark` renders 60 headless frames and reports timing (~14 ms/frame at
132x60 on a 2026 laptop); `--screenshot` writes one plain-text vista frame.
Exit codes: 0 success, 1 failure (What/Why/Fix on stderr), 2 misuse.

## What's Inside

```text
aldervale/
├── PLAY.bat            <- one-click launch on Windows (prefers Windows Terminal)
├── run.sh              <- one-command launch on macOS and Linux
├── .vscode/
│   └── launch.json     <- F5 / Run button configurations for VS Code
├── aldervale/
│   ├── __init__.py       <- package marker and version
│   ├── __main__.py     <- CLI: demo, benchmark, screenshot, error triads
│   ├── term.py         <- VT100 terminal control, non-blocking key input
│   ├── buffer.py       <- char-cell screen: colour, depth, diff flush
│   ├── math3d.py       <- vector/matrix helpers for the sprite baker
│   ├── noise.py        <- deterministic integer-hash value noise
│   ├── terrain.py      <- island heightfield, biomes, paths, light
│   ├── mesh.py         <- box/cone/cylinder/sphere builder + ASCII baker
│   ├── models.py       <- knight, wolf, skeleton, castle, trees, houses...
│   ├── atlas.py        <- bakes every (model, pose, yaw) into sprites
│   ├── render.py       <- sky, sun, clouds, voxel terrain, billboards
│   ├── entities.py     <- actors, props, pickups, AI state machines
│   ├── rules.py        <- items, damage, XP, inventory (pure functions)
│   ├── story.py        <- the Chronicle as data: cast, dialogue, quests
│   ├── world.py        <- generation, quests, dialogue, shops, saves
│   ├── hud.py          <- bars, minimap, menus, dialogue, title art
│   └── game.py         <- game states, camera, main loop, demo autopilot
├── tests/
│   ├── __init__.py          <- test package marker
│   ├── test_aldervale.py    <- unit tier: pure engine core (fast)
│   └── test_integration.py  <- world gen, quest chain, rendering, CLI
├── LORE.md             <- the canon: world, history, characters, open threads
├── ADAPTATION.md       <- canon to code: where story changes go and why
├── .aikit/             <- this project's memory: record, ledger, decisions
├── .gitignore
└── README.md
```

(`saves/` appears next to the executable once you save a game; it is
gitignored.)

## Technical Notes

- The renderer is a 2.5D composite: a per-column ray-march over the height
  grid (front-to-back with a hidden-row buffer) draws terrain, water and fog;
  entities are depth-tested billboards chosen from 20 yaw-baked frames per
  pose, baked at high cell density with silhouette outlines and flat-lit
  faces so they read as solid models rather than noise; emissive faces (fire,
  crystals, windows) bloom at night. The camera orbits and tilts freely, and
  clicking the world walks there by reading the depth buffer.
- Frames are emitted as foreground-only truecolor runs of changed cells, so
  HUD rows cost nothing and full-motion frames stay small.
- Everything is deterministic from `--seed`: terrain, village layout, spawns,
  and the rng behind combat rolls.

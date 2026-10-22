# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

Entry format: a `### ADR-NNN: <decision>` heading followed by Date, Status,
Context, Decision and Consequences lines.

### ADR-001: Pure-stdlib software 3D renderer instead of curses or external engines
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: The brief demands "almost real models" at ASCII density with zero setup friction; curses lacks 24-bit colour control and any pip dependency breaks portability.
- **Decision**: Low-poly meshes are baked at load into char-cell sprites (perspective projection, backface culling, Lambert shading onto a 12-glyph ramp, z-buffered scanlines with deterministic dither), then composited over a column-raymarched voxel heightfield with per-cell depth, all through VT100/truecolor escapes on a diff-flushing Screen buffer.
- **Consequences**: Boot pays ~3 s of baking and the hot loop is hand-tuned Python (~14 ms/frame at 132x60); in exchange the game runs on a bare Python 3.10+ install on Windows, macOS and Linux with no dependencies and pixel-like shaded output.

### ADR-002: Billboard sprites from 16 yaw frames (2.5D composition)
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: True per-frame 3D rasterisation of every entity is too slow in pure Python at playable frame rates.
- **Decision**: Every model is baked at 16 yaw steps per pose into sprite frames; the renderer picks the frame from (entity yaw - camera yaw) and scales it with depth-tested blits, far-to-near, with fog and day/night tinting; emissive faces are baked into separate glow sprites drawn at night.
- **Consequences**: Rotation snaps in 22.5-degree steps (imperceptible at game scale) and sprites upscale when very close; the whole scene stays within one depth-consistent painter's algorithm.

### ADR-003: Deterministic seeded world with entity-id save deltas
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: Saves must survive version changes to the world generator and stay tiny, and tests need reproducible worlds.
- **Decision**: The world (terrain, village, castle, camp, spawns) is rebuilt from a single integer seed; the save file stores only player state, quest state, clock and the sets of killed/collected/opened entity ids, written atomically (temp + fsync + os.replace).
- **Consequences**: Save files stay under a few KB, but regenerating a save made with an older generator can shift unmodified entity positions; acceptable for a single-session RPG.

### ADR-004: Terminal colour model is foreground-only truecolor
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: Background-colour SGR doubles escape traffic and breaks on light terminal themes; the pixel-art look needs dense glyphs rather than filled blocks.
- **Decision**: Every cell carries one 24-bit foreground colour and a ramp glyph chosen by luminance; the sky is a dithered gradient, never a background fill; `--no-color` degrades to the plain ramp.
- **Consequences**: The game reads best on dark terminal themes (documented in the README) and frame emission stays under ~60 KB in the worst case.

### ADR-005: Console-event mouse input, free-look camera, silhouetted high-density sprites
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: Players asked for mouse control, a genuine 3D camera and models that read as solid shapes instead of dithered noise; the terminal already polls console input records for keys.
- **Decision**: Read MOUSE_EVENT records from the same console input queue (Quick Edit disabled) and expose `take_mouse()`; the camera gains a pitch axis (right-drag, clamped 0.12-0.62 rad) and click-to-walk uses the depth buffer for 3D picking; sprites bake at 36 cells/unit for actors across 20 yaw steps, flat-shaded (no dither) with a darkened silhouette outline pass.
- **Consequences**: Mouse works in Windows Terminal and conhost but not on POSIX terminals yet (keyboard fully covers every action); sprite baking costs ~3.4 s at boot; the glyph output reads as clean outlined models instead of speckle.


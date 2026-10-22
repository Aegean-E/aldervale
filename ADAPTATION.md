# Adapting the Chronicle to the Game

How the canon in LORE.md becomes running code. This is the bridge document:
when you want to change the story, this tells you exactly which file owns
the change and what must stay true.

## The One Rule

Story content has three homes, and each change belongs to exactly one:

| Change | File |
|---|---|
| What is true in the world (canon, history, names, future acts) | `LORE.md` |
| What the game says (dialogue, cast, quest text) | `aldervale/story.py` |
| What the game does (spawns, actions, rewards, states) | `aldervale/world.py` |

A story edit should never require touching simulation code, and a simulation
edit should never hard-code story text. `story.py` is pure data with two
lookup helpers; `world.py` reads it and never quotes the Chronicle inline.

## Story-Bearing Surfaces

Every place narrative lives in the engine:

| Surface | Owner | Notes |
|---|---|---|
| Cast names, titles, models | `story.CAST` | Single source; `entities.Player` and world spawns read it |
| Villager names | `story.VILLAGER_NAMES` | Derived from `CAST["villagers"]` |
| Dialogue payloads | `story.dialogue_for()`, `story.guard_dialogue()` | Consumed by `world.npc_talk()` |
| Quest tracker text | `story.QUEST_OBJECTIVES` | Consumed by `world.quest_objective()` |
| Quest actions and rewards | `world.npc_choice()` | Simulation: state changes, gold, XP |
| Spawn layout | `world._spawn_*` | Which canon figures exist and where |
| Item names and flavour | `rules.ITEMS` | Descs are canon-adjacent prose |
| Help, title, controls text | `hud.py` | Presentation strings |
| Persistent story state | `world.save()/load()` | `quest`, `kills`, `collected`, `opened_chests` |
| Visual canon | `models.py` + `atlas.py` | Sprites are the canon's appearance |

## Cast to Engine

| Canon figure | Engine identity |
|---|---|
| Ser Alaric, the Margin Knight | `CAST["player"]` -> `entities.Player`, model `knight` |
| Elder Quill | `CAST["elder"]`, `ai_kind="villager"`, model `elder`, by the shrine |
| Bram the Smith | `CAST["smith"]`, `ai_kind="villager"`, model `smith`, at the forge |
| Mira, Old Tam, Wren | `CAST["villagers"]`, models `peasant0..2`, wander the green |
| Ser Aldous and Ser Aldric | `CAST["guards"]`, `ai_kind="guard"`, model `guard`, at the castle gate |
| The Bone Captain (Ser Corvin) | `CAST["captain"]`, model `captain`, the First Camp rite-circle |
| Vesper, the Mourning Wyvern | `CAST["wyvern"]`, `ai_kind="wyvern"`, circles Aldercastle |
| Wolves | model `wolf`, forest spawn (canon: the vale's ordinary grief) |
| The Unsworn (bandits) | model `bandit`, road spawn (canon: Hollowmere's diaspora) |
| Restless bones | model `skeleton`, camp spawn (canon: the unfinished dead) |
| Kestrel of the Unsworn | Not yet spawned - Act II; add a `CAST` entry and a named `bandit`-model villager-style actor |

## Zones to Anchors

| Canon place | Engine anchor |
|---|---|
| The village green | `terrain.village` (fraction 0.50, 0.68) |
| Aldercastle and the Keep's Heart | `terrain.castle` (0.47, 0.22) |
| The First Camp ("old camp") | `terrain.camp` (0.80, 0.55); its campfire prop is the Dead Fire |
| The Emberwood | `terrain.forest_at()` mask, east of `W * 0.35` |
| The Margins | The fog at the render distance edge (`render.MAX_DIST`) |
| The Inkwell | The `well` prop on the green |
| The shrine (First Mark) | The `shrine` prop; respawn and healing live here |

## Authoring Dialogue

A payload is `{"name": str, "pages": [str, ...], "choices": [(label,
action), ...]}`. The game shows up to 3 wrapped lines per page; keep pages
under ~230 characters. Actions understood by `game._key_dialogue`:

- `close` - end the conversation
- `shop` - open Bram's forge screen
- `quest_accept`, `quest_complete` - wired in `world.npc_choice()`

To add a line for an existing speaker, edit `story.py` only. To add a new
speaker: add a `CAST` entry, spawn them in the appropriate `world._spawn_*`
method, and add their pages to `story.dialogue_for()`. New actions need a
handler in `world.npc_choice()` plus, if they change UI, `game._key_dialogue`.

## Extending the Quest Machine

Current states: `none -> active -> return -> done`, held in `world.quest`
and persisted in saves. `story.QUEST_OBJECTIVES` must cover every state.

For Act II and beyond, keep the single-string state (save compatibility)
and make each new act a state family: `act2_circlet`, `act2_lantern`, and
so on, each with an objective in `QUEST_OBJECTIVES` and transitions in
`npc_choice()`. The pattern that scales: one quest flag per open question,
one action per choice that answers it.

## Canon-Compliance Checklist

Before merging any story change:

- Names come from the page lexicon (mark, margin, quill, ember, ash,
  chronicle, strand, ledger, ink, vigil, draft, cutting, gutter).
- The change answers one question and opens two.
- The dead are not evil, only unfinished; villains are grief with a sword
  in it; the Grey is punctual, never cruel.
- No gods, no chosen ones. Alaric is a draft, not a destiny.
- The comfortable page may be true, never the whole truth.
- Lines drawn from LORE.md's Sayings, Songs and Liturgy sections are
  preferred over invented idiom.

## Known Deliberate Divergences

Simplifications in the current build, each a planned adaptation point:

| Divergence | Canon | Adaptation point |
|---|---|---|
| Bandits attack on sight | The Unsworn are cold by policy, not cruel | Act II quest 4 humanizes Kestrel's camp |
| The Captain never speaks | Corvin has one great question to ask | Add a pre-fight dialogue page when he is engaged |
| The wyvern is ambient only | Vesper judges warmth of intent | Act II quest 3: carried-flame trust mechanic |
| Night only buffs skeleton aggro | The unkept stone gutters after sundown broadly | Extend `Env.night` effects if desired |
| Victory text stops at warmth | The deeper binding is the Act II hook | Post-victory elder dialogue already seeded |
| One village, one camp, one castle | Six other hearths exist | Acts III+; new terrain seeds via `--seed` |

## Guard Tests

The suite pins the story layer so refactors cannot drift it silently:

- `tests/test_aldervale.py::TestStoryData` - cast completeness, twin names,
  dialogue coverage per quest state, single-source player name
- `tests/test_integration.py::test_gate_guards_spawn_as_twins` - the twins
  exist in the generated world and speak under their own names
- `tests/test_integration.py::test_full_quest_chain` - the entire
  accept/slay/return/complete arc, including rewards

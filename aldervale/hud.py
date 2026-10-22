"""HUD and menu rendering: bars, minimap, dialogue, shop, inventory, titles."""

import math

from .buffer import pack_rgb
from .rules import ITEMS, SHOP_STOCK, WEAPON_ORDER, ARMOR_ORDER, xp_for_level

WHITE = pack_rgb(216, 220, 228)
GOLD = pack_rgb(232, 196, 90)
RED = pack_rgb(226, 84, 74)
GREEN = pack_rgb(120, 220, 130)
BLUE = pack_rgb(120, 160, 230)
GREY = pack_rgb(140, 144, 156)
DIM = pack_rgb(96, 100, 112)
ORANGE = pack_rgb(240, 160, 90)
PURPLE = pack_rgb(190, 150, 230)

TITLE_LOGO = [
    r"  AAA  L   DDDD  EEEE  RRRR  VVVV  AAA  L   EEEE ",
    r" A   A L   D   D E    R   R V  V A   A L   E    ",
    r" AAAAA L   D   D EEE  RRRR  V  V AAAAA L   EEE  ",
    r" A   A L   D   D E    R  R  V  V A   A L   E    ",
    r" A   A LLL DDDD  EEEE R   R  V   A   A LLL EEEE ",
]

CONTROLS = [
    "W A S D      walk (hold Shift to sprint)",
    "Arrows / Q E orbit the camera",
    "+ -          zoom the camera",
    "SPACE        swing your sword",
    "E            talk / open / pick up / pray",
    "I            inventory      M  toggle map",
    "F1 or H      this help      ESC  pause menu",
]


def wrap_text(text, width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        lines.append(cur)
    return lines


def bar(screen, x, y, width, label, cur, mx, color, show_num=True):
    """An ASCII gauge: label, hashed fill and numeric readout."""
    cur = max(0, cur)
    filled = 0 if mx <= 0 else int(width * min(1.0, cur / mx) + 0.5)
    text = "%-9s|%s|%s" % (label, "#" * filled, "-" * (width - filled))
    if show_num:
        text += " %d/%d" % (cur, mx)
    screen.text(x, y, text, color)


def draw_hud(screen, world, env, fps, show_map=True):
    p = world.player
    w, h = screen.w, screen.h
    inv = p.inventory
    screen.text(1, h - 5, "%s  Lv%d" % (p.name, p.level), WHITE)
    screen.text(20, h - 5, "Gold %d" % inv.count("gold"), GOLD)
    weapon = ITEMS[inv.weapon]
    screen.text(32, h - 5, "%s (atk %d)" % (weapon.name, weapon.atk), GREY)
    if w >= 92:
        armor = ITEMS[inv.armor]
        screen.text(58, h - 5, "%s (def %d)" % (armor.name, armor.dfn), GREY)
    if w >= 110:
        phase = "Dawn" if env.warm > 0.4 and env.daylight > 0.3 else (
            "Day" if env.daylight > 0.5 else ("Dusk" if env.warm > 0.3
                                              else "Night"))
        screen.text(w - 22, h - 5, "%-6s %2d fps" % (phase, fps), DIM)
    bar(screen, 1, h - 4, 12, "HP", p.hp, p.max_hp,
        GREEN if p.hp > p.max_hp * 0.35 else RED)
    bar(screen, 32, h - 4, 10, "Stam", p.stamina, p.max_stamina, BLUE,
        show_num=False)
    bar(screen, 55, h - 4, 14, "XP", p.xp, xp_for_level(p.level), PURPLE,
        show_num=False)
    bar(screen, 82, h - 4, 6, "Pot", inv.count("potion"), 9, ORANGE,
        show_num=True)
    screen.text(1, h - 3, "Quest: " + world.quest_objective(), pack_rgb(222, 200, 140))
    if show_map:
        draw_minimap(screen, world)
    y = h - 7
    for text, color, age in world.messages[-4:]:
        fade = max(0.25, 1.0 - age / 8.0)
        screen.text(1, y, text[:w - 30], color if fade > 0.5 else DIM)
        y -= 1


def draw_minimap(screen, world):
    """Coarse terrain map with entity markers, top-right."""
    p = world.player
    mw, mh = 26, 12
    x0 = screen.w - mw - 2
    y0 = 1
    ter = world.terrain
    step = 4.6
    half_w = mw * step * 0.5
    half_h = mh * step * 0.5
    for my in range(mh):
        for mx in range(mw):
            wx = p.x - half_w + mx * step
            wz = p.z - half_h + my * step * 2.0
            if not ter.in_bounds(wx, wz):
                c = pack_rgb(18, 30, 48)
            else:
                gh = ter.height(wx, wz)
                c = ter.color(wx, wz)
                if gh <= ter.water:
                    c = pack_rgb(30, 60, 96)
                c = pack_rgb(((c >> 16) & 255) * 0.75,
                             ((c >> 8) & 255) * 0.75, (c & 255) * 0.75)
            screen.set(x0 + mx, y0 + my, ".", c, -2.0)
    kx, kz = ter.castle
    cx, cz = ter.camp
    vx, vz = ter.village
    for ex, ez, ch, col in ((kx, kz, "C", BLUE), (cx, cz, "X", RED),
                            (vx, vz, "V", GOLD)):
        mx = int((ex - p.x + half_w) / step)
        my = int((ez - p.z + half_h) / (step * 2.0))
        if 0 <= mx < mw and 0 <= my < mh:
            screen.set(x0 + mx, y0 + my, ch, col, -3.0)
    for e in world.entities:
        kind = getattr(e, "kind", None)
        if kind in ("wolf", "bandit", "skeleton", "captain"):
            ch = "x"
            col = RED
        elif kind == "villager":
            ch = "o"
            col = GOLD
        else:
            continue
        if math.hypot(e.x - p.x, e.z - p.z) > 80.0:
            continue
        mx = int((e.x - p.x + half_w) / step)
        my = int((e.z - p.z + half_h) / (step * 2.0))
        if 0 <= mx < mw and 0 <= my < mh:
            screen.set(x0 + mx, y0 + my, ch, col, -3.0)
    mx = int(half_w / step)
    my = int(half_h / (step * 2.0))
    screen.set(x0 + mx, y0 + my, "@", WHITE, -4.0)
    screen.box(x0 - 1, y0 - 1, mw + 2, mh + 2, GREY)


def project_marker(screen, world, cam, wx, wy, wz):
    """World position to screen cell; returns (col, row) or None."""
    dx = wx - cam.x
    dz = wz - cam.z
    sin_y = math.sin(cam.yaw)
    cos_y = math.cos(cam.yaw)
    depth = dx * sin_y + dz * cos_y
    if depth < 0.7:
        return None
    side = dx * cos_y - dz * sin_y
    col = int(cam.w * 0.5 + side / depth * cam.f)
    row = int(cam.horizon - (wy - cam.y) / depth * cam.fy)
    if 0 <= col < screen.w and 0 <= row < screen.h:
        return col, row
    return None


def draw_world_overlays(screen, world, cam):
    """Damage numbers and the interaction prompt, anchored in the world."""
    for d in world.damage_numbers:
        pos = project_marker(screen, world, cam, d["x"], d["y"] + d["t"] * 0.4,
                             d["z"])
        if pos:
            alpha = 1.0 - d["t"]
            screen.text(pos[0] - len(d["text"]) // 2, pos[1], d["text"],
                        d["color"] if alpha > 0.4 else DIM)
    target = world.interact_target()
    if target is not None and not world.player.dead:
        if target.model == "shrine":
            label = "[E] Pray at the shrine"
        elif hasattr(target, "item_id"):
            item = ITEMS.get(target.item_id, ItemStub(target.item_id))
            label = "[E] Take " + item.name
        elif getattr(target, "ai_kind", "") in ("villager", "guard"):
            label = "[E] Talk to " + (target.name or "villager")
        elif hasattr(target, "opened"):
            label = "[E] Open the chest"
        else:
            label = "[E] Interact"
        wy = target.ground_y + target.height * target.scale + 0.5
        pos = project_marker(screen, world, cam, target.x, wy, target.z)
        if pos:
            screen.text(pos[0] - len(label) // 2, max(0, pos[1] - 1), label,
                        WHITE)


class ItemStub:
    def __init__(self, item_id):
        self.name = item_id.replace("_", " ").title()


def draw_dialogue(screen, world, dlg, page, choice_idx):
    """Bottom dialogue box with the current page and choices."""
    w, h = screen.w, screen.h
    bw = min(74, w - 4)
    bx = (w - bw) // 2
    by = h - 20
    bh = 9 + len(dlg["choices"])
    screen.box(bx, by, bw, bh, GREY, fill=" ")
    screen.text(bx + 2, by + 1, dlg["name"] + " says:", GOLD)
    text = dlg["pages"][page]
    for i, line in enumerate(wrap_text(text, bw - 5)[:3]):
        screen.text(bx + 2, by + 3 + i, line, WHITE)
    if page < len(dlg["pages"]) - 1:
        screen.text(bx + bw - 14, by + bh - 2, "[SPACE] more", DIM)
    else:
        cy = by + 7
        for i, (label, _action) in enumerate(dlg["choices"]):
            marker = ">" if i == choice_idx else " "
            screen.text(bx + 3, cy + i, "%s[%d] %s" % (marker, i + 1, label),
                        WHITE if i == choice_idx else GREY)


def draw_shop(screen, world, mode, sel, message):
    w, h = screen.w, screen.h
    screen.box(4, 2, w - 8, h - 8, GREY, fill=" ")
    screen.text_centered(3, "BRAM'S FORGE", GOLD)
    screen.text(6, 5, "Your gold: %d" % world.player.inventory.count("gold"),
                GOLD)
    screen.text(6, 6, "[TAB] switch buy/sell   [SPACE] confirm   [ESC] leave",
                DIM)
    if message:
        screen.text(6, 7, message, WHITE)
    if mode == "buy":
        screen.text(6, 9, "-- Wares for sale --", WHITE)
        for i, item_id in enumerate(SHOP_STOCK):
            item = ITEMS[item_id]
            sel_mark = ">" if i == sel else " "
            stat = "atk %d" % item.atk if item.kind == "weapon" else \
                ("def %d" % item.dfn if item.kind == "armor" else
                 ("heals %d" % item.heal if item.kind == "potion" else ""))
            screen.text(8, 10 + i, "%s[%d] %-16s %-10s %4d gold  %s" %
                        (sel_mark, i + 1, item.name, stat, item.price,
                         item.desc[:34]), WHITE if i == sel else GREY)
    else:
        screen.text(6, 9, "-- Your goods (half price) --", WHITE)
        sellables = [(iid, n) for iid, n in
                     sorted(world.player.inventory.counts.items())
                     if iid != "amulet" and n > 0]
        if not sellables:
            screen.text(8, 10, "Nothing to sell.", GREY)
        for i, (iid, n) in enumerate(sellables[:12]):
            item = ITEMS.get(iid, ItemStub(iid))
            sel_mark = ">" if i == sel else " "
            screen.text(8, 10 + i, "%s[%d] %-16s x%d  -> %d gold" %
                        (sel_mark, i + 1, item.name, n,
                         max(1, item.price // 2)),
                        WHITE if i == sel else GREY)


def draw_inventory(screen, world, message):
    p = world.player
    inv = p.inventory
    w, h = screen.w, screen.h
    screen.box(4, 2, w - 8, h - 8, GREY, fill=" ")
    screen.text_centered(3, "SATCHEL OF SER ALARIC", GOLD)
    screen.text(6, 5, "Level %d   HP %d/%d   Atk %d (+%d)   Def %d (+%d)" %
                (p.level, p.hp, p.max_hp, p.atk, inv.weapon_atk(), p.dfn,
                 inv.armor_dfn()), WHITE)
    screen.text(6, 6, "Gold %d" % inv.count("gold"), GOLD)
    screen.text(6, 8, "Weapon: %s" % ITEMS[inv.weapon].name, WHITE)
    screen.text(6, 9, "Armor : %s" % ITEMS[inv.armor].name, WHITE)
    if message:
        screen.text(6, 11, message, GREEN)
    screen.text(6, 13, "-- Satchel --", WHITE)
    row = 14
    if not inv.counts:
        screen.text(8, row, "Empty but for crumbs.", GREY)
    for iid, n in sorted(inv.counts.items()):
        item = ITEMS.get(iid, ItemStub(iid))
        hint = "[U] use" if getattr(item, "kind", "") == "potion" else ""
        screen.text(8, row, "%-20s x%d  %s" % (item.name, n, hint), GREY)
        row += 1
    known_w = [wid for wid in WEAPON_ORDER if inv.count(wid)]
    known_a = [aid for aid in ARMOR_ORDER if inv.count(aid)]
    screen.text(6, row + 1, "[U] drink potion   [E] equip best gear (%d wpn,"
                " %d arm)" % (len(known_w), len(known_a)), DIM)
    screen.text(6, row + 2, "[I] or [ESC] close", DIM)


def draw_help(screen):
    w, h = screen.w, screen.h
    screen.box(6, 3, min(56, w - 12), 4 + len(CONTROLS) + 4, GREY, fill=" ")
    screen.text_centered(4, "HOW TO BE A HERO", GOLD)
    for i, line in enumerate(CONTROLS):
        screen.text(9, 6 + i, line, WHITE)
    screen.text(9, 7 + len(CONTROLS),
                "Talk to Elder Quill by the shrine to begin.", DIM)


def draw_title(screen, world, cam, env, menu_sel, has_save):
    render_note = "shrink your terminal font (Ctrl+Minus) for finest detail"
    for i, line in enumerate(TITLE_LOGO):
        screen.text_centered(6 + i, line, GOLD if i < 3 else ORANGE)
    screen.text_centered(12, "A tale of steel and starlight, told in ASCII",
                         WHITE)
    opts = ["[N]ew game", "[C]ontinue" if has_save else "[C]ontinue (no save)",
            "[H]elp", "[Q]uit"]
    y = 16
    for i, opt in enumerate(opts):
        marker = "> " if i == menu_sel else "  "
        screen.text_centered(y + i, marker + opt,
                             WHITE if i == menu_sel else GREY)
    screen.text_centered(screen.h - 8,
                         "WASD walk . SPACE attack . E talk . I bag . H help",
                         DIM)
    screen.text_centered(screen.h - 6, render_note, DIM)
    screen.text_centered(screen.h - 4, "ALDERVALE v1.0 - an AIKit project",
                         DIM)


def draw_death(screen, world):
    w = screen.w
    screen.box((w - 44) // 2, screen.h // 2 - 4, 44, 8, RED, fill=" ")
    screen.text_centered(screen.h // 2 - 2, "YOU HAVE FALLEN", RED)
    screen.text_centered(screen.h // 2, "The shrine light carries you home.",
                         WHITE)
    screen.text_centered(screen.h // 2 + 2, "press any key", GREY)


def draw_pause(screen, sel):
    w, h = screen.w, screen.h
    opts = ["[C]ontinue", "[S]ave and quit to title", "[H]elp",
            "[Q]uit without saving"]
    screen.box((w - 40) // 2, h // 2 - 5, 40, 4 + len(opts), GREY, fill=" ")
    screen.text_centered(h // 2 - 3, "- PAUSED -", WHITE)
    for i, opt in enumerate(opts):
        marker = "> " if i == sel else "  "
        screen.text_centered(h // 2 - 1 + i, marker + opt,
                             WHITE if i == sel else GREY)


def draw_victory(screen, world, t):
    if t > 9.0:
        return
    alpha = max(0.0, min(1.0, (9.0 - t) / 2.0))
    col = GOLD if alpha > 0.5 else DIM
    w = screen.w
    screen.box((w - 56) // 2, 5, 56, 9, col, fill=" ")
    screen.text_centered(7, "THE SUNCREST IS HOME", col)
    screen.text_centered(9, "Aldervale shines warm again.", WHITE)
    screen.text_centered(10, "Ser Alaric, hero of the vale!", WHITE)
    screen.text_centered(12, "The realm is yours to roam.", GREY)


def draw_hurt_vignette(screen, world):
    if world.player.hurt_t <= 0.0:
        return
    k = world.player.hurt_t / 0.4
    col = pack_rgb(200 * k + 30, 40, 40)
    w, h = screen.w, screen.h
    for x in range(w):
        screen.chars[0][x] = ":"
        screen.fg[0][x] = col
        screen.chars[1][x] = "."
        screen.fg[1][x] = col
        screen.chars[h - 1][x] = ":"
        screen.fg[h - 1][x] = col

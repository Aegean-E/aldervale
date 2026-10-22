"""Pure RPG rules: items, stats, XP, damage and inventory (no side effects)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ItemDef:
    """An immutable item definition; instances live in ITEMS."""

    id: str
    name: str
    kind: str
    atk: int = 0
    dfn: int = 0
    heal: int = 0
    price: int = 0
    color: int = 0xC8C8C8
    desc: str = ""


def _i(id_, name, kind, **kw):
    return ItemDef(id=id_, name=name, kind=kind, **kw)


ITEMS = {
    d.id: d for d in (
        _i("rusty_sword", "Rusty Sword", "weapon", atk=3, price=20,
           color=0x9A7650, desc="A pitted blade that has seen better decades."),
        _i("iron_sword", "Iron Sword", "weapon", atk=7, price=120,
           color=0xAEB4BE, desc="Honest castle-forged iron."),
        _i("steel_sword", "Steel Sword", "weapon", atk=12, price=320,
           color=0xD2D8E2, desc="Bram's best fold-work, keen and true."),
        _i("knights_blade", "Knight's Blade", "weapon", atk=19, price=800,
           color=0xE8E4D0, desc="A relic of the old royal guard."),
        _i("tunic", "Padded Tunic", "armor", dfn=1, price=10,
           color=0x8C7A54, desc="Quilted cloth, better than nothing."),
        _i("leather_armor", "Leather Armor", "armor", dfn=4, price=90,
           color=0x74522F, desc="Boiled hide plates."),
        _i("chain_mail", "Chain Mail", "armor", dfn=7, price=260,
           color=0x9AA2AC, desc="Riveted rings against tooth and iron."),
        _i("plate_armor", "Plate Armor", "armor", dfn=12, price=700,
           color=0xC6CBD4, desc="The smith's masterpiece."),
        _i("potion", "Healing Draught", "potion", heal=60, price=25,
           color=0xD43E4A, desc="Bitter crimson, restores 60 health."),
        _i("pelt", "Wolf Pelt", "loot", price=15, color=0x92766A,
           desc="Thick grey fur; Bram pays for these."),
        _i("bone", "Old Bone", "loot", price=4, color=0xE4E0D0,
           desc="Rattling relic of the restless dead."),
        _i("amulet", "Suncrest Amulet", "quest", price=0, color=0xFFD269,
           desc="The hearth-stone of Aldervale, warm to the touch."),
    )
}

SHOP_STOCK = ("iron_sword", "steel_sword", "knights_blade", "leather_armor",
              "chain_mail", "plate_armor", "potion")

WEAPON_ORDER = ("rusty_sword", "iron_sword", "steel_sword", "knights_blade")
ARMOR_ORDER = ("tunic", "leather_armor", "chain_mail", "plate_armor")


def xp_for_level(level):
    return int(26 * level ** 1.45)


def damage_roll(atk, dfn, rng):
    """Attack power versus defence; never zero, mildly random."""
    base = atk * (0.85 + rng.random() * 0.32) - dfn * 0.55
    return max(1, int(base))


@dataclass
class Inventory:
    """Item counts plus the equipped weapon and armor ids."""

    counts: dict = field(default_factory=dict)
    weapon: str = "rusty_sword"
    armor: str = "tunic"

    def add(self, item_id, n=1):
        self.counts[item_id] = self.counts.get(item_id, 0) + n

    def remove(self, item_id, n=1):
        have = self.counts.get(item_id, 0)
        if have <= n:
            self.counts.pop(item_id, None)
        else:
            self.counts[item_id] = have - n

    def count(self, item_id):
        return self.counts.get(item_id, 0)

    def weapon_atk(self):
        return ITEMS[self.weapon].atk

    def armor_dfn(self):
        return ITEMS[self.armor].dfn

    def total_atk(self, base_atk):
        return base_atk + self.weapon_atk()

    def total_dfn(self, base_dfn):
        return base_dfn + self.armor_dfn()

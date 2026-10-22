"""Story data: the Chronicle's cast, dialogue and quest text as pure data.

All narrative content lives in this module so story changes never touch
simulation code. LORE.md is the canon; this file is its game-facing
translation. The world reads it through dialogue_for(), guard_dialogue()
and QUEST_OBJECTIVES and never hard-codes story text of its own.
"""

CAST = {
    "player": {
        "name": "Ser Alaric",
        "title": "the Margin Knight",
        "model": "knight",
    },
    "elder": {
        "name": "Elder Quill",
        "title": "Keeper-presumpt of Aldervale",
        "model": "elder",
        "home": "by the shrine, north-west of the well",
    },
    "smith": {
        "name": "Bram the Smith",
        "title": "forger of the Keeper's circlet",
        "model": "smith",
        "home": "at the village forge, east of the green",
    },
    "villagers": (
        {"name": "Mira of the Mill", "title": "watches horizons",
         "model": "peasant0"},
        {"name": "Old Tam", "title": "older than he admits",
         "model": "peasant1"},
        {"name": "Wren the Herder", "title": "right about the wyvern",
         "model": "peasant2"},
    ),
    "guards": (
        {"name": "Ser Aldous", "title": "twin of the gate",
         "model": "guard"},
        {"name": "Ser Aldric", "title": "twin of the gate",
         "model": "guard"},
    ),
    "captain": {
        "name": "The Bone Captain",
        "title": "Ser Corvin the Ashen, Champion of the Keep",
        "model": "captain",
        "home": "the rite-circle at the First Camp",
    },
    "wyvern": {
        "name": "Vesper",
        "title": "the Mourning Wyvern of Hollowmere",
        "model": "wyvern",
        "home": "circling Aldercastle",
    },
}

VILLAGER_NAMES = tuple(v["name"] for v in CAST["villagers"])

_ELDER_DIALOGUES = {
    "none": {
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
    },
    "active": {
        "name": "Elder Quill",
        "pages": [
            "'The Captain's camp lies east, past the wolves. Keep "
            "your blade sharp and your blood in.'",
        ],
        "choices": [("Farewell", "close")],
    },
    "return": {
        "name": "Elder Quill",
        "pages": [
            "The elder's eyes shine as you hold up the Suncrest "
            "Amulet. 'Blessed be this day!'",
            "'Aldervale owes you a hero's debt. Take this gold, and "
            "our gratitude, forever.'",
        ],
        "choices": [("Return the amulet.", "quest_complete")],
    },
    "done": {
        "name": "Elder Quill",
        "pages": ["'The vale is warm again, thanks to you. Rest, hero of "
                  "Aldervale.'"],
        "choices": [("Farewell", "close")],
    },
}

_SMITH_DIALOGUE = {
    "name": "Bram the Smith",
    "pages": [
        "Bram wipes soot from his brow. 'Steel keeps the vale "
        "standing, ser. Buy something before the dead do.'",
    ],
    "choices": [("Browse wares", "shop"), ("Farewell", "close")],
}

_GUARD_DIALOGUE = {
    "name": "Gate Guard",
    "pages": [
        "'Halt! ...Ah, a villager. Mind the east road, ser. "
        "The old camp stirs at night.'",
        "'The Captain wears our lord's stolen crown. No blade "
        "here has the reach for him.'",
    ],
    "choices": [("Farewell", "close")],
}

_VILLAGER_DIALOGUES = {
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
}

_DEFAULT_VILLAGER_DIALOGUE = ["'Fine weather for the vale, ser.'"]

QUEST_OBJECTIVES = {
    "none": "Speak with Elder Quill in the village (north of the well)",
    "active": "Slay the Bone Captain at the old camp (east)",
    "return": "Return the Suncrest Amulet to Elder Quill",
    "done": "The vale is at peace - roam on",
}


def dialogue_for(name, quest_state):
    """Dialogue payload for a named speaker at the given quest state."""
    if name == "Elder Quill":
        base = _ELDER_DIALOGUES.get(quest_state, _ELDER_DIALOGUES["done"])
    elif name == "Bram the Smith":
        base = _SMITH_DIALOGUE
    elif name in _VILLAGER_DIALOGUES:
        return {"name": name, "pages": list(_VILLAGER_DIALOGUES[name]),
                "choices": [("Farewell", "close")]}
    else:
        return {"name": name, "pages": list(_DEFAULT_VILLAGER_DIALOGUE),
                "choices": [("Farewell", "close")]}
    payload = dict(base)
    payload["pages"] = list(base["pages"])
    payload["choices"] = list(base["choices"])
    return payload


def guard_dialogue(name):
    """Dialogue payload for a gate guard, carrying the twin's own name."""
    payload = dict(_GUARD_DIALOGUE)
    payload["pages"] = list(_GUARD_DIALOGUE["pages"])
    payload["choices"] = list(_GUARD_DIALOGUE["choices"])
    payload["name"] = name or "Gate Guard"
    return payload

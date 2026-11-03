"""
Builds src/data/fe1/fe1Weapons.ts: Shadow Dragon and the Blade of Light's weapons and staves, read from the cartridge's own item
arrays (scripts/fe1_rom.py), named from the Switch release's own text (scripts/fe1_names.py). Run:
    python scripts/build-fe1-items.py

Items: an array per field in the fixed bank, by item number (data-raw/fe1/README.md). What the fields do was read in the game's code:
the hit, damage and crit routines (15:$CBE5, $CC64, $CD16), effectiveness tripling Mt (the class lists at 15:$D937), the equip check
(6:$A35E: a personal lock names a character, else the unit's weapon level must reach the item's, and the item's type must be one its
class uses), the range flags (15:$D9C3), the Devil weapons ($CE12), the Falchion lifting the damage cap ($CCD4), and the staves'
handlers (15:$D156, by the effect number at 15:$D967).
Left out: the dragons' forms (records with names the game never shows in English and no stats) and everything that isn't a weapon or a
staff.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe1_rom as R  # noqa: E402
import fe1_names as N  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe1', 'fe1Weapons.ts')

# The equip check's item types (6:$A3D1: the first item number, + 1, past each) -> the weapon page's category.
TYPE_BOUNDS = 0xA3D1
CATEGORIES = ['Sword', 'Lance', 'Bow', 'Ballista', 'Axe', 'Dragonstone', 'Tome', 'Staff', 'Staff']
LEVIN, DEVIL_SWORD, DEVIL_AXE, FALCHION = 8, 9, 29, 10

# The effectiveness lists' classes -> the weapon page's targets (each list must be one of these sets, or a union of them). Classes 23
# and 24 are the dragons a Manakete becomes (6:$AE48): the Earthstone, Medeus's, gives 24, the other stones 23.
TARGETS = [
    ('fe1-dragons-wyverns', {23, 5}), ('flying', {3, 5}), ('cavalier', {1, 4}), ('armour', {2, 22}), ('cavaliers-only', {1}),
    ('fe11-dragons', {23}), ('fe1-medeus', {24}), ('fe11-ballistician', {13}),
]

# The staves' handlers (15:$D156, by the effect number at 15:$D967) -> what each does, in the app's words.
STAFF_EFFECTS = {
    1: 'Restores 10 HP to an adjacent ally.',
    2: 'Restores 20 HP to an adjacent ally.',
    3: 'Restores 60 HP to an adjacent ally.',
    7: 'Sends an adjacent ally to another tile.',
    8: "Restores an adjacent ally's weapon to its full uses (not a personal weapon, nor one of weapon level 11 or more).",
    9: 'Brings a fallen ally back to life.',
    10: 'Restores HP to every ally.',
    12: "Raises an adjacent ally's Res to 7.",
    13: "Makes an adjacent ally's weapon never break (its uses become 255).",
}


def type_of(i):
    """The equip check's type of an item (0-8), or None past the last."""
    for t in range(9):
        if i + 1 < R.u8(6, TYPE_BOUNDS + t):
            return t
    return None


def targets(classes):
    rest, out = set(classes), []
    for key, group in TARGETS:
        if group <= rest:
            out.append(key)
            rest -= group
    assert not rest, f'no target for classes {rest}'
    return out


def ranges(i):
    flags = R.u8(R.FIXED, 0xD9C3 + i)
    near, far = bool(flags & 2), bool(flags & 4)
    return '1-2' if near and far else '2' if far else '1'


def character_name(c):
    return N.name(R.string(R.FIXED, R.u16(R.FIXED, 0xDE2B + 2 * (c - 1))))


def class_name(c):
    """A class's full name (the Switch release's class pages), by its text number."""
    return N.class_info()[N.text_number(R.class_name_codes(c))]


def main():
    effects = R.read(R.FIXED, 0xD967, R.ITEMS)
    out, seen = [], {}
    for i in range(R.ITEMS):
        it = R.item(i)
        t = type_of(i)
        if t is None:
            continue
        name = N.name(it['name_codes'])
        if name is None:
            continue  # the dragons' forms: no English, no stats
        cat = CATEGORIES[t]
        if name in seen:
            # The second Magestone record (item 41): the same name, its own stats.
            name = f'{name} (item {i})'
        seen[name] = i
        rules = []
        level = it['level']
        if level & 0x80:
            rank = 'Prf'
            rules.append(f'{character_name(level & 0x7F)} only')
        else:
            rank = str(level)
        if i == LEVIN:
            rules.append("Generals can't use it")
        if i == LEVIN or cat == 'Tome':
            rules.append("Magic: its Hit is less the foe's Luck, and its damage is its Mt less the foe's Res (Str isn't added)")
        if i in (DEVIL_SWORD, DEVIL_AXE):
            rules.append('May turn on its wielder after a hit next to the foe: a (21 − Luck) in 100 chance')
        if i == FALCHION:
            rules.append('While your side holds it, damage is no longer held at 40')
        if it['uses'] == 0xFF:
            rules.append('Never breaks')
        w = {
            'id': name.lower().replace("'", '').replace(' ', '-').replace('(', '').replace(')', ''),
            'name': name, 'romId': i, 'category': cat, 'rank': rank, 'range': ranges(i),
            'uses': None if it['uses'] == 0xFF else it['uses'],
            'worth': None if it['price'] in (0, 0xFF) else it['price'] * 10,
            'effective': targets(R.effective_classes(it['effective'])), 'rules': rules,
        }
        if i == LEVIN:
            w['magic'] = True
        if cat == 'Staff':
            w['effect'] = STAFF_EFFECTS[effects[i]]
            if effects[i] in (1,) and R.u8(R.FIXED, 0xD9C3 + i) & 0x20:
                w['effect'] = 'Restores 10 HP to an ally at any distance.'
            w['range'] = 'Any' if R.u8(R.FIXED, 0xD9C3 + i) & 0x20 else '1'
            if effects[i] == 10:
                w['range'] = '-'
        else:
            w.update({'mt': it['mt'], 'hit': it['hit'], 'crit': it['crit'], 'wt': it['wt']})
        out.append(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe1-items.py from Shadow Dragon and the Blade of Light's own item arrays (the cartridge), named from",
        " * the Switch release's own text. Do not edit by hand.",
        ' */',
        'export const FE1_WEAPONS: ChapterWeapon[] = [',
    ]
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in out]
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(out), 'weapons and staves')


if __name__ == '__main__':
    main()

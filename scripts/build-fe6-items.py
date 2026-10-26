"""
Builds src/data/fe6/fe6Weapons.ts from The Binding Blade's own item table (the user's clean Japanese ROM, scripts/fe6_rom.py), with
the English names (and the staves' effect lines) from the FE6 Localization patch (scripts/fe6_names.py). Run:
    python scripts/build-fe6-items.py

Items: 32-byte records at 0x60B648 (data-raw/fe6/README.md). What each attribute bit and weapon effect does was read in the battle code
where noted there; the rest follows the items that carry them. Left out: the map's ballistae (attribute 0x80 on a bow: fixed to their
tile), items the patch leaves unnamed (unused: the Watch staff, a dragonstone, the drawbridge key) and anything that isn't a weapon,
staff or dragonstone.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe6_rom as rom  # noqa: E402
from fe6_names import class_names, item_names, patched, TEXT_POINTER, CHARS  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe6', 'fe6Weapons.ts')
CATEGORY = {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Staff', 5: 'Anima', 6: 'Light', 7: 'Dark', 0xB: 'Stone'}
STATS = ['hp', 'str', 'skl', 'spd', 'def', 'res', 'lck', 'mov', 'con']

# Attribute bits (u32 at +8).
MAGIC = 0x02
UNBREAKABLE = 0x08
BRAVE = 0x20          # strikes twice
MAGIC_SWORD = 0x40    # magic damage when used at range (the Light Brand)
NO_COUNTER = 0x80     # ballistae and the long-range tomes
REAVER = 0x100        # battle code 0x8025a90: reverses the triangle
LOCKS = {0x400: 'Manaketes only', 0x800: 'Roy only', 0x1000: 'Myrmidons and Swordmasters only', 0x2000: 'Zephiel only'}
# Weapon effects (+0x1F), from the battle code (0x8024e8c and on).
EFFECTS = {
    1: 'Poisons the target on a hit',
    2: 'Restores the HP of the damage it deals to its wielder',
    3: 'Leaves the target with 1 HP',
    4: "May hurt its wielder instead: a (21 − Luck)% chance",
}


def description(item_id):
    """The patch's description line for an item, as plain text."""
    import struct
    p = patched()
    table = struct.unpack_from('<I', p, TEXT_POINTER)[0] - 0x08000000
    out = []
    for v in rom.huffman(p, table, rom.item(item_id)['desc_id']):
        c = v if v < 0x100 else (v & 0xFF) << 8 | v >> 8
        out.append(' ' if c == 1 else CHARS.get(c, ''))
    return re.sub(r'\s+', ' ', ''.join(out)).strip()


def targets(classes, names):
    """An effectiveness list of class ids -> the app's targets."""
    named = {names.get(c, '') for c in classes}
    out = []
    if 'Peg Knight' in named:
        out.append('flying')
    elif any(n in named for n in ('Fire Dragon', 'Manakete', 'Divine Dragon')):
        out.append('wyvern' if 'Wyvern Rider' in named else 'dragon')
    if 'Cavalier' in named or 'Paladin' in named:
        out.append('horseback')
    if 'Knight' in named or 'General' in named:
        out.append('armour')
    return out


def rank(v):
    for need, letter in rom.RANKS:
        if v >= need:
            return letter
    return 'Prf'


def main():
    names = item_names()
    cls = class_names()
    weapons = []
    for i in range(1, 128):
        it = rom.item(i)
        category = CATEGORY.get(it['type'])
        name = names.get(i)
        if not category or not name or (category == 'Bow' and it['attributes'] & NO_COUNTER):
            continue
        a = it['attributes']
        lo, hi = it['range']
        rng = f'{lo}-Mag/2' if hi == 0 else str(lo) if lo == hi else f'{lo}-{hi}'
        stats = {}
        if it['stat_bonus']:
            raw = rom.R[rom.off(it['stat_bonus']):rom.off(it['stat_bonus']) + len(STATS)]
            stats = {k: (v - 256 if v > 127 else v) for k, v in zip(STATS, raw) if v}
        rules = []
        if a & BRAVE:
            rules.append('Strikes twice in a row')
        if a & MAGIC_SWORD:
            rules.append('Deals magic damage when it strikes from 2 tiles away')
        if a & NO_COUNTER:
            rules.append("Can't be countered")
        if a & REAVER:
            rules.append('Reverses the weapon triangle')
        if it['weapon_effect'] in EFFECTS:
            rules.append(EFFECTS[it['weapon_effect']])
        rules += [label for bit, label in LOCKS.items() if a & bit]
        w = {
            'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + ('' if name not in [x['name'] for x in weapons] else f'-{i}'),
            'name': name,
            'romId': i,
            'category': category,
            'rank': rank(it['rank']),
            'range': rng,
            'uses': None if (a & UNBREAKABLE or not it['uses']) else it['uses'],
            'worth': it['uses'] * it['cost'] or None,
            'effective': targets(rom.class_list(it['effective']), cls) if it['effective'] else [],
            'rules': rules,
            'stats': stats,
        }
        if category == 'Staff':
            w['effect'] = description(i)
        else:
            # Eclipse's Mt is a placeholder (255): its effect sets the damage.
            w.update({'mt': None if it['mt'] == 255 else it['mt'], 'hit': it['hit'], 'crit': it['crit'], 'wt': it['wt']})
        weapons.append(w)

    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe6-items.py from The Binding Blade's own item table (the ROM), with the FE6 Localization patch's",
        ' * English names. Do not edit by hand.',
        ' */',
        'export const FE6_WEAPONS: ChapterWeapon[] = [',
        *[f'  {json.dumps(w, ensure_ascii=False)},' for w in weapons],
        ']',
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(len(weapons), 'weapons')


if __name__ == '__main__':
    main()

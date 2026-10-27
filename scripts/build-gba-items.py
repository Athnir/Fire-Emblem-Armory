"""
Builds the weapon lists of The Blazing Blade and The Sacred Stones from each game's own item table (the user's (U) ROMs,
scripts/gba_rom.py):
  src/data/fe7/fe7Weapons.ts
  src/data/fe8/fe8Weapons.ts
Run:
    python scripts/build-gba-items.py

Items: 36-byte records (data-raw/fe7/README.md). The attribute bits and weapon effects were read in the battle code where noted
there (the reaver, brave, magic sword, Luna's ignored defence; the effects 1-5); the weapon locks follow the items that carry them.
Left out: the ballistae (attribute 0x80 on a bow: fixed to their tile), FE8's unused "Dummy" items, and anything that isn't a weapon,
staff, dragonstone or monster weapon.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gba_rom import rom  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data')
STATS = ['hp', 'str', 'skl', 'spd', 'def', 'res', 'lck', 'mov', 'con']
RANKS = [(251, 'S'), (181, 'A'), (121, 'B'), (71, 'C'), (31, 'D'), (1, 'E')]

# Attribute bits (u32 at +8), the same in both games.
MAGIC = 0x02
UNBREAKABLE = 0x08
BRAVE = 0x20            # strikes twice
MAGIC_SWORD = 0x40      # magic damage at range (Light Brand, Runesword, Wind Sword)
NO_COUNTER = 0x80       # ballistae and the long-range tomes
REAVER = 0x100          # reverses the triangle and doubles it (the triangle routine: FE7 0x0802A120, FE8 0x0802C76C)
NEGATE_DEFENCE = 0x20000  # the target's Def or Res counts as 0 (Luna; Flametongue, Wretched Air)
LOCKS = {
    'fe7': {0x400: 'Manaketes only', 0x1000: 'Myrmidons and Swordmasters only', 0x40000: 'Eliwood only', 0x80000: 'Hector only',
            0x100000: 'Lyn only', 0x200000: 'Athos only'},
    'fe8': {0x400: 'Monsters and Manaketes only', 0x1000: 'Myrmidons and Swordmasters only', 0x40000: 'Eirika only',
            0x80000: 'Ephraim only'},
}
# Weapon effects (+0x1F), from the battle code (FE7 0x08028F3A and on, FE8 0x0802AE1A and on).
EFFECTS = {
    1: 'Poisons the target on a hit',
    2: 'Restores the HP of the damage it deals to its wielder',
    3: "Deals half the target's current HP, rounded up",
    4: 'May hurt its wielder instead: a (31 − Luck)% chance',
    5: 'Petrifies the target on a hit',
}
# FE8: these deal ×2 against what they're effective on instead of ×3 (the attack routine, 0x0802AABC).
FE8_DOUBLE = {0x3E, 0x85, 0x87, 0x8E, 0x91, 0x92, 0x93, 0x94}
FE8_STONE = 0xB5  # the Stone tome: its attack is set to 0 (0x0802AB5E)


def category(g, it, name):
    t = it['type']
    if t == 0xB:
        return 'Stone' if 'stone' in name.lower() or g == 'fe7' else 'Monster'
    return {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Staff', 5: 'Anima', 6: 'Light', 7: 'Dark'}.get(t)


def targets(classes, names):
    """An effectiveness list of class ids -> the app's targets."""
    named = {names.get(c, '') for c in classes}
    out = []
    if any('Peg' in n or 'Falco' in n for n in named):
        out.append('flying')
    elif any(n in named for n in ('Fire Dragon', 'Manakete', 'Draco Zombie', 'Wyvern Rider', 'Wyvern Lord', 'Wyvern Knight')):
        out.append('wyvern' if any('Wyvern' in n for n in named) else 'dragon')
    if any(n in named for n in ('Cavalier', 'Paladin')):
        out.append('horseback')
    if any(n in named for n in ('Knight', 'General')):
        out.append('armour')
    if any(n in named for n in ('Revenant', 'Bonewalker', 'Mogall', 'Gorgon', 'Cyclops', 'Gargoyle')):
        out.append('monster')
    if any(n in named for n in ('Myrmidon', 'Swordmaster')):
        out.append('swordfighter')
    return out


def rank(v):
    for need, letter in RANKS:
        if v >= need:
            return letter
    return 'Prf'


def build(g):
    r = rom(g)
    names = r.item_names()
    cls = r.class_names()
    weapons = []
    for i in range(1, r.item_count()):
        it = r.item(i)
        name = names.get(i)
        if not name or name == 'Dummy':
            continue
        cat = category(g, it, name)
        a = it['attributes']
        if not cat or (cat == 'Bow' and a & NO_COUNTER) or not a & 0x05:
            # Not a weapon or a staff (0x01 weapon, 0x04 staff), or a ballista.
            continue
        lo, hi = it['range']
        rng = f'{lo}-Mag/2' if hi == 0 else 'Any' if hi == 0xF and lo == 0xF else str(lo) if lo == hi else f'{lo}-{hi}'
        stats = {}
        if it['stat_bonus']:
            o = r.off(it['stat_bonus'])
            stats = {k: (v - 256 if v > 127 else v) for k, v in zip(STATS, r.R[o:o + len(STATS)]) if v}
        rules = []
        if a & BRAVE:
            rules.append('Strikes twice in a row')
        if a & MAGIC_SWORD:
            rules.append('Deals magic damage when it strikes from 2 tiles away')
        if a & NO_COUNTER:
            rules.append("Can't be countered")
        if a & REAVER:
            rules.append('Reverses the weapon triangle and doubles it')
        if a & NEGATE_DEFENCE:
            rules.append("The target's Def or Res counts as 0")
        if it['weapon_effect'] in EFFECTS:
            rules.append(EFFECTS[it['weapon_effect']])
        if g == 'fe8' and i == FE8_STONE:
            rules.append('Deals no damage')
        rules += [label for bit, label in LOCKS[g].items() if a & bit]
        eff = r.class_list(it['effective']) if it['effective'] else []
        tg = targets(eff, cls)
        if 'Dark Druid' in {cls.get(c) for c in eff}:
            rules.append('Effective against Nergal (Dark Druid)')
        w = {
            'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + ('' if name not in [x['name'] for x in weapons] else f'-{i}'),
            'name': name if name not in [x['name'] for x in weapons] else f'{name} ({i})',
            'romId': i,
            'category': cat,
            'rank': rank(it['rank']),
            'range': rng,
            'uses': None if (a & UNBREAKABLE or not it['uses']) else it['uses'],
            'worth': it['uses'] * it['cost'] or None,
            'effective': tg,
            'rules': rules,
            'stats': stats,
            'exp': it['exp'],
        }
        if g == 'fe8' and i in FE8_DOUBLE and tg:
            w['effectiveMultiplier'] = 2
        if cat == 'Staff':
            # The description says what the staff does; a legendary one's (0x10, Latona) is flavour, so its use line instead.
            w['effect'] = r.text(it['use_id'] if a & 0x10 and it['use_id'] else it['desc_id'])
        else:
            # Eclipse's Mt is a placeholder (255): its effect sets the damage.
            w.update({'mt': None if it['mt'] == 255 else it['mt'], 'hit': it['hit'], 'crit': it['crit'], 'wt': it['wt']})
        weapons.append(w)
    return weapons


GAME_NAME = {'fe7': 'The Blazing Blade', 'fe8': 'The Sacred Stones'}


def main():
    for g in ('fe7', 'fe8'):
        weapons = build(g)
        const = g.upper() + '_WEAPONS'
        lines = [
            "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
            '',
            '/*',
            f" * GENERATED by scripts/build-gba-items.py from {GAME_NAME[g]}'s own item table (the ROM). Do not edit by hand.",
            ' */',
            f'export const {const}: ChapterWeapon[] = [',
            *[f'  {json.dumps(w, ensure_ascii=False)},' for w in weapons],
            ']',
        ]
        out = os.path.join(ROOT, g, f'{g}Weapons.ts')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print(g, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

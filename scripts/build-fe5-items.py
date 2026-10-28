"""
Builds src/data/fe5/fe5Weapons.ts: Thracia 776's weapons and staves, read from the game's own item table (the user's clean ROM,
scripts/fe5_rom.py), named from Lil' Manster (scripts/fe5_names.py). Run:
    python scripts/build-fe5-items.py

Items: 23-byte records at $B0:80AB (data-raw/fe5/README.md). What each field does was read in the battle code where noted there:
effectiveness triples Mt ($83:D347), the magic swords strike with their second type's magic at 2 range ($83:CF77 and on), the weapon
effects ($83:E0D5 and on), the price (uses x the per-use cost, + 200 for weapons and staves, $83:B00D).
Left out: the ballistae (fixed to their tile), the broken items, and anything that isn't a weapon or a staff. The staves' effects
aren't in the item records: they're Serenes Forest's (its Thracia 776 staves page), each row matched to the ROM's rank, uses and
price first, in the app's own words.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe5_names import character_names, generic_names, item_names  # noqa: E402
from fe5_rom import BALLISTA, BROKEN, STAFF, TYPES, UNBREAKABLE, WEAPON, R, item, lo, u16, u8  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe5', 'fe5Weapons.ts')
RANKS = {50: 'E', 100: 'D', 150: 'C', 200: 'B', 250: 'A'}
STATS = ['str', 'mag', 'skl', 'spd', 'def', 'con', 'lck', 'mov']
SKILLS2 = {0x01: 'Adept', 0x02: 'Charm', 0x08: 'Miracle', 0x10: 'Vantage', 0x20: 'Accost', 0x40: 'Pavise', 0x80: 'Nihil'}
SKILLS3 = {0x01: 'Wrath', 0x02: 'Astra', 0x04: 'Luna', 0x08: 'Sol', 0x10: 'Paragon'}
BRAVE = 0x40  # skills3: strikes twice
# Weapon effects (+0x12, an offset into the table at $83:E0xx), from their routines.
EFFECTS = {
    2: 'Poisons the target on a hit, but only when an enemy or another army wields it',
    4: 'May turn on its wielder: a (21 − Luck)% chance',
    6: 'Restores the HP of the damage it deals to its wielder',
    8: 'Petrifies the target on a hit',
    10: 'Leaves the target with 1 HP',
    12: 'Berserks the target on a hit, except on a throne or gate',
    14: 'Puts the target to sleep on a hit, except on a throne or gate',
}
# Class ids in an effectiveness list (bank $B0) -> the app's targets.
ARMOUR, CAVALIER, PEGASUS, DRACO = 0x1A, 0x01, 0x10, 0x12
# Serenes Forest's staves (name there, rank, uses, price) -> what the staff does, by Lil' Manster's name.
STAVES = {
    'Heal': ('Live', 'E', 20, 2200, 'Restores HP to an adjacent ally.'),
    'Mend': ('Relive', 'D', 15, 2300, 'Restores more HP to an adjacent ally than Heal.'),
    'Recover': ('Recover', 'C', 10, 2200, "Restores all of an adjacent ally's HP."),
    'Physic': ('Reblow', 'C', 5, 1700, 'Restores HP to an ally at a distance.'),
    'Fortify': ('Reserve', 'B', 3, 1700, 'Restores the HP of every ally.'),
    'Rescue': ('Rescue', 'B', 3, 2000, "Brings an ally to the user's side."),
    'Warp': ('Warp', 'A', 3, 2000, 'Sends an adjacent ally to any tile it can stand on.'),
    'Restore': ('Rest', 'C', 5, 3200, "Cures an ally's status, except stone."),
    'Silence': ('Silence', 'B', 3, 1400, 'Stops an enemy using magic and staves; not on a throne or gate.'),
    'Sleep': ('Sleep', 'C', 3, 1700, 'Puts an enemy to sleep; not on a throne or gate.'),
    'Torch': ('Torch', 'D', 5, 2200, "Lights 10 tiles around the user in fog, 1 fewer each turn."),
    'Return': ('Return', 'A', 3, None, 'Lets an ally escape the map (unused).'),
    'Hammerne': ('Repair', None, 5, None, "Repairs an ally's weapon or staff."),
    'Thief': ('Thief', None, 4, None, "Steals an enemy's weapon, staff or item."),
    'Watch': ('Watch', 'C', 4, 1800, 'Unused: meant to show what roofs hide.'),
    'Berserk': ('Berserk', 'A', 3, 2000, 'Berserks an enemy; not on a throne or gate.'),
    'Unlock': ('Unlock', None, 3, None, 'Opens a door or chest.'),
    'Ensorcel': ('M Up', 'C', 5, 2200, "Raises an ally's Magic by 7, 1 less each turn."),
    'Rewarp': ('Rewarp', 'A', 5, 1200, 'Sends the user to any tile it can stand on.'),
    'Kia': ('Kia', None, 5, None, "Cures an ally's stone status."),
}


def class_list(p):
    out, a = set(), 0xB00000 | p
    while (c := u8(a)):
        out.add(c)
        a += 1
    return out


def targets(p):
    cl = class_list(p)
    t = []
    if ARMOUR in cl:
        t.append('armour')
    if CAVALIER in cl:
        t.append('horseback')
    if PEGASUS in cl:
        t.append('flying')
    elif DRACO in cl:
        t.append('wyvern')
    return t


def lock(p, names):
    """A weapon lock ($B0 list of character ids, ended by 0): the named characters on it, and whether generic foes are too."""
    who, foes, a = [], False, 0xB00000 | p
    while (c := u16(a)):
        if names[c] in generic_names():
            foes = True
        else:
            who.append(names[c])
        a += 2
    return list(dict.fromkeys(who)), foes


def rng(r):
    lo_, hi = r
    return str(lo_) if lo_ == hi else f'{lo_}-{hi}'


def main():
    names = item_names()
    people = character_names()
    out, seen = [], {}
    for i in range(1, 0xA0):
        it = item(i)
        if not it['traits'] & (WEAPON | STAFF) or it['traits'] & (BROKEN | BALLISTA):
            continue
        name = names[i]
        if name in seen:
            # Forseti's second record: the same tome without uses.
            assert it['traits'] & UNBREAKABLE, name
            name = f'{name} (unbreakable)'
        seen[name] = i
        cat = TYPES[it['type']]
        rules, skills = [], []
        if it['rank'] in RANKS:
            rank = RANKS[it['rank']]
        else:
            who, foes = lock(it['rank'], people)
            rank = 'Prf'
            if who:
                rules.append(f"{' and '.join(who) if len(who) < 3 else ', '.join(who[:-1]) + ' and ' + who[-1]} only"
                             + (' (and some foes)' if foes else ''))
            else:
                rules.append('Foes only' if foes else 'No one is on its list of wielders')
        if it['skills3'] & BRAVE:
            rules.append('Strikes twice in a row')
        skills += [v for k, v in SKILLS2.items() if it['skills2'] & k]
        skills += [v for k, v in SKILLS3.items() if it['skills3'] & k]
        if it['traits'] & 0x02:
            rules.append(f"Strikes with {TYPES[it['alt_type']].lower()} magic from 2 tiles away: the wielder's Magic adds to its Mt, "
                         "and the target defends with its Magic")
        if it['weapon_effect'] in EFFECTS:
            rules.append(EFFECTS[it['weapon_effect']])
        if it['traits'] & UNBREAKABLE:
            rules.append('Never breaks')
        b = lo(0xB00000 | it['bonuses'])
        bonus = R[b:b + 8]
        stats = {STATS[k]: v for k, v in enumerate(bonus) if v}
        w = {
            'id': name.lower().replace("'", '').replace(' ', '-').replace('(', '').replace(')', '').replace('á', 'a').replace('ö', 'o'),
            'name': name, 'romId': i, 'category': cat, 'rank': rank, 'range': rng(it['range']),
            'uses': None if it['uses'] < 0 else it['uses'], 'worth': it['price'] or None,
            'effective': targets(it['effective']), 'rules': rules, 'stats': stats,
        }
        if skills:
            w['skills'] = skills
        if cat == 'Staff':
            sname, srank, suses, sprice, effect = STAVES[name]
            assert suses == it['uses'] and (srank is None or srank == rank) and (sprice is None or sprice == it['price']), (name, sname)
            w['effect'] = effect
        else:
            w.update({'mt': it['mt'] if it['mt'] >= 0 else None, 'hit': it['hit'], 'crit': it['crit'], 'wt': it['wt']})
        out.append(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe5-items.py from Thracia 776's own item table (the ROM), named from Lil' Manster. Do not edit by",
        ' * hand.',
        ' */',
        'export const FE5_WEAPONS: ChapterWeapon[] = [',
    ]
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in out]
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(out), 'weapons and staves')


if __name__ == '__main__':
    main()

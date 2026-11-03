"""
Builds src/data/fe3/fe3Weapons.ts: Mystery of the Emblem's weapons and staves, read from the game's own item table (the user's clean
ROM, scripts/fe3_rom.py), named from the translation patch (scripts/fe3_names.py). Run:
    python scripts/build-fe3-items.py

Items: 14-byte records at $88:A6E9 (data-raw/fe3/README.md). What the fields do was read in the game's code: the hit and avoid
($83:B400: a tome's type bit, or a staff's, leaves the target's terrain avoid out), the damage ($83:B4D7: Str + Mt, the Levin Sword's
Mt alone; $83:B52E: against Def, Res for a tome's type bit, and a breath's against nothing unless the target fights with a breath
too), effectiveness tripling Mt ($83:B380, the class lists at $88:A633; none against a unit holding Iote's Shield or the Lightsphere,
$83:B364 and the flags $83:C11F sets), the weapon level or personal lock ($83:EF20, the lock lists at $88:A48E) and the classes that
may use each item ($83:EEB4, the lists at $88:A4B1), what a weapon becomes at 0 uses ($83:C054), the sale price ($87:9540), and the
weapons the battle code treats by id ($83:B1A3 the Devil weapons, $83:B4B4 the Levin Sword, $83:C102 the EXP doublers, $83:B28D
Imhullu and Starlight, $83:B720 Dulam, $83:B8CD Resire, $83:B111 the Shadow Dragon against tomes, $83:B15E Dark Breath).
Dragonstones (the user's call): each stone is listed with the breath its dragon fights with ($93:D305 the stone's class, $83:849F;
$93:D2C4 the class's breath, $83:84AD) and what the change does ($83:CF72). The breaths aren't listed on their own, nor anything that
isn't a weapon, a staff, a ballista or a stone. The staves' amounts were read in their handlers ($83:C4F3 by item); the rest of what
each does, and their ranges, are Serenes Forest's (its Mystery of the Emblem staves page), each row matched to the ROM's level, uses
and price first, in the app's own words.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe3_rom as r  # noqa: E402
from fe3_names import character_names, class_names, item_names  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe3', 'fe3Weapons.ts')
CATEGORY = {'Sword': 'Sword', 'Lance': 'Lance', 'Axe': 'Axe', 'Bow': 'Bow', 'Tome': 'Tome', 'Staff': 'Staff', 'Ballista': 'Ballista'}
LEVIN, DEVIL_SWORD, DEVIL_AXE = 0x09, 0x05, 0x22
EXP_DOUBLERS = {0x0A, 0x17, 0x1D}
STARLIGHT, IMHULLU, DULAM, RESIRE = 0x36, 0x37, 0x38, 0x39
DARK_BREATH, ICE_BREATH, MIST_BREATH = 0x2B, 0x2A, 0x2C
# The dragonstones and the dragon each makes ($93:D305), and each dragon's breath ($93:D2C4): 7 entries each.
DRAGON_CLASSES, STONES, BREATHS = 0x83849F, 0x8384A6, 0x8384AD
CLASS_TABLE = 0x88906C  # 9 bytes a class: +3 its Mov

# Effectiveness lists -> the weapon page's targets (each list must be one of these sets, or a union of them).
ARMOUR = {7, 8}
HORSEBACK = {3, 4}
FLYING = {9, 10, 40}
DRAGONS = {16, 38, 39, 40, 41, 42, 43, 44}
TARGETS = [
    ('dragons-all', DRAGONS | {10}),                 # Falchion: every dragon, and Dragon Knights
    ('dragons-most', DRAGONS - {41, 42} | {10}),     # Wyrmslayer: not Earth or Shadow Dragons
    ('armour', ARMOUR), ('cavalier', HORSEBACK), ('flying', FLYING), ('icedragon', {38}), ('firedragon', {16}),
    ('brigand', {19, 29, 30, 31}), ('mercenary', {17, 18, 32}),
]
BROKEN_FROM = {'Broken Sword': 'sword', 'Broken Lance': 'lance', 'Broken Bow': 'bow', 'Broken Axe': 'axe'}

# Serenes Forest's staves (name there, weapon level or None for a lock, uses, price, range) -> what the staff does, by the patch's name.
STAVES = {
    'Heal': ('Live', 1, 20, 1000, '1', "Restores 10 HP plus its user's Str to an adjacent ally."),
    'Mend': ('Relive', 2, 16, 1600, '1', "Restores 20 HP plus its user's Str to an adjacent ally."),
    'Recover': ('Recover', 3, 12, 2400, '1', "Restores all of an adjacent ally's HP."),
    'Physic': ('Reblow', 7, 12, 2400, 'Any', 'Restores HP to an ally at a distance.'),
    'Fortify': ('Reserve', 8, 12, 9600, '-', "Restores 10 HP plus its user's Str to every ally."),
    'Warp': ('Warp', 5, 7, 14000, '1', 'Sends an adjacent ally to any tile it can stand on.'),
    'MagShield': ('M Shield', 8, 12, 9600, '1', "Raises an adjacent ally's Resistance by 7, 1 less each turn."),
    'Hammerne': ('Hammerne', None, 5, 50000, '1', "Repairs an adjacent ally's weapon to its full uses (not one with no price)."),
    'Silence': ('Silence', 10, 5, 10000, 'Any', 'Stops every unit, friend and foe, using tomes (Imhullu aside) and staves for a turn.'),
    'Rescue': ('Rescue', None, 5, 10000, 'Any', "Brings an ally to the user's side."),
    'Aum': ('Ohm', None, 1, 10000, '-', 'Brings a fallen ally back to life.'),
    'Aum (5 uses)': ('Ohm', None, 5, None, '-', 'Brings a fallen ally back to life.'),
    'Unlock': ('Unlock', 8, 5, 10000, '1-2', 'Opens a door.'),
    'Thief': ('Thief', None, 5, 10000, 'Any', 'Opens a chest at a distance.'),
    'Watch': ('Watch', 11, 5, 10000, 'Any', 'Shows what the roofs of buildings hide.'),
    'Again': ('Again', 20, 3, None, '-', 'Lets every ally that has already moved this turn move again.'),
}


def targets(classes):
    rest, out = set(classes), []
    for key, group in TARGETS:
        if group <= rest:
            out.append(key)
            rest -= group
    assert not rest, f'no target for classes {rest}'
    return out


def joined(names):
    names = list(dict.fromkeys(names))
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def plural(name):
    if name.endswith(' (F)'):
        return 'female ' + plural(name[:-4])
    if name.endswith('y'):
        return name[:-1] + 'ies'
    if name.endswith('s'):
        return name + 'es'
    return name + 's'


def sell_price(price):
    """What a shop pays at full uses ($87:9540): half the value of the uses left, in tens, rounded down (the price is kept in tens)."""
    return max(10, price // 20 * 10)


def stones():
    """{stone id: (the dragon class it makes, that dragon's breath)}."""
    return {r.u8(STONES + k): (r.u8(DRAGON_CLASSES + k), r.u8(BREATHS + k)) for k in range(7)}


def main():
    names, people, classes = item_names(), character_names(), class_names()
    out, seen = [], {}
    dragonstones = stones()
    # The classes a category's ordinary weapon (its iron one) may be used by: a weapon whose list is narrower says who.
    usual = {cat: set(r.users(i)) for i, cat in ((0x00, 'Sword'), (0x0F, 'Lance'), (0x1E, 'Axe'), (0x18, 'Bow'), (0x2D, 'Tome'),
                                                 (0x40, 'Staff'))}
    for i in range(r.ITEM_COUNT):
        it = r.item(i)
        cat = 'Dragonstone' if i in dragonstones else CATEGORY.get(it['type'])
        if not cat:
            continue
        name = names[i]
        assert name not in seen, name
        seen[name] = i
        stat_from = it
        rules = []
        if i in dragonstones:
            # The stone's own record holds no stats: its dragon fights with its class's breath.
            dragon, breath = dragonstones[i]
            stat_from = r.item(breath)
            a = 'an' if classes[dragon][0] in 'AEIOU' else 'a'
            rules.append(f"Turns a Manakete into {a} {classes[dragon]} for 5 turns plus a random 0 to half its Luck, its HP and max HP "
                         'doubled (held at 52)')
            if breath == MIST_BREATH:
                # A Divine Dragon fights with Ice Breath before chapter 21 ($93:D2DA).
                mist = r.item(MIST_BREATH)
                stat_from = r.item(ICE_BREATH)
                rules.append(f"Its dragon fights with Ice Breath in Book 1, and with Mist Breath in Book 2 (Mt {mist['mt']}, Hit "
                             f"{mist['hit']}, effective against every dragon and Dragon Knights)")
            else:
                rules.append(f'Its dragon fights with {names[breath]}')
            rules.append("A breath strikes past the foe's Def, unless the foe fights with a breath too")
            if breath == DARK_BREATH:
                rules.append('Dark Breath halves the attack of whoever fights its dragon')
        if it['lock'] is not None:
            rank = 'Prf'
            rules.append(f"{joined(people[c] for c in r.lock(it['lock']))} only")
        else:
            rank = str(it['rank'])
        who = set(r.users(i))
        if (cat not in usual or who < usual[cat]) and it['lock'] is None:
            text = f"{joined(plural(classes[c]) for c in sorted(who))} only"
            rules.insert(0, text[0].upper() + text[1:])
        if cat == 'Ballista':
            assert who == {0x23} and r.u8(CLASS_TABLE + 9 * 0x23 + 3) == 0, who
            rules.append("A Shooter can't move (Mov 0)")
        if name in BROKEN_FROM:
            rules.append(f'What a {BROKEN_FROM[name]} becomes when its uses run out (a tome or staff is used up instead)')
        if i == LEVIN:
            rules.append("Its attack is its Mt alone: the wielder's Strength isn't added")
        if cat == 'Tome':
            rules.append("Its attack is its wielder's Str plus its Mt")
        if cat == 'Tome' or i == LEVIN:
            rules.append("Fought against Res, and terrain gives the foe no avoid against it")
            rules.append('Your unit can\'t hurt the Shadow Dragon with it')
        if i in (DEVIL_SWORD, DEVIL_AXE):
            rules.append('May turn on your unit wielding it: a (21 − Luck)% chance each strike, none while it holds the Lightsphere '
                         "(a foe's never does)")
        if i in EXP_DOUBLERS:
            rules.append('Doubles the EXP its wielder gains')
        if i == STARLIGHT:
            rules.append('The only weapon that can hurt a foe wielding Imhullu')
        if i == IMHULLU:
            rules.append('No attack against its wielder lands unless it is made with Starlight')
        if i == DULAM:
            rules.append('Leaves the target with 1 HP')
        if i == RESIRE:
            rules.append('Restores the HP of the damage it deals to its wielder')
        if it['uses'] == 0xFF:
            rules.append('Never breaks')
        effective = targets(r.effective(stat_from['id']))
        if effective:
            rules.append("No effect against a unit holding Iote's Shield or the Lightsphere")
        rng = stat_from['range']
        w = {
            'id': name.lower().replace("'", '').replace(' ', '-').replace('(', '').replace(')', ''),
            'name': name, 'romId': i, 'category': cat, 'rank': rank,
            'range': (str(rng[0]) if rng[0] == rng[1] else f'{rng[0]}-{rng[1]}') if rng else '1',
            'uses': None if it['uses'] == 0xFF else it['uses'], 'worth': it['price'] if it['price'] < 655350 else None,
            'effective': effective, 'rules': rules,
        }
        if w['worth'] and sell_price(w['worth']) != w['worth'] // 2:
            w['sell'] = sell_price(w['worth'])
        if i == LEVIN:
            w['magic'] = True
        if cat == 'Staff':
            sname, srank, suses, sprice, srange, effect = STAVES[name]
            assert suses == it['uses'] and (srank is None) == (rank == 'Prf') and (srank is None or str(srank) == rank) and \
                (sprice is None or sprice == it['price']), (name, sname, it)
            w['effect'] = effect
            w['exp'] = it['hit']  # a staff's +4 is the EXP it gives
            w['range'] = srange
        else:
            w.update({'mt': None if stat_from['mt'] == 0xFF else stat_from['mt'], 'hit': stat_from['hit'], 'crit': stat_from['crit'],
                      'wt': stat_from['wt']})
        out.append(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe3-items.py from Mystery of the Emblem's own item table (the ROM), named from the translation patch.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE3_WEAPONS: ChapterWeapon[] = [',
    ]
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in out]
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(out), 'weapons and staves')


if __name__ == '__main__':
    main()

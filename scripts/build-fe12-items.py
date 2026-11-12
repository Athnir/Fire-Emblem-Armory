"""
New Mystery of the Emblem's weapons, tomes, staves, dragonstones and ballistae, from the game's own item table (data/FE12Data.bin's
ItemData, `scripts/fe12_data.py`) named by the translation patch (`scripts/fe12_names.py`): writes src/data/fe12/fe12Weapons.ts.

Read in the game's code (data-raw/fe12/README.md): Shadow Dragon's battle code with changes. Nothing in battle reads weight (+0x18 is 0
on every weapon; attack speed is Spd, overlay 00 0x21f35a8), so no weapon has one; an effective weapon adds its Mt twice more (x3,
overlay 00 0x21f3494; an Iote's Shield the defender carries cancels its fliers' bit); a magic weapon (tomes, staves, +0x24 0x04) uses
Magic against Resistance at any range (arm9 0x20499c0); a devil weapon turns on its wielder when a 0-99 roll is under 21 - Lck / 2
(overlay 00 0x21f5128); a siege weapon (+0x24 0x08) can't be countered, never counters and never strikes twice (0x21f417c); +0x24
0x10000000 never wears out; who may use an item is the equip check's (arm9 0x204f870, `locks`); a healing staff heals its HP plus
half the user's Magic plus the user's staff rank bonus (arm9 0x204b004). Which of these the player can get is decided by their
sources (scripts/build-fe12-maps.py).

    python scripts/build-fe12-items.py
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe12_data as D  # noqa: E402
from fe13_bin import Bin  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe12', 'fe12Weapons.ts')
LISTED = {'Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone', 'Ballista'}
# What the forge takes (shop::RefineItem refuses staves and items; the ballistae and stones are never-forged ones, +0x2b 0x40).
FORGEABLE = {'Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Stone', 'Ballista'}
# +0x24 (what the item does).
USABLE, BRAVE, MAGIC, SIEGE, HEALS, DEVIL = 0x01, 0x02, 0x04, 0x08, 0x20, 0x40
IMHULLU, STARLIGHT, NO_MAGIC, NEVER_WEARS = 0x400, 0x800, 0x4000, 0x10000000
# +0x28 (more of what it does, and who may use it). Nosferatu's 0x100 (its help text: it drains) isn't read by the battle code that
# was traced, so it isn't said (data-raw/fe12/README.md, "Not confirmed").
IGNORES_DEF = 0x800
# The staff rank bonuses a healing staff adds (WeaponBonus's staff row: C, B, A).
STAFF_RANK = 'C +1, B +2, A +3'


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower().replace("'", '')).strip('-')


def targets(it):
    """The +0x2c bits as the weapon page's targets: dragons (0x01, every dragon class but Medeus's, the Shadow Dragon, which has
    0x02 alone: Falchion's 0x03 reaches him too), armour, ballisticians, horseback, fliers, manaketes, and the sword fighters."""
    bits = struct.unpack_from('<H', it['raw'], 0x2c)[0]
    out = []
    if bits & 0x03 == 0x03:
        out.append('fe12-dragons-all')
    elif bits & 0x01:
        out.append('fe12-dragons')
    for bit, t in ((0x04, 'armour'), (0x08, 'fe11-ballistician'), (0x10, 'horseback'), (0x20, 'flying'), (0x40, 'manakete'),
                   (0x80, 'fe12-swordfighter')):
        if bits & bit:
            out.append(t)
    assert not bits & ~0xFF, (it['name'], hex(bits))
    return out


# The equip check (arm9 0x204f870) reads +0x28's high bits against the unit's attributes (the person's +0x2c, the class's +0x38 and
# the placement's +0x0c, or'd): each of these asks for one attribute; 0x2000000 asks for the class's archer kind (+0x36 0x100);
# 0x4000000 turns away a woman (attribute 0x01) and 0x8000000 asks for one; 0x10000 and 0x20000 let Linde (attribute 0x100) and
# Merric (0x80) use the item from rank E.
NEEDS = {0x40000: 0x02, 0x80000: 0x04, 0x100000: 0x08, 0x200000: 0x20, 0x400000: 0x40, 0x1000000: 0x200}
FROM_E = {0x10000: 0x100, 0x20000: 0x80}
ARCHER, NO_WOMEN, WOMEN = 0x2000000, 0x4000000, 0x8000000


def and_list(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def placement_attrs():
    """{PID: the attributes its placements give it} (the placement records' +0x0c)."""
    out = {}
    P = D.persons()
    keys = {f for f, _, _, _ in D.maps()}
    for f in sorted(os.listdir(os.path.join(D.ROM, 'dispos'))):
        name = next((k for k, v in D.DLC_FILES.items() if v == f), f)
        if name not in keys:
            continue   # Shadow Dragon's leftover placements (bmap025, bmap101...): no map of this game uses them
        b = Bin(open(os.path.join(D.ROM, 'dispos', f), 'rb').read())
        o = 0
        while True:
            n, rec, cnt = struct.unpack_from('<3I', b.d, 0x20 + o)
            if not n and not rec:
                break
            for k in range(cnt):
                r = b.d[0x20 + rec + k * 88:0x20 + rec + k * 88 + 88]
                v = struct.unpack_from('<I', r, 0x0c)[0]
                if v:
                    pid = P[struct.unpack_from('<H', r, 0)[0]]['pid']
                    out[pid] = out.get(pid, 0) | v
            o += 12
    return out


PLACED = placement_attrs()


def who_has(attr):
    """The named people with an attribute, from their records or their placements (each once: a person's prologue double, PID_..._J,
    goes by the person's own name)."""
    return list(dict.fromkeys(p['name'] for p in D.persons() if p['named'] and p['pid'] and p['name']
                              and (p['attrs'] | PLACED.get(p['pid'], 0)) & attr))


def locks(it):
    """Who may use the item, in words, from its lock bits."""
    bits = it['more']
    out = []
    for bit, attr in NEEDS.items():
        if bits & bit:
            out.append(and_list(who_has(attr)) + ' only')
    if bits & ARCHER:
        classes = dict.fromkeys(j['name'] + 's' for j in D.jobs() if j['kinds'] & 0x100)
        out.append(and_list(list(classes)) + ' only')
    if bits & WOMEN:
        out.append('Women only')
    if bits & NO_WOMEN:
        out.append('Men only')
    for bit, attr in FROM_E.items():
        if bits & bit:
            out.append(f'{and_list(who_has(attr))} can use it from rank E')
    return out


def weapon(it):
    kind = D.KINDS[it['kind']]
    w = {'id': slug(it['name']), 'name': it['name'], 'romId': it['index'], 'category': kind, 'rank': D.rank_of(it['exp'])}
    lo, hi = it['min'], it['max']
    # 0xff: any distance; 0 (Fortify, Rescue, Silence, Aum): no tile, the staff reaches as its effect says.
    w['range'] = 'Any' if hi == 0xFF else '—' if not hi else (str(lo) if lo == hi else f'{lo}–{hi}')
    w['uses'] = None if it['flags'] & NEVER_WEARS else it['uses']
    w['worth'] = it['per_use'] * it['uses']
    if kind != 'Staff':
        w.update(mt=it['mt'], hit=it['hit'], crit=it['crit'])
    w['effective'] = targets(it)
    rules = locks(it)
    if it['flags'] & BRAVE:
        rules.append('Strikes twice in a row')
    if it['flags'] & MAGIC and kind not in ('Tome', 'Staff'):
        w['magic'] = True
        rules.append("Its attack uses the wielder's Magic, against the foe's Resistance, at any range")
    if it['flags'] & SIEGE:
        rules.append("The foe can't counter it, it never counters, and its wielder never strikes twice with it")
    if it['flags'] & DEVIL:
        rules.append("May turn on its wielder: a strike hits the wielder instead when a 0-99 roll is under 21 minus half the wielder's "
                     'Luck (rounded down)')
    if it['more'] & IGNORES_DEF:
        rules.append("Its damage ignores the foe's Def and Res")
    if it['flags'] & IMHULLU:
        rules.append('While it is equipped, no attack hurts its wielder unless it is made with Starlight')
    if it['flags'] & STARLIGHT:
        rules.append("The only weapon that can hurt a unit with Imhullu equipped")
    if it['flags'] & NO_MAGIC:
        rules.append('While it is equipped, no magic weapon hurts its wielder')
    if it['flags'] & USABLE and kind != 'Staff':
        if it['hp']:
            rules.append('Can be used to restore ' + ('all HP' if it['hp'] >= 99 else f"{it['hp']} HP"))
        raised = [f'{k.capitalize()} +{v}' for k, v in it['stats'].items() if v]
        if raised:
            rules.append('Can be used to raise ' + ', '.join(raised))
    if it['noforge'] and kind in FORGEABLE:
        rules.append("Can't be forged")   # +0x2b 0x40 (shop::RefineItem, arm9 0x206debc)
    if kind == 'Staff' and it['flags'] & HEALS:
        rules.append(f"Heals {it['hp']} HP plus half the user's Magic (rounded down), plus the user's staff rank bonus ({STAFF_RANK})")
    w['rules'] = rules
    if kind == 'Staff':
        w['effect'] = (it['help'] or '').replace('\n', ' ')
    return w


def main():
    out, names = [], {}
    for it in D.items():
        kind = D.KINDS.get(it['kind'])
        if kind not in LISTED or not it['name'] or it['iid'] == 'IID_NULL':
            continue
        out.append(weapon(it))
        names.setdefault(it['name'], []).append(out[-1])
    # Items the game gives one name (the dragons' breaths: each one at 1 range and, as ..._2, at 1-2): the second takes its range.
    for name, ws in names.items():
        for w in ws[1:]:
            w['name'] = f"{name} ({w['range']})"
            w['id'] = slug(w['name'])
    body = ',\n'.join('  ' + json.dumps(w, ensure_ascii=False) for w in out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write("import type { ChapterWeapon } from '../../components/ChapterWeapons'\n\n/*\n * GENERATED by scripts/build-fe12-items.py from"
                " New Mystery of the Emblem's own item table (data/FE12Data.bin), named by the translation patch.\n * Do not edit by"
                ' hand.\n */\nexport const FE12_WEAPONS: ChapterWeapon[] = [\n' + body + ',\n]\n')
    print(len(out), 'weapons')


if __name__ == '__main__':
    main()

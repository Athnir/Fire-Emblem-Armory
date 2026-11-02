"""
Shadow Dragon's weapons, tomes, staves and dragonstones, from the game's own item table (data/database's Item, `scripts/fe11_data.py`)
and its English text: writes src/data/fe11/fe11Weapons.ts.

Read in the game's code (`data-raw/fe11/README.md`): an effective weapon adds its Mt twice more (x3, overlay 00 at 0x21c7954; an
Iote's Shield the defender carries cancels what it covers); a magic weapon's attack uses Magic (0x2038348) and is fought against
Resistance (overlay 00 0x21c6cd8); who may use an item is the equip check's (arm9 0x203c834, `locks`); a devil weapon turns on its
wielder when a 0-99 roll is under 21 - Lck / 2 (overlay 00 0x21c9430); an item with +0x27 0x08 never wears out (arm9 0x203e09c); a
healing staff heals its HP plus half the user's Magic (arm9 0x2038e3c). Names are the game's own, abbreviations included ('Silv.
Sword'). The ballistae are items a Ballistician carries (the equip check lets only a class with the ballistician bit use one), so
they're listed. Left out: the unarmed slot and anything that isn't a weapon, tome, staff, dragonstone or ballista. Which of these the
player can get is decided by their sources (scripts/build-fe11-maps.py).

    python scripts/build-fe11-items.py
"""
import json
import os
import re
import struct

import fe11_data as D
from fe13_bin import Bin

OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'fe11', 'fe11Weapons.ts')
LISTED = {'Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone', 'Ballista'}
BRAVE, MAGIC, USABLE, HEALS, DEVIL = 0x02, 0x04, 0x01, 0x20, 0x40
IMHULLU_SHIELD, STARLIGHT = 0x04, 0x08


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower().replace("'", '')).strip('-')


def targets(raw):
    """The +0x2c bits as the weapon page's targets. Dragons are split: 0x01 is every dragon but Medeus (the Earth Dragon, whose
    class has 0x02 instead), so Wyrmslayer and Dragonpike miss him and Falchion (0x03) doesn't."""
    bits = raw[0x2c]
    out = []
    if bits & 0x03 == 0x03:
        out.append('fe11-dragons-all')
    elif bits & 0x01:
        out.append('fe11-dragons')
    for bit, t in ((0x04, 'armour'), (0x08, 'fe11-ballistician'), (0x10, 'horseback'), (0x20, 'flying'), (0x40, 'manakete')):
        if bits & bit:
            out.append(t)
    return out


# The equip check (arm9 0x203c834) reads the item's +0x2a lock bits against the unit's attributes (arm9 0x203c810: the person's +0x24,
# the class's +0x38 and the placement's +0x0c, or'd): each of these bits asks for one attribute; 0x0200 asks for the class's archer
# kind (+0x36 0x80); 0x0400 turns away a woman (attribute 0x01) and 0x0800 asks for one. 0x0001 and 0x0002 let Linde (attribute
# 0x100) and Merric (0x80) use the item from rank E, whatever rank it needs.
NEEDS = {0x0004: 0x02, 0x0008: 0x04, 0x0010: 0x08, 0x0020: 0x20, 0x0040: 0x40, 0x0080: 0x10, 0x0100: 0x200}
FROM_E = {0x0001: 0x100, 0x0002: 0x80}
ARCHER, WOMEN, NO_WOMEN = 0x0200, 0x0800, 0x0400


def and_list(names):
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def placement_attrs():
    """{PID: the attributes its placements give it} (the placement records' +0x0c: 0x02 on every one of Marth's)."""
    out = {}
    P = D.persons()
    for f in sorted(os.listdir(os.path.join(D.ROM, 'dispos'))):
        b = Bin(open(os.path.join(D.ROM, 'dispos', f), 'rb').read())
        o = 0
        while True:
            n, rec, cnt = struct.unpack_from('<3I', b.d, 0x20 + o)
            if not n and not rec:
                break
            for k in range(cnt):
                r = b.d[0x20 + rec + k * 80:0x20 + rec + k * 80 + 80]
                v = struct.unpack_from('<I', r, 0x0c)[0]
                if v:
                    pid = P[struct.unpack_from('<H', r, 0)[0]]['pid']
                    out[pid] = out.get(pid, 0) | v
            o += 12
    return out


PLACED = placement_attrs()


def who_has(attr):
    """The named people with an attribute, from their records or their placements."""
    return list(dict.fromkeys(p['name'] for p in D.persons() if p['named'] and p['pid'] and not p['pid'].endswith('_FALSE')
                              and (p['attrs'] | PLACED.get(p['pid'], 0)) & attr))


def locks(it):
    """Who may use the item, in words, from its lock bits."""
    bits = struct.unpack_from('<H', it['raw'], 0x2a)[0] & 0x3fff
    out = []
    for bit, attr in NEEDS.items():
        if bits & bit:
            out.append(and_list(who_has(attr)) + ' only')
    if bits & ARCHER:
        classes = dict.fromkeys(j['name'] + 's' for j in D.jobs() if j['kinds'] & 0x80)
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
    # 0xfe: Mag / 2; 0xff: any distance (arm9 0x2038e0c returns it as it is).
    w['range'] = 'Any' if hi == 0xFF else f'{lo}–Mag/2' if hi == 0xFE else '—' if not hi else (str(lo) if lo == hi else f'{lo}–{hi}')
    # +0x27 0x08: it never wears out (arm9 0x203e09c skips the use).
    w['uses'] = None if it['raw'][0x27] & 0x08 else it['uses']
    w['worth'] = it['per_use'] * it['uses']
    if kind != 'Staff':
        w.update(mt=it['mt'], hit=it['hit'], crit=it['crit'])
    w['wt'] = it['wt']
    w['effective'] = targets(it['raw'])
    rules = locks(it)
    if it['flags'] & BRAVE:
        rules.append('Strikes twice in a row')
    if it['flags'] & MAGIC and kind not in ('Tome', 'Staff'):
        w['magic'] = True
        rules.append("Its attack uses the wielder's Magic, against the foe's Resistance")
    if it['flags'] & DEVIL:
        rules.append("May turn on its wielder: a strike hits the wielder instead when a 0-99 roll is under 21 minus half the wielder's "
                     'Luck (rounded down)')
    if it['flags2'] & IMHULLU_SHIELD:
        rules.append('No attack hurts its bearer unless it is made with Starlight')
    if it['flags2'] & STARLIGHT:
        rules.append("The only magic that can break Imhullu's shield")
    if it['flags'] & USABLE and kind != 'Staff':
        if it['hp']:
            rules.append('Can be used to restore ' + ('all HP' if it['hp'] >= 99 else f"{it['hp']} HP"))
        raised = [f'{k.capitalize()} +{v}' for k, v in it['stats'].items() if v]
        if raised:
            rules.append('Can be used to raise ' + ', '.join(raised))
    if kind == 'Staff' and it['flags'] & HEALS:
        rules.append(f"Heals {it['hp']} HP plus half the user's Magic (rounded down)")
    w['rules'] = rules
    if kind == 'Staff':
        w['effect'] = staff_effect(it)
    return w


def staff_effect(it):
    """What a staff does: its help text, or (Barrier, Hammerne and Aum, whose help text the game draws with special glyphs the text
    file can't spell) what its record says."""
    help_ = (it['help'] or '').replace('\n', ' ')
    if help_ and help_.isascii():
        return help_
    if it['iid'] == 'IID_MAGICSHIELD':
        return f"Raises an adjacent ally's Resistance by {it['stats']['res']}."
    if it['iid'] == 'IID_HAMMARNE':
        return "Restores an adjacent ally's weapon to its full uses."
    if it['iid'] == 'IID_OM':
        return 'Brings a fallen ally back to life.'
    return ''


def main():
    out = []
    for it in D.items():
        kind = D.KINDS.get(it['kind'])
        if kind not in LISTED or not it['name'] or it['iid'] == 'IID_NULL':
            continue
        # Falchion and Imhullu have false copies (IID_FALCHION_FALSE, IID_MAFU_FALSE: Chapter 23's doubles of Gharnef carry them),
        # never yours; the weaker Falchion Chapter 24x's end gives (IID_FALCHION_TINY: Mt 7, Hit 90, Wt 9) is an item of its own under
        # the same name, so it's "Falchion (24x)".
        if it['iid'].endswith('_FALSE'):
            continue
        if it['iid'].endswith('_TINY'):
            it = dict(it, name=it['name'] + ' (24x)')
        out.append(weapon(it))
    body = ',\n'.join('  ' + json.dumps(w, ensure_ascii=False) for w in out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write("import type { ChapterWeapon } from '../../components/ChapterWeapons'\n\n/*\n * GENERATED by scripts/build-fe11-items.py from"
                " Shadow Dragon's own item table (data/database), named from its English text.\n * Do not edit by hand.\n */\n"
                'export const FE11_WEAPONS: ChapterWeapon[] = [\n' + body + ',\n]\n')
    print(len(out), 'weapons')


if __name__ == '__main__':
    main()

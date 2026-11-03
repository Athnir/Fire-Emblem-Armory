"""
Builds src/data/fe4/fe4Weapons.ts: Genealogy of the Holy War's weapons and staves, read from the ROM alone: the item table
(scripts/fe4_rom.py), the holy weapons' bonus records and the code that reads them, and what the battle and staff code does with each
effect. The English names are Lil' Nordion's, read from its item name table by the ROM's item id (scripts/fe4_names.py). Run:
    python scripts/build-fe4-items.py
"""
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_rom import ITEM_COUNT, R, item  # noqa: E402
import fe4_names as ln  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe4', 'fe4Weapons.ts')

# The holy weapons' records, by an item's holy id (its +5, 1-13): 16 bytes each, +0 the weapon type, +1 the weapon itself, +2..+9
# growth bonuses, +10..+15 Str, Mag, Skl, Spd, Def and Res while it's equipped ($84:A6B6 reads them through the offsets at $83:89C9).
HOLY = 0x389E3
HOLY_STATS = ('str', 'mag', 'skl', 'spd', 'def', 'mdf')
# Holy ids past 13 aren't records ($84:A6CC ignores them): the Def and Res routines add 7 themselves for the Safeguard (0x0E) and
# the Barrier Blade (0x0F): `LDA #stat / JSL $84:A6B6 / ... CMP #id / BNE / ... ADC #7` at $84:9C8B (Def) and $84:9CF7 (Res).
FIXED = ((0x49C8B, 'def'), (0x49CF7, 'mdf'))
# What a weapon's +8 bits give while it's equipped ($87:A280 maps them to skills), named as the patch names them.
WEAPON_SKILLS = ((0x01, 'Steal'), (0x08, 'Miracle'), (0x10, 'Critical'), (0x20, 'Renewal'), (0x40, 'Paragon'))
# Effectiveness (+0x10) against a class's bits ($83:8016): 1 the mounted classes, 2 pegasi and wyverns, 8 the armours, Baron and Emperor.
TARGETS = ((1, 'horseback'), (2, 'flying'), (8, 'armour'))
STATUS = {4: 'silence', 5: 'sleep', 6: 'berserk'}
RANKED = {'Sword': 'swords', 'Lance': 'lances', 'Axe': 'axes', 'Bow': 'bows', 'Fire': 'fire magic', 'Thunder': 'thunder magic',
          'Wind': 'wind magic', 'Light': 'light magic', 'Dark': 'dark magic', 'Staff': 'staves'}
# What each staff does (its +6), as the staff code does it: $87:E86A heals 10 + the caster's Mag (twice that for Mend, 80 for
# Recover: no unit has more HP); status staves land when the caster's Mag beats the target's Res, with no roll ($84:EE51).
STAVES = {
    1: "Restores an ally's HP by 10 + the caster's Mag.",
    2: "Restores an ally's HP by (10 + the caster's Mag) x 2.",
    3: "Restores 80 HP to an ally: all of it, as no unit has more.",
    4: "Restores an ally's HP by 10 + the caster's Mag, from afar.",
    5: "Restores 10 + the caster's Mag HP to every ally in range.",
    6: 'Sends an ally back to your home castle.',
    7: 'Sends an ally to any castle of yours.',
    8: 'Brings an ally next to the caster.',
    10: "Cures an ally's status.",
    11: 'Brings a fallen ally back to life; used in the home castle.',
    12: "Silences a foe, if the caster's Mag is higher than its Res.",
    13: "Puts a foe to sleep, if the caster's Mag is higher than its Res.",
    14: "Berserks a foe, if the caster's Mag is higher than its Res.",
}


def fixed_bonuses():
    """{holy id: (stat, amount)} the Def and Res routines add themselves."""
    out = {}
    for o, stat in FIXED:
        code = R[o:o + 40]
        m = re.search(rb'\xC9(.)\x00\xD0\x08\xA5\x4C\x18\x69(.)\x00', code, flags=re.S)
        assert m, hex(o)
        out[m.group(1)[0]] = (stat, m.group(2)[0])
    assert set(out) == {0x0E, 0x0F}, out
    return out


def holy_record(k):
    rec = R[HOLY + 16 * (k - 1):HOLY + 16 * k]
    return rec[1], {s: v for s, v in zip(HOLY_STATS, rec[10:16]) if v}


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()).strip('-')


def main():
    names = ln.item_names()
    fixed = fixed_bonuses()
    for _, skill in WEAPON_SKILLS:
        assert ln.in_text(skill) or ln.in_text(skill[:6]), skill
    # The weapon each holy record locks ($84:F66E): the Valkyrie Staff's holy id is 0, but record 11 names it.
    locked = {holy_record(k)[0] for k in range(1, 14)}
    out = []
    for rom_id in range(ITEM_COUNT):
        it = item(rom_id)
        if it['kind'] == 'ring':
            continue
        if it['uses'] == 0:
            continue   # broken stubs and drained tomes (what a weapon becomes), and the Charm and Thief Staves no one has
        if it['kind'] == 'weapon' and it['effect'] == 5 and it['uses'] == 255:
            continue   # the ballistae's arches, fixed to the map: Ballisticians never move (Mov 0, movement type 13)
        name = names[rom_id]
        holy = it['rank'] == '*'
        w = {
            'id': slug(name), 'name': name, 'romId': rom_id, 'category': it['type'], 'rank': 'Holy' if holy else it['rank'],
            'uses': it['uses'], 'worth': None if holy or it['price'] == 65535 else it['price'],
            'range': '—' if it['range'] == (0, 0) else f"{it['range'][0]}" if it['range'][0] == it['range'][1] else f"{it['range'][0]}-{it['range'][1]}",
        }
        rules = []
        if rom_id in locked:
            rules.append(f"Only a unit with its Major holy blood and a rank in {RANKED[it['type']]} can wield it.")
        if holy:
            rules.append("Can't be sold.")   # $84:B2DF: the shop refuses rank 0xFF
        if it['kind'] == 'staff':
            # A cast earns price / uses / 20 + 10 experience, at most 100 ($84:F99D).
            w['exp'] = min(100, it['price'] // it['uses'] // 20 + 10)
            w['effect'] = STAVES[it['staff_effect']]
        else:
            w.update(mt=it['mt'] if it['mt'] != 255 else None, hit=it['hit'], wt=it['wt'])
            w['effective'] = [t for bit, t in TARGETS if it['effective'] & bit]
            assert not it['effective'] & ~0b1011, (name, it['effective'])
            if w['effective']:
                # $84:E27F sets the crit rate to 100 against a class the weapon is effective on, and a crit doubles the whole attack
                # before Def or Res is taken off ($84:E6A9); no crit lands on a foe with Nihil.
                rules.append('Against them every hit is a critical, the whole attack doubled, unless the foe has Nihil.')
            w['skills'] = [s for bit, s in WEAPON_SKILLS if it['skills'] & bit]
            assert not it['skills'] & ~0x79, (name, it['skills'])
            e, arg = it['effect'], it['effect_arg']
            if e in (1, 2):
                # From 2 tiles away $84:DB25 swaps the whole item for the spell.
                rules.append(f"From 2 tiles away it attacks as {names[arg]}: the spell's Mt, Hit and Wt, Mag against Res, in the magic triangle.")
            if e in (2, 3):
                rules.append('Drains HP: the damage it deals heals the user.')
            elif e == 4:
                rules.append('Strikes twice in a row.')   # $84:E2FD doubles the strikes
            elif e == 5:
                rules.append("Attacks from far off and can't be countered.")   # $84:D9CF clears the target's weapon
            elif e == 6:
                rules.append(f"After a hit, a (30 - the foe's Res)% chance to inflict {STATUS[arg]}.")   # $84:E8C0
            elif e == 7:
                rules.append(f"Halves the foe's attack, unless the foe wields {names[0x50]}.")   # $84:DAF0
            elif e == 8:
                rules.append(f"Takes away {names[arg]}'s halving of its wielder's attack.")
            elif e == 9:
                rules.append("Reduces the foe's HP to 1.")   # $84:E904
            elif e == 0x0A:
                rules.append('Women only.')   # $84:F61E: the unit's $84:A3E5 must be 1
            else:
                assert e in (0, 1, 2, 3), (name, e)
            if it['holy'] and it['holy'] <= 13:
                record_item, stats = holy_record(it['holy'])
                assert record_item == rom_id, (name, record_item)
                w['stats'] = stats
            elif it['holy'] in fixed:
                stat, amount = fixed[it['holy']]
                w['stats'] = {stat: amount}
        if rules:
            w['rules'] = rules
        # Repairs cost price x uses spent / uses ($87:E25D).
        if it['price'] != 65535:
            w['repair'] = round(it['price'] / it['uses'], 2)
        out.append(w)
    lines = [
        "import type { Fe4Weapon } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-items.py from Genealogy of the Holy War's own item table and code (the ROM), with Lil' Nordion's",
        ' * English names. Do not edit by hand.',
        ' */',
        'export const FE4_WEAPONS: Fe4Weapon[] = [',
    ]
    for w in out:
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out), 'weapons and staves')


if __name__ == '__main__':
    main()

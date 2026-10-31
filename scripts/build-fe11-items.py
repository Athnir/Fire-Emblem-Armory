"""
Shadow Dragon's weapons, tomes, staves and dragonstones, from the game's own item table (data/database's Item, `scripts/fe11_data.py`)
and its English text: writes src/data/fe11/fe11Weapons.ts.

Read in the game's code (`data-raw/fe11/README.md`): an effective weapon adds its Mt twice more (x3, overlay 00 at 0x21c7954; an
Iote's Shield the defender carries cancels what it covers), a magic weapon's attack uses Magic (0x2038348). Names are the game's own,
abbreviations included ('Silv. Sword'). Left out: the ballistae (fixed to their tiles), the unarmed slot, and anything that isn't a
weapon, tome, staff or dragonstone. Which of these the player can get is decided by their sources (scripts/build-fe11-maps.py).

    python scripts/build-fe11-items.py
"""
import json
import os
import re

import fe11_data as D

OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'fe11', 'fe11Weapons.ts')
LISTED = {'Sword', 'Lance', 'Axe', 'Bow', 'Tome', 'Staff', 'Stone'}
BRAVE, MAGIC, USABLE, DEVIL = 0x02, 0x04, 0x01, 0x40
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
    for bit, t in ((0x04, 'armour'), (0x10, 'horseback'), (0x20, 'flying'), (0x40, 'manakete')):
        if bits & bit:
            out.append(t)
    return out


def personal(help_):
    """'For Marth.' / 'For Caeda.' in the item's own help text: the person it's locked to."""
    m = re.search(r'For (\w+)\.', help_ or '')
    return m.group(1) if m else None


def weapon(it):
    kind = D.KINDS[it['kind']]
    w = {'id': slug(it['name']), 'name': it['name'], 'romId': it['index'], 'category': kind, 'rank': D.rank_of(it['exp'])}
    lo, hi = it['min'], it['max']
    w['range'] = 'Mag/2' if hi == 0xFF else '—' if not hi else (str(lo) if lo == hi else f'{lo}–{hi}')
    w['uses'] = it['uses']
    w['worth'] = it['per_use'] * it['uses']
    if kind != 'Staff':
        w.update(mt=it['mt'], hit=it['hit'], crit=it['crit'])
    w['wt'] = it['wt']
    w['effective'] = targets(it['raw'])
    rules = []
    who = personal(it['help'])
    if who:
        rules.append(f'{who} only')
    if it['iid'] in ('IID_AURA', 'IID_EXCALIBUR'):
        # 'Light magic for women (Linde can use at level E).': who may use it, in the game's words.
        rules.append(it['help'].replace('\n', ' '))
    if it['flags'] & BRAVE:
        rules.append('Strikes twice in a row')
    if it['flags'] & MAGIC and kind not in ('Tome', 'Staff'):
        rules.append("Its attack uses the wielder's Magic")
    if it['flags'] & DEVIL:
        rules.append('May turn on its wielder')
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
        # Falchion and Imhullu each have variant records (IID_FALCHION_FALSE, IID_FALCHION_TINY, IID_MAFU_FALSE: the story's other
        # states of the item); the entry is the base record's, so a variant only shows where it's the one a source gives.
        if it['iid'].endswith(('_FALSE', '_TINY')):
            continue
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

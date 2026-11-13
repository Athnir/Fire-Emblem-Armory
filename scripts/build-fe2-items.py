"""
Builds Fire Emblem Gaiden's weapons, shields and rings from its own item arrays (scripts/fe2_data.py):
  src/data/fe2/fe2Weapons.ts

Run:
    python scripts/build-fe2-items.py

Every number and rule is the game's (data-raw/fe2/README.md has each table and the code that reads it). The spells (23-46) are learned
by level and never held, so they aren't items here; item 0 (the unarmed strike), 1 (a bow class's own bow) and 47 aren't items
anyone holds either.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe2_data as D  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe2', 'fe2Weapons.ts')

LANCES, SWORDS, BOWS, SHIELDS, RINGS = range(2, 11), range(11, 20), range(20, 23), range(48, 54), range(54, 59)
TENTACLE, LUNA, SHADOW_SWORD, LIGHTNING_SWORD, FALCHION = 19, 10, 14, 15, 17
HEXLOCK, DRACOSHIELD, BLESSED_SHIELD = 52, 53, 51
ANGEL_RING, SPEED_RING, MAGE_RING, PRAYER_RING = 55, 56, 57, 58
SOLDIER = 6
HEALS = 10   # an item's special byte (15:$DB38): its holder recovers 5 HP at the start of each turn (3:$9185 -> 3:$91A5)
# The effectiveness lists (15:$DAE4) as the weapon page names them: each list's classes, read below and checked.
TARGETS = {(3, 5): 'fe2-fliers', (1, 4, 7): 'fe2-mounted', (3, 5, 11, 17, 18): 'fe2-monsters'}


def category(i):
    return ('Lance' if i in LANCES else 'Sword' if i in SWORDS else 'Bow' if i in BOWS else 'Shield' if i in SHIELDS else 'Ring'
            if i in RINGS else None)


def ranges(i, it):
    """The map range (6:$A620): adjacent; the 0x04 bit adds 2 tiles; a bow held by a bow class reaches 1-5."""
    if i in BOWS:
        return '1-5'
    if i in SHIELDS or i in RINGS:
        return '-'
    return '1-2' if it['range'] & 0x04 else '1'


def main():
    items = D.items()
    users = D.weapon_users()
    out = []
    for it in items:
        i = it['id']
        if i == TENTACLE:
            cat = 'Monster'
        else:
            cat = category(i)
        if not cat:
            continue
        rules = []
        if i < D.WEAPON_ITEMS:
            own = it['own']
            if own & 0x80:
                rules.append(f'{D.SOV_NAMES[own & 0x7F]} only')
            first, last, cls = next((a, b, c) for a, b, c in users if a <= i <= b)
            if i in LANCES and SOLDIER in cls and i in (4, 7):
                # 15:$F46F: a Soldier can't use the Hand Lance or the Galdius.
                rules.append("Soldiers can't use it")
            eff = tuple(sorted(it['eff']))
            if eff:
                assert eff in TARGETS, (i, eff)
        else:
            eff = ()
        if it['special'] == HEALS:
            rules.append('Its holder recovers 5 HP at the start of each turn')
        if i == LUNA:
            rules.append("Its holder's weapon strikes always hit (the hit routine checks the item held, 9:$8207)")
        if i == SHADOW_SWORD:
            rules.append("In your units' hands (not a Dread Fighter's): once its first strike from beside the foe hits, a roll at or "
                         "below 20 − Lck turns it on the wielder, who takes Str + 13 − its own Def instead")
        if i == LIGHTNING_SWORD:
            rules.append("Deals 15 less the foe's Res, its wielder's Str not added, beside the foe or from 2 tiles away")
        if i == FALCHION:
            rules.append("Its wielder strikes back in a battle with a foe's Eyeball, which stops everyone else's strikes (9:$8A63)")
        if i == TENTACLE:
            rules.append('Duma\'s: while he has 52 HP or more he attacks with it (178 in 256) or Eye Beam; below 52, with Eyeball')
        if 'shield_def' in it:
            if i == BLESSED_SHIELD:
                rules.append(f"Def +{it['shield_def']} against weapons, only when the attacker is a monster (a Revenant, Gargoyle, "
                             'Necrodragon, Bonewalker or Mogall)')
            elif i == DRACOSHIELD:
                rules.append(f"Def +{it['shield_def']} against weapons, Res +13 against spells and the Lightning Sword")
            else:
                rules.append(f"Def +{it['shield_def']} against weapons")
        if i == HEXLOCK:
            rules.append("A spell's hit against its holder is 10")
        if i == ANGEL_RING:
            rules.append('Its holder counts 40 Lck in battle, and doubles its level-up gains')
        if i == SPEED_RING:
            rules.append('Its holder counts 40 Spd in battle (attack speed 40 less its weapon\'s Wt, and against spells), and moves 5 '
                         'more')
        if i == MAGE_RING:
            rules.append("Its holder's spells reach 1-5")
        if i == PRAYER_RING:
            rules.append('At half its max HP or less, its holder crits every strike (crit 100)')
        w = {
            'id': it['name'].lower().replace("'", '').replace(' ', '-'),
            'name': it['name'], 'romId': i, 'category': cat, 'rank': '', 'range': ranges(i, it),
            'effective': [TARGETS[eff]] if eff else [], 'rules': rules,
        }
        if i < D.WEAPON_ITEMS:
            w.update({'mt': it['mt'], 'hit': it['hit'], 'crit': it['crit'], 'wt': it['wt']})
        out.append(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe2-items.py from Fire Emblem Gaiden's own item arrays (the cartridge), named as Shadows of Valentia",
        ' * names them. Do not edit by hand.',
        ' */',
        'export const FE2_WEAPONS: ChapterWeapon[] = [',
    ]
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in out]
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(out), 'weapons, shields and rings')


if __name__ == '__main__':
    main()

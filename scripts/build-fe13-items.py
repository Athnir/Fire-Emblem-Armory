"""
Fire Emblem Awakening's weapons, staves, stones and monsters' weapons from the game's own item table (data/GameData.bin's ItemData,
56 bytes each), named and described from the game's English text (m/E/GameData.bin).

    python scripts/build-fe13-items.py   ->   src/data/fe13/fe13Weapons.ts

Formats in data-raw/fe13/README.md.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe13_data as D  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe13', 'fe13Weapons.ts')

CATEGORY = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'bow': 'Bow', 'tome': 'Tome', 'staff': 'Staff', 'dragonstone': 'Stone',
            'beaststone': 'Stone', 'claw': 'Monster', 'breath': 'Monster'}
# Item +48: the class categories it's effective against (the same bits as a class's +90), as the weapon page's targets.
TARGETS = {0x01: 'flying', 0x02: 'wyvern', 0x04: 'fe13-beast', 0x08: 'revenant', 0x10: 'armour', 0x20: 'grima'}
# Item +4 and +5: who may use it. Class categories (a class's +91) or one character.
LOCK4 = {0x04: 'chrom', 0x08: 0x01, 0x10: 0x02, 0x20: 0x04, 0x40: 0x08, 0x80: 'marth'}
LOCK5 = {0x01: 'walhart', 0x02: 'owain'}
PEOPLE = {'chrom': 'Chrom', 'marth': 'Marth (Lucina)', 'walhart': 'Walhart', 'owain': 'Owain'}
# Item +2 and +3: the effects the battle code reads from them (named after the skill each gives the wielder).
EFFECT2 = {
    0x01: 'Restores HP to its wielder equal to half the damage it deals',
    0x02: "May strike five times at half damage (the Astra skill: a chance of half the wielder's Skill)",
    0x04: "May restore HP equal to half the damage dealt (the Sol skill: a chance of the wielder's Skill)",
    0x08: "May halve the foe's Def or Res (the Luna skill: a chance of the wielder's Skill)",
    0x20: "May add half the damage its wielder has taken (the Vengeance skill: a chance of twice the wielder's Skill)",
    0x40: "May yield a Bullion (S) when its target falls (the Despoil skill: a chance of the wielder's Luck)",
    0x80: 'Hit and Avoid +50 against a foe with a sword equipped',
}
EFFECT3 = {
    0x01: 'Hit and Avoid +50 against a foe with a lance equipped',
    0x02: 'Hit and Avoid +50 against a foe with an axe equipped',
    0x04: 'Hit and Avoid +50 against a foe with a bow equipped',
    0x08: 'Hit and Avoid +50 against a foe with a tome equipped',
    0x10: 'Hit and Avoid +10 when its wielder is attacked',
    0x20: "Gains power when the foe's level is higher than its wielder's",
}
STAT_NAMES = {'str': 'Str', 'mag': 'Mag', 'skl': 'Skill', 'spd': 'Spd', 'lck': 'Lck', 'def': 'Def', 'res': 'Res'}


def joined(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ', '.join(xs[:-1]) + ' and ' + xs[-1]


def plural(name):
    return name[:-1] + 'ies' if name.endswith('y') else name + 'es' if name.endswith('s') else name + 's'


def class_group(bit):
    """Every class whose +95 has this category bit, by name (the male and female entries share one)."""
    return list(dict.fromkeys(c['name'] for c in D.classes() if c['cat2'] & bit and c['name']))


def main():
    out, seen = [], {}
    for it in D.items():
        cat = CATEGORY.get(it['type'])
        name = D.item_name(it)
        if not cat or not name:
            continue
        f = it['flags']
        if name in seen:
            # IID_ラグネル（敵）: the enemy's Ragnell, which never breaks, beside the one you can carry.
            assert name == 'Ragnell' and it['iid'].endswith('（敵）'), it['iid']
            name = 'Ragnell (enemy)'
        seen[name] = it['index']
        rules = []
        who = []
        for bit, v in LOCK4.items():
            if f[4] & bit:
                who.append(PEOPLE[v] if isinstance(v, str) else joined(plural(c) for c in class_group(v)))
        for bit, v in LOCK5.items():
            if f[5] & bit:
                who.append(PEOPLE[v])
        if cat == 'Stone':
            who.append('Manaketes' if it['type'] == 'dragonstone' else 'Taguel')
        if who:
            rules.append(f'{joined(who)} only')
        if f[0] & 0x02:
            rules.append('Strikes twice in a row')
        if f[0] & 0x04:
            rules.append("Deals magic damage: its attack uses the wielder's Mag and the foe's Res")
        for bit, text in EFFECT2.items():
            if f[2] & bit:
                rules.append(text)
        for bit, text in EFFECT3.items():
            if f[3] & bit and cat != 'Staff':
                rules.append(text)
        if f[1] & 0x80:
            rules.append(f"Restores {it['value']} HP to its wielder every turn")
        if f[0] & 0x01 and cat != 'Staff':
            # Usable from the item menu: +27 says how, +40 (or a stat byte) by how much.
            if it['use_kind'] == 1:
                rules.append('Can be used to restore all HP' if it['value'] >= 99 else f"Can be used to restore {it['value']} HP")
            elif it['use_kind'] == 6:
                stat = next(k for k, v in it['bonus'].items() if v)
                rules.append(f"Can be used for {STAT_NAMES[stat]} +{it['bonus'][stat]}, which wears off by 1 each turn")
            else:
                raise ValueError((name, it['use_kind']))
        stats = {k: v for k, v in it['bonus'].items() if v} if f[1] & 0x40 else {}
        if it['uses'] == 0:
            rules.append('Never breaks')
        worth = it['cost'] * it['uses'] or None
        if worth and f[4] & 0x02:
            rules.append('Sells for a quarter of its worth, not half')
        letter = D.rank_letter(it['rank_exp']) if it['rank_exp'] else None
        rng = (it['min_range'], it['max_range'])
        w = {
            'id': name.lower().replace("'", '').replace(' ', '-').replace('(', '').replace(')', '').replace('ö', 'o').replace('á', 'a'),
            'name': name, 'romId': it['index'], 'category': cat, 'rank': letter or '–',
            'range': f'{rng[0]}-Mag/2' if rng[1] == 0xFE else str(rng[0]) if rng[0] == rng[1] else f'{rng[0]}-{rng[1]}',
            'uses': it['uses'] or None, 'worth': worth,
            'effective': [TARGETS[b] for b in TARGETS if it['effective'] & b], 'rules': rules,
        }
        assert not it['effective'] & ~sum(TARGETS), name
        if stats:
            w['stats'] = stats
        if cat == 'Staff':
            w['effect'] = D.name_of(it['help_label'])
            w['exp'] = it['staff_exp']
        else:
            w.update({'mt': it['mt'], 'hit': it['hit'], 'crit': it['crit']})
        # Forging (any armory): a weapon with a worth, except Mire (+0's 0x08).
        if worth and cat not in ('Staff',) and not f[0] & 0x08:
            w['forge'] = True
        out.append(w)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = [
        "import type { ChapterWeapon } from '../../components/ChapterWeapons'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe13-items.py from Awakening's own item table (data/GameData.bin), named from its English text.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE13_WEAPONS: (ChapterWeapon & { forge?: true })[] = [',
    ]
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in out]
    lines.append(']')
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('wrote', len(out), 'weapons, staves and stones')


if __name__ == '__main__':
    main()

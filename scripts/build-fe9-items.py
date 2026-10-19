"""
Builds src/data/fe9/fe9Weapons.ts from Path of Radiance's own item table (FE8Data.bin) and text
(Mess/common.m): every weapon's rank, Mt, Hit, Crit, Wt, range, uses, worth, weapon EXP, stat bonuses,
what it's effective against and its special rules. Weapons the game never names (cut content) are
left out. The forge's base weapons, and the chapters they're offered in, come from shop/shopitem_*.bin.
Run:  python scripts/build-fe9-items.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe9_files import GameData, read_shop, read_text  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe9', 'fe9Weapons.ts')
RECORD = 96

CATEGORY = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'bow': 'Bow', 'knife': 'Knife',
            'flame': 'Fire', 'thunder': 'Thunder', 'wind': 'Wind'}
# What a weapon is effective against (its record's target fields).
TARGETS = {'fly': 'flying', 'armor': 'armour', 'knight': 'horseback', 'beast': 'beast', 'dragon': 'dragon', 'alize': 'laguz'}
# Rule flags, as the app words them. Flags not listed here don't change how the weapon plays.
RULES = {
    'twice': 'Strikes twice when it starts the fight',
    'poison': 'Poisons on contact',
    'crit0': "Can't land critical hits",
    'magsw': 'Deals magic damage (Mag against Res)',
    'resire': 'Restores HP equal to the damage dealt',
    'sealcrit': 'Negates critical hits against the wielder (except Wrath)',
    'weakA': "Negates the Goddess' blessing",
    'heroonly': 'Ike only',
    'blackonly': 'The Black Knight only',
    'finalonly': 'Ashnard only',
    'shootonly': 'Archers and Snipers only',
    'longfar': 'Siege weapon: long range, ignores the wielder\'s Str',
    'areaattack': 'Also hits units around the target',
    'absolutehit': 'Always hits',
}
# Named in the game but only obtainable with cheat codes (Serenes Forest's FE9 weapon tables), so left out.
CODES_ONLY = {'Devil Axe', 'Urvan', 'Bright Bow'}
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']
RANKS = {'E', 'D', 'C', 'B', 'A', 'S'}
# The NA release's difficulties: Easy and Normal share shopitem_n, Hard is shopitem_h (shopitem_m is the
# Japanese release's Maniac mode).
DIFFICULTIES = {'normal': 'n', 'hard': 'h'}
# Bases (and the forge) open before chapter 8, whose shop tables are file number 9 (MCT09).
FIRST_BASE = 9


def chapter_label(text, n):
    """9 -> 'Ch.8', 29 -> 'Ch.27-2', 31 -> 'Endgame' (the chapter title before its colon)."""
    return text[f'MCT{n:02d}'].split(':')[0]


def forge_availability(text):
    """{IID: {'normal': 'Ch.8 onward', 'hard': ...}} for each weapon the forge can use as a base."""
    out = {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        # A chapter with nothing in its shops has no base before it (Ch.27-2 follows straight on from 27).
        bases = [n for n in range(FIRST_BASE, 32) if any(isinstance(x, str) for x in shop.get(f'WSHOP_ITEMS_C{n:02d}', []))]
        offered = {}
        for n in bases:
            for iid in shop[f'FSHOP_ITEMS_C{n:02d}'][0::2]:
                if isinstance(iid, str):
                    offered.setdefault(iid, []).append(n)
        for iid, chapters in offered.items():
            # Runs of consecutive bases: 'Ch.8, Ch.10 onward'.
            runs, start = [], 0
            for i in range(1, len(chapters) + 1):
                if i == len(chapters) or bases.index(chapters[i]) != bases.index(chapters[i - 1]) + 1:
                    first, last = chapters[start], chapters[i - 1]
                    if last == bases[-1]:
                        runs.append(f'{chapter_label(text, first)} onward')
                    elif first == last:
                        runs.append(chapter_label(text, first))
                    else:
                        a, b = chapter_label(text, first), chapter_label(text, last)
                        runs.append(f"{a}–{b[3:] if a.startswith('Ch.') and b.startswith('Ch.') else b}")
                    start = i
            out.setdefault(iid, {})[key] = ', '.join(runs)
    return out


def main():
    g = GameData()
    text = read_text('common.m')
    forge = forge_availability(text)
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        r = g.d[o:o + RECORD]
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        effect_id = g.string(g.u32(o + 56)) or ''
        if not name or name in CODES_ONLY:
            continue  # never named in the game (cut content: Warp, Berserk, Unlock), or codes-only
        if kind == 'rod':
            category = 'Light' if effect_id.startswith('EID_LIGHT') else 'Staff'
        else:
            category = CATEGORY.get(kind)
        if not category:
            continue  # items, accessories, laguz claws and breath
        flags = [g.string(g.u32(o + 4 * i)) for i in range(6, 12) if g.u32(o + 4 * i)]
        targets = [TARGETS[t] for t in (g.string(g.u32(o + 4 * i)) for i in (12, 13) if g.u32(o + 4 * i)) if t in TARGETS]
        rank = g.string(g.u32(o + 20)) or ''
        uses = r[66]
        weapons.append({
            'id': iid[4:].lower(),
            'name': name,
            'category': category,
            # 'N' is a weapon only one character can use (no rank needed).
            'rank': rank if rank in RANKS else 'Prf',
            'mt': r[67], 'hit': r[68], 'crit': r[70], 'wt': r[69],
            # A staff whose range reaches 255 goes from 1 to half the wielder's Mag.
            'range': f'{r[71]}' if r[71] == r[72] else f"{r[71]}-{'Mag/2' if r[72] == 255 else r[72]}",
            'uses': None if 'infinity' in flags else uses,
            'worth': ((r[64] << 8) | r[65]) * uses,
            'wex': r[74],
            'stats': {k: (r[75 + i] - 256 if r[75 + i] > 127 else r[75 + i]) for i, k in enumerate(STATS) if r[75 + i]},
            'effective': targets,
            # A staff's rule is what it does, in the game's own words ("Restores some HP to an adjacent ally").
            'rules': [RULES[f] for f in flags if f in RULES]
            + ([' '.join(text.get(g.string(g.u32(o + 8)), '').split())] if category == 'Staff' else []),
            'flags': flags,
        })
        if iid in forge:
            # Which bases' forge offers it as a base weapon, by difficulty.
            weapons[-1]['forge'] = forge[iid]

    # Grouped by category (in the game's own order within each), so a bow never sits among the swords.
    order = ['Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Staff']
    weapons.sort(key=lambda w: order.index(w['category']))
    lines = [
        "import type { Fe9Weapon } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe9-items.py from Path of Radiance's own item table and text.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE9_WEAPONS: Fe9Weapon[] = [',
    ]
    for w in weapons:
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

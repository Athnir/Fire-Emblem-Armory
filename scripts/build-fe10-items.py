"""
Builds src/data/fe10/fe10Weapons.ts from Radiant Dawn's own item table (FE10Data.cms, ItemData) and
English text (Mess/e_common.m): every weapon's rank, Mt, Hit, Crit, Wt, range, uses, worth, weapon EXP,
stat bonuses, what it's effective against, its special rules and its description, and which bases'
shops sell it (regular stock, and one-off bargains). Laguz strikes and the spirits' attacks aren't
weapons a unit carries, so they're left out with the items.
Run:  python scripts/build-fe10-items.py
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe10_files import GameData, read_shop, read_text  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe10', 'fe10Weapons.ts')

CATEGORY = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'bow': 'Bow', 'ballista': 'Crossbow', 'knife': 'Knife',
            'flame': 'Fire', 'thunder': 'Thunder', 'wind': 'Wind', 'light': 'Light', 'dark': 'Dark', 'rod': 'Staff'}
# What a weapon is effective against (its SFXC_ targets). SFXC_DOORBREAK (every axe) isn't a unit type.
TARGETS = {'SFXC_FLY': 'flying', 'SFXC_ARMOR': 'armour', 'SFXC_KNIGHT': 'horseback', 'SFXC_BEAST': 'beast',
           'SFXC_DRAGON': 'dragon', 'SFXC_ALIZE': 'laguz', 'SFXC_BIRD': 'bird'}
# Personal weapons: the eqA-eqI flags, and who has the matching SID_EQ_ skill in PersonData.
OWNERS = {'eqA': 'Ike', 'eqB': 'Mist', 'eqC': 'Elincia (and Renning)', 'eqD': 'Micaiah', 'eqE': 'Sanaki',
          'eqF': 'Sephiran (Lehran)', 'eqG': 'Edward', 'eqH': 'Leonardo', 'eqI': 'Nolan'}
# Rule flags, as the app words them. Flags not listed here don't change how the weapon plays, or the
# game's own description already says it (the wind swords' shock wave).
RULES = {
    # Brave weapons only became attack-only in Fates (Fire Emblem Wiki, "Brave weapon").
    'twice': 'Strikes twice in a row, when attacking and when countering',
    'poison': 'Poisons on contact',
    'crit0': "Can't land critical hits",
    'resire': 'Restores HP equal to the damage dealt',
    'longfar': 'Siege weapon: attacks from long range',
    'sh': 'Fired from a ballista on the map',
    # main.dol 0x8002f3dc: a 'stone' weapon skips adding the wielder's Str.
    'stone': "Damage is its Mt alone: the wielder's Str isn't added",
    'absolutehit': 'Always hits',
    # Only Marksmen have SID_EXPANDRANGEO_1, which reaches one tile further with these bows.
    'expandrange': 'A Marksman can fire it at 2-3 range',
    'sealsteal': "Can't be stolen",
    'valuable': "Can't be sold",
}
# Not weapons a unit carries: the spirits' attacks, and a placeholder.
LEFT_OUT = re.compile(r'TAIL$|^IID_SPRT_')
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']
RANK = {'*': 'SS', 'S': 'S', 'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E'}
DIFFICULTIES = {'normal': 'n', 'hard': 'h'}
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}


def chapter_label(text, code):
    """'0305' -> ('Part 3', 'Ch.4'); '0407b' -> ('Part 4', 'Endgame (2)')."""
    return f"Part {ROMAN[text[f'MCT{code}_0_2']]}", text[f'MCT{code}_3']


def availability(text, entries):
    """{IID: {'normal': 'Part 3: Ch.4-6, 8 · Part 4: Prologue-Ch.2', 'hard': ...}} for the bases whose
    tables list each item. `entries(shop, table)` picks the IIDs a table offers."""
    out = {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        bases = [name.split('_C')[1] for name in shop if name.startswith('WSHOP_ITEMS_C') and name != 'WSHOP_ITEMS_C0000'
                 and any(isinstance(x, str) for x in shop[name] + shop.get(name.replace('WSHOP', 'ISHOP'), []))]
        bases.sort()
        offered = {}
        for b in bases:
            for iid in entries(shop, b):
                if b not in offered.setdefault(iid, []):
                    offered[iid].append(b)
        for iid, chapters in offered.items():
            parts = {}
            for c in chapters:
                parts.setdefault(c[:2], []).append(c)
            out_parts = []
            for p, cs in parts.items():
                own = [b for b in bases if b[:2] == p]
                runs, start = [], 0
                for i in range(1, len(cs) + 1):
                    if i == len(cs) or own.index(cs[i]) != own.index(cs[i - 1]) + 1:
                        first, last = chapter_label(text, cs[start])[1], chapter_label(text, cs[i - 1])[1]
                        both = first.startswith('Ch.') and last.startswith('Ch.')
                        runs.append(first if first == last else f"{first}–{last[3:] if both else last}")
                        start = i
                out_parts.append(f"{chapter_label(text, cs[0])[0]}: {', '.join(runs)}")
            out.setdefault(iid, {})[key] = ' · '.join(out_parts)
    return {iid: {key: d.get(key, '') for key in DIFFICULTIES} for iid, d in out.items()}


def stock(bargain):
    """The armory's and item shop's entries for one base: (IID, flag) pairs, the flag set on a one-off
    bargain (Serenes Forest's Bargains lists match)."""
    def entries(shop, b):
        out = []
        for table in (f'WSHOP_ITEMS_C{b}', f'ISHOP_ITEMS_C{b}'):
            rows = shop.get(table, [])
            out += [rows[i] for i in range(0, len(rows) - 1, 2) if isinstance(rows[i], str) and bool(rows[i + 1]) == bargain]
        return out
    return entries


def main():
    g = GameData()
    text = read_text()
    shop = availability(text, stock(False))
    bargain = availability(text, stock(True))
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        category = CATEGORY.get(kind)
        if not name or name == 'dummy' or not category or LEFT_OUT.search(iid):
            continue
        r = g.d[o:o + 0x38]
        rank = g.string(g.u32(o + 20)) if g.u32(o + 20) else ''
        price, = struct.unpack_from('>H', r, 0x26)
        mt, hit, crit, wt, uses, wex, rmin, rmax = r[0x28:0x30]
        n_attr, n_target, has_stats = r[0x35], r[0x36], r[0x37]
        p = o + 0x38
        flags = [g.string(g.u32(p + 4 * i)) for i in range(n_attr)]
        p += 4 * n_attr
        targets = [g.string(g.u32(p + 4 * i)) for i in range(n_target)]
        p += 4 * n_target
        # Stat bonuses while equipped (on staves the block means something else).
        block = g.d[p:p + 12] if has_stats and category != 'Staff' else bytes(12)
        owner = next((OWNERS[f] for f in flags if f in OWNERS), None)
        rules = ([f'{owner} only'] if owner else []) + [RULES[f] for f in flags if f in RULES]
        if category == 'Crossbow':
            # main.dol 0x8002f430: a crossbow's attack skips the wielder's Str; SID_EQBALLISTA (Warriors,
            # Reavers, Snipers, Marksmen) is what lets a class use one.
            rules = ['Warriors, Reavers, Snipers and Marksmen only, no weapon rank needed',
                     "Damage is its Mt alone: the wielder's Str isn't added"] + rules
        description = ' '.join(text.get(g.string(g.u32(o + 8)) or '', '').split())
        w = {
            'id': iid[4:].lower(),
            'name': name,
            'category': category,
            # 'N' is no rank needed: someone's own weapon, or a crossbow.
            'rank': RANK.get(rank) or ('Prf' if owner else '—'),
            'mt': mt, 'hit': hit, 'crit': crit, 'wt': wt,
            # A staff whose range reaches 255 goes from 1 to half the wielder's Mag.
            'range': f'{rmin}' if rmin == rmax else f"{rmin}-{'Mag/2' if rmax == 255 else rmax}",
            'uses': None if 'infinity' in flags else uses,
            'worth': price * uses,
            'wex': wex,
            'stats': {k: (block[i] - 256 if block[i] > 127 else block[i]) for i, k in enumerate(STATS) if block[i]},
            'effective': [TARGETS[t] for t in targets if t in TARGETS],
            'rules': rules,
            'flags': flags,
            'description': description,
        }
        if iid in shop:
            w['shop'] = shop[iid]
        if iid in bargain:
            w['bargain'] = bargain[iid]
        weapons.append(w)

    order = ['Sword', 'Lance', 'Axe', 'Bow', 'Crossbow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff']
    weapons.sort(key=lambda w: order.index(w['category']))
    lines = [
        "import type { TelliusWeapon } from '../fe9/types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe10-items.py from Radiant Dawn's own item table, text and shop files.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE10_WEAPONS: TelliusWeapon[] = [',
    ]
    for w in weapons:
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

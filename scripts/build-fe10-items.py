"""
Builds src/data/fe10/fe10Weapons.ts from Radiant Dawn's own item table (FE10Data.cms, ItemData) and
English text (Mess/e_common.m): every weapon's rank, Mt, Hit, Crit, Wt, range, uses, worth, weapon EXP,
stat bonuses, what it's effective against and its special rules, and which bases'
shops sell it (regular stock, and one-off bargains). Only weapons you can get are listed: sold,
found, dropped, stolen or carried by someone who joins you; not the maps' fixed ballistae or a weapon
locked to a boss. Laguz strikes and the spirits' attacks aren't weapons a unit carries, so they're left out too.
Run:  python scripts/build-fe10-items.py
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe10_files import FE10, GameData, read_dispos, read_shop, read_text  # noqa: E402
import fe9_cmb  # noqa: E402

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
# range already shows it (the wind swords' shock wave reaches 1-2).
RULES = {
    # Brave weapons only became attack-only in Fates (Fire Emblem Wiki, "Brave weapon").
    'twice': 'Strikes twice in a row, when attacking and when countering',
    'poison': 'Poisons on contact',
    'crit0': "Can't land critical hits",
    'resire': 'Restores HP equal to the damage dealt',
    'longfar': 'Siege weapon: attacks from long range',
    'absolutehit': 'Always hits',
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


def chapter_id(text, code):
    """'0305' -> 'fe10-3-4': the map page's id for a chapter code, so the app can tell when a chapter is reached.
    Part 1 Ch.6 is two maps ('fe10-1-6-1' and '-2'); a first appearance there counts from the first."""
    label = text[f'MCT{code}_3'].replace('Ch.', '')
    cid = 'fe10-' + re.sub(r'[^a-z0-9]+', '-', f'{int(code[:2])}-{label}'.lower()).strip('-')
    return cid + '-1' if code == '0107' else cid


def availability(text, entries):
    """({IID: {'normal': 'Part 3: Ch.4-6, 8 · Part 4: Prologue-Ch.2', 'hard': ...}}, {IID: {'normal': ['0304', ...],
    'hard': [...]}}, {'normal': ['0102', ...]}) for the bases whose tables list each item, as the text the app shows and
    as chapter codes, then every base.
    `entries(shop, table)` picks the IIDs a table offers."""
    out, at, base_list = {}, {}, {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        bases = [name.split('_C')[1] for name in shop if name.startswith('WSHOP_ITEMS_C') and name != 'WSHOP_ITEMS_C0000'
                 and any(isinstance(x, str) for x in shop[name] + shop.get(name.replace('WSHOP', 'ISHOP'), []))]
        bases.sort()
        base_list[key] = bases
        offered = {}
        for b in bases:
            for iid in entries(shop, b):
                if b not in offered.setdefault(iid, []):
                    offered[iid].append(b)
        for iid, chapters in offered.items():
            at.setdefault(iid, {})[key] = list(chapters)
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
    return ({iid: {key: d.get(key, '') for key in DIFFICULTIES} for iid, d in out.items()},
            {iid: {key: d.get(key, []) for key in DIFFICULTIES} for iid, d in at.items()}, base_list)


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


def forge_bases(shop, b):
    """The base weapons the forge offers at one base: FSHOP_ITEMS_Cppnn is a grid of (weapon type,
    material, IID or 0) triples (MIK_SW, MDV_IRN -> IID_IRONSWORD)."""
    rows = shop.get(f'FSHOP_ITEMS_C{b}', [])
    return [rows[i + 2] for i in range(0, len(rows) - 2, 3) if isinstance(rows[i + 2], str)]


def forge_cards(text):
    """FSHOP_CARD_DATA: a count, then (name label, bonus word, odds word) for each card a Coin can draw.
    The bonus bytes are Mt, Hit, Crit and extra Coins; the odds word's top byte is the chance in %."""
    rows = read_shop('n')['FSHOP_CARD_DATA']
    out = []
    for i in range(rows[0]):
        label, bonus, odds = rows[1 + 3 * i: 4 + 3 * i]
        mt, hit, crit, coins = bonus.to_bytes(4, 'big')
        out.append({'name': text[label], 'mt': mt, 'hit': hit, 'crit': crit, 'coins': coins, 'chance': odds >> 24})
    return out


# The test and tutorial maps aren't part of the game.
REAL_MAP = re.compile(r'^(bmap0[1-4]|emap0[1-4])')
# Script calls that hand an item over: chests and villages (MindGetItem), gifts and rewards, dig spots.
GIVES = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub', 'UnitAddItem', 'GetRndTreasure', 'NetuzoWeapon')


# Units nothing can be stolen from: Ashera, whose Judge is hers alone.
STEAL_PROOF = {'PID_ASTARTE'}


def chapter_of(folder):
    """'bmap0305' and 'emap0305b' -> '0305'; the Endgame's five maps keep their letter ('bmap0407c' -> '0407c')."""
    code = folder[4:]
    return code if folder.startswith('bmap0407') else code[:4]


def obtainable(shop_at, bargain_at, forge_at, sealed):
    """{IID: the first chapter code you can get it in} for every IID you can get: sold (shop, bargain, forge),
    handed over by a chapter script (treasure, villages, gifts), dropped by a foe ('/D' in its slot), carried by
    someone who joins your army (a character placed in any of the maps' mikata groups, from the chapter they
    join), or stolen from a foe once disarmed. A weapon can't be stolen when it's flagged sealsteal (`sealed`:
    Rewarp, Elsleep) or locked to its unit ('/L' in its slot: Sephiran's Creiddylad)."""
    import importlib.util
    fe9_cmb.FE9 = FE10
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    first = {}

    def seen(iid, code):
        first[iid] = min(code, first.get(iid, code))

    for sold in (shop_at, bargain_at, forge_at):
        for iid, by_difficulty in sold.items():
            for chapters in by_difficulty.values():
                for code in chapters:
                    seen(iid, code)
    for name in os.listdir(os.path.join(FE10, 'Scripts')):
        if re.match(r'C0[1-4]', name):
            script = fe9_cmb.Script(name)
            code = name[1:].split('.')[0]
            for h in script.handlers():
                for fn, args in maps.calls(script, h):
                    if fn in GIVES:
                        for a in args:
                            if isinstance(a, str) and a.startswith('IID_'):
                                seen(a, code)
    placed = [(chapter_of(folder), group, pid, items) for folder in os.listdir(os.path.join(FE10, 'zmap')) if REAL_MAP.match(folder)
              for diff in 'nhc' for group, pid, items in read_dispos(folder, diff)]
    # Who joins, and in which chapter: what they carry is yours from then on.
    joined = {}
    for code, group, pid, _ in placed:
        if 'mikata' in group:
            joined[pid] = min(code, joined.get(pid, code))
    for code, group, pid, items in placed:
        for item in items:
            base, _, mark = item.partition('/')
            marks = mark.split('/')
            stealable = 'L' not in marks and base not in sealed and pid not in STEAL_PROOF
            if 'D' in marks or stealable:
                seen(base, code)
            if pid in joined:
                seen(base, max(code, joined[pid]))
    return first


def main():
    g = GameData()
    text = read_text()
    shop, shop_at, bases = availability(text, stock(False))
    bargain, bargain_at, _ = availability(text, stock(True))
    forge, forge_at, _ = availability(text, forge_bases)
    # Only what you can get: not the map's own ballistae, nor a foe's weapon locked to it (Judge, Rewarp).
    sealed = set()
    for o in g.records('IID_', 'MIID_'):
        n_attr = g.d[o + 0x35]
        if 'sealsteal' in (g.string(g.u32(o + 0x38 + 4 * i)) for i in range(n_attr)):
            sealed.add(g.string(g.u32(o)))
    first = obtainable(shop_at, bargain_at, forge_at, sealed)
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        category = CATEGORY.get(kind)
        if not name or name == 'dummy' or not category or LEFT_OUT.search(iid) or iid not in first:
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
        if 'expandrange' in flags:
            # Only Marksmen have SID_EXPANDRANGEO_1: one tile further with a bow that has this flag. Longbows
            # and crossbows don't, so theirs stays as it is.
            rules.append(f'A Marksman can fire it at {rmin}-{rmax + 1} range')
        if category == 'Crossbow':
            # main.dol 0x8002f430: a crossbow's attack skips the wielder's Str; SID_EQBALLISTA (Warriors,
            # Reavers, Snipers, Marksmen) is what lets a class use one.
            rules = ['Warriors, Reavers, Snipers and Marksmen only, no weapon rank needed',
                     "Damage is its Mt alone: the wielder's Str isn't added"] + rules
        if category == 'Staff':
            # A staff's rule is what it does, in the game's own words ("Restores HP to an adjacent ally").
            what = ' '.join(text.get(g.string(g.u32(o + 8)) or '', '').split())
            rules += [what] if what else []
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
        }
        if iid in shop:
            w['shop'] = shop[iid]
            w['shopAt'] = {k: [chapter_id(text, c) for c in v] for k, v in shop_at[iid].items()}
        if iid in bargain:
            w['bargain'] = bargain[iid]
            w['bargainAt'] = {k: [chapter_id(text, c) for c in v] for k, v in bargain_at[iid].items()}
        if iid in forge:
            # Which bases' forge offers it as a base weapon, by difficulty.
            w['forge'] = forge[iid]
            w['forgeAt'] = {k: [chapter_id(text, c) for c in v] for k, v in forge_at[iid].items()}
        # The first chapter you can get it in: the spoiler block hides it until then.
        w['from'] = chapter_id(text, first[iid])
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
    lines += ['', "/** The chapters with a base (shop and forge) before them, in order, by difficulty. */",
              'export const FE10_BASES = ' + json.dumps({k: [chapter_id(text, c) for c in v] for k, v in bases.items()})]
    lines += ['', "/** What a Coin can add to a forged weapon: the card drawn, its bonus and its chance in %. */",
              'export const FE10_FORGE_CARDS = ' + json.dumps(forge_cards(text), ensure_ascii=False)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

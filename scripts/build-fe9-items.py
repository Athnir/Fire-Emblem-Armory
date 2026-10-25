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
    # Path of Radiance's Brave weapons hit twice in a row every time, attacking or countering.
    'twice': 'Strikes twice in a row, when attacking and when countering',
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
    'valuable': "Can't be sold",
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


# Chapter 17 is four maps (fe9-17-1 to fe9-17-4); a first appearance there counts from the first.
SECTIONED = {'fe9-17': 'fe9-17-1'}


def chapter_id(text, n):
    """9 -> 'fe9-8': the map page's id for chapter file number n, so the app can tell when a chapter is reached."""
    cid = 'fe9-' + chapter_label(text, n).lower().replace('ch.', '').replace(' ', '')
    return SECTIONED.get(cid, cid)


def availability(text, tables):
    """({IID: {'normal': 'Ch.8 onward', 'hard': ...}}, {IID: {'normal': [9, 10, ...], 'hard': [...]}}): the bases
    whose `tables` offer each item, as the text the app shows and as chapter file numbers. A table is
    (name prefix, step): the shops list IIDs, the forge (IID or 0, material) pairs."""
    out, at, base_list = {}, {}, {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        # A chapter with nothing in its shops has no base before it (Ch.27-2 follows straight on from 27).
        bases = [n for n in range(FIRST_BASE, 32) if any(isinstance(x, str) for x in shop.get(f'WSHOP_ITEMS_C{n:02d}', []))]
        base_list[key] = bases
        offered = {}
        for n in bases:
            for prefix, step in tables:
                for iid in shop.get(f'{prefix}_C{n:02d}', [])[0::step]:
                    if isinstance(iid, str) and n not in offered.get(iid, []):
                        offered.setdefault(iid, []).append(n)
        for iid, chapters in offered.items():
            at.setdefault(iid, {})[key] = list(chapters)
            # Runs of consecutive bases: 'Ch.8–11, 13, 20 onward'.
            runs, start = [], 0
            for i in range(1, len(chapters) + 1):
                if i == len(chapters) or bases.index(chapters[i]) != bases.index(chapters[i - 1]) + 1:
                    first, last = chapters[start], chapters[i - 1]
                    a, b = chapter_label(text, first), chapter_label(text, last)
                    if first == last:
                        runs.append(a)
                    elif last == bases[-1]:
                        runs.append(f'{a} onward')
                    else:
                        runs.append(f"{a}–{b[3:] if a.startswith('Ch.') and b.startswith('Ch.') else b}")
                    start = i
            # 'Ch.' once, at the front of the list.
            out.setdefault(iid, {})[key] = ', '.join(r if k == 0 else r.removeprefix('Ch.') for k, r in enumerate(runs))
    # Offered on one difficulty only: '' on the other.
    return ({iid: {key: d.get(key, '') for key in DIFFICULTIES} for iid, d in out.items()},
            {iid: {key: d.get(key, []) for key in DIFFICULTIES} for iid, d in at.items()}, base_list)


# Script calls that hand an item over: chests and villages, gifts and rewards, the desert's buried items.
GIVES = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub', 'UnitAddItem', 'GetRndTreasure')


def obtainable(shop_at, forge_at, staves, tomes):
    """{IID: the first chapter (file number) you can get it in} for every IID you can get in the story: sold
    (shop, forge), handed over by a chapter script (chests, villages, gifts, buried items), dropped by a foe,
    carried by someone who joins your army (a character placed in a mikata group, from the chapter they
    join), or stolen. Steal takes anything a foe hasn't equipped (the
    tutorial, tut.m MS_T11盗む_01/04: Spd and Str each 1 above the target's Spd and the item's Wt). A foe
    with two weapons unequips one whenever it fights with the other, so only a foe's lone weapon stays
    theirs unless it drops. The trial maps keep
    nothing, so they don't count."""
    import importlib.util
    from fe9_cmb import Script
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    first = {}

    def seen(iid, n):
        first[iid] = min(n, first.get(iid, n))

    for sold in (shop_at, forge_at):
        for iid, by_difficulty in sold.items():
            for chapters in by_difficulty.values():
                for n in chapters:
                    seen(iid, n)
    for n in range(1, 32):
        script = Script(f'C{n:02d}.cmb')
        for h in script.handlers():
            for fn, args in maps.calls(script, h):
                if fn in GIVES:
                    for a in args:
                        if isinstance(a, str) and a.startswith('IID_'):
                            seen(a, n)
    placed = [(n, group, u) for n in range(1, 32) for code in ('n', 'h', 'c')
              for group, units in maps.dispos(f'bmap{n:02d}', code).items() for u in units]
    # Who joins, and in which chapter: what they carry is yours from then on.
    joined = {}
    for n, group, u in placed:
        if 'mikata' in group:
            joined[u['pid']] = min(n, joined.get(u['pid'], n))
    for n, group, u in placed:
        arms = [w for w in u['weapons'] if w not in staves]
        loose = len(arms) > 1 or (arms and arms[0] in tomes and u['items'])
        for iid in set(u['drops']) | set(u['items']) | (set(arms) if loose else set()):
            seen(iid, n)
        if u['pid'] in joined:
            for iid in set(u['weapons']) | set(u['items']):
                seen(iid, max(n, joined[u['pid']]))
    return first


def main():
    g = GameData()
    text = read_text('common.m')
    forge, forge_at, bases = availability(text, [('FSHOP_ITEMS', 2)])
    shop, shop_at, _ = availability(text, [('WSHOP_ITEMS', 1), ('ISHOP_ITEMS', 1)])
    # Only what you can get: not the maps' own ballistae, nor a boss's own weapon (Gurgurant).
    staves = {g.string(g.u32(o)) for o in g.records('IID_', 'MIID_')
              if g.string(g.u32(o + 12)) == 'rod' and not (g.string(g.u32(o + 56)) or '').startswith('EID_LIGHT')}
    tomes = {g.string(g.u32(o)) for o in g.records('IID_', 'MIID_')
             if g.string(g.u32(o + 12)) in ('flame', 'thunder', 'wind') or (g.string(g.u32(o + 56)) or '').startswith('EID_LIGHT')}
    first = obtainable(shop_at, forge_at, staves, tomes)
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        r = g.d[o:o + RECORD]
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        effect_id = g.string(g.u32(o + 56)) or ''
        if not name or name in CODES_ONLY or iid not in first:
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
            # 'N' is no rank needed: a weapon only one character can use, or a knife (any thief's).
            'rank': rank if rank in RANKS else '—' if category == 'Knife' else 'Prf',
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
        if iid in shop:
            # Which bases' armory (or, for staves, item shop) sells it, by difficulty.
            weapons[-1]['shop'] = shop[iid]
            weapons[-1]['shopAt'] = {k: [chapter_id(text, n) for n in v] for k, v in shop_at[iid].items()}
        if iid in forge:
            # Which bases' forge offers it as a base weapon, by difficulty.
            weapons[-1]['forge'] = forge[iid]
            weapons[-1]['forgeAt'] = {k: [chapter_id(text, n) for n in v] for k, v in forge_at[iid].items()}
        # The first chapter you can get it in: the spoiler block hides it until then.
        weapons[-1]['from'] = chapter_id(text, first[iid])

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
    # Every chapter with a base before it, by difficulty: the app words a partial list ("Ch.8–11") from these.
    lines += ['', "/** The chapters with a base (shop and forge) before them, in order, by difficulty. */",
              'export const FE9_BASES = ' + json.dumps({k: [chapter_id(text, n) for n in v] for k, v in bases.items()})]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

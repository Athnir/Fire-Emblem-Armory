"""
Builds src/data/weapons/gameItems.ts from the game's item table (GameData.bin): every weapon's Mt, Hit,
Crit, Avoid, Dodge, range, weapon rank, prices, stat changes and what it's effective against, keyed by
its English name, so the app's weapon data can be checked against (and filled from) the game itself.

Needs the dumped game files in data-raw/fates/romfs/ (git-ignored). Run:
    python scripts/build-fates-items.py
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_lz import decompress  # noqa: E402
from fates_maps import RAW, ROOT, text_for  # noqa: E402

OUT = os.path.join(ROOT, 'src', 'data', 'weapons', 'gameItems.ts')
B = 0x20
RECORD = 104  # bytes per item

# Weapon experience needed for each rank.
RANKS = [(251, 'S'), (161, 'A'), (96, 'B'), (51, 'C'), (21, 'D'), (1, 'E')]
# Bits of the effectiveness byte (+0x2C).
EFFECTIVE_BITS = {1: 'flying', 2: 'dragon', 4: 'beast', 8: 'armour', 16: 'monster'}
# Weapon-type targets, named only in the item's description ("Effective against swords/katana").
EFFECTIVE_WORDS = {'swords': 'sword', 'spears': 'lance', 'lances': 'lance', 'axes': 'axe', 'tomes': 'tome'}
# The item type byte (+0x10): Nohr's line then Hoshido's, in pairs; stones, breaths, fists, rocks and saws are all 'Other'.
CATEGORIES = {2: 'Sword', 3: 'Katana', 4: 'Lance', 5: 'Naginata', 6: 'Axe', 7: 'Club', 8: 'Dagger', 9: 'Shuriken', 10: 'Bow',
              11: 'Yumi', 12: 'Tome', 13: 'Scroll', 14: 'Staff', 15: 'Rod'}
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']


def signed(b):
    return b - 256 if b > 127 else b


def main():
    text = text_for()
    items = {}
    # The main item table, then each DLC item's own file (the same record layout).
    files = [os.path.join(RAW, 'GameData.bin.lz')] + sorted(glob.glob(os.path.join(RAW, 'dlc', '*', '*', 'GameData', 'Item', '*.bin.lz')))
    for path in files:
        read_items(decompress(open(path, 'rb').read()), text, items)
    write(items)


def read_items(d, text, items):

    def s(ptr):
        o = B + ptr
        if not 0 < ptr < len(d) - B:
            return None
        try:
            return d[o:d.index(b'\0', o)].decode('shift_jis')
        except (ValueError, UnicodeDecodeError):
            return None

    u32 = lambda o: struct.unpack_from('<I', d, o)[0]  # noqa: E731
    starts = [o for o in range(B, len(d) - 8, 4) if (s(u32(o)) or '').startswith('IID_') and (s(u32(o + 4)) or '').startswith('MIID')]
    for o in starts:
        r = d[o:o + RECORD]
        iid = s(u32(o))
        name = text.get('M' + iid)
        wexp = r[20]
        if not name or not wexp or len(r) < RECORD:
            continue  # not a weapon (no rank needed)
        help_text = ' '.join(text.get('MIID_H_' + iid[4:], '').split())
        effective = [v for bit, v in EFFECTIVE_BITS.items() if r[44] & bit]
        lower = help_text.lower()
        if 'effective against' in lower:
            after = lower.split('effective against', 1)[1].split('.')[0]
            effective += [v for w, v in EFFECTIVE_WORDS.items() if w in after and v not in effective]
        stats = {k: signed(r[54 + i - 6]) for i, k in enumerate(STATS)}
        if '（青銅）' in iid:
            name += ' (Bronze form)'  # Kiragi's Fujin Yumi in Heirs of Fate shares the real one's name
        if '真ガングレリ' in iid:
            name += ' (reward)'  # The game names it Ganglari like Chapter 2's: a My Castle rank reward, far stronger
        if any(it['iid'] == iid for it in items.values()):
            continue
        items[name] = {
            'iid': iid,
            'category': CATEGORIES.get(r[16], 'Other'),
            'mt': r[23], 'hit': r[24], 'crit': signed(r[26]), 'avoid': signed(r[28]), 'dodge': signed(r[30]),
            'range': [r[32], r[33]],
            # Effective Spd for follow-ups: for your own (+0x22), and when the foe checks whether it doubles you (+0x23).
            'followUpSpd': signed(r[34]), 'guardSpd': signed(r[35]),
            'rank': next(letter for need, letter in RANKS if wexp >= need),
            'buy': u32(o + 36), 'sell': u32(o + 40),
            'uses': r[22] or None,
            'effective': effective,
            'weakVsOthers': 'weak against' in lower,
            # One flag (+0x40, bit 0) bars both critical hits and offensive skills.
            'noCritOrSkills': bool(r[64] & 1),
            'stats': {k: v for k, v in stats.items() if v},
            'help': help_text,
            # My Castle's ally gifts (+0x50 Hoshido's pool, +0x51 Nohr's): the gate the highest cleared chapter's progress must
            # reach, -1 when it isn't in that pool. Scouting maps' glinting spots draw from the same pools.
            'allyGift': {pool: signed(r[off]) for pool, off in (('Hoshido', 0x50), ('Nohr', 0x51)) if signed(r[off]) >= 0},
            # The Lottery's rank for it (1-5, 0 = not a prize): +0x56 in the Dawn Lottery, +0x57 in the Dusk Lottery.
            'lottery': {lot: r[off] for lot, off in (('Dawn', 0x56), ('Dusk', 0x57)) if r[off]},
        }


def write(items):
    lines = [
        '/*',
        " * GENERATED by scripts/build-fates-items.py from the game's item table. Do not edit by hand.",
        ' */',
        'export interface GameItem {',
        '  iid: string',
        "  /** The weapon type the item table gives it ('Sword', 'Katana', ... or 'Other' for stones, breaths, fists, rocks and saws). */",
        '  category: string',
        '  mt: number',
        '  hit: number',
        '  crit: number',
        '  avoid: number',
        '  dodge: number',
        '  range: [number, number]',
        '  /** Effective Spd for making your own follow-up attacks (Steel weapons -3, Parallel Falchion +3). */',
        '  followUpSpd: number',
        '  /** Effective Spd when the foe checks whether it can follow up on you (Javelin -5: "weak to follow-ups"). */',
        '  guardSpd: number',
        "  rank: 'E' | 'D' | 'C' | 'B' | 'A' | 'S'",
        '  /** Shop prices as the game lists them (0 = never sold). */',
        '  buy: number',
        '  sell: number',
        '  /** Staves / rods only. */',
        '  uses?: number',
        "  /** What it's effective against: flying, dragon, beast, armour, monster, or a weapon type. */",
        '  effective: string[]',
        '  /** It has a penalty against everything it isn\'t effective against. */',
        '  weakVsOthers: boolean',
        "  /** Can't land critical hits or trigger offensive skills (one flag in the game covers both). */",
        '  noCritOrSkills: boolean',
        '  /** Stat changes while equipped. */',
        '  stats: Partial<Record<string, number>>',
        "  /** The game's own description. */",
        '  help: string',
        "  /** My Castle's ally gifts: the progress gate in each pool it's in (Hoshido's for Birthright, Nohr's for Conquest, both for Revelation). */",
        "  allyGift?: Partial<Record<'Hoshido' | 'Nohr', number>>",
        "  /** Its rank among the Lottery's prizes (1-5): the Dawn Lottery is Birthright's and Revelation's, the Dusk Lottery Conquest's and Revelation's. */",
        "  lottery?: Partial<Record<'Dawn' | 'Dusk', number>>",
        '}',
        '',
        'export const GAME_ITEMS: Record<string, GameItem> = {',
    ]
    for name, it in items.items():
        fields = [f"iid: {json.dumps(it['iid'], ensure_ascii=False)}", f"category: '{it['category']}'", f"mt: {it['mt']}", f"hit: {it['hit']}",
                  f"crit: {it['crit']}", f"avoid: {it['avoid']}", f"dodge: {it['dodge']}",
                  f"range: [{it['range'][0]}, {it['range'][1]}]", f"followUpSpd: {it['followUpSpd']}", f"guardSpd: {it['guardSpd']}", f"rank: '{it['rank']}'",
                  f"buy: {it['buy']}", f"sell: {it['sell']}"]
        if it['uses']:
            fields.append(f"uses: {it['uses']}")
        fields += [f"effective: {json.dumps(it['effective'])}", f"weakVsOthers: {'true' if it['weakVsOthers'] else 'false'}",
                   f"noCritOrSkills: {'true' if it['noCritOrSkills'] else 'false'}",
                   'stats: {' + ', '.join(f' {k}: {v}' for k, v in it['stats'].items()) + (' }' if it['stats'] else '}'),
                   f"help: {json.dumps(it['help'], ensure_ascii=False)}"]
        for key in ('allyGift', 'lottery'):
            if it[key]:
                fields.append(f'{key}: {{ ' + ', '.join(f'{k}: {v}' for k, v in it[key].items()) + ' }')
        lines.append(f'  {json.dumps(name, ensure_ascii=False)}: {{ ' + ', '.join(fields) + ' },')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(items), 'weapons')


if __name__ == '__main__':
    main()

"""
Builds src/data/weapons/fatesShops.ts: which chapter each building level opens after, and what each shop stocks at each
level (an item's quantity: a number, or unlimited).

The levels come from the game's own castle/castle_building.bin (each level's chapter on each route). What the shops stock isn't
in any file we have (it's in the program), so that comes from Serenes Forest's My Castle pages, the best source available per
the ruleset (needs a network connection). The levels Serenes lists are checked against the file. Run:
    python scripts/build-fates-shops.py
"""
import json
import os
import re
import struct
import sys
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_lz import decompress  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'weapons', 'fatesShops.ts')
BASE = 'https://serenesforest.net/fire-emblem-fates/my-castle/'
# page -> the name the app uses for the shop (Dawn/Dusk Armoury sell weapons; Rod/Staff Store staves and items)
SHOPS = {'dawn-armoury': 'Dawn Armoury', 'dusk-armoury': 'Dusk Armoury', 'rod-store': 'Rod Store', 'staff-store': 'Staff Store'}


# Serenes Forest's spellings that differ from the game's English text, which the app uses.
ALIASES = {'Armourslayer': 'Armorslayer', 'Short Bow': 'Mini Bow'}


def item_name(text):
    text = text.replace('’', "'")
    return ALIASES.get(text, text)


class Tables(HTMLParser):
    """Every <table> as a list of rows of cell text."""

    def __init__(self):
        super().__init__()
        self.tables, self.row, self.cell, self.depth = [], None, None, 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.depth += 1
            self.tables.append([])
        elif tag == 'tr' and self.depth:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = ''

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.row is not None and self.cell is not None:
            self.row.append(' '.join(self.cell.split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row:
                self.tables[-1].append(self.row)
            self.row = None
        elif tag == 'table':
            self.depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def tables(page):
    req = urllib.request.Request(BASE + page + '/', headers={'User-Agent': 'Mozilla/5.0'})
    parser = Tables()
    parser.feed(urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace'))
    return parser.tables


# castle_building.bin's shop names (白武器屋 = white weapon shop...) as the app names them.
FILE_SHOPS = {'白武器屋': 'Dawn Armoury', '黒武器屋': 'Dusk Armoury', '白道具屋': 'Rod Store', '黒道具屋': 'Staff Store', '錬成屋': 'Smithy'}


def file_levels():
    """{shop: [chapter that must be completed for level 1, 2, 3]} from the game's building table. Each level record names its
    unlock chapter per route (Birthright, Conquest, Revelation) at +0x34, +0x38 and +0x3c; the routes that have the shop agree."""
    d = decompress(open(os.path.join(ROOT, 'data-raw', 'fates', 'romfs', 'castle', 'castle_building.bin.lz'), 'rb').read())
    base = 0x20

    def text(ptr):
        o = base + ptr
        if not 0 < ptr < len(d) - base:
            return None
        try:
            t = d[o:d.index(b'\0', o)].decode('shift_jis')
        except ValueError:
            return None
        return t if t and t.isprintable() else None

    out = {}
    for o in range(base, base + struct.unpack_from('<I', d, 4)[0], 4):
        m = re.fullmatch(r'KID_(.+)_([123])', text(struct.unpack_from('<I', d, o)[0]) or '')
        if not m or m.group(1) not in FILE_SHOPS:
            continue
        chapters = {int(c[1:]) for c in (text(struct.unpack_from('<I', d, o + off)[0]) for off in (0x34, 0x38, 0x3C)) if c}
        assert len(chapters) == 1, (m.group(0), chapters)
        out.setdefault(FILE_SHOPS[m.group(1)], {})[int(m.group(2))] = chapters.pop()
    return {shop: [lv[i] for i in sorted(lv)] for shop, lv in out.items()}


def level_chapters(rows):
    """The Upgrade Details table: shop level -> the chapter that must be completed first."""
    table = next(t for t in rows if t and t[0][:2] == ['Shop Level', 'Chapter Completion'])
    return [int(r[1]) for r in table[1:]]


def stock(cell):
    """'Infinite' -> None (unlimited), '3' -> 3, '0' -> 0 (not sold at that level)."""
    return None if cell.lower().startswith('inf') else int(cell)


def main():
    out = {'levels': file_levels(), 'items': {}}
    # Serenes Forest's own level tables must agree with the file.
    assert level_chapters(tables('smithy')) == out['levels']['Smithy'], 'Smithy levels differ from the game file'
    for page, shop in SHOPS.items():
        rows = tables(page)
        assert level_chapters(rows) == out['levels'][shop], f'{shop} levels differ from the game file'
        table = next(t for t in rows if any(len(r) == 6 and r[1:4] in (['Infinite'] * 3, ['0', '1', '2']) or (len(r) == 6 and r[4].isdigit() and r[5].isdigit()) for r in t))
        for r in table:
            if len(r) == 6 and r[4].isdigit() and r[5].isdigit() and re.fullmatch(r'Infinite|\d+', r[1]):
                out['items'].setdefault(item_name(r[0]), []).append({'shop': shop, 'stock': [stock(c) for c in r[1:4]], 'buy': int(r[4]), 'sell': int(r[5])})
    lines = [
        '/*',
        " * GENERATED by scripts/build-fates-shops.py from Serenes Forest's My Castle pages. Do not edit by hand.",
        ' */',
        '',
        '/** The chapter that must be completed before each level of a building opens (levels 1 to 3). */',
        'export const FATES_BUILDING_CHAPTERS: Record<string, number[]> = ' + json.dumps(out['levels']),
        '',
        '/** What a shop stocks at each of its three levels: a number, or null for unlimited (0 = not sold at that level). */',
        'export interface ShopStock {',
        '  shop: string',
        '  stock: [number | null, number | null, number | null]',
        '  buy: number',
        '  sell: number',
        '}',
        '',
        'export const FATES_SHOPS: Record<string, ShopStock[]> = {',
    ]
    for name, entries in out['items'].items():
        lines.append(f'  {json.dumps(name, ensure_ascii=False)}: {json.dumps(entries)},')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out['items']), 'items', out['levels'])


if __name__ == '__main__':
    main()

"""
Builds src/data/fe4/fe4Weapons.ts: Genealogy of the Holy War's weapons and staves.

Every number comes from the game's own item table in the ROM (scripts/fe4_rom.py). The English names, the holy weapons' stat bonuses
and the staves' effects are Serenes Forest's: the ROM's names are Japanese with kanji we don't read yet, and the bonus table and staff
effects aren't found in the ROM. Each Serenes row is checked against the ROM's (Mt, Hit, Wt, range, rank, price, uses) so a name can't
land on the wrong item. Needs a network connection. Run:
    python scripts/build-fe4-items.py
"""
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_rom import ITEM_COUNT, item  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe4', 'fe4Weapons.ts')
BASE = 'https://serenesforest.net/genealogy-of-the-holy-war/inventory/'
PAGES = ['swords', 'lances', 'axes', 'bows', 'fire-thunder-wind', 'light-dark', 'staves']


class Rows(HTMLParser):
    """Every table row on a page, as a list of cell text."""

    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = ''

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.row is not None and self.cell is not None:
            self.row.append(' '.join(self.cell.split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row and self.row[0] != 'Icon':
                self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def page(name):
    req = urllib.request.Request(BASE + name + '/', headers={'User-Agent': 'Mozilla/5.0'})
    p = Rows()
    p.feed(urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace'))
    return p.rows


def serenes():
    """Serenes' rows in page order, minus the 'Broken X (*)' and 'Empty Book' rows (the ROM keeps those apart from the rest)."""
    out = []
    for name in PAGES:
        for r in page(name):
            if r[1].startswith('Empty Book') or (r[1].startswith('Broken') and r[6 if name != 'staves' else 3] == '*'):
                continue
            out.append((name, r))
    return out


def rng(text):
    a, _, b = text.partition('~')
    return (int(a), int(b or a))


def same(kind, r, it):
    """Whether a Serenes row describes this ROM item (the numbers the page and the table share)."""
    if kind == 'staves':
        return it['kind'] == 'staff' and str(it['rank']) == r[3] and (r[1].startswith('Broken') or str(it['price']) == r[4]) and str(it['uses']) == r[5] and it['range'] == rng(r[2])
    mt, wt, hit, rg, rank, worth, uses = r[2:9]
    broken = r[1].startswith('Broken')
    return (it['kind'] == 'weapon' and (str(it['mt']) == mt or not mt.isdigit()) and str(it['wt']) == wt and str(it['hit']) == hit and it['range'] == rng(rg)
            and str(it['rank']) == rank and (broken or str(it['price']) == worth) and str(it['uses']) == uses)


def match():
    """[(ROM item id, Serenes page, Serenes row, ROM item)] for every Serenes row, in the ROM's order."""
    rows = serenes()
    items = [item(i) for i in range(ITEM_COUNT)]
    cursor, matched = 0, []
    for kind, r in rows:
        while cursor < len(items) and not same(kind, r, items[cursor]):
            cursor += 1
        assert cursor < len(items), ('no ROM item for', r)
        matched.append((cursor, kind, r, items[cursor]))
        cursor += 1
    return matched


def main():
    matched = match()
    assert [m[0] for m in matched][-1] < ITEM_COUNT
    names = {m[0]: m[2][1].replace('’', "'") for m in matched}
    out = []
    for rom_id, kind, r, it in matched:
        name = names[rom_id]
        text = r[-1].replace('’', "'")
        if name.startswith('Broken') or name.endswith('Arch') or 'unused' in text.lower():
            continue  # broken stubs, the ballistae's arches (fixed to the map) and the items Serenes lists as never used
        w = {
            'id': re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-'), 'name': name, 'romId': rom_id, 'category': it['type'],
            'rank': {'*': 'Holy'}.get(it['rank'], it['rank']), 'uses': it['uses'], 'worth': it['price'] if it['price'] != 65535 else None,
            'range': f"{it['range'][0]}" if it['range'][0] == it['range'][1] else f"{it['range'][0]}-{it['range'][1]}",
        }
        if kind == 'staves':
            w['exp'] = int(r[6])
            w['effect'] = text
            w['range'] = w['range'] if it['range'][1] else '1'
        else:
            w.update(mt=it['mt'] if it['mt'] != 255 else None, hit=it['hit'], wt=it['wt'])
            w['effective'] = [t for bit, t in ((1, 'horseback'), (2, 'flying'), (8, 'armour')) if it['effective'] & bit]
            assert not it['effective'] & ~0b1011, (name, it['effective'])
            w['skills'] = [t for bit, t in ((1, 'Steal'), (8, 'Prayer'), (0x10, 'Critical'), (0x20, 'Life'), (0x40, 'Elite')) if it['skills'] & bit]
            assert not it['skills'] & ~0x79, (name, it['skills'])
            rules = []
            e, arg = it['effect'], it['effect_arg']
            if e == 1:
                rules.append(f'Casts {names[arg]} from range')
            elif e in (2, 3):
                rules.append('Drains HP: the damage it deals heals the user' + (f' and casts {names[arg]} from range' if e == 2 else ''))
            elif e == 4:
                rules.append('Strikes twice in a row')
            elif e == 5:
                rules.append("Long range; the user can't be countered and can't move afterwards")
            elif e == 6:
                rules.append(f"May inflict {({6: 'berserk', 4: 'silence', 5: 'sleep'})[arg]} on the foe")
            elif e == 7:
                rules.append("Halves the foe's attack power")
            elif e == 8:
                rules.append("Negates Loputousu's effect")
            elif e == 9:
                rules.append("Reduces the foe's HP to 1")
            elif e == 0x0A:
                rules.append('Women only')
            else:
                assert e == 0, (name, e)
            w['rules'] = rules
            w['stats'] = {k.lower(): int(v) for k, v in re.findall(r'(Str|Mag|Skl|Spd|Def|Mdf|Lck|Mov) \+(\d+)', text)}
            w['serenes'] = text
        out.append(w)
    lines = [
        "import type { Fe4Weapon } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-items.py from Genealogy of the Holy War's own item table (the ROM), with Serenes Forest's English",
        " * names, holy weapon bonuses and staff effects. Do not edit by hand.",
        ' */',
        'export const FE4_WEAPONS: Fe4Weapon[] = [',
    ]
    for w in out:
        w.pop('serenes', None)
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    open(OUT, 'w', encoding='utf-8').write(chr(10).join(lines) + chr(10))
    print('wrote', OUT, len(out), 'weapons and staves')


if __name__ == '__main__':
    main()

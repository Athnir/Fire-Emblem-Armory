"""
Builds src/data/fe4/fe4Terrain.ts and src/data/fe4/fe4Maps.ts: Genealogy of the Holy War's chapter maps and terrain, read from the
user's own ROM (scripts/fe4_rom.py), with the game's own decompression routine run by scripts/fe4_cpu.py.

How the ROM keeps a chapter (found by tracing a chapter load in Mesen; details in data-raw/fe4/README.md):
  - a table of twelve 3-byte pointers at $88:9FC3 (Prologue, Chapters 1-10, the Final Chapter) leads to 27-byte chapter records;
  - a record holds the compressed map (a 64 x 64 grid of u16: the low 10 bits are a metatile, 16 x 16 pixels), the compressed
    metatile graphics, and the compressed terrain table (one byte per metatile: the terrain id);
  - byte 21 of the record is the width and byte 23 the height, each in units of 16 tiles (the Prologue is 64 x 32, the rest 64 x 64);
  - the terrain id indexes the movement cost table (15 movement types x 26 ids, $03:987D) and the avoid table ($03:9A25).

English chapter and class names come from Serenes Forest (the ROM's are Japanese). Needs a network connection. Run:
    python scripts/build-fe4-maps.py
"""
import html
import json
import os
import re
import sys
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_cpu import Cpu, rom_offset  # noqa: E402
from fe4_rom import R, u16  # noqa: E402
from terrain_codes import encode_row  # noqa: E402

import importlib.util  # noqa: E402


def _items():
    spec = importlib.util.spec_from_file_location('build_fe4_items', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-fe4-items.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe4')

CHAPTER_TABLE = 0x89FC3   # 12 x 3-byte SNES pointers to the chapter records
CLASSES = 0x38FCD         # 31 bytes each, 72 entries
MOVE_COSTS = 0x3987D      # u16 offsets from here: one row of 26 terrain ids per movement type
AVOID = 0x39A25           # one signed byte per terrain id
CHAPTERS = [
    ('fe4-prologue', 0, 'Prologue', 'Birth of the Holy Knight'),
    ('fe4-1', 1, 'Ch.1', 'Girl of the Spirit Forest'),
    ('fe4-2', 2, 'Ch.2', 'Disturbance in Agustria'),
    ('fe4-3', 3, 'Ch.3', 'Lion King Eltshan'),
    ('fe4-4', 4, 'Ch.4', 'Dance in the Skies'),
    ('fe4-5', 5, 'Ch.5', 'Doors of Destiny'),
    ('fe4-6', 6, 'Ch.6', 'Inheritors'),
    ('fe4-7', 7, 'Ch.7', 'Passing the Desert'),
    ('fe4-8', 8, 'Ch.8', 'Dragon Knights of Thracia'),
    ('fe4-9', 9, 'Ch.9', 'For Whose Sake'),
    ('fe4-10', 10, 'Ch.10', 'Light and Dark'),
    ('fe4-final', 11, 'Final', 'The Last Holy War'),
]

# Terrain id -> (the builder's letter, the name Serenes Forest gives it). Ids the maps never use (10, 11, 16, 17, 19-21, 23) are
# left out; the build stops if one turns up.
TERRAIN = {
    0: ('C', 'Peak'), 1: ('D', 'Deep forest'), 2: ('C', 'Cliff'), 3: ('.', 'Plain'), 4: ('f', 'Forest'), 5: ('a', 'Sea'),
    6: ('w', 'River'), 7: ('m', 'Mountain'), 8: ('s', 'Desert'), 9: ('N', 'Castle defence'), 12: ('g', 'Castle gate'),
    13: ('#', 'Castle wall'), 14: ('y', 'Sand'), 15: ('b', 'Bridge'), 18: ('v', 'Village'), 22: ('h', 'Church'),
    24: ('T', 'Tower'), 25: ('R', 'Road'),
}
# The movement types that have identical costs everywhere share one column on the page. (type numbers, the page's name)
MOVE_GROUPS = [
    ((0,), 'Knights'), ((1,), 'Promoted knights'), ((2,), 'Fliers'), ((3,), 'Swordfighters & archers'), ((4,), 'Armours'),
    ((5, 9), 'Soldiers & lords'), ((6,), 'Axe fighters'), ((7,), 'Barbarians & hunters'), ((8,), 'Pirates'),
    ((10, 14), 'Mages & priests'), ((11, 12), 'Thieves & civilians'),
]
SERENES = 'https://serenesforest.net/genealogy-of-the-holy-war/classes/base-stats/'
UNIT_LISTS = 0x1C000      # 57 u16 offsets (from here) to lists of 8-byte unit records, each ended by 0xFFFF
CHARACTERS = 0x38000 + 0x2DF5   # u16 count*2, then u16 offsets (from here) to each character's record, id 1 upward
# The lists each chapter's opening script loads, found by running the game (python scripts/fe4_mesen.py lists 0 11). A chapter owns
# its opening lists and every list up to the next chapter's first one; the last list (57) is a different table.
OPENING_LISTS = {0: [0], 1: [7, 2], 2: [8], 3: [13], 4: [18], 5: [24], 6: [30, 31], 7: [33, 34], 8: [37, 38], 9: [41, 42], 10: [46, 47], 11: [50]}
BOSS_PAGES = ['boss-data', 'npc-data']


def serenes_classes():
    """Serenes' class table: [(name, hp, str, mag, skl, spd, def, mdf, mov)] in its order."""
    req = urllib.request.Request(SERENES, headers={'User-Agent': 'Mozilla/5.0'})
    page = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    rows = []
    for r in re.findall(r'<tr.*?</tr>', page, flags=re.S):
        c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
        if len(c) == 10 and c[0] != 'Class':
            rows.append((c[0].rstrip(' *'), *[int(x) for x in c[1:9]]))
    return rows


def class_names():
    """ROM class index -> English name: Serenes' class table is in the ROM's order, Free Knight included. The ROM keeps each class's
    base stats one 31-byte slot early (class i's stats sit in slot i-1; the first five knights share theirs, so only later classes
    show it), which this checks: Str, Mag, Skl, Spd, Def and Mdf of slot i-1 must equal Serenes' row i."""
    rows = serenes_classes()
    assert len(rows) == 72, len(rows)
    for i in range(1, 71):
        slot = CLASSES + (i - 1) * 31
        assert tuple(rows[i][2:8]) == tuple(R[slot + 0x19:slot + 0x1F]), ('class', i, rows[i])
    return {i: rows[i][0] for i in range(72)}


def chapter_headers():
    """Each chapter's script header, [chapter u16][opening script][event table] (3-byte pointers), found by their self-reference: the
    opening script follows the 8-byte header. Returns {chapter: (bank, opening script address)}."""
    found = {}
    for o in range(len(R) - 8):
        n = R[o]
        if n <= 11 and R[o + 1] == 0:
            p1 = R[o + 2] | R[o + 3] << 8
            b1 = R[o + 4]
            p2 = R[o + 5] | R[o + 6] << 8
            if R[o + 7] == b1 and b1 >= 0x80 and (b1 & 0x3F) == o >> 16 and p1 == (o & 0xFFFF) + 8 and p1 < p2 < p1 + 0x4000:
                found[n] = (b1, p1)
    assert sorted(found) == list(range(12)), sorted(found)
    return found


def opening_relations(cpu, bank, y):
    """From a chapter's opening script: {army: its relation to your army} (1 hostile, 2 friendly, 3 neutral). The script's
    `4b army x` commands name the armies and its `4d relation army other` commands say how each stands to the others."""
    armies, relation = set(), {}
    for _ in range(80):
        o = rom_offset(bank << 16 | y)
        op = R[o]
        if op == 0x30 or R[o:o + 2] == bytes([0xFF, 0xFF]):
            break
        n = cpu.script_skip(bank, y)
        args = R[o + 1:o + (n - y)]
        if op == 0x4B:
            armies.add(args[0])
        elif op == 0x4D and args[2] == 0:
            relation[args[1]] = args[0]
        y = n
    assert 0 in armies, (bank, hex(y))
    return {a: relation.get(a) for a in armies if a != 0}


def character(i):
    """The character table's record for a unit id: 38 bytes for a named character (kind 0 playable, kind 2 named foe or NPC), 13 for a
    generic foe (kind 3), 12 for kind 1."""
    n = u16(CHARACTERS) // 2
    a = CHARACTERS + u16(CHARACTERS + 2 * (i - 1))
    return R[a:CHARACTERS + u16(CHARACTERS + 2 * i)] if i < n else R[a:a + 13]


def unit_lists():
    offsets = [u16(UNIT_LISTS + 2 * i) for i in range(57)]
    out = []
    for off in offsets:
        p, recs = UNIT_LISTS + off, []
        while u16(p) != 0xFFFF:
            recs.append(bytes(R[p:p + 8]))
            p += 8
        out.append(recs)
    return out


def owned_lists():
    """{chapter: [list indexes]}: its opening lists and every list up to the next chapter's first."""
    firsts = [min(OPENING_LISTS[c]) for c in range(12)]
    assert firsts == sorted(firsts)
    return {c: list(range(firsts[c], firsts[c + 1] if c < 11 else 57)) for c in range(12)}


BOSS_CHAPTER = {'P': 0, 'F': 11}


def boss_rows():
    """Serenes' boss and NPC tables: [(chapter, name, class, level, source page)]."""
    rows = []
    for page in BOSS_PAGES:
        req = urllib.request.Request('https://serenesforest.net/genealogy-of-the-holy-war/characters/' + page + '/', headers={'User-Agent': 'Mozilla/5.0'})
        text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
        for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
            c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
            if len(c) >= 6 and c[0] != 'Ch' and c[3].isdigit():
                c[1] = c[1].replace('�', 'ä')  # Serenes' Deetäver loses its umlaut in the page's encoding
                ch = BOSS_CHAPTER.get(c[0]) if c[0] in BOSS_CHAPTER else int(c[0]) if c[0].isdigit() else None
                if ch is not None:
                    rows.append((ch, c[1], c[2], int(c[3]), page))
    return rows


def ring_names():
    """Serenes' ring names, for the ROM's ring ids 0x6A upward (the page lists them in the table's order)."""
    req = urllib.request.Request('https://serenesforest.net/genealogy-of-the-holy-war/inventory/items/', headers={'User-Agent': 'Mozilla/5.0'})
    text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    names = []
    for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
        c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
        if len(c) == 4 and c[1].endswith('Ring'):
            names.append(c[1])
    assert len(names) == 16, names
    return {0x6A + i: n for i, n in enumerate(names)}


def build_units(heights, classes):
    """{chapter: (units, reinforcement groups)} from the unit lists, with the armies' relations from each chapter's opening script."""
    cpu = Cpu()
    lists = unit_lists()
    owned = owned_lists()
    items = {m[0]: m[2][1].replace('’', "'") for m in _items().match()}
    items.update(ring_names())
    bosses = boss_rows()
    norm = lambda n: re.sub(r' \([MF]\)$', '', n)
    out = {}
    for chapter, (bank, y) in sorted(chapter_headers().items()):
        relation = opening_relations(cpu, bank, y)
        height = heights[chapter]
        rows = [r for r in bosses if r[0] == chapter]

        def info(rec):
            """(unit id, x, y, flag, army, template) for a record, or None for an empty one."""
            ident = rec[0] | rec[1] << 8
            return (ident, rec[2], rec[3], rec[4], rec[6], character(ident)) if ident else None

        def fields(t):
            kind = t[0]
            return (t[5], t[7], t[10:13]) if kind == 3 else (t[9], t[10], b'') if kind in (0, 2) else (t[1], None, b'')

        # A boss or named foe is a leader (flag 1, or 254 / 255) or a named record whose class and level are a row of Serenes'
        # boss table. When more units fit a row than the table has names, only the flagged leaders take the name.
        candidates = {}
        for k in owned[chapter]:
            for rec in lists[k]:
                d = info(rec)
                if d and d[4] in relation and relation[d[4]] == 1:
                    cls, level, _ = fields(d[5])
                    if level is not None and (d[5][0] != 3 or d[3] in (1, 254, 255)):
                        candidates.setdefault((norm(classes.get(cls, '')), level), []).append(d)
        names_for = {}
        for key, found in candidates.items():
            row_names = sorted({r[1] for r in rows if r[3] == key[1] and norm(r[2]) == key[0]})
            if not row_names:
                continue
            leaders = [d for d in found if d[3] == 1]
            use = found if len(found) <= len(row_names) else leaders if 0 < len(leaders) <= len(row_names) else []
            for d in use:
                names_for[(d[0], d[1], d[2])] = ' / '.join(row_names)

        def make(rec):
            d = info(rec)
            if not d:
                return None
            ident, x, ty, flag, army, t = d
            if army not in relation:
                return None  # your own army's placements aren't shown yet
            cls, level, carried = fields(t)
            klass = classes.get(cls, f'Class {cls}')
            if relation[army] != 1:
                u = {'type': 'ally', 'name': klass, 'tile': [x + 1, height - ty]}
                if relation[army] == 3:
                    u['note'] = 'Neutral: no army is hostile to it.'
                return u
            u = {'type': 'enemy', 'name': klass, 'tile': [x + 1, height - ty]}
            name = names_for.get((ident, x, ty))
            if name:
                u['name'] = name
                u['type'] = 'boss' if flag == 1 else 'named'
                u['note'] = f'{klass}, Lv {level}'
            elif level is not None:
                u['note'] = f'Lv {level}'
            if carried:
                u['carries'] = [items.get(i, f'Item {i}') for i in carried if i != 0xFF]
            return u

        units, groups = [], []
        for k in owned[chapter]:
            made = [u for u in map(make, lists[k]) if u]
            if k in OPENING_LISTS[chapter]:
                units += made
            elif made:
                groups.append({'id': f'list{k}', 'label': f'Group {len(groups) + 1}', 'when': 'Arrives during the chapter; the script that triggers it has not been read yet.', 'units': made})
        out[chapter] = (units, groups)
    return out


def chapter_records():
    out = []
    for i in range(len(CHAPTERS)):
        p = int.from_bytes(R[CHAPTER_TABLE + 3 * i:CHAPTER_TABLE + 3 * i + 3], 'little')
        out.append(R[rom_offset(p):rom_offset(p) + 27])
    return out


def main():
    names = class_names()
    by_type = {}
    for i, n in names.items():
        by_type.setdefault(R[CLASSES + i * 31 + 0x12], []).append(n)
    costs = {t: list(R[MOVE_COSTS + u16(MOVE_COSTS + 2 * t):][:26]) for t in range(15)}
    avoid = [x - 256 if x > 127 else x for x in R[AVOID:AVOID + 26]]

    cpu = Cpu()
    maps = []
    used_ids = set()
    for (map_id, number, heading, title), rec in zip(CHAPTERS, chapter_records()):
        grid64 = np.frombuffer(cpu.decompress(int.from_bytes(rec[0:3], 'little')), dtype='<u2').reshape(64, 64)
        table = np.frombuffer(cpu.decompress(int.from_bytes(rec[24:27], 'little')), dtype='u1')
        width, height = rec[21] * 16, rec[23] * 16
        terrain = table[grid64[:height, :width] & 0x3FF]
        used_ids |= set(np.unique(terrain).tolist())
        unknown = set(np.unique(terrain).tolist()) - set(TERRAIN)
        assert not unknown, (map_id, unknown)
        rows = [''.join(TERRAIN[t][0] for t in row) for row in terrain.tolist()]
        maps.append({
            'id': map_id, 'route': 'Story', 'chapter': number, 'heading': heading, 'title': title, 'width': width, 'height': height,
            'grid': [encode_row('fe4', r) for r in rows], 'victory': '', 'defeat': '', 'objectives': [], 'units': [], 'starts': [],
            'objects': [], 'changes': [], 'notes': [],
        })

    units = build_units({i: m['height'] for i, m in enumerate(maps)}, names)
    for i, m in enumerate(maps):
        m['units'], groups = units[i]
        if groups:
            m['reinforcements'] = groups

    # One terrain entry per code: ids that share a code (Peak and Cliff) must agree.
    info = {}
    for tid, (letter, name) in TERRAIN.items():
        if tid not in used_ids:
            continue
        code = encode_row('fe4', letter)
        move = {}
        for types, label in MOVE_GROUPS:
            col = {costs[t][tid] for t in types}
            assert len(col) == 1, (tid, label, col)
            c = col.pop()
            move[label] = None if c == 0x80 else (0.7 if c == 0 and tid in (15, 25) else c)
        entry = {'name': name, 'def': 0, 'avo': avoid[tid], 'heal': 0, 'move': move}
        if code in info:
            assert {k: v for k, v in info[code].items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}, (code, tid)
            info[code]['name'] = info[code]['name'] + ' / ' + name.lower()
        else:
            info[code] = entry
    info['wn']['note'] = 'No unit can enter it.'
    info['oj']['note'] = 'A unit that stops here can be healed for gold (Serenes Forest: 5 gold per HP).'
    info['tl']['note'] = "The table holds 0 for every walker; the page shows Serenes Forest's 0.7."
    info['tb']['note'] = info['tl']['note']

    examples = {}
    for types, label in MOVE_GROUPS:
        examples[label] = ', '.join(sorted({n for t in types for n in by_type.get(t, [])}))

    lines = [
        "import type { TerrainInfo } from '../maps/fatesTerrain'",
        "import type { TerrainCode } from '../maps/terrainCodes'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's movement cost and avoid tables. Do not edit by hand.",
        ' */',
        '',
        "/** Movement types the game gives different costs: classes in a group pay the same on every terrain. */",
        'export const FE4_MOVE_CLASSES = ' + json.dumps([label for _, label in MOVE_GROUPS]) + ' as const',
        '',
        'export const FE4_MOVE_CLASS_EXAMPLES: Record<string, string> = ' + json.dumps(examples, indent=2, ensure_ascii=False),
        '',
        '/** Avoid and movement cost (null = can\'t enter) by terrain code. No Def bonus is listed: the Serenes damage formula mentions one, but no table for it is found in the ROM. */',
        'export const FE4_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {',
    ]
    for code, entry in info.items():
        lines.append(f'  {code}: {json.dumps(entry, ensure_ascii=False)},')
    lines.append('}')
    with open(os.path.join(OUT_DIR, 'fe4Terrain.ts'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    lines = [
        "import type { ChapterMap } from '../maps/types'",
        "import { FE4_TERRAIN } from './fe4Terrain'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's own chapter records. Do not edit by hand.",
        ' */',
        '',
        'const RAW = [',
    ]
    lines += ['  ' + json.dumps(m, ensure_ascii=False) + ',' for m in maps]
    lines += [']', '', 'export const FE4_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE4_TERRAIN }))']
    with open(os.path.join(OUT_DIR, 'fe4Maps.ts'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(maps), 'maps;', len(info), 'terrain codes;', sorted(used_ids))
    for i, m in enumerate(maps):
        print(i, m['heading'], 'units', len(m['units']), 'groups', len(m.get('reinforcements', [])), 'named', [u['name'] for u in m['units'] if u['type'] in ('boss', 'named')])


if __name__ == '__main__':
    main()

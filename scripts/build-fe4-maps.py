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


if __name__ == '__main__':
    main()

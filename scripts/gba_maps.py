"""
What the maps generators of The Blazing Blade and The Sacred Stones share (scripts/build-fe7-maps.py, build-fe8-maps.py): the terrain
table with its movement types, tile conversions, and writing the generated files. The Binding Blade's generator
(scripts/build-fe6-maps.py) does the same things for its own ROM.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from terrain_codes import encode  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data')

# Terrain ids -> the letters terrain_codes.py maps for 'fe7' and 'fe8' (the same ids as The Binding Blade's, plus the new ones from
# 42 up); ids that work the same share a letter. Names are the app's.
TERRAIN = {
    0: ('#', 'Void'), 1: ('.', 'Plain'), 2: ('.', 'Road'), 3: ('v', 'Village'), 4: ('V', 'Closed village'), 5: ('B', 'House'),
    6: ('W', 'Armory'), 7: ('I', 'Vendor'), 8: ('R', 'Arena'), 10: ('F', 'Fort'), 11: ('g', 'Gate'), 12: ('f', 'Forest'),
    13: ('k', 'Thicket'), 14: ('y', 'Sand'), 15: ('s', 'Desert'), 16: ('w', 'River'), 17: ('m', 'Mountain'), 18: ('P', 'Peak'),
    19: ('b', 'Bridge'), 20: ('b', 'Bridge'), 21: ('a', 'Sea'), 22: ('u', 'Lake'), 23: ('.', 'Floor'), 24: ('q', 'Floor (Res +10)'),
    25: ('l', 'Fence'), 26: ('#', 'Wall'), 27: ('#', 'Wall'), 29: ('p', 'Pillar'), 30: ('d', 'Door'), 31: ('t', 'Throne'),
    32: ('c', 'Chest'), 33: ('c', 'Chest'), 34: ('#', 'Roof'), 35: ('g', 'Gate'), 37: ('n', 'Ruins'), 38: ('C', 'Cliff'),
    39: ('L', 'Ballista'), 40: ('L', 'Long ballista'), 41: ('L', 'Killer ballista'), 42: ('.', 'Flat'), 44: ('#', 'Wall'),
    45: ('S', 'Stairs'), 46: ('C', 'Village wall'), 47: ('.', 'Glacier'), 49: ('z', 'Valley'), 51: ('#', 'Snag'), 53: ('Z', 'Sky'),
    54: ('D', 'Deeps'), 55: ('B', 'Ruins (village)'), 56: ('B', 'Inn'), 57: ('C', 'Barrel'), 58: ('C', 'Bone'), 59: ('x', 'Dark'),
    60: ('u', 'Water'), 61: ('C', 'Gunnel'), 62: ('.', 'Deck'), 63: ('#', 'Brace'), 64: ('#', 'Mast'),
}


def move_groups(r, names):
    """The game's movement types: classes whose cost rows are the same, named by `names` (a class id in the group -> the label).
    Every row must have a name, so a new kind of movement can't go unnoticed."""
    groups = {}
    for c in range(1, r.class_count()):
        if not r.u16(r.cfg['classes'] + 84 * c):
            continue
        row = bytes(r.R[r.class_(c)['move_cost']:r.class_(c)['move_cost'] + r.cfg['terrains']])
        groups.setdefault(row, []).append(c)
    out = []
    for row, classes in groups.items():
        label = next((names[c] for c in classes if c in names), None)
        assert label, f'no name for the movement row of classes {classes}'
        out.append((label, classes, row))
    order = list(dict.fromkeys(names.values()))
    return sorted(out, key=lambda g: order.index(g[0]))


def terrain_table(r, game, used, groups, flier_label='Fliers'):
    """One entry per terrain code: name, Def, Res, Avoid, healing and the cost for each movement type (None: can't enter). Terrain
    stats are the ground rows the first class points at; fliers' rows give no Avoid or Def."""
    lord = r.class_(1)
    info = {}
    for tid in sorted(used):
        letter, name = TERRAIN[tid]
        code = encode(game, letter)
        # 255 is "can't enter"; so is 0 (the Fire Dragon, which never moves, has 0 on a few tiles).
        move = {label: (None if row[tid] in (0, 255) else row[tid]) for label, _, row in groups}
        entry = {'name': name, 'def': r.s8(lord['terrain_def'] + tid), 'res': r.s8(lord['terrain_res'] + tid),
                 'avo': r.s8(lord['terrain_avoid'] + tid), 'heal': r.R[r.cfg['heal'] + tid], 'move': move}
        walkers = [v for k, v in move.items() if k != flier_label]
        if all(v is None for v in walkers):
            entry['def'] = entry['avo'] = 0
        if code in info:
            old = info[code]
            same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}
            nobody = all(v is None for v in move.values())
            assert same or nobody, (code, tid, old, entry)
            if name.lower() not in old['name'].lower():
                old['name'] += ' / ' + name.lower()
        else:
            info[code] = entry
    return info


def flier_rows_are_zero(r, flier_class):
    c = r.class_(flier_class)
    n = r.cfg['terrains']
    return set(r.R[c['terrain_avoid']:c['terrain_avoid'] + n]) == {0} and set(r.R[c['terrain_def']:c['terrain_def'] + n]) == {0}


def to_app(xy, height):
    """A tile from the top-left at (0, 0) -> the app's, from the bottom-left at (1, 1)."""
    return [xy[0] + 1, height - xy[1]]


def rect_to_app(rect, height):
    x1, y1, x2, y2 = rect
    return [x1 + 1, height - y2, x2 + 1, height - y1]


def article(name):
    return ('an ' if name[0].lower() in 'aeiou' else 'a ') + name


def write(game, name, lines):
    out = os.path.join(ROOT, game, name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def write_terrain(game, title, script, info, groups, cls):
    G = game.upper()
    examples = {label: ', '.join(sorted({cls[c] for c in classes if cls.get(c)})) for label, classes, _ in groups}
    lines = [
        "import type { TerrainInfo } from '../maps/fatesTerrain'",
        "import type { TerrainCode } from '../maps/terrainCodes'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s terrain and movement cost tables. Do not edit by hand.",
        ' */',
        '',
        '/** Movement types the game gives different costs: classes in a group pay the same on every terrain. */',
        f'export const {G}_MOVE_CLASSES = ' + json.dumps([label for label, _, _ in groups]) + ' as const',
        '',
        f'export const {G}_MOVE_CLASS_EXAMPLES: Record<string, string> = ' + json.dumps(examples, indent=2, ensure_ascii=False),
        '',
        "/** Def, Res, Avoid, healing and movement cost (null = can't enter) by terrain code. Fliers get no Def or Avoid from terrain. */",
        f'export const {G}_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {{',
    ]
    lines += [f'  {code}: {json.dumps(entry, ensure_ascii=False)},' for code, entry in info.items()]
    lines.append('}')
    write(game, f'{game}Terrain.ts', lines)


def write_maps(game, title, script, maps):
    G = game.upper()
    lines = [
        "import type { ChapterMap } from '../maps/types'",
        f"import {{ {G}_TERRAIN }} from './{game}Terrain'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s own chapter records and events. Do not edit by hand.",
        ' */',
        '',
        'const RAW = [',
    ]
    lines += ['  ' + json.dumps(m, ensure_ascii=False) + ',' for m in maps]
    lines += [']', '', f'export const {G}_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({{ ...m, terrain: {G}_TERRAIN }}))']
    write(game, f'{game}Maps.ts', lines)


def write_sources(game, title, script, sources):
    G = game.upper()
    # What a foe carries is only worth saying where nothing else gives it (it shows who carries a foe-only weapon): thieves steal
    # items, not weapons, so a weapon a foe holds and doesn't drop never reaches you.
    out = {}
    for name, lst in sources.items():
        yours = [s for s in lst if not s['kind'].startswith('foe')]
        out[name] = yours or [{**s, 'kind': s['kind'].replace('-generic', '')} for s in lst]
    lines = [
        "import type { ItemSource } from '../../components/ChapterWeapons'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s event scripts and shop lists. Do not edit by hand.",
        ' */',
        '',
        '/** Where each item turns up, by chapter: shops, chests, villages and houses, hidden spots, talks, what a recruit carries, the',
        " * end of a chapter, and what foes carry ('-later': a foe who arrives mid-chapter, seen from the next chapter). */",
        f'export const {G}_ITEM_SOURCES: Record<string, ItemSource[]> = ' + json.dumps(out, indent=2, ensure_ascii=False),
    ]
    write(game, f'{game}ItemSources.ts', lines)

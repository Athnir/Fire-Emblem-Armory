"""
Builds src/data/maps/gameTerrain.ts from the game's own terrain files: for each map, the tile grid in
the app's terrain letters plus each letter's exact name, Def, Avo, heal and movement costs.

Needs the game files dumped from your own copy into data-raw/fates/romfs/ (git-ignored; see
data-raw/fates/README.md). Run:  python scripts/build-fates-terrain.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_map_convert import parse_tid  # noqa: E402
from fates_movecost import load as load_costs  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_text import read as read_text  # noqa: E402
from fates_tricks import tricks as read_tricks  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameTerrain.ts')

# App map id -> the game's terrain file.
MAPS = {f'fe14-{n}': f'A00{n}' for n in range(1, 6)}
MAPS.update({f'fe14c-{n}': f'B0{n:02d}' for n in range(6, 28)})
MAPS['fe14c-endgame'] = 'B028'

WATER = {'湖', '海', '泉', '氷海', '湖地専', '海の道'}
SKY = {'空', '竜巻', '宇宙'}
LAUNCHER = {'弓砲台': 'L', '魔道砲台': 'O', '暗器砲台': 'U'}
# What a tile turns into after a Dragon Vein (the part after '／' in its terrain name).
AFTER = {'平地': '.', '床': '.', '暗夜床': '.', '回復床': 'H', '回復床50': 'H', '橋': 'b', '空': 'x', '湖': 'a',
         '海': 'a', '河': 'w', '壁': '#', '隆起': '#'}
VEIN, AREA, TOGGLE = 11, 12, 29


def letter(name, qual, cost):
    """Pick the app letter for one terrain kind from its base name and movement-cost class."""
    if name in ('扉', '襖'):
        return 'd'
    if cost in (0, 1, 14, 15):
        return 'D' if name == '水壁' else '#'
    if name in LAUNCHER:
        return LAUNCHER[name]
    if cost in (2, 12, 13):
        if name == '宝箱':
            return 'c'
        if name in WATER:
            return 'a'
        if name in SKY:
            return 'x'
        if name in ('低壁',):
            return 'l'
        if name in ('崖', '高山'):
            return 'C'
        if name in ('深い森',):
            return 'k'
        if name in ('建物', '低建物'):
            return 'B'
        return 'r'
    if cost == 3:
        return 'z'
    if cost == 4:
        return {'階段': 'S', '門口': 'e', '村': 'v', '廃村': 'V', '閉じ村': 'V', '剣の間': 'j', '回復床': 'H',
                '橋': 'b', '扉': 'd', '襖': 'd'}.get(name, '.')
    if cost == 5:
        return 'f'
    if cost == 6:
        return 'T' if name == '撒菱' else 'p'
    if cost == 8:
        return 'n' if '山' in name else 'W'
    if cost == 9:
        return 'w'
    if cost == 10:
        return {'砦': 'F', '済砦': 'F', '座布団': 'Q', '廃墟門': 'G', '城門': 'g', '玉座': 't'}.get(name, 'F')
    return '?'


def signed(b):
    return b - 256 if b & 0x80 else b


def main():
    text = read_text(os.path.join(RAW, 'm', '@E', 'GameData.bin.lz'))
    costs = load_costs(os.path.join(RAW, 'GameData.bin.lz'))
    out = {}
    for map_id, code in MAPS.items():
        t = read_terrain(os.path.join(RAW, 'Terrain', code + '.bin.lz'))
        W, H = t['w'] - 2, t['h'] - 2
        kinds = {}
        rows = []
        afters = {}
        for r in range(1, t['h'] - 1):
            row = ''
            for c in range(1, t['w'] - 1):
                ty = t['types'][t['rows'][r][c]]
                name, after, broken, vein, qual = parse_tid(ty['tid'])
                barrier = name == '防壁'
                if barrier:
                    name, after = '床', '壁'  # Endgame barriers: floor until a vein raises them
                r4 = ty['raw'][4]
                cost = r4 & 0xFF
                L = '.' if barrier else letter(name, qual, cost)
                frozen = name == '湖地専'
                if frozen:
                    # Conquest 8's frozen lake: ground units walk on it until a vein melts it into lake.
                    L, cost, after = 'i', 4, '湖'
                if L == '?':
                    raise SystemExit(f'{code}: no letter for {ty["tid"]} (cost class {cost})')
                en = 'Frozen lake' if frozen else text.get('MTID_' + name, name)
                if name in ('良薬', '劇薬'):
                    en, cost, L = 'Floor', 4, '.'  # pots are objects; the floor under them is what's left
                info = {'name': en, 'def': signed(r4 >> 8 & 0xFF), 'avo': signed(r4 >> 16 & 0xFF),
                        'heal': signed(r4 >> 24 & 0xFF), 'move': costs(cost)}
                if name in ('良薬', '劇薬'):
                    info.update({'def': 0, 'avo': 0, 'heal': 0})
                if barrier:
                    info.update({'def': 0, 'avo': 0, 'heal': 0, 'move': costs(4)})
                A = AFTER.get((after or '').replace('＃竜脈', ''))
                if A and A != L and name not in ('扉', '襖'):
                    afters[(c, H + 1 - r)] = A
                prev = kinds.get(L)
                if prev and (prev['def'], prev['avo'], prev['heal'], prev['move']) != (info['def'], info['avo'], info['heal'], info['move']):
                    raise SystemExit(f'{code}: letter {L} covers two different terrains: {prev} / {info}')
                if not prev:
                    kinds[L] = prev = dict(info, names={})
                prev['names'][en] = prev['names'].get(en, 0) + 1
                row += L
            rows.append(row)
        for info in kinds.values():
            names = sorted(info.pop('names').items(), key=lambda kv: -kv[1])
            # Walls keep the commonest name; walkable kinds list each name (e.g. "Plain / Floor").
            info['name'] = names[0][0] if len(names) == 1 or info['move']['Fliers'] is None else ' / '.join(n for n, _ in names)
        veins = []
        script = os.path.join(RAW, 'Scripts', code + '_Terrain.cmb')
        tr = [x for x in read_tricks(script) if max(x) < 100] if os.path.exists(script) else []
        vtiles = [(x, H + 1 - y) for x, y, w, h, k in tr if k == VEIN]
        mine = {v: set() for v in vtiles}

        def cells(x, y, w, h):
            return {(x + i, y - j) for i in range(w) for j in range(h)}

        def dist(v, cs):
            return min(abs(v[0] - a) + abs(v[1] - b) for a, b in cs)
        # Areas follow the vein(s) they belong to: one vein -> its own area; a run of veins followed by
        # fewer areas (or single-tile ones) -> they share them; otherwise each area goes to its nearest vein.
        has_toggles = any(k == TOGGLE for *_, k in tr)
        groups, run, areas = [], [], []
        for x, y, w, h, k in tr:
            if k == VEIN:
                if areas:
                    groups.append((run, areas))
                    run, areas = [], []
                run.append((x, H + 1 - y))
            elif k == (TOGGLE if has_toggles else AREA) and run:
                areas.append(cells(x, H + 1 - y, w, h))
        if run:
            groups.append((run, areas))
        for run, areas in groups:
            if not areas:
                continue
            if len(run) == 1 or len(areas) == 1 or all(len(cs) == 1 for cs in areas):
                for v in run:
                    for cs in areas:
                        mine[v] |= cs
            else:
                for cs in areas:
                    mine[min(run, key=lambda v: dist(v, cs))] |= cs
        if len(vtiles) == 1 and not mine[vtiles[0]]:
            mine[vtiles[0]] = set(afters)
        for v in vtiles:
            patch = sorted(((t, afters[t]) for t in mine[v] if t in afters), key=lambda p: (-p[0][1], p[0][0]))
            veins.append({'tile': v, 'patch': patch})
        out[map_id] = {'code': code, 'veins': veins, 'width': W, 'height': H, 'grid': rows, 'terrain': kinds}

    lines = [
        "import type { TerrainInfo } from './fatesTerrain'",
        "import type { TerrainLetter, Tile } from './types'",
        '',
        '/*',
        ' * GENERATED by scripts/build-fates-terrain.py from the game\'s own terrain files. Do not edit by hand:',
        ' * fix the generator (or the per-map data that uses it) and re-run it.',
        ' *',
        " * Each map's grid (top row first) in the app's terrain letters, and each letter's exact terrain",
        " * on that map: the game's English name, Def, Avo, heal % and movement costs.",
        ' */',
        'export interface GameTerrain {',
        '  code: string',
        '  width: number',
        '  height: number',
        '  grid: string[]',
        '  /** Every Dragon Vein tile, with the tiles it reshapes (empty when it changes no terrain). */',
        '  veins: { tile: Tile; patch: { tile: Tile; becomes: TerrainLetter }[] }[]',
        '  terrain: Partial<Record<TerrainLetter, TerrainInfo>>',
        '}',
        '',
        'export const GAME_TERRAIN: Record<string, GameTerrain> = {',
    ]
    for map_id, m in out.items():
        lines.append(f"  '{map_id}': {{")
        lines.append(f"    code: '{m['code']}',")
        lines.append(f"    width: {m['width']},")
        lines.append(f"    height: {m['height']},")
        lines.append('    grid: [')
        for i, row in enumerate(m['grid']):
            lines.append(f"      '{row}', // {m['height'] - i}")
        lines.append('    ],')
        lines.append('    veins: [')
        for v in m['veins']:
            patch = ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in v['patch'])
            lines.append(f"      {{ tile: [{v['tile'][0]}, {v['tile'][1]}], patch: [{patch}] }},")
        lines.append('    ],')
        lines.append('    terrain: {')
        for L, info in sorted(m['terrain'].items()):
            key = L if L.isalpha() else json.dumps(L)
            move = ', '.join(f"{json.dumps(k) if ' ' in k else k}: {json.dumps(v)}" for k, v in info['move'].items())
            lines.append(f"      {key}: {{ name: {json.dumps(info['name'])}, def: {info['def']}, avo: {info['avo']}, heal: {info['heal']}, move: {{ {move} }} }},")
        lines.append('    },')
        lines.append('  },')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out), 'maps')


if __name__ == '__main__':
    main()

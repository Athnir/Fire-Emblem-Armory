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
from fates_maps import MAPS, PACK, terrain, terrain_script, text_for  # noqa: E402
from fates_movecost import load as load_costs  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_tricks import tricks as read_tricks  # noqa: E402
from fates_cmb import Script  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameTerrain.ts')


WATER = {'湖', '海', '泉', '氷海', '湖地専', '海の道', '湖配置'}
SKY = {'空', '竜巻', '宇宙'}
LAUNCHER = {'弓砲台': 'L', '魔道砲台': 'O', '暗器砲台': 'U'}
# What a tile turns into after a Dragon Vein (the part after '／' in its terrain name).
AFTER = {'平地': '.', '床': '.', '暗夜床': '.', '回復床': 'H', '回復床50': 'H', '橋': 'b', '空': 'x', '湖': 'a',
         '海': 'a', '河': 'w', '壁': '#', '隆起': '#', '砦': 'F', '済砦': 'F', '宝箱': 'c', '林': 'f', '建物': 'B',
         '太柱': '#', '氷丘': 'f', '海の道': '.', '氷結泉': '.', '魔方陣': '.', '竜巻': 'z', '嵐': 'z',
         '毒沼配置': 'P', '宇宙': 'x'}
VEIN, AREA, TOGGLE = 11, 12, 29
# Terrain that can be broken down by attacking it (its name has a '｜' part saying what it becomes).
BREAKABLE = {'壁', '低壁', '建物', '古木', '土塁', '防壁'}


def letter(name, qual, cost):
    """Pick the app letter for one terrain kind from its base name and movement-cost class."""
    if name in ('扉', '襖'):
        return 'd'
    if cost in (0, 1, 14, 15):
        return {'水壁': 'D', '瘴気': 'D', '闇': 'X'}.get(name, '#')
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
        if name.startswith('毒沼'):
            return 'P'
        return {'段差': 'E', '亀裂': 'Z', '階段': 'S', '門口': 'e', '村': 'v', '廃村': 'V', '閉じ村': 'V', '剣の間': 'j', '回復床': 'H',
                '橋': 'b', '扉': 'd', '襖': 'd', '守護床': 'K'}.get(name, '.')
    if cost == 5:
        return 'M' if name == '熱水泉' else 'f'
    if cost == 6:
        return {'撒菱': 'T', '水たまり': 'u'}.get(name, 'p')
    if cost == 7:
        return 's'
    if cost == 8:
        return 'n' if '山' in name or name == '石垣' else 'W'
    if cost == 9:
        return 'w'
    if cost == 10:
        return {'砦': 'F', '済砦': 'F', '穴': 'F', '座布団': 'Q', '廃墟門': 'G', '城門': 'g', '玉座': 't',
                '召喚床': 'Y'}.get(name, 'F')
    return '?'


def signed(b):
    return b - 256 if b & 0x80 else b


def main():
    costs = load_costs(os.path.join(RAW, 'GameData.bin.lz'))
    out = {}
    for map_id, (code, _, _) in MAPS.items():
        pack = PACK.get(map_id)
        text = text_for(pack)
        t = read_terrain(terrain(code, pack))
        W, H = t['w'] - 2, t['h'] - 2
        kinds = {}
        rows = []
        afters = {}
        breaks = {}
        knock_on = {}
        dark = []
        for r in range(1, t['h'] - 1):
            row = ''
            for c in range(1, t['w'] - 1):
                ty = t['types'][t['rows'][r][c]]
                name, after, broken, vein, qual = parse_tid(ty['tid'])
                if name == '闇' and after:
                    # Revelation's darkness: the map keeps the terrain underneath, shaded until it lifts.
                    under = next((u for u in t['types'] if parse_tid(u['tid'])[0] == after), None)
                    if under:
                        dark.append((c, H + 1 - r))
                        ty = under
                        name, after, broken, vein, qual = parse_tid(ty['tid'])
                barrier = name == '防壁'
                if barrier:
                    name, after = '床', '壁'  # Endgame barriers: floor until a vein raises them
                r4 = ty['raw'][4]
                cost = r4 & 0xFF
                L = '.' if barrier else letter(name, qual, cost)
                frozen = name == '湖地専' and code == 'B008'
                if frozen:
                    # Conquest 8's frozen lake: ground units walk on it until a vein melts it into lake. Birthright
                    # 17 shares the map, but there it starts as lake and the vein freezes it.
                    L, cost, after = 'i', 4, '湖'
                if L == '?':
                    raise SystemExit(f'{code}: no letter for {ty["tid"]} (cost class {cost})')
                # The game calls both rivers (河) and puddles (水たまり) 'Water'; the puddles get their own name.
                en = 'Frozen lake' if frozen else 'Shallow water' if name == '水たまり' else text.get('MTID_' + name) or text.get('MTID_' + name.replace('配置', '')) or \
                    ('Acid Bog' if name.startswith('毒沼') else 'Floor' if name == '障壁用床' else name)
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
                # '｜' names what a tile becomes once broken: walls, partitions, buildings, an old tree, an earthwork.
                B = AFTER.get(broken or '') or {'段差': 'E'}.get(broken or '')
                if name in BREAKABLE and B and B != L:
                    breaks[(c, H + 1 - r)] = B
                elif B and B != L and name not in ('扉', '襖', '良薬', '劇薬') and not barrier:
                    knock_on[(c, H + 1 - r)] = B  # changes when something nearby breaks (the river under Conquest 19's tree)
                prev = kinds.get(L)
                blocked = all(v is None for v in info['move'].values())
                # Nothing can enter either: they're one obstacle, whatever bonuses the game lists on them.
                if prev and not blocked and (prev['def'], prev['avo'], prev['heal'], prev['move']) != (info['def'], info['avo'], info['heal'], info['move']):
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
        script = terrain_script(code, pack)
        tr = [x for x in read_tricks(script) if max(x) < 100] if script else []
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
        # A breakable tile's HP sits on the terrain-script trick that covers it (args: x, y, w, h, kind, HP).
        hp = {}
        if script:
            for h in Script(script).handlers():
                a = h['args']
                if len(a) >= 6 and a[4] in (0, 9) and 0 < a[5] < 1000 and max(a[:4]) < 100:
                    for i in range(a[2]):
                        for j in range(a[3]):
                            hp[(a[0] + i, H + 1 - (a[1] + j))] = a[5]
        breakables = [{'tile': t, 'becomes': b, 'also': [], **({'hp': hp[t]} if t in hp else {})}
                      for t, b in sorted(breaks.items(), key=lambda kv: (-kv[0][1], kv[0][0]))]
        # A tile that changes once something breaks goes with the nearest breakable (within 3 tiles).
        for t, b in knock_on.items():
            near = min(breakables, key=lambda x: abs(x['tile'][0] - t[0]) + abs(x['tile'][1] - t[1]), default=None)
            if near and abs(near['tile'][0] - t[0]) + abs(near['tile'][1] - t[1]) <= 3:
                near['also'].append((t, b))
        out[map_id] = {'code': code, 'dark': dark, 'breakables': breakables, 'veins': veins, 'width': W, 'height': H, 'grid': rows, 'terrain': kinds}

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
        "  /** Tiles under Revelation's darkness: impassable, and shown shaded, until the chapter lifts it. */",
        '  dark?: Tile[]',
        '  /** Walls, partitions and the like that can be attacked down: what each becomes, and its HP when the game sets one. */',
        '  breakables?: { tile: Tile; becomes: TerrainLetter; hp?: number; also?: { tile: Tile; becomes: TerrainLetter }[] }[]',
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
        if m['breakables']:
            lines.append('    breakables: [' + ', '.join(
                f"{{ tile: [{b['tile'][0]}, {b['tile'][1]}], becomes: {json.dumps(b['becomes'])}" + (f", hp: {b['hp']}" if 'hp' in b else '')
                + (', also: [' + ', '.join(f'{{ tile: [{x}, {y}], becomes: {json.dumps(a)} }}' for (x, y), a in b['also']) + ']' if b['also'] else '') + ' }'
                for b in m['breakables']) + '],')
        if m['dark']:
            lines.append('    dark: [' + ', '.join(f'[{x}, {y}]' for x, y in m['dark']) + '],')
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

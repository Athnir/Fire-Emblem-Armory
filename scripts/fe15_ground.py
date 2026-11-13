"""
Each Echoes map's ground, read from its 3D field (scripts/fe15_art.py): its colour per code and the plain tiles its art draws as dirt
(ds_art's two looks), written to data-raw/fe15-ground.json for scripts/build-fe15-maps.py to apply (the render takes a few seconds a
map, so it runs on its own; rerun it when the maps' fields or grids change).

Which field and terrain window each app map is drawn from: build-fe15-maps.py's own map builders, run read-only (its main(), which
writes, isn't called), with grid() and battle_map() wrapped to note each map's terrain file and battle.

    python scripts/fe15_ground.py            # every map
    python scripts/fe15_ground.py fe15-1-1   # some (the others kept)
"""
import importlib.util
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ds_art  # noqa: E402
import fe15_art  # noqa: E402
from terrain_codes import encode  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe15-ground.json')
# The codes each map colours from its art: plain, dirt, paving, floor, snow, deck, sand, river, sea, peaks and cliffs, castle walls,
# rock, castle floors, ramparts, and the burning ground and mires.
COLOURED = {'t0', 'ga', 'gb', 't1', 't2', 't3', 'td', 'tg', 'we', 'wb', 'w0', 'wt', 'b0', 'wx', 'dd'}

spec = importlib.util.spec_from_file_location('build_fe15_maps', os.path.join(HERE, 'build-fe15-maps.py'))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class _Tagged(list):
    key = None


_grid, _rows, _battle = B.grid, B.grid_rows, B.battle_map
WINDOW, BATTLE = {}, {}


def _tag_grid(key):
    win, g = _grid(key)
    g = _Tagged(g)
    g.key = key
    WINDOW[key] = tuple(win)
    return win, g


def _tag_rows(win, g):
    r = _Tagged(_rows(win, g))
    r.key = getattr(g, 'key', None)
    return r


def _tag_battle(mid, key, *a, **k):
    m = _battle(mid, key, *a, **k)
    BATTLE[mid] = key
    return m


B.grid, B.grid_rows, B.battle_map = _tag_grid, _tag_rows, _tag_battle


def maps():
    """[(app map, terrain window, field)] for every map the builder makes."""
    facts = defaultdict(lambda: defaultdict(list))
    counters = defaultdict(int)
    out = []
    for act, route, kind, key in B.STORY + B.SIDE:
        ck = (act if route != 'Extra' or act == 6 else 'x', route if act in (3, 4) else '')
        counters[ck] += 1
        n = counters[ck]
        mid = B.map_id(act, route, n, key)
        if kind == 'battle':
            ms = [B.battle_map(mid, key, B.battle_title(key) or B.place(key), f'Act {act}' if act else 'Prologue', n, route,
                               B.place(key), facts[mid])]
            if key in B.RETURNS:
                ms.append(B.returns_map(ms[0], key, B.RETURNS[key], lambda m_: facts[m_]))
        elif kind == 'cemetery':
            ms = B.cemetery_maps(mid, key, act, route, n, lambda m_: facts[m_])
        else:
            ms = B.dungeon_maps(mid, n, act, route, key, lambda m_: facts[m_])
        for m in ms:
            tkey = getattr(m['grid'], 'key', None)
            row = B.FIELDS.get(BATTLE[m['id']]) if m['id'] in BATTLE else None
            if row is None or row.get('フィールド名') is None:
                row = next((r for r in B.FIELDS.values() if r.get('地形データ名') == tkey and r.get('種類') == 4), None) or \
                    next((r for r in B.FIELDS.values() if r.get('地形データ名') == tkey), None) or B.FIELDS.get(tkey)
            out.append((m, WINDOW.get(tkey), row['フィールド名'] if row else None))
    return out


def ground(m, window, field):
    """{'fills': {code: colour}, 'dirt': [[x, y], ...]} for an app map."""
    codes = [[encode('fe15', c) for c in row] for row in m['grid']]
    px = fe15_art.render(field, window)
    dirt = ds_art.dirt_of(px, codes)
    for r, c in dirt:
        codes[r][c] = 'ga'
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED)
    h = len(codes)
    return {'fills': fills, 'dirt': sorted([c + 1, h - r] for r, c in dirt)}


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for m, window, field in maps():
        if (only and m['id'] not in only) or not field or not window:
            continue
        table[m['id']] = ground(m, window, field)
        print(m['id'], field, len(table[m['id']]['dirt']), 'dirt', table[m['id']]['fills'])
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])

"""
A map's ground from its rendered art, applied to its built grid: the 3D games whose renders take minutes (Echoes:
scripts/fe15_ground.py; Awakening: scripts/fe13_ground.py) write each map's colour per code and the plain tiles its art draws as dirt
to data-raw/<game>-ground.json, and their builders apply it here. A dirt-sorted plain tile takes the dirt code (`ga`) but keeps the
game's name for it (the tile panel says what the game says), and a return visit's map is its own (no override shared with its first).
"""
import json
import os
from collections import defaultdict

_TABLES = {}


def table(path):
    if path not in _TABLES:
        _TABLES[path] = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    return _TABLES[path]


def names_at(m, code, rows, own_name):
    """{name: [tiles]} for a code's tiles on a map, by its overrides (the most common name first) or the code's own name."""
    h = len(rows)
    tiles = [[x + 1, h - r] for r, row in enumerate(rows) for x, c in enumerate(row) if c == code]
    over = m.get('terrainOverrides', {}).get(code)
    if not over:
        return {own_name(code): tiles} if tiles else {}
    others = over.get('tileNames', {})
    taken = {tuple(t) for ts in others.values() for t in ts}
    return {over['name'].split(' / ')[0]: [t for t in tiles if tuple(t) not in taken], **others}


def name_over(m, code, names, own_name):
    """Sets a code's names on a map: an override where they aren't just the code's own."""
    names = {k: v for k, v in names.items() if v}
    order = sorted(names, key=lambda k: (-len(names[k]), k))
    over = m.setdefault('terrainOverrides', {})
    if not order or order == [own_name(code)]:
        over.pop(code, None)
    else:
        over[code] = {'name': ' / '.join(order), **({'tileNames': {k: names[k] for k in order[1:]}} if len(order) > 1 else {})}


def apply(m, g, own_name, plain='t0', dirt='ga'):
    """Applies a map's entry `g` ({'fills', 'dirt': [[x, y]], 'dirtAs': the code its paler look takes, when it isn't dirt: a snowy
    map's snow, `t2`}) to an encoded map `m`. `own_name(code)` a code's own name."""
    m['terrainOverrides'] = dict(m.get('terrainOverrides') or {})
    if not g:
        return m
    dirt = g.get('dirtAs', dirt)
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    h = len(rows)
    before_plain, before_dirt = names_at(m, plain, rows, own_name), names_at(m, dirt, rows, own_name)
    tiles = {tuple(t) for t in g['dirt'] if rows[h - t[1]][t[0] - 1] == plain}
    for x, y in tiles:
        rows[h - y][x - 1] = dirt
    moved = defaultdict(list)
    for name, ts in before_plain.items():
        moved[name] += [t for t in ts if tuple(t) in tiles]
        before_plain[name] = [t for t in ts if tuple(t) not in tiles]
    for name, ts in moved.items():
        before_dirt[name] = before_dirt.get(name, []) + ts
    m['grid'] = [''.join(r) for r in rows]
    name_over(m, plain, before_plain, own_name)
    name_over(m, dirt, before_dirt, own_name)
    m['fills'] = g['fills']
    return m

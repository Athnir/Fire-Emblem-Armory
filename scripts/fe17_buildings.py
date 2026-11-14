"""
What each Engage map's buildings are (its 'Edifice' tiles, `oe`), read from its battle scene (scripts/fe17_art.py): the scene's models
standing on each block of them, by their names (FileneHouseA, WindMillA, Yurt, FortWall, BuildingBreakA, WoodBoxA...), written to
data-raw/fe17-buildings.json for scripts/build-fe17-maps.py to draw each building as itself (the user's calls, the review of every
map: houses, windmills, yurts, forts and ruins, not blocks of wall). Scenes take half a minute each to load, so it runs on its own, on
the maps the builder last wrote; rerun it, then the builder, when the maps' grids change.

    python scripts/fe17_buildings.py              # every map
    python scripts/fe17_buildings.py fe17-m004    # some (the others kept)
"""
import collections
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fe17_art  # noqa: E402
import fe17_data as D  # noqa: E402
import fe17_ground as G  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe17-buildings.json')
# Models too small to say what a building is (the ground's dressing), left out.
PROP = re.compile(r'pebble|rock|bush|grass|tree|stump|leaf|flower|weed|moss|plant|fern|branch|root|mesh$|polysurface', re.I)
# A block's kind by the names of the models on it, the first that matches (a windmill's fence and wings are a windmill's).
KINDS = [
    ('windmill', re.compile(r'windmill', re.I)),
    ('yurt', re.compile(r'yurt', re.I)),
    ('fort', re.compile(r'fort|tower|castle', re.I)),
    ('ruins', re.compile(r'ruin|brick|buildingbreak', re.I)),
    ('house', re.compile(r'house', re.I)),
    # A market's goods (Engage's desert towns): vases, sacks, baskets, shelves and food laid out.
    ('stall', re.compile(r'storage|shelf|vase|basket|bag|foods|stand|stall', re.I)),
    ('crates', re.compile(r'box|barrel|crate|cargo', re.I)),
]
CACHE = os.path.join(HERE, '..', 'data-raw', 'fe17', 'romfs', 'art-cache')


def kind_of(names):
    for kind, pattern in KINDS:
        if any(pattern.search(n) for n in names):
            return kind
    return None


def tile_names(map_id, m, scene, window):
    """{"x,y": {model name: count}} over a map's Edifice tiles, kept in the art cache (a scene takes half a minute to load)."""
    path = os.path.join(CACHE, f'names-{map_id}.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    x1, z1 = window[0], window[1]
    w, h = m['width'], m['height']
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    edifice = {(x + 1, h - y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == 'oe'}
    names = collections.defaultdict(collections.Counter)
    for name, _, P, _, tri in scene().renderers():
        c = P[np.unique(tri)].mean(0)
        t = (int(c[0] // 5) - x1 + 1, int(c[2] // 5) - z1 + 1)
        if t in edifice and not PROP.search(name):
            names[f'{t[0]},{t[1]}'][re.sub(r'(_LOD\d+|\s*\(\d+\)|[\s_]\d+)+$', '', name)] += 1
    os.makedirs(CACHE, exist_ok=True)
    json.dump(names, open(path, 'w', encoding='utf-8'))
    return names


def buildings(map_id, m, scene, window):
    """[{'tiles': [[x, y]...], 'kind', 'names'}] for each block of a map's Edifice tiles."""
    w, h = m['width'], m['height']
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    edifice = {(x + 1, h - y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == 'oe'}
    names = tile_names(map_id, m, scene, window)
    out, seen = [], set()
    for start in sorted(edifice):
        if start in seen:
            continue
        comp, todo = set(), [start]
        while todo:
            p = todo.pop()
            if p in comp or p not in edifice:
                continue
            comp.add(p)
            todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
        seen |= comp
        agg = collections.Counter()
        for p in comp:
            agg.update(names.get(f'{p[0]},{p[1]}', {}))
        out.append({'tiles': sorted([list(p) for p in comp]), 'kind': kind_of(agg), 'names': [n for n, _ in agg.most_common(4)]})
    return out


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    chapters = {r['Cid']: r for r in D.rows('chapter')}
    scenes = {}
    for map_id, m in G.app_maps().items():
        if (only and map_id not in only) or not m['grid'] or not any('oe' in r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)):
            continue
        field, window = G.field_and_window(map_id, chapters)
        if not os.path.exists(os.path.join(fe17_art.ART, f'fe_scenes_fld_{field}.bundle')):
            print(map_id, 'no scene for', field)
            continue
        def scene(field=field):
            if field not in scenes:
                scenes.clear()
                scenes[field] = fe17_art.Scene(field)
            return scenes[field]
        table[map_id] = buildings(map_id, m, scene, window)
        print(map_id, field, collections.Counter(b['kind'] for b in table[map_id]), flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])

"""
What each Engage map's buildings are (its 'Edifice' tiles, `oe`), read from its battle scene (scripts/fe17_art.py): the scene's models
standing on each block of them, by their names (FileneHouseA, WindMillA, Yurt, FortWall, BuildingBreakA, WoodBoxA...), written to
data-raw/fe17-buildings.json for scripts/build-fe17-maps.py to draw each building as itself (the user's calls, the review of every
map: houses, windmills, yurts, forts and ruins, not blocks of wall). Scenes take half a minute each to load, so it runs on its own, on
the maps the builder last wrote; rerun it, then the builder, when the maps' grids change.

    python scripts/fe17_buildings.py              # every map
    python scripts/fe17_buildings.py fe17-m004    # some (the others kept)
    python scripts/fe17_buildings.py --houses fe17-m019 fe17-m019-sk    # their house blocks parted into the scene's houses
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


def house_footprints(map_id, m, scene, window):
    """[{'name', 'tiles'}]: each house model the scene stands on the map, the tiles whose centres its ground plan covers (one tile past
    the map's edge at most, where the builder draws a house the edge cuts), a model's LODs and parts merged into the house they belong
    to; kept in the art cache."""
    path = os.path.join(CACHE, f'houses-{map_id}.json')
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    x1, z1 = window[0], window[1]
    w, h = m['width'], m['height']
    # A house's parts (its walls, roof, front and door, each a model of its own in Chapter 6's Filene houses) gathered under the house
    # they belong to: the furthest of a part's ancestors named a house (Chapter 6's FileneHouseA_Break_M006(2)), not a group of them
    # ("House", "Grp_House", "Grp_IrcionHouseA"), else the part itself; its plan the parts' together.
    extent = {}
    for name, _, P, _, tri, owners in scene().renderers(owners=True):
        houses = [a for a in owners if re.search(r'house', a[1], re.I) and not re.match(r'\s*(grp|group)|\s*houses?\s*$', a[1], re.I)]
        if not (houses or re.search(r'house', name, re.I)):
            continue
        key = houses[-1] if houses else (id(P), name)
        V = P[np.unique(tri)]
        lo, hi = V.min(0) / 5, V.max(0) / 5
        label = houses[-1][1] if houses else name
        if key in extent:
            _, lo0, hi0 = extent[key]
            lo, hi = np.minimum(lo, lo0), np.maximum(hi, hi0)
        extent[key] = (label, lo, hi)
    found = []
    for label, lo, hi in extent.values():
        xs = range(int(np.ceil(lo[0] - 0.5)) - x1 + 1, int(np.floor(hi[0] - 0.5)) - x1 + 2)
        zs = range(int(np.ceil(lo[2] - 0.5)) - z1 + 1, int(np.floor(hi[2] - 0.5)) - z1 + 2)
        tiles = {(x, z) for x in xs for z in zs if 0 <= x <= w + 1 and 0 <= z <= h + 1}
        # No house runs more than seven tiles: what does is a town's wall the scene names a house's (Chapter 19's HouseWallA, the
        # length of its town), which would swallow the houses in its outline.
        if len(xs) and len(zs) and tiles and max(len(xs), len(zs)) <= 7:
            found.append((re.sub(r'(_LOD\d+|\s*\(\d+\)|[\s_]\d+)+$', '', label), tiles))
    kept = []
    for name, tiles in sorted(found, key=lambda f: -len(f[1])):
        if not any(len(tiles & k) >= 0.6 * len(tiles) for _, k in kept):
            kept.append((name, tiles))
    out = [{'name': n, 'tiles': sorted([list(t) for t in k])} for n, k in kept]
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(path, 'w', encoding='utf-8'))
    return out


def add_houses(map_id, m, scene, window, blocks):
    """Each house block's houses as the scene stands them (`houses`: each house model's tiles on the block, and past the map's edge),
    and what stands on its other tiles (`between`: {"x,y": kind}, its crates and the like) (the user, Chapter 19's town: 'way too many
    tiles for villages together, instead of where they should be split to different houses')."""
    w, h = m['width'], m['height']
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    names = tile_names(map_id, m, scene, window)
    feet = house_footprints(map_id, m, scene, window)
    for b in blocks:
        if b['kind'] != 'house':
            continue
        tiles = {tuple(t) for t in b['tiles']}
        houses = []
        for f in feet:
            ft = {tuple(t) for t in f['tiles']}
            on = ft & tiles
            if on:
                # Its plan's tiles past the map's edge, and its obstacles no unit enters under its roof (Chapter 19's (11, 17): the
                # user, "a roof tile to make a full 3x3 house").
                past = {t for t in ft - tiles if not (1 <= t[0] <= w and 1 <= t[1] <= h) or rows[h - t[1]][t[0] - 1] in ('wa', 'wj')}
                houses.append(sorted([list(t) for t in on | past]))
        covered = {tuple(t) for hs in houses for t in hs}
        b['houses'] = houses
        b['between'] = {f'{x},{y}': kind_of(names.get(f'{x},{y}', {})) for x, y in sorted(tiles - covered)}


def main(only):
    if only[:1] == ['--houses']:
        # The houses of maps whose house blocks are already read, from the blocks kept (the builder has since drawn those tiles as
        # houses, so the grid no longer shows them as Edifice).
        table = json.load(open(OUT, encoding='utf-8'))
        chapters = {r['Cid']: r for r in D.rows('chapter')}
        maps = G.app_maps()
        scenes = {}
        for map_id in only[1:]:
            field, window = G.field_and_window(map_id, chapters)
            def scene(field=field):
                if field not in scenes:
                    scenes.clear()
                    scenes[field] = fe17_art.Scene(field)
                return scenes[field]
            add_houses(map_id, maps[map_id], scene, window, table[map_id])
            print(map_id, [len(b['houses']) for b in table[map_id] if b['kind'] == 'house'], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)
        return
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

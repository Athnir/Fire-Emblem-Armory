"""
Each Fates map's ground, read from its 3D field (scripts/fates_art.py): its colour per code and the plain tiles its art draws as dirt
(sorted by hue, below), written to data-raw/fates-ground.json for scripts/build-fates-terrain.py to apply. Renders take a few seconds a
map, so it runs on its own, on the grids the builder last wrote (src/data/maps/gameTerrain.ts); rerun it, then the builder, when the
grids change.

Dirt is sorted by hue, not lightness: Fates' fields carry their shadows and sunlit patches in their art, so a sunlit stretch of grass
is as pale as a path. A pixel's warmth (red over green) and yellowness (green over blue), each over its brightest channel, hold under
shade; the plain's pixels part into the grass's look and a warmer, greyer one, and a plain tile is dirt where most of its pixels take
the second. Water keeps the app's colour unless its render is blue: Fates draws it as a dark tint of a land reflection map with a sky
reflection the render leaves out, so on many maps it comes out olive or teal. Renders are kept in data-raw/fates/romfs/art-cache
(git-ignored); delete it when the art or the renderer changes.

    python scripts/fates_ground.py            # every map
    python scripts/fates_ground.py fe14b-6    # some (the others kept)
"""
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_ground  # noqa: E402
import ds_art  # noqa: E402
import fates_art  # noqa: E402
import fates_maps as FM  # noqa: E402
import fates_terrain as FT  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fates-ground.json')
CACHE = os.path.join(HERE, '..', 'data-raw', 'fates', 'romfs', 'art-cache')
GRIDS = os.path.join(HERE, '..', 'src', 'data', 'maps', 'gameTerrain.ts')
PX = 24
PLAIN, DIRT = 'ta', 'ga'   # Fates' plain keeps its code ('ta': the hand-built chapters patch tiles to it)
# The codes each map colours from its art: plain, dirt, floor, wasteland, sand, its waters, cliffs, walls.
COLOURED = {'ta', 'ga', 't1', 'te', 'td', 'tf', 'we', 'wm', 'wb', 'wa'}
WATER = ('tf', 'we', 'wm')
def grids():
    src = open(GRIDS, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r"\n  '([^']+)': \{\n    code: '([^']+)',\n(?:    fills: .*\n)?    width: (\d+),\n    height: (\d+),\n    grid: \[\n"
                         r"((?:      '[^']*',.*\n)+)", src):
        rows = re.findall(r"'([^']*)'", m.group(5))
        out[m.group(1)] = {'width': int(m.group(3)), 'height': int(m.group(4)),
                           'grid': [[PLAIN if c == DIRT else c for c in (r[i:i + 2] for i in range(0, len(r), 2))] for r in rows]}
    return out


def render(map_id, t, pack):
    """The map's field seen from above at PX a tile, as an (h, w, 3) array, from the cache when it's there."""
    path = os.path.join(CACHE, f'{map_id}-{PX}.npy')
    if os.path.exists(path):
        return np.load(path)
    im = fates_art.render(t['field'], (1, 1, t['w'] - 1, t['h'] - 1), PX, os.path.basename(os.path.dirname(pack)) if pack else None)
    a = np.asarray(im.convert('RGB'), np.uint8)
    os.makedirs(CACHE, exist_ok=True)
    np.save(path, a)
    return a


def bluish(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return b >= max(r, g)


def ground(map_id, g):
    code, _, _ = FM.MAPS[map_id]
    pack = FM.PACK.get(map_id)
    t = FT.read(FM.terrain(code, pack))
    w, h = g['width'], g['height']
    assert (t['w'] - 2, t['h'] - 2) == (w, h), map_id
    a = render(map_id, t, pack).astype(np.float32)
    px = a[:h * PX, :w * PX].reshape(h, PX, w, PX, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, PX * PX, 3)
    codes = [row[:] for row in g['grid']]
    dirt = art_ground.dirt_by_hue(px, codes, PLAIN)
    for r, c in dirt:
        codes[r][c] = DIRT
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED)
    for c in WATER:
        if c in fills and not bluish(fills[c]):
            del fills[c]
    return {'fills': fills, 'dirt': sorted([c + 1, h - r] for r, c in dirt)}


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for map_id, g in grids().items():
        if (only and map_id not in only) or map_id not in FM.MAPS:
            continue
        table[map_id] = ground(map_id, g)
        print(map_id, len(table[map_id]['dirt']), 'dirt', table[map_id]['fills'], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])

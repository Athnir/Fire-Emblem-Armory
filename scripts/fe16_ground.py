"""
Each Three Houses map's ground, read from its battle stage (scripts/fe16_art.py: the terrain's baked colour under the stage's models):
its colour per code and the plain tiles its art draws as dirt (art_ground.dirt_by_hue), written to data-raw/fe16-ground.json for
scripts/build-fe16-maps.py to apply (art_ground.apply). Renders are kept in data-raw/fe16/romfs/art-cache (git-ignored); delete it
when the art or the renderer changes. It runs on the maps the builder last wrote (src/data/fe16/fe16Maps.ts); rerun it, then the
builder, when their grids change.

A map is its scenario's (the map id's number: fe16-12-be is scenario 12, fe16-p40 a paralogue's, fe16-a54 an auxiliary battle's), its
stage the scenario's battle map (Cindered Shadows' four, 38-41, the DLC's). Water keeps the app's blue unless its colour is blue.

    python scripts/fe16_ground.py               # every map
    python scripts/fe16_ground.py fe16-1-be     # some (the others kept)
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
import fe16_art  # noqa: E402
import fe16_data as D  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe16-ground.json')
CACHE = os.path.join(HERE, '..', 'data-raw', 'fe16', 'romfs', 'art-cache')
MAPS = os.path.join(HERE, '..', 'src', 'data', 'fe16', 'fe16Maps.ts')
PX = 24
PLAIN, DIRT = 'ta', 'ga'
STAGES = 42
# The codes each map colours from its art: plain, dirt, floor, wasteland, sand, bridge, stairs, shoal, sea and lake, river, cliffs and
# walls, rock, valley, what no unit enters.
COLOURED = {'ta', 'ga', 'tw', 'te', 'td', 'tb', 'tc', 'tg', 'we', 'wl', 'wb', 'wt', 'wn', 'wa'}
# The ground units walk and the walls kept a step darker than it (tellius_minimaps.contrast: a floor and its walls never blend).
GROUNDS, WALLS = ('ta', 'tw', 'ga', 'te', 'td'), ('wa', 'wb', 'wt', 'wn')
WATER = ('we', 'wl', 'tg')


def app_maps():
    out = {}
    for line in open(MAPS, encoding='utf-8'):
        line = line.strip().rstrip(',')
        if line.startswith('{"id"'):
            m = json.loads(line)
            out[m['id']] = m
    return out


def stage_of(map_id):
    s = int(re.match(r'fe16-[pa]?(\d+)', map_id).group(1))
    return D.scenario(s)['map']


def render(stage):
    path = os.path.join(CACHE, f'{stage}-{PX}.npy')
    if os.path.exists(path):
        return np.load(path)
    a = np.asarray(fe16_art.render(stage, fe16_art.battle_window(stage), PX).convert('RGB'), np.uint8)
    os.makedirs(CACHE, exist_ok=True)
    np.save(path, a)
    return a


def bluish(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return b >= max(r, g)


def ground(m, a):
    w, h = m['width'], m['height']
    px = a[:h * PX, :w * PX].astype(np.float32).reshape(h, PX, w, PX, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, PX * PX, 3)
    codes = [[PLAIN if c == DIRT else c for c in (row[i:i + 2] for i in range(0, len(row), 2))] for row in m['grid']]
    dirt = art_ground.dirt_by_hue(px, codes, PLAIN)
    for r, c in dirt:
        codes[r][c] = DIRT
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED, GROUNDS, WALLS)
    for c in WATER:
        if c in fills and not bluish(fills[c]):
            del fills[c]
    return {'fills': fills, 'dirt': sorted([c + 1, h - r] for r, c in dirt)}


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for map_id, m in app_maps().items():
        if (only and map_id not in only) or not m['grid']:
            continue
        stage = stage_of(map_id)
        if stage >= STAGES:
            continue
        a = render(stage)
        if a.shape[:2] != (m['height'] * PX, m['width'] * PX):
            print(map_id, 'size', a.shape, m['width'], m['height'])
            continue
        table[map_id] = ground(m, a)
        print(map_id, stage, len(table[map_id]['dirt']), 'dirt', table[map_id]['fills'], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])

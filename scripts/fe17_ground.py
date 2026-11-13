"""
Each Engage map's ground, read from its battle scene (scripts/fe17_art.py): its colour per code and the plain tiles its art draws as
dirt (art_ground.dirt_by_hue: Engage's paths are darker than its grass, so they part by hue), written to data-raw/fe17-ground.json
for scripts/build-fe17-maps.py to apply (art_ground.apply). Renders take half a minute a field, so it runs on its own, on the maps the
builder last wrote (src/data/fe17/fe17Maps.ts); rerun it, then the builder, when the maps' grids change. Renders are kept in
data-raw/fe17/romfs/art-cache (git-ignored); delete it when the art or the renderer changes.

A map's field is its chapter's (chapter.xml Field, 'Fld_*' its own: a skirmish fights on its location's, a Tempest Trial map on its
chapter's), seen over its terrain window. Water keeps the app's blue unless its colour is blue.

    python scripts/fe17_ground.py              # every map
    python scripts/fe17_ground.py fe17-m004    # some (the others kept)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import art_ground  # noqa: E402
import ds_art  # noqa: E402
import fe17_art  # noqa: E402
import fe17_data as D  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe17-ground.json')
CACHE = os.path.join(HERE, '..', 'data-raw', 'fe17', 'romfs', 'art-cache')
MAPS = os.path.join(HERE, '..', 'src', 'data', 'fe17', 'fe17Maps.ts')
PX = 24
PLAIN, DIRT = 'ta', 'ga'
# The codes each map colours from its art: plain, dirt, floor, deck, road, sand, stairs, bridge, shallows, lake and sea, river, cliffs
# and mountains, rock, walls.
COLOURED = {'ta', 'ga', 't1', 't3', 'tl', 'td', 'tc', 'tb', 'tg', 'we', 'wl', 'wb', 'wt', 'wa'}
WATER = ('we', 'wl', 'tg')


def app_maps():
    """{id: map} from the generated file's RAW array (one JSON object a line)."""
    out = {}
    for line in open(MAPS, encoding='utf-8'):
        line = line.strip().rstrip(',')
        if line.startswith('{"id"'):
            m = json.loads(line)
            out[m['id']] = m
    return out


def chapter_of(map_id):
    """The chapter (CID) a map is built from: a story chapter, paralogue or Xenologue battle, a skirmish's location, or a Tempest
    Trial's map (fe17-c001-1-2: CID_C001_1, its second line-up)."""
    key = map_id[len('fe17-'):]
    if key.endswith('-sk'):
        key = key[:-3]
    if key.startswith('c'):
        key = key.rsplit('-', 1)[0]
    return 'CID_' + key.replace('-', '_').upper()


def field_and_window(map_id, chapters):
    cid = chapter_of(map_id)
    row = chapters[cid]
    name = cid[4:]
    field = name.lower() if row['Field'] in ('', 'Fld_*') else row['Field'][len('Fld_'):].lower()
    terrain = row['Terrain'].replace('MapTerrain_', '') if row['Terrain'] not in ('', 'MapTerrain_*') else name
    t = D.terrain(terrain)
    return field, (t['x'], t['z'], t['x'] + t['width'], t['z'] + t['height'])


def render(field, window):
    path = os.path.join(CACHE, f"{field}-{'-'.join(map(str, window))}-{PX}.npy")
    if os.path.exists(path):
        return np.load(path)
    a = np.asarray(fe17_art.render(field, window, PX).convert('RGB'), np.uint8)
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
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED)
    for c in WATER:
        if c in fills and not bluish(fills[c]):
            del fills[c]
    return {'fills': fills, 'dirt': sorted([c + 1, h - r] for r, c in dirt)}


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    chapters = {r['Cid']: r for r in D.rows('chapter')}
    for map_id, m in app_maps().items():
        if (only and map_id not in only) or not m['grid']:
            continue
        field, window = field_and_window(map_id, chapters)
        if not os.path.exists(os.path.join(fe17_art.ART, f'fe_scenes_fld_{field}.bundle')):
            print(map_id, 'no scene for', field)
            continue
        table[map_id] = ground(m, render(field, window))
        print(map_id, field, len(table[map_id]['dirt']), 'dirt', table[map_id]['fills'], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])

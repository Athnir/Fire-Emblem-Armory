"""
Each Awakening map's ground, read from its 3D scene (scripts/fe13_art.py): its colour per code and the plain tiles its art draws as
dirt (ds_art's two looks), written to data-raw/fe13-ground.json for scripts/build-fe13-maps.py to apply (art_ground). Renders take a
second or two a map, so it runs on its own, on the maps the builder last wrote (src/data/fe13/fe13Maps.ts); rerun it, then the
builder, when the maps' grids change.

Two maps aren't drawn well enough yet to colour from and keep the app's own colours: the Endgame (Grima's back is a skinned model,
its skeleton not read) and Chapter 18 (half its islets placed by an animation not played, its lava sea in the effects left out).

    python scripts/fe13_ground.py            # every map
    python scripts/fe13_ground.py fe13-2     # some (the others kept)
"""
import colorsys
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ds_art  # noqa: E402
import fe13_art  # noqa: E402

OUT = os.path.join(HERE, '..', 'data-raw', 'fe13-ground.json')
PX = 24
SKIP = ('fe13-endgame', 'fe13-18')
# The codes each map colours from its art: plain, dirt, waste, floor, sand, river, sea, cliffs and peaks, castle walls and edifices,
# walls and obstacles.
COLOURED = {'t0', 'ga', 'te', 't1', 'td', 'tg', 'we', 'wb', 'w0', 'wa'}
WATER, DARK = ('tg', 'we'), 40
SNOW_V, SNOW_S = 0.75, 0.15   # a pale look this light and grey is snow


def ground(m):
    """{'fills': {code: colour}, 'dirt': [[x, y], ...]} for an app map."""
    # The plain as the builder made it, before any dirt or snow this table gave it.
    codes = [['t0' if c in ('ga', 't2') else c for c in (row[i:i + 2] for i in range(0, len(row), 2))] for row in m['grid']]
    w, h = m['width'], m['height']
    a = np.asarray(fe13_art.render(m['id'], px=PX).convert('RGB'), np.float32)
    px = a[:h * PX, :w * PX].reshape(h, PX, w, PX, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, PX * PX, 3)
    dirt = ds_art.dirt_of(px, codes)
    for r, c in dirt:
        codes[r][c] = 'ga'
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED)
    # On a snowy map the paler look is snow, not dirt (Paralogue 2): those tiles are snowfield, still the game's plain.
    as_ = 'ga'
    if 'ga' in fills:
        hh, ss, vv = colorsys.rgb_to_hsv(*(int(fills['ga'][i:i + 2], 16) / 255 for i in (1, 3, 5)))
        if vv > SNOW_V and ss < SNOW_S:
            as_, fills['t2'] = 't2', fills.pop('ga')
    # Water the scene leaves to the effects it doesn't draw (Chapter 2's river, a black gorge without them) keeps the app's own.
    for code in WATER:
        if code in fills and max(int(fills[code][i:i + 2], 16) for i in (1, 3, 5)) < DARK:
            del fills[code]
    return {'fills': fills, 'dirt': sorted([c + 1, h - r] for r, c in dirt), **({'dirtAs': as_} if as_ != 'ga' else {})}


def main(only):
    table = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    for mid, m in fe13_art.app_maps().items():
        base = mid[:-len('-skirmish')] if mid.endswith('-skirmish') else mid
        if (only and mid not in only) or base in SKIP:
            continue
        table[mid] = ground(m)
        print(mid, len(table[mid]['dirt']), 'dirt', table[mid]['fills'], flush=True)
        json.dump(table, open(OUT, 'w', encoding='utf-8'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main(sys.argv[1:])

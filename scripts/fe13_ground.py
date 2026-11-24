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
# The towns' and roads' cobbles the two looks don't find (the user's calls, the review of every map: cobbles missing), each found its own
# way in its render: the Prologue's causeways by their busy, grey stone (`stone`: a tile both more textured and greyer than half the
# plain, in patches of five or more), Chapter 1's cracked red ground by its warmth (`warm`: the warmest two fifths, in patches), and
# Chapter 9's paved floor inside its ruin's walls and Chapter 22's road through the dunes read off their renders (x0, y0, x1, y1 in map
# tiles), where sand drifts over the stone and the two measures are noisy. The builder draws them as paving (build-fe13-maps' PAVED).
PAVING = {'fe13-prologue': 'stone', 'fe13-1': 'warm', 'fe13-9': [(10, 9, 20, 18)], 'fe13-22': [(11, 1, 15, 16)]}
# Maps whose floor and walls the dark-colour lift (src/logic/mapFills.ts) draws too close (the user, Chapter 20: they blend): the floor
# lifted clear of the walls, its lightness 0.1 over theirs as drawn.
APART = {'fe13-20'}


apart = ds_art.apart


def patches(tiles, area=5):
    """The tiles in 4-connected groups of at least `area`."""
    keep, seen = set(), set()
    for k in tiles:
        if k in seen:
            continue
        comp, todo = set(), [k]
        while todo:
            p = todo.pop()
            if p in comp or p not in tiles:
                continue
            comp.add(p)
            todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
        seen |= comp
        if len(comp) >= area:
            keep |= comp
    return keep


def paving(mid, px, codes):
    """{(row, column) from 0}: the plain tiles a map's render shows paved (PAVING)."""
    how = PAVING[mid]
    h = len(codes)
    plain = [(r, c) for r, row in enumerate(codes) for c, code in enumerate(row) if code == 't0']
    if isinstance(how, list):
        return {(r, c) for r, c in plain for x0, y0, x1, y1 in how if x0 <= c + 1 <= x1 and y0 <= h - r <= y1}
    med = {k: np.median(px[k[0]][k[1]], axis=0) for k in plain}
    if how == 'stone':
        sat = {k: colorsys.rgb_to_hsv(*(med[k] / 255))[1] for k in plain}
        tex = {k: px[k[0]][k[1]].mean(1).std() / 255 for k in plain}
        ts, ss = np.quantile(list(tex.values()), 0.5), np.quantile(list(sat.values()), 0.5)
        return patches({k for k in plain if tex[k] >= ts and sat[k] <= ss})
    warm = {k: (med[k][0] - med[k][1]) / max(med[k].max(), 1) for k in plain}
    return patches({k for k in plain if warm[k] >= np.quantile(list(warm.values()), 0.6)})


def ground(m):
    """{'fills': {code: colour}, 'dirt': [[x, y], ...]} for an app map."""
    # The plain as the builder made it, before any dirt or snow this table gave it.
    codes = [['t0' if c in ('ga', 't2') else c for c in (row[i:i + 2] for i in range(0, len(row), 2))] for row in m['grid']]
    w, h = m['width'], m['height']
    a = np.asarray(fe13_art.render(m['id'], px=PX).convert('RGB'), np.float32)
    px = a[:h * PX, :w * PX].reshape(h, PX, w, PX, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, PX * PX, 3)
    base = m['id'][:-len('-skirmish')] if m['id'].endswith('-skirmish') else m['id']
    dirt = paving(base, px, codes) if base in PAVING else ds_art.dirt_of(px, codes)
    for r, c in dirt:
        codes[r][c] = 'ga'
    fills = ds_art.fills_of(np.median(px, axis=2), codes, COLOURED)
    # On a snowy map the paler look is snow, not dirt (Paralogue 2): those tiles are snowfield, still the game's plain.
    as_ = 'ga'
    if 'ga' in fills:
        hh, ss, vv = colorsys.rgb_to_hsv(*(int(fills['ga'][i:i + 2], 16) / 255 for i in (1, 3, 5)))
        if vv > SNOW_V and ss < SNOW_S:
            as_, fills['t2'] = 't2', fills.pop('ga')
    if base in APART:
        apart(fills)
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

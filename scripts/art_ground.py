"""
A map's ground from its rendered art, applied to its built grid: the 3D games whose renders take minutes (Echoes:
scripts/fe15_ground.py; Awakening: scripts/fe13_ground.py) write each map's colour per code and the plain tiles its art draws as dirt
to data-raw/<game>-ground.json, and their builders apply it here. A dirt-sorted plain tile takes the dirt code (`ga`) but keeps the
game's name for it (the tile panel says what the game says), and a return visit's map is its own (no override shared with its first).
"""
import json
import os
from collections import defaultdict

import numpy as np

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


# The dirt's look must be this much warmer and less yellow-green than the grass's (Birthright 6's paths: 0.09 and 0.16; Birthright
# 15's road 0.06 and 0.13), and a tile dirt where this share of its pixels take it (fewer catches dry, sunlit grass).
WARMER, GREYER, SHARE = 0.04, 0.10, 0.55
DARKEST = 40   # pixels darker than this (deep shade) say little of their hue
# The dirt's own look must be tan or brown: warmer than this and at least this yellow (paths and earth: 0.015-0.2 and 0.22-0.33),
# not the grey of a garden's or a ruin's stone (Conquest 18, Revelation 23) or a carpet (Birthright 14).
DIRT_WARM, DIRT_YELLOW = 0.01, 0.2
REDDEST = 0.35  # warmer than this is no dirt but a carpet, blossom, autumn leaf or lava (dirt's under 0.25); bluer than yellow is snow


def chroma(p):
    """(n, 2) warmth and yellowness of pixels `p` (n, 3), which are bright enough to count, and which of those could be grass or
    dirt (neither too red nor bluish)."""
    p = p.astype(np.float32)
    mx = p.max(1)
    X = np.stack([(p[:, 0] - p[:, 1]), (p[:, 1] - p[:, 2])], 1) / np.maximum(mx, 1)[:, None]
    bright = mx >= DARKEST
    return X, bright, bright & (X[:, 0] <= REDDEST) & (X[:, 1] >= 0)


def dirt_by_hue(px, codes, plain='t0'):
    """{(row, column) from 0 at the top left}: the `plain` tiles drawn as dirt, sorted by hue, not lightness, for 3D fields whose art
    carries its shadows and sunlit patches (Fates) or whose paths are darker than their grass (Engage). A pixel's warmth (red over
    green) and yellowness (green over blue), each over its brightest channel, hold under shade; the plain's pixels part into the
    grass's look and a warmer, greyer one, and a tile is dirt where most of its pixels take the second. `px` (h, w, n, 3) each tile's
    pixels, `codes` the map's rows of codes."""
    plain = [(r, c) for r, row in enumerate(codes) for c, code in enumerate(row) if code == plain]
    if len(plain) < 8:
        return set()
    X, _, ground = chroma(np.concatenate([px[r][c][::5] for r, c in plain]))
    X = X[ground]
    if len(X) < 100:
        return set()
    warm, yellow = X[:, 0], X[:, 1]
    greenest = (yellow >= np.quantile(yellow, 0.75)) & (warm <= np.median(warm))
    dirtiest = (warm >= np.quantile(warm, 0.75)) & (yellow <= np.median(yellow))
    if not greenest.any() or not dirtiest.any():
        return set()
    C = np.stack([np.median(X[greenest], 0), np.median(X[dirtiest], 0)])
    for _ in range(30):
        near = np.argmin(((X[:, None] - C[None]) ** 2).sum(2), 1)
        C = np.stack([X[near == k].mean(0) if (near == k).any() else C[k] for k in range(2)])
    grass, pale = C
    if not (pale[0] - grass[0] > WARMER and grass[1] - pale[1] > GREYER and pale[0] >= DIRT_WARM and pale[1] >= DIRT_YELLOW):
        return set()
    out = set()
    for r, c in plain:
        Y, bright, ground = chroma(px[r][c])
        if bright.mean() < 0.3:
            continue
        near = np.argmin(((Y[ground][:, None] - C[None]) ** 2).sum(2), 1)
        if (near == 1).sum() >= SHARE * bright.sum():
            out.add((r, c))
    return out


# Stone laid among the grass (Engage's Tempest Trial stages: the user, cobble patches): a tile whose pixels are mostly greyer than the
# grass's look, as yellow-green as stone (paving's yellowness under this, its warmth near nil) where the grass is far yellower.
PAVING_YELLOW, PAVING_GAP = 0.12, 0.15


def paving_by_hue(px, codes, plain='t0'):
    """{(row, column) from 0}: the `plain` tiles drawn as paving, stone set among grass, by the same sorting as dirt_by_hue but for a
    grey look (little warmth, little yellowness) rather than a warm one. `px` (h, w, n, 3) each tile's pixels."""
    plain = [(r, c) for r, row in enumerate(codes) for c, code in enumerate(row) if code == plain]
    if len(plain) < 8:
        return set()
    X, _, ground = chroma(np.concatenate([px[r][c][::5] for r, c in plain]))
    X = X[ground]
    if len(X) < 100:
        return set()
    yellow = X[:, 1]
    grass = np.median(X[yellow >= np.quantile(yellow, 0.6)], 0)
    stone = np.median(X[yellow <= np.quantile(yellow, 0.15)], 0)
    if not (stone[1] <= PAVING_YELLOW and grass[1] - stone[1] >= PAVING_GAP):
        return set()
    C = np.stack([grass, stone])
    out = set()
    for r, c in plain:
        Y, bright, ground = chroma(px[r][c])
        if bright.mean() < 0.3:
            continue
        near = np.argmin(((Y[ground][:, None] - C[None]) ** 2).sum(2), 1)
        if (near == 1).sum() >= SHARE * bright.sum():
            out.add((r, c))
    return out

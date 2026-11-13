"""
The Tellius games' ground and colours as their in-game minimaps show them. The games call nearly every walkable tile plain, so what a
map's ground looks like (grass, or a dirt path or yard) and every kind of tile's colour (a castle's dark stone, a night map's grass, a
gorge's grey rock) come from the chapter's minimap (Fire Emblem Wiki: a capture of the game's own map screen), fitted onto the tile
grid. The map files' 3D models aren't read yet: the plain variants (平地２-４) are areas of a map, not looks, and the texture packs'
blend masks don't line up with the grid by any plain scale.

Fetches each listed map's minimap into data-raw/minimaps/ (git-ignored), fits it onto the grid (the crop whose tiles' colours best
tell the map's own kinds of tile apart: houses, plain, floors, snow, sand, walls, cliffs, trees, water), and for each map reads what
it's listed for: `dirt` sorts each plain tile into grass or dirt by its colour there, `colours` gives every kind of tile on the map
(each code with enough tiles) its colour, the median of its tiles. Writes data-raw/tellius-ground.json, which build-fe9-maps.py and
build-fe10-maps.py read:
    {map id: {"file", "box": [x0, y0, x1, y1], "score", "dirt": [[x, y], ...], "fills": {"t0": "#...", "ga": "#...", ...}}}
Run it from the repo root before those builders: python scripts/tellius_minimaps.py [map ids, to redo only those]
"""
import colorsys
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data-raw', 'minimaps')
OUT = os.path.join(ROOT, 'data-raw', 'tellius-ground.json')
DATA = os.path.join(ROOT, 'src', 'data')
# The maps whose look is read from their minimaps, by the wiki file of each (the chapter page's first capture), and what to read:
# `dirt` the grassy towns, farm towns and forts with dirt paths and yards (the user's calls: Radiant Dawn's Part 2 Ch.1, the forts
# of Path of Radiance's Ch.8 and Radiant Dawn's Part 2 Ch.3), `colours` the maps whose colours the user agreed are the game's and
# not ours (the review of every Tellius map, 2026-11-12). Each is checked by eye: Path of Radiance's Gallia isn't read (its forest
# floor sorts as dirt, and its path to the fort is too faint on the capture to place).
# `thaw` sorts snowfield into snow and bare ground the same way, by lightness (Path of Radiance's Ch.20, Radiant Dawn's Part 3
# Endgame: the user, much of the ground is bare). Every map is also read for whether its trees are snowy (pale grey).
D, C, T = 'dirt', 'colours', 'thaw'
MAPS = {
    'fe9-1': ('Cm fe09 1.png', {D}), 'fe9-24': ('Cm fe09 24.png', {D}), 'fe10-2-1': ('Cm fe10 2-1.png', {D}),
    'fe10-3-9': ('Cm fe10 3-9.png', {D}), 'fe10-1-3': ('Cm fe10 1-3.png', {D, C}),
    'fe9-3': ('Cm fe09 3.png', {D, C}), 'fe9-4': ('Cm fe09 4.png', {D, C}), 'fe9-5': ('Cm fe09 5.png', {D, C}),
    'fe9-6': ('Cm fe09 6.png', {C}), 'fe9-7': ('Cm fe09 7.png', {C}), 'fe9-8': ('Cm fe09 8.png', {D}),
    'fe9-10': ('Cm fe09 10.png', {C}), 'fe9-14': ('Cm fe09 14.png', {C}), 'fe9-16': ('Cm fe09 16.png', {C}),
    'fe9-17-1': ('Cm fe09 17-1.png', {C}), 'fe9-18': ('Cm fe09 18.png', {C}), 'fe9-19': ('Cm fe09 19.png', {C}),
    'fe9-20': ('Cm fe09 20.png', {C, T}), 'fe9-22': ('Cm fe09 22.png', {C}), 'fe9-26': ('Cm fe09 26.png', {D, C}),
    'fe9-27': ('Cm fe09 27-1.png', {C}), 'fe9-27-2': ('Cm fe09 27-2.png', {C}), 'fe9-28': ('Cm fe09 28.png', {D, C}),
    'fe9-trial3': ('Cm fe09 T-3.png', {C}), 'fe9-trial4': ('Cm fe09 T-4.png', {C}),
    'fe10-1-2': ('Cm fe10 1-2.png', {C}), 'fe10-1-5': ('Cm fe10 1-5.png', {C}), 'fe10-1-6-1': ('Cm fe10 1-6-1.png', {C}),
    'fe10-1-6-2': ('Cm fe10 1-6-2.png', {D, C}), 'fe10-1-7': ('Cm fe10 1-7.png', {C}), 'fe10-1-endgame': ('Cm fe10 1-E.png', {C}),
    'fe10-2-2': ('Cm fe10 2-2.png', {C}), 'fe10-2-3': ('Cm fe10 2-3.png', {D, C}), 'fe10-2-endgame': ('Cm fe10 2-E.png', {C}),
    'fe10-3-2': ('Cm fe10 3-2.png', {C}), 'fe10-3-3': ('Cm fe10 3-3.png', {C}), 'fe10-3-4': ('Cm fe10 3-4.png', {C}),
    'fe10-3-5': ('Cm fe10 3-5.png', {D, C}), 'fe10-3-10': ('Cm fe10 3-10.png', {C}), 'fe10-3-12': ('Cm fe10 3-12.png', {C}),
    'fe10-3-endgame': ('Cm fe10 3-E.png', {C, T}), 'fe10-4-prologue': ('Cm fe10 4-P.png', {C}), 'fe10-4-2': ('Cm fe10 4-2.png', {C}),
    'fe10-4-4': ('Cm fe10 4-4.png', {C}), 'fe10-4-5': ('Cm fe10 4-5.png', {C}),
    'fe10-4-endgame-1': ('Cm fe10 4-E-1.png', {C}), 'fe10-4-endgame-2': ('Cm fe10 4-E-2.png', {C}),
    'fe10-4-endgame-3': ('Cm fe10 4-E-3.png', {C}), 'fe10-4-endgame-4': ('Cm fe10 4-E-4.png', {C}),
    'fe10-4-endgame-5': ('Cm fe10 4-E-5.png', {C}),
}
# Crops measured by eye (x0, y0, x1, y1 in the capture's pixels) where the fit can't find the playable grid: Radiant Dawn's captures
# show more than the grid, by an amount that varies, and some stretch it (the fit's score under 0.3 for these).
# A crop can run past the capture's edge (Part 3 Ch.2's and Ch.3's top rows are off it): those tiles aren't read. Measured from the
# units' markers and the rocks against our map.
# Path of Radiance's Ch.1 keeps the crop its dirt was approved with (the user's review: good).
BOXES = {'fe10-3-2': (10, -15, 245, 204), 'fe10-3-3': (56, -10, 187, 197), 'fe10-3-10': (0, 10, 250, 160),
         'fe9-1': (54, 12, 321, 264)}
# The night chapters (Path of Radiance's Flight! and Day Breaks): what their minimaps don't colour (trees, props) is drawn in shade.
NIGHT = {'fe9-5', 'fe9-17-1', 'fe9-17-2', 'fe9-17-3', 'fe9-17-4'}
# Maps whose captures show a bigger map than theirs, which take another's colours: Day Breaks' four sections are one map at night,
# each capture the whole of it, dark but for the section in play (the first the clearest).
ALIKE = {'fe9-17-2': 'fe9-17-1', 'fe9-17-3': 'fe9-17-1', 'fe9-17-4': 'fe9-17-1',
         # Escape is Prisoner Release's map (the user: use its colours).
         'fe9-trial5': 'fe9-10'}
# Maps whose minimap reads darker than the game in daylight (a shadowed capture): their colours lifted by this much in value (the user:
# Ch.6 read as a night map, Part 3 Ch.3's grass forest green where it's a lighter olive; Trial 3's capture is black at its edges).
LIGHTEN = {'fe9-6': 1.5, 'fe10-3-3': 1.45, 'fe9-trial3': 1.7, 'fe10-1-3': 1.35}
# How much less green than the map's grass a plain tile is before it's dirt, where a map's isn't the usual (the user: Clash!'s centre is
# much more dirt).
DIRT_MARGINS = {'fe9-26': 0.015, 'fe10-1-3': 0.0}
# Maps whose less green ground is a town's cobbles, not dirt (the user: most of Part 1 Ch.3 is cobble).
DIRT_AS = {'fe10-1-3': 'gb'}
# The codes a map's colours are read for (each with at least MIN_TILES tiles): its ground, walls, cliffs and water.
COLOURED = {'t0', 't1', 't2', 't4', 't5', 't7', 'bl', 'th', 'ti', 'wt', 'ga', 'gb', 'gc', 'gd', 'ge', 'td', 'tk', 'tl', 'w0', 'w1', 'w3', 'w5', 'wb',
            'tf', 'tg', 'te', 'tj', 'wk', 'we', 'wl'}
MIN_TILES = 4
# A plain tile is dirt where its minimap colour is clearly less green than the map's grass (its green share this much under the
# map's upper quartile): dry, yellowed grass stays grass.
DIRT_MARGIN = 0.025


def curl(url, out=None):
    args = ['curl', '-s', '-L', url] + (['-o', out] if out else [])
    return subprocess.run(args, capture_output=True, check=True).stdout


def wiki_raw(title):
    return curl('https://fireemblemwiki.org/w/index.php?title=' + title.replace(' ', '_') + '&action=raw').decode('utf-8', 'replace')


def minimap(mid, name):
    """The path of a chapter's minimap (the wiki file `name`), fetched once into the cache."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, mid + os.path.splitext(name)[1])
    if not os.path.exists(path):
        info = json.loads(curl('https://fireemblemwiki.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url&titles='
                               + ('File:' + name).replace(' ', '_')))
        curl(list(info['query']['pages'].values())[0]['imageinfo'][0]['url'], path)
    return path


def load_map(mid):
    game = mid.split('-')[0]
    for line in open(os.path.join(DATA, game, game + 'Maps.ts'), encoding='utf-8'):
        if line.startswith('  {') and f'"id": "{mid}"' in line:
            return json.loads(line.strip().rstrip(','))
    raise KeyError(mid)


def kind(code):
    """The kind of tile the fit tells apart by colour."""
    if (code[0] in 'rkp' and code[1] in 'abcdefghijklmnopqr') or code in ('w8', 'oc'):
        return 'house'
    if code in ('t0', 'ga'):
        return 'plain'
    if code in ('t1', 't4', 't5', 'tc', 'gb', 'gc'):
        return 'floor'
    if code == 't2':
        return 'snow'
    if code in ('td', 'tk'):
        return 'sand'
    if code == 'wb':
        return 'cliff'
    if code in ('ba', 'bb', 'bc', 'bk', 'bl'):
        return 'tree'
    if code in ('tf', 'tg', 'te', 'tj', 'wk', 'we', 'wl'):
        return 'water'
    if code[0] == 'w' and code not in ('ws', 'wa'):
        return 'wall'
    return None


class Fit:
    def __init__(self, arr, w, h):
        self.w, self.h = w, h
        # Summed-area table: any rectangle's colour sum in four lookups.
        self.sat = np.zeros((arr.shape[0] + 1, arr.shape[1] + 1, 3))
        self.sat[1:, 1:] = arr.cumsum(0).cumsum(1)

    def means(self, box, inner=(0.3, 0.7)):
        """Each tile's mean colour over its middle (rows, columns, RGB) for the image crop `box`."""
        x0, y0, x1, y1 = box
        tw, th = (x1 - x0) / self.w, (y1 - y0) / self.h
        a, b = inner
        xa = np.floor(x0 + (np.arange(self.w) + a) * tw).astype(int)
        xb = np.maximum(xa + 1, np.floor(x0 + (np.arange(self.w) + b) * tw).astype(int))
        ya = np.floor(y0 + (np.arange(self.h) + a) * th).astype(int)
        yb = np.maximum(ya + 1, np.floor(y0 + (np.arange(self.h) + b) * th).astype(int))
        s = self.sat
        tot = s[yb][:, xb] - s[ya][:, xb] - s[yb][:, xa] + s[ya][:, xa]
        area = ((yb - ya)[:, None] * (xb - xa)[None, :])[..., None]
        return tot / area


def fisher(means, kinds):
    """How well the tiles' colours tell the kinds apart: spread between the kinds over spread within them."""
    groups = [means[kinds == k] for k in set(kinds.flatten()) if k]
    allv = np.concatenate(groups)
    mu = allv.mean(0)
    between = sum(len(g) * ((g.mean(0) - mu) ** 2).sum() for g in groups)
    within = sum(((g - g.mean(0)) ** 2).sum() for g in groups)
    return between / within if within else 0


# The second search runs only where the first fits badly (a score under this): a good fit stays as it is.
WIDE_BELOW = 0.3


def fit(m, path):
    """(score, box): the crop of the minimap that best fits the map's grid. Two coarse searches, then a fine one round the best: the
    grid filling the capture but for its edges (Path of Radiance's captures), and where that fits badly, the grid anywhere in it, filling at least 60% of it
    one way with tiles near square (Radiant Dawn's captures show more than the playable grid, by an amount that varies: Part 2 Ch.3
    is a strip between cliffs, Part 1's Endgame a strip between black bars). The 60% keeps a small crop from fitting the noise."""
    w, h = m['width'], m['height']
    kinds = np.array([[kind(row[i:i + 2]) for i in range(0, len(row), 2)] for row in m['grid']], dtype=object)
    im = Image.open(path).convert('RGB')
    W, H = im.size
    f = Fit(np.asarray(im).astype(float), w, h)
    best = [0, None]

    def consider(box):
        x0, y0, x1, y1 = box
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H or x1 - x0 < w or y1 - y0 < h:
            return
        s = fisher(f.means(box), kinds)
        if s > best[0]:
            best[:] = [s, box]
    for x0 in range(0, int(W * 0.15), 3):
        for x1 in range(int(W * 0.85), W + 1, 3):
            for y0 in range(0, int(H * 0.15), 3):
                for y1 in range(int(H * 0.85), H + 1, 3):
                    consider((x0, y0, x1, y1))
    if best[0] < WIDE_BELOW:
        for tw in np.arange(0.35 * W / w, W / w + 1e-9, max(0.25, W / w / 40)):
            for ratio in (0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.35, 1.5):
                bw, bh = tw * w, tw / ratio * h
                if bw > W + 1 or bh > H + 1 or (bw < 0.6 * W and bh < 0.6 * H):
                    continue
                for x0 in np.arange(0, max(1, W - bw + 1), 3):
                    for y0 in np.arange(0, max(1, H - bh + 1), 3):
                        consider((int(x0), int(y0), int(min(W, x0 + bw)), int(min(H, y0 + bh))))
    if best[1] is None:
        # One kind of tile only (a castle all floor): nothing to tell apart, so the whole capture.
        return (0, (0, 0, W, H)), f
    x0, y0, x1, y1 = best[1]
    for a in range(x0 - 3, x0 + 4):
        for b in range(y0 - 3, y0 + 4):
            for c in range(x1 - 3, x1 + 4):
                for d in range(y1 - 3, y1 + 4):
                    consider((a, b, c, d))
    return tuple(best), f


def tile_colour(arr, box, w, h, r, c):
    """A tile's colour on the minimap: the median of its middle, leaving out the markers the capture shows (strong reds and
    cyans: units, starting tiles)."""
    x0, y0, x1, y1 = box
    tw, th = (x1 - x0) / w, (y1 - y0) / h
    ya, yb = max(0, int(y0 + (r + .2) * th)), min(arr.shape[0], int(y0 + (r + .8) * th) + 1)
    xa, xb = max(0, int(x0 + (c + .2) * tw)), min(arr.shape[1], int(x0 + (c + .8) * tw) + 1)
    if ya >= yb or xa >= xb:
        return None  # off the capture
    a = arr[ya:yb, xa:xb].reshape(-1, 3)
    hls = np.array([colorsys.rgb_to_hls(*(p / 255)) for p in a])
    marker = (hls[:, 2] > 0.45) & ((hls[:, 0] < 0.05) | (hls[:, 0] > 0.9) | ((hls[:, 0] > 0.45) & (hls[:, 0] < 0.6)))
    # Their glow too, dimmer but still a clear pink or red (no ground is: a sunset's is orange).
    marker |= ((hls[:, 0] < 0.035) | (hls[:, 0] > 0.9)) & (hls[:, 2] > 0.2) & (hls[:, 1] > 0.3)
    keep = a[~marker] if (~marker).sum() >= 3 else a
    return np.median(keep, 0)


WALLS = ('w0', 'w1', 'w3', 'w5', 'wb', 'wt')
GROUNDS = ('t0', 't1', 't2', 't4', 't7', 'ga', 'gb', 'gc', 'gd', 'td', 'tk')


def contrast(fills, by_code):
    """Walls and cliffs kept a step darker than the ground units walk (the user: a cave's floor and walls blended), as the minimap's
    own colours can put them within a shade of each other (Radiant Dawn's Part 2 Ch.2, a dark green cave): the map's most common
    ground lightened, or the wall darkened, until they're 0.12 apart in value."""
    grounds = [c for c in GROUNDS if c in fills]
    if not grounds:
        return
    g = max(grounds, key=lambda c: len(by_code.get(c, [])))
    for wcode in WALLS:
        if wcode not in fills:
            continue
        hg, sg, vg = colorsys.rgb_to_hsv(*(int(fills[g][i:i + 2], 16) / 255 for i in (1, 3, 5)))
        hw, sw, vw = colorsys.rgb_to_hsv(*(int(fills[wcode][i:i + 2], 16) / 255 for i in (1, 3, 5)))
        if vg - vw >= 0.12 or vw - vg >= 0.12:
            continue
        if vw > vg:  # a light wall over dark ground (snowy rock): keep it the lighter
            vw = min(1, vg + 0.12)
        elif vg + 0.12 <= 1 and vw < 0.2:
            vg = vw + 0.12
        else:
            vw = max(0, vg - 0.12)
        fills[g] = '#%02x%02x%02x' % tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hg, sg, vg))
        fills[wcode] = '#%02x%02x%02x' % tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hw, sw, vw))


def soften(rgb):
    """A minimap colour softened a little to the app's: less saturated, a touch lighter (held at white)."""
    h, s, v = colorsys.rgb_to_hsv(*(min(255, max(0, c)) / 255 for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, s * 0.85, min(1, v * 1.05))
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))


def ground(m, path, what, box=None):
    (score, box), _ = ((None, box), None) if box else fit(m, path)
    arr = np.asarray(Image.open(path).convert('RGB')).astype(float)
    w, h = m['width'], m['height']
    codes = [[row[c:c + 2] for c in range(0, len(row), 2)] for row in m['grid']]
    seen = {(r, c): tile_colour(arr, box, w, h, r, c) for r in range(h) for c in range(w)}
    seen = {k: v for k, v in seen.items() if v is not None}
    dirt, by_code = [], {}
    for (r, c), rgb in seen.items():
        # The Tower's Defense and Resistance floors are its floor with an emblem inlaid: their colour is the floor's.
        by_code.setdefault('t1' if codes[r][c] in ('bo', 'bp', 'bq', 'br') else codes[r][c], []).append(rgb)
    plain = {k: rgb for k, rgb in seen.items() if codes[k[0]][k[1]] in ('t0', 'ga', DIRT_AS.get(m['id'], 'ga'))}
    if 'dirt' in what and plain:
        share = {k: rgb[1] / (sum(rgb) + 1e-6) for k, rgb in plain.items()}
        grass = np.quantile(np.array(list(share.values())), 0.75)
        by_code['t0'], by_code['ga'], by_code[DIRT_AS.get(m['id'], 'ga')] = [], [], []
        for (r, c), rgb in sorted(plain.items()):
            is_dirt = share[(r, c)] < grass - DIRT_MARGINS.get(m['id'], DIRT_MARGIN)
            if is_dirt:
                dirt.append([c + 1, h - r])
            by_code[DIRT_AS.get(m['id'], 'ga') if is_dirt else 't0'].append(rgb)
    thawed = []
    if 'thaw' in what:
        # Snow is far lighter than bare ground: split the snowfield's tiles at the lightness that best parts them (Otsu's), when
        # the two parts are far enough apart to be two looks.
        snow = {k: rgb for k, rgb in seen.items() if codes[k[0]][k[1]] in ('t2', 'gd')}
        light = {k: sum(rgb) / 765 for k, rgb in snow.items()}
        vals = np.sort(np.array(list(light.values())))
        best = (0, None)
        for cut in vals[1:-1]:
            lo, hi = vals[vals < cut], vals[vals >= cut]
            if len(lo) and len(hi):
                score = len(lo) * len(hi) * (hi.mean() - lo.mean()) ** 2
                if score > best[0]:
                    best = (score, cut, hi.mean() - lo.mean())
        if best[1] is not None and best[2] > 0.12:
            by_code['t2'], by_code['gd'] = [], []
            for (r, c), rgb in sorted(snow.items()):
                bare = light[(r, c)] < best[1]
                if bare:
                    thawed.append([c + 1, h - r])
                by_code['gd' if bare else 't2'].append(rgb)
    # Trees are snowy where the map's trees are pale and grey on its minimap.
    trees = [rgb for (r, c), rgb in seen.items() if codes[r][c] in ('ba', 'wh', 'bk')]
    snowy_trees = False
    if len(trees) >= MIN_TILES:
        hh, ss, vv = colorsys.rgb_to_hsv(*(np.median(np.array(trees), 0) / 255))
        snowy_trees = bool(ss < 0.3 and vv > 0.42)
    # Each kind's colour: the median of its tiles, softened a little to the app's (the minimap is darker than the map). Without
    # `colours`, only the ground's grass and dirt.
    wanted = COLOURED if 'colours' in what else {'t0', 'ga'}
    lift = LIGHTEN.get(m['id'], 1)
    fills = {code: soften(np.median(np.array(cs), 0) * lift) for code, cs in by_code.items() if code in wanted and len(cs) >= MIN_TILES}
    contrast(fills, by_code)
    return {'box': [int(v) for v in box], 'score': round(float(score), 3) if score is not None else 'by eye', 'dirt': dirt, 'fills': fills,
            **({'bare': thawed} if thawed else {}), **({'snowyTrees': True} if snowy_trees else {})}


_TABLE = None


def apply(m, terrain):
    """A built (encoded) map with its minimap's ground (the table this script writes): its dirt tiles `ga` and its grass's and
    dirt's colours in its fills; `terrain` (the game's table by code) given `ga`, plain's stats."""
    global _TABLE
    if _TABLE is None:
        _TABLE = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    g = _TABLE.get(m['id'])
    if not g:
        return m
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    for x, y in g['dirt']:
        if rows[m['height'] - y][x - 1] == 't0':
            rows[m['height'] - y][x - 1] = DIRT_AS.get(m['id'], 'ga')
    for x, y in g.get('bare', []):
        if rows[m['height'] - y][x - 1] == 't2':
            rows[m['height'] - y][x - 1] = 'gd'
    m['grid'] = [''.join(r) for r in rows]
    m['fills'] = {**m.get('fills', {}), **g['fills']}
    if g.get('snowyTrees'):
        m['snowyTrees'] = True
    if m['id'] in NIGHT:
        m['night'] = True
    if 't0' in terrain:
        terrain.setdefault('ga', {**terrain['t0'], 'name': 'Plain (dirt)'})
        terrain.setdefault('gb', {**terrain['t0'], 'name': 'Plain (paving)'})
    if g.get('bare') and 't2' in terrain:
        terrain.setdefault('gd', {**terrain['t2'], 'name': 'Snowfield (bare ground)'})
    return m


def main():
    only = set(sys.argv[1:])
    out = json.load(open(OUT, encoding='utf-8')) if only and os.path.exists(OUT) else {}
    for mid, (name, what) in MAPS.items():
        if only and mid not in only:
            continue
        out[mid] = {'file': name, **ground(load_map(mid), minimap(mid, name), what, BOXES.get(mid))}
        print(mid, out[mid]['score'], out[mid]['box'], len(out[mid]['dirt']), 'dirt', out[mid]['fills'], flush=True)
        for alike, like in ALIKE.items():
            if like == mid:
                out[alike] = {'like': like, 'dirt': [], 'fills': out[mid]['fills']}
        # Saved after each map, so a long run keeps what it's done.
        with open(OUT, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write('\n')


if __name__ == '__main__':
    sys.exit(main())

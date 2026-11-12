"""
The Tellius games' ground as their in-game minimaps show it. The games call nearly every walkable tile plain, so what a map's
ground looks like (grass, or a dirt path or yard) and its colours come from the chapter's minimap (Fire Emblem Wiki: a capture of
the game's own map screen), fitted onto the tile grid. The map files' 3D models aren't read yet: the plain variants (平地２-４) are
areas of a map, not looks, and the texture packs' blend masks don't line up with the grid by any plain scale.

Fetches each listed map's minimap into data-raw/minimaps/ (git-ignored), fits it onto the grid (the crop whose tiles' colours best
tell the map's own kinds of tile apart: houses, plain, walls, trees, water), sorts each plain tile into grass or dirt by its colour
there, and writes data-raw/tellius-ground.json, which build-fe9-maps.py and build-fe10-maps.py read:
    {map id: {"title", "file", "box": [x0, y0, x1, y1], "score", "dirt": [[x, y], ...], "fills": {"t0": "#...", "ga": "#..."}}}
Run it from the repo root before those builders: python scripts/tellius_minimaps.py
"""
import colorsys
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

from gba_ground import tone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data-raw', 'minimaps')
OUT = os.path.join(ROOT, 'data-raw', 'tellius-ground.json')
DATA = os.path.join(ROOT, 'src', 'data')
# The maps whose ground is read from their minimaps (the user's call): the grassy towns, farm towns with dirt paths and yards
# (Radiant Dawn's Part 2 Ch.1). The wiki's page for a chapter, where its title is ambiguous.
# Path of Radiance's Flight! (a night map, its minimap dark and full of markers) and Gallia (forest and beach) are left out.
MAPS = {
    'fe9-1': 'The Battle Begins', 'fe9-24': 'Battle Reunion',
    'fe10-1-3': 'A Faint Light', 'fe10-2-1': 'Winds of Rebellion', 'fe10-3-9': 'Marauders',
}
# A plain tile is dirt where its minimap colour is clearly less green than the map's grass (its green share this much under the
# map's upper quartile): dry, yellowed grass stays grass.
DIRT_MARGIN = 0.025


def curl(url, out=None):
    args = ['curl', '-s', '-L', url] + (['-o', out] if out else [])
    return subprocess.run(args, capture_output=True, check=True).stdout


def wiki_raw(title):
    return curl('https://fireemblemwiki.org/w/index.php?title=' + title.replace(' ', '_') + '&action=raw').decode('utf-8', 'replace')


def minimap(mid, title):
    """(path, file name): the chapter's minimap, the first map image its wiki page names that isn't a gridded or detailed one."""
    os.makedirs(CACHE, exist_ok=True)
    text = wiki_raw(title)
    if text.startswith('#REDIRECT'):
        text = wiki_raw(re.search(r'\[\[([^\]]+)\]\]', text).group(1))
    files = re.findall(r'File:(Cm fe[^\]|]*)', text)
    name = next(f for f in files if not re.search(r' (d|m)\.(png|jpg)$', f))
    path = os.path.join(CACHE, mid + os.path.splitext(name)[1])
    if not os.path.exists(path):
        info = json.loads(curl('https://fireemblemwiki.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url&titles='
                               + ('File:' + name).replace(' ', '_')))
        curl(list(info['query']['pages'].values())[0]['imageinfo'][0]['url'], path)
    return path, name


def load_map(mid):
    game = mid.split('-')[0]
    for line in open(os.path.join(DATA, game, game + 'Maps.ts'), encoding='utf-8'):
        if line.startswith('  {') and f'"id": "{mid}"' in line:
            return json.loads(line.strip().rstrip(','))
    raise KeyError(mid)


def kind(code):
    """The kind of tile the fit tells apart by colour."""
    if (code[0] in 'rkp' and code[1] in 'abcdefghi') or code in ('w8', 'oc'):
        return 'house'
    if code in ('t0', 'ga'):
        return 'plain'
    if code in ('ba', 'bb', 'bc', 'bk', 'bl'):
        return 'tree'
    if code in ('tf', 'tg', 'te', 'tj', 'wk', 'we', 'wl'):
        return 'water'
    if code[0] == 'w':
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


def fit(m, path):
    """(score, box): the crop of the minimap that best fits the map's grid."""
    w, h = m['width'], m['height']
    kinds = np.array([[kind(row[i:i + 2]) for i in range(0, len(row), 2)] for row in m['grid']], dtype=object)
    im = Image.open(path).convert('RGB')
    W, H = im.size
    f = Fit(np.asarray(im).astype(float), w, h)
    best = (0, None)
    ranges = [(range(0, int(W * 0.15), 3), range(int(W * 0.85), W + 1, 3), range(0, int(H * 0.15), 3), range(int(H * 0.85), H + 1, 3))]
    for k in range(2):
        if k:
            x0, y0, x1, y1 = best[1]
            ranges = [(range(max(0, x0 - 3), x0 + 4), range(x1 - 3, min(W, x1 + 3) + 1), range(max(0, y0 - 3), y0 + 4),
                       range(y1 - 3, min(H, y1 + 3) + 1))]
        for xs0, xs1, ys0, ys1 in ranges:
            for x0 in xs0:
                for x1 in xs1:
                    for y0 in ys0:
                        for y1 in ys1:
                            s = fisher(f.means((x0, y0, x1, y1)), kinds)
                            if s > best[0]:
                                best = (s, (x0, y0, x1, y1))
    return best, f


def tile_colour(arr, box, w, h, r, c):
    """A tile's colour on the minimap: the median of its middle, leaving out the markers the capture shows (strong reds and
    cyans: units, starting tiles)."""
    x0, y0, x1, y1 = box
    tw, th = (x1 - x0) / w, (y1 - y0) / h
    a = arr[int(y0 + (r + .2) * th):int(y0 + (r + .8) * th) + 1, int(x0 + (c + .2) * tw):int(x0 + (c + .8) * tw) + 1].reshape(-1, 3)
    hls = np.array([colorsys.rgb_to_hls(*(p / 255)) for p in a])
    marker = (hls[:, 2] > 0.45) & ((hls[:, 0] < 0.05) | (hls[:, 0] > 0.9) | ((hls[:, 0] > 0.45) & (hls[:, 0] < 0.6)))
    keep = a[~marker] if (~marker).sum() >= 3 else a
    return np.median(keep, 0)


def ground(m, path):
    (score, box), _ = fit(m, path)
    arr = np.asarray(Image.open(path).convert('RGB')).astype(float)
    w, h = m['width'], m['height']
    plain = {(r, c // 2): tile_colour(arr, box, w, h, r, c // 2) for r, row in enumerate(m['grid'])
             for c in range(0, len(row), 2) if row[c:c + 2] in ('t0', 'ga')}
    share = {k: rgb[1] / (sum(rgb) + 1e-6) for k, rgb in plain.items()}
    grass = np.quantile(np.array(list(share.values())), 0.75)
    dirt, colours = [], {'t0': [], 'ga': []}
    for (r, c), rgb in sorted(plain.items()):
        is_dirt = share[(r, c)] < grass - DIRT_MARGIN
        if is_dirt:
            dirt.append([c + 1, h - r])
        colours['ga' if is_dirt else 't0'].append(rgb)
    # Each kind's colour: the median of its tiles, softened a little to the app's (the minimap is darker than the map).
    fills = {code: tone(tuple(int(v) for v in np.median(np.array(cs), 0)), s_mul=0.85, v_mul=1.05)
             for code, cs in colours.items() if len(cs) >= 4}
    return {'box': [int(v) for v in box], 'score': round(float(score), 3), 'dirt': dirt, 'fills': fills}


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
            rows[m['height'] - y][x - 1] = 'ga'
    m['grid'] = [''.join(r) for r in rows]
    m['fills'] = {**m.get('fills', {}), **g['fills']}
    if 't0' in terrain:
        terrain.setdefault('ga', {**terrain['t0'], 'name': 'Plain (dirt)'})
    return m


def main():
    out = {}
    for mid, title in MAPS.items():
        path, name = minimap(mid, title)
        out[mid] = {'title': title, 'file': name, **ground(load_map(mid), path)}
        print(mid, out[mid]['score'], out[mid]['box'], len(out[mid]['dirt']), 'dirt', out[mid]['fills'])
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write('\n')


if __name__ == '__main__':
    sys.exit(main())

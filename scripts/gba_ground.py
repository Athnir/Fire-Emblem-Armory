"""
The GBA games' ground as each map draws it (the user's call: plains, sand and water themed like the real maps, as the walls are by
scripts/gba_walls.py). Plains, roads, floors, decks, glaciers and the volcanic flats share their stats, but each is a code of its own
(gba_maps.TERRAIN), and every map carries its own colour for its ground and water codes (`fills`), read from its art: the chapter
record's graphics, palette and tile config, as the game draws them. So Ilia's plains are snow, Sacae's dry grass, a castle's floor its
own stone and a lake its own blue, without a kind per look.

A code's colour is the blend of the five colours its tiles' pixels show most (a pixel of colour 0 shows the backdrop, palette bank
0's colour 0): grass of several greens, a floor's slabs with their joints. Not every pixel's average, which blurs a tile's edges
into the next terrain's (The Sacred Stones' River of Regrets: its dry riverbed and its grass average to nearly one olive, though
the game draws them yellow and green), nor its commonest pixel alone (The Binding Blade's Chapter 3's is a teal in green grass).
Water is its blue pixels' average, its ripples' colours with it. All softened to the app's colours (the GBA's raw colours are
brighter than its screen shows them); water still too near its map's plains is drawn stronger, lighter or darker away from them,
so the two never read as one (the user's call), and a cliff too near any ground units walk on is drawn darker, a rock face in
shadow.

The ground is drawn tile by tile as its art shows it (`looks`, the user's review of every map, 2026-11-13), each look a code of its own
with the numbers of the terrain the game calls it: on a map with grass, a plain tile yellower than its grass is dirt (`ga`: paths and
patches; a map of yellow ground all over, a desert or the Western Isles, keeps its plain as it is), or paving in The Blazing Blade's town
set (`gb`: its squares); a road is cobbles (`gf`), but a desert's golden sand roads stay roads; a floor of planks is boards (`gi`: docks,
Borgo's fort), where three or more lie together. So the grass keeps its own green, not blended with the dirt and cobbles beside it.
"""
import collections
import colorsys
import struct

import numpy as np

# The terrain ids whose colour each map gives: plain, road, sand, desert, river, bridges, sea, lake, floor, cliff, flat, glacier,
# deeps, water, deck.
COLOURED = {1, 2, 14, 15, 16, 19, 20, 21, 22, 23, 38, 42, 47, 49, 54, 60, 62}


def bgr555(v):
    return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)


class Art:
    """A chapter's map graphics: `gfx` (4bpp tiles), `pal` (16 banks of 16 colours) and `tc` (the tile config: four tile entries per
    metatile, then each metatile's terrain at 0x2000)."""

    def __init__(self, gfx, pal, tc):
        self.gfx, self.pal, self.tc = gfx, pal, tc
        self.ntiles = len(gfx) // 32

    def image(self, meta):
        """A metatile as the game draws it, (16, 16, 3) in 0-1, each 8 x 8 tile flipped as its entry says."""
        out = np.zeros((16, 16, 3))
        back = np.array(self.pal[0][0], float) / 255
        for q in range(4):
            e = struct.unpack_from('<H', self.tc, meta * 8 + q * 2)[0]
            t, hf, vf, bank = e & 0x3FF, e & 0x400, e & 0x800, e >> 12
            y, x = (q >> 1) * 8, (q & 1) * 8
            if t >= self.ntiles:
                out[y:y + 8, x:x + 8] = back
                continue
            b = np.frombuffer(self.gfx[t * 32:t * 32 + 32], np.uint8)
            idx = np.empty(64, np.uint8)
            idx[0::2], idx[1::2] = b & 15, b >> 4
            idx = idx.reshape(8, 8)
            if hf:
                idx = idx[:, ::-1]
            if vf:
                idx = idx[::-1, :]
            col = np.array(self.pal[bank], float)[idx] / 255
            col[idx == 0] = back
            out[y:y + 8, x:x + 8] = col
        return out

    def pixels(self, meta):
        """A metatile's 256 pixel colours."""
        out = []
        for q in range(4):
            e = struct.unpack_from('<H', self.tc, meta * 8 + q * 2)[0]
            t, bank = e & 0x3FF, e >> 12
            if t >= self.ntiles:
                continue
            for byte in self.gfx[t * 32:t * 32 + 32]:
                for ci in (byte & 15, byte >> 4):
                    out.append(self.pal[bank][ci] if ci else self.pal[0][0])
        return out


def art(R, lz77, pointer, rec, base):
    """A chapter's art from its record: graphics at +base (and +base+1 when set), palette +base+2, tile config +base+3 (The Blazing
    Blade and The Sacred Stones: base 4; The Binding Blade: 8)."""
    gfx = lz77(pointer(R[rec + base]))
    if R[rec + base + 1]:
        gfx += lz77(pointer(R[rec + base + 1]))
    po = pointer(R[rec + base + 2])
    pal = [[bgr555(struct.unpack_from('<H', R, po + 32 * b + 2 * c)[0]) for c in range(16)] for b in range(16)]
    return Art(gfx, pal, lz77(pointer(R[rec + base + 3])))


def tone(rgb, s_mul=0.75, v_mul=0.85):
    """The app's softer version of a GBA colour: less saturated and a little darker."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, min(1, s * s_mul), v * v_mul)
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))


def rgb(hexc):
    return tuple(int(hexc[i:i + 2], 16) for i in (1, 3, 5))


def blend(counted):
    """The weighted average of (colour, count) pairs."""
    counted = list(counted)
    n = sum(k for _, k in counted)
    return tuple(sum(c[i] * k for c, k in counted) // n for i in range(3))


# Ground units walk on, which a cliff must stand apart from: plain, road, floor, deck, glacier, flat, sand, desert, and the ground's
# looks.
GROUND = ('t0', 'tl', 't1', 't3', 't6', 't7', 'tk', 'td', 'ga', 'gb', 'gf', 'gi')
# Water that runs through a map's plains: river, sea, lake and pond, deeps.
WATER = ('tg', 'we', 'wk', 'wm')
APART = 40   # how far apart (RGB distance) water and plains must be


def fills(a, tiles, terrain_of, code_of, codes=None):
    """{app code: colour} for a map's ground and water: the colour each code's tiles show most, toned. `tiles` the map's u16s by
    [y][x], `terrain_of(tile)` its terrain id, `code_of(terrain id)` the app code it's drawn with (None: not coloured here); `codes`
    the map's codes by [y][x] where its ground is drawn by look (`looks`), each look coloured by its own tiles."""
    count = collections.defaultdict(collections.Counter)
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            tid = terrain_of(t)
            if tid in COLOURED and code_of(tid):
                code = codes[y][x] if codes and codes[y][x] in LOOK_CODES else code_of(tid)
                count[code][t >> 2] += 1
    out = {}
    for code, metas in sorted(count.items()):
        seen, green = collections.Counter(), collections.Counter()
        for meta, k in metas.items():
            for c in a.pixels(meta):
                # Dirt is its earth's colour, not the grass its edge tiles show along it (where it has any earth).
                if code == 'ga' and c[1] > c[0] + 10 and c[1] > c[2] + 10:
                    green[c] += k
                else:
                    seen[c] += k
        seen = seen or green
        # Water is its blue pixels' average, ripples and all (Bulgar's lake is sky blue with lavender ripples, the ripples its most
        # common colour); a dry riverbed with little blue in it (River of Regrets) its most common colour, as the ground is.
        blue = {c: k for c, k in seen.items() if c[2] >= max(c[0], c[1])}
        # Anything else the blend of its five commonest colours: grass of several greens, a floor's slabs with their joints (The Binding
        # Blade's Chapter 3's commonest grass pixel is teal, the grass green; the final temple's floor purple, its commonest pixel a
        # dark green joint).
        if code in WATER and sum(blue.values()) * 4 >= sum(seen.values()):
            out[code] = tone(blend(blue.items()))
        else:
            out[code] = tone(blend(seen.most_common(5)))
    # Water too near the plains it runs through: stronger, and lighter or darker away from them.
    for code in WATER:
        if code in out and 't0' in out and sum((x - y) ** 2 for x, y in zip(rgb(out[code]), rgb(out['t0']))) ** 0.5 < APART:
            lighter = sum(rgb(out[code])) >= sum(rgb(out['t0']))
            out[code] = tone(rgb(out[code]), 1.4, 1.1 if lighter else 0.82)
    # A cliff too near any ground units walk on (Jehanna's desert cliffs, sand-coloured in the art): darker, a rock face in shadow,
    # since no one but a flier crosses it.
    near = lambda c: any(g in out and sum((x - y) ** 2 for x, y in zip(rgb(c), rgb(out[g]))) ** 0.5 < APART for g in GROUND)  # noqa: E731
    if 'wb' in out:
        for _ in range(3):
            if near(out['wb']):
                out['wb'] = tone(rgb(out['wb']), 1.1, 0.78)
    return out


# The ground drawn by look (the user's review of every map, 2026-11-13): plain (1), road (2) and floor (23) tiles as their art shows
# them, each look its own code with its terrain's numbers.
PLAIN, ROAD, FLOOR = 1, 2, 23
LOOK_CODES = {'ga', 'gb', 'gf', 'gi'}
GRASS_HUES = (70, 200)   # a plain tile whose colour's hue is in here is grass
HUE_GAP = 20             # ... and one this much yellower than the map's grass is dirt, or
HUE_NEAR, PALER = 10, 0.12   # ... this much yellower and this much less saturated
SOME_GRASS = 0.1         # ... on a map with this share of grass or more (else its yellow ground is its plain)
ROAD_SAND = 0.9          # a road this saturated is a desert's golden sand, not cobbles
PLANKS, WOOD, BOARDS = 2.0, 0.7, 3   # a floor's grain this much stronger one way, this share wood-coloured, in areas this big
# Graphics sets whose yellow plain is paving, not dirt (The Blazing Blade's towns: the user, Chapters 16, 22x and Hector's 11).
PAVED_PLAINS = {'fe7': {10}}


def hue_sat(img):
    """(the median hue of a tile's coloured pixels or None where it's mostly grey or white, the median saturation)."""
    p = img.reshape(-1, 3)
    mx, mn = p.max(1), p.min(1)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = p[:, 0], p[:, 1], p[:, 2]
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    keep = sat >= 0.12
    if keep.mean() < 0.3:
        return None, float(np.median(sat))
    return float(np.median(hue[keep])), float(np.median(sat))


def planks(img):
    """(how much stronger a tile's grain runs one way than the other, its share of wood-coloured pixels)."""
    L = (img.max(2) + img.min(2)) / 2
    dx, dy = np.abs(np.diff(L, axis=1)).mean(), np.abs(np.diff(L, axis=0)).mean()
    p = img.reshape(-1, 3)
    wood = ((p[:, 0] >= p[:, 1]) & (p[:, 1] >= p[:, 2] + 0.08)).mean()
    return max(dx, dy) / max(min(dx, dy), 1e-3), float(wood)


def looks(game, tileset, a, tiles, grid, letters):
    """Rewrites a map's ground letters in place by what each tile's art shows: `tiles` its u16s and `grid` its terrain ids by [y][x],
    `letters` its letters (the looks' are their codes)."""
    h, w = len(grid), len(grid[0])
    seen = {}

    def img(t):
        if t >> 2 not in seen:
            seen[t >> 2] = a.image(t >> 2)
        return seen[t >> 2]
    plain = [(y, x) for y in range(h) for x in range(w) if grid[y][x] == PLAIN and letters[y][x] == 'G']
    look = {(y, x): hue_sat(img(tiles[y][x])) for y, x in plain}
    green = [hs for hs in look.values() if hs[0] is not None and GRASS_HUES[0] <= hs[0] <= GRASS_HUES[1]]
    paved = tileset in PAVED_PLAINS.get(game, ())
    if plain and (len(green) >= SOME_GRASS * len(plain) or paved):
        ref = float(np.median([g[0] for g in green])) if len(green) >= 2 else 100.0
        ref_sat = float(np.median([g[1] for g in green])) if len(green) >= 2 else 0.5
        for (y, x), (hue, sat) in look.items():
            if hue is not None and (hue <= ref - HUE_GAP or (hue <= ref - HUE_NEAR and sat <= ref_sat - PALER)):
                letters[y][x] = 'gb' if paved else 'ga'
    roads = [(y, x) for y in range(h) for x in range(w) if grid[y][x] == ROAD and letters[y][x] == 'O']
    for y, x in roads:
        if hue_sat(img(tiles[y][x]))[1] < ROAD_SAND:
            letters[y][x] = 'gf'
    wood = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] == FLOOR and letters[y][x] == 'T':
                grain, share = planks(img(tiles[y][x]))
                if grain >= PLANKS and share >= WOOD:
                    wood.add((y, x))
    for area in _areas(wood):
        if len(area) >= BOARDS:
            for y, x in area:
                letters[y][x] = 'gi'
    # The terrain tables list each terrain under every look it's drawn with (gba_walls.table_letters).
    import gba_walls
    for y in range(h):
        for x in range(w):
            if letters[y][x] in LOOK_CODES:
                gba_walls.PLACED.setdefault(game, {}).setdefault((grid[y][x], letters[y][x]), 0)
                gba_walls.PLACED[game][(grid[y][x], letters[y][x])] += 1


def _areas(tiles):
    out, done = [], set()
    for t in tiles:
        if t in done:
            continue
        part, todo = set(), [t]
        while todo:
            c = todo.pop()
            if c in part or c not in tiles:
                continue
            part.add(c)
            todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
        done |= part
        out.append(part)
    return out

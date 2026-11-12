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
so the two never read as one (the user's call).
"""
import collections
import colorsys
import struct

# The terrain ids whose colour each map gives: plain, road, sand, desert, river, bridges, sea, lake, floor, flat, glacier, deeps,
# water, deck.
COLOURED = {1, 2, 14, 15, 16, 19, 20, 21, 22, 23, 42, 47, 54, 60, 62}


def bgr555(v):
    return ((v & 31) * 255 // 31, (v >> 5 & 31) * 255 // 31, (v >> 10 & 31) * 255 // 31)


class Art:
    """A chapter's map graphics: `gfx` (4bpp tiles), `pal` (16 banks of 16 colours) and `tc` (the tile config: four tile entries per
    metatile, then each metatile's terrain at 0x2000)."""

    def __init__(self, gfx, pal, tc):
        self.gfx, self.pal, self.tc = gfx, pal, tc
        self.ntiles = len(gfx) // 32

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


# Water that runs through a map's plains: river, sea, lake and pond, deeps.
WATER = ('tg', 'we', 'wk', 'wm')
APART = 40   # how far apart (RGB distance) water and plains must be


def fills(a, tiles, terrain_of, code_of):
    """{app code: colour} for a map's ground and water: the colour each code's tiles show most, toned. `tiles` the map's u16s by
    [y][x], `terrain_of(tile)` its terrain id, `code_of(terrain id)` the app code it's drawn with (None: not coloured here)."""
    count = collections.defaultdict(collections.Counter)
    for row in tiles:
        for t in row:
            tid = terrain_of(t)
            if tid in COLOURED and code_of(tid):
                count[code_of(tid)][t >> 2] += 1
    out = {}
    for code, metas in sorted(count.items()):
        seen = collections.Counter()
        for meta, k in metas.items():
            for c in a.pixels(meta):
                seen[c] += k
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
    return out

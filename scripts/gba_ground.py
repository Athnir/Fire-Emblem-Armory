"""
The GBA games' ground as each map draws it (the user's call: plains, sand and water themed like the real maps, as the walls are by
scripts/gba_walls.py). Plains, roads, floors, decks, glaciers and the volcanic flats share their stats, but each is a code of its own
(gba_maps.TERRAIN), and every map carries its own colour for its ground and water codes (`fills`), read from its art: the chapter
record's graphics, palette and tile config, as the game draws them. So Ilia's plains are snow, Sacae's dry grass, a castle's floor its
own stone and a lake its own blue, without a kind per look.

A code's colour is its most common metatile's: the average of its 16 x 16 pixels (a pixel of colour 0 shows the backdrop, palette
bank 0's colour 0), toned down to the app's softer colours (the GBA's raw colours are brighter than its screen shows them).
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
        self.cache = {}

    def colour(self, meta):
        """A metatile's average colour."""
        if meta not in self.cache:
            tot, n = [0, 0, 0], 0
            for q in range(4):
                e = struct.unpack_from('<H', self.tc, meta * 8 + q * 2)[0]
                t, bank = e & 0x3FF, e >> 12
                if t >= self.ntiles:
                    continue
                for byte in self.gfx[t * 32:t * 32 + 32]:
                    for ci in (byte & 15, byte >> 4):
                        c = self.pal[bank][ci] if ci else self.pal[0][0]
                        for i in range(3):
                            tot[i] += c[i]
                        n += 1
            self.cache[meta] = tuple(v // max(n, 1) for v in tot)
        return self.cache[meta]


def art(R, lz77, pointer, rec, base):
    """A chapter's art from its record: graphics at +base (and +base+1 when set), palette +base+2, tile config +base+3 (The Blazing
    Blade and The Sacred Stones: base 4; The Binding Blade: 8)."""
    gfx = lz77(pointer(R[rec + base]))
    if R[rec + base + 1]:
        gfx += lz77(pointer(R[rec + base + 1]))
    po = pointer(R[rec + base + 2])
    pal = [[bgr555(struct.unpack_from('<H', R, po + 32 * b + 2 * c)[0]) for c in range(16)] for b in range(16)]
    return Art(gfx, pal, lz77(pointer(R[rec + base + 3])))


def tone(rgb):
    """The app's softer version of a GBA colour: less saturated and a little darker."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, s * 0.62, v * 0.80)
    return '#%02x%02x%02x' % tuple(round(c * 255) for c in (r, g, b))


def fills(a, tiles, terrain_of, code_of):
    """{app code: colour} for a map's ground and water: each code's most common metatile's colour, toned. `tiles` the map's u16s by
    [y][x], `terrain_of(tile)` its terrain id, `code_of(terrain id)` the app code it's drawn with (None: not coloured here)."""
    count = collections.defaultdict(collections.Counter)
    for row in tiles:
        for t in row:
            tid = terrain_of(t)
            if tid in COLOURED and code_of(tid):
                count[code_of(tid)][t >> 2] += 1
    return {code: tone(a.colour(metas.most_common(1)[0][0])) for code, metas in sorted(count.items())}

"""
Shadow Dragon and the Blade of Light's (FE1) map art, read from the cartridge (data-raw/fe1/rom/fe1.nes) as the game draws it, for
each map's own ground and water colours (`fills`; the user's call, as scripts/gba_ground.py gives the GBA games theirs).

Traced in the code and checked against Mesen's name tables for every terrain tile of all 25 chapters:
- A map stores one graphic tile per 16x16 tile (scripts/fe1_rom.py's map_grid). Its four 8x8 quarters are 4 bytes at 6:$8000 + tile
  * 4 (top-left, top-right, bottom-left, bottom-right; the row drawer 15:$D419 -> $D469 -> $D484), its palette the low 2 bits of
  15:$F1BF + tile (the attribute builder, 15:$D648).
- Every chapter draws with one set: the background palettes of the PPU write list "3F 00 20" at 6:$BA2F (0F 20 10 1A / 0F 36 12 1A /
  0F 27 07 1A / 0F 35 15 1A) and the background's CHR page 0x18 (MMC4's $D000/$E000, both alike; the NMI cycles 0x18, 0x19, 0x15,
  0x19 for the water's animation, 15:$C1C4, and the first is used here).
- Colours: Mesen 2's NES palette.
"""
import collections

import fe1_rom as R
import gba_ground

METATILES = (6, 0x8000)
TILE_PALETTE = 0xF1BF
MAP_PALETTE = (6, 0xBA2F)
PAGE = 0x18

# Mesen 2's NES palette (2C02), by colour index.
NES_RGB = [
    (102, 102, 102), (0, 42, 136), (20, 18, 167), (59, 0, 164), (92, 0, 126), (110, 0, 64), (108, 6, 0), (86, 29, 0),
    (51, 53, 0), (11, 72, 0), (0, 82, 0), (0, 79, 8), (0, 64, 77), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (173, 173, 173), (21, 95, 217), (66, 64, 255), (117, 39, 254), (160, 26, 204), (183, 30, 123), (181, 49, 32), (153, 78, 0),
    (107, 109, 0), (56, 135, 0), (12, 147, 0), (0, 143, 50), (0, 124, 141), (0, 0, 0), (0, 0, 0), (0, 0, 0),
    (255, 254, 255), (100, 176, 255), (146, 144, 255), (198, 118, 255), (243, 106, 255), (254, 110, 204), (254, 129, 112),
    (234, 158, 34), (188, 190, 0), (136, 216, 0), (92, 228, 48), (69, 224, 130), (72, 205, 222), (79, 79, 79), (0, 0, 0), (0, 0, 0),
    (255, 254, 255), (192, 223, 255), (211, 210, 255), (232, 200, 255), (251, 194, 255), (254, 196, 234), (254, 204, 197),
    (247, 216, 165), (228, 229, 148), (207, 239, 150), (189, 244, 171), (179, 243, 204), (181, 235, 242), (184, 184, 184), (0, 0, 0),
    (0, 0, 0),
]

_rom = open(R.ROM, 'rb').read()
_chr = _rom[16 + 16 * 0x4000:]
_head = R.read(*MAP_PALETTE, 3)
assert _head == b'\x3f\x00\x20', _head.hex()
_cols = list(R.read(MAP_PALETTE[0], MAP_PALETTE[1] + 3, 16))
PALETTES = [[NES_RGB[c] for c in [_cols[0]] + _cols[4 * p + 1:4 * p + 4]] for p in range(4)]
_pixels = {}


def pixels(tile):
    """A graphic tile's 256 pixel colours."""
    if tile not in _pixels:
        pal = PALETTES[R.u8(R.FIXED, TILE_PALETTE + tile) & 3]
        out = []
        for n in R.read(METATILES[0], METATILES[1] + 4 * tile, 4):
            o = PAGE * 0x1000 + n * 16
            lo, hi = _chr[o:o + 8], _chr[o + 8:o + 16]
            out += [pal[((lo[y] >> (7 - x)) & 1) | (((hi[y] >> (7 - x)) & 1) << 1)] for y in range(8) for x in range(8)]
        _pixels[tile] = out
    return _pixels[tile]


# The plains FE1's water runs through (its grass, `tv`: Avoid 5), its water, and its sand (the shores, which its tiles draw on grass).
PLAINS, WATER, SANDS = 'tv', ('tg', 'we'), ('td',)


def fills(tiles, code_of):
    """{app code: colour} for a map's ground and water, as scripts/gba_ground.py's fills: each code's commonest five colours blended
    (water its blue pixels' average), toned to the app's, and water too near the plains drawn apart from them. `tiles` the map's
    graphic tiles, `code_of(tile)` the app code it's coloured as (None: not coloured here)."""
    count = collections.defaultdict(collections.Counter)
    for row in tiles:
        for t in row:
            if code_of(t):
                count[code_of(t)][t] += 1
    out = {}
    # The plains' own colours, which a shore's tiles show round their sand (the user: the shores came out olive, grass and sand blended).
    grass = collections.Counter()
    for t, k in count.get(PLAINS, {}).items():
        for c in pixels(t):
            grass[c] += k
    grass_colours = {c for c, _ in grass.most_common(2)}
    for code, ts in sorted(count.items()):
        seen = collections.Counter()
        for t, k in ts.items():
            for c in pixels(t):
                seen[c] += k
        if code in SANDS:
            own = collections.Counter({c: k for c, k in seen.items() if c not in grass_colours})
            if sum(own.values()) * 4 >= sum(seen.values()):
                seen = own
        blue = {c: k for c, k in seen.items() if c[2] >= max(c[0], c[1])}
        if code in WATER and sum(blue.values()) * 4 >= sum(seen.values()):
            out[code] = gba_ground.tone(gba_ground.blend(blue.items()))
        else:
            out[code] = gba_ground.tone(gba_ground.blend(seen.most_common(5)))
    for code in WATER:
        if code not in out or PLAINS not in out:
            continue
        if sum((x - y) ** 2 for x, y in zip(gba_ground.rgb(out[code]), gba_ground.rgb(out[PLAINS]))) ** 0.5 < gba_ground.APART:
            lighter = sum(gba_ground.rgb(out[code])) >= sum(gba_ground.rgb(out[PLAINS]))
            out[code] = gba_ground.tone(gba_ground.rgb(out[code]), 1.4, 1.1 if lighter else 0.82)
    return out

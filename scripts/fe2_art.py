"""
Fire Emblem Gaiden's (FE2) battle map art, read from the ROM (scripts/fe2_data.py) as the game draws it, for each map's own colours
(`fills`; the user's call, as the other games' are).

Traced in the code and checked in Mesen on all 80 battle maps (name table, attribute table and palette RAM tile for tile):
- A map stores one graphic tile per 16x16 tile (fe2_data.battle_map). The battle screen (15:$D39A, scrolled by 15:$CE38 / $CF2A)
  draws with bank 6 at $8000: a graphic tile's four 8x8 quarters are 4 bytes at 6:$8000 + tile * 4 (top-left, top-right,
  bottom-left, bottom-right), its palette the low 2 bits of 6:$8400 + tile.
- Every map draws with the one metatile set and CHR (the background's $1000 table, MMC4's $D000/$E000 pages both $18, 15:$D3CA; the
  NMI cycles $18, $19, $15, $19 for the water, the first used here). Only the palettes vary: the map's palette list number is
  15:$CC95[map], the list bank 6's PPU write list at 6:$8500 (u16 pointers, by number - 1): "3F 00 20" then the colours. Lists 21
  (green: the open fields and deserts), 1 (map 19), 17 (brown: the ships, caves, towns' and dungeons' fields), 19 (Celica's Chapter 4
  and Duma's), 20 (dark teal: the dark forests) and 22 (black, its plain sky blue: the Dragon Tower).
- Colours: Mesen 2's NES palette (fe1_art's).
"""
import collections

import numpy as np

import fe1_art
import fe2_data as D
import tellius_minimaps

R = D.R
TILESET_BANK, METATILES, TILE_PALETTE, PPU_LISTS = 6, 0x8000, 0x8400, 0x8500
MAP_PALETTE = 0xCC95
PAGE = 0x18
_pixels = {}


def palette_list(rom_map):
    return R.u8(D.FIXED, MAP_PALETTE + rom_map)


def palettes(plist):
    p = R.u16(TILESET_BANK, PPU_LISTS + 2 * (plist - 1))
    head = R.read(TILESET_BANK, p, 3)
    assert head[:2] == b'\x3f\x00' and head[2] >= 0x10, (plist, head.hex())
    cols = list(R.read(TILESET_BANK, p + 3, 16))
    return [[fe1_art.NES_RGB[c] for c in [cols[0]] + cols[4 * k + 1:4 * k + 4]] for k in range(4)]


def pixels(tile, plist):
    """A graphic tile's 256 pixel colours in palette list `plist`, (256, 3)."""
    if (tile, plist) not in _pixels:
        pal = palettes(plist)[R.u8(TILESET_BANK, TILE_PALETTE + tile) & 3]
        out = np.zeros((16, 16, 3), np.uint8)
        for q, n in enumerate(R.read(TILESET_BANK, METATILES + 4 * tile, 4)):
            o = PAGE * 0x1000 + n * 16
            lo, hi = R.chr[o:o + 8], R.chr[o + 8:o + 16]
            for y in range(8):
                for x in range(8):
                    out[(q >> 1) * 8 + y, (q & 1) * 8 + x] = pal[((lo[y] >> (7 - x)) & 1) | (((hi[y] >> (7 - x)) & 1) << 1)]
        _pixels[(tile, plist)] = out.reshape(256, 3)
    return _pixels[(tile, plist)]


# The palette lists whose plains are bare earth (brown: the caves, the towns' and dungeons' fields, the ships, Celica's Chapter 4 and
# Duma's): drawn as dirt (`ga`), not grass.
EARTH = {17, 19}

# The codes each map colours from its art: plain, floor, castle floor, sand, shallows, water, peaks, swamp, rock and castle walls,
# and the ships' decks and the stone bridges.
COLOURED = {'t0', 'ga', 't1', 'b0', 'td', 'tg', 'we', 'wb', 'df', 'wt', 'wx', 't3', 't8'}
MIN_TILES = 4


def fills(rom_map, tiles, codes):
    """{code: colour} for a map's ground, water and walls: the median of each code's tiles (each tile its pixels' median), softened
    to the app's and walls kept a step apart from the ground (tellius_minimaps' soften and contrast). `tiles` the map's graphic tiles
    and `codes` its app codes, both rows top to bottom over the playable grid."""
    plist = palette_list(rom_map)
    by_code = collections.defaultdict(list)
    for trow, crow in zip(tiles, codes):
        for t, code in zip(trow, crow):
            by_code[code].append(np.median(pixels(t, plist), 0))
    out = {code: tellius_minimaps.soften(np.median(np.array(cs), 0)) for code, cs in by_code.items()
           if code in COLOURED and len(cs) >= MIN_TILES}
    tellius_minimaps.contrast(out, by_code)
    return out

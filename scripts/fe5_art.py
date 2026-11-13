"""
Thracia 776's (FE5) map art, read from the clean ROM (scripts/fe5_rom.py) as the game draws it, for each map's own colours (`fills`;
the user's call, as the other games' are).

Traced in the code and checked against Mesen's VRAM, CGRAM and WRAM in 16 chapters covering all 7 graphics sets and all 5 extra-tile
blocks. $80:9C55 runs $84:8952, $84:89BC and $84:89E8, which read the chapter record ($84:804A + 52 x chapter):
- +0x00 its 4bpp BG tiles, compressed: the first 0x5000 bytes go to VRAM word $2800, tiles 128-767 of the BG character base ($2000);
- +0x2E extra tiles or 0: compressed, a u16 byte count first, to VRAM word $4000 (tile 512 on, over the set's own);
- +0x0C the chapter's palette ($F6:8000 + 0x100 x chapter): bytes 0x60-0xFF are BG palettes 3-7, the only ones maps use;
- +0x09 the tileset config, compressed: 1024 metatiles x 4 BG map entries in the order top left, bottom left, top right, bottom right
  (tile in the low 10 bits, palette bits 10-12, h flip $4000, v flip $8000), then a terrain byte per metatile;
- +0x31 the tile animation list ($83:C4CF plays it every frame: the water, some walls and floors), its first frame used here.
$84:8A20 clears tile 767. The map is drawn on BG2; no map palette cycles.
"""
import functools
import struct

import numpy as np

import fe5_rom as r
import tellius_minimaps

GFX, TILESET, PALETTE, EXTRA, ANIM = 0x00, 0x09, 0x0C, 0x2E, 0x31
MAIN_TILES, FIRST_TILE, EXTRA_TILE, CLEARED_TILE, BG_TILES, CHAR_BASE = 0x5000, 128, 512, 767, 1024, 0x2000


def _field(n, off):
    return r.u24(r.CHAPTERS + 52 * n + off)


def _decode_4bpp(data):
    n = len(data) // 32
    b = np.frombuffer(bytes(data[:n * 32]), dtype=np.uint8).reshape(n, 32)
    bits = np.unpackbits(b, axis=1).reshape(n, 32, 8)
    p0, p1, p2, p3 = bits[:, 0:16:2], bits[:, 1:16:2], bits[:, 16:32:2], bits[:, 17:32:2]
    return (p0 | p1 << 1 | p2 << 2 | p3 << 3).astype(np.uint8)


def _first_frame(n):
    """{VRAM word: source} of the animation list's first shown frame (a step of one game frame and the next together)."""
    a, cur = _field(n, ANIM), {}
    while a and r.u16(a):
        src, dst, wait = r.u24(a), r.u16(a + 3), r.u8(a + 5)
        cur[dst] = src
        if wait > 1:
            return cur
        a += 6
    return cur


@functools.lru_cache(maxsize=None)
def tiles(n):
    v = bytearray(BG_TILES * 32)
    v[FIRST_TILE * 32:FIRST_TILE * 32 + MAIN_TILES] = r.decompress(_field(n, GFX))[:MAIN_TILES]
    if _field(n, EXTRA):
        x = r.decompress(_field(n, EXTRA))
        size = struct.unpack_from('<H', x, 0)[0]
        v[EXTRA_TILE * 32:EXTRA_TILE * 32 + size] = x[2:2 + size]
    v[CLEARED_TILE * 32:CLEARED_TILE * 32 + 32] = bytes(32)
    for dst, src in _first_frame(n).items():
        o = (dst - CHAR_BASE) * 2
        v[o:o + 0x800] = r.R[r.lo(src):r.lo(src) + 0x800]
    return _decode_4bpp(bytes(v))


@functools.lru_cache(maxsize=None)
def metatiles(n):
    words = struct.unpack('<4096H', r.decompress(_field(n, TILESET))[:0x2000])
    return [words[4 * i:4 * i + 4] for i in range(1024)]


@functools.lru_cache(maxsize=None)
def palette(n):
    raw = bytearray(r.R[r.lo(_field(n, PALETTE)):][:0x100])
    raw[0:0x20] = r.R[r.lo(0x9E8260):][:0x20]
    w = np.array(struct.unpack('<128H', bytes(raw)), dtype=np.uint16)
    rgb = np.stack([w & 31, (w >> 5) & 31, (w >> 10) & 31], axis=-1).astype(np.uint16)
    return ((rgb << 3) | (rgb >> 2)).astype(np.uint8).reshape(8, 16, 3)


@functools.lru_cache(maxsize=None)
def pixels(n, mt):
    """Chapter n's metatile `mt` as 256 pixel colours, (256, 3)."""
    t, pal = tiles(n), palette(n)
    out = np.zeros((16, 16, 3), np.uint8)
    for q, w in enumerate(metatiles(n)[mt & 0x3FF]):
        px = t[w & 0x3FF]
        if w & 0x4000:
            px = px[:, ::-1]
        if w & 0x8000:
            px = px[::-1, :]
        out[(q & 1) * 8:(q & 1) * 8 + 8, (q >> 1) * 8:(q >> 1) * 8 + 8] = pal[(w >> 10) & 7][px]
    return out.reshape(256, 3)


# The codes each map colours from its art: plain, road, indoor floor, sand, wasteland, river, sea, lake, castle walls, outdoor walls
# and roofs. Its cliffs, drawn as grassy slopes, keep the app's rock colour.
COLOURED = {'t0', 'tl', 'tn', 'tk', 'te', 'tg', 'we', 'wk', 'w0', 'wx', 'w7'}
MIN_TILES = 4


def fills(n, cells, codes):
    """{code: colour} for chapter n's ground, water and walls: the median of each code's tiles (each its pixels' median), softened to
    the app's and walls kept a step apart from the ground (tellius_minimaps' soften and contrast). `cells` the map's metatile cells
    and `codes` its app codes, both rows top to bottom over the playable grid."""
    by_code = {}
    for crow, row in zip(cells, codes):
        for cell, code in zip(crow, row):
            by_code.setdefault(code, []).append(np.median(pixels(n, cell & 0x3FF), 0))
    out = {code: tellius_minimaps.soften(np.median(np.array(cs), 0)) for code, cs in by_code.items()
           if code in COLOURED and len(cs) >= MIN_TILES}
    tellius_minimaps.contrast(out, by_code)
    return out

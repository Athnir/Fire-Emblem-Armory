"""
Mystery of the Emblem's (FE3) map art, read from the clean ROM (scripts/fe3_rom.py) as the game draws it, for each map's own colours
(`fills`; the user's call, as the other games' are).

Traced in the code ($83:8851-$83:8A72, $80:A957-$80:A9F4) and checked against Mesen's VRAM and CGRAM in 14 chapters covering all 12
graphics sets:
- The map header ($8A:8000 + 8 x map) gives +0 the graphics set and +1 the tileset. Each table below is long pointers, 3 bytes per
  entry, the bank byte stored less the number given.
- By graphics set: $89:C9A3 (+$9D) its 4bpp tiles, compressed (the game's decompressor, fe3_rom.decompress), of which tiles 0-447 reach
  VRAM; $89:C9C7 (+$97) tiles 448-511, animated (8 frames of $800, uncompressed; the first used here); $89:CB6E (+$A2) its metatiles,
  compressed: 1024 x 4 BG map entries (top left, top right, bottom left, bottom right: tile in the low 10 bits, palette in bits 10-12,
  h flip $4000, v flip $8000).
- By tileset (the number that picks the terrain table): $89:C9EB (+$CB) its palette ($200 bytes), palette 0 then replaced by $94:D080
  and 5-7 by $95:F800; colours $37 and $38 cycle through 16 frames ($89:CA4E (+$CB) + $3000, 32 u16 each), shown here at each one's
  most frequent frame. Map tiles use palettes 1-4.
"""
import functools
import struct

import numpy as np

import fe3_rom as r
import tellius_minimaps

GFX_TILES = (0x89C9A3, 0x9D)
GFX_ANIM = (0x89C9C7, 0x97)
GFX_META = (0x89CB6E, 0xA2)
TS_PALETTE = (0x89C9EB, 0xCB)
TS_PAL_ANIM = (0x89CA4E, 0xCB)
PAL0, PAL5_7 = 0x94D080, 0x95F800
STATIC_TILES = 0x1C0


def _ptr(table, i):
    a, add = table
    o = r.lo(a) + 3 * i
    return r.R[o] | r.R[o + 1] << 8 | ((r.R[o + 2] + add) & 0xFF) << 16


def _decode_4bpp(data):
    n = len(data) // 32
    b = np.frombuffer(bytes(data[:n * 32]), dtype=np.uint8).reshape(n, 32)
    bits = np.unpackbits(b, axis=1).reshape(n, 32, 8)
    p0, p1, p2, p3 = bits[:, 0:16:2], bits[:, 1:16:2], bits[:, 16:32:2], bits[:, 17:32:2]
    return (p0 | p1 << 1 | p2 << 2 | p3 << 3).astype(np.uint8)


@functools.lru_cache(maxsize=None)
def tiles(gfx):
    static = r.decompress(_ptr(GFX_TILES, gfx))[:STATIC_TILES * 32]
    anim = r.R[r.lo(_ptr(GFX_ANIM, gfx)):][:0x800]
    return _decode_4bpp(static + anim)


@functools.lru_cache(maxsize=None)
def metatiles(gfx):
    words = struct.unpack('<4096H', r.decompress(_ptr(GFX_META, gfx))[:0x2000])
    return [words[4 * i:4 * i + 4] for i in range(1024)]


@functools.lru_cache(maxsize=None)
def palette(tileset):
    raw = bytearray(r.R[r.lo(_ptr(TS_PALETTE, tileset)):][:0x100])
    raw[0:0x20] = r.R[r.lo(PAL0):][:0x20]
    raw[0:2] = bytes(2)
    raw[0xA0:0x100] = r.R[r.lo(PAL5_7):][:0x60]
    words = list(struct.unpack('<128H', bytes(raw)))
    a = r.lo(_ptr(TS_PAL_ANIM, tileset) + 0x3000)
    cycle = struct.unpack('<32H', r.R[a:a + 0x40])
    for k, frames in zip((0x37, 0x38), (cycle[:16], cycle[16:])):
        words[k] = max(frames, key=lambda v: (frames.count(v), -frames.index(v)))
    w = np.array(words, dtype=np.uint16)
    rgb = np.stack([w & 31, (w >> 5) & 31, (w >> 10) & 31], axis=-1).astype(np.uint16)
    return ((rgb << 3) | (rgb >> 2)).astype(np.uint8).reshape(8, 16, 3)


@functools.lru_cache(maxsize=None)
def pixels(gfx, tileset, mt):
    """A metatile's 256 pixel colours, (256, 3)."""
    t, pal = tiles(gfx), palette(tileset)
    out = np.zeros((16, 16, 3), np.uint8)
    for q, w in enumerate(metatiles(gfx)[mt & 0x3FF]):
        px = t[(w & 0x3FF) % len(t)]
        if w & 0x4000:
            px = px[:, ::-1]
        if w & 0x8000:
            px = px[::-1, :]
        out[(q >> 1) * 8:(q >> 1) * 8 + 8, (q & 1) * 8:(q & 1) * 8 + 8] = pal[(w >> 10) & 7][px]
    return out.reshape(256, 3)


# The codes each map colours from its art: plain, the floors, path, sand, river, stream, sea and castle walls.
COLOURED = {'tv', 'ta', 'tn', 'tl', 'td', 'tg', 'to', 'we', 'w0'}
MIN_TILES = 4


def fills(gfx, tileset, cells, codes):
    """{code: colour} for a map's ground, water and walls: the median of each code's tiles (each tile its pixels' median), softened
    to the app's and walls kept a step apart from the ground (tellius_minimaps' soften and contrast). `cells` the map's metatile cells
    and `codes` its app codes, both rows top to bottom over the playable grid."""
    by_code = {}
    for crow, row in zip(cells, codes):
        for cell, code in zip(crow, row):
            by_code.setdefault(code, []).append(np.median(pixels(gfx, tileset, cell & 0x3FF), 0))
    out = {code: tellius_minimaps.soften(np.median(np.array(cs), 0)) for code, cs in by_code.items()
           if code in COLOURED and len(cs) >= MIN_TILES}
    # The contrast check knows the ground by the other games' codes: this game's plain (Avo 5) and floors under theirs.
    alias = {'tv': 't0', 'tn': 't1', 'ta': 't4'}
    seen = {alias.get(c, c): v for c, v in out.items()}
    tellius_minimaps.contrast(seen, {alias.get(c, c): v for c, v in by_code.items()})
    back = {v: k for k, v in alias.items()}
    return {back.get(c, c): v for c, v in seen.items()}

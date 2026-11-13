"""
Genealogy of the Holy War's (FE4) map art, read from the clean ROM (scripts/fe4_rom.py, the game's decompressor run by
scripts/fe4_cpu.py) as the game draws it, for each map's own colours (`fills`; the user's call, as the other games' are).

Traced in Mesen and read in the code ($88:9268, $88:9305, $88:80C9); checked against Mesen's VRAM, metatile table, map RAM and
palettes in all 12 chapters (BG1 drawn from them matches pixel for pixel). The chapter record (pointers at $88:9FC3):
- +0 the map, compressed (the low 10 bits of a cell are its metatile);
- +3 metatiles 0-255, compressed ($800 bytes, to $7F:0000); 256-1023 are every chapter's, at $D9:5000;
- +6 BG tiles 640-767, compressed ($1000 bytes, to VRAM $2800); tiles 0-639 are every chapter's, at $D9:0000 (160-191 and 192-255
  animated: 32 frames at $DC:0000, 16 at $DB:0000; the first used here);
- +9 BG palettes 1-7, uncompressed ($E0 bytes, to CGRAM $20); map tiles use palettes 1-5. No map palette cycles.
A metatile is 4 BG map entries in column order (top left, bottom left, top right, bottom right). As a chapter loads, $87:EF61 draws
each castle's owner shield and a closed village's door: both on plain ground, so the colours are the stored map's.
"""
import functools
import struct

import numpy as np

import fe4_rom as r
import tellius_minimaps
from fe4_cpu import Cpu  # noqa: E402
from fe4_cpu import rom_offset  # noqa: E402

CHAPTER_TABLE, COMMON_TILES, COMMON_META, ANIM_HI, ANIM_LO = 0x889FC3, 0xD90000, 0xD95000, 0xDB0000, 0xDC0000
_cpu = Cpu()


def _long(o):
    return r.R[o] | r.R[o + 1] << 8 | r.R[o + 2] << 16


def _ptr(chapter, off):
    return _long(rom_offset(_long(rom_offset(CHAPTER_TABLE) + 3 * chapter)) + off)


def _rom(addr, n):
    o = rom_offset(addr)
    return bytes(r.R[o:o + n])


@functools.lru_cache(maxsize=None)
def _decompress(addr):
    return _cpu.decompress(addr)


def _decode_4bpp(data):
    n = len(data) // 32
    b = np.frombuffer(bytes(data[:n * 32]), dtype=np.uint8).reshape(n, 32)
    bits = np.unpackbits(b, axis=1).reshape(n, 32, 8)
    p0, p1, p2, p3 = bits[:, 0:16:2], bits[:, 1:16:2], bits[:, 16:32:2], bits[:, 17:32:2]
    return (p0 | p1 << 1 | p2 << 2 | p3 << 3).astype(np.uint8)


@functools.lru_cache(maxsize=None)
def tiles(chapter):
    data = bytearray(_rom(COMMON_TILES, 0x5000))
    data[160 * 32:192 * 32] = _rom(ANIM_LO, 0x400)
    data[192 * 32:256 * 32] = _rom(ANIM_HI, 0x800)
    own = _decompress(_ptr(chapter, 6))
    assert len(own) == 0x1000, len(own)
    return _decode_4bpp(bytes(data) + own)


@functools.lru_cache(maxsize=None)
def metatiles(chapter):
    own = _decompress(_ptr(chapter, 3))
    assert len(own) == 0x800, len(own)
    words = struct.unpack('<4096H', own + _rom(COMMON_META, 0x1800))
    return [words[4 * i:4 * i + 4] for i in range(1024)]


@functools.lru_cache(maxsize=None)
def palette(chapter):
    words = [0] * 16 + list(struct.unpack('<112H', _rom(_ptr(chapter, 9), 0xE0)))
    w = np.array(words, dtype=np.uint16)
    rgb = np.stack([w & 31, (w >> 5) & 31, (w >> 10) & 31], axis=-1).astype(np.uint16)
    return ((rgb << 3) | (rgb >> 2)).astype(np.uint8).reshape(8, 16, 3)


@functools.lru_cache(maxsize=None)
def pixels(chapter, mt):
    """The chapter's metatile `mt` as 256 pixel colours, (256, 3)."""
    t, pal = tiles(chapter), palette(chapter)
    out = np.zeros((16, 16, 3), np.uint8)
    for q, w in enumerate(metatiles(chapter)[mt & 0x3FF]):
        px = t[(w & 0x3FF) % len(t)]
        if w & 0x4000:
            px = px[:, ::-1]
        if w & 0x8000:
            px = px[::-1, :]
        out[(q & 1) * 8:(q & 1) * 8 + 8, (q >> 1) * 8:(q >> 1) * 8 + 8] = pal[(w >> 10) & 7][px]
    return out.reshape(256, 3)


# The codes each map colours from its art: plain, road, sand, desert, river, sea and castle walls. Its peaks and cliffs, drawn on
# wooded slopes, keep the app's rock colour (their tiles' median is the slopes' dark green).
COLOURED = {'t0', 'tl', 'tk', 'td', 'tg', 'we', 'w0'}
MIN_TILES = 4


def fills(chapter, cells, codes):
    """{code: colour} for a chapter's ground, water and walls: the median of each code's tiles (each its pixels' median), softened to
    the app's and walls kept a step apart from the ground (tellius_minimaps' soften and contrast). `cells` the map's cells and
    `codes` its app codes, both rows top to bottom over the playable grid."""
    by_code = {}
    for crow, row in zip(cells, codes):
        for cell, code in zip(crow, row):
            by_code.setdefault(code, []).append(np.median(pixels(chapter, int(cell) & 0x3FF), 0))
    out = {code: tellius_minimaps.soften(np.median(np.array(cs), 0)) for code, cs in by_code.items()
           if code in COLOURED and len(cs) >= MIN_TILES}
    tellius_minimaps.contrast(out, by_code)
    return out

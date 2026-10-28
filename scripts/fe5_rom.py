"""
Reader for the user's own Fire Emblem: Thracia 776 (FE5) cartridge image, shared by the FE5 generators. The ROM is the clean Japanese
retail dump (the one Lil' Manster patches), kept outside the repo (default path below, or set FE5_ROM); only data built from it is
committed. The cartridge is LoROM: the SNES address $BB:AAAA is file offset (BB & 0x7F) * 0x8000 + (AAAA & 0x7FFF). Little-endian.

Table locations and field names follow the Lil' Manster team's public build files (github.com/famitino/fe776br, Zane Avernathy's
disassembly) and Zane Avernathy's VoltEdge library (github.com/ZaneAvernathy/VoltEdge); each one used here was checked in the clean
ROM. Formats are in data-raw/fe5/README.md.
"""
import functools
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_cpu import Cpu  # noqa: E402

ROM = os.environ.get('FE5_ROM', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Fire Emblem - Thraki 776 (J).smc'))
CRC32 = 0xFC519952

R = open(ROM, 'rb').read()
assert zlib.crc32(R) == CRC32, f'{ROM} is not the clean Thracia 776 dump (CRC32 {CRC32:08X})'

ITEMS = 0xB080AB          # 23 bytes per item id (0 is "none")
ITEM_COUNT = 0xA0
CLASSES = 0x868000        # 36 bytes per class id, from id 1
CHARACTERS = 0x869A2D     # 48 bytes per character id, from id 1
CHAPTERS = 0x84804A       # 52 bytes per chapter
CHAPTER_EVENTS = 0x8CD561  # 30 bytes per chapter: ten long pointers
DECOMPRESS = 0x80B574     # the game's decompressor


def lo(addr):
    """SNES address -> file offset."""
    return ((addr >> 16) & 0x7F) * 0x8000 + (addr & 0x7FFF)


def snes(offset):
    return 0x800000 | (offset // 0x8000) << 16 | 0x8000 | offset % 0x8000


def u8(a):
    return R[lo(a)]


def u16(a):
    return struct.unpack_from('<H', R, lo(a))[0]


def u24(a):
    o = lo(a)
    return R[o] | R[o + 1] << 8 | R[o + 2] << 16


TYPES = ['Sword', 'Lance', 'Axe', 'Bow', 'Staff', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', None, 'Item']
# Item traits (+0x15)
BALLISTA, MAGIC_RANGED, WEAPON, TOME, STAFF, UNBREAKABLE, UNSELLABLE, BROKEN = (1 << i for i in range(8))


def item(i):
    """One item record, as the game keeps it (its price is worked out as the game does, $83:B00D)."""
    a = ITEMS + 23 * i
    o = lo(a)
    b = R[o:o + 23]
    uses = struct.unpack_from('<b', b, 4)[0]
    per_use = struct.unpack_from('<H', b, 0xD)[0]
    traits = b[0x15]
    price = per_use * (uses if uses > 0 else 1) + (200 if traits & (WEAPON | STAFF) else 0)
    return {
        'id': i, 'type': b[0] & 0xF, 'alt_type': b[0] >> 4, 'mt': struct.unpack_from('<b', b, 1)[0], 'hit': b[2], 'wt': b[3],
        'uses': uses, 'crit': b[5], 'range': (b[6] & 0xF, b[6] >> 4), 'rank': struct.unpack_from('<H', b, 7)[0],
        'effective': struct.unpack_from('<H', b, 9)[0], 'bonuses': struct.unpack_from('<H', b, 0xB)[0], 'per_use': per_use,
        'price': price if per_use else 0, 'use_effect': b[0x11], 'weapon_effect': b[0x12], 'skills2': b[0x13], 'skills3': b[0x14],
        'traits': traits,
    }


def class_(c):
    a = CLASSES + 36 * (c - 1)
    o = lo(a)
    b = R[o:o + 36]
    return {
        'id': c, 'bases': list(b[0:8]), 'ranks': list(b[9:19]), 'skills1': b[0x13], 'skills2': b[0x14], 'skills3': b[0x15],
        'move_cost': 0x860000 | struct.unpack_from('<H', b, 0x17)[0], 'terrain_avoid': 0x860000 | struct.unpack_from('<H', b, 0x19)[0],
        'terrain_def': 0x860000 | struct.unpack_from('<H', b, 0x1B)[0], 'terrain_hit_avoid': 0x860000 | struct.unpack_from('<H', b, 0x1D)[0],
        'tier1': b[0x23],
    }


def character(c):
    a = CHARACTERS + 48 * (c - 1)
    o = lo(a)
    b = R[o:o + 48]
    return {'id': c, 'class': b[0x2C], 'leadership': b[0x2D], 'skills1': b[0x29], 'skills2': b[0x2A], 'skills3': b[0x2B]}


def chapter(n):
    """A chapter record ($84:804A): its map, the tileset with the terrain table, map changes and starting positions, fog."""
    a = CHAPTERS + 52 * n
    return {
        'tileset_config': u24(a + 9), 'map': u24(a + 15), 'map_changes': u24(a + 18), 'starts': u24(a + 21), 'objective': u24(a + 24),
        'vision': u8(a + 35), 'prep': u8(a + 36), 'min_units': u8(a + 37), 'max_units': u8(a + 38),
    }


def chapter_events(n):
    """The chapter's ten event pointers ($8C:D561)."""
    names = ['opening', 'turn', 'talk', 'location', 'before_action', 'shop', 'battle', 'ending', 'after_action', 'prep_groups']
    return {k: u24(CHAPTER_EVENTS + 30 * n + 3 * i) for i, k in enumerate(names)}


@functools.lru_cache(maxsize=None)
def decompress(src):
    """Runs the game's own decompressor ($80:B574) on the stream at `src`; returns what it writes from $7F:0000."""
    cpu = Cpu(R, lo)
    for i, v in enumerate((src & 0xFF, src >> 8 & 0xFF, src >> 16, 0, 0, 0x7F)):
        cpu.ram[i] = v
    cpu.s, cpu.d, cpu.db = 0x1FFF, 0, 0
    cpu.p = 0x30
    cpu.writes = []
    cpu.call(DECOMPRESS)
    top = max(w & 0xFFFF for w in cpu.writes if w >> 16 == 0x7F)
    return bytes(cpu.ram[0x10000:0x10000 + top + 1])


def map_grid(n):
    """(width, height, rows of metatile numbers) for chapter n: the map is width, height, then a u16 per tile whose top 13 bits
    are the metatile."""
    m = decompress(chapter(n)['map'])
    w, h = m[0], m[2]
    cells = struct.unpack_from(f'<{w * h}H', m, 4)
    return w, h, [[cells[y * w + x] >> 3 for x in range(w)] for y in range(h)]


def terrain_table(n):
    """The terrain id of each metatile: the tileset config's bytes from 0x2000 (the game reads them at $7F:2010, the config being
    unpacked to $7F:0010; 0x83:B476)."""
    return decompress(chapter(n)['tileset_config'])[0x2000:]

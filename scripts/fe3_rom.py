"""
Reader for the user's own Fire Emblem: Mystery of the Emblem (FE3) cartridge image, shared by the FE3 generators. The ROM is the clean
Japanese retail dump, revision 1.1 (the one the translation patch is made for), kept outside the repo (default path below, or set
FE3_ROM); only data built from it is committed. The cartridge is LoROM: the SNES address $BB:AAAA is file offset
(BB & 0x7F) * 0x8000 + (AAAA & 0x7FFF). Little-endian.

Every table here was found in the clean ROM by tracing the game in Mesen and reading its code (data-raw/fe3/README.md has the formats
and the routines that read each one).
"""
import functools
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_cpu import Cpu  # noqa: E402

ROM = os.environ.get('FE3_ROM', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games',
                                             'Fire Emblem - Monshou no Nazo (J) (V1.1).smc'))
CRC32 = 0xA427B7E6

R = open(ROM, 'rb').read()
assert zlib.crc32(R) == CRC32, f'{ROM} is not the clean Mystery of the Emblem 1.1 dump (CRC32 {CRC32:08X})'

ITEMS = 0x88A6E9          # 14 bytes per item id, from 0 (the Iron Sword)
ITEM_COUNT = 0x7F
EFFECTIVE = 0x88A633      # u16 per weapon (item +13): a list of class ids ended by 0xFF
LOCKS = 0x88A48E          # u16 per lock (item +2 with bit 7 set): name ids ended by 0xFF
USERS = 0x88A4B1          # u16 per item (item +12): the class ids that can use it, ended by 0xFF
CHAPTER_MAP = 0x848C15    # chapter number ($07DF) -> map index ($07CE)
MAP_HEADERS = 0x8A8000    # 8 bytes per map index
MAP_GRIDS = 0x89CAB1      # 3 bytes per map index: the compressed grid (bank byte + $A4)
TILESET_TERRAIN = 0x8A81F8  # long pointer per tileset: the terrain id of each of its 1024 metatiles
EVENT_UNITS = 0x888000    # u16 per map index: the units its scripts load by character id (19 bytes each, ended by 0xFF)
START_UNITS = 0x898000    # u16 per map index: the units placed as the chapter loads
REINFORCEMENT_UNITS = 0x889D6D  # 19 bytes each: the units the spawn slots bring in
DEPLOY = 0x89C45C         # u16 per map index: [count][row, col]... the starting tiles of your army
TURN_EVENTS = 0x8CA11C    # u16 per map index: [turn u16][phase][script u24]... ended by FFFF
AREA_EVENTS = 0x8B802E    # u16 per map index: [who][col1][col2][row1][row2][script u24]... ended by FF
CHAR_EVENTS = 0x8B85E0    # u16 per map index: [character][script u24]... ended by FF (runs once that character is gone)
TILE_EVENTS = 0x8C917C    # 10 bytes each, every map's: houses, villages, shops, the arena, secret shops, the seize tile
TILE_OBJECTS = 0x8C9AD3   # 10 bytes each: chests, doors and drawbridges
TILE_SCRIPTS = 0x8C8004   # u16 per event id: the scripts the two tables above run (bank $8C)
TALKS = 0x8B89C6          # 6 bytes each: [map][talker name][target name][flag][event id u16]
TALK_SCRIPTS = 0x8B8A93   # u16 per event id (bank $8B)
SHOPS = 0x8C9044          # 8 items per shop, padded with 0xFE
SUPPORTS = 0x88CD31       # [giver name][receiver name][bonus]... ended by FF
MOVE_COSTS = 0x88B383     # long pointer per class: its cost on each of the 162 terrain ids (0xFF can't enter)
AVOID = 0x88C29E          # long pointer per class: the avoid each terrain id gives
DECOMPRESS = 0x808F18     # the game's decompressor: source long pointer at $71, output at $7E:40FE
TERRAIN_COUNT = 162
MAX_CHAPTER = 44          # chapter numbers 1-20 are Book 1, 21-44 Book 2 (Endgame 1, then Endgame 2's three parts)


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


def ff_list(a):
    """Bytes from a until 0xFF."""
    out = []
    while u8(a) != 0xFF:
        out.append(u8(a))
        a += 1
    return out


# Item type (+0): a bit per kind; 0 is a ballista.
TYPES = {0x01: 'Sword', 0x02: 'Lance', 0x04: 'Bow', 0x08: 'Staff', 0x10: 'Tome', 0x20: 'Item', 0x40: 'Axe', 0x80: 'Breath', 0x00: 'Ballista'}
# Range (+11, low nibble).
RANGES = {0x9: (1, 1), 0xA: (2, 2), 0xB: (1, 2), 0xC: (3, 10)}


def item(i):
    """One item record ($88:A6E9 + 14 x id): its numbers as the game keeps them. A staff's +3 is its own id and its +4 the EXP it
    gives; the price is kept in tens."""
    o = lo(ITEMS) + 14 * i
    b = R[o:o + 14]
    return {
        # The Levin Sword is a sword with the tome bit as well (0x11).
        'id': i, 'type': TYPES[b[0] & 0xEF if b[0] & 0x01 else b[0]], 'magic_sword': b[0] == 0x11, 'rank': b[2] & 0x7F,
        'lock': b[2] & 0x7F if b[2] & 0x80 else None, 'mt': b[3], 'hit': b[4], 'crit': b[5], 'wt': b[6], 'uses': b[8],
        'price': (b[9] | b[10] << 8) * 10, 'flags': b[11], 'range': RANGES.get(b[11] & 0xF), 'users': b[12], 'effective': b[13],
    }


def class_list(table, index):
    return ff_list(0x880000 | u16(table + 2 * index))


EFFECTIVE_COUNT = 60      # the table covers the weapons, ids 0-59; staves and items have none


def effective(i):
    """The class ids a weapon is effective against (none: its list is the empty one most weapons share)."""
    return class_list(EFFECTIVE, item(i)['effective']) if i < EFFECTIVE_COUNT else []


def lock(n):
    """The name ids a locked weapon is for."""
    return class_list(LOCKS, n)


def users(i):
    return class_list(USERS, item(i)['users'])


def chapter_map(n):
    return u8(CHAPTER_MAP + n)


def map_header(m):
    """+0 graphics set, +1 tileset (its terrain table), +2 last column, +3 last row (the cursor stops one short of both, and at 1)."""
    o = lo(MAP_HEADERS) + 8 * m
    b = R[o:o + 8]
    return {'graphics': b[0], 'tileset': b[1], 'cols': b[2] + 1, 'rows': b[3] + 1}


@functools.lru_cache(maxsize=None)
def decompress(src):
    """Runs the game's own decompressor ($80:8F18) on the stream at the SNES address `src`; returns what it writes from $7E:40FE."""
    cpu = Cpu(R, lo)
    for i, v in enumerate((src & 0xFF, src >> 8 & 0xFF, src >> 16)):
        cpu.ram[0x71 + i] = v
    cpu.ram[0x76] = cpu.ram[0x77] = 0
    cpu.writes = []
    cpu.s = 0x1FF0
    cpu.m = cpu.xf = False
    cpu.p = 0
    cpu.call(DECOMPRESS, limit=5_000_000)
    top = max(w for w in cpu.writes if w >> 16 == 0x7E)
    return bytes(cpu.ram[0x40FE:(top & 0xFFFF) + 1])


def map_grid(m):
    """The stored map: 32 x 32 u16 cells (the low 10 bits the metatile), cut to the header's size, rows from the top."""
    o = lo(MAP_GRIDS) + 3 * m
    src = R[o] | R[o + 1] << 8 | ((R[o + 2] + 0xA4) & 0xFF) << 16
    cells = struct.unpack('<1024H', decompress(src)[:0x800])
    h = map_header(m)
    return [[cells[r * 32 + c] for c in range(h['cols'])] for r in range(h['rows'])]


def terrain_ids(m):
    """Each stored tile's terrain id (0-161), rows from the top."""
    table = R[lo(u24(TILESET_TERRAIN + 3 * map_header(m)['tileset'])):][:0x400]
    return [[table[c & 0x3FF] for c in row] for row in map_grid(m)]


def unit_record(a):
    """A 19-byte unit record ($83:DCC1 copies it into the unit): +0 character, +1 class, +2 level, +3 name id (the name shown), +4 row,
    +5 column, +6 the class it changes into (a Manakete's dragon), +7 portrait, +8..+11 its weapon slots, +12 and +13 its item slots,
    +14 u16 its gold, +16..+18 the AI. What a foe has in its item slots, and its gold, are what it leaves when it falls ($83:AE1B
    stores them as the battle's spoils)."""
    b = R[lo(a):lo(a) + 19]
    weapons = [i for i in b[8:12] if i != 0xFF]
    drops = [i for i in b[12:14] if i != 0xFF]
    gold = b[14] | b[15] << 8
    return {'char': b[0], 'class': b[1], 'level': b[2], 'name': b[3], 'row': b[4], 'col': b[5], 'portrait': b[7],
            'weapons': weapons, 'drops': drops, 'items': weapons + drops, 'gold': 0 if gold == 0xFFFF else gold,
            'ai': tuple(b[16:19]), 'at': a}


def unit_list(table, m):
    a = (table & 0xFF0000) | u16(table + 2 * m)
    out = []
    while u8(a) != 0xFF:
        out.append(unit_record(a))
        a += 19
    return out


def reinforcement_unit(k):
    return unit_record(REINFORCEMENT_UNITS + 19 * k)


def deploy_tiles(m):
    a = 0x890000 | u16(DEPLOY + 2 * m)
    return [(u8(a + 1 + 2 * k), u8(a + 2 + 2 * k)) for k in range(u8(a))]


def turn_events(m):
    a, out = 0x8C0000 | u16(TURN_EVENTS + 2 * m), []
    while u16(a) != 0xFFFF:
        out.append({'turn': u16(a), 'phase': u8(a + 2), 'ptr': u24(a + 3)})
        a += 6
    return out


def area_events(m):
    a, out = 0x8B0000 | u16(AREA_EVENTS + 2 * m), []
    while u8(a) != 0xFF:
        out.append({'who': u8(a), 'cols': (u8(a + 1), u8(a + 2)), 'rows': (u8(a + 3), u8(a + 4)), 'ptr': u24(a + 5)})
        a += 8
    return out


def char_events(m):
    a, out = 0x8B0000 | u16(CHAR_EVENTS + 2 * m), []
    while u8(a) != 0xFF:
        out.append({'char': u8(a), 'ptr': u24(a + 1)})
        a += 4
    return out


def tile_records(table):
    """[map][who: 0 your army, FF anyone][col][row][flag][kind][event id u16][u16]."""
    a, out = table, []
    while u8(a) != 0xFF:
        b = R[lo(a):lo(a) + 10]
        out.append({'map': b[0], 'who': b[1], 'col': b[2], 'row': b[3], 'flag': b[4], 'kind': b[5], 'id': b[6] | b[7] << 8,
                    'extra': b[8] | b[9] << 8})
        a += 10
    return out


def tile_script(event_id):
    return 0x8C0000 | u16(TILE_SCRIPTS + 2 * event_id)


def talks():
    a, out = TALKS, []
    while u8(a) != 0xFF:
        out.append({'map': u8(a), 'talker': u8(a + 1), 'target': u8(a + 2), 'flag': u8(a + 3), 'id': u16(a + 4),
                    'ptr': 0x8B0000 | u16(TALK_SCRIPTS + 2 * u16(a + 4))})
        a += 6
    return out


def shop(n):
    o = lo(SHOPS) + 8 * n
    return [i for i in R[o:o + 8] if i != 0xFE]


def supports():
    a, out = SUPPORTS, []
    while u8(a) != 0xFF:
        out.append((u8(a), u8(a + 1), u8(a + 2)))
        a += 3
    return out


def move_costs(c):
    return R[lo(u24(MOVE_COSTS + 3 * c)):][:TERRAIN_COUNT]


def avoid_row(c):
    return R[lo(u24(AVOID + 3 * c)):][:TERRAIN_COUNT]

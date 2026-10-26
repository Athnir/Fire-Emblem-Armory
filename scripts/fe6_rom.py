"""
Reader for the user's own Fire Emblem: Fuuin no Tsurugi (FE6, The Binding Blade) cartridge image, shared by the FE6 generators. The ROM
is the clean Japanese dump (GBA, game code AFEJ), kept outside the repo (default path below, or set FE6_ROM); only data built from it
is committed. Offsets are file offsets; the game addresses them as 0x08000000 + offset. Formats are in data-raw/fe6/README.md (and the
user's breakdown in Documents\\FE Games\\notes).
"""
import os
import struct
import zlib

ROM = os.environ.get('FE6_ROM', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Fire Emblem - Fuuin no Tsurugi (J) [!].gba'))
CRC32 = 0xD38763E1

TEXT_TABLE = 0x0F635C   # u32 pointer per text id
HUFF_TREE = 0x0F300C    # Huffman nodes: u16 left, u16 right; right == 0xFFFF marks a leaf (left = the character)
HUFF_ROOT_PTR = 0x0F6358  # u32 pointer to the root node
CHARACTERS = 0x6076D0   # 48 bytes each, ids 0-225
CLASSES = 0x60A0E8      # 72 bytes each, ids 0-75
ITEMS = 0x60B648        # 32 bytes each, ids 0-127
TERRAIN_NAMES = 0x60D00C  # u32 pointers to plain strings, 51 terrain ids
CHAPTERS = 0x6637A0     # 68 bytes each, 45 entries
POINTERS = 0x664398     # the central pointer table chapters index into
EVENT_COMMANDS = 0x5C4164  # per opcode: u32 handler (Thumb), u32 length in words (opcode included)

R = open(ROM, 'rb').read()
assert zlib.crc32(R) == CRC32, f'{ROM} is not the clean Japanese ROM'


def u8(o):
    return R[o]


def u16(o):
    return struct.unpack_from('<H', R, o)[0]


def s8(o):
    return struct.unpack_from('<b', R, o)[0]


def u32(o):
    return struct.unpack_from('<I', R, o)[0]


def off(v):
    """A ROM pointer (0x08xxxxxx) as a file offset."""
    return v - 0x08000000


def huffman(rom, table, i):
    """Text id `i` of a text table as its raw character codes: one byte below 0x100, else a two-byte Shift-JIS code (lead byte in
    the low half). Control codes (below 0x20) are kept. The tree and its root are the ROM's own (0x0F300C, root pointer 0x0F6358)."""
    def h16(o):
        return struct.unpack_from('<H', rom, o)[0]

    p = struct.unpack_from('<I', rom, table + 4 * i)[0] - 0x08000000
    root = struct.unpack_from('<I', rom, HUFF_ROOT_PTR)[0] - 0x08000000
    out, node, bit = [], root, 0
    while True:
        while h16(node + 2) != 0xFFFF:
            b = (rom[p] >> bit) & 1
            bit += 1
            if bit == 8:
                bit, p = 0, p + 1
            node = HUFF_TREE + (h16(node + 2) if b else h16(node)) * 4
        v = h16(node)
        if v == 0:
            return out
        out.append(v)
        node = root


def text(i):
    """A Japanese text id decoded to a string."""
    out = bytearray()
    for v in huffman(R, TEXT_TABLE, i):
        out += bytes([v]) if v < 0x100 else bytes([v & 0xFF, v >> 8])
    return out.decode('shift_jis', 'replace')


ITEM_TYPES = {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Staff', 5: 'Anima', 6: 'Light', 7: 'Dark', 9: 'Item', 0xB: 'Dragonstone'}
RANKS = [(251, 'S'), (201, 'A'), (151, 'B'), (101, 'C'), (51, 'D'), (1, 'E')]


def item(i):
    """One 32-byte item record (see the README for the fields)."""
    e = ITEMS + i * 32
    return {
        'id': i, 'name_id': u16(e), 'desc_id': u16(e + 2), 'type': R[e + 7], 'attributes': u32(e + 8),
        'stat_bonus': u32(e + 0xC), 'effective': u32(e + 0x10), 'uses': R[e + 0x14], 'mt': R[e + 0x15], 'hit': R[e + 0x16],
        'wt': R[e + 0x17], 'crit': R[e + 0x18], 'range': (R[e + 0x19] >> 4, R[e + 0x19] & 0xF), 'cost': u16(e + 0x1A),
        'rank': R[e + 0x1C], 'use_effect': R[e + 0x1E], 'weapon_effect': R[e + 0x1F],
    }


def class_(c):
    e = CLASSES + c * 72
    return {'id': c, 'name_id': u16(e), 'promotes_to': R[e + 5], 'abilities': u32(e + 0x24), 'move_cost': off(u32(e + 0x34)),
            'terrain_avoid': off(u32(e + 0x38)), 'terrain_def': off(u32(e + 0x3C)), 'terrain_res': off(u32(e + 0x40))}


def character(c):
    e = CHARACTERS + c * 48
    return {'id': c, 'name_id': u16(e), 'class': R[e + 5], 'affinity': R[e + 9], 'level': R[e + 0xB], 'abilities': u32(e + 0x28),
            'supports': u32(e + 0x2C)}


def class_list(p):
    """A list of class ids ending in 0 (an item's effectiveness list), from a ROM pointer."""
    o, out = off(p), []
    while R[o]:
        out.append(R[o])
        o += 1
    return out

"""
Reader for the user's own Fire Emblem: Seisen no Keifu (FE4, Genealogy of the Holy War) cartridge image, shared by the FE4
generators. The ROM is the clean Japanese dump, kept outside the repo (default path below, or set FE4_ROM); only data built from it
is committed. Offsets are file offsets; the SNES address $XX:YYYY is (XX & 0x3F) * 0x10000 + YYYY (HiROM, no copier header).
Formats are in data-raw/fe4/README.md.
"""
import os
import struct

ROM = os.environ.get('FE4_ROM', r'C:\Users\golds\Documents\FE Games\Fire Emblem - Seisen no Keifu (J).smc')
CRC32 = 0xDC0D8CF9

ITEM_POINTERS = 0x3E9D0   # u16 offsets from this address, one per item id (0x00-0x88)
ITEM_NAMES = 0x0D9402     # u16 pointers into bank $CD (Japanese; the kanji pages aren't read, so English names come from Serenes)
ITEM_COUNT = 137

R = open(ROM, 'rb').read()


def u16(o):
    return struct.unpack_from('<H', R, o)[0]


TYPES = ['Sword', 'Lance', 'Axe', 'Bow', 'Staff', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark']
RANKS = {0: 'A', 1: 'B', 2: 'C', 0xFF: '*'}


def item(i):
    """One entry of the item table (weapons, staves and rings), as a dict of the raw fields."""
    e = ITEM_POINTERS + u16(ITEM_POINTERS + 2 * i)
    if R[e + 1] == 2:  # a ring: 10 bytes
        return {'id': i, 'kind': 'ring', 'price': u16(e + 3), 'rank': RANKS.get(R[e + 7], R[e + 7]), 'skills': R[e + 8], 'skills2': R[e + 9]}
    return {
        'id': i, 'kind': ('weapon', 'staff')[R[e + 1]], 'uses': R[e + 2], 'price': u16(e + 3), 'holy': R[e + 5],
        'staff_effect': R[e + 6], 'rank': RANKS.get(R[e + 7], R[e + 7]), 'skills': R[e + 8], 'type': TYPES[R[e + 0xA]],
        'mt': R[e + 0xB], 'hit': R[e + 0xC], 'wt': R[e + 0xD], 'range': (R[e + 0xE], R[e + 0xF]), 'effective': R[e + 0x10],
        'effect': R[e + 0x11], 'effect_arg': R[e + 0x12],
    }

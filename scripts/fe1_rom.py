"""Read Shadow Dragon and the Blade of Light's cartridge (`data-raw/fe1/rom/fe1.nes`, written by fe1_extract.py).

MMC4 (mapper 10): 16 PRG banks of 16 KB, bank n switched in at $8000-$BFFF, the last (15) fixed at $C000-$FFFF. An address is
given as (bank, $addr); a $C000-$FFFF address is always bank 15. Data is little-endian.
"""
import os
import struct

from capstone import CS_ARCH_MOS65XX, CS_MODE_MOS65XX_6502, Cs

ROM = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe1', 'rom', 'fe1.nes')
_rom = open(ROM, 'rb').read()
assert _rom[:4] == b'NES\x1a' and _rom[4] == 16, 'run fe1_extract.py first'
PRG = _rom[16:16 + 16 * 0x4000]
FIXED = 15


def offset(bank, addr):
    if addr >= 0xC000:
        return FIXED * 0x4000 + addr - 0xC000
    assert 0x8000 <= addr < 0xC000, hex(addr)
    return bank * 0x4000 + addr - 0x8000


def read(bank, addr, n):
    o = offset(bank, addr)
    return PRG[o:o + n]


def u8(bank, addr):
    return PRG[offset(bank, addr)]


def u16(bank, addr):
    return struct.unpack_from('<H', PRG, offset(bank, addr))[0]


def string(bank, addr):
    """A string in the NES's text encoding, ended by 0xEF (the end mark not included)."""
    o = offset(bank, addr)
    return PRG[o:PRG.index(0xEF, o)]


_md = Cs(CS_ARCH_MOS65XX, CS_MODE_MOS65XX_6502)
_md.skipdata = True  # data in the middle of code shows as .byte instead of ending the listing


def dis(bank, addr, n=0x40):
    """6502 disassembly of n bytes, as text lines."""
    return [f'{bank:2d}:${i.address:04X}  {i.bytes.hex(" "):9s} {i.mnemonic} {i.op_str}'
            for i in _md.disasm(read(bank, addr, n), addr)]


# Items: one array per field, 92 entries each, indexed by item number (fixed bank).
ITEMS = 92
ITEM_FIELDS = {
    'mt': 0xD657, 'level': 0xD6B3, 'wt': 0xD70F, 'hit': 0xD76B, 'crit': 0xD7C7, 'price': 0xD823, 'uses': 0xD87F,
    'effective': 0xD8DB,
}
ITEM_NAMES = 0xDAD5        # u16 pointers to each item's name (NES text)
EFFECTIVE_LISTS = 0xD937   # u16 pointers by the item's 'effective' value: class numbers ended by FF
CLASS_NAMES = 0xDA1F       # u16 pointers, class number - 1
ARMY_NAMES = 0xDFA4        # u16 pointers: foes' names and armies


def item(i):
    rec = {k: u8(FIXED, a + i) for k, a in ITEM_FIELDS.items()}
    rec['id'] = i
    rec['name_codes'] = string(FIXED, u16(FIXED, ITEM_NAMES + 2 * i))
    return rec


def class_list(addr):
    out = []
    while (c := u8(FIXED, addr)) != 0xFF:
        out.append(c)
        addr += 1
    return out


def effective_classes(index):
    return class_list(u16(FIXED, EFFECTIVE_LISTS + 2 * index)) if index else []


def class_name_codes(cls):
    return string(FIXED, u16(FIXED, CLASS_NAMES + 2 * (cls - 1)))


# --- chapters (data-raw/fe1/README.md, "Chapters") ---

CHAPTERS = 25
TILE_TERRAIN = 0xE828      # graphic tile -> terrain code (your side's table; codes 14 and 31 mark units)
TERRAIN_AVOID = 0xEBD8     # by terrain code
TERRAIN_NAME = 0xEBEE      # by terrain code: the battle's terrain name (into 0xE5F1's 16)
MOVE_COSTS = 0xE9C8        # u16 pointers by class - 1: 22 costs, 255 can't enter
TERRAIN_CODES = 22


def _list(bank, table, ch):
    return u16(bank, table + 2 * (ch - 1))


def map_grid(ch):
    """(rows, cols, grid of graphic tiles) as stored: the playable map is this without its outer ring (the cursor's limits, 6:$A97B)."""
    bank, n = (2, ch) if ch <= 13 else (9, ch - 13)
    p = _list(bank, 0x8000, n)
    h = read(bank, p, 4)
    rows, cols = h[0] + 1, h[1] + 1
    return rows, cols, [list(read(bank, p + 4 + r * cols, cols)) for r in range(rows)]


def unit_records(bank, table, ch, size):
    p, out = _list(bank, table, ch), []
    while u8(bank, p):
        out.append(read(bank, p, size))
        p += size
    return out


def foes(ch):
    """The chapter's foes (8:$8AA3): 11-byte records [character][class][level][item][item][row][column][AI x4]; the first is the boss."""
    return unit_records(8, 0x8AA3, ch, 11)


def allies(ch):
    """Your units the chapter brings (8:$8490): whole 27-byte records (Chapter 1's: the starting army)."""
    return unit_records(8, 0x8490, ch, 27)


def village_recruits(ch):
    """The unit a village whose value is 0x80 recruits (3:$9466)."""
    return unit_records(3, 0x9466, ch, 27)


def reinforcements(ch):
    """3:$959C: foes' 11-byte records; +8: bit 7 clear the turn it arrives, set every turn after +8 & 0x7F up to last_turn()."""
    return unit_records(3, 0x959C, ch, 11)


def last_turn(ch):
    return u8(3, 0xA44E + ch - 1)


def deploy_tiles(ch):
    """8:$8790: [count] then (row, column) pairs."""
    p = _list(8, 0x8790, ch)
    if p == _list(8, 0x8790, ch + 1) if ch < CHAPTERS else False:
        return []
    n = u8(8, p)
    return [tuple(read(8, p + 1 + 2 * k, 2)) for k in range(n)]


def visits(ch):
    """3:$A0F1: 5-byte entries (row, column, a, b, c) ended by a 0 row."""
    p, out = _list(3, 0xA0F1, ch), []
    while u8(3, p) >= 1:
        out.append(tuple(read(3, p, 5)))
        p += 5
    return out


def shops(ch):
    """11:$A4FF: 4-byte entries (row, column, kind, list) ended by F0."""
    p, out = _list(11, 0xA4FF, ch), []
    while u8(11, p) != 0xF0:
        out.append(tuple(read(11, p, 4)))
        p += 4
    return out


def shop_stock(n):
    """11:$A6C2: a list of item numbers + 1, ended by F0."""
    p, out = u16(11, 0xA6C2 + 2 * n), []
    while (i := u8(11, p)) != 0xF0:
        out.append(i - 1)
        p += 1
    return out


def recruit_conditions(ch):
    """3:$A3C1 (a list number by chapter) and 3:$A3DA: 4-byte entries [foe][the character it becomes][?][a character that must be in
    your army, 0 none]."""
    k = u8(3, 0xA3C1 + ch - 1)
    if not k:
        return []
    p, out = u16(3, 0xA3DA + 2 * (k - 1)), []
    while u8(3, p):
        out.append(tuple(read(3, p, 4)))
        p += 4
    return out


def move_costs(cls):
    return read(FIXED, u16(FIXED, MOVE_COSTS + 2 * (cls - 1)), TERRAIN_CODES)


def talks():
    """The talk table (15:$EDB5 talkers, $EDC4 the foe each talks to, $EDE0 the character it becomes; read by 3:$9F4E): (talker,
    foe, becomes). The Ogma -> foe 0xBE (セイバー) entry names no foe any chapter has."""
    out, y = [], 0
    while (t := u8(FIXED, 0xEDB5 + y)):
        out.append((t, u8(FIXED, 0xEDC4 + y), u8(FIXED, 0xEDE0 + y)))
        y += 1
    return out

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

"""
Fire Emblem Gaiden (FE2, Famicom, 1992): the cartridge and its English fan translation's text.

Input: the user's own ROM, `Documents\\FE Games\\Fire Emblem Gaiden.nes` (FE2_ROM overrides it). It is an iNES file: a 16-byte
header ('NES' 1A, 16 PRG banks of 16 KB, 16 CHR banks of 8 KB, flags 6 = $A2: mapper 10 (MMC4), battery), then 256 KB of PRG and
128 KB of CHR. MMC4 switches $8000-$BFFF (a write to $A000 picks the bank, 15:$CA40) and fixes the last bank at $C000-$FFFF. CHR
is switched in 4 KB banks ($B000/$C000 for pattern table $0000, $D000/$E000 for $1000).

The ROM has an English fan translation patched in; no clean Japanese ROM is to hand, so everything is read from this one (the
user's call). The patch changes text and its pointers; the tables match Serenes Forest's numbers, so it left them alone (checked in
src/logic/__tests__/fe2.test.ts; see data-raw/fe2/README.md). Copied from the Unit Planner's scripts/fe2_rom.py.

Addresses are bank:$addr (bank 15 at $C000-$FFFF).

Text: a byte is the tile the game draws (CHR bank 0, the font), so the "encoding" is the font:
  $45-$4D a-i, $4E j, $4F ' (apostrophe), $50-$5F k-z, $60-$69 0-9, $6A-$83 A-Z, $FF space, $8B , $8C ; $8D : $8F . $9C ? $9D !
  $3F -, and tiles that draw two letters at once: $39 ll, $3C lt, $3D ti, $3E it, $40 il, $41 li, $42 's, $43 't, $44 'r, $38 lf;
  $36 $37 together draw "ata" and $3A $3B "att" (a letter split across two tiles). $30-$34 are the icons item names end with:
  lance, sword, bow, shield, ring. $96-$9A are leftover kana (あいうえお). $EF ends a string, $ED is a new line.
  Dialogue adds control codes (10:$8588): $DF b, $E1 b, $E9 b, $EC b (insert string b), $F0 b, $E4 b b, $E8 x y p (a portrait p at
  x, y: 10:$84D0), and $E0 $E2 $E3 $E5 $E6 $E7 $EA $EB $EE $F1 alone.
"""
import os
import struct

ROM = os.environ.get('FE2_ROM', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Fire Emblem Gaiden.nes'))
PRG_BANK, CHR_BANK, FIXED = 0x4000, 0x2000, 15

# The font (CHR bank 0): tile -> text.
TILES = {0xFF: ' ', 0xED: '\n', 0x8B: ',', 0x8C: ';', 0x8D: ':', 0x8F: '.', 0x9C: '?', 0x9D: '!', 0x3F: '-', 0x90: '-', 0x93: '.',
         0x9B: '·', 0x35: 't', 0x36: 'a', 0x37: 'ta', 0x38: 'lf', 0x39: 'll', 0x3A: 'a', 0x3B: 'tt', 0x3C: 'lt', 0x3D: 'ti',
         0x3E: 'it', 0x40: 'il', 0x41: 'li', 0x42: "'s", 0x43: "'t", 0x44: "'r", 0x4E: 'j', 0x4F: "'", 0x84: 'P', 0x85: 'f'}
for _i in range(9):
    TILES[0x45 + _i] = chr(ord('a') + _i)
for _i in range(16):
    TILES[0x50 + _i] = chr(ord('k') + _i)
for _i in range(10):
    TILES[0x60 + _i] = chr(ord('0') + _i)
for _i in range(26):
    TILES[0x6A + _i] = chr(ord('A') + _i)
for _i, _k in enumerate('あいうえお'):
    TILES[0x96 + _i] = _k
# The icons at the end of item names (an item is "Steel" + the lance icon).
ICONS = {0x30: 'Lance', 0x31: 'Sword', 0x32: 'Bow', 0x33: 'Shield', 0x34: 'Ring'}
# Dialogue control codes and how many bytes follow each (10:$8588 and 10:$84D0).
CONTROL_ARGS = {0xDF: 1, 0xE1: 1, 0xE9: 1, 0xEC: 1, 0xF0: 1, 0xE4: 2, 0xE8: 3,
                0xE0: 0, 0xE2: 0, 0xE3: 0, 0xE5: 0, 0xE6: 0, 0xE7: 0, 0xEA: 0, 0xEB: 0, 0xEE: 0, 0xF1: 0}
END = 0xEF


def decode(codes, icons=False):
    """Plain text (names, menus): each byte its glyph; an unknown byte as [xx]. With `icons`, an item icon becomes its word."""
    out = []
    for b in codes:
        if icons and b in ICONS:
            out.append(' ' + ICONS[b])
        else:
            out.append(TILES.get(b, f'[{b:02x}]'))
    return ''.join(out)


def decode_dialogue(codes):
    """Dialogue as read: control codes dropped (with their arguments), $E6 (end of a speaker's part) a line break. Returns the text
    and the portraits ($E8 x y p) in order."""
    out, speakers, i = [], [], 0
    while i < len(codes):
        b = codes[i]
        if b in CONTROL_ARGS:
            if b == 0xE8:
                speakers.append(codes[i + 3])
            if b == 0xE6:
                out.append('\n')
            i += 1 + CONTROL_ARGS[b]
            continue
        out.append(TILES.get(b, f'[{b:02x}]'))
        i += 1
    return ''.join(out), speakers


class Rom:
    def __init__(self, path=None):
        data = open(path or ROM, 'rb').read()
        assert data[:4] == b'NES\x1a', 'not an iNES file'
        prg_banks, chr_banks, f6, f7 = data[4], data[5], data[6], data[7]
        self.mapper = (f6 >> 4) | (f7 & 0xF0)
        assert self.mapper == 10, f'mapper {self.mapper}, not MMC4'
        assert prg_banks == 16 and chr_banks == 16, (prg_banks, chr_banks)
        self.battery = bool(f6 & 2)
        start = 16 + (512 if f6 & 4 else 0)
        self.prg = data[start:start + prg_banks * PRG_BANK]
        self.chr = data[start + len(self.prg):start + len(self.prg) + chr_banks * CHR_BANK]
        self.header = data[:16]

    # --- the banks ---
    def off(self, bank, addr):
        if addr >= 0xC000:
            return FIXED * PRG_BANK + addr - 0xC000
        assert 0x8000 <= addr < 0xC000, hex(addr)
        return bank * PRG_BANK + addr - 0x8000

    def u8(self, bank, addr):
        return self.prg[self.off(bank, addr)]

    def u16(self, bank, addr):
        return struct.unpack_from('<H', self.prg, self.off(bank, addr))[0]

    def read(self, bank, addr, n):
        o = self.off(bank, addr)
        return self.prg[o:o + n]

    def codes(self, bank, addr):
        """A string's bytes, up to its $EF."""
        o = self.off(bank, addr)
        return self.prg[o:self.prg.index(END, o)]

    def string(self, bank, addr, icons=False):
        return decode(self.codes(bank, addr), icons)

    def string_at(self, bank, table, index, icons=False):
        """String `index` of a table of u16 pointers in the same bank (or the fixed bank)."""
        return self.string(bank, self.u16(bank, table + 2 * index), icons)

    # --- dialogue ---
    def dialogue(self, n):
        """A town scene's text n (script op 3, 13:$9550): n < $4C is bank 3's table 0, otherwise bank 10's table 1 at n - $4C; a
        bank's text tables are listed at its $BFE0 (15:$E6DA). Returns (bank, address, raw codes)."""
        bank, sel, idx = (3, 0, n) if n < 0x4C else (10, 1, n - 0x4C)
        table = self.u16(bank, 0xBFE0 + 2 * sel)
        p = self.u16(bank, table + 2 * idx)
        return bank, p, self.codes(bank, p)

    # --- graphics ---
    def tile(self, chr4k, t):
        """An 8x8 tile of a 4 KB CHR bank as 2-bit pixel rows."""
        o = chr4k * 0x1000 + t * 16
        lo, hi = self.chr[o:o + 8], self.chr[o + 8:o + 16]
        return [[((lo[y] >> (7 - x)) & 1) | (((hi[y] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def load(path=None):
    return Rom(path)


if __name__ == '__main__':
    r = load()
    print(f'mapper {r.mapper}, PRG {len(r.prg) // 1024} KB, CHR {len(r.chr) // 1024} KB, battery {r.battery}')
    print(r.string(FIXED, r.u16(FIXED, 0xDEA9)), r.string(FIXED, r.u16(FIXED, 0xDEAB)))

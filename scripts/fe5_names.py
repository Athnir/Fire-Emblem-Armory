"""
Thracia 776's English names, read from Lil' Manster, the translation patch Serenes Forest hosts (Lil-Manster-1.08.zip, next to the ROM
in Documents\FE Games, or set FE5_PATCH). The patch is applied in memory to the user's clean ROM (scripts/bps.py) and only its name
tables are read, by the ROM's own ids: every number and table the generators use still comes from the clean ROM. Nothing patched is
written anywhere.

Lil' Manster draws its menu text from pre-built tiles: a name is a list of u16 codes, each a pair of 4-pixel-wide letters, looked up
in the patch's table at $BF:B704 (6 bytes each: the code, then the upper and lower 8x8 tile, 2bpp, at file offset 0x39CC80). So a
name is read by drawing each pair and matching its two halves against the shapes of the patch font's letters (GLYPHS: 4x16 pixels,
one byte per row), the font of the Lil' Manster team's menu text formatter (github.com/famitino/fe776br, text_menus/textformatter).
Wide letters span cells ("[m" is m, "]w" w, "(M" M, ")W" W, "+N" N; "12" an end-of-word w, "34" 's, "0" ö), and two pairs draw "im"
and "mm" with the m running into the next cell (TIED).

Tables (u16 pointers): items at $B0:8FC3 (bank $B0), classes at $89:8000 (bank $89), characters at $86:DA4D (bank $86).

    python scripts/fe5_names.py           # prints every table
"""
import functools
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bps import apply  # noqa: E402
from fe5_rom import R, lo  # noqa: E402

PATCH = os.environ.get('FE5_PATCH', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Lil-Manster-1.08.zip'))
PATCH_FILE = "Lil' Manster 1.08.bps"
PAIRS, PAIRS_END = 0xBFB704, 0xBFC502
FONT = 0x39CC80
ITEM_NAMES, CLASS_NAMES, CHARACTER_NAMES = 0xB08FC3, 0x898000, 0x86DA4D

GLYPHS = {
    '00000000000000000000000000000000': ' ',
    '00000000002c2c2c2c2c2c30002c3000': '!',
    '00000000000064bbbb67bbbab966ff00': '&',
    '00000000202c30000000000000000000': "'",
    '0000000000b090aca79bb9b6beb3c000': '(',
    '0000000000b0b0b0b2b6b99be72c3000': ')',
    '000000000090a49bb9b6beb3b3b0c000': '+',
    '0000000000000000000000000b0b273c': ',',
    '000000000000000000000000002c3000': '.',
    '000000000000bbcc64bbbbbbbb67fc00': '0',
    '0000000000000000b0bbbb99ee223300': '1',
    '0000000000000000b0b0b0b0c0c00000': '2',
    '00000000202c3000060b060d030a0f00': '3',
    '0000000000000000b0c070b0b070c000': '4',
    '0000000000000000002c3c00002c3c00': ':',
    '000000000069beb2c61b2c30002c3000': '?',
    '000000000064bbbbbbabbbbbbbbbcc00': 'A',
    '0000000000a4bbbbbba4bbbbbba7fc00': 'B',
    '00000000006bbcb0b0b0b0b0b06bfc00': 'C',
    '0000000000a4bbbbbbbbbbbbbba7fc00': 'D',
    '0000000000abbcb0b0abbcb0b0abfc00': 'E',
    '0000000000abbcb0b0abbcb0b0b0c000': 'F',
    '00000000006bbcb0b098bbbbbb67fc00': 'G',
    '0000000000bbbbbbbbabbbbbbbbbcc00': 'H',
    '0000000000abec2c2c2c2c2c2cabfc00': 'I',
    '00000000002a3b0b0b0b0b0b8b67fc00': 'J',
    '0000000000bbbbbbbba4bbbbbbbbcc00': 'K',
    '0000000000b0b0b0b0b0b0b0b0abfc00': 'L',
    '00000000000b1b2b6b9bbb7bcb0b0c00': 'M',
    '00000000000b0b0b0bcb7bbb9beb3c00': 'N',
    '000000000064bbbbbbbbbbbbbb67fc00': 'O',
    '0000000000a4bbbbbba7bcb0b0b0c000': 'P',
    '0000000000a4bbbbbba4bbbbbbbbcc00': 'R',
    '00000000006bbcb0b06cdb3b0ba7fc00': 'S',
    '0000000000abec2c2c2c2c2c2c2c3000': 'T',
    '0000000000bbbbbbbbbbbbbbbb67fc00': 'U',
    '0000000000bbbbbbbbbbbb9b67ec3000': 'V',
    '00000000000b0b0bcb7bbb9b6cec3000': 'W',
    '0000000000bbbbbb67ec679bbbbbcc00': 'X',
    '0000000000bbbbbb67ec2c2c2c2c3000': 'Y',
    '0000000000abfb0b272c2c9cb0abfc00': 'Z',
    '0000000000000000a9beb2b2b2b2c300': '[',
    '0000000000000000b2b6b99be72c3000': ']',
    '00000000000000006bbbbbbbb966ff00': 'a',
    '0000000000b0b0b0a4bbbbbbbba7fc00': 'b',
    '00000000000000006bbcb0b0b06bfc00': 'c',
    '00000000000b0b0b6bbbbbbbb966ff00': 'd',
    '000000000000000064bbabbcb06bfc00': 'e',
    '0000000000192e2fabec2c2c2c2c3000': 'f',
    '00000000000000006bbbbbbbbb6bfba7': 'g',
    '0000000000b0b0b0a4bbbbbbbbbbcc00': 'h',
    '00000000002c30002c2c2c2c2c2c3000': 'i',
    '00000000000b0c000b0b0b0b0b0b0ba7': 'j',
    '0000000000b0b0bbbba4bbbbbbbbcc00': 'k',
    '00000000002c2c2c2c2c2c2c2c2c3000': 'l',
    '0000000000000000a4fbcbcbcbcb0c00': 'm',
    '0000000000000000a4bbbbbbbbbbcc00': 'n',
    '000000000000000064bbbbbbbb67fc00': 'o',
    '0000000000000000a4bbbbbbbba7bcb0': 'p',
    '00000000000000006bbbbbbbbb6b3b0b': 'q',
    '0000000000000000bba7bcb0b0b0c000': 'r',
    '00000000000000006bbc67db3ba7fc00': 's',
    '00000000002c2c2cabec2c2c2c2c3000': 't',
    '0000000000000000bbbbbbbbbb67fc00': 'u',
    '0000000000000000bbbbbb9b67ec3000': 'v',
    '0000000000000000cb7bbb9b6cec3000': 'w',
    '00000000000000008bbb64649bbbcc00': 'x',
    '0000000000000000bbbbbbbb6bfb0ba7': 'y',
    '0000000000000000abdb276c9cabfc00': 'z',
    '00000000001b273c6bbbbbbbb966ff00': 'á',
    '00000000001b273c64bbabbcb06bfc00': 'é',
    '0000000000bbe43b6bbbbbbbbb67fc00': 'ð',
    '0000000000bbcc0064bbbbbbbb67fc00': 'ö',
}
# Cells drawn only inside a tied pair: "i" with an m starting, the first m of "mm", and the second m's start (each closes with the
# next cell, an n-shaped m end).
TIED = {
    '0000000000b0c000babbbbbbbbbbcc00': 'i\0',   # "im", pair 6D69
    '0000000000000000a6bbbbbbbbbbcc00': 'm',     # "mm", pair 6D31
    '00000000000000004abbbbbbbbbbcc00': '\0',
    '000000000000000040b0b0b0b0b0c000': '',      # a word's last m ends here, pair 6D32
}
WIDE = [('[m', 'm'), (']w', 'w'), ('(M', 'M'), (')W', 'W'), ('+N', 'N'), ('12', 'w'), ('34', "'s "), ('0', 'ö'), ('  ', ' ')]


@functools.lru_cache(maxsize=None)
def patched():
    with zipfile.ZipFile(PATCH) as z:
        return apply(bytes(R), z.read(PATCH_FILE))


def _u16(o):
    return struct.unpack_from('<H', patched(), o)[0]


@functools.lru_cache(maxsize=None)
def _pairs():
    o, end = lo(PAIRS), lo(PAIRS_END)
    return {_u16(i): (_u16(i + 2), _u16(i + 4)) for i in range(o, end, 6)}


def _tile(t):
    p = patched()
    o = FONT + 16 * (t & 0x3FF)
    rows = [[(p[o + 2 * y] >> (7 - x) & 1) | (p[o + 2 * y + 1] >> (7 - x) & 1) << 1 for x in range(8)] for y in range(8)]
    if t & 0x4000:
        rows = [r[::-1] for r in rows]
    if t & 0x8000:
        rows = rows[::-1]
    return rows


def _cells(code):
    upper, lower = _pairs()[code]
    rows = _tile(upper) + _tile(lower)
    return [''.join('%02x' % (r[h] << 6 | r[h + 1] << 4 | r[h + 2] << 2 | r[h + 3]) for r in rows) for h in (0, 4)]


def string_at(o):
    """The name at file offset o in the patched ROM: pairs up to a 0 code."""
    out = ''
    while (code := _u16(o)):
        for cell in _cells(code):
            if cell in GLYPHS:
                out += GLYPHS[cell]
            elif cell in TIED:
                out += TIED[cell]
            else:
                raise KeyError(f'no letter for a cell of pair {code:04X} at {o:X}')
        o += 2
    for a, b in WIDE:
        out = out.replace(a, b)
    return out.replace('\0n', 'm').strip()


def table(at, count):
    bank = at & 0xFF0000
    return [string_at(lo(bank | _u16(lo(at) + 2 * i))) for i in range(count)]


def item_names(count=0xA0):
    return dict(enumerate(table(ITEM_NAMES, count)))


def class_names(count=0x78):
    return dict(enumerate(table(CLASS_NAMES, count)))


CHARACTER_COUNT = 0x157


def character_names(count=CHARACTER_COUNT):
    return dict(enumerate(table(CHARACTER_NAMES, count)))


@functools.lru_cache(maxsize=None)
def generic_names():
    """Names that stand for a kind of unit, not a person: an army's or a class's (Munster, Friege, Civilian, Knight), any name three
    or more characters share, and the few armies only two share."""
    names = character_names()
    counts = {}
    for n in names.values():
        counts[n] = counts.get(n, 0) + 1
    return {n for n, c in counts.items() if c >= 3} | set(class_names().values()) | {'Supply', 'Gelbenritter', 'Pirate', 'Soldier'}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('items', item_names())
    print('classes', class_names())
    print('characters', character_names())

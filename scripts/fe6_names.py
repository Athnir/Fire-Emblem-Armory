"""
The Binding Blade's English names, read from the FE6 Localization patch (the translation Serenes Forest hosts). The patch is applied in
memory to the user's clean ROM (scripts/ups.py) and only its text is read, by the ROM's own text ids: every number the generators use
still comes from the clean Japanese ROM. Nothing patched is written anywhere.

The patch file sits next to the ROM in Documents\\FE Games (or set FE6_PATCH). What it changes for text:
  - the text table moves to 0x833530 (the pointer at 0x013B10 says where); entries are Huffman-compressed with the ROM's tree layout
    (0x0F300C, root pointer 0x0F6358), rebuilt for English;
  - English letters are drawn from the 0x82 page of the system font (the table at 0x59027C, glyphs indexed by the second byte minus
    0x40): the hiragana codes, given Latin glyphs (A = 0x82A0, a = 0x82D0, a space 0x82B8), and a few glyphs in the full-width
    letters' slots. CHARS below is read off the glyphs; a code it doesn't know raises.
Plain (uncompressed) strings, such as the terrain names, use the same codes.

    python scripts/fe6_names.py           # prints every table
"""
import functools
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe6_rom import CHARACTERS, CLASSES, ITEMS, R, TERRAIN_NAMES, huffman  # noqa: E402
from ups import apply  # noqa: E402

PATCH = os.environ.get('FE6_PATCH', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'FE6Localization_v1.2.1.ups'))
TEXT_POINTER = 0x013B10

_UPPER = [0xA0, 0xA2, 0xA4, 0xA6, 0xA8, 0xA9, 0xAB, 0xAD, 0xAF, 0xB1, 0xB3, 0xB5, 0xB7, 0xB9, 0xBB, 0xBD, 0xBF, 0xC2, 0xC4, 0xC6,
          0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD]
_LOWER = [0xD0, 0xD3, 0xD6, 0xD9, 0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE2, 0xE4, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xED, 0xF0, 0xF1,
          0xAA, 0xAC, 0xAE, 0xB0, 0xB2, 0xB4]
_DIGITS = [0xD8, 0xDB, 0x9F, 0xA1, 0xA3, 0xA5, 0xA7, 0xC1, 0xE1, 0xE3]
_MARKS = {0xB8: ' ', 0xB6: ' ', 0xBA: '!', 0xBC: '"', 0xBE: '#', 0xC0: '$', 0xC3: '%', 0xC5: '&', 0xC7: "'", 0xCE: '(', 0xCF: '-',
          0xD1: ')', 0xD2: '.', 0xD4: '*', 0xD5: '/', 0xD7: '+', 0xDA: ',', 0xE5: ':'}
CHARS = {
    **{0x8200 | c: chr(65 + i) for i, c in enumerate(_UPPER)},
    **{0x8200 | c: chr(97 + i) for i, c in enumerate(_LOWER)},
    **{0x8200 | c: str(i) for i, c in enumerate(_DIGITS)},
    **{0x8200 | c: ch for c, ch in _MARKS.items()},
    # A second set of glyphs in the full-width letters' slots, used by a few names ("Binding Blade", "Gwendolyn").
    0x8281: 'a', 0x8284: 'd', 0x8285: 'e', 0x8287: 'g', 0x828B: 'B', 0x828D: 'G', 0x828E: 'n', 0x828F: 'o', 0x8299: 'y',
    0x8356: "'",
}


@functools.lru_cache(maxsize=None)
def patched():
    with open(PATCH, 'rb') as f:
        return apply(bytes(R), f.read())


def decode(codes):
    """Raw character codes (two-byte ones with the lead byte in the low half) -> a string; an unknown code raises."""
    out = []
    for v in codes:
        code = v if v < 0x100 else (v & 0xFF) << 8 | v >> 8
        if code < 0x20:
            continue  # control codes (line breaks, portraits)
        if code not in CHARS:
            raise KeyError(f'unknown character code {code:#06x} in {out!r}')
        out.append(CHARS[code])
    return ''.join(out).strip()


def text(i):
    """A text id as the patch has it."""
    p = patched()
    table = struct.unpack_from('<I', p, TEXT_POINTER)[0] - 0x08000000
    return decode(huffman(p, table, i))


def _u16(o):
    return struct.unpack_from('<H', R, o)[0]


def item_names():
    """{item id: English name} for every item with a name."""
    return {i: text(_u16(ITEMS + 32 * i)) for i in range(1, 128) if _u16(ITEMS + 32 * i)}


def class_names():
    return {c: text(_u16(CLASSES + 72 * c)) for c in range(1, 76) if _u16(CLASSES + 72 * c)}


def character_names():
    """By character id: the record's own id at +4 (the table starts at id 1, Roy), which is what units on a map name."""
    return {R[CHARACTERS + 48 * c + 4]: text(_u16(CHARACTERS + 48 * c)) for c in range(0, 226) if _u16(CHARACTERS + 48 * c)}


def terrain_names():
    """The terrain names, plain strings of two-byte codes in the patch."""
    p = patched()
    out = []
    for i in range(51):
        o = struct.unpack_from('<I', p, TERRAIN_NAMES + 4 * i)[0] - 0x08000000
        raw = p[o:p.index(b'\0', o)]
        out.append(decode([raw[k] | raw[k + 1] << 8 for k in range(0, len(raw), 2)]))
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('items', item_names())
    print('classes', class_names())
    print('characters', character_names())
    print('terrain', terrain_names())

"""English names for Shadow Dragon and the Blade of Light, from the Switch release's own program (`data-raw/fe1/rom/main.bin`).

The cartridge still draws its Japanese text; the Switch side recognises each string as the NES draws it and puts its English over
it. Two tables in the program do that:

- the dictionary (32-byte entries {length, pointer to the string in the NES's encoding, the Japanese text in UTF-8, text number}): a
  name's key is its first `length` codes as the NES draws them on the line, without the voicing marks (0x0F ゛, 0x1F ゜) that go on
  the line above. Item names are keyed whole ("てつのつるぎ"), class names by their first three codes ("ソシアル ナイト");
- the English text (16-byte entries {u32 text number, u64 pointer to the UTF-8 string}), 294 of them: names of people, armies,
  classes, items, terrain, places and menu words.

A name is looked up by the longest key it starts with.

    python scripts/fe1_names.py      lists the dictionary
"""
import os
import struct

MAIN = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe1', 'rom', 'main.bin')
VOICING = (0x0F, 0x1F)

_img = None
_dictionary = None
_english = None


def _main():
    global _img
    if _img is None:
        _img = open(MAIN, 'rb').read()
    return _img


def _cstr(p):
    img = _main()
    return img[p:img.index(b'\0', p)].decode('utf-8')


def english():
    """Text number -> English string (the first entry wins where a number repeats)."""
    global _english
    if _english is None:
        img = _main()
        start = img.index(struct.pack('<IIQ', 0xC8, 0, img.index(b'\0Marth\0') + 1))
        _english = {}
        for k in range(294):
            tid, p = struct.unpack_from('<IxxxxQ', img, start + 16 * k)
            _english.setdefault(tid, _cstr(p))
        assert _english[0x15E] == 'Iron Sword', _english[0x15E]
    return _english


def dictionary():
    """[(key: the NES's codes, Japanese, text number)] as the program lists them."""
    global _dictionary
    if _dictionary is None:
        img = _main()
        ro = range(0x55000, 0xCA000)

        def entry(o):
            n, enc, ja, tid = struct.unpack_from('<QQQQ', img, o)
            if 0 < n < 64 and enc in ro and ja in ro and tid < 0x10000:
                return img[enc:enc + n], _cstr(ja), tid
            return None
        # anchor: the Iron Sword's entry, found by its Japanese text
        ja = img.index('てつのつるぎ'.encode())
        o = img.rindex(struct.pack('<Q', ja)) - 16  # the data segment's pointer (the first is the relocation list's)
        while entry(o - 32):
            o -= 32
        _dictionary = []
        while entry(o):
            _dictionary.append(entry(o))
            o += 32
    return _dictionary


def key(codes):
    """A string as the dictionary keys it: without the voicing marks."""
    return bytes(b for b in codes if b not in VOICING)


def text_number(codes):
    """The text number of a string in the NES's encoding (ended by 0xEF or not): its longest key, or None."""
    if 0xEF in codes:
        codes = codes[:codes.index(0xEF)]
    k = key(codes)
    best = None
    for dk, _, tid in dictionary():
        if k.startswith(dk) and (best is None or len(dk) > len(best[0])):
            best = (dk, tid)
    return best[1] if best else None


def name(codes):
    """The English for a string in the NES's encoding, or None where the program has none."""
    tid = text_number(codes)
    return english().get(tid) if tid is not None else None


# The NES's text codes (for notes and checks only: names come from the program above). 0x0F ゛ and 0x1F ゜ mark the code before.
KANA = ('あいうえおかきくけこさしすせそ゛たちつてとなにぬねのはひふへほ゜まみむめもやゆよらりるれろわをん'
        'アイウエオカキクケコサシスセソータチツテトナニヌネノハヒフヘホ?マミムメモヤユヨラリルレロワヲン')


def kana(codes):
    return ''.join(KANA[b] if b < len(KANA) else f'[{b:02x}]' for b in codes if b != 0xEF)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for k, ja, tid in dictionary():
        print(f'{tid:#05x} {ja:12s} {english().get(tid, "")!s:20s} {k.hex(" ")}')

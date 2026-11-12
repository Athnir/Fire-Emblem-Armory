"""
New Mystery of the Emblem's English names: the Heroes of Shadow translation (`FE12_v3.01.zip` in Documents\\FE Games, the patch
Serenes Forest hosts), an xdelta file applied in memory to the user's clean cartridge (scripts/vcdiff.py). Only its text (m/*: the
same label -> string container as the game's own) is read, by the game's labels (MPID_ people, MJID_ classes, MIID_ items, MS_TER_
terrain...). Nothing patched is written.

The dump's secure area is stored decrypted, so the patch's first 8 MB window (the program) doesn't come out as the patch's makers'
did; every other window matches its Adler-32, and the text is read through the patched file table.

The patch packs long names by putting a narrow-spacing code (0x88, a Shift-JIS lead byte with no character under 0x889F) between
their letters ("B r a v e  L a n c e"); it's dropped. A few generic names are drawn as pictures (MPID_REP16): read as None.
"""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe12_extract import CART, GAMES  # noqa: E402
from fe13_bin import Bin  # noqa: E402
from nds_rom import Nds, decompress  # noqa: E402
from vcdiff import apply  # noqa: E402

PATCH = os.path.join(GAMES, 'FE12_v3.01.zip')
DELTA = 'FE12_v3_01.delta'

_text = None


def decode(raw):
    """A Shift-JIS string with the patch's spacing codes taken out."""
    out, i = bytearray(), 0
    while i < len(raw):
        b = raw[i]
        if b == 0x88 and i + 1 < len(raw) and raw[i + 1] < 0x9F:
            i += 1
            continue
        if 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC:
            out += raw[i:i + 2]
            i += 2
            continue
        out.append(b)
        i += 1
    return out.decode('shift_jis', 'replace')


def text():
    """{label: English string} from every m/ file of the patched cartridge."""
    global _text
    if _text is None:
        clean = open(CART, 'rb').read()
        patched, bad = apply(clean, zipfile.ZipFile(PATCH).read(DELTA))
        # Only the first window (the header, the program and the file table's neighbourhood) may differ: the secure area.
        assert bad in ([], [(0, 8 << 20)]), bad
        rom = Nds(patched)
        _text = {}
        for path in sorted(rom.files):
            if not path.startswith('m/'):
                continue
            t = Bin(decompress(rom.read(path)))
            for o, n in t.labels:
                o += 0x20
                _text.setdefault(n, decode(t.d[o:t.d.index(b'\0', o)]))
    return _text


def say(label):
    """A label's English, or None (missing, or a name the patch draws as a picture)."""
    s = text().get(label) if label else None
    if s is None or any(0x3040 <= ord(c) <= 0x9FFF or 0xFF00 <= ord(c) <= 0xFFEF for c in s):
        return None
    return s

"""Copy the files the Armory reads out of the user's own Echoes: Shadows of Valentia cartridge into data-raw/fe15/romfs (git-ignored,
never committed).

The cartridge image (`Fire Emblem Echoes Shadows of Valentia.3ds`, North American, decrypted) sits in Documents\FE Games. From the
game: Data/, GameData/, Scripts/, map/, the English text (m/@NOA_EN), the exploration fields' placements (field/*.bin.lz: not their
models), plus the program (.code, decompressed) for checking mechanics.

    python scripts/fe15_extract.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ncch_romfs import RomFS, ncsd_partitions  # noqa: E402
from fe13_extract import exefs_code  # noqa: E402

GAMES = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games')
CART = os.path.join(GAMES, 'Fire Emblem Echoes Shadows of Valentia.3ds')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe15', 'romfs')
KEEP = ('/Data/', '/GameData/', '/Scripts/', '/map/', '/m/@NOA_EN/', '/GlobalMap/', '/params.bin.lz')


def main():
    part = dict((i, o) for i, o, _ in ncsd_partitions(CART))[0]
    r = RomFS(CART, part)
    r.extract(OUT, KEEP)
    for p, off, size in r.walk():
        if p.startswith('/field/') and p.endswith('.bin.lz'):
            dst = os.path.join(OUT, p.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(r.read(off, size))
    code = exefs_code(CART, part)
    open(os.path.join(OUT, 'code.bin'), 'wb').write(code)
    print('code', len(code))


if __name__ == '__main__':
    main()

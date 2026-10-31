"""Copy the files the Armory reads out of the user's own Shadow Dragon cartridge into data-raw/fe11/rom (git-ignored, never
committed), decompressed.

The cartridge image (`Fire Emblem - Shadow Dragon.nds`, North American, YFEE) sits in Documents\\FE Games. From it: data/ (the
database of items, people, classes and shops), dispos/ (each chapter's placements), map/ (each chapter's grid), script/ (the
chapters' scripts: the same bytecode as Fates'), the English text (m/en_*), plus the ARM9 program and its overlays for checking
mechanics.

    python scripts/fe11_extract.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from nds_rom import Nds, decompress  # noqa: E402

GAMES = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games')
CART = os.path.join(GAMES, 'Fire Emblem - Shadow Dragon.nds')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe11', 'rom')
KEEP = ('data/', 'dispos/', 'map/', 'script/', 'm/', 'cpu/')
# LZ10-compressed; map/ grids and script/ files are stored as they are (map/*.ta, the maps' textures, aren't needed).
PACKED = ('data/', 'dispos/', 'm/', 'cpu/')


def main():
    rom = Nds(CART)
    assert rom.code == 'YFEE', rom.code
    n = 0
    for path in rom.files:
        if not path.startswith(KEEP) or path.endswith('.ta'):
            continue
        dst = os.path.join(OUT, path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        data = rom.read(path)
        open(dst, 'wb').write(decompress(data) if path.startswith(PACKED) else data)
        n += 1
    open(os.path.join(OUT, 'arm9.bin'), 'wb').write(rom.arm9())
    os.makedirs(os.path.join(OUT, 'overlay'), exist_ok=True)
    for oid, (ram, data) in rom.overlays().items():
        open(os.path.join(OUT, 'overlay', f'{oid:02d}_{ram:08x}.bin'), 'wb').write(data)
    print(n, 'files; arm9 loaded at', hex(rom.arm9_ram))


if __name__ == '__main__':
    main()

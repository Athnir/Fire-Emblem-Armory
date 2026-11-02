"""Copy what the Armory reads out of the user's own Fire Emblem: Shadow Dragon and the Blade of Light (the Switch release of the
Famicom original, 2020) into data-raw/fe1/rom (git-ignored, never committed).

The package (`Fire Emblem_ Shadow Dragon and the Blade of Light [0100A12011CC8000][v0][BASE].nsp`, dumped with nxdumptool) sits
in Documents\\FE Games\\Switch dumps\\NSP; the console's keys are in ~/.switch (see switch_nsp.py). The game has no data files: its
program `main` holds the English text (the Switch side draws every line, from templates like "<$DATA_NAME2> broke!") and, in its
data, the Famicom cartridge whole: a 'FA5J' record with the Japanese title and the emulator's settings, 256 KB of program (PRG,
16 banks of 16 KB, the last fixed at $C000), 128 KB of graphics (CHR), and 'FA5J' again.

Writes:
  main.bin  the program as it sits in memory (its three segments decompressed, at their offsets)
  fe1.nes   the cartridge with an iNES header (mapper 10, MMC4, battery-backed RAM), for reading and for running in Mesen

    python scripts/fe1_extract.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from switch_nsp import Nsp, nso_image  # noqa: E402

NSP = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Switch dumps', 'NSP',
                   'Fire Emblem_ Shadow Dragon and the Blade of Light [0100A12011CC8000][v0][BASE].nsp')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe1', 'rom')
TITLE_ID = 0x0100A12011CC8000
PRG_BANK, CHR_BANK = 0x4000, 0x2000


def cartridge(main):
    """The cartridge inside the program: (settings record, PRG, CHR). 'FA5J' (the game's code) also names the save file
    ('FA5J_FA5J.sram'); the record is the one followed by the Japanese title."""
    title = 'ファイアーエムブレム　暗黒竜と光の剣'.encode('shift_jis')
    start = main.index(b'FA5J' + main[main.index(title) - 8:main.index(title)])
    assert main[start + 0xC:start + 0xC + len(title)] == title
    settings = main[start + 0x3C:start + 0x4C]
    assert settings[3] == 0x0A, settings.hex()  # mapper 10
    prg_banks, chr_banks = settings[5], settings[6]
    rom = start + 0x4C
    prg = main[rom:rom + prg_banks * PRG_BANK]
    chr_ = main[rom + len(prg):rom + len(prg) + chr_banks * CHR_BANK]
    assert main[rom + len(prg) + len(chr_):][:4] == b'FA5J', 'cartridge not framed as expected'
    nmi, reset, irq = struct.unpack_from('<HHH', prg, len(prg) - 6)
    assert 0xC000 <= reset < 0x10000, hex(reset)
    return settings, prg, chr_


def main():
    nsp = Nsp(NSP)
    program = nsp.program()
    assert program.title_id == TITLE_ID, f'{program.title_id:016x}'
    exefs = program.pfs0(next(s for s in program.sections if s['fs_type'] == 'PFS0' and s['index'] == 0))
    image, _ = nso_image(exefs.open('main'))
    settings, prg, chr_ = cartridge(image)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'main.bin'), 'wb').write(image)
    header = b'NES\x1a' + bytes([len(prg) // PRG_BANK, len(chr_) // CHR_BANK, 0xA2, 0x00]) + bytes(8)
    open(os.path.join(OUT, 'fe1.nes'), 'wb').write(header + prg + chr_)
    print(f'main.bin {len(image):#x} bytes; fe1.nes: PRG {len(prg) // 1024} KB, CHR {len(chr_) // 1024} KB; settings {settings.hex()}')


if __name__ == '__main__':
    main()

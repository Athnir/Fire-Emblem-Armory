"""Copy the files the Armory reads out of the user's own Awakening dumps into data-raw/fe13/romfs (git-ignored, never committed).

The cartridge image (`00040000000A0500_v00.trim.3ds`, decrypted) and the DLC (`Fire_Emblem_-_Awakening_NA_DLC.cia`, decrypted) sit
in Documents\\FE Games. From the game: data/, scripts/, map/data/ and the English text (m/E), plus the program (.code, decompressed)
for checking mechanics. Each DLC content goes to dlc/<content id>/ with its own romfs.

    python scripts/fe13_extract.py
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ncch_romfs import RomFS, cia_contents, ncsd_partitions  # noqa: E402

GAMES = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games')
CART = os.path.join(GAMES, '00040000000A0500_v00.trim.3ds')
DLC = os.path.join(GAMES, 'Fire_Emblem_-_Awakening_NA_DLC.cia')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe13', 'romfs')
KEEP = ('/data/', '/scripts/', '/map/data/', '/m/E/', '/m/E.', '/params.bin.lz')


def blz_decompress(buf):
    """The 3DS program's reverse LZ ('BLZ'): the footer says how much is compressed and how much it grows."""
    enc_info, add = struct.unpack_from('<II', buf, len(buf) - 8)
    enc_len = enc_info & 0xFFFFFF
    header_len = enc_info >> 24
    out = bytearray(buf) + bytearray(add)
    src = len(buf) - header_len
    dst = len(out)
    stop = len(buf) - enc_len
    while src > stop:
        src -= 1
        flags = buf[src]
        for _ in range(8):
            if src <= stop:
                break
            if flags & 0x80:
                src -= 2
                pair = buf[src] | buf[src + 1] << 8
                n = (pair >> 12) + 3
                disp = (pair & 0xFFF) + 3
                for _ in range(n):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = buf[src]
            flags = (flags << 1) & 0xFF
    return bytes(out)


def exefs_code(path, base):
    with open(path, 'rb') as f:
        f.seek(base)
        h = f.read(0x200)
        exh = f.read(0x400)
        exefs = base + struct.unpack_from('<I', h, 0x1A0)[0] * 0x200
        f.seek(exefs)
        eh = f.read(0x200)
        for i in range(10):
            name, off, size = struct.unpack_from('<8sII', eh, i * 16)
            if name.rstrip(b'\0') == b'.code':
                f.seek(exefs + 0x200 + off)
                code = f.read(size)
                return blz_decompress(code) if exh[0xD] & 1 else code
    raise ValueError('no .code')


def unpack_arc(path, out):
    """A DLC archive (`E0xx_MAP.arc`): the binary format, its labels the file names, each pointing at [name, index, size, offset].
    Only the data files the Armory reads are written, under the path the archive gives them."""
    from fe13_bin import Bin
    b = Bin(open(path, 'rb').read())
    for off, name in b.labels:
        if not name.startswith(('data/', 'map/data/', 'm/E/', 'scripts/')):
            continue
        size, start = b.u32(off + 8), b.u32(off + 12)
        dst = os.path.join(out, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(b.d[0x20 + start:0x20 + start + size])


def main():
    part = dict((i, o) for i, o, _ in ncsd_partitions(CART))[0]
    RomFS(CART, part).extract(OUT, KEEP)
    code = exefs_code(CART, part)
    open(os.path.join(OUT, 'code.bin'), 'wb').write(code)
    print('code', len(code))
    for cid, idx, off, _ in cia_contents(DLC):
        r = RomFS(DLC, off)
        files = list(r.walk())
        dst = os.path.join(OUT, 'dlc', '%04x' % cid)
        r.extract(dst)
        for p, _, _ in files:
            if p.endswith('_MAP.arc'):
                unpack_arc(os.path.join(dst, p.lstrip('/')), os.path.join(OUT, 'dlc', p.strip('/')[:4]))
        print('dlc %04x' % cid, len(files), [p for p, _, _ in files][:6])


if __name__ == '__main__':
    main()

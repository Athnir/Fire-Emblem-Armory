"""List / extract the RomFS of a decrypted 3DS NCCH (.app / .cxi) without other tools.

Also opens the NCCHs inside a decrypted cartridge image (`.3ds`, an NCSD: partition 0 is the game) and inside a decrypted `.cia`
(one NCCH per content): `ncsd_partitions(path)` and `cia_contents(path)` give each one's offset, for `RomFS(path, base)`.
"""
import struct
import sys
import os


class RomFS:
    def __init__(self, path, base=0):
        self.f = open(path, 'rb')
        self.base = base
        h = self.read(0, 0x200)
        assert h[0x100:0x104] == b'NCCH', 'not an NCCH'
        assert h[0x18F] & 0x4, 'still encrypted (NoCrypto flag not set)'
        romfs = struct.unpack_from('<I', h, 0x1B0)[0] * 0x200
        ivfc = self.read(romfs, 0x60)
        assert ivfc[:4] == b'IVFC'
        master = struct.unpack_from('<I', ivfc, 8)[0]
        l3_log2 = struct.unpack_from('<I', ivfc, 0x4C)[0]
        bs = 1 << l3_log2
        self.l3 = romfs + ((0x60 + master + bs - 1) // bs) * bs
        hdr = struct.unpack_from('<10I', self.read(self.l3, 0x28))
        self.dir_meta = self.read(self.l3 + hdr[3], hdr[4])
        self.file_meta = self.read(self.l3 + hdr[7], hdr[8])
        self.data = self.l3 + hdr[9]

    def read(self, off, n):
        self.f.seek(self.base + off)
        return self.f.read(n)

    def _name(self, meta, off, base):
        n = struct.unpack_from('<I', meta, off + base)[0]
        return meta[off + base + 4:off + base + 4 + n].decode('utf-16-le')

    def walk(self, d=0, path=''):
        parent, sib, child, file = struct.unpack_from('<4I', self.dir_meta, d)
        f = file
        while f != 0xFFFFFFFF:
            _, fsib, doff, dsize = struct.unpack_from('<IIQQ', self.file_meta, f)
            yield path + '/' + self._name(self.file_meta, f, 0x1C), self.data + doff, dsize
            f = fsib
        c = child
        while c != 0xFFFFFFFF:
            yield from self.walk(c, path + '/' + self._name(self.dir_meta, c, 0x14))
            c = struct.unpack_from('<I', self.dir_meta, c + 4)[0]

    def extract(self, out, only=None):
        for p, off, size in self.walk():
            if only and not any(p.startswith(o) for o in only):
                continue
            dst = os.path.join(out, p.lstrip('/'))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(self.read(off, size))


def ncsd_partitions(path):
    """The NCCH partitions of a cartridge image: (index, offset, size) in bytes."""
    with open(path, 'rb') as f:
        h = f.read(0x200)
    assert h[0x100:0x104] == b'NCSD', 'not a cartridge image'
    parts = [struct.unpack_from('<II', h, 0x120 + 8 * i) for i in range(8)]
    return [(i, o * 0x200, n * 0x200) for i, (o, n) in enumerate(parts) if n]


def cia_contents(path):
    """The contents of a CIA: (content id, index, offset, size). Each is an NCCH when the CIA is decrypted."""
    al = lambda x: (x + 63) // 64 * 64
    with open(path, 'rb') as f:
        hs, _, _, cert, tik, tmd, _, _ = struct.unpack('<IHHIIIIQ', f.read(0x20))
        o_tmd = al(hs) + al(cert) + al(tik)
        f.seek(o_tmd)
        t = f.read(tmd)
    assert struct.unpack('>I', t[:4])[0] == 0x10004, 'unexpected TMD signature type'
    body = t[0x140:]
    n = struct.unpack_from('>H', body, 0x9E)[0]
    recs = body[0xC4 + 64 * 36:]
    off = o_tmd + al(tmd)
    out = []
    for i in range(n):
        cid, idx, _, size = struct.unpack_from('>IHHQ', recs, i * 48)
        out.append((cid, idx, off, size))
        off += size
    return out


if __name__ == '__main__':
    for p, off, size in RomFS(sys.argv[1]).walk():
        print(p, size)

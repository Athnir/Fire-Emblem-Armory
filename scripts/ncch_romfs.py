"""List / extract the RomFS of a decrypted 3DS NCCH (.app / .cxi) without other tools."""
import struct
import sys
import os


class RomFS:
    def __init__(self, path):
        self.f = open(path, 'rb')
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
        self.f.seek(off)
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


if __name__ == '__main__':
    for p, off, size in RomFS(sys.argv[1]).walk():
        print(p, size)

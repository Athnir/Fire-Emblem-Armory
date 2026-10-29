"""Read Awakening's binary data files (the 3DS Fire Emblem format: a 0x20 header, the data, a pointer list, then labels)."""
import os
import struct

from fates_lz import decompress

ROMFS = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe13', 'romfs')


class Bin:
    def __init__(self, data):
        self.d = data
        _, self.size, pc, lc = struct.unpack_from('<4I', data, 0)
        ptab = 0x20 + self.size
        ltab = ptab + pc * 4
        names = ltab + lc * 8
        self.ptrs = set(struct.unpack_from('<%dI' % pc, data, ptab))
        self.labels = []
        for i in range(lc):
            off, no = struct.unpack_from('<II', data, ltab + i * 8)
            self.labels.append((off, self.cstr(names + no)))
        self.at = {}
        for off, name in self.labels:
            self.at.setdefault(name, off)

    def cstr(self, o):
        return self.d[o:self.d.index(b'\0', o)].decode('shift_jis', 'replace')

    def u8(self, o): return self.d[0x20 + o]
    def s8(self, o): return struct.unpack_from('<b', self.d, 0x20 + o)[0]
    def u16(self, o): return struct.unpack_from('<H', self.d, 0x20 + o)[0]
    def s16(self, o): return struct.unpack_from('<h', self.d, 0x20 + o)[0]
    def u32(self, o): return struct.unpack_from('<I', self.d, 0x20 + o)[0]

    def str(self, o):
        """The string a pointer field at o points to (None if the field isn't a pointer)."""
        if o not in self.ptrs:
            return None
        return self.cstr(0x20 + self.u32(o))


def load(path):
    raw = open(os.path.join(ROMFS, path), 'rb').read()
    return Bin(decompress(raw) if path.endswith('.lz') else raw)

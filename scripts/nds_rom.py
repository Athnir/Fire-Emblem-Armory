"""Read a Nintendo DS cartridge image (.nds): its file system (NitroFS: the FNT names, the FAT offsets), the ARM9 program and its
overlays, and the LZ10 / LZ11 compression its files use. Used for Shadow Dragon (FE11)."""
import struct

from fates_lz import lz11


class Nds:
    def __init__(self, path):
        self.d = open(path, 'rb').read()
        d = self.d
        self.title, self.code = d[:12].rstrip(b'\0').decode('ascii'), d[12:16].decode('ascii')
        self.fnt, _, self.fat, _ = struct.unpack_from('<4I', d, 0x40)
        self.arm9_off, self.arm9_entry, self.arm9_ram, self.arm9_size = struct.unpack_from('<4I', d, 0x20)
        self.ovt_off, self.ovt_size = struct.unpack_from('<2I', d, 0x50)
        self.files = {}
        self._walk(0xF000, '')

    def _walk(self, did, path):
        d = self.d
        sub, first, _ = struct.unpack_from('<IHH', d, self.fnt + (did & 0xFFF) * 8)
        p, fid = self.fnt + sub, first
        while True:
            t = d[p]
            p += 1
            if t == 0:
                return
            name = d[p:p + (t & 0x7F)].decode('latin1')
            p += t & 0x7F
            if t & 0x80:
                child = struct.unpack_from('<H', d, p)[0]
                p += 2
                self._walk(child, path + name + '/')
            else:
                self.files[path + name] = fid
                fid += 1

    def file_by_id(self, fid):
        s, e = struct.unpack_from('<2I', self.d, self.fat + fid * 8)
        return self.d[s:e]

    def read(self, path):
        return self.file_by_id(self.files[path])

    def arm9(self):
        """The ARM9 program as loaded at arm9_ram (decompressed when its module parameters say it's compressed)."""
        return blz(self.d[self.arm9_off:self.arm9_off + self.arm9_size])

    def overlays(self):
        """{overlay id: (load address, program)} from the ARM9 overlay table (each decompressed when flagged)."""
        out = {}
        for o in range(self.ovt_off, self.ovt_off + self.ovt_size, 32):
            oid, ram, size, _bss, _s, _e, fid, flags = struct.unpack_from('<8I', self.d, o)
            data = self.file_by_id(fid)
            if flags >> 24 & 1:
                data = blz(data)
            out[oid] = (ram, data)
        return out


def lz10(data):
    """LZ10 (type 0x10): the DS's plain LZ77."""
    assert data[0] == 0x10, f'not LZ10 (type {data[0]:#x})'
    size = int.from_bytes(data[1:4], 'little')
    pos, out = 4, bytearray()
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if flags >> bit & 1:
                b0, b1 = data[pos], data[pos + 1]
                pos += 2
                n, disp = (b0 >> 4) + 3, ((b0 & 0xF) << 8 | b1) + 1
                for _ in range(n):
                    out.append(out[-disp])
            else:
                out.append(data[pos])
                pos += 1
    return bytes(out[:size])


def decompress(data):
    """A file's contents, decompressed if it starts with an LZ10 or LZ11 header."""
    if data[:1] == b'\x10':
        return lz10(data)
    if data[:1] == b'\x11':
        return lz11(data)
    return data


def blz(data):
    """Backward LZ (the ARM9 program and overlays): the footer gives the compressed span and how much it grows. Data that doesn't
    end in a valid footer is returned as is."""
    if len(data) < 8:
        return data
    end_info, extra = struct.unpack_from('<II', data, len(data) - 8)
    enc_len, hdr_len = end_info & 0xFFFFFF, end_info >> 24
    if hdr_len < 8 or enc_len > len(data) or extra == 0:
        return data
    keep = len(data) - enc_len
    src = bytearray(data)
    out = bytearray(len(data) + extra)
    out[:len(data)] = src
    i, o = len(data) - hdr_len, len(out)
    start = keep
    while i > start:
        i -= 1
        flags = src[i]
        for _ in range(8):
            if i <= start:
                break
            if flags & 0x80:
                i -= 2
                v = src[i] | src[i + 1] << 8
                n, disp = (v >> 12) + 3, (v & 0xFFF) + 3
                for _ in range(n):
                    o -= 1
                    out[o] = out[o + disp]
            else:
                i -= 1
                o -= 1
                out[o] = src[i]
            flags = flags << 1 & 0xFF
    return bytes(out)

"""Open the user's own Switch dumps (NSP packages from nxdumptool) without other tools: the package (PFS0), the NCAs inside it
(decrypted with the console's own keys), their file systems (PFS0 / RomFS) and the program's executables (NSO, LZ4-compressed).

The keys come from Lockpick_RCM, run on the user's console: `prod.keys` and `title.keys` in `~/.switch` (never in the repo). A
digital game's NCAs are encrypted with its title key (`title.keys` holds it as the ticket gives it, under the title key
encryption key); a cartridge game's with keys in the NCA's own key area.

    python scripts/switch_nsp.py <file.nsp>          lists each NCA: content type, title, sections
"""
import os
import struct
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEYS = os.path.join(os.path.expanduser('~'), '.switch')
CONTENT_TYPES = {0: 'Program', 1: 'Meta', 2: 'Control', 3: 'Manual', 4: 'Data', 5: 'PublicData'}
MEDIA = 0x200


def load_keys(name):
    keys = {}
    for line in open(os.path.join(KEYS, name), encoding='ascii'):
        if '=' in line:
            k, v = (s.strip() for s in line.split('=', 1))
            keys[k.lower()] = bytes.fromhex(v)
    return keys


def ecb_decrypt(key, data):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(data) + d.finalize()


def ctr_decrypt(key, counter, data):
    d = Cipher(algorithms.AES(key), modes.CTR(counter)).decryptor()
    return d.update(data) + d.finalize()


def xts_decrypt(key, data, sector, sector_size=0x200):
    """Nintendo's AES-XTS: the tweak is the sector number, big-endian."""
    out = bytearray()
    for i in range(0, len(data), sector_size):
        d = Cipher(algorithms.AES(key), modes.XTS((sector + i // sector_size).to_bytes(16, 'big'))).decryptor()
        out += d.update(data[i:i + sector_size]) + d.finalize()
    return bytes(out)


class Pfs0:
    """A partition file system: the NSP package itself, and an NCA's ExeFS / logo sections."""

    def __init__(self, read, size=None):
        self.read = read
        magic, count, strings = struct.unpack('<4sII', read(0, 12))
        assert magic == b'PFS0', magic
        table = read(16, count * 24 + strings)
        names = table[count * 24:]
        data = 16 + count * 24 + strings
        self.files = {}
        for i in range(count):
            off, n, name = struct.unpack_from('<QQI', table, i * 24)
            self.files[names[name:names.index(b'\0', name)].decode()] = (data + off, n)

    def open(self, name):
        off, n = self.files[name]
        return self.read(off, n)


class Nca:
    def __init__(self, read, prod, titles):
        self.read = read
        self.header = xts_decrypt(prod['header_key'], read(0, 0xC00), 0)
        h = self.header
        assert h[0x200:0x204] == b'NCA3', h[0x200:0x204]
        self.content_type = CONTENT_TYPES.get(h[0x205], h[0x205])
        self.title_id = struct.unpack_from('<Q', h, 0x210)[0]
        generation = max(h[0x206], h[0x220])
        revision = max(generation - 1, 0)
        rights = h[0x230:0x240]
        if any(rights):
            enc = titles[rights.hex()]
            self.key = ecb_decrypt(prod[f'titlekek_{revision:02x}'], enc)
        else:
            kak = prod[('key_area_key_application', 'key_area_key_ocean', 'key_area_key_system')[h[0x207]] + f'_{revision:02x}']
            self.key = ecb_decrypt(kak, h[0x300:0x340])[0x20:0x30]
        self.sections = []
        for i in range(4):
            start, end = struct.unpack_from('<II', h, 0x240 + i * 16)
            if not end:
                continue
            fs = h[0x400 + i * 0x200:0x600 + i * 0x200]
            self.sections.append({
                'index': i, 'offset': start * MEDIA, 'size': (end - start) * MEDIA,
                'fs_type': ('RomFS', 'PFS0')[fs[2]], 'crypt': fs[4], 'fs': fs,
            })

    def section_reader(self, s):
        """Read the section's plain bytes: AES-CTR with the counter's upper half from the section header."""
        assert s['crypt'] in (1, 3), f"section crypt type {s['crypt']} not supported"
        upper = s['fs'][0x140:0x148][::-1]

        def read(off, n):
            if s['crypt'] == 1:
                return self.read(s['offset'] + off, n)
            a = (s['offset'] + off) & ~0xF
            b = s['offset'] + off + n
            raw = self.read(a, b - a)
            return ctr_decrypt(self.key, upper + (a >> 4).to_bytes(8, 'big'), raw)[(s['offset'] + off) - a:]
        return read

    def pfs0(self, s):
        """The PFS0 inside a section: past its hash table (offsets in the section header's hash data)."""
        read = self.section_reader(s)
        off = struct.unpack_from('<Q', s['fs'], 0x8 + 0x38)[0]
        return Pfs0(lambda o, n: read(off + o, n))

    def romfs(self, s):
        """The RomFS inside a section: its level 6 (the files) is the last of the IVFC levels."""
        read = self.section_reader(s)
        ivfc = s['fs'][0x8:0x8 + 0xF8]
        assert ivfc[:4] == b'IVFC', ivfc[:4]
        levels = struct.unpack_from('<I', ivfc, 0xC)[0]
        off = struct.unpack_from('<Q', ivfc, 0x10 + (levels - 2) * 0x18)[0]
        return RomFs(lambda o, n: read(off + o, n))


class RomFs:
    def __init__(self, read):
        self.read = read
        h = struct.unpack('<10Q', read(0, 0x50))
        self.dirs = read(h[3], h[4])
        self.file_meta = read(h[7], h[8])
        self.data = h[9]

    def walk(self, d=0, path=''):
        parent, sib, child, file, nxt, n = struct.unpack_from('<6I', self.dirs, d)
        f = file
        while f != 0xFFFFFFFF:
            parent, sib, off, size, nxt, n = struct.unpack_from('<IIQQII', self.file_meta, f)
            yield path + '/' + self.file_meta[f + 0x20:f + 0x20 + n].decode(), off, size
            f = sib
        c = child
        while c != 0xFFFFFFFF:
            parent, sib, ch, file, nxt, n = struct.unpack_from('<6I', self.dirs, c)
            yield from self.walk(c, path + '/' + self.dirs[c + 0x18:c + 0x18 + n].decode())
            c = sib

    def open(self, off, size):
        return self.read(self.data + off, size)


class Nsp:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.pfs = Pfs0(self._read)
        self.prod = load_keys('prod.keys')
        self.titles = {k: v for k, v in load_keys('title.keys').items()}

    def _read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)

    def ncas(self):
        for name, (off, n) in self.pfs.files.items():
            if name.endswith('.nca'):
                yield name, Nca(lambda o, k, base=off: self._read(base + o, k), self.prod, self.titles)

    def program(self):
        return next(nca for _, nca in self.ncas() if nca.content_type == 'Program')


def lz4_block(src, size):
    """Decompress one LZ4 block (NSO segments)."""
    out = bytearray()
    i = 0
    while i < len(src):
        token = src[i]
        i += 1
        n = token >> 4
        if n == 15:
            while True:
                b = src[i]
                i += 1
                n += b
                if b != 255:
                    break
        out += src[i:i + n]
        i += n
        if i >= len(src):
            break
        back = src[i] | src[i + 1] << 8
        i += 2
        m = token & 15
        if m == 15:
            while True:
                b = src[i]
                i += 1
                m += b
                if b != 255:
                    break
        m += 4
        start = len(out) - back
        if back >= m:
            out += out[start:start + m]
        else:
            for k in range(m):
                out.append(out[start + k])
    assert len(out) == size, (len(out), size)
    return bytes(out)


def nso_image(data):
    """An NSO as it sits in memory: text, rodata and data at their memory offsets, decompressed."""
    assert data[:4] == b'NSO0', data[:4]
    flags = struct.unpack_from('<I', data, 0xC)[0]
    segs = [struct.unpack_from('<III', data, o) for o in (0x10, 0x20, 0x30)]
    packed = struct.unpack_from('<III', data, 0x60)
    end = max(mem + size for _, mem, size in segs)
    image = bytearray(end)
    for k, ((foff, mem, size), psize) in enumerate(zip(segs, packed)):
        raw = data[foff:foff + psize]
        image[mem:mem + size] = lz4_block(raw, size) if flags & (1 << k) else raw[:size]
    return bytes(image), segs


def main(path):
    nsp = Nsp(path)
    for name, nca in nsp.ncas():
        print(name, nca.content_type, f'{nca.title_id:016x}')
        for s in nca.sections:
            print(f"  section {s['index']}: {s['fs_type']} crypt {s['crypt']} at {s['offset']:#x}, {s['size']:#x} bytes")


if __name__ == '__main__':
    main(sys.argv[1])

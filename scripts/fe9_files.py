"""
Where the user's own FE9 (Path of Radiance) files are, and readers shared by the FE9 generators.

The disc was extracted with Dolphin (Properties > Filesystem > Extract Entire Disc); the files stay on
the user's PC and out of git, like the Fates dump. GameCube files are big-endian.
"""
import os
import struct

FE9 = os.environ.get('FE9_FILES', r'C:\Users\golds\Documents\Extracted Games Dolphin\FE 9\files')


def read_text(name='common.m'):
    """A Mess/*.m text file -> {label: English text}."""
    return read_text_file(os.path.join(FE9, 'Mess', name))


def read_text_file(path):
    """A Tellius .m text file -> {label: text}. Header: size, data size, 0, entry count; then the text
    data at 0x20, a table of (text offset, label offset) pairs, and the labels. (Radiant Dawn's too.)"""
    d = open(path, 'rb').read()
    _, data_size, _, count = struct.unpack_from('>4I', d, 0)
    table = 0x20 + data_size
    labels = table + count * 8

    def c_str(o):
        return d[o:d.index(b'\0', o)].decode('shift_jis', 'replace')

    out = {}
    for k in range(count):
        text, label = struct.unpack_from('>2I', d, table + k * 8)
        out[c_str(labels + label)] = c_str(0x20 + text)
    return out


class GameData:
    """FE8Data.bin: data at 0x20, pointers are offsets from there (big-endian)."""

    B = 0x20

    def __init__(self):
        self.d = open(os.path.join(FE9, 'FE8Data.bin'), 'rb').read()

    def u32(self, o):
        return struct.unpack_from('>I', self.d, o)[0]

    def string(self, ptr):
        o = self.B + ptr
        if not 0 < ptr < len(self.d) - self.B:
            return None
        try:
            return self.d[o:self.d.index(b'\0', o)].decode('shift_jis')
        except (ValueError, UnicodeDecodeError):
            return None

    def records(self, id_prefix, name_prefix):
        """Offsets of records starting with an ID string pointer then a name label pointer."""
        return [o for o in range(self.B, len(self.d) - 8, 4)
                if (self.string(self.u32(o)) or '').startswith(id_prefix)
                and (self.string(self.u32(o + 4)) or '').startswith(name_prefix)]


def read_shop(difficulty):
    """shop/shopitem_{n,h,m}.bin -> {table name: [IID string or number, ...]}. The file is a block of
    words at 0x20 (header: size, data size, pointer count, name count), then the offsets of the words
    that are pointers, then (data offset, name offset) pairs naming each table, then the names.
    Tables: WSHOP_ITEMS_Cnn (weapon shop), ISHOP_ITEMS_Cnn (item shop), FSHOP_ITEMS_Cnn (the forge's
    base weapons, in (IID or 0, material) pairs), for the base before chapter file nn."""
    return read_shop_file(os.path.join(FE9, 'shop', f'shopitem_{difficulty}.bin'))


def read_shop_file(path):
    """A shopitem_*.bin -> {table name: [IID string or number, ...]} (Radiant Dawn's too)."""
    d = open(path, 'rb').read()
    _, data_size, n_ptrs, n_names = struct.unpack_from('>4I', d, 0)
    ptrs_at = 0x20 + data_size
    names_at = ptrs_at + n_ptrs * 4
    strings_at = names_at + n_names * 8
    ptrs = set(struct.unpack_from(f'>{n_ptrs}I', d, ptrs_at))

    def c_str(o):
        return d[o:d.index(b'\0', o)].decode('ascii')

    tables = sorted((struct.unpack_from('>I', d, names_at + k * 8)[0],
                     c_str(strings_at + struct.unpack_from('>I', d, names_at + k * 8 + 4)[0])) for k in range(n_names))
    out = {}
    for i, (start, name) in enumerate(tables):
        end = tables[i + 1][0] if i + 1 < len(tables) else data_size
        words = [struct.unpack_from('>I', d, 0x20 + o)[0] for o in range(start, end, 4)]
        out[name] = [c_str(0x20 + w) if o in ptrs else w for o, w in zip(range(start, end, 4), words)]
    return out


def lz10(data):
    """Nintendo LZ10 (header byte 0x10, then the 24-bit little-endian decompressed size)."""
    assert data[0] == 0x10, 'not LZ10'
    size = data[1] | data[2] << 8 | data[3] << 16
    out = bytearray()
    i = 4
    while len(out) < size:
        flags = data[i]
        i += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                length = (data[i] >> 4) + 3
                back = ((data[i] & 0xF) << 8 | data[i + 1]) + 1
                i += 2
                for _ in range(length):
                    out.append(out[-back])
            else:
                out.append(data[i])
                i += 1
    return bytes(out)


def unpack(data):
    """A 'pack' archive (inside the .cmp files): {name: bytes}. Header 'pack', u16 count; then 16-byte
    entries (0, name offset, data offset, size)."""
    assert data[:4] == b'pack'
    count = struct.unpack_from('>H', data, 4)[0]
    out = {}
    for k in range(count):
        _, name, start, size = struct.unpack_from('>4I', data, 8 + k * 16)
        out[data[name:data.index(b'\0', name)].decode('shift_jis')] = data[start:start + size]
    return out


def map_files(folder, name):
    """zmap/<folder>/<name>.cmp, decompressed and unpacked."""
    return unpack(lz10(open(os.path.join(FE9, 'zmap', folder, name + '.cmp'), 'rb').read()))

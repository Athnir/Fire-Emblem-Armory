"""
Where the user's own FE9 (Path of Radiance) files are, and readers shared by the FE9 generators.

The disc was extracted with Dolphin (Properties > Filesystem > Extract Entire Disc); the files stay on
the user's PC and out of git, like the Fates dump. GameCube files are big-endian.
"""
import os
import struct

FE9 = os.environ.get('FE9_FILES', r'C:\Users\golds\Documents\Extracted Games Dolphin\FE 9\files')


def read_text(name='common.m'):
    """A Mess/*.m text file -> {label: English text}. Header: size, data size, 0, entry count; then the
    text data at 0x20, a table of (text offset, label offset) pairs, and the labels."""
    d = open(os.path.join(FE9, 'Mess', name), 'rb').read()
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

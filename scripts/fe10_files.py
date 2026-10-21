"""
Where the user's own FE10 (Radiant Dawn) files are, and readers for the FE10 generators.

The disc (NA, RFEE01) was extracted with Dolphin; the files stay on the user's PC and out of git. The
game's data is in the DATA partition. Wii files are big-endian, and most formats are Path of
Radiance's (fe9_files has the shared readers).
"""
import os
import struct

from fe9_files import lz10, read_shop_file, read_text_file

FE10 = os.environ.get('FE10_FILES', r'C:\Users\golds\Documents\Extracted Games Dolphin\FE 10\DATA\files')


def read_text(name='e_common.m'):
    """Mess/e_*.m is the English text (the unprefixed files are Japanese)."""
    return read_text_file(os.path.join(FE10, 'Mess', name))


def read_shop(difficulty):
    """Shop/shopitem_{n,h,m}.bin (Easy/Normal, Hard, the Japanese release's Maniac). Tables are
    WSHOP_ITEMS_Cppnn (armory), ISHOP_ITEMS_Cppnn (item shop), FSHOP_ITEMS_Cppnn (forge) and
    SHOP_PERSON_Cppnn, for the base before chapter file ppnn (MCTppnn)."""
    return read_shop_file(os.path.join(FE10, 'Shop', f'shopitem_{difficulty}.bin'))


class GameData:
    """FE10Data.cms, LZ10-compressed: once unpacked, data at 0x20 and pointers as offsets from there,
    like Path of Radiance's FE8Data.bin."""

    B = 0x20

    def __init__(self):
        self.d = lz10(open(os.path.join(FE10, 'FE10Data.cms'), 'rb').read())

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

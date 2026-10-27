"""
Reader for the user's own The Blazing Blade (FE7) and The Sacred Stones (FE8) cartridge images, the English (U) ROMs, shared by the FE7
and FE8 generators. Both games keep their data the way The Binding Blade does (scripts/fe6_rom.py), with wider records: the same
Huffman text, item and unit layouts, chapter records and LZ77 maps. Each image stays outside the repo (default paths below, or set
FE7_ROM / FE8_ROM); only data built from it is committed. Offsets are file offsets; the game addresses them as 0x08000000 + offset.
Formats are in data-raw/fe7/README.md and data-raw/fe8/README.md.

    rom = Rom('fe7')
    rom.text(rom.item(1)['name_id'])    # 'Iron sword'
"""
import functools
import os
import struct
import zlib

FOLDER = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games')

GAMES = {
    'fe7': {
        'file': 'Fire Emblem (U) [!].gba', 'env': 'FE7_ROM', 'crc': 0x2A524221,
        # The text table; the word before it points to the Huffman tree's root node (the tree's nodes end there).
        'text': 0xB808AC,
        'characters': 0xBDCE18, 'classes': 0xBE015C, 'items': 0xBE222C,
        'chapters': 0xC9A200, 'chapter_size': 0x98, 'pointers': 0xC9C9C8,
        # Terrain: names (a u16 text id per terrain id), then the rows the classes point at.
        'terrain_names': 0xBE50E8, 'terrains': 65, 'heal': 0xBE47C4,
        'affinities': 0xC9A1C0,
    },
    'fe8': {
        'file': 'Fire Emblem - The Sacred Stones (U).gba', 'env': 'FE8_ROM', 'crc': 0xA47246AE,
        'text': 0x15D48C,
        'characters': 0x803D30, 'classes': 0x807110, 'items': 0x809B10,
        'chapters': 0x8B0890, 'chapter_size': 0x94, 'pointers': 0x8B363C,
        'terrain_names': 0x80D374, 'terrains': 65, 'heal': 0x80C744,
        'affinities': 0x8B05F8,
    },
}

ITEM_SIZE, CHARACTER_SIZE, CLASS_SIZE = 36, 52, 84
ITEM_TYPES = {0: 'Sword', 1: 'Lance', 2: 'Axe', 3: 'Bow', 4: 'Staff', 5: 'Anima', 6: 'Light', 7: 'Dark', 9: 'Item', 0xB: 'Stone',
              0xC: 'Ring'}


class Rom:
    def __init__(self, game):
        cfg = GAMES[game]
        self.game, self.cfg = game, cfg
        path = os.environ.get(cfg['env'], os.path.join(FOLDER, cfg['file']))
        with open(path, 'rb') as f:
            self.R = f.read()
        assert zlib.crc32(self.R) == cfg['crc'], f'{path} is not the clean {game.upper()} (U) ROM'
        self.root = self.u32(cfg['text'] - 4) - 0x08000000
        # The tree's nodes sit just before the root, which is the last of them.
        self.tree = self.root - 4 * (self.u16(self.root + 2) + 1)

    # Plain reads.
    def u8(self, o):
        return self.R[o]

    def s8(self, o):
        return struct.unpack_from('<b', self.R, o)[0]

    def u16(self, o):
        return struct.unpack_from('<H', self.R, o)[0]

    def u32(self, o):
        return struct.unpack_from('<I', self.R, o)[0]

    @staticmethod
    def off(v):
        """A ROM pointer (0x08xxxxxx) as a file offset."""
        return v - 0x08000000

    @staticmethod
    def is_ptr(v):
        return 0x08000000 <= v < 0x09000000

    # Text.
    @functools.lru_cache(maxsize=None)
    def raw_text(self, i):
        """Text id `i` as bytes: Huffman-coded with the ROM's tree, or stored plain when bit 31 of its pointer is set."""
        R = self.R
        p = self.u32(self.cfg['text'] + 4 * i)
        if p & 0x80000000:
            o = p & 0x1FFFFFF
            return bytes(R[o:R.index(b'\0', o)])
        p -= 0x08000000
        out, node, bit = bytearray(), self.root, 0
        while True:
            while self.u16(node + 2) != 0xFFFF:
                b = (R[p] >> bit) & 1
                bit += 1
                if bit == 8:
                    bit, p = 0, p + 1
                node = self.tree + (self.u16(node + 2) if b else self.u16(node)) * 4
            v = self.u16(node)
            if v == 0:
                return bytes(out)
            out += bytes([v & 0xFF]) if v < 0x100 else bytes([v & 0xFF, v >> 8])
            node = self.root

    def text(self, i, lines=' '):
        """A text id as a plain string: line breaks (0x01) become `lines`, other control codes are dropped."""
        out = []
        for c in self.raw_text(i):
            if c == 1:
                out.append(lines)
            elif c >= 0x20:
                out.append(chr(c))
        return ' '.join(''.join(out).split(' ')).strip() if lines == ' ' else ''.join(out).strip()

    # Records.
    def item(self, i):
        e = self.cfg['items'] + ITEM_SIZE * i
        R = self.R
        return {
            'id': i, 'name_id': self.u16(e), 'desc_id': self.u16(e + 2), 'use_id': self.u16(e + 4), 'type': R[e + 7],
            'attributes': self.u32(e + 8), 'stat_bonus': self.u32(e + 0xC), 'effective': self.u32(e + 0x10), 'uses': R[e + 0x14],
            'mt': R[e + 0x15], 'hit': R[e + 0x16], 'wt': R[e + 0x17], 'crit': R[e + 0x18], 'range': (R[e + 0x19] >> 4, R[e + 0x19] & 0xF),
            'cost': self.u16(e + 0x1A), 'rank': R[e + 0x1C], 'use_effect': R[e + 0x1E], 'weapon_effect': R[e + 0x1F],
            'exp': R[e + 0x20],
        }

    def item_count(self):
        """Items run up to the first record whose id byte (+6) isn't its index."""
        return self._count(self.cfg['items'], ITEM_SIZE, 6)

    def _count(self, table, size, id_at):
        n = 1
        while self.R[table + size * n + id_at] == n:
            n += 1
        return n

    def class_(self, c):
        e = self.cfg['classes'] + CLASS_SIZE * c
        return {'id': c, 'name_id': self.u16(e), 'promotes_to': self.R[e + 5], 'abilities': self.u32(e + 0x28),
                'move_cost': self.off(self.u32(e + 0x38)), 'move_rain': self.off(self.u32(e + 0x3C)),
                'move_snow': self.off(self.u32(e + 0x40)), 'terrain_avoid': self.off(self.u32(e + 0x44)),
                'terrain_def': self.off(self.u32(e + 0x48)), 'terrain_res': self.off(self.u32(e + 0x4C))}

    def class_count(self):
        return self._count(self.cfg['classes'], CLASS_SIZE, 4)

    def character_count(self):
        return self._count(self.cfg['characters'], CHARACTER_SIZE, 4)

    def character_record(self, c):
        """The record of character id c: the table is indexed by id, id 0 unused."""
        return self.cfg['characters'] + CHARACTER_SIZE * c

    def character(self, c):
        e = self.character_record(c)
        return {'id': self.R[e + 4], 'name_id': self.u16(e), 'class': self.R[e + 5], 'portrait': self.u16(e + 6),
                'affinity': self.R[e + 9], 'level': self.R[e + 0xB], 'abilities': self.u32(e + 0x28), 'supports': self.u32(e + 0x2C)}

    def class_list(self, p):
        """A list of class ids ending in 0 (an item's effectiveness list), from a ROM pointer."""
        o, out = self.off(p), []
        while self.R[o]:
            out.append(self.R[o])
            o += 1
        return out

    # Names.
    def names(self, table, size, count, name_at=0):
        out = {}
        for k in range(1, count):
            t = self.u16(table + size * k + name_at)
            if t:
                out[k] = self.text(t)
        return out

    def item_names(self):
        return self.names(self.cfg['items'], ITEM_SIZE, self.item_count())

    def class_names(self):
        return self.names(self.cfg['classes'], CLASS_SIZE, self.class_count())

    def character_names(self):
        return self.names(self.cfg['characters'], CHARACTER_SIZE, self.character_count())

    def terrain_names(self):
        return [self.text(self.u16(self.cfg['terrain_names'] + 2 * t)) for t in range(self.cfg['terrains'])]

    # Chapters and maps.
    def chapter(self, n):
        return self.cfg['chapters'] + self.cfg['chapter_size'] * n

    def pointer(self, i):
        """Entry i of the central pointer table (maps, tile configs, event data), as a file offset."""
        return self.off(self.u32(self.cfg['pointers'] + 4 * i))

    def lz77(self, o):
        """GBA BIOS LZ77 (type 0x10)."""
        R = self.R
        assert R[o] == 0x10, f'no LZ77 data at {o:#x}'
        size, out, p = self.u32(o) >> 8, bytearray(), o + 4
        while len(out) < size:
            flags = R[p]
            p += 1
            for b in range(8):
                if len(out) >= size:
                    break
                if flags & (0x80 >> b):
                    v = (R[p] << 8) | R[p + 1]
                    p += 2
                    for _ in range((v >> 12) + 3):
                        out.append(out[-((v & 0xFFF) + 1)])
                else:
                    out.append(R[p])
                    p += 1
        return bytes(out)

    def grid(self, n):
        """Chapter n's map as terrain ids, rows from the top: the map (+8) gives a metatile per tile (tile >> 2) and the tile
        config (+7) the terrain of each metatile, at 0x2000 + metatile."""
        rec = self.chapter(n)
        m = self.lz77(self.pointer(self.R[rec + 8]))
        tc = self.lz77(self.pointer(self.R[rec + 7]))
        w, h = m[0], m[1]
        return [[tc[0x2000 + (struct.unpack_from('<H', m, 2 + (y * w + x) * 2)[0] >> 2)] for x in range(w)] for y in range(h)]


@functools.lru_cache(maxsize=None)
def rom(game):
    return Rom(game)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for g in ('fe7', 'fe8'):
        r = rom(g)
        print(g, r.item_count(), 'items', r.class_count(), 'classes')
        print('  ', list(r.item_names().items())[:6])
        print('  ', list(r.character_names().items())[:6])
        print('  ', r.terrain_names()[:20])

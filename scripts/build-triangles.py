"""
Builds each game's weapon triangle data from the user's own game files (FE4's is in scripts/build-fe4-bonuses.py). Run:
    python scripts/build-triangles.py

Writes:
  - src/data/fe9/fe9Triangle.ts  (Path of Radiance)
  - src/data/fe10/fe10Triangle.ts (Radiant Dawn)
  - src/data/weapons/fatesTriangle.ts (Fates)

Where each number comes from (data-raw/<game>/README.md has the rest):
  - Path of Radiance has no triangle table in its data: it's in `sys/main.dol`. The routine at 0x801a601c walks 4-byte rows
    (attacking type, defending type, Hit, Mt) at 0x80297240 until a negative type, and stores Mt and Hit for each side. The weapon
    types are the item table's strings in the program's order (sword, lance, axe, bow, flame, thunder, wind, rod, knife).
  - Radiant Dawn's is `3SukumiData` in FE10Data.cms: 27 rows of (attacking type, defending type, Mt, Hit). `main.dol` 0x8002a8a4
    skips it when the difficulty byte is 2 (the script function `Maniac`, which is the North American Hard mode) and multiplies
    the army commander's leadership stars by 5 for hit and avoid (0x8002f9fc).
  - Fates keeps both tables in GameData.bin: the header's word at +0x40 points to the weapon rank bonuses (8 weapon types, 6 ranks
    from S down to E, two signed bytes each: attack, then hit; for staves healing, then hit) and +0x44 to the triangle bonus by the
    advantaged weapon's rank (the same layout), followed by an 8 x 8 matrix of +1 / -1 (attacking type, defending type).
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fates_lz import decompress  # noqa: E402
from fe9_files import FE9, lz10  # noqa: E402
from fe10_files import FE10  # noqa: E402

SRC = os.path.join(HERE, '..', 'src', 'data')
FATES_RAW = os.path.join(HERE, '..', 'data-raw', 'fates', 'romfs')


class Dol:
    """A GameCube / Wii main.dol: read words by their address."""

    def __init__(self, path):
        self.d = open(path, 'rb').read()
        offs = struct.unpack_from('>18I', self.d, 0)
        addrs = struct.unpack_from('>18I', self.d, 0x48)
        sizes = struct.unpack_from('>18I', self.d, 0x90)
        self.sections = [(o, a, s) for o, a, s in zip(offs, addrs, sizes) if s]

    def at(self, addr):
        for o, a, s in self.sections:
            if a <= addr < a + s:
                return o + addr - a
        raise ValueError(hex(addr))

    def word(self, addr):
        return struct.unpack_from('>I', self.d, self.at(addr))[0]

    def expect(self, words):
        """Checks the instructions the numbers are read from are still what the comments say (a different dump would fail here)."""
        for addr, w in words.items():
            assert self.word(addr) == w, f'{addr:#x}: {self.word(addr):#010x}, expected {w:#010x}'


def beats_from(rows, names):
    """{winner: [losers]} from (attacker, defender, value) rows, in the order of `names`."""
    out = {}
    for a, b, v in rows:
        if v > 0:
            out.setdefault(names[a], []).append(names[b])
    order = list(dict.fromkeys(names))
    return {k: sorted(out[k], key=order.index) for k in order if k in out}


def fe9():
    dol = Dol(os.path.join(FE9, '..', 'sys', 'main.dol'))
    dol.expect({
        0x801a6058: 0x3c608029,  # lis r3, 0x8029
        0x801a6060: 0x38837240,  # addi r4, r3, 0x7240: the table
        0x801a60e4: 0x88040003,  # lbz r0, 3(r4) -> Mt (+0x2c2, added to the weapon's Mt at 0x801a906c)
        0x801a60f0: 0x88040002,  # lbz r0, 2(r4) -> Hit (+0x2c4)
    })
    names = ['Sword', 'Lance', 'Axe', 'Bow', 'Fire', 'Thunder', 'Wind', 'Staff', 'Knife']
    pool = dol.d[dol.at(0x80268c98) - 1:dol.at(0x80268c98) + 0x100]
    assert b'\0sword\0lance\0axe\0bow\0flame\0thunder\0wind\0rod\0knife\0' in pool, 'the type strings moved'
    rows, o = [], dol.at(0x80297240)
    while dol.d[o] < 0x80:
        a, b, hit, mt = struct.unpack_from('>BBbb', dol.d, o)
        rows.append((a, b, hit, mt))
        o += 4
    hits = {abs(r[2]) for r in rows}
    mts = {abs(r[3]) for r in rows}
    assert len(hits) == 1 and len(mts) == 1, (hits, mts)
    return {'beats': beats_from([(a, b, h) for a, b, h, _ in rows], names), 'hit': hits.pop(), 'mt': mts.pop()}


def tables(d):
    """A Tellius data file's named tables: {name: (start, end)} as offsets into its data (at 0x20)."""
    _, size, n_ptrs, n_names = struct.unpack_from('>4I', d, 0)
    names_at = 0x20 + size + n_ptrs * 4
    strings_at = names_at + n_names * 8

    def c_str(o):
        return d[o:d.index(b'\0', o)].decode('shift_jis')

    found = sorted((struct.unpack_from('>I', d, names_at + 8 * k)[0], c_str(strings_at + struct.unpack_from('>I', d, names_at + 8 * k + 4)[0]))
                   for k in range(n_names))
    return {name: (start, found[i + 1][0] if i + 1 < len(found) else size) for i, (start, name) in enumerate(found)}


def fe10():
    d = lz10(open(os.path.join(FE10, 'FE10Data.cms'), 'rb').read())
    start, end = tables(d)['3SukumiData']
    base = 0x20 + start

    def s(ptr):
        return d[0x20 + ptr:d.index(b'\0', 0x20 + ptr)].decode('ascii')

    count = struct.unpack_from('>I', d, base)[0]
    rows = []
    for k in range(count):
        a, b, flags = struct.unpack_from('>III', d, base + 4 + 12 * k)
        mt, hit = struct.unpack_from('>bb', d, base + 4 + 12 * k + 8)
        rows.append((s(a), s(b), mt, hit))
    assert base + 4 + 12 * count <= 0x20 + end
    name = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'flame': 'Fire', 'thunder': 'Thunder', 'wind': 'Wind',
            'light': 'Light', 'dark': 'Dark'}
    # `elemental` stands for fire, thunder and wind against light and dark (main.dol 0x80112a3c turns those types into it).
    anima = ['flame', 'thunder', 'wind']
    beats = {}
    for a, b, mt, hit in rows:
        if hit > 0:
            for w in (anima if a == 'elemental' else [a]):
                for l in (anima if b == 'elemental' else [b]):
                    beats.setdefault(name[w], []).append(name[l])
    order = list(name.values())
    beats = {k: sorted(beats[k], key=order.index) for k in order if k in beats}
    hits = {abs(r[3]) for r in rows if r[3]}
    mts = {abs(r[2]) for r in rows if r[2]}
    assert len(hits) == 1 and len(mts) == 1, (hits, mts)

    dol = Dol(os.path.join(FE10, '..', 'sys', 'main.dol'))
    dol.expect({
        0x8002a8e4: 0x88030011,  # lbz r0, 0x11(r3): the difficulty
        0x8002a8e8: 0x28000002,  # cmplwi r0, 2
        0x8002a8ec: 0x418201e4,  # beq: no triangle at all
        0x800994c8: 0x88630011,  # the script function Maniac: difficulty == 2
        0x800994cc: 0x3803fffe,
        0x8002f9f8: 0x806300ec,  # the commander's character record
        0x8002f9fc: 0x88030021,  # lbz r0, 0x21(r3): leadership stars
        0x8002fa04: 0x5460103a,  # stars << 2
        0x8002fa08: 0x7fc01a14,  # + stars: x 5, added to hit and avoid
    })
    return {'beats': beats, 'hit': hits.pop(), 'mt': mts.pop(), 'leadershipPerStar': 5}


RANKS_FROM_S = ['S', 'A', 'B', 'C', 'D', 'E']
FATES_TYPES = ['Sword / Katana', 'Lance / Naginata', 'Axe / Club', 'Dagger / Shuriken', 'Bow / Yumi', 'Tome / Scroll', 'Staff / Rod',
               'Stone']


def fates():
    d = decompress(open(os.path.join(FATES_RAW, 'GameData.bin.lz'), 'rb').read())
    B = 0x20

    def u32(o):
        return struct.unpack_from('<I', d, o)[0]

    thresholds = list(d[B + u32(B + 0x3c):B + u32(B + 0x3c) + 6])
    assert thresholds == [251, 161, 96, 51, 21, 1], thresholds  # weapon experience for S, A, B, C, D, E

    def by_rank(o):
        """Six (first, second) signed pairs from S down to E -> {rank: [first, second]} from E up."""
        pairs = [struct.unpack_from('<bb', d, o + 2 * i) for i in range(6)]
        return {r: list(p) for r, p in reversed(list(zip(RANKS_FROM_S, pairs)))}

    rank_table = B + u32(B + 0x40)
    rank_bonus = {t: by_rank(rank_table + 12 * i) for i, t in enumerate(FATES_TYPES)}
    tri = B + u32(B + 0x44)
    assert tri == rank_table + 12 * len(FATES_TYPES), 'the triangle table follows the rank table'
    advantage = by_rank(tri)
    matrix = [[struct.unpack_from('<b', d, tri + 12 + 8 * a + b)[0] for b in range(8)] for a in range(8)]
    for a in range(8):
        for b in range(8):
            assert matrix[a][b] == -matrix[b][a], 'the matrix is antisymmetric'
    beats = beats_from([(a, b, matrix[a][b]) for a in range(8) for b in range(8)], FATES_TYPES)
    return {'beats': beats, 'advantage': advantage, 'rankBonus': rank_bonus}


def write(path, const, doc, data, source):
    lines = [
        '/*',
        f' * GENERATED by scripts/build-triangles.py from {source}. Do not edit by hand.',
        ' */',
        '',
        f'/** {doc} */',
        f'export const {const} = {json.dumps(data, indent=2, ensure_ascii=False)} as const',
    ]
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(const, json.dumps(data, ensure_ascii=False))


def main():
    write(os.path.join(SRC, 'fe9', 'fe9Triangle.ts'), 'FE9_TRIANGLE',
          'Which weapon types beat which, and what the advantage is worth (the other side loses as much).', fe9(),
          "Path of Radiance's main.dol")
    write(os.path.join(SRC, 'fe10', 'fe10Triangle.ts'), 'FE10_TRIANGLE',
          'Which weapon types beat which, what the advantage is worth (the other side loses as much), and the hit and avoid each of '
          "the army commander's leadership stars gives.", fe10(), "Radiant Dawn's FE10Data.cms (3SukumiData) and main.dol")
    write(os.path.join(SRC, 'weapons', 'fatesTriangle.ts'), 'FATES_TRIANGLE',
          'Which weapon types beat which; the triangle bonus by the advantaged weapon\'s rank ([attack, hit]; the other side loses as '
          'much); and each weapon type\'s rank bonus ([attack, hit], for staves [healing, hit]).', fates(), "Fates' GameData.bin")


if __name__ == '__main__':
    main()

"""
A chapter jump for checking a Radiant Dawn map in the game without a save there: a copy of the user's extracted disc whose New
Game opens on the chapter, with the chapter's developer roster as your army. Boot the copy's DATA/sys/main.dol in Dolphin and
start a New Game. The copy shares the game's save file (don't save in it), and RetroAchievements won't know it.

    python scripts/fe10_jump.py C0302 [C0308 ...]      -> "Extracted Games Dolphin/FE 10 jump to C0302", ...

Radiant Dawn's retail program has no debug title (Path of Radiance's does: data-raw/fe9/README.md), so two changes, written into
the copy alone (every other file of it is a hard link to the extracted disc's, nothing patched is in the repo):
- main.dol: the file menu's three New Game calls pass chapter record 1 (Part 1's Prologue) as `li r4, 1` into 0x800609d8, which
  writes it to the game state's chapter (0x803cab38 + 0x10); each becomes the chapter's record number (its chapter table
  record's +0x84).
- The chapter's script: its battle setup calls EvDevStart(map, roster) before MapLoad(map), and the retail startup.cmb's
  EvDevStart is empty, so a chapter started on a fresh game places no army. The same bytes become MapLoad(map) and
  JoinRank(roster, 5), as Part 3's Prologue joins Ike's team in its opening (team 5 is your army); a script whose string table
  lacks "JoinRank" gets it at the table's end, the file's absolute offsets moved past it.
Details: data-raw/fe10/README.md, "Checking things in the game".
"""
import os
import re
import struct
import sys

from fe10_files import FE10, GameData

DISC = os.path.dirname(os.path.dirname(FE10))  # the extracted disc's folder (FE 10), FE10 being its DATA/files
NEW_GAME_LI = (0x8019b930, 0x8019cb70, 0x8019d3d0)  # `li r4, 1` before each `bl 0x800609d8`
LI_R4 = 0x38800000
POP = b'\x20'


def chapters():
    """{script id: (record number, map folder)} from FE10Data's chapter table (0xB4 bytes a record, its id string first)."""
    g = GameData()
    out = {}
    for o in range(0x20, len(g.d) - 0xB4, 4):
        cid, mct = g.string(g.u32(o)) or '', g.string(g.u32(o + 4)) or ''
        if re.fullmatch(r'C\w+', cid) and mct.startswith('MCT'):
            out[cid] = (g.d[o + 0x84], g.string(g.u32(o + 8)))
    return out


def dol_offset(dol, addr):
    offs, addrs, sizes = (struct.unpack_from('>18I', dol, k) for k in (0, 0x48, 0x90))
    for o, a, s in zip(offs, addrs, sizes):
        if s and a <= addr < a + s:
            return o + addr - a
    raise ValueError(hex(addr))


def patch_dol(dol, record):
    dol = bytearray(dol)
    for addr in NEW_GAME_LI:
        o = dol_offset(dol, addr)
        assert struct.unpack_from('>I', dol, o)[0] == LI_R4 | 1, f'{addr:#x} is not the retail New Game call'
        struct.pack_into('>I', dol, o, LI_R4 | record)
    return bytes(dol)


class Cmb:
    """A chapter script (fe9_cmb.py's format) to patch in place."""

    def __init__(self, d):
        self.d = bytearray(d)
        assert self.d[:4] == b'cmb\0'

    def u32(self, o):
        return struct.unpack_from('<I', self.d, o)[0]

    def string_at(self, s):
        """s's offset from the string table's start, or None."""
        table = bytes(self.d[self.u32(0x24):self.u32(0x28)])
        key, i = s.encode() + b'\0', 0
        while (i := table.find(key, i)) >= 0:
            if i == 0 or table[i - 1] == 0:
                return i
            i += 1
        return None

    def add_string(self, s):
        """s put at the string table's end, over its padding, everything after it moved on by a multiple of 4 bytes."""
        if self.string_at(s) is not None:
            return
        table = self.u32(0x28)  # the handler table follows the strings
        end = table
        while self.d[end - 1] != 0:
            end -= 1
        new = s.encode() + b'\0'
        grow = max(0, (end + len(new) - table + 3) & ~3)
        records, o = [], table
        while self.u32(o):
            records.append(self.u32(o))
            o += 4
        self.d[end:table] = new + bytes(table + grow - end - len(new))
        struct.pack_into('<I', self.d, 0x28, table + grow)
        for k, r in enumerate(records):  # the handler table's offsets, each handler's name and code
            struct.pack_into('<I', self.d, table + grow + 4 * k, r + grow)
            name, code = struct.unpack_from('<2I', self.d, r + grow)
            struct.pack_into('<2I', self.d, r + grow, name + grow if name else 0, code + grow)

    def str_op(self, s):
        return b'\x1d' + struct.pack('>H', self.string_at(s))

    def call_op(self, name, argc):
        return b'\x38' + struct.pack('>H', self.string_at(name)) + bytes([argc])

    def find_once(self, seq, start=0):
        d = bytes(self.d)
        i = d.find(seq, start)
        if i < 0 or d.find(seq, i + 1) >= 0:
            return None
        return i


def patch_script(d, folder):
    """EvDevStart(map, roster) ... MapLoad(map) as ... MapLoad(map) JoinRank(roster, 5), the same length; None where the battle
    setup isn't found."""
    c = Cmb(d)
    roster = folder + '_mikata'
    if c.string_at('EvDevStart') is None or c.string_at(roster) is None:
        return None
    c.add_string('JoinRank')
    dev = c.str_op(folder) + c.str_op(roster) + c.call_op('EvDevStart', 2) + POP
    load = c.str_op(folder) + c.call_op('MapLoad', 1) + POP
    a = c.find_once(dev)
    b = None if a is None else c.find_once(load, a)
    if b is None:
        return None
    between = bytes(c.d[a + len(dev):b])  # what the setup does between them (Part 3 Ch.7: Comeback(), BlackOut())
    join = c.str_op(roster) + b'\x1a\x00\x05' + c.call_op('JoinRank', 2) + POP  # int 5 in two bytes keeps the length
    new = between + load + join
    assert len(new) == b + len(load) - a
    c.d[a:b + len(load)] = new
    return bytes(c.d)


def make(cid, record, folder):
    root = os.path.join(os.path.dirname(DISC), f'FE 10 jump to {cid}')
    script = os.path.join('DATA', 'files', 'Scripts', cid + '.cmb')
    patched = {os.path.join('DATA', 'sys', 'main.dol'): lambda d: patch_dol(d, record), script: lambda d: patch_script(d, folder)}
    linked = 0
    for dirpath, _, files in os.walk(DISC):
        rel = os.path.relpath(dirpath, DISC)
        os.makedirs(os.path.join(root, rel), exist_ok=True)
        for f in files:
            r = os.path.normpath(os.path.join(rel, f))
            src, dst = os.path.join(DISC, r), os.path.join(root, r)
            if os.path.exists(dst):
                os.remove(dst)
            out = None
            if r in patched:
                with open(src, 'rb') as fh:
                    out = patched[r](fh.read())
                if out is None:
                    print(f'{cid}: no EvDevStart before MapLoad in its script, so the chapter starts with no army')
            if out is None:
                os.link(src, dst)
                linked += 1
            else:
                with open(dst, 'wb') as fh:
                    fh.write(out)
    print(f'{root}: New Game opens {cid} (record {record}); {linked} files linked. Boot DATA/sys/main.dol, and don\'t save in it.')


def main():
    table = chapters()
    for arg in sys.argv[1:] or ['--help']:
        cid = arg if arg.startswith('C') else 'C' + arg
        if cid not in table:
            sys.exit(__doc__ if arg == '--help' else f'{arg}: no such chapter; the chapters: {" ".join(table)}')
        make(cid, *table[cid])


if __name__ == '__main__':
    main()

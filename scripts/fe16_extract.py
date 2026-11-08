"""Copy what the Armory reads out of the user's own Fire Emblem: Three Houses into data-raw/fe16/romfs (git-ignored, never
committed).

The packages (dumped with nxdumptool) sit in Documents\\FE Games\\Switch dumps\\NSP: the cartridge's base game
(`[010055D009F78000][v0][BASE]`), the 1.2.0 update (`[010055D009F78800][v327680][UPD]`) and the six DLC packages
(`[010055D009F7900n][DLC]`); the console's keys are in ~/.switch (see switch_nsp.py). The update's RomFS is a patch (BKTR) laid
over the base game's, so the two are read together.

The game keeps nearly everything in one archive: DATA0.bin, an index of 32-byte records (u64 offset, u64 size, u64 stored size,
u64 compressed), and DATA1.bin, the files it points at, each stored whole or in Koei's chunked zlib (see `koei_unzip`). Files go
by their number. The update replaces some (patchN/INFO0.bin: u64 number, u64 size, u64 stored size, u64 compressed, 0x100-byte
path of the replacement under rom:/patchN/) and adds others (INFO1.bin: the same without the number). Each DLC package has an
archive of its own, numbered on its own (0-1059), each number filled by one package.

Writes:
  romfs/<n>.bin       archive file n as the game reads it (the update's copy where it has one), decompressed: the data tables,
                      the text, the battle scripts and unit tables, the map grids, the talk events and the battles' talk lists
                      (WANTED)
  romfs/TALK_*.bin    the talk events the update adds (INFO1: TALK_EV05, Cindered Shadows', and TALK_EV06, the DLC paralogues'),
                      by their own names
  romfs/info1.json    the files the update adds, by their index in INFO1, with their paths
  romfs/main.bin      the update's program as it sits in memory (its NSO segments decompressed and relocated)
  dlc/<n>.bin         DLC archive file n (the small ones: data, scripts, unit tables)

    python scripts/fe16_extract.py
"""
import json
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(__file__))
from switch_nsp import Nsp, nso_image  # noqa: E402

NSP_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Switch dumps', 'NSP')
BASE = 'Fire Emblem_ Three Houses [010055D009F78000][v0][BASE].nsp'
UPDATE = 'Fire Emblem_ Three Houses 1.2.0 [010055D009F78800][v327680][UPD].nsp'
OUT = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe16')
# 0-82 data tables and text, 83-364 the battles' and the monastery's unit tables (.bai) and scripts (.bsi), 365-406 map grids (406:
# map 41, Beneath Garreg Mach, Cindered Shadows'); 6341-6666 the talk events TALK_EV00 to TALK_EV03 (nx/event/talk_event/script:
# INFO0 names TALK_EV00_007 6348, TALK_EV01_055 6538, TALK_EV03_008 6629...); 8845-8925 the battles' talk lists (nx/event/
# talk_scinario/dat/SCxx_yy_B.dat for scenarios 0-80: INFO0 names SC00_11_B 8856, SC01_02_B 8860, SC02_00_B 8876...).
WANTED = [*range(0, 407), *range(6341, 6667), *range(8845, 8926)]
# The update's own talk events (INFO1's nx/event/talk_event/script/TALK_EVxx_nnn.bin), copied by name.
ADDED_TALK = 'nx/event/talk_event/script/TALK_EV'
DLC_LIMIT = 0x40000      # DLC files kept: data, scripts and unit tables, not models, textures or sound


def koei_unzip(data):
    """Koei's chunked zlib: u32 chunk size, u32 chunk count, u32 total size, u32 stored size of each chunk, then (from the next
    0x80 boundary) each chunk as u32 size + zlib stream, each starting on a 0x80 boundary. A chunk that compression wouldn't
    shrink is stored as it is (its stored size is its own length, with no u32 in front)."""
    chunk, count, total = struct.unpack_from('<3I', data, 0)
    sizes = struct.unpack_from(f'<{count}I', data, 12)
    p = (12 + 4 * count + 0x7F) & ~0x7F
    out = bytearray()
    for s in sizes:
        plain = min(chunk, total - len(out))
        if s == plain:
            out += data[p:p + s]
        else:
            n = struct.unpack_from('<I', data, p)[0]
            out += zlib.decompress(data[p + 4:p + 4 + n])
        p = (p + s + 0x7F) & ~0x7F
    assert len(out) == total, (len(out), total)
    return bytes(out)


class Archive:
    """DATA0/DATA1 in a RomFS (`files`: path -> (offset, size); `rom`: the RomFS)."""

    def __init__(self, rom, files, prefix=''):
        self.rom, self.files = rom, files
        d0 = rom.open(*files[prefix + '/DATA0.bin'])
        self.entries = [struct.unpack_from('<4Q', d0, i * 32) for i in range(len(d0) // 32)]
        self.data1 = files[prefix + '/DATA1.bin'][0]

    def get(self, i):
        off, size, stored, compressed = self.entries[i]
        raw = self.rom.open(self.data1 + off, stored)
        return koei_unzip(raw) if compressed else raw

    def path(self, path):
        return self.rom.open(*self.files[path])


def merged_romfs():
    base = Nsp(os.path.join(NSP_DIR, BASE)).program()
    update = Nsp(os.path.join(NSP_DIR, UPDATE)).program()
    assert base.title_id == update.title_id == 0x010055D009F78000, (hex(base.title_id), hex(update.title_id))
    base_s = next(s for s in base.sections if s['fs_type'] == 'RomFS')
    upd_s = next(s for s in update.sections if s['fs_type'] == 'RomFS')
    rom = update.romfs_from(upd_s, update.patched_reader(upd_s, base.section_reader(base_s)))
    return update, rom, {p: (o, n) for p, o, n in rom.walk()}


def patch_index(archive, info):
    """INFO0 (replaced files: number -> path) and INFO1 (added files, in order), from the newest patch folder holding them."""
    replaced, added = {}, []
    i0 = archive.path(f'/{info}/INFO0.bin')
    for k in range(len(i0) // 0x120):
        number, size, stored, compressed = struct.unpack_from('<4Q', i0, k * 0x120)
        replaced[number] = (i0[k * 0x120 + 0x20:(k + 1) * 0x120].split(b'\0')[0].decode().replace('rom:', ''), size, compressed)
    i1 = archive.path(f'/{info}/INFO1.bin')
    for k in range(len(i1) // 0x118):
        size, stored, compressed = struct.unpack_from('<3Q', i1, k * 0x118)
        added.append((i1[k * 0x118 + 0x18:(k + 1) * 0x118].split(b'\0')[0].decode().replace('rom:', ''), size, compressed))
    counts = struct.unpack('<2Q', archive.path(f'/{info}/INFO2.bin'))
    assert counts == (len(replaced), len(added)), counts
    return replaced, added


def main():
    update, rom, files = merged_romfs()
    archive = Archive(rom, files)
    replaced, added = patch_index(archive, 'patch4')
    out = os.path.join(OUT, 'romfs')
    os.makedirs(out, exist_ok=True)
    for n in WANTED:
        if n in replaced:
            path, size, compressed = replaced[n]
            data = archive.path(path)
            data = koei_unzip(data) if compressed else data
            assert len(data) == size, (n, len(data), size)
        else:
            data = archive.get(n) if archive.entries[n][1] else b''   # an empty slot (TALK_EV01 and TALK_EV02 skip some numbers)
        open(os.path.join(out, f'{n}.bin'), 'wb').write(data)
    json.dump([{'path': p, 'size': s, 'compressed': bool(c)} for p, s, c in added], open(os.path.join(out, 'info1.json'), 'w'),
              indent=1)
    talks = 0
    for path, size, compressed in added:
        # Some INFO1 paths name a file no patch folder holds (rom:/patch4/... for an older patch's): those aren't there to copy.
        if ADDED_TALK in path and path in archive.files:
            data = archive.path(path)
            data = koei_unzip(data) if compressed else data
            open(os.path.join(out, path.rsplit('/', 1)[1]), 'wb').write(data)
            talks += 1
    print(f'romfs: {talks} talk events the update adds')
    exefs = update.pfs0(next(s for s in update.sections if s['fs_type'] == 'PFS0'))
    image, _ = nso_image(exefs.open('main'))
    open(os.path.join(out, 'main.bin'), 'wb').write(image)
    print(f'romfs: {len(WANTED)} archive files ({sum(n in replaced for n in WANTED)} from the update), main.bin {len(image):#x} bytes')

    dlc_out = os.path.join(OUT, 'dlc')
    os.makedirs(dlc_out, exist_ok=True)
    owner = {}
    for name in sorted(os.listdir(NSP_DIR)):
        if not (name.startswith('Fire Emblem_ Three Houses') and '[DLC]' in name):
            continue
        nca = next(c for _, c in Nsp(os.path.join(NSP_DIR, name)).ncas() if c.content_type == 'PublicData')
        s = next(x for x in nca.sections if x['fs_type'] == 'RomFS')
        r = nca.romfs(s)
        dlc = Archive(r, {p: (o, n) for p, o, n in r.walk()})
        kept = 0
        for n, (_off, size, _stored, _c) in enumerate(dlc.entries):
            if not size:
                continue
            assert n not in owner, f'DLC file {n} in {owner[n]} and {name}'
            owner[n] = name
            if size <= DLC_LIMIT:
                open(os.path.join(dlc_out, f'{n}.bin'), 'wb').write(dlc.get(n))
                kept += 1
        print(f'{name}: {kept} files kept')
    json.dump({n: owner[n].split('[')[1].rstrip(']') for n in sorted(owner)}, open(os.path.join(dlc_out, 'owners.json'), 'w'),
              indent=0)


if __name__ == '__main__':
    main()

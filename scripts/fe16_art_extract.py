"""Copy the battle stages' art out of the user's own Three Houses into data-raw/fe16/romfs/art (git-ignored, never committed), for
scripts/fe16_art.py: for each stage s of the base game (0-37), its terrain (archive file 2391 + s), its models (882 + s, or the nine
files from 985 + 9s for the twelve stages the program loads so: 0x59db20) and its eight texture files (1377 + 8s on), each written as
the game reads it (decompressed), as romfs/art/<n>.bin; and Cindered Shadows' stages' (38-41) from the DLC packages, as
romfs/art/dlc-<n>.bin (the DLC archive's numbers).

    python scripts/fe16_art_extract.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe16_extract as X  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe16', 'romfs', 'art')
STAGES = range(38)
RUN_STAGES = {s for s in range(33) if 0x14a8e2141 >> s & 1}


def wanted(s):
    models = [985 + 9 * s + k for k in range(9)] if s in RUN_STAGES else [882 + s]
    return [2391 + s, *models, *(1377 + 8 * s + k for k in range(8))]


# Cindered Shadows' stages (38-41) are the DLC's: the program's numbers for them less 0x8997 are the DLC archive's (fe16_art.py).
DLC_STAGES = range(38, 42)
DLC_FROM = 0x8997


def dlc_wanted(s):
    return [0x8a90 + s - DLC_FROM, 0x89b4 + s - DLC_FROM, *(0x88c0 + 8 * s + k - DLC_FROM for k in range(8))]


def dlc():
    """Cindered Shadows' stages' files, from whichever DLC package holds each, as romfs/art/dlc-<n>.bin."""
    from switch_nsp import Nsp
    want = {n for s in DLC_STAGES for n in dlc_wanted(s)}
    for name in sorted(os.listdir(X.NSP_DIR)):
        if not (name.startswith('Fire Emblem_ Three Houses') and '[DLC]' in name):
            continue
        nca = next(c for _, c in Nsp(os.path.join(X.NSP_DIR, name)).ncas() if c.content_type == 'PublicData')
        sec = next(x for x in nca.sections if x['fs_type'] == 'RomFS')
        r = nca.romfs(sec)
        archive = X.Archive(r, {p: (o, n) for p, o, n in r.walk()})
        for n in sorted(want):
            path = os.path.join(OUT, f'dlc-{n}.bin')
            if n < len(archive.entries) and archive.entries[n][1] and not os.path.exists(path):
                open(path, 'wb').write(archive.get(n))
                print('dlc', n, flush=True)


def main():
    dlc()
    update, rom, files = X.merged_romfs()
    archive = X.Archive(rom, files)
    replaced, _added = X.patch_index(archive, 'patch4')
    os.makedirs(OUT, exist_ok=True)
    for s in STAGES:
        for n in wanted(s):
            path = os.path.join(OUT, f'{n}.bin')
            if os.path.exists(path):
                continue
            if n in replaced:
                p, size, compressed = replaced[n]
                data = archive.path(p)
                data = X.koei_unzip(data) if compressed else data
            else:
                data = archive.get(n) if archive.entries[n][1] else b''
            open(path, 'wb').write(data)
        print(s, flush=True)


if __name__ == '__main__':
    main()

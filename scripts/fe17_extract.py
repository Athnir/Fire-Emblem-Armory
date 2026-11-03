"""Copy what the Armory reads out of the user's own Fire Emblem Engage into data-raw/fe17/romfs (git-ignored, never committed).

The packages (dumped with nxdumptool) sit in Documents\\FE Games\\Switch dumps\\NSP: the digital base game
(`[0100A6301214E000][v0][BASE]`) and the 2.0.0 update (`[0100A6301214E800][v327680][UPD]`), whose RomFS is a patch (BKTR) laid over
the base game's, so the two are read together; the Expansion Pass's content (its Divine Paralogues, Fell Xenologue, emblems and
items) is in the update itself, the two DLC packages being only its licences. The console's keys are in ~/.switch (see
switch_nsp.py).

The game is a Unity one: its data sits in asset bundles under Data/StreamingAssets/aa/Switch (unity_bundle.py reads them), each
holding one asset: the data tables as XML books (fe_assets_gamedata, the units of each battle in its dispos/ folder), each map's
terrain grid (fe_assets_gamedata/terrains, a MapTerrain object), the battle scripts as Lua source (fe_assets_scripts) and the text
as MSBT message files (fe_assets_message, English in us/usen). The program is IL2CPP: its code is the update's `main` NSO, its
names in Data/Managed/Metadata/global-metadata.dat.

Writes:
  gamedata/<name>.xml             each data table (gamedata/dispos/<chapter>.xml: a battle's units)
  terrains/<name>.json            each map's terrain grid: its window (m_X, m_Z, m_Width, m_Height) and its 32x32 terrain ids
  scripts/<name>.lua              each battle's script
  message/<name>.msbt             the English text
  main.bin                        the update's program as it sits in memory (its NSO segments decompressed and relocated)
  global-metadata.dat             the program's IL2CPP metadata

    python scripts/fe17_extract.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from switch_nsp import Nsp, nso_image  # noqa: E402
import unity_bundle as U  # noqa: E402

NSP_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Switch dumps', 'NSP')
BASE = 'Fire Emblem Engage [0100A6301214E000][v0][BASE].nsp'
UPDATE = 'Fire Emblem Engage 2.0.0 [0100A6301214E800][v327680][UPD].nsp'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe17', 'romfs')
AA = '/Data/StreamingAssets/aa/Switch/'
METADATA = '/Data/Managed/Metadata/global-metadata.dat'
LANGUAGE = 'us/usen'


def merged_romfs():
    base = Nsp(os.path.join(NSP_DIR, BASE)).program()
    update = Nsp(os.path.join(NSP_DIR, UPDATE)).program()
    assert base.title_id == update.title_id == 0x0100A6301214E000, (hex(base.title_id), hex(update.title_id))
    base_s = next(s for s in base.sections if s['fs_type'] == 'RomFS')
    upd_s = next(s for s in update.sections if s['fs_type'] == 'RomFS')
    rom = update.romfs_from(upd_s, update.patched_reader(upd_s, base.section_reader(base_s)))
    return update, rom, {p: (o, n) for p, o, n in rom.walk()}


def text_asset(data):
    """The one TextAsset a bundle holds: its name and its contents (str or bytes)."""
    found = [v for cid, v in U.assets(data) if cid == U.TEXT_ASSET]
    assert len(found) == 1, len(found)
    return found[0]['m_Name'], found[0]['m_Script']


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = 'wb' if isinstance(data, bytes) else 'w'
    with open(path, mode, **({} if mode == 'wb' else {'encoding': 'utf-8', 'newline': ''})) as f:
        f.write(data)


def main():
    update, rom, files = merged_romfs()
    counts = {}
    for path, (off, size) in sorted(files.items()):
        if not path.startswith(AA):
            continue
        rel = path[len(AA):]
        folder, _, name = rel.partition('/')
        if folder == 'fe_assets_gamedata':
            sub, _, leaf = name.rpartition('/')
            if sub == 'terrains':
                (terrain,) = [v for cid, v in U.assets(rom.open(off, size)) if cid == U.MONO_BEHAVIOUR]
                keep = {k: terrain[k] for k in ('m_Name', 'm_X', 'm_Z', 'm_Width', 'm_Height', 'm_Terrains', 'm_Layers', 'm_Overlaps')}
                write(os.path.join(OUT, 'terrains', leaf.replace('.bundle', '.json')), json.dumps(keep, ensure_ascii=False))
            else:
                _, text = text_asset(rom.open(off, size))
                write(os.path.join(OUT, 'gamedata', name.replace('.xml.bundle', '.xml')), text)
        elif folder == 'fe_assets_scripts':
            _, text = text_asset(rom.open(off, size))
            write(os.path.join(OUT, 'scripts', name.replace('.txt.bundle', '.lua')), text)
        elif folder == 'fe_assets_message' and name.startswith(LANGUAGE + '/'):
            _, data = text_asset(rom.open(off, size))
            write(os.path.join(OUT, 'message', name[len(LANGUAGE) + 1:].replace('.bytes.bundle', '.msbt')), data)
        else:
            continue
        counts[folder] = counts.get(folder, 0) + 1
    write(os.path.join(OUT, 'global-metadata.dat'), rom.open(*files[METADATA]))
    exefs = update.pfs0(next(s for s in update.sections if s['fs_type'] == 'PFS0'))
    image, _ = nso_image(exefs.open('main'))
    write(os.path.join(OUT, 'main.bin'), image)
    print(counts, f'main.bin {len(image):#x} bytes')


if __name__ == '__main__':
    main()

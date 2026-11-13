"""Copy the battle fields' art (field/: models, textures, placements) out of the user's own Fates cartridge dump and DLC .app files
into data-raw/fates/romfs/art (git-ignored, never committed), for scripts/fates_art.py.

    python scripts/fates_art_extract.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ncch_romfs  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data-raw', 'fates', 'romfs', 'art')
CART = r'C:/Users/golds/Documents/3ds stuff/Games/fe fates birthright/0004000000179400_v00.trim.3ds'
APPS = r'C:/Users/golds/Documents/New folder/attachments'

def main():
    r = ncch_romfs.RomFS(CART, 16384)
    n = 0
    for p, off, size in r.walk():
        if p.startswith('/field/') and not p.startswith('/field/Cas_'):
            dst = os.path.join(OUT, 'field', p[7:])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst) or os.path.getsize(dst) != size:
                open(dst, 'wb').write(r.read(off, size)); n += 1
    print('cart', n)
    for app in sorted(os.listdir(APPS)):
        if not app.endswith('.app'):
            continue
        try:
            r = ncch_romfs.RomFS(os.path.join(APPS, app))
        except AssertionError as e:
            print(app, e); continue
        for p, off, size in r.walk():
            if p.startswith('/local/field/') or p.startswith('/local/map/') or p.startswith('/local/bp/'):
                dst = os.path.join(OUT, 'dlc', app[:-4], p[7:])
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(r.read(off, size)); n += 1
    print('total', n)

if __name__ == '__main__':
    main()

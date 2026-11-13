"""Copy the battle fields' art out of the user's own Fire Emblem Engage into data-raw/fe17/romfs/art (git-ignored, never committed),
for scripts/fe17_art.py: each battle's scene bundle (fe_scenes_fld_<field>.bundle) and every bundle it draws on, followed through
their external references (CAB names, indexed from each bundle's directory) to the textures their materials use. Writes the bundles
under their own paths and deps.json (field -> the bundles it needs).

    python scripts/fe17_art_extract.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe17_extract as X  # noqa: E402
import unity_bundle as U  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe17', 'romfs', 'art')
SEARCHED = ('fe_assets_map', 'fe_scenes_fld')
LEFT_OUT = ('template', 'v001', 'v002', 'm003_title')


def directory(head):
    """The file names inside a bundle, from its header and (compressed) directory."""
    r = U.Reader(head)
    assert r.cstr() == 'UnityFS'
    version = r.take('I')
    r.cstr(), r.cstr()
    _t, packed, size, flags = r.take('QIII')
    if version >= 7:
        r.align(16)
    info = U.Reader(U._decompress(r.bytes(packed), flags, size))
    info.bytes(16)
    for _ in range(info.take('i')):
        info.take('IIH')
    names = []
    for _ in range(info.take('i')):
        info.take('QQI')
        names.append(info.cstr())
    return names


def externals(data):
    """The CAB names a bundle's serialized files point at."""
    import UnityPy
    env = UnityPy.load(io.BytesIO(data))
    out = set()
    for f in env.files.values():
        for sf in getattr(f, 'files', {}).values():
            for e in getattr(sf, 'externals', []) or []:
                out.add(e.path.split('/')[-1].replace('.sharedAssets', ''))
    return out


def main():
    update, rom, files = X.merged_romfs()
    bundles = {p[len(X.AA):]: (o, n) for p, (o, n) in files.items() if p.startswith(X.AA)
               and p[len(X.AA):].startswith(SEARCHED)}
    cab = {}
    for rel, (o, n) in bundles.items():
        for name in directory(rom.open(o, min(n, 0x40000))):
            if not name.endswith(('.resS', '.resource', '.sharedAssets')):
                cab[name] = rel
    read, ext = {}, {}

    def get(rel):
        if rel not in read:
            o, n = bundles[rel]
            read[rel] = rom.open(o, n)
            path = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'wb').write(read[rel])
            ext[rel] = {cab[c] for c in externals(read[rel]) if c in cab and cab[c] != rel}
            read[rel] = True
        return ext[rel]

    deps = {}
    for rel in sorted(bundles):
        name = os.path.basename(rel)
        if not name.startswith('fe_scenes_fld_') or any(x in name for x in LEFT_OUT):
            continue
        field = name[len('fe_scenes_fld_'):-len('.bundle')]
        seen, todo = set(), [rel]
        while todo:
            b = todo.pop()
            for d in get(b):
                if d not in seen:
                    seen.add(d)
                    todo.append(d)
        deps[field] = sorted(seen - {rel})
        print(field, len(deps[field]), flush=True)
    json.dump(deps, open(os.path.join(OUT, 'deps.json'), 'w', encoding='utf-8'), indent=0)
    print(len(read), 'bundles')


if __name__ == '__main__':
    main()

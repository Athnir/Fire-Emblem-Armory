"""Echoes' fields as scenes: a field's placement file (field/<name>.bin.lz: ReferList of [name, model, 4 words, scale, rotation in
degrees, translation]) places models found in the field's own BCH (field/<name>.bch.lz) and the shared object files its FileList
names (field/obj_*.bch.lz); textures sit in the same BCH or its _t / _ta / _tb companions. Each model comes in LODs: <model>_map is
the battle map's, then _low, _high."""
import glob
import math
import os
import struct
import sys
from functools import lru_cache

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fe13_bin import Bin  # noqa: E402
from fe15_bch import BCH, load_file  # noqa: E402
from fe15_shade import Material  # noqa: E402

RAW = os.path.join(HERE, '..', 'data-raw', 'fe15', 'romfs', 'field')  # scripts/fe15_extract.py copies the fields' art there


@lru_cache(maxsize=None)
def bch(name):
    path = os.path.join(RAW, name + '.bch.lz')
    if not os.path.exists(path):
        return None
    return BCH(load_file(path))


@lru_cache(maxsize=None)
def textures_of(name):
    """Every texture a field or object file can use: its own BCH's and its _t, _ta, _tb companions'. name -> (BCH, entry)."""
    out = {}
    for suffix in ('', '_t', '_ta', '_tb'):
        b = bch(name + suffix)
        if b is None:
            continue
        for t in b.textures():
            out.setdefault(t[0], (b, t))
    return out


_DECODED = {}


def texture(owner, tname):
    key = (owner, tname)
    if key not in _DECODED:
        e = textures_of(owner).get(tname)
        _DECODED[key] = e[0].texture_image(e[1]) if e else None
    return _DECODED[key]


@lru_cache(maxsize=None)
def models_of(name):
    b = bch(name)
    if b is None:
        return {}
    return {b.model_name(m): m for m in b.models()}


def references(field):
    """[(name, model, flags, scale, rotation degrees, translation)] and the file list of field/<field>.bin.lz."""
    b = Bin(load_file(os.path.join(RAW, field + '.bin.lz')))
    refs = []
    n, p = b.u32(b.at['ReferList']), b.u32(b.at['ReferList'] + 4)
    for i in range(n):
        o = p + i * 60
        w = struct.unpack_from('<4I9f', b.d, 0x20 + o + 8)
        refs.append((b.str(o), b.str(o + 4), w[:4], w[4:7], w[7:10], w[10:13]))
    files = []
    n, p = b.u32(b.at['FileList']), b.u32(b.at['FileList'] + 4)
    for i in range(n):
        files.append(b.str(p + 4 * i))
    return refs, files


LODS = ('_map', '_low', '', '_high')


def find_model(model, files, prefer=LODS):
    """(file, model offset, model name) of the best LOD of `model` among the files."""
    for lod in prefer:
        for f in files:
            ms = models_of(f)
            if model + lod in ms:
                return f, ms[model + lod], model + lod
    return None


def matrix(scale, rot, trans):
    """Scale, then rotate X, Y, Z (degrees), then translate."""
    rx, ry, rz = (math.radians(a) for a in rot)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    return R * np.array(scale)[None, :], np.array(trans)


UTILITY = ('ShadowMapDummyTex', 'cloudmap', 'DetailTexture')


def base_texture(names):
    """The material's colour texture: a ground split wherever it sits, else the first that isn't a utility map."""
    for n in names:
        if n and n.startswith('ground_split'):
            return n
    for n in names:
        if n and n not in UTILITY and not n.lower().startswith(('shadow', 'cloud', 'detail')):
            return n
    return None


SKIP = ('cloud', 'sky', 'fog', 'Cloud', 'Sky')


def _meshes_of(f, m, R, T, extra):
    b = bch(f)
    mats_off = b.u32(m + 0x34)
    mats = {}
    out = []
    for me in b.meshes(m):
        k = me['material']
        if k not in mats:
            mats[k] = Material(b, mats_off + k * 0x2c, lambda n, f=f: texture(f, n))
        out.append({**extra, 'file': f, 'mat': mats[k], 'material': mats[k].name, 'textures': mats[k].names,
                    'positions': me['positions'] @ R.T + T, 'uv0': me['uv0'], 'uv1': me['uv1'], 'uv2': me['uv2'], 'triangles': me['triangles'], 'color': me['color']})
    return out


def scene_meshes(field, lod_prefer=LODS):
    """Every mesh of the field placed in the world: dicts with positions (world), uv0, colour, triangles, the Material, model and
    reference names. The ground's low LOD (the land around the battle map) comes too, marked 'under'."""
    refs, files = references(field)
    files = [field] + [f for f in files if f != field]
    out = []
    for name, model, flags, scale, rot, trans in refs:
        if model.startswith(SKIP):
            continue
        found = find_model(model, files, lod_prefer)
        if not found:
            continue
        f, m, mname = found
        R, T = matrix(scale, rot, trans)
        out += _meshes_of(f, m, R, T, {'ref': name, 'model': mname, 'flags': flags})
        if model == 'ground':
            low = find_model(model, files, ('_low',))
            if low and low[2] != mname:
                out += _meshes_of(low[0], low[1], R, T, {'ref': name, 'model': low[2], 'flags': flags, 'under': True})
    return out

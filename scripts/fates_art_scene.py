"""Fates' battle fields as scenes (scratch). field/<name>.bin.lz: MapHeader, PartsList (0xf8-byte records: name, file, flags, bbox
min/max...), ReferList (0x2c-byte records: name, model, scale xyz, rotation xyz degrees, translation xyz), FileList (the field's own
file and the shared Obj_* / Mcl_* files). Models come in LODs: <model>_map (the battle map's), <model>_low (the combat scenes')."""
import glob
import math
import os
import struct
import sys
from functools import lru_cache

import numpy as np

from fe13_bin import Bin  # noqa: E402
from fe15_bch import BCH, load_file  # noqa: E402
from fates_art_material import FMaterial as Material  # noqa: E402
import fates_art_bch as bch_ext  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, '..', 'data-raw', 'fates', 'romfs', 'art')  # scripts/fates_art_extract.py
CART = os.path.join(RAW, 'field')

_pack = [None]  # the DLC pack whose field folder is searched first


def set_pack(pack):
    if _pack[0] != pack:
        _pack[0] = pack
        for f in (bch, textures_of, models_of):
            f.cache_clear()
        _DECODED.clear()


def path_of(name, ext):
    dirs = ([os.path.join(RAW, 'dlc', _pack[0], 'field')] if _pack[0] else []) + [CART]
    # other DLC packs last (a pack can use a field another pack ships)
    dirs += sorted(glob.glob(os.path.join(RAW, 'dlc', '*', 'field')))
    for d in dirs:
        p = os.path.join(d, name + ext)
        if os.path.exists(p):
            return p
    return None


@lru_cache(maxsize=None)
def bch(name):
    p = path_of(name, '.bch.lz')
    return BCH(load_file(p)) if p else None


@lru_cache(maxsize=None)
def textures_of(name):
    out = {}
    for suffix in ('', '_t', '_ta', '_tb'):
        b = bch(name + suffix)
        if b is None:
            continue
        for t in b.textures():
            out.setdefault(t[0], (b, t))
    return out


_DECODED = {}


def texture(owner, tname, files=()):
    key = (owner, tname)
    if key not in _DECODED:
        e = textures_of(owner).get(tname)
        if e is None:
            for f in files:
                e = textures_of(f).get(tname)
                if e:
                    break
        _DECODED[key] = e[0].texture_image(e[1]) if e else None
    return _DECODED[key]


@lru_cache(maxsize=None)
def models_of(name):
    b = bch(name)
    if b is None:
        return {}
    return {b.model_name(m): m for m in b.models()}


def references(field):
    b = Bin(load_file(path_of(field, '.bin.lz')))
    refs = []
    n, p = b.u32(b.at['ReferList']), b.u32(b.at['ReferList'] + 4)
    for i in range(n):
        o = p + i * 0x2c
        w = struct.unpack_from('<9f', b.d, 0x20 + o + 8)
        refs.append((b.str(o), b.str(o + 4), w[0:3], w[3:6], w[6:9]))
    files = []
    n, p = b.u32(b.at['FileList']), b.u32(b.at['FileList'] + 4)
    for i in range(n):
        files.append(b.str(p + 4 * i))
    parts = []
    n, p = b.u32(b.at['PartsList']), b.u32(b.at['PartsList'] + 4)
    for i in range(n):
        o = p + i * 0xf8
        parts.append((b.str(o), b.str(o + 4), b.u32(o + 8), struct.unpack_from('<6f', b.d, 0x20 + o + 12)))
    return refs, files, parts


def find_model(model, files, prefer=('_map',)):
    for lod in prefer:
        for f in files:
            ms = models_of(f)
            if model + lod in ms:
                return f, ms[model + lod], model + lod
    return None


def matrix(scale, rot, trans):
    rx, ry, rz = (math.radians(a) for a in rot)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    return R * np.array(scale)[None, :], np.array(trans)


def meshes_of(f, m, R, T, extra, files):
    b = bch(f)
    mats_off = b.u32(m + 0x34)
    mats = {}
    out = []
    for me in bch_ext.meshes(b, m):
        if me['positions'] is None:
            continue
        k = me['material']
        if k not in mats:
            mats[k] = Material(b, mats_off + k * 0x2c, lambda n, f=f: texture(f, n, files))
        out.append({**extra, 'file': f, 'mat': mats[k], 'material': mats[k].name, 'textures': mats[k].names,
                    'positions': me['positions'] @ R.T + T, 'uv0': me['uv0'], 'uv1': me['uv1'], 'uv2': me['uv2'],
                    'triangles': me['triangles'], 'color': me['color'], 'node': me['node'], 'bones': me['bones']})
    return out


def scene_meshes(field, skip=lambda name, model: False, prefer=('_map',)):
    refs, files, parts = references(field)
    files = [field] + [f for f in files if f != field]
    out = []
    for name, model, scale, rot, trans in refs:
        if not model or skip(name, model):
            continue
        found = find_model(model, files, prefer)
        if not found:
            continue
        f, m, mname = found
        R, T = matrix(scale, rot, trans)
        out += meshes_of(f, m, R, T, {'ref': name, 'model': mname}, files)
    return out

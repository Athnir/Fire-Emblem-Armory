"""Meshes of an H3D model placed by its skeleton (scratch): fe15_bch.BCH.meshes reads every mesh in its own space; Fates' map pieces
(Mcl_* models: bridges, doors, rocks) hang each mesh on a bone. Model +0x70 / +0x74: the skeleton (0x64-byte bones: flags, parent,
scale, rotation (radians, X then Y then Z), translation, inverse bind matrix, name). A submesh (0x34 bytes) starts with its skinning
(0 none, 1 rigid, 2 smooth) and up to 20 bone indices; a vertex's bone is its BoneIndex attribute (7) into that list, else the first.
Smooth-skinned vertices are already in model space (the bind pose). A mesh whose node is off in the model's mesh node visibility
list (+0x7c: bits, +0x80: count) is hidden at the start (treasure boxes' and doors' untextured stand-ins, Conquest 9's poison
volume, Birthright 12's glass) and left out."""
import math
import struct

import numpy as np

from fe15_bch import pica_commands


def _rot(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def skeleton(b, m):
    """[(name, 4x4 world matrix)] of the model's bones."""
    p, n = b.u32(m + 0x70), b.u32(m + 0x74)
    bones = []
    for i in range(n):
        o = p + i * 0x64
        flags, parent = struct.unpack_from('<Ih', b.d, o)
        s = struct.unpack_from('<9f', b.d, o + 8)
        M = np.eye(4)
        M[:3, :3] = _rot(*s[3:6]) * np.array(s[0:3])[None, :]
        M[:3, 3] = s[6:9]
        bones.append((b.cstr(b.u32(o + 0x5c)), parent, M, flags))
    world = []
    for i, (name, parent, M, flags) in enumerate(bones):
        W = world[parent][1] @ M if 0 <= parent < i else M
        world.append((name, W))
    return world


def meshes(b, m):
    """fe15_bch's meshes, one per mesh, with positions placed by the skeleton and the bone names used."""
    bones = skeleton(b, m)
    vp, vn = b.u32(m + 0x7c), b.u32(m + 0x80)
    visible = [bool((b.u32(vp + 4 * (k // 32)) >> (k % 32)) & 1) for k in range(vn)]
    mesh0, n = b.u32(m + 0x40), b.u32(m + 0x44)
    cull, ncull = b.u32(m + 0x68), b.u32(m + 0x6c)
    out = []
    for i in range(n):
        o = mesh0 + i * 0x38
        mi, fl, node, pri = struct.unpack_from('<4H', b.d, o)
        if node < len(visible) and not visible[node]:
            continue  # hidden at the start (the model's mesh node visibility list, +0x7c / +0x80)
        cmd, words, sub, nsub = struct.unpack_from('<4I', b.d, o + 8)
        regs, uni = pica_commands(b.d, cmd, words)
        r = lambda k, dflt=0: regs.get(k, [dflt])[-1]
        fmts = r(0x201) | (r(0x202) & 0xffff) << 32
        perm = r(0x2bb) | r(0x2bc) << 32
        addr = r(0x203)
        c1, c2 = r(0x204), r(0x205)
        comps = c1 | (c2 & 0xffff) << 32
        stride = (c2 >> 16) & 0xff
        ncomp = c2 >> 28
        off6 = uni.get(6, [0, 0, 0, 0])
        s7 = uni.get(7, [1, 1, 0, 1])
        s8 = uni.get(8, [1, 1, 1, 1])
        scale = {0: s7[0], 1: s7[1], 2: s7[2], 3: s7[3], 4: s8[0], 5: s8[1], 6: s8[2], 8: s8[3]}
        subs = []  # (triangles, skinning, bone list)
        if nsub:
            for k in range(nsub):
                so = sub + k * 0x34
                sk, bc = struct.unpack_from('<HH', b.d, so)
                bl = struct.unpack_from('<20H', b.d, so + 4)[:bc]
                fc, fw = struct.unpack_from('<II', b.d, so + 0x2c)
                fr, _ = pica_commands(b.d, fc, fw)
                cfg = fr.get(0x227, [0])[-1]
                cnt = fr.get(0x228, [0])[-1]
                prim = (fr.get(0x25e, [0])[-1] >> 8) & 3
                subs.append(((cfg & 0x7fffffff, cnt, bool(cfg >> 31), prim), sk, bl))
        elif i < ncull:
            co = cull + i * 0x1c
            ft, fcnt = struct.unpack_from('<II', b.d, co + 0x10)
            for k in range(fcnt):
                ia, ic = struct.unpack_from('<II', b.d, ft + k * 8)
                subs.append(((ia & 0x7fffffff, ic, True, 0), 0, ()))
        tri_sets = []
        for (ia, ic, wide, prim), sk, bl in subs:
            idx = np.frombuffer(b.d, np.uint16 if wide else np.uint8, ic, ia).astype(np.int64)
            if prim == 1:
                t = []
                for j in range(ic - 2):
                    a, b_, c = idx[j], idx[j + 1], idx[j + 2]
                    t.append((a, b_, c) if j % 2 == 0 else (b_, a, c))
                T = np.array(t, np.int64).reshape(-1, 3)
            else:
                T = idx[:ic - ic % 3].reshape(-1, 3)
            tri_sets.append((T, sk, bl))
        T_all = np.concatenate([t for t, _, _ in tri_sets]) if tri_sets else np.zeros((0, 3), np.int64)
        nv = int(T_all.max()) + 1 if len(T_all) else 0
        attrs = {}
        p = 0
        for k in range(ncomp):
            a = (comps >> (4 * k)) & 0xf
            if a >= 12:
                p += {12: 4, 13: 8, 14: 12, 15: 16}[a]
                continue
            f = (fmts >> (4 * a)) & 0xf
            typ, size = f & 3, (f >> 2) + 1
            dt = [np.int8, np.uint8, np.int16, np.float32][typ]
            esz = [1, 1, 2, 4][typ]
            name = (perm >> (4 * a)) & 0xf
            vals = np.zeros((nv, size), np.float64)
            if nv:
                raw = np.frombuffer(b.d, np.uint8, nv * stride, addr)
                rec = raw.reshape(nv, stride)[:, p:p + esz * size].copy()
                vals = rec.view(dt).reshape(nv, size).astype(np.float64)
            attrs[name] = vals * (scale.get(name, 1.0) if typ != 3 and name not in (7,) else 1.0)
            p += esz * size
            if esz == 2 and p % 2:
                p += 1
            if esz == 4 and p % 4:
                p += 4 - p % 4
        pos = attrs.get(0)
        if pos is None:
            continue
        pos = pos[:, :3] + np.array(off6[:3])
        # place each vertex by its bone
        placed = pos.copy()
        bone_of = np.full(nv, -1, np.int64)
        for T, sk, bl in tri_sets:
            vs = np.unique(T)
            if sk == 2 or not bl:
                continue
            if sk == 1 and 7 in attrs and len(bl) > 1:
                bi = attrs[7][vs, 0].astype(np.int64)
                bone_of[vs] = np.array(bl)[np.clip(bi, 0, len(bl) - 1)]
            else:
                bone_of[vs] = bl[0]
        for bi in np.unique(bone_of):
            if bi < 0 or bi >= len(bones):
                continue
            sel = bone_of == bi
            W = bones[bi][1]
            placed[sel] = pos[sel] @ W[:3, :3].T + W[:3, 3]
        used = sorted({bones[x][0] for x in np.unique(bone_of) if 0 <= x < len(bones)})
        out.append({'material': mi, 'node': node, 'positions': placed, 'uv0': attrs.get(4), 'uv1': attrs.get(5),
                    'uv2': attrs.get(6), 'color': attrs.get(3), 'triangles': T_all, 'bones': used, 'regs': regs})
    return out

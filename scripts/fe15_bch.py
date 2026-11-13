"""A reader for the 3DS BCH (H3D) container as Echoes: Shadows of Valentia stores its field models and textures.

Header (version 0x22/0x23 here): offsets and lengths of the contents, strings, GPU commands, raw data and extended raw data
sections, then a relocation table. Each relocation word: bits 0-24 the pointer's place (in words, in bytes for strings), bits 25-28
the target section whose base is added, bits 29-31 the section the pointer sits in. After relocation every pointer is a file
offset. Textures and vertex/index buffers are described by PICA200 GPU commands.
"""
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_lz import lz11  # noqa: E402
from nds_rom import lz10  # noqa: E402


def decompress(raw):
    t = raw[0]
    if t == 0x13:
        return lz11(raw[4:])
    if t == 0x11:
        return lz11(raw)
    if t == 0x10:
        return lz10(raw)
    if t == 0x00:
        size = int.from_bytes(raw[1:4], 'little')
        return raw[4:4 + size]
    raise ValueError(f'unknown compression {t:#x}')


def load_file(path):
    raw = open(path, 'rb').read()
    return decompress(raw) if path.endswith('.lz') else raw


# ---------------------------------------------------------------------------------------------------------------------------
# PICA200 commands

def pica_commands(d, off, words):
    """{register: [values]} of a PICA command list (each command: parameter, header; header = id | mask << 16 | extra << 20 |
    consecutive << 31; then the extra parameters, padded to 8 bytes). Also the float-uniform writes as (index, [floats])."""
    regs = {}
    uniforms = {}
    cur_uni = None
    uni_buf = []
    end = off + words * 4
    p = off
    while p + 8 <= end:
        param, header = struct.unpack_from('<II', d, p)
        p += 8
        rid = header & 0xffff
        extra = (header >> 20) & 0x7ff
        consec = header >> 31
        vals = [param] + list(struct.unpack_from('<%dI' % extra, d, p))
        p += extra * 4
        if extra & 1:
            p += 4  # pad to 8 bytes
        for i, v in enumerate(vals):
            r = rid + i if consec else rid
            regs.setdefault(r, []).append(v)
            if r == 0x2c0:
                cur_uni = v & 0xff
                uni_buf = []
            elif 0x2c1 <= r <= 0x2c8 and cur_uni is not None:
                uni_buf.append(struct.unpack('<f', struct.pack('<I', v))[0])
                if len(uni_buf) == 4:
                    # float32 mode: written w, z, y, x
                    uniforms[cur_uni] = uni_buf[::-1]
                    cur_uni += 1
                    uni_buf = []
    return regs, uniforms


# ---------------------------------------------------------------------------------------------------------------------------
# Texture codecs

TEX_FORMATS = {0: 'RGBA8', 1: 'RGB8', 2: 'RGBA5551', 3: 'RGB565', 4: 'RGBA4', 5: 'LA8', 6: 'HILO8', 7: 'L8', 8: 'A8', 9: 'LA4',
               10: 'L4', 11: 'A4', 12: 'ETC1', 13: 'ETC1A4'}
BPP = {0: 32, 1: 24, 2: 16, 3: 16, 4: 16, 5: 16, 6: 16, 7: 8, 8: 8, 9: 8, 10: 4, 11: 4, 12: 4, 13: 8}

# Morton order of an 8x8 tile: index -> (x, y)
_MORTON = []
for i in range(64):
    x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
    y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
    _MORTON.append((x, y))
_MX = np.array([m[0] for m in _MORTON])
_MY = np.array([m[1] for m in _MORTON])

ETC_MOD = np.array([[2, 8, -2, -8], [5, 17, -5, -17], [9, 29, -9, -29], [13, 42, -13, -42], [18, 60, -18, -60],
                    [24, 80, -24, -80], [33, 106, -33, -106], [47, 183, -47, -183]])


def _etc1_block(block):
    """One 4x4 ETC1 block (u64 little endian as the 3DS stores it) -> 4x4x3."""
    lo = block & 0xffffffff
    hi = block >> 32
    flip = hi & 1
    diff = (hi >> 1) & 1
    t1 = (hi >> 5) & 7
    t2 = (hi >> 2) & 7
    if diff:
        r = (hi >> 27) & 0x1f
        g = (hi >> 19) & 0x1f
        b = (hi >> 11) & 0x1f
        dr = ((hi >> 24) & 7)
        dg = ((hi >> 16) & 7)
        db = ((hi >> 8) & 7)
        dr = dr - 8 if dr > 3 else dr
        dg = dg - 8 if dg > 3 else dg
        db = db - 8 if db > 3 else db
        r2, g2, b2 = r + dr, g + dg, b + db
        c1 = [(v << 3) | (v >> 2) for v in (r, g, b)]
        c2 = [(v << 3) | (v >> 2) for v in (r2 & 0x1f, g2 & 0x1f, b2 & 0x1f)]
    else:
        c1 = [((hi >> s) & 0xf) * 17 for s in (28, 20, 12)]
        c2 = [((hi >> s) & 0xf) * 17 for s in (24, 16, 8)]
    out = np.zeros((4, 4, 3), np.int32)
    for py in range(4):
        for px in range(4):
            i = px * 4 + py
            msb = (lo >> (16 + i)) & 1
            lsb = (lo >> i) & 1
            idx = (msb << 1) | lsb
            # 0: +small, 1: +large, 2: -small, 3: -large  (table order [a, b, -a, -b])
            sub2 = (py >= 2) if flip else (px >= 2)
            base = c2 if sub2 else c1
            tab = t2 if sub2 else t1
            m = ETC_MOD[tab][[0, 1, 2, 3][idx]]
            out[py, px] = [base[0] + m, base[1] + m, base[2] + m]
    return np.clip(out, 0, 255)


def decode_texture(data, w, h, fmt):
    """Raw PICA texture -> RGBA uint8 array (h, w, 4) in stored order: the first stored row is the image's top (the title logo
    reads upright), sampled at row (1 - v) * h."""
    img = np.zeros((h, w, 4), np.uint8)
    if fmt in (12, 13):
        p = 0
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for sb in range(4):
                    bx = tx + (sb & 1) * 4
                    by = ty + (sb >> 1) * 4
                    alpha = None
                    if fmt == 13:
                        alpha = struct.unpack_from('<Q', data, p)[0]
                        p += 8
                    block = struct.unpack_from('<Q', data, p)[0]
                    p += 8
                    rgb = _etc1_block(block)
                    img[by:by + 4, bx:bx + 4, :3] = rgb
                    if alpha is None:
                        img[by:by + 4, bx:bx + 4, 3] = 255
                    else:
                        for px in range(4):
                            for py in range(4):
                                a = (alpha >> (4 * (px * 4 + py))) & 0xf
                                img[by + py, bx + px, 3] = a * 17
        return img
    bpp = BPP[fmt]
    n = w * h
    if bpp == 4:
        raw = np.frombuffer(data, np.uint8, n // 2)
        vals = np.empty(n, np.uint8)
        vals[0::2] = raw & 0xf
        vals[1::2] = raw >> 4
    else:
        raw = np.frombuffer(data, np.uint8, n * bpp // 8).reshape(n, bpp // 8)
    # pixel i of the linear stream -> (x, y)
    tiles_x = w // 8
    idx = np.arange(n)
    tile = idx // 64
    within = idx % 64
    xs = (tile % tiles_x) * 8 + _MX[within]
    ys = (tile // tiles_x) * 8 + _MY[within]
    out = np.zeros((n, 4), np.uint8)
    if fmt == 0:  # RGBA8 stored ABGR
        out[:, 0], out[:, 1], out[:, 2], out[:, 3] = raw[:, 3], raw[:, 2], raw[:, 1], raw[:, 0]
    elif fmt == 1:  # RGB8 stored BGR
        out[:, 0], out[:, 1], out[:, 2], out[:, 3] = raw[:, 2], raw[:, 1], raw[:, 0], 255
    elif fmt in (2, 3, 4):
        v = raw[:, 0].astype(np.uint16) | (raw[:, 1].astype(np.uint16) << 8)
        if fmt == 2:
            out[:, 0] = ((v >> 11) & 0x1f) * 255 // 31
            out[:, 1] = ((v >> 6) & 0x1f) * 255 // 31
            out[:, 2] = ((v >> 1) & 0x1f) * 255 // 31
            out[:, 3] = (v & 1) * 255
        elif fmt == 3:
            out[:, 0] = ((v >> 11) & 0x1f) * 255 // 31
            out[:, 1] = ((v >> 5) & 0x3f) * 255 // 63
            out[:, 2] = (v & 0x1f) * 255 // 31
            out[:, 3] = 255
        else:
            out[:, 0] = ((v >> 12) & 0xf) * 17
            out[:, 1] = ((v >> 8) & 0xf) * 17
            out[:, 2] = ((v >> 4) & 0xf) * 17
            out[:, 3] = (v & 0xf) * 17
    elif fmt == 5:  # LA8: A, L
        out[:, 0] = out[:, 1] = out[:, 2] = raw[:, 1]
        out[:, 3] = raw[:, 0]
    elif fmt == 6:  # HILO8
        out[:, 0], out[:, 1], out[:, 2], out[:, 3] = raw[:, 1], raw[:, 0], 0, 255
    elif fmt == 7:
        out[:, 0] = out[:, 1] = out[:, 2] = raw[:, 0]
        out[:, 3] = 255
    elif fmt == 8:
        out[:, 0] = out[:, 1] = out[:, 2] = 255
        out[:, 3] = raw[:, 0]
    elif fmt == 9:
        l = raw[:, 0] >> 4
        a = raw[:, 0] & 0xf
        out[:, 0] = out[:, 1] = out[:, 2] = l * 17
        out[:, 3] = a * 17
    elif fmt == 10:
        out[:, 0] = out[:, 1] = out[:, 2] = vals * 17
        out[:, 3] = 255
    elif fmt == 11:
        out[:, 0] = out[:, 1] = out[:, 2] = 255
        out[:, 3] = vals * 17
    img[ys, xs] = out
    return img


def texture_size(w, h, fmt):
    return w * h * BPP[fmt] // 8


# ---------------------------------------------------------------------------------------------------------------------------
# The container

class BCH:
    def __init__(self, data):
        d = bytearray(data)
        assert d[:4] == b'BCH\0', d[:4]
        self.back, self.fwd, self.version = d[4], d[5], struct.unpack_from('<H', d, 6)[0]
        assert self.back > 0x20, 'old BCH versions not handled'
        (self.contents, self.strings, self.commands, self.raw, self.rawext, self.reloc,
         self.contents_len, self.strings_len, self.commands_len, self.raw_len, self.rawext_len, self.reloc_len,
         self.uninit_data, self.uninit_desc) = struct.unpack_from('<14I', d, 8)
        self.flags, self.addr_count = struct.unpack_from('<HH', d, 0x40)
        base = {0: self.contents, 1: self.strings, 2: self.commands, 3: self.commands, 4: self.raw, 5: self.raw, 6: self.raw,
                7: self.raw, 8: self.raw, 9: self.rawext, 10: self.rawext, 11: self.rawext, 12: self.rawext, 13: self.rawext,
                14: self.rawext}
        for i in range(0, self.reloc_len, 4):
            v = struct.unpack_from('<I', d, self.reloc + i)[0]
            ptr = v & 0x1ffffff
            target = (v >> 25) & 0xf
            source = v >> 29
            if target != 1:
                ptr <<= 2
            at = base[source] + ptr
            val = struct.unpack_from('<I', d, at)[0] + base[target]
            if source == 2 and target in (7, 12):
                val |= 0x80000000  # a 16-bit index buffer
            struct.pack_into('<I', d, at, val & 0xffffffff)
        self.d = bytes(d)

    def u32(self, o):
        return struct.unpack_from('<I', self.d, o)[0]

    def f32s(self, o, n):
        return struct.unpack_from('<%df' % n, self.d, o)

    def cstr(self, o):
        if not o:
            return None
        e = self.d.index(b'\0', o)
        return self.d[o:e].decode('ascii', 'replace')

    def table(self, i):
        """The i-th (pointer table, count, names) triple of the contents header: [entry offsets]."""
        ptr, cnt, names = struct.unpack_from('<3I', self.d, self.contents + 12 * i)
        return [self.u32(ptr + 4 * k) for k in range(cnt)]

    # contents header order (H3D): models, materials, shaders, textures, LUTs, lights, cameras, fogs, skeletal anims,
    # material anims, visibility anims, light anims, camera anims, fog anims, scenes
    def models(self):
        return self.table(0)

    def textures(self):
        """[(name, width, height, format, data offset, data length)] of the file's textures (unit 0 commands)."""
        out = []
        for e in self.table(3):
            cmd, words = struct.unpack_from('<II', self.d, e)
            name = self.cstr(self.u32(e + 0x1c))
            regs, _ = pica_commands(self.d, cmd, words)
            size = regs.get(0x82, [0])[0]
            w, h = size >> 16, size & 0xffff
            fmt = regs.get(0x8e, [0])[0] & 0xf
            addr = regs.get(0x85, [0])[0]
            out.append((name, w, h, fmt, addr, texture_size(w, h, fmt)))
        return out

    def texture_image(self, t):
        name, w, h, fmt, addr, n = t
        return decode_texture(self.d[addr:addr + n], w, h, fmt)


    def materials(self, m):
        """A model's materials: [(texture names of units 0-2, name)] by index."""
        mats, n = self.u32(m + 0x34), self.u32(m + 0x38)
        out = []
        for i in range(n):
            w = struct.unpack_from('<11I', self.d, mats + i * 0x2c)
            out.append(([self.cstr(x) for x in w[7:10]], self.cstr(w[10])))
        return out

    def model_name(self, m):
        return self.cstr(self.u32(m + 0x84))

    def meshes(self, m):
        """A model's meshes: dicts with material, positions (N x 3), uv0 (N x 2) or None, color (N x 4) or None, triangles
        (M x 3), node."""
        mesh0, n = self.u32(m + 0x40), self.u32(m + 0x44)
        cull, ncull = self.u32(m + 0x68), self.u32(m + 0x6c)
        out = []
        for i in range(n):
            o = mesh0 + i * 0x38
            mi, fl, node, pri = struct.unpack_from('<4H', self.d, o)
            cmd, words, sub, nsub = struct.unpack_from('<4I', self.d, o + 8)
            regs, uni = pica_commands(self.d, cmd, words)
            r = lambda k, dflt=0: regs.get(k, [dflt])[-1]
            fmts = r(0x201) | (r(0x202) & 0xffff) << 32
            total_attr = (r(0x202) >> 28) + 1
            fixed_mask = (r(0x202) >> 16) & 0xfff
            perm = r(0x2bb) | r(0x2bc) << 32  # input register -> attribute name
            addr = r(0x203)
            c1, c2 = r(0x204), r(0x205)
            comps = c1 | (c2 & 0xffff) << 32
            stride = (c2 >> 16) & 0xff
            ncomp = c2 >> 28
            off6 = uni.get(6, [0, 0, 0, 0])
            s7 = uni.get(7, [1, 1, 0, 1])
            s8 = uni.get(8, [1, 1, 1, 1])
            scale = {0: s7[0], 1: s7[1], 2: s7[2], 3: s7[3], 4: s8[0], 5: s8[1], 6: s8[2], 8: s8[3]}
            # triangles
            tris = []
            if nsub:
                for k in range(nsub):
                    so = sub + k * 0x34
                    fc, fw = struct.unpack_from('<II', self.d, so + 0x2c)
                    fr, _ = pica_commands(self.d, fc, fw)
                    cfg = fr.get(0x227, [0])[-1]
                    cnt = fr.get(0x228, [0])[-1]
                    prim = (fr.get(0x25e, [0])[-1] >> 8) & 3
                    tris.append((cfg & 0x7fffffff, cnt, bool(cfg >> 31), prim))
            elif i < ncull:
                co = cull + i * 0x1c
                ft, fcnt = struct.unpack_from('<II', self.d, co + 0x10)
                for k in range(fcnt):
                    ia, ic = struct.unpack_from('<II', self.d, ft + k * 8)
                    tris.append((ia & 0x7fffffff, ic, True, 0))
            idx_all = []
            for ia, ic, wide, prim in tris:
                idx = np.frombuffer(self.d, np.uint16 if wide else np.uint8, ic, ia).astype(np.int64)
                if prim == 1:  # strip
                    t = []
                    for j in range(ic - 2):
                        a, b_, c = idx[j], idx[j + 1], idx[j + 2]
                        t.append((a, b_, c) if j % 2 == 0 else (b_, a, c))
                    idx_all.append(np.array(t, np.int64).reshape(-1, 3))
                else:
                    idx_all.append(idx[:ic - ic % 3].reshape(-1, 3))
            T = np.concatenate(idx_all) if idx_all else np.zeros((0, 3), np.int64)
            nv = int(T.max()) + 1 if len(T) else 0
            attrs = {}
            p = 0
            for k in range(ncomp):
                a = (comps >> (4 * k)) & 0xf  # loader attribute index
                if a >= 12:
                    p += {12: 4, 13: 8, 14: 12, 15: 16}[a]  # padding component
                    continue
                f = (fmts >> (4 * a)) & 0xf
                typ, size = f & 3, (f >> 2) + 1
                dt = [np.int8, np.uint8, np.int16, np.float32][typ]
                esz = [1, 1, 2, 4][typ]
                name = (perm >> (4 * a)) & 0xf
                raw = np.frombuffer(self.d, np.uint8, nv * stride if nv else 0, addr)
                vals = np.zeros((nv, size), np.float64)
                if nv:
                    rec = raw.reshape(nv, stride)[:, p:p + esz * size].copy()
                    vals = rec.view(dt).reshape(nv, size).astype(np.float64)
                attrs[name] = vals * (scale.get(name, 1.0) if typ != 3 else 1.0)
                p += esz * size
                if esz == 2 and p % 2:
                    p += 1
                if esz == 4 and p % 4:
                    p += 4 - p % 4
            pos = attrs.get(0)
            if pos is not None:
                pos = pos[:, :3] + np.array(off6[:3])
            out.append({'material': mi, 'node': node, 'positions': pos, 'uv0': attrs.get(4), 'uv1': attrs.get(5), 'uv2': attrs.get(6),
                        'color': attrs.get(3), 'triangles': T, 'regs': regs, 'uniforms': uni})
        return out


if __name__ == '__main__':
    b = BCH(load_file(sys.argv[1]))
    print('version', hex(b.back), hex(b.fwd), hex(b.version))
    for i in range(15):
        ptr, cnt, names = struct.unpack_from('<3I', b.d, b.contents + 12 * i)
        print(i, hex(ptr), cnt, hex(names))
    for t in b.textures():
        print(t[0], t[1], t[2], TEX_FORMATS.get(t[3]), hex(t[4]))

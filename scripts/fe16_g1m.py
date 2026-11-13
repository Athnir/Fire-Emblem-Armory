"""
Three Houses' models (G1M) and textures (G1T), Koei Tecmo's formats, read as far as drawing a battle field from above needs: each
mesh's positions, first UV set and vertex colours, its triangles and its colour texture. The layouts follow Joschuka's fmt_g1m (the
Noesis plugin, github.com/Joschuka/fmt_g1m) and the Three Houses Research Team's templates (010-binary-templates: G1M, G1T), each
checked against the game's own files here.

G1M: '_M1G', a version, the file size, the header size, u32 0, the chunk count; then chunks (u32 magic, a version, u32 size): G1MF,
G1MS (the skeleton), G1MM, G1MG (the geometry), EXTR... G1MG: a platform tag ('NX_ '), a float, the bounding box (six floats), the
count of its sections, each a u32 id (0x10001-0x10009) and size:
  0x10002 materials: per material u32 0, u32 texture count, two u32, then per texture u16 index (into the G1T), layer, type (1 colour,
          3 normal, ...), subtype, tile mode u and v;
  0x10004 vertex buffers: u32 0, stride, count, u32 0 (versions after 0040), the data;
  0x10005 vertex layouts: the buffers they read, then per element u16 buffer slot, u16 offset, u8 u8 the data type (0x0002 float3+1,
          0x0003 float4, 0x0001 float2, 0x000A half2, 0x000B half4, 0x0005 u8x4, 0x000D u8x4 normalised), u8 the attribute (0
          position, 3 normal, 5 UV, 10 colour) and u8 its layer;
  0x10007 index buffers: count, type (0x10 u16, 0x20 u32, 8 u8), u32 0, the data, padded to 4;
  0x10008 submeshes: 14 i32: +1 vertex buffer (and layout), +2 the joint map, +6 the material, +7 the index buffer, +9 3 triangles /
          4 a strip, +10 first vertex, +11 vertex count, +12 first index, +13 index count;
  0x10009 the LODs: each submesh listed under the LOD that draws it (the first is the full model).
G1T: 'GT1G', a version, the file size, the table's offset, the texture count, the platform (10 here: the textures aren't swizzled), a
size of ASTC data; a u32 per texture (normal-map flags), then from the table a u32 offset per texture to its 8-byte header: high
nibble the mip count, the format, log2 width and height in the nibbles, ..., an extra-header version (then u32 size, two u32, maybe
the width and height), then the data, top mip first. Formats: 0x59 BC1, 0x5B BC3, 0x5C BC4, 0x5D BC5, 0x5E BC6H, 0x5F BC7, 0/1 RGBA8
/ BGRA8.
"""
import struct

import numpy as np
from PIL import Image


def _chunks(data, start, count):
    o = start
    for _ in range(count):
        magic, version, size = struct.unpack_from('<4s4sI', data, o)
        yield magic, version, data[o:o + size]
        o += size


class G1M:
    """One G1M: `meshes` [{'positions': (n, 3), 'uv': (n, 2) or None, 'colour': (n, 4) or None, 'triangles': (m, 3), 'material':
    the index of its material}], `materials` [[(texture index, layer, type), ...]], `bbox`."""

    def __init__(self, data):
        magic, version, size, header, _zero, count = struct.unpack_from('<4s4sIIII', data, 0)
        assert magic == b'_M1G', magic
        self.meshes, self.materials, self.bbox = [], [], None
        for magic, ver, chunk in _chunks(data, header, count):
            if magic == b'GM1G':
                self._g1mg(chunk, int(ver[::-1].decode()) if ver[::-1].isdigit() else 0)

    def _g1mg(self, chunk, version):
        # The chunk's own 12-byte header, the platform tag, a float, the bounding box, the section count.
        self.bbox = struct.unpack_from('<6f', chunk, 0x14)
        count = struct.unpack_from('<I', chunk, 0x2c)[0]
        o = 0x30
        vbufs, layouts, ibufs, subs, lod0 = [], [], [], [], None
        for _ in range(count):
            sid, ssize = struct.unpack_from('<II', chunk, o)
            body = chunk[o + 8:o + ssize]
            if sid == 0x10002:
                self.materials = self._materials(body)
            elif sid == 0x10004:
                vbufs = self._vertex_buffers(body, version)
            elif sid == 0x10005:
                layouts = self._layouts(body)
            elif sid == 0x10007:
                ibufs = self._index_buffers(body, version)
            elif sid == 0x10008:
                n = struct.unpack_from('<I', body, 0)[0]
                subs = [struct.unpack_from('<14i', body, 4 + 56 * i) for i in range(n)]
            elif sid == 0x10009:
                lod0 = self._lod0(body, version)
            o += ssize
        drawn = range(len(subs)) if lod0 is None else sorted(set(lod0))
        for i in drawn:
            if i >= len(subs):
                continue
            s = subs[i]
            if s[11] <= 0 or s[13] <= 0:
                continue
            mesh = self._mesh(s, vbufs, layouts[s[1]], ibufs[s[7]])
            if mesh is not None:
                mesh['material'] = s[6]
                self.meshes.append(mesh)

    @staticmethod
    def _materials(body):
        n = struct.unpack_from('<I', body, 0)[0]
        o, out = 4, []
        for _ in range(n):
            _z, tcount, _a, _b = struct.unpack_from('<IIii', body, o)
            o += 16
            texs = []
            for _ in range(tcount):
                idx, layer, kind, sub, tu, tv = struct.unpack_from('<6H', body, o)
                texs.append((idx, layer, kind))
                o += 12
            out.append(texs)
        return out

    @staticmethod
    def _vertex_buffers(body, version):
        n = struct.unpack_from('<I', body, 0)[0]
        o, out = 4, []
        for _ in range(n):
            _z, stride, count = struct.unpack_from('<III', body, o)
            o += 12 + (4 if version > 40 else 0)
            out.append((stride, count, body[o:o + stride * count]))
            o += stride * count
        return out

    @staticmethod
    def _layouts(body):
        n = struct.unpack_from('<I', body, 0)[0]
        o, out = 4, []
        for _ in range(n):
            nb = struct.unpack_from('<I', body, o)[0]
            bufs = struct.unpack_from(f'<{nb}i', body, o + 4)
            o += 4 + 4 * nb
            ne = struct.unpack_from('<I', body, o)[0]
            o += 4
            els = []
            for _ in range(ne):
                slot, off, b1, b2, attr, layer = struct.unpack_from('<HHBBBB', body, o)
                els.append({'buffer': bufs[slot], 'offset': off, 'type': (b1 << 8) | b2, 'attr': attr, 'layer': layer})
                o += 8
            out.append(els)
        return out

    @staticmethod
    def _index_buffers(body, version):
        n = struct.unpack_from('<I', body, 0)[0]
        o, out = 4, []
        for _ in range(n):
            count, kind = struct.unpack_from('<II', body, o)
            o += 8 + (4 if version > 40 else 0)
            width = {8: 1, 0x10: 2, 0x20: 4}[kind]
            out.append(np.frombuffer(body, {1: '<u1', 2: '<u2', 4: '<u4'}[width], count, o).astype(np.int64))
            o += (count * width + 3) & ~3
        return out

    @staticmethod
    def _lod0(body, version):
        n = struct.unpack_from('<I', body, 0)[0]
        if not n:
            return None
        o = 4 + 12
        c1, c2 = struct.unpack_from('<II', body, o)
        o += 8 + (16 if version > 40 else 0)
        out = []
        for _ in range(c1 + c2):
            o += 16 + 2 + 2 + 4
            k = struct.unpack_from('<I', body, o)[0]
            o += 4
            out += list(struct.unpack_from(f'<{k}I', body, o))
            o += 4 * k
            if k == 0:
                o += 4
        return out

    @staticmethod
    def _attr(buf, el, first, count):
        stride, total, data = buf
        a = np.frombuffer(data, np.uint8).reshape(total, stride)[first:first + count, el['offset']:]
        t = el['type'] & 0xff if el['type'] & 0xff else el['type'] >> 8
        if t in (2, 3):
            return a[:, :16].copy().view('<f4').reshape(count, 4)
        if t == 1:
            return a[:, :8].copy().view('<f4').reshape(count, 2)
        if t == 0xA:
            return a[:, :4].copy().view('<f2').reshape(count, 2).astype(np.float32)
        if t == 0xB:
            return a[:, :8].copy().view('<f2').reshape(count, 4).astype(np.float32)
        if t in (5, 0xD):
            return a[:, :4].astype(np.float32) / 255.0
        return None

    def _mesh(self, s, vbufs, layout, ibuf):
        first, count = s[10], s[11]
        pos = uv = col = None
        for el in layout:
            buf = vbufs[el['buffer']]
            if el['attr'] == 0 and pos is None:
                v = self._attr(buf, el, first, count)
                pos = None if v is None else v[:, :3]
            elif el['attr'] == 5 and el['layer'] == 0 and uv is None:
                v = self._attr(buf, el, first, count)
                uv = None if v is None or v.shape[1] < 2 else v[:, :2]
            elif el['attr'] == 10 and el['layer'] == 0 and col is None:
                col = self._attr(buf, el, first, count)
        if pos is None:
            return None
        idx = ibuf[s[12]:s[12] + s[13]]
        if s[9] == 4:
            tris = []
            for k in range(len(idx) - 2):
                a, b, c = idx[k], idx[k + 1], idx[k + 2]
                if a == b or b == c or a == c:
                    continue
                tris.append((a, b, c) if k % 2 == 0 else (b, a, c))
            tris = np.array(tris, np.int64).reshape(-1, 3)
        else:
            tris = idx[:len(idx) // 3 * 3].reshape(-1, 3)
        tris = tris - first if tris.size and tris.min() >= first else tris
        tris = tris[(tris >= 0).all(1) & (tris < count).all(1)]
        return {'positions': pos, 'uv': uv, 'colour': col, 'triangles': tris}


def mdlk(data):
    """The G1M files in an MDLK pack ('MDLK0001', u32 count, 'PADD', then the G1Ms one after another)."""
    if data[:8] != b'MDLK0001':
        return []
    n = struct.unpack_from('<I', data, 8)[0]
    o, out = 16, []
    for _ in range(n):
        size = struct.unpack_from('<I', data, o + 8)[0]
        out.append(data[o:o + size])
        o += size
    return out


def container(data):
    """Koei's plain container: u32 count, a u32 size per entry, then each entry from the next 16-byte boundary."""
    n = struct.unpack_from('<I', data, 0)[0]
    sizes = struct.unpack_from(f'<{n}I', data, 4)
    o, out = (4 + 4 * n + 15) & ~15, []
    for s in sizes:
        out.append(data[o:o + s])
        o = (o + s + 15) & ~15
    return out


BCN = {0x59: (1, 8), 0x5B: (3, 16), 0x5C: (4, 8), 0x5D: (5, 16), 0x5E: (6, 16), 0x5F: (7, 16), 0x06: (1, 8), 0x08: (3, 16)}


def g1t(data, wanted=None, max_size=256):
    """{index: PIL RGBA image} for the G1T's textures (those in `wanted`, if given), each the first mip no bigger than `max_size`
    a side (a map's colours need no more)."""
    magic, version, size, table, count, platform, astc = struct.unpack_from('<4s4sIIIII', data, 0)
    assert magic == b'GT1G', magic
    offs = struct.unpack_from(f'<{count}I', data, table)
    out = {}
    for i, rel in enumerate(offs):
        if wanted is not None and i not in wanted:
            continue
        o = table + rel
        mips_sys, fmt, dims, _a, _b, _c, _d, extra = struct.unpack_from('<8B', data, o)
        w, h = 1 << (dims & 15), 1 << (dims >> 4)
        head = 8
        if extra:
            esize = struct.unpack_from('<I', data, o + 8)[0]
            if esize >= 0x10:
                w = struct.unpack_from('<I', data, o + 20)[0]
            if esize >= 0x14:
                h = struct.unpack_from('<I', data, o + 24)[0]
            head += esize
        mips = max(1, mips_sys >> 4)
        p = o + head
        for level in range(mips):
            mw, mh = max(1, w >> level), max(1, h >> level)
            if fmt in BCN:
                n, block = BCN[fmt]
                nbytes = ((mw + 3) // 4) * ((mh + 3) // 4) * block
            elif fmt in (0, 1):
                nbytes = mw * mh * 4
            else:
                break
            if max(mw, mh) <= max_size or level == mips - 1:
                raw = data[p:p + nbytes]
                try:
                    if fmt in BCN:
                        im = Image.frombytes('RGBA', (mw, mh), raw, 'bcn', BCN[fmt][0])
                    else:
                        im = Image.frombytes('RGBA', (mw, mh), raw)
                        if fmt == 1:
                            r, g, b, a = im.split()
                            im = Image.merge('RGBA', (b, g, r, a))
                except Exception:
                    im = None
                if im is not None:
                    out[i] = im
                break
            p += nbytes
    return out

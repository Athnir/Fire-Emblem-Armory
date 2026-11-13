"""A reader for the 3DS CGFX container (.bcres) as Fire Emblem Awakening stores its battle maps (map/terrain/<key>.bcres.lz).

CGFX: a 0x14-byte header ('CGFX', BOM, header size, revision, file size, block count), then the DATA block: 16 (count, self-relative
offset) pairs, each a DICT (a Patricia tree: 'DICT', size, count, root node, then 16-byte nodes [ref bit, left, right, name offset,
data offset], offsets self-relative). The sections: 0 models (CMDL), 1 textures (TXOB), 2 LUTs, 3 materials, 4 shaders, 5 cameras,
6 lights, 7 fogs, 8 scenes, 9 skeletal animations, 10 material animations, 11 visibility animations, 12-14 camera, light and fog
animations, 15 emitters.

Every pointer in the file is self-relative (a signed 32-bit offset from where it's stored). Read from the files themselves:

- CMDL (type 0x40000012, 0x40000092 skeletal): +0x0c name, +0x30 scale, +0x3c rotation, +0x48 translation, +0x54 local and +0x84
  world matrices (3x4), +0xb4 mesh count and list, +0xbc material count and DICT, +0xc4 shape count and list, +0xcc mesh node
  visibility DICT.
- Mesh (SOBJ, type 0x01000000): +0x18 shape index, +0x1c material index, +0x24 visible.
- Shape (SOBJ, type 0x10000001): +0x1c bounding box, +0x20 position offset (3 floats), +0x2c sub-mesh count and list, +0x38 vertex
  buffer count and list.  Sub-mesh: +0 bone indices (count, list), +8 skinning, +0x0c faces (count, list).  Face: +0 face descriptors
  (count, list).  Face descriptor: +0 index format (0x1401 u8, 0x1403 u16), +4 primitive mode (byte: 0 triangles, 1 strip, 2 fan),
  +8 index bytes (count, offset).
- Vertex buffer: type 0x40000002 interleaved (+0x14 bytes (count, offset), +0x24 stride, +0x28 attributes (count, list)), each
  attribute type 0x40000001 (+4 name: 0 position, 1 normal, 2 tangent, 3 colour, 4-6 UV sets 0-2, 7 bone index, 8 bone weight;
  +0x24 GL type 0x1400 s8, 0x1401 u8, 0x1402 s16, 0x1406 float; +0x28 elements; +0x2c scale; +0x30 offset in the vertex);
  type 0x40000001 alone: a separate stream; type 0x80000000: a fixed value (+4 name, +0x0c GL type, +0x10 elements, +0x14 scale (0: 1),
  +0x18 values (count, offset)).
- TXOB image texture (type 0x20000011): +0x18 height, +0x1c width, +0x34 PICA format, +0x38 image (height, width, bytes (count,
  offset)).  TXOB reference (type 0x20000004): +0x18 the texture's name (a path to look up in the file's textures).
- MTOB material (type 0x08000000): +0x18 flags, +0x24 colours (11 RGBA floats: emission, ambient, diffuse, specular 0 and 1,
  constants 0-5; then the same 11 as RGBA bytes at +0xd4), +0x104 rasterisation (+0x108 culling, +0x110 its command), +0x118
  fragment operations (depth, blend at +0x12c with its commands at +0x140, stencil), +0x168 texture coordinate count, +0x16c three
  texture coordinators (88 bytes: source UV set, mapping, reference camera, transform type, scale (2), rotation, translation (2),
  flags, 3x4 matrix), +0x274 three texture mappers (TMAP: +8 the TXOB reference, +0x0c the sampler, +0x10 the unit's PICA commands
  (wrap modes)), +0x284 the shader reference, +0x288 the fragment shader: +0x00 the buffer colour (RGBA float), +0x10 fragment
  lighting, +0x2c six combiner stages of 7 words each (the material constant the stage uses, then the PICA command writing its
  five registers), then the alpha test, buffer colour and buffer update commands.
- CFLT fragment light (type 0x400000a2): +0xbc ambient, +0xcc diffuse, +0xdc / +0xec speculars (RGBA floats), +0x10c direction.
"""
import struct

import numpy as np


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def i32(d, o):
    return struct.unpack_from('<i', d, o)[0]


def f32s(d, o, n):
    return struct.unpack_from('<%df' % n, d, o)


def rel(d, o):
    v = i32(d, o)
    return o + v if v else 0


def cstr(d, o):
    if not o:
        return None
    e = d.index(b'\0', o)
    return d[o:e].decode('ascii', 'replace')


def dict_entries(d, o):
    """[(name, data offset)] of a DICT."""
    if not o:
        return []
    assert d[o:o + 4] == b'DICT', d[o:o + 4]
    n = u32(d, o + 8)
    out = []
    for i in range(n):
        e = o + 0x1c + i * 16
        out.append((cstr(d, rel(d, e + 8)), rel(d, e + 12)))
    return out


def ptr_list(d, o):
    """A (count, self-relative offset to a list of self-relative pointers) pair at o."""
    n = u32(d, o)
    lst = rel(d, o + 4)
    return [rel(d, lst + 4 * i) for i in range(n)]


GL_TYPES = {0x1400: (np.int8, 1), 0x1401: (np.uint8, 1), 0x1402: (np.int16, 2), 0x1403: (np.uint16, 2), 0x1406: (np.float32, 4)}


class CGFX:
    SECTIONS = ('models', 'textures', 'luts', 'materials', 'shaders', 'cameras', 'lights', 'fogs', 'scenes', 'skel_anims',
                'mat_anims', 'vis_anims', 'cam_anims', 'light_anims', 'fog_anims', 'emitters')

    def __init__(self, data):
        d = bytes(data)
        assert d[:4] == b'CGFX', d[:4]
        self.d = d
        off = struct.unpack_from('<H', d, 6)[0]
        assert d[off:off + 4] == b'DATA'
        self.sec = {}
        for i, name in enumerate(self.SECTIONS):
            c = u32(d, off + 8 + 8 * i)
            self.sec[name] = dict_entries(d, rel(d, off + 12 + 8 * i)) if c else []

    # ---------------------------------------------------------------------------------------------------------------------
    def textures(self):
        """{name: (width, height, PICA format, data offset, byte count)} of the file's image textures."""
        out = {}
        d = self.d
        for name, o in self.sec['textures']:
            if u32(d, o) != 0x20000011:
                continue
            h, w = u32(d, o + 0x18), u32(d, o + 0x1c)
            fmt = u32(d, o + 0x34)
            im = rel(d, o + 0x38)
            n = u32(d, im + 8)
            data = rel(d, im + 0xc)
            out[name] = (w, h, fmt, data, n)
        return out

    def texture_image(self, name):
        from fe15_bch import decode_texture
        w, h, fmt, data, n = self.textures()[name]
        return decode_texture(self.d[data:data + n], w, h, fmt)

    # ---------------------------------------------------------------------------------------------------------------------
    def model_info(self, m):
        d = self.d
        world = np.array(f32s(d, m + 0x84, 12)).reshape(3, 4)
        return {'name': cstr(d, rel(d, m + 0x0c)), 'type': u32(d, m), 'world': world,
                'meshes': ptr_list(d, m + 0xb4), 'materials': dict_entries(d, rel(d, m + 0xc0)) if u32(d, m + 0xbc) else [],
                'shapes': ptr_list(d, m + 0xc4)}

    def vertex_streams(self, shape, nv=None):
        """{attribute name: N x k float array} of a shape's vertices."""
        d = self.d
        attrs = {}
        fixed = {}
        for vb in ptr_list(d, shape + 0x38):
            t = u32(d, vb)
            if t == 0x40000002:
                n_bytes, raw = u32(d, vb + 0x14), rel(d, vb + 0x18)
                stride = u32(d, vb + 0x24)
                nvert = n_bytes // stride
                buf = np.frombuffer(d, np.uint8, nvert * stride, raw).reshape(nvert, stride)
                for a in ptr_list(d, vb + 0x28):
                    name = u32(d, a + 4)
                    gl, el = u32(d, a + 0x24), u32(d, a + 0x28)
                    scale = f32s(d, a + 0x2c, 1)[0]
                    aoff = u32(d, a + 0x30)
                    dt, sz = GL_TYPES[gl]
                    vals = buf[:, aoff:aoff + sz * el].copy().view(dt).reshape(nvert, el).astype(np.float64) * scale
                    attrs[name] = vals
            elif t == 0x40000001:
                name = u32(d, vb + 4)
                n_bytes, raw = u32(d, vb + 0x14), rel(d, vb + 0x18)
                gl, el = u32(d, vb + 0x24), u32(d, vb + 0x28)
                scale = f32s(d, vb + 0x2c, 1)[0]
                dt, sz = GL_TYPES[gl]
                nvert = n_bytes // (sz * el)
                attrs[name] = np.frombuffer(d, dt, nvert * el, raw).reshape(nvert, el).astype(np.float64) * scale
            elif t == 0x80000000:
                name = u32(d, vb + 4)
                scale = f32s(d, vb + 0x14, 1)[0] or 1.0
                cnt, vo = u32(d, vb + 0x18), rel(d, vb + 0x1c)
                fixed[name] = np.array(f32s(d, vo, cnt)) * scale
        return attrs, fixed

    def shape_triangles(self, shape):
        d = self.d
        tris = []
        for sm in ptr_list(d, shape + 0x2c):
            for face in ptr_list(d, sm + 0x0c):
                for fd in ptr_list(d, face):
                    fmt = u32(d, fd)
                    mode = d[fd + 4]
                    n_bytes, raw = u32(d, fd + 8), rel(d, fd + 0xc)
                    dt, sz = GL_TYPES[fmt]
                    idx = np.frombuffer(d, dt, n_bytes // sz, raw).astype(np.int64)
                    if mode == 0:
                        tris.append(idx[:len(idx) - len(idx) % 3].reshape(-1, 3))
                    elif mode == 1:
                        t = [(idx[j], idx[j + 1], idx[j + 2]) if j % 2 == 0 else (idx[j + 1], idx[j], idx[j + 2])
                             for j in range(len(idx) - 2)]
                        tris.append(np.array(t, np.int64).reshape(-1, 3))
                    else:
                        t = [(idx[0], idx[j], idx[j + 1]) for j in range(1, len(idx) - 1)]
                        tris.append(np.array(t, np.int64).reshape(-1, 3))
        return np.concatenate(tris) if tris else np.zeros((0, 3), np.int64)

    def meshes(self, m):
        """A model's meshes: dicts with name, material (offset, name), shape positions (N x 3, the model's world matrix applied),
        normals, uv0..uv2, colour (N x 4, 0-1), triangles."""
        d = self.d
        info = self.model_info(m)
        W = info['world']
        out = []
        for me in info['meshes']:
            si, mi = u32(d, me + 0x18), u32(d, me + 0x1c)
            visible = d[me + 0x24]
            shape = info['shapes'][si]
            attrs, fixed = self.vertex_streams(shape)
            T = self.shape_triangles(shape)
            pos = attrs.get(0)
            if pos is None:
                continue
            pos = pos[:, :3] + np.array(f32s(d, shape + 0x20, 3))
            nv = len(pos)
            P = pos @ W[:, :3].T + W[:, 3]
            nrm = attrs.get(1)
            if nrm is not None:
                nrm = nrm[:, :3] @ W[:, :3].T
            col = attrs.get(3)
            if col is None and 3 in fixed:
                col = np.tile(fixed[3][:4], (nv, 1))
            mat_name, mat_off = info['materials'][mi] if mi < len(info['materials']) else (None, None)
            out.append({'model': info['name'], 'name': cstr(d, rel(d, me + 0x0c)), 'visible': visible,
                        'material_name': mat_name, 'material_off': mat_off, 'positions': P, 'normals': nrm,
                        'uv0': attrs.get(4), 'uv1': attrs.get(5), 'uv2': attrs.get(6), 'color': col, 'triangles': T,
                        'skinned': 7 in attrs or 8 in attrs})
        return out

    def lights(self):
        d = self.d
        out = []
        for name, o in self.sec['lights']:
            if u32(d, o) & 0xff != 0xa2:
                out.append({'name': name, 'type': u32(d, o)})
                continue
            out.append({'name': name, 'type': u32(d, o), 'ambient': np.array(f32s(d, o + 0xbc, 4)),
                        'diffuse': np.array(f32s(d, o + 0xcc, 4)), 'direction': np.array(f32s(d, o + 0x10c, 3))})
        return out

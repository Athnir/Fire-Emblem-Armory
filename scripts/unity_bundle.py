"""Read Unity asset bundles (UnityFS) without other tools: the bundle (LZ4-compressed blocks), the serialized files inside it, and
their objects through the files' own type trees (Fire Emblem Engage's data, text and map bundles; Unity 2020.3).

    Bundle(data).files                  name -> bytes (the serialized file `CAB-...` and any resource files)
    SerializedFile(data).objects        each object: path id, class id, its type tree, its bytes
    SerializedFile(data).read(obj)      the object as a dict, by its type tree (TextAsset: m_Name, m_Script; MonoBehaviour: ...)
    assets(data)                        every object of a bundle, read: [(class id, dict)]
"""
import struct

from switch_nsp import lz4_block

# The strings type trees share (offsets with the high bit set point here): Unity's own list, in its order.
COMMON = ('AABB AnimationClip AnimationCurve AnimationState Array Base BitField bitset bool char ColorRGBA Component data deque '
          'double dynamic_array FastPropertyName first float Font GameObject Generic_Mono GradientNEW GUID GUIStyle int list '
          'long_long map Matrix4x4f MdFour MonoBehaviour MonoScript m_ByteSize m_Curve m_EditorClassIdentifier m_EditorHideFlags '
          'm_Enabled m_ExtensionPtr m_GameObject m_Index m_IsArray m_IsStatic m_MetaFlag m_Name m_ObjectHideFlags m_PrefabInternal '
          'm_PrefabParentObject m_Script m_StaticEditorFlags m_Type m_Version Object pair PPtr<Component> PPtr<GameObject> '
          'PPtr<Material> PPtr<MonoBehaviour> PPtr<MonoScript> PPtr<Object> PPtr<Prefab> PPtr<Sprite> PPtr<TextAsset> '
          'PPtr<Texture> PPtr<Texture2D> PPtr<Transform> Prefab Quaternionf Rectf RectInt RectOffset second set short size SInt16 '
          'SInt32 SInt64 SInt8 staticvector string TextAsset TextMesh Texture Texture2D Transform TypelessData UInt16 UInt32 UInt64 '
          'UInt8 unsigned_int unsigned_long_long unsigned_short vector Vector2f Vector3f Vector4f m_ScriptingClassIdentifier '
          'Gradient Type* int2_storage int3_storage BoundsInt m_CorrespondingSourceObject m_PrefabInstance m_PrefabAsset FileSize '
          'Hash128').split()
COMMON_AT = {}
_at = 0
for _s in COMMON:
    COMMON_AT[_at] = _s.replace('_', ' ') if _s in ('Generic_Mono', 'long_long', 'unsigned_int', 'unsigned_long_long',
                                                    'unsigned_short') else _s
    _at += len(_s) + 1
del _at, _s

TEXT_ASSET, MONO_BEHAVIOUR = 49, 114


class Reader:
    def __init__(self, data, pos=0, endian='>'):
        self.d, self.p, self.e = data, pos, endian

    def take(self, fmt):
        v = struct.unpack_from(self.e + fmt, self.d, self.p)
        self.p += struct.calcsize(self.e + fmt)
        return v if len(v) > 1 else v[0]

    def bytes(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v

    def cstr(self):
        end = self.d.index(b'\0', self.p)
        v = self.d[self.p:end].decode('utf-8')
        self.p = end + 1
        return v

    def align(self, n=4):
        self.p = (self.p + n - 1) // n * n


def _decompress(data, flags, size):
    kind = flags & 0x3F
    if kind == 0:
        return data
    assert kind in (2, 3), f'compression {kind}'
    return lz4_block(data, size)


class Bundle:
    """A UnityFS bundle: its files (serialized files and resources) by name."""

    def __init__(self, data):
        r = Reader(data)
        assert r.cstr() == 'UnityFS'
        version = r.take('I')
        r.cstr(), r.cstr()
        _total, packed, size, flags = r.take('QIII')
        if version >= 7:
            r.align(16)
        assert not flags & 0x80, 'blocks info at the end'
        info = Reader(_decompress(r.bytes(packed), flags, size))
        r_data = r.p
        if flags & 0x200:
            r_data = (r_data + 15) // 16 * 16
        info.bytes(16)
        blocks = [info.take('IIH') for _ in range(info.take('i'))]
        nodes = []
        for _ in range(info.take('i')):
            off, n, _flags = info.take('QQI')
            nodes.append((info.cstr(), off, n))
        stream, p = bytearray(), r_data
        for usize, csize, bflags in blocks:
            stream += _decompress(data[p:p + csize], bflags, usize)
            p += csize
        self.files = {name: bytes(stream[off:off + n]) for name, off, n in nodes}


class SerializedFile:
    """A serialized file: its types (with type trees) and objects."""

    def __init__(self, data):
        self.data = data
        r = Reader(data)
        _meta, _fsize, self.version, data_offset = r.take('IIII')
        assert self.version >= 22, self.version
        endian = r.take('B')
        r.bytes(3)
        _meta, _fsize, data_offset, _ = r.take('IQQQ')
        r.e = '<' if endian == 0 else '>'
        self.unity = r.cstr()
        r.take('i')
        self.type_trees = r.take('?')
        self.types = [self._type(r, False) for _ in range(r.take('i'))]
        self.objects = []
        for _ in range(r.take('i')):
            r.align(4)
            path_id, start, size, type_id = r.take('qQIi')
            t = self.types[type_id]
            self.objects.append({'path_id': path_id, 'class_id': t['class_id'], 'type': t, 'start': data_offset + start,
                                 'size': size})
        self.endian = r.e

    def _type(self, r, ref):
        t = {'class_id': r.take('i')}
        r.take('?')
        script_index = r.take('h')
        if (ref and script_index >= 0) or t['class_id'] == MONO_BEHAVIOUR:
            r.bytes(16)
        r.bytes(16)
        if self.type_trees:
            t['nodes'] = self._tree(r)
            if ref:
                r.cstr(), r.cstr(), r.cstr()
            else:
                n = r.take('i')
                r.bytes(4 * n)
        return t

    @staticmethod
    def _tree(r):
        count, strings = r.take('ii')
        raw = [r.take('HBBIIiiiQ') for _ in range(count)]
        buf = r.bytes(strings)

        def name(off):
            if off & 0x80000000:
                return COMMON_AT[off & 0x7FFFFFFF]
            return buf[off:buf.index(b'\0', off)].decode('utf-8')
        return [{'level': lv, 'array': bool(flags & 1), 'type': name(t), 'name': name(n), 'size': size, 'meta': meta}
                for _v, lv, flags, t, n, size, _i, meta, _h in raw]

    def read(self, obj):
        nodes = obj['type']['nodes']
        r = Reader(self.data, obj['start'], self.endian)
        value, _ = self._value(r, nodes, 0)
        return value

    def _children(self, nodes, i):
        level, out, k = nodes[i]['level'], [], i + 1
        while k < len(nodes) and nodes[k]['level'] > level:
            if nodes[k]['level'] == level + 1:
                out.append(k)
            k += 1
        return out, k

    PRIMITIVE = {'SInt8': 'b', 'UInt8': 'B', 'char': 'B', 'bool': '?', 'SInt16': 'h', 'short': 'h', 'UInt16': 'H',
                 'unsigned short': 'H', 'SInt32': 'i', 'int': 'i', 'UInt32': 'I', 'unsigned int': 'I', 'Type*': 'I',
                 'SInt64': 'q', 'long long': 'q', 'UInt64': 'Q', 'unsigned long long': 'Q', 'FileSize': 'Q', 'float': 'f',
                 'double': 'd'}

    def _value(self, r, nodes, i):
        """The value of node i (read from r), and the index after its subtree."""
        node = nodes[i]
        kids, end = self._children(nodes, i)
        t = node['type']
        if t in self.PRIMITIVE:
            v = r.take(self.PRIMITIVE[t])
        elif t == 'string':
            n = r.take('i')
            raw = r.bytes(n)
            try:
                v = raw.decode('utf-8')
            except UnicodeDecodeError:
                v = raw
            if nodes[kids[0]]['meta'] & 0x4000 or True:
                r.align(4)
        elif node['array'] or (kids and nodes[kids[0]]['array']):
            arr = i if node['array'] else kids[0]
            akids, _ = self._children(nodes, arr)
            n = r.take('i')
            elem = akids[1]
            et = nodes[elem]['type']
            if et in ('UInt8', 'char', 'SInt8') and not self._children(nodes, elem)[0]:
                v = r.bytes(n)
            elif et in self.PRIMITIVE and not self._children(nodes, elem)[0]:
                v = list(struct.unpack_from(f'{self.endian}{n}{self.PRIMITIVE[et]}', r.d, r.p))
                r.p += n * struct.calcsize(self.PRIMITIVE[et])
            else:
                v = [self._value(r, nodes, elem)[0] for _ in range(n)]
            if nodes[arr]['meta'] & 0x4000:
                r.align(4)
        elif t == 'TypelessData':
            v = r.bytes(r.take('i'))
        else:
            v = {}
            for k in kids:
                v[nodes[k]['name']], _ = self._value(r, nodes, k)
        if node['meta'] & 0x4000:
            r.align(4)
        return v, end


def assets(data):
    """Every object in a bundle's serialized files, read: [(class id, value)]."""
    out = []
    for name, blob in Bundle(data).files.items():
        if name.endswith('.resS') or name.endswith('.resource'):
            continue
        sf = SerializedFile(blob)
        for obj in sf.objects:
            out.append((obj['class_id'], sf.read(obj)))
    return out

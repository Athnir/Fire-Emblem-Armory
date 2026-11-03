"""Read a Unity IL2CPP game's names: its metadata (global-metadata.dat, version 27: Unity 2020.2-2020.3) gives every type, method and
field by name, and each enum's constants; the program (an NSO image, relocated to 0) holds each method's code, found through the
code generation module of its assembly. Fire Emblem Engage's: data-raw/fe17/romfs.

    meta = Metadata(open('global-metadata.dat', 'rb').read())
    meta.types                       [{'name', 'namespace', 'full', 'image', 'methods': [...], 'fields': [...], ...}]
    meta.type('App.ItemData')        one by its full name ('App.ItemData.FlagEnum' for a nested one)
    meta.enum('App.ItemData.FlagEnum')   {constant name: value}
    meta.addresses(image)            {'App.ItemData$$GetName': code offset, ...}: each method's code, by type and name
"""
import struct

SANITY = 0xFAB11BAF
SECTIONS = ['stringLiteral', 'stringLiteralData', 'string', 'events', 'properties', 'methods', 'parameterDefaultValues',
            'fieldDefaultValues', 'fieldAndParameterDefaultValueData', 'fieldMarshaledSizes', 'parameters', 'fields',
            'genericParameters', 'genericParameterConstraints', 'genericContainers', 'nestedTypes', 'interfaces', 'vtableMethods',
            'interfaceOffsets', 'typeDefinitions', 'images', 'assemblies', 'fieldRefs', 'referencedAssemblies', 'attributesInfo',
            'attributeTypes', 'unresolvedVirtualCallParameterTypes', 'unresolvedVirtualCallParameterRanges',
            'windowsRuntimeTypeNames', 'windowsRuntimeStrings', 'exportedTypeDefinitions']
# Version 27's records.
TYPE_DEF = struct.Struct('<IIiiiiiIiiiiiiii8HII')       # 88 bytes
METHOD_DEF = struct.Struct('<IiiiiIHHHH')              # 32
FIELD_DEF = struct.Struct('<IiI')                      # 12
FIELD_DEFAULT = struct.Struct('<iii')                  # 12
IMAGE_DEF = struct.Struct('<IiiIiIiIiI')               # 40
NESTED = struct.Struct('<i')


class Metadata:
    def __init__(self, data):
        self.d = data
        sanity, self.version = struct.unpack_from('<Ii', data, 0)
        assert sanity == SANITY and self.version == 27, (hex(sanity), self.version)
        values = struct.unpack_from('<' + 'Ii' * len(SECTIONS), data, 8)
        self.sec = {n: (values[2 * k], values[2 * k + 1]) for k, n in enumerate(SECTIONS)}
        self.images = [self._image(r) for r in self._records('images', IMAGE_DEF)]
        self.fields = [{'name': self.string(n), 'type_index': t, 'token': tok} for n, t, tok in self._records('fields', FIELD_DEF)]
        self.methods = [{'name': self.string(r[0]), 'declaring': r[1], 'token': r[5], 'flags': r[6], 'params': r[9]}
                        for r in self._records('methods', METHOD_DEF)]
        nested = [r[0] for r in self._records('nestedTypes', NESTED)]
        self.types = []
        for k, r in enumerate(self._records('typeDefinitions', TYPE_DEF)):
            (name, ns, _byval, declaring, parent, _element, _generic, flags, field_start, method_start, _event, _prop, nested_start,
             _iface, _vtable, _ioff, method_count, _pc, field_count, _ec, nested_count, _vc, _ic, _ioc, bitfield, token) = r
            self.types.append({'index': k, 'name': self.string(name), 'namespace': self.string(ns), 'declaring': declaring,
                               'parent': parent, 'flags': flags, 'token': token, 'bitfield': bitfield,
                               'fields': list(range(field_start, field_start + field_count)) if field_start >= 0 else [],
                               'methods': list(range(method_start, method_start + method_count)) if method_start >= 0 else [],
                               'nested': nested[nested_start:nested_start + nested_count] if nested_start >= 0 else []})
        for img_index, img in enumerate(self.images):
            for t in range(img['type_start'], img['type_start'] + img['type_count']):
                self.types[t]['image'] = img['name']
        # A nested type's outer type: from the outer types' nested lists (declaringTypeIndex counts the program's type table).
        for t in self.types:
            t['outer'] = None
        for t in self.types:
            for n in t['nested']:
                self.types[n]['outer'] = t['index']
        for t in self.types:
            t['full'] = self._full(t)
        self.by_full = {}
        for t in self.types:
            self.by_full.setdefault(t['full'], t)
        defaults = {}
        data_off = self.sec['fieldAndParameterDefaultValueData'][0]
        for field, type_index, data_index in self._records('fieldDefaultValues', FIELD_DEFAULT):
            defaults[field] = data_off + data_index
        self.defaults = defaults

    def _records(self, section, st):
        off, size = self.sec[section]
        assert size % st.size == 0, (section, size, st.size)
        return [st.unpack_from(self.d, off + k * st.size) for k in range(size // st.size)]

    def _image(self, r):
        name, assembly, type_start, type_count, _ets, _etc, _entry, token, _cas, _cac = r
        return {'name': self.string(name), 'type_start': type_start, 'type_count': type_count, 'token': token}

    def string(self, index):
        off = self.sec['string'][0] + index
        return self.d[off:self.d.index(b'\0', off)].decode('utf-8')

    def _full(self, t):
        if t['outer'] is not None:
            return self._full(self.types[t['outer']]) + '.' + t['name']
        return (t['namespace'] + '.' if t['namespace'] else '') + t['name']

    def type(self, full):
        return self.by_full[full]

    def field_names(self, t):
        return [self.fields[f]['name'] for f in t['fields']]

    def enum(self, full, size=None):
        """An enum's constants: {name: value}. Each constant's value is in the default value data, as wide as the enum's
        underlying type: taken from the gap between consecutive constants unless `size` is given (4 when there's one)."""
        t = self.type(full)
        consts = [(self.fields[f]['name'], self.defaults[f]) for f in t['fields'] if f in self.defaults]
        if size is None:
            gaps = {b[1] - a[1] for a, b in zip(consts, consts[1:])}
            size = min(gaps) if gaps else 4
        fmt = {1: '<B', 2: '<h', 4: '<i', 8: '<q'}[size]
        return {name: struct.unpack_from(fmt, self.d, off)[0] for name, off in consts}

    def addresses(self, image_bytes, image_name):
        """{'Namespace.Type$$Method': code offset} for every method of one assembly (`image_name`, 'App.dll'), from its code
        generation module in the program: the module's record starts with a pointer to its name, then its method count and the
        pointer to its method pointers, indexed by each method's token's row number less one."""
        name = image_name.encode() + b'\0'
        at = 0
        hits = []
        while True:
            at = image_bytes.find(name, at)
            if at < 0:
                break
            if at == 0 or image_bytes[at - 1] == 0:
                hits.append(at)
            at += 1
        img = next(i for i in self.images if i['name'] == image_name)
        methods = [m for t in range(img['type_start'], img['type_start'] + img['type_count']) for m in self.types[t]['methods']]
        expect = max((self.methods[m]['token'] & 0xFFFFFF) for m in methods)
        for s in hits:
            ptr = struct.pack('<Q', s)
            p = 0
            while True:
                p = image_bytes.find(ptr, p)
                if p < 0:
                    break
                count, table = struct.unpack_from('<IxxxxQ', image_bytes, p + 8)
                if count == expect and 0 < table < len(image_bytes):
                    pointers = struct.unpack_from(f'<{count}Q', image_bytes, table)
                    out = {}
                    for m in methods:
                        md = self.methods[m]
                        key = f"{self.types[md['declaring']]['full']}$${md['name']}"
                        addr = pointers[(md['token'] & 0xFFFFFF) - 1]
                        if addr:
                            out.setdefault(key, addr)
                            out.setdefault(f"{key}#{md['token'] & 0xFFFFFF}", addr)
                    return out
                p += 8
        raise LookupError(f'no code generation module for {image_name}')

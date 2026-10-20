"""
Read Path of Radiance's chapter scripts (Scripts/Cnn.cmb). The format is an older version of Fates'
(see fates_cmb.py): little-endian header, big-endian bytecode for a small stack machine.

Header: 'cmb\\0', the file name, then at 0x24 the string table offset and at 0x28 the handler table
(offsets, 0-terminated). Each handler: name offset, code offset, 0, then u16 trigger kind, u16 argument
count (u8) and a u8 we don't need, u16 index, u16 flags, then the trigger's u16 arguments; the code
follows.
"""
import os
import struct

from fe9_files import FE9

OPS = {
    0x01: ('var', 1), 0x02: ('var', 2), 0x03: ('index', 1), 0x04: ('var', 2), 0x05: ('var', 1), 0x06: ('var', 2),
    0x07: ('load', 1), 0x08: ('load', 2), 0x09: ('load', 1), 0x0A: ('load', 2), 0x0B: ('ref', 1), 0x0C: ('ref', 2),
    0x0D: ('ref', 1), 0x0E: ('ref', 2), 0x0F: ('ref', 1), 0x10: ('ref', 2), 0x11: ('ref', 1), 0x12: ('ref', 2),
    0x13: ('ref', 1), 0x14: ('ref', 2), 0x15: ('ref', 1), 0x16: ('ref', 2), 0x17: ('ref', 1), 0x18: ('ref', 2),
    0x19: ('int', 1), 0x1A: ('int', 2), 0x1B: ('int', 4), 0x1C: ('str', 1), 0x1D: ('str', 2), 0x1E: ('str', 3),
    0x1F: ('deref', 0), 0x20: ('pop', 0),
    0x38: ('call', 3), 0x39: ('ret', 0), 0x3A: ('jmp', 2), 0x3B: ('jnz', 2), 0x3C: ('orjump', 2), 0x3D: ('jz', 2),
    0x3E: ('andjump', 2),
    # 0x37 marks a statement (its operand looks like a line counter); 0x41 formats a debug string.
    0x37: ('stmt', 1), 0x41: ('format', 1),
}
for _op in range(0x21, 0x38):
    OPS.setdefault(_op, (f'op{_op:02x}', 0))


class Script:
    def __init__(self, name):
        d = self.d = open(os.path.join(FE9, 'Scripts', name), 'rb').read()
        assert d[:4] == b'cmb\0', name
        self.strings = struct.unpack_from('<I', d, 0x24)[0]
        o = struct.unpack_from('<I', d, 0x28)[0]
        self.offs = []
        while True:
            v = struct.unpack_from('<I', d, o)[0]
            if v == 0:
                break
            self.offs.append(v)
            o += 4
        self.table = o

    def string(self, off):
        o = self.strings + off
        try:
            return self.d[o:self.d.index(b'\0', o)].decode('shift_jis', 'replace')
        except ValueError:
            return f'<bad {o:x}>'

    def handlers(self):
        out = []
        for i, f in enumerate(self.offs):
            name, code = struct.unpack_from('<2I', self.d, f)
            kind, argc, extra, index, flags = struct.unpack_from('<H2B2H', self.d, f + 12)
            args = struct.unpack_from(f'<{argc}H', self.d, f + 20) if argc and f + 20 + 2 * argc <= code else ()
            end = self.offs[i + 1] if i + 1 < len(self.offs) else self.table
            label = self.d[name:self.d.index(b'\0', name)].decode('shift_jis', 'replace') if name else ''
            out.append({'i': i, 'name': label, 'kind': kind, 'extra': extra, 'index': index, 'flags': flags, 'args': args,
                        'code': code, 'end': end})
        return out

    def disasm(self, h):
        d = self.d
        pc = h['code']
        out = []
        furthest = pc
        while pc < h['end']:
            op = d[pc]
            name, n = OPS.get(op, (f'?{op:02x}', 0))
            raw = d[pc + 1:pc + 1 + n]
            if name == 'str':
                arg = self.string(int.from_bytes(raw, 'big'))
            elif name == 'call':
                arg = f"{self.string(int.from_bytes(raw[:2], 'big'))}/{raw[2]}"
            elif name == 'int':
                arg = int.from_bytes(raw, 'big', signed=True)
            elif name in ('jmp', 'jz', 'jnz', 'orjump', 'andjump'):
                arg = pc + 1 + int.from_bytes(raw, 'big', signed=True)
            else:
                arg = raw.hex()
            out.append((pc, name, arg))
            if name in ('jmp', 'jz', 'jnz', 'orjump', 'andjump'):
                furthest = max(furthest, arg)
            pc += 1 + n
            # The code ends at the last return no jump goes past (what follows is padding and labels).
            if name == 'ret' and pc > furthest:
                break
        return out

"""
Read Fire Emblem Fates chapter scripts (Scripts/**/*.cmb): each event handler's trigger and a rough
disassembly of its bytecode (a small stack machine). Only as much of the instruction set as the map
tools need is decoded; unknown opcodes are shown as raw bytes.
"""
import struct
import sys

# opcode -> (mnemonic, operand bytes)
OPS = {
    0x01: ('var', 1), 0x02: ('var', 2), 0x03: ('index', 1), 0x04: ('var', 2), 0x05: ('var', 1), 0x06: ('var', 2),
    0x07: ('load', 1), 0x08: ('load', 2), 0x09: ('load', 1), 0x0A: ('load', 2), 0x0B: ('ref', 1), 0x0C: ('ref', 2),
    0x0D: ('ref', 1), 0x0E: ('ref', 2), 0x0F: ('ref', 1), 0x10: ('ref', 2), 0x11: ('ref', 1), 0x12: ('ref', 2),
    0x13: ('ref', 1), 0x14: ('ref', 2), 0x15: ('ref', 1), 0x16: ('ref', 2), 0x17: ('ref', 1), 0x18: ('ref', 2),
    0x19: ('int', 1), 0x1A: ('int', 2), 0x1B: ('int', 4), 0x1C: ('str', 1), 0x1D: ('str', 2), 0x1E: ('str', 3),
    0x1F: ('float', 4), 0x20: ('deref', 0), 0x21: ('pop', 0), 0x22: ('?22', 0), 0x23: ('assign', 0),
    0x24: ('?24', 0), 0x25: ('?25', 0), 0x26: ('add', 0), 0x27: ('?27', 0), 0x28: ('sub', 0), 0x29: ('?29', 0),
    0x2A: ('mul', 0), 0x2B: ('?2b', 0), 0x2C: ('div', 0), 0x2D: ('?2d', 0), 0x2E: ('mod', 0), 0x2F: ('?2f', 0),
    0x30: ('?30', 0), 0x31: ('?31', 0), 0x32: ('?32', 0), 0x33: ('?33', 0), 0x34: ('?34', 0), 0x35: ('?35', 0),
    0x36: ('?36', 0), 0x37: ('?37', 0),
    # Comparisons: int / float pairs, with string versions of == and != (0x3a, 0x3d).
    0x38: ('eq', 0), 0x39: ('feq', 0), 0x3A: ('seq', 0), 0x3B: ('ne', 0), 0x3C: ('fne', 0), 0x3D: ('sne', 0),
    0x3E: ('lt', 0), 0x3F: ('flt', 0), 0x40: ('le', 0), 0x41: ('fle', 0), 0x42: ('gt', 0), 0x43: ('fgt', 0),
    0x44: ('ge', 0), 0x45: ('fge', 0), 0x46: ('gvar', 1),
    0x47: ('call', 3), 0x48: ('callid', 2), 0x49: ('jmp', 2), 0x4A: ('jnz', 2), 0x4B: ('orjump', 2), 0x4C: ('jz', 2),
    0x4D: ('andjump', 2), 0x4E: ('?4e', 2), 0x4F: ('?4f', 2), 0x50: ('?50', 0), 0x51: ('?51', 0), 0x52: ('?52', 0),
    0x53: ('dup', 0), 0x54: ('ret', 0), 0x55: ('?55', 0), 0x56: ('?56', 0),
}


class Script:
    def __init__(self, path):
        d = self.d = open(path, 'rb').read()
        assert d[:4] == b'cmb\0', path
        self.strtab = struct.unpack_from('<I', d, 0x20)[0]
        # The handler table follows the file's name; its offset is in the header.
        o, self.offs = struct.unpack_from('<I', d, 0x1C)[0], []
        while True:
            v = struct.unpack_from('<I', d, o)[0]
            if v == 0:
                break
            self.offs.append(v)
            o += 4

    def string(self, off):
        o = self.strtab + off
        return self.d[o:self.d.index(b'\0', o)].decode('shift_jis', 'replace')

    def handlers(self):
        out = []
        for i, f in enumerate(self.offs):
            self_off, code, kind, idx, _, argp = struct.unpack_from('<6I', self.d, f)
            nargs = (code - argp) // 4 if argp and code > argp else 0
            args = struct.unpack_from(f'<{nargs}i', self.d, argp) if nargs else ()
            end = self.offs[i + 1] if i + 1 < len(self.offs) else self.strtab
            out.append({'index': idx, 'kind': kind, 'args': args, 'code': (code, end)})
        return out

    def disasm(self, handler):
        d = self.d
        pc, end = handler['code']
        out = []
        while pc < end:
            op = d[pc]
            name, n = OPS.get(op, (f'?{op:02x}', 0))
            raw = d[pc + 1:pc + 1 + n]
            if name == 'str':
                arg = repr(self.string(int.from_bytes(raw, 'big')))
            elif name == 'call':
                arg = f'{self.string(int.from_bytes(raw[:2], "big"))}/{raw[2]}'
            elif name == 'int':
                arg = int.from_bytes(raw, 'big', signed=True)
            elif name in ('jmp', 'jz', 'jnz', 'orjump', 'andjump'):
                arg = pc + 1 + int.from_bytes(raw, 'big', signed=True)
            else:
                arg = raw.hex()
            out.append((pc, name, arg))
            pc += 1 + n
            if name == 'ret' and pc >= end - 4:
                break
        return out


if __name__ == '__main__':
    s = Script(sys.argv[1])
    for h in s.handlers():
        print(f"== handler {h['index']} kind {h['kind']:#x} args {h['args']}")
        for pc, name, arg in s.disasm(h):
            print(f'   {pc:04x} {name} {arg}')

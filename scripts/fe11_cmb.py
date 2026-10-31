"""
Read Shadow Dragon's scripts (script/*.cmb): an older version (dated 2006-10-24) of the bytecode Fates' and Awakening's scripts use,
with its own header and opcode numbers. Worked out from the scripts themselves: the shapes repeat across every chapter.

Header: 'cmb\\0' and the file's name; +0x24 the string table's offset, +0x28 the handler table's (offsets, ending in 0). A handler:
+0 its name's offset (0: none), +4 its code, +0x10 u16 kind with a u16 count after, then its arguments (u16 each; a terrain script's
tile handlers take x, y and the tile's kind: 0x08 a village, 0x09 a house, 0x0a an armory, 0x0b a vendor...).

Opcodes (a stack machine): 0x19 / 0x1a / 0x1b push a 1 / 2 / 4-byte number (big-endian), 0x1c / 0x1d push a string (its 1 / 2-byte
offset in the string table), 0x38 call (a 2-byte name offset, then the argument count), 0x20 discard, 0x01 / 0x02 push a local /
argument, 0x07 / 0x0a push a local's / global's address, 0x47 assign, 0x29 not, 0x22-0x32 comparisons and arithmetic, 0x3a jump,
0x3c / 0x3d / 0x3e conditional jumps (2-byte relative offsets), 0x39 return, 0x45 the handler's end.
"""
import struct

WIDTH = {0x19: 1, 0x1a: 2, 0x1b: 4, 0x1c: 1, 0x1d: 2, 0x38: 3, 0x20: 0, 0x39: 0, 0x01: 1, 0x02: 1, 0x07: 1, 0x0a: 1, 0x47: 0,
         0x29: 0, 0x22: 0, 0x23: 0, 0x25: 0, 0x27: 0, 0x2f: 0, 0x30: 0, 0x31: 0, 0x32: 0, 0x37: 1, 0x3a: 2, 0x3c: 2, 0x3d: 2,
         0x3e: 2, 0x3f: 0, 0x42: 0, 0x46: 0, 0x09: 1}
NAMES = {0x19: 'int', 0x1a: 'int', 0x1b: 'int', 0x1c: 'str', 0x1d: 'str', 0x38: 'call', 0x20: 'pop', 0x39: 'ret', 0x01: 'local',
         0x02: 'arg', 0x07: 'addr', 0x0a: 'gaddr', 0x47: 'assign', 0x29: 'not', 0x3a: 'jmp', 0x3c: 'jcc', 0x3d: 'jz', 0x3e: 'jnz',
         0x45: 'end'}


class Script:
    def __init__(self, path):
        d = self.d = open(path, 'rb').read()
        assert d[:4] == b'cmb\0', path
        self.strtab, ht = struct.unpack_from('<II', d, 0x24)
        self.offs = []
        while True:
            v = struct.unpack_from('<I', d, ht)[0]
            if not v:
                break
            self.offs.append(v)
            ht += 4

    def string(self, off):
        o = self.strtab + off
        return self.d[o:self.d.index(b'\0', o)].decode('shift_jis', 'replace')

    def cstr(self, o):
        return self.d[o:self.d.index(b'\0', o)].decode('shift_jis', 'replace')

    def handlers(self):
        out = []
        for i, h in enumerate(self.offs):
            name, code = struct.unpack_from('<II', self.d, h)
            kind, count = struct.unpack_from('<HH', self.d, h + 0x10)
            nargs = (code - (h + 0x14)) // 2
            args = struct.unpack_from(f'<{nargs}H', self.d, h + 0x14) if nargs > 0 else ()
            end = self.offs[i + 1] if i + 1 < len(self.offs) else len(self.d)
            out.append({'index': i, 'name': self.cstr(name) if name else '', 'kind': kind, 'count': count, 'args': args,
                        'code': (code, end)})
        return out

    def disasm(self, h):
        """[(pc, mnemonic, value)] up to the handler's end."""
        d, (pc, end), out = self.d, h['code'], []
        while pc < end:
            op = d[pc]
            if op == 0x45 or op not in WIDTH:
                break
            n = WIDTH[op]
            raw = d[pc + 1:pc + 1 + n]
            name = NAMES.get(op, f'op{op:02x}')
            if op in (0x19, 0x1a, 0x1b):
                val = int.from_bytes(raw, 'big', signed=op != 0x19)
            elif op in (0x1c, 0x1d):
                val = self.string(int.from_bytes(raw, 'big'))
            elif op == 0x38:
                val = (self.string(int.from_bytes(raw[:2], 'big')), raw[2])
            elif op in (0x3a, 0x3c, 0x3d, 0x3e):
                val = pc + 3 + int.from_bytes(raw, 'big', signed=True)
            else:
                val = int.from_bytes(raw, 'big') if n else None
            out.append((pc, name, val))
            pc += 1 + n
        return out

    def calls(self, h):
        """[(function, [arguments])] in order, each argument the literal pushed for it (None where it isn't a literal)."""
        out, stack = [], []
        for _, name, val in self.disasm(h):
            if name in ('int', 'str'):
                stack.append(val)
            elif name == 'call':
                fn, argc = val
                args = stack[-argc:] if argc else []
                del stack[len(stack) - argc:]
                out.append((fn, args))
                stack.append(None)
            elif name == 'pop':
                if stack:
                    stack.pop()
            elif name in ('local', 'arg', 'addr', 'gaddr'):
                stack.append(None)
            elif name in ('assign',):
                del stack[-2:]
            elif name in ('jz', 'jnz', 'jcc'):
                if stack:
                    stack.pop()
            elif name.startswith('op') or name == 'not':
                # Comparisons and arithmetic take two values and leave one; 'not' one for one.
                if name != 'not' and len(stack) >= 2:
                    stack.pop()
                if stack:
                    stack[-1] = None
        return out

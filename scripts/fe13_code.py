"""Helpers for reading Awakening's program (data-raw/fe13/romfs/code.bin, loaded at 0x100000): find a class's virtual functions
through its RTTI name, follow references, and disassemble ARM code with capstone. Used to check mechanics in the code."""
import os
import re
import struct

import capstone

CODE = open(os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe13', 'romfs', 'code.bin'), 'rb').read()
BASE = 0x100000
md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
md.detail = False


def u32(addr):
    return struct.unpack_from('<I', CODE, addr - BASE)[0]


def refs(value):
    """Addresses of 4-byte words equal to value (pointers to it)."""
    pat = struct.pack('<I', value)
    return [m.start() + BASE for m in re.finditer(re.escape(pat), CODE) if m.start() % 4 == 0]


def string_addr(s):
    return [m.start() + BASE for m in re.finditer(re.escape(s.encode('shift_jis') + b'\0'), CODE)]


def vtable(mangled):
    """The vtable(s) of the class whose RTTI name is `mangled` ('N8shopMenu10refineMenu9EditPowerE'): lists of function addresses."""
    out = []
    for name in string_addr(mangled):
        for ti_field in refs(name):
            ti = ti_field - 4  # typeinfo: [vtable for the typeinfo class][name][base...]
            for vt_field in refs(ti):
                fns = []
                a = vt_field + 4
                while True:
                    v = u32(a)
                    if not (BASE <= v < BASE + len(CODE)) or v % 4:
                        break
                    fns.append(v)
                    a += 4
                out.append((vt_field, fns))
    return out


def dis(addr, n=60):
    code = CODE[addr - BASE:addr - BASE + 4 * n]
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(code, addr)]


def show(addr, n=60):
    for a, m, o in dis(addr, n):
        extra = ''
        mm = re.search(r'\[pc, #(-?0x[0-9a-f]+|-?\d+)\]', o)
        if mm and m.startswith('ldr'):
            lit = a + 8 + int(mm.group(1), 0)
            extra = f' ; ={u32(lit):#x}'
        print(f'{a:08x}  {m:8} {o}{extra}')


_ALL = None


def all_ins():
    """Every 4-byte word of the program disassembled once (data decodes as junk, which is fine for searching)."""
    global _ALL
    if _ALL is None:
        md.skipdata = True
        _ALL = [(i.address, i.mnemonic, i.op_str) for i in md.disasm(CODE, BASE)]
        md.skipdata = False
    return _ALL


def callers(target):
    t = f'#{target:#x}'
    return [a for a, m, o in all_ins() if m in ('bl', 'blx', 'b') and o == t]


def adr_refs(target):
    """Instructions that form `target` as add/sub rX, pc, #imm."""
    out = []
    for a, m, o in all_ins():
        if m in ('add', 'sub') and ', pc, #' in o and o.count('#') == 1:
            imm = int(o.split('#')[1], 0)
            v = a + 8 + (imm if m == 'add' else -imm)
            if v == target:
                out.append(a)
    return out


def func_start(addr):
    """The nearest `push {..., lr}` at or before addr: where the function holding addr likely begins."""
    a = addr - addr % 4
    while a > BASE:
        for x, m, o in dis(a, 1):
            if m in ('push', 'stmdb') and 'lr' in o:
                return a
        a -= 4
    return None


def literal_users(lit):
    """Instructions that load the literal pool word at `lit` (ldr rX, [pc, #imm])."""
    out = []
    ins = all_ins()
    k0 = (lit - 4096 - BASE) // 4
    for a, m, o in ins[max(k0, 0):(lit - BASE) // 4]:
        if m.startswith('ldr') and '[pc, #' in o:
            imm = int(o.split('#')[1].rstrip(']'), 0)
            if a + 8 + imm == lit:
                out.append(a)
    return out

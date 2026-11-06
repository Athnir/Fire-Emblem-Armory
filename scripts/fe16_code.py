"""Run small routines of Three Houses' program (`data-raw/fe16/romfs/main.bin`, the 1.2.0 update's main NSO decompressed and relocated,
loaded at 0) to read what they compute, where the answer is code rather than a table.

`Arm64` interprets AArch64 code instruction by instruction (decoded with capstone): the integer instructions the routines read here use,
with the program's own bytes as read-only memory under a writable overlay (the stack and whatever the caller sets up). A routine is
run with its arguments in registers; calls to stubbed addresses run Python instead, and an instruction it doesn't know stops it with
an error, so nothing is guessed.

`gambit_area(shape, target, user)` runs the gambit area builder (`0x41e4e0`) for one shape id (fixed_data.bin section 8 +10).
"""
import os
import struct

from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs
from capstone import arm64 as A

MAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe16', 'romfs', 'main.bin')
M64 = (1 << 64) - 1
STACK_TOP = 0x7F000000
RETURN = 0xDEAD0000      # the return address the outermost routine gets: reaching it ends the run

_COND = {
    A.ARM64_CC_EQ: lambda n, z, c, v: z, A.ARM64_CC_NE: lambda n, z, c, v: not z,
    A.ARM64_CC_HS: lambda n, z, c, v: c, A.ARM64_CC_LO: lambda n, z, c, v: not c,
    A.ARM64_CC_MI: lambda n, z, c, v: n, A.ARM64_CC_PL: lambda n, z, c, v: not n,
    A.ARM64_CC_VS: lambda n, z, c, v: v, A.ARM64_CC_VC: lambda n, z, c, v: not v,
    A.ARM64_CC_HI: lambda n, z, c, v: c and not z, A.ARM64_CC_LS: lambda n, z, c, v: not c or z,
    A.ARM64_CC_GE: lambda n, z, c, v: n == v, A.ARM64_CC_LT: lambda n, z, c, v: n != v,
    A.ARM64_CC_GT: lambda n, z, c, v: not z and n == v, A.ARM64_CC_LE: lambda n, z, c, v: z or n != v,
    A.ARM64_CC_AL: lambda n, z, c, v: True,
}


def _signed(x, bits):
    x &= (1 << bits) - 1
    return x - (1 << bits) if x >> (bits - 1) else x


class Arm64:
    def __init__(self, path=MAIN):
        self.rom = open(path, 'rb').read()
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.md.detail = True
        self.cache = {}
        self.stubs = {}
        self.reset()

    def reset(self):
        self.x = [0] * 31
        self.sp = STACK_TOP
        self.flags = (False, False, False, False)
        self.pages = {}

    # Memory: the program's bytes, read-only, under a byte overlay of what the run writes.
    def read(self, a, n):
        out = bytearray()
        for k in range(n):
            b = self.pages.get(a + k)
            if b is None:
                b = self.rom[a + k] if a + k < len(self.rom) else 0
            out.append(b)
        return bytes(out)

    def write(self, a, data):
        for k, b in enumerate(data):
            self.pages[a + k] = b

    def u64(self, a):
        return struct.unpack('<Q', self.read(a, 8))[0]

    def put64(self, a, v):
        self.write(a, struct.pack('<Q', v & M64))

    # Registers by capstone register id.
    def _reg(self, r):
        name = self.md.reg_name(r)
        if name in ('sp', 'wsp'):
            return 'sp', name == 'wsp'
        if name in ('xzr', 'wzr'):
            return 'zr', name == 'wzr'
        name = {'fp': 'x29', 'lr': 'x30'}.get(name, name)
        return int(name[1:]), name[0] == 'w'

    def get(self, r):
        n, w = self._reg(r)
        v = self.sp if n == 'sp' else 0 if n == 'zr' else self.x[n]
        return v & 0xFFFFFFFF if w else v

    def set(self, r, v):
        n, w = self._reg(r)
        v &= 0xFFFFFFFF if w else M64
        if n == 'sp':
            self.sp = v
        elif n != 'zr':
            self.x[n] = v

    def width(self, r):
        return 32 if self._reg(r)[1] else 64

    def _shifted(self, op, v, bits):
        """An operand's value with its shift or extension applied."""
        ext = op.ext
        if ext == A.ARM64_EXT_SXTW:
            v = _signed(v, 32) & M64
        elif ext == A.ARM64_EXT_UXTW:
            v &= 0xFFFFFFFF
        elif ext == A.ARM64_EXT_SXTB:
            v = _signed(v, 8) & M64
        elif ext == A.ARM64_EXT_UXTB:
            v &= 0xFF
        elif ext not in (A.ARM64_EXT_INVALID, A.ARM64_EXT_UXTX, A.ARM64_EXT_SXTX):
            raise NotImplementedError(f'extend {ext}')
        st, sv = op.shift.type, op.shift.value
        mask = (1 << bits) - 1
        if st == A.ARM64_SFT_LSL:
            v = (v << sv) & mask
        elif st == A.ARM64_SFT_LSR:
            v = (v & mask) >> sv
        elif st == A.ARM64_SFT_ASR:
            v = (_signed(v, bits) >> sv) & mask
        elif st != A.ARM64_SFT_INVALID:
            raise NotImplementedError(f'shift {st}')
        return v & mask

    def val(self, op, bits):
        if op.type == A.ARM64_OP_IMM:
            return self._shifted(op, op.imm & M64, bits)
        if op.type == A.ARM64_OP_REG:
            return self._shifted(op, self.get(op.reg), bits)
        raise NotImplementedError(f'operand type {op.type}')

    def _addr(self, insn, op):
        m = op.mem
        a = self.get(m.base)
        if m.index:
            a += self._shifted(op, self.get(m.index), 64)
        return (a + m.disp) & M64

    def _addsub(self, a, b, bits, sub, carry_in=None):
        mask = (1 << bits) - 1
        if sub:
            b = ~b & mask
            carry_in = 1 if carry_in is None else carry_in
        else:
            carry_in = 0 if carry_in is None else carry_in
        full = a + b + carry_in
        r = full & mask
        n = bool(r >> (bits - 1))
        z = r == 0
        c = full > mask
        v = (_signed(a, bits) + _signed(b, bits) + carry_in) != _signed(r, bits)
        return r, (n, z, c, v)

    def cond(self, cc):
        return _COND[cc](*self.flags)

    def decode(self, pc):
        if pc not in self.cache:
            self.cache[pc] = next(self.md.disasm(self.rom[pc:pc + 4], pc))
        return self.cache[pc]

    def call(self, pc, args=(), limit=200000):
        """Runs the routine at pc with x0.. = args until it returns."""
        for k, v in enumerate(args):
            self.x[k] = v & M64
        self.x[30] = RETURN
        for _ in range(limit):
            if pc == RETURN:
                return self.x[0]
            if pc in self.stubs:
                self.stubs[pc](self)
                pc = self.x[30]
                continue
            pc = self.step(pc)
        raise RuntimeError('routine did not return')

    def step(self, pc):
        i = self.decode(pc)
        m = i.mnemonic
        ops = i.operands
        nxt = pc + 4
        cc = i.cc
        if m.startswith('b.'):
            return ops[0].imm if self.cond(cc) else nxt
        if m == 'b':
            return ops[0].imm
        if m == 'bl':
            self.x[30] = nxt
            return ops[0].imm
        if m == 'br':
            return self.get(ops[0].reg)
        if m == 'blr':
            self.x[30] = nxt
            return self.get(ops[0].reg)
        if m == 'ret':
            return self.x[30]
        if m in ('cbz', 'cbnz'):
            z = self.get(ops[0].reg) == 0
            return ops[1].imm if z == (m == 'cbz') else nxt
        if m in ('tbz', 'tbnz'):
            bit = (self.get(ops[0].reg) >> ops[1].imm) & 1
            return ops[2].imm if (bit == 0) == (m == 'tbz') else nxt
        if m in ('nop', 'prfm'):
            return nxt
        if m in ('adrp', 'adr'):
            self.set(ops[0].reg, ops[1].imm)
            return nxt
        if m.startswith(('ldr', 'ldur', 'str', 'stur', 'ldp', 'stp', 'ldar')):
            self._mem(i, m, ops)
            return nxt
        bits = self.width(ops[0].reg)
        mask = (1 << bits) - 1
        if m in ('mov', 'movz'):
            self.set(ops[0].reg, self.val(ops[1], bits))
        elif m == 'movn':
            self.set(ops[0].reg, ~self.val(ops[1], bits))
        elif m == 'movk':
            sh = ops[1].shift.value
            old = self.get(ops[0].reg) & ~(0xFFFF << sh)
            self.set(ops[0].reg, old | (ops[1].imm & 0xFFFF) << sh)
        elif m in ('add', 'adds', 'sub', 'subs'):
            r, f = self._addsub(self.get(ops[1].reg) & mask, self.val(ops[2], bits), bits, m.startswith('sub'))
            self.set(ops[0].reg, r)
            if m.endswith('s'):
                self.flags = f
        elif m in ('cmp', 'cmn'):
            _, self.flags = self._addsub(self.get(ops[0].reg) & mask, self.val(ops[1], bits), bits, m == 'cmp')
        elif m == 'neg':
            self.set(ops[0].reg, -self.val(ops[1], bits))
        elif m in ('and', 'ands', 'orr', 'eor', 'bic'):
            a, b = self.get(ops[1].reg) & mask, self.val(ops[2], bits)
            r = {'and': a & b, 'ands': a & b, 'orr': a | b, 'eor': a ^ b, 'bic': a & ~b}[m] & mask
            self.set(ops[0].reg, r)
            if m == 'ands':
                self.flags = (bool(r >> (bits - 1)), r == 0, False, False)
        elif m == 'tst':
            r = self.get(ops[0].reg) & self.val(ops[1], bits)
            self.flags = (bool(r >> (bits - 1)), r == 0, False, False)
        elif m in ('lsl', 'lsr', 'asr'):
            a, s = self.get(ops[1].reg) & mask, self.val(ops[2], bits) % bits
            r = a << s if m == 'lsl' else a >> s if m == 'lsr' else _signed(a, bits) >> s
            self.set(ops[0].reg, r)
        elif m in ('sxtw', 'sxth', 'sxtb', 'uxtb', 'uxth'):
            src = self.get(ops[1].reg)
            r = {'sxtw': _signed(src, 32), 'sxth': _signed(src, 16), 'sxtb': _signed(src, 8), 'uxtb': src & 0xFF,
                 'uxth': src & 0xFFFF}[m]
            self.set(ops[0].reg, r)
        elif m in ('madd', 'msub', 'mul', 'mneg'):
            a, b = self.get(ops[1].reg) & mask, self.get(ops[2].reg) & mask
            acc = self.get(ops[3].reg) if m in ('madd', 'msub') else 0
            self.set(ops[0].reg, acc + a * b if m != 'msub' and m != 'mneg' else acc - a * b)
        elif m in ('smaddl', 'smull', 'umaddl', 'umull', 'smsubl'):
            a, b = self.get(ops[1].reg), self.get(ops[2].reg)
            if m[0] == 's':
                a, b = _signed(a, 32), _signed(b, 32)
            acc = self.get(ops[3].reg) if len(ops) > 3 else 0
            self.set(ops[0].reg, acc - a * b if m == 'smsubl' else acc + a * b)
        elif m in ('csel', 'csinc', 'csinv', 'csneg'):
            if self.cond(cc):
                r = self.get(ops[1].reg)
            else:
                b = self.get(ops[2].reg)
                r = {'csel': b, 'csinc': b + 1, 'csinv': ~b, 'csneg': -b}[m]
            self.set(ops[0].reg, r)
        elif m in ('cset', 'csetm'):
            self.set(ops[0].reg, (1 if m == 'cset' else -1) if self.cond(cc) else 0)
        elif m in ('cinc', 'cneg', 'cinv'):
            a = self.get(ops[1].reg)
            self.set(ops[0].reg, ({'cinc': a + 1, 'cneg': -a, 'cinv': ~a}[m]) if self.cond(cc) else a)
        elif m in ('ccmp', 'ccmn'):
            if self.cond(cc):
                _, self.flags = self._addsub(self.get(ops[0].reg) & mask, self.val(ops[1], bits), bits, m == 'ccmp')
            else:
                nzcv = ops[2].imm
                self.flags = (bool(nzcv & 8), bool(nzcv & 4), bool(nzcv & 2), bool(nzcv & 1))
        else:
            raise NotImplementedError(f'{pc:#x}: {m} {i.op_str}')
        return nxt

    def _mem(self, i, m, ops):
        pair = m in ('ldp', 'stp', 'ldpsw')
        mop = ops[2] if pair else ops[1]
        a = self._addr(i, mop)
        post = len(ops) > (3 if pair else 2)          # a post-index writes back base + imm after the access
        if post:
            a = self.get(mop.mem.base)
        regs = [ops[0], ops[1]] if pair else [ops[0]]
        if m.endswith('sw'):
            size = 4
        elif m.endswith('b'):
            size = 1
        elif m.endswith('h'):
            size = 2
        else:
            size = self.width(regs[0].reg) // 8
        signed = m.startswith(('ldrs', 'ldurs', 'ldpsw'))
        load = m.startswith(('ld',))
        for k, r in enumerate(regs):
            addr = a + k * size
            if load:
                v = int.from_bytes(self.read(addr, size), 'little')
                if signed:
                    v = _signed(v, size * 8)
                self.set(r.reg, v)
            else:
                self.write(addr, (self.get(r.reg) & ((1 << size * 8) - 1)).to_bytes(size, 'little'))
        if post:
            self.set(mop.mem.base, a + ops[-1].imm)
        elif i.writeback:
            self.set(mop.mem.base, a)


# The gambit area builder, `0x41e4e0(set, shape, target x, y, user x, y, facing, check bounds)`: it empties the set (`0x5be8d0`), then by
# the shape (a jump table at `0xce9f18`, shapes 1-14) adds each tile of the area through `0xae740(set, x, y, check)`, which (without
# the bounds check) adds the battle grid's tile record (`[[0x1aa7cc8]] + y * 0x600 + x * 0x30`) with `0x5be760`. Shape 1 is
# `0xad640` (the target and the four tiles around it), 5 `0x98ed0` (the target and the twelve tiles of the table at `0xcdc648`), 2
# `0xb1f30` (rows of a table at `0xcdc648` / `0xcdc6a8` chosen by the side the user stands on); the rest are written out in the
# routine, each by whether the user is further off along x or y and on which side.
AREA_BUILDER = 0x41E4E0
_CLEAR, _ADD = 0x5BE8D0, 0x5BE760
_GRID_GOT = 0x1AA7CC8
_GRID = 0x10000000
_SET = 0x30000000


def gambit_area(shape, target, user, cpu=None):
    """The tiles (x, y) the area builder puts in a gambit's area of `shape` for a user at `user` aiming at `target`."""
    cpu = cpu or Arm64()
    cpu.reset()
    tiles = []

    def add(c):
        off = c.x[1] - _GRID
        tiles.append(((off % 0x600) // 0x30, off // 0x600))
    cpu.stubs = {_CLEAR: lambda c: None, _ADD: add}
    cpu.put64(cpu.u64(_GRID_GOT), _GRID)
    cpu.call(AREA_BUILDER, (_SET, shape, target[0], target[1], user[0], user[1], 0, 0))
    return tiles

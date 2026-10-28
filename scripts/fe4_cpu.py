"""
A small 65816 interpreter, just enough to run Genealogy of the Holy War's own decompression routine on the user's ROM, so the
generators can read compressed data (maps, tables) without a hand-made port of the routine. Not a full SNES: only the ROM and the
128 KB of work RAM exist, and no hardware is touched.

    cpu = Cpu()
    out = cpu.decompress(0xC8142F)   # SNES address of the compressed stream -> bytes

The routine is the game's own, at $80:AA02 (found by tracing a chapter load in Mesen; see data-raw/fe4/README.md).
"""
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from fe4_asm import MODES, OPS  # noqa: E402
from fe4_rom import R  # noqa: E402

DECOMPRESS = 0x80AA02
SENTINEL = 0xFFFF00  # a return address nothing else uses


def rom_offset(addr):
    return ((addr >> 16) & 0x3F) << 16 | (addr & 0xFFFF)


class Cpu:
    def __init__(self, rom=None, mapper=None):
        # The ROM and its address mapping: Genealogy of the Holy War's (HiROM) unless another game's are given (Thracia 776 is LoROM).
        self.rom = R if rom is None else rom
        self.mapper = mapper or rom_offset
        self.ram = bytearray(0x20000)
        self.a = self.x = self.y = 0
        self.s = 0x1FFF
        self.d = 0
        self.db = 0
        self.pb = 0
        self.pc = 0
        # flags: N V M X D I Z C
        self.n = self.v = self.d_flag = self.i = self.z = self.c = False
        self.m = self.xf = True  # True = 8-bit
        self.e = False
        self.writes = []

    # --- memory ---
    def read(self, addr):
        bank, off = addr >> 16, addr & 0xFFFF
        if bank in (0x7E, 0x7F):
            return self.ram[(bank - 0x7E) << 16 | off]
        if bank < 0x40 or 0x80 <= bank < 0xC0:
            if off < 0x2000:
                return self.ram[off]
            if off < 0x8000:
                return 0
        o = self.mapper(addr)
        return self.rom[o] if o < len(self.rom) else 0

    def write(self, addr, value):
        bank, off = addr >> 16, addr & 0xFFFF
        if bank in (0x7E, 0x7F):
            self.ram[(bank - 0x7E) << 16 | off] = value & 0xFF
            self.writes.append(addr)
        elif (bank < 0x40 or 0x80 <= bank < 0xC0) and off < 0x2000:
            self.ram[off] = value & 0xFF

    def read16(self, addr):
        return self.read(addr) | self.read((addr + 1) & 0xFFFFFF) << 8

    def write16(self, addr, v):
        self.write(addr, v & 0xFF)
        self.write((addr + 1) & 0xFFFFFF, v >> 8 & 0xFF)

    # --- stack ---
    def push(self, v):
        self.write(self.s, v)
        self.s = (self.s - 1) & 0xFFFF

    def pull(self):
        self.s = (self.s + 1) & 0xFFFF
        return self.read(self.s)

    def push16(self, v):
        self.push(v >> 8 & 0xFF)
        self.push(v & 0xFF)

    def pull16(self):
        lo = self.pull()
        return lo | self.pull() << 8

    # --- flags ---
    @property
    def p(self):
        return (self.n << 7 | self.v << 6 | self.m << 5 | self.xf << 4 | self.d_flag << 3 | self.i << 2 | self.z << 1 | self.c)

    @p.setter
    def p(self, v):
        self.n, self.v, self.m, self.xf = bool(v & 0x80), bool(v & 0x40), bool(v & 0x20), bool(v & 0x10)
        self.d_flag, self.i, self.z, self.c = bool(v & 8), bool(v & 4), bool(v & 2), bool(v & 1)
        if self.xf:
            self.x &= 0xFF
            self.y &= 0xFF

    def nz(self, v, byte):
        mask = 0x80 if byte else 0x8000
        self.n = bool(v & mask)
        self.z = (v & (0xFF if byte else 0xFFFF)) == 0

    # --- fetch ---
    def fetch(self):
        v = self.read(self.pb << 16 | self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return v

    def fetch16(self):
        lo = self.fetch()
        return lo | self.fetch() << 8

    def fetch24(self):
        lo = self.fetch16()
        return lo | self.fetch() << 16

    # --- effective addresses (each returns a 24-bit address) ---
    def ea(self, mode):
        db = self.db << 16
        d = self.d
        if mode == 'dp':
            return (d + self.fetch()) & 0xFFFF
        if mode == 'dpx':
            return (d + self.fetch() + self.x) & 0xFFFF
        if mode == 'dpy':
            return (d + self.fetch() + self.y) & 0xFFFF
        if mode == 'idp':
            return db | self.read16((d + self.fetch()) & 0xFFFF)
        if mode == 'idpx':
            return db | self.read16((d + self.fetch() + self.x) & 0xFFFF)
        if mode == 'idpy':
            return (db | self.read16((d + self.fetch()) & 0xFFFF)) + self.y
        if mode == 'ildp':
            a = (d + self.fetch()) & 0xFFFF
            return self.read16(a) | self.read(a + 2) << 16
        if mode == 'ildpy':
            a = (d + self.fetch()) & 0xFFFF
            return (self.read16(a) | self.read(a + 2) << 16) + self.y
        if mode == 'abs':
            return db | self.fetch16()
        if mode == 'absx':
            return (db | self.fetch16()) + self.x
        if mode == 'absy':
            return (db | self.fetch16()) + self.y
        if mode == 'long':
            return self.fetch24()
        if mode == 'longx':
            return self.fetch24() + self.x
        if mode == 'sr':
            return (self.s + self.fetch()) & 0xFFFF
        if mode == 'sry':
            return (db | self.read16((self.s + self.fetch()) & 0xFFFF)) + self.y
        raise NotImplementedError(mode)

    def load(self, mode, byte):
        if mode == 'immM' or mode == 'immX':
            return self.fetch() if byte else self.fetch16()
        a = self.ea(mode) & 0xFFFFFF
        return self.read(a) if byte else self.read16(a)

    # --- execution ---
    def step(self):
        code = self.fetch()
        name, mode = OPS[code]
        m8, x8 = self.m, self.xf
        if name in ('LDA', 'STA', 'ADC', 'SBC', 'AND', 'ORA', 'EOR', 'CMP', 'BIT'):
            if name == 'STA':
                a = self.ea(mode) & 0xFFFFFF
                if m8:
                    self.write(a, self.a & 0xFF)
                else:
                    self.write16(a, self.a)
                return
            v = self.load(mode, m8)
            self.alu(name, v, m8)
        elif name in ('LDX', 'LDY', 'CPX', 'CPY'):
            v = self.load(mode, x8)
            if name == 'LDX':
                self.x = v
                self.nz(v, x8)
            elif name == 'LDY':
                self.y = v
                self.nz(v, x8)
            else:
                r = self.x if name == 'CPX' else self.y
                self.c = r >= v
                self.nz((r - v) & (0xFF if x8 else 0xFFFF), x8)
        elif name in ('STX', 'STY', 'STZ'):
            a = self.ea(mode) & 0xFFFFFF
            val = {'STX': self.x, 'STY': self.y, 'STZ': 0}[name]
            byte = m8 if name == 'STZ' else x8
            if byte:
                self.write(a, val & 0xFF)
            else:
                self.write16(a, val)
        elif name in ('ASL', 'LSR', 'ROL', 'ROR'):
            if mode == 'acc':
                self.a = self.shift(name, self.a, m8) if not m8 else (self.a & 0xFF00) | self.shift(name, self.a & 0xFF, True)
            else:
                a = self.ea(mode) & 0xFFFFFF
                v = self.read(a) if m8 else self.read16(a)
                r = self.shift(name, v, m8)
                self.write(a, r) if m8 else self.write16(a, r)
        elif name in ('INC', 'DEC'):
            delta = 1 if name == 'INC' else -1
            if mode == 'acc':
                if m8:
                    self.a = (self.a & 0xFF00) | ((self.a + delta) & 0xFF)
                    self.nz(self.a & 0xFF, True)
                else:
                    self.a = (self.a + delta) & 0xFFFF
                    self.nz(self.a, False)
            else:
                a = self.ea(mode) & 0xFFFFFF
                v = ((self.read(a) if m8 else self.read16(a)) + delta) & (0xFF if m8 else 0xFFFF)
                self.write(a, v) if m8 else self.write16(a, v)
                self.nz(v, m8)
        elif name in ('INX', 'INY', 'DEX', 'DEY'):
            delta = 1 if name[:2] == 'IN' else -1
            mask = 0xFF if x8 else 0xFFFF
            if name[2] == 'X':
                self.x = (self.x + delta) & mask
                self.nz(self.x, x8)
            else:
                self.y = (self.y + delta) & mask
                self.nz(self.y, x8)
        elif name in ('BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ', 'BRA'):
            off = self.fetch()
            take = {'BPL': not self.n, 'BMI': self.n, 'BVC': not self.v, 'BVS': self.v, 'BCC': not self.c, 'BCS': self.c,
                    'BNE': not self.z, 'BEQ': self.z, 'BRA': True}[name]
            if take:
                self.pc = (self.pc + (off - 256 if off > 127 else off)) & 0xFFFF
        elif name == 'BRL':
            off = self.fetch16()
            self.pc = (self.pc + (off - 65536 if off > 32767 else off)) & 0xFFFF
        elif name == 'JSR':
            if mode == 'abs':
                t = self.fetch16()
                self.push16((self.pc - 1) & 0xFFFF)
                self.pc = t
            else:  # (abs,X)
                t = self.fetch16()
                self.push16((self.pc - 1) & 0xFFFF)
                self.pc = self.read16(self.pb << 16 | (t + self.x) & 0xFFFF)
        elif name == 'JSL':
            t = self.fetch24()
            self.push(self.pb)
            self.push16((self.pc - 1) & 0xFFFF)
            self.pb, self.pc = t >> 16, t & 0xFFFF
        elif name == 'JML':
            if mode == 'long':
                t = self.fetch24()
                self.pb, self.pc = t >> 16, t & 0xFFFF
            else:
                a = self.fetch16()
                t = self.read16(a) | self.read(a + 2) << 16
                self.pb, self.pc = t >> 16, t & 0xFFFF
        elif name == 'JMP':
            t = self.fetch16()
            if mode == 'abs':
                self.pc = t
            elif mode == 'iabs':
                self.pc = self.read16(t)
            else:
                self.pc = self.read16(self.pb << 16 | (t + self.x) & 0xFFFF)
        elif name == 'RTS':
            self.pc = (self.pull16() + 1) & 0xFFFF
        elif name == 'RTL':
            self.pc = (self.pull16() + 1) & 0xFFFF
            self.pb = self.pull()
        elif name == 'REP':
            v = self.fetch()
            self.p = self.p & ~v
        elif name == 'SEP':
            v = self.fetch()
            self.p = self.p | v
        elif name == 'CLC':
            self.c = False
        elif name == 'SEC':
            self.c = True
        elif name == 'CLI':
            self.i = False
        elif name == 'SEI':
            self.i = True
        elif name == 'CLD':
            self.d_flag = False
        elif name == 'SED':
            self.d_flag = True
        elif name == 'CLV':
            self.v = False
        elif name == 'XCE':
            self.c, self.e = self.e, self.c
        elif name == 'XBA':
            self.a = ((self.a & 0xFF) << 8) | (self.a >> 8 & 0xFF)
            self.nz(self.a & 0xFF, True)
        elif name == 'NOP':
            pass
        elif name in ('PHA', 'PHX', 'PHY'):
            reg, byte = {'PHA': (self.a, m8), 'PHX': (self.x, x8), 'PHY': (self.y, x8)}[name]
            self.push(reg & 0xFF) if byte else self.push16(reg)
        elif name in ('PLA', 'PLX', 'PLY'):
            byte = m8 if name == 'PLA' else x8
            v = self.pull() if byte else self.pull16()
            if name == 'PLA':
                self.a = (self.a & 0xFF00) | v if byte else v
            elif name == 'PLX':
                self.x = v
            else:
                self.y = v
            self.nz(v, byte)
        elif name == 'PHP':
            self.push(self.p)
        elif name == 'PLP':
            self.p = self.pull()
        elif name == 'PHB':
            self.push(self.db)
        elif name == 'PLB':
            self.db = self.pull()
            self.nz(self.db, True)
        elif name == 'PHK':
            self.push(self.pb)
        elif name == 'PHD':
            self.push16(self.d)
        elif name == 'PLD':
            self.d = self.pull16()
            self.nz(self.d, False)
        elif name in ('TAX', 'TAY', 'TXA', 'TYA', 'TXY', 'TYX', 'TSX', 'TXS', 'TCD', 'TDC', 'TCS', 'TSC'):
            self.transfer(name)
        elif name in ('MVN', 'MVP'):
            dst, src = self.fetch(), self.fetch()
            delta = 1 if name == 'MVN' else -1
            while True:
                self.write(dst << 16 | self.y & 0xFFFF, self.read(src << 16 | self.x & 0xFFFF))
                self.x = (self.x + delta) & 0xFFFF
                self.y = (self.y + delta) & 0xFFFF
                self.a = (self.a - 1) & 0xFFFF
                if self.a == 0xFFFF:
                    break
            self.db = dst
        elif name in ('TSB', 'TRB'):
            a = self.ea(mode) & 0xFFFFFF
            v = self.read(a) if m8 else self.read16(a)
            mask = 0xFF if m8 else 0xFFFF
            self.z = (v & self.a & mask) == 0
            r = (v | self.a) & mask if name == 'TSB' else v & ~self.a & mask
            self.write(a, r) if m8 else self.write16(a, r)
        elif name == 'PEA':
            self.push16(self.fetch16())
        elif name == 'PEI':
            self.push16(self.read16(self.d + self.fetch() & 0xFFFF))
        elif name == 'PER':
            off = self.fetch16()
            self.push16((self.pc + off) & 0xFFFF)
        else:
            raise NotImplementedError(f'{name} {mode} at {self.pb:02X}:{(self.pc - 1) & 0xFFFF:04X}')

    def transfer(self, name):
        m8, x8 = self.m, self.xf
        if name == 'TAX':
            self.x = self.a & (0xFF if x8 else 0xFFFF)
            self.nz(self.x, x8)
        elif name == 'TAY':
            self.y = self.a & (0xFF if x8 else 0xFFFF)
            self.nz(self.y, x8)
        elif name == 'TXA':
            self.a = (self.a & 0xFF00) | self.x if m8 else self.x
            self.nz(self.a, m8)
        elif name == 'TYA':
            self.a = (self.a & 0xFF00) | self.y if m8 else self.y
            self.nz(self.a, m8)
        elif name == 'TXY':
            self.y = self.x
            self.nz(self.y, x8)
        elif name == 'TYX':
            self.x = self.y
            self.nz(self.x, x8)
        elif name == 'TSX':
            self.x = self.s & (0xFF if x8 else 0xFFFF)
            self.nz(self.x, x8)
        elif name == 'TXS':
            self.s = self.x
        elif name == 'TCD':
            self.d = self.a
            self.nz(self.d, False)
        elif name == 'TDC':
            self.a = self.d
            self.nz(self.a, False)
        elif name == 'TCS':
            self.s = self.a
        elif name == 'TSC':
            self.a = self.s
            self.nz(self.a, False)

    def alu(self, name, v, byte):
        mask = 0xFF if byte else 0xFFFF
        a = self.a & mask
        if name == 'LDA':
            self.a = (self.a & 0xFF00) | v if byte else v
            self.nz(v, byte)
        elif name == 'AND':
            r = a & v
            self.a = (self.a & 0xFF00) | r if byte else r
            self.nz(r, byte)
        elif name == 'ORA':
            r = a | v
            self.a = (self.a & 0xFF00) | r if byte else r
            self.nz(r, byte)
        elif name == 'EOR':
            r = a ^ v
            self.a = (self.a & 0xFF00) | r if byte else r
            self.nz(r, byte)
        elif name == 'CMP':
            self.c = a >= v
            self.nz((a - v) & mask, byte)
        elif name == 'BIT':
            self.z = (a & v) == 0
            self.n = bool(v & (0x80 if byte else 0x8000))
            self.v = bool(v & (0x40 if byte else 0x4000))
        elif name in ('ADC', 'SBC'):
            if self.d_flag:
                raise NotImplementedError('decimal mode')
            if name == 'SBC':
                v = (~v) & mask
            r = a + v + (1 if self.c else 0)
            self.c = r > mask
            res = r & mask
            sign = 0x80 if byte else 0x8000
            self.v = bool(~(a ^ v) & (a ^ res) & sign)
            self.a = (self.a & 0xFF00) | res if byte else res
            self.nz(res, byte)

    def shift(self, name, v, byte):
        mask = 0xFF if byte else 0xFFFF
        top = 0x80 if byte else 0x8000
        c = self.c
        if name == 'ASL':
            self.c = bool(v & top)
            r = (v << 1) & mask
        elif name == 'LSR':
            self.c = bool(v & 1)
            r = v >> 1
        elif name == 'ROL':
            self.c = bool(v & top)
            r = ((v << 1) | c) & mask
        else:
            self.c = bool(v & 1)
            r = (v >> 1) | (top if c else 0)
        self.nz(r, byte)
        return r

    # --- the routine ---
    def call(self, addr, limit=2_000_000):
        """Runs the long subroutine at `addr` (JSL ... RTL) from the current registers until it returns."""
        self.push(SENTINEL >> 16)
        self.push16((SENTINEL - 1) & 0xFFFF)
        self.pb, self.pc = addr >> 16, addr & 0xFFFF
        steps = 0
        while not (self.pb << 16 | self.pc) == SENTINEL:
            self.step()
            steps += 1
            if steps > limit:
                raise RuntimeError(f'${addr:06X} did not return')

    def decompress(self, src, limit=2_000_000):
        """Runs the game's decompressor on the stream at the SNES address `src`; returns the bytes it writes (to $7F:0000 upward)."""
        self.ram = bytearray(0x20000)
        self.writes = []
        # Direct page $C8-$CA: source; $CB-$CC: destination offset; $CD: destination bank.
        self.d = 0
        for i, v in enumerate((src & 0xFF, src >> 8 & 0xFF, src >> 16 & 0xFF, 0x00, 0x00, 0x7F)):
            self.ram[0xC8 + i] = v
        self.s = 0x1FFF
        self.m = self.xf = True
        self.e = False
        self.p = 0x30
        self.push(SENTINEL >> 16)
        self.push16((SENTINEL - 1) & 0xFFFF)
        self.pb, self.pc = DECOMPRESS >> 16, DECOMPRESS & 0xFFFF
        steps = 0
        while not (self.pb << 16 | self.pc) == SENTINEL:
            self.step()
            steps += 1
            if steps > limit:
                raise RuntimeError('decompressor did not finish')
        return bytes(self.ram[0x10000:0x10000 + max((w & 0xFFFF) for w in self.writes) + 1]) if self.writes else b''


    # --- the event script interpreter ($86:83D8) ---
    def script_skip(self, bank, y, limit=5000):
        """The address after the command at bank:y, found by running the interpreter's own skip entry ($86:83F0: carry set, which
        every command handler answers by stepping past its operands without doing anything)."""
        self.s = 0x1FFF
        self.m = False
        self.xf = False
        self.p = self.p & ~0x30
        self.db = bank
        self.y = y
        self.a = self.read16(bank << 16 | y)
        self.push16(0xFEFF)  # the handler ends in RTS: it returns here, in bank $86
        self.pb, self.pc = 0x86, 0x83F0
        steps = 0
        while not (self.pb == 0x86 and self.pc == 0xFF00):
            self.step()
            steps += 1
            if steps > limit:
                raise RuntimeError(f'skip did not finish at {bank:02X}:{y:04X}')
        return self.y


if __name__ == '__main__':
    cpu = Cpu()
    out = cpu.decompress(int(sys.argv[1], 16))
    print(len(out), out[:32].hex(' '))

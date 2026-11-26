"""
Radiant Dawn's startup script (Scripts/startup.cmb), the shared functions every chapter script calls by name: Path of Radiance's
format (fe9_cmb.py) with two differences. Op 0x37 calls another handler by its number, which takes one byte, or two when the
first has its top bit set (the startup script's helpers sit past handler 127: 0x81 0x81 is handler 0x181, TeamTransferPID); and
op 0x47 stores the value on top of the stack into the address under it. No chapter script calls a handler past 127, so the
generators read those with fe9_cmb (build-fe10-maps.py's calls10 handles the store). Ported from the Roster's fe10_cmb.py and
team_moves() (build-fe10-units.py), which read the teams the same way.
"""
import os

import fe9_cmb
from fe10_files import FE10

# The startup script's helpers that move units between teams (handler numbers): UnitTransferToForceALL (a whole team),
# TeamCheckTransferPID (each listed unit of a team), UnitCheckTransferPID (each listed unit, if it's in a team) and TeamTransferPID.
ALL_TO, TEAM_CHECK, UNIT_CHECK, TEAM_PID = 382, 383, 384, 385


class Script(fe9_cmb.Script):
    def __init__(self, name):
        super().__init__(os.path.join(FE10, 'Scripts', name))

    def disasm(self, h):
        """[(pc, op, arg)] as fe9_cmb's, with ('callh', handler number) for op 0x37 and ('store', '') for 0x47."""
        d = self.d
        pc = h['code']
        out = []
        furthest = pc
        while pc < h['end']:
            op = d[pc]
            if op == 0x37:
                b = d[pc + 1]
                if b & 0x80:
                    out.append((pc, 'callh', ((b & 0x7F) << 8) | d[pc + 2]))
                    pc += 3
                else:
                    out.append((pc, 'callh', b))
                    pc += 2
                continue
            if op == 0x47:
                out.append((pc, 'store', ''))
                pc += 1
                continue
            name, n = fe9_cmb.OPS.get(op, (f'?{op:02x}', 0))
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
            if name == 'ret' and pc > furthest:
                break
        return out


def team_moves(startup):
    """The startup script's TEAM_ functions as moves: {name: [(PID or None, from team or None, to team)]}. PID None moves a whole
    team; `from` None moves the unit wherever it is. Your army is team 5 while a chapter is set up (0 is your side on the map);
    8, 9 and 10 hold the armies not being played, 7 units away from every army."""
    out = {}
    for h in startup.handlers():
        if not h['name'].startswith('TEAM_'):
            continue
        moves, pids, ints, source = [], [], [], None
        for _, op, a in startup.disasm(h):
            if op == 'str':
                pids.append(a)
            elif op == 'int':
                ints.append(a)
            elif op == 'call' and a == 'ForceGetFirst/1':
                source = ints[-1]
            elif op == 'callh':
                if a == ALL_TO:
                    moves.append((None, ints[-2], ints[-1]))
                elif a == TEAM_PID:
                    moves.append((pids.pop(), None, ints[-1]))
                elif a == TEAM_CHECK:  # each unit of team `source` that's on the list goes to the team
                    moves += [(p, source, ints[-1]) for p in pids]
                    pids = []
                elif a == UNIT_CHECK:  # each listed unit in team `from` goes to team `to`
                    moves += [(p, ints[-2], ints[-1]) for p in pids]
                    pids = []
                ints = []
        out[h['name']] = moves
    return out

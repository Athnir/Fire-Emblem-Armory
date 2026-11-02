"""
Awakening's chapter scripts (scripts/<chapter>.cmb and <chapter>_Terrain.cmb; the DLC maps' own in their archives): the same bytecode
as Fates' (scripts/fates_cmb.py disassembles both), read here for what the maps need. The handler kinds (the low byte of a handler's
kind) the game uses:

  0x07  the chapter's load: PersonLoad, TerrainLoad (its argument names the grid; usually the chapter's own), DisposLoad and the
        groups placed before the battle
  0x0a  the end of the chapter (after victory): units placed here join once the battle is over
  0x0c  a turn's phase starting: (first turn, last turn, phase 0 player / 1 enemy / 2 other)
  0x0d  as 0x0c (Chapter 18's lava: one per turn and phase)
  0x0e  as 0x0c, the tutorials'
  0x0f  reinforcements: (first turn, last turn); -1 = no limit
  0x10  an area or condition: (x1, y1, x2, y2, side, condition function name); -1 = anywhere / any side
  0x11  (the _Terrain script) a tile: (x, y, kind, ...): 8 village or house, 14 door, 15 chest, 23 event tile
  0x12  a talk: (talker PID, target PID, ...); a target handed over with UnitTransferByIndex is recruited
  0x13  a battle conversation; 0x15 a death quote: (PID, 1 enemy / 2 ally, ...)
String arguments are offsets into the script's string table.
"""
import os

from fates_cmb import Script
from fates_schedule import UNKNOWN
from fates_cmb import OPS

DIFFS = ['Normal', 'Hard', 'Lunatic']
LOAD, END, TURN, TURN2, TUTORIAL, REINFORCE, AREA, TILE, TALK, DEATH = 0x07, 0x0A, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x15
TILE_KINDS = {8: 'village', 14: 'door', 15: 'chest', 23: 'event'}
PHASES = {0: 'player phase', 1: 'enemy phase', 2: 'other phase'}


class Chapter:
    """One map's scripts."""

    def __init__(self, path):
        self.s = Script(path)
        tpath = path.replace('.cmb', '_Terrain.cmb')
        self.t = Script(tpath) if os.path.exists(tpath) else None
        self.hs = [self._prep(self.s, h) for h in self.s.handlers()]
        self.ths = [self._prep(self.t, h) for h in self.t.handlers()] if self.t else []

    @staticmethod
    def _prep(s, h):
        h = dict(h)
        h['k'] = h['kind'] & 0xFF
        try:
            h['ins'] = s.disasm(h)
        except (ValueError, IndexError):
            h['ins'] = []
        return h

    def string(self, off, s=None):
        try:
            return (s or self.s).string(off)
        except (ValueError, IndexError):
            return None

    def of_kind(self, *kinds):
        return [h for h in self.hs if h['k'] in kinds]

    def calls(self, h, name):
        """The arguments of every call to `name` in a handler (only literal ints and strings; anything else is None)."""
        out = []
        ins = h['ins']
        for k, (_, n, a) in enumerate(ins):
            if n == 'call' and a.split('/')[0] == name:
                argc = int(a.split('/')[1])
                args = []
                for j in range(k - argc, k):
                    _, n2, a2 = ins[j]
                    args.append(a2.strip("'") if n2 == 'str' else a2 if n2 == 'int' else None)
                out.append(args)
        return out

    def terrain_load(self):
        """The grid a chapter loads: TerrainLoad's string, or None for its own."""
        for h in self.of_kind(LOAD):
            for args in self.calls(h, 'ev::TerrainLoad'):
                return args[0]
        return None


def run(script, h, difficulty, turn, limit=20000, with_flags=False, tricks=False, local0=None, depth=0):
    """[(group, conditional)] for every ev::Dispos a handler reaches on a difficulty (0 Normal, 1 Hard, 2 Lunatic) and turn, with
    DifficultyGet and TurnGet answered and every other unknown value tried both ways (marked conditional). With `with_flags`, each is
    (group, Dispos's second argument, conditional): 4 the load's placing, 8 a reinforcement's, 512 a set aside for a random pick and 1028
    the positions the picks are placed on (the DLC maps whose foes are random). With `tricks`, it's [((x, y, kind, state), conditional)]
    for every ev::TrickSet instead (None where an argument isn't known), following the script's own functions it calls (gvar n, with
    what the statement pushed before it as their first variables)."""
    d = script.d
    start, end = h['code']
    found = []
    paths = [(start, [], dict(local0 or {}), False)]
    steps = 0
    while paths:
        pc, stack, local, cond = paths.pop()
        while start <= pc < end:
            steps += 1
            if steps > limit:
                return found + [('?', None, True) if with_flags else ('?', True)]
            op = d[pc]
            if op not in OPS:
                break
            name, n = OPS[op]
            raw = d[pc + 1:pc + 1 + n]
            nxt = pc + 1 + n
            if name == 'int':
                stack.append(int.from_bytes(raw, 'big', signed=True))
            elif name == 'str':
                stack.append(script.string(int.from_bytes(raw, 'big')))
            elif name == 'call':
                fn = script.string(int.from_bytes(raw[:2], 'big'))
                argc = raw[2]
                args = stack[len(stack) - argc:] if argc else []
                del stack[len(stack) - argc:]
                if fn == 'ev::DifficultyGet':
                    stack.append(difficulty)
                elif fn == 'ev::TurnGet':
                    stack.append(turn)
                elif fn == 'ev::Dispos':
                    if args and isinstance(args[0], str) and not tricks:
                        found.append((args[0], cond) if not with_flags else (args[0], args[1] if len(args) > 1 else None, cond))
                    stack.append(0)
                elif fn == 'ev::TrickSet' and tricks:
                    found.append((tuple(a if isinstance(a, int) else None for a in args), cond))
                    stack.append(0)
                else:
                    stack.append(UNKNOWN)
            elif name == 'load':
                stack.append(('addr', raw[0]))
            elif name == 'var':
                stack.append(local.get(raw[0], UNKNOWN) if n == 1 else UNKNOWN)
            elif name == 'index':
                i = stack.pop() if stack else UNKNOWN
                stack.append(local.get(raw[0] + i, UNKNOWN) if isinstance(i, int) else UNKNOWN)
            elif name == 'deref':
                a = stack[-1] if stack else UNKNOWN
                stack.append(local.get(a[1], UNKNOWN) if isinstance(a, tuple) else UNKNOWN)
            elif name == 'dup':
                stack.append(stack[-1] if stack else UNKNOWN)
            elif name == 'assign':
                if len(stack) < 2:
                    break
                val, addr = stack.pop(), stack.pop()
                if isinstance(addr, tuple):
                    local[addr[1]] = val
                stack.append(val)
            elif name == 'pop':
                if stack:
                    stack.pop()
            elif name in ('eq', 'ne', 'lt', 'le', 'gt', 'ge', 'add', 'sub'):
                if len(stack) < 2:
                    break
                b, a = stack.pop(), stack.pop()
                if not isinstance(a, int) or not isinstance(b, int):
                    stack.append(UNKNOWN)
                else:
                    stack.append({'eq': a == b, 'ne': a != b, 'lt': a < b, 'le': a <= b, 'gt': a > b, 'ge': a >= b,
                                  'add': a + b, 'sub': a - b}[name])
            elif name in ('jz', 'jnz'):
                v = stack.pop() if stack else UNKNOWN
                target = pc + 1 + int.from_bytes(raw, 'big', signed=True)
                if v is UNKNOWN:
                    paths.append((target, list(stack), dict(local), True))
                    cond = True
                elif (not v) == (name == 'jz'):
                    nxt = target
            elif name in ('orjump', 'andjump'):
                v = stack[-1] if stack else UNKNOWN
                target = pc + 1 + int.from_bytes(raw, 'big', signed=True)
                if v is UNKNOWN:
                    paths.append((target, list(stack), dict(local), True))
                    if stack:
                        stack.pop()
                    cond = True
                elif bool(v) == (name == 'orjump'):
                    nxt = target
                elif stack:
                    stack.pop()
            elif name == 'jmp':
                nxt = pc + 1 + int.from_bytes(raw, 'big', signed=True)
            elif name == 'gvar':
                # A call to the script's own function n: what this statement pushed are its first variables; what it places or
                # changes counts for this handler (the Endgame's every-turn handler places its sigils' groups through them).
                callee = _handler_by_index(script, raw[0])
                if callee and depth < 3:
                    n_args = _params(script, callee)
                    args = stack[len(stack) - n_args:] if n_args else []
                    for item in run(script, callee, difficulty, turn, limit, with_flags, tricks, dict(enumerate(args)), depth + 1):
                        found.append(item[:-1] + (item[-1] or cond,))
                del stack[:]
                stack.append(UNKNOWN)
            elif name == 'ret':
                break
            elif name.startswith('?') and n == 0 and stack and name != '?4e':  # 0x4e only sits between statements
                stack[-1] = UNKNOWN
            pc = nxt
    return found


def called(script):
    """The indexes of the script's functions that another handler calls (gvar n)."""
    if not hasattr(script, '_called'):
        script._called = {d for hd in script.handlers() for _, n, a in script.disasm(hd) if n == 'gvar' for d in [int(a, 16)]}
    return script._called


def _params(script, h):
    """How many arguments a script function takes: the variables it reads (var n) without assigning them first (load n)."""
    read, set_ = set(), set()
    for _, n, a in script.disasm(h):
        if n == 'load':
            set_.add(int(a, 16))
        elif n == 'var' and int(a, 16) not in set_:
            read.add(int(a, 16))
    return max(read) + 1 if read else 0


def _handler_by_index(script, idx):
    if not hasattr(script, '_by_index'):
        script._by_index = {hd['index']: hd for hd in script.handlers()}
    return script._by_index.get(idx)


def tricks(ch, h, difficulty=0, turn=99):
    """[(x, y, kind, state, conditional)]: the tile changes a handler makes (ev::TrickSet, 0x3b6c8c), its own and its functions'."""
    s = ch.t if h in ch.ths else ch.s
    return [(*t, c) for t, c in run(s, h, difficulty, turn, tricks=True) if isinstance(t, tuple) and len(t) == 4]


def tricks_by_flag(ch, h):
    """{flag: [(x, y, kind, state)]}: a handler's tile changes split at its ev::FlagGet checks, each change under the last flag read
    before it (Paralogue 14's villages appearing, Paralogue 16's doors opening their walls)."""
    s = ch.t if h in ch.ths else ch.s
    ins = h['ins']
    marks = [(ins[k][0], ins[k - 1][2].strip("'")) for k in range(1, len(ins))
             if ins[k][1] == 'call' and ins[k][2].startswith('ev::FlagGet') and ins[k - 1][1] == 'str']
    out = {}
    for n, (pc, flag) in enumerate(marks):
        end = marks[n + 1][0] if n + 1 < len(marks) else h['code'][1]
        part = {'code': (pc, end), 'index': h.get('index')}
        found = [t for t, _ in run(s, part, 0, 99, tricks=True) if isinstance(t, tuple) and len(t) == 4 and None not in t]
        if found:
            out.setdefault(flag, [])
            out[flag] += [t for t in found if t not in out[flag]]
    return out


def removed_pids(ch, h):
    """PIDs a handler takes off the map (UnitGetByPID into a local, then UnitExpulsionByIndex / UnitDeleteByIndex on it)."""
    ins = h['ins']
    var_pid, out = {}, []
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::UnitGetByPID') and k >= 2 and ins[k - 2][1] == 'load' and ins[k - 1][1] == 'str':
            var_pid[ins[k - 2][2]] = ins[k - 1][2].strip("'")
        if n == 'call' and (a.startswith('ev::UnitExpulsionByIndex') or a.startswith('ev::UnitDeleteByIndex')) and k:
            if ins[k - 1][1] == 'var' and ins[k - 1][2] in var_pid:
                out.append(var_pid[ins[k - 1][2]])
            elif k >= 2 and str(ins[k - 1][2]).startswith('ev::UnitGetByPID') and ins[k - 2][1] == 'str':
                # UnitGetByPID straight into the removal, with no local between.
                out.append(ins[k - 2][2].strip("'"))
    return out


def item_gains(h):
    """Items a handler gives (ev::ItemGain's IID), with the PIDs it checks first (UnitIsPID): [(iid, [pids])]."""
    ins = h['ins']
    out = []
    pids = []
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::UnitIsPID') and k and ins[k - 1][1] == 'str':
            pids.append(ins[k - 1][2].strip("'"))
        if n == 'call' and (a.startswith('ev::ItemGain') or a.startswith('ev::ItemGainSilent')) and k and ins[k - 1][1] == 'str':
            out.append((ins[k - 1][2].strip("'"), list(pids)))
    return out


def random_gains(h):
    """The random items a handler gives (ev::ItemGain of ev::ItemGetRandom or ev::ItemGetRandomLimit, with a seed the map's load
    stored): ['any' or 'limit' for each]."""
    out = []
    for _, n, a in h['ins']:
        if n == 'call' and a.startswith('ev::ItemGetRandomLimit'):
            out.append('limit')
        elif n == 'call' and a.startswith('ev::ItemGetRandom'):
            out.append('any')
    return out


def gold_gains(h):
    ins = h['ins']
    return [ins[k - 1][2] for k, (_, n, a) in enumerate(ins)
            if n == 'call' and a.startswith('ev::GoldGain') and k and ins[k - 1][1] == 'int']


def flags_set(h):
    ins = h['ins']
    return [ins[k - 1][2].strip("'") for k, (_, n, a) in enumerate(ins)
            if n == 'call' and a.startswith('ev::FlagSet') and k and ins[k - 1][1] == 'str']


def flags_read(h):
    ins = h['ins']
    return [ins[k - 1][2].strip("'") for k, (_, n, a) in enumerate(ins)
            if n == 'call' and a.startswith('ev::FlagGet') and k and ins[k - 1][1] == 'str']


def recruits(ch, h):
    """PIDs a talk or event hands over to the player (UnitTransferByIndex)."""
    ins = h['ins']
    var_pid, out = {}, []
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::UnitGetByPID') and k >= 2 and ins[k - 2][1] == 'load' and ins[k - 1][1] == 'str':
            var_pid[ins[k - 2][2]] = ins[k - 1][2].strip("'")
        if n == 'call' and a.startswith('ev::UnitTransferByIndex'):
            for j in range(k - 1, max(k - 4, 0), -1):
                if ins[j][1] == 'var' and ins[j][2] in var_pid:
                    out.append(var_pid[ins[j][2]])
                    break
    return out

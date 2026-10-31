"""
The interpreter behind fates_arrivals.py: work out when each reinforcement / joiner group arrives, by running a chapter script's event handlers
in a tiny interpreter for every difficulty and turn. Anything the interpreter can't know (story flags,
which units are still alive...) forks both ways and marks the arrival as conditional.
"""
from fates_cmb import OPS, Script

DIFFS = ['Normal', 'Hard', 'Lunatic']
UNKNOWN = object()
TURN_KINDS = (0x10, 0x13)  # (first turn, last turn, phase) handlers; -1 = every turn
AREA_KIND = 0x14  # (x, y, x2, y2, ...) handlers: when a unit reaches the area
PHASES = {0: 'player phase', 1: 'enemy phase', 2: 'other phase'}


GROUP_PREFIXES = ('Reinforce', 'Enemy', 'Ally', 'Support')
_helpers = {}


def places_groups(script, index):
    """Whether handler `index` of the script places a group itself (calls ev::Dispos)."""
    key = (id(script), index)
    if key not in _helpers:
        h = next((x for x in script.handlers() if x['index'] == index), None)
        try:
            _helpers[key] = bool(h) and any(n == 'call' and a.startswith('ev::Dispos/') for _, n, a in script.disasm(h))
        except (ValueError, IndexError):
            _helpers[key] = False
    return _helpers[key]


def run(script, handler, difficulty, turn, limit=4000):
    """[(group, conditional)] for every ev::Dispos this handler reaches."""
    d = script.d
    start, end = handler['code']
    found = []
    # Each path remembers the unknown tests it has passed: reaching one again is a loop going round (Birthright 23 walks every
    # enemy to change its AI before placing a group), so it leaves the loop instead of forking forever.
    paths = [(start, [], {}, False, frozenset())]
    steps = 0
    while paths:
        pc, stack, local, cond, seen = paths.pop()
        while start <= pc < end:
            steps += 1
            if steps > limit:
                return found + [('?', True)]
            op = d[pc]
            if op not in OPS:
                return found
            name, n = OPS[op]
            raw = d[pc + 1:pc + 1 + n]
            nxt = pc + 1 + n
            if name == 'int':
                stack.append(int.from_bytes(raw, 'big', signed=True))
            elif name == 'str':
                try:
                    stack.append(script.string(int.from_bytes(raw, 'big')))
                except ValueError:
                    return found
            elif name == 'call':
                try:
                    fn = script.string(int.from_bytes(raw[:2], 'big'))
                except ValueError:
                    return found
                argc = raw[2]
                args = stack[len(stack) - argc:] if argc else []
                del stack[len(stack) - argc:]
                if fn == 'ev::DifficultyGet':
                    stack.append(difficulty)
                elif fn == 'ev::TurnGet':
                    stack.append(turn)
                elif fn == 'ev::Dispos':
                    if args and isinstance(args[0], str):
                        found.append((args[0], cond))
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
                # Reads through the address on top of the stack and keeps it (for `x = x - 4`).
                a = stack[-1] if stack else UNKNOWN
                stack.append(local.get(a[1], UNKNOWN) if isinstance(a, tuple) else UNKNOWN)
            elif name == 'dup':
                stack.append(stack[-1] if stack else UNKNOWN)
            elif name == 'gvar':
                # A call of one of the chapter's own helper handlers. Revelation 26 places each group through one
                # (gvar 0x0c('Reinforce01', x, y)): when the helper places a group, the group named in the call is placed.
                if places_groups(script, raw[0]):
                    group = next((v for v in reversed(stack[-4:]) if isinstance(v, str) and v.startswith(GROUP_PREFIXES)), None)
                    if group:
                        found.append((group, cond))
                stack.append(UNKNOWN)
            elif name == 'assign':
                if len(stack) < 2:
                    return found
                val, addr = stack.pop(), stack.pop()
                if isinstance(addr, tuple):
                    local[addr[1]] = val
                stack.append(val)
            elif name == 'pop':
                if stack:
                    stack.pop()
            elif name in ('eq', 'ne', 'lt', 'le', 'gt', 'ge', 'add', 'sub', 'mul', 'div', 'mod'):
                if len(stack) < 2:
                    return found
                b, a = stack.pop(), stack.pop()
                if a is UNKNOWN or b is UNKNOWN or not isinstance(a, int) or not isinstance(b, int):
                    stack.append(UNKNOWN)
                else:
                    if name in ('div', 'mod') and b == 0:
                        stack.append(UNKNOWN)
                    else:
                        stack.append({'eq': a == b, 'ne': a != b, 'lt': a < b, 'le': a <= b, 'gt': a > b, 'ge': a >= b,
                                      'add': a + b, 'sub': a - b, 'mul': a * b,
                                      'div': a // b if b else 0, 'mod': a % b if b else 0}[name])
            elif name in ('jz', 'jnz'):
                v = stack.pop() if stack else UNKNOWN
                target = pc + 1 + int.from_bytes(raw, 'big', signed=True)
                if v is UNKNOWN and name == 'jz' and pc in seen:
                    nxt = target
                elif v is UNKNOWN:
                    seen = seen | {pc}
                    paths.append((target, list(stack), dict(local), True, seen))
                    nxt, cond = nxt, True
                elif (not v) == (name == 'jz'):
                    nxt = target
            elif name in ('orjump', 'andjump'):
                # Short-circuit || / &&: jump keeping the value if it already decides the result.
                v = stack[-1] if stack else UNKNOWN
                target = pc + 1 + int.from_bytes(raw, 'big', signed=True)
                if v is UNKNOWN:
                    paths.append((target, list(stack), dict(local), True, seen))
                    stack.pop()
                    cond = True
                elif bool(v) == (name == 'orjump'):
                    nxt = target
                else:
                    stack.pop()
            elif name == 'jmp':
                nxt = pc + 1 + int.from_bytes(raw, 'big', signed=True)
            elif name == 'ret':
                break
            else:
                # Anything else (unary ops, unknown opcodes) only affects values we don't track.
                if name.startswith('?') and n == 0 and stack:
                    stack[-1] = UNKNOWN
            pc = nxt
    return found

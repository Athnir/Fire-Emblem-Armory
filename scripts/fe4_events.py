"""
Reads Genealogy of the Holy War's chapter events from the user's ROM: each chapter's event table, the numbered scenes it runs, the
map's castles and villages, the item instances the scripts hand out, and the playable characters' names. Used by build-fe4-maps.py.
How the formats were found is in data-raw/fe4/README.md.

    python scripts/fe4_events.py 0          # the Prologue's event table, with what each scene loads, gives and places

Two interpreters are involved:
  - the event interpreter ($86:83D8): chapter headers, opening scripts and event tables are written in it. Each command handler steps
    past its own operands when entered with carry set ($86:83F0), which `Cpu.script_skip` runs.
  - the scene interpreter ($91:A5E2, handlers at $91:A50A): the numbered scenes (pointers at $8F:E8BF). Its handlers have no skip
    entry, so `scene()` runs each handler on scripts/fe4_cpu.py and reads where it leaves the script position. Calls into other banks
    (graphics, sound, the map) are stepped over; a call to $86:816B runs one event command inline (scene opcodes 0x4A and 0x4D), whose
    length comes from the event interpreter's skip entry.
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_cpu import Cpu, rom_offset  # noqa: E402
from fe4_rom import R, u16  # noqa: E402

SCENES = 0x8FE8BF          # 3-byte pointers to the 562 scenes (the event command 0x30 runs one: `30 [flag] [u16 scene]`)
SCENE_COUNT = 0x232
SCENE_HANDLERS = 0x91A50A  # u16 per scene opcode, 0x00-0x5E
CHAPTER_DATA = 0x86C760    # 3-byte pointer per chapter to its data; its first u16 leads to the map's locations
INSTANCES = 0x3F489        # the item type of each of the 140 item instances the game tracks (the scripts give instances)
INSTANCE_COUNT = 140
NAMES = 0xD920D            # u16 pointers (bank $8D) to the playable characters' names, by the record's name index
NAME_COUNT = 63
PLACE_NAMES = 0xD90B5      # the 46 castle and place names, one after another, each ended by 02 01

# The skip entry of these event commands steps past fewer bytes than running them does: 0x34 reads one operand byte only when run,
# and 0x5F reads two more when its fifth operand byte is 0x0B. Checked by walking every scene to its end.
SKIP_SHORT = {0x34: lambda a: 1, 0x5F: lambda a: 2 if a[5] == 0x0B else 0}

# The kana the game's text uses: one byte per character (FE Games\notes\FE4 Genealogy - notes.md has the table's derivation).
_HIRA = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
_HIRA_V = 'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉっゃゅょ'
_KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン'
_KATA_V = 'ガギグゲゴザジズゼゾダヂヅデドバビブベボヴパピプペポァィゥェォッャュョー'
KANA = {**{0x10 + i: c for i, c in enumerate(_HIRA)}, **{0x3E + i: c for i, c in enumerate(_HIRA_V)},
        **{0x60 + i: c for i, c in enumerate(_KATA)}, **{0x8D + i: c for i, c in enumerate(_KATA_V)}}


def decode(b):
    """Kana text to a string. 0x09 opens the kana page; 0x0A 0x18 is a spacing quirk inside some words."""
    out, i = [], 0
    while i < len(b):
        x = b[i]
        if x == 0x0A and i + 1 < len(b) and b[i + 1] == 0x18:
            i += 2
            continue
        if x != 0x09:
            out.append(KANA.get(x, '?'))
        i += 1
    return ''.join(out)


def place_names():
    """The castle and place names in the ROM's order (a location record's name byte indexes them)."""
    names, o = [], PLACE_NAMES
    while len(names) < 46:
        end = R.index(b'\x02\x01', o)
        names.append(decode(R[o:end]))
        o = end + 2
    return names


def character_name(index):
    """A playable character's name (kana) by the name index in their record (u16 at +0x0F)."""
    p = (NAMES & 0xFF0000) | u16(NAMES + 2 * index)
    return decode(R[p:R.index(b'\x01', p)])


def instance_type(n):
    """The item type (the weapon table's id) of item instance n. Instances count from 1 (Chapter 2's village gives instance 0x87,
    the Bargain Ring Serenes lists there; 0x86 would be the Knight Ring)."""
    return R[INSTANCES + n - 1]


def scene_pointer(n):
    o = rom_offset(SCENES) + 3 * n
    return int.from_bytes(R[o:o + 3], 'little')


class SceneCpu(Cpu):
    def step_scene(self, ptr, y, limit=300000):
        """Runs the scene handler for the command at ptr + y; returns the offset after it."""
        self.ram = bytearray(0x20000)
        for a in range(0x17C4, 0x17CC):  # the four move slots read as free, so movement commands don't wait for one
            self.ram[a] = 0xFF
        self.s, self.d, self.db = 0x1FFF, 0, 0x91
        self.p = 0
        for i, v in enumerate((ptr & 0xFF, ptr >> 8 & 0xFF, ptr >> 16)):
            self.ram[0x30 + i] = v
        op = self.read(ptr + y)
        self.y, self.a = y + 1, op << 1
        self.push16(0xA5F4)  # the dispatcher's return address, less one
        self.pb, self.pc = 0x91, u16(rom_offset(SCENE_HANDLERS) + 2 * op)
        for _ in range(limit):
            if self.pb == 0x91 and self.pc == 0xA5F5:
                return self.y
            if self.read(self.pb << 16 | self.pc) == 0x22:  # JSL
                bank = self.read(self.pb << 16 | (self.pc + 3) & 0xFFFF)
                if bank == 0x86 and self.read16(self.pb << 16 | (self.pc + 1) & 0xFFFF) == 0x816B:
                    start = self.y
                    args = bytes(self.read(self.db << 16 | (start + i) & 0xFFFF) for i in range(8))
                    self.y = Cpu().script_skip(self.db, start) + SKIP_SHORT.get(args[0], lambda a: 0)(args)
                    self.pc = (self.pc + 4) & 0xFFFF
                    continue
                if bank != 0x91:
                    self.pc = (self.pc + 4) & 0xFFFF
                    continue
            self.step()
        raise RuntimeError(f'scene op {op:02X} at {ptr + y:06X} did not return')


# Scene opcodes walked as fixed lengths: 0x01 ends the scene; 0x02 is a jump, 0x03-0x06 conditional jumps (both paths lie inline).
SCENE_FIXED = {0x01: 1, 0x02: 3, 0x03: 3, 0x04: 3, 0x05: 3, 0x06: 3}
INLINE_OPS = (0x4A, 0x4D)  # scene opcodes that run one event command inline (its bytes follow the opcode)


def scene(n):
    """Scene n (see `scene_at`)."""
    return scene_at(scene_pointer(n))


@functools.lru_cache(maxsize=None)
def scene_at(ptr):
    """The scene at SNES address ptr as [(op, operand bytes)] in address order, following its jumps: 0x02 jumps to an address in the scene's bank, 0x03 and
    0x04 jump there or fall through, 0x05 and 0x06 jump by an offset from the operand or fall through. A path ends at 0x01 or 0xFFFF.
    0xFD (end of a step) is left out."""
    n = f'at {ptr:06X}'
    base = ptr & 0xFFFF
    cpu, seen, todo = SceneCpu(), {}, [0]
    while todo:
        y = todo.pop()
        while y not in seen:
            w = cpu.read16(ptr + y)
            if w == 0xFFFF:
                break
            if w == 0xFEFE:
                y += 2
                continue
            op = w & 0xFF
            if op == 0xFD:
                y += 1
                continue
            ny = y + SCENE_FIXED[op] if op in SCENE_FIXED else cpu.step_scene(ptr, y)
            if ny <= y:
                raise RuntimeError(f'scene {n} stalls at +{y:X}')
            args = bytes(cpu.read(ptr + i) for i in range(y + 1, ny))
            seen[y] = (op, args)
            if op == 0x01:
                break
            if op in (0x02, 0x03, 0x04):
                todo.append((args[0] | args[1] << 8) - base)
                if op == 0x02:
                    break
            elif op in (0x05, 0x06):
                todo.append((y + 1 + (args[0] | args[1] << 8)) & 0xFFFF)
            y = ny
        if len(seen) > 5000:
            raise RuntimeError(f'scene {n} has no end')
    return [seen[y] for y in sorted(seen)]


def scene_commands(n):
    """The event commands scene n runs inline: [(event op, operand bytes)]."""
    return [(a[0], a[1:]) for op, a in scene(n) if op in INLINE_OPS and a]


def action_scene(action):
    """The scene an event action runs, as [(op, operand bytes)], or []: `30 [flag] [u16 n]` runs scene n; `31 [flag] [pointer] [x]` and
    `32 [flag] [pointer] [u16]` show text (battle quotes), not a scene."""
    if not action:
        return []
    op, a = action
    if op == 0x30:
        return scene(a[1] | a[2] << 8)
    return []


def loaded_lists(chapter):
    """Every unit list the chapter's scripts load: the opening script and the scenes it runs, every trigger's and every block's."""
    bank, opening, _ = chapter_headers()[chapter]
    out = set()
    for _, op, a in script(bank, opening):
        if op == 0x4A:
            out.add(a[0])
        out |= set(action_lists((op, a)))
    triggers, blocks = event_table(chapter)
    for t in triggers:
        out |= set(action_lists(t['action']))
    for b in blocks:
        out |= set(action_lists((b['op'], b['args'])))
    return out


def action_gifts(action):
    """The items an action's scene hands over: [(unit id, item instance)] from `57` and `58 [unit u16][instance]` (0xFFFF: the unit
    that triggered it)."""
    return [(a[1] | a[2] << 8, a[3]) for op, a in action_scene(action) if op in INLINE_OPS and a[:1] in (b'W', b'X')]


def action_lists(action):
    """The unit lists the scene of an action loads (inline `4A nn`)."""
    return [a[1] for op, a in action_scene(action) if op in INLINE_OPS and a[:1] == b'J']


def script(bank, y, stop_ffff=True):
    """Event-interpreter commands from bank:y up to 0xFFFF: [(address, op, operand bytes)]."""
    cpu, out = Cpu(), []
    for _ in range(4000):
        o = rom_offset(bank << 16 | y)
        if u16(o) == 0xFFFF:
            return out
        ny = cpu.script_skip(bank, y)
        out.append((y, R[o], bytes(R[o + 1:o + (ny - y)])))
        y = ny
    raise RuntimeError(f'script at {bank:02X}:{y:04X} has no end')


def chapter_headers():
    """{chapter: (bank, opening script, event table)}: each chapter's 8-byte header `[chapter u16][opening][event table]` (3-byte
    pointers), found by its self-reference (the opening script follows the header)."""
    found = {}
    for o in range(len(R) - 8):
        n = R[o]
        if n <= 11 and R[o + 1] == 0:
            p1 = R[o + 2] | R[o + 3] << 8
            b1 = R[o + 4]
            p2 = R[o + 5] | R[o + 6] << 8
            if R[o + 7] == b1 and b1 >= 0x80 and (b1 & 0x3F) == o >> 16 and p1 == (o & 0xFFFF) + 8 and p1 < p2 < p1 + 0x4000:
                found[n] = (b1, p1, p2)
    assert sorted(found) == list(range(12)), sorted(found)
    return found


def locations(chapter):
    """The map's castles and villages: [(id, kind, name index, x, y)] with kind 0 castle, 2 village (x, y from the top left)."""
    o = rom_offset(CHAPTER_DATA) + 3 * chapter
    p = int.from_bytes(R[o:o + 3], 'little')
    bank = p & 0xFF0000
    table = rom_offset(bank | u16(rom_offset(p)))
    out = []
    for i in range(R[table]):
        q = rom_offset(bank | u16(table + 1 + 2 * i))
        out.append((R[q], R[q + 2], R[q + 1], R[q + 3], R[q + 4]))
    return out


def location_record(chapter, lid):
    """A location's raw record: castles are 8 bytes, `[id][name][kind][x][y][?][u16 pointer]`; villages 5."""
    o = rom_offset(CHAPTER_DATA) + 3 * chapter
    p = int.from_bytes(R[o:o + 3], 'little')
    bank = p & 0xFF0000
    table = rom_offset(bank | u16(rom_offset(p)))
    for i in range(R[table]):
        q = rom_offset(bank | u16(table + 1 + 2 * i))
        if R[q] == lid:
            return bank, R[q:q + 8]
    raise KeyError((chapter, lid))


def shop_stock(chapter):
    """The home castle's shop: the item instances behind its record's pointer, up to 0xFF (each instance is one item for sale).
    Checked against Serenes' item-locations page: Chapter 1 sells the Slim Sword, Iron Lance, Javelin and Steel Axe."""
    bank, rec = location_record(chapter, 0)
    ptr = rec[6] | rec[7] << 8
    if not ptr:
        return []
    o = rom_offset(bank | ptr)
    out = []
    while R[o] != 0xFF:
        out.append(R[o])
        o += 1
    return out


# Event-table conditions: opcode -> (the trigger kind the game raises, how many u16 arguments follow the flag byte).
# Kinds read from where the game raises them (STA $0EBC): 1 an army seizes a castle (army, castle); 3 a unit enters an area
# (unit, x1 y1, x2 y2 as bytes); 9 a unit visits a location (unit, location); 0x0A one unit talks to another (from, to, -);
# 0x17 a unit dies (unit); 0x14 a battle between two units (both orders); 6 a unit enters a castle (unit, location: Levin into
# Silesia, Yuria into Velthomer); the rest aren't needed for the page yet. Opcodes 0x15 and 0x16 are talks too (kind 0x0A, two units).
TRIGGERS = {
    0x01: (0x20, 1), 0x02: (0x01, 2), 0x03: (0x02, 2), 0x04: (0x0A, 3), 0x05: (0x04, 2), 0x06: (0x05, 2), 0x07: (0x06, 2),
    0x08: (0x07, 2), 0x09: (0x08, 2), 0x0A: (0x09, 2), 0x0B: (0x03, None), 0x0D: (0x14, 4), 0x0F: (0x17, 2), 0x10: (0x11, 2),
    0x15: (0x0A, 2), 0x16: (0x0A, 2),
    0x1A: (0x18, 2), 0x1C: (0x1A, 2), 0x1D: (0x1B, 1), 0x1F: (0x1D, 2),
}


def event_table(chapter):
    """A chapter's event table, read as the game runs it.

    Returns (triggers, blocks):
      triggers: [{'op', 'flag', 'args', 'action'}] - the once-per-check conditions before `20 66 66`; the first that holds runs its
        action and ends the check. flag < 0x80 marks it done (and sets that flag) when it fires; 0x80 + n requires flag n; 0xFF none.
      blocks: [{'turn': (turn, phase, a, b) or None, 'flags': [(test, [flags])], 'op', 'args'}] - every command after `20 66 66`, with
        the conditions it sits under: `21 turn phase a b` opens a block on the turn and phase (0xFF any) closed by `25 66 66`; flag tests
        (29 n set, 2A n clear, 2C all set, 2D any set) open one closed by `2E 66 66`.
    """
    bank, _, table = chapter_headers()[chapter]
    cmds = script(bank, table)
    triggers, blocks = [], []
    i = 0
    while i < len(cmds):
        _, op, a = cmds[i]
        if op == 0x20:
            i += 1
            break
        if op in TRIGGERS or op in (0x0C, 0x0E, 0x11, 0x12, 0x13, 0x14, 0x17, 0x18, 0x19, 0x1B, 0x1E):
            action = cmds[i + 1] if i + 1 < len(cmds) else None
            triggers.append({'op': op, 'flag': a[0], 'args': a[1:], 'action': (action[1], action[2]) if action else None})
            i += 2
        else:
            raise ValueError(f'chapter {chapter}: unexpected {op:02X} in the trigger list')
    turn, flags = None, []
    for _, op, a in cmds[i:]:
        if op in (0x21, 0x22, 0x23, 0x24):
            turn = (op, tuple(x - 256 if x > 127 else x for x in a[:4])) if op == 0x21 else (op, tuple(a))
            flags = []
        elif op == 0x25:
            turn, flags = None, []
        elif op in (0x29, 0x2A):
            flags.append(('set' if op == 0x29 else 'clear', [a[0]]))
        elif op in (0x2C, 0x2D):
            flags.append(('all set' if op == 0x2C else 'any set', list(a[:-1])))
        elif op in (0x2E, 0x2F):
            flags = []
        else:
            blocks.append({'turn': turn, 'flags': list(flags), 'op': op, 'args': a})
    return triggers, blocks



def flag_setters(triggers, blocks):
    """{flag: [what sets it]}: a trigger whose flag byte is under 0x80 sets it when it fires; so does a scene run with that flag byte
    (event command 0x30), and command 0x27 in a block."""
    out = {}

    def scene_flags(action):
        """Flags the scene an action runs sets itself (scene opcode 0x4B: [1][flag], the chapter's flags)."""
        return [a[1] for op, a in action_scene(action) if op == 0x4B and a[0] == 1]

    for t in triggers:
        if t['flag'] < 0x80:
            out.setdefault(t['flag'], []).append(('trigger', t))
        if t['action'] and t['action'][0] in (0x30, 0x31, 0x32) and t['action'][1][0] < 0x80:
            out.setdefault(t['action'][1][0], []).append(('trigger', t))
        if t['action'] and t['action'][0] == 0x27:  # the action sets a flag itself (Chapter 5: talking to Arvis sets the ambush's)
            out.setdefault(t['action'][1][0], []).append(('trigger', t))
        for f in scene_flags(t['action']):
            out.setdefault(f, []).append(('trigger', t))
    for b in blocks:
        if b['op'] == 0x27 or (b['op'] in (0x30, 0x31, 0x32) and b['args'][0] < 0x80):
            out.setdefault(b['args'][0], []).append(('block', b))
        for f in scene_flags((b['op'], b['args'])):
            out.setdefault(f, []).append(('block', b))
    return out


class Describer:
    """Puts a chapter's event conditions into words. `unit(id)` names a unit, `place(location id)` names a castle or village, and
    `army(n)` names an army ('your army', 'the enemy', ...)."""

    def __init__(self, chapter, unit, place, army, group=lambda lists: None, tile=lambda x, y: (x, y), phase=None):
        self.triggers, self.blocks = event_table(chapter)
        self.setters = flag_setters(self.triggers, self.blocks)
        self.unit, self.place, self.army, self.group, self.tile = unit, place, army, group, tile
        self.phase = phase or (lambda n: 'your phase' if n == 0 else f'the phase of {army(n)}')

    def trigger(self, t):
        """A trigger's condition, as a clause ('you seize Jungby'), or None when the kind isn't put into words."""
        a = t['args']
        w = [a[i] | a[i + 1] << 8 for i in range(0, len(a) - 1, 2)]
        op = t['op']
        if op == 0x02:
            return f'you seize {self.place(w[1])}' if w[0] == 0 else f'{self.army(w[0])} seizes {self.place(w[1])}'
        if op in (0x04, 0x15, 0x16):
            who = 'anyone' if w[0] == 0xFFFF else self.unit(w[0])
            return f'{who} talks to {self.unit(w[1])}'
        if op == 0x0F:
            return f'{self.unit(w[0])} is defeated' if w[0] != 0xFFFF else None
        if op == 0x0A:
            who = 'anyone' if w[0] == 0xFFFF else self.unit(w[0])
            return f'{who} visits {self.place(w[1])}'
        if op == 0x07:
            who = 'anyone' if w[0] == 0xFFFF else self.unit(w[0])
            return f'{who} enters {self.place(w[1])}'
        if op == 0x0B:
            who = 'anyone' if w[0] == 0xFFFF else self.unit(w[0])
            return f'{who} reaches {self.area(a[2:6])}'
        return None

    def area(self, b):
        """An area given as [x1, y1, x2, y2] (from the top left), in the page's coordinates."""
        (x1, y1), (x2, y2) = self.tile(b[0], b[1]), self.tile(b[2], b[3])
        if (x1, y1) == (x2, y2):
            return f'tile ({x1}, {y1})'
        return f'the area ({min(x1, x2)}, {min(y1, y2)})-({max(x1, x2)}, {max(y1, y2)})'

    def flags(self, conds, depth=0):
        """Flag tests as clauses, or None if one can't be put into words."""
        out = []
        for test, flags in conds:
            parts = [self.flag(f, depth) for f in flags]
            if any(p is None for p in parts):
                return None
            if test == 'set':
                out.append(parts[0])
            elif test == 'clear':
                out.append('not yet: ' + parts[0])
            elif test == 'all set':
                out.append(' and '.join(parts))
            else:
                out.append(' or '.join(parts))
        return out

    def flag(self, f, depth):
        """What sets flag f, as a clause (alternatives joined by 'or'), or None."""
        if depth > 3 or f not in self.setters:
            return None
        parts = []
        for kind, x in self.setters[f]:
            action = x['action'] if kind == 'trigger' else (x['op'], x['args'])
            lists = action_lists(action)
            arrives = self.group(lists) if lists else None
            if arrives:
                c = arrives
            elif kind == 'trigger':
                c = self.trigger(x)
            else:
                c = self.when(x, depth + 1, as_flag=True)
            if c is None:
                return None
            if c not in parts:
                parts.append(c)
        return ' or '.join(parts)

    def turn(self, turn):
        if turn is None:
            return None
        op, (n, phase, _, _) = turn
        if op != 0x21:
            return None
        side = self.phase(phase)
        return f'turn {n}, at the start of {side}' if n >= 0 else f'at the start of {side}'

    def when(self, block, depth=0, as_flag=False):
        """A block command's conditions as one clause, or None. As a flag's cause, a phase start that waits on other events is
        described by those events alone (it follows them at the next phase)."""
        t = self.turn(block['turn'])
        if block['turn'] is not None and t is None:
            return None
        if as_flag and block['turn'] and block['turn'][1][0] < 0 and block['flags']:
            t = None
        f = self.flags(block['flags'], depth)
        if f is None:
            return None
        clauses = [c for c in f if not c.startswith('not yet: ')]
        if t and clauses:
            return f'{t} after {" and ".join(clauses)}'
        if t:
            return t
        return ' and '.join(clauses) if clauses else None



if __name__ == '__main__':
    ch = int(sys.argv[1])
    trig, blocks = event_table(ch)
    for t in trig:
        act = t['action']
        line = f"{t['op']:02X} flag {t['flag']:02X} {t['args'].hex(' ')} -> {act[0]:02X} {act[1].hex(' ')}" if act else ''
        if act and act[0] == 0x30:
            line += '  ' + ' | '.join(f'{o:02X} {x.hex(" ")}' for o, x in scene_commands(act[1][1] | act[1][2] << 8))
        print(line)
    print('--')
    for b in blocks:
        line = f"{b['turn']} {b['flags']} {b['op']:02X} {b['args'].hex(' ')}"
        if b['op'] == 0x30:
            line += '  ' + ' | '.join(f'{o:02X} {x.hex(" ")}' for o, x in scene_commands(b['args'][1] | b['args'][2] << 8))
        print(line)

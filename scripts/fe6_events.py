"""
The Binding Blade's chapter events, read from the user's clean Japanese ROM (scripts/fe6_rom.py): the event lists of each chapter, the
event scripts split into commands, and a small interpreter that plays a script the way the game's event engine does, so the generators
know which units a chapter places and where they stand once its opening is over. Formats are in data-raw/fe6/README.md.

What the engine does was read in the program code (Thumb, capstone):
  - Event lists are 12-byte entries ended by a 0 type: u16 type, u16 flag, u32 script (or argument), then 4 bytes the type reads.
    The checks per type are a table at 0x08666114 (check routine, size in words). The flag is set once the event runs; 0 means it
    can run again.
      1 the flag in bytes 8-9 is set; 2 a turn: from byte 8 to byte 9 (0: just that turn), phase byte 10 (0x00 player, 0x40 other,
      0x80 enemy); 3 the same, only on Hard (0x0806A9DC: the chapter state's Hard bit, 0x0202AA48+0x14 & 0x40) and only while
      flag 2 is clear; 4 two characters talk (bytes 8, 9); 5-10 a tile (bytes 8, 9) and a command (byte 10): 5 a house or a seize
      tile, 6 a village, 7 a chest, 8 a door, 10 a shop; 11 an area (bytes 8-11: x1, y1, x2, y2); 13 a check routine (bytes 8-11).
  - Script commands (u32 words) have a handler and a length in words at 0x085C4164. The ones the generators follow:
      0x00 end of the script data; 0x01 stop; 0x1B label; 0x1C goto; 0x1F / 0x20 goto if a check routine returns non-zero / zero;
      0x21 goto if the scene is being skipped; 0x22 / 0x23 goto if a flag is set / clear; 0x24 goto if the acting unit is a character;
      0x12 / 0x13 load a unit group (0x13: your army, onto the group's tiles); 0x0D move the unit on a tile to another; 0x0F move a
      character to a tile; 0x10 move a character along a path; 0x30 remove a character; 0x2B change a character's side;
      0x26 give the acting unit an item; 0x27 give a character an item; 0x28 give gold; 0x2A apply the map change at a tile
      (x in the low byte, y in the next: a village closing, 0x0800FCF8); 0x34 / 0x35 set / clear a flag; 0x3D go to a chapter.
    A goto to a label that isn't in the script does nothing (0x0800F73C searches up to the 0x00 end).
  - A tile is a u32: x in the low half, y in the high half, counted from the top-left at (0, 0).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe6_rom import CHAPTERS, EVENT_COMMANDS, POINTERS, R, off, u16, u32  # noqa: E402

CHAPTER_STATE = 0x0202AA48
UNIT_AT = 0x0806ACEC       # any of your units (ids 1-63, not hidden) inside x1..x2, y1..y2
IN_ARMY = 0x0806C07C       # the character is one of your units, alive and in the army
ALIVE = 0x0806C168         # the character is one of your units and alive
TALK_CHECK = 0x0806AC90    # a coded talk: the two characters in r1 and r2
IS_HARD = 0x0806BAA1
GOLD = 0x08020A58          # your gold


def chapter_record(n):
    return CHAPTERS + 68 * n


def events_of(n):
    """The chapter's event data: its list pointers by name. 'enemies' is the group the chapter starts with (placed before the
    turn-1 events), 'army' your army's group (its tiles are where you deploy)."""
    e = chapter_record(n)
    base = off(u32(POINTERS + 4 * R[e + 0x3E]))
    slots = [u32(base + 4 * i) for i in range(7)]
    return {'turn': slots[0], 'talk': slots[1], 'location': slots[2], 'misc': slots[3], 'enemies': slots[4], 'army': slots[5],
            'end': slots[6]}


def event_list(ptr):
    """12-byte events up to a 0 type."""
    o, out = off(ptr), []
    while u16(o):
        b = R[o:o + 12]
        out.append({'type': u16(o), 'flag': u16(o + 2), 'ptr': u32(o + 4), 'b': b[8:12], 'at': o})
        o += 12
    return out


def command_length(op):
    return u32(EVENT_COMMANDS + op * 8 + 4)


def script(ptr):
    """A script split into (offset, opcode, args) up to the 0x00 end of its data."""
    a, out = off(ptr), []
    while True:
        op = u32(a)
        assert op < 0x64, f'not a script at {a:#x}'
        n = command_length(op)
        out.append((a, op, [u32(a + 4 * k) for k in range(1, n)]))
        a += 4 * n
        if op == 0:
            return out


def tile(v):
    """A script tile word as (x, y) from the top-left."""
    return v & 0xFFFF, v >> 16


def unit_group(ptr):
    """16-byte unit records up to an all-zero one."""
    o, out = off(ptr), []
    while R[o:o + 16] != bytes(16):
        f = R[o + 3]
        out.append({'char': R[o], 'class': R[o + 1], 'level': f >> 3, 'side': ('player', 'npc', 'enemy', 'enemy')[(f >> 1) & 3],
                    'start': (R[o + 4], R[o + 5]), 'end': (R[o + 6], R[o + 7]), 'items': [x for x in R[o + 8:o + 12] if x],
                    'ai': R[o + 12:o + 16]})
        o += 16
    return out


def thumb(addr, n=40):
    """The Thumb instructions of a short routine, as (address, mnemonic, operands)."""
    from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    o = (addr & ~1) - 0x08000000
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(R[o:o + n * 2], addr & ~1)][:n]


def _imm(op):
    return int(op.split('#')[1], 0)


def check(addr):
    """What a check routine tests, read from its code: ('hard',), ('alive', char), ('in_army', char), ('turn_over', n),
    ('phase', p), ('units_in', phase, [rects], negated), ('talk', a, b), or ('code', addr) when it does something else."""
    if addr == IS_HARD:
        return ('hard',)
    ins = thumb(addr, 30)
    calls = [i for i, x in enumerate(ins) if x[1] == 'bl']
    # movs r0, #c; bl ALIVE / IN_ARMY
    if len(calls) >= 1 and ins[1][1] == 'movs' and ins[1][2].startswith('r0') and ins[calls[0]][2] in (f'#{ALIVE:#x}', f'#{IN_ARMY:#x}'):
        return ('alive' if ins[calls[0]][2] == f'#{ALIVE:#x}' else 'in_army', _imm(ins[1][2]))
    # ldr r0, =state; ldrh r0, [r0, #0x10]; cmp r0, #n; bhi -> 1: the turn is past n
    if ins[1][1] == 'ldrh' and ins[1][2].endswith('#0x10]') and ins[2][1] == 'cmp' and ins[3][1] == 'bhi':
        return ('turn_over', _imm(ins[2][2]))
    # bl GOLD; ldr r1, =n; cmp r0, r1; ble -> 0: you hold more than n gold
    if calls and calls[0] == 1 and ins[1][2] == f'#{GOLD:#x}' and ins[2][1] == 'ldr' and ins[3][1] == 'cmp':
        lit = ((ins[2][0] + 4) & ~3) + int(ins[2][2].split('#')[1].rstrip(']'), 0)
        return ('gold_over', u32(lit - 0x08000000))
    # ldrb r0, [state, #0xf]; cmp r0, #p; bne 0 -> the phase is p
    if ins[1][1] == 'ldrb' and ins[1][2].endswith('#0xf]') and ins[2][1] == 'cmp' and ins[3][1] == 'bne' and len(calls) == 0:
        return ('phase', _imm(ins[2][2]))
    # A coded talk: movs r1, #a; movs r2, #b; bl TALK_CHECK
    for i in calls:
        if ins[i][2] == f'#{TALK_CHECK:#x}':
            a, b = _imm(ins[i - 2][2]), _imm(ins[i - 1][2])
            return ('talk', a, b)
    # Phase check, then UNIT_AT calls with immediate rectangles: fires when (not) any of your units stands in them.
    rects = []
    for i in calls:
        if ins[i][2] == f'#{UNIT_AT:#x}':
            regs = {}
            for j in range(i - 1, i - 5, -1):
                if ins[j][1] == 'movs' and ins[j][2][:2] in ('r0', 'r1', 'r2', 'r3'):
                    regs.setdefault(ins[j][2][:2], _imm(ins[j][2]))
            rects.append((regs['r0'], regs['r1'], regs['r2'], regs['r3']))
    if rects:
        phase = None
        if ins[1][1] == 'ldr' and ins[2][1] == 'ldrb' and ins[2][2].endswith('#0xf]') and ins[3][1] == 'cmp':
            phase = _imm(ins[3][2])
        # Returns 1 when the call returned 0 (bne past "movs r0, #1"): no unit in the area.
        after = ins[calls[0] + 1:calls[0] + 6]
        negated = any(x[1] == 'bne' for x in after) and any(x[1] == 'movs' and x[2] == 'r0, #1' for x in after)
        return ('units_in', phase, rects, negated)
    return ('code', addr)


class Run:
    """Plays one script. `world` answers what the script asks: hard (bool), alive(char) -> bool, flags (set), active (char or None),
    skipping (bool). Collects the unit groups it loads (with the tiles units end on once the scripted moves are done), gifts and the
    chapter it goes to."""

    def __init__(self, world, units=None):
        self.world = world
        self.units = units if units is not None else []    # dicts from unit_group, with 'tile' (where it stands now) and 'group'
        self.loads = []
        self.items = []         # (item, who): who is a character id, or None for the acting unit
        self.gold = []
        self.next_chapter = None
        self.recruits = []      # characters switched to your side
        self.removed = []
        self.flags_set = []
        self.checks = []        # every check met on the way, with its outcome
        self.map_changes = []   # tiles (x, y) whose map change the script applies

    def unit_of(self, char):
        return next((u for u in self.units if u['char'] == char), None)

    def run(self, ptr, limit=5000):
        cmds = script(ptr)
        labels = {args[0]: k for k, (_, op, args) in enumerate(cmds) if op == 0x1B}
        k = 0
        for _ in range(limit):
            a, op, args = cmds[k]
            jump = None
            if op in (0x00, 0x01):
                return self
            if op == 0x1C:
                jump = args[0]
            elif op in (0x1F, 0x20):
                c = check(args[1])
                v = self.world.answer(c)
                self.checks.append((c, v))
                if (op == 0x1F) == bool(v):
                    jump = args[0]
            elif op == 0x21:
                if self.world.skipping:
                    jump = args[0]
            elif op in (0x22, 0x23):
                v = args[1] in self.world.flags
                if (op == 0x22) == v:
                    jump = args[0]
            elif op == 0x24:
                if self.world.active == args[1]:
                    jump = args[0]
            elif op in (0x12, 0x13):
                group = unit_group(args[0])
                self.loads.append((op, args[0], group))
                for u in group:
                    self.units.append({**u, 'tile': u['end'], 'group': args[0], 'army': op == 0x13})
            elif op == 0x0D:
                src, dst = tile(args[0]), tile(args[1])
                u = next((u for u in self.units if u['tile'] == src), None)
                if u:
                    u['tile'] = dst
            elif op == 0x0F:
                u = self.unit_of(args[0])
                if u:
                    u['tile'] = tile(args[1])
            elif op == 0x10:
                u = self.unit_of(args[0])
                if u:
                    u['tile'] = walk(u['tile'], args[1])
            elif op == 0x30:
                u = self.unit_of(args[0])
                if u:
                    self.units.remove(u)
                    self.removed.append(args[0])
            elif op == 0x2B:
                if args[1] == 0:
                    self.recruits.append(args[0])
                u = self.unit_of(args[0])
                if u:
                    # The side is the top bits of a unit's id: 0 yours, 0x40 another army's, 0x80 the enemy's.
                    u['side'] = ('player', 'npc', 'enemy', 'enemy')[args[1] >> 6 & 3]
            elif op == 0x26:
                self.items.append((args[0], None))
            elif op == 0x27:
                self.items.append((args[1], args[0]))
            elif op == 0x28:
                self.gold.append(args[0])
            elif op == 0x2A:
                self.map_changes.append((args[0] & 0xFF, args[0] >> 8 & 0xFF))
            elif op == 0x34:
                self.flags_set.append(args[0])
                self.world.flags.add(args[0])
            elif op == 0x35:
                self.world.flags.discard(args[0])
            elif op == 0x3D:
                self.next_chapter = args[0]
            if jump is not None and jump in labels:
                k = labels[jump]
            else:
                k += 1
        raise RuntimeError(f'script at {ptr:#x} did not end')


def walk(start, path_ptr):
    """A movement path (0x10): direction bytes (0 left, 1 right, 2 down, 3 up), 0x0C then a speed byte, ended by 4; returns the
    last tile."""
    x, y = start
    o = off(path_ptr)
    while R[o] != 4:
        if R[o] == 0x0C:
            o += 2
            continue
        assert R[o] < 4, f'path byte {R[o]:#x} at {o:#x}'
        dx, dy = ((-1, 0), (1, 0), (0, 1), (0, -1))[R[o]]
        x, y = x + dx, y + dy
        o += 1
    return x, y


class World:
    """The state a script runs in: by default turn 1, your phase, everyone alive and in the army, no flags set."""

    def __init__(self, hard=False, dead=(), flags=(), active=None, turn=1, phase=0, skipping=False, units_in=False):
        self.hard = hard
        self.dead = set(dead)
        self.flags = set(flags)
        self.active = active
        self.turn = turn
        self.phase = phase
        self.skipping = skipping
        self.units_in = units_in

    def answer(self, c):
        kind = c[0]
        if kind == 'hard':
            return self.hard
        if kind in ('alive', 'in_army'):
            return c[1] not in self.dead
        if kind == 'turn_over':
            return self.turn > c[1]
        if kind == 'phase':
            return self.phase == c[1]
        if kind == 'units_in':
            return (not self.units_in) if c[3] else self.units_in
        return False


def pack(v):
    return struct.pack('<I', v)

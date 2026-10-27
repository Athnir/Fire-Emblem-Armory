"""
The Blazing Blade's chapter events, read from the user's (U) ROM (scripts/gba_rom.py): the event lists of each chapter, the event
scripts split into commands, and a small interpreter that plays a script the way the game's event engine does, so the generators know
which units a chapter places and where they stand once its opening is over. The engine grew out of The Binding Blade's
(scripts/fe6_events.py): the same 16-byte units, scripts of u32 words with the opcode in the low byte, labels found anywhere in the
script; but every opcode is renumbered and the story's modes (Lyn's, Eliwood's and Hector's) and Hard mode are checked throughout.
Formats are in data-raw/fe7/README.md.

What the engine does was read in the program code (Thumb, capstone):
  - The event data (the chapter record's +0x78, through the pointer table) has 16 pointers: turn, talk, location and misc events;
    the traps for Lyn's and Eliwood's story / Hector's; the enemies a chapter with preparations starts with, for Eliwood Normal,
    Eliwood Hard, Hector Normal and Hector Hard (0x08079214); your army's deploy tiles in the same order (0x08079280); the opening
    and the ending scenes.
  - The mode is the chapter state's byte 0x1B (1 Lyn, 2 Eliwood, 3 Hector); Hard is bit 0x40 of its byte 0x14.
  - Event lists are entries ended by a 0 type, each as long as its type says (the check table at 0x08C9E9A4: routine, size in
    words). The flag at +2 is set once the event runs.
      1 a flag (u16 at +8) is set; 2 a turn: from byte 8 to byte 9 (0: just that turn), phase byte 10, and a condition at +0xC
      (0 none; 1 Eliwood Normal, 2 Hector Normal, 3 Eliwood Hard, 4 Hector Hard, 5 Hard; the conditioned ones also need flag 2
      clear); 3 two characters talk (bytes 8, 9; +0xC: 0 always, 1 Eliwood's story, 2 Hector's, 3 once the flag in the high half
      is set); 4 a talk with a check routine at +0xC; 5-10 a tile (bytes 8, 9) and a command (byte 10): 0x0E a house or village,
      0x0F seize, 0x10 a door, 0x12 a chest (the item at +4, gold at +6), 0x13 / 0x14 / 0x15 an armory, vendor, secret shop (the
      script word points at a u16 item list); 11 an area (bytes 8-11: x1, y1, x2, y2); 12 / 13 the same in Eliwood's / Hector's
      story only; 14 a check routine (+8); 15 / 16 once the flag at +0xC is set.
  - Script commands (u32 words; the opcode is the low byte, some take an argument in the high half) have a handler and a length
    in words at 0x08B90E48. The ones the generators follow:
      0x00 / 0x01 end; 0x44 label; 0x45 goto; 0x46 goto unless a character is alive; 0x47 goto unless a character is in your army;
      0x48 / 0x49 goto if a check routine returns non-zero / zero; 0x4A goto if the scene is being skipped; 0x4C / 0x4D goto if a
      flag is set / clear; 0x4E goto if the acting unit is (high half set) or isn't a character; 0x4F / 0x50 goto in Eliwood's /
      Hector's story; 0x51 goto on Hard (high half set) or on Normal; 0x59 / 0x5A skip the next n commands (the high half) if a
      check routine returns non-zero / zero (the event loop, 0x0800B454);
      0x32 load a unit group; 0x33 the same, leaving out characters who are dead; 0x34 load it in one story (low byte) and, with
      the high half set, only on Hard; 0x35 load one of four groups by mode and difficulty (Eliwood Normal, Eliwood Hard, Hector
      Normal, Hector Hard); 0x36-0x38 the same three for your army, onto the group's tiles;
      0x3E-0x42 call a routine (the ones that clear the map are followed: CLEAR_OTHERS and the rest below);
      0x23 / 0x24 move the unit on a tile to another; 0x25 move it along a path; 0x26 / 0x27 / 0x2B / 0x2F move a character to a
      tile; 0x28 / 0x2C along a path; 0x29 to another character's tile; 0x65 change a character's side; 0x6A-0x6F remove a unit
      (by tile or character); 0x5B give the acting unit an item; 0x5C give a character an item; 0x5E give gold; 0x5F-0x64 apply a
      map change (its id in the high half); 0x76 / 0x77 set / clear a flag (the high half); 0x81 go to a chapter (the high half).
  - A tile is a u32: x in the low half, y in the high half, counted from the top-left at (0, 0).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gba_rom import rom  # noqa: E402

ROM = rom('fe7')
R = ROM.R
u8, u16, u32, off = ROM.u8, ROM.u16, ROM.u32, ROM.off

EVENT_COMMANDS = 0xB90E48
CHECKS = 0xC9E9A4
CHAPTER_STATE = 0x0202BBF8
IN_ARMY = 0x08079D40          # the character is one of your units and alive
ANY_ENEMY = 0x08079F7C        # any enemy unit is alive
NO_ENEMY = 0x08079FE9         # no enemy unit is left
LYN_PLAYED = 0x0807A3B9       # the chapter state's byte 0x2B bit 0
PLAYER_PHASE = 0x0807A2F1
# Routines a script calls (0x3E-0x42) that take units off the map: every unit that isn't yours (0x41-0xBF), only the enemies
# (0x81-0xBF), or everyone (yours stay in the army, off the map: x 0xFF and hidden).
CLEAR_OTHERS, CLEAR_ENEMIES, CLEAR_ALL = 0x0807A869, 0x0807A891, 0x0807A8B9
# Routines a script calls that hand a unit an item: 0x0807DBF5 finds Athos's unit (0x08017D34), makes a Sol Katti (0x08016174) and adds
# it to his items (0x08017654), in the Final Chapter's opening. routine -> (item, character)
ROUTINE_GIFTS = {0x0807DBF5: (0x8C, 0x27)}
MODES = {'Lyn': 1, 'Eliwood': 2, 'Hector': 3}


def chapter_record(n):
    return ROM.chapter(n)


def events_of(n):
    """The chapter's event data: its list pointers by name."""
    base = ROM.pointer(R[chapter_record(n) + 0x78])
    s = [u32(base + 4 * i) for i in range(16)]
    return {'turn': s[0], 'talk': s[1], 'location': s[2], 'misc': s[3], 'traps': s[4], 'traps_hector': s[5],
            'enemies': s[6:10], 'army': s[10:14], 'opening': s[14], 'end': s[15]}


def group_slot(mode, hard):
    """Which of the four groups (Eliwood Normal, Eliwood Hard, Hector Normal, Hector Hard) a mode and difficulty takes. Lyn's story
    takes Eliwood's (0x08079214 tests only for Hector)."""
    return (2 if mode == 'Hector' else 0) + (1 if hard else 0)


def event_size(t):
    return 4 * u32(CHECKS + 8 * t + 4) if t < 17 else 12


def event_list(ptr):
    """Entries up to a 0 type, each as long as its type."""
    o, out = off(ptr), []
    while u16(o):
        t = u16(o)
        n = event_size(t)
        b = R[o:o + n]
        out.append({'type': t, 'flag': u16(o + 2), 'ptr': u32(o + 4), 'b': b[8:n], 'at': o})
        o += n
    return out


def command_length(op):
    return u32(EVENT_COMMANDS + op * 8 + 4)


def script(ptr):
    """A script split into (offset, opcode, word, args) up to its 0 word."""
    a, out = off(ptr), []
    while True:
        w = u32(a)
        op = w & 0xFF
        assert op < 0xE8, f'not a script at {a:#x}'
        n = command_length(op)
        out.append((a, op, w, [u32(a + 4 * k) for k in range(1, n)]))
        a += 4 * n
        if w == 0:
            return out


def tile(v):
    """A script tile word as (x, y) from the top-left."""
    return v & 0xFFFF, v >> 16


def unit_group(ptr):
    """16-byte unit records up to one with character 0 (the loader at 0x0800D01C stops there)."""
    o, out = off(ptr), []
    while R[o]:
        f = R[o + 3]
        out.append({'char': R[o], 'class': R[o + 1], 'level': f >> 3, 'side': ('player', 'npc', 'enemy', 'enemy')[(f >> 1) & 3],
                    'start': (R[o + 4], R[o + 5]), 'end': (R[o + 6], R[o + 7]), 'items': [x for x in R[o + 8:o + 12] if x],
                    'ai': R[o + 12:o + 16]})
        o += 16
    return out


def thumb(addr, n=40):
    from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    o = (addr & ~1) - 0x08000000
    return [(i.address, i.mnemonic, i.op_str) for i in md.disasm(R[o:o + n * 2], addr & ~1)][:n]


def _imm(op):
    return int(op.split('#')[1], 0)


def check(addr):
    """What a check routine tests, read from its code: ('in_army', char), ('no_enemy',), ('lyn_played',), ('player_phase',),
    ('turn_over', n), ('units_in', rects), or ('code', addr) when it does something else."""
    if addr == NO_ENEMY:
        return ('no_enemy',)
    if addr == LYN_PLAYED:
        return ('lyn_played',)
    if addr == PLAYER_PHASE:
        return ('player_phase',)
    ins = thumb(addr, 24)
    calls = [i for i, x in enumerate(ins) if x[1] == 'bl']
    # push; movs r0, #c; bl IN_ARMY
    if calls and ins[calls[0]][2] == f'#{IN_ARMY:#x}' and ins[calls[0] - 1][1] == 'movs' and ins[calls[0] - 1][2].startswith('r0'):
        return ('in_army', _imm(ins[calls[0] - 1][2]))
    # ldr r0, =state; ldrh r0, [r0, #0x10]; cmp r0, #n; bhi -> 1: the turn is past n
    for i in range(len(ins) - 2):
        if ins[i][1] == 'ldrh' and ins[i][2].endswith('#0x10]') and ins[i + 1][1] == 'cmp' and ins[i + 2][1] in ('bhi', 'bls'):
            return ('turn_over' if ins[i + 2][1] == 'bhi' else 'turn_within', _imm(ins[i + 1][2]))
    return ('code', addr)


class Run:
    """Plays one script against a `world` (World below): collects the unit groups it loads (with the tiles units end on once the
    scripted moves are done), gifts, gold, side changes, map changes, flags and the chapter it goes to."""

    def __init__(self, world, units=None):
        self.world = world
        self.units = units if units is not None else []
        self.loads = []
        self.items = []         # (item, who): who is a character id, or None for the acting unit
        self.gold = []
        self.next_chapter = []
        self.recruits = []
        self.removed = []
        self.flags_set = []
        self.checks = []
        self.map_changes = []   # map change ids

    def unit_of(self, char):
        return next((u for u in self.units if u['char'] == char), None)

    def answer(self, c):
        """The world's answer, except that a character this script has loaded as yours is in your army."""
        if c[0] == 'in_army' and c[1] not in self.world.dead and (self.unit_of(c[1]) or {}).get('side') == 'player':
            return True
        return self.world.answer(c)

    def load(self, ptr, army=False, living=False):
        if not ROM.is_ptr(ptr):
            return
        group = unit_group(ptr)
        if living:
            group = [u for u in group if u['char'] not in self.world.dead]
        self.loads.append((ptr, group, army))
        for u in group:
            # The loader (0x0800A618): a unit for yours reuses the character's unit if it's on the map; one for another side takes
            # over the character's unit only if it's yours; anything else is a new unit.
            same = next((x for x in self.units if x['char'] == u['char']), None)
            if same and (u['side'] == 'player' or same['side'] == 'player'):
                same.update({'tile': u['end'], 'start': u['start'], 'side': u['side'], 'group': ptr, 'army': army})
                continue
            self.units.append({**u, 'tile': u['end'], 'group': ptr, 'army': army})

    def run(self, ptr, limit=5000):
        cmds = script(ptr)
        labels = {args[0]: k for k, (_, op, _, args) in enumerate(cmds) if op == 0x44}
        w_ = self.world
        k, skip = 0, 0
        for _ in range(limit):
            a, op, w, args = cmds[k]
            hi = w >> 16
            if skip:
                skip -= 1
                k += 1
                continue
            jump = None
            if op in (0x00, 0x01):
                return self
            if op == 0x45:
                jump = args[0]
            elif op in (0x46, 0x47):
                if args[1] & 0xFFFF in w_.dead:
                    jump = args[0]
            elif op in (0x48, 0x49):
                c = check(args[1])
                v = self.answer(c)
                self.checks.append((c, v))
                if (op == 0x48) == bool(v):
                    jump = args[0]
            elif op == 0x4A:
                if w_.skipping:
                    jump = args[0]
            elif op in (0x4C, 0x4D):
                if (op == 0x4C) == (args[1] in w_.flags):
                    jump = args[0]
            elif op == 0x4E:
                if (w_.active == (args[1] & 0xFF)) == bool(hi):
                    jump = args[0]
            elif op == 0x4F:
                if w_.mode == 'Eliwood':
                    jump = args[0]
            elif op == 0x50:
                if w_.mode == 'Hector':
                    jump = args[0]
            elif op == 0x51:
                if w_.hard == bool(hi):
                    jump = args[0]
            elif op in (0x59, 0x5A):
                c = check(args[0])
                v = self.answer(c)
                self.checks.append((c, v))
                if (op == 0x59) == bool(v):
                    skip = hi
            elif 0x3E <= op <= 0x42 and args[0] in (CLEAR_OTHERS, CLEAR_ENEMIES, CLEAR_ALL):
                keep = {CLEAR_OTHERS: ('player',), CLEAR_ENEMIES: ('player', 'npc'), CLEAR_ALL: ()}[args[0]]
                self.removed += [u['char'] for u in self.units if u['side'] not in keep]
                self.units = [u for u in self.units if u['side'] in keep]
            elif 0x3E <= op <= 0x42 and args[0] in ROUTINE_GIFTS:
                item, who = ROUTINE_GIFTS[args[0]]
                # Into the record the unit was loaded from (the unit shares its item list), so it counts as what the unit
                # carries on joining.
                rec = next((g for _, grp, _ in self.loads[::-1] for g in grp if g['char'] == who), None)
                if rec:
                    rec['items'].append(item)
            elif op == 0x32:
                self.load(args[0])
            elif op == 0x33:
                self.load(args[0], living=True)
            elif op in (0x34, 0x37):
                if (args[0] & 0xFF) == MODES[w_.mode] and (not args[0] >> 16 or w_.hard):
                    self.load(args[1], army=op == 0x37)
            elif op in (0x35, 0x38):
                self.load(args[group_slot(w_.mode, w_.hard)], army=op == 0x38)
            elif op == 0x36:
                self.load(args[0], army=True)
            elif op in (0x23, 0x24):
                src, dst = tile(args[0]), tile(args[1])
                u = next((u for u in self.units if u['tile'] == src), None)
                if u:
                    u['tile'] = dst
            elif op == 0x25:
                u = next((u for u in self.units if u['tile'] == tile(args[0])), None)
                if u:
                    u['tile'] = walk(u['tile'], args[1])
            elif op in (0x26, 0x27, 0x2B, 0x2F):
                u = self.unit_of(args[0] & 0xFF)
                if u:
                    u['tile'] = tile(args[1])
            elif op in (0x28, 0x2C):
                u = self.unit_of(args[0] & 0xFF)
                if u:
                    u['tile'] = walk(u['tile'], args[1])
            elif op == 0x29:
                u, v = self.unit_of(args[0] & 0xFF), self.unit_of(args[1] & 0xFF)
                if u and v:
                    u['tile'] = v['tile']
            elif op in (0x6A, 0x6C, 0x6E):
                u = next((u for u in self.units if u['tile'] == tile(args[0])), None)
                if u:
                    self.units.remove(u)
                    self.removed.append(u['char'])
            elif op in (0x6B, 0x6D, 0x6F):
                u = self.unit_of(args[0] & 0xFF)
                if u:
                    self.units.remove(u)
                    self.removed.append(args[0] & 0xFF)
            elif op == 0x65:
                char, side = args[0] & 0xFF, args[1]
                if side == 0:
                    self.recruits.append(char)
                for u in self.units:
                    if u['char'] == char:
                        u['side'] = ('player', 'npc', 'enemy', 'enemy')[side >> 6 & 3]
            elif op == 0x5B:
                self.items.append((args[0] & 0xFFFF, None))
            elif op == 0x5C:
                self.items.append((args[1] & 0xFFFF, args[0] & 0xFFFF))
            elif op == 0x5E:
                self.gold.append(args[0])
            elif 0x5F <= op <= 0x64:
                self.map_changes.append(hi)
            elif op == 0x76:
                self.flags_set.append(hi)
                w_.flags.add(hi)
            elif op == 0x77:
                w_.flags.discard(hi)
            elif op == 0x81:
                self.next_chapter.append(hi)
            if jump is not None and jump in labels:
                k = labels[jump]
            else:
                k += 1
        raise RuntimeError(f'script at {ptr:#x} did not end')


def walk(start, path_ptr):
    """A movement path: direction bytes (0 left, 1 right, 2 down, 3 up), 0x0C then a speed byte, ended by 4; returns the last
    tile."""
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
    """The state a script runs in: by default turn 1, your phase, everyone alive, no flags set, Lyn's story played. `away`: characters
    not in your army (yet)."""

    def __init__(self, mode='Eliwood', hard=False, dead=(), flags=(), active=None, turn=1, phase=0, skipping=False,
                 lyn_played=True, enemies_left=True, away=()):
        self.mode = mode
        self.hard = hard
        self.dead = set(dead)
        self.away = set(away)
        self.flags = set(flags)
        self.active = active
        self.turn = turn
        self.phase = phase
        self.skipping = skipping
        self.lyn_played = lyn_played
        self.enemies_left = enemies_left

    def answer(self, c):
        kind = c[0]
        if kind == 'in_army':
            return c[1] not in self.dead and c[1] not in self.away
        if kind == 'no_enemy':
            return not self.enemies_left
        if kind == 'lyn_played':
            return self.lyn_played
        if kind == 'player_phase':
            return self.phase == 0
        if kind == 'turn_over':
            return self.turn > c[1]
        if kind == 'turn_within':
            return self.turn <= c[1]
        return False


def pack(v):
    return struct.pack('<I', v)

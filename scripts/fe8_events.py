"""
The Sacred Stones' chapter events, read from the user's (U) ROM (scripts/gba_rom.py): the event lists of each chapter, the event
scripts split into commands, and a small interpreter that plays a script the way the game's event engine does, so the generators know
which units a chapter places and where they stand once its opening is over. The data (units, items, text, maps) is laid out as in The
Blazing Blade, but the event engine is a different one: scripts of u16s with numbered slots, labels, calls and branches on the
slots, where The Blazing Blade's had u32 words with checks built into each command. Formats are in data-raw/fe8/README.md.

What the engine does was read in the program code (Thumb, capstone), with the FE8 decompilation project's names for the commands
(github.com/FireEmblemUniverse/fireemblem8u, include/eventscript.h) as a map:
  - The event data (the chapter record's +0x74, through the pointer table) has 20 pointers: turn, talk, location and misc events; four
    lists for selection and tutorial events; traps, and the extra traps on Hard; your army's deploy tiles on Normal and Hard (the same
    group in every chapter); three choices of your army and three of the enemies for a skirmish on the chapter's map; the opening and
    ending scenes.
  - Event lists are entries ended by a 0 type, each as long as its type says (the check table at 0x089E84F4: routine, size in
    words). The flag at +2 is set once the event runs; the script is at +4.
      1 a flag (u16 at +8) is set (0 or 0x64: always); 2 a turn: from byte 8 to byte 9 (0: just that turn, 0xFF: every turn), the
      phase at +0xA (0 yours, 0x40 the other army's, 0x80 the enemy's); 3 two characters talk (bytes 8, 9; 0 at byte 8: anyone;
      +0xC: 0 always, 3 once the flag at +0xE is set); 4 a talk with a check routine at +0xC; 5 a tile (bytes 8, 9) and a command
      (byte 10: 0x11 seize, 0x20 a village's gate); 6 a village (command 0x10); 7 a chest: the item at +4 (gold: item 0x77 and the
      amount in the high half), tile at +8, command 0x14; 8 a door (command 0x12); 10 a shop (+4 a u16 item list ended by 0;
      command 0x16 armory, 0x17 vendor, 0x18 secret shop, which needs a Member Card, 0x08083A59); 11 an area (bytes 8-11: x1, y1,
      x2, y2); 14 a check routine (+8); 15 / 16 the flag at +0xC set and the one at +2 clear (the script at +8).
  - A script command is a u16: the command in the high byte, its length in u16s in bits 4-7 and a variant in bits 0-3
    (0x0800CED0; commands 0x00-0x45 have handlers at 0x08591B28). The arguments follow as u16s; a pointer or value is two of them.
    Slots 0-13 (s0 is 0) hold values: checks leave their answer in s12 (0x0800E17A). A label is searched for from the script's start
    (0x0800D980). A character argument of 0xFFFF is the acting unit, 0xFFFE the unit at the tile in s11 (x in its low half, y in the
    high half), 0xFFFD the character in s2
    (0x0800BC50). The ones the generators follow:
      0x01 end (variant 0 returns from a call, 1 ends everything); 0x02 flags (variant 9 sets, 1 clears); 0x03 variant 1 checks a flag;
      0x05 sets a slot; 0x06 slot arithmetic (one u16: destination, then the two sources, a nibble each); 0x07 the queue (variant 1
      adds s1, 2 takes one off into a slot); 0x08 label; 0x09 goto; 0x0A call (0xFFFFFFFF: the script in s2); 0x0C goto if s[a] =,
      !=, >=, >, <=, < s[b] (variants 0-5); 0x19 checks: 0 the story (the play state's byte 0x1B: 1 before the split, 2 Eirika's
      route, 3 Ephraim's), 2 Hard, 3 the turn, 4 how many enemies, 7 Easy (the tutorial); 0x25 load a chapter's map; 0x27 apply a
      map change; 0x2A go to a chapter; 0x2C load a unit group (variants 0-2; the first argument says who is left out: 0 your dead,
      1 nobody, 2 your dead unless ..., 0x0800F528); 0x2F move a character: to a tile (variants 0 and 8), onto another character
      (1), one step (2), along the tiles in the queue (3); 0x32 load one character; 0x33 unit checks (0 on the map, 2 alive, 3
      deployed, 4 acting, 5 side); 0x34 a character's side (variants 2-4: yours, the other army, the enemy), 0xA / 0xB / 0xC take
      your units / the other army / the enemies off the map, 0xD / 0xE / 0xF remove a character; 0x37 give a character the item in
      s3 (variant 0), gold (1, 2); 0x3E the preparations screen.
  - A unit group is 20-byte records up to a 0 character: character, class, leader, flags (level << 3, side << 1, auto-level), the
    tile as a u16 (x in bits 0-5, y in 6-11; bit 12: a random monster is made in its place, 0x08017ACC; bit 13: it drops its last
    item, 0x08017CC4; bit 14: the loader may leave it out, picking among them by a percentage, 0x0800F914), the number of
    REDA steps at +7 and their address at +8, four items at +0xC, the AI at +0x10. A unit walks its REDA steps (8 bytes each: the
    tile the same way, then speed and delays) once loaded; it ends on the last.
  - A tile in a script is a u16: x in the low byte, y in the high byte, from the top-left at (0, 0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gba_rom import rom  # noqa: E402

ROM = rom('fe8')
R = ROM.R
u8, u16, u32, off = ROM.u8, ROM.u16, ROM.u32, ROM.off

LIST_CHECKS = 0x9E84F4
LIST_SIZES = [4 * u32(LIST_CHECKS + 8 * t + 4) for t in range(17)]
SIDES = ('player', 'npc', 'enemy', 'enemy')
MODES = {'Prologue': 1, 'Eirika': 2, 'Ephraim': 3}
GOLD_ITEM = 0x77


def events_of(n):
    """The chapter's event data: its list pointers by name."""
    base = ROM.pointer(R[ROM.chapter(n) + 0x74])
    s = [u32(base + 4 * i) for i in range(20)]
    return {'turn': s[0], 'talk': s[1], 'location': s[2], 'misc': s[3], 'traps': s[8], 'traps_hard': s[9], 'army': s[10],
            'army_hard': s[11], 'skirmish_army': s[12:15], 'skirmish_enemies': s[15:18], 'opening': s[18], 'end': s[19]}


def event_list(ptr):
    """Entries up to a 0 type, each as long as its type."""
    o, out = off(ptr), []
    while u16(o):
        t = u16(o)
        n = LIST_SIZES[t]
        out.append({'type': t, 'flag': u16(o + 2), 'ptr': u32(o + 4), 'b': R[o + 8:o + n], 'at': o})
        o += n
    return out


def command(a):
    """The command at file offset a: (offset, command, variant, argument u16s, the next command's offset)."""
    h = u16(a)
    n = max((h >> 4) & 0xF, 1)
    return a, h >> 8, h & 0xF, [u16(a + 2 * k) for k in range(1, n)], a + 2 * n


def script(ptr, limit=4000):
    """A script's commands up to its last end: commands after an end are read on while a label could still lead there."""
    a, out = off(ptr), []
    for _ in range(limit):
        c = command(a)
        out.append(c[:4])
        a = c[4]
        if c[1] == 0x01:
            # Past an end, more script follows only if some goto in it names a label further on.
            targets = {args[0] for _, cmd, _, args in out if cmd in (0x09, 0x0C)}
            labels = {args[0] for _, cmd, _, args in out if cmd == 0x08}
            if not targets - labels:
                return out
    raise ValueError(f'no end to the script at {ptr:#x}')


def tile(v):
    """A script tile (x in the low byte, y in the high byte)."""
    return v & 0xFF, v >> 8


def unit_tile(v):
    return v & 0x3F, (v >> 6) & 0x3F


def unit_group(ptr):
    """20-byte unit records up to one with character 0. 'end' is the tile its REDA steps leave it on."""
    o, out = off(ptr), []
    while R[o]:
        f, pos = R[o + 3], u16(o + 4)
        end = unit_tile(pos)
        steps, reda = R[o + 7], u32(o + 8)
        if steps and ROM.is_ptr(reda):
            end = unit_tile(u16(off(reda) + 8 * (steps - 1)))
        out.append({'char': R[o], 'class': R[o + 1], 'level': f >> 3, 'side': SIDES[(f >> 1) & 3], 'autolevel': f & 1,
                    'start': unit_tile(pos), 'end': end, 'monster': bool(pos & 0x1000), 'drop': bool(pos & 0x2000),
                    'optional': bool(pos & 0x4000), 'items': [x for x in R[o + 12:o + 16] if x],
                    'ai': R[o + 16:o + 20]})
        o += 20
    return out


class World:
    """The state a script runs in: by default turn 1, your phase, everyone alive, no flags set. `mode`: 'Prologue' (before the
    split), 'Eirika' or 'Ephraim'; `difficulty`: 'Easy', 'Normal' or 'Hard'. `away`: characters not in your army (yet)."""

    def __init__(self, mode='Prologue', difficulty='Normal', dead=(), flags=(), active=None, turn=1, phase=0, away=(),
                 enemies_left=True, best=False):
        self.mode = mode
        self.difficulty = difficulty
        self.dead = set(dead)
        self.flags = set(flags)
        self.active = active
        self.turn = turn
        self.phase = phase
        self.away = set(away)
        self.enemies_left = enemies_left
        # The best case for an end scene's rewards: everyone it asks about alive, and every unit of the other army left.
        self.best = best


class Run:
    """Plays one script against a `world`: collects the unit groups it loads (with the tiles units end on once the scripted moves are
    done), gifts, gold, side changes, map changes, flags and the chapter it goes to."""

    def __init__(self, world, units=None, chapter=None):
        self.world = world
        self.units = units if units is not None else []
        self.chapter = chapter    # the chapter whose map the units stand on; another map's units (a cutscene's) aren't kept
        self.map = chapter
        self.slots = [0] * 14
        self.queue = []
        self.loads = []
        self.items = []           # (item, who): who is a character id, or None for the acting unit
        self.gold = []
        self.next_chapter = []
        self.recruits = []
        self.removed = []
        self.flags_set = []
        self.checks = []
        self.map_changes = []
        self.prep = False

    def unit_of(self, char):
        return next((u for u in self.units if u['char'] == char), None)

    def who(self, v):
        """A character argument: 0xFFFF the acting unit, 0xFFFE the unit on the tile in s11, 0xFFFD the character in s2."""
        if v == 0xFFFF:
            return self.world.active
        if v == 0xFFFE:
            # s11 holds a tile as x in the low half, y in the high half.
            t = (self.slots[11] & 0xFFFF, self.slots[11] >> 16)
            return next((u['char'] for u in self.units if u['tile'] == t), None)
        if v == 0xFFFD:
            return self.slots[2] & 0xFF
        return v

    def load(self, ptr, army=False, keep_dead=False):
        if not ROM.is_ptr(ptr):
            return
        group = unit_group(ptr)
        if not keep_dead:
            # The loader leaves out your characters who have died (0x0800F528).
            group = [u for u in group if not (u['side'] == 'player' and u['char'] in self.world.dead)]
        self.loads.append((ptr, group, army))
        for u in group:
            if army:
                # A deployment group's records are slots: after the first (the lord), the characters are placeholders.
                self.units.append({**u, 'tile': u['end'], 'group': ptr, 'army': True})
            else:
                self.place(u, ptr, army)

    def place(self, u, ptr, army=False):
        # A unit for a character already on the map is that unit (the loader reuses it); anything else is a new unit.
        same = self.unit_of(u['char']) if u['char'] < 0x40 else None
        if same:
            same.update({'tile': u['end'], 'start': u['start'], 'side': u['side'], 'group': ptr, 'army': army})
            return
        self.units.append({**u, 'tile': u['end'], 'group': ptr, 'army': army})

    def answer(self, sub, args):
        """A check (0x19 / 0x33 / 0x03): what it leaves in s12."""
        w_ = self.world
        if sub == ('19', 0):
            return MODES[w_.mode]
        if sub == ('19', 2):
            return int(w_.difficulty == 'Hard')
        if sub == ('19', 3):
            return w_.turn
        if sub == ('19', 4):
            return len([u for u in self.units if u['side'] == 'enemy']) if w_.enemies_left else 0
        if sub == ('19', 5):
            return 99 if w_.best else len([u for u in self.units if u['side'] == 'npc'])
        if sub == ('19', 7):
            return int(w_.difficulty == 'Easy')
        if sub == ('03', 1):
            return int(args[0] in w_.flags)
        if sub[0] == '33':
            c = self.who(args[0])
            unit = self.unit_of(c)
            here = unit is not None
            mine = c not in w_.dead and (c not in w_.away or (here and unit['side'] == 'player'))
            if sub[1] == 0:
                return int(here)
            if sub[1] == 2:
                if w_.best:
                    return int(c not in w_.dead)
                return int(mine if c is not None and c < 0x40 else here)
            if sub[1] == 3:
                return int(here and unit['side'] == 'player')
            if sub[1] == 4:
                return int(c == w_.active)
            if sub[1] == 5:
                return {'player': 0, 'npc': 1, 'enemy': 2}[unit['side']] if here else 0
        return 0

    def run(self, ptr, limit=20000):
        stack = []
        cmds = script(ptr)
        k = 0
        w_ = self.world
        s = self.slots
        for _ in range(limit):
            if k >= len(cmds):
                return self
            a, cmd, sub, args = cmds[k]
            k += 1
            if cmd == 0x01:
                if sub == 0 and stack:
                    cmds, k = stack.pop()
                    continue
                return self
            arg32 = (args[1] | args[2] << 16) if len(args) >= 3 else None
            if cmd == 0x02:
                if sub == 9:
                    w_.flags.add(args[0])
                    self.flags_set.append(args[0])
                elif sub == 1:
                    w_.flags.discard(args[0])
            elif cmd in (0x03, 0x19, 0x33):
                v = self.answer((f'{cmd:02x}', sub), args)
                self.checks.append(((cmd, sub, tuple(args)), v))
                s[12] = v
            elif cmd == 0x05:
                if args[0]:
                    s[args[0]] = arg32
            elif cmd == 0x06:
                d, x, y = args[0] & 0xF, (args[0] >> 4) & 0xF, (args[0] >> 8) & 0xF
                ops = [lambda p, q: p + q, lambda p, q: p - q, lambda p, q: p * q, lambda p, q: p // q if q else 0,
                       lambda p, q: p % q if q else 0, lambda p, q: p & q, lambda p, q: p | q, lambda p, q: p ^ q,
                       lambda p, q: p << q, lambda p, q: p >> q]
                if d:
                    s[d] = ops[sub](s[x], s[y]) & 0xFFFFFFFF
            elif cmd == 0x07:
                if sub == 0:
                    self.queue.append(s[args[0]])
                elif sub == 1:
                    self.queue.append(s[1])
                elif sub == 2 and args[0]:
                    s[args[0]] = self.queue.pop(0) if self.queue else 0
            elif cmd == 0x09:
                k = self.label(cmds, args[0], k)
            elif cmd == 0x0A:
                target = s[2] if arg32 == 0xFFFFFFFF else arg32
                if target is not None and ROM.is_ptr(target):
                    stack.append((cmds, k))
                    cmds, k = script(target), 0
            elif cmd == 0x0C:
                p, q = signed(s[args[1]]), signed(s[args[2]])
                if [p == q, p != q, p >= q, p > q, p <= q, p < q][sub]:
                    k = self.label(cmds, args[0], k)
            elif cmd == 0x25:
                self.map = args[0]
            elif cmd == 0x27 and sub == 0:
                self.map_changes.append(args[0])
            elif cmd == 0x2A:
                if sub in (1, 2, 3):
                    self.next_chapter.append(args[0])
            elif cmd == 0x2C and sub in (0, 1, 2):
                ptr = s[2] if arg32 & 0x80000000 else arg32
                if self.map == self.chapter:
                    self.load(ptr, keep_dead=args[0] == 1)
            elif cmd == 0x2F:
                u = self.unit_of(self.who(args[1]))
                kind = sub & 7
                if u and kind == 0:
                    u['tile'] = tile(args[2])
                elif u and kind == 1:
                    v = self.unit_of(self.who(args[2]))
                    if v:
                        u['tile'] = v['tile']
                elif u and kind == 2:
                    x, y = u['tile']
                    u['tile'] = [(x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)][args[2] & 3]
                elif kind == 3:
                    # The queue holds REDA-like steps, two values each (the tile, then speed and delays); the last tile is where
                    # it stops.
                    steps = self.queue[0::2]
                    if u and steps:
                        u['tile'] = unit_tile(steps[-1] & 0xFFFF)
                    self.queue = []
            elif cmd == 0x32:
                c = self.who(args[0])
                if c and self.map == self.chapter:
                    rec = {'char': c, 'class': None, 'level': None, 'side': SIDES[sub & 3], 'autolevel': 0,
                           'start': tile(args[1]), 'end': tile(args[1]), 'monster': False, 'drop': False, 'optional': False,
                           'items': [], 'ai': b''}
                    self.place(rec, None)
            elif cmd == 0x34:
                c = self.who(args[0]) if args else None
                if sub in (2, 3, 4):
                    if sub == 2:
                        self.recruits.append(c)
                    for u in self.units:
                        if u['char'] == c:
                            u['side'] = ('player', 'npc', 'enemy')[sub - 2]
                elif sub in (0xA, 0xB, 0xC):
                    side = {0xA: 'player', 0xB: 'npc', 0xC: 'enemy'}[sub]
                    self.removed += [u['char'] for u in self.units if u['side'] == side]
                    self.units = [u for u in self.units if u['side'] != side]
                elif sub in (0xD, 0xE, 0xF):
                    u = self.unit_of(c)
                    if u:
                        self.units.remove(u)
                        self.removed.append(c)
            elif cmd == 0x37:
                if sub == 0:
                    self.items.append((s[3] & 0xFF, self.who(args[0])))
                else:
                    self.gold.append(s[3])
            elif cmd == 0x38:
                w_.active = self.who(args[0])
            elif cmd == 0x3E:
                self.prep = True
        raise RuntimeError(f'script at {ptr:#x} did not end')

    @staticmethod
    def label(cmds, n, k):
        """Where a goto lands: the label's command, searched for from the script's start (0x0800D980)."""
        for i, (_, cmd, _, args) in enumerate(cmds):
            if cmd == 0x08 and args[0] == n:
                return i + 1
        return k


def signed(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v

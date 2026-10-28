"""
Thracia 776's chapter events, read from the user's clean ROM (scripts/fe5_rom.py) and played the way the game's event engine does,
so units stand where the openings leave them. Command names and the meaning of the engine's ASM calls are Zane Avernathy's (VoltEdge
and the Lil' Manster build files); the byte layouts below were checked in the ROM (Chapter 1's units and scripts decode exactly).

A chapter's ten event pointers ($8C:D561): opening, turn, talk, location, before-action, shop, battle, ending, after-action and prep
definitions. A definition list is entries of [flag u8][script u24][conditions...][FF], ended by FF FF; an entry runs when every
condition holds and its flag is clear (then the flag is set; flag 0 is never set). Scripts are byte commands (LENGTHS); FC-FF end
or pause one. A unit group is 20-byte records ended by a 0 character:
    [character u16][start x | side << 6][start y][to x][to y][leader u16][7 items][level | boss << 7][4 AI bytes]
side 0 is yours, 1 (0x40) the enemy's, 2 (0x80) the other army's; a unit appears at its start and walks to its "to" tile.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe5_rom import R, lo, u8, u16, u24  # noqa: E402

PLAYER, ENEMY, NPC = 'player', 'enemy', 'npc'
SIDES = {0x00: PLAYER, 0x40: ENEMY, 0x80: NPC}
SIDE_VALUE = {v: k for k, v in SIDES.items()}

# WRAM the conditions and scripts read and write.
TURN, PHASE, CHAPTER = 0x0E13, 0x0E15, 0x0E11
CURSOR_X, CURSOR_Y = 0x0E4D, 0x0E4F
SELECTED = 0x0E6F            # the acting unit's buffer: +0 its character
STRUCT_PARAM, TARGET, EX, EY = 0x1734, 0x1736, 0x1738, 0x173A
PARAM1, PARAM2, PARAM3, LONG_PARAM, TRUTH = 0x1740, 0x1742, 0x1744, 0x1746, 0x174B
GROUP_POINTER = 0x1798
TILE_X, TILE_Y = 0x7E4FA0, 0x7E4FA2  # a door's tile, for the before-action checks

# Unit states (VoltEdge Statuses.h)
DEAD, RESCUED, HIDDEN, DISABLED, CAPTURED = 0x0001, 0x0010, 0x0040, 0x0400, 0x0800

# Condition codes -> operand layout (u8 'b', u16 'w', u24 'l'); VoltEdge EVENTS/Conditions.h.
CONDITIONS = {
    0x00: 'ww', 0x01: 'ww', 0x02: 'w', 0x03: 'w', 0x04: 'lw', 0x05: 'lb', 0x06: 'lw', 0x07: 'll', 0x08: 'lw', 0x09: 'll', 0x0A: 'll',
    0x0B: 'lbb', 0x0C: 'lww', 0x0D: 'b', 0x0E: 'b', 0x0F: 'l', 0x10: 'ww', 0x11: 'ww', 0x12: 'b', 0x13: 'b', 0x14: 'w', 0x15: 'w',
    0x16: 'wb', 0x17: 'wb', 0x18: 'b', 0x19: '', 0x1A: 'w', 0x1B: 'w',
}
# Script commands -> operand layout ('s' a signed u16); VoltEdge EVENTS/Main.h. 'c' is a [x, y] pair (2 bytes).
COMMANDS = {
    0x00: '', 0x01: '', 0x02: 'w', 0x03: 'w', 0x04: 'w', 0x05: 's', 0x06: 's', 0x07: 's', 0x08: 'lb', 0x09: 'lw', 0x0A: 'lb', 0x0B: 'lw',
    0x0C: 'b', 0x0D: 'b', 0x0E: 'b', 0x0F: 'lb', 0x10: 'lw', 0x11: 'll', 0x12: 'll', 0x13: 'll', 0x14: 'll', 0x15: 'lb', 0x16: 'lw',
    0x17: 'll', 0x18: 'lb', 0x19: 'lw', 0x1A: 'll', 0x1B: 'lw', 0x1C: 'll', 0x1D: 'lw', 0x1E: 'w', 0x1F: 'w', 0x20: '', 0x21: 'w',
    0x22: 'lb', 0x23: 'lw', 0x24: 'lb', 0x25: 'lw', 0x26: 'b', 0x27: 'b', 0x28: 'll', 0x29: '', 0x2A: '', 0x2B: 'l', 0x2C: 'l',
    0x2D: 'lbb', 0x2E: '', 0x2F: 'l', 0x30: 'l', 0x31: 'b', 0x32: 'b', 0x33: 'b', 0x34: 'b', 0x35: 'bb', 0x36: '', 0x37: 'b',
    0x38: '', 0x39: 'c', 0x3A: 'b', 0x3B: '', 0x3C: 'bbb', 0x3D: 'cb', 0x3E: 'b', 0x3F: 'wcbbl', 0x40: 'wcbbl', 0x41: 'wccbl',
    0x42: 'l', 0x43: 'l', 0x44: 'l', 0x45: '', 0x46: 'wcc',
}
SIZES = {'b': 1, 'w': 2, 's': 2, 'l': 3, 'c': 2}
ENDS = {0xFC: 'yield', 0xFD: 'end3', 0xFE: 'end2', 0xFF: 'end1'}

# The engine's ASM calls (VoltEdge EVENTS/Values.h), by address.
ASMC = {
    0x8CA177: 'ChangeAllegianceToPlayer', 0x8CA189: 'ChangeAllegianceToEnemy', 0x8CA19B: 'ChangeAllegianceToNPC',
    0x8CA1AD: 'ChangeAllegiance', 0x8CA1C7: 'ChangeAllegianceToPlayerIfHeld', 0x8CA20C: 'IsUnitHeld', 0x8CA238: 'IsUnitHeldByEnemy',
    0x8CA343: 'RemoveUnit', 0x8CA36B: 'PromoteUnit', 0x8CA376: 'PromoteUnitSilent', 0x8CA385: 'SetUnitPosition',
    0x8CA464: 'SetUnitState', 0x8CA486: 'UnsetUnitState', 0x8CA4B1: 'CheckUnitStateSet', 0x8CA4E0: 'CheckUnitStateUnset',
    0x8CA541: 'CheckAbleToTalk', 0x8CA652: 'ActiveUnitCheckUnitState', 0x8CA6A1: 'ActiveUnitCheckCarrying', 0x8CA6F3: 'CountOwnedItem',
    0x8CA755: 'CheckUnitForItem', 0x8CA789: 'GiveUnitItemSilent', 0x8CA7B0: 'CheckUnitExists', 0x8CA7DF: 'RemoveItemFromUnit',
    0x8CA8DD: 'GiveActiveUnitItem', 0x8CA8E9: 'GiveActiveUnitItemCurrentDurability', 0x8CA939: 'GiveConvoyItem',
    0x8CA9C5: 'CheckIfUnitHasEquippedWeapon', 0x8CAA27: 'AddGoldWord', 0x8CAA37: 'SubtractGoldWord', 0x8CAA47: 'CompareGoldGTE',
    0x8CAADA: 'SingleTileChangeByCoords', 0x8CAAA5: 'SingleTileChangeSavedTile', 0x8CAB17: 'SetTileToDoor', 0x8CAB5B: 'ChapterEnd',
    0x8CABC9: 'FinalChapterEnd', 0x8CACD3: 'TileChangeByID', 0x8CAD57: 'CheckIfUnitAtCoords', 0x8CAE1C: 'LoadUnitGroup',
    0x8CAF73: 'LoadPlayerUnitsByStartingPositions', 0x8CB0CC: 'SetCharacterDataByte', 0x8CB127: 'SetCharacterDataWord',
    0x8CB4CE: 'CountAllUnitsUncapturedAlive', 0x8CB4FA: 'CountPlayerUnitsUncapturedAlive', 0x8CB526: 'CountEnemyUnitsUncapturedAlive',
    0x8CB552: 'CountNPCUnitsUncapturedAlive', 0x8CB597: 'CountAllUnitsUncapturedAliveWithHidden',
    0x8CB5DC: 'CountAllUnitsUncapturedAliveByTable', 0x8CB621: 'CountAllUnitsRescuedByPlayerOrNPCByTable',
    0x8CB666: 'CountAllUnitsRescuedByPlayerOrNPC', 0x8CB6EC: 'CheckConomorOnMap', 0x8CB70C: 'CountAllUnitsAlive',
    0x8CB82B: 'CreateRandomChestItemArrayFromUnitInventories', 0x8CB9C7: 'GetRandomChestItem', 0x80C29D: 'GameOver',
}


def operands(a, layout):
    out, o = [], lo(a)
    for f in layout:
        if f == 'b':
            out.append(R[o])
        elif f == 'w':
            out.append(struct.unpack_from('<H', R, o)[0])
        elif f == 's':
            out.append(struct.unpack_from('<h', R, o)[0])
        elif f == 'l':
            out.append(R[o] | R[o + 1] << 8 | R[o + 2] << 16)
        elif f == 'c':
            out.append((R[o], R[o + 1]))
        o += SIZES[f]
    return out


def size(layout):
    return sum(SIZES[f] for f in layout)


def definitions(ptr):
    """A definition list: [{flag, ptr, conds: [(code, args)], at}]."""
    out, a = [], ptr
    if not ptr:
        return out
    while not (u8(a) == 0xFF and u8(a + 1) == 0xFF):
        e = {'at': a, 'flag': u8(a), 'ptr': u24(a + 1), 'conds': []}
        a += 4
        while u8(a) != 0xFF:
            code = u8(a)
            layout = CONDITIONS[code]
            e['conds'].append((code, operands(a + 1, layout)))
            a += 1 + size(layout)
        a += 1
        out.append(e)
    return out


def command(a):
    """(command, operands, next address) at a; FC-FF are the ends."""
    c = u8(a)
    if c in ENDS:
        return c, [], a + 1
    layout = COMMANDS[c]
    return c, operands(a + 1, layout), a + 1 + size(layout)


def script(ptr, limit=4000):
    """Every command of a script from ptr up to its end (following no jumps): [(address, command, operands)]."""
    out, a = [], ptr
    while len(out) < limit:
        c, args, nxt = command(a)
        out.append((a, c, args))
        if c in (0xFD, 0xFE, 0xFF):
            break
        a = nxt
    return out


def reachable(ptr, limit=6000):
    """Every command a script can reach, following both sides of each jump (JUMP and its conditional forms, in the script's bank):
    [(address, command, operands)], each once."""
    seen, todo, out = set(), [ptr], []
    while todo and len(out) < limit:
        a = todo.pop()
        while a not in seen and len(out) < limit:
            seen.add(a)
            try:
                c, args, nxt = command(a)
            except KeyError:
                break
            out.append((a, c, args))
            if c in (0xFD, 0xFE, 0xFF):
                break
            if c in (0x02, 0x03, 0x04):
                todo.append(a & 0xFF0000 | args[0])
                if c == 0x02:
                    break
            elif c in (0x05, 0x06, 0x07):
                todo.append(nxt + args[0])
                if c == 0x05:
                    break
            a = nxt
    return out


def unit_group(ptr):
    """The 20-byte unit records at ptr, up to a 0 character."""
    out, a = [], ptr
    while (c := u16(a)):
        o = lo(a)
        b = R[o:o + 20]
        out.append({
            'char': c, 'side': SIDES[b[2] & 0xC0], 'start': (b[2] & 0x3F, b[3]), 'tile': (b[4], b[5]),
            'leader': b[6] | b[7] << 8, 'items': [i for i in b[8:15] if i], 'level': b[15] & 0x7F, 'boss': bool(b[15] & 0x80),
            'ai': tuple(b[16:20]), 'state': 0, 'group': ptr,
        })
        a += 20
    return out


def positions(ptr):
    """A starting-positions list: [x, y] pairs ended by FF."""
    out, a = [], ptr
    while ptr and u8(a) != 0xFF:
        out.append((u8(a), u8(a + 1)))
        a += 2
    return out


class World:
    """What the scripts ask about: who is dead, captured or held, the flags set, the turn and phase, the acting unit, and a few
    answers the generators choose (`answers`: the truth an ASM check gives, by name, overriding the default)."""

    def __init__(self, flags=(), turn=1, phase=0, active=None, dead=(), captured=(), held=(), roll=True, answers=None,
                 disabled=()):
        self.flags = set(flags)
        # Characters out of your army for now (left behind or gone with another group: unit state $0400).
        self.disabled = set(disabled)
        self.turn, self.phase, self.active = turn, phase, active
        self.dead, self.captured, self.held = set(dead), set(captured), set(held)
        self.roll = roll
        self.answers = answers or {}


class Run:
    """One script played against a world: the units it loads and moves, the items and gold it gives, map changes, recruits, the
    chapter it goes to next."""

    def __init__(self, world, units=None, mem=None):
        self.world = world
        self.units = [dict(u) for u in units] if units else []
        self.mem = dict(mem or {})
        self.mem.setdefault(TURN, world.turn)
        self.mem.setdefault(PHASE, world.phase)
        if world.active:
            self.mem[SELECTED] = world.active
        self.loads = []           # (group pointer, [units])
        self.items = []           # (item, who: a character or None for the convoy)
        self.gold = []
        self.recruits = []
        self.removed = []
        self.tile_changes = []    # (x, y, tile id)
        self.map_changes = []     # map change ids
        self.chapter_add = 0      # what the script adds to the chapter number
        self.starts_loaded = False
        self.calls = []
        self.flag_sets, self.flag_clears = [], []
        self.ended = None

    # --- memory ---
    def word(self, a):
        if a >> 16 >= 0x80 and (a & 0xFFFF) >= 0x8000:
            return u16(a)  # the ROM: a chest's item, a shop's tile
        return self.mem.get(a & 0xFFFFFF if a > 0xFFFF else a, 0)

    def put(self, a, v):
        self.mem[a & 0xFFFFFF if a > 0xFFFF else a] = v & 0xFFFF

    # --- units ---
    def find(self, c):
        for u in self.units:
            if u['char'] == c and not u['state'] & DEAD:
                return u
        return None

    def alive(self, c):
        return c not in self.world.dead and (self.find(c) is not None or c not in self.world.dead)

    def load(self, ptr):
        grp = unit_group(ptr)
        for g in grp:
            g = dict(g)
            g['state'] = 0
            if g['char'] in self.world.dead and g['side'] == PLAYER:
                continue
            self.units.append(g)
        self.loads.append((ptr, grp))

    def move(self, c, target, to, movestring):
        u = self.find(c) if c and c != 0xFFFF else None
        if c == 0xFFFF:
            u = self.find(self.word(SELECTED))
        if u is None and not c:
            u = next((x for x in self.units if x['tile'] == target), None)
        if u is None:
            return
        if movestring:
            x, y = u['tile']
            a = movestring
            # Movestring steps (VoltEdge EVENTS/Helpers.h): 1-4 a step down, left, up or right (9-12 the same without turning),
            # 5-8 a turn held for a u16 time, $80 | speed, and one-byte marks.
            while (m := u8(a)) != 0:
                if m in (1, 2, 3, 4, 9, 10, 11, 12):
                    x, y = {1: (x, y + 1), 2: (x - 1, y), 3: (x, y - 1), 4: (x + 1, y)}[(m - 1) % 4 + 1]
                a += 3 if 5 <= m <= 8 else 1
            u['tile'] = (x, y)
        elif to != (0, 0):
            u['tile'] = to

    # --- conditions ---
    def check(self, code, args):
        w = self.world
        if code in (0x00, 0x01):
            return w.active == args[0] and self.mem.get(TARGET) == args[1]
        if code == 0x02:
            return args[0] in (w.active, self.mem.get(TARGET))
        if code in (0x05, 0x06, 0x08):
            v = self.word(args[0])
            return v != args[1] if code == 0x08 else v == args[1]
        if code == 0x0B or code == 0x0C:
            return args[1] <= self.word(args[0]) <= args[2]
        if code == 0x0D:
            return args[0] in w.flags
        if code == 0x0E:
            return args[0] not in w.flags
        if code == 0x10:
            return self.state(args[0]) & args[1] == args[1]
        if code == 0x11:
            return self.state(args[0]) & args[1] != args[1]
        if code == 0x16:
            return self.count(args[0]) <= args[1]
        if code == 0x17:
            return self.count(args[0]) >= args[1]
        if code == 0x18:
            return w.roll
        if code == 0x1A:
            return args[0] in w.dead
        return w.answers.get(('cond', code), True)

    def state(self, c):
        s = 0
        if c in self.world.dead:
            s |= DEAD
        if c in self.world.captured:
            s |= CAPTURED
        if c in self.world.held:
            s |= RESCUED
        if c in self.world.disabled:
            s |= DISABLED
        u = self.find(c)
        return s | (u['state'] if u else 0)

    def count(self, c):
        return sum(1 for u in self.units if u['char'] == c and not u['state'] & DEAD) if c not in self.world.dead else 0

    # --- ASM calls ---
    def asmc(self, addr, arg):
        name = ASMC.get(addr)
        self.calls.append(name or addr)
        c = self.mem.get(TARGET, 0)
        truth = None
        if name in self.world.answers:
            truth = self.world.answers[name](self, c) if callable(self.world.answers[name]) else self.world.answers[name]
        elif name == 'LoadUnitGroup':
            self.load(self.mem.get(GROUP_POINTER, 0))
        elif name in ('ChangeAllegianceToPlayer', 'ChangeAllegianceToEnemy', 'ChangeAllegianceToNPC', 'ChangeAllegianceToPlayerIfHeld'):
            side = {'ChangeAllegianceToEnemy': ENEMY, 'ChangeAllegianceToNPC': NPC}.get(name, PLAYER)
            u = self.find(c)
            if name == 'ChangeAllegianceToPlayerIfHeld' and c not in self.world.held:
                truth = False
            elif u:
                u['side'] = side
                if side == PLAYER:
                    self.recruits.append(c)
                truth = True
        elif name == 'ChangeAllegiance':
            u = self.find(c)
            if u:
                u['side'] = SIDES.get(self.mem.get(PARAM3, 0) & 0xC0, u['side'])
                if u['side'] == PLAYER:
                    self.recruits.append(c)
        elif name == 'RemoveUnit':
            u = self.find(c)
            if u:
                self.units.remove(u)
                self.removed.append(c)
        elif name == 'SetUnitPosition':
            u = self.find(c)
            if u is None and c in self.world.disabled:
                # A character out of your army, put back on the map (Chapter 8's Marty): what they carry is whatever they had.
                u = {'char': c, 'side': PLAYER, 'start': (0, 0), 'tile': (0, 0), 'leader': 0, 'items': [], 'level': 0,
                     'boss': False, 'ai': (0, 0, 0, 0), 'state': 0, 'group': 0, 'roster': True}
                self.units.append(u)
            if u:
                u['tile'] = (self.mem.get(EX, 0), self.mem.get(EY, 0))
        elif name in ('SetUnitState', 'UnsetUnitState'):
            u = self.find(c)
            if u:
                if name == 'SetUnitState':
                    u['state'] |= self.mem.get(PARAM1, 0)
                else:
                    u['state'] &= ~self.mem.get(PARAM1, 0)
        elif name == 'CheckUnitStateSet':
            want = self.mem.get(PARAM1, 0)
            truth = self.state(c) & want == want
        elif name == 'CheckUnitStateUnset':
            want = self.mem.get(PARAM1, 0)
            truth = self.state(c) & want != want
        elif name in ('IsUnitHeld', 'IsUnitHeldByEnemy', 'CountAllUnitsRescuedByPlayerOrNPC'):
            truth = c in self.world.held
        elif name in ('CountAllUnitsAlive', 'CountAllUnitsUncapturedAlive', 'CountPlayerUnitsUncapturedAlive',
                      'CountEnemyUnitsUncapturedAlive', 'CountNPCUnitsUncapturedAlive', 'CountAllUnitsUncapturedAliveWithHidden',
                      'CheckUnitExists'):
            truth = c not in self.world.dead and (name == 'CountAllUnitsAlive' or c not in self.world.captured)
        elif name in ('GiveActiveUnitItem', 'GiveActiveUnitItemCurrentDurability'):
            self.items.append((self.mem.get(PARAM1, 0) & 0xFF, self.word(SELECTED) or None))
            truth = True
        elif name == 'GiveUnitItemSilent':
            self.items.append((self.mem.get(PARAM1, 0) & 0xFF, c))
        elif name == 'GiveConvoyItem':
            self.items.append((self.mem.get(PARAM1, 0) & 0xFF, None))
        elif name == 'AddGoldWord':
            self.gold.append(self.mem.get(PARAM1, 0))
        elif name in ('SingleTileChangeByCoords', 'SetTileToDoor', 'SingleTileChangeSavedTile'):
            self.tile_changes.append((self.mem.get(EX, 0), self.mem.get(EY, 0), self.mem.get(PARAM1, 0)))
        elif name == 'TileChangeByID':
            self.map_changes.append(self.mem.get(PARAM1, 0))
        elif name == 'LoadPlayerUnitsByStartingPositions':
            self.starts_loaded = True
        elif name in ('ChapterEnd', 'FinalChapterEnd'):
            self.ended = name
        if truth is not None:
            self.mem[TRUTH] = 1 if truth else 0

    # --- the script ---
    def run(self, ptr, limit=5000):
        if not ptr:
            return self
        a, bank, steps = ptr, ptr & 0xFF0000, 0
        while steps < limit:
            steps += 1
            c, args, nxt = command(a)
            if c in (0xFD, 0xFE, 0xFF):
                break
            if c in (0x02, 0x03, 0x04):
                go = c == 0x02 or (c == 0x03) == bool(self.mem.get(TRUTH, 0))
                a = bank | args[0] if go else nxt
                continue
            if c in (0x05, 0x06, 0x07):
                go = c == 0x05 or (c == 0x06) == bool(self.mem.get(TRUTH, 0))
                a = nxt + args[0] if go else nxt
                continue
            if c in (0x08, 0x09):
                # VoltEdge names these "less than", but the handler ($8C:8598) answers true when the value is at least the operand.
                self.mem[TRUTH] = 1 if (self.word(args[0]) & (0xFF if c == 0x08 else 0xFFFF)) >= args[1] else 0
            elif c in (0x0A, 0x0B):
                self.mem[TRUTH] = 1 if self.word(args[0]) == args[1] else 0
            elif c == 0x0C:
                self.world.flags.add(args[0])
                self.flag_sets.append(args[0])
            elif c == 0x0D:
                self.world.flags.discard(args[0])
                self.flag_clears.append(args[0])
            elif c == 0x0E:
                self.mem[TRUTH] = 1 if args[0] in self.world.flags else 0
            elif c in (0x0F, 0x10, 0x11):
                self.put(args[0], args[1])
                if c == 0x11:
                    self.mem[args[0] & 0xFFFFFF] = args[1]
            elif c in (0x12, 0x13, 0x14):
                self.put(args[0], self.word(args[1]))
            elif c in (0x15, 0x16, 0x17):
                if args[0] == CHAPTER:
                    self.chapter_add += args[1]
                self.put(args[0], self.word(args[0]) + args[1])
            elif c in (0x18, 0x19, 0x1A):
                self.put(args[0], self.word(args[0]) | args[1])
            elif c in (0x1B, 0x1C, 0x1D):
                self.asmc(args[0], args[1])
            elif c in (0x42, 0x43):
                self.load(args[0])
            elif c == 0x41:
                self.move(args[0], args[1], args[2], args[4])
            elif c == 0x46:
                self.move(args[0], args[1], args[2], 0)
            a = nxt
        return self

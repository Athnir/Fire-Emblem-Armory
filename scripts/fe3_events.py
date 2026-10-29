"""
Mystery of the Emblem's event scripts, read and played the way the game does ($87:81C9 dispatches a script's byte commands through the
table at $87:81E1). Used by scripts/build-fe3-maps.py to place each chapter's units where its opening leaves them, and to read what its
events hand out and when its reinforcements come. Formats and the routine behind each command are in data-raw/fe3/README.md.

A script runs in its own bank; its jumps are u16 within that bank.
"""
import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe3_rom as r  # noqa: E402

# Command -> (length, name). None: a variable length (AI), worked out in `length`.
COMMANDS = {
    0x00: (1, 'END'), 0x01: (3, 'CAMERA'), 0x02: (3, 'TALK'), 0x03: (4, 'SCROLL'), 0x04: (4, 'CURSOR'), 0x05: (2, 'SHOW'),
    0x06: (4, 'SCENE'), 0x07: (2, 'SOUND'), 0x08: (3, 'MUSIC'), 0x09: (9, 'PATHS'), 0x0A: (2, 'WAIT'), 0x0B: (2, 'REMOVE'),
    0x0C: (3, 'LOAD'), 0x0D: (4, 'SWAP'), 0x0E: (11, 'BATTLE'), 0x0F: (1, 'TILE_EVENT'), 0x10: (4, 'SHOP'), 0x11: (3, 'SET_FLAG'),
    0x12: (3, 'CLEAR_FLAG'), 0x13: (5, 'IF_FLAG'), 0x14: (3, 'GOTO'), 0x15: (4, 'GOLD'), 0x16: (5, 'ITEM'), 0x17: (1, 'TURN_EVENTS'),
    0x18: (None, 'AI'), 0x19: (1, 'AREA_EVENTS'), 0x1A: (1, 'TALK_EVENT'), 0x1B: (1, 'CHAR_EVENTS'), 0x1C: (7, 'SPAWN_SLOT'),
    0x1D: (1, 'SPAWN'), 0x1E: (1, 'COUNT_EVENTS'), 0x1F: (5, 'IF_PRESENT'), 0x20: (1, 'LEAVE_EVENT'), 0x21: (6, 'SET_TILE'),
    0x22: (2, 'TAKE_ITEM'), 0x23: (1, 'MENU'), 0x24: (4, 'SET_TURN'), 0x25: (2, 'SETTING'), 0x26: (5, 'TEXT_BOX'), 0x27: (1, 'ARENA'),
    0x28: (2, 'NAME_BOX'), 0x29: (4, 'IF_NO_ITEM'), 0x2A: (1, 'FLASH'), 0x2B: (2, 'BOOK_END'), 0x2C: (1, 'RELOAD_MAP'),
    0x2D: (1, 'CLEAR'), 0x2E: (2, 'SELECT'), 0x2F: (3, 'SOUND2'), 0x30: (3, 'SOUND3'), 0x31: (1, 'NEXT_CHAR_EVENT'), 0x32: (1, 'NOP'),
}
# Commands after which the script stops: END, and those that hand over to another script (a table's, by the event in hand).
STOPS = {0x00, 0x0F, 0x17, 0x19, 0x1A, 0x1B, 0x1D, 0x1E, 0x20, 0x31}

PLAYER, ENEMY = 'player', 'enemy'
# A path's directions (its 02 op), as (row, column) steps.
DIRS = {0: (0, -1), 1: (0, 1), 2: (-1, 0), 3: (1, 0)}


def length(a):
    c = r.u8(a)
    if c == 0x18:  # AI: three bytes, then characters ended by FF (FE: every enemy)
        n = 4
        while r.u8(a + n) != 0xFF:
            n += 1
        return n + 1
    return COMMANDS[c][0]


def command(a):
    """(address, command, operand bytes)."""
    n = length(a)
    return a, r.u8(a), bytes(r.R[r.lo(a) + 1:r.lo(a) + n])


def script(a, limit=600):
    """The commands from a, straight on until one that stops it."""
    out = []
    for _ in range(limit):
        a, c, ops = command(a)
        out.append((a, c, ops))
        if c in STOPS:
            break
        a += 1 + len(ops)
    return out


def reachable(a):
    """Every command a script can reach, following its jumps."""
    bank, seen, todo, out = a & 0xFF0000, set(), [a], []
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for at, c, ops in script(p):
            out.append((at, c, ops))
            if c == 0x13:
                todo.append(bank | ops[2] | ops[3] << 8)
            elif c == 0x14:
                todo.append(bank | ops[0] | ops[1] << 8)
            elif c == 0x1F:
                todo.append(bank | ops[2] | ops[3] << 8)
            elif c == 0x29:
                todo.append(bank | ops[1] | ops[2] << 8)
    return out


@dataclass
class World:
    """What the script can ask about: the flags set, the turn, who's in your army, which items it holds, and the choice answered."""
    flags: set = field(default_factory=set)
    turn: int = 1
    phase: int = 0
    army: set = field(default_factory=set)     # character ids in your army (IF_PRESENT's mode 0 also counts them)
    items: set = field(default_factory=set)    # item ids anyone in the army holds (IF_NO_ITEM)
    answer: bool = True                        # what a CHOICE is answered


class Run:
    """Plays scripts on one map: the units they place, move and remove, what they give, the slots they fill and the tiles they change."""

    def __init__(self, m, world=None, units=None):
        self.m = m
        self.world = world or World()
        self.event_list = {u['char']: u for u in r.unit_list(r.EVENT_UNITS, m)}
        self.units = list(units or [])     # in placement order: dicts with char, side, row, col, items...
        self.loads, self.removed, self.recruits = [], [], []
        self.items, self.gold, self.taken = [], [], []
        self.slots, self.tiles, self.calls = {}, [], []
        self.camera = [0, 0]                # column, row
        self.sprites = {}                   # path slot -> unit dict
        self.floating = set()               # ids of units whose sprite is still off the map

    # --- units ---
    def find(self, char):
        return next((u for u in self.units if u['char'] == char), None)

    def place(self, rec, side):
        """A unit into the next free slot. Generic units share a character id (0x45), so nothing is replaced."""
        u = {**rec, 'side': side, 'start': (rec['row'], rec['col'])}
        self.units.append(u)
        return u

    def load(self, char, side):
        rec = self.event_list.get(char)
        if rec is None:
            return None
        u = self.place(rec, side)
        self.loads.append(u)
        return u

    # --- paths ---
    def paths(self, bank, ops):
        for slot in range(4):
            p = ops[2 * slot] | ops[2 * slot + 1] << 8
            if p & 0x8000 == 0 or p == 0x8000:
                continue
            a = bank | p
            while r.u16(a) != 0xFFFF:
                op, val = r.u8(a), r.u8(a + 1)
                a += 2
                if op == 0x00:
                    u = self.find(val)
                    self.sprites[slot] = u
                    if u is not None and id(u) not in self.floating:
                        u['screen'] = [u['row'] - self.camera[1], u['col'] - self.camera[0]]
                        self.floating.add(id(u))
                    direction = None
                elif op == 0x02:
                    direction = val
                elif op == 0x05:
                    u = self.sprites.get(slot)
                    if u is not None:
                        if id(u) not in self.floating:
                            u['screen'] = [u['row'] - self.camera[1], u['col'] - self.camera[0]]
                            self.floating.add(id(u))
                        dr, dc = DIRS[direction]
                        u['screen'][0] += dr * (val // 16)
                        u['screen'][1] += dc * (val // 16)
                elif op == 0xFF:
                    # FF 02 sets the unit down where its sprite stands once the walk ends; FF 03 leaves it on the screen, to walk on
                    # (with the camera having moved meanwhile) in a later path of the same slot.
                    u = self.sprites.get(slot)
                    if u is not None and val & 1 == 0:
                        u['set_down'] = True

    def wait(self):
        for u in self.units:
            if id(u) in self.floating and u.pop('set_down', False):
                u['row'] = u['screen'][0] + self.camera[1]
                u['col'] = u['screen'][1] + self.camera[0]
                self.floating.discard(id(u))

    def settle(self):
        """At the script's end every walk has finished."""
        for u in self.units:
            if id(u) in self.floating:
                u['row'] = u['screen'][0] + self.camera[1]
                u['col'] = u['screen'][1] + self.camera[0]
                u.pop('set_down', None)
        self.floating.clear()

    # --- the script ---
    def run(self, a, limit=2000):
        bank = a & 0xFF0000
        for _ in range(limit):
            at, c, ops = command(a)
            nxt = a + 1 + len(ops)
            if c in STOPS:
                self.calls.append(COMMANDS[c][1])
                break
            if c == 0x01:
                self.camera = [ops[0], ops[1]]
            elif c == 0x03:
                self.camera = [ops[0], ops[1]]
            elif c == 0x09:
                self.paths(bank, ops)
            elif c == 0x0A:
                self.wait()
            elif c == 0x0B:
                # Every unit with the character goes ($87:86F6 repeats until none is left).
                for u in [u for u in self.units if u['char'] == ops[0]]:
                    self.units.remove(u)
                    self.removed.append(u)
            elif c == 0x0C:
                self.load(ops[1], PLAYER if ops[0] == 0 else ENEMY)
            elif c == 0x0D:
                # The unit [old] is taken off and [new], from the chapter's list, joins your army on its tile.
                old = self.find(ops[2])
                new = self.event_list.get(ops[1])
                if new is not None:
                    tile = (old['row'], old['col']) if old else (new['row'], new['col'])
                    if old:
                        self.units.remove(old)
                    u = self.place({**new, 'row': tile[0], 'col': tile[1]}, PLAYER)
                    self.recruits.append(u)
            elif c == 0x11:
                self.world.flags.add(ops[0] | ops[1] << 8)
            elif c == 0x12:
                self.world.flags.discard(ops[0] | ops[1] << 8)
            elif c == 0x13:
                if (ops[0] | ops[1] << 8) in self.world.flags:
                    nxt = bank | ops[2] | ops[3] << 8
            elif c == 0x14:
                nxt = bank | ops[0] | ops[1] << 8
            elif c == 0x15:
                self.gold.append(ops[0] | ops[1] << 8)
            elif c == 0x16:
                self.items.append((ops[0], None if ops[2] == 0xFF else ops[2]))
            elif c == 0x1C:
                self.slots[ops[0]] = {'count': ops[1], 'chance': ops[2], 'col': ops[3], 'row': ops[4], 'unit': ops[5]}
            elif c == 0x1F:
                # Mode 0 asks your army and the map, any other mode the map alone.
                here = self.find(ops[0]) is not None or (ops[1] == 0 and ops[0] in self.world.army)
                if here:
                    nxt = bank | ops[2] | ops[3] << 8
            elif c == 0x21:
                self.tiles.append({'col': ops[1], 'row': ops[2], 'tile': ops[3] | ops[4] << 8})
            elif c == 0x22:
                self.taken.append(ops[0])
            elif c == 0x29:
                if ops[0] not in self.world.items:
                    nxt = bank | ops[1] | ops[2] << 8
            elif c in (0x10, 0x27, 0x2B):
                self.calls.append((COMMANDS[c][1], tuple(ops)))
            a = nxt
        self.settle()
        return self

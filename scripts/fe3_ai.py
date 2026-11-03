"""
Mystery of the Emblem's unit AI, read from the scripts a unit's AI bytes name (unit record +16..+18, copied to the unit's +0x18, +0x1A
and +0x1C at $83:DD53). Used by scripts/build-fe3-maps.py for the looter badge, the exits a unit leaves by, where its AI sends it, whom
it comes to talk to, and which foes never attack. Formats are in data-raw/fe3/README.md.

Each enemy phase a unit runs its decision script, then, if that settles nothing, its movement script (the driver at $82:8000, states 4
and 5). Only a decision attacks: the movement commands only move (they end with action 0x0B, wait: $82:970F).
- Decision scripts (AI1, +16): u16 pointers 3 bytes apart at $88:C46C (bank $88), run by $82:85B1. A byte below 0x10 is an attack
  decision with one operand ($82:8AA8); 0x10 and 0x11 are attack decisions too, 0x14 [chance] attacks only that % of the time, 0x12
  ends the script, and 0x13 [character][talk][0] walks the unit to that character, if it's on the map, and starts that talk ($82:8711).
  Script 0x02 is the lone 0x12: a unit with it never attacks.
- Movement scripts (AI2, +17): u16 pointers 3 bytes apart at $88:C5E1, read by $82:8C63 through the command table at $82:8CCE:
  [command][operands], commands (with their lengths): 0 loop back (2); 1 [name][moves] hold while a unit of that name is on the map (3,
  $93:D52E); 2 [class group][moves] advance on the nearest unit of that class group, FF any (3, $82:90EE); 3 [moves] stay (2: it moves
  toward its own tile, $82:95E0); 4 [group][moves] go to the nearest tile of a terrain group (3, $82:91AB, the groups at $88:CB7A);
  5 [column][row][moves] go to that tile, then the next command (4, $82:9040); 6 [n][0] run leave script n (3, u16 pointers at
  $8B:91F7: a walk off the map, then REMOVE; Book 1's Chapter 8 has one that opens a door instead); 7 [0] use a staff (2); 8 [n][0]
  loot: go for the nearest village (terrain group 3) or chest (group 9) it can reach, raze it ($83:9A34) or empty it, and after n chests,
  or with none left, the next command (3, $82:8D2F); 9 a Manakete's change (1). [moves] is how far it may move a turn: 0 holds it still.
- Event command 0x18 [AI1][AI2][AI3][character]...FF gives every unit of each character (FE: every enemy) new AI from the start of its
  scripts ($87:9BC0).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe3_events as fe  # noqa: E402
import fe3_rom as r  # noqa: E402

MOVES, DECISIONS, LEAVES, GROUPS = 0x88C5E1, 0x88C46C, 0x8B91F7, 0x88CB7A
LENGTH = {0: 2, 1: 3, 2: 3, 3: 2, 4: 3, 5: 4, 6: 3, 7: 2, 8: 3, 9: 1}
PASSIVE = 0x02  # the decision script with no decisions
# The terrain groups ($88:CB7A), by what the maps call them.
GROUP_NAMES = {0: 'castle tile', 1: 'fort', 2: 'tunnel', 3: 'village', 4: 'shop', 5: 'house', 6: 'mountain', 7: 'bridge', 8: 'forest',
               9: 'chest', 10: 'drawbridge', 11: 'door', 12: 'plain'}


def terrain_groups():
    """[set of terrain ids] per group: FF-ended lists, the table ending with an empty one ($82:9834)."""
    out, a = [], GROUPS
    while r.u8(a) != 0xFF:
        ids = set()
        while r.u8(a) != 0xFF:
            ids.add(r.u8(a))
            a += 1
        out.append(ids)
        a += 1
    return out


def leave_script(n):
    """Leave script n's commands."""
    return fe.script(0x8B0000 | r.u16(LEAVES + 2 * n))


def leaves_map(n):
    """Leave script n takes the unit off the map (REMOVE): it walks off from the tile it went to."""
    return any(c == 0x0B for _, c, _ in leave_script(n))


def moves(k):
    """Movement script k as [(command, operands)], up to the command it stays on: a loop, a hold, an advance on any unit (with no
    target it stays), a terrain goal (once there, its own tile is the nearest), a stay, a staff, or a leave that takes it off. Going to a
    tile, looting and a Manakete's change go on to the next command."""
    a, out = 0x880000 | r.u16(MOVES + 3 * k), []
    for _ in range(64):
        c = r.u8(a)
        assert c in LENGTH, (k, hex(a), c)
        ops = [r.u8(a + i) for i in range(1, LENGTH[c])]
        out.append((c, ops))
        if c in (0, 1, 2, 3, 4, 7) or (c == 6 and leaves_map(ops[0])):
            break
        a += LENGTH[c]
    return out


def talk_goals(k):
    """[(character, talk id)] for decision script k's talks (0x13), in the order it tries them."""
    a, out = 0x880000 | r.u16(DECISIONS + 3 * k), []
    for _ in range(16):
        v = r.u8(a)
        if v in (0x12, 0xFF):
            break
        if v == 0x13:
            out.append((r.u8(a + 1), r.u8(a + 2)))
            a += 4
        else:
            a += 2
    return out


def plan(ai):
    """What AI bytes make a unit do: {'passive': never attacks, 'talks': [(character, talk id)], 'steps': [step]}, the steps in order:
    ('tile', (row, column)), ('leave', script, takes it off), ('loot', chests), ('terrain', group), ('advance',), ('hold',), ('staff',)
    (a Manakete's change is left out). An AI1 of FF is none at all."""
    a1, a2, _ = ai
    if a1 == 0xFF:
        return {'passive': False, 'talks': [], 'steps': [('hold',)]}
    steps = []
    for c, ops in moves(a2):
        if c == 5:
            steps.append(('tile', (ops[1], ops[0])))
        elif c == 6:
            steps.append(('leave', ops[0], leaves_map(ops[0])))
        elif c == 8:
            steps.append(('loot', ops[0]))
        elif c == 4:
            steps.append(('terrain', ops[0]))
        elif c == 2:
            assert ops[0] == 0xFF, ai  # every advance in the game goes for any class
            steps.append(('advance',) if ops[1] else ('hold',))
        elif c in (0, 1, 3):
            steps.append(('hold',))
        elif c == 7:
            steps.append(('staff',))
    return {'passive': a1 == PASSIVE, 'talks': talk_goals(a1), 'steps': steps}


def rewrites(ptr):
    """[(AI bytes, [character])] for the AI a script gives (event command 0x18), on every branch it can take."""
    out = []
    for _, c, ops in fe.reachable(ptr):
        if c == 0x18:
            out.append((tuple(ops[:3]), [x for x in ops[3:] if x != 0xFF]))
    return out

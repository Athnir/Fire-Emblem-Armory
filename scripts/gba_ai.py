"""
What a GBA unit's movement AI does, read from each game's AI scripts (The Binding Blade, The Blazing Blade, The Sacred Stones): who
goes for the villages and chests, and who leaves the map, by which exits. Used by the three maps generators.

What the engine does was read in the program code (Thumb, capstone), the same in all three games:
  - A unit record's second AI byte (FE6 / FE7 +0xD, FE8 +0x11; the loaders copy it to the unit's +0x44: 0x08030A92, 0x0803735E,
    0x0803C266) picks a script from a pointer table (the pointer to it at FE6 0x085C97EC, FE7 0x08B989E4, FE8 0x085A91D8). A script
    is 16-byte commands, the command in byte 0, run by an interpreter whose 28 handlers sit in one table (FE6 0x0810D688, FE7
    0x081D3678, FE8 0x080D80FC). A command that acts ends the unit's turn; one with nothing to do steps to the next. The ones read:
      0x10 go for the nearest village it can reach (terrain 3, 0x24 and, in FE7 and FE8, 0x37, which some villages stand on) or, for a
           unit holding a Chest Key, or a Lockpick with the class ability that uses it (abilities +0x28, bit 2), and fewer than five
           items, a chest (0x21), and raze or loot it there; with nothing left it steps on (FE7 0x08037DD0, the lists read by
           0x080369F4, the item check 0x08036A8C);
      0x02 change the unit's AI (byte 1 the first AI, byte 2 this one; 0xFF keeps it);
      0x03 back to the start of the script;
      0x0E wait out the turn;
      0x17 make for the nearest of the chapter's escape points and leave the map (FE7 0x08038030 -> 0x0803993C): a list per
           chapter for foes and one for other armies' units, 4 bytes a point (x, y first), ended by x = 0xFF.
"""
import struct

GAMES = {
    # The AI2 table's pointer, the raiders' and the key holders' terrain lists, the Chest Key and Lockpick, the escape point tables
    # (foes, other armies).
    'fe6': {'ai2': 0x085C97EC, 'raid': 0x085C864C, 'keys': 0x085C864F, 'chest_key': 0x64, 'lockpick': 0x67,
            'escapes': (0x085C86B8, 0x085C876C)},
    'fe7': {'ai2': 0x08B989E4, 'raid': 0x08B97098, 'keys': 0x08B9709C, 'chest_key': 0x68, 'lockpick': 0x6A,
            'escapes': (0x08B97100, 0x08B971C0)},
    'fe8': {'ai2': 0x085A91D8, 'raid': 0x085A8120, 'keys': 0x085A8124, 'chest_key': 0x69, 'lockpick': 0x6B,
            'escapes': (0x085A8188, 0x085A828C)},
}
LOOT, CHANGE, RESTART, WAIT, ESCAPE = 0x10, 0x02, 0x03, 0x0E, 0x17
CHEST = 0x21


class Ai:
    def __init__(self, game, R):
        self.cfg, self.R = GAMES[game], R

    def u32(self, a):
        return struct.unpack_from('<I', self.R, a - 0x08000000)[0]

    def terrains(self, at):
        o, out = at - 0x08000000, []
        while self.R[o]:
            out.append(self.R[o])
            o += 1
        return out

    def behaviour(self, ai2):
        """What a second AI byte does, following its script from the start: {'loots', 'escapes', 'waits'} (waits: turns spent before
        it acts), or None when it does neither."""
        table = self.u32(self.cfg['ai2'])
        seen, out = set(), {'loots': False, 'escapes': False, 'waits': 0}
        while ai2 not in seen:
            seen.add(ai2)
            p = self.u32(table + 4 * ai2)
            for k in range(64):
                c = self.R[p - 0x08000000 + 16 * k:p - 0x08000000 + 16 * k + 16]
                if c[0] == LOOT:
                    out['loots'] = True
                elif c[0] == WAIT and not out['loots']:
                    out['waits'] += 1
                elif c[0] == ESCAPE:
                    out['escapes'] = True
                    break
                elif c[0] == CHANGE and c[2] == 0xFF:
                    continue  # only the first AI changes: this script steps on
                elif c[0] == CHANGE and c[2] != ai2:
                    ai2 = c[2]
                    break
                else:
                    ai2 = None  # another command, or back to the start: nothing more to follow
                    break
            if ai2 is None:
                break
        return out if out['loots'] or out['escapes'] else None

    def opens_chests(self, items, abilities):
        """Whether a looter goes for chests too: a Chest Key, or a Lockpick and the class ability that uses it (bit 2)."""
        return len(items) < 5 and (self.cfg['chest_key'] in items or (self.cfg['lockpick'] in items and abilities & 4))

    def escape_points(self, chapter, side):
        """The chapter's escape points for foes ('enemy') or another army's units, as (x, y) from the top-left."""
        lst = self.u32(self.cfg['escapes'][0 if side == 'enemy' else 1] + 4 * chapter)
        if not 0x08000000 <= lst < 0x0A000000:
            return []
        o, out = lst - 0x08000000, []
        while self.R[o] != 0xFF:
            out.append((self.R[o], self.R[o + 1]))
            o += 4
        return out


def of(ai, u, abilities):
    """A unit's '_ai' mark for settle(): what its movement AI does, or None. `u` is a record from the game's unit groups ('ai',
    'items', 'side')."""
    if not u.get('ai') or u['side'] == 'player':
        return None
    b = ai.behaviour(u['ai'][1])
    if not b:
        return None
    return {**b, 'chests': b['loots'] and bool(ai.opens_chests(u['items'], abilities)), 'side': u['side']}


DOES = {('villages',): 'razing what it reaches', ('chests',): 'emptying what it reaches',
        ('villages', 'chests'): 'razing or emptying what it reaches'}


def settle(m, ai, chapter, to_app):
    """Turns each unit's and joiner's '_ai' mark into what the map says: the looter badge and what it goes for, the exits it leaves
    by (`goesTo`), and on each village the looters on the map at the start that can raze it. `to_app(xy)` converts a top-left tile.
    A unit the chapter's script takes off the map (its note says so) doesn't get the AI's exit as well."""
    h, w = m['height'], m['width']
    has = {k: any(o['type'] == k for o in m['objects']) for k in ('village', 'chest')}
    raiders = []
    every = ([(u, True) for u in m['units']] + [(u, False) for g in m.get('reinforcements', []) for u in g['units']]
             + [(j, False) for j in m.get('joiners', [])])
    for u, at_start in every:
        a = u.pop('_ai', None)
        if not a:
            continue
        exits = [t for t in (to_app(p) for p in ai.escape_points(chapter, a['side'])) if 1 <= t[0] <= w and 1 <= t[1] <= h]
        goes = tuple(k for k, on in (('villages', has['village']), ('chests', a['chests'] and has['chest'])) if on)
        leaves = a['escapes'] and exits and 'leaves the map' not in (u.get('note') or '')
        if a['loots'] and goes:
            u['looter'] = True
            wait = 'after a turn, ' if a['waits'] == 1 else f"after {a['waits']} turns, " if a['waits'] else ''
            what = f"{wait}goes for the {' and '.join(goes)}, {DOES[goes]}"
            if leaves:
                what += ', then leaves the map by an exit'
            if 'villages' in goes and at_start:
                raiders.append(u['name'])
        elif leaves:
            what = 'makes for an exit and leaves the map'
        else:
            continue
        u['note'] = f"{u['note']}; {what}" if u.get('note') else what[0].upper() + what[1:]
        if leaves:
            u['goesTo'] = exits
    if raiders:
        raze = f"{' or '.join(dict.fromkeys(raiders))} can raze it before you visit."
        for o in m['objects']:
            if o['type'] == 'village':
                o['note'] = f"{raze} {o['note']}" if o.get('note') else raze

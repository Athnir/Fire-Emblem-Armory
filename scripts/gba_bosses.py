"""
Which boss-flagged units are a GBA chapter's own boss (The Binding Blade, The Blazing Blade, The Sacred Stones), as the map's
skull: the rest only pass through (a named foe, or a plain foe for a generic one).

Each game keeps a death-quote table read when a character dies (one entry per character and chapter, or any chapter); the
entry's flag is set by the death, and flag 2 is the boss's fall: The Binding Blade's Hard-only turn events and The Blazing
Blade's conditioned ones stop once it's set, and the games' "defeat the boss" endings wait for it.
  - The Binding Blade: 0x08666598 (read by 0x0806B808), 16 bytes: character, chapter (0x2D any), text, flag (u32 at +8).
  - The Blazing Blade: 0x08C9F2EC (0x080796C8), 16 bytes: character, chapter (0x43 any), text, event, flag (u32 at +0xC).
  - The Sacred Stones: 0x089ECD4C (0x0808472C), 12 bytes: character (u16), route, chapter (0xFF any), flag (u16 at +4), text,
    event.
A unit the chapter's script takes off the map passes through. Of the rest, those whose death sets flag 2 in this chapter are its
boss; with none (a seize or defend map: The Sacred Stones' Caellach), every boss-flagged unit left is. Where that still leaves
more than one character on a seize map, the one on a seize tile is the boss (The Binding Blade's Chapter 13: Narcian, at the gate).
"""
import struct

TABLES = {
    'fe6': (0x08666598, 16, lambda R, o: (R[o], R[o + 1], struct.unpack_from('<I', R, o + 8)[0]), 0x2D),
    'fe7': (0x08C9F2EC, 16, lambda R, o: (R[o], R[o + 1], struct.unpack_from('<I', R, o + 12)[0]), 0x43),
    'fe8': (0x089ECD4C, 12, lambda R, o: (struct.unpack_from('<H', R, o)[0], R[o + 3], struct.unpack_from('<H', R, o + 4)[0]), 0xFF),
}
BOSS_DOWN = 2


def boss_down(game, R, chapter):
    """The characters whose death sets flag 2 in this chapter (its index in the game's chapter table)."""
    at, size, read, anywhere = TABLES[game]
    out, o = set(), at - 0x08000000
    while True:
        char, chap, flag = read(R, o)
        if not char:
            return out
        if flag == BOSS_DOWN and chap in (anywhere, chapter):
            out.add(char)
        o += size


def settle(m, down, plain):
    """Leaves the skull on the chapter's own boss only, in place. Each unit entry carries `_char` (and `_leaves` when the chapter's
    script takes it off the map), which this removes; `plain(char)`: a generic character, a plain foe once it's no boss."""
    units = m['units'] + [u for g in m.get('reinforcements', []) for u in g['units']]
    bosses = [u for u in units if u['type'] == 'boss' and '_char' in u]
    stay = [u for u in bosses if not u.get('_leaves')]
    chosen = [u for u in stay if u['_char'] in down] or stay
    seize = {tuple(t) for o in m.get('objectives', []) if o['type'] == 'seize' for t in o['tiles']}
    if len({u['_char'] for u in chosen}) > 1 and seize:
        holders = {u['_char'] for u in chosen if tuple(u['tile']) in seize}
        if holders:
            chosen = [u for u in chosen if u['_char'] in holders]
    keep = {id(u) for u in chosen}
    for u in bosses:
        if id(u) not in keep:
            u['type'] = 'enemy' if plain(u['_char']) else 'named'
    for u in units:
        u.pop('_char', None)
        u.pop('_leaves', None)


def army_names(names, has_portrait):
    """Names the game gives a whole army or role rather than a person: shared by several characters, at least one of them with no
    portrait ('Monster', 'Enemy' and Chapter 5's 'Bandit' in The Sacred Stones, 'Black Fang' in The Blazing Blade, 'Bandit' in The
    Binding Blade). A unit of one goes by its class. A person's several versions (Lyon, Valter, Lloyd) all have portraits; a
    one-off with none (Morva, Fomortiis, the Fire Dragon) keeps its name."""
    by = {}
    for c, n in names.items():
        if n:
            by.setdefault(n, []).append(c)
    return {n for n, cs in by.items() if len(cs) > 1 and any(not has_portrait(c) for c in cs)}

"""
What the maps generators of The Blazing Blade and The Sacred Stones share (scripts/build-fe7-maps.py, build-fe8-maps.py): the terrain
table with its movement types, tile conversions, and writing the generated files. The Binding Blade's generator
(scripts/build-fe6-maps.py) does the same things for its own ROM.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gba_doors  # noqa: E402
import gba_walls  # noqa: E402
from terrain_codes import encode  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data')

# Terrain ids -> the letters terrain_codes.py maps for 'fe7' and 'fe8' (the same ids as The Binding Blade's, plus the new ones from
# 42 up); ids that work the same share a letter. Names are the app's. Terrain 55, which the game calls Ruins as it does 37, is a
# village: village events stand on it and looters go for it (the raiders' terrain list, scripts/gba_ai.py).
TERRAIN = {
    0: ('#', 'Void'), 1: ('G', 'Plain'), 2: ('O', 'Road'), 3: ('v', 'Village'), 4: ('V', 'Closed village'), 5: ('B', 'House'),
    6: ('W', 'Armory'), 7: ('I', 'Vendor'), 8: ('R', 'Arena'), 10: ('F', 'Fort'), 11: ('g', 'Gate'), 12: ('f', 'Forest'),
    13: ('k', 'Thicket'), 14: ('y', 'Sand'), 15: ('s', 'Desert'), 16: ('w', 'River'), 17: ('m', 'Mountain'), 18: ('P', 'Peak'),
    19: ('b', 'Bridge'), 20: ('b', 'Bridge'), 21: ('a', 'Sea'), 22: ('u', 'Lake'), 23: ('T', 'Floor'), 24: ('q', 'Floor (Res +10)'),
    25: ('l', 'Fence'), 26: ('#', 'Wall'), 27: ('#', 'Wall'), 29: ('p', 'Pillar'), 30: ('d', 'Door'), 31: ('t', 'Throne'),
    32: ('c', 'Chest'), 33: ('c', 'Chest'), 34: ('#', 'Roof'), 35: ('g', 'Gate'), 37: ('n', 'Ruins'), 38: ('C', 'Cliff'),
    39: ('L', 'Ballista'), 40: ('L', 'Long ballista'), 41: ('L', 'Killer ballista'), 42: ('X', 'Flat'), 44: ('#', 'Wall'),
    45: ('S', 'Stairs'), 46: ('C', 'Village wall'), 47: ('J', 'Glacier'), 49: ('z', 'Valley'), 51: ('#', 'Snag'),
    52: ('j', 'Bridge'), 53: ('Z', 'Sky'),
    54: ('D', 'Deeps'), 55: ('v', 'Ruins (village)'), 56: ('B', 'Inn'), 57: ('C', 'Barrel'), 58: ('C', 'Bone'), 59: ('x', 'Dark'),
    60: ('u', 'Water'), 61: ('C', 'Gunnel'), 62: ('A', 'Deck'), 63: ('#', 'Brace'), 64: ('#', 'Mast'),
}

# What a game reads differently: The Sacred Stones' terrain 35, a gate with more Avoid than its terrain 11.
GAME_TERRAIN = {'fe7': TERRAIN, 'fe8': {**TERRAIN, 35: ('Y', 'Castle gate')}}


def move_groups(r, names):
    """The game's movement types: classes whose cost rows are the same, named by `names` (a class id in the group -> the label).
    Every row must have a name, so a new kind of movement can't go unnoticed."""
    groups = {}
    for c in range(1, r.class_count()):
        if not r.u16(r.cfg['classes'] + 84 * c):
            continue
        if r.class_(c)['move_cost'] < 0:
            # No movement row at all (The Sacred Stones' Gorgon Eggs never move): not a movement type.
            continue
        row = bytes(r.R[r.class_(c)['move_cost']:r.class_(c)['move_cost'] + r.cfg['terrains']])
        groups.setdefault(row, []).append(c)
    out = []
    for row, classes in groups.items():
        label = next((names[c] for c in classes if c in names), None)
        assert label, f'no name for the movement row of classes {classes}'
        out.append((label, classes, row))
    order = list(dict.fromkeys(names.values()))
    return sorted(out, key=lambda g: order.index(g[0]))


def terrain_table(r, game, used, groups, flier_label='Fliers'):
    """One entry per terrain code: name, Def, Res, Avoid, healing and the cost for each movement type (None: can't enter). Terrain
    stats are the ground rows the first class points at; fliers' rows give no Avoid or Def."""
    lord = r.class_(1)
    info = {}
    for tid in sorted(used):
        # A wall is listed under each kind it's drawn as (scripts/gba_walls.py).
        for letter, name in gba_walls.table_letters(game, tid, *GAME_TERRAIN[game][tid]):
            code = encode(game, letter)
            # 255 is "can't enter"; so is 0 (the Fire Dragon, which never moves, has 0 on a few tiles).
            move = {label: (None if row[tid] in (0, 255) else row[tid]) for label, _, row in groups}
            entry = {'name': name, 'def': r.s8(lord['terrain_def'] + tid), 'res': r.s8(lord['terrain_res'] + tid),
                     'avo': r.s8(lord['terrain_avoid'] + tid), 'heal': r.R[r.cfg['heal'] + tid], 'move': move}
            walkers = [v for k, v in move.items() if k != flier_label]
            if all(v is None for v in walkers):
                entry['def'] = entry['avo'] = 0
            if code in info:
                old = info[code]
                same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}
                nobody = all(v is None for v in move.values())
                assert same or nobody, (code, tid, old, entry)
                if name.lower() not in old['name'].lower():
                    old['name'] += ' / ' + name.lower()
            else:
                info[code] = entry
    return info


def add_closed_rooms(info, game, maps, groups):
    """The closed room's entry (scripts/gba_doors.py), where any map starts with one."""
    code = encode(game, 'Q')
    if any(code in [row[i:i + 2] for i in range(0, len(row), 2)] for m in maps for row in m['grid']):
        info[code] = gba_doors.closed_room([label for label, _, _ in groups])


def flier_rows_are_zero(r, flier_class):
    c = r.class_(flier_class)
    n = r.cfg['terrains']
    return set(r.R[c['terrain_avoid']:c['terrain_avoid'] + n]) == {0} and set(r.R[c['terrain_def']:c['terrain_def'] + n]) == {0}


def to_app(xy, height):
    """A tile from the top-left at (0, 0) -> the app's, from the bottom-left at (1, 1)."""
    return [xy[0] + 1, height - xy[1]]


def rect_to_app(rect, height):
    x1, y1, x2, y2 = rect
    return [x1 + 1, height - y2, x2 + 1, height - y1]


def article(name):
    return ('an ' if name[0].lower() in 'aeiou' else 'a ') + name


def write(game, name, lines):
    out = os.path.join(ROOT, game, name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def write_terrain(game, title, script, info, groups, cls, fliers='Fliers get no Def or Avoid from terrain.'):
    """`fliers`: what the game's code gives fliers on terrain, for the table's comment ('' where it isn't traced)."""
    G = game.upper()
    examples = {label: ', '.join(sorted({cls[c] for c in classes if cls.get(c)})) for label, classes, _ in groups}
    lines = [
        "import type { TerrainInfo } from '../maps/fatesTerrain'",
        "import type { TerrainCode } from '../maps/terrainCodes'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s terrain and movement cost tables. Do not edit by hand.",
        ' */',
        '',
        '/** Movement types the game gives different costs: classes in a group pay the same on every terrain. */',
        f'export const {G}_MOVE_CLASSES = ' + json.dumps([label for label, _, _ in groups]) + ' as const',
        '',
        f'export const {G}_MOVE_CLASS_EXAMPLES: Record<string, string> = ' + json.dumps(examples, indent=2, ensure_ascii=False),
        '',
        "/** Def, Res, Avoid, healing and movement cost (null = can't enter) by terrain code." + (f' {fliers}' if fliers else '') + ' */',
        f'export const {G}_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {{',
    ]
    lines += [f'  {code}: {json.dumps(entry, ensure_ascii=False)},' for code, entry in info.items()]
    lines.append('}')
    write(game, f'{game}Terrain.ts', lines)


def write_maps(game, title, script, maps):
    G = game.upper()
    lines = [
        "import type { ChapterMap } from '../maps/types'",
        f"import {{ {G}_TERRAIN }} from './{game}Terrain'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s own chapter records and events. Do not edit by hand.",
        ' */',
        '',
        'const RAW = [',
    ]
    lines += ['  ' + json.dumps(m, ensure_ascii=False) + ',' for m in maps]
    lines += [']', '', f'export const {G}_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({{ ...m, terrain: {G}_TERRAIN }}))']
    write(game, f'{game}Maps.ts', lines)


def mark_difficulties(sources, held, every):
    """Each line of `sources` ({item: [line]}) that holds on only some of its map's difficulties says which, in the game's order.
    `held`: (item, map id, kind, text) -> the difficulties a line holds on (those of the units it's written from, all of them for a
    line from anything else; a line several units give holds on all of theirs); `every`: map id -> the difficulties it's played on."""
    for name, lst in sources.items():
        for s in lst:
            on = held.get((name, s['mapId'], s['kind'], s['text']))
            if on is not None and not set(every[s['mapId']]) <= on:
                s['difficulties'] = [d for d in every[s['mapId']] if d in on]


def write_sources(game, title, script, sources, prefixes=(), diffs=()):
    G = game.upper()
    # What a foe carries is only worth saying where nothing else gives it (it shows who carries a foe-only weapon): thieves steal
    # items, not weapons, so a weapon a foe holds and doesn't drop never reaches you. `prefixes` are kinds' prefixes that only say
    # where a source is (Echoes' 'amiibo-'): a prefixed 'foe' is still a foe's.
    # It's decided difficulty by difficulty (`diffs`, the game's, in order; a game without any has one): a foe's line keeps the
    # difficulties no other line of the item holds on, and goes where none are left. A line without `difficulties` holds on all.
    every = list(diffs) or ['']

    def bare(kind):
        for pre in prefixes:
            if kind.startswith(pre):
                return kind[len(pre):]
        return kind

    def foe(s):
        return bare(s['kind']).startswith('foe')
    out = {}
    for name, lst in sources.items():
        covered = {d for s in lst if not foe(s) for d in s.get('difficulties', every)}
        out[name] = []
        for s in lst:
            if not foe(s):
                out[name].append(s)
                continue
            left = [d for d in s.get('difficulties', every) if d not in covered]
            if left:
                line = {k: v for k, v in s.items() if k != 'difficulties'}
                line['kind'] = s['kind'].replace('-generic', '')
                if len(left) < len(every):
                    line['difficulties'] = left
                out[name].append(line)
    lines = [
        "import type { ItemSource } from '../../components/ChapterWeapons'",
        '',
        '/*',
        f" * GENERATED by scripts/{script} from {title}'s event scripts and shop lists. Do not edit by hand.",
        ' */',
        '',
        '/** Where each item turns up, by chapter: shops, chests, villages and houses, hidden spots, talks, what a recruit carries, the',
        " * end of a chapter, and what foes carry ('-later': a foe who arrives mid-chapter, seen from the next chapter). */",
        f'export const {G}_ITEM_SOURCES: Record<string, ItemSource[]> = ' + json.dumps(out, indent=2, ensure_ascii=False),
    ]
    write(game, f'{game}ItemSources.ts', lines)


def trap_records(r, ptr):
    """A chapter's trap list: 6-byte records up to a 0 type (The Blazing Blade's loader 0x080345EC, The Sacred Stones' 0x08037840):
    type, x, y, then three bytes the type reads."""
    out = []
    if not r.is_ptr(ptr):
        return out
    o = r.off(ptr)
    while r.R[o]:
        out.append(tuple(r.R[o:o + 6]))
        o += 6
    return out


def _every(countdown, interval):
    count = lambda n: f'{n} turn' + ('' if n == 1 else 's')  # noqa: E731
    first = f'the first time after {count(countdown)}' if countdown else 'from the first turn'
    every = 'every turn' if interval == 1 else f'every {interval} turns'
    return f'{every}, {first}' if interval else f'once, after {count(countdown)}'


def trap_unconfirmed(objects):
    """What isn't confirmed about the map's traps: when in the turn they tick over, and what gas and arrows do."""
    kinds = {o['kind'] for o in objects if o['type'] == 'trap'}
    if not kinds:
        return None
    what = [w for k, w in (('gas', "what a gas vent's gas does"), ('arrow', "what an arrow launcher's arrows do")) if k in kinds]
    return "When in the turn a trap's countdown ticks over" + (', and ' + ' and '.join(what) if what else '') + (
        ", aren't confirmed." if what else " isn't confirmed.")


def trap_objects(records, h, item_name, diffs=None):
    """Map objects for a chapter's traps. A ballista (type 1: the item in byte 3) is fired by an Archer or Sniper standing on it
    (class ability 0x80). A fire tile (4), a gas vent (5: its facing in byte 3) and an arrow launcher (7: The Sacred Stones', a
    column) count down from byte 4 once a turn and go off when it runs out, then every byte 5 turns (The Sacred Stones 0x0802E9A8);
    a fire tile's bursts do 10 damage (the 10 its constructor keeps, 0x0802BB24 / 0x0802E314)."""
    out = []
    extra = {'difficulties': diffs} if diffs else {}
    for t, x, y, b3, b4, b5 in records:
        tile = to_app((x, y), h)
        if t == 1:
            out.append({'type': 'ballista', 'tile': tile, 'machine': tile, 'weapon': item_name(b3), 'mounted': True, **extra})
        elif t == 4:
            out.append({'type': 'trap', 'tile': tile, 'kind': 'fire', **extra,
                        'note': f'Fire bursts from it {_every(b4, b5)}: 10 damage to a unit standing on it.'})
        elif t == 5:
            out.append({'type': 'trap', 'tile': tile, 'kind': 'gas', **extra, 'note': f'It lets out gas {_every(b4, b5)}.'})
        elif t == 7:
            out.append({'type': 'trap', 'tile': to_app((x, 0), h), 'kind': 'arrow', **extra,
                        'note': f'It fires arrows down column {x + 1} {_every(b4, b5)}.'})
    return out


# One group per arrival (CLAUDE.md), for all three games' arrivals (The Binding Blade's generator uses it too).
LEVEL = re.compile(r'^Lv (\d+)(?: \(([^)]*)\))?')
TURNS = re.compile(r'^(?:Turn (\d+)|Every turn from (\d+) to (\d+)|Every turn from (\d+)|Every turn), (.+)$')
VAGUE = re.compile(r'an event in the chapter|During the chapter')  # times that don't say what sets them off


def _unit_key(u):
    """A unit entry but for its difficulties and its level."""
    m = LEVEL.match(u.get('note') or '')
    rest = (u.get('note') or '')[m.end():] if m else u.get('note')
    return json.dumps({**{k: v for k, v in u.items() if k not in ('difficulties', 'note')}, 'note': rest}, sort_keys=True)


def _levels(u, diffs):
    """{difficulty: level} a unit entry's note gives, for the difficulties it's on."""
    m = LEVEL.match(u.get('note') or '')
    if not m:
        return {}
    others = {d: int(v) for d, v in (x.rsplit(' ', 1) for x in m.group(2).split(', '))} if m.group(2) else {}
    return {d: others.get(d, int(m.group(1))) for d in (u.get('difficulties') or diffs)}


def _merge_units(lists, diffs):
    """Several lists of unit entries as one: a unit they share (the same but for its difficulties and level) is one entry on all
    their difficulties, its level per difficulty; two identical units in one list stay two."""
    copies = {}
    for units in lists:
        seen = {}
        for u in units:
            k = _unit_key(u)
            seen[k] = seen.get(k, 0) + 1
            copies.setdefault((k, seen[k]), []).append(u)
    out = []
    for cs in copies.values():
        u = dict(cs[0])
        ds = [d for d in diffs if any(d in (c.get('difficulties') or diffs) for c in cs)]
        if len({c.get('note') for c in cs}) > 1:
            levels = {}
            for c in cs:
                levels.update(_levels(c, diffs))
            base = 'Normal' if 'Normal' in levels else next(d for d in diffs if d in levels)
            others = [f'{d} {levels[d]}' for d in diffs if d in levels and d != base and levels[d] != levels[base]]
            rest = u['note'][LEVEL.match(u['note']).end():]
            u['note'] = f'Lv {levels[base]}' + (f" ({', '.join(others)})" if others else '') + rest
        if len(ds) < len(diffs):
            u['difficulties'] = ds
        else:
            u.pop('difficulties', None)
        out.append(u)
    return out


def _whens(g, diffs):
    """{difficulty: when} for the difficulties a group comes on."""
    ds = [d for d in diffs if any(d in (u.get('difficulties') or diffs) for u in g['units'])]
    w = g.get('when')
    if isinstance(w, dict):
        return {d: w[d] for d in ds if d in w}
    return {d: w for d in ds} if w else {}


def _turns_text(specs, rest):
    """'Turns 4, 6 and 8, your phase' from (first, last) turn spans (last None: every turn on), contiguous ones joined."""
    joined = []
    for a, b in sorted(set(specs), key=lambda s: (s[0], 10 ** 6 if s[1] is None else s[1])):
        if joined and joined[-1][1] is not None and a <= joined[-1][1] + 1:
            pa, pb = joined[-1]
            joined[-1] = (pa, None if b is None else max(pb, b))
        elif not (joined and joined[-1][1] is None):
            joined.append((a, b))
    if len(joined) == 1:
        a, b = joined[0]
        if b is None:
            return f'Every turn from {a}, {rest}' if a > 1 else f'Every turn, {rest}'
        return f'Turn {a}, {rest}' if a == b else f'Every turn from {a} to {b}, {rest}'
    words = [str(a) if a == b else f'{a} on' if b is None else f'{a} to {b}' for a, b in joined]
    return f"Turns {', '.join(words[:-1])} and {words[-1]}, {rest}"


def combine_whens(parts):
    """One sentence for a group placed several times: turns that share the rest of their wording are listed together ('Turn 4,
    your phase' and 'Turn 6, your phase': 'Turns 4 and 6, your phase'); anything else follows after a semicolon."""
    parts = list(dict.fromkeys(p for p in parts if p))
    if len(parts) < 2:
        return parts[0] if parts else None
    spans, order = {}, []
    for p in parts:
        m = TURNS.match(p)
        if not m:
            order.append(p)
            continue
        single, a, b, from_, rest = m.groups()
        span = (int(single),) * 2 if single else (int(a), int(b)) if a else (int(from_), None) if from_ else (1, None)
        if rest not in spans:
            spans[rest] = []
            order.append(('turns', rest))
        spans[rest].append(span)
    texts = [_turns_text(spans[x[1]], x[1]) if isinstance(x, tuple) else x for x in order]
    return texts[0] + ''.join(f'; {t[0].lower()}{t[1:]}' for t in texts[1:])


def _merge_same_units(groups, diffs):
    """The same units on the same tiles from handlers of their own: one group, its times per difficulty. Two handlers that place them
    at the same time on one difficulty place two copies (The Binding Blade's Chapter 5 lists one Hard event twice): kept apart."""
    buckets = []
    for g in groups:
        key, whens = json.dumps(sorted(_unit_key(u) for u in g['units'])), _whens(g, diffs)
        b = next((b for b in buckets if b[0] == key and not any(w in b[1].get(d, []) for d, w in whens.items())), None)
        if not b:
            b = (key, {}, [])
            buckets.append(b)
        for d, w in whens.items():
            b[1].setdefault(d, []).append(w)
        b[2].append(g)
    out = []
    for _, parts, gs in buckets:
        g = gs[0]
        if len(gs) > 1:
            g['units'] = _merge_units([o['units'] for o in gs], diffs)
            g['when'] = {d: combine_whens(parts[d]) for d in diffs if d in parts}
            areas = [a for o in gs for a in o.get('areas', [])]
            if areas:
                g['areas'] = list({json.dumps(a, sort_keys=True): a for a in areas}.values())
        out.append(g)
    return out


def _fold_same_time(groups, diffs):
    """Groups that come at the same time on every difficulty, set off the same way (the same turns, the same visit or talk, the same
    areas), are one arrival; a time that doesn't say what sets it ('After an event in the chapter') can't tell two apart."""
    out = []
    for g in groups:
        whens, key = _whens(g, diffs), json.dumps(sorted(_unit_key(u) for u in g['units']))
        same = next((o for o in out if g.get('areas') == o.get('areas') and whens and _whens(o, diffs) == whens
                     and not any(VAGUE.search(w) for w in whens.values())
                     and json.dumps(sorted(_unit_key(u) for u in o['units'])) != key), None)
        if same:
            same['units'] += g['units']
            continue
        out.append(g)
    return out


# A thief takes only items: each game's steal routines (the target list, the item menu and the steal itself) test an item with
# one check, type (item record +7) == 9 (FE6 0x08016D34, FE7 0x08016D38, FE8 0x08017054), so never a weapon, staff or dragonstone.
# The target list (FE6 0x0802156C, FE7 0x080244AC, FE8 0x08025BA0) takes an enemy-army unit (+0xB & 0xC0 == 0x80) holding such an
# item; FE7's and FE8's also need the thief's Spd (+0x16) at least the target's, FE6's doesn't compare it.
STEALABLE_TYPE = 9


def stealable(items, dropped, type_of):
    """The item ids of a foe's that a thief can take and that it doesn't drop: what a unit entry keeps as `_take`."""
    rest = list(dropped)
    out = []
    for i in items:
        if i in rest:
            rest.remove(i)
        elif type_of(i) == STEALABLE_TYPE:
            out.append(i)
    return out


# An item's use (item record +0x1E, the same place in all three) that's over in a moment: keys and lockpicks, healing and curing
# items, torches, mines and runes (FE6 0x20-0x28; FE7 and FE8 0x1E-0x28, and FE7's and FE8's 60-use Vulneraries 0x33-0x35). The
# rest last: stat boosters (FE6 0x12-0x1A, FE7 and FE8 0x10-0x18), promotion items and seals, and none at all (0: gems and gold to
# sell, things that work while held such as the Delphi Shield and the membership cards).
USE_EFFECT = 0x1E
MOMENTARY = {'fe6': set(range(0x20, 0x29)), 'fe7': set(range(0x1E, 0x29)) | {0x33, 0x34, 0x35},
             'fe8': set(range(0x1E, 0x29)) | {0x33, 0x34, 0x35}}


def mark_steals(maps, item_name, use_of, game, extra_sold=()):
    """Each foe's `steal`: the items it can be robbed of (`_take`, set by its unit entry) that are rare. Rare: kept for something
    lasting (its use, `use_of(item)`, isn't one of the game's MOMENTARY ones), and no ordinary shop in the game sells it, an armory
    or vendor on any map (`stock` of its shops) or in `extra_sold` (The Sacred Stones' world map towns). What only a secret shop sells
    (behind a Member Card: The Binding Blade's crests and stat boosters) still counts as rare. A foe a talk recruits brings its items
    along (Klein, Hugh, Amelia), and a trial map keeps nothing, so neither is marked."""
    sold = {n for m in maps for o in m['objects'] if o['type'] == 'shop' and o.get('kind') != 'Secret shop'
            for n in o.get('stock', [])} | set(extra_sold)
    for m in maps:
        for u in m['units'] + [x for g in m.get('reinforcements') or [] for x in g['units']]:
            take = [i for i in u.pop('_take', None) or [] if use_of(i) not in MOMENTARY[game]]
            # A trial map (The Binding Blade's) keeps nothing you take, and a recruit brings its items along.
            if m.get('route') == 'Trial' or (u.get('talk') or '').startswith('Recruit'):
                continue
            rare = [n for n in dict.fromkeys(item_name(i) for i in take) if n not in sold]
            if rare:
                u['steal'] = rare


def one_per_arrival(groups, diffs):
    """One group per arrival: what one handler places is one group, whatever each difficulty places (a unit only some difficulties
    have says so: Ephraim's Chapter 12's extra Gargoyles on Hard), and groups of the same units on the same tiles placed by
    handlers of their own, on other turns or other difficulties, are one group whose time says each (Hector's Chapter 13's
    Normal and Hard turns; The Binding Blade's Hard-only repeats of a group). Groups carry their event as `_event`; the result is
    numbered afresh."""
    pos = {id(g): k for k, g in enumerate(groups)}
    by_event = {}
    for g in groups:
        by_event.setdefault(g.pop('_event', id(g)), []).append(g)
    merged = []
    for gs in by_event.values():
        g = gs[0]
        if len(gs) > 1:
            whens = {}
            for o in gs:
                whens.update(_whens(o, diffs))
            g['units'] = _merge_units([o['units'] for o in gs], diffs)
            g['when'] = whens
            areas = [a for o in gs for a in o.get('areas', [])]
            if areas:
                g['areas'] = list({json.dumps(a, sort_keys=True): a for a in areas}.values())
        merged.append(g)
    # Same units, other times; then other units, the same time: each can make a pair the other merges, so both run until neither
    # finds one.
    out = merged
    while True:
        n = len(out)
        out = _fold_same_time(_merge_same_units(out, diffs), diffs)
        if len(out) == n:
            break
    for g in out:
        w = g.get('when')
        if isinstance(w, dict) and len(w) == len(diffs) and len(set(w.values())) == 1:
            g['when'] = next(iter(w.values()))
    out.sort(key=lambda g: pos[id(g)])
    for n, g in enumerate(out, 1):
        g['id'], g['label'] = f'g{n}', f'Group {n}'
    return out

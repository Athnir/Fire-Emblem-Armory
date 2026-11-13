"""
Builds Fire Emblem Gaiden's maps from the cartridge (scripts/fe2_data.py):
  src/data/fe2/fe2Terrain.ts      terrain avoid, healing and movement costs, from the game's own tables
  src/data/fe2/fe2Maps.ts         every battle: the chapters' armies on the world map, the random armies, the dungeons' encounters
  src/data/fe2/fe2ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe2-maps.py

Formats are in data-raw/fe2/README.md. Coordinates: the stored grid has an outer ring no unit enters (6:$9708), so the playable map is
the grid without it; the game counts columns and rows from 0 at the top left, the app from (1, 1) at the bottom left.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe2_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from terrain_codes import encode  # noqa: E402
import fe2_art  # noqa: E402
import map_pieces  # noqa: E402

GAME, TITLE, SCRIPT = 'fe2', 'Fire Emblem Gaiden', 'build-fe2-maps.py'

# Terrain code (15:$E8DE) -> the app's letter and name. Codes 9 and 13 (walls; 13 draws doors and gates, which nothing opens) cost the
# same and give the same, as do 6, 18, 19 and 20 (floors).
CODE_LETTER = {
    0: ('.', 'Plain'), 1: ('f', 'Forest'), 2: ('s', 'Sand'), 3: ('w', 'Shallows'), 4: ('m', 'Mountain'), 5: ('C', 'Peak'),
    6: ('O', 'Floor'), 7: ('a', 'Water'), 8: ('T', 'Castle floor'), 9: ('#', 'Wall'), 10: ('p', 'Pillar'), 11: ('S', 'Stairs'),
    12: ('N', 'Castle'), 13: ('#', 'Wall'), 15: ('F', 'Fort'), 16: ('M', 'Swamp'), 17: ('G', 'Grave'), 18: ('O', 'Floor'),
    19: ('O', 'Floor'), 20: ('O', 'Floor'),
}
FORT_TILE, FORT, SWAMP = 0xDA, 15, 16
# The turn's start (3:$90F0): a unit on tile $DA (code 15) recovers 5 HP; on code 16 it loses 5 (never below 1), unless it's a Pegasus
# or Falcon Knight (classes 3 and 5) or a foe Revenant, Bonewalker, Mogall or Duma (11, 17, 18, 21).
FORT_NOTE = 'Restores 5 HP at the start of each turn (3:$9114).'
SWAMP_NOTE = ("Takes 5 HP at the start of each turn (never below 1) from all but Pegasus and Falcon Knights (and the Gargoyles and "
              "Necrodragons of their classes) and the foes' Revenants, Bonewalkers, Mogalls and Duma (3:$9143).")
MOVE_NAMES = {1: 'Cavaliers', 2: 'Knights', 3: 'Pegasus & Falcon Knights', 4: 'Paladins', 6: 'Soldiers, Saints & Clerics',
              7: 'Gold Knights', 8: 'Mercenaries & Priestesses', 9: 'Myrmidons', 10: 'Dread Fighters',
              12: 'Archers, Snipers & Villagers', 15: 'Mages & Sages', 20: 'Bow Knights', 21: 'Fighters', 22: 'Barons'}

# The story: each chapter's battles on the world map, by army and in the order its road takes them. Chapter 1 is Alm's, 2 Celica's;
# in 3 and 4 each army has its own half of the map (Alm's north through the woods to Rigel's border and castle, Celica's by the coast,
# the deserts and the swamps), as the chapters' tables place their armies (8:$9291 / 8:$9299) and the towns each army reaches
# (the Unit Planner's joins). Node 8 holds Chapter 2's random army (always composition 8), 20 and 44 Chapters 3 and 4's (one of
# five), and 32 the army Desaix's death sends (8:$927B: Tatarrah's).
STORY = [
    (1, 'Alm', [1, 2, 3, 4, 5, 6, 7]),
    (2, 'Celica', [8, 9, 10, 11, 12, 13, 14, 15]),
    (3, 'Alm', [17, 27, 28, 29, 30, 31, 32]),
    (3, 'Celica', [19, 20, 21, 22, 23, 24, 25, 26]),
    (4, 'Alm', [33, 34, 38, 39, 40, 37, 41, 42]),
    (4, 'Celica', [43, 44, 45, 47, 48]),
]
FINAL_ENCOUNTER = 22          # the Duma battle (town specials 5 and 8: both armies)
RUDOLF = 5                    # the battle ends when he falls (6:$B8B0)
SHIELD_ROOM, SHIELD_PAIR = 48, (50, 51)   # the Fear Shrine's Silver and Blessed Shields: one or the other (13:$8A91)
PENDING = {32: 1}             # node -> the foe whose death sends its army (8:$927B: composition 67's 32, set by Desaix's death)
# Who joins where (the Unit Planner's: character -> (army, chapter, town)); a recruit's item counts from the battle beside its town.
JOIN_TOWNS = {
    5: ('alm', 1, 1), 6: ('alm', 1, 1), 7: ('alm', 1, 1), 8: ('alm', 1, 1), 9: ('alm', 1, 2), 11: ('alm', 1, 3), 12: ('alm', 1, 3),
    20: ('alm', 1, 33), 14: ('alm', 1, 32),
    15: ('celica', 2, 5), 16: ('celica', 2, 5), 13: ('celica', 2, 5), 27: ('celica', 2, 6), 17: ('celica', 2, 7),
    21: ('celica', 2, 7), 18: ('celica', 2, 7),
    28: ('alm', 3, 16), 19: ('alm', 3, 17), 29: ('alm', 3, 19),
    32: ('celica', 3, 9), 31: ('celica', 3, 9), 22: ('celica', 3, 10), 23: ('celica', 3, 12), 26: ('celica', 3, 13),
    25: ('celica', 3, 13), 33: ('celica', 3, 13),
    30: ('alm', 4, 23), 34: ('alm', 4, 21), 3: ('alm', 4, 30),
    4: ('celica', 4, 34),
}
ROOM_NODES = {3: 51, 32: 80, 34: 63}   # rooms the world map doesn't lead to directly, and the place each is in (the Unit Planner's)


def readable(place):
    """The patch's place names have no spaces ("LiberationHQ"): put them back."""
    import re
    return re.sub(r'(?<=[a-z.])(?=[A-Z])', ' ', place).replace("'s", "'s")


def move_groups():
    groups = {}
    for c in range(1, 23):
        groups.setdefault(bytes(D.move_costs(c)), []).append(c)
    out = []
    for row, classes in groups.items():
        label = next(MOVE_NAMES[c] for c in classes if c in MOVE_NAMES)
        out.append((label, classes, row))
    order = list(MOVE_NAMES.values())
    return sorted(out, key=lambda g: order.index(g[0]))


TILES = D.tile_codes()
FOE_TILES = D.tile_codes(True)
AVOID = D.terrain_avoid()


# Walls drawn as what they are in the map's art (the user's call; scripts/fe2_art.py): a wall (9) the caves' orange rock, or the black
# void ($70); the five door-like walls (13) a castle's; and of the tiles only fliers cross (12), the ships' planks their sides.
VOID_TILE = 0x70
SHIP_TILES = set(range(0xE0, 0xED)) | {0xF0, 0xFF}


# A castle (tiles only fliers cross) of this many tiles or fewer, standing in the open round a fort or its stairs, is drawn whole: its
# pieces (`ca`-`ci`, map_pieces.place) round what's inside it (the user's call, as the DS games' castles).
SMALL_CASTLE = 9


def small_castles(codes):
    """{(row, column) from 0: piece code} for a map's small castles; `codes` its rows of app codes."""
    h, w = len(codes), len(codes[0])
    keep, seen = set(), set()
    for y in range(h):
        for x in range(w):
            if codes[y][x] != 'wx' or (y, x) in seen:
                continue
            part, todo = set(), [(y, x)]
            while todo:
                c = todo.pop()
                if c in part or not (0 <= c[0] < h and 0 <= c[1] < w) or codes[c[0]][c[1]] != 'wx':
                    continue
                part.add(c)
                todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            seen |= part
            beside = {codes[c[0] + dy][c[1] + dx] for c in part for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                      if 0 <= c[0] + dy < h and 0 <= c[1] + dx < w}
            if len(part) <= SMALL_CASTLE and beside & {'bb', 'tc', 'bv'}:
                keep |= part
    rows = [''.join(code if code != 'wx' or (y, x) in keep else 'XX' for x, code in enumerate(row)) for y, row in enumerate(codes)]
    placed = map_pieces.place(rows, 'wx', 'c', {'wx', 'bb', 'tc', 'bv'})
    return {(y, x): placed[y][2 * x:2 * x + 2] for y, x in keep}


def tile_info(tile, groups):
    code = TILES[tile]
    letter, name = CODE_LETTER[code]
    if code == 9:
        letter = '_' if tile == VOID_TILE else 'K'
    elif code == 13:
        letter = '0'
    elif code == 12 and tile in SHIP_TILES:
        letter = '9'
    move = {label: (None if row[code] == 0xFF else row[code]) for label, _, row in groups}
    e = {'name': name, 'def': 0, 'avo': AVOID[code], 'heal': 0, 'move': move}
    if tile == FORT_TILE:
        e['heal'] = 5
        e['note'] = FORT_NOTE
    elif code == SWAMP:
        e['heal'] = -5
        e['note'] = SWAMP_NOTE
    else:
        assert code != FORT, hex(tile)
    return letter, e


class Field:
    def __init__(self, n):
        self.n = n
        self.rows, self.cols, self.grid = D.battle_map(n)
        self.w, self.h = self.cols - 2, self.rows - 2

    def app(self, col, row):
        return [col, self.h + 1 - row]

    def inside(self, col, row):
        return 1 <= col <= self.w and 1 <= row <= self.h


def joined(names):
    names = list(dict.fromkeys(names))
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


def spells_of(rec):
    """A foe caster's spells: its +10 bits over its class's foes' list (15:$E1C9, by class order 15:$F459)."""
    order = list(D.R.read(D.FIXED, 0xF459, 6))
    if rec[1] not in order or not rec[5]:
        return []
    lst = list(D.R.read(D.FIXED, 0xE1C9 + 8 * order.index(rec[1]), 8))
    return [D.item_menu_name(lst[b]) for b in range(8) if rec[5] >> b & 1]


DROPS, DROP_CAPS = D.random_drops()


def foe_unit(rec, tile, kind, chapter):
    name = D.foe_name(rec)
    cls = D.FOE_CLASSES[rec[1]]
    person = D.is_person(rec)
    note = f'Lv {rec[2]}' + (f' {cls}' if person else '')
    item = D.item_name(rec[3]) if rec[3] else None
    if item:
        note += f': {item}'
    sp = spells_of(rec)
    if sp:
        note += f'. Spells: {joined(sp)}'
    u = {'type': kind, 'name': name, 'tile': tile, 'note': note}
    if item:
        u['carries'] = [item]
        # A foe's held item always drops to the unit that beats it (6:$AA4B).
        u['drops'] = [item]
    elif chapter <= 4:
        # 15:$F225: a foe holding nothing may drop an item of its kind, both of two rolls under the chance, while the chapter's count
        # of such drops is under 15:$F23E's.
        for foe, chance, it in DROPS:
            if foe & 0x7F == rec[0] & 0x7F:
                u['note'] += (f'. Holding nothing, it may drop a {D.item_name(it)} (two rolls, each under {chance} in 100; at most '
                              f'{DROP_CAPS[chapter - 1]} such drops by Chapter {chapter})')
    return u


def write_opens(opens):
    """src/data/fe2/fe2Opens.ts: the story battle each dungeon encounter opens with."""
    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe2', 'fe2Opens.ts')
    lines = ['/*', f" * GENERATED by scripts/{SCRIPT} from {TITLE}'s world map. Do not edit by hand.", ' */', '',
             '/** The story battle each town or dungeon encounter opens with: the one after the battle beside its place. */',
             'export const FE2_OPENS: Record<string, string> = ' + json.dumps(opens, indent=2)]
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    groups = move_groups()
    maps, sources, variants, used = [], {}, {}, {}
    story_ids = []
    names = {n: readable(D.node_name(n)) for n in range(1, D.N_NODES + 1)}
    spawns = D.spawn_points()
    deaths = D.death_events()
    guests = dict(D.guests())
    # A town or dungeon's world node -> the battle nodes beside it.
    town_node = {}
    for node in range(49, D.N_NODES + 1):
        town_node.setdefault(D.entry_room(node), node)
    town_node.update(ROOM_NODES)

    def source(item, map_id, kind, words):
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(D.item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    def leaves(comps):
        """What a death takes off the battle (death events of kind 2, 15:$F18D: list v at 15:$F20C, [foe][flag event][message]): Slayde
        and Desaix at Sofia Gate each leave when the other falls; Barth's Brigands flee when he does."""
        recs = [r for c in comps for r in D.composition(c)]
        by_number = {r[0] & 0x7F: r for r in recs}
        out = []
        for foe, kind, v in deaths:
            if kind != 2 or (foe & 0x7F) not in by_number:
                continue
            leaver = D.R.u8(D.FIXED, D.R.u16(D.FIXED, 0xF20C + 2 * v)) & 0x7F
            if leaver not in by_number:
                continue
            who = D.foe_name(by_number[leaver])
            them = who if D.is_person(by_number[leaver]) else f'the {who}s'
            out.append(f'When {D.foe_name(by_number[foe & 0x7F])} falls, {them} {"leaves" if D.is_person(by_number[leaver]) else "leave"} '
                       'the battle (15:$F20C).')
        return out

    battle_id = {}    # (army, node) -> map id
    order = []

    def build(map_id, field, chapter, army, comps, title, heading, route, number, extra_notes=()):
        """One battle: the field, your army's tiles, the foes' groups on theirs."""
        m = {'id': map_id, 'route': route, 'chapter': number, 'heading': heading, 'title': title, 'width': field.w,
             'height': field.h, 'grid': [], 'victory': 'Rout the enemy', 'defeat': f'{army} is defeated' if army != 'both' else
             'Alm or Celica is defeated', 'objectives': [], 'units': [], 'starts': [], 'objects': [], 'changes': [],
             'notes': list(extra_notes), 'lord': army if army != 'both' else 'Alm'}
        lists = D.deploy_lists(field.n)
        mine, theirs = ((lists[0], lists[1]), (lists[2], lists[3])) if army != 'Celica' or field.n == 36 else ((lists[2], lists[3]), (lists[0], lists[1]))
        m['starts'] = [field.app(c, r) for c, r in mine[0] + mine[1] if field.inside(c, r)]
        m['starts'] = [t for i, t in enumerate(m['starts']) if t not in m['starts'][:i]]
        if m['starts']:
            m['corrinStart'] = m['starts'][0]
        # Foe group 0 on list A, group 1 on list B; a lone group overflows from A into B (8:$9E33).
        tiles_for = [theirs[0], theirs[1]] if len(comps) > 1 else [theirs[0] + theirs[1]]
        for g, comp in enumerate(comps):
            recs = D.composition(comp)
            tiles = [t for t in tiles_for[g] if field.inside(*t)]
            for k, rec in enumerate(recs[:len(tiles)]):
                n = rec[0] & 0x7F
                kind = 'boss' if n == RUDOLF and D.is_person(rec) else 'named' if D.is_person(rec) else 'enemy'
                u = foe_unit(rec, field.app(*tiles[k]), kind, chapter)
                m['units'].append(u)
                who = u['name'] if kind != 'enemy' else f"a foe {u['name']}"
                if rec[3]:
                    source(rec[3], map_id, 'drop', f'Dropped by {who}')
                elif chapter <= 4:
                    for foe, chance, it in DROPS:
                        if foe & 0x7F == n:
                            source(it, map_id, 'drop', f'Sometimes dropped by {who} holding nothing')
            if len(recs) > len(tiles):
                m['notes'].append(f'{len(recs) - len(tiles)} of its army find no tile and stay off the map.')
        if any(u['name'] == 'Rudolf' for u in m['units']):
            m['victory'] = 'Defeat Rudolf'
        # Terrain. A brown map's plains are bare earth, dirt (fe2_art.EARTH); a small castle in the open drawn whole round what's in it.
        infos = []
        earth = fe2_art.palette_list(field.n) in fe2_art.EARTH
        pieces = small_castles([[encode(GAME, tile_info(field.grid[r][c], groups)[0]) for c in range(1, field.cols - 1)]
                                for r in range(1, field.rows - 1)])
        for r in range(1, field.rows - 1):
            line = []
            for c in range(1, field.cols - 1):
                t = field.grid[r][c]
                letter, info = tile_info(t, groups)
                code = encode(GAME, letter)
                if code == 't0' and earth:
                    code = 'ga'
                code = pieces.get((r - 1, c - 1), code)
                line.append(code)
                infos.append((code, info))
                variants.setdefault(code, {}).setdefault(repr(info), [info, set()])[1].add(map_id)
            m['grid'].append(''.join(line))
        # Its ground, water and walls in its own colours, from its art.
        m['fills'] = fe2_art.fills(field.n, [row[1:field.cols - 1] for row in field.grid[1:field.rows - 1]],
                                   [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']])
        used[map_id] = {}
        for code, info in infos:
            old = used[map_id].setdefault(code, info)
            assert old == info, (map_id, code, old, info)
        foe_mountains = sum(1 for r in range(1, field.rows - 1) for c in range(1, field.cols - 1) if field.grid[r][c] == 0xE7)
        if foe_mountains:
            m['notes'].append('Its mountain tiles of the castle kind (tile $E7) are mountains to your units but castle walls to the '
                              'foes (fliers alone cross: 15:$E9DE).')
        maps.append(m)
        return m

    # The story.
    for chapter, army, nodes in STORY:
        heading = f'Chapter {chapter}'
        for k, node in enumerate(nodes, 1):
            map_id = f'fe2-{chapter}' + (army[0].lower() if chapter in (3, 4) else '') + f'-{k}'
            comps = [c for c, n in D.chapter_groups(chapter) if n == node]
            notes = []
            randoms = [c for c, n in D.random_groups(chapter) if n == node]
            if randoms and len(set(randoms)) == 1:
                comps = [randoms[0]]
            elif randoms:
                notes.append('Its army is one of five the chapter picks at random as it starts (8:$9D38): '
                             + '; '.join(f'{joined([D.foe_name(r) for r in D.composition(c)][:1])} and '
                                         f'{len(D.composition(c)) - 1} more' for c in randoms) + '.')
                comps = []
            if node in PENDING:
                comps = [32]
                notes.append(f'This army comes once {D.FOE_SOV[PENDING[node]]} falls at Tozeh\'s Fort (his death event).')
            for g_node, people in guests.items():
                if g_node == node and people:
                    notes.append(f"Fighting on your side here (guests): {joined([D.SOV_NAMES[p] for p in people])}; each joins your "
                                 'army afterwards if talked to.')
            notes += leaves(comps)
            # Spawn points on this node: what can gather here later.
            for x, (town, wnode, levels) in enumerate(spawns):
                if wnode == node:
                    notes.append(f'Monsters can gather here later (spawn point {x}): ' + '; '.join(
                        f'level {L}: {len(D.composition(c))} ({D.foe_name(D.composition(c)[0])}...), {min(ch, 100)}%'
                        for L, (c, ch) in enumerate(levels, 1)) + '. The deaths of bosses set its level (15:$F18D).')
            if randoms and len(set(randoms)) > 1:
                field = Field(node)
                m = build(map_id, field, chapter, army, [], names[node], heading, army if chapter in (3, 4) else 'Story', k, notes)
                lists = D.deploy_lists(node)
                theirs = (lists[2] + lists[3]) if army != 'Celica' else (lists[0] + lists[1])
                most = max(len(D.composition(c)) for c in randoms)
                for c, r in [t for t in theirs if field.inside(*t)][:most]:
                    m['units'].append({'type': 'enemy', 'name': 'Random foe', 'tile': field.app(c, r),
                                       'note': 'One of the five armies the chapter picks from stands here.'})
                for c in randoms:
                    for rec in D.composition(c):
                        if rec[3]:
                            source(rec[3], map_id, 'drop', f"Dropped by {'a foe ' if not D.is_person(rec) else ''}{D.foe_name(rec)} (if the "
                                   'chapter picks its army)')
            else:
                build(map_id, Field(node), chapter, army, comps, names[node], heading, army if chapter in (3, 4) else 'Story', k, notes)
            battle_id[(army, node)] = map_id
            order.append(map_id)
    # Chapter 5: the battle with Duma (encounter 22), both armies.
    comp, second, field_n = D.dungeon_encounters()[FINAL_ENCOUNTER]
    final = build('fe2-5-1', Field(field_n), 5, 'both', [comp] + ([second] if second is not None else []), "Duma's Altar",
                  'Chapter 5', 'Story', 1,
                  ['Below 52 HP Duma attacks with Eyeball, which stops the strikes of everyone but the Falchion\'s wielder (9:$8CC8, '
                   '9:$8A63); above it, with the Tentacle (178 in 256) or Eye Beam.'])
    order.append('fe2-5-1')
    # Duma's attack (9:$8CC8): the Tentacle, an item no one holds.
    source(19, 'fe2-5-1', 'foe', 'Duma attacks with it')

    # The towns' and dungeons' encounters (8:$935B): started on entering a room (13:$BA01) or stepping on its tiles (13:$8FF9), each on
    # its own field (maps 49-80). Each opens once the battle beside its place on the world map is won, and is fought by the army
    # whose road that is.
    reach = D.rooms_from_nodes()
    on_entry, on_step = D.room_encounters()
    rooms_of = {}
    for room, enc, _bit in on_entry:
        rooms_of.setdefault(enc, []).append(room)
    for room, enc in on_step:
        rooms_of.setdefault(enc, []).append(room)
    opens = {}
    for e, (comp, second, field_n) in enumerate(D.dungeon_encounters()):
        if e == FINAL_ENCOUNTER:
            continue
        reaching = {n: d for room in rooms_of.get(e, []) for n, d in reach.get(room, {}).items()}

        def army_of(n):
            arms = {k[0] for k in battle_id if k[1] in D.adjacent(n)}
            return arms.pop() if len(arms) == 1 else None
        # The army whose side of the field the foes fit (a field may leave the other army one or two tiles: Regal Castle's rooms,
        # which the Dragon Tower's also reach); the place among that army's.
        comps_n = len(D.composition(comp & 0x7F)) + (len(D.composition(second)) if second is not None else 0)
        lists = D.deploy_lists(field_n)
        fld = Field(field_n)
        fits = {a for a, foes in (('Alm', lists[2] + lists[3]), ('Celica', lists[0] + lists[1]))
                if len([t for t in foes if fld.inside(*t)]) >= comps_n}
        if len(fits) == 1:
            reaching = {n: d for n, d in reaching.items() if army_of(n) in fits} or reaching
        nodes = D.nearest_nodes(reaching)
        also = sorted(set(reaching) - set(nodes))
        beside = sorted({b for n in nodes for b in D.adjacent(n) if b < 49})
        near = [(k, v) for k, v in battle_id.items() if k[1] in beside]
        if not near:
            print('encounter', e, 'reached from no story battle: skipped', nodes)
            continue
        (army, _), after = min(near, key=lambda kv: order.index(kv[1]))
        chapter = int(after.split('-')[1][0])
        place = joined([names[n] for n in nodes])
        how = 'on entering' if any(enc == e for _r, enc, _b in on_entry) else 'on stepping onto a marked tile in'
        comps = [comp & 0x7F] + ([second] if second is not None else [])
        m = build(f'fe2-d{e}', Field(field_n), chapter, army, comps, place, 'Dungeons', 'Story', e,
                  [f'Fought {how} a room of {place}, once per visit (13:$BA01, 13:$8FF9).'] + leaves(comps))
        if also:
            m['unconfirmed'] = [f"Its room is also reached from {joined([names[n] for n in also])}; it's put at the nearest place, "
                                'which wants an in-game check.']
        nxt = order[order.index(after) + 1] if order.index(after) + 1 < len(order) else after
        opens[m['id']] = nxt

    # Chests in the towns and dungeons (13:$BD70, kind 0): counted from the battle beside the place on the world map.
    for room in range(1, 51):
        for x, y, kind, value in D.room_objects(room):
            if kind != 0:
                continue
            nodes = D.nearest_nodes(reach.get(room, {}))
            others = sorted(set(reach.get(room, {})) - set(nodes))
            place = joined([names[n] for n in nodes]) if nodes else f'room {room}'
            if others:
                place += f" (a room {joined([names[n] for n in others])} also reach{'es' if len(others) == 1 else ''})"
            beside = sorted({b for n in nodes for b in D.adjacent(n) if b < 49})
            ids = [battle_id[k] for k in battle_id if k[1] in beside]
            if not ids:
                continue
            first = min(ids, key=order.index)
            words = f'In a chest at {place}'
            if room == SHIELD_ROOM and value in SHIELD_PAIR:
                # 13:$8A91: the room's two shields are one or the other (its sign: "Right, Holy Shield. Left, Silver Shield.").
                other = next(v for v in SHIELD_PAIR if v != value)
                words += f', or the {D.item_name(other)} instead: one of the two'
            source(value, first, 'chest-later', words)

    # Recruits' items: from the battle beside the town they join in (the Unit Planner's joins).
    for ch_, (army, chapter, town) in JOIN_TOWNS.items():
        rec = D.character(ch_)
        if not rec[11]:
            continue
        node = town_node.get(town)
        beside = [b for b in D.adjacent(node) if b < 49] if node else []
        arm = 'Alm' if army == 'alm' else 'Celica'
        ids = [battle_id[(arm, b)] for b in beside if (arm, b) in battle_id]
        target = min(ids, key=order.index) if ids else next(i for (a, n), i in battle_id.items() if a == arm)
        source(rec[11], target, 'kit-later' if ids else 'kit', f'Carried by {D.SOV_NAMES[ch_]} on joining')

    info = {}
    for code, vs in variants.items():
        info[code] = max(vs.values(), key=lambda v: len(v[1]))[0]
    for m in maps:
        over = {}
        for code, e in used[m['id']].items():
            if e != info[code]:
                over[code] = {k: v for k, v in e.items() if v != info[code].get(k)}
        if over:
            m['terrainOverrides'] = over
    classes = {c: D.SOV_CLASSES[c] for c in range(1, 23)}
    write_opens(opens)
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, classes,
                     fliers='Pegasus and Falcon Knights (and the Gargoyles and Necrodragons of their classes) fight on terrain code '
                            '13 whatever they stand on: no Avoid from terrain (6:$ABAD).')
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)
    for m in maps:
        print(m['id'], m['title'], f"{m['width']}x{m['height']}", len(m['units']), 'foes')


if __name__ == '__main__':
    main()

"""
Builds Shadow Dragon and the Blade of Light's maps from the cartridge (scripts/fe1_rom.py), named from the Switch release's own text
(scripts/fe1_names.py):
  src/data/fe1/fe1Terrain.ts      terrain avoid and movement costs, from the game's own tables
  src/data/fe1/fe1Maps.ts         every chapter's map, foes, joining units, reinforcements, villages, chests, shops and objectives
  src/data/fe1/fe1ItemSources.ts  where each item turns up
Run:
    python scripts/build-fe1-maps.py

Formats are in data-raw/fe1/README.md. Coordinates: the game counts rows and columns from 0 at the top left, and the cursor never goes
onto row or column 0 or the last ones (6:$A97B and on), so the playable map is the stored one without its outer ring; the app counts
from (1, 1) at the bottom left.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe1_names as N  # noqa: E402
import fe1_rom as R  # noqa: E402
import gba_maps as gm  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe1', 'Shadow Dragon and the Blade of Light', 'build-fe1-maps.py'
MARTH = 1
FORT, CASTLE, THRONE, CHEST, VILLAGE = 0x4A, 0x4B, 0xAE, 0xAB, 0xA5
HEALS = {FORT, CASTLE, THRONE}  # 3:$935B: 3 + a random 0-7 HP at the start of each turn
# The foes' army names (the foe name table's generic entries); every other foe name is a person.
GENERIC = {3, 5, 6, 31, 33, 35, 36, 43, 47, 52, 53, 55}
# Who talks to recruit whom: the game's talk table (15:$EDB5), and each chapter's list of recruits with a condition (3:$A3DA), which
# the routine that reads it (3:$8CE0) doesn't tie to a talker: Marth's, as Nintendo Wire's recruitment guide has them
# (data-raw/fe1/README.md).
LIST_TALKER = 'Marth'
GOLD = {0x78: 100, 0x79: 200, 0x7A: 500, 0x7B: 1000, 0x7C: 1500, 0x7D: 2000, 0x7E: 3000, 0x7F: 5000}  # 3:$9C6E
SHOP_KINDS = {1: 'Armory', 2: 'Shop', 3: 'Arena', 4: 'Storage', 5: 'Secret Shop'}
SHOP_LETTER = {1: 'A', 2: 'V', 3: 'R', 5: 'X'}
STARSPHERE, LIGHTSPHERE, STARLIGHT = 87, 90, 52

# Terrain code (15:$E828) -> the app's letter and name. The names are the battle's (15:$EBEE into the 16 at 15:$E5F1), except where
# the Switch release's own terrain words say more (Peak, House, Throne, Chest): the battle draws a peak as a mountain. A village's roof
# (code 20) is a wall, as nothing can enter it. Code 19 is
# a village with no entry to visit (Chapter 1's (10, 22)): its roof can be walked through, unlike a village's (code 20).
CODE_LETTER = {
    0: ('g', 'Grassland'), 1: ('.', 'Floor'), 2: ('v', 'Village'), 3: ('F', 'Fortress'), 4: ('N', 'Castle'), 5: ('f', 'Forest'),
    6: ('s', 'Desert'), 7: ('w', 'River'), 8: ('m', 'Mountain'), 9: ('P', 'Peak'), 10: ('b', 'Bridge'), 11: ('a', 'Sea'),
    12: ('.', 'Floor'), 13: ('#', 'Wall'), 15: ('B', 'House'), 16: ('p', 'Pillar'), 17: ('S', 'Stairs'), 18: ('.', 'Floor'),
    19: ('D', 'Village (no visit)'), 20: ('#', 'Wall'), 21: ('u', 'Stone wall'),
}

TILES = R.read(R.FIXED, R.TILE_TERRAIN, 0xD0)
AVOID = R.read(R.FIXED, R.TERRAIN_AVOID, R.TERRAIN_CODES)
ITEM_NAMES = {i: N.name(R.item(i)['name_codes']) for i in range(R.ITEMS)}
CHARS = {k + 1: N.name(R.string(R.FIXED, R.u16(R.FIXED, 0xDE2B + 2 * k))) for k in range(53)}
FOES = {k + 1: N.name(R.string(R.FIXED, R.u16(R.FIXED, 0xDFA4 + 2 * k))) for k in range(69)}
CLASSES = {c: N.class_info()[N.text_number(R.class_name_codes(c))] for c in range(1, 23)}
CLASSES.update({23: 'Dragon', 24: 'Earth Dragon'})

# Movement groups: classes whose cost rows are the same, named after their members.
MOVE_NAMES = {
    1: 'Cavaliers', 2: 'Knights', 3: 'Pegasus & Wyvern Knights', 4: 'Paladins', 6: 'Mercenaries & Manaketes', 7: 'Fighters & Hunters',
    8: 'Pirates', 9: 'Thieves', 10: 'Heroes', 11: 'Archers & Ballisticians', 14: 'Horsemen', 15: 'Snipers', 16: 'Freelancers',
    18: 'Mages & Bishops', 19: 'Curates', 21: 'Lord', 22: 'Generals',
}


def item_name(i):
    return ITEM_NAMES.get(i) or f'item {i}'


def move_groups():
    groups = {}
    for c in range(1, 23):
        groups.setdefault(bytes(R.move_costs(c)), []).append(c)
    out = []
    for row, classes in groups.items():
        label = next((MOVE_NAMES[c] for c in classes if c in MOVE_NAMES), None)
        assert label, f'no name for the movement row of {[CLASSES[c] for c in classes]}'
        out.append((label, classes, row))
    order = list(MOVE_NAMES.values())
    return sorted(out, key=lambda g: order.index(g[0]))


def tile_info(tile, groups, shop=None, chest=False):
    """A graphic tile -> (letter, terrain info)."""
    code = TILES[tile]
    letter, name = CODE_LETTER[code]
    if tile == THRONE:
        letter, name = 't', 'Throne'
    elif tile == CHEST and chest:
        letter, name = 'c', 'Chest'
    elif code == 15 and shop in SHOP_LETTER:
        letter, name = SHOP_LETTER[shop], SHOP_KINDS[shop]
    move = {label: (None if row[code] == 0xFF else row[code]) for label, _, row in groups}
    e = {'name': name, 'def': 0, 'avo': AVOID[code], 'heal': 0, 'move': move}
    if tile in HEALS:
        e['note'] = 'Restores 3 to 10 HP (at random) at the start of each turn.'
    return letter, e


class Chapter:
    def __init__(self, n):
        self.n = n
        self.rows, self.cols, self.grid = R.map_grid(n)
        self.w, self.h = self.cols - 2, self.rows - 2

    def app(self, row, col):
        """A game tile (row, column from 0 at the top left) -> the app's [x, y] (from (1, 1) at the bottom left)."""
        return [col, self.h + 1 - row]

    def inside(self, row, col):
        return 1 <= row <= self.h and 1 <= col <= self.w


def joined(names):
    names = list(dict.fromkeys(names))
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' or ' + names[-1]


def foe_name(char):
    return FOES.get(char & 0x7F) or f'foe {char & 0x7F}'


def talk_of(char, conditions, talkers):
    """'Recruit: talk with ...' for a foe the talk table or the chapter's recruit list names, else None."""
    who = list(talkers.get(char, []))
    if char in conditions and LIST_TALKER not in who:
        who.insert(0, LIST_TALKER)
    if not who:
        return None
    text = f'Recruit: talk with {joined(who)}'
    cond = conditions.get(char)
    if cond and cond[3]:
        text += f' (only with {CHARS[cond[3]]} in your army)'
    return text


def foe_entry(ch, rec, kind, talk=None):
    """A foe's 11-byte record -> the map's unit."""
    cls = CLASSES.get(rec[1], '?')
    generic = (rec[0] & 0x7F) in GENERIC
    lv = f'Lv {rec[2]}'
    out = {'type': kind, 'name': cls if generic else foe_name(rec[0]), 'tile': ch.app(rec[5], rec[6]),
           'note': lv if generic else f'{lv} {cls}'}
    items = [item_name(i - 1) for i in rec[3:5] if i]
    if items:
        out['carries'] = items
    # A defeated foe drops its second item to the unit that beat it (6:$AD79 keeps it as the battle's drop, 6:$935E gives it).
    if rec[4] and not talk:
        out['drops'] = [item_name(rec[4] - 1)]
    if talk:
        out['talk'] = talk
    return out


def main():
    titles, places = N.chapter_titles(), N.place_names()
    groups = move_groups()
    maps, sources, variants, used = [], {}, {}, {}
    joined_chars = set()
    talkers = {}  # foe character -> the characters who talk to it
    for t, foe, becomes in R.talks():
        talkers.setdefault(foe, []).append(CHARS[t])

    def source(item, map_id, kind, words, who=None):
        if who is not None:
            if who in joined_chars:
                return
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)

    for n in range(1, R.CHAPTERS + 1):
        ch = Chapter(n)
        map_id = f'fe1-{n}'
        m = {
            'id': map_id, 'route': 'Story', 'chapter': n, 'title': titles[n - 1], 'location': places[n - 1],
            'width': ch.w, 'height': ch.h, 'grid': [], 'victory': '', 'defeat': 'Marth is defeated', 'objectives': [],
            'units': [], 'starts': [], 'objects': [], 'changes': [], 'notes': [], 'lord': 'Marth',
        }
        shops = {(r, c): (kind, lst) for r, c, kind, lst in R.shops(n)}
        visits = R.visits(n)
        chests = {(r, c) for r, c, a, b, kind in visits if ch.grid[r][c] == CHEST}
        # Shops (11:$A4FF): armories, shops (vendors), secret shops; the arena and the storage are said in the notes.
        for (r, c), (kind, lst) in shops.items():
            tile = ch.app(r, c)
            if kind in (1, 2, 5):
                stock = R.shop_stock(lst)
                name = SHOP_KINDS[kind]
                m['objects'].append({'type': 'shop', 'tile': tile, 'kind': name, 'stock': [item_name(i) for i in stock]})
                for i in stock:
                    source(i, map_id, 'shop', f'Sold at the {name.lower()}' + (', with a VIP Card' if kind == 5 else ''))
            elif kind == 3:
                m['notes'].append(f'An arena stands at ({tile[0]}, {tile[1]}).')
            elif kind == 4:
                m['notes'].append(f'The storage (deposit and withdraw items) stands at ({tile[0]}, {tile[1]}).')
        # Places to visit (3:$A0F1), by what stands on the tile: a chest, a castle gate or throne to seize (with what seizing it gives),
        # a village; a house only talks.
        seize = []
        recruits = R.village_recruits(n)

        def give(a, words, note_to):
            """What a visit's value gives (3:$9B46): an item, gold or a recruit; returns the reward's words."""
            if 1 <= a < 0x78:
                source(a - 1, map_id, words[0], words[1])
                return item_name(a - 1)
            if a in GOLD:
                return f'{GOLD[a]} gold'
            if a == 0x80 or a in (0x81, 0x82):
                who = recruits[0][0] if a == 0x80 else (0x27 if a == 0x81 else 0x26)
                rec = next(x for x in recruits if x[0] == who)
                note_to.append(f'{CHARS[who]} joins your army.')
                for i in rec[19:23]:
                    if i:
                        source(i - 1, map_id, 'kit', f'Carried by {CHARS[who]} on joining', who=who)
                joined_chars.add(who)
                return ''
            if a == 0x84:
                note_to.append(f'Only for a visitor holding the {item_name(STARSPHERE)} and the {item_name(LIGHTSPHERE)}, which it takes.')
                source(STARLIGHT, map_id, 'village', f'Given at a village for the {item_name(STARSPHERE)} and the {item_name(LIGHTSPHERE)}')
                return item_name(STARLIGHT)
            return ''

        for r, c, a, b, flags in visits:
            tile = ch.app(r, c)
            gt = ch.grid[r][c]
            if gt == CHEST:
                contents = give(a, ('chest', 'In a chest'), [])
                if contents:
                    m['objects'].append({'type': 'chest', 'tile': tile, 'contents': contents})
            elif gt in (CASTLE, THRONE) or (flags in (0x20, 0x10, 0x08) and TILES[gt] != 2):
                # A castle gate or throne (Chapter 11's gate has a tile drawn as grass among them).
                seize.append((r, c))
                what = 'throne' if any(ch.grid[rr][cc] == THRONE for rr, cc, *_ in visits if (rr, cc) in seize) else 'castle'
                notes = []
                reward = give(a, ('event', f'Given when Marth seizes the {what}'), notes)
                if reward:
                    m['notes'].append(f'Seizing the {what} gives {reward}.')
                for t in notes:
                    m['notes'].append(f'When Marth seizes the {what}: {t[0].lower() + t[1:]}')
            elif TILES[gt] == 2:
                notes = []
                o = {'type': 'village', 'tile': tile, 'reward': give(a, ('village', 'Given at a village'), notes)}
                if notes:
                    o['note'] = ' '.join(notes)
                if o['reward'] or notes:
                    m['objects'].append(o)
            else:
                assert TILES[gt] == 15 and a == 0, (n, r, c, hex(gt), a)  # a house: it only talks
        # Your army: Chapter 1's list is the starting army; later chapters' lists join as the chapter starts.
        forced = []
        for rec in R.allies(n):
            who = rec[0]
            tile = ch.app(rec[16], rec[17])
            if who == MARTH:
                m['corrinStart'] = tile
            words = 'from the start' if n == 1 else 'on joining'
            for i in rec[19:23]:
                if i:
                    source(i - 1, map_id, 'kit', f'Carried by {CHARS[who]} {words}', who=who)
            joined_chars.add(who)
            if who != MARTH:
                forced.append({'name': CHARS[who], 'tile': tile})
        if forced:
            m['forced'] = forced
        m['starts'] = [ch.app(r, c) for r, c in R.deploy_tiles(n) if ch.inside(r, c)]
        if m['starts'] and not m.get('corrinStart'):
            m['corrinStart'] = m['starts'][0]
        # Foes (8:$8AA3): the first is the boss (the loader makes it worth 10 more EXP).
        conditions = {e[0]: e for e in R.recruit_conditions(n)}
        for k, rec in enumerate(R.foes(n)):
            name = foe_name(rec[0])
            talk = talk_of(rec[0], conditions, talkers)
            kind = 'boss' if k == 0 else 'enemy' if (rec[0] & 0x7F) in GENERIC else 'named'
            e = foe_entry(ch, rec, kind, talk)
            m['units'].append(e)
            if talk:
                for i in rec[3:5]:
                    if i:
                        source(i - 1, map_id, 'kit', f'Carried by {name} on joining')
            else:
                generic = kind == 'enemy'
                who = f"a foe {e['name']}" if generic else e['name']
                if rec[4]:
                    source(rec[4] - 1, map_id, 'drop', f'Dropped by {who}')
                if rec[3]:
                    source(rec[3] - 1, map_id, 'foe' + ('-generic' if generic else ''), f"Carried by {who}{'' if generic else ', a foe'}")
        # Reinforcements (3:$959C).
        rein = []
        for rec in R.reinforcements(n):
            name = foe_name(rec[0])
            turn = rec[8]
            if turn & 0x80:
                when = f'Turns {(turn & 0x7F) + 1} to {R.last_turn(n)}: one each turn while its tile is free'
            else:
                when = f'Turn {turn}, if its tile is free'
            cond = conditions.get(rec[0])
            if cond and cond[3]:
                when += f', only with {CHARS[cond[3]]} in your army'
            talk = talk_of(rec[0], conditions, talkers)
            u = foe_entry(ch, rec, 'enemy' if (rec[0] & 0x7F) in GENERIC else 'named', talk)
            u['from'] = u['tile']
            rein.append({'when': when, 'unit': u})
            generic = u['type'] == 'enemy'
            who = f"a foe {u['name']}" if generic else u['name']
            for k, i in enumerate(rec[3:5]):
                if not i:
                    continue
                if talk:
                    source(i - 1, map_id, 'kit-later', f'Carried by {name} on joining')
                elif k == 1:
                    source(i - 1, map_id, 'drop-later', f'Dropped by {who}, arriving mid-chapter')
                else:
                    source(i - 1, map_id, 'foe-later' + ('-generic' if generic else ''),
                           f"Carried by {who}{'' if generic else ', a foe'}, arriving mid-chapter")
        if rein:
            groups_out, by_when = [], {}
            for x in rein:
                by_when.setdefault(x['when'], []).append(x['unit'])
            for k, (when, units) in enumerate(by_when.items(), 1):
                groups_out.append({'id': f'g{k}', 'label': f'Group {k}', 'when': when, 'units': units})
            m['reinforcements'] = groups_out
        # The goal: seize the castle gate or the throne with Marth.
        if seize:
            on_throne = any(ch.grid[r][c] == THRONE for r, c in seize)
            what = 'throne' if on_throne else 'castle'
            m['victory'] = f'Seize the {what} with Marth'
            m['objectives'].append({'type': 'seize', 'tiles': [ch.app(r, c) for r, c in seize], 'label': f'Seize the {what} with Marth'})
        if n == 7:
            # 15:$CDA9: in this chapter every attack in a battle with Minerva, Catria, Palla or Est misses.
            m['notes'].append('In a battle with Minerva, Catria, Palla or Est, every attack misses, theirs and yours.')
        # Terrain.
        codes, infos = [], []
        for r in range(1, ch.rows - 1):
            line = []
            for c in range(1, ch.cols - 1):
                t = ch.grid[r][c]
                shop = shops.get((r, c), (None, None))[0]
                letter, info = tile_info(t, groups, shop, (r, c) in chests)
                code = encode(GAME, letter)
                line.append(code)
                infos.append((code, info))
                variants.setdefault(code, {}).setdefault(repr(info), [info, set()])[1].add(map_id)
            codes.append(''.join(line))
        m['grid'] = codes
        used[map_id] = {}
        for code, info in infos:
            old = used[map_id].setdefault(code, info)
            assert old == info, (map_id, code, old, info)
        maps.append(m)
        print(map_id, m['title'], f'{ch.w}x{ch.h}', len(m['units']), 'foes', len(rein), 'reinforcements')

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
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES,
                     fliers='Pegasus and Wyvern Knights always fight as if in the sky: no Avoid from terrain (6:$ADAF).')
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources)


if __name__ == '__main__':
    main()

"""
Builds Path of Radiance's maps from the game's own files:

- src/data/fe9/fe9Terrain.ts: the terrain table (Def, Avoid, healing and the cost for each movement
  group), from FE8Data.bin.
- src/data/fe9/fe9Maps.ts: every chapter's terrain grid (zmap/bmapNN/map.cmp), its units on Easy/Normal
  and Hard (dispos.cmp), and from the chapter script (Scripts/Cnn.cmb): the starting groups,
  reinforcements and when they come, chests, villages, doors, objectives and must-deploy units. The win
  and lose conditions come from the chapter table in FE8Data.bin.

Coordinates: the game counts from the top-left corner (0, 0); the app counts from the bottom-left (1, 1)
like the Fates maps, so (x, y) becomes (x + 1, height - y). Formats are in data-raw/fe9/README.md.
Run:  python scripts/build-fe9-maps.py
"""
import copy
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe9_cmb import Script  # noqa: E402
from fe9_files import GameData, map_files, read_text  # noqa: E402
from terrain_codes import encode, encode_map  # noqa: E402
import map_pieces  # noqa: E402
import tellius_minimaps  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe9')

# The game's terrain names (without their variant digits) -> the app's map letters. Terrains that share
# a letter must share their stats (checked below).
LETTERS = {
    # The ground, each kind as itself (they work alike).
    '平地': 'G', '訪問': 'G', '床': 'T', '台座': '{', '石畳': 'U', '雪原': 'Z', '船': 'D',
    '橋': 'b', '橋蓋': 'b', '階段': 'S',
    '玉座': 't', '制圧': 't', '到達': 't', '離脱': 't', '防衛': 't',
    '茂み': 'f', '光の茂み': 'H', '回復': 'H',
    '川': 'w', '水路': 'w', '海': 'a', '池': 'u', '堀': 'u',
    '崖': 'C', '岩': 'C',
    '木': 'k', '屋根': '7', '小物': '+', '建物': '%',
    '柵': 'l', '土嚢': 'l', '穴': 'x',
    '砂漠': 's', '沼': 'M', '山道': 'W', '海岸': 'Y',
    # A pillar no one can enter is a wall: the pillar icon is kept for ones a unit can stand on (Fates').
    '柱': '0', '宝箱': 'c', '扉': 'd', '壊れる扉': 'd',
    # Walls by what they are: a castle's, ruins; the rest (map edges, fountains, flowerbeds) a plain wall.
    '移動不可': '#', '城門': '0', '壁': '0', '廃墟': '1', '遺跡': '1', '城': '0', '砦': '0', '噴水': '(',
    '花壇': '#', 'アーチ': 'L', '投石器': 'L', '落石': '#', '未設定': '#', '光の守り': 'K',
}
# The app's name for each letter on Path of Radiance's maps.
LETTER_NAMES = {
    '.': 'Plain / floor', 'b': 'Bridge', 'S': 'Stairs', 't': 'Throne / goal tile', 'f': 'Thicket', 'H': 'Healing thicket',
    'w': 'River', 'a': 'Sea', 'u': 'Pond / moat', 'C': 'Cliff / rock', 'k': 'Tree', 'B': 'Building / roof',
    'l': 'Fence', 'x': 'Hole', 's': 'Desert', 'M': 'Swamp', 'W': 'Trail', 'p': 'Pillar', 'c': 'Chest',
    'd': 'Door', '#': 'Wall / structure', 'L': 'Ballista', 'K': 'Talisman tile', 'Y': 'Coast', 'Q': 'Roof (closed room)',
    'G': 'Plain', 'T': 'Floor', 'U': 'Paving', 'Z': 'Snowfield', 'D': 'Deck', '0': 'Castle wall', '5': 'Sandstone wall', '@': 'Plain (paving)', '1': 'Ruins',
    '7': 'Roof',
    '+': 'Odds and ends', '%': 'House / building', '`': 'Plain (mossy cobbles)', '(': 'Fountain', '{': 'Pedestal (a wooden platform)',
}
# Movement groups: the game's movement types that share every terrain cost, named as players know them.
GROUP_NAMES = {1: 'Infantry', 3: 'Knights', 4: 'Generals', 5: 'Mages, priests & thieves', 7: 'Horse knights',
               8: 'Paladins & Valkyries', 9: 'Fliers', 11: 'Bandits & Berserkers', 12: 'Beast laguz'}
# The difficulties and the placement file each opens with: Easy takes the '_m' records (the Japanese release's Maniac;
# InstantDisposRank picks them on Easy, main.dol 0x801a1884), Normal '_n', Hard '_h'.
DIFFS = {'Easy': 'm', 'Normal': 'n', 'Hard': 'h'}
# What the scripts' difficulty tests return on each difficulty: Normal() is true on Easy too, and Easy() isn't a function at all
# (an unknown name returns 0), nor is Maniac() ever true on this disc (main.dol 0x800b78d4-0x800b7938, 0x80011d98).
TRUE_ON = {'Normal': {'Easy', 'Normal'}, 'Hard': {'Hard'}, 'Easy': set(), 'Maniac': set()}
# The placement file a group name's ending names.
CODE_DIFF = {code: d for d, code in DIFFS.items()}
# Which of a group's copies a difficulty takes when the script names more than one: its own, then the next closest. The game
# finds a group by name in any difficulty's records, so one named alone comes on every difficulty that runs the call.
PREFER = {'Easy': 'mnh', 'Normal': 'nmh', 'Hard': 'hnm'}
DISPOS_CALLS = ('Dispos', 'DisposSetMode', 'DisposContinue', 'DisposContinueSetMode', 'InstantDisposFirstSetMode',
                'DisposAuxiliary', 'InstantDispos', 'InstantDisposFirst', 'InstantDisposRank', 'InstantDisposSetMode',
                'DisposAsynchronous')
PHASE = {0: 'start of the player phase', 1: 'start of the enemy phase', 2: 'start of the ally phase'}
# What opens each trial map, set in the program rather than a script: clearing the story opens Trial 1 on any difficulty, 2 on
# Normal or Hard and 3 on Hard (main.dol 0x801e3400), and a Game Boy Advance link the rest: The Blazing Blade opens 5, The Sacred
# Stones 6, either one 4 (0x801f5544). The trial menu reads these (0x801f7880).
TRIAL_OPENS = {
    91: 'Opens once the story is cleared, on any difficulty.',
    92: 'Opens once the story is cleared on Normal or Hard.',
    93: 'Opens once the story is cleared on Hard.',
    94: 'Opens with a Game Boy Advance link to The Blazing Blade or The Sacred Stones.',
    95: 'Opens with a Game Boy Advance link to The Blazing Blade.',
    96: 'Opens with a Game Boy Advance link to The Sacred Stones.',
}


def strip_digits(name):
    return name.rstrip('０１２３４５６７８９')


class Reloc:
    """A pointer-relocated data file (map.bin, dispos_*.bin): see data-raw/fe9/README.md."""

    def __init__(self, d):
        _, size, n_ptrs, n_names = struct.unpack_from('>4I', d, 0)
        ptrs_at = 0x20 + size
        names_at = ptrs_at + n_ptrs * 4
        strings_at = names_at + n_names * 8
        self.data = d[0x20:0x20 + size]
        self.ptrs = set(struct.unpack_from(f'>{n_ptrs}I', d, ptrs_at))
        self.tables = sorted((struct.unpack_from('>I', d, names_at + k * 8)[0],
                              self._c(d, strings_at + struct.unpack_from('>I', d, names_at + k * 8 + 4)[0]))
                             for k in range(n_names))
        self.named = {n: o for o, n in self.tables}

    @staticmethod
    def _c(d, o):
        return d[o:d.index(b'\0', o)].decode('shift_jis')

    def string(self, o):
        """The string a pointer field points at, or None."""
        if o not in self.ptrs:
            return None
        return self._c(self.data, struct.unpack_from('>I', self.data, o)[0])


class Game:
    def __init__(self):
        self.g = GameData()
        self.text = read_text('common.m')
        g, t = self.g, self.text
        self.items = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in g.records('IID_', 'MIID_')}
        self.classes = {g.string(g.u32(o)): t.get(g.string(g.u32(o + 4))) for o in g.records('JID_', 'MJID_')}
        self.move_type = {g.string(g.u32(o)): g.d[o + 66] for o in g.records('JID_', 'MJID_')}
        pids = g.records('PID_', 'MPID_')
        shared = Counter(g.string(g.u32(o + 4)) for o in pids)
        faces = defaultdict(set)
        for o in pids:
            faces[g.string(g.u32(o + 12))].add(g.string(g.u32(o + 4)))
        self.people = {}
        for o in pids:
            mpid, face = g.string(g.u32(o + 4)), g.string(g.u32(o + 12))
            skills = [g.string(g.u32(o + 4 * k)) for k in (7, 8, 9)]
            # A character has a portrait of their own (FID_GREIL, however many records Greil has). Generic
            # units share a faction's portrait across many names (FID_DAYNE: Soldier, Watch, Mercenary...),
            # or a name with others and a portrait that isn't theirs (Pirates, FID_BANDITS2).
            own_face = face == 'FID_' + mpid[5:]
            self.people[g.string(g.u32(o))] = {
                'name': t.get(mpid) or mpid,
                'generic': not face or len(faces[face]) >= 2 or (shared[mpid] >= 3 and not own_face),
                'boss': any(s in ('SID_BOSS', 'SID_FINAL') for s in skills),
            }
        self.terrain = self._terrain()
        self.no_stand = self._no_stand()
        self.english = self._terrain_names()
        self.chapters = self._chapters()

    def _terrain(self):
        """{game terrain name: (avoid, def, heal, costs by movement type)}."""
        g, out = self.g, {}
        o = next(x for x in range(0x20, len(g.d) - 12, 4) if g.string(g.u32(x)) == '移動不可' and (g.string(g.u32(x + 4)) or '').startswith('MT_'))
        while (g.string(g.u32(o + 4)) or '').startswith('MT_'):
            rec = g.d[0x20 + g.u32(o + 8):0x20 + g.u32(o + 8) + 23]
            out[g.string(g.u32(o))] = (rec[0], rec[1], rec[6], tuple(rec[8:23]))
            o += 12
        return out

    def _no_stand(self):
        """The game's terrain names no unit may stop on (byte 7 of the record): Building, Roof, Tree, Fence, Hole and the like,
        which fliers can still cross where their cost allows. The routine at main.dol 0x80107e60 rules such a tile out before
        it looks at who's on it; in the game a flier crosses a village house but can't land on it (the user, 2026-11-01)."""
        g, out = self.g, set()
        o = next(x for x in range(0x20, len(g.d) - 12, 4) if g.string(g.u32(x)) == '移動不可' and (g.string(g.u32(x + 4)) or '').startswith('MT_'))
        while (g.string(g.u32(o + 4)) or '').startswith('MT_'):
            if g.d[0x20 + g.u32(o + 8) + 7]:
                out.add(g.string(g.u32(o)))
            o += 12
        return out

    def _terrain_names(self):
        """{game terrain name: its English name} ('平地' -> 'Plain'), from the terrain table's MT_ labels."""
        g, out = self.g, {}
        o = next(x for x in range(0x20, len(g.d) - 12, 4) if g.string(g.u32(x)) == '移動不可' and (g.string(g.u32(x + 4)) or '').startswith('MT_'))
        while (g.string(g.u32(o + 4)) or '').startswith('MT_'):
            out[strip_digits(g.string(g.u32(o)))] = self.text.get(g.string(g.u32(o + 4)))
            o += 12
        return out

    def _chapters(self):
        g, t = self.g, self.text
        out = {}
        # The story's chapters (MCTnn, on bmapNN) and the trial maps (MTM_TRI_MAPn, on trial_0n), keyed by
        # script number: C01-C31 and C91-C96.
        for o in g.records('MCT', 'bmap') + g.records('MTM_TRI_MAP', 'trial'):
            mct = g.string(g.u32(o))
            label = lambda k: g.string(g.u32(o + 4 * k)) if g.u32(o + 4 * k) else None  # noqa: E731
            clean = lambda s: re.sub(r'#X3A|#x', '', t.get(s, s)) if s else None  # noqa: E731
            out[int(label(2)[1:])] = {
                'folder': label(1), 'blurb': t.get(mct + '_EX'),
                'title': t[mct], 'win': clean(label(5)), 'lose': clean(label(7)),
                # Extra conditions: slot 0 another way to lose; slot 1 the second goal set's win, which is Hard's (Ch.20's
                # 20 turns: the script's own limit is 15 on Normal, 20 on Hard and 15 on Maniac).
                'lose2': clean(label(8)), 'hard_win': clean(label(9)),
                # Levels added to the generic foes (+0x3d-+0x40: Normal, Hard, Maniac, Easy): 2 on Easy in every story
                # chapter, none in the trials (main.dol 0x801661cc).
                'level_bonus': {'Normal': g.d[o + 0x3d], 'Hard': g.d[o + 0x3e], 'Easy': g.d[o + 0x40]},
            }
        return out


def build_terrain(game):
    """FE9_TERRAIN by letter, and the movement groups."""
    by_cost = defaultdict(list)
    for mt in range(15):
        by_cost[tuple(v[3][mt] for v in game.terrain.values())].append(mt)
    groups = []  # (name, representative movement type, examples)
    for types in by_cost.values():
        name = next((GROUP_NAMES[m] for m in types if m in GROUP_NAMES), None)
        if name is None:
            continue  # a movement type no playable or enemy class uses
        examples = sorted({c for j, c in game.classes.items() if c and game.move_type.get(j) in types and not c.startswith('JID')
                           and c not in ('Dummy', 'Child', 'Citizen', 'Princess Crimea', 'King Daein')})
        groups.append((name, types[0], examples))
    order = list(GROUP_NAMES.values())
    groups.sort(key=lambda gr: order.index(gr[0]))
    table = {}
    for name, (avo, dfn, heal, costs) in game.terrain.items():
        letter = LETTERS.get(strip_digits(name))
        if not letter:
            continue
        move = {gname: (None if costs[mt] == 255 else costs[mt]) for gname, mt, _ in groups}
        entry = {'name': LETTER_NAMES[letter], 'def': dfn, 'avo': avo, 'heal': heal, 'move': move}
        if name in game.no_stand and any(v is not None for v in move.values()):
            entry['note'] = 'Fliers can fly over it, but no unit can stop on it.'
        if letter in table:
            a, b = table[letter], entry
            impassable = all(v is None for v in a['move'].values())
            if (a['move'] != b['move'] or a['def'] != b['def'] or a['avo'] != b['avo'] or (a['heal'] != b['heal'] and not impassable)
                    or a.get('note') != b.get('note')):
                raise SystemExit(f'{name} differs from the other terrain on letter {letter!r}')
        else:
            table[letter] = entry
    # A sandy map's castle walls are sandstone (sandy_map); a town's paved plain is plain (paved_town).
    table['5'] = {**table['0'], 'name': LETTER_NAMES['5']}
    table['@'] = {**table['G'], 'name': LETTER_NAMES['@']}
    table['`'] = {**table['G'], 'name': LETTER_NAMES['`']}
    table['('] = {**table['#'], 'name': LETTER_NAMES['(']}
    # A room under its roof until a door into it opens: the game's table lets fliers onto a roof, but no unit enters a closed
    # room in play (the user, in the game), so it's a wall to everyone until then.
    table['Q'] = {'name': LETTER_NAMES['Q'], 'def': 0, 'avo': 0, 'heal': 0, 'move': {g: None for g, _, _ in groups},
                  'note': 'A room under its roof: no unit can enter it, fliers included, until a door into it opens.'}
    # The machine itself: no one enters it; a bow user fires it from the tile beside it.
    if 'L' in table:
        table['L']['note'] = 'The machine itself: no one can enter it. A bow user fires it from the marked tile beside it.'
    return table, groups


def dispos(folder, diff):
    """All groups in a chapter's placement file: {group: [unit dict]}."""
    files = map_files(folder, 'dispos')
    name = f'dispos_{diff}.bin'
    if name not in files:
        return {}
    r = Reloc(files[name])
    out = {}
    for i, (o, group) in enumerate(r.tables):
        if group.endswith('date_' + diff):
            continue
        count, p, units = r.data[o], o + 4, []
        for _ in range(count):
            raw = r.data[p:p + 108]
            items = [r.string(p + 12 + 4 * k) for k in range(8)]
            units.append({
                'pid': r.string(p), 'jid': r.string(p + 4),
                'weapons': [x for x in items[:4] if x], 'items': [x for x in items[4:] if x],
                # Slot flags, bytes 100-103 for the weapon slots and 104-107 for the item slots: bit 0 drops the item, bit 1
                # holds it only from a second playthrough on (the bands; main.dol 0x8003edd0 skips the slot on the first).
                'drops': [items[k] for k in range(8) if items[k] and raw[100 + k] & 1],
                'replay': [items[k] for k in range(8) if items[k] and raw[100 + k] & 2],
                'skills': [x for x in (r.string(p + 44 + 4 * k) for k in range(5)) if x],
                # Its AI routines (bytes 76-88): SEQ_LOOTERMOVE goes for villages and chests, _ESCAPE leaves by an exit after.
                'ai': [x for x in (r.string(p + 76 + 4 * k) for k in range(4)) if x],
                'from': (raw[92], raw[93]), 'at': (raw[94], raw[95]), 'level': raw[96], 'side': raw[97],
                # Byte 98 bit 0: stats rolled from the class's growths (every generic foe, no battle boss); such a foe gains
                # the chapter's level bonus for the difficulty (main.dol 0x8003d70c).
                'grown': bool(raw[98] & 1),
            })
            p += 108
        out[group] = units
    return out


LEVELS = ('Normal', 'Hard', 'Easy', 'Maniac')


def calls(script, h, follow=True):
    """The handler's calls with their literal arguments: [(name, [args])]. With follow=False, only its own (not those of
    the handlers it calls): for scans over every handler, which would see a callee's calls twice."""
    return [(fn, args) for fn, args, _ in calls_by_difficulty(script, h, depth=0 if follow else 8)]


# What a chapter's script does that its handlers don't say in so many words, read by hand from the scripts and checked against
# the Fire Emblem Wiki (data-raw/fe9/README.md, "Read by hand"). By chapter file: a unit's name, note (added) or talk, by PID;
# a group's arrival, by group; a joiner's condition or talk, by name; the chapter's notes; units the game sets on fixed tiles;
# the goal where the record doesn't give all of it.
ALARM = ('When a Watch raises the alarm: at the start of an enemy phase if a Watch can attack one of your units, when one of '
         'your units fights a Watch, or when a Watch dies')
PRISONER = ('Once its cell door is open, it heads for the exit at (5, 19)\u2013(6, 19): it joins your army when it leaves by it, '
            "or at the end if its door was opened and it's still on the map. Its cell door: {}")
# Items a unit uses up at once with no effect id of their own: the keys and the Laguz Stones (the rest of the momentary ones,
# healing, curing and the Torch, carry one: item record +56, EID_LIVE, EID_SPECIFIC, EID_ANTIDOTE, EID_HOLYWATER, EID_TORCH).
MOMENTARY_ITEMS = {'IID_TREASUREKEY', 'IID_DOORKEY', 'IID_CHANGESTONE', 'IID_CHANGESTONE1'}
_STEAL = []


def steal_rules():
    """(sold, staves, tomes, strikes, momentary, worn): what Steal and the shops need, read once with build-fe9-items.py's readers.
    Sold: a base's armory or item shop stocks it, or its forge offers it. Momentary: an item used up for a moment's effect
    (MOMENTARY_ITEMS and those with an effect id). Worn: the accessories (item record +12 'acc': bands, guards, the Knight Ring)."""
    if not _STEAL:
        import importlib.util
        spec = importlib.util.spec_from_file_location('items9', os.path.join(os.path.dirname(__file__), 'build-fe9-items.py'))
        it = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(it)
        g = GameData()
        text = read_text('common.m')
        forge, _ = it.availability(text, [('FSHOP_ITEMS', 2)])
        shop, _ = it.availability(text, [('WSHOP_ITEMS', 1), ('ISHOP_ITEMS', 1)])
        kinds = {g.string(g.u32(o)): (g.string(g.u32(o + 12)), g.string(g.u32(o + 56)) or '') for o in g.records('IID_', 'MIID_')}
        staves = {i for i, (k, e) in kinds.items() if k == 'rod' and not e.startswith('EID_LIGHT')}
        tomes = {i for i, (k, e) in kinds.items() if k in ('flame', 'thunder', 'wind') or e.startswith('EID_LIGHT')}
        momentary = {i for i, (k, e) in kinds.items() if k == 'item' and (e or i in MOMENTARY_ITEMS)}
        worn = {i for i, (k, _) in kinds.items() if k == 'acc'}
        _STEAL.extend([set(shop) | set(forge), staves, tomes, set(it.class_strikes().values()), momentary, worn])
    return _STEAL


def stealable(u):
    """The IIDs of a placed foe's that Steal takes and it doesn't drop, as build-fe9-items.py's obtainable() reads Steal: anything
    unequipped (the tutorial, tut.m MS_T11盗む_01: "they can't steal items that are already equipped"), so every item but the
    accessory it wears (no foe holds two: Shiharam's Full Guard, Ena's Demi Band stay theirs), and its weapons when it has more than
    one to fight with (it unequips one to fight with the other) or a lone tome beside an item (silenced, it unequips the tome to use
    the item); never a staff or a laguz's own attack."""
    _, staves, tomes, strikes, _, worn = steal_rules()
    arms = [w for w in u['weapons'] if w not in staves and w not in strikes]
    loose = len(arms) > 1 or (arms and arms[0] in tomes and u['items'])
    rest, out = list(u['drops']), []
    for i in [x for x in u['items'] if x not in worn] + (arms if loose else []):
        if i in rest:
            rest.remove(i)
        else:
            out.append(i)
    return out


BY_HAND = {
    # Ch.3: Marcia's talk is what brings her back in Ch.9 (talk 17: she flies off the map).
    4: {'joiner_talk': {'Marcia': 'Talk with Ike: she flies off the map, and this talk is what brings her back in Ch.9'}},
    # Ch.9: she comes only if Ike talked to her in Ch.3 and she survived it (handler 23). After preparations Mist and Rolf
    # walk in and join you (Opening2, handler 21). Lethe and Mordecai are a partner army; each joins before Ch.10 if alive
    # (Ch.10's Opening0: Join('always_lete') unless G_レテ死亡).
    10: {'joiner_when': {'Marcia': ' (only if Ike talked to her in Ch.3 and she survived it)'},
         'note': {'PID_LETHE': '. Fights on her own; joins your army before Ch.10 if she survives',
                  'PID_MORDY': '. Fights on his own; joins your army before Ch.10 if he survives'}},
    # Ch.10: the alarm (handler 32, called by 37, 38, 49-56) brings all three groups at once. The prisoners' talks make them
    # partner units (army 3); they join as they leave by the exit (handler 5) or at the end (handler 57; not on Maniac).
    11: {'name': {'PID_D_ZAKO_11_1': 'Watch', 'PID_D_ZAKO_11_2': 'Watch', 'PID_D_ZAKO_11_3': 'Watch', 'PID_D_ZAKO_11_4': 'Watch'},
         'note': {**{f'PID_D_ZAKO_11_{k}': '. Walks a fixed route and never attacks; it raises the alarm if it can attack one of '
                                            'your units at the start of an enemy phase, is fought, or dies' for k in range(1, 5)},
                  'PID_CHAP': '. ' + PRISONER.format('(18, 7)'), 'PID_KEVIN': '. ' + PRISONER.format('(18, 7)'),
                  'PID_NEPENEE': '. ' + PRISONER.format('(10, 14)'),
                  'PID_CEPHERAN_FAKE': '. Heads for the exit once his cell door at (7, 7) is open; his talk only changes the closing scene'},
         'when': {'bmap11_zoen1': ALARM}, 'escapers': ['PID_CHAP', 'PID_KEVIN', 'PID_NEPENEE', 'PID_CEPHERAN_FAKE']},
    # Ch.11: the Black Knight comes out of the house at (20, 15) at the start of the enemy phase after anyone first fights
    # Mackoya (battle talks 48-51 set the flag, handler 28 places him).
    12: {'when': {'bmap12_z_blk_c': 'At the start of the enemy phase after a unit first fights the boss, Mackoya: out of the house at (20, 15)'}},
    # Ch.12: Jill comes only if she was on the map at the end of Ch.11 (G_ジル仲間条件, handler 13), and flies to Ike to talk.
    13: {'joiner_when': {'Jill': " (only if she was still on the map at the end of Ch.11, where she's a foe)"},
         'joiner_talk': {'Jill': 'Recruit: she flies to Ike and starts the talk herself'}},
    # Ch.13: Gatrie comes back as he left your army (handler 18 gives a Steel Lance and a Vulnerary if he has no weapon).
    14: {'note_replace': {'PID_GATRIE': 'Knight, as he left your army in Ch.7 (his own level and items; a Steel Lance and a '
                                        "Vulnerary if he has no weapon)"}},
    # Ch.18: Shinon joins at the end only if Rolf talked to him and Ike defeated him (end handler 49). The setup (handler 14)
    # gives him a Brave Bow, set to drop, and a Vulnerary if he has no weapon.
    19: {'note_replace': {'PID_CHINON': 'Sniper, as he left your army in Ch.7 (his own level; a Brave Bow, which he drops, and a '
                                        'Vulnerary if he has no weapon)'},
         'drops': {'PID_CHINON': ['Brave Bow']},
         'talk': {'PID_CHINON': 'Recruit: Rolf talks to him, then Ike defeats him; he joins at the end (also talks with Mist and Rhys)'}},
    # Ch.19: Naesala can't die (SID_IMMORTAL from Opening1). Janaff's or Ulki's talk (82-83) turns him to Reyson; his talk with
    # Reyson (84) gives a Knight Ring if no raven died, turns him green, and handler 80 sends every raven off by the side edges.
    20: {'talk': {'PID_NAESALA': 'Talk with Janaff or Ulki: he stops fighting and flies to Reyson'},
         'note': {'PID_NAESALA': ". Can be beaten but won't die. Talking to Reyson (once Janaff or Ulki has talked to him), he "
                                 "gives Reyson a Knight Ring if no raven has died, turns green, and every Kilvas raven turns green "
                                 "and leaves by the map's left or right edge; beating him sends them off the same way. On Hard he "
                                 "also carries a Laguz Band and a Coin, and starts transformed",
                  'PID_K_ZAKO': ". Leaves by the map's left or right edge once Naesala withdraws"}},
    # Ch.20: unless Jill has an A support with Mist or Lethe, the talk sends her over to the enemy for good (talks 26-27); on
    # Normal the opening (handler 22) only offers it when she has one.
    21: {'talk': {'PID_SIHARAMU': 'Talk with Jill: unless she has an A support with Mist or Lethe, she goes over to the enemy for good '
                                  "(on Normal the talk is only offered when she has one)"}},
    # Ch.23: the Crimean Paladins fight on your side but never attack Petrine (SEQ_ALLATK100_NOPRAGUE).
    24: {'joiner_note': {'Paladin': 'Crimean knights: they fight on your side but never attack Petrine'}},
    # Ch.24: Geoffrey stays put with his knights and joins at the end if still on the map (end handler 56); the Black Knight
    # leaves once he has fought Ike (handler 29).
    25: {'note': {'PID_GEOFFRAY': ". Doesn't move, and his six knights stay with him; joins your army at the end if he's still on the map",
                  'PID_BLACKKNIGHT': '. Leaves the map once he has fought Ike'}},
    # Ch.27-2: tile events 1-3 end it when Ike (or Mist carrying him) leaves by the exit; handler 13 ends it on turn 5.
    29: {'victory': 'Defeat the Black Knight (the game shows ???), escape by the marked exit with Ike (Mist can carry him '
                    "out), or hold out to turn 5's ally phase"},
    # Ch.28: Tibarn is a partner unit who fights on his own.
    30: {'note': {'PID_TIBARN': ". Fights on his own, and doesn't join"}},
    # Endgame: only the royal you pick comes (handlers 18-19 on Easy and Normal, 22-23 on Hard).
    31: {'notes': ['Tibarn, Naesala and Giffca share one tile: only the one you pick comes. On Easy and Normal the game asks on '
                   'turn 2 and brings your choice on turn 3, or nobody; on Hard it asks once Ashnard\'s first form falls, and '
                   'your choice arrives at the next player phase.']},
}



def callees(script):
    """The numbers of the handlers another handler calls (opcode 0x37): what they do counts for their callers, so a scan
    over every handler that follows calls skips them (Ch.4's Opening0 calls the handler that gives Ike the Regal Sword)."""
    if not hasattr(script, '_callees'):
        script._callees = {int(a, 16) for h in script.handlers() for _, op, a in script.disasm(h)
                           if op == 'stmt' and int(a, 16) != h['i']}
    return script._callees


def handler_at(script, i):
    """A script's handler by its number (cached on the script)."""
    if not hasattr(script, '_by_i'):
        script._by_i = {hh['i']: hh for hh in script.handlers()}
    return script._by_i.get(i)


def calls_by_difficulty(script, h, alive=None, depth=0):
    """[(name, [args], difficulties that reach the call)]. The scripts branch on difficulty with
    `if (Normal()) { ... }` (`call Normal ; jz end`), `if (!Hard()) { ... }` (`... op29 ; jz end`), several
    joined by `orjump`; a block that ends in `return` also takes those difficulties out of what follows. A call
    into another handler (opcode 0x37) brings that handler's calls in, on the difficulties that reach it."""
    dis = script.disasm(h)
    stack, out, blocks = [], [], []
    alive = set(DIFFS) if alive is None else set(alive)
    pcs = [pc for pc, _, _ in dis]
    chained = set()  # the later tests of an 'a || b' chain, read with the first
    for k, (pc, op, a) in enumerate(dis):
        while blocks and pc >= blocks[-1][0]:
            alive = blocks.pop()[1]
        if op == 'stmt' and depth < 8:
            callee = handler_at(script, int(a, 16))
            if callee and callee['i'] != h['i']:
                out += calls_by_difficulty(script, callee, alive, depth + 1)
            continue
        if k in chained:
            continue
        if op == 'call' and a.split('/')[0] in LEVELS:
            names, j = {a.split('/')[0]}, k + 1
            while j + 1 < len(dis) and dis[j][1] == 'orjump' and dis[j + 1][1] == 'call' and dis[j + 1][2].split('/')[0] in LEVELS:
                names.add(dis[j + 1][2].split('/')[0])
                chained.add(j + 1)
                j += 2
            negate = j < len(dis) and dis[j][1] == 'op29'
            j += negate
            if j < len(dis) and dis[j][1] == 'jz':
                end = dis[j][2]
                true = set().union(*(TRUE_ON[x] for x in names))
                inside = (alive - true) if negate else (alive & true)
                last = max((i for i, x in enumerate(pcs) if x < end), default=j)
                after = alive - inside if dis[last][1] == 'ret' else alive
                blocks.append((end, after))
                alive = inside
        if op in ('str', 'int'):
            stack.append(a)
        elif op == 'call':
            fn, argc = a.split('/')
            argc = int(argc)
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            out.append((fn, args, frozenset(alive)))
    return out


def difficulty_turns(script, h):
    """Turns a handler checks with BMGetTurn, by difficulty: {'Easy': 9, 'Normal': 9, 'Hard': 6} (or {} if none).
    'Normal() || Hard()' is one test (Ch.13's first group: turn 5 on every difficulty, turn 4 on Maniac only)."""
    dis = script.disasm(h)
    out, cond, else_at = {}, None, None
    chained = set()
    for k, (pc, op, a) in enumerate(dis):
        if k in chained:
            continue
        if op == 'call' and a.split('/')[0] in ('Normal', 'Hard', 'Easy', 'Maniac'):
            names = {a.split('/')[0]}
            j = k + 1
            while j + 1 < len(dis) and dis[j][1] == 'orjump' and dis[j + 1][1] == 'call':
                names.add(dis[j + 1][2].split('/')[0])
                chained.add(j + 1)
                j += 2
            if j < len(dis) and dis[j][1] == 'jz':
                cond, else_at = set().union(*(TRUE_ON[x] for x in names)), dis[j][2]
        if op == 'call' and a == 'BMGetTurn/0' and k + 2 < len(dis) and dis[k + 1][1] == 'int' and dis[k + 2][1] == 'op30':
            turn = dis[k + 1][2]
            if cond is None:
                for d in DIFFS:
                    out.setdefault(d, turn)
            else:
                applies = cond if pc < else_at else set(DIFFS) - cond
                for d in DIFFS:
                    if d in applies:
                        out.setdefault(d, turn)
    return out


def goal_text(ch, units, later_goals, extra_cleared):
    """The chapter's win and lose conditions in plain words. `later_goals`: the goals its script sets as it
    moves on to new sections (Ch.17); `extra_cleared`: the extra loss condition is dropped when it no longer
    applies (Elincia's, when she isn't on the map)."""
    win = {'Rout enemy': 'Rout the enemy'}.get(ch['win'], ch['win'])
    if win == '???':
        # Ch.27-2 hides its goal; it's the duel with its one enemy.
        boss = next(u['name'] for u in units if u['type'] == 'boss')
        win = f"Defeat {'the ' if boss.startswith('Black') else ''}{boss} (the game shows ???)"
    turns = re.match(r'Arrive (\d+) turns', win)
    hard = re.match(r'Arrive (\d+) turns', ch['hard_win'] or '')
    on_hard = f' ({hard.group(1)} on Hard)' if turns and hard and hard.group(1) != turns.group(1) else ''
    if turns:
        win = f'Arrive within {turns.group(1)} turns{on_hard}'
    if later_goals:
        steps = [w[0].lower() + w[1:] for w in [win] + [{'Rout enemy': 'Rout the enemy'}.get(g, g) for g in later_goals]]
        win = f'In {len(steps)} sections: ' + ', then '.join(steps)
    lose = ch['lose']
    if ch['lose2']:
        over = re.match(r'Exceed (\d+) turns', ch['lose2'])
        extra = ch['lose2'][0].lower() + ch['lose2'][1:] if ch['lose2'].startswith('Enemy') else ch['lose2']
        lose += f", or take more than {over.group(1)} turns{on_hard}" if over else f", or {extra}{' (while on the map)' if extra_cleared else ''}"
    return win, lose


# The playable grid (game coordinates, 0-based from the top left: x0, x1, y0, y1). Each map file stores its own border width
# (mapextra byte 5, read at main.dol 0x80047af8), and the game blocks every move out of it (0x80023a4c): that's the grid.
# Ch.17's four sections share one map, so each keeps the part fireemblemwod.com's overview shots and the user's own check gave.
PLAYABLE = {
    (18, 1): (0, 19, 28, 55), (18, 2): (0, 27, 0, 26), (18, 3): (29, 51, 5, 26), (18, 4): (31, 55, 29, 47),
}


def border(mp):
    """The game's playable grid for a map file: its border width in from every edge."""
    w, h = struct.unpack_from('>2H', mp.data, 0)
    m = mp.data[mp.named['mapextra'] + 5]
    return (m, w - 1 - m, m, h - 1 - m)


# The models a map lays its top layer over while they're closed (mapbuilddesc flags 0x800 / 0x1000, not 0x10), by name:
# goal markers, village houses, doors, room roofs, rocks, trap lids and ruins. Opening or destroying one brings back the main
# layer under it (main.dol: DoorOpen 0x8019f4a8, BuildDestruction 0x8019eaf4, InstantRoofOpen 0x8019f13c).
GOAL_MODELS = ('ascendancy', 'attainment', 'defense', 'secession')
HOUSE_MODELS = ('house_', 'bar_')
ROOF_MODELS = ('castleroof', 'mansionroof')
# The edge table (maplink, maplinkAbs): per tile, the sides a ground unit may leave by (0x8 up, 0x4 down, 0x1 left, 0x2 right,
# in the game's top-down coordinates). maplink only binds ground units; maplinkAbs binds fliers too (Ch.17's section walls).
EXIT = {(0, -1): 0x8, (0, 1): 0x4, (-1, 0): 0x1, (1, 0): 0x2}


def top_layer(mp, handlers, hcalls, cells_only=False):
    """The map's top layer as the battle starts: {(x, y): (top terrain name, main terrain name, model name)} for every tile a
    closed model lays a different terrain on. A model an opening opens (InstantRoofOpen: Ch.12's gangplank) is left open.
    `cells_only`: every tile the top layer covers, whatever its terrain (its corner heights replace the main layer's)."""
    w, h = struct.unpack_from('>2H', mp.data, 0)

    def layer(suffix):
        def at(x, y):
            idx = struct.unpack_from('>H', mp.data, mp.named['panelindex' + suffix] + 2 * (y * w + x))[0]
            return strip_digits(mp.string(mp.named['uniquepanel' + suffix] + 12 * idx + 8))
        return at
    main, roof = layer(''), layer('Roof') if 'panelindexRoof' in mp.named else None
    if not roof:
        return {}
    d0, d1 = mp.named['mapbuilddesc'], mp.named['mapbuildinst']
    descs = [(struct.unpack_from('>7I', mp.data, o)[6], mp.string(o + 0x1c)) for o in range(d0, d1, 0x20)]
    inst_end = min(o for o, _ in mp.tables if o > d1)
    opened = {(a[0], a[1]) for hh in handlers if hh['name'].startswith('Opening')
              for fn, a in hcalls[hh['i']] if fn == 'InstantRoofOpen' and len(a) >= 2}
    out = {}
    for o in range(d1, inst_end, 12):
        x, y, rot, idx, rx0, ry0, rx1, ry1 = mp.data[o:o + 8]
        if idx >= len(descs):
            continue
        flags, name = descs[idx]
        if not flags & 0x1800 or flags & 0x10 or rot & 3:
            continue
        cells = [(cx, cy) for cy in range(max(0, ry0), min(h - 1, ry1) + 1) for cx in range(max(0, rx0), min(w - 1, rx1) + 1)]
        if any(c in opened for c in cells):
            continue
        for c in cells:
            if cells_only:
                out[c] = name
            elif roof(*c) != main(*c):
                out[c] = (roof(*c), main(*c), name)
    return out


def corner_heights(mp, covered):
    """{(x, y): its four corner heights}, the top layer's on `covered`, and the test for a step between two corners."""
    w, h = struct.unpack_from('>2H', mp.data, 0)
    unit = struct.unpack_from('>f', mp.data, mp.named['mapcapacity'] + 8)[0]

    def corners(suffix):
        idx = mp.named['panelindex' + suffix]
        recs = mp.named['uniquepanel' + suffix]
        return lambda x, y: struct.unpack_from('>4h', mp.data, recs + 12 * struct.unpack_from('>H', mp.data, idx + 2 * (y * w + x))[0])
    main = corners('')
    roof = corners('Roof') if 'panelindexRoof' in mp.named else None
    hts = {(x, y): (roof if (x, y) in covered else main)(x, y) for y in range(h) for x in range(w)}
    return hts, lambda a, b: (a - b) ** 2 >= 0.04 * unit * unit


def ship_stairs(mp, covered, names):
    """A ship's stairs: deck tiles (船) whose own corners climb a step from one side to the other. The game calls them Ship, but
    their sides along the climb are steps (height_exits), so a ground unit takes them only up or down: drawn as stairs."""
    hts, step = corner_heights(mp, covered)
    return {p for p, c in hts.items() if names[p[1]][p[0]] == '船' and (step(c[0], c[1]) or step(c[2], c[3]) or step(c[0], c[2]) or step(c[1], c[3]))}


def height_exits(mp, covered):
    """{(x, y): the sides a ground unit may leave by (EXIT bits)} from the tiles' corner heights, as the map loads (main.dol
    0x80023b80 opens every side, then 0x800237a0 closes those between tiles whose shared corners differ): each `uniquepanel`
    record starts with four corner heights (top-left, top-right, bottom-left, bottom-right), the top layer's where a closed model
    lays it (`covered`), and a side shuts to ground units when either corner pair differs by a fifth of the map's unit or more
    ((d / unit)^2 >= 0.04, the unit the float at `mapcapacity` +8). Fliers pass. Opening a door or roof loads the map again
    (DoorOpen and InstantRoofOpen call 0x80044450), so a room's floor has its own heights once a unit can walk it: `covered`
    holds only the tiles walkable under their top layer (goal markers, trap lids)."""
    return step_exits(*corner_heights(mp, covered))


def step_exits(hts, step):
    """The sides between two tiles whose shared corners are a step apart, closed: {(x, y): the sides left open (EXIT bits)}
    for the tiles with one closed. `hts` maps each tile to its corner heights (top-left, top-right, bottom-left, bottom-right)."""
    # (side, this tile's two corners, the neighbour's two corners facing them)
    sides = (((0, -1), (0, 1), (2, 3)), ((0, 1), (2, 3), (0, 1)), ((-1, 0), (0, 2), (1, 3)), ((1, 0), (1, 3), (0, 2)))
    out = {}
    for (x, y), c in hts.items():
        mask = 0xF
        for (dx, dy), mine, theirs in sides:
            n = hts.get((x + dx, y + dy))
            if n and any(step(c[i], n[j]) for i, j in zip(mine, theirs)):
                mask &= ~EXIT[(dx, dy)]
        if mask != 0xF:
            out[(x, y)] = mask
    return out


# What a prop tile (小物, odds and ends) holds, by the name of the 3D model standing on it (the user: a castle's props are mostly lights,
# a port's crates and barrels): the first name that matches. Both games' models: Path of Radiance's candle_02, box_01, barrel_01,
# ｆlowerpot_01, sculpture_selinos_01; Radiant Dawn's cndl03, indr0405cd01 (Part 4 Ch.4's candles), boxx01, brrl01, cart01, snbd01
# (sandbags), trsr_sand (gold), indr0407a_pillar (the Tower's small pillars). parts, deco and royal pieces stay odds and ends.
PROP_KINDS = (('house_', 'roof'), ('roof_', 'roof'), ('candle', 'candle'), ('cndl', 'candle'), ('cd0', 'candle'), ('box', 'box'), ('barrel', 'barrel'), ('brrl', 'barrel'),
              ('cart', 'cart'), ('flowerpot', 'flowerpot'), ('sculpture', 'statue'), ('pillar', 'pillar'), ('snbd', 'sandbags'),
              ('trsr', 'gold'))


def prop_kind(models):
    """The kind of prop the models on a tile make, or None."""
    for part, kind in PROP_KINDS:
        if any(part in m.lower() for m in models):
            return kind
    return None


def models_on(mp):
    """{(x, y): the names of the models placed over the tile} (mapbuildinst's rectangles, and each model's own tile)."""
    d0, d1 = mp.named['mapbuilddesc'], mp.named['mapbuildinst']
    descs = [mp.string(o + 0x1c) or '' for o in range(d0, d1, 0x20)]
    end = min(o for o, _ in mp.tables if o > d1)
    on = defaultdict(list)
    for o in range(d1, end, 12):
        x, y, rot, idx, rx0, ry0, rx1, ry1 = mp.data[o:o + 8]
        if idx < len(descs):
            for cy in range(ry0, ry1 + 1):
                for cx in range(rx0, rx1 + 1):
                    on[(cx, cy)].append(descs[idx])
            if (x, y) not in on:
                on[(x, y)].append(descs[idx])
    return on


def edge_masks(mp):
    """{(x, y): (ground exits, also binds fliers)} for the tiles the edge table names (every other tile is open all round)."""
    out = {}
    for name in ('maplink', 'maplinkAbs'):
        o = mp.named.get(name)
        if o is None:
            continue
        for k in range(struct.unpack_from('>h', mp.data, o)[0]):
            x, y, v = mp.data[o + 2 + 3 * k:o + 5 + 3 * k]
            out[(x, y)] = (v & 0xF, name == 'maplinkAbs')
    return out

# A fence model's rotation (top two bits) -> the tile side it stands on.
FENCE_SIDE = {0x00: 'w', 0x80: 'e', 0x40: 'n', 0xC0: 's'}
# Units placed on the map who never take part, by chapter file: why, as the map's note.
WATCHING = {
    1: {'PID_MIST': "Mist watches from just off the map. She walks over to hand Ike a practice sword if he's left "
                    "without a weapon, and a Vulnerary once Boyd is beaten."},
}
# The facing a ballista (SetShooter) or boulder (SetRock) call gives, as a step in game coordinates.
FACING = {1: (-1, 0), 2: (1, 0), 4: (0, 1), 8: (0, -1)}
# Numpad directions in the scripts' walk strings ('2242444').
STEP = {'2': (0, 1), '8': (0, -1), '4': (-1, 0), '6': (1, 0)}


def expand(corners):
    """Corner tiles -> every tile along the path."""
    out = [corners[0]]
    for (x, y) in corners[1:]:
        px, py = out[-1]
        while (px, py) != (x, y):
            px += (x > px) - (x < px)
            py += (y > py) - (y < py)
            out.append((px, py))
    return out


def shift(m, dx, dy):
    """Move every tile on the map by (-dx, -dy) after a crop."""
    def mv(t):
        return [t[0] - dx, t[1] - dy]

    def mv_rect(a):
        l, b, r, t = a['rect']
        a['rect'] = [l - dx, b - dy, r - dx, t - dy]

    for u in m['units']:
        u['tile'] = mv(u['tile'])
        if 'goesTo' in u:  # where its AI sends it (Radiant Dawn's fleeing horses)
            u['goesTo'] = [mv(t) for t in u['goesTo']]
    m['starts'] = [mv(t) for t in m['starts']]
    for f in m.get('forced', []):
        if 'tile' in f:
            f['tile'] = mv(f['tile'])
    for o in m['objects']:
        o['tile'] = mv(o['tile'])
        if 'machine' in o:  # a ballista's machine, beside its firing tile
            o['machine'] = mv(o['machine'])
        if 'area' in o:  # a hidden item's dig zone
            l, b, r, t = o['area']
            o['area'] = [l - dx, b - dy, r - dx, t - dy]
    for o in m['objectives']:
        o['tiles'] = [mv(t) for t in o['tiles']]
    if 'corrinStart' in m:
        m['corrinStart'] = mv(m['corrinStart'])
    if 'props' in m:
        m['props'] = {','.join(map(str, mv([int(v) for v in k.split(',')]))): kind for k, kind in m['props'].items()}
    for w in m.get('walls', []):
        w['tile'] = mv(w['tile'])
    for c in m['changes']:
        c['tile'] = {'default': mv(c['tile']['default'])}
        for p in c.get('patch', []):
            p['tile'] = mv(p['tile'])
        if 'path' in c:
            c['path'] = [mv(t) for t in c['path']]
    for g in m.get('reinforcements', []):
        for u in g['units']:
            u['tile'] = mv(u['tile'])
            if 'from' in u:
                u['from'] = mv(u['from'])
            if 'goesTo' in u:  # an arriving looter's exits, or where its AI sends it
                u['goesTo'] = [mv(t) for t in u['goesTo']]
        for a in g.get('areas', []):
            mv_rect(a)
    for j in m.get('joiners', []):
        j['tile'] = mv(j['tile'])
        j['from'] = mv(j['from'])
        for a in j.get('areas', []):
            mv_rect(a)


def cut(m, left, right, bottom, top):
    """Cut the map to columns left..right and rows bottom..top (map tiles)."""
    W, H = m['width'], m['height']
    left, right, bottom, top = max(1, left), min(W, right), max(1, bottom), min(H, top)
    if (left, bottom, right, top) == (1, 1, W, H):
        return m
    m['grid'] = [row[left - 1:right] for row in m['grid'][H - top:H - bottom + 1]]
    if '_names' in m:  # Path of Radiance's per-tile names, kept in step with the grid until they're written out
        m['_names'] = [row[left - 1:right] for row in m['_names'][H - top:H - bottom + 1]]
    m['width'], m['height'] = right - left + 1, top - bottom + 1
    shift(m, left - 1, bottom - 1)
    m['walls'] = [w for w in m.get('walls', []) if 1 <= w['tile'][0] <= m['width'] and 1 <= w['tile'][1] <= m['height']]
    if not m['walls']:
        del m['walls']
    if 'props' in m:
        m['props'] = {k: v for k, v in m['props'].items()
                      if 1 <= int(k.split(',')[0]) <= m['width'] and 1 <= int(k.split(',')[1]) <= m['height']}
    return m


def crop(m, ground, margin=0, reach=True):
    """Trim the map to where things happen: every tile a unit can walk to from anything on the map (or,
    with reach=False, just the things themselves), plus a margin. Ch.13's ships sit in 62x59 tiles of sea."""
    return cut(m, *reach_bounds(m, ground, margin, reach))


def reach_bounds(m, ground, margin=0, reach=True):
    """The (left, right, bottom, top) map tiles `crop` keeps."""
    W, H = m['width'], m['height']
    seeds = [tuple(u['tile']) for u in m['units']] + [tuple(t) for t in m['starts']] + [tuple(o['tile']) for o in m['objects']]
    seeds += [tuple(t) for o in m['objectives'] for t in o['tiles']]
    seeds += [tuple(u['tile']) for g in m.get('reinforcements', []) for u in g['units']] + [tuple(j['tile']) for j in m.get('joiners', [])]
    seeds += [tuple(t) for c in m['changes'] for t in c.get('path', [])]
    seeds = [s for s in seeds if 1 <= s[0] <= W and 1 <= s[1] <= H]
    keep = set(seeds)
    if reach:
        def letter(x, y):
            return m['grid'][H - y][x - 1]
        todo = [s for s in seeds if letter(*s) in ground]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 1 <= nx <= W and 1 <= ny <= H and (nx, ny) not in keep and letter(nx, ny) in ground:
                    keep.add((nx, ny))
                    todo.append((nx, ny))
    # ...but no further than a few tiles past the outermost thing on the map (Endgame's open floor runs on
    # far beyond the battle).
    sx = [x for x, _ in seeds]
    sy = [y for _, y in seeds]
    keep = {(x, y) for x, y in keep if min(sx) - 2 <= x <= max(sx) + 2 and min(sy) - 2 <= y <= max(sy) + 2}
    return (max(1, min(x for x, _ in keep) - margin), min(W, max(x for x, _ in keep) + margin),
            max(1, min(y for _, y in keep) - margin), min(H, max(y for _, y in keep) + margin))


def crop_to(m, left, right, bottom, top):
    """Cut the map to its playable grid. Anyone placed off it only watches (Haar and his wyverns in Ch.11)
    or, in Ch.17, belongs to another section, and is left out."""
    def inside(p):
        return left <= p[0] <= right and bottom <= p[1] <= top
    gone = [u['name'] for u in m['units'] if not inside(u['tile'])]
    gone += [u['name'] for g in m.get('reinforcements', []) for u in g['units'] if not inside(u['tile'])]
    gone += [j['name'] for j in m.get('joiners', []) if not inside(j['tile'])]
    gone += [o['type'] for o in m['objects'] if not inside(o['tile'])]
    if gone:
        print(f"  {m['heading']}: off the playable grid, left out: {', '.join(gone)}")
    m['units'] = [u for u in m['units'] if inside(u['tile'])]
    for g in m.get('reinforcements', []):
        g['units'] = [u for u in g['units'] if inside(u['tile'])]
    m['reinforcements'] = [g for g in m.get('reinforcements', []) if g['units']]
    m['joiners'] = [j for j in m.get('joiners', []) if inside(j['tile'])]
    for k in ('reinforcements', 'joiners'):
        if not m[k]:
            del m[k]
    m['objects'] = [o for o in m['objects'] if inside(o['tile'])]
    m['starts'] = [t for t in m['starts'] if inside(t)]
    for o in m['objectives']:
        o['tiles'] = [t for t in o['tiles'] if inside(t)]
    return cut(m, left, right, bottom, top)


def flag_tests(script, h):
    """The flags a handler tests: [(flag, wanted True/False)]."""
    dis, out = script.disasm(h), []
    for k, (_, op, a) in enumerate(dis[:-2]):
        if op == 'str' and dis[k + 1][1] == 'call' and dis[k + 1][2] == 'get/1':
            out.append((a, not (k + 2 < len(dis) and dis[k + 2][1] == 'op29')))
    return out


def section_number(flag):
    return int(flag[-1].translate(str.maketrans('１２３４', '1234')))


def build_chapter(game, terrain, n, section=None):
    """One chapter's map. `section` (1-4) builds one part of Ch.17, the marathon of four sections."""
    ch = game.chapters[n]
    folder = ch['folder']
    script = Script(f'C{n:02d}.cmb')
    trial = folder.startswith('trial')
    handlers = script.handlers()
    hcalls = {h['i']: calls(script, h) for h in handlers}
    own = {h['i']: calls(script, h, follow=False) for h in handlers}
    # Where units walk: what infantry can enter (not water, which only fliers and pirates cross).
    ground = {k for k, info in terrain.items() if info['move']['Infantry'] is not None}

    # Terrain, with any border of unset tiles trimmed.
    mp = Reloc(map_files(folder, 'map')['map.bin'])
    w, h = struct.unpack_from('>2H', mp.data, 0)

    def panel(x, y):
        idx = struct.unpack_from('>H', mp.data, mp.named['panelindex'] + 2 * (y * w + x))[0]
        return mp.string(mp.named['uniquepanel'] + 12 * idx + 8)

    names = [[strip_digits(panel(x, y)) for x in range(w)] for y in range(h)]
    if n in FOUNTAIN_BEDS:
        names = [['噴水' if c == '花壇' else c for c in row] for row in names]
    top = top_layer(mp, handlers, hcalls)
    after = {}  # (x, y) -> the letter a tile becomes once its model opens or breaks
    for (cx, cy), (start, below, model) in top.items():
        names[cy][cx] = start
        after[(cx, cy)] = LETTERS[below]

    def unset(cells):
        return all(c == '未設定' for c in cells)

    x0 = next(x for x in range(w) if not unset(names[y][x] for y in range(h)))
    x1 = next(x for x in range(w - 1, -1, -1) if not unset(names[y][x] for y in range(h)))
    y0 = next(y for y in range(h) if not unset(names[y]))
    y1 = next(y for y in range(h - 1, -1, -1) if not unset(names[y]))
    W, H = x1 - x0 + 1, y1 - y0 + 1
    grid = [[LETTERS[names[y][x]] for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    # A room under its roof is closed to everyone until a door into it opens.
    rooms = defaultdict(set)
    for (cx, cy), (start, below, model) in top.items():
        if model.startswith(ROOF_MODELS) and x0 <= cx <= x1 and y0 <= cy <= y1:
            grid[cy - y0][cx - x0] = 'Q'
            rooms[model].add((cx, cy))
    # The game's English name for each tile, as the battle starts (the tile panel shows it).
    tile_names = [[game.english.get(names[y][x], names[y][x]) for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    # Heights count from the top layer only where a unit walks it (goal markers, trap lids); a room's floor has its own once open.
    walk_on_top = {c for c in top_layer(mp, handlers, hcalls, cells_only=True) if LETTERS.get(names[c[1]][c[0]]) in ground}
    for cx, cy in ship_stairs(mp, walk_on_top, names):
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            grid[cy - y0][cx - x0] = 'S'
            tile_names[cy - y0][cx - x0] = f"{game.english.get('船', '船')} (stairs)"

    def tile(p):
        return [p[0] - x0 + 1, H - (p[1] - y0)]

    def on_map(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    def rect(ax, ay, bx, by):
        return [tile((ax, by))[0], tile((ax, by))[1], tile((bx, ay))[0], tile((bx, ay))[1]]

    # Blocked sides: the edge table's sides a ground unit can't leave by, between two tiles ground units could otherwise walk
    # (fences, Ch.20's barricades, a bridge's sides), and the steps between two heights (a ship's decks, a terrace's edge).
    # Fliers cross them, except where the table binds them too. The heights' sides first, then the edge table's, which replace
    # a named tile's (main.dol 0x80045604).
    links = {p: (exits, False, True) for p, exits in height_exits(mp, walk_on_top).items()}
    links.update({p: (exits, binds, False) for p, (exits, binds) in edge_masks(mp).items()})
    walls = []

    def walkable(p):
        # A chest stands on the floor it's opened from: a step beside it is drawn too (Ch.13's raised chests: the user).
        return on_map(p) and (grid[p[1] - y0][p[0] - x0] in ground or grid[p[1] - y0][p[0] - x0] == 'c' or after.get(p, '') in ground)
    for (ax, ay), (exits, binds, step) in sorted(links.items()):
        for (dx, dy), bit in EXIT.items():
            b = (ax + dx, ay + dy)
            if exits & bit or not walkable((ax, ay)) or not walkable(b):
                continue
            # One entry per edge: a tile's east or south side.
            here, side = ((ax, ay), {(1, 0): 'e', (0, 1): 's'}.get((dx, dy))) if (dx, dy) in ((1, 0), (0, 1)) else (b, 'e' if dx else 's')
            wall = {'tile': tile(here), 'side': side, **({'all': True} if binds else {}), **({'step': True} if step else {})}
            if not any(x['tile'] == wall['tile'] and x['side'] == side for x in walls):
                walls.append(wall)

    # Tile events: chests, villages, doors and goal tiles.
    objects, objectives = [], []
    destroyable = {(hh['args'][0], hh['args'][1]) for hh in handlers if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 37}
    goal = {13: ('seize', 'Seize'), 14: ('escape', 'Escape'), 41: ('arrive', 'Arrive')}
    goals = defaultdict(list)
    for hh in handlers:
        if hh['kind'] != 5 or len(hh['args']) < 3:
            continue
        x, y, sub = hh['args'][:3]
        got = [a[0] for fn, a in hcalls[hh['i']] if fn == 'MindGetItem' and a]
        gold = [a[0] for fn, a in hcalls[hh['i']] if fn == 'MindGetMoney' and a]
        reward = ', '.join(game.items.get(i, i) for i in got) or (f'{gold[0]} gold' if gold else '')
        if sub == 12:
            objects.append({'type': 'chest', 'tile': tile((x, y)), 'contents': reward})
            if grid[y - y0][x - x0] != 'Q':  # a chest in a closed room stays under the roof until a door opens
                grid[y - y0][x - x0] = 'c'
        elif sub == 9:
            v = {'type': 'village', 'tile': tile((x, y)), 'reward': reward}
            if (x, y) in destroyable:
                v['_raze'] = True  # said once we know who on the map can raze it
            # A village that turns laguz away (Ch.11: Lethe and Mordecai get nothing, and it stays open for someone else).
            fns = [fn for fn, _ in hcalls[hh['i']]]
            turned = [game.people[a[0]]['name'] for fn, a in hcalls[hh['i']]
                      if fn == 'UnitGetByPID' and a and a[0] in ('PID_LETHE', 'PID_MORDY')]
            if turned and 'Comeback' in fns:
                v['note'] = f"{' and '.join(dict.fromkeys(turned))} get nothing here, and it stays open for someone else."
            objects.append(v)
        elif sub == 11:
            grid[y - y0][x - x0] = 'd'
        elif sub in goal:
            goals[sub].append(tile((x, y)))
    for sub, tiles in goals.items():
        objectives.append({'type': goal[sub][0], 'tiles': tiles, 'label': goal[sub][1]})
    for hh in handlers:
        if hh['kind'] == 4 and any(fn == 'set' and a == ['gf_gameover'] for fn, a in hcalls[hh['i']]):
            ax, ay, bx, by = hh['args'][:4]
            objectives.append({'type': 'defend', 'tiles': [tile((x, y)) for x in range(ax, bx + 1) for y in range(ay, by + 1)],
                               'label': 'Defend (the enemy wins by reaching it)'})

    # Hidden items (Ch.15's desert): an area event that rolls (GetRnd) and gives an item. Entering the area
    # gives a (Skill + 1)% chance to dig it up; Thieves and Assassins always find it.
    for hh in handlers:
        got = [a[0] for fn, a in hcalls[hh['i']] if fn == 'MindGetItem' and a]
        if hh['kind'] == 4 and got and any(fn == 'GetRnd' for fn, _ in hcalls[hh['i']]):
            ax, ay, bx, by = hh['args'][:4]
            objects.append({'type': 'hidden', 'tile': tile(((ax + bx) // 2, (ay + by) // 2)), 'area': rect(ax, ay, bx, by),
                            'contents': ', '.join(game.items.get(i, i) for i in got)})
    # A hidden recruit: a one-tile area whose flag lets a later event move someone to your army (Stefan).
    for hh in handlers:
        if hh['kind'] != 4 or hh['args'][:2] != hh['args'][2:4]:
            continue
        flag = next((a[0] for fn, a in hcalls[hh['i']] if fn == 'set' and a), None)
        for other in handlers:
            if other['i'] == hh['i'] or not any(f == flag for f, _ in flag_tests(script, other)):
                continue
            moved = [a[0] for fn, a in hcalls[other['i']] if fn == 'UnitTransferToForceByPID' and a]
            seekers = [game.people[a[0]]['name'] for fn, a in hcalls[other['i']]
                       if fn == 'UnitGetByPID' and a and a[0] in game.people][:2]
            if moved and seekers:
                who = game.people[moved[0]]['name']
                gear = [game.items.get(i, i) for g, us in dispos(folder, 'c').items() for u in us if u['pid'] == moved[0] for i in u['weapons']]
                objects.append({'type': 'hidden', 'tile': tile(hh['args'][:2]), 'area': rect(*hh['args'][:4]),
                                'contents': who + (f" (with the {gear[0]})" if gear else ''),
                                'note': f"Move {' or '.join(seekers)} here first and {who} appears and joins you. "
                                        f"If anyone else steps here first, {who} never comes."})

    pits = []
    # Ballistae (SetShooter: x, y, facing, weapon): a bow user on the tile fires the machine that stands on
    # the next tile in the facing direction. Ch.23's pits (SetPit) are traps in its bridge: the tile reads as
    # a hole in the terrain table, but a ground unit can move onto it, falls in, and waits out the turn
    # (fireemblemwod.com's Ch.23 traps page), so the map shows the bridge it looks like.
    for hh in handlers:
        for fn, a in own[hh['i']]:
            if fn == 'SetShooter' and len(a) == 4 and on_map((a[0], a[1])):
                dx, dy = FACING[a[2]]
                objects.append({'type': 'ballista', 'tile': tile((a[0], a[1])), 'machine': tile((a[0] + dx, a[1] + dy)),
                                'weapon': game.items.get(a[3], a[3])})
            elif fn == 'SetPit' and len(a) == 2 and on_map((a[0], a[1])):
                # A trap lid over a hole: a ground unit that stops on it falls in and waits out the turn, and the hole stays
                # open after (only fliers cross it then).
                t = tile((a[0], a[1]))
                pits.append({'id': f'pit-{t[0]}-{t[1]}', 'trigger': 'trap', 'tile': {'default': t}, 'usableBy': '', 'group': 'pits',
                             'effect': "A hidden pit: a ground unit that stops on it falls in and waits out the turn, and the "
                                       "pit stays open after (a hole only fliers can cross).",
                             'patch': [{'tile': t, 'becomes': after.get((a[0], a[1]), 'x')}]})

    # Breakable doors and walls (SetFragile) and Ch.25's boulders: previewed like Fates' Dragon Veins.
    changes = []

    def room_behind(door):
        """The closed rooms a door opens: those whose roof covers the door's tile, or that it stands beside."""
        dx_, dy_ = door
        near = {(dx_ + ex, dy_ + ey) for ex, ey in EXIT} | {door}
        return [t for cells in rooms.values() if cells & near for t in sorted(cells)]

    def room_patch(door):
        return [{'tile': tile(t), 'becomes': after[t]} for t in room_behind(door)]
    fragile = set()
    for hh in handlers:
        for fn, a in own[hh['i']]:
            if fn == 'SetFragile' and len(a) == 3 and on_map((a[0], a[1])):
                t = tile((a[0], a[1]))
                door = grid[a[1] - y0][a[0] - x0] == 'd'
                fragile.add((a[0], a[1]))
                room = room_patch((a[0], a[1])) if door else []
                changes.append({'id': f'break-{t[0]}-{t[1]}', 'trigger': 'breakable', 'tile': {'default': t},
                                'usableBy': 'Any unit that can attack it',
                                'effect': f'{a[2]} HP. ' + ('A door: open it with a key, or attack it down.' if door
                                                            else 'Attack it down and it becomes open ground.')
                                + (' The room behind it opens.' if room else ''),
                                'patch': [{'tile': t, 'becomes': 'T'}] + room})
    for hh in handlers:
        if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 11 and (hh['args'][0], hh['args'][1]) not in fragile:
            door = (hh['args'][0], hh['args'][1])
            room = room_patch(door) if on_map(door) else []
            if room:
                t = tile(door)
                changes.append({'id': f'door-{t[0]}-{t[1]}', 'trigger': 'event', 'tile': {'default': t}, 'usableBy': '',
                                'effect': 'A locked door: open it with a key or a thief, and the room behind it opens.',
                                'patch': [{'tile': t, 'becomes': 'T'}] + room})
    # A village bandits can raze: its house (the top layer's Building) becomes the ruin under it, which no unit can enter.
    razed = {(a[0], a[1]) for hh in handlers for fn, a in own[hh['i']] if fn == 'BuildDestruction' and len(a) == 2}
    houses = defaultdict(set)
    for (cx, cy), (start, below, model) in top.items():
        if model.startswith(HOUSE_MODELS) and on_map((cx, cy)):
            houses[model].add((cx, cy))
    for model, cells in houses.items():
        hx0, hx1, hy1 = min(c[0] for c in cells), max(c[0] for c in cells), max(c[1] for c in cells)
        visit = next((v for v in sorted(razed) if hx0 <= v[0] <= hx1 and v[1] == hy1 + 1 and on_map(v)), None)
        if visit:
            # Said in the village's note, not previewed (the user's call: a raze is no map change to toggle).
            for o in objects:
                if o['type'] == 'village' and o['tile'] == tile(visit):
                    o['note'] = ((o.get('note') or '') + ' Bandits can raze it: its house becomes ruins no unit can enter.').strip()
    # Rocks (SetRock: the pushing foe's tile, the side it pushes to, and its path's number). The chapter's script spells each path
    # out as numpad steps (TTPMEntry, numbered in call order: main.dol 0x80110048); the rock starts beside the foe and follows its
    # path tile by tile, whatever stands in the way, and breaks on the last tile (0x80129ca8, 0x8012a260, 0x80129fa4).
    rock_paths = [a[0] for hh in handlers for fn, a in own[hh['i']] if fn == 'TTPMEntry' and a and isinstance(a[0], str)]
    rocks = [a for hh in handlers for fn, a in own[hh['i']] if fn == 'SetRock' and len(a) == 4]
    for x, y, facing, k in rocks:
        dx, dy = FACING[facing]
        steps = [(x + dx, y + dy)]
        for c in rock_paths[k]:
            sx, sy = STEP[c]
            steps.append((steps[-1][0] + sx, steps[-1][1] + sy))
        path = [tile(p) for p in steps]
        rock = steps[0]
        changes.append({'id': f'boulder-{k + 1}', 'trigger': 'boulder', 'tile': {'default': path[0]}, 'usableBy': '', 'path': path,
                        **({'patch': [{'tile': path[0], 'becomes': after[rock]}]} if rock in after else {}),
                        'effect': 'The foe behind it pushes it down the marked path. Any unit it rolls over takes 10 damage, '
                                  'whatever its Def, and it breaks on the last tile.'})

    placement = {d: dispos(folder, code) for d, code in DIFFS.items()}
    common = dispos(folder, 'c')
    players = {u['pid'] for src in [common] + list(placement.values()) for g, us in src.items() if 'mikata' in g for u in us} | {'PID_IKE'}

    bonus = ch['level_bonus']

    def load(group_names, diff):
        """The units the script's group names place on one difficulty. A name may be the shared '_c' group,
        one difficulty's own ('_m' Easy's, '_n' Normal's, '_h' Hard's), or a base name the game completes for the
        difficulty being played. The game finds a group by name in any difficulty's records, so a group named alone comes
        on every difficulty that runs the call (Ch.22's turn-5 thief, named by its Hard group, comes on Normal too: the
        user, in the game). Where the script names several copies of one group (the *SetMode helpers' three in
        startup.cmb; an `if (Normal())` pair), the difficulty takes its own copy, Easy falling back on Normal's since
        Normal() is true there (PREFER). Each group counts once however many calls name it. The generic foes gain the
        chapter's level bonus for the difficulty (2 on Easy, up to level 20)."""
        code, picked = DIFFS[diff], set()
        named = set(group_names)
        for a in group_names:
            if a.endswith('_c'):
                picked.add(('c', a))
            elif re.search(r'_[nhm]$', a):
                if a[-1] == next(x for x in PREFER[diff] if f'{a[:-2]}_{x}' in named):
                    picked.add((a[-1], a))
            else:
                picked.add((code, f'{a}_{code}'))
        units = [u for src, g in sorted(picked) for u in (common if src == 'c' else placement[CODE_DIFF[src]]).get(g, [])]
        if bonus.get(diff):
            units = [{**u, 'level': min(20, u['level'] + bonus[diff])} if u['side'] == 1 and u['grown'] else u for u in units]
        return units

    # Talks: who can talk to whom, and whether the talk recruits.
    talks = defaultdict(lambda: {'recruit': [], 'talk': [], 'partner': []})
    for hh in handlers:
        if hh['kind'] != 8 or len(hh['args']) < 2:
            continue
        a, b = (script.string(x) for x in hh['args'][:2])
        # The talk recruits whoever it moves to your army (army 0); one it moves to army 3 becomes a partner unit.
        moved = {x[0] for fn, x in hcalls[hh['i']] if fn == 'UnitTransferToForceByPID' and x and (len(x) < 2 or x[1] == 0)}
        partnered = {x[0] for fn, x in hcalls[hh['i']] if fn == 'UnitTransferToForceByPID' and len(x) == 2 and x[1] == 3}
        for speaker, target in ((a, b), (b, a)):
            if speaker not in game.people:
                continue
            name = game.people[speaker]['name']
            kind = 'recruit' if target in moved else 'partner' if target in partnered else 'talk'
            if name not in talks[target][kind]:
                talks[target][kind].append(name)

    def talk_text(pid):
        t = talks.get(pid)
        if not t:
            return None
        others = [x for x in t['talk'] if x not in t['recruit'] and x not in t['partner']]
        if t['partner']:
            return f"Talk with {' or '.join(t['partner'])}: becomes a partner unit (yellow), fighting beside you but not yet yours"
        if t['recruit']:
            return f"Recruit: talk with {' or '.join(t['recruit'])}" + (f" (also talks with {', '.join(others)})" if others else '')
        return f"Talk with {' or '.join(others)}" if others else None

    # The chapter's own boss: whoever's death wins it (a death handler that sets gf_complete: Muarim in Ch.15, whose record lacks
    # the boss skill). Anyone else with the boss skill (the Black Knight passing through Ch.11 and Ch.24, Bryce beside Ashnard)
    # is a named foe there.
    goal_pids = set()
    for hh in handlers:
        if hh['kind'] == 11 and hh['args'] and any(fn == 'set' and a == ['gf_complete'] for fn, a in hcalls[hh['i']]):
            pid = script.string(hh['args'][0]) if isinstance(hh['args'][0], int) else hh['args'][0]
            goal_pids.add(pid)
    # Exits a unit leaves the map by (tile events of subtype 44): where looters head once they've done their work.
    exits = [(hh['args'][0], hh['args'][1]) for hh in handlers if hh['kind'] == 5 and len(hh['args']) > 2 and hh['args'][2] == 44]

    def to_unit(u, diff_list):
        person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True, 'boss': False})
        cls = game.classes.get(u['jid'], u['jid'])
        boss = (u['pid'] in goal_pids) if goal_pids else (person['boss'] or 'SID_BOSS' in u['skills'])
        if u['side'] in (2, 3):
            kind = 'ally'
        elif boss:
            kind = 'boss'
        elif not person['generic']:
            kind = 'named'
        else:
            kind = 'enemy'
        def named(i):
            return game.items.get(i, i) + (' (from a second playthrough)' if i in u['replay'] else '')
        gear = ', '.join(named(i) for i in u['weapons'] + u['items'])
        unit = {'type': kind, 'name': cls if person['generic'] and kind != 'boss' else person['name'], 'tile': tile(u['at']),
                'note': f"Lv {u.get('level_text', u['level'])} {cls}" + (f': {gear}' if gear else '')}
        if kind == 'ally' and person['generic']:
            unit['generic'] = True  # a plain green dot: the person icon is for named green units
        if u['side'] == 3:
            unit['yellow'] = True  # a partner army (army 3): fights on your side, and you can partly direct it
        if any(a.startswith('SEQ_LOOTERMOVE') for a in u.get('ai', [])):
            unit['looter'] = True
            leaves = any(a == 'SEQ_LOOTERMOVE_ESCAPE' for a in u['ai'])
            unit['note'] += ('. Goes for the chests, then leaves the map by an exit' if leaves and exits
                             else '. Goes for the villages and chests, razing what it reaches')
            if leaves and exits:
                unit['goesTo'] = [tile(e) for e in exits if on_map(e)]
        if u['drops']:
            unit['drops'] = [named(i) for i in u['drops']]
        if talk_text(u['pid']):
            unit['talk'] = talk_text(u['pid'])
        hand = BY_HAND.get(n, {})
        if u['pid'] in hand.get('name', {}):
            unit['name'] = hand['name'][u['pid']]
        if u['pid'] in hand.get('talk', {}):
            unit['talk'] = hand['talk'][u['pid']]
        if u['pid'] in hand.get('note_replace', {}):
            unit['note'] = hand['note_replace'][u['pid']]
        unit['note'] += hand.get('note', {}).get(u['pid'], '')
        if u['pid'] in hand.get('drops', {}):
            unit['drops'] = hand['drops'][u['pid']]
        if u['pid'] in hand.get('escapers', []):
            unit['goesTo'] = [t for o in objectives if o['type'] == 'escape' for t in o['tiles']]
        # What a thief can take that's rare (nothing sells or forges it, and it lasts: a stat booster, a band, a skill scroll, a
        # gem) and the foe doesn't drop. A foe a talk recruits brings its items along.
        if kind != 'ally' and not (unit.get('talk') or '').startswith('Recruit'):
            sold, _, _, _, momentary, _ = steal_rules()
            rare = [named(i) for i in stealable(u) if i not in sold and i not in momentary]
            rare = [x for x in dict.fromkeys(rare) if x not in unit.get('drops', [])]
            if rare:
                unit['steal'] = rare
        if diff_list is not None:
            unit['difficulties'] = diff_list
        return unit

    def merge(per_diff):
        """Each unit once, in Normal's order and then the others': one placed alike on every difficulty unmarked, one on some
        marked with those. A unit that differs between difficulties only by level is one entry with its Normal level and the
        others beside it: 'Lv 4 (Easy 6, Hard 5)'."""
        def same(u):
            return (u['pid'], u['jid'], u['at'], tuple(u['weapons'] + u['items']), tuple(u['drops']))
        # The k-th unit with the same placement on one difficulty is the k-th on another.
        order, slots = [], {}
        for d in ['Normal'] + [x for x in DIFFS if x != 'Normal']:
            seen = Counter()
            for u in per_diff[d]:
                k = (same(u), seen[same(u)])
                seen[same(u)] += 1
                if k not in slots:
                    slots[k] = {}
                    order.append(k)
                slots[k][d] = u
        out = []
        for k in order:
            on = slots[k]
            diffs = [d for d in DIFFS if d in on]
            first = on.get('Normal') or on[diffs[0]]
            others = [f'{d} {on[d]["level"]}' for d in diffs if on[d]['level'] != first['level']]
            u = {**first, 'level_text': f"{first['level']} ({', '.join(others)})"} if others else first
            out.append((u, None if len(diffs) == len(DIFFS) else diffs))
        return out

    # Who starts on the map: the groups the setup handler places (FinalDisposition, or a Ch.17 section's
    # own opening), minus anyone the openings send away (Nasir in Ch.11), and only the "if X is alive"
    # side of a choice (Gatrie, rather than the Begnion soldier on his tile, in Ch.13).
    scene = set_down = False
    if section and section > 1:
        setup = next(hh for hh in handlers if hh['name'] == f'Opening18_{section}')
    else:
        setup = next((hh for hh in handlers if hh['name'] == 'FinalDisposition'), None)
        scene = not setup
        if not setup:
            # The prologue has no prep screen: its opening handler places everyone.
            setup = next(hh for hh in handlers if any(fn == 'MapLoad' and a == [folder] for fn, a in hcalls[hh['i']]))
    dis = script.disasm(setup)
    branch = {}  # pc -> ('then' | 'else', PID tested)
    for k, (pc, op, a) in enumerate(dis[:-2]):
        if op == 'str' and dis[k + 1][2] == 'UnitCheckLiveByPID/1' and dis[k + 2][1] == 'jz':
            else_at = dis[k + 2][2]
            jmp = next((x for x in dis if x[1] == 'jmp' and pc < x[0] < else_at), None)
            for pc2, _, _ in dis:
                if pc < pc2 < else_at:
                    branch[pc2] = ('then', a)
                elif jmp and else_at <= pc2 < jmp[2]:
                    branch[pc2] = ('else', a)
    start_groups, if_alive, instead_groups, stack = set(), {}, [], []
    for pc, op, a in dis:
        if op in ('str', 'int'):
            stack.append(a)
        elif op == 'call':
            fn, argc = a.split('/')
            argc = int(argc)
            args = stack[len(stack) - argc:] if argc else []
            del stack[len(stack) - argc:]
            if fn not in DISPOS_CALLS:
                continue
            for g in args:
                if not (isinstance(g, str) and g.startswith(folder + '_')) or 'mikata' in g:
                    continue
                # Placed by the opening cutscene: its 'event' groups are only in the scene (Ena in Ch.27-2).
                if scene and '_event_' in g:
                    continue
                side = branch.get(pc)
                if side and side[0] == 'else':
                    instead_groups.append(g)
                    continue
                start_groups.add(g)
                if side:
                    if_alive[g] = side[1]
    if section and section > 1:
        sent_away = {a[0] for fn, a in hcalls[setup['i']] if fn == 'UnitEscapeByPID' and a}
    else:
        sent_away = {a[0] for hh in handlers if hh['name'] == 'FinalDisposition' or (hh['name'].startswith('Opening') and not section)
                     for fn, a in hcalls[hh['i']] if fn == 'UnitEscapeByPID' and a}

    # A map with no prep screen whose opening scene isn't cleared away before the battle (the Prologue): the
    # units it places end the scene wherever it walks them, and that's where they stand when the battle starts.
    staged = {}
    cleared = any(fn == 'AllUnitEscape' for hh in handlers if hh['name'].startswith('Opening') for fn, _ in hcalls[hh['i']])
    if scene and not cleared:
        # Only someone placed once can be told apart by the scene (not one of many generic soldiers).
        placed = Counter(u['pid'] for u in load(start_groups, 'Normal'))
        pos = {u['pid']: u['at'] for d in DIFFS for u in load(start_groups, d) if placed[u['pid']] == 1}
        moved = set()
        for fn, a in hcalls[setup['i']]:
            if fn == 'UnitSetPosDirByPID' and len(a) == 4 and isinstance(a[1], int) and a[0] in pos:
                pos[a[0]] = (a[1], a[2])
                moved.add(a[0])
            elif fn == 'UnitMoveDirByPID' and len(a) == 2 and a[0] in pos and isinstance(a[1], str):
                x, y = pos[a[0]]
                for c in a[1]:
                    dx, dy = STEP.get(c, (0, 0))
                    x, y = x + dx, y + dy
                pos[a[0]] = (x, y)
                moved.add(a[0])
        staged = {pid: p for pid, p in pos.items() if pid in moved}

    def starting(d):
        out, seen = [], set()
        for u in load(start_groups, d):
            if u['pid'] in staged:
                u = {**u, 'at': staged[u['pid']]}
            # Your own units come from the deployment slots; someone on your roster can still start as an
            # enemy (Shinon in Ch.18).
            if not on_map(u['at']) or u['side'] == 0 or u['pid'] in sent_away or (u['pid'] in players and u['side'] != 1):
                continue
            if u['pid'] in seen and not game.people.get(u['pid'], {}).get('generic', True):
                continue  # the same character placed twice (Ena in Ch.27-2)
            seen.add(u['pid'])
            out.append(u)
        return out

    # Ike carries Leanne through Ch.17's last two sections (he can't drop her or hand her over), so she
    # isn't a unit on the map there.
    carried = section and section >= 3

    watching = WATCHING.get(n, {})

    def shown(d):
        return [u for u in starting(d) if not (carried and u['pid'].startswith('PID_LEARNE')) and u['pid'] not in watching]

    merged = merge({d: shown(d) for d in DIFFS})
    units = [to_unit(u, dl) for u, dl in merged]
    if if_alive:
        cond_pids = {u['pid'] for g in if_alive for u in load([g], 'Normal')}
        alive = ' and '.join(sorted({game.people[p]['name'] for p in if_alive.values()}))
        instead = ', '.join(sorted({to_unit(u, None)['name'] for u in load(instead_groups, 'Normal')})) or 'no one'
        instead_units = [to_unit(u, None) for u in load(instead_groups, 'Normal')]
        for unit, (raw, _) in zip(units, merged):
            if raw['pid'] in cond_pids:
                stand = next((x for x in instead_units if x['tile'] == unit['tile']), None)
                if stand:
                    # Placed only when the character is gone (died earlier): the map's stand-in toggle swaps it in.
                    unit['standIn'] = {k: stand[k] for k in ('type', 'name', 'note', 'generic', 'drops', 'steal') if k in stand}
                else:
                    unit['note'] += f' (only if {alive} is still alive)'

    # Your deployment slots: the mikata_c group (Ike's slot is the lord's start). A Ch.17 section after the
    # first keeps your army where it stood; its opening moves Ike and a few others into place.
    if section and section > 1:
        pos = {}
        for fn, a in hcalls[setup['i']]:
            if fn == 'UnitSetPosDirByPID' and len(a) == 4 and a[0] in players and isinstance(a[1], int):
                pos[a[0]] = (a[1], a[2])
            elif fn == 'UnitMoveDirByPID' and len(a) == 2 and a[0] in pos and isinstance(a[1], str):
                x, y = pos[a[0]]
                for c in a[1]:
                    dx, dy = STEP.get(c, (0, 0))
                    x, y = x + dx, y + dy
                pos[a[0]] = (x, y)
            elif fn == 'UnitEscapeByPID' and a and a[0] in pos:
                del pos[a[0]]
        roster = roster_places(script, setup)
        starts = [tile(p) for p in list(pos.values()) + list(roster.values()) if on_map(p)]
        starts = [t for i, t in enumerate(starts) if t not in starts[:i]]
        lord = tile(pos['PID_IKE']) if 'PID_IKE' in pos and on_map(pos['PID_IKE']) else None
    else:
        slots = [u for u in common.get(f'{folder}_mikata_c', []) if on_map(u['at'])]
        # No prep screen: the opening clears the scene and sets your units down itself (Ike and Mist in Ch.27-2).
        set_down = scene and any(fn == 'InstantDisposSetMode' and f'{folder}_mikata_n' in a for hh in handlers
                       if hh['name'].startswith('Opening') for fn, a in hcalls[hh['i']])
        if set_down:
            slots = []
        if not slots:
            slots = [u for u in placement['Normal'].get(f'{folder}_mikata_n', []) if on_map(u['at'])]
        starts = [tile(u['at']) for u in slots]
        lord = next((tile(u['at']) for u in slots if u['pid'] == 'PID_IKE'), None)
    # Units the game sets on a tile of its own choosing, beside Ike.
    fixed = [] if section or not set_down else [
        {'name': game.people[u['pid']]['name'], 'tile': tile(u['at'])} for u in slots if u['pid'] != 'PID_IKE' and u['pid'] in game.people]
    forced = [] if section and section > 1 else sorted({
        game.people[a[0]]['name'] for hh in handlers for fn, a in hcalls[hh['i']]
        if fn == 'UnitForcedSallyByPID' and a and a[0] in game.people and a[0] != 'PID_IKE'})

    # Flags set by area triggers: {flag: [area]}; and by turn handlers: {flag: text}.
    flag_areas, flag_turns = defaultdict(list), {}
    for hh in handlers:
        for fn, a in hcalls[hh['i']]:
            if fn != 'set' or not a or not isinstance(a[0], str):
                continue
            if hh['kind'] == 4:
                ax, ay, bx, by, who = hh['args'][:5]
                flag_areas[a[0]].append({'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)})
            elif hh['kind'] == 3 and hh['args'] and hh['args'][0]:
                flag_turns[a[0]] = hh['args']

    def when(hh):
        """The handler's trigger as a sentence (per difficulty when it differs), plus any areas."""
        if hh['kind'] == 4:
            ax, ay, bx, by, who = hh['args'][:5]
            return 'When a unit enters the marked area', [{'who': 'enemy' if who == 1 else 'player', 'rect': rect(ax, ay, bx, by)}]
        if hh['kind'] != 3:
            return None, []
        first, last_, phase = (list(hh['args']) + [0, 0, 0])[:3]
        per = difficulty_turns(script, hh)
        ph = PHASE.get(phase, 'turn start')
        if per and len(set(per.values())) > 1:
            return {d: f'Turn {t}, {ph}' for d, t in per.items()}, []
        if per:
            return f'Turn {next(iter(per.values()))}, {ph}', []
        if first:
            # A range fires every turn in it unless the handler marks itself done.
            once = any(fn == 'set' for fn, _ in calls(script, hh))
            return (f'Turn {first}, {ph}' if first == last_ else f"Turns {first}–{last_}, {ph}{'' if once else ', each turn'}"), []
        # Every turn, once a flag is set: by entering an area, or by an earlier turn.
        for f, _ in flag_tests(script, hh):
            if f in flag_areas:
                who = 'an enemy enters' if any(x['who'] == 'enemy' for x in flag_areas[f]) else 'one of your units enters'
                side = {0: 'player', 1: 'enemy', 2: 'ally'}.get(phase, 'player')
                return f"At the start of the next {side} phase after {who} the marked area", flag_areas[f]
            if f in flag_turns:
                ts, _, tp = (list(flag_turns[f]) + [0, 0, 0])[:3]
                return f'Turn {ts}, {PHASE.get(tp, "turn start")}', []
        return 'When an event in the chapter sets it off', []

    # Flags a door sets when it's opened (tile event 11), and which group each door lets in: a handler that
    # tests a door's flag and then places a group.
    door_flags = {}
    for hh in handlers:
        if hh['kind'] == 5 and len(hh['args']) >= 3 and hh['args'][2] == 11:
            for fn, a in hcalls[hh['i']]:
                if fn == 'set' and a and not re.fullmatch(r'F\d+', a[0]):
                    m_ = re.fullmatch(r'扉(左|右)(上|下)', a[0])
                    name = f"{'top' if m_.group(2) == '上' else 'bottom'}-{'left' if m_.group(1) == '左' else 'right'} door" if m_ else 'door'
                    door_flags[a[0]] = (name, (hh['args'][0], hh['args'][1]))
    door_gates = {}
    for hh in handlers:
        current = None
        for fn, a in hcalls[hh['i']]:
            if fn == 'get' and a and a[0] in door_flags:
                current = door_flags[a[0]]
            elif fn in DISPOS_CALLS and current:
                for g_ in a:
                    if isinstance(g_, str):
                        door_gates.setdefault(hh['i'], {})[g_] = current

    def section_of(hh):
        """Which of Ch.17's sections a handler belongs to, from the flags it tests."""
        tests = flag_tests(script, hh)
        for f, _ in tests:
            m_ = re.match(r'S(\d)増援', f)
            if m_:
                return int(m_.group(1))
        on = [section_number(f) for f, want in tests if f.startswith('セクション') and want]
        off = [section_number(f) for f, want in tests if f.startswith('セクション') and not want]
        if on:
            return max(on)
        if off:
            return min(off) - 1
        # No section flag: whichever section's grid its units land in (the hawks in section 4).
        return None

    reinforcements, joiners, seen = [], [], set()
    for hh in handlers:
        # Not the opening (who starts), the chapter end, or cutscenes on another map.
        if hh['name'] == 'FinalDisposition' or hh['name'].startswith('Opening') or hh['kind'] == 1:
            continue
        if any(fn == 'MapLoad' for fn, _ in hcalls[hh['i']]):
            continue
        # One handler brings every section's ally reinforcements; each section takes its own group from it.
        own_allies = section and any(f'mikata_zoen_{section:02d}' in str(a) for _, a in hcalls[hh['i']])
        if section and section_of(hh) not in (section, None) and not own_allies:
            continue
        here = calls_by_difficulty(script, hh)
        # A cutscene places its own 'event' groups; anything else it places is part of the scene too.
        if hh['kind'] == 0 and any('event' in a for fn, args, _ in here if fn in DISPOS_CALLS for a in args if isinstance(a, str)):
            continue

        def by_place(fn, args, alive):
            """The groups a call places, each with the difficulties it does so on. The *SetMode helpers (startup.cmb) take theirs
            by place, not by name: NormalOnly() never holds on this disc, so Easy and Normal take the third and Hard the second
            (Ch.28's turn-8 call names z03_n, z04_h, z03_m; Ch.24's names z01_h, z01_h, z01_m)."""
            if fn.endswith('SetMode') and len(args) == 3 and all(isinstance(a, str) for a in args):
                return [(args[1], alive & {'Hard'}), (args[2], alive & {'Easy', 'Normal'})]
            return [(a, alive) for a in args]
        # An 'event' group a turn or area brings in can be a real arrival (Jill in Ch.11)...
        loaded = [(a, ds) for fn, args, alive in here if fn in DISPOS_CALLS for a, ds in by_place(fn, args, alive)
                  if isinstance(a, str) and a.startswith(folder + '_') and ('event' not in a or hh['kind'] in (3, 4))]
        # ...but only alongside the reinforcement group it belongs to (event_jill with z_jill), not a
        # walk-on in a scene (Petrine in Ch.7).
        plain = [a for a, _ in loaded if 'event' not in a]
        loaded = [(a, alive) for a, alive in loaded if 'event' not in a or any(a.split('event_')[1].removesuffix('_c') in p for p in plain)]
        # A starting group the opening sent away can come back later (Haar and his wyverns in Ch.23).
        on_map_at_start = {g for g in start_groups if any(u['pid'] not in sent_away for d in DIFFS for u in load([g], d))}
        if not loaded or {a for a, _ in loaded} <= on_map_at_start:
            continue
        for base in sorted({re.sub(r'_[nhm]$', '', a) for a, _ in loaded if a not in on_map_at_start}):
            group_names = [a for a, _ in loaded if re.sub(r'_[nhm]$', '', a) == base]
            text, areas = when(hh)
            # One handler, several doors: each group comes when its own door opens (Trial 5).
            gate = next((door_gates[hh['i']][a] for a in group_names if a in door_gates.get(hh['i'], {})), None)
            if gate:
                text, areas = f"After the {gate[0]} is opened", [{'who': 'player', 'rect': rect(*gate[1], *gate[1])}]
            if 'mikata' in base:
                # Ch.17's ally reinforcements: units you pick join you shortly into the section.
                if section and base.endswith(f'_{section:02d}_c'):
                    for u in load(group_names, 'Normal'):
                        if on_map(u['at']):
                            joiners.append({'name': 'A unit you choose', 'tile': tile(u['at']), 'from': tile(u['from']),
                                            'group': 'Ally reinforcements',
                                            'when': "Turn 3 of the section, start of the player phase (you pick who comes)"})
                continue
            per = {d: [u for u in load([a for a, alive in loaded if re.sub(r'_[nhm]$', '', a) == base and d in alive], d)
                       if u['side'] == 1] for d in DIFFS}
            # Units that arrive on your side: your own (Gatrie and Shinon in Ch.7 join you), a new recruit still
            # to talk to (Marcia in Ch.3), or another army fighting alongside you. Not anyone the same event
            # sends off again (Greil, who comes and goes in Ch.7).
            leaving = {a[0] for fn, a in hcalls[hh['i']] if fn == 'UnitEscapeByPID' and a}
            for u in load(group_names, 'Normal'):
                if u['side'] in (0, 2, 3) and on_map(u['at']) and u['pid'] not in leaving and (u['side'] == 0 or u['pid'] not in players):
                    person = game.people.get(u['pid'], {'name': u['pid'], 'generic': True})
                    j = {'name': game.classes.get(u['jid'], u['jid']) if person['generic'] else person['name'], 'tile': tile(u['at']),
                         'from': tile(u['from']), 'group': base[len(folder) + 1:]}
                    if u['side'] != 0:
                        j['ally'] = True
                        if person['generic']:
                            j['generic'] = True
                    j['when'] = (text if isinstance(text, str) else text.get('Normal')) if text else 'When an event in the chapter sets it off'
                    if areas:
                        j['areas'] = copy.deepcopy(areas)
                    if talk_text(u['pid']):
                        j['talk'] = talk_text(u['pid'])
                    joiners.append(j)
            if not any(per.values()):
                continue
            bosses = {u['name'] for u in units if u['type'] == 'boss'}
            later = [to_unit(u, None)['name'] for d in DIFFS for u in per[d]]
            if later and all(name in bosses for name in later):
                # The same boss again (Ashnard's second form, after the first is beaten).
                text = f'After {later[0]} is first defeated (a second form)'
            if (base, json.dumps(text)) in seen:
                continue
            seen.add((base, json.dumps(text)))
            us = []
            for u, dl in merge(per):
                unit = to_unit(u, dl)
                if u['from'] != u['at']:
                    unit['from'] = tile(u['from'])
                us.append(unit)
            group = {'id': f"{base}-{hh['i']}", 'label': '', 'units': us}
            if text:
                group['when'] = text
            if areas:
                group['areas'] = copy.deepcopy(areas)
            reinforcements.append(group)
    # Someone the script hands to the enemy and walks onto the map once a unit falls (Greil, after Boyd, in
    # the Prologue); the one who fell steps aside on your side.
    deaths = {}
    for hh in handlers:
        if hh['kind'] == 11 and hh['args']:
            pid = script.string(hh['args'][0]) if isinstance(hh['args'][0], int) else hh['args'][0]
            for fn, a in hcalls[hh['i']]:
                if fn == 'set' and a:
                    deaths[a[0]] = pid
    for hh in handlers:
        fallen_pid = next((deaths[f] for f, want in flag_tests(script, hh) if want and f in deaths), None)
        fallen = game.people.get(fallen_pid, {}).get('name', fallen_pid) if fallen_pid else None
        cs = hcalls[hh['i']]
        for k, (fn, a) in enumerate(cs):
            if fn != 'UnitTransferToForceByPID' or len(a) != 2 or not fallen:
                continue
            move = next((b for f2, b in cs[k + 1:] if f2 == 'UnitMovePosByPID' and len(b) == 3 and b[0] == a[0] and isinstance(b[1], int)), None)
            raw = next((u for u in load(start_groups, 'Normal') if u['pid'] == a[0]), None)
            if not raw:
                continue
            if a[1] == 1 and move:
                u = {**raw, 'side': 1, 'from': staged.get(a[0], raw['at']), 'at': (move[1], move[2])}
                unit = to_unit(u, None)
                if unit['type'] in ('enemy', 'named') and ch['win'] == 'Defeat boss' and not any(x['type'] == 'boss' for x in units):
                    unit['type'] = 'boss'
                unit['from'] = tile(u['from'])
                reinforcements.append({'id': f"{a[0].lower()}-{hh['i']}", 'label': '', 'units': [unit], 'when': f'Once {fallen} is beaten'})
            elif a[1] == 2 and a[0] == fallen_pid:
                for unit, (raw_, _) in zip(units, merged):
                    if raw_['pid'] == fallen_pid:
                        unit['note'] += f'. Once beaten, {fallen} turns green and steps aside.'

    reinforcements = one_per_arrival(reinforcements)
    # Who can raze a village: only looters go for them (SEQ_LOOTERMOVE), on the map at the start or arriving later.
    looters = sorted({u['name'] for u in units + [x for g in reinforcements for x in g['units']] if u.get('looter')})
    for o in objects:
        if o.pop('_raze', False) and looters:
            raze = f"{' or '.join(looters)} can raze it before you visit."
            o['note'] = f"{raze} {o['note']}" if o.get('note') else raze
    hand = BY_HAND.get(n, {})
    for g in reinforcements:
        base = g['id'].rpartition('-')[0]
        if base in hand.get('when', {}):
            g['when'] = hand['when'][base]
    for j in joiners:
        j['when'] = j.get('when', '') + hand.get('joiner_when', {}).get(j['name'], '')
        if j['name'] in hand.get('joiner_talk', {}):
            j['talk'] = hand['joiner_talk'][j['name']]
        if j['name'] in hand.get('joiner_note', {}):
            j['note'] = hand['joiner_note'][j['name']]
    # A boss who only passes through (the Black Knight in Ch.11 and Ch.24) is a named foe there: the skull is for the chapter's
    # own boss. The same boss coming back (Ashnard's second form) keeps it.
    start_bosses = {u['name'] for u in units if u['type'] == 'boss'}
    for g in reinforcements:
        for u in g['units']:
            if u['type'] == 'boss' and start_bosses and u['name'] not in start_bosses:
                u['type'] = 'named'
    # A defend chapter ends after its last turn: a group timed after that never comes (Ch.8's turn 9).
    # So does one won within a turn limit (Trial 4), going by the longest limit (Easy's, when it has more).
    limit = re.match(r'(?:Defend|Survive) for (\d+) turns|Arrive \d+ turns', ch['win'] or '')
    if limit:
        last_turn = max(int(t) for t in re.findall(r'(\d+)', f"{ch['win']} {ch.get('hard_win') or ''}"))
        reinforcements = [g for g in reinforcements
                          if not (isinstance(g.get('when'), str) and (m_ := re.match(r'Turns? (\d+)', g['when']))
                                  and int(m_.group(1)) > last_turn)]
    for i, g in enumerate(reinforcements):
        g['label'] = f'Group {i + 1}'

    title = ch['title'].split(': ', 1)[1] if ': ' in ch['title'] else ch['title']
    # Goals the script sets later (BMSetTerm slot 0, in its sections' order), and an extra loss it clears (slot 3).
    terms = sorted(((hh['name'], a) for hh in handlers for fn, a in hcalls[hh['i']] if fn == 'BMSetTerm' and len(a) == 2), key=lambda x: x[0])
    later_goals = [game.text.get(a[1], a[1]) for _, a in terms if a[0] == 0]
    if section:
        ch = {**ch, 'win': ([ch['win']] + later_goals)[section - 1]}
        later_goals = []
    win, lose = goal_text(ch, units, later_goals, any(a[0] == 3 and a[1] == 'MW_空' for _, a in terms))
    win = BY_HAND.get(n, {}).get('victory', win)
    goal_words = ' '.join([win] + later_goals).lower()
    objectives = [o for o in objectives if o['type'] == 'defend' or o['type'] in goal_words]
    heading = f'Trial {n - 90}' if trial else ch['title'].split(':')[0] + (f'-{section}' if section else '')
    notes = []
    for g in reinforcements:
        for u in g['units']:
            if u['type'] == 'boss' and 'first defeated' not in str(g.get('when', '')):
                w_ = g.get('when')
                w_ = w_ if isinstance(w_, str) else '; '.join(f'{k}: {v}' for k, v in (w_ or {}).items())
                notes.append(f"{u['name']} isn't on the map at the start: arrives with {g['label']} "
                             f"({w_[0].lower() + w_[1:] if w_ else 'when the script sets it off'}).")
    if section and section > 1:
        notes.append('Your units carry over from the last section: the opening sets them down on the marked tiles, '
                     'Ike on his own.')
    notes += watching.values()
    notes += BY_HAND.get(n, {}).get('notes', [])
    if carried:
        notes.append("Ike carries Leanne the whole section: he takes the rescue penalties and can't drop her or hand "
                     "her to anyone, so she isn't on the map.")
    # The same arrival placed by two handlers (one per difficulty) counts once.
    joiners = [j for i, j in enumerate(joiners) if not any((k['name'], k['tile']) == (j['name'], j['tile']) for k in joiners[:i])]
    # A hidden recruit's arrival happens when the right unit finds the spot.
    for o in objects:
        if o['type'] == 'hidden' and 'note' in o:
            for j in joiners:
                if o['contents'].startswith(j['name']):
                    j['when'] = f"When {o['note'].split(' here')[0].removeprefix('Move ')} reaches the hidden spot"
    m = {
        'id': f'fe9-{heading.lower().replace("ch.", "").replace(" ", "")}',
        'route': 'Trial' if trial else 'Story', 'chapter': n - 1, 'heading': heading,
        'title': title,
        'width': W, 'height': H,
        # Ch.17's ruins: what the files call building is rubble there (fliers only, as before).
        'grid': [''.join('r' if c in 'B%7+' else c for c in r) if section else ''.join(r) for r in grid],
        'victory': win, 'defeat': lose, 'objectives': objectives, 'units': units, 'starts': starts,
        'objects': objects, 'changes': changes, 'notes': ([TRIAL_OPENS[n]] if n in TRIAL_OPENS else []) + notes,
    }
    if walls:
        m['walls'] = walls
    # Each prop tile's look, from the model on it.
    on = models_on(mp)
    props = {f'{tile(p)[0]},{tile(p)[1]}': k for p in ((x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))
             if names[p[1]][p[0]] == '小物' and (k := prop_kind(on.get(p, [])))}
    if props:
        m['props'] = props
    m['changes'] += pits
    # Fog of war (SetSight(1, ...), here in a function the opening calls), on the difficulties that reach it: Ch.5 on Hard.
    fogged = {d for hh in handlers for fn, a, ds in calls_by_difficulty(script, hh) if fn == 'SetSight' and a and a[0] == 1 for d in ds}
    if fogged:
        shown_diffs = [d for d in DIFFS if d in fogged]
        if len(shown_diffs) == len(DIFFS):
            m['fog'] = True
        else:
            m['fogOn'] = shown_diffs
            m['notes'].append(f"Fog of war on {' and '.join(shown_diffs)} only.")
        # The army's sight at the start: SetSight's second argument (Ch.5's 3).
        m['vision'] = max(a[1] for hh in handlers for fn, a, ds in calls_by_difficulty(script, hh)
                          if fn == 'SetSight' and len(a) > 1 and a[0] == 1)
    m['_names'] = tile_names
    if lord:
        m['corrinStart'] = lord
    if forced or fixed:
        m['forced'] = [{'name': f} for f in forced] + fixed
    # Units an opening places after preparations and hands to your army (Mist and Rolf in Ch.9): set down by the game.
    for hh in handlers:
        if not hh['name'].startswith('Opening') or hh['name'] == 'Opening0':
            continue
        handed = {a[0] for fn, a in hcalls[hh['i']] if fn == 'UnitTransferToForceByPID' and len(a) == 2 and a[1] == 0}
        for fn, a in hcalls[hh['i']]:
            if fn not in DISPOS_CALLS:
                continue
            for g_ in a:
                for u in common.get(g_, []) if isinstance(g_, str) else []:
                    if u['pid'] in handed and on_map(u['at']) and u['pid'] in game.people:
                        entry = {'name': game.people[u['pid']]['name'], 'tile': tile(u['at'])}
                        if entry not in m.get('forced', []):
                            m.setdefault('forced', []).append(entry)
    if reinforcements:
        m['reinforcements'] = reinforcements
    if joiners:
        m['joiners'] = joiners
    gx0, gx1, gy0, gy1 = PLAYABLE[(n, section)] if section else border(mp)
    m = crop_to(m, gx0 - x0 + 1, gx1 - x0 + 1, H - (gy1 - y0), H - (gy0 - y0))
    # A blocked side that faces off the cropped map blocks nothing on it (Ch.17-2's wall to section 1).
    out = {'s': lambda t: t[1] == 1, 'n': lambda t: t[1] == m['height'], 'e': lambda t: t[0] == m['width'], 'w': lambda t: t[0] == 1}
    if 'walls' in m:
        m['walls'] = [w_ for w_ in m['walls'] if not out[w_['side']](w_['tile'])]
        if not m['walls']:
            del m['walls']
    return with_tile_names(m, game)


def one_per_arrival(groups):
    """One group per arrival. A group a caller and its callee both place is said once (Ch.10's alarm); the groups one handler
    places at one time are one arrival (Jill and her Wyvern Riders in Ch.11); and one group the files place on each difficulty by
    a handler of its own, at different times, is one group whose time differs by difficulty (Ch.7's thief)."""
    def units_key(g):
        return json.dumps(sorted((u['name'], u['tile'], u.get('note'), u.get('difficulties')) for u in g['units']))

    def vague(w):
        return w is None or 'sets it off' in str(w)
    kept = []
    for g in groups:
        # The same group, the same units, placed by a handler and again by the one calling it (only one of them can say when).
        dup = next((o for o in kept if o['id'].rpartition('-')[0] == g['id'].rpartition('-')[0] and units_key(o) == units_key(g)
                    and (o.get('when') == g.get('when') or vague(o.get('when')) or vague(g.get('when')))), None)
        if dup:
            if vague(dup.get('when')) and not vague(g.get('when')):
                dup['when'], dup['id'] = g.get('when'), g['id']
            continue
        kept.append(g)
    out = []
    for g in kept:
        base, _, handler = g['id'].rpartition('-')
        # Placed by the same handler at the same time as another group: one arrival.
        same = next((o for o in out if o['id'].rpartition('-')[2] == handler and o.get('when') == g.get('when')
                     and o.get('areas') == g.get('areas')), None)
        if same:
            same['units'] += g['units']
            continue
        # The same group on the other difficulty, at another time.
        def diffs(gr):
            return {d for u in gr['units'] for d in (u.get('difficulties') or DIFFS)}
        twin = next((o for o in out if o['id'].rpartition('-')[0] == base and not (diffs(o) & diffs(g))
                     and isinstance(o.get('when'), str) and isinstance(g.get('when'), str)), None)
        if twin:
            when = {d: twin['when'] for d in diffs(twin)}
            when.update({d: g['when'] for d in diffs(g)})
            twin['when'] = {d: when[d] for d in DIFFS if d in when}
            twin['units'] += g['units']
            continue
        out.append(g)
    return out


def roster_places(script, h, depth=0):
    """Where a Ch.17 section's opening sets each place in your army down: {place: (x, y)}. The opening switches on the place
    ('var 09; int K; op2f; jz') and sets that unit on a tile, sometimes walking it on to another (UnitSetPos, UnitMovePos: the
    last two literals are the tile). Calls into other handlers are followed."""
    dis = script.disasm(h)
    out, place = {}, None
    for k, (pc, op, a) in enumerate(dis):
        if op == 'stmt' and depth < 8:
            callee = handler_at(script, int(a, 16))
            if callee and callee['i'] != h['i']:
                out.update(roster_places(script, callee, depth + 1))
        elif op == 'int' and k + 2 < len(dis) and dis[k + 1][1] == 'op2f' and dis[k + 2][1] == 'jz' and k and dis[k - 1][1] == 'var':
            place = a
        elif op == 'call' and a in ('UnitSetPos/3', 'UnitMovePos/3') and place is not None and dis[k - 1][1] == 'int' and dis[k - 2][1] == 'int':
            out[place] = (dis[k - 2][2], dis[k - 1][2])
    return out


def with_tile_names(m, game):
    """Each code's names on this map, as the game names its tiles: the most common first, then the tiles with each other
    name ('Plain / Snow field'), so the legend and the tile panel say what the game says."""
    names = m.pop('_names')
    by_letter = defaultdict(lambda: defaultdict(list))
    H = m['height']
    for r, row in enumerate(m['grid']):
        for c, letter in enumerate(row):
            by_letter[letter][names[r][c]].append([c + 1, H - r])
    over = {}
    for letter, found in by_letter.items():
        order = sorted(found, key=lambda k: -len(found[k]))
        if letter == 'Q':
            continue  # a closed room: the game calls it a roof; the terrain's own name says what it does
        if len(order) == 1 and order[0] == LETTER_NAMES.get(letter):
            continue
        over[encode('fe9', letter)] = {'name': ' / '.join(order), **({'tileNames': {k: found[k] for k in order[1:]}} if len(order) > 1 else {})}
    if over:
        m['terrainOverrides'] = over
    return m



def sandy_map(m):
    """A built (not yet encoded) map with more sand than grass or snow drawn in sandstone (the user's call: a sandy ruin reads tan):
    its castle walls sandstone, its floors and paving their sandy colours."""
    letters = [c for row in m['grid'] for c in row]
    sand = sum(letters.count(c) for c in 's*')
    if sand <= sum(letters.count(c) for c in 'GZ'):
        return m
    m['grid'] = [row.replace('0', '5') for row in m['grid']]
    for c in m.get('changes', []):
        for p in c.get('patch', []):
            if p['becomes'] == '0':
                p['becomes'] = '5'
    m['fills'] = {**m.get('fills', {}), 't1': '#c8b48c', 't4': '#c2ad86'}
    return m

# Towns whose plain is drawn as a town's ground (the game calls every walkable tile of these maps plain): Port Toha (Ch.11),
# whose minimap (Fire Emblem Wiki) shows tan ground with grass among it, as mossy cobbles (the user's call: a town of grass and
# stone). Pirates Aground's port is grass and dirt inside its walls (the user, against the paving it had).
PAVED = {'fe9-11': '`'}


def paved_town(m):
    """A town map's plain drawn as its town's ground (PAVED): the same stats, its own look."""
    letter = PAVED.get(m['id'])
    if letter:
        m['grid'] = [row.replace('G', letter) for row in m['grid']]
        for c in m.get('changes', []):
            for p in c.get('patch', []):
                if p['becomes'] == 'G':
                    p['becomes'] = letter
    return m


# Buildings the 3D map shows as market stalls, which the game calls Building like the houses (the user, from the game's map):
# drawn as stalls, with the building's stats. App coordinates.
STALLS = {
    'fe9-11': [(3, 14), (3, 17), (4, 17), (5, 17), (6, 17), (6, 18), (10, 15), (11, 15)],
}
# Flowerbeds (花壇) the user saw as fountains in the game: the Endgame's four 4 x 4 basins and its two top rows of three 2 x 2.
FOUNTAIN_BEDS = {31}


def stall_fixes(m, terrain):
    """An encoded map's buildings that are market stalls (STALLS) as stalls (`o6`, placed along their rows by map_pieces.town)."""
    tiles = STALLS.get(m['id'], [])
    if not tiles:
        return m
    rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
    for x, y in tiles:
        if rows[m['height'] - y][x - 1] != 'w8':
            raise SystemExit(f"{m['id']}: ({x}, {y}) is {rows[m['height'] - y][x - 1]}, not a building")
        rows[m['height'] - y][x - 1] = 'o6'
    m['grid'] = [''.join(r) for r in rows]
    terrain.setdefault('o6', {**terrain['w8'], 'name': 'Market stall (a building)'})
    over = m.setdefault('terrainOverrides', {})
    if 'w8' in over:
        over['o6'] = over['w8']
    return m


def main():
    game = Game()
    terrain, groups = build_terrain(game)
    terrain['r'] = {**terrain['%'], 'name': 'Rubble'}
    maps = []
    # The story's chapters, then the six trial maps (scripts C91-C96).
    for n in [*range(1, 32), *range(91, 97)]:
        # Ch.17 (file 18) is four sections played back to back on one big map: one map each.
        for section in ((1, 2, 3, 4) if n == 18 else (None,)):
            m = build_chapter(game, terrain, n, section)
            if m['route'] == 'Trial':
                # A trial map keeps nothing you take (its battle hands nothing back to the story), so nothing on it is worth a theft.
                for u in m['units'] + [x for g in m.get('reinforcements', []) for x in g['units']]:
                    u.pop('steal', None)
                    (u.get('standIn') or {}).pop('steal', None)
            maps.append(m)
            print(f"{m['heading']}: {m['width']}x{m['height']}, {len(m['units'])} units, {len(m.get('reinforcements', []))} groups, "
                  f"{len(m.get('joiners', []))} joiners, {len(m['objects'])} objects, {len(m.get('walls', []))} fences, "
                  f"{len(m['changes'])} changes")

    with open(os.path.join(OUT_DIR, 'fe9Terrain.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { TerrainInfo } from '../maps/fatesTerrain'\nimport type { TerrainCode } from '../maps/terrainCodes'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe9-maps.py from the terrain table in FE8Data.bin. Do not edit by hand.\n */\n\n')
        f.write("/** Path of Radiance's movement groups: classes in a group pay the same cost on every terrain. */\n")
        f.write(f'export const FE9_MOVE_CLASSES = {json.dumps([g[0] for g in groups], ensure_ascii=False)} as const\n\n')
        f.write('export const FE9_MOVE_CLASS_EXAMPLES: Record<string, string> = {\n')
        for name, _, ex in groups:
            f.write(f"  {json.dumps(name, ensure_ascii=False)}: {json.dumps(', '.join(ex), ensure_ascii=False)},\n")
        f.write('}\n\n/** Def, Avoid, healing (% of max HP each turn) and movement cost (null = can\'t enter) by terrain code. */\n')
        f.write('export const FE9_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {\n')
        coded = {encode('fe9', letter): info for letter, info in terrain.items()}
        encoded = [map_pieces.stone_crossing(tellius_minimaps.apply(map_pieces.town(stall_fixes(encode_map('fe9', paved_town(sandy_map(m))),
                                                                                               coded), coded), coded), coded)
                   for m in maps]
        for code, info in coded.items():
            f.write(f"  {code}: {json.dumps(info, ensure_ascii=False)},\n")
        f.write('}\n')
    with open(os.path.join(OUT_DIR, 'fe9Maps.ts'), 'w', encoding='utf-8') as f:
        f.write("import type { ChapterMap } from '../maps/types'\nimport { FE9_TERRAIN } from './fe9Terrain'\n\n")
        f.write('/*\n * GENERATED by scripts/build-fe9-maps.py from the game\'s own map, placement and script files.\n')
        f.write(' * Do not edit by hand.\n */\n\nconst RAW = [\n')
        for m in encoded:
            f.write('  ' + json.dumps(m, ensure_ascii=False) + ',\n')
        f.write(']\n\nexport const FE9_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE9_TERRAIN }))\n')


if __name__ == '__main__':
    main()

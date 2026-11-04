"""
Builds Three Houses' maps from the game's own files (scripts/fe16_data.py):
  src/data/fe16/fe16Terrain.ts      terrain Prt, Rsl, Avoid, healing and movement costs, from the game's own tables
  src/data/fe16/fe16Maps.ts         each battle's map, units by difficulty and house, reinforcements, objectives
  src/data/fe16/fe16ItemSources.ts  where each weapon turns up on the maps
Run:
    python scripts/build-fe16-maps.py

This first part is White Clouds: the Prologue and Chapters 1 to 11, which every house plays (Chapter 12 is where the routes part).
Formats are in data-raw/fe16/README.md. Coordinates: the grids count rows and columns from 0 at the top left; the app counts from
(1, 1) at the bottom left.
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe16_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe16', 'Three Houses', 'build-fe16-maps.py'
DIFFS = ['Normal', 'Hard', 'Maddening']
# The houses, their unit table in a battle's .bai and the routes its scripts test for them (Route 0 Silver Snow and 3 Crimson Flower
# are both the Black Eagles' until the end of Chapter 11, 1 Azure Moon the Blue Lions', 2 Verdant Wind the Golden Deer's).
HOUSES = [('be', 'Black Eagles', 0, (0, 3)), ('bl', 'Blue Lions', 1, (1,)), ('gd', 'Golden Deer', 2, (2,))]
STORY = list(range(12))
# The routes from Chapter 12 (fixed_flow.bin: each chapter's battle per route), in the same form: Crimson Flower and Silver Snow are
# the Black Eagles' (their unit table), Azure Moon the Blue Lions', Verdant Wind the Golden Deer's. Each route's leader fights beside
# Byleth (Silver Snow has none: Edelgard is the foe).
ROUTES = [('cf', 'Crimson Flower', 0, (D.CRIMSON_FLOWER,)), ('ss', 'Silver Snow', 0, (D.SILVER_SNOW,)),
          ('am', 'Azure Moon', 1, (D.AZURE_MOON,)), ('vw', 'Verdant Wind', 2, (D.VERDANT_WIND,))]
ROUTE_LORD = {'cf': 2, 'ss': None, 'am': 3, 'vw': 4, 'cs': None}
# Cindered Shadows (the DLC's side story: fixed_flow.bin section 5), its own route (the user's call), played on Normal and Hard; the
# scripts number it route 4, and none of its battles tests a route.
CINDERED = ('cs', 'Cindered Shadows', 0, (4,))
CS_DIFFS = DIFFS[:2]
# Who is in your army on each route from Chapter 12 (persons): the house's students, as Part II's scripts test them ('is recruited'),
# but for Silver Snow's Edelgard and Hubert, who leave the Black Eagles. A student recruited from another house is an addition the
# maps show as a stand-in or a joiner 'if recruited'.
ROUTE_ARMY = {'cf': (2, 5, 6, 7, 8, 9, 10, 11), 'ss': (6, 7, 8, 9, 10, 11), 'am': (3, 12, 13, 14, 15, 16, 17, 18),
              'vw': (4, 19, 20, 21, 22, 23, 24, 25)}
PART_TWO = 12            # the first chapter whose battle the routes choose (fixed_flow.bin)
# The scenario byte with each route's lose condition (D.scenario: +41 the Black Eagles' and Silver Snow's, +42 Azure Moon's, +43
# Verdant Wind's, +44 Crimson Flower's).
DEFEAT_FIELD = {D.SILVER_SNOW: 41, D.AZURE_MOON: 42, D.VERDANT_WIND: 43, D.CRIMSON_FLOWER: 44, 4: 41}
# The teams a phase belongs to (StartOfTeamPhase2's argument, bsic's Team): yours, the foe's, the green army's, the third army's.
TEAM_PHASE = {0: 'your phase', 1: 'the enemy phase', 2: "the allied army's phase", 3: "the third army's phase"}
# Battles each house plays as its own: the mock battles (each house's unit table), the Rite of Rebirth (the Blue Lions' copy of one
# opening event places two more Myrmidons on Hard and Maddening) and the Holy Tomb (on the Black Eagles' route Edelgard is the foe's
# commander and no leader fights for you). In every other White Clouds battle the houses differ only in which leader fights beside
# Byleth, on the same tile (`shared_check`).
PER_HOUSE = (1, 4, 7, 11)
LORDS = {2: 'Edelgard', 3: 'Dimitri', 4: 'Claude'}
LEADER = 'Your house leader (Edelgard, Dimitri or Claude)'
# Each house's students, who join it at Chapter 1 (persons): the lord first. Byleth and the three lords fight from the Prologue.
STUDENTS = {
    'be': [2, 5, 6, 7, 8, 9, 10, 11], 'bl': [3, 12, 13, 14, 15, 16, 17, 18], 'gd': [4, 19, 20, 21, 22, 23, 24, 25],
}
PROLOGUE_ARMY = [0, 2, 3, 4]
# The faculty and knights the monastery's script lets you recruit (file 360's RecruitTalk events), with the chapter each check opens
# from: Catherine 4, Cyril and Shamir 5, Hanneman and Manuela 8, Alois 11.
RECRUITS = {32: 4, 34: 5, 33: 5, 28: 8, 29: 8, 31: 11}
PLAYER_SLOT = 299        # the person a slot you fill holds ("Player")
NO_ARMY = 4              # a unit record's army byte: 0 yours, 1 the foe, 2 green, 3 a third army, 4 none (never on the map)
# A unit record's rank (+33) of 4, 5 or 6 isn't a unit but a reinforcement point: from the turn it's placed, a copy of the record comes in
# every turn, every other turn or every third turn, until the script takes the point off the map. Read from the data against Fire
# Emblem Wiki: Chapter 8's two rank-6 Commoners come 'every third turn starting turn 1' (the wiki's 14 villagers at the start, not 16),
# Legend of the Lake's rank-6 groups, placed on turns 2, 3 and 4, repeat every third turn, Insurmountable's rank-5 Wyvern Riders (Normal)
# come on odd-numbered turns and its rank-4 ones (Hard) every turn, and Protecting Garreg Mach's two rank-5 Falcon Knights on odd turns.
# The loader gives them no level change (only ranks 1-3 have one).
POINT_EVERY = {4: 1, 5: 2, 6: 3}
NAMED_BELOW = 100        # persons 0-99 are people; 100 on are the generic soldiers, villagers and beasts
DLC_PEOPLE = 1000        # from 1000, the DLC's people (the Ashen Wolves, Aelfric, Jeritza, Anna)
# How many person records show each name (+18, a person number): a commander or sub-commander whose name only its own record shows is
# someone (the DLC paralogues' Myson, Baron Ochs, Duke Gerth; Cindered Shadows' Marcelle and Simone; Shambhala's Chilon), where a
# soldier's one record can carry an army's name for many ('Phantom Soldier').
NAME_SHARED = {}
for _r in D.persons():
    _n = struct.unpack_from('<H', _r, 18)[0]
    NAME_SHARED[_n] = NAME_SHARED.get(_n, 0) + 1


def is_person(u):
    """Whether a unit record's person is someone of their own, named on the map, rather than a generic unit named by its class."""
    p = u['person']
    if p is None:
        return False
    if p < NAMED_BELOW or p >= DLC_PEOPLE:
        return True
    # A commander or sub-commander (ranks 0-2); the rest (3) and the reinforcement points (4-6) are soldiers.
    return u['rank'] in (0, 1, 2) and p != PLAYER_SLOT and NAME_SHARED.get(struct.unpack_from('<H', D.persons()[p], 18)[0], 0) == 1
# The actions that place a unit (README, 'Spawns'): SpawnUnit130 where its record stands; SpawnUnit from a tile to its record's;
# SpawnSpooky (620: the record, x, y, facing, a flag) on the action's own tile, never the record's. The script interpreter (`0x5480c0`,
# codes 530-860 through the jump table at `0xd17610`) hands SpawnSpooky to `0x54cdf0`: its first step passes the action's x and y to
# `0xa6940`, which keeps them where the unit can stand there and otherwise takes the nearest tile it can (squares of widening radius),
# and moves the unit there (`0x952e0`, `0x9b2c0`), turned to the facing (0 keeps its own); the next shows it (`0xa75a0`) with an effect
# and a sound. A tile outside the playable area places no one.
SPAWNS = ('SpawnUnit', 'SpawnUnit130', 'SpawnSpooky')
# Events at the start of the battle: the map's load (10000, 10001), the battle's start (11500, 12000), their group heads (1999, 9999,
# 11499, 11999) and the checks after each action (2000), which the start's conditions also hold for.
START_TRIGGERS = {1999, 2000, 9999, 10000, 10001, 11499, 11500, 11999, 12000}
LOAD_TRIGGERS = START_TRIGGERS - {1999, 2000}   # those that run only as the battle starts
PHASE = {13000: 'your phase', 14000: 'the enemy phase'}
START_LEAVES = {'IsStartOfMap', 'IsStartOfBattle', 'StartOfBattleMaybe'}
# Event flags the White Clouds battles test, and what sets them: 61 is set in the monastery's Blue Sea Moon script (file 342) when
# the house's story step "The Goddess's Rite of Rebirth" (quests 42-44: text 14943 + quest) is marked 4.
FLAGS = {61: "\"The Goddess's Rite of Rebirth\" ended a certain way (event flag 61)",
         # Set by The Face Beneath's script (scenario 47) when your army beats the Death Knight in a battle there (its events 43 and
         # 53; 0 when he falls otherwise): the Enbarr Infiltration's Death Knight carries a Brave Lance instead of the Scythe of Sariel.
         71: 'your army beat the Death Knight in battle in "The Face Beneath" (event flag 71)',
         # Set by The Face Beneath's script (its event 48) when the battle is won.
         62: 'you cleared "The Face Beneath" (event flag 62)'}

# Terrain kind (fixed_stagedata.bin) -> builder letter (terrain_codes.py's 'fe16'), by how the game treats each: its stats and cost
# category. No unit enters category 0; only fliers cross category 1 (drawn by look); 2 and 12 cost everyone 1; 10 is a floor that costs
# some monsters 3.
LETTER = {
    0: '#', 1: '.', 2: '.', 3: 'f', 6: 'w', 8: 'R', 9: 'C', 10: 'b', 12: 'O', 13: 'C', 14: 'l', 15: 'S', 16: 'C', 17: 'd', 19: 'r',
    20: '#', 24: 'D', 25: 'T', 34: '#', 37: 'C', 38: 'W', 40: 'H', 41: '#', 42: 'C', 43: 'z', 44: '#', 45: '#', 46: 'c', 47: '#',
    51: 'V', 52: 'o', 56: 'm', 57: 'q', 58: 'A', 59: 'P', 60: 'L', 63: '#', 65: 'C', 68: '#', 69: 'O', 77: 'x', 78: 'Q', 79: '.',
    87: 'C', 91: 'O', 93: '#', 95: 'W', 102: 'C', 106: 'e',
    # Part II and the side battles: desert and beach (Prt -2, Avoid -20, slow going), sea, lake and pond, a channel, lava, a
    # stronghold, the throne, a ship's deck (walkable) and hull, the ruins, churches and the opera hall only fliers cross, a swamp,
    # floor traps and craters that hurt, the fire orbs and onagers units fire, a shoal, a raised bridge, and what no unit enters
    # (statues, gates, masts, the Viskam's tiles).
    5: 's', 73: 's', 11: 'a', 71: 'a', 83: 'a', 86: 'w', 18: 'J', 21: 'M', 22: 'F', 28: 'Z', 35: 't', 48: 'b', 49: 'C', 74: 'C',
    84: 'C', 85: 'C', 50: 'X', 54: 'K', 55: 'K', 61: 'G', 67: 'U', 70: 'h', 72: 'Y', 64: '#', 66: '#', 75: '#', 89: '#', 98: '#',
    99: '#', 100: '#', 101: '#',
    # Cindered Shadows: a floor, a cavity only fliers cross, the Abyss's gate (a door), magic seals and statues no unit enters.
    27: 'O', 29: 'x', 107: 'd', 108: '#', 109: '#', 110: '#', 111: '#', 112: '#', 113: '#',
}
LETTER_NAME = {
    '.': 'Plain', 'O': 'Floor', 'b': 'Bridge', 'S': 'Stairs', 'e': 'Wasteland', 'f': 'Forest', 'D': 'Thicket', 'T': 'Thicket',
    'A': 'Floor (Avo +40)', 'q': 'Cover', 'm': 'Wardwood', 'H': 'Healing tile +', 'J': 'Healing tile', 'P': 'Prayer stone', 'o': 'Burning floor',
    'w': 'River / channel', 'R': 'Rock', 'C': 'Cliff / mountain / wall / building', 'z': 'Valley', 'l': 'Fence', 'r': 'Rubble', 'x': 'Trench',
    '#': 'Wall', 'Q': 'Crest Stone', 'd': 'Door', 'c': 'Chest', 'L': 'Ballista', 'V': 'Lever', 'W': 'Breakable wall',
    's': 'Desert / beach', 'a': 'Sea / lake', 'M': 'Lava', 'F': 'Stronghold', 'Z': 'Swamp', 't': 'Throne', 'X': 'Floor trap',
    'K': 'Crater', 'G': 'Fire Orb', 'U': 'Onager', 'h': 'Shoal', 'Y': 'Raised bridge',
}
TERRAIN = D.terrain()
COSTS = D.move_costs()
CLASSES = D.classes()
DEFAULTS = D.default_weapons()
MONSTER_WEAPON = [r[4] | r[5] << 8 for r in D.table(D.CLASSDATA, 4)]   # by the class's byte +73 (fixed_classdata.bin section 4)
TIER_BONUS = [0, 1, 5, 8, 10, 10, 10]   # 0x1aa9168-0x1aa9198: level added for the default weapon, by the class tier (+69)
STEEL_FROM, SILVER_FROM = 19, 31        # 0x1a271a8, 0x1a271ac


def move_groups():
    """Movement types whose cost rows are the same, named after the classes that move that way."""
    by_row = {}
    for t in range(10):
        by_row.setdefault(tuple(COSTS[t]), []).append(t)
    names = {0: 'Infantry & armour', 2: 'Cavalry', 4: 'Mages', 5: 'Thieves & brawlers', 6: 'Fliers', 7: 'Beasts',
             8: 'Giant Crawlers', 9: 'Giant Wolves'}
    out = []
    for row, types in by_row.items():
        out.append((names[types[0]], types, list(row)))
    return out


GROUPS = move_groups()
CLASS_GROUP = {}
for _c, _r in enumerate(CLASSES):
    for _label, _types, _row in GROUPS:
        if _r[D.MOVE_TYPE] in _types:
            CLASS_GROUP[_c] = _label


def tile_info(kind):
    t = TERRAIN[kind]
    move = {label: (None if row[t['cost']] == 0xFF else row[t['cost']]) for label, _, row in GROUPS}
    e = {'name': LETTER_NAME[LETTER[kind]], 'def': t['prt'], 'res': t['rsl'], 'avo': t['avo'], 'heal': 0, 'move': move}
    if t['heal'] > 0:
        e['heal'] = t['heal']
    elif t['heal'] < 0:
        e['note'] = f"Takes {-t['heal']}% of max HP at the start of each turn."
    return e


def class_name(c):
    return D.class_name(c)


def default_weapon(cls, level):
    """What a unit with no items is given (the unit tables' loader, `0x19e2f8`): a monster its class's weapon; anyone else whose class
    fights with a weapon (main type 0-4) that type's Iron, Steel or Silver one by its level plus its class tier's bonus."""
    rec = CLASSES[cls]
    if rec[0x49] <= 0x1d:
        return MONSTER_WEAPON[rec[0x49]]
    kind = rec[D.MAIN_WEAPON]
    if kind > 4:
        return None
    eff = level + TIER_BONUS[min(rec[D.CLASS_TIER], 6)]
    tier = 2 if eff >= SILVER_FROM else 1 if eff >= STEEL_FROM else 0
    return DEFAULTS[kind][tier] + 10


def inventory(u, level):
    """The unit's items as the loader gives them: the default weapon (or monster weapon) in the first slot, then each filled slot of
    the table replacing the item in its own slot or taking the first free one (`0x19e470`). The drop field (+18) names the slot that
    drops (2-7: slot 0-5), or, from 8, an item more (the field - 1) put in the first free slot and dropped (`0x1a0ef8`)."""
    inv = []
    cls = unit_class(u)
    if cls is not None:
        g = default_weapon(cls, level)
        if g is not None:
            inv.append([g, False])
    drop = u['drops'] - 2 if u['drops'] else None
    for k, raw in enumerate(u['items']):
        if raw:
            if k < len(inv):
                inv[k] = [raw - 1, k == drop]
            else:
                inv.append([raw - 1, k == drop])
        elif k == drop and k < len(inv):
            inv[k][1] = True
    if u['drops'] >= 8 and len(inv) < 6:
        inv.append([u['drops'] - 1, True])
    return inv


def item_name(g):
    return D.global_item_name(g)


# What a thief can take from a foe that's worth marking (`MapUnit.steal`). Steal (`0x175da4`: the action menu offers it to a unit with
# skill property 61, ability 159's) lists the foes on the four tiles beside the thief, of an army it fights, with lower Spd and an item
# `D.stealable` allows (`0xca560`): never a weapon or a spell, never a relic. Of those, an item that lasts (equipment works while it's
# equipped; an item by its kind, its record's +13: a seal, gold, a stat booster or a dragon sign, not a potion, torch, key or meal used
# up for a moment's effect) and that no shop keeps in regular stock (a limited offer, availability 2, isn't renewed: `D.shop_stock`).
LASTING_KINDS = {5: 'seal', 6: 'gold', 9: 'stat booster', 11: 'dragon sign'}
SHOP_STOCK = D.shop_stock()


def rare_steal(g):
    if not D.stealable(g):
        return False
    lasting = 600 <= g < 650 or D.item_record(g)[13] in LASTING_KINDS
    return lasting and not any(kind == 'regular' for _, kind in SHOP_STOCK.get(g, ()))


def _group(kind, vals):
    """Three-valued 'and' / 'or' (None: unknown). An empty group holds (Chapter 8's Tomas becomes Solon under an empty 'or')."""
    if not vals:
        return True
    if kind == 'and':
        return False if False in vals else None if None in vals else True
    return True if True in vals else None if None in vals else False


def holds(t, ctx):
    """A condition tree's truth at the start of the battle (None: it can't be known there)."""
    if t[0] in ('and', 'or'):
        return _group(t[0], [holds(c, ctx) for c in t[1]])
    name, args = t
    if name == 'Difficulty':
        # (negated, a difficulty, how it compares: 0 <, 1 <=, 2 ==, 3 >=, 4 >)
        d, v, cmp = ctx['diff'], args[1], args[2]
        res = [d < v, d <= v, d == v, d >= v, d > v][cmp]
        return not res if args[0] else res
    if name == 'Route':
        res = args[1] in ctx['routes']
        return (res if args[2] else not res) if not args[0] else not (res if args[2] else not res)
    if name in ('IsStartOfMap', 'IsStartOfBattle', 'StartOfBattleMaybe'):
        return ctx['start']
    if name in ('IsRecruited', 'WasRecruitedPreTimeskip'):
        # Whether a person is in your army (`recruited`: White Clouds' maps take none, Part II's the route's students, `ROUTE_ARMY`),
        # which Part II's battles test as recruited before the timeskip too.
        res = args[1] in ctx.get('recruited', ())
        return not res if args[0] else res
    if name == 'CheckDeathStatus' and args[2] == 4:
        # (negated, a slot, 4): whether the unit's person was lost before this battle (Chapter 13's Seteth joins unless he was). The maps
        # take no one as lost.
        return bool(args[0])
    if name == 'CharacterRecruitedButDead':
        # A recruited student who has died: the battle places the stand-in as it does for one alive in your army. The maps show who
        # stands there without your army's losses.
        return bool(args[0])
    if name == 'HasOtherScriptRun':
        if args[1] in ctx['ran']:
            return bool(args[2])
        return None if args[1] in ctx['pending'] else not args[2]
    return None


class Battle:
    def __init__(self, s, house, extra=()):
        self.s = s
        self.scen = D.scenario(s)
        self.w, self.h, self.rows = D.grid(self.scen['map'])
        tabs = D.units(s)
        self.house = house
        # A battle whose units are each house's own (the scenario's +36 bit 0: the mock battles and To War at Gronder) starts from the
        # house's table, one Crimson Flower fights apart (+36 bit 1: Foreign Land and Sky) from table 1 on that route; every other
        # battle from table 0, its scripts placing the rest by slot.
        self.table = house[2] if self.scen['per_house'] else 1 if self.scen['cf_table'] and house[3] == (D.CRIMSON_FLOWER,) else 0
        self.tables = tabs
        # Who is in your army: the route's students from Chapter 12, no one in White Clouds' battles.
        self.army = (ROUTE_ARMY.get(house[0], ()) if len(house[3]) == 1 and house in ROUTES else ()) + tuple(extra)
        # A switched-off event never runs (fe16_data.script): it isn't read at all; a wait for one never ends (`_simplify`).
        self.events = [e for e in D.script(s) if not e['off']]
        self.event_nums = {e['num'] for e in self.events}
        self._ends = None
        self.after = {}   # `_after`
        self._starts, self._described = {}, {}
        # Foes the script swaps for a unit of yours (ReplaceUnitBAI: the new record, the old): none in any battle. Its swaps across
        # armies are Chapter 9's beasts turning back into green students and green units turning on you (Chapter 8's Tomas into
        # Solon, Falling Short of Heaven's and Legend of the Lake's).
        self.joins = {a[1] for e in self.events for n, a in e['actions']
                      if n == 'ReplaceUnitBAI' and self.record(a[0])['army'] == 0 and self.record(a[1])['army'] in (1, 3)}
        self.loot = looting(self)
        self._grants = {}
        # Cindered Shadows is played on Normal and Hard.
        self.diffs = CS_DIFFS if s in D.flow(D.CINDERED_SHADOWS) else DIFFS

    def ends(self):
        """The end scene's events (`end_events`)."""
        if self._ends is None:
            self._ends = end_events(self)
        return self._ends

    def grants(self, diff):
        if diff not in self._grants:
            self._grants[diff] = self.granted(diff)
        return self._grants[diff]

    def app(self, x, y):
        return [x + 1, self.h - y]

    def recruit_checks(self):
        """The persons the start's events test 'is recruited' for whom your army doesn't hold (students another house can take)."""
        out = []
        for e in self.events:
            if e['trigger'][0] in START_TRIGGERS:
                out += [a[1] for n, a in _flat(e['conditions']) if n == 'IsRecruited' and a[1] not in self.army]
        return list(dict.fromkeys(out))

    def record(self, slot):
        return self.tables[slot // 100][slot % 100]

    def start(self, diff, recruited=()):
        """The units on the map when the battle starts, as {slot: [x, y]}, after the start's events: spawns, removals and walks
        (`recruited`: the students taken from other houses besides your army, whom the start replaces with stand-ins)."""
        key = (diff, tuple(recruited))
        if key not in self._starts:
            placed, ran = self._start(diff, recruited)
            self._starts[key] = (placed, ran, self.points)
        placed, ran, self.points = self._starts[key]
        return dict(placed), set(ran)

    def on_map(self, diff):
        """Who can be on the map on a difficulty: the start's units and points, and what later events can bring."""
        placed, ran = self.start(diff)
        course = {'diff': diff, 'routes': self.house[3], 'recruited': self.army}
        return set(placed) | set(self.points) | {a[1][0] for x in self.events if x['num'] not in ran and x['trigger'][0] not in LOAD_TRIGGERS
                                                 and on_course(x['conditions'], course) is not False
                                                 for a in x['actions'] if a[0] in SPAWNS}

    def context(self, diff):
        """What a time is read for on a difficulty (`describe`)."""
        placed, ran = self.start(diff)
        return {'diff': diff, 'routes': self.house[3], 'recruited': self.army, 'ran': ran, 'placed': self.on_map(diff)}

    def described(self, e, diff):
        """An event's time on a difficulty, its areas named by their corners (a unit's note can't outline them)."""
        key = (e['num'], diff)
        if key not in self._described:
            self._described[key] = describe(self, e, self.context(diff), corners=True)
        return self._described[key]

    def _start(self, diff, recruited=()):
        recruited = tuple(self.army) + tuple(recruited)
        placed = {}
        for u in self.tables[self.table]:
            if u['army'] in (0, 1, 2, 3) and not u['scripted'] and (u['person'] is not None or u['class'] is not None):
                placed[self.table * 100 + u['slot']] = (u['x'], u['y'])
        ran, done = set(), set()
        # A unit the map's load takes off (10000: Tales of the Red Canyon's Normal-only Giant Bird) is out of the battle: the opening
        # scene that hides the beasts and walks them back in (its RemoveFromMap and SpawnUnit) doesn't bring it back.
        out = set()
        starts = [e for e in self.events if e['trigger'][0] in START_TRIGGERS]
        changed = True
        while changed:
            changed = False
            for e in starts:
                if e['num'] in done:
                    continue
                ctx = {'diff': diff, 'routes': self.house[3], 'start': True, 'ran': ran, 'recruited': recruited,
                       'pending': {x['num'] for x in starts if x['num'] not in done}}
                v = holds(e['conditions'], ctx)
                if v is None:
                    continue
                done.add(e['num'])
                changed = True
                if not v:
                    continue
                ran.add(e['num'])
                for name, args in e['actions']:
                    if name in SPAWNS:
                        r = self.record(args[0])
                        # A unit of no army (4) never appears, whatever places it: Chapter 6 fields Fire Emblem Wiki's 26, 28 and 32
                        # foes only without its one.
                        if r['army'] != NO_ARMY and args[0] not in out:
                            if name == 'SpawnSpooky':
                                placed[args[0]] = (args[1], args[2])   # the action's tile (`SPAWNS`), moving a unit already there
                            else:
                                placed.setdefault(args[0], (r['x'], r['y']))
                    elif name == 'RemoveFromMap':
                        placed.pop(args[0], None)
                        if e['trigger'][0] in (10000, 10001):
                            out.add(args[0])
                    elif name == 'Walk' and args[0] in placed:
                        placed[args[0]] = (args[1], args[2])
                    elif name == 'Walk' and self.record(args[0])['army'] == 0:
                        # A unit of yours the opening walks onto the map (Chapter 2's house leader) stands where the walk ends.
                        placed[args[0]] = (args[1], args[2])
                    elif name == 'ReplaceUnitBAI' and args[1] in placed:
                        placed[args[0]] = placed.pop(args[1])
        # Reinforcement points (`POINT_EVERY`) send their copies in from the first turn: they aren't units at the start.
        self.points = {slot: tile for slot, tile in placed.items() if self.is_point(slot)}
        placed = {slot: tile for slot, tile in placed.items() if slot not in self.points}
        return placed, ran

    def granted(self, diff):
        """What the start's events hand units ({slot: [global item]}: GrantItem to a unit's slot, a foe's weapon by difficulty:
        Insurmountable's Steel Bows)."""
        _, ran = self.start(diff)
        out = {}
        for e in self.events:
            if e['num'] in ran:
                for name, args in e['actions']:
                    if name == 'GrantItem' and args[0] and args[0] < 300:
                        out.setdefault(args[0], []).append(args[1])
        return out

    def is_point(self, slot):
        r = self.record(slot)
        return r['army'] != 0 and r['rank'] in POINT_EVERY


COURSE = ('Difficulty', 'Route', 'IsRecruited', 'WasRecruitedPreTimeskip', 'CharacterRecruitedButDead')


def on_course(t, ctx):
    """A condition tree's truth by its difficulty, route and army checks alone (None: something else decides it): whether an event can
    run on this difficulty and route, with your army as the maps take it, at all."""
    if t[0] in ('and', 'or'):
        return _group(t[0], [on_course(c, ctx) for c in t[1]])
    if t[0] == 'CheckDeathStatus' and t[1][2] == 4:
        return holds(t, ctx)
    return holds(t, ctx) if t[0] in COURSE else None


def unit_class(u):
    """The unit's class: its record's (+4, class + 1), or, where that's 0, its person's own (person record +26)."""
    if u['class'] is not None:
        return u['class']
    if u['person'] is not None:
        return D.persons()[u['person']][26]
    return None


def level_of(b, u, diff):
    if u['level']:
        return u['level']
    base = b.scen['levels'][diff]
    # A reinforcement point's copies come in two levels under the battle's, as the rest do (Fire Emblem Wiki: Chapter 8's repeating
    # Commoners Lv 15 of the battle's 17, Insurmountable's Wyvern Riders Lv 29 of 31).
    return max(1, base - {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 2}.get(u['rank'], 0))


def unit_entry(b, slot, tile, diff, victory, came=None):
    """A unit as the map shows it, on a difficulty; `came`: the event that brings it in (None for a unit at the start)."""
    u = b.record(slot)
    person = u['person']
    generic = not is_person(u)
    cls = unit_class(u)
    lv = level_of(b, u, diff)
    inv = inventory(u, lv)
    # What the opening hands it goes in its first free slot.
    for g in b.grants(diff).get(slot, []):
        if len(inv) < 6 and g not in [x for x, _ in inv]:
            inv.append([g, False])
    army = u['army']
    commander = u['rank'] == 0 and army == 1
    kind = 'ally' if army == 2 else ('boss' if commander and victory in (1, 3, 8) else 'enemy' if generic else 'named')
    name = class_name(cls) if generic and cls is not None else D.person_shown_name(person)
    e = {'type': kind, 'name': name, 'tile': b.app(*tile)}
    if cls is not None and D.monster_size(cls) > 1:
        # A monster covers a square of tiles, its record's tile the square's top-left (the app's too: the square runs right and down).
        e['size'] = D.monster_size(cls)
    bars = D.monster_bars(cls) if cls is not None else 1
    if bars > 1:
        e['bars'] = bars   # its health bars: pips along the bottom of its marker
    note = f'Lv {lv}' if generic else f'Lv {lv} {class_name(cls)}'
    if army == 3:
        note += ' · third army (yellow in the game): fights you and the red army'
    if cls is not None and D.monster_bars(cls) > 1:
        note += f'; {D.monster_bars(cls)} health bars'
    loot = b.loot.get(slot)
    if loot:
        at = [f'({x}, {y})' for x, y in (b.app(*t) for t in loot['tiles'])]
        what = f"the {loot['thing']} at {at[0]}" if len(at) == 1 else \
            f"the {plural(loot['thing'])} at {', '.join(at[:-1])} and {at[-1]}"
        out = b.app(*loot['exit'])
        note += f'; takes {what}, then leaves the map at ({out[0]}, {out[1]})'
        e['looter'] = True
        e['goesTo'] = [b.app(*t) for t in loot['tiles']] + [out]
    else:
        ai = ai_words(b, slot, diff, came)
        if ai:
            note += f'; {ai}'
    e['note'] = note
    carries = [item_name(g) for g, _ in inv]
    if carries:
        e['carries'] = carries
    drops = [item_name(g) for g, d in inv if d]
    if drops:
        e['drops'] = drops
    # A thief steals from the red and third armies (`0xca560`), never from a foe the battle brings into your army (`b.joins`).
    steal = [n for n in dict.fromkeys(item_name(g) for g, d in inv if not d and rare_steal(g)) if n not in drops]
    if steal and army in (1, 3) and slot not in b.joins:
        e['steal'] = steal
    if generic:
        e['generic'] = True
    if army == 3:
        e['yellow'] = True
    return e, inv


# The units' AI (README, 'AI'). A unit's AI kind is its +0xf6, from its record's +31 (the loader, `0x1a0f3c`); the script sets it:
# SetMovementFlag (440, `0x549ce0` -> `0xa6fd0`) to a kind, MoveToUnitAI2 (370, `0x54bd90`) to kind 1 with five units to go for,
# MoveToUnitAI (690, `0x54d8b0`) to kind 18 with five to move with, MoveToRectangleAI (380, `0x54bf70`) and MoveToRectangleAI820
# (820, `0x54de10`) to kind 11 with a rectangle to head for, MoveToRectangleAI580 (580, `0x54cbf0`) to kind 10 (the looters'). The
# kinds are archive file 14's records (25 of 20 bytes, loaded at `0x3b59e4`): +0 how it attacks (0 never), +2 when it starts moving
# (`0x169b30`: 0 never, 1 at once, 2 once one of your units is within its reach), +3 the HP share at which it goes to heal
# (`0x16ab10`), +4 how it moves (`0x169098`, its cases through `0xcdb608`; 0 and 2 give it no Mov, `0x405180` in the stat getter
# `0xb0240`).
AI_KINDS = D.table(14, 0)
AI_ACTIONS = {'SetMovementFlag': None, 'MoveToUnitAI2': 1, 'MoveToUnitAI': 18, 'MoveToRectangleAI': 11, 'MoveToRectangleAI820': 11,
              'MoveToRectangleAI580': 10}


def _ai_targets(b, slot, targets, any_army):
    """The units an AI goes for (or moves with), first first: of its five targets (records of the battle's table, 300 none: the
    handlers keep each as its record, `slot % 100`), those that can be on the map, by name ('Claude', 'the green Commoner at (3, 4)',
    'your units' for the slots you fill), up to Byleth, who always is; going for one, only those of an army it fights, as the AI picks
    them (`0x16ac40`)."""
    me = b.record(slot)
    out = []
    for t in targets:
        if t == 300:
            continue
        r = b.tables[b.table][t % 100]
        if r['army'] == NO_ARMY or (r['person'] is None and r['class'] is None) or (not any_army and r['army'] == me['army']):
            continue
        if r['army'] == 0 and r['person'] in (None, PLAYER_SLOT):
            w = ('your units', None)
        elif is_person(r) or r['army'] == 0:
            w = (person_words(r), None)
        else:
            x, y = b.app(r['x'], r['y'])
            w = (f"{'green' if r['army'] == 2 else 'foe'} {class_name(unit_class(r))}", f'({x}, {y})')
        if w not in out:
            out.append(w)
        if r['army'] == 0 and r['person'] == 0:
            break
    # Generic units of one class in a row are said together ('the foe Heroes at (9, 16), (12, 19) and (13, 20)').
    runs = []
    for name, tile in out:
        if tile and runs and runs[-1][0] == name and runs[-1][1]:
            runs[-1][1].append(tile)
        else:
            runs.append([name, [tile] if tile else None])
    words = []
    for name, tiles in runs:
        if not tiles:
            words.append(name)
        elif len(tiles) == 1:
            words.append(f'the {name} at {tiles[0]}')
        else:
            side, cls = name.split(' ', 1)
            words.append(f"the {side} {plural(cls)} at {', '.join(tiles[:-1])} and {tiles[-1]}")
    return words


def _ai_pattern(b, slot, how, args, kind):
    """What an AI does that's its own, in words, or None for the plain ways (waiting until one of your units is in reach, or
    advancing on your army, attacking what it reaches). Read in the program: kind 1's targets (`0x16ac40`): the first of its five on
    the map and of an army it fights, attacked once it can reach it; until then, with the action's last argument set, it attacks
    what else it reaches (`0x16b780`) and otherwise moves toward it (`0x16dbf0`), without, it only moves toward it. Kind 18's
    (`0x16b170`): the first on the map, of any army, which it heals with a staff or spell once it has lost half its HP (`0x16e290`)
    and moves to stay beside. Kind 11 (`0x16c430`): the rectangle's tile it reaches soonest; MoveToRectangleAI's fifth argument lets
    it attack on the way (`0x16fa70`), without it never does; MoveToRectangleAI820 attacks only from inside the rectangle. A kind
    whose +4 leaves it no Mov holds its ground, attacking what comes into its weapon's reach, or, where it never starts moving or
    never attacks, does nothing (Chapter 9's students)."""
    if how == 'MoveToUnitAI2':
        names = _ai_targets(b, slot, args[1:6], False)
        return ('goes for ' + ', then '.join(names) + ('' if args[6] else ', attacking no one else')) if names else None
    if how == 'MoveToUnitAI':
        names = _ai_targets(b, slot, args[1:6], True)
        return ('moves with ' + ', then '.join(names)) if names else None
    if how in ('MoveToRectangleAI', 'MoveToRectangleAI820'):
        x1, x2 = sorted((args[1], args[3]))
        y1, y2 = sorted((args[2], args[4]))
        if not (0 <= x1 and x2 < b.w and 0 <= y1 and y2 < b.h):
            return None
        left, bottom, right, top = gm.rect_to_app((x1, y1, x2, y2), b.h)
        where = f'({left}, {bottom})' if (left, bottom) == (right, top) else f'the area from ({left}, {bottom}) to ({right}, {top})'
        return f'heads for {where}' + (', never attacking' if how == 'MoveToRectangleAI' and not args[5] else '')
    if how == 'MoveToRectangleAI580' or kind >= len(AI_KINDS):
        return None    # the looters' (`looting`)
    rec = AI_KINDS[kind]
    if rec[4] in (0, 2):
        return 'never moves or attacks' if not rec[0] or not rec[2] else 'holds its ground'
    return 'never attacks' if not rec[0] else None


def ai_words(b, slot, diff, came=None):
    """What a foe's or green unit's AI does, for its note, or None: its own way as it appears (its record's kind, what the start's
    events set, or the event that brings it in; an event at a phase's start that checks nothing else counts as at once), then up to
    two changes later events make ('holds its ground until Claude is defeated'; 'once Hilda is defeated, goes for Claude, then
    Byleth'), a time too long for the note said as 'an event in the chapter'. An arrival's later changes are those of the events that
    wait for it; the same AI said again is left out."""
    r = b.record(slot)
    if r['army'] in (0, NO_ARMY):
        return None
    ctx = {'diff': diff, 'routes': b.house[3], 'recruited': b.army}
    placed, ran = b.start(diff)
    ends = b.ends()

    def sets(e):
        st = None
        for name, args in e['actions']:
            if name in AI_ACTIONS and args[0] == slot:
                st = (name, args, args[1] if name == 'SetMovementFlag' else AI_ACTIONS[name])
        return st

    state = ('record', (), r['raw'][31])
    if came is None:
        for e in b.events:
            if e['num'] in ran and sets(e):
                state = sets(e)
        later = [e for e in b.events if e['num'] not in ran and e['num'] not in ends and e['trigger'][0] not in LOAD_TRIGGERS
                 and on_course(e['conditions'], ctx) is not False]
        start_time = None
    else:
        # Every event that can bring it in on this difficulty (the routes' and difficulties' copies, its other ways in) says the same:
        # the first that sets its AI as it comes, then what the events waiting for any of them change.
        placers = [x for x in b.events if x['num'] not in ran and x['num'] not in ends and slot in _brings(b, x)
                   and on_course(x['conditions'], ctx) is not False] or [next(x for x in b.events if x['num'] == came)]
        state = next((sets(x) for x in placers if sets(x)), state)
        after = set().union(*(_after(b, x['num']) for x in placers)) - {x['num'] for x in placers}
        later = [e for e in b.events if e['num'] in after and e['num'] not in ends and on_course(e['conditions'], ctx) is not False]
        start_time = {t for t, once in (_ai_time(b.described(x, diff)) for x in placers) if t != 'After an event in the chapter'}
    # Set as it appears: by an event that runs as the one bringing it in does, at a phase's start with nothing else, or on turn 1 at
    # your phase or its own, before it first acts.
    first = ('Turn 1', 'Turn 1, your phase', f"Turn 1, {TEAM_PHASE.get(r['army'])}")
    base = _ai_pattern(b, slot, *state)
    timed = []    # (time, the time as a step before a later one, the AI it takes on)
    for e in later:
        st = sets(e)
        if not st:
            continue
        w = b.described(e, diff)
        text, once = _ai_time(w)
        if (start_time and text in start_time) or (not w['flags'] and not w['partial'] and (
                (w['once'] is None and w['text'].startswith(('At the start of', 'During'))) or w['text'] in first)):
            base = _ai_pattern(b, slot, *st)
        else:
            timed.append((text, once, _ai_pattern(b, slot, *st)))
    cur, changes, more = base, [], False
    for text, once, p in timed:
        if changes and changes[-1][0] == text and changes[-1][1] is not None:
            # Two events at one time (Saving Derdriu's Hilda on Maddening: a tile to head for, then holding it): the later stands.
            changes.pop()
            cur = changes[-1][2] if changes else base
        if p == cur:
            continue
        if len(changes) == AI_CHANGES:
            more = True
            break
        changes.append((text, once, p))
        cur = p
    # Each change with its time where the note has room, else after 'an event in the chapter'; one more than the note can hold ends
    # the last said with 'until an event in the chapter'.
    parts = [base] if base else []
    size = len(base or '')
    for text, once, p in changes:
        if p is None:
            if not parts:
                continue
            ways = [' until ' + once] if once else []
            ways.append(' until an event in the chapter')
        else:
            ways = [f'; {text[0].lower()}{text[1:]}, {p}'] if once is not None else []
            ways.append(f'; after an event in the chapter, {p}')
        piece = next((x for x in ways if size + len(x) <= AI_BUDGET), None)
        if piece is None:
            more = True
            break
        size += len(piece)
        if p is None:
            parts[-1] += piece
        else:
            parts.append(piece[2:])
    if more and parts and ' until ' not in parts[-1]:
        parts[-1] += ' until an event in the chapter'
    return '; '.join(parts) if parts else None


# A note says at most this many later changes of a unit's AI, in at most this many characters (a time that doesn't fit is 'an event
# in the chapter').
AI_CHANGES, AI_BUDGET = 2, 200


def _ai_time(w):
    """An event's time (`describe`) for a note: as a time ('on turn 3', 'at the enemy phase of turn 2, ...') and as a step ('once
    ...'), with the event flags it needs; one that checks something it can't say is 'an event in the chapter'."""
    if w['partial']:
        return 'After an event in the chapter', None
    flags = ''.join(', ' + f for f in flag_words(w['flags']))
    text = re.sub(r"^Turn (\d+), (your phase|the enemy phase|the allied army's phase|the third army's phase)", r'at \2 of turn \1',
                  w['text'])
    text = re.sub(r'^Turn (\d+)', r'on turn \1', text)
    return text + flags, (w['once'] + flags if w['once'] else None)


def _flat(t):
    if t[0] in ('and', 'or'):
        out = []
        for c in t[1]:
            out += _flat(c)
        return out
    return [t]


def end_events(b):
    """The events that end the battle (EndMission), those that run once it's won (DidCompleteMap: the rewards and the closing scene,
    Ambush in the Arena's Aelfric, Besieged in the Chapel Ruins' Dark Bishops) and every event that waits for one: the end scene, whose
    cast is never a unit on the battle map."""
    ends = {e['num'] for e in b.events if any(a[0] == 'EndMission' for a in e['actions'])
            or any(n == 'DidCompleteMap' and not a[0] for n, a in _flat(e['conditions']))}
    changed = True
    while changed:
        changed = False
        for e in b.events:
            if e['num'] in ends:
                continue
            if any(n == 'HasOtherScriptRun' and a[2] and a[1] in ends for n, a in _flat(e['conditions'])):
                ends.add(e['num'])
                changed = True
    return ends


def _defeat(name, args):
    """Whether a condition is a defeat: CheckDeathStatus (negated, a slot, kind) of kind 1, the unit at 0 HP, or of kind 0, the unit on
    the map with HP left, negated (`0x556860`: kind 0 on the map with HP left, 1 at 0 HP, 2 taken off the map, 3 no such unit, 4 lost
    before the battle; any condition's first argument negates it, `0x545e00`)."""
    return name == 'CheckDeathStatus' and ((args[2] == 1 and not args[0]) or (args[2] == 0 and args[0]))


def _standing(name, args):
    """Whether a condition wants a unit still standing (kind 0, or kind 1 negated): what stops an arrival that checks it."""
    return name == 'CheckDeathStatus' and ((args[2] == 0 and not args[0]) or (args[2] == 1 and args[0]))


def _deaths(t):
    """The defeats a condition tree checks, as (kind, slots): 'all' for those it needs together, 'any' for one of those under an
    'or'."""
    if t[0] == 'or':
        slots = [a[1] for n, a in _flat(t) if _defeat(n, a)]
        return [('any', slots)] if slots else []
    if t[0] == 'and':
        out, mine = [], []
        for c in t[1]:
            if c[0] in ('and', 'or'):
                out += _deaths(c)
            elif _defeat(*c):
                mine.append(c[1][1])
        return ([('all', mine)] if mine else []) + out
    return [('all', [t[1][1]])] if _defeat(*t) else []


def _who_falls(b, kind, slots):
    """'Kostas is defeated', 'the foe Dark Mage at (12, 3) is defeated', 'either foe Thief at (4, 22) or (4, 21) is defeated'."""
    names, sides = [], []
    for slot in slots:
        u = b.record(slot)
        p = u['person']
        named = is_person(u)
        names.append((D.person_shown_name(p) if named else class_name(unit_class(u)), named, b.app(u['x'], u['y'])))
        # A green unit is said as one (Saving Derdriu's War Master standing in for Hilda), a red or third army's as a foe.
        sides.append('green' if u['army'] == 2 else 'foe')
    side = sides[0] if len(set(sides)) == 1 else 'foe'
    if len(names) > 4 and not any(named for _, named, _ in names):
        # A long list of generic foes (True Chivalry's nine) by class: 'any of 9 foes (2 Mercenaries, 4 Thieves...)'.
        count = {n: [x for x, _, _ in names].count(n) for n in dict.fromkeys(x for x, _, _ in names)}
        parts = [f'a{"n" if n[0] in "AEIOU" else ""} {n}' if k == 1 else f'{k} {plural(n)}' for n, k in count.items()]
        listed = parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' and ' + parts[-1]
        many = 'foes' if side == 'foe' else 'green units'
        return (f'any of {len(names)} {many} ({listed}) is defeated' if kind == 'any' else
                f'the {len(names)} {many} ({listed}) are defeated')
    if len({n for n, _, _ in names}) == 1 and not names[0][1]:
        cls, tiles = names[0][0], [f'({t[0]}, {t[1]})' for _, _, t in names]
        if len(names) == 1:
            return f'the {side} {cls} at {tiles[0]} is defeated'
        if kind == 'any':
            first = 'either' if len(names) == 2 else 'any'
            return f"{first} {side} {cls} at {', '.join(tiles[:-1])} or {tiles[-1]} is defeated"
        return f"the {len(names)} {side} {plural(cls)} at {', '.join(tiles[:-1])} and {tiles[-1]} are defeated"
    # One person in two records (the Enbarr Infiltration's two Death Knights, one per event flag) is said once, and generic units of
    # one army on one tile (Combat at Tailtean Plains' Paladin and the Altered Demonic Beast it becomes) as one.
    tiled = {}
    for (n, named, t), s in zip(names, sides):
        if not named:
            tiled.setdefault((s, tuple(t)), []).append(n)
    words = []
    for (n, named, t), s in zip(names, sides):
        if named:
            words.append(n)
        else:
            classes = list(dict.fromkeys(tiled[(s, tuple(t))]))
            words.append(f"the {s} {' or '.join(classes) if kind == 'any' else ' and '.join(classes)} at ({t[0]}, {t[1]})")
    words = list(dict.fromkeys(words))
    joined = words[0] if len(words) == 1 else ', '.join(words[:-1]) + (' or ' if kind == 'any' else ' and ') + words[-1]
    if kind == 'any' and len(words) > 1:
        return f'{joined} is defeated'
    return f'{joined} {"is" if len(words) == 1 else "are"} defeated'


def _used(b, n):
    """A gimmick record (fixed_gimmick.bin, `D.gimmick`) as the thing used: 'the Magic Seal at (1, 2) is used', the tile named by its
    terrain; None where the record isn't this battle's map's."""
    g = D.gimmick(n)
    if g['map'] != b.scen['map'] or not (0 <= g['x'] < b.w and 0 <= g['y'] < b.h):
        return None
    x, y = b.app(g['x'], g['y'])
    return f"the {D.text(5502 + b.rows[g['y']][g['x']][0])} at ({x}, {y}) is used", g['changed']


def _or_words(words):
    """'A', 'A or B', 'A, B or C'."""
    words = list(dict.fromkeys(words))
    return words[0] if len(words) == 1 else ', '.join(words[:-1]) + ' or ' + words[-1]


def _unit_words(b, slot):
    """A unit as a time names it: a person by name ('Ladislava', 'Byleth'), a slot you fill as 'one of your units', any other unit by
    its army, class and tile ('the foe Archer at (15, 18)', 'the green Commoner at (3, 4)'); None for a record of no unit."""
    u = b.record(slot)
    if u['army'] == 0 and u['person'] in (None, PLAYER_SLOT):
        return 'one of your units'
    if u['army'] == NO_ARMY or (u['person'] is None and u['class'] is None):
        return None
    if is_person(u) or u['army'] == 0:
        return person_words(u)
    x, y = b.app(u['x'], u['y'])
    return f"the {'green' if u['army'] == 2 else 'foe'} {class_name(unit_class(u))} at ({x}, {y})"


def person_words(u):
    """A named unit as a time or note names it: by its name, a monster's with 'the' ('the Black Beast', not 'The Wind Caller')."""
    name = D.person_shown_name(u['person'])
    cls = unit_class(u)
    return f'the {name}' if cls is not None and D.monster_size(cls) > 1 and not name.startswith('The ') else name


def _who_words(names):
    """Who enters an area, from (name, whether one of yours): 'one of your units', 'one of your units, or Jeralt,' (your units and
    someone else's), 'Byleth' or 'Hapi or Balthus' (named units alone); with a slot you fill, your named units are among your units
    (Black Market Scheme's Byleth, Hapi, Balthus and a fourth slot)."""
    names = [x if isinstance(x, tuple) else (x, x == 'one of your units') for x in names]
    names = [(n, own) for n, own in dict.fromkeys(names) if n]
    if any(n == 'one of your units' for n, _ in names):
        others = [n for n, own in names if not own]
        return 'one of your units' + (f', or {_or_words(others)},' if others else '')
    return _or_words([n for n, _ in names]) if names else 'one of your units'


def _corners(areas):
    """Areas named by their corners, for a time whose areas aren't the group's outlines: 'the area from (21, 16) to (29, 21)'."""
    rects = list(dict.fromkeys(tuple(a['rect']) for a in areas))
    return ' or '.join(f'({r[0]}, {r[1]})' if r[:2] == r[2:] else f"the area from ({r[0]}, {r[1]}) to ({r[2]}, {r[3]})"
                       for r in rects)


# The conditions of a moment (a phase's start, a unit's action ended, the battle's start): the event's trigger says them; the time
# names the phase alone.
MOMENT_LEAVES = {'IsStartOfEnemyPhase', 'IsStartOfPlayerPhase', 'StartOfTeamPhase2', 'StartOfTeamPhase', 'DidUnitsTurnEnd',
                 'IsStartOfMap', 'IsStartOfBattle', 'StartOfBattleMaybe'}
# Kinds of condition a time says the same way, so an 'or' of them is one clause ('either foe Thief at ... or ... is defeated', 'one of
# your units, or Jeralt, in the marked area'); an 'or' of different kinds is said as alternatives ('... or once ...').
# Who a team's area check names (MovedAnyUnitInRectangle: negated, the team, the rectangle).
TEAM_WHO = {0: 'one of your units', 1: 'a foe', 2: 'a green unit', 3: 'a unit of the third army'}
# The area checks of one tile.
ONE_TILE = ('MovedCharacterOnTile', 'MovedTeamIntoSpace')
FAMILY = {'MovedAnyUnitInRectangle': 'area', 'MovedSpecificUnitInRectangle': 'area', 'MovedCharacterOnTile': 'area',
          'MovedTeamIntoSpace': 'area', 'CheckDoorOpened': 'door',
          'TeamMovedIntoRangeOf': 'range', 'UnitMovedIntoRangeOf': 'range', 'DidBattle': 'battle', 'DidBAIsBattle': 'battle',
          'TurnNumber': 'turn', 'CheckLeverActivated': 'used', 'InteractedWithTerrain': 'used'}


def _family(t):
    if t[0] in ('and', 'or'):
        return None
    if _defeat(*t):
        return 'defeat'
    if t[0] == 'MovedAnyUnitInRectangle' and t[1][0]:
        return 'empty'
    if t[0] == 'MovedSpecificUnitInRectangle' and t[1][0]:
        return 'not-in-area'
    if t[0] in ONE_TILE and t[1][0]:
        return t[0]    # off a tile: no words for it
    if t[0] == 'HasOtherScriptRun':
        return 'event'
    return FAMILY.get(t[0], t[0])


def _simplify(b, t, ctx=None, standing=()):
    """A condition tree with what can be known taken out, or True or False where that decides it: a wait for an event that never runs
    (switched off, or not in the script) is False, a check that one hasn't run True, and so for an event the battle's start ran
    (`ctx['ran']`); with `ctx`, the difficulty, route and army checks (`holds`); a defeat of a unit the arrival needs standing
    (`standing`) is False, the arrival can't come after it."""
    if t[0] in ('and', 'or'):
        kids = []
        for c in t[1]:
            k = _simplify(b, c, ctx, standing)
            kids += k[1] if isinstance(k, tuple) and k[0] == t[0] else [k]
        stop, keep = (False, True) if t[0] == 'and' else (True, False)
        if stop in kids:
            return stop
        kids = [k for k in kids if k is not keep]
        if not kids:
            return keep
        return kids[0] if len(kids) == 1 else (t[0], kids)
    name, args = t
    if name == 'HasOtherScriptRun':
        if args[1] not in b.event_nums:
            return not args[2]
        if ctx is not None and args[1] in ctx.get('ran', ()):
            return bool(args[2])
    if ctx is not None and name in COURSE:
        v = holds(t, ctx)
        if v is not None:
            return v
    if standing and _defeat(name, args) and args[1] in standing:
        return False
    if ctx is not None and 'placed' in ctx and name == 'CheckDeathStatus' and args[0] and args[2] == 0 and args[1] not in ctx['placed']:
        return True    # 'not on the map with HP left' of a unit the battle doesn't place (Reclaiming the Capital's Titanus on Normal)
    return t


def _tree(x):
    """A simplified tree as a tree: True an empty 'and', a leaf one in an 'and' (None for False)."""
    if x is True:
        return ('and', [])
    if x is False:
        return None
    return x if x[0] in ('and', 'or') else ('and', [x])


def _stops(t):
    """What stops an arrival, from the checks its condition makes alongside the rest ('and' all the way up): units it needs standing,
    as [('any', slots)] (one's defeat stops it) or ('all', slots) for an 'or' of them (only all of theirs does), and the events it
    needs not to have run."""
    units, events = [], []
    if t[0] == 'and':
        for c in t[1]:
            if c[0] == 'and':
                u, ev = _stops(c)
                units += u
                events += ev
            elif c[0] == 'or':
                if c[1] and all(k[0] not in ('and', 'or') and _standing(*k) for k in c[1]):
                    units.append(('all', [k[1][1] for k in c[1]]))
            elif _standing(*c):
                units.append(('any', [c[1][1]]))
            elif c[0] == 'HasOtherScriptRun' and not c[1][2]:
                events.append(c[1][1])
    return units, events


def _body(t, top=True):
    """The tree with only what says the time: no moment, course or flag checks, no waits for earlier steps (`_chain`) and none of what
    stops it (`_stops`); True where nothing is left."""
    if t[0] not in ('and', 'or'):
        name, args = t
        if name in MOMENT_LEAVES or name in COURSE or name == 'CheckEventFlag':
            return True
        if top and (_standing(name, args) or name == 'HasOtherScriptRun'):
            return True
        if name == 'HasOtherScriptRun' and not args[2]:
            return True
        return t
    if t[0] == 'and':
        # A unit standing and in an area (Black Market Scheme's fourth slot): the area says it.
        inside = {c[1][1] for c in t[1] if c[0] == 'MovedSpecificUnitInRectangle' and not c[1][0]}
        t = ('and', [c for c in t[1] if not (c[0] not in ('and', 'or') and _standing(*c) and c[1][1] in inside)])
    if t[0] == 'or':
        leaves = [c for c in t[1] if c[0] not in ('and', 'or')]
        if len(leaves) == len(t[1]) and all(c[0] == 'HasOtherScriptRun' and c[1][2] for c in leaves):
            return True    # the routes' copies of one step: `_chain` follows them
        if top and len(leaves) == len(t[1]) and all(_standing(*c) for c in leaves):
            return True    # units of which one must stand: what stops it
    kids = [_body(c, top and t[0] == 'and') for c in t[1]]
    if t[0] == 'or' and True in kids:
        kids = [k for k in kids if k is not True]   # an alternative the time can't say: the others say it
    kids = [k for k in kids if k is not True]
    if not kids:
        return True
    return kids[0] if len(kids) == 1 else (t[0], kids)


# The conditions a time read so far has no words for (`describe`'s 'partial': a unit's note doesn't say such a time).
_UNSAID = []


def _part(b, kind, leaves, phase, at, ctx, seen, any_=False):
    """One clause of a time from conditions of one kind: {'when', 'once', 'areas', 'main'} ('main' 0-2 for one that can open the
    sentence: a turn, units in an area). `any_`: the conditions are alternatives (an 'or''s), not all needed. What it can't say goes
    in `_UNSAID`."""
    if kind == 'turn':
        # TurnNumber (negated, the turn, how it compares: 2 that turn, 3 that turn or later). An event runs once, so 'turn N or later'
        # alone comes on turn N; beside another check it waits for both ('from turn 5, ... with one of your units in the area').
        n = leaves[0][1][1]
        return {'when': f'Turn {n}' + (f', {phase}' if phase else ''), 'once': f'turn {n} has come', 'areas': [], 'main': 0,
                'from': n if leaves[0][1][2] == 3 else None}
    if kind == 'area':
        # A unit's or a team's: a rectangle (negated, the unit or team, its corners), or one tile (MovedCharacterOnTile and
        # MovedTeamIntoSpace: negated, the unit or team, the tile).
        unit = ('MovedSpecificUnitInRectangle', 'MovedCharacterOnTile')
        areas = [{'who': 'player' if (n in unit or a[1] == 0) else 'enemy',
                  'rect': gm.rect_to_app((a[2], a[3], a[2], a[3]) if n in ONE_TILE else (a[2], a[3], a[4], a[5]), b.h)}
                 for n, a in leaves]
        who = _who_words([(_unit_words(b, a[1]), b.record(a[1])['army'] == 0) if n in unit else
                          (TEAM_WHO.get(a[1], 'one of your units'), a[1] == 0) for n, a in leaves])
        return {'when': f'{at} {phase} with {who} in {{area}}' if phase else f'As soon as {who} enters {{area}}',
                'once': f'{who} has been in {{area}} {at} {phase}' if phase else f'{who} has entered {{area}}', 'areas': areas,
                'main': 1}
    if kind == 'empty':
        # Negated: none of your units there (A Harrowing Escape's first checkpoint, all your units past the first gate).
        areas = [{'who': 'player', 'rect': gm.rect_to_app((a[2], a[3], a[4], a[5]), b.h)} for _, a in leaves]
        return {'when': 'once none of your units is left in {area}', 'once': 'none of your units is left in {area}', 'areas': areas,
                'main': 2}
    words = None
    if kind == 'defeat':
        slots = list(dict.fromkeys(a[1] for _, a in leaves))
        words = _who_falls(b, 'any' if any_ and len(slots) > 1 else 'all', slots)
    elif kind == 'door':
        # CheckDoorOpened: the tile as y x 1000 + x (`0x544ec0`).
        tiles = [b.app(a[1] % 1000, a[1] // 1000) for _, a in leaves]
        words = 'the door at ' + _or_words([f'({x}, {y})' for x, y in tiles]) + ' is opened'
    elif kind == 'used':
        found = []
        for n, a in leaves:
            if n == 'CheckLeverActivated' and not a[0]:
                thing = _used(b, a[1])
                if thing and thing[1]:
                    found.append(thing[0])
                    continue
            elif n == 'InteractedWithTerrain' and a[2]:
                # (negated, the tile as y x 100 + x, whether it's been used)
                x, y = a[1] % 100, a[1] // 100
                if 0 <= x < b.w and 0 <= y < b.h:
                    ax, ay = b.app(x, y)
                    thing = D.text(5502 + b.rows[y][x][0])
                    found.append(f"the chest at ({ax}, {ay}) is opened" if thing == 'Chest' else f"the {thing} at ({ax}, {ay}) is used")
                    continue
            _UNSAID.append(n)
        words = _or_words(found) if found else None
    elif kind == 'range':
        # TeamMovedIntoRangeOf (negated, a unit, a team, a distance, how it compares: `0x547200`, a unit of the team other than it that
        # many tiles away or nearer); UnitMovedIntoRangeOf (negated, a unit, another, a distance, 1 for farther: `0x547020`).
        near = {}
        for n, a in leaves:
            if a[0]:
                _UNSAID.append(n)
                continue
            if n == 'TeamMovedIntoRangeOf' and a[2] == 0 and a[4] in (0, 1):
                who, target, tiles = ('one of your units', True), _unit_words(b, a[1]), a[3] - (a[4] == 0)
            elif n == 'UnitMovedIntoRangeOf' and not a[4]:
                who, target, tiles = (_unit_words(b, a[1]), b.record(a[1])['army'] == 0), _unit_words(b, a[2]), a[3]
            else:
                _UNSAID.append(n)   # a foe's or a green unit's range, or farther than: no words for it
                continue
            if who[0] and target:
                near.setdefault(tiles, ([], []))
                near[tiles][0].append(who)
                near[tiles][1].append(target)
            else:
                _UNSAID.append(n)
        found = [f"{_who_words(whos)} has come within {tiles} tile{'s' if tiles != 1 else ''} of {_or_words(_compress(targets))}"
                 for tiles, (whos, targets) in near.items()]
        words = _or_words(found) if found else None
    elif kind == 'battle':
        # DidBattle (360: `0x544e44`): the unit took part in the battle just fought, attacking or attacked; DidBAIsBattle (350: negated,
        # a unit, the one it fought, 300 for anyone).
        who = [_unit_words(b, a[1]) for _, a in leaves if not a[0]]
        foes = [_unit_words(b, a[2]) for n, a in leaves if not a[0] and n == 'DidBAIsBattle' and a[2] != 300]
        _UNSAID.extend(n for n, a in leaves if a[0])
        words = None
        if any(who):
            words = f'{_or_words([w for w in who if w])} has fought'
            if foes and len(foes) == len([n for n, a in leaves if not a[0] and n == 'DidBAIsBattle']):
                words += ' ' + _or_words(_compress([f for f in foes if f]))
    elif kind == 'CheckTeamSurvivors':
        found = []
        for n, a in leaves:
            if not a[0] and a[3] == 0 and a[4] in (1, 2) and a[1] in (1, 2, 3):
                found.append({1: 'every foe is defeated', 2: 'every green unit is defeated',
                              3: "every unit of the third army is defeated"}[a[1]])
            else:
                _UNSAID.append(n)
        words = _or_words(found) if found else None
    elif kind == 'CheckVariableValue':
        found = []
        for n, a in leaves:
            counted = counter_words(b, a[1])
            if counted and not a[0] and a[3] in (2, 3):
                found.append(f'{a[2]} of the {counted[0]} {counted[1]} have fallen')
            else:
                _UNSAID.append(n)
        words = _or_words(found) if found else None
    elif kind == 'event':
        # (What the events waited for can't say is theirs: their own reading adds it.)
        found = [w for w in (_event_once(b, a[1], ctx, seen) for _, a in leaves) if w]
        words = _or_words(found) if found else None
    if words is None:
        if kind != 'event':
            _UNSAID.append(kind)
        return None
    return {'when': f'once {words}', 'once': words, 'areas': [], 'main': 3}


def _event_once(b, num, ctx=None, seen=()):
    """What sets off another event, as a step before a later one ('the Magic Seal at (1, 2) is used'), its areas named by their
    corners; None where it can't be said."""
    other = next((x for x in b.events if x['num'] == num), None)
    if other is None or num in seen:
        return None
    steps, _, _ = _chain(b, other, seen, ctx)
    if not steps or steps[-1]['once'] is None or steps[-1].get('bare'):
        return None
    return steps[-1]['once'].replace('{area}', _corners(steps[-1]['areas']))


def _clause(b, t, phase, at, ctx=None, seen=()):
    """A condition tree (its `_body`) as a time: {'when', 'once', 'areas', 'rank'}, its 'and' as one sentence ('Turn 3, once Bias
    is defeated'), an 'or' of different kinds as alternatives, a turn first, then an area, its first as the time and the others as
    'or once ...' ('At the start of the enemy phase with one of your units in the marked area or once the foe Golem at (16, 15) is
    defeated'); None where nothing in it can be said."""
    if t[0] not in ('and', 'or'):
        t = ('and', [t])
    if t[0] == 'or':
        fams, alts = {}, []
        for c in t[1]:
            f = _family(c)
            if f is None:
                alts.append(('tree', c))
            else:
                fams.setdefault(f, []).append(c)
        alts = [('leaves', x) for x in fams.items()] + alts
        said = []
        for form, x in alts:
            if form == 'tree':
                c = _clause(b, x, phase, at, ctx, seen)
            else:
                p = _part(b, x[0], x[1], phase, at, ctx, seen, any_=True)
                c = _sentence([p], phase, at) if p else None
            if c is not None:
                said.append(c)
        said = [c for k, c in enumerate(said) if c['once'] not in [x['once'] for x in said[:k]]]
        if not said:
            return None
        said.sort(key=lambda c: c['rank'])
        first, rest = said[0], said[1:]
        sep = ', or once ' if ', ' in first['when'] else ' or once '
        return {'when': first['when'] + ''.join(f"{sep}{c['once']}" for c in rest),
                'once': ' or '.join(c['once'] for c in said), 'areas': [a for c in said for a in c['areas']], 'rank': first['rank']}
    fams = {}
    for c in t[1]:
        if c[0] not in ('and', 'or'):
            fams.setdefault(_family(c), []).append(c)
    parts = []
    for f, ls in sorted(fams.items(), key=lambda kv: ORDER.index(kv[0]) if kv[0] in ORDER else len(ORDER)):
        p = _part(b, f, ls[:1] if f == 'turn' else ls, phase, at, ctx, seen)
        if p:
            parts.append(p)
    for c in t[1]:
        if c[0] in ('and', 'or'):
            sub = _clause(b, c, phase, at, ctx, seen)
            if sub is not None:
                parts.append({'when': f"once {sub['once']}", 'once': sub['once'], 'areas': sub['areas'], 'main': 3})
    return _sentence(parts, phase, at)


# The order of an 'and''s clauses: a turn or an area opens the sentence, then defeats, doors and the rest.
ORDER = ['turn', 'area', 'empty', 'defeat', 'door', 'used', 'range', 'battle']


def _sentence(parts, phase, at):
    """Clauses that all hold as one time: a turn or units in an area opens it ('Turn 3, the enemy phase'), the rest follow ('...,
    once Bias is defeated'); a phase opens one that has neither ('At the start of the enemy phase, once ...')."""
    if not parts:
        return None
    parts = sorted(parts, key=lambda p: p['main'])
    since = ''
    if len(parts) > 1 and parts[0].get('from'):
        # A turn or later beside something else: that thing from the turn on.
        since, parts = f", from turn {parts[0]['from']}", parts[1:]
    whens = [parts[0]['when']] + [p['when'] if p['main'] == 3 else f"once {p['once']}" for p in parts[1:]]
    if parts[0]['main'] == 3 and phase:
        whens.insert(0, f'{at} {phase}')
    when = whens[0][0].upper() + whens[0][1:] + ''.join(', ' + w for w in whens[1:]) + since
    return {'when': when, 'once': ' and '.join(p['once'] for p in parts) + since.replace(',', ''),
            'areas': [a for p in parts for a in p['areas']], 'rank': min(p['main'] for p in parts)}


def _step(b, e, ctx=None, standing=(), seen=()):
    """One event's own condition (the events it waits for aside): {'when', 'once', 'areas', 'flags', 'stops'}, 'when' None where it
    adds nothing to its time. 'when' says it as the arrival's time, 'once' as a step before a later one; 'stops' are what it checks
    that would stop it (`_stops`). `standing`: units the arrival needs standing, whose defeat as an alternative can't lead to it."""
    t = _tree(_simplify(b, e['conditions'], ctx, standing))
    if t is None:
        return {'when': None, 'once': None, 'areas': [], 'flags': [], 'stops': ([], [])}
    phase = PHASE.get(e['trigger'][0])
    # StartOfTeamPhase (400, the 18000 events') tests another moment than a phase's start (the flags word's bit 12, fired by `0x18bf00`;
    # a phase's start is bit 7, `0x189e24`, which IsStartOfEnemyPhase and StartOfTeamPhase2 test): said as during the phase (README).
    at = 'at the start of'
    flags = []
    for name, args in _flat(t):
        if name == 'IsStartOfEnemyPhase':
            phase = 'the enemy phase'
        elif name == 'IsStartOfPlayerPhase':
            phase = 'your phase'
        elif name in ('StartOfTeamPhase2', 'StartOfTeamPhase') and not args[0] and args[1] in TEAM_PHASE:
            phase = TEAM_PHASE[args[1]]
            if name == 'StartOfTeamPhase':
                at = 'during'
        elif name == 'CheckEventFlag':
            # (negated, the flag, the value it's checked for): whether the event wants the flag set.
            flags.append((args[1], bool(args[2]) != bool(args[0])))
    stops = _stops(t)
    body = _body(t)
    c = None if body is True else _clause(b, body, phase, at, ctx, seen + (e['num'],))
    if c is None:
        if e['trigger'][0] in START_TRIGGERS or not phase:
            return {'when': None, 'once': None, 'areas': [], 'flags': flags, 'stops': stops}
        c = {'when': f'{at[0].upper()}{at[1:]} {phase}', 'once': f'{phase} has begun' if at == 'at the start of' else
             f'{phase} has come', 'areas': [], 'bare': True}
    return {'when': c['when'], 'once': c['once'], 'areas': c['areas'], 'flags': flags, 'stops': stops, 'bare': c.get('bare', False)}


def _root(t):
    """A condition tree without the single-child 'and's around it."""
    while t[0] == 'and' and len(t[1]) == 1 and t[1][0][0] in ('and', 'or'):
        t = t[1][0]
    return t


# Trigger kinds whose events run as a phase starts or ends, and the condition of a moment none of them runs at: each moment's own
# condition is found only under its kinds (IsStartOfEnemyPhase under 13999 and 14000, StartOfTeamPhase under 17999 and 18000,
# DidUnitsTurnEnd, a unit's action ended, under 1999 and 2000), but in one branch of The Great Bridge Coup's Acheron event (README).
PHASE_KINDS = {12999, 13000, 13999, 14000, 17999, 18000}
ACTION_MOMENT = 'DidUnitsTurnEnd'


def _pruned(e):
    """The event as its trigger lets it hold: of an 'or' at the root of its conditions, a branch that tests a moment the event never
    runs at is left out (The Great Bridge Coup's Acheron event, a phase start's: its other branch, after Ladislava's defeat or a
    battle with Ferdinand, wants a unit's action just ended)."""
    t = _root(e['conditions'])
    if t[0] != 'or' or e['trigger'][0] not in PHASE_KINDS:
        return e
    keep = [c for c in t[1] if ACTION_MOMENT not in {n for n, _ in _flat(c)}]
    if not keep or len(keep) == len(t[1]):
        return e
    return dict(e, conditions=('and', [('or', keep)] if len(keep) > 1 else [keep[0]]))


def _waits(t, alt=False):
    """The events a condition tree waits for (HasOtherScriptRun), as (event, whether only as one alternative: an 'or' above it that
    also checks something else, a defeat or an area; an 'or' of waits alone is the routes' copies of one step, Chapter 10's)."""
    if t[0] not in ('and', 'or'):
        name, args = t
        return [(args[1], alt)] if name == 'HasOtherScriptRun' and args[2] else []
    real = t[0] == 'or' and any(n not in COURSE and n != 'HasOtherScriptRun' for c in t[1] for n, _ in _flat(c))
    out = []
    for c in t[1]:
        out += _waits(c, alt or real)
    return out


def _only_defeats(t):
    """The defeats a condition tree checks, where it checks nothing else (None otherwise)."""
    leaves = _flat(t)
    if leaves and all(_defeat(n, a) for n, a in leaves):
        return [a[1] for _, a in leaves]
    return None


def _inline(t, trees):
    """The tree with each wait for an event in `trees` (one that checks nothing but defeats) as that event's own condition."""
    if t[0] in ('and', 'or'):
        return (t[0], [_inline(c, trees) for c in t[1]])
    name, args = t
    if name == 'HasOtherScriptRun' and args[2] and args[1] in trees:
        return trees[args[1]]
    return t


def _wait_groups(t):
    """The events a tree waits for as earlier steps: each it needs alongside the rest a group of one, an 'or' of waits alone a group of
    alternatives (the routes' copies of one step, or two ways to one: Ambush in the Arena's waves, each at an enemy phase from turn 4
    or once every foe is defeated). A wait under an 'or' that also checks something else is an alternative of this step (`_clause`)."""
    if t[0] not in ('and', 'or'):
        return [[t[1][1]]] if t[0] == 'HasOtherScriptRun' and t[1][2] else []
    if t[0] == 'or':
        if all(c[0] == 'HasOtherScriptRun' and c[1][2] for c in t[1]):
            return [[c[1][1] for c in t[1]]]
        return []
    out = []
    for c in t[1]:
        out += _wait_groups(c)
    return out


def _composed(steps):
    """A chain of steps as one ('At the start of the enemy phase, once one of your units has entered the marked areas'), a step that
    names a phase alone said only where nothing else is."""
    last, before = steps[-1], steps[:-1]
    said = [x for x in steps if not x.get('bare')] or steps[-1:]
    return {'when': last['when'] + ''.join(f", once {x['once']}" for x in reversed(before)),
            'once': ' and '.join(x['once'] for x in said), 'areas': [a for x in steps for a in x['areas']], 'flags': [],
            'stops': ([], []), 'bare': all(x.get('bare') for x in steps)}


def _joined(steps_list, word):
    """Several ways to a time ('or'), or several things it needs ('and'), as one step: each way's chain said whole ('Turn 4, the enemy
    phase, or once every foe is defeated'; 'At the start of the enemy phase, once one of your units has entered the marked areas, or
    once Sylvain is defeated'). One way alone keeps its steps (areas numbered by step)."""
    ways = []
    for steps in steps_list:
        if _alike(steps[-1]['once']) not in [_alike(x[-1]['once']) for x in ways]:
            ways.append(steps)
    # A way that names a phase alone (an event of a phase's start that checks nothing else) joins nothing a way that says more.
    if any(not all(x.get('bare') for x in w) for w in ways):
        ways = [w for w in ways if not all(x.get('bare') for x in w)]
    else:
        ways = ways[:1]
    if len(ways) == 1:
        return ways[0]
    steps = [_composed(w) for w in ways]
    first = steps[0]
    sep = (', or once ' if ', ' in first['when'] else ' or once ') if word == 'or' else ', once '
    return [{'when': first['when'] + ''.join(sep + x['once'] for x in steps[1:]),
             'once': f' {word} '.join(x['once'] for x in steps), 'areas': [a for x in steps for a in x['areas']], 'flags': [],
             'stops': ([], []), 'bare': False}]


def _chain(b, e, seen=(), ctx=None, standing=None):
    """The steps an event's arrival waits on, earliest first, each its own condition (`_step`), with the event flags and what stops
    it: an event waits for another (HasOtherScriptRun) that ran before it. Events at the battle's start lend only their flags; of
    several alternatives (an 'or' of waits) each that says something is said ('..., or once ...'), the routes' copies of one event
    once; several it needs are said together; an event that waits for the arrival of units whose defeat it checks needs nothing more
    said. An event checked only as one alternative of an 'or' isn't a step before it but one of its alternatives (`_clause`); one that
    checks nothing but defeats (Saving Derdriu: either of Hilda's two records; Crimson Flower's Chapter 12: Flayn's, Seteth's and
    Gilbert's) is said by those defeats. A unit the arrival needs standing (`_stops`) makes its defeat, as an earlier step's
    alternative, one that can't lead to it (Capturing Derdriu: turn 4 or Nader's defeat, then only while Nader stands); an earlier
    step that checks nothing but who stands runs at once, and what it checks then stops nothing."""
    e = _pruned(e)
    t = _tree(_simplify(b, e['conditions'], ctx))
    if t is None:
        return [], [], ([], [])
    trees = {}
    ways = {n for group in _wait_groups(t) if len(group) > 1 for n in group}
    for num, _ in _waits(t):
        other = next((x for x in b.events if x['num'] == num), None)
        if other is None or num in seen or num in ways:
            continue
        ot = _tree(_simplify(b, other['conditions'], ctx))
        if ot is not None and ot[1] and _only_defeats(ot):
            trees[num] = ot
    if trees:
        t = _tree(_simplify(b, _inline(t, trees), ctx))
    if t is not None and standing is None:
        standing = tuple(x for _, slots in _stops(t)[0] for x in slots)
    t = _tree(_simplify(b, t, ctx, standing)) if t is not None else None
    if t is None:
        return [], [], ([], [])
    e = dict(e, conditions=t)
    me = _step(b, e, ctx, standing, seen)
    units, events = me['stops']
    groups = _wait_groups(t)
    if seen and me['when'] is None and not groups:
        units, events = [], []
    dead = {x for _, slots in _deaths(t) for x in slots}
    flags, befores = [], []
    for group in groups:
        ways = []
        for num in dict.fromkeys(group):
            other = next((x for x in b.events if x['num'] == num), None)
            if other is None or num in seen:
                continue
            if dead & {a[1][0] for a in other['actions'] if a[0] in SPAWNS}:
                continue
            sub, sub_flags, (sub_units, sub_events) = _chain(b, other, seen + (e['num'],), ctx, standing)
            flags += sub_flags
            units, events = units + sub_units, events + sub_events
            if sub:
                ways.append(sub)
        if ways:
            befores.append(_joined(ways, 'or'))
    steps = _joined(befores, 'and') if befores else []
    flags += me['flags']
    if me['when'] is not None:
        steps = steps + [me]
    return steps, flags, (units, events)


def _compress(words):
    """'the Magic Seal at (1, 2) is used or the Magic Seal at (10, 1) is used' as 'the Magic Seal at (1, 2) or (10, 1) is used'."""
    out = []
    for w in dict.fromkeys(words):
        head, sep, rest = w.partition(' at (')
        tile, close, tail = rest.partition(')')
        prev = out[-1] if out else None
        if sep and close and prev and prev[0] == head and prev[2] == tail:
            prev[1].append(f'({tile})')
        else:
            out.append([head, [f'({tile})'] if sep and close else [], tail if sep and close else w])
    return [f"{h} at {_or_words(tiles)}{t}" if tiles else t for h, tiles, t in out]


def _brings(b, ev):
    """The units an event brings onto the map: those it spawns, and those of the script's own it walks in (`reinforcements`)."""
    return {a[1][0] for a in ev['actions'] if a[0] in SPAWNS or (a[0] == 'Walk' and b.record(a[1][0])['scripted'])}


def _after(b, num):
    """An event and every event that waits for it, all the way on."""
    if num not in b.after:
        out, todo = set(), [num]
        while todo:
            n = todo.pop()
            if n in out:
                continue
            out.add(n)
            todo += [x['num'] for x in b.events if any(nm == 'HasOtherScriptRun' and a[2] and a[1] == n
                                                       for nm, a in _flat(x['conditions']))]
        b.after[num] = out
    return b.after[num]


def _leads_to(b, num):
    """The units an event brings, and those of every event that waits for it, all the way on."""
    return {u for n in _after(b, num) for ev in b.events if ev['num'] == n for u in _brings(b, ev)}


def _before(b, num):
    """An event and every event it waits for, all the way back."""
    out, todo = set(), [num]
    while todo:
        n = todo.pop()
        if n in out:
            continue
        out.add(n)
        ev = next((x for x in b.events if x['num'] == n), None)
        if ev is not None:
            todo += [a[1] for nm, a in _flat(ev['conditions']) if nm == 'HasOtherScriptRun' and a[2]]
    return out


def _course_free(t):
    """A condition tree as a key, its difficulty, route and army checks left out: the same event for another difficulty or route."""
    if t[0] in ('and', 'or'):
        kids = [k for k in (_course_free(c) for c in t[1]) if k is not None]
        return json.dumps([t[0], kids])
    return None if t[0] in COURSE else json.dumps(t)


def _alike(words):
    """A time's words as what they name, whatever their order ('turn 4 has come or every foe is defeated')."""
    return frozenset(re.split(r' or | and |, ', words))


def _stop_words(b, e, stops, ctx=None, own=()):
    """What stops an arrival, in words ('Simone is defeated or the Magic Seal at (1, 2) or (10, 1) is used'), or None: a unit it needs
    standing (not one of yours), and another event it needs not to have run, said by what sets that event off (Search for the Chalice's
    Golems: a Magic Seal's group). An event that leads to placing any of the same units (another way in for the group, said as its
    own time: the routes' and difficulties' copies, an earlier wave), one that in turn needs this arrival not to have come (two ways
    the chapter can go: Protecting Garreg Mach's groups, each the first of several to come), one that ends the battle, sets off as
    the arrival does (`own`) or at a phase alone, or can't be said, is left out."""
    units, events = stops
    anys = [x for kind, slots in units if kind == 'any' for x in slots]
    groups = [list(slots) for kind, slots in units if kind == 'all' and not set(slots) & set(anys)]
    words = []
    for kind, slots in [('any', anys)] + [('all', g) for g in groups]:
        slots = [x for x in dict.fromkeys(slots) if b.record(x)['army'] not in (0, NO_ARMY)]
        if slots:
            words.append(_who_falls(b, 'all' if kind == 'all' and len(slots) > 1 else 'any', slots))
    mine = _brings(b, e)
    ends = b.ends()
    related = _before(b, e['num']) | _after(b, e['num'])
    key = _course_free(e['conditions'])
    for x in b.events:
        if _course_free(x['conditions']) == key:
            related |= _after(b, x['num'])     # the same event for another difficulty or route
    own = [_alike(w) for w in own]
    for num in dict.fromkeys(events):
        if num in ends or num == e['num'] or mine & _leads_to(b, num):
            continue
        other = next((x for x in b.events if x['num'] == num), None)
        if other is None or any(n == 'HasOtherScriptRun' and not a[2] and a[1] in related for n, a in _flat(other['conditions'])):
            continue    # each needs the other not to have run: two ways the chapter can go, each said as its own group's time
        w = _event_once(b, num, ctx, (e['num'],))
        if w and _alike(w) not in own:
            words.append(w)
    return _or_words(_compress(words)) if words else None


def describe(b, e, ctx=None, corners=False):
    """When an event's units arrive: {'text', 'areas', 'flags'}, or None where nothing can be read. A chain of events reads from its
    last step back ('At the start of the enemy phase with one of your units in area 2, once one of your units has been in area 1 at
    the start of your phase'), its areas numbered by step where more than one step has some; 'unless', what stops it ('Simone is
    defeated', `_stop_words`); 'partial', whether it checks something it has no words for (`_UNSAID`). `ctx`: the difficulty, route and army it's read for ({'diff', 'routes', 'recruited', 'ran'})."""
    del _UNSAID[:]
    steps, flags, stops = _chain(b, e, ctx=ctx)
    partial = bool(_UNSAID)
    unless = _stop_words(b, e, stops, ctx, [x['once'].replace('{area}', _corners(x['areas'])) for x in steps])
    # A step that says what a later one does (Chapter 5: a scene, then the units' walks, then the Black Beast, each once Miklan is
    # defeated) is said once.
    keep, seen = [], set()
    for s in reversed(steps):
        key = (_alike(s['once']), json.dumps(s['areas'], sort_keys=True))
        if key not in seen:
            seen.add(key)
            keep.append(s)
    steps = keep[::-1]
    if not steps:
        # An event of the battle's start that the start couldn't run waits on something the map can't know there (an event flag:
        # Chapter 4's groups, the Enbarr Infiltration's Death Knight); a check after each action (2000) that waits on a count or a
        # choice comes after an event in the chapter.
        leaves = {n for n, _ in _flat(e['conditions'])}
        if e['trigger'][0] in START_TRIGGERS and (e['trigger'][0] not in (1999, 2000) or leaves & START_LEAVES):
            return {'text': 'At the start of the battle', 'areas': [], 'flags': flags, 'unless': unless, 'once': None,
                    'partial': partial}
        return {'text': 'After an event in the chapter', 'areas': [], 'flags': flags, 'unless': unless, 'once': None,
                'partial': partial}
    with_areas = [s for s in steps if s['areas']]
    numbered = len(with_areas) > 1
    areas = []
    for k, s in enumerate(with_areas, 1):
        name = f'area {k}' if numbered else ('the marked areas' if len(s['areas']) > 1 else 'the marked area')
        if corners:
            name = _corners(s['areas'])
        s['when'] = s['when'].replace('{area}', name)
        s['once'] = s['once'].replace('{area}', name)
        areas += [{**a, 'step': k} if numbered else a for a in s['areas']]
    last, before = steps[-1], [s for s in steps[:-1] if not s.get('bare')]
    text = last['when'] + ''.join(f', once {s["once"]}' for s in reversed(before))
    once = last['once'] + ''.join(f', once {s["once"]}' for s in reversed(before))
    return {'text': text, 'areas': list({json.dumps(a, sort_keys=True): a for a in areas}.values()), 'flags': flags,
            'unless': unless, 'once': None if last.get('bare') and not before else once, 'partial': partial}


def when_text(w):
    """An arrival's time as the map says it (`describe`): the time, the event flags it needs, then what stops it ('Turn 3, the enemy
    phase, unless Simone is defeated first')."""
    if not w:
        return 'After an event in the chapter'
    return w['text'] + ''.join(', ' + f for f in flag_words(w['flags'])) + (f", unless {w['unless']} first" if w['unless'] else '')


def plural(name):
    if name.endswith('Hero'):
        return name + 'es'   # Heroes
    if name.endswith('y') and name[-2:-1] not in ('a', 'e', 'o', 'u'):
        return name[:-1] + 'ies'   # Mercenaries
    return name[:-1] + 'ves' if name.endswith('f') else name + 'es' if name.endswith(('s', 'sh', 'ch')) else name + 's'


def flag_words(flags):
    """What an event flag the battle tests means, where it's traced (data-raw/fe16/README.md)."""
    out = []
    for flag, wanted in dict.fromkeys(flags):
        what = FLAGS.get(flag, f'event flag {flag}')
        out.append(f'if {what}' if wanted else f'unless {what}')
    return out


def reinforcements(b, victory, joiners=None):
    """Groups from the events after the start that place units, per difficulty and merged (gba_maps.one_per_arrival). Units of yours
    an event brings in (Chapter 13's students, back for the reunion) go in `joiners` instead ({event: [joiner]}, from Normal's run)."""
    groups = []
    ends = end_events(b)
    spawned = {a[1][0] for e in b.events for a in e['actions'] if a[0] in SPAWNS}
    for d, dname in enumerate(b.diffs):
        placed, ran = b.start(d)
        on_map = b.on_map(d)
        # The start's reinforcement points: a copy each turn, every other turn or every third turn, from turn 1.
        for slot, tile in b.points.items():
            r = b.record(slot)
            u, inv = unit_entry(b, slot, tile, d, victory)
            u['difficulties'] = [dname]
            when = repeat_words(r['rank'], None) + point_until(b, slot, ends, {'diff': d, 'routes': b.house[3], 'recruited': b.army})
            groups.append({'_event': ('point', r['rank'], when), 'when': {dname: when}, 'units': [u], '_inv': {dname: [(u, inv)]}})
        for e in b.events:
            if e['num'] in ran or e['num'] in ends:
                continue
            # What the event places, where: a spawn at the record's own tile (SpawnUnit walks it in from its own tile), SpawnSpooky at the
            # action's tile (`SPAWNS`: Acheron in The Great Bridge Coup); a Walk of a unit not on the map brings it in to where the walk
            # ends (Chapter 5's Black Beast, on Miklan's tile once he falls).
            at, entry = {}, {}
            for name, args in e['actions']:
                if name in ('SpawnUnit', 'SpawnUnit130') and args[0] not in placed:
                    r = b.record(args[0])
                    at.setdefault(args[0], (r['x'], r['y']))
                    if name == 'SpawnUnit':
                        entry.setdefault(args[0], (args[1], args[2]))
                elif name == 'SpawnSpooky' and args[0] not in placed:
                    at.setdefault(args[0], (args[1], args[2]))
                elif name == 'Walk' and args[0] not in placed and args[0] not in spawned and b.record(args[0])['scripted']:
                    at.setdefault(args[0], (args[1], args[2]))
            if not at:
                continue
            ctx = {'diff': d, 'routes': b.house[3], 'recruited': b.army}
            # A student another house's: the event runs only if you recruited them (`ROUTE_ARMY` holds your own).
            extra = list(dict.fromkeys(a[1] for n, a in _flat(e['conditions']) if n == 'IsRecruited' and a[1] not in b.army))
            only_if = []
            if on_course(e['conditions'], ctx) is False:
                if not extra or on_course(e['conditions'], dict(ctx, recruited=tuple(b.army) + tuple(extra))) is False:
                    continue
                only_if = extra
            w = describe(b, e, dict(ctx, recruited=tuple(b.army) + tuple(extra), ran=ran, placed=on_map))
            if joiners is not None and d == 0:
                for slot, tile in at.items():
                    r = b.record(slot)
                    if r['army'] != 0 or r['person'] is None:
                        continue
                    j = {'name': D.person_shown_name(r['person']), 'tile': b.app(*tile), 'from': b.app(*entry.get(slot, tile)),
                         'group': f"j{e['num']}", 'when': when_text(w)}
                    if w and w['areas']:
                        j['areas'] = w['areas']
                    if only_if:
                        j['note'] = 'If ' + ' and '.join(D.person_shown_name(p) for p in only_if) +                             (' is' if len(only_if) == 1 else ' are') + ' in your army'
                    joiners.setdefault(e['num'], []).append(j)
            if only_if:
                continue   # a foe an army without that student meets instead stands in for them (`standIn`), not as an arrival
            units = []
            for slot, tile in at.items():
                r = b.record(slot)
                if r['army'] in (0, NO_ARMY):
                    continue
                u, inv = unit_entry(b, slot, tile, d, victory, came=e['num'])
                u['difficulties'] = [dname]
                if b.is_point(slot):
                    # A reinforcement point the event places: its copies come from then on.
                    when = repeat_words(r['rank'], w['text'] if w else 'After an event in the chapter') + point_until(b, slot, ends, ctx)
                    g = {'_event': ('point', r['rank'], e['num']), 'when': {dname: when}, 'units': [u], '_inv': {dname: [(u, inv)]}}
                    if w and w['areas']:
                        g['areas'] = w['areas']
                    groups.append(g)
                    continue
                units.append((u, inv))
            if not units:
                continue
            when = when_text(w)
            g = {'_event': e['num'], 'when': {dname: when}, 'units': [u for u, _ in units], '_inv': {dname: units}}
            if w and w['areas']:
                g['areas'] = w['areas']
            groups.append(g)
    invs = [(g.pop('_inv'), g['_event']) for g in groups]
    merged = gm.one_per_arrival(groups, b.diffs)
    for g in merged:
        g['when'] = {d: _counted(w) for d, w in g['when'].items()} if isinstance(g.get('when'), dict) else _counted(g.get('when'))
    return merged, invs


def _counted(when):
    """A merged time whose events read alike (each of Search for the Chalice's Golems once the one before it on that tile falls) says
    it once, with how many times: '...; at the start of the enemy phase, once the foe Golem at (6, 2) is defeated (3 times)'."""
    if not isinstance(when, str):
        return when
    parts = when.split('; ')
    # What stops every one of them (Search for the Chalice's Golems: Simone's defeat, a Magic Seal used) is said once, at the end.
    tails = {p[p.index(', unless '):] if ', unless ' in p else '' for p in parts}
    tail = tails.pop() if len(parts) > 1 and len(tails) == 1 else ''
    parts = [p[:len(p) - len(tail)] for p in parts]
    count = {p: parts.count(p) for p in dict.fromkeys(parts)}
    return '; '.join(p if k == 1 else f'{p} ({k} times)' for p, k in count.items()) + tail


def objectives(b, victory, defeat):
    """The tiles the opening marks blue (MakeMapTilesBlue: a rectangle and whether to mark or clear it) where the battle's conditions
    name them: the defended locations a foe takes to win (Chapters 12 and 14, Insurmountable...), or the target destination a unit
    reaches (Rumored Nuptials' Ingrid, Foreign Land and Sky's Petra). The script marks other tiles blue too (Fort Merceus' gates, the
    onager Protecting Garreg Mach's Church Soldier makes for), which no condition names: those aren't objectives."""
    _, ran = b.start(0)
    rects = []
    for e in b.events:
        if e['num'] in ran:
            rects += [a[:4] for n, a in e['actions'] if n == 'MakeMapTilesBlue' and a[4]]
    if 'defended location' in defeat:
        kind, label = 'defend', 'Defended location (the enemy wins by reaching it)'
    elif 'target destination' in victory:
        who = victory.split(' get ')[-1].split(' to the target')[0] if ' get ' in victory else 'your units'
        kind, label = 'arrive', f"Target destination ({'all your units' if who.startswith('all of your units') else who})"
    else:
        return []
    out = []
    for x1, y1, x2, y2 in dict.fromkeys(rects):
        tiles = [b.app(x, y) for y in range(min(y1, y2), max(y1, y2) + 1) for x in range(min(x1, x2), max(x1, x2) + 1)]
        out.append({'type': kind, 'tiles': tiles, 'label': label})
    return out


def repeat_words(rank, first):
    """When a reinforcement point's copies come: from turn 1 ('Turn 1 and every other turn after'), or from the event that places it
    ('Turn 2, then every third turn after')."""
    every = POINT_EVERY[rank]
    if first is None:
        return 'Every turn' if every == 1 else f"Turn 1 and every {'other' if every == 2 else 'third'} turn after"
    return f"{first}, then every {'turn' if every == 1 else 'other turn' if every == 2 else 'third turn'} after"


def point_until(b, slot, ends, ctx):
    """What stops a reinforcement point: the events that take it off the map on this difficulty and route. One that waits only for
    another unit's defeat says whose ('until the foe Wyvern Lord at (30, 26) is defeated', Insurmountable); one that hangs on the
    chapter's other events (Protecting Garreg Mach's fire attack) is 'an event in the chapter'."""
    words, other = [], False
    for e in b.events:
        if e['num'] in ends or not any(n == 'RemoveFromMap' and a[0] == slot for n, a in e['actions']):
            continue
        if on_course(e['conditions'], ctx) is False:
            continue
        waits = any(n == 'HasOtherScriptRun' and a[2] for n, a in _flat(e['conditions']))
        deaths = [x for _, slots in _deaths(e['conditions']) for x in slots]
        if not waits and deaths and slot not in deaths:
            step = _step(b, e)
            # The group's own outlines are the areas that bring it in, so an area that stops it is said by its corners (Sword and
            # Shield of Seiros: 'one of your units has entered the area from (21, 16) to (29, 21) or the foe Brigand ... is defeated').
            rects = [a['rect'] for a in step['areas']]
            where = ' or '.join(f'the area from ({r[0]}, {r[1]}) to ({r[2]}, {r[3]})' for r in rects)
            words.append(step['once'].replace('{area}', where))
        else:
            other = True
    if other:
        words.append('an event in the chapter stops them')
    return (', until ' + ' or '.join(dict.fromkeys(words))) if words else ''


def looting(b):
    """Units the script sends to take something from the map's tiles, then off the map: Chapter 11's Thieves and Brigands and the Crest
    Stones in the Holy Tomb's walls. MoveToRectangleAI580 sends a unit to work in an area; once the tiles it's after are taken
    (InteractedWithTerrain, the tile as y * 100 + x) MoveToRectangleAI sends it to one tile, and standing there (MovedCharacterOnTile)
    takes it off the map (RemoveFromMap) and adds to a count (IncrementVariable: the count, by how many). {slot: {'tiles', 'exit',
    'count', 'adds', 'thing'}}, the thing named by its tiles' terrain ('Crest Stone')."""
    out = {}
    for e in b.events:
        for name, args in e['actions']:
            if name == 'MoveToRectangleAI580':
                out.setdefault(args[0], {})
    for e in b.events:
        tiles = [a[1] for n, a in _flat(e['conditions']) if n == 'InteractedWithTerrain' and a[2]]
        for name, args in e['actions']:
            if name == 'MoveToRectangleAI' and args[0] in out and tiles and (args[1], args[2]) == (args[3], args[4]):
                out[args[0]].update(tiles=[(t % 100, t // 100) for t in tiles], exit=(args[1], args[2]))
    for e in b.events:
        on = [a for n, a in _flat(e['conditions']) if n == 'MovedCharacterOnTile' and a[1] in out]
        if on and any(a[0] == 'RemoveFromMap' and a[1][0] == on[0][1] for a in e['actions']):
            for name, args in e['actions']:
                if name == 'IncrementVariable':
                    out[on[0][1]].update(count=args[0], adds=args[1])
    out = {k: v for k, v in out.items() if 'tiles' in v}
    for v in out.values():
        kinds = {b.rows[y][x][0] for x, y in v['tiles']}
        assert len(kinds) == 1, kinds
        v['thing'] = D.text(5502 + kinds.pop())
        # What it adds to a count is how many of the tiles it takes: the count is of the things carried off (Chapter 11's Crest Stones;
        # a thief after a chest keeps no count).
        assert 'adds' not in v or v['adds'] == len(v['tiles']), v
    return out


def reward_words(b, e):
    """When a gift the battle's end gives holds: its checks on a count the script keeps ('if none of the 5 green Commoners fall'), on
    how many allies survive, or 'on a count the battle keeps' where the count is more than that; '' where it always holds."""
    t = e['conditions']
    vars_ = list(dict.fromkeys(a[1] for n, a in _flat(t) if n == 'CheckVariableValue'))
    out = []
    for var in vars_:
        values = check_range(t, var)
        counted = counter_words(b, var)
        if values is not None and counted:
            n, what = counted
            words = range_words(values, n)
            if words:
                verb = 'falls' if words == '1' else 'fall'
                out.append(f'if {words} of the {n} {what} {verb}' if words != 'none' else f'if none of the {n} {what} fall')
                continue
        out.append('on a count the battle keeps')
    survivors = survivor_words(t)
    if survivors:
        out.append(survivors)
    return ', '.join(dict.fromkeys(out))


def count_words(conds, var, thing, total):
    """A gift's checks on a looting count, in words ('if no Crest Stone is carried off the map', 'if 1 to 10 Crest Stones are ...').
    CheckVariableValue: (negated, the count, a value, how it compares: 0 <, 1 <=, 2 ==, 3 >=, 4 >)."""
    lo, hi = 0, total
    for name, args in conds:
        if name != 'CheckVariableValue' or args[1] != var:
            continue
        assert not args[0], args
        v, cmp = args[2], args[3]
        if cmp == 2:
            lo = hi = v
        elif cmp in (0, 1):
            hi = min(hi, v - (cmp == 0))
        else:
            lo = max(lo, v + (cmp == 4))
    things = plural(thing)
    if hi == 0:
        return f'if no {thing} is carried off the map'
    if lo == hi:
        return f'if all {total} {things} are carried off the map' if lo == total else f'if {lo} {things} are carried off the map'
    if hi == total:
        return f'if {lo} or more {things} are carried off the map'
    return f'if {lo} to {hi} {things} are carried off the map'


def counter_words(b, var):
    """What a count the battle's script keeps counts, where every event that adds to it waits only on one unit's defeat (True
    Chivalry's villagers): 'of the 5 Commoners (green) that fall'; None where it counts more than that."""
    slots = []
    for e in b.events:
        for name, args in e['actions']:
            if name != 'IncrementVariable' or args[0] != var:
                continue
            leaves = [x for x in _flat(e['conditions']) if x[0] != 'HasOtherScriptRun']
            if len(leaves) != 1 or not _defeat(*leaves[0]) or args[1] != 1:
                return None
            slots.append(leaves[0][1][1])
    if not slots:
        return None
    units = [b.record(x) for x in slots]
    armies = {u['army'] for u in units}
    if len(armies) != 1:
        return None
    side = {1: 'foe ', 2: 'green ', 3: 'third army '}.get(armies.pop(), '')
    names = [D.person_shown_name(u['person']) if is_person(u) else
             class_name(unit_class(u)) for u in units]
    if len(set(names)) == 1:
        return len(slots), f'{side}{plural(names[0])}'
    # Of different kinds (Chapter 3's Catherine and two Myrmidons): named, as many of each.
    count = {n: names.count(n) for n in dict.fromkeys(names)}
    parts = [n if k == 1 else f'{k} {plural(n)}' for n, k in count.items()]
    return len(slots), f"{side}units ({', '.join(parts[:-1])} and {parts[-1]})"


def check_range(t, var):
    """The values of a count a condition tree accepts, as a set (CheckVariableValue: negated, the count, a value, how it compares:
    0 <, 1 <=, 2 ==, 3 >=, 4 >; an 'or' of them joins their sets), or None where it doesn't check the count."""
    if t[0] in ('and', 'or'):
        sets = [x for x in (check_range(c, var) for c in t[1]) if x is not None]
        if not sets:
            return None
        out = set(sets[0])
        for x in sets[1:]:
            out = out | x if t[0] == 'or' else out & x
        return out
    name, args = t
    if name != 'CheckVariableValue' or args[1] != var or args[0]:
        return None
    v, cmp = args[2], args[3]
    return {n for n in range(0, 100) if [n < v, n <= v, n == v, n >= v, n > v][cmp]}


def range_words(values, top):
    """'none', '1 or 2', '3 to 5', 'all 5'."""
    vals = sorted(n for n in values if n <= top)
    if not vals:
        return None
    lo, hi = vals[0], vals[-1]
    if hi == 0:
        return 'none'
    if lo == hi:
        return f'all {top}' if lo == top else str(lo)
    if hi == top and lo > 0:
        return f'{lo} or more'
    return f'{lo} or {hi}' if hi == lo + 1 else f'{lo} to {hi}'


def survivor_words(t):
    """A reward's check on how many of a team are left (CheckTeamSurvivors: negated, the team, -, a number, how it compares): 'if at
    least 4 green units survive'."""
    for name, args in _flat(t):
        if name == 'CheckTeamSurvivors' and not args[0] and args[1] in (0, 2):
            n, cmp = args[3], args[4]
            who = 'of your units' if args[1] == 0 else 'green units'
            word = {3: f'at least {n}', 4: f'more than {n}', 2: f'exactly {n}', 1: f'at most {n}', 0: f'fewer than {n}'}[cmp]
            return f'if {word} {who} survive'
    return None


def defeat_text(b, house):
    """The battle's lose condition, the route's own (`DEFEAT_FIELD`: the Black Eagles' house plays Silver Snow's until the routes
    part; Crimson Flower's falls back on it where it has none). A battle every house plays alike says it once for all three, the leader
    as 'your house leader (Edelgard, Dimitri or Claude)'."""
    texts = [clean(D.text(11906 + b.scen['raw'][41 + k])) for k in range(3)]
    if house is not None:
        v = b.scen['raw'][DEFEAT_FIELD[house[3][0]]] or b.scen['raw'][41]
        return clean(D.text(11906 + v))
    forms = {t.replace(LORDS[2 + k], '{lord}') for k, t in enumerate(texts)}
    assert len(forms) == 1, texts
    return forms.pop().replace('{lord}', 'your house leader (Edelgard, Dimitri or Claude)')


def shared_check(s):
    """A battle every house plays alike is one map: each house's start and arrivals are the same but for its leader (`LORDS`), who
    stands on the same tile."""
    seen = []
    for house in HOUSES:
        b = Battle(s, house)
        starts = []
        for d in range(len(DIFFS)):
            placed, _ = b.start(d)
            starts.append(sorted((-1 if b.record(slot)['person'] in LORDS and b.record(slot)['army'] == 0 else slot, tile)
                                 for slot, tile in placed.items()))
        rein, _ = reinforcements(b, b.scen['victory'])
        groups = sorted(json.dumps([g.get('when'), g.get('areas'), sorted(json.dumps(u, sort_keys=True) for u in g['units'])])
                        for g in rein)
        seen.append((json.dumps(starts), json.dumps(groups)))
    assert len(set(seen)) == 1, f'chapter {s} differs by house beyond its leader'


# The auxiliary battles (scenarios 61-85, the free days' Battle menu; 81-85 the Expansion Pass's): which part of the game offers each,
# from Fire Emblem Wiki's list of auxiliary battle maps by location (the days the game offers each on aren't traced: README). 'I' Part I
# only, 'II' Part II only, both otherwise. The battles fought against monsters alone are where rare monsters are sighted.
AUX = range(61, 86)
AUX_PART = {61: 'I', 72: 'II', 73: 'II', 74: 'II', 75: 'II', 76: 'II', 77: 'II', 79: 'II', 80: 'II', 84: 'II', 85: 'II'}
AUX_DLC = range(81, 86)
# The Rusted weapons a rare monster drops (Fire Emblem Wiki): the King of Fangs a sword or gauntlets, the King of Wings a sword or a
# bow, the King of Beasts a lance or an axe; each the one forged into a silver weapon, or once the one forged into a legendary one.
RARE_DROPS = {96: 'Fangs or Wings', 98: 'Fangs or Wings', 116: 'Fangs', 117: 'Fangs', 111: 'Wings', 113: 'Wings',
              101: 'Beasts', 103: 'Beasts', 106: 'Beasts', 108: 'Beasts'}
LEGENDARY_RUSTED = (98, 103, 108, 113, 117)


# The DLC's paralogues (their battles in the DLC's archive): when each can be fought, from Fire Emblem Wiki (no script read so far opens
# them: README), and what each needs. Black Market Scheme and A Cursed Relic in Chapters 7 or 8 to 11 for every house; The Secret
# Merchant in Chapters 9 to 11 for the Blue Lions and Golden Deer, 13 to 17 on Crimson Flower, never for the Black Eagles otherwise.
DLC_PARALOGUES = {
    93: ({r: (7, 11, []) for r in ('cf', 'ss', 'am', 'vw')}, 'Balthus or Hapi in your army'),
    94: ({r: (8, 11, []) for r in ('cf', 'ss', 'am', 'vw')}, 'Yuri or Constance in your army'),
    97: ({'cf': (13, 17, []), 'am': (9, 11, []), 'vw': (9, 11, [])}, 'Anna in your army (and Jeritza on Crimson Flower)'),
}


# The persons a paralogue is about who aren't units of yours: Rhea (Eternal Guardian) and Sothis (Tales of the Red Canyon).
NOT_IN_ARMY = (36, 37)
SUPPORT_RANK = {1: 'C', 2: 'B', 3: 'A', 4: 'S'}
# The flags the paralogue script tests, where they're traced: Crimson Flower's Protecting Garreg Mach (its events 137 and 138, battle
# flags 0 and 1 set when Seteth and Flayn are defeated) sets 68 and 69.
PARALOGUE_FLAGS = {(68, 69): 'Seteth and Flayn both fell in Protecting Garreg Mach (Crimson Flower\'s Chapter 15)'}


def _script_holds(t, route, chapter):
    """The paralogue script's condition by its route and chapter checks (ChapterSelect: negated, a chapter, how it compares); None for
    anything else (a support, a flag)."""
    if t[0] in ('and', 'or'):
        return _group(t[0], [_script_holds(c, route, chapter) for c in t[1]])
    name, args = t
    if name == 'Route':
        res = args[1] == route
        return (res if args[2] else not res) if not args[0] else not (res if args[2] else not res)
    if name == 'ChapterSelect':
        v, cmp = args[1], args[2]
        res = [chapter < v, chapter <= v, chapter == v, chapter >= v, chapter > v][cmp]
        return not res if args[0] else res
    return None


def paralogue_windows():
    """When each paralogue can be fought on each route (the monastery script `D.PARALOGUE_SCRIPT`: SetParalogueAvailability opens or
    closes it, by the chapter the calendar is in, the route and, for some, a support or a flag). {scenario: {route key: (first chapter,
    last chapter, [what else it needs])}}: open from the first chapter a script opens it in until one closes it. A route counts as its
    house's until Chapter 12 (the scripts number the Black Eagles' as Silver Snow's, 0, until the routes part)."""
    events = D.parse_events(D.archive_file(D.PARALOGUE_SCRIPT))
    heads = {e['num']: e for e in events if e['trigger'][1] & 1}
    found = {}
    for e in events:
        conds, h = [e['conditions']], heads.get(e['trigger'][2])
        while h is not None:
            conds.append(h['conditions'])
            h = heads.get(h['trigger'][2])
        for name, args in e['actions']:
            if name == 'SetParalogueAvailability':
                found.setdefault(args[0], []).append((args[1], ('and', conds)))
    house_route = {'cf': D.SILVER_SNOW, 'ss': D.SILVER_SNOW, 'am': D.AZURE_MOON, 'vw': D.VERDANT_WIND}
    out = {}
    for s, evs in found.items():
        for key, label, _, (route,) in ROUTES:
            last = max(k for k, x in enumerate(D.flow(route)) if x is not None)
            at = lambda ch: route if ch >= PART_TWO else house_route[key]  # noqa: E731
            opened = [ch for ch in range(last + 1) if any(v and _script_holds(c, at(ch), ch) is not False for v, c in evs)]
            if not opened:
                continue
            first = opened[0]
            closed = [ch for ch in range(first + 1, last + 1) if any(not v and _script_holds(c, at(ch), ch) for v, c in evs)]
            end = closed[0] - 1 if closed else last
            needs = []
            for v, c in evs:
                if v and _script_holds(c, at(first), first) is not False:
                    needs += [x for x in _flat(c) if x[0] not in ('Route', 'ChapterSelect')]
            out.setdefault(s, {})[key] = (first, end, list(dict.fromkeys(needs)))
    return out


def needs_words(needs, persons, routes):
    """A paralogue's requirements in words: its persons in your army (where a route's house hasn't got them), a support level, someone
    alive, a flag."""
    out = []
    others = [p for p in persons if p not in NOT_IN_ARMY and any(p not in ROUTE_ARMY[r] for r in routes)]
    if others:
        out.append(' and '.join(D.person_shown_name(p) for p in others) + ' in your army')
    flags = []
    for name, args in needs:
        if name == 'Characters' and not args[0]:
            a, b = D.person_shown_name(args[1]), D.person_shown_name(args[2])
            out.append(f'{a} and {b} at support {SUPPORT_RANK.get(args[3], args[3])} or above')
        elif name == 'DeathFlag' and args[3]:
            out.append(f'{D.person_shown_name(args[1])} alive')
        elif name == 'CheckEventFlag':
            flags.append(args[1])
    for key, words in PARALOGUE_FLAGS.items():
        if set(key) <= set(flags):
            out.append(f'unless {words}')
    out = list(dict.fromkeys(out))
    return out


def window_words(windows, routes):
    """'Can be fought in the months of Chapters 8 to 10' (every route alike), or each route's own range."""
    names = {key: label for key, label, _, _ in ROUTES}
    ranges = {r: windows[r][:2] for r in routes}
    span = lambda a, b: f'Chapter {a}' if a == b else f'Chapters {a} to {b}'  # noqa: E731
    if len(set(ranges.values())) == 1:
        a, b = next(iter(ranges.values()))
        return f'Can be fought in the month of {span(a, b)}' if a == b else f'Can be fought in the months of {span(a, b)}'
    parts = [f'{span(*ranges[r])} on {names[r]}' for r in routes]
    return 'Can be fought in the months of ' + ', '.join(parts[:-1]) + ' and ' + parts[-1]


def _signature(b):
    """A battle's units at the start and its arrivals, its leader as -1: what tells two routes' copies apart."""
    starts = []
    for d in range(len(DIFFS)):
        placed, _ = b.start(d)
        starts.append(sorted((-1 if b.record(slot)['person'] in LORDS and b.record(slot)['army'] == 0 else slot, tile)
                             for slot, tile in placed.items()))
    rein, _ = reinforcements(b, b.scen['victory'])
    return json.dumps([starts, sorted(json.dumps([g.get('when'), g.get('areas'), sorted(json.dumps(u, sort_keys=True)
                                                                                         for u in g['units'])]) for g in rein)])


def paralogue_plan():
    """Each paralogue the story has (38-60): the routes that can fight it, each fought as its house's battle where it opens in White
    Clouds, as its route's after; routes that fight it alike (but for their leader) share one map. The persons it's about count as in
    your army (the game opens a paralogue only with them)."""
    windows = paralogue_windows()
    for s, (w, _) in DLC_PARALOGUES.items():
        windows[s] = w
    persons = dict(D.paralogues())
    lines = {key: line for line in ROUTES for key in [line[0]]}
    house_of = {'cf': HOUSES[0], 'ss': HOUSES[0], 'am': HOUSES[1], 'vw': HOUSES[2]}
    out = []
    for s in sorted(windows):
        routes = list(windows[s])
        groups = {}
        for r in routes:
            line = house_of[r] if windows[s][r][0] < PART_TWO else lines[r]
            sig = _signature(Battle(s, line, persons.get(s, ())))
            groups.setdefault(sig, []).append(r)
        for keys in groups.values():
            line = house_of[keys[0]] if windows[s][keys[0]][0] < PART_TWO else lines[keys[0]]
            out.append({'s': s, 'keys': keys, 'line': line, 'windows': windows[s], 'persons': persons.get(s, ()),
                        'id': f'fe16-p{s}' if len(groups) == 1 else f'fe16-p{s}-{keys[0]}'})
    return out


def plan_lines(plan):
    """The houses or routes a shared paralogue is fought as: its house where it opens in White Clouds (Crimson Flower and Silver Snow
    are both the Black Eagles' there), its route after."""
    house_of = {'cf': HOUSES[0], 'ss': HOUSES[0], 'am': HOUSES[1], 'vw': HOUSES[2]}
    out = []
    for k in plan['keys']:
        line = house_of[k] if plan['windows'][k][0] < PART_TWO else next(x for x in ROUTES if x[0] == k)
        if line not in out:
            out.append(line)
    return out


def line_lord(line):
    """The leader beside Byleth for a house (White Clouds) or route (Silver Snow has none)."""
    if line in HOUSES:
        return LORDS[2 + line[2]]
    return LORDS.get(ROUTE_LORD[line[0]])


def random_foe(e, u):
    """An auxiliary battle's foe as the map shows it: where it stands, a monster or a soldier, nothing about its class or gear (the game
    picks them each time); its commander still drops what its record does."""
    monster = e.get('size') or e.get('bars')
    e['name'] = 'Random monster' if monster else 'Random foe'
    e['note'] = 'Class, level and items picked when the battle starts' + ('; its commander' if u['rank'] == 0 else '')
    e.pop('carries', None)
    e.pop('steal', None)
    drops = [d for d in e.get('drops', []) if d not in [D.weapon_label(w) for w in range(500)]]
    if drops:
        e['drops'] = drops
    else:
        e.pop('drops', None)
    if e['type'] in ('boss', 'named'):
        e['type'] = 'enemy'
    e['generic'] = True


def leader_words(lines):
    """Whoever leads beside Byleth for these houses or routes: one leader by name, else 'Your house leader (Edelgard, Dimitri or
    Claude)' for the houses, 'Your leader (Dimitri or Claude)' for routes."""
    names = list(dict.fromkeys(n for n in (line_lord(x) for x in lines) if n))
    if len(names) == 1:
        return names[0]
    who = 'Your house leader' if all(x in HOUSES for x in lines) else 'Your leader'
    return f"{who} ({', '.join(names[:-1])} or {names[-1]})"


def merged_defeat(b, lines):
    """A shared paralogue's lose condition: the houses' or routes' own where they agree, the leader as `leader_words` where only the
    leader differs, else each one's in turn."""
    texts = {x[1]: defeat_text(b, x) for x in lines}
    if len(set(texts.values())) == 1:
        return next(iter(texts.values()))
    forms = set()
    for x in lines:
        lord = line_lord(x)
        forms.add(texts[x[1]].replace(lord, '{lord}') if lord else texts[x[1]])
    if len(forms) == 1 and '{lord}' in next(iter(forms)):
        words = leader_words(lines)
        return forms.pop().replace('{lord}', words[0].lower() + words[1:])
    return '; '.join(f'{t} ({label})' for label, t in texts.items())


def battle_list():
    """Every story battle once per way it's fought: White Clouds (the Prologue to Chapter 11) once, or once per house where the houses
    fight it differently (`PER_HOUSE`); from Chapter 12 each route's own battles (fixed_flow.bin), once per route that fights them."""
    out = []
    for s in STORY:
        own = s in PER_HOUSE
        for house in HOUSES if own else [HOUSES[0]]:
            out.append({'s': s, 'line': house, 'id': f'fe16-{s}' + (f'-{house[0]}' if own else ''), 'own': own, 'chapter': s,
                        'route': 'Story', 'shared': not own and s > 0})
    for route in ROUTES:
        for chapter, s in enumerate(D.flow(route[3][0])):
            if chapter >= PART_TWO and s is not None:
                out.append({'s': s, 'line': route, 'id': f'fe16-{s}-{route[0]}', 'own': True, 'chapter': chapter,
                            'route': route[1], 'shared': False})
    for chapter, s in enumerate(D.flow(D.CINDERED_SHADOWS)):
        if s is not None:
            out.append({'s': s, 'line': CINDERED, 'id': f'fe16-{s}-cs', 'own': True, 'chapter': chapter,
                        'route': 'Cindered Shadows', 'shared': False, 'cs': True})
    for s in AUX:
        part = AUX_PART.get(s)
        out.append({'s': s, 'line': HOUSES[0], 'id': f'fe16-a{s}', 'own': True, 'chapter': 13 if part == 'II' else 2,
                    'route': 'Auxiliary', 'shared': False, 'aux': part or 'both'})
    for plan in paralogue_plan():
        out.append({'s': plan['s'], 'line': plan['line'], 'id': plan['id'], 'own': len(plan['keys']) == 1,
                    'chapter': min(plan['windows'][k][0] for k in plan['keys']), 'route': 'Paralogue', 'shared': False,
                    'paralogue': plan})
    return out


def main():
    groups = GROUPS
    maps, sources, variants, used = [], {}, {}, {}

    held = {}   # (item, map id, kind, text) -> the difficulties the line holds on

    def source(name, map_id, kind, text, diffs=None):
        held.setdefault((name, map_id, kind, text), set()).update(diffs or DIFFS)

    opens = {}   # paralogue map id -> {route: the chapter it opens in}

    for entry in battle_list():
        s, house, map_id, own, chapter = entry['s'], entry['line'], entry['id'], entry['own'], entry['chapter']
        part_two = chapter >= PART_TWO
        if entry['shared']:
            shared_check(s)
        plan = entry.get('paralogue')
        if True:
            b = Battle(s, house, plan['persons'] if plan else ())
            title = D.text(s)
            victory = b.scen['victory']
            m = {
                'id': map_id, 'route': entry['route'], 'chapter': chapter, 'title': title,
                'location': D.text(957 + b.scen['map']),
                'heading': 'Prologue' if chapter == 0 else f'Ch.{chapter}' + (f' ({house[1]})' if own and not part_two else ''),
                'width': b.w, 'height': b.h, 'grid': [], 'objectives': [], 'units': [], 'starts': [], 'objects': [],
                'changes': [], 'notes': [], 'lord': 'Byleth',
                'victory': clean(D.text(11906 + victory)),
                'defeat': merged_defeat(b, plan_lines(plan)) if plan else defeat_text(b, house if own else None),
            }
            if entry.get('aux'):
                m['heading'] = 'Auxiliary battle'
                part = {'I': 'Part I (White Clouds) only', 'II': 'Part II only', 'both': 'both parts'}[entry['aux']]
                m['notes'].append(f'Offered on free days (the Battle menu) during {part}' +
                                  (', with the Expansion Pass.' if s in AUX_DLC else '.'))
                m['notes'].append("Its foes' classes, levels and items are picked each time it starts; their levels follow your "
                                  'progress in the story.')
                if all(D.monster_size(unit_class(b.record(sl))) > 1 or b.record(sl)['army'] != 1 for sl in b.start(0)[0]):
                    m['notes'].append('On a rare monster sighting day its commander is a King of Fangs, Wings or Beasts, which drops a '
                                      'Rusted weapon.')
                    for w, kings in RARE_DROPS.items():
                        once = ', only once' if w in LEGENDARY_RUSTED else ''
                        source(D.weapon_label(w), map_id, 'drop', f'Dropped by a rare monster (King of {kings}) at random{once}')
                opens[map_id] = {label: m['chapter'] for _, label, _, _ in ROUTES}
            if plan:
                names = {key: label for key, label, _, _ in ROUTES}
                m['heading'] = 'Paralogue'
                m['availableIn'] = [names[k] for k in plan['keys']]
                m['notes'].append(window_words(plan['windows'], plan['keys']) + '.')
                needs = needs_words([n for k in plan['keys'] for n in plan['windows'][k][2]], plan['persons'], plan['keys'])
                if s in DLC_PARALOGUES:
                    needs = [DLC_PARALOGUES[s][1]]
                    m['notes'].append('Comes with the Expansion Pass.')
                if needs:
                    m['notes'].append('Needs ' + '; '.join(needs) + '.')
                opens[map_id] = {names[k]: plan['windows'][k][0] for k in plan['keys']}
            m['objectives'] = objectives(b, m['victory'], m['defeat'])
            # Units per difficulty, merged.
            per_diff, forced, starts = [], {}, set()
            for d, dname in enumerate(b.diffs):
                placed, _ = b.start(d)
                units = []
                for slot, tile in sorted(placed.items()):
                    u = b.record(slot)
                    if u['army'] == 0:
                        if u['person'] in (None, PLAYER_SLOT):
                            starts.add(tuple(b.app(*tile)))
                        else:
                            if plan and u['person'] in LORDS and len(plan_lines(plan)) > 1:
                                who = leader_words(plan_lines(plan))
                            else:
                                who = LEADER if not own and s > 0 and u['person'] in LORDS else D.person_shown_name(u['person'])
                            forced[who] = b.app(*tile)
                        continue
                    e, inv = unit_entry(b, slot, tile, d, victory)
                    e['difficulties'] = [dname]
                    units.append(e)
                    if entry.get('aux'):
                        random_foe(e, u)
                        continue
                    who = e['name'] if not e.get('generic') else f"a foe {e['name']}" if u['army'] == 1 else f"a {e['name']}"
                    for g, dropping in inv:
                        if dropping and 10 <= g < 600:
                            source(item_name(g), map_id, 'drop', f'Dropped by {who}', [dname])
                        elif 10 <= g < 600 and u['army'] in (1, 3):
                            kind = 'foe-generic' if e.get('generic') else 'foe'
                            source(item_name(g), map_id, kind, f"Carried by {who}{'' if e.get('generic') else ', a foe'}", [dname])
                per_diff.append(units)
            m['units'] = gm._merge_units(per_diff, b.diffs)
            if b.diffs != DIFFS:
                m['difficulties'] = list(b.diffs)
            # Stand-ins: a student another house can recruit is replaced, on the same tile, by a soldier of their class.
            for p in b.recruit_checks():
                base, _ = b.start(0)
                alt, _ = b.start(0, recruited=(p,))
                gone = [slot for slot in base if slot not in alt and b.record(slot)['person'] == p]
                new = [slot for slot in alt if slot not in base]
                for slot in gone:
                    tile = b.app(*base[slot])
                    sub = next((x for x in new if b.app(*alt[x]) == tile), None)
                    if sub is None:
                        continue
                    e, _ = unit_entry(b, sub, alt[sub], 0, victory)
                    for u in m['units']:
                        if u['tile'] == tile and u['name'] == D.person_shown_name(p):
                            u['standIn'] = {'type': e['type'], 'name': e['name'], 'note': e['note'], 'generic': True,
                                            'when': f'if you recruited {D.person_shown_name(p)} into your house'}
            joins = {}
            rein, invs = reinforcements(b, victory, joins)
            if joins:
                m['joiners'] = [j for js in joins.values() for j in js]
            if rein:
                for g in rein:
                    for u in g['units']:
                        if u.get('difficulties') == list(b.diffs):
                            u.pop('difficulties')
                m['reinforcements'] = rein
            # What the battle's script gives (GrantItem: a slot, a global item number) once it's won; a gift that checks the count of
            # what looters carried off says how many (Chapter 11's Crest Stones), and the map's notes list every such reward.
            loot = next((v for v in b.loot.values() if 'count' in v), None)
            total = sum(v.get('adds', 0) for v in b.loot.values())
            rewards = []
            for e in b.events:
                gifts = [a[1][1] for a in e['actions'] if a[0] == 'GrantItem' and a[1][0] == 0]
                conds = [c for c in _flat(e['conditions']) if c[0] == 'CheckVariableValue']
                if loot and any(c[1][1] == loot['count'] for c in conds):
                    words = count_words(conds, loot['count'], loot['thing'], total)
                    names = [item_name(g) for g in gifts]
                    rewards.append(f"{words}, {', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0] if names else 'nothing'}")
                elif not gifts:
                    continue
                else:
                    words = reward_words(b, e)
                    if words:
                        names = [item_name(g) for g in gifts]
                        line = f"{words}, {', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]}"
                        if line not in rewards:
                            rewards.append(line)
                for g in gifts:
                    if 10 <= g < 600:
                        source(item_name(g), map_id, 'event-later', 'Given when the battle is won' + (f', {words}' if words else ''))
            if loot:
                kinds = [plural(k) for k in dict.fromkeys(class_name(unit_class(b.record(slot))) for slot in sorted(b.loot))]
                who = kinds[0] if len(kinds) == 1 else ', '.join(kinds[:-1]) + ' and ' + kinds[-1]
                m['notes'].append(f"{who} go for the {total} {plural(loot['thing'])} in the walls, then leave the map with them: tap one "
                                  'to see what it takes and where it leaves.')
            if rewards:
                m['notes'].append('When the battle is won: ' + '; '.join(rewards) + '.')
            for per, _ in invs:
                for dname, units in per.items():
                    for u, inv in units:
                        who = u['name'] if not u.get('generic') else f"a foe {u['name']}"
                        for g, dropping in inv:
                            if dropping and 10 <= g < 600:
                                source(item_name(g), map_id, 'drop-later', f'Dropped by {who}, arriving mid-chapter', [dname])
            for u in m['units']:
                if u.get('difficulties') == list(b.diffs):
                    u.pop('difficulties')
            # Your units' tiles: the slots you fill, Byleth's own and those the game places (each one a starting tile).
            if 'Byleth' in forced:
                m['corrinStart'] = forced.pop('Byleth')
                starts.add(tuple(m['corrinStart']))
            starts |= {tuple(t) for t in forced.values()}
            m['starts'] = sorted([list(t) for t in starts], key=lambda t: (-t[1], t[0]))
            m['forced'] = [{'name': n, 'tile': t} for n, t in forced.items()]
            # A leader the lose condition names but nothing places is one you must deploy, on a slot you choose.
            if entry.get('aux') or entry.get('cs'):
                leader = None
            elif plan:
                leader = leader_words(plan_lines(plan)) if any(line_lord(x) for x in plan_lines(plan)) else None
            elif part_two:
                lord = ROUTE_LORD[house[0]]
                leader = LORDS[lord] if lord else None
            else:
                leader = LEADER if not own else LORDS[2 + house[2]]
            named = leader is not None and (('your house leader' in m['defeat']) if not own and not plan else
                                            leader.lower() in m['defeat'].lower())
            if s > 0 and named and leader not in forced:
                m['forced'].append({'name': leader})
            if not m['forced']:
                del m['forced']
            # Terrain.
            codes, infos = [], []
            for r in range(b.h):
                line = []
                for c in range(b.w):
                    kind = b.rows[r][c][0]
                    letter = LETTER[kind]
                    code = encode(GAME, letter)
                    info = tile_info(kind)
                    line.append(code)
                    infos.append((code, info))
                    variants.setdefault(code, {}).setdefault(json.dumps(info, sort_keys=True), [info, set()])[1].add(map_id)
                codes.append(''.join(line))
            m['grid'] = codes
            used[map_id] = {}
            for code, info in infos:
                old = used[map_id].setdefault(code, info)
                assert old == info, (map_id, code, old, info)
            maps.append(m)
            print(map_id, title, f'{b.w}x{b.h}', len(m['units']), 'units', len(m['starts']), 'starts')

    info = {}
    for code, vs in variants.items():
        info[code] = json.loads(max(vs.items(), key=lambda kv: len(kv[1][1]))[0])
    for m in maps:
        over = {}
        for code, e in used[m['id']].items():
            if e != info[code]:
                over[code] = {k: v for k, v in e.items() if v != info[code].get(k)}
        if over:
            m['terrainOverrides'] = over
    members = [(label, [c for c, g in CLASS_GROUP.items() if g == label and class_name(c)], row) for label, _, row in groups]
    gm.write_terrain(GAME, TITLE, SCRIPT, info, members, {c: class_name(c) for c in range(len(CLASSES))},
                     fliers='')
    # Starting gear (fixed_persondata.bin section 6): Byleth and the lords from the Prologue, each house's students from its Chapter 1.
    for p in PROLOGUE_ARMY:
        for g in D.starting_items(p):
            if 10 <= g < 600:
                source(item_name(g), 'fe16-0', 'kit', f'Carried by {D.person_shown_name(p)} from the start')
    for key, people in STUDENTS.items():
        for p in people:
            if p in PROLOGUE_ARMY:
                continue
            for g in D.starting_items(p):
                if 10 <= g < 600:
                    source(item_name(g), f'fe16-1-{key}', 'kit', f'Carried by {D.person_shown_name(p)} on joining')
    # The faculty and knights you can recruit (the monastery's script, file 360: each RecruitTalk's chapter check) bring their own gear
    # (persondata section 6): Catherine her Thunderbrand from Chapter 4.
    for p, chapter in RECRUITS.items():
        ids = [f'fe16-{chapter}-{h[0]}' for h in HOUSES] if chapter in PER_HOUSE else [f'fe16-{chapter}']
        for g in D.starting_items(p):
            if 10 <= g < 600:
                for map_id in ids:
                    source(item_name(g), map_id, 'kit', f'Carried by {D.person_shown_name(p)} on joining')
    # The monastery's armory (fixed_shopdata.bin section 0): open from Chapter 1 (after the Prologue), its stock by the shop's level
    # (+16, +17, +18: how many, 0xFF unlimited, 0 none). What raises the level isn't traced yet (README).
    for r in D.table(D.SHOPDATA, 0):
        price, sell, w = struct.unpack_from('<iiH', r, 0)
        if not (6 <= w < 500) or not r[12]:
            continue
        name = D.weapon_name(w)
        for lv in range(3):
            n = r[16 + lv]
            if n == 0:
                continue
            words = "Sold at the monastery's armory" + ('' if lv == 0 else f' once it reaches level {lv + 1}')
            entry = {'mapId': 'fe16-0', 'kind': 'town-shop-later', 'text': words}
            if n != 0xFF:
                entry['limited'] = n
            sources.setdefault(name, []).append(entry)
            if n == 0xFF:
                break   # unlimited from this level on: the higher levels add nothing
    for (name, map_id, kind, text), ds in held.items():
        line = {'mapId': map_id, 'kind': kind, 'text': text}
        if len(ds) < len(DIFFS):
            line['difficulties'] = [d for d in DIFFS if d in ds]
        sources.setdefault(name, []).append(line)
    forging(sources, maps)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    write_opens(opens)
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=DIFFS)


# The blacksmith's forging (fixed_shopdata.bin section 4): a weapon, gold and a material make another weapon, from the professor level
# the record names (+10: an index in E, E+, D, D+ ... S+; Fire Emblem Wiki's forging table gives the same levels). The blacksmith opens
# with the quest "Forge the Way" in Chapter 5's month (Fire Emblem Wiki).
PROFESSOR_LEVELS = ['E', 'E+', 'D', 'D+', 'C', 'C+', 'B', 'B+', 'A', 'A+', 'S', 'S+']
FORGE_MATERIAL = 5056    # a material's name: text table 1's string at 5056 + its number (64 Smithing Stone .. 71 Venomstone)
FORGE_OPENS = 5          # the chapter the blacksmith opens in


def forging(sources, maps):
    """Each weapon the blacksmith forges, as a source where both it and the weapon it's forged from can be had: from Chapter 5, or
    from where the base weapon first turns up on each route, story or side list (a weapon forged from a forged one waits for that)."""
    chapter = {m['id']: m['chapter'] for m in maps}
    group = {m['id']: m['route'] if m['route'] != 'Story' else (m['id'].split('-')[2] if m['id'].count('-') > 1 else '')
             for m in maps}
    recipes = D.forge_list()
    for _ in range(4):   # forged from forged: Silver Sword+ from a Silver Sword forged from a Steel Sword
        for f in recipes:
            base, made = D.weapon_label(f['from']), D.weapon_label(f['made'])
            have = [x for x in sources.get(base, []) if x['mapId'] in chapter]
            if not have or f['from'] == f['made']:
                continue
            words = (f"Forged from {'an' if base[0] in 'AEIOU' else 'a'} {base} at the blacksmith (professor level "
                     f"{PROFESSOR_LEVELS[f['level']]}): {f['price']:,} gold and {f['amount']} {D.text(FORGE_MATERIAL + f['material'])}")
            first = {}
            for x in have:
                key = group[x['mapId']]
                if key not in first or chapter[x['mapId']] < chapter[first[key]]:
                    first[key] = x['mapId']
            # Where the story has the base weapon, a side list's (a paralogue's, an auxiliary battle's) adds nothing.
            story = {k: v for k, v in first.items() if k not in ('Paralogue', 'Auxiliary')}
            for map_id in (story or first).values():
                at = map_id if chapter[map_id] >= FORGE_OPENS else 'fe16-5'
                line = {'mapId': at, 'kind': 'forge', 'text': words}
                if line not in sources.setdefault(made, []):
                    sources[made].append(line)


def write_opens(opens):
    """src/data/fe16/fe16Opens.ts: the chapter each paralogue opens in, per route (the spoiler block opens it there)."""
    lines = [
        '/*',
        f' * GENERATED by scripts/{SCRIPT} from the monastery\'s paralogue script. Do not edit by hand.',
        ' */',
        '',
        '/** The chapter each paralogue opens in (its month, before the chapter\'s battle), per route. */',
        'export const FE16_OPENS: Record<string, Record<string, number>> = ' + json.dumps(opens, indent=2, ensure_ascii=False),
    ]
    gm.write(GAME, 'fe16Opens.ts', lines)


def clean(text):
    """The game's text without its colour codes, Byleth's name for its placeholder."""
    out = text.replace('\x1bS0', 'Byleth')
    while '\x1bC' in out:
        i = out.index('\x1bC')
        out = out[:i] + out[i + 3:]
    return out.replace('\x1bR', '').replace('\n', ' ').rstrip('.')


if __name__ == '__main__':
    main()

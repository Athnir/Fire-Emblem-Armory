"""Read Fire Emblem: Three Houses' data files, as fe16_extract.py copies them into data-raw/fe16/romfs (archive file n as `<n>.bin`).

Field names follow the Three Houses Research Team's 010 Editor templates (github.com/three-houses-research-team/
010-binary-templates), each checked against the files here; data-raw/fe16/README.md lists the layouts and what was checked.

Most data files are one container: u32 section count, then (u32 offset, u32 size) per section. A table section starts with a
0x40-byte header (u32 magic 0x16121900, u32 record count, u32 record size) and its records follow. The text (file 0) is the same
container, one section per language (1 = English, as the US release has it), each holding four Koei 'XL' string tables.
"""
import os
import struct

ROMFS = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe16', 'romfs')
DLC = os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe16', 'dlc')
TABLE_MAGIC = 0x16121900
ENGLISH = 1

# Archive file numbers (DATA0), as the update's INFO0 names the ones it replaces.
MSGDATA, FIXED_DATA, STAGEDATA, CLASSDATA, PERSONDATA, ACTDATA, SKILL, SCENARIO, SHOPDATA = 0, 6, 10, 11, 12, 13, 15, 22, 30
SC_FIRST = 83            # SC00_00.bai; each scenario has a .bai (its units) and a .bsi (its script), in turn
GRID_FIRST = 365         # map 0's grid; map m's is GRID_FIRST + m

# Text table 1's ranges (each name list is followed by its descriptions).
PERSON_NAME = 1157       # person p's name
CLASS_NAME = 3453        # class c's name
WEAPON_NAME = 3756       # weapon w's name; its description is WEAPON_NAME + 500 + w

_cache = {}


def archive_file(n):
    if n not in _cache:
        _cache[n] = open(os.path.join(ROMFS, f'{n}.bin'), 'rb').read()
    return _cache[n]


def sections(data):
    count = struct.unpack_from('<I', data, 0)[0]
    return [data[o:o + s] for o, s in (struct.unpack_from('<II', data, 4 + 8 * k) for k in range(count))]


def records(section):
    """A table section's records."""
    magic, count, size = struct.unpack_from('<III', section, 0)
    assert magic == TABLE_MAGIC, hex(magic)
    return [section[0x40 + i * size:0x40 + (i + 1) * size] for i in range(count)]


def table(n, k):
    return records(sections(archive_file(n))[k])


def xl_strings(t):
    """A Koei XL string table: 'XL', u16 version, u16 size (its low 16 bits), u16 columns, u16 count, u16 entry size, u32 header
    size, u32 -; then a u32 offset per string (from the header's end), each string UTF-8 and NUL-terminated."""
    assert t[:2] == b'XL', t[:4]
    count, _esize, header = struct.unpack_from('<HHI', t, 8)
    out = []
    for k in range(count):
        o = header + struct.unpack_from('<I', t, header + 4 * k)[0]
        out.append(t[o:t.index(b'\0', o)].decode('utf-8'))
    return out


def texts(lang=ENGLISH):
    """The language's three string tables (the fourth XL table, its first, is an index)."""
    key = ('texts', lang)
    if key not in _cache:
        _cache[key] = [xl_strings(x) for x in sections(sections(archive_file(MSGDATA))[lang])[1:]]
    return _cache[key]


def text(n, table_no=1, lang=ENGLISH):
    return texts(lang)[table_no][n]


def person_name(p):
    return text(PERSON_NAME + p)


def class_name(c):
    return text(CLASS_NAME + c)


def weapon_name(w):
    return text(WEAPON_NAME + w)


def kept_weapon(x):
    """Whether a weapon record (`weapons()`) is an item of its own: not Unarmed (0) or the five broken forms a weapon at 0 uses fights
    as (1-5), not a record no text names, and a weapon of the five kinds or a crest stone (+15 bit 0x80, or a blank +0)."""
    if not x['name'] or x['id'] < 6:
        return False
    return bool(x['flags1'] & 0x80) or x['raw'][0] == 0 or x['type'] <= 4


_LABELS = {}


def weapon_label(w):
    """A weapon's name as the app lists it: the game's own; a Rusted weapon (+15 bit 0x40 past the broken five: Mt 0, Hit 30) named for
    what the blacksmith forges it into, as the game names five of each kind alike ('Rusted Bow (Silver Bow)', `forge_list()`); any
    other name the game gives two kept records with the later record's number ('Crest of Flames Power (228)')."""
    if not _LABELS:
        made = {f['from']: f['made'] for f in forge_list()}
        seen = set()
        for x in weapons():
            if not kept_weapon(x):
                continue
            if x['flags1'] & 0x40 and x['id'] in made:
                _LABELS[x['id']] = f"{x['name']} ({weapon_name(made[x['id']])})"
            else:
                _LABELS[x['id']] = f"{x['name']} ({x['id']})" if x['name'] in seen else x['name']
            seen.add(x['name'])
    return _LABELS.get(w, weapon_name(w))


def monster_size(c):
    """How many tiles on a side a unit of class c covers: a monster class (its +73 indexes the monster table, `fixed_classdata.bin`
    section 4) the table's +56 plus one, any other 1. It matches Fire Emblem Wiki's 'Size' for every monster checked (Demonic Beast
    and Giant Crawler 2, the Immaculate One 3, the Hegemon Husk 1: 'taking up only one space'), and with the unit's tile as the
    square's top-left every monster any battle places stands on ground it can enter (196 of size 2, 7 of size 3)."""
    r = classes()[c]
    monsters = table(CLASSDATA, 4)
    return monsters[r[0x49]][56] + 1 if r[0x49] < len(monsters) else 1


def monster_bars(c):
    """How many health bars a unit of class c has: a monster class's monster table +52 (Fire Emblem Wiki: the Experimental Demonic
    Beast and Giant Wolf two, the Demonic Beast three, the Immaculate One four), any other class's one."""
    r = classes()[c]
    monsters = table(CLASSDATA, 4)
    return monsters[r[0x49]][52] if r[0x49] < len(monsters) else 1


def forge_list():
    """The blacksmith's forging (fixed_shopdata.bin section 4, 12-byte records): +0 price, +4 the weapon forged from, +6 the material
    (its own item list), +8 the weapon made, +10 the professor level it needs, +11 how much material."""
    out = []
    for r in table(SHOPDATA, 4):
        price, base, material, made, level, amount = struct.unpack_from('<iHHHBB', r, 0)
        out.append({'price': price, 'from': base, 'material': material, 'made': made, 'level': level, 'amount': amount})
    return out


def weapon_description(w):
    return text(WEAPON_NAME + 500 + w)


# fixed_data.bin (file 6), section 0: the weapons, 24-byte records.
WEAPON_TYPES = ['Sword', 'Lance', 'Axe', 'Bow', 'Gauntlets']


def weapons():
    """Each weapon record: +2/+3 its two effects' values, +4 an extra effect, +5 type (0 sword .. 4 gauntlets), +6 rank, +7 max
    range, +8 model, +9 crest (86 none), +10 min range, +11 uses, +12 status it inflicts, +13 icon, +14 effective against (bits:
    infantry, armour, cavalry, flier, dragon, monster), +15 flags (0x40 broken or rusted: Mt 0, Hit 30; 0x80 crest stone), +16 Mt,
    +17 Hit, +18 Crit, +19 Wt, +20/+21 two effects (skill properties), +22 flags (0x01 magic, 0x02 against Res, 0x04 leaves 1 HP,
    0x08 not fliers, 0x10 no follow-up, 0x20 strikes twice, 0x40/0x80 relic)."""
    out = []
    for w, r in enumerate(table(FIXED_DATA, 0)):
        out.append({
            'id': w, 'name': weapon_name(w),
            'value1': r[2], 'value2': r[3], 'extra': r[4], 'type': r[5], 'rank': r[6], 'max_range': r[7], 'model': r[8],
            'crest': r[9], 'min_range': r[10], 'uses': r[11], 'status': r[12], 'icon': r[13], 'effective': r[14],
            'flags1': r[15], 'mt': r[16], 'hit': r[17], 'crit': r[18], 'wt': r[19], 'effect1': r[20], 'effect2': r[21],
            'flags': r[22], 'raw': r,
        })
    return out


# fixed_classdata.bin section 0: the classes, 118-byte records.
MOVE_TYPE, DISMOUNTED_MOVE_TYPE, MAIN_WEAPON, CLASS_TIER, CLASS_TYPES = 77, 78, 79, 69, 81


def classes():
    return table(CLASSDATA, 0)


def persons():
    return table(PERSONDATA, 0)


def person_shown_name(p):
    """The name a person is shown with: its record's name (+18) is a person number too (generic foes share them)."""
    return person_name(struct.unpack_from('<H', persons()[p], 18)[0])


def starting_items(p):
    """A playable character's starting items (persondata section 6, the 45 playable characters): global item numbers."""
    r = table(PERSONDATA, 6)[p]
    return [i for i in struct.unpack_from('<6H', r, 2) if i]


# Global item numbers: a weapon is its number + 10, equipment 600 on (names from text 4556), items 1000 on (names from 4656).
def global_item_name(g):
    if 10 <= g < 600:
        return weapon_label(g - 10)
    if 600 <= g < 650:
        return text(4556 + g - 600)
    if 1000 <= g < 1200:
        return text(4656 + g - 1000)
    return f'item {g}'


# fixed_scenario.bin section 0: the battles (100 x 46 bytes).
def scenario(n):
    """+15 the chapter byte (23 a paralogue, 24 an auxiliary battle, 25 DLC), +31 the victory condition, +32 the map, +33-35 the foes'
    level on Normal, Hard and Maddening, +36 bit 0 the battle's units are each house's own (`units()`' tables: the mock battles and
    To War at Gronder), +40-44 the lose conditions (+41 the Black Eagles' and Silver Snow's, +42 the Blue Lions', +43 the Golden Deer's,
    +44 Crimson Flower's; 0 where that route never fights it)."""
    r = table(SCENARIO, 0)[n]
    return {'chapter': r[15], 'victory': r[31], 'map': r[32], 'levels': tuple(r[33:36]), 'tier': r[14],
            'per_house': bool(r[36] & 1), 'defeat': tuple(r[40:45]), 'raw': r}


# fixed_flow.bin (file 7): the story's chapters per route. Sections 0-3 are the routes as the scripts number them (0 Silver Snow,
# 1 Azure Moon, 2 Verdant Wind, 3 Crimson Flower), 5 Cindered Shadows; a 40-byte record per chapter (record k is chapter k), its +30
# the battle fought (a scenario; 0xFF none). Section 4 lists the paralogues (10 bytes: +2 and +4 the persons it's about, +8 the
# scenario).
FLOW = 7
SILVER_SNOW, AZURE_MOON, VERDANT_WIND, CRIMSON_FLOWER, CINDERED_SHADOWS = 0, 1, 2, 3, 5


def flow(route):
    """The battle of each chapter on a route (chapter k at index k; None where the chapter has no battle)."""
    return [None if r[30] == 0xFF else r[30] for r in table(FLOW, route)]


def paralogues():
    """The paralogues: [(scenario, persons)], the persons the paralogue is about (persondata numbers)."""
    out = []
    for r in table(FLOW, 4):
        _a, p1, p2, _b, s = struct.unpack_from('<5h', r, 0)
        if 0 <= s < 255:
            out.append((s, [p for p in (p1, p2) if p >= 0]))
    return out


def default_weapons():
    """fixed_scenario.bin section 1: by weapon type (0 sword .. 4 gauntlets), the Iron, Steel and Silver weapon a unit with no items
    is given (`0x19e41c`)."""
    return [tuple(r) for r in table(SCENARIO, 1)[:5]]


# fixed_stagedata.bin: section 0 the terrain kinds (128 x 14), section 1 the movement costs (16 movement types x 16 categories).
def terrain():
    out = []
    for t, r in enumerate(table(STAGEDATA, 0)):
        out.append({'id': t, 'name': text(5502 + t), 'prt': struct.unpack_from('<b', r, 4)[0], 'rsl': struct.unpack_from('<b', r, 5)[0],
                    'avo': struct.unpack_from('<b', r, 6)[0], 'heal': struct.unpack_from('<b', r, 7)[0], 'hp': r[8], 'cost': r[10],
                    'flags': r[11] | r[12] << 8 | r[13] << 16})
    return out


def move_costs():
    return [list(r) for r in table(STAGEDATA, 1)]


def grid(map_no):
    """A battle map's grid (archive file 365 + map): its size and, per tile from the top left, (terrain at the start, terrain after the
    tile's change)."""
    d = archive_file(GRID_FIRST + map_no)
    assert struct.unpack_from('<HH', d, 0) == (0, 0xFE17), d[:4].hex()
    x1, y1, x2, y2 = d[4:8]
    w, h = (x2 - x1) // 2, (y2 - y1) // 2
    rows = [[(d[8 + (r * 32 + c) * 2], d[9 + (r * 32 + c) * 2]) for c in range(w)] for r in range(h)]
    return w, h, rows


def units(scenario_no):
    """A battle's unit tables (`SCxx_yy.bai`): one per house (0 Black Eagles, 1 Blue Lions, 2 Golden Deer), 100 records each."""
    d = archive_file(SC_FIRST + 2 * scenario_no)
    offs = struct.unpack_from('<3I', d, 0xC)
    out = []
    for o in offs:
        tab = []
        for k in range(100):
            r = d[0x18 + o + k * 44:0x18 + o + (k + 1) * 44]
            person, _, cls = struct.unpack_from('<HHH', r, 0)
            tab.append({
                'slot': k, 'person': person - 1 if person else None, 'class': cls - 1 if cls else None,
                'items': [i for i in struct.unpack_from('<6H', r, 6)], 'drops': struct.unpack_from('<H', r, 18)[0],
                'abilities': [a - 1 for a in r[20:25] if a], 'x': r[25], 'y': r[26], 'level': r[28], 'army': r[29],
                'scripted': r[30], 'movement': r[31], 'rank': r[33], 'battalion': r[34] - 1 if r[34] else None, 'raw': r,
            })
        out.append(tab)
    return out


def bai_item_name(raw):
    """A unit slot's item: global item number + 1 (0: empty)."""
    return global_item_name(raw - 1) if raw else None


# The battle scripts (`SCxx_yy.bsi`): each command is a u32 code and its u32 arguments. Names and argument counts follow the Three
# Houses Research Team's BSI compiler (github.com/three-houses-research-team/bsic); every battle script parses to its events' own
# command counts and lengths with them.
ACTIONS = {
    0: ('ShowTextS', 1), 15: ('BattleTalk', 5), 20: ('PlayBGM', 2), 30: ('MusicSomething', 1), 40: ('Unknown40', 2),
    50: ('IncrementVariable', 2), 60: ('Unknown60', 2), 70: ('SetFlag70', 2), 80: ('TargetScriptMaybe', 1),
    90: ('EndMission', 1), 130: ('SpawnUnit130', 7), 140: ('Walk', 10), 150: ('ReplaceUnitBAI', 9), 160: ('RemoveFromMap', 5),
    170: ('KillAllInTeam', 6), 220: ('Unknown220', 2), 240: ('GrantItem', 2), 250: ('Unknown250', 2),
    270: ('SetupTerrainEffects', 1), 320: ('Unknown320', 1), 330: ('MoveCameraToBai', 4), 340: ('MoveCameraToCoords', 5),
    370: ('MoveToUnitAI2', 7), 380: ('MoveToRectangleAI', 7), 400: ('MakeMapTilesBlue', 7), 430: ('PlayMovie', 2),
    440: ('SetMovementFlag', 2), 450: ('Unknown450', 4), 460: ('ApplyStatusToUnit', 3), 470: ('ApplyStatusToUnitAOE', 8),
    530: ('Unknown530', 2), 540: ('WriteSomethingToSaveMaybe2', 3), 550: ('Unknown550', 1), 560: ('Unknown560', 1),
    570: ('OpenDoor', 2), 580: ('MoveToRectangleAI580', 7), 590: ('SetupWorkTilePair', 4), 600: ('SpawnUnit', 4),
    610: ('KeepOnMapWhenSlain', 3), 620: ('SpawnSpooky', 5), 630: ('ChangeRotation', 2), 640: ('FadeToBlack', 1),
    650: ('ShortPause', 0), 660: ('PersuadeKill', 3), 670: ('Unknown670', 2), 680: ('SpareKill', 2), 690: ('MoveToUnitAI', 7),
    700: ('GrantBattalion', 1), 710: ('UpdateMapResultConditions', 2), 720: ('GrantItemQuantity', 2),
    730: ('RemoveInventory', 1), 740: ('SetDeathString', 2), 750: ('Unk750', 1), 760: ('Unk760', 2), 770: ('Unk770', 1),
    780: ('Unk780', 1), 790: ('UpdateMapVictoryAndDefeat', 2), 800: ('UpdateUnitStatus', 0), 810: ('BlackBeastSomething', 3),
    820: ('MoveToRectangleAI820', 7), 830: ('GrantDroppableItem', 2), 840: ('ChaliceBlast', 6), 850: ('MapShake', 3),
    860: ('FadeToWhite', 1), 2010: ('MonasteryTalk', 2), 2030: ('SpawnCharacterMonastery', 1),
    2040: ('RemoveFromMonastery', 1), 2050: ('Unknown2050', 1), 2060: ('Unknown2060', 1), 2070: ('SetEventFlag', 2),
    2100: ('SetQuestStatus', 2), 2120: ('ShowTutorial', 1), 2180: ('MoveBaiMonastery', 4), 2190: ('SupportPoints', 4),
    2200: ('RemoveItemMonasteryGift', 3), 2210: ('SetOrderThisCharacterAppearsInScript', 2),
    2260: ('GrantItemMonasteryGift', 3), 2280: ('Unknown2280', 1), 2300: ('CreateTalkingGroup', 4), 2340: ('Unknown2340', 10),
    2360: ('FadeToBlackMonastery', 1), 2370: ('BylethChoiceDialog', 10), 2420: ('SetDoorState', 2),
    2430: ('ShowVMesMonastery', 1), 2440: ('ShowChoiceDialog', 1), 2450: ('Unknown2450', 1), 2460: ('Unknown2460', 1),
    2470: ('SkipToEndOfMonth', 0), 2480: ('RecruitTalk', 5), 2500: ('SetupAuxBattleMapAsQuestMap', 2),
    2510: ('Unknown2510', 2), 2520: ('GrantItemMonastery', 3), 2530: ('RemoveItemMonastery', 3), 2540: ('Unknown2540', 1),
    2550: ('Unknown2550', 2), 2560: ('Unknown2560', 2), 2570: ('Unknown2570', 3), 2580: ('Unknown2580', 2),
    2590: ('Unknown2590', 2), 2600: ('Unknown2600', 0), 2610: ('Unknown2610', 9), 2640: ('ChooseForHeronCup', 2),
    2650: ('SetMonasteryTodoMessage', 2), 2660: ('RemoveMonasteryTodoMessage', 2), 2690: ('Unknown2690', 2),
    2700: ('SetParalogueAvailability', 2), 2710: ('Unknown2710', 2), 2720: ('Unknown2720', 2), 2730: ('Unknown2730', 2),
    2740: ('SetNormalQuestIndicator', 2), 2750: ('HideCharacterOnMinimap', 2), 2760: ('Unknown2760', 1),
    2770: ('MonasteryLocationAvailability', 2), 2780: ('Unknown2780', 1), 2790: ('Unknown2790', 1),
    2800: ('SetFinishExploringActive', 1), 2810: ('ShowEnding', 1), 2830: ('ShowEnding1411', 2),
    2840: ('SetQuestIndicatorOnCharacter', 2), 2860: ('PlaceCharacterInAbyss', 4), 2870: ('Unknown2870', 3),
    10000: ('Unknown10000', 9),
}
CONDITIONS = {
    0: ('HasOtherScriptRun', 3), 10: ('CheckVariableValue', 4), 15: ('Unknown15', 5), 20: ('CheckFlag70', 3),
    30: ('IsStartOfMap', 1), 40: ('Unknown40', 4), 50: ('KillCheck', 4), 60: ('IsCharacterIDSlain', 3),
    70: ('HPPercentageCharacterID', 4), 80: ('CheckDeathStatus', 3), 90: ('HPPercentage', 4), 100: ('MovedCharacterOnTile', 4),
    110: ('MovedSpecificUnitInRectangle', 7), 120: ('CheckTeamSurvivors', 5), 130: ('InteractedWithTerrain', 3),
    140: ('Difficulty', 3), 170: ('IsStartOfBattle', 1), 180: ('IsStartOfPlayerPhase', 1), 190: ('IsStartOfEnemyPhase', 1),
    200: ('FirstTimeSelect', 2), 220: ('TurnNumber', 5), 230: ('IsAdjacentTo', 3), 240: ('UnitMovedIntoRangeOf', 5),
    250: ('IsRecruited', 2), 280: ('TeamMovedIntoRangeOf', 5), 300: ('DidBattleCharacterIDs2', 5),
    310: ('MovedTeamIntoSpace', 4), 320: ('MovedAnyUnitInRectangle', 7), 330: ('DidBattleCharacterIDs', 7), 340: ('Route', 3),
    350: ('DidBAIsBattle', 5), 360: ('DidBattle', 2), 370: ('BylethGender', 2), 380: ('CheckDoorOpened', 3),
    390: ('CountUnitsSlain', 4), 400: ('StartOfTeamPhase', 2), 410: ('StartOfTeamPhase2', 2),
    420: ('MovedCharacterIntoRectangle', 7), 430: ('OnlyUsedInBattleOfTheEagleAndLion', 2), 440: ('StartOfBattleMaybe', 1),
    450: ('TeamDidBattle', 5), 470: ('TeamDidBattleAndDefeat', 5), 480: ('DidCompleteMap', 1), 490: ('InventoryCheck', 4),
    500: ('RivalryoftheHousesUnused', 3), 510: ('CheckLeverActivated', 2), 520: ('IsGameMode', 3),
    530: ('WasRecruitedPreTimeskip', 2), 540: ('DidUnitsTurnEnd', 1), 550: ('CheckBattleDialogHappened', 2),
    560: ('UnkTheUndergroundChamber', 1), 570: ('CharacterRecruitedButDead', 2), 580: ('UmbralSurgeUsed', 1),
    590: ('NonAshenWolvesOnTile', 3), 1000: ('HaveTalkedToCharacter', 3), 1010: ('QuestCheck', 3), 1020: ('CheckEventFlag', 3),
    1030: ('CheckClearedAuxMapAsQuestMap', 3), 1060: ('Characters', 6), 1080: ('CheckGiftedQuestItem', 3),
    1110: ('Unknown1110', 2), 1120: ('CheckChoiceId', 4), 1130: ('RecruitmentCheckMonastery', 4),
    1150: ('InteractedWithAreaMonasteryMaybe', 7), 1160: ('Unknown1160', 2), 1170: ('CheckPlayerInMonasteryArea', 2),
    1180: ('CalendarDay', 3), 1190: ('DeathFlag', 4), 1210: ('Unused1210', 3), 1220: ('ChapterSelect', 3),
    1230: ('HaveTalkedToCharacterID', 2), 1240: ('InventoryContains', 3), 1250: ('Unused1250', 4),
    1270: ('CharacterChosenForHeron', 3), 1280: ('Unknown1280', 2), 1310: ('UnknownEdelgard', 2),
    1320: ('CheckTutorialSeen', 2), 1330: ('HasDLC', 3), 1340: ('CinderedShadowsCompletion', 3), 1350: ('IsInSunlight', 2),
    1360: ('InfluencerPerks', 3), 99998: ('AndContainer', 3), 99999: ('OrContainer', 3),
}


def _conditions(words):
    """A condition block as a tree: ('and' / 'or', [children]) for a container (its third argument the words its children take),
    else (name, args)."""
    def node(i):
        code = words[i]
        name, n = CONDITIONS[code]
        args = tuple(words[i + 1:i + 1 + n])
        if name in ('AndContainer', 'OrContainer'):
            kids, j, end = [], i + 1 + n, i + 1 + n + args[2]
            for _ in range(args[1]):
                child, j = node(j)
                kids.append(child)
            assert j == end, (j, end)
            return ('and' if name == 'AndContainer' else 'or', kids), j
        return (name, args), i + 1 + n
    out, i = [], 0
    while i < len(words):
        t, i = node(i)
        out.append(t)
    return ('and', out)


def script(scenario_no):
    """A battle's events: number, trigger (kind and three parameters), the condition tree and the actions (name, args), and whether
    the event is switched off (`off`). The trigger's first parameter is a bit field: 1 a group head (its events name it as their
    second parameter), 2 switched off. A switched-off event never runs, nor does any event in a switched-off group (each carries the
    bit itself as well): with them left out, the battles field what Fire Emblem Wiki counts (Chapter 9's 4, 5 and 7 Demonic Beasts,
    Chapter 1's five units of yours), and one of them holds a condition bsic names 'RivalryoftheHousesUnused'."""
    d = archive_file(SC_FIRST + 2 * scenario_no + 1)
    if not d:
        return []
    count = struct.unpack_from('<I', d, 8)[0]
    events = []
    for o in struct.unpack_from(f'<{count}I', d, 0x38):
        num, _, kind, p1, p2, p3, cstart, block2, acount, astart, _, end = struct.unpack_from('<12I', d, o)
        cwords = list(struct.unpack_from(f'<{(block2 - cstart) // 4}I', d, cstart))
        acts, p = [], astart
        while p < end:
            code = struct.unpack_from('<I', d, p)[0]
            name, n = ACTIONS[code]
            acts.append((name, struct.unpack_from(f'<{n}I', d, p + 4)))
            p += 4 + 4 * n
        assert p == end and len(acts) == acount, (scenario_no, num)
        events.append({'num': num, 'trigger': (kind, p1, p2, p3), 'off': bool(p1 & 2), 'conditions': _conditions(cwords),
                       'actions': acts})
    heads = {e['num']: e for e in events if e['trigger'][1] & 1}
    for e in events:
        seen, h = {e['num']}, heads.get(e['trigger'][2])
        while h is not None and h['num'] not in seen and not e['off']:
            e['off'] = h['off']
            seen.add(h['num'])
            h = heads.get(h['trigger'][2])
    return events

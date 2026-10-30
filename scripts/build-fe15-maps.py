"""
Builds Echoes: Shadows of Valentia's maps and item sources from the user's own cartridge dump (data-raw/fe15/romfs, from
scripts/fe15_extract.py):
  src/data/fe15/fe15Terrain.ts      terrain stats and movement costs, from Data/Terrain.bin
  src/data/fe15/fe15Maps.ts         every battle's grid, units, reinforcements and objectives; each dungeon's skirmish maps (the
                                    encounters its wandering foes start) and its boss battles; the cemeteries' layouts
  src/data/fe15/fe15ItemSources.ts  where each weapon, shield and ring turns up
  src/data/fe15/fe15Opens.ts        when each optional map opens
Run:
    python scripts/build-fe15-maps.py

Formats are in data-raw/fe15/README.md. Coordinates: a battle's grid (Data/Terrain/<map>.bin) is 32 x 32 tiles with the playable window
[x1, x2) x [y1, y2) in its header, counted from the top left; the app counts from (1, 1) at the bottom left.
"""
import json
import os
import re
import struct
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe13_events as E  # noqa: E402
import fe15_data as D  # noqa: E402
import gba_maps as gm  # noqa: E402
from fates_cmb import Script  # noqa: E402
from fates_lz import decompress  # noqa: E402
from fe15_bin import ROMFS, Table, load, table  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe15', 'Echoes: Shadows of Valentia', 'build-fe15-maps.py'
DIFFS = ['Normal', 'Hard']
# A placement record's +10 bits: 0x01 Normal, 0x02 / 0x04 Hard (the game's two difficulties), 0x10 the boss (a foe) or the lord.
NORMAL, HARD, BOSS = 0x01, 0x06, 0x10
# Script handler kinds (the low byte of a handler's kind) Echoes uses.
LOAD, SETTING, OPENING, COMPLETE, TURN, TURN2, REINFORCE, CONDITION, TALK = 0x07, 0x08, 0x0B, 0x0D, 0x10, 0x12, 0x13, 0x14, 0x1C

# Terrain id (Data/Terrain.bin's row) -> builder letter (terrain_codes.py's 'fe15'), by how the game treats each tile. Hills (27) and
# Flames (38) are on no battle map, so have no letter.
LETTER = {
    0: '#', 1: '.', 2: '.', 3: 'f', 4: 'f', 5: 's', 6: 'w', 7: 'w', 8: 'm', 9: 'C', 10: 'b', 11: 'a', 12: 'T', 13: '#', 14: 'K',
    15: 'S', 16: 'C', 17: 'd', 18: '#', 19: 'F', 20: 'F', 21: 'F', 22: 'H', 23: 'G', 24: '.', 25: '.', 26: '.', 28: '#',
    29: '#', 30: 'Y', 31: '.', 32: '.', 33: 'H', 34: 'C', 35: '#', 36: 'C', 37: '#', 39: 'Y', 40: 'Y', 41: 'Z', 42: 'm',
    43: 'l', 44: '.', 45: 'r', 46: 'Q', 47: '#', 48: 'R', 49: 'd', 50: '#', 51: 'T', 52: '.', 53: 'C', 54: 'w',
}
LETTER_NAME = {
    '.': 'Plain / floor', 'b': 'Bridge', 'S': 'Stairs', 'f': 'Forest', 's': 'Desert', 'w': 'River / shoal', 'm': 'Mountain / cliff',
    'C': 'Peak / rampart / cavern', 'a': 'Sea', 'Z': 'Sky', 'l': 'Partition', 'r': 'Rubble', 'T': 'Castle tile / broken bridge',
    'K': 'Bulwark', 'F': 'Fort / supplies / orange tree', 'H': 'Lava / swamp', 'G': 'Grave', 'Y': 'Pillar / thicket / coral',
    'Q': 'Sigil', 'R': 'Ruin', 'd': 'Door', '#': 'Wall / rock / pillar',
}
FLIERS = 15  # the movement cost row every flying class uses (Data/Terrain.bin's COST_飛行)

# The story as the Fire Emblem Wiki's act lists give it: (act, army, kind, world map node). Acts 3 and 4 are played by both armies at
# once, Alm's battles listed first. 'dungeon' nodes are explored: their wandering foes start skirmishes and some floors hold a boss.
STORY = [
    (0, 'Story', 'battle', 'プロローグ'),
    (1, 'Alm', 'battle', 'ラムの林'), (1, 'Alm', 'battle', '盗賊の森'), (1, 'Alm', 'dungeon', '盗賊のほこら'),
    (1, 'Alm', 'battle', 'ラムの谷'), (1, 'Alm', 'battle', '南の砦'), (1, 'Alm', 'battle', 'ソフィアの南１'),
    (1, 'Alm', 'battle', 'ソフィアの南２'), (1, 'Alm', 'dungeon', '解放軍のアジト'), (1, 'Alm', 'battle', 'ソフィアの門'),
    (2, 'Celica', 'cemetery', 'ノーヴァの墓地'), (2, 'Celica', 'battle', '海１'), (2, 'Celica', 'battle', '海２'),
    (2, 'Celica', 'battle', '海賊の砦'), (2, 'Celica', 'battle', '海３'), (2, 'Celica', 'battle', '海のほこら'),
    (2, 'Celica', 'dungeon', '海のほこら内部'), (2, 'Celica', 'battle', '海４'), (2, 'Celica', 'battle', '海５'),
    (2, 'Celica', 'battle', 'ソフィアの門２'),
    (3, 'Alm', 'battle', 'ソフィアの北'), (3, 'Alm', 'battle', 'ソフィアの森１'), (3, 'Alm', 'battle', '森の村'),
    (3, 'Alm', 'battle', 'ドゼーの砦'), (3, 'Alm', 'battle', 'ソフィアの森２'), (3, 'Alm', 'dungeon', '森のほこら'),
    (3, 'Alm', 'battle', '森の北'), (3, 'Alm', 'battle', '水門'),
    (3, 'Celica', 'battle', 'ソフィアの海岸'), (3, 'Celica', 'cemetery', '山の墓場'), (3, 'Celica', 'battle', '砂漠の砦'),
    (3, 'Celica', 'battle', '砂漠の北'), (3, 'Celica', 'battle', '砂漠の南'), (3, 'Celica', 'battle', 'ギースの砦'),
    (3, 'Celica', 'battle', 'ミラへの谷'), (3, 'Celica', 'dungeon', '竜のほこら'), (3, 'Celica', 'battle', 'ミラ神殿'),
    (4, 'Alm', 'battle', '国境'), (4, 'Alm', 'battle', 'リゲルの森'), (4, 'Alm', 'battle', '恐山'),
    (4, 'Alm', 'dungeon', '恐山のほこら'), (4, 'Alm', 'battle', 'ヌイババ館'), (4, 'Alm', 'battle', 'リゲル平野'),
    (4, 'Alm', 'battle', '竜の火口'), (4, 'Alm', 'battle', 'リゲルの滝'), (4, 'Alm', 'dungeon', '秘密のほこら'),
    (4, 'Alm', 'battle', '要塞'), (4, 'Alm', 'battle', 'リゲル城'),
    (4, 'Celica', 'battle', '死人の沼'), (4, 'Celica', 'cemetery', '沼の墓地'), (4, 'Celica', 'battle', 'ドルクの砦'),
    (4, 'Celica', 'dungeon', '迷いの森'), (4, 'Celica', 'battle', 'ドーマの門'), (4, 'Celica', 'battle', 'ドーマの沼'),
    (4, 'Celica', 'dungeon', 'ドーマの塔'),
    (5, 'Story', 'dungeon', 'ドーマ神殿'), (5, 'Story', 'battle', 'ドーマの祭壇'),
]
# What's optional: Act 6 (after the story: the seaways to Archanea and the Thabes Labyrinth) and the amiibo dungeons.
SIDE = [
    (6, 'Extra', 'battle', 'アカネイア航路２'), (6, 'Extra', 'battle', 'アカネイア航路４'), (6, 'Extra', 'battle', 'アカネイア航路６'),
    (6, 'Extra', 'dungeon', 'テーベの地下迷宮'),
    (3, 'Extra', 'dungeon', '戦神の試練'), (3, 'Extra', 'dungeon', '女神の試練'),
]
# Each dungeon node's floors (Data/Field.bin's 迷路_ fields, whose encounter field is the battle they start) and its fixed battles.
DUNGEON_FLOORS = {
    '盗賊のほこら': '迷路_盗賊のほこら', '解放軍のアジト': '迷路_解放軍のアジト', '海のほこら内部': '迷路_海のほこら',
    '森のほこら': '迷路_森のほこら', '竜のほこら': '迷路_竜のほこら', '恐山のほこら': '迷路_恐山のほこら', '秘密のほこら': '迷路_秘密のほこら',
    '迷いの森': '迷路_迷いの森', 'ドーマの塔': '迷路_ドーマの塔', 'ドーマ神殿': '迷路_ドーマ神殿', 'テーベの地下迷宮': '迷路_テーベ',
    '戦神の試練': '迷路_戦神の試練', '女神の試練': '迷路_女神の試練',
}
# A dungeon's boss battles, which a scene starts (not a wandering foe): the field (Data/Field.bin) and the groups it places.
BOSS_BATTLES = {
    '盗賊のほこら': [('戦場_盗賊のほこら_ボス', None)],
    'ドーマ神殿': [('ドーマ神殿_ベルクト戦', None), ('ドーマ神殿_王家の間１', '防衛リッチー'), ('ドーマ神殿_王家の間２', '防衛バルログ'),
                ('ドーマ神殿_王家の間３', '防衛白竜')],
    'テーベの地下迷宮': [('戦場_テーベ_門番１', None), ('戦場_テーベ_門番２', None)],
}
# Where an army starts the game (Alm in Ram Village, Celica at the Priory): a location there counts from the act's first battle, not
# from a battle next to it. Every other place (Zofia Castle, where Act 3 starts Alm, included) is first reached after a battle.
ACT_STARTS = {'ラムの村': 1, '修道院': 2}

ITEMS = D.items()
PERSONS = D.persons()
JOBS = D.jobs()
FIELDS = table('Data/Field.bin.lz').by_id
NAME_COUNT = defaultdict(int)
for _r in PERSONS.rows:
    NAME_COUNT[_r['名前']] += 1


def item_name(iid):
    return D.item_name(iid) if iid else None


# A battle fought at another node's place: Act 2's last battle is at Zofia Castle, not its gate.
PLACE_OF = {'ソフィアの門２': 'ソフィア城'}


def place(key):
    key = PLACE_OF.get(key, key)
    return D.say('MID_' + key, 'Name') or key


def battle_title(key):
    """The battle's name as the game shows it: its own title (MID_戦闘タイトル_<node>), else "<place> Battle" (MID_の戦い), the
    Prologue's from the act titles."""
    if key == 'プロローグ':
        return D.say('MID_章タイトル_PROLOGUE', 'Name')
    own = D.say('MID_戦闘タイトル_' + key, 'Name')
    if own:
        return own
    return D.say('MID_の戦い', 'Name').replace('$a$a0', place(key))


def person(pid):
    return PERSONS.by_id.get(pid)


def unit_name(pid):
    """A person's name; one with no name text (Archanea Seaway 6's ghostly Falcon Knight) goes by its class."""
    p = person(pid)
    return (D.say(p['名前'], 'Name') if p else None) or class_name(pid) or pid


def class_name(pid):
    p = person(pid)
    j = JOBS.by_id.get(p['兵種']) if p else None
    return D.say(j['名前'], 'Job') if j else None


# ---------------------------------------------------------------------------------------------------------------------------------
# Files


def grid(key):
    """A battle's terrain: (window x1, y1, x2, y2, 32 x 32 tile ids by [y][x] from the top left)."""
    d = decompress(open(os.path.join(ROMFS, 'Data', 'Terrain', key + '.bin.lz'), 'rb').read())
    _, _, x1, y1, x2, y2 = struct.unpack_from('<6I', d, 0x20)
    g = d[0x38:0x38 + 1024]
    return (x1, y1, x2, y2), [[g[y * 32 + x] for x in range(32)] for y in range(32)]


def dispos(key):
    """A placement file (Data/Dispos/<key>.bin): {group: [unit]}. Records are 96 bytes: +0 PID, +6 team (0 yours, 1 enemy, 2 green),
    +7 level (0: the person's own), +10 u16 flags, +12 start x, y and +14 end x, y (a unit marching in walks from start to end; 0, 0:
    none), +20 its item, +24 bit 0 the item drops."""
    path = os.path.join(ROMFS, 'Data', 'Dispos', key + '.bin.lz')
    if not os.path.exists(path):
        return {}
    b = load(os.path.relpath(path, ROMFS))
    dat = b.at['DAT_配置']
    out = {}
    for o, n in b.labels:
        if o < dat or n.startswith(('DAT_', 'MOD_', 'SHEET')):
            continue
        cnt, q = b.u32(o + 4), b.u32(o + 8)
        units = []
        for i in range(cnt):
            r = q + i * 96
            raw = b.d[0x20 + r:0x20 + r + 96]
            fl = raw[10] | raw[11] << 8
            units.append({'pid': b.str(r), 'team': raw[6], 'level': raw[7], 'flags': fl,
                          'difficulties': [d for d, bit in (('Normal', NORMAL), ('Hard', HARD)) if fl & bit],
                          'start': (raw[12], raw[13]), 'end': (raw[14], raw[15]), 'item': b.str(r + 20), 'drop': bool(raw[24] & 1)})
        out[n] = units
    return out


def script(key):
    path = os.path.join(ROMFS, 'Scripts', key + '.cmb')
    return E.Chapter(path) if os.path.exists(path) else None


class Window:
    def __init__(self, win):
        self.x1, self.y1, self.x2, self.y2 = win

    def app(self, x, y):
        return [x - self.x1 + 1, self.y2 - y]

    def inside(self, x, y):
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2


def grid_rows(win, g):
    return [''.join(LETTER[g[y][x]] for x in range(win.x1, win.x2)) for y in range(win.y1, win.y2)]


# ---------------------------------------------------------------------------------------------------------------------------------
# Terrain


def move_groups():
    rows = defaultdict(list)
    for i, j in enumerate(JOBS.rows):
        name = D.say(j['名前'], 'Job')
        if name and name not in ('Unknown',) and j['移動'] > 0:
            rows[j['移動タイプ']].append(i)
    out = []
    for row in sorted(rows):
        names = list(dict.fromkeys(D.say(JOBS.rows[i]['名前'], 'Job') for i in rows[row]))
        label = 'Fliers' if row == FLIERS else ', '.join(names[:3]) + (' and others' if len(names) > 3 else '')
        out.append((label, rows[row], row))
    return out


def build_terrain():
    terr = table('Data/Terrain.bin.lz')
    costs = table('Data/Terrain.bin.lz', '地形コスト')
    cols = [f for f, _ in costs.fields[1:11]]
    groups = move_groups()
    info = {}
    for tid, letter in LETTER.items():
        t = terr.rows[tid]
        code = encode(GAME, letter)
        cat = t['コスト']
        move = {}
        for label, _, row in groups:
            c = costs.rows[row][cols[cat]]
            move[label] = None if c == 255 or cat == 0 else c
        entry = {'name': LETTER_NAME[letter], 'def': 0, 'avo': t['回避'], 'heal': t['回復'], 'move': move}
        if letter == 'H':
            entry['note'] = 'Takes 5 HP from a unit standing on it each turn.'
        if letter == 'K':
            entry['note'] = 'Mounted units can\'t cross it.'
        if all(v is None for v in move.values()):
            entry['avo'] = entry['heal'] = 0
        if code in info:
            old = info[code]
            same = {k: v for k, v in old.items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}
            assert same, (letter, tid, old, entry)
        else:
            info[code] = entry
    return info, groups


# ---------------------------------------------------------------------------------------------------------------------------------
# Units


def own_weapons(pid):
    """What a unit's class fights with when nothing is equipped (Data/Job.bin's 基本装備): a monster's claws, fangs or breath."""
    p = person(pid)
    j = JOBS.by_id.get(p['兵種']) if p else None
    return [item_name(j[k]) for k in ('基本装備1', '基本装備2') if j and j[k] and ITEMS.by_id.get(j[k], {}).get('種類') == 7]


def unit_entry(u, win, where=None):
    """A placement record -> the app's unit."""
    pid = u['pid']
    p = person(pid)
    name = unit_name(pid)
    cls = class_name(pid)
    lv = u['level'] or (p['LV'] if p else 0)
    item = item_name(u['item'])
    note = ' '.join(x for x in [f'Lv {lv}' if lv else '', cls or ''] if x)
    if item:
        note += ': ' + item
    generic = bool(p and p['フラグ'] & 0x01)
    if u['team'] == 1:
        kind = 'boss' if u['flags'] & BOSS else ('enemy' if generic else 'named')
    else:
        kind = 'ally'
    e = {'type': kind, 'name': name, 'tile': win.app(*u['end']), 'note': note, '_pid': pid}
    own = own_weapons(pid)
    if own:
        e['_own'] = own
    if u['team'] == 1 and item:
        e['carries'] = [item]
        if u['drop']:
            e['drops'] = [item]
    if kind == 'ally' and generic:
        e['generic'] = True
    if set(u['difficulties']) != set(DIFFS):
        e['difficulties'] = list(u['difficulties'])
    return e


def placed_by(ch, kinds, turn=1):
    """Groups the handlers of these kinds place (any difficulty)."""
    out = []
    for hd in ch.of_kind(*kinds):
        for di in range(2):
            for g, _ in E.run(ch.s, hd, di, turn):
                if g and g not in out:
                    out.append(g)
    return out


def removed(ch, kinds):
    out = set()
    for hd in ch.of_kind(*kinds):
        out |= set(E.removed_pids(ch, hd))
    return out


def reinforcements_of(ch):
    """{group: text}: the reinforcement handlers (kind 0x13: first and last turn, phase) name the group a shared routine places."""
    out = defaultdict(list)
    for hd in ch.of_kind(REINFORCE):
        groups = [a.strip("'") for _, n, a in hd['ins'] if n == 'str']
        first, last, phase = hd['args'][:3]
        for g in groups:
            out[g].append((first, last, phase))
    text = {}
    for g, runs in out.items():
        parts = []
        for first, last, phase in sorted(runs):
            t = f'Turn {first}' if first == last or last < 0 else f'Turns {first}–{last}'
            if last < 0:
                t = f'Every turn from turn {first}'
            parts.append(t + (', enemy phase' if phase == 1 else ', player phase' if phase == 0 else ''))
        text[g] = '; '.join(parts)
    return text


def lord_of(groups):
    for u in groups.get('Player', []):
        if u['flags'] & BOSS and u['pid']:
            return u
    return None


def battle_map(mid, key, title, heading, chapter, route, location, facts, terrain_key=None, dispos_key=None, script_key=None,
               only_groups=None):
    """One battle: its grid, the units placed as it starts, reinforcements and the win rule."""
    ch = script(script_key or key)
    tkey = terrain_key or (ch.terrain_load() if ch else None) or key
    win, g = grid(tkey)
    win = Window(win)
    groups = dispos(dispos_key or key)
    m = {'id': mid, 'route': route, 'heading': heading, 'chapter': chapter, 'title': title, 'location': location,
         'width': win.x2 - win.x1, 'height': win.y2 - win.y1, 'grid': grid_rows(win, g)}
    rule = 'rout'
    if ch:
        for hd in ch.of_kind(LOAD):
            if ch.calls(hd, 'ev::ChapterSetWinRuleDestroyBoss'):
                rule = 'boss'
    # The battle's own groups: the setting places Player, Enemy and the NPC groups (and any group its load or setting handler names);
    # the opening scene's Event groups are actors in the cutscene (they repeat units of these groups, or walk your army on).
    at_start = ['Player', 'Enemy'] + [gname for gname in groups if re.fullmatch(r'NPC\d*', gname)] if only_groups is None else         list(only_groups)
    if ch and only_groups is None:
        for gname in placed_by(ch, (LOAD, SETTING)):
            if gname not in at_start:
                at_start.append(gname)
    units, starts = [], []
    lord = lord_of(groups)
    for gname in at_start:
        for u in groups.get(gname, []):
            if not u['pid'] and u['team'] != 0:
                continue
            if u['team'] == 0 and gname.startswith('Player'):
                if win.inside(*u['end']):
                    starts.append(win.app(*u['end']))
                continue
            if not win.inside(*u['end']) or not u['difficulties']:
                continue
            units.append(unit_entry(u, win))
    # A Reinforce group the placement file gives no tile (Zofia Castle's Slayde and his cavalry, Rigel Plains' Zeke and his company).
    waiting = [u for u in groups.get('Reinforce', []) if u['pid'] and u['team'] == 1 and not win.inside(*u['end'])]
    m['units'] = units
    m['starts'] = starts
    if lord and win.inside(*lord['end']):
        # The Player group's 0x10 slot is the army leader's start; its PID is a placeholder (Alm's, in Celica's battles too).
        m['corrinStart'] = win.app(*lord['end'])
        m['lord'] = route if route in ('Alm', 'Celica') else unit_name(lord['pid'])
    m['victory'] = 'Rout the enemy'
    if rule == 'boss':
        bosses = [u['name'] for u in units if u['type'] == 'boss']
        m['victory'] = f'Defeat {bosses[0]}' if bosses else 'Defeat the commander'
    lname = m.get('lord') or ('Alm' if route == 'Alm' else 'Celica' if route == 'Celica' else None)
    m['defeat'] = f'{lname} is defeated' if lname else 'Your lord is defeated'
    # Reinforcements the script names by turn.
    reinf = []
    if ch:
        for n, (gname, when) in enumerate(reinforcements_of(ch).items()):
            foes = [u for u in groups.get(gname, []) if u['pid'] and u['team'] == 1 and win.inside(*u['end']) and u['difficulties']]
            if foes:
                reinf.append({'id': f'{mid}-{n + 1}', 'label': f'Group {n + 1}', 'when': when,
                              'units': [{**unit_entry(u, win), 'from': win.app(*u['start']) if win.inside(*u['start']) else
                                         win.app(*u['end'])} for u in foes]})
    if reinf:
        m['reinforcements'] = reinf
    m['objectives'], m['objects'], m['changes'], m['notes'] = [], [], [], []
    if waiting:
        by = defaultdict(lambda: defaultdict(int))
        for u in waiting:
            for d in u['difficulties']:
                by[d][unit_name(u['pid'])] += 1
        parts = []
        for d in DIFFS:
            parts.append(f"{d}: " + ', '.join(f'{name}' + (f' ×{k}' if k > 1 else '') for name, k in by[d].items()))
        text = parts[0][len('Normal: '):] if parts[0][len('Normal: '):] == parts[1][len('Hard: '):] else '; '.join(parts)
        m['notes'].append(f'More foes join the battle later, with no tile of their own in the placement file: {text}.')
        m['unconfirmed'] = ["Where and when the later foes come in: their placement records give no tile, and the trigger isn't "
                            'decoded yet.']
        for u in waiting:
            e = unit_entry(u, win)
            if e['type'] != 'ally' and e.get('carries'):
                facts['carries'].append((e['name'], e['carries'], e.get('drops', []), True, e['type'] == 'enemy'))
    for e in units:
        if e['type'] != 'ally' and (e.get('carries') or e.get('_own')):
            facts['carries'].append((e['name'], e.get('carries', []) + e.get('_own', []), e.get('drops', []), False, e['type'] == 'enemy'))
    for gr in reinf:
        for e in gr['units']:
            if e.get('carries') or e.get('_own'):
                facts['carries'].append((e['name'], e.get('carries', []) + e.get('_own', []), e.get('drops', []), True,
                                         e['type'] == 'enemy'))
    for e in units + [u for gr in reinf for u in gr['units']]:
        pid = e.get('_pid')
        p = person(pid)
        if p and e['type'] != 'ally' and p['落下アイテム'] and p['落下率'] > 0:
            facts['random_drops'].append((e['name'], p['落下アイテム'], p['落下率'], e['type'] == 'enemy'))
    for e in units + [u for gr in reinf for u in gr['units']]:
        e.pop('_pid', None)
        e.pop('_own', None)
    return m


# ---------------------------------------------------------------------------------------------------------------------------------
# Dungeons and cemeteries


def encounters(prefix):
    """Every floor of a dungeon: its encounter field (Data/Field.bin) and its encounters (Data/Encount/<floor>.bin): wandering foes
    who start a battle when touched, each placing a group of the field's placement file."""
    out = []
    for path in sorted(os.listdir(os.path.join(ROMFS, 'Data', 'Encount'))):
        floor = path[:-7]
        if not floor.startswith(prefix):
            continue
        t = Table(load(os.path.join('Data', 'Encount', path)))
        if 'ダンジョンID' not in dict(t.fields):
            continue
        field = FIELDS.get(floor, {}).get('エンカウントフィールド')
        for r in t.rows:
            if r['ダンジョンID'] and r['配置名']:
                out.append({'floor': floor, 'field': field, 'group': r['配置名'], 'did': r['ダンジョンID'], 'rate': r['出現率'],
                            'act': r['出現章'], 'rare': r['出現フラグ'] == 'レアモン発生'})
    return out


FORMATIONS = [('EnemyU', 'ahead'), ('EnemyUL', 'ahead and to the left'), ('EnemyUR', 'ahead and to the right'), ('EnemyL', 'to the left'),
              ('EnemyR', 'to the right')]


def lineup(units):
    """'Brigand ×2' per difficulty: one text where both agree, else 'Normal: …; Hard: …'."""
    by = {}
    for d in DIFFS:
        count = defaultdict(int)
        for u in units:
            if d in u['difficulties'] and u['pid']:
                count[unit_name(u['pid'])] += 1
        by[d] = ', '.join(f'{name}' + (f' ×{k}' if k > 1 else '') for name, k in count.items())
    return by['Normal'] if by['Normal'] == by['Hard'] else f"Normal: {by['Normal']}; Hard: {by['Hard']}"


def dungeon_maps(base, n, act, route, key, facts):
    """A dungeon's maps. Its wandering foes (Data/Encount/<floor>.bin) start a battle on their floor's encounter field when touched; the
    encounter script (Scripts/Encount.cmb) sets your units on the field's Player group (Player_Good when you strike first, and the foes
    then lose 5-19% of their HP) and the foes on one of five formations (EnemyU, UL, UR, L, R), further waves on later turns. So each
    field is one map, its formations the groups, and each encounter's line-up a note. Then the dungeon's boss battles."""
    prefix = DUNGEON_FLOORS[key]
    encs = encounters(prefix)
    maps = []
    by_field = defaultdict(list)
    for e in encs:
        if e['field']:
            by_field[e['field']].append(e)
    heading = f'Act {act}' if route != 'Extra' or act == 6 else 'amiibo'
    name = place(key)
    boss_fields = {f for f, _ in BOSS_BATTLES.get(key, [])}
    fields = [f for f in by_field if f not in boss_fields]
    for field in fields:
        es = by_field[field]
        f = FIELDS[field]
        groups = dispos(f['配置データ名'])
        win, g = grid(f['地形データ名'])
        win = Window(win)
        mid = base + (chr(ord('a') + len(maps)) if len(fields) > 1 or boss_fields else '')
        title = f'{name}: skirmishes' + (f' ({len(maps) + 1})' if len(fields) > 1 else '')
        m = {'id': mid, 'route': route, 'heading': heading, 'chapter': n, 'title': title, 'location': name,
             'width': win.x2 - win.x1, 'height': win.y2 - win.y1, 'grid': grid_rows(win, g)}
        m['starts'] = [win.app(*u['end']) for u in groups.get('Player', []) if win.inside(*u['end'])]
        m['units'] = []
        m['victory'] = 'Rout the enemy'
        m['defeat'] = 'Your lord is defeated'
        reinf = []
        for gname, where in FORMATIONS:
            spots = [u for u in groups.get(gname, []) if win.inside(*u['end'])]
            if spots:
                reinf.append({'id': f'{mid}-{gname.lower()}', 'label': f'Foes {where}',
                              'when': 'One formation the encounter can set its foes on',
                              'units': [{'type': 'enemy', 'name': 'Encounter foe', 'tile': win.app(*u['end']),
                                         'note': "One of the encounter's foes stands here", 'from': win.app(*u['end'])} for u in spots]})
        good = [win.app(*u['end']) for u in groups.get('Player_Good', []) if win.inside(*u['end'])]
        notes = ['Wandering foes in the dungeon start a battle here when they touch your army. Striking one first puts your units on '
                 "the better starting tiles and takes 5–19% of the foes' HP; then the foes take one of the formations below."]
        if good and good != m['starts']:
            notes.append('Better starting tiles (when you strike first): ' + ', '.join(f'({x}, {y})' for x, y in good) + '.')
        seen = []
        for e in es:
            if e['group'] not in groups:
                continue
            us = [u for u in groups[e['group']] if u['pid']]
            if not us:
                continue
            bits = []
            if e['rare']:
                bits.append(f"rare monster, {e['rate']}% once rare monsters appear")
            elif e['rate'] < 100:
                bits.append(f"{e['rate']}% chance to be there")
            if e['act'] > 1:
                bits.append(f"from Act {e['act']}")
            text = lineup(us) + (f" ({'; '.join(bits)})" if bits else '')
            placed = [u for u in us if win.inside(*u['end']) and u['difficulties']]
            if placed:
                # A fixed encounter (a gatekeeper, the amiibo ordeals' guards): its own group places each foe on its tile.
                if not any(r['id'] == f"{mid}-{e['group']}" for r in reinf):
                    units = [{**unit_entry(u, win), 'from': win.app(*u['end'])} for u in placed]
                    for ue in units:
                        ue.pop('_pid', None)
                        ue.pop('_own', None)
                    reinf.append({'id': f"{mid}-{e['group']}", 'label': f'Fixed encounter {sum(1 for r in reinf if r["label"].startswith("Fixed")) + 1}',
                                  'when': 'Touching this foe in the dungeon starts the battle' + (f" ({'; '.join(bits)})" if bits else ''),
                                  'units': units})
            elif text not in seen:
                seen.append(text)
            for u in us:
                carried = ([item_name(u['item'])] if u['item'] else []) + own_weapons(u['pid'])
                # An encounter that only turns up from a later act (the rare monsters) counts from that act.
                if u['team'] == 1 and carried:
                    facts['carries'].append((unit_name(u['pid']), carried, [item_name(u['item'])] if u['item'] and u['drop'] else [],
                                             False, bool(person(u['pid']) and person(u['pid'])['フラグ'] & 1), e['act'], name))
                p = person(u['pid'])
                if p and p['落下アイテム'] and p['落下率'] > 0:
                    facts['random_drops'].append((unit_name(u['pid']), p['落下アイテム'], p['落下率'], bool(p['フラグ'] & 1), e['act'], name))
        if not reinf and not seen:
            continue  # a field only boss battles use (the royal chambers, Thabes' gatekeepers): those are built below
        notes += ['Encounter: ' + t for t in seen]
        m['reinforcements'] = reinf
        m['objectives'], m['objects'], m['changes'] = [], [], []
        m['notes'] = notes
        m['randomSpawns'] = True
        m['groupsNote'] = ("the formations an encounter's foes can take (one per battle), and the encounters that always stand on "
                           'their own tiles.')
        maps.append(m)
    for bi, (field, group_prefix) in enumerate(BOSS_BATTLES.get(key, [])):
        f = FIELDS[field]
        mid = base + chr(ord('a') + len(maps))
        dk = f['配置データ名'] or field
        tk = f['地形データ名']
        only = None
        if group_prefix:
            only = ['Player'] + [gname for gname in dispos(dk) if gname.startswith(group_prefix)]
        m = battle_map(mid, field, f'{name}: {boss_title(field, dk, group_prefix)}', heading, n, route, name, facts, terrain_key=tk,
                       dispos_key=dk, script_key=field.replace('ドーマ神殿_王家の間', '戦場_王家の間'), only_groups=only)
        maps.append(m)
    return maps


def boss_title(field, dk, group_prefix):
    groups = dispos(dk)
    names = []
    for gname, us in groups.items():
        if group_prefix and not gname.startswith(group_prefix):
            continue
        for u in us:
            # The boss flag, or (Duma Temple's royal chambers, which flag none) the chamber's 「_ボス」 group.
            if u['team'] == 1 and u['pid'] and (u['flags'] & BOSS or gname.endswith('_ボス')):
                names.append(unit_name(u['pid']))
    return ' and '.join(dict.fromkeys(names)) or D.say('MID_' + field, 'Name') or 'boss'


def cemetery_map(mid, key, act, route, n, facts):
    """A cemetery (Novis, the mountain graveyard, the swamp graveyard): one of its layouts (GroupN) fills it each time it's fought."""
    m = battle_map(mid, key, battle_title(key) or 'Skirmish', f'Act {act}', n, route, place(key), facts, only_groups=['Player'])
    groups = dispos(key)
    win, _ = grid(key)
    win = Window(win)
    layouts = [gname for gname in groups if re.fullmatch(r'Group\d+', gname)]
    for i, gname in enumerate(layouts):
        foes = [u for u in groups[gname] if u['pid'] and win.inside(*u['end']) and u['difficulties']]
        units = [{**unit_entry(u, win), 'from': win.app(*u['end'])} for u in foes]
        for ue in units:
            pid = ue.pop('_pid', None)
            own = ue.pop('_own', None)
            if own or ue.get('carries'):
                facts['carries'].append((ue['name'], ue.get('carries', []) + (own or []), ue.get('drops', []), False, ue['type'] == 'enemy'))
            p = person(pid)
            if p and p['落下アイテム'] and p['落下率'] > 0:
                facts['random_drops'].append((ue['name'], p['落下アイテム'], p['落下率'], ue['type'] == 'enemy'))
        m.setdefault('reinforcements', []).append({'id': f'{mid}-{i + 1}', 'label': f'Layout {i + 1}',
                                                   'when': 'One of the layouts fills the cemetery each time it is fought', 'units': units})
    m['randomSpawns'] = True
    m['groupsNote'] = 'the layouts the cemetery can be filled with: one each time it is fought.'
    m['notes'] = ['Terrors gather here again after each battle; the game picks one of the layouts below each time.']
    m['unconfirmed'] = ['How the game picks a layout (no script does it: the battle setup in the program chooses).']
    return m


# ---------------------------------------------------------------------------------------------------------------------------------
# Exploration: chests, finds, containers and gifts


def access_points():
    """Data/Access.bin: each dungeon floor's points to examine. Records are 76 bytes: +0 the part's name, +4 kind (1 a chest, 10 a
    glinting find, 2 a padlock, others statues and messages), +8 the item."""
    b = load('Data/Access.bin.lz')
    dat = b.at['DAT_地形アクセス']
    out = defaultdict(list)
    for o, n in b.labels:
        if o < dat or n.startswith(('DAT_', 'MOD_', 'SHEET')):
            continue
        cnt, q = b.u32(o + 4), b.u32(o + 8)
        for i in range(cnt):
            r = q + i * 76
            out[n].append({'part': b.str(r), 'kind': b.u32(r + 4), 'item': b.str(r + 8)})
    return out


def drop_lists():
    """Data/Dungeon.bin's containers: each floor's drop group (DG_<floor>: container, the drop list it draws from) and the lists (DL_:
    [item, weight])."""
    b = load('Data/Dungeon.bin.lz')
    by_off = {o: n for o, n in b.labels if n.startswith('DL_')}
    lists = {}
    for o, n in by_off.items():
        cnt, q = b.u32(o + 4), b.u32(o + 8)
        lists[n] = [(b.str(q + i * 8), b.u32(q + i * 8 + 4)) for i in range(cnt)]
    groups = {}
    for o, n in b.labels:
        if not n.startswith('DG_'):
            continue
        cnt, q = b.u32(o + 4), b.u32(o + 8)
        groups[n[3:]] = [(b.str(q + i * 12), by_off.get(b.u32(q + i * 12 + 4))) for i in range(cnt)]
    return groups, lists


CONTAINER = {'樽': 'barrel', '壺': 'pot', '木箱': 'box', '草': 'patch of grass'}


def event_gifts():
    """Every item an exploration event hands over (Data/Event/<location>.bin's アイテム入手 rows), with the location, the sequence and
    the act it needs at the least (a '*章' condition on the row or on the calls that lead to it)."""
    out = []
    for path in sorted(os.listdir(os.path.join(ROMFS, 'Data', 'Event'))):
        loc = path[:-7]
        b = load(os.path.join('Data', 'Event', path))
        rows = []
        for o, n in b.labels:
            if n.startswith('MOD_'):
                t = Table(b, n[4:], every=True)
                cur = None
                for r in t.rows:
                    if r['_id']:
                        cur = r['_id']
                    rows.append((cur, r))
        # Who calls each sequence, and under what act condition.
        callers = defaultdict(list)
        for seq, r in rows:
            args = [r.get(k) for k in ('引数１（ジャンプ先）', '引数２', '引数３', '引数４', '引数５', '引数６')]
            act = act_condition(r)
            for a in args:
                if isinstance(a, str) and a:
                    callers[a].append((seq, act))

        def min_act(seq, seen=()):
            if seq in seen:
                return 0
            best = None
            for parent, act in callers.get(seq, []):
                a = max(act, min_act(parent, seen + (seq,)))
                best = a if best is None else min(best, a)
            return best or 0
        for seq, r in rows:
            if r['コマンド'] == 'アイテム入手':
                iid = r['引数１（ジャンプ先）'] if isinstance(r['引数１（ジャンプ先）'], str) else None
                if iid and iid.startswith('IID_'):
                    out.append({'location': loc, 'seq': seq or '', 'iid': iid, 'act': max(act_condition(r), min_act(seq))})
            if r['コマンド'] == '仲間入り':
                for a in (r.get('引数１（ジャンプ先）'), r.get('引数２'), r.get('引数３'), r.get('引数４')):
                    if isinstance(a, str) and a and not a.startswith('*'):
                        out.append({'location': loc, 'seq': seq or '', 'join': a, 'act': max(act_condition(r), min_act(seq))})
    return out


def act_condition(r):
    """The act a row's own condition asks for at the least: ('*章', 4 = at least, n) or ('*章', 1 = exactly, n)."""
    if r['条件1'] == '*章' and isinstance(r['比較'], int):
        try:
            n = int(r['条件2'])
        except (TypeError, ValueError):
            return 0
        return n if r['比較'] in (1, 4) else 0
    return 0


# ---------------------------------------------------------------------------------------------------------------------------------


def map_id(act, route, n, key):
    """'fe15-1-3': Act 1's third map; Acts 3 and 4 number each army's own ('fe15-3a-2', 'fe15-4c-5'); the amiibo dungeons are 'fe15-x-'."""
    if route == 'Extra' and act != 6:
        return f'fe15-x-{n}'
    return f'fe15-{act}{route[0].lower() if act in (3, 4) else ""}-{n}'


# Where an exploration's floor (Access.bin, Dungeon.bin's DG_) or an event file is, when it isn't a story node itself.
FLOOR_NODE = {
    '迷路_盗賊のほこら': '盗賊のほこら', '迷路_解放軍のアジト': '解放軍のアジト', '迷路_海のほこら': '海のほこら内部', '迷路_森のほこら': '森のほこら',
    '迷路_竜のほこら': '竜のほこら', '迷路_恐山のほこら': '恐山のほこら', '迷路_秘密のほこら': '秘密のほこら', '迷路_迷いの森': '迷いの森',
    '迷路_ドーマの塔': 'ドーマの塔', '迷路_ドーマ神殿': 'ドーマ神殿', '迷路_テーベ': 'テーベの地下迷宮', '迷路_戦神の試練': '戦神の試練',
    '迷路_女神の試練': '女神の試練', '迷路_ノーヴァ修道院': '修道院', '迷路_ミラ神殿': 'ミラ神殿内部', '迷路_ドルクの砦': 'ドルクの砦内部',
}
# Scripts whose ItemGain is a story node's (a battle's, a dungeon's or its boss's).
SCRIPT_NODE = {'Dng_迷路_戦神の試練': '戦神の試練', 'Dng_迷路_女神の試練': '女神の試練', 'Dng_迷路_恐山のほこら１': '恐山のほこら',
               'Dng_迷路_テーベ_Ｂ５_門番１': 'テーベの地下迷宮', 'Dng_迷路_テーベ_Ｂ１０_門番２': 'テーベの地下迷宮'}
# Event sequences left out: the 7-Eleven quest (a Japanese promotion that hands over the Seven Sword and Eleven Shield) and the
# skip-the-scene copies of real joins.
LEFT_OUT = ('SUB711', 'アドベンチャーをスキップ')
WEAPON_KINDS = {1, 2, 3, 4, 7, 9, 10}
BLACKSMITHS = ['森の村内部', '山の村', 'リゲルの村', '賢者の里', 'フリアの港']


def main():
    info, groups = build_terrain()
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, {i: D.say(j['名前'], 'Job') for i, j in enumerate(JOBS.rows)})
    src = defaultdict(list)  # IID -> sources (the Rusted copies share a name but each evolves into its own weapon)
    name_iid = {}
    for r in ITEMS.rows:
        name = item_name(r['アイテム'])
        if name and name not in name_iid:
            name_iid[name] = r['アイテム']

    def add(iid, mid, kind, text):
        if iid and {'mapId': mid, 'kind': kind, 'text': text} not in src[iid]:
            src[iid].append({'mapId': mid, 'kind': kind, 'text': text})

    maps, first_of_act, node_map, pending = [], {}, {}, []
    counters = defaultdict(int)
    for act, route, kind, key in STORY + SIDE:
        ck = (act if route != 'Extra' or act == 6 else 'x', route if act in (3, 4) else '')
        counters[ck] += 1
        n = counters[ck]
        facts = defaultdict(list)
        mid = map_id(act, route, n, key)
        if kind == 'battle':
            ms = [battle_map(mid, key, battle_title(key) or place(key), f'Act {act}' if act else 'Prologue', n, route, place(key), facts)]
        elif kind == 'cemetery':
            ms = [cemetery_map(mid, key, act, route, n, facts)]
        else:
            ms = dungeon_maps(mid, n, act, route, key, facts)
        for m in ms:
            maps.append({k: v for k, v in m.items() if v is not None})
        mid0 = ms[0]['id']
        node_map[key] = mid0
        first_of_act.setdefault((act, route), mid0)
        first_of_act.setdefault(act, mid0)
        pending.append((mid0, act, route, facts))
    for mid0, act, route, facts in pending:
        def at(needed):
            return mid0 if not needed or needed <= act else first_of_act.get((needed, route)) or first_of_act.get(needed) or mid0
        for who, carries, drops, later, generic, *needed in facts['carries']:
            whom = (f'a foe {who}' if generic else who) + (f' in {needed[1]}' if len(needed) > 1 else '')
            mid = at(needed[0] if needed else 0)
            for name in drops:
                add(name_iid.get(name), mid, 'drop-later' if later else 'drop', f'Dropped by {whom}')
            for name in carries:
                if name not in drops:
                    add(name_iid.get(name), mid, 'foe-later' if later else 'foe', f'Carried by {whom}')
        for who, iid, rate, generic, *needed in facts['random_drops']:
            whom = (f'{who}s' if generic else who) + (f' in {needed[1]}' if len(needed) > 1 else '')
            add(iid, at(needed[0] if needed else 0), 'random-drop', f'Sometimes dropped by {whom} ({rate * 100:g}%)')
    order = {m['id']: i for i, m in enumerate(maps)}
    where = Places(node_map, first_of_act, order)

    # Dungeons' chests and glinting finds (Access.bin: kind 1 a chest, 10 something to pick up).
    for floor, points in access_points().items():
        node = where.floor_node(floor)
        if not node:
            continue
        mid, later = where.of(node)
        suffix = '-later' if later else ''
        for pt in points:
            if pt['item'] and pt['kind'] in (1, 10):
                if pt['kind'] == 1:
                    add(pt['item'], mid, 'chest' + suffix, f'In a chest in {place(node)}')
                else:
                    add(pt['item'], mid, 'find' + suffix, f'Found glinting on the ground in {place(node)}')
    # Barrels, pots, boxes and grass: a random pick from the floor's drop list.
    dg, dl = drop_lists()
    for floor, containers in dg.items():
        node = where.floor_node(floor)
        if not node:
            continue
        mid, later = where.of(node)
        for container, lst in containers:
            items = dl.get(lst, [])
            total = sum(w for _, w in items) or 1
            chance = defaultdict(int)
            for iid, w in items:
                chance[iid] += w
            for iid, w in chance.items():
                r = ITEMS.by_id.get(iid)
                if r and r['種類'] in WEAPON_KINDS:
                    add(iid, mid, 'random' + ('-later' if later else ''),
                        f"Sometimes in a {CONTAINER.get(container, container)} in {place(node)} ({100 * w / total:.3g}%)")
    # Who joins carrying what: each army's lord from their army's first map (Alm in Act 1, Celica in Act 2); the events' 仲間入り give
    # the rest.
    joined = set()
    for pid, act, army in (('PID_アルム', 1, 'Alm'), ('PID_セリカ', 2, 'Celica')):
        joined.add(pid)
        it = person(pid)['所持アイテム（IID_*)']
        if it:
            add(it, first_of_act[(act, army)], 'kit', f'Carried by {unit_name(pid)} when they join')
    # Events: what villagers and the story hand over, and who joins carrying what.
    for g in sorted(event_gifts(), key=lambda g: where.rank(g['location'], g['act'])):
        if g['seq'].startswith(LEFT_OUT) or g['location'] in ('Sample',) or not where.known(g['location']):
            continue
        mid, later = where.of(g['location'], g['act'])
        if 'iid' in g:
            r = ITEMS.by_id.get(g['iid'])
            if r and r['種類'] in WEAPON_KINDS:
                add(g['iid'], mid, 'gift' + ('-later' if later else ''), f"Given in {place(where.node(g['location']))}")
        else:
            pid = 'PID_' + g['join']
            p = person(pid)
            if not p or pid in joined:
                continue
            joined.add(pid)
            it = p['所持アイテム（IID_*)']
            if it:
                add(it, mid, 'kit' + ('-later' if later else ''), f'Carried by {unit_name(pid)} when they join')
    # Scripts' ItemGain: the story's rewards in battles and dungeons.
    for path in sorted(os.listdir(os.path.join(ROMFS, 'Scripts'))):
        key = path[:-4]
        node = SCRIPT_NODE.get(key, key if key in node_map else None)
        if not node or not path.endswith('.cmb'):
            continue
        ch = script(key)
        for hd in ch.hs:
            for iid, _ in E.item_gains(hd):
                r = ITEMS.by_id.get(iid)
                if r and r['種類'] in WEAPON_KINDS:
                    add(iid, node_map[node], 'gift', f'Given in {place(node)}')
    # Evolving at a blacksmith: a weapon (or a Rusted item: each copy turns into its own) becomes another once it has the stars.
    smiths = [where.of(b)[0] for b in BLACKSMITHS if where.known(b)]
    first_smith = min(smiths, key=lambda m: order[m])
    for r in ITEMS.rows:
        if not r['進化'] or not src.get(r['アイテム']):
            continue
        first = min(src[r['アイテム']], key=lambda s_: order[s_['mapId']])['mapId']
        at = max(first, first_smith, key=lambda m: order[m])
        base = item_name(r['アイテム'])
        for e in D.evolve(r['進化']):
            marks = [f"{e['silver']} silver mark{'s' if e['silver'] != 1 else ''}" if e['silver'] else '',
                     f"{e['gold']} gold mark{'s' if e['gold'] != 1 else ''}" if e['gold'] else '']
            cost = ' and '.join(x for x in marks if x)
            stars = f", once it has {e['stars']} star{'s' if e['stars'] != 1 else ''}" if e['stars'] else ''
            article = 'a ' if base.startswith('Rusted') else 'the '
            add(e['into'], at, 'evolve-later', f'Evolved from {article}{base} at a blacksmith ({cost}{stars})')
    # The amiibo dungeons' sources sit behind their own switch on the weapon page.
    amiibo = {m['id'] for m in maps if m['id'].startswith('fe15-x-')}
    for lst in src.values():
        for s_ in lst:
            if s_['mapId'] in amiibo and not s_['kind'].startswith('amiibo-'):
                s_['kind'] = 'amiibo-' + s_['kind']
    sources = defaultdict(list)
    for iid, lst in src.items():
        name = item_name(iid)
        for s_ in lst:
            if s_ not in sources[name]:
                sources[name].append(s_)
    gm.write_maps(GAME, TITLE, SCRIPT, [encode_grid(m) for m in maps])
    gm.write_sources(GAME, TITLE, SCRIPT, sources, prefixes=('amiibo-',))
    # When each optional map opens: Act 6 once the Final Battle is won; the amiibo dungeons with Act 3 (their chapter records' act).
    final = node_map['ドーマの祭壇']
    opens = {m['id']: final for m in maps if m['id'].startswith('fe15-6-')}
    opens.update({m['id']: first_of_act[(3, 'Alm')] for m in maps if m['id'].startswith('fe15-x-')})
    gm.write(GAME, f'{GAME}Opens.ts', [
        '/*',
        f" * GENERATED by scripts/{SCRIPT} from {TITLE}'s chapter list (Data/Chapter.bin). Do not edit by hand.",
        ' */',
        '',
        '/** Each optional map, and the story map from which it opens (Act 6: once the Final Battle is won). */',
        f'export const FE15_OPENS: Record<string, string> = {json.dumps(opens, indent=2)}',
    ])
    print('wrote', len(maps), 'maps and the sources of', len(sources), 'items')


class Places:
    """Which story map a location's sources count from. A battle or dungeon counts from its own map; where an act starts an army
    counts from that act's first map; another location (a village, a fortress's interior) from the next chapter after the battle
    beside it on the world map (Data/Chapter.bin's links), the first in story order. A gift that needs a later act counts from that
    act's first map."""

    def __init__(self, node_map, first_of_act, order):
        self.node_map, self.first_of_act, self.order = node_map, first_of_act, order
        t = D.chapters()
        labels = {o: n for o, n in t.b.labels}
        self.ch = {r['チャプター'][4:]: r for r in t.rows if r['チャプター']}
        self.links = {}
        for key, r in self.ch.items():
            self.links[key] = [labels[r[k]][4:] for k in ('上連結', '左連結', '下連結', '右連結') if r[k] and r[k] in labels]

    def node(self, loc):
        if loc not in self.ch and loc + '内部' in self.ch:
            return loc + '内部'
        return loc

    def floor_node(self, floor):
        for prefix, node in FLOOR_NODE.items():
            if floor.startswith(prefix):
                return node
        return None

    def known(self, loc):
        return self.node(loc) in self.ch or loc in self.node_map

    def army(self, node):
        r = self.ch.get(node)
        return {1: 'Alm', 2: 'Celica'}.get(r['ルート']) if r else None

    def of(self, loc, act=0):
        node = self.node(loc)
        r = self.ch.get(node)
        own_act = r['章'] if r else 0
        if act > max(own_act, ACT_STARTS.get(node, 0)):
            return self.first_of_act.get((act, self.army(node))) or self.first_of_act[act], False
        if node in self.node_map:
            return self.node_map[node], False
        if node in ACT_STARTS:
            a = ACT_STARTS[node]
            return self.first_of_act.get((a, self.army(node))) or self.first_of_act[a], False
        # The battles beside it (through paths and other places, not past a battle).
        seen, todo, found = {node}, [node], []
        while todo:
            cur = todo.pop()
            for nb in self.links.get(cur, []):
                if nb in seen:
                    continue
                seen.add(nb)
                if nb in self.node_map:
                    found.append(self.node_map[nb])
                else:
                    todo.append(nb)
        if not found:
            return self.first_of_act[own_act], False
        return min(found, key=lambda m: self.order[m]), True

    def rank(self, loc, act):
        if not self.known(loc):
            return 10 ** 6
        mid, later = self.of(loc, act)
        return self.order[mid] * 2 + later


def encode_grid(m):
    m['grid'] = [''.join(encode(GAME, c) for c in row) for row in m['grid']]
    return m


if __name__ == '__main__':
    main()

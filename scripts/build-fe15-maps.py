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
import fe15_dlc as DLC  # noqa: E402
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

# The story: (act, army, kind, world map node). Acts 3 and 4 are played by both armies at once, Alm's battles listed first where the
# game allows it: in Act 4, Alm reaching the Dragon's Maw before Duma Tower is cleared springs its trap and shuts the road on to Rigel
# Falls (Scripts/GMAP.cmb: ev::IsMoveAfterDra, and ev::DraOpen once G_ドーマの塔4_クリア is set), so Celica's Act 4 comes between.
# 'dungeon' nodes are explored: their wandering foes start skirmishes and some floors hold a boss.
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
    (4, 'Alm', 'battle', '竜の火口'),
    (4, 'Celica', 'battle', '死人の沼'), (4, 'Celica', 'cemetery', '沼の墓地'), (4, 'Celica', 'battle', 'ドルクの砦'),
    (4, 'Celica', 'dungeon', '迷いの森'), (4, 'Celica', 'battle', 'ドーマの門'), (4, 'Celica', 'battle', 'ドーマの沼'),
    (4, 'Celica', 'dungeon', 'ドーマの塔'),
    (4, 'Alm', 'battle', 'リゲルの滝'), (4, 'Alm', 'dungeon', '秘密のほこら'), (4, 'Alm', 'battle', '要塞'), (4, 'Alm', 'battle', 'リゲル城'),
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
# A dungeon's boss battles, which a scene starts (not a wandering foe): the field (Data/Field.bin), the groups it places, and the battle
# script where it isn't the field's own (Fear Mountain Shrine's statue of Duma: Dng_迷路_恐山のほこら１ asks "Test yourself in battle?"
# and runs DungeonBattle('戦場_恐山のほこら_像'), which loads the shrine's first encounter field and places Player and 恐山１の像).
BOSS_BATTLES = {
    '盗賊のほこら': [('戦場_盗賊のほこら_ボス', None)],
    '恐山のほこら': [('戦場_恐山のほこら１', '恐山１の像', '戦場_恐山のほこら_像')],
    'ドーマ神殿': [('ドーマ神殿_ベルクト戦', None), ('ドーマ神殿_王家の間１', '防衛リッチー'), ('ドーマ神殿_王家の間２', '防衛バルログ'),
                ('ドーマ神殿_王家の間３', '防衛白竜')],
    'テーベの地下迷宮': [('戦場_テーベ_門番１', None), ('戦場_テーベ_門番２', None)],
}
# The battles you can leave unfought, so they're in the second list (the user's call): the world map's links (Data/Chapter.bin) give
# another way on, and no move check (Scripts/GMAP.cmb's IsMoveBefore…) needs them won. Of the two deserts before Grieth's Citadel one is
# fought: once either army falls the other withdraws to the citadel (GMAP: GMapEscape), so the Southern Desert is listed apart. A
# dungeon's wandering-foe fields are skirmishes (the third list) wherever the dungeon is; a skippable dungeon's boss battle is optional.
SKIPPABLE = {'盗賊のほこら', '海のほこら', '恐山', '恐山のほこら', 'ヌイババ館', '砂漠の南'}
ALTERNATIVE = {'砂漠の北': '砂漠の南', '砂漠の南': '砂漠の北'}

# Where an army starts the game (Alm in Ram Village, Celica at the Priory): a location there counts from the act's first battle, not
# from a battle next to it. Every other place (Zofia Castle, where Act 3 starts Alm, included) is first reached after a battle.
ACT_STARTS = {'ラムの村': 1, '修道院': 2}

ITEMS = D.items()
PERSONS = D.persons()
JOBS = D.jobs()
FIELDS = table('Data/Field.bin.lz').by_id
# A dungeon foe's record (Data/Dungeon.bin's 敵情報, by the encounter's ダンジョンID): its スクリプト is the battle script it starts.
DUNGEON_FOES = table('Data/Dungeon.bin.lz', '敵情報').by_id
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
    +7 level (0: the person's own), +8 the levels Hard adds (the level routine, 0x42df34: +8 when the difficulty byte is 1; +9, for a
    2, is 0 in every record), +10 u16 flags, +12 start x, y and +14 end x, y (a unit marching in walks from start to end; 0, 0: none),
    +20 its item, +24 bit 0 the item drops."""
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
            units.append({'pid': b.str(r), 'team': raw[6], 'level': raw[7], 'hard': raw[8], 'flags': fl,
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
    # Hard adds the record's +8 levels: one entry says both ('Lv 5 (Hard 7)': the map shows the picked difficulty's), a Hard-only
    # record its Hard level.
    hard = lv + u.get('hard', 0)
    ds = u['difficulties']
    lv_text = (f'Lv {lv} (Hard {hard})' if 'Normal' in ds and 'Hard' in ds and hard != lv else
               f'Lv {hard}' if ds == ['Hard'] else f'Lv {lv}') if lv else ''
    item = item_name(u['item'])
    note = ' '.join(x for x in [lv_text, cls or ''] if x)
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
                facts['carries'].append((e['name'], e['carries'], e.get('drops', []), True, e['type'] == 'enemy', e.get('difficulties')))
    # What foes carry and drop, with the difficulties they're placed on (None: both).
    for e in units:
        if e['type'] != 'ally' and (e.get('carries') or e.get('_own')):
            facts['carries'].append((e['name'], e.get('carries', []) + e.get('_own', []), e.get('drops', []), False, e['type'] == 'enemy',
                                     e.get('difficulties')))
    for gr in reinf:
        for e in gr['units']:
            if e.get('carries') or e.get('_own'):
                facts['carries'].append((e['name'], e.get('carries', []) + e.get('_own', []), e.get('drops', []), True,
                                         e['type'] == 'enemy', e.get('difficulties')))
    for e in units + [u for gr in reinf for u in gr['units']]:
        pid = e.get('_pid')
        p = person(pid)
        if p and e['type'] != 'ally' and p['落下アイテム'] and p['落下率'] > 0:
            facts['random_drops'].append((e['name'], p['落下アイテム'], p['落下率'], e['type'] == 'enemy', e.get('difficulties')))
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
        # Encounters that share a group (グループ) are one pick among them, the empty picks (DID_なし) included, so each one's chance
        # is its figure (出現率) over the group's; one in no group is there at its figure, or (a request's foe) while its flag is set.
        totals = defaultdict(int)
        for r in t.rows:
            if r['ダンジョンID'] and r['ダンジョンID'] != 'エンカウント' and r['グループ']:
                totals[r['グループ']] += r['出現率']
        for r in t.rows:
            if r['ダンジョンID'] and r['配置名']:
                chance = 100 * r['出現率'] / totals[r['グループ']] if r['グループ'] else r['出現率']
                flag = r['出現フラグ']
                out.append({'floor': floor, 'field': field, 'group': r['配置名'], 'did': r['ダンジョンID'], 'rate': round(chance),
                            'act': r['出現章'], 'rare': flag == 'レアモン発生',
                            'request': bool(flag and flag.startswith('G_SUB_'))})
    return out


FORMATIONS = [('EnemyU', 'ahead'), ('EnemyUL', 'ahead and to the left'), ('EnemyUR', 'ahead and to the right'), ('EnemyL', 'to the left'),
              ('EnemyR', 'to the right')]


def plural(name):
    """'Witch' -> 'Witches', 'Mogall' -> 'Mogalls'."""
    return name + ('es' if name.endswith(('ch', 'sh', 's', 'x')) else 's')


def lineup(units):
    """[(text, difficulties)]: 'Brigand ×2', one line where both difficulties agree, else one per difficulty."""
    by = {}
    for d in DIFFS:
        count = defaultdict(int)
        for u in units:
            if d in u['difficulties'] and u['pid']:
                count[unit_name(u['pid'])] += 1
        by[d] = ', '.join(f'{name}' + (f' ×{k}' if k > 1 else '') for name, k in count.items())
    return [(by['Normal'], DIFFS)] if by['Normal'] == by['Hard'] else [(by[d], [d]) for d in DIFFS if by[d]]


def dungeon_maps(base, n, act, route, key, facts_of):
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
    battles = BOSS_BATTLES.get(key, [])
    # A boss battle on a field of its own takes that field out of the skirmishes; one with its own script shares the field.
    boss_fields = {b[0] for b in battles if len(b) < 3}
    fields = [f for f in by_field if f not in boss_fields]
    for field in fields:
        es = by_field[field]
        f = FIELDS[field]
        groups = dispos(f['配置データ名'])
        win, g = grid(f['地形データ名'])
        win = Window(win)
        mid = base + (chr(ord('a') + len(maps)) if len(fields) > 1 or battles else '')
        facts = facts_of(mid)
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
        # The amiibo ordeals have no wandering foes and no formations: only guards, each on its own tiles, whose battles run
        # Scripts/戦場_amiibo.cmb (the same first strike as Encount.cmb).
        guards_only = not reinf
        if guards_only:
            notes = ["Touching one of the dungeon's guards starts its battle here, with its foes on their own tiles below. Striking it "
                     "first puts your units on the better starting tiles and takes 5–19% of the foes' HP."]
            if any(DUNGEON_FOES.get(e['did'], {}).get('スクリプト') == '戦場_amiibo' for e in es):
                # Its turn-1 handler: a guard whose death set its 'G_<dungeon>_<n>' variable has its item drop turned off.
                notes.append("Each guard's item drops only the first time it's beaten: on later visits the battle script "
                             '(Scripts/戦場_amiibo.cmb) takes the drop off.')
        else:
            notes = ['Wandering foes in the dungeon start a battle here when they touch your army. Striking one first puts your units '
                     "on the better starting tiles and takes 5–19% of the foes' HP; then the foes take one of the formations below."]
        if guards_only:
            m['title'] = name
        else:
            m['unconfirmed'] = ["How an encounter's foes are picked where several share a group: their chances here are each one's "
                                "figure over the group's, an empty pick included."]
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
            elif e['request']:
                bits.append("placed while a villager's request is open")
            elif e['rate'] < 100:
                bits.append(f"{e['rate']}% chance to be there")
            if e['act'] > 1:
                bits.append(f"from Act {e['act']}")
            lines = [(t + (f" ({'; '.join(bits)})" if bits else ''), ds) for t, ds in lineup(us)]
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
            else:
                for line in lines:
                    if (line, e['act']) not in seen:
                        seen.append((line, e['act']))
            for u in us:
                carried = ([item_name(u['item'])] if u['item'] else []) + own_weapons(u['pid'])
                # An encounter that only turns up from a later act (the rare monsters) counts from that act.
                if u['team'] == 1 and carried:
                    facts['carries'].append((unit_name(u['pid']), carried, [item_name(u['item'])] if u['item'] and u['drop'] else [],
                                             False, bool(person(u['pid']) and person(u['pid'])['フラグ'] & 1), u['difficulties'],
                                             e['act'], name))
                p = person(u['pid'])
                if p and p['落下アイテム'] and p['落下率'] > 0:
                    facts['random_drops'].append((unit_name(u['pid']), p['落下アイテム'], p['落下率'], bool(p['フラグ'] & 1), u['difficulties'],
                                                  e['act'], name))
        if not reinf and not seen:
            continue  # a field only boss battles use (the royal chambers, Thabes' gatekeepers): those are built below
        # Each encounter's line on the difficulties it holds on, from the act it turns up in (main() gives the act's first map).
        m['_encounters'] = [('Encounter: ' + t, ds, a) for (t, ds), a in seen]
        m['reinforcements'] = reinf
        m['objectives'], m['objects'], m['changes'] = [], [], []
        m['notes'] = notes
        m['randomSpawns'] = not guards_only
        m['groupsNote'] = ("the dungeon's guards, each a battle of its own." if guards_only else
                           "the formations an encounter's foes can take (one per battle), and the encounters that always stand on "
                           'their own tiles.')
        # The wandering foes' battles are skirmishes, in a list of their own; the amiibo ordeals' guards are optional battles.
        m['_list'] = 'optional' if guards_only else 'skirmishes'
        maps.append(m)
    for bi, (field, group_prefix, *own_script) in enumerate(battles):
        f = FIELDS[field]
        mid = base + chr(ord('a') + len(maps))
        dk = f['配置データ名'] or field
        tk = f['地形データ名']
        only = None
        if group_prefix:
            only = ['Player'] + [gname for gname in dispos(dk) if gname.startswith(group_prefix)]
        battle = own_script[0] if own_script else field.replace('ドーマ神殿_王家の間', '戦場_王家の間')
        title = STATUE if own_script else boss_title(field, dk, group_prefix)
        m = battle_map(mid, field, f'{name}: {title}', heading, n, route, name, facts_of(mid), terrain_key=tk,
                       dispos_key=dk, script_key=battle, only_groups=only)
        m['_battle'] = battle
        if key in SKIPPABLE:
            m['_list'] = 'optional'
        if own_script:
            m['notes'].insert(0, "Answering the statue of Duma's challenge in the shrine (\"Test yourself in battle?\") starts this battle, "
                                 "once: winning it gives Duma's Lance.")
        maps.append(m)
    return maps


# The statue of Duma's battle in Fear Mountain Shrine: the game names it after the statue (MID_DNG_恐山のほこら_ドーマ像_*).
STATUE = 'Statue of Duma'


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


def node_placements(node):
    """Data/Chapter.bin's 配置 list for a world-map node (a DID_ record: its count and a list of 28-byte entries): [(group, kind, act,
    figure, level)]. Kind 1: the army there from the start (a cemetery's first layout; a castle's Enemy and Reinforce groups); 2: the
    army a level brings (the Dragon's Maw Interior's Necrodragons); 3: an army that gathers there again after a battle (a cemetery's
    layouts), with its figure."""
    b = D.chapters().b
    start = next(o for o, n in b.labels if n == 'DAT_配置')
    end = next(o for o, n in b.labels if n == 'MOD_経路')
    for o in range(start, end, 12):
        if struct.unpack_from('<I', b.d, 0x20 + o)[0] and b.str(o) == 'DID_' + node:
            count, lst = struct.unpack_from('<2I', b.d, 0x20 + o + 4)
            out = []
            for k in range(count):
                r = lst + k * 28
                kind, act, figure, level = b.d[0x20 + r + 16:0x20 + r + 20]
                out.append((b.str(r + 4), kind, act, figure, level))
            return out
    return []


def slot_fill(units, slots, win):
    """A world-map army's units on the battle's Enemy records (a cemetery's, the Dragon's Maw's: the army's own records have no tile):
    each difficulty's units in record order on the slots in record order, one entry where both difficulties agree."""
    entries = []
    at = {d: {id(u): k for k, u in enumerate(u_ for u_ in units if d in u_['difficulties'] and u_['pid'])} for d in DIFFS}
    for u in units:
        if not u['pid']:
            continue
        ks = {at[d][id(u)] for d in u['difficulties']}
        if len(ks) == 1:
            # The same slot on each of its difficulties: one entry, its Hard level beside its Normal one.
            k = ks.pop()
            if k < len(slots) and win.inside(*slots[k]['end']):
                entries.append(unit_entry({**u, 'end': slots[k]['end']}, win))
            continue
        for d in u['difficulties']:
            k = at[d][id(u)]
            if k < len(slots) and win.inside(*slots[k]['end']):
                entries.append(unit_entry({**u, 'end': slots[k]['end'], 'difficulties': [d]}, win))
    merged = []
    for e in entries:
        same = {k: v for k, v in e.items() if k != 'difficulties'}
        twin = next((x for x in merged if {k: v for k, v in x.items() if k != 'difficulties'} == same), None)
        if twin:
            twin['difficulties'] = [d for d in DIFFS if d in twin.get('difficulties', DIFFS) + e.get('difficulties', DIFFS)]
        else:
            merged.append(dict(e))
    for e in merged:
        if e.get('difficulties') == DIFFS:
            e.pop('difficulties')
    return merged


def unit_facts(entries, facts, later=False):
    """What placed units carry and drop, for the sources; drops the entries' private fields."""
    for e in entries:
        if e['type'] != 'ally' and (e.get('carries') or e.get('_own')):
            facts['carries'].append((e['name'], e.get('carries', []) + e.get('_own', []), e.get('drops', []), later, e['type'] == 'enemy',
                                     e.get('difficulties')))
        p = person(e.get('_pid'))
        if p and e['type'] != 'ally' and p['落下アイテム'] and p['落下率'] > 0:
            facts['random_drops'].append((e['name'], p['落下アイテム'], p['落下率'], e['type'] == 'enemy', e.get('difficulties')))
        e.pop('_pid', None)
        e.pop('_own', None)


def refight_map(first, rid, title, layouts, notes, unconfirmed, groups_note):
    """A battle's later fights on its map: the layouts (label, when, units) as groups, in the third list."""
    m = {'id': rid, **{k: v for k, v in first.items() if k in ('route', 'heading', 'chapter', 'location', 'width', 'height', 'grid',
                                                                 'starts', 'corrinStart', 'lord', 'defeat')}}
    m.update({'title': title, 'units': [], 'victory': 'Rout the enemy', 'objectives': [], 'objects': [], 'changes': [],
              'notes': notes, 'unconfirmed': unconfirmed, 'randomSpawns': True, 'groupsNote': groups_note, '_list': 'skirmishes'})
    m['reinforcements'] = [{'id': f'{rid}-{i + 1}', 'label': label, 'when': when, 'units': [{**u, 'from': u['tile']} for u in units]}
                           for i, (label, when, units) in enumerate(layouts) if units]
    return m


SLOT_ORDER = ("Which tile each foe takes: the army's foes in their record order on the Enemy group's records in theirs (the "
              "program's pairing isn't traced).")


def cemetery_maps(mid, key, act, route, n, facts_of):
    """A cemetery (Novis, the mountain graveyard, the swamp graveyard): its first battle, the layout its kind-1 placement names, and
    its later battles, when Terrors gather there again: one of its kind-3 layouts, each with the game's figure (Data/Chapter.bin's
    配置). A layout's foes have no tiles of their own: they take the Enemy group's records'."""
    first = battle_map(mid, key, battle_title(key) or 'Skirmish', f'Act {act}', n, route, place(key), facts_of(mid), only_groups=['Player'])
    groups = dispos(key)
    win, _ = grid(key)
    win = Window(win)
    slots = [u for u in groups.get('Enemy', []) if not u['pid']]
    plan = node_placements(key)
    for gname, kind, *_ in plan:
        if kind == 1:
            units = slot_fill(groups.get(gname, []), slots, win)
            unit_facts(units, facts_of(mid))
            first['units'] += units
    first['notes'] = ['Terrors gather here again after the battle: the later fights are under Skirmishes.']
    first['unconfirmed'] = [SLOT_ORDER]
    rid = mid + 'r'
    layouts = []
    for gname, kind, _, figure, _ in plan:
        if kind == 3:
            units = slot_fill(groups.get(gname, []), slots, win)
            unit_facts(units, facts_of(rid))
            layouts.append((f'Layout {gname[5:]}' if gname.startswith('Group') else gname,
                            f'Can gather here after a battle (the game gives it a figure of {figure})', units))
    # A villager's request can put a Revenant with what they're after here on a later battle (the setting's Dispos, while the request
    # is open, by a counter and a saved random number: 山の墓場's SUB29 / SUB33 groups).
    for gname, us in groups.items():
        if gname.startswith('SUB'):
            units = [{**unit_entry(u, win)} for u in us if u['pid'] and win.inside(*u['end']) and u['difficulties']]
            unit_facts(units, facts_of(rid))
            layouts.append((f"Request foe {sum(1 for x in layouts if x[0].startswith('Request')) + 1}",
                            "On a later battle while a villager's request is open, now and then (a counter and a saved random number "
                            'decide)', units))
    later = refight_map(first, rid, f'{place(key)}: skirmishes', layouts,
                        ['Terrors gather here again after each battle: one of the layouts below, by the figures the game gives them.'],
                        ['How the game turns the layouts\' figures into a pick.', SLOT_ORDER],
                        'the layouts the cemetery can be filled with: one each time it is fought.')
    return [first, later]


# The Dragon's Maw: each win there in Act 4 raises the level of the Necrodragon army inside (竜の火口.cmb's closing handler:
# SpotSetDisposLevel('竜の火口内部', its level + 1, at most 5)), and the next battle there brings the army that level names.
RETURNS = {'竜の火口': '竜の火口内部'}


def returns_map(first, key, interior, facts_of):
    groups = dispos(key)
    win, _ = grid(key)
    win = Window(win)
    slots = groups.get('Enemy', [])
    army = dispos(interior)
    rid = first['id'] + 'r'
    layouts = []
    for gname, kind, _, figure, level in node_placements(interior):
        if kind == 2:
            units = slot_fill(army.get(gname, []), slots, win)
            unit_facts(units, facts_of(rid))
            layouts.append((f'Level {level}', f"After {level} win{'s' if level > 1 else ''} here (the game gives this army a figure of "
                                              f'{figure})', units))
    first['notes'].append('Each win here in Act 4 raises the level of the Necrodragon army inside (at most 5): the bigger armies '
                          'it sends back are under Skirmishes.')
    return refight_map(first, rid, f'{place(key)}: skirmishes', layouts,
                       ["Each win here in Act 4 raises the level of the Necrodragon army inside, and the next battle brings that "
                        "level's army."],
                       ["What each army's figure does when it comes back.", SLOT_ORDER],
                       'the armies each level of the Necrodragons brings back.')


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
# Dungeon scripts whose ItemGain rewards one of its battles: the battle (its script) and what the line says. Fear Mountain Shrine's
# statue gives Duma's Lance once its battle is won (撃破済み); Thabes' B10 gatekeeper gives the Rusted Ring once The Creation
# (its ギムレーＡ) has fallen.
SCRIPT_BATTLE = {'Dng_迷路_恐山のほこら１': ('戦場_恐山のほこら_像', "Given for winning the statue of Duma's battle in {place}"),
                 'Dng_迷路_テーベ_Ｂ１０_門番２': ('戦場_テーベ_門番２', 'Given for defeating The Creation in {place}')}
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

    # (item name, map id, kind, text) -> the difficulties the line holds on; by name, as the Rusted copies' lines are merged below.
    held = defaultdict(set)

    def add(iid, mid, kind, text, ds=None):
        """`ds`: the difficulties of the placed unit the line comes from (None: both, as for anything else)."""
        if not iid:
            return
        if {'mapId': mid, 'kind': kind, 'text': text} not in src[iid]:
            src[iid].append({'mapId': mid, 'kind': kind, 'text': text})
        held[(item_name(iid), mid, kind, text)] |= set(DIFFS if ds is None else ds)

    maps, first_of_act, node_map, pending = [], {}, {}, []
    counters = defaultdict(int)
    # What each map's foes carry and drop: the map's own (a dungeon's boss battle's are its own, not the dungeon's first map's).
    facts_by = defaultdict(lambda: defaultdict(list))
    for act, route, kind, key in STORY + SIDE:
        ck = (act if route != 'Extra' or act == 6 else 'x', route if act in (3, 4) else '')
        counters[ck] += 1
        n = counters[ck]
        mid = map_id(act, route, n, key)
        if kind == 'battle':
            ms = [battle_map(mid, key, battle_title(key) or place(key), f'Act {act}' if act else 'Prologue', n, route, place(key),
                             facts_by[mid])]
            if key in SKIPPABLE or route == 'Extra':
                ms[0]['_list'] = 'optional'
            if key in RETURNS:
                ms.append(returns_map(ms[0], key, RETURNS[key], lambda m_: facts_by[m_]))
        elif kind == 'cemetery':
            ms = cemetery_maps(mid, key, act, route, n, lambda m_: facts_by[m_])
        else:
            ms = dungeon_maps(mid, n, act, route, key, lambda m_: facts_by[m_])
        for m in ms:
            if route == 'Extra' and m.get('_list') != 'skirmishes':
                m['_list'] = 'optional'
            if key in ALTERNATIVE:
                m['notes'].insert(0, f"You fight this battle or the {battle_title(ALTERNATIVE[key])}, not both: once one army falls, the "
                                     "other withdraws to Grieth's Citadel.")
            maps.append({k: v for k, v in m.items() if v is not None})
            pending.append((m['id'], act, route, facts_by[m['id']]))
        mid0 = ms[0]['id']
        node_map[key] = mid0
        first_of_act.setdefault((act, route), mid0)
        first_of_act.setdefault(act, mid0)
    battle_ids = {m['_battle']: m['id'] for m in maps if m.get('_battle')}
    # An encounter line holds from the act it turns up in: under the spoiler block it waits for that act's first map.
    for m in maps:
        for text, ds, a in m.pop('_encounters', []):
            on = {'note': text, 'difficulties': list(ds)}
            own = int(m['heading'][4:]) if m['heading'].startswith('Act ') else 0
            if a > own:
                on['from'] = first_of_act.get((a, m['route'])) or first_of_act[a]
            m.setdefault('notesOn', []).append(on)
    for mid0, act, route, facts in pending:
        def at(needed):
            return mid0 if not needed or needed <= act else first_of_act.get((needed, route)) or first_of_act.get(needed) or mid0
        for who, carries, drops, later, generic, ds, *needed in facts['carries']:
            whom = (f'a foe {who}' if generic else who) + (f' in {needed[1]}' if len(needed) > 1 else '')
            mid = at(needed[0] if needed else 0)
            for name in drops:
                add(name_iid.get(name), mid, 'drop-later' if later else 'drop', f'Dropped by {whom}', ds)
            for name in carries:
                if name not in drops:
                    add(name_iid.get(name), mid, 'foe-later' if later else 'foe', f'Carried by {whom}', ds)
        # Person.bin's 落下率 is already a percentage (0.09: Fire Emblem Wiki's 0.09% for a Bonewalker's Rusted Sword). Foes of
        # one class with different rates (a Witch and a stronger Witch) share a row; where the rates differ by difficulty (Dragon
        # Shrine's Revenants drop a Rusted Shield at 0.25% on Normal, 0.5% on Hard), each difficulty's rates get a row of their own.
        rates = defaultdict(lambda: defaultdict(set))  # (item, map, whom) -> difficulty -> rates
        for who, iid, rate, generic, ds, *needed in facts['random_drops']:
            whom = (plural(who) if generic else who) + (f' in {needed[1]}' if len(needed) > 1 else '')
            key = (iid, at(needed[0] if needed else 0), whom)
            for d in (DIFFS if ds is None else ds):
                rates[key][d].add(round(rate, 2))
        for (iid, mid, whom), by in rates.items():
            rows = defaultdict(list)  # the rates -> the difficulties with those
            for d in DIFFS:
                if d in by:
                    rows[tuple(sorted(by[d]))].append(d)
            for rs, ds in rows.items():
                add(iid, mid, 'random-drop', f"Sometimes dropped by {whom} ({' or '.join(f'{r:g}%' for r in rs)})", ds)
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
        battle, text = SCRIPT_BATTLE.get(key, (None, 'Given in {place}'))
        for hd in ch.hs:
            for iid, _ in E.item_gains(hd):
                r = ITEMS.by_id.get(iid)
                if r and r['種類'] in WEAPON_KINDS:
                    add(iid, battle_ids[battle] if battle else node_map[node], 'gift', text.format(place=place(node)))
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
    # A line from units placed on one difficulty only says which (the copies of an item that share its name share the line).
    for iid, lst in src.items():
        for s_ in lst:
            on = held[(item_name(iid), s_['mapId'], s_['kind'], s_['text'])]
            if on != set(DIFFS):
                s_['difficulties'] = [d for d in DIFFS if d in on]
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
    # The DLC's rewards (Fire Emblem Wiki's: scripts/fe15_dlc.py), from when the world map's Connect menu first opens. Behind
    # their own switch.
    for name, (pack, dlc_map, how) in DLC.REWARDS.items():
        sources[name].append({'mapId': DLC.OPENS_AT, 'kind': 'dlc-reward', 'text': f'DLC map {dlc_map} ({pack}): {how}, once'})
    # The list each map is in: the story (the battles everyone fights), the optional battles (the skippable ones, Act 6 and the amiibo
    # ordeals) and the skirmishes (the dungeons' wandering foes). And the story map from which each of the others opens: the first
    # story map after it; Act 6 with the Final Battle (the story is over: the user's spoiler rule), the amiibo dungeons with Act 3 (their
    # chapter records' act).
    lists = {m['id']: m.pop('_list') for m in maps if m.get('_list')}
    for m in maps:
        m.pop('_battle', None)
    story = [m['id'] for m in maps if m['id'] not in lists]
    final = node_map['ドーマの祭壇']
    opens = {}
    for i, m in enumerate(maps):
        if m['id'] not in lists:
            continue
        if m['id'].startswith('fe15-6-'):
            opens[m['id']] = final
        elif m['id'].startswith('fe15-x-'):
            opens[m['id']] = first_of_act[(3, 'Alm')]
        else:
            opens[m['id']] = next((x['id'] for x in maps[i + 1:] if x['id'] in story), final)
    # Act 6 also waits on a request: its world map announces "A foreign trading ship has arrived at Zofia Harbor." and keeps Archanea
    # Seaway 1 shut until the quest that goes with it is taken (GMAP: G_SUB_40遙かなる遠き大地).
    for m in maps:
        if m['id'] == 'fe15-6-1':
            m['notes'].insert(0, "Act 6 opens once the Final Battle is won: the world map then tells of a foreign trading ship at Zofia "
                                 "Harbor, and Archanea Seaway 1 opens once the request that goes with it is taken.")
    gm.write_maps(GAME, TITLE, SCRIPT, [encode_grid(m) for m in maps])
    gm.write_sources(GAME, TITLE, SCRIPT, sources, prefixes=('amiibo-', 'dlc-'), diffs=DIFFS)
    gm.write(GAME, f'{GAME}Opens.ts', [
        '/*',
        f" * GENERATED by scripts/{SCRIPT} from {TITLE}'s chapter list (Data/Chapter.bin) and world map script. Do not edit by hand.",
        ' */',
        '',
        "/** Each map outside the story's list, and the story map from which it opens (Act 6: the Final Battle). */",
        f'export const FE15_OPENS: Record<string, string> = {json.dumps(opens, indent=2)}',
        '',
        "/** The list each of those maps is in: the optional battles (the second list) or the skirmishes (the third). */",
        f"export const FE15_LISTS: Record<string, 'optional' | 'skirmishes'> = {json.dumps(lists, indent=2)}",
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

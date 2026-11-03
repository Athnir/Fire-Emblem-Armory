"""
Builds src/data/fe17/fe17Maps.ts, fe17Terrain.ts, fe17ItemSources.ts and fe17Opens.ts: Fire Emblem Engage's battles (the story,
the paralogues, Fell Xenologue, the skirmishes and the Tempest Trials), read from the game's own chapter table, terrain grids, unit
placements and battle scripts (scripts/fe17_data.py, scripts/fe17_events.py; data-raw/fe17/README.md). Run (a few minutes):
    python scripts/build-fe17-maps.py

Each battle is played by its script on each difficulty: what the game places at the start and the opening leaves on the map are
its units; what the turns place, and what each of the chapter's events brings on or holds back (a defeat, a fight, an area, a unit
reaching a tile, an AI starting: `arrivals`), are its groups and joiners, with every turn they come on; what a village visit or a
chest's event gives is the village's or the chest's. Coordinates: the game's x across and z up
from the bottom row (0-based), inside the terrain grid's window; the app's (1, 1) is the window's bottom-left tile.
"""
import functools
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe17_data as D  # noqa: E402
import fe17_events as E  # noqa: E402
import gba_maps as gm  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME = 'fe17'
TITLE = 'Fire Emblem Engage'
SCRIPT = 'build-fe17-maps.py'
DIFFS = ['Normal', 'Hard', 'Maddening']
STORY = ['M%03d' % k for k in range(27)]
# The paralogues and the Divine Paralogues (DLC): the second list. Each opens once the chapter its world map spot names
# (chapter.xml GmapSpotOpenCondition) is cleared; the first Divine Paralogue names none: it opens once Chapter 6 is cleared (Fire
# Emblem Wiki), and the other five once it's cleared.
SIDE = ['S%03d' % k for k in range(1, 16)] + ['G%03d' % k for k in range(1, 7)]
DIVINE_OPENS = 'M006'
# Fell Xenologue (DLC): a story of its own (the user's call), entered from the Somniel's Ancient Well (Fire Emblem Wiki), which opens
# once Chapter 6 is cleared (hubarea.xml); its chapters follow each other.
XENO = ['E%03d' % k for k in range(1, 7)]
WELL = 'AID_不思議な井戸'
ROUTE = {'M': 'Story', 'S': 'Paralogue', 'G': 'Paralogue', 'E': 'Fell Xenologue'}
TURNS = 40
LEADER = 16          # App.DisposData.Flags: Leader (the boss)
POS = 128            # a deployment tile
MUST = 256
LORD = 'PID_リュール'
MOVE_GROUPS = [('Infantry', 'Foot', 1), ('Cavalry', 'Horse', 2), ('Fliers', 'Fly', 3), ('Dragons', 'Dragon', 4)]
PHASE = {0: 'player phase', 1: 'enemy phase', 2: 'ally phase'}
# A cause also set off this many turns in: a group whose time moves with it comes so many phases after it; one that doesn't waits
# for its own turns.
LATE = 5
EVERY = {1: 'every turn', 2: 'every other turn', 3: 'every third turn', 4: 'every fourth turn', 5: 'every fifth turn',
         6: 'every sixth turn'}
# The armory, item shop and smithy open with these chapters cleared (hubarea.xml 施設情報); a shop list's own condition names the
# chapter whose clearing adds it.
FACILITY = {'armory': 'AID_武器屋', 'item': 'AID_道具屋', 'smithy': 'AID_錬成屋', 'flea': 'AID_蚤の市'}

# Each terrain kind by the game's terrain id: its letter (scripts/terrain_codes.py GAME['fe17']).
LETTER = {
    'TID_平地': '.', 'TID_草原': '.', 'TID_地面': '.', 'TID_甲板': '.', 'TID_床': '.', 'TID_加勢マス': '.', 'TID_謎の平地': '.',
    'TID_起動盤': '.', 'TID_火山弾跡': '.', 'TID_魔法陣': '.', 'TID_船着き場': '.', 'TID_床_ターゲット・ワープ禁': '.',
    'TID_床_氷結界': '.', 'TID_魔法陣_氷結界': '.',
    # A floor every unit crosses that carries a battle prohibition (its Prohibition: All; what it stops isn't traced): floor.
    'TID_床_全戦禁': '.',
    'TID_道': 'R', 'TID_橋': 'b', 'TID_壊れた橋': 'b', 'TID_階段': 'S', 'TID_階段_戦禁': 'S',
    'TID_砂漠': 's', 'TID_砂浜': 's', 'TID_砂浜_M016': 's', 'TID_流砂': 's',
    'TID_浅瀬': 'h', 'TID_砂場': 'h', 'TID_金貨の山': 'h', 'TID_泉': 'h', 'TID_氷の床': 'I',
    'TID_茂み': 'f', 'TID_林': 'f', 'TID_砦': 'F', 'TID_柱': 'p', 'TID_柱_ターゲット・ワープ禁': 'p', 'TID_サボテン': 'f',
    'TID_ローズアーチ': 'f', 'TID_遺跡': 'f',
    'TID_回復床': 'H', 'TID_防衛床': 'P', 'TID_防衛床_ターゲット・ワープ禁': 'P',
    'TID_川': 'w', 'TID_水路': 'w', 'TID_海': 'a', 'TID_海_影無': 'a', 'TID_湖': 'a', 'TID_池': 'a', 'TID_海_全戦禁': '#',
    'TID_山': 'C', 'TID_崖': 'C', 'TID_空': 'x', 'TID_岩': 'K', 'TID_土嚢': 'r', 'TID_低障害物': 'r', 'TID_防柵': 'r',
    'TID_防壁': 'r', 'TID_瓦礫': 'r', 'TID_瓦礫_ターゲット・ワープ禁': 'r', 'TID_溶岩': 'M', 'TID_森': 'T', 'TID_植込': 'T',
    'TID_長椅子': 'r', 'TID_崩れた床': 'x', 'TID_低い壁': 'r', 'TID_荷車': 'r', 'TID_井戸': 'r', 'TID_積み荷': 'r',
    'TID_噴火口': 'x',
    'TID_無し': '#', 'TID_進入不可': '#', 'TID_大岩': '#', 'TID_障害物': '#', 'TID_瓦礫_全戦禁': '#', 'TID_上橋': 'Y',
    'TID_民家': 'B', 'TID_民家入口': 'B', 'TID_建物': 'B', 'TID_風車': 'B', 'TID_建物灯': 'B', 'TID_船体': 'B', 'TID_建造物': 'B',
    'TID_建造物灯': 'B', 'TID_配置物': '#', 'TID_石像': '#', 'TID_祭壇': '#', 'TID_石棺': '#', 'TID_廃墟': 'B', 'TID_大柱': '#',
    'TID_帆柱': '#', 'TID_台座': '#', 'TID_壁': '#', 'TID_柵': '#', 'TID_動物像': '#', 'TID_ソラ像': '#', 'TID_魔法障壁': '#',
'TID_墓地': '#', 'TID_噴気孔': '#', 'TID_篝火': '#', 'TID_篝火消': '#', 'TID_篝火常': '#', 'TID_燭台': '#',
    'TID_邪竜脈': '#', 'TID_扉_破壊不可': 'd',
    'TID_壊れる壁': 'W', 'TID_壊れる壁_HP30': 'W', 'TID_壊れる壁_HP50': 'W', 'TID_破壊可能_HP20': 'W', 'TID_破壊可能_HP30': 'W',
    'TID_破壊可能_HP50': 'W', 'TID_防護柵': 'W', 'TID_雪だるま': 'W', 'TID_干し草': 'W', 'TID_結晶': 'W', 'TID_水晶': 'W',
    'TID_水晶_味方破壊': 'W', 'TID_壊れる壁_HP90_敵のみ': 'W',
    'TID_扉': 'd', 'TID_扉_HP30': 'd', 'TID_宝箱': 'c', 'TID_空宝箱': 'c', 'TID_宝箱_氷結界': 'c', 'TID_屋根': '#',
    'TID_弓砲台': 'L', 'TID_弓砲台_S010': 'L', 'TID_魔砲台': 'O', 'TID_火炎砲台': 'G', 'TID_火炎砲台_M019': 'G',
    'TID_火炎砲台_S013': 'G',
    'TID_進入不可_M026': 'N', 'TID_竜１': 'N', 'TID_竜２': 'N', 'TID_竜３': 'N', 'TID_竜４': 'N', 'TID_竜５': 'N', 'TID_竜６': 'N',
    'TID_竜７': 'N',
}
LETTER['TID_屋根'] = 'Q'          # a roof over a closed room (a terrain layer: it lifts when its group's door opens)
# What lies over a tile at the start (a map's overlaps: Corrin's Dragon Vein terrain, the Corrupted's miasma), by the kind of tile under
# it: open ground (plain, road, floor, sand, stairs) or cover (woods, pillars). Its Def, Avoid and healing add to the tile's, its
# move cost to the tile's on foot and horseback (fliers and dragons add its fly cost: App.TerrainCostData.GetCost).
OVERLAY_LETTER = {
    ('TID_霧_永続', 'open'): 'e', ('TID_霧_永続', 'cover'): 'j', ('TID_水溜まり_永続', 'open'): 'u', ('TID_水溜まり_永続', 'cover'): 'U',
    ('TID_土柱_永続', 'open'): 'z', ('TID_炎上_永続', 'open'): 'i', ('TID_瘴気_永続', 'open'): 'm', ('TID_瘴気_永続', 'cover'): 'D',
    ('TID_氷床_永続', 'open'): 'q',
}
DOOR_FLAG, ROOF_FLAG, FLY_ENABLE = 1, 1024, 16384      # App.TerrainData.Flags
# The emblems' rings on their pedestals (Chapter 22): objects no unit enters.
for _tid in ('シグルド', 'セリカ', 'ミカヤ', 'ロイ', 'リーフ', 'ルキナ', 'リン', 'アイク', 'ベレト', 'カムイ', 'エイリーク'):
    LETTER[f'TID_{_tid}の指輪'] = '#'


def text(label, default=''):
    t = D.text(label, default) if label else default
    return t.replace('[6:3:]', 'Alear') if t else t


class Names:
    def __init__(self):
        self.person = {r['Pid']: r for r in D.rows('person')}
        self.job = {r['Jid']: r for r in D.rows('job')}
        self.item = {r['Iid']: r for r in D.rows('item')}
        shared = {}
        for r in self.person.values():
            shared.setdefault(r['Name'], []).append(r)
        # A name several persons share, one of them drawn as a generic soldier (an asset, no portrait of its own): an army's or a
        # role's name, so the unit goes by its class.
        # The generic soldiers' bodies are the assets named for soldiers (AID_一般兵, AID_異形兵, AID_幻影兵, AID_レア異形兵); a named
        # character's are its own (AID_Person_チキ, Nel's dragon form AID_エル竜化).
        self.generic_names = {n for n, rs in shared.items() if len(rs) > 1 and any(r['Aid'].endswith('兵') for r in rs)}

    def job_of(self, row):
        p = self.person.get(row['Pid'], {})
        return row.get('Jid') or p.get('Jid', '')

    def class_name(self, jid):
        j = self.job.get(jid)
        return text(j['Name']) if j else jid

    def generic(self, pid):
        p = self.person.get(pid)
        return p is not None and p['Name'] in self.generic_names

    def name(self, row):
        pid = row['Pid']
        p = self.person.get(pid)
        if p is None:
            return pid
        if self.generic(pid):
            return self.class_name(self.job_of(row))
        return text(p['Name']) or pid

    def item_name(self, iid):
        r = self.item.get(iid)
        return D.item_label(iid) if r and r['Name'] else None

    def level(self, row, d):
        v = row[('LevelN', 'LevelH', 'LevelL')[d]]
        if v not in ('', '0'):
            return int(v)
        p = self.person.get(row['Pid'])
        return int(p['Level']) if p and p['Level'] else 1


def app_tile(t, x, z):
    return [x - t['x'] + 1, z - t['z'] + 1]


def unit_entry(n, u, d, t):
    row = u.row
    force = u.force
    boss = int(row['Flag'] or 0) & LEADER and force == E.FORCE_ENEMY
    generic = n.generic(u.pid)
    kind = 'boss' if boss else ('ally' if force == E.FORCE_ALLY else ('enemy' if generic else 'named'))
    e = {'type': kind, 'name': n.name(row), 'tile': app_tile(t, u.x, u.z)}
    if kind == 'ally' and generic:
        e['generic'] = True
    items = [(row[f'Item{k}.Iid'], row[f'Item{k}.Drop']) for k in range(1, 7) if row[f'Item{k}.Iid']]
    drops = [n.item_name(i) for i, dr in items if dr == '1' and n.item_name(i)]
    carries = [n.item_name(i) for i, dr in items if dr != '1' and n.item_name(i)]
    if drops:
        e['drops'] = drops
    if carries:
        e['carries'] = carries
    note = f'Lv {n.level(row, d)} {n.class_name(n.job_of(row))}'
    if kind in ('named', 'boss', 'ally') and not generic:
        note += ''
    e['note'] = note
    return e


def ordinal(k):
    words = {1: 'next', 2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh', 8: 'eighth', 9: 'ninth',
             10: 'tenth'}
    if k in words:
        return words[k]
    return f"{k}{'th' if 10 <= k % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(k % 10, 'th')}"


def phase_words(phase, kind):
    return f'end of the {PHASE[phase]}' if kind == 'EventEntryTurnEnd' else PHASE[phase]


def joined(words, last='and'):
    words = list(dict.fromkeys(words))
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} {last} {words[-1]}"


def turn_words(turns):
    """Turns in words: 'Turn 5', 'Turns 6, 12 and 13', 'Every third turn from 13' (the turns played reach TURNS: it goes on),
    'Turns 3, 5 and 7, then every turn from 9'."""
    turns = sorted(turns)
    step = turns[-1] - turns[-2] if len(turns) > 1 else 0
    k = len(turns) - 1
    while k > 0 and turns[k] - turns[k - 1] == step:
        k -= 1
    head, tail = turns[:k], turns[k:]
    goes_on = len(tail) > 2 and tail[-1] + step > TURNS
    if not goes_on and len(tail) < (3 if step == 1 else 4):
        head, tail = turns, []
    pattern = None
    if tail:
        pattern = f"{EVERY.get(step, f'every {step} turns')} from {tail[0]}" + ('' if goes_on else f' to {tail[-1]}')
    if not head:
        return pattern[0].upper() + pattern[1:]
    items = f"Turn {head[0]}" if len(head) == 1 else f"Turns {joined([str(x) for x in head])}"
    return items + (f', then {pattern}' if pattern else '')


def schedule_words(keys):
    """Placements (turn, phase, kind) in words, a phase at a time: 'Every third turn from 13, player phase'."""
    by = {}
    for turn, phase, kind in keys:
        by.setdefault((phase, kind), []).append(turn)
    parts = [f'{turn_words(sorted(set(ts)))}, {phase_words(p, k)}' for (p, k), ts in by.items()]
    return parts[0] + ''.join(f'; {x[0].lower()}{x[1:]}' for x in parts[1:])


def after_words(keys, clause, parity=False):
    """Placements so many phases after a cause in words: 'At the start of the next player phase after Zephia is defeated', 'At the
    start of each of the next 9 player phases after ...', 'At the start of every player phase after ...' (to the turns' end)."""
    by = {}
    for k, phase, kind in keys:
        by.setdefault((phase, kind), []).append(k)
    parts = []
    for (phase, kind), ks in by.items():
        ks = sorted(set(ks))
        edge = 'end' if kind == 'EventEntryTurnEnd' else 'start'
        run = ks == list(range(ks[0], ks[-1] + 1))
        if parity and len(ks) == 1:
            # The cause comes at turn 0 in the probes: the group waits for a turn as odd or even as its own.
            parts.append(f"At the {edge} of the next {PHASE[phase]} on an {'odd' if ks[0] % 2 else 'even'} turn after {clause}")
        elif len(ks) == 1:
            parts.append(f'At the {edge} of the {ordinal(ks[0])} {PHASE[phase]} after {clause}')
        elif run and ks[-1] + LATE >= TURNS:
            parts.append(f'At the {edge} of every {PHASE[phase]} from the {ordinal(ks[0])} after {clause}')
        elif run and ks[0] == 1:
            parts.append(f'At the {edge} of each of the next {len(ks)} {PHASE[phase]}s after {clause}')
        elif run:
            parts.append(f'At the {edge} of each {PHASE[phase]} from the {ordinal(ks[0])} to the {ordinal(ks[-1])} after {clause}')
        elif len(ks) > 2 and len({b - a for a, b in zip(ks, ks[1:])}) == 1:
            nth = EVERY.get(ks[1] - ks[0], f'every {ks[1] - ks[0]} turns').replace(' turn', f' {PHASE[phase]}')
            parts.append(f'At the {edge} of {nth} from the {ordinal(ks[0])} to the {ordinal(ks[-1])} after {clause}')
        else:
            parts.append(f"At the {edge} of the {joined([ordinal(k) for k in ks])} {PHASE[phase]}s after {clause}")
    return '; '.join(parts)


def tile_rects(tiles, t):
    """Tiles as rectangles in the app's coordinates: [left, bottom, right, top], rows merged where they line up."""
    rows = {}
    for x, z in tiles:
        rows.setdefault(z, []).append(x)
    runs = []
    for z, xs in sorted(rows.items()):
        xs = sorted(xs)
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            runs.append((start, prev, z))
            if x is not None:
                start = prev = x
    out = []
    for x1, x2, z in sorted(runs):
        if out and out[-1][0] == x1 and out[-1][2] == x2 and out[-1][3] == z - 1:
            out[-1][3] = z
        else:
            out.append([x1, z, x2, z])
    return [[a - t['x'] + 1, b - t['z'] + 1, c - t['x'] + 1, d - t['z'] + 1] for a, b, c, d in out]


class Clauses:
    """What sets an event off, as a clause ('Zephia is defeated', 'one of your units talks to Céline'): the chapter's people by
    name, a foe with no name of its own by its class and tile. Clauses that share a verb and its object, or a subject and its verb,
    are said once ('one of your units fights the Archer at (18, 15) or the Mage at (13, 15)')."""
    ANY = 'one of your units'

    def __init__(self, n, t, b, present):
        self.n, self.t = n, t
        self.units = {}
        for u in b.units:
            self.units.setdefault(u.pid, []).append(u)
        # Everyone some run of the battle puts on the map: a cause naming anyone else (Chapter 5's fourth platoon's Mage, placed on
        # Hard and Maddening only) can't happen.
        self.present = present

    def who(self, pid):
        if not pid:
            return self.ANY
        name = self.n.name({'Pid': pid, 'Jid': ''})
        us = self.units.get(pid, [])
        if us and (self.n.generic(pid) or name == self.n.class_name(self.n.job_of(us[0].row))):
            tiles = joined([self.at(u.start[0], u.start[1]) for u in us])
            return f'the {name} at {tiles}' if len(us) == 1 else f'the {name}s at {tiles}'
        return name

    def at(self, x, z):
        return f"({int(x) - self.t['x'] + 1}, {int(z) - self.t['z'] + 1})"

    def tile_name(self, x, z, b):
        """What stands on a tile at the start: a layer over it (a breakable wall, a door), or its terrain."""
        tid = next((L['Attr'] for L in self.t['layers'] if L['X'] <= x < L['X'] + L['W'] and L['Y'] <= z < L['Y'] + L['H']),
                   None) or b._terrain_get(int(x), int(z))
        r = next((r for r in D.rows('terrain') if r['Tid'] == tid), None)
        return (text(r['Name']) if r else '').lower() or 'tile'

    def triple(self, ev, b):
        """(subject, verb, object) of what sets the event off; None where it names someone the battle never places."""
        k, a = ev['kind'], ev['args']
        pids = [a[1]] if k in ('EventEntryDie', 'EventEntryEscape', 'EventEntryFixed') else [a[1], a[3]] if k in (
            'EventEntryTalk', 'EventEntryBattleTalk', 'EventEntryBattleBefore', 'EventEntryBattleAfter') else []
        if any(p and p not in self.present for p in pids):
            return None
        if k == 'EventEntryDie':
            return (self.who(a[1]), 'is defeated', '')
        if k == 'EventEntryTalk':
            return (self.who(a[1]), 'talks to', self.who(a[3]))
        if k in ('EventEntryBattleTalk', 'EventEntryBattleBefore', 'EventEntryBattleAfter'):
            # The two sides: a foe named first with no one second is a fight with that foe.
            if a[1] and a[2] == E.FORCE_ENEMY and not a[3]:
                return (self.ANY, 'fights', self.who(a[1]))
            return (self.who(a[1]), 'fights', self.who(a[3])) if a[3] else (self.who(a[1]), 'fights', '')
        if k == 'EventEntryArea':
            return (self.ANY if a[5] in (E.FORCE_PLAYER, -1) else 'a foe', 'enters', 'the marked area')
        if k == 'EventEntryVisit':
            return (f'the village at {self.at(a[1], a[2])}', 'is visited', '')
        if k == 'EventEntryTbox':
            return (f'the chest at {self.at(a[1], a[2])}', 'is opened', '')
        if k == 'EventEntryDestroy':
            name = self.tile_name(a[1], a[2], b)
            visited = any(e['kind'] == 'EventEntryVisit' and (e['args'][1], e['args'][2]) == (a[1], a[2]) for e in b.events)
            if name == 'house' or visited:
                return (f'the village at {self.at(a[1], a[2])}', 'is razed', '')
            return (f'the {name} at {self.at(a[1], a[2])}', 'is broken', '')
        if k == 'EventEntryDoor':
            return (f'the door at {self.at(a[1], a[2])}', 'is opened', '')
        if k == 'EventEntryEscape':
            return (self.who(a[1]), 'escapes', '')
        if k == 'EventEntryFixed':
            return (self.who(a[1]), 'finishes an action', '')
        if k in ('EventEntryReviveBefore', 'EventEntryReviveAfter'):
            return (self.who(a[1]), 'uses a revival stone', '')
        if k in ('EventEntryEngageBefore', 'EventEntryEngageAfter'):
            return (self.who(a[1]) if len(a) > 1 and isinstance(a[1], str) else self.ANY, 'engages', '')
        return None

    def words(self, triples, last='or'):
        """Clauses as one: shared verbs and objects said once."""
        by_object = {}
        for sub, verb, obj in triples:
            subs = by_object.setdefault((verb, obj), [])
            if sub not in subs:
                subs.append(sub)
        by_subject = {}
        for (verb, obj), subs in by_object.items():
            sub = self.ANY if self.ANY in subs else joined(subs, 'or')
            by_subject.setdefault((sub, verb), []).append(obj)
        by_sub = {}
        for (sub, verb), objs in by_subject.items():
            objs = [o for o in objs if o]
            by_sub.setdefault(sub, []).append(' '.join(x for x in (verb, joined(objs, 'or') if objs else '') if x))
        clauses = [f"{sub} {listed(preds, last)}" for sub, preds in by_sub.items()]
        return listed(clauses, last, comma=len(clauses) > 2 or any(',' in x for x in clauses))

    def where(self, tiles, b):
        return f"the {self.tile_name(*tiles[0], b)} at {self.at(*tiles[0])}" if len(tiles) == 1 else 'the marked area'

    def cause(self, c, b):
        """One cause as a clause, or None where it can't happen."""
        kind = c[0]
        if kind == 'ai':
            return None if c[1] not in self.present else f'{self.who(c[1])} starts to move'
        if kind == 'ai-all':
            return f"{joined([self.who(p) for p in c[1]])} have {'both' if len(c[1]) == 2 else 'all'} started to move"
        if kind == 'event':
            tr = self.triple(b.events[c[1]], b)
            return self.words([tr]) if tr else None
        if kind == 'at':
            tr = self.triple(b.events[c[1]], b)
            return f'{self.words([tr])} in {self.where(c[3], b)}' if tr else None
        if kind == 'stand':
            return f'{self.who(c[2])} reaches {self.where(c[3], b)}'
        if kind in ('clear', 'hold'):
            ev = b.events[c[1]]
            tr = None if ev['kind'] in E.TURN_KINDS else self.triple(ev, b)
            if ev['kind'] not in E.TURN_KINDS and not tr:
                return None
            if kind == 'clear':
                gone = [self.who(u.pid) for u in (b._unit_at(x, z) for x, z in c[2]) if u is not None]
                verb = 'leaves its tile or is defeated' if c[3] == 'or' or len(gone) == 1 else 'leave their tiles or are defeated'
                what = f'{joined(gone, c[3])} {verb}'
            else:
                what = f"your units stand on {joined([self.at(x, z) for x, z in c[2]])}"
            if tr:
                return f"{self.words([tr])} {'once' if kind == 'clear' else 'while'} {what}"
            return what
        evs = [b.events[i] for i in c[1]]
        if all(e['kind'] == 'EventEntryTalk' for e in evs):
            return f"your units have talked to {joined([self.who(e['args'][3]) for e in evs])}"
        if all(e['kind'] == 'EventEntryDie' for e in evs):
            return f"{joined([self.who(e['args'][1]) for e in evs])} are all defeated"
        trs = [self.triple(e, b) for e in evs]
        if all(x and x[0].startswith('the ') and ' at ' in x[0] for x in trs) and len({(x[0].split(' at ')[0], x[1]) for x in trs}) == 1:
            thing, verb = trs[0][0].split(' at ')[0], trs[0][1]
            done = {'is broken': 'broken', 'is razed': 'razed', 'is visited': 'visited', 'is opened': 'opened'}.get(verb, verb)
            return f"{thing}s at {joined([x[0].split(' at ', 1)[1] for x in trs])} are all {done}"
        return self.words([x for x in trs if x], 'and') + ' (all of them)'

    def causes(self, cs, b):
        """Several causes, any of which does it: their clauses as one."""
        trs = [self.triple(b.events[c[1]], b) for c in cs if c[0] == 'event']
        parts = [x for x in ([self.words([x for x in trs if x])] if any(trs) else []) + [self.cause(c, b) for c in cs if c[0] != 'event']
                 if x]
        return listed(parts, 'or', comma=len(parts) > 1 and any(' or ' in x for x in parts))


def listed(parts, last, comma=False):
    """Clauses joined: 'A, B or C'; with a comma before the last where a clause has commas of its own (or `comma`)."""
    parts = list(dict.fromkeys(parts))
    if len(parts) > 1 and (comma or any(',' in x for x in parts)):
        return ', '.join(parts[:-1]) + f', {last} ' + parts[-1]
    return joined(parts, last)


class Snap:
    """A unit as it stood once the opening was over."""
    def __init__(self, u):
        self.row, self.group, self.pid, self.x, self.z, self.force = u.row, u.group, u.pid, u.x, u.z, u.force
        self.on_map = u.on_map
        self.came_from = getattr(u, 'came_from', None)
        self.unit = u


def play(name, d, army_level=None):
    b = E.battle(name, d, army_level)
    b.snapshot = [Snap(u) for u in b.units]
    b.run_turns(TURNS)
    return b


def probe(name, d, army_level, cause, after=0):
    """The battle played with a cause brought about at the start, or after `after` turns: an event's moment (Battle.happen), a
    unit's AI started, a unit standing on a tile (for an event that waits for it there), or several of these at once. The battle
    and the log entry its effects start from."""
    b = E.battle(name, d, army_level)
    b.run_turns(after)
    mark = len(b.log)
    kind = cause[0]
    if kind == 'ai':
        b.active.add(cause[1])
    elif kind == 'ai-all':
        b.active |= set(cause[1])
    elif kind in ('at', 'stand'):
        u = b._unit(cause[2])
        if u is not None:
            u.x, u.z = cause[3][0]
    elif kind == 'clear':
        for x, z in cause[2]:
            u = b._unit_at(x, z)
            if u is not None:
                b._delete(u)
    elif kind == 'hold':
        yours = [u for u in b._force_units(E.FORCE_PLAYER) if u.pid == E.LORD] + [
            u for u in b._force_units(E.FORCE_PLAYER) if u.pid != E.LORD]
        for (x, z), u in zip(cause[2], yours):
            u.x, u.z = x, z
    one = (cause[1],) if kind in ('event', 'at') or (kind in ('clear', 'hold') and b.events[cause[1]]['kind'] not in E.TURN_KINDS) else ()
    for i in one or (cause[1] if kind == 'all' else ()):
        b.happen(b.events[i])
    b.run_turns(TURNS, first=after + 1)
    return b, mark


def placements(b, mark=0):
    """What the battle placed after log entry `mark`, by group: (turn, phase, kind, units) at a turn, ('now', ...) by the cause. The
    terrain one moment sets (a village razed to ruins, Chapter 16's tide, Chapter 22's ring pedestals cleared) is a group of its own,
    keyed ('terrain', its tiles and what each becomes)."""
    out = {}
    sets = {}
    for at, kind, data in b.log[mark:]:
        if at[0] not in ('turn', 'event'):
            continue
        key = (at[1], at[2], at[3]) if at[0] == 'turn' else ('now', None, None)
        if kind == 'dispos' and data['units']:
            out.setdefault(data['group'], []).append((key, data['units']))
        elif kind == 'terrain':
            sets.setdefault(at, (key, {}))[1][data['tile']] = data['tid']
    for key, tiles in sets.values():
        if tiles:
            out.setdefault(('terrain', tuple(sorted(tiles.items()))), []).append((key, None))
    return out


def standing(b, ev):
    """For an event whose condition reads where a unit stands (Chapter 22's emblems appear once Alear ends an action near their
    rings; Chapter 9's reinforcements once Kagetsu reaches the fort): the unit and the tiles where it holds."""
    pos = sorted(r[4:] for r in b.condition_reads(ev) if r.startswith('pos:'))
    for pid in pos:
        tiles = b.where(ev, pid)
        if tiles:
            return pid, tuple(tiles)
    return None


def on_tiles(b, ev):
    """For an event whose condition reads who stands on some tiles (Chapter 11's Ivy waits for her escape tiles to be clear, The Lonely
    Heir's switches for your units): ('clear', tiles, 'or'/'and') where emptying them makes it hold (any one, or all), ('hold',
    tiles) where your units on them do; None otherwise, or where it holds already."""
    tiles = sorted({tuple(int(v) for v in r[5:].split(',')) for r in b.condition_reads(ev) if r.startswith('tile:')})
    if not tiles or b.holds_with(ev):
        return None
    if b.holds_with(ev, empty=tiles):
        return ('clear', tuple(tiles), 'or' if any(b.holds_with(ev, empty=[x]) for x in tiles) else 'and')
    if b.holds_with(ev, mine=tiles):
        return ('hold', tuple(tiles))
    return None


def arrivals(name, d, level, b, n, t):
    """What arrives after the start, and when: the groups the turns place with nothing else happening, and what each of the
    chapter's events (a defeat, a talk, a fight, an area, a village...), each unit's AI starting, a unit reaching the tiles an event
    waits for, or a set of like events brings on or holds back. [(group, when, units, areas)], and what the villages and chests
    give: {(kind, tile): items}."""
    base_places = placements(b)
    base = {g: [k for k, _ in es if k[0] != 'now'] for g, es in base_places.items()}
    first = {g: es[0][1] for g, es in base_places.items()}
    events = b.events
    causes = []
    for ev in events:
        if ev['kind'] in E.TURN_KINDS:
            continue
        spot, held = standing(b, ev), on_tiles(b, ev)
        causes.append(('at', ev['index'], *spot) if spot else (held[0], ev['index'], *held[1:]) if held else ('event', ev['index']))
    asked = sorted(x for x in b.ai_asked if x)
    causes += [('ai', pid) for pid in asked]
    like = {}
    for ev in events:
        if ev['kind'] not in E.TURN_KINDS:
            like.setdefault((ev['kind'], id(ev['args'][0])), []).append(ev['index'])
    causes += [('all', tuple(ix)) for ix in like.values() if len(ix) > 1]
    if len(asked) > 1:
        causes.append(('ai-all', tuple(asked)))
    # A turn event whose condition waits for a unit on a tile (Chapter 9's fort): that unit standing there.
    for ev in events:
        if ev['kind'] in E.TURN_KINDS and not ev['runs']:
            spot, held = standing(b, ev), on_tiles(b, ev)
            if spot:
                causes.append(('stand', ev['index'], *spot))
            elif held:
                causes.append((held[0], ev['index'], *held[1:]))
    now, later, until, objects, ran, present = {}, {}, {}, {}, set(), {u.pid for u in b.units}
    results = []
    for c in causes:
        try:
            pb, mark = probe(name, d, level, c)
        except E.LuaError:
            continue
        ran |= {ev['index'] for ev in pb.events if ev['runs']}
        present |= {u.pid for u in pb.units}
        results.append((c, pb, mark))
    clauses = Clauses(n, t, b, present)
    seen, seen_causes = {}, [c for c, _, _ in results]
    for c, pb, mark in results:
        got = placements(pb, mark)
        single = ([('event', i) for i in c[1]] + [('at', i) for i in c[1]]) if c[0] == 'all' else (
            [('ai', p) for p in c[1]] if c[0] == 'ai-all' else [])
        for g in set(got) | set(base):
            keys = [k for k, _ in got.get(g, [])]
            seen[c, g] = keys
            if any(seen.get((y, g)) == keys for x in single for y in seen_causes
                   if y[0] in ('event', 'at', 'clear', 'hold', 'ai') and x[0] in ('event', 'at', 'ai') and y[1] == x[1]):
                continue
            if any(k[0] == 'now' for k in keys):
                now.setdefault(g, {})[c] = next(us for k, us in got[g] if k[0] == 'now')
                first.setdefault(g, now[g][c])
            extra = list((Counter(k for k in keys if k[0] != 'now') - Counter(base.get(g, []))).elements())
            if extra:
                lb, lmark = probe(name, d, level, c, after=LATE)
                late_keys = [k for k, _ in placements(lb, lmark).get(g, []) if k[0] != 'now']
                late = sorted((Counter(late_keys) - Counter(k for k in base.get(g, []) if k[0] > LATE)).elements())
                moved = sorted((k[0] + LATE, k[1], k[2]) for k in extra if k[0] + LATE <= TURNS)
                parity = False
                if late != moved:
                    eb, emark = probe(name, d, level, c, after=LATE - 1)
                    even = sorted((Counter(k for k, _ in placements(eb, emark).get(g, []) if k[0] != 'now')
                                   - Counter(k for k in base.get(g, []) if k[0] > LATE - 1)).elements())
                    parity = even == sorted((k[0] + LATE - 1, k[1], k[2]) for k in extra if k[0] + LATE - 1 <= TURNS)
                later.setdefault(g, {})[c] = (sorted(extra), late == moved or parity, parity)
                first.setdefault(g, next(us for k, us in got[g] if k in extra))
            if Counter(base.get(g, [])) - Counter(keys):
                until.setdefault(g, []).append(c)
        if c[0] in ('event', 'at', 'clear', 'hold') and events[c[1]]['kind'] in ('EventEntryVisit', 'EventEntryTbox'):
            ev = events[c[1]]
            tile = tuple(app_tile(t, int(ev['args'][1]), int(ev['args'][2])))
            for at, kind, data in pb.log[mark:]:
                if kind == 'item' and at[0] == 'event':
                    iid = data['iid']
                    objects.setdefault((ev['kind'], tile), set()).add(
                        n.item_name(iid) or (iid.replace('IID_', '').replace('G', ' gold') if 'G' in iid else iid))
    # A turn event nothing sets off whose condition reads more than the script's variables, the difficulty and the turn (how many
    # foes are left, a unit's state): what it places comes after an event the chapter's checks decide.
    for ev in events:
        if ev['kind'] not in E.TURN_KINDS or ev['runs'] or ev['index'] in ran:
            continue
        if b.condition_reads(ev) <= E.DECIDED:
            continue
        pb, mark = probe(name, d, level, ('all', (ev['index'],)))
        for g, es in placements(pb, mark).items():
            if g not in base and g not in now and g not in later:
                now.setdefault(g, {})[('vague', ev['index'])] = es[0][1]
                first.setdefault(g, es[0][1])
    out = []
    for g in first:
        parts = []
        if base.get(g):
            stop = [c for c in until.get(g, []) if clauses.cause(c, b)]
            parts.append(schedule_words(base[g]) + (f', until {clauses.causes(stop, b)}' if stop else ''))
        whens = [c for c in now.get(g, {}) if c[0] != 'vague' and clauses.cause(c, b)]
        if whens:
            parts.append(f'When {clauses.causes(whens, b)}')
        if any(c[0] == 'vague' for c in now.get(g, {})):
            parts.append('After an event in the chapter')
        rel, fixed = {}, {}
        for c, (keys, moves, parity) in later.get(g, {}).items():
            if not clauses.cause(c, b):
                continue
            if moves:
                rel.setdefault((tuple(keys), parity), []).append(c)
            else:
                fixed.setdefault(tuple(keys), []).append(c)
        for keys, cs in fixed.items():
            parts.append(f'{schedule_words(keys)}, once {clauses.causes(cs, b)}')
        for (keys, parity), cs in rel.items():
            parts.append(after_words(keys, clauses.causes(cs, b), parity))
        if not parts:
            continue
        when = parts[0] + ''.join(f'; or {p[0].lower()}{p[1:]}' for p in parts[1:])
        rects = []
        for c in list(now.get(g, {})) + list(later.get(g, {})):
            if c[0] == 'event' and events[c[1]]['kind'] == 'EventEntryArea':
                a = events[c[1]]['args']
                x1, z1, x2, z2 = (int(v) for v in a[1:5])
                r = {'who': 'player', 'rect': [x1 - t['x'] + 1, z1 - t['z'] + 1, x2 - t['x'] + 1, z2 - t['z'] + 1]}
                if r not in rects:
                    rects.append(r)
            elif c[0] in ('at', 'stand') and len(c[3]) > 1:
                u = b._unit(c[2])
                who = 'enemy' if u is not None and u.force == E.FORCE_ENEMY else 'player'
                for rect in tile_rects(c[3], t):
                    r = {'who': who, 'rect': rect}
                    if r not in rects:
                        rects.append(r)
        out.append((g, when, first.get(g), rects or None))
    return out, objects


def start_units(b):
    """What stands on the map once the opening is over: the start's groups and what the opening places (Chapter 10's army)."""
    opening = {id(u) for at, kind, data in b.log if kind == 'dispos' and at[0] in ('start', 'opening') for u in data['units']}
    return [u for u in b.snapshot if u.on_map and u.force in (E.FORCE_ENEMY, E.FORCE_ALLY) and id(u.unit) in opening and u.pid]


def army_levels(name):
    """A Divine Paralogue's army level bands (its rows' LevelMin-LevelMax): their first levels, lowest first; none elsewhere."""
    return sorted({int(r['LevelMin']) for _, rows in D.dispos(name) for r in rows if r.get('LevelMin') not in (None, '', '0')})


def band(row):
    lo, hi = int(row['LevelMin']), int(row['LevelMax'] or 255)
    return f'{lo} or more' if hi >= 99 else f'{lo}-{hi}'


def brief(n, u):
    """A unit in a few words: its class and weapons."""
    items = [n.item_name(u.row[f'Item{k}.Iid']) for k in range(1, 7) if u.row[f'Item{k}.Iid']]
    items = [i for i in items if i]
    return n.class_name(n.job_of(u.row)) + (f" with {', '.join(items)}" if items else '')


def battle_map(cid, chapter_row, n, sources, used_tids):
    name = cid.replace('CID_', '')
    t = D.terrain(chapter_row['Terrain'].replace('MapTerrain_', '') if chapter_row['Terrain'] not in ('', 'MapTerrain_*') else name)
    per_diff, starts, groups, joiners, objects, forced = [], set(), {}, {}, {}, []
    shifts = {}
    opening_terrain = None
    corrin = None
    win = None
    levels = army_levels(name)
    tiers = {}
    for d, dname in enumerate(DIFFS):
        b = play(name, d, levels[0] if levels else None)
        win = win or b.win
        if opening_terrain is None:
            opening_terrain = {data['tile']: data['tid'] for at, kind, data in b.log if kind == 'terrain' and at[0] in ('start', 'opening')}
        opening = {id(u) for at, kind, data in b.log if kind == 'dispos' and at[0] in ('start', 'opening') for u in data['units']}
        start = start_units(b)
        # A Divine Paralogue at its other army level bands: what each tile holds there instead, and what only those bands place.
        notes_at, extra = {}, []
        if levels:
            base = {(u.x, u.z): u for u in start}
            for lv in levels[1:]:
                for u in start_units(play(name, d, lv)):
                    was = base.get((u.x, u.z))
                    if was is None:
                        extra.append((band(u.row), u))
                    elif (was.pid, was.row['Jid'], brief(n, was)) != (u.pid, u.row['Jid'], brief(n, u)):
                        line = f'At army level {band(u.row)}: {brief(n, u)}'
                        if line not in notes_at.setdefault((u.x, u.z), []):
                            notes_at[(u.x, u.z)].append(line)
        for u in b.snapshot:
            if u.on_map and u.force == E.FORCE_PLAYER and id(u.unit) in opening and u.pid and u.group not in E.START_GROUPS:
                entry = {'name': n.name(u.row), 'tile': app_tile(t, u.x, u.z)}
                if entry not in forced:
                    forced.append(entry)
        units = []
        for u in start:
            e = unit_entry(n, u, d, t)
            if levels:
                e['note'] = f"{brief(n, u)}; at army level {band(u.row)}" + ''.join(f'. {x}' for x in notes_at.get((u.x, u.z), []))
            units.append(e)
        per_diff.append([{**e, 'difficulties': [dname]} for e in units])
        for label, u in extra:
            g = tiers.setdefault(label, {'when': {}, 'units': []})
            g['when'][dname] = f'At the start, when your army level is {label}'
            entry = next((x for x in g['units'] if x[0] == dname), None)
            if entry is None:
                entry = (dname, [])
                g['units'].append(entry)
            seen = {(id(x[0].row), x[0].x, x[0].z) for x in entry[1]}
            if (id(u.row), u.x, u.z) not in seen:
                e = unit_entry(n, u, d, t)
                e['note'] = f'{brief(n, u)}; only at army level {label}'
                entry[1].append((u, e))
        for r in b.placed('Player'):
            fl = int(r['Flag'] or 0)
            x, z = int(r['DisposX']), int(r['DisposY'])
            if fl & POS or r['Pid']:
                starts.add(tuple(app_tile(t, x, z)))
            if r['Pid'] == LORD:
                corrin = app_tile(t, x, z)
            elif r['Pid'] and fl & MUST:
                entry = {'name': n.name(r), 'tile': app_tile(t, x, z)}
                if entry not in forced:
                    forced.append(entry)
        # Groups placed after the start, and when.
        timed, got = arrivals(name, d, levels[0] if levels else None, b, n, t)
        for key, items in got.items():
            objects.setdefault(key, set()).update(items)
        for group, when, gunits, areas in timed:
            if isinstance(group, tuple):
                shifts.setdefault(group, {'when': {}, 'areas': areas})['when'].setdefault(dname, when)
                continue
            entry = groups if any(u.force == E.FORCE_ENEMY for u in gunits) else joiners
            g = entry.setdefault(group, {'when': {}, 'units': [], 'areas': areas})
            g['when'].setdefault(dname, when)
            g['units'].append((dname, [(u, unit_entry(n, u, d, t)) for u in gunits]))
    units = gm._merge_units(per_diff, DIFFS)
    for u in units:
        if u.get('difficulties') == DIFFS:
            u.pop('difficulties')
    m = {
        'id': f'fe17-{name.lower()}', 'route': ROUTE[name[0]], 'chapter': int(name[1:]),
        'title': text(f'MCID_{name}'), 'location': text(f'MCID_{name}_PLACE'),
        'heading': text(f'MCID_{name}_PREFIX'),
        'width': t['width'], 'height': t['height'], 'grid': [],
        'victory': '', 'defeat': '', 'objectives': [], 'units': units, 'starts': sorted([list(s) for s in starts]),
        'objects': [], 'changes': [], 'notes': [],
    }
    if corrin:
        m['corrinStart'] = corrin
    if forced:
        m['forced'] = forced
    mid = (win or {}).get('mid')
    m['victory'] = text(mid[0]).replace('[1:0:]', str(mid[1]) if len(mid) > 1 else '') if mid else 'Defeat the boss'
    lose = (win or {}).get('lose')
    m['defeat'] = (text(lose[0]).replace('[1:0:]', str(lose[1]) if len(lose) > 1 else '') if lose else
                   text('MID_RULE_COMMON_LOSE'))
    if int(chapter_row['Flag'] or 0) & 4:
        m['fog'] = True
    if levels:
        m['notes'].append('Comes with the Expansion Pass.')
        m['notes'].append("Its foes depend on your army level: the map shows the lowest band's, each foe says what it becomes at the "
                          'higher bands, and the foes only the higher bands bring are groups of their own (placed at the start).')
        m['unconfirmed'] = ['Army level is the internal level of Alear and the units in the deployment slots (Fire Emblem Wiki); how the '
                            'game measures it is not traced in its program.']
    for label, g in tiers.items():
        groups[f'Army level {label}'] = {'when': g['when'], 'units': g['units'], 'areas': None}
    rein = []
    for k, (gname, g) in enumerate(groups.items(), 1):
        lists = [[{**e, 'difficulties': [dn]} for _, e in us] for dn, us in g['units']]
        merged = gm._merge_units(lists, DIFFS)
        for u in merged:
            if u.get('difficulties') == DIFFS:
                u.pop('difficulties')
        firsts = {}
        for dn, us in g['units']:
            for u, e in us:
                if getattr(u, 'came_from', None):
                    firsts[e['name'], tuple(e['tile'])] = app_tile(t, *u.came_from)
        for u in merged:
            f = firsts.get((u['name'], tuple(u['tile'])))
            if f and f != u['tile']:
                u['from'] = f
        whens = g['when']
        when = whens[DIFFS[0]] if len(set(whens.values())) == 1 and len(whens) == len(DIFFS) else whens
        if isinstance(when, dict) and len(set(when.values())) == 1:
            when = next(iter(when.values()))
        grp = {'id': f'{m["id"]}-g{k}', 'label': f'Group {k}', 'units': merged, 'when': when}
        if g['areas']:
            grp['areas'] = g['areas']
        rein.append(grp)
    if rein:
        m['reinforcements'] = rein
    js = []
    for gname, g in joiners.items():
        dn, us = g['units'][0]
        for u, e in us:
            js.append({'name': e['name'], 'tile': e['tile'], 'from': app_tile(t, *getattr(u, 'came_from', (u.x, u.z))),
                       'group': gname, **({'ally': True} if u.force == E.FORCE_ALLY else {}),
                       'when': g['when'][dn], **({'areas': g['areas']} if g['areas'] else {})})
    if js:
        m['joiners'] = js
    for (kind, tile), items in objects.items():
        if kind == 'EventEntryVisit':
            m['objects'].append({'type': 'village', 'tile': list(tile), 'reward': ', '.join(sorted(items))})
        else:
            m['objects'].append({'type': 'chest', 'tile': list(tile), 'contents': ', '.join(sorted(items))})
    # Terrain as the battle starts, top row first: what the opening sets is made, the layers and overlaps lie over it.
    m['grid'] = encode_grid(t, opening_terrain, used_tids, m['id'])
    m['changes'] = layer_changes(t, opening_terrain, used_tids, m['id']) + script_changes(t, shifts, opening_terrain, used_tids,
                                                                                          m['id'])
    # Sources: chests, villages, drops.
    for o in m['objects']:
        for item in (o.get('reward') or o.get('contents') or '').split(', '):
            if item:
                add_source(sources, item, m['id'], 'chest' if o['type'] == 'chest' else 'village',
                           f"{'In a chest' if o['type'] == 'chest' else 'From a village'} ({m['heading']})")
    for u in units:
        for item in u.get('drops', []):
            add_source(sources, item, m['id'], 'drop', f"Dropped by {u['name']}", u.get('difficulties'))
        for item in u.get('carries', []):
            add_source(sources, item, m['id'], 'foe' if u['type'] != 'ally' else 'kit', f"Carried by {u['name']}",
                       u.get('difficulties'))
    for g in rein:
        for u in g['units']:
            for item in u.get('drops', []):
                add_source(sources, item, m['id'], 'drop-later', f"Dropped by {u['name']} (arrives later)", u.get('difficulties'))
            for item in u.get('carries', []):
                add_source(sources, item, m['id'], 'foe-later', f"Carried by {u['name']} (arrives later)", u.get('difficulties'))
    return m


# A location's skirmish (dispos <map>e, script <map>_encount): its deployment tiles (Player0) and its foes' slots (Mob00, each a
# dummy person the game fills with a class from the location's pools: chapter.xml EncountJobs, encount.xml 敵兵種), on the map's own
# terrain as the skirmish's opening leaves it.
SKIRMISH_GROUPS = ('Player0', 'Mob00')


def random_foes(n, dispos, script, terrain_name, groups):
    """A battle whose foes the game draws (a skirmish's, a Tempest Trial's): its terrain as the opening leaves it, its deployment
    tiles and its foe slots (a dummy person: 'Random foe'; a person of its own: by name), per difficulty."""
    t = D.terrain(terrain_name)
    per_diff, starts, terrain = [], set(), {}
    for d, dname in enumerate(DIFFS):
        b = E.Battle(dispos, d, script=script, terrain=terrain_name, start_groups=groups)
        b.start()
        terrain.update(b.terrain)
        units = []
        for u in b.units:
            if not u.on_map or u.group != groups[1]:
                continue
            boss = int(u.row['Flag'] or 0) & LEADER
            if u.pid == 'PID_ダミー':
                units.append({'type': 'enemy', 'name': 'Random foe (leader)' if boss else 'Random foe',
                              'tile': app_tile(t, u.x, u.z), 'difficulties': [dname]})
            else:
                units.append({**unit_entry(n, u, d, t), 'difficulties': [dname]})
        per_diff.append(units)
        for r in b.placed(groups[0]):
            starts.add(tuple(app_tile(t, int(r['DisposX']), int(r['DisposY']))))
    units = gm._merge_units(per_diff, DIFFS)
    for u in units:
        if u.get('difficulties') == DIFFS:
            u.pop('difficulties')
    return t, units, starts, terrain


def pool_words(n, chapter_row):
    pools = {r['EJid']: [n.class_name(j) for j in D.flag_list(r['Jobs'])] for r in D.rows('encount', '敵兵種')}
    lists = [pools[e] for e in D.flag_list(chapter_row['EncountJobs']) if e in pools]
    return ('Each foe is drawn by the game when the battle starts: its class from '
            + ('these classes: ' if len(lists) == 1 else 'one of these pools: ') + '; or '.join(', '.join(p) for p in lists) + '.')


@functools.lru_cache(maxsize=None)
def terrain_rows():
    return {r['Tid']: r for r in D.rows('terrain')}


def ground(tid):
    """The kind of tile an overlap lies on: open ground or cover (woods, pillars)."""
    r = terrain_rows()[tid]
    if r['CostName'] == 'COST_平地' and int(r['Avoid'] or 0) == 0 and int(r['Defense'] or 0) == 0:
        return 'open'
    if r['CostName'] == 'COST_林' and int(r['Avoid'] or 0) == 30:
        return 'cover'
    raise SystemExit(f'an overlap on {tid}: add its kind of ground')


def ground_tiles(t, terrain=None):
    """Each tile of the map's window under its layers: its grid's terrain, what the opening set (`terrain`) and what lies over it (an
    overlap: (overlap, tile) for both)."""
    out = {}
    for z in range(t['z'], t['z'] + t['height']):
        for x in range(t['x'], t['x'] + t['width']):
            out[x, z] = (terrain or {}).get((x, z), t['tiles'][z * D.GRID + x])
    for o in t['overlaps']:
        if (o['X'], o['Y']) in out:
            out[o['X'], o['Y']] = (o['Attr'], out[o['X'], o['Y']])
    return out


def start_tiles(t, terrain=None):
    """Each tile as the battle starts: the ground (ground_tiles) with the layers over it (doors, breakable walls, roofs: Chapter 15's
    miasma lies in rooms under roofs)."""
    out = ground_tiles(t, terrain)
    for L in t['layers']:
        for z in range(L['Y'], L['Y'] + L['H']):
            for x in range(L['X'], L['X'] + L['W']):
                if (x, z) in out:
                    out[x, z] = L['Attr']
    return out


def letter_of(key):
    if isinstance(key, tuple):
        return OVERLAY_LETTER[key[0], ground(key[1])]
    if key not in LETTER:
        raise SystemExit(f'no letter for {key}')
    return LETTER[key]


def tile_name(key):
    """A tile's name as the game gives it ('Rickety Wall'; an overlap's on its tile's: 'Miasma on floor')."""
    if isinstance(key, tuple):
        return f"{text(terrain_rows()[key[0]]['Name'])} on {text(terrain_rows()[key[1]]['Name']).lower()}"
    return text(terrain_rows()[key]['Name']) or key


# Each map's tiles by code and the game's name: {map id: {code: {name: [tiles]}}}, for the names a map's codes cover (terrain_names).
TILE_NAMES = {}


def encode_grid(t, terrain, used_tids, map_id):
    tiles = start_tiles(t, terrain)
    names = TILE_NAMES.setdefault(map_id, {})
    rows = []
    for z in range(t['z'] + t['height'] - 1, t['z'] - 1, -1):
        line = []
        for x in range(t['x'], t['x'] + t['width']):
            key = tiles[x, z]
            used_tids.setdefault(key, set()).add(map_id)
            code = encode(GAME, letter_of(key))
            names.setdefault(code, {}).setdefault(tile_name(key), []).append(app_tile(t, x, z))
            line.append(code)
        rows.append(''.join(line))
    return rows


def terrain_names(m, info):
    """A map's own names for codes that cover several of the game's (Engage's breakables: Rickety Wall here, Junk there): the most
    common first, then the tiles with each other name, so the legend and the tile panel say what the game says."""
    over = {}
    for code, names in TILE_NAMES.get(m['id'], {}).items():
        order = sorted(names, key=lambda k: (-len(names[k]), k))
        if order == [info[code]['name']]:
            continue
        over[code] = {'name': ' / '.join(order), **({'tileNames': {k: names[k] for k in order[1:]}} if len(order) > 1 else {})}
    if over:
        m['terrainOverrides'] = over


def script_changes(t, shifts, terrain, used_tids, map_id):
    """What the script changes on the map after the start, a change for each set of tiles one moment sets: when (as a group's time),
    and what the tiles become; previewed on the tiles in the map's window."""
    out, back = [], []
    under = ground_tiles(t, terrain)
    for k, (key, g) in enumerate(shifts.items(), 1):
        tiles = [((x, z), tid) for (x, z), tid in key[1] if (x, z) in under]
        if not tiles:
            continue
        whens = g['when']
        when = whens[DIFFS[0]] if len(set(whens.values())) == 1 and len(whens) == len(DIFFS) else '; '.join(
            f'{d}: {w}' for d, w in whens.items())
        patch = []
        for (x, z), tid in tiles:
            # What lies over a tile stays over its new terrain only where the game keeps it (not traced): the new terrain alone.
            used_tids.setdefault(tid, set()).add(map_id)
            patch.append({'tile': app_tile(t, x, z), 'becomes': encode(GAME, letter_of(tid))})
        start = start_tiles(t, terrain)
        if all(p['becomes'] == encode(GAME, letter_of(start[x, z])) for p, ((x, z), _) in zip(patch, tiles)):
            # Tiles put back as they started (Chapter 16's tide going out): said with the change that moved them, if one did.
            back.append(({xz for xz, _ in tiles}, when, joined(sorted({tile_name(tid).lower() for _, tid in tiles}))))
            continue
        names = joined(sorted({tile_name(tid).lower() for _, tid in tiles}))
        what = (f'its tile becomes {names}' if len(tiles) == 1 else f'{len(tiles)} tiles become {names}')
        X, Y = patch[0]['tile']
        change = {'id': f'{map_id}-shift-{k}', 'trigger': 'event', 'tile': {'default': [X, Y]}, 'usableBy': '',
                  'effect': f'{when}: {what}.', 'patch': patch}
        if len(whens) < len(DIFFS):
            change['difficulties'] = [d for d in DIFFS if d in whens]
            if len(set(whens.values())) == 1:
                change['effect'] = f'{next(iter(whens.values()))}: {what}.'
        if len(tiles) > 1:
            change['wide'] = True
        change['_tiles'] = {xz for xz, _ in tiles}
        out.append(change)
    for tiles, when, names in back:
        c = next((c for c in out if c['_tiles'] == tiles), None)
        if c is not None:
            c['effect'] = c['effect'][:-1] + f'; {when[0].lower()}{when[1:]}, they become {names} again.'
    for c in out:
        del c['_tiles']
    return out


def layer_changes(t, terrain, used_tids, map_id):
    """A change per layer group: its doors and breakables open (a door with a Thief's Door command, or attacked down; a wall, junk or
    a fence attacked down), and the roofs of its group lift with them; previewed as the tiles under them."""
    groups = {}
    for L in t['layers']:
        groups.setdefault(L['Group'], []).append(L)
    out = []
    for g, Ls in sorted(groups.items()):
        rows = terrain_rows()
        opens = [L for L in Ls if not int(rows[L['Attr']]['Flag'] or 0) & ROOF_FLAG]
        roofs = [L for L in Ls if int(rows[L['Attr']]['Flag'] or 0) & ROOF_FLAG]
        tiles = [(x, z) for L in Ls for z in range(L['Y'], L['Y'] + L['H']) for x in range(L['X'], L['X'] + L['W'])
                 if t['x'] <= x < t['x'] + t['width'] and t['z'] <= z < t['z'] + t['height']]
        if not opens or not tiles:
            continue
        r = rows[opens[0]['Attr']]
        hp = [int(r[k] or 0) for k in ('Hp_N', 'Hp_H', 'Hp_L')]
        hp_words = f'{hp[0]} HP' + ('' if len(set(hp)) == 1 else f" (Hard {hp[1]}, Maddening {hp[2]})")
        name = text(r['Name']).lower()
        door = int(r['Flag'] or 0) & DOOR_FLAG
        first = (opens[0]['X'], opens[0]['Y'])
        X, Y = app_tile(t, *first)
        room = ', and the room behind it opens' if roofs else ''
        if door:
            effect = f"A {name} with {hp_words}: attack it down, or a Thief opens it with the Door command{room}."
            who = 'Any unit that can attack it, or a Thief'
        elif r['Destroyer'] == '2':
            effect = f"A {name} with {hp_words} only foes can break (it opens when one does){room}."
            who = 'Foes only'
        else:
            effect = f"A {name} with {hp_words}: attack it down and it opens{room}."
            who = 'Any unit that can attack it'
        patch = []
        under = ground_tiles(t, terrain)
        for x, z in tiles:
            key = under[x, z]
            used_tids.setdefault(key, set()).add(map_id)
            patch.append({'tile': app_tile(t, x, z), 'becomes': encode(GAME, letter_of(key))})
        out.append({'id': f'{map_id}-open-{X}-{Y}', 'trigger': 'breakable', 'tile': {'default': [X, Y]}, 'usableBy': who,
                    'effect': effect, 'patch': patch})
    return out


def skirmish_map(loc, chapter_row, n, used_tids, opens_at):
    terrain_name = chapter_row['Terrain'].replace('MapTerrain_', '') if chapter_row['Terrain'] not in ('', 'MapTerrain_*') else loc
    t, units, starts, terrain = random_foes(n, loc + 'E', f'{loc}_encount', terrain_name, SKIRMISH_GROUPS)
    m = {
        'id': f'fe17-{loc.lower()}-sk', 'route': 'Skirmish', 'skirmishOf': f'fe17-{loc.lower()}', 'chapter': int(loc[1:]),
        'heading': 'Skirmish', 'title': text(f'MCID_{loc}_PLACE') or text(f'MCID_{loc}'), 'location': text(f'MCID_{loc}_PLACE'),
        'width': t['width'], 'height': t['height'], 'grid': [], 'victory': text('MID_RULE_ANNIHILATE') or 'Rout the enemy.',
        'defeat': text('MID_RULE_COMMON_LOSE'), 'objectives': [], 'units': units, 'starts': sorted([list(x) for x in starts]),
        'objects': [], 'changes': [],
        'notes': [f"A skirmish at {text(f'MCID_{loc}_PLACE') or loc}: it appears on the world map once {text(f'MCID_{loc}_PREFIX')}: "
                  f"{text(f'MCID_{loc}')} is cleared.", pool_words(n, chapter_row)],
        'unconfirmed': ["How the game picks among a location's pools, and each foe's level and weapons, isn't traced in its "
                        'program (encount.xml lists the classes and the weapons by level band).'],
    }
    m['grid'] = encode_grid(t, terrain, used_tids, m['id'])
    m['changes'] = layer_changes(t, terrain, used_tids, m['id'])
    return m


def trial_maps(n, chapters, used_tids, story_ids, opens):
    """The Tempest Trials (chapter.xml sheet やり込み): each trial's first two stages are fought on one of its four maps, its third on
    one of six maps every trial shares; each map has two line-ups (Player0 with Mob00, Player1 with Mob10). A map per line-up; each
    opens once its trial's chapter is cleared (the shared ones with the first trials)."""
    out = []
    first = {}
    for tr in D.rows('chapter', 'やり込み'):
        name = text(tr['Name'])
        at = story_ids[story_ids.index('fe17-' + tr['UnlockCid'][4:].lower()) + 1]
        for k, cid in enumerate(D.flag_list(tr['Stage1']), 1):
            first.setdefault(cid, (name, f'map {k}', at))
        for k, cid in enumerate(D.flag_list(tr['Stage3']), 1):
            if cid not in first or story_ids.index(at) < story_ids.index(first[cid][2]):
                first[cid] = ('Final stage', f'map {k}', at)
    for cid, (trial, which, at) in first.items():
        row = chapters[cid]
        key = cid[4:]
        terrain_name = row['Terrain'].replace('MapTerrain_', '') if row['Terrain'] not in ('', 'MapTerrain_*') else key
        for lineup, groups in ((1, ('Player0', 'Mob00')), (2, ('Player1', 'Mob10'))):
            if groups[1] not in dict(D.dispos(key)):
                continue
            script = row['ScriptBmap'] if row['ScriptBmap'] not in ('', '*') else key
            t, units, starts, terrain = random_foes(n, key, script, terrain_name, groups)
            mid = 'fe17-' + key.lower().replace('_', '-') + f'-{lineup}'
            final = trial == 'Final stage'
            m = {
                'id': mid, 'route': 'Challenge', 'chapter': 0, 'heading': 'Tempest Trial',
                'title': (f'Final stage, {which}' if final else f'{trial}, {which}') + f', line-up {lineup}',
                'width': t['width'], 'height': t['height'], 'grid': encode_grid(t, terrain, used_tids, mid),
                'victory': text('MID_RULE_ANNIHILATE') or 'Rout the enemy.', 'defeat': text('MID_RULE_COMMON_LOSE'),
                'objectives': [], 'units': units, 'starts': sorted([list(x) for x in starts]), 'objects': [],
                'changes': layer_changes(t, terrain, used_tids, mid),
                'notes': [('Fought as stage 3 of every Tempest Trial.' if final else f'Fought as stage 1 or 2 of the {trial} trial.')
                          + f" Each map has two line-ups; this is the {'first' if lineup == 1 else 'second'}.", pool_words(n, row)],
                'unconfirmed': ["How the game picks a stage's map and line-up, and each foe, isn't traced in its program."],
            }
            out.append(m)
            opens[mid] = at
    # Each trial's own maps in the trials' order, then the final stage's.
    return sorted(out, key=lambda m: (m['id'].startswith('fe17-c000'), m['id']))


def add_source(sources, item, map_id, kind, words, diffs=None):
    line = {'mapId': map_id, 'kind': kind, 'text': words}
    if diffs:
        line['difficulties'] = diffs
    lst = sources.setdefault(item, [])
    if line not in lst:
        lst.append(line)


def terrain_notes(rs):
    """What a tile's records do beyond Def, Avoid and healing: per army, at the start of a move, damage (flat HP, read in
    App.MapSequenceTurnBeginEffect), and that fliers aren't healed or hurt where the terrain isn't flier ground."""
    out = []
    for field, words in (('Defense', 'Def'), ('Avoid', 'Avo')):
        mine = sum(int(r[f'Player{field}'] or 0) for r in rs)
        foes = sum(int(r[f'Enemy{field}'] or 0) for r in rs)
        if mine or foes:
            out.append(f'{words} {mine:+d} for your units, {foes:+d} for foes')
    first = sum(int(r['MoveFirst'] or 0) for r in rs)
    if first:
        out.append(f'Mov {first:+d} for a unit that starts its move here')
    heal = sum(int(r['Heal'] or 0) for r in rs)
    if heal < 0:
        out.append(f'Takes {-heal} HP at the start of each turn' + ('' if all(int(r['Flag'] or 0) & FLY_ENABLE for r in rs if int(r['Heal'] or 0) < 0)
                                                                   else ' (not fliers)'))
    elif heal > 0 and not all(int(r['Flag'] or 0) & FLY_ENABLE for r in rs if int(r['Heal'] or 0) > 0):
        out.append("Fliers aren't healed here")
    return '. '.join(out) + '.' if out else None


def terrain_info(tid_rows, used_tids, costs):
    """Each code's TerrainInfo: the game's terrain record's Def, Avoid, healing (flat HP) and its cost group's move costs; for a tile
    with an overlap, both records' numbers added (App.BattleDetail.CalcAvoid adds the overlap's to the terrain's), its move cost
    added to the tile's."""
    info, seen = {}, {}
    for key in used_tids:
        if isinstance(key, tuple):
            ov, r = tid_rows[key[0]], tid_rows[key[1]]
            rs = [r, ov]
            name = f"{text(ov['Name'])} on {text(r['Name']).lower()}"
        else:
            r = tid_rows[key]
            rs, ov, name = [r], None, text(r['Name']) or key
        code = encode(GAME, letter_of(key))
        c = costs[r['CostName']]
        move = {}
        for label, col, mv in MOVE_GROUPS:
            cost = None if int(c[col]) == 255 else int(c[col])
            if cost is not None and ov is not None:
                cost += int(ov['FlyCost' if mv in (3, 4) else 'MoveCost'] or 0)
            move[label] = cost
        e = {'name': name, 'def': sum(int(x['Defense'] or 0) for x in rs), 'avo': sum(int(x['Avoid'] or 0) for x in rs),
             'heal': max(0, sum(int(x['Heal'] or 0) for x in rs)), 'move': move}
        note = terrain_notes(rs)
        if note:
            e['note'] = note
        seen.setdefault(code, {}).setdefault(json.dumps(e, sort_keys=True, ensure_ascii=False), []).append(key)
    for code, vs in seen.items():
        best = max(vs.items(), key=lambda kv: sum(len(used_tids[k]) for k in kv[1]))
        e = json.loads(best[0])
        names = sorted({json.loads(k)['name'] for k in vs})
        # A code several named terrains share joins their names when they're few; the walls and buildings, dozens of kinds, keep
        # the commonest's.
        if 1 < len(names) <= 4:
            e['name'] = ' / '.join([e['name']] + [x for x in names if x != e['name']])
        info[code] = e
    return info


def shop_sources(sources, n, story_ids):
    """The armory's and item shop's stock (shop.xml): each list is added once its chapter is cleared, so from the next chapter."""
    nxt = {story_ids[k]: story_ids[k + 1] for k in range(len(story_ids) - 1)}
    for sheet, shop in (('武器屋', 'the armory'), ('道具屋', 'the item shop')):
        cond = None
        for r in D.rows('shop', sheet):
            if r['Condition']:
                cond = r['Condition'].split(',')
                continue
            name = n.item_name(r['Iid'])
            if not name or not cond:
                continue
            chapter = f'fe17-{cond[0].lower()}'
            at = nxt.get(chapter)
            if at is None:
                continue
            extra = ' (once the Mage Cannoneer class is unlocked)' if 'CC_マージカノン' in cond else (
                ' (once the Enchanter class is unlocked)' if 'CC_エンチャント' in cond else '')
            line = {'mapId': at, 'kind': 'shop', 'text': f'Sold at {shop} in the Somniel{extra}'}
            if r['Stock'] not in ('', '-1'):
                line['limited'] = int(r['Stock'])
            add = sources.setdefault(name, [])
            if not any(x['mapId'] == at and x['kind'] == 'shop' for x in add):
                add.append(line)


def forge_sources(sources, n, story_ids):
    """Evolving at the smithy (item.xml 進化): a weapon becomes another for ore and gold, from the chapter after the smithy opens,
    or after the weapon it's made from first turns up."""
    opens = next(r['ConditionCID'] for r in D.rows('hubarea', 1) if r['AID'] == FACILITY['smithy'])
    first = story_ids.index(f"fe17-{opens.replace('CID_', '').lower()}") + 1
    recipes, base = [], None
    for r in D.rows('item', '進化'):
        if r['Eid']:
            base = r['Eid'].replace('EID_', 'IID_')
            continue
        recipes.append((base, r))
    for _ in range(4):
        for base, r in recipes:
            src, made = n.item_name(base), n.item_name(r['Iid'])
            if not src or not made:
                continue
            have = [x for x in sources.get(src, []) if x['mapId'] in story_ids and not x['kind'].startswith('foe')]
            if not have:
                continue
            at = max(first, min(story_ids.index(x['mapId']) for x in have))
            cost = [f"{int(r[k]):,} {w}" for k, w in (('Iron', 'Iron'), ('Steel', 'Steel'), ('Silver', 'Silver')) if r[k] not in ('', '0')]
            words = f"Evolved from {'an' if src[0] in 'AEIOU' else 'a'} {src} at the smithy: {int(r['Price'] or 0):,} gold" + (
                f", {', '.join(cost)}" if cost else '')
            line = {'mapId': story_ids[at], 'kind': 'forge', 'text': words}
            lst = sources.setdefault(made, [])
            if not any(x['kind'] == 'forge' and x['text'] == words for x in lst):
                lst.append(line)


def main():
    n = Names()
    chapters = {r['Cid']: r for r in D.rows('chapter')}
    maps, sources, used_tids = [], {}, {}
    for name in STORY:
        cid = f'CID_{name}'
        m = battle_map(cid, chapters[cid], n, sources, used_tids)
        maps.append(m)
        print(m['id'], m['heading'], m['title'], f"{m['width']}x{m['height']}", len(m['units']), 'units',
              len(m.get('reinforcements', [])), 'groups', len(m['objects']), 'objects')
    story_ids = [m['id'] for m in maps]
    opens = {}
    for name in SIDE:
        cid = f'CID_{name}'
        m = battle_map(cid, chapters[cid], n, sources, used_tids)
        maps.append(m)
        cond = chapters[cid]['GmapSpotOpenCondition'] or DIVINE_OPENS
        while cond[0] == 'G':
            cond = chapters['CID_' + cond]['GmapSpotOpenCondition'] or DIVINE_OPENS
        opens[m['id']] = story_ids[story_ids.index(f'fe17-{cond.lower()}') + 1]
        print(m['id'], m['heading'], m['title'], 'opens', opens[m['id']], len(m['units']), 'units')
    well = next(r['ConditionCID'] for r in D.rows('hubarea', 1) if r['AID'] == WELL).replace('CID_', '').lower()
    for name in XENO:
        cid = f'CID_{name}'
        m = battle_map(cid, chapters[cid], n, sources, used_tids)
        m['notes'].insert(0, 'Comes with the Expansion Pass.')
        maps.append(m)
        opens[m['id']] = story_ids[story_ids.index(f'fe17-{well}') + 1]
        print(m['id'], m['heading'], m['title'], 'opens', opens[m['id']], len(m['units']), 'units')
    # The skirmishes: one per location whose placement file has foes (m021e is an empty stub), opening with its location.
    for name in STORY + SIDE + XENO:
        rows = dict(D.dispos(name + 'E')) if os.path.exists(os.path.join(D.ROMFS, 'gamedata', 'dispos', name.lower() + 'e.xml')) else {}
        if len(rows.get('Mob00', [])) < 2:
            continue
        m = skirmish_map(name, chapters[f'CID_{name}'], n, used_tids, None)
        maps.append(m)
        own = f'fe17-{name.lower()}'
        opens[m['id']] = opens.get(own) or story_ids[min(story_ids.index(own) + 1, len(story_ids) - 1)]
        print(m['id'], m['title'], 'opens', opens[m['id']], len(m['units']), 'slots')
    for m in trial_maps(n, chapters, used_tids, story_ids, opens):
        maps.append(m)
        print(m['id'], m['title'], 'opens', opens[m['id']], len(m['units']), 'slots')
    gm.write(GAME, 'fe17Opens.ts', [
        '/*', " * GENERATED by scripts/build-fe17-maps.py from the chapter table's world map spots. Do not edit by hand.", ' */', '',
        '/** Each paralogue: the story chapter it opens before (the one after the chapter whose clearing opens it). */',
        'export const FE17_OPENS: Record<string, string> = ' + json.dumps(opens, indent=2)])
    shop_sources(sources, n, story_ids)
    forge_sources(sources, n, story_ids)
    tid_rows = {r['Tid']: r for r in D.rows('terrain')}
    costs = {r['Name']: r for r in D.rows('terrain', 1)}
    info = terrain_info(tid_rows, used_tids, costs)
    for m in maps:
        terrain_names(m, info)
    members = []
    for label, col, mv in MOVE_GROUPS:
        members.append((label, sorted({r['Jid'] for r in n.job.values() if r['MoveType'] == str(mv) and r['Name']}), None))
    gm.write_terrain(GAME, TITLE, SCRIPT, info, members, {j: n.class_name(j) for j in n.job},
                     fliers='')
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=DIFFS)


if __name__ == '__main__':
    main()

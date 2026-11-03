"""
Builds src/data/fe17/fe17Maps.ts, fe17Terrain.ts and fe17ItemSources.ts: Fire Emblem Engage's battles (the story: the Prologue and
Chapters 1-26), read from the game's own chapter table, terrain grids, unit placements and battle scripts (scripts/fe17_data.py,
scripts/fe17_events.py; data-raw/fe17/README.md). Run:
    python scripts/build-fe17-maps.py

Each battle is played by its script on each difficulty: what the game places at the start and the opening leaves on the map are
its units; what the turn events place on their turns, and what an area, a death, a talk or a visit places, are its groups and
joiners; what a village visit or a chest's event gives is the village's or the chest's. Coordinates: the game's x across and z up
from the bottom row (0-based), inside the terrain grid's window; the app's (1, 1) is the window's bottom-left tile.
"""
import json
import os
import sys

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
TURNS = 40
LEADER = 16          # App.DisposData.Flags: Leader (the boss)
POS = 128            # a deployment tile
MUST = 256
LORD = 'PID_リュール'
MOVE_GROUPS = [('Infantry', 'Foot', 1), ('Cavalry', 'Horse', 2), ('Fliers', 'Fly', 3), ('Dragons', 'Dragon', 4)]
PHASE = {0: 'player phase', 1: 'enemy phase', 2: 'ally phase'}
# The armory, item shop and smithy open with these chapters cleared (hubarea.xml 施設情報); a shop list's own condition names the
# chapter whose clearing adds it.
FACILITY = {'armory': 'AID_武器屋', 'item': 'AID_道具屋', 'smithy': 'AID_錬成屋', 'flea': 'AID_蚤の市'}

# Each terrain kind by the game's terrain id: its letter (scripts/terrain_codes.py GAME['fe17']).
LETTER = {
    'TID_平地': '.', 'TID_草原': '.', 'TID_地面': '.', 'TID_甲板': '.', 'TID_床': '.', 'TID_加勢マス': '.', 'TID_謎の平地': '.',
    'TID_起動盤': '.', 'TID_火山弾跡': '.', 'TID_魔法陣': '.', 'TID_船着き場': '.', 'TID_床_ターゲット・ワープ禁': '.',
    'TID_床_氷結界': '.', 'TID_魔法陣_氷結界': '.',
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
    'TID_床_全戦禁': '#', 'TID_墓地': '#', 'TID_噴気孔': '#', 'TID_篝火': '#', 'TID_篝火消': '#', 'TID_篝火常': '#', 'TID_燭台': '#',
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
        # (A named character's own asset is AID_Person_<name>: Tiki's, an emblem's.)
        self.generic_names = {n for n, rs in shared.items()
                              if len(rs) > 1 and any(r['Aid'].startswith('AID_') and not r['Aid'].startswith('AID_Person') for r in rs)}

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


def describe_event(ev, n, t):
    """When an event's function runs, in words."""
    k, a = ev['kind'], ev['args']
    if k == 'EventEntryArea':
        return 'When one of your units enters the marked area'
    if k == 'EventEntryDie':
        return f"When {n.name({'Pid': a[1], 'Jid': ''})} is defeated"
    if k == 'EventEntryTalk':
        return f"After {n.name({'Pid': a[1], 'Jid': ''}) if a[1] else 'a unit'} talks to {n.name({'Pid': a[3], 'Jid': ''})}"
    if k == 'EventEntryVisit':
        return f'When the village at ({a[1] - t["x"] + 1}, {a[2] - t["z"] + 1}) is visited'
    if k in ('EventEntryBattleAfter', 'EventEntryBattleBefore', 'EventEntryBattleTalk'):
        who = a[3] or a[1]
        return f"After a fight with {n.name({'Pid': who, 'Jid': ''})}" if who else 'After a fight'
    if k == 'EventEntryDestroy':
        return 'When a village is destroyed'
    return 'After an event in the chapter'


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
    corrin = None
    win = None
    levels = army_levels(name)
    tiers = {}
    for d, dname in enumerate(DIFFS):
        b = play(name, d, levels[0] if levels else None)
        win = win or b.win
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
                forced.append({'name': n.name(r), 'tile': app_tile(t, x, z)})
        # Groups placed after the start: by turn, then by each other event fired on its own.
        timed = []
        for at, kind, data in b.log:
            if kind == 'dispos' and at[0] == 'turn' and data['units']:
                _, turn, phase, ek = at
                when = f'Turn {turn}, {PHASE[phase]}' if ek != 'EventEntryTurnEnd' else f'End of turn {turn}, {PHASE[phase]}'
                timed.append((data['group'], when, data['units'], None))
        for ev in b.events:
            # A turn event whose condition never held with nothing else happening (Chapter 5's countdown, which starts once you
            # fight a platoon or break a wall) is fired on its own too: its groups come after an event the chapter's checks decide.
            if ev['runs']:
                continue
            probe = play(name, d)
            pev = probe.events[ev['index']]
            mark = len(probe.log)
            try:
                probe.fire(pev)
            except Exception:
                continue
            for at, kind, data in probe.log[mark:]:
                if kind == 'dispos' and data['units']:
                    areas = None
                    if ev['kind'] == 'EventEntryArea':
                        a = ev['args']
                        x1, z1, x2, z2 = (int(v) for v in a[1:5])
                        areas = [{'who': 'player', 'rect': [x1 - t['x'] + 1, z1 - t['z'] + 1, x2 - t['x'] + 1, z2 - t['z'] + 1]}]
                    timed.append((data['group'], describe_event(ev, n, t), data['units'], areas))
                if kind == 'item' and ev['kind'] in ('EventEntryVisit', 'EventEntryTbox'):
                    a = ev['args']
                    tile = tuple(app_tile(t, int(a[1]), int(a[2])))
                    iname = n.item_name(data['iid']) or (data['iid'].replace('IID_', '').replace('G', ' gold') if 'G' in data['iid'] else data['iid'])
                    objects.setdefault((ev['kind'], tile), set()).add(iname)
        for group, when, gunits, areas in timed:
            key = group
            entry = groups if any(u.force == E.FORCE_ENEMY for u in gunits) else joiners
            g = entry.setdefault(key, {'when': {}, 'units': [], 'areas': areas})
            g['when'].setdefault(dname, when)
            g['units'].append((dname, [(u, unit_entry(n, u, d, t)) for u in gunits]))
    units = gm._merge_units(per_diff, DIFFS)
    for u in units:
        if u.get('difficulties') == DIFFS:
            u.pop('difficulties')
    m = {
        'id': f'fe17-{name.lower()}', 'route': 'Story' if name[0] == 'M' else 'Paralogue', 'chapter': int(name[1:]),
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
                       'when': g['when'][dn]})
    if js:
        m['joiners'] = js
    for (kind, tile), items in objects.items():
        if kind == 'EventEntryVisit':
            m['objects'].append({'type': 'village', 'tile': list(tile), 'reward': ', '.join(sorted(items))})
        else:
            m['objects'].append({'type': 'chest', 'tile': list(tile), 'contents': ', '.join(sorted(items))})
    # Terrain, top row first.
    rows = []
    for z in range(t['z'] + t['height'] - 1, t['z'] - 1, -1):
        line = []
        for x in range(t['x'], t['x'] + t['width']):
            tid = t['tiles'][z * D.GRID + x]
            used_tids.setdefault(tid, set()).add(m['id'])
            letter = LETTER.get(tid)
            if letter is None:
                raise SystemExit(f'{name}: no letter for {tid}')
            line.append(encode(GAME, letter))
        rows.append(''.join(line))
    m['grid'] = rows
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


def add_source(sources, item, map_id, kind, words, diffs=None):
    line = {'mapId': map_id, 'kind': kind, 'text': words}
    if diffs:
        line['difficulties'] = diffs
    lst = sources.setdefault(item, [])
    if line not in lst:
        lst.append(line)


def terrain_info(tid_rows, used_tids, costs):
    """Each code's TerrainInfo: the game's terrain record's Def, Avoid, healing and its cost group's move costs."""
    info, seen = {}, {}
    for tid in used_tids:
        r = tid_rows[tid]
        code = encode(GAME, LETTER[tid])
        c = costs[r['CostName']]
        e = {'name': text(r['Name']) or tid, 'def': int(r['Defense'] or 0), 'avo': int(r['Avoid'] or 0), 'heal': int(r['Heal'] or 0),
             'move': {label: (None if int(c[col]) == 255 else int(c[col])) for label, col, _ in MOVE_GROUPS}}
        seen.setdefault(code, {}).setdefault(json.dumps(e, sort_keys=True, ensure_ascii=False), []).append(tid)
    for code, vs in seen.items():
        best = max(vs.items(), key=lambda kv: sum(len(used_tids[t]) for t in kv[1]))
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
    gm.write(GAME, 'fe17Opens.ts', [
        '/*', " * GENERATED by scripts/build-fe17-maps.py from the chapter table's world map spots. Do not edit by hand.", ' */', '',
        '/** Each paralogue: the story chapter it opens before (the one after the chapter whose clearing opens it). */',
        'export const FE17_OPENS: Record<string, string> = ' + json.dumps(opens, indent=2)])
    shop_sources(sources, n, story_ids)
    forge_sources(sources, n, story_ids)
    tid_rows = {r['Tid']: r for r in D.rows('terrain')}
    costs = {r['Name']: r for r in D.rows('terrain', 1)}
    info = terrain_info(tid_rows, used_tids, costs)
    members = []
    for label, col, mv in MOVE_GROUPS:
        members.append((label, sorted({r['Jid'] for r in n.job.values() if r['MoveType'] == str(mv) and r['Name']}), None))
    gm.write_terrain(GAME, TITLE, SCRIPT, info, members, {j: n.class_name(j) for j in n.job},
                     fliers='')
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=DIFFS)


if __name__ == '__main__':
    main()

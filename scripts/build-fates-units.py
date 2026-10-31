"""
Builds src/data/maps/gameUnits.ts from the game's unit placement files (Dispos) and character files
(Person): every starting enemy and green unit on each difficulty with its English name, pair-ups and
item drops, the player's starting tiles, Corrin's own tile, and each reinforcement wave.

Needs the dumped game files in data-raw/fates/romfs/ (git-ignored). Run:
    python scripts/build-fates-units.py
"""
import json
import re
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_arrivals import arrivals as read_arrivals  # noqa: E402
from fates_dispos import read as read_dispos  # noqa: E402
from fates_lz import decompress  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_cmb import Script  # noqa: E402
from fates_maps import GRIND, MAPS, PACK, ROOT, find, find_script, terrain, terrain_script, text_for  # noqa: E402

OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameUnits.ts')
DIFFS = ['Normal', 'Hard', 'Lunatic']


def ts_when(w):
    out = []
    if 'when' in w:
        v = w['when']
        out.append(f"when: {json.dumps(v)}" if isinstance(v, str) else
                   'when: { ' + ', '.join(f"{d}: {json.dumps(t)}" for d, t in v.items()) + ' }')
    if w.get('areas'):
        out.append('areas: [' + ', '.join(f"{{ who: '{a['who']}', rect: [{', '.join(map(str, a['rect']))}] }}" for a in w['areas']) + ']')
    return out


def persons(code, pack=None):
    """PID -> (MPID, has portrait, class number) from a chapter's Person file (152-byte records; the class number is at +0x24)."""
    p = find('Person', code, pack)
    if not p:
        return {}
    d = decompress(open(p, 'rb').read())
    B = 0x20
    ds = struct.unpack_from('<I', d, 4)[0]

    def s(ptr):
        o = B + ptr
        if not ptr or o < B + ds - 4 or o >= len(d):
            return None
        try:
            return d[o:d.index(b'\0', o)].decode('shift_jis')
        except (ValueError, UnicodeDecodeError):
            return None
    out = {}
    for o in range(B, B + ds, 4):
        pid = s(struct.unpack_from('<I', d, o)[0])
        if pid and pid.startswith('PID_'):
            fid = s(struct.unpack_from('<I', d, o + 4)[0])
            mpid = s(struct.unpack_from('<I', d, o + 12)[0])
            if mpid and mpid.startswith('MPID_'):
                out[pid] = (mpid, bool(fid and fid.startswith('FID_')), struct.unpack_from('<H', d, o + 0x24)[0])
    return out


GRIND_WHEN = 'Spawn point (no set turn: see the map note)'

# The names the game gives a whole army rather than a person ('Nohrian', 'Vallite', 'Invader', 'Illusion', 'Ruffian'...): a unit
# named only by one of these goes by its class.
ARMIES = {'MPID_暗夜兵', 'MPID_白夜兵', 'MPID_透魔兵', 'MPID_謎の兵', 'MPID_幻影兵', 'MPID_賊', 'MPID_部族兵', 'MPID_参加者',
          'MPID_フウマ兵', 'MPID_魔物', 'MPID_傭兵団', 'MPID_運営者', 'MPID_シュヴァリエ兵', 'MPID_その他', 'MPID_村人'}


def class_names(text):
    """Class number -> English name, from GameData.bin's class table: 128-byte records (JID, FID, MJID pointers), the class's
    number at +0x10, the number a character record gives at +0x24."""
    d = decompress(open(os.path.join(ROOT, 'data-raw', 'fates', 'romfs', 'GameData.bin.lz'), 'rb').read())
    B = 0x20

    def s(ptr):
        o = B + ptr
        if not B < o < len(d):
            return None
        try:
            return d[o:d.index(b'\0', o)].decode('shift_jis')
        except (ValueError, UnicodeDecodeError):
            return None
    out = {}
    for o in range(B, len(d) - 0x14, 4):
        jid = s(struct.unpack_from('<I', d, o)[0])
        mjid = s(struct.unpack_from('<I', d, o + 8)[0]) if jid and jid.startswith('JID_') else None
        if mjid and mjid.startswith('MJID_') and mjid in text:
            out[struct.unpack_from('<H', d, o + 0x10)[0]] = text[mjid]
    return out


def item_text(iid, text):
    """An item's English name. A few item ids have no line of their own: the Heirs of Fate copies of the royals' weapons
    ('IID_E035_ジークフリート'), a chapter's own copy ('IID_ドロー（B027）', Conquest 27's Entrap) and Anankos's numbered breaths
    ('IID_透魔竜のブレス１'): they read as the item they copy."""
    for key in (iid, re.sub(r'^IID_E\d+_', 'IID_', iid), re.sub(r'（[^）]*）$', '', iid), re.sub(r'[０-９0-9]+$', '', iid)):
        if 'M' + key in text:
            return text['M' + key]
    return None


# Anankos's two breaths share the name "Dragon Breath"; the short-range one (Mt 30, range 1-3) gets a suffix, as Ganglari's
# reward does (see build-fates-items.py).
SUFFIX = {'IID_透魔竜のブレス１': ' (1-3)',
          # The Heirs of Fate copies are the royals' weapons stat for stat, but this 'Skadi' has the Fujin Yumi's stats (Mt 14, range
          # 2), not Skadi's: kept apart so it isn't taken for the real one.
          'IID_E040_スカディ': ' (Heirs of Fate)'}


def opening_groups(script):
    """The groups a chapter's opening handler (kind 0x07) places by name, besides the player's."""
    if not script:
        return set()
    s = Script(script)
    out = set()
    for h in s.handlers():
        if h['kind'] & 0xFF != 7:
            continue
        ins = s.disasm(h)
        for k, (_, n, a) in enumerate(ins):
            if n == 'call' and a.startswith('ev::Dispos/') and k >= 2 and ins[k - 2][1] == 'str':
                g = ins[k - 2][2].strip("'")
                if not g.startswith('Player'):
                    out.add(g)
    return out


def label(group):
    """'Reinforce03' -> 'Group 3', 'Reinforce01_2' -> 'Group 1-2'; other names are relabelled later."""
    m = re.fullmatch(r'Reinforce_?(\d+(?:_\d+)*)', group)
    return 'Group ' + '-'.join(str(int(n)) for n in m.group(1).split('_')) if m else group


def main():
    def item(iid):
        name = item_text(iid, text) or iid
        # Items the game gives one name get a suffix (see build-fates-items.py): the true Ganglari, Kiragi's bronze Fujin Yumi,
        # Anankos's short-range breath.
        name += ' (reward)' if '真ガングレリ' in iid else ' (Bronze form)' if '（青銅）' in iid else SUFFIX.get(iid, '')
        # Gold-bag items ('5000G') read the way the rest of the app writes gold.
        return f'{int(name[:-1]):,} Gold' if name[:-1].isdigit() and name.endswith('G') else name

    classes = class_names(text_for())
    result = {}
    for map_id, (code, route, _) in MAPS.items():
        pack = PACK.get(map_id)
        text = text_for(pack)
        t = read_terrain(terrain(code, pack))
        W, H = t['w'] - 2, t['h'] - 2
        people = persons(code, pack)

        def name(pid):
            if pid in people:
                mpid, portrait, job = people[pid]
                # A unit named only by its army goes by its class, as the game shows it ('Spear Master'), not 'Nohrian'.
                if mpid in ARMIES and job in classes:
                    return classes[job]
                return text.get(mpid, mpid)
            if pid == 'PID_無し':
                return 'Random enemy'
            base = pid.split('_')[-1]
            # 'PID_カンナ男' / 'PID_カンナ女': Kana's male and female versions share one name.
            return text.get('M' + pid) or text.get('MPID_' + base) or text.get('MPID_' + base.rstrip('男女'), pid)

        def named(pid):
            return pid in people and people[pid][1]

        def character(pid):
            """A playable character from the main game: their records aren't in the chapter's file."""
            return bool(pid) and pid not in people and pid != 'PID_無し' and name(pid) != pid

        def base(pid):
            """The character a route's own record stands for: Revelation's 'PID_C_サイゾウ' is the script's 'PID_サイゾウ'."""
            return re.sub(r'^PID_[ABC]_', 'PID_', pid or '')

        def talk_text(pid):
            t = talks.get(base(pid))
            if not t:
                return None
            who = ' or '.join(t['with'])
            # A talk that hands nobody over itself recruits when another handler of the chapter does (Nyx in Conquest 9).
            force = 0 if t['force'] is None and base(pid) in transferred else t['force']
            return (f'Recruit: talk with {who}' if force == 0 else f'Talk with {who}: they turn green and stop fighting'
                    if force == 2 else f'Talk with {who}')

        def on_map(xy):
            return 1 <= xy[0] <= W and 1 <= xy[1] <= H

        factions = read_dispos(find('Dispos', code, pack), H)
        script = find_script(code, pack)
        timing = read_arrivals(script, H) if script else {}
        # Who can talk to whom (handler kind 0x617: the speaker's PID or '' for anyone, then the listener's), and whether it recruits
        # (the handler hands the unit over with UnitTransferByIndex).
        talks = {}
        if script:
            sc = Script(script)
            for h in sc.handlers():
                if h['kind'] & 0xFFF != 0x617 or len(h['args']) < 3:
                    continue
                try:
                    speaker, target = sc.string(h['args'][0]), sc.string(h['args'][2])
                    ins = sc.disasm(h)
                except (ValueError, IndexError, UnicodeDecodeError):
                    continue
                # No speaker named: anyone in your army (Conquest 16's four suspects).
                who = 'any of your units' if not speaker else 'Corrin' if speaker.startswith('PID_プレイヤー') else name(speaker)
                t = talks.setdefault(target, {'with': [], 'force': None})
                if who not in t['with']:
                    t['with'].append(who)
                # Where the talk sends the listener: UnitTransferByIndex(unit, force), 0 your army (a recruit), 2 the green army
                # (Arthur and Effie in Birthright 23 stop fighting).
                last = None
                for i, (_, op, arg) in enumerate(ins):
                    if op == 'str' and isinstance(arg, str) and arg.startswith("'PID_"):
                        last = arg.strip("'")
                    if op == 'call' and str(arg).startswith('ev::UnitTransferByIndex') and last == target and i and ins[i - 1][1] == 'int':
                        t['force'] = 0 if 0 in (t['force'], ins[i - 1][2]) else ins[i - 1][2]

        transferred = set()
        for h in sc.handlers() if script else []:
            try:
                ins = sc.disasm(h)
            except (ValueError, IndexError):
                continue
            last = None
            for i, (_, op, arg) in enumerate(ins):
                if op == 'str' and isinstance(arg, str) and arg.startswith("'PID_"):
                    last = arg.strip("'")
                if op == 'call' and str(arg).startswith('ev::UnitTransferByIndex') and last and i and ins[i - 1][1:] == ('int', 0):
                    transferred.add(last)
        # What a recruit brings when they join: a Support group's units, a green unit the script hands over, a foe a talk
        # recruits. Their own items, the gear that is really theirs (the Player groups' later kits are only presets).
        recruits = []

        def recruit(u):
            """Notes a unit joining your army here, with its own items."""
            pid = u['pid'] or ''
            if u['items'] and (named(pid) or character(pid)) and route in ('Shared', 'Birthright', 'Conquest', 'Revelation'):
                mine = {'name': name(pid), 'items': [item(n) for n, _ in u['items']]}
                if mine not in recruits:
                    recruits.append(mine)

        # How a green unit joins: a talk can hand over others besides its listener (talking to Hinoka in Birthright 8 brings Azama
        # and Setsuna too); the chapter's end handler (kind 0xd) hands units over or places a Support group (a child at the end of
        # their paralogue).
        with_talk, at_end, end_groups = {}, set(), set()
        for h in sc.handlers() if script else []:
            try:
                ins = sc.disasm(h)
            except (ValueError, IndexError):
                continue
            talk = h['kind'] & 0xFFF == 0x617 and len(h['args']) >= 3
            last = None
            for i, (_, op, arg) in enumerate(ins):
                if op == 'str' and isinstance(arg, str):
                    last = arg.strip("'")
                if op == 'call' and str(arg).startswith('ev::UnitTransferByIndex') and last and i and ins[i - 1][1:] == ('int', 0):
                    if talk and last != sc.string(h['args'][2]):
                        speaker = sc.string(h['args'][0])
                        who = 'any of your units' if not speaker else 'Corrin' if speaker.startswith('PID_プレイヤー') else name(speaker)
                        with_talk.setdefault(last, (who, name(sc.string(h['args'][2]))))
                    elif h['kind'] & 0xFF == 0xD:
                        at_end.add(last)
                if op == 'call' and str(arg).startswith('ev::Dispos') and h['kind'] & 0xFF == 0xD and last and last.startswith('Support'):
                    end_groups.add(last)

        script_bytes = open(script, 'rb').read() if script else b''
        tpath = terrain_script(code, pack)
        tscript = Script(tpath) if tpath else None

        def used(group):
            """Whether a script ever calls the group: some files keep groups nothing brings in."""
            g = group.encode()
            return g in script_bytes or bool(tscript and g in tscript.d)

        def terrain_when(group):
            """A group the terrain script brings in, from the village or door it hangs on."""
            for h in tscript.handlers() if tscript else []:
                try:
                    ins = tscript.disasm(h)
                except (ValueError, IndexError):
                    continue
                if not any(n == 'str' and a == repr(group) for _, n, a in ins):
                    continue
                a = h['args']
                if len(a) >= 5 and a[4] in (1, 9):
                    x, y = a[0], H + 1 - a[1]
                    what = 'village' if a[4] == 1 else 'door'
                    verb = 'visited' if a[4] == 1 else 'opened'
                    return {'when': f'When the {what} at ({x}, {y}) is {verb}',
                            'areas': [{'who': 'player', 'rect': [x, y, x, y]}]}
            return {'when': 'During a map event'}

        def when(group):
            """{'when': text or {difficulty: text}, 'areas': [...]} for a group, from the chapter script."""
            by = timing.get(group, {})
            if not by:
                return terrain_when(group) if tscript and group.encode() in tscript.d else {}
            texts = {d: v['text'] for d, v in by.items()}
            areas = []
            for v in by.values():
                for a in v['areas']:
                    if a not in areas:
                        areas.append(a)
            single = len(set(texts.values())) == 1 and len(texts) == 3
            return {'when': next(iter(texts.values())) if single else texts, 'areas': areas}
        opening = opening_groups(script)
        units, starts, corrin, waves, joins, forced, kit = [], [], None, [], [], [], []
        end_names = {name(u['pid'] or '') for f in factions if f['name'] in end_groups for u in f['units']}

        def joins_text(pid):
            """What a named green unit does about joining, when no talk of its own says."""
            by = with_talk.get(base(pid))
            end = base(pid) in at_end or name(pid) in end_names
            if by and end:
                return f'Joins your army when {by[0]} talks to {by[1]}, or at the end of the chapter'
            if by:
                return f'Joins your army when {by[0]} talks to {by[1]}'
            if end:
                return 'Joins your army at the end of the chapter'
            return "Stays a green unit: doesn't join your army here"

        for f in factions:
            fname = f['name']
            if fname in ('Player', 'PlayerM', 'PlayerF'):
                # 'PlayerM' / 'PlayerF' are the male / female Corrin versions of the same deployment.
                for u in f['units']:
                    # What each of your units starts the chapter carrying: what the spoiler block lists as in your army's hands.
                    # (Story chapters only: a paralogue or DLC map lists whichever form of Yato that point of the game has.)
                    if u['items'] and (u['pid'] or '') != 'PID_無し' and route in ('Shared', 'Birthright', 'Conquest', 'Revelation'):
                        mine = {'name': 'Corrin' if (u['pid'] or '').startswith('PID_プレイヤー') else name(u['pid'] or ''), 'items': [item(n) for n, _ in u['items']]}
                        if mine not in kit:
                            kit.append(mine)
                    if on_map(u['start']) and u['start'] not in starts:
                        starts.append(u['start'])
                        if (u['pid'] or '').startswith('PID_プレイヤー') and corrin is None:
                            corrin = u['start']
                    # A slot's flag byte (0x10): 0x20 an open slot, 0x04 Corrin, 0x08 a unit you must deploy
                    # (the parent in a child's paralogue), 0x80 one the game places on that tile itself, and
                    # 0x00 the scripted line-ups of chapters 1-6, also fixed.
                    pid, flag = u['pid'] or '', u['raw'][0x10]
                    if pid.startswith('PID_プレイヤー') or flag not in (0x00, 0x08, 0x80):
                        continue
                    if flag == 0x08:
                        entry = {'name': name(pid)}
                    elif on_map(u['start']):
                        entry = {'name': name(pid), 'tile': u['start']}
                    else:
                        continue  # walks in later
                    same = next((x for x in forced if x.get('tile') == entry.get('tile') and 'tile' in entry), None)
                    if same and entry['name'] not in same['name'].split(' or '):
                        same['name'] += ' or ' + entry['name']  # Felicia or Jakob, by Corrin's gender
                    elif not same and entry not in forced:
                        forced.append(entry)
                continue
            if fname.startswith(('Support', 'Reinforce', 'Enemy', 'Ally')) and fname not in ('Enemy', 'Ally') and not used(fname):
                continue
            # Placed when the chapter opens: 'Enemy' / 'Ally', or whatever the opening handler places by name.
            at_start = fname in opening or (fname in ('Enemy', 'Ally') and not opening)
            # An 'Enemy…' group placed on turn 1 before you move (Hidden Truths 1's army) is on the map when play
            # begins. 'Reinforce…' groups placed then (Leo's ambush in Birthright 18) count as reinforcements.
            if not at_start and fname.startswith('Enemy') and when(fname).get('when') == 'Turn 1, player phase':
                at_start = True
            if map_id in GRIND:
                at_start = False
            if fname.startswith('Support'):
                for u in f['units']:
                    recruit(u)
                    if not on_map(u['arrive']):
                        continue  # joins by event, off the map
                    joins.append({'name': name(u['pid'] or ''), 'tile': u['arrive'], 'from': u['start'], 'group': fname,
                                  **when(fname)})
                continue
            if not fname.startswith(('Enemy', 'Ally', 'Reinforce')):
                continue
            group = []
            for i, u in enumerate(f['units']):
                diff_bits = u['raw'][0x11] & 7
                pair_bits = u['raw'][0x12]
                if pair_bits & 2:
                    continue  # the supporting half of a pair-up; recorded on its lead
                ds = [d for k, d in enumerate(DIFFS) if diff_bits >> k & 1]
                if not ds:
                    continue
                # Where the unit stands once it has moved in; a unit placed nowhere on the map (the script
                # picks its spot) is left out.
                tile = u['arrive'] if on_map(u['arrive']) else u['start'] if on_map(u['start']) else None
                if tile is None:
                    continue
                pid = u['pid'] or ''
                # 'PID_無し' marks a spawn point whose unit the script makes up (random class).
                spawn = pid == 'PID_無し'
                support = f['units'][i + 1] if pair_bits & 1 and i + 1 < len(f['units']) else None
                drops = [item(n) for n, fl in u['items'] if fl & 1]
                # What the foe carries and fights with: the non-drop slots (a drop is a separate bonus item).
                carries = [item(n) for n, fl in u['items'] if not fl & 1]
                if support:
                    drops += [item(n) for n, fl in support['items'] if fl & 1]
                    carries += [item(n) for n, fl in support['items'] if not fl & 1]
                boss = 'ボス' in pid or bool(u['raw'][0x11] & 0x20)
                team = u['team']
                # A playable character fighting you gets the named marker, except in the grinding maps, where the whole cast
                # turns up as foes for fun (Beach Brawl, Royal Royale).
                kind = 'ally' if team == 2 else 'boss' if boss else 'named' if named(pid) or (character(pid) and map_id not in GRIND) else 'enemy'
                entry = {
                    'type': kind, 'name': 'Random enemy' if spawn else name(pid), 'tile': tile,
                    'difficulties': ds,
                }
                if not at_start:
                    entry['from'] = u['start']
                if kind == 'boss' and not named(pid):
                    entry['generic'] = True
                # A green unit with no name of its own (a plain green dot on the map): one the chapter defines
                # without a portrait. Playable characters in their paralogues use the main game's IDs, which
                # aren't in the chapter's file, so they count as named.
                if kind == 'ally' and pid in people and not people[pid][1]:
                    entry['generic'] = True
                if talk_text(pid):
                    entry['talk'] = talk_text(pid)
                elif kind == 'ally' and not entry.get('generic') and map_id not in GRIND:
                    entry['note'] = joins_text(pid)
                if support:
                    entry['paired'] = True
                    entry['partner'] = name(support['pid'] or '')
                if drops:
                    entry['drops'] = drops
                if carries and kind != 'ally':
                    entry['carries'] = carries
                if base(pid) in transferred or (talks.get(base(pid)) or {}).get('force') == 0:
                    recruit(u)
                group.append(entry)
            if at_start:
                units += group
            elif group:
                arrival = {'when': GRIND_WHEN} if map_id in GRIND else when(fname)
                waves.append({'group': fname, 'label': label(fname), 'units': group, **arrival})
        # Groups without a number get plain labels: the game's own names are internal shorthand.
        letters = iter('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        for i, w in enumerate(waves):
            if map_id in GRIND:
                w['label'] = f'Spawn {i + 1}'
            elif not w['label'].startswith('Group '):
                w['label'] = f'Group {next(letters)}'
        # Gender versions of one unit (Kana's 'Ally_Male' / 'Ally_Female') come out identical: keep one.
        units = [u for i, u in enumerate(units) if u['type'] != 'ally' or u not in units[:i]]
        # Two foes on one tile without the pair-up flag (Revelation 25 and 27) still stand as a pair: the
        # first leads, the second supports.
        merged = []
        for u in units:
            lead = next((m for m in merged if m['tile'] == u['tile'] and m['type'] != 'ally' and u['type'] != 'ally'
                         and not m.get('paired') and not u.get('paired') and m['difficulties'] == u['difficulties']), None)
            if lead:
                lead['paired'], lead['partner'] = True, u['name']
                lead['drops'] = lead.get('drops', []) + u.get('drops', [])
                if not lead['drops']:
                    del lead['drops']
                if u.get('carries'):
                    lead['carries'] = lead.get('carries', []) + u['carries']
            else:
                merged.append(u)
        units = merged
        result[map_id] = {'units': units, 'starts': starts, 'corrin': corrin, 'waves': waves, 'joins': joins, 'forced': forced, 'kit': kit,
                          'recruits': recruits}

    def ts_unit(u, indent):
        f = [f"type: '{u['type']}'", f"name: {json.dumps(u['name'])}", f"tile: [{u['tile'][0]}, {u['tile'][1]}]"]
        if u.get('paired'):
            f.append('paired: true')
            f.append(f"partner: {json.dumps(u['partner'])}")
        if u.get('drops'):
            f.append(f"drops: {json.dumps(u['drops'])}")
        if u.get('carries'):
            f.append(f"carries: {json.dumps(u['carries'])}")
        if len(u['difficulties']) < 3:
            f.append('difficulties: [' + ', '.join(f"'{d}'" for d in u['difficulties']) + ']')
        if u.get('generic'):
            f.append('generic: true')
        if u.get('talk'):
            f.append(f"talk: {json.dumps(u['talk'])}")
        if u.get('note'):
            f.append(f"note: {json.dumps(u['note'])}")
        if 'from' in u and u['from'] != u['tile']:
            f.append(f"from: [{u['from'][0]}, {u['from'][1]}]")
        return ' ' * indent + '{ ' + ', '.join(f) + ' },'

    first_kits(result)
    lines = [
        "import type { Arrival, Difficulty, MapUnit, Tile } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fates-units.py from the game's unit placement and character files.",
        ' * Do not edit by hand: fix the generator, or put notes on the map itself.',
        ' */',
        'export interface GameUnit extends Omit<MapUnit, "difficulties"> {',
        '  difficulties?: Difficulty[]',
        '  /** The pair-up partner standing with this unit. */',
        '  partner?: string',
        "  /** Where a reinforcement enters from, when it isn't the tile it moves to. */",
        '  from?: Tile',
        "  /** A boss without a portrait (its name is only its army's, e.g. 'Invader'), or a green unit with no name of its own. */",
        '  generic?: true',
        '}',
        '',
        'export interface GameUnits {',
        '  units: GameUnit[]',
        '  starts: Tile[]',
        '  corrin?: Tile',
        "  /** Units besides Corrin the game deploys for you: on a fixed tile, or (no tile) wherever you place them. */",
        '  forced?: { name: string; tile?: Tile }[]',
        '  /** Reinforcement groups, in the order the game lists them (turns come from the chapter script). */',
        '  waves: ({ group: string; label: string; units: GameUnit[] } & Arrival)[]',
        "  /** Units that join mid-chapter: where they walk in from and the tile they stop on. */",
        '  joins: ({ name: string; tile: Tile; from: Tile; group: string } & Arrival)[]',
        "  /** What each of your own units starts the chapter carrying (a weapon you hold from this chapter on). */",
        '  kit?: { name: string; items: string[] }[]',
        "  /** A grinding map (DLC): enemies keep spawning at random points, on no set turn. */",
        '  grind?: true',
        '}',
        '',
        'export const GAME_UNITS: Record<string, GameUnits> = {',
    ]
    for map_id, r in result.items():
        lines.append(f"  '{map_id}': {{")
        lines.append('    units: [')
        lines += [ts_unit(u, 6) for u in r['units']]
        lines.append('    ],')
        lines.append('    starts: [' + ', '.join(f'[{x}, {y}]' for x, y in r['starts']) + '],')
        if r['corrin']:
            lines.append(f"    corrin: [{r['corrin'][0]}, {r['corrin'][1]}],")
        if r['kit']:
            lines.append('    kit: [' + ', '.join('{ name: ' + json.dumps(k['name']) + ', items: ' + json.dumps(k['items']) + ' }' for k in r['kit']) + '],')
        if map_id in GRIND:
            lines.append('    grind: true,')
        if r['forced']:
            lines.append('    forced: [' + ', '.join(
                '{ name: ' + json.dumps(x['name']) + (f", tile: [{x['tile'][0]}, {x['tile'][1]}]" if 'tile' in x else '') + ' }'
                for x in r['forced']) + '],')
        lines.append('    joins: [')
        for j in r['joins']:
            f = [f"name: {json.dumps(j['name'])}", f"tile: [{j['tile'][0]}, {j['tile'][1]}]", f"from: [{j['from'][0]}, {j['from'][1]}]",
                 f"group: '{j['group']}'"] + ts_when(j)
            lines.append('      { ' + ', '.join(f) + ' },')
        lines.append('    ],')
        lines.append('    waves: [')
        for w in r['waves']:
            extra = ''.join(', ' + x for x in ts_when(w))
            lines.append(f"      {{ group: {json.dumps(w['group'])}, label: {json.dumps(w['label'])}{extra}, units: [")
            lines += [ts_unit(u, 8) for u in w['units']]
            lines.append('      ] },')
        lines.append('    ],')
        lines.append('  },')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT)
    for map_id, r in result.items():
        tot = {d: sum((2 if u.get('paired') else 1) for u in r['units'] if d in u['difficulties'] and u['type'] != 'ally') for d in DIFFS}
        special = [(u['type'], u['name'], tuple(u['tile']), u.get('drops')) for u in r['units'] if u['type'] != 'enemy' or u.get('drops')]
        print(map_id, tot, len(r['waves']), 'waves;', special)


ROUTE_PREFIX = {'Birthright': 'fe14b', 'Conquest': 'fe14c', 'Revelation': 'fe14r'}


def first_kits(result):
    """What your units hold that counts as yours from a chapter: Corrin's gear in every chapter (the Yato's forms), what a
    recruit brings in the chapter they join (a Support group's unit, a green unit the script hands over, a foe a talk recruits),
    and a unit's gear where it first turns up in a Player group on the route without having joined before (the prologue's
    line-ups; Kaden in Birthright 12). The Player groups after that list each unit with preset gear (Azura with a Bronze Lance in
    Birthright 6, Benny with a Blessed Lance in Conquest 21, Hinata in Birthright 26) that the game only hands to a unit it has to
    make, never to one already in your army, so those don't count."""
    keep = set()
    for route, prefix in ROUTE_PREFIX.items():
        ids = [f'fe14-{n}' for n in range(1, 6)] + [f'{prefix}-{n}' for n in range(6, 28)] + [f'{prefix}-endgame']
        joined = set()
        for map_id in ids:
            if map_id not in result:
                continue
            for k in result[map_id]['kit']:
                who = k['name']
                if who == 'Corrin' or who not in joined:
                    keep.add((map_id, who))
                joined.add(who)
            joined |= {k['name'] for k in result[map_id]['recruits']}
    for map_id, r in result.items():
        kit = [k for k in r['kit'] if (map_id, k['name']) in keep]
        r['kit'] = kit + [k for k in r.pop('recruits') if k not in kit]


if __name__ == '__main__':
    main()

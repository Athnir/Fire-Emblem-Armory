"""
Builds src/data/maps/gameUnits.ts from the game's unit placement files (Dispos) and character files
(Person): every starting enemy and green unit on each difficulty with its English name, pair-ups and
item drops, the player's starting tiles, Corrin's own tile, and each reinforcement wave.

Needs the dumped game files in data-raw/fates/romfs/ (git-ignored). Run:
    python scripts/build-fates-units.py
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_arrivals import arrivals as read_arrivals  # noqa: E402
from fates_dispos import read as read_dispos  # noqa: E402
from fates_lz import decompress  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_text import read as read_text  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
CONQ = os.path.join(RAW, 'dlc', '00000002', 'local', 'GameData')
OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameUnits.ts')
DIFFS = ['Normal', 'Hard', 'Lunatic']

MAPS = {f'fe14-{n}': f'A00{n}' for n in range(1, 6)}
MAPS.update({f'fe14c-{n}': f'B0{n:02d}' for n in range(6, 28)})
MAPS['fe14c-endgame'] = 'B028'


def find(kind, code):
    for base in (os.path.join(CONQ, kind, code[0]), os.path.join(RAW, kind), os.path.join(RAW, kind, code[0])):
        p = os.path.join(base, code + '.bin.lz')
        if os.path.exists(p):
            return p
    return None


def find_script(code):
    for p in (os.path.join(RAW, 'dlc', '00000002', 'local', 'Scripts', code[0], code + '.cmb'),
              os.path.join(RAW, 'Scripts', code + '.cmb'), os.path.join(RAW, 'Scripts', code[0], code + '.cmb')):
        if os.path.exists(p):
            return p
    return None


def ts_when(w):
    out = []
    if 'when' in w:
        v = w['when']
        out.append(f"when: {json.dumps(v)}" if isinstance(v, str) else
                   'when: { ' + ', '.join(f"{d}: {json.dumps(t)}" for d, t in v.items()) + ' }')
    if w.get('areas'):
        out.append('areas: [' + ', '.join(f"{{ who: '{a['who']}', rect: [{', '.join(map(str, a['rect']))}] }}" for a in w['areas']) + ']')
    return out


def persons(code):
    """PID -> (MPID, has portrait) from a chapter's Person file."""
    p = find('Person', code)
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
                out[pid] = (mpid, bool(fid and fid.startswith('FID_')))
    return out


def main():
    text = read_text(os.path.join(RAW, 'm', '@E', 'GameData.bin.lz'))

    def item(iid):
        return text.get('M' + iid, iid)

    result = {}
    for map_id, code in MAPS.items():
        t = read_terrain(os.path.join(RAW, 'Terrain', code + '.bin.lz'))
        W, H = t['w'] - 2, t['h'] - 2
        people = persons(code)

        def name(pid):
            if pid in people:
                return text.get(people[pid][0], people[pid][0])
            return text.get('M' + pid) or text.get('MPID_' + pid.split('_')[-1], pid)

        def named(pid):
            return pid in people and people[pid][1]

        def on_map(xy):
            return 1 <= xy[0] <= W and 1 <= xy[1] <= H

        factions = read_dispos(find('Dispos', code), H)
        script = find_script(code)
        timing = read_arrivals(script, H) if script else {}

        def when(group):
            """{'when': text or {difficulty: text}, 'areas': [...]} for a group, from the chapter script."""
            by = timing.get(group, {})
            if not by:
                return {}
            texts = {d: v['text'] for d, v in by.items()}
            areas = []
            for v in by.values():
                for a in v['areas']:
                    if a not in areas:
                        areas.append(a)
            single = len(set(texts.values())) == 1 and len(texts) == 3
            return {'when': next(iter(texts.values())) if single else texts, 'areas': areas}
        units, starts, corrin, waves, joins = [], [], None, [], []
        for f in factions:
            fname = f['name']
            if fname == 'Player':
                for u in f['units']:
                    if on_map(u['start']):
                        starts.append(u['start'])
                        if (u['pid'] or '').startswith('PID_プレイヤー') and corrin is None:
                            corrin = u['start']
                continue
            if fname.startswith('Support'):
                for u in f['units']:
                    if not on_map(u['arrive']):
                        continue  # joins by event, off the map
                    joins.append({'name': name(u['pid'] or ''), 'tile': u['arrive'], 'from': u['start'], 'group': fname,
                                  **when(fname)})
                continue
            if fname not in ('Enemy', 'Ally') and not fname.startswith('Reinforce'):
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
                pid = u['pid'] or ''
                support = f['units'][i + 1] if pair_bits & 1 and i + 1 < len(f['units']) else None
                drops = [item(n) for n, fl in u['items'] if fl & 1]
                if support:
                    drops += [item(n) for n, fl in support['items'] if fl & 1]
                boss = 'ボス' in pid or bool(u['raw'][0x11] & 0x20)
                team = u['team']
                kind = 'ally' if team == 2 else 'boss' if boss else 'named' if named(pid) else 'enemy'
                entry = {
                    'type': kind, 'name': name(pid), 'tile': u['start'] if on_map(u['start']) else u['arrive'],
                    'difficulties': ds,
                }
                if fname != 'Enemy':
                    entry['from'] = u['start']
                if kind == 'boss' and not named(pid):
                    entry['generic'] = True
                if support:
                    entry['paired'] = True
                    entry['partner'] = name(support['pid'] or '')
                if drops:
                    entry['drops'] = drops
                group.append(entry)
            if fname in ('Enemy', 'Ally'):
                units += group
            elif group:
                waves.append({'group': fname, 'units': group, **when(fname)})
        result[map_id] = {'units': units, 'starts': starts, 'corrin': corrin, 'waves': waves, 'joins': joins}

    def ts_unit(u, indent):
        f = [f"type: '{u['type']}'", f"name: {json.dumps(u['name'])}", f"tile: [{u['tile'][0]}, {u['tile'][1]}]"]
        if u.get('paired'):
            f.append('paired: true')
            f.append(f"partner: {json.dumps(u['partner'])}")
        if u.get('drops'):
            f.append(f"drops: {json.dumps(u['drops'])}")
        if len(u['difficulties']) < 3:
            f.append('difficulties: [' + ', '.join(f"'{d}'" for d in u['difficulties']) + ']')
        if u.get('generic'):
            f.append('generic: true')
        if 'from' in u and u['from'] != u['tile']:
            f.append(f"from: [{u['from'][0]}, {u['from'][1]}]")
        return ' ' * indent + '{ ' + ', '.join(f) + ' },'

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
        "  /** A boss without a portrait: its name is only its army's (e.g. 'Invader'). */",
        '  generic?: true',
        '}',
        '',
        'export interface GameUnits {',
        '  units: GameUnit[]',
        '  starts: Tile[]',
        '  corrin?: Tile',
        '  /** Reinforcement groups, in the order the game lists them (turns come from the chapter script). */',
        '  waves: ({ group: string; units: GameUnit[] } & Arrival)[]',
        "  /** Units that join mid-chapter: where they walk in from and the tile they stop on. */",
        '  joins: ({ name: string; tile: Tile; from: Tile; group: string } & Arrival)[]',
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
        lines.append('    joins: [')
        for j in r['joins']:
            f = [f"name: {json.dumps(j['name'])}", f"tile: [{j['tile'][0]}, {j['tile'][1]}]", f"from: [{j['from'][0]}, {j['from'][1]}]",
                 f"group: '{j['group']}'"] + ts_when(j)
            lines.append('      { ' + ', '.join(f) + ' },')
        lines.append('    ],')
        lines.append('    waves: [')
        for w in r['waves']:
            extra = ''.join(', ' + x for x in ts_when(w))
            lines.append(f"      {{ group: {json.dumps(w['group'])}{extra}, units: [")
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


if __name__ == '__main__':
    main()

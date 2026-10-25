"""
Builds src/data/maps/fatesJoins.ts from the game's own chapter files: the chapter each character joins your army for good,
on each route (a temporary guest who leaves, like Ryoma in Chapter 6, doesn't count).

The game has no table of who joins when, so it's read from how the chapters use each character, in this order:
  1. a script hands them to you (`UnitTransferByIndex(unit, 0)`, the player's force) or a chapter's Support group places them
     for you to recruit: the earliest such chapter from 6 on;
  2. otherwise the chapter they start appearing in, with the army, for the rest of the game: they're in the Player group or an
     Event group of a run of chapters (one missing chapter is tolerated), and the last such run counts. When that last run is
     only a chapter or two (Revelation places few units after they join), the run before it counts instead;
  3. a recruitable green unit (the Ally group) in the chapter before that run began is the chapter they joined in.
`src/logic/__tests__/fatesSpoiler.test.ts` checks the result against Serenes Forest's recruitment pages for every parent.

Needs the dumped game files in data-raw/fates/romfs/ (git-ignored). Run:
    python scripts/build-fates-joins.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_cmb import Script  # noqa: E402
from fates_dispos import read as read_dispos  # noqa: E402
from fates_maps import MAPS, ROOT, find, find_script, terrain, text_for  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402

OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'fatesJoins.ts')
# The fixed parents of the children's paralogues (the other parent is whoever you marry). Jakob is left out: he joins in 6 or
# only much later depending on Corrin's gender, which no chapter file can say.
PARENTS = ['Azura', 'Silas', 'Kaze', 'Ryoma', 'Takumi', 'Saizo', 'Kaden', 'Hinata', 'Azama', 'Subaki', 'Hayato', 'Xander', 'Leo',
           'Benny', 'Keaton', 'Arthur', 'Odin', 'Laslow', 'Niles']
ROUTES = {'Birthright': 'fe14b', 'Conquest': 'fe14c', 'Revelation': 'fe14r'}
PLAYER = ('Player', 'PlayerM', 'PlayerF')


def chapters(route):
    """The route's chapters in order, as (chapter number, app map id): the five shared ones, then its own, the Endgame as 28."""
    ids = [f'fe14-{n}' for n in range(1, 6)] + [f'{ROUTES[route]}-{n}' for n in range(6, 28)] + [f'{ROUTES[route]}-endgame']
    return [(28 if i.endswith('endgame') else MAPS[i][2], i) for i in ids]


def main():
    text = text_for()

    def name(pid):
        return text.get('M' + pid) or text.get('MPID_' + pid.split('_')[-1])

    result = {}
    for route in ROUTES:
        seen = {}  # chapter -> {'player': names, 'event': names, 'support': names, 'ally': names, 'transfer': names}
        for n, map_id in chapters(route):
            code = MAPS[map_id][0]
            d = seen[n] = {k: set() for k in ('player', 'event', 'support', 'ally', 'transfer')}
            path = find('Dispos', code)
            if path:
                height = read_terrain(terrain(code))['h'] - 2
                for faction in read_dispos(path, height):
                    f = faction['name']
                    kind = 'player' if f in PLAYER else 'event' if f.startswith('Event') else 'support' if f.startswith('Support') else 'ally' if f == 'Ally' else None
                    for u in faction['units'] if kind else []:
                        who = name(u['pid'] or '')
                        if who:
                            d[kind].add(who)
            script = find_script(code)
            s = Script(script) if script else None
            for h in (s.handlers() if s else []):
                try:
                    ins = s.disasm(h)
                except ValueError:
                    continue  # a handler the disassembler can't read (two in the whole game, neither about joining)
                pid = None
                for i, (_, op, arg) in enumerate(ins):
                    if op == 'str' and isinstance(arg, str) and arg.startswith("'PID_"):
                        pid = arg.strip("'")
                    if op == 'call' and arg.startswith('ev::UnitTransferByIndex') and pid and i and ins[i - 1][1] == 'int' and ins[i - 1][2] == 0:
                        who = name(pid)
                        if who:
                            d['transfer'].add(who)
        nums = sorted(seen)
        joins = {}
        for who in PARENTS:
            handed = [c for c in nums if c >= 6 and (who in seen[c]['transfer'] or who in seen[c]['support'])]
            if handed:
                joins[who] = min(handed)
                continue
            present = [c for c in nums if who in seen[c]['player'] or who in seen[c]['event']]
            if not present:
                continue
            runs = [[present[0]]]
            for c in present[1:]:
                runs[-1].append(c) if c - runs[-1][-1] <= 2 else runs.append([c])
            # A character placed in only a chapter or two at the end (Revelation lists few units once they've joined) joined
            # in the run before; a guest who only turns up in the shared chapters and leaves never joined.
            earlier = runs[-2] if len(runs[-1]) < 3 and len(runs) > 1 else None
            run = earlier if earlier and earlier[-1] >= 6 else runs[-1]
            if run[-1] < 6:
                continue
            start = run[0]
            recruited = [c for c in nums if who in seen[c]['ally'] and 6 <= c < start]
            joins[who] = max(recruited) if recruited else start
        result[route] = joins
    lines = [
        '/*',
        " * GENERATED by scripts/build-fates-joins.py from the game's chapter files. Do not edit by hand.",
        ' */',
        '',
        "/** The chapter each character joins your army for good, by route (a temporary guest who leaves doesn't count). */",
        'export const FATES_JOINS: Record<string, Record<string, number>> = ' + json.dumps(result, ensure_ascii=False),
    ]
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, {r: len(v) for r, v in result.items()})


if __name__ == '__main__':
    main()

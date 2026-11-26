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

When a paralogue opens is the program's (0x3d2e6c, run as a chapter ends): each chapter record of GameData.bin (CID_*, 28 bytes)
names the chapter to clear first on each route (+0x0d Birthright, +0x0e Conquest, +0x0f Revelation: that chapter's index, the
record's +0x08) and a fixed parent (+0x10, a person's index, the person record's +0x1c; 0 for none), who must be in your army and
married to someone of the other gender. Every paralogue names Chapter 7 on every route but Midori's, which names Birthright 15;
Mozu's names no parent. The chapters a route goes on from with no My Castle visit are those whose script calls
ev::ChapterSetSkipChapterSaveCastle(1) (Revelation 16, every route's 27), so nothing opens in the castle before the next one.

Needs the dumped game files in data-raw/fates/romfs/ (git-ignored). Run:
    python scripts/build-fates-joins.py
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_cmb import Script  # noqa: E402
from fates_dispos import read as read_dispos  # noqa: E402
from fates_lz import decompress  # noqa: E402
from fates_maps import MAPS, RAW, ROOT, find, find_script, terrain, text_for  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402

OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'fatesJoins.ts')
ROUTES = {'Birthright': 'fe14b', 'Conquest': 'fe14c', 'Revelation': 'fe14r'}
PLAYER = ('Player', 'PlayerM', 'PlayerF')
B = 0x20  # GameData.bin's pointers count from its header's end
CHAPTER, PERSON = 0x1c, 0x98  # record sizes, counted from each record's ID pointer
# The parents whose joins are read here: every paralogue's but Corrin's (always in your army) and Jakob's, who joins in 6 or
# only after Chapter 15 depending on Corrin's gender (castle/castle_join.bin), which no chapter file can say.
NOT_READ = ('Corrin', 'Jakob')


def paralogue_records(text):
    """{paralogue: (the chapter to clear first on each route, the fixed parent's name or None)} from the CID_X records."""
    d = decompress(open(os.path.join(RAW, 'GameData.bin.lz'), 'rb').read())
    u32 = lambda o: struct.unpack_from('<I', d, o)[0]  # noqa: E731

    def s(ptr):
        if not 0 < ptr < len(d) - B:
            return ''
        end = d.find(b'\0', B + ptr)
        try:
            return d[B + ptr:end].decode('shift_jis')
        except UnicodeDecodeError:
            return ''

    def table(prefix, size):
        o = next(o for o in range(B, len(d) - 4, 4) if s(u32(o)).startswith(prefix))
        while s(u32(o)).startswith(prefix):
            yield o
            o += size

    chapters = {o: s(u32(o))[4:] for o in table('CID_', CHAPTER)}
    code_at = {d[o + 8]: code for o, code in chapters.items()}  # +0x08: the chapter's own index
    people = {struct.unpack_from('<H', d, o + 0x1c)[0]: o for o in table('PID_', PERSON)}

    def person(index):
        o = people[index]
        pid = s(u32(o))
        return 'Corrin' if pid.startswith('PID_プレイヤー') else text[s(u32(o + 0x0c))]

    out = {}
    for o, code in chapters.items():
        m = re.fullmatch(r'X(\d{3})', code)
        if not m:
            continue
        assert d[o + 9] == 1, (code, d[o + 9])  # +9: the chapter's kind, 1 a paralogue
        after = {}
        for i, route in enumerate(ROUTES):
            first = code_at[d[o + 0x0d + i]]
            assert re.fullmatch(r'[ABC]\d{3}', first), (code, first)
            after[route] = int(first[1:])
        parent = struct.unpack_from('<H', d, o + 0x10)[0]
        out[int(m.group(1))] = (after, person(parent) if parent else None)
    return dict(sorted(out.items()))


def no_castle_after():
    """{route: [chapters]}: the story chapters whose script calls ev::ChapterSetSkipChapterSaveCastle(1), so the next chapter
    follows with no My Castle visit between (Revelation 16's ending runs Chapter 17's opening at once)."""
    out = {route: [] for route in ROUTES}
    for map_id, (code, route, n) in MAPS.items():
        if route not in ('Shared', *ROUTES):
            continue
        path = find_script(code)
        if not path or b'ChapterSetSkipChapterSaveCastle' not in open(path, 'rb').read():
            continue
        s = Script(path)
        for h in s.handlers():
            try:
                ins = s.disasm(h)
            except ValueError:
                continue
            if any(op == 'call' and str(arg).startswith('ev::ChapterSetSkipChapterSaveCastle') and ins[i - 1][1:] == ('int', 1)
                   for i, (_, op, arg) in enumerate(ins)):
                for r in ROUTES if route == 'Shared' else [route]:
                    if n not in out[r]:
                        out[r].append(n)
    return {r: sorted(chs) for r, chs in out.items()}


def chapters(route):
    """The route's chapters in order, as (chapter number, app map id): the five shared ones, then its own, the Endgame as 28."""
    ids = [f'fe14-{n}' for n in range(1, 6)] + [f'{ROUTES[route]}-{n}' for n in range(6, 28)] + [f'{ROUTES[route]}-endgame']
    return [(28 if i.endswith('endgame') else MAPS[i][2], i) for i in ids]


def main():
    text = text_for()
    paralogues = paralogue_records(text)
    # The fixed parents of the children's paralogues, in the paralogues' order.
    PARENTS = []
    for _, parent in paralogues.values():
        if parent and parent not in NOT_READ and parent not in PARENTS:
            PARENTS.append(parent)

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
    skipped = no_castle_after()
    lines = [
        '/*',
        " * GENERATED by scripts/build-fates-joins.py from the game's chapter files. Do not edit by hand.",
        ' */',
        '',
        "/** The chapter each character joins your army for good, by route (a temporary guest who leaves doesn't count). */",
        'export const FATES_JOINS: Record<string, Record<string, number>> = ' + json.dumps(result, ensure_ascii=False),
        '',
        "/** The story chapter each paralogue's record (GameData.bin, CID_X001-X022, +0x0d to +0x0f) says to clear first on each",
        " * route: Chapter 7, or Birthright 15 for Paralogue 6. It opens once that chapter is cleared (0x3d2e6c). */",
        'export const PARALOGUE_AFTER: Record<number, Record<string, number>> = '
        + json.dumps({n: after for n, (after, _) in paralogues.items()}, ensure_ascii=False),
        '',
        "/** Each child's paralogue's fixed parent (its record's +0x10), who must be in your army and married to someone of the",
        " * other gender for it to open; the child's other parent is whoever they marry. Mozu's (Paralogue 1) names none. */",
        'export const PARALOGUE_PARENT: Record<number, string> = '
        + json.dumps({n: parent for n, (_, parent) in paralogues.items() if parent}, ensure_ascii=False),
        '',
        '/** The story chapters each route goes on from with no My Castle visit (their script calls',
        ' * ev::ChapterSetSkipChapterSaveCastle), so nothing that opens in the castle opens before the next one. */',
        'export const NO_CASTLE_AFTER: Record<string, number[]> = ' + json.dumps(skipped, ensure_ascii=False),
    ]
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, {r: len(v) for r, v in result.items()}, len(paralogues), 'paralogues; no castle after', skipped)


if __name__ == '__main__':
    main()

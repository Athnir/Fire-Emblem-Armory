"""
When each reinforcement / joiner group arrives, from a chapter script: a short sentence per difficulty
plus any map areas whose entry triggers it.

    python scripts/fates_arrivals.py <chapter.cmb> <map height>
"""
from fates_cmb import Script
from fates_schedule import AREA_KIND, DIFFS, GROUP_PREFIXES, PHASES, TURN_KINDS, run

# How many turns are played out. Conquest's Endgame brings its second set of groups in a 48-turn cycle, so a cycle is only seen
# whole this far out.
HORIZON = 99
ANYWHERE = 'a condition in the chapter is met'


def anywhere(args):
    """An area handler covering the whole map whose last argument names a condition function ('IsBoss2Appear'): it runs after
    every action and acts once the function says so, so the area says nothing about when. What the functions check varies too
    much to put in words (both of Anankos's claws defeated, an enemy able to attack): build-fates-units.py words the ones that
    place groups."""
    return len(args) >= 6 and tuple(args[:4]) == (-1, -1, -1, -1) and args[5] not in (0, -1)


def area_item(s, args, height):
    if anywhere(args) and s.string(args[5]):
        return ('text', ANYWHERE)
    return ('area', 'enemy' if args[4] == 1 else 'player', area_rect(args, height))


def area_rect(args, height):
    """A handler's (x1, y1, x2, y2) area in the app's bottom-left coordinates: [left, bottom, right, top]. -1 for both of an
    axis is the whole of it: (-1, 22, -1, 22) is row 22, any column (crossing that line)."""
    x1, y1, x2, y2 = args[:4]
    xs = (-1, -1) if x1 == x2 == -1 else (min(x1, x2), max(x1, x2))
    ys = (-1, -1) if y1 == y2 == -1 else tuple(sorted((height + 1 - y1, height + 1 - y2)))
    return (xs[0], ys[0], xs[1], ys[1])


def flag_reads(ins, lo=0, hi=None):
    """Story flags read (ev::FlagGet) and condition results read (gvar N) in ins[lo:hi]."""
    flags, gvars = [], []
    for k in range(lo, len(ins) if hi is None else hi):
        _, n, a = ins[k]
        if n == 'call' and a.startswith('ev::FlagGet') and k and ins[k - 1][1] == 'str':
            flags.append(ins[k - 1][2].strip("'"))
        if n == 'gvar':
            gvars.append(int(a, 16))
    return flags, gvars


def own_flags(ins):
    return {ins[k - 1][2].strip("'") for k, (_, n, a) in enumerate(ins)
            if n == 'call' and a.startswith('ev::FlagSet') and k and ins[k - 1][1] == 'str'}


# A condition is ('area', 'player' | 'enemy', rect), ('spot', 1 | 9 | 11, (x, y)) for a village, door or Dragon Vein, or ('text', words).
SPOTS = {1: ('village', 'villages', 'visited'), 9: ('door', 'doors', 'opened'), 11: ('Dragon Vein', 'Dragon Veins', 'used')}


def conditions(s, height, terrain=None, label=None):
    """What sets each story flag, and what each condition handler (read back as gvar N) checks. The terrain script's villages,
    doors and Dragon Veins set flags too (Revelation 13's veins bring its reinforcements), and a turn handler that sets a flag after
    placing a group is that group's arrival (`label` names it)."""
    setters, raw_checks, listing = {}, {}, {}
    for h in Script(terrain).handlers() if terrain else []:
        a = h['args']
        if len(a) < 5 or a[4] not in SPOTS:
            continue
        try:
            ins = Script(terrain).disasm(h)
        except (ValueError, IndexError):
            continue
        for f in own_flags(ins):
            item = ('spot', a[4], (a[0], height + 1 - a[1]))
            if item not in setters.setdefault(f, []):
                setters[f].append(item)
    for h in s.handlers():
        try:
            ins = s.disasm(h)
        except (ValueError, IndexError):
            continue
        listing[h['index']] = ins
        calls = {a.split('/')[0] for _, n, a in ins if n == 'call'}
        kind, args = h['kind'] & 0xFF, h['args']
        for k, (_, n, a) in enumerate(ins):
            if n == 'call' and a.startswith('ev::FlagSet') and k and ins[k - 1][1] == 'str':
                flag = ins[k - 1][2].strip("'")
                if kind == AREA_KIND and len(args) >= 5:
                    item = area_item(s, args, height)
                elif 'ev::ForceUnitGetCountArea' in calls:
                    item = ('text', 'enough units gather in a set area')
                elif kind in TURN_KINDS and args and args[0] > 0:
                    placed = [ins[j - 2][2].strip("'") for j in range(2, k) if ins[j][1] == 'call'
                              and ins[j][2].startswith('ev::Dispos/') and ins[j - 2][1] == 'str']
                    named = label(placed[0]) if placed and label else ''
                    item = ('text', f'{named} has arrived' if named.startswith('Group ') else f'turn {args[0]}')
                else:
                    item = None
                if item:
                    setters.setdefault(flag, []).append(item)
        if 'ev::AiGetActive' in calls or 'ev::AiGetDisposX' in calls:
            raw_checks[h['index']] = ('text', 'a set group of enemies starts moving')
        elif 'ev::UnitIsAlive' in calls or 'ev::UnitIsDead' in calls:
            raw_checks[h['index']] = ('text', 'a particular unit is defeated')
        elif 'ev::ForceUnitGetCountArea' in calls:
            raw_checks[h['index']] = ('text', 'enough units gather in a set area')
    # A condition handler may itself read story flags: fold in what sets them.
    checks = {}
    for idx, ins in listing.items():
        flags, _ = flag_reads(ins)
        items = [t for f in flags if f not in own_flags(ins) for t in setters.get(f, [])]
        if idx in raw_checks:
            items.append(raw_checks[idx])
        if items:
            checks[idx] = list(dict.fromkeys(items))
    return setters, checks


def guard_items(s, h, setters, checks, group):
    """The conditions guarding one group's ev::Dispos inside a handler."""
    ins = s.disasm(h)
    at = next((k for k, (_, n, a) in enumerate(ins)
               if n == 'call' and a.startswith('ev::Dispos/') and k >= 2 and ins[k - 2][2] == repr(group)), len(ins))
    # Groups placed one after another with nothing read between them share the first one's checks (Revelation 24's
    # Reinforce05_1_1 to _3).
    dispos = [k for k, (_, n, a) in enumerate(ins[:at]) if n == 'call' and a.startswith('ev::Dispos/')]
    while dispos and flag_reads(ins, dispos[-1] + 1, at) == ([], []) and \
            not any(n in ('jz', 'jnz', 'orjump', 'andjump') for _, n, _ in ins[dispos[-1] + 1:at]):
        at = dispos.pop()
    prev = dispos[-1] if dispos else -1
    own = own_flags(ins)
    for lo in (prev + 1, 0):  # the checks just before this group first, else everything before it
        flags, gvars = flag_reads(ins, lo, at)
        items = [t for f in flags if f not in own for t in setters.get(f, [])]
        items += [t for g in gvars for t in checks.get(g, [])]
        if items:
            return list(dict.fromkeys(items))
    return []


def phrase(items):
    """Conditions -> 'one of your units enters a marked area or a set group of enemies starts moving'."""
    parts = []
    for who in ('player', 'enemy'):
        rects = [i[2] for i in items if i[0] == 'area' and i[1] == who]
        if not rects:
            continue
        subject = 'one of your units' if who == 'player' else 'an enemy'
        tiles = all(r[0] == r[2] and r[1] == r[3] for r in rects)
        if len(rects) == 1 and tiles and rects[0][0] == -1 and rects[0][1] == -1:
            # (-1, -1, -1, -1): anywhere on the map, so the first time one of them acts.
            parts.append(f'{subject} moves' if who == 'player' else 'an enemy moves')
        elif len(rects) == 1 and tiles and rects[0][0] == -1:
            parts.append(f'{subject} reaches row {rects[0][1]}')
        elif len(rects) == 1 and tiles and rects[0][1] == -1:
            parts.append(f'{subject} reaches column {rects[0][0]}')
        elif len(rects) == 1 and tiles:
            parts.append(f'{subject} reaches ({rects[0][0]}, {rects[0][1]})')
        else:
            parts.append(f'{subject} reaches a marked tile' if tiles else f'{subject} enters a marked area')
    for kind, (one, many, verb) in SPOTS.items():
        tiles = [i[2] for i in items if i[0] == 'spot' and i[1] == kind]
        if tiles:
            at = ' or '.join(f'({x}, {y})' for x, y in tiles)
            parts.append(f'the {one} at {at} is {verb}')
    parts += [i[1] for i in items if i[0] == 'text']
    return ' or '.join(dict.fromkeys(parts))


def ordinal(n):
    return {2: '2nd', 3: '3rd'}.get(n, f'{n}th')


def span(ts):
    """'3', '3–5', 'every 2nd turn from turn 2 (2, 4, 6…)'. A step that would carry on past the horizon is a cycle, even one
    seen only twice (every 48th turn)."""
    step = ts[1] - ts[0] if len(ts) > 1 else 0
    if len(ts) >= 2 and ts[-1] + step > HORIZON and all(b - a == step for a, b in zip(ts, ts[1:])):
        return f'every turn from turn {ts[0]}' if step == 1 else \
            f'every {ordinal(step)} turn from turn {ts[0]} ({", ".join(map(str, ts[:3]))}…)'
    runs, a = [], ts[0]
    for prev, t in zip(ts, ts[1:] + [None]):
        if t != prev + 1:
            runs.append(f'{a}' if a == prev else f'{a}–{prev}')
            a = t
    return ', '.join(runs)


def span_text(ts, phase):
    text = span(ts)
    if text.startswith('every'):
        return f'{phase}, {text}'
    return f'turn {text}, {phase}' if len(ts) == 1 else f'turns {text}, {phase}'


def arrivals(path, height, never=None, terrain=None, label=None):
    """{group: {difficulty: {'text': str, 'areas': [{'who': 'player'|'enemy', 'rect': [l, b, r, t]}]}}}. `never`, a set, gets the
    groups only turn handlers name that no turn and difficulty places (half of Conquest's Endgame's second set: the turn
    arithmetic that picks them never lands on them)."""
    s = Script(path)
    out = {}
    setters, checks = conditions(s, height, terrain, label)
    named, placed, blind = {}, set(), set()

    def put(group, dname, text, items=()):
        if group == '?':
            return
        areas = [{'who': i[1], 'rect': list(i[2])} for i in items if i[0] == 'area']
        areas += [{'who': 'player', 'rect': [*i[2], *i[2]]} for i in items if i[0] == 'spot']
        out.setdefault(group, {})[dname] = {'text': text[0].upper() + text[1:], 'areas': areas}

    calls = {}
    for h in s.handlers():
        try:
            calls[h['index']] = {int(a, 16) for _, n, a in s.disasm(h) if n == 'gvar'}
        except (ValueError, IndexError):
            calls[h['index']] = set()
    by_index = {h['index']: h for h in s.handlers()}

    def caller_areas(index, depth=0):
        """The map areas whose handlers run function handler `index`, directly or through one more call."""
        items = []
        for i, called in calls.items():
            if index not in called or i == index:
                continue
            c = by_index[i]
            if c['kind'] & 0xFF == AREA_KIND and len(c['args']) >= 5:
                items.append(area_item(s, c['args'], height))
            elif depth < 1:
                items += caller_areas(i, depth + 1)
        return list(dict.fromkeys(items))

    for h in s.handlers():
        try:
            for _, n, a in s.disasm(h):
                if n == 'str' and a.strip("'").startswith(GROUP_PREFIXES):
                    named.setdefault(a.strip("'"), set()).add(h['index'])
        except (ValueError, IndexError):
            blind.add(h['index'])

    # Every handler that places a group adds to what's said of it: Birthright 10 brings Group 2 on turn 6 from one handler and
    # turn 9 from another, both on Lunatic. Turns a group surely comes on are merged by phase; a conditional arrival keeps its
    # handler's condition; the areas that bring it in are phrased together.
    turn_hits, area_items = {}, {}
    for h in s.handlers():
        kind, args = h['kind'] & 0xFF, h['args']
        if kind in TURN_KINDS and len(args) >= 3:
            first, last, phase = args[:3]
            # -1 = no limit: "from turn 4" is (4, -1); every turn is (-1, -1).
            turns = range(max(first, 1), (last if last > 0 else HORIZON) + 1)
            for di, dname in enumerate(DIFFS):
                for t in turns:
                    for group, cond in run(s, h, di, t):
                        turn_hits.setdefault((group, dname), []).append((h, PHASES.get(phase, 'phase'), t, cond))
                        placed.add(group)
                        if group == '?':
                            blind.add(h['index'])
        elif kind == AREA_KIND and len(args) >= 5:
            item = area_item(s, args, height)
            for di, dname in enumerate(DIFFS):
                for group, cond in run(s, h, di, 1):
                    placed.add(group)
                    if item not in area_items.setdefault((group, dname), []):
                        area_items[(group, dname)].append(item)

    texts = {}
    for (group, dname), hits in turn_hits.items():
        said, items = texts.setdefault((group, dname), ([], []))
        sure = {}
        for h, phase, t, cond in hits:
            if not cond:
                sure.setdefault(phase, set()).add(t)
        for phase, ts in sure.items():
            said.append(span_text(sorted(ts), phase))
        bounded = {}
        for index in dict.fromkeys(x[0]['index'] for x in hits if x[3]):
            h = by_index[index]
            first, last = h['args'][:2]
            phase = PHASES.get(h['args'][2], 'phase')
            maybe = sorted({t for x, _, t, c in hits if x['index'] == index and c})
            try:
                guard = guard_items(s, h, setters, checks, group)
            except (ValueError, IndexError):
                guard = []
            why = phrase(guard) or ANYWHERE
            if last <= 0 and len(maybe) >= HORIZON - 10 - max(first, 1):
                said.append(f'the first {phase} after {why}')
            else:
                bounded.setdefault((phase, why), set()).update(maybe)
            items += [i for i in guard if i not in items]
        for (phase, why), ts in bounded.items():
            said.append(f'{span_text(sorted(ts), phase)}, once {why}')
    for (group, dname), its in area_items.items():
        said, items = texts.setdefault((group, dname), ([], []))
        said.append(f'as soon as {phrase(its)}')
        items += [i for i in its if i not in items]
    for (group, dname), (said, items) in texts.items():
        put(group, dname, '; '.join(dict.fromkeys(said)), items)

    for h in s.handlers():
        kind, args = h['kind'] & 0xFF, h['args']
        if (kind in TURN_KINDS and len(args) >= 3) or (kind == AREA_KIND and len(args) >= 5):
            continue
        # A function handler: some area handlers call it (gvar N runs handler N), e.g. Revelation 7's rooms, each lit up and
        # filled by stepping on its tile.
        items = caller_areas(h['index'])
        for di, dname in enumerate(DIFFS):
            for group, cond in run(s, h, di, 1):
                placed.add(group)
                if dname in out.get(group, {}):
                    continue
                if items:
                    put(group, dname, f'as soon as {phrase(items)}', items)
                else:
                    put(group, dname, 'during a story event')
    if never is not None:
        turn_handlers = {h['index'] for h in s.handlers() if h['kind'] & 0xFF in TURN_KINDS and len(h['args']) >= 3}
        never.update(g for g, hs in named.items() if g not in placed and hs <= turn_handlers and not hs & blind)
    return out


def summons(path):
    """Anankos's summons (Revelation's Endgame, the Heirs of Fate finale): a turn handler reads the 'ステージ' (stage) variable
    and calls a function handler with it, which picks each summon point's group for that stage. {group: [stages]}, from running
    the function once per stage."""
    s = Script(path)
    by_index = {h['index']: h for h in s.handlers()}
    out = {}
    # The stage starts at 1, and each boss form's handler adds 1 (VariableAdd('ステージ', 1)).
    last = 1
    for h in s.handlers():
        try:
            ins = s.disasm(h)
        except (ValueError, IndexError):
            continue
        last += sum(1 for k in range(2, len(ins)) if ins[k][1] == 'call' and ins[k][2].startswith('ev::VariableAdd')
                    and ins[k - 2][2] == "'ステージ'" and ins[k - 1][1:] == ('int', 1))
    for h in s.handlers():
        if h['kind'] & 0xFF not in TURN_KINDS:
            continue
        ins = s.disasm(h)
        for k in range(2, len(ins)):
            if ins[k][1] == 'gvar' and ins[k - 1][1] == 'call' and ins[k - 1][2].startswith('ev::VariableGet') \
                    and ins[k - 2][2] == "'ステージ'" and int(ins[k][2], 16) in by_index:
                f = by_index[int(ins[k][2], 16)]
                for stage in range(1, last + 1):
                    for group, _ in run(s, f, 0, 1, limit=20000, local={0: stage}):
                        if group != '?':
                            out.setdefault(group, set()).add(stage)
    return {g: sorted(v) for g, v in out.items()}


if __name__ == '__main__':
    import sys
    for group, by in arrivals(sys.argv[1], int(sys.argv[2])).items():
        texts = {v['text'] for v in by.values()}
        areas = len(next(iter(by.values()))['areas'])
        print(group, texts.pop() if len(texts) == 1 and len(by) == 3 else {k: v['text'] for k, v in by.items()},
              f'[{areas} areas]' if areas else '')

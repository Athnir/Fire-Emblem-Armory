"""
When each reinforcement / joiner group arrives, from a chapter script: a short sentence per difficulty
plus any map areas whose entry triggers it.

    python scripts/fates_arrivals.py <chapter.cmb> <map height>
"""
from fates_cmb import Script
from fates_schedule import AREA_KIND, DIFFS, PHASES, TURN_KINDS, run


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


# A condition is ('area', 'player' | 'enemy', rect) or ('text', words).
def conditions(s, height):
    """What sets each story flag, and what each condition handler (read back as gvar N) checks."""
    setters, raw_checks, listing = {}, {}, {}
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
                    item = ('area', 'enemy' if args[4] == 1 else 'player', area_rect(args, height))
                elif 'ev::ForceUnitGetCountArea' in calls:
                    item = ('text', 'enough units gather in a set area')
                elif kind in TURN_KINDS and args and args[0] > 0:
                    item = ('text', f'turn {args[0]}')
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
    prev = max((k for k, (_, n, a) in enumerate(ins[:at]) if n == 'call' and a.startswith('ev::Dispos/')), default=-1)
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
    parts += [i[1] for i in items if i[0] == 'text']
    return ' or '.join(dict.fromkeys(parts))


def ordinal(n):
    return {2: '2nd', 3: '3rd'}.get(n, f'{n}th')


def span(ts):
    """'3', '3–5', 'every 2nd turn from turn 2 (2, 4, 6…)'."""
    step = ts[1] - ts[0] if len(ts) > 1 else 0
    if len(ts) >= 3 and ts[-1] + step > 40 and all(b - a == step for a, b in zip(ts, ts[1:])):
        return f'every turn from turn {ts[0]}' if step == 1 else \
            f'every {ordinal(step)} turn from turn {ts[0]} ({ts[0]}, {ts[1]}, {ts[2]}…)'
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


def arrivals(path, height):
    """{group: {difficulty: {'text': str, 'areas': [{'who': 'player'|'enemy', 'rect': [l, b, r, t]}]}}}."""
    s = Script(path)
    out = {}
    setters, checks = conditions(s, height)

    def put(group, dname, text, items=()):
        areas = [{'who': i[1], 'rect': list(i[2])} for i in items if i[0] == 'area']
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
                items.append(('area', 'enemy' if c['args'][4] == 1 else 'player', area_rect(c['args'], height)))
            elif depth < 1:
                items += caller_areas(i, depth + 1)
        return list(dict.fromkeys(items))

    for h in s.handlers():
        kind, args = h['kind'] & 0xFF, h['args']
        if kind in TURN_KINDS and len(args) >= 3:
            first, last, phase = args[:3]
            phase = PHASES.get(phase, 'phase')
            # -1 = no limit: "from turn 4" is (4, -1); every turn is (-1, -1).
            turns = range(max(first, 1), (last if last > 0 else 40) + 1)
            for di, dname in enumerate(DIFFS):
                hits = {}
                for t in turns:
                    for group, cond in run(s, h, di, t):
                        hits.setdefault(group, []).append((t, cond))
                for group, ts in hits.items():
                    sure = sorted({t for t, c in ts if not c})
                    maybe = sorted({t for t, c in ts if c})
                    if not maybe:
                        put(group, dname, span_text(sure, phase))
                        continue
                    try:
                        items = guard_items(s, h, setters, checks, group)
                    except (ValueError, IndexError):
                        items = []
                    why = phrase(items) or 'a condition in the chapter is met'
                    if last <= 0 and len(maybe) >= 30 - max(first, 1):
                        put(group, dname, f'the first {phase} after {why}', items)
                    else:
                        put(group, dname, f'{span_text(maybe, phase)}, once {why}', items)
        elif kind == AREA_KIND and len(args) >= 5:
            item = ('area', 'enemy' if args[4] == 1 else 'player', area_rect(args, height))
            for di, dname in enumerate(DIFFS):
                for group, cond in run(s, h, di, 1):
                    put(group, dname, f'as soon as {phrase([item])}', [item])
        else:
            # A function handler: some area handlers call it (gvar N runs handler N), e.g. Revelation 7's
            # rooms, each lit up and filled by stepping on its tile.
            items = caller_areas(h['index'])
            for di, dname in enumerate(DIFFS):
                for group, cond in run(s, h, di, 1):
                    if dname in out.get(group, {}):
                        continue
                    if items:
                        put(group, dname, f'as soon as {phrase(items)}', items)
                    else:
                        put(group, dname, 'during a story event')
    return out


if __name__ == '__main__':
    import sys
    for group, by in arrivals(sys.argv[1], int(sys.argv[2])).items():
        texts = {v['text'] for v in by.values()}
        areas = len(next(iter(by.values()))['areas'])
        print(group, texts.pop() if len(texts) == 1 and len(by) == 3 else {k: v['text'] for k, v in by.items()},
              f'[{areas} areas]' if areas else '')

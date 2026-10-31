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
# A battle-talk handler: its first PID's side fights the second's (args: PID, side, PID, side, ...).
BATTLE_KIND = 0x18


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


def band_checked(ins):
    """The AI band a condition handler checks (AiGetBand(unit) == N, read with AiGetActive): N, or 'arg' when the handler is a
    function its caller hands the band to (Conquest 18 and 24), or None. It passes once a unit of that band is moving
    (AiGetActive returns at once, opcode 0x55) or none of them is left."""
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::AiGetBand') and k + 1 < len(ins):
            nxt = ins[k + 1]
            if nxt[1] == 'int':
                return nxt[2]
            if nxt[1] == 'var' and int(nxt[2], 16) == 0:
                return 'arg'
    return None


def conditions(s, height, terrain=None, label=None, pid_name=None):
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
                elif kind == BATTLE_KIND and len(args) >= 4 and pid_name:
                    # (PID, side, PID, side): Birthright 18's '主要敵戦闘' is set when the boss, Odin or Niles (side 1, the enemy)
                    # fights anyone ('' on side -1).
                    pids = [s.string(args[0]), s.string(args[2])]
                    foe = pids[0] if args[1] == 1 else pids[1] if args[3] == 1 else None
                    item = ('fight', pid_name(foe)) if foe else None
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
            band = band_checked(ins) if 'ev::AiGetActive' in calls else None
            raw_checks[h['index']] = ('band', band) if band is not None else ('text', 'a set group of enemies starts moving')
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


def terrain_checks(ins, lo, hi, height, tid_name):
    """Tile tests guarding a group, TerrainAttributeIsTID(x, y, 'TID_毒沼配置／床'): the group comes while that tile is still
    that terrain (Birthright 20's foes rise out of acid bogs a Dragon Vein can dry into floor)."""
    out = []
    for k in range(max(lo, 3), hi):
        _, n, a = ins[k]
        if n == 'call' and a.startswith('ev::TerrainAttributeIsTID') and ins[k - 1][1] == 'str' and ins[k - 2][1] == 'int' \
                and ins[k - 3][1] == 'int':
            x, y, tid = ins[k - 3][2], ins[k - 2][2], ins[k - 1][2].strip("'")
            gone = k + 1 < hi and ins[k + 1][1] == '?32'
            out.append(('while', f"the {tid_name(tid)} at ({x}, {height + 1 - y}) {'is gone' if gone else 'remains'}"))
    return out


def count_checks(ins, lo, hi):
    """An army's headcount tested against a number: 'load 00; int 1; call ev::ForceUnitGetCount/1; assign', later 'var 00;
    int 10; lt' (Birthright 14: fewer than 10 foes left), or the call compared at once."""
    words = {0: 'of your units', 1: 'foes', 2: 'green units'}
    held = {}
    for k in range(2, len(ins)):
        if ins[k][1] == 'call' and ins[k][2].startswith('ev::ForceUnitGetCount') and ins[k - 1][1] == 'int' \
                and k + 1 < len(ins) and ins[k + 1][1] == 'assign' and ins[k - 2][1] == 'load':
            held[ins[k - 2][2]] = ins[k - 1][2]
    out = []
    for k in range(max(lo, 1), min(hi, len(ins) - 2)):
        force = None
        if ins[k][1] == 'var' and ins[k][2] in held:
            force = held[ins[k][2]]
        elif ins[k][1] == 'call' and ins[k][2].startswith('ev::ForceUnitGetCount') and ins[k - 1][1] == 'int' \
                and ins[k + 1][1] != 'assign':
            force = ins[k - 1][2]
        if force is None or ins[k + 1][1] != 'int':
            continue
        n, op = ins[k + 1][2], ins[k + 2][1]
        who = words.get(force, 'units')
        text = {'lt': f'fewer than {n} {who} are left', 'le': f'{n} or fewer {who} are left',
                'gt': f'more than {n} {who} are on the map', 'ge': f'{n} or more {who} are on the map'}.get(op)
        if text:
            out.append(('text', text))
    return out


def area_veins(terrain, height):
    """{(x, y) of a terrain-change area, the script's coordinates: the Dragon Vein that changes it, the app's}: each vein's
    handler (args (x, y, w, h, 11, ...)) hands its areas to TrickSetAnyForDragon as a string, '1, 27, 7, 28, 15, 27' (Birthright
    21's lava vein at (12, 3))."""
    out = {}
    t = Script(terrain) if terrain else None
    for h in t.handlers() if t else []:
        a = h['args']
        if len(a) < 5 or a[4] != 11:
            continue
        try:
            ins = t.disasm(h)
        except (ValueError, IndexError):
            continue
        for k in range(1, len(ins)):
            if ins[k][1] == 'call' and ins[k][2].startswith('ev::TrickSetAnyForDragon') and ins[k - 1][1] == 'str':
                nums = [int(n) for n in ins[k - 1][2].strip("'").replace(' ', '').split(',') if n.lstrip('-').isdigit()]
                for x, y in zip(nums[::2], nums[1::2]):
                    out[(x, y)] = (a[0], height + 1 - a[1])
    return out


def function_items(s, args, caller, setters):
    """What a whole-map area handler's condition function waits on, when all it does is read flags ('ev::IsBurn': Birthright
    21's boss has had its battle talk, '戦闘会話'). The caller's own flags are its 'once' guards ('ボス本気')."""
    if not anywhere(args):
        return []
    fn = next((h for h in s.handlers() if h['name'] == 'ev::' + s.string(args[5])), None)
    try:
        ins = s.disasm(fn) if fn else []
        own = own_flags(s.disasm(caller))
    except (ValueError, IndexError):
        return []
    if not ins or any(n == 'call' and not a.startswith('ev::FlagGet') for _, n, a in ins):
        return []
    flags, gvars = flag_reads(ins)
    return [] if gvars else list(dict.fromkeys(t for f in flags if f not in own for t in setters.get(f, [])))


def counter_guard(s, h, ins, at, height, setters=None, veins=None):
    """('counter', start, limits, unless) when the group waits on a counter: read before it ('str C; VariableGet; jz', then
    'var V; eq' against the limit) and counted up after it ('VariableInc'). The limit is V's 'load V; int N; assign', per
    difficulty where a 'DifficultyGet; int D; eq' test precedes one (Paralogue 9: 2, or 5 on Lunatic). The start is C counted
    up in another handler: a fixed turn (an int), or the conditions it waits on (a tuple): a trick tested in its second state
    (a Dragon Vein used, the one tested last before the count), or an area handler's area or condition function. `unless`
    are the Dragon Veins whose use, by then, skips the count: a trick tested with a 'not' whose jump passes it (Birthright 21's
    deadline turns skip an island whose bridge is down, an area its vein changes)."""
    def named(k, fn):
        return ins[k][1] == 'call' and ins[k][2].startswith(fn) and k and ins[k - 1][1] == 'str'
    reads = [ins[k - 1][2].strip("'") for k in range(1, at) if named(k, 'ev::VariableGet')]
    after = {ins[k - 1][2].strip("'") for k in range(at, len(ins)) if named(k, 'ev::VariableInc')}
    c = next((n for n in reversed(reads) if n in after), None)
    if not c:
        return None
    v = next((ins[k + 1][2] for k in range(1, len(ins) - 2) if named(k, 'ev::VariableGet') and ins[k - 1][2] == repr(c)
              and ins[k + 1][1] == 'var' and ins[k + 2][1] == 'eq'), None)
    default, per = None, {}
    for k in range(2, len(ins)):
        if v is not None and ins[k][1] == 'assign' and ins[k - 1][1] == 'int' and ins[k - 2][1] == 'load' and ins[k - 2][2] == v:
            d = next((ins[j + 1][2] for j in range(max(0, k - 9), k - 2) if ins[j][1] == 'call'
                      and ins[j][2].startswith('ev::DifficultyGet') and ins[j + 1][1] == 'int' and ins[j + 2][1] == 'eq'), None)
            if d is None:
                default = ins[k - 1][2]
            else:
                per[d] = ins[k - 1][2]
    if default is None:
        return None
    limits = tuple(per.get(d, default) for d in range(3))
    for h2 in s.handlers():
        if h2['index'] == h['index']:
            continue
        try:
            ins2 = s.disasm(h2)
        except (ValueError, IndexError):
            continue
        for k in range(1, len(ins2)):
            if not (ins2[k][1] == 'call' and ins2[k][2].startswith('ev::VariableInc') and ins2[k - 1][2] == repr(c)):
                continue
            kind2, args2 = h2['kind'] & 0xFF, h2['args']
            tests = [j for j in range(4, k) if ins2[j][1] == 'call' and ins2[j][2].startswith('ev::TrickTst')
                     and all(ins2[j - i][1] == 'int' for i in range(1, 5)) and ins2[j - 1][2] == 2]
            tricks = [('spot', ins2[j - 2][2], (ins2[j - 4][2], height + 1 - ins2[j - 3][2])) for j in tests
                      if ins2[j - 2][2] in SPOTS and ins2[j + 1][1] != '?32']
            unless = []
            for j in tests:
                x, y, kind = ins2[j - 4][2], ins2[j - 3][2], ins2[j - 2][2]
                if ins2[j + 1][1] == '?32' and ins2[j + 2][1] == 'jz' and int(ins2[j + 2][2]) > ins2[k][0]:
                    vein = (x, height + 1 - y) if kind == 11 else (veins or {}).get((x, y))
                    if vein and ('spot', 11, vein) not in unless:
                        unless.append(('spot', 11, vein))
            start = None
            if tricks:
                start = (tricks[-1],)
            elif kind2 == AREA_KIND and len(args2) >= 5:
                start = tuple(function_items(s, args2, h2, setters or {}) or [area_item(s, args2, height)])
            elif kind2 in TURN_KINDS and args2 and args2[0] > 0:
                start = args2[0]
            if start is not None:
                return ('counter', start, limits, tuple(unless))
    return None


def guard_items(s, h, setters, checks, group, height=0, tid_name=None, veins=None):
    """The conditions guarding one group's ev::Dispos inside a handler."""
    ins = s.disasm(h)
    at = next((k for k, (_, n, a) in enumerate(ins)
               if n == 'call' and a.startswith('ev::Dispos/') and k >= 2 and ins[k - 2][2] == repr(group)), None)
    if at is None:
        # Handed by name to a helper that places it (Hidden Truths 2's 'ReinforceU02'; gvar 0f): its name marks the spot,
        # and the groups named before it mark where its own checks begin.
        at = next((k for k, (_, n, a) in enumerate(ins) if n == 'str' and a == repr(group)), len(ins))
        dispos = [k for k in range(at) if ins[k][1] == 'str' and ins[k][2].strip("'").startswith(GROUP_PREFIXES)]
    else:
        dispos = [k for k, (_, n, a) in enumerate(ins[:at]) if n == 'call' and a.startswith('ev::Dispos/')]
    # Groups placed one after another with nothing read between them share the first one's checks (Revelation 24's
    # Reinforce05_1_1 to _3).
    while dispos and flag_reads(ins, dispos[-1] + 1, at) == ([], []) and \
            not any(n in ('jz', 'jnz', 'orjump', 'andjump') for _, n, _ in ins[dispos[-1] + 1:at]):
        at = dispos.pop()
    prev = dispos[-1] if dispos else -1
    own = own_flags(ins)

    def gvar_items(k):
        """What the condition handler called at ins[k] checks; a band check its caller hands the band to ('int 1; gvar 05')
        gets the number pushed before the call."""
        arg = ins[k - 1][2] if k and ins[k - 1][1] == 'int' else None
        return [('band', arg) if t == ('band', 'arg') else t for t in checks.get(int(ins[k][2], 16), [])]

    # A flag the handler sets itself, after its own checks (Conquest 24: band 1 moving, from turn 3, sets '増援条件1'): each
    # FlagSet's block runs from the previous FlagSet. A group guarded by such a flag waits on that block's checks.
    # A block that places a group is that group's 'placed once' flag (Conquest 26's '増援3'), not a condition.
    blocks, start = {}, 0
    for k, (_, n, a) in enumerate(ins):
        if n == 'call' and a.startswith('ev::FlagSet') and k and ins[k - 1][1] == 'str':
            if not any(ins[j][1] == 'call' and ins[j][2].startswith('ev::Dispos/') for j in range(start, k)):
                blocks.setdefault(ins[k - 1][2].strip("'"), []).append((start, k))
            start = k + 1
    inside = {k for spans in blocks.values() for b0, b1 in spans for k in range(b0, b1)}
    last_own = next((ins[k - 1][2].strip("'") for k in range(at - 1, 0, -1) if k not in inside and ins[k][1] == 'call'
                     and ins[k][2].startswith('ev::FlagGet') and ins[k - 1][1] == 'str' and ins[k - 1][2].strip("'") in blocks), None)
    pc_at = ins[at][0] if at < len(ins) else 1 << 30

    def skips(k):
        """Whether the jump after the check at ins[k] goes past the group: a check that guards it, not one of another
        branch (Birthright 21's island time limits decide whether an island resets, not whether its groups come)."""
        j = next((j for j in range(k + 1, min(k + 4, len(ins))) if ins[j][1] in ('jz', 'jnz', 'andjump', 'orjump')), None)
        return j is not None and int(ins[j][2]) > pc_at
    negated, guarding = set(), set()
    for k in range(1, at):
        if ins[k][1] == 'call' and ins[k][2].startswith('ev::FlagGet') and ins[k - 1][1] == 'str' and k + 1 < len(ins)                 and ins[k + 1][1] == '?32':
            negated.add(ins[k - 1][2].strip("'"))
            if skips(k):
                guarding.add(ins[k - 1][2].strip("'"))
    for lo in (prev + 1, 0):  # the checks just before this group first, else everything before it
        flags, _ = flag_reads(ins, lo, at)
        items = [t for f in flags if f not in own and f not in negated for t in setters.get(f, [])]
        items += [('not', t) for f in flags if f not in own and f in guarding for t in setters.get(f, [])]
        items += [t for k in range(lo, at) if k not in inside and ins[k][1] == 'gvar' for t in gvar_items(k)]
        for b0, b1 in blocks.get(last_own, []) if last_own else []:
            got = [t for k in range(b0, b1) if ins[k][1] == 'gvar' for t in gvar_items(k)]
            # 'TurnGet() >= 3' in the block: not before turn 3.
            turn = next((ins[k + 1][2] for k in range(b0, b1 - 2) if ins[k][1] == 'call' and ins[k][2].startswith('ev::TurnGet')
                         and ins[k + 1][1] == 'int' and ins[k + 2][1] == 'ge'), None)
            items += [(t[0], t[1], turn) if t[0] == 'band' and turn else t for t in got]
            # 'DifficultyGet() >= 2' in the block: the flag, and so the group, only on those difficulties (Conquest 24's third
            # set, Lunatic).
            for k in range(b0, b1 - 2):
                if ins[k][1] == 'call' and ins[k][2].startswith('ev::DifficultyGet') and ins[k + 1][1] == 'int':
                    d, op = ins[k + 1][2], ins[k + 2][1]
                    ok = {'ge': lambda x: x >= d, 'gt': lambda x: x > d, 'eq': lambda x: x == d, 'le': lambda x: x <= d,
                          'lt': lambda x: x < d, 'ne': lambda x: x != d}.get(op)
                    if ok:
                        items.append(('diffs', frozenset(x for x in range(3) if ok(x))))
        if tid_name:
            items += terrain_checks(ins, lo, at, height, tid_name)
        items += count_checks(ins, lo, at)
        counter = counter_guard(s, h, ins, at, height, setters, veins)
        if counter:
            return [counter]
        if items:
            # A counter picking one group an enemy phase ('dup; int 2; eq; jnz' before the group): its place in the order.
            nth = next((ins[k + 1][2] for k in range(at - 4, max(0, at - 24) - 1, -1) if ins[k][1] == 'dup' and ins[k + 1][1] == 'int'
                        and ins[k + 2][1] == 'eq' and ins[k + 3][1] == 'jnz'), None)
            return list(dict.fromkeys(items + ([('nth', nth)] if nth else [])))
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
    parts += [BAND_TEXT(i[1]) + (f' (from turn {i[2]})' if len(i) > 2 else '') for i in items if i[0] == 'band']
    foes = list(dict.fromkeys(i[1] for i in items if i[0] == 'fight'))
    if foes:
        parts.append('one of your units fights ' + (foes[0] if len(foes) == 1 else f"{', '.join(foes[:-1])} or {foes[-1]}"))
    parts += [i[1] for i in items if i[0] == 'text']
    return ' or '.join(dict.fromkeys(parts))


def BAND_TEXT(band):
    """Words for an AI band; arrivals() sets the map's own."""
    return 'a set group of enemies starts moving'


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


def arrivals(path, height, never=None, terrain=None, label=None, tid_name=lambda tid: tid, band_text=None, pid_name=None):
    """{group: {difficulty: {'text': str, 'areas': [{'who': 'player'|'enemy', 'rect': [l, b, r, t]}]}}}. `never`, a set, gets the
    groups only turn handlers name that no turn and difficulty places (half of Conquest's Endgame's second set: the turn
    arithmetic that picks them never lands on them)."""
    s = Script(path)
    out = {}
    global BAND_TEXT
    BAND_TEXT = (lambda b: band_text(b) or 'a set group of enemies starts moving') if band_text else \
        (lambda b: 'a set group of enemies starts moving')
    setters, checks = conditions(s, height, terrain, label, pid_name)
    veins = area_veins(terrain, height)
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
                guard = guard_items(s, h, setters, checks, group, height, tid_name, veins)
            except (ValueError, IndexError):
                guard = []
            allowed = next((i[1] for i in guard if i[0] == 'diffs'), None)
            if allowed is not None and DIFFS.index(dname) not in allowed:
                continue  # the flag it waits on is only set on other difficulties
            counter = next((i for i in guard if i[0] == 'counter'), None)
            if counter:
                # Comes on each of its phases while the counter runs: limit - 1 times (Paralogue 9: once, four times on Lunatic).
                _, start, limits, unless = counter
                waves = max(limits[DIFFS.index(dname)] - 1, 1)
                if isinstance(start, int):
                    said.append(span_text(list(range(start, start + waves)), phase)
                                + (f', unless {phrase(list(unless))} before turn {start}' if unless else ''))
                else:
                    many = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six'}.get(waves, str(waves))
                    said.append(f"the first {f'{many} {phase}s' if waves > 1 else phase} after {phrase(list(start))}")
                    items += [i for i in start if i[0] in ('area', 'spot') and i not in items]
                continue
            whiles = [i[1] for i in guard if i[0] == 'while']
            nots = [i[1] for i in guard if i[0] == 'not']
            nth = next((i[1] for i in guard if i[0] == 'nth'), 1)
            why = phrase([i for i in guard if i[0] not in ('while', 'nth', 'diffs', 'not')]) or ('' if whiles or nots else ANYWHERE)
            tail = (f", while {' and '.join(whiles)}" if whiles else '') + (f', before {phrase(nots)}' if nots else '')
            if why and last <= 0 and len(maybe) >= HORIZON - 10 - max(first, 1):
                said.append(f"the {['first', 'second', 'third', 'fourth', 'fifth'][nth - 1] if nth <= 5 else f'{nth}th'} {phase} after {why}{tail}")
            else:
                # A standing condition ('while', 'before') or a bounded run of turns: the turns, then the conditions.
                bounded.setdefault((phase, why, tail), set()).update(maybe)
            items += [i for i in guard if i not in items and i[0] not in ('while', 'nth', 'band', 'diffs', 'not', 'fight')]
        for (phase, why, tail), ts in bounded.items():
            said.append(f"{span_text(sorted(ts), phase)}{f', once {why}' if why else ''}{tail}")
    for (group, dname), its in area_items.items():
        said, items = texts.setdefault((group, dname), ([], []))
        said.append(f'as soon as {phrase(its)}')
        items += [i for i in its if i not in items]
    for (group, dname), (said, items) in texts.items():
        if said:  # nothing said: the group doesn't come on this difficulty
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

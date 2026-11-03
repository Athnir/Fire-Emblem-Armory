"""Play a Fire Emblem Engage battle's script the way the game does, to see what it places, gives and changes
(data-raw/fe17/README.md, "Script events").

The game places a battle's Player, Enemy and Ally groups itself (the program's own names for them), calls the script's Startup (which
registers its events: `EventEntryTurn`, `EventEntryArea`...), then MapOpening. Each event is an inspector holding its function, its
arguments and a condition (`App.MapInspector.IsCondition`: a function's result, a boolean, or the name of a done-flag variable).
`Battle` runs the script's Lua (fe17_lua.py) with the game's functions written here: they keep the units on the map, the script's
variables and the terrain, and log what the script does (`Battle.log`: placements, items given, joins, terrain changes) under
the moment it happened (`Battle.at`).

    b = Battle('M004', difficulty=0)       # 0 Normal, 1 Hard, 2 Maddening
    b.start()                              # places the start, runs Startup and MapOpening
    b.run_turns(30)                        # each turn's phases: the turn events whose conditions hold
    b.fire(event)                          # runs one registered event's function (an area entered, a village visited...)
"""
import functools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe17_data as D  # noqa: E402
from fe17_lua import Function, Lua, LuaError, Table, truthy  # noqa: E402

FORCE_PLAYER, FORCE_ENEMY, FORCE_ALLY = 0, 1, 2
LORD = 'PID_リュール'
AI_ORDERS = {0: 'cause', 1: 'mind', 2: 'attack', 3: 'move'}
# What a condition may read and still be settled by the script alone: its variables, the difficulty, the turn. Such a condition that
# doesn't hold keeps its event from happening now; one that reads more (a unit's tile, how many foes are left) can't be judged here.
DECIDED = {'VariableGet', 'VariableIsExist', 'VariableEntry', 'VariableSet', 'VariableInc', 'DifficultyGet', 'GameModeGet',
           'MapGetTurn', 'MapGetPhase', 'Log'}
START_GROUPS = ('Player', 'Enemy', 'Ally')
DIFF_BIT = (1, 2, 4)             # App.DisposData.Flags: Normal, Hard, Lunatic (Maddening)
MOVE_FLAG_ESCAPE = 2
# Turn-event registrations: (function, first turn, last turn, phase, condition, arguments...); -1 for any turn.
TURN_KINDS = ('EventEntryTurn', 'EventEntryTurnAfter', 'EventEntryTurnEnd')
# Where each kind's condition sits among its arguments (the function is argument 0); the rest after it are passed to the function.
COND_AT = {'EventEntryTurn': 4, 'EventEntryTurnAfter': 4, 'EventEntryTurnEnd': 4, 'EventEntryArea': 6, 'EventEntryVisit': 3,
           'EventEntryTalk': 6, 'EventEntryBattleTalk': 6, 'EventEntryBattleBefore': 6, 'EventEntryBattleAfter': 6,
           'EventEntryDie': 3, 'EventEntryEscape': 4, 'EventEntryFixed': 3, 'EventEntryPickup': 2, 'EventEntryReviveBefore': 3,
           'EventEntryReviveAfter': 3, 'EventEntryEngageAfter': 2, 'EventEntryEngageBefore': 2, 'EventEntryBreakdownEnemy': 3,
           'EventEntryUnitCommandPrepare': 2, 'EventEntryUnitCommandInterrupt': 3}
# Kinds with no condition slot: every argument after the place is the function's.
ARGS_FROM = {'EventEntryTbox': 3, 'EventEntryDestroy': 5, 'EventEntryDoor': 5, 'EventEntryBreakdown': 5, 'EventEntryWaypoint': 3}


@functools.lru_cache(maxsize=None)
def _person_levels():
    return {r['Pid']: int(r['Level'] or 1) for r in D.rows('person')}


def person_level(pid):
    """A person's own level (person.xml), 1 where it has none."""
    return _person_levels().get(pid, 1) or 1


class Unit:
    def __init__(self, row, group, x, z, force):
        self.row, self.group = row, group
        self.pid = row['Pid']
        self.x, self.z, self.force = x, z, force
        self.start = (x, z)
        self.on_map = True
        # Its AI by slot (App.DisposData's AI_* fields), as AiSetSequence leaves it: (routine, its parameters).
        self.ai = {'cause': (row.get('AI_ActionName', ''), row.get('AI_ActionVal', '')),
                   'mind': (row.get('AI_MindName', ''), row.get('AI_MindVal', '')),
                   'attack': (row.get('AI_AttackName', ''), row.get('AI_AttackVal', '')),
                   'move': (row.get('AI_MoveName', ''), row.get('AI_MoveVal', ''))}

    def __repr__(self):
        return f'<{self.pid} {self.group} ({self.x},{self.z}) f{self.force}>'

    def __lt__(self, other):
        return id(self) < id(other)


class Battle:
    def __init__(self, name, difficulty=0, script=None, army_level=None, terrain=None, start_groups=START_GROUPS):
        self.name = name.upper()
        self.d = difficulty
        # A skirmish (dispos <map>e, script <map>_encount) is fought on its map's own terrain, from the groups Player0 and Mob00.
        self.terrain_name = terrain or self.name
        self.start_groups = start_groups
        # The Divine Paralogues' rows each hold for a band of your army's level (LevelMin-LevelMax): the level to place for.
        self.army_level = army_level
        self.groups = {}
        for group, rows in D.dispos(name):
            self.groups.setdefault(group, []).extend(rows)
        self.units = []
        self.vars = {}
        self.events = []
        self.log = []
        self.at = ('setup',)
        self.turn, self.phase = 0, FORCE_PLAYER
        self.terrain = {}
        self.win = {}
        self.actor = self.target = None
        self.active = set()
        self.ai_asked = set()
        self.errors = []
        self.seen = None
        self.lua = Lua()
        self._install()
        self.loaded = set()
        self._include(script or self.name)

    # -- loading -----------------------------------------------------------------------------------------------------------------
    def _include(self, name):
        key = name.lower()
        if key in self.loaded:
            return
        self.loaded.add(key)
        self.lua.run(D.script(key), key)

    def _install(self):
        g = self.lua.globals
        api = {
            'Include': lambda name: self._include(name),
            'Log': None, 'Yield': None, 'Talk': None, 'Dialog': None, 'Movie': None, 'PuppetDemo': None, 'Tutorial': None,
            'SkipIsBlackOut': lambda: True, 'TimeGetDelta': lambda: 1, 'UnitIsAction': lambda: False,
            'EventIsPlayingObject': lambda *a: False,
            'DifficultyGet': lambda: self.d, 'GameModeGet': lambda: 1,
            'MapGetTurn': lambda: self.turn, 'MapGetPhase': lambda: self.phase,
            'VariableEntry': self._var_entry, 'VariableGet': lambda k, *a: self.vars.get(k, 0),
            'VariableSet': lambda k, v=0, *a: self.vars.__setitem__(k, v), 'VariableIsExist': lambda k, *a: k in self.vars,
            'Dispos': self._dispos,
            'UnitIsExist': lambda u: self._unit(u) is not None, 'UnitGetByPID': lambda pid: self._unit(pid),
            'UnitGetByPos': self._unit_on, 'UnitGetPID': lambda u=None, *a: (self._unit(u) or Unit({'Pid': None}, '', 0, 0, 0)).pid,
            'UnitGetForce': lambda u: self._unit(u).force if self._unit(u) else None,
            'UnitGetX': lambda u, *a: self._place(u)[0], 'UnitGetZ': lambda u, *a: self._place(u)[1],
            'UnitSetPos': self._set_pos, 'UnitMovePos': self._move_pos, 'UnitDelete': self._delete,
            'UnitJoin': self._join, 'UnitGetHp': lambda u: 1, 'UnitGetHpStock': lambda u: 0,
            # A unit moved to another army (Chapter 2's opening sends Lumera to the foes' side).
            'UnitTransfer': lambda u, force, *a: self._unit(u) and setattr(self._unit(u), 'force', int(force)),
            'ForceUnitGetFirst': lambda f: self._force_units(f)[0] if self._force_units(f) else None,
            'ForceUnitGetNext': self._force_next,
            'ItemGain': lambda u, iid, *a: self._record('item', iid=iid, unit=self._pid(u)),
            'ItemGainSilent': lambda u, iid, *a: self._record('item', iid=iid, unit=self._pid(u)),
            'GoldGain': lambda *a: self._record('gold', amount=a[-1]),
            'TerrainSet': self._terrain_set, 'TerrainSetOne': self._terrain_set,
            'TerrainGet': lambda x, z: self._terrain_get(x, z),
            'WinRuleSetDestroyBoss': lambda v=True, *a: self.win.__setitem__('boss', truthy(v)),
            'WinRuleSetMID': lambda mid, *a: self.win.__setitem__('mid', (mid, *a)),
            'WinRuleSetLimitTurn': lambda n, *a: self.win.__setitem__('turns', n),
            'WinRuleSetEnemyNumberLessThanOrEqualTo': lambda n, *a: self.win.__setitem__('enemies', n),
            'LoseRuleSetMID': lambda mid, *a: self.win.__setitem__('lose', (mid, *a)),
            # Functions whose values the scripts compute with: a first draw, the person's own ids, middling stats.
            'RandomGet': lambda n=1, *a: 0, 'PersonGetIndex': lambda *a: 0,
            'UnitGetMPID': lambda u, *a: 'MPID_' + str(self._pid(u) or ''),
            'UnitGetJID': lambda u, *a: (self._unit(u).row.get('Jid') if self._unit(u) else None) or '',
            'UnitGetCapability': lambda *a: 10, 'UnitGetEngageCount': lambda *a: 0, 'UnitGetLevel': lambda *a: 1,
            'MapGetPosition': lambda v, *a: v, 'MapGetHeight': lambda *a: 0,
            'SubPrefix': lambda s, *a: str(s).split('_', 1)[-1], 'DisposGetGroupCount': lambda g, *a: len(self.placed(g)),
            'MindGetUnit': lambda: self.actor, 'MindGetEventUnit': lambda: self.actor, 'MindGetTargetUnit': lambda: self.target,
            'UnitCreateGodUnit': None,
            # Whether a unit's AI has started (a foe waiting until your units come near): none has, unless `active` names it.
            'AiGetActive': self._ai_active,
            'AiSetSequence': self._ai_set,
        }
        for k in ['EventEntryTurn', 'EventEntryTurnAfter', 'EventEntryTurnEnd', 'EventEntryArea', 'EventEntryVisit',
                  'EventEntryDestroy', 'EventEntryTbox', 'EventEntryDoor', 'EventEntryTalk', 'EventEntryBattleTalk',
                  'EventEntryDie', 'EventEntryEscape', 'EventEntryFixed', 'EventEntryPickup', 'EventEntryBattleBefore',
                  'EventEntryBattleAfter', 'EventEntryReviveBefore', 'EventEntryReviveAfter', 'EventEntryEngageAfter',
                  'EventEntryEngageBefore', 'EventEntryBreakdown', 'EventEntryBreakdownEnemy', 'EventEntryUnitCommandPrepare',
                  'EventEntryUnitCommandInterrupt', 'EventEntryWaypoint', 'EventEntryCommand', 'EventEntryTargetSelect']:
            api[k] = (lambda kind: lambda *args: self._register(kind, args))(k)
        for k, v in api.items():
            g[k] = self._tracked(k, v if v is not None else (lambda *a: None))
        self.lua.unknown = lambda fexpr, args: self._seen(fexpr[1] if fexpr[0] == 'Name' else '?') or []
        self.overrides = {k: g[k] for k in ('SkipIsBlackOut', 'UnitIsAction', 'EventIsPlayingObject')}

    def _tracked(self, name, f):
        def call(*a):
            self._seen(name)
            return f(*a)
        return call

    def _seen(self, name):
        if self.seen is not None:
            self.seen.add(name)

    def _place(self, u):
        """A unit's tile, noted as read ('pos:<pid>'): a condition that reads it holds where that unit stands."""
        unit = self._unit(u)
        self._seen('pos:' + str(unit.pid if unit else u))
        return (unit.x, unit.z) if unit else (0, 0)

    def _ai_set(self, u, order, name='', val='', *rest):
        # The slot by its number (common.lua's AI_ORDER_CAUSE 0, MIND 1, ATTACK 2, MOVE 3).
        order = AI_ORDERS.get(order, order)
        unit = self._unit(u)
        if unit is not None and order in unit.ai:
            unit.ai = {**unit.ai, order: (name or '', val or '')}
            self._record('ai', unit=unit, order=order, name=name, val=val)
        elif unit is None and isinstance(u, str):
            # For someone not on the map yet (Chapter 4's bandit, who comes on turn 2): noted, so the caller can try later.
            self._record('ai-miss', pid=u)

    def _ai_active(self, u, *a):
        pid = self._pid(u)
        self.ai_asked.add(pid)
        return pid in self.active

    # -- the game's functions ------------------------------------------------------------------------------------------------
    def _record(self, kind, **data):
        self.log.append((self.at, kind, data))

    def _var_entry(self, k, v=0):
        self.vars.setdefault(k, v)

    def _register(self, kind, args):
        self.events.append({'kind': kind, 'args': list(args), 'index': len(self.events), 'runs': 0})

    def _pid(self, u):
        unit = self._unit(u)
        return unit.pid if unit else (u if isinstance(u, str) else None)

    def _unit(self, u):
        if isinstance(u, Unit):
            return u if u.on_map else None
        if isinstance(u, str):
            for unit in self.units:
                if unit.on_map and unit.pid == u:
                    return unit
        return None

    def _unit_on(self, x, z, *a):
        """Who stands on a tile, noted as read ('tile:x,z'): a condition that reads it holds by who is there."""
        self._seen(f'tile:{int(x)},{int(z)}')
        return self._unit_at(x, z)

    def _unit_at(self, x, z):
        for unit in self.units:
            if unit.on_map and unit.x == x and unit.z == z:
                return unit
        return None

    def _force_units(self, force):
        return [u for u in self.units if u.on_map and (force == -1 or u.force == force)]

    def _force_next(self, u):
        units = self._force_units(u.force) if isinstance(u, Unit) else []
        k = units.index(u) if u in units else -1
        return units[k + 1] if 0 <= k < len(units) - 1 else None

    def placed(self, group):
        """A group's rows that this difficulty places (and, on a Divine Paralogue, this army level: a row's band holds the level its
        unit would have, the army level plus its person's level less 1: App.DisposData.CanDispos, App.Unit.CreateDlcGodEnemy)."""
        out = []
        for r in self.groups.get(group, []):
            if not int(r['Flag'] or 0) & DIFF_BIT[self.d]:
                continue
            # 0-0 (the Player and Terrain groups): every level.
            if self.army_level is not None and r.get('LevelMin') not in (None, '', '0'):
                level = self.army_level + person_level(r['Pid']) - 1
                if not int(r['LevelMin']) <= level <= int(r['LevelMax'] or 255):
                    continue
            out.append(r)
        return out

    def _dispos(self, group, flag=0, *rest):
        units = []
        for r in self.placed(group):
            x, z = int(r['DisposX']), int(r['DisposY'])
            u = Unit(r, group, x, z, int(r['Force'] or 0))
            # Where it walks in from; 0, 0 (most rows) is none: it appears on its tile.
            if r['AppearX'] not in ('', '0') or r['AppearY'] not in ('', '0'):
                u.came_from = (int(r['AppearX'] or 0), int(r['AppearY'] or 0))
            self.units.append(u)
            units.append(u)
        self._record('dispos', group=group, units=units)

    def _set_pos(self, u, x, z, *rest):
        unit = self._unit(u)
        if unit:
            unit.x, unit.z = int(x), int(z)
            self._record('move', unit=unit, to=(unit.x, unit.z))

    def _move_pos(self, u, x, z=0, flag=0, *rest):
        unit = self._unit(u)
        if not isinstance(x, (int, float)):
            # Moved to another unit (Chapter 11's Ivy and her retainers walk to Alear): onto its tile, as near as this goes.
            to = self._unit(x)
            x, z, flag = (to.x, to.z, z) if to else (unit.x if unit else 0, unit.z if unit else 0, z)
        if unit:
            unit.x, unit.z = int(x), int(z)
            if int(flag or 0) & MOVE_FLAG_ESCAPE:
                unit.on_map = False
                self._record('leave', unit=unit)
            else:
                self._record('move', unit=unit, to=(unit.x, unit.z))

    def _delete(self, u, *rest):
        unit = self._unit(u)
        if unit:
            unit.on_map = False
            self._record('leave', unit=unit)

    def _join(self, *pids):
        for p in pids:
            unit = self._unit(p)
            if unit:
                unit.force = FORCE_PLAYER
            self._record('join', pid=self._pid(p))

    def _terrain_set(self, x, z, tid, *rest):
        self.terrain[(int(x), int(z))] = tid
        self._record('terrain', tile=(int(x), int(z)), tid=tid)

    def _terrain_get(self, x, z):
        if (x, z) in self.terrain:
            return self.terrain[(x, z)]
        t = D.terrain(self.terrain_name)
        return t['tiles'][int(z) * D.GRID + int(x)]

    # -- running -------------------------------------------------------------------------------------------------------------
    def call(self, f, args=()):
        if isinstance(f, str):
            f = self.lua.globals.get(f)
        if f is None:
            return []
        return self.lua.call_value(f, list(args))

    def start(self):
        """The battle's start: its groups placed, Startup (the events registered) and MapOpening run."""
        self.at = ('start',)
        for g in self.start_groups:
            if g in self.groups:
                self._dispos(g)
        self.call('MapDispos')
        self.call('Startup')
        self.at = ('opening',)
        self.call('MapOpening')

    def condition(self, ev):
        """Whether an event's condition holds now (App.MapInspector.IsCondition)."""
        k = COND_AT.get(ev['kind'])
        if k is None or k >= len(ev['args']):
            return True
        c = ev['args'][k]
        if c is None:
            return True
        if isinstance(c, bool):
            return c
        if isinstance(c, str):
            return self.vars.get(c, 0) != 1
        if isinstance(c, Function) or callable(c):
            r = self.call(c, self.fn_args(ev))
            return bool(r) and truthy(r[0])
        return True

    def condition_reads(self, ev):
        """The game's functions an event's condition calls, as it stands now: none beyond the script's variables, the difficulty and
        the turn means only the script's own events can make it hold."""
        self.seen = set()
        try:
            self.condition(ev)
        except LuaError:
            self.seen.add('?')
        out, self.seen = self.seen, None
        return out

    def where(self, ev, pid):
        """The tiles of the map's window where an event's condition holds with that unit standing there (the script's variables put
        back after each try)."""
        unit = self._unit(pid)
        if unit is None:
            return []
        t = D.terrain(self.terrain_name)
        was, out = (unit.x, unit.z), []
        for z in range(t['z'], t['z'] + t['height']):
            for x in range(t['x'], t['x'] + t['width']):
                unit.x, unit.z = x, z
                kept = dict(self.vars)
                try:
                    ok = self.condition(ev)
                except LuaError:
                    ok = False
                self.vars = kept
                if ok:
                    out.append((x, z))
        unit.x, unit.z = was
        return out

    def holds_with(self, ev, empty=(), mine=()):
        """Whether an event's condition holds with these tiles emptied (their units off the map) or with your units on those (the
        lord first), everything put back after."""
        moved = []
        for x, z in empty:
            u = self._unit_at(x, z)
            if u is not None:
                moved.append((u, u.x, u.z, u.on_map))
                u.on_map = False
        yours = [u for u in self._force_units(FORCE_PLAYER) if u.pid == LORD] + [
            u for u in self._force_units(FORCE_PLAYER) if u.pid != LORD]
        for (x, z), u in zip(mine, yours):
            moved.append((u, u.x, u.z, u.on_map))
            u.x, u.z = x, z
        kept = dict(self.vars)
        try:
            return self.condition(ev)
        except LuaError:
            return False
        finally:
            self.vars = kept
            for u, x, z, on in reversed(moved):
                u.x, u.z, u.on_map = x, z, on

    def fn_args(self, ev):
        k = COND_AT.get(ev['kind'])
        if k is not None:
            return ev['args'][k + 1:]
        return ev['args'][ARGS_FROM.get(ev['kind'], len(ev['args'])):]

    def fire(self, ev, at=None, actor=None, target=None):
        """Run an event's function now (its done-flag, if it has one, set), logging under `at`; `actor` the unit whose act set it off
        (MindGetUnit), `target` the unit it acted on (MindGetTargetUnit: the one talked to)."""
        self.at = at or ('event', ev['index'])
        self.actor, self.target = actor, target
        k = COND_AT.get(ev['kind'])
        if k is not None and k < len(ev['args']) and isinstance(ev['args'][k], str):
            self.vars[ev['args'][k]] = 1
        ev['runs'] += 1
        try:
            self.call(ev['args'][0], self.fn_args(ev))
        finally:
            self.actor = self.target = None

    def happen(self, ev):
        """An event's moment as the game brings it about: the unit that sets it off (where any of your units may, the lord, or the
        first of yours on the map) and the one it acts on (the one talked to, fought or defeated); a defeated unit leaves the map once
        its event has run, and the acting unit's action then ends (each of your units' end-of-action events whose condition holds:
        Chapter 2's first round ends once Lumera falls). An event whose condition reads only the script's own state and doesn't hold
        can't happen now: False."""
        k, a = ev['kind'], ev['args']
        self.seen = set()
        try:
            ok = self.condition(ev)
        finally:
            reads, self.seen = self.seen, None
        if not ok and reads <= DECIDED:
            return False
        mine = self._unit(LORD) or next(iter(self._force_units(FORCE_PLAYER)), None)
        actor = target = None
        if k in ('EventEntryTalk', 'EventEntryBattleTalk', 'EventEntryBattleBefore', 'EventEntryBattleAfter'):
            actor, target = (self._unit(a[1]) if a[1] else mine), self._unit(a[3])
        elif k in ('EventEntryDie', 'EventEntryEscape', 'EventEntryReviveBefore', 'EventEntryReviveAfter'):
            actor = self._unit(a[1]) if a[1] else None
        elif k == 'EventEntryFixed':
            actor = self._unit(a[1]) if a[1] else mine
        else:
            actor = mine
        self.fire(ev, actor=actor, target=target)
        if k == 'EventEntryDie' and a[1]:
            self._delete(a[1])
        if k != 'EventEntryFixed':
            for fx in self.events:
                if fx['kind'] == 'EventEntryFixed' and fx['args'][2] == FORCE_PLAYER and fx is not ev and self.condition(fx):
                    self.fire(fx, at=self.at, actor=self._unit(fx['args'][1]) if fx['args'][1] else mine)
        return True

    def turn_events(self, kind, turn, phase):
        out = []
        for ev in self.events:
            if ev['kind'] != kind:
                continue
            a = ev['args']
            lo, hi, force = a[1], a[2], a[3]
            if force != phase and force != -1:
                continue
            if (lo != -1 and turn < lo) or (hi != -1 and turn > hi):
                continue
            out.append(ev)
        return out

    def run_turns(self, last=30, phases=(FORCE_PLAYER, FORCE_ENEMY, FORCE_ALLY), first=1):
        """Play turns `first` to `last` with nothing else happening: at each phase's start its turn events whose conditions hold,
        then its after-start events, and at its end its end events. Logs under ('turn', turn, phase, kind)."""
        for turn in range(first, last + 1):
            self.turn = turn
            for phase in phases:
                self.phase = phase
                for kind in TURN_KINDS:
                    for ev in self.turn_events(kind, turn, phase):
                        self.at = ('turn', turn, phase, kind)
                        # A turn event that fails on a state this player can't reach (Chapter 25's beam, aimed by a defeated
                        # unit's tile) is noted and passed over, so the turns go on.
                        try:
                            if self.condition(ev):
                                self.fire(ev, self.at)
                        except LuaError as e:
                            self.errors.append((self.at, ev['index'], str(e)))

    def registered(self, kind):
        return [e for e in self.events if e['kind'] == kind]


def battle(name, difficulty=0, army_level=None):
    """A battle with its start played: placed, registered and opened."""
    b = Battle(name, difficulty, army_level=army_level)
    try:
        b.start()
    except LuaError as e:
        raise LuaError(f'{name}: {e}') from e
    return b


__all__ = ['Battle', 'Unit', 'battle', 'FORCE_PLAYER', 'FORCE_ENEMY', 'FORCE_ALLY', 'Table']

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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe17_data as D  # noqa: E402
from fe17_lua import Function, Lua, LuaError, Table, truthy  # noqa: E402

FORCE_PLAYER, FORCE_ENEMY, FORCE_ALLY = 0, 1, 2
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


class Unit:
    def __init__(self, row, group, x, z, force):
        self.row, self.group = row, group
        self.pid = row['Pid']
        self.x, self.z, self.force = x, z, force
        self.start = (x, z)
        self.on_map = True

    def __repr__(self):
        return f'<{self.pid} {self.group} ({self.x},{self.z}) f{self.force}>'

    def __lt__(self, other):
        return id(self) < id(other)


class Battle:
    def __init__(self, name, difficulty=0, script=None, army_level=None):
        self.name = name.upper()
        self.d = difficulty
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
        self.actor = None
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
            'UnitGetByPos': self._unit_at, 'UnitGetPID': lambda u: (self._unit(u) or Unit({'Pid': None}, '', 0, 0, 0)).pid,
            'UnitGetForce': lambda u: self._unit(u).force if self._unit(u) else None,
            'UnitGetX': lambda u: self._unit(u).x if self._unit(u) else 0,
            'UnitGetZ': lambda u: self._unit(u).z if self._unit(u) else 0,
            'UnitSetPos': self._set_pos, 'UnitMovePos': self._move_pos, 'UnitDelete': self._delete,
            'UnitJoin': self._join, 'UnitGetHp': lambda u: 1, 'UnitGetHpStock': lambda u: 0,
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
            'MindGetUnit': lambda: self.actor, 'MindGetEventUnit': lambda: self.actor,
            'UnitCreateGodUnit': None,
        }
        for k in ['EventEntryTurn', 'EventEntryTurnAfter', 'EventEntryTurnEnd', 'EventEntryArea', 'EventEntryVisit',
                  'EventEntryDestroy', 'EventEntryTbox', 'EventEntryDoor', 'EventEntryTalk', 'EventEntryBattleTalk',
                  'EventEntryDie', 'EventEntryEscape', 'EventEntryFixed', 'EventEntryPickup', 'EventEntryBattleBefore',
                  'EventEntryBattleAfter', 'EventEntryReviveBefore', 'EventEntryReviveAfter', 'EventEntryEngageAfter',
                  'EventEntryEngageBefore', 'EventEntryBreakdown', 'EventEntryBreakdownEnemy', 'EventEntryUnitCommandPrepare',
                  'EventEntryUnitCommandInterrupt', 'EventEntryWaypoint', 'EventEntryCommand', 'EventEntryTargetSelect']:
            api[k] = (lambda kind: lambda *args: self._register(kind, args))(k)
        for k, v in api.items():
            g[k] = v if v is not None else (lambda *a: None)
        self.overrides = {k: g[k] for k in ('SkipIsBlackOut', 'UnitIsAction', 'EventIsPlayingObject')}

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
        """A group's rows that this difficulty places (and, on a Divine Paralogue, this army level)."""
        out = []
        for r in self.groups.get(group, []):
            if not int(r['Flag'] or 0) & DIFF_BIT[self.d]:
                continue
            # 0-0 (the Player and Terrain groups): every level.
            if self.army_level is not None and r.get('LevelMin') not in (None, '', '0'):
                if not int(r['LevelMin']) <= self.army_level <= int(r['LevelMax'] or 255):
                    continue
            out.append(r)
        return out

    def _dispos(self, group, flag=0, *rest):
        units = []
        for r in self.placed(group):
            x, z = int(r['DisposX']), int(r['DisposY'])
            u = Unit(r, group, x, z, int(r['Force'] or 0))
            if r['AppearX'] != '' and r['AppearY'] != '':
                u.came_from = (int(r['AppearX']), int(r['AppearY']))
            self.units.append(u)
            units.append(u)
        self._record('dispos', group=group, units=units)

    def _set_pos(self, u, x, z, *rest):
        unit = self._unit(u)
        if unit:
            unit.x, unit.z = int(x), int(z)
            self._record('move', unit=unit, to=(unit.x, unit.z))

    def _move_pos(self, u, x, z, flag=0, *rest):
        unit = self._unit(u)
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
        t = D.terrain(self.name)
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
        for g in START_GROUPS:
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

    def fn_args(self, ev):
        k = COND_AT.get(ev['kind'])
        if k is not None:
            return ev['args'][k + 1:]
        return ev['args'][ARGS_FROM.get(ev['kind'], len(ev['args'])):]

    def fire(self, ev, at=None, actor=None):
        """Run an event's function now (its done-flag, if it has one, set), logging under `at`."""
        self.at = at or ('event', ev['index'])
        self.actor = actor
        k = COND_AT.get(ev['kind'])
        if k is not None and k < len(ev['args']) and isinstance(ev['args'][k], str):
            self.vars[ev['args'][k]] = 1
        ev['runs'] += 1
        try:
            self.call(ev['args'][0], self.fn_args(ev))
        finally:
            self.actor = None

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

    def run_turns(self, last=30, phases=(FORCE_PLAYER, FORCE_ENEMY, FORCE_ALLY)):
        """Play turns 1 to `last` with nothing else happening: at each phase's start its turn events whose conditions hold, then
        its after-start events, and at its end its end events. Logs under ('turn', turn, phase, kind)."""
        for turn in range(1, last + 1):
            self.turn = turn
            for phase in phases:
                self.phase = phase
                for kind in TURN_KINDS:
                    for ev in self.turn_events(kind, turn, phase):
                        self.at = ('turn', turn, phase, kind)
                        if self.condition(ev):
                            self.fire(ev, self.at)

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

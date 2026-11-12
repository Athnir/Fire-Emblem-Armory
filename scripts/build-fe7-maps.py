"""
Builds The Blazing Blade's maps from the user's (U) ROM (scripts/gba_rom.py, scripts/fe7_events.py):
  src/data/fe7/fe7Terrain.ts      terrain stats and movement costs by movement type
  src/data/fe7/fe7Maps.ts         every chapter of Lyn's, Eliwood's and Hector's stories: terrain, units, reinforcements, joiners,
                                  chests, villages, shops
  src/data/fe7/fe7ItemSources.ts  where each item turns up, by chapter (the weapon page and the spoiler block)
Run:
    python scripts/build-fe7-maps.py

What is read where (data-raw/fe7/README.md has the formats):
  - Chapter records, 0x98 bytes at 0xC9A200: the tile config at +7 and the map at +8 are indices into the pointer table at 0xC9C9C8;
    map changes at +0xB; the fog vision at +0xC; +0xD set when the chapter has preparations; the titles in Eliwood's and Hector's
    stories at +0x70 / +0x72 (text ids); the event data at +0x78; the goal at +0x8C.
  - A chapter's start: the opening scene, played for the story and difficulty. A chapter with preparations then clears every unit
    that isn't yours and loads the event data's enemy group for the story and difficulty (0x0803089C, 0x08018980); your army's
    group gives the deploy tiles. Then every turn-1 event on your phase runs. Units end on the tile the scripted moves leave them.
  - Every later turn, talk, area and location event that loads units is a reinforcement, with when it fires.
Chapter titles and goals are the game's own text. The gaiden chapters' conditions are read from the end scripts (each one also asks
"Embark on side quest?"); where a condition is a routine of its own, its wording is Serenes Forest's, checked against the numbers in
the code.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe7_events as fe  # noqa: E402
import gba_ai  # noqa: E402
import gba_bosses  # noqa: E402
import gba_doors  # noqa: E402
import gba_ground  # noqa: E402
import gba_walls  # noqa: E402
import gba_maps as gm  # noqa: E402
from gba_rom import rom  # noqa: E402
from terrain_codes import encode  # noqa: E402

GAME, TITLE, SCRIPT = 'fe7', 'The Blazing Blade', 'build-fe7-maps.py'
r = rom('fe7')
R = r.R
AI = gba_ai.Ai('fe7', R)
NAMES = r.character_names()
CLASSES = r.class_names()
ITEMS = r.item_names()

LYN = list(range(0, 12))
ELIWOOD = [12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 46, 47]
HECTOR = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 44,
          45, 46, 47]
DIFFS = ['Normal', 'Hard']  # Lyn's story is played on Normal only
LORD = {'Lyn': 3, 'Eliwood': 1, 'Hector': 2}
DEFEAT = {'Lyn': 'Lyn is defeated', 'Eliwood': 'Eliwood or Hector is defeated', 'Hector': 'Eliwood or Hector is defeated'}
# The two versions of Chapter 23 (Eliwood) / 24 (Hector) and of 25 / 27: who the story pits you against.
VERSION = {31: 'Lloyd', 32: 'Linus', 35: 'Kenneth', 36: 'Jerme'}

# When the story reaches a chapter that not everyone plays: read from the end scripts' checks before each "go to chapter"; every
# gaiden is also offered with "Embark on side quest?". Where the check is a routine of its own, the wording is Serenes Forest's.
SIDE = ' The game asks "Embark on side quest?" first.'
OPENS = {
    8: 'Opens if Chapter 7 is cleared within 15 turns.' + SIDE,
    16: "Opens if Chapter 13's north-western village is visited (flag 9)." + SIDE,
    21: 'Opens if Chapter {16} is cleared with at least one of the Caelin soldiers alive (at most 2 lost).' + SIDE,
    24: 'Opens if Chapter {18} is cleared within 15 turns.' + SIDE,
    25: "Opens in Hector's story if Nils reached level 7 in Lyn's story and Kishuna is defeated in Chapter 19x." + SIDE,
    30: 'Opens if Chapter {22} is cleared with Hawkeye recruited and alive, and your party gained more than 699 EXP in it.' + SIDE,
    31: "Played when Lyn's, Eliwood's and Hector's levels total 49 or less (Serenes Forest; the game's own check is code).",
    32: "Played when Lyn's, Eliwood's and Hector's levels total 50 or more (Serenes Forest; the game's own check is code).",
    # 0x0807D4C1 totals a measure (0x080A01DC) over two of the game's own lists (0x08CB8984, 0x08CB898E); that it's EXP gained is
    # Serenes Forest's.
    35: 'Played when Erk, Lucius, Renault, Priscilla and Serra have gained at least as much EXP as Guy, Dorcas, Bartre and Raven.',
    36: 'Played when Guy, Dorcas, Bartre and Raven have gained more EXP than Erk, Lucius, Renault, Priscilla and Serra.',
    38: 'Opens if Nino talks to Jaffar in Chapter {26} and both are alive at its end.' + SIDE,
    45: "Opens in Hector's story if Chapter 32 is cleared within 20 turns." + SIDE,
}
# Hector's chapter numbers run one or two ahead of Eliwood's from Chapter 15; the notes name chapters the way the mode does.
NUMBERS = {'Eliwood': {16: '16', 18: '18', 22: '22', 26: '26'}, 'Hector': {16: '17', 18: '19', 22: '23', 26: '28'}}

MOVE_NAMES = {1: 'Lords, heroes & thieves', 10: 'Infantry', 20: 'Armours', 18: 'Fighters', 57: 'Brigands', 58: 'Pirates',
              59: 'Berserkers', 28: 'Mages & priests', 40: 'Cavaliers', 42: 'Paladins', 46: 'Nomads', 48: 'Nomad troopers',
              50: 'Fliers', 70: 'Dragons'}
PHASE = {0x00: 'your phase', 0x40: "the other army's phase", 0x80: 'enemy phase'}
TURN_CONDITION = {1: ('Eliwood', False), 2: ('Hector', False), 3: ('Eliwood', True), 4: ('Hector', True)}
ORDINAL = {2: 'second', 3: 'third', 4: 'fourth'}


def char_record(c):
    return r.character_record(c)


def is_boss(c):
    """The boss flag: bit 0x8000 of the abilities (+0x28), set on each chapter's boss."""
    return bool(r.u32(char_record(c) + 0x28) & 0x8000)


def drops(u):
    """The item a foe drops: its last one, when its character's or class's abilities have 0x08000000 (the unit's state gets 0x1000
    as it's made, 0x08017826; a defeated unit in that state hands its last item over, 0x0802FA22)."""
    a = r.u32(char_record(u['char']) + 0x28) | r.u32(r.cfg['classes'] + 84 * class_of(u) + 0x28)
    return u['items'][-1:] if a & 0x08000000 else []


def has_portrait(c):
    return r.u16(char_record(c) + 6) != 0


_ARMY = None


def personal(c):
    """A character the game names as a person: a name no army shares (gba_bosses.army_names), on a unit with a portrait or a
    boss's (Morva and Fomortiis have none)."""
    global _ARMY
    if _ARMY is None:
        _ARMY = gba_bosses.army_names({x: NAMES.get(x) for x in range(1, 0x100)}, has_portrait)
    return NAMES.get(c) not in _ARMY and (has_portrait(c) or is_boss(c))


def class_of(u):
    return u['class'] or R[char_record(u['char']) + 5]


def item_name(i):
    return ITEMS.get(i, f'item {i:#x}')


def heading_title(text):
    """'Ch. 11: Taking Leave' -> ('Ch.11', 'Taking Leave'); 'Final Chapter: Light' -> ('Final', 'Light')."""
    m = re.match(r'(Ch\. ([0-9]+[x]*)(?: pt 2)?|Prologue|Final Chapter): (.*)', text)
    assert m, text
    head = m.group(1)
    if head.startswith('Ch.'):
        head = 'Ch.' + m.group(2) + (' pt 2' if 'pt 2' in head else '')
    elif head == 'Final Chapter':
        head = 'Final'
    return head, m.group(3).strip()


def map_changes(entry):
    """The chapter's map changes: id -> (x, y, w, h, tiles) from the top-left (scripts/gba_doors.py)."""
    i = R[r.chapter(entry) + 0xB]
    return gba_doors.read_changes(R, r.pointer(i) if i else None)


ROOF = 34


def changes_of(ch):
    """[(event, [change ids])]: what the chapter's scripts change on the map besides its doors, chests and villages closing
    themselves; an end scene's (one that goes to the next chapter) only stages it."""
    out = []
    for e in ch.turns + ch.talks + ch.misc + ch.locations:
        if not r.is_ptr(e['ptr']) or e['type'] in (6, 7, 8, 10) or (5 <= e['type'] <= 10 and e['b'][2] == 0x0E):
            continue
        if Chapter.is_opening(e) or e['ptr'] == ch.ev['opening']:
            continue
        if e['type'] == 2 and not any(condition_ok(e, ch.mode, hard) for hard in (False, True)):
            continue
        if not area_allowed(e, ch.mode) or (e['type'] in (3, 4) and not talk_allowed(e, ch.mode)):
            continue
        try:
            run = fe.Run(ch.world(False, turn=e['b'][0] if e['type'] == 2 else 1)).run(e['ptr'])
        except (AssertionError, RuntimeError, IndexError):
            continue
        if run.next_chapter:
            continue
        at = (e['b'][0], e['b'][1]) if 5 <= e['type'] <= 10 else None
        cids = [c for c in dict.fromkeys(ch.change_ids(run, at)) if c is not None]
        if cids:
            out.append((e, cids))
    return out


def condition_ok(e, mode, hard):
    """A turn event's condition (+0xC) for a mode and difficulty."""
    c = struct_u32(e, 4)
    if c in TURN_CONDITION:
        m, h = TURN_CONDITION[c]
        return m == mode and h == hard
    if c == 5:
        return hard
    return True


def struct_u32(e, i):
    b = e['b']
    return b[i] | b[i + 1] << 8 | b[i + 2] << 16 | b[i + 3] << 24


def turn_conditions(e):
    """The difficulties a turn event fires on, for one mode: None when on all."""
    c = struct_u32(e, 4)
    if c in (3, 4, 5):
        return ['Hard']
    if c in (1, 2):
        return ['Normal']
    return None


class Chapter:
    def __init__(self, entry, mode, height):
        self.entry, self.mode, self.h = entry, mode, height
        self.away = set()
        self.ev = fe.events_of(entry)
        self.turns = fe.event_list(self.ev['turn'])
        self.talks = fe.event_list(self.ev['talk'])
        self.locations = fe.event_list(self.ev['location'])
        self.misc = fe.event_list(self.ev['misc'])
        self.prep = R[r.chapter(entry) + 0xD]
        self.changes = map_changes(entry)
        self.promoted_sides = set()  # the sides of the promoted units the game levels on Hard (hard_notes)

    def leveled(self, u):
        if u.get('autolevel') and u['side'] != 'player' and promoted(u):
            self.promoted_sides.add(u['side'])

    def world(self, hard, **kw):
        return fe.World(mode=self.mode, hard=hard, away=self.away, **kw)

    def opening(self, hard):
        run = fe.Run(self.world(hard))
        run.run(self.ev['opening'])
        if self.prep:
            # Everyone not yours is cleared; the chapter's enemies for the story and difficulty are loaded, and your army deploys on
            # its group's tiles.
            run.units = [u for u in run.units if u['side'] == 'player' and not u['army']]
            run.units = [u for u in run.units if u['char'] not in [a['char'] for a in fe.unit_group(self.army(hard))]]
            slot = fe.group_slot(self.mode, hard)
            run.load(self.ev['enemies'][slot])
            run.load(self.army(hard), army=True)
        for e in self.turns:
            # A chapter without preparations lists its opening scene as a turn-1 event as well; it plays once.
            if self.is_opening(e) and condition_ok(e, self.mode, hard) and r.is_ptr(e['ptr']) and e['ptr'] != self.ev['opening']:
                run.run(e['ptr'])
        return run

    def army(self, hard):
        return self.ev['army'][fe.group_slot(self.mode, hard)]

    def change_ids(self, run, at=None):
        """A run's map changes as ids: by id, by tile, or the event's own (the one at its tile `at`)."""
        out = []
        for kind, v in run.map_changes:
            if kind == 'id':
                out.append(v if v in self.changes else None)
            else:
                xy = v if kind == 'tile' else at
                out.append(gba_doors.change_at(self.changes, xy) if xy else None)
        return out

    @staticmethod
    def is_opening(e):
        b = e['b']
        return e['type'] == 2 and b[0] == 1 and b[2] == 0


def turn_text(e):
    first, last, phase = e['b'][0], e['b'][1], e['b'][2]
    p = PHASE.get(phase, 'any phase')
    if last == 255 or (last > first and e['flag'] == 0 and last - first > 30):
        return f'Every turn from {first}, {p}' if first > 1 else f'Every turn, {p}'
    if last > first and e['flag'] == 0:
        return f'Every turn from {first} to {last}, {p}'
    return f'Turn {first}, {p}'


def talk_pair(e):
    if e['type'] == 3:
        return e['b'][0], e['b'][1]
    if e['type'] == 4:
        return e['b'][0], e['b'][1]
    return None


def talk_allowed(e, mode):
    if e['type'] != 3:
        return True
    c = e['b'][4]
    return c == 0 or c == 3 or (c == 1 and mode == 'Eliwood') or (c == 2 and mode == 'Hector')


def level_text(u, levels=None):
    """'Lv 8 (Hard 17)': the unit's Normal level, with Hard's beside it where that difficulty's own group gives it another."""
    lv = (levels or {}).get('Normal', u['level'])
    hard = (levels or {}).get('Hard', lv)
    return f'Lv {lv}' + (f' (Hard {hard})' if hard != lv else '')


def abilities(u):
    """The character's and the class's abilities (+0x28) together, as the game reads them."""
    return r.u32(char_record(u['char']) + 0x28) | r.u32(r.cfg['classes'] + 84 * class_of(u) + 0x28)


def promoted(u):
    """The promoted bit (0x100) of the abilities, as the game reads it when it levels a unit."""
    return bool(abilities(u) & 0x100)


def unit_entry(u, h, talk=None, levels=None):
    c = u['char']
    cls = CLASSES.get(class_of(u), '?')
    name = NAMES.get(c, '?')
    items = [item_name(i) for i in u['items']]
    if u['side'] == 'enemy':
        kind = 'boss' if is_boss(c) else 'named' if personal(c) else 'enemy'
    else:
        kind = 'ally'
    # A generic boss (The Sacred Stones' boss monsters, 'Monster' by name) goes by its class, as any other generic does.
    named = personal(c) and kind != 'enemy'
    lv = level_text(u, levels)
    out = {'type': kind, 'name': name if named else cls, 'tile': gm.to_app(u['tile'], h), 'note': f'{lv} {cls}' if named else lv}
    if kind == 'boss':
        out['_char'] = c  # which skull stays is settled once the whole map is in (gba_bosses.settle)
    if kind == 'ally' and not named:
        out['generic'] = True
    if items:
        out['carries'] = items
    if u['side'] == 'enemy' and drops(u):
        out['drops'] = [item_name(i) for i in drops(u)]
    if u['side'] == 'enemy':
        out['_take'] = gm.stealable(u['items'], drops(u), lambda i: r.item(i)['type'])
    if talk:
        out['talk'] = talk
    # What its movement AI does (scripts/gba_ai.py), said once the map's villages and chests are in (gba_ai.settle).
    ai = gba_ai.of(AI, u, abilities(u))
    if ai:
        out['_ai'] = ai
    return out


def end_events(ch):
    """[(event, chapter it goes to)]: the chapter's events whose script goes on to a chapter (0x81), as they play by default."""
    if not hasattr(ch, 'ends'):
        ch.ends = []
        for e in ch.turns + ch.talks + ch.misc + ch.locations:
            if r.is_ptr(e['ptr']) and any(c[1] == 0x81 for c in script_cmds(e['ptr'])):
                try:
                    run = fe.Run(ch.world(False, turn=e['b'][0] if e['type'] == 2 else 1)).run(e['ptr'])
                except (AssertionError, RuntimeError, IndexError, KeyError):
                    continue
                if run.next_chapter:
                    ch.ends.append((e, run.next_chapter[-1]))
    return ch.ends


def chapter_name(ch, entry):
    """'Chapter 26x': a chapter of this story by its record."""
    return next((f"Chapter {heading[len('Ch.'):]}" for e, _, mode, _, heading, _ in story() if e == entry and mode == ch.mode),
                f'chapter {entry}')


def talk_effects(ch, e, run):
    """What a talk does besides recruiting: clears the chapter where its script goes on to the chapter the end does (Fargus, 16x),
    or opens another where a flag it sets, its own included, sends an end event there instead (Nino's talk with Jaffar: 26x)."""
    out = []
    ends = end_events(ch)
    if run.next_chapter:
        dest = run.next_chapter[-1]
        out.append('clears the chapter' if dest in {d for _, d in ends} else f'goes on to {chapter_name(ch, dest)}')
    for flag in dict.fromkeys(run.flags_set + ([e['flag']] if e['flag'] else [])):
        for end, dest in ends:
            w = ch.world(False, turn=end['b'][0] if end['type'] == 2 else 1)
            w.flags.add(flag)
            w.away -= set(talk_pair(e))  # both of the talk are there, as an end that asks for them alive wants (26x)
            try:
                other = fe.Run(w).run(end['ptr']).next_chapter
            except (AssertionError, RuntimeError, IndexError, KeyError):
                continue
            if other and other[-1] != dest:
                out.append(f'opens {chapter_name(ch, other[-1])}')
    return list(dict.fromkeys(out))


def talks_of(ch):
    """{name: 'Recruit: talk with Eliwood or Hector'} from the talk events this story allows; a talk that doesn't recruit says what
    else it does ('Talk with Nino (opens Chapter 26x)')."""
    found = {}
    for e in ch.talks:
        pair = talk_pair(e)
        if not pair or not r.is_ptr(e['ptr']) or not talk_allowed(e, ch.mode):
            continue
        a, b = pair
        run = fe.Run(ch.world(False, active=a)).run(e['ptr'])
        t = found.setdefault(NAMES.get(b, '?'), {'recruit': [], 'talk': [], 'gives': [], 'does': []})
        who = NAMES.get(a, '?') if a else 'anyone'
        cmds = fe.script(e['ptr'])
        if b in run.recruits or any(op == 0x65 and (args[0] & 0xFF) == b and args[1] == 0 for _, op, _, args in cmds):
            t['recruit'].append(who)
        else:
            t['talk'].append(who)
            t['gives'] += [item_name(i) for i, _ in run.items]
            t['does'] += talk_effects(ch, e, run)
    out = {}
    for name, t in found.items():
        if t['recruit']:
            out[name] = 'Recruit: talk with ' + ' or '.join(dict.fromkeys(t['recruit']))
        else:
            what = ([f"gives {', '.join(t['gives'])}"] if t['gives'] else []) + list(dict.fromkeys(t['does']))
            out[name] = 'Talk with ' + ' or '.join(dict.fromkeys(t['talk'])) + (f" ({'; '.join(what)})" if what else '')
    return out


def build_units(ch, m, source, diffs):
    h = m['height']
    talks = talks_of(ch)
    for e in ch.talks:
        pair = talk_pair(e)
        if pair and r.is_ptr(e['ptr']) and talk_allowed(e, ch.mode):
            run = fe.Run(ch.world(False, active=pair[0])).run(e['ptr'])
            for i, _ in run.items:
                # A gift a talk hands over mid-battle is yours from the next chapter.
                source(i, m['id'], 'talk-later', f"{NAMES.get(pair[0], '?')} talks to {NAMES.get(pair[1], '?')}")
    runs = {d: ch.opening(d == 'Hard') for d in diffs}
    # What the opening hands over before the battle is yours from this chapter.
    for d, run in runs.items():
        for i, who in run.items:
            source(i, m['id'], 'gift', f"Given to {NAMES.get(who, 'your army')} at the start of the chapter", ds=[d])
    ch.closed = set()
    for cid in ch.change_ids(runs[diffs[0]]):
        if cid is not None:
            x, y, w, hh, _ = ch.changes[cid]
            ch.closed |= {(x + i, y + j) for i in range(w) for j in range(hh)}
    placed = {}
    moved = False
    for d, run in runs.items():
        moved |= spread(run.units, m)
        seen = {}
        for u in run.units:
            # The same unit on both difficulties but for its level (each difficulty's own group can give it another: Lv 8 and
            # Lv 17 in 16x) is one entry that says both.
            key = (u['char'], class_of(u), u['tile'], tuple(u['items']), u['side'], u['army'])
            # Two identical units in one run stay two (a group can walk onto another's tiles: Hector's Chapter 13).
            seen[key] = seen.get(key, 0) + 1
            one = placed.setdefault(key + (seen[key],), (u, [], {}))
            one[1].append(d)
            one[2][d] = u['level']
            if d == 'Hard':
                ch.leveled(u)
    if moved:
        m.setdefault('unconfirmed', []).append(
            "A unit whose tile was taken when it arrived is shown on the nearest free tile; the game picks its own free tile, which "
            "may differ.")
    lord_id = LORD[ch.mode]
    army = [(u, ds) for u, ds, _ in placed.values() if u['army']]
    lord = next((u for u, _, _ in placed.values() if u['char'] == lord_id and u['side'] == 'player'), None)
    if army:
        m['starts'] = [gm.to_app(u['tile'], h) for u, _ in dict(((u['tile'], (u, ds)) for u, ds in army)).values()]
    if lord:
        m['corrinStart'] = gm.to_app(lord['tile'], h)
        if not army:
            m['starts'] = [m['corrinStart']]
    forced = []
    # A unit the opening scene loads as yours joins here, even when it leaves the map before the battle (Athos in the Final
    # Chapter, with the legendary weapons) or the preparations put it on a deployment tile.
    for d, run in runs.items():
        for _, grp, in_army in run.loads:
            for g in grp:
                if g['side'] == 'player' and not in_army:
                    for i in g['items']:
                        source(i, m['id'], 'kit', f"Carried by {NAMES.get(g['char'], '?')} on joining", who=g['char'], ds=[d])
    for u, ds, lv in placed.values():
        if u['army']:
            continue
        if u['side'] == 'player':
            if u['char'] != lord_id and not ch.prep:
                f = {'name': NAMES.get(u['char'], '?'), 'tile': gm.to_app(u['tile'], h)}
                if f not in forced:
                    forced.append(f)
            for i in u['items']:
                source(i, m['id'], 'kit', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'], ds=ds)
            continue
        e = unit_entry(u, h, talks.get(NAMES.get(u['char'], '?')), lv)
        if m['victory'] == f"Defeat {e['name']}" or (e['name'] in m['victory'] and is_boss(u['char'])):
            e['type'] = 'boss'
            e['_char'] = u['char']
        if len(ds) < len(diffs):
            e['difficulties'] = ds
        m['units'].append(e)
        if (e.get('talk') or '').startswith('Recruit'):
            # A foe a talk recruits joins mid-battle: what it carries is yours from the next chapter.
            for i in u['items']:
                source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'], ds=ds)
        elif e['type'] in ('boss', 'named') and u['side'] == 'enemy' and personal(u['char']):
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by {e['name']}", ds=ds)
            for i in u['items']:
                source(i, m['id'], 'foe', f"Carried by {e['name']}, a foe", ds=ds)
        elif u['side'] == 'enemy':
            for i in drops(u):
                source(i, m['id'], 'drop', f"Dropped by a foe {CLASSES.get(class_of(u), '?')}", ds=ds)
            for i in u['items']:
                source(i, m['id'], 'foe-generic', f"Carried by a foe {CLASSES.get(class_of(u), '?')}", ds=ds)
    if forced:
        m['forced'] = forced
    leaves = {}
    for e in ch.turns:
        if Chapter.is_opening(e) or not r.is_ptr(e['ptr']) or e['ptr'] == ch.ev['opening']:
            continue
        cmds = fe.script(e['ptr'])
        if any(op == 0x81 for _, op, _, _ in cmds):
            continue  # the chapter's end clears the map (Vaida as Unfulfilled Heart's 11 turns are up): no one leaves early
        for _, op, _, args in cmds:
            if op in (0x6B, 0x6D, 0x6F):
                leaves.setdefault(NAMES.get(args[0] & 0xFF, '?'), turn_text(e))
    for u in m['units']:
        if u['type'] != 'enemy' and u['name'] in leaves:
            u['note'] = f"{u['note']}; leaves the map: {leaves[u['name']].lower()}"
            u['_leaves'] = True
    build_arrivals(ch, m, source, talks, diffs)


def spread(units, m):
    """Units that end on a tile another unit already holds go to the nearest free tile (by steps, then top to bottom, left to
    right): the game moves them off; which tile it picks isn't simulated. True when any moved."""
    taken, moved = set(), False
    for u in units:
        if u['tile'] in taken and not u['army']:
            x0, y0 = u['tile']
            free = sorted((abs(x - x0) + abs(y - y0), y, x) for x in range(m['width']) for y in range(m['height'])
                          if (x, y) not in taken)
            u['tile'] = (free[0][2], free[0][1])
            moved = True
        taken.add(u['tile'])
    return moved


def area_who(e):
    """Who sets an area event off. The check after each action (0x08079140, run by your units' and the AI's: the procs at
    0x08B93470 and 0x08B96FF8) reads the acting unit's tile alone (0x08078650), so any unit stopping there does, unless the script
    first tests your phase (0x48 on PLAYER_PHASE) and otherwise clears the event's flag to wait for the next: then one of yours."""
    if not r.is_ptr(e['ptr']):
        return 'a unit of any army'
    cmds = fe.script(e['ptr'])
    if cmds and cmds[0][1] == 0x48 and cmds[0][3][1] == fe.PLAYER_PHASE:
        return 'one of your units'
    return 'a unit of any army'


def place(ch, e):
    """'the village at (4, 19)': what a location event's tile is (byte 10: 0x0E a village, a house as type 5; 0x0F seize)."""
    x, y, cmd = e['b'][0] + 1, ch.h - e['b'][1], e['b'][2]
    kind = ('seize point' if cmd == 0x0F else 'door' if e['type'] == 8 else 'chest' if e['type'] == 7 else
            'shop' if e['type'] == 10 else 'house' if e['type'] == 5 else 'village')
    return f'the {kind} at ({x}, {y})'


def visited(ch, e):
    """'Eliwood seizes the seize point at (4, 19)', 'the village at (4, 19) is visited', 'the door at (4, 19) is opened'."""
    if e['b'][2] == 0x0F:
        return f"{NAMES[LORD[ch.mode]]} seizes {place(ch, e)}"
    return f"{place(ch, e)} is {'opened' if e['type'] in (7, 8) else 'visited'}"


def script_cmds(ptr, seen=None):
    """A script's commands with those of the scripts it goes on in or calls (0x58, 0xCB)."""
    seen = seen if seen is not None else set()
    if ptr in seen or not r.is_ptr(ptr):
        return []
    seen.add(ptr)
    out = []
    for c in fe.script(ptr):
        out.append(c)
        if c[1] in (0x58, 0xCB) and r.is_ptr(c[3][0]):
            out += script_cmds(c[3][0], seen)
    return out


def flag_events(ch, flag):
    """The events that set a flag: those whose own flag it is (set as each fires), then those whose script sets it (0x76)."""
    every = ch.turns + ch.talks + ch.locations + ch.misc
    own = [e for e in every if e['flag'] == flag and e['type'] != 1]
    return own + [e for e in every if e not in own and r.is_ptr(e['ptr'])
                  and any(c[1] == 0x76 and c[2] >> 16 == flag for c in script_cmds(e['ptr']))]


def describe_flag(ch, flag):
    for e in flag_events(ch, flag):
        if e['type'] == 2:
            return turn_text(e)
        if e['type'] in (3, 4):
            return f"once {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}"
        if 5 <= e['type'] <= 10:
            return f'once {visited(ch, e)}'
        if e['type'] in (11, 12, 13):
            return f'once {area_who(e)} stops in the marked area'
        if e['type'] == 14:
            what, _ = arrival_of(ch, e)
            if what != 'When an event in the chapter fires':
                return what[0].lower() + what[1:]
    return None


def arrival_of(ch, e):
    t = e['type']
    if t == 2:
        return turn_text(e), None
    if t in (1, 15, 16):
        flag = (e['b'][0] | e['b'][1] << 8) if t == 1 else (e['b'][4] | e['b'][5] << 8)
        # A flag the chapter's areas set as they fire: those areas bring the group (a check on tiles brings its tiles).
        setters = [x for x in flag_events(ch, flag) if x['type'] in (11, 12, 13) and area_allowed(x, ch.mode)]
        if setters:
            areas = [{'who': 'player', 'rect': gm.rect_to_app(tuple(x['b'][:4]), ch.h)} for x in setters]
            where = 'a marked area' if len(setters) > 1 else 'the marked area'
            return f'As soon as {area_who(setters[0])} stops in {where}', areas
        checks = [x for x in flag_events(ch, flag) if x['type'] == 14]
        if checks and arrival_of(ch, checks[0])[1]:
            return arrival_of(ch, checks[0])
        what = describe_flag(ch, flag)
        if what and what.startswith('once '):
            what = 'when ' + what[len('once '):]
        return (what[0].upper() + what[1:] if what else 'After an event in the chapter'), None
    if t in (3, 4):
        return f"When {NAMES.get(e['b'][0], '?')} talks to {NAMES.get(e['b'][1], '?')}", None
    if t in (11, 12, 13):
        x1, y1, x2, y2 = e['b'][:4]
        return f'As soon as {area_who(e)} stops in the marked area', [{'who': 'player', 'rect': gm.rect_to_app((x1, y1, x2, y2), ch.h)}]
    if t in (5, 6):
        return f'When {visited(ch, e)}', None
    if t == 14:
        c = fe.check(r.u32(e["at"] + 8))
        if c == ('no_enemy',):
            return 'Once no enemy is left', None
        if c[0] == 'units_on':
            return ('As soon as one of your units stands on a marked tile',
                    [{'who': 'player', 'rect': gm.rect_to_app((x, y, x, y), ch.h)} for x, y in c[1]])
        return 'When an event in the chapter fires', None
    return 'During the chapter', None


def change_words(ch, e, patch, letters):
    """'Turn 7, your phase: the wall opens.' An area's is named by its tiles."""
    when, areas = arrival_of(ch, e)
    if areas and e['type'] in (11, 12, 13):
        lo, b, hi, t = areas[0]['rect']
        when = f"As soon as {area_who(e)} stops in the area at ({lo}, {b})" + (f"\u2013({hi}, {t})" if (lo, b) != (hi, t) else '')
    what = gba_doors.what_opens([letters[y][x] for (x, y), _ in patch], [c for _, c in patch])
    return f'{when}: {what}.'


def event_marker(e, patch, h):
    """Where an event's change is marked: the changed tile nearest its area, else its middle."""
    tiles = [t for t, _ in patch]
    if e['type'] in (11, 12, 13):
        x1, y1, x2, y2 = e['b'][:4]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    else:
        cx, cy = sum(x for x, _ in tiles) / len(tiles), sum(y for _, y in tiles) / len(tiles)
    return gm.to_app(min(tiles, key=lambda t: ((t[0] - cx) ** 2 + (t[1] - cy) ** 2, t[1], t[0])), h)


def area_allowed(e, mode):
    return e['type'] not in (12, 13) or (e['type'] == 12) == (mode == 'Eliwood')


def vision(ch, values):
    """The fog's vision once a script's 0x9D / 0x9E are done (below 0: the chapter record's own, +0xC); None if it sets none."""
    v = None
    for x in values:
        v = R[r.chapter(ch.entry) + 0xC] if x < 0 else x
    return v


def fog_of(ch, m, diffs):
    """The fog: the record's vision (+0xC), or what the opening sets (Living Legend's on Hector Hard, a turn-1 event); a later turn
    event that sets it brings the fog in or lifts it (Lyn's Chapter 9 on turn 3, Battle before Dawn's on turn 16)."""
    start, sight = {}, {}
    for d in diffs:
        v = vision(ch, ch.opening(d == 'Hard').vision)
        sight[d] = R[r.chapter(ch.entry) + 0xC] if v is None else v
        start[d] = bool(sight[d])
    later = {}
    for e in ch.turns:
        if e['type'] != 2 or Chapter.is_opening(e) or not r.is_ptr(e['ptr']) or e['ptr'] == ch.ev['opening']:
            continue
        for d in diffs:
            if condition_ok(e, ch.mode, d == 'Hard'):
                v = vision(ch, fe.Run(ch.world(d == 'Hard', turn=e['b'][0])).run(e['ptr']).vision)
                if v is not None:
                    when = turn_text(e)
                    when = when[0].lower() + when[1:]
                    later.setdefault(f'Fog of war from {when}.' if v else f'The fog lifts on {when}.', []).append(d)
    if all(start.values()) or (not any(start.values()) and any(n.startswith('Fog of war') for n in later)):
        m['fog'] = True
    elif any(start.values()):
        m['fogOn'] = [d for d in diffs if start[d]]
    # The army's sight where the fog is there at the start (a fog that comes later hides no one at the start).
    if any(start.values()):
        m['vision'] = max(sight.values())
    for note, ds in later.items():
        if len(ds) == len(diffs):
            m['notes'].append(note)
        else:
            m.setdefault('notesOn', []).append({'note': note, 'difficulties': ds})


def hard_notes(ch, m, diffs):
    """Hard's growth the shown level doesn't count. Hector Hard gives every foe the chapter record's +0x14 levels' worth of its
    class's growth (an event's foes as they're placed, 0x0800A6BC; a chapter with preparations' starting foes after them,
    0x080799C8); on Hard in either story, a promoted unit the game levels gets 19 extra levels' worth instead of 9 (0x08017B80,
    0x0803486C). Both raise HP, Str, Skl, Spd, Def and Res (0x08017AC0), not Lck."""
    if 'Hard' not in diffs:
        return
    stats = 'HP, Str, Skl, Spd, Def and Res'
    who = ' or '.join({'enemy': 'foe', 'npc': 'green unit'}[x] for x in ('enemy', 'npc') if x in ch.promoted_sides)
    n = R[r.chapter(ch.entry) + 0x14] if ch.mode == 'Hector' else 0
    if n:
        note = f"On Hard, foes gain {n} levels' worth of their class's growth in {stats}."
        if who:
            note += f" A promoted {who} the game levels also gets 19 extra levels' worth rather than Normal's 9."
        note += ' Their shown level stays the same.'
    elif who:
        note = (f"On Hard, a promoted {who} the game levels gets 19 extra levels' worth of its class's growth in {stats} rather than "
                "Normal's 9; its shown level stays the same.")
    else:
        return
    m.setdefault('notesOn', []).append({'note': note, 'difficulties': ['Hard']})


def build_arrivals(ch, m, source, talks, diffs):
    h = m['height']
    groups, joiners = [], []
    events = [e for e in ch.turns if not Chapter.is_opening(e) and e['ptr'] != ch.ev['opening']]
    # Type 14 fires when a check routine says so (Hector's 32x: its group on Hector Normal and Hard).
    events += [e for e in ch.talks + ch.misc + ch.locations if e['type'] in (1, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16)]
    n = 0
    for e in events:
        if not r.is_ptr(e['ptr']) or not area_allowed(e, ch.mode) or (e['type'] in (3, 4) and not talk_allowed(e, ch.mode)):
            continue
        on = {}
        for d in diffs:
            hard = d == 'Hard'
            if e['type'] == 2 and not condition_ok(e, ch.mode, hard):
                continue
            on[d] = fe.Run(ch.world(hard, turn=e['b'][0] if e['type'] == 2 else 1)).run(e['ptr'])
        if not any(run.loads for run in on.values()):
            continue
        # A script that goes on to the next chapter is the chapter's end: whoever it places is that scene's cast, not a unit on
        # the battle map (Lloyd in both of Linus's chapters, Nergal and Limstella in 29x).
        if all(run.next_chapter for run in on.values()):
            continue
        when, areas = arrival_of(ch, e)
        # One group per difficulty where they differ; one where they're the same.
        by_units = {}
        for d, run in on.items():
            key = tuple((u['char'], class_of(u), u['tile'], u['side']) for u in run.units)
            by_units.setdefault(key, (run, []))[1].append(d)
        for run, ds in by_units.values():
            only = ds if len(ds) < len(diffs) else None
            foes = [u for u in run.units if u['side'] == 'enemy']
            friends = [u for u in run.units if u['side'] != 'enemy']
            # What each unit carries and drops on each of the group's difficulties, as (item, difficulty): the same units can hold
            # other items on another one (Fiora's Axereaver on Hard, Chapter 18), so it's read from each difficulty's own run.
            carried, dropped, levels = {}, {}, {}
            for d in ds:
                for u, v in zip(run.units, on[d].units):
                    carried.setdefault(id(u), []).extend((i, d) for i in v['items'])
                    dropped.setdefault(id(u), []).extend((i, d) for i in drops(v))
                    levels.setdefault(id(u), {})[d] = v['level']
                    if d == 'Hard':
                        ch.leveled(v)
            if foes:
                n += 1
                g = {'id': f'g{n}', 'label': f'Group {n}', 'when': ({d: when for d in only} if only else when),
                     'units': [{**unit_entry(u, h, talks.get(NAMES.get(u['char'], '?')), levels[id(u)]), 'from': gm.to_app(u['start'], h)}
                               for u in foes]}
                if areas:
                    g['areas'] = areas
                if only:
                    for u in g['units']:
                        u['difficulties'] = only
                g['_event'] = e['at']  # one group per arrival (gba_maps.one_per_arrival)
                groups.append(g)
                for u, entry in zip(foes, g['units']):
                    if (entry.get('talk') or '').startswith('Recruit'):
                        for i, d in carried[id(u)]:
                            source(i, m['id'], 'kit-later', f"Carried by {entry['name']} on joining", who=u['char'], ds=[d])
                    elif entry['type'] in ('boss', 'named') and personal(u['char']):
                        for i, d in dropped[id(u)]:
                            source(i, m['id'], 'drop-later', f"Dropped by {entry['name']}, a foe arriving mid-chapter", ds=[d])
                        for i, d in carried[id(u)]:
                            source(i, m['id'], 'foe-later', f"Carried by {entry['name']}, a foe arriving mid-chapter", ds=[d])
                    else:
                        cls = CLASSES.get(class_of(u), '?')
                        for i, d in dropped[id(u)]:
                            source(i, m['id'], 'drop-later', f"Dropped by a foe {cls} arriving mid-chapter", ds=[d])
                        for i, d in carried[id(u)]:
                            source(i, m['id'], 'foe-later-generic', f"Carried by a foe {cls} arriving mid-chapter", ds=[d])
            for u in friends:
                if u['army']:
                    continue
                named = has_portrait(u['char'])
                j = {'name': NAMES.get(u['char'], '?') if named else CLASSES.get(class_of(u), '?'), 'tile': gm.to_app(u['tile'], h),
                     'from': gm.to_app(u['start'], h), 'group': f"e{e['at']:x}", 'when': ({d: when for d in only} if only else when)}
                if areas:
                    j['areas'] = areas
                if u['side'] == 'npc':
                    j['ally'] = True
                    if not named:
                        j['generic'] = True
                    if NAMES.get(u['char']) in talks:
                        j['talk'] = talks[NAMES.get(u['char'])]
                        if j['talk'].startswith('Recruit'):
                            for i, d in carried[id(u)]:
                                source(i, m['id'], 'kit-later', f"Carried by {j['name']} on joining", who=u['char'], ds=[d])
                    ai = gba_ai.of(AI, u, abilities(u))
                    if ai:
                        j['_ai'] = ai
                else:
                    for i, d in carried[id(u)]:
                        source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')} on joining", who=u['char'], ds=[d])
                if j not in joiners:
                    joiners.append(j)
    if groups:
        m['reinforcements'] = gm.one_per_arrival(groups, diffs)
    if joiners:
        m['joiners'] = joiners


def reward_of(ch, ptr):
    """What a village or house gives, from its script: items, gold. Visitors the script tells apart get their own."""
    base = fe.Run(ch.world(False)).run(ptr)
    whos = sorted({args[1] & 0xFF for _, op, w, args in fe.script(ptr) if op == 0x4E})

    def words(run):
        return ', '.join([item_name(i) for i, _ in run.items] + [f'{g} gold' for g in run.gold])

    plain = words(base)
    special = {}
    for c in whos:
        w = words(fe.Run(ch.world(False, active=c)).run(ptr))
        if w != plain:
            special.setdefault(w, []).append(NAMES.get(c, '?'))
    if not special:
        return plain, [i for i, _ in base.items], base
    parts = [f"{w} if visited by {' or '.join(names)}" for w, names in special.items()]
    items = [i for i, _ in base.items] + [i for c in whos for i, _ in fe.Run(ch.world(False, active=c)).run(ptr).items]
    return '; '.join(parts) + (f'; anyone else: {plain}' if plain else ''), items, base


SHOP = {0x13: 'Armory', 0x14: 'Vendor', 0x15: 'Secret shop'}
GOLD_ITEM = 0x76


def build_locations(ch, m, source):
    h = m['height']
    seize, seen = [], set()
    for e in ch.locations:
        x, y, cmd = e['b'][0], e['b'][1], e['b'][2]
        key = (e['type'], x, y, cmd)
        if key in seen:
            continue
        seen.add(key)
        tile = gm.to_app((x, y), h)
        t = e['type']
        if t == 5 and cmd == 0x0F:
            seize.append(tile)
        elif t == 7:
            item, amount = e['ptr'] & 0xFFFF, e['ptr'] >> 16
            if item == GOLD_ITEM:
                contents = f'{amount} gold'
            else:
                contents = item_name(item)
                source(item, m['id'], 'chest', 'In a chest')
            m['objects'].append({'type': 'chest', 'tile': tile, 'contents': contents})
        elif t == 8:
            m['objects'].append({'type': 'door', 'tile': tile})
        elif t == 10 and cmd in SHOP:
            o, stock = r.off(e['ptr']), []
            while r.u16(o):
                stock.append(r.u16(o))
                o += 2
            m['objects'].append({'type': 'shop', 'tile': tile, 'kind': SHOP[cmd], 'stock': [item_name(i) for i in stock]})
            for i in stock:
                source(i, m['id'], 'shop', f"Sold at the {SHOP[cmd].lower()}")
        elif t in (5, 6) and cmd == 0x0E and r.is_ptr(e['ptr']):
            if {(x, y), (x, y - 1)} & getattr(ch, 'closed', set()):
                continue
            reward, items, run = reward_of(ch, e['ptr'])
            joins = [NAMES.get(u['char'], '?') for _, grp, _ in run.loads for u in grp if u['side'] == 'player']
            if t == 5 and not reward and not joins:
                continue
            o = {'type': 'village', 'tile': tile, 'reward': reward}
            notes = ([f"{' and '.join(joins)} {'joins' if len(joins) == 1 else 'join'} your army."] if joins else [])
            if t == 5:
                notes.append('(A house.)')
            if notes:
                o['note'] = ' '.join(notes)
            m['objects'].append(o)
            for i in items:
                source(i, m['id'], 'village', 'Given at a village' if t == 6 else 'Given at a house')
    if seize:
        what = 'the throne' if 'throne' in m['victory'].lower() else 'the gate'
        m['objectives'].append({'type': 'seize', 'tiles': seize, 'label': f"Seize {what} with {NAMES[LORD[ch.mode]]}"})
    # Hidden items: area events whose script gives one.
    for e in ch.misc:
        if e['type'] not in (11, 12, 13) or not r.is_ptr(e['ptr']) or not area_allowed(e, ch.mode):
            continue
        cmds = fe.script(e['ptr'])
        gives = [args[0] & 0xFFFF for _, op, _, args in cmds if op == 0x5B]
        if not gives:
            continue
        area = gm.rect_to_app(tuple(e['b'][:4]), h)
        finders = [NAMES.get(args[1] & 0xFF, '?') for _, op, w, args in cmds if op == 0x4E and w >> 16]
        o = {'type': 'hidden', 'tile': [(area[0] + area[2]) // 2, (area[1] + area[3]) // 2], 'area': area,
             'contents': ', '.join(item_name(i) for i in gives)}
        if finders:
            o['note'] = f"Found only by {' or '.join(finders)}, by stopping in the area."
        m['objects'].append(o)
        for i in gives:
            source(i, m['id'], 'hidden', 'Hidden in the area')
    # The end of the chapter: gifts the end script hands over, and who joins there.
    end = fe.Run(ch.world(False)).run(ch.ev['end'])
    for i, who in end.items:
        source(i, m['id'], 'event-later', f'Given to {NAMES.get(who, "your army")} at the end of the chapter')
    for _, grp, _ in end.loads:
        for u in grp:
            if u['side'] == 'player':
                for i in u['items']:
                    source(i, m['id'], 'kit-later', f"Carried by {NAMES.get(u['char'], '?')}, who joins at the end of the chapter", who=u['char'])


def story():
    """(entry, map id, mode, number, heading, title) for every map, Lyn's story then Eliwood's and Hector's."""
    out = []
    for mode, entries in (('Lyn', LYN), ('Eliwood', ELIWOOD), ('Hector', HECTOR)):
        for entry in entries:
            rec = r.chapter(entry)
            text = r.text(r.u16(rec + (0x72 if mode == 'Hector' else 0x70)))
            head, title = heading_title(text)
            if entry in VERSION:
                title = f'{title} (vs {VERSION[entry]})'
            if entry == 47:
                title = f'{title} (part 2)'
            number = int(re.match(r'Ch\.([0-9]+)', head).group(1)) if head.startswith('Ch.') else (0 if head == 'Prologue' else 33)
            slug = {'Lyn': 'lyn', 'Eliwood': 'e', 'Hector': 'h'}[mode]
            tail = head.replace('Ch.', '').replace(' pt 2', '-2').lower() if head.startswith('Ch.') else head.lower()
            if entry in VERSION:
                tail += '-' + VERSION[entry].lower()
            if entry == 47:
                tail += '-2'
            out.append((entry, f'fe7-{slug}-{tail}', mode, number, head, title))
    return out


def main():
    maps, sources = [], {}
    used_terrain = set()
    # A unit's items count once per story: when it first joins. The openings of chapters without preparations load your units
    # again (the loader reuses the unit already in your army), and that isn't a new copy of what they carry.
    joined = {}        # story -> characters that have joined it in an earlier chapter
    joining = {}       # character -> (kind, words) of their first join in this chapter
    before_split = {}  # story -> who had joined before the first version of a split chapter
    held = {}          # (item, map id, kind, words) -> the difficulties the line holds on
    every = {}         # map id -> the difficulties it's played on

    def source(item, map_id, kind, words, who=None, ds=None):
        """`ds`: the difficulties of the placed unit the line comes from (None: every one the map has, as for anything else)."""
        if who is not None:
            if who in joined[mode]:
                return
            if joining.setdefault(who, (kind, words)) != (kind, words):
                return
        entry = {'mapId': map_id, 'kind': kind, 'text': words}
        lst = sources.setdefault(item_name(item), [])
        if entry not in lst:
            lst.append(entry)
        held.setdefault((item_name(item), map_id, kind, words), set()).update(every[map_id] if ds is None else ds)

    for entry, map_id, mode, number, heading, title in story():
        # The two versions of Chapter 23 (Lloyd, Linus) and of 25 (Kenneth, Jerme) are alternatives: each starts from who had
        # joined before the split, and what follows counts both.
        joined.setdefault(mode, set())
        joining = {}
        other_version = None
        if entry in (31, 35):
            before_split[mode] = set(joined[mode])
        if entry in (32, 36):
            other_version, joined[mode] = joined[mode], set(before_split[mode])
        tiles, terrain_of = r.tiles(entry)
        grid = [[terrain_of(t) for t in row] for row in tiles]
        h, w = len(grid), len(grid[0])
        rec = r.chapter(entry)
        # The map as the battle starts: the opening's map changes made (Hector's 28's doors stand open), then each door and
        # each other script's change previewed; a room under its roof is closed until one opens it.
        ch = Chapter(entry, mode, h)
        # Walls by kind (scripts/gba_walls.py): a map change's tile on its own, the map's with its neighbours.
        tileset = R[rec + 4]
        letter_of = lambda t: gba_walls.letter(GAME, tileset, entry, t, terrain_of(t), gm.GAME_TERRAIN[GAME][terrain_of(t)][0])  # noqa: E731
        opened = [c for c in ch.change_ids(ch.opening(False)) if c is not None]
        gba_doors.apply(ch.changes, grid, terrain_of, opened)
        after = [row[:] for row in tiles]
        gba_doors.apply(ch.changes, after, lambda t: t, opened)
        letters = [[gm.GAME_TERRAIN[GAME][t][0] for t in row] for row in grid]
        gba_walls.theme(GAME, tileset, entry, after, grid, letters)
        doors = {}
        for e in ch.locations:
            if e['type'] == 8:
                cid = gba_doors.change_at(ch.changes, (e['b'][0], e['b'][1]))
                if cid is not None:
                    doors.setdefault((e['b'][0], e['b'][1]), [cid])
        events = changes_of(ch)
        # Cracked walls and snags: the chapter record's wall HP (+0x2C), 20 for a snag.
        broken = gba_doors.breakables(ch.changes, grid, R[r.chapter(entry) + 0x2C])
        cracks = [(('break', xy), [gba_doors.change_at(ch.changes, xy)]) for xy, _, _ in broken]
        previews = gba_doors.previews(ch.changes, letters, letter_of,
                                      list(doors.items()) + [(id(e), c) for e, c in events] + cracks,
                                      lambda xy: grid[xy[1]][xy[0]] == ROOF)
        # A turn's change is made on the map as the turns before left it.
        timed = [(id(e), (e['b'][0], gba_doors.PHASE_ORDER.get(e['b'][2], 3)), c) for e, c in events if e['type'] == 2]
        before = gba_doors.in_turn_order(ch.changes, letters, letter_of, timed, previews)
        for cid in set(opened) | {c for cs in doors.values() for c in cs} | {c for _, cs in events + cracks for c in cs}:
            used_terrain |= {terrain_of(t) for t in ch.changes[cid][4] if t}
        for row in grid:
            used_terrain |= set(row)
        unknown = {t for row in grid for t in row} - set(gm.TERRAIN)
        assert not unknown, (map_id, unknown)
        diffs = ['Normal'] if mode == 'Lyn' else DIFFS
        every[map_id] = diffs
        m = {
            'id': map_id, 'route': mode, 'chapter': number, 'heading': heading, 'title': title, 'width': w, 'height': h,
            'grid': [''.join(encode(GAME, c) for c in row) for row in letters],
            # Its ground's and water's own colours, from its art.
            'fills': gba_ground.fills(gba_ground.art(R, r.lz77, r.pointer, rec, 4), tiles, terrain_of,
                                      lambda t: encode(GAME, gm.GAME_TERRAIN[GAME][t][0]) if t in gm.GAME_TERRAIN[GAME] else None),
            'victory': r.text(r.u16(rec + 0x8C)), 'defeat': DEFEAT[mode], 'objectives': [], 'units': [], 'starts': [], 'objects': [],
            'changes': [], 'notes': [], 'lord': NAMES[LORD[mode]],
            **({'difficulties': diffs} if mode == 'Lyn' else {}),
        }
        if entry in OPENS:
            note = OPENS[entry]
            for k, v in NUMBERS.get(mode, NUMBERS['Eliwood']).items():
                note = note.replace('{%d}' % k, v)
            m['notes'].append(note)
        for door in doors:
            patch = previews[door]
            others = [t for t, _ in patch if t != door and letters[t[1]][t[0]] == 'd']
            m['changes'].append(gba_doors.door_change(gm.to_app(door, h), [(gm.to_app(t, h), encode(GAME, c)) for t, c in patch],
                                                      [gm.to_app(t, h) for t in others]))
        for xy, hp, kind in broken:
            patch = previews[('break', xy)]
            if patch:
                m['changes'].append(gba_doors.breakable_change(gm.to_app(xy, h), hp, kind,
                                                               [(gm.to_app(t, h), encode(GAME, c)) for t, c in patch]))
        closings = {}
        for e, _ in events:
            patch = previews[id(e)]
            # A script that only closes a village says so in the village's note (a turn's), not as a change.
            if gba_doors.only_closes_villages(before.get(id(e), letters), patch):
                if e['type'] == 2:
                    closings.update({tuple(gm.to_app(t, h)): turn_text(e) for t, _ in patch})
                continue
            if patch:
                m['changes'].append(gba_doors.event_change(event_marker(e, patch, h),
                                                           [(gm.to_app(t, h), encode(GAME, c)) for t, c in patch],
                                                           change_words(ch, e, patch, before.get(id(e), letters)),
                                                           e['b'][0] if id(e) in before else None))
        gba_doors.unique_ids(m['changes'])
        # Who isn't in your army yet: everyone (your characters are ids below 0x40) but those who joined the story before.
        ch.away = set(range(1, 0x40)) - joined[mode]
        build_units(ch, m, source, diffs)
        build_locations(ch, m, source)
        fog_of(ch, m, diffs)
        hard_notes(ch, m, diffs)
        # The traps: ballistae, fire tiles and gas vents (Hector's story has its own list).
        traps = gm.trap_objects(gm.trap_records(r, ch.ev['traps_hector'] if mode == 'Hector' else ch.ev['traps']), h, item_name)
        m['objects'] += traps
        if gm.trap_unconfirmed(traps):
            m.setdefault('unconfirmed', []).append(gm.trap_unconfirmed(traps))
        # Only the chapter's own boss keeps the skull: one who leaves the map, or whose death doesn't set the boss's flag here
        # (Kishuna arriving in Aion's chapter), is a named foe.
        gba_bosses.settle(m, gba_bosses.boss_down('fe7', R, entry), lambda c: not personal(c))
        # Looters and the units that leave the map, with the exits they head for.
        gba_ai.settle(m, AI, entry, lambda xy: gm.to_app(xy, h))
        gba_doors.note_closings(m, closings)
        loaded = {g['char'] for d in (False, True) for _, grp, in_army in ch.opening(d).loads if not in_army for g in grp
                  if g['side'] == 'player'}
        joined[mode] |= set(joining) | loaded | (other_version or set())
        maps.append(m)
        print(map_id, title, f'{w}x{h}', len(m['units']), 'units', len(m.get('reinforcements', [])), 'groups')

    groups = gm.move_groups(r, MOVE_NAMES)
    assert gm.flier_rows_are_zero(r, 50)
    info = gm.terrain_table(r, GAME, used_terrain, groups)
    gm.add_closed_rooms(info, GAME, maps, groups)
    gm.write_terrain(GAME, TITLE, SCRIPT, info, groups, CLASSES)
    gm.mark_walled_in(maps, info)
    # What a thief can take from each foe that nothing sells (gba_maps.mark_steals).
    gm.mark_steals(maps, item_name, lambda i: R[r.cfg['items'] + 36 * i + gm.USE_EFFECT], GAME)
    gm.write_maps(GAME, TITLE, SCRIPT, maps)
    gm.mark_difficulties(sources, held, every)
    gm.write_sources(GAME, TITLE, SCRIPT, sources, diffs=DIFFS)


if __name__ == '__main__':
    main()

"""
Builds src/data/fe4/fe4Terrain.ts and src/data/fe4/fe4Maps.ts: Genealogy of the Holy War's chapter maps and terrain, read from the
user's own ROM (scripts/fe4_rom.py), with the game's own decompression routine run by scripts/fe4_cpu.py.

How the ROM keeps a chapter (found by tracing a chapter load in Mesen; details in data-raw/fe4/README.md):
  - a table of twelve 3-byte pointers at $88:9FC3 (Prologue, Chapters 1-10, the Final Chapter) leads to 27-byte chapter records;
  - a record holds the compressed map (a 64 x 64 grid of u16: the low 10 bits are a metatile, 16 x 16 pixels), the compressed
    metatile graphics, and the compressed terrain table (one byte per metatile: the terrain id);
  - byte 21 of the record is the width and byte 23 the height, each in units of 16 tiles (the Prologue is 64 x 32, the rest 64 x 64);
  - the terrain id indexes the movement cost table (15 movement types x 26 ids, $03:987D) and the avoid table ($03:9A25).

English chapter and class names come from Serenes Forest (the ROM's are Japanese). Needs a network connection. Run:
    python scripts/build-fe4-maps.py
"""
import html
import json
import os
import re
import sys
import urllib.request

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe4_cpu import Cpu, rom_offset  # noqa: E402
from fe4_rom import R, item as rom_item, u16  # noqa: E402
from terrain_codes import encode_row  # noqa: E402
import fe4_events as ev  # noqa: E402
import fe4_names as ln  # noqa: E402

import importlib.util  # noqa: E402


def _items():
    spec = importlib.util.spec_from_file_location('build_fe4_items', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-fe4-items.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src', 'data', 'fe4')

CHAPTER_TABLE = 0x89FC3   # 12 x 3-byte SNES pointers to the chapter records
CLASSES = 0x38FCD         # 31 bytes each, 72 entries
MOVE_COSTS = 0x3987D      # u16 offsets from here: one row of 26 terrain ids per movement type
AVOID = 0x39A25           # one signed byte per terrain id
CHAPTERS = [
    ('fe4-prologue', 0, 'Prologue', 'Birth of the Holy Knight'),
    ('fe4-1', 1, 'Ch.1', 'Girl of the Spirit Forest'),
    ('fe4-2', 2, 'Ch.2', 'Disturbance in Agustria'),
    ('fe4-3', 3, 'Ch.3', 'Lion King Eltshan'),
    ('fe4-4', 4, 'Ch.4', 'Dance in the Skies'),
    ('fe4-5', 5, 'Ch.5', 'Doors of Destiny'),
    ('fe4-6', 6, 'Ch.6', 'Inheritors'),
    ('fe4-7', 7, 'Ch.7', 'Passing the Desert'),
    ('fe4-8', 8, 'Ch.8', 'Dragon Knights of Thracia'),
    ('fe4-9', 9, 'Ch.9', 'For Whose Sake'),
    ('fe4-10', 10, 'Ch.10', 'Light and Dark'),
    ('fe4-final', 11, 'Final', 'The Last Holy War'),
]

# Terrain id -> (the builder's letter, the name Serenes Forest gives it). Ids the maps never use (10, 11, 16, 17, 19-21, 23) are
# left out; the build stops if one turns up.
TERRAIN = {
    0: ('C', 'Peak'), 1: ('D', 'Deep forest'), 2: ('C', 'Cliff'), 3: ('.', 'Plain'), 4: ('f', 'Forest'), 5: ('a', 'Sea'),
    6: ('w', 'River'), 7: ('m', 'Mountain'), 8: ('s', 'Desert'), 9: ('N', 'Castle'), 12: ('g', 'Castle gate'),
    13: ('#', 'Castle wall'), 14: ('y', 'Sand'), 15: ('b', 'Bridge'), 18: ('v', 'Village'), 22: ('h', 'Church'),
    24: ('T', 'Tower'), 25: ('R', 'Road'),
}
# The movement types that have identical costs everywhere share one column on the page. (type numbers, the page's name)
MOVE_GROUPS = [
    ((0,), 'Knights'), ((1,), 'Promoted knights'), ((2,), 'Fliers'), ((3,), 'Swordfighters & archers'), ((4,), 'Armours'),
    ((5, 9), 'Soldiers & lords'), ((6,), 'Axe fighters'), ((7,), 'Barbarians & hunters'), ((8,), 'Pirates'),
    ((10, 14), 'Mages & priests'), ((11, 12), 'Thieves & civilians'),
]
SERENES = 'https://serenesforest.net/genealogy-of-the-holy-war/classes/base-stats/'
UNIT_LISTS = 0x1C000      # 57 u16 offsets (from here) to lists of 8-byte unit records, each ended by 0xFFFF
CHARACTERS = 0x38000 + 0x2DF5   # u16 count*2, then u16 offsets (from here) to each character's record, id 1 upward
# The lists each chapter's opening loads, as the game was seen loading them (python scripts/fe4_mesen.py lists 0 11): the build checks
# that reading the opening scripts gives the same. A chapter owns its opening lists and every list up to the next chapter's first one.
OPENING_LISTS = {0: [0], 1: [7, 2], 2: [8], 3: [13], 4: [18], 5: [24], 6: [30, 31], 7: [33, 34], 8: [37, 38], 9: [41, 42], 10: [46, 47], 11: [50]}
BOSS_PAGES = ['boss-data', 'npc-data']


def serenes_classes():
    """Serenes' class table: [(name, hp, str, mag, skl, spd, def, mdf, mov)] in its order."""
    req = urllib.request.Request(SERENES, headers={'User-Agent': 'Mozilla/5.0'})
    page = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    rows = []
    for r in re.findall(r'<tr.*?</tr>', page, flags=re.S):
        c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
        if len(c) == 10 and c[0] != 'Class':
            rows.append((c[0].rstrip(' *'), *[int(x) for x in c[1:9]]))
    return rows


SERENES_CLASSES = {}   # Serenes' class names by class id: its boss tables name classes this way


def class_names():
    """ROM class index -> English name, from Lil' Nordion's class table. Serenes' class table is in the ROM's order, Free Knight
    included, and is used to check the stats: the ROM keeps each class's
    base stats one 31-byte slot early (class i's stats sit in slot i-1; the first five knights share theirs, so only later classes
    show it), which this checks: Str, Mag, Skl, Spd, Def and Mdf of slot i-1 must equal Serenes' row i."""
    rows = serenes_classes()
    assert len(rows) == 72, len(rows)
    for i in range(1, 71):
        slot = CLASSES + (i - 1) * 31
        assert tuple(rows[i][2:8]) == tuple(R[slot + 0x19:slot + 0x1F]), ('class', i, rows[i])
    SERENES_CLASSES.update({i: rows[i][0] for i in range(72)})
    names = ln.class_names()
    return {i: names[i] for i in range(72)}


def chapter_headers():
    """Each chapter's script header, [chapter u16][opening script][event table] (3-byte pointers), found by their self-reference: the
    opening script follows the 8-byte header. Returns {chapter: (bank, opening script address)}."""
    found = {}
    for o in range(len(R) - 8):
        n = R[o]
        if n <= 11 and R[o + 1] == 0:
            p1 = R[o + 2] | R[o + 3] << 8
            b1 = R[o + 4]
            p2 = R[o + 5] | R[o + 6] << 8
            if R[o + 7] == b1 and b1 >= 0x80 and (b1 & 0x3F) == o >> 16 and p1 == (o & 0xFFFF) + 8 and p1 < p2 < p1 + 0x4000:
                found[n] = (b1, p1)
    assert sorted(found) == list(range(12)), sorted(found)
    return found


def inline_cmds(op, args):
    """The event commands an action runs, in order: the command itself (unless it runs a scene: 0x30), then the scene's inline event
    commands (scene ops 0x4A and 0x4D); a scene's walk (scene op 0x24 [unit u16][mode][x1][y1][x2][y2], mode 1 a unit walking onto
    the map) as ('walk', operands)."""
    out = [] if op == 0x30 else [(op, args)]
    for o, x in ev.action_scene((op, args)):
        if o in ev.INLINE_OPS and x:
            out.append((x[0], x[1:]))
        elif o == 0x24 and len(x) >= 7:
            out.append(('walk', x))
    return out


def chapter_events(chapter):
    """A chapter's events in the table's order: ('open', None, cmds, scene) for the opening script, ('trigger', t, cmds, scene) for
    each trigger, and ('block', [blocks], cmds, scene) for each run of block commands under one condition (the table lists them one at a
    time); `scene` is the raw scene commands they run (where units are put)."""
    bank, opening, _ = ev.chapter_headers()[chapter]
    script = ev.script(bank, opening)
    out = [('open', None, [c for _, op, a in script for c in inline_cmds(op, a)], [c for _, op, a in script for c in ev.action_scene((op, a))])]
    triggers, blocks = ev.event_table(chapter)
    for t in triggers:
        out.append(('trigger', t, inline_cmds(*t['action']) if t['action'] else [], ev.action_scene(t['action']) if t['action'] else []))
    for b in blocks:
        last = out[-1]
        if last[0] == 'block' and (last[1][0]['turn'], last[1][0]['flags']) == (b['turn'], b['flags']):
            last[1].append(b)
            last[2].extend(inline_cmds(b['op'], b['args']))
            last[3].extend(ev.action_scene((b['op'], b['args'])))
        else:
            out.append(('block', [b], inline_cmds(b['op'], b['args']), list(ev.action_scene((b['op'], b['args'])))))
    return out


def relation_set(cmds, army):
    """The relation to your army the last `4D [relation] [a] [b]` in cmds gives `army` (it's symmetric, $84:C1A5: either side may be
    yours), or None. Relations: 1 hostile, 2 friendly, 3 neither (it clears both bits, $84:C1DD)."""
    out = None
    for o, x in cmds:
        if o == 0x4D and len(x) >= 3 and (x[1], x[2]) in ((army, 0), (0, army)):
            out = x[0]
    return out


def army_relations(events):
    """{army: its relation to yours as it comes onto the map}: the opening's, and for an army an event creates (`4B [army] [def]`,
    $84:BBD2), that event's own; one no `4D` sets is neutral."""
    out = {}
    for _, _, cmds, _ in events:
        for o, x in cmds:
            if o == 0x4B and x[0] and x[0] not in out:
                r = relation_set(cmds, x[0])
                out[x[0]] = r if r is not None else 3
    return out


def character(i):
    """The character table's record for a unit id: 38 bytes for a named character (kind 0 playable, kind 2 named foe or NPC), 13 for a
    generic foe (kind 3), 12 for kind 1."""
    n = u16(CHARACTERS) // 2
    a = CHARACTERS + u16(CHARACTERS + 2 * (i - 1))
    return R[a:CHARACTERS + u16(CHARACTERS + 2 * i)] if i < n else R[a:a + 13]


def unit_lists():
    offsets = [u16(UNIT_LISTS + 2 * i) for i in range(57)]
    out = []
    for off in offsets:
        p, recs = UNIT_LISTS + off, []
        while u16(p) != 0xFFFF:
            recs.append(bytes(R[p:p + 8]))
            p += 8
        out.append(recs)
    return out


def opening_lists():
    """{chapter: [lists]} each chapter's opening loads, in order: `4A nn` in the opening script, or in a scene it runs (`30`)."""
    out = {}
    for chapter, (bank, opening, _) in ev.chapter_headers().items():
        found = []
        for _, op, a in ev.script(bank, opening):
            if op == 0x4A:
                found.append(a[0])
            found += ev.action_lists((op, a))
        out[chapter] = found
    assert out == OPENING_LISTS, out
    return out


def owned_lists():
    """{chapter: [list indexes]}: its opening lists and every list up to the next chapter's first."""
    firsts = [min(OPENING_LISTS[c]) for c in range(12)]
    assert firsts == sorted(firsts)
    return {c: list(range(firsts[c], firsts[c + 1] if c < 11 else 57)) for c in range(12)}


BOSS_CHAPTER = {'P': 0, 'F': 11}


def boss_rows():
    """Serenes' boss and NPC tables: [(chapter, name, class, level, source page)]."""
    rows = []
    for page in BOSS_PAGES:
        req = urllib.request.Request('https://serenesforest.net/genealogy-of-the-holy-war/characters/' + page + '/', headers={'User-Agent': 'Mozilla/5.0'})
        text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
        for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
            c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
            if len(c) >= 6 and c[0] != 'Ch' and c[3].isdigit():
                c[1] = c[1].replace('�', 'ä').replace('’', 'ä')  # Serenes' Deetäver loses its umlaut in the page's encoding
                ch = BOSS_CHAPTER.get(c[0]) if c[0] in BOSS_CHAPTER else int(c[0]) if c[0].isdigit() else None
                if ch is not None:
                    rows.append((ch, c[1], c[2], int(c[3]), page))
    return rows


def boss_items():
    """Serenes' boss and NPC item tables: {(chapter, name): [item names as Serenes writes them]}."""
    out = {}
    for page in BOSS_PAGES:
        req = urllib.request.Request('https://serenesforest.net/genealogy-of-the-holy-war/characters/' + page + '/', headers={'User-Agent': 'Mozilla/5.0'})
        text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
        for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
            c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
            if len(c) == 6 and c[0] != 'Ch' and not c[3].isdigit():
                ch = BOSS_CHAPTER.get(c[0]) if c[0] in BOSS_CHAPTER else int(c[0]) if c[0].isdigit() else None
                if ch is not None:
                    out[(ch, c[1].replace('\ufffd', 'ä'))] = [x.strip() for x in c[3].split(',') if x.strip()]
    return out


def ring_names():
    """Serenes' ring names, for the ROM's ring ids 0x6A upward (the page lists them in the table's order)."""
    req = urllib.request.Request('https://serenesforest.net/genealogy-of-the-holy-war/inventory/items/', headers={'User-Agent': 'Mozilla/5.0'})
    text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    names = []
    for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
        c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
        if len(c) == 4 and c[1].endswith('Ring'):
            names.append(c[1])
    assert len(names) == 16, names
    return {0x6A + i: n for i, n in enumerate(names)}


NAME_CHART = 'https://serenesforest.net/genealogy-of-the-holy-war/general/name-chart/'
# Bosses whose name the patch's dialogue spells differently from Serenes (each read in context there: "You and Gerald are in charge",
# "Banba! Fotla! Eriu!"); the build checks that the patch uses each spelling.
BOSS_SPELLINGS = {
    'Gerrard': 'Gerald', 'Jacoban': 'Jacobi', 'Disler': 'Distler', 'Dobarl': 'Dobar', 'Maikov': 'Maykov', 'Morigan': 'Morrigan',
    'Muhammed': 'Muhammad', 'Papilion': 'Papilio', 'Pizarl': 'Pizare', 'Voltz': 'Völtz', 'Maybell': 'Meabel', 'Bleg': 'Breg',
    'Palmark': 'Polemarch', 'Rodan': 'Rodin', 'Vaha': 'Vaja', 'Coruta': 'Gortach', 'Eliu': 'Eriu', 'Fetra': 'Fotla',
    'Deetäver': 'Dithorba', 'Maios': 'Myos', 'Magorn': 'Magon',
}
LORDS = {c: 'Sigurd' if c <= 5 else 'Seliph' for c in range(12)}   # the first generation's lord, then the second's (Lil' Nordion's names)
VILLAGE_GOLD = 0x7F453     # u16 offsets per location kind (0 castle, 2 village) to [gold u16][footprint]: what a village holds


def name_chart():
    """Serenes' name chart: {Japanese name: (the fan translation's name, which its pages use; the official one, where there is one)}."""
    req = urllib.request.Request(NAME_CHART, headers={'User-Agent': 'Mozilla/5.0'})
    text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    out = {}
    for r in re.findall(r'<tr.*?</tr>', text, flags=re.S):
        c = [html.unescape(re.sub(r'<.*?>', '', x)).strip() for x in re.findall(r'<t[dh].*?</t[dh]>', r, flags=re.S)]
        if len(c) >= 5 and c[0] and c[0] != 'Japanese name':
            out[c[0]] = (c[3], c[4])
    return out


SUBSTITUTES = 0x69CA5   # $86:9CA5: from unit id 0x19 on, the id each counts as in a talk check ($86:9C95)


def substitute_ids():
    """{child id: substitute id}: the second generation's children (ids 0x32-0x3F) and the substitutes the game places when a child
    doesn't exist. The talk checks map a child to its substitute through this table ($86:9C95), so either answers a talk."""
    return {i: R[SUBSTITUTES + i - 0x19] for i in range(0x19, 0x40) if R[SUBSTITUTES + i - 0x19] != i}


def narration_names(chart, bosses):
    """{unit id: fan name}: the chapter openings' map tours name a character, then point the camera at its unit (`82 nn [unit u16]
    00`, nn even: Chapter 1's キンボイス, then `82 06 48 00`). Only the generic and named records (kinds 3 and 2), and only names of
    Serenes' boss and NPC tables."""
    known = {r[1] for r in bosses}
    out = {}
    for m in re.finditer(rb'\x82([\x02-\x1e])(.)(.)\x00', R, flags=re.S):
        ident = m.group(2)[0] | m.group(3)[0] << 8
        if m.group(1)[0] % 2 or not 1 <= ident < u16(CHARACTERS) // 2 or character(ident)[0] not in (2, 3):
            continue
        for run in reversed(re.findall(r'[ァ-ヴー]{2,}', ev.decode(R[max(0, m.start() - 40):m.start()]))[-2:]):
            if run in chart and chart[run][0] in known:
                out.setdefault(ident, chart[run][0])
                break
    return out


def names_list(names, pairs, children=()):
    """Names joined for a sentence, a child and the substitute standing in for them as 'Lester or Deimne'; also how many there are."""
    out, seen = [], set()
    for n in names:
        if n in seen:
            continue
        other = pairs.get(n)
        if other in names:
            out.append(f'{n} or {other}' if n in children else f'{other} or {n}')
            seen |= {n, other}
        else:
            out.append(n)
            seen.add(n)
    return (', '.join(out[:-1]) + ' and ' + out[-1]) if len(out) > 1 else out[0], len(out)


def village_gold():
    return u16(VILLAGE_GOLD + u16(VILLAGE_GOLD + 4))


def article(item):
    return ('an ' if item[0] in 'AEIOU' else 'a ') + item


def gift(type_, name):
    """An item handed over, in words: a holy weapon (rank 0xFF) by its name alone ('Tyrfing'), anything else with its article."""
    return name if rom_item(type_)['rank'] == '*' else article(name)


def build_units(heights, classes):
    """{chapter: (units, reinforcement groups, events)} from the unit lists and the event tables (scripts/fe4_events.py), with the
    armies' relations from each chapter's opening script. `events` holds the castles, villages, notes and the castle that wins."""
    cpu = Cpu()
    lists = unit_lists()
    opening = opening_lists()
    owned = owned_lists()
    items = ln.item_names()
    bosses = boss_rows()
    carried_by = boss_items()
    # Serenes' item names to the patch's: the weapons through the rows matched to ROM ids, the rest through the name chart.
    item_en = {m[2][1].replace('’', "'"): items[m[0]] for m in _items().match()}
    chart = name_chart()
    lnames = ln.character_names()
    # Serenes' (fan) names to the patch's: the playable ones through the ROM's own kana name list, the rest through the patch's text.
    fan_to_ln = {chart[ev.character_name(i)][0]: lnames[i] for i in range(len(lnames)) if ev.character_name(i) in chart}
    by_fan = {fan: official for fan, official in chart.values()}

    def english(fan):
        """A Serenes (fan) name as the patch spells it: its table for playable characters, its dialogue for the rest (the official
        name or Serenes' own, as the dialogue spells it, or BOSS_SPELLINGS); Serenes' when the dialogue never names them."""
        if fan in fan_to_ln:
            return fan_to_ln[fan]
        out = []
        for part in fan.split(' / '):
            if part in BOSS_SPELLINGS:
                assert ln.spelling(BOSS_SPELLINGS[part]) == BOSS_SPELLINGS[part], part
                out.append(BOSS_SPELLINGS[part])
            else:
                out.append(ln.spelling(by_fan.get(part), part) or part)
        return ' / '.join(out)

    places = ev.place_names()
    gold = village_gold()
    norm = lambda n: re.sub(r' \([MF]\)$', '', n)

    def item_name(instance):
        t = ev.instance_type(instance)
        return items.get(t, f'Item {t}')

    def playable(ident):
        """A playable character's English name, or None: kind 0 records hold the name index at +0x0F, kind 1 (the second
        generation's children) at +5."""
        t = character(ident)
        index = (t[0x0F] | t[0x10] << 8) if t[0] == 0 else (t[5] | t[6] << 8) if t[0] == 1 else None
        if index is None:
            return None
        return lnames[index]

    subs = substitute_ids()
    pairs = {}   # name -> the other of its pair
    for child, sub in subs.items():
        pairs[playable(child)], pairs[playable(sub)] = playable(sub), playable(child)
    child_of = {sub: child for child, sub in subs.items()}
    children = {playable(c) for c in subs}
    told = narration_names(chart, bosses)

    out = {}
    joined = set()   # the units whose own items have been counted: once, in the first chapter each joins you
    for chapter, (bank, y) in sorted(chapter_headers().items()):
        events = chapter_events(chapter)
        relation = army_relations(events)
        height = heights[chapter]
        rows = [r for r in bosses if r[0] == chapter]
        locs = {l[0]: l for l in ev.locations(chapter)}

        def info(rec):
            """(unit id, x, y, flag, army, template) for a record, or None for an empty one."""
            ident = rec[0] | rec[1] << 8
            return (ident, rec[2], rec[3], rec[4], rec[6], character(ident)) if ident else None

        def fields(t):
            """(class, level, carried item types) of a record. A generic foe's record (kind 3) holds two carried item types at +10 and
            the item instance it drops at +12; a named foe's or NPC's (kind 2) the same three at +0x23 (Hilda carries Bolganone and
            Hel and drops Bolganone). A playable character's are item instances (see the item sources below), not shown on the map."""
            kind = t[0]
            if kind == 3:
                return t[5], t[7], bytes(i for i in t[10:12] if i in items)
            if kind == 2:
                return t[9], t[10], bytes(i for i in t[0x23:0x25] if i in items)
            return (t[9], t[10], b'') if kind == 0 else (t[1], None, b'')

        def drop(t):
            """The item a foe drops when defeated, or None: an item instance (counted from 1) at +12 (kind 3) or +0x25 (kind 2)."""
            i = t[12] if t[0] == 3 else t[0x25] if t[0] == 2 and len(t) > 0x25 else 0xFF
            return items[ev.instance_type(i)] if 0 < i <= ev.INSTANCE_COUNT else None

        # A boss or named foe is a leader (flag 1, or 254 / 255) or a named record whose class and level are a row of Serenes'
        # boss table: the game keeps no name for them (its name table, $8D:920D, covers the 63 playable characters: $91:8D56 holds the
        # index under 0x3F). The opening narration's pointer at a unit names it first (Chapter 1's Kinbois is 0x48, not Genoa's
        # leader 0x5C). When more units fit a row than the table has names, only the flagged leaders take the name, else the one
        # given a battle quote of its own (trigger 0x0D [0][talker][FFFF][unit] showing text when anyone fights it: Chapter 2's Elliot,
        # 0x66, has one, the other Level 15 Duke Knight none), else the one holding a castle; a named record whose level isn't Serenes'
        # takes the chapter's one row of its class left (Eldigan: a Level 25 Paladin in Chapter 3's ROM, 23 on Serenes).
        castle_tiles = {(l[3], l[4]) for l in locs.values() if l[1] == 0}
        home_raw = (locs[0][3], locs[0][4])
        quoted = {t['args'][6] | t['args'][7] << 8 for t in ev.event_table(chapter)[0] if t['op'] == 0x0D and len(t['args']) >= 8}
        # A unit a scripted talk names is a character too (Chapter 10's Polemarch, who hands Seliph Tyrfing).
        spoken = {t['args'][i] | t['args'][i + 1] << 8 for t in ev.event_table(chapter)[0] if t['op'] in (0x04, 0x15, 0x16) for i in (0, 2)}
        candidates, names_for, name_of_id, used = {}, {}, {}, set()
        for k in owned[chapter]:
            for rec in lists[k]:
                d = info(rec)
                if d and d[4] in relation:
                    cls, level, _ = fields(d[5])
                    if d[0] in told:
                        names_for[(d[0], d[1], d[2])] = name_of_id[d[0]] = english(told[d[0]])
                        used.add(told[d[0]])
                    elif level is not None and d[5][0] != 0 and (d[5][0] != 3 or d[3] in (1, 254, 255) or (d[1], d[2]) in castle_tiles
                                                                 or d[0] in quoted | spoken):
                        candidates.setdefault((norm(SERENES_CLASSES.get(cls, '')), level), []).append(d)
        for key, found in candidates.items():
            row_names = sorted({r[1] for r in rows if r[3] == key[1] and norm(r[2]) == key[0] and r[1] not in fan_to_ln} - used)
            if not row_names:
                continue
            leaders = [d for d in found if d[3] == 1]
            heard = [d for d in found if d[0] in quoted]
            held_ = [d for d in found if (d[1], d[2]) in castle_tiles - {home_raw}]
            use = next((x for x in (found, leaders, heard, held_) if 0 < len(x) <= len(row_names)), [])
            used |= set(row_names) if use else set()
            for d in use:
                name = ' / '.join(row_names)
                if len(row_names) > 1:
                    # Several bosses share a class and level (Chapter 5's Barons): the one whose items Serenes lists is the one.
                    held = {items[i] for i in fields(d[5])[2]}
                    official = {fan: off for fan, off in chart.values()}
                    fits = [n for n in row_names if held & {item_en.get(x) or ln.spelling(official.get(x), x) or x for x in carried_by.get((chapter, n), [])}]
                    if len(fits) == 1:
                        name = fits[0]
                names_for[(d[0], d[1], d[2])] = english(name)
                name_of_id[d[0]] = english(name)
        by_class = {}
        for found in candidates.values():
            for d in found:
                if (d[0], d[1], d[2]) not in names_for and (d[5][0] == 2 or d[0] in spoken):
                    by_class.setdefault(norm(SERENES_CLASSES.get(fields(d[5])[0], '')), []).append(d)
        for cls_, found in by_class.items():
            left = sorted({r[1] for r in rows if norm(r[2]) == cls_ and r[1] not in fan_to_ln} - used)
            if len(left) == 1 and len({d[0] for d in found}) == 1:
                for d in found:
                    names_for[(d[0], d[1], d[2])] = name_of_id[d[0]] = english(left[0])
                used.add(left[0])

        def unit_name(ident):
            """Who a unit id is, for the event text: a playable character, a named foe of this chapter, a named record matching one
            row of Serenes' boss and NPC tables by class and level (this chapter's rows first, then the chapter's only row of that
            class: Eltshan is a Level 25 Paladin in the ROM, 23 on Serenes), or its class."""
            p = playable(ident)
            if p:
                return p
            if ident in name_of_id:
                return name_of_id[ident]
            t = character(ident)
            cls, level, _ = fields(t)
            klass = classes.get(cls, f'unit {ident:X}')
            sklass = SERENES_CLASSES.get(cls, klass)
            if t[0] in (2, 3):
                here = [r for r in bosses if r[0] == chapter]
                for found in ({r[1] for r in here if r[3] == level and norm(r[2]) == norm(sklass)},
                              {r[1] for r in bosses if r[3] == level and norm(r[2]) == norm(sklass)} if t[0] == 2 else set(),
                              {r[1] for r in here if norm(r[2]) == norm(sklass)}):
                    if len(found) == 1:
                        return english(found.pop())
            return 'the ' + klass

        def place(lid):
            kind, name, x, ly = locs[lid][1], locs[lid][2], locs[lid][3], locs[lid][4]
            return ln.place(places[name]) if kind == 0 else f'the village at ({x + 1}, {height - ly})'

        def army(n):
            return 'your army' if n == 0 else {1: 'the enemy', 2: 'an allied army', 3: 'a neutral army'}.get(relation.get(n), f'army {n}')

        def phase(n):
            return 'your phase' if n == 0 else {1: 'the enemy phase', 2: 'the allied phase', 3: "a neutral army's phase"}.get(relation.get(n), f"army {n}'s phase")

        def make(rec, rel=None):
            """A unit as its army stands toward yours when it comes onto the map (`rel`; the army's starting relation by default)."""
            d = info(rec)
            if not d:
                return None
            ident, x, ty, flag, army_, t = d
            if army_ not in relation:
                return None  # your own army's placements aren't shown yet
            rel = relation[army_] if rel is None else rel
            cls, level, carried = fields(t)
            klass = classes.get(cls, f'Class {cls}')
            if rel != 1:
                named = playable(ident) or names_for.get((ident, x, ty))
                u = {'type': 'ally', 'name': named or klass, 'tile': [x + 1, height - ty], '_army': army_, '_id': ident}
                if t[0] in (2, 3):
                    # What it carries and drops, should its army turn on yours (Chapter 2's Bishop and his Sleep Staff).
                    u['_carries'] = [items.get(i, f'Item {i}') for i in carried if i != 0xFF]
                    u['_drops'] = [x_ for x_ in [drop(t)] if x_]
                if not named:
                    u['generic'] = True
                if rel == 3:
                    u['neutral'] = True
                    u['note'] = 'Neutral to your army: it neither fights you nor helps you.'
                if named and level is not None:
                    u['note'] = ' '.join(x_ for x_ in (f'{klass}, Lv {level}.', u.get('note')) if x_)
                return u
            u = {'type': 'enemy', 'name': klass, 'tile': [x + 1, height - ty], '_army': army_, '_id': ident}
            name = (playable(ident) if t[0] in (0, 1) else None) or names_for.get((ident, x, ty))
            # The skull is every castle's holder's: FE4 is won by seizing, and each castle a foe holds is one to take.
            holds = next((ln.place(places[l[2]]) for l in locs.values() if l[1] == 0 and (l[3], l[4]) == (x, ty) and l[0] != 0), None)
            if name:
                u['name'] = name
                u['type'] = 'boss' if holds and t[0] not in (0, 1) else 'named'
                u['note'] = f'{klass}, Lv {level}' if level is not None else klass
            elif level is not None:
                u['note'] = f'Lv {level}'
            if holds and t[0] not in (0, 1):
                u['type'] = 'boss'
                u['note'] = ' '.join(x_ for x_ in (u.get('note', '') + '.' if u.get('note') else None, f'Holds {holds}.') if x_)
            if carried:
                u['carries'] = [items.get(i, f'Item {i}') for i in carried if i != 0xFF]
            dropped = drop(t)
            if dropped:
                u['drops'] = [dropped]
            return u

        # Where each later list comes in: the events whose commands load it (0x4A) or place it swapping one id for another (0x4F
        # [list][flag][id][id]: Chapter 8's list 40, which nothing else loads), apart from a scene that ends the chapter (0x78: its cast
        # is no unit on the battle map, Chapter 5's Arvis and his men after Ida's talk); and how its armies stand toward yours then:
        # the event's own `4D` for the army, or the army's starting relation.
        def ends(cmds):
            return any(o == 0x78 for o, _ in cmds)

        # How each army stands toward yours as each event runs: the relations so far, carried through the blocks in the table's order
        # (turn and flag blocks follow one another; a trigger can fire at any time, so what it changes is said on the units instead),
        # with the event's own `4D`s on top (Chapter 5: Travant's army is made neutral before his wyverns come).
        state, state_at = dict(relation), {0: dict(relation)}
        made = {}
        for o, x in events[0][2]:
            if o == 0x4B and x[0]:
                made[x[0]] = made.get(x[0], -1) + 1
        made_at, latest = {0: dict(made)}, dict(made)
        for i_, e in enumerate(events[1:], 1):
            fresh = dict(made)
            for o, x in e[2]:
                if o == 0x4B and x[0]:
                    fresh[x[0]] = fresh.get(x[0], -1) + 1
                    latest[x[0]] = max(latest.get(x[0], 0), fresh[x[0]])
            made_at[i_] = fresh
            if e[0] == 'block':
                made = fresh
            snap = dict(state)
            for o, x in e[2]:
                if o == 0x4B and x[0] and x[0] not in snap:
                    snap[x[0]] = 3
            for a in {x[k_] for o, x in e[2] if o == 0x4D and len(x) >= 3 for k_ in (1, 2)} - {0}:
                r_ = relation_set(e[2], a)
                if r_ is not None:
                    snap[a] = r_
            state_at[i_] = snap
            if e[0] == 'block':
                state = snap
        index_of = {id(e): i_ for i_, e in enumerate(events)}

        arrive = {}   # list -> [(event, {army: relation})]
        for e in events[1:]:
            if ends(e[2]):
                continue
            for o, x in e[2]:
                if o in (0x4A, 0x4F) and x and x[0] in owned[chapter] and x[0] not in opening[chapter]:
                    rels = {a: state_at[index_of[id(e)]].get(a) for a in {r_[6] for r_ in lists[x[0]]}}
                    if all(ev_ is not e for ev_, _ in arrive.get(x[0], [])):
                        arrive.setdefault(x[0], []).append((e, rels))

        def hostile_part(k):
            rels = arrive[k][0][1]
            return [u for u in (make(r_, rels.get(r_[6])) for r_ in lists[k]) if u and u['type'] != 'ally']

        # A list placed with an id swap (`4F [list][byte][id][id]`) holds a substitute, swapped for the child it stands in for when
        # the child exists (Chapter 8's Asaello and Febail, Hawk and Ced): named as both, as the notes name them.
        swaps = {(x[0], x[2] | x[3] << 8): x[4] | x[5] << 8 for e in events for o, x in e[2] if o == 0x4F and len(x) >= 6}

        later = [k for k in owned[chapter] if k in arrive and hostile_part(k)]
        label_of = {k: f'Group {i + 1}' for i, k in enumerate(later)}

        def group(ls):
            """'Group 3 arrives' / 'Groups 3 and 4 arrive' for the lists a scene loads."""
            numbers = sorted(int(label_of[k].split()[1]) for k in ls if k in label_of)
            if not numbers:
                return None
            if len(numbers) == 1:
                return f'Group {numbers[0]} arrives'
            return 'Groups ' + ', '.join(map(str, numbers[:-1])) + f' and {numbers[-1]} arrive'

        def tile(x, ty):
            return (x + 1, height - ty)

        d = ev.Describer(chapter, unit_name, place, army, group, tile, phase)

        def sentence(clause):
            return clause[0].upper() + clause[1:] + '.'

        def event_when(e):
            """When an event runs, as a clause ('when you seize Jungby', 'turn 3, at the start of the enemy phase'), or None; a phase is
            named by how its army stands toward yours as the event runs."""
            if e[0] == 'trigger':
                c = d.trigger(e[1])
                return 'when ' + c if c else None
            snap, kept = state_at[index_of[id(e)]], d.phase
            d.phase = lambda n: 'your phase' if n == 0 else {1: 'the enemy phase', 2: 'the allied phase', 3: "a neutral army's phase"}.get(
                snap.get(n), f"army {n}'s phase")
            try:
                c = d.when(e[1][0])
            finally:
                d.phase = kept
            if c and e[1][0]['turn'] is None:
                c = 'after ' + c  # a block on flags alone runs as soon as they're set
            return c

        # When each later group arrives: the events that load it (0x4A) or place it with a swap (0x4F).
        when = {}
        for e in events[1:]:
            c = event_when(e)
            for k in dict.fromkeys(x[0] for o, x in e[2] if o in (0x4A, 0x4F) and x):
                if c:
                    when.setdefault(k, []).append(c)

        units, groups, arrivals_ = [], [], []
        for k in owned[chapter]:
            if k in opening[chapter]:
                units += [u for u in map(make, lists[k]) if u]
                continue
            if k not in arrive:
                continue
            text = ' or '.join(dict.fromkeys(when[k])) if k in when else None
            said = sentence(text) if text else 'Arrives during the chapter; what triggers it has not been read yet.'
            rels = arrive[k][0][1]
            came = index_of[id(arrive[k][0][0])]
            made = [(r_, make(r_, rels.get(r_[6]))) for r_ in lists[k]]
            for r_, u in made:
                if u:
                    u['_came'] = came
                    ident = r_[0] | r_[1] << 8
                    if (k, ident) in swaps:
                        # The list holds the substitute's record; the game swaps in the child when the child was born ($84:8873).
                        child_id = swaps[(k, ident)]
                        if u['type'] == 'boss':
                            u['type'] = 'named'  # a substitute leads no one: its fall wins nothing
                        u['standIn'] = {'type': u['type'], 'name': unit_name(ident), 'note': (u.get('note') or '').rstrip('.'),
                                        'when': f"{playable(child_id)} wasn't born"}
                        u['name'] = playable(child_id)
                        u['note'] = classes.get(fields(character(child_id))[0], '')  # a child's record holds no level
            foes = [u for _, u in made if u and u['type'] != 'ally']
            if foes:
                g = {'id': f'list{k}', 'label': label_of[k], 'when': said, 'units': foes}
                # A group the game brings once a unit reaches an area (0x0B triggers setting the flags its block waits on) shows them.
                first, areas = arrive[k][0][0], []
                spots = [t_ for test, fl in (first[1][0]['flags'] if first[0] == 'block' else []) if test != 'clear' for f_ in fl
                         for kind_, t_ in d.setters.get(f_, []) if kind_ == 'trigger' and t_['op'] == 0x0B]
                if first[0] == 'trigger' and first[1]['op'] == 0x0B:
                    spots.append(first[1])
                for t_ in spots:
                    a_ = t_['args']
                    (x1, y1), (x2, y2) = tile(a_[2], a_[3]), tile(a_[4], a_[5])
                    area = {'who': 'player', 'rect': [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]}
                    if area not in areas:
                        areas.append(area)
                if areas:
                    g['areas'] = areas
                groups.append(g)
            # Another army's units that arrive friendly or neutral to yours: drawn as arriving green (or neutral) units.
            for r_, u in made:
                if u and u['type'] == 'ally':
                    j = {'name': u['name'], 'tile': u['tile'], 'from': u['tile'], 'group': f'list{k}', 'when': said, 'ally': True}
                    for key in ('generic', 'neutral'):
                        if u.get(key):
                            j[key] = True
                    j['_army'], j['_came'] = u['_army'], came
                    for key in ('_id', '_drops', '_carries', 'standIn'):
                        if key in u:
                            j[key] = u[key]
                    note = (u.get('note') or '').replace('Neutral to your army: it neither fights you nor helps you.', '').strip()
                    if note:
                        j['note'] = note
                    arrivals_.append(j)
        # A unit a scene walks onto the map from off it (scene op 0x24, mode 1: Chapter 8's Ishtar on turn 5), as one of the army
        # whose phase it comes in.
        for e in events[1:]:
            if e[0] != 'block' or ends(e[2]) or not e[1][0]['turn']:
                continue
            for o, x in e[2]:
                if o == 'walk' and x[2] == 1:
                    ident = x[0] | x[1] << 8
                    army_ = e[1][0]['turn'][1][1]
                    rec = bytes([x[0], x[1], x[5], x[6], 0, 0, army_, 0])
                    u = make(rec, state_at[index_of[id(e)]].get(army_))
                    if u:
                        u['_came'] = index_of[id(e)]
                    if u and u['type'] == 'enemy' and not unit_name(ident).startswith('the '):
                        # Named as the game's text names the unit (Chapter 8's Ishtar).
                        level = fields(character(ident))[1]
                        u.update({'type': 'named', 'name': unit_name(ident), 'note': f"{u['name']}, Lv {level}"})
                    if u and u['type'] != 'ally':
                        c = d.when(e[1][0])
                        groups.append({'id': f'walk{ident}', 'label': f'Group {len(groups) + 1}',
                                       'when': sentence(c) if c else 'Arrives during the chapter.',
                                       'units': [{**u, 'from': list(tile(x[3], x[4]))}]})

        # What visiting or entering gives (event triggers: 0x0A a unit, or anyone, visits a village or castle; 0x07 a unit enters a
        # castle), and the castle that wins: the one whose seizing runs the scene that ends the chapter (event command 0x78).
        visits, hidden = {}, []
        for t in d.triggers:
            a = t['args']
            gifts = [(who, item_name(i)) for who, i in ev.action_gifts(t['action'])]
            if not gifts:
                continue
            if t['op'] in (0x0A, 0x07):
                who, lid = a[0] | a[1] << 8, a[2] | a[3] << 8
                visits.setdefault(lid, []).append((None if who == 0xFFFF else unit_name(who), [g for _, g in gifts]))
            elif t['op'] == 0x0B:  # a unit reaching a spot: the hidden finds (Lex's Hero Axe, Arden's Pursuit Ring)
                who = a[0] | a[1] << 8
                (x1, y1), (x2, y2) = tile(a[2], a[3]), tile(a[4], a[5])
                hidden.append({'type': 'hidden', 'tile': [min(x1, x2), min(y1, y2)],
                               'area': [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], 'contents': ', '.join(g for _, g in gifts),
                               'note': f"Found by {'anyone' if who == 0xFFFF else unit_name(who)} moving here."})
        end = None
        for t in d.triggers:
            ops = [x[0] for op, x in ev.action_scene(t['action']) if op in ev.INLINE_OPS and x]
            if t['op'] == 0x02 and 0x78 in ops and (t['args'][0] | t['args'][1] << 8) == 0:
                end = t['args'][2] | t['args'][3] << 8
        if end is None:  # Chapter 2: seizing Agusty sets a flag, and the block that waits on it ends the chapter
            for b in d.blocks:
                ops = [x[0] for op, x in ev.action_scene((b['op'], b['args'])) if op in ev.INLINE_OPS and x]
                if 0x78 in ops and len(b['flags']) == 1 and b['flags'][0][0] == 'set':
                    for kind, t in d.setters.get(b['flags'][0][1][0], []):
                        if kind == 'trigger' and t['op'] == 0x02:
                            end = t['args'][2] | t['args'][3] << 8
        assert end is not None, chapter

        # Who isn't on the map at the start: what a visit by them gives says so, for the spoiler block (Chapter 7's Laylea, the Final
        # Chapter's Julia).
        arriving_ids = {x[0] | x[1] << 8 for e in events[1:] for o, x in e[2] if o in (0x49, 0x53) and len(x) >= 2}
        arriving_ids |= {r_[0] | r_[1] << 8 for k in owned[chapter] if k not in opening[chapter] for r_ in lists[k]}
        arriving = {unit_name(i) for i in arriving_ids if i} - {unit_name(r_[0] | r_[1] << 8) for k in opening[chapter] for r_ in lists[k] if r_[0] | r_[1]}

        def visitor(who):
            return f'{who} (once {who} appears on the map)' if who in arriving else who

        objects, notes = [], []
        for lid, (_, kind, name, x, ly) in sorted(locs.items()):
            gifts = visits.get(lid, [])
            if kind == 0:
                o = {'type': 'castle', 'tile': [x + 1, height - ly], 'name': ln.place(places[name])}
                n = []
                if lid == 0:
                    n.append('Your home castle: the chapter is lost if the enemy seizes it.')
                if lid == end:
                    n.append(f'Seizing it with {LORDS[chapter]} wins the chapter.')
                for who, g in gifts:
                    n.append(f"{visitor(who) if who else 'Anyone'} entering it receives {' and '.join(g)}.")
                if n:
                    o['note'] = ' '.join(n)
                objects.append(o)
            else:
                o = {'type': 'village', 'tile': [x + 1, height - ly], 'reward': f'{gold} gold'}
                n = [f"Visited by {visitor(who)}: {', '.join(g)} as well." if who else f"Also gives {' and '.join(article(i) for i in g)}." for who, g in gifts]
                if n:
                    o['note'] = ' '.join(n)
                objects.append(o)

        # Talks that hand over an item or recruit someone (one line for a pair the game checks both ways round), and the playable
        # units the turn blocks bring in.
        later = set()
        for t in d.triggers:
            later |= {x[1] | x[2] << 8 for op, x in ev.action_scene(t['action']) if op in ev.INLINE_OPS and x[:1] == b'\x49'}
        for b in d.blocks:
            later |= {x[1] | x[2] << 8 for op, x in ev.action_scene((b['op'], b['args'])) if op in ev.INLINE_OPS and x[:1] == b'\x49'}
        later_names = {unit_name(i) for i in later}
        # Talks (event triggers 0x04, 0x15 and 0x16). 0x15 takes the talker's child or substitute as one, 0x16 both sides ($86:8828,
        # $86:8876 through $86:9C95): their ids are the substitutes'. A talk that does something goes on the unit talked to, and on the
        # talker when it's someone else's unit (the Prologue's Arvis), as the game's talk does it: who joins, for how much gold (0x55
        # takes it from the talker), what's handed over, an army that turns, who leaves the map, the chapter ending. Only a talk
        # between two of your own units stays a note.
        drawn = {}   # unit id -> the units of that id on the map that aren't yours
        for u in units + [x for g in groups for x in g['units']] + arrivals_:
            if u.get('_id'):
                drawn.setdefault(u['_id'], []).append(u)
        endings_on = {f_ for b_ in d.blocks if (b_['turn'], repr(b_['flags'])) in d.endings for test, fl in b_['flags'] if test != 'clear'
                      for f_ in fl}

        def either(ident, paired):
            """The ids a talk's id stands for: a child and its substitute both, when the trigger takes the pair as one (0x16 maps its
            own ids too, so either can be written)."""
            if not paired:
                return [ident]
            return [ident, subs[ident]] if ident in subs else [ident, child_of[ident]] if ident in child_of else [ident]

        def who_words(ids):
            return ' or '.join(playable(i) or unit_name(i) for i in sorted(ids, key=lambda i: i not in subs))   # the child first

        talks, talked, unsure = {}, {}, []
        for t in d.triggers:
            if t['op'] not in (0x04, 0x15, 0x16) or not t['action']:
                continue
            a = t['args']
            frm, to = a[0] | a[1] << 8, a[2] | a[3] << 8
            frm_ids, to_ids = either(frm, t['op'] in (0x15, 0x16)), either(to, t['op'] == 0x16)
            cmds = [x for op, x in ev.action_scene(t['action']) if op in ev.INLINE_OPS and x]
            joins = [x[1] | x[2] << 8 for x in cmds if x[0] == 0x53 and x[3] == 0]
            speaker = 'any of your units' if frm == 0xFFFF else who_words(frm_ids)
            target = who_words(to_ids)
            cost = sum(x[3] | x[4] << 8 for x in cmds if x[0] == 0x55 and len(x) >= 5 and (x[1] | x[2] << 8) == 0xFFFF)
            results, given = [], {}
            for who, i in ev.action_gifts(t['action']):
                given.setdefault(speaker if who == 0xFFFF else unit_name(who), []).append(gift(ev.instance_type(i), item_name(i)))
            branches = any(op in (0x03, 0x04, 0x05, 0x06) for op, _ in ev.action_scene(t['action']))
            for receiver, gifts in given.items():
                # Two gifts in a scene that branches are alternatives (Julia's Aura or Nosferatu, by whether Isaach is seized).
                results.append(f"{receiver} receives {(' or ' if branches else ' and ').join(gifts)}")
            army_of = {u_['_army'] for i in to_ids for u_ in drawn.get(i, []) if '_army' in u_}
            for x in cmds:
                if x[0] == 0x4D and len(x) >= 4 and 0 in (x[2], x[3]) and x[2] != x[3]:
                    turned = x[2] or x[3]
                    words = {1: 'hostile', 2: 'friendly', 3: 'neutral'}.get(x[1])
                    if words:
                        results.append(f"{'their' if turned in army_of else 'another'} army turns {words}")
            # A unit that joins is taken off the map as its playable record takes over (Chapter 2's Erinys): no departure.
            gone = [x[1] | x[2] << 8 for x in cmds if x[0] in (0x65, 0x66, 0x74) and len(x) >= 3 and not any(
                x[1] | x[2] << 8 in ids_ for ids_ in (to_ids, frm_ids) if any(j in ids_ for j in joins))]
            for i in dict.fromkeys(gone):
                n = gone.count(i)
                name = unit_name(i) if playable(i) or i in name_of_id or character(i)[0] == 2 else 'the ' + classes.get(fields(character(i))[0], 'unit')
                if i in to_ids or i in frm_ids:
                    results.append(f'{target if i in to_ids else speaker} leaves the map')
                elif name.startswith('the '):
                    results.append(f'{name.replace("the ", f"the {n} ", 1) + "s" if n > 1 else name} leave{"" if n > 1 else "s"} the map')
                else:
                    results.append(f'{name} leaves the map')
            sets = {t['flag']} if t['flag'] < 0x80 else set()
            if t['action'][0] == 0x27:
                sets.add(t['action'][1][0])
            elif t['action'][0] == 0x30 and t['action'][1][0] < 0x80:
                sets.add(t['action'][1][0])
            # The chapter's ending is said on the unit; a note leaves it to "The chapter also ends ..." below.
            ends_here = bool(sets & endings_on or any(x[0] == 0x78 for x in cmds))
            if not (results or joins or ends_here):
                continue

            def joined_words(ids_):
                """Who else the talk recruits, as a result ('Hannibal joins your army'), leaving out the unit it's said on."""
                others_ = [unit_name(i) for i in dict.fromkeys(joins) if i not in ids_]
                if not others_:
                    return []
                text_, n_ = names_list(others_, pairs, children)
                return [f"{text_} join{'s' if n_ == 1 else ''} your army"]

            for ids, other in ((to_ids, speaker), (frm_ids, target)):
                said = joined_words(ids) + results + (['the chapter ends'] if ends_here else [])
                for i in ids:
                    for u_ in drawn.get(i, []):
                        if any(j in ids for j in joins):
                            text = f"Recruit: talk with {other}" + (f' for {cost:,} gold' if cost else '') + ''.join(f'; {r}' for r in said)
                        else:
                            text = f"Talk with {other}: {'; '.join(said)}"
                        talked.setdefault(id(u_), (u_, []))[1].append(text)
            if any(drawn.get(i) for i in to_ids + frm_ids):
                continue
            results = joined_words([]) + results
            if not results:
                continue
            key = frozenset((speaker, target))
            prior = talks.get(key)
            arriving = [n for n in (speaker, target) if n in later_names]
            opener = prior[0] if prior else f"{speaker[0].upper() + speaker[1:]} talks to {target}" + (f" (once {arriving[0]} appears on the map)" if arriving else '')
            talks[key] = (opener, list(dict.fromkeys((prior[1] if prior else []) + results)))
        for u_, texts in talked.values():
            u_['talk'] = '. '.join(dict.fromkeys(texts))
            if 'standIn' in u_:
                u_['standIn']['talk'] = u_['talk']
        for opener, results in talks.values():
            notes.append(f"{opener}: {'; '.join(results)}.")
        for e in events[1:]:
            # Event command 0x49 puts a unit on the map: a playable character joins you; anyone else (Alvis, Julius) appears. One the
            # same scene takes off again (0x65) is its cast, and a scene that ends the chapter puts no one on the battle map.
            if ends(e[2]):
                continue
            gone = {x[0] | x[1] << 8 for o, x in e[2] if o == 0x65 and len(x) >= 2}
            placed = [x[0] | x[1] << 8 for o, x in e[2] if o == 0x49 and len(x) >= 2 and (x[0] | x[1] << 8) not in gone]
            c = event_when(e)
            if not c:
                # A named unit put on the map by an event that waits on a flag nothing in the chapter sets (Chapter 5's Ida).
                unset = [f_ for test, fl in (e[1][0]['flags'] if e[0] == 'block' else []) if test != 'clear' for f_ in fl if f_ not in d.setters]
                for i in placed:
                    if unset and not playable(i) and not unit_name(i).startswith('the '):
                        unsure.append(f'When {unit_name(i)} appears on the map: the event that places {unit_name(i)} waits on an event '
                                      'flag no script in the chapter sets.')
                continue
            joining = list(dict.fromkeys(unit_name(i) for i in placed if playable(i)))
            others = list(dict.fromkeys(unit_name(i) for i in placed if not playable(i) and not unit_name(i).startswith('the ')))
            if not (e[0] == 'trigger' and e[1]['op'] in (0x04, 0x15, 0x16)):
                joining += [unit_name(x[0] | x[1] << 8) for o, x in e[2] if o == 0x53 and len(x) > 2 and x[2] == 0]
                joining = list(dict.fromkeys(joining))
            if joining:
                text, n = names_list(joining, pairs, children)
                notes.append(f"{text} join{'s' if n == 1 else ''} your army: {c}.")
            if others:
                text, n = names_list(others, pairs, children)
                notes.append(f"{text} appear{'s' if n == 1 else ''} on the map: {c}.")
        objects += hidden
        notes = list(dict.fromkeys(notes))

        # Where units are put: scene op 0x24 walks a unit `[unit u16][00][x1][y1][x2][y2]...` and the inline event command 0x50 sets
        # its tile `[unit u16][FF][x][y]`. Joiners come from the blocks and triggers whose scenes put a playable unit on the map
        # (event command 0x49); the starting units from the opening.
        def placements(scene_cmds, loads):
            """{unit id: (from tile, to tile)} for the units a scene puts somewhere, in the page's coordinates; `loads` are the unit lists
            loaded with it, whose records on your side give a tile too."""
            out = {}
            for op, a in scene_cmds:
                if op == 0x24 and len(a) >= 7:
                    out[a[0] | a[1] << 8] = (tile(a[3], a[4]), tile(a[5], a[6]))
                elif op in ev.INLINE_OPS and a[:1] == b'\x50' and len(a) >= 6 and (a[4], a[5]) != (0, 0):  # (0, 0): no tile given
                    t_ = tile(a[4], a[5])
                    out[a[1] | a[2] << 8] = (t_, t_)
            # A unit the lists loaded with it place on your side (Arden in the Prologue, Brigid in Chapter 3) stands where its record says.
            for k in loads:
                for r_ in lists[k]:
                    if r_[6] == 0 and (r_[0] | r_[1] << 8) not in out and (r_[0] | r_[1] << 8):
                        t_ = tile(r_[2], r_[3])
                        out[r_[0] | r_[1] << 8] = (t_, t_)
            return out

        def merge(entries):
            """[(name, ...rest, stand-in)]: a child and their substitute placed alike are one entry, the child's, with the substitute
            as its stand-in (the game places the substitute only when the child wasn't born); anyone else has None."""
            out = []
            for e_ in entries:
                twin = next((i_ for i_, o in enumerate(out) if pairs.get(e_[0]) == o[0] and o[1:-1] == tuple(e_[1:])), None)
                if twin is not None:
                    o = out[twin]
                    child, sub = (o[0], e_[0]) if o[0] in children else (e_[0], o[0])
                    out[twin] = (child,) + o[1:-1] + (sub,)
                else:
                    out.append(tuple(e_) + (None,))
            return out

        bank_, opening_, _ = ev.chapter_headers()[chapter]
        joiners = []
        for n_, e in enumerate(events[1:], 1):
            if ends(e[2]):
                continue
            gone = {x[0] | x[1] << 8 for o, x in e[2] if o == 0x65 and len(x) >= 2}
            placed = [x[0] | x[1] << 8 for o, x in e[2] if o == 0x49 and len(x) >= 2]
            moves = placements(e[3], [x[0] for o, x in e[2] if o in (0x4A, 0x4F) and x])
            c = event_when(e)
            here = [(playable(i), tuple(moves[i][1]), tuple(moves[i][0])) for i in placed if playable(i) and i in moves and i not in gone]
            for name, to, frm, sub in merge(here):
                if c:
                    joiners.append({'name': name, 'tile': list(to), 'from': list(frm), 'group': f'event{n_}', 'when': sentence(c)})
                    if sub:
                        joiners[-1]['standIn'] = {'type': 'ally', 'name': sub, 'note': '', 'when': f"{name} wasn't born"}
        # Where items turn up this chapter, by item type: (type, kind, text). Kinds: shop (the home castle's stock: item instances
        # behind the castle record's pointer), village, castle, hidden, talk, and kit (what a unit carries when it joins you: the
        # item instances in its record, +0x23 for the first generation's records and +9 for the children's).
        found, found_pairs = [], []
        home = locs[0]
        type_of = {v: k for k, v in items.items()}

        def later(kind):
            """A source that counts from the next chapter: what joins, or is given, during or after the battle ('kit-later'); the last
            chapter has no next, so what it gives counts there."""
            return kind if chapter == 11 else f'{kind}-later'

        def gift_words(paths):
            """The flag tests a gift sits behind, in words (', before you seize Isaach'); '' when one way to it tests nothing, and ', on
            a condition' when a test can't be put into words."""
            ways_ = {frozenset(c) for c in paths}
            merged = True
            while merged:  # a test whose two answers both lead to the gift, other tests alike, says nothing
                merged = False
                for w_ in sorted(ways_, key=sorted):
                    for f_, v_ in sorted(w_):
                        twin = (w_ - {(f_, v_)}) | {(f_, not v_)}
                        if twin in ways_:
                            ways_ = (ways_ - {w_, twin}) | {w_ - {(f_, v_)}}
                            merged = True
                            break
                    if merged:
                        break
            if any(not c for c in ways_):
                return ''
            ways = []
            for conds in sorted(ways_, key=sorted):
                parts = []
                for (bank_n, f_), is_set in sorted(conds):
                    c = d.flag(f_, 0) if bank_n == chapter else None
                    if c is None:
                        return ', on a condition'
                    parts.append(('after ' if is_set else 'before ') + c)
                ways.append(' and '.join(parts))
            return ', ' + ' or '.join(dict.fromkeys(ways))

        def gifts_of(action):
            """[(unit id, instance, the gift's conditions in words)] for what an action's scene hands over."""
            by = {}
            for who, i, conds in ev.action_gift_paths(action):
                by.setdefault((who, i), []).append(conds)
            return [(who, i, gift_words(paths)) for (who, i), paths in by.items()]

        for instance in ev.shop_stock(chapter):
            found.append((ev.instance_type(instance), 'shop', f"Sold at {ln.place(places[home[2]])}"))
        # Visits, castle entries and hidden finds are the map's own and count in the chapter; a talk's gift, or one an event during
        # the battle hands over, counts from the next (the home castle's shop open mid-chapter notwithstanding).
        for t in d.triggers:
            a = t['args']
            for who, i, cond in gifts_of(t['action']):
                kind = {0x0A: 'village', 0x07: 'castle', 0x0B: 'hidden'}.get(t['op'], 'talk' if t['op'] in (0x04, 0x15, 0x16) else 'event')
                if kind in ('village', 'castle'):
                    lid = a[2] | a[3] << 8
                    text = ('Visiting ' if kind == 'village' else 'Entering ') + place(lid) + (f" ({unit_name(a[0] | a[1] << 8)})" if (a[0] | a[1] << 8) != 0xFFFF else '')
                elif kind == 'hidden':
                    (x1, y1) = tile(a[2], a[3])
                    text = f"Found by {unit_name(a[0] | a[1] << 8)} at ({x1}, {y1})"
                elif kind == 'talk':
                    frm = a[0] | a[1] << 8
                    text = f"{'Anyone' if frm == 0xFFFF else unit_name(frm)} talks to {unit_name(a[2] | a[3] << 8)}"
                else:
                    c = d.trigger(t)
                    text = f"Given to {unit_name(who)} when {c}" if c and who != 0xFFFF else f"Given to {unit_name(who)} during the chapter"
                text += cond
                if kind == 'talk':
                    pair = {a[0] | a[1] << 8, a[2] | a[3] << 8}
                    if any(k == 'talk' and p == pair and it == ev.instance_type(i) and cond in tx for it, k, tx, p in found_pairs):
                        continue
                    found_pairs.append((ev.instance_type(i), kind, text, pair))
                found.append((ev.instance_type(i), later(kind) if kind in ('talk', 'event') else kind, text))
        # A block's gift (Chapter 9: Charlot's Berserk Staff once Galatia is seized and Charlot has spoken to Hannibal), and one an end
        # scene hands over (Chapter 2's Knight Ring), count from the next chapter.
        for e in events[1:]:
            if e[0] != 'block':
                continue
            for b_ in e[1]:
                for who, i, cond in gifts_of((b_['op'], b_['args'])):
                    c = 'at the end of the chapter' if ends(e[2]) else event_when(e)
                    c = ('on ' + c if c.startswith('turn') else c) if c else 'during the chapter'
                    found.append((ev.instance_type(i), later('event'), f'Given to {unit_name(who)} {c}{cond}'))
        # What a unit carries when it joins you: the item instances in its record (+0x23 for the first generation's records, +9 for
        # the children's), counted once, in the first chapter it joins. One the opening places, or a list the opening loads puts on
        # your side (Arden in the Prologue), counts there; one a trigger or block brings, from the next chapter.
        cmds_by_kind = [('kit', [(op, a) for _, op, a in ev.script(bank_, opening_)])]
        for _, op, a in ev.script(bank_, opening_):
            cmds_by_kind[0][1].extend((x[0], x[1:]) for o, x in ev.action_scene((op, a)) if o in ev.INLINE_OPS and x)
        cmds_by_kind[0][1].extend((0x4A, bytes([k])) for k in opening[chapter])
        for e in events[1:]:
            cmds_by_kind.append((later('kit'), [(o, x) for o, x in e[2] if o != 'walk' and not (ends(e[2]) and o in (0x4A, 0x4F))]))
        for kind, commands in cmds_by_kind:
            for op, a in commands:
                if op in (0x4A, 0x4F) and a:  # a list's records on your side join you with the list
                    idents = [r_[0] | r_[1] << 8 for r_ in lists[a[0]] if r_[6] == 0] if a[0] < len(lists) else []
                elif op == 0x49 or (op == 0x53 and len(a) > 2 and a[2] == 0):
                    idents = [a[0] | a[1] << 8]
                else:
                    continue
                for ident in idents:
                    if ident and playable(ident) and ident not in joined:
                        joined.add(ident)
                        t = character(ident)
                        kit = t[0x23:0x26] if t[0] == 0 else t[9:11]
                        # A child and their substitute carry the same copies: one line for the pair.
                        pair_ = (ident, subs[ident]) if ident in subs else (child_of[ident], ident) if ident in child_of else None
                        who_ = f'{playable(pair_[0])} or {playable(pair_[1])}' if pair_ else playable(ident)
                        for i in kit:
                            if i not in (0, 0xFF):
                                found.append((ev.instance_type(i), kind, f'Carried by {who_} on joining'))
        start_cmds = []
        for _, op, a in ev.script(bank_, opening_):
            start_cmds += ev.action_scene((op, a))
        # The second generation's openings also move Sigurd's id (a scene of the past), so he's left out from Chapter 6 on.
        starting = merge([(playable(i), tuple(to)) for i, (_, to) in placements(start_cmds, opening[chapter]).items()
                          if playable(i) and not (chapter >= 6 and playable(i) == 'Sigurd')])
        for e in events[1:]:
            if not ends(e[2]) or (e[0] == 'trigger' and e[1]['op'] == 0x02):
                continue
            setters = [x for test, fl in (e[1][0]['flags'] if e[0] == 'block' else []) for f_ in fl for x in d.setters.get(f_, [])]
            if setters and all(kind_ == 'trigger' and t_['op'] == 0x02 for kind_, t_ in setters):
                continue  # Chapter 2: seizing Agusty sets the flag the ending waits on
            c = event_when(e)
            if c:
                notes.append(f'The chapter also ends {c}.')

        # An army's stance toward yours that a later event changes (`4D`), on each of its units: "Turns hostile when ...".
        changes = []
        for n_, e in enumerate(events[1:], 1):
            if ends(e[2]):
                continue  # the scene that ends the chapter changes nothing on the battle map
            touched = {x[i_] for o, x in e[2] if o == 0x4D and len(x) >= 3 for i_ in (1, 2)} - {0}
            for a in sorted(touched):
                r_ = relation_set(e[2], a)
                if r_ is not None:
                    # A trigger can fire only while the units it names are on the map: it acts on the army's latest creation.
                    epoch = latest.get(a, 0) if e[0] == 'trigger' else made_at[n_].get(a, 0)
                    changes.append((n_, a, r_, e, epoch))
        # The blocks' changes come first, in their order, then the triggers' (which can fire at any time); changes to one stance in a
        # row are one sentence ("turns hostile after ..., or when Ethlyn is defeated").
        changes.sort(key=lambda c_: c_[3][0] == 'trigger')
        stance = {1: 'hostile', 2: 'friendly', 3: 'neutral'}
        for u in units + [x for g in groups for x in g['units']] + arrivals_:
            a, came = u.pop('_army', None), u.get('_came', 0)
            cur = 3 if u.get('neutral') else 2 if u.get('ally') or u.get('type') == 'ally' else 1
            own = made_at[came].get(a, 0)
            runs = []   # [relation, [whens]]
            for n_, a_, r_, e, epoch in changes:
                if a_ != a or n_ == came or epoch != own:
                    continue
                lists_ = list(dict.fromkeys(x[0] for o, x in e[2] if o in (0x4A, 0x4F) and x))
                arrives = group(lists_) if lists_ else None
                c = (f"when {arrives}" if arrives and e[0] == 'block' else event_when(e)) or 'during the chapter'
                if runs and runs[-1][0] == r_:
                    if c not in runs[-1][1]:
                        runs[-1][1].append(c)
                elif r_ != cur:
                    runs.append([r_, [c]])
                cur = r_
            if runs:
                text = '; '.join(f"turns {stance[r_]} {', or '.join(cs)}" for r_, cs in runs)
                u['note'] = ' '.join(x for x in (u.get('note'), text[0].upper() + text[1:] + '.') if x)
            u['_hostile'] = cur == 1 or any(r_ == 1 for r_, _ in runs)

        # What foes carry and drop, from the units of every army hostile to yours when it comes or once it turns: one standing on the
        # map at the start counts in this chapter, one that arrives mid-chapter from the next ('-later'). What a foe carries is only
        # said where nothing else gives the weapon (main()). A unit the scripts take off the map on turn 1 that none of your units
        # can reach first gives nothing (the Prologue's Gandolf leaves on its enemy phase; his Skill Ring is his Chapter 1 drop).
        gone_early = {x[0] | x[1] << 8 for e in events[1:] if e[0] == 'block' and e[1][0]['turn'] and e[1][0]['turn'][1][0] == 1
                      for o, x in e[2] if o == 0x65 and len(x) >= 2}
        reach = max(R[CLASSES + i * 31 + 0x10] for i in range(72)) + 2   # the longest move, and a bow's or tome's range
        start_tiles = [t_ for _, t_, _ in starting] + [(home[3] + 1, height - home[4])]

        def foe_lines(u, tail, kind):
            if u.get('_id') in gone_early and min(abs(u['tile'][0] - x) + abs(u['tile'][1] - y) for x, y in start_tiles) > reach:
                return
            named = u.get('type', 'ally') in ('boss', 'named', 'ally') and not u.get('generic') and u.get('type') != 'enemy'
            for item in u.get('drops', u.get('_drops', [])):
                found.append((type_of[item], 'drop' + kind, f"Dropped by {u['name'] if named else 'a ' + u['name']}{tail}"))
            for item in dict.fromkeys(u.get('carries', u.get('_carries', []))):
                if item not in u.get('drops', u.get('_drops', [])):
                    found.append((type_of[item], 'foe' + kind, f"Carried by {u['name'] + ', a foe' if named else 'a foe ' + u['name']}{tail}"))

        for u in units:
            if u.pop('_hostile'):
                if u['type'] == 'ally' and u.get('_drops'):
                    u['drops'] = u['_drops']  # it drops it once its army has turned on yours
                foe_lines(u, '', '')
        for g in groups:
            for u in g['units']:
                if u.pop('_hostile'):
                    foe_lines(u, ', arriving mid-chapter', '-later')
        for j in arrivals_:
            if j.pop('_hostile'):
                if j.get('_drops'):
                    j['note'] = ' '.join(x for x in (j.get('note'), f"Drops {' and '.join(article(i) for i in j['_drops'])}.") if x)
                foe_lines(j, ', arriving mid-chapter', '-later')
        # Who leaves the map during the chapter (event commands 0x65 and 0x66, not the unit's own defeat, a scene's cast or the end),
        # and who withdraws after a battle (trigger 0x1A, "A fights B": kind 0x18, raised as a battle starts at $84:B981, runs 0x74).
        leaves = {}   # unit id -> [(the event's index, words)]
        for n_, e in enumerate(events[1:], 1):
            if ends(e[2]):
                continue
            if e[0] == 'trigger' and e[1]['op'] == 0x1A and e[1]['action'] and e[1]['action'][0] == 0x74:
                a_ = e[1]['args']
                foe_ = a_[2] | a_[3] << 8
                leaves.setdefault(a_[0] | a_[1] << 8, []).append((len(events), 'Withdraws after a battle' + ('' if foe_ == 0xFFFF else f' with {unit_name(foe_)}')))
                continue
            if e[0] == 'trigger' and e[1]['op'] in (0x04, 0x15, 0x16):
                talk_ = e[1]['args']
                c = f"when {unit_name(talk_[0] | talk_[1] << 8)} talks to {unit_name(talk_[2] | talk_[3] << 8)}"
            else:
                c = event_when(e)
                c = ('on ' + c if c and c.startswith('turn') else c) or 'during the chapter'
            placed_ = {x[0] | x[1] << 8 for o, x in e[2] if o == 0x49 and len(x) >= 2}
            own = (e[1]['args'][0] | e[1]['args'][1] << 8) if e[0] == 'trigger' and e[1]['op'] == 0x0F else None
            for o, x in e[2]:
                if o in (0x65, 0x66) and len(x) >= 2 and (x[0] | x[1] << 8) not in placed_ | {own}:
                    # A block's removal reaches only the units on the map by then (in the table's order, as the relations are read):
                    # Chapter 1's scene that takes off the Nordion messenger runs before Eldigan's Cavaliers, who share his id, arrive.
                    # A trigger can fire at any time.
                    leaves.setdefault(x[0] | x[1] << 8, []).append((n_ if e[0] == 'block' else len(events), f'Leaves the map {c}'))
        for u in units + [x for g in groups for x in g['units']] + arrivals_:
            said_ = [w for at, w in dict.fromkeys(leaves.get(u.get('_id'), [])) if at >= u.get('_came', 0)
                     and not (u.get('talk') and 'talks to' in w)]
            gone_ = [w[len('Leaves the map '):] for w in said_ if w.startswith('Leaves the map ')]
            fights = [w[len('Withdraws after a battle'):] for w in said_ if w.startswith('Withdraws after a battle')]
            said_ = (([f"Leaves the map {', or '.join(gone_)}"] if gone_ else []) +
                     (['Withdraws after a battle' + ('' if '' in fights else ' with ' + ' or '.join(f[len(' with '):] for f in fights))] if fights else []))
            if said_:
                u['note'] = ' '.join(x for x in (u.get('note'), ' '.join(w + '.' for w in said_)) if x)
        for u in units + [x for g in groups for x in g['units']] + arrivals_:
            for key in ('_id', '_drops', '_carries', '_came'):
                u.pop(key, None)
        joiners += arrivals_
        out[chapter] = (units, groups, {'objects': objects, 'notes': notes, 'end': end, 'found': found, 'joiners': joiners, 'unsure': unsure,
                                        'starting': starting})
    return out


def chapter_records():
    out = []
    for i in range(len(CHAPTERS)):
        p = int.from_bytes(R[CHAPTER_TABLE + 3 * i:CHAPTER_TABLE + 3 * i + 3], 'little')
        out.append(R[rom_offset(p):rom_offset(p) + 27])
    return out


def main():
    names = class_names()
    by_type = {}
    for i, n in names.items():
        by_type.setdefault(R[CLASSES + i * 31 + 0x12], []).append(n)
    costs = {t: list(R[MOVE_COSTS + u16(MOVE_COSTS + 2 * t):][:26]) for t in range(15)}
    avoid = [x - 256 if x > 127 else x for x in R[AVOID:AVOID + 26]]

    cpu = Cpu()
    maps = []
    used_ids = set()
    for (map_id, number, heading, title), rec in zip(CHAPTERS, chapter_records()):
        grid64 = np.frombuffer(cpu.decompress(int.from_bytes(rec[0:3], 'little')), dtype='<u2').reshape(64, 64)
        table = np.frombuffer(cpu.decompress(int.from_bytes(rec[24:27], 'little')), dtype='u1')
        width, height = rec[21] * 16, rec[23] * 16
        terrain = table[grid64[:height, :width] & 0x3FF]
        used_ids |= set(np.unique(terrain).tolist())
        unknown = set(np.unique(terrain).tolist()) - set(TERRAIN)
        assert not unknown, (map_id, unknown)
        rows = [''.join(TERRAIN[t][0] for t in row) for row in terrain.tolist()]
        maps.append({
            'id': map_id, 'route': 'Story', 'chapter': number, 'heading': heading, 'title': title, 'width': width, 'height': height,
            'grid': [encode_row('fe4', r) for r in rows], 'victory': '', 'defeat': '', 'objectives': [], 'units': [], 'starts': [],
            'objects': [], 'changes': [], 'notes': [],
        })

    units = build_units({i: m['height'] for i, m in enumerate(maps)}, names)
    for i, m in enumerate(maps):
        m['units'], groups, events = units[i]
        if groups:
            m['reinforcements'] = groups
        castles = {o['name']: o for o in events['objects'] if o['type'] == 'castle'}
        home = events['objects'][0]
        assert home['type'] == 'castle', m['id']
        final = next(o for o in events['objects'] if o['type'] == 'castle' and 'wins the chapter' in o.get('note', ''))
        lord = LORDS[CHAPTERS[i][1]]
        m['victory'] = f"Seize {final['name']} with {lord}"
        m['defeat'] = f"{lord} is defeated, or the enemy seizes {home['name']}"
        m['objectives'] = [{'type': 'seize', 'tiles': [final['tile']], 'label': f"Seize {final['name']}"}]
        starting = events['starting']
        lord_tile = next((t for n, t, _ in starting if n == lord), None)
        if starting:
            # Those the opening places, and the home castle, where the rest (the lord too, when it isn't placed) start.
            m['starts'] = [list(t) for _, t, _ in starting] + ([] if lord_tile else [home['tile']])
            m['forced'] = [{'name': n, 'tile': list(t), **({'standIn': {'name': s_, 'when': f"{n} wasn't born"}} if s_ else {})}
                           for n, t, s_ in starting if n != lord]
        else:
            m['starts'] = [home['tile']]
        m['corrinStart'] = list(lord_tile) if lord_tile else home['tile']
        m['lord'] = lord
        if events['joiners']:
            m['joiners'] = events['joiners']
        # A village covers several tiles and visiting any of them counts, so its contents go on each: the footprint the game checks a
        # unit against (the location kind's record at $87:F453: x - 1 to x + 1 and the row above, for a village).
        codes = [[row[2 * i:2 * i + 2] for i in range(m['width'])] for row in m['grid']]
        objects = []
        for o in events['objects']:
            if o['type'] != 'village':
                objects.append(o)
                continue
            x0, y0 = o['tile']
            tiles = [(x, y) for y in (y0, y0 + 1) for x in (x0 - 1, x0, x0 + 1)]
            assert all(codes[m['height'] - y][x - 1] == 'oc' for x, y in tiles), (m['id'], o['tile'])
            objects += [{**o, 'tile': [x, y]} for x, y in tiles]
        m['objects'] = objects
        start_note = (f"Your army starts in {home['name']}, your home castle." if not starting else
                      f"The rest of your army starts in {home['name']}, your home castle.")
        # Joiners with a tile are on the map; their join notes would say it twice.
        drawn = {j['name'] for j in events['joiners'] if not j.get('ally')}

        def said_elsewhere(n):
            if ' your army: ' not in n or 'talks to' in n:
                return False
            who = n.split(' your army: ')[0].rsplit(' join', 1)[0]
            names = [x.strip().split(' or ')[0] for part in who.split(' and ') for x in part.split(',') if x.strip()]
            return all(x in drawn for x in names)
        m['notes'] = [start_note] + [n for n in events['notes'] if not said_elsewhere(n)]
        if events['unsure']:
            m['unconfirmed'] = list(dict.fromkeys(events['unsure']))
        assert len(castles) == sum(1 for o in events['objects'] if o['type'] == 'castle'), m['id']

    # One terrain entry per code: ids that share a code (Peak and Cliff) must agree.
    info = {}
    for tid, (letter, name) in TERRAIN.items():
        if tid not in used_ids:
            continue
        code = encode_row('fe4', letter)
        move = {}
        for types, label in MOVE_GROUPS:
            col = {costs[t][tid] for t in types}
            assert len(col) == 1, (tid, label, col)
            c = col.pop()
            move[label] = None if c == 0x80 else (0.7 if c == 0 and tid in (15, 25) else c)
        entry = {'name': name, 'def': 0, 'avo': avoid[tid], 'heal': 0, 'move': move}
        if code in info:
            assert {k: v for k, v in info[code].items() if k != 'name'} == {k: v for k, v in entry.items() if k != 'name'}, (code, tid)
            info[code]['name'] = info[code]['name'] + ' / ' + name.lower()
        else:
            info[code] = entry
    info['ol']['note'] = ("The castle itself: units move in and out with the castle command (the movement table gives it no cost), a "
                          "boss defends it from inside, and the lord seizes it.")
    info['oj']['note'] = 'A unit that stops here can be healed for gold (Serenes Forest: 5 gold per HP).'
    info['tl']['note'] = "The table holds 0 for every walker; the page shows Serenes Forest's 0.7."
    info['tb']['note'] = info['tl']['note']

    examples = {}
    for types, label in MOVE_GROUPS:
        examples[label] = ', '.join(sorted({n for t in types for n in by_type.get(t, [])}))

    lines = [
        "import type { TerrainInfo } from '../maps/fatesTerrain'",
        "import type { TerrainCode } from '../maps/terrainCodes'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's movement cost and avoid tables. Do not edit by hand.",
        ' */',
        '',
        "/** Movement types the game gives different costs: classes in a group pay the same on every terrain. */",
        'export const FE4_MOVE_CLASSES = ' + json.dumps([label for _, label in MOVE_GROUPS]) + ' as const',
        '',
        'export const FE4_MOVE_CLASS_EXAMPLES: Record<string, string> = ' + json.dumps(examples, indent=2, ensure_ascii=False),
        '',
        '/** Avoid and movement cost (null = can\'t enter) by terrain code. No Def bonus is listed: the Serenes damage formula mentions one, but no table for it is found in the ROM. */',
        'export const FE4_TERRAIN: Partial<Record<TerrainCode, TerrainInfo>> = {',
    ]
    for code, entry in info.items():
        lines.append(f'  {code}: {json.dumps(entry, ensure_ascii=False)},')
    lines.append('}')
    with open(os.path.join(OUT_DIR, 'fe4Terrain.ts'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    lines = [
        "import type { ChapterMap } from '../maps/types'",
        "import { FE4_TERRAIN } from './fe4Terrain'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's own chapter records. Do not edit by hand.",
        ' */',
        '',
        'const RAW = [',
    ]
    lines += ['  ' + json.dumps(m, ensure_ascii=False) + ',' for m in maps]
    lines += [']', '', 'export const FE4_MAPS: ChapterMap[] = (RAW as unknown as ChapterMap[]).map((m) => ({ ...m, terrain: FE4_TERRAIN }))']
    with open(os.path.join(OUT_DIR, 'fe4Maps.ts'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    # Where each item turns up, by chapter: read by the weapon page for the spoiler block and its source lines.
    item_names = ln.item_names()
    sources = {}
    for i, m in enumerate(maps):
        for itype, kind, text in units[i][2]['found']:
            entry = {'mapId': m['id'], 'kind': kind, 'text': text}
            lst = sources.setdefault(item_names[itype], [])
            if entry not in lst:
                lst.append(entry)
    # What a foe carries is only said where nothing else gives the item: a foe holds item types, not one of the 140 copies the game
    # tracks ($83:F489), and Steal takes only gold ($84:EAD9), so a weapon no copy exists of is the foes' alone.
    for name, lst in sources.items():
        if any(not s_['kind'].startswith('foe') for s_ in lst):
            lst[:] = [s_ for s_ in lst if not s_['kind'].startswith('foe')]
    lines = [
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's event scripts and shop lists. Do not edit by hand.",
        ' */',
        '',
        "/** Where an item turns up: the chapter (a map id), how (the home castle's shop, a village, entering a castle, a hidden find,",
        " * a talk, an event, what a unit carries when it joins, or what a foe drops or carries), and in words. A kind ending in '-later'",
        " * counts from the next chapter: a unit that arrives mid-chapter, a talk's or an event's gift, a recruit's own items. */",
        "export interface Fe4ItemSource {",
        "  mapId: string",
        "  kind: 'shop' | 'village' | 'castle' | 'hidden' | 'talk' | 'talk-later' | 'event' | 'event-later' | 'kit' | 'kit-later' | 'foe' | 'foe-later' | 'drop' | 'drop-later'",
        "  text: string",
        "}",
        '',
        'export const FE4_ITEM_SOURCES: Record<string, Fe4ItemSource[]> = ' + json.dumps(sources, indent=2, ensure_ascii=False),
    ]
    with open(os.path.join(OUT_DIR, 'fe4ItemSources.ts'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', len(maps), 'maps;', len(info), 'terrain codes;', sorted(used_ids))
    for i, m in enumerate(maps):
        print(i, m['heading'], 'units', len(m['units']), 'groups', len(m.get('reinforcements', [])), 'named', [u['name'] for u in m['units'] if u['type'] in ('boss', 'named')])


if __name__ == '__main__':
    main()

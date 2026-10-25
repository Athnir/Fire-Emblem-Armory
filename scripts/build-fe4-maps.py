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
from fe4_rom import R, u16  # noqa: E402
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


def opening_relations(cpu, bank, y):
    """From a chapter's opening script: {army: its relation to your army} (1 hostile, 2 friendly, 3 neutral). The script's
    `4b army x` commands name the armies and its `4d relation army other` commands say how each stands to the others."""
    armies, relation = set(), {}
    for _ in range(80):
        o = rom_offset(bank << 16 | y)
        op = R[o]
        if op == 0x30 or R[o:o + 2] == bytes([0xFF, 0xFF]):
            break
        n = cpu.script_skip(bank, y)
        args = R[o + 1:o + (n - y)]
        if op == 0x4B:
            armies.add(args[0])
        elif op == 0x4D and args[2] == 0:
            relation[args[1]] = args[0]
        y = n
    assert 0 in armies, (bank, hex(y))
    return {a: relation.get(a) for a in armies if a != 0}


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


RECRUITMENT = 'https://serenesforest.net/genealogy-of-the-holy-war/characters/recruitment/'


def substitutes(rename=lambda n: n):
    """{name: the other}: the second generation's substitutes and the children they stand in for, from Serenes' recruitment page
    ('Tristan/Delmud'), passed through `rename`. The scripts place both; only one exists in a given game."""
    req = urllib.request.Request(RECRUITMENT, headers={'User-Agent': 'Mozilla/5.0'})
    text = html.unescape(re.sub(r'<.*?>', ' ', urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')))
    out = {}
    for a, b in re.findall(r'\b([A-Z][a-z]+)/([A-Z][a-z]+)\b', text):
        a, b = rename(a), rename(b)
        out[a], out[b] = b, a
    return out


def names_list(names, pairs):
    """Names joined for a sentence, a substitute and the child it stands in for as 'Dimna / Lester'; also how many there are."""
    out, seen = [], set()
    for n in names:
        if n in seen:
            continue
        other = pairs.get(n)
        if other in names:
            out.append(f'{n} / {other}')
            seen |= {n, other}
        else:
            out.append(n)
            seen.add(n)
    return (', '.join(out[:-1]) + ' and ' + out[-1]) if len(out) > 1 else out[0], len(out)


def village_gold():
    return u16(VILLAGE_GOLD + u16(VILLAGE_GOLD + 4))


def article(item):
    return ('an ' if item[0] in 'AEIOU' else 'a ') + item


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

    pairs = substitutes(english)
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

    out = {}
    for chapter, (bank, y) in sorted(chapter_headers().items()):
        relation = opening_relations(cpu, bank, y)
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
        # boss table. When more units fit a row than the table has names, only the flagged leaders take the name.
        candidates = {}
        for k in owned[chapter]:
            for rec in lists[k]:
                d = info(rec)
                if d and d[4] in relation and relation[d[4]] == 1:
                    cls, level, _ = fields(d[5])
                    if level is not None and d[5][0] != 0 and (d[5][0] != 3 or d[3] in (1, 254, 255)):
                        candidates.setdefault((norm(SERENES_CLASSES.get(cls, '')), level), []).append(d)
        names_for, name_of_id = {}, {}
        for key, found in candidates.items():
            row_names = sorted({r[1] for r in rows if r[3] == key[1] and norm(r[2]) == key[0] and r[1] not in fan_to_ln})
            if not row_names:
                continue
            leaders = [d for d in found if d[3] == 1]
            use = found if len(found) <= len(row_names) else leaders if 0 < len(leaders) <= len(row_names) else []
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

        def make(rec):
            d = info(rec)
            if not d:
                return None
            ident, x, ty, flag, army_, t = d
            if army_ not in relation:
                return None  # your own army's placements aren't shown yet
            cls, level, carried = fields(t)
            klass = classes.get(cls, f'Class {cls}')
            if relation[army_] != 1:
                named = playable(ident)
                u = {'type': 'ally', 'name': named or klass, 'tile': [x + 1, height - ty]}
                if not named:
                    u['generic'] = True
                if relation[army_] == 3:
                    u['note'] = 'Neutral: no army is hostile to it.'
                return u
            u = {'type': 'enemy', 'name': klass, 'tile': [x + 1, height - ty]}
            name = (playable(ident) if t[0] in (0, 1) else None) or names_for.get((ident, x, ty))
            if name:
                u['name'] = name
                u['type'] = 'boss' if flag == 1 else 'named'
                u['note'] = f'{klass}, Lv {level}' if level is not None else klass
            elif level is not None:
                u['note'] = f'Lv {level}'
            if carried:
                u['carries'] = [items.get(i, f'Item {i}') for i in carried if i != 0xFF]
            dropped = drop(t)
            if dropped:
                u['drops'] = [dropped]
            return u

        # Lists no script loads are left out (Chapter 8's list 40, Asaello alone): leftover data, like the unused maps.
        loaded = ev.loaded_lists(chapter)
        later = [k for k in owned[chapter] if k not in opening[chapter] and k in loaded and any(map(make, lists[k]))]
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

        # When each later group arrives: the trigger or block whose scene loads it.
        when = {}
        for t in d.triggers:
            c = d.trigger(t)
            for k in ev.action_lists(t['action']):
                if c:
                    when.setdefault(k, []).append('when ' + c)
        for b in d.blocks:
            c = d.when(b)
            if c and b['turn'] is None:
                c = 'after ' + c  # a block on flags alone runs as soon as they're set
            for k in ev.action_lists((b['op'], b['args'])):
                if c:
                    when.setdefault(k, []).append(c)

        units, groups = [], []
        for k in owned[chapter]:
            made = [u for u in map(make, lists[k]) if u]
            if k in opening[chapter]:
                units += made
            elif made and k in label_of:
                text = ' or '.join(dict.fromkeys(when[k])) if k in when else None
                groups.append({'id': f'list{k}', 'label': label_of[k],
                               'when': sentence(text) if text else 'Arrives during the chapter; what triggers it has not been read yet.',
                               'units': made})

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
                    n.append(f"{who or 'Anyone'} entering it receives {' and '.join(g)}.")
                if n:
                    o['note'] = ' '.join(n)
                objects.append(o)
            else:
                o = {'type': 'village', 'tile': [x + 1, height - ly], 'reward': f'{gold} gold'}
                n = [f"Visited by {who}: {', '.join(g)} as well." if who else f"Also gives {' and '.join(article(i) for i in g)}." for who, g in gifts]
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
        talks = {}
        for t in d.triggers:
            if t['op'] not in (0x04, 0x15, 0x16):
                continue
            a = t['args']
            frm, to = a[0] | a[1] << 8, a[2] | a[3] << 8
            cmds = [x for op, x in ev.action_scene(t['action']) if op in ev.INLINE_OPS and x]
            joins = [unit_name(x[1] | x[2] << 8) for x in cmds if x[0] == 0x53 and x[3] == 0]
            speaker = 'Anyone' if frm == 0xFFFF else unit_name(frm)
            results, given = [], {}
            for who, i in ev.action_gifts(t['action']):
                given.setdefault(speaker if who == 0xFFFF else unit_name(who), []).append(article(item_name(i)))
            branches = any(op in (0x03, 0x04, 0x05, 0x06) for op, _ in ev.action_scene(t['action']))
            for receiver, gifts in given.items():
                # Two gifts in a scene that branches are alternatives (Yuria's Aura or Resire, Serenes: "only one can be obtained").
                results.append(f"{receiver} receives {(' or ' if branches else ' and ').join(gifts)}")
            if joins:
                text, n = names_list(joins, pairs)
                results.append(f"{text} join{'s' if n == 1 else ''} your army")
            if results:
                key = frozenset((speaker, unit_name(to)))
                prior = talks.get(key)
                arriving = [n for n in (speaker, unit_name(to)) if n in later_names]
                opener = prior[0] if prior else f"{speaker} talks to {unit_name(to)}" + (f" (once {arriving[0]} appears on the map)" if arriving else '')
                talks[key] = (opener, list(dict.fromkeys((prior[1] if prior else []) + results)))
        for opener, results in talks.values():
            notes.append(f"{opener}: {'; '.join(results)}.")
        for b in d.blocks:
            # Event command 0x49 puts a unit on the map: a playable character joins you; anyone else (Alvis, Julius) appears.
            placed = [x[1] | x[2] << 8 for op, x in ev.action_scene((b['op'], b['args'])) if op in ev.INLINE_OPS and x[:1] == b'\x49']
            c = d.when(b)
            if not c:
                continue
            arrive = list(dict.fromkeys(unit_name(i) for i in placed if playable(i)))
            others = list(dict.fromkeys(unit_name(i) for i in placed if not playable(i) and not unit_name(i).startswith('the ')))
            if arrive:
                text, n = names_list(arrive, pairs)
                notes.append(f"{text} join{'s' if n == 1 else ''} your army: {c}.")
            if others:
                text, n = names_list(others, pairs)
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
            """[(name, ...rest)] with a substitute and the child it stands in for on the same tile joined as 'Deimne / Lester'."""
            out = []
            for e_ in entries:
                twin = next((o for o in out if pairs.get(e_[0]) in o[0].split(' / ') and o[1:] == e_[1:]), None)
                if twin:
                    out[out.index(twin)] = (f"{twin[0]} / {e_[0]}",) + twin[1:]
                else:
                    out.append(e_)
            return out

        bank_, opening_, _ = ev.chapter_headers()[chapter]
        joiners = []
        for b in d.blocks:
            cmds = ev.action_scene((b['op'], b['args']))
            placed = [x[1] | x[2] << 8 for op, x in cmds if op in ev.INLINE_OPS and x[:1] == b'\x49']
            moves = placements(cmds, ev.action_lists((b['op'], b['args'])))
            c = d.when(b)
            group_id = f"scene{b['args'][1] | b['args'][2] << 8}" if b['op'] == 0x30 else 'block'
            here = [(playable(i), tuple(moves[i][1]), tuple(moves[i][0])) for i in placed if playable(i) and i in moves]
            for name, to, frm in merge(here):
                if c:
                    joiners.append({'name': name, 'tile': list(to), 'from': list(frm), 'group': group_id, 'when': c[0].upper() + c[1:] + '.'})
        # Where items turn up this chapter, by item type: (type, kind, text). Kinds: shop (the home castle's stock: item instances
        # behind the castle record's pointer), village, castle, hidden, talk, and kit (what a unit carries when it joins you: the
        # item instances in its record, +0x23 for the first generation's records and +9 for the children's).
        found, found_pairs = [], []
        home = locs[0]
        type_of = {v: k for k, v in items.items()}
        for u in units:
            for item in u.get('drops', []):
                found.append((type_of[item], 'drop', f"Dropped by {u['name'] if u['type'] in ('boss', 'named') else 'a ' + u['name']}"))
            if u['type'] in ('boss', 'named'):
                for item in dict.fromkeys(u.get('carries', [])):
                    found.append((type_of[item], 'foe', f"Carried by {u['name']}, a foe"))
        for g in groups:  # a foe that arrives mid-chapter: what it drops counts from the next chapter, once it's been seen
            for u in g['units']:
                for item in u.get('drops', []):
                    found.append((type_of[item], 'drop-later', f"Dropped by {u['name'] if u['type'] in ('boss', 'named') else 'a ' + u['name']} ({g['label']})"))
        for instance in ev.shop_stock(chapter):
            found.append((ev.instance_type(instance), 'shop', f"Sold at {ln.place(places[home[2]])}"))
        for t in d.triggers:
            a = t['args']
            for who, i in ev.action_gifts(t['action']):
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
                    text = d.trigger(t) or 'An event'
                if kind == 'talk':
                    pair = {a[0] | a[1] << 8, a[2] | a[3] << 8}
                    if any(k == 'talk' and p == pair and it == ev.instance_type(i) for it, k, _, p in found_pairs):
                        continue
                    found_pairs.append((ev.instance_type(i), kind, text, pair))
                found.append((ev.instance_type(i), kind, text))
        joined = set()
        commands = [(op, a) for _, op, a in ev.script(bank_, opening_)]
        for _, op, a in ev.script(bank_, opening_):
            commands += [(x[0], x[1:]) for o, x in ev.action_scene((op, a)) if o in ev.INLINE_OPS and x]
        for t in d.triggers:
            commands += [(x[0], x[1:]) for o, x in ev.action_scene(t['action']) if o in ev.INLINE_OPS and x]
        for b in d.blocks:
            commands += [(x[0], x[1:]) for o, x in ev.action_scene((b['op'], b['args'])) if o in ev.INLINE_OPS and x]
        for op, a in commands:
            if op == 0x49 or (op == 0x53 and len(a) > 2 and a[2] == 0):
                ident = a[0] | a[1] << 8
                if playable(ident) and ident not in joined:
                    joined.add(ident)
                    t = character(ident)
                    kit = t[0x23:0x26] if t[0] == 0 else t[9:11]
                    for i in kit:
                        if i not in (0, 0xFF):
                            found.append((ev.instance_type(i), 'kit', f'Carried by {playable(ident)} on joining'))
        start_cmds = []
        for _, op, a in ev.script(bank_, opening_):
            start_cmds += ev.action_scene((op, a))
        # The second generation's openings also move Sigurd's id (a scene of the past), so he's left out from Chapter 6 on.
        starting = merge([(playable(i), tuple(to)) for i, (_, to) in placements(start_cmds, opening[chapter]).items()
                          if playable(i) and not (chapter >= 6 and playable(i) == 'Sigurd')])
        out[chapter] = (units, groups, {'objects': objects, 'notes': notes, 'end': end, 'found': found, 'joiners': joiners,
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
        lord_tile = next((t for n, t in starting if n == lord), None)
        if starting:
            # Those the opening places, and the home castle, where the rest (the lord too, when it isn't placed) start.
            m['starts'] = [list(t) for _, t in starting] + ([] if lord_tile else [home['tile']])
            m['forced'] = [{'name': n, 'tile': list(t)} for n, t in starting if n != lord]
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
        m['notes'] = [start_note] + [n for n in events['notes'] if not (' your army: ' in n and 'talks to' not in n)]
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
    lines = [
        '/*',
        " * GENERATED by scripts/build-fe4-maps.py from Genealogy of the Holy War's event scripts and shop lists. Do not edit by hand.",
        ' */',
        '',
        "/** Where an item turns up: the chapter (a map id), how (the home castle's shop, a village, entering a castle, a hidden find,",
        " * a talk, or what a unit carries when it joins), and in words. */",
        "export interface Fe4ItemSource {",
        "  mapId: string",
        "  kind: 'shop' | 'village' | 'castle' | 'hidden' | 'talk' | 'kit' | 'foe' | 'drop' | 'drop-later' | 'event'",
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

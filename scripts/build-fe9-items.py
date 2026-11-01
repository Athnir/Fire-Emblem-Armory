"""
Builds src/data/fe9/fe9Weapons.ts from Path of Radiance's own item table (FE8Data.bin) and text
(Mess/common.m): every weapon's rank, Mt, Hit, Crit, Wt, range, uses, worth, weapon EXP, stat bonuses,
what it's effective against and its special rules. Weapons the game never names (cut content) are
left out. The forge's base weapons, and the chapters they're offered in, come from shop/shopitem_*.bin.
Run:  python scripts/build-fe9-items.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe9_files import GameData, read_shop, read_text  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe9', 'fe9Weapons.ts')
RECORD = 96

CATEGORY = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'bow': 'Bow', 'knife': 'Knife',
            'flame': 'Fire', 'thunder': 'Thunder', 'wind': 'Wind', 'fang': 'Strike'}
# What a weapon is effective against (its record's target fields). Axes also target breakable doors and walls: attacking
# one, the program builds a stand-in unit of a class with that attribute (main.dol 0x801a9c74), so axes deal Mt x2 to them.
TARGETS = {'fly': 'flying', 'armor': 'armour', 'knight': 'horseback', 'beast': 'beast', 'dragon': 'dragon', 'alize': 'laguz',
           'doorbreak': 'doors and walls'}
# A weapon's second type (record +16) decides its damage: fire, thunder, wind or light ('rod') adds Mag, and the target
# defends with Res (main.dol 0x8001ddc4, 0x801a90f4, 0x801a9150). The triangle reads it too (0x801a609c), so the Flame Lance
# counts as fire there. A tome's second type is its own; on another weapon it makes that weapon magic.
MAGIC = {'flame': 'fire', 'thunder': 'thunder', 'wind': 'wind', 'rod': 'light'}
# Laguz strikes share three names in the game ("Claw", "Breath", "Beak"); each is told apart by its class's name.
STRIKE_CLASS = {'IID_LIONNAIL': 'MJID_LION', 'IID_TIGERNAIL': 'MJID_TIGER', 'IID_CATNAIL': 'MJID_CAT',
                'IID_WHITEBREATH': 'MJID_WHITEDRAGON', 'IID_REDBREATH': 'MJID_REDDRAGON', 'IID_HAWKBEAK': 'MJID_HAWK',
                'IID_CROWBEAK': 'MJID_CROW', 'IID_HAWKBEAK_KING': 'MPID_TIBARN', 'IID_CROWBEAK_KING': 'MPID_NAESALA'}
# What the story takes away again: the Prologue's ending deletes Ike's first item (the Trainer) and gives him an Iron Sword
# (C01 handler 19: UnitDelItem(0), UnitAddItem(IID_IRONSWORD)). Mist's spare Trainer, if he throws his away, isn't a gift.
TAKEN_AWAY = {'IID_PRACTICESWORD': 'The Prologue only: its ending swaps it for an Iron Sword'}
# Rule flags, as the app words them. Flags not listed here don't change how the weapon plays.
RULES = {
    # Path of Radiance's Brave weapons hit twice in a row every time, attacking or countering.
    'twice': 'Strikes twice in a row, when attacking and when countering',
    'poison': 'Poisons on contact',
    'crit0': "Can't land critical hits",
    # At 2 range or more (0x801a6e6c) the three blades' and the two magic swords' flags clear the wielder's attack skills for
    # that battle (0x801a85f4). Their magic damage is their second type's doing (MAGIC).
    'magsw': "At 2 range, the wielder's Aether, Astra, Luna, Sol, Flare, Colossus, Deadeye, Stun and Lethality can't trigger",
    'stormsw': "At 2 range, the wielder's Aether, Astra, Luna, Sol, Flare, Colossus, Deadeye, Stun and Lethality can't trigger",
    'resire': 'Restores HP equal to the damage dealt',
    'sealcrit': 'Negates critical hits against the wielder (except Wrath)',
    # The Black Knight's and King Daein's classes have SID_WEAK_A: weapons without this flag deal them no damage (0x801a8c60).
    # Ragnell, the lion's claws and the dragons' breath have it.
    'weakA': "Can damage units under the goddess's blessing (the Black Knight, and Ashnard as King Daein)",
    # Only Rolf has SID_EQ_A and only Elincia SID_EQ_B, the skills these flags need.
    'eqA': 'Rolf only',
    'eqB': 'Elincia only',
    'fang': "A laguz's own attack: it can't be unequipped or dropped",
    'heroonly': 'Ike only',
    'blackonly': 'The Black Knight only',
    'finalonly': 'Ashnard only',
    'shootonly': 'Archers and Snipers only',
    # Stops counters both ways (0x801a99e8): the target can't counter it, and it can't be used to counter. Only the ballistae
    # (flag 'sh') skip the wielder's stat; the siege tomes add Mag as usual.
    'longfar': "Can't be countered, and can't counter",
    'areaattack': 'Also hits units around the target',
    'absolutehit': 'Always hits',
    'valuable': "Can't be sold",
}
# Named in the game but only obtainable with cheat codes (Serenes Forest's FE9 weapon tables), so left out. Rexflame and the
# Venin Lance are held only on a leftover test map (zmap/Map6) and Rexcalibur only by Soren's preset entries; no script gives them.
CODES_ONLY = {'Devil Axe', 'Urvan', 'Bright Bow', 'Rexflame', 'Venin Lance', 'Rexcalibur'}
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']
RANKS = {'E', 'D', 'C', 'B', 'A', 'S'}
# The NA release's difficulties: Easy and Normal share shopitem_n, Hard is shopitem_h (shopitem_m is the
# Japanese release's Maniac mode).
DIFFICULTIES = {'normal': 'n', 'hard': 'h'}
# Bases (and the forge) open before chapter 8, whose shop tables are file number 9 (MCT09).
FIRST_BASE = 9


def chapter_label(text, n):
    """9 -> 'Ch.8', 29 -> 'Ch.27-2', 31 -> 'Endgame' (the chapter title before its colon)."""
    return text[f'MCT{n:02d}'].split(':')[0]


# Chapter 17 is four maps (fe9-17-1 to fe9-17-4); a first appearance there counts from the first.
SECTIONED = {'fe9-17': 'fe9-17-1'}


def chapter_id(text, n):
    """9 -> 'fe9-8': the map page's id for chapter file number n, so the app can tell when a chapter is reached."""
    cid = 'fe9-' + chapter_label(text, n).lower().replace('ch.', '').replace(' ', '')
    return SECTIONED.get(cid, cid)


def availability(text, tables):
    """({IID: {'normal': 'Ch.8 onward', 'hard': ...}}, {IID: {'normal': [9, 10, ...], 'hard': [...]}}): the bases
    whose `tables` offer each item, as the text the app shows and as chapter file numbers. A table is
    (name prefix, step): the shops list IIDs, the forge (IID or 0, material) pairs."""
    out, at = {}, {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        # A chapter with nothing in its shops has no base before it (Ch.27-2 follows straight on from 27).
        bases = [n for n in range(FIRST_BASE, 32) if any(isinstance(x, str) for x in shop.get(f'WSHOP_ITEMS_C{n:02d}', []))]
        offered = {}
        for n in bases:
            for prefix, step in tables:
                for iid in shop.get(f'{prefix}_C{n:02d}', [])[0::step]:
                    if isinstance(iid, str) and n not in offered.get(iid, []):
                        offered.setdefault(iid, []).append(n)
        for iid, chapters in offered.items():
            at.setdefault(iid, {})[key] = list(chapters)
            # Runs of consecutive bases: 'Ch.8–11, 13, 20 onward'.
            runs, start = [], 0
            for i in range(1, len(chapters) + 1):
                if i == len(chapters) or bases.index(chapters[i]) != bases.index(chapters[i - 1]) + 1:
                    first, last = chapters[start], chapters[i - 1]
                    a, b = chapter_label(text, first), chapter_label(text, last)
                    if first == last:
                        runs.append(a)
                    elif last == bases[-1]:
                        runs.append(f'{a} onward')
                    else:
                        runs.append(f"{a}–{b[3:] if a.startswith('Ch.') and b.startswith('Ch.') else b}")
                    start = i
            # 'Ch.' once, at the front of the list.
            out.setdefault(iid, {})[key] = ', '.join(r if k == 0 else r.removeprefix('Ch.') for k, r in enumerate(runs))
    # Offered on one difficulty only: '' on the other.
    return ({iid: {key: d.get(key, '') for key in DIFFICULTIES} for iid, d in out.items()},
            {iid: {key: d.get(key, []) for key in DIFFICULTIES} for iid, d in at.items()})


# Script calls that hand an item over: chests and villages, gifts and rewards, the desert's buried items.
GIVES = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub', 'UnitAddItem', 'GetRndTreasure')


def obtainable(shop, forge, staves, tomes):
    """Every IID you can get in the story: sold (shop, forge), handed over by a chapter script (chests,
    villages, gifts, buried items), dropped by a foe, carried by someone who joins your army (a
    character placed in a mikata group), or stolen. Steal takes anything a foe hasn't equipped (the
    tutorial, tut.m MS_T11盗む_01/04: Spd and Str each 1 above the target's Spd and the item's Wt). A foe
    with two weapons unequips one whenever it fights with the other, so only a foe's lone weapon stays
    theirs unless it drops. The trial maps keep
    nothing, so they don't count."""
    import importlib.util
    from fe9_cmb import Script
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    got = set(shop) | set(forge)
    for n in range(1, 32):
        script = Script(f'C{n:02d}.cmb')
        for h in script.handlers():
            got |= {a for fn, args in maps.calls(script, h) if fn in GIVES for a in args if isinstance(a, str) and a.startswith('IID_')}
    placed = [(group, u) for n in range(1, 32) for code in ('n', 'h', 'c')
              for group, units in maps.dispos(f'bmap{n:02d}', code).items() for u in units]
    # Your own units' gear comes from where each joins (kit(), added in main()).
    for group, u in placed:
        if debug_group(group):
            continue
        # A laguz's own attack can't be unequipped, so Steal never takes it (a Kilvas raven's Beak beside its Dagger).
        arms = [w for w in u['weapons'] if w not in staves and w not in class_strikes().values()]
        loose = len(arms) > 1 or (arms and arms[0] in tomes and u['items'])
        got |= set(u['drops']) | set(u['items']) | (set(arms) if loose else set())
    return got


_STRIKES = {}


def class_strikes():
    """{JID: IID}: the laguz classes' own attacks. FE8Data.bin pairs each such class with its weapon (a JID pointer followed by
    an IID pointer): the beast tribes' claws, the dragons' breath, the bird tribes' beaks, Tibarn's and Naesala's own."""
    import struct
    if _STRIKES:
        return _STRIKES
    g = GameData()
    out = _STRIKES
    for o in range(g.B, len(g.d) - 8, 4):
        a, b = struct.unpack_from('>2I', g.d, o)
        ja, ib = g.string(a) if a else None, g.string(b) if b else None
        if ja and ib and ja.startswith('JID_') and ib.startswith('IID_'):
            out[ja] = ib
    return out


# What a chapter script hands over, as the player sees it: a gift or reward (UnitGetItemShowing, MindGetItem). Handler
# kind 14 is a base conversation; kinds 4 and 5 are the tiles and areas of chests, villages and buried items, which the
# map data already lists. A chapter's opening can hand an item over quietly (UnitAddItem: Ike's Ragnell); anywhere else
# UnitAddItem fills a unit's own kit, which isn't a gift.
SHOWN = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub')
BASE_CONVERSATION = 14
MAP_EVENTS = (4, 5)


def given():
    """({IID: [chapter file numbers]}, {IID: [...]}): what base conversations give, and what the chapters' own scripts
    hand over outside the chests and villages (Path of Radiance's Regal Sword, Vague Katti)."""
    import importlib.util
    from fe9_cmb import Script
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    base, gift = {}, {}
    for n in range(1, 32):
        script = Script(f'C{n:02d}.cmb')
        # Units the chapter places on another side: what the setup gives them is theirs (Shinon's Brave Bow in Ch.18, which
        # he drops; the Steel Lance Gatrie gets in Ch.13 if he came back with no weapon), not a gift to your army.
        others = {u['pid'] for code in ('c', 'n', 'h') for us in maps.dispos(f'bmap{n:02d}', code).values()
                  for u in us if u['side'] != 0}
        for h in script.handlers():
            if h['kind'] in MAP_EVENTS or h['i'] in maps.callees(script):
                continue
            into = base if h['kind'] == BASE_CONVERSATION else gift
            # A gift before the battle (a base conversation, an opening) is the chapter's; one at its end or from an event
            # during it (the Mend Rhys gets after Ch.6, the Ashera Staff after Ch.22) is the next chapter's.
            at = n if h['kind'] == BASE_CONVERSATION or h['name'].startswith('Opening') else n + 1
            if at > 31:
                continue
            pid = None  # the unit a plain UnitAddItem goes to: the one the handler last fetched
            for fn, args in maps.calls(script, h):
                if fn == 'UnitGetByPID' and args:
                    pid = args[0]
                added = fn == 'UnitAddItem' and (h['name'].startswith('Opening') or h['kind'] == 1) and pid not in others
                for a in args if fn in SHOWN or added else ():
                    if isinstance(a, str) and a.startswith('IID_') and at not in into.setdefault(a, []):
                        into[a].append(at)
    return base, gift


def debug_group(name):
    """The rosters the openings place only when a chapter is started from the debug menu with no army (inside
    `if (!get("DBG_最初からやってる") && ForceGetCount(5) == 0)`, "dispos for debug"): their gear is no one's."""
    return bool(re.search(r'_mikata_[nhm]$', name)) or name.startswith('always_dbg')


def kit():
    """{IID: [chapter file numbers]}: the gear each of your units brings, counted once, in the chapter it first joins: the
    deployment roster it first appears in (`bmapNN_mikata_c`), a group placed on your side, a Join() from the shared roster
    (zmap/always: Calill in a base conversation), or a unit an opening hands over (Mist and Rolf in Ch.9) are yours from that
    chapter; a recruit who joins during the battle (a talk, or the end) is yours from the next, the first base they're at."""
    import importlib.util
    from fe9_cmb import Script
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    always = maps.dispos('always', 'c')
    strikes = class_strikes()
    first = {}  # PID -> (chapter file the gear is yours from, [IIDs])

    def own(u):
        """A unit's items, and a laguz's own attack, which comes with its class (Janaff's and Ulki's beaks)."""
        return u['weapons'] + u['items'] + ([strikes[u['jid']]] if u['jid'] in strikes else [])

    def joins(pid, n, items):
        if pid and pid not in first and n <= 31:
            first[pid] = (n, items)
    for n in range(1, 32):
        folder = f'bmap{n:02d}'
        files = {code: maps.dispos(folder, code) for code in ('c', 'n', 'h')}
        groups = {g: us for code in ('c', 'n', 'h') for g, us in files[code].items() if not debug_group(g)}

        def gear(pid):
            u = next((u for us in groups.values() for u in us if u['pid'] == pid), None)
            return own(u) if u else []
        script = Script(f'C{n:02d}.cmb')
        handlers = script.handlers()
        before, during = [], []  # (PID, items): yours from this chapter, or from the next
        for u in files['c'].get(f'{folder}_mikata_c', []):
            before.append((u['pid'], own(u)))
        for h in handlers:
            if h['i'] in maps.callees(script):
                continue  # read through the handler that calls it, at its time
            at_base = h['name'] == 'FinalDisposition' or h['name'].startswith('Opening') or h['kind'] == 14
            cs = maps.calls(script, h)
            last_pid = None  # the unit a bare UnitTransferToForce hands over: the PID the handler last looked up
            for fn, a in cs:
                if fn == 'UnitTransferToForce' and a and a[-1] == 0 and last_pid:
                    # Ch.24's end hands Geoffrey over this way (UnitCheckExistsByPID2, then UnitTransferToForce(unit, 0)).
                    (before if at_base else during).append((last_pid, gear(last_pid)))
                    continue
                if a and isinstance(a[0], str) and a[0].startswith('PID_'):
                    last_pid = a[0]
                if fn == 'Join' and a and isinstance(a[0], str) and not debug_group(a[0]):
                    for u in always.get(a[0], []):
                        before.append((u['pid'], own(u)))
                elif fn in maps.DISPOS_CALLS:
                    for g in a:
                        # A cutscene's 'event' groups only stage a scene (Nasir on your side in Ch.12's).
                        for u in groups.get(g, []) if isinstance(g, str) and '_event' not in g else []:
                            if u['side'] == 0:
                                (before if at_base else during).append((u['pid'], own(u)))
                elif fn == 'UnitTransferToForceByPID' and len(a) == 2 and a[1] == 0 and isinstance(a[0], str):
                    # Handed to your army: by an opening (before the battle), or by a talk or the chapter's end (during it).
                    (before if at_base else during).append((a[0], gear(a[0])))
        for pid, items in before:
            joins(pid, n, items)
        for pid, items in during:
            joins(pid, min(n + 1, 31), items)  # the Endgame has no base after it: its joiners count there
    out = {}
    for pid, (n, items) in first.items():
        for iid in items:
            if n not in out.setdefault(iid, []):
                out[iid].append(n)
    return out


def main():
    g = GameData()
    text = read_text('common.m')
    forge, forge_at = availability(text, [('FSHOP_ITEMS', 2)])
    shop, shop_at = availability(text, [('WSHOP_ITEMS', 1), ('ISHOP_ITEMS', 1)])
    # Only what you can get: not the maps' own ballistae, nor a boss's own weapon (Gurgurant).
    staves = {g.string(g.u32(o)) for o in g.records('IID_', 'MIID_')
              if g.string(g.u32(o + 12)) == 'rod' and not (g.string(g.u32(o + 56)) or '').startswith('EID_LIGHT')}
    tomes = {g.string(g.u32(o)) for o in g.records('IID_', 'MIID_')
             if g.string(g.u32(o + 12)) in ('flame', 'thunder', 'wind') or (g.string(g.u32(o + 56)) or '').startswith('EID_LIGHT')}
    got = obtainable(shop, forge, staves, tomes)
    base_at, gift_at = given()
    kit_at = kit()
    got |= set(kit_at)  # what a recruit brings (Haar's Brave Axe through Jill's talk)
    # Names the game gives a weapon and another item both ('Torch': a staff and the item that lights fog): the weapon's gets
    # its kind added, so the item's drops and the staff's stock can't be mixed up.
    item_names = {text.get(g.string(g.u32(o + 4))) for o in g.records('IID_', 'MIID_')
                  if g.string(g.u32(o + 12)) in ('item', 'acc')}
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        r = g.d[o:o + RECORD]
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        effect_id = g.string(g.u32(o + 56)) or ''
        if not name or name in CODES_ONLY:
            continue  # never named in the game (cut content: Warp, Berserk, Unlock), or codes-only
        foe_only = iid not in got
        if kind == 'rod':
            category = 'Light' if effect_id.startswith('EID_LIGHT') else 'Staff'
        else:
            category = CATEGORY.get(kind)
        if not category:
            continue  # items and accessories
        if category == 'Strike':
            if iid not in STRIKE_CLASS:
                continue  # a strike no placement or script gives anyone (the hawk and raven kings' beaks, Vortex)
            name = f"{name} ({text[STRIKE_CLASS[iid]]})"
        elif name in item_names:
            name = f'{name} ({category.lower()})'
        kind2 = g.string(g.u32(o + 16)) or ''
        flags = [g.string(g.u32(o + 4 * i)) for i in range(6, 12) if g.u32(o + 4 * i)]
        if foe_only and 'longfar' in flags:
            continue  # the maps' fixed siege machines (ballistae, the onager) aren't weapons anyone carries
        targets = [TARGETS[t] for t in (g.string(g.u32(o + 4 * i)) for i in (12, 13) if g.u32(o + 4 * i)) if t in TARGETS]
        rank = g.string(g.u32(o + 20)) or ''
        uses = r[66]
        weapons.append({
            'id': iid[4:].lower(),
            'name': name,
            'category': category,
            # 'N' is no rank needed: a weapon only one character can use, or a knife (any thief's), or a laguz's own attack.
            'rank': rank if rank in RANKS else '—' if category in ('Knife', 'Strike') else 'Prf',
            'mt': r[67], 'hit': r[68], 'crit': r[70], 'wt': r[69],
            # A staff whose range reaches 255 goes from 1 to half the wielder's Mag, held between 5 and 15 (0x8001dd54).
            'range': f'{r[71]}' if r[71] == r[72] else f"{r[71]}-{'Mag/2 (5-15)' if r[72] == 255 else r[72]}",
            'uses': None if 'infinity' in flags else uses,
            # A laguz's own attack can't be dropped, so it can't be sold either: no price.
            'worth': 0 if category == 'Strike' else ((r[64] << 8) | r[65]) * uses,
            'wex': r[74],
            'stats': {k: (r[75 + i] - 256 if r[75 + i] > 127 else r[75 + i]) for i, k in enumerate(STATS) if r[75 + i]},
            'effective': targets,
            # A staff's rule is what it does, in the game's own words ("Restores some HP to an adjacent ally").
            'rules': list(dict.fromkeys([RULES[f] for f in flags if f in RULES]
                                        + ([TAKEN_AWAY[iid]] if iid in TAKEN_AWAY else [])
                                        + (['Uses the staff rank'] if category == 'Light' else [])))
            + ([' '.join(text.get(g.string(g.u32(o + 8)), '').split())] if category == 'Staff' else []),
            'flags': flags,
        })
        if kind2 in MAGIC and kind not in ('flame', 'thunder', 'wind', 'rod'):
            weapons[-1]['magic'] = MAGIC[kind2]
        # Hidden growth changes (record +85, one byte per stat, signed): a Fixed-mode level-up adds those of the weapon used in
        # that battle (main.dol 0x800357e0).
        growths = {k: (r[85 + i] - 256 if r[85 + i] > 127 else r[85 + i]) for i, k in enumerate(STATS) if r[85 + i]}
        if growths:
            weapons[-1]['growths'] = growths
        if foe_only:
            # Nothing gives it to the player: a foe's own weapon. The app lists it, marked as not available.
            weapons[-1]['foeOnly'] = True
        if iid in shop:
            # Which bases' armory (or, for staves, item shop) sells it, by difficulty.
            weapons[-1]['shop'] = shop[iid]
            weapons[-1]['shopAt'] = {k: [chapter_id(text, n) for n in v] for k, v in shop_at[iid].items()}
        if iid in forge:
            # Which bases' forge offers it as a base weapon, by difficulty.
            weapons[-1]['forge'] = forge[iid]
            weapons[-1]['forgeAt'] = {k: [chapter_id(text, n) for n in v] for k, v in forge_at[iid].items()}
        # What the spoiler block lists in a chapter, besides the base's stock: a base conversation's gift, a script's gift.
        if iid in base_at:
            weapons[-1]['baseAt'] = [chapter_id(text, n) for n in base_at[iid]]
        if iid in gift_at and iid not in TAKEN_AWAY:
            weapons[-1]['giftAt'] = [chapter_id(text, n) for n in gift_at[iid]]
        if iid in kit_at:
            weapons[-1]['kitAt'] = [chapter_id(text, n) for n in sorted(kit_at[iid])]

    # Grouped by category (in the game's own order within each), so a bow never sits among the swords.
    order = ['Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Staff', 'Strike']
    weapons.sort(key=lambda w: order.index(w['category']))
    lines = [
        "import type { Fe9Weapon } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe9-items.py from Path of Radiance's own item table and text.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE9_WEAPONS: Fe9Weapon[] = [',
    ]
    for w in weapons:
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

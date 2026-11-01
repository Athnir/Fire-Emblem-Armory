"""
Builds src/data/fe10/fe10Weapons.ts from Radiant Dawn's own item table (FE10Data.cms, ItemData) and
English text (Mess/e_common.m): every weapon's rank, Mt, Hit, Crit, Wt, range, uses, worth, weapon EXP,
stat bonuses, what it's effective against and its special rules, and which bases'
shops sell it (regular stock, and one-off bargains). Only weapons you can get are listed: sold,
found, dropped, stolen or carried by someone who joins you; not the maps' fixed ballistae or a weapon
locked to a boss. Laguz strikes and the spirits' attacks aren't weapons a unit carries, so they're left out too.
Run:  python scripts/build-fe10-items.py
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe10_files import FE10, GameData, read_dispos, read_shop, read_text  # noqa: E402
import fe9_cmb  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'fe10', 'fe10Weapons.ts')

CATEGORY = {'sword': 'Sword', 'lance': 'Lance', 'axe': 'Axe', 'bow': 'Bow', 'ballista': 'Crossbow', 'knife': 'Knife',
            'flame': 'Fire', 'thunder': 'Thunder', 'wind': 'Wind', 'light': 'Light', 'dark': 'Dark', 'rod': 'Staff',
            'blow': 'Strike'}
# A weapon's second type (record +16) decides its damage: the attack routine adds Mag rather than Str, and the target defends
# with Res rather than Def, when 0x80110758 calls it magic (main.dol 0x8002f474, 0x8002f2d8): fire, thunder, wind, light, dark,
# card, elemental and neutral. On a weapon whose own type isn't magic, only the white dragons' Breath ('neutral') and Ashera's
# Judge have one.
MAGIC = {'flame': 'fire', 'thunder': 'thunder', 'wind': 'wind', 'light': 'light', 'dark': 'dark', 'neutral': 'neutral'}
# What a weapon is effective against (its SFXC_ targets). SFXC_DOORBREAK (every axe) isn't a unit type.
TARGETS = {'SFXC_FLY': 'flying', 'SFXC_ARMOR': 'armour', 'SFXC_KNIGHT': 'horseback', 'SFXC_BEAST': 'beast',
           'SFXC_DRAGON': 'dragon', 'SFXC_ALIZE': 'laguz', 'SFXC_BIRD': 'bird'}
# Personal weapons: the eqA-eqI flags, and who has the matching SID_EQ_ skill in PersonData.
OWNERS = {'eqA': 'Ike', 'eqB': 'Mist', 'eqC': 'Elincia (and Renning)', 'eqD': 'Micaiah', 'eqE': 'Sanaki',
          'eqF': 'Sephiran (Lehran)', 'eqG': 'Edward', 'eqH': 'Leonardo', 'eqI': 'Nolan'}
# Rule flags, as the app words them. Flags not listed here don't change how the weapon plays, or the
# range already shows it (the wind swords' shock wave reaches 1-2).
RULES = {
    # Brave weapons only became attack-only in Fates (Fire Emblem Wiki, "Brave weapon").
    'twice': 'Strikes twice in a row, when attacking and when countering',
    'poison': 'Poisons on contact',
    'crit0': "Can't land critical hits",
    'resire': 'Restores HP equal to the damage dealt',
    'longfar': 'Siege weapon: attacks from long range',
    'absolutehit': 'Always hits',
    'sealsteal': "Can't be stolen",
    'valuable': "Can't be sold",
}
# Not weapons a unit carries: the spirits' attacks, and a placeholder.
LEFT_OUT = re.compile(r'TAIL$|^IID_SPRT_')
STATS = ['hp', 'str', 'mag', 'skl', 'spd', 'lck', 'def', 'res']
RANK = {'*': 'SS', 'S': 'S', 'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E'}
DIFFICULTIES = {'normal': 'n', 'hard': 'h'}
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}


def chapter_label(text, code):
    """'0305' -> ('Part 3', 'Ch.4'); '0407b' -> ('Part 4', 'Endgame (2)')."""
    return f"Part {ROMAN[text[f'MCT{code}_0_2']]}", text[f'MCT{code}_3']


def chapter_id(text, code):
    """'0305' -> 'fe10-3-4': the map page's id for a chapter code, so the app can tell when a chapter is reached.
    Part 1 Ch.6 is two maps ('fe10-1-6-1' and '-2'); a first appearance there counts from the first."""
    label = text[f'MCT{code}_3'].replace('Ch.', '')
    cid = 'fe10-' + re.sub(r'[^a-z0-9]+', '-', f'{int(code[:2])}-{label}'.lower()).strip('-')
    return cid + '-1' if code == '0107' else cid


def availability(text, entries):
    """({IID: {'normal': 'Part 3: Ch.4-6, 8 · Part 4: Prologue-Ch.2', 'hard': ...}}, {IID: {'normal': ['0304', ...],
    'hard': [...]}}) for the bases whose tables list each item, as the text the app shows and
    as chapter codes.
    `entries(shop, table)` picks the IIDs a table offers."""
    out, at = {}, {}
    for key, code in DIFFICULTIES.items():
        shop = read_shop(code)
        bases = [name.split('_C')[1] for name in shop if name.startswith('WSHOP_ITEMS_C') and name != 'WSHOP_ITEMS_C0000'
                 and any(isinstance(x, str) for x in shop[name] + shop.get(name.replace('WSHOP', 'ISHOP'), []))]
        bases.sort()
        offered = {}
        for b in bases:
            for iid in entries(shop, b):
                if b not in offered.setdefault(iid, []):
                    offered[iid].append(b)
        for iid, chapters in offered.items():
            at.setdefault(iid, {})[key] = list(chapters)
            parts = {}
            for c in chapters:
                parts.setdefault(c[:2], []).append(c)
            out_parts = []
            for p, cs in parts.items():
                own = [b for b in bases if b[:2] == p]
                runs, start = [], 0
                for i in range(1, len(cs) + 1):
                    if i == len(cs) or own.index(cs[i]) != own.index(cs[i - 1]) + 1:
                        first, last = chapter_label(text, cs[start])[1], chapter_label(text, cs[i - 1])[1]
                        both = first.startswith('Ch.') and last.startswith('Ch.')
                        runs.append(first if first == last else f"{first}–{last[3:] if both else last}")
                        start = i
                out_parts.append(f"{chapter_label(text, cs[0])[0]}: {', '.join(runs)}")
            out.setdefault(iid, {})[key] = ' · '.join(out_parts)
    return ({iid: {key: d.get(key, '') for key in DIFFICULTIES} for iid, d in out.items()},
            {iid: {key: d.get(key, []) for key in DIFFICULTIES} for iid, d in at.items()})


def stock(bargain):
    """The armory's and item shop's entries for one base: (IID, flag) pairs, the flag set on a one-off
    bargain (Serenes Forest's Bargains lists match)."""
    def entries(shop, b):
        out = []
        for table in (f'WSHOP_ITEMS_C{b}', f'ISHOP_ITEMS_C{b}'):
            rows = shop.get(table, [])
            out += [rows[i] for i in range(0, len(rows) - 1, 2) if isinstance(rows[i], str) and bool(rows[i + 1]) == bargain]
        return out
    return entries


def forge_bases(shop, b):
    """The base weapons the forge offers at one base: FSHOP_ITEMS_Cppnn is a grid of (weapon type,
    material, IID or 0) triples (MIK_SW, MDV_IRN -> IID_IRONSWORD)."""
    rows = shop.get(f'FSHOP_ITEMS_C{b}', [])
    return [rows[i + 2] for i in range(0, len(rows) - 2, 3) if isinstance(rows[i + 2], str)]


def forge_cards(text):
    """FSHOP_CARD_DATA: a count, then (name label, bonus word, odds word) for each card a Coin can draw.
    The bonus bytes are Mt, Hit, Crit and extra Coins; the odds word's top byte is the chance in %."""
    rows = read_shop('n')['FSHOP_CARD_DATA']
    out = []
    for i in range(rows[0]):
        label, bonus, odds = rows[1 + 3 * i: 4 + 3 * i]
        mt, hit, crit, coins = bonus.to_bytes(4, 'big')
        out.append({'name': text[label], 'mt': mt, 'hit': hit, 'crit': crit, 'coins': coins, 'chance': odds >> 24})
    return out


# The test and tutorial maps aren't part of the game.
REAL_MAP = re.compile(r'^(bmap0[1-4]|emap0[1-4])')
# Script calls that hand an item over: chests and villages (MindGetItem), gifts and rewards, dig spots.
GIVES = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub', 'UnitAddItem', 'GetRndTreasure', 'NetuzoWeapon')


# Units nothing can be stolen from: Ashera, whose Judge is hers alone.
STEAL_PROOF = {'PID_ASTARTE'}


def obtainable(shop, bargain, forge, sealed):
    """(every IID you can get, every IID a battle's units carry, every IID any placement file holds). You can get what's sold (shop, bargain, forge), handed over
    by a chapter script (treasure, villages, gifts), dropped by a foe ('/D' in its slot), brought by someone who joins your
    army (kit()), or stolen from a foe once disarmed. A weapon can't be stolen when it's flagged sealsteal (`sealed`: Rewarp,
    Elsleep) or locked to its unit ('/L' in its slot: Sephiran's Creiddylad). Only units the battle places count, not a
    cutscene's cast or a roster's preset gear."""
    import importlib.util
    fe9_cmb.FE9 = FE10
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    got = set(shop) | set(bargain) | set(forge) | set(kit())
    for name in os.listdir(os.path.join(FE10, 'Scripts')):
        if re.match(r'C0[1-4]', name):
            script = fe9_cmb.Script(name)
            for h in script.handlers():
                got |= {a for fn, args in maps.calls(script, h) if fn in GIVES for a in args if isinstance(a, str) and a.startswith('IID_')}
    # A foe's drops and what it can be disarmed of: only units the battle places (not a cutscene's cast, nor a roster's
    # preset gear: a unit of yours brings only what kit() counts).
    maps10 = maps_reader()
    # What the battle's units carry at all, and what any placement file holds (a cutscene's cast, a roster, a test map too).
    carried = set()
    anywhere = {item.partition('/')[0] for folder in os.listdir(os.path.join(FE10, 'zmap')) for diff in 'nhc'
                for _, _, items in read_dispos(folder, diff) for item in items}
    for code in story_codes():
        groups = battle_groups(maps, maps10, code)
        for diff in 'nhc':
            for group, pid, items in read_dispos(f'bmap{code}', diff):
                if ROSTER.match(group) or not ({group, re.sub(r'_[nhm]$', '', group)} & set(groups)):
                    continue
                for item in items:
                    base, _, mark = item.partition('/')
                    marks = mark.split('/')
                    carried.add(base)
                    stealable = 'L' not in marks and base not in sealed and pid not in STEAL_PROOF
                    if 'D' in marks or stealable:
                        got.add(base)
    # Held only off the battle map: no one can get it or meets it (the Slim Lance, only in cutscenes' casts). What no file
    # places at all is a foe's by other means (Lekain's Judge), so it stays.
    return got, carried, anywhere


# What a chapter script hands over, as the player sees it (see build-fe9-items.py). Handler kind 14 is a base
# conversation; kinds 4 and 5 are chests, villages and random treasure. A chapter's opening can hand an item over
# quietly (UnitAddItem); anywhere else UnitAddItem fills a unit's own kit, which isn't a gift.
SHOWN = ('MindGetItem', 'UnitGetItemShowing', 'UnitGetItemShowingSub')
BASE_CONVERSATION = 14
MAP_EVENTS = (4, 5)


def story_codes():
    """The story's chapter codes in the order they're played: '0101' ... '0406', then the endgame's '0407a'-'0407e'."""
    return sorted(m.group(1) for f in os.listdir(os.path.join(FE10, 'zmap')) if (m := re.fullmatch(r'bmap(0[1-4]\d\d|0407[a-e])', f)))


def script_reader():
    """Path of Radiance's script reader (build-fe9-maps.py), pointed at Radiant Dawn's files."""
    import importlib.util
    fe9_cmb.FE9 = FE10
    spec = importlib.util.spec_from_file_location('maps', os.path.join(os.path.dirname(__file__), 'build-fe9-maps.py'))
    maps = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps)
    return maps


def maps_reader():
    """Radiant Dawn's maps generator (build-fe10-maps.py): its placement reader (each unit's side) and cutscene filter."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('maps10', os.path.join(os.path.dirname(__file__), 'build-fe10-maps.py'))
    maps10 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(maps10)
    return maps10


def is_placement(fn):
    """A call that puts a group on the map (Dispos, InstantDisposRank, DisposContinueRank and the rest) or adds it to your army."""
    return fn.startswith(('Dispos', 'InstantDispos')) or fn in GROUP_JOINS


def battle_groups(maps, maps10, code):
    """{group name: placed before the battle (an opening, a base conversation)} for what the chapter's script places outside
    its cutscenes, by base name (without the difficulty's _n / _h). A cutscene's own cast (Part 1 Ch.1's Daein soldiers, the
    endgame's opening scene) isn't on the battle map."""
    path = os.path.join(FE10, 'Scripts', f'C{code}.cmb')
    if not os.path.exists(path):
        return {}
    script, out = fe9_cmb.Script(f'C{code}.cmb'), {}
    for h in script.handlers():
        if h['i'] in maps.callees(script):
            continue
        at_base = h['name'].startswith('Opening') or h['kind'] == BASE_CONVERSATION
        for fn, a in maps10.scenes_removed(maps.calls(script, h), f'bmap{code}'):
            if is_placement(fn) and a and isinstance(a[0], str):
                out[a[0]] = out.get(a[0], False) or at_base
    return out


def given():
    """({IID: [chapter codes]}, {IID: [...]}): what base conversations give (Jill's Brave Axe, Tarvos), and what the
    chapters' own scripts hand over outside the chests and villages (Ragnell, Amiti, the tomes Part 4 Ch.4's opening gives
    Tormod). A gift before the battle (a base conversation, an opening) is that chapter's; one at its end or from an event
    during it is the next chapter's. A handler another one calls is read through its caller."""
    maps = script_reader()
    codes = story_codes()
    base, gift = {}, {}
    for k, code in enumerate(codes):
        if not os.path.exists(os.path.join(FE10, 'Scripts', f'C{code}.cmb')):
            continue
        script = fe9_cmb.Script(f'C{code}.cmb')
        for h in script.handlers():
            if h['kind'] in MAP_EVENTS or h['i'] in maps.callees(script):
                continue
            into = base if h['kind'] == BASE_CONVERSATION else gift
            at = code if h['kind'] == BASE_CONVERSATION or h['name'].startswith('Opening') else codes[min(k + 1, len(codes) - 1)]
            for fn, args in maps.calls(script, h):
                for a in args if fn in SHOWN or (fn == 'UnitAddItem' and h['name'].startswith('Opening')) else ():
                    if isinstance(a, str) and a.startswith('IID_') and at not in into.setdefault(a, []):
                        into[a].append(at)
    return base, gift


# A chapter's own roster of your units: bmapPPCC_mikata_n / _h / _c and its lettered or numbered variants (a_mikata, mikata2).
# The opening's and the ending's scene casts (_op01_mikata_c, _ed01_mikata_c) only stage a scene.
ROSTER = re.compile(r'bmap\d{4}[a-e]?_(?:[a-e]_)?mikata\d?_[nhc]$')
# Calls that add a group's units to your army: a base conversation's recruits (Meg, Volug), Tormod's group.
GROUP_JOINS = ('JoinRank', 'Join', 'SallyAddByGroupRank')


def kit():
    """{IID: [chapter codes]}: the gear each of your units brings, counted once, in the chapter it first joins, in story order.
    The chapter's own roster (ROSTER), a group a base conversation or an opening adds (GROUP_JOINS), or a unit an opening
    hands over are yours from that chapter; one a talk or the chapter's end hands over (UnitTransferToForceByPID(pid, 0)) is
    yours from the next, the first base it's at. Later rosters only place a unit you already have, carrying what it carries.
    The endgame's five maps (bmap0407a-e) keep their letter."""
    maps, maps10 = script_reader(), maps_reader()
    codes = story_codes()
    strikes = class_strikes()
    first = {}  # PID -> (chapter code, items)
    for k, code in enumerate(codes):
        placed = [u for diff in 'nhc' for u in read_dispos(f'bmap{code}', diff)]
        side = {(g, u['pid']): u['side'] for diff in 'nhc' for g, us in maps10.dispos(f'bmap{code}', diff).items() for u in us}
        jid_of = {u['pid']: u['jid'] for diff in 'nhc' for us in maps10.dispos(f'bmap{code}', diff).values() for u in us}

        def own(pid, items):
            """A unit's items, and a laguz's own attack, which comes with its class (Lethe's Claw, Tibarn's Great Talon)."""
            return items + ([strikes[jid_of[pid]][0]] if jid_of.get(pid) in strikes else [])

        def gear(pid):
            return next((items for _, p, items in placed if p == pid), [])
        before = [(pid, items) for group, pid, items in placed if ROSTER.match(group)]
        during = []
        # A group the battle places on your side outside the rosters joins you (Lehran in Endgame (5)); a join call adds a
        # group whatever its side (a base conversation's recruits).
        for name, at_base in battle_groups(maps, maps10, code).items():
            for group, pid, items in placed:
                if not ROSTER.match(group) and (re.sub(r'_[nhm]$', '', group) == name or group == name) and side.get((group, pid)) == 0:
                    (before if at_base else during).append((pid, items))
        if os.path.exists(os.path.join(FE10, 'Scripts', f'C{code}.cmb')):
            script = fe9_cmb.Script(f'C{code}.cmb')
            for h in script.handlers():
                if h['i'] in maps.callees(script):
                    continue
                at_base = h['name'].startswith('Opening') or h['kind'] == BASE_CONVERSATION
                for fn, a in maps10.scenes_removed(maps.calls(script, h), f'bmap{code}'):
                    if fn in GROUP_JOINS and a and isinstance(a[0], str):
                        for group, pid, items in placed:
                            if re.sub(r'_[nhm]$', '', group) == a[0] or group == a[0]:
                                (before if at_base else during).append((pid, items))
                    elif fn == 'UnitTransferToForceByPID' and len(a) == 2 and a[1] == 0 and isinstance(a[0], str):
                        (before if at_base else during).append((a[0], gear(a[0])))
        for pid, items in before:
            first.setdefault(pid, (code, own(pid, items)))
        for pid, items in during:
            first.setdefault(pid, (codes[min(k + 1, len(codes) - 1)], own(pid, items)))
    out = {}
    for code, items in first.values():
        for item in items:
            iid = item.partition('/')[0]
            if code not in out.setdefault(iid, []):
                out[iid].append(code)
    return out


_STRIKES = {}


def class_strikes():
    """{JID: (IID, name)}: each laguz class's own attack and the name it's listed under (build-fe10-maps.py's
    Game.strikes, so the weapon page and the map's gear agree)."""
    if not _STRIKES:
        _STRIKES.update(maps_reader().Game().strikes)
    return _STRIKES


def kit_chapter(text, code):
    """'0305' -> 'fe10-3-4'; the endgame's '0407c' -> 'fe10-4-endgame-3'."""
    return f'fe10-4-endgame-{ord(code[4]) - 96}' if len(code) == 5 else chapter_id(text, code)


def main():
    g = GameData()
    text = read_text()
    shop, shop_at = availability(text, stock(False))
    bargain, bargain_at = availability(text, stock(True))
    forge, forge_at = availability(text, forge_bases)
    # Only what you can get: not the map's own ballistae, nor a foe's weapon locked to it (Judge, Rewarp).
    sealed = set()
    for o in g.records('IID_', 'MIID_'):
        n_attr = g.d[o + 0x35]
        if 'sealsteal' in (g.string(g.u32(o + 0x38 + 4 * i)) for i in range(n_attr)):
            sealed.add(g.string(g.u32(o)))
    got, carried, anywhere = obtainable(shop, bargain, forge, sealed)
    base_at, gift_at = given()
    kit_at = kit()
    # The laguz classes' own attacks, and the higher forms of each (one name, a higher rank: IID_NAIL1, 2 and 3), which are
    # listed with the class's own rather than on their own.
    strike_names = dict(class_strikes().values())
    forms = {}
    for o in g.records('IID_', 'MIID_'):
        m_ = re.fullmatch(r'(IID_\w+?)(\d)', g.string(g.u32(o)))
        if m_ and g.string(g.u32(o + 12)) == 'blow':
            mt, hit, crit = g.d[o + 0x28], g.d[o + 0x29], g.d[o + 0x2a]
            forms.setdefault(m_.group(1), {})[int(m_.group(2))] = (RANK.get(g.string(g.u32(o + 20))), mt, hit, crit)
    weapons = []
    for o in g.records('IID_', 'MIID_'):
        iid = g.string(g.u32(o))
        name = text.get(g.string(g.u32(o + 4)))
        kind = g.string(g.u32(o + 12))
        category = CATEGORY.get(kind)
        if not name or name == 'dummy' or not category or LEFT_OUT.search(iid):
            continue
        if category == 'Strike':
            if iid not in strike_names:
                continue  # no class's own: a higher form (listed with the class's), Vortex, Ashera's Judge
            name = strike_names[iid]
        foe_only = iid not in got
        if foe_only and iid in anywhere and iid not in carried:
            continue  # codes-only: only off the battle map (the Slim Lance, in cutscenes' casts)
        r = g.d[o:o + 0x38]
        rank = g.string(g.u32(o + 20)) if g.u32(o + 20) else ''
        price, = struct.unpack_from('>H', r, 0x26)
        mt, hit, crit, wt, uses, wex, rmin, rmax = r[0x28:0x30]
        n_attr, n_target, has_stats = r[0x35], r[0x36], r[0x37]
        p = o + 0x38
        flags = [g.string(g.u32(p + 4 * i)) for i in range(n_attr)]
        if foe_only and 'longfar' in flags:
            continue  # the maps' fixed siege machines (ballistae, the onager, Ashera's Judge) aren't weapons anyone carries
        p += 4 * n_attr
        targets = [g.string(g.u32(p + 4 * i)) for i in range(n_target)]
        p += 4 * n_target
        # Stat bonuses while equipped (on staves the block means something else).
        block = g.d[p:p + 12] if has_stats and category != 'Staff' else bytes(12)
        owner = next((OWNERS[f] for f in flags if f in OWNERS), None)
        rules = ([f'{owner} only'] if owner else []) + [RULES[f] for f in flags if f in RULES]
        if 'expandrange' in flags:
            # Only Marksmen have SID_EXPANDRANGEO_1: one tile further with a bow that has this flag. Longbows
            # and crossbows don't, so theirs stays as it is.
            rules.append(f'A Marksman can fire it at {rmin}-{rmax + 1} range')
        if category == 'Crossbow':
            # main.dol 0x8002f430: a crossbow's attack skips the wielder's Str; SID_EQBALLISTA (Warriors,
            # Reavers, Snipers, Marksmen) is what lets a class use one.
            rules = ['Warriors, Reavers, Snipers and Marksmen only, no weapon rank needed',
                     "Damage is its Mt alone: the wielder's Str isn't added"] + rules
        if category == 'Staff':
            # A staff's rule is what it does, in the game's own words ("Restores HP to an adjacent ally").
            what = ' '.join(text.get(g.string(g.u32(o + 8)) or '', '').split())
            rules += [what] if what else []
        if category == 'Strike':
            # The class's own (JobData +0x1c), not an item in a unit's slots; its higher forms share its name.
            family, tier = re.fullmatch(r'(IID_\w+?)(\d)', iid).groups()
            rules = ["A laguz's own attack, which comes with its class: it isn't one of the unit's items"] + [
                f"Rank {r_} form: Mt {m_}, Hit {h_}" + (f', Crit {c_}' if c_ else '')
                for t_, (r_, m_, h_, c_) in sorted(forms[family].items()) if t_ > int(tier)] + rules
        w = {
            'id': iid[4:].lower(),
            'name': name,
            'category': category,
            # 'N' is no rank needed: someone's own weapon, or a crossbow.
            'rank': RANK.get(rank) or ('Prf' if owner else '—'),
            'mt': mt, 'hit': hit, 'crit': crit, 'wt': wt,
            # A staff whose range reaches 255 goes from 1 to half the wielder's Mag.
            'range': f'{rmin}' if rmin == rmax else f"{rmin}-{'Mag/2' if rmax == 255 else rmax}",
            'uses': None if 'infinity' in flags else uses,
            # A laguz's own attack isn't an item, so it can't be sold: no price.
            'worth': 0 if category == 'Strike' else price * uses,
            'wex': wex,
            'stats': {k: (block[i] - 256 if block[i] > 127 else block[i]) for i, k in enumerate(STATS) if block[i]},
            'effective': [TARGETS[t] for t in targets if t in TARGETS],
            'rules': rules,
            'flags': flags,
        }
        kind2 = g.string(g.u32(o + 16)) or ''
        if kind2 in MAGIC and kind not in MAGIC:
            w['magic'] = MAGIC[kind2]  # a physical weapon that deals magic damage (the white dragons' Breath)
        if foe_only:
            # Nothing gives it to the player: a foe's own weapon. The app lists it, marked as not available.
            w['foeOnly'] = True
        if iid in shop:
            w['shop'] = shop[iid]
            w['shopAt'] = {k: [chapter_id(text, c) for c in v] for k, v in shop_at[iid].items()}
        if iid in bargain:
            w['bargain'] = bargain[iid]
            w['bargainAt'] = {k: [chapter_id(text, c) for c in v] for k, v in bargain_at[iid].items()}
        if iid in forge:
            # Which bases' forge offers it as a base weapon, by difficulty.
            w['forge'] = forge[iid]
            w['forgeAt'] = {k: [chapter_id(text, c) for c in v] for k, v in forge_at[iid].items()}
        # What the spoiler block lists in a chapter, besides the base's stock: a base conversation's gift, a script's gift.
        if iid in base_at:
            w['baseAt'] = [chapter_id(text, c) for c in base_at[iid]]
        if iid in gift_at:
            w['giftAt'] = [chapter_id(text, c) for c in gift_at[iid]]
        if iid in kit_at:
            w['kitAt'] = [kit_chapter(text, c) for c in sorted(kit_at[iid])]
        weapons.append(w)

    order = ['Sword', 'Lance', 'Axe', 'Bow', 'Crossbow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff', 'Strike']
    weapons.sort(key=lambda w: order.index(w['category']))
    lines = [
        "import type { TelliusWeapon } from '../fe9/types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fe10-items.py from Radiant Dawn's own item table, text and shop files.",
        ' * Do not edit by hand.',
        ' */',
        'export const FE10_WEAPONS: TelliusWeapon[] = [',
    ]
    for w in weapons:
        lines.append('  ' + json.dumps(w, ensure_ascii=False) + ',')
    lines.append(']')
    lines += ['', "/** What a Coin can add to a forged weapon: the card drawn, its bonus and its chance in %. */",
              'export const FE10_FORGE_CARDS = ' + json.dumps(forge_cards(text), ensure_ascii=False)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(weapons), 'weapons')


if __name__ == '__main__':
    main()

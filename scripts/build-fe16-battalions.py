"""
Builds src/data/fe16/fe16Battalions.ts: Three Houses' battalions and their gambits, read from the game's own tables and program
(scripts/fe16_data.py, fe16_code.py; data-raw/fe16/README.md), with the battles' gifts and foes from the map builder
(build-fe16-maps.py). Run:
    python scripts/build-fe16-battalions.py

- The battalions (fixed_data.bin section 11, 200 x 44 bytes): +6 u16 endurance, +8 / +9 Mag at level 1 and its gain per level (tenths),
  +10 Phys, +11 Hit, +12 Crit, +13 Avo (+14 the same), +15 Prot, +16 Res at level 1 (signed), +19 to +25 the same stats' gains per level
  (tenths: Phys, Hit, Crit, Avo, Avo, Prot, Res), +36 Cha, +38 the Authority rank it needs (0 E to 4 A), +39 its gambit, +40 its kind
  (bits 1 infantry, 2 armored, 4 cavalry, 8 flying: the icon `0x5cfe24` and `0x416c10` read). Every stat but Cha and endurance rises
  with its level, 1 to 5, by its gain, the fraction dropped (Serenes Forest's maximum stats: level 1 plus four gains, rounded down).
- Who can equip one (`0x3dd8f0`, the check the battalion menu asks): the rank x 2 at most the unit's Authority level (+0x8f: E 0, E+ 1,
  D 2 ... A 8), and a unit whose class flies (its class's +81 bit 3) only a flying battalion; any other unit takes any kind.
- The gambits (section 3, 80 x 24 in a weapon's layout: +7 max range, +10 min range, +14 effective against, +16 Mt, +17 Hit, +22 bit 0
  magic; section 8, 80 x 13: +6 what it is (5 support, 6 healing), +7 uses, +10 its area's shape). The area is what the program's area
  builder (`0x41e4e0`) puts in it, run here (`fe16_code.gambit_area`) for a user aiming straight ahead at the nearest tile in range,
  with the target itself.
- The Battalion Guild (fixed_shopdata.bin section 3, 200 x 20): +0 price, +8 the battalion, +13 2 (limited), +15 the routes whose guild
  offers it (bit 1 << the route the scripts number: 0 Silver Snow and the Black Eagles, 1 Azure Moon and the Blue Lions, 2 Verdant
  Wind and the Golden Deer, 3 Crimson Flower; the menu `0x244350`), +16-18 how many at the guild's levels 1-3. A limited record gains
  only what a higher level adds to the one before (`0x3dea04`): each battalion is hired once. The guild's level is the month's
  (fixed_lobby_common.bin section 0 +11, by each chapter's month, fixed_flow.bin +25; it never falls): 1 from Chapter 3, 2 from
  Chapter 8, 3 from Part II's second month (Crimson Flower's Chapter 12, the other routes' Chapter 14).
- The battles' gifts (GrantBattalion) are the map builder's `battalion_grants`; foes lead battalions from their unit records (+34).
- Quests aren't read yet (their scripts aren't among the files read): their battalions are Fire Emblem Wiki's quest list, below.
"""
import importlib.util
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe16_code  # noqa: E402
import fe16_data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'data', 'fe16', 'fe16Battalions.ts')
_spec = importlib.util.spec_from_file_location('fe16_maps', os.path.join(HERE, 'build-fe16-maps.py'))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

RANKS = 'EDCBA'
KINDS = {1: 'Infantry', 2: 'Armored', 4: 'Cavalry', 8: 'Flying'}
STATS = ['Phys', 'Mag', 'Hit', 'Crit', 'Avo', 'Prot', 'Res', 'Cha']
BASE = {'Phys': 10, 'Mag': 8, 'Hit': 11, 'Crit': 12, 'Avo': 13, 'Prot': 15, 'Res': 16, 'Cha': 36}
GAIN = {'Phys': 19, 'Mag': 9, 'Hit': 20, 'Crit': 21, 'Avo': 22, 'Prot': 24, 'Res': 25}
EFFECTIVE = {1: 'infantry', 2: 'armored units', 4: 'cavalry', 8: 'fliers', 16: 'dragons', 32: 'monsters'}
GAMBIT_SUPPORT, GAMBIT_HEALING = 5, 6
LOBBY_COMMON, MONTHS = 24, 0
# The routes (fixed_flow.bin sections), each with the house it comes from: the guild checks the route the scripts number, the house's
# in White Clouds (the Black Eagles' 0), and from Chapter 12 the route's own.
ROUTES = {'cf': (D.CRIMSON_FLOWER, 'be'), 'ss': (D.SILVER_SNOW, 'be'), 'am': (D.AZURE_MOON, 'bl'), 'vw': (D.VERDANT_WIND, 'gd')}
HOUSE_ROUTE = {'be': 0, 'bl': 1, 'gd': 2}
ROUTE_NAMES = {'cf': 'Crimson Flower', 'ss': 'Silver Snow', 'am': 'Azure Moon', 'vw': 'Verdant Wind'}

# Quests that give battalions, from Fire Emblem Wiki's quest list (the quest scripts aren't read): the quest, the chapter it's offered
# in per route (None: not on that route), and the battalions (the guild records +15 0x0F; the second of a name the game uses twice is
# the foes' copy). Taking Care of Business gives one battalion per route besides the Thieves.
QUESTS = [
    ('Leading the Charge', {r: 2 for r in ROUTES}, ["Jeralt's Mercenaries", 'Church of Seiros Soldiers', 'Seiros Mercenaries']),
    ('Maintaining Your Training', {r: 5 for r in ROUTES}, ['Merchant Military']),
    ('Clearing the Way', {r: 5 for r in ROUTES}, ['Merchant Military', 'Bandits']),
    ('Banish the Bandits', {r: 7 for r in ROUTES}, ['Remire Militia']),
    ('The Best of the Best', {r: 7 for r in ROUTES}, ['Kingdom Youths']),
    ('Something to Prove', {r: 8 for r in ROUTES}, ['Kingdom Youths']),
    ("A Servant's Essentials", {r: 9 for r in ROUTES}, ['Nuvelle Chamberlain Co.', 'Nuvelle Attendants Co.', 'Nuvelle Stewards Co.']),
    ('The Cream of the Crop', {r: 10 for r in ROUTES}, ['Empire Youths']),
    ('Pirates in the North', {r: 14 for r in ROUTES}, ['Pirates', 'Rogues']),
    ('Dealing with Deserters', {'cf': 13, 'ss': 14, 'am': 14, 'vw': 14}, ['Alliance Youths']),
    ('Floral Tribute', {'vw': 14}, ['Morfis Magic Corps']),
    ('Fighting Alongside Death', {'cf': 14}, ['Reaper Knights']),
    ('Undercover Commerce', {r: 15 for r in ROUTES}, ['Almyra Mercenaries']),
    ('Taking Care of Business', {r: 16 for r in ROUTES}, ['Thieves']),
    ('Taking Care of Business', {'ss': 16}, ['Morfis Magic Corps']),
    ('Taking Care of Business', {'am': 16}, ['Duscur Infantry']),
    ('Taking Care of Business', {'vw': 16}, ['Almyra Mercenaries']),
    ('Taking Care of Business', {'cf': 16}, ['Brigid Mercenaries']),
]
# Given outside any chapter: four Online Liaison Recon Missions finished three weeks in a row (Fire Emblem Wiki), from the month of
# Chapter 2 (when the monastery's free days start).
ONLINE = {'Essar Research Group': 'Given for finishing four Online Liaison Recon Missions three weeks in a row'}


def battalions():
    return D.table(D.FIXED_DATA, 11)


def kind_of(r):
    bits = r[40] & 0x0F
    assert bits in KINDS, r[40]
    return KINDS[bits]


def stats_by_level(r):
    """Each stat at levels 1 to 5: level 1 plus the gain per level (tenths), the fraction dropped."""
    out = {}
    for s in STATS:
        base = struct.unpack_from('<b', r, BASE[s])[0]
        gain = r[GAIN[s]] if s in GAIN else 0
        out[s] = [base + gain * lv // 10 for lv in range(5)]
    return out


def gambit(g, cpu):
    a, x = D.table(D.FIXED_DATA, 3)[g], D.table(D.FIXED_DATA, 8)[g]
    lo, hi = a[10], a[7]
    support = x[6] in (GAMBIT_SUPPORT, GAMBIT_HEALING)
    user, target = (16, 16), (16, 16 - lo)
    tiles = set(fe16_code.gambit_area(x[10], target, user, cpu)) | {target}
    out = {
        'id': g, 'name': D.text(D.GAMBIT_NAME + g), 'kind': 'support' if support else 'magic' if a[22] & 1 else 'physical',
        'hit': a[17], 'range': [lo, hi], 'uses': x[7], 'help': ' '.join(D.text(D.GAMBIT_HELP + g).split()),
        # The area, from the user's tile: x across, y forward (negative: toward the target, which stands at [0, -min range]).
        'area': sorted([t[0] - user[0], t[1] - user[1]] for t in tiles),
    }
    if a[16]:
        out['mt'] = a[16]
    if x[6] == GAMBIT_HEALING:
        out['heals'] = True
    eff = [w for bit, w in EFFECTIVE.items() if a[14] & bit]
    if eff:
        out['effective'] = eff
    return out


def months():
    return D.table(LOBBY_COMMON, MONTHS)


def guild_level(section, chapter, level):
    """The guild's level in a chapter's month: the month's (+11), held from earlier months (it never falls)."""
    m = D.table(D.FLOW, section)[chapter][25]
    return max(level, months()[m if m < 100 else 0][11])


def story_map(key, chapter):
    """A route's chapter as the maps name it: White Clouds' shared map or its house's own, from Chapter 12 the route's."""
    section, house = ROUTES[key]
    if chapter < M.PART_TWO:
        return f'fe16-{chapter}-{house}' if chapter in M.PER_HOUSE else f'fe16-{chapter}'
    return f'fe16-{D.flow(section)[chapter]}-{key}'


HOUSES = {'be': ['cf', 'ss'], 'bl': ['am'], 'gd': ['vw']}


def guild_sources():
    """{battalion: [source]}: when the guild first offers it, in White Clouds by your house (its routes in `routes`: the map is every
    house's) and from Chapter 12 by your route, where a route's guild offers one its house's didn't, or stops offering one it did
    (Crimson Flower's guild, from Chapter 12, has no Church battalion: kind 'guild-gone')."""
    out = {}
    for r in D.table(D.SHOPDATA, 3):
        price, b = struct.unpack_from('<iH', r, 0)[0], struct.unpack_from('<H', r, 8)[0]
        stock = list(r[16:19])
        if not any(stock) or not price:
            continue
        assert r[13] == 2 and max(stock) == 1, (b, r.hex())   # limited, one: hired once
        need = next(k for k, n in enumerate(stock) if n) + 1
        lines = []
        for house, keys in HOUSES.items():
            section = ROUTES[keys[0]][0]
            level, first = 0, None
            for chapter in range(1, M.PART_TWO):
                level = guild_level(section, chapter, level)
                if first is None and level >= need and r[15] >> HOUSE_ROUTE[house] & 1:
                    first = chapter
            if first is not None:
                lines.append({'mapId': story_map(keys[0], first), 'kind': 'guild', 'text': 'Hired at the Battalion Guild',
                              'routes': list(keys)})
            for key in keys:
                section = ROUTES[key][0]
                offered = first is not None
                late = level
                for chapter in range(M.PART_TWO, len(D.flow(section))):
                    if D.flow(section)[chapter] is None:
                        continue
                    late = guild_level(section, chapter, late)
                    now = late >= need and bool(r[15] >> section & 1)
                    if now != offered:
                        if now:
                            lines.append({'mapId': story_map(key, chapter), 'kind': 'guild', 'text': 'Hired at the Battalion Guild'})
                        else:
                            lines.append({'mapId': story_map(key, chapter), 'kind': 'guild-gone',
                                          'text': 'No longer offered by the Battalion Guild'})
                        offered = now
        # One line per map and words (a White Clouds chapter every house shares lists the houses' routes together).
        merged = {}
        for line in lines:
            key = (line['mapId'], line['kind'])
            if key in merged and 'routes' in line:
                merged[key]['routes'] += line['routes']
            else:
                merged.setdefault(key, line)
        out[b] = list(merged.values())
    return out


def guild_prices():
    out = {}
    for r in D.table(D.SHOPDATA, 3):
        price, b = struct.unpack_from('<iH', r, 0)[0], struct.unpack_from('<H', r, 8)[0]
        if price and any(r[16:19]):
            out[b] = price
    return out


def battle_sources():
    """{battalion: [source]} from the battles: what each one's end gives (`battalion_grants`), and the foes that lead a battalion
    ({battalion: [(map id, kind, who, difficulties)]})."""
    gifts, foes = {}, {}
    for entry in M.battle_list():
        if entry.get('aux'):
            continue
        plan = entry.get('paralogue')
        b = M.Battle(entry['s'], entry['line'], plan['persons'] if plan else ())
        late = entry['chapter'] >= M.PART_TWO or bool(plan and max(w[1] for w in plan['windows'].values()) >= M.PART_TWO)
        for x, words in M.battalion_grants(b, late):
            text = 'Given when the battle is won' + (f', {words}' if words else '')
            gifts.setdefault(x, []).append({'mapId': entry['id'], 'kind': 'event-later', 'text': text})
        for d, dname in enumerate(b.diffs):
            placed, _ = b.start(d)
            for slot in sorted(b.on_map(d)):
                r = b.record(slot)
                if r['battalion'] is None or r['army'] not in (1, 3):
                    continue
                who = D.person_shown_name(r['person']) if M.is_person(r) else f"a foe {M.class_name(M.unit_class(r))}"
                kind = 'foe' if slot in placed else 'foe-later'
                key = (entry['id'], kind, who)
                foes.setdefault(r['battalion'], {}).setdefault(key, []).append(dname)
    return gifts, foes


def main():
    cpu = fe16_code.Arm64()
    recs = battalions()
    t = D.texts()[1]
    names = {b: D.battalion_label(b) for b in range(len(recs))}
    by_name = {}
    for b, n in names.items():
        by_name.setdefault(D.text(D.BATTALION_NAME + b), b)   # a quest's battalion: the first record of its name (the player's)
    sources = {b: [] for b in range(len(recs))}
    for b, ss in guild_sources().items():
        sources[b] += ss
    gifts, foes = battle_sources()
    for b, ss in gifts.items():
        sources[b] += ss
    for quest, chapters, bats in QUESTS:
        for bname in bats:
            b = by_name[bname]
            for m in dict.fromkeys(story_map(key, ch) for key, ch in chapters.items()):
                sources[b].append({'mapId': m, 'kind': 'quest', 'text': f'Reward for the quest "{quest}"'})
    for bname, text in ONLINE.items():
        sources[by_name[bname]].append({'mapId': 'fe16-2', 'kind': 'online', 'text': text})
    prices = guild_prices()
    gambits, out_bats, out_sources = {}, [], {}
    for b, r in enumerate(recs):
        led = foes.get(b, {})
        if not sources[b] and not led:
            continue
        name = names[b]
        foe_only = not sources[b]
        if foe_only:
            # What foes lead it, for a battalion nothing gives you: each map's foes once, the difficulties they're on.
            for (map_id, kind, who), ds in led.items():
                line = {'mapId': map_id, 'kind': kind, 'text': f'Led by {who}'}
                if len(ds) < 3 and map_id.startswith('fe16-') and not map_id.endswith('-cs'):
                    line['difficulties'] = ds
                sources[b].append(line)
        g = r[39]
        if g not in gambits:
            gambits[g] = gambit(g, cpu)
        entry = {'id': b, 'name': name, 'rank': RANKS[r[38]], 'kind': kind_of(r), 'endurance': struct.unpack_from('<H', r, 6)[0],
                 'stats': stats_by_level(r), 'gambit': g}
        if b in prices:
            entry['price'] = prices[b]
        if foe_only:
            entry['foeOnly'] = True
        out_bats.append(entry)
        out_sources[name] = sources[b]
    lines = [
        '/*',
        " * GENERATED by scripts/build-fe16-battalions.py from Three Houses' battalion, gambit and guild tables (fixed_data.bin sections",
        ' * 3, 8 and 11, fixed_shopdata.bin section 3), its program (the gambit areas) and its battles. Do not edit by hand.',
        ' */',
        '',
        "import type { Fe16Battalion, Fe16BattalionSource, Fe16Gambit } from './fe16BattalionTypes'",
        '',
        '/** Every battalion you can get, and those only foes lead (`foeOnly`): in the game\'s own order. */',
        'export const FE16_BATTALIONS: Fe16Battalion[] = ' + json.dumps(out_bats, ensure_ascii=False, indent=1),
        '',
        '/** The gambits those battalions use, by the game\'s gambit number. */',
        'export const FE16_GAMBITS: Record<number, Fe16Gambit> = ' + json.dumps({k: gambits[k] for k in sorted(gambits)},
                                                                                ensure_ascii=False, indent=1),
        '',
        '/** Where each battalion turns up (by name), in the weapon pages\' form: a chapter (a map id), how, in words, and for a line that',
        " * holds on some routes only (the guild's stock, a quest), those routes. */",
        'export const FE16_BATTALION_SOURCES: Record<string, Fe16BattalionSource[]> = '
        + json.dumps(out_sources, ensure_ascii=False, indent=1),
    ]
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out_bats), 'battalions,', sum(1 for x in out_bats if x.get('foeOnly')), 'foe-only,', len(gambits), 'gambits')


if __name__ == '__main__':
    main()

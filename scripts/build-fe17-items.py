"""
Builds src/data/fe17/fe17Weapons.ts: Fire Emblem Engage's weapons, read from the game's own item table (item.xml, sheet アイテム) and
named from its English text (scripts/fe17_data.py; data-raw/fe17/README.md). Run:
    python scripts/build-fe17-items.py

A weapon's effects are skills it carries (EquipSids, GiveSids), read from the skill table's own actions: effectiveness (Efficacy,
its EfficacyValue the multiplier: 3), striking twice (行動回数 x2), Smash (吹き飛ばし: pushes the foe back, no follow-up), no
follow-up, never missing, halving or ignoring the foe's defences, Arts' attack ((Str + Mag) / 2). A weapon flagged ReverseAttribute
(App.ItemData.Flags 65536) deals the other kind of damage: the magic swords, lances, axes, bows and knives fight against Res. Staves
have uses; every other weapon never breaks (Endurance 255).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe17_data as D  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'data', 'fe17', 'fe17Weapons.ts')
REFINE_OUT = os.path.join(os.path.dirname(OUT), 'fe17Refine.ts')
SMITHY = 'AID_錬成屋'
CATEGORIES = {1: 'Sword', 2: 'Lance', 3: 'Axe', 4: 'Bow', 5: 'Knife', 6: 'Tome', 7: 'Staff', 8: 'Arts', 9: 'Special'}
REVERSE_ATTRIBUTE = 65536
ONLY_ENEMY = 16
ENGAGE = 128
# Effectiveness skills (each skill's Efficacy bit) -> the weapon page's targets.
EFFICACY = {2: 'horseback', 4: 'armour', 8: 'flying', 16: 'dragon', 64: 'corrupted'}
STAT_FIELDS = [('Enhance.Hp', 'hp'), ('Enhance.Str', 'str'), ('Enhance.Tech', 'dex'), ('Enhance.Quick', 'spd'),
               ('Enhance.Luck', 'lck'), ('Enhance.Def', 'def'), ('Enhance.Magic', 'mag'), ('Enhance.Mdef', 'res'),
               ('Enhance.Phys', 'bld'), ('Enhance.Move', 'mov'), ('Avoid', 'avo'), ('Secure', 'ddg')]


def skill_rules(sids, skills, give=False):
    """What a weapon's skills do, in words, from their actions; unread ones by the skill's own English help, if it has one."""
    out, effective = [], []
    for sid in sids:
        s = skills.get(sid)
        if s is None:
            continue
        acts = list(zip(D.flag_list(s['ActNames']), D.flag_list(s['ActOperations']), D.flag_list(s['ActValues'])))
        if s.get('Efficacy') and s['Efficacy'] != '0':
            effective.append(EFFICACY[int(s['Efficacy'])])
        elif ('行動回数', '*', '2') in acts:
            out.append('Strikes twice when its user starts the fight')
        elif acts and acts[0][0] == '吹き飛ばし率':
            out.append('Smash: pushes the foe back a tile; no follow-up attack')
        elif acts == [('手番回数', '=', 'min(手番回数, 1)')]:
            out.append('No follow-up attack')
        elif acts and acts[0] == ('攻撃結果', '=', 'ヒット'):
            out.append('Never misses')
        elif acts == [('命中率', '=', '100'), ('必殺率', '=', '0')]:
            out.append('Hit is always 100, Crit 0')
        elif acts == [('相手の防御力', '=', '0')]:
            out.append("Ignores the foe's Def and Res")
        elif acts and acts[0][0] == '相手の守備' and acts[0][2].startswith('cond'):
            out.append("Halves the foe's Def (or Res, against magic)")
        elif acts == [('ユニット攻撃力', '=', '(力+魔力)/2')]:
            out.append("Its user's attack is (Str + Mag) / 2")
        elif acts == [('ユニット攻撃力', '=', '力 * 0.5')]:
            out.append("Its user's attack is Str / 2")
        elif acts == [('ユニット攻撃力', '=', '技')]:
            out.append("Its user's attack is Dex")
        elif acts and acts[0][0] == '回復' and 'ダメージ' in acts[0][2]:
            out.append('Heals its user by half the damage it deals')
        elif acts == [('威力', '+', '魔力 / 3')]:
            out.append("Mt + a third of its user's Mag")
        elif sid == 'SID_毒' and give:
            out.append('Poisons the foe it hits')
        elif sid == 'SID_移動不可' and give:
            out.append("Stops the foe moving")
        elif sid == 'SID_沈黙' and give:
            out.append('Silences the foe')
        elif sid == 'SID_気絶' and give:
            out.append('Stuns the foe')
        else:
            words = D.text(s['Help']) if s['Help'] else None
            if words:
                out.append(' '.join(words.split()))
    return out, effective


def main():
    skills = {r['Sid']: r for r in D.rows('skill')}
    weapons = []
    for n, r in enumerate(D.rows('item')):
        kind = int(r['Kind'] or 0)
        if kind not in CATEGORIES or not r['Name']:
            continue
        name = D.item_label(r['Iid'])
        if not name:
            continue
        flags = int(r['Flag'] or 0)
        rules, effective = skill_rules(D.flag_list(r['EquipSids']) + D.flag_list(r['PassiveSids']), skills)
        given, _ = skill_rules(D.flag_list(r['GiveSids']), skills, give=True)
        if flags & ENGAGE:
            # App.ItemData.Flags Engage: an emblem's weapon, in its user's hands only while engaged with that emblem.
            rules.insert(0, 'An engage weapon: wielded only while engaged with its emblem')
        lo, hi = int(r['RangeI'] or 0), int(r['RangeO'] or 0)
        w = {
            'id': f'fe17-{n}', 'name': name, 'romId': n, 'iid': r['Iid'], 'category': CATEGORIES[kind],
            'rank': r['WeaponLevel'] or '', 'range': str(lo) if lo == hi else f'{lo}-{hi}',
            'mt': int(r['Power'] or 0), 'hit': int(r['Hit'] or 0), 'crit': int(r['Critical'] or 0), 'wt': int(r['Weight'] or 0),
            'uses': int(r['Endurance']) if kind == 7 and int(r['Endurance'] or 255) != 255 else None,
            # An engage weapon is never in a unit's items, so never sold: no price.
            'worth': None if flags & ENGAGE else int(r['Price'] or 0), 'effective': effective, 'rules': rules + given,
        }
        if kind == 7:
            del w['crit']
        if flags & REVERSE_ATTRIBUTE and kind not in (6, 7):
            w['magic'] = True
        stats = {key: int(r[f]) for f, key in STAT_FIELDS if r[f] not in ('', '0')}
        if stats:
            w['stats'] = stats
        if flags & ONLY_ENEMY:
            w['onlyEnemy'] = True
        if flags & ENGAGE:
            w['engage'] = True
        weapons.append(w)
    write_refine(weapons)
    lines = ["import type { ChapterWeapon } from '../../components/ChapterWeapons'", '', '/*',
             " * GENERATED by scripts/build-fe17-items.py from Fire Emblem Engage's own item table (item.xml), named from its English text.",
             ' * Do not edit by hand.', ' */',
             'export const FE17_WEAPONS: (ChapterWeapon & { iid: string; onlyEnemy?: true; engage?: true })[] = [']
    lines += ['  ' + json.dumps(w, ensure_ascii=False) + ',' for w in weapons]
    lines.append(']')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'wrote {OUT}: {len(weapons)} weapons')


def write_refine(weapons):
    """Each weapon's refining (item.xml sheet 錬成: a weapon's `RID_` table, the item's id with IID_ for RID_, App.ItemRefineData.Iid2Rid):
    five levels, each its Mt, Wt, Hit and Crit added in all at that level (App.UnitItem.GetPower adds the level's row to the item's)
    and the ore and gold the step to it costs (the next level's row: App.UnitItem.GetNextRefineData). The smithy opens once the
    chapter its facility names is cleared (hubarea.xml), so from the next."""
    tables, rid = {}, None
    for r in D.rows('item', '錬成'):
        if r['Rid']:
            rid = r['Rid']
            tables[rid] = []
            continue
        tables[rid].append(r)
    out = {}
    for w in weapons:
        rows = tables.get('RID_' + w['iid'][4:])
        if not rows:
            continue
        out[w['id']] = [{'mt': w['mt'] + int(r['Power'] or 0), 'hit': w['hit'] + int(r['Hit'] or 0),
                         'crit': w.get('crit', 0) + int(r['Critical'] or 0), 'wt': w['wt'] + int(r['Weight'] or 0),
                         'iron': int(r['Iron'] or 0), 'steel': int(r['Steel'] or 0), 'silver': int(r['Silver'] or 0),
                         'gold': int(r['Price'] or 0)} for r in rows]
    opens = next(r['ConditionCID'] for r in D.rows('hubarea', 1) if r['AID'] == SMITHY).replace('CID_', '')
    story = ['M%03d' % k for k in range(27)]
    at = 'fe17-' + story[story.index(opens) + 1].lower()
    lines = ['/*', " * GENERATED by scripts/build-fe17-items.py from Fire Emblem Engage's refining table (item.xml, sheet 錬成). Do not edit by",
             ' * hand.', ' */', '',
             "/** The chapter the Somniel's smithy is first open before: its facility opens once the chapter before is cleared (hubarea.xml). */",
             f"export const FE17_SMITHY_OPENS = '{at}'", '',
             '/** Each refinable weapon (by id): its five levels, the stats it has at each and the ore and gold the step to it costs. */',
             'export const FE17_REFINE: Record<string, { mt: number; hit: number; crit: number; wt: number; iron: number; steel: number; '
             'silver: number; gold: number }[]> = {']
    lines += [f"  '{k}': {json.dumps(v)}," for k, v in out.items()]
    lines.append('}')
    with open(REFINE_OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'wrote {REFINE_OUT}: {len(out)} refinable weapons, smithy from {at}')


if __name__ == '__main__':
    main()

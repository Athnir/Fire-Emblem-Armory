"""
Echoes: Shadows of Valentia's weapons and equipment, from the game's item table (Data/Item.bin), its skill table (Data/Skill.bin)
and its English text: writes src/data/fe15/fe15Weapons.ts.

Listed: the swords, lances, axes, bows, shields and rings, and the monsters' weapons (foe-only: their classes' own). Not listed: the classes' unarmed
defaults ("Sword", "Lance", "Axe", "Bow": what a unit fights with when nothing is equipped), the illusory heroes' weapons (Exalted
Falchion and the other amiibo summons'), and spells (learned by units, not items). Which of these the player can get is decided by
their sources (scripts/build-fe15-maps.py); src/data/fe15/fe15Listed.ts leaves out the ones nothing gives.

    python scripts/build-fe15-items.py
"""
import json
import os
import re

from fe15_data import EFFECTIVE, KINDS, evolve, forge, item_name, items, say, skills

OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'fe15', 'fe15Weapons.ts')
LISTED = {'Sword', 'Lance', 'Axe', 'Bow', 'Shield', 'Ring', 'Monster'}
# Item.bin's フラグ: 0x02 a class's unarmed default or an illusory hero's weapon (never an item), 0x80 a lord's own, 0x20 Alm's,
# 0x40 Celica's (Royal Sword and Falchion: 0xa1; Beloved Zofia: 0xc1; matching Serenes Forest's "Alm only" / "Celica only").
NOT_AN_ITEM, LORD, ALM, CELICA = 0x02, 0x80, 0x20, 0x40
STATS = [('HP+', 'hp'), ('力+', 'str'), ('技+', 'skl'), ('速さ+', 'spd'), ('運+', 'lck'), ('守備+', 'def'), ('魔防+', 'res'),
         ('移動+', 'mov')]


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower().replace("'", '').replace('ä', 'a')).strip('-')


def skill(sid):
    """A skill or combat art by id. Two shields name 'SID_G.物理半減' / 'SID_G.魔法半減', which no skill has (the table's are
    'SID_G物理半減' and 'SID_G魔法半減'): kept as the game has them, so those arts read as missing."""
    return skills().by_id.get(sid)


def art(sid):
    """A combat art: what it costs and changes (Skill.bin's 戦技 rows). Its 経験値 is the weapon mastery needed to learn it."""
    r = skill(sid)
    if r is None:
        return {'name': None, 'id': sid}
    out = {'name': say(r['名前'], 'Skill'), 'mastery': r['経験値'], 'hp': r['消費HP']}
    for key, field in (('mt', '威力増減'), ('hit', '命中増減'), ('avo', '回避増減'), ('crit', '必殺増減'), ('range', '射程増減')):
        if r[field]:
            out[key] = r[field]
    if r['回数'] > 1:
        out['strikes'] = r['回数']
    if r['攻撃率'] not in (0, 100):
        out['attack'] = r['攻撃率']
    eff = [t for bit, t in EFFECTIVE.items() if r['特効'] & bit]
    if eff:
        out['effective'] = eff
    out['effect'] = (say(r['ヘルプ'], 'Skill') or '').replace('- ', '').replace('\n', ' ')
    return out


def weapon(i, r):
    name = say(r['名前'], 'Item')
    kind = KINDS.get(r['種類'])
    w = {'id': slug(name), 'name': name, 'romId': i, 'category': kind, 'rank': '', 'range': ''}
    lo, hi = r['内射程'], r['外射程']
    w['range'] = '' if not hi else str(lo) if lo == hi else '%d–%d' % (lo, hi)
    if kind not in ('Shield', 'Ring'):
        w.update(mt=r['威力'], hit=r['命中'], crit=r['必殺'])
    w['wt'] = r['重さ']
    lock = None
    if r['フラグ'] & LORD:
        lock = 'Alm only' if r['フラグ'] & ALM else 'Celica only' if r['フラグ'] & CELICA else None
    stats = {key: r[f] for f, key in STATS if r[f]}
    if r['回避']:
        stats['avo'] = r['回避']
    if r['必殺回避']:
        stats['ddg'] = r['必殺回避']
    if stats:
        w['stats'] = stats
    passive = [r[k] for k in ('スキル1', 'スキル2', 'スキル3', 'スキル4', 'スキル1#2', 'スキル2#2', 'スキル3#2', 'スキル4#2') if r[k]]
    effective, rules, named = [], [], []
    for sid in passive:
        s = skill(sid)
        if s is None:
            continue
        for bit, t in EFFECTIVE.items():
            if s['特効'] & bit and t not in effective:
                effective.append(t)
        label, help_ = say(s['名前'], 'Skill'), (say(s['ヘルプ'], 'Skill') or '').replace('- ', '').replace('\n', ' ')
        if label and not s['特効']:
            named.append(label)
            rules.append('%s: %s' % (label, help_) if help_ and help_ != label else label)
    w['effective'] = effective
    w['rules'] = ([lock] if lock else []) + rules
    arts = [art(r[k]) for k in ('戦技1', '戦技2', '戦技3', '戦技4') if r[k]]
    if arts:
        w['arts'] = arts
    if r['練成']:
        rows = forge(r['練成'])
        w['markValue'] = {'silver': rows[0]['silver'], 'gold': rows[0]['gold']}
        if len(rows) > 1:
            w['forge'] = rows[1:]
    if r['進化']:
        w['evolve'] = [dict(e, into=item_name(e['into'])) for e in evolve(r['進化'])]
    return w


def main():
    out, seen = [], {}
    for i, r in enumerate(items().rows):
        kind = KINDS.get(r['種類'])
        # The monsters' claws, fangs and breath are their classes' own weapons too (flag 0x02), but they're what foes fight with.
        if kind not in LISTED or (r['フラグ'] & NOT_AN_ITEM and kind != 'Monster') or not r['名前']:
            continue
        w = weapon(i, r)
        if w['category'] == 'Monster':
            w['foeOnly'] = True
        if w['name'] in seen:
            # The Rusted items: one entry per name, with every outcome its copies evolve into.
            first = seen[w['name']]
            for e in w.get('evolve', []):
                if e not in first.setdefault('evolve', []):
                    first['evolve'].append(e)
            continue
        seen[w['name']] = w
        out.append(w)
    body = ',\n'.join('  ' + json.dumps(w, ensure_ascii=False) for w in out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write("import type { Fe15Weapon } from './fe15Types'\n\n/*\n * GENERATED by scripts/build-fe15-items.py from Echoes' own item"
                " and skill tables (Data/Item.bin, Data/Skill.bin), named from\n * its English text. Do not edit by hand.\n */\n"
                'export const FE15_WEAPONS: Fe15Weapon[] = [\n' + body + ',\n]\n')
    print(len(out), 'weapons')


if __name__ == '__main__':
    main()

"""
Builds src/data/supports/fatesSupports.ts: what each Fates character gives the unit they support.

- Tag Team (fighting next to them): Hit / Avoid / Crit / Dodge per support level.
- Pair Up (paired with them): stats per support level, plus their class's pair-up stats.

These tables aren't in the game files we have, so they come from Serenes Forest's support bonus and
pair-up pages. Run:  python scripts/build-fates-supports.py
"""
import html
import json
import os
import re
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'src', 'data', 'supports', 'fatesSupports.ts')
SITE = 'https://serenesforest.net/fire-emblem-fates/'
TAG_PAGES = ['hoshidan-characters', 'nohrian-characters', 'revelation', 'other-characters']
PAIR_PAGES = ['hoshidan-characters', 'nohrian-characters', 'other-characters']
CLASS_PAGES = ['hoshidan-classes', 'nohrian-classes', 'other-classes']
COMBAT = {'Hit rate': 'hit', 'Hit': 'hit', 'Avoid': 'avoid', 'Critical': 'crit', 'Dodge': 'dodge'}
STATS = {'Str': 'str', 'Mag': 'mag', 'Skl': 'skl', 'Spd': 'spd', 'Lck': 'lck', 'Def': 'def', 'Res': 'res', 'Mov': 'mov'}
BANES = ['Sickly', 'Weak', 'Dull', 'Clumsy', 'Slow', 'Unlucky', 'Fragile', 'Excitable']
BOONS = ['Robust', 'Strong', 'Clever', 'Deft', 'Quick', 'Lucky', 'Sturdy', 'Calm']
# Tag Team tables for the Avatar come in four bane groups, rows in four boon groups.
TAG_BANE_GROUPS = [['Sickly', 'Clumsy'], ['Weak', 'Dull'], ['Slow', 'Fragile'], ['Unlucky', 'Excitable']]
TAG_BOON_GROUPS = [['Robust', 'Deft'], ['Strong', 'Clever'], ['Quick', 'Sturdy'], ['Lucky', 'Calm']]


def fetch(path):
    req = urllib.request.Request(SITE + path + '/', headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')


def tables(page):
    out = []
    for tb in re.findall(r'<table.*?</table>', page, re.S):
        rows = [[html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
                for r in re.findall(r'<tr.*?</tr>', tb, re.S)]
        if rows and rows[0] and rows[0][0] != 'Navigation' and rows[0][0] != 'Page':
            out.append(rows)
    return out


def bonus(cell, names):
    """'Hit rate +5, Critical +3' -> {'hit': 5, 'crit': 3}; '–' -> {}."""
    out = {}
    for name, n in re.findall(r'([A-Za-z ]+?)\s*\+(\d+)', cell):
        key = names.get(name.strip())
        if key:
            out[key] = out.get(key, 0) + int(n)
    return out


def names_in(cell):
    # Serenes' Revelation table runs two names together ("Oboro Hinata"); split them back.
    cell = cell.replace('Oboro Hinata', 'Oboro, Hinata')
    return [n.strip() for n in re.split(r',|\n', cell) if n.strip()]


def main():
    tag, tag_avatar = {}, {}
    for p in TAG_PAGES:
        ts = tables(fetch(p + '/supports/support-bonus'))
        for t in ts:
            head = t[0][0]
            if head == 'Boon':
                continue
            for row in t[1:]:
                if row[0] == 'Any':
                    continue  # children: their parents' bonuses (noted in the app)
                levels = [bonus(c, COMBAT) for c in row[1:6]]
                for n in names_in(row[0]):
                    if n in tag and tag[n] != levels:
                        raise SystemExit(f'Tag Team bonuses for {n} differ between pages')
                    tag[n] = levels
        if p == 'hoshidan-characters':
            boon_tables = [t for t in ts if t[0][0] == 'Boon']
            for gi, t in enumerate(boon_tables):
                for row in t[1:]:
                    gj = next(i for i, g in enumerate(TAG_BOON_GROUPS) if row[0].startswith(g[0]))
                    for bane in TAG_BANE_GROUPS[gi]:
                        for boon in TAG_BOON_GROUPS[gj]:
                            tag_avatar.setdefault(boon, {})[bane] = [bonus(c, COMBAT) for c in row[1:6]]
    pair, pair_avatar = {}, {}
    for p in PAIR_PAGES:
        ts = tables(fetch(p + '/pair-up-stats'))
        for t in ts:
            if t[0][0] == 'Boon':
                if p != 'hoshidan-characters':
                    continue
                dash = next(r[0] for r in t[1:] if r[1] in ('–', '-'))
                bane = BANES[BOONS.index(dash.split()[0])]
                for row in t[1:]:
                    if row[1] in ('–', '-'):
                        continue
                    pair_avatar.setdefault(row[0].split()[0], {})[bane] = [bonus(c, STATS) for c in row[1:5]]
                continue
            for row in t[1:]:
                if row[0] == 'Any':
                    continue
                pair[row[0]] = [bonus(c, STATS) for c in row[1:5]]
    classes = {}
    for p in CLASS_PAGES:
        for t in tables(fetch(p + '/pair-up-stats')):
            if t[0][:2] != ['Name', 'Str']:
                continue
            cols = [STATS[c] for c in t[0][1:]]
            for row in t[1:]:
                classes[row[0]] = {k: int(v) for k, v in zip(cols, row[1:]) if v.strip().lstrip('+').isdigit() and int(v)}

    def ts_obj(d):
        return '{ ' + ', '.join(f'{k}: {v}' for k, v in d.items()) + ' }' if d else '{}'

    lines = [
        "import type { CombatBonus, StatBonus } from './types'",
        '',
        '/*',
        " * GENERATED by scripts/build-fates-supports.py from Serenes Forest's Fates support bonus and pair-up",
        " * pages (these tables aren't in the game files we have). Do not edit by hand.",
        ' *',
        ' * Each level lists only what that level adds; the totals are cumulative (S = No + C + B + A + S).',
        ' */',
        '',
        '/** Fighting next to this unit (Tag Team): No support, C, B, A, S. */',
        'export const FATES_TAG_TEAM: Record<string, CombatBonus[]> = {',
    ]
    for n, levels in sorted(tag.items()):
        lines.append(f'  {json.dumps(n)}: [' + ', '.join(ts_obj(x) for x in levels) + '],')
    lines += ['}', '', "/** The Avatar's Tag Team bonuses, by boon then bane. */",
              'export const FATES_TAG_TEAM_AVATAR: Record<string, Record<string, CombatBonus[]>> = {']
    for boon, by in tag_avatar.items():
        lines.append(f'  {boon}: {{ ' + ', '.join(f'{bane}: [' + ', '.join(ts_obj(x) for x in lv) + ']' for bane, lv in by.items()) + ' },')
    lines += ['}', '', '/** Paired up with this unit: the stats each support level adds (C, B, A, S), on top of their class. */',
              'export const FATES_PAIR_UP: Record<string, StatBonus[]> = {']
    for n, levels in sorted(pair.items()):
        lines.append(f'  {json.dumps(n)}: [' + ', '.join(ts_obj(x) for x in levels) + '],')
    lines += ['}', '', "/** The Avatar's Pair Up stats per support level, by boon then bane. */",
              'export const FATES_PAIR_UP_AVATAR: Record<string, Record<string, StatBonus[]>> = {']
    for boon, by in pair_avatar.items():
        lines.append(f'  {boon}: {{ ' + ', '.join(f'{bane}: [' + ', '.join(ts_obj(x) for x in lv) + ']' for bane, lv in by.items()) + ' },')
    lines += ['}', '', "/** Each class's Pair Up stats: what the partner's class adds to the lead. */",
              'export const FATES_CLASS_PAIR_UP: Record<string, StatBonus> = {']
    for c, d in classes.items():
        lines.append(f'  {json.dumps(c)}: {ts_obj(d)},')
    lines.append('}')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(tag), 'tag team,', len(pair), 'pair up,', len(classes), 'classes,',
          len(tag_avatar), 'boons for the Avatar')


if __name__ == '__main__':
    main()

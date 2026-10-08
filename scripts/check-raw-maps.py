"""
Sanity-checks data-raw/fates/<route>/: every wiki and minimap file parses, each terrain guess matches
the map size, and each difficulty's minimap census adds up to the wiki's starting-enemy total.

Census rule: a tile with 8+ red pixels is a pair-up (2 units), 3–7 is one unit. A boss's glow can add a
few red pixels, so a tile flagged here usually needs a look by eye at build time, not a data fix.

Usage:  python scripts/check-raw-maps.py [route]     (default: conquest)
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fates')
route = sys.argv[1] if len(sys.argv) > 1 else 'conquest'
base = os.path.join(ROOT, route)

wiki = {}
for f in glob.glob(os.path.join(base, 'wiki', '*.json')):
    key = os.path.basename(f).split('-')[0]
    wiki['endgame' if key == '28' else key] = json.load(open(f, encoding='utf-8'))

problems = 0
for f in sorted(glob.glob(os.path.join(base, 'minimap', '*.json'))):
    m = json.load(open(f, encoding='utf-8'))
    ch = m['chapter']
    w = wiki.get(ch)
    line = [f'{ch:>7} {m["width"]}x{m["height"]}']
    if w and list(w['dims']) != [m['width'], m['height']]:
        line.append(f'DIMS wiki {w["dims"]}')
        problems += 1
    if len(m['guess']) != m['height'] or any(len(r) != m['width'] for r in m['guess']):
        line.append('GUESS-SIZE')
        problems += 1
    for d in ('Normal', 'Hard', 'Lunatic'):
        img = m['difficulty'].get(d) or m['difficulty'].get('Normal' if d == 'Hard' else 'Hard') or m['difficulty']['Normal']
        n = sum(2 if c >= 8 else 1 for c in img['red'].values())
        want = w['initial'].get(d, {}).get('total') if w else None
        mark = 'ok' if want == n else f'census {n} vs wiki {want}'
        if want != n:
            problems += 1
            odd = [t for t, c in img['red'].items() if c not in (4, 8)]
            if odd:
                mark += f' (check {", ".join(odd)})'
        line.append(f'{d[0]}:{mark}')
    print('  '.join(line))
print(f'\n{problems} item(s) to look at.')

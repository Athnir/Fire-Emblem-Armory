"""Turn Fates terrain files into the app's terrain letters, plus veins, changes, pots, chests and doors."""
import re
from fates_terrain import read

# Base terrain name (Japanese TID, before any ／ ｜ ＃ （ ） decoration) -> app letter.
BASE = {
    '平地': '.', '床': '.', '剣の間': '.', '剣の間2': '.', '暗夜床': '.', '回復床': 'H', '回復床50': 'H',
    '林': 'f', '深い森': 'k',
    '砦': 'F', '済砦': 'F', '座布団': 'F', '廃墟門': 'G', '城門': 'g', '玉座': 't', '門口': 'S',
    '階段': 'S', '宝箱': 'c', '扉': 'd', '襖': 'd',
    '橋': 'b', '村': 'v', '廃村': 'B', '閉じ村': 'B',
    '荒地': 'W', '柱': 'p', '太柱': '#',
    '壁': '#', '移動不可': '#', '御神木': '#', '古木': '#', '土塁': '#', '隆起': '#', '防壁': '#', '水壁': '#',
    '断崖': '#', '桜': '#', '篝火': '#', '大樹': '#', '本棚': '#', '水晶玉': '#',
    '空': 'x', '風の渦': 'x', '竜巻': 'x', '湖': 'w', '河': 'w', '海': 'w', '湖地専': 'w', '泉': 'w', '堀': 'w', '空堀': '.',
    '瓦礫': 'r', '庭石': 'r', '低壁': 'l', '山': 'n', '高山': 'C', '崖': 'C', '低建物': 'B', '建物': 'B',
    '弓砲台': 'L', '魔道砲台': 'L', '暗器砲台': 'L', '撒菱': 'T',
    '良薬': '.', '劇薬': '.',
}
POT = {'良薬': 'medicine', '劇薬': 'poison'}


def parse_tid(tid):
    """'TID_扉／床｜床' -> ('扉', after-vein '床', after-break '床', vein?, qualifier)"""
    t = tid[4:]
    vein = '＃竜脈' in t
    t = t.replace('＃竜脈', '')
    qual = ''
    m = re.search(r'（[^）]*）', t)
    if m:
        qual = m.group(0)
        t = t.replace(qual, '')
    t = re.sub(r'[@＠].*', '', t)
    broken = None
    if '｜' in t:
        t, broken = t.split('｜', 1)
    after = None
    if '／' in t:
        t, after = t.split('／', 1)
    return t, after, broken, vein, qual


def letter(name, qual=''):
    if qual == '（移動不可）':
        return '#'
    return BASE.get(name)


def convert(path):
    t = read(path)
    W, H = t['w'] - 2, t['h'] - 2
    grid, unknown, veins, changes, pots, chests, doors = {}, set(), [], [], [], [], []
    for r in range(1, t['h'] - 1):
        for c in range(1, t['w'] - 1):
            ty = t['types'][t['rows'][r][c]]
            name, after, broken, vein, qual = parse_tid(ty['tid'])
            x, y = c, H + 1 - r
            L = letter(name, qual)
            if L is None:
                unknown.add(ty['tid'])
                L = '?'
            grid[(x, y)] = L
            if vein:
                veins.append((x, y))
            if name in POT:
                pots.append(((x, y), POT[name]))
            if L == 'c':
                chests.append((x, y))
            if L == 'd':
                doors.append((x, y))
            if after:
                A = letter(after.replace('＃竜脈', ''))
                if A and A != L:
                    changes.append(((x, y), A, ty['tid']))
    rows = [''.join(grid[(x, y)] for x in range(1, W + 1)) for y in range(H, 0, -1)]
    stats = {}
    for ty in t['types']:
        name = parse_tid(ty['tid'])[0]
        r4 = ty['raw'][4]
        stats[ty['tid']] = {'class': ty['raw'][5], 'def': (r4 >> 8 & 0xFF) - (256 if r4 >> 8 & 0x80 else 0),
                            'avo': (r4 >> 16 & 0xFF) - (256 if r4 >> 16 & 0x80 else 0), 'heal': (r4 >> 24 & 0xFF) - (256 if r4 >> 24 & 0x80 else 0)}
    return {'field': t['field'], 'w': W, 'h': H, 'grid': rows, 'unknown': unknown, 'veins': veins,
            'changes': changes, 'pots': pots, 'chests': chests, 'doors': doors, 'stats': stats}

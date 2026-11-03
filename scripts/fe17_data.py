"""Read Fire Emblem Engage's data as fe17_extract.py copies it into data-raw/fe17/romfs (data-raw/fe17/README.md has the formats).

    book(name)              a data table: {sheet name: [row dicts by the header's field names (Ident)]}, sheets in their order
    rows(name, sheet=0)     one sheet's rows (by its index or Japanese name)
    text(label)             a text label's English (MIID_IronSword -> 'Iron Sword'), from every message file
    messages(name)          one message file: {label: text}
    terrain(name)           a map's terrain grid: {'x', 'z', 'width', 'height', 'tiles': 32x32 terrain ids, row z*32 + x}
    dispos(name)            a battle's units: [(group, [row dicts])], groups in their order
    script(name)            a battle's Lua script
"""
import functools
import json
import os
import struct
import xml.etree.ElementTree as ET

ROMFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-raw', 'fe17', 'romfs')
GRID = 32      # every terrain grid is 32 x 32 tiles; the map's window sits inside it


@functools.lru_cache(maxsize=None)
def book(name):
    """A data table (an XML book: sheets, each a header of fields and rows of values): {sheet name: [rows]}. A row is a dict by the
    fields' Idents, every value a string as the book has it ('' for none)."""
    root = ET.parse(os.path.join(ROMFS, 'gamedata', name + '.xml')).getroot()
    out = {}
    for sheet in root.findall('Sheet'):
        idents = [p.get('Ident') for p in sheet.find('Header')]
        out[sheet.get('Name')] = [{k: p.get(k, '') for k in idents} for p in sheet.find('Data')]
    return out


def rows(name, sheet=0):
    b = book(name)
    return b[sheet] if isinstance(sheet, str) else list(b.values())[sheet]


def header(name, sheet=0):
    """A sheet's fields: [(Ident, Japanese name, type)]."""
    root = ET.parse(os.path.join(ROMFS, 'gamedata', name + '.xml')).getroot()
    sheets = root.findall('Sheet')
    s = next(x for x in sheets if x.get('Name') == sheet) if isinstance(sheet, str) else sheets[sheet]
    return [(p.get('Ident'), p.get('Name'), p.get('Type')) for p in s.find('Header')]


def parse_msbt(d):
    """A message file (MSBT, UTF-16): {label: text}. Control tags (0x0E group, type, params) are written [g:t:hex], closing tags
    (0x0F) [/g:t]."""
    assert d[:8] == b'MsgStdBn' and d[8:10] == b'\xff\xfe', d[:10]
    assert d[0xC] == 1, 'not UTF-16'
    sections, p = {}, 0x20
    for _ in range(struct.unpack_from('<H', d, 0xE)[0]):
        magic, size = d[p:p + 4].decode(), struct.unpack_from('<I', d, p + 4)[0]
        sections[magic] = d[p + 16:p + 16 + size]
        p = (p + 16 + size + 15) // 16 * 16
    lbl, labels = sections['LBL1'], {}
    for b in range(struct.unpack_from('<I', lbl, 0)[0]):
        count, off = struct.unpack_from('<II', lbl, 4 + 8 * b)
        for _ in range(count):
            n = lbl[off]
            labels[struct.unpack_from('<I', lbl, off + 1 + n)[0]] = lbl[off + 1:off + 1 + n].decode()
            off += 1 + n + 4
    txt = sections['TXT2']
    count = struct.unpack_from('<I', txt, 0)[0]
    offsets = list(struct.unpack_from(f'<{count}I', txt, 4)) + [len(txt)]
    out = {}
    for i in range(count):
        raw, k, s = txt[offsets[i]:offsets[i + 1]], 0, []
        while k + 1 < len(raw):
            c = struct.unpack_from('<H', raw, k)[0]
            k += 2
            if c == 0:
                break
            if c == 0x0E:
                g, t, n = struct.unpack_from('<HHH', raw, k)
                s.append(f'[{g}:{t}:{raw[k + 6:k + 6 + n].hex()}]')
                k += 6 + n
            elif c == 0x0F:
                g, t = struct.unpack_from('<HH', raw, k)
                s.append(f'[/{g}:{t}]')
                k += 4
            else:
                s.append(chr(c))
        out[labels[i]] = ''.join(s)
    return out


@functools.lru_cache(maxsize=None)
def messages(name):
    return parse_msbt(open(os.path.join(ROMFS, 'message', name + '.msbt'), 'rb').read())


@functools.lru_cache(maxsize=None)
def _all_text():
    """Every label of every English message file (a label two files share keeps the first file's, in name order)."""
    out = {}
    folder = os.path.join(ROMFS, 'message')
    for f in sorted(os.listdir(folder)):
        for k, v in messages(f[:-5]).items():
            out.setdefault(k, v)
    return out


def text(label, default=None):
    return _all_text().get(label, default)


@functools.lru_cache(maxsize=None)
def terrain(name):
    """A map's terrain (terrains/mapterrain_<name>.json): its window inside the 32x32 grid and the grid's terrain ids by z*32 + x;
    its layers (what stands over the grid at the start, each a rect: X, Y, W, H, its Attr a terrain id, a Group opened together:
    doors, breakable walls, roofs) and overlaps (one tile each, its Attr a lasting effect: puddles, fog, miasma, fire)."""
    t = json.load(open(os.path.join(ROMFS, 'terrains', f'mapterrain_{name.lower()}.json'), encoding='utf-8'))
    assert len(t['m_Terrains']) == GRID * GRID, len(t['m_Terrains'])
    return {'x': t['m_X'], 'z': t['m_Z'], 'width': t['m_Width'], 'height': t['m_Height'], 'tiles': t['m_Terrains'],
            'layers': t.get('m_Layers', []), 'overlaps': t.get('m_Overlaps', [])}


@functools.lru_cache(maxsize=None)
def dispos(name):
    """A battle's units (gamedata/dispos/<name>.xml): [(group, [units])]. A row naming a Group starts the next group."""
    out = []
    for r in rows(f'dispos/{name.lower()}'):
        if r['Group']:
            out.append((r['Group'], []))
        else:
            out[-1][1].append(r)
    return out


def script(name):
    with open(os.path.join(ROMFS, 'scripts', name.lower() + '.lua'), encoding='utf-8-sig') as f:
        return f.read()


def flag_list(value):
    """A ';'-separated list field ('CID_C001_1;CID_C001_2;') as a list."""
    return [x for x in value.split(';') if x]


# What an item id's parts say, for telling apart items the game gives one English name (four Libérations, each emblem's own Rapier,
# the weaker copies the Divine Paralogues' foes carry).
_ID_TAGS = [('改_ノーマル', 'upgraded, Normal'), ('改', 'upgraded'), ('＋＋', '++'), ('＋', '+'), ('_最弱', 'weakest'),
            ('_微弱', 'a little weaker'), ('_弱', 'weaker'), ('_微強', 'a little stronger'), ('_最強', 'strongest'),
            ('_強', 'stronger'), ('_低命中', 'lower Hit'), ('闇', 'dark'), ('黒', 'dark'), ('_竜族', 'dragons'),
            ('_重装', 'armoured'), ('_気功', 'Arts'), ('_風魔法', 'wind'), ('_炎魔法', 'fire'), ('_雷魔法', 'thunder')]


@functools.lru_cache(maxsize=None)
def _emblems():
    """Each emblem's id name (GID_マルス -> マルス) -> its English name."""
    out = {}
    for r in rows('god'):
        if r['Gid'].startswith('GID_') and r['Mid']:
            name = text(r['Mid'])
            if name:
                out.setdefault(r['Gid'][4:], name)
    out.setdefault('三級長', 'Edelgard, Dimitri and Claude')
    return out


@functools.lru_cache(maxsize=None)
def _item_names():
    names = {}
    for r in rows('item'):
        if r['Name'] and r['Kind'] in [str(k) for k in range(1, 10)]:
            names.setdefault(text(r['Name']), []).append(r['Iid'])
    return names


def item_label(iid):
    """An item's name, unique among the weapons: the game's English name, with what its id says added where another weapon has the
    same name ('Rapier (Emblem Marth)', 'Libération (upgraded)', 'Levin Sword (Emblem Chrom, foes)')."""
    r = next((x for x in rows('item') if x['Iid'] == iid), None)
    if r is None or not r['Name']:
        return None
    name = text(r['Name'])
    same = _item_names().get(name, [iid])
    if len(same) <= 1 or not name:
        return name
    rest = iid[4:]
    tags = []
    for jp, en in _emblems().items():
        if rest.startswith(jp + '_'):
            tags.append(f'Emblem {en}')
            rest = rest[len(jp) + 1:]
            break
    else:
        # A boss's own attack ('IID_ソンブル_物理攻撃'): whose it is.
        owner = next((x for x in rows('person') if x['Pid'] == 'PID_' + rest.split('_')[0]), None)
        if owner is not None and '_' in rest:
            tags.append(text(owner['Name']) + "'s")
    m = __import__('re').search(r'_(M|S|G|E)(\d{3})', rest)
    if m:
        kind = {'M': 'Chapter', 'S': 'Paralogue', 'G': 'Divine Paralogue', 'E': 'Fell Xenologue'}[m.group(1)]
        num = int(m.group(2))
        tags.append('Prologue' if (kind == 'Chapter' and num == 0) else f'{kind} {num}' if kind != 'Divine Paralogue' else kind)
    if '_通常' in rest or rest.endswith('通常'):
        tags.append('foes')
    for jp, en in _ID_TAGS:
        if jp in rest:
            tags.append(en)
            rest = rest.replace(jp, '')
    for who in ('セピア', 'グリ'):
        if who + '専用' in rest:
            p = next((x for x in rows('person') if x['Pid'] == 'PID_' + who), None)
            tags.append((text(p['Name']) if p else who) + "'s")
    if not tags:
        return name
    return f"{name} ({', '.join(tags)})"

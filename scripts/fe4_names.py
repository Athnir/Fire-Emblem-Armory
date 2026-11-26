"""
Genealogy of the Holy War's English names, read from Lil' Nordion, the translation patch Serenes Forest hosts. The patch is applied in
memory to the user's clean ROM (scripts/bps.py) and only its name tables are read: every number and table the generators use still
comes from the clean Japanese ROM. Nothing patched is written anywhere.

The patch zip sits next to the ROM in Documents\\FE Games (or set FE4_PATCH). Its name tables keep the ROM's own pointers, moved to
bank $50:
  - items: u16 pointers at $8D:9402, by item id;
  - classes: u16 pointers at $8D:9892, by class id;
  - playable characters: u16 pointers at $8D:920D, by the character record's name index (63 names);
  - castle labels: a list of strings in $50:4A00 onward (the castle names shown on the map; matched to the ROM's kana names in
    PLACES below, each checked to be in the patch).
Bosses and other foes have no name table in either version (their names appear only in the dialogue), so `spelling()` reads the
dialogue, and only what the game shows of it: the patch keeps older drafts of much of its script beside the text it uses (Chapter 7's
"Yied's fallen... Fort Melgen... Jabarro" next to "Aed's fallen... Fort Mergen... Javarro"), and no pointer leads to them (`shown`).

    python scripts/fe4_names.py           # prints every table
"""
import functools
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bps import apply  # noqa: E402
from fe4_rom import R  # noqa: E402

PATCH = os.environ.get('FE4_PATCH', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'Lil-Nordion 1.01.zip'))
PATCH_FILE = 'Lil-Nordion 1.01.bps'
NAME_BANK = 0x500000
ITEM_NAMES, CLASS_NAMES, CHARACTER_NAMES = 0xD9402, 0xD9892, 0xD920D
PLACE_LABELS = 0x504A00, 0x504CC0

# The patch's text: A-Z from 0x10, a-z from 0x2A, 0xBF a space, and a few marks and accented letters. The accented letters keep
# ISO-8859-1's order, capitals 0x56 below it (0x6B Á in "Ásmundr", 0x73 É in "Ériu") and small letters 0x58 below (0x89 á, 0x95 í in
# "Díthorba", 0x97 ï in "naïve", 0x9B ó, 0x9E ö; then ü at 0xA3, ÷ left out).
CHARS = {**{0x10 + i: chr(65 + i) for i in range(26)}, **{0x2A + i: chr(97 + i) for i in range(26)}, 0xBF: ' ', 0x44: '.', 0x45: ',',
         0x46: '?', 0x47: '!', 0x48: "'", 0x49: '-', 0x73: 'É', 0x89: 'á', 0x95: 'í', 0x9B: 'ó', 0x9E: 'ö', 0xA3: 'ü'}
ENCODE = {v: k for k, v in CHARS.items()}

# The ROM's kana castle names (scripts/fe4_events.py place_names) and the patch's castle labels.
PLACES = {
    'マディノ': 'Madino', 'シルベール': 'Sylvale', 'アンフォニー': 'Infini', 'アグスティ': 'Agusti', 'ハイライン': 'Hochrhein',
    'マッキリー': 'Makariy', 'ノディオン': 'Nordion', 'ヴェルトマー': 'Velthomer', 'フリージ': 'Friege', 'バーハラ': 'Belhalla',
    'ドズル': 'Dozel', 'エッダ': 'Edda', 'シアルフィ': 'Chalphy', 'ユングヴィ': 'Yngvi', 'レンスター': 'Leonster', 'コノート': 'Connacht',
    'マンスター': 'Munster', 'メルゲン': 'Mergen', 'アルスター': 'Ulster', 'オーガヒル': 'Orgahil', 'トーヴェ': 'Tófa',
    'セイレーン': 'Seiren', 'ザクソン': 'Zaxon', 'シレジア': 'Silesse', 'リューベック': 'Lübeck', 'ティルナノグ': 'Tirnanog',
    'ガネーシャ': 'Ganesha', 'ソファラ': 'Sophara', 'イザーク': 'Isaach', 'リボー': 'Ribaut', 'フィノーラ': 'Fionnuala',
    'イード': 'Aed', 'ダーナ': 'Dahna', 'ヴェルダン': 'Verdane', 'エバンス': 'Evans', 'ジェノア': 'Genoa', 'マーファ': 'Marpha',
    'ミレトス': 'Miletos', 'ペルルーク': 'Plutarch', 'クロノス': 'Kronos', 'ラドス': 'Rhódos', 'ミーズ': 'Meath',
    'カパトギア': 'Cappadocia', 'ルテキア': 'Lutetia', 'トラキア': 'Thracia', 'グルティア': 'Galatia',
}


@functools.lru_cache(maxsize=None)
def patched():
    with zipfile.ZipFile(PATCH) as z:
        return apply(bytes(R), z.read(PATCH_FILE))


def decode(b):
    return ''.join(CHARS.get(x, '') for x in b if x in CHARS)


def string_at(o):
    p = patched()
    return decode(p[o:p.index(b'\x01', o)])


def table(at, count):
    p = patched()
    return [string_at(NAME_BANK + (p[at + 2 * i] | p[at + 2 * i + 1] << 8)) for i in range(count)]


def item_names(count=0x8A):
    return dict(enumerate(table(ITEM_NAMES, count)))


def class_names(count=72):
    return dict(enumerate(table(CLASS_NAMES, count)))


def character_names(count=63):
    return table(CHARACTER_NAMES, count)


@functools.lru_cache(maxsize=None)
def place_labels():
    """The patch's castle labels, in its order."""
    p, (start, end) = patched(), PLACE_LABELS
    return [s for s in (decode(x) for x in p[start:end].split(b'\x01')) if s]


def in_text(name):
    """Whether the patch's text uses this spelling anywhere (case as given)."""
    try:
        return bytes(ENCODE[c] for c in name) in patched()
    except KeyError:
        return False


@functools.lru_cache(maxsize=None)
def _text():
    """The patch's added banks as text, lower-cased (other bytes become NUL), for spelling checks."""
    p = patched()
    return ''.join(CHARS.get(x, '\0') for x in p[0x500000:]).lower()


# The control codes (00 xx) whose operands can be 0x01, the byte that otherwise ends a string, and how many operand bytes they take:
# 00 3F a portrait (u16 id: Fisher's scene shows portraits 0x1B8 and 0x1B5), 00 82 the map tour's camera on a unit (a byte, then the
# unit's u16 id: Sigurd's 01 00), 00 12 and 00 86 one each (a 0x01 after them is never followed by a string the patch points to).
OPERANDS = {0x3F: 2, 0x82: 3, 0x12: 1, 0x86: 1}


@functools.lru_cache(maxsize=None)
def _pointed():
    """Where the patch's own pointers lead: every 3-byte value into its banks ($50 on) that sits in bytes it changed in the original
    4 MB (the scenes' text commands, 0x0C and 0x14, and the death quotes' table at $8E:F67A) or in its code bank $50 (the epilogue's
    pointers at $50:9010). A value in bytes it left alone is the clean ROM's code or art, which only matches by chance."""
    import numpy as np
    p, c = np.frombuffer(patched(), dtype=np.uint8), np.frombuffer(R, dtype=np.uint8)
    n = len(c)
    v = p[:-2].astype(np.uint32) | p[1:-1].astype(np.uint32) << 8 | p[2:].astype(np.uint32) << 16
    written = np.zeros(len(v), dtype=bool)
    written[:n - 2] = (p[:n - 2] != c[:n - 2]) | (p[1:n - 1] != c[1:n - 1]) | (p[2:n] != c[2:n])
    written[NAME_BANK:NAME_BANK + 0x10000] = True
    return frozenset(v[written & (v >= NAME_BANK)].tolist())


def shown(o):
    """Whether the patch's text at file offset o is shown in the game: the string it's in (from the last 0x01 before it that ends one,
    not a control code's operand) is where one of the patch's pointers leads. Checked on the names: each of the 13 Javarros and 9
    Raisas in the dialogue is shown, the older drafts' Jabarros, Lizas, Elliots and Fort Melgen not."""
    p, s = patched(), o
    while True:
        s = p.rfind(b'\x01', NAME_BANK, s)
        if s < 0:
            return False
        if p[s - 1] == 0 or any(p[s - k - 1] == 0 and k <= OPERANDS.get(p[s - k], 0) for k in (1, 2, 3)):
            continue  # an operand
        return s + 1 in _pointed()


def spelling(*candidates):
    """The first candidate the patch's text shows (ignoring case), in the patch's own capitalisation, or None. The patch has no table
    for bosses and other foes, so their names are taken from its dialogue this way (Serenes' Dimaggio is its DiMaggio); only text the
    game shows counts (`shown`), so the older drafts' spellings don't."""
    text, p = _text(), patched()
    for c in candidates:
        if not c:
            continue
        i = text.find(c.lower())
        while i >= 0:
            # a whole word: not run into other letters
            before = text[i - 1] if i else '\0'
            after = text[i + len(c)] if i + len(c) < len(text) else '\0'
            if not before.isalpha() and not after.isalpha() and shown(NAME_BANK + i):
                return decode(p[NAME_BANK + i:NAME_BANK + i + len(c)])
            i = text.find(c.lower(), i + 1)
    return None


def place(kana):
    """The patch's name for a castle, by the ROM's kana name; checked to be one of its labels or in its text."""
    name = PLACES[kana]
    assert name in place_labels() or in_text(name), (kana, name)
    return name


# The terrain window: the patch replaces the game's own names ($84:8EFB, Shift-JIS through $83:837B) with drawn ones (`JSL $51:0800`).
# Per terrain id, 16 bytes at $50:3000 (+0: how many 8 x 8 tiles wide) and its name drawn at $58:0000 + id x 0x200, 2bpp: the top row's
# tiles, then (0x100 on) the bottom row's. Colour 2 is the letters' ink (1 a few softened pixels), 3 their outline.
TERRAIN_WINDOW = 0x503000
TERRAIN_DRAWN = 0x580000
# What the drawn names say, ids 0-25, read off the drawing; terrain_names() checks them against the drawn letters.
TERRAIN_WORDS = ['Peak', 'Thicket', 'Cliff', 'Plain', 'Forest', 'Sea', 'River', 'Mountain', 'Desert', 'Castle', 'Fort', 'House', 'Gate',
                 'Rampart', 'Sand', 'Bridge', 'Swamp', 'Gate', 'Village', 'Ruins', 'Depository', 'Ruins', 'Church', 'Temple', 'Bragi Tower',
                 'Road']


def _drawn(i):
    """Terrain id i's drawn name as rows of ink (1) and the rest (0), 16 pixels tall."""
    p = patched()
    count, base = p[TERRAIN_WINDOW + 16 * i], TERRAIN_DRAWN + 0x200 * i
    img = [[0] * (8 * count) for _ in range(16)]
    for half in range(2):
        for t in range(count):
            o = base + 0x100 * half + 16 * t
            for y in range(8):
                for x in range(8):
                    v = (p[o + 2 * y] >> (7 - x) & 1) | (p[o + 2 * y + 1] >> (7 - x) & 1) << 1
                    img[8 * half + y][8 * t + x] = 1 if v in (1, 2) else 0
    return img


def _pieces(img):
    """The drawing cut at the columns with no ink: each piece a letter, or two that touch."""
    cols = [any(row[x] for row in img) for x in range(len(img[0]))]
    out, start = [], None
    for x in range(len(cols) + 1):
        if x < len(cols) and cols[x]:
            start = x if start is None else start
        elif start is not None:
            out.append(tuple(tuple(row[start:x]) for row in img))
            start = None
    return out


def _beside(a, b, overlap):
    """Two letters' shapes side by side, `overlap` columns shared."""
    wa, wb = len(a[0]), len(b[0])
    return tuple(tuple((a[y][x] if x < wa else 0) | (b[y][x - wa + overlap] if 0 <= x - wa + overlap < wb else 0)
                       for x in range(wa + wb - overlap)) for y in range(16))


@functools.lru_cache(maxsize=None)
def terrain_names():
    """{terrain id: name}: TERRAIN_WORDS, checked against the patch's drawn letters. Each name is cut at the columns with no ink; a
    letter must have one shape wherever it's drawn and no two letters one shape, and a piece where two letters touch (a t's bar, the
    F of Fort and Forest against its o) must be the two side by side. A letter seen only touching a known one is learnt from that."""
    shapes, left = {}, []
    for i, word in enumerate(TERRAIN_WORDS):
        letters, pieces = word.replace(' ', ''), _pieces(_drawn(i))
        if len(pieces) == len(letters):
            for ch, g in zip(letters, pieces):
                assert shapes.setdefault(ch, g) == g, (word, ch)
        else:
            left.append((word, letters, pieces))
    def read(letters, pieces, j=0, k=0, learnt=None):
        """The letters this word's pieces teach, or None if they can't be read as it: each piece one letter, or two that touch."""
        learnt = learnt or {}
        if k == len(pieces):
            return learnt if j == len(letters) else None
        known = lambda ch: shapes.get(ch) or learnt.get(ch)  # noqa: E731
        g, ways = pieces[k], []
        if j < len(letters):
            if known(letters[j]) == g:
                ways.append((j + 1, learnt))
            elif not known(letters[j]):
                ways.append((j + 1, {**learnt, letters[j]: g}))
        if j + 1 < len(letters):
            a, b = known(letters[j]), known(letters[j + 1])
            if a and b and any(_beside(a, b, ov) == g for ov in (0, 1, 2)):
                ways.append((j + 2, learnt))
            elif not a and b:   # an unknown letter touching a known one: the piece less the known letter on its right
                for ov in (0, 1, 2):
                    cut = tuple(row[:len(g[0]) - len(b[0]) + ov] for row in g)
                    if cut[0] and _beside(cut, b, ov) == g:
                        ways.append((j + 2, {**learnt, letters[j]: cut}))
        for j2, l2 in ways:
            got = read(letters, pieces, j2, k + 1, l2)
            if got is not None:
                return got
        return None

    for _ in range(len(left) + 1):
        later = []
        for word, letters, pieces in left:
            got = read(letters, pieces)
            if got is None:
                later.append((word, letters, pieces))
                continue
            for ch, g in got.items():
                assert shapes.setdefault(ch, g) == g, (word, ch)
        left = later
    assert not left, [w for w, _, _ in left]
    assert len(set(shapes.values())) == len(shapes), 'two letters share a shape'
    return dict(enumerate(TERRAIN_WORDS))


# The chapters' headings and titles, as the patch's turn record lists them ($69:9192): `[heading] 4C BF [title] 02`, then the screen's
# own bytes, chapter after chapter (digits from 0x50). The older list at $68:3112 ("Birth of a Crusader"...) is unused.
CHAPTER_TITLES = 0x699192


@functools.lru_cache(maxsize=None)
def chapter_titles():
    """[(heading, title)] for the twelve chapters: ('Prologue', 'Birth of a Holy Knight'), ('Ch. 1', 'Lady of the Forest')...
    ('Endgame', 'End of the Holy War')."""
    p = patched()
    chars = {**CHARS, **{0x50 + i: str(i) for i in range(10)}, 0x4C: ':'}
    out, o = [], CHAPTER_TITLES
    while len(out) < 12:
        colon = p.index(bytes([0x4C, 0xBF]), o)
        start = colon
        while start > o and p[start - 1] in chars:
            start -= 1
        end = p.index(bytes([0x02]), colon)
        heading = ''.join(chars[x] for x in p[start:colon])
        title = ''.join(chars[x] for x in p[colon + 2:end])
        out.append((heading, title))
        o = end + 1
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('terrain', terrain_names())
    print('titles', chapter_titles())
    print('items', item_names())
    print('classes', class_names())
    print('characters', character_names())
    print('castle labels', place_labels())
    print('castles', {k: place(k) for k in PLACES})

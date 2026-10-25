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
Bosses and other foes have no name table in either version (their names appear only in the dialogue).

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

# The patch's text: A-Z from 0x10, a-z from 0x2A, 0xBF a space, and a few marks and accented letters.
CHARS = {**{0x10 + i: chr(65 + i) for i in range(26)}, **{0x2A + i: chr(97 + i) for i in range(26)}, 0xBF: ' ', 0x44: '.', 0x45: ',',
         0x46: '?', 0x47: '!', 0x48: "'", 0x49: '-', 0x89: 'á', 0x9B: 'ó', 0x9E: 'ö', 0xA3: 'ü'}
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


def spelling(*candidates):
    """The first candidate the patch's text uses (ignoring case), in the patch's own capitalisation, or None. The patch has no table
    for bosses and other foes, so their names are taken from its dialogue this way (Serenes' Dimaggio is its DiMaggio)."""
    text, p = _text(), patched()
    for c in candidates:
        if not c:
            continue
        i = text.find(c.lower())
        while i >= 0:
            # a whole word: not run into other letters
            before = text[i - 1] if i else '\0'
            after = text[i + len(c)] if i + len(c) < len(text) else '\0'
            if not before.isalpha() and not after.isalpha():
                return decode(p[0x500000 + i:0x500000 + i + len(c)])
            i = text.find(c.lower(), i + 1)
    return None


def place(kana):
    """The patch's name for a castle, by the ROM's kana name; checked to be one of its labels or in its text."""
    name = PLACES[kana]
    assert name in place_labels() or in_text(name), (kana, name)
    return name


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('items', item_names())
    print('classes', class_names())
    print('characters', character_names())
    print('castle labels', place_labels())
    print('castles', {k: place(k) for k in PLACES})

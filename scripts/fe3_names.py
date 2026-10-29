"""
English names for Mystery of the Emblem, from the translation patch the user supplied (FE3_patches_v1.2.zip next to the ROM:
RPGuy96 and VincentASM's translation, Quirino's update, Robert of Normandy's current project). Its Translation_Only_E.ips is applied in
memory to the clean 1.1 image (scripts/fe3_rom.py) and only its text is read, by the ROM's own ids; nothing patched is written.

The patch's text tables (addresses from its public build files, FE3_buildfiles_v1.2.zip, each checked here against what it decodes to):
  characters   $F0:8000  u16 pointers by name id (bank $F0), "menu" text: u16 codes, 0xFFFF ends
  classes      $F0:889C  the same, by class id: the menu's 7-letter names ("ArmrKnt"), spelled out below as the patch's class roll
                         and class descriptions spell them ("Armor Knight")
  items        $8E:8C4A  u16 pointers (bank $E7) to the storage messages ("Iron Sword was sent to the storage."), by item id: the
                         patch's full item names (its menu shows 7 letters, "Iron" with a sword icon)
  status       $F0:A352  "Book 1 Chapter 1" and the chapter's title, by chapter number
  objectives   $F0:AFA6  by chapter number ("Seize castle")
"""
import functools
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fe3_rom import R, lo  # noqa: E402

PATCHES = os.environ.get('FE3_PATCHES', os.path.join(os.path.expanduser('~'), 'Documents', 'FE Games', 'FE3_patches_v1.2.zip'))


def apply_ips(src, patch):
    assert patch[:5] == b'PATCH', 'not an IPS patch'
    out, i = bytearray(src), 5
    while patch[i:i + 3] != b'EOF':
        off, n = int.from_bytes(patch[i:i + 3], 'big'), int.from_bytes(patch[i + 3:i + 5], 'big')
        i += 5
        if n == 0:
            n, data = int.from_bytes(patch[i:i + 2], 'big'), bytes([patch[i + 2]]) * int.from_bytes(patch[i:i + 2], 'big')
            i += 3
        else:
            data = patch[i:i + n]
            i += n
        out.extend(b'\0' * max(0, off + n - len(out)))
        out[off:off + n] = data
    return bytes(out)


@functools.lru_cache(maxsize=None)
def patched():
    return apply_ips(R, zipfile.ZipFile(PATCHES).read('FE3_patches_v1.2/Translation_Only_E.ips'))


# The menu font's codes (the patch's config/in.yml, "menu").
MENU = {i: c for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst')}
MENU.update({0x50 + i: c for i, c in enumerate('uvwxyz')})
MENU.update({0x9F + i: c for i, c in enumerate('0123456789')})
MENU.update({0x56: "'", 0x57: ',', 0x58: '(', 0x59: ')', 0x5A: '.', 0x5B: ' ', 0x5D: ';', 0xB0: '/', 0xBA: '%', 0xBE: '_', 0xC0: '(',
             0xC1: ')', 0xC2: ' ', 0xC3: '-', 0xC4: '!', 0xF4: '+', 0xFC: '?'})
NEWLINE = 0xFFFD

# The dialogue font without digraphs ("nodigraph"): one byte a character; 0x00 starts a command.
TEXT = {2 + i: c for i, c in enumerate('BCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuv')}
TEXT.update({0x31: ' ', 0x32: 'w', 0x33: 'x', 0x34: 'y', 0x35: 'z', 0x36: '(', 0x37: ')', 0x38: ',', 0x39: '.', 0x3A: '!', 0x3B: '?',
             0x47: "'", 0x48: ';', 0x49: 'll', 0x4A: 'la', 0x4C: 'ia', 0x51: ':', 0x54: '-', 0x69: 'A'})
TEXT.update({0x3D + i: c for i, c in enumerate('0123456789')})


def _ptr(table, k):
    p = patched()
    o = lo(table) + 2 * k
    return p[o] | p[o + 1] << 8


def menu_text(table, k):
    """A menu string: lines joined by a space."""
    p = patched()
    o = lo((table & 0xFF0000) | _ptr(table, k))
    out = []
    while True:
        v = p[o] | p[o + 1] << 8
        o += 2
        if v == 0xFFFF:
            break
        out.append(' ' if v == NEWLINE else MENU.get(v, '?'))
    return ''.join(out).strip()


def storage_name(k):
    p = patched()
    o = lo(0xE70000 | _ptr(0x8E8C4A, k))
    out = []
    while p[o] != 0 and len(out) < 40:
        out.append(TEXT.get(p[o], '?'))
        o += 1
    s = ''.join(out)
    assert ' was sent' in s, (k, s)
    return s.split(' was sent')[0]


CHAR_COUNT = 0x8E
CLASS_COUNT = 0x2D

# The menu's class names spelled out as the patch's own text spells them (its class roll: "Cavalier", "Armor Knight", "Pegasus Knight",
# "Dragon Knight"; its class descriptions: "Mercenaries", "Horsemen"...). Where a name stands for two classes, the one for women
# says so: their weapon lists differ (the Lady Sword, Resire).
CLASS_FULL = {'Cavalr': 'Cavalier', 'ArmrKnt': 'Armor Knight', 'Pegasus': 'Pegasus Knight', 'DrgnKnt': 'Dragon Knight',
              'Horsman': 'Horseman', 'Manakte': 'Manakete', 'FireDrg': 'Fire Dragon', 'Mercnry': 'Mercenary', 'Commndo': 'Commando',
              'Barbran': 'Barbarian', 'Brserkr': 'Berserker', 'DarkKnt': 'Dark Knight', 'DrkMage': 'Dark Mage', 'IceDrg': 'Ice Dragon',
              'SeaDrg': 'Sea Dragon', 'FlyDrg': 'Flying Dragon', 'ErthDrg': 'Earth Dragon', 'ShadwDr': 'Shadow Dragon',
              'DivnDrg': 'Divine Dragon', 'MageDrg': 'Mage Dragon', 'Guardian': 'Guardian'}
# The second class of a pair (the women's): Knight 6 (a dismounted Pegasus Knight), Mage 0x17 (Linde's), Bishop 0x18 (Lena's).
WOMEN = {0x06, 0x17, 0x18}


@functools.lru_cache(maxsize=None)
def class_names():
    out = {}
    for c in range(CLASS_COUNT):
        n = menu_text(0xF0889C, c)
        n = CLASS_FULL.get(n, n)
        out[c] = f'{n} (F)' if c in WOMEN else n
    return out


@functools.lru_cache(maxsize=None)
def character_names():
    return {c: menu_text(0xF08000, c) for c in range(CHAR_COUNT)}


@functools.lru_cache(maxsize=None)
def item_names():
    """By item id. The staves' storage names add "Staff" ("Heal Staff"), which the menu doesn't: it's dropped. "SwordSlayer" is
    spelled as the patch's dialogue spells it."""
    out = {}
    for i in range(0x7F):
        n = storage_name(i)
        if n.endswith(' Staff'):
            n = n[:-6]
        out[i] = {'SwordSlayer': 'Swordslayer'}.get(n, n)
    return out


@functools.lru_cache(maxsize=None)
def chapter_titles():
    """{chapter number: (heading as the status screen writes it, title)}: "Book 1 Chapter 1", "Marth Embarks"."""
    out = {}
    for n in range(1, 45):
        p = patched()
        o = lo(0xF00000 | _ptr(0xF0A352, n))
        lines, cur = [], []
        while True:
            v = p[o] | p[o + 1] << 8
            o += 2
            if v in (0xFFFF, NEWLINE):
                lines.append(''.join(cur).strip())
                cur = []
                if v == 0xFFFF:
                    break
            else:
                cur.append(MENU.get(v, '?'))
        out[n] = (lines[0], ' '.join(lines[1:]))
    return out


@functools.lru_cache(maxsize=None)
def objectives():
    return {n: menu_text(0xF0AFA6, n) for n in range(1, 45)}


if __name__ == '__main__':
    print(class_names())
    print(item_names())
    print(character_names())
    print(chapter_titles())
    print(objectives())

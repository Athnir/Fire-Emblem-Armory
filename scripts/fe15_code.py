"""Helpers for reading Echoes: Shadows of Valentia's program (data-raw/fe15/romfs/code.bin, loaded at 0x100000): Awakening's
(scripts/fe13_code.py) pointed at Echoes' code. Used to check mechanics in the code."""
import os

import fe13_code as C

C.CODE = open(os.path.join(os.path.dirname(__file__), '..', 'data-raw', 'fe15', 'romfs', 'code.bin'), 'rb').read()
from fe13_code import *  # noqa: E402,F401,F403

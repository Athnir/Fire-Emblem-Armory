"""
Builds src/data/maps/gameTerrain.ts from the game's own terrain files: for each map, the tile grid in
the app's terrain letters plus each letter's exact name, Def, Avo, heal and movement costs.

Needs the game files dumped from your own copy into data-raw/fates/romfs/ (git-ignored; see
data-raw/fates/README.md). Run:  python scripts/build-fates-terrain.py
"""
import json
import re
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fates_map_convert import parse_tid  # noqa: E402
from fates_maps import MAPS, PACK, find_script, terrain, terrain_script, text_for  # noqa: E402
from fates_movecost import load as load_costs  # noqa: E402
from fates_terrain import read as read_terrain  # noqa: E402
from fates_tricks import tricks as read_tricks  # noqa: E402
from fates_cmb import Script  # noqa: E402
from terrain_codes import encode, encode_row  # noqa: E402
import map_pieces  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'data-raw', 'fates', 'romfs')
OUT = os.path.join(ROOT, 'src', 'data', 'maps', 'gameTerrain.ts')
GROUND = os.path.join(ROOT, 'data-raw', 'fates-ground.json')
# The renders scripts/fates_ground.py keeps (git-ignored), for the looks read off a map's art (its sky, its stalls).
ART_CACHE = os.path.join(ROOT, 'data-raw', 'fates', 'romfs', 'art-cache')


WATER = {'湖', '海', '泉', '氷海', '湖地専', '海の道', '湖配置'}
SKY = {'空', '竜巻', '宇宙'}
LAUNCHER = {'弓砲台': 'L', '魔道砲台': 'O', '暗器砲台': 'U'}
# What a tile turns into after a Dragon Vein (the part after '／' in its terrain name).
AFTER = {'平地': '.', '床': '1', '暗夜床': '1', '回復床': 'H', '回復床50': 'H', '橋': 'b', '空': 'x', '湖': 'a',
         '海': 'a', '河': 'w', '壁': '#', '隆起': '#', '砦': 'F', '済砦': 'F', '宝箱': 'c', '林': 'f', '建物': 'B',
         '太柱': '#', '氷丘': 'I', '溶岩床': 'o', '海の道': '.', '氷結泉': 'i', '魔方陣': '.', '竜巻': 'z', '嵐': 'z',
         '毒沼配置': 'P', '宇宙': 'x'}
VEIN, AREA, TOGGLE = 11, 12, 29
# A sigil that sends a unit standing on it to another tile (Revelation 18's): its trick's string names the tile, 'x, y' from the top.
WARP = 28
# Terrain that can be broken down by attacking it (its name has a '｜' part saying what it becomes).
BREAKABLE = {'壁', '低壁', '建物', '古木', '土塁', '防壁'}
# Revelation 9's whirlwinds: the battle-start handler (kind 8) turns all 50 edge tiles to sky, then calls a helper with computed tiles
# to raise the first two winds, x 8-12 on the top row and x 17-21 on the bottom (in the files' top-down rows 1 and 29). Read live
# on turn 1 (Normal and Lunatic alike): those ten are whirlwinds, the other forty sky.
OPENING_STORMS = {'C009': {(x, 1) for x in range(8, 13)} | {(x, 29) for x in range(17, 22)}}
# Terrain the game's text has no English line for: Birthright 17's lake (the one Conquest 8 has frozen) and a fort in Witches' Trial.
# Revelation 16's flame walls: each one's flag in the chapter script ('炎壁０１' to '炎壁２０').
WALL_FLAG = '炎壁'
UNNAMED = {'湖地専': 'Lake', '済砦': 'Fort', '剣の間2': 'Chamber'}
# Its buildings (建物, 低建物) standing alone as a block two to six tiles wide and up to four tall are each a house drawn whole, its roof
# along its top and its front with a door (the user's calls, the review of every map: Fates' villages and houses, not blocks of wall;
# map_pieces.place, as the Tellius games' towns). A village below one is its door mat.
BUILDINGS = ('建物', '低建物')
HOUSE_WIDE, HOUSE_TALL = (2, 6), 4


# The maps whose walls standing alone two tiles by two its art draws as statues (the user's call: Birthright 21's; elsewhere they're
# crystals, rocks and the like, kept as walls).
STATUE_MAPS = {'fe14b-21'}
# Birthright 24's great dragon statue in its hall (the user's call): its block of walls, five by five, drawn as the statue over them.
DRAGON_MAPS = {'fe14b-24'}
# Birthright 25's walls standing alone in its halls are pillars (the user, its corridor's): drawn as pillars over them.
PILLAR_MAPS = {'fe14b-25'}
# A map's colours its render gets wrong (the user's calls): Birthright 19's void between its buildings drawn as the void, black.
FILLS = {'fe14b-19': {'wa': '#0b0b0e'},
         # Paralogue 4's building walls, near-black in its render, a dark brown so they read as a building's bricks, not the void (the user).
         'fe14-x4': {'wa': '#3a2e26'},
         # Conquest 10's low stone walls along its canals, the game's light grey stone (the user: walls, not fences), and Revelation 14's.
         'fe14c-10': {'wg': '#8f8a7e'}, 'fe14r-14': {'wg': '#8f8a7e'},
         # Conquest 12's walls and floor kept apart (the user: the walls melded into the floor): the floor a step lighter, the walls darker.
         'fe14c-12': {'t1': '#5a5348', 'wa': '#2f2e2b'},
         # Revelation 25's halls a stone floor (the user: stone, not dirt; the candlelit render reads brown), its walls darker.
         'fe14r-25': {'t1': '#6f685c', 'wa': '#2e2c28'},
         # Birthright 9's floor a step lighter and its walls darker, so they part (the user: they blended at (17, 5) and (19, 5)), and
         # Conquest 18's, the same map.
         'fe14b-9': {'t1': '#6a4a33', 'wa': '#3d2c1f'}, 'fe14c-18': {'t1': '#6a4a33', 'wa': '#3d2c1f'},
         # Ghostly Gold's stone partitions (STONE_FENCES), the grey stone its photos show (the user: (17, 10) wrong colour, it was tan).
         'fe14-dlc-6a': {'wg': '#57535c'},
         # Museum Melee's Exit (DRAWN_AS), the purple pad its photos show.
         'fe14-dlc-6b': {'ge': '#733f90'},
         # Revelation 13's docks (DOCKS), weathered timber.
         'fe14r-13': {'gi': '#6b5238'}}
# Ships whose floor is their deck (the user: wood, not flagstones; Revelation 14's two ships, Paralogue 3's, Birthright 11's, Revelation
# 12's in the ice, Conquest 10's two docked boats), and the same maps on the other routes (Conquest 16's ship is Birthright 11's,
# Revelation 14's port Conquest 10's): the floor drawn as deck (`t3`), the floor's numbers kept; every wall joined to the walls beside its
# deck the ship's wood (masts, cabins, hulls: no stone on a ship, the user) and every partition joined to those beside it its wooden rails.
SHIP_FLOORS = {'fe14r-14', 'fe14-x3', 'fe14b-11', 'fe14c-16', 'fe14r-12', 'fe14c-10'}
# Partitions off the ships that are a town's low stone walls (Conquest 10's along its canals: the user, walls not fences; Revelation 14's,
# the same port).
STONE_PARTITIONS = {'fe14c-10', 'fe14r-14'}
# Boats moored in rows (Birthright 12's and Conquest 14's: the user, every walkable tile a wooden boat): the floor drawn as the boats'
# decks (`t3`) in their wood, the floor's numbers kept, and each partition at a boat's end its bow over the water, pointing away from
# its deck (`boatEnds`); where a partition has deck on both sides, its boat is the shorter run (the other is the next boat's or the
# great round deck's).
BOATS = {'fe14b-12': '#76553a', 'fe14c-14': '#76553a'}
# Maps whose buildings standing alone are ice (Birthright 17's and Conquest 8's village in the snow: the user, ice blocks, not stone):
# each block two tiles by two its ice crystals over the snow, the block three by three in its lake a frozen fountain; the building's
# numbers kept.
ICE_MAPS = {'fe14b-17', 'fe14c-8'}
# Birthright 8's houses are yurts (the user): each block of buildings a round yurt seen from above (`roundYurt`), the building's numbers
# kept.
YURT_MAPS = {'fe14b-8'}
# Birthright 9's blocks of buildings three tiles by three standing in its gravel are small gardens with a tree and stones (the user, all
# four), Conquest 18's the same map.
GARDEN_MAPS = {'fe14b-9', 'fe14c-18'}
# The void beside a map's floors drawn as its buildings' timber walls where it meets them (Birthright 19's: the user, a wood wall next to
# the play area; Conquest 11's and Revelation 15's the same map): each wall touching a walkable tile, corners too.
TIMBER_WALLS = {'fe14b-19', 'fe14c-11', 'fe14r-15'}
# Market stalls: every building of Birthright 22's square (the user, market stalls for all of these tiles), each block shared out into
# stalls two tiles wide and two or three long, their canopies red, blue and yellow in turn (`stall-*`).
STALL_MAPS = {'fe14b-22'}
# Cobbled roads its art draws on its plain (x0, y0, x1, y1; the colour its render gives them, lifted a step so they read against the
# grass): Birthright 14's stone road up to its castle, Birthright 22's cross of cobbled streets (the user), the plain's numbers and name
# kept (`gb`).
COBBLES = {'fe14b-14': ([(12, 1, 14, 17)], '#6a665a'),
           # (and its top row's walkway along the wall: the user's (8, 23) and (18, 23), 2026-11-24)
           'fe14b-22': ([(12, 1, 14, 23), (1, 11, 25, 12), (1, 23, 25, 23)], '#5f604c'),
           # Before Awakening is Awakening's Chapter 2 tile for tile (the user: see the Awakening notes): its road up the middle as the
           # user marked Awakening's (build-fe13-maps.py's ROAD_ONLY), the rest of its plain grass (NO_DIRT).
           'fe14-dlc-40': ([(8, 3, 9, 7), (9, 8, 10, 17), (9, 18, 9, 20), (8, 20, 8, 20), (7, 1, 7, 3)], '#c8b680')}
# Maps whose plain is all grass, no dirt sorted from its art (Before Awakening: Awakening's Chapter 2, its road the cobbles above).
NO_DIRT = {'fe14-dlc-40'}
# Muck drawn as a bog, its mud and puddles with no icon (Boo Camp's: the user, the bog texture).
BOG_MUCK = {'fe14-dlc-67'}
# Conquest 24's cherry trees and stones as big trees and boulders, two tiles by two at most (the user: larger trees and boulders).
BIG_TREES = {'fe14c-24'}
# Chapter 5's rubble varied (the user: other rubble icons): in blocks large stone rubble, else its pieces varied tile to tile (`rubble`).
RUBBLE_MAPS = {'fe14-5'}
# Conquest 21's partitions are its terraces' cliff edges (the user: a cliff, not a fence).
CLIFF_PARTITIONS = {'fe14c-21'}
# Partitions that are low stone walls (Ghostly Gold's two at (16, 10) and (17, 10): the user, stone), in their render's colour (FILLS).
STONE_FENCES = {'fe14-dlc-6a'}
# The user's notes of 2026-11-26. Tiles drawn as another code, their numbers kept (`looksAs`): Boo Camp's partitions (低壁) the walls
# they are in its photos (the user: all of this type of tile is a wall on this map), Museum Melee's Exit (出口) a purple pad on the
# floor (the user: not a wall; its photos' purple, FILLS), by the game's name for the tile.
DRAWN_AS = {'fe14-dlc-67': {'低壁': 'wa'}, 'fe14-dlc-6b': {'出口': 'ge'}}
# Tiles named apart from the code they share, so the tile panel and the legend say what the game says (Museum Melee's Exit, among its
# walls).
OWN_NAMES = {'fe14-dlc-6b': ('出口',)}
# What's drawn over a tile by the game's name for it (`decor`): Conquest 26's torches (篝火) candlesticks (the user: candlesticks, (9, 7)
# and those like it in its rooms).
NAMED_DECOR = {'fe14c-26': {'篝火': 'candle'}}
# What's drawn over a tile, by tile: Conquest 23's three partitions braziers (the user: braziers, Radiant Dawn's Part 2 Ch.2 lit torch,
# not candlesticks).
TILE_DECOR = {'fe14c-23': {(14, 21): 'brazier', (22, 19): 'brazier', (29, 21): 'brazier'}}
# What a map's partitions are, by box (x0, y0, x1, y1 in map tiles), the last kind the rest (`decor`; the user's final pass, 2026-11-26):
# Paralogue 16's all candlesticks ('candlesticks and lighting'), Paralogue 22's candles from (11, 23) to (17, 12) and the rest tables
# holding vases, three tiles long ('1x3 tables holding vases'). Their challenges are the same maps.
PARTITION_DECOR = {'fe14-x16': ([], 'candle'), 'fe14-x22': ([((11, 12, 17, 23), 'candle')], 'vaseTable')}
# Partitions, and its boxes (CRATE_BUILDINGS) joined to another, wooden fences, bold as Radiant Dawn's; its single boxes crates and its
# breakable walls stone bricks in its walls' grey, as its photos show them, cracked grey stone (Museum Melee's: the user, 'wooden fences
# like in fe 10 3-2', 'all the breakable tiles are all stone bricks').
FENCE_MAPS = {'fe14-dlc-6b'}
# The ground an icon stands on, by tile (`standOn`): Ghostly Gold's rubble on its grass (the user: the backdrop of these on grass),
# Revelation 13's obstacles on the stone or the dock's wood under each in its photos (the user: some on the wrong ground).
STAND_ON = {'fe14-dlc-6a': {(19, 8): 'ta', (22, 11): 'ta', (22, 12): 'ta'},
            'fe14r-13': {(2, 3): 't1', (15, 3): 't1', (18, 4): 't1', (9, 5): 't1', (4, 6): 't1', (4, 10): 't1', (11, 10): 'gi',
                         (19, 11): 't1', (19, 15): 't1', (4, 17): 't1'}}
# Its sky (空) the void, a drop into the dark (the user, Museum Melee: sky void tiles, not cliffs, as Engage's).
SKY_VOID = {'fe14-dlc-6b'}
# Wooden docks and piers its art lays where the game says floor (Revelation 13's: the user, wood instead of stone, (3, 4), (11, 11) and
# the tiles like them; each found by its planks' stripes in the render, checked by eye): boards (`gi`), the floor's numbers kept.
DOCKS = {'fe14r-13': [(17, 25), (17, 24), (17, 23), (5, 22), (4, 18), (11, 13), (11, 12), (12, 12), (5, 11), (11, 11), (5, 10), (6, 10), (10, 10), (16, 8), (17, 8), (17, 7), (3, 6), (17, 6), (3, 5), (16, 5), (17, 5), (1, 4), (2, 4), (3, 4), (6, 2), (7, 2), (8, 2), (6, 1), (8, 1), (13, 1)]}
# Bridges its art lays where the game says floor (Revelation 13's five pale plank crossings: the user, bridges, (18, 14), (14, 9),
# (6, 21), (16, 22) and (2, 15)): each drawn as a wooden bridge read off its box (x0, y0, x1, y1), its rails along the water, the floor's
# numbers kept (`bridgeFloors`, `wholeBridges`).
FLOOR_BRIDGES = {'fe14r-13': [(2, 15, 2, 16), (5, 21, 6, 21), (15, 22, 16, 22), (14, 9, 15, 9), (18, 13, 18, 14)]}
# Conquest 15's and Revelation 19's obstacles round its island: the sky below where its render shows sky through the rifts (the user: not
# bricks), the rest its cliffs' rock; the sky's colour off the render.
SKY_RIFTS = {'fe14c-15': '#d8c6a7', 'fe14r-19': '#d8c6a7'}
# Paralogue 20's town (the user's notes: its villages, houses and stalls): its houses (x0, y0, x1, y1) over its villages, each village
# before one its door mat, as its render shows them; its market stalls by their colour on the render; its roofs grey; its streets
# cobbles (as Paralogue 21's).
TOWN_HOUSES = {'fe14-x20': [(2, 20, 4, 21), (5, 20, 7, 21), (8, 20, 10, 21), (15, 18, 17, 19), (18, 18, 20, 19), (22, 18, 25, 19),
                            (26, 16, 28, 18), (15, 11, 17, 12), (4, 9, 6, 10)]}
TOWN_STALLS = {'fe14-x20': [((11, 20, 12, 21), 'orange'), ((4, 15, 5, 16), 'orange'), ((2, 12, 3, 13), 'orange'), ((4, 12, 5, 13), 'purple'),
                            ((2, 9, 3, 10), 'orange'), ((6, 5, 7, 6), 'purple'), ((28, 8, 29, 9), 'purple'), ((18, 11, 19, 12), 'orange')]}
TOWN_CRATES = {'fe14-x20': [(20, 11)]}
GREY_ROOFS = {'fe14-x20'}
PAVED_FLOORS = {'fe14-x20', 'fe14-x21'}
# Paralogue 21's houses all roofs seen from above, in the colours its render paints them (the user), (10, 17), (16, 9), (8, 8) and
# (23, 8) houses too, and the two more its render shows at (6, 6) and (13, 6): x0, y0, x1, y1, colour.
ROOFS = {'fe14-x21': [(6, 23, 8, 24, 'yellow'), (9, 22, 11, 23, 'red'), (13, 23, 15, 24, 'red'), (16, 23, 18, 24, 'blue'),
                      (22, 22, 24, 23, 'red'), (14, 20, 16, 21, 'red'), (19, 20, 21, 21, 'yellow'), (10, 19, 12, 20, 'yellow'),
                      (6, 17, 8, 18, 'red'), (18, 17, 20, 18, 'blue'), (22, 17, 24, 18, 'red'), (9, 16, 11, 17, 'blue'),
                      (20, 14, 22, 15, 'yellow'), (8, 13, 10, 14, 'blue'), (21, 12, 23, 13, 'red'), (16, 11, 18, 12, 'yellow'),
                      (7, 10, 9, 11, 'red'), (11, 10, 13, 11, 'yellow'), (20, 10, 22, 11, 'yellow'), (15, 9, 17, 10, 'blue'),
                      (11, 8, 13, 9, 'red'), (7, 8, 9, 9, 'yellow'), (22, 8, 24, 9, 'blue'), (17, 7, 19, 8, 'red'),
                      (6, 6, 8, 7, 'yellow'), (13, 6, 15, 7, 'blue')]}
# The DLC's Museum Melee: its buildings are carts, crates and benches on the plaza (the user: villages where they don't belong), drawn as
# crates; the one in its spring's middle a pedestal.
CRATE_BUILDINGS = {'fe14-dlc-6b': {(12, 13): 'pillar'}}
# Ballistician Blitz's house, three tiles by two, drawn as the small house with a low wall round it that Shadow Dragon and the Blade of
# Light and Mystery of the Emblem draw for a village (the user: the house from the map's original game).
WALLED_HOUSES = {'fe14-dlc-76': [(19, 16, 21, 17)]}
# Bridges its field builds of stone (Conquest 7's, Revelation 20's slabs: the user's bridge notes), drawn as stone (`t8`), the bridge's
# numbers kept, the bridges its veins lay too.
STONE_BRIDGES = {'fe14c-7', 'fe14r-20'}
# Bridges that turn or jog, every tile of one running one way (the user: Chapter 3's, a turning bridge, not a broken one two tiles wide;
# Paralogue 15's walkway, its (27, 9) turned): a tile of the bridge, and the way all of its tiles run; rails on each tile's water sides.
BRIDGE_SPANS = {'fe14-3': [((12, 16), 'ew')], 'fe14-x15': [((27, 9), 'ns')]}
# Maps whose few plain tiles are their halls' floor (Revelation 25's raised platforms: the user, floor not dirt): drawn as floor (`t1`)
# where the two work alike.
PLAIN_AS_FLOOR = {'fe14r-25'}
# Building blocks that are forts, drawn as castles (`ca`-`ci`) not houses (the user, Chapter 3's at (16, 6)-(18, 8)), the building's
# numbers kept: x0, y0, x1, y1 in map tiles.
FORTS = {'fe14-3': [(16, 6, 18, 8)]}
# The maps whose small groups of Stairs (four tiles or fewer) are stairwells going down, dark openings where foes come up (the user's
# notes, 2026-11-22: 'downward stairs icons for this game'), and the copies of their maps on the other routes; each drawn as stairs
# going down (`bz`, the stairs' numbers), Paralogue 3's ships' hatches too (the user, 2026-11-24). Real staircases stay stairs: Conquest
# 21's terraces (groups of 23 to 66), Revelation Paralogue 4's and Revelation 21's steps.
# Maps whose building blocks aren't houses (the user's notes, 2026-11-22): the DLC's temple plaza (stone works, no village), Revelation
# 10's corners of buildings its snow buries (not houses standing alone).
NO_HOUSES = {'fe14-dlc-6b', 'fe14r-10'}
# Maps whose buildings all stand in ruins.
RUINED = {'fe14c-15'}
# Steps its field builds where the game says floor or plain (the user, 2026-11-24: stairs shown even where they change nothing, every map
# checked): each tile of the field's surface that rises evenly across it, a quarter or half a tile, its flights checked by eye on the
# renders (x0, y0, x1, y1 in map tiles; a challenge battle has its chapter's); the stairs' icon over the ground, which keeps its numbers.
STEPS = {
    'fe14-2': [(5, 2, 11, 2), (4, 3, 4, 9), (12, 3, 12, 9), (5, 10, 11, 10), (1, 14, 15, 14)],
    'fe14-dlc-86': [(10, 3, 10, 4), (19, 3, 19, 4)],
    'fe14-x22': [(9, 3, 9, 4), (19, 3, 19, 4), (2, 24, 3, 24), (22, 24, 23, 24)],
    'fe14b-11': [(11, 6, 11, 7), (5, 10, 5, 11), (16, 11, 17, 13), (5, 13, 5, 14), (11, 17, 11, 18)],
    'fe14b-24': [(12, 5, 13, 5), (13, 6, 13, 6), (24, 15, 24, 16), (2, 16, 3, 16), (23, 16, 23, 16), (2, 17, 2, 17), (13, 26, 13, 27), (14, 27, 14, 27)],
    # (and the two flights either side of its carpet at the bottom: the user, 2026-11-26)
    'fe14b-27': [(6, 6, 6, 7), (12, 6, 14, 6), (20, 6, 20, 7), (6, 14, 6, 15), (20, 14, 20, 15), (7, 19, 9, 19), (17, 19, 19, 19), (12, 21, 14, 22),
                 (11, 1, 11, 5), (15, 1, 15, 5)],
    'fe14b-7': [(12, 2, 14, 3)],
    'fe14b-9': [(12, 1, 14, 2)],
    'fe14c-16': [(11, 6, 11, 7), (5, 10, 5, 11), (16, 11, 17, 13), (5, 13, 5, 14), (11, 17, 11, 18)],
    'fe14c-18': [(12, 1, 14, 2)],
    'fe14c-20': [(15, 4, 15, 4), (6, 10, 6, 10), (21, 10, 21, 10), (13, 11, 13, 11), (10, 13, 10, 13), (15, 13, 16, 13), (20, 14, 20, 14), (4, 19, 4, 19), (16, 25, 16, 25)],
    'fe14c-25': [(10, 3, 10, 4), (19, 3, 19, 4)],
    'fe14c-26': [(6, 14, 7, 16), (20, 14, 21, 16)],
    'fe14c-27': [(13, 3, 17, 3), (12, 9, 18, 10), (13, 15, 17, 15)],
    'fe14c-9': [(6, 7, 6, 9)],
    'fe14c-endgame': [(12, 3, 18, 3), (12, 9, 18, 10), (12, 15, 17, 15)],
    'fe14r-13': [(10, 15, 12, 15)],
    'fe14r-8': [(12, 2, 14, 3)],
    'fe14r-9': [(15, 4, 15, 4), (6, 10, 6, 10), (21, 10, 21, 10), (13, 11, 13, 11), (10, 13, 10, 13), (15, 13, 16, 13), (20, 14, 20, 14), (4, 19, 4, 19), (16, 25, 16, 25)],
    # (the scan's slope cut left these out, the steps up to its three statues: the user, 'stairs')
    'fe14r-25': [(7, 24, 7, 25), (8, 12, 8, 14), (7, 1, 7, 2)],
}
DOWN_STAIRS = {'fe14b-7', 'fe14b-9', 'fe14b-11', 'fe14b-14', 'fe14b-16', 'fe14b-19', 'fe14b-25', 'fe14b-26', 'fe14c-9', 'fe14c-11',
               'fe14c-12', 'fe14c-16', 'fe14c-18', 'fe14c-20', 'fe14c-23', 'fe14c-25', 'fe14c-26', 'fe14c-27', 'fe14r-8', 'fe14r-9',
               'fe14r-12', 'fe14r-15', 'fe14-x3', 'fe14-x9', 'fe14-x11', 'fe14-x16', 'fe14-x22', 'fe14-dlc-6a', 'fe14-dlc-74', 'fe14-dlc-7f'}


def stairwells(rows):
    """The encoded rows with each group of four Stairs tiles or fewer made stairs going down (`bz`)."""
    grid = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in rows]
    h, w = len(grid), len(grid[0]) if grid else 0
    seen = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] != 'tc' or (x, y) in seen:
                continue
            group, todo = [], [(x, y)]
            while todo:
                c = todo.pop()
                if c in seen or not (0 <= c[0] < w and 0 <= c[1] < h) or grid[c[1]][c[0]] != 'tc':
                    continue
                seen.add(c)
                group.append(c)
                todo += [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
            if len(group) <= 4:
                for gx, gy in group:
                    grid[gy][gx] = 'bz'
    return [''.join(r) for r in grid]


def dragons(walls):
    """The blocks of walls five by five, filling their box, drawn as the dragon statue: {"x,y": 'dragon'}."""
    out = {}
    for x, y in walls:
        block = {(i, j) for i in range(x, x + 5) for j in range(y - 4, y + 1)}
        if block <= walls and not ({(x - 1, y), (x, y + 1)} & walls):
            out.update({f'{i},{j}': 'dragon' for i, j in block})
    return out


def pillars(walls, letters):
    """The walls standing alone in a hall, all four sides open: {"x,y": 'pillar'}."""
    return {f'{x},{y}': 'pillar' for x, y in walls
            if all(letters.get(t, '#') not in ('#',) and t not in walls for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))}


def statues(walls, letters, changing):
    """The walls standing alone in the open two tiles by two, drawn as statues: {"x,y": 'statue'} for the decor drawn over them;
    none of them changing in the battle."""
    out = {}
    for x, y in walls:
        block = {(x, y), (x + 1, y), (x, y - 1), (x + 1, y - 1)}
        if not block <= walls or block & changing:
            continue
        ring = {(i, j) for i in range(x - 1, x + 3) for j in range(y - 2, y + 2)} - block
        if all(t in letters and letters[t] != '#' for t in ring):
            out.update({f'{i},{j}': 'statue' for i, j in block})
    return out


def house_blocks(tiles, changing):
    """The tiles of the buildings drawn as houses: each block of building tiles that fills its box, sized as a house, none of it
    changing in the battle (`changing`: a building broken down or a vein's change keeps the building's own look)."""
    out, seen = set(), set()
    for start in sorted(tiles):
        if start in seen:
            continue
        comp, todo = set(), [start]
        while todo:
            p = todo.pop()
            if p in comp or p not in tiles:
                continue
            comp.add(p)
            todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
        seen |= comp
        xs, ys = [p[0] for p in comp], [p[1] for p in comp]
        w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        if len(comp) == w * h and HOUSE_WIDE[0] <= w <= HOUSE_WIDE[1] and h <= HOUSE_TALL and not comp & changing:
            out |= comp
    return out


def rects(boxes):
    '''The tiles of boxes (x0, y0, x1, y1).'''
    return {(x, y) for x0, y0, x1, y1 in boxes for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}


def parts(tiles):
    '''The blocks of tiles joined side by side: [(set of tiles, (x0, y0, x1, y1))].'''
    out, seen = [], set()
    for start in sorted(tiles):
        if start in seen:
            continue
        comp, todo = set(), [start]
        while todo:
            p = todo.pop()
            if p in comp or p not in tiles:
                continue
            comp.add(p)
            todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
        seen |= comp
        xs, ys = [p[0] for p in comp], [p[1] for p in comp]
        out.append((comp, (min(xs), min(ys), max(xs), max(ys))))
    return out


def stall_chunks(box):
    '''A block of stalls (x0, y0, x1, y1) shared out into stalls two tiles wide and two or three long, from its top left, staggered
    column to column: [set of tiles].'''
    x0, y0, x1, y1 = box
    widths, x = [], x0
    while x <= x1:
        w = 3 if x1 - x == 2 else 2 if x1 - x >= 1 else 1
        widths.append((x, x + w - 1))
        x += w
    out = []
    for c, (a, b) in enumerate(widths):
        sizes, left, k = [], y1 - y0 + 1, c % 2
        while left > 0:
            n = min((3, 2)[k % 2], left)
            if left - n == 1:
                n += 1
            sizes.append(n)
            left -= n
            k += 1
        top = y1
        for n in sizes:
            out.append({(x, y) for x in range(a, b + 1) for y in range(top - n + 1, top + 1)})
            top -= n
    return out


def art(map_id, w, h):
    '''The map's render from the cache, per tile: (h, w, pixels, 3) top row first, or None.'''
    path = os.path.join(ART_CACHE, f'{map_id}-24.npy')
    if not os.path.exists(path):
        return None
    a = np.load(path).astype(np.float32)
    return a[:h * 24, :w * 24].reshape(h, 24, w, 24, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, 576, 3)


def letter(name, qual, cost):
    """Pick the app letter for one terrain kind from its base name and movement-cost class."""
    if name in ('扉', '襖'):
        return 'd'
    if cost in (0, 1, 14, 15):
        # Rubble nothing crosses (Birthright's Endgame, Revelation 27) and Revelation 10's ice to dig through get their own letters.
        # An obstacle (Revelation 13's and Paralogue 21's: the user, its own icon, not a wall).
        return {'水壁': 'D', '瘴気': 'D', '闇': 'X', '瓦礫': 'R', '氷': 'J', '障害物': 'A'}.get(name, '#')
    if name in LAUNCHER:
        return LAUNCHER[name]
    if cost in (2, 12, 13):
        if name == '宝箱':
            return 'c'
        if name in WATER:
            return 'a'
        if name in SKY:
            return 'x'
        if name in ('低壁',):
            return 'l'
        if name in ('崖', '高山'):
            return 'C'
        if name in ('深い森',):
            return 'k'
        if name in ('建物', '低建物'):
            return 'B'
        return 'r'
    if cost == 3:
        return 'z'
    if cost == 4:
        if name.startswith('毒沼'):
            return 'P'
        # A floor (床, 暗夜床) is its own code, apart from the plain (the user's call: each kind as the game draws it, its own colour).
        # Revelation 26's Ice Patch (氷結泉: its pools frozen) drawn as ice, the frozen lake's look (the user: the pools gone in its
        # challenge, where every pool is frozen); it plays as the plain it is.
        return {'段差': 'E', '亀裂': 'Z', '階段': 'S', '門口': 'e', '村': 'v', '廃村': 'V', '閉じ村': 'V', '剣の間': 'j', '回復床': 'H',
                '橋': 'b', '扉': 'd', '襖': 'd', '守護床': 'K', '竹槍': 'q', '剣の間2': 'N', '床': '1', '暗夜床': '1', '氷結泉': 'i',
                # A moat drained to its bed (Paralogue 2's, dry from the start: the user, in the game) drawn as bare earth, a dry ditch.
                '空堀': 'W'}.get(name, '.')
    if cost == 5:
        # A forest's costs: hot springs, Birthright 21's lava floor (it hurts) and Birthright 12's ice hills (no bonus).
        return {'熱水泉': 'M', '溶岩床': 'o', '氷丘': 'I'}.get(name, 'f')
    if cost == 6:
        return {'撒菱': 'T', '水たまり': 'u'}.get(name, 'p')
    if cost == 7:
        return 's'
    if cost == 8:
        return 'n' if '山' in name or name == '石垣' else 'W'
    if cost == 9:
        return 'w'
    if cost == 10:
        return {'砦': 'F', '済砦': 'F', '穴': 'F', '座布団': 'Q', '廃墟門': 'G', '城門': 'g', '玉座': 't',
                '召喚床': 'Y'}.get(name, 'F')
    return '?'


def signed(b):
    return b - 256 if b & 0x80 else b


def main():
    costs = load_costs(os.path.join(RAW, 'GameData.bin.lz'))
    out = {}
    for map_id, (code, _, _) in MAPS.items():
        pack = PACK.get(map_id)
        text = text_for(pack)
        t = read_terrain(terrain(code, pack))
        W, H = t['w'] - 2, t['h'] - 2
        kinds = {}
        def after_letter(state):
            """The letter of what a tile becomes ('／'): the map's own terrain of that name when it has one (Revelation 16's flames
            die down to Canyon, Conquest 25's Chamber turns into its Avo -20 form), else the usual table."""
            if not state:
                return None
            other = next((u for u in t['types'] if parse_tid(u['tid'])[:3] == (state, None, None)), None)
            if other:
                oname, _, _, _, oqual = parse_tid(other['tid'])
                L2 = letter(oname, oqual, other['raw'][4] & 0xFF)
                if L2 != '?':
                    return L2
            return AFTER.get(state)

        rows = []
        tile_names = {}
        buildings = set()
        walls = set()
        firsts = {}
        afters = {}
        breaks = {}
        knock_on = {}
        dark = []
        pots = []
        spent = {}
        for r in range(1, t['h'] - 1):
            row = ''
            for c in range(1, t['w'] - 1):
                ty = t['types'][t['rows'][r][c]]
                name, after, broken, vein, qual = parse_tid(ty['tid'])
                if name == '闇' and after:
                    # Revelation's darkness: the map keeps the terrain underneath, shaded until it lifts.
                    under = next((u for u in t['types'] if parse_tid(u['tid'])[0] == after), None)
                    if under:
                        dark.append((c, H + 1 - r))
                        ty = under
                        name, after, broken, vein, qual = parse_tid(ty['tid'])
                barrier = name == '防壁'
                if barrier:
                    name, after = '床', '壁'  # Endgame barriers: floor until a vein raises them
                r4 = ty['raw'][4]
                cost = r4 & 0xFF
                L = '.' if barrier else letter(name, qual, cost)
                frozen = name == '湖地専' and code == 'B008'
                if frozen:
                    # Conquest 8's frozen lake: ground units walk on it until a vein melts it into lake. Birthright
                    # 17 shares the map, but there it starts as lake and the vein freezes it.
                    L, cost, after = 'i', 4, '湖'
                if L == '?':
                    raise SystemExit(f'{code}: no letter for {ty["tid"]} (cost class {cost})')
                # The game calls both rivers (河) and puddles (水たまり) 'Water'; the puddles get their own name.
                en = 'Frozen lake' if frozen else 'Shallow water' if name == '水たまり' else text.get('MTID_' + name) or text.get('MTID_' + name.replace('配置', '')) or \
                    ('Acid Bog' if name.startswith('毒沼') else 'Floor' if name == '障壁用床' else UNNAMED.get(name, name))
                if name in ('良薬', '劇薬'):
                    en, cost, L = 'Floor', 4, '.'  # pots are objects; the floor under them is what's left
                    pots.append((c, H + 1 - r))
                info = {'name': en, 'def': signed(r4 >> 8 & 0xFF), 'avo': signed(r4 >> 16 & 0xFF),
                        'heal': signed(r4 >> 24 & 0xFF), 'move': costs(cost)}
                if name in ('良薬', '劇薬'):
                    info.update({'def': 0, 'avo': 0, 'heal': 0})
                if barrier:
                    info.update({'def': 0, 'avo': 0, 'heal': 0, 'move': costs(4)})
                A = after_letter((after or '').replace('＃竜脈', ''))
                if A and A != L and name not in ('扉', '襖'):
                    afters[(c, H + 1 - r)] = A
                # '｜' names what a tile becomes once broken: walls, partitions, buildings, an old tree, an earthwork.
                B = AFTER.get(broken or '') or {'段差': 'E'}.get(broken or '')
                if name in BREAKABLE and B and B != L:
                    breaks[(c, H + 1 - r)] = B
                elif B and B != L and name not in ('扉', '襖', '良薬', '劇薬') and not barrier:
                    knock_on[(c, H + 1 - r)] = B  # changes when something nearby breaks (the river under Conquest 19's tree)
                prev = kinds.get(L)
                blocked = all(v is None for v in info['move'].values())
                # Its second state ('／', else what it breaks into, '｜'; a village closes): a challenge battle has the chapter's
                # map with every trick in it spent (read live: Revelation 20's every bridge down at once, its veins and villages
                # used; Paralogue 14's bog all gone and its village closed).
                second = after or broken or {'村': '閉じ村'}.get(name)
                if second and name not in ('良薬', '劇薬') and not barrier:
                    other = next((u for u in t['types'] if parse_tid(u['tid'])[:3] == (second, None, None)), None) or                         next((u for u in t['types'] if parse_tid(u['tid'])[0] == second), None)
                    if other:
                        oname, _, _, _, oqual = parse_tid(other['tid'])
                        o4 = other['raw'][4]
                        S = letter(oname, oqual, o4 & 0xFF)
                        sinfo = {'name': text.get('MTID_' + oname) or UNNAMED.get(oname, oname), 'def': signed(o4 >> 8 & 0xFF),
                                 'avo': signed(o4 >> 16 & 0xFF), 'heal': signed(o4 >> 24 & 0xFF), 'move': costs(o4 & 0xFF)}
                    else:
                        S, sinfo = AFTER.get(second) or {'段差': 'E', '閉じ村': 'V'}.get(second), None
                    if S and S not in ('?', L):
                        spent[(c, H + 1 - r)] = (S, sinfo)
                # Nothing can enter either: they're one obstacle, whatever bonuses the game lists on them.
                if prev and not blocked and (prev['def'], prev['avo'], prev['heal'], prev['move']) != (info['def'], info['avo'], info['heal'], info['move']):
                    raise SystemExit(f'{code}: letter {L} covers two different terrains: {prev} / {info}')
                if not prev:
                    kinds[L] = prev = dict(info, names={}, where={})
                prev['names'][en] = prev['names'].get(en, 0) + 1
                prev['where'].setdefault(en, []).append((c, H + 1 - r))
                firsts[(c, H + 1 - r)] = L
                tile_names[(c, H + 1 - r)] = (name, en)
                if name in BUILDINGS and L in ('#', 'B'):
                    buildings.add((c, H + 1 - r))
                if name == '壁' and L == '#':
                    walls.add((c, H + 1 - r))
                row += L
            rows.append(row)
        # A spent tile's terrain needs its own entry when nothing on the map is that already.
        for S, info in spent.values():
            if info:
                kinds.setdefault(S, dict(info, names={info['name']: 0}, where={}))
        spent = {tile: S for tile, (S, _) in spent.items()}
        for info in kinds.values():
            names = sorted(info.pop('names').items(), key=lambda kv: -kv[1])
            where = info.pop('where')
            # Tiles under one code with names of their own (Revelation 18's Sigils among its plain, V: Endless Dawn's Dragon Vein
            # tile among its forts): each keeps its name in the tile panel; the most common name is the default.
            if len(names) > 1 and info['move']['Fliers'] is not None:
                info['tileNames'] = {n: sorted(where.get(n, []), key=lambda p: (-p[1], p[0])) for n, _ in names[1:] if where.get(n)}
            # Walls keep the commonest name; walkable kinds list each name (e.g. "Plain / Floor").
            info['name'] = names[0][0] if len(names) == 1 or info['move']['Fliers'] is None else ' / '.join(n for n, _ in names)
        veins = []
        script = terrain_script(code, pack)
        tr = [x for x in read_tricks(script) if max(x) < 100] if script else []
        warps = []
        if script:
            wsc = Script(script)
            for h in wsc.handlers():
                a = h['args']
                if len(a) >= 8 and a[4] == WARP:
                    tx, ty = (int(n) for n in wsc.string(a[7]).split(','))
                    warps.append(((a[0], H + 1 - a[1]), (tx, H + 1 - ty)))
        # Blocks the chapter script moves (Revelation 23's stone blocks): a function that moves a field object two tiles by two and
        # swaps the terrain under it, called with each block's two stops ('x, y' of its top left, from the top).
        blocks = []
        bscript = find_script(code, pack)
        if bscript:
            bsc = Script(bscript)
            hs = {h['index']: h for h in bsc.handlers()}
            movers = set()
            for i, h in hs.items():
                try:
                    ins = bsc.disasm(h)
                except (ValueError, IndexError):
                    continue
                if any(n == 'call' and a.startswith('ev::FieldObjectMove') for _, n, a in ins) and \
                        any(n == 'call' and a.startswith('ev::TerrainAttributeSetTID') for _, n, a in ins):
                    movers.add(i)
            for h in hs.values():
                try:
                    ins = bsc.disasm(h)
                except (ValueError, IndexError):
                    continue
                for k, (_, n, a) in enumerate(ins):
                    if n == 'gvar' and int(a, 16) in movers and k >= 5 and all(ins[k - j][1] == 'int' for j in range(1, 6)):
                        x0, y0, x1, y1, _ = (ins[k - j][2] for j in range(5, 0, -1))
                        blocks.append(((x0, H - y0), (x1, H - y1)))

        # Areas the chapter script sets as the map loads (its kind 7 handler) start in that state: Revelation 20 lays the first
        # bridge of each pair, the Heirs of Fate's The Changing Tide spreads three of its bogs (read live: Revelation 20's 34
        # bridge tiles are down on turn 1). The opening cutscene's own changes don't last (Revelation 20's bridge 7).
        loaded = set()
        cscript = find_script(code, pack)
        area_cells = {(x, y): {(x + i, H + 1 - (y + j)) for i in range(w) for j in range(h)} for x, y, w, h, k in tr if k == AREA}
        # Its calls, and those of the functions it calls (Paralogue 2's opening sets its moats in a helper, each by its tile: kind 0,
        # the trick there whatever its kind; read in X002.cmb, every route alike).
        lsc = Script(cscript) if cscript else None
        lby = {hh['index']: hh for hh in lsc.handlers()} if lsc else {}

        def trick_sets(h, depth=0):
            try:
                ins = lsc.disasm(h)
            except (ValueError, IndexError):
                return []
            out = []
            for i, (_, n, a) in enumerate(ins):
                if n == 'call' and a.startswith('ev::TrickSet/') and i >= 5 and all(ins[i - k][1] == 'int' for k in range(1, 6)):
                    out.append((ins[i - 5][2], ins[i - 4][2], ins[i - 3][2], ins[i - 2][2]))
                elif n == 'gvar' and depth < 2 and int(a, 16) in lby and lby[int(a, 16)]['kind'] & 0xFF == 0 and \
                        (i + 1 >= len(ins) or ins[i + 1][1] == 'pop' or ins[i - 1][1] not in ('int', 'str', 'var')):
                    out += trick_sets(lby[int(a, 16)], depth + 1)
            return out
        for h in lsc.handlers() if lsc else []:
            if h['kind'] & 0xFF != 7:
                continue
            for x, y, kind, state in trick_sets(h):
                if kind in (AREA, 0) and (x, y) in area_cells:
                    loaded = (loaded | area_cells[(x, y)]) if state == 2 else (loaded - area_cells[(x, y)])
        if code in OPENING_STORMS:
            loaded |= {t for t in afters if (t[0], H + 1 - t[1]) not in OPENING_STORMS[code]}
        if code == 'B008':
            loaded = set()  # its frozen lake is already the start (above)
        loaded &= set(afters)
        if loaded:
            grid = [list(row) for row in rows]
            for (c, y) in loaded:
                grid[H - y][c - 1] = afters[(c, y)]
            rows = [''.join(row) for row in grid]

        # What each vein does to its areas: TrickSetForDragon's fourth argument is 2 to put them in their second state (Birthright 10
        # raises its spikes) or 1 to flip them (most veins; Revelation 11's lower its spikes once they've sprung). A vein that calls
        # a function flips them too (Revelation 20 moves a bridge from one place to the other).
        vein_state = {}
        if script:
            sc0 = Script(script)
            for h in sc0.handlers():
                a = h['args']
                if len(a) < 5 or a[4] != VEIN:
                    continue
                ins = sc0.disasm(h)
                state = None
                for i, (_, n, arg) in enumerate(ins):
                    if n == 'call' and arg.startswith('ev::TrickSetForDragon/') and i >= 3 and ins[i - 3][1] == 'int':
                        state = 2 if ins[i - 3][2] == 2 else 'toggle'
                if state is None and any(n == 'gvar' for _, n, _ in ins):
                    state = 'toggle'
                vein_state[(a[0], H + 1 - a[1])] = state
        vtiles = [(x, H + 1 - y) for x, y, w, h, k in tr if k == VEIN]
        mine = {v: set() for v in vtiles}

        def cells(x, y, w, h):
            return {(x + i, y - j) for i in range(w) for j in range(h)}

        def dist(v, cs):
            return min(abs(v[0] - a) + abs(v[1] - b) for a, b in cs)
        # Areas follow the vein(s) they belong to: one vein -> its own area; a run of veins followed by
        # fewer areas (or single-tile ones) -> they share them; otherwise each area goes to its nearest vein.
        has_toggles = any(k == TOGGLE for *_, k in tr)
        groups, run, areas = [], [], []
        for x, y, w, h, k in tr:
            if k == VEIN:
                if areas:
                    groups.append((run, areas))
                    run, areas = [], []
                run.append((x, H + 1 - y))
            elif k == (TOGGLE if has_toggles else AREA) and run:
                areas.append(cells(x, H + 1 - y, w, h))
        if run:
            groups.append((run, areas))
        for run, areas in groups:
            if not areas:
                continue
            if len(run) == 1 or len(areas) == 1 or all(len(cs) == 1 for cs in areas):
                for v in run:
                    for cs in areas:
                        mine[v] |= cs
            else:
                for cs in areas:
                    mine[min(run, key=lambda v: dist(v, cs))] |= cs
        # A vein's handler names the areas it changes: its 8th argument is a string of their corners ('3, 3, 5, 3, 6, 3'), in
        # the script's own top-down coordinates. Where it does, that's the vein's patch (Revelation 12's last vein changes all
        # four areas; Conquest 17's veins all name the one area covering the map, so each shows every tile there that changes).
        if script:
            area_at = {(x, y): cells(x, H + 1 - y, w, h) for x, y, w, h, k in tr if k == AREA}
            sc = Script(script)
            for h in sc.handlers():
                a = h['args']
                if len(a) < 8 or a[4] != VEIN or (a[0], H + 1 - a[1]) not in mine:
                    continue
                # Or its code hands them to TrickSetAnyForDragon, last: Birthright 21's bridge vein at (11, 3) names only its
                # bridge, '8, 24' (the lava over the boss's island is the boss's battle talk's doing, not a vein's).
                try:
                    ins = sc.disasm(h)
                except (ValueError, IndexError):
                    ins = []
                given = next((ins[k - 1][2].strip("'") for k in range(len(ins) - 1, 0, -1) if ins[k][1] == 'call'
                              and ins[k][2].startswith('ev::TrickSetAnyForDragon') and ins[k - 1][1] == 'str'), None)
                try:
                    nums = [int(n) for n in (given or sc.string(a[7])).split(',')]
                except (ValueError, IndexError, UnicodeDecodeError):
                    continue
                named = [area_at[(x, y)] for x, y in zip(nums[::2], nums[1::2]) if (x, y) in area_at]
                if not named:
                    continue
                mine[(a[0], H + 1 - a[1])] = set().union(*named)
        if len(vtiles) == 1 and not mine[vtiles[0]]:
            mine[vtiles[0]] = set(afters)
        for v in vtiles:
            state = vein_state.get(v) or 2
            patch = []
            for t in mine[v]:
                if t not in afters:
                    continue
                if t in loaded and state == 'toggle':
                    patch.append((t, firsts[t]))  # back to its first state
                elif t not in loaded and state in (2, 'toggle'):
                    patch.append((t, afters[t]))
            veins.append({'tile': v, 'patch': sorted(patch, key=lambda p: (-p[0][1], p[0][0]))})
        # A breakable tile's HP sits on the terrain-script trick that covers it (args: x, y, w, h, kind, HP).
        hp = {}
        if script:
            for h in Script(script).handlers():
                a = h['args']
                if len(a) >= 6 and a[4] in (0, 9) and 0 < a[5] < 1000 and max(a[:4]) < 100:
                    for i in range(a[2]):
                        for j in range(a[3]):
                            hp[(a[0] + i, H + 1 - (a[1] + j))] = a[5]
        breakables = [{'tile': t, 'becomes': b, 'also': [], **({'hp': hp[t]} if t in hp else {})}
                      for t, b in sorted(breaks.items(), key=lambda kv: (-kv[0][1], kv[0][0]))]
        # A tile that changes once something breaks goes with the nearest breakable (within 3 tiles).
        for t, b in knock_on.items():
            near = min(breakables, key=lambda x: abs(x['tile'][0] - t[0]) + abs(x['tile'][1] - t[1]), default=None)
            if near and abs(near['tile'][0] - t[0]) + abs(near['tile'][1] - t[1]) <= 3:
                near['also'].append((t, b))
        # Traps: a handler for one of your units stopping in an area (kind 0x14, your side) that puts a terrain area in its second
        # state, itself or through a helper it calls with the area's corner: Birthright 10's and Revelation 11's bamboo spikes
        # (checked live on Birthright 10: a unit stopping on a spike tile outside the handler's area springs nothing, one inside it
        # raises the whole group).
        traps = []
        if cscript:
            csc = Script(cscript)
            by_index = {h['index']: h for h in csc.handlers()}

            def raised(h, args=()):
                """The corners of the terrain areas a handler puts in their second state."""
                found = []
                try:
                    ins = csc.disasm(h)
                except (ValueError, IndexError):
                    return found
                for i, (_, n, a) in enumerate(ins):
                    if n == 'call' and a.startswith('ev::TrickSet/') and i >= 5:
                        vals = []
                        for k in range(5, 0, -1):
                            op, arg = ins[i - k][1], ins[i - k][2]
                            vals.append(arg if op == 'int' else args[int(arg, 16)] if op == 'var' and int(arg, 16) < len(args) else None)
                        if vals[2] == AREA and vals[3] == 2 and isinstance(vals[0], int) and isinstance(vals[1], int):
                            found.append((vals[0], vals[1]))
                    if n == 'gvar' and not args and int(a, 16) in by_index:
                        lits, j = [], i - 1
                        while j >= 0 and ins[j][1] in ('int', 'str'):
                            lits.insert(0, ins[j][2])
                            j -= 1
                        found += raised(by_index[int(a, 16)], tuple(lits))
                return found
            for h in csc.handlers():
                a = h['args']
                if h['kind'] & 0xFF != 0x14 or len(a) < 5 or a[4] != 0 or min(a[:4]) < 0:
                    continue
                cells = set().union(*(area_cells.get(c, set()) for c in raised(h)))
                patch = sorted(((t, afters[t]) for t in cells if t in afters and t not in loaded), key=lambda p: (-p[0][1], p[0][0]))
                if patch:
                    zone = [min(a[0], a[2]), H + 1 - max(a[1], a[3]), max(a[0], a[2]), H + 1 - min(a[1], a[3])]
                    traps.append({'zone': zone, 'patch': patch})
        # Walls the chapter script raises and lowers (Revelation 16's flame walls): a wall is a function that hands a helper the
        # corners of its areas, its flag, then the flags of the walls it shares an area with (the helper keeps a shared area up
        # while the other wall is). The battle-start handler (kind 8) raises them all, then lowers one of several sets that
        # RandomGetGame picks; a turn handler flips sets on the turns that divide by 3 and by 4; each vein flips its own wall,
        # and stays usable. Read live on Lunatic: the battle started with the fifth set down, and every state after two veins and
        # on turns 3 and 4 matched.
        switch = None
        if cscript:
            csc = Script(cscript)
            hs = {h['index']: h for h in csc.handlers()}

            def number(flag):
                return int(flag[len(WALL_FLAG):].translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            wall_of, wall_tiles = {}, {}
            for i, h in hs.items():
                if h['kind'] & 0xFF:
                    continue
                try:
                    ins = csc.disasm(h)
                except (ValueError, IndexError):
                    continue
                strs = [a.strip("'") for _, n, a in ins if n == 'str']
                if not strs or not strs[0].startswith(WALL_FLAG) or any(n == 'call' for _, n, _ in ins):
                    continue
                ints = [a for _, n, a in ins if n == 'int']
                segs = list(zip(ints[::2], ints[1::2]))
                if not segs or len(ints) % 2 or not all(sg in area_cells for sg in segs):
                    continue
                wall_of[i] = number(strs[0])
                wall_tiles[number(strs[0])] = set().union(*(area_cells[sg] for sg in segs))
            if wall_of:
                def walls_called(h, arg):
                    '''The walls a handler flips: the wall functions it calls with `arg` (0 at the start, 1 on a turn).'''
                    ins = csc.disasm(h)
                    return [wall_of[int(a, 16)] for k, (_, n, a) in enumerate(ins)
                            if n == 'gvar' and int(a, 16) in wall_of and ins[k - 1][1] == 'int' and ins[k - 1][2] == arg]
                starts, turns = [], []
                for h in hs.values():
                    ins = csc.disasm(h)
                    if h['kind'] & 0xFF == 8 and any(n == 'call' and a.startswith('ev::RandomGetGame') for _, n, a in ins):
                        starts = [sorted(walls_called(hs[int(a, 16)], 0)) for _, n, a in ins if n == 'gvar' and int(a, 16) in hs]
                    if h['kind'] & 0xFF == 0x10:
                        every = None
                        for k, (_, n, a) in enumerate(ins):
                            if n == 'call' and a.startswith('ev::TurnGet') and [x[1] for x in ins[k + 1:k + 6]] == ['int', 'mod', 'int', 'eq', 'jz']:
                                every = ins[k + 1][2]
                                turns.append({'every': every, 'from': h['args'][0], 'walls': []})
                            elif n == 'gvar' and int(a, 16) in wall_of and every and ins[k - 1][2] == 1:
                                turns[-1]['walls'].append(wall_of[int(a, 16)])
                turns = [t for t in turns if t['walls']]
                downs = {afters[t] for ts in wall_tiles.values() for t in ts}
                assert len(starts) > 1 and turns and len(downs) == 1, (code, starts, turns, downs)
                switch = {'walls': sorted(wall_tiles.items()), 'down': downs.pop(), 'starts': starts,
                          'turns': [dict(t, walls=sorted(t['walls'])) for t in turns]}
                # A vein flips the wall whose flag its handler tests first.
                tsc = Script(script)
                for h in tsc.handlers():
                    a = h['args']
                    if len(a) >= 5 and a[4] == VEIN:
                        flags = [x[2].strip("'") for x in tsc.disasm(h) if x[1] == 'str' and x[2].strip("'").startswith(WALL_FLAG)]
                        v = next((v for v in veins if v['tile'] == (a[0], H + 1 - a[1])), None)
                        if v and flags:
                            v['flips'], v['patch'] = number(flags[0]), []
                assert all('flips' in v for v in veins), code
        decor = statues(walls, firsts, set(breaks) | set(afters)) if map_id in STATUE_MAPS else {}
        decor |= dragons(walls) if map_id in DRAGON_MAPS else {}
        decor |= pillars(walls, firsts) if map_id in PILLAR_MAPS else {}
        out[map_id] = {'statues': decor, 'houses': house_blocks(buildings, set(breaks) | set(afters)), 'code': code, 'dark': dark, 'breakables': breakables, 'veins': veins, 'traps': traps, 'width': W, 'height': H,
                       'grid': rows, 'terrain': kinds, 'spent': sorted(spent.items(), key=lambda kv: (-kv[0][1], kv[0][0])),
                       'switch': switch, 'pots': pots, 'warps': warps, 'blocks': blocks, 'names': tile_names}

    # Out in the app's two-character terrain codes (scripts/terrain_codes.py).
    ground = json.load(open(GROUND, encoding='utf-8')) if os.path.exists(GROUND) else {}
    for map_id, m in out.items():
        m['grid'] = [encode_row('fates', row) for row in m['grid']]
        for b in m['breakables']:
            b['becomes'] = encode('fates', b['becomes'])
            b['also'] = [(t, encode('fates', a)) for t, a in b['also']]
        for v in m['veins'] + m['traps']:
            v['patch'] = [(t, encode('fates', b)) for t, b in v['patch']]
        m['spent'] = [(t, encode('fates', b)) for t, b in m['spent']]
        if m['switch']:
            m['switch']['down'] = encode('fates', m['switch']['down'])
        m['terrain'] = {encode('fates', L): info for L, info in m['terrain'].items()}
        same_stats = lambda a, b: {k: v for k, v in m['terrain'][a].items() if k not in ('name', 'tileNames')} ==             {k: v for k, v in m['terrain'][b].items() if k not in ('name', 'tileNames')}
        if map_id in STONE_BRIDGES and 'tb' in m['terrain']:
            stone = lambda c: 't8' if c == 'tb' else c
            m['grid'] = [''.join(stone(row[i:i + 2]) for i in range(0, len(row), 2)) for row in m['grid']]
            for v in m['veins'] + m['traps']:
                v['patch'] = [(t, stone(b)) for t, b in v['patch']]
            for b in m['breakables']:
                b['becomes'] = stone(b['becomes'])
                b['also'] = [(t, stone(a)) for t, a in b['also']]
            m['spent'] = [(t, stone(b)) for t, b in m['spent']]
            m['terrain']['t8'] = m['terrain'].pop('tb')
        if map_id in SHIP_FLOORS and 't1' in m['terrain']:
            m['grid'] = [''.join('t3' if row[i:i + 2] == 't1' else row[i:i + 2] for i in range(0, len(row), 2)) for row in m['grid']]
            m['terrain']['t3'] = dict(m['terrain']['t1'], name='Deck')
            # Its walls beside the deck its wood and its partitions there its wooden sides, and every wall or partition joined to them
            # the same (a cabin's or a hull's far side: the user, no stone on a ship); other partitions, where a map has them, a town's
            # low stone walls.
            g2 = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            hh, ww = len(g2), len(g2[0])
            near = lambda xx, yy: [(xx + dx, yy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                                   if 0 <= xx + dx < ww and 0 <= yy + dy < hh]
            looks, todo = {}, []
            for yy in range(hh):
                for xx in range(ww):
                    if g2[yy][xx] in ('wa', 'wg') and any(g2[b][a] in ('t3', 'tc', 'bz') for a, b in near(xx, yy)):
                        looks[(xx, yy)] = 'wood' if g2[yy][xx] == 'wa' else 'ship'
                        todo.append((xx, yy))
            while todo:
                xx, yy = todo.pop()
                for a, b in near(xx, yy):
                    if (a, b) not in looks and g2[b][a] == g2[yy][xx]:
                        looks[(a, b)] = looks[(xx, yy)]
                        todo.append((a, b))
            if map_id in STONE_PARTITIONS:
                looks.update({(xx, yy): 'stone' for yy in range(hh) for xx in range(ww) if g2[yy][xx] == 'wg' and (xx, yy) not in looks})
            if looks:
                m['wallLooks'] = {f'{xx + 1},{hh - yy}': v for (xx, yy), v in sorted(looks.items())}
        if map_id in BOATS and 't1' in m['terrain']:
            m['grid'] = [''.join('t3' if row[i:i + 2] == 't1' else row[i:i + 2] for i in range(0, len(row), 2)) for row in m['grid']]
            m['terrain']['t3'] = dict(m['terrain'].pop('t1'), name='Deck')
            g2 = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            hh, ww = len(g2), len(g2[0])

            def run(xx, yy, dx, dy):
                '''How many deck tiles in a row from beside (xx, yy) the way (dx, dy) goes.'''
                n = 0
                while 0 <= xx + dx * (n + 1) < ww and 0 <= yy + dy * (n + 1) < hh and g2[yy + dy * (n + 1)][xx + dx * (n + 1)] == 't3':
                    n += 1
                return n
            ends = {}
            for yy in range(hh):
                for xx in range(ww):
                    if g2[yy][xx] != 'wg':
                        continue
                    e, w_ = run(xx, yy, 1, 0), run(xx, yy, -1, 0)
                    n_, s_ = run(xx, yy, 0, -1), run(xx, yy, 0, 1)
                    if e or w_:
                        ends[f'{xx + 1},{hh - yy}'] = 'e' if w_ and (not e or w_ <= e) else 'w'
                    elif n_ or s_:
                        ends[f'{xx + 1},{hh - yy}'] = 's' if n_ and (not s_ or n_ <= s_) else 'n'
            if ends:
                m['boatEnds'] = ends
            rest = {f'{xx + 1},{hh - yy}': 'wood' for yy in range(hh) for xx in range(ww) if g2[yy][xx] == 'wg' and f'{xx + 1},{hh - yy}' not in ends}
            if rest:
                m['wallLooks'] = {**(m.get('wallLooks') or {}), **rest}
        if map_id in PLAIN_AS_FLOOR and 'ta' in m['terrain'] and 't1' in m['terrain'] and same_stats('ta', 't1'):
            m['grid'] = [''.join('t1' if row[i:i + 2] == 'ta' else row[i:i + 2] for i in range(0, len(row), 2)) for row in m['grid']]
        if map_id in DOWN_STAIRS:
            m['grid'] = stairwells(m['grid'])
            if any('bz' in r[i:i + 2] for r in m['grid'] for i in range(0, len(r), 2)):
                m['terrain']['bz'] = {**m['terrain']['tc'], 'name': 'Stairs going down'}
        for x0, y0, x1, y1 in STEPS.get(map_id, []):
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    c = m['grid'][m['height'] - y][2 * (x - 1):2 * x]
                    assert c in ('t1', 'ta', 'ga', 'te', 'td', 't3'), (map_id, x, y, c)
                    m['statues'][f'{x},{y}'] = 'stairs'
        spans = {}
        for (sx, sy), span in BRIDGE_SPANS.get(map_id, []):
            at = lambda x, y: m['grid'][m['height'] - y][2 * (x - 1):2 * x] if 1 <= x <= m['width'] and 1 <= y <= m['height'] else None
            seed = at(sx, sy)
            assert seed in ('tb', 't8'), (map_id, sx, sy, seed)
            part, todo = set(), [(sx, sy)]
            while todo:
                p = todo.pop()
                if p in part or at(*p) != seed:
                    continue
                part.add(p)
                todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
            spans.update({f'{x},{y}': span for x, y in sorted(part)})
        if spans:
            m['bridgeSpans'] = spans
        W, H = m['width'], m['height']
        at = lambda x, y: m['grid'][H - y][2 * (x - 1):2 * x] if 1 <= x <= W and 1 <= y <= H else None

        def put(x, y, code):
            row = m['grid'][H - y]
            m['grid'][H - y] = row[:2 * (x - 1)] + code + row[2 * x:]
        every = lambda *codes: {(x, y) for y in range(1, H + 1) for x in range(1, W + 1) if at(x, y) in codes}
        looks = m.setdefault('wallLooks', {})
        decor = m['statues']
        # The user's notes of 2026-11-26: tiles drawn as the game names them.
        names = m.pop('names')
        for (x, y), (jp, en) in names.items():
            k = f'{x},{y}'
            if jp in DRAWN_AS.get(map_id, {}):
                m.setdefault('looksAs', {})[k] = DRAWN_AS[map_id][jp]
            if jp in NAMED_DECOR.get(map_id, {}):
                decor[k] = NAMED_DECOR[map_id][jp]
            if map_id in SKY_VOID and jp == '空' and at(x, y) == 'wd':
                looks[k] = 'void'
            if jp in OWN_NAMES.get(map_id, ()):
                info = m['terrain'][at(x, y)]
                info.setdefault('tileNames', {}).setdefault(en, []).append((x, y))
        for (x, y), kind in TILE_DECOR.get(map_id, {}).items():
            decor[f'{x},{y}'] = kind
        if map_id in STAND_ON:
            m['standOn'] = {f'{x},{y}': code for (x, y), code in STAND_ON[map_id].items()}
        # Pots stand on the floor round them where it's floor, not the plain the game leaves under an object (Conquest 12's: the user).
        if 't1' in m['terrain']:
            for x, y in m.pop('pots'):
                near = [at(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
                if at(x, y) == 'ta' and near.count('t1') * 2 > sum(c in ('t1', 'ta', 'ga') for c in near):
                    put(x, y, 't1')
                    plain = m['terrain']['ta']
                    names = plain.get('tileNames') or {}
                    if [x, y] in names.get('Floor', []) or (x, y) in names.get('Floor', []):
                        names['Floor'] = [t for t in names['Floor'] if tuple(t) != (x, y)]
                        if not names['Floor']:
                            del names['Floor']
                            plain['name'] = plain['name'].split(' / ')[0]
                    if not names:
                        plain.pop('tileNames', None)
            # A vein's or trap's change to the floor where the pot now stands on the floor changes nothing to draw (Conquest 12's vein).
            for v in m['veins'] + m['traps']:
                v['patch'] = [(t, b) for t, b in v['patch'] if at(*t) != b]
            m['spent'] = [(t, b) for t, b in m['spent'] if at(*t) != b]
        else:
            m.pop('pots')
        if map_id in COBBLES:
            for x, y in rects(COBBLES[map_id][0]):
                if at(x, y) in ('ta', 'ga'):
                    put(x, y, 'gb')
            m['terrain']['gb'] = {k: v for k, v in m['terrain']['ta'].items() if k != 'tileNames'} | {'name': m['terrain']['ta']['name'].split(' / ')[0]}
        if map_id in PAVED_FLOORS:
            for x, y in every('t1'):
                put(x, y, 'gb')
            m['terrain']['gb'] = dict(m['terrain'].pop('t1'))
        if map_id in BIG_TREES:
            stones = {tuple(t) for t in (m['terrain']['wj'].get('tileNames') or {}).get('Stone', [])}
            decor.update({f'{x},{y}': 'rock' if (x, y) in stones else 'cherry' for x, y in every('wj')})
        if map_id in RUBBLE_MAPS:
            decor.update({f'{x},{y}': 'rubble' for x, y in every('wj')})
        if map_id in CLIFF_PARTITIONS:
            looks.update({f'{x},{y}': 'cliff' for x, y in every('wg')})
        if map_id in STONE_FENCES:
            looks.update({f'{x},{y}': 'stone' for x, y in every('wg')})
        if map_id in FLOOR_BRIDGES:
            boxes = FLOOR_BRIDGES[map_id]
            m['bridgeFloors'] = sorted(f'{x},{y}' for x, y in rects(boxes))
            assert all(at(*map(int, k.split(','))) == 't1' for k in m['bridgeFloors']), map_id
            m['wholeBridges'] = [[x0, x1, y0, y1] for x0, y0, x1, y1 in boxes]
        if map_id in DOCKS:
            for x, y in DOCKS[map_id]:
                assert at(x, y) == 't1', (map_id, x, y, at(x, y))
                put(x, y, 'gi')
            m['terrain']['gi'] = dict(m['terrain']['t1'])
        if map_id in SKY_RIFTS:
            px = art(map_id, W, H)
            for x, y in every('wa'):
                sky = px is not None and np.median(px[H - y][x - 1], axis=0).mean() > 140
                looks[f'{x},{y}'] = 'sky' if sky else 'cliff'
        if map_id in TIMBER_WALLS:
            for x, y in every('wa'):
                if any((at(x + dx, y + dy) or 'w')[0] != 'w' for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    looks[f'{x},{y}'] = 'timber'
        if map_id in STALL_MAPS:
            colours = ('red', 'blue', 'yellow')
            for b, (comp, _) in enumerate(parts(every('wa'))):
                # Its rows of one width each a block of their own (Birthright 22's blocks sit staggered a tile), then its stalls.
                bands, ys = [], sorted({y for _, y in comp}, reverse=True)
                for y in ys:
                    xs = sorted(x for x, yy in comp if yy == y)
                    span = (xs[0], xs[-1])
                    if bands and bands[-1][0] == span and bands[-1][1][-1] == y + 1:
                        bands[-1][1].append(y)
                    else:
                        bands.append((span, [y]))
                chunks = [c for (x0, x1), rows in bands for c in stall_chunks((x0, min(rows), x1, max(rows)))]
                given = []
                for k, chunk in enumerate(chunks):
                    near = {tuple(t) for x, y in chunk for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))} - chunk
                    taken = {given[j] for j, other in enumerate(chunks[:k]) if other & near}
                    # A stall touching all three colours takes a fourth (orange: the game's stalls come in more paints).
                    given.append(next(c for c in colours[b % 3:] + colours[:b % 3] + ('orange',) if c not in taken))
                    decor.update({f'{x},{y}': f'stall-{given[-1]}' for x, y in chunk})
        if map_id in GARDEN_MAPS:
            for comp, (x0, y0, x1, y1) in parts(every('wa')):
                ring = {(x, y) for x in range(x0 - 1, x1 + 2) for y in range(y0 - 1, y1 + 2)} - comp
                if (x1 - x0, y1 - y0) == (2, 2) and len(comp) == 9 and all(at(*t) == 'ta' for t in ring):
                    decor.update({f'{x},{y}': 'zenGarden' for x, y in comp})
        if map_id in CRATE_BUILDINGS:
            decor.update({f'{x},{y}': CRATE_BUILDINGS[map_id].get((x, y), 'crates') for x, y in every('oe')})
        for (x0, y0, x1, y1), colour in TOWN_STALLS.get(map_id, []):
            decor.update({f'{x},{y}': f'stall-{colour}' for x, y in rects([(x0, y0, x1, y1)])})
        decor.update({f'{x},{y}': 'crates' for x, y in TOWN_CRATES.get(map_id, [])})
        if map_id in PARTITION_DECOR:
            boxes, rest = PARTITION_DECOR[map_id]
            for x, y in every('wg'):
                decor[f'{x},{y}'] = next((k for (x0, y0, x1, y1), k in boxes if x0 <= x <= x1 and y0 <= y <= y1), rest)
        if map_id in FENCE_MAPS:
            crates = {tuple(map(int, k.split(','))) for k, v in decor.items() if v == 'crates'}
            joined = {(x, y) for x, y in crates if {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)} & crates}
            for x, y in every('wg') | joined:
                looks[f'{x},{y}'] = 'fence'
                decor.pop(f'{x},{y}', None)
            for b in m['breakables']:
                looks[f"{b['tile'][0]},{b['tile'][1]}"] = 'wall'
            m['boldFences'] = True
        for x0, y0, x1, y1, colour in ROOFS.get(map_id, []):
            decor.update({f'{x},{y}': f'roof-{colour}' for x, y in rects([(x0, y0, x1, y1)])})
        for box in WALLED_HOUSES.get(map_id, []):
            decor.update({f'{x},{y}': 'walledHouse' for x, y in rects([box])})
        if map_id in GREY_ROOFS:
            m['greyRoofs'] = True
        # Tiles that send a unit to another: in pairs that lead to each other, stairs (the Rainbow Sage's, Conquest 23's and 27's: the
        # pairs the user checked in the game on the Rainbow Sage's map); one way, Revelation 18's warps, each sigil and the platform it
        # sends a unit to (the user: a warp platform tile, and where they go).
        warps = m.pop('warps')
        both = {(a, b) for a, b in warps if (b, a) in warps}
        if both:
            m['links'] = [[list(a), list(b)] for a, b in sorted(both) if a < b]
        warps = [(a, b) for a, b in warps if (a, b) not in both]
        if warps:
            m['warps'] = [[list(a), list(b)] for a, b in warps]
            decor.update({f'{x},{y}': 'warpSigil' for (x, y), _ in warps if at(x, y) not in (None, 'wa', 'wd')})
            decor.update({f'{x},{y}': 'warpPad' for _, (x, y) in warps})
        # Revelation 23's stone blocks: the ground beside each stop paved as the blocks' floor, as its art paves it (the user: flagstones
        # on the entry tiles), the plain's numbers and name kept; each block's two stops, its bottom left tile.
        blocks = m.pop('blocks')
        if blocks:
            entries = set()
            for stop in (s for pair in blocks for s in pair):
                box = {(stop[0] + i, stop[1] + j) for i in (0, 1) for j in (0, 1)}
                for x, y in box:
                    for t in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if t not in box and at(*t) in ('ta', 'ga'):
                            entries.add(t)
            for x, y in sorted(entries):
                put(x, y, 't1')
            floor = m['terrain']['t1']
            floor['name'] = 'Floor / Plain'
            floor['tileNames'] = {**(floor.get('tileNames') or {}), 'Plain': sorted(entries, key=lambda p: (-p[1], p[0]))}
            m['movingBlocks'] = [[list(a), list(b)] for a, b in blocks]
        # Revelation 16's flame walls, up and down, drawn as such wherever they stand (the user: a fire wall tile, up and down).
        if m.get('switch'):
            m['flameWalls'] = sorted({f'{x},{y}' for _, ts in m['switch']['walls'] for x, y in ts})
        if not looks:
            del m['wallLooks']
        if not m['statues']:
            del m['statues']
        # Its houses drawn whole (BUILDINGS), each piece with the numbers of the building it stands for.
        houses = m.pop('houses')
        if map_id in NO_HOUSES:
            houses = set()
        if map_id in YURT_MAPS:
            for comp, _ in parts(houses):
                m.setdefault('statues', {}).update({f'{x},{y}': 'roundYurt' for x, y in comp})
            houses = set()
        drawn_over = {tuple(map(int, k.split(','))) for k, v in (m.get('statues') or {}).items()
                      if v.startswith(('stall-', 'roof-')) or v in ('crates', 'walledHouse')}
        houses -= drawn_over
        fort_tiles = {(x, y) for x0, y0, x1, y1 in FORTS.get(map_id, []) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
        houses -= fort_tiles
        if fort_tiles:
            rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            was = {}
            for x, y in fort_tiles:
                was[(x, y)] = rows[m['height'] - y][x - 1]
                rows[m['height'] - y][x - 1] = 'XC'
            placed = map_pieces.place([''.join(r) for r in rows], 'XC', 'c', {'XC'})
            m['grid'] = placed
            for x, y in fort_tiles:
                piece = placed[m['height'] - y][2 * (x - 1):2 * x]
                own = {k: v for k, v in m['terrain'][was[(x, y)]].items() if k != 'tileNames'}
                m['terrain'].setdefault(piece, dict(own, name='Fort'))
        # Where the game's buildings join into blocks the house rule can't part (Fates x21's town: its walls and houses all Edifice),
        # the render's roofs part them (scripts/fates_ground.py: ROOF_COLOURS), each colour's blocks its own houses.
        cuts = []
        roofs = [] if map_id in ROOFS else (ground.get(map_id) or {}).get('roofs') or []
        # A town's houses as its render shows them, each its own house where they stand side by side (Paralogue 20's).
        own = TOWN_HOUSES.get(map_id, [])
        for k, box in enumerate(own):
            tiles = rects([box])
            houses |= tiles
            others = rects([b for j, b in enumerate(own) if j != k])
            cuts += [((x - 1, m['height'] - y), (x, m['height'] - y)) for x, y in tiles if (x + 1, y) in others or ((x + 1, y) in houses and (x + 1, y) not in tiles)]
            cuts += [((x - 1, m['height'] - y), (x - 1, m['height'] - y - 1)) for x, y in tiles if (x, y + 1) in others]
        for k, group in enumerate(roofs):
            tiles = {tuple(t) for t in group}
            houses |= house_blocks(tiles, set())
            others = {tuple(t) for j, g2 in enumerate(roofs) if j != k for t in g2}
            cuts += [((x - 1, m['height'] - y), (x, m['height'] - y)) for x, y in tiles if (x + 1, y) in others]
            cuts += [((x - 1, m['height'] - y), (x - 1, m['height'] - y - 1)) for x, y in tiles if (x, y + 1) in others]
        if houses:
            rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            was = {}
            for x, y in houses:
                was[(x, y)] = rows[m['height'] - y][x - 1]
                rows[m['height'] - y][x - 1] = 'XH'
            placed = map_pieces.place([''.join(r) for r in rows], 'XH', 'r', {'XH'}, side_on=True, cuts=cuts)
            m['grid'] = placed
            for x, y in houses:
                piece = placed[m['height'] - y][2 * (x - 1):2 * x]
                own = {k: v for k, v in m['terrain'][was[(x, y)]].items() if k != 'tileNames'}
                m['terrain'].setdefault(piece, dict(own, name='House'))
        ice = set()
        if map_id in ICE_MAPS:
            at = lambda x, y: m['grid'][m['height'] - y][2 * (x - 1):2 * x] if 1 <= x <= m['width'] and 1 <= y <= m['height'] else None
            seen = set()
            for y in range(1, m['height'] + 1):
                for x in range(1, m['width'] + 1):
                    if at(x, y) != 'wa' or (x, y) in seen:
                        continue
                    part, todo = set(), [(x, y)]
                    while todo:
                        p = todo.pop()
                        if p in part or at(*p) != 'wa':
                            continue
                        part.add(p)
                        todo += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
                    seen |= part
                    xs, ys = [p[0] for p in part], [p[1] for p in part]
                    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
                    kind = 'ice' if (w, h) == (2, 2) else 'frozenFountain' if (w, h) == (3, 3) else None
                    assert kind and len(part) == w * h, (map_id, sorted(part))
                    m.setdefault('statues', {}).update({f'{px},{py}': kind for px, py in part})
                    ice |= part
        # A map whose buildings all stand in ruins (Conquest 15's: the user, every structure a form of ruins): its houses' tiles and its
        # closed villages drawn in ruins (`ruins`), their numbers kept.
        if map_id in RUINED:
            m['ruins'] = sorted(f'{x + 1},{m["height"] - r}' for r, row in enumerate(m['grid']) for x in range(len(row) // 2)
                                if re.match(r'^r[a-r]$|^od$|^oe$', row[2 * x:2 * x + 2]))
        # Its ground from its 3D field (scripts/fates_ground.py: data-raw/fates-ground.json): its colours, and the plain tiles its art
        # draws as dirt (the plain's stats and name).
        g = ground.get(map_id)
        if map_id in BOG_MUCK:
            m['muckAsBog'] = True
        if g:
            rows = [[r[i:i + 2] for i in range(0, len(r), 2)] for r in m['grid']]
            dirt = [] if map_id in NO_DIRT else [(x, y) for x, y in g['dirt'] if rows[m['height'] - y][x - 1] == 'ta']
            for x, y in dirt:
                rows[m['height'] - y][x - 1] = 'ga'
            m['grid'] = [''.join(r) for r in rows]
            if dirt:
                plain = m['terrain']['ta']
                m['terrain']['ga'] = {k: v for k, v in plain.items() if k != 'tileNames'} | {'name': plain['name'].split(' / ')[0]}
            m['fills'] = {**g['fills'], **FILLS.get(map_id, {}), **({'t3': BOATS[map_id]} if map_id in BOATS else {}),
                          **({'gb': COBBLES[map_id][1]} if map_id in COBBLES else {}),
                          **({'gb': g['fills']['t1']} if map_id in PAVED_FLOORS and 't1' in g['fills'] else {}),
                          **({'wf': SKY_RIFTS[map_id]} if map_id in SKY_RIFTS else {})}
    lines = [
        "import type { TerrainInfo } from './fatesTerrain'",
        "import type { TerrainCode } from './terrainCodes'",
        "import type { ChapterMap, SwitchWalls, Tile } from './types'",
        '',
        '/*',
        ' * GENERATED by scripts/build-fates-terrain.py from the game\'s own terrain files. Do not edit by hand:',
        ' * fix the generator (or the per-map data that uses it) and re-run it.',
        ' *',
        " * Each map's grid (top row first) in the app's two-character terrain codes, and each code's exact terrain",
        " * on that map: the game's English name, Def, Avo, heal % and movement costs.",
        ' */',
        'export interface GameTerrain {',
        '  code: string',
        '  width: number',
        '  height: number',
        '  grid: string[]',
        "  /** Tiles under Revelation's darkness: impassable, and shown shaded, until the chapter lifts it. */",
        '  dark?: Tile[]',
        '  /** Walls, partitions and the like that can be attacked down: what each becomes, and its HP when the game sets one. */',
        '  breakables?: { tile: Tile; becomes: TerrainCode; hp?: number; also?: { tile: Tile; becomes: TerrainCode }[] }[]',
        "  /** Every Dragon Vein tile, with the tiles it reshapes (empty when it changes no terrain), or the wall it flips. */",
        '  veins: { tile: Tile; patch: { tile: Tile; becomes: TerrainCode }[]; flips?: number }[]',
        "  /** Traps that spring when one of your units stops in their zone ([left, bottom, right, top]): the tiles they change. */",
        '  traps?: { zone: [number, number, number, number]; patch: { tile: Tile; becomes: TerrainCode }[] }[]',
        "  /** Walls the chapter raises and lowers (Revelation 16's flame walls): each wall's tiles, what they are once down, the",
        "   * sets the battle can start with down (it picks one at random), and the turns that flip sets of them. */",
        '  switchWalls?: SwitchWalls',
        "  /** Every tile with a second state (a vein's or the chapter's change, a door, a wall broken down), and that state: a",
        "   * challenge battle has the chapter's map with everything in it spent. */",
        '  spent?: { tile: Tile; becomes: TerrainCode }[]',
        '  terrain: Partial<Record<TerrainCode, TerrainInfo>>',
        "  /** Its ground's, water's and walls' colours, from its 3D field (scripts/fates_ground.py). */",
        '  fills?: Partial<Record<TerrainCode, string>>',
        "  /** Walls its art draws as statues (two tiles by two), its great dragon statue (five by five) or pillars: drawn over their tiles. */",
        "  decor?: Record<string, NonNullable<ChapterMap['decor']>[string]>",
        "  /** Tiles drawn in ruins though their terrain stands (Conquest 15's buildings: the user). */",
        '  ruins?: string[]',
        "  /** Walls drawn as what they are on a ship (Revelation 14's and Paralogue 3's cabins and rails: the user), or the void (Museum Melee's sky). */",
        "  wallLooks?: Record<string, 'wood' | 'ship' | 'stone' | 'timber' | 'cliff' | 'sky' | 'void' | 'fence' | 'wall'>",
        "  /** Tiles drawn as another code, their numbers kept (Boo Camp's partitions as its walls, Museum Melee's Exit as a purple pad). */",
        '  looksAs?: Record<string, TerrainCode>',
        "  /** The ground an icon stands on, by tile (Ghostly Gold's rubble on grass, Revelation 13's obstacles on stone or wood). */",
        '  standOn?: Record<string, TerrainCode>',
        "  /** Its houses' roofs grey, as its art paints them (Paralogue 20's: the user). */",
        "  greyRoofs?: true",
        "  /** Its muck drawn as a bog, no icon (Boo Camp's: the user). */",
        "  muckAsBog?: true",
        "  /** Its wooden fences bold, light wood edged dark (Museum Melee's, as Radiant Dawn's: the user). */",
        "  boldFences?: true",
        "  /** Floor its art draws as wooden bridges, drawn as them, and those bridges' boxes (Revelation 13's: the user). */",
        "  bridgeFloors?: string[]",
        "  wholeBridges?: [number, number, number, number][]",
        "  /** Sigils that send a unit standing on them to another tile (Revelation 18's): [from, to]. */",
        "  /** Stairs that take a unit to another tile, each pair's ends leading to each other (the Rainbow Sage's, Conquest 23's). */",
        "  links?: [Tile, Tile][]",
        "  warps?: [Tile, Tile][]",
        "  /** Stone blocks the chapter moves between two stops (Revelation 23's): each block's stops, their bottom left tiles. */",
        "  movingBlocks?: [Tile, Tile][]",
        "  /** The flame walls' tiles (Revelation 16's), up or down. */",
        "  flameWalls?: string[]",
        "  /** Bridges whose tiles all run one way though the bridge turns or jogs (Chapter 3's, Paralogue 15's: the user), by tile. */",
        "  bridgeSpans?: Record<string, 'ew' | 'ns'>",
        "  /** Each partition at a boat's end, drawn as its bow over the water the way it points (Birthright 12's: the user). */",
        "  boatEnds?: Record<string, 'n' | 's' | 'e' | 'w'>",
        '}',
        '',
        'export const GAME_TERRAIN: Record<string, GameTerrain> = {',
    ]
    for map_id, m in out.items():
        lines.append(f"  '{map_id}': {{")
        lines.append(f"    code: '{m['code']}',")
        if m.get('fills'):
            lines.append('    fills: { ' + ', '.join(f"{c}: '{v}'" for c, v in sorted(m['fills'].items())) + ' },')
        if m.get('statues'):
            lines.append('    decor: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['statues'].items())) + ' },')
        if m.get('ruins'):
            lines.append('    ruins: [' + ', '.join(f"'{t}'" for t in m['ruins']) + '],')
        if m.get('wallLooks'):
            lines.append('    wallLooks: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['wallLooks'].items())) + ' },')
        if m.get('bridgeSpans'):
            lines.append('    bridgeSpans: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['bridgeSpans'].items())) + ' },')
        if m.get('boatEnds'):
            lines.append('    boatEnds: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['boatEnds'].items())) + ' },')
        if m.get('looksAs'):
            lines.append('    looksAs: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['looksAs'].items())) + ' },')
        if m.get('standOn'):
            lines.append('    standOn: { ' + ', '.join(f"'{k}': '{v}'" for k, v in sorted(m['standOn'].items())) + ' },')
        if m.get('greyRoofs'):
            lines.append('    greyRoofs: true,')
        if m.get('muckAsBog'):
            lines.append('    muckAsBog: true,')
        if m.get('boldFences'):
            lines.append('    boldFences: true,')
        if m.get('bridgeFloors'):
            lines.append('    bridgeFloors: [' + ', '.join(f"'{t}'" for t in m['bridgeFloors']) + '],')
            lines.append('    wholeBridges: [' + ', '.join(f'[{a}, {b}, {c}, {d}]' for a, b, c, d in m['wholeBridges']) + '],')
        if m.get('warps'):
            lines.append('    warps: [' + ', '.join(f'[[{a[0]}, {a[1]}], [{b[0]}, {b[1]}]]' for a, b in m['warps']) + '],')
        if m.get('links'):
            lines.append('    links: [' + ', '.join(f'[[{a[0]}, {a[1]}], [{b[0]}, {b[1]}]]' for a, b in m['links']) + '],')
        if m.get('movingBlocks'):
            lines.append('    movingBlocks: [' + ', '.join(f'[[{a[0]}, {a[1]}], [{b[0]}, {b[1]}]]' for a, b in m['movingBlocks']) + '],')
        if m.get('flameWalls'):
            lines.append('    flameWalls: [' + ', '.join(f"'{t}'" for t in m['flameWalls']) + '],')
        lines.append(f"    width: {m['width']},")
        lines.append(f"    height: {m['height']},")
        lines.append('    grid: [')
        for i, row in enumerate(m['grid']):
            lines.append(f"      '{row}', // {m['height'] - i}")
        lines.append('    ],')
        if m['breakables']:
            lines.append('    breakables: [' + ', '.join(
                f"{{ tile: [{b['tile'][0]}, {b['tile'][1]}], becomes: {json.dumps(b['becomes'])}" + (f", hp: {b['hp']}" if 'hp' in b else '')
                + (', also: [' + ', '.join(f'{{ tile: [{x}, {y}], becomes: {json.dumps(a)} }}' for (x, y), a in b['also']) + ']' if b['also'] else '') + ' }'
                for b in m['breakables']) + '],')
        if m['spent']:
            lines.append('    spent: [' + ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in m['spent']) + '],')
        if m['dark']:
            lines.append('    dark: [' + ', '.join(f'[{x}, {y}]' for x, y in m['dark']) + '],')
        lines.append('    veins: [')
        for v in m['veins']:
            patch = ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in v['patch'])
            flips = f", flips: {v['flips']}" if 'flips' in v else ''
            lines.append(f"      {{ tile: [{v['tile'][0]}, {v['tile'][1]}], patch: [{patch}]{flips} }},")
        lines.append('    ],')
        if m['switch']:
            sw = m['switch']
            lines.append('    switchWalls: {')
            lines.append(f"      down: {json.dumps(sw['down'])},")
            lines.append('      walls: [')
            for n, ts in sw['walls']:
                lines.append(f"        {{ id: {n}, tiles: [" + ', '.join(f'[{x}, {y}]' for x, y in sorted(ts, key=lambda p: (-p[1], p[0]))) + '] },')
            lines.append('      ],')
            lines.append('      starts: [' + ', '.join('[' + ', '.join(map(str, st)) + ']' for st in sw['starts']) + '],')
            lines.append('      turns: [' + ', '.join(f"{{ every: {t['every']}, from: {t['from']}, walls: [{', '.join(map(str, t['walls']))}] }}"
                                                   for t in sw['turns']) + '],')
            lines.append('    },')
        if m['traps']:
            lines.append('    traps: [')
            for v in m['traps']:
                patch = ', '.join(f"{{ tile: [{x}, {y}], becomes: {json.dumps(b)} }}" for (x, y), b in v['patch'])
                lines.append(f"      {{ zone: [{', '.join(map(str, v['zone']))}], patch: [{patch}] }},")
            lines.append('    ],')
        lines.append('    terrain: {')
        for L, info in sorted(m['terrain'].items()):
            key = L
            move = ', '.join(f"{json.dumps(k) if ' ' in k else k}: {json.dumps(v)}" for k, v in info['move'].items())
            tile_names = ''
            if info.get('tileNames'):
                tile_names = ', tileNames: { ' + ', '.join(f"{json.dumps(n)}: [" + ', '.join(f'[{x}, {y}]' for x, y in ts) + ']'
                                                          for n, ts in info['tileNames'].items()) + ' }'
            lines.append(f"      {key}: {{ name: {json.dumps(info['name'])}, def: {info['def']}, avo: {info['avo']}, heal: {info['heal']}, move: {{ {move} }}{tile_names} }},")
        lines.append('    },')
        lines.append('  },')
    lines.append('}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(out), 'maps')


if __name__ == '__main__':
    main()

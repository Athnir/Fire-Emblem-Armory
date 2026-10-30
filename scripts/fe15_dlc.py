"""
Echoes: Shadows of Valentia's downloadable content, which isn't in the user's files (no DLC owned): transcribed from Fire Emblem Wiki
(fireemblemwiki.org: "Downloadable content in Fire Emblem Echoes: Shadows of Valentia", each weapon's page and each DLC map's page).
Replace with the game's own DLC files once they can be read.

Each weapon: its base stats, its forge stars as the wiki gives them (each star's totals and its "worth": the weapon's mark value plus
every star's cost so far, which matches the cartridge's own forge lists for the Steel Lance and the Blessed Lance), the combat arts it
teaches by their English names with the SP the wiki gives (scripts/build-fe15-items.py takes each art's numbers from the cartridge's
Skill.bin and checks the SP against its mastery), and the passive skills it grants. The three arts no cartridge table has are here
in full. Where each turns up: `REWARDS`.
"""

# The DLC is played from the world map's Connect menu, which first opens in Act 1 (Prima Games' and Twinfinite's guides).
OPENS_AT = 'fe15-1-1'

# name: category, range, (Mt, Wt, Hit, Crit), worth in (silver, gold) marks, stars [(Mt, Wt, Hit, Crit, worth)], arts [(name, SP)],
# passive skills, stat bonuses.
WEAPONS = {
    "Fernand's Lance": dict(category='Lance', range='1', base=(3, 1, 90, 0), worth=(20, 0),
                            stars=[(4, 1, 90, 0, (50, 0)), (5, 1, 90, 0, (120, 0)), (5, 1, 90, 5, (240, 0)), (6, 1, 90, 5, (240, 1)),
                                   (9, 1, 90, 15, (240, 3))],
                            arts=[('Longearche', 20), ('Penetrate', 10), ('Windsweep', 25)]),
    "Clair's Lance": dict(category='Lance', range='1', base=(2, 0, 90, 0), worth=(50, 0),
                          stars=[(3, 0, 90, 0, (50, 1)), (4, 0, 90, 0, (50, 2)), (5, 0, 90, 0, (50, 3)), (7, -1, 100, 0, (50, 5))],
                          arts=[('Mistdancer', 20)], passive=['Anti-Terrors'], stats={'res': 5}),
    "Clive's Lance": dict(category='Lance', range='1', base=(5, 2, 80, 0), worth=(30, 0),
                          stars=[(6, 2, 80, 0, (80, 0)), (7, 2, 80, 0, (200, 0)), (8, 2, 80, 0, (400, 0)), (9, 2, 80, 0, (400, 1)),
                                 (10, 2, 85, 0, (400, 3)), (13, 2, 90, 0, (400, 6))],
                          arts=[('Wrath Strike', 10), ('Armorcrush', 15), ('Lunge', 10)]),
    "Trainee's Lance": dict(category='Lance', range='1', base=(2, 0, 100, 0), worth=(20, 0),
                            stars=[(3, 0, 100, 0, (40, 0)), (4, 0, 100, 0, (90, 0)), (4, 0, 110, 0, (180, 0)), (5, 0, 110, 0, (320, 0)),
                                   (8, 0, 120, 0, (320, 1))],
                            arts=[('Solo Triangle Attack', 20)]),
    'Wayward Lance': dict(category='Lance', range='1', base=(3, 2, 70, 20), worth=(30, 0),
                          stars=[(4, 2, 70, 20, (60, 0)), (5, 2, 70, 20, (130, 0)), (6, 2, 70, 20, (250, 0)), (7, 2, 70, 20, (430, 0)),
                                 (10, 1, 70, 30, (430, 2))],
                          arts=[('Heaven or Hell', 20)]),
    "Python's Bow": dict(category='Bow', range='2–3', base=(2, 3, 80, 0), worth=(20, 0),
                         stars=[(3, 3, 80, 0, (60, 0)), (4, 3, 80, 0, (150, 0)), (5, 3, 80, 5, (300, 0)), (7, 3, 80, 10, (300, 2)),
                                (9, 3, 80, 20, (300, 4))],
                         arts=[('Curved Shot', 15), ('Heavy Draw', 20), ('Encloser', 20)], passive=['Anti-Fliers']),
    "Warrior's Sword": dict(category='Sword', range='1', base=(6, 2, 80, 20), worth=(30, 0),
                            stars=[(7, 2, 80, 20, (60, 0)), (7, 2, 85, 20, (130, 0)), (8, 2, 85, 20, (250, 0)), (10, 2, 100, 20, (250, 2))],
                            arts=[('Armor Disruptor', 15)]),
    "Lukas's Shield": dict(category='Shield', range='', wt=3, worth=(20, 0), stats={'def': 5},
                           arts=[('Swap', 5), ('Shove', 10), ('Defensive', 15)]),
}

# The arts only the DLC weapons teach (Fire Emblem Wiki's pages; `effect` is the game's help text the wiki quotes, or for Solo
# Triangle Attack, whose help text says nothing of what it does, the wiki's note).
NEW_ARTS = {
    'Armor Disruptor': {'name': 'Armor Disruptor', 'mastery': 15, 'hp': 5, 'mt': 5, 'hit': 30, 'crit': 10, 'effective': ['armour'],
                        'effect': 'Effective against armored units. Increases hit rate.'},
    'Heaven or Hell': {'name': 'Heaven or Hell', 'mastery': 20, 'hp': 4, 'hit': -30, 'crit': 30, 'strikes': 2,
                       'effect': 'Deals two strikes which either yield criticals or miss.'},
    'Solo Triangle Attack': {'name': 'Solo Triangle Attack', 'mastery': 20, 'hp': 5, 'strikes': 3, 'effect': 'Strikes three times.'},
}

# Where each turns up: (pack, DLC map, how). All once only (the first clear or recruitment).
REWARDS = {
    "Fernand's Lance": ('Rise of the Deliverance', 'Battle of Zofia Harbor', 'clear it with no casualties'),
    "Python's Bow": ('Rise of the Deliverance', 'Outpost Rescue', 'clear it with every ally rescued'),
    "Clair's Lance": ('Rise of the Deliverance', 'Flight from the Ruins', 'clear it'),
    "Clive's Lance": ('Rise of the Deliverance', 'Siege of Zofia Castle', 'clear it with no casualties'),
    "Lukas's Shield": ('Rise of the Deliverance', 'Siege of Zofia Castle', 'clear it with no casualties'),
    "Trainee's Lance": ('Cipher Companions', 'Cipher Legends I', 'given when Emma is recruited at its end'),
    'Wayward Lance': ('Cipher Companions', 'Cipher Legends I', 'given when Randal is recruited at its end'),
    "Warrior's Sword": ('Cipher Companions', 'Cipher Legends II', 'given when Yuzu is recruited at its end'),
}

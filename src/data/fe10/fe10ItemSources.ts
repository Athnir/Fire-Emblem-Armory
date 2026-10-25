import { itemSourcesFor } from '../../logic/fe9ItemSources'
import { FE10_MAP_SET } from './fe10MapSet'
import { FE10_WEAPONS } from './fe10Weapons'

/** Every chest, village, buried spot and enemy drop on Radiant Dawn's maps that gives an item, and the foes who carry a foe-only weapon. */
export const fe10ItemSources = itemSourcesFor(FE10_MAP_SET, new Set(FE10_WEAPONS.filter((w) => w.foeOnly).map((w) => w.name)))

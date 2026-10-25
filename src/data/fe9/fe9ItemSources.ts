import { itemSourcesFor } from '../../logic/fe9ItemSources'
import { FE9_MAP_SET } from './fe9MapSet'
import { FE9_WEAPONS } from './fe9Weapons'

/** Every chest, village, buried spot and enemy drop on Path of Radiance's maps that gives an item, and the foes who carry a foe-only weapon. */
export const fe9ItemSources = itemSourcesFor(FE9_MAP_SET, new Set(FE9_WEAPONS.filter((w) => w.foeOnly).map((w) => w.name)))

import { itemSourcesFor } from '../../logic/fe9ItemSources'
import { FE10_MAP_SET } from './fe10MapSet'
import { FE10_WEAPONS } from './fe10Weapons'

/**
 * Every chest, village, buried spot and enemy drop on Radiant Dawn's maps that gives an item, the foes who carry a foe-only weapon,
 * and the foes a weapon no base sells, bargains or forges can be taken from: any foe can be disarmed of any weapon but its locked
 * and seal-steal ones, which are foe-only (the Venin weapons). A laguz's own attack comes with its class, not an item, so it's
 * never taken.
 */
export const fe10ItemSources = itemSourcesFor(FE10_MAP_SET, new Set(FE10_WEAPONS.filter((w) => w.foeOnly).map((w) => w.name)), {
  categories: new Map(FE10_WEAPONS.filter((w) => w.category !== 'Strike').map((w) => [w.name, w.category])),
  listed: new Set(FE10_WEAPONS.filter((w) => !w.shop && !w.bargain && !w.forge && !w.foeOnly).map((w) => w.name)),
  any: true,
})

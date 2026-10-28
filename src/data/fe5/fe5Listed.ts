import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE5_ITEM_SOURCES } from './fe5ItemSources'
import { FE5_WEAPONS } from './fe5Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has). None is foe-only: any foe can be captured, and a captured foe's items can be taken.
 */
export const FE5_LISTED: ChapterWeapon[] = FE5_WEAPONS.filter((w) => FE5_ITEM_SOURCES[w.name]?.length)

import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE6_ITEM_SOURCES } from './fe6ItemSources'
import { FE6_WEAPONS } from './fe6Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has: the Poison lance and bow, Fortify). A weapon only foes carry is marked: The Binding Blade's thieves can't steal
 * weapons and foes drop nothing, so it never reaches you.
 */
export const FE6_LISTED: ChapterWeapon[] = FE6_WEAPONS.filter((w) => FE6_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE6_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

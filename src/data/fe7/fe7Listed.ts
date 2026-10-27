import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE7_ITEM_SOURCES } from './fe7ItemSources'
import { FE7_WEAPONS } from './fe7Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has). A weapon only foes carry is marked: The Blazing Blade's thieves steal only items, not weapons, so it never reaches
 * you.
 */
export const FE7_LISTED: ChapterWeapon[] = FE7_WEAPONS.filter((w) => FE7_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE7_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

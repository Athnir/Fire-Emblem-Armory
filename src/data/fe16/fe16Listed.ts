import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE16_ITEM_SOURCES } from './fe16ItemSources'
import { FE16_WEAPONS } from './fe16Weapons'

/**
 * The weapons the weapon page lists: those something in the game gives or a unit carries (the item table also holds weapons nobody
 * has). A weapon only foes carry, which nothing gives you, is marked (whether a thief's Steal can take one isn't traced yet).
 */
export const FE16_LISTED: ChapterWeapon[] = FE16_WEAPONS.filter((w) => FE16_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE16_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE8_ITEM_SOURCES } from './fe8ItemSources'
import { FE8_WEAPONS } from './fe8Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has). A weapon only foes carry is marked: The Sacred Stones' thieves steal only items, not weapons, so it never reaches
 * you.
 */
export const FE8_LISTED: ChapterWeapon[] = FE8_WEAPONS.filter((w) => FE8_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE8_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE11_ITEM_SOURCES } from './fe11ItemSources'
import { FE11_WEAPONS } from './fe11Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries. A weapon only foes carry and never drop
 * is marked: Shadow Dragon's thieves steal items, not weapons, so it never reaches you.
 */
export const FE11_LISTED: ChapterWeapon[] = FE11_WEAPONS.filter((w) => FE11_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE11_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

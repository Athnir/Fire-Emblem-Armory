import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE3_ITEM_SOURCES } from './fe3ItemSources'
import { FE3_WEAPONS } from './fe3Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has). A weapon only foes carry is marked: Mystery of the Emblem's foes drop only their item slots (and gold), never what
 * they wield, and its thieves can't steal, so it never reaches you.
 */
export const FE3_LISTED: ChapterWeapon[] = FE3_WEAPONS.filter((w) => FE3_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE3_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

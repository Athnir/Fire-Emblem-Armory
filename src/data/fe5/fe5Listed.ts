import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE5_ITEM_SOURCES } from './fe5ItemSources'
import { FE5_WEAPONS } from './fe5Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item table also holds weapons
 * nobody has). A weapon only foes that can be neither captured nor robbed of it carry ('foe-held': the Loptrian Fang, at Con 20
 * and too heavy to steal; Chapter 5's Shadow Sword, whose arena door takes Mareeta away) is marked foe-only.
 */
export const FE5_LISTED: ChapterWeapon[] = FE5_WEAPONS.filter((w) => FE5_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE5_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe-held')) ? { ...w, foeOnly: true } : w,
)

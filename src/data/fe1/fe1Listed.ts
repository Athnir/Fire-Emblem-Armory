import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE1_ITEM_SOURCES } from './fe1ItemSources'
import { FE1_WEAPONS } from './fe1Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries (the item arrays also hold weapons
 * nobody has). A weapon only foes carry is marked: a defeated foe drops only its second item (6:$AD79), never the one it fights with,
 * and the game has no stealing, so it never reaches you.
 */
export const FE1_LISTED: ChapterWeapon[] = FE1_WEAPONS.filter((w) => FE1_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE1_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

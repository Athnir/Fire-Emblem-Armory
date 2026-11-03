import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE4_ITEM_SOURCES } from './fe4ItemSources'
import { FE4_WEAPONS } from './fe4Weapons'

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries. A weapon only foes carry is marked:
 * Genealogy of the Holy War's player only ever owns one of the 140 copies the game tracks, foes hold item types, not copies, and
 * Steal takes only gold, so a weapon no copy exists of never reaches you (the sources say a foe's weapon only where nothing else gives
 * it).
 */
export const FE4_LISTED: ChapterWeapon[] = FE4_WEAPONS.filter((w) => FE4_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE4_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

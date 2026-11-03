import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE17_ITEM_SOURCES } from './fe17ItemSources'
import { FE17_WEAPONS } from './fe17Weapons'

/**
 * The weapons the weapon page lists: those something in the game gives or a unit carries (the item table also holds weapons nobody
 * has). A weapon only foes carry and never drop is marked: Engage has no stealing of weapons (a thief's Steal takes items).
 */
export const FE17_LISTED: ChapterWeapon[] = FE17_WEAPONS.filter((w) => FE17_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE17_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

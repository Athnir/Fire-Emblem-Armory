import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE2_ITEM_SOURCES } from './fe2ItemSources'
import { FE2_WEAPONS } from './fe2Weapons'

/**
 * The weapons, shields and rings the weapon page lists: those something in the game hands out or a unit carries. Gaiden has no shops
 * and no stealing; a defeated foe drops what it holds to the unit that beats it (6:$AA4B), so only a weapon nothing gives (Duma's
 * Tentacle, the attack the battle code picks for him) is marked foe-only.
 */
export const FE2_LISTED: ChapterWeapon[] = FE2_WEAPONS.filter((w) => FE2_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE2_ITEM_SOURCES[w.name].every((s) => s.kind.startsWith('foe')) ? { ...w, foeOnly: true } : w,
)

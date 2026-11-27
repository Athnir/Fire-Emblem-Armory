import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE12_ITEM_SOURCES } from './fe12ItemSources'
import { FE12_WEAPONS } from './fe12Weapons'

/** A source only foes give: what they carry and don't drop (the story's maps alone: the Chronicles and downloadable chapters give
 * nothing). */
const foeKind = (kind: string) => kind.startsWith('foe')

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries. A weapon only foes carry and never drop
 * is marked: New Mystery of the Emblem has no stealing (no unit command steals: its menu's MUMH_ texts), so it never reaches you.
 */
export const FE12_LISTED: ChapterWeapon[] = FE12_WEAPONS.filter((w) => FE12_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE12_ITEM_SOURCES[w.name].every((s) => foeKind(s.kind)) ? { ...w, foeOnly: true } : w,
)

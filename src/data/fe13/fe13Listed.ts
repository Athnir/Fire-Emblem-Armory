import type { ChapterWeapon } from '../../components/ChapterWeapons'
import { FE13_ITEM_SOURCES } from './fe13ItemSources'
import { FE13_WEAPONS } from './fe13Weapons'

/** A source only foes give: what they carry and don't drop (no one in Awakening can steal a weapon). */
const foeKind = (kind: string) => kind.replace(/^dlc-/, '').startsWith('foe')

/**
 * The weapons the weapon page lists: those something in the game hands out or a unit carries. A weapon only foes carry (and none
 * drops) is marked; one that sells for a quarter of its worth says so in its price.
 */
export const FE13_LISTED: (ChapterWeapon & { forge?: true })[] = FE13_WEAPONS.filter((w) => FE13_ITEM_SOURCES[w.name]?.length).map((w) => {
  const out = FE13_ITEM_SOURCES[w.name].every((s) => foeKind(s.kind)) ? { ...w, foeOnly: true } : { ...w }
  if (w.worth && w.rules?.some((r) => r.startsWith('Sells for a quarter'))) out.sell = Math.floor(w.worth / 4)
  return out
})

import { FE15_ITEM_SOURCES } from './fe15ItemSources'
import type { Fe15Weapon } from './fe15Types'
import { FE15_WEAPONS } from './fe15Weapons'

/** A source only foes give: what they carry and don't drop (no one in Echoes can steal a weapon). */
const foeKind = (kind: string) => kind.replace(/^amiibo-/, '').startsWith('foe')

/**
 * The weapons the weapon page lists: those something in the game hands out, a unit carries, or a forge evolves into. A weapon only
 * foes carry (the monsters' claws and breath, Berkut's Kriemhild) is marked.
 */
export const FE15_LISTED: Fe15Weapon[] = FE15_WEAPONS.filter((w) => FE15_ITEM_SOURCES[w.name]?.length).map((w) =>
  FE15_ITEM_SOURCES[w.name].every((s) => foeKind(s.kind)) ? { ...w, foeOnly: true } : { ...w },
)

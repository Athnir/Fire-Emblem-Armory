import type { ItemSource } from '../components/ChapterWeapons'
import type { ChapterMap } from '../data/maps/types'

/** One line of a weapon's "Where it turns up": the same way of getting it (a shop, a foe's drop, a unit's starting items) in one
 * story, with every chapter it happens in. */
export interface SourceRow {
  text: string
  /** It came with a unit arriving mid-chapter, so it counts from the next chapter. */
  later: boolean
  /** The story or route the chapters are in, where the game has more than one ("Eliwood's story"). */
  route?: string
  /** The chapters, short ("Ch.11"), in the order given. */
  chapters: string[]
}

/**
 * Sources merged into rows: the same text in the same story is one row listing its chapters, so a weapon three shops sell reads
 * "Sold at the armory (Eliwood's story): Ch.11, Ch.12, Ch.14" rather than three lines. Rows keep the order of their first source.
 */
export function sourceRows(
  sources: ItemSource[],
  mapOf: (mapId: string) => ChapterMap | undefined,
  short: (map: ChapterMap) => string,
  routeName?: (map: ChapterMap) => string | undefined,
): SourceRow[] {
  const rows = new Map<string, SourceRow>()
  for (const s of sources) {
    const m = mapOf(s.mapId)
    const later = s.kind.endsWith('-later')
    const route = m && routeName ? routeName(m) : undefined
    const key = JSON.stringify([s.text, later, route])
    const row = rows.get(key) ?? { text: s.text, later, route, chapters: [] }
    const chapter = m ? short(m) : s.mapId
    if (!row.chapters.includes(chapter)) row.chapters.push(chapter)
    rows.set(key, row)
  }
  return [...rows.values()]
}

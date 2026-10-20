import type { ChapterMap, Difficulty } from './types'

/** One game's maps and the game facts the map page needs to show them. */
export interface MapSet {
  maps: ChapterMap[]
  /** Fates' route buttons and paralogue list. A game without routes lists every chapter in one dropdown. */
  routes?: {
    list: readonly string[]
    /** The route's own chapters, in order. */
    maps: (route: string) => ChapterMap[]
    /** Side chapters the route can reach (shown in their own dropdown). */
    side: (route: string) => ChapterMap[]
    /** The route a map is listed under. */
    of: (map: ChapterMap) => string
  }
  /** A game without routes can still list side maps in a second dropdown (Path of Radiance's trial maps).
   * They're left out of the chapter dropdown. */
  extras?: { label: string; maps: ChapterMap[] }
  difficulties: { value: Difficulty; label: string }[]
  /** The game's movement groups, in the order the terrain panel lists them, with example classes. */
  moveClasses: readonly string[]
  moveClassExamples: Record<string, string>
  /** Whose starting tile `corrinStart` is ('Corrin', 'Ike'). */
  lord: string
  /** A rule about terrain bonuses worth showing under them (Fates: fliers get none). */
  terrainNote?: string
  /** A map's name in its dropdown, and in full. */
  chapterLabel: (map: ChapterMap) => string
  mapLabel: (map: ChapterMap) => string
}

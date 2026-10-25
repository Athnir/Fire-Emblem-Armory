import type { ChapterMap, Difficulty } from './types'

/**
 * A game's story in the order it's played, for the spoiler block, which opens one chapter at a time.
 * Side maps (Path of Radiance's trial maps) aren't part of it: they open once the story is cleared.
 */
export interface StoryOrder {
  maps: ChapterMap[]
  /** A chapter without its title ('Chapter 8', 'Part 3, Chapter 4'): what "Proceed" and "Jump to" say. Two maps
   * that share a chapter get "(part 1)" and "(part 2)" added. */
  name: (map: ChapterMap) => string
  /** A chapter as a shop list writes it ('Ch.8', 'Prologue', 'Endgame (2)'). */
  short: (map: ChapterMap) => string
  /** The part a chapter is in (Radiant Dawn), where the game has them. */
  part?: (map: ChapterMap) => number
  /**
   * When a map outside the story opens: its index in the story, Infinity for never (the other routes' chapters, a
   * paralogue this route can't reach). Without it, side maps open once the story is cleared (Path of Radiance's trial maps).
   */
  opensAt?: (mapId: string) => number
}

/**
 * A game whose story splits (Fates' three routes after Chapter 5): the chapters everyone plays, then one story for each
 * route, each starting with those same chapters. The spoiler block asks which route you're on at the split.
 */
export interface StoryFork {
  before: StoryOrder
  choices: { id: string; label: string; story: StoryOrder }[]
}

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
  /** The order the spoiler block opens the maps in. A game without it can't use the spoiler block yet. */
  story?: StoryOrder
  /** A map's name in its dropdown, and in full. */
  chapterLabel: (map: ChapterMap) => string
  mapLabel: (map: ChapterMap) => string
}

import type { TerrainInfo } from './fatesTerrain'

/**
 * Map data model. Coordinates everywhere are the games' own convention: the bottom-left tile is
 * (1, 1), X counts right and Y counts up. Some sources count rows from the top instead (the Fire
 * Emblem Wiki's chapter pages do), so each source's numbering is converted once, at data entry.
 */
export type Difficulty = 'Normal' | 'Hard' | 'Lunatic'
export const DIFFICULTIES: Difficulty[] = ['Normal', 'Hard', 'Lunatic']

export type Tile = [x: number, y: number]

/** A tile that can differ by difficulty. Conquest 12's Dragon Vein, for one, sits on a different
 * tile on Lunatic. `default` applies to any difficulty not listed. */
export type DifficultyTile = { default: Tile } & Partial<Record<Difficulty, Tile>>

/** One letter per tile in a map's `grid`. Stats live in the per-game terrain table. */
export type TerrainLetter =
  | '.' // floor
  | '#' // wall
  | 'p' // pillar
  | 'f' // woods
  | 'w' // water / spring
  | 'S' // stairs
  | 'c' // chest
  | 'd' // door
  | 't' // throne
  | 'b' // bridge
  | 'r' // rubble / debris
  | 'H' // healing tile
  | 'x' // chasm / empty space (fliers only)
  | 'F' // fort
  | 'G' // old gate
  | 'B' // building
  | 'v' // village
  | 'n' // snow mountain
  | 'W' // wasteland
  | 'g' // gate
  | 'k' // thick wood (fliers only)
  | 'a' // lake / sea (fliers only; rivers are 'w')
  | 'l' // partition (low wall, fliers only)
  | 'C' // cliff / peak (fliers only)
  | 'L' // ballista
  | 'O' // fire orb (magic launcher)
  | 'U' // launcher (hidden-weapon launcher)
  | 'T' // caltrops
  | 'D' // dark waters
  | 'e' // gateway (Avo +10)
  | 'Q' // cushion
  | 'V' // village that can't be visited
  | 'z' // storm (fliers only, cost 2)
  | 'j' // chamber (heals 5%)
  | 'i' // frozen lake (walkable until melted)
  | 's' // desert
  | 'P' // acid bog (hurts each turn)
  | 'X' // darkness (impassable until lifted)
  | 'K' // ward (Avo +40, heals 20%)
  | 'u' // shallow water (puddle)
  | 'Y' // summoning sigil
  | 'M' // muck (hurts each turn)
  | 'Z' // fissure
  | 'E' // ledge (Def +2, Avo +30)

export type StatKey = 'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'res'

/** What breaking a pot does to every unit (either side) within its radius. */
export type PotEffect =
  | { type: 'heal'; percent: number }
  | { type: 'damage'; percent: number }
  /** +/- to listed stats. `kind` follows the game's split: a "tonic" boost (+2) and a "status"
   * boost (+4) stack with each other, but not with another of the same kind. */
  | { type: 'stats'; kind: 'tonic' | 'status' | 'debuff'; changes: Partial<Record<StatKey, number>> }
  | { type: 'silence' }
  | { type: 'freeze' }
  | { type: 'hex' }

export type MapObject =
  | { type: 'pot'; tile: Tile; pot: 'medicine' | 'poison'; effect: PotEffect; radius: number }
  | { type: 'chest'; tile: Tile; contents: string }
  | { type: 'door'; tile: Tile }
  /** `reward` is empty when a visit gives nothing. */
  | { type: 'village'; tile: Tile; reward: string; note?: string }

export interface MapUnit {
  /** boss = the chapter's boss; named = another named foe worth drawing attention to; enemy = a
   * common foe (shown as a plain marker); ally = a named green (NPC) unit. */
  type: 'boss' | 'named' | 'enemy' | 'ally'
  name: string
  tile: Tile
  note?: string
  /** Two units paired up on one tile. */
  paired?: boolean
  /** The supporting unit of a pair-up, when it's worth naming (a generic one is just its army's name). */
  partner?: string
  /** Items dropped on defeat. */
  drops?: string[]
  /** Set only on bosses / named foes that Niles (Conquest) or Orochi (Birthright) can capture.
   * Anyone playable on any route never can; generic foes can but aren't worth noting. */
  capturable?: true
  /** Only present on these difficulties; on all of them when omitted. */
  difficulties?: Difficulty[]
}

/** When a group arrives, read from the chapter's script, and any map areas whose entry triggers it. */
export interface Arrival {
  /** One sentence, or one per difficulty when they differ ("Turn 4, enemy phase"). */
  when?: string | Partial<Record<Difficulty, string>>
  /** Entering (or, for 'enemy', reaching) one of these brings the group in: [left, bottom, right, top]. */
  areas?: { who: 'player' | 'enemy'; rect: [number, number, number, number] }[]
}

/** A group of enemies that arrives mid-chapter: each moves from where it enters to its tile. */
export interface ReinforcementGroup extends Arrival {
  id: string
  /** The game's own group number ("Group 3"); which turn it arrives isn't in the map data. */
  label: string
  units: (MapUnit & { from?: Tile })[]
}

/** A playable unit that joins mid-chapter, walking in from `from` to `tile`. */
export interface Joiner extends Arrival {
  name: string
  tile: Tile
  from: Tile
  /** Joiners listed together arrive together. */
  group: string
}

export interface MapObjective {
  type: 'escape' | 'seize' | 'defend' | 'arrive'
  tiles: Tile[]
  label: string
}

/** Something that reshapes the map when triggered. Previewed one at a time from its own panel. */
export interface MapChange {
  id: string
  /** A Dragon Vein a royal uses, or a wall / partition attacked down. */
  trigger: 'dragonVein' | 'breakable'
  tile: DifficultyTile
  usableBy: string
  effect: string
  /** Breaks every pot on the map (each one's effect still fires). */
  breaksAllPots?: boolean
  /** Tiles this change reshapes, and what each becomes. */
  patch?: { tile: Tile; becomes: TerrainLetter }[]
}

export interface ChapterMap {
  id: string
  /** Fates' routes; 'Story' for a game without them. */
  route: 'Birthright' | 'Conquest' | 'Revelation' | 'Shared' | 'Paralogue' | 'DLC' | 'Story'
  /** Paralogues only: the routes that can reach it. */
  availableIn?: ('Birthright' | 'Conquest' | 'Revelation')[]
  /** The game's heading for it, where it isn't a plain chapter ('Xenologue', 'Heirs of Fate', 'Hero Battle'). */
  heading?: string
  chapter: number
  title: string
  location?: string
  width: number
  height: number
  /** Top row FIRST (y = height), so the file reads like the map. One TerrainLetter per tile. */
  grid: string[]
  /** Tiles under Revelation's darkness: the grid holds the terrain beneath; nothing enters until it lifts. */
  dark?: Tile[]
  victory: string
  defeat: string
  objectives: MapObjective[]
  units: MapUnit[]
  starts: Tile[]
  reinforcements?: ReinforcementGroup[]
  joiners?: Joiner[]
  /** The lord's own starting tile (Corrin's, Ike's; one of `starts`), when known. */
  corrinStart?: Tile
  /** Units besides Corrin the game deploys for you: on a fixed tile, or (no tile) wherever you place them. */
  forced?: { name: string; tile?: Tile }[]
  objects: MapObject[]
  changes: MapChange[]
  /** Short facts only (who can't deploy, when reinforcements come), not strategy. */
  notes: string[]
  /** Facts still to be confirmed in-game, shown in the UI rather than presented as certain. */
  unconfirmed?: string[]
  /** This map's exceptions to the game-wide terrain table (e.g. Chapter 1's 50% healing tile). */
  terrainOverrides?: Partial<Record<TerrainLetter, Partial<TerrainInfo>>>
  /** The game's own terrain table, for a game other than Fates. */
  terrain?: Partial<Record<TerrainLetter, TerrainInfo>>
}

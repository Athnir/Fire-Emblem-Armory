import type { TerrainInfo } from './fatesTerrain'

/**
 * Map data model. Coordinates everywhere are the games' own convention: the bottom-left tile is
 * (1, 1), X counts right and Y counts up. Some sources count rows from the top instead (the Fire
 * Emblem Wiki's chapter pages do), so each source's numbering is converted once, at data entry.
 */
export type Difficulty = 'Easy' | 'Normal' | 'Hard' | 'Lunatic'
export const DIFFICULTIES: Difficulty[] = ['Normal', 'Hard', 'Lunatic']

export type Tile = [x: number, y: number]

/** A tile that can differ by difficulty. Conquest 12's Dragon Vein, for one, sits on a different
 * tile on Lunatic. `default` applies to any difficulty not listed. */
export type DifficultyTile = { default: Tile } & Partial<Record<Difficulty, Tile>>

import type { TerrainCode } from './terrainCodes'

export type { TerrainCode }

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
  /** A castle on the map (Genealogy of the Holy War): its name, and what it means for the chapter (home castle, the one to seize). */
  | { type: 'castle'; tile: Tile; name: string; note?: string }
  /** Something buried in an area ([left, bottom, right, top]) for a unit to find (Path of Radiance's desert). */
  | { type: 'hidden'; tile: Tile; area: [number, number, number, number]; contents: string; note?: string }
  /** A ballista (Path of Radiance): a bow user on `tile` fires the `weapon` of the machine on `machine`, next to it. */
  | { type: 'ballista'; tile: Tile; machine: Tile; weapon: string }
  /** A pit trap in the floor (Path of Radiance's Ch.23 bridge): a ground unit that steps on it falls in and stops. */
  | { type: 'pit'; tile: Tile }
  /** A house ([left, bottom, right, top]) the enemy's arsonists can set alight; a unit beside it can put it out
   * (Radiant Dawn Part 3 Ch.9). */
  | { type: 'fire'; tile: Tile; area: [number, number, number, number] }
  /** A shop on the map (The Binding Blade): an armory, a vendor or a secret shop, and what it sells. */
  | { type: 'shop'; tile: Tile; kind: string; stock: string[] }
  /** An event tile (Awakening): a unit that stops on it gets a random bonus. */
  | { type: 'event'; tile: Tile }
  /** A shiny spot (Fates' challenge battles): a unit that stops on it finds gold, ore, an item or weapon experience. */
  | { type: 'shiny'; tile: Tile }

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
  /** What the unit carries and fights with (a foe's own weapons, staves and items), from the placement files. */
  carries?: string[]
  /** Who can talk to them, and whether that recruits them ('Recruit: talk with Ike'). */
  talk?: string
  /** Set only on bosses / named foes that Niles (Conquest) or Orochi (Birthright) can capture.
   * Anyone playable on any route never can; generic foes can but aren't worth noting. */
  capturable?: true
  /** Only present on these difficulties; on all of them when omitted. */
  difficulties?: Difficulty[]
  /** A green unit with no name of its own (another army's soldier, a horse): drawn as a plain green dot, not the
   * person icon, which is kept for named green units. */
  generic?: true
  /** Where its AI sends it, when that's a fixed spot rather than the nearest (Radiant Dawn Part 3 Ch.3's
   * horses each run for their own exit): shown when the unit is tapped. */
  goesTo?: Tile[]
  /** Who the game places on this tile instead when this character is gone (Radiant Dawn: Lethe died earlier, so
   * Kezhda stands here; Jill left Micaiah's army, so a Dragonmaster does). The map's stand-in toggle swaps them all. */
  standIn?: StandIn
}

export interface StandIn {
  type: MapUnit['type']
  name: string
  note: string
  generic?: true
  drops?: string[]
  /** When it stands in: 'Lethe has died earlier'. */
  when: string
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
  /** Arrives as a green unit (another army, or a recruit you still have to talk to), not under your control. */
  ally?: boolean
  /** A green unit with no name of its own: a plain green dot, like `MapUnit.generic`. */
  generic?: true
  /** Anything else about them ('Carrying Leanne'). */
  note?: string
  /** Who can talk to them, and whether that recruits them. */
  talk?: string
}

export interface MapObjective {
  /** burn: supplies to set alight (Radiant Dawn Part 3 Ch.3), one objective per set. */
  type: 'escape' | 'seize' | 'defend' | 'arrive' | 'burn'
  tiles: Tile[]
  label: string
}

/** Something that reshapes the map when triggered. Previewed one at a time from its own panel. */
export interface MapChange {
  id: string
  /** A Dragon Vein a royal uses, a wall / partition attacked down, a boulder rolling down its path, a torch
   * lit on a fog map (Radiant Dawn), a lava floor that turns to hazard on set turns (Awakening Ch.18), or another
   * change a chapter's script makes (Awakening Ch.23's barrier falling). */
  trigger: 'dragonVein' | 'breakable' | 'boulder' | 'torch' | 'eruption' | 'event'
  tile: DifficultyTile
  usableBy: string
  effect: string
  /** Breaks every pot on the map (each one's effect still fires). */
  breaksAllPots?: boolean
  /** Tiles this change reshapes, and what each becomes. */
  patch?: { tile: Tile; becomes: TerrainCode }[]
  /** A boulder's route, from where it starts to where it ends. */
  path?: Tile[]
  /** A torch: once lit, it lights every tile within this many steps. */
  radius?: number
  /** A torch already lit when the chapter starts: previewing it puts it out. */
  lit?: boolean
  /** A change that covers an area rather than one tile (Revelation 10's snow): listed on every tile it reshapes, with no
   * marker of its own. */
  wide?: true
}

/** A fence: a thin barrier along one side of a tile that units can't cross. */
export interface MapWall {
  tile: Tile
  side: 'n' | 'e' | 's' | 'w'
}

export interface ChapterMap {
  id: string
  /** Fates' routes; The Blazing Blade's stories (Lyn's, Eliwood's, Hector's); The Sacred Stones' routes and side maps; 'Story' for
   * a game without them, and 'Trial' for Path of Radiance's trial maps. */
  route:
    | 'Birthright'
    | 'Conquest'
    | 'Revelation'
    | 'Shared'
    | 'Paralogue'
    | 'DLC'
    | 'Story'
    | 'Trial'
    | 'Lyn'
    | 'Eliwood'
    | 'Hector'
    | 'Eirika'
    | 'Ephraim'
    | 'Extra'
    | 'Alm'
    | 'Celica'
    | 'Challenge'
  /** Paralogues and challenge battles only: the routes that can reach it. */
  availableIn?: ('Birthright' | 'Conquest' | 'Revelation')[]
  /** A challenge battle (Fates): the chapter or paralogue map it's fought on, whose terrain it keeps. */
  challengeOf?: string
  /** A challenge battle's foe groups (Fates): the tiles each one's foes can stand on, outlined on the map. A battle has one
   * group, either one, or both in a dual-boss battle. */
  foeGroups?: { label: string; tiles: Tile[] }[]
  /** The game's heading for it, where it isn't a plain chapter ('Xenologue', 'Heirs of Fate', 'Hero Battle'). */
  heading?: string
  chapter: number
  title: string
  location?: string
  width: number
  height: number
  /** Top row FIRST (y = height), so the file reads like the map. Two characters (one TerrainCode) per tile. */
  grid: string[]
  /** Fences along tile sides (Path of Radiance). */
  walls?: MapWall[]
  /** Tiles under Revelation's darkness: the grid holds the terrain beneath; nothing enters until it lifts. */
  dark?: Tile[]
  /** A grinding map (Fates DLC): its reinforcements spawn at random, so not every group arrives. Every other
   * map's reinforcements are fixed by its script. */
  randomSpawns?: true
  /** What the groups are, where they aren't reinforcements (Echoes: a dungeon's formations and fixed encounters, a cemetery's
   * layouts): said in place of the usual line about when they arrive. */
  groupsNote?: string
  /** Fog of war: everything outside the light of the torches being previewed as lit is shaded. */
  fog?: boolean
  /** Tiles under a roof that lifts when what's inside is opened (Radiant Dawn's cells): to check in-game. */
  roofed?: Tile[]
  /** Clouds that drift one tile left each phase (Radiant Dawn Part 2's Prologue): the whole map's pattern on the
   * shown rows (top first, '#' a cloud), the pattern column at the map's column 1, and the chapter's turns. */
  clouds?: { pattern: string[]; left: number; turns: number }
  victory: string
  defeat: string
  objectives: MapObjective[]
  units: MapUnit[]
  starts: Tile[]
  reinforcements?: ReinforcementGroup[]
  joiners?: Joiner[]
  /** What each of your own units starts the chapter carrying (Fates): weapons you hold from this chapter on. */
  kit?: { name: string; items: string[] }[]
  /** The lord's own starting tile (Corrin's, Ike's; one of `starts`), when known. */
  corrinStart?: Tile
  /** Whose starting tile `corrinStart` is, where it isn't the game's one lord (Radiant Dawn's change with each Part). */
  lord?: string
  /** Units besides Corrin the game deploys for you: on a fixed tile, or (no tile) wherever you place them. */
  forced?: { name: string; tile?: Tile }[]
  objects: MapObject[]
  changes: MapChange[]
  /** Short facts only (who can't deploy, when reinforcements come), not strategy. */
  notes: string[]
  /** Facts still to be confirmed in-game, shown in the UI rather than presented as certain. */
  unconfirmed?: string[]
  /** This map's exceptions to the game-wide terrain table (e.g. Chapter 1's 50% healing tile). */
  terrainOverrides?: Partial<Record<TerrainCode, Partial<TerrainInfo>>>
  /** The difficulties this map is played on, where it's fewer than the game's (The Blazing Blade's Lyn's story: Normal only). */
  difficulties?: Difficulty[]
  /** The game's own terrain table, for a game other than Fates. */
  terrain?: Partial<Record<TerrainCode, TerrainInfo>>
}
